# Engine internals

This is the implementation of the Robot Strategy Game — everything an
**agent author** doesn't need to see. If you're writing agents, see the
top-level `README.md` (or `documentation/`) instead; this file is for anyone
editing the engine itself.

## Module map

| Module | Responsibility |
|---|---|
| `config.py` | All tunable constants (robot & box physics, scoring, timing). Map geometry (size, areas, `INITIAL_BOXES`) is loaded from `map.json` and re-exported under the same names. Pure data, no logic. |
| `map.json` | The map definition: overall size, `player0_area`/`player1_area`/`scoring_areas` rectangles, and `initial_boxes` (position, orientation, color). Loaded by `config.py` at import time. |
| `game.py` | The actual simulation: `Area`, `Map`, `Box`, `Robot`, `GameState` dataclasses; geometry helpers (`_normalize`, `_dot`, `_box_corners`, `_circle_rect_distance`, `_circle_rect_collides`, `_obb_obb_collides`, `_circle_in_map`, `_longest_move_to_rect_outside`, `_longest_move_to_rect_inside`, `_longest_move_to_circle`, `_longest_move`); action implementations (`do_move`, `do_rotate`, `do_pickup`, `do_set_color`, `do_lay_down`), each gated by the shared `_require_not_busy` cooldown check; `is_box_accessible`, `is_move_colliding`, `compute_scores`; `GameError`. |
| `interface.py` | The agent-facing API. Wraps `game.py` behind a `_Context`/`_ctx()` mechanism that enforces the one-action-per-turn rule and exposes only player-scoped, read-only-feeling free functions. **The only engine module agent code imports.** |
| `display.py` | pygame rendering: `init_window`, `draw_state`, `handle_events`, `show`. Imports `game` private helpers directly (`_box_corners`, etc.) to draw oriented rectangles. |
| `history.py` | JSON (de)serialization of `GameState` snapshots: `snapshot`, `save`, `load`, `load_map`, `load_frame`, `_map_to_dict`. |
| `run_game.py` | The game loop / runner: loads agents, ticks the simulation, prints progress, writes history. Entry point invoked by `play.py run`. |
| `viewer.py` | Thin wrapper around `history` + `display` that replays a saved JSON file frame by frame. Entry point invoked by `play.py view`. |

All of these live together in `engine/` and import each other by plain name
(`import game`, `import config`, `from game import GameError`, …) — see
"Import wiring" below for why that works without making `engine` a package.

## Data classes (`game.py`)

```python
@dataclass
class Box:
    id: int
    position: Tuple[float, float]
    orientation: Tuple[float, float]   # unit vector along the width axis
    color: int                         # 0 or 1
    owner: int                         # -1 = on the ground, else player id

@dataclass
class Robot:
    player: int
    position: Tuple[float, float]
    orientation: Tuple[float, float]
    held_boxes: List[int]              # box ids, capped at MAX_BOXES_HELD
    cooldown: int                      # turns remaining until next action allowed (0 = free)

@dataclass
class Area:
    id: int        # stable, assigned sequentially at map-build time
    type: int      # 0 = player0, 1 = player1, 2 = scoring
    x: float; y: float; width: float; height: float
    def contains(self, point) -> bool: ...

@dataclass
class Map:
    width: float; height: float
    areas: List[Area]

@dataclass
class GameState:
    tick: int
    map: Map
    robots: List[Robot]   # index 0/1 = player 0/1
    boxes: List[Box]
    def get_area(self, area_id) -> Optional[Area]: ...
    def get_box(self, box_id) -> Optional[Box]: ...
```

`Area.id` and `Box.id` are assigned once at construction and never reused.
Areas are numbered in `_build_map()` in config order: player0 area (0),
player1 area (1), then each scoring area (2, 3, …) via a `next_id` counter.

## Geometry & collision implementation

- **Coordinates**: `(x, y)`, `(0, 0)` = top-left. Directions/orientations are
  unit vectors. Boxes are oriented rectangles (`orientation` = unit vector
  along the `BOX_WIDTH` axis); areas and the map are axis-aligned.
- **Circle ↔ oriented-rectangle distance** (`_circle_rect_distance`):
  transforms the circle's center into the rectangle's local space (using
  `orientation` and its perpendicular as basis vectors), clamps to the
  half-extents to find the nearest point on the rectangle, then measures the
  distance in local space. Used for accessibility checks (`is_box_accessible`,
  `ACCESSIBILITY_RADIUS`) and for `get_box_distance`/`get_area_distance`.
  `_circle_rect_collides` is the boolean form (distance < radius).
- **Circle ↔ circle**: plain Euclidean distance, used for robot-vs-robot
  collision.
- **OBB ↔ OBB** (`_obb_obb_collides`): Separating Axis Theorem over the four
  face-normal axes of the two oriented rectangles (`_box_corners` produces the
  four corners from center/orientation/half-extents). Used only for
  box-vs-box overlap checks in `do_lay_down`.
- **Map edge**: simple AABB containment check (`_circle_in_map`).
- **Movement collision** (`do_move`): the maximum safe travel distance is
  computed by `_longest_move` as the minimum of `_longest_move_to_rect_inside`
  (map edge), `_longest_move_to_circle` (other robot), and
  `_longest_move_to_rect_outside` (each laid-down box) — the robot is moved to
  just-before the obstacle. `interface.get_obstacle_distance` exposes this raw
  value (uncapped, possibly `inf`) to agents.
- **Lay-down placement**: fixed `LAY_DOWN_DISTANCE` directly in front of the
  robot (along its current orientation), the box inherits the robot's
  orientation. Fails with `GameError` (turn not consumed) if the spot is out
  of map bounds or SAT-overlaps another box.

## Action costs / cooldown (`game.py`)

`Robot.cooldown` tracks how many more ticks the robot is "busy" after
performing a costly action (0 = free). `_require_not_busy(robot)` is called
first by **all five** `do_*` functions — including `do_rotate` — and raises
`GameError` if `cooldown > 0`, so a busy robot is fully frozen (it can't even
turn in place).

On success, `do_move`, `do_pickup`, `do_set_color` and `do_lay_down` set
`robot.cooldown = config.<ACTION>_COOLDOWN` (`MOVE_COOLDOWN`,
`PICKUP_COOLDOWN`, `SET_COLOR_COOLDOWN`, `LAY_DOWN_COOLDOWN`). This includes a
0-distance `do_move` (e.g. driving straight into a wall still "takes time").
`do_rotate` never sets `cooldown`.

`run_game.py`'s per-player `finally` block decrements `robot.cooldown` by 1
(floored at 0) once per tick, after that tick's action attempt — this is what
gives `X_COOLDOWN = N` the meaning "robot occupied for N total turns
including the one the action succeeded on" (N=1 ⇒ no extra delay; N>1 ⇒ N-1
additional frozen turns). `interface.get_cooldown(player)` exposes the raw
value to agents read-only.

## The one-action rule (`interface._Context`)

```python
class _Context:
    __slots__ = ("game", "player_id", "action_taken")
    def require_action_available(self): ...   # raises ActionError if action_taken
    def mark_action_taken(self): ...
```

`run_game.py` constructs a fresh `_Context` and assigns it to the module-level
`interface._context` immediately before calling `agent.make_decision()`, and
clears it (`= None`) in a `finally` block right after. `interface._ctx()`
raises `RuntimeError` if called when `_context` is `None` — this is what
prevents agents from calling interface functions outside of their turn (e.g.
from `__init__` or background threads).

Each action wrapper (`move`, `pickup`, `set_color`, `lay_down`) calls
`ctx.require_action_available()` *before* delegating to the corresponding
`do_*` function in `game.py`, and `ctx.mark_action_taken()` only on success.
`rotate` is the deliberate exception — it calls `do_rotate` directly without
touching `action_taken`, so it never counts toward the one-action-per-turn
limit and is turn-preserving. A `GameError` raised by the underlying `do_*`
propagates *before* `mark_action_taken()` is reached, which is exactly why
failed actions don't consume the turn — no special-casing needed, it falls
out of the call order.

Note that `rotate` being exempt from `action_taken`/`ActionError` does **not**
make it unconditionally free: like the other four action functions, `do_rotate`
still calls `_require_not_busy` first (see "Action costs / cooldown" above),
so a robot frozen by a previous move/pickup/set_color/lay_down also can't
rotate — that call raises `GameError` (still turn-preserving).

## Agent loading (`run_game.py`)

```python
agent0 = importlib.import_module(agents_config.PLAYER0_AGENT).Agent()
agent1 = importlib.import_module(agents_config.PLAYER1_AGENT).Agent()
```

Agent modules must define a class `Agent` with `make_decision(self)`. A
**separate instance is created per player** — even when both config slots
name the same module path (Python caches imported modules in `sys.modules`,
so the module object itself would be shared, but each `Agent()` call still
produces a distinct object with its own `__dict__`). This is what lets agents
keep per-player memory on `self` safely; see the top-level docs' "Agent
memory" section for the agent-author-facing explanation.

## Import wiring / `sys.path`

`engine/` is a plain directory, not a package — no `__init__.py`, and its
modules `import` each other by bare name (`import game as _game`, `import
config`, …). This works because:

- When you run a script directly (`python engine/run_game.py`, or via
  `play.py` → `subprocess.run([python, "engine/run_game.py", ...])`), Python
  prepends that script's own directory to `sys.path[0]`. So from inside
  `engine/run_game.py`, `import config` / `import game` / `import history`
  resolve to the sibling files in `engine/` automatically.
- `run_game.py` additionally does
  `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
  — i.e. it prepends the **project root** — so it can also
  `import agents_config` and dynamically `importlib.import_module("agents.xxx")`,
  both of which live one level up.
- `viewer.py` doesn't need the project root (it only touches `history`,
  `display`, `pygame`, all in `engine/`), so it has no extra path setup.
- Agent modules, loaded via `importlib` *after* `run_game.py` has already
  patched `sys.path`, transparently get both the project root (for `import
  config`/`import interface`, which — confusingly but correctly — resolve to
  `engine/config.py`/`engine/interface.py` because `engine/` is on the path
  too) and the root (for `import agents_config` if an agent ever wanted it).

If you ever split `engine/` into a real package, all of `game.py`'s,
`interface.py`'s, `display.py`'s, `history.py`'s, `run_game.py`'s and
`viewer.py`'s intra-engine imports would need to become relative (`from . import
game`) or package-qualified (`from engine import game`) — a more invasive
change than the current sys.path approach, which was chosen specifically to
avoid forcing agent code to ever write anything other than `import interface`.

## `play.py` (root launcher)

Lives at the project root, not here, but worth understanding since it's how
`run_game.py`/`viewer.py` actually get invoked in normal use: it's a tiny
stdlib-only script that locates `.venv`'s interpreter (`bin/python` on
Linux/macOS, `Scripts/python.exe` on Windows) and re-execs the relevant
engine entry point through `subprocess.run([venv_python, engine_script, *args],
cwd=project_root)`. Setting `cwd` to the project root (rather than `engine/`)
is what makes `saved_games/` end up at the top level. `play.py view <name>`
additionally resolves a bare filename against `saved_games/` before falling
back to treating it as a literal path.

If no `.venv` is found, `play.py` bootstraps one before doing any of the
above: `subprocess.run([sys.executable, "-m", "venv", VENV])` (using whatever
system Python launched `play.py`), then `pip install --upgrade pip` and
`pip install -r requirements.txt` inside the new venv, printing a one-time
"setting up" message. This is also why `requirements.txt` exists and why
`.venv` itself doesn't need to ship with the project (see below).

### Why `.venv` isn't shipped / isn't portable

`.venv` is full of absolute paths and platform-specific binaries: `pyvenv.cfg`
and `bin/activate*` hardcode the original machine's path, every script under
`bin/` starts with a `#!/path/to/.venv/bin/python` shebang, `bin/python` is
typically a symlink to a specific system interpreter that won't exist
elsewhere, the directory layout itself differs by OS (`bin/` + ELF binaries on
Linux/macOS vs. `Scripts/` + `.exe`/`.dll` on Windows), and compiled
dependencies like `pygame` ship OS/libc-specific wheels. None of that survives
copying the folder to another machine (or even moving it on the same
machine). That's why `.venv` should be excluded when zipping/sharing this
project — `requirements.txt` plus `play.py`'s auto-bootstrap (above)
regenerates a working one on the target machine on first run instead.

## History format (`history.py`)

`snapshot(state)` captures `tick`, all robots (`position`, `orientation`,
`held_boxes`, `cooldown`), and all boxes (`position`, `orientation`, `color`,
`owner`). `save(frames, game_map, path)` writes one JSON document: the static
map once (`_map_to_dict`, preserving `Area.id`/`type`/geometry) plus the list
of per-tick frames (`TOTAL_TICKS + 1` of them, including the initial state).
`load`/`load_map`/`load_frame` reconstruct `Map`/`GameState` objects from
that JSON for replay — note `load_frame` needs the loaded `Map` to build a
full `GameState` since frames don't repeat static map data. `load_frame` reads
`cooldown` via `r.get("cooldown", 0)` so history files saved before this field
existed still load correctly (robots default to "free").

## Display (`display.py`)

`draw_state` color-codes areas by `Area.type` (dicts keyed `0`/`1`/`2`),
draws boxes as oriented rectangles via `game._box_corners`, and renders
robots as circles with a facing-direction indicator and held-box count badge.
`handle_events` is guarded with `if not pygame.display.get_init(): return
True` so it's safe to call even when no window has been opened (e.g. in
headless tests) — it both pumps the event queue (required so the OS doesn't
flag the window as unresponsive) and detects the close button / Escape key.

## Testing changes

There's no formal test suite; the convention used while building this engine
was headless smoke-testing via `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
.venv/bin/python -c "..."` — runs full games and exercises `display`/`history`
without opening a real window. Useful for verifying refactors didn't change
behavior (compare scores / outputs before and after).

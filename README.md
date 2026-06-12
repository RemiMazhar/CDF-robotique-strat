# Robotics French Cup Strategy Simultor

A 2-player game simulating the 2026 Robotics French Cup, to be played by python agents.
Two circular robots compete on a rectangular map to collect, recolor, and
deposit "boxes" for points. This repo contains the game engine, the agent
interface, a pygame visualizer, and a history-recording/replay system.

**Where to find things:**

- **Writing agents, running games, the rules, the interface, configuration:**
  see [`Robot Strategy Game - Agent Guide.pdf`](<Robot Strategy Game - Agent Guide.pdf>) —
  it has everything you need as an agent author, and is the canonical reference
  (this README intentionally doesn't repeat it).
- **Editing the engine itself:** see [`engine/README.md`](engine/README.md) for
  implementation details (data structures, collision algorithms, import
  wiring, etc.).

## File map

The layout is split so that what you actually touch day to day — agents,
agent selection, and the launcher — lives at the top level, while the game
engine internals (and the scripts that drive them) live out of the way in
`engine/`.

| File | Purpose |
|---|---|
| `agents/` | Agent implementations: `idle_agent` (does nothing), `random_agent` (random valid actions), `simple_agent` (a basic but functional strategy — the default in `agents_config.py`). Write your own modules here. |
| `agents_config.py` | Which agent module plays player 0 / player 1 |
| `play.py` | **Launcher — run this.** `python play.py run [...]` / `python play.py view <file>`. Sets up the virtual environment for you on first run (see "Setup" below) and uses it automatically — no activation needed. |
| `requirements.txt` | Dependencies installed into `.venv` on first run (currently just `pygame`). |
| `saved_games/` | Recorded game histories (`--save`/`view`), created automatically. |
| `Robot Strategy Game - Agent Guide.pdf` | The full agent-author guide — rules, tutorial, interface & configuration reference. |
| `engine/` | Engine internals — not needed for writing agents; see `engine/README.md`. |

## Setup

There's nothing to install by hand. The first time you run `play.py`, it
notices there's no `.venv` yet, creates one, and installs the dependencies
listed in `requirements.txt` into it automatically:

```bash
python play.py run
# No virtual environment found — setting one up at .venv (this happens once)...
# ... pip output ...
# Setup complete.
#
# Game start  —  1200 ticks  (120.0 s)
# ...
```

This takes a little while the first time and needs an internet connection; 
every run after that reuses the existing `.venv` and starts immediately.

## Running

```bash
python play.py run                  # run a game, print progress + final score
python play.py run --quiet          # suppress per-tick error logging
python play.py run --save           # also save a timestamped game to saved_games/
python play.py run --save --view    # run, save, then immediately replay it
python play.py run --random-colors  # randomize each box's starting color
python play.py view <history.json>  # replay a game from saved_games/ (or any path)
```

See the agent guide PDF for the full walkthrough: choosing which agent
plays, writing your own agent, visualizing and replaying games, and the
complete interface/configuration reference.

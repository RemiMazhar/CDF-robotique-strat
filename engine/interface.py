"""
Agent interface — the only module agents should import.

Before each make_decision() call the game engine sets _context to a fresh
_Context object.  Agents call the free functions below; the context is
invisible to them.

One action rule
---------------
Each call to make_decision() may invoke exactly ONE action function
(move, rotate, pickup, set_color, lay_down).  Calling a second action
raises ActionError.  Calling information functions (me, get_position, …)
is always free.

Cooldown
--------
move, pickup, set_color and lay_down each put the robot on a cooldown of
config.<ACTION>_COOLDOWN turns (including the turn the action is performed
on).  While get_cooldown(player) > 0, calling ANY of the five action
functions — including rotate — raises GameError.  rotate itself never
starts a cooldown.

A failed action (GameError) does NOT consume the turn, so agents can
safely do pre-checks and fall back gracefully.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import game as _game
from game import (
    Box, Map, Area, GameState, GameError,
    is_box_accessible, compute_scores,
    _circle_rect_distance, _normalize, is_move_colliding, _longest_move,
    do_move, do_rotate, do_pickup, do_set_color, do_lay_down,
)

if TYPE_CHECKING:
    pass


# ── Context (set by game engine, invisible to agents) ─────────────────────────

class ActionError(Exception):
    """Raised when an agent tries to take more than one action per turn. (note that rotating does not count as an action)"""


class _Context:
    __slots__ = ("game", "player_id", "action_taken")

    def __init__(self, game: GameState, player_id: int) -> None:
        self.game         = game
        self.player_id    = player_id
        self.action_taken = False

    def require_action_available(self) -> None:
        if self.action_taken:
            raise ActionError("Only one action is allowed per turn")

    def mark_action_taken(self) -> None:
        self.action_taken = True


_context: Optional[_Context] = None


def _ctx() -> _Context:
    if _context is None:
        raise RuntimeError("Interface functions must be called from inside make_decision()")
    return _context


# ── Information functions ─────────────────────────────────────────────────────
# Convention: when a function takes both a player and an id, player comes first.

def me() -> int:
    """Return this agent's player index (0 or 1)."""
    return _ctx().player_id


def opponent() -> int:
    """Return the index of the other player (1 - me())."""
    return 1 - _ctx().player_id


def get_position(player: int) -> Tuple[float, float]:
    """Return the (x, y) centre position of player's robot."""
    return _ctx().game.robots[player].position


def get_orientation(player: int) -> Tuple[float, float]:
    """Return the unit vector the robot of player is facing."""
    return _ctx().game.robots[player].orientation


def get_map() -> Map:
    """Return the Map object describing map dimensions and all areas."""
    return _ctx().game.map


def get_area_containing(position: Tuple[float, float]) -> Optional[Area]:
    """Return the Area that contains position, or None if it is in no area."""
    for area in _ctx().game.map.areas:
        if area.contains(position):
            return area
    return None


def get_area(area_id: int) -> Optional[Area]:
    """Return the Area with the given id, or None if it does not exist."""
    return _ctx().game.get_area(area_id)


def get_area_center(area_id: int) -> Tuple[float, float]:
    """Return the (x, y) centre position of the area with the given id."""
    area = _ctx().game.get_area(area_id)
    if area is None:
        raise GameError(f"No area with id {area_id}")
    return (area.x + area.width / 2, area.y + area.height / 2)


def get_boxes() -> List[Box]:
    """Return all Box objects in the game (on ground and held)."""
    return list(_ctx().game.boxes)


def get_box(box_id: int) -> Optional[Box]:
    """Return the Box with the given id, or None if it does not exist."""
    return _ctx().game.get_box(box_id)


def get_accessible_boxes(player: int) -> List[Box]:
    """Return all boxes currently within reach of player (on the ground)."""
    g = _ctx().game
    return [b for b in g.boxes if is_box_accessible(g, player, b.id)]


def get_boxes_held(player: int) -> List[Box]:
    """Return the list of Box objects currently held by player."""
    g = _ctx().game
    return [g.get_box(bid) for bid in g.robots[player].held_boxes]


def get_cooldown(player: int) -> int:
    """Return the number of remaining turns before player's robot can act
    again (0 = free now). Calling move/rotate/pickup/set_color/lay_down
    while this is > 0 raises GameError."""
    return _ctx().game.robots[player].cooldown


def is_accessible(player: int, box_id: int) -> bool:
    """Return True if box box_id is on the ground and within reach of player."""
    return is_box_accessible(_ctx().game, player, box_id)


def is_colliding(player: int, amount: float) -> bool:
    """Return True if moving player's robot forward by amount would collide
    with the map edge, the other robot, or a laid-down box."""
    return is_move_colliding(_ctx().game, player, amount)


def get_obstacle_distance(player: int) -> float:
    """Return the distance from player's robot to the nearest obstacle (map
    edge, the other robot, or a laid-down box) along its current orientation,
    i.e. how far it could move forward before colliding -- NOT capped at
    config.MAX_MOVE_SPEED. May be float('inf') if nothing is in the way."""
    return _longest_move(_ctx().game, player)


def get_box_distance(player: int, box_id: int) -> float:
    """Return the minimum distance from player's robot centre to box box_id
    (circle-to-rectangle distance, same metric used for accessibility checks)."""
    g   = _ctx().game
    box = g.get_box(box_id)
    if box is None:
        raise GameError(f"No box with id {box_id}")
    return _circle_rect_distance(
        g.robots[player].position,
        box.position, box.orientation,
        _game.config.BOX_WIDTH / 2, _game.config.BOX_HEIGHT / 2,
    )


def get_box_direction(player: int, box_id: int) -> Tuple[float, float]:
    """Return a unit vector pointing from player's robot centre toward box box_id's centre."""
    g   = _ctx().game
    box = g.get_box(box_id)
    if box is None:
        raise GameError(f"No box with id {box_id}")
    rx, ry = g.robots[player].position
    bx, by = box.position
    return _normalize((bx - rx, by - ry))


def get_area_distance(player: int, area_id: int) -> float:
    """Return the shortest distance from player's robot centre to the area
    with the given area_id (0 if the robot is already inside the area)."""
    g    = _ctx().game
    area = g.get_area(area_id)
    if area is None:
        raise GameError(f"No area with id {area_id}")
    return _circle_rect_distance(
        g.robots[player].position,
        get_area_center(area_id), (1.0, 0.0),
        area.width / 2, area.height / 2,
    )


def get_area_direction(player: int, area_id: int) -> Tuple[float, float]:
    """Return a unit vector pointing from player's robot centre toward area area_id's centre."""
    g      = _ctx().game
    area   = g.get_area(area_id)
    if area is None:
        raise GameError(f"No area with id {area_id}")
    rx, ry = g.robots[player].position
    ax, ay = get_area_center(area_id)
    return _normalize((ax - rx, ay - ry))


def get_score(player: int) -> int:
    """Return the score player would have if the game ended right now."""
    return compute_scores(_ctx().game)[player]


# ── Action functions ──────────────────────────────────────────────────────────
# Each (except rotate, which is free) consumes the agent's turn for this tick.
# If the game rejects the action (GameError) the turn is NOT consumed, so the
# agent can try a different action.  Two successful action calls per turn
# raise ActionError.
#
# All five functions below (including rotate) raise GameError if
# get_cooldown(player) > 0 — see the "Cooldown" section in the module
# docstring.  move/pickup/set_color/lay_down additionally start a new
# cooldown on success; rotate never does.

def move(amount: float) -> None:
    """Move forward by amount distance (must be >= 0, capped at MAX_MOVE_SPEED).
    Stops before any collision. Starts a cooldown of config.MOVE_COOLDOWN turns.

    Raises GameError if amount is negative — backward movement is not allowed."""
    ctx = _ctx()
    ctx.require_action_available()
    do_move(ctx.game, ctx.player_id, amount)
    ctx.mark_action_taken()


def rotate(new_direction: Tuple[float, float]) -> None:
    """Rotate to face new_direction (automatically normalised).

    Does not consume the turn (does not count as the one action per
    make_decision()) and does not itself start a cooldown. However, if the
    robot is currently on cooldown from a previous move/pickup/set_color/
    lay_down, this raises GameError (and, like any GameError, does not
    consume the turn either) — check get_cooldown(me()) first if you want to
    avoid the exception."""
    ctx = _ctx()
    do_rotate(ctx.game, ctx.player_id, new_direction)


def pickup(box_id: int) -> None:
    """Pick up the accessible box with the given id.
    Raises GameError if not accessible or hands are full.
    Starts a cooldown of config.PICKUP_COOLDOWN turns on success."""
    ctx = _ctx()
    ctx.require_action_available()
    do_pickup(ctx.game, ctx.player_id, box_id)
    ctx.mark_action_taken()


def set_color(box_id: int, color: int) -> None:
    """Change the color of an accessible box to color (0 or 1).
    Raises GameError if not accessible.
    Starts a cooldown of config.SET_COLOR_COOLDOWN turns on success."""
    ctx = _ctx()
    ctx.require_action_available()
    do_set_color(ctx.game, ctx.player_id, box_id, color)
    ctx.mark_action_taken()


def lay_down(box_id: int) -> None:
    """Place a held box directly in front of the robot.
    Raises GameError if the target position is blocked or out of map.
    Starts a cooldown of config.LAY_DOWN_COOLDOWN turns on success."""
    ctx = _ctx()
    ctx.require_action_available()
    do_lay_down(ctx.game, ctx.player_id, box_id)
    ctx.mark_action_taken()

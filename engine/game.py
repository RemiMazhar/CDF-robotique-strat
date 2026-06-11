"""Core game engine. Agents should not import this directly; use interface.py."""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import config


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Area:
    id: int   # unique per-area index (assigned sequentially at map load)
    type: int      # 0 = player0, 1 = player1, 2 = scoring
    x: float
    y: float
    width: float
    height: float

    def contains(self, point: Tuple[float, float]) -> bool:
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
    


@dataclass
class Map:
    width: float
    height: float
    areas: List[Area]


@dataclass
class Box:
    id: int
    position: Tuple[float, float]      # center (x, y)
    orientation: Tuple[float, float]   # unit vector along box width-axis
    color: int                          # 0 or 1
    owner: int                          # -1 if on ground, 0 or 1 if held by that player


@dataclass
class Robot:
    player: int
    position: Tuple[float, float]
    orientation: Tuple[float, float]   # unit vector the robot is facing
    held_boxes: List[int] = field(default_factory=list)
    cooldown: int = 0   # turns remaining until next action allowed (0 = free)


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _normalize(v: Tuple[float, float]) -> Tuple[float, float]:
    x, y = v
    mag = math.hypot(x, y)
    if mag < 1e-12:
        return (1.0, 0.0)
    return (x / mag, y / mag)


def _dot(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _box_corners(center: Tuple[float, float],
                 orient: Tuple[float, float],
                 half_w: float,
                 half_h: float) -> List[Tuple[float, float]]:
    """Return the four corners of an oriented rectangle."""
    cx, cy = center
    # Width-axis component
    wx, wy = orient[0] * half_w, orient[1] * half_w
    # Height-axis component (90° CCW from width axis)
    hx, hy = -orient[1] * half_h, orient[0] * half_h
    return [
        (cx + wx + hx, cy + wy + hy),
        (cx + wx - hx, cy + wy - hy),
        (cx - wx + hx, cy - wy + hy),
        (cx - wx - hx, cy - wy - hy),
    ]


def _circle_rect_distance(circle: Tuple[float, float],
                           rect_center: Tuple[float, float],
                           rect_orient: Tuple[float, float],
                           half_w: float,
                           half_h: float) -> float:
    """Minimum distance from a point to the nearest point on an oriented rectangle."""
    dx = circle[0] - rect_center[0]
    dy = circle[1] - rect_center[1]
    cos_a, sin_a = rect_orient
    # Transform to rectangle-local space (rect_orient = local x-axis)
    local_x =  dx * cos_a + dy * sin_a
    local_y = -dx * sin_a + dy * cos_a
    # Nearest point on rectangle in local space
    nx = max(-half_w, min(half_w, local_x))
    ny = max(-half_h, min(half_h, local_y))
    return math.hypot(local_x - nx, local_y - ny)


def _circle_rect_collides(circle: Tuple[float, float],
                           radius: float,
                           rect_center: Tuple[float, float],
                           rect_orient: Tuple[float, float],
                           half_w: float,
                           half_h: float) -> bool:
    return _circle_rect_distance(circle, rect_center, rect_orient, half_w, half_h) < radius


def _obb_obb_collides(ca, oa, hw_a, hh_a,
                      cb, ob, hw_b, hh_b) -> bool:
    """Separating Axis Theorem test for two oriented bounding boxes.
    Returns True if they overlap (touching edges are NOT considered overlapping)."""
    corners_a = _box_corners(ca, oa, hw_a, hh_a)
    corners_b = _box_corners(cb, ob, hw_b, hh_b)
    # Test each box's own axes
    axes = [oa, (-oa[1], oa[0]), ob, (-ob[1], ob[0])]
    for axis in axes:
        proj_a = [_dot(c, axis) for c in corners_a]
        proj_b = [_dot(c, axis) for c in corners_b]
        if max(proj_a) <= min(proj_b) or max(proj_b) <= min(proj_a):
            return False   # separating axis found
    return True


def _circle_in_map(pos: Tuple[float, float], radius: float,
                   w: float, h: float) -> bool:
    x, y = pos
    return radius <= x <= w - radius and radius <= y <= h - radius


def _angle_to_vec(angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    return (math.cos(rad), math.sin(rad))


# ── Game state ────────────────────────────────────────────────────────────────

def _build_map() -> Map:
    areas: List[Area] = []
    next_id = 0
    ax, ay, aw, ah = config.PLAYER0_AREA
    areas.append(Area(next_id, 0, ax, ay, aw, ah)); next_id += 1
    ax, ay, aw, ah = config.PLAYER1_AREA
    areas.append(Area(next_id, 1, ax, ay, aw, ah)); next_id += 1
    for sx, sy, sw, sh in config.SCORING_AREAS:
        areas.append(Area(next_id, 2, sx, sy, sw, sh)); next_id += 1
    return Map(width=config.MAP_WIDTH, height=config.MAP_HEIGHT, areas=areas)


def _build_boxes() -> List[Box]:
    boxes = []
    for i, (x, y, angle, color) in enumerate(config.INITIAL_BOXES):
        orient = _angle_to_vec(angle)
        boxes.append(Box(id=i, position=(x, y), orientation=orient, color=color, owner=-1))
    return boxes


class GameState:
    def __init__(self) -> None:
        self.map    = _build_map()
        self.robots = [
            Robot(0, config.PLAYER0_START, _angle_to_vec(config.PLAYER0_START_ANGLE)),
            Robot(1, config.PLAYER1_START, _angle_to_vec(config.PLAYER1_START_ANGLE)),
        ]
        self.boxes = _build_boxes()
        self.tick   = 0

    def get_box(self, box_id: int) -> Optional[Box]:
        for box in self.boxes:
            if box.id == box_id:
                return box
        return None
    
    def get_area(self, area_id: int) -> Optional[Area]:
        for area in self.map.areas:
            if area.id == area_id:
                return area
        return None

    def laid_down_boxes(self) -> List[Box]:
        return [b for b in self.boxes if b.owner == -1]

# ── Public helpers (used by interface.py) ─────────────────────────────────────

def is_box_accessible(game: GameState, player: int, box_id: int) -> bool:
    """True if the box is on the ground and within the player's accessibility radius."""
    box = game.get_box(box_id)
    if box is None or box.owner != -1:
        return False
    robot = game.robots[player]
    dist = _circle_rect_distance(
        robot.position, box.position, box.orientation,
        config.BOX_WIDTH / 2, config.BOX_HEIGHT / 2,
    )
    return dist <= config.ACCESSIBILITY_RADIUS

def is_move_colliding(game: GameState, player: int, amount: float) -> bool:
    robot  = game.robots[player]
    other  = game.robots[1 - player]
    sign   = 1.0 if amount >= 0.0 else -1.0
    target = min(abs(amount), config.MAX_MOVE_SPEED)

    hw = config.BOX_WIDTH  / 2
    hh = config.BOX_HEIGHT / 2
    laid = game.laid_down_boxes()
    ox, oy = robot.orientation

    nx = robot.position[0] + ox * amount
    ny = robot.position[1] + oy * amount
    p  = (nx, ny)
    if not _circle_in_map(p, config.ROBOT_RADIUS, game.map.width, game.map.height):
        return True
    if math.hypot(nx - other.position[0], ny - other.position[1]) < 2 * config.ROBOT_RADIUS:
        return True
    for box in laid:
        if _circle_rect_collides(p, config.ROBOT_RADIUS, box.position, box.orientation, hw, hh):
            return True
    return False

# ── Actions ───────────────────────────────────────────────────────────────────

class GameError(Exception):
    """Raised when a requested action is invalid."""


def _require_not_busy(robot: Robot) -> None:
    """Raise GameError if the robot is still on cooldown from a previous action."""
    if robot.cooldown > 0:
        raise GameError(
            f"Player {robot.player}'s robot is busy for {robot.cooldown} more tick(s)"
        )


def do_move(game: GameState, player: int, amount: float) -> None:
    """Move the robot up to |amount| distance (capped at MAX_MOVE_SPEED).
    Stops just before the first collision with the map edge, the other robot,
    or any laid-down box.

    Raises GameError if the robot is still on cooldown from a previous action.
    On success (including a 0-distance move due to immediate collision),
    starts a new cooldown of config.MOVE_COOLDOWN turns."""
    robot  = game.robots[player]
    _require_not_busy(robot)
    other  = game.robots[1 - player]
    sign   = 1.0 if amount >= 0.0 else -1.0
    target = min(abs(amount), config.MAX_MOVE_SPEED)

    hw = config.BOX_WIDTH  / 2
    hh = config.BOX_HEIGHT / 2
    laid = game.laid_down_boxes()
    ox, oy = robot.orientation

    def collides(dist: float) -> bool:
        nx = robot.position[0] + ox * dist
        ny = robot.position[1] + oy * dist
        p  = (nx, ny)
        if not _circle_in_map(p, config.ROBOT_RADIUS, game.map.width, game.map.height):
            return True
        if math.hypot(nx - other.position[0], ny - other.position[1]) < 2 * config.ROBOT_RADIUS:
            return True
        for box in laid:
            if _circle_rect_collides(p, config.ROBOT_RADIUS, box.position, box.orientation, hw, hh):
                return True
        return False

    # Fast path: no collision at full distance
    if not collides(sign * target):
        actual = sign * target
    else:
        # Binary search for maximum safe distance
        lo, hi = 0.0, target
        for _ in range(config.COLLISION_STEPS):
            mid = (lo + hi) / 2.0
            if collides(sign * mid):
                hi = mid
            else:
                lo = mid
        actual = sign * lo

    robot.position = (
        robot.position[0] + ox * actual,
        robot.position[1] + oy * actual,
    )
    robot.cooldown = config.MOVE_COOLDOWN


def do_rotate(game: GameState, player: int, new_direction: Tuple[float, float]) -> None:
    """Rotate the robot to face new_direction (normalised automatically).

    Raises GameError if the robot is still on cooldown from a previous action
    (a robot frozen by move/pickup/set_color/lay_down cannot rotate either).
    Does not itself start a cooldown."""
    robot = game.robots[player]
    _require_not_busy(robot)
    robot.orientation = _normalize(new_direction)


def do_pickup(game: GameState, player: int, box_id: int) -> None:
    robot = game.robots[player]
    _require_not_busy(robot)
    if len(robot.held_boxes) >= config.MAX_BOXES_HELD:
        raise GameError(f"Player {player} cannot hold more than {config.MAX_BOXES_HELD} boxes")
    if not is_box_accessible(game, player, box_id):
        raise GameError(f"Box {box_id} is not accessible by player {player}")
    box = game.get_box(box_id)
    box.owner = player
    robot.held_boxes.append(box_id)
    robot.cooldown = config.PICKUP_COOLDOWN


def do_set_color(game: GameState, player: int, box_id: int, color: int) -> None:
    robot = game.robots[player]
    _require_not_busy(robot)
    if color not in (0, 1):
        raise GameError("Color must be 0 or 1")
    if not is_box_accessible(game, player, box_id):
        raise GameError(f"Box {box_id} is not accessible by player {player}")
    game.get_box(box_id).color = color
    robot.cooldown = config.SET_COLOR_COOLDOWN


def do_lay_down(game: GameState, player: int, box_id: int) -> None:
    """Place a held box directly in front of the robot.
    Raises GameError if the robot is busy, the target position is out of
    bounds, or it overlaps another box."""
    robot = game.robots[player]
    _require_not_busy(robot)
    if box_id not in robot.held_boxes:
        raise GameError(f"Player {player} is not holding box {box_id}")

    ox, oy = robot.orientation
    tx = robot.position[0] + ox * config.LAY_DOWN_DISTANCE
    ty = robot.position[1] + oy * config.LAY_DOWN_DISTANCE
    target_pos    = (tx, ty)
    target_orient = robot.orientation

    hw = config.BOX_WIDTH  / 2
    hh = config.BOX_HEIGHT / 2

    # Verify all corners are inside the map
    for cx, cy in _box_corners(target_pos, target_orient, hw, hh):
        if not (0.0 <= cx <= game.map.width and 0.0 <= cy <= game.map.height):
            raise GameError("Cannot lay down box: target position is outside the map")

    # Verify no overlap with other laid-down boxes
    for other in game.laid_down_boxes():
        if _obb_obb_collides(target_pos, target_orient, hw, hh,
                              other.position, other.orientation, hw, hh):
            raise GameError(f"Cannot lay down box: would overlap box {other.id}")

    box = game.get_box(box_id)
    box.position    = target_pos
    box.orientation = target_orient
    box.owner       = -1
    robot.held_boxes.remove(box_id)
    robot.cooldown  = config.LAY_DOWN_COOLDOWN


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(game: GameState) -> Tuple[int, int]:
    """Count final points. Held boxes do not score."""
    scores = [0, 0]
    for box in game.boxes:
        if box.owner != -1:
            continue
        for area in game.map.areas:
            if area.contains(box.position):
                if area.type == 0:
                    scores[0] += config.POINTS_OWN_AREA
                elif area.type == 1:
                    scores[1] += config.POINTS_OWN_AREA
                elif area.type == 2:
                    scores[box.color] += config.POINTS_SCORING_AREA
                break  # areas are non-overlapping
    return (scores[0], scores[1])

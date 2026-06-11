# ── Map ────────────────────────────────────────────────────────────────────────
MAP_WIDTH  = 1000.0
MAP_HEIGHT = 600.0

# ── Areas: (x, y, width, height) ───────────────────────────────────────────────
PLAYER0_AREA = (0.0, 200.0, 150.0, 200.0)
PLAYER1_AREA = (850.0, 200.0, 150.0, 200.0)
SCORING_AREAS = [
    (300.0, 100.0, 100.0, 100.0),
    (600.0, 400.0, 100.0, 100.0),
]

# ── Robot starting positions and orientations ───────────────────────────────────
PLAYER0_START       = (75.0, 300.0)
PLAYER0_START_ANGLE = 0.0    # degrees; 0 = facing +x

PLAYER1_START       = (925.0, 300.0)
PLAYER1_START_ANGLE = 180.0  # degrees; facing -x

# ── Robot physics ───────────────────────────────────────────────────────────────
ROBOT_RADIUS    = 20.0
MAX_MOVE_SPEED  = 10.0   # max |distance| per tick
MAX_BOXES_HELD  = 3

# ── Box dimensions ──────────────────────────────────────────────────────────────
BOX_WIDTH  = 40.0   # along orientation axis
BOX_HEIGHT = 25.0   # along perpendicular axis

# ── Interaction distances ───────────────────────────────────────────────────────
# Distance from robot center to nearest point on box (for pickup / set_color)
ACCESSIBILITY_RADIUS = 25.0
# Distance from robot center to placed box center (for lay_down)
LAY_DOWN_DISTANCE = 45.0

# ── Scoring ─────────────────────────────────────────────────────────────────────
POINTS_OWN_AREA     = 3   # per box in the owning player's area (any color)
POINTS_SCORING_AREA = 5   # per box in a scoring area, for matching color

# ── Timing ──────────────────────────────────────────────────────────────────────
DT            = 0.1      # seconds per tick (informational; game is turn-based)
GAME_DURATION = 120.0    # seconds
TOTAL_TICKS   = int(GAME_DURATION / DT)   # 1200

# ── Action costs (temporal) ─────────────────────────────────────────────────────
# Each *_COOLDOWN value is the TOTAL number of turns the robot is occupied by
# that action, INCLUDING the turn the action is performed on.
#   - A value of 1 means "no extra delay" (robot is free again next turn).
#   - A value of N > 1 means the robot is frozen for N-1 ADDITIONAL turns
#     after the one where the action succeeded (it cannot move, rotate,
#     pick up, recolor, or lay down during that time).
# Starting values for playtesting -- tune freely.
MOVE_COOLDOWN      = 1
PICKUP_COOLDOWN    = 10
SET_COLOR_COOLDOWN = 5
LAY_DOWN_COOLDOWN  = 10

# ── Initial boxes: (x, y, angle_degrees, initial_color) ────────────────────────
# angle_degrees: angle of the box's width-axis from +x direction
# color: 0 or 1
INITIAL_BOXES = [
    (200.0, 150.0,  0.0, 0),
    (200.0, 300.0,  0.0, 0),
    (200.0, 450.0,  0.0, 0),
    (350.0, 200.0, 45.0, 1),
    (350.0, 400.0, 45.0, 1),
    (500.0, 300.0,  0.0, 0),
    (650.0, 200.0, 45.0, 0),
    (650.0, 400.0, 45.0, 1),
    (800.0, 150.0,  0.0, 1),
    (800.0, 300.0,  0.0, 1),
    (800.0, 450.0,  0.0, 1),
]

# ── Collision precision ─────────────────────────────────────────────────────────
COLLISION_STEPS = 16   # binary-search iterations for movement collision

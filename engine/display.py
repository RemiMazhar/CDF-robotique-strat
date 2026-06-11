"""
Visualisation of a GameState using pygame.

Quick usage
-----------
    import display
    screen, clock = display.init_window()
    # inside a loop:
    display.draw_state(screen, state)
    pygame.display.flip()
    clock.tick(60)

Convenience wrapper (blocks until the window is closed):
    display.show(state)

See also display.handle_events() to detect quit / keypress.
"""

import math
import pygame
import config
from game import GameState, compute_scores

# ── Layout ────────────────────────────────────────────────────────────────────
_PADDING     = 20
_INFO_HEIGHT = 72    # pixels below the map for the HUD

# Scale so the map fits inside a 1400 × 900 budget (capped at 1:1)
_MAX_MAP_W = 1400 - 2 * _PADDING
_MAX_MAP_H = 900  - 2 * _PADDING - _INFO_HEIGHT
SCALE = min(1.0, _MAX_MAP_W / config.MAP_WIDTH, _MAX_MAP_H / config.MAP_HEIGHT)

MAP_DISPLAY_W = int(config.MAP_WIDTH  * SCALE)
MAP_DISPLAY_H = int(config.MAP_HEIGHT * SCALE)
WINDOW_W      = MAP_DISPLAY_W + 2 * _PADDING
WINDOW_H      = MAP_DISPLAY_H + 2 * _PADDING + _INFO_HEIGHT

# ── Colours ───────────────────────────────────────────────────────────────────
_C_WINDOW_BG     = ( 30,  30,  30)
_C_MAP_BG        = (215, 215, 205)
_C_MAP_BORDER     = ( 60,  60,  60)

_C_AREA = {
    0: (160, 200, 255),   # player0 — pale blue
    1: (255, 175, 175),   # player1 — pale red
    2: (255, 248, 130),   # scoring — pale yellow
}
_C_AREA_BORDER = {
    0: ( 40,  80, 200),
    1: (200,  40,  40),
    2: (180, 160,   0),
}
_C_AREA_LABEL = {
    0: ( 20,  60, 180),
    1: (180,  20,  20),
    2: (130, 110,   0),
}

_C_BOX_FILL    = {0: ( 50, 100, 230), 1: (220,  55,  55)}   # blue / red
_C_BOX_OUTLINE = (255, 255, 255)

_C_ROBOT_FILL    = {0: ( 20,  70, 200), 1: (190,  30,  30)}
_C_ROBOT_OUTLINE = (255, 255, 255)
_C_ROBOT_DIR     = (255, 255, 255)   # orientation line

_C_COOLDOWN_BG   = (255, 165,   0)   # cooldown badge background
_C_COOLDOWN_TEXT = ( 30,  30,  30)   # cooldown badge text

_C_HUD_BG   = ( 20,  20,  20)
_C_HUD_TEXT = (220, 220, 220)
_C_P0_TEXT  = ( 80, 140, 255)
_C_P1_TEXT  = (255,  80,  80)

# ── Geometry helpers (local, no dependency on game internals) ─────────────────

def _box_corners(cx, cy, ox, oy, half_w, half_h):
    """Four corners of an oriented rectangle in game coordinates."""
    wx, wy = ox * half_w, oy * half_w      # along width axis
    hx, hy = -oy * half_h, ox * half_h    # along height axis (90° CCW)
    return [
        (cx + wx + hx, cy + wy + hy),
        (cx + wx - hx, cy + wy - hy),
        (cx - wx - hx, cy - wy - hy),
        (cx - wx + hx, cy - wy + hy),
    ]


def _to_screen(gx, gy):
    """Convert game coordinates to screen pixel coordinates."""
    return (int(_PADDING + gx * SCALE), int(_PADDING + gy * SCALE))


def _r(game_radius):
    return max(1, int(game_radius * SCALE))


# ── Drawing primitives ────────────────────────────────────────────────────────

def _draw_area(surface, area):
    fill   = _C_AREA.get(area.type, (200, 200, 200))
    border = _C_AREA_BORDER.get(area.type, (100, 100, 100))
    sx, sy = _to_screen(area.x, area.y)
    sw     = max(1, int(area.width  * SCALE))
    sh     = max(1, int(area.height * SCALE))
    rect   = pygame.Rect(sx, sy, sw, sh)
    pygame.draw.rect(surface, fill,   rect)
    pygame.draw.rect(surface, border, rect, 2)


def _draw_area_label(surface, area, font_small):
    label_map = {0: "P0 zone", 1: "P1 zone", 2: "Score"}
    label  = label_map.get(area.type, "")
    color  = _C_AREA_LABEL.get(area.type, (80, 80, 80))
    cx     = area.x + area.width  / 2
    cy     = area.y + area.height / 2
    sx, sy = _to_screen(cx, cy)
    text   = font_small.render(label, True, color)
    rect   = text.get_rect(center=(sx, sy))
    surface.blit(text, rect)


def _draw_box(surface, box):
    hw = config.BOX_WIDTH  / 2
    hh = config.BOX_HEIGHT / 2
    cx, cy = box.position
    ox, oy = box.orientation
    corners_g = _box_corners(cx, cy, ox, oy, hw, hh)
    corners_s = [_to_screen(gx, gy) for gx, gy in corners_g]
    pygame.draw.polygon(surface, _C_BOX_FILL[box.color], corners_s)
    pygame.draw.polygon(surface, _C_BOX_OUTLINE, corners_s, 2)


def _draw_robot(surface, robot, game_state, font_small):
    sx, sy = _to_screen(*robot.position)
    radius = _r(config.ROBOT_RADIUS)

    # Body
    pygame.draw.circle(surface, _C_ROBOT_FILL[robot.player], (sx, sy), radius)
    pygame.draw.circle(surface, _C_ROBOT_OUTLINE, (sx, sy), radius, 2)

    # Orientation line (from centre to rim)
    ox, oy = robot.orientation
    ex = int(sx + ox * radius)
    ey = int(sy + oy * radius)
    pygame.draw.line(surface, _C_ROBOT_DIR, (sx, sy), (ex, ey), max(2, radius // 4))

    # Held-box indicators: small coloured squares above/below the robot
    held = robot.held_boxes
    if held:
        sq   = max(6, int(10 * SCALE))
        gap  = 3
        total_w = len(held) * sq + (len(held) - 1) * gap
        start_x = sx - total_w // 2
        indicator_y = sy - radius - sq - 5
        for i, bid in enumerate(held):
            box = game_state.get_box(bid)
            if box is None:
                continue
            ix = start_x + i * (sq + gap)
            pygame.draw.rect(surface, _C_BOX_FILL[box.color],
                             (ix, indicator_y, sq, sq))
            pygame.draw.rect(surface, _C_BOX_OUTLINE,
                             (ix, indicator_y, sq, sq), 1)

    # Cooldown badge: small circle with remaining-turns count, bottom-right
    if robot.cooldown > 0:
        badge_r = max(7, int(11 * SCALE))
        bx = sx + radius - badge_r // 2
        by = sy + radius - badge_r // 2
        pygame.draw.circle(surface, _C_COOLDOWN_BG, (bx, by), badge_r)
        pygame.draw.circle(surface, _C_ROBOT_OUTLINE, (bx, by), badge_r, 1)
        cd_text = font_small.render(str(robot.cooldown), True, _C_COOLDOWN_TEXT)
        cd_rect = cd_text.get_rect(center=(bx, by))
        surface.blit(cd_text, cd_rect)

    # Player label inside circle
    label = font_small.render(str(robot.player), True, _C_ROBOT_OUTLINE)
    lrect = label.get_rect(center=(sx, sy))
    surface.blit(label, lrect)


def _draw_hud(surface, state, font, font_small):
    """Draw the info bar below the map."""
    hud_y  = _PADDING + MAP_DISPLAY_H + _PADDING // 2
    hud_h  = _INFO_HEIGHT
    pygame.draw.rect(surface, _C_HUD_BG,
                     (0, hud_y - _PADDING // 2, WINDOW_W, hud_h + _PADDING))

    scores = compute_scores(state)
    p0_pts, p1_pts = scores
    total  = config.TOTAL_TICKS

    # Tick counter + progress bar
    tick_text = font.render(f"Tick {state.tick:5d} / {total}", True, _C_HUD_TEXT)
    surface.blit(tick_text, (_PADDING, hud_y))

    bar_x  = _PADDING + tick_text.get_width() + 12
    bar_w  = WINDOW_W - bar_x - _PADDING
    bar_h  = 14
    bar_y  = hud_y + (tick_text.get_height() - bar_h) // 2
    pygame.draw.rect(surface, (70, 70, 70), (bar_x, bar_y, bar_w, bar_h))
    fill_w = int(bar_w * min(state.tick, total) / max(total, 1))
    pygame.draw.rect(surface, (100, 180, 100), (bar_x, bar_y, fill_w, bar_h))
    pygame.draw.rect(surface, (150, 150, 150), (bar_x, bar_y, bar_w, bar_h), 1)

    # Scores
    p0_surf = font.render(
        f"Player 0: {p0_pts} pts  ({len(state.robots[0].held_boxes)} held)",
        True, _C_P0_TEXT)
    p1_surf = font.render(
        f"Player 1: {p1_pts} pts  ({len(state.robots[1].held_boxes)} held)",
        True, _C_P1_TEXT)
    score_y = hud_y + tick_text.get_height() + 6
    surface.blit(p0_surf, (_PADDING, score_y))
    surface.blit(p1_surf, (WINDOW_W // 2, score_y))


# ── Public API ────────────────────────────────────────────────────────────────

def init_window(title: str = "Robot Strategy Game"):
    """Initialise pygame and open the window.

    Returns (screen, clock).  Call pygame.quit() when done.
    """
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption(title)
    clock  = pygame.time.Clock()
    return screen, clock


def draw_state(screen: pygame.Surface, state: GameState) -> None:
    """Render one frame of game_state onto screen.

    Does NOT call pygame.display.flip() — the caller decides when to present.
    """
    # Lazily create fonts the first time (requires pygame.init() to have run)
    if not hasattr(draw_state, "_font"):
        draw_state._font       = pygame.font.SysFont("monospace", 18)
        draw_state._font_small = pygame.font.SysFont("monospace", 13)
    font       = draw_state._font
    font_small = draw_state._font_small

    screen.fill(_C_WINDOW_BG)

    # Map background
    pygame.draw.rect(screen, _C_MAP_BG,
                     (_PADDING, _PADDING, MAP_DISPLAY_W, MAP_DISPLAY_H))
    pygame.draw.rect(screen, _C_MAP_BORDER,
                     (_PADDING, _PADDING, MAP_DISPLAY_W, MAP_DISPLAY_H), 2)

    # Areas
    for area in state.map.areas:
        _draw_area(screen, area)
    for area in state.map.areas:
        _draw_area_label(screen, area, font_small)

    # Laid-down boxes
    for box in state.boxes:
        if box.owner == -1:
            _draw_box(screen, box)

    # Robots (drawn on top of boxes)
    for robot in state.robots:
        _draw_robot(screen, robot, state, font_small)

    # HUD
    _draw_hud(screen, state, font, font_small)


def handle_events() -> bool:
    """Process pygame events.  Returns False if the window was closed.
    Safe to call even when no window has been opened (returns True immediately)."""
    if not pygame.display.get_init():
        return True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
    return True


def show(state: GameState, fps: int = 60) -> None:
    """Open a window, display state, and block until the window is closed."""
    screen, clock = init_window()
    running = True
    while running:
        running = handle_events()
        draw_state(screen, state)
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()
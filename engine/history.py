"""
Serialisation of game history to / from JSON.

A history file contains:
  - the static map description (saved once)
  - one frame per tick (initial state + state after every tick)

Usage
-----
    frames = []
    frames.append(history.snapshot(state))   # capture before / after each tick
    history.save(frames, state.map, "run.json")

    # later:
    data   = history.load("run.json")
    map_   = history.load_map(data)
    frame0 = history.load_frame(data, 0)     # returns a GameState
"""

import json
from typing import List

from game import GameState, Map, Area, Box, Robot


# ── Serialise ──────────────────────────────────────────────────────────────────

def snapshot(state: GameState) -> dict:
    """Return a plain-dict representation of the mutable part of state."""
    return {
        "tick": state.tick,
        "robots": [
            {
                "player":      r.player,
                "position":    list(r.position),
                "orientation": list(r.orientation),
                "held_boxes":  list(r.held_boxes),
                "cooldown":    r.cooldown,
            }
            for r in state.robots
        ],
        "boxes": [
            {
                "id":          b.id,
                "position":    list(b.position),
                "orientation": list(b.orientation),
                "color":       b.color,
                "owner":       b.owner,
            }
            for b in state.boxes
        ],
    }


def _map_to_dict(m: Map) -> dict:
    return {
        "width":  m.width,
        "height": m.height,
        "areas": [
            {"area_id": a.id, "type": a.type, "x": a.x, "y": a.y, "width": a.width, "height": a.height}
            for a in m.areas
        ],
    }


def save(frames: List[dict], game_map: Map, path: str) -> None:
    """Write history to *path* as compact JSON."""
    data = {
        "map":    _map_to_dict(game_map),
        "frames": frames,
    }
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))


# ── Deserialise ────────────────────────────────────────────────────────────────

def load(path: str) -> dict:
    """Read a history file and return the raw dict."""
    with open(path) as fh:
        return json.load(fh)


def load_map(data: dict) -> Map:
    m = data["map"]
    areas = [
        Area(a["area_id"], a["type"], a["x"], a["y"], a["width"], a["height"])
        for a in m["areas"]
    ]
    return Map(width=m["width"], height=m["height"], areas=areas)


def load_frame(data: dict, index: int) -> GameState:
    """Reconstruct a GameState from frame *index* in a loaded history dict.

    The returned state has the map from the file; config values are NOT re-read,
    so use it for display / analysis only, not for continuing a live game.
    """
    frame = data["frames"][index]
    state = GameState.__new__(GameState)   # skip __init__ (avoids re-reading config)
    state.map = load_map(data)
    state.tick = frame["tick"]
    state.robots = [
        Robot(
            player=r["player"],
            position=tuple(r["position"]),
            orientation=tuple(r["orientation"]),
            held_boxes=list(r["held_boxes"]),
            cooldown=r.get("cooldown", 0),
        )
        for r in frame["robots"]
    ]
    state.boxes = [
        Box(
            id=b["id"],
            position=tuple(b["position"]),
            orientation=tuple(b["orientation"]),
            color=b["color"],
            owner=b["owner"],
        )
        for b in frame["boxes"]
    ]
    return state

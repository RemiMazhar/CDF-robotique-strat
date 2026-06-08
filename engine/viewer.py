"""Replays a saved history file. Normally launched via `play.py view <file>`
at the project root, which also takes care of using the project's virtual
environment."""

import sys

import history
import display
import pygame

def view_past_game(fn):
    data   = history.load(fn)
    map_   = history.load_map(data)

    screen, clock = display.init_window()
    for i in range(len(data["frames"])):
        if not display.handle_events():
            break
        display.draw_state(screen, history.load_frame(data, i))
        pygame.display.flip()
        clock.tick(10)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: play view <history_file.json>")
    view_past_game(sys.argv[1])

"""Agent that takes random actions every turn."""

import math
import random

import config
import interface


class Agent:
    def __init__(self):
        pass
    
    def make_decision(self):
        player     = interface.me()
        held       = interface.get_boxes_held(player)
        accessible = interface.get_accessible_boxes(player)

        # Build the menu of currently valid actions
        choices = ["move", "rotate"]

        if accessible and len(held) < config.MAX_BOXES_HELD:
            choices.append("pickup")

        if accessible:
            choices.append("set_color")

        if held:
            choices.append("lay_down")

        action = random.choice(choices)

        if action == "move":
            amount = random.uniform(0.0, config.MAX_MOVE_SPEED)
            interface.move(amount)

        elif action == "rotate":
            angle = random.uniform(0.0, 2.0 * math.pi)
            interface.rotate((math.cos(angle), math.sin(angle)))

        elif action == "pickup":
            target = random.choice(accessible)
            interface.pickup(target.id)

        elif action == "set_color":
            target = random.choice(accessible)
            interface.set_color(target.id, player)   # paint to own color

        elif action == "lay_down":
            # lay_down may fail if the spot ahead is blocked; that's fine,
            # the turn is not consumed and the exception propagates to main.py
            interface.lay_down(held[0].id)

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
        areas = interface.get_map().areas
        boxes = interface.get_boxes()
        orientation = interface.get_orientation(player)
        position = interface.get_position(player)

        if random.random() < 0.1:
            angle = random.random() * math.pi * 2
            interface.rotate((math.cos(angle), math.sin(angle)))
            interface.move(config.MAX_MOVE_SPEED)
            return


        if held:
            good_areas = []

            for area in interface.get_map().areas:
                if area.type == player or area.type == 2:
                    good_areas.append((interface.get_area_distance(player, area.id) * (2 if area.type == player else 1), area))

            for d, area in sorted(good_areas):
                direction = interface.get_area_direction(player, area.id)
                interface.rotate(direction)

                if d == 0:
                    try:
                        interface.lay_down(held[0].id)
                        return
                    except:
                        angle = random.random() * math.pi * 2
                        interface.rotate((math.cos(angle), math.sin(angle)))
                        interface.move(config.MAX_MOVE_SPEED)
                        return

                if interface.is_colliding(player, config.MAX_MOVE_SPEED):
                    continue

                interface.move(config.MAX_MOVE_SPEED)
                return

        boxes = sorted(boxes, key=lambda x : interface.get_box_distance(player, x.id))

        for box in boxes:
            area = interface.get_area_containing(box.position)
            zone = area.type if area is not None else -1

            if zone == player or (zone == 2 and box.color == player):
                continue

            accessible = interface.is_accessible(player, box.id)
            if accessible and box.color != player :
                interface.set_color(box.id, player)
                return

            if accessible:
                interface.pickup(box.id)
                return
            else:
                interface.rotate(interface.get_box_direction(player, box.id))
                interface.move(config.MAX_MOVE_SPEED)
                return
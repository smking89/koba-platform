"""Reusable mechanical animation primitives, driving rig empties created by
rigging/mechanical.py."""
import math

import bpy

from core.naming import name as make_name

_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}


def _iter_fcurves(action):
    """Blender 5.x's layered-Action model nests fcurves under
    layers -> strips -> channelbags instead of a flat action.fcurves."""
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in getattr(strip, "channelbags", ()):
                for fc in channelbag.fcurves:
                    yield fc


def animate_hinge_rotation(asset, hinge_empty, axis, angle_deg, part_name,
                            start_frame=1, end_frame=48, action_name=None):
    """Keyframe hinge_empty's rotation on `axis` from 0deg (closed) to
    angle_deg (open) between start_frame/end_frame. Registers the action
    name on the asset. Returns the action."""
    idx = _AXIS_INDEX[axis]
    hinge_empty.rotation_mode = "XYZ"

    rot = list(hinge_empty.rotation_euler)
    rot[idx] = 0.0
    hinge_empty.rotation_euler = rot
    hinge_empty.keyframe_insert(data_path="rotation_euler", index=idx, frame=start_frame)

    rot[idx] = math.radians(angle_deg)
    hinge_empty.rotation_euler = rot
    hinge_empty.keyframe_insert(data_path="rotation_euler", index=idx, frame=end_frame)

    action = hinge_empty.animation_data.action
    action.name = action_name or make_name("animation", asset.name, f"{part_name}Open")

    fcurve = next((fc for fc in _iter_fcurves(action) if fc.array_index == idx), None)
    if fcurve is not None:
        for kp in fcurve.keyframe_points:
            kp.interpolation = "SINE"

    asset.add_animation(action.name)
    return action


def animate_slider_translation(asset, slider_empty, axis, distance, part_name,
                                start_frame=1, end_frame=48, action_name=None):
    """Keyframe slider_empty's location on `axis`, offset by `distance`
    (meters) between start_frame/end_frame."""
    idx = _AXIS_INDEX[axis]
    start_loc = list(slider_empty.location)

    slider_empty.location = start_loc
    slider_empty.keyframe_insert(data_path="location", index=idx, frame=start_frame)

    end_loc = list(start_loc)
    end_loc[idx] += distance
    slider_empty.location = end_loc
    slider_empty.keyframe_insert(data_path="location", index=idx, frame=end_frame)

    action = slider_empty.animation_data.action
    action.name = action_name or make_name("animation", asset.name, f"{part_name}Slide")

    fcurve = next((fc for fc in _iter_fcurves(action) if fc.array_index == idx), None)
    if fcurve is not None:
        for kp in fcurve.keyframe_points:
            kp.interpolation = "SINE"

    asset.add_animation(action.name)
    return action

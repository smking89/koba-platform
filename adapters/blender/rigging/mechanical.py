"""Reusable mechanical rig primitives — hinges, sliders, follow points,
constraints. Kept generic (not door/crane-specific) so cranes, elevators,
vehicle doors, and gantries can all reuse the same building blocks per the
framework's naming/rig conventions."""
import bpy

from core import collections as collections_mod
from core.naming import name as make_name
from core.transforms import parent_keep_transform


def _new_rig_empty(asset, part_name, suffix, display_type, display_size, world_location):
    empty = bpy.data.objects.new(make_name("empty", asset.name, f"{part_name}{suffix}"), None)
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    empty.location = world_location
    bpy.context.scene.collection.objects.link(empty)
    collections_mod.link_only(empty, asset.collections["RIG"])
    return empty


def create_hinge(asset, part_name, objs, hinge_point, axis="Z"):
    """Create an Empty at `hinge_point` (world space) and parent `objs`
    (a single object or a list of them) to it, so rotating the Empty swings
    all of them around that point/axis together. Registers the rig on the
    asset. Returns the hinge Empty — parent IT to another hinge for nested
    DOFs (e.g. a boom pitch hinge nested inside a crane's slew hinge)."""
    if axis not in ("X", "Y", "Z"):
        raise ValueError(f"axis must be X/Y/Z, got {axis!r}")
    objs_list = list(objs) if isinstance(objs, (list, tuple)) else [objs]

    empty = _new_rig_empty(asset, part_name, "Hinge", "PLAIN_AXES", 0.2, hinge_point)
    for obj in objs_list:
        parent_keep_transform(obj, empty)

    asset.add_rig({"type": "hinge", "part": part_name, "empty": empty, "axis": axis})
    return empty


def create_slider(asset, part_name, obj, slide_axis="Z"):
    """Parent `obj` to a new Empty at obj's current location so translating
    the Empty slides obj along one axis (e.g. a sliding door, an elevator
    platform, a crane hook winch). Returns the slider Empty."""
    if slide_axis not in ("X", "Y", "Z"):
        raise ValueError(f"slide_axis must be X/Y/Z, got {slide_axis!r}")

    bpy.context.view_layer.update()  # matrix_world is stale right after .location is set — see core.transforms.parent_keep_transform
    world_loc = obj.matrix_world.translation.copy()
    empty = _new_rig_empty(asset, part_name, "Slider", "ARROWS", 0.15, world_loc)
    parent_keep_transform(obj, empty)

    asset.add_rig({"type": "slider", "part": part_name, "empty": empty, "axis": slide_axis})
    return empty


def create_follow_point(asset, part_name, parent_obj, world_location):
    """A plain Empty parented to parent_obj at a fixed world location (e.g.
    marking a boom's tip) — not a DOF itself, just a reference point other
    rig parts can track via a constraint (see add_copy_location_constraint)."""
    empty = _new_rig_empty(asset, part_name, "Point", "SPHERE", 0.06, world_location)
    parent_keep_transform(empty, parent_obj)
    return empty


def add_copy_location_constraint(obj, target, use_x=True, use_y=True, use_z=True, name=None):
    """Lock some axes of obj's world location to target while leaving the
    rest free for independent animation — e.g. a crane hook that must track
    the boom tip horizontally (X/Y) while its vertical winch drop (Z) is
    keyframed independently."""
    con = obj.constraints.new(type="COPY_LOCATION")
    con.target = target
    con.use_x, con.use_y, con.use_z = use_x, use_y, use_z
    if name:
        con.name = name
    return con

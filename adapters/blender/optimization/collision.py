"""Automatic collision generation. Box collision only for now — convex/compound
are documented as a later phase, not faked."""
import bpy
import mathutils

from core.naming import collision_name


def generate_box_collision(asset, part_name, source_objects):
    """Build one box collider that encloses all source_objects' world-space bounds."""
    bpy.context.view_layer.update()  # matrix_world can be stale right after a .location set — see core.transforms.parent_keep_transform
    mins = mathutils.Vector((float("inf"),) * 3)
    maxs = mathutils.Vector((float("-inf"),) * 3)
    for obj in source_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            mins = mathutils.Vector(min(a, b) for a, b in zip(mins, world_corner))
            maxs = mathutils.Vector(max(a, b) for a, b in zip(maxs, world_corner))

    size = maxs - mins
    center = (mins + maxs) / 2

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    col_obj = bpy.context.active_object
    col_obj.scale = size
    col_obj.name = collision_name(asset.name, part_name)
    col_obj.data.name = col_obj.name + "_mesh"
    col_obj.display_type = "WIRE"  # viewport-only
    col_obj.hide_render = True     # display_type doesn't affect actual renders — must set this too

    return asset.add_collision(col_obj)

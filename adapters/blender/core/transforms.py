"""Origin and transform management helpers."""
import bpy
import mathutils


def parent_keep_transform(obj, parent_obj):
    """Parent obj to parent_obj without obj jumping — used everywhere a rig
    Empty needs to take over an already-positioned mesh (or another Empty).

    Blender scripting gotcha: reading matrix_world immediately
    after setting .location on a freshly created/linked object returns a
    STALE identity matrix until the depsgraph is evaluated — confirmed by
    direct testing. Without the view_layer.update() below,
    matrix_parent_inverse silently becomes Identity instead of the correct
    inverse, and the object's position effectively doubles once Blender
    later evaluates the real transform (visually subtle for a single hinge,
    catastrophic for nested hinges — this is what broke the crane's boom)."""
    bpy.context.view_layer.update()
    obj.parent = parent_obj
    obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()


def apply_all_transforms(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def set_origin_to_point(obj, point):
    """Move obj's origin to a world-space point without moving the geometry."""
    prev_cursor = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = mathutils.Vector(point)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = prev_cursor


def set_origin_to_bounds_bottom(obj):
    """Common case: origin at the bottom-center of the bounding box (good for
    props/buildings that should sit flush on the ground)."""
    bpy.context.view_layer.update()  # matrix_world can be stale right after a .location set — see parent_keep_transform above
    bbox = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xs = [v.x for v in bbox]
    ys = [v.y for v in bbox]
    z_min = min(v.z for v in bbox)
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    set_origin_to_point(obj, (cx, cy, z_min))

"""Preview rendering: camera + light rig + render-to-PNG for visual QA."""
import math
import os

import bpy
import mathutils

from config.blender_config import PREVIEWS_DIR
from core.scene import new_camera, new_sun


def _bounds_of(objects):
    bpy.context.view_layer.update()  # matrix_world can be stale right after a .location set — see core.transforms.parent_keep_transform
    mins = mathutils.Vector((float("inf"),) * 3)
    maxs = mathutils.Vector((float("-inf"),) * 3)
    for obj in objects:
        for corner in obj.bound_box:
            wc = obj.matrix_world @ mathutils.Vector(corner)
            mins = mathutils.Vector(min(a, b) for a, b in zip(mins, wc))
            maxs = mathutils.Vector(max(a, b) for a, b in zip(maxs, wc))
    return mins, maxs


def render_preview(asset, filename=None, angle="three_quarter", resolution=(960, 720),
                    engine=None, samples=64):
    """engine=None (default) auto-picks EEVEE, as before. Pass engine="CYCLES"
    for materials that need real path-traced transmission/subsurface —
    EEVEE Next's transmission is screen-space only and renders thick/
    complex transmissive meshes (e.g. materials.candy.gummy_material on a
    solid prop) dark and muddy instead of properly see-through, confirmed
    by direct comparison against a Cycles render of the same asset."""
    objects = list(asset.geometry_objects)
    if not objects:
        raise ValueError("Asset has no geometry to preview")

    mins, maxs = _bounds_of(objects)
    center = (mins + maxs) / 2
    size = maxs - mins
    radius = max(size.x, size.y, size.z, 0.5) * 2.2

    angles = {
        "front": (0, -1, 0.4),
        "side": (1, 0, 0.4),
        "rear": (0, 1, 0.4),
        "three_quarter": (0.85, -0.85, 0.6),
        "top": (0.001, 0.001, 1.6),
    }
    dx, dy, dz = angles.get(angle, angles["three_quarter"])
    cam_loc = center + mathutils.Vector((dx, dy, dz)) * radius
    direction = center - cam_loc
    rot_quat = direction.to_track_quat("-Z", "Y")

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.05, 0.05, 0.06, 1.0)
        bg.inputs["Strength"].default_value = 0.3
    bpy.context.scene.world = world

    cam = new_camera(cam_loc, rot_quat.to_euler())
    bpy.context.scene.camera = cam
    new_sun(energy=1.5)
    fill = new_sun(name="LGT_Fill", energy=0.5, rotation_euler=(1.4, 0.0, -0.9))

    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = resolution
    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    else:
        scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
        scene.eevee.use_raytracing = True
    # AgX (Blender's default view transform) aggressively desaturates
    # overexposed diffuse surfaces toward gray, which makes preview
    # renders lie about an asset's actual material color. Previews are
    # for QA, not final look-dev, so use Standard for true color.
    scene.view_settings.view_transform = "Standard"

    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    filename = filename or f"{asset.name}_{angle}.png"
    out_path = os.path.join(PREVIEWS_DIR, filename)
    scene.render.filepath = out_path
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)

    return out_path

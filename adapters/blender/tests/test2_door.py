"""TEST 2: Industrial door.

First asset exercising rigging + animation: a hinged door panel that swings
open around a vertical Empty pivot.

Exercises: rigging.mechanical.create_hinge, animation.mechanical.animate_hinge_rotation,
plus everything test 1 already covered.

Run headless:
  <blender> -b --python tests/test2_door.py

Run live, staged (each call visible in the open GUI as it happens):
  python3 scripts/blender_client.py -c "from tests.test2_door import *; asset = stage_init(interactive=True)"
  python3 scripts/blender_client.py -c "stage_frame(asset)"
  python3 scripts/blender_client.py -c "stage_panel_and_handle(asset)"
  python3 scripts/blender_client.py -c "stage_collision(asset)"
  python3 scripts/blender_client.py -c "stage_rig(asset)"
  python3 scripts/blender_client.py -c "stage_animation(asset)"
  python3 scripts/blender_client.py -c "stage_finalize(asset, interactive=True)"
"""
import math
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms, set_origin_to_point  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.entity_metadata import for_mechanism  # noqa: E402
from geometry.primitives import create_box, create_cylinder  # noqa: E402
from materials.metal import painted_metal, galvanized_steel, bare_metal  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from rigging.mechanical import create_hinge  # noqa: E402
from animation.mechanical import animate_hinge_rotation  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

DEFAULT_PARAMS = dict(
    door_width=0.9,
    door_height=2.0,
    door_thickness=0.045,
    frame_thickness=0.08,
    frame_depth=0.12,
    hinge_open_deg=100,
)


def stage_init(interactive=False, **params):
    """STAGE 01 — scene init + asset + materials."""
    dims = {**DEFAULT_PARAMS, **params}
    prepare_scene("Door", interactive)
    asset = Asset(name="Door", asset_type="mechanism")
    asset.params = dims

    frame_mat = galvanized_steel(make_name("material", asset.name, "Frame"))
    panel_mat = painted_metal(make_name("material", asset.name, "Panel"), color=(0.15, 0.2, 0.24))
    handle_mat = bare_metal(make_name("material", asset.name, "Handle"))
    for mat in (frame_mat, panel_mat, handle_mat):
        asset.register_material(mat.name)
    asset.materials = {"frame": frame_mat, "panel": panel_mat, "handle": handle_mat}

    return asset


def stage_frame(asset):
    """STAGE 02 — primary geometry: door frame (two jambs + header)."""
    d = asset.params
    mat = asset.materials["frame"]
    jamb_height = d["door_height"] + d["frame_thickness"]

    left_jamb = create_box(make_name("mesh", asset.name, "JambLeft"),
                            width=d["frame_thickness"], depth=d["frame_depth"],
                            height=jamb_height, bevel_width=0.004, material=mat)
    left_jamb.location.x = -(d["door_width"] / 2 + d["frame_thickness"] / 2)
    apply_all_transforms(left_jamb)
    asset.add_geometry(left_jamb)

    right_jamb = create_box(make_name("mesh", asset.name, "JambRight"),
                             width=d["frame_thickness"], depth=d["frame_depth"],
                             height=jamb_height, bevel_width=0.004, material=mat)
    right_jamb.location.x = d["door_width"] / 2 + d["frame_thickness"] / 2
    apply_all_transforms(right_jamb)
    asset.add_geometry(right_jamb)

    header = create_box(make_name("mesh", asset.name, "Header"),
                         width=d["door_width"] + 2 * d["frame_thickness"], depth=d["frame_depth"],
                         height=d["frame_thickness"], bevel_width=0.004, material=mat)
    header.location.z = d["door_height"]
    apply_all_transforms(header)
    asset.add_geometry(header)

    return left_jamb, right_jamb, header


def stage_panel_and_handle(asset):
    """STAGE 03 — secondary geometry: door panel + handle."""
    d = asset.params

    panel = create_box(make_name("mesh", asset.name, "Panel"),
                        width=d["door_width"], depth=d["door_thickness"],
                        height=d["door_height"], bevel_width=0.003,
                        material=asset.materials["panel"])
    # Both the panel and handle rotate with the hinge (stage_rig, below) —
    # metadata says so explicitly rather than leaving the optimizer to guess
    # from geometry alone, so it never merges/instances them away.
    asset.add_geometry(panel, metadata=for_mechanism(category="door_panel"))
    asset.door_panel = panel

    handle = create_cylinder(make_name("mesh", asset.name, "Handle"),
                              radius=0.015, depth=0.12, vertices=12,
                              material=asset.materials["handle"])
    handle.rotation_euler = (math.radians(90), 0, 0)
    handle.location = (d["door_width"] / 2 - 0.08, -(d["door_thickness"] / 2 + 0.03), d["door_height"] * 0.5)
    apply_all_transforms(handle)
    asset.add_geometry(handle, metadata=for_mechanism(category="door_handle", collision_required=False))
    asset.door_handle = handle

    return panel, handle


def stage_collision(asset):
    """STAGE 04 — box collision enclosing the whole (closed) door assembly."""
    return generate_box_collision(asset, "Main", asset.geometry_objects)


def stage_rig(asset):
    """STAGE 05 — hinge rig: parent the door panel + handle to a pivot Empty
    on the door's hinge edge, then reparent the frame's collision awareness
    is left as-is (collision is generated from the closed pose, a documented
    limitation — see README)."""
    d = asset.params
    hinge_point = (-d["door_width"] / 2, 0.0, 0.0)

    hinge_empty = create_hinge(asset, "Panel", asset.door_panel, hinge_point, axis="Z")

    # The handle must swing with the panel — parent it to the same hinge.
    asset.door_handle.parent = hinge_empty
    asset.door_handle.matrix_parent_inverse = hinge_empty.matrix_world.inverted()

    asset.hinge_empty = hinge_empty
    return hinge_empty


def stage_animation(asset):
    """STAGE 06 — keyframe the door swinging open."""
    d = asset.params
    action = animate_hinge_rotation(
        asset, asset.hinge_empty, axis="Z", angle_deg=d["hinge_open_deg"],
        part_name="Panel", start_frame=1, end_frame=48,
    )
    return action


def stage_finalize(asset, interactive=False, preview_frame=48, save=True, export=True):
    """STAGE 07 — validate, preview, save, export."""
    result = validate_asset(asset, poly_budget=5000)
    print(result.report())

    if interactive:
        bpy.context.scene.frame_set(preview_frame)
        frame_objects(asset.geometry_objects)
    else:
        bpy.context.scene.frame_set(preview_frame)
        preview_path = render_preview(asset, angle="three_quarter")
        print(f"Preview rendered: {preview_path}")
        bpy.context.scene.frame_set(1)

    if save:
        asset.save_asset_properties()
        os.makedirs(GENERATED_DIR, exist_ok=True)
        blend_path = os.path.join(GENERATED_DIR, f"{asset.name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"Saved: {blend_path}")

    if export and not interactive:
        out = export_asset(asset, preset_name="fbx_generic", filename=f"{asset.name}.fbx")
        print(f"Exported: {out}")

    print("SUMMARY:", asset.summary())
    return result


def build_door(interactive=False, **params):
    asset = stage_init(interactive=interactive, **params)
    stage_frame(asset)
    stage_panel_and_handle(asset)
    stage_collision(asset)
    stage_rig(asset)
    stage_animation(asset)
    asset._last_validation = stage_finalize(asset, interactive=interactive)
    return asset


def main():
    asset = build_door(interactive=False)
    if not asset._last_validation.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

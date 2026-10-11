"""TEST 9: Procedural jet ski.

Exercises: core.asset, geometry.primitives.create_hull (reused from
test6_boat.py, narrower/sportier proportions), the new
materials.plastic.glossy_plastic, optimization.collision/.lod,
core.validation, core.preview, export.exporter.

Run with:
  <blender> -b --python tests/test9_jetski.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms, set_origin_to_bounds_bottom  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from geometry.primitives import create_hull, create_box, create_cylinder  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.metal import bare_metal  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR, PROJECT_ROOT as CFG_ROOT  # noqa: E402


def build_jetski(length=2.8, beam=0.9, draft=0.35, body_color=(0.85, 0.1, 0.15), interactive=False):
    prepare_scene("JetSki", interactive)
    asset = Asset(name="JetSki", asset_type="vehicle")

    body_mat = glossy_plastic(make_name("material", asset.name, "Body"), color=body_color)
    trim_mat = glossy_plastic(make_name("material", asset.name, "Trim"), color=(0.95, 0.95, 0.95), roughness=0.25)
    metal_mat = bare_metal(make_name("material", asset.name, "Nozzle"))
    asset.register_material(body_mat.name)
    asset.register_material(trim_mat.name)
    asset.register_material(metal_mat.name)

    hull = create_hull(
        make_name("mesh", asset.name, "Hull"),
        length=length, beam=beam, draft=draft, deck_height=draft * 0.7,
        sections=16, material=body_mat,
    )
    asset.add_geometry(hull)

    # Saddle seat: a raised, slightly tapered box running most of the
    # hull's length along the centerline.
    seat = create_box(
        make_name("mesh", asset.name, "Seat"),
        width=beam * 0.4, depth=length * 0.55, height=0.18,
        bevel_width=0.03, material=trim_mat,
    )
    seat.location.x = -length * 0.05
    seat.location.z = draft * 0.7
    apply_all_transforms(seat)
    asset.add_geometry(seat)

    # Handlebar: a vertical post plus a horizontal bar, mounted at the bow.
    post = create_cylinder(make_name("mesh", asset.name, "HandlebarPost"), radius=0.025, depth=0.32, material=metal_mat)
    post.location.x = length * 0.32
    post.location.z = draft * 0.7
    apply_all_transforms(post)
    asset.add_geometry(post)

    bar = create_cylinder(make_name("mesh", asset.name, "HandlebarBar"), radius=0.02, depth=beam * 0.7, material=metal_mat)
    bar.rotation_euler.x = 1.5708  # 90 degrees: lay the cylinder flat across the beam
    bar.location.x = length * 0.32
    bar.location.z = draft * 0.7 + 0.32
    apply_all_transforms(bar)
    asset.add_geometry(bar)

    # Rear water-jet nozzle.
    nozzle = create_cylinder(make_name("mesh", asset.name, "JetNozzle"), radius=0.08, depth=0.2, material=metal_mat)
    nozzle.rotation_euler.y = 1.5708
    nozzle.location.x = -length / 2 - 0.05
    nozzle.location.z = -draft * 0.3
    apply_all_transforms(nozzle)
    asset.add_geometry(nozzle)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Main", asset.geometry_objects)
    generate_decimated_lod(asset, "Hull", hull, level=1, ratio=0.4)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_jetski()

    result = validate_asset(asset, poly_budget=15000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test9_jetski.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test9_jetski.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

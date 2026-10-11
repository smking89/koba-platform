"""TEST 6: Procedural boat.

Exercises: core.asset, geometry.primitives.create_hull (new — lofted
tapered hull, no external mesh), materials.wood/metal, optimization
.collision/.lod, core.validation, core.preview, export.exporter.

Run with:
  <blender> -b --python tests/test6_boat.py
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
from materials.wood import painted_wood  # noqa: E402
from materials.metal import bare_metal, painted_metal  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR, PROJECT_ROOT as CFG_ROOT  # noqa: E402


def build_boat(length=3.6, beam=1.3, draft=0.4, seats=2, interactive=False):
    prepare_scene("Boat", interactive)
    asset = Asset(name="Boat", asset_type="vehicle")

    hull_mat = painted_wood(make_name("material", asset.name, "Hull"), color=(0.55, 0.32, 0.14))
    trim_mat = bare_metal(make_name("material", asset.name, "Trim"))
    motor_mat = painted_metal(make_name("material", asset.name, "Motor"), color=(0.1, 0.1, 0.12))
    asset.register_material(hull_mat.name)
    asset.register_material(trim_mat.name)
    asset.register_material(motor_mat.name)

    hull = create_hull(
        make_name("mesh", asset.name, "Hull"),
        length=length, beam=beam, draft=draft, deck_height=draft * 0.55,
        sections=14, material=hull_mat,
    )
    asset.add_geometry(hull)

    # Bench seats: thin planks spanning the beam, evenly spaced along the
    # open midbody (between the flat stern and where the hull starts
    # narrowing toward the bow).
    seat_span = length * 0.45
    for i in range(seats):
        t = (i + 1) / (seats + 1)
        seat = create_box(
            make_name("mesh", asset.name, f"Seat{i}"),
            width=beam * 0.85, depth=0.18, height=0.04,
            bevel_width=0.005, material=hull_mat,
        )
        seat.location.x = -length * 0.15 + (t - 0.5) * seat_span
        seat.location.z = draft * 0.15
        apply_all_transforms(seat)
        asset.add_geometry(seat)

    # Rub rail: a thin trim strip along each side at the deck line, purely
    # cosmetic (breaks up the flat wood-only read).
    for side in (-1, 1):
        rail = create_box(
            make_name("mesh", asset.name, f"RubRail{'L' if side < 0 else 'R'}"),
            width=length * 0.92, depth=0.03, height=0.03,
            bevel_width=0.005, material=trim_mat,
        )
        rail.location.y = side * (beam / 2 + 0.01)
        rail.location.z = draft * 0.55
        apply_all_transforms(rail)
        asset.add_geometry(rail)

    # Outboard motor: a cylinder shaft + a small box housing, mounted at
    # the transom (stern).
    motor_shaft = create_cylinder(
        make_name("mesh", asset.name, "MotorShaft"),
        radius=0.06, depth=0.5, material=motor_mat,
    )
    motor_shaft.rotation_euler.x = 0.15
    motor_shaft.location.x = -length / 2 - 0.05
    motor_shaft.location.z = -draft * 0.3
    apply_all_transforms(motor_shaft)
    asset.add_geometry(motor_shaft)

    motor_housing = create_box(
        make_name("mesh", asset.name, "MotorHousing"),
        width=0.22, depth=0.3, height=0.35,
        bevel_width=0.02, material=motor_mat,
    )
    motor_housing.location.x = -length / 2 - 0.05
    motor_housing.location.z = draft * 0.55
    apply_all_transforms(motor_housing)
    asset.add_geometry(motor_housing)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Main", asset.geometry_objects)
    generate_decimated_lod(asset, "Hull", hull, level=1, ratio=0.4)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_boat()

    result = validate_asset(asset, poly_budget=15000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test6_boat.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test6_boat.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

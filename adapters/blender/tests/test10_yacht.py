"""TEST 10: Procedural yacht.

Exercises: core.asset, geometry.primitives.create_hull (reused, larger
proportions) + create_box for a multi-level cabin superstructure,
materials.plastic (hull/cabin) + materials.metal (railings), optimization
.collision/.lod, core.validation, core.preview, export.exporter.

Run with:
  <blender> -b --python tests/test10_yacht.py
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


def build_yacht(length=14.0, beam=4.2, draft=1.3, interactive=False):
    prepare_scene("Yacht", interactive)
    asset = Asset(name="Yacht", asset_type="vehicle")

    hull_mat = glossy_plastic(make_name("material", asset.name, "Hull"), color=(0.92, 0.92, 0.9), roughness=0.2)
    window_mat = glossy_plastic(make_name("material", asset.name, "Window"), color=(0.05, 0.08, 0.12), roughness=0.1)
    rail_mat = bare_metal(make_name("material", asset.name, "Rail"))
    asset.register_material(hull_mat.name)
    asset.register_material(window_mat.name)
    asset.register_material(rail_mat.name)

    hull = create_hull(
        make_name("mesh", asset.name, "Hull"),
        length=length, beam=beam, draft=draft, deck_height=draft * 0.5,
        sections=18, material=hull_mat,
    )
    asset.add_geometry(hull)

    # Lower cabin: a wide, low superstructure sitting on the deck,
    # covering the midbody where the hull is at full beam.
    lower_cabin = create_box(
        make_name("mesh", asset.name, "LowerCabin"),
        width=beam * 0.75, depth=length * 0.42, height=1.4,
        bevel_width=0.04, material=hull_mat,
    )
    lower_cabin.location.x = length * 0.02
    lower_cabin.location.z = draft * 0.5
    apply_all_transforms(lower_cabin)
    asset.add_geometry(lower_cabin)

    # Window band around the lower cabin (a slightly recessed dark strip
    # — simulated as a thinner box sitting in front of the cabin face
    # rather than a real transmissive material, per the project's own
    # documented gummy-material caution about transmission/SSS materials
    # not reading correctly outside Rendered/Cycles preview).
    window_band = create_box(
        make_name("mesh", asset.name, "WindowBand"),
        width=beam * 0.76, depth=length * 0.38, height=0.35,
        material=window_mat,
    )
    window_band.location.x = lower_cabin.location.x
    window_band.location.z = draft * 0.5 + 0.75
    apply_all_transforms(window_band)
    asset.add_geometry(window_band)

    # Upper flybridge: a smaller second-level box, set back toward the stern.
    flybridge = create_box(
        make_name("mesh", asset.name, "Flybridge"),
        width=beam * 0.5, depth=length * 0.2, height=0.9,
        bevel_width=0.03, material=hull_mat,
    )
    flybridge.location.x = -length * 0.08
    flybridge.location.z = draft * 0.5 + 1.4
    apply_all_transforms(flybridge)
    asset.add_geometry(flybridge)

    # A short mast/antenna on the flybridge roof.
    mast = create_cylinder(make_name("mesh", asset.name, "Mast"), radius=0.03, depth=1.6, material=rail_mat)
    mast.location.x = -length * 0.08
    mast.location.z = draft * 0.5 + 1.4 + 0.9
    apply_all_transforms(mast)
    asset.add_geometry(mast)

    # Deck railings along both sides of the bow (forward of the cabin,
    # where the deck is walkable) — thin horizontal rails on short posts.
    for side in (-1, 1):
        rail = create_box(
            make_name("mesh", asset.name, f"Rail{'L' if side < 0 else 'R'}"),
            width=0.02, depth=length * 0.3, height=0.02,
            material=rail_mat,
        )
        rail.location.y = side * (beam * 0.42)
        rail.location.x = length * 0.28
        rail.location.z = draft * 0.5 + 0.55
        apply_all_transforms(rail)
        asset.add_geometry(rail)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Main", asset.geometry_objects)
    generate_decimated_lod(asset, "Hull", hull, level=1, ratio=0.4)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_yacht()

    result = validate_asset(asset, poly_budget=20000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test10_yacht.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test10_yacht.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

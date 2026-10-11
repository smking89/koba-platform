"""TEST 1: Procedural crate.

Exercises: core.asset, geometry.primitives, materials.wood/metal,
optimization.collision, optimization.lod, core.validation, core.preview,
export.exporter.

Run with:
  <blender> -b --python tests/test1_crate.py
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
from geometry.primitives import create_box  # noqa: E402
from geometry.mesh_utils import bevel_edges  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from materials.metal import bare_metal  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR, PROJECT_ROOT as CFG_ROOT  # noqa: E402


def build_crate(length=1.0, width=1.0, height=1.0, plank_thickness=0.03, corner_metal=True, interactive=False):
    prepare_scene("Crate", interactive)
    asset = Asset(name="Crate", asset_type="prop")

    wood_mat = painted_wood(make_name("material", asset.name, "Wood"))
    metal_mat = bare_metal(make_name("material", asset.name, "Corner"))
    asset.register_material(wood_mat.name)
    if corner_metal:
        asset.register_material(metal_mat.name)

    body = create_box(
        make_name("mesh", asset.name, "Body"),
        width=width, depth=width, height=height,
        bevel_width=0.01, material=wood_mat,
    )
    asset.add_geometry(body)

    # Corner brackets: 4 thin metal strips along the vertical edges.
    if corner_metal:
        bracket_w = 0.05
        for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
            bracket = create_box(
                make_name("mesh", asset.name, f"CornerBracket{i}"),
                width=bracket_w, depth=bracket_w, height=height * 1.02,
                bevel_width=0.003, material=metal_mat,
            )
            bracket.location.x = sx * (width / 2 - bracket_w / 2)
            bracket.location.y = sy * (width / 2 - bracket_w / 2)
            apply_all_transforms(bracket)
            asset.add_geometry(bracket)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Main", asset.geometry_objects)
    generate_decimated_lod(asset, "Body", body, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_crate()

    result = validate_asset(asset, poly_budget=5000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test1_crate.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test1_crate.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

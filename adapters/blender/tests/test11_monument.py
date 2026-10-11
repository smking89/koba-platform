"""TEST 11: Procedural monument.

Exercises: core.asset, geometry.primitives.create_pyramid (new — a tapered
obelisk tip, the first non-box/cylinder/hull procedural shape besides the
boat hull), the new materials.stone, optimization.collision/.lod,
core.validation, core.preview, export.exporter.

A static landmark prop (a stepped-base obelisk with corner pillars and a
plaque) — not the master spec's full "Monuments" product type (an actual
KOBA content category with its own pipeline, not started, see
ROADMAP.md), just another asset-generator test in this series.

Run with:
  <blender> -b --python tests/test11_monument.py
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
from core.entity_metadata import for_hero_asset  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from geometry.primitives import create_box, create_cylinder, create_pyramid  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR, PROJECT_ROOT as CFG_ROOT  # noqa: E402


def build_monument(base_width=6.0, tiers=3, obelisk_height=8.0, interactive=False):
    prepare_scene("Monument", interactive)
    asset = Asset(name="Monument", asset_type="prop")

    stone_mat = carved_stone(make_name("material", asset.name, "Stone"))
    plaque_mat = galvanized_steel(make_name("material", asset.name, "Plaque"))
    asset.register_material(stone_mat.name)
    asset.register_material(plaque_mat.name)

    # Stepped base: `tiers` stacked boxes, each narrower and shorter than
    # the one below it, like a plinth.
    z_cursor = 0.0
    tier_height = 0.6
    top_width = base_width
    for i in range(tiers):
        width = base_width * (1.0 - i * 0.22)
        tier = create_box(
            make_name("mesh", asset.name, f"BaseTier{i}"),
            width=width, depth=width, height=tier_height,
            bevel_width=0.02, material=stone_mat,
        )
        tier.location.z = z_cursor
        apply_all_transforms(tier)
        asset.add_geometry(tier, metadata=for_hero_asset(category="monument"))
        z_cursor += tier_height
        top_width = width

    # Obelisk shaft: a tall, slightly tapered box rising from the top tier.
    shaft_width = top_width * 0.35
    shaft_height = obelisk_height * 0.75
    shaft = create_box(
        make_name("mesh", asset.name, "Shaft"),
        width=shaft_width, depth=shaft_width, height=shaft_height,
        bevel_width=0.02, material=stone_mat,
    )
    shaft.location.z = z_cursor
    apply_all_transforms(shaft)
    asset.add_geometry(shaft, metadata=for_hero_asset(category="monument"))

    # Pyramidal tip.
    tip = create_pyramid(
        make_name("mesh", asset.name, "Tip"),
        base_width=shaft_width * 1.05, height=obelisk_height * 0.25, sides=4, material=stone_mat,
    )
    tip.rotation_euler.z = 0.7854  # 45 degrees: align the 4-sided cone's flat faces with the shaft's box faces
    tip.location.z = z_cursor + shaft_height
    apply_all_transforms(tip)
    asset.add_geometry(tip, metadata=for_hero_asset(category="monument"))

    # Corner pillars on the top tier.
    pillar_offset = top_width / 2 - 0.4
    for sx, sy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        pillar = create_cylinder(
            make_name("mesh", asset.name, f"Pillar{sx}{sy}"), radius=0.25, depth=1.8, material=stone_mat,
        )
        pillar.location.x = sx * pillar_offset
        pillar.location.y = sy * pillar_offset
        pillar.location.z = z_cursor
        apply_all_transforms(pillar)
        asset.add_geometry(pillar, metadata=for_hero_asset(category="monument"))

    # A plaque on the base's front face.
    plaque = create_box(
        make_name("mesh", asset.name, "Plaque"),
        width=base_width * 0.3, depth=0.03, height=0.9,
        material=plaque_mat,
    )
    plaque.location.y = -(base_width / 2 + 0.02)
    plaque.location.z = tier_height * 1.5
    apply_all_transforms(plaque)
    asset.add_geometry(plaque, metadata=for_hero_asset(category="monument"))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Main", asset.geometry_objects)
    generate_decimated_lod(asset, "Shaft", shaft, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_monument()

    result = validate_asset(asset, poly_budget=10000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test11_monument.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test11_monument.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

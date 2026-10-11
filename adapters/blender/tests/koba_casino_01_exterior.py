"""KOBA CASINO & RESORT — Phase 1: exterior silhouette & grand entrance.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 1: the Main Resort Tower's
exterior shell/blockout, the "KOBA CASINO & RESORT" pylon sign, and the
grand entrance massing (glass frontage + entrance stairs). First real
test of this Blender pipeline at building scale — everything before
this has been a single prop/vehicle, never a 50m-tall structure.

Deliberately a BLOCKOUT: stepped-tier massing + glass curtain-wall
panels for visual read, not modeled windows/interior/ornamentation.
Honest about that in its own metadata/naming, not a finished facade.

Run with:
  <blender> -b --python tests/koba_casino_01_exterior.py
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
from geometry.primitives import create_box, create_cylinder  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from materials.glass import curtain_wall_glass  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402


def build_exterior(interactive=False):
    prepare_scene("KobaCasinoResort_Exterior", interactive)
    asset = Asset(name="KobaCasinoResort_Exterior", asset_type="monument")

    stone_mat = carved_stone(make_name("material", asset.name, "TowerStone"), color=(0.62, 0.59, 0.54))
    metal_mat = galvanized_steel(make_name("material", asset.name, "TowerMetal"))
    glass_mat = curtain_wall_glass(make_name("material", asset.name, "CurtainWall"))
    sign_mat = galvanized_steel(make_name("material", asset.name, "SignFrame"))
    for mat in (stone_mat, metal_mat, glass_mat, sign_mat):
        asset.register_material(mat.name)

    # --- Main Resort Tower: 3-tier stepped massing (base -> mid -> crown) ---
    tiers = [
        # (width, depth, height)
        (40.0, 30.0, 15.0),
        (32.0, 24.0, 20.0),
        (24.0, 18.0, 15.0),
    ]
    z_cursor = 0.0
    tower_objects = []
    for i, (w, d, h) in enumerate(tiers):
        tier = create_box(
            make_name("mesh", asset.name, f"TowerTier{i}"),
            width=w, depth=d, height=h, bevel_width=0.1, material=stone_mat,
        )
        tier.location.z = z_cursor
        apply_all_transforms(tier)
        asset.add_geometry(tier, metadata=for_hero_asset(category="monument"))
        tower_objects.append(tier)

        # A curtain-wall glass band wrapped on the tier's front (south)
        # face, reading as windows without modeling individual panes.
        band_height = h * 0.6
        band = create_box(
            make_name("mesh", asset.name, f"TowerTier{i}_GlassBand"),
            width=w * 0.85, depth=0.15, height=band_height, material=glass_mat,
        )
        band.location.y = -(d / 2 + 0.1)
        band.location.z = z_cursor + h * 0.2
        apply_all_transforms(band)
        asset.add_geometry(band, metadata=for_hero_asset(category="monument"))

        z_cursor += h
    tower_top_z = z_cursor

    # Crown cap on the tower's roofline — a small stepped-back metal cap,
    # not the full rooftop-equipment pass (that's Phase 8).
    crown = create_box(
        make_name("mesh", asset.name, "TowerCrown"),
        width=tiers[-1][0] * 0.5, depth=tiers[-1][1] * 0.5, height=2.5,
        bevel_width=0.05, material=metal_mat,
    )
    crown.location.z = tower_top_z
    apply_all_transforms(crown)
    asset.add_geometry(crown, metadata=for_hero_asset(category="monument"))
    tower_objects.append(crown)

    # --- Grand entrance massing: glass frontage canopy + entrance stairs ---
    canopy_width, canopy_depth, canopy_height = 26.0, 8.0, 7.0
    canopy = create_box(
        make_name("mesh", asset.name, "EntranceCanopy"),
        width=canopy_width, depth=canopy_depth, height=canopy_height,
        bevel_width=0.08, material=glass_mat,
    )
    canopy.location.y = -(tiers[0][1] / 2 + canopy_depth / 2)
    canopy.location.z = 0.0
    apply_all_transforms(canopy)
    asset.add_geometry(canopy, metadata=for_hero_asset(category="monument"))

    canopy_frame = create_box(
        make_name("mesh", asset.name, "EntranceCanopyFrame"),
        width=canopy_width + 1.0, depth=canopy_depth + 1.0, height=0.6,
        bevel_width=0.05, material=metal_mat,
    )
    canopy_frame.location.y = canopy.location.y
    canopy_frame.location.z = canopy_height
    apply_all_transforms(canopy_frame)
    asset.add_geometry(canopy_frame, metadata=for_hero_asset(category="monument"))

    # A few stepped stair-tier boxes leading up to the entrance.
    stair_tiers, stair_run = 4, 2.0
    stair_y_base = canopy.location.y - canopy_depth / 2 - 1.0
    for i in range(stair_tiers):
        step = create_box(
            make_name("mesh", asset.name, f"EntranceStair{i}"),
            width=canopy_width * 0.9, depth=stair_run, height=0.3,
            material=stone_mat,
        )
        step.location.y = stair_y_base - i * stair_run
        step.location.z = -0.3 * (stair_tiers - i - 1)
        apply_all_transforms(step)
        asset.add_geometry(step, metadata=for_hero_asset(category="monument"))

    # --- "KOBA CASINO & RESORT" pylon sign, forward of the entrance ---
    sign_pole = create_cylinder(
        make_name("mesh", asset.name, "SignPole"), radius=1.0, depth=18.0, material=sign_mat,
    )
    sign_x, sign_y = 0.0, stair_y_base - stair_tiers * stair_run - 6.0
    sign_pole.location.x = sign_x
    sign_pole.location.y = sign_y
    apply_all_transforms(sign_pole)
    asset.add_geometry(sign_pole, metadata=for_hero_asset(category="monument"))

    sign_panel = create_box(
        make_name("mesh", asset.name, "SignPanel"),
        width=16.0, depth=0.6, height=4.5, bevel_width=0.05, material=sign_mat,
    )
    sign_panel.location.x = sign_x
    sign_panel.location.y = sign_y
    sign_panel.location.z = 15.5
    apply_all_transforms(sign_panel)
    asset.add_geometry(sign_panel, metadata=for_hero_asset(category="monument"))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "TowerMain", tower_objects)
    generate_decimated_lod(asset, "TowerTier0", tower_objects[0], level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_exterior()

    result = validate_asset(asset, poly_budget=50000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_01_exterior.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_01_exterior.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

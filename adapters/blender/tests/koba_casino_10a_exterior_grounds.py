"""KOBA CASINO & RESORT — Phase 10a: Exterior grounds.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 10 / master prompt §5,§26:
the resort's arrival grounds — a decorative fountain, vehicle roads
(main approach, a branch toward the event sites, a service road to the
Phase 7 loading dock), a surface parking lot with marked stalls, a
valet/drop-off lane, and basic landscaping (planters + simple
tree-like markers).

Its own ground-level site (own floor slab at z=0) in front of Phase 1's
tower entrance — like every other phase, this is validated as an
independent asset, not literally composited into the same Blender file
as Phase 1-9's assets; the spatial relationships described here are
the intended real-world layout, not an enforced shared coordinate
space yet (true multi-asset composition is future work).

Honest blockout limitations: roads are flat colored strips, not real
road meshes with curbs; "trees" are a pyramid stand-in, not foliage
geometry; no actual vehicles parked in the lot.

Run with:
  <blender> -b --python tests/koba_casino_10a_exterior_grounds.py
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
from core.entity_metadata import for_static_prop  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.interaction_point import add_interaction_point  # noqa: E402
from geometry.primitives import create_box, create_cylinder, create_pyramid  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.glass import tinted_glass  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 0.1


def _box(asset, part, x, y, z, w, d, h, mat, category="grounds_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_exterior_grounds(interactive=False):
    prepare_scene("KobaCasinoResort_ExteriorGrounds", interactive)
    asset = Asset(name="KobaCasinoResort_ExteriorGrounds", asset_type="monument")

    mats = {
        "ground": carved_stone(make_name("material", asset.name, "SiteGround"), color=(0.4, 0.42, 0.38)),
        "road": carved_stone(make_name("material", asset.name, "RoadSurface"), color=(0.2, 0.2, 0.2)),
        "stall_line": glossy_plastic(make_name("material", asset.name, "StallLine"), color=(0.9, 0.85, 0.2), roughness=0.5),
        "fountain": carved_stone(make_name("material", asset.name, "FountainStone"), color=(0.6, 0.58, 0.5)),
        "water": tinted_glass(make_name("material", asset.name, "FountainWater"), tint=(0.15, 0.5, 0.6), alpha=0.5),
        "planter": carved_stone(make_name("material", asset.name, "Planter"), color=(0.45, 0.4, 0.35)),
        "foliage": glossy_plastic(make_name("material", asset.name, "Foliage"), color=(0.15, 0.4, 0.15), roughness=0.7),
        "valet": glossy_plastic(make_name("material", asset.name, "ValetLane"), color=(0.6, 0.1, 0.1), roughness=0.5),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Site ground ---
    _box(asset, "SiteGround", 0.0, 0.0, 0.0, 60.0, 50.0, 0.1, mats["ground"], category="grounds_site", importance="high")

    # --- Main approach road, leading toward the tower entrance (north) ---
    _box(asset, "MainApproachRoad", 0.0, 5.0, FLOOR_Z, 8.0, 30.0, 0.02, mats["road"], category="grounds_road", importance="high")

    # --- Fountain, traffic circle near the entrance ---
    fountain_base = create_cylinder(make_name("mesh", asset.name, "FountainBase"), radius=4.0, depth=0.6, material=mats["fountain"])
    fountain_base.location.x, fountain_base.location.y, fountain_base.location.z = 0.0, 16.0, FLOOR_Z
    apply_all_transforms(fountain_base)
    asset.add_geometry(fountain_base, metadata=for_static_prop(category="grounds_fountain", importance="hero"))

    fountain_water = create_cylinder(make_name("mesh", asset.name, "FountainWater"), radius=3.5, depth=0.1, material=mats["water"])
    fountain_water.location.x, fountain_water.location.y, fountain_water.location.z = 0.0, 16.0, FLOOR_Z + 0.6
    apply_all_transforms(fountain_water)
    asset.add_geometry(fountain_water, metadata=for_static_prop(category="grounds_fountain", importance="hero"))

    fountain_center = create_cylinder(make_name("mesh", asset.name, "FountainCenterSpout"), radius=0.5, depth=2.0, material=mats["fountain"])
    fountain_center.location.x, fountain_center.location.y, fountain_center.location.z = 0.0, 16.0, FLOOR_Z + 0.7
    apply_all_transforms(fountain_center)
    asset.add_geometry(fountain_center, metadata=for_static_prop(category="grounds_fountain", importance="hero"))
    add_interaction_point(asset, "Grounds.Fountain.001", location=(0.0, 16.0, FLOOR_Z + 2.0))

    # --- Valet / drop-off lane, beside the main road near the entrance ---
    _box(asset, "ValetLane", 6.0, 20.0, FLOOR_Z, 4.0, 8.0, 0.02, mats["valet"], category="grounds_valet", importance="high")
    add_interaction_point(asset, "Grounds.Valet.001", location=(6.0, 20.0, FLOOR_Z + 0.02))

    # --- Service road to the Phase 7 loading dock ---
    _box(asset, "ServiceRoad", 20.0, -10.0, FLOOR_Z, 5.0, 24.0, 0.02, mats["road"], category="grounds_road", importance="medium")
    add_interaction_point(asset, "Grounds.ServiceRoad.001", location=(20.0, -10.0, FLOOR_Z + 0.02))

    # --- Branch road toward the event sites (south) ---
    _box(asset, "EventBranchRoad", -18.0, -5.0, FLOOR_Z, 5.0, 30.0, 0.02, mats["road"], category="grounds_road", importance="medium")
    add_interaction_point(asset, "Grounds.EventAccessRoad.001", location=(-18.0, -5.0, FLOOR_Z + 0.02))

    # --- Surface parking lot, east side: 4 rows x 6 stalls ---
    stall_idx = 1
    for row in range(4):
        for col in range(6):
            sx = 18.0 + col * 2.2
            sy = -20.0 + row * 4.0
            _box(asset, f"ParkingStallLine{stall_idx:03d}", sx, sy, FLOOR_Z, 0.1, 4.0, 0.02, mats["stall_line"],
                 category="grounds_parking", importance="low")
            stall_idx += 1
    add_interaction_point(asset, "Grounds.Parking.001", location=(23.0, -12.0, FLOOR_Z + 0.02))

    # --- Landscaping: planters with a pyramid "tree" stand-in ---
    for i, (px, py) in enumerate(((-6.0, 20.0), (6.0, 12.0), (-10.0, 8.0), (10.0, 8.0)), start=1):
        _box(asset, f"Planter{i:03d}", px, py, FLOOR_Z, 1.2, 1.2, 0.5, mats["planter"], category="grounds_landscape", importance="low")
        tree = create_pyramid(make_name("mesh", asset.name, f"TreeFoliage{i:03d}"), base_width=1.5, height=2.5, sides=6, material=mats["foliage"])
        tree.location.x, tree.location.y, tree.location.z = px, py, FLOOR_Z + 0.5
        apply_all_transforms(tree)
        asset.add_geometry(tree, metadata=for_static_prop(category="grounds_landscape", importance="low"))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    roads = [o for o in asset.geometry_objects if "Road" in o.name]
    generate_box_collision(asset, "Roads", roads)
    generate_decimated_lod(asset, "FountainBase", fountain_base, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_exterior_grounds()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_10a_exterior_grounds.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_10a_exterior_grounds.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

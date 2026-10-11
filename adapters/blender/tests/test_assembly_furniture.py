"""Test for geometry/assemblies/furniture/* — the second group of the
primitive-library expansion (Hotel Furniture), on top of KOBA CASINO &
RESORT's existing blockouts.

Builds ONE real example of every furniture assembly (double bed, desk+
chair, nightstand, sofa, lounge daybed, bathroom set, wardrobe), runs
the scene through the real validate_asset path, and reports real
entity/triangle/collision/LOD numbers.

Run with:
  <blender> -b --python tests/test_assembly_furniture.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from materials.glass import tinted_glass  # noqa: E402
from materials.pbr_library import get_pbr_material  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

from geometry.assemblies.furniture.beds import build_bed  # noqa: E402
from geometry.assemblies.furniture.desks import build_desk_and_chair, build_nightstand  # noqa: E402
from geometry.assemblies.furniture.seating import build_sofa, build_lounge_daybed  # noqa: E402
from geometry.assemblies.furniture.bathroom import build_toilet, build_sink, build_shower_stall  # noqa: E402
from geometry.assemblies.furniture.storage import build_wardrobe  # noqa: E402


def build_furniture_showcase(interactive=False):
    prepare_scene("FurnitureAssemblyShowcase", interactive)
    asset = Asset(name="FurnitureAssemblyShowcase", asset_type="monument")

    # Real downloaded PBR materials (ambientCG, via materials/pbr_library.py)
    # — one shared material per surface category, reused across every part
    # that needs it, same "one shared material, many objects" pattern
    # test11_monument.py already used for stone_mat.
    pbr_wood = get_pbr_material("wood", make_name("material", asset.name, "PBRWood"))
    pbr_metal = get_pbr_material("metal", make_name("material", asset.name, "PBRMetal"))
    pbr_fabric = get_pbr_material("fabric", make_name("material", asset.name, "PBRFabric"))
    pbr_leather = get_pbr_material("leather", make_name("material", asset.name, "PBRLeather"))
    pbr_marble = get_pbr_material("marble", make_name("material", asset.name, "PBRMarble"))

    mats = {
        "bed_frame": pbr_wood,
        "mattress": pbr_fabric,
        "headboard": pbr_wood,
        "pillow": pbr_fabric,
        "desk_top": pbr_wood,
        "leg": pbr_metal,
        "chair": pbr_leather,
        "nightstand_body": pbr_wood,
        "nightstand_drawer": pbr_metal,
        "sofa_seat": pbr_leather,
        "sofa_back": pbr_leather,
        "sofa_arm": pbr_wood,
        "lounge_cushion": pbr_fabric,
        "lounge_frame": pbr_metal,
        "toilet": pbr_marble,
        "sink": pbr_marble,
        "faucet": pbr_metal,
        "shower_glass": tinted_glass(make_name("material", asset.name, "ShowerGlass"), tint=(0.5, 0.55, 0.55), alpha=0.3),
        "shower_frame": pbr_metal,
        "wardrobe_body": pbr_wood,
        "wardrobe_door": pbr_wood,
    }
    for mat in {id(m): m for m in mats.values()}.values():
        asset.register_material(mat.name)

    counts_by_group = {}

    def _count(label, fn):
        before = len(asset.geometry_objects)
        fn()
        counts_by_group[label] = len(asset.geometry_objects) - before

    _count("bed_king", lambda: build_bed(asset, "Bed1", -5.0, 0.0, 0.0, size="king",
                                          frame_mat=mats["bed_frame"], mattress_mat=mats["mattress"],
                                          headboard_mat=mats["headboard"], pillow_mat=mats["pillow"], num_pillows=3))

    _count("desk_and_chair", lambda: build_desk_and_chair(asset, "Desk1", -1.0, 0.0, 0.0,
                                                           top_mat=mats["desk_top"], leg_mat=mats["leg"], chair_mat=mats["chair"]))

    _count("nightstand", lambda: build_nightstand(asset, "Nightstand1", 2.0, 0.0, 0.0,
                                                    body_mat=mats["nightstand_body"], drawer_mat=mats["nightstand_drawer"]))

    _count("sofa", lambda: build_sofa(asset, "Sofa1", 5.0, 0.0, 0.0,
                                       seat_mat=mats["sofa_seat"], back_mat=mats["sofa_back"], arm_mat=mats["sofa_arm"]))

    _count("lounge_daybed", lambda: build_lounge_daybed(asset, "Lounge1", 9.0, 0.0, 0.0,
                                                         cushion_mat=mats["lounge_cushion"], frame_mat=mats["lounge_frame"]))

    _count("toilet", lambda: build_toilet(asset, "Toilet1", -5.0, 5.0, 0.0, mat=mats["toilet"]))
    _count("sink", lambda: build_sink(asset, "Sink1", -2.5, 5.0, 0.0, mat=mats["sink"], faucet_mat=mats["faucet"]))
    _count("shower_stall", lambda: build_shower_stall(asset, "Shower1", 0.5, 5.0, 0.0,
                                                        glass_mat=mats["shower_glass"], frame_mat=mats["shower_frame"]))

    _count("wardrobe", lambda: build_wardrobe(asset, "Wardrobe1", 4.0, 5.0, 0.0,
                                               body_mat=mats["wardrobe_body"], door_mat=mats["wardrobe_door"], num_doors=3))

    collidable = [o for o in asset.geometry_objects if "glass" not in o.name.lower()]
    generate_box_collision(asset, "ShowcaseMain", collidable[:25])
    generate_decimated_lod(asset, "WardrobeBody", next(o for o in asset.geometry_objects if "Wardrobe1_body" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, counts_by_group


def main():
    asset, counts_by_group = build_furniture_showcase()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print("\nReal part counts per assembly:")
    total = 0
    for label, count in counts_by_group.items():
        print(f"  {label}: {count} real objects")
        total += count
    print(f"  TOTAL: {total} objects, {asset.summary()['geometry_count']} registered on asset")

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test_assembly_furniture.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test_assembly_furniture.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

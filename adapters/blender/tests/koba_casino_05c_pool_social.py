"""KOBA CASINO & RESORT — Phase 5c: Pool & Social Club.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 5 / master prompt §12: a
luxury indoor pool + deck + lounge chairs, plus the social-club
activities (pool tables, darts, air hockey, foosball), and a small VIP
pool nook.

Sits on Floor4_PoolSocial's footprint from Phase 2 (the 32x24 tier band
-> 31x23 usable, floor surface at z=19.4 = Floor4's z_cursor=19.0 +
Phase 2's SLAB_THICKNESS=0.4).

Honest blockout limitations: the pool is a flat tinted panel standing
in for a real water volume/sunken basin — no actual depth/sunken
geometry yet. No showers/changing rooms/bathrooms modeled.

Run with:
  <blender> -b --python tests/koba_casino_05c_pool_social.py
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
from geometry.primitives import create_box  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.glass import tinted_glass  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 19.4  # Floor4_PoolSocial's slab top surface (Phase 2: z_cursor=19.0 + SLAB_THICKNESS=0.4)


def _box(asset, part, x, y, z, w, d, h, mat, category="pool_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_pool_social(interactive=False):
    prepare_scene("KobaCasinoResort_PoolSocial", interactive)
    asset = Asset(name="KobaCasinoResort_PoolSocial", asset_type="monument")

    mats = {
        "water": tinted_glass(make_name("material", asset.name, "PoolWater"), tint=(0.1, 0.45, 0.55), alpha=0.6),
        "deck": carved_stone(make_name("material", asset.name, "PoolDeck"), color=(0.75, 0.72, 0.65)),
        "lounger": glossy_plastic(make_name("material", asset.name, "LoungerFrame"), color=(0.9, 0.9, 0.85), roughness=0.4),
        "pooltable": glossy_plastic(make_name("material", asset.name, "PoolTableFelt"), color=(0.05, 0.3, 0.12), roughness=0.6),
        "dartboard": painted_wood(make_name("material", asset.name, "DartboardFrame")),
        "arcade_cab": glossy_plastic(make_name("material", asset.name, "AirHockeyCabinet"), color=(0.1, 0.1, 0.15), roughness=0.3),
        "foosball": painted_wood(make_name("material", asset.name, "FoosballTable"), color=(0.5, 0.1, 0.1)),
        "vip_nook": carved_stone(make_name("material", asset.name, "VIPNookStone"), color=(0.5, 0.4, 0.15)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Pool deck (whole social-club footprint) + the pool itself ---
    _box(asset, "PoolDeck", -2.0, -2.0, FLOOR_Z, 26.0, 18.0, 0.1, mats["deck"],
         category="pool_deck", importance="high")
    _box(asset, "Pool_Water", -2.0, -2.0, FLOOR_Z + 0.1, 14.0, 8.0, 0.05, mats["water"],
         category="pool_water", importance="hero")
    add_interaction_point(asset, "Pool.Main.001", location=(-2.0, -2.0, FLOOR_Z + 0.15))

    # --- Lounge chairs around the pool edge ---
    lounger_positions = [(-9.0, -7.0), (-6.0, -7.0), (-3.0, -7.0), (0.0, -7.0), (3.0, -7.0),
                          (-9.0, 3.0), (-6.0, 3.0), (-3.0, 3.0), (0.0, 3.0), (3.0, 3.0)]
    for i, (lx, ly) in enumerate(lounger_positions, start=1):
        _box(asset, f"Lounger{i:03d}", lx, ly, FLOOR_Z, 0.7, 1.9, 0.3, mats["lounger"],
             category="pool_furniture", importance="low")
    add_interaction_point(asset, "Pool.LoungeArea.001", location=(-3.0, -2.0, FLOOR_Z + 0.3))

    # --- Social-club activities, east side of the deck ---
    _box(asset, "PoolTable", 10.0, -6.0, FLOOR_Z, 2.6, 1.4, 0.8, mats["pooltable"],
         category="pool_game", importance="medium")
    add_interaction_point(asset, "Pool.PoolTable.001", location=(10.0, -6.0, FLOOR_Z + 0.8))

    _box(asset, "Dartboard", 10.0, -2.0, FLOOR_Z, 0.1, 0.6, 0.6, mats["dartboard"],
         category="pool_game", importance="medium")
    add_interaction_point(asset, "Pool.Darts.001", location=(10.0, -1.8, FLOOR_Z + 1.5))

    _box(asset, "AirHockeyTable", 10.0, 2.0, FLOOR_Z, 2.2, 1.2, 0.9, mats["arcade_cab"],
         category="pool_game", importance="medium")
    add_interaction_point(asset, "Pool.AirHockey.001", location=(10.0, 2.0, FLOOR_Z + 0.9))

    _box(asset, "FoosballTable", 10.0, 6.0, FLOOR_Z, 1.8, 0.9, 0.85, mats["foosball"],
         category="pool_game", importance="medium")
    add_interaction_point(asset, "Pool.Foosball.001", location=(10.0, 6.0, FLOOR_Z + 0.85))

    # --- VIP pool nook, a small raised corner ---
    _box(asset, "VIPNook_Dais", -9.0, 9.0, FLOOR_Z, 6.0, 4.0, 0.5, mats["vip_nook"],
         category="pool_vip", importance="high")
    add_interaction_point(asset, "Pool.VIPArea.001", location=(-9.0, 9.0, FLOOR_Z + 0.5))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    loungers = [o for o in asset.geometry_objects if "Lounger" in o.name]
    generate_box_collision(asset, "Loungers", loungers)
    generate_box_collision(asset, "Games", [o for o in asset.geometry_objects
                                             if any(k in o.name for k in ("PoolTable", "AirHockey", "Foosball"))])
    generate_decimated_lod(asset, "VIPNook", next(o for o in asset.geometry_objects if "VIPNook_Dais" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_pool_social()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_05c_pool_social.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_05c_pool_social.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""KOBA CASINO & RESORT — Phase 6a: Restaurant + Bar.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 6 / master prompt §13-14:
a full restaurant (host desk, dining room, kitchen, private dining)
and the main + VIP bar, sharing Floor5_RestaurantBar's footprint from
Phase 2 (tier1 band -> 31x23 usable, floor surface at z=25.4 =
Floor5's z_cursor=25.0 + Phase 2's SLAB_THICKNESS=0.4).

Honest blockout limitations: no real kitchen equipment (one block
standing in for the whole back-of-house), no staff-only corridor
separate from the dining floor, no bathrooms.

Run with:
  <blender> -b --python tests/koba_casino_06a_restaurant_bar.py
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
from materials.wood import painted_wood  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 25.4  # Floor5_RestaurantBar's slab top surface (Phase 2: z_cursor=25.0 + SLAB_THICKNESS=0.4)


def _box(asset, part, x, y, z, w, d, h, mat, category="restaurant_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_restaurant_bar(interactive=False):
    prepare_scene("KobaCasinoResort_RestaurantBar", interactive)
    asset = Asset(name="KobaCasinoResort_RestaurantBar", asset_type="monument")

    mats = {
        "desk": carved_stone(make_name("material", asset.name, "HostDesk"), color=(0.4, 0.3, 0.2)),
        "table": painted_wood(make_name("material", asset.name, "DiningTable")),
        "booth": glossy_plastic(make_name("material", asset.name, "BoothSeat"), color=(0.4, 0.08, 0.1), roughness=0.5),
        "kitchen": galvanized_steel(make_name("material", asset.name, "KitchenBlock")),
        "bar_counter": carved_stone(make_name("material", asset.name, "BarCounter"), color=(0.32, 0.26, 0.22)),
        "vip_bar": carved_stone(make_name("material", asset.name, "VIPBarCounter"), color=(0.5, 0.4, 0.15)),
        "private_wall": carved_stone(make_name("material", asset.name, "PrivateDiningWall"), color=(0.55, 0.5, 0.45)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Host desk, near the floor's entrance corner ---
    _box(asset, "HostDesk", -13.0, -9.0, FLOOR_Z, 2.5, 1.0, 1.1, mats["desk"],
         category="restaurant_counter", importance="high")
    add_interaction_point(asset, "Restaurant.Host.001", location=(-13.0, -9.0, FLOOR_Z + 1.1))

    # --- Dining room: a mix of tables and booths ---
    table_positions = [(-8.0, -6.0), (-4.0, -6.0), (0.0, -6.0), (-8.0, -2.0), (-4.0, -2.0), (0.0, -2.0)]
    for i, (tx, ty) in enumerate(table_positions, start=1):
        _box(asset, f"DiningTable{i:03d}", tx, ty, FLOOR_Z, 1.2, 1.2, 0.75, mats["table"],
             category="restaurant_table", importance="medium")
        add_interaction_point(asset, f"Restaurant.Table.{i:03d}", location=(tx, ty, FLOOR_Z + 0.75))

    for i, bx in enumerate((-8.0, -4.0, 0.0), start=1):
        _box(asset, f"BoothSeat{i:03d}", bx, 2.0, FLOOR_Z, 1.8, 0.8, 0.5, mats["booth"],
             category="restaurant_seating", importance="low")

    # --- Private dining room: small walled-off area with one table ---
    _box(asset, "PrivateDining_Wall", 8.0, -4.0, FLOOR_Z, 0.2, 8.0, 1.2, mats["private_wall"],
         category="restaurant_wall", importance="low")
    _box(asset, "PrivateDining_Table", 10.0, -4.0, FLOOR_Z, 2.0, 1.4, 0.75, mats["table"],
         category="restaurant_table", importance="high")
    add_interaction_point(asset, "Restaurant.PrivateDining.001", location=(10.0, -4.0, FLOOR_Z + 0.75))

    # --- Kitchen / back-of-house block ---
    _box(asset, "Kitchen_Block", 9.0, 7.0, FLOOR_Z, 6.0, 5.0, 2.2, mats["kitchen"],
         category="restaurant_kitchen", importance="high")
    add_interaction_point(asset, "Restaurant.Kitchen.001", location=(9.0, 4.6, FLOOR_Z + 1.0))

    # --- Main bar + VIP bar nook ---
    _box(asset, "MainBar_Counter", -10.0, 8.0, FLOOR_Z, 7.0, 1.2, 1.1, mats["bar_counter"],
         category="bar_counter", importance="high")
    add_interaction_point(asset, "Bar.Main.001", location=(-10.0, 8.0, FLOOR_Z + 1.1))

    _box(asset, "VIPBar_Counter", -2.0, 9.5, FLOOR_Z, 3.0, 1.2, 1.1, mats["vip_bar"],
         category="bar_counter", importance="high")
    add_interaction_point(asset, "Bar.VIP.001", location=(-2.0, 9.5, FLOOR_Z + 1.1))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    tables = [o for o in asset.geometry_objects if "DiningTable" in o.name]
    generate_box_collision(asset, "DiningTables", tables)
    generate_box_collision(asset, "Counters", [o for o in asset.geometry_objects if "Counter" in o.name])
    generate_decimated_lod(asset, "KitchenBlock", next(o for o in asset.geometry_objects if "Kitchen_Block" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_restaurant_bar()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_06a_restaurant_bar.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_06a_restaurant_bar.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

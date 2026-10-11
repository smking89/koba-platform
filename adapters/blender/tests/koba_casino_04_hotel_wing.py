"""KOBA CASINO & RESORT — Phase 4: Hotel wing + room templates.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 4 / master prompt §16-17,§40:
one hotel wing, one floor, with the four room templates (Standard/
Deluxe/Suite/Penthouse) built ONCE each as reusable blockouts (door +
card-reader interaction point + bed/storage/table primitives), then
genuinely INSTANCED down a corridor via geometry/instancing.py — the
first real use of that module in this build (Phases 1-3 never repeated
a shape enough to need it for real).

Each room type's first occurrence is built as real geometry (the
"template"); every additional repeat of that type reuses
create_instance() for each of its mesh parts — same shared mesh
datablock, a new Object + location per repeat. The door/card-reader are
still unique per room (every room needs its OWN named
`Hotel.Room.<Type>.<NNN>.CardReader` interaction point and its own door
Object, even though the door's MESH is shared across repeats).

Layout: one 3m-wide corridor, rooms on the south side only (north side
intentionally left for a later pass — see honest limitations below),
in order: 4x Standard, 2x Deluxe, 1x Suite, 1x Penthouse — a believable
hotel-floor mix (lots of standard rooms, fewer premium), not an even
split.

Honest blockout limitations:
- Rooms exist on one side of the corridor only; mirroring it for the
  opposite side is future work, not attempted here.
- No real bathroom geometry per room — called out as missing, not
  silently represented by nothing.
- The Penthouse's "optional additional bedroom" (prompt §16) is not
  built — explicitly optional in the source spec, skipped honestly.
- Balcony is a flush platform + a thin rail bar, not a real guarded
  outdoor space.

Run with:
  <blender> -b --python tests/koba_casino_04_hotel_wing.py
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
from core.entity_metadata import for_static_prop  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.interaction_point import add_interaction_point  # noqa: E402
from geometry.primitives import create_box, create_panel  # noqa: E402
from geometry.instancing import create_instance, count_unique_meshes  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

CORRIDOR_WIDTH = 3.0
CORRIDOR_FRONT_Y = CORRIDOR_WIDTH  # door wall line; rooms extend south (increasing y) from here
FLOOR_Z = 0.0


def _mk(asset, part, x, y, z, width, depth, height, material, category="hotel_furniture", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=width, depth=depth, height=height, material=material)
    obj.location = (x, y, z)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_standard_template(asset, mats, cx):
    """Standard room: bed, nightstand storage, desk+chair (one box),
    door. width=4, depth=5."""
    parts = {}
    parts["Bed"] = _mk(asset, "Standard_Bed", cx - 1.0, CORRIDOR_FRONT_Y + 2.0, FLOOR_Z, 1.8, 2.0, 0.55, mats["bed"])
    parts["Storage"] = _mk(asset, "Standard_Storage", cx + 1.3, CORRIDOR_FRONT_Y + 0.6, FLOOR_Z, 0.6, 0.5, 0.7, mats["wood"])
    parts["Desk"] = _mk(asset, "Standard_Desk", cx + 1.3, CORRIDOR_FRONT_Y + 3.8, FLOOR_Z, 1.0, 0.6, 0.75, mats["wood"])
    door = create_panel(make_name("mesh", asset.name, "Standard_Door"), width=0.9, height=2.1, thickness=0.08, material=mats["door"])
    door.location = (cx, CORRIDOR_FRONT_Y, FLOOR_Z + 1.05)
    asset.add_geometry(door, metadata=for_static_prop(category="hotel_door", importance="high"))
    parts["Door"] = door
    return parts, 4.0, 5.0


def build_deluxe_template(asset, mats, cx):
    """Deluxe room: larger bed, storage, a lounge sofa, desk, door.
    width=5, depth=6."""
    parts = {}
    parts["Bed"] = _mk(asset, "Deluxe_Bed", cx - 1.2, CORRIDOR_FRONT_Y + 2.0, FLOOR_Z, 2.0, 2.2, 0.6, mats["bed"])
    parts["Storage"] = _mk(asset, "Deluxe_Storage", cx + 1.6, CORRIDOR_FRONT_Y + 0.6, FLOOR_Z, 0.8, 0.5, 0.8, mats["wood"])
    parts["Lounge"] = _mk(asset, "Deluxe_Lounge", cx + 1.6, CORRIDOR_FRONT_Y + 4.5, FLOOR_Z, 1.6, 0.8, 0.5, mats["sofa"])
    parts["Desk"] = _mk(asset, "Deluxe_Desk", cx - 1.2, CORRIDOR_FRONT_Y + 4.8, FLOOR_Z, 1.2, 0.6, 0.75, mats["wood"])
    door = create_panel(make_name("mesh", asset.name, "Deluxe_Door"), width=1.0, height=2.1, thickness=0.08, material=mats["door"])
    door.location = (cx, CORRIDOR_FRONT_Y, FLOOR_Z + 1.05)
    asset.add_geometry(door, metadata=for_static_prop(category="hotel_door", importance="high"))
    parts["Door"] = door
    return parts, 5.0, 6.0


def build_suite_template(asset, mats, cx):
    """Suite: separate bedroom zone + living/dining zone, larger
    storage, door. width=6, depth=8."""
    parts = {}
    parts["Bed"] = _mk(asset, "Suite_Bed", cx - 1.5, CORRIDOR_FRONT_Y + 2.0, FLOOR_Z, 2.2, 2.4, 0.6, mats["bed"])
    parts["Storage"] = _mk(asset, "Suite_Storage", cx + 2.0, CORRIDOR_FRONT_Y + 0.7, FLOOR_Z, 1.0, 0.6, 0.9, mats["wood"])
    parts["Divider"] = _mk(asset, "Suite_LoungeDivider", cx, CORRIDOR_FRONT_Y + 4.2, FLOOR_Z, 0.2, 5.5, 1.2,
                            mats["stone"], category="hotel_wall", importance="low")
    parts["Sofa"] = _mk(asset, "Suite_Sofa", cx - 1.8, CORRIDOR_FRONT_Y + 6.0, FLOOR_Z, 2.0, 0.8, 0.5, mats["sofa"])
    parts["DiningTable"] = _mk(asset, "Suite_DiningTable", cx + 1.8, CORRIDOR_FRONT_Y + 6.3, FLOOR_Z, 1.4, 1.0, 0.75, mats["wood"])
    door = create_panel(make_name("mesh", asset.name, "Suite_Door"), width=1.1, height=2.2, thickness=0.08, material=mats["door"])
    door.location = (cx, CORRIDOR_FRONT_Y, FLOOR_Z + 1.1)
    asset.add_geometry(door, metadata=for_static_prop(category="hotel_door", importance="high"))
    parts["Door"] = door
    return parts, 6.0, 8.0


def build_penthouse_template(asset, mats, cx):
    """Penthouse: large living room, premium bed, premium storage,
    balcony platform + rail, door. width=8, depth=10. The prompt's
    optional second bedroom is deliberately NOT built."""
    parts = {}
    parts["Bed"] = _mk(asset, "Penthouse_Bed", cx - 2.2, CORRIDOR_FRONT_Y + 2.2, FLOOR_Z, 2.4, 2.6, 0.65, mats["premium_bed"])
    parts["Storage"] = _mk(asset, "Penthouse_Storage", cx + 2.6, CORRIDOR_FRONT_Y + 0.8, FLOOR_Z, 1.2, 0.7, 1.0, mats["premium_wood"])
    parts["Sofa"] = _mk(asset, "Penthouse_Sofa", cx - 2.4, CORRIDOR_FRONT_Y + 6.5, FLOOR_Z, 3.0, 1.0, 0.55, mats["sofa"])
    parts["DiningTable"] = _mk(asset, "Penthouse_DiningTable", cx + 2.2, CORRIDOR_FRONT_Y + 6.8, FLOOR_Z, 2.0, 1.2, 0.75, mats["premium_wood"])
    parts["Balcony"] = _mk(asset, "Penthouse_Balcony", cx, CORRIDOR_FRONT_Y + 9.5, FLOOR_Z, 7.0, 1.6, 0.15,
                            mats["stone"], category="hotel_balcony", importance="medium")
    rail = create_box(make_name("mesh", asset.name, "Penthouse_Rail"), width=7.0, depth=0.1, height=0.9, material=mats["rail"])
    rail.location = (cx, CORRIDOR_FRONT_Y + 10.3, FLOOR_Z + 0.15)
    asset.add_geometry(rail, metadata=for_static_prop(category="hotel_balcony", importance="medium"))
    parts["Rail"] = rail
    door = create_panel(make_name("mesh", asset.name, "Penthouse_Door"), width=1.2, height=2.3, thickness=0.08, material=mats["door"])
    door.location = (cx, CORRIDOR_FRONT_Y, FLOOR_Z + 1.15)
    asset.add_geometry(door, metadata=for_static_prop(category="hotel_door", importance="high"))
    parts["Door"] = door
    return parts, 8.0, 10.0


TEMPLATE_BUILDERS = {
    "Standard": build_standard_template,
    "Deluxe": build_deluxe_template,
    "Suite": build_suite_template,
    "Penthouse": build_penthouse_template,
}


def build_room_row(asset, mats, type_label, count, x_start):
    """Builds the template once at x_start (real geometry), then reuses
    create_instance() for every additional repeat's mesh parts — the
    actual instancing proof this phase exists to demonstrate."""
    builder = TEMPLATE_BUILDERS[type_label]
    template_parts, width, depth = builder(asset, mats, x_start)
    add_interaction_point(
        asset, f"Hotel.Room.{type_label}.001.CardReader",
        location=(x_start + width * 0.3, CORRIDOR_FRONT_Y, FLOOR_Z + 1.0),
    )

    for i in range(2, count + 1):
        slot_cx = x_start + (i - 1) * width
        for part_name, source_obj in template_parts.items():
            rel_x = source_obj.location.x - x_start
            create_instance(
                asset, f"{type_label}{i:03d}_{part_name}", source_obj,
                location=(slot_cx + rel_x, source_obj.location.y, source_obj.location.z),
            )
        add_interaction_point(
            asset, f"Hotel.Room.{type_label}.{i:03d}.CardReader",
            location=(slot_cx + width * 0.3, CORRIDOR_FRONT_Y, FLOOR_Z + 1.0),
        )

    return x_start + count * width, width, depth


def build_hotel_wing(interactive=False):
    prepare_scene("KobaCasinoResort_HotelWing", interactive)
    asset = Asset(name="KobaCasinoResort_HotelWing", asset_type="monument")

    mats = {
        "bed": glossy_plastic(make_name("material", asset.name, "BedLinen"), color=(0.85, 0.85, 0.8), roughness=0.5),
        "premium_bed": glossy_plastic(make_name("material", asset.name, "PremiumBedLinen"), color=(0.6, 0.5, 0.2), roughness=0.4),
        "wood": painted_wood(make_name("material", asset.name, "FurnitureWood")),
        "sofa": glossy_plastic(make_name("material", asset.name, "SofaFabric"), color=(0.3, 0.32, 0.4), roughness=0.55),
        "door": painted_wood(make_name("material", asset.name, "DoorWood")),
        "stone": carved_stone(make_name("material", asset.name, "WingStone"), color=(0.55, 0.52, 0.48)),
        "rail": galvanized_steel(make_name("material", asset.name, "BalconyRail")),
        "premium_wood": painted_wood(make_name("material", asset.name, "PremiumWood"), color=(0.25, 0.14, 0.08)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # Floor slab for this one hotel-wing level.
    total_rooms_width = 4 * 4.0 + 2 * 5.0 + 1 * 6.0 + 1 * 8.0  # Standard*4 + Deluxe*2 + Suite + Penthouse
    floor = create_box(
        make_name("mesh", asset.name, "WingFloorSlab"),
        width=total_rooms_width + 4.0, depth=CORRIDOR_WIDTH + 10.0 + 4.0, height=0.3,
        material=mats["stone"],
    )
    floor.location = (total_rooms_width / 2, (CORRIDOR_WIDTH + 10.0) / 2, -0.3)
    asset.add_geometry(floor, metadata=for_static_prop(category="hotel_floor", importance="high"))

    x_cursor = 0.0
    row_meta = []
    for type_label, count in (("Standard", 4), ("Deluxe", 2), ("Suite", 1), ("Penthouse", 1)):
        x_cursor, width, depth = build_room_row(asset, mats, type_label, count, x_cursor)
        row_meta.append((type_label, count, width, depth))

    generate_box_collision(asset, "Furniture", [o for o in asset.geometry_objects if o.type == "MESH"][:20])
    standard_bed = next(o for o in asset.geometry_objects if "Standard_Bed" in o.name)
    generate_decimated_lod(asset, "StandardBed", standard_bed, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, row_meta, x_cursor


def main():
    asset, row_meta, corridor_length = build_hotel_wing()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print(f"Corridor length: {corridor_length}m, rooms: {row_meta}")
    print(f"Real unique meshes used: {count_unique_meshes(asset.geometry_objects)} "
          f"for {len(asset.geometry_objects)} total objects")
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_04_hotel_wing.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_04_hotel_wing.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

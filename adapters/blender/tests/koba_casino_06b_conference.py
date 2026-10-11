"""KOBA CASINO & RESORT — Phase 6b: Conference Center.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 6 / master prompt §15: the
4 named room sizes (Small/Medium/Large/Grand), each a real walled room
(reusing Phase 2's perimeter-ring approach) with a table sized to the
room, plus a reception area.

Sits on Floor6_Conference's footprint from Phase 2 (tier1 band -> 31x23
usable, floor surface at z=30.4 = Floor6's z_cursor=30.0 + Phase 2's
SLAB_THICKNESS=0.4).

Honest blockout limitations: no chairs around the tables (count/
arrangement would depend on real capacity figures nobody has supplied);
no presentation screens/boards modeled, just the room + table + door +
one interaction point per room.

Run with:
  <blender> -b --python tests/koba_casino_06b_conference.py
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
from geometry.primitives import create_box, create_panel  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 30.4  # Floor6_Conference's slab top surface (Phase 2: z_cursor=30.0 + SLAB_THICKNESS=0.4)
WALL_HEIGHT = 2.6
WALL_THICKNESS = 0.2

ROOMS = [
    ("Small", 4.0, 5.0),
    ("Medium", 6.0, 6.0),
    ("Large", 8.0, 7.0),
    ("Grand", 10.0, 9.0),
]


def build_room_walls(asset, mats, label, cx, cy, width, depth):
    """Four thin walls forming a rectangle, door gap left open on the
    north (corridor-facing) wall — same ring approach Phase 2 used for
    floor spandrels, reused here for an actual enclosed room."""
    half_w, half_d = width / 2, depth / 2
    segments = [
        (width, WALL_THICKNESS, 0.0, -half_d),   # south
        (WALL_THICKNESS, depth, -half_w, 0.0),   # west
        (WALL_THICKNESS, depth, half_w, 0.0),    # east
    ]
    for i, (w, d, ox, oy) in enumerate(segments):
        seg = create_box(make_name("mesh", asset.name, f"{label}_Wall{i}"), width=w, depth=d, height=WALL_HEIGHT, material=mats["wall"])
        seg.location.x, seg.location.y, seg.location.z = cx + ox, cy + oy, FLOOR_Z
        apply_all_transforms(seg)
        asset.add_geometry(seg, metadata=for_static_prop(category="conference_wall", importance="medium"))

    # North wall with a door gap in the middle — two short segments.
    door_gap = min(1.2, width * 0.3)
    side_w = (width - door_gap) / 2
    for sign in (-1, 1):
        seg = create_box(make_name("mesh", asset.name, f"{label}_NorthWall{sign}"), width=side_w, depth=WALL_THICKNESS, height=WALL_HEIGHT, material=mats["wall"])
        seg.location.x, seg.location.y, seg.location.z = cx + sign * (door_gap / 2 + side_w / 2), cy + half_d, FLOOR_Z
        apply_all_transforms(seg)
        asset.add_geometry(seg, metadata=for_static_prop(category="conference_wall", importance="medium"))

    door = create_panel(make_name("mesh", asset.name, f"{label}_Door"), width=door_gap, height=2.1, thickness=0.08, material=mats["door"])
    door.location.x, door.location.y, door.location.z = cx, cy + half_d, FLOOR_Z + 1.05
    apply_all_transforms(door)
    asset.add_geometry(door, metadata=for_static_prop(category="conference_door", importance="high"))


def build_conference(interactive=False):
    prepare_scene("KobaCasinoResort_Conference", interactive)
    asset = Asset(name="KobaCasinoResort_Conference", asset_type="monument")

    mats = {
        "wall": carved_stone(make_name("material", asset.name, "RoomWall"), color=(0.6, 0.58, 0.52)),
        "door": painted_wood(make_name("material", asset.name, "RoomDoor")),
        "table": painted_wood(make_name("material", asset.name, "ConferenceTable"), color=(0.28, 0.18, 0.1)),
        "reception": carved_stone(make_name("material", asset.name, "ReceptionDesk"), color=(0.4, 0.3, 0.2)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Reception, near the floor's entrance corner ---
    reception = create_box(make_name("mesh", asset.name, "ReceptionDesk"), width=2.5, depth=1.0, height=1.1, material=mats["reception"])
    reception.location.x, reception.location.y, reception.location.z = -13.0, -9.0, FLOOR_Z
    apply_all_transforms(reception)
    asset.add_geometry(reception, metadata=for_static_prop(category="conference_counter", importance="high"))
    add_interaction_point(asset, "Conference.Reception.001", location=(-13.0, -9.0, FLOOR_Z + 1.1))

    # --- 4 rooms side by side, sized Small -> Grand ---
    x_cursor = -10.0
    gap = 1.5
    for label, width, depth in ROOMS:
        cx = x_cursor + width / 2
        cy = -2.0
        build_room_walls(asset, mats, label, cx, cy, width, depth)

        table_w, table_d = width * 0.4, depth * 0.3
        table = create_box(make_name("mesh", asset.name, f"{label}_Table"), width=table_w, depth=table_d, height=0.75, material=mats["table"])
        table.location.x, table.location.y, table.location.z = cx, cy, FLOOR_Z
        apply_all_transforms(table)
        asset.add_geometry(table, metadata=for_static_prop(category="conference_table", importance="medium"))
        add_interaction_point(asset, f"Conference.{label}.001", location=(cx, cy, FLOOR_Z + 0.75))

        x_cursor += width + gap

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    walls = [o for o in asset.geometry_objects if "_Wall" in o.name]
    generate_box_collision(asset, "RoomWalls", walls)
    generate_decimated_lod(asset, "GrandTable", next(o for o in asset.geometry_objects if "Grand_Table" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_conference()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_06b_conference.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_06b_conference.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

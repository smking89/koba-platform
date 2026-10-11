"""KOBA CASINO & RESORT — Phase 2: core vertical floor structure.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 2: floorplate blockout for the
Main Resort Tower's floor stack (Floor 1 Grand Lobby/Casino up through
Floor 8 Security/Vault, plus a Rooftop level), as flat slabs + a
perimeter spandrel ring per floor, with a stairwell shaft and an
elevator shaft running the tower's full height.

This is a SEPARATE real asset from Phase 1's exterior shell (its own
project/registration), not a rebuild of it — Phase 2 is the internal
floor-plate skeleton; Phase 1's tower tiers already establish the
exterior massing/silhouette those plates sit inside of. The footprint
per floor is chosen from the SAME 3 width/depth bands Phase 1's tower
tiers used (40x30 / 32x24 / 24x18 by z-height), so the two assets stay
dimensionally consistent when assembled together later, even though
they're validated as independent artifacts here.

Honest blockout limitations, stated plainly rather than hidden:
- No door openings cut into the shaft walls or floor slabs — the
  stairwell/elevator are solid-walled volumes standing in for where
  real vertical circulation will go, not yet-functional circulation.
- No per-floor interior partitioning — that's each floor's own later
  phase (Main Casino, Hotel wing, etc.), not this one.

Run with:
  <blender> -b --python tests/koba_casino_02_floors.py
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
from geometry.primitives import create_box  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

# Same 3 footprint bands as koba_casino_01_exterior.py's tower tiers,
# keyed by the z-height range they cover, so Phase 2's floor plates
# land inside Phase 1's exterior massing rather than floating free of it.
FOOTPRINT_BANDS = [
    (0.0, 15.0, 40.0, 30.0),
    (15.0, 35.0, 32.0, 24.0),
    (35.0, 50.0, 24.0, 18.0),
]

# (floor_label, height) — Floor 1 (Grand Lobby/Casino) through Floor 8
# (Security/Vault), then a Rooftop cap. Heights are a design guideline
# per the master prompt's own section 7, not a rigid requirement.
FLOOR_STACK = [
    ("Floor1_GrandLobbyCasino", 8.0),
    ("Floor2_Arcade", 5.0),
    ("Floor3_Nightclub", 6.0),
    ("Floor4_PoolSocial", 6.0),
    ("Floor5_RestaurantBar", 5.0),
    ("Floor6_Conference", 5.0),
    ("Floor7_VIP", 5.0),
    ("Floor8_SecurityVault", 5.0),
    ("Rooftop", 2.0),
]

SLAB_THICKNESS = 0.4
WALL_THICKNESS = 0.3
WALL_HEIGHT = 1.0  # spandrel/parapet stub, not a full-height wall — exterior walls are Phase 1's job


def _footprint_for_z(z):
    for lo, hi, w, d in FOOTPRINT_BANDS:
        if lo <= z < hi:
            return w, d
    return FOOTPRINT_BANDS[-1][2], FOOTPRINT_BANDS[-1][3]


def _build_perimeter_ring(asset, name_prefix, width, depth, z, material):
    """Four thin wall-stub segments forming a rectangle ring at a
    floor's edge — a spandrel band marking the floor line, not a
    full-height wall (Phase 1's tower tiers already are the real
    exterior walls)."""
    segments = [
        (width, WALL_THICKNESS, 0.0, -(depth / 2 - WALL_THICKNESS / 2)),   # north
        (width, WALL_THICKNESS, 0.0, (depth / 2 - WALL_THICKNESS / 2)),    # south
        (WALL_THICKNESS, depth, -(width / 2 - WALL_THICKNESS / 2), 0.0),   # west
        (WALL_THICKNESS, depth, (width / 2 - WALL_THICKNESS / 2), 0.0),    # east
    ]
    for i, (w, d, x, y) in enumerate(segments):
        seg = create_box(
            make_name("mesh", asset.name, f"{name_prefix}_Wall{i}"),
            width=w, depth=d, height=WALL_HEIGHT, material=material,
        )
        seg.location.x = x
        seg.location.y = y
        seg.location.z = z
        apply_all_transforms(seg)
        asset.add_geometry(seg, metadata=for_hero_asset(category="monument"))


def build_floors(interactive=False):
    prepare_scene("KobaCasinoResort_Floors", interactive)
    asset = Asset(name="KobaCasinoResort_Floors", asset_type="monument")

    slab_mat = carved_stone(make_name("material", asset.name, "SlabStone"), color=(0.5, 0.48, 0.45))
    wall_mat = galvanized_steel(make_name("material", asset.name, "SpandrelMetal"))
    shaft_mat = carved_stone(make_name("material", asset.name, "ShaftStone"), color=(0.4, 0.38, 0.36))
    for mat in (slab_mat, wall_mat, shaft_mat):
        asset.register_material(mat.name)

    z_cursor = 0.0
    floor_slabs = []
    for label, height in FLOOR_STACK:
        w, d = _footprint_for_z(z_cursor)

        slab = create_box(
            make_name("mesh", asset.name, f"{label}_Slab"),
            width=w - 1.0, depth=d - 1.0, height=SLAB_THICKNESS, material=slab_mat,
        )
        slab.location.z = z_cursor
        apply_all_transforms(slab)
        asset.add_geometry(slab, metadata=for_hero_asset(category="monument"))
        floor_slabs.append(slab)

        _build_perimeter_ring(asset, label, w - 0.6, d - 0.6, z_cursor + SLAB_THICKNESS, wall_mat)

        z_cursor += height
    total_height = z_cursor

    # Stairwell + elevator shafts, full tower height, offset toward one
    # corner of the smallest (topmost) footprint band so they clear
    # every floor's slab at every tier width.
    smallest_w, smallest_d = FOOTPRINT_BANDS[-1][2], FOOTPRINT_BANDS[-1][3]
    shaft_x = smallest_w / 2 - 3.0
    shaft_y = smallest_d / 2 - 3.0

    stairwell = create_box(
        make_name("mesh", asset.name, "StairwellShaft"),
        width=4.0, depth=4.0, height=total_height, material=shaft_mat,
    )
    stairwell.location.x = shaft_x
    stairwell.location.y = shaft_y
    stairwell.location.z = 0.0
    apply_all_transforms(stairwell)
    asset.add_geometry(stairwell, metadata=for_hero_asset(category="monument"))

    elevator = create_box(
        make_name("mesh", asset.name, "ElevatorShaft"),
        width=3.0, depth=3.0, height=total_height, material=shaft_mat,
    )
    elevator.location.x = shaft_x
    elevator.location.y = -shaft_y
    elevator.location.z = 0.0
    apply_all_transforms(elevator)
    asset.add_geometry(elevator, metadata=for_hero_asset(category="monument"))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "FloorSlabs", floor_slabs)
    generate_box_collision(asset, "Shafts", [stairwell, elevator])
    generate_decimated_lod(asset, "StairwellShaft", stairwell, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, total_height


def main():
    asset, total_height = build_floors()

    result = validate_asset(asset, poly_budget=80000)
    print(result.report())
    print(f"Total floor-stack height: {total_height}m across {len(FLOOR_STACK)} levels")

    preview_path = render_preview(asset, angle="front")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_02_floors.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_02_floors.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

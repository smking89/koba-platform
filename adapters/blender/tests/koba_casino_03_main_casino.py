"""KOBA CASINO & RESORT — Phase 3: Main Casino floor (ground level).

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 3 / master prompt §8-9: the
ground-floor casino's distinct gaming zones — Slots, Blackjack,
Roulette, Craps, Poker, High Roller, Jackpot display, Cashier, and a
dedicated Prize/Reward counter — as zoned blockouts with one
representative primitive-built machine/table per zone, each with a
real plugin-integration-point Empty named per the master prompt's §39
convention (`Casino.Slot.001`, `Casino.Blackjack.001`, ...).

Footprint matches Floor1_GrandLobbyCasino's slab from Phase 2
(39m x 29m, the 40x30 tier band minus the 1m slab margin), floor
surface at z=0.4 (Phase 2's slab thickness) — this asset sits logically
ON TOP of that slab, not rebuilding it.

Honest blockout limitations:
- Every machine/table is a primitive box/cylinder standing in for a real
  prop, not modeled casino furniture — recognizable and correctly
  placed/spaced, not detailed prop art (see KOBA_CASINO_RESORT_ROADMAP.md
  §0's "what this roadmap does NOT cover").
- The High Roller area's "private, restricted" feel is only a raised
  dais here — no railing/rope-stanchion or private entrance wall yet.
- Walking-space spacing is a straight-line grid, not a validated
  circulation study (prompt §44's circulation-validation step — future
  work once multiple zones/phases coexist in one assembled scene).

Run with:
  <blender> -b --python tests/koba_casino_03_main_casino.py
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
from geometry.primitives import create_box, create_cylinder, create_panel  # noqa: E402
from materials.metal import galvanized_steel, bare_metal  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 0.4  # Phase 2's Floor1 slab top surface


def build_slot_machine(asset, mats, idx, x, y):
    cabinet = create_box(
        make_name("mesh", asset.name, f"Slot{idx:03d}_Cabinet"),
        width=1.0, depth=0.8, height=1.6, bevel_width=0.03, material=mats["cabinet"],
    )
    cabinet.location.x, cabinet.location.y, cabinet.location.z = x, y, FLOOR_Z
    apply_all_transforms(cabinet)
    asset.add_geometry(cabinet, metadata=for_static_prop(category="casino_machine", importance="medium"))

    screen = create_panel(
        make_name("mesh", asset.name, f"Slot{idx:03d}_Screen"),
        width=0.6, height=0.5, thickness=0.04, material=mats["screen"],
    )
    screen.location.x, screen.location.y, screen.location.z = x, y - 0.42, FLOOR_Z + 1.1
    apply_all_transforms(screen)
    asset.add_geometry(screen, metadata=for_static_prop(category="casino_machine", importance="medium"))

    add_interaction_point(asset, f"Casino.Slot.{idx:03d}", location=(x, y - 0.5, FLOOR_Z + 1.0))


def build_table(asset, mats, label, idx, x, y, width=2.0, depth=1.2, top_mat=None):
    table = create_box(
        make_name("mesh", asset.name, f"{label}{idx:03d}_Table"),
        width=width, depth=depth, height=0.9, bevel_width=0.04, material=top_mat or mats["felt"],
    )
    table.location.x, table.location.y, table.location.z = x, y, FLOOR_Z
    apply_all_transforms(table)
    asset.add_geometry(table, metadata=for_static_prop(category="casino_table", importance="medium"))
    add_interaction_point(asset, f"Casino.{label}.{idx:03d}", location=(x, y, FLOOR_Z + 0.9))
    return table


def build_roulette(asset, mats, idx, x, y):
    table = build_table(asset, mats, "Roulette", idx, x, y, width=1.6, depth=1.6, top_mat=mats["felt"])
    wheel = create_cylinder(
        make_name("mesh", asset.name, f"Roulette{idx:03d}_Wheel"),
        radius=0.6, depth=0.12, material=mats["wheel"],
    )
    wheel.location.x, wheel.location.y, wheel.location.z = x, y, FLOOR_Z + 0.9
    apply_all_transforms(wheel)
    asset.add_geometry(wheel, metadata=for_static_prop(category="casino_table", importance="medium"))


def build_counter(asset, mats, name_id, x, y, width=4.0, depth=1.0):
    counter = create_box(
        make_name("mesh", asset.name, f"{name_id}_Counter"),
        width=width, depth=depth, height=1.1, bevel_width=0.04, material=mats["counter"],
    )
    counter.location.x, counter.location.y, counter.location.z = x, y, FLOOR_Z
    apply_all_transforms(counter)
    asset.add_geometry(counter, metadata=for_static_prop(category="casino_counter", importance="high"))
    add_interaction_point(asset, f"Casino.{name_id}", location=(x, y, FLOOR_Z + 1.1))
    return counter


def build_jackpot_display(asset, mats, idx, x, y):
    pillar = create_box(
        make_name("mesh", asset.name, f"Jackpot{idx:03d}_Pillar"),
        width=1.5, depth=1.5, height=4.0, bevel_width=0.05, material=mats["pillar"],
    )
    pillar.location.x, pillar.location.y, pillar.location.z = x, y, FLOOR_Z
    apply_all_transforms(pillar)
    asset.add_geometry(pillar, metadata=for_static_prop(category="casino_display", importance="hero"))

    panel = create_box(
        make_name("mesh", asset.name, f"Jackpot{idx:03d}_Panel"),
        width=2.5, depth=0.3, height=1.0, material=mats["sign"],
    )
    panel.location.x, panel.location.y, panel.location.z = x, y, FLOOR_Z + 4.0
    apply_all_transforms(panel)
    asset.add_geometry(panel, metadata=for_static_prop(category="casino_display", importance="hero"))

    add_interaction_point(asset, f"Casino.Jackpot.{idx:03d}", location=(x, y, FLOOR_Z + 4.5))


def build_high_roller_dais(asset, mats, x, y, width=10.0, depth=8.0):
    dais = create_box(
        make_name("mesh", asset.name, "HighRoller_Dais"),
        width=width, depth=depth, height=0.3, bevel_width=0.03, material=mats["dais"],
    )
    dais.location.x, dais.location.y, dais.location.z = x, y, FLOOR_Z
    apply_all_transforms(dais)
    asset.add_geometry(dais, metadata=for_static_prop(category="casino_dais", importance="high"))

    dais_top_z = FLOOR_Z + 0.3
    for i, offset_x in enumerate((-2.5, 2.5), start=1):
        table = create_box(
            make_name("mesh", asset.name, f"HighRoller{i:03d}_Table"),
            width=2.0, depth=1.2, height=0.9, bevel_width=0.04, material=mats["premium_felt"],
        )
        table.location.x, table.location.y, table.location.z = x + offset_x, y, dais_top_z
        apply_all_transforms(table)
        asset.add_geometry(table, metadata=for_static_prop(category="casino_table", importance="high"))
        add_interaction_point(asset, f"Casino.HighRoller.{i:03d}", location=(x + offset_x, y, dais_top_z + 0.9))


def build_main_casino(interactive=False):
    prepare_scene("KobaCasinoResort_MainCasino", interactive)
    asset = Asset(name="KobaCasinoResort_MainCasino", asset_type="monument")

    mats = {
        "cabinet": bare_metal(make_name("material", asset.name, "SlotCabinet")),
        "screen": emissive_sign(make_name("material", asset.name, "SlotScreen"), color=(0.2, 0.6, 1.0)),
        "felt": glossy_plastic(make_name("material", asset.name, "Felt"), color=(0.05, 0.35, 0.15), roughness=0.6),
        "premium_felt": glossy_plastic(make_name("material", asset.name, "PremiumFelt"), color=(0.3, 0.02, 0.05), roughness=0.5),
        "wheel": galvanized_steel(make_name("material", asset.name, "WheelMetal")),
        "counter": carved_stone(make_name("material", asset.name, "CounterStone"), color=(0.35, 0.3, 0.25)),
        "pillar": galvanized_steel(make_name("material", asset.name, "JackpotPillar")),
        "sign": emissive_sign(make_name("material", asset.name, "JackpotSign"), color=(1.0, 0.75, 0.05), strength=4.0),
        "dais": carved_stone(make_name("material", asset.name, "DaisStone"), color=(0.45, 0.4, 0.3)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Slot area: 2 rows of 4, west side, near the entrance ---
    slot_idx = 1
    for row_y in (-6.0, -1.0):
        for col_x in (-17.0, -13.0, -9.0, -5.0):
            build_slot_machine(asset, mats, slot_idx, col_x, row_y)
            slot_idx += 1

    # --- Entrance-adjacent: Cashier + Prize/Reward counter ---
    build_counter(asset, mats, "Cashier", x=-6.0, y=-13.0, width=5.0, depth=1.2)
    build_counter(asset, mats, "PrizeCounter", x=1.0, y=-13.0, width=3.5, depth=1.2)

    # --- Jackpot display, central/visible from the entrance ---
    build_jackpot_display(asset, mats, 1, x=6.0, y=-10.0)

    # --- Blackjack (3), Roulette (2), Craps (1) — mid floor, east side ---
    for i, x in enumerate((2.0, 6.0, 10.0), start=1):
        build_table(asset, mats, "Blackjack", i, x, -4.0, width=2.2, depth=1.3)
    for i, x in enumerate((2.0, 8.0), start=1):
        build_roulette(asset, mats, i, x, 1.0)
    build_table(asset, mats, "Craps", 1, x=14.0, y=1.0, width=3.0, depth=1.5)

    # --- Poker (3) — toward the back ---
    for i, x in enumerate((-6.0, 0.0, 6.0), start=1):
        build_table(asset, mats, "Poker", i, x, 6.0, width=1.8, depth=1.8)

    # --- High Roller dais, furthest back/most restricted-feeling ---
    build_high_roller_dais(asset, mats, x=12.0, y=8.0)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "SlotRow", [o for o in asset.geometry_objects if "Slot" in o.name and "Cabinet" in o.name])
    generate_box_collision(asset, "Counters", [o for o in asset.geometry_objects if "Counter" in o.name])
    generate_decimated_lod(asset, "JackpotPillar", next(o for o in asset.geometry_objects if "Jackpot001_Pillar" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_main_casino()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_03_main_casino.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_03_main_casino.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

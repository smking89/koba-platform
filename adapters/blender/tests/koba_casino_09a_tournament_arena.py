"""KOBA CASINO & RESORT — Phase 9a: Live Tournament Arena + Spectator Area.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 9 / master prompt §25-26,§29:
a dedicated event arena with a central combat floor, team entrances,
competitor staging/waiting/preparation rooms, registration + ticket
counter, spectator stands (standard/premium/VIP boxes), an elevated
viewing platform, a commentator platform, a scoreboard, and an Event
Control Room overlooking the whole site (shared with Phase 9b's Mad Max
Race track, per prompt §29 — this is the ONE control room for both).

This is its OWN ground-level site (its own floor slab at z=0), not part
of the Main Resort Tower's floor stack — matching the prompt's own
description of the arena as "connected to" the resort, not inside it.

Honest blockout limitations: the arena floor is a flat square, not a
shaped combat space; stands are simple stepped boxes, not raked seating
with individual seats; no roof/covering over the arena.

Run with:
  <blender> -b --python tests/koba_casino_09a_tournament_arena.py
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
from materials.metal import galvanized_steel  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 0.3  # this site's own ground slab top surface


def _box(asset, part, x, y, z, w, d, h, mat, category="arena_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_simple_room(asset, mats, label, cx, cy, width, depth, door_side="north"):
    half_w, half_d = width / 2, depth / 2
    thickness = 0.2
    walls = {
        "south": (width, thickness, 0.0, -half_d),
        "north": (width, thickness, 0.0, half_d),
        "west": (thickness, depth, -half_w, 0.0),
        "east": (thickness, depth, half_w, 0.0),
    }
    for side, (w, d, ox, oy) in walls.items():
        if side == door_side:
            continue
        _box(asset, f"{label}_Wall{side}", cx + ox, cy + oy, FLOOR_Z, w, d, 2.5, mats["wall"], category="arena_wall", importance="low")


def build_tournament_arena(interactive=False):
    prepare_scene("KobaCasinoResort_TournamentArena", interactive)
    asset = Asset(name="KobaCasinoResort_TournamentArena", asset_type="monument")

    mats = {
        "ground": carved_stone(make_name("material", asset.name, "SiteGround"), color=(0.45, 0.42, 0.38)),
        "arena_floor": carved_stone(make_name("material", asset.name, "ArenaFloor"), color=(0.3, 0.28, 0.25)),
        "wall": carved_stone(make_name("material", asset.name, "ArenaWall"), color=(0.5, 0.48, 0.45)),
        "gate": galvanized_steel(make_name("material", asset.name, "TeamGate")),
        "stand": galvanized_steel(make_name("material", asset.name, "SpectatorStand")),
        "premium_stand": painted_wood(make_name("material", asset.name, "PremiumStand"), color=(0.3, 0.05, 0.08)),
        "vip_box": carved_stone(make_name("material", asset.name, "VIPBox"), color=(0.5, 0.4, 0.15)),
        "platform": galvanized_steel(make_name("material", asset.name, "ViewingPlatform")),
        "desk": carved_stone(make_name("material", asset.name, "RegistrationDesk"), color=(0.4, 0.3, 0.2)),
        "scoreboard": emissive_sign(make_name("material", asset.name, "Scoreboard"), color=(1.0, 0.3, 0.1), strength=3.0),
        "control": galvanized_steel(make_name("material", asset.name, "ControlRoom")),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Site ground slab ---
    _box(asset, "SiteGround", 0.0, 0.0, 0.0, 48.0, 56.0, 0.3, mats["ground"], category="arena_site", importance="high")

    # --- Central arena floor ---
    _box(asset, "ArenaFloor", 0.0, 0.0, FLOOR_Z, 16.0, 16.0, 0.05, mats["arena_floor"], category="arena_floor", importance="hero")
    add_interaction_point(asset, "Event.Tournament.Arena.001", location=(0.0, 0.0, FLOOR_Z + 0.05))

    # --- Team entrance gates (north/south tunnels into the arena) ---
    for side, sy in (("North", 9.0), ("South", -9.0)):
        _box(asset, f"TeamGate{side}", 0.0, sy, FLOOR_Z, 3.0, 3.0, 3.0, mats["gate"], category="arena_gate", importance="high")
        add_interaction_point(asset, f"Event.TeamEntrance.{side}.001", location=(0.0, sy, FLOOR_Z + 1.5))

    # --- Staging / waiting / preparation rooms behind each gate ---
    build_simple_room(asset, mats, "StagingNorth", 0.0, 14.0, 4.0, 4.0, door_side="south")
    add_interaction_point(asset, "Event.StagingArea.North.001", location=(0.0, 14.0, FLOOR_Z + 1.0))
    build_simple_room(asset, mats, "StagingSouth", 0.0, -14.0, 4.0, 4.0, door_side="north")
    add_interaction_point(asset, "Event.StagingArea.South.001", location=(0.0, -14.0, FLOOR_Z + 1.0))

    for side, (sx, sy) in (("NorthWest", (-5.0, 14.0)), ("NorthEast", (5.0, 14.0))):
        build_simple_room(asset, mats, f"Prep{side}", sx, sy, 3.0, 3.0, door_side="south")
        add_interaction_point(asset, f"Event.PreparationRoom.{side}.001", location=(sx, sy, FLOOR_Z + 1.0))

    for side, (sx, sy) in (("SouthWest", (-5.0, -14.0)), ("SouthEast", (5.0, -14.0))):
        build_simple_room(asset, mats, f"Waiting{side}", sx, sy, 3.0, 3.0, door_side="north")
        add_interaction_point(asset, f"Event.WaitingRoom.{side}.001", location=(sx, sy, FLOOR_Z + 1.0))

    # --- Registration + ticket counter + event entrance, west side ---
    _box(asset, "RegistrationDesk", -18.0, -2.0, FLOOR_Z, 2.5, 1.0, 1.1, mats["desk"], category="arena_counter", importance="high")
    add_interaction_point(asset, "Event.Registration.001", location=(-18.0, -2.0, FLOOR_Z + 1.1))
    _box(asset, "TicketCounter", -18.0, 2.0, FLOOR_Z, 2.5, 1.0, 1.1, mats["desk"], category="arena_counter", importance="high")
    add_interaction_point(asset, "Event.Spectator.Ticket.001", location=(-18.0, 2.0, FLOOR_Z + 1.1))
    add_interaction_point(asset, "Event.Entrance.001", location=(-20.0, 0.0, FLOOR_Z + 1.0))

    # --- Spectator stands, east side: 3 stepped tiers (standard -> premium outer tier) ---
    for tier in range(3):
        tier_mat = mats["premium_stand"] if tier == 2 else mats["stand"]
        _box(asset, f"StandTier{tier}", 11.0 + tier * 1.8, 0.0, FLOOR_Z + tier * 1.0, 1.6, 16.0, 1.0, tier_mat,
             category="arena_seating", importance="medium")
    add_interaction_point(asset, "Event.Spectator.Standard.001", location=(11.0, 0.0, FLOOR_Z + 1.0))
    add_interaction_point(asset, "Event.Spectator.Premium.001", location=(14.6, 0.0, FLOOR_Z + 3.0))

    # --- VIP boxes, elevated behind the stands ---
    for i, vy in enumerate((-4.0, 4.0), start=1):
        _box(asset, f"VIPBox{i:03d}", 18.0, vy, FLOOR_Z + 3.0, 3.0, 3.0, 2.2, mats["vip_box"], category="arena_vip", importance="high")
        add_interaction_point(asset, f"Event.Spectator.VIPBox.{i:03d}", location=(18.0, vy, FLOOR_Z + 4.1))

    # --- Elevated general viewing platform ---
    _box(asset, "ViewingPlatform", 20.0, 0.0, FLOOR_Z + 1.5, 3.0, 4.0, 0.3, mats["platform"], category="arena_viewing", importance="medium")
    add_interaction_point(asset, "Event.ElevatedViewing.001", location=(20.0, 0.0, FLOOR_Z + 1.5))

    # --- Commentator / host platform + scoreboard ---
    _box(asset, "CommentatorPlatform", 0.0, -18.0, FLOOR_Z, 3.0, 2.0, 1.0, mats["platform"], category="arena_commentary", importance="high")
    add_interaction_point(asset, "Event.Commentator.001", location=(0.0, -18.0, FLOOR_Z + 1.0))

    scoreboard = create_panel(make_name("mesh", asset.name, "Scoreboard"), width=6.0, height=3.0, thickness=0.3, material=mats["scoreboard"])
    scoreboard.location.x, scoreboard.location.y, scoreboard.location.z = 0.0, 18.0, FLOOR_Z + 6.0
    apply_all_transforms(scoreboard)
    asset.add_geometry(scoreboard, metadata=for_static_prop(category="arena_display", importance="hero"))
    add_interaction_point(asset, "Event.Scoreboard.001", location=(0.0, 18.0, FLOOR_Z + 6.0))

    # --- Shared Event Control Room, elevated at the far end overlooking
    #     both this arena and Phase 9b's Mad Max Race track ---
    _box(asset, "EventControlRoom", 0.0, 24.0, FLOOR_Z + 4.0, 6.0, 4.0, 2.8, mats["control"],
         category="arena_control", importance="hero")
    add_interaction_point(asset, "Event.ControlRoom.001", location=(0.0, 24.0, FLOOR_Z + 5.4))
    add_interaction_point(asset, "Event.Announcer.001", location=(1.5, 24.0, FLOOR_Z + 5.4))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    stands = [o for o in asset.geometry_objects if "StandTier" in o.name]
    generate_box_collision(asset, "Stands", stands)
    generate_box_collision(asset, "Gates", [o for o in asset.geometry_objects if "TeamGate" in o.name])
    generate_decimated_lod(asset, "EventControlRoom", next(o for o in asset.geometry_objects if "EventControlRoom" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_tournament_arena()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_09a_tournament_arena.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_09a_tournament_arena.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

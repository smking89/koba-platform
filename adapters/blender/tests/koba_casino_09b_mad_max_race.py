"""KOBA CASINO & RESORT — Phase 9b: KOBA MAD MAX RACE track.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 9 / master prompt §27-28: a
large outdoor combat-racing course — starting grid, vehicle staging
bays, a dirt track with a ramp/jump, wrecks, barriers, a tunnel, a
collapsed structure, a mud section, a narrow combat section, an
elevated section, an alternate route branch, obstacles, a final
straightaway, finish line, spectator grandstands, VIP viewing, a
vehicle service area, and the shared Event Control Room's race-side
booth point (the physical control room itself was built once, in
Phase 9a, per prompt §29 — this just adds this site's own interaction
point near it, not a second room).

Honest, significant blockout limitation, stated plainly rather than
hidden: this is a LINEAR course (a sequence of straight/angled ground
segments), not a closed racing loop. A genuine closed circuit needs
curved-road geometry (splines/curve modifiers) this pipeline has never
used — every primitive here is still a box/cylinder. Building a real
loop is future work, not attempted here.

Run with:
  <blender> -b --python tests/koba_casino_09b_mad_max_race.py
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
from materials.metal import galvanized_steel, rusted_metal  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 0.3


def _box(asset, part, x, y, z, w, d, h, mat, category="race_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_mad_max_race(interactive=False):
    prepare_scene("KobaCasinoResort_MadMaxRace", interactive)
    asset = Asset(name="KobaCasinoResort_MadMaxRace", asset_type="monument")

    mats = {
        "ground": carved_stone(make_name("material", asset.name, "SiteGround"), color=(0.4, 0.35, 0.28)),
        "dirt": carved_stone(make_name("material", asset.name, "DirtTrack"), color=(0.35, 0.28, 0.18)),
        "mud": carved_stone(make_name("material", asset.name, "MudSection"), color=(0.22, 0.18, 0.12)),
        "ramp": rusted_metal(make_name("material", asset.name, "RampMetal"), rust_amount=0.4),
        "barrier": rusted_metal(make_name("material", asset.name, "Barrier"), rust_amount=0.5),
        "wreck": rusted_metal(make_name("material", asset.name, "WreckedVehicle"), rust_amount=0.7),
        "tunnel": galvanized_steel(make_name("material", asset.name, "TunnelStructure")),
        "stand": galvanized_steel(make_name("material", asset.name, "Grandstand")),
        "vip": carved_stone(make_name("material", asset.name, "VIPViewing"), color=(0.5, 0.4, 0.15)),
        "bay": carved_stone(make_name("material", asset.name, "VehicleBay"), color=(0.3, 0.3, 0.32)),
        "finish": emissive_sign(make_name("material", asset.name, "FinishLine"), color=(1.0, 1.0, 1.0), strength=2.0),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Site ground ---
    _box(asset, "SiteGround", 0.0, 4.0, 0.0, 30.0, 56.0, 0.3, mats["ground"], category="race_site", importance="high")

    # --- Starting grid + vehicle staging bays (south end) ---
    _box(asset, "StartingGrid", 0.0, -22.0, FLOOR_Z, 8.0, 4.0, 0.05, mats["dirt"], category="race_start", importance="hero")
    add_interaction_point(asset, "Event.Race.Start.001", location=(0.0, -22.0, FLOOR_Z + 0.05))
    for i, bx in enumerate((-6.0, -2.0, 2.0, 6.0), start=1):
        _box(asset, f"VehicleBay{i:03d}", bx, -26.0, FLOOR_Z, 3.0, 2.5, 0.1, mats["bay"], category="race_staging")
        add_interaction_point(asset, f"Event.Race.VehicleSpawn.{i:03d}", location=(bx, -26.0, FLOOR_Z + 0.1))

    # --- Straightaway 1 ---
    _box(asset, "Straightaway1", 0.0, -14.0, FLOOR_Z, 6.0, 12.0, 0.05, mats["dirt"], category="race_track")

    # --- Ramp / jump ---
    ramp = _box(asset, "Ramp001", 0.0, -6.0, FLOOR_Z, 5.0, 4.0, 1.5, mats["ramp"], category="race_ramp", importance="high")
    ramp.rotation_euler.x = -0.35
    add_interaction_point(asset, "Event.Race.Ramp.001", location=(0.0, -6.0, FLOOR_Z + 1.5))

    # --- Wrecks scattered near the ramp ---
    for i, (wx, wy) in enumerate(((-4.0, -4.0), (4.0, -8.0)), start=1):
        _box(asset, f"Wreck{i:03d}", wx, wy, FLOOR_Z, 2.0, 1.0, 0.6, mats["wreck"], category="race_hazard")
        add_interaction_point(asset, f"Event.Race.Wreck.{i:03d}", location=(wx, wy, FLOOR_Z + 0.6))

    # --- Mud section ---
    _box(asset, "MudSection", 0.0, 2.0, FLOOR_Z, 6.0, 8.0, 0.05, mats["mud"], category="race_track", importance="medium")
    add_interaction_point(asset, "Event.Race.MudSection.001", location=(0.0, 2.0, FLOOR_Z + 0.05))

    # --- Narrow combat section: barriers pinch the track width ---
    _box(asset, "NarrowSection", 0.0, 9.0, FLOOR_Z, 3.0, 6.0, 0.05, mats["dirt"], category="race_track")
    for sx in (-1.8, 1.8):
        _box(asset, f"Barrier_{sx:+.0f}", sx, 9.0, FLOOR_Z, 0.3, 6.0, 1.2, mats["barrier"], category="race_barrier")
    add_interaction_point(asset, "Event.Race.NarrowSection.001", location=(0.0, 9.0, FLOOR_Z + 1.2))

    # --- Collapsed structure, a toppled box beside the track ---
    collapsed = _box(asset, "CollapsedStructure", 4.0, 12.0, FLOOR_Z, 4.0, 2.0, 2.0, mats["barrier"], category="race_hazard", importance="high")
    collapsed.rotation_euler.z = 0.5
    collapsed.rotation_euler.x = 0.3
    add_interaction_point(asset, "Event.Race.CollapsedStructure.001", location=(4.0, 12.0, FLOOR_Z + 1.0))

    # --- Elevated section: raised track platform ---
    _box(asset, "ElevatedSection", 0.0, 15.0, FLOOR_Z + 1.0, 6.0, 6.0, 1.0, mats["ramp"], category="race_track", importance="high")
    add_interaction_point(asset, "Event.Race.ElevatedSection.001", location=(0.0, 15.0, FLOOR_Z + 2.0))

    # --- Alternate route branch, offset to one side ---
    _box(asset, "AlternateRoute", -7.0, 15.0, FLOOR_Z, 4.0, 10.0, 0.05, mats["dirt"], category="race_track", importance="medium")
    add_interaction_point(asset, "Event.Race.AlternateRoute.001", location=(-7.0, 15.0, FLOOR_Z + 0.05))

    # --- Obstacles ---
    for i, (ox, oy) in enumerate(((2.0, 18.0), (-2.0, 20.0)), start=1):
        _box(asset, f"Obstacle{i:03d}", ox, oy, FLOOR_Z, 1.2, 1.2, 1.0, mats["barrier"], category="race_hazard")

    # --- Tunnel: a covered track segment ---
    _box(asset, "TunnelRoof", 0.0, 21.0, FLOOR_Z + 2.0, 6.0, 5.0, 0.4, mats["tunnel"], category="race_structure", importance="medium")
    _box(asset, "TunnelTrack", 0.0, 21.0, FLOOR_Z, 6.0, 5.0, 0.05, mats["dirt"], category="race_track")
    add_interaction_point(asset, "Event.Race.Tunnel.001", location=(0.0, 21.0, FLOOR_Z + 1.0))

    # --- Final straightaway + finish line ---
    _box(asset, "FinalStraightaway", 0.0, 27.0, FLOOR_Z, 6.0, 8.0, 0.05, mats["dirt"], category="race_track")
    _box(asset, "FinishLine", 0.0, 30.5, FLOOR_Z, 6.5, 0.4, 0.05, mats["finish"], category="race_finish", importance="hero")
    add_interaction_point(asset, "Event.Race.Finish.001", location=(0.0, 30.5, FLOOR_Z + 0.05))

    # --- Spectator grandstands + VIP viewing, east side of the course ---
    for tier in range(2):
        _box(asset, f"GrandstandTier{tier}", 6.0 + tier * 1.6, 10.0, FLOOR_Z + tier * 0.9, 1.4, 40.0, 0.9, mats["stand"],
             category="race_seating", importance="medium")
    add_interaction_point(asset, "Event.Race.Grandstand.001", location=(6.0, 10.0, FLOOR_Z + 0.9))

    _box(asset, "VIPViewing", 9.0, 20.0, FLOOR_Z + 2.0, 4.0, 4.0, 2.0, mats["vip"], category="race_vip", importance="high")
    add_interaction_point(asset, "Event.Race.VIPViewing.001", location=(9.0, 20.0, FLOOR_Z + 3.0))

    # --- Vehicle service area, near the start ---
    _box(asset, "VehicleServiceArea", -10.0, -24.0, FLOOR_Z, 6.0, 4.0, 0.1, mats["bay"], category="race_service", importance="medium")
    add_interaction_point(asset, "Event.Race.ServiceArea.001", location=(-10.0, -24.0, FLOOR_Z + 0.1))

    # Shared Event Control Room was built once, in Phase 9a (per prompt
    # §29) -- this is this site's own interaction point near it, not a
    # second control room.
    add_interaction_point(asset, "Event.Race.ControlBooth.001", location=(0.0, 24.0, FLOOR_Z + 2.0))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    track_segments = [o for o in asset.geometry_objects if any(k in o.name for k in ("Straightaway", "MudSection", "NarrowSection", "TunnelTrack", "AlternateRoute"))]
    generate_box_collision(asset, "TrackSegments", track_segments)
    generate_box_collision(asset, "Hazards", [o for o in asset.geometry_objects if "Wreck" in o.name or "Obstacle" in o.name])
    generate_decimated_lod(asset, "ElevatedSection", next(o for o in asset.geometry_objects if "ElevatedSection" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_mad_max_race()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_09b_mad_max_race.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_09b_mad_max_race.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""KOBA CASINO & RESORT — Phase 5a: Arcade floor.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 5 / master prompt §10: the
arcade level's 10 named game zones (Shooting Gallery, Reaction Game,
Whack-a-Mole, Racing Game, Fishing Game, Boxing/Punch Machine, Claw
Machine, Memory Game, Target Gallery, High Score Challenge), each a
cabinet blockout with its own interaction point, plus a large central
leaderboard wall.

Sits on Floor2_Arcade's footprint from Phase 2 (same 40x30 tier band as
Floor1 -> 39x29 usable, floor surface at z=8.4 = Floor2's z_cursor=8.0 +
Phase 2's SLAB_THICKNESS=0.4).

Honest blockout limitations: every cabinet is one upright box + one
screen panel — a generic arcade-cabinet silhouette, not 10 visually
distinct game props. Queue/standing space is implied by cabinet
spacing, not modeled floor markings.

Run with:
  <blender> -b --python tests/koba_casino_05a_arcade.py
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
from materials.metal import bare_metal  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 8.4  # Floor2_Arcade's slab top surface (Phase 2: z_cursor=8.0 + SLAB_THICKNESS=0.4)

GAMES = [
    "ShootingGallery", "ReactionGame", "WhackAMole", "RacingGame", "FishingGame",
    "BoxingMachine", "ClawMachine", "MemoryGame", "TargetGallery",
]


def build_cabinet(asset, mats, game_name, idx, x, y):
    cabinet = create_box(
        make_name("mesh", asset.name, f"{game_name}_Cabinet"),
        width=0.9, depth=0.8, height=2.0, bevel_width=0.03, material=mats["cabinet"],
    )
    cabinet.location.x, cabinet.location.y, cabinet.location.z = x, y, FLOOR_Z
    apply_all_transforms(cabinet)
    asset.add_geometry(cabinet, metadata=for_static_prop(category="arcade_machine", importance="medium"))

    screen = create_panel(
        make_name("mesh", asset.name, f"{game_name}_Screen"),
        width=0.6, height=0.5, thickness=0.04, material=mats["screen"],
    )
    screen.location.x, screen.location.y, screen.location.z = x, y - 0.42, FLOOR_Z + 1.3
    apply_all_transforms(screen)
    asset.add_geometry(screen, metadata=for_static_prop(category="arcade_machine", importance="medium"))

    score_panel = create_panel(
        make_name("mesh", asset.name, f"{game_name}_ScoreDisplay"),
        width=0.5, height=0.2, thickness=0.03, material=mats["score"],
    )
    score_panel.location.x, score_panel.location.y, score_panel.location.z = x, y - 0.42, FLOOR_Z + 1.9
    apply_all_transforms(score_panel)
    asset.add_geometry(score_panel, metadata=for_static_prop(category="arcade_machine", importance="low"))

    add_interaction_point(asset, f"Arcade.{game_name}.{idx:03d}", location=(x, y - 0.5, FLOOR_Z + 1.0))


def build_leaderboard_wall(asset, mats, x_center, y, width=20.0, height=4.0):
    wall = create_box(
        make_name("mesh", asset.name, "Leaderboard_Wall"),
        width=width, depth=0.3, height=height, material=mats["leaderboard"],
    )
    wall.location.x, wall.location.y, wall.location.z = x_center, y, FLOOR_Z
    apply_all_transforms(wall)
    asset.add_geometry(wall, metadata=for_static_prop(category="arcade_display", importance="hero"))
    add_interaction_point(asset, "Arcade.HighScoreChallenge.001", location=(x_center, y + 0.3, FLOOR_Z + height / 2))
    return wall


def build_arcade(interactive=False):
    prepare_scene("KobaCasinoResort_Arcade", interactive)
    asset = Asset(name="KobaCasinoResort_Arcade", asset_type="monument")

    mats = {
        "cabinet": bare_metal(make_name("material", asset.name, "CabinetMetal")),
        "screen": emissive_sign(make_name("material", asset.name, "CabinetScreen"), color=(0.3, 0.9, 0.4)),
        "score": emissive_sign(make_name("material", asset.name, "ScoreDisplay"), color=(1.0, 0.3, 0.1), strength=2.0),
        "leaderboard": emissive_sign(make_name("material", asset.name, "LeaderboardWall"), color=(1.0, 0.85, 0.1), strength=2.5),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # 9 named cabinets along the back wall, evenly spaced across the floor's width.
    row_y = -12.0
    start_x, end_x = -17.0, 17.0
    step = (end_x - start_x) / (len(GAMES) - 1)
    for i, game in enumerate(GAMES, start=1):
        build_cabinet(asset, mats, game, 1, start_x + (i - 1) * step, row_y)

    # Central leaderboard wall ("High Score Challenge") facing the floor.
    build_leaderboard_wall(asset, mats, x_center=0.0, y=12.5)

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    cabinets = [o for o in asset.geometry_objects if "_Cabinet" in o.name]
    generate_box_collision(asset, "Cabinets", cabinets)
    generate_decimated_lod(asset, "LeaderboardWall", next(o for o in asset.geometry_objects if "Leaderboard_Wall" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_arcade()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_05a_arcade.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_05a_arcade.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

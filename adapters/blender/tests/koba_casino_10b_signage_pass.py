"""KOBA CASINO & RESORT — Phase 10b: Signage pass.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 10 / master prompt §30: the
wayfinding signage system — a main lobby directory board listing every
named zone (Casino/Hotel/Arcade/Nightclub/Pool/Restaurant/Bar/VIP/Event
Arena/Parking/Security), plus directional sign posts at junction
points, built LAST since signage only makes sense once the spaces it
labels actually exist (Phases 1-9).

Honest, real limitation: this pipeline has no text-rendering system
(no font/glyph geometry has ever been used in this project) — the
directory board and directional signs use distinct colored panels per
destination, not actual readable text. A real wayfinding pass with
legible signage is future work on top of this blockout, not claimed
as done here.

Run with:
  <blender> -b --python tests/koba_casino_10b_signage_pass.py
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
from materials.metal import galvanized_steel  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 0.1

# (zone label, color) -- the prompt's own §30 list, in order.
ZONES = [
    ("Casino", (0.9, 0.1, 0.1)),
    ("Hotel", (0.1, 0.4, 0.9)),
    ("Arcade", (0.3, 0.9, 0.4)),
    ("Nightclub", (0.6, 0.1, 0.9)),
    ("Pool", (0.1, 0.7, 0.8)),
    ("Restaurant", (0.9, 0.5, 0.1)),
    ("Bar", (0.6, 0.4, 0.1)),
    ("VIP", (0.9, 0.75, 0.1)),
    ("EventArena", (0.9, 0.2, 0.5)),
    ("Parking", (0.5, 0.5, 0.5)),
    ("Security", (0.2, 0.2, 0.25)),
]


def build_signage_pass(interactive=False):
    prepare_scene("KobaCasinoResort_SignagePass", interactive)
    asset = Asset(name="KobaCasinoResort_SignagePass", asset_type="monument")

    mats = {"post": galvanized_steel(make_name("material", asset.name, "SignPost"))}
    for label, color in ZONES:
        mats[label] = emissive_sign(make_name("material", asset.name, f"Directory_{label}"), color=color, strength=1.5)
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Main lobby directory board: one panel per named zone, stacked ---
    board_backing = create_panel(make_name("mesh", asset.name, "DirectoryBoard_Backing"), width=3.0, height=len(ZONES) * 0.5 + 0.4, thickness=0.1, material=mats["post"])
    board_backing.location.x, board_backing.location.y, board_backing.location.z = 0.0, 0.0, 1.0 + (len(ZONES) * 0.5) / 2
    apply_all_transforms(board_backing)
    asset.add_geometry(board_backing, metadata=for_static_prop(category="signage_board", importance="hero"))

    for i, (label, _color) in enumerate(ZONES):
        entry = create_panel(make_name("mesh", asset.name, f"DirectoryEntry_{label}"), width=2.6, height=0.4, thickness=0.03, material=mats[label])
        entry.location.x, entry.location.y, entry.location.z = 0.0, 0.08, 1.2 + i * 0.5
        apply_all_transforms(entry)
        asset.add_geometry(entry, metadata=for_static_prop(category="signage_directory_entry", importance="medium"))
        add_interaction_point(asset, f"Signage.Directory.{label}.001", location=(0.0, 0.1, 1.2 + i * 0.5))

    # --- Directional sign posts at 4 junction points ---
    junctions = [
        ("Junction001", (-10.0, 0.0), ["Casino", "Hotel"]),
        ("Junction002", (10.0, 0.0), ["Arcade", "Nightclub", "Pool"]),
        ("Junction003", (0.0, 10.0), ["Restaurant", "Bar", "VIP"]),
        ("Junction004", (0.0, -10.0), ["EventArena", "Parking", "Security"]),
    ]
    for junction_name, (jx, jy), labels in junctions:
        pole = create_cylinder(make_name("mesh", asset.name, f"{junction_name}_Pole"), radius=0.1, depth=2.5, material=mats["post"])
        pole.location.x, pole.location.y, pole.location.z = jx, jy, FLOOR_Z
        apply_all_transforms(pole)
        asset.add_geometry(pole, metadata=for_static_prop(category="signage_post", importance="medium"))

        for j, label in enumerate(labels):
            arrow = create_box(make_name("mesh", asset.name, f"{junction_name}_Arrow_{label}"), width=0.8, depth=0.05, height=0.3, material=mats[label])
            arrow.location.x, arrow.location.y, arrow.location.z = jx, jy, FLOOR_Z + 2.0 - j * 0.35
            apply_all_transforms(arrow)
            asset.add_geometry(arrow, metadata=for_static_prop(category="signage_directional", importance="medium"))
        add_interaction_point(asset, f"Signage.{junction_name}.001", location=(jx, jy, FLOOR_Z + 2.0))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    posts = [o for o in asset.geometry_objects if "_Pole" in o.name]
    generate_box_collision(asset, "SignPosts", posts)
    generate_decimated_lod(asset, "DirectoryBoard", board_backing, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_signage_pass()

    result = validate_asset(asset, poly_budget=100000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="front")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_10b_signage_pass.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_10b_signage_pass.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

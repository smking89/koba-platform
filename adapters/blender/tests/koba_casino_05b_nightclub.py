"""KOBA CASINO & RESORT — Phase 5b: Nightclub.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 5 / master prompt §11: dance
floor, DJ booth + stage, lighting rig/speaker array placeholders, bar,
booth seating, VIP balcony/lounge, backstage area.

Sits on Floor3_Nightclub's footprint from Phase 2 (same 40x30 tier band
as Floor1/Floor2 -> 39x29 usable, floor surface at z=13.4 = Floor3's
z_cursor=13.0 + Phase 2's SLAB_THICKNESS=0.4).

Honest blockout limitations: lighting/speaker placeholders are static
boxes, not real dynamic lights or audio-zone logic (prompt §35/§42 are
their own later concerns). No bathrooms modeled. VIP balcony is a
raised dais, not a separate enclosed room.

Run with:
  <blender> -b --python tests/koba_casino_05b_nightclub.py
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
from materials.metal import bare_metal, galvanized_steel  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.plastic import glossy_plastic  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 13.4  # Floor3_Nightclub's slab top surface (Phase 2: z_cursor=13.0 + SLAB_THICKNESS=0.4)


def _box(asset, part, x, y, z, w, d, h, mat, category="nightclub_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_nightclub(interactive=False):
    prepare_scene("KobaCasinoResort_Nightclub", interactive)
    asset = Asset(name="KobaCasinoResort_Nightclub", asset_type="monument")

    mats = {
        "dance_floor": emissive_sign(make_name("material", asset.name, "DanceFloor"), color=(0.6, 0.1, 0.9), strength=1.5),
        "booth_base": carved_stone(make_name("material", asset.name, "DJBoothBase"), color=(0.2, 0.2, 0.25)),
        "console": bare_metal(make_name("material", asset.name, "DJConsole")),
        "speaker": bare_metal(make_name("material", asset.name, "Speaker")),
        "bar_counter": carved_stone(make_name("material", asset.name, "BarCounter"), color=(0.3, 0.25, 0.22)),
        "booth_seat": glossy_plastic(make_name("material", asset.name, "BoothSeat"), color=(0.5, 0.05, 0.1), roughness=0.5),
        "vip_dais": carved_stone(make_name("material", asset.name, "VIPDais"), color=(0.4, 0.3, 0.1)),
        "backstage": galvanized_steel(make_name("material", asset.name, "BackstageWall")),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- Dance floor, center of the room ---
    _box(asset, "DanceFloor", 0.0, -2.0, FLOOR_Z, 14.0, 12.0, 0.15, mats["dance_floor"],
         category="nightclub_floor", importance="hero")
    add_interaction_point(asset, "Nightclub.DanceFloor.001", location=(0.0, -2.0, FLOOR_Z + 0.15))

    # --- DJ booth: elevated platform + console, against the north wall ---
    booth = _box(asset, "DJBooth_Platform", 0.0, -12.0, FLOOR_Z, 5.0, 2.5, 0.8, mats["booth_base"],
                 category="nightclub_stage", importance="hero")
    _box(asset, "DJBooth_Console", 0.0, -12.0, FLOOR_Z + 0.8, 3.0, 0.8, 1.0, mats["console"],
         category="nightclub_stage", importance="hero")
    add_interaction_point(asset, "Nightclub.DJBooth.001", location=(0.0, -12.0, FLOOR_Z + 1.8))
    add_interaction_point(asset, "Nightclub.LightingController.001", location=(1.8, -12.0, FLOOR_Z + 1.8))
    del booth

    # --- Speaker stacks flanking the DJ booth ---
    for sx in (-4.0, 4.0):
        _box(asset, f"Speaker_{sx:+.0f}", sx, -11.0, FLOOR_Z, 1.0, 1.0, 2.2, mats["speaker"],
             category="nightclub_audio", importance="medium")

    # --- Main bar, opposite the DJ booth ---
    _box(asset, "MainBar_Counter", 0.0, 12.0, FLOOR_Z, 8.0, 1.2, 1.1, mats["bar_counter"],
         category="nightclub_bar", importance="high")
    add_interaction_point(asset, "Nightclub.Bar.001", location=(0.0, 12.0, FLOOR_Z + 1.1))

    # --- Booth seating along both side walls ---
    booth_idx = 1
    for side in (-1, 1):
        for row in range(3):
            bx = side * 16.0
            by = -8.0 + row * 6.0
            _box(asset, f"Booth{booth_idx:03d}_Seat", bx, by, FLOOR_Z, 2.0, 1.4, 0.5, mats["booth_seat"],
                 category="nightclub_seating", importance="low")
            add_interaction_point(asset, f"Nightclub.VIPBooth.{booth_idx:03d}", location=(bx, by, FLOOR_Z + 0.5))
            booth_idx += 1

    # --- VIP balcony: raised dais in the back corner ---
    _box(asset, "VIPBalcony_Dais", 14.0, 12.0, FLOOR_Z, 8.0, 6.0, 1.0, mats["vip_dais"],
         category="nightclub_vip", importance="high")
    add_interaction_point(asset, "Nightclub.VIPLounge.001", location=(14.0, 12.0, FLOOR_Z + 1.0))

    # --- Backstage/service area marker, behind the DJ booth ---
    _box(asset, "Backstage_Wall", 0.0, -14.0, FLOOR_Z, 6.0, 0.3, 2.5, mats["backstage"],
         category="nightclub_service", importance="low")
    add_interaction_point(asset, "Nightclub.Backstage.001", location=(0.0, -14.3, FLOOR_Z + 1.0))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    generate_box_collision(asset, "Stage", [o for o in asset.geometry_objects if "DJBooth" in o.name or "Bar_Counter" in o.name])
    generate_decimated_lod(asset, "VIPBalcony", next(o for o in asset.geometry_objects if "VIPBalcony_Dais" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_nightclub()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_05b_nightclub.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_05b_nightclub.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

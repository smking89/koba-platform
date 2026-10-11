"""KOBA CASINO & RESORT — Phase 8: Rooftop.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 8 / master prompt §24:
rooftop equipment (HVAC, generators, communications equipment, security
equipment, maintenance access), an observation area, and the prompt's
own OPTIONAL helipad + VIP rooftop area — built here since they're
cheap blockout value, not because the prompt requires them.

Sits on the Rooftop level's footprint from Phase 2 (tier2 band -> 23x17
usable, floor surface at z=45.4 = Rooftop's z_cursor=45.0 + Phase 2's
SLAB_THICKNESS=0.4) — below Phase 1's TowerCrown cap at z=50, not
conflicting with it.

Honest blockout limitations: the comms dish/camera are simple
primitive assemblies, not real antenna/camera models. No guardrail
around the roof edge itself (only the observation area has one).

Run with:
  <blender> -b --python tests/koba_casino_08_rooftop.py
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
from geometry.primitives import create_box, create_cylinder  # noqa: E402
from materials.metal import galvanized_steel, bare_metal, rusted_metal  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 45.4  # Rooftop's slab top surface (Phase 2: z_cursor=45.0 + SLAB_THICKNESS=0.4)


def _box(asset, part, x, y, z, w, d, h, mat, category="rooftop_equipment", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_rooftop(interactive=False):
    prepare_scene("KobaCasinoResort_Rooftop", interactive)
    asset = Asset(name="KobaCasinoResort_Rooftop", asset_type="monument")

    mats = {
        "hvac": galvanized_steel(make_name("material", asset.name, "HVACUnit")),
        "generator": rusted_metal(make_name("material", asset.name, "Generator"), rust_amount=0.2),
        "antenna": bare_metal(make_name("material", asset.name, "AntennaMast")),
        "dish": galvanized_steel(make_name("material", asset.name, "CommsDish")),
        "camera": bare_metal(make_name("material", asset.name, "SecurityCamera")),
        "hatch": rusted_metal(make_name("material", asset.name, "MaintenanceHatch"), rust_amount=0.3),
        "deck": carved_stone(make_name("material", asset.name, "ObservationDeck"), color=(0.5, 0.48, 0.45)),
        "rail": galvanized_steel(make_name("material", asset.name, "ObservationRail")),
        "helipad": carved_stone(make_name("material", asset.name, "HelipadSurface"), color=(0.15, 0.15, 0.16)),
        "helipad_marking": emissive_sign(make_name("material", asset.name, "HelipadMarking"), color=(1.0, 0.85, 0.1), strength=2.0),
        "vip_dais": carved_stone(make_name("material", asset.name, "VIPRooftopDais"), color=(0.5, 0.4, 0.15)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # --- HVAC units, a row of 4 ---
    for i, x in enumerate((-9.0, -6.0, -3.0, 0.0), start=1):
        _box(asset, f"HVAC{i:03d}", x, -6.0, FLOOR_Z, 1.5, 1.5, 1.2, mats["hvac"], category="rooftop_hvac")
        add_interaction_point(asset, f"Rooftop.HVAC.{i:03d}", location=(x, -6.0, FLOOR_Z + 1.2))

    # --- Generator ---
    _box(asset, "Generator001", 4.0, -6.0, FLOOR_Z, 3.0, 2.0, 1.8, mats["generator"], category="rooftop_power", importance="high")
    add_interaction_point(asset, "Rooftop.Generator.001", location=(4.0, -6.0, FLOOR_Z + 1.8))

    # --- Communications array: mast + dish ---
    mast = create_cylinder(make_name("mesh", asset.name, "CommsMast"), radius=0.25, depth=4.0, material=mats["antenna"])
    mast.location.x, mast.location.y, mast.location.z = 9.0, -6.0, FLOOR_Z
    apply_all_transforms(mast)
    asset.add_geometry(mast, metadata=for_static_prop(category="rooftop_comms", importance="high"))

    dish = create_cylinder(make_name("mesh", asset.name, "CommsDish"), radius=0.7, depth=0.12, material=mats["dish"])
    dish.rotation_euler.x = 0.6
    dish.location.x, dish.location.y, dish.location.z = 9.0, -5.6, FLOOR_Z + 3.5
    apply_all_transforms(dish)
    asset.add_geometry(dish, metadata=for_static_prop(category="rooftop_comms", importance="high"))
    add_interaction_point(asset, "Rooftop.CommsArray.001", location=(9.0, -6.0, FLOOR_Z + 4.0))

    # --- Security camera post ---
    cam_pole = create_cylinder(make_name("mesh", asset.name, "CameraPole"), radius=0.08, depth=2.5, material=mats["camera"])
    cam_pole.location.x, cam_pole.location.y, cam_pole.location.z = -9.0, 0.0, FLOOR_Z
    apply_all_transforms(cam_pole)
    asset.add_geometry(cam_pole, metadata=for_static_prop(category="rooftop_security", importance="medium"))
    _box(asset, "CameraHead", -9.0, 0.2, FLOOR_Z + 2.5, 0.25, 0.4, 0.2, mats["camera"], category="rooftop_security")
    add_interaction_point(asset, "Rooftop.SecurityCamera.001", location=(-9.0, 0.0, FLOOR_Z + 2.5))

    # --- Maintenance access hatch ---
    _box(asset, "MaintenanceHatch001", -5.0, 0.0, FLOOR_Z, 1.2, 1.2, 0.1, mats["hatch"], category="rooftop_maintenance")
    add_interaction_point(asset, "Rooftop.MaintenanceAccess.001", location=(-5.0, 0.0, FLOOR_Z + 0.1))

    # --- Observation area: raised deck + rail ---
    _box(asset, "ObservationDeck", 0.0, 4.0, FLOOR_Z, 5.0, 4.0, 0.3, mats["deck"], category="rooftop_observation", importance="high")
    _box(asset, "ObservationRail", 0.0, 6.0, FLOOR_Z + 0.3, 5.0, 0.1, 0.9, mats["rail"], category="rooftop_observation")
    add_interaction_point(asset, "Rooftop.ObservationArea.001", location=(0.0, 4.0, FLOOR_Z + 0.3))

    # --- Optional: helipad (prompt's own "optional") ---
    pad = create_cylinder(make_name("mesh", asset.name, "HelipadSurface"), radius=4.0, depth=0.1, material=mats["helipad"])
    pad.location.x, pad.location.y, pad.location.z = 7.0, 4.0, FLOOR_Z
    apply_all_transforms(pad)
    asset.add_geometry(pad, metadata=for_static_prop(category="rooftop_helipad", importance="medium"))
    for i, (mw, mh, mx, my) in enumerate(((2.0, 0.4, -0.8, 0.0), (2.0, 0.4, 0.8, 0.0), (0.4, 2.0, 0.0, 0.0))):
        marking = create_box(make_name("mesh", asset.name, f"HelipadMarking{i}"), width=mw, depth=mh, height=0.02, material=mats["helipad_marking"])
        marking.location.x, marking.location.y, marking.location.z = 7.0 + mx, 4.0 + my, FLOOR_Z + 0.1
        apply_all_transforms(marking)
        asset.add_geometry(marking, metadata=for_static_prop(category="rooftop_helipad", importance="low"))
    add_interaction_point(asset, "Rooftop.Helipad.001", location=(7.0, 4.0, FLOOR_Z + 0.1))

    # --- Optional: VIP rooftop area ---
    _box(asset, "VIPRooftopDais", -9.0, 6.0, FLOOR_Z, 4.0, 3.0, 0.5, mats["vip_dais"], category="rooftop_vip", importance="high")
    add_interaction_point(asset, "Rooftop.VIPArea.001", location=(-9.0, 6.0, FLOOR_Z + 0.5))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    hvac_units = [o for o in asset.geometry_objects if "HVAC" in o.name]
    generate_box_collision(asset, "HVACUnits", hvac_units)
    generate_box_collision(asset, "BigStructures", [o for o in asset.geometry_objects if "Generator" in o.name or "ObservationDeck" in o.name])
    generate_decimated_lod(asset, "VIPRooftopDais", next(o for o in asset.geometry_objects if "VIPRooftopDais" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_rooftop()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_08_rooftop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_08_rooftop.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

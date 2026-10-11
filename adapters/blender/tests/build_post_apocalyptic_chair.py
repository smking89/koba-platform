"""A real post-apocalyptic torn leather armchair — a themed deliverable
built entirely from this project's existing procedural toolkit
(geometry.primitives, geometry.assemblies.furniture.hardware's turned
legs, geometry.detailing's inset panels, materials.pbr_library's real
downloaded leather/metal textures). No new asset-type abstraction added
to the generic furniture library — this composes existing real building
blocks into one specific themed prop, same pattern as every KOBA CASINO
& RESORT showcase script.

"Torn and worn" is represented honestly within this pipeline's real
capabilities:
  - a genuine GAP in the backrest (two separate leather panels instead
    of one, with real empty space between them) with a real exposed
    "foam stuffing" box visible through the gap
  - a scavenged sheet-metal "repair patch" bridging part of the gap
  - rusted (not clean) metal for every piece of hardware: legs, rivets
  - real array-distributed rivets along the arms, scavenger-repair look

No organic rip/fray geometry is attempted (this pipeline has no cloth/
tear simulation) — the "torn" read comes from a real structural gap +
mismatched repair patch, not a texture trick.

Run with:
  <blender> -b --python tests/build_post_apocalyptic_chair.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.entity_metadata import for_static_prop  # noqa: E402
from materials.pbr_library import get_pbr_material  # noqa: E402
from materials.metal import rusted_metal  # noqa: E402
from geometry.primitives import create_box  # noqa: E402
from geometry.assemblies.furniture.hardware import build_turned_leg, build_stud_source, turned_leg_profile  # noqa: E402
from geometry.profiles import lathe_profile  # noqa: E402
from geometry.detailing import inset_panel, find_face_by_normal, distribute_array_detail  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402


def build_post_apocalyptic_chair(interactive=False):
    prepare_scene("PostApocalypticChair", interactive)
    asset = Asset(name="PostApocalypticChair", asset_type="prop")

    leather = get_pbr_material("leather", make_name("material", asset.name, "WornLeather"))
    rusted_leg_mat = rusted_metal(make_name("material", asset.name, "RustedLegMetal"), rust_amount=0.65)
    rusted_rivet_mat = rusted_metal(make_name("material", asset.name, "RustedRivet"), rust_amount=0.75)
    patch_mat = rusted_metal(make_name("material", asset.name, "ScavengedPatch"), rust_amount=0.5)
    foam_mat = rusted_metal(make_name("material", asset.name, "ExposedFoam"), rust_amount=0.1)
    for mat in (leather, rusted_leg_mat, rusted_rivet_mat, patch_mat, foam_mat):
        asset.register_material(mat.name)

    width, depth = 0.85, 0.85
    leg_height = 0.22

    # --- 4 rusted, slightly mismatched turned legs (scavenged look: not
    #     a matched factory set) ---
    for i, (lx, ly, scale) in enumerate((
        (-1, -1, 1.0), (1, -1, 0.92), (-1, 1, 1.05), (1, 1, 0.97),
    )):
        profile = turned_leg_profile(leg_height, 0.03 * scale)
        leg = lathe_profile(make_name("mesh", asset.name, f"Leg{i:03d}"), profile, steps=10, material=rusted_leg_mat)
        leg.location.x = lx * (width / 2 - 0.08)
        leg.location.y = ly * (depth / 2 - 0.08)
        leg.location.z = 0.0
        apply_all_transforms(leg)
        asset.add_geometry(leg, metadata=for_static_prop(category="chair_leg", importance="medium"))

    # --- seat base, worn leather, real tufted inset ---
    seat_height = 0.42
    base = create_box(make_name("mesh", asset.name, "SeatBase"), width=width, depth=depth, height=seat_height, bevel_width=0.025, material=leather)
    base.location.x, base.location.y, base.location.z = 0.0, 0.0, leg_height
    apply_all_transforms(base)
    base_top = find_face_by_normal(base, normal_axis="z", sign=1)
    inset_panel(base, base_top, thickness=0.07, depth=-0.015)
    asset.add_geometry(base, metadata=for_static_prop(category="chair_seat", importance="high"))

    seat_top_z = leg_height + seat_height

    # --- backrest: TWO separate leather panels with a real gap between
    #     them (the "torn open" structural read) ---
    backrest_height = 0.55
    backrest_depth = 0.1
    gap_width = 0.14
    panel_width = (width - gap_width) / 2
    back_y = -depth / 2 + 0.05
    back_z = seat_top_z + backrest_height / 2

    panels = {}
    for side, ox in (("left", -1), ("right", 1)):
        panel = create_box(make_name("mesh", asset.name, f"Backrest_{side}"), width=panel_width, depth=backrest_depth, height=backrest_height, bevel_width=0.02, material=leather)
        panel.location.x = ox * (gap_width / 2 + panel_width / 2)
        panel.location.y, panel.location.z = back_y, back_z
        apply_all_transforms(panel)
        front_face = find_face_by_normal(panel, normal_axis="y", sign=-1)
        inset_panel(panel, front_face, thickness=0.04, depth=-0.012)
        asset.add_geometry(panel, metadata=for_static_prop(category="chair_backrest", importance="high"))
        panels[side] = panel

    # --- exposed foam stuffing, visible through the gap ---
    foam = create_box(make_name("mesh", asset.name, "ExposedFoam"), width=gap_width * 0.8, depth=backrest_depth * 0.7, height=backrest_height * 0.55, bevel_width=0.01, material=foam_mat)
    foam.location.x, foam.location.y, foam.location.z = 0.0, back_y + 0.01, back_z - backrest_height * 0.05
    apply_all_transforms(foam)
    asset.add_geometry(foam, metadata=for_static_prop(category="chair_damage", importance="medium"))

    # --- a crude scavenged sheet-metal patch, bridging part of the gap
    #     (classic post-apoc "someone repaired this" detail) ---
    patch = create_box(make_name("mesh", asset.name, "RepairPatch"), width=gap_width * 1.6, depth=0.015, height=backrest_height * 0.3, bevel_width=0.005, material=patch_mat)
    patch.rotation_euler.z = 0.08  # slightly crooked, hand-applied look
    patch.location.x, patch.location.y, patch.location.z = 0.01, back_y - 0.04, back_z + backrest_height * 0.12
    apply_all_transforms(patch)
    asset.add_geometry(patch, metadata=for_static_prop(category="chair_damage", importance="medium"))

    # a couple of crude rivets holding the patch on
    patch_rivet_source = build_stud_source(asset, "PatchRivet", radius=0.01, height=0.012, material=rusted_rivet_mat)
    distribute_array_detail(
        asset, "PatchRivet", patch_rivet_source,
        start=(-gap_width * 0.5, back_y - 0.05, back_z + backrest_height * 0.12),
        end=(gap_width * 0.5, back_y - 0.05, back_z + backrest_height * 0.12),
        count=3, importance="low",
    )

    # --- arms, worn leather with inset + a row of rusted rivets along each ---
    arm_height = 0.22
    arm_width = 0.1
    rivet_source = build_stud_source(asset, "ArmRivet", radius=0.012, height=0.015, material=rusted_rivet_mat)
    for side, ox in (("left", -1), ("right", 1)):
        arm = create_box(make_name("mesh", asset.name, f"Arm_{side}"), width=arm_width, depth=depth * 0.9, height=arm_height, bevel_width=0.02, material=leather)
        arm.location.x = ox * (width / 2 - arm_width / 2 + 0.02)
        arm.location.y, arm.location.z = 0.0, seat_top_z + arm_height / 2
        apply_all_transforms(arm)
        arm_top = find_face_by_normal(arm, normal_axis="z", sign=1)
        inset_panel(arm, arm_top, thickness=0.015, depth=-0.006)
        asset.add_geometry(arm, metadata=for_static_prop(category="chair_arm", importance="medium"))

        distribute_array_detail(
            asset, f"ArmRivet_{side}", rivet_source,
            start=(arm.location.x, -depth * 0.35, seat_top_z + arm_height + 0.005),
            end=(arm.location.x, depth * 0.35, seat_top_z + arm_height + 0.005),
            count=4, importance="low",
        )

    collidable = [o for o in asset.geometry_objects if o.type == "MESH"]
    generate_box_collision(asset, "Chair", collidable[:20])
    generate_decimated_lod(asset, "SeatBase", base, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_post_apocalyptic_chair()

    result = validate_asset(asset, poly_budget=80000)
    print(result.report())

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "post_apocalyptic_chair.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="post_apocalyptic_chair.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

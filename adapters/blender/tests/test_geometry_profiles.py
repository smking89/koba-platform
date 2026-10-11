"""Test for geometry/profiles.py (lathe + profile-sweep) and
geometry/detailing.py (inset panels + array-based detail hooks) — the
2026-10-01 "escape the blocky barrier without sculpting" additions.

Builds, for real:
  - a lathed chair-leg profile (bmesh.ops.spin)
  - a swept console-bracket profile along a 3-point path (bmesh.ops.bridge_loops)
  - a box with a real recessed inset panel (cushion-indent technique)
  - a box with a real raised inset panel (rivet-head technique)
  - a row of 6 real rivet instances distributed along an edge (shared-mesh instancing)

...then runs the whole scene through the real validate_asset path and
reports real entity/triangle/collision/LOD numbers.

Run with:
  <blender> -b --python tests/test_geometry_profiles.py
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
from geometry.primitives import create_box  # noqa: E402
from geometry.profiles import lathe_profile, extrude_profile_along_path  # noqa: E402
from geometry.detailing import inset_panel, distribute_array_detail  # noqa: E402
from geometry.instancing import count_unique_meshes  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402


def build_profiles_showcase(interactive=False):
    prepare_scene("GeometryProfilesShowcase", interactive)
    asset = Asset(name="GeometryProfilesShowcase", asset_type="monument")

    wood = get_pbr_material("wood", make_name("material", asset.name, "PBRWood"))
    metal = get_pbr_material("metal", make_name("material", asset.name, "PBRMetal"))
    for mat in (wood, metal):
        asset.register_material(mat.name)

    counts = {}

    # --- 1. Lathed chair leg: a real turned-leg silhouette, not a bare cylinder ---
    leg_profile = [(0.035, 0.0), (0.028, 0.08), (0.045, 0.14), (0.022, 0.22), (0.03, 0.35), (0.03, 0.42)]
    leg = lathe_profile(make_name("mesh", asset.name, "ChairLeg"), leg_profile, steps=14, material=wood)
    leg.location.x, leg.location.y, leg.location.z = -3.0, 0.0, 0.0
    apply_all_transforms(leg)
    asset.add_geometry(leg, metadata=for_static_prop(category="lathed_leg", importance="medium"))
    counts["lathed_chair_leg_polys"] = len(leg.data.polygons)

    # --- 2. Swept console bracket: a real custom cross-section along a bent path ---
    bracket_profile = [(-0.04, 0.0), (0.04, 0.0), (0.04, 0.06), (-0.04, 0.06)]
    bracket_path = [(0.0, 0.0, 0.0), (0.0, 0.15, 0.0), (0.0, 0.22, 0.12), (0.0, 0.22, 0.3)]
    bracket = extrude_profile_along_path(make_name("mesh", asset.name, "ConsoleBracket"), bracket_profile, bracket_path, material=metal)
    bracket.location.x, bracket.location.y, bracket.location.z = 0.0, 0.0, 0.0
    apply_all_transforms(bracket)
    asset.add_geometry(bracket, metadata=for_static_prop(category="swept_bracket", importance="medium"))
    counts["swept_console_bracket_polys"] = len(bracket.data.polygons)

    # --- 3. Box with a real recessed inset panel (cushion-indent technique) ---
    cushion_box = create_box(make_name("mesh", asset.name, "CushionPanelBox"), width=1.0, depth=1.0, height=0.3, material=wood)
    cushion_box.location.x, cushion_box.location.y, cushion_box.location.z = 3.0, 0.0, 0.0
    apply_all_transforms(cushion_box)
    polys_before = len(cushion_box.data.polygons)
    top_face_index = max(range(len(cushion_box.data.polygons)),
                          key=lambda i: cushion_box.data.polygons[i].center.z)
    new_faces = inset_panel(cushion_box, top_face_index, thickness=0.12, depth=-0.04)
    asset.add_geometry(cushion_box, metadata=for_static_prop(category="inset_panel", importance="low"))
    counts["cushion_inset_new_faces"] = new_faces
    counts["cushion_box_polys_before"] = polys_before
    counts["cushion_box_polys_after"] = len(cushion_box.data.polygons)

    # --- 4. Box with a real raised inset panel (rivet-head boss technique) ---
    boss_box = create_box(make_name("mesh", asset.name, "RivetHeadBox"), width=0.3, depth=0.3, height=0.05, material=metal)
    boss_box.location.x, boss_box.location.y, boss_box.location.z = 6.0, 0.0, 0.0
    apply_all_transforms(boss_box)
    top_face_index2 = max(range(len(boss_box.data.polygons)), key=lambda i: boss_box.data.polygons[i].center.z)
    inset_panel(boss_box, top_face_index2, thickness=0.05, depth=0.02)
    asset.add_geometry(boss_box, metadata=for_static_prop(category="raised_boss", importance="low"))

    # --- 5. Array-based detail hook: a row of real rivet instances ---
    rivet_source = create_box(make_name("mesh", asset.name, "RivetSource"), width=0.04, depth=0.04, height=0.02, material=metal)
    rivet_source.location.x, rivet_source.location.y, rivet_source.location.z = 8.0, -0.3, 0.1
    apply_all_transforms(rivet_source)
    asset.add_geometry(rivet_source, metadata=for_static_prop(category="rivet", importance="low"))
    rivets = distribute_array_detail(asset, "SeamRivet", rivet_source,
                                      start=(7.5, 0.3, 0.1), end=(8.5, 0.3, 0.1), count=6)
    counts["rivet_instances_created"] = len(rivets)

    generate_box_collision(asset, "Showcase", [leg, bracket, cushion_box, boss_box])
    generate_decimated_lod(asset, "Leg", leg, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, counts


def main():
    asset, counts = build_profiles_showcase()

    result = validate_asset(asset, poly_budget=50000)
    print(result.report())
    print("\nReal facts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  total objects: {len(asset.geometry_objects)}")
    print(f"  real unique meshes: {count_unique_meshes(asset.geometry_objects)}")

    assert counts["lathed_chair_leg_polys"] > 0, "lathe must produce real faces"
    assert counts["swept_console_bracket_polys"] > 0, "sweep must produce real faces"
    assert counts["cushion_box_polys_after"] > counts["cushion_box_polys_before"], \
        "inset+extrude must add real new faces to the mesh, not fake a panel"
    assert counts["rivet_instances_created"] == 6, "array detail must place exactly the requested count"
    assert count_unique_meshes(asset.geometry_objects) < len(asset.geometry_objects), \
        "the rivet row must be real shared-mesh instances, not 6 unique meshes"
    print("\nAll real profile/detailing assertions PASSED.")

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test_geometry_profiles.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test_geometry_profiles.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

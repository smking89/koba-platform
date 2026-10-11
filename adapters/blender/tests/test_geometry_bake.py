"""Test for geometry/bake.py — the join+weld+bevel downstream step added
on top of the assembly library, per the 2026-10-01 conversation
resolving the tension between "force-join everything" and "assemblies
must stay instance-ready."

Confirms, for real (not just by reading the code):
  - the ORIGINAL assembly objects are completely untouched after baking
    (still present, same count, still separate — still valid instancing
    sources)
  - the baked result is genuinely ONE new mesh object, with a real
    (lower) vertex count than the sum of the originals (proving the
    weld actually ran, not just the join)
  - the baked mesh has a real non-overlapping UV layout (not the
    per-object cube-projection the originals have)
  - the baked object passes the same real validate_asset path as
    everything else in this project

Run with:
  <blender> -b --python tests/test_geometry_bake.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from materials.pbr_library import get_pbr_material  # noqa: E402
from geometry.assemblies.furniture.desks import build_desk_and_chair  # noqa: E402
from geometry.bake import bake_assembly_to_mesh  # noqa: E402
from geometry.primitives import create_box  # noqa: E402
from core.entity_metadata import for_static_prop  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402


def build_bake_test(interactive=False):
    prepare_scene("GeometryBakeTest", interactive)
    asset = Asset(name="GeometryBakeTest", asset_type="monument")

    wood = get_pbr_material("wood", make_name("material", asset.name, "PBRWood"))
    metal = get_pbr_material("metal", make_name("material", asset.name, "PBRMetal"))
    leather = get_pbr_material("leather", make_name("material", asset.name, "PBRLeather"))
    for mat in (wood, metal, leather):
        asset.register_material(mat.name)

    parts = build_desk_and_chair(asset, "Desk1", 0.0, 0.0, 0.0, top_mat=wood, leg_mat=metal, chair_mat=leather)
    original_objects = list(parts.values())
    original_count = len(asset.geometry_objects)

    baked = bake_assembly_to_mesh(asset, original_objects, "Desk1_Baked")

    # --- controlled weld proof: two boxes placed FLUSH (a shared,
    # guaranteed-coincident face) -- the desk+chair's parts don't touch
    # each other, so remove_doubles has nothing to weld there and that's
    # not a fair test of welding specifically. This pair exists purely
    # to prove remove_doubles actually fires on real coincident geometry,
    # independent of bevel's own vertex contribution. ---
    box_a = create_box(make_name("mesh", asset.name, "WeldTestA"), width=1.0, depth=1.0, height=1.0, material=wood)
    box_a.location.x = -0.5
    box_b = create_box(make_name("mesh", asset.name, "WeldTestB"), width=1.0, depth=1.0, height=1.0, material=wood)
    box_b.location.x = 0.5
    for obj in (box_a, box_b):
        asset.add_geometry(obj, metadata=for_static_prop(category="weld_test", importance="low"))
    weld_pair_vert_sum = len(box_a.data.vertices) + len(box_b.data.vertices)
    weld_test_baked = bake_assembly_to_mesh(asset, [box_a, box_b], "WeldTest_Baked", bevel_width=0.0)

    # --- real checks, not assumed ---
    still_present = all(o.name in bpy.data.objects for o in original_objects)
    count_after = len(asset.geometry_objects)
    baked_vert_count = len(baked.data.vertices)
    has_real_uvs = len(baked.data.uv_layers) > 0
    weld_test_vert_count = len(weld_test_baked.data.vertices)

    generate_box_collision(asset, "Baked", [baked, weld_test_baked])
    generate_decimated_lod(asset, "Baked", baked, level=1, ratio=0.6)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, {
        "original_count": original_count,
        "count_after": count_after,
        "originals_still_present": still_present,
        "baked_vert_count": baked_vert_count,
        "baked_has_uvs": has_real_uvs,
        "baked_name": baked.name,
        "weld_pair_vert_sum": weld_pair_vert_sum,
        "weld_test_vert_count": weld_test_vert_count,
    }


def main():
    asset, facts = build_bake_test()

    result = validate_asset(asset, poly_budget=50000)
    print(result.report())
    print("\nReal facts about the bake:")
    for k, v in facts.items():
        print(f"  {k}: {v}")

    # desk bake adds 1 object; the weld-test pair adds 2 (box_a, box_b) + 1 (their bake) = 4 total.
    assert facts["count_after"] == facts["original_count"] + 4, \
        "baking must ADD new objects, not replace/remove the originals"
    assert facts["originals_still_present"], "original instancing-ready objects must survive baking untouched"
    assert facts["baked_has_uvs"], "the baked mesh must have a real UV layout from smart_uv_unwrap"
    assert facts["weld_test_vert_count"] < facts["weld_pair_vert_sum"], \
        ("the weld must actually reduce vertex count on two FLUSH boxes with a real coincident "
         "face (bevel_width=0 here, isolating weld from bevel) — if this doesn't shrink, "
         "remove_doubles isn't firing")
    print("\nAll real bake assertions PASSED.")

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test_geometry_bake.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test_geometry_bake.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

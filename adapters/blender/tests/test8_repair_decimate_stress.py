"""TEST 8: Decimate-repair stress fixture.

A single high-poly icosphere, deliberately over 240fps_esports' real
max_triangles=250000 budget (and nothing else — entity_count=1,
unique_meshes=1, well within budget), used to exercise
repair/repair_engine.py's decimate-based repair strategy in isolation
from the merge strategy (see test7_repair_stress.py for that one).

Run with:
  <blender> -b --python tests/test8_repair_decimate_stress.py -- <subdivisions>
(subdivisions defaults to 8 -> confirmed 327680 triangles at this
Blender version — the subdivisions->facecount formula isn't simply
20*4^subdivisions, confirmed by direct testing rather than assumed;
comfortably over the 240fps_esports 250000 cap either way)
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene  # noqa: E402
from core.entity_metadata import for_static_prop  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from materials.metal import bare_metal  # noqa: E402
from geometry.mesh_utils import simple_box_uv_unwrap  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402


def build_stress_asset(subdivisions=8, interactive=False):
    prepare_scene("DecimateStress", interactive)
    asset = Asset(name="DecimateStress", asset_type="prop")

    mat = bare_metal(make_name("material", asset.name, "Sphere"))
    asset.register_material(mat.name)

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0)
    sphere = bpy.context.active_object
    sphere.name = make_name("mesh", asset.name, "Sphere")
    sphere.data.name = sphere.name + "_mesh"
    simple_box_uv_unwrap(sphere)
    sphere.data.materials.append(mat)

    asset.add_geometry(sphere, metadata=for_static_prop(category="prop"))

    return asset


def main():
    subdivisions = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else 8
    asset = build_stress_asset(subdivisions=subdivisions)

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test8_repair_decimate_stress.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")
    print("SUMMARY:", asset.summary())


if __name__ == "__main__":
    main()

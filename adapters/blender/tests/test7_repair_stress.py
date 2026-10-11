"""TEST 7: Repair-loop stress fixture.

Not a showcase asset — a deliberately over-budget scene (many small
boxes, all tagged with the same visibility_group) used to exercise
repair/repair_engine.py's real merge-based repair strategy against a
real production performance profile (240fps_esports, max_visible_entities
=350), rather than inventing a fake tiny budget just to make a demo work.

Run with:
  <blender> -b --python tests/test7_repair_stress.py -- <entity_count>
(entity_count defaults to 400 — comfortably over 240fps_esports' 350 cap)
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
from geometry.primitives import create_box  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

MERGE_GROUP = "cluster"


def build_stress_asset(entity_count=400, interactive=False):
    prepare_scene("RepairStress", interactive)
    asset = Asset(name="RepairStress", asset_type="prop")

    mat = painted_wood(make_name("material", asset.name, "Crate"))
    asset.register_material(mat.name)

    per_row = 20
    for i in range(entity_count):
        box = create_box(make_name("mesh", asset.name, f"Crate{i}"), width=0.4, depth=0.4, height=0.4, material=mat)
        box.location.x = (i % per_row) * 0.5
        box.location.y = (i // per_row) * 0.5
        asset.add_geometry(box, metadata=for_static_prop(category="prop", visibility_group=MERGE_GROUP))

    return asset


def main():
    entity_count = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else 400
    asset = build_stress_asset(entity_count=entity_count)

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test7_repair_stress.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")
    print("SUMMARY:", asset.summary())


if __name__ == "__main__":
    main()

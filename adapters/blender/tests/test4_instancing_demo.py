"""TEST 4: repeated-asset instancing demo.

Exercises the performance/optimization architecture (core.entity_metadata,
geometry.instancing, optimization.merge, optimization.performance_validator)
added on top of tests 1-3. Builds a small "casino floor" style layout —
one master prop mesh instanced 40 times — and proves the engine keeps
unique-mesh count at 1 while entity count is 40, per the spec's core
principle: "How can the player SEE lots of detail while the game only has
to PROCESS a fraction of it?"

Also builds a naive (non-instanced, one unique mesh per copy) version of
the same layout so the two can be compared directly — same visible
result, very different unique-mesh count.

Run headless:
  <blender> -b --python tests/test4_instancing_demo.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.entity_metadata import for_static_prop, for_instanced_prop  # noqa: E402
from geometry.primitives import create_box  # noqa: E402
from geometry.instancing import create_instance_grid, count_unique_meshes  # noqa: E402
from materials.metal import painted_metal  # noqa: E402
from optimization.performance_validator import validate_performance  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

GRID_SIZE = (8, 5)   # 40 "slot machines"
SPACING = 0.9


def _grid_positions():
    cols, rows = GRID_SIZE
    positions = []
    for r in range(rows):
        for c in range(cols):
            positions.append((c * SPACING, r * SPACING, 0.0))
    return positions


def build_instanced(interactive=False):
    """The correct way: one mesh, many instances."""
    prepare_scene("CasinoFloorInstanced", interactive)
    asset = Asset(name="CasinoFloorInstanced", asset_type="environment")

    mat = painted_metal(make_name("material", asset.name, "Cabinet"), color=(0.6, 0.05, 0.1))
    asset.register_material(mat.name)

    positions = _grid_positions()
    master = create_box(make_name("mesh", asset.name, "SlotMachine"),
                         width=0.5, depth=0.5, height=1.2, bevel_width=0.02, material=mat)
    master.location = positions[0]
    asset.add_geometry(master, metadata=for_instanced_prop(category="slot_machine", importance="low"))

    create_instance_grid(asset, "SlotMachine", master, positions[1:],
                          importance="low", visibility_group="casino_floor")

    generate_box_collision(asset, "Floor", [master])
    return asset


def build_naive(interactive=False):
    """The wrong way, built deliberately for comparison: one unique mesh
    per copy, exactly what section 2 of the brief calls out as BAD."""
    prepare_scene("CasinoFloorNaive", interactive)
    asset = Asset(name="CasinoFloorNaive", asset_type="environment")

    mat = painted_metal(make_name("material", asset.name, "Cabinet"), color=(0.6, 0.05, 0.1))
    asset.register_material(mat.name)

    for i, (x, y, z) in enumerate(_grid_positions()):
        obj = create_box(make_name("mesh", asset.name, "SlotMachine", index=i),
                          width=0.5, depth=0.5, height=1.2, bevel_width=0.02, material=mat)
        obj.location = (x, y, z)
        asset.add_geometry(obj, metadata=for_static_prop(category="slot_machine", importance="low"))

    return asset


def main():
    # NOTE: each build_*() calls prepare_scene(), which factory-resets the
    # whole file in headless mode — that invalidates any previously-built
    # asset's bpy object references. So each build must be fully measured
    # and asserted on before the next one resets the scene, not deferred
    # to a shared block at the end.
    instanced = build_instanced(interactive=False)
    instanced_entity_count = len(instanced.geometry_objects)
    instanced_unique_meshes = count_unique_meshes(instanced.geometry_objects)
    print(f"Instanced version: entity_count={instanced_entity_count}, "
          f"unique_meshes={instanced_unique_meshes}")

    report = validate_performance(instanced, profile_name="240fps_esports")
    print()
    print(report.report())

    instanced.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(GENERATED_DIR, "test4_instancing_demo.blend"))

    assert instanced_unique_meshes == 1, "instancing failed to keep unique mesh count at 1"
    assert instanced_entity_count == GRID_SIZE[0] * GRID_SIZE[1]

    naive = build_naive(interactive=False)
    naive_entity_count = len(naive.geometry_objects)
    naive_unique_meshes = count_unique_meshes(naive.geometry_objects)
    print(f"\nNaive version:     entity_count={naive_entity_count}, "
          f"unique_meshes={naive_unique_meshes}")

    naive.save_asset_properties()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(GENERATED_DIR, "test4_naive_comparison.blend"))

    assert naive_unique_meshes == GRID_SIZE[0] * GRID_SIZE[1], \
        "naive comparison build should have one unique mesh per object"

    print("\nAll assertions passed.")
    if report.result != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()

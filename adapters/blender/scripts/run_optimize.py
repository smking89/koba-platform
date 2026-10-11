"""Headless entry point for the orchestration CLI's `optimize` command.

Always safe/non-destructive: assigns visibility/culling distances. If
--merge-group is given, also merges that visibility group's mergeable
objects into one mesh (refuses per-object if metadata says no — see
optimization.merge.MergeRefused). If --decimate-ratio is given, also
applies in-place decimation to every geometry object (see
optimization.decimate — lossy, reduces the real triangle count the
validator counts, unlike LOD registration). ALWAYS writes to
output_path, never overwrites blend_path in place — the caller
(adapters/blender_bridge.py) is responsible for choosing an output_path
that isn't the source, per the project's own "never destroy source
assets" rule.

Usage (invoked by adapters/blender_bridge.py, not normally run by hand):
  blender -b --python run_optimize.py -- <blend_path> <output_path> <profile_name> [asset_name] [--merge-group NAME] [--decimate-ratio FLOAT]
"""
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset_reconstruction import load_asset_from_blend  # noqa: E402
from optimization.performance_validator import validate_performance  # noqa: E402
from optimization.culling import assign_visibility_distances  # noqa: E402
from optimization.merge import merge_static_group, find_mergeable_groups, MergeRefused  # noqa: E402
from optimization.decimate import decimate_geometry  # noqa: E402


def _parse_args(argv):
    merge_group = None
    if "--merge-group" in argv:
        idx = argv.index("--merge-group")
        merge_group = argv[idx + 1]
        argv = argv[:idx] + argv[idx + 2:]
    decimate_ratio = None
    if "--decimate-ratio" in argv:
        idx = argv.index("--decimate-ratio")
        decimate_ratio = float(argv[idx + 1])
        argv = argv[:idx] + argv[idx + 2:]
    blend_path, output_path, profile_name = argv[0], argv[1], argv[2]
    asset_name = argv[3] if len(argv) > 3 else None
    return blend_path, output_path, profile_name, asset_name, merge_group, decimate_ratio


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 3:
        print(json.dumps({"error": "usage: run_optimize.py <blend_path> <output_path> <profile_name> [asset_name] [--merge-group NAME] [--decimate-ratio FLOAT]"}))
        sys.exit(2)

    blend_path, output_path, profile_name, asset_name, merge_group, decimate_ratio = _parse_args(argv)
    actions = []

    try:
        asset = load_asset_from_blend(blend_path, asset_name=asset_name)

        before = validate_performance(asset, profile_name=profile_name).metrics

        assign_visibility_distances(asset)
        actions.append("assigned visibility/culling distances to all geometry objects")

        if merge_group:
            groups = find_mergeable_groups(asset)
            target = groups.get(merge_group)
            if not target:
                actions.append(f"no mergeable group named '{merge_group}' with 2+ objects found — nothing merged")
            else:
                try:
                    merged = merge_static_group(asset, merge_group, target)
                    actions.append(f"merged {len(target)} objects in group '{merge_group}' into '{merged.name}'")
                except MergeRefused as e:
                    actions.append(f"merge refused: {e}")

        if decimate_ratio is not None:
            results = decimate_geometry(asset.geometry_objects, decimate_ratio)
            total_before = sum(r["before"] for r in results.values())
            total_after = sum(r["after"] for r in results.values())
            actions.append(
                f"decimated {len(results)} object(s) to ratio {decimate_ratio} "
                f"({total_before} -> {total_after} triangles)"
            )

        asset.save_asset_properties()
        after = validate_performance(asset, profile_name=profile_name).metrics

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=output_path)

    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        sys.exit(1)

    print(json.dumps({
        "asset_name": asset.name,
        "output_path": output_path,
        "actions": actions,
        "metrics_before": before,
        "metrics_after": after,
    }))


main()

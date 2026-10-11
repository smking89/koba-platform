"""Headless entry point for the orchestration CLI's `validate` command.
Read-only — never saves the .blend back.

Usage (invoked by adapters/blender_bridge.py, not normally run by hand):
  blender -b --python run_validate.py -- <blend_path> <profile_name> [asset_name]

Prints exactly one JSON object on the last line of stdout; everything
else (Blender's own startup banner, our INFO logs) goes to stdout/stderr
too but the bridge only trusts the last '{'-prefixed line.
"""
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.asset_reconstruction import load_asset_from_blend  # noqa: E402
from optimization.performance_validator import validate_performance  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 2:
        print(json.dumps({"error": "usage: run_validate.py <blend_path> <profile_name> [asset_name]"}))
        sys.exit(2)

    blend_path, profile_name = argv[0], argv[1]
    asset_name = argv[2] if len(argv) > 2 else None

    try:
        asset = load_asset_from_blend(blend_path, asset_name=asset_name)
        report = validate_performance(asset, profile_name=profile_name)
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        sys.exit(1)

    print(json.dumps({
        "asset_name": asset.name,
        "profile": profile_name,
        "result": report.result,
        "metrics": report.metrics,
        "warnings": report.warnings,
        "failures": report.failures,
    }))


main()

"""CLI entry point: generate a registered test/example asset by name and run
it through validation + preview + save, exactly like the phase tests do.

Run from the project root with the system Blender:
  <blender> -b --python scripts/generate_asset.py -- --asset crate

Everything after the bare '--' is this script's own argv (Blender eats
anything before it as its own args).
"""
import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

# Registry of known asset builders. Add an entry here every time a new
# tests/testN_*.py or examples/example_*.py exposes a build_*() function.
BUILDERS = {}


def _register_builders():
    from tests.test1_crate import build_crate
    from tests.test2_door import build_door
    from tests.test3_crane import build_crane
    BUILDERS["crate"] = build_crate
    BUILDERS["door"] = build_door
    BUILDERS["crane"] = build_crane


def main():
    parser = argparse.ArgumentParser(description="Generate a procedural asset")
    parser.add_argument("--asset", required=True, choices=None)
    parser.add_argument("--export-format", default="fbx_generic")
    parser.add_argument("--no-export", action="store_true")

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    _register_builders()
    if args.asset not in BUILDERS:
        print(f"Unknown asset '{args.asset}'. Known: {sorted(BUILDERS)}", file=sys.stderr)
        sys.exit(2)

    asset = BUILDERS[args.asset]()

    result = validate_asset(asset)
    print(result.report())

    preview_path = render_preview(asset)
    print(f"Preview: {preview_path}")

    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, f"{asset.name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    if not args.no_export:
        out = export_asset(asset, preset_name=args.export_format)
        print(f"Exported: {out}")

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

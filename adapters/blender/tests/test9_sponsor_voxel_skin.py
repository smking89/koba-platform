"""Cube Clash Events sponsor-skin Asset Automation Core — real headless
test. Simulates the moment described in the game spec: an advertiser's
checkout has already gone through (not this script's concern), and a
backend process now shells out to Blender with the advertiser's brand
hex colors + logo file, expecting a validated, exported .glb back.

Run with:
  <blender> -b --python tests/test9_sponsor_voxel_skin.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.scene import prepare_scene  # noqa: E402
from generators.voxel_sponsor_skin import generate_and_export  # noqa: E402


def main():
    prepare_scene("SponsorSkinTest", interactive=False)

    # No real advertiser logo on disk for this test — proves the no-logo
    # path works (brand colors only, no decal stamped) rather than
    # faking a logo file that doesn't exist.
    asset, export_path, result = generate_and_export(
        advertiser_name="AcmeSoda",
        primary_hex="#FF3B30",
        secondary_hex="#1C7ED6",
        logo_path=None,
        poly_budget=5000,
    )

    print(result.report())
    print(f"Exported: {export_path}")
    print("SUMMARY:", asset.summary())

    assert os.path.exists(export_path), f"export did not produce a file at {export_path}"

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

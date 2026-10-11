"""KOBA CASINO & RESORT — Phase 6c: VIP floor shell.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 6 / master prompt §20: a
SHELL for the VIP floor — zone outlines + one representative prop per
named zone (private casino, VIP lounge, VIP bar, VIP restaurant,
private poker room, private blackjack area, private pool/lounge,
premium suite marker, private conference room marker, balcony, premium
event-viewing area) — deliberately lighter than Phases 3/5/6a/6b's full
furnishing, per this roadmap's own Phase 6 description ("VIP floor
shell").

Sits on Floor7_VIP's footprint from Phase 2 (tier2 band -> 23x17
usable, floor surface at z=35.4 = Floor7's z_cursor=35.0 + Phase 2's
SLAB_THICKNESS=0.4).

Honest blockout limitation: each zone is ONE marker prop + ONE
interaction point, not the fully-furnished room Phase 3/5/6a built for
their non-VIP equivalents — a real shell, not a shortcut pretending to
be full detail.

Run with:
  <blender> -b --python tests/koba_casino_06c_vip_floor_shell.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms, set_origin_to_bounds_bottom  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.entity_metadata import for_static_prop  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.interaction_point import add_interaction_point  # noqa: E402
from geometry.primitives import create_box  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.metal import galvanized_steel  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 35.4  # Floor7_VIP's slab top surface (Phase 2: z_cursor=35.0 + SLAB_THICKNESS=0.4)

# (zone_id, interaction_point_name, grid position)
ZONES = [
    ("PrivateCasino", "VIP.PrivateCasino.001", (-8.0, -6.0)),
    ("Lounge", "VIP.Lounge.001", (-4.0, -6.0)),
    ("Bar", "VIP.Bar.001", (0.0, -6.0)),
    ("Restaurant", "VIP.Restaurant.001", (4.0, -6.0)),
    ("PrivatePoker", "VIP.PrivatePoker.001", (-8.0, -1.0)),
    ("PrivateBlackjack", "VIP.PrivateBlackjack.001", (-4.0, -1.0)),
    ("PrivatePool", "VIP.PrivatePool.001", (0.0, -1.0)),
    ("PremiumSuite", "VIP.PremiumSuite.001", (4.0, -1.0)),
    ("PrivateConference", "VIP.PrivateConference.001", (-8.0, 4.0)),
    ("Balcony", "VIP.Balcony.001", (-3.0, 4.0)),
    ("PremiumEventViewing", "VIP.PremiumEventViewing.001", (3.0, 4.0)),
]


def build_vip_shell(interactive=False):
    prepare_scene("KobaCasinoResort_VIPFloorShell", interactive)
    asset = Asset(name="KobaCasinoResort_VIPFloorShell", asset_type="monument")

    mats = {
        "marker": carved_stone(make_name("material", asset.name, "ZoneMarker"), color=(0.5, 0.4, 0.15)),
        "frame": galvanized_steel(make_name("material", asset.name, "ZoneFrame")),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    for zone_id, ip_name, (zx, zy) in ZONES:
        marker = create_box(make_name("mesh", asset.name, f"{zone_id}_Marker"), width=2.5, depth=2.5, height=0.15, material=mats["marker"])
        marker.location.x, marker.location.y, marker.location.z = zx, zy, FLOOR_Z
        apply_all_transforms(marker)
        asset.add_geometry(marker, metadata=for_static_prop(category="vip_zone_marker", importance="high"))

        post = create_box(make_name("mesh", asset.name, f"{zone_id}_Post"), width=0.2, depth=0.2, height=1.8, material=mats["frame"])
        post.location.x, post.location.y, post.location.z = zx, zy - 1.0, FLOOR_Z + 0.15
        apply_all_transforms(post)
        asset.add_geometry(post, metadata=for_static_prop(category="vip_zone_marker", importance="medium"))

        add_interaction_point(asset, ip_name, location=(zx, zy, FLOOR_Z + 1.0))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    markers = [o for o in asset.geometry_objects if "_Marker" in o.name]
    generate_box_collision(asset, "ZoneMarkers", markers)
    generate_decimated_lod(asset, "PremiumSuiteMarker", next(o for o in asset.geometry_objects if "PremiumSuite_Marker" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_vip_shell()

    result = validate_asset(asset, poly_budget=150000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_06c_vip_floor_shell.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_06c_vip_floor_shell.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

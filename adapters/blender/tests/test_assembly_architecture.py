"""Test for geometry/assemblies/architecture/* — the first group of the
primitive-library expansion requested on top of KOBA CASINO & RESORT's
existing blockouts.

Builds ONE real example of every architecture assembly (window single/
double/curtain-wall, door single/double/sliding with a real card-reader
mount, straight + corner railings, a round + a square column, a
straight staircase with handrail, a canopy, a gable roof, and a
spandrel band with a door gap), runs the whole scene through the real
validate_asset path, and reports real entity/triangle/collision/LOD
numbers — same discipline as every other test in this project.

Run with:
  <blender> -b --python tests/test_assembly_architecture.py
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
from materials.metal import galvanized_steel, bare_metal  # noqa: E402
from materials.glass import curtain_wall_glass  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from materials.signage import emissive_sign  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

from geometry.assemblies.architecture.windows import build_window_single, build_window_double, build_curtain_wall_segment  # noqa: E402
from geometry.assemblies.architecture.doors import build_door_single, build_door_double, build_door_sliding  # noqa: E402
from geometry.assemblies.architecture.railings import build_railing_straight, build_railing_corner  # noqa: E402
from geometry.assemblies.architecture.columns import build_column  # noqa: E402
from geometry.assemblies.architecture.stairs import build_staircase_straight  # noqa: E402
from geometry.assemblies.architecture.roofing import build_canopy, build_gable_roof  # noqa: E402
from geometry.assemblies.architecture.spandrels import build_spandrel_band  # noqa: E402


def build_architecture_showcase(interactive=False):
    prepare_scene("ArchitectureAssemblyShowcase", interactive)
    asset = Asset(name="ArchitectureAssemblyShowcase", asset_type="monument")

    mats = {
        "frame": galvanized_steel(make_name("material", asset.name, "WindowFrame")),
        "glass": curtain_wall_glass(make_name("material", asset.name, "WindowGlass")),
        "door": painted_wood(make_name("material", asset.name, "DoorWood")),
        "reader": emissive_sign(make_name("material", asset.name, "ReaderIndicator"), color=(0.2, 0.9, 0.3), strength=1.5),
        "post": bare_metal(make_name("material", asset.name, "RailingPost")),
        "rail": galvanized_steel(make_name("material", asset.name, "RailingRail")),
        "column": carved_stone(make_name("material", asset.name, "ColumnStone")),
        "step": carved_stone(make_name("material", asset.name, "StairStone"), color=(0.5, 0.48, 0.44)),
        "canopy_support": galvanized_steel(make_name("material", asset.name, "CanopySupport")),
        "canopy_roof": curtain_wall_glass(make_name("material", asset.name, "CanopyRoof")),
        "gable_roof": painted_wood(make_name("material", asset.name, "GableRoof"), color=(0.3, 0.15, 0.1)),
        "spandrel": carved_stone(make_name("material", asset.name, "SpandrelStone"), color=(0.55, 0.52, 0.48)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    counts_by_group = {}

    def _count(label, fn):
        before = len(asset.geometry_objects)
        result = fn()
        counts_by_group[label] = len(asset.geometry_objects) - before
        return result

    _count("window_single", lambda: build_window_single(asset, "Win1", -12.0, 0.0, 2.0, width=1.2, height=1.5, frame_mat=mats["frame"], glass_mat=mats["glass"]))
    _count("window_double", lambda: build_window_double(asset, "Win2", -8.0, 0.0, 2.0, width=2.2, height=1.5, frame_mat=mats["frame"], glass_mat=mats["glass"]))
    _count("curtain_wall_segment", lambda: build_curtain_wall_segment(asset, "CurtainWall1", -2.0, 0.0, 2.5, width=5.0, height=3.0, cols=3, rows=2, frame_mat=mats["frame"], glass_mat=mats["glass"]))

    _count("door_single", lambda: build_door_single(asset, "Door1", 4.0, 0.0, 0.0, width=0.9, height=2.1,
                                                      frame_mat=mats["frame"], door_mat=mats["door"],
                                                      reader_mat=mats["reader"], card_reader_name="Architecture.Test.Door1.CardReader"))
    _count("door_double", lambda: build_door_double(asset, "Door2", 8.0, 0.0, 0.0, width=1.8, height=2.1, frame_mat=mats["frame"], door_mat=mats["door"]))
    _count("door_sliding", lambda: build_door_sliding(asset, "Door3", 12.0, 0.0, 0.0, width=1.2, height=2.1, frame_mat=mats["frame"], door_mat=mats["door"], open_ratio=0.3))

    _count("railing_straight", lambda: build_railing_straight(asset, "Rail1", -10.0, 6.0, 0.0, length=6.0, post_mat=mats["post"], rail_mat=mats["rail"]))
    _count("railing_corner", lambda: build_railing_corner(asset, "Rail2", 0.0, 6.0, 0.0, length_x=4.0, length_y=4.0, post_mat=mats["post"], rail_mat=mats["rail"]))

    _count("column_round", lambda: build_column(asset, "Col1", -6.0, 10.0, 0.0, height=3.0, radius=0.3, style="round", mat=mats["column"]))
    _count("column_square", lambda: build_column(asset, "Col2", -3.0, 10.0, 0.0, height=3.0, radius=0.3, style="square", mat=mats["column"]))

    _count("staircase", lambda: build_staircase_straight(asset, "Stairs1", 2.0, 10.0, 0.0, num_steps=8, step_width=1.2, step_depth=0.3, step_height=0.18, step_mat=mats["step"], handrail_mat=mats["rail"]))

    _count("canopy", lambda: build_canopy(asset, "Canopy1", -8.0, -8.0, 0.0, width=5.0, depth=3.5, support_height=3.0, support_mat=mats["canopy_support"], roof_mat=mats["canopy_roof"]))
    _count("gable_roof", lambda: build_gable_roof(asset, "Gable1", -2.0, -8.0, 3.0, width=4.0, depth=4.0, pitch_height=1.5, mat=mats["gable_roof"]))

    _count("spandrel_band", lambda: build_spandrel_band(asset, "Spandrel1", 6.0, -8.0, 0.0, width=5.0, depth=4.0, thickness=0.3, height=1.0, mat=mats["spandrel"], door_gap=1.1, door_side="north"))

    collidable = [o for o in asset.geometry_objects if "glass" not in o.name.lower()]
    generate_box_collision(asset, "ShowcaseMain", collidable[:30])
    generate_decimated_lod(asset, "Gable", next(o for o in asset.geometry_objects if "Gable1_panel_left" in o.name), level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset, counts_by_group


def main():
    asset, counts_by_group = build_architecture_showcase()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print("\nReal part counts per assembly:")
    total = 0
    for label, count in counts_by_group.items():
        print(f"  {label}: {count} real objects")
        total += count
    print(f"  TOTAL: {total} objects, {asset.summary()['geometry_count']} registered on asset")

    preview_path = render_preview(asset, angle="three_quarter")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "test_assembly_architecture.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="test_assembly_architecture.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

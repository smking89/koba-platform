"""TEST/DEMO 5: imported prop + full material override.

Not a procedural generator like tests 1-4 — this demonstrates the other
half of the pipeline: importing a real third-party OBJ (a sci-fi gun,
~31.7k verts / ~29.4k faces, single plain-gray material, no textures) and
completely overriding its material so it looks made entirely of gummy
candy (materials.candy.gummy_material) — every material slot on every
imported part gets replaced, not blended with the original.

Source: /home/koba/Downloads/92-sci_fi_gun_obj.zip, copied into
assets/source/scifi_gun/ (source preserved, never modified in place).

Run headless:
  <blender> -b --python tests/test5_gummy_gun.py

Run live, staged:
  python3 scripts/blender_client.py -c "from tests.test5_gummy_gun import *; asset = stage_init(interactive=True)"
  python3 scripts/blender_client.py -c "stage_import(asset)"
  python3 scripts/blender_client.py -c "stage_apply_gummy_material(asset)"
  python3 scripts/blender_client.py -c "stage_finalize(asset, interactive=True)"
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
from core.entity_metadata import for_hero_asset  # noqa: E402
from materials.candy import gummy_material  # noqa: E402
from geometry.mesh_utils import assign_material_bands  # noqa: E402
from config.blender_config import GENERATED_DIR, PROJECT_ROOT as CFG_ROOT  # noqa: E402

SOURCE_OBJ = os.path.join(CFG_ROOT, "assets", "source", "scifi_gun", "scifi_gun.obj")

# Gummy-bear color palette — cycled across imported parts so a multi-part
# mesh reads as an assortment rather than one flat blob of color.
GUMMY_COLORS = [
    (0.95, 0.08, 0.12),  # red
    (0.98, 0.45, 0.03),  # orange
    (0.92, 0.88, 0.05),  # yellow/lime
    (0.10, 0.70, 0.20),  # green
    (0.90, 0.10, 0.55),  # pink
]


def stage_init(interactive=False):
    """STAGE 01 — scene init + asset."""
    prepare_scene("GummyGun", interactive)
    asset = Asset(name="GummyGun", asset_type="prop")
    return asset


def stage_import(asset):
    """STAGE 02 — import the real OBJ, register every resulting part as
    geometry with hero-asset metadata (never culled/merged/instanced away
    — this is the single showcase object, not a repeated prop)."""
    if not os.path.isfile(SOURCE_OBJ):
        raise FileNotFoundError(f"Source OBJ not found: {SOURCE_OBJ}")

    before = set(bpy.data.objects.keys())
    bpy.ops.wm.obj_import(filepath=SOURCE_OBJ)
    after = set(bpy.data.objects.keys())
    imported_names = after - before
    if not imported_names:
        raise RuntimeError("obj_import reported success but no new objects appeared")

    imported = [bpy.data.objects[n] for n in imported_names]
    for obj in imported:
        if obj.type == "MESH":
            asset.add_geometry(obj, metadata=for_hero_asset(category="weapon"))

    asset.imported_objects = [o for o in imported if o.type == "MESH"]
    return asset.imported_objects


def stage_apply_gummy_material(asset, assorted=True, band_axis="Z"):
    """STAGE 03 — completely replace every material slot on every imported
    part with gummy material(s) — this overrides the source's original
    plain-gray material entirely, per the request that the weapon look
    made completely of gummy candy, not just gray-with-a-tint.

    assorted=True (default) bands each part's faces into len(GUMMY_COLORS)
    stripes along `band_axis` (local space) via
    geometry.mesh_utils.assign_material_bands, for an "assorted gummy
    candy" look rather than one flat color. assorted=False keeps the
    original single-color-per-part behavior."""
    materials = [
        gummy_material(f"MAT_{asset.name}_Gummy{i}", color=color)
        for i, color in enumerate(GUMMY_COLORS)
    ]
    for mat in materials:
        asset.register_material(mat.name)

    for i, obj in enumerate(asset.imported_objects):
        if assorted:
            assign_material_bands(obj, materials, axis=band_axis, by="count")
        else:
            obj.data.materials.clear()  # drop the original material(s) entirely
            obj.data.materials.append(materials[i % len(materials)])

    return materials


def stage_finalize(asset, interactive=False, save=True, export=False):
    """STAGE 04 — validate, preview/frame, save."""
    result = validate_asset(asset, poly_budget=40000)
    print(result.report())

    from core.scene import new_sun
    if "LGT_Backlight" not in bpy.data.objects:
        new_sun(name="LGT_Backlight", energy=10.0, rotation_euler=(-2.0, 0.3, 2.4))
    if "LGT_Key" not in bpy.data.objects:
        new_sun(name="LGT_Key", energy=4.0, rotation_euler=(0.6, -0.3, -0.8))

    if interactive:
        frame_objects(asset.geometry_objects)
    else:
        # Gummy/transmissive materials need Cycles, not EEVEE, to actually
        # render see-through — see materials.candy.gummy_material's
        # docstring for why (EEVEE's screen-space transmission can't trace
        # through a solid/complex mesh properly).
        preview_path = render_preview(asset, angle="three_quarter", engine="CYCLES", samples=96)
        print(f"Preview rendered: {preview_path}")

    if save:
        os.makedirs(GENERATED_DIR, exist_ok=True)
        blend_path = os.path.join(GENERATED_DIR, f"{asset.name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"Saved: {blend_path}")

    print("SUMMARY:", asset.summary())
    return result


def build_gummy_gun(interactive=False):
    asset = stage_init(interactive=interactive)
    stage_import(asset)
    stage_apply_gummy_material(asset)
    asset._last_validation = stage_finalize(asset, interactive=interactive)
    return asset


def main():
    asset = build_gummy_gun(interactive=False)
    if not asset._last_validation.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

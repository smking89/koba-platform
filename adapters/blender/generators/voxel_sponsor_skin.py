"""Cube Clash 'Events' sponsor-skin generator — the real implementation
of the game spec's Asset Automation Core: an advertiser's brand hex
colors + logo upload drive a headless Blender run that constructs,
textures, optimizes, and exports a custom voxel block skin (.glb).

This module only builds geometry/materials/export — it does not open
a web portal, touch a payment flow, or write to a game-server database.
Those belong to a separate backend service that shells out to Blender
(`blender -b --python generators/voxel_sponsor_skin.py -- <args>`,
or imports build_sponsor_voxel_skin directly from a Blender Python
environment) and hands this module nothing but already-validated
inputs (hex colors, a local logo file path, an output filename).

Matches the art style guide from the Cube Clash spec: simple voxel
blocks, matte finish (roughness ~0.7), bright flat colors — no PBR
texture library involved, since a sponsor skin's whole point is to be
exactly the advertiser's brand color, not a curated material.
"""
import os

from core.asset import Asset
from core.naming import name as make_name
from core.entity_metadata import for_static_prop
from core.validation import validate_asset
from geometry.primitives import create_box
from geometry.decals import apply_logo_decal
from materials.branding import simple_color_material
from optimization.decimate import decimate_geometry
from export.exporter import export_asset


def _triangle_count(obj):
    return sum(max(len(p.vertices) - 2, 1) for p in obj.data.polygons)


def build_sponsor_voxel_skin(advertiser_name, primary_hex, secondary_hex,
                             logo_path=None, block_size=1.0, poly_budget=5000):
    """Builds a 3-block voxel tile set skinned in an advertiser's brand
    colors: a ground/base block (primary color), a raised accent block
    (secondary color, with the logo decal stamped on its top face if
    `logo_path` is given), and a small corner/decoration block (primary
    color). Mirrors Cube Clash's hex-grid tile footprint at 1 unit per
    block by default. Returns the built Asset (not yet exported)."""
    asset = Asset(name=f"SponsorSkin_{advertiser_name}", asset_type="event_skin")

    primary_mat = simple_color_material(make_name("material", asset.name, "Primary"), primary_hex)
    accent_mat = simple_color_material(make_name("material", asset.name, "Accent"), secondary_hex)
    asset.register_material(primary_mat.name)
    asset.register_material(accent_mat.name)

    ground = create_box(make_name("mesh", asset.name, "GroundBlock"),
                         width=block_size, depth=block_size, height=block_size * 0.3,
                         material=primary_mat)
    asset.add_geometry(ground, metadata=for_static_prop(category="sponsor_tile", importance="high"))

    accent = create_box(make_name("mesh", asset.name, "AccentBlock"),
                         width=block_size * 0.6, depth=block_size * 0.6, height=block_size * 0.6,
                         material=accent_mat)
    accent.location.z = block_size * 0.3
    if logo_path:
        logo_mat_name = make_name("material", asset.name, "Logo")
        apply_logo_decal(accent, logo_path, logo_mat_name, normal_axis="z", sign=1)
    asset.add_geometry(accent, metadata=for_static_prop(category="sponsor_tile", importance="high"))

    corner = create_box(make_name("mesh", asset.name, "CornerBlock"),
                         width=block_size * 0.25, depth=block_size * 0.25, height=block_size * 0.25,
                         material=primary_mat)
    corner.location.x = block_size * 0.35
    corner.location.y = block_size * 0.35
    corner.location.z = block_size * 0.3 + block_size * 0.125
    asset.add_geometry(corner, metadata=for_static_prop(category="sponsor_tile", importance="medium"))

    total_tris = sum(_triangle_count(o) for o in asset.geometry_objects if o.type == "MESH")
    if total_tris > poly_budget:
        ratio = poly_budget / total_tris
        decimate_geometry([o for o in asset.geometry_objects if o.type == "MESH"], ratio)

    return asset


def generate_and_export(advertiser_name, primary_hex, secondary_hex, logo_path=None,
                         poly_budget=5000, filename=None):
    """End-to-end: build the skin, validate it, export as .glb, return
    (asset, export_path, validation_report). This is the function a
    calling backend service should invoke per sponsor-skin order."""
    asset = build_sponsor_voxel_skin(advertiser_name, primary_hex, secondary_hex,
                                      logo_path=logo_path, poly_budget=poly_budget)
    result = validate_asset(asset, poly_budget=poly_budget)
    export_path = export_asset(asset, preset_name="gltf_generic",
                                filename=filename or f"sponsor_skin_{advertiser_name}.glb")
    return asset, export_path, result

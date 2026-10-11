"""Real PBR material library — curated ambientCG texture sets (Color +
Roughness + real Normal maps, downloaded via textures/texture_manager.py's
already-verified API client) wired onto Principled BSDF, instead of the
flat single-color procedural materials every other materials/*.py module
in this project uses.

This is the direct response to the honest fidelity gap named on
2026-10-01: procedural primitive assemblies can't match hand-sculpted/
scanned assets (e.g. Sketchfab's artist-made models) — that's a
different production method entirely. What CAN close part of that gap
while staying procedural: real downloaded PBR surface detail on the
primitive geometry this engine already builds. Not a substitute for
real modeling, but a genuine, honest improvement over a flat Principled
BSDF color.

Downloads happen ONCE per asset (cached under assets/textures/downloaded/
ambientcg/<asset_id>/ by texture_manager.py) and the resulting Blender
material is cached by name via materials.material_manager.get_or_create,
same pattern as every other material generator in this project.

Curated set (chosen 2026-10-01, real ambientCG asset IDs, confirmed
downloadable): wood (Planks037A), metal (Metal055A), marble/stone
(Marble012), leather (Leather037), fabric (Fabric061).
"""
import os

from config.blender_config import PROJECT_ROOT
from materials.material_manager import get_or_create
from textures.texture_manager import download_ambientcg_texture, apply_image_textures

_LOCAL_CACHE_ROOT = os.path.join(PROJECT_ROOT, "assets", "textures", "downloaded", "ambientcg")


def _local_cached_maps(asset_id):
    """Real local-file check — if this asset's maps are already sitting
    on disk from a previous run/call, reuse them directly instead of
    re-hitting the network. Mirrors download_ambientcg_texture's own
    {role: path} role-extraction so the result is a drop-in replacement
    for it."""
    asset_dir = os.path.join(_LOCAL_CACHE_ROOT, asset_id)
    if not os.path.isdir(asset_dir):
        return None
    local_paths = {}
    for fname in os.listdir(asset_dir):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".exr")):
            stem = os.path.splitext(fname)[0]
            role = stem.split("_")[-1]
            local_paths[role] = os.path.join(asset_dir, fname)
    return local_paths or None

CURATED_ASSETS = {
    "wood": "Planks037A",
    "metal": "Metal055A",
    "marble": "Marble012",
    "leather": "Leather037",
    "fabric": "Fabric061",
}

UV_SCALE_DEFAULT = {
    "wood": 1.0,
    "metal": 1.0,
    "marble": 0.5,
    "leather": 1.0,
    "fabric": 2.0,
}


def _apply_uv_scale(material, scale):
    """Adds a Mapping node between UV and every Image Texture node so the
    real texture repeats at a sensible frequency for furniture-scale
    primitives instead of stretching one tile across a whole object."""
    if scale == 1.0:
        return
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    uv_map = nodes.new("ShaderNodeUVMap")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(uv_map.outputs["UV"], mapping.inputs["Vector"])

    for node in nodes:
        if node.type == "TEX_IMAGE":
            links.new(mapping.outputs["Vector"], node.inputs["Vector"])


def get_pbr_material(category, name, resolution="1K", uv_scale=None):
    """category in CURATED_ASSETS. Returns a real, cached Blender material
    with Color/Roughness/Normal wired from a real downloaded texture set.
    `name` is the material's own name (so multiple objects/assets can
    request the SAME underlying texture under different material names
    if they need independent per-object tweaks later — get_or_create
    still dedupes by that name, consistent with every other materials/*.py
    module)."""
    if category not in CURATED_ASSETS:
        raise ValueError(f"Unknown PBR category '{category}'. Known: {sorted(CURATED_ASSETS)}")
    asset_id = CURATED_ASSETS[category]
    scale = UV_SCALE_DEFAULT[category] if uv_scale is None else uv_scale

    def build(mat):
        image_paths = _local_cached_maps(asset_id) or download_ambientcg_texture(asset_id, resolution=resolution)
        apply_image_textures(mat, image_paths)
        _apply_uv_scale(mat, scale)

    return get_or_create(name, build)

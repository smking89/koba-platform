"""Fetches real PBR texture sets from free, unauthenticated APIs and wires
them into a Blender material via Image Texture nodes.

Verified directly against the live APIs (2026-09-27), not guessed:
  - Poly Haven: https://api.polyhaven.com/assets?type=textures (list),
    https://api.polyhaven.com/files/<asset_id> (per-asset download URLs).
    No API key needed.
  - ambientCG: https://ambientcg.com/api/v2/full_json?id=<AssetId>&include=downloadData
    returns downloadFolders -> downloadFiletypeCategories -> zip -> downloads,
    each with a fullDownloadPath like https://ambientcg.com/get?file=<name>.zip.
    No API key needed, but assets ship as a zip that must be extracted.

Poliigon (poliigon.com/textures/free) is NOT supported here — its free
downloads go through an account-gated web UI, not an unauthenticated API,
so it can't be scripted the same way. Fetch those manually if needed.

Downloading is a real network + filesystem action, so nothing in this
module writes to disk until a caller explicitly asks it to via
download_polyhaven_texture / download_ambientcg_texture.
"""
import json
import os
import urllib.parse
import urllib.request
import zipfile

from config.blender_config import PROJECT_ROOT

TEXTURES_CACHE_DIR = os.path.join(PROJECT_ROOT, "assets", "textures", "downloaded")
MODELS_CACHE_DIR = os.path.join(PROJECT_ROOT, "assets", "cache", "polyhaven_models")

POLYHAVEN_API = "https://api.polyhaven.com"
AMBIENTCG_API = "https://ambientcg.com/api/v2/full_json"

# Poly Haven map names -> the role our materials care about.
POLYHAVEN_MAP_ROLES = {
    "Diffuse": "base_color",
    "nor_gl": "normal",
    "Rough": "roughness",
    "AO": "ao",
    "Displacement": "displacement",
}


_HEADERS = {"User-Agent": "blender-asset-system/1.0 (+https://github.com/)"}


def _http_get_json(url):
    # Poly Haven's API returns 403 for Python's default urllib User-Agent —
    # confirmed by testing, not a hypothetical precaution.
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download_file(url, dest_path):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())


def search_polyhaven(query=None, limit=20):
    """Return [(asset_id, display_name, categories), ...] for texture assets,
    optionally filtered by a case-insensitive substring match on name/tags."""
    data = _http_get_json(f"{POLYHAVEN_API}/assets?type=textures")
    results = []
    q = query.lower() if query else None
    for asset_id, info in data.items():
        if q and q not in asset_id.lower() and q not in info.get("name", "").lower() \
                and not any(q in t.lower() for t in info.get("tags", [])):
            continue
        results.append((asset_id, info["name"], info.get("categories", [])))
        if len(results) >= limit:
            break
    return results


def get_polyhaven_file_urls(asset_id, resolution="2k", file_format="jpg"):
    """Return {map_name: url} for the given asset/resolution/format, using
    whatever maps that asset actually has (not every asset has every map)."""
    data = _http_get_json(f"{POLYHAVEN_API}/files/{asset_id}")
    urls = {}
    for map_name, by_res in data.items():
        if not isinstance(by_res, dict):
            continue
        entry = by_res.get(resolution, {}).get(file_format)
        if entry:
            urls[map_name] = entry["url"]
    return urls


def download_polyhaven_texture(asset_id, resolution="2k", file_format="jpg", dest_dir=None):
    """Download all available maps for one Poly Haven texture asset. Returns
    {map_name: local_path}. Caller must have already confirmed this download
    with the user — this function does not ask."""
    dest_dir = dest_dir or os.path.join(TEXTURES_CACHE_DIR, "polyhaven", asset_id)
    os.makedirs(dest_dir, exist_ok=True)

    urls = get_polyhaven_file_urls(asset_id, resolution, file_format)
    if not urls:
        raise ValueError(f"No '{resolution}' {file_format} files found for polyhaven asset '{asset_id}'")

    local_paths = {}
    for map_name, url in urls.items():
        filename = f"{asset_id}_{map_name}_{resolution}.{file_format}"
        local_path = os.path.join(dest_dir, filename)
        _download_file(url, local_path)
        local_paths[map_name] = local_path
    return local_paths


def search_polyhaven_models(query=None, limit=20):
    """Return [(asset_id, display_name, categories), ...] for real CC0 3D
    MODEL assets (type=models, not type=textures) — actual pre-authored
    low-poly furniture/props, not a texture set. Verified live
    2026-10-02 against https://api.polyhaven.com/assets?type=models
    (521 real models found at the time)."""
    data = _http_get_json(f"{POLYHAVEN_API}/assets?type=models")
    results = []
    q = query.lower() if query else None
    for asset_id, info in data.items():
        if q and q not in asset_id.lower() and q not in info.get("name", "").lower() \
                and not any(q in t.lower() for t in info.get("tags", [])):
            continue
        results.append((asset_id, info["name"], info.get("categories", [])))
        if len(results) >= limit:
            break
    return results


def get_polyhaven_model_file_urls(asset_id, resolution="1k", file_format="gltf"):
    """Return {"main": url, "<relative_path>": url, ...} for one model —
    the main .gltf/.fbx file plus every file it `include`s (its own
    .bin and texture files, each at the RELATIVE PATH the main file
    references them by, e.g. "textures/Chair_diff_1k.jpg") — download
    every key to that same relative path under one directory and the
    main file's references resolve correctly on import."""
    data = _http_get_json(f"{POLYHAVEN_API}/files/{asset_id}")
    entry = data.get(file_format, {}).get(resolution, {}).get(file_format)
    if not entry:
        raise ValueError(f"No '{resolution}' {file_format} package found for polyhaven model '{asset_id}'")
    urls = {"main": entry["url"]}
    for rel_path, info in entry.get("include", {}).items():
        urls[rel_path] = info["url"]
    return urls


def download_polyhaven_model(asset_id, resolution="1k", file_format="gltf", dest_dir=None):
    """Downloads one real Poly Haven CC0 model (main file + every
    textures/.bin dependency, preserving relative paths) into
    MODELS_CACHE_DIR/<asset_id>/. Returns the local path to the main
    importable file (.gltf/.fbx). Caller must have already confirmed
    this download with the user — this function does not ask."""
    dest_dir = dest_dir or os.path.join(MODELS_CACHE_DIR, asset_id)
    urls = get_polyhaven_model_file_urls(asset_id, resolution, file_format)

    main_url = urls.pop("main")
    main_filename = os.path.basename(urllib.parse.urlparse(main_url).path)
    main_local_path = os.path.join(dest_dir, main_filename)
    os.makedirs(dest_dir, exist_ok=True)
    _download_file(main_url, main_local_path)

    for rel_path, url in urls.items():
        local_path = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        _download_file(url, local_path)

    return main_local_path


def search_ambientcg(query, limit=10):
    """Return [(asset_id, display_name, category), ...] matching a search string."""
    url = f"{AMBIENTCG_API}?q={urllib.parse.quote(query)}&limit={limit}&type=Material"
    data = _http_get_json(url)
    return [(a["assetId"], a["displayName"], a.get("displayCategory")) for a in data.get("foundAssets", [])]


def get_ambientcg_zip_url(asset_id, resolution="2K", filetype="JPG"):
    """Return the direct .zip download URL for one ambientCG asset/resolution."""
    url = f"{AMBIENTCG_API}?id={asset_id}&include=downloadData"
    data = _http_get_json(url)
    assets = data.get("foundAssets", [])
    if not assets:
        raise ValueError(f"ambientCG asset '{asset_id}' not found")

    attribute = f"{resolution}-{filetype}"
    downloads = assets[0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    for d in downloads:
        if d["attribute"] == attribute:
            return d["fullDownloadPath"], d["size"]
    available = [d["attribute"] for d in downloads]
    raise ValueError(f"No '{attribute}' package for '{asset_id}'. Available: {available}")


def download_ambientcg_texture(asset_id, resolution="2K", filetype="JPG", dest_dir=None):
    """Download and extract one ambientCG material zip. Returns
    {map_suffix: local_path} for the extracted image files. Caller must have
    already confirmed this download with the user — this function does not ask."""
    dest_dir = dest_dir or os.path.join(TEXTURES_CACHE_DIR, "ambientcg", asset_id)
    os.makedirs(dest_dir, exist_ok=True)

    zip_url, size = get_ambientcg_zip_url(asset_id, resolution, filetype)
    zip_path = os.path.join(dest_dir, f"{asset_id}_{resolution}-{filetype}.zip")
    _download_file(zip_url, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)

    local_paths = {}
    for fname in os.listdir(dest_dir):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".exr")):
            # ambientCG names files like "Bricks105_2K-JPG_Color.jpg" — the part
            # after the last underscore-before-extension is the map role.
            stem = os.path.splitext(fname)[0]
            role = stem.split("_")[-1]
            local_paths[role] = os.path.join(dest_dir, fname)
    return local_paths


def apply_image_textures(material, image_paths, base_color_key="Color", roughness_key="Roughness",
                          normal_key="NormalGL", ao_key="AmbientOcclusion"):
    """Wire a dict of {role: filepath} (from either download_* function above,
    keys vary by source) into an existing material's Principled BSDF via
    Image Texture nodes. Only wires roles it can find a match for — missing
    maps are skipped, not faked."""
    import bpy

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        raise ValueError(f"Material '{material.name}' has no Principled BSDF node")

    def _load(path):
        return bpy.data.images.load(path, check_existing=True)

    def _find(keys):
        for k in keys:
            for role, path in image_paths.items():
                if k.lower() in role.lower():
                    return path
        return None

    base_color_path = _find([base_color_key, "diffuse", "diff", "albedo", "color"])
    if base_color_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = _load(base_color_path)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    rough_path = _find([roughness_key, "rough"])
    if rough_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = _load(rough_path)
        tex.image.colorspace_settings.name = "Non-Color"
        links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])

    normal_path = _find([normal_key, "nor_gl", "normal"])
    if normal_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = _load(normal_path)
        tex.image.colorspace_settings.name = "Non-Color"
        normal_map = nodes.new("ShaderNodeNormalMap")
        links.new(tex.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    return material

"""Rebuilds a lightweight Asset-like stub from a saved .blend file, using
only the custom properties core.asset stamped onto objects/collections at
build time (core.asset.Asset.set_metadata / save_asset_properties) — no
dependency on the original Python Asset instance or build script still
being around. This is what lets a separate process (the orchestration
CLI's `validate`/`optimize` commands, run long after the asset was built)
inspect/modify an asset headlessly.

If an asset was built before this persistence existed, or a caller forgot
save_asset_properties(), reconstruction still works for geometry_objects/
entity_metadata (stamped per-object at add_geometry time) — only the
asset-level fields (materials/rig/animations/export_status) fall back to
empty defaults, since those live on the ROOT collection.
"""
import json

import bpy

from core.asset import METADATA_PROP, ASSET_PROP_PREFIX
from core.entity_metadata import EntityMetadata, for_static_prop


class ReconstructedAsset:
    """Implements the subset of core.asset.Asset's interface that
    optimization/performance_validator.py and optimization/merge.py
    actually use: geometry_objects, entity_metadata, get_metadata,
    set_metadata, collision_objects, lod_objects, material_names, rig,
    animations, name."""

    def __init__(self, name):
        self.name = name
        self.asset_type = "unknown"
        self.geometry_objects = []
        self.entity_metadata = {}
        self.collision_objects = []
        self.lod_objects = {}
        self.material_names = []
        self.rig = []
        self.animations = []
        self.export_status = "unknown"

    def get_metadata(self, obj):
        return self.entity_metadata.get(obj.name, for_static_prop())

    def register_material(self, mat_name):
        if mat_name not in self.material_names:
            self.material_names.append(mat_name)

    def set_metadata(self, obj, metadata):
        self.entity_metadata[obj.name] = metadata
        obj[METADATA_PROP] = json.dumps(metadata.as_dict())

    def save_asset_properties(self):
        """Mirrors core.asset.Asset.save_asset_properties — re-stamps the
        ASSET_<name> collection so changes made during this reconstructed
        session (e.g. a merge) are reflected if the file is saved."""
        root = bpy.data.collections.get(f"ASSET_{self.name}")
        if root is None:
            return
        root[ASSET_PROP_PREFIX + "name"] = self.name
        root[ASSET_PROP_PREFIX + "type"] = self.asset_type
        root[ASSET_PROP_PREFIX + "materials"] = json.dumps(self.material_names)
        root[ASSET_PROP_PREFIX + "rig"] = json.dumps(self.rig)
        root[ASSET_PROP_PREFIX + "animations"] = json.dumps(self.animations)
        root[ASSET_PROP_PREFIX + "export_status"] = self.export_status


def _read_metadata(obj):
    raw = obj.get(METADATA_PROP)
    if not raw:
        return for_static_prop()  # no stamp found — same conservative default as core.asset.Asset.get_metadata
    try:
        return EntityMetadata(**json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return for_static_prop()


def list_asset_names_in_current_file():
    """Every ASSET_<name> collection present, regardless of whether it was
    stamped with save_asset_properties() (falls back to the collection
    name if not)."""
    names = []
    for coll in bpy.data.collections:
        if coll.name.startswith("ASSET_"):
            stamped = coll.get(ASSET_PROP_PREFIX + "name")
            names.append(stamped if stamped else coll.name[len("ASSET_"):])
    return names


def load_asset_from_blend(blend_path, asset_name=None):
    """Opens blend_path (replacing whatever is currently loaded — call this
    first thing in a headless script, not mid-session) and reconstructs the
    named asset. If asset_name is None and exactly one ASSET_* collection
    exists, uses that one; otherwise raises."""
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    return load_asset_from_current_file(asset_name)


def load_asset_from_current_file(asset_name=None):
    """Same as load_asset_from_blend but operates on whatever .blend is
    already open — for use from the live bridge, where the file is already
    loaded in the running GUI session."""
    available = list_asset_names_in_current_file()
    if not available:
        raise ValueError("No ASSET_<name> collections found in this file")

    if asset_name is None:
        if len(available) > 1:
            raise ValueError(f"Multiple assets in this file, specify asset_name: {available}")
        asset_name = available[0]
    elif asset_name not in available:
        raise ValueError(f"Asset '{asset_name}' not found. Available: {available}")

    root_coll = bpy.data.collections.get(f"ASSET_{asset_name}")
    if root_coll is None:
        raise ValueError(f"Collection 'ASSET_{asset_name}' not found even though it was listed — inconsistent state")

    asset = ReconstructedAsset(asset_name)
    asset.asset_type = root_coll.get(ASSET_PROP_PREFIX + "type", "unknown")
    asset.material_names = json.loads(root_coll.get(ASSET_PROP_PREFIX + "materials", "[]"))
    asset.rig = json.loads(root_coll.get(ASSET_PROP_PREFIX + "rig", "[]"))
    asset.animations = json.loads(root_coll.get(ASSET_PROP_PREFIX + "animations", "[]"))
    asset.export_status = root_coll.get(ASSET_PROP_PREFIX + "export_status", "unknown")

    geo_coll = bpy.data.collections.get(f"GEO_{asset_name}")
    geo_detail_coll = bpy.data.collections.get(f"GEO_DETAIL_{asset_name}")
    collision_coll = bpy.data.collections.get(f"COLLISION_{asset_name}")

    for obj in (geo_coll.objects if geo_coll else []):
        asset.geometry_objects.append(obj)
        asset.entity_metadata[obj.name] = _read_metadata(obj)

    if geo_detail_coll:
        # LOD level isn't individually recoverable post-hoc from the naming
        # convention alone without re-parsing "LOD<level>_..." — group
        # everything here under level 1 rather than guess wrong.
        asset.lod_objects[1] = list(geo_detail_coll.objects)

    if collision_coll:
        asset.collision_objects = list(collision_coll.objects)

    return asset

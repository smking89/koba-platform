"""Asset metadata container.

Every generator function should build and return an Asset so downstream
stages (validation, optimization, export) have a single object to work
against instead of loose object references.
"""
import datetime
import json
import uuid

from core import collections as collections_mod
from core import logging as log
from core.entity_metadata import EntityMetadata, for_static_prop

METADATA_PROP = "koba_metadata"  # per-object custom property key
ASSET_PROP_PREFIX = "koba_asset_"  # per-collection custom property keys


class Asset:
    def __init__(self, name, asset_type, author="claude-code", engine_target=None, scale_unit="meters"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.asset_type = asset_type
        self.author = author
        self.engine_target = engine_target
        self.scale_unit = scale_unit
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.collections = collections_mod.build_asset_collections(name)

        self.geometry_objects = []
        self.material_names = []
        self.lod_objects = {}      # {level: [objects]}
        self.collision_objects = []
        self.rig = []  # list of rig_info dicts — multi-part assets (e.g. a crane) have more than one
        self.animations = []
        self.entity_metadata = {}  # {object_name: EntityMetadata} — see core.entity_metadata

        self.export_status = "not_exported"

        log.info(f"Created asset '{name}' ({asset_type}) id={self.id}")

    def add_geometry(self, obj, metadata=None):
        """metadata is an EntityMetadata (see core.entity_metadata) describing
        this object's runtime behavior for the optimization pipeline
        (instancing/merging/culling/the performance validator). Defaults to
        a plain static/mergeable/cullable prop if omitted — callers building
        rigged or interactive parts should pass an explicit metadata to
        prevent them being merged/instanced away by mistake."""
        collections_mod.link_only(obj, self.collections["GEO"])
        self.geometry_objects.append(obj)
        self.set_metadata(obj, metadata or for_static_prop())
        return obj

    def get_metadata(self, obj):
        return self.entity_metadata.get(obj.name, for_static_prop())

    def set_metadata(self, obj, metadata):
        """Stores metadata both in-memory (self.entity_metadata) AND as a
        Blender custom property on the object itself, so it survives a
        save/reload — a separate process (e.g. the CLI's `validate`/
        `optimize` commands, running long after this Python Asset instance
        is gone) can reconstruct it from the saved .blend alone. See
        core.asset_reconstruction."""
        self.entity_metadata[obj.name] = metadata
        obj[METADATA_PROP] = json.dumps(metadata.as_dict())

    def save_asset_properties(self):
        """Call once, right before saving the .blend, to stamp asset-level
        info (name/type/materials/rig/animations) onto the ROOT collection
        as custom properties — the other half of what
        core.asset_reconstruction needs to rebuild this Asset from disk."""
        root = self.collections["ROOT"]
        root[ASSET_PROP_PREFIX + "name"] = self.name
        root[ASSET_PROP_PREFIX + "type"] = self.asset_type
        root[ASSET_PROP_PREFIX + "materials"] = json.dumps(self.material_names)
        root[ASSET_PROP_PREFIX + "rig"] = json.dumps([
            {k: v for k, v in r.items() if k != "empty"} for r in self.rig
        ])
        root[ASSET_PROP_PREFIX + "animations"] = json.dumps(self.animations)
        root[ASSET_PROP_PREFIX + "export_status"] = self.export_status

    def add_collision(self, obj):
        collections_mod.link_only(obj, self.collections["COLLISION"])
        self.collision_objects.append(obj)
        return obj

    def add_lod(self, level, obj):
        collections_mod.link_only(obj, self.collections["GEO_DETAIL"] if level > 0 else self.collections["GEO"])
        self.lod_objects.setdefault(level, []).append(obj)
        return obj

    def register_material(self, mat_name):
        if mat_name not in self.material_names:
            self.material_names.append(mat_name)

    def add_rig(self, rig_info):
        """rig_info is a plain dict describing one rig component (e.g.
        {'type': 'hinge', 'part': ..., 'empty': ..., 'axis': ...}) — kept
        loose since rig shapes vary a lot between mechanical/vehicle/
        character rigs. A multi-part mechanism (e.g. a crane) calls this
        once per DOF (slew, boom pitch, hook winch, ...)."""
        self.rig.append(rig_info)

    def set_rig(self, rig_info):
        """Back-compat alias for single-rig assets (e.g. a door's one hinge)."""
        self.add_rig(rig_info)

    def add_animation(self, action_name):
        if action_name not in self.animations:
            self.animations.append(action_name)

    def summary(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.asset_type,
            "author": self.author,
            "created_at": self.created_at,
            "geometry_count": len(self.geometry_objects),
            "instanced_count": sum(1 for m in self.entity_metadata.values() if m.instanceable),
            "materials": self.material_names,
            "lod_levels": sorted(self.lod_objects.keys()),
            "collision_count": len(self.collision_objects),
            "has_rig": bool(self.rig),
            "rig_parts": [r.get("part") for r in self.rig],
            "animation_count": len(self.animations),
            "export_status": self.export_status,
        }

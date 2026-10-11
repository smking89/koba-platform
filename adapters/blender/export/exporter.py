"""Centralized exporter. Wraps the verified operators from config/export_config.py
so individual scripts never hand-roll export kwargs."""
import os

import bpy

from config.export_config import EXPORT_PRESETS
from config.blender_config import EXPORTS_DIR
from core import logging as log


def _select_only(objects):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_asset(asset, preset_name="fbx_generic", filename=None):
    """Export all of an asset's geometry/collision/rig objects using a named
    preset from EXPORT_PRESETS. Returns the output file path."""
    if preset_name not in EXPORT_PRESETS:
        raise ValueError(f"Unknown export preset '{preset_name}'. Known: {sorted(EXPORT_PRESETS)}")

    preset = EXPORT_PRESETS[preset_name]
    fmt = preset["format"]
    filename = filename or f"{asset.name}.{('glb' if fmt == 'gltf' else fmt)}"
    out_path = os.path.join(EXPORTS_DIR, filename)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    objects = list(asset.geometry_objects) + list(asset.collision_objects)
    _select_only(objects)
    kwargs = dict(preset["kwargs"])
    kwargs["use_selection"] = True if fmt in ("fbx", "obj") else kwargs.get("use_selection", True)

    if fmt == "fbx":
        bpy.ops.export_scene.fbx(filepath=out_path, **kwargs)
    elif fmt == "gltf":
        kwargs["use_selection"] = True
        bpy.ops.export_scene.gltf(filepath=out_path, **kwargs)
    elif fmt == "obj":
        bpy.ops.wm.obj_export(filepath=out_path, **kwargs)
    else:
        raise ValueError(f"Unsupported export format '{fmt}'")

    asset.export_status = f"exported:{preset_name}"
    log.info(f"Exported '{asset.name}' -> {out_path}")
    return out_path


def export_game_asset(asset, target="generic"):
    """Target-specific convenience wrapper. Only implements presets that have
    been verified — see config/export_config.py for the 'rust' caveat."""
    target_to_preset = {
        "generic": "fbx_generic",
        "gltf": "gltf_generic",
        "rust": "fbx_generic",  # no confirmed Blender->Rust pipeline; safe fallback
    }
    if target == "rust":
        log.warn(
            "No verified direct Blender export pipeline exists for Rust/RustEdit. "
            "Falling back to generic FBX export — validate manually before shipping."
        )
    preset_name = target_to_preset.get(target, "fbx_generic")
    return export_asset(asset, preset_name=preset_name)

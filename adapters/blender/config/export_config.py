"""Per-target export presets.

Only settings verified against this Blender build's actual exporter
operators are included here. Extend EXPORT_PRESETS as new targets are
validated — do not invent settings for engines that haven't been tested.
"""

# Generic, engine-agnostic presets built from bpy.ops.export_scene.fbx /
# .gltf / bpy.ops.wm.obj_export kwargs that exist in Blender 5.2.2.
EXPORT_PRESETS = {
    "fbx_generic": {
        "format": "fbx",
        "kwargs": dict(
            use_selection=False,
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_ALL",
            object_types={"MESH", "ARMATURE", "EMPTY"},
            use_mesh_modifiers=True,
            mesh_smooth_type="FACE",
            add_leaf_bones=False,
            bake_anim=True,
        ),
    },
    "gltf_generic": {
        "format": "gltf",
        "kwargs": dict(
            export_format="GLB",
            export_apply=True,
            export_yup=True,
            export_animations=True,
        ),
    },
    "obj_generic": {
        "format": "obj",
        "kwargs": dict(
            export_selected_objects=False,
            apply_modifiers=True,
        ),
    },
}

# NOTE on "rust" target: RustEdit / Facepunch's Rust does not officially
# document a Blender export pipeline for user-authored maps — asset
# import into Rust servers typically goes through Unity + Oxide/Carbon
# bundles, not a direct Blender exporter. Until that pipeline is
# confirmed, export_game_asset(target="rust") falls back to fbx_generic
# and logs a warning rather than fabricating Rust-specific settings.
#
# Related, and worth remembering when that pipeline eventually gets built:
# official monument IDs like "launch_site_1" only exist for vanilla
# prefabs bundled in Rust's own core files — a custom monument built from
# Blender-exported geometry is just a cluster of base prefabs saved as a
# RustEdit map-file package, with no such ID of its own. The modding
# community's workarounds (as of the community's own docs, not verified
# by us against a running server):
#   - Drop a `monument_marker.prefab` entity onto the custom monument in
#     RustEdit — registers it on the in-game map and makes it readable by
#     server plugins.
#   - Oxide/uMod plugins (Monument Finder, Monument Names API) track
#     coordinates and assign a dynamic ID string based on grid position
#     for server-side systems to reference.
# Neither is a Blender-side export setting — they're RustEdit/server-side
# steps that would come after whatever this framework exports.

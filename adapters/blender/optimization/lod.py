"""LOD generation via decimation. Choose levels based on the asset, don't
blindly generate LOD0-3 for everything (see project brief section 13)."""
import bpy

from core.naming import lod_name


def generate_decimated_lod(asset, part_name, source_obj, level, ratio):
    """Duplicate source_obj, decimate it to `ratio` of its polycount, register
    it as LOD<level> on the asset."""
    bpy.context.view_layer.objects.active = source_obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    source_obj.select_set(True)
    bpy.ops.object.duplicate()
    lod_obj = bpy.context.active_object
    lod_obj.name = lod_name(asset.name, part_name, level)
    lod_obj.data.name = lod_obj.name + "_mesh"

    mod = lod_obj.modifiers.new("Decimate", type="DECIMATE")
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = lod_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # LOD1+ occupies the same transform as its source — only one LOD should
    # be visible/rendered at a time (a game engine swaps them by distance),
    # so hide every level above 0 by default to avoid overlapping geometry.
    if level > 0:
        lod_obj.hide_render = True
        lod_obj.hide_set(True)

    return asset.add_lod(level, lod_obj)

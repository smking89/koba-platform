"""Centralized material creation/caching. Generators should call get_or_create
instead of building bpy.data.materials directly, so identical materials are
reused instead of duplicated across an asset."""
import bpy


def get_or_create(name, build_fn):
    """Return an existing material named `name`, or build one with `build_fn(mat)`."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    build_fn(mat)
    return mat


def set_principled(mat, base_color=None, metallic=None, roughness=None,
                    emission_color=None, emission_strength=0.0, alpha=None):
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    if base_color is not None:
        bsdf.inputs["Base Color"].default_value = (*base_color, 1.0) if len(base_color) == 3 else base_color
    if metallic is not None:
        bsdf.inputs["Metallic"].default_value = metallic
    if roughness is not None:
        bsdf.inputs["Roughness"].default_value = roughness
    if emission_color is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission_color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha is not None:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"

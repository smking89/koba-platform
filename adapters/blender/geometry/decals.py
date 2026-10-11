"""Single-face logo decals — stamps one image onto one face of an
existing box (via a second material slot), instead of texturing the
whole material like textures.texture_manager.apply_image_textures does.
Built for the Cube Clash sponsor-skin pipeline: an advertiser's logo PNG
needs to sit on one face of a voxel block, not wrap the whole mesh.

Relies on create_box's existing cube_project UV unwrap (geometry.
mesh_utils.simple_box_uv_unwrap) already giving each face a roughly
0..1 UV quad from its own facing direction — good enough for a flat
logo decal on a cube face, no custom UV island packing needed.
"""
import bpy

from geometry.detailing import find_face_by_normal
from materials.material_manager import get_or_create


def _logo_material(name, image_path):
    def build(mat):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")

        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image_path, check_existing=True)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

        if tex.image.depth in (32, 64):  # has an alpha channel
            links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method = "CLIP"

        bsdf.inputs["Roughness"].default_value = 0.7
    return get_or_create(name, build)


def apply_logo_decal(obj, image_path, material_name, normal_axis="z", sign=1):
    """Stamps `image_path` onto the face of `obj` facing (normal_axis, sign)
    (default: the top face) by appending a dedicated logo material as a
    new slot and assigning that one face to it. Every other face keeps
    its existing material. Returns the face index that was stamped."""
    logo_mat = _logo_material(material_name, image_path)
    obj.data.materials.append(logo_mat)
    decal_slot = len(obj.data.materials) - 1

    face_index = find_face_by_normal(obj, normal_axis=normal_axis, sign=sign)
    obj.data.polygons[face_index].material_index = decal_slot
    return face_index

"""Flat brand-color materials — for assets whose color comes from an
advertiser's hex code at request time, not from a curated material
library (see materials/pbr_library.py for that case). Matte by default
(roughness ~0.7) to match Cube Clash's voxel art style guide."""
from materials.material_manager import get_or_create, set_principled


def hex_to_rgb(hex_color):
    """'#3B82F6' or '3B82F6' -> (r, g, b) floats in 0..1."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got {hex_color!r}")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def simple_color_material(name, hex_color, roughness=0.7, metallic=0.0):
    def build(mat):
        set_principled(mat, base_color=hex_to_rgb(hex_color), metallic=metallic, roughness=roughness)
    return get_or_create(name, build)

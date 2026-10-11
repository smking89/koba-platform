"""Reusable metal material generators."""
from materials.material_manager import get_or_create, set_principled


def painted_metal(name, color=(0.6, 0.05, 0.05), roughness=0.4):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness)
    return get_or_create(name, build)


def bare_metal(name, roughness=0.3):
    def build(mat):
        set_principled(mat, base_color=(0.6, 0.6, 0.6), metallic=1.0, roughness=roughness)
    return get_or_create(name, build)


def rusted_metal(name, rust_amount=0.35):
    def build(mat):
        base = (0.55, 0.5, 0.45)
        rust = (0.35, 0.14, 0.05)
        mixed = tuple(b * (1 - rust_amount) + r * rust_amount for b, r in zip(base, rust))
        set_principled(mat, base_color=mixed, metallic=0.6 * (1 - rust_amount), roughness=0.5 + 0.4 * rust_amount)
    return get_or_create(name, build)


def galvanized_steel(name):
    def build(mat):
        set_principled(mat, base_color=(0.65, 0.67, 0.7), metallic=0.9, roughness=0.35)
    return get_or_create(name, build)

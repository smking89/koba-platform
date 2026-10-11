"""Reusable glass material generator — the curtain-wall/glazing material
category this framework didn't have yet (wood/metal/candy/plastic/stone
existed, nothing transparent). KOBA CASINO & RESORT's grand entrance,
tower curtain wall, and most interior storefronts all need real glass,
not a painted-opaque stand-in."""
from materials.material_manager import get_or_create, set_principled


def curtain_wall_glass(name, tint=(0.55, 0.65, 0.7), roughness=0.05, alpha=0.35):
    """Bright, lightly-tinted architectural glass — large exterior panels."""
    def build(mat):
        set_principled(mat, base_color=tint, metallic=0.0, roughness=roughness, alpha=alpha)
    return get_or_create(name, build)


def tinted_glass(name, tint=(0.15, 0.2, 0.22), roughness=0.08, alpha=0.5):
    """Darker, more opaque glass — interior partitions, VIP booths."""
    def build(mat):
        set_principled(mat, base_color=tint, metallic=0.0, roughness=roughness, alpha=alpha)
    return get_or_create(name, build)

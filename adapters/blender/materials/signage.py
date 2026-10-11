"""Reusable emissive signage material generator — the lit-sign/display
category this framework didn't have yet. KOBA CASINO & RESORT's jackpot
displays, arcade leaderboards, and nightclub/event signage all need a
real emissive surface, not a flat-colored stand-in that only reads as
"lit" in a renderer that fakes bloom."""
from materials.material_manager import get_or_create, set_principled


def emissive_sign(name, color=(1.0, 0.8, 0.1), strength=3.0, roughness=0.3):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness,
                        emission_color=color, emission_strength=strength)
    return get_or_create(name, build)

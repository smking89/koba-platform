"""Reusable glossy-plastic/fiberglass material generator — the vehicle-
body material category this framework didn't have yet (wood/metal/candy
existed; jet ski/boat hulls with a painted fiberglass finish need
something non-metallic and glossier than painted_wood)."""
from materials.material_manager import get_or_create, set_principled


def glossy_plastic(name, color=(0.9, 0.1, 0.1), roughness=0.15):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness)
    return get_or_create(name, build)

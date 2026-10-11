"""Reusable wood material generator (procedural, no external textures)."""
from materials.material_manager import get_or_create, set_principled


def painted_wood(name, color=(0.35, 0.22, 0.1), roughness=0.6):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")

        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 12.0
        noise.inputs["Detail"].default_value = 4.0

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * 0.7 for c in color], 1.0)
        ramp.color_ramp.elements[1].color = (*color, 1.0)

        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return get_or_create(name, build)

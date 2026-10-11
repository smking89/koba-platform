"""Reusable stone material generator — the monument/architecture material
category this framework didn't have yet (wood/metal/candy/plastic
existed, nothing rough-and-matte gray for stonework)."""
from materials.material_manager import get_or_create, set_principled


def carved_stone(name, color=(0.55, 0.53, 0.5), roughness=0.85):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")

        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 8.0
        noise.inputs["Detail"].default_value = 6.0

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * 0.75 for c in color], 1.0)
        ramp.color_ramp.elements[1].color = (*color, 1.0)

        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return get_or_create(name, build)

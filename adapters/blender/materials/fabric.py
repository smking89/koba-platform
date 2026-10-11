"""Reusable fabric material generator — the matte-upholstery category
this framework didn't have yet (every prior bed/sofa/pillow in this
project reused materials.plastic.glossy_plastic, which is wrong for
cloth: real fabric is matte, not glossy). Hotel bed linens, sofa
cushions, and pillows all need this, not a repurposed vehicle-body
material.

Uses a real procedural weave bump (noise -> bump node -> Normal input),
the same noise-driven-surface-variation pattern materials.wood/.stone
already use for their color — fabric's defining visual trait is surface
texture, not color variation, so the bump is the one that matters here.
"""
from materials.material_manager import get_or_create, set_principled


def woven_fabric(name, color=(0.8, 0.8, 0.75), roughness=0.88, weave_scale=60.0, bump_strength=0.15):
    def build(mat):
        set_principled(mat, base_color=color, metallic=0.0, roughness=roughness)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")

        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = weave_scale
        noise.inputs["Detail"].default_value = 2.0

        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength

        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return get_or_create(name, build)

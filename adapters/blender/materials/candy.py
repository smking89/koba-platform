"""Gummy/jelly candy material — translucent, glossy, colored subsurface
look. Socket names verified directly against this Blender 5.2.2 build's
Principled BSDF v2 (`Subsurface Weight`, `Transmission Weight`, etc. —
these differ from pre-4.0 Blender's `Subsurface`/`Transmission` names,
confirmed by inspecting bsdf.inputs rather than assumed from old docs).
"""
from materials.material_manager import get_or_create


def gummy_material(name, color=(0.95, 0.05, 0.08), transmission=0.95, subsurface=0.3,
                    roughness=0.02, ior=1.5, subsurface_scale=0.5):
    """A candy/gummy-bear style material: very high transmission + low
    roughness for genuine see-through glassy translucency, with a
    strongly-tinted subsurface scatter so light passing through picks up
    the candy's own color rather than washing out white.

    IMPORTANT — this material needs two things to actually look gummy,
    both confirmed by direct rendering, not assumed:
    1. **Cycles, not EEVEE.** EEVEE Next's transmission is screen-space
       only, and on a solid/complex mesh it can't properly trace light
       through the far side — it renders flat dark opaque red no matter
       how these values are tuned. Pass `engine="CYCLES"` to
       core.preview.render_preview; for the live GUI viewport, set
       `scene.render.engine = 'CYCLES'` and use "Rendered" shading (not
       "Material Preview", which uses a fixed studio light and ignores
       the scene).
    2. **Even light from all directions, not just directional suns.**
       Two hard sun lamps only light the material from the angles they
       point at, leaving most of the surface looking flat and opaque.
       Use core.scene.setup_studio_world_lighting() — it decouples a
       bright even light source from what the camera actually sees as
       the backdrop, so the material glows uniformly without blowing the
       background out to white.

    `color` also tints the subsurface radius (biased toward the color's
    dominant channel) so thicker parts of the mesh glow with the candy's
    own hue rather than washing out to white."""
    def build(mat):
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            return
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["IOR"].default_value = ior
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
        bsdf.inputs["Subsurface Radius"].default_value = (color[0], color[1] * 0.3, color[2] * 0.3)
        bsdf.inputs["Subsurface Scale"].default_value = subsurface_scale

        # Only relevant if this material is ever rendered in EEVEE — still
        # set for robustness, but Cycles (recommended above) ignores these
        # entirely and does the right thing regardless.
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = True
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"

    return get_or_create(name, build)

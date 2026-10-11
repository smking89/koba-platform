"""Scene-level setup/teardown utilities."""
import bpy


def reset_scene():
    """Clear the current scene back to an empty state (background-mode safe)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_studio_world_lighting(light_strength=5.0, light_color=(1.0, 1.0, 1.0),
                                 backdrop_color=(0.05, 0.05, 0.06), backdrop_strength=1.0):
    """Decouples "how much light illuminates the scene" from "what color
    the camera sees directly behind objects" — required for any
    transmission/subsurface material (e.g. materials.candy.gummy_material)
    to look genuinely translucent rather than dark and muddy.

    Why: a transmissive material needs strong, even light coming from
    ALL directions to glow — two hard directional suns only light it from
    the specific angles they point at. Just cranking the world background
    strength up achieves the even light, but then the background itself
    blows out to a flat white in the render. Cycles' Light Path "Is Camera
    Ray" output lets us route camera rays (what's directly visible) to a
    dim neutral backdrop while every other ray (light bouncing through/
    around the object) sees the bright environment — confirmed by direct
    rendering comparison, including one iteration where the Mix Shader
    inputs were accidentally swapped and produced the exact opposite
    (bright backdrop, dark object) of what was intended.

    Only takes effect under Cycles — EEVEE doesn't evaluate Light Path
    the same way and this node setup will just look like the dim backdrop
    color there."""
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    light_bg = nt.nodes.new("ShaderNodeBackground")
    light_bg.inputs["Color"].default_value = (*light_color, 1.0)
    light_bg.inputs["Strength"].default_value = light_strength

    visible_bg = nt.nodes.new("ShaderNodeBackground")
    visible_bg.inputs["Color"].default_value = (*backdrop_color, 1.0)
    visible_bg.inputs["Strength"].default_value = backdrop_strength

    light_path = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    output = nt.nodes.new("ShaderNodeOutputWorld")

    nt.links.new(light_path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    # Fac=0 (not a camera ray -> a bounce used for illumination) -> input 1 -> bright light.
    # Fac=1 (is a camera ray -> directly visible) -> input 2 -> dim visible backdrop.
    nt.links.new(light_bg.outputs["Background"], mix.inputs[1])
    nt.links.new(visible_bg.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], output.inputs["Surface"])

    bpy.context.scene.world = world
    return world


def frame_objects(objects):
    """Select `objects` and frame them in the first available 3D viewport.
    Only meaningful with a real GUI window (interactive mode) — in
    headless/background mode there is no VIEW_3D area to override, so this
    is a no-op there."""
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]

    framed = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            # Default "Solid" shading doesn't show real material colors, which
            # makes freshly-generated geometry look flat gray for no visible
            # reason — switch to Material Preview so what the user sees
            # actually reflects the materials the build script assigned.
            for space in area.spaces:
                if space.type == "VIEW_3D" and space.shading.type == "SOLID":
                    space.shading.type = "MATERIAL"
            if framed:
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.view3d.view_selected()
            framed = True
    return framed


def prepare_scene(asset_name, interactive):
    """Standard entry point every builder should call before constructing an
    asset. Headless (interactive=False) gets a full factory reset — cheap
    and safe since that process exits right after. Interactive mode only
    clears this one asset's own previous geometry, preserving everything
    else already in the live session."""
    if interactive:
        clear_asset_collection(asset_name)
    else:
        reset_scene()


def clear_asset_collection(asset_name):
    """Non-destructively remove a previously generated asset's own
    ASSET_<name> collection hierarchy (objects, meshes, the collections
    themselves) without touching anything else in the scene. Use this
    instead of reset_scene() when iterating on one asset inside a
    persistent interactive session."""
    root_name = f"ASSET_{asset_name}"
    root = bpy.data.collections.get(root_name)
    if root is None:
        return

    def _collect(coll):
        objs = list(coll.objects)
        for child in coll.children:
            objs.extend(_collect(child))
        return objs

    for obj in _collect(root):
        mesh = obj.data if obj.type == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    def _remove_children(coll):
        for child in list(coll.children):
            _remove_children(child)
            coll.children.unlink(child)
            bpy.data.collections.remove(child)

    _remove_children(root)
    for parent in bpy.data.collections:
        if root.name in parent.children.keys():
            parent.children.unlink(root)
    if root.name in bpy.context.scene.collection.children.keys():
        bpy.context.scene.collection.children.unlink(root)
    bpy.data.collections.remove(root)


def new_camera(location, rotation_euler, name="CAM_Preview"):
    cam_data = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = location
    cam_obj.rotation_euler = rotation_euler
    bpy.context.scene.collection.objects.link(cam_obj)
    return cam_obj


def new_sun(name="LGT_Sun", energy=3.0, rotation_euler=(0.9, 0.0, 0.7)):
    light_data = bpy.data.lights.new(name, type="SUN")
    light_data.energy = energy
    light_obj = bpy.data.objects.new(name, light_data)
    light_obj.rotation_euler = rotation_euler
    bpy.context.scene.collection.objects.link(light_obj)
    return light_obj

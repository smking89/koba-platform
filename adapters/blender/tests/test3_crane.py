"""TEST 3: Mechanical crane.

First asset with a multi-part mechanical rig: base/slew rotation, boom
pitch, and a hook winch that tracks the boom tip horizontally while
dropping independently in world Z (rigging.mechanical.add_copy_location_constraint).

Known, documented limitation: the cable is straight geometry sized at the
rest pose (geometry.primitives.create_cable) — it will not visually
stretch as the boom pitches or the hook drops. A correct version needs a
Stretch-To constraint on a Y-aligned mesh; not implemented yet.

Run headless:
  <blender> -b --python tests/test3_crane.py

Run live, staged:
  python3 scripts/blender_client.py -c "from tests.test3_crane import *; asset = stage_init(interactive=True)"
  python3 scripts/blender_client.py -c "stage_base_and_slew(asset)"
  python3 scripts/blender_client.py -c "stage_boom(asset)"
  python3 scripts/blender_client.py -c "stage_hook_and_cable(asset)"
  python3 scripts/blender_client.py -c "stage_collision(asset)"
  python3 scripts/blender_client.py -c "stage_animation(asset)"
  python3 scripts/blender_client.py -c "stage_finalize(asset, interactive=True)"
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402
import mathutils  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms, set_origin_to_point, parent_keep_transform  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.entity_metadata import for_mechanism, for_rigid_group_member  # noqa: E402
from geometry.primitives import create_box, create_cylinder, create_cable  # noqa: E402
from materials.metal import painted_metal, galvanized_steel, bare_metal  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from rigging.mechanical import create_hinge, create_slider, create_follow_point, add_copy_location_constraint  # noqa: E402
from animation.mechanical import animate_hinge_rotation, animate_slider_translation  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

DEFAULT_PARAMS = dict(
    base_size=1.6, base_height=0.3,
    tower_radius=0.15, tower_height=3.0,
    cab_size=(0.5, 0.5, 0.4),
    boom_length=3.2, boom_height=0.15, boom_depth=0.15,
    counter_jib_length=1.2, counterweight_size=(0.4, 0.4, 0.4),
    hook_drop=1.5, hook_size=0.15,
    slew_deg=50, boom_pitch_deg=-15, hook_lower=0.7,
    end_frame=60,
)


def stage_init(interactive=False, **params):
    """STAGE 01 — scene init + asset + materials."""
    dims = {**DEFAULT_PARAMS, **params}
    prepare_scene("Crane", interactive)
    asset = Asset(name="Crane", asset_type="machinery")
    asset.params = dims

    yellow = painted_metal(make_name("material", asset.name, "Yellow"), color=(0.85, 0.6, 0.05), roughness=0.45)
    steel = galvanized_steel(make_name("material", asset.name, "Steel"))
    dark = painted_metal(make_name("material", asset.name, "Dark"), color=(0.08, 0.08, 0.09), roughness=0.5)
    cable_mat = bare_metal(make_name("material", asset.name, "Cable"), roughness=0.6)
    for mat in (yellow, steel, dark, cable_mat):
        asset.register_material(mat.name)
    asset.materials = {"yellow": yellow, "steel": steel, "dark": dark, "cable": cable_mat}

    return asset


def stage_base_and_slew(asset):
    """STAGE 02 — primary geometry: static base + the slew hinge that carries
    everything above it (tower, cab, counter-jib, counterweight, winch)."""
    d = asset.params

    base = create_box(make_name("mesh", asset.name, "Base"),
                       width=d["base_size"], depth=d["base_size"], height=d["base_height"],
                       bevel_width=0.01, material=asset.materials["steel"])
    asset.add_geometry(base)

    slew_point = (0.0, 0.0, d["base_height"])
    # The slew hinge starts out carrying nothing; parts are attached to it as
    # they're built below with core.transforms.parent_keep_transform.
    slew_hinge = create_hinge(asset, "Slew", [], slew_point, axis="Z")
    asset.slew_hinge = slew_hinge

    tower = create_cylinder(make_name("mesh", asset.name, "Tower"),
                             radius=d["tower_radius"], depth=d["tower_height"], vertices=12,
                             material=asset.materials["yellow"])
    tower.location.z += d["base_height"]  # create_cylinder already sits the cylinder on its own origin (z=depth/2)
    apply_all_transforms(tower)
    parent_keep_transform(tower, slew_hinge)
    asset.add_geometry(tower, metadata=for_rigid_group_member(category="crane_turret"))

    cab_w, cab_d, cab_h = d["cab_size"]
    cab = create_box(make_name("mesh", asset.name, "Cab"), width=cab_w, depth=cab_d, height=cab_h,
                      bevel_width=0.005, material=asset.materials["dark"])
    cab.location = (d["tower_radius"] + cab_w / 2 - 0.05, 0.0, d["base_height"] + d["tower_height"] - cab_h)
    apply_all_transforms(cab)
    parent_keep_transform(cab, slew_hinge)
    asset.add_geometry(cab, metadata=for_rigid_group_member(category="crane_turret"))

    jib_h = 0.12
    counter_jib = create_box(make_name("mesh", asset.name, "CounterJib"),
                              width=d["counter_jib_length"], depth=jib_h, height=jib_h,
                              bevel_width=0.004, material=asset.materials["yellow"])
    counter_jib.location = (-d["counter_jib_length"] / 2, 0.0, d["base_height"] + d["tower_height"])
    apply_all_transforms(counter_jib)
    parent_keep_transform(counter_jib, slew_hinge)
    asset.add_geometry(counter_jib, metadata=for_rigid_group_member(category="crane_turret"))

    cw_w, cw_d, cw_h = d["counterweight_size"]
    counterweight = create_box(make_name("mesh", asset.name, "Counterweight"),
                                width=cw_w, depth=cw_d, height=cw_h,
                                bevel_width=0.005, material=asset.materials["dark"])
    counterweight.location = (-d["counter_jib_length"] + cw_w / 2, 0.0,
                               d["base_height"] + d["tower_height"] - cw_h / 2)
    apply_all_transforms(counterweight)
    parent_keep_transform(counterweight, slew_hinge)
    asset.add_geometry(counterweight, metadata=for_rigid_group_member(category="crane_turret"))

    winch_drum = create_cylinder(make_name("mesh", asset.name, "WinchDrum"),
                                  radius=0.08, depth=0.18, vertices=10, material=asset.materials["steel"])
    winch_drum.rotation_euler = (1.5708, 0, 0)
    winch_drum.location = (d["tower_radius"] + 0.05, 0.4, d["base_height"] + d["tower_height"] - 0.15)
    apply_all_transforms(winch_drum)
    parent_keep_transform(winch_drum, slew_hinge)
    asset.add_geometry(winch_drum, metadata=for_rigid_group_member(category="crane_turret"))

    return base, slew_hinge


def stage_boom(asset):
    """STAGE 03 — secondary geometry: the main boom, pitching on its own
    hinge which is itself nested inside the slew hinge."""
    d = asset.params
    boom_pivot = mathutils.Vector((0.0, 0.0, d["base_height"] + d["tower_height"]))

    boom = create_box(make_name("mesh", asset.name, "Boom"),
                       width=d["boom_length"], depth=d["boom_depth"], height=d["boom_height"],
                       bevel_width=0.004, material=asset.materials["yellow"])
    # Pivot at the near end, mid-height, so the boom swings from its base not its center.
    set_origin_to_point(boom, (-d["boom_length"] / 2, 0.0, d["boom_height"] / 2))
    boom.location = boom_pivot
    asset.add_geometry(boom, metadata=for_mechanism(category="crane_boom"))

    boom_hinge = create_hinge(asset, "Boom", boom, boom_pivot, axis="Y")
    parent_keep_transform(boom_hinge, asset.slew_hinge)  # nest pitch DOF inside slew DOF
    asset.boom_hinge = boom_hinge

    boom_tip_world = boom_pivot + mathutils.Vector((d["boom_length"], 0.0, 0.0))
    boom_tip = create_follow_point(asset, "Boom", boom_hinge, boom_tip_world)
    asset.boom_tip = boom_tip
    asset.boom_tip_world = boom_tip_world

    return boom, boom_hinge


def stage_hook_and_cable(asset):
    """STAGE 04 — tertiary geometry + rig: hook block on an independent
    vertical slider that tracks the boom tip horizontally (see module
    docstring for the cable's documented limitation)."""
    d = asset.params
    hook_rest = asset.boom_tip_world - mathutils.Vector((0.0, 0.0, d["hook_drop"]))

    hook = create_box(make_name("mesh", asset.name, "HookBlock"),
                       width=d["hook_size"], depth=d["hook_size"], height=d["hook_size"] * 1.3,
                       bevel_width=0.003, material=asset.materials["dark"])
    hook.location = hook_rest
    # NOTE: deliberately not apply_all_transforms() here — that bakes the
    # mesh and resets .location to (0,0,0), which would make the very next
    # line (create_slider reading hook.matrix_world.translation) capture
    # the wrong rest position. Only apply transforms on an object once
    # nothing downstream still needs to read its current .location/.matrix_world.
    asset.add_geometry(hook, metadata=for_mechanism(category="crane_hook"))

    hook_slider = create_slider(asset, "Hook", hook, slide_axis="Z")
    add_copy_location_constraint(hook_slider, asset.boom_tip, use_x=True, use_y=True, use_z=False,
                                  name="FollowBoomTipXY")
    asset.hook_slider = hook_slider

    cable = create_cable(make_name("mesh", asset.name, "Cable"),
                          start=asset.boom_tip_world, end=hook_rest, radius=0.012,
                          material=asset.materials["cable"])
    parent_keep_transform(cable, asset.boom_tip)
    asset.add_geometry(cable, metadata=for_mechanism(category="crane_cable", collision_required=False))

    return hook, cable


def stage_collision(asset):
    """STAGE 05 — box collision around the rest-pose geometry (doesn't track
    the animated boom/hook — same documented limitation as test 2's door)."""
    return generate_box_collision(asset, "Main", asset.geometry_objects)


def stage_animation(asset):
    """STAGE 06 — three independent keyframed DOFs: slew, boom pitch, hook drop."""
    d = asset.params
    end = d["end_frame"]

    slew_action = animate_hinge_rotation(asset, asset.slew_hinge, axis="Z", angle_deg=d["slew_deg"],
                                          part_name="Slew", start_frame=1, end_frame=end)
    boom_action = animate_hinge_rotation(asset, asset.boom_hinge, axis="Y", angle_deg=d["boom_pitch_deg"],
                                          part_name="Boom", start_frame=1, end_frame=end)
    hook_action = animate_slider_translation(asset, asset.hook_slider, axis="Z", distance=-d["hook_lower"],
                                              part_name="Hook", start_frame=1, end_frame=end)
    return slew_action, boom_action, hook_action


def stage_finalize(asset, interactive=False, preview_frame=None, save=True, export=True):
    """STAGE 07 — validate, preview, save, export."""
    preview_frame = preview_frame or asset.params["end_frame"]
    result = validate_asset(asset, poly_budget=8000)
    print(result.report())

    bpy.context.scene.frame_set(preview_frame)
    if interactive:
        frame_objects(asset.geometry_objects)
    else:
        preview_path = render_preview(asset, angle="three_quarter")
        print(f"Preview rendered: {preview_path}")
        bpy.context.scene.frame_set(1)

    if save:
        asset.save_asset_properties()
        os.makedirs(GENERATED_DIR, exist_ok=True)
        blend_path = os.path.join(GENERATED_DIR, f"{asset.name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"Saved: {blend_path}")

    if export and not interactive:
        out = export_asset(asset, preset_name="fbx_generic", filename=f"{asset.name}.fbx")
        print(f"Exported: {out}")

    print("SUMMARY:", asset.summary())
    return result


def build_crane(interactive=False, **params):
    asset = stage_init(interactive=interactive, **params)
    stage_base_and_slew(asset)
    stage_boom(asset)
    stage_hook_and_cable(asset)
    stage_collision(asset)
    stage_animation(asset)
    asset._last_validation = stage_finalize(asset, interactive=interactive)
    return asset


def main():
    asset = build_crane(interactive=False)
    if not asset._last_validation.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

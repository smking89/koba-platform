"""Bathroom set — toilet, sink, shower stall. Kept simple but
recognizable, per the user's own spec: real distinct fixtures, not
photorealistic plumbing.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_cylinder
from geometry.detailing import inset_panel, find_face_by_normal


def build_toilet(asset, name_prefix, x, y, z, mat=None):
    """A base + tank, cylinder-based bowl silhouette. z is the floor.
    Returns {"base","bowl","tank"}."""
    base = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_base"), radius=0.18, depth=0.38, material=mat)
    base.location.x, base.location.y, base.location.z = x, y, z
    apply_all_transforms(base)
    asset.add_geometry(base, metadata=for_static_prop(category="bathroom_toilet", importance="medium"))

    bowl = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_bowl"), radius=0.22, depth=0.12, material=mat)
    bowl.location.x, bowl.location.y, bowl.location.z = x, y, z + 0.38
    apply_all_transforms(bowl)
    asset.add_geometry(bowl, metadata=for_static_prop(category="bathroom_toilet", importance="medium"))

    tank = create_box(make_name("mesh", asset.name, f"{name_prefix}_tank"), width=0.38, depth=0.18, height=0.35, material=mat)
    tank.location.x, tank.location.y, tank.location.z = x, y - 0.25, z + 0.4
    apply_all_transforms(tank)
    asset.add_geometry(tank, metadata=for_static_prop(category="bathroom_toilet", importance="low"))

    return {"base": base, "bowl": bowl, "tank": tank}


def build_sink(asset, name_prefix, x, y, z, width=0.55, mat=None, faucet_mat=None):
    """A counter slab + a basin recess cue (a slightly inset top panel)
    + a faucet. z is the floor. Returns {"cabinet","basin","faucet"}."""
    cabinet_height = 0.75
    cabinet = create_box(make_name("mesh", asset.name, f"{name_prefix}_cabinet"), width=width, depth=0.45, height=cabinet_height, bevel_width=0.015, material=mat)
    cabinet.location.x, cabinet.location.y, cabinet.location.z = x, y, z
    apply_all_transforms(cabinet)
    cabinet_front = find_face_by_normal(cabinet, normal_axis="y", sign=-1)
    inset_panel(cabinet, cabinet_front, thickness=min(width, cabinet_height) * 0.12, depth=-0.008)
    asset.add_geometry(cabinet, metadata=for_static_prop(category="bathroom_sink", importance="medium"))

    basin = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_basin"), radius=width * 0.3, depth=0.08, material=mat)
    basin.location.x, basin.location.y, basin.location.z = x, y, z + cabinet_height
    apply_all_transforms(basin)
    asset.add_geometry(basin, metadata=for_static_prop(category="bathroom_sink", importance="medium"))

    faucet = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_faucet"), radius=0.02, depth=0.15, material=faucet_mat or mat)
    faucet.location.x, faucet.location.y, faucet.location.z = x, y - 0.15, z + cabinet_height + 0.08
    apply_all_transforms(faucet)
    asset.add_geometry(faucet, metadata=for_static_prop(category="bathroom_sink", importance="low"))

    return {"cabinet": cabinet, "basin": basin, "faucet": faucet}


def build_shower_stall(asset, name_prefix, x, y, z, width=0.9, depth=0.9, height=2.0, glass_mat=None, frame_mat=None, head_mat=None):
    """A glass enclosure (2 real glass panels + a frame) + a shower
    head. z is the floor. Returns {"panel_front","panel_side","frame",
    "shower_head"}."""
    frame = create_box(make_name("mesh", asset.name, f"{name_prefix}_frame"), width=width, depth=depth, height=0.03, material=frame_mat)
    frame.location.x, frame.location.y, frame.location.z = x, y, z
    apply_all_transforms(frame)
    asset.add_geometry(frame, metadata=for_static_prop(category="bathroom_shower", importance="low"))

    panel_front = create_box(make_name("mesh", asset.name, f"{name_prefix}_panel_front"), width=width, depth=0.03, height=height, material=glass_mat)
    panel_front.location.x, panel_front.location.y, panel_front.location.z = x, y - depth / 2, z + height / 2
    apply_all_transforms(panel_front)
    asset.add_geometry(panel_front, metadata=for_static_prop(category="bathroom_shower", importance="medium"))

    panel_side = create_box(make_name("mesh", asset.name, f"{name_prefix}_panel_side"), width=0.03, depth=depth, height=height, material=glass_mat)
    panel_side.location.x, panel_side.location.y, panel_side.location.z = x + width / 2, y, z + height / 2
    apply_all_transforms(panel_side)
    asset.add_geometry(panel_side, metadata=for_static_prop(category="bathroom_shower", importance="medium"))

    head = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_shower_head"), radius=0.06, depth=0.04, material=head_mat or frame_mat)
    head.rotation_euler.x = 1.5708
    head.location.x, head.location.y, head.location.z = x, y + depth / 2 - 0.1, z + height - 0.2
    apply_all_transforms(head)
    asset.add_geometry(head, metadata=for_static_prop(category="bathroom_shower", importance="low"))

    return {"frame": frame, "panel_front": panel_front, "panel_side": panel_side, "shower_head": head}

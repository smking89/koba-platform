"""Sofa / lounge seating assembly — a base cushion + backrest + 2 arms
on real turned feet, with real tufted inset panels on the backrest/arms
instead of flat boxes. Updated 2026-10-01 to pull from the shared
hardware module and the detailing toolkit, replacing the earlier flat-
box-only version.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box
from geometry.assemblies.furniture.hardware import build_turned_leg
from geometry.detailing import inset_panel, find_face_by_normal


def build_sofa(asset, name_prefix, x, y, z, width=2.0, depth=0.9, seat_mat=None, back_mat=None, arm_mat=None,
               leg_mat=None):
    """z is the floor. Returns {"base","backrest","arm_left","arm_right",
    "leg_000"...}."""
    parts = {}
    leg_height = 0.12
    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_leg{i:03d}", leg_height, 0.025, leg_mat or back_mat, steps=8)
        leg.location.x = x + lx * (width / 2 - 0.1)
        leg.location.y = y + ly * (depth / 2 - 0.1)
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"leg_{i:03d}"] = leg

    seat_height = 0.45
    base = create_box(make_name("mesh", asset.name, f"{name_prefix}_base"), width=width, depth=depth, height=seat_height, bevel_width=0.02, material=seat_mat)
    base.location.x, base.location.y, base.location.z = x, y, z + leg_height
    apply_all_transforms(base)
    base_top = find_face_by_normal(base, normal_axis="z", sign=1)
    inset_panel(base, base_top, thickness=0.08, depth=-0.015)
    asset.add_geometry(base, metadata=for_static_prop(category="furniture_sofa", importance="medium"))
    parts["base"] = base

    backrest_height = 0.5
    backrest = create_box(make_name("mesh", asset.name, f"{name_prefix}_backrest"), width=width, depth=0.15, height=backrest_height, bevel_width=0.02, material=back_mat)
    backrest.location.x, backrest.location.y, backrest.location.z = x, y - depth / 2 + 0.05, z + leg_height + seat_height + backrest_height / 2
    apply_all_transforms(backrest)
    # real tufted look: two side-by-side insets instead of one flat panel
    seg_width = width / 2
    back_front = find_face_by_normal(backrest, normal_axis="y", sign=-1)
    inset_panel(backrest, back_front, thickness=min(seg_width, backrest_height) * 0.18, depth=-0.012)
    asset.add_geometry(backrest, metadata=for_static_prop(category="furniture_sofa", importance="medium"))
    parts["backrest"] = backrest

    arm_height = 0.3
    for side, ox in (("left", -1), ("right", 1)):
        arm = create_box(make_name("mesh", asset.name, f"{name_prefix}_arm_{side}"), width=0.15, depth=depth, height=arm_height, bevel_width=0.015, material=arm_mat)
        arm.location.x, arm.location.y, arm.location.z = x + ox * (width / 2 - 0.05), y, z + leg_height + seat_height + arm_height / 2
        apply_all_transforms(arm)
        arm_top = find_face_by_normal(arm, normal_axis="z", sign=1)
        inset_panel(arm, arm_top, thickness=0.03, depth=-0.008)
        asset.add_geometry(arm, metadata=for_static_prop(category="furniture_sofa", importance="low"))
        parts[f"arm_{side}"] = arm

    return parts


def build_lounge_daybed(asset, name_prefix, x, y, z, length=2.0, width=0.8, cushion_mat=None, frame_mat=None):
    """A real poolside lounge chair on real turned feet: a tilted
    backrest cushion + a flat base cushion with a real inset seam line.
    z is the floor. Returns {"frame","base_cushion","back_cushion",
    "leg_000"...}."""
    parts = {}
    leg_height = 0.15
    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_leg{i:03d}", leg_height, 0.02, frame_mat, steps=8)
        leg.location.x = x + lx * (width / 2 - 0.05)
        leg.location.y = y + ly * (length / 2 - 0.15)
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"leg_{i:03d}"] = leg

    frame_height = 0.1
    frame = create_box(make_name("mesh", asset.name, f"{name_prefix}_frame"), width=width, depth=length, height=frame_height, bevel_width=0.015, material=frame_mat)
    frame.location.x, frame.location.y, frame.location.z = x, y, z + leg_height
    apply_all_transforms(frame)
    asset.add_geometry(frame, metadata=for_static_prop(category="furniture_lounge", importance="low"))
    parts["frame"] = frame

    cushion_z = z + leg_height + frame_height
    base_cushion = create_box(make_name("mesh", asset.name, f"{name_prefix}_base_cushion"), width=width - 0.05, depth=length * 0.65, height=0.08, bevel_width=0.02, material=cushion_mat)
    base_cushion.location.x, base_cushion.location.y, base_cushion.location.z = x, y - length * 0.15, cushion_z
    apply_all_transforms(base_cushion)
    base_top = find_face_by_normal(base_cushion, normal_axis="z", sign=1)
    inset_panel(base_cushion, base_top, thickness=0.04, depth=0.0)
    asset.add_geometry(base_cushion, metadata=for_static_prop(category="furniture_lounge", importance="low"))
    parts["base_cushion"] = base_cushion

    back_cushion = create_box(make_name("mesh", asset.name, f"{name_prefix}_back_cushion"), width=width - 0.05, depth=length * 0.35, height=0.08, bevel_width=0.02, material=cushion_mat)
    back_cushion.location.x, back_cushion.location.y, back_cushion.location.z = x, y + length * 0.32, cushion_z + 0.15
    back_cushion.rotation_euler.x = -0.5
    apply_all_transforms(back_cushion)
    asset.add_geometry(back_cushion, metadata=for_static_prop(category="furniture_lounge", importance="low"))
    parts["back_cushion"] = back_cushion

    return parts

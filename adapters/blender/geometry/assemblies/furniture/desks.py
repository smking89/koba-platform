"""Desk + chair, and nightstand assemblies.

Legs are real LATHED profiles (geometry.assemblies.furniture.hardware.
build_turned_leg) with explicit collars/notches/taper — a genuine turned-
leg silhouette, not a bare cylinder. The nightstand drawer gets a real
lathed knob instead of a flat inset face. Updated 2026-10-01 to pull
from the shared hardware module rather than defining its own leg
profile inline.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box
from geometry.assemblies.furniture.hardware import build_turned_leg, build_drawer_knob
from geometry.detailing import inset_panel, find_face_by_normal

LEG_RADIUS = 0.025


def build_desk_and_chair(asset, name_prefix, x, y, z, desk_width=1.2, desk_depth=0.6, desk_height=0.75,
                          top_mat=None, leg_mat=None, chair_mat=None):
    """A desk with 4 real turned legs + a top, plus a simple chair (seat
    + backrest + 4 real turned legs) placed in front of it. z is the
    floor. Returns {"desk_top","desk_leg_000"..., "chair_seat",
    "chair_back","chair_leg_000"...}."""
    parts = {}
    top_thickness = 0.04
    top = create_box(make_name("mesh", asset.name, f"{name_prefix}_desk_top"), width=desk_width, depth=desk_depth, height=top_thickness, bevel_width=0.015, material=top_mat)
    top.location.x, top.location.y, top.location.z = x, y, z + desk_height - top_thickness / 2
    apply_all_transforms(top)
    asset.add_geometry(top, metadata=for_static_prop(category="furniture_desk", importance="medium"))
    parts["desk_top"] = top

    leg_height = desk_height - top_thickness
    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_desk_leg{i:03d}", leg_height, LEG_RADIUS, leg_mat)
        leg.location.x = x + lx * (desk_width / 2 - 0.05)
        leg.location.y = y + ly * (desk_depth / 2 - 0.05)
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"desk_leg_{i:03d}"] = leg

    chair_y = y + desk_depth / 2 + 0.3
    seat_height = 0.45
    seat = create_box(make_name("mesh", asset.name, f"{name_prefix}_chair_seat"), width=0.45, depth=0.45, height=0.05, bevel_width=0.015, material=chair_mat)
    seat.location.x, seat.location.y, seat.location.z = x, chair_y, z + seat_height
    apply_all_transforms(seat)
    asset.add_geometry(seat, metadata=for_static_prop(category="furniture_chair", importance="low"))
    parts["chair_seat"] = seat

    back = create_box(make_name("mesh", asset.name, f"{name_prefix}_chair_back"), width=0.45, depth=0.04, height=0.5, bevel_width=0.015, material=chair_mat)
    back.location.x, back.location.y, back.location.z = x, chair_y + 0.2, z + seat_height + 0.25
    apply_all_transforms(back)
    back_front = find_face_by_normal(back, normal_axis="y", sign=-1)
    inset_panel(back, back_front, thickness=0.06, depth=-0.006)
    asset.add_geometry(back, metadata=for_static_prop(category="furniture_chair", importance="low"))
    parts["chair_back"] = back

    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_chair_leg{i:03d}", seat_height, LEG_RADIUS, leg_mat)
        leg.location.x = x + lx * 0.18
        leg.location.y = chair_y + ly * 0.18
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"chair_leg_{i:03d}"] = leg

    return parts


def build_nightstand(asset, name_prefix, x, y, z, width=0.5, depth=0.4, height=0.55, body_mat=None,
                      drawer_mat=None, knob_mat=None):
    """A real body + a recessed drawer panel + a real lathed knob —
    not a single box standing in for 'nightstand'. z is the floor.
    Returns {"body","drawer","knob","leg_000"...}."""
    parts = {}
    leg_height = 0.08
    body_height = height - leg_height
    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_leg{i:03d}", leg_height, 0.018, body_mat, steps=8)
        leg.location.x = x + lx * (width / 2 - 0.04)
        leg.location.y = y + ly * (depth / 2 - 0.04)
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"leg_{i:03d}"] = leg

    body = create_box(make_name("mesh", asset.name, f"{name_prefix}_body"), width=width, depth=depth, height=body_height, bevel_width=0.015, material=body_mat)
    body.location.x, body.location.y, body.location.z = x, y, z + leg_height
    apply_all_transforms(body)
    asset.add_geometry(body, metadata=for_static_prop(category="furniture_nightstand", importance="low"))
    parts["body"] = body

    drawer = create_box(make_name("mesh", asset.name, f"{name_prefix}_drawer"), width=width * 0.8, depth=0.03, height=body_height * 0.3, bevel_width=0.008, material=drawer_mat)
    drawer.location.x, drawer.location.y, drawer.location.z = x, y - depth / 2 - 0.01, z + leg_height + body_height * 0.6
    apply_all_transforms(drawer)
    drawer_front = find_face_by_normal(drawer, normal_axis="y", sign=-1)
    inset_panel(drawer, drawer_front, thickness=min(width * 0.8, body_height * 0.3) * 0.15, depth=-0.006)
    asset.add_geometry(drawer, metadata=for_static_prop(category="furniture_nightstand", importance="low"))
    parts["drawer"] = drawer

    knob = build_drawer_knob(asset, f"{name_prefix}_knob", radius=0.012, depth=0.03, material=knob_mat or drawer_mat)
    knob.location.x, knob.location.y, knob.location.z = x, y - depth / 2 - 0.04, z + leg_height + body_height * 0.6
    apply_all_transforms(knob)
    parts["knob"] = knob

    return parts

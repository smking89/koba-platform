"""Bed assemblies — frame on real turned feet + mattress + headboard
(with a real recessed inset panel AND a row of real array-distributed
decorative studs along its border) + pillows, instead of Phase 4's
single bare box standing in for a bed. Updated 2026-10-01 to move past
a single inset into a fuller composed assembly.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box
from geometry.assemblies.furniture.hardware import build_turned_leg, build_stud_source
from geometry.detailing import inset_panel, find_face_by_normal, distribute_array_detail

# (size, width, depth) — real-ish bed footprints, not guessed arbitrarily.
BED_SIZES = {
    "single": (1.0, 2.0),
    "double": (1.5, 2.0),
    "king": (2.0, 2.1),
}


def build_bed(asset, name_prefix, x, y, z, size="double", frame_mat=None, mattress_mat=None,
              headboard_mat=None, pillow_mat=None, stud_mat=None, num_pillows=2):
    """z is the floor. `size` in ("single","double","king") picks a
    real footprint from BED_SIZES. Returns {"frame","mattress",
    "headboard","pillow_000",...,"leg_000"...,"stud_000"...}."""
    width, depth = BED_SIZES[size]
    parts = {}

    leg_height = 0.15
    for i, (lx, ly) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        leg = build_turned_leg(asset, f"{name_prefix}_leg{i:03d}", leg_height, 0.03, frame_mat, steps=10)
        leg.location.x = x + lx * (width / 2 - 0.08)
        leg.location.y = y + ly * (depth / 2 - 0.08)
        leg.location.z = z
        apply_all_transforms(leg)
        parts[f"leg_{i:03d}"] = leg

    frame_height = 0.3
    frame = create_box(make_name("mesh", asset.name, f"{name_prefix}_frame"), width=width, depth=depth, height=frame_height, bevel_width=0.02, material=frame_mat)
    frame.location.x, frame.location.y, frame.location.z = x, y, z + leg_height
    apply_all_transforms(frame)
    asset.add_geometry(frame, metadata=for_static_prop(category="furniture_bed_frame", importance="medium"))
    parts["frame"] = frame

    mattress_height = 0.25
    mattress_z = z + leg_height + frame_height
    mattress = create_box(make_name("mesh", asset.name, f"{name_prefix}_mattress"), width=width - 0.05, depth=depth - 0.05, height=mattress_height, bevel_width=0.03, bevel_segments=3, material=mattress_mat)
    mattress.location.x, mattress.location.y, mattress.location.z = x, y, mattress_z
    apply_all_transforms(mattress)
    asset.add_geometry(mattress, metadata=for_static_prop(category="furniture_bed_mattress", importance="medium"))
    parts["mattress"] = mattress

    headboard_height = 0.8
    headboard = create_box(make_name("mesh", asset.name, f"{name_prefix}_headboard"), width=width + 0.1, depth=0.08, height=headboard_height, bevel_width=0.02, material=headboard_mat)
    headboard.location.x, headboard.location.y, headboard.location.z = x, y - depth / 2, z + leg_height + frame_height / 2 + headboard_height / 2
    apply_all_transforms(headboard)
    headboard_front = find_face_by_normal(headboard, normal_axis="y", sign=1)
    inset_panel(headboard, headboard_front, thickness=min(width, headboard_height) * 0.15, depth=-0.01)
    asset.add_geometry(headboard, metadata=for_static_prop(category="furniture_bed_headboard", importance="medium"))
    parts["headboard"] = headboard

    # real array-distributed decorative studs along the headboard's top border
    stud_source = build_stud_source(asset, f"{name_prefix}_stud_source", radius=0.012, height=0.01, material=stud_mat or headboard_mat)
    stud_y = y - depth / 2 + 0.041
    studs = distribute_array_detail(
        asset, f"{name_prefix}_headboard_stud", stud_source,
        start=(x - width / 2 + 0.15, stud_y, z + leg_height + frame_height / 2 + headboard_height - 0.08),
        end=(x + width / 2 - 0.15, stud_y, z + leg_height + frame_height / 2 + headboard_height - 0.08),
        count=7, importance="low",
    )
    for j, stud in enumerate(studs):
        parts[f"stud_{j:03d}"] = stud

    pillow_w = (width - 0.1) / num_pillows
    for i in range(num_pillows):
        px = x - width / 2 + pillow_w * (i + 0.5)
        pillow = create_box(make_name("mesh", asset.name, f"{name_prefix}_pillow{i:03d}"), width=pillow_w - 0.05, depth=0.4, height=0.12, bevel_width=0.04, bevel_segments=3, material=pillow_mat)
        pillow.location.x, pillow.location.y, pillow.location.z = px, y - depth / 2 + 0.3, mattress_z + mattress_height
        apply_all_transforms(pillow)
        asset.add_geometry(pillow, metadata=for_static_prop(category="furniture_bed_pillow", importance="low"))
        parts[f"pillow_{i:03d}"] = pillow

    return parts

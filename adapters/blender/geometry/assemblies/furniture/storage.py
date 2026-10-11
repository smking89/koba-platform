"""Wardrobe / storage unit assembly — a body with real visible door
panels, each with a real recessed double-border inset
(geometry.detailing.inset_panel) AND real array-distributed hinge
hardware (geometry.detailing.distribute_array_detail) along the hinge
edge, instead of a flat, featureless door face. Updated 2026-10-01 to
move past a single inset into a fuller composed assembly.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box
from geometry.assemblies.furniture.hardware import build_stud_source
from geometry.detailing import inset_panel, find_face_by_normal, distribute_array_detail


def build_wardrobe(asset, name_prefix, x, y, z, width=1.2, depth=0.6, height=1.9,
                    body_mat=None, door_mat=None, hinge_mat=None, num_doors=2):
    """z is the floor. Returns {"body","door_000",...,"hinge_000_000"...}."""
    parts = {}
    body = create_box(make_name("mesh", asset.name, f"{name_prefix}_body"), width=width, depth=depth, height=height, bevel_width=0.015, material=body_mat)
    body.location.x, body.location.y, body.location.z = x, y, z
    apply_all_transforms(body)
    asset.add_geometry(body, metadata=for_static_prop(category="furniture_wardrobe", importance="medium"))
    parts["body"] = body

    hinge_source = build_stud_source(asset, f"{name_prefix}_hinge_source", radius=0.015, height=0.04, material=hinge_mat or door_mat)
    door_h = height - 0.05

    door_w = width / num_doors
    for i in range(num_doors):
        dx = x - width / 2 + door_w * (i + 0.5)
        door = create_box(make_name("mesh", asset.name, f"{name_prefix}_door{i:03d}"), width=door_w - 0.02, depth=0.02, height=door_h, material=door_mat)
        door.location.x, door.location.y, door.location.z = dx, y - depth / 2 - 0.01, z + height / 2
        apply_all_transforms(door)

        front_face = find_face_by_normal(door, normal_axis="y", sign=-1)
        # outer decorative border, then a deeper inner recessed panel -- a
        # real double-border look, not one flat inset.
        inset_panel(door, front_face, thickness=min(door_w, door_h) * 0.06, depth=-0.003)
        inner_face = find_face_by_normal(door, normal_axis="y", sign=-1)
        inset_panel(door, inner_face, thickness=min(door_w, door_h) * 0.14, depth=-0.01)

        asset.add_geometry(door, metadata=for_static_prop(category="furniture_wardrobe", importance="low"))
        parts[f"door_{i:03d}"] = door

        # real hinge hardware, array-distributed down the door's hinge edge
        hinge_x = dx - (door_w - 0.02) / 2 if i == 0 else dx + (door_w - 0.02) / 2
        hinges = distribute_array_detail(
            asset, f"{name_prefix}_door{i:03d}_hinge", hinge_source,
            start=(hinge_x, y - depth / 2 - 0.02, z + door_h * 0.15),
            end=(hinge_x, y - depth / 2 - 0.02, z + door_h * 0.85),
            count=3, importance="low",
        )
        for j, hinge in enumerate(hinges):
            parts[f"hinge_{i:03d}_{j:03d}"] = hinge

    return parts

"""Staircase assemblies — a straight flight of real individual riser
steps + an optional sloped handrail, instead of Phase 1's flat stepped-
tier boxes with no risers.
"""
import math

from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_cylinder
from geometry.assemblies.architecture.railings import POST_RADIUS


def build_staircase_straight(asset, name_prefix, x, y, z, num_steps=10, step_width=1.2,
                              step_depth=0.3, step_height=0.18, step_mat=None,
                              handrail_mat=None, direction="y"):
    """z is the floor at the BOTTOM of the flight. Steps ascend along
    +direction. Returns {"step_000"..., "handrail_post_000"...,
    "handrail"} (handrail keys only present if handrail_mat given)."""
    parts = {}
    for i in range(num_steps):
        step = create_box(make_name("mesh", asset.name, f"{name_prefix}_step{i:03d}"),
                           width=step_width, depth=step_depth, height=step_height * (i + 1), bevel_width=0.015, material=step_mat)
        offset = step_depth * i
        if direction == "y":
            step.location.x, step.location.y, step.location.z = x, y + offset, z
        else:
            step.location.x, step.location.y, step.location.z = x + offset, y, z
        apply_all_transforms(step)
        asset.add_geometry(step, metadata=for_static_prop(category="architecture_stair_step", importance="medium"))
        parts[f"step_{i:03d}"] = step

    if handrail_mat is not None:
        run_length = step_depth * num_steps
        total_rise = step_height * num_steps
        side_offset = step_width / 2 + 0.05

        post_count = max(2, num_steps // 2)
        for i in range(post_count):
            t = i / (post_count - 1)
            post_height = 0.9 + t * total_rise
            post = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_handrail_post{i:03d}"), radius=POST_RADIUS, depth=post_height, vertices=20, material=handrail_mat)
            offset = run_length * t
            if direction == "y":
                post.location.x, post.location.y, post.location.z = x + side_offset, y + offset, z
            else:
                post.location.x, post.location.y, post.location.z = x + offset, y + side_offset, z
            apply_all_transforms(post)
            asset.add_geometry(post, metadata=for_static_prop(category="architecture_handrail_post", importance="low"))
            parts[f"handrail_post_{i:03d}"] = post

        rail_length = (run_length ** 2 + total_rise ** 2) ** 0.5
        rail = create_box(make_name("mesh", asset.name, f"{name_prefix}_handrail"), width=0.05, depth=rail_length, height=0.05, bevel_width=0.015, material=handrail_mat)
        rail.rotation_euler.x = -math.atan2(total_rise, run_length) if run_length else 0.0
        if direction == "y":
            rail.location.x, rail.location.y, rail.location.z = x + side_offset, y + run_length / 2, z + 0.9 + total_rise / 2
        else:
            rail.location.x, rail.location.y, rail.location.z = x + run_length / 2, y + side_offset, z + 0.9 + total_rise / 2
        apply_all_transforms(rail)
        asset.add_geometry(rail, metadata=for_static_prop(category="architecture_handrail", importance="low"))
        parts["handrail"] = rail

    return parts

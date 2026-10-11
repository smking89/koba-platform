"""Simple roof / canopy assemblies — a roof slab + real support posts,
instead of Phase 1's single glass box standing in for a canopy.
"""
import math

from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_cylinder


def build_canopy(asset, name_prefix, x, y, z, width=6.0, depth=4.0, roof_thickness=0.2,
                  support_height=3.0, support_mat=None, roof_mat=None, post_radius=0.12):
    """A flat canopy roof on 4 corner posts. z is the floor (post
    base). Returns {"post_nw","post_ne","post_sw","post_se","roof"}."""
    parts = {}
    half_w, half_d = width / 2 - 0.3, depth / 2 - 0.3
    corners = {"nw": (-half_w, -half_d), "ne": (half_w, -half_d), "sw": (-half_w, half_d), "se": (half_w, half_d)}
    for corner, (ox, oy) in corners.items():
        post = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_post_{corner}"), radius=post_radius, depth=support_height, vertices=20, material=support_mat)
        post.location.x, post.location.y, post.location.z = x + ox, y + oy, z
        apply_all_transforms(post)
        asset.add_geometry(post, metadata=for_static_prop(category="architecture_canopy_post", importance="medium"))
        parts[f"post_{corner}"] = post

    roof = create_box(make_name("mesh", asset.name, f"{name_prefix}_roof"), width=width, depth=depth, height=roof_thickness, bevel_width=0.03, material=roof_mat)
    roof.location.x, roof.location.y, roof.location.z = x, y, z + support_height
    apply_all_transforms(roof)
    asset.add_geometry(roof, metadata=for_static_prop(category="architecture_canopy_roof", importance="high"))
    parts["roof"] = roof
    return parts


def build_gable_roof(asset, name_prefix, x, y, z, width=6.0, depth=4.0, pitch_height=1.5, thickness=0.15, mat=None):
    """Two angled panels meeting at a center ridge — a real pitched
    roof silhouette, not a flat slab. z is the eave height (where the
    panels start). Returns {"panel_left", "panel_right"}."""
    half_depth = depth / 2
    slope_length = math.sqrt(half_depth ** 2 + pitch_height ** 2)
    pitch_angle = math.atan2(pitch_height, half_depth)

    parts = {}
    for side, sign in (("left", -1), ("right", 1)):
        panel = create_box(make_name("mesh", asset.name, f"{name_prefix}_panel_{side}"), width=width, depth=slope_length, height=thickness, bevel_width=0.02, material=mat)
        panel.rotation_euler.x = sign * pitch_angle
        panel.location.x = x
        panel.location.y = y + sign * (half_depth / 2) * math.cos(pitch_angle)
        panel.location.z = z + (pitch_height / 2)
        apply_all_transforms(panel)
        asset.add_geometry(panel, metadata=for_static_prop(category="architecture_roof_panel", importance="high"))
        parts[f"panel_{side}"] = panel
    return parts

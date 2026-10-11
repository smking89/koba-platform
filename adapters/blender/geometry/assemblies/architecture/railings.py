"""Railing / balustrade assemblies — evenly-spaced posts + a top rail,
real parts instead of Phase 1/4/9's bare single rail bar.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_cylinder

POST_RADIUS = 0.04
RAIL_HEIGHT_DEFAULT = 0.9


def build_railing_straight(asset, name_prefix, x, y, z, length, height=RAIL_HEIGHT_DEFAULT,
                            post_spacing=1.0, orientation="x", post_mat=None, rail_mat=None):
    """A straight run along X or Y. Posts every `post_spacing` (at
    least 2, at the ends), one continuous top rail bar. Returns
    {"post_000"..., "top_rail"}."""
    parts = {}
    num_posts = max(2, int(length / post_spacing) + 1)
    for i in range(num_posts):
        t = i / (num_posts - 1) - 0.5  # -0.5..0.5 along the run
        post = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_post{i:03d}"), radius=POST_RADIUS, depth=height, vertices=20, material=post_mat)
        if orientation == "x":
            post.location.x, post.location.y, post.location.z = x + t * length, y, z
        else:
            post.location.x, post.location.y, post.location.z = x, y + t * length, z
        apply_all_transforms(post)
        asset.add_geometry(post, metadata=for_static_prop(category="architecture_railing_post", importance="low"))
        parts[f"post_{i:03d}"] = post

    rail_w, rail_d = (length, 0.06) if orientation == "x" else (0.06, length)
    top_rail = create_box(make_name("mesh", asset.name, f"{name_prefix}_top_rail"), width=rail_w, depth=rail_d, height=0.06, bevel_width=0.015, material=rail_mat)
    top_rail.location.x, top_rail.location.y, top_rail.location.z = x, y, z + height
    apply_all_transforms(top_rail)
    asset.add_geometry(top_rail, metadata=for_static_prop(category="architecture_railing_rail", importance="low"))
    parts["top_rail"] = top_rail
    return parts


def build_railing_corner(asset, name_prefix, x, y, z, length_x, length_y, height=RAIL_HEIGHT_DEFAULT,
                          post_spacing=1.0, post_mat=None, rail_mat=None):
    """Two straight runs meeting at the corner (x, y) — an L-shaped
    balustrade, e.g. around a raised platform's two open edges."""
    leg_x = build_railing_straight(asset, f"{name_prefix}_legX", x + length_x / 2, y, z, length_x,
                                    height=height, post_spacing=post_spacing, orientation="x",
                                    post_mat=post_mat, rail_mat=rail_mat)
    leg_y = build_railing_straight(asset, f"{name_prefix}_legY", x, y + length_y / 2, z, length_y,
                                    height=height, post_spacing=post_spacing, orientation="y",
                                    post_mat=post_mat, rail_mat=rail_mat)
    parts = {f"legX_{k}": v for k, v in leg_x.items()}
    parts.update({f"legY_{k}": v for k, v in leg_y.items()})
    return parts

"""Window assemblies — real frame + glass, not a single flat glass band.

Mid-level, reusable building blocks on top of geometry.primitives
(create_box) and materials.glass — every function here takes an Asset
and placement/size parameters, builds real geometry, registers it on
the asset, and returns a dict of the created Objects so a caller can
reuse them for instancing (geometry.instancing.create_instance) exactly
like Phase 4's hotel room templates already did.

All windows are placed facing -Y (consistent with every KOBA CASINO &
RESORT phase script's "entrance side" convention) in the wall plane at
world Z=z (window CENTER height), centered at world X=x. Rotate the
whole returned group yourself if a different wall orientation is
needed — these functions don't guess orientation.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box

FRAME_THICKNESS = 0.08
FRAME_DEPTH = 0.12
GLASS_DEPTH = 0.02


def _frame_and_glass(asset, name_prefix, x, y, z, width, height, frame_mat, glass_mat):
    """One real frame (4 bars) + one glass pane filling the opening.
    Returns {"frame_top", "frame_bottom", "frame_left", "frame_right", "glass"}."""
    parts = {}
    half_w, half_h = width / 2, height / 2

    bars = {
        "frame_top": (width, FRAME_THICKNESS, 0.0, half_h - FRAME_THICKNESS / 2),
        "frame_bottom": (width, FRAME_THICKNESS, 0.0, -half_h + FRAME_THICKNESS / 2),
        "frame_left": (FRAME_THICKNESS, height, -half_w + FRAME_THICKNESS / 2, 0.0),
        "frame_right": (FRAME_THICKNESS, height, half_w - FRAME_THICKNESS / 2, 0.0),
    }
    for part, (bw, bh, ox, oz) in bars.items():
        bar = create_box(make_name("mesh", asset.name, f"{name_prefix}_{part}"), width=bw, depth=FRAME_DEPTH, height=bh,
                          bevel_width=0.015, material=frame_mat)
        bar.location.x, bar.location.y, bar.location.z = x + ox, y, z + oz
        apply_all_transforms(bar)
        asset.add_geometry(bar, metadata=for_static_prop(category="architecture_window_frame", importance="low"))
        parts[part] = bar

    glass = create_box(make_name("mesh", asset.name, f"{name_prefix}_glass"),
                        width=width - 2 * FRAME_THICKNESS, depth=GLASS_DEPTH,
                        height=height - 2 * FRAME_THICKNESS, bevel_width=0.005, material=glass_mat)
    glass.location.x, glass.location.y, glass.location.z = x, y, z
    apply_all_transforms(glass)
    asset.add_geometry(glass, metadata=for_static_prop(category="architecture_window_glass", importance="low"))
    parts["glass"] = glass
    return parts


def build_window_single(asset, name_prefix, x, y, z, width=1.2, height=1.5, frame_mat=None, glass_mat=None):
    """One framed pane. Real part count: 5 (4 frame bars + 1 glass)."""
    return _frame_and_glass(asset, name_prefix, x, y, z, width, height, frame_mat, glass_mat)


def build_window_double(asset, name_prefix, x, y, z, width=2.2, height=1.5, frame_mat=None, glass_mat=None):
    """Two panes sharing a center mullion (modeled as each pane's
    adjoining frame_left/frame_right bars, slightly overlapping at the
    shared edge — a real double-casement look, not one wide pane)."""
    half_width = width / 2
    left = _frame_and_glass(asset, f"{name_prefix}_L", x - half_width / 2, y, z, half_width, height, frame_mat, glass_mat)
    right = _frame_and_glass(asset, f"{name_prefix}_R", x + half_width / 2, y, z, half_width, height, frame_mat, glass_mat)
    parts = {f"left_{k}": v for k, v in left.items()}
    parts.update({f"right_{k}": v for k, v in right.items()})
    return parts


def build_curtain_wall_segment(asset, name_prefix, x, y, z, width=6.0, height=3.0, cols=3, rows=2, frame_mat=None, glass_mat=None):
    """A grid of `cols` x `rows` individually-framed panes — a real
    curtain-wall look (mullions dividing the glazing into a grid), not
    Phase 1's single flat glass band. Returns a flat dict keyed
    "r{row}c{col}_{part}"."""
    pane_w, pane_h = width / cols, height / rows
    parts = {}
    for r in range(rows):
        for c in range(cols):
            px = x - width / 2 + pane_w * (c + 0.5)
            pz = z - height / 2 + pane_h * (r + 0.5)
            pane_parts = _frame_and_glass(asset, f"{name_prefix}_r{r}c{c}", px, y, pz, pane_w, pane_h, frame_mat, glass_mat)
            for k, v in pane_parts.items():
                parts[f"r{r}c{c}_{k}"] = v
    return parts

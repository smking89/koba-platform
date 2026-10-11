"""Spandrel / floor-edge profile assembly — a real reusable version of
the perimeter-ring pattern Phase 2's `koba_casino_02_floors.py` and
Phase 6's `koba_casino_06b_conference.py` each built inline.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box


def build_spandrel_band(asset, name_prefix, x, y, z, width, depth, thickness=0.3, height=1.0, mat=None,
                         door_gap=None, door_side="north"):
    """A 4-segment rectangular band at a floor's edge. If `door_gap` is
    given, the named side is split into two segments leaving that gap
    open (matching the door-opening pattern used throughout Phases
    2/6/7/9). Returns {"wall_south","wall_north","wall_west","wall_east"}
    (north split into "wall_north_a"/"wall_north_b" when door_gap is used
    and door_side="north", etc.)."""
    half_w, half_d = width / 2, depth / 2
    sides = {
        "south": (width, thickness, 0.0, -half_d),
        "north": (width, thickness, 0.0, half_d),
        "west": (thickness, depth, -half_w, 0.0),
        "east": (thickness, depth, half_w, 0.0),
    }
    parts = {}
    for side, (w, d, ox, oy) in sides.items():
        if side == door_side and door_gap is not None:
            side_w = (w - door_gap) / 2 if side in ("north", "south") else w
            side_d = d if side in ("north", "south") else (d - door_gap) / 2
            for half, sign in (("a", -1), ("b", 1)):
                seg = create_box(make_name("mesh", asset.name, f"{name_prefix}_wall_{side}_{half}"), width=side_w, depth=side_d, height=height, bevel_width=0.02, material=mat)
                if side in ("north", "south"):
                    seg.location.x, seg.location.y = x + sign * (door_gap / 2 + side_w / 2), y + oy
                else:
                    seg.location.x, seg.location.y = x + ox, y + sign * (door_gap / 2 + side_d / 2)
                seg.location.z = z
                apply_all_transforms(seg)
                asset.add_geometry(seg, metadata=for_static_prop(category="architecture_spandrel", importance="low"))
                parts[f"wall_{side}_{half}"] = seg
        else:
            seg = create_box(make_name("mesh", asset.name, f"{name_prefix}_wall_{side}"), width=w, depth=d, height=height, bevel_width=0.02, material=mat)
            seg.location.x, seg.location.y, seg.location.z = x + ox, y + oy, z
            apply_all_transforms(seg)
            asset.add_geometry(seg, metadata=for_static_prop(category="architecture_spandrel", importance="low"))
            parts[f"wall_{side}"] = seg
    return parts

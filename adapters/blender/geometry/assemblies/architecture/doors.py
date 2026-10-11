"""Door assemblies — frame + leaf (+ optional card-reader mount), real
parts instead of Phase 1-10's bare single door panel.

Naming stays compatible with the interaction-point system already in
use: pass `card_reader_name` (e.g. "Hotel.Room.Standard.012.CardReader")
to get a real core.interaction_point Empty placed at the mount, exactly
matching the convention `koba_casino_04_hotel_wing.py` established.
"""
from core.entity_metadata import for_static_prop
from core.interaction_point import add_interaction_point
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_panel

FRAME_THICKNESS = 0.1
FRAME_DEPTH = 0.15
READER_SIZE = 0.15


def _door_frame(asset, name_prefix, x, y, z, width, height, frame_mat):
    """A 3-sided frame (no bottom bar — a door needs a real threshold,
    not a tripping bar). z is the floor (door bottom). Returns
    {"frame_top", "frame_left", "frame_right"}."""
    half_w = width / 2
    # (part, box_width, box_height, x_offset, z_center)
    bars = [
        ("frame_top", width + FRAME_THICKNESS, FRAME_THICKNESS, 0.0, z + height + FRAME_THICKNESS / 2),
        ("frame_left", FRAME_THICKNESS, height, -half_w - FRAME_THICKNESS / 2, z + height / 2),
        ("frame_right", FRAME_THICKNESS, height, half_w + FRAME_THICKNESS / 2, z + height / 2),
    ]
    parts = {}
    for part, bw, bh, ox, bz in bars:
        bar = create_box(make_name("mesh", asset.name, f"{name_prefix}_{part}"), width=bw, depth=FRAME_DEPTH, height=bh,
                          bevel_width=0.015, material=frame_mat)
        bar.location.x, bar.location.y, bar.location.z = x + ox, y, bz
        apply_all_transforms(bar)
        asset.add_geometry(bar, metadata=for_static_prop(category="architecture_door_frame", importance="low"))
        parts[part] = bar
    return parts


def _card_reader_mount(asset, x, y, z, width, height, reader_mat, card_reader_name):
    """A small physical mount box beside the door, at hand height, plus
    the real named interaction point on it."""
    mount = create_box(make_name("mesh", asset.name, "CardReaderMount"), width=READER_SIZE, depth=0.05, height=READER_SIZE,
                        bevel_width=0.01, material=reader_mat)
    mount.location.x, mount.location.y, mount.location.z = x + width / 2 + 0.2, y, z + height * 0.45
    apply_all_transforms(mount)
    asset.add_geometry(mount, metadata=for_static_prop(category="architecture_door_hardware", importance="high"))
    if card_reader_name:
        add_interaction_point(asset, card_reader_name, location=(mount.location.x, mount.location.y, mount.location.z))
    return mount


def build_door_single(asset, name_prefix, x, y, z, width=0.9, height=2.1,
                       frame_mat=None, door_mat=None, reader_mat=None, card_reader_name=None):
    """z is the FLOOR (door bottom), matching how every KOBA CASINO &
    RESORT phase script places floor-level props. Returns frame parts +
    "leaf" + optionally "card_reader_mount"."""
    parts = _door_frame(asset, name_prefix, x, y, z, width, height, frame_mat)

    leaf = create_panel(make_name("mesh", asset.name, f"{name_prefix}_leaf"), width=width, height=height, thickness=0.06, bevel_width=0.015, material=door_mat)
    leaf.location.x, leaf.location.y, leaf.location.z = x, y, z + height / 2
    apply_all_transforms(leaf)
    asset.add_geometry(leaf, metadata=for_static_prop(category="architecture_door_leaf", importance="high"))
    parts["leaf"] = leaf

    if reader_mat is not None:
        parts["card_reader_mount"] = _card_reader_mount(asset, x, y, z, width, height, reader_mat, card_reader_name)
    return parts


def build_door_double(asset, name_prefix, x, y, z, width=1.8, height=2.1,
                       frame_mat=None, door_mat=None, reader_mat=None, card_reader_name=None):
    """Two leaves meeting at the center. Frame spans the full width
    once; each leaf is half-width."""
    parts = _door_frame(asset, name_prefix, x, y, z, width, height, frame_mat)
    leaf_w = width / 2
    for side, ox in (("left", -leaf_w / 2), ("right", leaf_w / 2)):
        leaf = create_panel(make_name("mesh", asset.name, f"{name_prefix}_leaf_{side}"), width=leaf_w - 0.02, height=height, thickness=0.06, bevel_width=0.015, material=door_mat)
        leaf.location.x, leaf.location.y, leaf.location.z = x + ox, y, z + height / 2
        apply_all_transforms(leaf)
        asset.add_geometry(leaf, metadata=for_static_prop(category="architecture_door_leaf", importance="high"))
        parts[f"leaf_{side}"] = leaf
    if reader_mat is not None:
        parts["card_reader_mount"] = _card_reader_mount(asset, x, y, z, width, height, reader_mat, card_reader_name)
    return parts


def build_door_sliding(asset, name_prefix, x, y, z, width=1.2, height=2.1,
                        frame_mat=None, door_mat=None, reader_mat=None, card_reader_name=None, open_ratio=0.0):
    """A sliding leaf + an overhead track bar. open_ratio in [0,1]: 0 =
    fully closed (centered on the opening), 1 = fully open (slid clear
    of the opening, offset by one full width)."""
    parts = _door_frame(asset, name_prefix, x, y, z, width, height, frame_mat)

    track = create_box(make_name("mesh", asset.name, f"{name_prefix}_track"), width=width * 1.3, depth=0.1, height=0.08, bevel_width=0.01, material=frame_mat)
    track.location.x, track.location.y, track.location.z = x, y, z + height + 0.04
    apply_all_transforms(track)
    asset.add_geometry(track, metadata=for_static_prop(category="architecture_door_hardware", importance="low"))
    parts["track"] = track

    leaf_x = x + width * open_ratio
    leaf = create_panel(make_name("mesh", asset.name, f"{name_prefix}_leaf"), width=width, height=height, thickness=0.05, bevel_width=0.015, material=door_mat)
    leaf.location.x, leaf.location.y, leaf.location.z = leaf_x, y, z + height / 2
    apply_all_transforms(leaf)
    asset.add_geometry(leaf, metadata=for_static_prop(category="architecture_door_leaf", importance="high"))
    parts["leaf"] = leaf

    if reader_mat is not None:
        parts["card_reader_mount"] = _card_reader_mount(asset, x, y, z, width, height, reader_mat, card_reader_name)
    return parts

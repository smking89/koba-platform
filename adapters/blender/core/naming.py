"""Central naming convention enforcement.

All framework code should name objects through these helpers instead of
constructing name strings ad hoc, so the convention can change in one
place.
"""

PREFIXES = {
    "mesh": "SM",       # static mesh
    "material": "MAT",
    "rig": "RIG",
    "animation": "ANIM",
    "collision": "COL",
    "lod": "LOD",
    "collection": "GRP",
    "light": "LGT",
    "empty": "EMP",
    "camera": "CAM",
}


def name(kind, asset_name, part=None, index=None):
    """Build a convention-compliant name, e.g. name('mesh', 'Crate', 'Lid') -> SM_Crate_Lid."""
    if kind not in PREFIXES:
        raise ValueError(f"Unknown naming kind '{kind}'. Known: {sorted(PREFIXES)}")
    pieces = [PREFIXES[kind], asset_name]
    if part:
        pieces.append(part)
    if index is not None:
        pieces.append(str(index))
    return "_".join(pieces)


def lod_name(asset_name, part, level):
    return f"{PREFIXES['lod']}{level}_{asset_name}_{part}"


def collision_name(asset_name, part):
    return f"{PREFIXES['collision']}_{asset_name}_{part}"

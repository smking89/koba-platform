"""Distance-based visibility culling metadata.

This is the achievable, honest slice of "occlusion/visibility
optimization" from the spec — per-object min/max visibility distance and
LOD transition distances, stamped as custom properties (so they survive
save/reload, same pattern as core.asset's metadata stamping) for a game
engine's own streaming/culling system to read on import.

NOT implemented here (see adapters/blender/README.md's "deferred" list):
zone/portal occlusion structures, room/sector organization, actual
runtime frustum/occlusion culling — those require a target engine to
define how portals/zones are represented, which varies per engine and
hasn't been decided yet.

Distances are in the asset's own units (meters, per core.asset.Asset's
default scale_unit) and are starting points, not physically derived —
tune per project.
"""
import bpy

from core.entity_metadata import EntityMetadata  # noqa: F401  (referenced in docstrings/type hints)

CULL_MIN_PROP = "koba_cull_min_distance"
CULL_MAX_PROP = "koba_cull_max_distance"   # -1.0 sentinel means "never culled"
LOD_TRANSITION_PROP = "koba_lod_transition_distance"

# (min_distance, max_distance) by importance tier. max_distance=None means
# never culled regardless of distance (a hero asset stays visible).
DEFAULT_TIERS = {
    "hero": (0.0, None),
    "high": (0.0, 200.0),
    "medium": (0.0, 80.0),
    "low": (0.0, 35.0),
    "trivial": (0.0, 15.0),
}


def _stamp(obj, min_distance, max_distance):
    obj[CULL_MIN_PROP] = float(min_distance)
    obj[CULL_MAX_PROP] = float(max_distance) if max_distance is not None else -1.0


def assign_visibility_distances(asset, tiers=None, objects=None):
    """Stamp min/max visibility distance on every object in `objects`
    (default: all of asset.geometry_objects) based on its importance tier.
    Objects with cullable=False in their metadata are stamped "never
    culled" (max_distance sentinel -1.0) regardless of importance — that
    flag exists precisely to override distance-based culling for things
    like rigged mechanisms that must stay visible/updating.

    Also assigns LOD transition distances for any object that appears in
    asset.lod_objects, scaled as fractions of its own max visibility
    distance (or a flat fallback if the object has no max, e.g. a hero
    asset) so higher LOD levels kick in progressively closer to the max
    cull distance.
    """
    tiers = tiers or DEFAULT_TIERS
    objects = objects if objects is not None else asset.geometry_objects

    stamped = {"cullable": [], "never_culled": []}
    for obj in objects:
        meta = asset.get_metadata(obj)
        if not meta.cullable:
            _stamp(obj, 0.0, None)
            stamped["never_culled"].append(obj.name)
            continue
        min_d, max_d = tiers.get(meta.importance, tiers["medium"])
        _stamp(obj, min_d, max_d)
        stamped["cullable"].append((obj.name, min_d, max_d))

    lod_fractions = {1: 0.3, 2: 0.6, 3: 0.85}
    lod_stamped = []
    for level, objs in asset.lod_objects.items():
        fraction = lod_fractions.get(level, min(0.3 * level, 0.95))
        for obj in objs:
            meta = asset.get_metadata(obj)
            _, max_d = tiers.get(meta.importance, tiers["medium"])
            reference_distance = max_d if max_d is not None else 100.0
            obj[LOD_TRANSITION_PROP] = float(reference_distance * fraction)
            lod_stamped.append((obj.name, level, obj[LOD_TRANSITION_PROP]))

    return {"cullable": stamped["cullable"], "never_culled": stamped["never_culled"], "lod_transitions": lod_stamped}


def read_visibility_distances(obj):
    """Read back what assign_visibility_distances stamped, e.g. for the
    performance validator or a later export step. Returns
    (min_distance, max_distance_or_None) or None if never stamped."""
    if CULL_MIN_PROP not in obj:
        return None
    max_raw = obj.get(CULL_MAX_PROP, -1.0)
    return (obj[CULL_MIN_PROP], None if max_raw < 0 else max_raw)


def culling_coverage(asset, objects=None):
    """Fraction of objects that have been stamped with a culling distance
    at all (cullable or explicitly never-culled) — a validator-style
    coverage metric, same shape as collision/LOD coverage."""
    objects = objects if objects is not None else asset.geometry_objects
    if not objects:
        return 1.0
    stamped = sum(1 for o in objects if CULL_MIN_PROP in o)
    return round(stamped / len(objects), 2)

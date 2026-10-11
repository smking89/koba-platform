"""In-place geometry decimation — reduces a mesh object's ACTUAL triangle
count via a Decimate modifier applied directly to the object itself, not
a parallel duplicate (see optimization.lod.generate_decimated_lod for
that — it registers an alternate representation for distance-based
runtime switching, which this framework has no switching system for yet,
so it does NOT change what the performance validator counts).

This is the repair engine's strategy for triangle-budget overages: the
only way to actually reduce the `triangles` metric
optimization.performance_validator reports is to reduce the real,
currently-visible mesh complexity. Lossy and irreversible on the object
it's applied to — always run against a copy (this project's optimize
pipeline already never writes back over the source .blend).
"""
import bpy


def _triangle_count(obj):
    return sum(max(len(p.vertices) - 2, 1) for p in obj.data.polygons)


def decimate_geometry(objects, ratio):
    """Applies a Decimate modifier (collapsing to `ratio` of each
    object's original triangle count) to every MESH object in `objects`,
    in place. Returns {object_name: {"before": int, "after": int}}."""
    if not (0.0 < ratio < 1.0):
        raise ValueError(f"ratio must be strictly between 0 and 1, got {ratio}")

    results = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        before = _triangle_count(obj)

        mod = obj.modifiers.new("Decimate", type="DECIMATE")
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)

        after = _triangle_count(obj)
        results[obj.name] = {"before": before, "after": after}
    return results

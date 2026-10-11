"""Static geometry merging — combine multiple objects into one mesh to cut
entity/draw-call count, but ONLY for objects whose entity_metadata says
it's safe (mergeable=True — see core.entity_metadata). Never merges based
on guessing from geometry; refuses outright if metadata is missing or
says no.
"""
import bpy

from core.naming import name as make_name


class MergeRefused(Exception):
    """Raised instead of silently skipping — a caller asking to merge
    objects that aren't all mergeable made a real mistake worth surfacing."""


def find_mergeable_groups(asset, candidates=None):
    """Group `candidates` (default: all of asset.geometry_objects) by
    (mergeable, visibility_group) so callers can merge each group
    independently — objects in different visibility groups shouldn't be
    fused into one mesh even if both are individually mergeable, since
    that would defeat zone-based culling later."""
    candidates = candidates if candidates is not None else asset.geometry_objects
    groups = {}
    for obj in candidates:
        meta = asset.get_metadata(obj)
        if not meta.mergeable:
            continue
        groups.setdefault(meta.visibility_group, []).append(obj)
    return {k: v for k, v in groups.items() if len(v) > 1}


def merge_static_group(asset, part_name, objects):
    """Join `objects` into one new mesh object. Every object must have
    mergeable=True metadata — raises MergeRefused otherwise rather than
    silently merging something animated/interactive into static geometry.
    The originals are removed from the scene (their data stays on disk in
    the .blend only if still referenced elsewhere)."""
    if len(objects) < 2:
        raise ValueError("merge_static_group needs at least 2 objects")

    non_mergeable = [o.name for o in objects if not asset.get_metadata(o).mergeable]
    if non_mergeable:
        raise MergeRefused(
            f"Refusing to merge — these objects are not marked mergeable: {non_mergeable}. "
            "Check their entity_metadata (e.g. rig parts from for_mechanism() are never mergeable)."
        )

    # Cache what we need as plain strings/values BEFORE join() — it deletes
    # every non-active object outright, and touching a deleted object's
    # .name afterward raises ReferenceError (confirmed by testing, not a
    # hypothetical), so nothing below may dereference `objects` post-join.
    sample_meta = asset.get_metadata(objects[0])
    object_names = [o.name for o in objects]

    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    merged.name = make_name("mesh", asset.name, part_name)
    merged.data.name = merged.name + "_mesh"

    # The merged result carries the group's shared metadata forward —
    # still mergeable/cullable, no longer separately trackable per-source.
    # Filter geometry_objects by Python-level identity (id()), never by
    # attribute access (.name) — some of `objects` are now deleted
    # StructRNA wrappers, and merely reading .name off one raises
    # ReferenceError even inside a list-comprehension guard, since the
    # attribute access happens before membership is evaluated.
    for name in object_names:
        asset.entity_metadata.pop(name, None)
    stale_ids = {id(o) for o in objects}
    asset.geometry_objects = [o for o in asset.geometry_objects if id(o) not in stale_ids]
    asset.geometry_objects.append(merged)
    asset.set_metadata(merged, sample_meta)  # in-memory + stamped as a custom property (see core.asset)

    return merged

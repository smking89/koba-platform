"""Real Blender instancing — many Objects sharing ONE mesh datablock.

This is not a simulated/logical instancing layer bolted on top; it's
Blender's own native mechanism (multiple objects with `obj.data` pointing
at the same Mesh datablock use one copy of the geometry in memory, and
export as instances in formats that support it, e.g. glTF/USD). A
duplicated *unique* mesh (bpy.ops.object.duplicate with linked=False, or
copy.deepcopy of mesh data) is exactly what this module exists to avoid.

Use this whenever an asset repeats a prop (chairs, crates, lights, slot
machines, ...) — never build N independent meshes for what is visually
one shape placed N times.
"""
import bpy

from core.entity_metadata import for_instanced_prop
from core.naming import name as make_name


def create_instance(asset, part_name, source_obj, location=(0, 0, 0), rotation=(0, 0, 0),
                     scale=(1, 1, 1), index=None, importance="low", visibility_group=None):
    """Create a new Object that shares source_obj's mesh datablock (and
    material slots, since materials live on the mesh/object data too) —
    zero additional geometry memory regardless of how many instances exist.
    Registers it on the asset with for_instanced_prop metadata."""
    if source_obj.type != "MESH":
        raise ValueError(f"create_instance requires a MESH source, got {source_obj.type}")

    inst_name = make_name("mesh", asset.name, part_name, index=index)
    inst = bpy.data.objects.new(inst_name, source_obj.data)  # <-- shared data, this IS the instancing
    inst.location = location
    inst.rotation_euler = rotation
    inst.scale = scale

    bpy.context.scene.collection.objects.link(inst)
    asset.add_geometry(inst, metadata=for_instanced_prop(
        category=asset.get_metadata(source_obj).category,
        importance=importance,
        visibility_group=visibility_group,
    ))
    return inst


def create_instance_grid(asset, part_name, source_obj, positions, importance="low", visibility_group=None):
    """Convenience: one create_instance() call per world-space position in
    `positions` (list of (x,y,z) or (x,y,z,rot_z) tuples). Returns the list
    of created instance objects."""
    instances = []
    for i, pos in enumerate(positions):
        if len(pos) == 4:
            x, y, z, rot_z = pos
        else:
            x, y, z = pos
            rot_z = 0.0
        instances.append(create_instance(
            asset, part_name, source_obj,
            location=(x, y, z), rotation=(0, 0, rot_z),
            index=i, importance=importance, visibility_group=visibility_group,
        ))
    return instances


def count_unique_meshes(objects):
    """How many distinct mesh datablocks a set of objects actually uses —
    the number that matters for memory/load time, as opposed to len(objects)."""
    return len({obj.data.name for obj in objects if obj.type == "MESH" and obj.data is not None})


def _geometry_signature(obj):
    """A cheap, deterministic fingerprint for 'this looks like the same
    shape' — vertex/polygon counts plus rounded bounding-box dimensions.
    Not a hash of exact vertex positions (two shapes could theoretically
    collide), but good enough to flag "these are probably duplicates of
    each other" for a human/generator to confirm, which is the point: a
    detector that suggests candidates, not one that silently auto-merges."""
    mesh = obj.data
    dims = tuple(round(d, 3) for d in obj.dimensions)
    return (len(mesh.vertices), len(mesh.polygons), dims)


def detect_instanceable_candidates(asset, objects=None, min_group_size=2):
    """Find groups of objects that LOOK like the same shape but use more
    than one mesh datablock — i.e. exactly the mistake section 2 of the
    perf spec calls out (unique mesh per copy instead of shared
    instances). Returns a list of
    {"object_names": [...], "unique_mesh_count": N, "count": M}
    for each group worth flagging (M >= min_group_size and N > 1 — if
    N == 1 they're already properly instanced, nothing to flag).

    This only detects and reports; it never auto-converts anything to
    instances itself — that decision (and picking which object becomes
    the shared source) is left to a caller, since collapsing to instances
    changes which object's transform/material edits propagate to all the
    others."""
    objects = objects if objects is not None else asset.geometry_objects
    groups = {}
    for obj in objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        groups.setdefault(_geometry_signature(obj), []).append(obj)

    candidates = []
    for objs in groups.values():
        if len(objs) < min_group_size:
            continue
        unique_mesh_count = len({o.data.name for o in objs})
        if unique_mesh_count <= 1:
            continue  # already sharing one mesh — properly instanced already
        candidates.append({
            "object_names": [o.name for o in objs],
            "unique_mesh_count": unique_mesh_count,
            "count": len(objs),
        })
    return candidates

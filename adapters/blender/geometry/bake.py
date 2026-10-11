"""Assembly baking — produces a single, clean, welded + beveled mesh
from a set of loose assembly Objects, WITHOUT touching the originals.

The loose multi-object form every geometry/assemblies/* builder returns
stays the real source of truth for instancing (geometry.instancing) and
per-part collision/LOD/EntityMetadata tuning — exactly the contract
those assemblies were built with. This module is an explicit, opt-in
DOWNSTREAM step for when a single-mesh deployment variant is actually
needed, operating on CLONES so the instancing-ready originals are never
mutated. Same "explicit opt-in, never automatic" precedent
optimization/merge.py already set for whole-scene static merging — this
is that same idea at assembly scope, with real bevel smoothing added.

Every operation here is destructive/baked directly into the output
mesh's data (bmesh ops, not a live modifier) — real polygon counts, so
core.validation's poly-budget check (and every KOBA CASINO & RESORT
phase's reported triangle count) stays honest, per this project's
standing "report real numbers, never estimate" rule. Verified live
against Blender 5.2.2's actual bmesh.ops.bevel signature before writing
this (see /tmp/test_bevel_api.py in the session that built this), not
assumed from documentation.

Known, real limitation (confirmed by tests/test_geometry_bake.py's own
validate_asset run, not hidden): `remove_doubles` merges duplicate
VERTICES at a shared seam, but it does NOT remove the duplicate
INTERIOR FACES left behind when two source objects were touching
flush — e.g. two boxes placed face-to-face end up with both of their
touching faces still present after welding, which is real non-manifold
geometry (core.validation correctly flags it as a WARNING). A true
watertight merge of flush-touching solids needs an actual Boolean
union, which this function does not perform — it does exactly what was
asked (join + vertex weld + bevel), not a full CSG merge. Source
objects that don't physically overlap/touch (the common case for an
assembly's parts, which are usually spaced apart) are unaffected by
this.
"""
import math

import bmesh
import bpy

from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from geometry.mesh_utils import smart_uv_unwrap

DEFAULT_WELD_DISTANCE = 0.0001
DEFAULT_BEVEL_WIDTH = 0.01
DEFAULT_BEVEL_ANGLE_LIMIT = math.radians(30)
DEFAULT_BEVEL_SEGMENTS = 2
DEFAULT_UV_ISLAND_MARGIN = 0.02


def bake_assembly_to_mesh(asset, objects, name, weld_distance=DEFAULT_WELD_DISTANCE,
                           bevel_width=DEFAULT_BEVEL_WIDTH, bevel_angle_limit=DEFAULT_BEVEL_ANGLE_LIMIT,
                           bevel_segments=DEFAULT_BEVEL_SEGMENTS, uv_island_margin=DEFAULT_UV_ISLAND_MARGIN,
                           category="baked_mesh", importance="medium"):
    """Clone `objects`, join the clones into one mesh, weld coincident
    seam vertices, then bevel every edge sharper than `bevel_angle_limit`
    directly into the mesh data. Registers the result on `asset` as a
    new Object (via add_geometry, so it goes through the normal
    collision/LOD/validation pipeline like anything else) and returns
    it. The input `objects` are left completely untouched — still valid
    as instancing sources."""
    if len(objects) < 1:
        raise ValueError("bake_assembly_to_mesh needs at least 1 object")

    clones = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        clone = obj.copy()
        clone.data = obj.data.copy()
        clone.name = make_name("mesh", asset.name, f"{name}_bake_tmp")
        bpy.context.collection.objects.link(clone)
        clones.append(clone)
    if not clones:
        raise ValueError("bake_assembly_to_mesh: none of the given objects were MESH type")

    bpy.context.view_layer.objects.active = clones[0]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for c in clones:
        c.select_set(True)
    bpy.ops.object.join()
    baked = clones[0]
    baked.name = make_name("mesh", asset.name, name)

    bm = bmesh.new()
    bm.from_mesh(baked.data)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld_distance)

    sharp_edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.calc_face_angle() > bevel_angle_limit:
                sharp_edges.append(e)
    if sharp_edges:
        bmesh.ops.bevel(bm, geom=sharp_edges, offset=bevel_width, segments=bevel_segments, affect="EDGES")

    bm.to_mesh(baked.data)
    bm.free()
    baked.data.update()

    # A joined multi-part mesh can't reuse each original part's own
    # cube-projected UVs cleanly (seams no longer line up with faces the
    # way they did per-object) -- re-unwrap the WHOLE baked mesh with a
    # real non-overlapping layout instead.
    smart_uv_unwrap(baked, island_margin=uv_island_margin)

    asset.add_geometry(baked, metadata=for_static_prop(category=category, importance=importance))
    return baked

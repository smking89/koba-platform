"""Procedural profile lathe/extrusion — real 2D-vector-path-to-3D
geometry, the bridge out of pure box/cylinder stacking for parts whose
actual silhouette ISN'T a box or cylinder (a turned chair leg, a
tapered console bracket) WITHOUT crossing into sculpting/subdivision-
displacement (explicitly out of scope — see geometry/detailing.py's
docstring for how low-poly surface detail is handled instead).

Both functions here are real bmesh operations (bmesh.ops.spin,
bmesh.ops.bridge_loops), verified live against Blender 5.2.2 before
this module was written (see /tmp/test_spin_api.py and
/tmp/test_bridge_api.py from the session that built this) — not
assumed from documentation. Both stay honest about real polygon counts:
nothing here uses a live modifier, every face exists in the returned
mesh's data immediately.
"""
import math

import bmesh
import bpy

from core.naming import name as make_name
from geometry.mesh_utils import simple_box_uv_unwrap


def lathe_profile(name, profile_points, axis=(0, 0, 1), angle_deg=360.0, steps=16, material=None):
    """Revolves a 2D profile (list of (radius, height) pairs, traced
    bottom-to-top) around `axis` to build a real turned/lathed shape —
    a chair leg, a balustrade spindle, a lamp base — instead of a bare
    cylinder. `angle_deg` < 360 produces a partial revolve (e.g. a
    quarter-round trim profile). Returns a real Object, positioned with
    its base at local Z=0 like every other geometry.primitives shape."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, h)) for r, h in profile_points]
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i + 1]))

    bmesh.ops.spin(bm, geom=list(bm.verts) + list(bm.edges), axis=axis, cent=(0, 0, 0),
                   angle=math.radians(angle_deg), steps=steps, use_duplicate=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(make_name("mesh", name, "lathe") + "_mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(make_name("mesh", name, "lathe"), mesh)
    bpy.context.collection.objects.link(obj)
    simple_box_uv_unwrap(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def extrude_profile_along_path(name, profile_points_2d, path_points_3d, closed_profile=True, material=None):
    """Sweeps a 2D cross-section (list of (x, z) pairs, in the profile's
    own local plane) along a real 3D polyline path, bridging consecutive
    rings into real faces (bmesh.ops.bridge_loops) — a tapered bracket,
    a run of custom-profile molding/trim, a railing cap. Each ring is
    placed at a path point with NO automatic orientation-to-tangent
    (the caller positions path_points_3d already accounting for any
    twist/rotation it wants — this function stays a straightforward,
    predictable sweep, not a full Frenet-frame pipe generator)."""
    bm = bmesh.new()
    rings = []
    for px, py, pz in path_points_3d:
        ring_verts = [bm.verts.new((px + cx, py, pz + cz)) for cx, cz in profile_points_2d]
        n = len(ring_verts)
        edge_count = n if closed_profile else n - 1
        for j in range(edge_count):
            bm.edges.new((ring_verts[j], ring_verts[(j + 1) % n]))
        rings.append(ring_verts)

    for i in range(len(rings) - 1):
        ring_a, ring_b = rings[i], rings[i + 1]
        n = len(ring_a)
        edge_count = n if closed_profile else n - 1
        edges_a = [bm.edges.get((ring_a[j], ring_a[(j + 1) % n])) for j in range(edge_count)]
        edges_b = [bm.edges.get((ring_b[j], ring_b[(j + 1) % n])) for j in range(edge_count)]
        bmesh.ops.bridge_loops(bm, edges=edges_a + edges_b)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(make_name("mesh", name, "sweep") + "_mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(make_name("mesh", name, "sweep"), mesh)
    bpy.context.collection.objects.link(obj)
    simple_box_uv_unwrap(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj

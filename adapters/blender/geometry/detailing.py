"""Low-poly surface detailing — the agreed replacement for noise-driven
vertex displacement/subdivision sculpting (explicitly ruled out
2026-10-01: that technique is procedural sculpting by another name, and
would blow every KOBA CASINO & RESORT phase's real-time triangle
budget if wired into the base generator).

Two real, cheap, bmesh-based techniques instead:
  - inset_panel(): steps a face inward/outward (bmesh.ops.inset_region +
    extrude_face_region) — a real cushion indent, a recessed door
    panel, a console insert. A handful of extra triangles per panel,
    not thousands.
  - distribute_array_detail(): places a small detail object (a rivet,
    a bracket, a seam strip) at evenly-spaced points along an edge/run
    via geometry.instancing.create_instance_grid — real shared-mesh
    instances, zero extra unique geometry per repeat.

Both verified live against Blender 5.2.2's actual bmesh.ops signatures
before this module was written (see /tmp/test_inset_api.py from the
session that built this), not assumed from documentation.
"""
import bmesh

from geometry.instancing import create_instance_grid


def find_face_by_normal(obj, normal_axis="y", sign=-1):
    """Finds the face most closely facing the given direction (default:
    -Y, this project's standing 'front' convention) — so inset_panel()
    can be pointed at the right face (a door/headboard front, not a
    side/top/bottom) without the caller hand-picking a polygon index."""
    axis_index = {"x": 0, "y": 1, "z": 2}[normal_axis]
    best_index, best_score = 0, -2.0
    for i, poly in enumerate(obj.data.polygons):
        score = poly.normal[axis_index] * sign
        if score > best_score:
            best_score, best_index = score, i
    return best_index


def inset_panel(obj, face_index, thickness=0.1, depth=0.0, material_index=None):
    """Insets face `face_index` of `obj`'s mesh by `thickness`, then
    extrudes the resulting inner face by `depth` (negative = recessed
    panel/cushion indent, positive = raised boss/rivet head, 0 = a flat
    inset seam line with no indent at all). Mutates obj.data directly
    (real baked geometry, no modifier). Returns the number of new faces
    created."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    face = bm.faces[face_index]
    original_material_index = face.material_index

    inset_result = bmesh.ops.inset_region(bm, faces=[face], thickness=thickness, depth=0.0)
    inner_faces = inset_result["faces"]

    if depth != 0.0:
        extrude_result = bmesh.ops.extrude_face_region(bm, geom=inner_faces)
        new_verts = [v for v in extrude_result["geom"] if isinstance(v, bmesh.types.BMVert)]
        normal = face.normal.copy()
        bmesh.ops.translate(bm, verts=new_verts, vec=normal * depth)

    if material_index is not None:
        for f in inner_faces:
            f.material_index = material_index
    else:
        for f in inner_faces:
            f.material_index = original_material_index

    new_face_count = len(inner_faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return new_face_count


def distribute_array_detail(asset, part_name, detail_source_obj, start, end, count,
                             importance="low", visibility_group=None):
    """Places `count` real shared-mesh instances of `detail_source_obj`
    evenly spaced along the straight run from `start` to `end`
    (world-space (x,y,z) tuples) — rivets along a seam, support
    brackets along a girder, panel-line studs. Real instancing
    (geometry.instancing.create_instance_grid), not unique geometry per
    repeat. Returns the list of created instance Objects."""
    if count < 1:
        return []
    positions = []
    for i in range(count):
        t = i / max(1, count - 1) if count > 1 else 0.5
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        z = start[2] + (end[2] - start[2]) * t
        positions.append((x, y, z))
    return create_instance_grid(asset, part_name, detail_source_obj, positions,
                                 importance=importance, visibility_group=visibility_group)

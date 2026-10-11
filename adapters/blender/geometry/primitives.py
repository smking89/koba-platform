"""Parametric primitive generators. Every function takes explicit
dimension/style parameters — never hardcode numbers here."""
import bmesh
import bpy
import mathutils

from geometry.mesh_utils import new_bmesh_cube, bmesh_to_object, simple_box_uv_unwrap


def create_box(name, width, depth, height, bevel_width=0.0, bevel_segments=2, material=None):
    """A box sitting on Z=0, centered in X/Y. Optional bevel via a non-destructive
    modifier (kept applied so downstream export sees real geometry)."""
    bm = new_bmesh_cube(width, depth, height)
    obj = bmesh_to_object(bm, name)

    if bevel_width > 0:
        mod = obj.modifiers.new("Bevel", type="BEVEL")
        mod.width = bevel_width
        mod.segments = bevel_segments
        mod.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)

    simple_box_uv_unwrap(obj)

    if material is not None:
        obj.data.materials.append(material)

    return obj


def create_panel(name, width, height, thickness, bevel_width=0.0, material=None):
    """A thin flat panel — width x height in the XZ plane, thickness in Y."""
    obj = create_box(name, width, thickness, height, bevel_width=bevel_width, material=material)
    return obj


def create_cylinder(name, radius, depth, vertices=16, material=None):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=vertices, location=(0, 0, depth / 2)
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name + "_mesh"
    simple_box_uv_unwrap(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def create_pyramid(name, base_width, height, sides=4, material=None):
    """A tapered pyramid/obelisk tip sitting on Z=0 — a cone primitive
    with a low, even side count so it reads as flat-faced (a 4-sided
    pyramid, not a rounded cone)."""
    bpy.ops.mesh.primitive_cone_add(
        vertices=sides, radius1=base_width / 2, radius2=0.0, depth=height,
        location=(0, 0, height / 2),
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name + "_mesh"
    simple_box_uv_unwrap(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def create_pipe(name, radius, length, segments=12, material=None):
    """Straight pipe along Z. (Curve-following pipes are a later phase —
    documented limitation, not yet implemented.)"""
    return create_cylinder(name, radius, length, vertices=segments, material=material)


def create_hull(name, length, beam, draft, deck_height, sections=12, material=None):
    """A tapered small-boat hull: lofts `sections` 5-vertex V-shaped rings
    along X (stern at -X, bow at +X). Width and draft taper toward the bow
    from the midship section onward, so the hull narrows to a near-point
    at the bow; the stern stays full and is capped flat (a transom). The
    top edge (deck line) is left open, like an open dinghy — there is no
    separate deck-plate generator yet, a documented limitation, not a bug.
    """
    bm = bmesh.new()
    ring_verts = []

    half_beam = beam / 2
    for i in range(sections):
        t = i / (sections - 1)  # 0 = stern, 1 = bow
        x = -length / 2 + t * length

        if t < 0.5:
            taper = 1.0
        else:
            taper = max(0.02, 1.0 - ((t - 0.5) / 0.5) ** 1.5)

        w = half_beam * taper
        d = draft * taper

        ring_verts.append([
            bm.verts.new((x, -w, deck_height)),       # deck, left
            bm.verts.new((x, -w * 0.6, -d)),           # chine, left
            bm.verts.new((x, 0.0, -d * 1.15)),         # keel line
            bm.verts.new((x, w * 0.6, -d)),            # chine, right
            bm.verts.new((x, w, deck_height)),         # deck, right
        ])

    for i in range(sections - 1):
        a, b = ring_verts[i], ring_verts[i + 1]
        for j in range(len(a) - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))

    stern = ring_verts[0]
    bm.faces.new((stern[4], stern[3], stern[2], stern[1], stern[0]))  # transom cap
    bow = ring_verts[-1]
    bm.faces.new((bow[0], bow[1], bow[2], bow[3], bow[4]))  # bow cap

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    obj = bmesh_to_object(bm, name)
    simple_box_uv_unwrap(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def create_cable(name, start, end, radius=0.01, segments=8, material=None):
    """A straight cylinder connecting two world-space points — e.g. a crane
    cable from boom tip to hook. Built directly at the rest pose; it does
    NOT dynamically stretch if something parented at either end animates
    afterward (that needs a Stretch-To constraint on a Y-aligned mesh —
    not implemented yet, a documented limitation, not a bug)."""
    start_v = mathutils.Vector(start)
    end_v = mathutils.Vector(end)
    length = (end_v - start_v).length

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                           radius1=radius, radius2=radius, depth=length)
    bmesh.ops.translate(bm, vec=(0, 0, length / 2), verts=bm.verts)  # base at local origin
    obj = bmesh_to_object(bm, name)
    simple_box_uv_unwrap(obj)

    obj.location = start_v
    direction = end_v - start_v
    if direction.length > 1e-9:
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()

    if material is not None:
        obj.data.materials.append(material)
    return obj

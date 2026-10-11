"""Low-level mesh editing helpers shared by every geometry generator."""
import bmesh
import bpy


def bevel_edges(obj, width=0.01, segments=2, angle_limit_deg=30):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bevel(offset=width, segments=segments, affect="EDGES")
    bpy.ops.object.mode_set(mode="OBJECT")


def shade_smooth_by_angle(obj, angle_deg=45):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=angle_deg * 3.14159265 / 180.0)


def recalc_normals(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def simple_box_uv_unwrap(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project()
    bpy.ops.object.mode_set(mode="OBJECT")


def smart_uv_unwrap(obj, island_margin=0.02, angle_limit_deg=66.0):
    """Non-overlapping UV layout via Smart UV Project — the right choice
    for a multi-part JOINED mesh (geometry.bake.bake_assembly_to_mesh's
    output), where per-object cube projection no longer applies cleanly
    once parts are fused. `island_margin` keeps UV islands from touching
    (avoids texture bleed across seams at render/export time)."""
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=angle_limit_deg * 3.14159265 / 180.0, island_margin=island_margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def new_bmesh_cube(width, depth, height):
    """Create a bmesh cube centered at origin in XY, sitting on Z=0."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(width, depth, height), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, height / 2), verts=bm.verts)
    return bm


def assign_material_bands(obj, materials, axis="Z", by="count"):
    """Splits obj's faces into len(materials) bands along a local-space axis
    and assigns one material per band — e.g. an "assorted gummy candy" look
    on a single imported mesh that only ever had one material slot.

    by="count" (default) splits so each band gets an equal number of faces,
    which reads more evenly on meshes with very uneven geometry density
    than splitting by equal position ranges (by="range") would.
    """
    if axis not in ("X", "Y", "Z"):
        raise ValueError(f"axis must be X/Y/Z, got {axis!r}")
    axis_index = {"X": 0, "Y": 1, "Z": 2}[axis]
    n = len(materials)
    if n < 1:
        raise ValueError("materials must be non-empty")

    obj.data.materials.clear()
    for mat in materials:
        obj.data.materials.append(mat)

    mesh = obj.data
    centers = []
    for poly in mesh.polygons:
        coord = sum((mesh.vertices[vi].co[axis_index] for vi in poly.vertices), 0.0) / len(poly.vertices)
        centers.append(coord)

    if by == "count":
        order = sorted(range(len(mesh.polygons)), key=lambda i: centers[i])
        band_size = max(1, len(order) // n)
        for rank, poly_index in enumerate(order):
            band = min(rank // band_size, n - 1)
            mesh.polygons[poly_index].material_index = band
    elif by == "range":
        lo, hi = min(centers), max(centers)
        span = (hi - lo) or 1.0
        for poly_index, coord in enumerate(centers):
            band = min(int((coord - lo) / span * n), n - 1)
            mesh.polygons[poly_index].material_index = band
    else:
        raise ValueError(f"by must be 'count' or 'range', got {by!r}")

    mesh.update()


def bmesh_to_object(bm, name):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj

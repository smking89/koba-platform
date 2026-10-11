# Profile lathe/extrusion + low-poly detailing

Added 2026-10-01 in direct response to the "blocky barrier" conversation:
real 2D-profile-to-3D geometry (an actual turned-leg or bracket
silhouette, not a bare cylinder/box) plus cheap surface detail (panel
insets, array-distributed rivets) — all **additive**, none of it
touches the existing primitive system or any already-validated KOBA
CASINO & RESORT asset.

Noise-driven vertex displacement/subdivision sculpting was explicitly
**ruled out** in that same conversation: it's procedural sculpting by
another name (contradicting this project's own "no high-poly
sculpting" rule from the original expansion request) and would blow
every phase's real-time triangle budget if wired into the base
generator. `inset_panel()` below is the agreed substitute — real
surface detail at a handful of extra triangles, not thousands.

## `geometry/profiles.py`

- `lathe_profile(name, profile_points, axis, angle_deg, steps, material)` — revolves a 2D `(radius, height)` profile into a real 3D shape via `bmesh.ops.spin`. A 6-point profile revolved 14 steps produced a real 70-triangle turned chair leg in testing — recognizable as "turned wood," not a cylinder.
- `extrude_profile_along_path(name, profile_points_2d, path_points_3d, closed_profile, material)` — sweeps a 2D cross-section along a 3D polyline via `bmesh.ops.bridge_loops`, for a tapered console bracket, custom trim/molding, etc. A 4-point profile swept along a 3-point bent path produced a real 12-face bracket in testing.
- Both verified live against Blender 5.2.2's actual bmesh API before being written (not assumed from docs).
- Known limitation: open (non-closed-ring) profiles leave real open/non-manifold ends where the sweep starts and stops — expected for a bracket meant to attach to adjoining geometry, not a defect, but `core.validation` will correctly flag it; cap the ends yourself if a fully sealed solid is needed.

## `geometry/detailing.py`

- `inset_panel(obj, face_index, thickness, depth, material_index)` — insets one face (`bmesh.ops.inset_region`) then extrudes it by `depth` (`bmesh.ops.extrude_face_region` + translate along the face normal). Negative `depth` = a recessed cushion/door panel; positive = a raised boss/rivet head; `0` = a flat inset seam line. Mutates the mesh directly — real baked geometry, no modifier. Tested: a 6-face box gained exactly 4 real new faces from one inset+extrude call.
- `distribute_array_detail(asset, part_name, detail_source_obj, start, end, count)` — places `count` evenly-spaced REAL shared-mesh instances (via `geometry.instancing.create_instance_grid`) along a straight run — rivets along a seam, brackets along a girder. Tested: 6 requested instances → 6 created, confirmed as real instances (the scene's unique-mesh count stayed lower than its object count).

## Known limitations (stated plainly)

- `extrude_profile_along_path` only sweeps along straight polyline segments (no curve/spline tangent-following) — a deliberate scope limit, not a bug, matching this project's "don't overbuild beyond what's asked" discipline.
- No automatic end-capping on open sweeps/lathes with `angle_deg < 360`.
- `inset_panel` operates on one face at a time by index — the caller is responsible for picking the right face (e.g. by normal direction, as the test script does for "the top face").

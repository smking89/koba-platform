# Architecture assemblies

Mid-level, reusable building blocks on top of `geometry/primitives.py` —
real multi-part assemblies (window = frame + glass, door = frame + leaf
+ optional card-reader mount, column = base + shaft + capital, etc.)
instead of the single flat boxes/panels every KOBA CASINO & RESORT
phase script used before this. Each function takes an `Asset`,
placement coordinates, and size/style parameters; it builds real
geometry, registers it on the asset (with sensible `EntityMetadata`
categories), and returns a `dict` of the created `Object`s so a caller
can reuse them for real instancing (`geometry.instancing.create_instance`)
exactly like `koba_casino_04_hotel_wing.py`'s hotel room templates did.

Validated for real in `tests/test_assembly_architecture.py`: one example
of every assembly together — **111 entities, 2676 triangles, 12
materials, PASS against `60fps_standard`, 100% collision/LOD
coverage** (culling coverage 0% — not run in this showcase, same as
every KOBA CASINO & RESORT phase so far).

## Modules

### `windows.py`
- `build_window_single(asset, name_prefix, x, y, z, width, height, frame_mat, glass_mat)` — one framed pane (4 frame bars + 1 glass pane = 5 real objects). `z` is the window's vertical CENTER. Faces -Y.
- `build_window_double(asset, name_prefix, x, y, z, width, height, frame_mat, glass_mat)` — two panes sharing a center mullion (10 objects).
- `build_curtain_wall_segment(asset, name_prefix, x, y, z, width, height, cols, rows, frame_mat, glass_mat)` — a real grid of individually-framed panes (5 objects per pane × cols × rows) — this is the fidelity upgrade over Phase 1's single flat glass band.

### `doors.py`
- `build_door_single(asset, name_prefix, x, y, z, width, height, frame_mat, door_mat, reader_mat=None, card_reader_name=None)` — 3-sided frame + 1 leaf (+ 1 card-reader mount box with a real named interaction point, if `reader_mat`/`card_reader_name` given). `z` is the floor.
- `build_door_double(asset, ...)` — same frame, 2 half-width leaves.
- `build_door_sliding(asset, ..., open_ratio=0.0)` — 1 leaf + an overhead track bar; `open_ratio` in `[0,1]` slides the leaf clear of the opening.
- All three accept `reader_mat`/`card_reader_name` for a real `Hotel.Room.<Type>.<NNN>.CardReader`-style interaction point, matching the existing convention exactly.

### `railings.py`
- `build_railing_straight(asset, name_prefix, x, y, z, length, height, post_spacing, orientation, post_mat, rail_mat)` — evenly-spaced posts (always ≥2, at the run's ends) + one continuous top rail. `orientation` is `"x"` or `"y"`.
- `build_railing_corner(asset, ..., length_x, length_y, ...)` — two straight runs meeting at `(x, y)`, an L-shape (e.g. around a platform's two open edges).

### `columns.py`
- `build_column(asset, name_prefix, x, y, z, height, radius, style, mat, base_height, capital_height)` — base plinth + shaft + capital (3 real objects). `style="round"` uses cylinders, `style="square"` uses boxes of equivalent footprint.

### `stairs.py`
- `build_staircase_straight(asset, name_prefix, x, y, z, num_steps, step_width, step_depth, step_height, step_mat, handrail_mat=None, direction="y")` — real individual riser steps (each step's own box, height growing with `i+1` so each tread sits on solid risers, not floating slabs), plus an optional sloped handrail (posts growing in height along the run + one angled rail bar at the correct real slope, via `atan2`).

### `roofing.py`
- `build_canopy(asset, name_prefix, x, y, z, width, depth, support_height, support_mat, roof_mat, post_radius)` — 4 corner posts + 1 flat roof slab.
- `build_gable_roof(asset, name_prefix, x, y, z, width, depth, pitch_height, thickness, mat)` — two angled panels meeting at a center ridge, a real pitched silhouette (not a flat slab).

### `spandrels.py`
- `build_spandrel_band(asset, name_prefix, x, y, z, width, depth, thickness, height, mat, door_gap=None, door_side=None)` — the Phase 2/6 perimeter-ring pattern, now a real reusable function instead of being hand-written inline in 3 different phase scripts. `door_gap`/`door_side` split that side into two segments leaving a real opening, same as Phases 6/7/9's inline door-gap logic.

## Known limitations (stated plainly)

- No real window/door hardware detail (handles, hinges) — frame + glass/leaf only.
- Staircases are straight flights only; no winders/landings/switchbacks.
- The gable roof is a simple two-panel pitch; no hip roofs, dormers, or overhangs beyond the panel's own footprint.
- Every assembly is still primitive-based (boxes/cylinders) — no curved/organic architectural forms.
- Heavy real instancing opportunity exists across every assembly (window frame bars, railing posts, column base/capital pairs) — correctly flagged by the CLI validator's duplicate-mesh detector, intentionally NOT auto-converted here; that's `geometry.instancing.create_instance`'s job at the call site, same discipline as every KOBA CASINO & RESORT phase.

# Hotel furniture assemblies

Real multi-part furniture (bed = frame + mattress + headboard +
pillows, sofa = base + backrest + 2 arms, wardrobe = body + visible
door panels, etc.) instead of the single undifferentiated boxes every
KOBA CASINO & RESORT hotel/pool/VIP phase used before this.

Added `materials/fabric.py` (`woven_fabric`) alongside this group —
every prior bed/sofa/pillow in this project reused
`materials.plastic.glossy_plastic`, which is wrong for cloth (glossy
vehicle-body finish vs. matte woven fabric); this was the one real
material-system gap worth filling for this group, per the user's own
"extend only when necessary" instruction.

Validated for real in `tests/test_assembly_furniture.py`: one example
of every assembly together — **40 entities, 1104 triangles, 21
materials, PASS against `60fps_standard`, 100% collision/LOD
coverage.**

## Modules

### `beds.py`
- `build_bed(asset, name_prefix, x, y, z, size, frame_mat, mattress_mat, headboard_mat, pillow_mat, num_pillows=2)` — frame + mattress + headboard + N separate pillows (6 real objects for `num_pillows=2`). `size` in `("single","double","king")` picks a real footprint from `BED_SIZES` — not a guessed dimension.

### `desks.py`
- `build_desk_and_chair(asset, name_prefix, x, y, z, desk_width, desk_depth, desk_height, top_mat, leg_mat, chair_mat)` — desk top + 4 real cylinder legs, plus a simple chair (seat + backrest + 4 legs) placed in front (11 real objects).
- `build_nightstand(asset, name_prefix, x, y, z, width, depth, height, body_mat, drawer_mat)` — body + an inset drawer face (2 objects) — real enough to read as "nightstand," not "unlabeled box."

### `seating.py`
- `build_sofa(asset, name_prefix, x, y, z, width, depth, seat_mat, back_mat, arm_mat)` — base + backrest + 2 arms (4 objects).
- `build_lounge_daybed(asset, name_prefix, x, y, z, length, width, cushion_mat, frame_mat)` — frame + a flat base cushion + a tilted (real angled, via `rotation_euler`) back cushion (3 objects) — the pool-lounger upgrade Phase 5c's flat box didn't have.

### `bathroom.py`
- `build_toilet(asset, name_prefix, x, y, z, mat)` — base + bowl + tank (3 objects, cylinder-based silhouette).
- `build_sink(asset, name_prefix, x, y, z, width, mat, faucet_mat)` — cabinet + basin + faucet (3 objects).
- `build_shower_stall(asset, name_prefix, x, y, z, width, depth, height, glass_mat, frame_mat, head_mat)` — 2 real glass panels + frame + shower head (4 objects).

### `storage.py`
- `build_wardrobe(asset, name_prefix, x, y, z, width, depth, height, body_mat, door_mat, num_doors=2)` — body + N visible door panels (4 objects for `num_doors=2`).

## Known limitations (stated plainly)

- No interior detail (shelves, hangers inside the wardrobe; tank lid/flush handle on the toilet) — exterior silhouettes only.
- No bedding wrinkle/drape detail — mattress and pillows are flat boxes, recognizable but not soft-body-simulated.
- Bathroom fixtures have no plumbing connections modeled (no pipes, no drain).
- Every assembly is still primitive-based — same standing limitation as the architecture group.
- Real instancing opportunity flagged (bed pillows, desk/chair legs, wardrobe doors, sofa arms) — intentionally not auto-converted, same discipline as everywhere else in this project.

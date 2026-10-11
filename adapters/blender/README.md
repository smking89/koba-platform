# Blender Procedural Asset System

A reusable Python framework for generating game-ready 3D assets inside
Blender, driven by Claude Code. Assets are described as Python calls into
reusable modules (geometry, materials, rigging, animation, optimization,
export), not one-off scripts.

This is the Blender adapter inside **Koba Creator Engine** (merged
2026-09-27 from a separate `blender_asset_system` project — see
[../../README.md](../../README.md) and [../../ROADMAP.md](../../ROADMAP.md)
for the whole engine, including the planned orchestration layer that
would wrap this framework alongside Inkscape/GIMP/Krita/ImageMagick/FFmpeg).

## Environment (verified on this machine, 2026-09-27)

- Blender **5.2.2 LTS**, installed at
  `/home/koba/Downloads/blender-5.2.2-linux-x64/blender`
  (not on `$PATH`, not installed via a package manager — invoke by full
  path or add it to `PATH` yourself).
- Runs headless: `blender -b --python <script>` works and has full `bpy`
  access, confirmed with Python 3.13.13 embedded.
- Render engine identifier in this build is `BLENDER_EEVEE` only (legacy
  EEVEE and "EEVEE Next" have been merged under this single id — don't
  branch on `BLENDER_EEVEE_NEXT`).
- Export operators confirmed present: `bpy.ops.export_scene.fbx`,
  `bpy.ops.export_scene.gltf`, `bpy.ops.wm.obj_export`,
  `bpy.ops.wm.usd_export`.
- There is **no verified direct Blender-to-Rust (RustEdit) export
  pipeline** — Rust/Facepunch asset import is normally a Unity +
  Oxide/Carbon workflow, not something Blender exports to directly. The
  `export_game_asset(target="rust")` preset falls back to generic FBX and
  logs a warning rather than inventing settings. Treat this as an open
  problem, not a solved one.

## Directory layout

```
config/      Environment + naming + export presets (no magic numbers elsewhere)
core/        Asset object, scene/collection/transform/naming utilities, validation, preview
geometry/    Parametric mesh generators (primitives.py, mesh_utils.py)
materials/   Centralized material manager + reusable PBR generators (metal, wood, ...)
optimization/  LOD generation, collision generation
export/      Centralized exporter wrapping verified export presets
tests/       testN_*.py — increasingly complex validation assets (see project brief)
scripts/     CLI entry points runnable from the terminal
assets/      generated/ (.blend files), exports/ (fbx/glb/obj), previews/ (PNG renders)
```

## Interactive live mode (default)

`INTERACTIVE_MODE = True` in `config/blender_config.py` is the default
development mode: a normal GUI Blender window stays open and visible, and
Claude drives it through a small local socket bridge instead of
launching short-lived headless (`-b`) processes. Headless mode is only
for explicitly requested batch/CI/export work (see "Headless / batch
mode" below) — it never runs automatically otherwise.

**Why a socket bridge, not GUI automation.** Blender has no built-in
remote-control channel, and this machine has no `xdotool`/`pynput` and no
passwordless `sudo` to install one, so simulating clicks/keystrokes into
an *already-running* window isn't reliably available. The approach that
actually works with what's on this machine: launch Blender's normal GUI
(no `-b`) with a `--python` startup script — a real, documented Blender
CLI feature — that opens a tiny local TCP listener on a background
thread. The GUI event loop keeps running exactly as normal (the window
stays fully open and interactive); the listener just lets Claude push
Python snippets into it afterward. Execution of received code is
marshalled onto Blender's main thread via `bpy.app.timers` (required
because `bpy` isn't thread-safe from arbitrary Python threads), and all
snippets share one persistent namespace — like a REPL — so an `Asset`
object created in one call is still there for the next one.

**Starting the live session** (only needed if no bridge is already
running — check first with `python3 scripts/blender_client.py --check`):

```bash
setsid nohup /home/koba/Downloads/blender-5.2.2-linux-x64/blender --python live/blender_live_server.py \
  > /tmp/blender_gui.log 2>&1 < /dev/null &
disown
```

`setsid` matters: without it, the Blender process stayed attached to the
launching shell's process group and was observed to die a few seconds
after the launching command returned, even with `nohup`/`disown`/output
redirected — `setsid` fully detaches it into its own session so it
survives independently of whatever shell started it.

**Sending code to the running session:**

```bash
python3 scripts/blender_client.py --check              # UP / DOWN
python3 scripts/blender_client.py -c "print(bpy.app.version)"
python3 scripts/blender_client.py live/snippet_test_crate.py
```

The response protocol is `OK`/`ERROR` followed by captured stdout/stderr.

**Rules for live snippets** (see `live/snippet_test_crate.py` for a
working example):
- Never call `core.scene.reset_scene()` in live mode — it factory-resets
  the whole file and would wipe unrelated work sitting in the same
  session. Use `core.scene.clear_asset_collection(asset_name)` instead,
  which only removes that one asset's own `ASSET_<name>` collection tree.
- Call `core.scene.frame_objects(asset.geometry_objects)` after a
  meaningful stage so the viewport actually shows what changed — this
  only works with a real GUI window (it overrides a `VIEW_3D` area that
  doesn't exist in headless mode).
- Break large assets into multiple snippets/stages (primary geometry,
  then secondary, then materials, ...) rather than one giant script, so
  progress is visible incrementally rather than appearing all at once.
- `bpy.ops.wm.save_as_mainfile(filepath=...)` works normally from a
  snippet and does **not** close the window — save at milestones, don't
  wait until the very end.
- Editing a framework file (`core/*.py`, `geometry/*.py`, ...) takes effect
  on the **next** snippet you send — the bridge reloads every previously
  imported project module before each execution, so you never need to
  restart Blender just because a `.py` file changed.

## Headless / batch mode

Use this only when explicitly asked for automated testing, CI, batch
generation, or background export — not for normal asset development.

## Running things

All commands below were actually executed against this repo and produce
real output — nothing here is aspirational.

Generate the registered "crate" test asset (geometry, materials, UVs,
collision, LOD1, validation report, preview render, .blend save, FBX
export):

```bash
/home/koba/Downloads/blender-5.2.2-linux-x64/blender -b --python scripts/generate_asset.py -- --asset crate
```

Run a phase test directly (equivalent, useful while developing a new test):

```bash
/home/koba/Downloads/blender-5.2.2-linux-x64/blender -b --python tests/test1_crate.py
```

Outputs land in:
- `assets/generated/<AssetName>.blend`
- `assets/exports/<AssetName>.fbx`
- `assets/previews/<AssetName>_<angle>.png`

## Real PBR textures (Poly Haven / ambientCG)

`textures/texture_manager.py` fetches real photo-based PBR texture sets
from two free, unauthenticated APIs and wires them into a material's
Principled BSDF — verified against the live APIs, not guessed:

- **Poly Haven** (`api.polyhaven.com`) — no API key, but its API returns
  `403 Forbidden` for Python's default `urllib` User-Agent; the module
  sends a custom one.
- **ambientCG** (`ambientcg.com/api/v2`) — no API key; assets download as
  a `.zip` that the module extracts automatically.
- **Poliigon** (`poliigon.com/textures/free`) is NOT supported — its free
  downloads are gated behind an account login on the website, not a
  scriptable API. Fetch those manually if ever needed.

```python
from textures.texture_manager import search_polyhaven, download_polyhaven_texture, apply_image_textures

search_polyhaven("rust")                              # [(asset_id, name, categories), ...]
paths = download_polyhaven_texture("corrugated_iron", resolution="1k")   # downloads to assets/textures/downloaded/
apply_image_textures(some_material, paths)             # wires Diffuse/Rough/Normal into the Principled BSDF
```

`search_ambientcg` / `download_ambientcg_texture` are the ambientCG
equivalents. Downloading is a real network+disk action — nothing in this
module writes a file until a caller explicitly calls a `download_*`
function; it isn't triggered automatically by any asset generator.

## Cube Clash sponsor-skin generator (brand hex colors + logo decal)

`generators/voxel_sponsor_skin.py` is a real implementation of one piece
of the "Cube Clash" game spec's Automated Ad Economy (its "Asset
Automation Core"): an advertiser's brand hex colors + logo image drive a
headless Blender run that builds, textures, optimizes, and exports a
custom voxel block skin as a `.glb`. This module owns only that — it
does not run a web portal, check calendar availability, take a payment,
or write to a game-server database; a separate backend service would
call `generate_and_export()` once an order is confirmed and hand it
nothing but already-validated inputs.

- **`materials/branding.py`** — `simple_color_material(name, hex_color, roughness=0.7)`
  converts an arbitrary `#RRGGBB` string straight into a matte Principled
  BSDF material. Separate from `materials/pbr_library.py`'s curated
  texture sets on purpose: a sponsor skin's entire point is to be exactly
  the advertiser's brand color, not a stock material.
- **`geometry/decals.py`** — `apply_logo_decal(obj, image_path, material_name, normal_axis="z", sign=1)`
  stamps one image onto one face of an existing box by appending a
  dedicated logo material as a second material slot and assigning just
  that face to it (via `geometry.detailing.find_face_by_normal`) — every
  other face keeps its brand-color material. Relies on `create_box`'s
  existing cube-project UV unwrap already giving each face a roughly
  0..1 UV quad; no custom UV packing needed for a flat decal.
- **`generators/voxel_sponsor_skin.py`** — `build_sponsor_voxel_skin(advertiser_name, primary_hex, secondary_hex, logo_path=None, poly_budget=5000)`
  builds a 3-block voxel tile (ground/accent/corner), colors it from the
  two brand hex codes, decals the logo onto the accent block's top face
  if given, and auto-decimates if the real triangle count exceeds
  `poly_budget`. `generate_and_export(...)` wraps that with
  `core.validation.validate_asset` and a `.glb` export via the existing
  `gltf_generic` preset — returns `(asset, export_path, validation_report)`.

Verified live, both paths: `tests/test9_sponsor_voxel_skin.py` (no logo)
and a manual run against a real Cube Clash logo PNG both produced a
validated, exported `.glb` (18 polys, `PASS`), with the logo-decal run
confirming exactly 2 materials on the accent block (brand color + the
one stamped face) — not texturing the whole mesh.

## Performance & optimization architecture (PC-only)

Koba Creator Engine targets **PC only** — no console (Xbox/PlayStation)
profiles or budgets anywhere in this system. The core principle: entity
count is a first-class optimization metric, not a side effect of however
detailed the asset specification is. "How can the player SEE lots of
detail while the engine only has to PROCESS a fraction of it?"

- **`core/entity_metadata.py`** — every object added via `Asset.add_geometry(obj, metadata=...)`
  carries an `EntityMetadata` (static/dynamic/interactive/destructible/
  physics/animated/collision_required/instanceable/mergeable/
  lod_required/cullable/visibility_group/importance). This is what later
  optimization stages read to decide what's safe to instance/merge/cull —
  they never infer it by guessing from geometry alone. Presets:
  `for_static_prop`, `for_instanced_prop`, `for_mechanism`,
  `for_rigid_group_member` (moves because its *parent* is animated, but
  has no animation of its own — e.g. a crane cab riding the slew turret),
  `for_hero_asset`.
- **`geometry/instancing.py`** — `create_instance()` / `create_instance_grid()`
  use Blender's own native instancing (multiple Objects sharing one Mesh
  datablock) — not a simulated layer on top. `count_unique_meshes()` is
  the metric that actually matters for memory/load time, as distinct from
  raw entity count.
- **`optimization/merge.py`** — `merge_static_group()` joins objects into
  one mesh via `bpy.ops.object.join`, but refuses (raises `MergeRefused`)
  if any object's metadata says `mergeable=False` — it will not silently
  fuse an animated/interactive part into static geometry.
- **`config/performance_profiles.py`** — PC performance budgets (60/90/
  120/144/165/240 fps + an unbudgeted cinematic profile), a plain Python
  dict, not YAML — **Blender's bundled Python has no `pyyaml` installed**
  (verified directly), so anything loaded inside Blender uses plain-Python
  config, matching the existing convention in `config/export_config.py`.
- **`optimization/performance_validator.py`** — `validate_performance(asset, profile_name)`
  produces a KOBA PERFORMANCE REPORT (entity/unique-mesh/instance/
  triangle/material/light/physics/animated counts, collision+LOD
  coverage) and a PASS/FAIL against the chosen budget, plus warnings
  (e.g. low instancing reuse ratio for a large entity count).

**Test 4** (`tests/test4_instancing_demo.py`) proves this end to end: a
40-"slot-machine" layout built via instancing keeps `unique_meshes == 1`
and passes validation even against the strictest `240fps_esports`
profile, versus a deliberately-naive comparison build (one unique mesh
per copy) with `unique_meshes == 40` — same visible result, very
different runtime cost.

**Deferred, not built** (the full spec has 24 sections; this is a real,
tested vertical slice of the core pieces, not the whole thing): distance
culling / LOD-transition distances, zone/portal visibility & occlusion
structures, material/texture-atlas consolidation, automatic-fix
optimization passes (auto-instancing detection, auto-consolidating
duplicate materials), deterministic seeded generation, and lighting
static/dynamic classification beyond simple sun-vs-other-light counting.

## Adding a new asset generator

1. Write a `build_<name>(...)` function in `tests/testN_<name>.py` (while
   iterating) or `generators/<category>/<name>.py` (once stable). It should:
   - call `core.scene.reset_scene()`
   - construct a `core.asset.Asset(name, asset_type)`
   - build geometry via `geometry/*` helpers, register it with
     `asset.add_geometry(obj)`
   - get materials via `materials.material_manager.get_or_create` (or the
     per-material-family helpers in `materials/metal.py`, `wood.py`, etc.)
     — never call `bpy.data.materials.new` directly in a generator
   - generate collision (`optimization/collision.py`) and LOD
     (`optimization/lod.py`) where appropriate — not unconditionally for
     every asset
   - return the `Asset`
2. Register it in `scripts/generate_asset.py`'s `BUILDERS` dict.
3. Run it, read the validation report, fix warnings, look at the preview
   PNG before declaring it done.

## Known limitations (documented, not silently skipped)

- **Curved pipes** (following an arbitrary path) are not implemented —
  `geometry.primitives.create_pipe` is straight-only for now.
- **Rigging and animation modules are not yet built.** `core.validation`
  will correctly report `[WARNING] Rig` / `[WARNING] Animation` until
  they exist — that warning is accurate, not a bug.
- **Only box collision** is implemented (`optimization/collision.py`).
  Convex/compound collision generation is a later phase.
- **LOD generation is decimate-only**, single ratio per call — no
  automatic LOD0-3 ladder yet, by design (see project brief: don't
  generate LODs blindly).
- Two rendering gotchas already hit and fixed once — don't reintroduce them:
  - Blender's default **AgX view transform desaturates bright diffuse
    surfaces toward gray**; `core.preview.render_preview` explicitly sets
    `view_transform = "Standard"` so preview colors are trustworthy.
  - `display_type = "WIRE"` on collision meshes is **viewport-only** — it
    still renders as a solid gray box in F12/headless renders unless you
    also set `hide_render = True` (done in `optimization/collision.py`).
    The same applies to hidden LOD levels (`optimization/lod.py`).

## Phase status (see original project brief for the full 33-phase plan)

| Phase | Status |
|---|---|
| 1. Environment detection | Done |
| 2. Core framework | Done (asset, naming, collections, scene, transforms, logging, validation) |
| 3. Geometry system | Minimal (box, panel, cylinder, straight pipe) — not architecture/hard-surface/vehicle libraries yet |
| 4. Material system | Minimal (manager + metal.py + wood.py) — not the full material list from the brief |
| 5, 11 (UV depth, weathering) | Not started |
| 10. Procedural textures / real textures | Minimal (Poly Haven + ambientCG download-and-apply pipeline — see "Real PBR textures" above; no procedural noise-based texture library yet beyond `materials/wood.py`'s grain) |
| 6. Rigging | Minimal (mechanical hinge + slider primitives only — no vehicle/character rigs) |
| 7. Animation | Minimal (hinge rotation + slider translation keyframing only) |
| 12. Export | Minimal (FBX/glTF/OBJ presets, generic + rust-fallback target) |
| 13-14. Optimization / collision | Minimal (single-ratio decimate LOD, box collision only) |
| 15-17. Transforms/naming/collections | Done as part of core |
| 18. Validation | Done (readable PASS/WARNING/FAIL report) |
| 19. Preview rendering | Done (single-angle render; multi-angle sweep not wired into CLI yet) |
| Performance/optimization architecture (entity metadata, instancing, static merge, PC performance budgets + validator) | Minimal but real — see "Performance & optimization architecture" above. Distance culling, zone/portal visibility, and automatic-fix optimization passes not built. |
| 20-32 | Not started |

**Interactive live-generation mode** is built and verified: launching the
GUI Blender with `live/blender_live_server.py`, driving it via
`scripts/blender_client.py`, and confirming (via Outliner/Properties
state and a real screenshot) that generated geometry appears in the
already-open window without ever closing it.

Tests 1-3 (procedural crate, industrial door, mechanical crane) are
complete and passing, headless and live. Test 2 introduced the first
rigging/animation primitives (`rigging/mechanical.create_hinge`/
`create_slider`, `animation/mechanical.animate_hinge_rotation`/
`animate_slider_translation`). Test 3 extended those to a real multi-part
mechanism — independent slew (base rotation), boom pitch, and a hook
winch that tracks the boom tip horizontally while dropping independently
in world Z (`rigging/mechanical.create_follow_point` +
`add_copy_location_constraint`) — and pushed `core.asset.rig` from a
single dict to a list so multi-DOF assets can register more than one rig
component. All three tests are broken into discrete `stage_*()` functions
matching the brief's STAGE 01-14 structure, independently callable over
the live bridge.

Building the crane surfaced a serious, previously-silent framework bug
(now fixed and documented below): reading `matrix_world` immediately
after setting `.location` on a freshly created/linked object returns a
stale identity matrix until Blender's depsgraph is evaluated, which
silently broke nested-empty parenting (a hinge parented to another hinge)
by doubling the child's effective position. It happened to be invisible
for test 1/2's single-level parenting but was severe for test 3's
2-level slew→boom chain. Fixed at the shared root
(`core.transforms.parent_keep_transform`) plus every other direct
`matrix_world` read in the framework, rather than patched per call site.

Test 4 (repeated-asset instancing demo) is complete and passing,
headless and live — see "Performance & optimization architecture" above.

Test 6 (`tests/test6_boat.py`, procedural small boat) is complete and
passing headless. It introduced `geometry.primitives.create_hull` — a
lofted 5-vertex-ring tapered hull (stern flat/full, bow narrowing to a
near-point), the first non-box/cylinder procedural shape in the
framework. The hull's deck line is intentionally left open (like a
dinghy) rather than capped, which is why validation reports a
"non-manifold edges" warning on the hull mesh — documented, not a bug;
there is no deck-plate generator yet.

Tests 9-11 (`tests/test9_jetski.py`, `test10_yacht.py`,
`test11_monument.py`) are complete and passing headless. The jet ski and
yacht reuse `create_hull` at different proportions (narrow/sporty vs.
wide/full) rather than needing a new hull generator — the yacht adds a
multi-level cabin superstructure (stacked boxes) on top. Both introduced
`materials.plastic.glossy_plastic` (vehicle-body glossy plastic/
fiberglass — wood/metal/candy existed, nothing non-metallic-and-glossy
did). The monument introduced `geometry.primitives.create_pyramid` (a
flat-faced tapered obelisk tip via a low-vertex-count cone) and
`materials.stone.carved_stone`, and is a stepped-base obelisk with corner
pillars and a plaque — the cleanest validation of this whole series (no
warnings at all beyond the standard missing-rig/-animation ones, since
it's built entirely from closed box/cylinder/pyramid primitives with no
open-hull compromise). This is a single showcase prop, not the master
spec's full "Monuments" product type (an actual KOBA content category
with its own pipeline — not started, see ROADMAP.md).

A dock/ferry terminal from the original project brief's Test 7-9 list
still hasn't been built — build it next by following "Adding a new asset
generator" above, extracting any new reusable geometry/material logic
into the shared modules as you go (per the project brief's
self-improving development loop).

## Gotchas discovered while building the live bridge (don't reintroduce)

- **`setsid` is required** when launching the GUI Blender from a script/tool
  process — `nohup ... &` plus `disown` alone was observed to let the
  process die a few seconds after the launching command returned. Always
  launch via `setsid nohup blender --python ... < /dev/null > log 2>&1 &`.
- **Bind the bridge socket before reporting success.** The first version of
  `live/blender_live_server.py` printed "listening" immediately after
  spawning the accept-loop thread, not after the thread's `bind()` actually
  succeeded — a port conflict failed silently. `start()` now does
  `socket.bind()`/`listen()` on the main thread itself before starting the
  thread, so a failure raises immediately and visibly instead.
- **`obj.matrix_world` is stale (identity) immediately after setting
  `.location`** on a freshly created/linked object, until
  `bpy.context.view_layer.update()` runs — confirmed by direct testing, not
  assumption. This silently breaks any code that parents object B to
  object A right after positioning A, if A was *itself* just repositioned/
  reparented in the same script with no operator call in between (operator
  calls like `transform_apply` happen to force an update as a side effect,
  which is why this stayed hidden in tests 1-2's simpler parenting and only
  surfaced as a doubled position in test 3's nested slew→boom hinge chain).
  Fixed once in `core.transforms.parent_keep_transform` (and every other
  direct `matrix_world` reader in the framework) rather than worked around
  per call site — call `parent_keep_transform`/the rigging helpers instead
  of writing `.parent =` / `.matrix_parent_inverse =` by hand.
- **Blender 5.x replaced the flat `Action.fcurves` API** with a layered
  model: `action.layers[].strips[].channelbags[].fcurves`. Code written
  against older Blender API docs/tutorials referencing `action.fcurves`
  directly will raise `AttributeError` on this build — see
  `animation/mechanical._iter_fcurves()` for the correct traversal.
- **Default viewport shading is "Solid," which does not show real material
  colors** — a freshly launched GUI Blender shows everything flat gray
  until the viewport is switched to Material Preview or Rendered shading
  (the four sphere icons top-right of the 3D viewport, or the `Z` pie
  menu). This is a per-session UI setting, not part of the scene data, so
  it isn't something a build script should need to fix permanently — but
  since the user can't be assumed to know to click it, proactively set it
  once after the first meaningful geometry appears:
  `space.shading.type = 'MATERIAL'` on every `VIEW_3D` space (see the
  one-off fix applied live during the crane build for the exact snippet).
- **"Material Preview" shading is still not enough for transmission/
  subsurface materials** (e.g. `materials.candy.gummy_material`) — it
  uses a fixed studio-HDRI lighting rig and ignores the scene's own
  lights, so translucent/SSS materials render flat with no real shading
  or shadows, reading as "just a flat color." Confirmed by comparing the
  live viewport against a headless `render_preview()` of the same asset —
  the render looked correctly glossy/translucent while Material Preview
  looked flat. Fix: switch to **Rendered** shading instead
  (`space.shading.type = 'RENDERED'`, plus
  `space.shading.use_scene_lights_render = True` and
  `use_scene_world_render = True` so it actually uses the scene's lights/
  world rather than its own studio setup) and make sure
  `scene.eevee.use_raytracing = True` (off by default) — see
  `tests/test5_gummy_gun.py`. Don't force Rendered mode as the default for
  every asset via `frame_objects()` though — it's slower than Material
  Preview and unnecessary for plain opaque materials; only switch to it
  when the asset actually uses transmission/subsurface.
- **The pose/result differs from a headless preview screenshot only
  because of camera framing.** A headless render uses `core.preview`'s
  scripted three-quarter camera; the live GUI viewport uses whatever the
  user last navigated to. Same geometry, different vantage point — not a
  bug, don't chase it as one.
- **Python module caching**: the live Blender process keeps every imported
  framework module in memory for its entire lifetime. Editing `core/*.py`
  etc. does nothing to an already-running session unless something calls
  `importlib.reload()` — handled automatically now by
  `_reload_project_modules()` in the bridge before every executed snippet.

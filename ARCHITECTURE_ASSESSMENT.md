# KOBA Creator Engine — Architecture Assessment vs. Master Production Architecture v2.0

Produced per the spec's own "FIRST ACTION" instruction: inspect before
rewriting. This is a gap analysis, not a rewrite. Source spec:
`~/Desktop/koba pc engine stuff/KOBA CREATOR ENGINE MASTER PRODUCTION
ARCHITECTURE_260928_235448.txt` (2026-09-28).

**Headline finding**: what exists today is a real, tested, working asset
*generation* toolkit (~1,000 lines of orchestration code + a substantial
Blender adapter). What the spec describes is a multi-AI-provider
production *platform* — job orchestration, an artifact graph with
lineage/hashing, a validation authority separate from AI, automated
repair loops, a compiler/signing/packaging pipeline, and marketplace/
KOBA-Live/KOBA-Core/telemetry integration points. These are not the same
scale of system. Sections 9-25 of the target document to almost
scratch — nothing resembling a job queue, artifact graph, repair loop,
compiler, or manifest-signing exists. This assessment says so plainly
rather than mapping a handful of existing files onto those names and
calling it done.

## 1. Current architecture map

```
koba_creator_engine/
├── asset-factory              CLI entry point (argparse)
├── cli/main.py                 doctor, create, status, logs, validate, optimize, process — REAL
│                                everything else — HONEST STUB (prints "not implemented", exit 2)
├── core/
│   ├── config.py                YAML config loader (tools.yaml, defaults.yaml, export_profiles.yaml)
│   ├── detection.py              Tool detection (subprocess --version probing)
│   ├── logging_setup.py          Per-invocation JSON log files (core/logging_setup.OperationLog)
│   ├── manifest.py               Flat per-project JSON manifest (assets/tools/exports/errors/warnings)
│   └── project.py                Project directory scaffolding + registry
├── adapters/
│   ├── blender_bridge.py         Shells out to headless Blender scripts, parses one JSON line back
│   ├── inkscape_adapter.py       Real subprocess wrapper (export_png/pdf/variants)
│   ├── imagemagick_adapter.py    Real subprocess wrapper (resize/convert/thumbnail/mip chain)
│   └── blender/                  Full Blender procedural-asset framework (see below) — the mature part
├── config/*.yaml                 Tool paths, defaults, export profiles
├── tests/                        5 real test modules incl. one live Blender subprocess integration test
└── projects/<name>/              Per-project workspace: source/blender/inkscape/gimp/krita/textures/
                                   models/materials/animations/renders/previews/optimized/exports/
                                   marketplace/logs + project.json manifest

adapters/blender/  (the mature subsystem — a self-contained procedural asset toolkit)
├── core/            Asset container, entity metadata, naming, collections, scene/transform helpers,
│                    a lightweight "reconstruct an Asset from a saved .blend's custom properties" layer
├── geometry/        Parametric primitives, instancing, mesh utilities
├── materials/       Material generators (metal, wood, candy/gummy, procedural)
├── rigging/         Mechanical hinge/slider/follow-point rig primitives
├── animation/       Hinge-rotation / slider-translation keyframing
├── optimization/    Culling metadata, static merge, LOD, collision, performance validator
├── textures/        Poly Haven + ambientCG PBR texture download/apply pipeline
├── export/          FBX/glTF/OBJ export presets
├── live/            A socket-bridge server for driving an already-open GUI Blender interactively
├── scripts/         Headless entry points (run_validate.py, run_optimize.py, blender_client.py)
└── tests/           5 working end-to-end asset builds (crate, door, crane, instancing demo, gummy gun)
```

This is **Layer 3 (Tool Contracts + Adapters)** and a slice of **Layer 4
(Deterministic Production)** from the target spec, with a thin,
non-authoritative sliver of **Layer 2 (Orchestration)** — a CLI and a
flat manifest, not a job/pipeline/dependency system.

## 2. Existing components (mapped against the target's 5 layers)

| Target layer | What exists | What's missing |
|---|---|---|
| 1. Intelligence (AI Router/Providers/Agents) | **Nothing.** Claude Code itself has been the "intelligence," operating directly on the filesystem/CLI in this session — there is no `ai_router`, provider abstraction, or agent framework in the repo | Everything: `ai/ai_router`, `providers/*`, `agents/*`, `tool_selector`, `output_validator` |
| 2. Orchestration | `cli/main.py` (direct command dispatch), `core/project.py` (directory scaffolding), `core/logging_setup.py` (per-call JSON logs) | `pipeline_manager`, `job_queue`/`job_scheduler`, `dependency_graph`, `checkpoint_manager`, `retry_manager`, `repair_manager`, `worker_manager`, `execution_context`, `build_state` machine (section 23) — none exist. Nothing is async, queued, or resumable beyond "re-run the CLI command" |
| 3. Tool Contracts + Adapters | `adapters/blender_bridge.py`, `adapters/inkscape_adapter.py`, `adapters/imagemagick_adapter.py`, `bin/gimp-flatpak-wrapper.sh` (invocable but no `GimpAdapter` class yet) | No `tool_contracts`/`tool_registry`/`tool_permissions`/`tool_schemas`/`tool_audit` layer — the CLI calls adapters directly, there is no authorization boundary. No RustEdit or FFmpeg adapter (FFmpeg not installed; RustEdit not evaluated at all — see `adapters/blender/config/export_config.py`'s note that no verified Blender→Rust pipeline exists) |
| 4. Deterministic Production | Real: geometry/materials/rigging/animation/optimization inside `adapters/blender/`, covering props, mechanisms, and a PC performance-budget system | No CUI, Monuments-as-a-product-type, NPCs, Events, Vehicles-as-a-pipeline, Audio, VFX, or Building-Skins processors. What exists is asset/prop-level, not game-content-level |
| 5. Artifact/Validation/Compilation | `core/manifest.py` (flat list of assets/exports/errors/warnings per project), `adapters/blender/core/validation.py` + `optimization/performance_validator.py` (real PASS/WARN/FAIL reports) | No artifact graph (no ArtifactID/lineage/hashing/dependency edges), no validator *registry* or authority separation from AI, no repair loop, no compiler, no packaging/signing |
| External ecosystem (Marketplace/Live/Core/Telemetry) | Nothing | Nothing — no `integrations/koba-core`, `integrations/marketplace`, `integrations/koba-live`, `integrations/telemetry` |

## 3. Existing scripts

- `asset-factory` — CLI entry shim
- `adapters/blender/scripts/run_validate.py`, `run_optimize.py` — headless Blender entry points invoked by `blender_bridge.py`
- `adapters/blender/scripts/blender_client.py` — TCP client for the live-GUI socket bridge
- `adapters/blender/live/blender_live_server.py` — the socket bridge server run *inside* an interactive Blender session
- `adapters/blender/tests/test1_crate.py` … `test5_gummy_gun.py` — five working staged asset builders
- `tests/test_detection.py`, `test_manifest.py`, `test_project.py`, `test_adapters.py`, `test_cli.py`, `tests/run_all.py` — orchestration-layer test suite

## 4. Existing adapters

| Adapter | Real? | Notes |
|---|---|---|
| Blender | ✓ | Via `blender_bridge.py` (headless subprocess) *and* a separate live-GUI socket bridge — two different transport mechanisms, not yet unified under one `BlenderAdapter` class matching the spec's `discover_installation/detect_version/check_capabilities/launch/...` interface |
| Inkscape | ✓ | `InkscapeAdapter` class exists, methods are ad hoc (`export_png`, `export_variants`) rather than the spec's generic `execute_supported_operation()` shape |
| ImageMagick | ✓ | `ImageMagickAdapter`, same ad-hoc-methods caveat |
| GIMP | Partial | Flatpak wrapper script exists and is detected by `core/detection.py`; no `GimpAdapter` class with actual operations yet |
| RustEdit | ✗ | Not started. No capability has been verified — per this repo's own existing honesty rule (`adapters/blender/config/export_config.py`), do not invent one |
| FFmpeg | ✗ | Not installed on this machine, not started |

None of the existing adapters implement the spec's exact required
interface (`discover_installation()`, `check_capabilities()`, `monitor()`,
`collect_artifacts()`, `collect_logs()`, `shutdown()`) — they're
simpler, direct-call wrappers. That interface is a real, valuable target
to converge on, not something to fake as already done.

## 5. Existing KOBA Core interfaces

**None.** There is no `integrations/koba-core/` directory, no manifest
generator aimed at a runtime, no content-registration calls of any kind.
KOBA Core itself is not present in this repository or referenced by any
code — this entire integration layer is unbuilt.

## 6. Existing external-tool integrations

Blender, Inkscape, ImageMagick (all real, tested against actual installed
versions on this machine), GIMP (installed, detected, not yet wrapped in
operations). No RustEdit, no FFmpeg, no Krita adapter code (Krita is not
installed).

## 7. Existing artifact/storage systems

`core/manifest.py` produces one flat `project.json` per project — a list
of assets, tools used, exports, errors, warnings, each with a timestamp.
This has **no ArtifactID, no ParentArtifacts/Dependencies edges, no
InputHash/OutputHash, no ProcessorVersion, no lineage traversal, no
caching/invalidation, no rebuild planning.** It is a log, not a graph.
`projects/<name>/{source,blender,optimized,exports,...}` gives a flat
directory convention (source vs. generated output kept separate, which
*is* consistent with the spec's intent) but nothing computes hashes or
tracks what depends on what.

## 8. Existing validation systems

Two real, working validators exist:
- `adapters/blender/core/validation.py` — geometry/naming/UV/collision/LOD
  checks, PASS/WARNING report
- `adapters/blender/optimization/performance_validator.py` — entity
  count/triangle/material/light/collision/culling coverage vs. a chosen
  PC performance profile, PASS/FAIL report

Both are genuinely deterministic (not AI-judged) and already respect the
spec's Rule 10 ("validators determine pass or fail") in spirit. What's
missing: a validator *registry* (the spec lists ~19 distinct validator
types — topology, dependency, compatibility, manifest, runtime,
interaction, NPC, event, memory, network, security, console-error —
essentially none of which apply yet since there's no runtime/NPC/event/
network content to validate), and no separation layer that would stop an
AI agent from claiming PASS without validator evidence (today, nothing
*stops* that misuse — it just hasn't been built as a foot-gun because
there's no agent layer yet either).

## 9. Missing components (the honest, large list)

Everything in target Layer 1 (AI Router/Providers/Agents — 18 named
agents). Nearly everything in Layer 2 (job queue/scheduler/dependency
graph/checkpoints/retry/repair/worker manager/build-state machine). The
`tool_contracts`/`tool_registry`/`tool_permissions`/`tool_audit`
authorization boundary in Layer 3. RustEdit and FFmpeg adapters. Every
game-content processor beyond geometry/materials/props (CUI, Monuments-
as-product, NPCs, Events, Vehicles, Audio, VFX, Building Skins). The
entire artifact graph (lineage, hashing, dependency-aware incremental
rebuilds). The entire repair subsystem (diagnosis engine, failure
classifier, repair planner/executor/history). The compiler, packaging,
signing, and storage layers. Security (sandbox manager, credential/secret
management, malware scanner, audit logger beyond today's plain-text
logs). Telemetry. All four external integrations (KOBA Core, Marketplace,
KOBA Live, Telemetry). The full `koba-*` CLI surface (only
`create`/`validate`/`optimize`/`process`/`status`/`logs`/`doctor` exist
today, under different names and without job semantics).

## 10. Proposed migration/implementation plan

Given the gap, the honest path is incremental convergence, not a rewrite
— reusing the real, tested adapters and Blender framework as Layer 3/4,
and building the layers above them in order of what unlocks the most
value per unit of work:

**Phase A — Formalize what already works (low risk, immediate value)**
1. Wrap the existing three adapters in the spec's actual interface shape
   (`discover_installation/detect_version/check_capabilities/launch/...`)
   without changing their internals — a real refactor, not a rename.
2. Build a `capabilities/capability_registry` that wraps `core/detection.py`'s
   existing tool-detection + adds Blender/OS/tool-version capability flags,
   returning `UNSUPPORTED_CAPABILITY` rather than guessing (this repo
   already has the right instinct — `export_config.py`'s Rust caveat is
   exactly this pattern, just not registry-shaped yet).
3. Replace the flat `core/manifest.py` with a real (even if simple)
   Artifact node/edge model — ArtifactID, ParentArtifacts, InputHash/
   OutputHash — since almost everything above this layer depends on it
   existing first.

**Phase B — Orchestration skeleton**
4. A `job` abstraction (JobID, isolated workspace under
   `projects/<name>/jobs/<job_id>/`, state machine per section 23) wrapping
   what `cli/main.py`'s commands do today.
5. A minimal dependency graph + incremental-rebuild check (section 5) —
   even just "did this artifact's input hash change" is a real, valuable
   first version.

**Phase C — Tool contracts + first AI agent**
6. A `tool_contracts` layer between the CLI/future-agent and the
   adapters, with input/output schemas and permission checks — this is
   what would let an AI agent call `create_material()` safely instead of
   editing Python directly (which is what this session has been doing).
7. One real agent (e.g. `blender_agent`) wired through an `ai_router`
   with a single provider (Claude) — proves the AI-replaceable design
   without building all 18 agents or 4 providers speculatively.

**Phase D — Validation authority + first repair loop**
8. A `validation_registry` distinguishing "AI suggested a fix" from
   "validator confirmed PASS," using the two validators that already
   exist as the first real entries.
9. One real repair loop end-to-end (e.g. collision failure → repair →
   revalidate → new artifact version), reusing
   `optimization/performance_validator.py` as the trigger.

**Phase E — Compiler/packaging (only once A-D are real)**
10. `koba_compiler` + signed package output. Explicitly deferred until
    there's an actual artifact graph and validation authority to compile
    *from* — building a compiler before those exist would just be
    packaging unvalidated files with extra ceremony.

**Deliberately not started**: Marketplace/KOBA Live/KOBA Core/Telemetry
integrations (section 19-22) — those require an external KOBA Core
runtime that does not exist in this repository or environment; building
integration stubs against a system that isn't there would be fabricating
an integration, which the spec's own Rule 19/section 29 explicitly
prohibits ("do not fabricate integrations").

## Recommendation

Start with Phase A, item 3 (the artifact graph) — it's the one piece
nearly everything else in the spec depends on, it's a bounded, testable
unit of work, and it doesn't require inventing anything (no AI agents, no
external systems) to build correctly. Confirm before I start writing
code, since this is a genuine architectural pivot for the manifest system
every existing CLI command already uses.

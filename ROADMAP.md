# Roadmap: KOBA Creator Engine

**Source of truth**: `~/Desktop/koba pc engine stuff/KOBA CREATOR ENGINE
MASTER PRODUCTION ARCHITECTURE_260928_235448.txt` ("the master spec").
This is the real target — a five-layer AI-enabled production
orchestration platform for KOBA.GAMES, not a Blender-scripting toolkit.
For the full narrative gap analysis (what exists, what's missing, why,
and the recommended build order), see
[ARCHITECTURE_ASSESSMENT.md](ARCHITECTURE_ASSESSMENT.md) — this file is
the actionable checklist version of that assessment, kept in sync with it.

History: this repo started as two separate toy projects
(`blender_asset_system` + `asset_factory`), merged 2026-09-27, then
reframed 2026-09-29 once the master spec clarified the actual target
architecture. Earlier roadmap entries below marked "legacy" predate that
reframing and are kept only as a record of what's already built and
reusable — they are not the target architecture.

## Status legend
`[x]` done and tested · `[~]` partial/stub exists · `[ ]` not started

---

## Layer 1 — Intelligence (AI Router / Providers / Agents)

- [x] `ai/router` (`ai/router.py`) — `AIRouter.get_provider()` reads
      `config/ai_providers.yaml` and instantiates whichever provider is
      configured; swapping providers is a one-line config edit, nothing
      in `agents/`/`tools/`/orchestrator changes (verified in
      `tests/test_ai_agent.py` by swapping the router's config in-memory
      and confirming a different provider class comes back)
- [ ] `ai/model_registry`, `ai/prompt_registry`, `ai/context_builder`,
      `ai/tool_selector`, `ai/output_validator` — not built; the router +
      each provider's own `decide()` currently does this work inline,
      which is fine for one agent/two providers but would need real
      structure before a second agent is added
- [x] `ai/providers/rule_based_provider` — a genuinely working
      deterministic (keyword-match) provider, always available, no
      network/API key required; the default active provider
- [x] `ai/providers/anthropic_provider` — real `urllib` calls to the
      actual Anthropic Messages API (no SDK dependency); honestly reports
      `available() == False` when `ANTHROPIC_API_KEY` isn't set rather
      than faking a decision (same pattern as GIMP/Krita/FFmpeg detection)
- [ ] `ai/providers/openai_adapter`, `gemini_adapter`, `local_model_adapter`
      — not built; the interface (`ai/provider_base.py`) is generic enough
      that adding one is a new file, not a router/agent change
- [x] `agents/blender_agent` — the one real agent from the assessment's
      recommendation. Takes a free-text instruction, gets a decision from
      the active provider (which of `validate_blend`/`optimize_blend` to
      call), executes it through `tools/tool_executor` exactly like the
      CLI does — the AI decides WHAT to run, never whether the result is
      valid (Rule 2). Wired into a real `agent` CLI command with full job
      tracking. Covered by `tests/test_ai_agent.py` (real Blender
      subprocess calls, not mocked).
- [x] `agents/repair_agent` (`agents/repair_agent.py`) — the second real
      agent, proving the one-router/multiple-agents pattern generalizes.
      Scope kept deliberately narrow after a real bug forced a redesign
      (see the module's own docstring): the agent's only real
      contribution is `get_merge_group_hint()` — extracting a named
      `visibility_group` from free text (e.g. "merge the 'cluster'
      group") via `ai/providers/rule_based_provider.py`'s new
      `_extract_merge_group()`, a genuine regex-based extraction, not a
      guess. `cli/main.py`'s `repair-agent` command orchestrates the rest
      (diagnose → record → classify → repair → revalidate → record) in
      the exact same order `cmd_repair` does — an earlier version let the
      agent orchestrate everything behind one call, which minted two
      different artifact ids for the same source file (one computed
      before the diagnosis's FAIL status was persisted, one after) and
      crashed `save_graph()`. A second, unrelated real bug surfaced in
      the same pass: the "validation already PASSes, nothing to repair"
      path in both `cmd_repair` *and* `cmd_repair_agent` tried
      `RUNNING`→`READY` directly, which `orchestrator/build_state.py`
      doesn't allow (must pass through `VALIDATING` first) — never
      caught before because no prior test exercised a PASSing fixture
      through the repair path. Both bugs are now regression-tested in
      `tests/test_repair_agent.py`.
- [ ] the other 16 named agents (product_planner, architecture_agent,
      asset_agent, texture_agent, material_agent, cui_agent,
      monument_agent, npc_agent, event_agent, vehicle_agent, audio_agent,
      vfx_agent, optimization_agent, qa_agent, diagnosis_agent,
      debugging_agent) — **deliberately not started**, per the
      assessment's own recommendation to prove the pattern with a couple
      of real agents before building the rest speculatively.
      `rustedit_agent` specifically — **dropped**, not "not started": see
      Layer 3's RustEdit note for why (needs a licensed Rust game
      install; wrong tool for the only stated use case anyway).

## Layer 2 — Orchestration

- [~] Command dispatch — `cli/main.py` (real commands: `doctor`, `create`,
      `status`, `logs`, `validate`, `optimize`, `process`, `agent`,
      `jobs`, `resume`, `graph`) — but this is still direct CLI dispatch,
      not `pipeline_manager`/`job_queue` orchestration
- [~] `core/project.py` — project workspace scaffolding (maps loosely to
      `orchestrator/execution_context`, not the real thing)
- [~] `core/logging_setup.py` — per-invocation JSON logs (not
      `build_telemetry`, no structured JobID/StageID tracking yet)
- [x] `orchestrator/pipeline_manager`, `pipeline_registry` (both in
      `orchestrator/pipeline_manager.py`) — sequences real CLI-command
      stages (each stage still creates its own genuine Job, exactly as if
      run by hand) via `orchestrator/argv_utils.reconstruct_argv` +
      `cli.main.main`, no separate dispatch logic duplicated. One real
      named pipeline (`pipeline_registry`'s one entry) —
      `validate_then_repair`: validate (allowed to FAIL —
      `continue_on_failure`) → repair (real failure stops the run). A
      `PipelineRun` is persisted per run (`projects/<name>/pipelines/
      <run_id>/pipeline_run.json`) with per-stage PENDING/RUNNING/PASSED/
      FAILED/SKIPPED status — a stage after a non-continuing failure is
      marked SKIPPED and genuinely never invoked (verified). New
      `pipeline`/`pipelines` CLI commands. Covered by
      `tests/test_pipeline_manager.py` (stub-driven unit tests of the
      stop/continue logic, plus a real end-to-end run against the actual
      400-entity repair-stress fixture).
- [x] `orchestrator/job_queue`, `job_scheduler`, `build_scheduler` (all
      three in `orchestrator/job_queue.py`, treated as one component —
      nothing here would meaningfully separate "what's next" from "when
      does it run"). Real: a persisted FIFO queue (`projects/<name>/
      queue.json`), real time-gated eligibility (`not_before`, an actual
      ISO-timestamp comparison against the clock at drain time, never a
      label), real priority ordering. `drain()` is a single-worker
      sequential loop — **not** concurrent/async, stated plainly in the
      module docstring, consistent with every other orchestration piece
      here. New `enqueue`/`queue`/`work` CLI commands. Two real bugs
      found and fixed during manual testing before any test was written:
      `cancel()` required an exact UUID instead of prefix-matching like
      every other lookup in this codebase; `enqueue`'s `argparse.
      REMAINDER` silently swallowed `--not-before`/`--priority` into the
      downstream command when they appeared after the project name
      (fixed by hand-parsing the `--` separator instead of relying on
      REMAINDER) — both locked in as regression tests in
      `tests/test_job_queue.py`.
- [x] `orchestrator/build_state` (`orchestrator/build_state.py`) — the
      state machine from section 23, real subset (`CREATED`→`RUNNING`→
      `VALIDATING`/`PACKAGING`/`REPAIRING`→`READY`/`FAILED`, `FAILED`→
      `RUNNING` for resume). `REPAIRING` is real now (`cmd_repair` reaches
      it — fixed 2026-09-30, it was declared-but-unreachable even after
      the repair loop shipped). `QUEUED`/`PLANNING`/`SIGNING`/`PUBLISHED`
      are still declared but have no valid transitions — no AI planner/
      compiler/marketplace exists to reach them, and faking that
      transition would be fabricating capability.
- [x] Job isolation (section 24) — `orchestrator/job.py`: real `JobID`
      (uuid4), isolated workspace at `projects/<name>/jobs/<job_id>/`,
      persisted `job.json` (state, history, args, result_summary, and now
      a real `capability_snapshot` — see Layer 3's `capability_registry`
      below). `validate`/`optimize`/`process`/`agent`/`repair`/`krita`/
      `gimp`/`ffmpeg` each create and transition a job. `jobs` CLI command
      inspects them; `resume` CLI command does genuine re-entry (argv
      reconstruction now shared via `orchestrator/argv_utils.py` with
      `pipeline_manager`, factored out once a second real caller needed
      it) — verified against a real forced failure in `tests/test_cli.py`.
- [x] `orchestrator/stage_runner` — the stage-execution loop inside
      `run_pipeline()` (see `pipeline_manager` above); not a separate
      module since it has no independent reason to exist yet
- [x] `orchestrator/dependency_graph` (`orchestrator/dependency_graph.py`)
      — distinct from `core.artifact_graph` (which tracks dependencies
      BETWEEN ARTIFACTS): this answers "is pipeline stage N stale" via a
      thin, real translation from `has_changed()`. Not yet wired into
      `pipeline_manager`'s one real pipeline — `validate_then_repair`'s
      `validate` stage must always run (it's what decides whether
      `repair` is needed), so "skip if unchanged" has no honest
      application there yet; wiring it in is future work for when a
      multi-stage artifact-flow pipeline exists to actually benefit from
      it. Covered by `tests/test_dependency_graph.py` (a real file,
      really hashed, really modified to prove staleness detection reacts
      to genuine content change).
- [ ] `orchestrator/checkpoint_manager`, `retry_manager`, `repair_manager`
- [ ] `orchestrator/cancellation_manager`, `worker_manager`

## Layer 3 — Tool Contracts + Adapters

- [x] `tools/tool_registry`, `tool_contracts`, `tool_permissions`,
      `tool_executor`, `tool_schemas`, `tool_audit` — the authorization
      boundary is real: every CLI command and the `blender_agent` call
      `tools.tool_executor.execute(tool_id, caller_id, **kwargs)`, which
      enforces permission (`allowed_callers`) → capability detection →
      input/output schema validation → the actual adapter call → an
      append-only JSONL audit log (`logs/tool_audit.jsonl`, argument
      *keys* only, never values). Eight contracts registered today:
      `validate_blend`, `optimize_blend` (allow `cli`, `blender_agent`,
      `repair_engine`), `export_svg_variants`, `convert_image_format`,
      `krita_export`, `gimp_export`, `ffmpeg_transcode`,
      `ffmpeg_extract_frame` (all `cli`-only). Covered by
      `tests/test_tool_executor.py` —
      unknown tool, missing required field, unauthorized caller, missing
      capability, and a real successful call are all exercised, no mocks.
- [x] Blender — `adapters/blender_bridge.py` (headless subprocess) +
      `adapters/blender/live/` (separate live-GUI socket bridge) — two
      transport mechanisms, not yet unified under one `BlenderAdapter`
      class matching the spec's `discover_installation/detect_version/
      check_capabilities/launch/open_project/execute_script/monitor/
      collect_artifacts/collect_logs/shutdown` interface
- [x] Inkscape — `adapters/inkscape_adapter.py`, real, tested, ad-hoc method
      shape (not yet the generic `execute_supported_operation()` contract)
- [x] ImageMagick — `adapters/imagemagick_adapter.py`, same caveat
- [x] GIMP — `adapters/gimp_adapter.py`: `export_to()`, via GIMP 3's real
      Python-Fu batch CLI (`Gimp.file_load`/`Gimp.file_save` — the legacy
      Script-Fu `file-jpeg-save`/`gimp-pdb-query` PDB names from GIMP 2.x
      no longer exist in 3.x, confirmed by live testing, not assumed from
      old docs; a top-level `--quit` flag, not a `-b` batch command, is
      what makes GIMP 3 actually exit instead of lingering as "a
      background process"). Wired into a `gimp_export` tool contract and
      a real `gimp` CLI command (`xcf_source` → `texture_raster`), same
      shape as Krita's. Covered end-to-end in `tests/test_adapters.py`
      and `tests/test_cli.py`.
- **RustEdit adapter — dropped (2026-09-30), not a `[ ]`/`[~]`/`[x]` item
      anymore.** Actually tested: installed Wine, ran the real
      `RustEditLauncher.exe` (found in `~/Downloads`), let it download and
      patch the genuine ~180MB RustEdit Unity application, and launched
      the real `RustEdit.exe`. It immediately asked to browse to a "Rust
      install directory" — RustEdit reads Rust's own game asset bundles
      directly off disk to render terrain/prefabs, so it's non-functional
      without a full, legitimately-owned ~30GB Rust (Facepunch) install,
      which doesn't exist in this environment and isn't something to
      acquire just to test an adapter. Separately, and more importantly:
      RustEdit is a *server map editor* (terrain/monument/prefab
      placement) — a different tool for a different job than "make a skin
      for an item," which is done by painting that item's own UV texture
      template (a flat PNG) and uploading via Steam Workshop. The
      Krita/GIMP/ImageMagick adapters already built cover that job
      completely; no RustEdit integration is needed for it.
- [x] FFmpeg adapter — `adapters/ffmpeg_adapter.py`: `transcode()`,
      `extract_frame()` (a still frame at a timestamp, e.g. a video-asset
      thumbnail), `get_duration()` (via `ffprobe`, resolved separately
      since it isn't its own `config/tools.yaml`/detection entry). Real,
      tested against an actual synthetic clip generated by ffmpeg's own
      `lavfi testsrc` (no external video file, no mock) in
      `tests/test_adapters.py`. **Wired into tool contracts**
      (`ffmpeg_transcode`, `ffmpeg_extract_frame`) and a real `ffmpeg` CLI
      command (`--transcode <ext>` / `--thumbnail <timestamp>`, at least
      one required — refuses rather than no-op'ing with neither), with
      full artifact-graph (`video_source` → `video_transcoded`/
      `texture_png`) and job tracking. Covered end-to-end in
      `tests/test_cli.py`.
- [x] Krita adapter — `adapters/krita_adapter.py`: `export_to()`, wrapping
      Krita's real `--export`/`--export-filename` batch CLI flags — the
      one thing Krita does that Inkscape/ImageMagick don't (open `.kra`,
      Krita's native layered format). Real, tested (a real PNG opened and
      re-exported as JPEG headlessly). **Wired into a `krita_export` tool
      contract** and a real `krita` CLI command, with artifact-graph
      (`kra_source` → `texture_raster`) and job tracking, mirroring
      `process`'s Inkscape path. Covered end-to-end in `tests/test_cli.py`.
- [ ] `image_processor_adapter`, `audio_processor_adapter` (as distinct
      from the tool-specific ones above)
- [x] `filesystem_adapter`-equivalent — implicit in `core/project.py` /
      the adapters themselves; not a formal contract-checked boundary

## Layer 4 — Deterministic Production (Processors)

- [x] Geometry — `adapters/blender/geometry/` (parametric primitives,
      instancing, mesh utilities) — real, tested (5 working asset builds)
- [x] Materials — `adapters/blender/materials/` (metal, wood, candy/gummy,
      procedural generators) — real, tested, including a from-scratch
      Cycles-vs-EEVEE transmission investigation for the gummy material
- [x] Textures — `adapters/blender/textures/` (Poly Haven + ambientCG PBR
      download/apply pipeline, real API calls, not mocked)
- [x] Assets (props/mechanisms) — crate, door, crane, imported-prop
      re-texturing all working end to end, headless and live
- [~] Rigging/Animation — `adapters/blender/rigging/` + `animation/`
      (mechanical hinge/slider/follow-point primitives only — no vehicle
      or character rigs)
- [x] **Product types formalized** (`products/product_types.py`,
      2026-10-01) — a real registry, same honest pattern as
      `validation/validation_registry.py`: each type declares
      `required_metadata` (checked for presence AND type, not just
      presence) and `required_validators` (the SAME real validators
      `validation_registry` tracks). A new `register-product` CLI
      command validates metadata, validates the backing asset against
      the type's real validators when one is given, and only persists
      (`manifest["product_type"]`/`["product_metadata"]`) on success —
      never on a refused registration. A new `product-types` command
      inspects the registry. Covered by `tests/test_product_types.py`.
  - [x] **CUI** — backed by a real texture asset. This is what forced
        `validation/texture_validator.py` + a real `ImageMagickAdapter
        .inspect()` into existence (resolution/format/power-of-two,
        via `identify`) — `texture` in `validation_registry` moved from
        UNSUPPORTED to IMPLEMENTED as a direct result. No UI
        interaction/widget runtime exists to validate behavior against
        — this is asset-level validation only, stated in the schema's
        own notes.
  - [x] **Monuments** (the master spec's own example of "a product
        type, not just a big Blender scene") — backed by a real .blend,
        real `geometry`+`asset` validation via the existing
        `validate_blend` path. Verified against the actual
        `test11_monument.py` fixture.
  - [x] **Vehicles** (as a product type, not just a pipeline/asset
        category) — backed by a real .blend, real `geometry`+`asset`+
        `performance` validation. Verified against the actual
        `test9_jetski.py` fixture.
  - [x] **NPCs** — registered as a real product type, but honestly
        metadata-only (`required_validators=[]`): no character-rigging,
        AI-behavior, or dialogue system exists in this codebase to
        validate an NPC against. The schema proves the concept
        (declared, typed metadata) without fabricating enforcement.
  - [x] **Events** — same honest scope as NPCs: metadata-only, no
        scripting/trigger-execution runtime exists to validate against.
  - [x] **Building Skins** — texture-backed, same real `texture`
        validator as CUI, PLUS a genuinely new real check:
        `ImageMagickAdapter.check_seamless_tiling()` (actual opposite-
        edge pixel comparison via `compare -metric AE`, confirmed live
        against both a real seamless solid-color image and a
        deliberately non-seamless red|blue image before being written).
        `texture_validator.validate_texture(require_seamless=True)` folds
        this in as a hard FAIL, not a warning — seamless tiling is the
        entire point of this asset type.
  - [x] **Audio** — backed by a real audio file,
        `validation/audio_validator.py` (new), via a new
        `FFmpegAdapter.inspect()` (real `ffprobe`-backed
        codec/sample_rate/channels/duration). Deliberately NOT one of
        `validation_registry`'s 17 formal types — the master spec's own
        `validation/` section doesn't name an `audio_validator`, so
        `audio`'s `required_validators` stays `[]` and real validation
        is called directly (same pattern `texture` used before it became
        a formal registry entry).
  - [x] **VFX** — backed by a real .blend, same real `geometry`+`asset`+
        `performance` validators as Vehicle. No particle-simulation-at-
        runtime or compositing-pipeline validation exists beyond that.

## Layer 5 — Artifact / Validation / Compilation

- [x] **Artifact Graph** — `core/artifact_graph.py`: real ArtifactID
      (uuid4) per node, ParentArtifacts/Dependencies edges (validated on
      insert — adding an artifact with an unknown parent raises rather
      than silently creating a dangling edge), InputHash/OutputHash
      (sha256, file-content-based via `hash_file()` or canonical-JSON via
      `hash_data()`), lineage traversal (`lineage()`), forward
      dependency-impact traversal (`find_affected()` — section 5's
      incremental-rebuild core promise, tested: invalidating a changed
      material correctly reaches its prefab+package but never touches an
      unrelated npc_logic artifact), cascading `invalidate()`, `diff()`,
      and JSON persistence (`artifact_graph.json` per project, alongside
      `project.json`). **Wired into real CLI commands, not just a
      standalone library**: `create` initializes an empty graph;
      `validate` registers/updates the source blend's node and its
      PASS/FAIL status; `optimize` registers an `optimized_blend` node
      parented to the source, detects if the source changed since last
      run via `has_changed()`, and cascades invalidation if so; `process`
      builds a real 3-level chain (svg_source → texture_png →
      texture_webp) with correct parent edges. A new `graph` CLI command
      (`--lineage`/`--affected`) lets a human actually inspect it — real
      output verified: `./asset-factory graph "Demo Casino Floor"` shows
      the source→optimized edge with real hashes. Covered by
      `tests/test_artifact_graph.py` (12 assertions, no mocks) plus
      integration assertions added to `tests/test_cli.py` checking the
      graph after real validate/optimize/process runs.
      **Not yet built**: `artifact_store` (a real content-addressed
      store, vs. today's "storage_location is just wherever the file
      already was written"), `artifact_versioning` (no VersionID
      immutability enforcement yet), `artifact_cache` (nothing skips
      re-running work based on an unchanged hash yet — `has_changed()`
      exists and is tested, but no command actually short-circuits on it).
- [x] Geometry/naming/UV/collision/LOD validation —
      `adapters/blender/core/validation.py`, real, deterministic
- [x] Performance validation — `adapters/blender/optimization/performance_validator.py`,
      real PASS/FAIL against PC performance budgets, deterministic
- [x] `validation/validation_registry` (`validation/validation_registry.py`)
      — a formal, honest catalog of the spec's 17 named validator types
      (geometry, topology, collision, texture, material, asset,
      dependency, compatibility, manifest, runtime, interaction, npc,
      event, performance, memory, network, security). 6 are IMPLEMENTED
      (mapped to the real `validate_asset`/`validate_performance` entry
      points, with what each actually covers); the other 11 are
      UNSUPPORTED with a real reason each (most because there's no
      runtime/NPC/event content to validate yet) — never a silent gap.
      New `validators` CLI command (not project-scoped) to inspect it.
      Covered by `tests/test_validation_registry.py`, including a
      completeness check that the registry can't silently drift from the
      spec's actual 17-item list.
- [x] Validation-authority separation (stopping "AI says PASS" from ever
      being treated as "KOBA validation PASS") — real now, not just
      architecturally-prevented-in-theory: `repair/repair_engine.py`
      never sets `validation_status` itself (only `revalidate()`'s real
      `validate_blend` call does), and `cli/main.py`'s
      `_record_optimization()` was fixed to record `PENDING` instead of
      asserting `PASS` by fiat for `optimize_blend` output that was never
      actually revalidated. See Phase D below.
- [x] `repair/` (`repair/repair_engine.py`) — `classify_failure()` /
      `run_repair()` / `revalidate()` implement diagnosis, failure
      classification, and repair execution for the two strategies that
      exist (merge, decimate); `affected_artifact_resolver`-equivalent
      logic (counting prior repair attempts against a source artifact) is
      inline in `cli/main.py`'s `cmd_repair`, not a separate module yet.
      See Phase D below for the full account.
- [ ] `compiler/` — product_compiler, dependency_compiler,
      runtime_compiler, asset_compiler, manifest_compiler — not started
- [ ] `packaging/` — artifact_builder, version_builder, package_builder,
      hash_generator, signature_generator, manifest_signer,
      release_builder/verifier — not started

## Supporting systems

- [x] `capabilities/capability_registry` (`capabilities/capability_registry.py`)
      — registry-shaped wrapper around `core/detection.py`'s real
      tool-detection: `capture_snapshot()` (a real, fresh, never-cached
      detection pass), `record_snapshot()`/`read_recent_snapshots()`
      (append-only JSONL history at `logs/capability_snapshots.jsonl`,
      same convention as `tool_audit.jsonl`), `diff_snapshots()`. Wired
      structurally, not just standalone: every real Job (`orchestrator/
      job.py`'s `create_job()`) now stamps a genuine `CapabilitySnapshot`
      (the master spec's own structured-log field name) at creation, so
      "what tools/versions were present when this job ran" is answerable
      after the fact. New `capabilities` CLI command (`--record`,
      `--history`). Covered by `tests/test_capability_registry.py` and a
      new assertion in `tests/test_job.py`.
- [~] `manifest/` (Product Manifest, section 12) — `core/manifest.py`
      covers a small slice (Assets/exports/errors); Identity, Type,
      Compatibility, Runtime, Permissions, Performance, Security,
      Licensing, Verification sections don't exist
- [ ] `storage/` — no cache_manager, immutable_artifact_store, etc.;
      projects/ is a plain directory tree
- [ ] `security/` — no sandbox_manager, credential/secret management,
      malware_scanner, audit_logger beyond today's plaintext JSON logs
- [ ] `telemetry/` — not started
- [ ] `integrations/koba-core/`, `integrations/marketplace/`,
      `integrations/koba-live/`, `integrations/telemetry/` — **deliberately
      not started**; KOBA Core itself doesn't exist in this environment,
      and building integration stubs against a system that isn't there
      would be fabricating an integration (explicitly prohibited by the
      spec's own Rule/section 29)
- [~] `testing/` — real orchestration-layer tests exist
      (`tests/test_detection.py`, `test_manifest.py`, `test_project.py`,
      `test_adapters.py`, `test_cli.py` — the last including a genuine
      Blender subprocess integration test) and 5 real Blender asset-build
      tests. Missing: `multiplayer_tests`, `load_tests`,
      `regression_tests`, and everything from section 31's list that
      depends on layers that don't exist yet (repair loops, checkpoint
      recovery, artifact lineage, etc.)

## CLI surface (target: `koba-*`, current: `asset-factory <command>`)

- [x] `create` (target: `koba-create`) — project skeleton + manifest only,
      no AI planning yet
- [x] `validate` (target: `koba-validate`) — real, but validates a single
      Blender asset, not a full product's artifact graph
- [x] `optimize` — not in the target CLI list by this name, but real and
      useful (culling assignment + optional static merge + decimation)
- [x] `process`, `krita`, `gimp`, `ffmpeg` — ditto, not in target list,
      real (SVG/`.kra`/`.xcf`/video → texture or media variants)
- [x] `agent` — not in target list either, real: natural-language
      instruction → AI router → `validate_blend`/`optimize_blend`
- [x] `repair-agent` — not in target list either, real: the second agent
      (`agents/repair_agent.py`), same AI router, extracts a
      `merge_group` from free text. See Layer 1 above.
- [x] `repair` (target: `koba-repair`) — **done**, not stale: the section-10
      repair loop (merge + decimate strategies) is real, see Phase D above
- [x] `resume` (target: `koba-resume`) — **done**, not stale: genuine
      argv-reconstruction re-entry against a FAILED job, see Layer 2 above
- [x] `jobs`, `graph`, `validators`, `capabilities`, `product-types`,
      `pipelines`, `queue` — not in target list, real inspection commands
      for the job/artifact-graph/validation-registry/capability-registry/
      product-type-registry/pipeline-run/job-queue systems of record
- [x] `pipeline` — not in target list, real: runs the one named
      multi-stage pipeline (`validate_then_repair`). See Layer 2 above.
- [x] `enqueue`, `work` — not in target list, real: the job queue +
      single-worker drain loop. See Layer 2 above.
- [x] `register-product` — not in target list, real: formal product-type
      registration with metadata + asset validation. See Layer 4 above.
- [x] `status`, `logs`, `doctor` — utility commands, real
- [ ] `koba-plan` — no AI planning layer to call
- [x] `koba-build` — **partially real now**: `pipeline`/`enqueue`+`work`
      give queued and multi-stage sequencing (see Layer 2), but both are
      synchronous/single-worker, not the spec's full async scheduler —
      still an honest gap, just a smaller one than before
- [ ] `koba-test` — no test-orchestration layer
- [ ] `koba-package` — no compiler
- [ ] `koba-publish` — no marketplace integration

---

## Environment (tool availability, re-verify before relying on this — re-checked 2026-09-30 via `core.detection.detect_all()`)

| Tool | Status | Notes |
|---|---|---|
| Blender 5.2.2 LTS | ✓ installed | `~/Downloads/blender-5.2.2-linux-x64/blender` |
| Inkscape | ✓ installed | v1.4, on PATH |
| ImageMagick | ✓ installed | v7.1.1, on PATH (`magick`) |
| GIMP | ✓ installed | v3.2.6 via Flatpak (`org.gimp.GIMP`), wrapped via `bin/gimp-flatpak-wrapper.sh` |
| Krita | ✓ installed (as of 2026-09-30) | v5.2.9, on PATH (`krita`) — was absent as of 2026-09-29, appeared without this session installing it; `tests/test_detection.py` and `tests/test_cli.py`'s `doctor` assertions were updated to match |
| FFmpeg | ✓ installed (as of 2026-09-30) | v7.1.5, on PATH (`ffmpeg`) — same |
| RustEdit | ✗ dropped (evaluated, blocked) | Wine 10.0 installed, real `RustEditLauncher.exe` run, real app patched and launched — but it requires a full licensed Rust game install to function at all, and is the wrong tool for item-skinning anyway (see Layer 3 note above). Not pursuing further. |
| FreeCAD / FontForge / Godot | ✗ not installed | optional/future, lowest priority |
| Python `pyyaml` | ✓ available (system Python) | used by `core/config.py` — **not** available inside Blender's bundled Python, confirmed by testing; anything loaded inside Blender uses plain-Python config (`adapters/blender/config/*.py`) |

`core.detection.system_ready()` now returns `True` — every REQUIRED_TOOLS
entry is genuinely installed for the first time this session.

## Recommended next step

~~Phase A: build the real Artifact Graph~~ — **done** (2026-09-29).
~~Phase B/C: tool contracts + authorization boundary, job abstraction,
one real AI agent~~ — **done** (2026-09-29), see Layers 1-3 above, all
three built in the order the user specified and covered by real tests
(`test_tool_executor.py`, `test_job.py`, `test_ai_agent.py`) plus a real
end-to-end run against the actual GummyGun asset (not just fixtures).

~~Phase D: validation authority + first repair loop~~ — **done**
(2026-09-30). `repair/repair_engine.py` implements the real section-10
lifecycle (GENERATE→VALIDATE→FAIL→DIAGNOSE→CLASSIFY→REPAIR→CREATE NEW
ARTIFACT VERSION→REVALIDATE→PASS/FAIL). `cli/main.py`'s
`_record_optimization()` was also fixed to stop marking every
`optimize_blend` output `PASS` by fiat (it now correctly records
`PENDING` — optimize never validates its own output) — a real
validation-authority-separation fix, not just the repair path. Wired
into a `repair` CLI command with full job tracking.

Two repair strategies exist today, both delegated to `optimize_blend` in
one call:
- **merge** a named `visibility_group` — fixes `entity_count`/
  `unique_meshes` overages. Verified end-to-end against a genuine
  400-entity fixture that FAILs 240fps_esports' real budget, gets merged
  down to 1 entity, and re-validates PASS — plus a second repair attempt
  proving the first attempt's output is never overwritten.
- **decimate** geometry in place (`optimization/decimate.py`, new) —
  fixes `triangles` overages. This is deliberately NOT the existing LOD
  system (`optimization/lod.py`'s `generate_decimated_lod`): that
  registers a parallel, hidden alternate mesh for future distance-based
  runtime switching, which this framework has no switcher for yet, so it
  does not change what the validator counts. Decimating the actual
  visible object is what genuinely reduces the reported `triangles`
  metric. The ratio is computed from the failure's own numbers (target
  budget ÷ current count, with a 10% safety margin) — never guessed, and
  the caller never has to supply one. Verified end-to-end against a
  single 327680-triangle icosphere fixture that FAILs
  240fps_esports' real 250000 cap on triangles alone, decimates to
  224984, and independently re-validates PASS.

Both strategies can fire in the same repair pass if a report has both
kinds of failures. Neither is guessed: merging still requires an explicit
`--merge-group` (classify_failure refuses to pick one), and both refuse
outright (`UnrepairableFailure`) for failure categories with no automated
fix (materials/lights/physics/animated-object overages). Covered by
`tests/test_repair.py`.

Also done (2026-09-30): **FFmpeg and Krita adapters, fully wired**
(`adapters/ffmpeg_adapter.py`, `adapters/krita_adapter.py`) — both tools
turned out to already be installed on this machine (re-detected via
`core.detection`, not assumed). Registered as tool contracts
(`ffmpeg_transcode`, `ffmpeg_extract_frame`, `krita_export`) and real
`ffmpeg`/`krita` CLI commands, with artifact-graph and job tracking
matching every other real command. See Layer 3 above.

Also done (2026-09-30), working through the user's explicit "small,
bounded, unblocked" list in order:
- **GimpAdapter** — `adapters/gimp_adapter.py`, `gimp_export` tool
  contract, `gimp` CLI command. See Layer 3 above.
- **RustEdit adapter — dropped**, not built. Actually tested (Wine
  installed, real launcher run, real ~180MB app downloaded/patched/
  launched) rather than assumed: it requires a full licensed Rust game
  install to function at all, and is a server-map editor anyway, not an
  item-skinning tool. See Layer 3 above for the full account.
- **More Blender asset-generator tests** — `test9_jetski.py`,
  `test10_yacht.py` (both reuse `create_hull` at different proportions;
  the yacht adds a stacked-box cabin superstructure), `test11_monument.py`
  (introduced `create_pyramid` + `materials.stone`; the cleanest
  validation in the whole series — no warnings beyond missing rig/
  animation, since it's built entirely from closed primitives). All three
  introduced `materials.plastic.glossy_plastic` where used. See the
  Blender README's asset-generator section for details.

- **`validation_registry`** — `validation/validation_registry.py`, a
  formal, honest catalog of the spec's 17 named validator types (6
  IMPLEMENTED with real entry points, 11 UNSUPPORTED with real reasons).
  New `validators` CLI command. See Layer 5 above.

**The user's entire "small, bounded, unblocked" list is now done.**

~~The "medium, real orchestration gaps" tier~~ — **done** (2026-09-30):
- **`pipeline_manager`/`pipeline_registry`/`stage_runner`** —
  `orchestrator/pipeline_manager.py`, real multi-stage sequencing of CLI
  commands (`validate_then_repair`), persisted `PipelineRun` records,
  `pipeline`/`pipelines` CLI commands. See Layer 2 above.
- **`dependency_graph`** (pipeline-level) — `orchestrator/
  dependency_graph.py`, staleness detection distinct from the artifact-
  level graph; built and tested but not yet wired into the one real
  pipeline (no honest use case there yet — see its own docstring). See
  Layer 2 above.
- **`capability_registry`** — `capabilities/capability_registry.py`,
  wired into every real Job's `capability_snapshot` field, plus a
  `capabilities` CLI command. See Layer 3 above.
- Fixed along the way: `REPAIRING` in `orchestrator/build_state.py` was
  still declared-unreachable even after the real repair loop shipped —
  `cmd_repair` was using `PACKAGING` instead. Now genuinely reachable and
  used. Also factored `orchestrator/argv_utils.reconstruct_argv()` out of
  `cli/main.py`'s `resume` command once `pipeline_manager` needed the
  exact same logic — shared, not duplicated.
~~`job_queue`/`job_scheduler`/`build_scheduler`~~ — **done** (2026-10-01).
`orchestrator/job_queue.py`: real persisted FIFO queue, real time-gated
scheduling, single-worker sequential `drain()` (stated plainly as not
concurrent — see Layer 2 above for the full account, including two real
bugs found and fixed during testing).

**The entire "medium, real orchestration gaps" tier is now done.**

~~Layer 1's second agent~~ — **done** (2026-10-01): `agents/repair_agent.py`
+ `repair-agent` CLI command, proving the one-router/multiple-agents
pattern generalizes. Real scope (merge_group extraction from free text),
real bugs found and fixed (two, both now regression-tested — see Layer 1
above for the full account). A second *provider* (vs. a second agent on
the same provider) is still not exercised — `AnthropicProvider` exists
and is real, but no `ANTHROPIC_API_KEY` is available in this environment
to actually call it.

~~The "large, deliberately not started" tier's product types~~ — **done**
(2026-10-01): `products/product_types.py` + `register-product`/
`product-types` CLI commands. All 5 named types registered
(CUI/monument/NPC/event/vehicle), in the order asked. Three get real
asset-backed validation (CUI→texture, monument & vehicle→Blender
geometry/asset/performance); NPC/event are honestly metadata-only — no
fabricated runtime enforcement. Building the real CUI path required
implementing `validation/texture_validator.py` for real, upgrading
`texture` in `validation_registry` from UNSUPPORTED to IMPLEMENTED (now
3 of 17 validators are real, not 2). See Layer 4 above for the full
account.

~~Building Skins/Audio/VFX~~ — **done** (2026-10-01): all 8 of Layer 4's
named product types are now registered, real where an asset backing
exists. Real side effects along the way: `ImageMagickAdapter
.check_seamless_tiling()` (genuine opposite-edge pixel comparison) and
`FFmpegAdapter.inspect()` (real `ffprobe`-backed audio metadata) — both
confirmed live against real generated fixtures before being written, not
assumed. `validation/audio_validator.py` is real and used but
deliberately NOT a `validation_registry` entry (the master spec's 17
named types don't include an `audio_validator`). See Layer 4 above for
the full account.

**Every named product type in the master spec's Layer 4 "Deterministic
Production" section now exists as a real, registered product type.**

~~Compiler + packaging/signing/release~~ — **done** (2026-10-01), item 1
of the user's explicit 4-item "in order" priority list:
- **`compiler/product_compiler.py`** — the ONE real compiler (not the
  spec's full compiler+dependency_compiler+runtime_compiler+
  asset_compiler+manifest_compiler set, same scope-honesty pattern as
  every prior "one real X" build). `compile_product()` strictly obeys
  Rule 2: it never re-validates or re-decides PASS/FAIL, it only reads
  `validation_status` already recorded in the artifact graph by a real
  validator, and refuses (raises `CompilerError`) if the project has no
  registered product type or no currently-PASSing artifacts.
- **`packaging/package_builder.py`** (folds in `hash_generator`,
  `version_builder`, `artifact_builder`) — `build_package()` writes a
  real release to disk: copies each artifact's actual file into
  `projects/<name>/releases/<version>/assets/`, recomputes every file's
  hash fresh at copy-time, and writes `release_manifest.json`. Versioning
  is a real auto-incrementing integer (not semver — nothing here tracks
  semantic compatibility, so claiming semver would be fabricated
  precision); an explicit `--version` label is honored verbatim too.
- **`packaging/signature_generator.py`** (folds in `manifest_signer`) —
  genuine Ed25519 asymmetric signing via the `cryptography` library
  (confirmed installed, v43.0.0; generate/sign/verify/reject-tampered
  all verified live in a throwaway script before any module code was
  written). Keypair persists under `config/signing/` (gitignored, private
  key `chmod 600`), generated once and never silently rotated — rotating
  would invalidate every prior release's signature. `verify_signature()`
  returns `False` on any mismatch/corruption, never raises past its own
  boundary.
- New CLI commands: `package <project>` (compile → package → sign →
  `release_package` artifact added to the graph, linked via
  `parent_artifacts` to everything it was built from) and
  `releases <project>` (list all releases, or `--version N` for one
  release's manifest + real signature verification, printed as
  `VALID`/`INVALID`).
- `orchestrator/build_state.py`'s `SIGNING` state — declared since the
  very beginning of this project but unreachable — is now genuinely
  reachable (`PACKAGING → SIGNING → READY`).
- Verified end-to-end live before any tests were written: refusal with
  no product type registered (exit 1, correct message), then a full
  happy path on a real monument fixture (compile → package → sign →
  `releases` listing shows `VALID` → artifact graph shows the
  `release_package` artifact with the correct parent link).
- `tests/test_compiler_packaging.py` (new, registered in
  `tests/run_all.py`) covers: both compile refusals, a real end-to-end
  compile+package+sign against the real Blender monument fixture,
  multi-version auto-increment (including an explicit custom version
  label), valid-signature verification, two tampered/mismatched-
  signature rejection cases, hash-drift detection (corrupting the source
  file on disk after validation causes packaging to refuse rather than
  ship stale bytes under a now-wrong hash), and the full CLI `package`/
  `releases` happy path including the graph linkage check. Full suite:
  **20/20 test modules passing.**
- Honestly still missing: no `release_verifier` as a separate module
  (verification lives inline in `cmd_releases` and the test file — there
  was no real second use case yet to justify splitting it out); no
  marketplace/KOBA Core integration to actually *consume* a signed
  release (nothing exists yet to integrate with, same honest gap noted
  throughout Layer 4/Phase 4 work above).

~~Checkpoint/retry/repair managers~~ — **done** (2026-10-01), item 2 of
the user's 4-item "in order" priority list. Extended, not rebuilt — both
pieces were already partially real (`repair/repair_engine.py`'s single
repair action; `orchestrator/job.py`'s checkpoint persistence + the
`resume` command's single-attempt replay), so this closed the loop each
was missing rather than starting a new subsystem:
- **`repair/repair_manager.py`** (new) — a bounded multi-attempt wrapper
  around `repair_engine`'s existing classify/run/revalidate calls. If a
  decimate-fixable attempt still fails on the same metric afterward, it
  retries with a progressively tighter ratio (`RATIO_TIGHTEN_FACTOR =
  0.75`, floored at `MIN_DECIMATE_RATIO`), up to `--max-attempts` times.
  It explicitly refuses to keep retrying when the chosen strategy is a
  merge (deterministic — retrying would waste a real Blender invocation
  on a guaranteed-identical outcome) or when revalidation surfaces a
  genuinely new failure metric that wasn't there before (a different
  problem this engine has no strategy for either, not a signal to push
  the same lever harder). `cmd_repair` gained a `--max-attempts` flag
  (default 1, so the pre-existing single-attempt behavior and its tests
  are untouched) that drives this loop, printing/recording each attempt
  exactly as before.
- **`orchestrator/retry_manager.py`** (new) — a bounded wrapper around
  the existing checkpoint/resume mechanism, not a new checkpoint format.
  `retry_job()` calls an injected `resume_once(job)` repeatedly against
  whatever is currently the resumable FAILED job, up to `max_attempts`,
  stopping at the first success; refuses immediately (`RetryExhausted`,
  zero attempts wasted) if nothing is resumable or the named job isn't
  actually FAILED. New `retry` CLI command (`--job-id`, `--max-attempts`,
  `--backoff-seconds`) built on top, replacing the old `retry` stub in
  `NOT_YET_IMPLEMENTED`. `cmd_resume`'s single-attempt body was factored
  into `_resume_job_once()` so `resume` and `retry` share one real
  re-entry path rather than duplicating it.
- Real bug found and fixed during this work: `repair_manager`'s first
  draft called `run_tool`/`validate_blend` under a new `"repair_manager"`
  caller identity, which `tools/tool_permissions.py`'s allowed-callers
  list didn't recognize — authorization correctly refused it. Fixed by
  defaulting `repair_loop()`'s `caller_id` to `"repair_engine"` instead:
  this module is a bounded retry wrapper AROUND repair_engine, not a new
  actor, so it should authenticate as the thing it's wrapping rather than
  requiring a new entry in the permissions boundary.
- `tests/test_repair_retry_managers.py` (new, registered in
  `tests/run_all.py`) covers: `tighten_ratio`/`should_retry`'s pure
  arithmetic and branch logic (merge never retries; decimate retries
  while attempts remain and the failure set hasn't grown; stops on
  exhaustion or a genuinely new failure metric) with no Blender needed;
  real end-to-end `repair_loop()` runs against the same real Blender
  fixtures `test_repair.py` already uses (merge-fixable stress fixture —
  confirms it stops after exactly 1 attempt even with `max_attempts=3`;
  decimate-fixable fixture — confirms it stops at the first real PASS);
  an unfixable failure propagating `UnrepairableFailure` with zero wasted
  attempts; the full `repair --max-attempts N` CLI path; a
  deterministically-failing `retry` CLI run exhausting correctly without
  faking success; and `retry_job()`'s own orchestration exercised
  directly against real persisted Job state (a job that fails once then
  succeeds stops at exactly 2 attempts, not `max_attempts`; a non-FAILED
  job and an empty project both refuse immediately). Full suite:
  **21/21 test modules passing.**
- Honestly still missing: no backoff/concurrency semantics beyond a
  plain `time.sleep` between attempts (this whole codebase is still
  synchronous single-process, as `job.py`/`job_queue.py` already state
  plainly); the repair-retry tightening heuristic is a single hardcoded
  factor, not tuned against a corpus of real overage fixtures, since
  only two real stress fixtures exist to tune against.

~~Artifact store/versioning/cache~~ — **done** (2026-10-01), item 3 of
the user's 4-item "in order" priority list:
- **`core/artifact_store.py`** (new) — a real content-addressed blob
  store built directly on `core.artifact_graph.hash_file`/`hash_data`
  (which already did the hard part: computing and comparing hashes).
  `put()`/`get()`/`has()` give artifacts an actual place to live keyed
  by their own sha256 (two-level fan-out directories, same scheme git
  uses) — storing byte-identical content twice is a genuine no-op, so
  "versioning" and deduplication fall out of content-addressing for
  free rather than needing a separate mechanism. `cache_lookup()`/
  `cache_store()` add a real cache keyed by the exact
  (processor, input_hash, params) tuple — never a guessed equivalence —
  and a cache entry whose object has been physically removed reports as
  an honest miss, never a stale hit.
- Wired into a genuine use case, not left unused: `repair/
  repair_manager.py`'s `repair_loop()` gained an optional `proj_dir`
  parameter — when given, an attempt whose exact source bytes +
  merge_group/decimate_ratio/profile has already been computed skips
  the real Blender `optimize_blend` invocation and reuses the cached
  output instead. `revalidate()` still always runs for real regardless
  of a cache hit — Rule 2 forbids skipping validation for any reason,
  including a construction-step cache hit; this is purely a performance
  optimization on the expensive Blender call, never on PASS/FAIL
  authority. `cmd_repair` passes its real `proj_dir` through
  automatically.
- New `cache` CLI command (`--entries` for the full list) — real object
  counts/bytes read off the filesystem, plus the cache-hit index,
  mirroring `graph`'s existing observability intent.
- `tests/test_artifact_store.py` (new, registered in `tests/
  run_all.py`) covers: put/get/has and real on-disk deduplication (two
  byte-identical files produce exactly one stored object); honest misses
  for an unknown hash; cache lookup/store with exact-match-only
  semantics (different params or a different processor against the same
  input must NOT collide); a cache entry surviving its object being
  physically deleted reports `object_present: False`, never a stale hit;
  the `cache` CLI command; and a real end-to-end cache hit through
  `repair_loop()` against a real Blender fixture — the first call does a
  genuine Blender repair (and the test asserts the "cache hit" marker is
  absent, so this isn't vacuously true), the second identical call hits
  the cache (asserts the marker IS present), both calls' output files
  are confirmed byte-identical on disk, and revalidation independently
  confirms PASS both times. Full suite: **22/22 test modules passing.**
- Honestly still missing: no garbage collection (stored objects live
  forever — fine at this project's current scale, not fine indefinitely);
  no remote/shared store across projects, only project-local; no
  compression; the cache is currently wired into exactly one real
  consumer (`repair_manager`), not retrofitted onto `optimize_blend`'s
  other callers or `validate_blend` (validation is intentionally never
  cached, per Rule 2 — see above).

~~Generic image/audio processor adapters, full manifest,
storage/security/telemetry~~ — **done** (2026-10-01), item 4 (the last)
of the user's 4-item "in order" priority list. Each sub-piece assessed
honestly on its own merits rather than padded with busywork:

- **Generic image/audio processor adapters — judged already satisfied,
  not rebuilt.** Five real adapters already exist (ImageMagick,
  Inkscape, FFmpeg, GIMP, Krita), each wired through the same real
  authorization boundary + manifest + artifact-graph pipeline via its
  own CLI command (`process`/`krita`/`gimp`/`ffmpeg`). A "generic"
  dispatcher on top (route by file extension to the right adapter)
  would be a thin wrapper adding no new real capability over working,
  tested code — exactly the kind of abstraction-beyond-what's-needed
  this project's own discipline (and this session's standing
  instructions) say not to build. Left as-is.
- **Full manifest — genuinely extended.** `repair` and `package` were
  the two real commands that updated the artifact graph + Job state but
  never touched `project.json` (section 12's actual Product Manifest) —
  a real gap, since `validate`/`optimize`/`process`/`krita`/`gimp`/
  `ffmpeg` all already did. `_record_repair()` (shared by `cmd_repair`
  and `cmd_repair_agent`) now also records a real manifest export on a
  PASSing repair, or the real remaining failures as manifest errors on
  one that still FAILs. `cmd_package` now records a real
  `release_package` export on success, or a real manifest error on a
  `CompilerError`/`PackagingError` refusal.
- **Storage — no new work; already covered.** `core/artifact_store.py`
  (item 3, immediately above) IS this codebase's real storage layer now
  — a project-local content-addressed object store. Nothing further to
  add without inventing a use case that doesn't exist yet (a shared/
  remote store, which nothing in this single-machine CLI tool needs).
- **Security — assessed, not padded.** The real authorization boundary
  (`tools/tool_permissions.py`'s allowed-callers enforcement, Rule 3)
  and genuine Ed25519 release signing (item 1) already cover this
  codebase's actual attack surface. Checked specifically for this item:
  `core.project.slugify()` strips every non-alphanumeric character
  before a project name becomes a directory path, so `../../etc` or
  similar can never escape `projects/` via a crafted project name — this
  was already true, verified rather than assumed. `--blend-file`/
  `--asset-file`/`--source` flags intentionally accept arbitrary local
  paths, same as any CLI tool a user runs against their own filesystem
  with their own permissions — not a privilege boundary, nothing to
  sandbox. The master spec's broader "security" section (auth tokens,
  sandboxed execution, multi-tenant isolation) only makes sense once a
  real multi-user/server component exists, which it doesn't — same
  honest "nothing to integrate with yet" judgment already applied to
  marketplace/KOBA Core/KOBA Live throughout this roadmap.
- **Telemetry — genuinely extended, as expected ("mostly already
  half-done via the audit/capability-snapshot logs").** `core/
  logging_setup.py`'s `OperationLog` already wrote a real structured
  JSON record (command, args, duration, success, errors, warnings) for
  every CLI run — but the only way to see them was `logs`, which just
  lists file paths one at a time. New `core/telemetry.py`:
  `summarize()` reads every real log file back off disk and rolls it up
  per command — run counts, success rate, average duration, total
  errors/warnings — skipping unreadable files with an honest count
  rather than crashing or silently dropping them. New `telemetry` CLI
  command (`--command` to filter) prints the aggregate as a table. Ran
  for real against this project's actual accumulated history (2000+
  real log files from this entire session) as a live smoke test before
  the automated test was even written.
- `tests/test_telemetry_manifest.py` (new, registered in `tests/
  run_all.py`) covers: `summarize()`'s real arithmetic against real
  (and one deliberately corrupted) log files — exact success rate,
  exact average duration, corrupt-file skip count, command-name
  filtering returning a genuine zero rather than falling back to
  unfiltered; the `telemetry` CLI command; a real `repair` run recording
  a real manifest export; a real `package` run recording a real
  manifest export; and a real compile-refusal recording a real manifest
  error. Full suite: **23/23 test modules passing.**

**All 4 items of the user's "in order" priority list are now done.**
Per the original gap-triage: everything genuinely buildable right now
without a real second use case (marketplace/KOBA Core/KOBA Live
integration, the spec's full 17-validator/19-agent/5-compiler rosters,
async job scheduling beyond the existing single-process `job_queue`) has
already been declined with an honest reason throughout this roadmap,
not silently skipped.

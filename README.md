# KOBA Creator Engine

The real target architecture is defined in the master spec at
`~/Desktop/koba pc engine stuff/KOBA CREATOR ENGINE MASTER PRODUCTION
ARCHITECTURE_260928_235448.txt`: a five-layer AI-enabled production
orchestration platform for KOBA.GAMES — AI agents operating through
authorized tool contracts, adapters driving external creative tools, an
artifact graph tracking every production output with lineage/hashing,
deterministic validators as the authority (not AI), automated repair
loops, and a compiler that packages validated artifacts into signed
products for a marketplace/live/runtime ecosystem.

**What exists today is a real, working slice of Layers 3-4** (tool
adapters + deterministic asset-generation processors) — not yet Layers
1-2 (AI/orchestration) or the artifact-graph/repair/compiler parts of
Layer 5. See [ARCHITECTURE_ASSESSMENT.md](ARCHITECTURE_ASSESSMENT.md)
for the full gap analysis and [ROADMAP.md](ROADMAP.md) for the
component-by-component checklist — don't take this file's "Quick start"
below as the finished product; it's what the current adapter/CLI slice
can do, not the master spec's actual CLI surface (`koba-create`,
`koba-build`, etc., which don't exist yet).

This repo started as two separate toy projects (`blender_asset_system` +
`asset_factory`), merged 2026-09-27, then reframed 2026-09-29 once the
master spec clarified the real target.

## Layout

```
koba_creator_engine/
  asset-factory        CLI entry point — run ./asset-factory <command>
  cli/                 CLI implementation (argparse-based)
  core/                Orchestration: config loading, tool detection, logging, manifest, project management
  config/              tools.yaml (executable paths), defaults.yaml, export_profiles.yaml, projects.yaml
  projects/            Generated project workspaces live here (gitignored contents)
  logs/                One JSON log per CLI invocation
  tests/               Tests for the orchestration layer
  adapters/
    blender_bridge.py  Shells out to Blender's headless scripts for validate/optimize (system Python, no bpy)
    blender/           The Blender procedural-asset framework — see adapters/blender/README.md
                        (geometry, materials, rigging, animation, LOD, collision, export,
                        a live-GUI socket bridge, a real PBR texture pipeline, and a
                        PC performance/optimization architecture)
    (inkscape/, gimp/, krita/, imagemagick/, ffmpeg/ — not built yet)
```

See [ROADMAP.md](ROADMAP.md) for what's built vs. planned, and
[adapters/blender/README.md](adapters/blender/README.md) for the Blender
framework's own detailed docs (it's the most mature part today).

## Quick start

```bash
./asset-factory doctor          # check which tools are installed
./asset-factory create "My Asset Pack"
./asset-factory status
./asset-factory logs

# once a project has a .blend in its blender/ subdirectory:
./asset-factory validate "My Asset Pack" --profile 60fps_standard
./asset-factory optimize "My Asset Pack" --profile 60fps_standard

# SVG -> PNG variants (+ optional format conversion) via Inkscape/ImageMagick:
./asset-factory process "My Asset Pack" --svg logo.svg --sizes 128,256,512 --format webp
```

`doctor`, `create`, `status`, `logs`, `validate`, `optimize`, and
`process` are real. `validate`/`optimize` shell out to Blender headlessly
(via `adapters/blender_bridge.py`) to run the performance validator /
apply culling+merge optimizations against a project's Blender asset — see
`adapters/blender/README.md`'s "Performance & optimization architecture"
section for what that actually does. `process` drives
`adapters/inkscape_adapter.py` and `adapters/imagemagick_adapter.py`
directly (verified against this machine's real Inkscape 1.4 / ImageMagick
7.1.1 CLIs) — it's narrow (one SVG-to-texture path), not the master
spec's orchestrator/pipeline layer. Everything else
(`create-pack`, `render`, `animate`, `export`, `preview`, `package`,
`marketplace`, `batch`, `resume`, `retry`) is not implemented yet — they
say so explicitly and exit non-zero rather than pretending to work. See
ROADMAP.md for the build order.

Run the orchestration layer's own test suite (real tests, including a
genuine Blender subprocess integration test — no mocks):
```bash
python3 tests/run_all.py
```

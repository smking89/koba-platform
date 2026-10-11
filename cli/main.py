"""Asset Factory CLI. Phase 1 fully implements: doctor, create, status, logs.
Every other command from the spec is registered (so --help is complete and
honest about the planned surface) but exits with a clear "not implemented
yet" message and non-zero status rather than silently no-op'ing — see
project brief section 26, "do not fake capabilities"."""
import argparse
import json
import os
import shutil
import sys

from core.detection import detect_all, system_ready, REQUIRED_TOOLS, OPTIONAL_TOOLS
from core.logging_setup import OperationLog, list_recent_logs
from core.telemetry import summarize as telemetry_summarize
from core.project import create_project, project_exists, list_projects, get_project_status, \
    project_dir_for, find_blend_files
from core.manifest import load_manifest, save_manifest, add_warning, add_error, add_export, add_asset, add_tool_used, set_product_type
from core.artifact_graph import (
    load_graph, save_graph, get_or_create_source_artifact, find_by_path, hash_file,
    PASS as ART_PASS, FAIL as ART_FAIL, PENDING as ART_PENDING,
)
from adapters.blender_bridge import BlenderBridgeError
from adapters.inkscape_adapter import InkscapeAdapter, InkscapeAdapterError
from adapters.imagemagick_adapter import ImageMagickAdapter, ImageMagickAdapterError
from adapters.krita_adapter import KritaAdapter, KritaAdapterError
from adapters.ffmpeg_adapter import FFmpegAdapter, FFmpegAdapterError
from adapters.gimp_adapter import GimpAdapter, GimpAdapterError
from tools import registered_tools
from tools.tool_executor import execute as run_tool, ToolNotFound, UnsupportedCapability
from tools.tool_permissions import PermissionDenied
from tools.tool_schemas import SchemaValidationError
from orchestrator.job import create_job, transition as job_transition, list_jobs, get_job, find_resumable
from orchestrator.build_state import RUNNING, VALIDATING, PACKAGING, REPAIRING, SIGNING, READY, FAILED, InvalidTransition
from orchestrator.argv_utils import reconstruct_argv
from orchestrator.pipeline_manager import (
    run_pipeline, get_pipeline_run, list_pipeline_runs,
    build_validate_then_repair_stages, VALIDATE_THEN_REPAIR, PASSED as PIPELINE_PASSED,
)
from orchestrator.job_queue import (
    enqueue as queue_enqueue, list_queue, cancel as cancel_queue_item, drain as drain_queue,
    FAILED as QUEUE_FAILED,
)
from agents.blender_agent import BlenderAgent, BlenderAgentError
from agents.repair_agent import RepairAgent, RepairAgentError
from repair.repair_engine import classify_failure, run_repair, revalidate, UnrepairableFailure
from repair.repair_manager import repair_loop
from orchestrator.retry_manager import retry_job, RetryExhausted
from core import artifact_store
from validation.validation_registry import (
    get as get_validator, list_validators, UnknownValidator, IMPLEMENTED as VALIDATOR_IMPLEMENTED,
)
from capabilities.capability_registry import capture_snapshot, record_snapshot, read_recent_snapshots
from validation.texture_validator import validate_texture
from validation.audio_validator import validate_audio
from products.product_types import (
    get as get_product_type, list_product_types, validate_metadata as validate_product_metadata,
    unsupported_validators, UnknownProductType, ProductMetadataError,
)
from compiler.product_compiler import compile_product, CompilerError
from packaging.package_builder import (
    build_package, list_releases, load_release_manifest, PackagingError, PACKAGE_MANIFEST_FILENAME,
)
from packaging.signature_generator import sign_bytes, verify_signature

# Every real operation below goes through the tool-contract authorization
# boundary (tools/tool_executor.py) instead of calling adapters directly —
# register_all() is idempotent per-process, called once here at import time
# so the CLI always has its tools available.
registered_tools.register_all()

CALLER_ID = "cli"  # the identity this process presents to the authorization boundary

NOT_YET_IMPLEMENTED = {
    "create-pack": "Phase 2 (multi-asset packs need the workflow engine)",
    "render": "Phase 2 (Blender adapter)",
    "animate": "Phase 2 (Blender adapter)",
    "export": "Phase 2 (Blender adapter)",
    "preview": "Phase 3 (preview generation)",
    "marketplace": "Phase 4 (marketplace packaging) — deliberately not started, no KOBA Core/marketplace runtime exists to integrate with",
    "batch": "Phase 4 (batch generation)",
}


def cmd_doctor(args):
    with OperationLog("doctor", args=vars(args)) as log:
        results = detect_all()
        print("ASSET FACTORY SYSTEM CHECK\n")
        for name in REQUIRED_TOOLS:
            status = results[name]
            mark = "✓" if status.found else "✗"
            detail = status.version if status.found else status.error
            print(f"{mark} {name:<12} {detail or ''}")
            log.info(f"{name}: found={status.found} detail={detail}")

        print("\nOptional:")
        for name in OPTIONAL_TOOLS:
            status = results[name]
            mark = "✓" if status.found else "✗"
            detail = status.version if status.found else "not found"
            print(f"{mark} {name:<12} {detail or ''}")
            log.info(f"{name}: found={status.found} detail={detail}")

        ready = system_ready(results)
        print(f"\n{'System ready.' if ready else 'System NOT ready — missing required tools above.'}")
        if not ready:
            log.warn("system not ready: missing required tools")
        return 0 if ready else 1


def cmd_capabilities(args):
    """Registry-shaped view of the same real detection `doctor` reports,
    plus persisted history: every real job already stamps a fresh
    CapabilitySnapshot on creation (see orchestrator/job.py); `--record`
    additionally appends a standalone snapshot to the same log, and
    `--history` shows recent ones so capability drift over time is
    actually inspectable, not just "what's true right now"."""
    with OperationLog("capabilities", args=vars(args)):
        if args.history:
            snapshots = read_recent_snapshots(limit=args.limit)
            if not snapshots:
                print("No recorded snapshots yet. Run with --record to create one.")
                return 0
            print(f"{len(snapshots)} recorded snapshot(s):\n")
            for snap in snapshots:
                found = sum(1 for t in snap["tools"].values() if t["found"])
                print(f"{snap['captured_at']}  {found}/{len(snap['tools'])} tools found")
            return 0

        snapshot = record_snapshot() if args.record else capture_snapshot()
        print(f"Capability snapshot ({snapshot['captured_at']}){' — recorded' if args.record else ''}:\n")
        for name, tool in sorted(snapshot["tools"].items()):
            mark = "✓" if tool["found"] else "✗"
            req = "required" if tool["required"] else "optional"
            detail = tool["version"] or "not found"
            print(f"{mark} {name:<12} ({req}) {detail}")
        return 0


def cmd_create(args):
    with OperationLog("create", args=vars(args)) as log:
        if project_exists(args.name):
            print(f"Project '{args.name}' already exists.", file=sys.stderr)
            log.error(f"project '{args.name}' already exists")
            return 1

        if args.dry_run:
            plan = create_project(args.name, project_type=args.type, dry_run=True)
            print(json.dumps(plan, indent=2))
            log.info("dry-run only, nothing created")
            return 0

        proj_dir = create_project(args.name, project_type=args.type)
        log.record_file(proj_dir)
        print(f"Created project '{args.name}' at {proj_dir}")
        print("Note: this creates the project skeleton + manifest only. Actual")
        print("asset generation (Blender/Inkscape/etc. adapters) is Phase 2 —")
        print("not implemented yet.")
        return 0


def cmd_status(args):
    with OperationLog("status", args=vars(args)):
        if args.name:
            status = get_project_status(args.name)
            if status is None:
                print(f"No such project: {args.name}", file=sys.stderr)
                return 1
            print(json.dumps(status, indent=2))
            return 0

        projects = list_projects()
        if not projects:
            print("No projects yet. Create one with: asset-factory create <name>")
            return 0
        print(f"{len(projects)} project(s):")
        for p in projects:
            print(f"  - {p}")
        return 0


def cmd_telemetry(args):
    """Real aggregation over every OperationLog record on disk (not
    project-scoped — logs/ is global across projects, same as `logs`
    itself): per-command run counts, success rates, average durations,
    total errors/warnings. Every number here comes from an actual past
    command run; an empty logs/ directory reports zero runs, never a
    fabricated baseline."""
    with OperationLog("telemetry", args=vars(args)):
        summary = telemetry_summarize(command=args.command)
        print(f"{summary['total_runs']} logged run(s)"
              + (f" for command '{args.command}'" if args.command else "")
              + (f" ({summary['skipped_unreadable']} unreadable log file(s) skipped)"
                 if summary["skipped_unreadable"] else "") + "\n")
        if not summary["by_command"]:
            print("(nothing logged yet)")
            return 0
        print(f"{'COMMAND':<14} {'RUNS':<6} {'SUCCESS%':<10} {'AVG_SEC':<9} {'ERRORS':<8} WARNINGS")
        for cmd, b in sorted(summary["by_command"].items()):
            print(f"{cmd:<14} {b['runs']:<6} {b['success_rate'] * 100:<10.1f} "
                  f"{b['avg_duration_seconds']:<9.3f} {b['total_errors']:<8} {b['total_warnings']}")
        return 0


def cmd_logs(args):
    with OperationLog("logs", args=vars(args)):
        recent = list_recent_logs(limit=args.limit)
        if not recent:
            print("No logs yet.")
            return 0
        for path in recent:
            print(path)
        return 0


def _resolve_blend_file(name, explicit_path, prefer_optimized=False):
    if explicit_path:
        if not os.path.isfile(explicit_path):
            raise FileNotFoundError(f"--blend-file not found: {explicit_path}")
        return explicit_path

    search_order = ["optimized", "blender"] if prefer_optimized else ["blender", "optimized"]
    for subdir in search_order:
        found = find_blend_files(name, subdir=subdir)
        if found:
            return found[0]

    raise FileNotFoundError(
        f"No .blend file found for project '{name}' in blender/ or optimized/. "
        f"Put one there or pass --blend-file."
    )


def _print_report(d):
    print(f"KOBA PERFORMANCE REPORT (profile: {d['profile']})\n")
    m = d["metrics"]
    for key in ("entity_count", "unique_meshes", "instanced_count", "triangles", "materials",
                "dynamic_lights", "physics_objects", "animated_objects"):
        print(f"{key.upper():<20} {m[key]}")
    for key in ("collision_coverage", "lod_coverage", "culling_coverage"):
        print(f"{key.upper():<20} {m[key] * 100:.0f}%")
    print(f"\nRESULT: {d['result']}")
    if d["failures"]:
        print("\nFAILURES (over budget):")
        for f in d["failures"]:
            print(f"  - {f}")
    if d["warnings"]:
        print("\nWARNINGS:")
        for w in d["warnings"]:
            print(f"  - {w}")


def _record_validation(proj_dir, blend_path, report, log):
    """Shared by cmd_validate and cmd_agent (when the agent decides to
    validate) — the manifest/artifact-graph bookkeeping is identical
    either way, since the AI only decided WHICH tool to run, not what the
    result means (master spec Rule 2)."""
    if not os.path.isdir(proj_dir):
        return
    manifest = load_manifest(proj_dir)
    for w in report["warnings"]:
        add_warning(manifest, w)
    if report["result"] == "FAIL":
        for f in report["failures"]:
            add_error(manifest, f)
    save_manifest(proj_dir, manifest)

    graph = load_graph(proj_dir)
    artifact_id = get_or_create_source_artifact(graph, blend_path, "blend_source")
    graph.set_validation_status(artifact_id, ART_PASS if report["result"] == "PASS" else ART_FAIL)
    graph.artifacts[artifact_id]["metadata"]["last_validation"] = report
    save_graph(proj_dir, graph)
    log.info(f"artifact {artifact_id} validation_status -> {report['result']}")


def _record_optimization(proj_dir, blend_path, profile, result, log):
    """Shared by cmd_optimize and cmd_agent (when the agent decides to
    optimize). validation_status is PENDING, not PASS — optimize_blend
    only assigns culling/merges geometry, it never re-runs the validator
    against its own output, so nothing here has actually earned a PASS
    yet (Rule 2: AI/tooling is not the validation authority; only a real
    validate_blend call is). Run `validate --optimized` afterward, or use
    `repair` (repair/repair_engine.py), which always revalidates before
    recording a status."""
    log.record_file(result["output_path"])
    if not os.path.isdir(proj_dir):
        return
    manifest = load_manifest(proj_dir)
    add_export(manifest, asset_name=result["asset_name"], fmt="optimized_blend", path=result["output_path"])
    save_manifest(proj_dir, manifest)

    graph = load_graph(proj_dir)
    fresh_hash = hash_file(blend_path)
    existing_source = find_by_path(graph, blend_path)
    if existing_source and graph.has_changed(existing_source["artifact_id"], fresh_hash):
        invalidated = graph.invalidate(existing_source["artifact_id"])
        log.info(f"source blend changed since last graph update — invalidated {len(invalidated)} artifact(s)")
    source_artifact_id = get_or_create_source_artifact(graph, blend_path, "blend_source")
    graph.artifacts[source_artifact_id]["input_hash"] = fresh_hash
    optimized_id = graph.add_artifact(
        artifact_type="optimized_blend", processor="blender_bridge.optimize_blend",
        parent_artifacts=[source_artifact_id], input_hash=fresh_hash,
        output_path=result["output_path"], validation_status=ART_PENDING,
        metadata={"profile": profile, "actions": result["actions"]},
    )
    save_graph(proj_dir, graph)
    log.info(f"artifact {optimized_id} (optimized_blend) <- parent {source_artifact_id}")


def cmd_validate(args):
    with OperationLog("validate", args=vars(args)) as log:
        try:
            blend_path = _resolve_blend_file(args.name, args.blend_file, prefer_optimized=args.optimized)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        proj_dir = project_dir_for(args.name)
        job = create_job(proj_dir, "validate", {
            "name": args.name, "profile": args.profile, "blend_file": args.blend_file,
            "asset_name": args.asset_name, "optimized": args.optimized,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        log.info(f"validating {blend_path} against profile '{args.profile}' via tool contract 'validate_blend'")
        try:
            report = run_tool("validate_blend", CALLER_ID, blend_path=blend_path,
                               profile_name=args.profile, asset_name=args.asset_name)
        except (BlenderBridgeError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Validation failed to run: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, VALIDATING)
        _print_report(report)

        _record_validation(proj_dir, blend_path, report, log)

        # The job's own state tracks "did the validate command complete" —
        # distinct from whether the ASSET passed, which lives in the
        # artifact graph's validation_status above. A job that ran
        # validation and got a clean FAIL verdict still completed
        # successfully as a job.
        job_transition(job, READY, result_summary={"result": report["result"]})
        log.info(f"job {job['job_id']}: READY")

        return 0 if report["result"] == "PASS" else 1


def cmd_optimize(args):
    with OperationLog("optimize", args=vars(args)) as log:
        try:
            blend_path = _resolve_blend_file(args.name, args.blend_file, prefer_optimized=False)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        proj_dir = project_dir_for(args.name)
        output_path = args.output or os.path.join(proj_dir, "optimized", os.path.basename(blend_path))

        job = create_job(proj_dir, "optimize", {
            "name": args.name, "profile": args.profile, "blend_file": args.blend_file,
            "asset_name": args.asset_name, "merge_group": args.merge_group, "output": args.output,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        log.info(f"optimizing {blend_path} -> {output_path} (profile '{args.profile}') via tool contract 'optimize_blend'")
        try:
            result = run_tool("optimize_blend", CALLER_ID, blend_path=blend_path, output_path=output_path,
                               profile_name=args.profile, asset_name=args.asset_name, merge_group=args.merge_group)
        except (BlenderBridgeError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Optimize failed to run: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, PACKAGING)

        print(f"Asset: {result['asset_name']}")
        print("Actions taken:")
        for a in result["actions"]:
            print(f"  - {a}")
        print(f"\nSaved: {result['output_path']}  (source at {blend_path} left untouched)")
        print("\nBefore -> After:")
        for key in ("entity_count", "unique_meshes", "triangles", "culling_coverage"):
            before, after = result["metrics_before"][key], result["metrics_after"][key]
            print(f"  {key:<20} {before} -> {after}")

        _record_optimization(proj_dir, blend_path, args.profile, result, log)

        job_transition(job, READY, result_summary={"output_path": result["output_path"]})
        log.info(f"job {job['job_id']}: READY")

        return 0


def cmd_agent(args):
    """The blender_agent path: a natural-language instruction goes through
    the AI router to a provider, which decides WHICH tool contract to
    call (validate_blend or optimize_blend) — the same two contracts
    cmd_validate/cmd_optimize call directly. The AI never declares the
    result valid (master spec Rule 2); that's still the artifact graph's
    validation_status, recorded via the exact same helpers."""
    with OperationLog("agent", args=vars(args)) as log:
        try:
            blend_path = _resolve_blend_file(args.name, args.blend_file, prefer_optimized=False)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        proj_dir = project_dir_for(args.name)
        output_path = args.output or os.path.join(proj_dir, "optimized", os.path.basename(blend_path))

        job = create_job(proj_dir, "agent", {
            "name": args.name, "instruction": args.instruction, "profile": args.profile,
            "blend_file": args.blend_file, "asset_name": args.asset_name,
            "merge_group": args.merge_group, "output": args.output,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        agent = BlenderAgent()
        try:
            outcome = agent.run(
                args.instruction, blend_path=blend_path, profile_name=args.profile,
                asset_name=args.asset_name, merge_group=args.merge_group, output_path=output_path,
            )
        except BlenderAgentError as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Agent failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        tool_id, result = outcome["tool_id"], outcome["result"]
        print(f"AI provider: {outcome['provider_id']} (model={outcome['model_id']})")
        print(f"Decision: {tool_id}  ({outcome.get('reasoning')})")
        log.info(f"blender_agent (provider={outcome['provider_id']}, model={outcome['model_id']}) "
                 f"chose '{tool_id}': {outcome.get('reasoning')}")

        if tool_id == "validate_blend":
            job = job_transition(job, VALIDATING)
            _print_report(result)
            _record_validation(proj_dir, blend_path, result, log)
            job_transition(job, READY, result_summary={"tool_id": tool_id, "result": result["result"]})
            log.info(f"job {job['job_id']}: READY")
            return 0 if result["result"] == "PASS" else 1

        job = job_transition(job, PACKAGING)
        print(f"Asset: {result['asset_name']}")
        print("Actions taken:")
        for a in result["actions"]:
            print(f"  - {a}")
        print(f"\nSaved: {result['output_path']}  (source at {blend_path} left untouched)")
        _record_optimization(proj_dir, blend_path, args.profile, result, log)
        job_transition(job, READY, result_summary={"tool_id": tool_id, "output_path": result["output_path"]})
        log.info(f"job {job['job_id']}: READY")
        return 0


def _count_prior_repair_attempts(graph, source_artifact_id):
    if not graph:
        return 0
    return sum(
        1 for a in graph.artifacts.values()
        if a.get("metadata", {}).get("repairs_artifact") == source_artifact_id
    )


def _repair_output_path_for(proj_dir, blend_path, attempt):
    basename, ext = os.path.splitext(os.path.basename(blend_path))
    return os.path.join(proj_dir, "repaired", f"{basename}__repair_v{attempt}{ext}")


def _next_repair_output_path(proj_dir, graph, source_artifact_id, blend_path):
    """Never overwrite the failed artifact — count prior repair attempts
    against this exact source so each one gets its own numbered output
    path and its own new artifact node. Shared by cmd_repair_agent (and,
    for a single attempt, cmd_repair)."""
    attempt = _count_prior_repair_attempts(graph, source_artifact_id) + 1
    return attempt, _repair_output_path_for(proj_dir, blend_path, attempt)


def _record_repair(proj_dir, graph, source_artifact_id, blend_path, profile,
                    result, decision, attempt, revalidated, log):
    """Records a repair attempt as a new artifact VERSION, parented to
    the source — never overwriting the source's own FAILED status.
    validation_status always comes from `revalidated` (a real
    validate_blend result), never asserted by fiat. Shared by cmd_repair
    and cmd_repair_agent. Also updates the project manifest (section 12),
    the same dual bookkeeping _record_validation already does — a
    repaired output that PASSes is a real export; one that still FAILs
    records its real remaining failures as manifest errors, same as a
    plain `validate` FAIL does."""
    if os.path.isdir(proj_dir):
        manifest = load_manifest(proj_dir)
        if revalidated["result"] == "PASS":
            add_export(manifest, asset_name=os.path.basename(blend_path), fmt="repaired_blend",
                       path=result["output_path"])
        else:
            for f in revalidated["failures"]:
                add_error(manifest, f)
        save_manifest(proj_dir, manifest)

    if not graph:
        return None
    fresh_hash = hash_file(blend_path)
    if graph.has_changed(source_artifact_id, fresh_hash):
        graph.invalidate(source_artifact_id)
    graph.artifacts[source_artifact_id]["input_hash"] = fresh_hash
    repaired_id = graph.add_artifact(
        artifact_type="optimized_blend", processor="repair_engine.run_repair",
        parent_artifacts=[source_artifact_id], input_hash=fresh_hash,
        output_path=result["output_path"],
        validation_status=ART_PASS if revalidated["result"] == "PASS" else ART_FAIL,
        metadata={
            "profile": profile, "actions": result["actions"],
            "repairs_artifact": source_artifact_id, "repair_attempt": attempt,
            "repair_strategy": decision["strategy"],
            "repair_merge_group": decision["merge_group"],
            "repair_decimate_ratio": decision["decimate_ratio"],
        },
    )
    graph.artifacts[repaired_id]["version_id"] = f"repair_v{attempt}"
    save_graph(proj_dir, graph)
    log.info(f"artifact {repaired_id} (repair attempt #{attempt}) <- parent {source_artifact_id}, "
             f"revalidation: {revalidated['result']}")
    return repaired_id


def cmd_repair(args):
    """Phase D: the first real repair loop (master spec section 10):
    GENERATE -> VALIDATE -> FAIL -> DIAGNOSE -> CLASSIFY -> REPAIR ->
    CREATE NEW ARTIFACT VERSION -> REVALIDATE -> PASS/FAIL. The failed
    source artifact is never overwritten or have its status touched by
    this command — a repair attempt always writes to its own numbered
    output path and gets its own new artifact node, and PASS/FAIL always
    comes from a fresh validate_blend call (repair.repair_engine never
    decides that itself — Rule 2)."""
    with OperationLog("repair", args=vars(args)) as log:
        try:
            blend_path = _resolve_blend_file(args.name, args.blend_file, prefer_optimized=False)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        proj_dir = project_dir_for(args.name)
        job = create_job(proj_dir, "repair", {
            "name": args.name, "profile": args.profile, "blend_file": args.blend_file,
            "asset_name": args.asset_name, "merge_group": args.merge_group,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        # DIAGNOSE: always a fresh, real validate_blend call — never trust
        # a stale graph status for the repair decision.
        try:
            report = revalidate(blend_path, args.profile, asset_name=args.asset_name)
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Diagnosis failed to run: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        _print_report(report)
        _record_validation(proj_dir, blend_path, report, log)

        if report["result"] == "PASS":
            job_transition(job, VALIDATING)
            job_transition(job, READY, result_summary={"result": "PASS", "repair_needed": False})
            log.info(f"job {job['job_id']}: READY (nothing to repair)")
            print("Nothing to repair — validation already PASSes.")
            return 0

        proj_dir_exists = os.path.isdir(proj_dir)
        graph = load_graph(proj_dir) if proj_dir_exists else None
        source_artifact_id = get_or_create_source_artifact(graph, blend_path, "blend_source") if graph else None
        base_attempt = _count_prior_repair_attempts(graph, source_artifact_id)

        def output_path_fn(i):
            return _repair_output_path_for(proj_dir, blend_path, base_attempt + i)

        # CLASSIFY + SELECT REPAIR STRATEGY, then REPAIR -> REVALIDATE,
        # bounded-retried by repair_manager if --max-attempts > 1 (see its
        # module docstring for exactly when it does/doesn't keep going).
        job = job_transition(job, REPAIRING)
        try:
            loop_attempts = repair_loop(
                report, blend_path, args.profile, output_path_fn,
                merge_group=args.merge_group, asset_name=args.asset_name,
                max_attempts=args.max_attempts, proj_dir=proj_dir if proj_dir_exists else None,
            )
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"No repair strategy available: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        for step in loop_attempts:
            decision, result, revalidated = step["decision"], step["repair_result"], step["revalidation"]
            global_attempt = base_attempt + step["attempt"]
            log.info(f"diagnosis: {decision}")
            strategy_parts = []
            if decision["merge_group"]:
                strategy_parts.append(f"merge visibility_group '{decision['merge_group']}'")
            if decision["decimate_ratio"] is not None:
                strategy_parts.append(f"decimate geometry to ratio {decision['decimate_ratio']}")
            print(f"\nRepair strategy: {' + '.join(strategy_parts)} (addresses: {decision['addresses']})")
            if decision["cannot_address"]:
                print(f"NOTE: cannot address (no automated fix exists for): {decision['cannot_address']}")

            log.record_file(result["output_path"])
            print(f"\nRepair attempt #{global_attempt} saved: {result['output_path']}")
            print("Actions taken:")
            for a in result["actions"]:
                print(f"  - {a}")

            print("\nAfter repair:")
            _print_report(revalidated)

            _record_repair(proj_dir, graph, source_artifact_id, blend_path, args.profile,
                            result, decision, global_attempt, revalidated, log)

        final = loop_attempts[-1]
        final_result, final_revalidated = final["repair_result"], final["revalidation"]
        job_transition(job, READY, result_summary={
            "repair_attempts": len(loop_attempts), "output_path": final_result["output_path"],
            "result": final_revalidated["result"],
        })
        log.info(f"job {job['job_id']}: READY")
        return 0 if final_revalidated["result"] == "PASS" else 1


def cmd_repair_agent(args):
    """The second real agent (master spec's agents/repair_agent): a
    natural-language instruction goes through the SAME AI router as
    `agent` (blender_agent) to a provider, which extracts a merge_group
    from free text if the instruction names one (e.g. "merge the
    'cluster' group"). Proves the one-router/multiple-agents pattern
    generalizes. Deliberately mirrors cmd_repair's exact ordering
    (diagnose -> record -> classify -> repair -> revalidate -> record)
    rather than delegating that sequence to the agent — see
    agents/repair_agent.py's docstring for the real bug that ordering
    avoids (two artifact ids minted for one file when a repair attempt
    was computed before the source artifact's FAIL status was persisted).
    The AI only supplies the merge_group hint; everything else, including
    PASS/FAIL, is exactly the same deterministic path cmd_repair uses."""
    with OperationLog("repair-agent", args=vars(args)) as log:
        try:
            blend_path = _resolve_blend_file(args.name, args.blend_file, prefer_optimized=False)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        proj_dir = project_dir_for(args.name)
        job = create_job(proj_dir, "repair-agent", {
            "name": args.name, "instruction": args.instruction, "profile": args.profile,
            "blend_file": args.blend_file, "asset_name": args.asset_name,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        agent = RepairAgent()
        try:
            provider, merge_group = agent.get_merge_group_hint(args.instruction)
        except RepairAgentError as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Repair agent failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1
        print(f"AI provider: {provider.provider_id} (model={getattr(provider, 'model_id', None)})")
        if merge_group:
            print(f"Extracted merge_group from instruction: '{merge_group}'")

        # DIAGNOSE: always a fresh, real validate_blend call.
        try:
            report = revalidate(blend_path, args.profile, asset_name=args.asset_name)
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Diagnosis failed to run: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        _print_report(report)
        _record_validation(proj_dir, blend_path, report, log)

        if report["result"] == "PASS":
            job_transition(job, VALIDATING)
            job_transition(job, READY, result_summary={"result": "PASS", "repair_needed": False})
            log.info(f"job {job['job_id']}: READY (nothing to repair)")
            print("Nothing to repair — validation already PASSes.")
            return 0

        # CLASSIFY + SELECT REPAIR STRATEGY — merge_group came from the AI
        # (or None, if the instruction didn't name one); classify_failure
        # still refuses to guess, exactly as it does for a CLI --merge-group.
        try:
            decision = classify_failure(report, merge_group=merge_group)
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"No repair strategy available: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        strategy_parts = []
        if decision["merge_group"]:
            strategy_parts.append(f"merge visibility_group '{decision['merge_group']}'")
        if decision["decimate_ratio"] is not None:
            strategy_parts.append(f"decimate geometry to ratio {decision['decimate_ratio']}")
        print(f"\nRepair strategy: {' + '.join(strategy_parts)} (addresses: {decision['addresses']})")

        # Load the graph fresh now — AFTER _record_validation above has
        # already created/persisted the source artifact — so this
        # resolves the SAME artifact id, not a second never-saved one.
        proj_dir_exists = os.path.isdir(proj_dir)
        graph = load_graph(proj_dir) if proj_dir_exists else None
        source_artifact_id = get_or_create_source_artifact(graph, blend_path, "blend_source") if graph else None
        attempt, output_path = _next_repair_output_path(proj_dir, graph, source_artifact_id, blend_path)

        job = job_transition(job, REPAIRING)
        try:
            result = run_repair(blend_path, output_path, args.profile, decision, asset_name=args.asset_name)
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Repair action failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        log.record_file(result["output_path"])
        print(f"\nRepair attempt #{attempt} saved: {result['output_path']}")
        print("Actions taken:")
        for a in result["actions"]:
            print(f"  - {a}")

        # REVALIDATE — the only thing allowed to decide PASS/FAIL.
        try:
            revalidated = revalidate(result["output_path"], args.profile, asset_name=args.asset_name)
        except UnrepairableFailure as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Revalidation failed to run: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        print("\nAfter repair:")
        _print_report(revalidated)

        _record_repair(proj_dir, graph, source_artifact_id, blend_path, args.profile,
                        result, decision, attempt, revalidated, log)

        job_transition(job, READY, result_summary={
            "repair_attempt": attempt, "output_path": result["output_path"], "result": revalidated["result"],
        })
        log.info(f"job {job['job_id']}: READY")
        return 0 if revalidated["result"] == "PASS" else 1


def _short(artifact_id):
    return artifact_id[:8] if artifact_id else artifact_id


def cmd_graph(args):
    """Inspect a project's artifact graph — proves it's a real, queryable
    system of record (master spec section 4/30 observability), not just
    internal bookkeeping nobody can see."""
    with OperationLog("graph", args=vars(args)):
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        graph = load_graph(proj_dir)

        if args.lineage:
            matches = [a for a in graph.artifacts.values() if a["artifact_id"].startswith(args.lineage)]
            if not matches:
                print(f"No artifact id starting with '{args.lineage}'", file=sys.stderr)
                return 1
            target = matches[0]
            print(f"Lineage of {_short(target['artifact_id'])} ({target['artifact_type']}):")
            for a in graph.lineage(target["artifact_id"]):
                print(f"  {_short(a['artifact_id'])}  {a['artifact_type']:<16} {a['validation_status']:<12} {a.get('storage_location') or ''}")
            return 0

        if args.affected:
            matches = [a for a in graph.artifacts.values() if a["artifact_id"].startswith(args.affected)]
            if not matches:
                print(f"No artifact id starting with '{args.affected}'", file=sys.stderr)
                return 1
            target = matches[0]
            print(f"Artifacts affected by a change to {_short(target['artifact_id'])} ({target['artifact_type']}):")
            affected = graph.find_affected(target["artifact_id"])
            if not affected:
                print("  (none)")
            for a in affected:
                print(f"  {_short(a['artifact_id'])}  {a['artifact_type']:<16} {a['validation_status']:<12} {a.get('storage_location') or ''}")
            return 0

        if not graph.artifacts:
            print(f"No artifacts yet for '{args.name}'. Run validate/optimize/process to create some.")
            return 0
        print(f"{len(graph.artifacts)} artifact(s) in '{args.name}':\n")
        print(f"{'ID':<10} {'TYPE':<16} {'STATUS':<11} {'PARENTS':<10} LOCATION")
        for a in sorted(graph.artifacts.values(), key=lambda x: x["created_at"]):
            parent_summary = ",".join(_short(p) for p in a["parent_artifacts"]) or "-"
            print(f"{_short(a['artifact_id']):<10} {a['artifact_type']:<16} {a['validation_status']:<11} {parent_summary:<10} {a.get('storage_location') or ''}")
        return 0


def cmd_cache(args):
    """Inspect a project's content-addressed artifact store
    (core/artifact_store.py) — real object counts/bytes on disk and the
    real cache-hit index, not just internal bookkeeping nobody can see
    (same observability intent as `graph`)."""
    with OperationLog("cache", args=vars(args)):
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        stats = artifact_store.store_stats(proj_dir)
        print(f"Artifact store for '{args.name}':")
        print(f"  objects:       {stats['object_count']}")
        print(f"  total bytes:   {stats['total_bytes']}")
        print(f"  cache entries: {stats['cache_entries']}")

        if args.entries:
            entries = artifact_store.list_cache_entries(proj_dir)
            if not entries:
                print("\n(no cache entries yet)")
                return 0
            print(f"\n{'KEY':<10} {'OUTPUT_HASH':<10} {'PRESENT':<8} CACHED_AT")
            for e in entries:
                print(f"{e['key'][:8]:<10} {e['output_hash'][:8]:<10} {str(e['object_present']):<8} {e['cached_at']}")
        return 0


def cmd_process(args):
    """Process an SVG through Inkscape (-> PNG variants) and optionally
    ImageMagick (-> format conversion) into a project's textures/
    directory. This is the first real (non-Blender) tool-adapter path —
    intentionally narrow (one input type) rather than a general dispatcher,
    since the workflow engine that would route arbitrary asset specs to
    the right adapter is still Phase 3, not built yet."""
    with OperationLog("process", args=vars(args)) as log:
        if not os.path.isfile(args.svg):
            print(f"SVG not found: {args.svg}", file=sys.stderr)
            log.error(f"SVG not found: {args.svg}")
            return 1

        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        basename = args.basename or os.path.splitext(os.path.basename(args.svg))[0]
        source_copy = os.path.join(proj_dir, "source", os.path.basename(args.svg))
        textures_dir = os.path.join(proj_dir, "textures")

        job = create_job(proj_dir, "process", {
            "name": args.name, "svg": args.svg, "sizes": args.sizes,
            "format": args.format, "basename": args.basename,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        try:
            shutil.copyfile(args.svg, source_copy)  # preserve source, per project brief section 11

            inkscape = InkscapeAdapter()  # kept for .version() reporting below, not for the export call itself
            sizes = tuple(int(s) for s in args.sizes.split(","))
            variants = run_tool("export_svg_variants", CALLER_ID, svg_path=source_copy,
                                 output_dir=textures_dir, basename=basename, widths=sizes)
            log.info(f"exported {len(variants)} PNG variants via tool contract 'export_svg_variants'")

            generated_files = list(variants.values())
            converted = {}

            if args.format and args.format != "png":
                for size, png_path in variants.items():
                    out_path = os.path.join(textures_dir, f"{basename}_{size}.{args.format}")
                    converted[size] = run_tool("convert_image_format", CALLER_ID,
                                                src_path=png_path, dst_path=out_path)
                    generated_files.append(converted[size])
                log.info(f"converted {len(converted)} variants via tool contract 'convert_image_format'")

        except (InkscapeAdapterError, ImageMagickAdapterError, ToolNotFound,
                UnsupportedCapability, PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Processing failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, PACKAGING)

        print(f"Processed '{args.svg}' -> {len(generated_files)} file(s) in {textures_dir}")
        for f in generated_files:
            print(f"  - {f}")

        manifest = load_manifest(proj_dir)
        add_tool_used(manifest, "inkscape", version=inkscape.version())
        if args.format and args.format != "png":
            add_tool_used(manifest, "imagemagick", version=ImageMagickAdapter().version())
        add_asset(manifest, basename, "texture", source_files=[source_copy], generated_files=generated_files)
        save_manifest(proj_dir, manifest)
        for f in generated_files:
            log.record_file(f)

        graph = load_graph(proj_dir)
        svg_id = graph.add_artifact(
            artifact_type="svg_source", processor="process_cli",
            output_path=source_copy, input_hash=hash_file(source_copy), validation_status=ART_PASS,
        )
        png_ids = {}
        for size, png_path in variants.items():
            png_ids[size] = graph.add_artifact(
                artifact_type="texture_png", processor="inkscape_adapter", processor_version=inkscape.version(),
                parent_artifacts=[svg_id], output_path=png_path, validation_status=ART_PASS,
                metadata={"width": size},
            )
        for size, conv_path in converted.items():
            graph.add_artifact(
                artifact_type=f"texture_{args.format}", processor="imagemagick_adapter",
                parent_artifacts=[png_ids[size]], output_path=conv_path, validation_status=ART_PASS,
                metadata={"width": size},
            )
        save_graph(proj_dir, graph)
        log.info(f"artifact graph: svg_source {svg_id} -> {len(png_ids)} texture_png -> {len(converted)} converted")

        job_transition(job, READY, result_summary={"generated_files": generated_files})
        log.info(f"job {job['job_id']}: READY")

        return 0


def cmd_krita(args):
    """Export a Krita document (.kra, or anything Krita can open) to a
    raster format via the real krita_export tool contract, into a
    project's textures/ directory — the Krita-adapter equivalent of
    cmd_process's Inkscape path, for the one thing Krita does that
    Inkscape/ImageMagick don't (read .kra)."""
    with OperationLog("krita", args=vars(args)) as log:
        if not os.path.isfile(args.source):
            print(f"Source not found: {args.source}", file=sys.stderr)
            log.error(f"source not found: {args.source}")
            return 1

        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        basename = args.basename or os.path.splitext(os.path.basename(args.source))[0]
        source_copy = os.path.join(proj_dir, "source", os.path.basename(args.source))
        dst_path = os.path.join(proj_dir, "textures", f"{basename}.{args.format}")

        job = create_job(proj_dir, "krita", {
            "name": args.name, "source": args.source, "format": args.format, "basename": args.basename,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        try:
            shutil.copyfile(args.source, source_copy)  # preserve source, per project brief section 11
            krita = KritaAdapter()  # kept for .version() reporting below, not for the export call itself
            run_tool("krita_export", CALLER_ID, src_path=source_copy, dst_path=dst_path)
            log.info("exported via tool contract 'krita_export'")
        except (KritaAdapterError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Export failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, PACKAGING)

        print(f"Exported '{args.source}' -> {dst_path}")

        manifest = load_manifest(proj_dir)
        add_tool_used(manifest, "krita", version=krita.version())
        add_asset(manifest, basename, "texture", source_files=[source_copy], generated_files=[dst_path])
        save_manifest(proj_dir, manifest)
        log.record_file(dst_path)

        graph = load_graph(proj_dir)
        source_id = graph.add_artifact(
            artifact_type="kra_source", processor="krita_cli",
            output_path=source_copy, input_hash=hash_file(source_copy), validation_status=ART_PASS,
        )
        graph.add_artifact(
            artifact_type="texture_raster", processor="krita_adapter", processor_version=krita.version(),
            parent_artifacts=[source_id], output_path=dst_path, validation_status=ART_PASS,
        )
        save_graph(proj_dir, graph)
        log.info(f"artifact graph: kra_source {source_id} -> texture_raster")

        job_transition(job, READY, result_summary={"output_path": dst_path})
        log.info(f"job {job['job_id']}: READY")

        return 0


def cmd_gimp(args):
    """Export a GIMP document (.xcf, or anything GIMP can open) to a
    raster format via the real gimp_export tool contract, into a
    project's textures/ directory — the GIMP-adapter equivalent of
    cmd_krita, for the one thing GIMP does that Inkscape/ImageMagick
    don't (read .xcf, GIMP's own layered format)."""
    with OperationLog("gimp", args=vars(args)) as log:
        if not os.path.isfile(args.source):
            print(f"Source not found: {args.source}", file=sys.stderr)
            log.error(f"source not found: {args.source}")
            return 1

        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        basename = args.basename or os.path.splitext(os.path.basename(args.source))[0]
        source_copy = os.path.join(proj_dir, "source", os.path.basename(args.source))
        dst_path = os.path.join(proj_dir, "textures", f"{basename}.{args.format}")

        job = create_job(proj_dir, "gimp", {
            "name": args.name, "source": args.source, "format": args.format, "basename": args.basename,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        try:
            shutil.copyfile(args.source, source_copy)  # preserve source, per project brief section 11
            gimp = GimpAdapter()  # kept for .version() reporting below, not for the export call itself
            run_tool("gimp_export", CALLER_ID, src_path=source_copy, dst_path=dst_path)
            log.info("exported via tool contract 'gimp_export'")
        except (GimpAdapterError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Export failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, PACKAGING)

        print(f"Exported '{args.source}' -> {dst_path}")

        manifest = load_manifest(proj_dir)
        add_tool_used(manifest, "gimp", version=gimp.version())
        add_asset(manifest, basename, "texture", source_files=[source_copy], generated_files=[dst_path])
        save_manifest(proj_dir, manifest)
        log.record_file(dst_path)

        graph = load_graph(proj_dir)
        source_id = graph.add_artifact(
            artifact_type="xcf_source", processor="gimp_cli",
            output_path=source_copy, input_hash=hash_file(source_copy), validation_status=ART_PASS,
        )
        graph.add_artifact(
            artifact_type="texture_raster", processor="gimp_adapter", processor_version=gimp.version(),
            parent_artifacts=[source_id], output_path=dst_path, validation_status=ART_PASS,
        )
        save_graph(proj_dir, graph)
        log.info(f"artifact graph: xcf_source {source_id} -> texture_raster")

        job_transition(job, READY, result_summary={"output_path": dst_path})
        log.info(f"job {job['job_id']}: READY")

        return 0


def cmd_ffmpeg(args):
    """Transcode and/or extract a thumbnail frame from a video/audio
    source via the real ffmpeg_transcode/ffmpeg_extract_frame tool
    contracts. At least one of --transcode/--thumbnail is required —
    there's no default action to fall back to."""
    with OperationLog("ffmpeg", args=vars(args)) as log:
        if not args.transcode and not args.thumbnail:
            print("Nothing to do: pass --transcode <ext> and/or --thumbnail <timestamp>", file=sys.stderr)
            log.error("no action requested")
            return 1

        if not os.path.isfile(args.source):
            print(f"Source not found: {args.source}", file=sys.stderr)
            log.error(f"source not found: {args.source}")
            return 1

        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        basename = args.basename or os.path.splitext(os.path.basename(args.source))[0]
        source_copy = os.path.join(proj_dir, "source", os.path.basename(args.source))

        job = create_job(proj_dir, "ffmpeg", {
            "name": args.name, "source": args.source, "transcode": args.transcode,
            "thumbnail": args.thumbnail, "basename": args.basename,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        transcoded_path = None
        thumbnail_path = None
        try:
            shutil.copyfile(args.source, source_copy)  # preserve source, per project brief section 11
            ffmpeg = FFmpegAdapter()  # kept for .version() reporting below

            if args.transcode:
                transcoded_path = os.path.join(proj_dir, "media", f"{basename}.{args.transcode}")
                run_tool("ffmpeg_transcode", CALLER_ID, src_path=source_copy, dst_path=transcoded_path)
                log.info(f"transcoded via tool contract 'ffmpeg_transcode' -> {transcoded_path}")

            if args.thumbnail:
                thumbnail_path = os.path.join(proj_dir, "textures", f"{basename}_thumb.png")
                run_tool("ffmpeg_extract_frame", CALLER_ID, src_path=source_copy,
                         dst_path=thumbnail_path, timestamp=args.thumbnail)
                log.info(f"extracted frame via tool contract 'ffmpeg_extract_frame' -> {thumbnail_path}")

        except (FFmpegAdapterError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError) as e:
            job_transition(job, FAILED, error=str(e))
            print(f"FFmpeg action failed: {e}", file=sys.stderr)
            log.error(str(e))
            return 1

        job = job_transition(job, PACKAGING)

        generated_files = [p for p in (transcoded_path, thumbnail_path) if p]
        print(f"Processed '{args.source}':")
        for f in generated_files:
            print(f"  - {f}")

        manifest = load_manifest(proj_dir)
        add_tool_used(manifest, "ffmpeg", version=ffmpeg.version())
        add_asset(manifest, basename, "media", source_files=[source_copy], generated_files=generated_files)
        save_manifest(proj_dir, manifest)
        for f in generated_files:
            log.record_file(f)

        graph = load_graph(proj_dir)
        source_id = graph.add_artifact(
            artifact_type="video_source", processor="ffmpeg_cli",
            output_path=source_copy, input_hash=hash_file(source_copy), validation_status=ART_PASS,
        )
        if transcoded_path:
            graph.add_artifact(
                artifact_type="video_transcoded", processor="ffmpeg_adapter", processor_version=ffmpeg.version(),
                parent_artifacts=[source_id], output_path=transcoded_path, validation_status=ART_PASS,
            )
        if thumbnail_path:
            graph.add_artifact(
                artifact_type="texture_png", processor="ffmpeg_adapter", processor_version=ffmpeg.version(),
                parent_artifacts=[source_id], output_path=thumbnail_path, validation_status=ART_PASS,
                metadata={"extracted_at": args.thumbnail},
            )
        save_graph(proj_dir, graph)
        log.info(f"artifact graph: video_source {source_id} -> "
                 f"{'video_transcoded ' if transcoded_path else ''}"
                 f"{'texture_png' if thumbnail_path else ''}".strip())

        job_transition(job, READY, result_summary={"generated_files": generated_files})
        log.info(f"job {job['job_id']}: READY")

        return 0


def cmd_enqueue(args):
    """Adds a real, persisted queue item (master spec's job_queue) rather
    than running it immediately. The downstream command is parsed through
    the real argument parser (build_parser()) so it round-trips through
    orchestrator.argv_utils.reconstruct_argv exactly like a Job's or
    PipelineRun stage's args do — never a loosely-typed guess at what the
    command needs."""
    with OperationLog("enqueue", args=vars(args)) as log:
        if not args.downstream:
            print("Nothing to enqueue — pass a command after the project name, e.g.:\n"
                  "  enqueue <project> -- validate <project> --profile 60fps_standard", file=sys.stderr)
            return 1

        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        try:
            downstream_args = build_parser().parse_args(args.downstream)
        except SystemExit:
            print(f"Could not parse downstream command: {' '.join(args.downstream)}", file=sys.stderr)
            return 1

        command = args.downstream[0]
        # "func" and "command" are argparse's own bookkeeping (the latter
        # is the subparsers' dest=) — not real flags, must never be
        # replayed as --command <name> by reconstruct_argv.
        downstream_dict = {k: v for k, v in vars(downstream_args).items() if k not in ("func", "command")}
        item = queue_enqueue(proj_dir, command, downstream_dict,
                              not_before=args.not_before, priority=args.priority)

        detail = f" (priority={args.priority}"
        detail += f", not before {args.not_before})" if args.not_before else ")"
        print(f"Enqueued {item['queue_id'][:8]}: {command}{detail}")
        log.info(f"enqueued {item['queue_id']}: {command}")
        return 0


def cmd_queue(args):
    """Inspect or cancel items in a project's job queue."""
    with OperationLog("queue", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        if args.cancel:
            try:
                item = cancel_queue_item(proj_dir, args.cancel)
            except ValueError as e:
                print(str(e), file=sys.stderr)
                log.error(str(e))
                return 1
            print(f"Cancelled {item['queue_id'][:8]} ({item['command']})")
            return 0

        items = list_queue(proj_dir)
        if not items:
            print(f"Queue is empty for '{args.name}'.")
            return 0
        print(f"{len(items)} queued item(s) for '{args.name}':\n")
        print(f"{'ID':<10} {'COMMAND':<10} {'STATUS':<10} {'PRI':<4} {'NOT BEFORE':<22} ENQUEUED")
        for i in items:
            print(f"{i['queue_id'][:8]:<10} {i['command']:<10} {i['status']:<10} "
                  f"{i['priority']:<4} {i['not_before'] or '-':<22} {i['enqueued_at']}")
        return 0


def cmd_work(args):
    """The worker/scheduler: drains eligible items from the queue one at
    a time (sequential, not concurrent — see orchestrator/job_queue.py's
    docstring) through the real CLI dispatch, same as pipeline_manager."""
    with OperationLog("work", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        ran = drain_queue(proj_dir, run_stage_fn=main, max_items=args.max_items)
        if not ran:
            print("Nothing eligible to run right now (queue empty, or remaining items aren't due yet).")
            return 0

        print(f"Ran {len(ran)} item(s):\n")
        for item in ran:
            print(f"  [{item['status']:<8}] {item['command']} (exit={item['exit_code']})")
        log.info(f"drained {len(ran)} queue item(s)")

        return 0 if not any(i["status"] == QUEUE_FAILED for i in ran) else 1


def cmd_pipeline(args):
    """Runs a named multi-stage pipeline (master spec's pipeline_manager
    + stage_runner). Only one real pipeline is defined today —
    validate_then_repair — rather than a generic templating DSL built
    ahead of a second real use case. Each stage is dispatched through the
    real CLI (main()), so it creates its own genuine Job exactly as if
    run by hand; this command only sequences them and records the
    stage-level outcome."""
    with OperationLog("pipeline", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        if args.template == VALIDATE_THEN_REPAIR:
            stages = build_validate_then_repair_stages(
                args.name, args.profile, merge_group=args.merge_group,
                asset_name=args.asset_name, blend_file=args.blend_file,
            )
        else:
            print(f"Unknown pipeline template: '{args.template}'", file=sys.stderr)
            return 1

        log.info(f"running pipeline '{args.template}' ({len(stages)} stage(s))")
        run = run_pipeline(proj_dir, args.template, stages, run_stage_fn=main)

        print(f"Pipeline '{run['pipeline_name']}' ({run['run_id'][:8]}): {run['status']}\n")
        for stage in run["stages"]:
            print(f"  [{stage['status']:<8}] {stage['command']} (exit={stage['exit_code']})")
        log.info(f"pipeline {run['run_id']}: {run['status']}")

        return 0 if run["status"] == PIPELINE_PASSED else 1


def cmd_pipelines(args):
    """Inspect a project's pipeline runs — list them, or show one run's
    full per-stage detail. Mirrors the `jobs` command's UX."""
    with OperationLog("pipelines", args=vars(args)):
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        if args.run_id:
            run = get_pipeline_run(proj_dir, args.run_id)
            if run is None:
                print(f"No pipeline run found with id prefix '{args.run_id}'", file=sys.stderr)
                return 1
            print(f"Pipeline run {run['run_id']}")
            print(f"  pipeline: {run['pipeline_name']}")
            print(f"  status:   {run['status']}")
            print(f"  created:  {run['created_at']}")
            print(f"  updated:  {run['updated_at']}")
            print("  stages:")
            for stage in run["stages"]:
                print(f"    [{stage['index']}] {stage['command']:<10} {stage['status']:<8} exit={stage['exit_code']}")
            return 0

        runs = list_pipeline_runs(proj_dir)
        if not runs:
            print(f"No pipeline runs yet for '{args.name}'. Run `pipeline` to create one.")
            return 0
        print(f"{len(runs)} pipeline run(s) for '{args.name}':\n")
        print(f"{'ID':<10} {'PIPELINE':<22} {'STATUS':<10} CREATED")
        for r in runs:
            print(f"{r['run_id'][:8]:<10} {r['pipeline_name']:<22} {r['status']:<10} {r['created_at']}")
        return 0


def cmd_validators(args):
    """Inspect the validation registry — the spec's 17 named validator
    types, honestly split into IMPLEMENTED (with the real entry point and
    what it actually checks) and UNSUPPORTED (with why). Master spec
    Rule 11: never let a caller assume a validator ran just because its
    name exists in the spec's diagram."""
    with OperationLog("validators", args=vars(args)):
        if args.validator_id:
            try:
                entry = get_validator(args.validator_id)
            except UnknownValidator as e:
                print(str(e), file=sys.stderr)
                return 1
            print(f"{entry.validator_id}: {entry.status}")
            if entry.status == VALIDATOR_IMPLEMENTED:
                print(f"  entry point: {entry.entry_point}")
                print("  covers:")
                for c in entry.covers:
                    print(f"    - {c}")
            else:
                print(f"  reason: {entry.reason}")
            return 0

        entries = list_validators()
        implemented = sorted(k for k, v in entries.items() if v.status == VALIDATOR_IMPLEMENTED)
        unsupported = sorted(k for k, v in entries.items() if v.status != VALIDATOR_IMPLEMENTED)
        print(f"{len(entries)} validator type(s) in the registry ({len(implemented)} implemented, "
              f"{len(unsupported)} unsupported):\n")
        print("IMPLEMENTED:")
        for vid in implemented:
            print(f"  {vid:<15} -> {entries[vid].entry_point}")
        print("\nUNSUPPORTED:")
        for vid in unsupported:
            print(f"  {vid:<15} -> {entries[vid].reason}")
        return 0


def _coerce_field_value(raw):
    """--field values arrive as strings; coerce to int/float where
    possible so required_metadata type checks (e.g. "seats": int) can
    actually pass for a value typed as `--field seats=4` on a shell."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def cmd_product_types(args):
    """Inspect the product type registry (products/product_types.py) —
    which types exist, their required metadata schema, their required
    validators, and which of those validators are actually real vs still
    unsupported. Not project-scoped."""
    with OperationLog("product-types", args=vars(args)):
        if args.product_type:
            try:
                schema = get_product_type(args.product_type)
            except UnknownProductType as e:
                print(str(e), file=sys.stderr)
                return 1
            print(f"{schema.product_type}")
            print(f"  asset_backing: {schema.asset_backing or '(metadata-only)'}")
            print("  required_metadata:")
            for k, v in schema.required_metadata.items():
                print(f"    {k}: {v}")
            print(f"  required_validators: {schema.required_validators or '(none)'}")
            unsupported = unsupported_validators(args.product_type)
            if unsupported:
                print(f"  NOTE: not yet real for this type: {unsupported}")
            print(f"  notes: {schema.notes}")
            return 0

        types = list_product_types()
        print(f"{len(types)} product type(s) registered:\n")
        for pt, schema in sorted(types.items()):
            unsupported = unsupported_validators(pt)
            backing = schema.asset_backing or "metadata-only"
            line = f"  {pt:<10} backing={backing:<14} validators={schema.required_validators or '(none)'}"
            if unsupported:
                line += f"  [unsupported: {unsupported}]"
            print(line)
        return 0


def cmd_register_product(args):
    """Registers a project as a formal product type (products/
    product_types.py) — real metadata-schema validation always, plus real
    asset validation (the same validate_blend/validate_texture this
    codebase already has) when the type has an asset backing and
    --asset-file is given. Refuses to register (never persists) if
    metadata is invalid or the backing asset fails its required validator
    — a declared product type is a checkable contract, not a label."""
    with OperationLog("register-product", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        try:
            schema = get_product_type(args.product_type)
        except UnknownProductType as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        if args.asset_file and not os.path.isfile(args.asset_file):
            print(f"Asset file not found: {args.asset_file}", file=sys.stderr)
            log.error(f"asset file not found: {args.asset_file}")
            return 1

        metadata = {}
        for raw in args.field or []:
            if "=" not in raw:
                print(f"--field must be key=value, got: {raw!r}", file=sys.stderr)
                return 1
            key, _, value = raw.partition("=")
            metadata[key] = _coerce_field_value(value)

        job = create_job(proj_dir, "register-product", {
            "name": args.name, "product_type": args.product_type,
            "asset_file": args.asset_file, "profile": args.profile, "asset_name": args.asset_name,
        })
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        try:
            validate_product_metadata(args.product_type, metadata)
        except ProductMetadataError as e:
            job_transition(job, FAILED, error=str(e))
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1
        print(f"Metadata OK for product type '{args.product_type}': {metadata}")

        unsupported = unsupported_validators(args.product_type)
        if unsupported:
            print(f"NOTE: {unsupported} required by this type but not yet implemented in "
                  f"validation_registry — not enforced here, see the 'validators' command")

        # Always pass through VALIDATING before READY, even when no asset
        # is checked (metadata-only registration, or no --asset-file
        # given yet) — RUNNING cannot transition directly to READY.
        job = job_transition(job, VALIDATING)

        if args.asset_file and schema.asset_backing == "blend":
            try:
                report = run_tool("validate_blend", CALLER_ID, blend_path=args.asset_file,
                                   profile_name=args.profile, asset_name=args.asset_name)
            except (BlenderBridgeError, ToolNotFound, UnsupportedCapability,
                    PermissionDenied, SchemaValidationError) as e:
                job_transition(job, FAILED, error=str(e))
                print(f"Asset validation failed to run: {e}", file=sys.stderr)
                log.error(str(e))
                return 1
            _print_report(report)
            _record_validation(proj_dir, args.asset_file, report, log)
            if report["result"] != "PASS":
                job_transition(job, FAILED, error="backing asset failed validation")
                print("Refusing to register: backing asset failed validation.", file=sys.stderr)
                return 1

        elif args.asset_file and schema.asset_backing == "texture":
            try:
                result = validate_texture(
                    args.asset_file,
                    min_width=metadata.get("resolution_width"),
                    min_height=metadata.get("resolution_height"),
                    require_seamless=(args.product_type == "building_skin"),
                )
            except (ImageMagickAdapterError, FileNotFoundError) as e:
                job_transition(job, FAILED, error=str(e))
                print(f"Texture validation failed to run: {e}", file=sys.stderr)
                log.error(str(e))
                return 1
            print(result.report())
            if not result.passed:
                job_transition(job, FAILED, error="backing texture failed validation")
                print("Refusing to register: backing texture failed validation.", file=sys.stderr)
                return 1

            graph = load_graph(proj_dir)
            graph.add_artifact(
                artifact_type="texture_raster", processor="texture_validator",
                output_path=args.asset_file, input_hash=hash_file(args.asset_file),
                validation_status=ART_PASS, metadata={"product_type": args.product_type},
            )
            save_graph(proj_dir, graph)
            log.info(f"artifact graph: texture_raster <- product_type '{args.product_type}'")

        elif args.asset_file and schema.asset_backing == "audio":
            try:
                result = validate_audio(
                    args.asset_file,
                    max_duration=metadata.get("max_duration_seconds"),
                )
            except (FFmpegAdapterError, FileNotFoundError) as e:
                job_transition(job, FAILED, error=str(e))
                print(f"Audio validation failed to run: {e}", file=sys.stderr)
                log.error(str(e))
                return 1
            print(result.report())
            if not result.passed:
                job_transition(job, FAILED, error="backing audio failed validation")
                print("Refusing to register: backing audio failed validation.", file=sys.stderr)
                return 1

            graph = load_graph(proj_dir)
            graph.add_artifact(
                artifact_type="audio_source", processor="audio_validator",
                output_path=args.asset_file, input_hash=hash_file(args.asset_file),
                validation_status=ART_PASS, metadata={"product_type": args.product_type},
            )
            save_graph(proj_dir, graph)
            log.info(f"artifact graph: audio_source <- product_type '{args.product_type}'")

        manifest = load_manifest(proj_dir)
        set_product_type(manifest, args.product_type, metadata)
        save_manifest(proj_dir, manifest)

        job_transition(job, READY, result_summary={"product_type": args.product_type})
        log.info(f"job {job['job_id']}: READY — registered as '{args.product_type}'")
        print(f"\nRegistered '{args.name}' as product type '{args.product_type}'.")
        return 0


def cmd_package(args):
    """Compiles + packages + signs a real release (master spec's
    compiler -> packaging -> signing pipeline). Refuses — never fakes a
    release — if the project has no registered product type
    (`register-product` first) or no currently-PASSing artifacts to
    compile. Genuine PACKAGING -> SIGNING -> READY job-state transitions,
    both real now (see orchestrator/build_state.py)."""
    with OperationLog("package", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            log.error(f"no such project: {args.name}")
            return 1

        job = create_job(proj_dir, "package", {"name": args.name, "version": args.version})
        job = job_transition(job, RUNNING)
        log.info(f"job {job['job_id']}: RUNNING")

        job = job_transition(job, PACKAGING)
        try:
            compiled = compile_product(proj_dir)
        except CompilerError as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Compile failed: {e}", file=sys.stderr)
            log.error(str(e))
            manifest = load_manifest(proj_dir)
            add_error(manifest, str(e))
            save_manifest(proj_dir, manifest)
            return 1
        print(f"Compiled '{compiled['source_project']}' as product type '{compiled['product_type']}': "
              f"{len(compiled['artifacts'])} artifact(s)")

        try:
            package = build_package(proj_dir, compiled, version=args.version)
        except PackagingError as e:
            job_transition(job, FAILED, error=str(e))
            print(f"Packaging failed: {e}", file=sys.stderr)
            log.error(str(e))
            manifest = load_manifest(proj_dir)
            add_error(manifest, str(e))
            save_manifest(proj_dir, manifest)
            return 1
        print(f"Packaged -> {package['package_dir']} (version {package['version']})")
        log.record_file(package["manifest_path"])

        job = job_transition(job, SIGNING)
        with open(package["manifest_path"], "rb") as f:
            manifest_bytes = f.read()
        signature = sign_bytes(manifest_bytes)
        sig_path = package["manifest_path"] + ".sig"
        with open(sig_path, "wb") as f:
            f.write(signature)
        log.record_file(sig_path)
        print(f"Signed -> {sig_path}")

        graph = load_graph(proj_dir)
        package_id = graph.add_artifact(
            artifact_type="release_package", processor="package_builder",
            parent_artifacts=[a["artifact_id"] for a in compiled["artifacts"]],
            output_path=package["manifest_path"], input_hash=package["package_hash"],
            validation_status=ART_PASS,
            metadata={"version": package["version"], "product_type": compiled["product_type"]},
        )
        save_graph(proj_dir, graph)
        log.info(f"artifact {package_id} (release_package) version {package['version']}")

        manifest = load_manifest(proj_dir)
        add_export(manifest, asset_name=compiled["source_project"], fmt="release_package",
                   path=package["manifest_path"])
        save_manifest(proj_dir, manifest)

        job_transition(job, READY, result_summary={
            "version": package["version"], "package_dir": package["package_dir"],
        })
        log.info(f"job {job['job_id']}: READY")
        print(f"\nRelease {package['version']} ready: {package['package_dir']}")
        return 0


def cmd_releases(args):
    """Inspect a project's built releases — list them, or show one
    version's full manifest plus real Ed25519 signature verification
    (never assumed valid just because a .sig file exists)."""
    with OperationLog("releases", args=vars(args)):
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        if args.version:
            manifest_path = os.path.join(proj_dir, "releases", args.version, PACKAGE_MANIFEST_FILENAME)
            if not os.path.isfile(manifest_path):
                print(f"No release version '{args.version}' found", file=sys.stderr)
                return 1
            manifest = load_release_manifest(manifest_path)
            print(f"Release {manifest['version']} — product_type={manifest['product_type']}")
            print(f"  packaged_at:   {manifest['packaged_at']}")
            print(f"  package_hash:  {manifest['package_hash']}")
            print("  files:")
            for f in manifest["files"]:
                print(f"    {f['relative_path']}  ({f['artifact_type']}, {f['hash'][:12]}...)")

            sig_path = manifest_path + ".sig"
            if os.path.isfile(sig_path):
                with open(sig_path, "rb") as fh:
                    signature = fh.read()
                with open(manifest_path, "rb") as fh:
                    manifest_bytes = fh.read()
                verified = verify_signature(manifest_bytes, signature)
                print(f"  signature:     {'VALID' if verified else 'INVALID'}")
            else:
                print("  signature:     (none found)")
            return 0

        releases = list_releases(proj_dir)
        if not releases:
            print(f"No releases yet for '{args.name}'. Run `package` to create one.")
            return 0
        print(f"{len(releases)} release(s) for '{args.name}':\n")
        for r in releases:
            print(f"  v{r['version']:<6} {r['product_type']:<14} {len(r['files'])} file(s)  {r['packaged_at']}")
        return 0


def cmd_jobs(args):
    """Inspect a project's job records — proves job tracking is a real,
    queryable system of record, not just internal bookkeeping nobody can
    see. Mirrors the `graph` command's UX."""
    with OperationLog("jobs", args=vars(args)):
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        if args.job_id:
            job = get_job(proj_dir, args.job_id)
            if job is None:
                print(f"No job found with id prefix '{args.job_id}'", file=sys.stderr)
                return 1
            print(f"Job {job['job_id']}")
            print(f"  command: {job['command']}")
            print(f"  state:   {job['state']}")
            print(f"  args:    {job['args']}")
            print(f"  created: {job['created_at']}")
            print(f"  updated: {job['updated_at']}")
            if job.get("error"):
                print(f"  error:   {job['error']}")
            if job.get("result_summary"):
                print(f"  result:  {job['result_summary']}")
            print("  history:")
            for h in job["history"]:
                print(f"    {h['timestamp']}  {h['state']}")
            return 0

        jobs = list_jobs(proj_dir)
        if not jobs:
            print(f"No jobs yet for '{args.name}'. Run validate/optimize/process to create some.")
            return 0
        print(f"{len(jobs)} job(s) for '{args.name}':\n")
        print(f"{'ID':<10} {'COMMAND':<10} {'STATE':<12} CREATED")
        for j in jobs:
            print(f"{j['job_id'][:8]:<10} {j['command']:<10} {j['state']:<12} {j['created_at']}")
        return 0


def _resume_job_once(job, log):
    """The actual re-entry of a single FAILED job: reconstructs the
    original argv from its stored command+args and re-invokes it, rather
    than a stub. The old job is closed out (READY/FAILED) based on the
    replay's outcome; the replay itself creates its own fresh job
    record, since cmd_validate/cmd_optimize/cmd_process each track their
    own run. Shared by cmd_resume (one attempt) and cmd_retry (this,
    looped by orchestrator.retry_manager)."""
    job = job_transition(job, RUNNING)
    log.info(f"job {job['job_id']}: resuming ({job['command']}), FAILED -> RUNNING")

    argv = reconstruct_argv(job["command"], job["args"])
    print(f"Resuming job {job['job_id'][:8]}: {' '.join(argv)}")

    try:
        sub_args = build_parser().parse_args(argv)
    except SystemExit:
        job_transition(job, FAILED, error="failed to reconstruct original command for resume")
        print("Could not reconstruct the original command from stored job args.", file=sys.stderr)
        return 1

    exit_code = sub_args.func(sub_args)
    if exit_code == 0:
        job_transition(job, READY, result_summary={"resumed": True})
    else:
        job_transition(job, FAILED, error="resumed command exited non-zero")
    return exit_code


def cmd_resume(args):
    """Genuinely re-enters a FAILED job — a single attempt. See `retry`
    for a bounded multi-attempt version of this same mechanism."""
    with OperationLog("resume", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        if args.job_id:
            job = get_job(proj_dir, args.job_id)
            if job is None:
                print(f"No job found with id prefix '{args.job_id}'", file=sys.stderr)
                return 1
        else:
            job = find_resumable(proj_dir)
            if job is None:
                print(f"No FAILED job to resume for '{args.name}'.", file=sys.stderr)
                return 1

        if job["state"] != FAILED:
            print(f"Job {job['job_id']} is in state {job['state']}, not FAILED — nothing to resume.", file=sys.stderr)
            return 1

        return _resume_job_once(job, log)


def cmd_retry(args):
    """Bounded checkpoint-based retry (master spec section 25): calls the
    same real resume mechanism as `resume` repeatedly — up to
    --max-attempts times — against whatever is currently the resumable
    FAILED job, stopping at the first success. Does not add a new
    checkpoint format; it only loops the existing one. See
    orchestrator/retry_manager.py for exactly when it gives up."""
    with OperationLog("retry", args=vars(args)) as log:
        proj_dir = project_dir_for(args.name)
        if not os.path.isdir(proj_dir):
            print(f"No such project: {args.name}", file=sys.stderr)
            return 1

        try:
            outcome = retry_job(
                proj_dir, lambda job: _resume_job_once(job, log),
                job_id=args.job_id, max_attempts=args.max_attempts, backoff_seconds=args.backoff_seconds,
            )
        except RetryExhausted as e:
            print(str(e), file=sys.stderr)
            log.error(str(e))
            return 1

        for a in outcome["attempts"]:
            print(f"  attempt #{a['attempt']}: job {a['job_id'][:8]} -> exit {a['exit_code']}")
        if outcome["succeeded"]:
            print(f"Succeeded after {len(outcome['attempts'])} attempt(s).")
            return 0
        print(f"Retry exhausted after {len(outcome['attempts'])} attempt(s), still failing.", file=sys.stderr)
        return 1


def _not_implemented(command):
    def handler(args):
        reason = NOT_YET_IMPLEMENTED.get(command, "a later phase")
        print(f"'{command}' is not implemented yet — planned for {reason}.", file=sys.stderr)
        print("See ROADMAP.md in the project root for the build order.", file=sys.stderr)
        return 2
    return handler


def build_parser():
    parser = argparse.ArgumentParser(prog="asset-factory", description="Universal Asset Factory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="Check which required/optional tools are installed")
    p_doctor.set_defaults(func=cmd_doctor)

    p_capabilities = sub.add_parser("capabilities", help="Registry-shaped, persistable view of tool capabilities (not project-scoped)")
    p_capabilities.add_argument("--record", action="store_true", help="Append this snapshot to logs/capability_snapshots.jsonl")
    p_capabilities.add_argument("--history", action="store_true", help="Show recently recorded snapshots instead of a fresh one")
    p_capabilities.add_argument("--limit", type=int, default=20, help="Max snapshots to show with --history")
    p_capabilities.set_defaults(func=cmd_capabilities)

    p_create = sub.add_parser("create", help="Create a new project workspace (skeleton + manifest only in Phase 1)")
    p_create.add_argument("name", help="Project name, e.g. \"Rust casino monument\"")
    p_create.add_argument("--type", default="generic", help="Project type tag stored in the manifest")
    p_create.add_argument("--dry-run", action="store_true", help="Print what would be created without creating it")
    p_create.set_defaults(func=cmd_create)

    p_status = sub.add_parser("status", help="List projects, or show one project's manifest summary")
    p_status.add_argument("name", nargs="?", default=None)
    p_status.set_defaults(func=cmd_status)

    p_logs = sub.add_parser("logs", help="List recent operation log files")
    p_logs.add_argument("--limit", type=int, default=20)
    p_logs.set_defaults(func=cmd_logs)

    p_telemetry = sub.add_parser("telemetry", help="Aggregate real counts/success-rates/durations across every operation log (not project-scoped)")
    p_telemetry.add_argument("--command", default=None, help="Only summarize this command instead of all of them")
    p_telemetry.set_defaults(func=cmd_telemetry)

    p_validate = sub.add_parser("validate", help="Run the KOBA performance validator against a project's Blender asset")
    p_validate.add_argument("name", help="Project name")
    p_validate.add_argument("--profile", default="60fps_standard", help="Performance profile (see config/performance_profiles.py in the Blender adapter)")
    p_validate.add_argument("--blend-file", default=None, help="Override: validate this exact .blend instead of auto-finding one")
    p_validate.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection to validate, if the file has more than one")
    p_validate.add_argument("--optimized", action="store_true", help="Prefer the optimized/ copy over blender/ (source) if both exist")
    p_validate.set_defaults(func=cmd_validate)

    p_optimize = sub.add_parser("optimize", help="Assign culling distances (+ optionally merge a group) into a new optimized/ copy")
    p_optimize.add_argument("name", help="Project name")
    p_optimize.add_argument("--profile", default="60fps_standard", help="Performance profile used for the before/after comparison")
    p_optimize.add_argument("--blend-file", default=None, help="Override: optimize this exact .blend (always reads from blender/ source, never optimized/)")
    p_optimize.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection to optimize, if the file has more than one")
    p_optimize.add_argument("--merge-group", default=None, help="Also merge this visibility_group's mergeable objects into one mesh")
    p_optimize.add_argument("--output", default=None, help="Override output path (default: projects/<name>/optimized/<same filename>)")
    p_optimize.set_defaults(func=cmd_optimize)

    p_process = sub.add_parser("process", help="Export an SVG to PNG variants (+ optional format conversion) into a project's textures/")
    p_process.add_argument("name", help="Project name")
    p_process.add_argument("--svg", required=True, help="Path to the source SVG file")
    p_process.add_argument("--sizes", default="128,256,512", help="Comma-separated PNG widths to export")
    p_process.add_argument("--format", default="png", help="Also convert each PNG variant to this format via ImageMagick (e.g. webp)")
    p_process.add_argument("--basename", default=None, help="Output filename stem (default: the SVG's own filename)")
    p_process.set_defaults(func=cmd_process)

    p_krita = sub.add_parser("krita", help="Export a Krita document (.kra or anything Krita can open) to a raster format into a project's textures/")
    p_krita.add_argument("name", help="Project name")
    p_krita.add_argument("--source", required=True, help="Path to the source Krita document (or other Krita-openable file)")
    p_krita.add_argument("--format", default="png", help="Output raster format, inferred from this extension (e.g. png, jpg)")
    p_krita.add_argument("--basename", default=None, help="Output filename stem (default: the source file's own filename)")
    p_krita.set_defaults(func=cmd_krita)

    p_gimp = sub.add_parser("gimp", help="Export a GIMP document (.xcf or anything GIMP can open) to a raster format into a project's textures/")
    p_gimp.add_argument("name", help="Project name")
    p_gimp.add_argument("--source", required=True, help="Path to the source GIMP document (or other GIMP-openable file)")
    p_gimp.add_argument("--format", default="png", help="Output raster format, inferred from this extension (e.g. png, jpg)")
    p_gimp.add_argument("--basename", default=None, help="Output filename stem (default: the source file's own filename)")
    p_gimp.set_defaults(func=cmd_gimp)

    p_ffmpeg = sub.add_parser("ffmpeg", help="Transcode and/or extract a thumbnail frame from a video/audio source")
    p_ffmpeg.add_argument("name", help="Project name")
    p_ffmpeg.add_argument("--source", required=True, help="Path to the source video/audio file")
    p_ffmpeg.add_argument("--transcode", default=None, help="Transcode to this format (e.g. webm) into a project's media/")
    p_ffmpeg.add_argument("--thumbnail", default=None, help="Extract a still frame at this timestamp (e.g. 00:00:01) into a project's textures/")
    p_ffmpeg.add_argument("--basename", default=None, help="Output filename stem (default: the source file's own filename)")
    p_ffmpeg.set_defaults(func=cmd_ffmpeg)

    p_agent = sub.add_parser("agent", help="Ask the blender_agent (AI router -> tool contract) to validate or optimize an asset from a natural-language instruction")
    p_agent.add_argument("name", help="Project name")
    p_agent.add_argument("--instruction", required=True, help="Natural-language instruction, e.g. \"check if this passes 60fps\" or \"optimize this and merge crates\"")
    p_agent.add_argument("--profile", default="60fps_standard", help="Performance profile passed through to whichever tool the AI decides to call")
    p_agent.add_argument("--blend-file", default=None, help="Override: use this exact .blend instead of auto-finding one")
    p_agent.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection, if the file has more than one")
    p_agent.add_argument("--merge-group", default=None, help="Passed through if the AI decides to optimize")
    p_agent.add_argument("--output", default=None, help="Override output path if the AI decides to optimize")
    p_agent.set_defaults(func=cmd_agent)

    p_repair = sub.add_parser("repair", help="Diagnose a FAILing asset and attempt the one real repair strategy (merge a visibility_group), then revalidate")
    p_repair.add_argument("name", help="Project name")
    p_repair.add_argument("--profile", default="60fps_standard", help="Performance profile to diagnose/revalidate against")
    p_repair.add_argument("--blend-file", default=None, help="Override: diagnose this exact .blend instead of auto-finding one")
    p_repair.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection, if the file has more than one")
    p_repair.add_argument("--merge-group", default=None, help="visibility_group to merge if the failure is entity_count/unique_meshes-fixable — required for that strategy, never guessed")
    p_repair.add_argument("--max-attempts", type=int, default=1, help="For decimate-fixable failures only: retry with a progressively tighter ratio up to this many times if a prior attempt still fails on the same metric (default 1 = today's single-attempt behavior). Merge-fixable failures never retry, since merging is deterministic.")
    p_repair.set_defaults(func=cmd_repair)

    p_repair_agent = sub.add_parser("repair-agent", help="The second real agent: AI router decides whether/how to repair from a natural-language instruction")
    p_repair_agent.add_argument("name", help="Project name")
    p_repair_agent.add_argument("--instruction", required=True, help="Natural-language instruction, e.g. \"check this and merge the 'cluster' group if needed\"")
    p_repair_agent.add_argument("--profile", default="60fps_standard", help="Performance profile to diagnose/revalidate against")
    p_repair_agent.add_argument("--blend-file", default=None, help="Override: diagnose this exact .blend instead of auto-finding one")
    p_repair_agent.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection, if the file has more than one")
    p_repair_agent.set_defaults(func=cmd_repair_agent)

    p_graph = sub.add_parser("graph", help="Inspect a project's artifact graph — list artifacts, or show lineage/affected for one")
    p_graph.add_argument("name", help="Project name")
    p_graph.add_argument("--lineage", default=None, help="Show the ancestor chain of this artifact id (prefix match)")
    p_graph.add_argument("--affected", default=None, help="Show what would need rebuilding if this artifact id changed (prefix match)")
    p_graph.set_defaults(func=cmd_graph)

    p_cache = sub.add_parser("cache", help="Inspect a project's content-addressed artifact store — object counts/bytes, and cache-hit history")
    p_cache.add_argument("name", help="Project name")
    p_cache.add_argument("--entries", action="store_true", help="Also list every recorded cache entry, not just summary stats")
    p_cache.set_defaults(func=cmd_cache)

    p_validators = sub.add_parser("validators", help="Inspect the validation registry — which validator types are real vs. unsupported (not project-scoped)")
    p_validators.add_argument("--validator-id", default=None, help="Show this validator type's full detail instead of listing all")
    p_validators.set_defaults(func=cmd_validators)

    p_product_types = sub.add_parser("product-types", help="Inspect the product type registry — required metadata/validators per type (not project-scoped)")
    p_product_types.add_argument("--product-type", default=None, help="Show this product type's full schema instead of listing all")
    p_product_types.set_defaults(func=cmd_product_types)

    p_register_product = sub.add_parser("register-product", help="Register a project as a formal product type (cui/monument/vehicle/npc/event), with real metadata + asset validation")
    p_register_product.add_argument("name", help="Project name")
    p_register_product.add_argument("--product-type", required=True, choices=sorted(list_product_types().keys()), help="Which product type to register as")
    p_register_product.add_argument("--field", action="append", default=[], help="A metadata field as key=value — repeat for multiple fields")
    p_register_product.add_argument("--asset-file", default=None, help="The real asset backing this product (a .blend for monument/vehicle, an image for cui) — validated against the type's required validators")
    p_register_product.add_argument("--profile", default="60fps_standard", help="Performance profile, used only when the backing asset is a .blend")
    p_register_product.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection, if the .blend has more than one")
    p_register_product.set_defaults(func=cmd_register_product)

    p_package = sub.add_parser("package", help="Compile + package + sign a real release from the project's currently-PASSing artifacts")
    p_package.add_argument("name", help="Project name")
    p_package.add_argument("--version", default=None, help="Release version label (default: auto-incrementing integer)")
    p_package.set_defaults(func=cmd_package)

    p_releases = sub.add_parser("releases", help="Inspect a project's built releases — list them, or show one version's manifest + signature verification")
    p_releases.add_argument("name", help="Project name")
    p_releases.add_argument("--version", default=None, help="Show this release version in full, instead of listing all")
    p_releases.set_defaults(func=cmd_releases)

    p_pipeline = sub.add_parser("pipeline", help="Run a named multi-stage pipeline (e.g. validate_then_repair)")
    p_pipeline.add_argument("name", help="Project name")
    p_pipeline.add_argument("--template", default=VALIDATE_THEN_REPAIR, choices=[VALIDATE_THEN_REPAIR], help="Which pipeline to run")
    p_pipeline.add_argument("--profile", default="60fps_standard", help="Performance profile used by every stage")
    p_pipeline.add_argument("--merge-group", default=None, help="Passed to the repair stage if the validate stage FAILs on entity_count/unique_meshes")
    p_pipeline.add_argument("--asset-name", default=None, help="Which ASSET_<name> collection, if the file has more than one")
    p_pipeline.add_argument("--blend-file", default=None, help="Override: use this exact .blend instead of auto-finding one")
    p_pipeline.set_defaults(func=cmd_pipeline)

    p_pipelines = sub.add_parser("pipelines", help="Inspect a project's pipeline runs — list them, or show one run's full per-stage detail")
    p_pipelines.add_argument("name", help="Project name")
    p_pipelines.add_argument("--run-id", default=None, help="Show this pipeline run id (prefix match) in full, instead of listing all")
    p_pipelines.set_defaults(func=cmd_pipelines)

    p_enqueue = sub.add_parser("enqueue", help="Add a command to a project's job queue instead of running it immediately")
    p_enqueue.add_argument("name", help="Project name")
    p_enqueue.add_argument("--not-before", default=None, help="ISO timestamp — the item is ineligible to run until this real time has passed")
    p_enqueue.add_argument("--priority", type=int, default=0, help="Higher runs first among eligible items (ties broken by enqueue order)")
    p_enqueue.add_argument("downstream", nargs=argparse.REMAINDER, help="The command to run later, e.g.: validate <project> --profile 60fps_standard")
    p_enqueue.set_defaults(func=cmd_enqueue)

    p_queue = sub.add_parser("queue", help="Inspect or cancel items in a project's job queue")
    p_queue.add_argument("name", help="Project name")
    p_queue.add_argument("--cancel", default=None, help="Cancel this queue item id (prefix match) — only QUEUED items can be cancelled")
    p_queue.set_defaults(func=cmd_queue)

    p_work = sub.add_parser("work", help="Drain eligible items from a project's job queue, one at a time (sequential, not concurrent)")
    p_work.add_argument("name", help="Project name")
    p_work.add_argument("--max-items", type=int, default=None, help="Stop after running this many items (default: drain everything currently eligible)")
    p_work.set_defaults(func=cmd_work)

    p_jobs = sub.add_parser("jobs", help="Inspect a project's jobs — list them, or show one job's full history")
    p_jobs.add_argument("name", help="Project name")
    p_jobs.add_argument("--job-id", default=None, help="Show this job id (prefix match) in full, instead of listing all")
    p_jobs.set_defaults(func=cmd_jobs)

    p_resume = sub.add_parser("resume", help="Resume the most recent FAILED job for a project (or a specific --job-id)")
    p_resume.add_argument("name", help="Project name")
    p_resume.add_argument("--job-id", default=None, help="Resume this job id (prefix match) instead of the most recent FAILED one")
    p_resume.set_defaults(func=cmd_resume)

    p_retry = sub.add_parser("retry", help="Checkpoint-based retry: calls `resume`'s mechanism repeatedly (bounded) until it succeeds or attempts run out")
    p_retry.add_argument("name", help="Project name")
    p_retry.add_argument("--job-id", default=None, help="Start from this job id (prefix match) instead of the most recent FAILED one")
    p_retry.add_argument("--max-attempts", type=int, default=3, help="Give up after this many attempts (default 3)")
    p_retry.add_argument("--backoff-seconds", type=float, default=0, help="Sleep this long between attempts (default 0)")
    p_retry.set_defaults(func=cmd_retry)

    for command in ("create-pack", "render",
                     "animate", "export", "preview", "marketplace",
                     "batch"):
        p = sub.add_parser(command, help=f"(not implemented yet — {NOT_YET_IMPLEMENTED[command]})")
        p.add_argument("args", nargs=argparse.REMAINDER)
        p.set_defaults(func=_not_implemented(command))

    return parser


def _dispatch_enqueue(rest):
    """argparse.REMAINDER has a well-known footgun: mixed with other
    optional flags on the same parser, it can swallow flags meant for
    THIS command into the remainder depending on argv ordering (confirmed
    by direct testing — `--not-before X -- validate ...` after the
    project name silently failed to parse). Handled here instead: find
    the `--` separator ourselves, parse only the prefix (name,
    --not-before, --priority) with a small dedicated parser that never
    sees the downstream tokens, so there's no ordering ambiguity."""
    if "--" not in rest:
        print("enqueue requires a '--' separator before the downstream command, e.g.:\n"
              "  enqueue <project> [--not-before TS] [--priority N] -- <command> ...", file=sys.stderr)
        return 1
    sep = rest.index("--")
    prefix, downstream = rest[:sep], rest[sep + 1:]

    prefix_parser = argparse.ArgumentParser(prog="asset-factory enqueue", add_help=False)
    prefix_parser.add_argument("name")
    prefix_parser.add_argument("--not-before", dest="not_before", default=None)
    prefix_parser.add_argument("--priority", type=int, default=0)
    try:
        prefix_args = prefix_parser.parse_args(prefix)
    except SystemExit:
        print(f"Could not parse enqueue arguments: {' '.join(prefix)}", file=sys.stderr)
        return 1

    prefix_args.downstream = downstream
    return cmd_enqueue(prefix_args)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "enqueue":
        return _dispatch_enqueue(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

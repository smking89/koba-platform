"""Pipeline Manager + Stage Runner (master spec's `orchestrator/
pipeline_manager`, `pipeline_registry`, `stage_runner`).

Scope honesty: this sequences REAL CLI command invocations one after
another in the same process — no concurrency, no async workers, no
separate scheduler. That matches orchestrator/job.py's own documented
scope (synchronous tracking, not async orchestration) and avoids
fabricating a queue/worker system this codebase doesn't have.

A Pipeline is just an ordered list of Stages — {"command": <cli command
name>, "args": {...dest-name: value...}, "continue_on_failure": bool}.
That's the exact shape orchestrator.job.py already persists per-command,
which is what lets run_pipeline() reuse cli.main.main() (via
orchestrator.argv_utils.reconstruct_argv) to actually execute each stage
instead of re-implementing validate/optimize/repair dispatch a second
time. Each stage still creates its own real Job (see orchestrator/job.py)
exactly as if it had been run by hand — a PipelineRun only ties a
sequence of those together and records stage-level outcome.

A PipelineRun is persisted the same way a Job is: one JSON record per
run, in projects/<name>/pipelines/<run_id>/pipeline_run.json. Stopping at
the first failing stage is the default; a stage may set
"continue_on_failure": True to keep going anyway (e.g. a `validate` stage
that's *expected* to FAIL before a `repair` stage runs).
"""
import datetime
import json
import os
import uuid

PIPELINE_RUN_FILENAME = "pipeline_run.json"

PENDING = "PENDING"
RUNNING = "RUNNING"
PASSED = "PASSED"
FAILED = "FAILED"
SKIPPED = "SKIPPED"

# The one real named pipeline this codebase defines today (master spec's
# pipeline_registry) — deliberately not a generic templating DSL until a
# second real use case actually needs one.
VALIDATE_THEN_REPAIR = "validate_then_repair"


def build_validate_then_repair_stages(name, profile, merge_group=None, asset_name=None, blend_file=None):
    """The validate stage is expected to possibly FAIL (that's what
    triggers the repair stage) — continue_on_failure=True there. The
    repair stage's own failure is real and must stop the pipeline."""
    return [
        {
            "command": "validate",
            "args": {"name": name, "profile": profile, "asset_name": asset_name, "blend_file": blend_file},
            "continue_on_failure": True,
        },
        {
            "command": "repair",
            "args": {"name": name, "profile": profile, "merge_group": merge_group,
                     "asset_name": asset_name, "blend_file": blend_file},
            "continue_on_failure": False,
        },
    ]


def _pipelines_dir(proj_dir):
    return os.path.join(proj_dir, "pipelines")


def _save(workspace_dir, run):
    with open(os.path.join(workspace_dir, PIPELINE_RUN_FILENAME), "w") as f:
        json.dump(run, f, indent=2)
    return run


def create_pipeline_run(proj_dir, pipeline_name, stages):
    run_id = str(uuid.uuid4())
    workspace_dir = os.path.join(_pipelines_dir(proj_dir), run_id)
    os.makedirs(workspace_dir, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run = {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "created_at": now,
        "updated_at": now,
        "status": PENDING,
        "workspace_dir": workspace_dir,
        "stages": [
            {
                "index": i, "command": s["command"], "args": s["args"],
                "continue_on_failure": s.get("continue_on_failure", False),
                "status": PENDING, "exit_code": None,
            }
            for i, s in enumerate(stages)
        ],
    }
    _save(workspace_dir, run)
    return run


def run_pipeline(proj_dir, pipeline_name, stages, run_stage_fn):
    """Executes each stage in order via `run_stage_fn(argv) -> exit_code`
    (the caller passes cli.main.main — kept as an injected function
    rather than imported directly here so this module has no import-time
    dependency on cli.main, avoiding a circular import since cli.main
    will import this module to expose the `pipeline` command). Stops at
    the first stage that fails unless that stage is marked
    continue_on_failure. Returns the final persisted PipelineRun record."""
    from orchestrator.argv_utils import reconstruct_argv

    run = create_pipeline_run(proj_dir, pipeline_name, stages)
    workspace_dir = run["workspace_dir"]
    run["status"] = RUNNING
    _save(workspace_dir, run)

    for stage in run["stages"]:
        stage["status"] = RUNNING
        _save(workspace_dir, run)

        argv = reconstruct_argv(stage["command"], stage["args"])
        exit_code = run_stage_fn(argv)

        stage["exit_code"] = exit_code
        stage["status"] = PASSED if exit_code == 0 else FAILED
        run["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _save(workspace_dir, run)

        if exit_code != 0 and not stage["continue_on_failure"]:
            for later in run["stages"]:
                if later["status"] == PENDING:
                    later["status"] = SKIPPED
            run["status"] = FAILED
            _save(workspace_dir, run)
            return run

    run["status"] = PASSED
    _save(workspace_dir, run)
    return run


def get_pipeline_run(proj_dir, run_id_prefix):
    """Prefix match, consistent with get_job()'s UX."""
    pipelines_dir = _pipelines_dir(proj_dir)
    if not os.path.isdir(pipelines_dir):
        return None
    for run_id in os.listdir(pipelines_dir):
        if run_id.startswith(run_id_prefix):
            path = os.path.join(pipelines_dir, run_id, PIPELINE_RUN_FILENAME)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    return json.load(f)
    return None


def list_pipeline_runs(proj_dir):
    pipelines_dir = _pipelines_dir(proj_dir)
    if not os.path.isdir(pipelines_dir):
        return []
    runs = []
    for run_id in os.listdir(pipelines_dir):
        path = os.path.join(pipelines_dir, run_id, PIPELINE_RUN_FILENAME)
        if os.path.isfile(path):
            with open(path, "r") as f:
                runs.append(json.load(f))
    return sorted(runs, key=lambda r: r["created_at"])

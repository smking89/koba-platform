"""Job records with isolated workspaces (master spec section 24) and a
real state machine (section 23) via orchestrator.build_state.

Scope honesty: this is synchronous job *tracking*, not the spec's full
async job_queue/job_scheduler/worker_manager — there is no queue, no
concurrent workers, no scheduler. Each CLI command that does real work
creates a Job, transitions it through states as it progresses, and
persists it — which is what makes checkpoint-based resume (section 25)
possible: if the process dies mid-command, the last-persisted state and
args survive on disk and `resume_job()` can re-enter from there. Building
genuine async orchestration is future work, not faked here.
"""
import datetime
import json
import os
import uuid

from capabilities.capability_registry import capture_snapshot
from orchestrator.build_state import CREATED, require_valid_transition

JOB_FILENAME = "job.json"


def _jobs_dir(proj_dir):
    return os.path.join(proj_dir, "jobs")


def create_job(proj_dir, command, args):
    """Creates an isolated workspace (projects/<name>/jobs/<job_id>/) and
    a job.json record in state CREATED. `args` must be JSON-serializable —
    it's what resume_job() replays.

    Stamps a real, fresh CapabilitySnapshot (master spec's structured-log
    field) at creation time — a genuine `core.detection` pass, never
    cached — so a job answers "what tools/versions were actually present
    when this ran" after the fact, not just live."""
    job_id = str(uuid.uuid4())
    workspace_dir = os.path.join(_jobs_dir(proj_dir), job_id)
    os.makedirs(workspace_dir, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "command": command,
        "args": args,
        "state": CREATED,
        "created_at": now,
        "updated_at": now,
        "workspace_dir": workspace_dir,
        "history": [{"state": CREATED, "timestamp": now}],
        "error": None,
        "result_summary": None,
        "capability_snapshot": capture_snapshot(),
    }
    _save(workspace_dir, job)
    return job


def _save(workspace_dir, job):
    with open(os.path.join(workspace_dir, JOB_FILENAME), "w") as f:
        json.dump(job, f, indent=2)
    return job


def transition(job, new_state, error=None, result_summary=None):
    """Validates and applies a state transition, persists it, returns the
    updated job dict. Raises orchestrator.build_state.InvalidTransition
    rather than silently allowing an impossible jump (e.g. CREATED
    straight to READY) — the whole point of a state machine is that not
    every transition is allowed."""
    require_valid_transition(job["state"], new_state)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    job["state"] = new_state
    job["updated_at"] = now
    job["history"].append({"state": new_state, "timestamp": now})
    if error is not None:
        job["error"] = error
    if result_summary is not None:
        job["result_summary"] = result_summary
    _save(job["workspace_dir"], job)
    return job


def get_job(proj_dir, job_id_prefix):
    """Prefix match, consistent with the `graph` CLI command's UX."""
    jobs_dir = _jobs_dir(proj_dir)
    if not os.path.isdir(jobs_dir):
        return None
    for job_id in os.listdir(jobs_dir):
        if job_id.startswith(job_id_prefix):
            path = os.path.join(jobs_dir, job_id, JOB_FILENAME)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    return json.load(f)
    return None


def list_jobs(proj_dir):
    jobs_dir = _jobs_dir(proj_dir)
    if not os.path.isdir(jobs_dir):
        return []
    jobs = []
    for job_id in os.listdir(jobs_dir):
        path = os.path.join(jobs_dir, job_id, JOB_FILENAME)
        if os.path.isfile(path):
            with open(path, "r") as f:
                jobs.append(json.load(f))
    return sorted(jobs, key=lambda j: j["created_at"])


def find_resumable(proj_dir):
    """Most recent FAILED job, if any — what `asset-factory resume`
    without an explicit job id operates on."""
    from orchestrator.build_state import FAILED
    failed = [j for j in list_jobs(proj_dir) if j["state"] == FAILED]
    return failed[-1] if failed else None

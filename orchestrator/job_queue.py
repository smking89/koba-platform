"""Job Queue + Scheduler (master spec's `orchestrator/job_queue`,
`job_scheduler`, `build_scheduler` — treated as one real component here,
since this codebase has nothing that would meaningfully separate "what's
next" from "when do I run it").

Scope honesty, stated plainly because it's easy to overclaim here: this
is a REAL, persisted FIFO queue with REAL time-gated scheduling (an item
can declare `not_before`, an actual timestamp compared against the real
clock at drain time — not a label). It is NOT a concurrent/multi-worker
system. `drain()` runs one item at a time, sequentially, in this process,
to completion, before picking the next. That matches every other
orchestration piece already built here (`orchestrator/job.py`'s and
`orchestrator/pipeline_manager.py`'s own documented scope) and avoids
claiming async/parallel execution this project does not actually have.
Building genuine concurrent workers is future work, not faked here.

A queue item is JSON-serializable: {command, args} — the exact same
shape `orchestrator.job.create_job()` persists per-command, which is
what lets `drain()` reuse `orchestrator.argv_utils.reconstruct_argv()` +
an injected `run_stage_fn` (the caller passes `cli.main.main`) to
actually execute each item, instead of re-implementing dispatch a third
time (job.py / pipeline_manager.py / job_queue.py all reuse the same
reconstruct-and-dispatch pattern now).
"""
import datetime
import json
import os
import uuid

QUEUE_FILENAME = "queue.json"

QUEUED = "QUEUED"
RUNNING = "RUNNING"
DONE = "DONE"
FAILED = "FAILED"
CANCELLED = "CANCELLED"


def _queue_path(proj_dir):
    return os.path.join(proj_dir, QUEUE_FILENAME)


def _load_queue(proj_dir):
    path = _queue_path(proj_dir)
    if not os.path.isfile(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _save_queue(proj_dir, items):
    with open(_queue_path(proj_dir), "w") as f:
        json.dump(items, f, indent=2)


def enqueue(proj_dir, command, args, not_before=None, priority=0):
    """Adds a request to the queue in QUEUED state. `not_before` (an ISO
    timestamp string, optional) gates eligibility — real comparison
    against the clock at drain time. `priority`: higher runs first among
    currently-eligible items; ties broken by enqueue order (FIFO)."""
    items = _load_queue(proj_dir)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    item = {
        "queue_id": str(uuid.uuid4()),
        "command": command,
        "args": args,
        "status": QUEUED,
        "priority": priority,
        "not_before": not_before,
        "enqueued_at": now,
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
    }
    items.append(item)
    _save_queue(proj_dir, items)
    return item


def list_queue(proj_dir):
    return _load_queue(proj_dir)


def _eligible(item, now_iso):
    if item["status"] != QUEUED:
        return False
    if item["not_before"] and item["not_before"] > now_iso:
        return False
    return True


def next_eligible(proj_dir):
    """The item the scheduler would pick next: among currently-eligible
    QUEUED items (not_before has genuinely passed, or is unset), highest
    priority first, then earliest enqueued — a real comparison, never a
    guess at what "should" run."""
    items = _load_queue(proj_dir)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    eligible = [i for i in items if _eligible(i, now_iso)]
    if not eligible:
        return None
    eligible.sort(key=lambda i: (-i["priority"], i["enqueued_at"]))
    return eligible[0]


def mark_running(proj_dir, queue_id):
    items = _load_queue(proj_dir)
    for item in items:
        if item["queue_id"] == queue_id:
            item["status"] = RUNNING
            item["started_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _save_queue(proj_dir, items)


def mark_finished(proj_dir, queue_id, exit_code):
    items = _load_queue(proj_dir)
    updated = None
    for item in items:
        if item["queue_id"] == queue_id:
            item["status"] = DONE if exit_code == 0 else FAILED
            item["exit_code"] = exit_code
            item["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            updated = item
    _save_queue(proj_dir, items)
    return updated


def cancel(proj_dir, queue_id_prefix):
    """Prefix match, consistent with get_job()/get_pipeline_run()'s UX.
    Only a still-QUEUED item can be cancelled — raises rather than
    silently no-op'ing on a RUNNING/DONE/FAILED/already-CANCELLED one,
    since pretending to cancel something already settled would be
    misleading, not helpful."""
    items = _load_queue(proj_dir)
    found = None
    for item in items:
        if item["queue_id"].startswith(queue_id_prefix):
            if item["status"] != QUEUED:
                raise ValueError(f"cannot cancel a {item['status']} item — only QUEUED items can be cancelled")
            item["status"] = CANCELLED
            found = item
    _save_queue(proj_dir, items)
    if found is None:
        raise ValueError(f"no such queue item: {queue_id_prefix}")
    return found


def drain(proj_dir, run_stage_fn, max_items=None):
    """The worker/scheduler loop: repeatedly picks the next eligible item
    (see next_eligible) and runs it to completion — one at a time, see
    module docstring — until nothing is eligible or max_items is reached.
    Returns the list of items that were actually run, each with its final
    status."""
    from orchestrator.argv_utils import reconstruct_argv

    ran = []
    while max_items is None or len(ran) < max_items:
        item = next_eligible(proj_dir)
        if item is None:
            break
        mark_running(proj_dir, item["queue_id"])
        argv = reconstruct_argv(item["command"], item["args"])
        exit_code = run_stage_fn(argv)
        finished = mark_finished(proj_dir, item["queue_id"], exit_code)
        ran.append(finished)
    return ran

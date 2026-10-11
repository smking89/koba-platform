"""Telemetry (master spec's telemetry/observability layer) — a real
aggregation on top of core.logging_setup.OperationLog's structured JSON
log files, which already record every command's success/failure,
duration, and errors/warnings but were, until now, only ever listed one
file path at a time (`logs` CLI command). This module reads those real
records back off disk and rolls them up: per-command run counts and
success rates, average duration, and total errors/warnings — genuine
numbers computed from what actually happened, never estimated or
fabricated.

Scope honesty: this reads OperationLog's existing JSON files as its
only data source. It does not add a new logging/metrics pipeline, a
time-series store, or anything that needs to run continuously — the
data was already being captured; this is what was missing to make it
answerable as a question ("what's actually been happening here?")
instead of just a pile of individual files.
"""
import json
import os

from core.logging_setup import LOGS_DIR


def _load_all_logs():
    """Every real OperationLog record on disk, oldest-unknown-order —
    corrupt/unreadable files are skipped (recorded as a count, never
    silently merged into the good data or allowed to crash the whole
    report)."""
    records = []
    skipped = 0
    if not os.path.isdir(LOGS_DIR):
        return records, skipped
    for fname in sorted(os.listdir(LOGS_DIR)):
        if not fname.endswith(".log"):
            continue
        path = os.path.join(LOGS_DIR, fname)
        try:
            with open(path, "r") as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            skipped += 1
    return records, skipped


def summarize(command=None):
    """Real counts/rates from every OperationLog record on disk,
    optionally filtered to one command. Returns:
      {"total_runs", "skipped_unreadable", "by_command": {
          command: {"runs", "successes", "failures", "success_rate",
                    "avg_duration_seconds", "total_errors", "total_warnings"}
      }}
    An empty log directory yields total_runs=0 and an empty by_command
    dict — never a fabricated baseline."""
    records, skipped = _load_all_logs()
    if command:
        records = [r for r in records if r.get("command") == command]

    by_command = {}
    for r in records:
        cmd = r.get("command", "unknown")
        bucket = by_command.setdefault(cmd, {
            "runs": 0, "successes": 0, "failures": 0,
            "_duration_sum": 0.0, "total_errors": 0, "total_warnings": 0,
        })
        bucket["runs"] += 1
        if r.get("success"):
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1
        bucket["_duration_sum"] += r.get("duration_seconds", 0) or 0
        bucket["total_errors"] += len(r.get("errors") or [])
        bucket["total_warnings"] += len(r.get("warnings") or [])

    for cmd, bucket in by_command.items():
        runs = bucket["runs"]
        bucket["success_rate"] = round(bucket["successes"] / runs, 4) if runs else 0.0
        bucket["avg_duration_seconds"] = round(bucket.pop("_duration_sum") / runs, 4) if runs else 0.0

    return {
        "total_runs": len(records),
        "skipped_unreadable": skipped,
        "by_command": by_command,
    }

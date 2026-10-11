"""Capability Registry (master spec's `capabilities/capability_registry`,
and the `CapabilitySnapshot` field the spec lists among a job/artifact's
structured-log fields — section on JobID/StageID/.../CapabilitySnapshot/
Timestamp/Duration/Status). Wraps `core.detection`'s real tool-detection
(never guesses — every result comes from actually locating/running an
executable) into a registry-shaped, persisted, versioned snapshot.

This is the piece that answers "what tools, at what versions, were
actually present when this job ran" — which `core.detection.detect_all()`
alone answers only for *right now*, with nothing recorded. Every job
created by `orchestrator.job.create_job()` gets one stamped on it (see
job.py), which is what makes "why did this build behave differently"
answerable after the fact instead of only debuggable live.
"""
import datetime
import json
import os

from core.config import PROJECT_ROOT
from core.detection import detect_all

SNAPSHOT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "capability_snapshots.jsonl")


def capture_snapshot():
    """A real, fresh detection pass — never cached, never assumed. Shape:
    {"captured_at": iso, "tools": {name: {found, version, executable, required}}}."""
    results = detect_all()
    return {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tools": {
            name: {
                "found": status.found,
                "version": status.version,
                "executable": status.executable,
                "required": status.required,
            }
            for name, status in results.items()
        },
    }


def record_snapshot():
    """Captures a fresh snapshot and appends it to the append-only log —
    same convention as tools/tool_audit.py's JSONL log, so capability
    history is queryable the same way tool-call history is."""
    snapshot = capture_snapshot()
    os.makedirs(os.path.dirname(SNAPSHOT_LOG_PATH), exist_ok=True)
    with open(SNAPSHOT_LOG_PATH, "a") as f:
        f.write(json.dumps(snapshot) + "\n")
    return snapshot


def read_recent_snapshots(limit=20):
    if not os.path.isfile(SNAPSHOT_LOG_PATH):
        return []
    with open(SNAPSHOT_LOG_PATH, "r") as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-limit:]]


def diff_snapshots(snapshot_a, snapshot_b):
    """Field-by-field comparison of two snapshots' tools — which tools
    changed found/version/executable between them. Returns
    {tool_name: {field: (value_a, value_b)}} for every tool that differs."""
    tools_a, tools_b = snapshot_a["tools"], snapshot_b["tools"]
    differences = {}
    for name in set(tools_a) | set(tools_b):
        a, b = tools_a.get(name, {}), tools_b.get(name, {})
        field_diffs = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
        if field_diffs:
            differences[name] = field_diffs
    return differences

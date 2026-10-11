"""Append-only audit log of every tool invocation — who called what, when,
whether it succeeded, how long it took. Master spec section 30
(observability) + "never log secrets": this logs argument *keys*, not
raw values, since a future tool contract might carry something sensitive
even though none of today's do.
"""
import datetime
import json
import os

from core.config import PROJECT_ROOT

AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "tool_audit.jsonl")


def record(tool_id, caller_id, success, duration_seconds, arg_keys=None, error=None):
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool_id": tool_id,
        "caller_id": caller_id,
        "success": success,
        "duration_seconds": round(duration_seconds, 4),
        "arg_keys": sorted(arg_keys or []),
        "error": error,
    }
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_recent(limit=50):
    if not os.path.isfile(AUDIT_LOG_PATH):
        return []
    with open(AUDIT_LOG_PATH, "r") as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-limit:]]

"""Real tests for the capability registry — actual detection calls
(no mocks), actual append-only JSONL persistence on disk."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from capabilities.capability_registry import (  # noqa: E402
    capture_snapshot, record_snapshot, read_recent_snapshots, diff_snapshots, SNAPSHOT_LOG_PATH,
)
from core.detection import REQUIRED_TOOLS, OPTIONAL_TOOLS  # noqa: E402


def run():
    # --- capture_snapshot: real, fresh, matches core.detection's own tool list ---
    snapshot = capture_snapshot()
    assert "captured_at" in snapshot
    assert set(snapshot["tools"].keys()) == set(REQUIRED_TOOLS) | set(OPTIONAL_TOOLS)

    blender = snapshot["tools"]["blender"]
    assert blender["found"] is True, "blender should genuinely be detected on this machine"
    assert blender["required"] is True
    assert "Blender" in (blender["version"] or "")

    fake_optional = [t for t in OPTIONAL_TOOLS if not snapshot["tools"][t]["found"]]
    assert fake_optional, "expected at least one genuinely-absent optional tool to exercise the not-found path"
    assert snapshot["tools"][fake_optional[0]]["required"] is False

    # --- record_snapshot: real append-only persistence ---
    before_count = len(read_recent_snapshots(limit=10_000))
    recorded = record_snapshot()
    after = read_recent_snapshots(limit=10_000)
    assert len(after) == before_count + 1, "record_snapshot must append, not overwrite"
    assert after[-1]["captured_at"] == recorded["captured_at"]
    assert os.path.isfile(SNAPSHOT_LOG_PATH)

    # --- read_recent_snapshots: limit is honored ---
    limited = read_recent_snapshots(limit=1)
    assert len(limited) == 1
    assert limited[0]["captured_at"] == recorded["captured_at"]

    # --- diff_snapshots: real field-level comparison ---
    snap_a = {"tools": {"blender": {"found": True, "version": "5.2.2"}, "gimp": {"found": True, "version": "3.2.6"}}}
    snap_b = {"tools": {"blender": {"found": True, "version": "5.2.3"}, "gimp": {"found": True, "version": "3.2.6"}}}
    diff = diff_snapshots(snap_a, snap_b)
    assert set(diff.keys()) == {"blender"}, "only the changed tool should appear in the diff"
    assert diff["blender"]["version"] == ("5.2.2", "5.2.3")

    identical_diff = diff_snapshots(snap_a, snap_a)
    assert identical_diff == {}, "diffing a snapshot against itself must be empty"

    return True


if __name__ == "__main__":
    ok = run()
    print("test_capability_registry: PASS" if ok else "test_capability_registry: FAIL")
    sys.exit(0 if ok else 1)

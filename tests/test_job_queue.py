"""Real tests for the job queue + scheduler — a real persisted FIFO
queue, real time-gated eligibility (actual ISO-timestamp comparison), a
real single-worker drain loop driven through the real CLI (`enqueue`/
`queue`/`work`), and a real Blender fixture at the end of the chain. No
mocks. Also locks in two bugs found and fixed during manual smoke-testing
so they can't silently regress:
  1. cancel() must prefix-match (like get_job()/get_pipeline_run()), not
     require the full UUID.
  2. the args dict built from a parsed downstream command must never
     leak argparse's own "command"/"func" bookkeeping keys — those broke
     reconstruct_argv() by turning into a bogus `--command <name>` flag.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.main import main  # noqa: E402
from core.config import load_projects_registry, save_projects_registry  # noqa: E402
from core.project import project_dir_for, slugify  # noqa: E402
from orchestrator.job_queue import (  # noqa: E402
    enqueue, list_queue, cancel, drain, next_eligible,
    QUEUED, DONE, CANCELLED,
)
from orchestrator.job import list_jobs  # noqa: E402
from orchestrator.build_state import READY  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Queue ZZZ Temp"


def _cleanup():
    proj_dir = project_dir_for(TEST_PROJECT_NAME)
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir)
    registry = load_projects_registry()
    slug = slugify(TEST_PROJECT_NAME)
    if slug in registry.get("projects", []):
        registry["projects"].remove(slug)
        save_projects_registry(registry)


def _run_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def run():
    # --- unit-level: enqueue/eligibility/drain with a stub runner ---
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_job_queue_")
    try:
        item_a = enqueue(tmp_dir, "stage_a", {"name": "x"})
        assert item_a["status"] == QUEUED
        assert os.path.isfile(os.path.join(tmp_dir, "queue.json"))

        # not_before in the far future must never be eligible.
        item_b = enqueue(tmp_dir, "stage_b", {"name": "x"}, not_before="2099-01-01T00:00:00+00:00")
        assert next_eligible(tmp_dir)["queue_id"] == item_a["queue_id"], \
            "the future-gated item must not be picked while ineligible"

        # higher priority runs first among eligible items.
        item_c = enqueue(tmp_dir, "stage_c", {"name": "x"}, priority=10)
        assert next_eligible(tmp_dir)["queue_id"] == item_c["queue_id"], \
            "a higher-priority eligible item must be picked over an older lower-priority one"

        calls = []
        ran = drain(tmp_dir, run_stage_fn=lambda argv: (calls.append(argv), 0)[1])
        assert len(ran) == 2, "only the 2 eligible items (c, a) should run — b is still future-gated"
        assert {r["queue_id"] for r in ran} == {item_c["queue_id"], item_a["queue_id"]}
        assert all(r["status"] == DONE for r in ran)
        assert calls[0][0] == "stage_c" and calls[1][0] == "stage_a", "priority order must be honored"

        remaining = list_queue(tmp_dir)
        b = next(i for i in remaining if i["queue_id"] == item_b["queue_id"])
        assert b["status"] == QUEUED, "the future-gated item must still be untouched"

        # --- bug #1 regression: cancel() must accept a prefix ---
        cancelled = cancel(tmp_dir, item_b["queue_id"][:8])
        assert cancelled["status"] == CANCELLED
        try:
            cancel(tmp_dir, item_b["queue_id"][:8])
            assert False, "cancelling an already-CANCELLED item must raise, not silently succeed"
        except ValueError:
            pass
        try:
            cancel(tmp_dir, "not-a-real-prefix")
            assert False
        except ValueError:
            pass

        # max_items caps a drain call.
        enqueue(tmp_dir, "stage_d", {"name": "x"})
        enqueue(tmp_dir, "stage_e", {"name": "x"})
        ran2 = drain(tmp_dir, run_stage_fn=lambda argv: 0, max_items=1)
        assert len(ran2) == 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # --- real end-to-end: enqueue/queue/work against a real project +
    # a real Blender fixture, through the actual CLI ---
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_src = os.path.join(PROJECT_ROOT, "adapters", "blender", "assets", "generated", "GummyGun.blend")
        assert os.path.isfile(fixture_src), "expected an already-built fixture from earlier sessions/tests"
        fixture_path = os.path.join(proj_dir, "blender", "GummyGun.blend")
        os.makedirs(os.path.dirname(fixture_path), exist_ok=True)
        shutil.copyfile(fixture_src, fixture_path)

        # bug #2 regression: a real downstream command parsed through
        # build_parser() must not leak "command"/"func" into the stored args.
        code, out = _run_cli(["enqueue", TEST_PROJECT_NAME, "--",
                               "validate", TEST_PROJECT_NAME, "--profile", "60fps_standard"])
        assert code == 0, out
        assert "Enqueued" in out

        items = list_queue(proj_dir)
        assert len(items) == 1
        assert "command" not in items[0]["args"], \
            "argparse's own subparsers dest='command' must never leak into the stored downstream args"
        assert "func" not in items[0]["args"]

        code, out = _run_cli(["queue", TEST_PROJECT_NAME])
        assert code == 0
        assert "1 queued item(s)" in out

        code, out = _run_cli(["work", TEST_PROJECT_NAME])
        assert code == 0, f"expected the real validate command to run and PASS:\n{out}"
        assert "RESULT: PASS" in out
        assert "[DONE" in out

        final_items = list_queue(proj_dir)
        assert final_items[0]["status"] == DONE

        # the drained item must have created a real, independent Job.
        jobs = list_jobs(proj_dir)
        assert len(jobs) == 1 and jobs[0]["command"] == "validate" and jobs[0]["state"] == READY

        code, out = _run_cli(["work", TEST_PROJECT_NAME])
        assert code == 0
        assert "Nothing eligible" in out

        # --- enqueue flag-ordering regression: --not-before/--priority
        # must parse correctly regardless of their position relative to
        # the project name (the original argparse.REMAINDER bug). ---
        code, out = _run_cli(["enqueue", TEST_PROJECT_NAME, "--not-before", "2099-01-01T00:00:00Z",
                               "--priority", "5", "--",
                               "validate", TEST_PROJECT_NAME, "--profile", "60fps_standard"])
        assert code == 0, f"enqueue with flags before '--' must parse cleanly:\n{out}"
        queued = list_queue(proj_dir)
        future_item = next(i for i in queued if i["status"] == QUEUED)
        assert future_item["not_before"] == "2099-01-01T00:00:00Z"
        assert future_item["priority"] == 5

        code, out = _run_cli(["work", TEST_PROJECT_NAME])
        assert "Nothing eligible" in out, "the far-future item must not run"

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_job_queue: PASS" if ok else "test_job_queue: FAIL")
    sys.exit(0 if ok else 1)

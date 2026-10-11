"""Real tests for the job abstraction — actual directories/files on disk,
actual state-machine enforcement (including the negative cases: an
invalid transition must raise, not silently succeed)."""
import os
import shutil
import sys
import tempfile

from orchestrator.build_state import (
    valid_transition, require_valid_transition, InvalidTransition,
    CREATED, RUNNING, VALIDATING, PACKAGING, READY, FAILED, CANCELLED,
)
from orchestrator.job import create_job, transition, get_job, list_jobs, find_resumable


def run():
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_job_")
    try:
        # --- state machine: positive and negative cases ---
        assert valid_transition(CREATED, RUNNING) is True
        assert valid_transition(CREATED, READY) is False, "CREATED must not be able to jump straight to READY"
        assert valid_transition(RUNNING, VALIDATING) is True
        assert valid_transition(RUNNING, PACKAGING) is True
        assert valid_transition(VALIDATING, READY) is True
        assert valid_transition(FAILED, RUNNING) is True, "resume must be able to re-enter RUNNING from FAILED"
        assert valid_transition(READY, RUNNING) is False, "READY is terminal"

        try:
            require_valid_transition(CREATED, READY)
            assert False, "should have raised InvalidTransition"
        except InvalidTransition:
            pass

        # --- create_job: real workspace + file on disk ---
        job = create_job(tmp_dir, "validate", {"blend_path": "/tmp/x.blend", "profile": "60fps_standard"})
        assert job["state"] == CREATED
        assert os.path.isdir(job["workspace_dir"])
        assert os.path.isfile(os.path.join(job["workspace_dir"], "job.json"))
        assert len(job["history"]) == 1
        assert "capability_snapshot" in job, "every job must stamp a real CapabilitySnapshot at creation"
        assert job["capability_snapshot"]["tools"]["blender"]["found"] is True
        reloaded_job = get_job(tmp_dir, job["job_id"])
        assert reloaded_job["capability_snapshot"] == job["capability_snapshot"], \
            "the snapshot must round-trip through persistence, not just live in memory"

        # --- transition: valid path, persisted to disk ---
        job = transition(job, RUNNING)
        assert job["state"] == RUNNING
        reloaded = get_job(tmp_dir, job["job_id"])
        assert reloaded["state"] == RUNNING, "transition must persist, not just mutate in memory"

        job = transition(job, VALIDATING)
        job = transition(job, READY, result_summary={"result": "PASS"})
        assert job["state"] == READY
        assert job["result_summary"] == {"result": "PASS"}
        assert len(job["history"]) == 4  # CREATED, RUNNING, VALIDATING, READY

        # --- transition: invalid path must raise and must NOT silently mutate state ---
        try:
            transition(job, RUNNING)  # READY is terminal
            assert False, "should have raised InvalidTransition"
        except InvalidTransition:
            pass
        assert get_job(tmp_dir, job["job_id"])["state"] == READY, \
            "a rejected transition must not have changed the persisted state"

        # --- a second job that fails, for find_resumable ---
        job2 = create_job(tmp_dir, "optimize", {"blend_path": "/tmp/y.blend"})
        job2 = transition(job2, RUNNING)
        job2 = transition(job2, FAILED, error="BlenderBridgeError: something broke")

        # --- get_job by prefix ---
        found = get_job(tmp_dir, job2["job_id"][:8])
        assert found is not None
        assert found["job_id"] == job2["job_id"]
        assert get_job(tmp_dir, "not-a-real-prefix") is None

        # --- list_jobs: both present, sorted by creation time ---
        jobs = list_jobs(tmp_dir)
        assert len(jobs) == 2
        assert jobs[0]["job_id"] == job["job_id"]
        assert jobs[1]["job_id"] == job2["job_id"]

        # --- find_resumable: only the FAILED one ---
        resumable = find_resumable(tmp_dir)
        assert resumable["job_id"] == job2["job_id"]

        # --- resume path: FAILED -> RUNNING is allowed, and args survive for replay ---
        job2 = transition(job2, RUNNING)
        assert job2["state"] == RUNNING
        assert job2["args"] == {"blend_path": "/tmp/y.blend"}, \
            "args must survive a resume — that's what makes replay possible"

        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = run()
    print("test_job: PASS" if ok else "test_job: FAIL")
    sys.exit(0 if ok else 1)

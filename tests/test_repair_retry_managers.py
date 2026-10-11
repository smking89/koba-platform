"""Real tests for repair/repair_manager.py (bounded multi-attempt repair
loop) and orchestrator/retry_manager.py (bounded checkpoint-based retry),
item 2 of the user's 4-item "in order" roadmap list — no mocks. Both
modules are thin, injected-dependency wrappers around mechanisms already
covered elsewhere (tests/test_repair.py's real Blender repair loop,
tests/test_cli.py's real `resume` replay); these tests exercise the
bounded-retry CONTROL FLOW they add on top, using real Blender fixtures
for repair_manager and real persisted Job state for retry_manager.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.main import main  # noqa: E402
from core.config import load_projects_registry, save_projects_registry, load_tools_config  # noqa: E402
from core.project import project_dir_for, slugify  # noqa: E402
from orchestrator.job import list_jobs, get_job, find_resumable, transition as job_transition  # noqa: E402
from orchestrator.build_state import READY, FAILED, RUNNING, VALIDATING  # noqa: E402
from orchestrator.retry_manager import retry_job, RetryExhausted  # noqa: E402
from repair.repair_manager import repair_loop, tighten_ratio, should_retry, DEFAULT_MAX_ATTEMPTS  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Repair Retry Managers ZZZ Temp"
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")
PROFILE = "240fps_esports"


def _cleanup(name=TEST_PROJECT_NAME):
    proj_dir = project_dir_for(name)
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir)
    registry = load_projects_registry()
    slug = slugify(name)
    if slug in registry.get("projects", []):
        registry["projects"].remove(slug)
        save_projects_registry(registry)


def _run_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def _build_decimate_fixture(dest_path, subdivisions=8):
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test8_repair_decimate_stress.py", "--", str(subdivisions)],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test8_repair_decimate_stress.blend")
    assert os.path.isfile(src)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def _build_stress_fixture(dest_path, entity_count=400):
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test7_repair_stress.py", "--", str(entity_count)],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test7_repair_stress.blend")
    assert os.path.isfile(src)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def run():
    # === repair_manager: pure control-flow logic, no Blender needed ===
    assert tighten_ratio(0.9) == 0.675
    assert tighten_ratio(0.1) == 0.075
    assert tighten_ratio(0.01) == 0.05, "must floor at MIN_DECIMATE_RATIO, never go near zero"

    decimate_decision = {"decimate_ratio": 0.5}
    merge_decision = {"decimate_ratio": None}

    # merge is deterministic -- never worth retrying, regardless of attempts left.
    assert should_retry(merge_decision, ["entity_count = 400 exceeds max_visible_entities = 350"],
                         ["entity_count = 390 exceeds max_visible_entities = 350"], 1, 5) is False

    # decimate, attempts remain, same metric still failing -> retry.
    assert should_retry(decimate_decision, ["triangles = 300000 exceeds max_triangles = 250000"],
                         ["triangles = 260000 exceeds max_triangles = 250000"], 1, 3) is True

    # decimate, but attempts exhausted -> stop.
    assert should_retry(decimate_decision, ["triangles = 300000 exceeds max_triangles = 250000"],
                         ["triangles = 260000 exceeds max_triangles = 250000"], 3, 3) is False

    # decimate, but a genuinely NEW failure metric appeared -> stop, don't guess.
    assert should_retry(decimate_decision, ["triangles = 300000 exceeds max_triangles = 250000"],
                         ["triangles = 260000 exceeds max_triangles = 250000",
                          "materials = 90 exceeds max_materials = 80"], 1, 3) is False

    # === repair_manager.repair_loop: real end-to-end, real Blender ===
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        proj_dir = project_dir_for(TEST_PROJECT_NAME)

        # merge-fixable failure: even with max_attempts=3, must stop after
        # exactly 1 real attempt (deterministic strategy, no point retrying).
        fixture_path = os.path.join(proj_dir, "blender", "test7_repair_stress.blend")
        _build_stress_fixture(fixture_path, entity_count=400)
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", PROFILE])
        assert code == 1

        from repair.repair_engine import revalidate as re_revalidate
        report = re_revalidate(fixture_path, PROFILE)
        assert report["result"] == "FAIL"

        counter = {"n": 0}

        def output_path_fn(i):
            counter["n"] += 1
            return os.path.join(proj_dir, "repaired", f"merge_attempt_{i}.blend")

        attempts = repair_loop(report, fixture_path, PROFILE, output_path_fn,
                                merge_group="cluster", max_attempts=3)
        assert len(attempts) == 1, "merge strategy must never retry even when max_attempts allows more"
        assert attempts[0]["revalidation"]["result"] == "PASS"

        # decimate-fixable failure: real fixture that already passes in
        # one attempt (same fixture as tests/test_repair.py's decimate
        # case) -- confirms the loop stops at the first PASS rather than
        # always running out max_attempts.
        decimate_fixture_path = os.path.join(proj_dir, "blender", "test8_repair_decimate_stress.blend")
        _build_decimate_fixture(decimate_fixture_path)
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", PROFILE,
                               "--blend-file", decimate_fixture_path])
        assert code == 1
        report = re_revalidate(decimate_fixture_path, PROFILE)
        assert report["result"] == "FAIL"

        def output_path_fn2(i):
            return os.path.join(proj_dir, "repaired", f"decimate_attempt_{i}.blend")

        attempts = repair_loop(report, decimate_fixture_path, PROFILE, output_path_fn2, max_attempts=DEFAULT_MAX_ATTEMPTS)
        assert len(attempts) == 1, "a fixture that passes on the first real decimate attempt must not retry further"
        assert attempts[0]["revalidation"]["result"] == "PASS"

        # unfixable failure: repair_loop must propagate UnrepairableFailure
        # immediately (zero wasted Blender invocations), exactly like
        # repair_engine.classify_failure itself.
        from repair.repair_engine import UnrepairableFailure
        unfixable_report = {"result": "FAIL", "failures": ["materials = 90 exceeds max_materials = 80"]}
        try:
            repair_loop(unfixable_report, fixture_path, PROFILE, lambda i: "/dev/null", max_attempts=3)
            assert False, "must not silently no-op on an unfixable failure"
        except UnrepairableFailure:
            pass

        # --- CLI integration: `repair --max-attempts 2` on an
        # already-PASSing decimate fixture must take exactly one attempt
        # (loop + CLI wiring together, exercising the real `repair` command) ---
        fresh_decimate_path = os.path.join(proj_dir, "blender", "test8b.blend")
        shutil.copyfile(decimate_fixture_path, fresh_decimate_path)
        code, out = _run_cli(["repair", TEST_PROJECT_NAME, "--profile", PROFILE,
                               "--blend-file", fresh_decimate_path, "--max-attempts", "2"])
        assert code == 0, f"expected decimation to fix a pure triangle-budget overage:\n{out}"
        assert "Repair attempt #1" in out
        assert "Repair attempt #2" not in out, "must not run a second attempt once the first already PASSed"
    finally:
        _cleanup()

    # === retry_manager: real persisted Job state, injected resume_once ===
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test7_repair_stress.blend")
        _build_stress_fixture(fixture_path, entity_count=10)

        # a deterministically-failing replay (bad profile never becomes
        # valid) must exhaust real `retry`, not fake success.
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", "not_a_real_profile"])
        assert code == 1
        code, out = _run_cli(["retry", TEST_PROJECT_NAME, "--max-attempts", "2"])
        assert code == 1, "a deterministically-failing replay must exhaust retry, not fake success"
        assert "attempt #1" in out and "attempt #2" in out

        validate_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "validate"]
        assert len(validate_jobs) == 3, "original + 2 retried replays, each its own fresh persisted job"

        # retry_job()'s own orchestration, directly: a job that fails
        # once then succeeds must stop at exactly 2 attempts, not run to
        # max_attempts -- using real Job persistence/transitions (no CLI
        # replay, since no real command here is guaranteed to flip from
        # FAIL to PASS mid-loop; resume_once is retry_job's own injected
        # seam by design).
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", "not_a_real_profile"])
        assert code == 1
        target_job = find_resumable(proj_dir)
        assert target_job is not None and target_job["state"] == FAILED

        call_count = {"n": 0}

        def flaky_resume_once(job):
            call_count["n"] += 1
            job = job_transition(job, RUNNING)
            if call_count["n"] < 2:
                job_transition(job, FAILED, error="still failing")
                return 1
            job = job_transition(job, VALIDATING)
            job_transition(job, READY, result_summary={"resumed": True})
            return 0

        outcome = retry_job(proj_dir, flaky_resume_once, job_id=target_job["job_id"], max_attempts=5)
        assert outcome["succeeded"] is True
        assert len(outcome["attempts"]) == 2, "must stop at the first success, not keep going to max_attempts"

        # a job that is not FAILED must be refused immediately, zero attempts.
        ready_job = get_job(proj_dir, target_job["job_id"])
        assert ready_job["state"] == READY
        try:
            retry_job(proj_dir, flaky_resume_once, job_id=ready_job["job_id"], max_attempts=3)
            assert False, "must refuse a non-FAILED job, not silently no-op"
        except RetryExhausted:
            pass

        # a project with nothing resumable at all must also refuse loudly.
        _cleanup("Koba Test Retry Manager Empty ZZZ Temp")
        code, out = _run_cli(["create", "Koba Test Retry Manager Empty ZZZ Temp"])
        assert code == 0, out
        empty_proj_dir = project_dir_for("Koba Test Retry Manager Empty ZZZ Temp")
        try:
            retry_job(empty_proj_dir, flaky_resume_once, max_attempts=3)
            assert False, "must refuse when there is nothing resumable, not loop forever"
        except RetryExhausted:
            pass
        _cleanup("Koba Test Retry Manager Empty ZZZ Temp")

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_repair_retry_managers: PASS" if ok else "test_repair_retry_managers: FAIL")
    sys.exit(0 if ok else 1)

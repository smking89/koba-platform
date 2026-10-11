"""Real tests for the pipeline manager / stage runner — unit-level tests
of run_pipeline()'s stop/continue-on-failure logic with a stub stage
runner (no Blender needed), plus a real end-to-end run of the
validate_then_repair pipeline against the actual 400-entity repair-stress
fixture (same one tests/test_repair.py uses), driven through the real
`pipeline` CLI command. No mocks in the end-to-end path.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.main import main  # noqa: E402
from core.config import load_projects_registry, save_projects_registry, load_tools_config  # noqa: E402
from core.project import project_dir_for, slugify  # noqa: E402
from orchestrator.pipeline_manager import (  # noqa: E402
    run_pipeline, get_pipeline_run, list_pipeline_runs, PASSED, FAILED, SKIPPED,
)
from orchestrator.job import list_jobs  # noqa: E402
from orchestrator.build_state import READY as JOB_READY  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Pipeline ZZZ Temp"
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")
PROFILE = "240fps_esports"


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
    # --- unit-level: run_pipeline()'s own stop/continue logic, stubbed
    # stage runner (no Blender, no real CLI dispatch) ---
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_pipeline_")
    try:
        # Stop-on-failure is the default: stage 2 must be SKIPPED, never run.
        calls = []

        def stub_stop_on_fail(argv):
            calls.append(argv)
            return 1 if argv[0] == "stage_a" else 0

        stages = [
            {"command": "stage_a", "args": {"name": "x"}, "continue_on_failure": False},
            {"command": "stage_b", "args": {"name": "x"}, "continue_on_failure": False},
        ]
        run = run_pipeline(tmp_dir, "test_pipeline", stages, run_stage_fn=stub_stop_on_fail)
        assert run["status"] == FAILED
        assert run["stages"][0]["status"] == FAILED
        assert run["stages"][0]["exit_code"] == 1
        assert run["stages"][1]["status"] == SKIPPED, "must not run a stage after a non-continuing failure"
        assert run["stages"][1]["exit_code"] is None
        assert len(calls) == 1, "the skipped stage must never actually be invoked"

        # continue_on_failure=True on stage 1 lets stage 2 run despite the failure.
        calls = []

        def stub_continue(argv):
            calls.append(argv)
            return 1 if argv[0] == "stage_a" else 0

        stages_continue = [
            {"command": "stage_a", "args": {"name": "x"}, "continue_on_failure": True},
            {"command": "stage_b", "args": {"name": "x"}, "continue_on_failure": False},
        ]
        run2 = run_pipeline(tmp_dir, "test_pipeline_continue", stages_continue, run_stage_fn=stub_continue)
        assert run2["status"] == PASSED, "overall status reflects the last (only real) failure point — here nothing unrecovered failed"
        assert run2["stages"][0]["status"] == FAILED
        assert run2["stages"][1]["status"] == PASSED
        assert len(calls) == 2, "stage_b must actually run since stage_a was marked continue_on_failure"

        # all-pass case
        run3 = run_pipeline(tmp_dir, "test_pipeline_allpass", stages_continue, run_stage_fn=lambda argv: 0)
        assert run3["status"] == PASSED
        assert all(s["status"] == PASSED for s in run3["stages"])

        # persistence: get_pipeline_run / list_pipeline_runs round-trip
        reloaded = get_pipeline_run(tmp_dir, run["run_id"][:8])
        assert reloaded is not None and reloaded["run_id"] == run["run_id"]
        assert get_pipeline_run(tmp_dir, "not-a-real-prefix") is None

        all_runs = list_pipeline_runs(tmp_dir)
        assert len(all_runs) == 3
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # --- real end-to-end: validate_then_repair against a genuine
    # over-budget fixture, driven through the real `pipeline` CLI command ---
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test7_repair_stress.blend")
        _build_stress_fixture(fixture_path, entity_count=400)

        code, out = _run_cli(["pipeline", TEST_PROJECT_NAME, "--template", "validate_then_repair",
                               "--profile", PROFILE, "--merge-group", "cluster"])
        assert code == 0, f"expected the pipeline to end PASSED (validate FAILs, repair fixes it):\n{out}"
        assert "PASSED" in out
        assert "[FAILED" in out and "validate" in out, "the validate stage's expected FAIL must be visible"
        assert "[PASSED" in out and "repair" in out

        runs = list_pipeline_runs(proj_dir)
        assert len(runs) == 1
        run = runs[0]
        assert run["pipeline_name"] == "validate_then_repair"
        assert run["status"] == PASSED
        assert run["stages"][0]["command"] == "validate" and run["stages"][0]["status"] == FAILED
        assert run["stages"][1]["command"] == "repair" and run["stages"][1]["status"] == PASSED

        # each stage genuinely created its own real, independent job.
        jobs = list_jobs(proj_dir)
        assert len(jobs) == 2
        assert {j["command"] for j in jobs} == {"validate", "repair"}
        assert all(j["state"] == JOB_READY for j in jobs), \
            "both jobs completed as jobs (validate's own FAIL is a valid job outcome, not a job failure)"

        repaired_path = os.path.join(proj_dir, "repaired", "test7_repair_stress__repair_v1.blend")
        assert os.path.isfile(repaired_path), "the repair stage must have actually produced its output"

        # `pipelines` CLI inspection command
        code, out = _run_cli(["pipelines", TEST_PROJECT_NAME])
        assert code == 0
        assert "1 pipeline run(s)" in out

        code, out = _run_cli(["pipelines", TEST_PROJECT_NAME, "--run-id", run["run_id"][:8]])
        assert code == 0
        assert "validate_then_repair" in out

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_pipeline_manager: PASS" if ok else "test_pipeline_manager: FAIL")
    sys.exit(0 if ok else 1)

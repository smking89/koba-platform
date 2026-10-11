"""Real tests for the second agent (repair_agent) — no mocks. Locks in
two real bugs found during manual smoke-testing before any test existed:
  1. the "nothing to repair" (validate already PASSes) path tried
     RUNNING -> READY directly, which orchestrator.build_state does not
     allow (RUNNING must go through VALIDATING/PACKAGING/REPAIRING
     first) — this also affected cmd_repair itself, never exercised by
     any prior test since test_repair.py only ever drove FAILing fixtures.
  2. an earlier design had RepairAgent orchestrate diagnose+repair in one
     call, which computed a repair-attempt artifact id from an in-memory
     graph BEFORE the diagnosis's FAIL status was persisted — the
     subsequently-reloaded graph had a different id for the same source
     file, and save_graph() crashed on the stale id. Fixed by having the
     agent only decide the merge_group hint; cli.main.cmd_repair_agent
     orchestrates in the same order cmd_repair does.
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
from core.artifact_graph import load_graph, find_by_path, PASS as ART_PASS, FAIL as ART_FAIL  # noqa: E402
from orchestrator.job import list_jobs  # noqa: E402
from orchestrator.build_state import READY  # noqa: E402
from agents.repair_agent import RepairAgent  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Repair Agent ZZZ Temp"
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


def _run_end_to_end():
    # --- unit-level: the agent's one real decision, merge_group extraction ---
    agent = RepairAgent()
    provider, merge_group = agent.get_merge_group_hint("merge the 'cluster' group and retry")
    assert provider.provider_id == "rule_based"
    assert merge_group == "cluster"

    _, no_group = agent.get_merge_group_hint("please check this asset")
    assert no_group is None, "must not invent a group name that wasn't in the instruction"

    # --- real end-to-end: a genuine FAIL, AI extracts the group, repairs, PASSes ---
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test7_repair_stress.blend")
        _build_stress_fixture(fixture_path, entity_count=400)

        code, out = _run_cli(["repair-agent", TEST_PROJECT_NAME, "--profile", PROFILE,
                               "--instruction", "please check this and merge the 'cluster' group if needed"])
        assert code == 0, f"expected the AI-extracted merge_group to actually fix the overage:\n{out}"
        assert "Extracted merge_group from instruction: 'cluster'" in out
        assert "RESULT: PASS" in out

        # regression #2: both artifacts must exist with the CORRECT,
        # independently-verified statuses — this silently produced only
        # one artifact (and, without this fix, crashed outright) before.
        graph = load_graph(proj_dir)
        source = find_by_path(graph, fixture_path)
        assert source is not None, "the source artifact must exist"
        assert source["validation_status"] == ART_FAIL, \
            "the source's real FAIL diagnosis must survive, not get clobbered by a later stale save_graph()"

        repaired_path = os.path.join(proj_dir, "repaired", "test7_repair_stress__repair_v1.blend")
        repaired = find_by_path(graph, repaired_path)
        assert repaired is not None, "the repaired artifact must exist (previously silently missing)"
        assert repaired["validation_status"] == ART_PASS
        assert source["artifact_id"] in repaired["parent_artifacts"]

        jobs = [j for j in list_jobs(proj_dir) if j["command"] == "repair-agent"]
        assert len(jobs) == 1 and jobs[0]["state"] == READY

        # regression #1: no --merge-group given, instruction names none —
        # must refuse to guess, exactly like the CLI --merge-group path.
        code, out = _run_cli(["repair-agent", TEST_PROJECT_NAME, "--profile", PROFILE,
                               "--instruction", "please take a look at this"])
        assert code == 1, "must refuse rather than guess a merge_group, even on a second attempt"

        return True
    finally:
        _cleanup()


def _run_pass_path():
    """Regression #1, isolated: the "nothing to repair" PASS path must
    not crash with InvalidTransition (RUNNING -> READY was invalid;
    fixed by adding a VALIDATING transition first)."""
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "GummyGun.blend")
        assert os.path.isfile(fixture_src), "expected an already-built fixture from earlier sessions/tests"
        fixture_path = os.path.join(proj_dir, "blender", "GummyGun.blend")
        os.makedirs(os.path.dirname(fixture_path), exist_ok=True)
        shutil.copyfile(fixture_src, fixture_path)

        code, out = _run_cli(["repair-agent", TEST_PROJECT_NAME, "--profile", "60fps_standard",
                               "--instruction", "check this please"])
        assert code == 0, f"the PASS path must not crash with InvalidTransition:\n{out}"
        assert "Nothing to repair" in out

        jobs = [j for j in list_jobs(proj_dir) if j["command"] == "repair-agent"]
        assert len(jobs) == 1 and jobs[0]["state"] == READY

        return True
    finally:
        _cleanup()


def run():
    return _run_end_to_end() and _run_pass_path()


if __name__ == "__main__":
    ok = run()
    print("test_repair_agent: PASS" if ok else "test_repair_agent: FAIL")
    sys.exit(0 if ok else 1)

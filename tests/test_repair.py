"""Real tests for the repair loop (master spec section 10) — no mocks:
builds an actual over-budget fixture via a real Blender subprocess (400
boxes sharing one visibility_group), drives the real `repair` CLI command
against it under an actual production profile (240fps_esports), and
verifies the full GENERATE -> VALIDATE -> FAIL -> DIAGNOSE -> REPAIR ->
REVALIDATE -> PASS lifecycle, including that the failed source artifact
is never overwritten or have its status touched by the repair.
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
from repair.repair_engine import classify_failure, UnrepairableFailure  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Repair ZZZ Temp"
DECIMATE_PROJECT_NAME = "Koba Test Repair Decimate ZZZ Temp"
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")
PROFILE = "240fps_esports"  # real production profile: max_visible_entities=350, max_unique_meshes=60, max_triangles=250000


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


def _build_stress_fixture(dest_path, entity_count=400):
    """Real (non-mocked) Blender build: `entity_count` boxes, all tagged
    visibility_group='cluster' — comfortably over 240fps_esports' 350
    entity cap and 60 unique-mesh cap, so validate genuinely FAILs and
    merge genuinely fixes it (not a fabricated tiny budget)."""
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test7_repair_stress.py", "--", str(entity_count)],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test7_repair_stress.blend")
    assert os.path.isfile(src), "fixture build did not produce test7_repair_stress.blend"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def _build_decimate_fixture(dest_path, subdivisions=8):
    """Real Blender build: a single high-poly icosphere (327680 triangles
    at subdivisions=8, confirmed by direct testing — the subdivisions->
    facecount relationship isn't simply 20*4^subdivisions) — comfortably
    over 240fps_esports' real max_triangles=250000, and nothing else
    (entity_count=1, unique_meshes=1), isolating the decimate strategy
    from the merge strategy tested above."""
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test8_repair_decimate_stress.py", "--", str(subdivisions)],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test8_repair_decimate_stress.blend")
    assert os.path.isfile(src), "fixture build did not produce test8_repair_decimate_stress.blend"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def run():
    # --- classify_failure: unit-level, no Blender needed ---
    fail_report = {"result": "FAIL", "failures": ["entity_count = 400 exceeds max_visible_entities = 350"]}
    decision = classify_failure(fail_report, merge_group="cluster")
    assert decision["strategy"] == "optimize_repair"
    assert decision["merge_group"] == "cluster"
    assert decision["decimate_ratio"] is None
    assert decision["cannot_address"] == []

    try:
        classify_failure(fail_report, merge_group=None)
        assert False, "must not guess a merge_group"
    except UnrepairableFailure:
        pass

    # --- triangle overage: fixable via decimation, ratio computed (not guessed) ---
    tri_report = {"result": "FAIL", "failures": ["triangles = 58806 exceeds max_triangles = 250000"]}
    decision = classify_failure(tri_report)
    assert decision["merge_group"] is None
    assert decision["decimate_ratio"] is not None
    # 250000/58806 > 1 -> would clamp to 0.95, not blow past it or go negative
    assert 0.0 < decision["decimate_ratio"] <= 0.95

    tri_over_report = {"result": "FAIL", "failures": ["triangles = 4000000 exceeds max_triangles = 250000"]}
    decision = classify_failure(tri_over_report)
    expected_ratio = round(min(0.95, (250000 / 4000000) * 0.9), 4)
    assert decision["decimate_ratio"] == expected_ratio

    # --- both entity_count and triangles over budget: both actions selected ---
    combined_report = {"result": "FAIL", "failures": [
        "entity_count = 400 exceeds max_visible_entities = 350",
        "triangles = 4000000 exceeds max_triangles = 250000",
    ]}
    decision = classify_failure(combined_report, merge_group="cluster")
    assert decision["merge_group"] == "cluster"
    assert decision["decimate_ratio"] is not None
    assert len(decision["addresses"]) == 2

    unfixable_report = {"result": "FAIL", "failures": ["materials = 90 exceeds max_materials = 80"]}
    try:
        classify_failure(unfixable_report, merge_group="cluster")
        assert False, "must not fake a fix for a failure category it has no strategy for"
    except UnrepairableFailure:
        pass

    pass_report = {"result": "PASS", "failures": []}
    try:
        classify_failure(pass_report, merge_group="cluster")
        assert False, "nothing to repair when the report already PASSes"
    except UnrepairableFailure:
        pass

    # --- real end-to-end repair loop ---
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test7_repair_stress.blend")
        _build_stress_fixture(fixture_path, entity_count=400)

        # DIAGNOSE via plain `validate` first — confirm the failure is real.
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", PROFILE])
        assert code == 1, f"expected a genuine FAIL over 240fps_esports' budget:\n{out}"
        assert "entity_count = 400 exceeds max_visible_entities = 350" in out

        graph = load_graph(proj_dir)
        source_artifact = find_by_path(graph, fixture_path)
        assert source_artifact["validation_status"] == ART_FAIL
        source_id = source_artifact["artifact_id"]

        # repair without --merge-group must refuse, not guess.
        code, out = _run_cli(["repair", TEST_PROJECT_NAME, "--profile", PROFILE])
        assert code == 1, "must refuse to repair without a merge_group, not silently no-op"

        # repair with --merge-group must genuinely fix it.
        code, out = _run_cli(["repair", TEST_PROJECT_NAME, "--profile", PROFILE, "--merge-group", "cluster"])
        assert code == 0, f"expected the repair to actually fix the budget overage:\n{out}"
        assert "Repair attempt #1" in out
        assert "RESULT: PASS" in out.splitlines()[-1] or "RESULT: PASS" in out

        repaired_path = os.path.join(proj_dir, "repaired", "test7_repair_stress__repair_v1.blend")
        assert os.path.isfile(repaired_path), "repair must write a new, separately-versioned output file"
        assert os.path.isfile(fixture_path), "repair must never touch/overwrite the original failed source"

        # The failed source artifact's status must be untouched by the repair.
        graph = load_graph(proj_dir)
        source_artifact = graph.get(source_id)
        assert source_artifact["validation_status"] == ART_FAIL, \
            "the original FAILED artifact's status must never be overwritten by a repair"

        repaired_artifact = find_by_path(graph, repaired_path)
        assert repaired_artifact is not None
        assert repaired_artifact["artifact_type"] == "optimized_blend"
        assert repaired_artifact["validation_status"] == ART_PASS, \
            "the repaired artifact's status must come from a real revalidate() call"
        assert repaired_artifact["version_id"] == "repair_v1"
        assert repaired_artifact["metadata"]["repairs_artifact"] == source_id
        assert source_id in repaired_artifact["parent_artifacts"]

        # A second repair attempt against the same (still-FAILed) source
        # must get its own new numbered version, not overwrite v1.
        code, out = _run_cli(["repair", TEST_PROJECT_NAME, "--profile", PROFILE, "--merge-group", "cluster"])
        assert code == 0, out
        assert "Repair attempt #2" in out
        repaired_path_v2 = os.path.join(proj_dir, "repaired", "test7_repair_stress__repair_v2.blend")
        assert os.path.isfile(repaired_path_v2)
        assert os.path.isfile(repaired_path), "the first repair attempt's output must still exist, untouched"

        repair_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "repair"]
        assert len(repair_jobs) == 3, "one refused (no merge_group) + two successful repair attempts"
        ready_repair_jobs = [j for j in repair_jobs if j["state"] == READY]
        assert len(ready_repair_jobs) == 2

    finally:
        _cleanup()

    # --- real end-to-end decimate-based repair loop (triangle overage,
    # no merge_group involved or needed) ---
    _cleanup(DECIMATE_PROJECT_NAME)
    try:
        code, out = _run_cli(["create", DECIMATE_PROJECT_NAME])
        assert code == 0, out

        proj_dir = project_dir_for(DECIMATE_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test8_repair_decimate_stress.blend")
        _build_decimate_fixture(fixture_path)

        code, out = _run_cli(["validate", DECIMATE_PROJECT_NAME, "--profile", PROFILE])
        assert code == 1, f"expected a genuine triangle-budget FAIL:\n{out}"
        assert "triangles = 327680 exceeds max_triangles = 250000" in out
        assert "entity_count" not in "\n".join(line for line in out.splitlines() if "exceeds" in line), \
            "this fixture must FAIL on triangles only, isolating the decimate strategy"

        # No --merge-group given and none needed — must still repair.
        code, out = _run_cli(["repair", DECIMATE_PROJECT_NAME, "--profile", PROFILE])
        assert code == 0, f"expected decimation to fix a pure triangle-budget overage:\n{out}"
        assert "decimate geometry to ratio" in out
        assert "RESULT: PASS" in out

        repaired_path = os.path.join(proj_dir, "repaired", "test8_repair_decimate_stress__repair_v1.blend")
        assert os.path.isfile(repaired_path)

        graph = load_graph(proj_dir)
        repaired_artifact = find_by_path(graph, repaired_path)
        assert repaired_artifact is not None
        assert repaired_artifact["validation_status"] == ART_PASS
        assert repaired_artifact["metadata"]["repair_decimate_ratio"] is not None
        assert repaired_artifact["metadata"]["repair_merge_group"] is None

        # Revalidate the repaired output directly, independent of the
        # repair command's own revalidate call — confirms the fix is real
        # and persisted to disk, not just reported.
        code, out = _run_cli(["validate", DECIMATE_PROJECT_NAME, "--blend-file", repaired_path, "--profile", PROFILE])
        assert code == 0, f"the repaired .blend must independently pass validation:\n{out}"

        return True
    finally:
        _cleanup(DECIMATE_PROJECT_NAME)


if __name__ == "__main__":
    ok = run()
    print("test_repair: PASS" if ok else "test_repair: FAIL")
    sys.exit(0 if ok else 1)

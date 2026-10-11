"""Real tests for core/artifact_store.py (item 3 of the user's 4-item
"in order" roadmap list: artifact store/versioning/cache) — no mocks.
Covers the content-addressed object store directly (put/get/has,
deduplication, honest misses), the cache index (lookup/store, stale-
object detection), and a real end-to-end cache hit through
repair/repair_manager.repair_loop against a real Blender fixture: the
second identical repair call must reuse the first call's bytes instead
of invoking Blender again.
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
from core import artifact_store  # noqa: E402
from repair.repair_engine import revalidate as re_revalidate  # noqa: E402
from repair.repair_manager import repair_loop  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Artifact Store ZZZ Temp"
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


def run():
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        proj_dir = project_dir_for(TEST_PROJECT_NAME)

        # --- content-addressed object store: put/get/has, dedup ---
        file_a = os.path.join(proj_dir, "a.bin")
        with open(file_a, "wb") as f:
            f.write(b"hello artifact store")
        hash_a = artifact_store.put(proj_dir, file_a)
        assert artifact_store.has(proj_dir, hash_a)
        stored_path = artifact_store.get(proj_dir, hash_a)
        assert stored_path is not None and os.path.isfile(stored_path)
        with open(stored_path, "rb") as f:
            assert f.read() == b"hello artifact store"

        # storing byte-identical content again is a real no-op, not a
        # second copy -- same hash, same single object on disk.
        file_a_copy = os.path.join(proj_dir, "a_copy.bin")
        shutil.copyfile(file_a, file_a_copy)
        hash_a2 = artifact_store.put(proj_dir, file_a_copy)
        assert hash_a2 == hash_a
        stats = artifact_store.store_stats(proj_dir)
        assert stats["object_count"] == 1, "byte-identical content must be deduplicated, not stored twice"

        # different content -> different object, both retained.
        file_b = os.path.join(proj_dir, "b.bin")
        with open(file_b, "wb") as f:
            f.write(b"different bytes entirely")
        hash_b = artifact_store.put(proj_dir, file_b)
        assert hash_b != hash_a
        stats = artifact_store.store_stats(proj_dir)
        assert stats["object_count"] == 2

        # an unknown hash is an honest miss, never fabricated.
        assert artifact_store.get(proj_dir, "0" * 64) is None
        assert artifact_store.has(proj_dir, "0" * 64) is False

        # --- cache index: lookup/store, exact-match only ---
        params = {"merge_group": "cluster", "decimate_ratio": None}
        assert artifact_store.cache_lookup(proj_dir, "optimize_blend", hash_a, params) is None

        cached_output_hash = artifact_store.cache_store(proj_dir, "optimize_blend", hash_a, params, file_a)
        assert cached_output_hash == hash_a
        hit_path = artifact_store.cache_lookup(proj_dir, "optimize_blend", hash_a, params)
        assert hit_path is not None
        with open(hit_path, "rb") as f:
            assert f.read() == b"hello artifact store"

        # different params against the same input -- a genuinely
        # different cache key, must NOT collide with the first.
        other_params = {"merge_group": "cluster", "decimate_ratio": 0.5}
        assert artifact_store.cache_lookup(proj_dir, "optimize_blend", hash_a, other_params) is None

        # different processor, same input/params -- also must not collide.
        assert artifact_store.cache_lookup(proj_dir, "some_other_tool", hash_a, params) is None

        entries = artifact_store.list_cache_entries(proj_dir)
        assert len(entries) == 1 and entries[0]["object_present"] is True

        # a cache entry whose object got physically removed must report
        # as an honest miss, never a stale hit.
        os.remove(stored_path)
        assert artifact_store.cache_lookup(proj_dir, "optimize_blend", hash_a, params) is None
        entries = artifact_store.list_cache_entries(proj_dir)
        assert entries[0]["object_present"] is False

        # --- `cache` CLI command: real inspection ---
        code, out = _run_cli(["cache", TEST_PROJECT_NAME])
        assert code == 0 and "cache entries: 1" in out

        code, out = _run_cli(["cache", TEST_PROJECT_NAME, "--entries"])
        assert code == 0 and "PRESENT" in out

        # --- real end-to-end cache hit through repair_manager.repair_loop ---
        decimate_fixture_path = os.path.join(proj_dir, "blender", "cache_fixture.blend")
        _build_decimate_fixture(decimate_fixture_path)
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", PROFILE,
                               "--blend-file", decimate_fixture_path])
        assert code == 1
        report = re_revalidate(decimate_fixture_path, PROFILE)
        assert report["result"] == "FAIL"

        first_output = os.path.join(proj_dir, "repaired", "cache_test_v1.blend")
        attempts_1 = repair_loop(report, decimate_fixture_path, PROFILE,
                                  lambda i: first_output, proj_dir=proj_dir)
        assert len(attempts_1) == 1
        assert attempts_1[0]["revalidation"]["result"] == "PASS"
        assert "cache hit" not in attempts_1[0]["repair_result"]["actions"][0], \
            "the FIRST call must do a real Blender repair, not claim a cache hit it hasn't earned"

        stats_after_first = artifact_store.store_stats(proj_dir)
        assert stats_after_first["object_count"] >= 1

        # the SAME source file + SAME decision, run again from scratch —
        # must reuse the cached bytes instead of invoking Blender again.
        second_output = os.path.join(proj_dir, "repaired", "cache_test_v2.blend")
        attempts_2 = repair_loop(report, decimate_fixture_path, PROFILE,
                                  lambda i: second_output, proj_dir=proj_dir)
        assert len(attempts_2) == 1
        assert "cache hit" in attempts_2[0]["repair_result"]["actions"][0], \
            "an identical repeat repair call must hit the cache, not silently recompute"
        assert attempts_2[0]["revalidation"]["result"] == "PASS", \
            "revalidation must still run for real even on a cache hit (Rule 2) -- and must independently confirm PASS"

        # the two outputs must be byte-identical real files, not just a
        # claimed hit -- proof the cache actually reused the same bytes.
        with open(first_output, "rb") as f1, open(second_output, "rb") as f2:
            assert f1.read() == f2.read()

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_artifact_store: PASS" if ok else "test_artifact_store: FAIL")
    sys.exit(0 if ok else 1)

"""Drives the real CLI (cli.main.main), not mocked handlers — including a
genuine end-to-end validate/optimize run against a real Blender-generated
.blend file, per the project brief's "perform real small test operations
with the installed applications, not only mock functions."""
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
from core.artifact_graph import load_graph, find_by_path, PASS as ART_PASS  # noqa: E402
from orchestrator.job import list_jobs, get_job, find_resumable  # noqa: E402
from orchestrator.build_state import READY, FAILED  # noqa: E402

TEST_PROJECT_NAME = "Koba Test CLI ZZZ Temp"
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")


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


def _build_real_fixture_blend(dest_path):
    """Actually invokes Blender headlessly to build+save test1_crate — a
    real asset with real entity_metadata stamped, not a hand-crafted fake
    .blend — then copies it to dest_path."""
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test1_crate.py"],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test1_crate.blend")
    assert os.path.isfile(src), "fixture build did not produce test1_crate.blend"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def run():
    _cleanup()
    try:
        code, out = _run_cli(["doctor"])
        assert "ASSET FACTORY SYSTEM CHECK" in out
        assert code == 0, "expected zero: every required tool (including Krita/FFmpeg) is now installed"

        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        assert "Created project" in out

        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 1, "creating a duplicate project must fail"

        code, out = _run_cli(["status", TEST_PROJECT_NAME])
        assert code == 0
        assert TEST_PROJECT_NAME in out

        code, out = _run_cli(["logs", "--limit", "3"])
        assert code == 0

        code, out = _run_cli(["render", "whatever"])
        assert code == 2, "unimplemented commands must exit non-zero, not silently succeed"

        # --- real integration: validate/optimize against an actual Blender fixture ---
        proj_dir = project_dir_for(TEST_PROJECT_NAME)
        fixture_path = os.path.join(proj_dir, "blender", "test1_crate.blend")
        _build_real_fixture_blend(fixture_path)

        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", "60fps_standard"])
        assert code == 0, f"expected the crate to PASS validation:\n{out}"
        assert "KOBA PERFORMANCE REPORT" in out
        assert "RESULT: PASS" in out

        # --- job abstraction: validate must create a real, persisted, READY job ---
        jobs = list_jobs(proj_dir)
        assert len(jobs) == 1 and jobs[0]["command"] == "validate"
        assert jobs[0]["state"] == READY
        assert jobs[0]["result_summary"] == {"result": "PASS"}

        # --- artifact graph: validate must register/update a real node for the source blend ---
        graph = load_graph(proj_dir)
        source_artifact = find_by_path(graph, fixture_path)
        assert source_artifact is not None, "validate must create an artifact node for the source .blend"
        assert source_artifact["validation_status"] == ART_PASS
        assert source_artifact["metadata"].get("last_validation", {}).get("result") == "PASS"

        code, out = _run_cli(["optimize", TEST_PROJECT_NAME, "--profile", "60fps_standard"])
        assert code == 0, out
        optimized_path = os.path.join(proj_dir, "optimized", "test1_crate.blend")
        assert os.path.isfile(optimized_path), "optimize should have written a copy into optimized/"

        assert os.path.isfile(fixture_path), "optimize must never delete/move the source"

        # --- job abstraction: optimize must create its own separate READY job ---
        jobs = list_jobs(proj_dir)
        optimize_jobs = [j for j in jobs if j["command"] == "optimize"]
        assert len(optimize_jobs) == 1 and optimize_jobs[0]["state"] == READY
        assert optimize_jobs[0]["result_summary"] == {"output_path": optimized_path}

        # --- artifact graph: optimize must add an optimized_blend node parented to the source ---
        graph = load_graph(proj_dir)
        source_artifact = find_by_path(graph, fixture_path)
        optimized_artifact = find_by_path(graph, optimized_path)
        assert optimized_artifact is not None, "optimize must create an artifact node for its output"
        assert optimized_artifact["artifact_type"] == "optimized_blend"
        assert source_artifact["artifact_id"] in optimized_artifact["parent_artifacts"], \
            "optimized_blend artifact must list the source blend as a parent"
        affected = {a["artifact_id"] for a in graph.find_affected(source_artifact["artifact_id"])}
        assert optimized_artifact["artifact_id"] in affected, \
            "find_affected(source) must include the derived optimized_blend artifact"

        # --- real integration: process (Inkscape + ImageMagick) ---
        svg_path = os.path.join(proj_dir, "test_icon_input.svg")
        with open(svg_path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
                    '<rect width="64" height="64" fill="#0f0"/></svg>')

        code, out = _run_cli(["process", TEST_PROJECT_NAME, "--svg", svg_path,
                               "--sizes", "32,64", "--format", "webp", "--basename", "testicon"])
        assert code == 0, out
        for size in (32, 64):
            png = os.path.join(proj_dir, "textures", f"testicon_{size}.png")
            webp = os.path.join(proj_dir, "textures", f"testicon_{size}.webp")
            assert os.path.isfile(png), f"missing {png}"
            assert os.path.isfile(webp), f"missing {webp}"
        assert os.path.isfile(os.path.join(proj_dir, "source", "test_icon_input.svg")), \
            "process must copy the SVG into source/"

        # --- job abstraction: process must create its own separate READY job ---
        jobs = list_jobs(proj_dir)
        process_jobs = [j for j in jobs if j["command"] == "process"]
        assert len(process_jobs) == 1 and process_jobs[0]["state"] == READY
        assert len(jobs) == 3, "validate, optimize, and process must each leave exactly one job record"

        # --- artifact graph: process must build a real svg -> png -> webp chain ---
        graph = load_graph(proj_dir)
        svg_copy_path = os.path.join(proj_dir, "source", "test_icon_input.svg")
        svg_artifact = find_by_path(graph, svg_copy_path)
        assert svg_artifact is not None, "process must create an artifact node for the copied SVG"
        assert svg_artifact["artifact_type"] == "svg_source"

        png_32_path = os.path.join(proj_dir, "textures", "testicon_32.png")
        png_artifact = find_by_path(graph, png_32_path)
        assert png_artifact is not None
        assert png_artifact["artifact_type"] == "texture_png"
        assert svg_artifact["artifact_id"] in png_artifact["parent_artifacts"]

        webp_32_path = os.path.join(proj_dir, "textures", "testicon_32.webp")
        webp_artifact = find_by_path(graph, webp_32_path)
        assert webp_artifact is not None
        assert webp_artifact["artifact_type"] == "texture_webp"
        assert png_artifact["artifact_id"] in webp_artifact["parent_artifacts"], \
            "the webp conversion must be parented to its own PNG, not the SVG directly"

        # the full lineage of the webp must trace back through the png to the svg
        lineage_ids = {a["artifact_id"] for a in graph.lineage(webp_artifact["artifact_id"])}
        assert png_artifact["artifact_id"] in lineage_ids
        assert svg_artifact["artifact_id"] in lineage_ids

        # --- `jobs` CLI command: list + single-job inspection ---
        code, out = _run_cli(["jobs", TEST_PROJECT_NAME])
        assert code == 0
        assert "3 job(s)" in out
        validate_job_id = next(j["job_id"] for j in jobs if j["command"] == "validate")

        code, out = _run_cli(["jobs", TEST_PROJECT_NAME, "--job-id", validate_job_id[:8]])
        assert code == 0
        assert "command: validate" in out
        assert "state:   READY" in out

        # --- `resume` CLI command: genuine re-entry on a real FAILED job ---
        code, out = _run_cli(["validate", TEST_PROJECT_NAME, "--profile", "not_a_real_profile"])
        assert code == 1, "an unknown profile must fail the run, not silently pass"
        failed_job = find_resumable(proj_dir)
        assert failed_job is not None and failed_job["state"] == FAILED
        assert failed_job["args"]["profile"] == "not_a_real_profile"

        code, out = _run_cli(["resume", TEST_PROJECT_NAME])
        assert code == 1, "replaying the same bad profile must fail again, not fake success"
        assert "Resuming job" in out
        assert "not_a_real_profile" in out, "resume must reconstruct the original argv, including the bad profile"

        resumed_job = get_job(proj_dir, failed_job["job_id"])
        assert resumed_job["state"] == FAILED, \
            "the original job must be closed out FAILED since its replay also failed"

        new_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "validate"]
        assert len(new_jobs) == 3, "resume's replay must create its own fresh job, not silently reuse the old one"

        # --- real integration: krita (Krita export) ---
        krita_src = os.path.join(proj_dir, "test_krita_input.png")
        subprocess.run(["magick", "-size", "48x48", "xc:blue", krita_src], check=True, capture_output=True)

        code, out = _run_cli(["krita", TEST_PROJECT_NAME, "--source", krita_src, "--format", "jpg"])
        assert code == 0, out
        krita_out = os.path.join(proj_dir, "textures", "test_krita_input.jpg")
        assert os.path.isfile(krita_out), f"missing {krita_out}"

        graph = load_graph(proj_dir)
        kra_source_copy = os.path.join(proj_dir, "source", "test_krita_input.png")
        kra_artifact = find_by_path(graph, kra_source_copy)
        assert kra_artifact is not None and kra_artifact["artifact_type"] == "kra_source"
        raster_artifact = find_by_path(graph, krita_out)
        assert raster_artifact is not None and raster_artifact["artifact_type"] == "texture_raster"
        assert kra_artifact["artifact_id"] in raster_artifact["parent_artifacts"]

        krita_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "krita"]
        assert len(krita_jobs) == 1 and krita_jobs[0]["state"] == READY

        # --- real integration: gimp (GIMP export) ---
        gimp_src = os.path.join(proj_dir, "test_gimp_input.png")
        subprocess.run(["magick", "-size", "48x48", "xc:purple", gimp_src], check=True, capture_output=True)

        code, out = _run_cli(["gimp", TEST_PROJECT_NAME, "--source", gimp_src, "--format", "jpg"])
        assert code == 0, out
        gimp_out = os.path.join(proj_dir, "textures", "test_gimp_input.jpg")
        assert os.path.isfile(gimp_out), f"missing {gimp_out}"

        graph = load_graph(proj_dir)
        xcf_source_copy = os.path.join(proj_dir, "source", "test_gimp_input.png")
        xcf_artifact = find_by_path(graph, xcf_source_copy)
        assert xcf_artifact is not None and xcf_artifact["artifact_type"] == "xcf_source"
        gimp_raster_artifact = find_by_path(graph, gimp_out)
        assert gimp_raster_artifact is not None and gimp_raster_artifact["artifact_type"] == "texture_raster"
        assert xcf_artifact["artifact_id"] in gimp_raster_artifact["parent_artifacts"]

        gimp_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "gimp"]
        assert len(gimp_jobs) == 1 and gimp_jobs[0]["state"] == READY

        # --- real integration: ffmpeg (transcode + thumbnail) ---
        ffmpeg_src = os.path.join(proj_dir, "test_clip.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=32x32:rate=5", ffmpeg_src],
            check=True, capture_output=True,
        )

        code, out = _run_cli(["ffmpeg", TEST_PROJECT_NAME, "--source", ffmpeg_src])
        assert code == 1, "ffmpeg with neither --transcode nor --thumbnail must refuse, not silently no-op"

        code, out = _run_cli(["ffmpeg", TEST_PROJECT_NAME, "--source", ffmpeg_src,
                               "--transcode", "webm", "--thumbnail", "00:00:00"])
        assert code == 0, out
        transcoded = os.path.join(proj_dir, "media", "test_clip.webm")
        thumb = os.path.join(proj_dir, "textures", "test_clip_thumb.png")
        assert os.path.isfile(transcoded), f"missing {transcoded}"
        assert os.path.isfile(thumb), f"missing {thumb}"

        graph = load_graph(proj_dir)
        video_source_copy = os.path.join(proj_dir, "source", "test_clip.mp4")
        video_artifact = find_by_path(graph, video_source_copy)
        assert video_artifact is not None and video_artifact["artifact_type"] == "video_source"
        transcoded_artifact = find_by_path(graph, transcoded)
        assert transcoded_artifact is not None and transcoded_artifact["artifact_type"] == "video_transcoded"
        thumb_artifact = find_by_path(graph, thumb)
        assert thumb_artifact is not None and thumb_artifact["artifact_type"] == "texture_png"
        assert video_artifact["artifact_id"] in transcoded_artifact["parent_artifacts"]
        assert video_artifact["artifact_id"] in thumb_artifact["parent_artifacts"]

        # The "nothing to do" refusal above happens before job creation
        # (it's a usage error, not a job failure) — only the successful
        # run created a job.
        ffmpeg_jobs = [j for j in list_jobs(proj_dir) if j["command"] == "ffmpeg"]
        assert len(ffmpeg_jobs) == 1 and ffmpeg_jobs[0]["state"] == READY

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_cli: PASS" if ok else "test_cli: FAIL")
    sys.exit(0 if ok else 1)

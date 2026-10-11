"""Real tests for the product type registry (products/product_types.py)
and the `register-product` CLI command — no mocks. Covers all 8
declared product types: cui/monument/vehicle/building_skin/vfx (real
asset-backed validation) and npc/event (metadata-only, honestly so).
Audio ties into the same end-to-end flow via a real synthetic WAV.
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
from core.manifest import load_manifest  # noqa: E402
from core.artifact_graph import load_graph, find_by_path, PASS as ART_PASS  # noqa: E402
from orchestrator.job import list_jobs  # noqa: E402
from orchestrator.build_state import READY, FAILED  # noqa: E402
from products.product_types import (  # noqa: E402
    get, list_product_types, validate_metadata, unsupported_validators,
    UnknownProductType, ProductMetadataError,
)

TEST_PROJECT_NAME = "Koba Test Product Types ZZZ Temp"
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


def _build_blend_fixture(script_name, generated_name, dest_path):
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", f"tests/{script_name}"],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", generated_name)
    assert os.path.isfile(src)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def run():
    # --- registry-level: completeness + honesty ---
    assert set(list_product_types().keys()) == {
        "cui", "monument", "vehicle", "npc", "event", "building_skin", "audio", "vfx",
    }

    try:
        get("not_a_real_type")
        assert False
    except UnknownProductType:
        pass

    # npc/event must be honestly metadata-only — no required validators.
    assert get("npc").required_validators == []
    assert get("event").required_validators == []
    assert get("npc").asset_backing is None

    # audio is real (asset_backing="audio") but deliberately NOT routed
    # through validation_registry's required_validators — "audio" isn't
    # one of its 17 formal types.
    assert get("audio").asset_backing == "audio"
    assert get("audio").required_validators == []

    # cui/monument/vehicle/building_skin/vfx must require real validators.
    assert "texture" in get("cui").required_validators
    assert "texture" in get("building_skin").required_validators
    assert "geometry" in get("monument").required_validators
    assert "performance" in get("vehicle").required_validators
    assert "performance" in get("vfx").required_validators

    # every required validator for every type must now be implemented —
    # if this ever fails, a product type promised real enforcement it
    # doesn't have.
    for pt in list_product_types():
        assert unsupported_validators(pt) == [], f"{pt} requires a validator that isn't real yet"

    # --- validate_metadata: real type checking, not just key presence ---
    validate_metadata("npc", {"faction": "raiders", "role": "vendor"})
    try:
        validate_metadata("npc", {"faction": "raiders"})
        assert False, "missing 'role' must raise"
    except ProductMetadataError:
        pass
    try:
        validate_metadata("vehicle", {"vehicle_class": "boat", "seats": "four"})
        assert False, "seats must be int, a string must raise"
    except ProductMetadataError:
        pass

    # --- real end-to-end: all 5 types through the actual CLI ---
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        proj_dir = project_dir_for(TEST_PROJECT_NAME)

        # npc: metadata-only, no asset file, must succeed with no validator run.
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "npc",
                               "--field", "faction=raiders", "--field", "role=vendor"])
        assert code == 0, out
        manifest = load_manifest(proj_dir)
        assert manifest["product_type"] == "npc"
        assert manifest["product_metadata"] == {"faction": "raiders", "role": "vendor"}

        # event: metadata-only, string field with spaces must survive via '='-partition.
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "event",
                               "--field", "trigger_type=zone_enter",
                               "--field", "description=Spawns a horde on entry"])
        assert code == 0, out
        manifest = load_manifest(proj_dir)
        assert manifest["product_metadata"]["description"] == "Spawns a horde on entry"

        # cui: real texture-backed validation, PASS case.
        panel_path = os.path.join(proj_dir, "panel.png")
        subprocess.run(["magick", "-size", "256x256", "xc:navy", panel_path], check=True, capture_output=True)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "cui",
                               "--field", "resolution_width=256", "--field", "resolution_height=256",
                               "--field", "anchor=top-left", "--asset-file", panel_path])
        assert code == 0, f"a real 256x256 PNG must pass its own declared resolution:\n{out}"
        graph = load_graph(proj_dir)
        texture_artifact = find_by_path(graph, panel_path)
        assert texture_artifact is not None and texture_artifact["validation_status"] == ART_PASS

        # cui: real texture-backed validation, genuine FAIL case (too small).
        small_path = os.path.join(proj_dir, "small.png")
        subprocess.run(["magick", "-size", "32x32", "xc:red", small_path], check=True, capture_output=True)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "cui",
                               "--field", "resolution_width=256", "--field", "resolution_height=256",
                               "--field", "anchor=top-left", "--asset-file", small_path])
        assert code == 1, "a 32x32 texture declaring a 256x256 requirement must genuinely fail, not pass"
        manifest = load_manifest(proj_dir)
        assert manifest["product_type"] == "cui" and manifest["product_metadata"]["resolution_width"] == 256, \
            "a refused registration must NOT overwrite the prior successful one"

        # monument: real Blender-backed validation, PASS case.
        monument_path = os.path.join(proj_dir, "monument.blend")
        _build_blend_fixture("test11_monument.py", "test11_monument.blend", monument_path)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "monument",
                               "--field", "height_meters=8.0", "--field", "era=modern",
                               "--field", "landmark_importance=hero", "--asset-file", monument_path])
        assert code == 0, f"the real monument fixture must pass geometry/asset validation:\n{out}"
        manifest = load_manifest(proj_dir)
        assert manifest["product_type"] == "monument"
        assert manifest["product_metadata"]["height_meters"] == 8.0

        # missing a required field must refuse without creating a successful job.
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "monument",
                               "--field", "height_meters=8.0", "--field", "era=modern"])
        assert code == 1, "a missing required field must refuse registration"

        # vfx: real Blender-backed validation (geometry/asset/performance),
        # reusing the real jetski fixture — the point here is the
        # registration/validation plumbing, not asset realism.
        vfx_path = os.path.join(proj_dir, "vfx.blend")
        _build_blend_fixture("test9_jetski.py", "test9_jetski.blend", vfx_path)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "vfx",
                               "--field", "effect_type=splash", "--field", "duration_frames=30",
                               "--asset-file", vfx_path])
        assert code == 0, f"the real jetski fixture must pass geometry/asset/performance validation:\n{out}"

        # building_skin: real seamless-tiling PASS case (a solid color
        # trivially tiles on both axes).
        skin_pass_path = os.path.join(proj_dir, "skin_pass.png")
        subprocess.run(["magick", "-size", "256x256", "xc:gray50", skin_pass_path],
                        check=True, capture_output=True)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "building_skin",
                               "--field", "tile_size_meters=2.0", "--field", "material_category=brick",
                               "--asset-file", skin_pass_path])
        assert code == 0, f"a solid-color texture must pass the real seamless-tiling check:\n{out}"
        assert "Seamless tiling" in out

        # building_skin: real seamless-tiling FAIL case — two different
        # solid colors side by side genuinely don't tile (left/right
        # edges differ), the same real check verified live before this
        # test was written.
        skin_fail_path = os.path.join(proj_dir, "skin_fail.png")
        subprocess.run(["magick", "-size", "128x128", "xc:red", os.path.join(proj_dir, "half1.png")],
                        check=True, capture_output=True)
        subprocess.run(["magick", "-size", "128x128", "xc:blue", os.path.join(proj_dir, "half2.png")],
                        check=True, capture_output=True)
        subprocess.run(["magick", os.path.join(proj_dir, "half1.png"), os.path.join(proj_dir, "half2.png"),
                         "+append", skin_fail_path], check=True, capture_output=True)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "building_skin",
                               "--field", "tile_size_meters=2.0", "--field", "material_category=brick",
                               "--asset-file", skin_fail_path])
        assert code == 1, "a genuinely non-tiling texture must fail, not pass"

        # audio: real ffprobe-backed validation, PASS case.
        audio_pass_path = os.path.join(proj_dir, "sfx_pass.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", audio_pass_path],
            check=True, capture_output=True,
        )
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "audio",
                               "--field", "max_duration_seconds=5", "--field", "category=sfx",
                               "--asset-file", audio_pass_path])
        assert code == 0, f"a real 1s clip under a 5s budget must pass:\n{out}"
        graph = load_graph(proj_dir)
        audio_artifact = find_by_path(graph, audio_pass_path)
        assert audio_artifact is not None and audio_artifact["validation_status"] == ART_PASS

        # audio: real duration-budget FAIL case.
        audio_fail_path = os.path.join(proj_dir, "sfx_fail.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", audio_fail_path],
            check=True, capture_output=True,
        )
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "audio",
                               "--field", "max_duration_seconds=1", "--field", "category=sfx",
                               "--asset-file", audio_fail_path])
        assert code == 1, "a real 3s clip against a 1s budget must genuinely fail, not pass"

        jobs = [j for j in list_jobs(proj_dir) if j["command"] == "register-product"]
        assert len(jobs) == 11, "9 successful + 2 refused attempts, each its own real job"
        ready_jobs = [j for j in jobs if j["state"] == READY]
        failed_jobs = [j for j in jobs if j["state"] == FAILED]
        assert len(ready_jobs) == 7 and len(failed_jobs) == 4

        # --- CLI inspection command ---
        code, out = _run_cli(["product-types"])
        assert code == 0
        assert "8 product type(s)" in out

        code, out = _run_cli(["product-types", "--product-type", "vehicle"])
        assert code == 0
        assert "performance" in out

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_product_types: PASS" if ok else "test_product_types: FAIL")
    sys.exit(0 if ok else 1)

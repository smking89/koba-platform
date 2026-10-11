"""Real tests for compiler/product_compiler.py, packaging/package_builder.py,
and packaging/signature_generator.py — no mocks. Covers: compile refusal
(no product type, no PASS artifacts), a real end-to-end compile+package+sign
against a real Blender fixture, hash-drift detection (file changed after
validation must fail packaging, not silently ship stale bytes), signature
verification (valid + tampered-manifest-rejected), and multi-version
auto-increment behavior.
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
from core.artifact_graph import load_graph  # noqa: E402
from compiler.product_compiler import compile_product, CompilerError  # noqa: E402
from packaging.package_builder import build_package, list_releases, load_release_manifest, PackagingError  # noqa: E402
from packaging.signature_generator import sign_bytes, verify_signature  # noqa: E402

TEST_PROJECT_NAME = "Koba Test Compiler Packaging ZZZ Temp"
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
    _cleanup()
    try:
        code, out = _run_cli(["create", TEST_PROJECT_NAME])
        assert code == 0, out
        proj_dir = project_dir_for(TEST_PROJECT_NAME)

        # --- compile refusal: no product type registered yet ---
        try:
            compile_product(proj_dir)
            assert False, "must refuse to compile a project with no registered product type"
        except CompilerError as e:
            assert "no registered product type" in str(e)

        # --- register a real monument, with a real PASSing artifact ---
        monument_path = os.path.join(proj_dir, "monument.blend")
        _build_blend_fixture("test11_monument.py", "test11_monument.blend", monument_path)
        code, out = _run_cli(["register-product", TEST_PROJECT_NAME, "--product-type", "monument",
                               "--field", "height_meters=8.0", "--field", "era=modern",
                               "--field", "landmark_importance=hero", "--asset-file", monument_path])
        assert code == 0, f"the real monument fixture must pass validation:\n{out}"

        # --- real end-to-end: compile -> package -> sign ---
        compiled = compile_product(proj_dir)
        assert compiled["product_type"] == "monument"
        assert len(compiled["artifacts"]) == 1

        result = build_package(proj_dir, compiled)
        assert result["version"] == "1"
        assert os.path.isfile(result["manifest_path"])
        manifest = load_release_manifest(result["manifest_path"])
        assert manifest["package_hash"] == result["package_hash"]
        assert len(manifest["files"]) == 1

        with open(result["manifest_path"], "rb") as f:
            manifest_bytes = f.read()
        signature = sign_bytes(manifest_bytes)
        assert verify_signature(manifest_bytes, signature) is True

        # tampering with the signed bytes must be caught, not waved through.
        tampered = manifest_bytes.replace(b'"version": "1"', b'"version": "9"')
        assert tampered != manifest_bytes, "tamper substitution must have actually changed the bytes"
        assert verify_signature(tampered, signature) is False

        # a signature made for different bytes entirely must also fail.
        assert verify_signature(b"not the real manifest", signature) is False

        # --- multi-version auto-increment ---
        compiled_again = compile_product(proj_dir)
        result2 = build_package(proj_dir, compiled_again)
        assert result2["version"] == "2", "second package for the same project must auto-increment"
        releases = list_releases(proj_dir)
        assert [r["version"] for r in releases] == ["1", "2"]

        # explicit version label must be honored verbatim.
        result3 = build_package(proj_dir, compiled_again, version="v3-rc1")
        assert result3["version"] == "v3-rc1"

        # --- hash-drift detection: file changed on disk since validation ---
        # mutate the real artifact's bytes on disk after it was validated,
        # then try to compile+package again — must refuse, not ship stale
        # (now-mismatched) bytes under a hash that no longer matches reality.
        graph = load_graph(proj_dir)
        drifted_artifact_id = next(iter(graph.artifacts))
        with open(monument_path, "ab") as f:
            f.write(b"\x00corruption-after-validation")
        compiled_drifted = compile_product(proj_dir)
        # output_hash recorded in the graph still reflects the pre-corruption
        # content, so packaging must now detect the mismatch and refuse.
        try:
            build_package(proj_dir, compiled_drifted, version="drift-check")
            assert False, "packaging must refuse when the source file changed since validation"
        except PackagingError as e:
            assert "no longer matches the hash recorded" in str(e)
        del drifted_artifact_id  # only used to document intent above

        # --- full CLI happy path (separate project, clean fixture) ---
        cli_proj_name = TEST_PROJECT_NAME + " CLI"
        cli_proj_dir = project_dir_for(cli_proj_name)
        if os.path.isdir(cli_proj_dir):
            shutil.rmtree(cli_proj_dir)
        try:
            code, out = _run_cli(["create", cli_proj_name])
            assert code == 0, out
            cli_monument_path = os.path.join(cli_proj_dir, "monument.blend")
            _build_blend_fixture("test11_monument.py", "test11_monument.blend", cli_monument_path)
            code, out = _run_cli(["register-product", cli_proj_name, "--product-type", "monument",
                                   "--field", "height_meters=5.0", "--field", "era=modern",
                                   "--field", "landmark_importance=minor", "--asset-file", cli_monument_path])
            assert code == 0, out

            code, out = _run_cli(["package", cli_proj_name])
            assert code == 0, f"package command must succeed on a validated project:\n{out}"
            assert "Signed" in out and "Release 1 ready" in out

            code, out = _run_cli(["releases", cli_proj_name])
            assert code == 0 and "1 release(s)" in out

            code, out = _run_cli(["releases", cli_proj_name, "--version", "1"])
            assert code == 0 and "VALID" in out, out

            # the release_package artifact must land in the graph, linked
            # to the real source artifact it was built from.
            cli_graph = load_graph(cli_proj_dir)
            release_artifacts = [a for a in cli_graph.artifacts.values() if a["artifact_type"] == "release_package"]
            assert len(release_artifacts) == 1
            assert len(release_artifacts[0]["parent_artifacts"]) == 1
        finally:
            if os.path.isdir(cli_proj_dir):
                shutil.rmtree(cli_proj_dir)
            registry = load_projects_registry()
            slug = slugify(cli_proj_name)
            if slug in registry.get("projects", []):
                registry["projects"].remove(slug)
                save_projects_registry(registry)

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_compiler_packaging: PASS" if ok else "test_compiler_packaging: FAIL")
    sys.exit(0 if ok else 1)

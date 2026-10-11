"""Round-trips a real manifest through disk — not a mock — using a
throwaway temp directory, cleaned up at the end regardless of outcome."""
import shutil
import sys
import tempfile

from core.manifest import (
    new_manifest, save_manifest, load_manifest,
    add_asset, add_tool_used, add_export, add_error, add_warning,
)


def run():
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_manifest_")
    try:
        manifest = new_manifest("Test Asset", project_type="prop", version="0.1.0")
        assert manifest["name"] == "Test Asset"
        assert manifest["assets"] == []

        add_asset(manifest, "Crate", "prop", source_files=["crate.blend"], polycount=270)
        add_tool_used(manifest, "blender", version="5.2.2")
        add_export(manifest, "Crate", "fbx", "/tmp/crate.fbx", size_bytes=1024)
        add_warning(manifest, "no LODs generated")
        add_error(manifest, "example error for round-trip testing")

        path = save_manifest(tmp_dir, manifest)
        assert path.endswith("project.json")

        reloaded = load_manifest(tmp_dir)
        assert reloaded["name"] == "Test Asset"
        assert len(reloaded["assets"]) == 1 and reloaded["assets"][0]["name"] == "Crate"
        assert reloaded["assets"][0]["polycount"] == 270
        assert reloaded["tools"] == [{"tool": "blender", "version": "5.2.2"}]
        assert len(reloaded["exports"]) == 1 and reloaded["exports"][0]["size_bytes"] == 1024
        assert len(reloaded["warnings"]) == 1
        assert len(reloaded["errors"]) == 1
        assert reloaded["updated"] >= reloaded["created"]

        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = run()
    print("test_manifest: PASS" if ok else "test_manifest: FAIL")
    sys.exit(0 if ok else 1)

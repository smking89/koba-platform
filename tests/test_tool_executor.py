"""Real tests for the tool-contract authorization boundary — a genuine
Blender subprocess call through the executor, a genuine permission
denial, a genuine schema rejection, a genuine unsupported-capability
refusal. No mocks."""
import os
import subprocess
import sys

from tools import tool_registry
from tools import registered_tools
from tools.tool_executor import execute, ToolNotFound, UnsupportedCapability
from tools.tool_permissions import PermissionDenied
from tools.tool_schemas import SchemaValidationError
from tools.tool_contracts import ToolContract
from tools.tool_audit import read_recent
from core.config import load_tools_config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")


def _build_real_fixture_blend():
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test1_crate.py"],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    path = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test1_crate.blend")
    assert os.path.isfile(path)
    return path


def run():
    tool_registry.clear()
    registered_tools.register_all()

    fixture_path = _build_real_fixture_blend()

    # --- unknown tool ---
    try:
        execute("does_not_exist", "cli")
        assert False, "should have raised ToolNotFound"
    except ToolNotFound:
        pass

    # --- schema rejection: missing required field ---
    try:
        execute("validate_blend", "cli", profile_name="60fps_standard")  # missing blend_path
        assert False, "should have raised SchemaValidationError"
    except SchemaValidationError:
        pass

    # --- permission denial: caller not in allowed_callers ---
    try:
        execute("validate_blend", "some_random_unauthorized_agent", blend_path=fixture_path)
        assert False, "should have raised PermissionDenied"
    except PermissionDenied:
        pass

    # --- unsupported capability: a tool requiring something not installed ---
    tool_registry.register(ToolContract(
        tool_id="fake_tool_needs_missing_capability", name="Fake", version="1.0",
        implementation=lambda: None,
        required_capabilities=["definitely_not_a_real_tool_xyz123"],
        allowed_callers=["cli"],
    ))
    try:
        execute("fake_tool_needs_missing_capability", "cli")
        assert False, "should have raised UnsupportedCapability"
    except UnsupportedCapability:
        pass

    # --- the real path: authorized caller, valid input, real capability present ---
    result = execute("validate_blend", "cli", blend_path=fixture_path, profile_name="60fps_standard")
    assert result["result"] in ("PASS", "FAIL")
    assert result["asset_name"] == "Crate"

    # blender_agent is also authorized per the contract's allowed_callers
    result2 = execute("validate_blend", "blender_agent", blend_path=fixture_path, profile_name="60fps_standard")
    assert result2["result"] == result["result"]

    # --- audit log reflects both the failures and the successes ---
    recent = read_recent(limit=50)
    tool_ids_seen = [e["tool_id"] for e in recent]
    assert "validate_blend" in tool_ids_seen
    assert any(not e["success"] for e in recent if e["tool_id"] == "validate_blend"), \
        "the permission-denied validate_blend call must be recorded as a failure in the audit log"
    assert any(e["success"] for e in recent if e["tool_id"] == "validate_blend"), \
        "the successful validate_blend call must be recorded as a success in the audit log"

    return True


if __name__ == "__main__":
    ok = run()
    print("test_tool_executor: PASS" if ok else "test_tool_executor: FAIL")
    sys.exit(0 if ok else 1)

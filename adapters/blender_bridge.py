"""Bridges the orchestration CLI (runs under system Python) to the
Blender adapter's headless scripts (run inside Blender's own Python).
Shells out to a real Blender subprocess — this file has no `bpy` import
of its own and can't; it only knows how to invoke the executable and
parse the one JSON line each script prints.
"""
import json
import os
import subprocess

from core.detection import detect_tool

BLENDER_ADAPTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender")
SCRIPTS_DIR = os.path.join(BLENDER_ADAPTER_DIR, "scripts")


class BlenderBridgeError(Exception):
    pass


def get_blender_executable():
    status = detect_tool("blender")
    if not status.found:
        raise BlenderBridgeError(f"Blender not found: {status.error}. Check config/tools.yaml.")
    return status.executable


def _extract_json(stdout):
    """Our scripts print exactly one JSON object as their last non-empty
    stdout line — everything before it is Blender's own startup banner or
    our INFO logs, which aren't JSON."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return None


def _run_script(script_name, args, timeout=180):
    blender = get_blender_executable()
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [blender, "-b", "--python", script_path, "--", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    parsed = _extract_json(result.stdout)
    if parsed is None:
        raise BlenderBridgeError(
            f"No JSON output from {script_name} (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if "error" in parsed:
        raise BlenderBridgeError(f"{script_name} reported: {parsed['error']}")
    return parsed


def validate_blend(blend_path, profile_name="60fps_standard", asset_name=None):
    args = [blend_path, profile_name]
    if asset_name:
        args.append(asset_name)
    return _run_script("run_validate.py", args)


def optimize_blend(blend_path, output_path, profile_name="60fps_standard",
                    asset_name=None, merge_group=None, decimate_ratio=None):
    args = [blend_path, output_path, profile_name]
    if asset_name:
        args.append(asset_name)
    if merge_group:
        args += ["--merge-group", merge_group]
    if decimate_ratio is not None:
        args += ["--decimate-ratio", str(decimate_ratio)]
    return _run_script("run_optimize.py", args)

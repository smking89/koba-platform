"""Detects installed creative applications. Never assumes a tool exists —
every result here comes from actually locating and (where practical)
running the executable, not from guessing paths."""
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from core.config import load_tools_config, PROJECT_ROOT

REQUIRED_TOOLS = ("blender", "inkscape", "gimp", "krita", "imagemagick", "ffmpeg")
OPTIONAL_TOOLS = ("freecad", "fontforge", "godot")

_VERSION_FLAGS = {
    "blender": ["--version"],
    "inkscape": ["--version"],
    "gimp": ["-v"],
    "krita": ["--version"],
    "imagemagick": ["-version"],
    "ffmpeg": ["-version"],
    "freecad": ["--version"],
    "fontforge": ["-version"],
    "godot": ["--version"],
}


@dataclass
class ToolStatus:
    name: str
    found: bool
    executable: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None
    required: bool = True


def _resolve_executable(tool_name, tool_cfg):
    """Configured path wins if set; otherwise try each candidate name on PATH."""
    configured = (tool_cfg or {}).get("executable")
    if configured:
        # A relative path (e.g. "bin/gimp-flatpak-wrapper.sh") must resolve
        # against PROJECT_ROOT, not whatever directory the CLI happened to
        # be invoked from — otherwise this "works when I test it" and then
        # silently breaks the moment someone runs asset-factory from
        # elsewhere.
        candidate_path = configured if os.path.isabs(configured) else os.path.join(PROJECT_ROOT, configured)
        if shutil.which(configured) or os.path.isfile(candidate_path):
            return candidate_path if os.path.isfile(candidate_path) else configured
        return None  # explicitly configured but not actually there — don't silently fall back

    for candidate in (tool_cfg or {}).get("candidates", [tool_name]):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _get_version(tool_name, executable):
    flags = _VERSION_FLAGS.get(tool_name, ["--version"])
    try:
        result = subprocess.run(
            [executable, *flags],
            capture_output=True, text=True, timeout=15,
        )
        output = (result.stdout or result.stderr or "").strip()
        return output.splitlines()[0] if output else None
    except Exception as e:
        return f"(version check failed: {e})"


def detect_tool(tool_name, required=True):
    tools_cfg = load_tools_config()
    tool_cfg = tools_cfg.get(tool_name, {})
    executable = _resolve_executable(tool_name, tool_cfg)

    if not executable:
        return ToolStatus(name=tool_name, found=False, required=required,
                           error="not found on PATH and not configured in config/tools.yaml")

    version = _get_version(tool_name, executable)
    return ToolStatus(name=tool_name, found=True, executable=executable, version=version, required=required)


def detect_all():
    results = {}
    for name in REQUIRED_TOOLS:
        results[name] = detect_tool(name, required=True)
    for name in OPTIONAL_TOOLS:
        results[name] = detect_tool(name, required=False)
    return results


def system_ready(results=None):
    results = results or detect_all()
    return all(status.found for status in results.values() if status.required)

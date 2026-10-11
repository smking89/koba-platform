"""Registers the real tool contracts wrapping this repo's actual working
adapters. Import this module once (main() does it at startup) before
calling tool_executor.execute() — nothing is registered until it runs.

Each contract's `implementation` is a thin wrapper, not new logic — the
real work still happens in adapters/blender_bridge.py,
adapters/inkscape_adapter.py, adapters/imagemagick_adapter.py exactly as
before. This module only adds the authorization/schema layer in front of
calls that used to go straight to those adapters.
"""
from adapters.blender_bridge import validate_blend, optimize_blend
from adapters.inkscape_adapter import InkscapeAdapter
from adapters.imagemagick_adapter import ImageMagickAdapter
from adapters.krita_adapter import KritaAdapter
from adapters.ffmpeg_adapter import FFmpegAdapter
from adapters.gimp_adapter import GimpAdapter
from tools.tool_contracts import ToolContract
from tools.tool_registry import register, get


def _export_svg_variants(svg_path, output_dir, basename, widths):
    adapter = InkscapeAdapter()
    if not adapter.detect():
        raise RuntimeError("Inkscape not detected")
    return adapter.export_variants(svg_path, output_dir, basename, widths=widths)


def _convert_image_format(src_path, dst_path):
    adapter = ImageMagickAdapter()
    if not adapter.detect():
        raise RuntimeError("ImageMagick not detected")
    return adapter.convert_format(src_path, dst_path)


def _krita_export(src_path, dst_path):
    adapter = KritaAdapter()
    if not adapter.detect():
        raise RuntimeError("Krita not detected")
    return adapter.export_to(src_path, dst_path)


def _ffmpeg_transcode(src_path, dst_path):
    adapter = FFmpegAdapter()
    if not adapter.detect():
        raise RuntimeError("FFmpeg not detected")
    return adapter.transcode(src_path, dst_path)


def _ffmpeg_extract_frame(src_path, dst_path, timestamp="00:00:01"):
    adapter = FFmpegAdapter()
    if not adapter.detect():
        raise RuntimeError("FFmpeg not detected")
    return adapter.extract_frame(src_path, dst_path, timestamp=timestamp)


def _gimp_export(src_path, dst_path):
    adapter = GimpAdapter()
    if not adapter.detect():
        raise RuntimeError("GIMP not detected")
    return adapter.export_to(src_path, dst_path)


def register_all():
    """Idempotent-ish: registering twice raises (tool_registry.register
    guards against silent duplicate registration) — call tool_registry.clear()
    first if you need to re-register (tests do this)."""
    if get("validate_blend") is not None:
        return  # already registered this process

    register(ToolContract(
        tool_id="validate_blend", name="Validate Blender Asset", version="1.0",
        implementation=validate_blend,
        input_schema={
            "blend_path": {"type": str, "required": True},
            "profile_name": {"type": str, "required": False},
            "asset_name": {"type": (str, type(None)), "required": False},
        },
        output_schema={
            "asset_name": {"type": str, "required": True},
            "profile": {"type": str, "required": True},
            "result": {"type": str, "required": True},
            "metrics": {"type": dict, "required": True},
            "warnings": {"type": list, "required": True},
            "failures": {"type": list, "required": True},
        },
        required_capabilities=["blender"],
        allowed_callers=["cli", "blender_agent", "repair_engine", "repair_agent"],
        timeout=180,
        required_artifact_types=["blend_source"],
        produced_artifact_types=[],
    ))

    register(ToolContract(
        tool_id="optimize_blend", name="Optimize Blender Asset", version="1.0",
        implementation=optimize_blend,
        input_schema={
            "blend_path": {"type": str, "required": True},
            "output_path": {"type": str, "required": True},
            "profile_name": {"type": str, "required": False},
            "asset_name": {"type": (str, type(None)), "required": False},
            "merge_group": {"type": (str, type(None)), "required": False},
            "decimate_ratio": {"type": (float, int, type(None)), "required": False},
        },
        output_schema={
            "asset_name": {"type": str, "required": True},
            "output_path": {"type": str, "required": True},
            "actions": {"type": list, "required": True},
            "metrics_before": {"type": dict, "required": True},
            "metrics_after": {"type": dict, "required": True},
        },
        required_capabilities=["blender"],
        allowed_callers=["cli", "blender_agent", "repair_engine", "repair_agent"],
        timeout=180,
        required_artifact_types=["blend_source"],
        produced_artifact_types=["optimized_blend"],
    ))

    register(ToolContract(
        tool_id="export_svg_variants", name="Export SVG to PNG variants", version="1.0",
        implementation=_export_svg_variants,
        input_schema={
            "svg_path": {"type": str, "required": True},
            "output_dir": {"type": str, "required": True},
            "basename": {"type": str, "required": True},
            "widths": {"type": (list, tuple), "required": True},
        },
        required_capabilities=["inkscape"],
        allowed_callers=["cli"],
        timeout=60,
        required_artifact_types=["svg_source"],
        produced_artifact_types=["texture_png"],
    ))

    register(ToolContract(
        tool_id="convert_image_format", name="Convert Image Format", version="1.0",
        implementation=_convert_image_format,
        input_schema={
            "src_path": {"type": str, "required": True},
            "dst_path": {"type": str, "required": True},
        },
        required_capabilities=["imagemagick"],
        allowed_callers=["cli"],
        timeout=60,
        required_artifact_types=["texture_png"],
        produced_artifact_types=["texture_webp"],
    ))

    register(ToolContract(
        tool_id="krita_export", name="Export Krita Document", version="1.0",
        implementation=_krita_export,
        input_schema={
            "src_path": {"type": str, "required": True},
            "dst_path": {"type": str, "required": True},
        },
        required_capabilities=["krita"],
        allowed_callers=["cli"],
        timeout=120,
        required_artifact_types=["kra_source"],
        produced_artifact_types=["texture_raster"],
    ))

    register(ToolContract(
        tool_id="ffmpeg_transcode", name="Transcode Video/Audio", version="1.0",
        implementation=_ffmpeg_transcode,
        input_schema={
            "src_path": {"type": str, "required": True},
            "dst_path": {"type": str, "required": True},
        },
        required_capabilities=["ffmpeg"],
        allowed_callers=["cli"],
        timeout=180,
        required_artifact_types=["video_source"],
        produced_artifact_types=["video_transcoded"],
    ))

    register(ToolContract(
        tool_id="ffmpeg_extract_frame", name="Extract Video Frame", version="1.0",
        implementation=_ffmpeg_extract_frame,
        input_schema={
            "src_path": {"type": str, "required": True},
            "dst_path": {"type": str, "required": True},
            "timestamp": {"type": str, "required": False},
        },
        required_capabilities=["ffmpeg"],
        allowed_callers=["cli"],
        timeout=60,
        required_artifact_types=["video_source"],
        produced_artifact_types=["texture_png"],
    ))

    register(ToolContract(
        tool_id="gimp_export", name="Export GIMP Document", version="1.0",
        implementation=_gimp_export,
        input_schema={
            "src_path": {"type": str, "required": True},
            "dst_path": {"type": str, "required": True},
        },
        required_capabilities=["gimp"],
        allowed_callers=["cli"],
        timeout=120,
        required_artifact_types=["xcf_source"],
        produced_artifact_types=["texture_raster"],
    ))

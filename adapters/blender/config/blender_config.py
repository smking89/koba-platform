"""Environment configuration detected on this machine.

Detected 2026-09-27 by direct inspection — do not assume these paths
on a different machine, re-run tools/detect_environment.sh instead.
"""
import os

BLENDER_BIN = "/home/koba/Downloads/blender-5.2.2-linux-x64/blender"
BLENDER_VERSION = (5, 2, 2)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
GENERATED_DIR = os.path.join(ASSETS_DIR, "generated")
EXPORTS_DIR = os.path.join(ASSETS_DIR, "exports")
PREVIEWS_DIR = os.path.join(ASSETS_DIR, "previews")

# Export operators confirmed available in this Blender build:
#   bpy.ops.export_scene.fbx
#   bpy.ops.export_scene.gltf
#   bpy.ops.wm.obj_export
#   bpy.ops.wm.usd_export
SUPPORTED_EXPORT_FORMATS = ("fbx", "gltf", "glb", "obj", "usd")

# Interactive-mode default: normal asset development drives an already-open
# GUI Blender through live/blender_live_server.py + scripts/blender_client.py
# instead of headless -b invocations. Only batch/CI/export-only work should
# set this False and use the headless tests/*.py path.
INTERACTIVE_MODE = True
LIVE_BRIDGE_HOST = "127.0.0.1"
LIVE_BRIDGE_PORT = 8765

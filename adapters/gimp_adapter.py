"""GIMP adapter — batch export via GIMP's real Python-Fu batch interpreter
(GObject-introspection `Gimp.file_load`/`Gimp.file_save`, not the legacy
Script-Fu `gimp-file-load`/`file-jpeg-save` PDB names, which no longer
exist in GIMP 3.x — confirmed directly against this machine's real GIMP
3.2.6, not assumed from older documentation).

Three things about GIMP 3's batch CLI were confirmed by direct testing,
not assumed, and are load-bearing for this adapter:
  - `--batch-interpreter` must be given explicitly (`plug-in-script-fu-eval`
    or `python-fu-eval`) — GIMP 3 has no default, unlike 2.x.
  - The Script-Fu PDB no longer has `file-jpeg-save`/`gimp-pdb-query`;
    export must go through Python-Fu's `Gimp.file_save()`.
  - After a batch command finishes, GIMP 3 stays running as a background
    process ("GIMP is now running as a background process") instead of
    exiting — a plain top-level `--quit` flag (not a `-b` batch command)
    is what actually makes it exit cleanly with a real return code.

Like KritaAdapter, this is the adapter for what GIMP does that
Inkscape/ImageMagick don't: open GIMP's own layered format (`.xcf`) — not
a general image adapter, use ImageMagickAdapter for plain conversions.
"""
import os
import subprocess

from core.detection import detect_tool

_BATCH_SCRIPT = """
import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio
image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path({src!r}))
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path({dst!r}))
"""


class GimpAdapterError(Exception):
    pass


class GimpAdapter:
    name = "gimp"

    def __init__(self):
        self._status = None

    def detect(self):
        self._status = detect_tool("gimp")
        return self._status.found

    def version(self):
        if self._status is None:
            self.detect()
        return self._status.version if self._status.found else None

    def _executable(self):
        if self._status is None:
            self.detect()
        if not self._status.found:
            raise GimpAdapterError(f"GIMP not found: {self._status.error}")
        return self._status.executable

    def export_to(self, src_path, dst_path, timeout=90):
        """Opens src_path (e.g. a .xcf, flattening on load) and exports it
        to dst_path — format inferred from dst_path's extension via
        Gimp.file_save's own file-type detection, same convention as the
        other adapters."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)

        script = _BATCH_SCRIPT.format(src=os.path.abspath(src_path), dst=os.path.abspath(dst_path))
        cmd = [self._executable(), "-i", "--batch-interpreter=python-fu-eval", "-b", script, "--quit"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise GimpAdapterError(
                f"gimp exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )
        if not os.path.isfile(dst_path):
            raise GimpAdapterError(f"gimp reported success but {dst_path} wasn't created")
        return dst_path

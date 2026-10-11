"""Krita adapter — batch export of Krita's native `.kra` painted-texture
files (and any other format Krita can open) to a game-ready raster
format, via Krita's real `--export`/`--export-filename` batch CLI flags.
Verified against this machine's real Krita 5.2.9: a PNG was actually
opened and re-exported as JPEG headlessly before this adapter was
written, confirming the flags work as documented, not just that they
exist in `--help`.

This is the adapter for the one thing Krita does that Inkscape/
ImageMagick don't: read `.kra` (Krita's own layered format). It is not a
general image adapter — for plain format conversion/resize on formats
ImageMagick already reads, use ImageMagickAdapter instead (same guidance
ImageMagickAdapter's own docstring gives for GIMP).
"""
import os
import subprocess

from core.detection import detect_tool


class KritaAdapterError(Exception):
    pass


class KritaAdapter:
    name = "krita"

    def __init__(self):
        self._status = None

    def detect(self):
        self._status = detect_tool("krita")
        return self._status.found

    def version(self):
        if self._status is None:
            self.detect()
        return self._status.version if self._status.found else None

    def _executable(self):
        if self._status is None:
            self.detect()
        if not self._status.found:
            raise KritaAdapterError(f"Krita not found: {self._status.error}")
        return self._status.executable

    def export_to(self, src_path, dst_path, timeout=120):
        """Opens src_path (e.g. a .kra painted texture) and exports it to
        dst_path — format inferred from dst_path's extension, same
        convention as the other adapters. Batch/headless: Krita exits on
        its own once the export completes, no GUI interaction needed."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)

        cmd = [self._executable(), src_path, "--export", "--export-filename", dst_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise KritaAdapterError(
                f"krita exited {result.returncode}\ncmd: {' '.join(cmd)}\nstderr: {result.stderr}"
            )
        if not os.path.isfile(dst_path):
            raise KritaAdapterError(f"krita reported success but {dst_path} wasn't created")
        return dst_path

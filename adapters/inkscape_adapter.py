"""Inkscape adapter — vector artwork (logos, signs, decals, icons) via
Inkscape's real CLI. Flags verified directly against this machine's
Inkscape 1.4 (`inkscape --help`), not assumed from older Inkscape docs —
1.x's CLI (`--export-type`, `--export-filename`) differs from 0.92's
(`--export-png`, `-e`).

Follows the ToolAdapter shape from ROADMAP.md: detect/version/execute-style
methods, real subprocess calls only, no invented capabilities.
"""
import os
import subprocess

from core.detection import detect_tool


class InkscapeAdapterError(Exception):
    pass


class InkscapeAdapter:
    name = "inkscape"

    def __init__(self):
        self._status = None

    def detect(self):
        self._status = detect_tool("inkscape")
        return self._status.found

    def version(self):
        if self._status is None:
            self.detect()
        return self._status.version if self._status.found else None

    def _executable(self):
        if self._status is None:
            self.detect()
        if not self._status.found:
            raise InkscapeAdapterError(f"Inkscape not found: {self._status.error}")
        return self._status.executable

    def _run(self, args, timeout=60):
        cmd = [self._executable(), *args]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise InkscapeAdapterError(
                f"inkscape exited {result.returncode}\ncmd: {' '.join(cmd)}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def export_png(self, svg_path, png_path, width=None, height=None, dpi=None, area="page"):
        """Render an SVG to PNG. area='page' uses the SVG's own page/canvas
        size (matches --export-area-page); area='drawing' tightly crops to
        the actual artwork bounds (--export-area-drawing) — useful for
        icons/decals where the SVG canvas has extra margin."""
        if not os.path.isfile(svg_path):
            raise FileNotFoundError(svg_path)
        os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)

        args = [svg_path, "--export-type=png", f"--export-filename={png_path}"]
        args.append("--export-area-page" if area == "page" else "--export-area-drawing")
        if width is not None:
            args.append(f"--export-width={width}")
        if height is not None:
            args.append(f"--export-height={height}")
        if dpi is not None:
            args.append(f"--export-dpi={dpi}")

        self._run(args)
        if not os.path.isfile(png_path):
            raise InkscapeAdapterError(f"inkscape reported success but {png_path} wasn't created")
        return png_path

    def export_pdf(self, svg_path, pdf_path):
        if not os.path.isfile(svg_path):
            raise FileNotFoundError(svg_path)
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        self._run([svg_path, "--export-type=pdf", f"--export-filename={pdf_path}"])
        if not os.path.isfile(pdf_path):
            raise InkscapeAdapterError(f"inkscape reported success but {pdf_path} wasn't created")
        return pdf_path

    def export_variants(self, svg_path, output_dir, basename, widths=(128, 256, 512, 1024)):
        """Generate multiple PNG sizes from one SVG — e.g. an icon at
        several resolutions. Returns {width: path}."""
        results = {}
        for w in widths:
            out_path = os.path.join(output_dir, f"{basename}_{w}.png")
            results[w] = self.export_png(svg_path, out_path, width=w)
        return results

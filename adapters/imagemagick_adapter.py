"""ImageMagick adapter — high-speed batch raster processing (resize,
format conversion, thumbnails, mip/LOD texture chains). Verified against
this machine's real ImageMagick 7.1.1 `magick` CLI (`magick -version`,
`magick -list format`) — PNG/JPEG/SVG/WEBP all confirmed supported.

Prefer this over GIMP for batch operations per the project brief's own
guidance ("use ImageMagick or other appropriate tools when they are more
reliable for batch processing") — relevant now since GIMP isn't even
installed on this machine (see ROADMAP.md).
"""
import os
import subprocess
import tempfile

from core.detection import detect_tool


class ImageMagickAdapterError(Exception):
    pass


class ImageMagickAdapter:
    name = "imagemagick"

    def __init__(self):
        self._status = None

    def detect(self):
        self._status = detect_tool("imagemagick")
        return self._status.found

    def version(self):
        if self._status is None:
            self.detect()
        return self._status.version if self._status.found else None

    def _executable(self):
        if self._status is None:
            self.detect()
        if not self._status.found:
            raise ImageMagickAdapterError(f"ImageMagick not found: {self._status.error}")
        return self._status.executable  # resolves to `magick` per config/tools.yaml candidates

    def _run(self, args, timeout=60):
        cmd = [self._executable(), *args]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise ImageMagickAdapterError(
                f"magick exited {result.returncode}\ncmd: {' '.join(cmd)}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def resize(self, src_path, dst_path, width, height=None, keep_aspect=True):
        """Resize src to dst. If height is None, width alone sets a uniform
        scale (aspect preserved). If both given and keep_aspect=False, the
        image is stretched to exactly width x height (magick's '!' geometry
        suffix)."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)

        if height is None:
            geometry = str(width)
        else:
            geometry = f"{width}x{height}" + ("" if keep_aspect else "!")

        self._run([src_path, "-resize", geometry, dst_path])
        if not os.path.isfile(dst_path):
            raise ImageMagickAdapterError(f"magick reported success but {dst_path} wasn't created")
        return dst_path

    def convert_format(self, src_path, dst_path):
        """Format is inferred from dst_path's extension — magick's normal
        convention (e.g. .png -> .webp)."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
        self._run([src_path, dst_path])
        if not os.path.isfile(dst_path):
            raise ImageMagickAdapterError(f"magick reported success but {dst_path} wasn't created")
        return dst_path

    def generate_thumbnail(self, src_path, dst_path, size=256):
        """A square-bounded thumbnail (fits within size x size, aspect
        preserved) — the common "grid preview" case."""
        return self.resize(src_path, dst_path, width=size, height=size, keep_aspect=True)

    def inspect(self, src_path):
        """Real image metadata via `identify` — width/height/format,
        confirmed against an actual generated PNG before this method was
        written (`identify -format "%w %h %m"` -> "256 128 PNG")."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        output = self._run(["identify", "-format", "%w %h %m", src_path]).stdout.strip()
        width, height, fmt = output.split()
        return {"width": int(width), "height": int(height), "format": fmt}

    def check_seamless_tiling(self, src_path):
        """Real pixel comparison, not a heuristic: crops the 1px-wide
        left/right edge columns and 1px-tall top/bottom edge rows, then
        uses `compare -metric AE` (absolute error — count of differing
        pixels) to check whether opposite edges match exactly, which is
        what makes a texture tile seamlessly. Confirmed against a real
        deliberately-non-seamless image (left=red, right=blue -> AE=64
        for a 64px edge) and a real seamless one (AE=0) before this
        method was written. Returns {"horizontal": bool, "vertical": bool}
        — horizontal is left-vs-right edge match, vertical is top-vs-bottom."""
        info = self.inspect(src_path)
        width, height = info["width"], info["height"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            left = os.path.join(tmp_dir, "left.png")
            right = os.path.join(tmp_dir, "right.png")
            top = os.path.join(tmp_dir, "top.png")
            bottom = os.path.join(tmp_dir, "bottom.png")

            exe = self._executable()
            subprocess.run([exe, src_path, "-crop", f"1x{height}+0+0", "+repage", left],
                            capture_output=True, text=True, timeout=30, check=True)
            subprocess.run([exe, src_path, "-crop", f"1x{height}+{width - 1}+0", "+repage", right],
                            capture_output=True, text=True, timeout=30, check=True)
            subprocess.run([exe, src_path, "-crop", f"{width}x1+0+0", "+repage", top],
                            capture_output=True, text=True, timeout=30, check=True)
            subprocess.run([exe, src_path, "-crop", f"{width}x1+0+{height - 1}", "+repage", bottom],
                            capture_output=True, text=True, timeout=30, check=True)

            def _edges_match(a, b):
                result = subprocess.run(
                    [exe, "compare", "-metric", "AE", a, b, "null:"],
                    capture_output=True, text=True, timeout=30,
                )
                try:
                    return float(result.stdout.strip() or result.stderr.strip()) == 0.0
                except ValueError:
                    return False

            return {
                "horizontal": _edges_match(left, right),
                "vertical": _edges_match(top, bottom),
            }

    def create_mip_chain(self, src_path, dest_dir, sizes=(2048, 1024, 512, 256, 128), basename=None):
        """Generate a texture LOD/mip chain — one resized copy per size in
        `sizes`, matching config/export_profiles.py's texture_resolution
        budgets. Returns {size: path}. Does not upscale — a size larger
        than the source image's own width is skipped, not faked."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        basename = basename or os.path.splitext(os.path.basename(src_path))[0]
        ext = os.path.splitext(src_path)[1]

        source_width = self.inspect(src_path)["width"]

        results = {}
        for size in sorted(sizes, reverse=True):
            if size > source_width:
                continue
            out_path = os.path.join(dest_dir, f"{basename}_{size}{ext}")
            results[size] = self.resize(src_path, out_path, width=size)
        return results

"""Texture Validator (master spec's `validation/texture_validator`) —
real texture-file validation via ImageMagickAdapter's `identify`-backed
`inspect()`: actual width/height/format read off the file, not guessed.
Plain Python, no bpy dependency (textures aren't Blender scenes), unlike
`adapters/blender/core/validation.py`'s geometry validator.

Checks resolution floor, power-of-two dimensions (the common game-texture
convention — mipmapping/GPU compression tools generally expect it), and
format — each independently, same PASS/WARNING/FAIL report shape as
`adapters/blender/core/validation.py`'s `ValidationResult` for
consistency, even though this one has no bpy dependency to share code
with that module directly.
"""
from adapters.imagemagick_adapter import ImageMagickAdapter, ImageMagickAdapterError


class TextureValidationResult:
    def __init__(self, path):
        self.path = path
        self.checks = []  # list of (label, status, detail), status in PASS/WARNING/FAIL

    def add(self, label, status, detail=""):
        self.checks.append((label, status, detail))

    @property
    def passed(self):
        return all(s != "FAIL" for _, s, _ in self.checks)

    @property
    def result(self):
        return "FAIL" if not self.passed else "PASS"

    def report(self):
        lines = [f"TEXTURE VALIDATION: {self.path}", ""]
        for label, status, detail in self.checks:
            line = f"[{status}] {label}"
            if detail:
                line += f" — {detail}"
            lines.append(line)
        lines.append(f"\nRESULT: {self.result}")
        return "\n".join(lines)


def _is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def validate_texture(path, min_width=None, min_height=None, required_format=None, require_seamless=False):
    """Real inspection via ImageMagick — raises ImageMagickAdapterError
    upward (not caught here) if the file doesn't exist or ImageMagick
    itself isn't available, same UNSUPPORTED_CAPABILITY discipline as
    everywhere else; this function only reports on what it actually
    measured, never a guess.

    require_seamless=True additionally checks real opposite-edge pixel
    matching (ImageMagickAdapter.check_seamless_tiling) — a hard FAIL if
    either axis doesn't tile cleanly, for product types (e.g. building
    skins) where seamless tiling is the whole point of the asset. Left
    False by default (e.g. a CUI panel has no reason to tile)."""
    adapter = ImageMagickAdapter()
    if not adapter.detect():
        raise ImageMagickAdapterError("ImageMagick not detected")

    info = adapter.inspect(path)
    result = TextureValidationResult(path)

    if min_width is not None and info["width"] < min_width:
        result.add("Resolution (width)", "FAIL", f"{info['width']}px below minimum {min_width}px")
    else:
        result.add("Resolution (width)", "PASS", f"{info['width']}px")

    if min_height is not None and info["height"] < min_height:
        result.add("Resolution (height)", "FAIL", f"{info['height']}px below minimum {min_height}px")
    else:
        result.add("Resolution (height)", "PASS", f"{info['height']}px")

    if not _is_power_of_two(info["width"]) or not _is_power_of_two(info["height"]):
        result.add("Power-of-two dimensions", "WARNING",
                    f"{info['width']}x{info['height']} is not power-of-two — may not mipmap cleanly")
    else:
        result.add("Power-of-two dimensions", "PASS")

    if required_format is not None and info["format"].upper() != required_format.upper():
        result.add("Format", "FAIL", f"got {info['format']}, required {required_format}")
    else:
        result.add("Format", "PASS", info["format"])

    if require_seamless:
        tiling = adapter.check_seamless_tiling(path)
        if tiling["horizontal"] and tiling["vertical"]:
            result.add("Seamless tiling", "PASS")
        else:
            failing_axes = [axis for axis, ok in tiling.items() if not ok]
            result.add("Seamless tiling", "FAIL", f"edges don't match on: {failing_axes}")

    return result

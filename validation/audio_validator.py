"""Audio Validator — real audio-file validation via FFmpegAdapter's
`ffprobe`-backed `inspect()`: actual codec/sample_rate/channels/duration
read off the file, not guessed. Plain Python, no bpy dependency.

NOT one of validation/validation_registry.py's 17 formal validator
types — the master spec's own validation/ section (geometry_validator,
topology_validator, ..., security_validator) doesn't list an
audio_validator, so adding "audio" there would be inventing a type the
spec doesn't name, which this project avoids on principle (confirmed via
the exact 17-id completeness check in tests/test_validation_registry.py).
This module is real and genuinely used (by the `audio` product type in
products/product_types.py, called directly from cli/main.py's
cmd_register_product — same pattern validate_texture already uses for
"texture", which IS one of the 17), it's just outside that specific
registry's scope.
"""
from adapters.ffmpeg_adapter import FFmpegAdapter, FFmpegAdapterError


class AudioValidationResult:
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
        lines = [f"AUDIO VALIDATION: {self.path}", ""]
        for label, status, detail in self.checks:
            line = f"[{status}] {label}"
            if detail:
                line += f" — {detail}"
            lines.append(line)
        lines.append(f"\nRESULT: {self.result}")
        return "\n".join(lines)


def validate_audio(path, max_duration=None, min_sample_rate=None, required_channels=None):
    """Real inspection via ffprobe — raises FFmpegAdapterError upward
    (not caught here) if the file doesn't exist or ffmpeg/ffprobe isn't
    available, same UNSUPPORTED_CAPABILITY discipline as everywhere
    else; this function only reports on what it actually measured."""
    adapter = FFmpegAdapter()
    if not adapter.detect():
        raise FFmpegAdapterError("FFmpeg not detected")

    info = adapter.inspect(path)
    result = AudioValidationResult(path)

    if info["duration"] is None:
        result.add("Duration", "FAIL", "could not be read — no duration reported by ffprobe")
    elif max_duration is not None and info["duration"] > max_duration:
        result.add("Duration", "FAIL", f"{info['duration']:.1f}s exceeds maximum {max_duration}s")
    else:
        result.add("Duration", "PASS", f"{info['duration']:.1f}s")

    if min_sample_rate is not None:
        if info["sample_rate"] is None:
            result.add("Sample rate", "FAIL", "could not be read")
        elif info["sample_rate"] < min_sample_rate:
            result.add("Sample rate", "FAIL", f"{info['sample_rate']}Hz below minimum {min_sample_rate}Hz")
        else:
            result.add("Sample rate", "PASS", f"{info['sample_rate']}Hz")
    else:
        result.add("Sample rate", "PASS", f"{info['sample_rate']}Hz" if info["sample_rate"] else "unknown")

    if required_channels is not None and info["channels"] != required_channels:
        result.add("Channels", "FAIL", f"got {info['channels']}, required {required_channels}")
    else:
        result.add("Channels", "PASS", str(info["channels"]))

    return result

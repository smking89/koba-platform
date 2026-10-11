"""Real tests for the audio validator and ImageMagickAdapter's
seamless-tiling check — actual ffmpeg-generated audio, actual
ImageMagick-generated images, no mocks."""
import os
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adapters.ffmpeg_adapter import FFmpegAdapter  # noqa: E402
from adapters.imagemagick_adapter import ImageMagickAdapter  # noqa: E402
from validation.audio_validator import validate_audio  # noqa: E402


def _make_sine(path, duration, sample_rate=44100, channels=2):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
         "-ar", str(sample_rate), "-ac", str(channels), path],
        check=True, capture_output=True,
    )


def run():
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_audio_validator_")
    try:
        ffmpeg = FFmpegAdapter()
        assert ffmpeg.detect()

        # --- inspect(): real metadata ---
        clip_path = os.path.join(tmp_dir, "clip.wav")
        _make_sine(clip_path, duration=2, sample_rate=44100, channels=2)
        info = ffmpeg.inspect(clip_path)
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert 1.9 < info["duration"] < 2.1

        # --- validate_audio: PASS case ---
        result = validate_audio(clip_path, max_duration=5, min_sample_rate=22050, required_channels=2)
        assert result.passed
        assert result.result == "PASS"

        # --- validate_audio: duration FAIL ---
        result = validate_audio(clip_path, max_duration=1)
        assert not result.passed
        assert any(label == "Duration" and status == "FAIL" for label, status, _ in result.checks)

        # --- validate_audio: sample rate FAIL ---
        low_rate_path = os.path.join(tmp_dir, "low_rate.wav")
        _make_sine(low_rate_path, duration=1, sample_rate=8000, channels=1)
        result = validate_audio(low_rate_path, min_sample_rate=44100)
        assert not result.passed
        assert any(label == "Sample rate" and status == "FAIL" for label, status, _ in result.checks)

        # --- validate_audio: channel count FAIL ---
        result = validate_audio(low_rate_path, required_channels=2)
        assert not result.passed
        assert any(label == "Channels" and status == "FAIL" for label, status, _ in result.checks)

        try:
            validate_audio(os.path.join(tmp_dir, "does_not_exist.wav"))
            assert False, "must raise on a missing file, not silently no-op"
        except FileNotFoundError:
            pass

        # --- ImageMagickAdapter.check_seamless_tiling: real pixel comparison ---
        magick = ImageMagickAdapter()
        assert magick.detect()

        solid_path = os.path.join(tmp_dir, "solid.png")
        subprocess.run(["magick", "-size", "64x64", "xc:gray50", solid_path], check=True, capture_output=True)
        tiling = magick.check_seamless_tiling(solid_path)
        assert tiling == {"horizontal": True, "vertical": True}

        half1 = os.path.join(tmp_dir, "half1.png")
        half2 = os.path.join(tmp_dir, "half2.png")
        nonseamless_path = os.path.join(tmp_dir, "nonseamless.png")
        subprocess.run(["magick", "-size", "64x64", "xc:red", half1], check=True, capture_output=True)
        subprocess.run(["magick", "-size", "64x64", "xc:blue", half2], check=True, capture_output=True)
        subprocess.run(["magick", half1, half2, "+append", nonseamless_path], check=True, capture_output=True)
        tiling = magick.check_seamless_tiling(nonseamless_path)
        assert tiling["horizontal"] is False, "a hard red|blue seam must be detected as non-seamless"

        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = run()
    print("test_audio_validator: PASS" if ok else "test_audio_validator: FAIL")
    sys.exit(0 if ok else 1)

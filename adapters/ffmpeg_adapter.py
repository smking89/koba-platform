"""FFmpeg adapter — video/audio transcoding, thumbnail-frame extraction,
and duration probing. Verified against this machine's real FFmpeg 7.1.5
(`ffmpeg -version`) and its bundled `ffprobe` — a real synthetic test
clip (`ffmpeg -f lavfi -i testsrc=...`) was actually transcoded, had a
frame extracted, and had its duration probed before this adapter was
written; every method here matches a command confirmed to work, not a
guess from documentation.

`ffprobe` ships in the same package as `ffmpeg` and isn't tracked as a
separate entry in config/tools.yaml/core.detection — resolved via
shutil.which() at call time, and _probe() raises FFmpegAdapterError
rather than assuming it exists just because ffmpeg does.
"""
import os
import shutil
import subprocess

from core.detection import detect_tool


class FFmpegAdapterError(Exception):
    pass


class FFmpegAdapter:
    name = "ffmpeg"

    def __init__(self):
        self._status = None

    def detect(self):
        self._status = detect_tool("ffmpeg")
        return self._status.found

    def version(self):
        if self._status is None:
            self.detect()
        return self._status.version if self._status.found else None

    def _executable(self):
        if self._status is None:
            self.detect()
        if not self._status.found:
            raise FFmpegAdapterError(f"FFmpeg not found: {self._status.error}")
        return self._status.executable

    def _probe_executable(self):
        path = shutil.which("ffprobe")
        if not path:
            raise FFmpegAdapterError("ffprobe not found on PATH — it ships with ffmpeg but wasn't located")
        return path

    def _run(self, args, timeout=120):
        cmd = [self._executable(), "-y", *args]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise FFmpegAdapterError(
                f"ffmpeg exited {result.returncode}\ncmd: {' '.join(cmd)}\nstderr: {result.stderr}"
            )
        return result

    def transcode(self, src_path, dst_path):
        """Format is inferred from dst_path's extension, same convention
        as ImageMagickAdapter.convert_format — e.g. .mp4 -> .webm."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
        self._run(["-i", src_path, dst_path])
        if not os.path.isfile(dst_path):
            raise FFmpegAdapterError(f"ffmpeg reported success but {dst_path} wasn't created")
        return dst_path

    def extract_frame(self, src_path, dst_path, timestamp="00:00:01"):
        """A single still frame at `timestamp` — e.g. a thumbnail/preview
        image for a video asset. -update 1 (ffmpeg's own recommendation)
        silences the image2-muxer's "looks like a sequence pattern"
        warning for a single-frame output path."""
        if not os.path.isfile(src_path):
            raise FileNotFoundError(src_path)
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
        self._run(["-i", src_path, "-ss", timestamp, "-frames:v", "1", "-update", "1", dst_path])
        if not os.path.isfile(dst_path):
            raise FFmpegAdapterError(f"ffmpeg reported success but {dst_path} wasn't created")
        return dst_path

    def inspect(self, path):
        """Real audio/video stream metadata via ffprobe — confirmed
        against an actual synthetic sine-wave WAV before this method was
        written (`ffprobe -show_entries stream=sample_rate,channels,
        codec_name -show_entries format=duration -of
        default=noprint_wrappers=1` -> "codec_name=pcm_s16le\\n
        sample_rate=44100\\nchannels=2\\nduration=2.000000"). Returns
        {"codec": str, "sample_rate": int|None, "channels": int|None,
        "duration": float}."""
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        cmd = [self._probe_executable(), "-v", "error", "-select_streams", "a:0",
               "-show_entries", "stream=sample_rate,channels,codec_name",
               "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise FFmpegAdapterError(f"ffprobe exited {result.returncode}\nstderr: {result.stderr}")

        info = {"codec": None, "sample_rate": None, "channels": None, "duration": None}
        for line in result.stdout.strip().splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key == "codec_name":
                info["codec"] = value
            elif key == "sample_rate":
                info["sample_rate"] = int(value)
            elif key == "channels":
                info["channels"] = int(value)
            elif key == "duration":
                info["duration"] = float(value)
        return info

    def get_duration(self, path):
        """Duration in seconds (float), via ffprobe."""
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        cmd = [self._probe_executable(), "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise FFmpegAdapterError(f"ffprobe exited {result.returncode}\nstderr: {result.stderr}")
        try:
            return float(result.stdout.strip())
        except ValueError as e:
            raise FFmpegAdapterError(f"ffprobe returned a non-numeric duration: {result.stdout!r}") from e

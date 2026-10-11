"""Real tests against actually-installed tools — not mocks. Confirms the
detector correctly finds what's really on this machine and correctly
reports what's really absent."""
import sys

from core.detection import detect_tool, detect_all, system_ready, REQUIRED_TOOLS


def run():
    # Blender: configured explicitly in config/tools.yaml — must resolve.
    blender = detect_tool("blender")
    assert blender.found, f"blender should be found (configured in tools.yaml): {blender.error}"
    assert "Blender" in (blender.version or ""), f"unexpected blender version string: {blender.version}"

    # Inkscape: on PATH, not configured — must resolve via candidates.
    inkscape = detect_tool("inkscape")
    assert inkscape.found, f"inkscape should be found on PATH: {inkscape.error}"
    assert "Inkscape" in (inkscape.version or ""), f"unexpected inkscape version string: {inkscape.version}"

    # A tool that doesn't exist must correctly report not found, not crash.
    fake = detect_tool("definitely_not_a_real_tool_xyz123")
    assert not fake.found
    assert fake.error is not None

    # GIMP is installed via Flatpak (org.gimp.GIMP) — confirmed and wired
    # via bin/gimp-flatpak-wrapper.sh + config/tools.yaml.
    gimp = detect_tool("gimp")
    assert gimp.found, f"gimp should be found via the flatpak wrapper: {gimp.error}"
    # GIMP's --version output spells out "GNU Image Manipulation Program",
    # not the literal acronym "GIMP" — confirmed by actually running it.
    assert "Image Manipulation" in (gimp.version or ""), gimp.version

    # Krita and FFmpeg: confirmed installed on this machine (re-detected
    # 2026-09-30 mid-session — see ROADMAP.md's environment table).
    krita = detect_tool("krita")
    assert krita.found, f"krita should be found on PATH: {krita.error}"

    ffmpeg = detect_tool("ffmpeg")
    assert ffmpeg.found, f"ffmpeg should be found on PATH: {ffmpeg.error}"

    # detect_all covers every required tool; system_ready is True now
    # that Krita/FFmpeg are both actually installed — if this ever flips
    # back to False it means one of them disappeared, worth noticing.
    results = detect_all()
    assert set(results.keys()) >= set(REQUIRED_TOOLS)
    ready = system_ready(results)
    assert ready is True, (
        "system_ready() returned False — either Krita/FFmpeg got uninstalled "
        "(update ROADMAP.md) or detection broke silently"
    )

    return True


if __name__ == "__main__":
    ok = run()
    print("test_detection: PASS" if ok else "test_detection: FAIL")
    sys.exit(0 if ok else 1)

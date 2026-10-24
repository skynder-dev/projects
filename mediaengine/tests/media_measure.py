"""Exact audio/video lengths by decoding (Windows has no ffprobe; the app's ffmpeg-only probe has no per-stream durations)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def ffmpeg_exe() -> str:
    import os
    if os.environ.get("MEDENG_FFMPEG"):
        return os.environ["MEDENG_FFMPEG"]
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def av_durations(path, ff: str | None = None, fps: float = 30.0) -> tuple[float, float | None]:
    """(video seconds, audio seconds or None). Video = decoded frames / fps (the reel is constant 30 fps)."""
    ff = ff or ffmpeg_exe()
    v = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", "scale=8:8", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True)
    frames = len(v.stdout) // 64
    a = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:a:0?", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                       capture_output=True)
    samples = len(a.stdout) // 2
    return frames / fps, (samples / 48000.0 if samples else None)


def loudness(path, ff: str | None = None) -> tuple[float | None, float | None]:
    """(integrated loudness in LUFS, loudest sample in dB) of the first sound track; (None, None) without sound."""
    import re
    ff = ff or ffmpeg_exe()
    t = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0?", "-af", "ebur128=framelog=quiet,volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", t)
    m = re.findall(r"max_volume:\s*(-?[\d.]+|-inf) dB", t)
    return (float(i[-1]) if i else None), (float(m[-1]) if m and m[-1] != "-inf" else (-200.0 if m else None))


if __name__ == "__main__":
    import sys
    print(av_durations(Path(sys.argv[1])))

"""Make small synthetic test folders (no personal media). Uses the ffmpeg the app itself uses.

  python tests/make_fixtures.py <out_dir>
creates <out_dir>/two (2 clips), <out_dir>/seven (7 clips + 1 broken file + 1 duplicate, one portrait clip) and
<out_dir>/static (2 clips + 1 still video).
"""
from __future__ import annotations

import os, shutil, subprocess, sys
from pathlib import Path

SOURCES = [
    "testsrc2=size=640x360:rate=30",
    "mandelbrot=size=640x360:rate=30",
    "life=size=640x360:rate=30:mold=10:ratio=0.3:death_color=#202020:life_color=#80c0ff",
    "cellauto=size=640x360:rate=30:rule=110",
    "smptehdbars=size=640x360:rate=30",
    "rgbtestsrc=size=640x360:rate=30",
    "testsrc=size=360x640:rate=30",  # portrait
]


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main(out: Path) -> None:
    ff = ffmpeg()
    seven = out / "seven"
    two = out / "two"
    for d in (seven, two):
        d.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(SOURCES, 1):
        dst = seven / f"clip_{i}.mp4"
        if dst.exists():
            continue
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", src, "-f", "lavfi", "-i", f"sine=frequency={200 + 90 * i}:sample_rate=48000",
                        "-t", "14", "-vf", f"hue=h=t*{7 * i},rotate=0.05*sin(t*{i})", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(dst)], check=True)
    (seven / "broken.mp4").write_bytes(os.urandom(50000))
    shutil.copyfile(seven / "clip_2.mp4", seven / "clip_2 copy.mp4")
    for n in (1, 3):
        shutil.copyfile(seven / f"clip_{n}.mp4", two / f"clip_{n}.mp4")
    # "static": two normal clips + a still (black) video the technical analysis cannot use
    static = out / "static"
    static.mkdir(parents=True, exist_ok=True)
    for n in (1, 3):
        shutil.copyfile(seven / f"clip_{n}.mp4", static / f"clip_{n}.mp4")
    if not (static / "still.mp4").exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:r=30", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(static / "still.mp4")], check=True)
    print("fixtures ready:", sorted(p.name for p in seven.iterdir()), sorted(p.name for p in two.iterdir()))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

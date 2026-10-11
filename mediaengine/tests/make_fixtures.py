"""Make small synthetic test folders (no personal media). Uses the ffmpeg the app itself uses.

  python tests/make_fixtures.py <out_dir>
creates <out_dir>/two (2 clips), <out_dir>/seven (7 clips + 1 broken file + 1 duplicate, one portrait clip) and
<out_dir>/static (2 clips + 1 still video) and <out_dir>/phone (rotated portrait, HEVC .MOV 60 fps, VFR, no audio,
very short clip, Cyrillic names).
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
    make_phone(ff, out / "phone")
    make_hdr(ff, out / "hdr")
    print("fixtures ready:", sorted(p.name for p in seven.iterdir()), sorted(p.name for p in two.iterdir()))


def make_phone(ff: str, phone: Path) -> None:
    """Phone/camera-style files: portrait stored with a rotation tag (like iPhone), HEVC in .MOV at 60 fps with
    44.1 kHz mono sound, variable frame rate, no audio track, a very short clip, Cyrillic file names.
    The rotated clip has a red band at the TOP and a blue band at the BOTTOM when shown upright."""
    phone.mkdir(parents=True, exist_ok=True)
    tmp = phone.parent / "_phone_tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    def run(*args):
        subprocess.run([ff, "-v", "error", "-y", *args], check=True)

    rotated = phone / "Отпуск — пляж.mp4"
    if not rotated.exists():
        stored = tmp / "stored.mp4"
        run("-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=30", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "12", "-vf", "hue=h=t*20,drawbox=x=0:y=0:w=720:h=260:color=red:t=fill,drawbox=x=0:y=1020:w=720:h=260:color=blue:t=fill,"
            "transpose=2", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(stored))
        run("-display_rotation", "-90", "-i", str(stored), "-c", "copy", str(rotated))   # shows upright, like a phone
    hevc = phone / "IMG_0042.MOV"
    if not hevc.exists():
        run("-f", "lavfi", "-i", "mandelbrot=size=1280x720:rate=60", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=44100",
            "-t", "10", "-c:v", "libx265", "-x265-params", "log-level=error", "-preset", "ultrafast", "-tag:v", "hvc1", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "1", "-ar", "44100", "-shortest", str(hevc))
    vfr = phone / "переменная частота.mp4"
    if not vfr.exists():
        run("-f", "lavfi", "-i", "life=size=640x360:rate=30:mold=10:ratio=0.3", "-f", "lavfi", "-i", "sine=frequency=520:sample_rate=48000",
            "-t", "10", "-vf", "select='lt(t,4)+not(mod(n,3))',hue=s=2", "-fps_mode", "vfr", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(vfr))
    silent = phone / "no_audio.mp4"
    if not silent.exists():
        run("-f", "lavfi", "-i", "cellauto=size=640x360:rate=30:rule=30", "-t", "9", "-vf", "hue=h=t*15",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(silent))
    short = phone / "short.mp4"
    if not short.exists():
        run("-f", "lavfi", "-i", "rgbtestsrc=size=640x360:rate=30", "-f", "lavfi", "-i", "sine=frequency=700:sample_rate=48000",
            "-t", "1.5", "-vf", "rotate=0.4*t", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(short))
    shutil.rmtree(tmp, ignore_errors=True)


PATCHES = "drawbox=x=0:y=0:w=320:h=180:color=0xC81E1E:t=fill,drawbox=x=960:y=0:w=320:h=180:color=0x808080:t=fill"


def make_hdr(ff: str, hdr: Path) -> None:
    """HDR phone-style clips made from SDR content with known patches (top-left red C81E1E, top-right grey 808080):
    hlg/hlg.mov = 10-bit HEVC HLG (iPhone / Dolby Vision 8.4 style), pq/pq.mp4 = 10-bit HEVC PQ (HDR10 style).
    A correct conversion back to normal video shows the patches close to their original colours."""
    filt = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    if " zscale " not in filt:
        print("HDR fixtures skipped: this ffmpeg has no zscale")
        return
    for kind, trc, name in (("hlg", "arib-std-b67", "hlg.mov"), ("pq", "smpte2084", "pq.mp4")):
        d = hdr / kind
        d.mkdir(parents=True, exist_ok=True)
        dst = d / name
        if dst.exists():
            continue
        npl = ":npl=203" if kind == "pq" else ""
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i",
                        "sine=frequency=400:sample_rate=48000", "-t", "8", "-vf",
                        f"{PATCHES},format=gbrpf32le,zscale=tin=bt709:t={trc}:pin=bt709:p=bt2020:min=bt709:m=bt2020nc:r=tv{npl},format=yuv420p10le",
                        "-c:v", "libx265", "-x265-params", f"log-level=error:colorprim=bt2020:transfer={trc}:colormatrix=bt2020nc",
                        "-color_primaries", "bt2020", "-color_trc", trc, "-colorspace", "bt2020nc", "-tag:v", "hvc1",
                        "-c:a", "aac", "-shortest", str(dst)], check=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

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
    make_camcorder(ff, out / "camcorder", seven)
    make_anamorphic(ff, out / "anamorphic")
    make_formats(ff, out / "formats")
    make_older(ff, out / "older")
    make_levels(ff, out / "levels")
    make_camera2(ff, out / "camera2")
    make_subject(ff, out / "subject")
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


def make_camcorder(ff: str, cam: Path, seven: Path) -> None:
    """AVCHD-style camcorder file: 1080i50 H.264 in MPEG-TS (.MTS) with AC-3 sound, plus one normal clip."""
    cam.mkdir(parents=True, exist_ok=True)
    mts = cam / "00012.MTS"
    if not mts.exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=50", "-f", "lavfi", "-i",
                        "sine=frequency=500:sample_rate=48000", "-t", "10", "-vf", "hue=h=t*15,interlace=scan=tff,setfield=tff",
                        "-c:v", "libx264", "-preset", "ultrafast", "-flags", "+ildct+ilme", "-x264-params", "tff=1", "-pix_fmt", "yuv420p",
                        "-c:a", "ac3", "-f", "mpegts", str(mts)], check=True)
    if not (cam / "clip_3.mp4").exists():
        shutil.copyfile(seven / "clip_3.mp4", cam / "clip_3.mp4")


BOX = "eq=brightness=-0.35,drawbox=x=iw/2-ih*0.185:y=ih*0.315:w=ih*0.37:h=ih*0.37:color=white:t=fill"


def make_anamorphic(ff: str, d: Path) -> None:
    """Wide pictures stored in narrow pixels, with a white SQUARE in the middle (must stay square in the reel):
    HDV/AVCHD-style 1440x1080 (pixel aspect 4:3) and DVD-style 16:9 MPEG-2 720x576 (pixel aspect 64:45)."""
    d.mkdir(parents=True, exist_ok=True)
    for name, size, store, sar, codec in (("HDV_1440.mp4", "1920x1080", "1440:1080", "4/3", ["-c:v", "libx264", "-preset", "ultrafast"]),
                                          ("DVD_169.mpg", "1024x576", "720:576", "64/45", ["-c:v", "mpeg2video", "-b:v", "6M"])):
        dst = d / name
        if dst.exists():
            continue
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=25", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=48000", "-t", "12", "-vf", f"hue=h=t*40,{BOX},scale={store},setsar={sar}",
                        *codec, "-pix_fmt", "yuv420p", "-c:a", "aac" if name.endswith(".mp4") else "mp2", "-shortest", str(dst)], check=True)


def make_formats(ff: str, d: Path) -> None:
    """Other formats people have on disk. A format this ffmpeg build cannot WRITE is skipped (and reported)."""
    d.mkdir(parents=True, exist_ok=True)
    tone = lambda f, sr=48000: ["-f", "lavfi", "-i", f"sine=frequency={f}:sample_rate={sr}"]
    specs = {
        "surround_51.mp4": ["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=25,hue=h=t*40", *tone(440), "-filter_complex",
                            "[1:a]pan=5.1|FL=c0|FR=c0|FC=c0|LFE=c0|BL=c0|BR=c0[a]", "-map", "0:v", "-map", "[a]",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac"],
        "slowmo_120.MOV": ["-f", "lavfi", "-i", "testsrc=size=1280x720:rate=120,hue=h=t*90", *tone(600), "-c:v", "libx265",
                           "-x265-params", "log-level=error", "-preset", "ultrafast", "-tag:v", "hvc1", "-pix_fmt", "yuv420p", "-c:a", "aac"],
        "square.mp4": ["-f", "lavfi", "-i", "mandelbrot=size=1080x1080:rate=30", *tone(500), "-c:v", "libx264", "-preset", "ultrafast",
                       "-pix_fmt", "yuv420p", "-c:a", "aac"],
        "odd_size_444.mkv": ["-f", "lavfi", "-i", "testsrc2=size=853x479:rate=30000/1001,hue=s=t", *tone(700), "-c:v", "libx264",
                             "-preset", "ultrafast", "-pix_fmt", "yuv444p", "-c:a", "aac"],
        "OLDCAM01.AVI": ["-f", "lavfi", "-i", "life=size=640x480:rate=15:mold=10:ratio=0.2", *tone(350, 22050), "-c:v", "mjpeg",
                         "-q:v", "4", "-pix_fmt", "yuvj420p", "-c:a", "pcm_s16le", "-ac", "1"],
        "screen.webm": ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30,hue=h=t*60", *tone(800), "-c:v", "libvpx-vp9",
                        "-deadline", "realtime", "-cpu-used", "8", "-b:v", "1M", "-c:a", "libopus"],
        "ten_bit.mov": ["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=50,hue=h=t*30", *tone(900), "-c:v", "libx264",
                        "-preset", "ultrafast", "-pix_fmt", "yuv420p10le", "-c:a", "aac"],
        "two_tracks.mp4": ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30,hue=h=-t*50", *tone(300), *tone(1200), "-map", "0:v",
                           "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac"],
        "late_sound.mp4": ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30,hue=h=t*20", *tone(1000), "-filter_complex",
                           "[1:a]adelay=2000|2000,atrim=0:10[a]", "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast",
                           "-pix_fmt", "yuv420p", "-c:a", "aac"],
        "prores.mov": ["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=24000/1001,hue=h=t*70", *tone(650), "-c:v", "prores_ks",
                       "-profile:v", "0", "-c:a", "pcm_s24le"],
        "oldphone.3gp": ["-f", "lavfi", "-i", "testsrc2=size=176x144:rate=15,hue=h=t*80", *tone(450, 8000), "-c:v", "mpeg4",
                         "-c:a", "aac", "-ar", "8000", "-ac", "1"],
    }
    for name, args in specs.items():
        dst = d / name
        if dst.exists():
            continue
        cp = subprocess.run([ff, "-v", "error", "-y", *args, "-t", "8", str(dst)], capture_output=True, text=True)
        if cp.returncode != 0:
            dst.unlink(missing_ok=True)
            print(f"format fixture skipped (this ffmpeg cannot write it): {name}: {cp.stderr.strip()[-200:]}")


def make_older(ff: str, d: Path) -> None:
    """Older formats: Windows Media, Flash video, DVD .VOB, JVC camcorder .MOD (PS, wide in narrow pixels) and .TOD
    (TS, HDV-like), HDV tape .m2t, DV tape .dv. A format this ffmpeg build cannot WRITE is skipped (and reported)."""
    d.mkdir(parents=True, exist_ok=True)
    src = lambda size, rate, h, f, sr=48000: ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate},hue=h=t*{h}",
                                              "-f", "lavfi", "-i", f"sine=frequency={f}:sample_rate={sr}"]
    specs = {
        "old_clip.wmv": [*src("640x480", 30, 40, 440, 44100), "-c:v", "wmv2", "-b:v", "2M", "-c:a", "wmav2"],
        "web.flv": [*src("640x360", 30, 90, 340, 44100), "-c:v", "flv1", "-c:a", "aac", "-f", "flv"],
        "VTS_01_1.VOB": [*src("720x576", 25, -40, 540), "-c:v", "mpeg2video", "-b:v", "5M", "-c:a", "ac3", "-f", "vob"],
        "MOV001.MOD": [*src("720x576", 25, 60, 640), "-vf", "setsar=64/45", "-c:v", "mpeg2video", "-b:v", "6M", "-c:a", "ac3", "-f", "vob"],
        "MOV002.TOD": [*src("1440x1080", 25, 20, 740), "-vf", "setsar=4/3", "-c:v", "mpeg2video", "-b:v", "15M", "-c:a", "mp2", "-f", "mpegts"],
        "hdv_tape.m2t": [*src("1440x1080", 25, -20, 840), "-vf", "setsar=4/3", "-c:v", "mpeg2video", "-b:v", "15M", "-c:a", "mp2", "-f", "mpegts"],
        "tape.dv": [*src("720x576", 25, 70, 940), "-c:v", "dvvideo", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ac", "2", "-f", "dv"],
    }
    for name, args in specs.items():
        dst = d / name
        if dst.exists():
            continue
        cp = subprocess.run([ff, "-v", "error", "-y", *args, "-t", "8", str(dst)], capture_output=True, text=True)
        if cp.returncode != 0:
            dst.unlink(missing_ok=True)
            print(f"older-format fixture skipped (this ffmpeg cannot write it): {name}: {cp.stderr.strip()[-200:]}")


def make_levels(ff: str, d: Path) -> None:
    """A very quiet clip and a loud clip (like a phone next to a camera): the reel should even them out."""
    d.mkdir(parents=True, exist_ok=True)
    for name, vol, h in (("quiet_phone.mp4", 0.08, 50), ("loud_camera.mp4", 1.0, -50)):
        dst = d / name
        if dst.exists():
            continue
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30,hue=h=t*{h}", "-f", "lavfi", "-i",
                        "anoisesrc=color=pink:sample_rate=48000:amplitude=0.5", "-t", "12", "-af", f"volume={vol}",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", str(dst)], check=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))


def make_camera2(ff: str, d: Path) -> None:
    """More phone/camera cases: a phone held upside down (stored turned 180 degrees with a rotation tag), portrait
    turned the other way (tag +90), an action-camera file with a timecode track at 29.97 fps, a 25 fps (PAL) clip and
    a .MOV with a subtitle track. Every clip, shown upright, has a red band at the TOP and a blue band at the BOTTOM."""
    d.mkdir(parents=True, exist_ok=True)
    tmp = d.parent / "_camera2_tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    def run(*args):
        subprocess.run([ff, "-v", "error", "-y", *args], check=True)

    def bands(w, h):
        b = max(40, h // 5)
        return f"drawbox=x=0:y=0:w={w}:h={b}:color=red:t=fill,drawbox=x=0:y={h - b}:w={w}:h={b}:color=blue:t=fill"

    upside = d / "upside_down.mp4"
    if not upside.exists():
        stored = tmp / "upside_stored.mp4"
        run("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=380:sample_rate=48000",
            "-t", "10", "-vf", "hue=h=t*25," + bands(1280, 720) + ",hflip,vflip", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(stored))
        run("-display_rotation", "180", "-i", str(stored), "-c", "copy", str(upside))
    port = d / "portrait_cw.mp4"
    if not port.exists():
        stored = tmp / "portrait_stored.mp4"
        run("-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=30", "-f", "lavfi", "-i", "sine=frequency=610:sample_rate=48000",
            "-t", "10", "-vf", "hue=h=t*30," + bands(720, 1280) + ",transpose=1", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(stored))
        run("-display_rotation", "90", "-i", str(stored), "-c", "copy", str(port))
    gopro = d / "GX010007.MP4"
    if not gopro.exists():
        run("-f", "lavfi", "-i", "mandelbrot=size=1920x1080:rate=30000/1001", "-f", "lavfi", "-i", "sine=frequency=480:sample_rate=48000",
            "-t", "9", "-vf", "hue=h=t*15," + bands(1920, 1080), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-timecode", "10:20:30;00", "-shortest", str(gopro))
    pal = d / "PAL_25fps.mp4"
    if not pal.exists():
        run("-f", "lavfi", "-i", "life=size=1280x720:rate=25:mold=10:ratio=0.3", "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000",
            "-t", "9", "-vf", "hue=h=t*20:s=2," + bands(1280, 720), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(pal))
    subs = d / "with_subtitles.mov"
    if not subs.exists():
        srt = tmp / "s.srt"
        srt.write_text("1\n00:00:00,500 --> 00:00:04,000\nhello\n\n2\n00:00:05,000 --> 00:00:08,000\nworld\n", encoding="utf-8")
        run("-f", "lavfi", "-i", "cellauto=size=1280x720:rate=30:rule=110", "-f", "lavfi", "-i", "sine=frequency=560:sample_rate=48000",
            "-i", str(srt), "-t", "9", "-map", "0:v", "-map", "1:a", "-map", "2:s", "-vf", "hue=h=t*10," + bands(1280, 720),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "mov_text",
            "-metadata", "creation_time=2026-07-14T10:20:30Z", "-shortest", str(subs))
    shutil.rmtree(tmp, ignore_errors=True)


def make_subject(ff: str, d: Path) -> None:
    """A landscape clip whose only detailed, moving thing (a textured square) stays in the RIGHT fifth of a dark,
    flat picture: a vertical reel must follow it instead of cutting the middle of the frame."""
    d.mkdir(parents=True, exist_ok=True)
    f = d / "subject_right.mp4"
    if not f.exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202020:s=1920x1080:r=30",
                        "-f", "lavfi", "-i", "testsrc2=size=300x300:rate=30", "-f", "lavfi", "-i", "sine=frequency=420:sample_rate=48000",
                        "-t", "10", "-filter_complex", "[0:v][1:v]overlay=x=1500+40*sin(t*2):y=390+120*sin(t*1.3),format=yuv420p[v]",
                        "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(f)], check=True)

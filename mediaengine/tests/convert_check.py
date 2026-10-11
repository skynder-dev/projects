"""Full-video Convert (existing Archivist feature, contract §9): whole video, original order and frame rate, H.264.

  python tests/convert_check.py <fixtures_dir> <work_dir>

Converts with the app's own converter.convert_file: a 1440p 60 fps clip -> High Quality 1080p, the rotated phone clip and
the VFR clip from <fixtures_dir>/phone. Checks: output size cap, frame rate kept, duration and frame count match the source
(no cut, no drop), full decode clean, upright portrait stays upright, audio kept, source bytes unchanged, no .part left.
"""
from __future__ import annotations

import hashlib, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import av_durations, ffmpeg_exe  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def frames(ff, path):
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", "scale=8:8", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return len(raw) // 64


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.converter import convert_file
    from archivist.auto_edit import _probe
    ff = ffmpeg_exe()
    src_dir = work / "src"
    src_dir.mkdir(exist_ok=True)
    big = src_dir / "walkthrough_1440p60.mp4"
    if not big.exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=2560x1440:rate=60", "-f", "lavfi", "-i",
                        "sine=frequency=330:sample_rate=48000", "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(big)], check=True)
    cases = [(big, "hq_1080p", (1920, 1080), 60.0), (fx / "phone" / "Отпуск — пляж.mp4", "hq_1080p", (720, 1280), 30.0),
             (fx / "phone" / "переменная частота.mp4", "share_1080p", (640, 360), None)]
    checks = []

    def check(name, ok, detail=None):
        checks.append(ok)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    out_dir = work / "Converted"
    for src, preset, dims, fps in cases:
        before = sha(src)
        res = convert_file(src, preset, output_dir=out_dir)
        out = Path(res["output"])
        info = _probe(out)
        v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"][0]
        a = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        tag = src.stem[:20]
        check(f"convert_{tag}_h264_size", v.get("codec_name") == "h264" and (int(v["width"]), int(v["height"])) == dims, (v.get("codec_name"), v.get("width"), v.get("height")))
        if fps:
            num, den = (v.get("r_frame_rate") or "0/1").split("/")
            check(f"convert_{tag}_fps_kept", abs(float(num) / float(den) - fps) < 0.01, v.get("r_frame_rate"))
        fs, fo = frames(ff, src), frames(ff, out)
        check(f"convert_{tag}_no_frames_lost", fo >= fs - 1, (fs, fo))
        vd_s, ad_s = av_durations(src, ff, fps or 30.0)
        vd_o, ad_o = av_durations(out, ff, fps or 30.0)
        check(f"convert_{tag}_full_length", abs(float(info["format"]["duration"]) - float(_probe(src)["format"]["duration"])) <= 0.15
              and bool(a) == bool(ad_s), (info["format"]["duration"], _probe(src)["format"]["duration"]))
        dec = subprocess.run([ff, "-v", "error", "-i", str(out), "-f", "null", "-"], capture_output=True, text=True)
        check(f"convert_{tag}_decodes_clean", dec.returncode == 0 and not dec.stderr.strip(), dec.stderr[-300:])
        check(f"convert_{tag}_source_unchanged", sha(src) == before)
        if dims == (720, 1280):   # portrait phone clip: never upscaled, stays upright
            raw = subprocess.run([ff, "-v", "error", "-ss", "2", "-i", str(out), "-frames:v", "1", "-vf", "scale=90:160", "-f", "rawvideo",
                                  "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            top, bot = raw[: 90 * 10 * 3], raw[-90 * 10 * 3:]
            red_top = sum(top[0::3]) > sum(top[2::3]) + 60 * 900 and sum(bot[2::3]) > sum(bot[0::3]) + 60 * 900
            check(f"convert_{tag}_upright", red_top)
    hlg = fx / "hdr" / "hlg" / "hlg.mov"
    if hlg.is_file():
        res = convert_file(hlg, "share_1080p", output_dir=out_dir)
        raw = subprocess.run([ff, "-v", "error", "-ss", "2", "-i", res["output"], "-frames:v", "1", "-vf", "scale=128:72", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        px = lambda x, y: tuple(raw[(y * 128 + x) * 3:(y * 128 + x) * 3 + 3]) if len(raw) == 128 * 72 * 3 else None
        red, grey = px(12, 8), px(115, 8)
        check("convert_hdr_hlg_normal_colours", red and grey and red[0] >= 160 and red[1] <= 70 and 100 <= grey[1] <= 160, (red, grey))
    check("convert_no_part_files", not list(out_dir.glob("*.part*")))
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

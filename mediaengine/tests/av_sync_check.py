"""Audio/video sync at every cut of a reel built by the engine.

  python tests/av_sync_check.py <work_dir> [--target 30] [--keep]

Makes 4 synthetic sources in which a white flash frame and a 1 kHz beep happen at the same instant every second,
builds a reel with the app's engine (technical mode), then measures in the reel: for every flash, the time from the
flash to the nearest beep onset (negative = sound early). Pass = at every cut the sound is at most 25 ms early and
40 ms late (well inside the ITU-R BT.1359 detectability window of 45 ms early / 125 ms late), and the reel's sound is
as long as its picture (±50 ms).
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402

SOURCES = ["testsrc2=size=640x360:rate=30", "mandelbrot=size=640x360:rate=30",
           "life=size=640x360:rate=30:mold=10:ratio=0.3", "cellauto=size=640x360:rate=30:rule=110"]


def make_sources(ff, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(SOURCES, 1):
        dst = folder / f"sync_{i}.mp4"
        if dst.exists():
            continue
        off = 0.1 * i   # flashes at k + off seconds
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", src,
                        "-f", "lavfi", "-i", f"aevalsrc='0.3*sin(2*PI*(200+60*{i})*t)+if(lt(mod(t-{off},1),0.04),0.9*sin(2*PI*1000*t),0)':s=48000",
                        "-t", "14", "-vf", f"hue=h=t*{9*i},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t-{off},1),0.0333)'",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)],
                       check=True)


def flashes(ff, path, fps=30.0):
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", "scale=8:8", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True).stdout
    out, prev = [], False
    for n in range(len(raw) // 64):
        lit = sum(raw[n * 64:(n + 1) * 64]) / 64 > 225
        if lit and not prev:          # first frame of each flash
            out.append(n / fps)
        prev = lit
    return out


def beeps(ff, path, rate=48000):
    """Onsets of 1 kHz bursts (band energy in 5 ms windows)."""
    import math
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                          "-af", "highpass=f=800,lowpass=f=1300", "-f", "s16le", "-"], capture_output=True).stdout
    import array
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    win = rate // 200
    energy = [math.sqrt(sum(x * x for x in a[i:i + win]) / win) for i in range(0, len(a) - win, win)]
    if not energy:
        return []
    thr = max(energy) * 0.35
    on, last = [], -1.0
    for k, e in enumerate(energy):
        t = k * win / rate
        if e > thr and (not on or t - last > 0.3):
            on.append(t)
        if e > thr:
            last = t
    return on


def main():
    work = Path(sys.argv[1]).resolve()
    target = sys.argv[sys.argv.index("--target") + 1] if "--target" in sys.argv else "30"
    ff = ffmpeg_exe()
    src = work / "sync_sources"
    make_sources(ff, src)
    out = work / "sync_out"
    shutil.rmtree(out, ignore_errors=True)
    env = dict(os.environ, MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "no-model"))
    cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(src), "--output-dir", str(out),
                         "--work-dir", str(work / "sync_work"), "--runtime-dir", str(R3), "--target-seconds", target,
                         "--semantic", "off", "--audio", "source", "--profile", "16x9"], capture_output=True, text=True, env=env)
    if cp.returncode != 0:
        print(cp.stdout[-1500:], cp.stderr[-2500:])
        return 1
    reel = out / "MediaEngine Reel.mp4"
    res = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8"))
    fl, bp = flashes(ff, reel), beeps(ff, reel)
    rows = []
    for t in fl:
        near = min(bp, key=lambda b: abs(b - t)) if bp else None
        seg = next((s["position"] for s in res["segments"] if s["reel_in_s"] <= t < s["reel_out_s"]), None)
        rows.append({"flash_s": round(t, 3), "beep_offset_ms": None if near is None else round((near - t) * 1000, 1), "segment": seg})
    offs = [r["beep_offset_ms"] for r in rows if r["beep_offset_ms"] is not None and abs(r["beep_offset_ms"]) < 400]
    worst = max((abs(x) for x in offs), default=None)
    from media_measure import av_durations
    vd, ad = av_durations(reel, ff)
    by_seg = {}
    for r in rows:
        if r["beep_offset_ms"] is not None and abs(r["beep_offset_ms"]) < 400:
            by_seg.setdefault(r["segment"], []).append(r["beep_offset_ms"])
    report = {"reel_s": res["actual_duration_s"], "segments": len(res["segments"]), "flashes": len(fl), "beeps": len(bp),
              "matched": len(offs), "picture_s": round(vd, 3), "sound_s": round(ad or 0, 3), "worst_abs_ms": worst, "sound_early_max_ms": -min(offs, default=0), "sound_late_max_ms": max(offs, default=0), "per_segment_ms": {str(k): v for k, v in sorted(by_seg.items(), key=lambda x: str(x[0]))}}
    print(json.dumps(report, indent=1))
    early = min(offs, default=None)
    late = max(offs, default=None)
    report_ok = offs and early >= -25 and late <= 40 and ad is not None and abs(vd - ad) <= 0.05
    ok = bool(report_ok) and len(by_seg) >= max(2, len(res["segments"]) - 1)
    print("PASS av_sync_every_cut" if ok else "FAIL av_sync_every_cut")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Large phone-like footage: 4K H.264, 4K HEVC .MOV and a long 1080p video, through the engine (technical mode).

  python tests/heavy_media_check.py <work_dir> [--small]

Measures the whole build time and checks: reel made, nothing skipped for time-outs, Social HD output, and the
reel is cut from the original (full quality). --small makes short, low-resolution stand-ins (script self-test).
"""
from __future__ import annotations

import json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402


def main():
    work = Path(sys.argv[1]).resolve()
    small = "--small" in sys.argv
    ff = ffmpeg_exe()
    src = work / "heavy"
    src.mkdir(parents=True, exist_ok=True)
    specs = [("4K_walk.mp4", "testsrc2", "3840x2160", 60, "libx264"), ("4K_boat.MOV", "mandelbrot", "3840x2160", 45, "libx265"),
             ("long_1080p.mp4", "life=mold=10:ratio=0.3", "1920x1080", 300, "libx264")]
    if small:
        specs = [(n, s, "640x360", max(8, d // 10), c) for n, s, _, d, c in specs]
    t_make = time.time()
    for name, lav, size, dur, codec in specs:
        dst = src / name
        if dst.exists():
            continue
        kind, _, opts = lav.partition("=")
        extra = ["-x265-params", "log-level=error", "-tag:v", "hvc1"] if codec == "libx265" else []
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"{kind}=size={size}:rate=30" + (":" + opts if opts else ""),
                        "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000", "-t", str(dur), "-vf", "hue=h=t*9",
                        "-c:v", codec, "-preset", "ultrafast", *extra, "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(dst)], check=True)
    print(f"made test footage in {time.time() - t_make:.0f} s:", [f"{p.name} {p.stat().st_size // 1_000_000} MB" for p in sorted(src.iterdir())], flush=True)
    out = work / "out"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    env = dict(os.environ, MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "no-model"))
    t0 = time.time()
    cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(src), "--output-dir", str(out),
                         "--work-dir", str(work / "work"), "--runtime-dir", str(R3), "--target-seconds", "30", "--semantic", "off",
                         "--profile", "9x16", "--resolution", "social_hd", "--progress-file", str(work / "progress.json")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    dt = time.time() - t0
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
    check("heavy_build_done", r is not None, cp.stderr[-1500:])
    if r:
        check("heavy_nothing_timed_out", not [x for x in r.get("skipped_inputs", []) if "TIMEOUT" in x["reason"] or "ANALYSIS" in x["reason"]],
              r.get("skipped_inputs"))
        check("heavy_social_hd", (r["output"]["width"], r["output"]["height"]) == (1080, 1920))
        check("heavy_cut_from_original", r.get("render_source") == "ORIGINAL_FULL_QUALITY_RECUT")
        check("heavy_uses_several_sources", len(set(r["selected_sources"])) >= 2, r["selected_sources"])
    print(json.dumps({"build_s": round(dt, 1), "reel_s": r and r["actual_duration_s"], "passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

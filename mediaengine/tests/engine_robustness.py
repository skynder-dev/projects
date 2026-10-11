"""R3 engine robustness on real (synthetic) media, outside the R2-identical path.

  python tests/engine_robustness.py <fixtures_dir> <work_root>

Uses <fixtures_dir>/static (2 clips + 1 still video). Checks, technical mode (the model is not in git):
  - a video the analysis cannot use is skipped and reported, the reel is still built (R2 failed the whole run);
  - a later run in the same work folder with a file marked Private ignores that file's old analysis
    (R2 rescanned every item ever analysed and failed);
  - too little footage for the requested length gives an honest shorter reel with LIMITED_TOTAL_FOOTAGE;
  - a damaged segment cache entry is rebuilt instead of failing the project forever;
  - Social HD is vertical only.
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / "app" / "archivist" / "engine_p11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    fx, work_root = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    folder = fx / "static"
    shutil.rmtree(work_root, ignore_errors=True)
    work_root.mkdir(parents=True)
    env = dict(os.environ)
    try:
        import imageio_ffmpeg
        ff = os.environ.get("MEDENG_FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ff = os.environ.get("MEDENG_FFMPEG", "ffmpeg")
    env.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work_root / "no-model"))
    work = work_root / "work"
    checks = []

    def check(name, ok, detail=None):
        checks.append((name, bool(ok)))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def run(tag, target, extra=(), expect_ok=True):
        out = work_root / ("out_" + tag)
        cmd = [sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(folder), "--output-dir", str(out),
               "--work-dir", str(work), "--runtime-dir", str(R3), "--target-seconds", str(target), "--semantic", "off", *extra]
        cp = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if cp.returncode != 0:
            if expect_ok:
                print(cp.stdout[-1500:], cp.stderr[-2500:])
            return None, cp
        return json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")), cp

    r, _ = run("a", 15)
    skipped = {x["name"]: x["reason"] for x in (r or {}).get("skipped_inputs", [])}
    check("still_video_skipped_reel_built", r and r["status"] == "PASS" and skipped.get("still.mp4") in ("STATIC_VIDEO", "NO_MOMENTS")
          and "still.mp4" not in r["selected_sources"], skipped)
    check("skipped_file_not_in_inputs", r and "still.mp4" not in [x["name"] for x in r["inputs"]], r and r["inputs"])

    priv = work_root / "private.txt"
    priv.write_text(sha(folder / "clip_1.mp4") + "\n", encoding="utf-8")
    r, _ = run("b", 15, ["--skip-sha-file", str(priv)])
    skipped = {x["name"]: x["reason"] for x in (r or {}).get("skipped_inputs", [])}
    check("private_file_ignored_with_old_analysis_present", r and skipped.get("clip_1.mp4") == "PRIVATE"
          and set(r["selected_sources"]) == {"clip_3.mp4"}, (skipped, r and r["selected_sources"]))

    r, _ = run("c", 60)
    check("limited_footage_gives_shorter_reel", r and "LIMITED_TOTAL_FOOTAGE" in r.get("warnings", []) and r["actual_duration_s"] < 60,
          r and (r.get("warnings"), r["actual_duration_s"]))

    segs = sorted((work / "segment_cache_v2").glob("*.mp4"))
    if segs:
        segs[0].write_bytes(b"damaged")
    r, _ = run("d", 15)
    check("damaged_segment_cache_rebuilt", segs and r and r["status"] == "PASS", segs[:1])

    r, cp = run("e", 15, ["--profile", "16x9", "--resolution", "social_hd"], expect_ok=False)
    check("social_hd_is_vertical_only", r is None and "PRESET_NOT_ACCEPTED" in (cp.stdout + cp.stderr), cp.stderr[-300:])

    print(json.dumps({"passed": sum(ok for _, ok in checks), "total": len(checks)}))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

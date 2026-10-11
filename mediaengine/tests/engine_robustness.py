"""R3 engine robustness on real (synthetic) media, outside the R2-identical path.

  python tests/engine_robustness.py <fixtures_dir> <work_root>

Uses <fixtures_dir>/static (2 clips + 1 still video). Checks, technical mode (the model is not in git):
  - a video the analysis cannot use is skipped and reported, the reel is still built (R2 failed the whole run);
  - a later run in the same work folder with a file marked Private ignores that file's old analysis
    (R2 rescanned every item ever analysed and failed);
  - too little footage for the requested length gives an honest shorter reel with LIMITED_TOTAL_FOOTAGE;
  - a damaged segment cache entry is rebuilt instead of failing the project forever;
  - Social HD is vertical only;
  - phone/camera files (<fixtures_dir>/phone): rotated portrait, HEVC .MOV 60 fps, VFR, no audio track, very short clip,
    Cyrillic names build a reel, and the rotated clip comes out upright in every format.
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / "app" / "archivist" / "engine_p11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def upright_rows(ff, path):
    """16 horizontal bands of a frame 2.5 s in: R = red, B = blue, - = other."""
    cp = subprocess.run([ff, "-v", "error", "-ss", "2.5", "-i", str(path), "-frames:v", "1", "-vf", "scale=90:160",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    raw = cp.stdout
    if len(raw) != 90 * 160 * 3:
        return "no-frame"
    out = ""
    for i in range(16):
        band = raw[i * 10 * 90 * 3:(i + 1) * 10 * 90 * 3]
        r, b = sum(band[0::3]) / (len(band) / 3), sum(band[2::3]) / (len(band) / 3)
        out += "R" if r > b + 60 else ("B" if b > r + 60 else "-")
    return out


def patch_colours(ff, path):
    """RGB at the centre of the red and grey patches (fixtures: top-left red C81E1E, top-right grey 808080) in a
    16x9 reel frame 2.5 s in (the 1280x720 source is shown whole, scaled)."""
    cp = subprocess.run([ff, "-v", "error", "-ss", "2.5", "-i", str(path), "-frames:v", "1", "-vf", "scale=128:72",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    a = cp.stdout
    if len(a) != 128 * 72 * 3:
        return None, None
    px = lambda x, y: tuple(a[(y * 128 + x) * 3:(y * 128 + x) * 3 + 3])
    return px(12, 8), px(115, 8)


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

    # phone / camera files: rotated portrait, HEVC .MOV 60 fps, VFR, no audio, very short, Cyrillic names
    phone = fx / "phone"
    out = work_root / "out_phone"
    cmd = [sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(phone), "--output-dir", str(out),
           "--work-dir", str(work_root / "work_phone"), "--runtime-dir", str(R3), "--target-seconds", "30", "--semantic", "off",
           "--profile", "9x16", "--resolution", "social_hd"]
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
    if r is None:
        print(cp.stdout[-1500:], cp.stderr[-2500:])
    used = set((r or {}).get("selected_sources", []))
    skipped = {x["name"]: x["reason"] for x in (r or {}).get("skipped_inputs", [])}
    check("phone_files_build", r and r["output"]["width"] == 1080 and r["output"]["height"] == 1920
          and {"Отпуск — пляж.mp4", "IMG_0042.MOV", "переменная частота.mp4", "no_audio.mp4"} <= used, (used, skipped))
    check("phone_short_clip_reported", r and (("short.mp4" in used) or skipped.get("short.mp4", "").startswith(("TOO_SHORT", "ANALYSIS"))), skipped)
    if r:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from media_measure import av_durations
        vd, ad = av_durations(out / "MediaEngine Reel.mp4", ff)
        if r["audio"]["applied"] == "mute":
            check("phone_reel_audio_video_same_length", vd > 5 and (ad is None or abs(vd - ad) <= 0.1), (vd, ad))
        else:
            check("phone_reel_audio_video_same_length", vd > 5 and ad is not None and abs(vd - ad) <= 0.1, (vd, ad))
    # the rotated clip alone: must come out upright (red band on top, blue at the bottom) in every format
    rot_dir = work_root / "rot_in"
    rot_dir.mkdir(exist_ok=True)
    shutil.copy2(phone / "Отпуск — пляж.mp4", rot_dir / "Отпуск — пляж.mp4")
    for prof, res in (("9x16", "social_hd"), ("9x16", "standard"), ("16x9", "standard")):
        out = work_root / f"out_rot_{prof}_{res}"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(rot_dir), "--output-dir", str(out),
                             "--work-dir", str(work_root / "work_rot"), "--runtime-dir", str(R3), "--target-seconds", "5", "--semantic", "off",
                             "--profile", prof, "--resolution", res], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        rows = upright_rows(ff, out / "MediaEngine Reel.mp4") if cp.returncode == 0 else "failed"
        check(f"rotated_phone_video_upright_{prof}_{res}", rows.startswith("R") and rows.endswith("B") and "B" not in rows[:4]
              and "R" not in rows[-4:], rows)

    # HDR phone video (HLG like iPhone, PQ like HDR10): the reel must show normal colours, not grey/dark HDR numbers
    for kind in ("hlg", "pq"):
        d = fx / "hdr" / kind
        if not d.is_dir():
            print(f"SKIP hdr_{kind}: fixture not made (no zscale in the fixture ffmpeg)")
            continue
        out = work_root / f"out_hdr_{kind}"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(d), "--output-dir", str(out),
                             "--work-dir", str(work_root / f"work_hdr_{kind}"), "--runtime-dir", str(R3), "--target-seconds", "5",
                             "--semantic", "off", "--profile", "16x9"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
        red, grey = patch_colours(ff, out / "MediaEngine Reel.mp4") if r else (None, None)
        ok = (r and r.get("hdr_sources") and "HDR_NOT_CONVERTED" not in r.get("warnings", []) and red and grey
              and red[0] >= 160 and red[1] <= 70 and red[2] <= 70 and 100 <= grey[1] <= 160)
        check(f"hdr_{kind}_normal_colours", ok, (cp.stderr[-400:] if not r else (r.get("hdr_sources"), r.get("warnings"), red, grey)))

    print(json.dumps({"passed": sum(ok for _, ok in checks), "total": len(checks)}))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

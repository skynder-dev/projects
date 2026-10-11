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
    Cyrillic names build a reel, and the rotated clip comes out upright in every format;
  - HDR (HLG/PQ) shows normal colours; camcorder 1080i .MTS is read, de-interlaced and can be trimmed by hand;
  - wide pictures stored in narrow pixels (HDV 1440x1080, DVD 16:9) keep their shape (a square stays square);
  - other formats (5.1 sound, 120 fps HEVC, square, odd size 4:4:4, MJPEG AVI + PCM, VP9/Opus WebM, 10-bit H.264,
    two sound tracks, sound starting late, ProRes, old 3GP) are all analysed and used.
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(Path(__file__).resolve().parent))


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


def box_aspect(ff, path, t):
    """Width/height of the white square (fixtures: anamorphic/) as shown in the reel frame at t seconds."""
    pr = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    import re
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", pr or "")
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    raw = subprocess.run([ff, "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    if len(raw) < w * h:
        return None
    rows = [raw[y * w:(y + 1) * w] for y in range(h)]
    ys = [y for y, r in enumerate(rows) if max(r) > 235]
    if not ys:
        return None
    xs = [x for x in range(w) if any(rows[y][x] > 235 for y in ys[::max(1, len(ys) // 40)])]
    return round((max(xs) - min(xs) + 1) / (max(ys) - min(ys) + 1), 3)


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

    # camcorder: interlaced 1080i AVCHD .MTS must be read and de-interlaced
    cam = fx / "camcorder"
    mts = cam / "00012.MTS"
    readable = False
    if mts.is_file():
        pr = subprocess.run([ff, "-hide_banner", "-i", str(mts)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        readable = pr.returncode >= 0 and "Video:" in (pr.stderr or "")
    if not readable:
        print("SKIP camcorder: fixture missing or this ffmpeg build cannot read MPEG-TS (.MTS)")
    else:
        out = work_root / "out_cam"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(cam), "--output-dir", str(out),
                             "--work-dir", str(work_root / "work_cam"), "--runtime-dir", str(R3), "--target-seconds", "15",
                             "--semantic", "off", "--profile", "16x9"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
        check("camcorder_mts_used_and_deinterlaced", r and "00012.MTS" in r["selected_sources"] and "00012.MTS" in r.get("deinterlaced_sources", []),
              cp.stderr[-500:] if not r else (r["selected_sources"], r.get("deinterlaced_sources"), r.get("skipped_inputs")))

        if r and "00012.MTS" in r["selected_sources"]:
            # a hand trim of the camcorder clip must be cut from the readable stand-in (a cut straight from the stream
            # gave sound without picture on Windows)
            ev = next(s for s in r["segments"] if s["source_name"] == "00012.MTS")
            edits = work_root / "cam_edits.json"
            edits.write_text(json.dumps({"selection": [s["event_id"] for s in r["segments"]], "trims": {ev["event_id"]: [1.0, 5.0]}}),
                             encoding="utf-8")
            out = work_root / "out_cam_trim"
            cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(cam), "--output-dir", str(out),
                                 "--work-dir", str(work_root / "work_cam"), "--runtime-dir", str(R3), "--target-seconds", "15",
                                 "--semantic", "off", "--profile", "16x9", "--edits", str(edits)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            r2 = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
            seg = next((s for s in (r2 or {}).get("segments", []) if s["source_name"] == "00012.MTS"), None)
            frame = None
            if seg:
                fcp = subprocess.run([ff, "-v", "error", "-ss", str(seg["reel_in_s"] + 1.0), "-i", str(out / "MediaEngine Reel.mp4"),
                                      "-frames:v", "1", "-vf", "scale=32:18", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
                frame = max(fcp.stdout) if fcp.stdout else None
            check("camcorder_mts_hand_trim_has_picture", seg and seg.get("manual_trim") and frame and frame > 60,
                  cp.stderr[-500:] if not r2 else (seg, frame))

    # wide pictures in narrow pixels: the white square must stay square (it came out 0.70 wide before)
    ana = fx / "anamorphic"
    if ana.is_dir():
        for prof, res in (("16x9", "standard"), ("9x16", "social_hd")):
            out = work_root / f"out_ana_{prof}"
            cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(ana), "--output-dir", str(out),
                                 "--work-dir", str(work_root / "work_ana"), "--runtime-dir", str(R3), "--target-seconds", "15",
                                 "--semantic", "off", "--profile", prof, "--resolution", res],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
            shapes = []
            for s in (r or {}).get("segments", []):
                mid = (s["reel_in_s"] + s["reel_out_s"]) / 2
                shapes.append((s["source_name"], box_aspect(ff, out / "MediaEngine Reel.mp4", mid)))
            check(f"anamorphic_keeps_shape_{prof}", r and set(r.get("widened_sources", {})) == {"HDV_1440.mp4", "DVD_169.mpg"}
                  and len(shapes) >= 2 and all(a and 0.96 <= a <= 1.04 for _, a in shapes),
                  cp.stderr[-500:] if not r else (r.get("widened_sources"), shapes))

    # other formats people have on disk
    fmt = fx / "formats"
    have = sorted(p.name for p in fmt.iterdir()) if fmt.is_dir() else []
    if have:
        out = work_root / "out_formats"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(fmt), "--output-dir", str(out),
                             "--work-dir", str(work_root / "work_formats"), "--runtime-dir", str(R3), "--target-seconds", "60",
                             "--semantic", "off", "--profile", "16x9"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
        used = set((r or {}).get("selected_sources", []))
        skipped = {x["name"]: x["reason"] for x in (r or {}).get("skipped_inputs", [])}
        check("other_formats_analysed", r and not skipped, cp.stderr[-800:] if not r else skipped)
        check("other_formats_used", r and len(used) >= len(have) - 2, (sorted(set(have) - used), len(have)))
        if r:
            from media_measure import av_durations
            vd, ad = av_durations(out / "MediaEngine Reel.mp4", ff)
            check("other_formats_sound_as_long_as_picture", vd > 30 and ad is not None and abs(vd - ad) <= 0.1, (vd, ad, r["audio"]["applied"]))
        print("formats:", len(have), "used:", len(used), "stage seconds:", (r or {}).get("stage_seconds"))

    # older formats (Windows Media, Flash, DVD VOB, JVC MOD/TOD, HDV tape, DV tape); MPEG-TS needs a build that reads it
    old = fx / "older"
    have = sorted(p.name for p in old.iterdir()) if old.is_dir() else []
    if have and not readable:
        print("SKIP older TS formats: this ffmpeg build cannot read MPEG-TS")
        have = [n for n in have if Path(n).suffix.lower() not in (".tod", ".m2t")]
        old2 = work_root / "older_no_ts"
        old2.mkdir(exist_ok=True)
        for n in have:
            shutil.copyfile(old / n, old2 / n)
        old = old2
    if have:
        out = work_root / "out_older"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(old), "--output-dir", str(out),
                             "--work-dir", str(work_root / "work_older"), "--runtime-dir", str(R3), "--target-seconds", "60",
                             "--semantic", "off", "--profile", "16x9"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
        used = set((r or {}).get("selected_sources", []))
        skipped = {x["name"]: x["reason"] for x in (r or {}).get("skipped_inputs", [])}
        check("older_formats_analysed_and_used", r and not skipped and len(used) >= len(have) - 1,
              cp.stderr[-800:] if not r else (skipped, sorted(set(have) - used)))
        wide = set((r or {}).get("widened_sources", {}))
        check("older_formats_wide_ones_widened", r and {"MOV001.MOD", "tape.dv"} & used <= wide, (wide, used))
        print("older formats:", len(have), "used:", len(used), "widened:", sorted(wide))

    # a quiet and a loud clip (like a phone next to a camera): the accepted render brings every moment to the same
    # loudness (loudnorm per segment) - the reel must not jump in volume between them
    lv = fx / "levels"
    if lv.is_dir():
        import re

        def mean_db(path, a=None, t=None):
            cmd = [ff, "-hide_banner", "-nostats"] + (["-ss", f"{a:.3f}", "-t", f"{t:.3f}"] if a is not None else []) + \
                  ["-i", str(path), "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"]
            m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                                                          errors="replace").stderr or "")
            return float(m.group(1)) if m else None
        src = [mean_db(x) for x in sorted(lv.glob("*.mp4"))]
        out = work_root / "out_levels"
        cp = subprocess.run([sys.executable, str(R3 / "p11_folder_to_reel_r3.py"), "--input-dir", str(lv), "--output-dir", str(out),
                             "--work-dir", str(work_root / "work_levels"), "--runtime-dir", str(R3), "--target-seconds", "15",
                             "--semantic", "off", "--profile", "16x9", "--audio", "source"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        r = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8")) if cp.returncode == 0 else None
        reel = {}
        for sg in (r or {}).get("segments", []):
            a, b = sg["reel_in_s"] + 0.4, sg["reel_out_s"] - 0.4
            if b - a >= 0.5:
                reel.setdefault(sg["source_name"], mean_db(out / "MediaEngine Reel.mp4", a, b - a))
        before = max(src) - min(src) if len(src) == 2 and None not in src else None
        after = max(reel.values()) - min(reel.values()) if len(reel) == 2 and None not in reel.values() else None
        check("sound_levels_evened_out", before and after is not None and before > 15 and after <= 4,
              cp.stderr[-500:] if not r else (src, reel))
        print("levels: sources", before and round(before, 1), "dB apart; in the reel", after is not None and round(after, 1), "dB")

    print(json.dumps({"passed": sum(ok for _, ok in checks), "total": len(checks)}))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

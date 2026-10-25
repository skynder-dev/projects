"""AI-mode GLUE test with a STUB ranking (not an AI quality test; the real FAST_LOCAL model is not in git).

  python tests/semantic_glue_check.py <fixtures_dir> <work_dir>

Runs the R3 orchestrator in-process with semantic=required, but replaces the model preflight and the semantic hook
with a stub that ranks fixed windows per video (two of them overlap on purpose). Checks the R3 code that AI mode uses
around the model: candidate clips cut from the original, overlap removal, bounded selection, skipped damaged file,
full render with sound fitted to picture. Any claim about AI quality needs the real model on the owner's PC.
"""
from __future__ import annotations

import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
from media_measure import av_durations, ffmpeg_exe  # noqa: E402


class StubSemantic:
    """analyze_video() returns three ranked windows per video: 1-6 s, 3-8 s (overlaps the first by 60 %), 8-13 s."""

    @staticmethod
    def analyze_video(path, mode, profile, model_root, ffmpeg, ffprobe):
        size = Path(path).stat().st_size
        base = (size % 97) / 1000.0
        wins = [(1.0, 6.0, 0.90 - base), (3.0, 8.0, 0.88 - base), (8.0, 13.0, 0.70 - base)]
        return {"ranked": [{"start_s": a, "end_s": b, "center_s": (a + b) / 2, "scout_eventness": 0.6, "scout_novelty": 0.5,
                            "scout_quality": 0.7, "semantic_margin_raw": 0.1, "final_score": sc, "semantic_scout_score": sc}
                           for a, b, sc in wins]}


def ffprobe_wh(ff, path):
    """(width, height) of a video's picture, read with ffmpeg itself (no ffprobe needed)."""
    err = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    return (int(m.group(1)), int(m.group(2))) if m else (99999, 99999)


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "stub-model"))
    src = work / "in"
    shutil.copytree(fx / "seven", src)

    def build(name, work_name=None, prepare=False):
        spec = importlib.util.spec_from_file_location("r3_under_test_" + name, R3 / "p11_folder_to_reel_r3.py")
        r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
        real_load = r3.load_module
        r3.load_module = lambda n, path: StubSemantic if n == "medeng_event_semantic_v7" else real_load(n, path)
        r3.semantic_runtime_preflight = lambda runtime, model_root, adapter_root: {"pass": True, "checks": {"stub": True}, "note": "STUB - not the model"}
        out_ = work / ("out" if name == "one" else "out_" + name)
        wd = work / (work_name or ("w" if name == "one" else "w_" + name))
        args = argparse.Namespace(input_dir=str(src), input_list="", output_dir=str(out_), work_dir=str(wd),
                                  runtime_dir=str(R3), target_seconds=30.0, audio="auto", semantic="required", profile="9x16",
                                  resolution="social_hd", progress_file="", exclude_events="", edits="", skip_sha_file="",
                                  prepare_only=prepare)
        r3.run(args)
        return out_, r3

    os.environ["MEDENG_SEMANTIC_WORKERS"] = "1"
    out, r3 = build("one")
    # several videos analysed at once (a PC with many cores): the same reel to the frame; "seven" has a copy of a
    # video under another name, which once made two threads write the same clip file
    os.environ["MEDENG_SEMANTIC_WORKERS"] = "3"
    os.environ["MEDENG_RENDER_WORKERS"] = "3"          # and the pieces cut three at once
    os.environ["MEDENG_CLIP_WORKERS"] = "2"            # and each video's moments two at a time
    out3, _ = build("three")
    os.environ.pop("MEDENG_SEMANTIC_WORKERS", None)
    os.environ.pop("MEDENG_RENDER_WORKERS", None)
    os.environ.pop("MEDENG_CLIP_WORKERS", None)
    # what the AI found and the moment clips, shared by all projects (the app sets MEDENG_AI_SHARED_CACHE): a new
    # project from the same videos analyses and cuts nothing; a project made before the cache was shared hands its
    # files over (moved, not analysed again)
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared")
    out_sn, _ = build("shared_new")
    out_sa, _ = build("shared_again")
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_adopt")
    out_ad, _ = build("adopt", work_name="w")          # the work folder of build "one", made without the shared cache
    # the reports are there but the clips are not (b113's reports, b117's first build on the owner's PC): the videos go
    # three at once all the same, the clips are cut again, nothing is analysed again - the same reel
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_reclip")
    shutil.copytree(work / "shared" / "semantic_reports", work / "shared_reclip" / "semantic_reports")
    os.environ["MEDENG_SEMANTIC_WORKERS"] = "3"
    out_rc, _ = build("reclip")
    os.environ.pop("MEDENG_SEMANTIC_WORKERS", None)
    # the same on a 16-core PC without a set number: only cutting is left - more cuts at once (memory allowing)
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_reclip16")
    shutil.copytree(work / "shared" / "semantic_reports", work / "shared_reclip16" / "semantic_reports")
    real_cpus = os.cpu_count
    os.cpu_count = lambda: 16
    try:
        out_rc16, r3_16 = build("reclip16")
    finally:
        os.cpu_count = real_cpus
    # decoding on the graphics card that fails (here: a method FFmpeg does not know): every cut is made again on the
    # processor - the same reel, nothing left at preview quality
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_hw")
    os.environ["MEDENG_HWACCEL"] = "no_such_method"
    out_hw, _ = build("hwfallback")
    # the path a working graphics card takes ('-hwaccel none' = FFmpeg's own decoder): the card's cut with the picture
    # format step - every preview clip byte-identical to the processor's
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_hwnone")
    os.environ["MEDENG_HWACCEL"] = "none"
    out_hn, _ = build("hwnone")
    os.environ.pop("MEDENG_HWACCEL", None)
    # "Prepare in advance": analysis only (no reel); the reel made after it analyses, cuts and measures nothing
    os.environ["MEDENG_AI_SHARED_CACHE"] = str(work / "shared_prep")
    out_pp, _ = build("prep", prepare=True)
    rows_before = sorted(x.name for x in (work / "shared_prep" / "camera_drop_rows").glob("*.json"))
    out_ap, _ = build("after_prep", work_name="w_prep")
    rows_after = sorted(x.name for x in (work / "shared_prep" / "camera_drop_rows").glob("*.json"))
    os.environ.pop("MEDENG_AI_SHARED_CACHE", None)
    res = json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8"))
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    check("ai_glue_mode_label", res["selection_mode"].startswith("FAST_LOCAL"), res["selection_mode"])
    check("ai_glue_overlaps_removed", any(w.startswith("OVERLAPPING_MOMENTS_DROPPED") for w in res.get("warnings", [])), res.get("warnings"))
    segs = res["segments"]
    by_src = {}
    for s_ in segs:
        by_src.setdefault(s_["source_name"], []).append((s_["source_in_s"], s_["source_out_s"]))
    overlap = any(min(b1, b2) - max(a1, a2) > 0.5 * min(b1 - a1, b2 - a2) for v in by_src.values() for i, (a1, b1) in enumerate(v)
                  for (a2, b2) in v[i + 1:])
    check("ai_glue_no_moment_twice", not overlap, by_src)
    check("ai_glue_damaged_and_duplicate_skipped", {"broken.mp4"} <= {x["name"] for x in res["skipped_inputs"]}, res["skipped_inputs"])
    vd, ad = av_durations(out / "MediaEngine Reel.mp4", ff)
    check("ai_glue_reel_sound_fits_picture", ad is not None and abs(vd - ad) <= 0.05 and abs(vd - res["actual_duration_s"]) <= 0.1, (vd, ad))
    check("ai_glue_social_hd", (res["output"]["width"], res["output"]["height"]) == (1080, 1920))
    def same_reel(o1, o2):
        """Same moments in the same order, the same sound, the same picture (PSNR: x264 in FFmpeg 7 is not always
        bit-identical from run to run - with "fast" as with "veryfast", 1-2 runs in 10 on the same clip, 49-75 dB, far
        below what an eye can see; the same reel one frame late gives 9-18 dB - so every frame >= 40 dB)."""
        r1, r2 = (json.loads((o / "MediaEngine Result.json").read_text(encoding="utf-8")) for o in (o1, o2))
        cut = (r1["selected_event_ids"] == r2["selected_event_ids"] and
               [(x["source_name"], x["source_in_s"], x["source_out_s"]) for x in r1["segments"]] ==
               [(x["source_name"], x["source_in_s"], x["source_out_s"]) for x in r2["segments"]])
        a_md5 = [subprocess.run([ff, "-v", "error", "-i", str(o / "MediaEngine Reel.mp4"), "-map", "0:a", "-f", "md5", "-"],
                                capture_output=True, text=True).stdout.strip() for o in (o1, o2)]
        pq = subprocess.run([ff, "-hide_banner", "-i", str(o1 / "MediaEngine Reel.mp4"), "-i", str(o2 / "MediaEngine Reel.mp4"),
                             "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"], capture_output=True, text=True).stderr
        m = re.search(r"PSNR .*? min:(\S+)", pq)
        pmin = float("inf") if m and m.group(1) == "inf" else (float(m.group(1)) if m else -1.0)
        return bool(cut and a_md5[0] == a_md5[1] and a_md5[0] and pmin >= 40), (cut, a_md5, pmin)

    ok_, det_ = same_reel(out, out3)
    t3_ = json.loads((out3 / "MediaEngine Result.json").read_text(encoding="utf-8")).get("semantic_timing") or {}
    check("ai_glue_parallel_analysis_same_reel", ok_ and t3_.get("clip_workers") == 2, (det_, t3_.get("clip_workers")))
    # the moment clips themselves are bit-identical when cut again (x264 sync-lookahead=0)
    # (cut three times: build "one" - its clips were handed over to shared_adopt -, "three" and "shared_new")
    shas = [{f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (work / d / "semantic_previews").glob("*.mp4")}
            for d in ("w", "w_three", "shared", "shared_adopt")]
    check("ai_moment_clips_cut_the_same_every_time", shas[0] and shas[0] == shas[1] == shas[2] == shas[3],
          sorted(k for k in shas[0] if not shas[0].get(k) == shas[1].get(k) == shas[2].get(k) == shas[3].get(k))[:5])
    # the moments are analysed on previews (at most 960 px wide) and the reel is cut from the originals
    pv = [ffprobe_wh(ff, f) for f in sorted((work / "shared" / "semantic_previews").glob("*.mp4"))[:3]]
    check("ai_previews_small_reel_from_originals", pv and all(w_ <= 960 for w_, _ in pv)
          and res.get("render_source") == "ORIGINAL_FULL_QUALITY_RECUT"
          and not any(w.startswith("PREVIEW_QUALITY_USED") for w in res.get("warnings", [])), (pv, res.get("render_source")))
    tim = {k: json.loads((o / "MediaEngine Result.json").read_text(encoding="utf-8")).get("semantic_timing") or {}
           for k, o in (("new", out_sn), ("again", out_sa), ("adopt", out_ad))}
    check("ai_shared_cache_filled_by_the_first_project", tim["new"].get("shared_cache") and tim["new"].get("videos_analysed", 0) > 0
          and tim["new"].get("clips_cut", 0) > 0 and any((work / "shared" / "semantic_previews").glob("*.mp4"))
          and any((work / "shared" / "semantic_reports").glob("*.json")) and any((work / "shared" / "v22_metrics").glob("*.json"))
          and (work / "shared" / "source_sha256.json").is_file() and any((work / "shared" / "signatures").glob("*.json"))
          and any((work / "shared" / "camera_drop_rows").glob("*.json")), tim["new"])
    ok_, det_ = same_reel(out, out_sa)
    check("ai_shared_cache_new_project_analyses_and_cuts_nothing", tim["again"].get("videos_analysed") == 0 and tim["again"].get("clips_cut") == 0
          and tim["again"].get("clips_measured") == 0 and tim["again"].get("clips_cached", 0) > 0 and ok_, (tim["again"], det_))
    ok_, det_ = same_reel(out, out_ad)
    check("ai_shared_cache_takes_over_an_older_projects_files", tim["adopt"].get("videos_analysed") == 0
          and not any((work / "w" / "semantic_reports").glob("*.json")) and ok_, (tim["adopt"], det_))
    prep = json.loads((out_pp / "MediaEngine Prepared.json").read_text(encoding="utf-8"))
    after = json.loads((out_ap / "MediaEngine Result.json").read_text(encoding="utf-8"))
    ok_, det_ = same_reel(out, out_ap)
    check("prepare_in_advance_makes_no_reel", sorted(x.name for x in out_pp.iterdir()) == ["MediaEngine Prepared.json"]
          and prep.get("prepared") is True and prep.get("moments", 0) >= len(after.get("segments", [])) > 0
          and prep.get("clip_edges_measured", 0) >= len(after.get("segments", [])), prep)
    st_ = after.get("semantic_timing") or {}
    check("build_after_prepare_analyses_cuts_measures_nothing", st_.get("videos_analysed") == 0 and st_.get("clips_cut") == 0
          and st_.get("clips_measured") == 0 and rows_before and rows_after == rows_before and ok_, (st_, len(rows_before), len(rows_after), det_))
    rc_ = json.loads((out_rc / "MediaEngine Result.json").read_text(encoding="utf-8")).get("semantic_timing") or {}
    ok_, det_ = same_reel(out, out_rc)
    check("known_reports_missing_clips_cut_in_parallel", rc_.get("videos_analysed") == 0 and rc_.get("clips_cut", 0) > 0
          and rc_.get("workers") == 3 and ok_, (rc_, det_))
    res16 = json.loads((out_rc16 / "MediaEngine Result.json").read_text(encoding="utf-8"))
    rc16 = res16.get("semantic_timing") or {}
    ram16, n16 = r3_16._total_ram_gb(), int(res16.get("input_count") or 0)
    want16 = max(max(1, min(3, 16 // 4, int(ram16 // 6) or 1, n16)), min(6, 16 // 3, int(ram16 // 4) or 1, n16))
    ok_, det_ = same_reel(out, out_rc16)
    check("only_cutting_left_more_cuts_at_once_on_16_cores", rc16.get("videos_analysed") == 0 and rc16.get("clips_cut", 0) > 0
          and rc16.get("workers") == want16 and ok_, (rc16.get("workers"), want16, det_))
    hwres = json.loads((out_hw / "MediaEngine Result.json").read_text(encoding="utf-8"))
    ok_, det_ = same_reel(out, out_hw)
    hd_ = hwres.get("hw_decode") or {}
    check("hw_decode_failure_falls_back_to_processor", hd_.get("method") == "no_such_method" and hd_.get("cuts") == 0
          and hd_.get("fallbacks", 0) > 0 and not any(w.startswith("PREVIEW_QUALITY_USED") for w in hwres.get("warnings", [])) and ok_,
          (hd_, hwres.get("warnings"), det_))
    hn = json.loads((out_hn / "MediaEngine Result.json").read_text(encoding="utf-8"))
    hnd = hn.get("hw_decode") or {}
    sha_ = lambda d: {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((work / d / "semantic_previews").glob("*.mp4"))}
    a_, b_ = sha_("shared"), sha_("shared_hwnone")
    ok_, det_ = same_reel(out, out_hn)
    check("hw_decode_path_gives_the_same_clips", hnd.get("cuts", 0) > 0 and hnd.get("fallbacks") == 0 and a_ and a_ == b_ and ok_,
          (hnd, len(a_), len(b_), [k for k in a_ if a_.get(k) != b_.get(k)][:3], det_))
    # boundary rows from one pass through a clip = the accepted rows from a seek per row (OpenCV of this PC)
    cl = sorted((work / "shared" / "semantic_previews").glob("*.mp4"))[:6]
    same_rows = [r3.camera_drop_rows(c_) == r3.camera_drop_rows_fast(c_) for c_ in cl]
    check("boundary_rows_one_pass_same_as_seeks", cl and all(same_rows), [c_.name for c_, ok in zip(cl, same_rows) if not ok])
    # a spot-check that disagrees (another OpenCV, an odd clip): the clip is measured the accepted way
    real_seek, calls = r3._seek_row, []
    r3._seek_row = lambda path, t: {"t": -1.0}
    real_slow = r3.camera_drop_rows
    r3.camera_drop_rows = lambda path, step=.25: (calls.append(path), real_slow(path, step))[1]
    try:
        fb = r3.camera_drop_rows_fast(cl[0]) if cl else None
    finally:
        r3._seek_row, r3.camera_drop_rows = real_seek, real_slow
    check("boundary_rows_fall_back_when_a_spot_check_differs", cl and calls == [cl[0]] and fb == real_slow(cl[0]), calls)
    # a drone's 1-2 s shots: "too short", not "could not be analysed" (the folder page already says "too short")
    sk = r3._semantic_skip_reason
    check("ai_short_clip_is_too_short", sk(RuntimeError("SCOUT_INSUFFICIENT_FRAMES"), {"duration_s": 30.0}) == "TOO_SHORT_FOR_ANALYSIS"
          and sk(RuntimeError("DENSE_INSUFFICIENT_FRAMES"), {"duration_s": 2.3}) == "TOO_SHORT_FOR_ANALYSIS"
          and sk(RuntimeError("DENSE_INSUFFICIENT_FRAMES"), {"duration_s": 200.0}) == "ANALYSIS_FAILED:DENSE_INSUFFICIENT_FRAMES"
          and sk(RuntimeError("SOMETHING_ELSE: x"), {"duration_s": 2.3}) == "ANALYSIS_FAILED:SOMETHING_ELSE")
    print(json.dumps({"passed": sum(checks), "total": len(checks), "reel_s": res["actual_duration_s"], "segments": len(segs)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

"""AI-mode GLUE test with a STUB ranking (not an AI quality test; the real FAST_LOCAL model is not in git).

  python tests/semantic_glue_check.py <fixtures_dir> <work_dir>

Runs the R3 orchestrator in-process with semantic=required, but replaces the model preflight and the semantic hook
with a stub that ranks fixed windows per video (two of them overlap on purpose). Checks the R3 code that AI mode uses
around the model: candidate clips cut from the original, overlap removal, bounded selection, skipped damaged file,
full render with sound fitted to picture. Any claim about AI quality needs the real model on the owner's PC.
"""
from __future__ import annotations

import argparse, importlib.util, json, os, re, shutil, subprocess, sys
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


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "stub-model"))
    src = work / "in"
    shutil.copytree(fx / "seven", src)

    def build(name):
        spec = importlib.util.spec_from_file_location("r3_under_test_" + name, R3 / "p11_folder_to_reel_r3.py")
        r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
        real_load = r3.load_module
        r3.load_module = lambda n, path: StubSemantic if n == "medeng_event_semantic_v7" else real_load(n, path)
        r3.semantic_runtime_preflight = lambda runtime, model_root, adapter_root: {"pass": True, "checks": {"stub": True}, "note": "STUB - not the model"}
        out_ = work / ("out" if name == "one" else "out_" + name)
        args = argparse.Namespace(input_dir=str(src), input_list="", output_dir=str(out_), work_dir=str(work / ("w" if name == "one" else "w_" + name)),
                                  runtime_dir=str(R3), target_seconds=30.0, audio="auto", semantic="required", profile="9x16",
                                  resolution="social_hd", progress_file="", exclude_events="", edits="", skip_sha_file="")
        r3.run(args)
        return out_, r3

    os.environ["MEDENG_SEMANTIC_WORKERS"] = "1"
    out, r3 = build("one")
    # several videos analysed at once (a PC with many cores): the same reel to the frame; "seven" has a copy of a
    # video under another name, which once made two threads write the same clip file
    os.environ["MEDENG_SEMANTIC_WORKERS"] = "3"
    out3, _ = build("three")
    os.environ.pop("MEDENG_SEMANTIC_WORKERS", None)
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
    # several videos analysed at once: the same moments in the same order, the same sound and the same picture
    # (x264 in FFmpeg 7 is not always bit-identical from run to run, with "fast" as with "veryfast" - measured 1-2 runs in
    # 10 on the same clip, 49-75 dB, far below what an eye can see; the same reel one frame late gives 9-18 dB) - so the
    # picture is compared by PSNR, every frame >= 40 dB
    res3 = json.loads((out3 / "MediaEngine Result.json").read_text(encoding="utf-8"))
    same_cut = (res3["selected_event_ids"] == res["selected_event_ids"] and
                [(x["source_name"], x["source_in_s"], x["source_out_s"]) for x in res3["segments"]] ==
                [(x["source_name"], x["source_in_s"], x["source_out_s"]) for x in segs])
    a_md5 = [subprocess.run([ff, "-v", "error", "-i", str(o / "MediaEngine Reel.mp4"), "-map", "0:a", "-f", "md5", "-"],
                            capture_output=True, text=True).stdout.strip() for o in (out, out3)]
    pq = subprocess.run([ff, "-hide_banner", "-i", str(out / "MediaEngine Reel.mp4"), "-i", str(out3 / "MediaEngine Reel.mp4"),
                         "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"PSNR .*? min:(\S+)", pq)
    psnr_min = float("inf") if m and m.group(1) == "inf" else (float(m.group(1)) if m else -1.0)
    check("ai_glue_parallel_analysis_same_reel", same_cut and a_md5[0] == a_md5[1] and a_md5[0] and psnr_min >= 40,
          (same_cut, a_md5, psnr_min))
    # a drone's 1-2 s shots: "too short", not "could not be analysed" (the folder page already says "too short")
    sk = r3._semantic_skip_reason
    check("ai_short_clip_is_too_short", sk(RuntimeError("DENSE_INSUFFICIENT_FRAMES"), {"duration_s": 3.0}) == "TOO_SHORT_FOR_ANALYSIS"
          and sk(RuntimeError("SOMETHING_ELSE: x"), {"duration_s": 1.8}) == "TOO_SHORT_FOR_ANALYSIS"
          and sk(RuntimeError("SOMETHING_ELSE: x"), {"duration_s": 30.0}) == "ANALYSIS_FAILED:SOMETHING_ELSE")
    print(json.dumps({"passed": sum(checks), "total": len(checks), "reel_s": res["actual_duration_s"], "segments": len(segs)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

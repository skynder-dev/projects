"""AI-mode GLUE test with a STUB ranking (not an AI quality test; the real FAST_LOCAL model is not in git).

  python tests/semantic_glue_check.py <fixtures_dir> <work_dir>

Runs the R3 orchestrator in-process with semantic=required, but replaces the model preflight and the semantic hook
with a stub that ranks fixed windows per video (two of them overlap on purpose). Checks the R3 code that AI mode uses
around the model: candidate clips cut from the original, overlap removal, bounded selection, skipped damaged file,
full render with sound fitted to picture. Any claim about AI quality needs the real model on the owner's PC.
"""
from __future__ import annotations

import argparse, importlib.util, json, os, shutil, sys
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
    spec = importlib.util.spec_from_file_location("r3_under_test", R3 / "p11_folder_to_reel_r3.py")
    r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
    real_load = r3.load_module
    r3.load_module = lambda name, path: StubSemantic if name == "medeng_event_semantic_v7" else real_load(name, path)
    r3.semantic_runtime_preflight = lambda runtime, model_root, adapter_root: {"pass": True, "checks": {"stub": True}, "note": "STUB - not the model"}
    src = work / "in"
    shutil.copytree(fx / "seven", src)
    out = work / "out"
    args = argparse.Namespace(input_dir=str(src), input_list="", output_dir=str(out), work_dir=str(work / "w"), runtime_dir=str(R3),
                              target_seconds=30.0, audio="auto", semantic="required", profile="9x16", resolution="social_hd",
                              progress_file="", exclude_events="", edits="", skip_sha_file="")
    r3.run(args)
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
    print(json.dumps({"passed": sum(checks), "total": len(checks), "reel_s": res["actual_duration_s"], "segments": len(segs)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

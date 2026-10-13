"""AI+ GLUE test with a STAND-IN scorer (not an AI quality test; the real PE-Core model is tested by
tests/pe_core_probe.py and, on Windows CI, by a real AI+ build).

  python tests/aiplus_glue_check.py <fixtures_dir> <work_dir>

Runs the R3 orchestrator in-process with --semantic required --semantic-model pe_core_l14. The model preflight and
the scorer are replaced by a stand-in that prefers colourful frames; everything else is real: the accepted hook's
scout frames, candidate windows, rerank and dense check (imported unchanged), the AI+ descriptions, candidate clips
cut from the originals, selection, render. Checks: AI+ label in the result, own caches (AI and AI+ never mix), a
second build reuses the analysis without loading the model, a missing model is refused (never a silent fallback).
"""
from __future__ import annotations

import argparse, importlib.util, json, os, shutil, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
from media_measure import av_durations, ffmpeg_exe  # noqa: E402

LOADS = []
OPENED = {"vision": 0, "text": 0}


class StandInScorer:
    """Colourful frames match the good descriptions, grey frames the bad ones, blue frames the 'sea' theme."""
    identity = {"profile": "STAND_IN_NOT_THE_MODEL"}

    def __init__(self, *_a, **_k):
        LOADS.append(1)
        self._vision = self._text = None

    @property
    def vision(self):
        if self._vision is None:
            OPENED["vision"] += 1
            self._vision = True
        return self._vision

    @property
    def text(self):
        if self._text is None:
            OPENED["text"] += 1
            self._text = True
        return self._text

    @staticmethod
    def _n(a):
        a = np.asarray(a, np.float32)
        return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-9)

    def encode_images(self, images):
        assert self._vision, "vision part used without opening it"
        rows = []
        for im in images:
            a = np.asarray(im.convert("RGB"), np.float32) / 255.0
            colour = float(a.std(axis=2).mean())
            rows.append([colour, max(0.0, 0.25 - colour), float(a[..., 0].mean()), float(a[..., 2].mean() - a[..., 0].mean() + 0.5)])
        return self._n(rows)

    def encode_text(self, texts):
        assert self._text, "text part used without opening it"
        import p13_event_semantic_pe as hook
        sea = set(hook.THEMES["sea"][1])
        return self._n([[0, 1, 0, 0] if t in hook.NEGATIVE_PROMPTS else [0, 0, 0, 1] if t in sea else [1, 0, 0, 0] for t in texts])


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "models"))
    spec = importlib.util.spec_from_file_location("r3_under_test", R3 / "p11_folder_to_reel_r3.py")
    r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    src = work / "in"
    shutil.copytree(fx / "two", src)

    def args(out, **kw):
        a = dict(input_dir=str(src), input_list="", output_dir=str(out), work_dir=str(work / "w"), runtime_dir=str(R3),
                 target_seconds=10.0, audio="auto", semantic="required", semantic_model="pe_core_l14", theme="", profile="9x16",
                 resolution="standard", progress_file="", exclude_events="", edits="", skip_sha_file="")
        a.update(kw)
        return argparse.Namespace(**a)

    # the real preflight first: no model files -> refused, nothing built
    try:
        r3.run(args(work / "refused"))
        refused = False
    except RuntimeError as exc:
        refused = str(exc).startswith("AIPLUS_MODEL_NOT_READY")
    check("aiplus_missing_model_refused_no_fallback", refused and not (work / "refused" / "MediaEngine Reel.mp4").exists())

    r3.pe_runtime_preflight = lambda pe_dir: {"pass": True, "model_dir": str(pe_dir), "note": "STAND-IN - not the model"}
    r3.make_pe_scorer = lambda pe_dir: StandInScorer()
    r3.run(args(work / "out1"))
    res = json.loads((work / "out1" / "MediaEngine Result.json").read_text(encoding="utf-8"))
    check("aiplus_mode_label", res["selection_mode"] == "PE_CORE_L14_SEMANTIC_V1" and res.get("semantic_model") == "pe_core_l14",
          (res["selection_mode"], res.get("semantic_model")))
    check("aiplus_own_caches", (work / "w" / "semantic_reports_pe").is_dir() and not (work / "w" / "semantic_reports").exists()
          and any((work / "w" / "semantic_candidates_pe").glob("*.mp4")))
    rep = json.loads(next((work / "w" / "semantic_reports_pe").glob("*.json")).read_text(encoding="utf-8"))
    check("aiplus_report_has_ranked_windows", rep["report"]["hook"] == "P13_EVENT_SEMANTIC_PE_V2" and len(rep["report"]["ranked"]) >= 2,
          rep["report"].get("hook"))
    vd, ad = av_durations(work / "out1" / "MediaEngine Reel.mp4", ff)
    check("aiplus_reel_built_sound_fits", ad is not None and abs(vd - ad) <= 0.05 and vd > 3, (vd, ad))
    check("aiplus_model_loaded_once", len(LOADS) == 1, len(LOADS))
    r3.run(args(work / "out2", target_seconds=5.0))
    res2 = json.loads((work / "out2" / "MediaEngine Result.json").read_text(encoding="utf-8"))
    check("aiplus_second_build_reuses_analysis", len(LOADS) == 1 and res2["selection_mode"] == "PE_CORE_L14_SEMANTIC_V1", len(LOADS))
    ids1 = {s["event_id"] for s in res["segments"]}
    r3.run(args(work / "out3", semantic="off", semantic_model="fast_local"))
    res3 = json.loads((work / "out3" / "MediaEngine Result.json").read_text(encoding="utf-8"))
    # a theme for the analysed videos: only the text part of the model is opened, no frame is encoded again
    vision_before = OPENED["vision"]
    r3.run(args(work / "out_theme", theme="sea"))
    rt = json.loads((work / "out_theme" / "MediaEngine Result.json").read_text(encoding="utf-8"))
    check("aiplus_theme_reel_built", rt.get("theme") == "sea" and rt["selection_mode"] == "PE_CORE_L14_SEMANTIC_V1"
          and any(w.startswith("THEME:sea:") for w in rt.get("warnings", [])), (rt.get("theme"), rt.get("warnings")))
    check("aiplus_theme_needs_no_frame_encoding", OPENED["vision"] == vision_before, OPENED)
    check("aiplus_theme_cached_per_theme", any((work / "w" / "semantic_reports_pe").glob("*.sea.json"))
          and any((work / "w" / "semantic_reports_pe").glob("*.general.json")))
    try:
        r3.run(args(work / "out_bad", theme="no_such_theme"))
        bad = ""
    except RuntimeError as exc:
        bad = str(exc)
    check("aiplus_unknown_theme_refused", bad.startswith("UNKNOWN_THEME"), bad)
    check("technical_mode_unchanged", res3["selection_mode"] == "ACCEPTED_V52_TECHNICAL_AESTHETIC" and not ids1 & {s["event_id"] for s in res3["segments"]},
          res3["selection_mode"])
    # the model cannot start (e.g. not enough memory): one clear error, not "no moments" for every video
    def broken(_pe_dir):
        raise MemoryError("bad allocation")
    r3.make_pe_scorer = broken
    try:
        r3.run(args(work / "out4", work_dir=str(work / "w_new")))
        load_err = ""
    except RuntimeError as exc:
        load_err = str(exc)
    check("aiplus_model_start_failure_is_one_clear_error", load_err.startswith("AIPLUS_MODEL_LOAD_FAILED:MemoryError"), load_err)
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

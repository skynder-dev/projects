"""AI+ moment ranking: the accepted semantic hook's steps (scout frames, candidate windows, rerank, dense check of
the best three) with the stronger PE-Core L/14 model and descriptions written for personal footage (people, family,
travel, nature, events) instead of only travel / car b-roll.

The accepted hook (medeng_event_semantic_v7) is imported and used as it is - nothing in it is changed; only the
scorer and the descriptions differ. Weights are the accepted ones (.68 meaning / .32 scout, then .70 / .30 dense).
"""
from __future__ import annotations

import time
from pathlib import Path

HOOK = "P13_EVENT_SEMANTIC_PE_V1"

# fixed English descriptions (the model was trained on English captions); first the good, then the bad
POSITIVE_PROMPTS = (
    "a happy moment with people smiling or laughing",
    "children playing and having fun",
    "family or friends together",
    "a beautiful landscape or scenic view",
    "a striking sunset, sea, mountains or city view",
    "an interesting moment while traveling",
    "a celebration, party or special event",
    "a pet or an animal doing something cute",
    "an exciting action or sports moment",
    "a well composed shot with a clear subject",
)
NEGATIVE_PROMPTS = (
    "a boring frame where nothing happens",
    "a blurry or shaky low quality frame",
    "an accidental shot of the floor, the ceiling or a pocket",
    "a very dark underexposed frame",
    "a camera pointed at a car dashboard or interior",
    "a frame with no clear subject",
)


def analyze_video(v7, scorer, path: Path, ffmpeg="ffmpeg", ffprobe="ffprobe") -> dict:
    """SELECT_BEST of the accepted hook, with `scorer` (p13_pe_core_adapter.PECoreScorer or a test stand-in)."""
    import p13_pe_core_adapter as adapter

    def score_images(images):
        return adapter.margin(scorer.logits(images, list(POSITIVE_PROMPTS + NEGATIVE_PROMPTS)), len(POSITIVE_PROMPTS))

    scout_started = time.perf_counter()
    probed = v7.ffprobe_duration(path, ffprobe, ffmpeg)
    step = v7.adaptive_scout_step(probed, target_frames=48, min_step=1.0)
    duration, vals, unique_ratio = v7.parallel_scout_frames(path, step=step, ffmpeg=ffmpeg, ffprobe=ffprobe)
    scout_elapsed = time.perf_counter() - scout_started
    d = v7.feature_table(vals)
    candidates = v7.event_candidates(d, duration)
    started = time.perf_counter()
    ranked = v7.semantic_rerank(candidates, vals, score_images)
    semantic_elapsed = time.perf_counter() - started
    started = time.perf_counter()
    for c in ranked[:3]:
        c.update(v7.dense_window_quality(path, c["start_s"], c["end_s"], ffmpeg))
        c["final_score"] = round(.70 * c["semantic_scout_score"] + .30 * c["dense_score"], 6)
    for c in ranked[3:]:
        c["final_score"] = round(.70 * c["semantic_scout_score"], 6)
    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return {
        "video": str(path), "duration_s": round(duration, 6), "scout_frame_count": len(vals), "scout_step_s": round(step, 3),
        "scout_unique_ratio": round(unique_ratio, 4), "scout_elapsed_s": round(scout_elapsed, 3),
        "semantic_elapsed_s": round(semantic_elapsed, 3), "dense_refine_elapsed_s": round(time.perf_counter() - started, 3),
        "hook": HOOK, "semantic_model_identity": getattr(scorer, "identity", None),
        "mode": "SELECT_BEST", "selection_claim": True, "ranked": ranked,
    }

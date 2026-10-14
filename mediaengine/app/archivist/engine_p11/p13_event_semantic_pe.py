"""AI+ moment ranking with PE-Core L/14.

Steps (the accepted hook medeng_event_semantic_v7 is imported and used unchanged for scouting, features, technical
candidate windows and the dense check of the best three):
  1. scout frames of the video (accepted method, about one per second, at most 48), their technical features, and an
     AI+ embedding of EVERY scout frame - computed once per video and cached by the engine;
  2. rank windows for "no theme" (the accepted technical windows, scored by the meaning of all their frames, weights as
     in the accepted hook: .68 meaning / .32 scout) or for a THEME (windows centred on the frames that match the theme
     best - any part of the video can be chosen);
  3. dense check of the best three (accepted; with a theme: the best three that match it), final score .70 / .30.
A theme only needs the cached embeddings and a few text embeddings: no frame is decoded for the model again.
"""
from __future__ import annotations

import hashlib, json, time
from pathlib import Path

import numpy as np

HOOK = "P13_EVENT_SEMANTIC_PE_V3"
# what scout() stores (frames, features, embeddings): bump when scout() changes - ranking changes do not make the
# model look at the frames again
SCOUT_VERSION = "P13_SCOUT_V1"

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
    # added after the real-footage check (2026-10-13): a promo graphic and a close-up of twigs were chosen as moments
    "a drawing, logo or text graphic",
    "a close-up of the ground, branches or leaves",
)

# key: (English name for reports, descriptions). The interface shows Russian / English names (auto_edit.THEMES).
THEMES = {
    "sea": ("Sea and beach", ("the sea or the ocean", "a beach with waves", "people swimming in the sea", "a boat on the water")),
    "mountains": ("Mountains", ("mountains", "a mountain landscape", "a hiking trail in the mountains", "snowy mountain peaks")),
    "kids": ("Children", ("children playing", "a small child", "kids laughing", "a baby")),
    "family": ("Family and friends", ("a family together", "friends together", "people hugging", "a group of people smiling")),
    "party": ("Celebration", ("a birthday party", "a celebration with friends", "a wedding", "people dancing at a party")),
    "animals": ("Animals", ("a dog", "a cat", "a pet", "wild animals in nature")),
    "sunset": ("Sunset", ("a sunset", "a sunrise", "golden hour light", "the sky at dusk")),
    "nature": ("Nature", ("a forest", "a field with flowers", "a lake or a river", "green nature")),
    "snow": ("Winter and snow", ("snow", "a winter landscape", "people playing in the snow", "a snowy forest")),
    "city": ("City", ("a city street", "buildings in a city", "a town square", "city lights at night")),
    "food": ("Food", ("food on a table", "people eating together", "a meal at a restaurant", "cooking food")),
    "sport": ("Sport", ("people playing sports", "a person running or cycling", "skiing or snowboarding", "a ball game")),
    "road": ("Road trip", ("a road trip", "driving on a road", "a view from a car window", "a train or a plane journey")),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scout_key() -> str:
    """The key of what the model saw in a video: adapter + contract code, scout version, model files. The engine and
    'Prepare AI+ for the Library' use exactly this, so either one's result serves the other."""
    import p13_pe_core_contract as pc
    here = Path(__file__)
    code_sha = "|".join(_sha256(here.with_name(n)) for n in ("p13_pe_core_adapter.py", "p13_pe_core_contract.py"))
    model_key = "|".join(v[2] for v in pc.MODEL_FILES.values())
    return hashlib.sha256((code_sha + "|" + SCOUT_VERSION + "|" + model_key).encode()).hexdigest()


def read_scout(cache_dir: Path, sha: str, key: str):
    """(info, embeddings) from the cache, or (None, None)."""
    sj, sn = Path(cache_dir) / (sha + ".json"), Path(cache_dir) / (sha + ".npy")
    if not (sj.is_file() and sn.is_file()):
        return None, None
    try:
        obj = json.loads(sj.read_text(encoding="utf-8"))
        if obj.get("source_sha256") != sha or obj.get("key") != key:
            return None, None
        emb = np.load(sn).astype(np.float32)
        return (obj["info"], emb) if emb.shape[0] == len(obj["info"]["rows"]) else (None, None)
    except Exception:
        return None, None


def write_scout(cache_dir: Path, sha: str, key: str, info: dict, emb) -> None:
    """Own temp names (two processes may analyse the same video), embeddings first, then the description, then the
    key alone."""
    import os
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{os.getpid()}.{time.time_ns()}"
    tmp = cache_dir / (sha + f".{tag}.tmp.npy"); np.save(tmp, np.asarray(emb).astype(np.float16)); os.replace(tmp, cache_dir / (sha + ".npy"))
    tj = cache_dir / (sha + f".{tag}.tmp.json")
    tj.write_text(json.dumps({"source_sha256": sha, "key": key, "info": info}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tj, cache_dir / (sha + ".json"))
    # the key alone (64 bytes): the app counts the prepared videos without reading every description
    tk = cache_dir / (sha + f".{tag}.tmp.key")
    tk.write_text(key, encoding="utf-8")
    os.replace(tk, cache_dir / (sha + ".key"))


def prompts_for(theme: str | None):
    if theme:
        return THEMES[theme][1], NEGATIVE_PROMPTS
    return POSITIVE_PROMPTS, NEGATIVE_PROMPTS


def prompt_key(theme: str | None) -> str:
    pos, neg = prompts_for(theme)
    return hashlib.sha256(json.dumps([theme or "", list(pos), list(neg)]).encode()).hexdigest()[:16]


def scout(v7, scorer, path: Path, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    """Scout frames + features (accepted) and an AI+ embedding of every scout frame. Returns (info, embeddings)."""
    import cv2
    from PIL import Image
    started = time.perf_counter()
    probed = v7.ffprobe_duration(path, ffprobe, ffmpeg)
    step = v7.adaptive_scout_step(probed, target_frames=48, min_step=1.0)
    duration, vals, unique_ratio = v7.parallel_scout_frames(path, step=step, ffmpeg=ffmpeg, ffprobe=ffprobe)
    rows = v7.feature_table(vals)
    scout_s = time.perf_counter() - started
    started = time.perf_counter()
    emb = scorer.encode_images([Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)) for _, bgr in vals])
    info = {"hook": HOOK, "duration_s": round(float(duration), 6), "scout_step_s": round(float(step), 3),
            "scout_unique_ratio": round(float(unique_ratio), 4), "scout_frame_count": len(vals),
            "scout_elapsed_s": round(scout_s, 3), "embed_elapsed_s": round(time.perf_counter() - started, 3),
            "rows": [{k: float(v) for k, v in r.items()} for r in rows]}
    return info, np.asarray(emb, np.float32)


def frame_margins(scorer, emb, theme: str | None) -> np.ndarray:
    """Per scout frame: mean of the two best matching good descriptions minus the best bad one (as accepted)."""
    pos, neg = prompts_for(theme)
    lp = 100.0 * emb @ scorer.encode_text(list(pos)).T
    ln = 100.0 * emb @ scorer.encode_text(list(neg)).T
    k = min(2, lp.shape[1])
    return np.sort(lp, axis=1)[:, -k:].mean(axis=1) - ln.max(axis=1)


def _robust01(v7, xs):
    return v7.robust01(list(xs)) if len(xs) else np.asarray([])


def _window_stats(rows, margins, start, end):
    idx = [i for i, r in enumerate(rows) if start - 1e-6 <= float(r["t"]) <= end + 1e-6]
    if not idx:                                    # very short window: the nearest scout frame
        c = (start + end) / 2
        idx = [int(np.argmin([abs(float(r["t"]) - c) for r in rows]))]
    m = float(np.mean([margins[i] for i in idx]))
    q = float(np.mean([rows[i]["quality"] for i in idx]))
    ev = float(np.mean([rows[i]["eventness"] for i in idx]))
    nv = float(np.mean([rows[i]["novelty"] for i in idx]))
    sc = float(np.mean([rows[i]["scout_score"] for i in idx]))
    return m, q, ev, nv, sc


def theme_windows(rows, margins, duration, window=5.5, max_candidates=8):
    """Windows centred on the scout frames that match the theme best (at least 2 s apart)."""
    order = np.argsort(-np.asarray(margins))
    picked = []
    for i in order:
        center = float(rows[int(i)]["t"])
        start = min(max(0.0, center - window / 2), max(0.0, duration - window))
        start = round(start * 2) / 2
        end = min(duration, start + window)
        # 2 s apart by centre AND by start: near the ends of a short video two centres give the same window
        if all(abs(center - x["center_s"]) >= 2.0 and abs(start - x["start_s"]) >= 2.0 for x in picked):
            picked.append({"center_s": center, "start_s": round(start, 3), "end_s": round(end, 3)})
        if len(picked) >= max_candidates:
            break
    return picked


def rank(v7, scorer, path: Path, info: dict, emb, theme: str | None = None, ffmpeg="ffmpeg") -> dict:
    """Ranked windows of one video for 'no theme' or a theme (embeddings from scout(); only text is encoded here)."""
    rows, duration = info["rows"], float(info["duration_s"])
    margins = frame_margins(scorer, emb, theme)
    started = time.perf_counter()
    if theme:
        wins = theme_windows(rows, margins, duration)
    else:
        wins = [{"center_s": c["center_s"], "start_s": c["start_s"], "end_s": c["end_s"]} for c in v7.event_candidates(rows, duration)]
    cands = []
    for w in wins:
        m, q, ev, nv, sc = _window_stats(rows, margins, w["start_s"], w["end_s"])
        cands.append({**w, "semantic_margin_raw": round(m, 6), "scout_quality": round(q, 6), "scout_eventness": round(ev, 6),
                      "scout_novelty": round(nv, 6), "scout_priority": round(.55 * nv + .45 * sc, 6)})
    if not cands:
        return {"hook": HOOK, "theme": theme or "", "ranked": []}
    sem = _robust01(v7, [c["semantic_margin_raw"] for c in cands])
    scout_n = _robust01(v7, [c["scout_priority"] for c in cands])
    for c, s, p in zip(cands, sem, scout_n):
        c["semantic_score_0_1"] = round(float(s), 6)
        c["semantic_scout_score"] = round(.68 * float(s) + .32 * float(p), 6)
    cands.sort(key=lambda x: x["semantic_scout_score"], reverse=True)
    # the dense check (decodes the window) for the best three; with a theme only windows that match it - a video
    # with no matching moment needs no decoding (a new theme over many videos was minutes of it)
    dense = [c for c in cands if not theme or c["semantic_margin_raw"] > 0][:3]
    for c in dense:
        c.update(v7.dense_window_quality(path, c["start_s"], c["end_s"], ffmpeg))
        c["final_score"] = round(.70 * c["semantic_scout_score"] + .30 * c["dense_score"], 6)
    for c in cands:
        if "final_score" not in c:
            c["final_score"] = round(.70 * c["semantic_scout_score"], 6)
    cands.sort(key=lambda x: x["final_score"], reverse=True)
    return {"hook": HOOK, "theme": theme or "", "video": str(path), "duration_s": duration,
            "rank_elapsed_s": round(time.perf_counter() - started, 3), "mode": "SELECT_BEST", "selection_claim": True,
            "frames_matching_theme": int((np.asarray(margins) > 0).sum()) if theme else None,
            "semantic_model_identity": getattr(scorer, "identity", None), "ranked": cands}

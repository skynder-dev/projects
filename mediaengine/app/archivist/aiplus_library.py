"""Library search by theme with the AI+ model (PE-Core L/14), on this PC.

Each video in the Library is indexed once: the AI+ model looks at its preview frames (the same 8 storyboard frames
the Library shows) and keeps one embedding per frame. A search for a theme ("sea", "children", ...) then compares
those embeddings with the theme's descriptions - plain arithmetic, no model run, instant. Private, rejected and
excluded videos are never indexed or shown. Nothing leaves the PC.
"""
from __future__ import annotations

import json, threading, time
from pathlib import Path

import numpy as np

from .db import db, now_iso

_STATE = {"state": "idle", "done": 0, "total": 0, "error": "", "file": "", "waiting": False}
_LOCK = threading.Lock()
_STOP = threading.Event()
_TEXT: dict = {}           # model key -> {theme: (pos emb, neg emb)}


def ensure_schema() -> None:
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS aiplus_frames(
            inventory_id INTEGER PRIMARY KEY, model_key TEXT NOT NULL, times TEXT NOT NULL, emb BLOB NOT NULL,
            source_fingerprint TEXT, indexed_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS aiplus_texts(
            model_key TEXT NOT NULL, theme TEXT NOT NULL, pos BLOB NOT NULL, neg BLOB NOT NULL, PRIMARY KEY(model_key, theme))""")
        con.commit()


def _ae():
    from . import auto_edit as ae
    return ae


def model_key() -> str:
    return _ae().aiplus_identity()


_VISIBLE = ("media_type='video' AND work_selected=1 AND excluded=0 AND COALESCE(analysis_status,'')<>'private' "
            "AND private_path IS NULL AND rejected_path IS NULL")
_VISIBLE_I = ("i.media_type='video' AND i.work_selected=1 AND i.excluded=0 AND COALESCE(i.analysis_status,'')<>'private' "
              "AND i.private_path IS NULL AND i.rejected_path IS NULL")


def _videos():
    with db() as con:
        return [dict(r) for r in con.execute(f"SELECT id,filename,source_fingerprint FROM inventory WHERE {_VISIBLE} ORDER BY id").fetchall()]


def status() -> dict:
    ensure_schema()
    ae = _ae()
    ready = ae.aiplus_status()["ready"]
    vids = _videos()
    indexed = 0
    if ready and vids:
        key = model_key()
        with db() as con:
            done = {int(r["inventory_id"]): r["source_fingerprint"] for r in
                    con.execute("SELECT inventory_id,source_fingerprint FROM aiplus_frames WHERE model_key=?", (key,)).fetchall()}
        indexed = sum(1 for v in vids if v["id"] in done and (done[v["id"]] or "") == (v["source_fingerprint"] or ""))
    return {"model_ready": ready, "videos": len(vids), "indexed": indexed,
            **{k: _STATE[k] for k in ("state", "done", "total", "error", "file", "waiting")}}


def running() -> bool:
    return _STATE["state"] == "running"


def start() -> bool:
    ae = _ae()
    if not ae.aiplus_status()["ready"]:
        raise ValueError("The AI+ model is not on this computer yet. Download it once on 'Check this PC'.")
    with _LOCK:
        if _STATE["state"] == "running":
            return False
        _STATE.update(state="running", done=0, total=0, error="", file="", waiting=False)
    _STOP.clear()
    threading.Thread(target=_run, name="aiplus-library-index", daemon=True).start()
    return True


def stop() -> None:
    _STOP.set()


def _engine_path() -> None:
    import sys
    ae = _ae()
    if str(ae.ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ae.ENGINE_DIR))


def _scorer():
    _engine_path()
    import p13_pe_core_adapter as pa
    return pa.PECoreScorer(_ae().aiplus_dir(), full_check=False)


LOAD_FAILED = "The AI+ model could not be started (not enough memory?). Close other programs and try again."


def _load():
    try:
        return _scorer()
    except Exception as exc:
        raise RuntimeError(LOAD_FAILED) from exc


def _theme_texts(sc, key: str) -> None:
    """Text embeddings of every theme (and the bad descriptions), kept in the database: searches need no model."""
    _engine_path()
    import p13_event_semantic_pe as hook
    with db() as con:
        have = {r["theme"] for r in con.execute("SELECT theme FROM aiplus_texts WHERE model_key=?", (key,)).fetchall()}
    neg = None
    for theme, (_name, prompts) in hook.THEMES.items():
        if theme in have:
            continue
        neg = sc.encode_text(list(hook.NEGATIVE_PROMPTS)) if neg is None else neg
        pos = sc.encode_text(list(prompts))
        with db() as con:
            con.execute("INSERT OR REPLACE INTO aiplus_texts(model_key,theme,pos,neg) VALUES(?,?,?,?)",
                        (key, theme, pos.astype(np.float32).tobytes(), neg.astype(np.float32).tobytes()))
            con.commit()


def _reel_building() -> bool:
    try:
        with db() as con:
            return con.execute("SELECT 1 FROM ae_jobs WHERE status='running' LIMIT 1").fetchone() is not None
    except Exception:
        return False


def _run() -> None:
    from PIL import Image
    from . import service
    ensure_schema()
    sc = None
    try:
        key = model_key()
        vids = _videos()
        with db() as con:
            done = {int(r["inventory_id"]): r["source_fingerprint"] for r in
                    con.execute("SELECT inventory_id,source_fingerprint FROM aiplus_frames WHERE model_key=?", (key,)).fetchall()}
        todo = [v for v in vids if not (v["id"] in done and (done[v["id"]] or "") == (v["source_fingerprint"] or ""))]
        _STATE.update(total=len(todo), done=0)
        sc = _load()
        _STATE.update(file="")
        _theme_texts(sc, key)
        for i, v in enumerate(todo):
            if _STOP.is_set():
                raise RuntimeError("Stopped.")
            if _reel_building():
                # a reel is being built: it gets the computer (and its memory) first; the search waits
                sc = None
                _STATE.update(done=i, file="", waiting=True)
                while _reel_building() and not _STOP.is_set():
                    time.sleep(2)
                _STATE.update(waiting=False)
                if _STOP.is_set():
                    raise RuntimeError("Stopped.")
            if sc is None:
                sc = _load()
            _STATE.update(done=i, file=v["filename"])
            try:
                info = service.cached_storyboard(v["id"]) or service.ensure_storyboard(v["id"])
            except Exception:
                info = None
            frames = (info or {}).get("frames") or []
            if not frames:
                continue                      # no preview frames (file unavailable): tried again next time
            images, times = [], []                  # times: [preview frame number, second] of every frame looked at
            for k, fr in enumerate(frames):
                try:
                    with Image.open(fr["path"]) as im:
                        images.append(im.convert("RGB"))
                    times.append([k, float(fr["time"])])
                except Exception:
                    continue
            if not images:
                continue
            emb = sc.encode_images(images).astype(np.float16)
            with db() as con:
                con.execute("INSERT OR REPLACE INTO aiplus_frames(inventory_id,model_key,times,emb,source_fingerprint,indexed_at) VALUES(?,?,?,?,?,?)",
                            (v["id"], key, json.dumps(times), emb.tobytes(), v["source_fingerprint"], now_iso()))
                con.commit()
        _STATE.update(state="done", done=len(todo), file="")
    except Exception as exc:
        msg = str(exc)
        _STATE.update(state="stopped" if msg == "Stopped." else "failed", error="" if msg == "Stopped." else msg[:300], file="")
    finally:
        del sc


def search(theme: str, limit: int = 60) -> list[dict]:
    """Library videos that match a theme, best first: [{inventory_id, filename, best_s, frame, score}] (score > 0 = matches;
    frame = the number of the preview frame of the best moment)."""
    _engine_path()
    import p13_event_semantic_pe as hook
    if theme not in hook.THEMES:
        raise ValueError("Unknown theme")
    ensure_schema()
    key = model_key()
    with db() as con:
        t = con.execute("SELECT pos,neg FROM aiplus_texts WHERE model_key=? AND theme=?", (key, theme)).fetchone()
        rows = con.execute(f"SELECT f.inventory_id,f.times,f.emb,i.filename FROM aiplus_frames f JOIN inventory i ON i.id=f.inventory_id "
                           f"WHERE f.model_key=? AND {_VISIBLE_I}", (key,)).fetchall()
    if not t or not rows:
        return []
    pos = np.frombuffer(t["pos"], np.float32).reshape(-1, 1024)
    neg = np.frombuffer(t["neg"], np.float32).reshape(-1, 1024)
    out = []
    for r in rows:
        emb = np.frombuffer(r["emb"], np.float16).astype(np.float32).reshape(-1, 1024)
        times = json.loads(r["times"])
        lp, ln = 100.0 * emb @ pos.T, 100.0 * emb @ neg.T
        k = min(2, lp.shape[1])
        margin = np.sort(lp, axis=1)[:, -k:].mean(axis=1) - ln.max(axis=1)
        i = int(np.argmax(margin))
        at = times[i] if i < len(times) else [i, 0.0]
        frame, best = (int(at[0]), float(at[1])) if isinstance(at, list) else (i, float(at))
        out.append({"inventory_id": int(r["inventory_id"]), "filename": r["filename"], "best_s": best, "frame": frame,
                    "score": round(float(margin[i]), 3)})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[: max(1, int(limit))]

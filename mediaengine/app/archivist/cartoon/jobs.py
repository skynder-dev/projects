"""Cartoon films as jobs of the program's queue (the voice-over queue: one heavy thing at a time, made again after a
restart, Stop / Try again / Delete like a voice-over): the voices (the voice add-on), then the pictures and the MP4,
checked, saved as "<title>.mp4" in a "Cartoons" folder next to the saved reels.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .. import voice as vo
from . import film as F

CAPTION_STYLES = ("pop", "box", "classic", "minimal", "single", "block")


def new_make(script: dict, voices: bool = True, captions: dict | None = None, title: str = "") -> str:
    """A film to make (a job). voices: the characters speak (the voice add-on needed); otherwise a quick preview
    whose line lengths are estimated (silent, captions only)."""
    film = F.check_script(script)                         # (a bad script is refused at once, not in the queue)
    if voices and not vo.installed():
        raise vo.VoiceError("The voices need the voice add-on: install it on the Voice-over page, or make a preview without voices.")
    cap = None
    if captions is not None:
        cap = {"style": captions.get("style") if captions.get("style") in CAPTION_STYLES else "pop",
               "color": captions.get("color") or "yellow", "size": captions.get("size") or "medium",
               "position": captions.get("position") or ("middle" if film["format"] == "vertical" else "bottom")}
    return vo._submit({"kind": "cartoon_make", "script": script, "voices": bool(voices), "captions": cap,
                       "title": (title or film["title"])[:60], "format": film["format"], "needs_addon": bool(voices)},
                      addon=bool(voices))


def do(jid: str, d: Path, job: dict) -> dict:
    """voice._do for the cartoon jobs (in the queue's thread)."""
    from .. import auto_edit as ae, orders as od
    film = F.check_script(job["script"])
    stop = lambda: bool(vo._CURRENT.get("cancel"))      # noqa: E731
    voices = None
    try:
        if job.get("voices"):
            from . import voices as V
            vo._CURRENT.update(step="voices", progress=0.02)
            voices = V.make(film, d / "voices", lambda x: vo._CURRENT.update(step="voices", progress=round(0.02 + 0.6 * x, 3)),
                            stop)
        vo._CURRENT.update(step="drawing", progress=0.63 if voices else 0.02)
        base = 0.63 if voices else 0.02
        tmp = d / "film.new.mp4"
        r = F.render(job["script"], tmp, d / "render", voices, job.get("captions"),
                     lambda x: vo._CURRENT.update(step="drawing", progress=round(base + (0.97 - base) * x, 3)), stop)
    except F.FilmError as exc:
        return {"ok": False, "error": str(exc)}
    vo._CURRENT.update(step="checking", progress=0.98)
    checks = od._check_output(tmp, {"seconds": r["seconds"], "tolerance": 0.6, "audio": True})
    if not all(x["pass"] for x in checks):
        bad = next(x for x in checks if not x["pass"])
        return {"ok": False, "error": f"The film did not pass its check ({bad['check']}: {bad['detail']}).", "checks": checks}
    ae._replace_retry(tmp, d / "film.mp4", tries=30)
    saved = _save(d / "film.mp4", job.get("title") or film["title"])
    if not (vo.load_config().get("voice") or {}).get("keep_work"):
        shutil.rmtree(d / "render", ignore_errors=True)
    return {"ok": True, "file": "film.mp4", "seconds": r["seconds"], "scenes": r["scenes"], "lines": r["lines"],
            "width": r["width"], "height": r["height"], "voices": bool(voices), "saved": saved, "checks": checks}


def folder() -> Path | None:
    from .. import auto_edit as ae
    try:
        f = ae.default_export_dir() / ("Мультфильмы" if ae._ui_ru() else "Cartoons")
        f.mkdir(parents=True, exist_ok=True)
        return f
    except Exception:
        return None


def _save(made: Path, title: str) -> str:
    from .. import auto_edit as ae
    f = folder()
    if f is None:
        return ""
    base = ae.safe_filename(title[:80], "Cartoon")
    dst = f / f"{base}.mp4"
    k = 2
    while dst.exists():
        dst = f / f"{base} ({k}).mp4"
        k += 1
    try:
        try:
            os.link(made, dst)
        except OSError:
            shutil.copy2(made, dst)
        return str(dst)
    except Exception:
        return ""


def films(limit: int = 200) -> list[dict]:
    return [j for j in vo.list_jobs(limit) if str(j.get("kind") or "").startswith("cartoon_")]


def script_of(jid: str) -> dict:
    try:
        return json.loads((vo._job_dir(jid) / "job.json").read_text("utf-8")).get("script") or {}
    except Exception:
        return {}

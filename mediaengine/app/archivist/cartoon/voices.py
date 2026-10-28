"""The voices of a cartoon, made by the voice add-on: every character says all its lines in one go (one voice for the
whole film); a character given by a description gets its voice made once and kept with the character (the same voice
in the next episode). Each line becomes its own WAV with its words' times.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from .. import voice as vo
from ..platform_adapter import process_kwargs
from .film import SR, FilmError


def library() -> Path:
    from ..config import HOME
    return HOME / "cartoon" / "voices"


def _kept(key: str, desc: str) -> dict | None:
    """A character's voice made before (the same description): its recording and words."""
    d = library() / _safe(key)
    try:
        meta = json.loads((d / "voice.json").read_text("utf-8"))
    except Exception:
        return None
    if meta.get("description") == desc and (d / "voice.wav").is_file():
        return {"ref_wav": str(d / "voice.wav"), "ref_text": meta.get("text") or ""}
    return None


def _keep(key: str, desc: str, wav: Path, text: str) -> None:
    d = library() / _safe(key)
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wav, d / "voice.wav")
    (d / "voice.json").write_text(json.dumps({"description": desc, "text": text}, ensure_ascii=False), "utf-8")


def _safe(key: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(key).lower())[:40] or "voice"


def _voice_for(c: dict, key: str) -> tuple[dict, str]:
    """The voice of a character for the worker, and a description to keep it by ("" for the program's own voice)."""
    v = c.get("voice") or {}
    if v.get("kind") == "describe" and str(v.get("text") or "").strip():
        desc = re.sub(r"[()\r\n]+", " ", str(v["text"])).strip()[:400]
        kept = _kept(key, desc)
        return (kept or {"description": desc}), desc
    pv = vo.VOICES.get(v.get("key") or vo.DEFAULT_VOICE) or vo.VOICES[vo.DEFAULT_VOICE]
    out = {"key": v.get("key") or vo.DEFAULT_VOICE, "ref_wav": str(vo.ASSETS / pv["ref"])}
    if pv.get("ref_text"):
        out["ref_text"] = pv["ref_text"]
    if pv.get("cfg"):
        out["cfg"] = float(pv["cfg"])
    return out, ""


def _wav(p: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(p), "rb") as w:
        n, chn, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        a = np.frombuffer(raw, np.int32).astype(np.float32) / 2147483648.0
    else:
        a = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128.0
    if chn > 1:
        a = a.reshape(-1, chn).mean(axis=1)
    return a, sr


def _to48k(src: Path, dst: Path) -> float:
    """A line's WAV as 48 kHz mono 16-bit, evened out (FFmpeg); returns its seconds."""
    cp = subprocess.run([vo._ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(src),
                         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
                        **process_kwargs(dict(capture_output=True, timeout=300)))
    if cp.returncode != 0 or not dst.is_file():
        raise FilmError("A line of the voices could not be finished.")
    a, sr = _wav(dst)
    return len(a) / float(sr)


_EN_MONEY = {"$": "dollars", "€": "euros", "£": "pounds"}
_EN_BIG = {"k": "thousand", "m": "million", "mn": "million", "mln": "million", "b": "billion", "bn": "billion"}


def _ru_plural(n: float, one: str, few: str, many: str, frac: str) -> str:
    if n != int(n):
        return frac
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def spoken(text: str, lang: str = "en") -> str:
    """Money written short said in full: "$4.8M" -> "4.8 million dollars", "$300" -> "300 dollars", "480 млн ₽" ->
    "480 миллионов рублей" (the numbers themselves the voice says well; the signs and short words it may not)."""
    t = str(text or "")
    if lang == "en":
        def en(m):
            sign, num, big = m.group(1), m.group(2), (m.group(3) or "").lower()
            return f"{num}{' ' + _EN_BIG[big] if big else ''} {_EN_MONEY[sign]}"
        t = re.sub(r"([$€£])\s?(\d[\d,]*(?:\.\d+)?)\s?(k|mn|mln|m|bn|b)?\b", en, t, flags=re.I)
        t = re.sub(r"(\d)\s?%", r"\1 percent", t)
    elif lang == "ru":
        big_w = {"тыс": ("тысяча", "тысячи", "тысяч", "тысячи"), "млн": ("миллион", "миллиона", "миллионов", "миллиона"),
                 "млрд": ("миллиард", "миллиарда", "миллиардов", "миллиарда")}
        money_w = {"₽": ("рубль", "рубля", "рублей", "рубля"), "$": ("доллар", "доллара", "долларов", "доллара"),
                   "€": ("евро",) * 4}

        def num(s_):
            try:
                return float(s_.replace(" ", "").replace(",", "."))
            except ValueError:
                return 0.0

        def ru(m):
            n_s, big, cur = m.group(1).strip(), (m.group(2) or "").lower().rstrip("."), m.group(3) or ""
            n = num(n_s)
            out = n_s + (" " + _ru_plural(n, *big_w[big]) if big in big_w else "")
            return out + " " + (money_w[cur][2] if big in big_w and cur != "€" else _ru_plural(n, *money_w[cur]))
        t = re.sub(r"(\d+(?:[  ]\d{3})*(?:[.,]\d+)?)\s?(тыс\.?|млн\.?|млрд\.?)?\s?([₽$€])", ru, t)
        t = re.sub(r"([$€])\s?(\d+(?:[  ]\d{3})*(?:[.,]\d+)?)(?:\s?(тыс\.?|млн\.?|млрд\.?))?",
                   lambda m: ru(type("M", (), {"group": lambda self, k: {1: m.group(2), 2: m.group(3), 3: m.group(1)}[k]})()), t)

        def big(m):
            n_s, w, dot, nxt = m.group(1).strip(), m.group(2), m.group(3) or "", m.group(4) or ""
            keep = dot if dot and not re.match(r"\s+[а-яё]", nxt) else ""
            return f"{n_s} {_ru_plural(num(n_s), *big_w[w])}{keep}{nxt}"
        t = re.sub(r"(\d+(?:[  ]\d{3})*(?:[.,]\d+)?)\s?(млрд|млн|тыс)(\.)?(?![а-яё])(\s*[а-яёА-ЯЁ]?)", big, t)
        t = re.sub(r"(\d)\s?%", r"\1 процентов", t)
    return t


def make(film: dict, work: Path, progress=None, stop=None) -> dict:
    """All the lines said: {"<scene>.<line>": {"wav", "seconds", "words"}} (word times from the line's start)."""
    if not vo.installed():
        raise FilmError("The voices need the voice add-on (Auto Edit → Voice-over → Install).")
    lang = str(film.get("language") or "en")[:2]
    from ..config import load_config
    cfg = load_config().get("voice") or {}
    device = cfg.get("device") or ("cuda" if vo.manifest().get("cuda") else "cpu")
    groups: dict = {}
    for i, s in enumerate(film["scenes"]):
        for j, ln in enumerate(s["lines"]):
            groups.setdefault(ln["who"], []).append((i, j, ln["text"]))
    out: dict = {}
    done, total = 0, max(1, sum(len(g) for g in groups.values()))
    for key, items in groups.items():
        if stop is not None and stop():
            raise FilmError("Stopped.")
        v, desc = _voice_for(film["cast"][key], key)
        engine = ("qwen" if v.get("ref_wav") and lang in vo.QWEN_LANGS and vo.qwen_installed() else "voxcpm")
        d = work / f"voice_{_safe(key)}"
        shutil.rmtree(d, ignore_errors=True)
        chunks = [{"text": spoken(t.replace("*", ""), lang), "pause_after": 0.3} for _, _, t in items]
        all_text = " ".join(c["text"] for c in chunks)

        def line(msg, base=done, n=len(items)):
            if progress is not None and msg.get("chunk"):
                progress((base + min(n, int(msg["chunk"]) - 1)) / total)
        res = vo._run_worker({"task": "tts", "chunks": chunks, "voice": v, "language": lang,
                              "out_wav": str(d / "all.wav"), "seed": int(cfg.get("seed") or 1), "steps": cfg.get("steps"),
                              "device": device, "cfg": v.get("cfg") or cfg.get("cfg"), "engine": engine,
                              "qwen_language": vo.QWEN_LANGS.get(lang),
                              "qwen_icl": vo.qwen_icl(all_text, v.get("ref_text") or "")}, d / "work", timeout=6 * 3600,
                             on_line=line)
        if not res.get("ok"):
            raise FilmError(f"The voice of {film['cast'][key].get('name') or key} could not be made: "
                            + str(res.get("error") or "?")[:200])
        rep = res.get("chunks") or []
        if len(rep) != len(items):
            raise FilmError("The voices came back incomplete.")
        if desc and not v.get("ref_wav") and rep:             # keep the new voice with the character
            try:
                _keep(key, desc, d / "work" / rep[0]["file"], chunks[0]["text"])
            except OSError:
                pass
        words = res.get("words") or []
        at = 0.15
        for (i, j, text), r in zip(items, rep):
            src = d / "work" / r["file"]
            dst = work / f"line_{i:02d}_{j:02d}.wav"
            secs = _to48k(src, dst)
            dur = float(r.get("seconds") or secs)
            mine = [dict(w, s=round(max(0.0, float(w["s"]) - at), 3), e=round(max(0.0, float(w["e"]) - at), 3))
                    for w in words if at - 0.1 <= float(w["s"]) < at + dur + 0.15]
            if not mine:                                        # (no words heard back: spread the line's own words)
                from .film import estimate_words
                mine, _ = estimate_words(text, 0.0, max(1.0, len(text.split()) / max(0.5, secs)))
            out[f"{i}.{j}"] = {"wav": str(dst), "seconds": round(secs, 3), "words": mine}
            at += dur + 0.3
            done += 1
            if progress is not None:
                progress(done / total)
        if not cfg.get("keep_work"):
            shutil.rmtree(d / "work", ignore_errors=True)
    return out

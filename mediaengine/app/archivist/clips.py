"""Clips from a long video (clipping): a podcast, a stream or an interview is listened to once; the complete thoughts
of 15-90 s that make good short clips are listed with their words, the likeliest first; the chosen ones become
vertical clips with the face in the frame (two people apart: one above the other), the video's own sound and captions
timed to the words.

The video itself is only read. Listening needs the voice add-on (its Whisper); making the clips does not. The jobs run
in the voice-over queue (voice.py: one at a time, Stop, made again after a restart); their files are in its folder.
"""
from __future__ import annotations

import json, math, os, re, shutil, subprocess, threading, wave
from pathlib import Path

from . import textfx as tf
from . import voice as vo
from .platform_adapter import process_kwargs

LENGTHS = {"short": (15.0, 30.0), "medium": (30.0, 60.0), "long": (45.0, 90.0)}
LENGTH_LABELS = {"short": "15–30 s", "medium": "30–60 s", "long": "45–90 s"}
FORMATS = {"vertical": (1080, 1920), "square": (1080, 1080), "original": None}
FORMAT_LABELS = {"vertical": "Vertical 9:16 (TikTok, Reels, Shorts)", "square": "Square 1:1", "original": "As filmed"}
FRAMINGS = {"face": "Keep the face in the frame", "blur": "Whole picture, blurred edges"}
MAX_CANDIDATES = 40
MAX_CHOSEN = 30
MAX_SOURCE_S = 6 * 3600            # a recording of at most six hours (Whisper on the processor: still within a night)

# words that make an opening or a moment stronger (English and Russian; lower case, without punctuation)
_HOOK = {"secret", "never", "nobody", "nobody's", "everyone", "everybody", "imagine", "truth", "biggest", "best", "worst",
         "mistake", "mistakes", "crazy", "insane", "wrong",
         "секрет", "никогда", "никто", "представь", "представьте", "правда", "самый", "самая", "самое", "лучший", "худший",
         "ошибка", "ошибки", "главное"}
# ... and words that open strongly only as the first word ("Actually", "really" or "this" later on are just talk)
_HOOK_FIRST = {"why", "how", "what", "here's", "listen", "stop", "honestly", "this", "imagine",
               "почему", "как", "зачем", "слушай", "стоп", "честно", "представь"}
_STRONG = {"amazing", "crazy", "insane", "incredible", "never", "always", "best", "worst", "secret", "mistake", "truth",
           "money", "million", "millions", "billion", "love", "hate", "died", "dead", "killed", "shocked", "scared", "huge",
           "impossible", "fired", "rich", "broke", "free", "war", "lie", "lied", "wow", "unbelievable",
           "невероятно", "безумие", "никогда", "всегда", "лучший", "худший", "секрет", "ошибка", "правда", "деньги",
           "миллион", "миллиона", "миллионов", "миллиард", "люблю", "ненавижу", "умер", "шок", "страшно", "огромный",
           "невозможно", "уволили", "богатый", "бесплатно", "война", "врал", "ложь", "вау"}
_BAD_START = {"and", "but", "so", "because", "or", "which", "that", "then", "also", "like", "um", "uh", "yeah", "anyway",
              "и", "но", "а", "потому", "так", "что", "который", "которая", "которые", "также", "ну", "типа", "короче", "ещё"}
_YOU = {"you", "your", "you're", "yourself", "ты", "вы", "тебе", "вам", "тебя", "вас", "твой", "ваш"}
_NUMBER_WORDS = {"hundred", "thousand", "million", "billion", "percent", "сто", "тысяч", "тысячи", "миллион", "процентов",
                 "процента"}
_LAUGH = re.compile(r"(?:\b|^)(?:ha){2,}|laugh|applause|chuckl|(?:х[аи]-?){2,}|смех|смеётся|аплодисмент")
_END = re.compile(r"[.!?…]+[\"'»”)\]]*$")
# talk that is not content: sound checks, greetings, thanks, goodbyes, "subscribe" (a clip of it is no use) - and
# sponsor reads (a clip of an advert is worse than none)
_SMALLTALK = re.compile(
    r"\b(?:how do you hear me|thanks?(?: you)?(?: so much| very much)? for (?:joining|having|watching|listening|tuning in"
    r"|coming on)|welcome (?:back )?to (?:the|our|my|this) (?:show|podcast|channel|stream|episode)|"
    r"that concludes (?:the|this|our|today's) (?:event|show|episode|broadcast|stream|call)|please stand by|"
    r"see you (?:next time|next week|in the next)|(?:like|hit) (?:and|the) subscribe|subscribe to (?:the|my|our) channel|"
    r"smash (?:that|the) like|don't forget to (?:like|subscribe)|follow (?:me|us) on (?:instagram|twitter|tiktok|youtube|twitch|x\b)|"
    r"всем привет|добро пожаловать (?:на|в) (?:канал|стрим|подкаст|выпуск|эфир)|"
    r"спасибо,? что (?:смотрите|посмотрели|были с нами|слушаете|пришли)|подпишись|подпишитесь|подписывайтесь на|"
    r"ставь(?:те)? лайк|(?:нажми|нажмите|жми) (?:на )?колокольчик|до (?:новых|скорых) встреч|до встречи(?=[.!,]|$)|всем пока)")
_AD = re.compile(
    r"\b(?:sponsored by|today'?s sponsor|(?:episode|video|show|stream) is (?:brought to you by|sponsored)|promo code|"
    r"use (?:the )?code \w+ (?:at|for|to)\b|discount code|\d+ ?(?:%|percent) off|free trial|link (?:is )?in the (?:description|bio)|"
    r"dot com slash|промокод|спонсор (?:этого|сегодняшнего|выпуска|видео|канала|подкаста)|ссылка в (?:описании|био))")


class ClipsError(vo.VoiceError):
    pass


def _bare(w: str) -> str:
    return re.sub(r"^[^\w]+|[^\w']+$", "", str(w or "").lower())


def _ends(w: str) -> bool:
    t = str(w or "")
    if not _END.search(t):
        return False
    return t.rstrip(".").lower().strip("\"'»”)(«“") not in vo._ABBR


# ------------------------------------------------------------------------------------------- finding the clips

def sentences(words: list[dict], gap: float = 1.0, longest: float = 20.0) -> list[dict]:
    """The words grouped into sentences: a sentence ends at . ? ! … or at a pause longer than `gap`; a sentence longer
    than `longest` seconds (speech written without stops) is split at its longest pause or comma."""
    groups, cur = [], []
    for w in words:
        if not str(w.get("w") or "").strip():
            continue
        if cur and float(w["s"]) - float(cur[-1]["e"]) > gap:
            groups.append(cur)
            cur = []
        cur.append(w)
        if _ends(w["w"]):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    def split(g):
        if len(g) < 4 or float(g[-1]["e"]) - float(g[0]["s"]) <= longest:
            return [g]
        best, at = -1.0, len(g) // 2
        for i in range(2, len(g) - 1):
            pause = float(g[i]["s"]) - float(g[i - 1]["e"]) + (0.3 if re.search(r"[,;:–—-]$", g[i - 1]["w"]) else 0.0)
            mid = 1.0 - abs(i - len(g) / 2) / len(g)            # (near the middle when pauses are alike)
            if pause + 0.05 * mid > best:
                best, at = pause + 0.05 * mid, i
        return split(g[:at]) + split(g[at:])
    out = []
    for g in groups:
        for part in split(g):
            out.append({"s": float(part[0]["s"]), "e": float(part[-1]["e"]), "words": part,
                        "text": " ".join(str(x["w"]).strip() for x in part), "whole": _ends(part[-1]["w"])})
    return out


def energy_db(wav: Path, step: float = 0.5) -> list[float]:
    """Loudness of a 16-bit mono WAV every `step` seconds (dB below full scale)."""
    import numpy as np
    out: list[float] = []
    try:
        with wave.open(str(wav), "rb") as f:
            rate, width, ch = f.getframerate(), f.getsampwidth(), f.getnchannels()
            if width != 2:
                return []
            n = max(1, int(rate * step))
            while True:
                b = f.readframes(n)
                if not b:
                    break
                a = np.frombuffer(b, dtype="<i2").astype(np.float32)
                if ch > 1:
                    a = a.reshape(-1, ch).mean(axis=1)
                rms = float(np.sqrt(np.mean(a * a))) if a.size else 0.0
                out.append(round(20 * math.log10(rms / 32768.0 + 1e-6), 2))
    except (OSError, wave.Error, EOFError):
        return []
    return out


def _features(sents: list[dict]) -> list[dict]:
    """What the scoring needs of each sentence, counted once (a window's numbers are then sums, never recounted)."""
    out = []
    for st in sents:
        ws = st["words"]
        bare = [_bare(w["w"]) for w in ws]
        tail = st["text"].rstrip("\"'»”) ")
        out.append({
            "n": len(ws), "spoken": sum(max(0.0, float(w["e"]) - float(w["s"])) for w in ws),
            "unsure": sum(1 for w in ws if float(w.get("p", 1) or 1) < 0.4),
            "strong": sum(1 for x in bare if x in _STRONG),
            "number": any(re.search(r"\d", w["w"]) for w in ws) or any(x in _NUMBER_WORDS for x in bare),
            "excl": tail.endswith("!"), "quest": tail.endswith("?"),
            "gap": max((float(y["s"]) - float(x["e"]) for x, y in zip(ws, ws[1:])), default=0.0),
            "bad_start": bool(bare) and bare[0] in _BAD_START, "hook": bool(bare) and (bare[0] in _HOOK_FIRST or any(x in _HOOK for x in bare[:6])),
            "you": [x in _YOU for x in bare],
            "laugh": sum(1 for w in ws if _LAUGH.search(str(w["w"]).lower())),
            "small": len(_SMALLTALK.findall(st["text"].lower())), "ad": len(_AD.findall(st["text"].lower())),
        })
    return out


def find_candidates(words: list[dict], energy: list[float] | None = None, lmin: float = 30.0, lmax: float = 60.0,
                    limit: int = MAX_CANDIDATES, step: float = 0.5, stop=None) -> list[dict]:
    """The clips worth making: windows of whole sentences of lmin..lmax seconds, scored, the best first, never
    overlapping each other by more than a second. Every window is scored from running sums (a six-hour talk in
    seconds). stop(): asked now and then; True ends the search (a Stop pressed)."""
    sents = sentences(words)
    ft = _features(sents)
    energy = list(energy or [])
    speech = sorted(x for x in energy if x > -90)
    med = speech[len(speech) // 2] if speech else 0.0
    ce, cn = [0.0], [0]                                   # running sums of the loudness of speech
    for x in energy:
        ce.append(ce[-1] + (x if x > -90 else 0.0))
        cn.append(cn[-1] + (1 if x > -90 else 0))
    mid = (lmin + lmax) / 2
    found = []
    for i in range(len(sents)):
        if stop is not None and i % 200 == 0 and stop():
            return []
        f0 = ft[i]
        s0 = max(0.0, sents[i]["s"] - 0.15)
        base = 50.0
        why0 = []
        if f0["bad_start"]:
            base -= 12
        if f0["quest"]:
            base += 10
            why0.append("a question at the start")
        if f0["hook"]:
            base += 8
            why0.append("a strong opening")
        if 3 <= f0["n"] <= 14:
            base += 5
        elif f0["n"] > 30:
            base -= 8
        you = list(f0["you"])                            # "you" among the first 40 words of the window
        k = i + 1
        while len(you) < 40 and k < len(sents):
            you += ft[k]["you"]
            k += 1
        if any(you[:40]):
            base += 4
        n = spoken = unsure = strong = excl = laugh = small = ad = 0
        number = False
        gap = 0.0
        for j in range(i, len(sents)):
            fj = ft[j]
            e0 = sents[j]["e"] + 0.3
            if e0 - s0 > lmax:
                break
            n += fj["n"]
            spoken += fj["spoken"]
            unsure += fj["unsure"]
            strong += fj["strong"]
            excl += fj["excl"]
            laugh += fj["laugh"]
            small += fj["small"]
            ad += fj["ad"]
            number = number or fj["number"]
            gap = max(gap, fj["gap"], (sents[j]["s"] - sents[j - 1]["e"]) if j > i else 0.0)
            dur = e0 - s0
            if dur < lmin:
                continue
            score, why = base, list(why0)
            if not sents[i].get("whole", True) and j == i:
                score -= 4
            if number:
                score += 4
                why.append("numbers")
            if strong:
                score += min(12, 3 * strong)
                if strong >= 2:
                    why.append("strong words")
            score += min(6, 3 * excl)
            if laugh:                                    # people laughing (Whisper writes "(laughs)", "haha"): a funny moment
                score += min(12, 6 * laugh)
                why.append("laughter")
            if fj["quest"] and j > i:
                score -= 6                               # (ends on an open question: the answer is cut off)
            score -= min(24, 12 * small) + min(40, 25 * ad)   # (sound checks, hellos, goodbyes; adverts above all)
            if dur > 0 and spoken / dur < 0.55:
                score -= 10
            if gap > 2.0:
                score -= 8
            wps = n / max(1.0, dur)
            if 2.0 <= wps <= 4.2:
                score += 4
            elif wps < 1.4:
                score -= 8
            if n and unsure / n > 0.25:
                score -= 10                              # music, noise or several people at once
            if energy:
                a, b = int(s0 / step), max(int(s0 / step) + 1, int(math.ceil(e0 / step)))
                a, b = min(a, len(energy)), min(b, len(energy))
                cnt = cn[b] - cn[a]
                if cnt:
                    lift = (ce[b] - ce[a]) / cnt - med
                    score += max(-8.0, min(10.0, 2.0 * lift))
                    if lift >= 2.0:
                        why.append("lively")
            score -= 6 * abs(dur - mid) / max(1.0, lmax - lmin)
            found.append((max(0.0, min(100.0, score)), i, j, s0, e0, why))
    found.sort(key=lambda x: (-x[0], x[3]))
    chosen: list[tuple] = []
    for c in found:
        if all(min(c[4], o[4]) - max(c[3], o[3]) <= 1.0 for o in chosen):
            chosen.append(c)
            if len(chosen) >= limit:
                break
    out = []
    for sc, i, j, s0, e0, why in chosen:
        text = " ".join(s["text"] for s in sents[i:j + 1])
        out.append({"id": f"c{int(round(s0 * 1000))}", "s": round(s0, 2), "e": round(e0, 2), "score": int(round(sc)),
                    "first": tf.clean_text(sents[i]["text"], 200), "text": text[:1500], "why": why})
    return out


def words_between(words: list[dict], s: float, e: float) -> list[dict]:
    """The words said in [s, e], their times from s (for the captions of a clip)."""
    return [{"w": w["w"], "s": round(max(0.0, float(w["s"]) - s), 3), "e": round(min(e, float(w["e"])) - s, 3)}
            for w in words if float(w["s"]) >= s - 0.05 and float(w["e"]) <= e + 0.3 and str(w.get("w") or "").strip()]


# --------------------------------------------------------------------------------------------------- the jobs

def _video_info(p: Path) -> dict:
    """Length, picture size (as shown), sound - or a clear error."""
    try:
        info = vo._probe_video(p)
    except Exception as exc:
        raise vo._no_picture(exc)
    streams = info.get("streams", []) if isinstance(info, dict) else []
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not vs:
        raise ClipsError("This file has no picture: choose a video.")
    dur = float((info.get("format") or {}).get("duration") or 0)
    w, h = vo._display_size(vs, info)
    return {"duration": dur, "w": w, "h": h, "sar": vo._sar(vs), "audio": any(s.get("codec_type") == "audio" for s in streams)}


def new_find(source: str, length: str = "medium", language: str = "") -> str:
    """Listen to a long video and list the clips worth making (a job; needs the voice add-on)."""
    vo._need_addon()
    p = Path(str(source or "").strip().strip('"'))
    from . import auto_edit as ae
    try:
        if not p.is_absolute() or not p.is_file():
            raise ClipsError("Choose the long video (its full path).")
        ae._guard_private(p)
        cloud = ae.cloud_only(p)
    except ClipsError:
        raise
    except ValueError:
        raise ClipsError("Private and Rejected videos are not used.")
    except OSError:
        raise ClipsError("Choose the long video (its full path).")
    if cloud:
        raise ClipsError("This video is only in OneDrive (not on this PC): keep it on this PC first.")
    info = _video_info(p)
    if not info["audio"]:
        raise ClipsError("This video has no sound: clips are found by what is said.")
    if info["duration"] > MAX_SOURCE_S:
        raise ClipsError("The video is longer than six hours: cut it into parts first (Convert → Cut…).")
    if info["duration"] and info["duration"] < LENGTHS.get(length, LENGTHS["medium"])[0] + 5:
        raise ClipsError("The video is shorter than one clip: choose a longer video or shorter clips.")
    lang = str(language or "").strip().lower()
    lang = lang if re.fullmatch(r"[a-z]{2}", lang) else ""
    length = length if length in LENGTHS else "medium"
    _remember(length=length)
    return vo._submit({"kind": "clips_find", "source": str(p), "length": length, "language": lang or None,
                       "duration": info["duration"], "title": p.name[:60]})


def new_make(find_jid: str, chosen: list[dict], fmt: str = "vertical", framing: str = "face", captions: bool = True,
             opts: dict | None = None, title: bool = False) -> str:
    """The chosen clips of a listened video, made one after another (a job; no add-on needed)."""
    fj = vo.read_job(find_jid)
    if fj.get("kind") != "clips_find" or not (fj.get("result") or {}).get("ok"):
        raise ClipsError("The clips of this video are not found yet.")
    src = Path(fj["source"])
    if not src.is_file():
        raise ClipsError("The video is not there any more: " + str(src))
    dur = float((fj.get("result") or {}).get("duration") or fj.get("duration") or 0)
    clean = []
    for c in (chosen or [])[: MAX_CHOSEN + 1]:
        try:
            s, e = float(c["s"]), float(c["e"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(s) and math.isfinite(e)):
            continue
        s, e = max(0.0, s), (min(e, dur) if dur > 0 else e)
        if e - s < 3.0:
            raise ClipsError("A clip must be at least 3 seconds long.")
        if e - s > 180.0:
            raise ClipsError("A clip can be at most 3 minutes long.")
        clean.append({"s": round(s, 2), "e": round(e, 2), "first": tf.clean_text(str(c.get("first") or ""), 200),
                      **({"title": tf.clean_text(str(c.get("title") or ""))} if tf.clean_text(str(c.get("title") or "")) else {})})
    if not clean:
        raise ClipsError("Tick the clips to make first.")
    if len(clean) > MAX_CHOSEN:
        raise ClipsError(f"At most {MAX_CHOSEN} clips at once.")
    fmt = fmt if fmt in FORMATS else "vertical"
    framing = framing if framing in FRAMINGS else "face"
    o = tf.options(**(opts or {}))
    _remember(format=fmt, framing=framing, captions=bool(captions), title=bool(title))
    return vo._submit({"kind": "clips_make", "find": find_jid, "source": str(src), "clips": clean, "format": fmt,
                       "framing": framing, "captions": bool(captions), "opts": o, "first_as_title": bool(title),
                       "title": src.name[:60], "needs_addon": False}, addon=False)


def _remember(**kw) -> None:
    try:
        from .config import update_config
        update_config(lambda c: c.setdefault("clips", {}).update(kw))
    except Exception:
        pass


def last_choices() -> dict:
    try:
        from .config import load_config
        c = dict(load_config().get("clips") or {})
    except Exception:
        c = {}
    return {"length": c.get("length") if c.get("length") in LENGTHS else "medium",
            "format": c.get("format") if c.get("format") in FORMATS else "vertical",
            "framing": c.get("framing") if c.get("framing") in FRAMINGS else "face",
            "captions": c.get("captions") is not False, "title": c.get("title") is True}


def sweep_orphans() -> int:
    """Made-clips jobs whose video's job is gone (deleted while they waited): their folders go (the clips saved next to
    the reels stay)."""
    n = 0
    for j in vo.list_jobs(100000):
        if j.get("kind") == "clips_make" and j["state"] not in ("working", "waiting"):
            try:
                if not (vo._job_dir(str(j.get("find") or "")) / "job.json").is_file():
                    vo.delete_job(j["id"])
                    n += 1
            except vo.VoiceError:
                pass
    return n


def candidates(jid: str) -> list[dict]:
    try:
        return list(json.loads((vo._job_dir(jid) / "clips.json").read_text("utf-8")).get("candidates") or [])
    except Exception:
        return []


def thumb(jid: str, cid: str) -> Path | None:
    """A small picture of a found clip (a moment a little after its start), made when the page asks for it."""
    c = next((x for x in candidates(jid) if x.get("id") == cid), None)
    if c is None or not re.fullmatch(r"c\d{1,9}", cid):
        return None
    d = vo._job_dir(jid)
    out = d / "thumbs" / f"{cid}.jpg"
    if out.is_file() and out.stat().st_size > 0:
        return out
    try:
        src = Path(json.loads((d / "job.json").read_text("utf-8"))["source"])
    except Exception:
        return None
    if not src.is_file():
        return None
    out.parent.mkdir(exist_ok=True)
    t = float(c["s"]) + min(2.0, (float(c["e"]) - float(c["s"])) / 3)
    with _THUMB_LOCK:
        if out.is_file() and out.stat().st_size > 0:   # (made meanwhile for another request)
            return out
        tmp = out.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part.jpg")
        vf = _hdr_first(src) + ["scale=w='if(gte(iw,ih),240,-2)':h='if(gte(iw,ih),-2,240)'"]
        try:
            vo._run_child([vo._ffmpeg(), "-v", "error", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                           "-vf", ",".join(vf), "-q:v", "4", str(tmp)], 60)
            if tmp.is_file() and tmp.stat().st_size > 0:
                os.replace(tmp, out)
                return out
        except Exception:
            pass
        finally:
            _unlink(tmp)
    return None


_THUMB_LOCK = threading.Lock()
_HDR: dict = {}


def _hdr_first(src: Path) -> list[str]:
    """An HDR phone video's conversion to normal colours (as the reels and the converter do), asked once per file;
    a camcorder's interlaced picture made whole frames first."""
    try:
        st = src.stat()
        key = (str(src), st.st_size, st.st_mtime_ns)
    except OSError:
        key = (str(src), 0, 0)
    if key not in _HDR:
        from .converter import HDR_TO_SDR, _hdr_kind, _is_interlaced
        hdr = _hdr_kind(vo._ffmpeg(), src)
        _HDR[key] = (["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if _is_interlaced(vo._ffmpeg(), src) else []) + \
                    ([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else [])
    return list(_HDR[key])


def words_of(jid: str) -> list[dict]:
    try:
        return list(json.loads((vo._job_dir(jid) / "words.json").read_text("utf-8")))
    except Exception:
        return []


def do(jid: str, d: Path, job: dict) -> dict:
    """voice._do for the clip jobs (in the voice-over queue's thread)."""
    if job["kind"] == "clips_find":
        return _do_find(d, job)
    return _do_make(d, job)


def _do_find(d: Path, job: dict) -> dict:
    src = Path(job["source"])
    heard = d / "heard.json"
    if heard.is_file():                                   # heard before (Try again): never listened to again
        try:
            h = json.loads(heard.read_text("utf-8"))
            return save_found(d, job, h["words"], h.get("energy") or [], h.get("language") or "")
        except Exception:
            pass
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src)}
    wav = d / "sound16k.wav"
    wjob = {"task": "transcribe", "source": str(src), "wav16": str(wav), "ffmpeg": vo._ffmpeg(),
            "language": job.get("language"), "duration": float(job.get("duration") or 0), "piece_s": PIECE_S}
    res = vo.transcribe(wjob, d / "work", timeout=12 * 3600)  # (on the NVIDIA card when it can)
    energy = energy_db(wav) if wav.is_file() else []
    if not res.get("ok"):
        _unlink(wav)
        return res
    words = [{"w": str(w["w"]), "s": float(w["s"]), "e": float(w["e"]), "p": float(w.get("p") or 0)}
             for w in (res.get("words") or []) if str(w.get("w") or "").strip()]
    if words:                                             # kept before anything else: hours of listening are never lost
        heard.write_text(json.dumps({"words": words, "energy": energy, "language": res.get("language") or ""},
                                    ensure_ascii=False), "utf-8")
    _unlink(wav)
    if not words:
        return {"ok": False, "error": "No speech was found in this video."}
    out = save_found(d, job, words, energy, res.get("language") or "")
    out["device"] = res.get("device") or "cpu"            # (where it was listened to: for support)
    return out


PIECE_S = 1200.0           # Whisper listens to a long video in pieces of about 20 minutes (its memory stays small)


def _unlink(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except OSError:                                       # (Windows: a virus scanner reading it - removed later)
        pass


def save_found(d: Path, job: dict, words: list[dict], energy: list[float], language: str = "") -> dict:
    """The words and the clips found in them, kept with the job (also used by the checks without listening)."""
    if not (d / "heard.json").is_file():
        (d / "heard.json").write_text(json.dumps({"words": words, "energy": energy, "language": language}, ensure_ascii=False),
                                      "utf-8")
    lmin, lmax = LENGTHS.get(job.get("length") or "medium", LENGTHS["medium"])
    found = find_candidates(words, energy, lmin, lmax, stop=lambda: bool(vo._CURRENT.get("cancel")))
    if vo._CURRENT.get("cancel"):
        return {"ok": False, "error": "Stopped."}
    (d / "words.json").write_text(json.dumps(words, ensure_ascii=False), "utf-8")
    (d / "clips.json").write_text(json.dumps({"candidates": found, "length": [lmin, lmax], "length_key": job.get("length")},
                                             ensure_ascii=False), "utf-8")
    if not found:
        return {"ok": False, "error": "No part of the speech makes a clip of this length: choose shorter or longer clips.",
                "heard": True, "duration": float(job.get("duration") or 0)}
    return {"ok": True, "language": language, "candidates": len(found), "words": len(words),
            "duration": float(job.get("duration") or 0)}


def rescore(jid: str, length: str) -> dict:
    """Another length of clips for a video heard already: found again from its words, in a moment (no listening)."""
    if length not in LENGTHS:
        raise ClipsError("Choose the length of a clip.")
    j = vo.read_job(jid)
    d = vo._job_dir(jid)
    if j.get("kind") != "clips_find" or j["state"] in ("working", "waiting") or not (d / "heard.json").is_file():
        raise ClipsError("The clips of this video are not found yet.")
    h = json.loads((d / "heard.json").read_text("utf-8"))
    job = json.loads((d / "job.json").read_text("utf-8"))
    job["length"] = length
    vo._write_job(d, job)
    res = save_found(d, job, h["words"], h.get("energy") or [], h.get("language") or "")
    res["finished_at"] = (j.get("result") or {}).get("finished_at") or ""
    tmp = d / "result.json.tmp"
    tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    os.replace(tmp, d / "result.json")
    _remember(length=length)
    return res


# ------------------------------------------------------------------------------------------ the face in the frame

_FACES: dict = {}


def _cascade(cv2, path: str):
    """One of OpenCV's face finder files, read by Python and given to OpenCV from memory: OpenCV cannot open a path
    with Russian letters on Windows (a program folder named so)."""
    if not os.path.isfile(path):
        return None
    try:
        fs = cv2.FileStorage(Path(path).read_text("utf-8", errors="replace"), cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
        c = cv2.CascadeClassifier()
        if c.read(fs.getFirstTopLevelNode()) and not c.empty():
            return c
    except Exception:
        pass
    try:
        c = cv2.CascadeClassifier(path)
        return None if c.empty() else c
    except Exception:
        return None


FACE_MODEL = Path(__file__).resolve().parent / "assets" / "faces" / "face_detection_yunet_2023mar.onnx"
FACE_SCORE = 0.8                                          # (YuNet's own sureness: below it, the "faces" in busy backgrounds)


class _YuNet:
    """YuNet (OpenCV's FaceDetectorYN, a small face finder made for this): faces looking at the camera or turned,
    small ones (a streamer's camera picture) too; hardly ever a face in a busy background. Looks at a picture about
    640 wide; a close-up too big for it is looked for again in a half-size picture."""
    kind = "yunet"
    width = 640

    def __init__(self, det):
        self.det, self.size = det, None

    def _run(self, img) -> list:
        h, w = img.shape[:2]
        if self.size != (w, h):
            self.det.setInputSize((w, h))
            self.size = (w, h)
        _, faces = self.det.detect(img)
        return [] if faces is None else [(int(f[0]), int(f[1]), int(f[2]), int(f[3])) for f in faces if float(f[14]) >= FACE_SCORE]

    def find(self, bgr) -> list:
        found = self._run(bgr)
        h, w = bgr.shape[:2]
        if not found and min(w, h) >= 240:
            import cv2
            half = cv2.resize(bgr, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
            found = [(2 * x, 2 * y, 2 * fw, 2 * fh) for (x, y, fw, fh) in self._run(half)]
        return [f for f in found if f[2] >= max(12, h // 30)]


class _Finder:
    """OpenCV's older face finder files (Haar cascades) - only where YuNet cannot run: faces looking at the camera;
    with fewer than two of them, also faces turned to a side (people talking to each other) - both sides."""
    kind = "haar"
    width = 960

    def __init__(self, front, side):
        self.front, self.side = front, side

    def find(self, bgr) -> list:
        import cv2
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
        return self.detectMultiScale(g, scaleFactor=1.12, minNeighbors=5, minSize=(max(24, g.shape[0] // 24),) * 2)

    def detectMultiScale(self, img, scaleFactor=1.1, minNeighbors=5, minSize=(0, 0)):
        kw = dict(scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)
        found = [tuple(int(v) for v in r) for r in self.front.detectMultiScale(img, **kw)]
        if self.side is None or len(found) >= 2:          # (two looking at the camera: enough to choose the layout)
            return found
        import numpy as np
        w = img.shape[1]
        side = [tuple(int(v) for v in r) for r in self.side.detectMultiScale(img, **kw)]
        side += [(w - int(x) - int(fw), int(y), int(fw), int(fh))
                 for (x, y, fw, fh) in self.side.detectMultiScale(np.ascontiguousarray(img[:, ::-1]), **kw)]
        for r in side:                                   # (one face seen twice: once)
            if all(abs((r[0] + r[2] / 2) - (q[0] + q[2] / 2)) > 0.5 * max(r[2], q[2]) for q in found):
                found.append(r)
        return found


def _yunet(cv2):
    """YuNet from the program's own file, given to OpenCV from memory (OpenCV cannot open a path with Russian
    letters on Windows); None when this OpenCV cannot run it."""
    path = os.environ.get("MEDENG_FACE_MODEL") or str(FACE_MODEL)
    if not hasattr(cv2, "FaceDetectorYN") or not os.path.isfile(path):
        return None
    import numpy as np
    try:
        buf = np.frombuffer(Path(path).read_bytes(), np.uint8)
        det = cv2.FaceDetectorYN.create("onnx", buf, np.empty(0, np.uint8), (640, 360), FACE_SCORE, 0.3, 50)
    except Exception:
        try:
            det = cv2.FaceDetectorYN.create(path, "", (640, 360), FACE_SCORE, 0.3, 50)
        except Exception:
            return None
    try:                                                  # (it really runs: a blank picture finds nothing)
        f = _YuNet(det)
        f._run(np.zeros((360, 640, 3), np.uint8))
        return f
    except Exception:
        return None


def face_finder():
    """The face finder: YuNet (the program's own file), else OpenCV's own Haar files, else None."""
    if "f" in _FACES:
        return _FACES["f"]
    found = None
    try:
        import cv2
        if os.environ.get("MEDENG_FACE_FINDER") != "haar":
            found = _yunet(cv2)
        if found is None and hasattr(cv2, "CascadeClassifier"):
            base = str(getattr(getattr(cv2, "data", None), "haarcascades", "") or "")
            front = _cascade(cv2, os.environ.get("MEDENG_FACE_CASCADE") or os.path.join(base, "haarcascade_frontalface_default.xml"))
            if front is not None:
                found = _Finder(front, _cascade(cv2, os.path.join(base, "haarcascade_profileface.xml")))
    except Exception:
        found = None
    _FACES["f"] = found
    return found


def plan_shots(src: Path, start: float, dur: float, info: dict, out_aspect: float, framing: str = "face",
               split_ok: bool = True, pre: list[str] | None = None, log: Path | None = None) -> dict:
    """Where the picture of each shot of a clip is cut: one look at the clip (small, 30 pictures a second) finds the
    cuts between shots; faces are looked for three times a second (YuNet, else OpenCV's Haar files). Per shot: the
    crop's middle on the face (going after someone who walks); a group that fits the crop: its middle on the group; two
    people apart (a podcast's wide shot): each face in its own half, one above the other ("split"; only for a tall
    clip); people side by side or three and more: the group as big as it fits, on blurred edges. Shot boundaries lie
    half a frame before the first frame of the new shot (whatever the exact time of the clip's first frame)."""
    W, H = int(info["w"]), int(info["h"])
    cw = min(1.0, (H * out_aspect) / max(1, W))          # the crop's width as a share of the picture's
    plan = {"shots": [], "faces": False, "crop_w": cw}
    if framing == "blur" or cw >= 0.98:
        plan["shots"] = [{"s": 0.0, "e": dur, "layout": "fit" if framing == "blur" else "crop", "cx": 0.5}]
        return plan
    finder = face_finder()
    plan["faces"] = finder is not None
    plan["finder"] = getattr(finder, "kind", "") if finder is not None else ""
    fw = int(getattr(finder, "width", 960) or 960)       # (a streamer's small camera picture still has a face to find)
    fh = max(2, int(round(fw * H / max(1, W) / 2)) * 2)
    step = max(8, fw // 60)                               # (the grid the cuts between shots are looked for on)
    sar = "setsar=1," if abs(float(info.get("sar") or 1) - 1) < 0.01 else "scale=trunc(iw*sar/2)*2:ih,setsar=1,"
    first = ",".join(pre or [])
    cmd = [vo._ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
           "-an", "-vf", f"{first + ',' if first else ''}{sar}fps=30:start_time=0,scale={fw}:{fh},format=bgr24", "-f", "rawvideo", "-"]
    errf = open(log, "ab") if log else subprocess.DEVNULL
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf, stdin=subprocess.DEVNULL, **process_kwargs({}))
    finally:
        if log:
            errf.close()
    from . import auto_edit as ae
    ae._attach_job_object(proc)
    vo._track(proc)
    import numpy as np
    import cv2
    size = fw * fh * 3
    cuts, samples = [0], []
    prev, prev_h, i, last_face = None, None, 0, -100
    try:
        while True:
            b = proc.stdout.read(size)
            if not b or len(b) < size:
                break
            if vo._CURRENT.get("cancel"):
                break
            f = np.frombuffer(b, dtype=np.uint8).reshape(fh, fw, 3)
            small = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[::step, ::step].astype(np.int16)
            hist = np.bincount((small // 16).ravel(), minlength=16) / small.size
            if prev is not None and i - cuts[-1] >= 8 and (float(np.mean(np.abs(small - prev))) > 22.0
                                                           or float(np.abs(hist - prev_h).sum()) > 0.9):
                cuts.append(i)                           # a new shot (the picture or its light changed at once)
                last_face = -100                         # (its faces looked for at once)
            prev, prev_h = small, hist
            if finder is not None and i - last_face >= 10:
                last_face = i
                try:
                    found = finder.find(f)
                except Exception:
                    found = ()
                samples.append((i, _people([(float(x + w / 2) / fw, float(w) / fw, float(y + h / 2) / fh) for (x, y, w, h) in found],
                                           fw, fh)))
            i += 1
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        proc.wait()
        vo._untrack(proc)
    if vo._CURRENT.get("cancel"):
        raise ClipsError("Stopped.")
    if i == 0:                                            # nothing could be read: the middle of the picture
        plan.update(faces=False, read=False, shots=[{"s": 0.0, "e": dur, "layout": "crop", "cx": 0.5}])
        return plan
    edges = cuts + [i]
    shots = []
    for a, b in zip(edges, edges[1:]):
        if b <= a:
            continue
        timed = [(k, fs) for (k, fs) in samples if a <= k < b]
        faces = [fs for (_, fs) in timed]
        mains, pairs, groups, track = [], [], [], []      # (track: where the crop's middle should be, when)
        for k, fs in timed:
            if not fs:
                continue
            big = max(fs, key=lambda t: t[1])
            near = sorted((t for t in fs if t[1] >= 0.6 * big[1]), key=lambda t: t[0])
            main = big
            if len(near) >= 2:                             # (one big face of a close-up counts by itself)
                lo, hi = min(t[0] - t[1] / 2 for t in near), max(t[0] + t[1] / 2 for t in near)
                need = hi - lo + 1.6 * sorted(t[1] for t in near)[len(near) // 2]   # the faces and their shoulders
                if need <= cw:                             # all of them fit the crop: its middle on the group
                    main = ((lo + hi) / 2, big[1], big[2])
                elif len(near) == 2 and need * W / max(1, H) > 1.0:
                    pairs.append((near, ((lo + hi) / 2, need)))   # two people far apart
                else:                                      # people side by side: the group's picture
                    groups.append(((lo + hi) / 2, need))
            mains.append(main)
            track.append((k / 30.0, main[0]))
        seen = [fs for fs in faces if fs]
        med = lambda xs: sorted(xs)[len(xs) // 2]
        counts: dict = {}
        for fs in faces:
            counts[str(min(len(fs), 3))] = counts.get(str(min(len(fs), 3)), 0) + 1
        shot = {"s": 0.0 if a == 0 else round((a - 0.5) / 30.0, 6), "e": round((b - 0.5) / 30.0, 6), "layout": "crop", "cx": 0.5,
                "seen": counts}                          # (how many people each look found: for support)
        if seen and len(pairs) + len(groups) >= max(1, len(seen) / 2):
            if split_ok and pairs and len(pairs) >= len(groups):   # two people apart: each in a half, one above the other
                shot.update(layout="split", faces=[{"cx": round(med([p[0][k][0] for p in pairs]), 4),
                                                    "cy": round(med([p[0][k][2] for p in pairs]), 4),
                                                    "size": round(med([p[0][k][1] for p in pairs]), 4)} for k in (0, 1)])
            else:                                          # people side by side: all of them, as big as they fit,
                boxes = groups + [p[1] for p in pairs]     # on blurred edges (the whole picture when they fill it)
                ws = sorted(min(1.0, max(cw, b_[1] * 1.15)) for b_ in boxes)
                shot.update(layout="fit", box={"cx": round(med([b_[0] for b_ in boxes]), 4),
                                               "w": round(ws[min(len(ws) - 1, int(len(ws) * 0.8))], 4)})
        elif mains and split_ok and _facecam(mains, len(seen)):
            # a streamer's camera in a corner of the game (small, never moving): the camera above, the game below
            shot.update(layout="cam", cam={"cx": round(med([t[0] for t in mains]), 4), "cy": round(med([t[2] for t in mains]), 4),
                                           "size": round(med([t[1] for t in mains]), 4)})
        elif mains:
            shot.update(cx=round(med([t[0] for t in mains]), 4))
            path = _follow(track, cw)
            if path:                                       # (someone walking: the crop goes with them)
                shot.update(path=path)
        shots.append(shot)
    shots[-1]["e"] = max(shots[-1]["e"], dur + 1.0)
    plan["shots"] = shots
    return plan


def _follow(track: list, cw: float) -> list | None:
    """The crop's middle over a shot when its person moves more than a still crop can hold: [[t, x], ...] (x as a
    share of the width), or None. The crop stays put while the face is near its middle and then goes after it -
    smoothly, at most one crop width a second - the way a camera operator pans."""
    if len(track) < 4:
        return None
    xs = sorted(x for _, x in track)
    cut = len(xs) // 10
    if xs[-1 - cut] - xs[cut] <= 0.45 * cw:              # (a still crop keeps the face well inside)
        return None
    jumps = sum(1 for (t0, x0), (t1, x1) in zip(track, track[1:]) if abs(x1 - x0) > 0.5 * cw and t1 - t0 <= 1.0)
    if jumps >= 2:                                         # (two people found in turns, not one who walks: a still crop)
        return None
    sm = []
    for i in range(len(track)):                            # (each look: the middle of the looks around it, about 1.3 s)
        win = sorted(x for _, x in track[max(0, i - 2):i + 3])
        sm.append((track[i][0], win[len(win) // 2]))
    dead, vmax = 0.12 * cw, 1.0 * cw
    cam, prev_t = sm[0][1], sm[0][0]
    path = [[round(prev_t, 3), round(cam, 4)]]
    for t, x in sm[1:]:
        before = cam
        err = x - cam
        if abs(err) > dead:
            step = err - math.copysign(dead, err)
            lim = vmax * max(0.0, t - prev_t)
            cam += max(-lim, min(lim, step))
        if cam != before and path[-1][0] < prev_t - 1e-6:   # (the pan starts at the look before, not at the last point)
            path.append([round(prev_t, 3), round(before, 4)])
        prev_t = t
        if abs(cam - path[-1][1]) >= 0.002 or t - path[-1][0] >= 2.0:
            path.append([round(t, 3), round(cam, 4)])
    if len(path) > 120:                                   # (an expression FFmpeg reads quickly: at most ~120 points)
        k = -(-len(path) // 120)
        path = path[::k] + ([path[-1]] if (len(path) - 1) % k else [])
    return path if max(p[1] for p in path) - min(p[1] for p in path) > 0.02 else None


def _path_expr(path: list, W: int, cw: int) -> str:
    """The crop's left edge over time (straight lines between the points of the path), in pixels: the first place plus
    each stretch's move, done between its two times - a flat sum (a long walk would nest too deep for FFmpeg)."""
    px = [(t, max(0, min(W - cw, int(round(x * W - cw / 2))))) for t, x in path]
    out = [str(px[0][1])]
    for (t0, x0), (t1, x1) in zip(px, px[1:]):
        if x1 == x0:
            continue
        out.append(f"({x1 - x0})*gte(t,{t0:.3f})" if t1 <= t0 else f"({x1 - x0})*clip((t-{t0:.3f})/{t1 - t0:.3f},0,1)")
    return "+".join(out)


def _people(faces: list, fw: int, fh: int) -> list:
    """The faces found in one picture, one per person: a second find close to a bigger one (the same head found twice,
    or a find on the same body) is left out. faces: (centre x, width, centre y), x and width as shares of the width."""
    out = []
    for f in sorted(faces, key=lambda t: -t[1]):
        wpx = f[1] * fw
        if all(abs(f[0] - k[0]) * fw >= 1.5 * k[1] * fw or abs(f[2] - k[2]) * fh >= 2.2 * k[1] * fw for k in out) \
                or wpx <= 0:
            out.append(f)
    return out


def _facecam(mains: list, samples: int) -> bool:
    """One small face that stays where it is near a side of the picture, found in most looks at the shot: the camera
    picture a streamer puts over a game."""
    if len(mains) < 3 or len(mains) < 0.7 * samples:
        return False
    xs, ys, ss = [t[0] for t in mains], [t[2] for t in mains], [t[1] for t in mains]
    mx, my, ms = sum(xs) / len(xs), sum(ys) / len(ys), sorted(ss)[len(ss) // 2]
    still = max(abs(x - mx) for x in xs) < 0.02 and max(abs(y - my) for y in ys) < 0.03
    return still and ms < 0.09 and (abs(mx - 0.5) > 0.25 or abs(my - 0.5) > 0.25)


def _until(shots: list[dict], vals: list) -> str:
    """A value per shot as an FFmpeg expression of the time t: shot k's value from the end of shot k-1 until its own
    end. A flat sum, never nested: FFmpeg reads at most about 100 brackets inside each other (a clip of many shots)."""
    if len(vals) == 1:
        return str(vals[0])
    parts = []
    for k, v in enumerate(vals):
        on = ([f"gte(t,{shots[k - 1]['e']:.6f})"] if k > 0 else []) + ([f"lt(t,{shots[k]['e']:.6f})"] if k < len(vals) - 1 else [])
        parts.append(f"({v})*" + "*".join(on))
    return "+".join(parts)


def _graph(plan: dict, info: dict, out: tuple[int, int] | None) -> tuple[str, int, int]:
    """[0:v] -> [pv]: the picture of the clip in its new shape (the shots' crops; the split and blurred-edges shots
    laid over them at exactly their times)."""
    W, H = int(info["w"]), int(info["h"])
    pre = "setsar=1" if abs(float(info.get("sar") or 1) - 1) < 0.01 else "scale=trunc(iw*sar/2)*2:ih,setsar=1"
    if out is None:                                       # as filmed: at most 1080 on the short side
        k = min(1.0, vo.MAX_SHORT_SIDE / max(1, min(W, H)))
        ow, oh = int(W * k) // 2 * 2, int(H * k) // 2 * 2
        return f"[0:v]{pre},scale={ow}:{oh}:flags=lanczos,setsar=1[pv]", ow, oh
    ow, oh = out
    shots = plan["shots"]
    cw = min(W, int(round(H * ow / oh / 2)) * 2)
    ch = H if cw < W else min(H, int(round(W * oh / ow / 2)) * 2)
    xs = [_path_expr(sh["path"], W, cw) if sh.get("path") else max(0, min(W - cw, int(round(sh["cx"] * W - cw / 2))))
          for sh in shots]
    crop = f"crop=w={cw}:h={ch}:x='{_until(shots, xs)}':y={(H - ch) // 2},scale={ow}:{oh}:flags=lanczos,setsar=1"
    fits = [sh for sh in shots if sh["layout"] == "fit"]
    bw = min(W, int(round(max((sh.get("box") or {}).get("w", 1.0) for sh in fits) * W / 2)) * 2) if fits else W
    box = ""
    if bw < W - 2:                                        # (a group: its part of the picture, full height)
        last, bx = None, []
        for sh in shots:
            b_ = sh.get("box") if sh["layout"] == "fit" else last
            last = b_ or last
            bx.append(max(0, min(W - bw, int(round((b_ or {"cx": 0.5})["cx"] * W - bw / 2)))))
        box = f"crop=w={bw}:h={H}:x='{_until(shots, bx)}':y=0,"
    fit = (f"{box}split=2[bga][fga];[bga]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},gblur=sigma=28,"
           f"eq=brightness=-0.06[bgb];[fga]scale={ow}:{oh}:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[fgb];"
           f"[bgb][fgb]overlay=(W-w)/2:(H-h)/2")
    split = _split_chain(shots, W, H, ow, oh)
    kinds = {"crop": crop, "fit": fit + ",setsar=1", "split": split, "cam": _cam_chain(shots, W, H, ow, oh)}
    used = [k for k in ("crop", "fit", "split", "cam") if any(sh["layout"] == k for sh in shots)]
    if len(used) == 1:
        return f"[0:v]{pre},{kinds[used[0]]}[pv]", ow, oh
    # several layouts: each made for the whole clip, the one of each shot laid over the first - between exactly the
    # same times as the crop's own switches (no frame in between shows a third picture)
    parts = [f"[0:v]{pre},split={len(used)}" + "".join(f"[i{k}]" for k in used)]
    parts += [f"[i{k}]{kinds[k]}[o{k}]" for k in used]
    cur = f"o{used[0]}"
    starts = [0.0] + [sh["e"] for sh in shots[:-1]]
    for k in used[1:]:
        on = "+".join((f"lt(t,{sh['e']:.6f})" if st <= 0 else f"gte(t,{st:.6f})*lt(t,{sh['e']:.6f})")
                      for st, sh in zip(starts, shots) if sh["layout"] == k)
        parts.append(f"[{cur}][o{k}]overlay=0:0:enable='{on}'[m{k}]")
        cur = f"m{k}"
    parts[-1] = parts[-1][: parts[-1].rindex("[")] + "[pv]"
    return ";".join(parts), ow, oh


def _cam_chain(shots: list[dict], W: int, H: int, ow: int, oh: int) -> str:
    """A streamer's camera above (about two fifths of the clip), the middle of the game below."""
    sp = [sh for sh in shots if sh["layout"] == "cam"]
    if not sp:
        return "null"
    th = int(oh * 0.42) // 2 * 2
    bh = oh - th
    sizes = sorted(sh["cam"]["size"] * W for sh in sp)
    ch = int(max(0.18 * H, min(H, 2.8 * sizes[len(sizes) // 2])))       # (about the camera picture itself)
    cw = int(min(W, ch * ow / th)) // 2 * 2
    ch = int(cw * th / ow) // 2 * 2
    last = sp[0]["cam"]
    xs, ys = [], []
    for sh in shots:
        fc = sh["cam"] if sh["layout"] == "cam" else last
        last = fc
        xs.append(max(0, min(W - cw, int(round(fc["cx"] * W - cw / 2)))))
        ys.append(max(0, min(H - ch, int(round(fc["cy"] * H - 0.45 * ch)))))
    gw = int(min(W, H * ow / bh)) // 2 * 2
    gh = int(min(H, gw * bh / ow)) // 2 * 2
    top = f"crop=w={cw}:h={ch}:x='{_until(shots, xs)}':y='{_until(shots, ys)}',scale={ow}:{th}:flags=lanczos,setsar=1"
    game = f"crop=w={gw}:h={gh}:x={(W - gw) // 2}:y={(H - gh) // 2},scale={ow}:{bh}:flags=lanczos,setsar=1"
    return f"split=2[ca1][cb1];[ca1]{top}[cta];[cb1]{game}[ctb];[cta][ctb]vstack=2,setsar=1"


def _split_chain(shots: list[dict], W: int, H: int, ow: int, oh: int) -> str:
    """Two faces one above the other: each half of the clip a crop around one face (the left one on top), the same
    size for the whole clip, placed per shot (shots without two faces keep the last place - they are not shown)."""
    sp = [sh for sh in shots if sh["layout"] == "split"]
    if not sp:
        return "null"
    ph = oh // 2 // 2 * 2
    aspect = ow / ph
    out = []
    for k in (0, 1):
        sizes = sorted(sh["faces"][k]["size"] * W for sh in sp)
        ch = int(max(0.42 * H, min(H, 3.4 * sizes[len(sizes) // 2])))
        cw = int(min(W, ch * aspect)) // 2 * 2
        ch = int(cw / aspect) // 2 * 2
        last = sp[0]["faces"][k]
        xs, ys = [], []
        for sh in shots:
            fc = sh["faces"][k] if sh["layout"] == "split" else last
            last = fc
            xs.append(max(0, min(W - cw, int(round(fc["cx"] * W - cw / 2)))))
            ys.append(max(0, min(H - ch, int(round(fc["cy"] * H - 0.42 * ch)))))
        out.append(f"crop=w={cw}:h={ch}:x='{_until(shots, xs)}':y='{_until(shots, ys)}',scale={ow}:{ph}:flags=lanczos,setsar=1")
    return f"split=2[sa][sb];[sa]{out[0]}[sta];[sb]{out[1]}[stb];[sta][stb]vstack=2,pad={ow}:{oh}:0:0,setsar=1"


def _made_before(d: Path) -> dict:
    """The clips of this job already made and saved (a job made again after a restart, Stop or Try again goes on
    where it stopped: nothing made twice, no second copy in the folder)."""
    try:
        m = json.loads((d / "made.json").read_text("utf-8"))
        return {int(k): v for k, v in m.items() if (d / v["file"]).is_file()}
    except Exception:
        return {}


def _keep_made(d: Path, made: dict) -> None:
    tmp = d / f"made.json.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps({str(k): v for k, v in made.items()}, ensure_ascii=False), "utf-8")
    os.replace(tmp, d / "made.json")


def _do_make(d: Path, job: dict) -> dict:
    src = Path(job["source"])
    clips = list(job.get("clips") or [])
    done = _made_before(d)
    folder = _out_folder(src)
    failed = []
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src), **_listing(done, folder)}
    words = words_of(job["find"])
    info = _video_info(src)
    out = FORMATS.get(job.get("format") or "vertical")
    pre = _hdr_first(src)
    for n, c in enumerate(clips, 1):
        if n in done:
            continue
        if vo._CURRENT.get("cancel"):
            break
        vo._CURRENT.update(step=f"clip {n}/{len(clips)}", progress=round((n - 1) / max(1, len(clips)), 3))
        try:
            done[n] = _make_one(d, job, n, c, src, info, out, pre, words, folder)
            _keep_made(d, done)
        except ClipsError as exc:
            if vo._CURRENT.get("cancel"):
                break
            failed.append({"n": n, "error": str(exc)})    # (the next clips are made all the same)
    lst = _listing(done, folder)
    if vo._CURRENT.get("cancel"):
        return {"ok": False, "error": "Stopped.", **lst}
    if failed:
        first = failed[0]["error"]
        return {"ok": False, "error": first, "failed": failed, **lst}
    vo._CURRENT.update(step="checking", progress=1.0)
    return {"ok": True, **lst}


def _listing(done: dict, folder: Path | None) -> dict:
    return {"clips": [dict(done[k], n=k) for k in sorted(done)], "folder": str(folder) if folder else ""}


def _make_one(d: Path, job: dict, n: int, c: dict, src: Path, info: dict, out, pre: list[str], words: list[dict],
              folder: Path | None) -> dict:
    from . import auto_edit as ae, orders as od
    s, e = float(c["s"]), float(c["e"])
    dur = round(e - s, 3)
    plan = plan_shots(src, s, dur, info, (out[0] / out[1]) if out else 1.0, job.get("framing") or "face",
                      split_ok=bool(out and out[1] > out[0]), pre=pre, log=d / "analysis.log") if out else \
        {"shots": [{"s": 0.0, "e": dur, "layout": "crop", "cx": 0.5}], "faces": False}
    graph, ow, oh = _graph(plan, info, out)
    if pre:                                               # camcorder fields / an HDR phone video: first of all
        graph = graph.replace("[0:v]", f"[0:v]{','.join(pre)},", 1)
    o = tf.options(**(job.get("opts") or {}))
    if o["position"] == "bottom" and any(sh["layout"] in ("split", "cam") for sh in plan["shots"]):
        o["position"] = "middle"                         # (two faces one above the other: the captions between them)
    cs = vo.style_cues(words_between(words, s, e), o) if job.get("captions", True) else []
    texts = []
    title = c.get("title") or (c.get("first") if job.get("first_as_title") else "")   # (a clip's own title first)
    if title:
        texts = tf.parse_texts([{"text": title[: tf.TEXT_MAX], "start": "0", "end": "3", "where": "top", "look": "banner"}])
    chain = ["scale=out_range=tv"]
    if cs or texts:
        (d / "captions.ass").write_text(tf.document(ow, oh, cs, tf.resolve_texts(texts, dur), o, 0.0), "utf-8")
        fonts = tf.install_fonts(d)
        fonts = vo._caption_font(d) or fonts
        chain.append("ass=captions.ass" + (":fontsdir=fonts" if fonts else ""))
    chain.append("format=yuv420p")
    fc = graph + f";[pv]{','.join(chain)}[v]"
    if info["audio"]:                                    # (gaps in the recorded sound filled: the sound stays with the picture)
        fc += (f";[0:a:0]aresample=48000:async=1:first_pts=0,aformat=channel_layouts=stereo,afade=t=in:d=0.06,"
               f"afade=t=out:st={max(0.0, dur - 0.15):.3f}:d=0.15,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    cmd = [vo._ffmpeg(), "-hide_banner", "-nostdin", "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
           "-filter_complex", fc, "-map", "[v]"] + (["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if info["audio"] else [])
    hdr = any(x.startswith("zscale") for x in pre)
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if hdr else []
    name = f"clip_{n:02d}.mp4"
    tmp = d / f"clip_{n:02d}.new.mp4"
    _unlink(tmp)
    tries = ([[*tags, "-color_range", "tv", "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0",
               "-profile:v", "high"]] if vo.nvenc_ok() else []) + \
            [[*tags, "-color_range", "tv", "-c:v", "libx264", "-preset", "medium", "-crf", "18"]]
    rc = -1
    for enc in tries:
        rc = vo._run_ffmpeg(cmd + enc + ["-t", f"{dur:.3f}", "-movflags", "+faststart", tmp.name], d, d / "ffmpeg.log", 3 * 3600)
        if rc == 0 and tmp.is_file() and tmp.stat().st_size > 1000:
            break
        _unlink(tmp)
        if vo._CURRENT.get("cancel"):
            break
    shutil.rmtree(d / "fonts", ignore_errors=True)
    if vo._CURRENT.get("cancel"):
        _unlink(tmp)
        raise ClipsError("Stopped.")
    if rc != 0 or not tmp.is_file():
        lines = [x for x in (d / "ffmpeg.log").read_text("utf-8", errors="replace").splitlines() if x.strip()]
        why = next((x for x in reversed(lines) if not re.match(r"\s*(frame=|size=|\$ )", x)), lines[-1] if lines else "?")
        raise ClipsError(f"Clip {n} could not be made (" + why[:200] + ").")
    checks = od._check_output(tmp, {"seconds": dur, "tolerance": 0.3, "audio": info["audio"]})
    if not all(x["pass"] for x in checks):
        bad = next(x for x in checks if not x["pass"])
        ae._replace_retry(tmp, d / f"clip_{n:02d}_failed_check.mp4")
        raise ClipsError(f"Clip {n} did not pass its check ({bad['check']}: {bad['detail']}).")
    ae._replace_retry(tmp, d / name, tries=30)
    saved = _save(d / name, folder, n, c.get("first") or "")
    return {"file": name, "s": s, "e": e, "seconds": dur, "saved": saved, "width": ow, "height": oh,
            "layouts": sorted({sh["layout"] for sh in plan["shots"]}), "shots": len(plan["shots"]),
            "faces": bool(plan.get("faces")), "captions": len(cs), "plan": plan["shots"]}


def _out_folder(src: Path) -> Path | None:
    """Where the clips of a video are saved: '<video> - clips' next to the saved reels."""
    from . import auto_edit as ae
    try:
        base = ae.default_export_dir()
        f = base / ae.safe_filename(f"{src.stem[:60]} - " + ("клипы" if ae._ui_ru() else "clips"), "MediaEngine clips")
        f.mkdir(parents=True, exist_ok=True)
        return f
    except Exception:
        return None


def _save(made: Path, folder: Path | None, n: int, first: str) -> str:
    from . import auto_edit as ae
    if folder is None:
        return ""
    words = " ".join(re.findall(r"[\w'’-]+", first)[:7])
    base = ae.safe_filename(f"{n:02d} - {words}" if words else f"{n:02d}", f"{n:02d}")
    dst = folder / f"{base}.mp4"
    k = 2
    while dst.exists():
        dst = folder / f"{base} ({k}).mp4"
        k += 1
    try:
        try:
            os.link(made, dst)                            # the same disk: one file with two names
        except OSError:
            shutil.copy2(made, dst)
        return str(dst)
    except Exception:
        return ""


_LOCK = threading.Lock()

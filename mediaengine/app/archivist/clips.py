"""Clips from a long video (clipping): a podcast, a stream or an interview is listened to once; the complete thoughts
of 15-90 s that make good short clips are listed with their words, the likeliest first; the chosen ones become
vertical clips with the face in the frame, the video's own sound and captions timed to the words.

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
_HOOK = {"why", "how", "what", "secret", "never", "nobody", "everyone", "everybody", "imagine", "stop", "truth", "biggest",
         "best", "worst", "mistake", "mistakes", "nobody's", "here's", "this", "listen", "honestly", "actually", "crazy",
         "insane", "wrong", "real", "really", "most", "only", "first", "last",
         "почему", "как", "что", "секрет", "никогда", "никто", "все", "всё", "представь", "представьте", "стоп", "правда",
         "самый", "самая", "самое", "лучший", "худший", "ошибка", "ошибки", "слушай", "честно", "реально", "главное",
         "только", "вот"}
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
_END = re.compile(r"[.!?…]+[\"'»”)\]]*$")


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


def _score(sents: list[dict], s0: float, e0: float, lmin: float, lmax: float, energy: list[float], med: float,
           step: float) -> tuple[float, list[str]]:
    words = [w for s in sents for w in s["words"]]
    first = sents[0]
    fw = [_bare(w["w"]) for w in first["words"]]
    allw = [_bare(w["w"]) for w in words]
    dur = e0 - s0
    score, why = 50.0, []
    if fw and fw[0] in _BAD_START:
        score -= 12
    if first["text"].rstrip("\"'»”) ").endswith("?"):
        score += 10
        why.append("a question at the start")
    if any(x in _HOOK for x in fw[:6]):
        score += 8
        why.append("a strong opening")
    if 3 <= len(fw) <= 14:
        score += 5
    elif len(fw) > 30:
        score -= 8
    if not first.get("whole", True) and len(sents) == 1:
        score -= 4
    if any(x in _YOU for x in allw[:40]):
        score += 4
    if any(re.search(r"\d", w["w"]) for w in words) or any(x in _NUMBER_WORDS for x in allw):
        score += 4
        why.append("numbers")
    strong = sum(1 for x in allw if x in _STRONG)
    if strong:
        score += min(12, 3 * strong)
        if strong >= 2:
            why.append("strong words")
    score += min(6, 3 * sum(1 for s in sents if s["text"].rstrip("\"'»”) ").endswith("!")))
    if sents[-1]["text"].rstrip("\"'»”) ").endswith("?") and len(sents) > 1:
        score -= 6                                       # (ends on an open question: the answer is cut off)
    spoken = sum(max(0.0, float(w["e"]) - float(w["s"])) for w in words)
    gaps = [float(b["s"]) - float(a["e"]) for a, b in zip(words, words[1:])]
    if dur > 0 and spoken / dur < 0.55:
        score -= 10
    if gaps and max(gaps) > 2.0:
        score -= 8
    wps = len(words) / max(1.0, dur)
    if 2.0 <= wps <= 4.2:
        score += 4
    elif wps < 1.4:
        score -= 8
    unsure = sum(1 for w in words if float(w.get("p", 1) or 1) < 0.4)
    if words and unsure / len(words) > 0.25:
        score -= 10                                      # music, noise or several people at once
    if energy:
        a, b = int(s0 / step), max(int(s0 / step) + 1, int(math.ceil(e0 / step)))
        part = [x for x in energy[a:b] if x > -90]
        if part:
            lift = sum(part) / len(part) - med
            score += max(-8.0, min(10.0, 2.0 * lift))
            if lift >= 2.0:
                why.append("lively")
    mid = (lmin + lmax) / 2
    score -= 6 * abs(dur - mid) / max(1.0, lmax - lmin)
    return max(0.0, min(100.0, score)), why


def find_candidates(words: list[dict], energy: list[float] | None = None, lmin: float = 30.0, lmax: float = 60.0,
                    limit: int = MAX_CANDIDATES, step: float = 0.5) -> list[dict]:
    """The clips worth making: windows of whole sentences of lmin..lmax seconds, scored, the best first, never
    overlapping each other by more than a second."""
    sents = sentences(words)
    energy = list(energy or [])
    speech = sorted(x for x in energy if x > -90)
    med = speech[len(speech) // 2] if speech else 0.0
    found = []
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            s0 = max(0.0, sents[i]["s"] - 0.15)
            e0 = sents[j]["e"] + 0.3
            if e0 - s0 > lmax:
                break
            if e0 - s0 < lmin:
                continue
            sc, why = _score(sents[i:j + 1], s0, e0, lmin, lmax, energy, med, step)
            found.append((sc, i, j, s0, e0, why))
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
    if not p.is_file():
        raise ClipsError("Choose the long video (its full path).")
    from . import auto_edit as ae
    ae._guard_private(p)
    if ae.cloud_only(p):
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
        clean.append({"s": round(s, 2), "e": round(e, 2), "first": tf.clean_text(str(c.get("first") or ""), 200)})
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


def candidates(jid: str) -> list[dict]:
    try:
        return list(json.loads((vo._job_dir(jid) / "clips.json").read_text("utf-8")).get("candidates") or [])
    except Exception:
        return []


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
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src)}
    wav = d / "sound16k.wav"
    res = vo._run_worker({"task": "transcribe", "source": str(src), "wav16": str(wav), "ffmpeg": vo._ffmpeg(),
                          "language": job.get("language"), "duration": float(job.get("duration") or 0)},
                         d / "work", timeout=12 * 3600, on_line=vo._progress)
    energy = energy_db(wav) if wav.is_file() else []
    wav.unlink(missing_ok=True)
    if not res.get("ok"):
        return res
    words = [{"w": str(w["w"]), "s": float(w["s"]), "e": float(w["e"]), "p": float(w.get("p") or 0)}
             for w in (res.get("words") or []) if str(w.get("w") or "").strip()]
    if not words:
        return {"ok": False, "error": "No speech was found in this video."}
    return save_found(d, job, words, energy, res.get("language") or "")


def save_found(d: Path, job: dict, words: list[dict], energy: list[float], language: str = "") -> dict:
    """The words and the clips found in them, kept with the job (also used by the checks without listening)."""
    lmin, lmax = LENGTHS.get(job.get("length") or "medium", LENGTHS["medium"])
    found = find_candidates(words, energy, lmin, lmax)
    (d / "words.json").write_text(json.dumps(words, ensure_ascii=False), "utf-8")
    (d / "clips.json").write_text(json.dumps({"candidates": found, "length": [lmin, lmax]}, ensure_ascii=False), "utf-8")
    if not found:
        return {"ok": False, "error": "No part of the speech makes a clip of this length: choose shorter or longer clips."}
    return {"ok": True, "language": language, "candidates": len(found), "words": len(words),
            "duration": float(job.get("duration") or 0)}


# ------------------------------------------------------------------------------------------ the face in the frame

_FACES: dict = {}


def face_finder():
    """OpenCV's frontal face finder (its file shipped with OpenCV), or None. The file is read by Python and given to
    OpenCV from memory: OpenCV cannot open a path with Russian letters on Windows (a program folder named so)."""
    if "f" in _FACES:
        return _FACES["f"]
    found = None
    try:
        import cv2
        path = os.environ.get("MEDENG_FACE_CASCADE") or os.path.join(
            str(getattr(getattr(cv2, "data", None), "haarcascades", "") or ""), "haarcascade_frontalface_default.xml")
        if hasattr(cv2, "CascadeClassifier") and os.path.isfile(path):
            text = Path(path).read_text("utf-8", errors="replace")
            fs = cv2.FileStorage(text, cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            c = cv2.CascadeClassifier()
            if c.read(fs.getFirstTopLevelNode()) and not c.empty():
                found = c
            else:
                c = cv2.CascadeClassifier(path)
                found = None if c.empty() else c
    except Exception:
        found = None
    _FACES["f"] = found
    return found


def plan_shots(src: Path, start: float, dur: float, info: dict, out_aspect: float, framing: str = "face") -> dict:
    """Where the picture of each shot of a clip is cut: one look at the clip (small, grey, 30 pictures a second) finds
    the cuts between shots; faces are looked for a few times a second. Per shot: the crop's middle on the face, or the
    whole picture on blurred edges when two faces would not both fit (or none is found and the picture is wide)."""
    W, H = int(info["w"]), int(info["h"])
    cw = min(1.0, (H * out_aspect) / max(1, W))          # the crop's width as a share of the picture's
    plan = {"shots": [], "faces": False, "crop_w": cw}
    if framing == "blur" or cw >= 0.98:
        plan["shots"] = [{"s": 0.0, "e": dur, "layout": "fit" if framing == "blur" else "crop", "cx": 0.5}]
        return plan
    fw = 480
    fh = max(2, int(round(fw * H / max(1, W) / 2)) * 2)
    finder = face_finder()
    plan["faces"] = finder is not None
    pre = "setsar=1," if abs(float(info.get("sar") or 1) - 1) < 0.01 else "scale=trunc(iw*sar/2)*2:ih,setsar=1,"
    cmd = [vo._ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
           "-an", "-vf", f"{pre}fps=30,scale={fw}:{fh},format=gray", "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, **process_kwargs({}))
    from . import auto_edit as ae
    ae._attach_job_object(proc)
    vo._track(proc)
    import numpy as np
    size = fw * fh
    cuts, samples = [0], []
    prev, i, last_face = None, 0, -100
    try:
        while True:
            b = proc.stdout.read(size)
            if not b or len(b) < size:
                break
            if vo._CURRENT.get("cancel"):
                break
            f = np.frombuffer(b, dtype=np.uint8).reshape(fh, fw)
            small = f[::8, ::8].astype(np.int16)
            if prev is not None and float(np.mean(np.abs(small - prev))) > 28.0 and i - cuts[-1] >= 8:
                cuts.append(i)
                last_face = -100                         # (a new shot: its faces looked for at once)
            prev = small
            if finder is not None and i - last_face >= 10:
                last_face = i
                try:
                    found = finder.detectMultiScale(f, scaleFactor=1.12, minNeighbors=5, minSize=(max(24, fh // 12),) * 2)
                except Exception:
                    found = ()
                samples.append((i, [(float(x + w / 2) / fw, float(w) / fw) for (x, y, w, h) in found]))
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
    n = max(i, 1)
    edges = cuts + [n]
    shots = []
    for a, b in zip(edges, edges[1:]):
        if b <= a:
            continue
        faces = [fs for (k, fs) in samples if a <= k < b]
        mains, spread_wide = [], 0
        for fs in faces:
            if not fs:
                continue
            big = max(fs, key=lambda t: t[1])
            near = [t for t in fs if t[1] >= 0.6 * big[1]]
            lo, hi = min(t[0] - t[1] / 2 for t in near), max(t[0] + t[1] / 2 for t in near)
            if hi - lo > cw * 0.95:
                spread_wide += 1
            mains.append(big[0])
        seen = [fs for fs in faces if fs]
        if seen and spread_wide >= max(1, len(seen) / 2):
            layout, cx = "fit", 0.5                      # two people apart: both stay in the picture
        elif mains:
            mains.sort()
            layout, cx = "crop", mains[len(mains) // 2]
        else:
            layout, cx = "crop", 0.5
        shots.append({"s": round(a / 30.0, 3), "e": round(b / 30.0, 3), "layout": layout, "cx": round(cx, 4)})
    if not shots:
        shots = [{"s": 0.0, "e": dur, "layout": "crop", "cx": 0.5}]
    shots[-1]["e"] = max(shots[-1]["e"], dur)
    plan["shots"] = shots
    return plan


def _graph(plan: dict, info: dict, out: tuple[int, int] | None) -> tuple[str, int, int]:
    """[0:v] -> [pv]: the picture of the clip in its new shape (the shots' crops, the blurred-edges shots laid over)."""
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
    xs = [max(0, min(W - cw, int(round(sh["cx"] * W - cw / 2)))) for sh in shots]
    expr = str(xs[-1])
    for sh, x in reversed(list(zip(shots[:-1], xs[:-1]))):
        expr = f"if(lt(t,{sh['e']:.3f}),{x},{expr})"
    crop = (f"crop=w={cw}:h={ch}:x='{expr}':y={(H - ch) // 2},scale={ow}:{oh}:flags=lanczos,setsar=1")
    fit = (f"split=2[bga][fga];[bga]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},gblur=sigma=28,"
           f"eq=brightness=-0.06[bgb];[fga]scale={ow}:{oh}:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[fgb];"
           f"[bgb][fgb]overlay=(W-w)/2:(H-h)/2")
    fits = [sh for sh in shots if sh["layout"] == "fit"]
    if not fits:
        return f"[0:v]{pre},{crop}[pv]", ow, oh
    if len(fits) == len(shots):
        return f"[0:v]{pre},{fit},setsar=1[pv]", ow, oh
    on = "+".join(f"between(t,{sh['s']:.3f},{sh['e'] - 0.001:.3f})" for sh in fits)
    return (f"[0:v]{pre},split=2[ca][fa];[ca]{crop}[cb];[fa]{fit},setsar=1[fb];"
            f"[cb][fb]overlay=0:0:enable='{on}'[pv]", ow, oh)


def _do_make(d: Path, job: dict) -> dict:
    from . import auto_edit as ae, orders as od
    src = Path(job["source"])
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src)}
    words = words_of(job["find"])
    info = _video_info(src)
    out = FORMATS.get(job.get("format") or "vertical")
    clips = list(job.get("clips") or [])
    folder = _out_folder(src)
    made = []
    from .converter import HDR_TO_SDR, _hdr_kind
    hdr = _hdr_kind(vo._ffmpeg(), src)
    for n, c in enumerate(clips, 1):
        if vo._CURRENT.get("cancel"):
            raise ClipsError("Stopped.")
        s, e = float(c["s"]), float(c["e"])
        dur = round(e - s, 3)
        vo._CURRENT.update(step=f"clip {n}/{len(clips)}", progress=round((n - 1) / max(1, len(clips)), 3))
        plan = plan_shots(src, s, dur, info, (out[0] / out[1]) if out else 1.0, job.get("framing") or "face") if out else \
            {"shots": [{"s": 0.0, "e": dur, "layout": "crop", "cx": 0.5}], "faces": False}
        graph, ow, oh = _graph(plan, info, out)
        if hdr in HDR_TO_SDR:                             # an HDR phone video: normal colours first
            graph = graph.replace("[0:v]", f"[0:v]{HDR_TO_SDR[hdr]},", 1)
        cs = vo.style_cues(words_between(words, s, e), job.get("opts")) if job.get("captions", True) else []
        texts = []
        if job.get("first_as_title") and c.get("first"):
            texts = tf.parse_texts([{"text": c["first"][: tf.TEXT_MAX], "start": "0", "end": "3", "where": "top", "look": "banner"}])
        chain = ["scale=out_range=tv"]
        if cs or texts:
            (d / "captions.ass").write_text(tf.document(ow, oh, cs, tf.resolve_texts(texts, dur), job.get("opts"), 0.0), "utf-8")
            fonts = tf.install_fonts(d)
            fonts = vo._caption_font(d) or fonts
            chain.append("ass=captions.ass" + (":fontsdir=fonts" if fonts else ""))
        chain.append("format=yuv420p")
        fc = graph + f";[pv]{','.join(chain)}[v]"
        cmd = [vo._ffmpeg(), "-hide_banner", "-nostdin", "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
               "-filter_complex", fc, "-map", "[v]"]
        if info["audio"]:
            fc_a = (f"[0:a:0]aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.06,"
                    f"afade=t=out:st={max(0.0, dur - 0.15):.3f}:d=0.15,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
            cmd[cmd.index("-filter_complex") + 1] = fc + ";" + fc_a
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if hdr in HDR_TO_SDR else []
        name = f"clip_{n:02d}.mp4"
        tmp = d / f"clip_{n:02d}.new.mp4"
        tmp.unlink(missing_ok=True)
        tries = ([[*tags, "-color_range", "tv", "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0",
                   "-profile:v", "high"]] if vo.nvenc_ok() else []) + \
                [[*tags, "-color_range", "tv", "-c:v", "libx264", "-preset", "medium", "-crf", "18"]]
        rc = -1
        for enc in tries:
            rc = vo._run_ffmpeg(cmd + enc + ["-t", f"{dur:.3f}", "-movflags", "+faststart", tmp.name], d, d / "ffmpeg.log", 3 * 3600)
            if rc == 0 and tmp.is_file() and tmp.stat().st_size > 1000:
                break
            tmp.unlink(missing_ok=True)
            if vo._CURRENT.get("cancel"):
                break
        shutil.rmtree(d / "fonts", ignore_errors=True)
        if vo._CURRENT.get("cancel"):
            tmp.unlink(missing_ok=True)
            raise ClipsError("Stopped.")
        if rc != 0 or not tmp.is_file():
            lines = [x for x in (d / "ffmpeg.log").read_text("utf-8", errors="replace").splitlines() if x.strip()]
            why = next((x for x in reversed(lines) if not re.match(r"\s*(frame=|size=|\$ )", x)), lines[-1] if lines else "?")
            return {"ok": False, "error": f"Clip {n} could not be made (" + why[:200] + ").", "made": made}
        checks = od._check_output(tmp, {"seconds": dur, "tolerance": 0.3, "audio": info["audio"]})
        if not all(x["pass"] for x in checks):
            bad = next(x for x in checks if not x["pass"])
            ae._replace_retry(tmp, d / f"clip_{n:02d}_failed_check.mp4")
            return {"ok": False, "error": f"Clip {n} did not pass its check ({bad['check']}: {bad['detail']}).", "made": made}
        ae._replace_retry(tmp, d / name, tries=30)
        saved = _save(d / name, folder, n, c.get("first") or "")
        made.append({"file": name, "s": s, "e": e, "seconds": dur, "saved": saved, "width": ow, "height": oh,
                     "layouts": sorted({sh["layout"] for sh in plan["shots"]}), "shots": len(plan["shots"]),
                     "faces": bool(plan.get("faces")), "captions": len(cs)})
    vo._CURRENT.update(step="checking", progress=1.0)
    return {"ok": True, "clips": made, "folder": str(folder) if folder else ""}


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

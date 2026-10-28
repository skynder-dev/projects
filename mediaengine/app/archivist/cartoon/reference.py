"""Reference Lab: a cartoon (or any short video) the owner likes, studied for its rhythm - not copied. Where its shots
change (hard cuts and soft ones - a cross-fade, a slide), how long they last, a picture of each (a storyboard), its
main colours; with the voice add-on also what is said in each shot, how fast, how soon the first words come, how much
of it is speech and whether music or sounds play between the words. Kept with the job (reference.json, frames/), and
used by the story writer: "Write a story with this rhythm" asks the model for as many scenes, as many words a second
and an opening as quick as the reference's - the story itself stays new.
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import wave
from pathlib import Path

import numpy as np

MAX_FRAMES = 40                   # (a long video: this many pictures, spread over it)
MAX_SECONDS = 30 * 60             # (a reference is a cartoon or a short: half an hour at most)


class StudyError(Exception):
    pass


def new_study(video: str, listen: bool = True) -> str:
    """A video to study (a job of the queue)."""
    from .. import voice as vo
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise StudyError("Choose a video (its full path) to study.")
    vo._check_video(p)
    from .. import auto_edit as ae
    try:
        info = ae._probe(p)
    except Exception:
        info = {}
    if float((info.get("format") or {}).get("duration") or 0) > MAX_SECONDS:
        raise StudyError("This video is longer than half an hour: choose a cartoon or a short (or a part of a long video).")
    sound = any(x.get("codec_type") == "audio" for x in (info.get("streams") or [])) if info else True
    listen = bool(listen) and vo.installed() and sound      # (a video without sound: nothing to listen to)
    return vo._submit({"kind": "cartoon_study", "video": str(p), "listen": listen, "sound": sound, "title": p.stem[:60] or "Video",
                       "needs_addon": False}, addon=False)


def _run(cmd: list, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


SCAN_FPS = 6                      # pictures a second compared
SCAN_W, SCAN_H = 64, 64           # (small: the cut is in the whole picture, not its details)


def _cuts(src: Path, duration: float, ff: str, stop, progress=None, colours: list | None = None) -> list[float]:
    """Where the shots change: a hard cut (the picture unlike the one before, much more than the movement around it)
    and a soft one - a cross-fade, a slide or an opening circle of up to half a second (unlike the picture half a
    second before, the most around). colours: filled with every picture's average colour (b, g, r). OSError when the
    video cannot be read (or not quickly enough); [] when stopped."""
    import tempfile
    import threading
    import time
    from .. import auto_edit as ae, voice as vo
    errf = tempfile.TemporaryFile()                        # (FFmpeg's complaints: a file, never a pipe that fills up)
    proc = subprocess.Popen([ff, "-hide_banner", "-nostdin", "-v", "error", "-i", str(src), "-an", "-sn", "-dn",
                             "-vf", f"fps={SCAN_FPS},scale={SCAN_W}:{SCAN_H}:flags=area", "-pix_fmt", "bgr24", "-f", "rawvideo", "-"],
                            stdout=subprocess.PIPE, stderr=errf, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    ae._attach_job_object(proc)                            # (closed with the program; Stop reaches it)
    queued = threading.current_thread().name == "voice-jobs"   # (the queue's own job: its Stop and Quit reach it)
    vo._track(proc, queued)
    limit = time.monotonic() + 60 + duration * 0.5
    why: list = []

    def watch():                                           # (a read that waits for ever is ended too)
        while proc.poll() is None:
            if stop():
                why.append("stop")
            elif time.monotonic() > limit:
                why.append("slow")
            if why:
                try:
                    proc.kill()
                except OSError:
                    pass
                return
            time.sleep(0.5)
    threading.Thread(target=watch, name="study-scan", daemon=True).start()
    size = SCAN_W * SCAN_H * 3
    frames: list = []                                      # (the last few pictures only)
    d1, d3 = [], []
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            f = np.frombuffer(buf, np.uint8).astype(np.int16)
            frames = (frames + [f])[-4:]
            d1.append(float(np.abs(f - frames[-2]).mean()) / 255 if len(frames) >= 2 else 0.0)
            d3.append(float(np.abs(f - frames[0]).mean()) / 255 if len(frames) >= 4 else 0.0)
            if colours is not None:
                colours.append(tuple(float(x) for x in f.reshape(-1, 3).mean(axis=0)))
            if progress and len(d1) % 60 == 0:
                progress(min(1.0, len(d1) / max(1.0, duration * SCAN_FPS)))
        proc.wait(timeout=30)
        errf.seek(0)
        err = errf.read()[-4000:].decode("utf-8", "replace")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=30)
        vo._untrack(proc, queued)
        errf.close()
    if "stop" in why or stop():
        return []
    if "slow" in why:
        raise OSError("too slow")
    if proc.returncode and not d1:
        raise OSError((err.strip().splitlines() or ["FFmpeg failed"])[-1][:200])
    n = len(d1)
    found = []
    for i in range(1, n):
        around = sorted(d1[max(1, i - 12):i] + d1[i + 1:i + 4])
        calm = around[len(around) // 2] if around else 0.0      # (the usual change here: movement, not a cut)
        if d1[i] > max(0.07, 4 * calm):                          # a hard cut
            found.append((i, d1[i]))
        elif i >= 3 and d3[i] > max(0.12, 6 * calm) and d3[i] == max(d3[max(3, i - 3):i + 4]) \
                and max(d1[i - 2:i + 1]) < d3[i] * 0.8:          # a soft one: no single jump, a big change over 0.5 s
            found.append((i - 1, d3[i]))
    out: list = []
    for i, strength in sorted(found):
        t = i / SCAN_FPS
        if not (0.3 < t < duration - 0.3):
            continue
        if out and t - out[-1][0] < 0.5:                         # (the stronger of two close ones)
            if strength > out[-1][1]:
                out[-1] = (t, strength)
            continue
        out.append((t, strength))
    return [round(t, 2) for t, _ in out]


def _frames(src: Path, shots: list[dict], out: Path, ff: str, stop) -> list[str]:
    """A small picture from the middle of each shot (at most MAX_FRAMES, spread over the video)."""
    out.mkdir(parents=True, exist_ok=True)
    idx = list(range(len(shots)))
    if len(idx) > MAX_FRAMES:
        idx = sorted({round(i * (len(shots) - 1) / (MAX_FRAMES - 1)) for i in range(MAX_FRAMES)})
    names = [""] * len(shots)
    for i in idx:
        if stop():
            break
        s = shots[i]
        name = f"{i:04d}.jpg"
        t = s["s"] + (s["e"] - s["s"]) * 0.5
        try:
            _run([ff, "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                  "-vf", "scale=320:-2", "-q:v", "4", "-y", str(out / name)], timeout=60)
        except subprocess.TimeoutExpired:
            continue
        if (out / name).is_file() and (out / name).stat().st_size > 0:
            names[i] = name
    return names


def _palette(folder: Path, names: list[str], k: int = 6) -> list[dict]:
    """The main colours of the pictures (k-means), the most used first, with their shares."""
    import cv2
    px = []
    for n in names:
        if not n:
            continue
        try:                                               # (imread cannot open a path with Cyrillic letters on Windows)
            img = cv2.imdecode(np.fromfile(str(folder / n), np.uint8), cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            img = None
        if img is None:
            continue
        small = cv2.resize(img, (48, 48), interpolation=cv2.INTER_AREA)
        px.append(small.reshape(-1, 3))
    if not px:
        return []
    data = np.concatenate(px).astype(np.float32)
    k = max(1, min(k, len(data)))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
    cv2.setRNGSeed(7)
    _c, labels, centers = cv2.kmeans(data, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.reshape(-1), minlength=k).astype(float)
    groups: list[list] = []                                # (colours nearly the same: one, with their shares added)
    for i in np.argsort(-counts):
        if counts[i] <= 0:
            continue
        near = next((g for g in groups if float(np.linalg.norm(g[0] - centers[i])) < 40), None)
        if near:
            near[1] += counts[i]
        else:
            groups.append([centers[i].copy(), counts[i]])
    out = []
    for c, n in sorted(groups, key=lambda g: -g[1]):
        b, g_, r = (int(round(x)) for x in c)
        out.append({"hex": f"#{r:02x}{g_:02x}{b:02x}", "share": round(float(n) / len(data), 3)})
    return out


def _listen(src: Path, d: Path, duration: float) -> dict:
    """What is said, with the words' times (Whisper, the voice add-on); the sound kept a moment for the music check."""
    from .. import voice as vo
    kept = d / "words.json"
    if kept.is_file():
        try:
            return json.loads(kept.read_text("utf-8"))
        except ValueError:
            pass
    wav = d / "sound16k.wav"
    wjob = {"task": "transcribe", "source": str(src), "wav16": str(wav), "ffmpeg": vo._ffmpeg(), "language": None,
            "duration": duration, "piece_s": 1200.0}

    def line(msg):
        if "progress" in msg:
            vo._CURRENT.update(step="listening", progress=round(0.35 + 0.5 * float(msg["progress"]), 3))
    res = vo.transcribe(wjob, d / "work", timeout=6 * 3600, on_line=line)
    shutil.rmtree(d / "work", ignore_errors=True)
    if not res.get("ok"):                                  # (the shots and pictures are kept; Whisper's own words in detail)
        wav.unlink(missing_ok=True)
        return {"ok": False, "error": "The words could not be listened to (Whisper stopped).",
                "detail": str(res.get("error") or "")[:300]}
    words = [{"w": str(w.get("w") or "").strip(), "s": float(w.get("s") or 0), "e": float(w.get("e") or 0)}
             for w in res.get("words") or [] if str(w.get("w") or "").strip()]
    between = _between_words(wav, words, duration)
    wav.unlink(missing_ok=True)
    out = {"ok": True, "words": words, "between": between, "language": res.get("language") or ""}
    kept.write_text(json.dumps(out, ensure_ascii=False), "utf-8")
    return out


def _between_words(wav: Path, words: list[dict], duration: float) -> str:
    """'music' when sound goes on between the words (music or noises under the voice), 'quiet' when the gaps are
    silent, '' when it cannot be told (no sound file, hardly any gaps)."""
    try:
        with wave.open(str(wav), "rb") as w:
            if w.getsampwidth() != 2:
                return ""
            sr = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
            if w.getnchannels() > 1:
                a = a.reshape(-1, w.getnchannels()).mean(axis=1)
    except (OSError, wave.Error, EOFError):
        return ""
    hop = int(0.05 * sr)
    n = len(a) // hop
    if n < 20:
        return ""
    rms = np.sqrt(np.mean(a[: n * hop].reshape(n, hop) ** 2, axis=1))
    talk = np.zeros(n, bool)
    for wd in words:
        talk[max(0, int((wd["s"] - 0.15) / 0.05)):min(n, int((wd["e"] + 0.15) / 0.05) + 1)] = True
    edge = int(0.5 / 0.05)
    gaps = rms[edge:n - edge][~talk[edge:n - edge]]
    said = rms[talk]
    if len(gaps) < 10 or len(said) < 20:                    # (half a second of gaps at least)
        return ""
    ratio = float(np.median(gaps)) / max(1e-6, float(np.median(said)))
    return "music" if ratio > 0.12 else "quiet"


def _first_sentence(words: list[dict]) -> str:
    out = []
    for w in words[:40]:
        out.append(w["w"])
        if re.search(r"[.!?…]$", w["w"]) or len(out) >= 22:
            break
    return " ".join(out).strip()


def do(jid: str, d: Path, job: dict) -> dict:
    """voice._do for a video to study (in the queue's thread)."""
    from .. import auto_edit as ae, voice as vo
    stop = lambda: bool(vo._CURRENT.get("cancel"))      # noqa: E731
    src = Path(str(job.get("video") or ""))
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src)}
    vo._CURRENT.update(step="looking", progress=0.02)
    try:
        info = ae._probe(src)
    except Exception as exc:
        return {"ok": False, "error": "The video could not be read: " + str(exc)[:200]}
    duration = float((info.get("format") or {}).get("duration") or 0)
    vs = next((x for x in info.get("streams") or [] if x.get("codec_type") == "video"), {})
    w, h = int(vs.get("width") or 0), int(vs.get("height") or 0)
    try:                                                   # (a phone video turned when it is played)
        rot = int(float(info.get("rotation") or (vs.get("tags") or {}).get("rotate") or 0)) % 360
    except (TypeError, ValueError):
        rot = 0
    if rot in (90, 270):
        w, h = h, w
    if duration < 3:
        return {"ok": False, "error": "The video is too short to study (a few seconds at least)."}
    if duration > MAX_SECONDS:
        return {"ok": False, "error": "This video is longer than half an hour: choose a cartoon or a short (or a part of a long video)."}
    ff = vo._ffmpeg()
    try:                                                   # (not "one long shot" when the scan itself did not work)
        seen: list = []
        cuts = _cuts(src, duration, ff, stop, lambda x: vo._CURRENT.update(step="looking", progress=round(0.02 + 0.2 * x, 3)),
                     colours=seen)
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "error": "The video's shots could not be found (FFmpeg could not read it quickly enough). "
                                      "Try a shorter video, or convert it first (Media → Convert)."}
    if stop():
        return {"ok": False, "error": "Stopped."}
    bounds = [0.0] + [t for t in cuts if 0 < t < duration] + [duration]
    shots = [{"s": round(bounds[i], 2), "e": round(bounds[i + 1], 2)} for i in range(len(bounds) - 1)]
    vo._CURRENT.update(step="pictures", progress=0.25)
    names = _frames(src, shots, d / "frames", ff, stop)
    for s, n in zip(shots, names):
        s["frame"] = n
        part = seen[int(s["s"] * SCAN_FPS):max(int(s["s"] * SCAN_FPS) + 1, int(s["e"] * SCAN_FPS))]
        if part:                                           # (its average colour, every shot - for the strip)
            b, g, r = (int(sum(c[k] for c in part) / len(part)) for k in range(3))
            s["color"] = f"#{r:02x}{g:02x}{b:02x}"
    palette = _palette(d / "frames", names)
    heard = {}
    if job.get("listen") and not stop():
        if vo.installed():
            heard = _listen(src, d, duration)
        else:
            heard = {"ok": False, "error": "The voice add-on is not installed: the words were not listened to."}
    if stop():
        return {"ok": False, "error": "Stopped."}
    words = heard.get("words") or []
    for s in shots:
        mid = [x["w"] for x in words if s["s"] <= (x["s"] + x["e"]) / 2 < s["e"]]
        s["text"] = " ".join(mid)[:400]
    lens = [s["e"] - s["s"] for s in shots]
    talk = 0.0
    if words:                                              # (the time someone speaks: the words with short gaps joined)
        cur_s, cur_e = words[0]["s"], words[0]["e"]
        for x in words[1:]:
            if x["s"] - cur_e < 0.6:
                cur_e = max(cur_e, x["e"])
            else:
                talk += cur_e - cur_s
                cur_s, cur_e = x["s"], x["e"]
        talk += cur_e - cur_s
    ref = {"video": str(src), "duration": round(duration, 2), "width": w, "height": h,
           "format": "vertical" if h > w else "horizontal", "shots": shots, "palette": palette,
           "shot_avg": round(statistics.mean(lens), 2), "shot_median": round(statistics.median(lens), 2),
           "shot_min": round(min(lens), 2), "shot_max": round(max(lens), 2),
           "cuts_per_min": round(len(cuts) / duration * 60, 1),
           "listened": bool(words), "listen_error": heard.get("error") if heard and not heard.get("ok") else "",
           "words": len(words), "wps": round(len(words) / duration, 2) if words else 0,
           "talk_share": round(min(1.0, talk / duration), 2) if words else 0,
           "first_words_at": round(words[0]["s"], 2) if words else None,
           "opening": _first_sentence(words), "between": heard.get("between") or "", "language": heard.get("language") or ""}
    (d / "reference.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), "utf-8")
    return {"ok": True, "file": "reference.json", "seconds": ref["duration"], "shots": len(shots), "shot_avg": ref["shot_avg"],
            "wps": ref["wps"], "listened": ref["listened"], "format": ref["format"]}


def reference_of(jid: str) -> dict:
    from .. import voice as vo
    try:
        return json.loads((vo._job_dir(jid) / "reference.json").read_text("utf-8"))
    except Exception:
        return {}


def studies() -> list[dict]:
    """The videos studied (done), newest first."""
    from .. import voice as vo
    return [j for j in vo.list_jobs(200) if j.get("kind") == "cartoon_study" and j.get("state") == "done"]


def style_of(jid: str) -> dict:
    """What the story writer takes from a reference: its length, how many scenes for its pace of cuts, how many
    words a second, how soon it speaks and how it opens. {} when there is no such study."""
    ref = reference_of(jid)
    if not ref:
        return {}
    from .. import voice as vo
    try:
        title = vo.read_job(jid).get("title") or ""
    except Exception:
        title = ""
    secs = int(max(45, min(120, round(float(ref.get("duration") or 75)))))
    avg = float(ref.get("shot_avg") or 6.0)
    scenes = scenes_for(secs, avg)
    opening = str(ref.get("opening") or "")
    return {"ref": jid, "title": title, "secs": secs, "scenes": scenes, "shot_avg": avg,
            "wps": float(ref.get("wps") or 0), "first_at": ref.get("first_words_at"),
            "opens": "question" if opening.rstrip().endswith("?") else ("statement" if opening else ""),
            "talk_share": float(ref.get("talk_share") or 0), "format": ref.get("format") or "vertical"}


def scenes_for(secs: float, shot_avg: float) -> int:
    """How many scenes a story of `secs` gets for a reference whose shots last `shot_avg` s on average (a scene of
    the cartoon is a place with a few lines: at least 3 s), 6 to 14."""
    return int(max(6, min(14, round(float(secs) / max(3.0, float(shot_avg or 6.0))))))


def targets(style: dict | None, secs: int) -> tuple[int, int, int | None]:
    """The scenes (from, to) and the words (None: the usual) asked of a story of `secs` with a reference's style."""
    if not style:
        return 8, 10, None
    n = scenes_for(secs, float(style.get("shot_avg") or 6.0))
    lo, hi = max(6, n - 1), min(14, n + 1)
    words = None
    wps = float(style.get("wps") or 0)
    if wps > 0:                                            # (the model writes about a third more than asked)
        words = int(max(secs * 1.3, min(secs * 2.3, secs * min(3.2, max(1.6, wps)) * 0.76)))
    return lo, hi, words


def rules_of(style: dict, secs: int) -> tuple[str, int | None]:
    """The writer's rules from a reference's style: the line about the scenes, and the words to ask for (None: the
    usual)."""
    lo, hi, words = targets(style, secs)
    avg = float(style.get("shot_avg") or 6.0)              # (the pace is the reference's own: how long its shots last)
    per = "1 or 2 lines" if avg < 4.5 else "2 or 3 lines"
    extra = [f"- {lo} to {hi} scenes, {per} in each; every line one or two short sentences (at most 16 words)."]
    pace = ("quick cuts: short scenes that change often" if avg < 4.5 else "an even pace" if avg < 9 else
            "a calm pace: longer scenes, nothing rushed")
    extra.append(f"- The rhythm of a cartoon the viewer liked: {pace}.")
    first = style.get("first_at")
    if first is not None and float(first) <= 1.5:
        extra.append("- The very first line speaks at once and grabs attention"
                     + (" with a question." if style.get("opens") == "question" else " with a surprising fact or number."))
    elif style.get("opens") == "question":
        extra.append("- The first line asks the viewer a question.")
    return "\n".join(extra), words

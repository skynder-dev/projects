"""How much better would a bigger Whisper hear a real interview than the voice add-on's "small"? (a research probe)

  python tests/whisper_probe.py --out <dir> [--models a,b,c]

The 9-minute public-domain NASA interview of the voice add-on check (Wikimedia Commons, pinned SHA-256) is heard by
each model the way the add-on hears (faster-whisper, word times, VAD, beam 5) on the processor (int8). Writes
whisper_probe.json (time, words, the words of each model) and whisper_probe.md: how far each model's words are from the
biggest model's (a word error rate against it - no human transcript exists) and the places they differ, to read.
Captions of clips show these words, so a wrong word is seen by every viewer. Free models (MIT); nothing paid.
Not part of the program.
"""
from __future__ import annotations

import argparse, difflib, hashlib, json, re, shutil, sys, time, urllib.request
from pathlib import Path

TALK = {"url": "https://upload.wikimedia.org/wikipedia/commons/transcoded/4/46/SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_%28iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170%29.webm/SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_%28iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170%29.webm.480p.vp9.webm",
        "sha256": "812a2ec9e1bc66c7a6a21d23e2c32b665ac20a98e2bb1b377cad8788dcc63fe7",
        "page": "https://commons.wikimedia.org/wiki/File:SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_(iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170).webm"}
UA = {"User-Agent": "MediaEngine-CI/1.0 (https://github.com/skynder-dev/projects; automated test, small number of requests)"}
# (repository, revision or "" for the newest; the first is the add-on's own)
MODELS = [("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120"),
          ("Systran/faster-distil-whisper-large-v3", ""),
          ("deepdml/faster-whisper-large-v3-turbo-ct2", ""),
          ("Systran/faster-whisper-large-v3", "")]


def norm(w: str) -> str:
    return re.sub(r"[^\w']+", "", w.lower())


def wer(ref: list[str], hyp: list[str]) -> float:
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    errs = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
    return errs / max(1, len(ref))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--work", default="")
    ap.add_argument("--models", default="")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    work = Path(a.work or out / "work"); work.mkdir(parents=True, exist_ok=True)
    src = work / "nasa_interview.webm"
    if not src.is_file():
        with urllib.request.urlopen(urllib.request.Request(TALK["url"], headers=UA), timeout=600) as r, src.open("wb") as fh:
            shutil.copyfileobj(r, fh, 1 << 20)
    if hashlib.sha256(src.read_bytes()).hexdigest() != TALK["sha256"]:
        print("the interview changed on Commons"); return 1
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    models = [m for m in MODELS if not a.models or m[0] in a.models.split(",")]
    rep: dict = {"video": TALK, "models": {}}
    for repo, rev in models:
        t0 = time.time()
        try:
            path = snapshot_download(repo, revision=rev or None)
            asr = WhisperModel(path, device="cpu", compute_type="int8")
        except Exception as exc:
            rep["models"][repo] = {"error": f"{type(exc).__name__}: {exc}"[:400]}
            continue
        load_s = time.time() - t0
        t1 = time.time()
        segs, info = asr.transcribe(str(src), language="en", word_timestamps=True, vad_filter=True, beam_size=5)
        words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 3)}
                 for sg in segs for w in (sg.words or [])]
        rep["models"][repo] = {"revision": Path(path).name, "load_s": round(load_s, 1), "hear_s": round(time.time() - t1, 1),
                               "audio_s": round(info.duration, 1), "words": words}
        print(repo, rep["models"][repo]["hear_s"], "s,", len(words), "words", flush=True)
        del asr
    (out / "whisper_probe.json").write_text(json.dumps(rep, ensure_ascii=False), "utf-8")
    ok = [r for r, v in rep["models"].items() if "words" in v]
    md = ["# Whisper models on the NASA interview (9 min, CPU int8)", ""]
    for r in rep["models"]:
        v = rep["models"][r]
        md.append(f"- {r}: " + (v["error"] if "error" in v else
                                 f"{v['hear_s']} s to hear {v['audio_s']} s ({v['load_s']} s to load), {len(v['words'])} words"))
    if ok:
        ref_name = ok[-1]                                   # (the biggest one heard as the reference)
        ref = [norm(w["w"]) for w in rep["models"][ref_name]["words"] if norm(w["w"])]
        md += ["", f"## Word error rate against {ref_name} (no human transcript: the biggest model as the reference)", ""]
        for r in ok[:-1]:
            hyp = [norm(w["w"]) for w in rep["models"][r]["words"] if norm(w["w"])]
            md.append(f"- {r}: {100 * wer(ref, hyp):.1f} %")
        for r in ok[:-1]:
            hyp_w = [w for w in rep["models"][r]["words"] if norm(w["w"])]
            ref_w = [w for w in rep["models"][ref_name]["words"] if norm(w["w"])]
            sm = difflib.SequenceMatcher(a=[norm(w["w"]) for w in ref_w], b=[norm(w["w"]) for w in hyp_w], autojunk=False)
            md += ["", f"### Where {r} hears otherwise ({ref_name} -> {r})", ""]
            n = 0
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    continue
                at = ref_w[i1]["s"] if i1 < len(ref_w) else (hyp_w[j1]["s"] if j1 < len(hyp_w) else 0)
                ctx = " ".join(w["w"] for w in ref_w[max(0, i1 - 4):i1])
                md.append(f"- {at:.0f} s: ...{ctx} **{' '.join(w['w'] for w in ref_w[i1:i2]) or '-'}** -> "
                          f"**{' '.join(w['w'] for w in hyp_w[j1:j2]) or '-'}**")
                n += 1
                if n >= 60:
                    break
    (out / "whisper_probe.md").write_text("\n".join(md) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

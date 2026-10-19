"""Voice lab: free local voice-over engines side by side, before any of them goes into MediaEngine.

One English test text, one female American voice, several engines and settings. Every take is checked by machine
(what was actually said - faster-whisper; how high the voice is - pitch; how long) and the better of two takes
by those checks is kept. The owner then listens blind (letters A, B, C ...) and picks; only the pick goes into
MediaEngine. Nothing here is the product: it decides which engine the product uses.

  python voice_lab.py kokoro    <out>              (Kokoro-82M af_heart - the voice the owner found flat; reference)
  python voice_lab.py qwen      <out>              (Qwen3-TTS VoiceDesign: a voice from a description; the locked voice)
  python voice_lab.py chatterbox <out> [<ref.wav>] (Chatterbox: built-in voice, and the locked voice from qwen)
  python voice_lab.py check     <in> <out>         (word check, pitch, loudness, blind letters, results)

Each engine runs in its own venv (their pins clash); CPU only (GitHub runners have no GPU). Synthetic voices only:
no recordings of real people, no owner data.
"""
from __future__ import annotations

import gc, json, os, random, re, subprocess, sys, time, traceback
from pathlib import Path

TEXT = ("Okay, so here's something nobody tells you about packing for a beach trip. "
        "You don't need ten outfits. You need three, and one really good hat. "
        "We tried it last summer, and honestly? It changed everything. "
        "Less stuff, more time in the water. Would you try it? Let me know in the comments!")
REF_TEXT = ("Hi! I'm so glad you're here. Today I want to show you something simple "
            "that made my mornings so much easier.")
WARM = ("A warm, friendly young American woman in her late twenties, talking casually to a good friend. "
        "She smiles while she talks, with natural rises and falls in pitch, a relaxed pace and small natural pauses. "
        "Never flat, never like reading an announcement.")
UPBEAT = ("An upbeat, energetic young female social media host from California. Bright and expressive, "
          "playful emphasis on key words, lively but clear, a medium-fast pace.")
TAKES = (1, 2)

# variant id -> what it is (shown to the owner only after the pick)
VARIANTS = {
    "kokoro_af_heart": "Kokoro-82M, voice af_heart, speed 1.0 (what Social uses now)",
    "chatterbox_builtin": "Chatterbox, built-in voice, exaggeration 0.7, cfg 0.3 (more expressive than default)",
    "chatterbox_locked": "Chatterbox, the locked designed voice as reference, exaggeration 0.6, cfg 0.4",
    "qwen_design_warm": "Qwen3-TTS 1.7B VoiceDesign, 'warm friendly young American woman, casual'",
    "qwen_design_upbeat": "Qwen3-TTS 1.7B VoiceDesign, 'upbeat energetic social media host'",
    "qwen_locked": "Qwen3-TTS 1.7B Base, cloning the locked designed voice (the same character every time)",
}
LICENSES = {
    "kokoro": "Kokoro-82M: Apache-2.0 (misaki uses espeak-ng: GPL-3 - check before shipping)",
    "chatterbox": "Chatterbox: MIT (outputs carry Resemble's inaudible Perth watermark)",
    "qwen": "Qwen3-TTS: Apache-2.0",
}


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def _threads() -> None:
    import torch
    torch.set_num_threads(max(1, os.cpu_count() or 1))


def _save(path: Path, audio, sr: int) -> None:
    import numpy as np, soundfile as sf
    a = audio
    if hasattr(a, "detach"):
        a = a.detach().cpu().float().numpy()
    a = np.asarray(a, dtype="float32").squeeze()
    sf.write(str(path), a, int(sr))


def _record(out: Path, name: str, info: dict) -> None:
    p = out / "gen.json"
    data = json.loads(p.read_text("utf-8")) if p.exists() else {}
    data[name] = info
    p.write_text(json.dumps(data, indent=1), "utf-8")


def _take(out: Path, variant: str, take: int, fn) -> None:
    """Make one take; a failure is recorded (with the traceback), it does not stop the other variants."""
    name = f"{variant}_t{take}"
    t0 = time.time()
    try:
        audio, sr = fn(take)
        _save(out / f"{name}.wav", audio, sr)
        _record(out, name, {"variant": variant, "take": take, "seconds_to_make": round(time.time() - t0, 1), "sr": sr})
        _log(f"made {name} in {time.time() - t0:.0f} s")
    except Exception as exc:
        _record(out, name, {"variant": variant, "take": take, "error": f"{type(exc).__name__}: {exc}",
                            "trace": traceback.format_exc()[-3000:]})
        _log(f"FAILED {name}: {exc}")


def _api_dump(out: Path, obj, label: str) -> None:
    """What the installed package really offers (names and signatures) - for fixing a call that did not fit."""
    import inspect
    rows = []
    for n in dir(obj):
        if n.startswith("_"):
            continue
        try:
            rows.append(f"{n}{inspect.signature(getattr(obj, n))}")
        except Exception:
            rows.append(n)
    (out / f"api_{label}.txt").write_text("\n".join(rows), "utf-8")


def kokoro(out: Path) -> None:
    _threads()
    import numpy as np
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    def make(take):
        parts = []
        for r in pipe(TEXT, voice="af_heart", speed=1.0):
            a = r.audio if hasattr(r, "audio") else r[2]
            parts.append(a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a))
        return np.concatenate(parts), 24000

    _take(out, "kokoro_af_heart", 1, make)        # Kokoro is deterministic: one take is all there is


def qwen(out: Path) -> None:
    _threads()
    import torch
    from qwen_tts import Qwen3TTSModel

    def load(repo):
        _log(f"loading {repo}")
        try:
            return Qwen3TTSModel.from_pretrained(repo, device_map="cpu", dtype=torch.float32)
        except TypeError:
            return Qwen3TTSModel.from_pretrained(repo, device_map="cpu", torch_dtype=torch.float32)

    vd = load("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
    _api_dump(out, vd, "qwen_model")

    def design(text, instruct, seed):
        torch.manual_seed(seed)
        wavs, sr = vd.generate_voice_design(text=text, language="English", instruct=instruct)
        return wavs[0], sr

    ref = out / "reference_locked_voice.wav"
    try:                                           # the character's voice, made once from the description
        a, sr = design(REF_TEXT, WARM, 7)
        _save(ref, a, sr)
        _log("made the locked reference voice")
    except Exception as exc:
        _record(out, "reference", {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-3000:]})
        _log(f"FAILED reference: {exc}")
    for take in TAKES:
        _take(out, "qwen_design_warm", take, lambda t: design(TEXT, WARM, 100 + t))
        _take(out, "qwen_design_upbeat", take, lambda t: design(TEXT, UPBEAT, 200 + t))
    del vd
    gc.collect()
    if not ref.exists():
        return
    base = load("Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    _api_dump(out, base, "qwen_base")
    prompt = None
    try:
        prompt = base.create_voice_clone_prompt(ref_audio=str(ref), ref_text=REF_TEXT)
    except Exception as exc:
        _log(f"create_voice_clone_prompt did not fit ({exc}); passing the reference directly")

    def clone(take):
        torch.manual_seed(300 + take)
        if prompt is not None:
            wavs, sr = base.generate_voice_clone(text=TEXT, language="English", voice_clone_prompt=prompt)
        else:
            wavs, sr = base.generate_voice_clone(text=TEXT, language="English", ref_audio=str(ref), ref_text=REF_TEXT)
        return wavs[0], sr

    for take in TAKES:
        _take(out, "qwen_locked", take, clone)


def chatterbox(out: Path, ref: Path | None) -> None:
    _threads()
    import torch
    from chatterbox.tts import ChatterboxTTS
    m = ChatterboxTTS.from_pretrained(device="cpu")
    _api_dump(out, m, "chatterbox")

    def make(seed, **kw):
        torch.manual_seed(seed)
        return m.generate(TEXT, **kw), m.sr

    for take in TAKES:
        _take(out, "chatterbox_builtin", take, lambda t: make(400 + t, exaggeration=0.7, cfg_weight=0.3))
        if ref is not None and ref.exists():
            _take(out, "chatterbox_locked", take,
                  lambda t: make(500 + t, audio_prompt_path=str(ref), exaggeration=0.6, cfg_weight=0.4))


# ---------------------------------------------------------------------------------------------------------- check

def _words(s: str) -> list[str]:
    s = s.lower().replace("’", "'")
    return re.findall(r"[a-z0-9']+", s)


def _diff(ref: list[str], hyp: list[str]) -> tuple[int, list[str], list[str]]:
    """Word edit distance, words missing from the speech, words the speech added."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, missing, extra = n, m, [], []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] != hyp[j - 1]:
                missing.append(ref[i - 1]); extra.append(hyp[j - 1])
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            missing.append(ref[i - 1]); i -= 1
        else:
            extra.append(hyp[j - 1]); j -= 1
    return d[n][m], missing[::-1], extra[::-1]


def check(src: Path, out: Path) -> int:
    import numpy as np, librosa
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    ref_words = _words(TEXT)
    takes = {}
    for wav in sorted(src.rglob("*_t[0-9].wav")):
        name = wav.stem
        y, sr = librosa.load(str(wav), sr=16000, mono=True)
        dur = len(y) / sr
        segs, _ = asr.transcribe(str(wav), language="en", beam_size=5, vad_filter=True)
        said = " ".join(s.text.strip() for s in segs)
        dist, missing, extra = _diff(ref_words, _words(said))
        f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=450, sr=sr, frame_length=1024)
        f0v = f0[voiced & ~np.isnan(f0)] if f0 is not None else np.array([])
        med = float(np.median(f0v)) if f0v.size else 0.0
        semis = float(np.std(12 * np.log2(f0v / med))) if f0v.size and med else 0.0   # how much the pitch moves
        info = dict(gen.get(name, {}))
        info.pop("trace", None)
        info.update(file=str(wav.relative_to(src)), seconds=round(dur, 2), said=said, word_errors=dist,
                    word_error_rate=round(dist / max(1, len(ref_words)), 3), missing=missing, extra=extra,
                    pitch_median_hz=round(med, 1), pitch_movement_semitones=round(semis, 2),
                    female_range=bool(160 <= med <= 300),
                    words_per_minute=round(len(ref_words) / dur * 60, 1) if dur else 0)
        takes[name] = info
        _log(f"{name}: {dur:.1f} s, {dist} word errors, pitch {med:.0f} Hz +-{semis:.1f} st")
    best = {}
    for name, info in takes.items():          # the better take by the machine checks: fewer word errors, then take 1
        v = info.get("variant") or name.rsplit("_t", 1)[0]
        cur = best.get(v)
        if cur is None or (info["word_errors"], info.get("take", 9)) < (cur["word_errors"], cur.get("take", 9)):
            best[v] = info
    order = [v for v in VARIANTS if v in best]
    letters = "ABCDEFGH"
    shuffled = order[:]
    random.Random(2026).shuffle(shuffled)
    blind = {letters[i]: v for i, v in enumerate(shuffled)}
    for letter, v in blind.items():
        wav = src / best[v]["file"]
        mp3 = out / f"voice_{letter}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "44100", "-ac", "1", "-b:a", "160k", str(mp3)], check=True)
        best[v]["letter"] = letter
    failed = {k: v.get("error") for k, v in gen.items() if v.get("error")}
    res = {"text": TEXT, "reference_text": REF_TEXT, "descriptions": {"warm": WARM, "upbeat": UPBEAT},
           "blind": blind, "variants": {v: {"what": VARIANTS[v], **best[v]} for v in order},
           "missing_variants": [v for v in VARIANTS if v not in best], "failed_takes": failed,
           "all_takes": takes, "licenses": LICENSES,
           "note": "CPU only (GitHub runner); seconds_to_make on the owner's RTX 3060 will be far lower. "
                   "Loudness of every file evened out (-16 LUFS) so that no voice wins by being louder."}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab", "", f"Text: {TEXT}", "", "| letter | words wrong | seconds | pitch Hz | pitch moves (semitones) |",
          "|---|---|---|---|---|"]
    for letter, v in sorted(blind.items()):
        b = best[v]
        md.append(f"| {letter} | {b['word_errors']} | {b['seconds']} | {b['pitch_median_hz']} | {b['pitch_movement_semitones']} |")
    md += ["", "Which letter is which engine: results.json -> blind (kept out of this table on purpose)."]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"made": len(order), "of": len(VARIANTS), "failed_takes": len(failed)}))
    return 0 if order else 1


def main() -> int:
    cmd = sys.argv[1]
    out = Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if cmd == "kokoro":
        kokoro(out)
    elif cmd == "qwen":
        qwen(out)
    elif cmd == "chatterbox":
        chatterbox(out, Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None)
    elif cmd == "check":
        return check(out, Path(sys.argv[3]).resolve())
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""MediaEngine voice-over worker: runs in its own Python process with ONLY the voice add-on's packages.

  python -S -E -B voice_worker.py <job.json>

Started by voice.py with the program's own Python 3.11 but without its site-packages (-S): the add-on brings its own
torch / VoxCPM2 / faster-whisper (DATA\\addons\\voice\\site) and must never mix with the program's pinned packages.
A voice cloned from a recording is said by Qwen3-TTS (engine 'qwen'): its own folder (site_qwen) goes first.
Prints one JSON object per line on stdout ({"progress": 0.4, "step": "..."}, then {"result": {...}}); writes the
files the job names. Only standard library imports at the top: the add-on folder is added first.

Tasks:
  tts         text (in chunks) -> one WAV in one voice (VoxCPM2, or Qwen3-TTS for engine 'qwen'); every chunk is
              listened to (faster-whisper) and made again (up to 3 more times) when words are missing or the pitch drifts
  transcribe  a sound / video file -> the words said with their times (for captions)
  selftest    the add-on loads and sees the GPU (no model run)
"""
from __future__ import annotations

import json, os, re, site, subprocess, sys, time, traceback
from pathlib import Path


def say(**kw) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                       "fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_ORD = {w: f"{i + 1}" for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
                                            "twelfth".split())}
_SAME = {"okay": "ok", "mister": "mr", "missus": "mrs", "doctor": "dr", "versus": "vs", "and": "and"}


def _words(s: str) -> list[str]:
    """The words of a text in one way of writing, so that the same thing said is the same words: numbers as digits
    ("twenty five" = "25"), "%" = "percent", "#" = "number", "e-mail" = "email", "p.m." = "pm", "1,000" = "1000",
    "okay" = "ok", "1st" = "first" (words in brackets are said too, and checked)."""
    s = str(s).lower().replace("’", "'").replace("%", " percent ").replace("#", " number ")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)            # 1,000 -> 1000
    s = re.sub(r"\be-mail", "email", s)
    s = re.sub(r"(?<=\w)-(?=\w)", " ", s)                  # first-class = first class, twenty-five = twenty five
    s = re.sub(r"(?<=[^\W\d_])\.(?=[^\W\d_])", "", s)      # p.m. = pm, U.S. = us (not 10.30 or 2.0)
    out = []
    for w in re.findall(r"[\w']+", s):
        w = _SAME.get(w, w)
        m = re.fullmatch(r"(\d+)(st|nd|rd|th)", w)
        if m:
            w = m.group(1)
        elif w in _ORD:
            w = _ORD[w]
        else:                              # twentyfive (from twenty-five): two number words
            for t, v in _TENS.items():
                if w.startswith(t) and w[len(t):] in _UNITS and _UNITS[w[len(t):]] < 10:
                    out.append(t)
                    w = w[len(t):]
                    break
        out.append(w)
    # runs of number words -> one number ("two hundred and five" = "205", "twenty five" = "25"; "one two three" stays
    # three numbers, "five and six" stays two)
    res, i = [], 0
    while i < len(out):
        if out[i] not in _UNITS and out[i] not in _TENS:
            res.append(out[i])
            i += 1
            continue
        total, cur, last, j = 0, 0, None, i
        while j < len(out):
            w = out[j]
            if w in _UNITS and _UNITS[w] < 10 and last in (None, "tens", "hundred", "thousand", "and"):
                cur, last = cur + _UNITS[w], "unit"
            elif w in _UNITS and last in (None, "hundred", "thousand", "and"):
                cur, last = cur + _UNITS[w], "teen"
            elif w in _TENS and last in (None, "hundred", "thousand", "and"):
                cur, last = cur + _TENS[w], "tens"
            elif w == "hundred" and last in ("unit", "teen") and cur % 100 == cur:
                cur, last = cur * 100, "hundred"
            elif w == "thousand" and last in ("unit", "teen", "tens", "hundred"):
                total, cur, last = total + cur * 1000, 0, "thousand"
            elif (w == "and" and last in ("hundred", "thousand") and j + 1 < len(out)
                  and (out[j + 1] in _UNITS or out[j + 1] in _TENS)):
                last = "and"
            else:
                break
            j += 1
        res.append(str(total + cur))
        i = j
    return res


def word_errors(ref: str, said: str) -> int:
    """Word edit distance between the text and what was really said, both written one way (a spoken "twenty percent"
    written "20%" is not an error)."""
    a, b = _words(ref), _words(said)
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[-1]


def _patch_torchaudio() -> None:
    """torchaudio 2.8 may want FFmpeg's shared libraries to read a WAV (torchcodec); soundfile reads it without them."""
    import soundfile as sf, torch, torchaudio

    def load(path, *a, **k):
        d, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return torch.from_numpy(d.T.copy()), sr

    torchaudio.load = load


def _device(job: dict) -> str:
    import torch
    if job.get("device") in ("cpu", "cuda"):
        return job["device"]
    return "cuda" if torch.cuda.is_available() else "cpu"


def _whisper(job: dict):
    from faster_whisper import WhisperModel
    return WhisperModel(job["whisper_dir"], device="cpu", compute_type="int8",
                        cpu_threads=max(1, (os.cpu_count() or 2) - 1))


def _listen(asr, wav: str, language: str | None, total_s: float = 0.0, offset: float = 0.0) -> tuple[str, list[dict], str]:
    """total_s (a long recording): how far the listening is, said as it goes (from 20 % to 95 %); offset: where this
    piece of a long recording starts (added to every word's time)."""
    segs, info = asr.transcribe(wav, language=language or None, word_timestamps=True, vad_filter=True, beam_size=5)
    words = []
    for s in segs:
        if total_s > 0:
            say(progress=round(0.2 + 0.75 * min(1.0, (offset + float(s.end)) / total_s), 3))
        for w in (s.words or []):
            words.append({"w": w.word.strip(), "s": round(offset + float(w.start), 3), "e": round(offset + float(w.end), 3),
                          "p": round(float(getattr(w, "probability", 0) or 0), 3)})
    return " ".join(w["w"] for w in words), words, getattr(info, "language", "") or ""


def _pieces(wav: str, piece_s: float) -> list[tuple[float, float]]:
    """A long recording cut into pieces of about piece_s seconds, each cut in the quietest half second near its place
    (never in the middle of a word): Whisper keeps the whole sound of what it listens to in memory."""
    import wave
    import numpy as np
    with wave.open(wav, "rb") as f:
        rate, n = f.getframerate(), f.getnframes()
        total = n / float(rate)
        if piece_s <= 0 or total <= piece_s * 1.25:
            return [(0.0, total)]
        step = max(1, rate // 10)                           # loudness every 0.1 s
        loud = []
        while True:
            b = f.readframes(step)
            if not b:
                break
            a = np.frombuffer(b, dtype="<i2").astype(np.float32)
            loud.append(float(np.sqrt(np.mean(a * a))) if a.size else 0.0)
    loud = np.asarray(loud)
    cuts, at = [0.0], piece_s
    while at < total - piece_s * 0.25:
        a, b = int((at - 60) * 10), int((at + 60) * 10)
        win = np.convolve(loud[max(0, a):b], np.ones(5) / 5, mode="same") if b > a else np.array([])
        best = (max(0, a) + int(np.argmin(win))) / 10.0 if win.size else at
        cuts.append(best)
        at = best + piece_s
    cuts.append(total)
    return [(x, y) for x, y in zip(cuts, cuts[1:]) if y - x > 0.5]


def _trim(y, sr: int, top_db: float = 45.0):
    """Silence at both ends of a chunk cut (a little air kept), so the pauses between chunks are ours."""
    import numpy as np
    if y.size == 0:
        return y
    frame = max(1, int(0.02 * sr))
    n = y.size // frame
    if n == 0:
        return y
    rms = np.sqrt(np.mean(np.square(y[: n * frame].reshape(n, frame)), axis=1) + 1e-12)
    loud = np.where(20 * np.log10(rms / (rms.max() or 1e-9)) > -top_db)[0]
    if loud.size == 0:
        return y
    a = max(0, loud[0] * frame - int(0.04 * sr))
    b = min(y.size, (loud[-1] + 1) * frame + int(0.08 * sr))
    return y[a:b]


def _pitch(y, sr: int) -> float:
    """The median pitch of a voice, Hz (0 = none found)."""
    import numpy as np, librosa
    y = np.asarray(y, dtype="float32").reshape(-1)
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=450, sr=16000, frame_length=1024)
    f = f0[voiced & ~np.isnan(f0)] if f0 is not None else np.array([])
    return float(np.median(f)) if f.size else 0.0


PITCH_OFF_ST = 1.5          # a piece more than this many semitones off the voice's own pitch is made again


def _said(text: str) -> str:
    """The words for VoxCPM2: brackets as pauses (it takes a text that starts with "(...)" for a direction and would
    not say it)."""
    t = re.sub(r"\s*[()]\s*", ", ", str(text)).strip(" ,")
    return re.sub(r",\s*([,.!?;:])", r"\1", t)


class _Qwen:
    """Qwen3-TTS 1.7B Base (the owner's pick, voice lab 14_5) behind the same two calls the worker makes of VoxCPM2:
    generate(text=..., reference_wav_path=..., prompt_text=...) -> samples at tts_model.sample_rate. The voice is
    taken from the recording once (its words too, when known: the closest voice) and reused for every piece."""

    def __init__(self, model_dir: str, device: str, language: str | None):
        import torch
        from qwen_tts import Qwen3TTSModel
        if device == "cuda":                       # bf16 where the card has it (RTX 30xx and newer); else full
            try:                                   # precision (fp16 may overflow; emulated bf16 is slow)
                native = torch.cuda.is_bf16_supported(including_emulation=False)
            except TypeError:
                native = torch.cuda.get_device_capability(0)[0] >= 8
            kw = {"device_map": "cuda:0", "dtype": torch.bfloat16 if native else torch.float32}
        else:
            kw = {"device_map": "cpu", "dtype": torch.float32}
        try:
            self.m = Qwen3TTSModel.from_pretrained(model_dir, **kw)
        except TypeError:
            kw["torch_dtype"] = kw.pop("dtype")
            self.m = Qwen3TTSModel.from_pretrained(model_dir, **kw)
        self.language = language
        self.prompt, self.prompt_key = None, None
        self.tts_model = self                      # the worker reads tts_model.sample_rate
        self.sample_rate = 24000

    def generate(self, text: str, reference_wav_path: str, prompt_text: str = "", **_ignored):
        import numpy as np
        key = (str(reference_wav_path), prompt_text or "")
        if self.prompt is None or self.prompt_key != key:
            if prompt_text:
                self.prompt = self.m.create_voice_clone_prompt(ref_audio=str(reference_wav_path), ref_text=prompt_text)
            else:                                   # a recording without its words: the voice's timbre only
                self.prompt = self.m.create_voice_clone_prompt(ref_audio=str(reference_wav_path), x_vector_only_mode=True)
            self.prompt_key = key
        wavs, sr = self.m.generate_voice_clone(text=text, language=self.language, voice_clone_prompt=self.prompt)
        self.sample_rate = int(sr)
        return np.asarray(wavs[0], dtype="float32").reshape(-1)


def tts(job: dict) -> dict:
    import numpy as np, soundfile as sf, torch
    # (torch's own thread count: the program's OMP_NUM_THREADS=2 is not passed to the worker; setting one less than all
    #  cores made a CPU voice 4x slower on a 4-core runner - runs 39247474464 vs 39251509089)
    _patch_torchaudio()
    qwen = job.get("engine") == "qwen"
    dev = _device(job)
    say(progress=0.02, step="loading", device=dev)
    t0 = time.time()
    def load(device):
        if qwen:
            return _Qwen(job["qwen_dir"], device, job.get("qwen_language"))
        from voxcpm import VoxCPM
        kw = {"load_denoiser": False, "optimize": False, "device": device}
        try:
            return VoxCPM.from_pretrained(job["model_dir"], local_files_only=True, **kw)
        except TypeError:
            return VoxCPM.from_pretrained(job["model_dir"], **kw)
    try:
        model = load(dev)
    except Exception as exc:                 # the graphics card refused (too old a driver, too little memory): the processor
        if dev != "cuda":
            raise
        say(progress=0.03, step="loading", device="cpu", note=f"graphics card: {type(exc).__name__}: {str(exc)[:200]}")
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        dev = "cpu"
        model = load(dev)
    sr = int(model.tts_model.sample_rate)
    asr = _whisper(job)
    load_s = time.time() - t0
    chunks = [c for c in job["chunks"] if str(c.get("text") or "").strip()]
    voice = job.get("voice") or {}
    steps = int(job.get("steps") or (30 if dev == "cuda" else 10))
    cfg = float(job.get("cfg") or 2.0)
    seed = int(job.get("seed") or 1)
    tries_max = 4
    ref_hz = 0.0                            # the locked voice's own pitch: every piece is kept near it (a seed can lift it)
    out_dir = Path(job["work_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_wav, ref_text = voice.get("ref_wav"), voice.get("ref_text") or ""
    pieces, report = [], []
    total = len(chunks)
    for i, ch in enumerate(chunks):
        text = str(ch["text"]).strip()
        best = None
        for attempt in range(tries_max):
            torch.manual_seed(seed + 101 * i + 7 * attempt)
            say(progress=0.05 + 0.85 * (i + attempt / tries_max / 2) / total, step="speaking", chunk=i + 1, chunks=total,
                attempt=attempt + 1)
            g = {"cfg_value": cfg, "inference_timesteps": steps}
            if qwen:                            # Qwen3-TTS: the recording (and its words, when in the same writing)
                g = {"text": text, "reference_wav_path": str(ref_wav),
                     "prompt_text": ref_text if job.get("qwen_icl", True) else ""}
            elif ref_wav:                       # the locked voice: its own recording and words
                g.update(text=_said(text), reference_wav_path=str(ref_wav))
                if ref_text:
                    g.update(prompt_wav_path=str(ref_wav), prompt_text=ref_text)
                elif voice.get("style"):
                    g["text"] = "(" + voice["style"] + ")" + _said(text)
            else:                               # a voice from a description (the first chunk; the rest copy it)
                g["text"] = ("(" + voice["description"] + ")" if voice.get("description") else "") + _said(text)
            t1 = time.time()
            try:
                y = np.asarray(model.generate(**g), dtype="float32").reshape(-1)
            except Exception as exc:              # the graphics card fails while speaking (memory, an unsupported card)
                if dev != "cuda":
                    raise
                say(progress=0.05, step="loading", device="cpu", note=f"graphics card: {type(exc).__name__}: {str(exc)[:200]}")
                model = None
                import gc
                gc.collect()
                torch.cuda.empty_cache()
                dev, steps = "cpu", min(steps, 10)
                if not qwen:
                    g["inference_timesteps"] = steps
                model = load(dev)
                y = np.asarray(model.generate(**g), dtype="float32").reshape(-1)
            gen_s = time.time() - t1
            if qwen:                            # its rate as it says it (24 kHz)
                sr = int(model.sample_rate)
            y = _trim(y, sr)
            p = out_dir / f"chunk_{i + 1:03d}_try{attempt + 1}.wav"
            sf.write(str(p), y, sr)
            said, _w, _lang = _listen(asr, str(p), job.get("language"))
            errs = word_errors(text, said)
            n = max(1, len(_words(text)))
            off = 0.0
            if ref_wav:
                try:
                    if not ref_hz:
                        ry, rsr = sf.read(str(ref_wav), dtype="float32", always_2d=True)
                        ref_hz = _pitch(ry.mean(axis=1), rsr) or -1.0
                    hz = _pitch(y, sr) if ref_hz > 0 else 0.0
                    off = abs(12 * float(np.log2(hz / ref_hz))) if hz > 0 and ref_hz > 0 else 0.0
                except Exception:
                    off = 0.0                      # (no pitch check rather than no voice)
            row = {"chunk": i + 1, "attempt": attempt + 1, "seconds": round(y.size / sr, 2), "make_s": round(gen_s, 1),
                   "said": said, "word_errors": errs, "words": n, "file": p.name, "pitch_off_st": round(off, 2)}
            ok_words = errs <= max(0, n // 25)    # every word (or almost: 1 in 25) is there
            score = (not ok_words, errs, off > PITCH_OFF_ST, off)
            if best is None or score < best["_score"]:
                best = row | {"audio": y, "_score": score}
            if ok_words and off <= PITCH_OFF_ST:   # and the voice is its own height
                break
            if ok_words and attempt >= 2:          # words right twice over: the closest height is good enough
                break
        report.append({k: v for k, v in best.items() if k not in ("audio", "_score")})
        pieces.append((best["audio"], ch.get("pause_after", 0.35)))
        if not ref_wav and voice.get("lock_after_first", True) and i == 0 and total > 1:
            ref_wav, ref_text = str(out_dir / best["file"]), text     # one voice for the whole text
    say(progress=0.92, step="joining")
    parts = []
    for y, pause in pieces:
        parts += [y, np.zeros(int(sr * float(pause)), dtype="float32")]
    full = np.concatenate([np.zeros(int(sr * 0.15), dtype="float32")] + parts) if parts else np.zeros(sr, dtype="float32")
    peak = float(np.max(np.abs(full)) or 1.0)
    if peak > 0.99:
        full = full / peak * 0.99
    sf.write(job["out_wav"], full, sr)
    say(progress=0.95, step="listening")
    said, words, lang = _listen(asr, job["out_wav"], job.get("language"))
    return {"ok": True, "device": dev, "sample_rate": sr, "seconds": round(full.size / sr, 2), "load_s": round(load_s, 1),
            "said": said, "words": words, "language": lang, "chunks": report, "steps": None if qwen else steps,
            "cfg": None if qwen else cfg, "engine": "qwen" if qwen else "voxcpm",
            "word_errors": word_errors(" ".join(c["text"] for c in chunks), said)}


def transcribe(job: dict) -> dict:
    src, wav = job["source"], job["wav16"]
    say(progress=0.05, step="reading")
    # the first sound track (the one a clip of the video keeps), its gaps filled with silence: the words' times are the
    # video's times even when the recording lost some sound (a stream, OBS)
    cp = subprocess.run([job["ffmpeg"], "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", src, "-vn", "-map", "0:a:0",
                         "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
                        capture_output=True, text=True, errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if cp.returncode != 0 or not Path(wav).is_file():
        return {"ok": False, "error": "The sound could not be read: " + (cp.stderr.strip().splitlines() or ["?"])[-1][:200]}
    say(progress=0.2, step="listening")
    asr = _whisper(job)
    total = float(job.get("duration") or 0)
    parts = _pieces(wav, float(job.get("piece_s") or 0))
    if len(parts) == 1:
        said, words, lang = _listen(asr, wav, job.get("language"), total)
        return {"ok": True, "said": said, "words": words, "language": lang}
    import wave
    words, lang = [], job.get("language") or None
    piece = str(Path(wav).with_name("piece.wav"))
    with wave.open(wav, "rb") as f:
        rate, width, ch = f.getframerate(), f.getsampwidth(), f.getnchannels()
        for a, b in parts:
            f.setpos(int(a * rate))
            with wave.open(piece, "wb") as g:
                g.setnchannels(ch); g.setsampwidth(width); g.setframerate(rate)
                g.writeframes(f.readframes(int((b - a) * rate)))
            _said, w, heard_lang = _listen(asr, piece, lang, total or parts[-1][1], offset=a)
            lang = lang or heard_lang or None              # (the language heard in the first piece, kept for the rest)
            words += w
    Path(piece).unlink(missing_ok=True)
    return {"ok": True, "said": " ".join(x["w"] for x in words), "words": words, "language": lang or ""}


def selftest(job: dict) -> dict:
    import torch, librosa, soundfile  # noqa: F401
    from importlib import metadata
    if job.get("engine") == "qwen":              # the new engine's folder first: its whole model code imports
        from qwen_tts import Qwen3TTSModel  # noqa: F401
        from faster_whisper import WhisperModel  # noqa: F401
        return {"ok": True, "torch": torch.__version__, "qwen_tts": metadata.version("qwen-tts"),
                "transformers": metadata.version("transformers")}
    from voxcpm import VoxCPM  # noqa: F401          (the whole model code, not only the package name)
    from faster_whisper import WhisperModel  # noqa: F401
    cuda = bool(torch.cuda.is_available())
    note = ""
    if cuda:
        try:                                     # a card torch sees but cannot compute on (no kernels for it)
            x = torch.ones(256, 256, device="cuda", dtype=torch.bfloat16)
            float((x @ x).float().sum().item())
        except Exception as exc:
            cuda, note = False, f"{type(exc).__name__}: {str(exc)[:200]}"
    return {"ok": True, "torch": torch.__version__, "cuda": cuda, "cuda_note": note,
            "gpu": torch.cuda.get_device_name(0) if cuda else "",
            "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 2 ** 30, 1) if cuda else 0,
            "voxcpm": metadata.version("voxcpm"), "faster_whisper": metadata.version("faster-whisper")}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Cyrillic words and paths, whatever the code page
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    job = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    site.addsitedir(job["site"])
    if job.get("engine") == "qwen" and job.get("site_qwen"):   # its own versions (transformers 4.57) win
        site.addsitedir(job["site_qwen"])
        q = os.path.normcase(os.path.abspath(job["site_qwen"]))
        sys.path[:] = [job["site_qwen"]] + [x for x in sys.path if os.path.normcase(os.path.abspath(x)) != q]
    os.environ.setdefault("HF_HUB_OFFLINE", "1")              # the models are on disk; the worker never goes online
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    try:
        res = {"tts": tts, "transcribe": transcribe, "selftest": selftest}[job["task"]](job)
    except Exception as exc:
        res = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500], "trace": traceback.format_exc()[-4000:]}
    say(result=res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

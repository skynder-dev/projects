"""MediaEngine voice-over worker: runs in its own Python process with ONLY the voice add-on's packages.

  python -S -E -B voice_worker.py <job.json>

Started by voice.py with the program's own Python 3.11 but without its site-packages (-S): the add-on brings its own
torch / VoxCPM2 / faster-whisper (DATA\\addons\\voice\\site) and must never mix with the program's pinned packages.
Prints one JSON object per line on stdout ({"progress": 0.4, "step": "..."}, then {"result": {...}}); writes the
files the job names. Only standard library imports at the top: the add-on folder is added first.

Tasks:
  tts         text (in chunks) -> one WAV in one voice; every chunk is listened to (faster-whisper) and made again
              (up to 2 more times) when words are missing
  transcribe  a sound / video file -> the words said with their times (for captions)
  selftest    the add-on loads and sees the GPU (no model run)
"""
from __future__ import annotations

import json, os, re, site, subprocess, sys, time, traceback
from pathlib import Path


def say(**kw) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _words(s: str) -> list[str]:
    s = re.sub(r"\([^)]*\)|\[[a-z ]+\]", " ", str(s).lower().replace("’", "'"))
    return re.findall(r"[\w']+", s)


_NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
        "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve"}


def word_errors(ref: str, said: str) -> int:
    """Word edit distance between the text and what was really said (a spoken "ten" written "10" is not an error)."""
    a, b = _words(ref), [_NUM.get(w, w) for w in _words(said)]
    a = [_NUM.get(w, w) for w in a]
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


def _listen(asr, wav: str, language: str | None) -> tuple[str, list[dict], str]:
    segs, info = asr.transcribe(wav, language=language or None, word_timestamps=True, vad_filter=True, beam_size=5)
    words = []
    for s in segs:
        for w in (s.words or []):
            words.append({"w": w.word.strip(), "s": round(float(w.start), 3), "e": round(float(w.end), 3),
                          "p": round(float(getattr(w, "probability", 0) or 0), 3)})
    return " ".join(w["w"] for w in words), words, getattr(info, "language", "") or ""


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


def tts(job: dict) -> dict:
    import numpy as np, soundfile as sf, torch
    # (torch's own thread count: the program's OMP_NUM_THREADS=2 is not passed to the worker; setting one less than all
    #  cores made a CPU voice 4x slower on a 4-core runner - runs 39247474464 vs 39251509089)
    _patch_torchaudio()
    from voxcpm import VoxCPM
    dev = _device(job)
    say(progress=0.02, step="loading", device=dev)
    t0 = time.time()
    def load(device):
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
    tries_max = 3
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
            if ref_wav:                         # the locked voice: its own recording and words
                g.update(text=text, reference_wav_path=str(ref_wav))
                if ref_text:
                    g.update(prompt_wav_path=str(ref_wav), prompt_text=ref_text)
                elif voice.get("style"):
                    g["text"] = "(" + voice["style"] + ")" + text
            else:                               # a voice from a description (the first chunk; the rest copy it)
                g["text"] = ("(" + voice["description"] + ")" if voice.get("description") else "") + text
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
                g["inference_timesteps"] = steps
                model = load(dev)
                y = np.asarray(model.generate(**g), dtype="float32").reshape(-1)
            gen_s = time.time() - t1
            y = _trim(y, sr)
            p = out_dir / f"chunk_{i + 1:03d}_try{attempt + 1}.wav"
            sf.write(str(p), y, sr)
            said, _w, _lang = _listen(asr, str(p), job.get("language"))
            errs = word_errors(text, said)
            n = max(1, len(_words(text)))
            row = {"chunk": i + 1, "attempt": attempt + 1, "seconds": round(y.size / sr, 2), "make_s": round(gen_s, 1),
                   "said": said, "word_errors": errs, "words": n, "file": p.name}
            if best is None or errs < best["word_errors"]:
                best = row | {"audio": y}
            if errs <= max(0, n // 25):          # every word (or almost: 1 in 25) is there
                break
        report.append({k: v for k, v in best.items() if k != "audio"})
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
            "said": said, "words": words, "language": lang, "chunks": report, "steps": steps, "cfg": cfg,
            "word_errors": word_errors(" ".join(c["text"] for c in chunks), said)}


def transcribe(job: dict) -> dict:
    src, wav = job["source"], job["wav16"]
    say(progress=0.05, step="reading")
    cp = subprocess.run([job["ffmpeg"], "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1",
                         "-ar", "16000", "-c:a", "pcm_s16le", wav], capture_output=True, text=True, errors="replace",
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if cp.returncode != 0 or not Path(wav).is_file():
        return {"ok": False, "error": "The sound could not be read: " + (cp.stderr.strip().splitlines() or ["?"])[-1][:200]}
    say(progress=0.2, step="listening")
    asr = _whisper(job)
    said, words, lang = _listen(asr, wav, job.get("language"))
    return {"ok": True, "said": said, "words": words, "language": lang}


def selftest(job: dict) -> dict:
    import torch, librosa, soundfile  # noqa: F401
    from voxcpm import VoxCPM  # noqa: F401          (the whole model code, not only the package name)
    from faster_whisper import WhisperModel  # noqa: F401
    from importlib import metadata
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

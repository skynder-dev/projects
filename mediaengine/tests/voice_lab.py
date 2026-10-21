"""Voice lab: free local voice-over engines side by side, before any of them goes into MediaEngine.

One English test text, one female American voice, several engines and settings. Every take is checked by machine
(what was actually said - faster-whisper; how high the voice is - pitch; how long) and the better of two takes
by those checks is kept. The owner then listens blind (letters A, B, C ...) and picks; only the pick goes into
MediaEngine. Nothing here is the product: it decides which engine the product uses.

  python voice_lab.py kokoro    <out>              (Kokoro-82M af_heart - the voice the owner found flat; reference)
  python voice_lab.py qwen      <out>              (Qwen3-TTS VoiceDesign: a voice from a description; the locked voice)
  python voice_lab.py chatterbox <out> [<ref.wav>] (Chatterbox: built-in voice, and the locked voice from qwen)
  python voice_lab.py check     <in> <out>         (word check, pitch, loudness, blind letters, results)

Round 1 (run 39197836516, branch mediaengine-voice-lab latest/): the owner kept B (Chatterbox built-in voice),
D (Qwen Base, locked voice) and E (Chatterbox, locked voice) - "still feels like AI, but good intonations"; rejected
A (Qwen VoiceDesign upbeat), C (VoiceDesign warm: "too sexy") and F (Kokoro). Round 2 aims at "less like AI":

  python voice_lab.py turbo  <out> <ref.wav>      (Chatterbox Turbo, locked voice, a [chuckle] tag)
  python voice_lab.py voxcpm <out> <ref.wav>      (VoxCPM2, 48 kHz, locked voice)
  python voice_lab.py round2 <in> <out>           (the very takes B, D, E he heard + the two new engines, all with
                                                   the same voice-over finishing; blind letters G-K)

Round 2 (run 39209510581): "they are so alike - I thought you would work on the voices, you just put random music".
He was right (three of five were round 1's very takes). Round 3 works on the voice itself (see SPOKEN below):

  python voice_lab.py vox3   <out> <voice_b.wav>   (VoxCPM2: two designed characters + voice B, directed)
  python voice_lab.py cb3    <out> <voice_de.wav>  (Chatterbox: voice B on the spoken script; Turbo: voice D/E)
  python voice_lab.py round3 <in> <out>            (word check against the spoken script, best take, voice3_N.mp3)

Round 3 verdict: only 3.1 (VoxCPM2 designed "friend") is worth working on. Round 4 improves it:

  python voice_lab.py vox4a  <out> <3.1.wav>       (3.1 at 30 steps; sharper direction; 3.1's voice on a new text)
  python voice_lab.py vox4b  <out>                 (six takes of the sharper direction)
  python voice_lab.py round4 <in> <out> <branch>   (UTMOS checked against his verdicts, best take, voice4_N.mp3)

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


def _kwargs_that_fit(fn, wanted: dict) -> dict:
    import inspect
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return wanted
    if any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return wanted
    return {k: v for k, v in wanted.items() if k in params}


TURBO_TEXT = TEXT.replace("honestly? It", "honestly? [chuckle] It")


def turbo(out: Path, ref: Path) -> None:
    _threads()
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    try:
        m = ChatterboxTurboTTS.from_pretrained(device="cpu")
    except Exception as exc:          # its loader may insist on a Hugging Face token; the model is public
        _log(f"from_pretrained failed ({exc}); downloading the public files without a token")
        from huggingface_hub import snapshot_download
        m = ChatterboxTurboTTS.from_local(snapshot_download("ResembleAI/chatterbox-turbo", token=False), "cpu")
    _api_dump(out, m, "turbo")

    def make(take):
        torch.manual_seed(600 + take)
        return m.generate(TURBO_TEXT, **_kwargs_that_fit(m.generate, {"audio_prompt_path": str(ref)})), m.sr

    for take in TAKES:
        _take(out, "turbo_locked", take, make)


def voxcpm(out: Path, ref: Path) -> None:
    """VoxCPM2 (2B, 48 kHz, Apache-2.0; ~8 GB on a GPU): 'ultimate cloning' - the reference clip, its exact words and
    the same clip as the timbre reference, as its model card advises for the closest voice."""
    _threads()
    import torch
    from voxcpm import VoxCPM
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", **_kwargs_that_fit(
        VoxCPM.from_pretrained, {"load_denoiser": False, "optimize": False, "device": "cpu"}))
    _api_dump(out, m, "voxcpm")
    sr = int(getattr(getattr(m, "tts_model", None), "sample_rate", 0) or getattr(m, "sample_rate", 0) or 48000)

    def make(take):
        torch.manual_seed(700 + take)
        return m.generate(text=TEXT, prompt_wav_path=str(ref), prompt_text=REF_TEXT, reference_wav_path=str(ref),
                          cfg_value=2.0, inference_timesteps=10), sr

    for take in TAKES:
        _take(out, "voxcpm_locked", take, make)


# ---------------------------------------------------------------------------------------------------------- check

def _words(s: str) -> list[str]:
    """Words of a text, any alphabet (Russian included; rounds before 14 checked Russian words as none)."""
    s = s.lower().replace("’", "'").replace("ё", "е")
    return [w.strip("'") for w in re.findall(r"[^\W_]+(?:'[^\W_]+)*", s) if w.strip("'")]


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


_NUMBERS = {"10": "ten", "3": "three"}       # the checker writes "10" for a spoken "ten": not a wrong word


def _analyze(asr, wav: Path, src: Path, gen: dict, text: str = TEXT, language: str = "en") -> dict:
    """What a take really says (faster-whisper), how long it is, how high the voice is and how much it moves."""
    import numpy as np, librosa
    name = wav.stem
    ref_words = _words(re.sub(r"\[[a-z ]+\]|\([^)]*\)", " ", text))
    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    dur = len(y) / sr
    segs, _ = asr.transcribe(str(wav), language=language, beam_size=5, vad_filter=True)
    said = " ".join(s.text.strip() for s in segs)
    dist, missing, extra = _diff(ref_words, [_NUMBERS.get(w, w) for w in _words(said)])
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
    _log(f"{name}: {dur:.1f} s, {dist} word errors, pitch {med:.0f} Hz +-{semis:.1f} st")
    return info


FINISHING = ("voice-over finishing: silence trimmed (0.25 s lead, 0.6 s tail), high-pass 70 Hz, a small dark room "
             "mixed 20 dB under the voice, a faint room tone 55 dB under it instead of digital silence, gentle "
             "compression (2.5:1), de-essing, loudness -16 LUFS, 44.1 kHz")


def produce(wav: Path, mp3: Path, seed: int, music: Path | None = None, music_mp3: Path | None = None) -> None:
    """The same finishing for every voice: a voice in a room, not in a vacuum."""
    import numpy as np, librosa, soundfile as sf
    from scipy.signal import butter, sosfilt, fftconvolve
    sr = 44100
    y, _ = librosa.load(str(wav), sr=sr, mono=True)
    y, _ = librosa.effects.trim(y, top_db=45, frame_length=1024, hop_length=256)
    y = np.concatenate([np.zeros(int(0.25 * sr)), y, np.zeros(int(0.6 * sr))])
    y = sosfilt(butter(2, 70, btype="highpass", fs=sr, output="sos"), y)
    rng = np.random.default_rng(seed)

    def rms(a):
        return float(np.sqrt(np.mean(np.square(a)))) or 1e-9

    n = int(0.3 * sr)                                      # small room: a dark diffuse tail, -60 dB after 0.3 s
    t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / 0.3)
    ir[: int(0.004 * sr)] = 0.0
    ir = sosfilt(butter(2, 5000, btype="lowpass", fs=sr, output="sos"), ir)
    wet = fftconvolve(y, ir)[: len(y)]
    y = y + wet * (rms(y) / rms(wet)) * 10 ** (-20 / 20)
    tone = sosfilt(butter(2, [120, 4000], btype="bandpass", fs=sr, output="sos"), rng.standard_normal(len(y)))
    y = y + tone * (rms(y) / rms(tone)) * 10 ** (-55 / 20)
    y = y / (np.max(np.abs(y)) or 1.0) * 0.7
    tmp = mp3.with_suffix(".finished.wav")
    sf.write(str(tmp), y.astype("float32"), sr)
    voice_chain = "acompressor=threshold=-21dB:ratio=2.5:attack=8:release=120:makeup=1.5,deesser=i=0.4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", voice_chain + ",loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-ar", "44100", "-ac", "1", "-b:a", "192k", str(mp3)], check=True)
    if music is not None and music_mp3 is not None:
        dur = len(y) / sr + 1.0                            # the music starts 1 s before the voice, ends 1.5 s after
        fc = (f"[1:a]atrim=start={MUSIC_START_S},asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=mono,"
              f"volume=-13dB,afade=t=in:d=0.6[m];"
              f"[0:a]{voice_chain},adelay=1000,apad=pad_dur=1.5,asplit=2[v][sc];"
              f"[m][sc]sidechaincompress=threshold=0.03:ratio=4:attack=30:release=400[md];"
              f"[v][md]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={dur:.2f}:d=1.5,"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[out]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(music), "-filter_complex", fc,
                        "-map", "[out]", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(music_mp3)], check=True)
    tmp.unlink()


MUSIC = {"title": "File:Flutey Funk (ISRC USUAN1100519).mp3", "author": "Kevin MacLeod (incompetech.com)",
         "licence": "CC BY 3.0", "page": "https://commons.wikimedia.org/wiki/File:Flutey_Funk_(ISRC_USUAN1100519).mp3"}
MUSIC_START_S = 2.0
_UA = {"User-Agent": "MediaEngine-voice-lab/1.0 (https://github.com/skynder-dev/projects; CI test, no reuse)"}


def fetch_music(dst: Path) -> Path:
    """A free-licence instrumental from Wikimedia Commons (the reels' usual case: a voice over music). SHA-1 checked."""
    import hashlib, urllib.parse, urllib.request
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2", "titles": MUSIC["title"],
                                "prop": "imageinfo", "iiprop": "url|sha1"})
    with urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + q, headers=_UA),
                                timeout=60) as r:
        info = json.load(r)["query"]["pages"][0]["imageinfo"][0]
    with urllib.request.urlopen(urllib.request.Request(info["url"], headers=_UA), timeout=180) as r:
        data = r.read()
    if hashlib.sha1(data).hexdigest() != info["sha1"]:
        raise RuntimeError("music file does not match Commons' SHA-1")
    dst.write_bytes(data)
    return dst


ROUND2 = {   # round 1's very takes the owner kept (results.json of run 39197836516), then the new engines
    "chatterbox_builtin": ("chatterbox_builtin_t2", "B of round 1: Chatterbox built-in voice, exaggeration 0.7, cfg 0.3"),
    "qwen_locked": ("qwen_locked_t1", "D of round 1: Qwen3-TTS 1.7B Base, the locked designed voice"),
    "chatterbox_locked": ("chatterbox_locked_t1", "E of round 1: Chatterbox, the locked designed voice"),
    "turbo_locked": (None, "Chatterbox Turbo, the locked designed voice, a [chuckle] after 'honestly?'"),
    "voxcpm_locked": (None, "VoxCPM2 (2B, 48 kHz), the locked designed voice (ultimate cloning)"),
}


def round2(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    wavs = {w.stem: w for w in src.rglob("*_t[0-9].wav")}
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    chosen, takes = {}, {}
    for v, (fixed, what) in ROUND2.items():
        names = [fixed] if fixed else sorted(n for n in wavs if n.rsplit("_t", 1)[0] == v)
        for n in names:
            if n in wavs:
                takes[n] = _analyze(asr, wavs[n], src, gen)
        have = [takes[n] for n in names if n in takes]
        if have:
            chosen[v] = dict(min(have, key=lambda i: (i["word_errors"], i.get("take", 9))), what=what)
    order = [v for v in ROUND2 if v in chosen]
    shuffled = order[:]
    random.Random(2027).shuffle(shuffled)
    blind = {"GHIJK"[i]: v for i, v in enumerate(shuffled)}
    music = None
    try:
        music = fetch_music(out.parent / "music.mp3")
    except Exception as exc:
        _log(f"no music ({exc}): voice-only files only")
    for i, (letter, v) in enumerate(blind.items()):
        produce(src / chosen[v]["file"], out / f"voice_{letter}.mp3", 900 + i, music, out / f"music_{letter}.mp3")
        chosen[v]["letter"] = letter
    failed = {k: v.get("error") for k, v in gen.items() if v.get("error") and k.rsplit("_t", 1)[0] in ROUND2}
    res = {"round": 2, "text": TEXT, "turbo_text": TURBO_TEXT, "finishing": FINISHING, "blind": blind,
           "variants": chosen, "missing_variants": [v for v in ROUND2 if v not in chosen], "failed_takes": failed,
           "all_takes": takes, "licenses": {**LICENSES, "voxcpm": "VoxCPM2: Apache-2.0"},
           "round1": "branch mediaengine-voice-lab latest/ (run 39197836516)",
           "music": {**MUSIC, "used": music is not None, "mix": "starts 1 s before the voice, 13 dB down and ducked "
                     "under the voice, fades out 1.5 s after it; whole mix -14 LUFS"}}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 2 (less like AI)", "", f"Text: {TEXT}", "", f"Every file: {FINISHING}.", "",
          "| letter | words wrong | seconds | pitch Hz | pitch moves (semitones) |", "|---|---|---|---|---|"]
    for letter, v in sorted(blind.items()):
        b = chosen[v]
        md.append(f"| {letter} | {b['word_errors']} | {b['seconds']} | {b['pitch_median_hz']} | {b['pitch_movement_semitones']} |")
    md += ["", "music_<letter>.mp3: the same voice over music - " + f"{MUSIC['title'][5:]} by {MUSIC['author']}, "
           f"{MUSIC['licence']} ({MUSIC['page']}).", "", "Which letter is which: results.json -> blind."]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {str(e).splitlines()[0][:300]}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"made": len(order), "of": len(ROUND2), "failed_takes": len(failed)}))
    return 0 if len(order) >= 3 else 1


# ---------------------------------------------------------------------------------------------------------- round 3
# Round 2 was too alike (three of five were round 1's very takes, all one voice) and only the sound was finished, not
# the voice. Round 3 works on the voice itself: a script written to be SAID (pauses, "like", "seriously" - the same
# message), distinct characters, direction (VoxCPM2 takes a style note; Turbo a [chuckle]), no music.

SPOKEN = ("Okay... so here's something nobody tells you about packing for a beach trip. "
          "You don't need ten outfits. Seriously. You need, like, three. And one really good hat. "
          "We tried it last summer and, honestly? It changed everything. "
          "Less stuff... more time in the water. So, would you try it? Tell me in the comments!")
SPOKEN_TURBO = SPOKEN.replace("honestly? It", "honestly? [chuckle] It")
FRIEND = ("(A friendly American woman in her late twenties with a clear, natural everyday voice, medium pitch, not breathy, "
          "telling her best friend a little secret: casual, playful, a bit amused, relaxed pace, real pauses)")
VLOGGER = ("(A confident American travel vlogger in her early thirties, medium pitch, bright but natural, talking straight "
           "to the camera: expressive, quick but clear, a smile in her voice, never shouting)")
CASUAL = "(Casual and playful, a bit amused, like talking to a good friend, relaxed pace, real pauses)"
ROUND3 = {
    "vox_friend": "VoxCPM2: a new voice from a description - a friend telling a little secret",
    "vox_vlogger": "VoxCPM2: a new voice from a description - a travel vlogger talking to the camera",
    "vox_voice_b": "VoxCPM2: voice B of round 1, directed 'casual, playful, like talking to a good friend'",
    "chatterbox_b_spoken": "Chatterbox: voice B of round 1 itself on the spoken script (exaggeration 0.6, cfg 0.35)",
    "turbo_de_spoken": "Chatterbox Turbo: voice D/E of round 1 on the spoken script, a [chuckle] after 'honestly?'",
}


def vox3(out: Path, ref_b: Path) -> None:
    _threads()
    import torch
    from voxcpm import VoxCPM
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", **_kwargs_that_fit(
        VoxCPM.from_pretrained, {"load_denoiser": False, "optimize": False, "device": "cpu"}))
    sr = int(getattr(getattr(m, "tts_model", None), "sample_rate", 0) or 48000)

    def make(seed, text, **kw):
        torch.manual_seed(seed)
        return m.generate(text=text, cfg_value=2.0, inference_timesteps=10, **kw), sr

    for take in TAKES:
        _take(out, "vox_friend", take, lambda t: make(800 + t, FRIEND + SPOKEN))
        _take(out, "vox_vlogger", take, lambda t: make(810 + t, VLOGGER + SPOKEN))
        if ref_b.exists():
            _take(out, "vox_voice_b", take, lambda t: make(820 + t, CASUAL + SPOKEN, reference_wav_path=str(ref_b)))


def cb3(out: Path, ref_de: Path) -> None:
    _threads()
    import torch
    from chatterbox.tts import ChatterboxTTS
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    m = ChatterboxTTS.from_pretrained(device="cpu")
    for take in TAKES:
        _take(out, "chatterbox_b_spoken", take, lambda t: (torch.manual_seed(830 + t), (
            m.generate(SPOKEN, exaggeration=0.6, cfg_weight=0.35, temperature=0.85), m.sr))[1])
    del m
    gc.collect()
    tm = ChatterboxTurboTTS.from_pretrained(device="cpu")
    for take in TAKES:
        _take(out, "turbo_de_spoken", take, lambda t: (torch.manual_seed(840 + t), (
            tm.generate(SPOKEN_TURBO, audio_prompt_path=str(ref_de)), tm.sr))[1])


def round3(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    wavs = {w.stem: w for w in src.rglob("*_t[0-9].wav") if w.stem.rsplit("_t", 1)[0] in ROUND3}
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes, chosen = {}, {}
    for n, w in sorted(wavs.items()):
        takes[n] = _analyze(asr, w, src, gen, SPOKEN)
    for v, what in ROUND3.items():
        have = [i for n, i in takes.items() if n.rsplit("_t", 1)[0] == v]
        if have:
            chosen[v] = dict(min(have, key=lambda i: (i["word_errors"], i.get("take", 9))), what=what)
    for i, v in enumerate([v for v in ROUND3 if v in chosen], 1):
        produce(src / chosen[v]["file"], out / f"voice3_{i}.mp3", 950 + i)
        chosen[v]["file_sent"] = f"voice3_{i}.mp3"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items()
              if v.get("error") and k.rsplit("_t", 1)[0] in ROUND3}
    res = {"round": 3, "spoken_text": SPOKEN, "turbo_text": SPOKEN_TURBO, "directions": {"friend": FRIEND,
           "vlogger": VLOGGER, "casual": CASUAL}, "finishing": FINISHING, "variants": chosen, "failed_takes": failed,
           "all_takes": takes, "missing_variants": [v for v in ROUND3 if v not in chosen]}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 3 (the voice itself)", "", f"Spoken script: {SPOKEN}", "",
          "| file | what | words wrong | seconds | pitch Hz | pitch moves (st) |", "|---|---|---|---|---|---|"]
    for v, b in chosen.items():
        md.append(f"| {b['file_sent']} | {b['what']} | {b['word_errors']} | {b['seconds']} | {b['pitch_median_hz']} | "
                  f"{b['pitch_movement_semitones']} |")
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"made": len(chosen), "of": len(ROUND3), "failed_takes": len(failed)}))
    return 0 if len(chosen) >= 3 else 1


# ---------------------------------------------------------------------------------------------------------- round 4
# Round 3 verdict: 3.3 and 3.4 bad, 3.5 tolerable ("AI noticeable"), 3.1 (VoxCPM2 designed "friend with a secret")
# "interesting - intonation not bad, breaths and so on, but you can tell it is AI; can it be improved?". Round 4 works
# only on 3.1: more diffusion steps, a sharper direction, best of six takes by a naturalness predictor (UTMOS, checked
# against his earlier verdicts), the same take with and without a "microphone" finishing, and the 3.1 voice locked on
# a new text. Voice only, no music; finishing is loudness only unless the file says otherwise.

FRIEND2 = ("(A friendly American woman in her late twenties with a clear, natural everyday voice, medium pitch, not "
           "breathy, sending a voice message to her best friend: spontaneous and unscripted, casual, playful, a bit "
           "amused, relaxed pace, real pauses and small natural imperfections)")
NEW_TEXT = ("Hey, quick one. You know that feeling when you pack the night before... and still forget your charger? "
            "Yeah. Me too. So now I keep a tiny bag that never gets unpacked. Charger, sunscreen, snacks. Done. "
            "Honestly? Game changer.")
STEPS4 = 30
ROUND4 = {
    "r4_same_more_steps": ("3.1 again (same direction, same seed), 30 steps instead of 10", SPOKEN),
    "r4_direction_cfg16": ("3.1's character, sharper direction ('voice message, unscripted'), 30 steps, cfg 1.6", SPOKEN),
    "r4_best_of_six": ("sharper direction, 30 steps: the best of six takes by the naturalness predictor", SPOKEN),
    "r4_best_of_six_mic": ("the very same take as the best of six, with a 'microphone' finishing", SPOKEN),
    "r4_locked_new_text": ("3.1's own voice locked (ultimate cloning) on a new text, 30 steps", NEW_TEXT),
}


def _vox2(cpu_model=True):
    _threads()
    from voxcpm import VoxCPM
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", **_kwargs_that_fit(
        VoxCPM.from_pretrained, {"load_denoiser": False, "optimize": False, "device": "cpu"}))
    return m, int(getattr(getattr(m, "tts_model", None), "sample_rate", 0) or 48000)


def vox4a(out: Path, ref31: Path) -> None:
    import torch
    m, sr = _vox2()

    def make(seed, text, cfg=2.0, **kw):
        torch.manual_seed(seed)
        return m.generate(text=text, cfg_value=cfg, inference_timesteps=STEPS4, **kw), sr

    _take(out, "r4_same_more_steps", 1, lambda t: make(801, FRIEND + SPOKEN))     # 3.1 was seed 801, 10 steps
    _take(out, "r4_direction_cfg16", 1, lambda t: make(901, FRIEND2 + SPOKEN, cfg=1.6))
    for take in TAKES:
        _take(out, "r4_locked_new_text", take, lambda t: make(
            920 + t, NEW_TEXT, prompt_wav_path=str(ref31), prompt_text=SPOKEN, reference_wav_path=str(ref31)))


def vox4b(out: Path) -> None:
    import torch
    m, sr = _vox2()
    for take in range(1, 7):
        _take(out, "r4_best_of_six", take, lambda t: (torch.manual_seed(910 + t), (
            m.generate(text=FRIEND2 + SPOKEN, cfg_value=2.0, inference_timesteps=STEPS4), sr))[1])


def vox4one(out: Path, variant: str, take: int, ref31: Path) -> None:
    """One take of round 4 (each take is its own CI job, all in parallel: 30 steps on a CPU are slow)."""
    import torch
    m, sr = _vox2()
    seeds = {"r4_same_more_steps": 801, "r4_direction_cfg16": 901, "r4_best_of_six": 910, "r4_locked_new_text": 920}

    def make(t):
        torch.manual_seed(seeds[variant] + (0 if variant in ("r4_same_more_steps", "r4_direction_cfg16") else t))
        if variant == "r4_same_more_steps":
            return m.generate(text=FRIEND + SPOKEN, cfg_value=2.0, inference_timesteps=STEPS4), sr
        if variant == "r4_direction_cfg16":
            return m.generate(text=FRIEND2 + SPOKEN, cfg_value=1.6, inference_timesteps=STEPS4), sr
        if variant == "r4_best_of_six":
            return m.generate(text=FRIEND2 + SPOKEN, cfg_value=2.0, inference_timesteps=STEPS4), sr
        return m.generate(text=NEW_TEXT, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(ref31),
                          prompt_text=SPOKEN, reference_wav_path=str(ref31)), sr

    _take(out, variant, take, make)


def _utmos():
    """UTMOS22 (strong learner): a predictor of how natural speech sounds, 1-5 (the VoiceMOS 2022 winner)."""
    import torch
    return torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True)


def _mos(pred, wav: Path) -> float:
    import torch, librosa
    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    with torch.no_grad():
        return round(float(pred(torch.from_numpy(y).unsqueeze(0), 16000).item()), 3)


def produce_plain(wav: Path, mp3: Path) -> None:
    """Loudness only (-16 LUFS), silence at the ends trimmed: the model as it is."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:"
                    "start_threshold=-50dB,areverse,adelay=200,apad=pad_dur=0.5,loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "48000", "-ac", "1", "-b:a", "192k", str(mp3)], check=True)


MIC = ("'microphone' finishing: gentle roll-off above 11 kHz (where a neural vocoder's glassy sheen lives), a touch of "
       "tape-like saturation, a small room 24 dB under the voice, light compression, loudness -16 LUFS")


def produce_mic(wav: Path, mp3: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:"
                    "start_threshold=-50dB,areverse,adelay=200,apad=pad_dur=0.5,highpass=f=80,"
                    "lowpass=f=11000:p=1,asoftclip=type=tanh:threshold=0.9,"
                    "aecho=0.9:0.9:23|37|53:0.06|0.045|0.03,"
                    "acompressor=threshold=-22dB:ratio=2:attack=10:release=150:makeup=1.3,"
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", "-b:a", "192k", str(mp3)], check=True)


# the owner's verdicts on files he heard (to check the predictor against his ear before trusting it)
VERDICTS = {"latest/voice_A.mp3": "bad", "latest/voice_C.mp3": "bad (too sexy)", "latest/voice_F.mp3": "bad",
            "latest/voice_B.mp3": "good", "latest/voice_D.mp3": "good", "latest/voice_E.mp3": "good",
            "round3/voice3_3.mp3": "bad", "round3/voice3_4.mp3": "bad", "round3/voice3_5.mp3": "tolerable",
            "round3/voice3_1.mp3": "interesting (best)"}


def round4(src: Path, out: Path, branch: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    pred = _utmos()
    calib = {}
    for rel, verdict in VERDICTS.items():
        f = branch / rel
        if f.exists():
            calib[rel] = {"verdict": verdict, "utmos": _mos(pred, f)}
            _log(f"calibration {rel}: {verdict} -> UTMOS {calib[rel]['utmos']}")
    takes = {}
    for w in sorted(src.rglob("r4_*_t[0-9].wav")):
        v = w.stem.rsplit("_t", 1)[0]
        info = _analyze(asr, w, src, gen, ROUND4.get(v, ("", SPOKEN))[1])
        info["utmos"] = _mos(pred, w)
        takes[w.stem] = info
        _log(f"  {w.stem}: UTMOS {info['utmos']}")
    chosen = {}
    for v, (what, _text) in ROUND4.items():
        if v == "r4_best_of_six_mic":
            continue
        have = [i for n, i in takes.items() if n.rsplit("_t", 1)[0] == v]
        fit = [i for i in have if i["word_errors"] == 0 and 170 <= i["pitch_median_hz"] <= 320] or have
        if fit:
            chosen[v] = dict(max(fit, key=lambda i: i["utmos"]), what=what)
    if "r4_best_of_six" in chosen:
        chosen["r4_best_of_six_mic"] = dict(chosen["r4_best_of_six"], what=ROUND4["r4_best_of_six_mic"][0])
    files = {}
    for i, v in enumerate([v for v in ROUND4 if v in chosen], 1):
        mp3 = out / f"voice4_{i}.mp3"
        (produce_mic if v.endswith("_mic") else produce_plain)(src / chosen[v]["file"], mp3)
        chosen[v]["file_sent"] = mp3.name
        chosen[v]["utmos_sent_file"] = _mos(pred, mp3)
        files[mp3.name] = v
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items()
              if v.get("error") and k.startswith("r4_")}
    res = {"round": 4, "spoken_text": SPOKEN, "new_text": NEW_TEXT, "direction_3_1": FRIEND, "direction_r4": FRIEND2,
           "steps": STEPS4, "mic_finishing": MIC, "files": files, "variants": chosen, "all_takes": takes,
           "failed_takes": failed, "utmos_vs_owner": calib,
           "note": "UTMOS is a machine estimate of naturalness (1-5); it only helps pick among takes - the owner's ear decides."}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 4 (3.1 improved)", "", "| file | what | words wrong | seconds | pitch Hz | UTMOS |",
          "|---|---|---|---|---|---|"]
    for v, b in chosen.items():
        md.append(f"| {b['file_sent']} | {b['what']} | {b['word_errors']} | {b['seconds']} | {b['pitch_median_hz']} | "
                  f"{b.get('utmos_sent_file')} |")
    md += ["", "UTMOS against the owner's verdicts:", ""] + [f"- {k}: {c['verdict']} -> {c['utmos']}" for k, c in calib.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"made": len(chosen), "of": len(ROUND4), "failed_takes": len(failed)}))
    return 0 if len(chosen) >= 3 else 1


# ---------------------------------------------------------------------------------------------------------- round 5
# Round 4 verdict (2026-10-19 15:41): 4_1 and 3.1 "sound like sex - we don't need that", 4_5 (3.1 locked) "too squeaky,
# not for business info", 4_3 "too tired", 4_4 (the same take as 4_3 with the microphone finishing) "will do", 4_2
# "OK". Round 5: the voices of 4_2 and 4_4 locked (ultimate cloning of those very takes) on a business-info text,
# each plain and with the microphone finishing - the owner picks the program's default voice.

BUSINESS = ("Here's what you need to know this week. First, flights to Europe got almost twenty percent cheaper. "
            "Second, if you book before Friday, most airlines let you change the dates for free. "
            "And third, the best deals are on Tuesday and Wednesday. Save this, and send it to someone who's planning a trip.")
ROUND5_REFS = {"v42": "r4_direction_cfg16_t1.wav", "v44": "r4_best_of_six_t2.wav"}


def vox5one(out: Path, voice: str, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()

    def make(t):
        torch.manual_seed(1000 + 10 * list(ROUND5_REFS).index(voice) + t)
        return m.generate(text=BUSINESS, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(ref),
                          prompt_text=SPOKEN, reference_wav_path=str(ref)), sr

    _take(out, f"r5_{voice}", take, make)


def round5(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes, chosen = {}, {}
    for w in sorted(src.rglob("r5_*_t[0-9].wav")):
        takes[w.stem] = _analyze(asr, w, src, gen, BUSINESS)
    for voice in ROUND5_REFS:
        have = [i for n, i in takes.items() if n.startswith(f"r5_{voice}_t")]
        if have:
            chosen[voice] = min(have, key=lambda i: (i["word_errors"], i.get("take", 9)))
    files = {}
    n = 0
    for voice, label in (("v42", "the voice of 4_2"), ("v44", "the voice of 4_4")):
        if voice not in chosen:
            continue
        for mic in (False, True):
            n += 1
            mp3 = out / f"voice5_{n}.mp3"
            (produce_mic if mic else produce_plain)(src / chosen[voice]["file"], mp3)
            files[mp3.name] = f"{label}, {'microphone finishing' if mic else 'as made'}"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    res = {"round": 5, "text": BUSINESS, "files": files, "chosen": chosen, "all_takes": takes, "failed_takes": failed}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 5 (4_2 and 4_4 locked, business text)", "", f"Text: {BUSINESS}", ""]
    md += [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| voice | take | words wrong | seconds | pitch Hz |", "|---|---|---|---|---|"]
    md += [f"| {v} | {c.get('take')} | {c['word_errors']} | {c['seconds']} | {c['pitch_median_hz']} |" for v, c in chosen.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if len(files) >= 2 else 1


# ---------------------------------------------------------------------------------------------------------- round 7
# Round 5 verdict (2026-10-19 21:22): 5_1 / 5_2 (the voice of 4_2) "squeaky, but the talking itself is better than the
# others"; 4_4 "a low timbre, or something that makes the robot audible in the lows". A pitch shift of the finished
# sound (rubberband, sent as voice6_1..3 from the sandbox) was rejected at once: "as if drowned in a toilet". So round 7
# makes the MODEL itself say the business text lower in 4_2's voice, three ways (no shifting of the finished sound):
#   r7_ctrl_lower  - controllable cloning: 4_2's recording as the timbre, a style note asking for a lower, calmer voice
#   r7_low_ref     - ultimate cloning from 4_2's recording made 2 semitones lower (Praat PSOLA, formants kept) - the
#                    model continues from it in its own sound
#   r7_design_low  - 4_2's own recipe (its description, cfg 1.6, its seed) with "low-medium pitch, a warm voice"
# Target: about 215-235 Hz (4_2 is ~260 Hz, 4_4 ~205 Hz). Loudness finishing only.

LOWER = "(A slightly lower, warmer, calm voice; relaxed and natural, like telling a friend)"
FRIEND_LOW = FRIEND2.replace("medium pitch, not breathy", "low-medium pitch, a warm and slightly deep voice, not breathy")
ROUND7 = {
    "r7_ctrl_lower": "4_2's voice as the timbre, the model asked for a lower, calmer voice",
    "r7_low_ref": "4_2's voice continued from its recording made 2 semitones lower",
    "r7_design_low": "4_2's own recipe with a lower, warmer voice described",
}
SEMITONES_DOWN = 2.0


def lower_ref(ref: Path, out_wav: Path, semitones: float = SEMITONES_DOWN) -> dict:
    """The reference made lower by PSOLA (Praat 'Change gender', formant ratio 1: the same throat, a lower note)."""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(str(ref))
    med = call(call(snd, "To Pitch", 0.0, 75, 600), "Get quantile", 0, 0, 0.5, "Hertz")
    new = call(snd, "Change gender", 75, 600, 1.0, med * 2 ** (-semitones / 12), 1.0, 1.0)
    call(new, "Save as WAV file", str(out_wav))
    after = call(call(new, "To Pitch", 0.0, 75, 600), "Get quantile", 0, 0, 0.5, "Hertz")
    return {"median_before_hz": round(med, 1), "median_after_hz": round(after, 1)}


def vox7one(out: Path, variant: str, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()
    if variant == "r7_low_ref":
        low = out / "host_4_2_lower.wav"
        _record(out, "lowered_reference", lower_ref(ref, low))
    seed = {"r7_ctrl_lower": 1100, "r7_low_ref": 1110, "r7_design_low": 900}[variant]

    def make(t):
        torch.manual_seed(seed + t)          # r7_design_low take 1 = seed 901, 4_2's own
        if variant == "r7_ctrl_lower":
            return m.generate(text=LOWER + BUSINESS, cfg_value=2.0, inference_timesteps=STEPS4,
                              reference_wav_path=str(ref)), sr
        if variant == "r7_low_ref":
            return m.generate(text=BUSINESS, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(low),
                              prompt_text=SPOKEN, reference_wav_path=str(low)), sr
        return m.generate(text=FRIEND_LOW + BUSINESS, cfg_value=1.6, inference_timesteps=STEPS4), sr

    _take(out, variant, take, make)


def round7(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes, chosen, files = {}, {}, {}
    for w in sorted(src.rglob("r7_*_t[0-9].wav")):
        takes[w.stem] = _analyze(asr, w, src, gen, BUSINESS)

    def rank(i):                              # every word first, then a pitch in the target band, then take 1
        hz = i.get("pitch_median_hz") or 0
        return (i["word_errors"] > 2, 0 if 210 <= hz <= 240 else 1, abs(hz - 225), i.get("take", 9))
    for n, v in enumerate(ROUND7, 1):
        have = [i for k, i in takes.items() if k.startswith(f"{v}_t")]
        if not have:
            continue
        chosen[v] = min(have, key=rank)
        mp3 = out / f"voice7_{n}.mp3"
        produce_plain(src / chosen[v]["file"], mp3)
        files[mp3.name] = ROUND7[v]
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    res = {"round": 7, "text": BUSINESS, "files": files, "chosen": chosen, "all_takes": takes, "failed_takes": failed,
           "lowered_reference": gen.get("lowered_reference")}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 7 (4_2's way of talking, lower - made by the model, not shifted afterwards)", "",
          f"Text: {BUSINESS}", ""]
    md += [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| variant | take | words wrong | seconds | pitch Hz |", "|---|---|---|---|---|"]
    md += [f"| {v} | {i.get('take')} | {i['word_errors']} | {i['seconds']} | {i['pitch_median_hz']} |"
           for v, i in sorted(takes.items())]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 8
# Round 7 verdict (2026-10-19 23:16): 7_1 (4_2's timbre + a style note asking for a lower, calmer voice) "good but
# squeaky"; 7_2 (continued from a PSOLA-lowered recording) and 7_3 (4_2's recipe described lower) "robot voice". So
# only 7_1's way, pushed further, with more takes, and the lowest natural ones picked by pitch (target ~205-230 Hz;
# 7_1 was 237 Hz):
#   r8_ctrl    - 7_1's very way (4_2's timbre, the same note), new seeds
#   r8_calm    - 4_2's timbre, a stronger note: calm, lower, a little slower (excited talk goes up in pitch)
#   r8_from71  - 7_1 itself as the timbre, the same note again (one more step down, still made by the model)

CALM = ("(A calm, confident woman with a lower, warm voice, speaking a little slower and relaxed, like a friendly "
        "podcast host sharing a tip)")
ROUND8 = {
    "r8_ctrl": "7_1's way again (4_2's voice, asked for a lower, calmer voice), the lowest natural take",
    "r8_calm": "4_2's voice, asked for a calm, lower, a little slower voice, the lowest natural take",
    "r8_from71": "7_1 itself as the voice, asked once more for a lower, calmer voice, the lowest natural take",
}


def vox8one(out: Path, variant: str, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()
    seed = {"r8_ctrl": 1200, "r8_calm": 1300, "r8_from71": 1400}[variant]
    note = CALM if variant == "r8_calm" else LOWER

    def make(t):
        torch.manual_seed(seed + t)
        return m.generate(text=note + BUSINESS, cfg_value=2.0, inference_timesteps=STEPS4, reference_wav_path=str(ref)), sr

    _take(out, variant, take, make)


def round8(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes, chosen, files = {}, {}, {}
    for w in sorted(src.rglob("r8_*_t[0-9].wav")):
        takes[w.stem] = _analyze(asr, w, src, gen, BUSINESS)

    def rank(i):        # every word; a natural pitch movement (not a squeal); as low as possible within 200-232 Hz
        hz = i.get("pitch_median_hz") or 0
        return (i["word_errors"] > 2, i.get("pitch_movement_semitones", 9) > 5.5, 0 if 200 <= hz <= 232 else 1, hz,
                i.get("take", 9))
    for n, v in enumerate(ROUND8, 1):
        have = [i for k, i in takes.items() if k.startswith(f"{v}_t")]
        if not have:
            continue
        chosen[v] = min(have, key=rank)
        mp3 = out / f"voice8_{n}.mp3"
        produce_plain(src / chosen[v]["file"], mp3)
        files[mp3.name] = ROUND8[v]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src / chosen[v]["file"]), "-c:a", "flac",   # the take
                        "-compression_level", "8", str(out / f"voice8_{n}.flac")], check=True)  # as the program's voice
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    res = {"round": 8, "text": BUSINESS, "files": files, "chosen": chosen, "all_takes": takes, "failed_takes": failed}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 8 (7_1's way, lower)", "", f"Text: {BUSINESS}", ""]
    md += [f"- {k}: {v} ({chosen[list(ROUND8)[int(k[7]) - 1]]['file']})" for k, v in files.items()]
    md += ["", "| take | words wrong | seconds | pitch Hz | pitch moves (st) |", "|---|---|---|---|---|"]
    md += [f"| {k} | {i['word_errors']} | {i['seconds']} | {i['pitch_median_hz']} | {i['pitch_movement_semitones']} |"
           for k, i in sorted(takes.items())]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 9
# Round 8 (run 39368973655): 14 more takes of 7_1's way all landed at 237-280 Hz - the model does not take 4_2's timbre
# lower without the robot sound, so they were not sent. Round 9: 4_2's own recipe (its description and cfg 1.6 - "the
# talking itself is better than the others") with other seeds = other women's voices, some naturally lower; the three
# lowest natural ones (all words, 200-232 Hz, a natural pitch movement) are sent. Also checked (not sent): 7_1 locked
# the program's way (ultimate cloning of 7_1's very recording) on another text keeps 7_1's pitch.

BUSINESS2 = ("Quick update for anyone planning a summer trip. Hotel prices usually drop about three weeks before the "
             "date, so don't book too early. And if a price looks too good, check the reviews first. Follow for more tips "
             "like this.")


def vox9one(out: Path, variant: str, take: int, ref: Path | None) -> None:
    import torch
    m, sr = _vox2()

    def make(t):
        if variant == "r9_design":
            torch.manual_seed(1500 + t)
            return m.generate(text=FRIEND2 + BUSINESS, cfg_value=1.6, inference_timesteps=STEPS4), sr
        torch.manual_seed(1600 + t)                       # r9_lock71: the program's way of keeping a voice
        return m.generate(text=BUSINESS2, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(ref),
                          prompt_text=BUSINESS, reference_wav_path=str(ref)), sr

    _take(out, variant, take, make)


def round9(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes = {}
    for w in sorted(src.rglob("r9_design_t*.wav")):
        takes[w.stem] = _analyze(asr, w, src, gen, BUSINESS)
    for w in sorted(src.rglob("r9_lock71_t*.wav")):
        takes[w.stem] = _analyze(asr, w, src, gen, BUSINESS2)
    design = [i for k, i in takes.items() if k.startswith("r9_design_t")]
    ok = [i for i in design if i["word_errors"] <= 2 and i.get("pitch_movement_semitones", 9) <= 5.5
          and 195 <= (i.get("pitch_median_hz") or 0) <= 232]
    picked = sorted(ok, key=lambda i: i["pitch_median_hz"])[:3]
    if len(picked) < 3:                                   # fewer than three in the band: the next lowest natural ones
        rest = sorted((i for i in design if i not in picked and i["word_errors"] <= 2), key=lambda i: i["pitch_median_hz"])
        picked += [i for i in rest if i["pitch_median_hz"] >= 195][:3 - len(picked)]
    files = {}
    for n, i in enumerate(picked, 1):
        mp3 = out / f"voice9_{n}.mp3"
        produce_plain(src / i["file"], mp3)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src / i["file"]), "-c:a", "flac", "-compression_level", "8",
                        str(out / f"voice9_{n}.flac")], check=True)
        files[mp3.name] = f"4_2's recipe, another voice: {Path(i['file']).stem} ({i['pitch_median_hz']} Hz)"
    lock = [i for k, i in takes.items() if k.startswith("r9_lock71_t")]
    for i in lock:
        produce_plain(src / i["file"], out / f"check_{Path(i['file']).stem}.mp3")
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    res = {"round": 9, "text": BUSINESS, "files": files, "picked": picked, "lock71": lock, "all_takes": takes,
           "failed_takes": failed}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 9 (4_2's recipe, naturally lower voices; 7_1 locked the program's way)", "",
          f"Text: {BUSINESS}", ""]
    md += [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | seconds | pitch Hz | pitch moves (st) |", "|---|---|---|---|---|"]
    md += [f"| {k} | {i['word_errors']} | {i['seconds']} | {i['pitch_median_hz']} | {i['pitch_movement_semitones']} |"
           for k, i in sorted(takes.items())]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 10
# Round 9 (run 39372109372) sent voice9_1..3 (4_2's recipe, other seeds, 221-233 Hz); no verdict yet. Round 10 widens
# the same search (20 more seeds, the same recipe and text) so that, whatever he says of round 9, the next three
# naturally lower voices are ready (picked by the same rule; not sent unless asked).

def vox10one(out: Path, take: int) -> None:
    import torch
    m, sr = _vox2()

    def make(t):
        torch.manual_seed(1700 + t)
        return m.generate(text=FRIEND2 + BUSINESS, cfg_value=1.6, inference_timesteps=STEPS4), sr

    _take(out, "r10_design", take, make)


def round10(src: Path, out: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes = {w.stem: _analyze(asr, w, src, gen, BUSINESS) for w in sorted(src.rglob("r10_design_t*.wav"))}
    ok = [i for i in takes.values() if i["word_errors"] <= 2 and i.get("pitch_movement_semitones", 9) <= 5.5
          and 195 <= (i.get("pitch_median_hz") or 0) <= 232]
    picked = sorted(ok, key=lambda i: i["pitch_median_hz"])[:3]
    files = {}
    for n, i in enumerate(picked, 1):
        mp3 = out / f"voice10_{n}.mp3"
        produce_plain(src / i["file"], mp3)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src / i["file"]), "-c:a", "flac", "-compression_level", "8",
                        str(out / f"voice10_{n}.flac")], check=True)
        files[mp3.name] = f"4_2's recipe, another voice: {Path(i['file']).stem} ({i['pitch_median_hz']} Hz)"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    (out / "results.json").write_text(json.dumps({"round": 10, "files": files, "picked": picked, "all_takes": takes,
                                                  "failed_takes": failed}, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 10 (4_2's recipe, 20 more seeds)", ""] + [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | pitch Hz | pitch moves (st) |", "|---|---|---|---|"]
    md += [f"| {k} | {i['word_errors']} | {i['pitch_median_hz']} | {i['pitch_movement_semitones']} |" for k, i in sorted(takes.items())]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 11
# Round 9 verdict (2026-10-20 18:03): 9_2 "a cleaner voice, not bad, but a shade of AI"; 9_3 "good, but lisping - sh,
# ch, s too bright; if that can be fixed, 9_3 is better than 9_2". A de-esser (FFmpeg deesser: only the moments of
# s/sh, no change of pitch or timing) was sent as voice9_3a (i=0.6) / 9_3b (i=1). Round 11 checks the program's way:
# 9_3's very recording locked (ultimate cloning) on other texts keeps its voice - pitch and the s/sh brightness.

RU_TEXT = "Короче, вот что важно знать на этой неделе. Билеты в Европу подешевели почти на двадцать процентов."


def vox11one(out: Path, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()
    text = {1: BUSINESS2, 2: BUSINESS2, 3: RU_TEXT}[take]

    def make(t):
        torch.manual_seed(1800 + t)
        return m.generate(text=text, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(ref),
                          prompt_text=BUSINESS, reference_wav_path=str(ref)), sr

    _take(out, "r11_lock93", take, make)


def _sibilance(wav: Path) -> float:
    """How loud the s/sh peaks (4.5-10 kHz) are against the voice, dB (9_3 -16, 9_2 -20)."""
    import numpy as np
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                       capture_output=True).stdout
    x = np.frombuffer(b, np.float32)
    n, hop = 1024, 512
    win, fr = np.hanning(n), np.fft.rfftfreq(n, 1 / 48000)
    sib, tot = [], []
    for i in range(0, len(x) - n, hop):
        sp = np.abs(np.fft.rfft(x[i:i + n] * win)) ** 2
        if sp.sum() < 1e-4:
            continue
        sib.append(sp[(fr >= 4500) & (fr <= 10000)].sum())
        tot.append(sp.sum())
    if not sib:
        return 0.0
    return round(float(np.percentile(10 * np.log10(np.array(sib) + 1e-12), 98)
                       - np.percentile(10 * np.log10(np.array(tot) + 1e-12), 90)), 1)


def round11(src: Path, out: Path, ref: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    rows, files = {}, {}
    rows["reference 9_3"] = {"pitch_median_hz": 232.7, "sibilance_db": _sibilance(ref)}
    for w in sorted(src.rglob("r11_lock93_t*.wav")):
        take = int(w.stem.rsplit("_t", 1)[1])
        info = _analyze(asr, w, src, gen, RU_TEXT if take == 3 else BUSINESS2)
        info["sibilance_db"] = _sibilance(w)
        rows[w.stem] = info
        for tag, ds in (("a", "deesser=i=0.6:m=0.5:f=0.5,"), ("b", "deesser=i=1:m=0.8:f=0.45,")):
            mp3 = out / f"voice11_{take}{tag}.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-af", ds + "loudnorm=I=-16:TP=-1.5:LRA=11",
                            "-ar", "48000", "-ac", "1", "-b:a", "192k", str(mp3)], check=True)
            files[mp3.name] = f"9_3 locked, take {take} ({'Russian' if take == 3 else 'another English text'}), de-esser {tag}"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    (out / "results.json").write_text(json.dumps({"round": 11, "files": files, "rows": rows, "failed_takes": failed},
                                                 indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 11 (9_3 locked the program's way; de-esser a / b)", ""] + [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | pitch Hz | s/sh peaks dB |", "|---|---|---|---|"]
    md += [f"| {k} | {i.get('word_errors', '-')} | {i.get('pitch_median_hz')} | {i.get('sibilance_db')} |" for k, i in rows.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 12
# Round 11 (run 39512712859): 9_3 locked keeps its s/sh (-16 dB, "lisping" - the owner: "3a / 3b hiss too": it is how
# the voice says them, not how loud) and its pitch drifts with the seed (235 / 275 / 221 Hz). The owner's rule: "if 9_3
# can be fixed, 9_3, else 9_2" -> 9_2. Round 12: 9_2 locked the program's way, 4 English takes (seeds) + Russian:
# how steady is it (pitch per take), are all words said.

def vox12one(out: Path, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()
    text = RU_TEXT if take == 5 else BUSINESS2

    def make(t):
        torch.manual_seed(1900 + t)
        return m.generate(text=text, cfg_value=2.0, inference_timesteps=STEPS4, prompt_wav_path=str(ref),
                          prompt_text=BUSINESS, reference_wav_path=str(ref)), sr

    _take(out, "r12_lock92", take, make)


def round12(src: Path, out: Path, ref: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    rows, files = {"reference 9_2": {"pitch_median_hz": 232.7, "sibilance_db": _sibilance(ref)}}, {}
    for w in sorted(src.rglob("r12_lock92_t*.wav")):
        take = int(w.stem.rsplit("_t", 1)[1])
        ru = take == 5
        info = _analyze(asr, w, src, gen, RU_TEXT if ru else BUSINESS2, language="ru" if ru else "en")
        info["sibilance_db"] = _sibilance(w)
        rows[w.stem] = info
        mp3 = out / f"voice12_{take}.mp3"
        produce_plain(w, mp3)
        files[mp3.name] = f"9_2 locked, take {take} ({'Russian' if ru else 'another English text'})"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    (out / "results.json").write_text(json.dumps({"round": 12, "files": files, "rows": rows, "failed_takes": failed},
                                                 indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 12 (9_2 locked the program's way)", ""] + [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | pitch Hz | s/sh peaks dB | said |", "|---|---|---|---|---|"]
    md += [f"| {k} | {i.get('word_errors', '-')} | {i.get('pitch_median_hz')} | {i.get('sibilance_db')} | {str(i.get('said', ''))[:70]} |"
           for k, i in rows.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 13
# Round 12 verdict (2026-10-20 22:52): 9_2 locked the program's way (ultimate cloning: its recording + its words + its
# timbre) is "too robotic". Earlier hints: 7_1 (controllable cloning: the timbre only, plus a style note) was "good";
# every ultimate-cloned voice was turned down (4_5, 5_x). Round 13 keeps 9_2's voice three other ways, same new text:
#   r13_ctrl      - controllable cloning: 9_2's recording as the timbre only
#   r13_ctrl_note - the same with 9_2's own recipe as the style note (the casual, unscripted description)
#   r13_ult_cfg16 - ultimate cloning as now, but at cfg 1.6 (the recipe 9_2 itself was made with)

ROUND13 = {"r13_ctrl": "9_2's recording as the timbre only (controllable cloning)",
           "r13_ctrl_note": "9_2's timbre + its own recipe as the style note",
           "r13_ult_cfg16": "9_2 locked as now (ultimate cloning), cfg 1.6"}


def vox13one(out: Path, variant: str, take: int, ref: Path) -> None:
    import torch
    m, sr = _vox2()
    text = RU_TEXT if take == 9 else BUSINESS2

    def make(t):
        torch.manual_seed(2000 + t)
        if variant == "r13_ctrl":
            return m.generate(text=text, cfg_value=2.0, inference_timesteps=STEPS4, reference_wav_path=str(ref)), sr
        if variant == "r13_ctrl_note":
            return m.generate(text=FRIEND2 + text, cfg_value=1.6, inference_timesteps=STEPS4, reference_wav_path=str(ref)), sr
        return m.generate(text=text, cfg_value=1.6, inference_timesteps=STEPS4, prompt_wav_path=str(ref),
                          prompt_text=BUSINESS, reference_wav_path=str(ref)), sr

    _take(out, variant, take, make)


def round13(src: Path, out: Path, ref: Path) -> int:
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    rows, files = {}, {}
    for w in sorted(src.rglob("r13_*_t[0-9].wav")):
        take = int(w.stem.rsplit("_t", 1)[1])
        ru = take == 9
        info = _analyze(asr, w, src, gen, RU_TEXT if ru else BUSINESS2, language="ru" if ru else "en")
        rows[w.stem] = info
    for n, v in enumerate(ROUND13, 1):
        for take, tag in ((1, ""), (9, "_ru")):
            i = rows.get(f"{v}_t{take}")
            if not i:
                continue
            mp3 = out / f"voice13_{n}{tag}.mp3"
            produce_plain(src / i["file"], mp3)
            files[mp3.name] = ROUND13[v] + (" (Russian)" if tag else "")
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    (out / "results.json").write_text(json.dumps({"round": 13, "files": files, "rows": rows, "failed_takes": failed},
                                                 indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 13 (9_2 kept three other ways)", ""] + [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | pitch Hz | said |", "|---|---|---|---|"]
    md += [f"| {k} | {i.get('word_errors')} | {i.get('pitch_median_hz')} | {str(i.get('said', ''))[:70]} |" for k, i in rows.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if files else 1


# ---------------------------------------------------------------------------------------------------------- round 14
# The owner (2026-10-21): 9_2 (VoxCPM2) is the cleanest voice, but at every setting tried it "still has an AI shade" /
# is "too robotic" (13_3 at cfg 1.6 "a little more pleasant" - the program's voice now). Round 14 tries OTHER free
# engines whose licence allows working use, each one cloning the very same 9_2 recording (the program's
# assets/voice/host_9_2.flac) on the same text as round 13, plus the Russian line where the engine speaks Russian:
#   r14_cosy   - Fun-CosyVoice3 0.5B (Alibaba, Apache-2.0): zero-shot cloning (the recording + its words)
#   r14_cb     - Chatterbox Multilingual V3 (Resemble AI, MIT; an inaudible watermark): defaults
#   r14_cblive - the same, livelier (exaggeration 0.7, cfg 0.3 - round 1's B, which the owner kept)
#   r14_neu    - NeuTTS Air (Neuphonic; weights Apache-2.0, code free under $5M revenue a year): the recording's
#                first 11.3 s (it wants 3-15 s) + their words; English only
#   r14_qwen   - Qwen3-TTS 1.7B Base (Alibaba, Apache-2.0): cloning (the recording + its words)
# (Run 39597794361: neuphonic/neutts-air has become a gated download - a sign-up - so r14_neu is not made, like Orpheus.)
# Not tried: Orpheus and TADA (Meta's Llama licence, behind a sign-up), Fish S2 / F5 / XTTS / OmniVoice / Raon
# (non-commercial), ZONOS2 and MOSS-TTS (8B: too big for a CPU runner), Kokoro (no cloning; round 1: "flat").

ROUND14 = {"r14_cosy": "Fun-CosyVoice3 0.5B (Apache-2.0), cloning 9_2's recording",
           "r14_cb": "Chatterbox Multilingual V3 (MIT), cloning 9_2's recording, default settings",
           "r14_cblive": "Chatterbox Multilingual V3 (MIT), cloning 9_2's recording, livelier (exaggeration 0.7, cfg 0.3)",
           "r14_neu": "NeuTTS Air (Apache-2.0 weights), cloning the first 11 s of 9_2's recording",
           "r14_qwen": "Qwen3-TTS 1.7B Base (Apache-2.0), cloning 9_2's recording"}
REF92_SHORT_S = 11.3          # the end of the third sentence (the pause at 11.0-11.6 s)
REF92_SHORT_TEXT = ("Here's what you need to know this week. First, flights to Europe got almost twenty percent cheaper. "
                    "Second, if you book before Friday, most airlines let you change the dates for free.")
R14_TAKES = (1, 2)            # English takes (other seeds); take 9 is the Russian line
R14_RU = 9


def _seed_all(seed: int) -> None:
    import numpy as np, torch
    random.seed(seed)
    np.random.seed(seed % (2 ** 32))
    torch.manual_seed(seed)


def cosy14(out: Path, ref: Path, cosy_dir: Path, model_dir: Path) -> None:
    _threads()
    sys.path[:0] = [str(cosy_dir), str(cosy_dir / "third_party" / "Matcha-TTS")]
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel
    m = AutoModel(model_dir=str(model_dir))
    _api_dump(out, m, "cosyvoice3")
    prompt = "You are a helpful assistant.<|endofprompt|>" + BUSINESS

    def make(text):
        def f(t):
            _seed_all(2100 + t)
            parts = [j["tts_speech"] for j in m.inference_zero_shot(text, prompt, str(ref), stream=False)]
            return torch.cat(parts, dim=1), m.sample_rate
        return f

    for take in R14_TAKES:
        _take(out, "r14_cosy", take, make(BUSINESS2))
    _take(out, "r14_cosy", R14_RU, make(RU_TEXT))


def cb14(out: Path, ref: Path) -> None:
    _threads()
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    try:
        m = ChatterboxMultilingualTTS.from_pretrained(device="cpu", t3_model="v3")
    except TypeError:                                   # an older package without the V3 choice
        m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    _api_dump(out, m, "chatterbox_mtl")

    def make(text, lang, **kw):
        def f(t):
            _seed_all(2200 + t)
            return m.generate(text, language_id=lang, audio_prompt_path=str(ref), **kw), m.sr
        return f

    for v, kw in (("r14_cb", dict(exaggeration=0.5, cfg_weight=0.5)),
                  ("r14_cblive", dict(exaggeration=0.7, cfg_weight=0.3))):
        for take in R14_TAKES:
            _take(out, v, take, make(BUSINESS2, "en", **kw))
        # an English reference for Russian words: cfg 0 keeps its accent out (the Chatterbox README's advice)
        _take(out, v, R14_RU, make(RU_TEXT, "ru", exaggeration=kw["exaggeration"], cfg_weight=0.0))


def neu14(out: Path, ref_short: Path) -> None:
    _threads()
    from neutts import NeuTTS
    m = NeuTTS(backbone_repo="neuphonic/neutts-air", backbone_device="cpu",
               codec_repo="neuphonic/neucodec", codec_device="cpu")
    _api_dump(out, m, "neutts")
    codes = m.encode_reference(str(ref_short))

    def f(t):
        _seed_all(2300 + t)
        return m.infer(BUSINESS2, codes, REF92_SHORT_TEXT), m.sample_rate

    for take in R14_TAKES:
        _take(out, "r14_neu", take, f)


def qwen14(out: Path, ref: Path) -> None:
    _threads()
    import torch
    from qwen_tts import Qwen3TTSModel
    try:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32)
    except TypeError:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", torch_dtype=torch.float32)
    _api_dump(out, m, "qwen_base")
    prompt = m.create_voice_clone_prompt(ref_audio=str(ref), ref_text=BUSINESS)

    def make(text, lang):
        def f(t):
            _seed_all(2400 + t)
            wavs, sr = m.generate_voice_clone(text=text, language=lang, voice_clone_prompt=prompt)
            return wavs[0], sr
        return f

    for take in R14_TAKES:
        _take(out, "r14_qwen", take, make(BUSINESS2, "English"))
    _take(out, "r14_qwen", R14_RU, make(RU_TEXT, "Russian"))


def _pitch_median(wav: Path) -> float:
    import numpy as np, librosa
    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=450, sr=sr, frame_length=1024)
    f0v = f0[voiced & ~np.isnan(f0)]
    return float(np.median(f0v)) if f0v.size else 0.0


def round14(src: Path, out: Path, ref: Path, now_mp3: Path | None) -> int:
    """Words and pitch of every take; per engine the English take with the fewest wrong words (then the pitch
    nearest 9_2's own) and its Russian take; voice14_0_now.mp3 = the program's voice today (round 13's 13_3)."""
    import math, shutil
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    ref_hz = _pitch_median(ref)
    rows, files = {"reference 9_2": {"pitch_median_hz": round(ref_hz, 1)}}, {}
    for w in sorted(src.rglob("r14_*_t[0-9].wav")):
        take = int(w.stem.rsplit("_t", 1)[1])
        ru = take == R14_RU
        info = _analyze(asr, w, src, gen, RU_TEXT if ru else BUSINESS2, language="ru" if ru else "en")
        hz = info.get("pitch_median_hz") or 0
        info["off_9_2_semitones"] = round(12 * math.log2(hz / ref_hz), 2) if hz and ref_hz else None
        rows[w.stem] = info
    if now_mp3 is not None and now_mp3.exists():
        shutil.copyfile(now_mp3, out / "voice14_0_now.mp3")
        files["voice14_0_now.mp3"] = "the program's voice today (VoxCPM2, 9_2 at cfg 1.6 - round 13's 13_3), the same text"
    for n, v in enumerate(ROUND14, 1):
        en = [i for k, i in rows.items() if k.startswith(v + "_t") and not k.endswith(f"_t{R14_RU}")]
        if en:
            best = min(en, key=lambda i: (i["word_errors"], 9 if i.get("off_9_2_semitones") is None
                                              else abs(i["off_9_2_semitones"])))
            mp3 = out / f"voice14_{n}.mp3"
            produce_plain(src / best["file"], mp3)
            files[mp3.name] = ROUND14[v] + f" ({Path(best['file']).stem})"
        ru = rows.get(f"{v}_t{R14_RU}")
        if ru:
            mp3 = out / f"voice14_{n}_ru.mp3"
            produce_plain(src / ru["file"], mp3)
            files[mp3.name] = ROUND14[v] + " (Russian)"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    (out / "results.json").write_text(json.dumps({"round": 14, "files": files, "rows": rows, "failed_takes": failed},
                                                 indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 14 (other free engines cloning 9_2)", ""] + [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | seconds | pitch Hz | off 9_2 (semitones) | made in s | said |",
           "|---|---|---|---|---|---|---|"]
    md += [f"| {k} | {i.get('word_errors', '-')} | {i.get('seconds', '-')} | {i.get('pitch_median_hz')} | "
           f"{i.get('off_9_2_semitones', '-')} | {i.get('seconds_to_make', '-')} | {str(i.get('said', ''))[:70]} |"
           for k, i in rows.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps({"files": len(files), "failed_takes": len(failed)}))
    return 0 if len(files) > 1 else 1


# ---------------------------------------------------------------------------------------------------------- round 15
# The owner picked 14_5 (Qwen3-TTS) and it is the program's engine for 9_2 (b184). The real add-on run on Windows
# (39695153819): its Russian "Привет! Это короткая проверка голоса." was heard back as "... Киротка Япровьерка
# Галлесса" - 9_2's recording is English, and Qwen3-TTS continuing it (the recording + its English words, 'ICL')
# carries the English accent into Russian. Round 15: the same voice in Russian two ways - ICL as now, and the
# voice's timbre only ('x-vector only': no English words to continue) - on three Russian texts, two seeds each.

RU15 = {"a": "Привет! Это короткая проверка голоса.",
        "b": RU_TEXT,
        "c": ("Сохрани это видео, чтобы не потерять. Отели дешевеют примерно за три недели до поездки, "
              "так что не спеши с бронированием.")}


def qwen15(out: Path, ref: Path) -> None:
    _threads()
    import torch
    from qwen_tts import Qwen3TTSModel
    try:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32)
    except TypeError:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", torch_dtype=torch.float32)
    prompts = {"icl": m.create_voice_clone_prompt(ref_audio=str(ref), ref_text=BUSINESS),
               "xvec": m.create_voice_clone_prompt(ref_audio=str(ref), x_vector_only_mode=True)}
    for mode, prompt in prompts.items():
        for key, text in RU15.items():
            for seed in (1, 2):
                def make(t, text=text, prompt=prompt, seed=seed):
                    _seed_all(2500 + seed)
                    wavs, sr = m.generate_voice_clone(text=text, language="Russian", voice_clone_prompt=prompt)
                    return wavs[0], sr
                _take(out, f"r15_{mode}_{key}", seed, make)


def round15(src: Path, out: Path, ref: Path) -> int:
    import math
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small", device="cpu", compute_type="int8")     # the program's own listener
    ref_hz = _pitch_median(ref)
    rows, files, total = {}, {}, {"icl": [0, 0], "xvec": [0, 0]}
    for w in sorted(src.rglob("r15_*_t[0-9].wav")):
        mode, key = w.stem.split("_")[1], w.stem.split("_")[2]
        info = _analyze(asr, w, src, gen, RU15[key], language="ru")
        hz = info.get("pitch_median_hz") or 0
        info["off_9_2_semitones"] = round(12 * math.log2(hz / ref_hz), 2) if hz and ref_hz else None
        rows[w.stem] = info
        total[mode][0] += info["word_errors"]
        total[mode][1] += len(_words(RU15[key]))
    for mode in ("icl", "xvec"):
        for key in RU15:
            takes = [i for k, i in rows.items() if k.startswith(f"r15_{mode}_{key}_t")]
            if takes:
                best = min(takes, key=lambda i: i["word_errors"])
                mp3 = out / f"voice15_{mode}_{key}.mp3"
                produce_plain(src / best["file"], mp3)
                files[mp3.name] = f"9_2 in Russian, {'as now (ICL)' if mode == 'icl' else 'timbre only (x-vector)'}, text {key}"
    failed = {k: str(v.get("error")).splitlines()[0][:300] for k, v in gen.items() if v.get("error")}
    summary = {m: {"word_errors": e, "words": n, "rate": round(e / max(1, n), 3)} for m, (e, n) in total.items()}
    (out / "results.json").write_text(json.dumps({"round": 15, "summary": summary, "files": files, "rows": rows,
                                                  "failed_takes": failed}, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Voice lab - round 15 (9_2 in Russian: ICL vs timbre only)", "", json.dumps(summary, ensure_ascii=False), ""]
    md += [f"- {k}: {v}" for k, v in files.items()]
    md += ["", "| take | words wrong | pitch Hz | off 9_2 | said |", "|---|---|---|---|---|"]
    md += [f"| {k} | {i['word_errors']} | {i['pitch_median_hz']} | {i['off_9_2_semitones']} | {i['said'][:80]} |"
           for k, i in rows.items()]
    if failed:
        md += ["", "Failed takes:"] + [f"- {k}: {e}" for k, e in failed.items()]
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", "utf-8")
    print(json.dumps(summary))
    return 0 if rows else 1


def check(src: Path, out: Path) -> int:
    import numpy as np, librosa
    from faster_whisper import WhisperModel
    out.mkdir(parents=True, exist_ok=True)
    gen = {}
    for p in src.rglob("gen.json"):
        gen.update(json.loads(p.read_text("utf-8")))
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    takes = {}
    for wav in sorted(src.rglob("*_t[0-9].wav")):
        takes[wav.stem] = _analyze(asr, wav, src, gen)
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
        md += ["", "Failed takes:"] + [f"- {k}: {str(e).splitlines()[0][:300]}" for k, e in failed.items()]
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
    elif cmd == "turbo":
        turbo(out, Path(sys.argv[3]).resolve())
    elif cmd == "voxcpm":
        voxcpm(out, Path(sys.argv[3]).resolve())
    elif cmd == "round2":
        return round2(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox3":
        vox3(out, Path(sys.argv[3]).resolve())
    elif cmd == "cb3":
        cb3(out, Path(sys.argv[3]).resolve())
    elif cmd == "round3":
        return round3(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox4a":
        vox4a(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox4b":
        vox4b(out)
    elif cmd == "vox5one":
        vox5one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve())
    elif cmd == "round5":
        return round5(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox7one":
        vox7one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve())
    elif cmd == "round7":
        return round7(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox8one":
        vox8one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve())
    elif cmd == "round8":
        return round8(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox9one":
        vox9one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve() if len(sys.argv) > 5 else None)
    elif cmd == "round9":
        return round9(out, Path(sys.argv[3]).resolve())
    elif cmd == "qwen15":
        qwen15(out, Path(sys.argv[3]).resolve())
    elif cmd == "round15":
        return round15(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    elif cmd == "cosy14":
        cosy14(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve(), Path(sys.argv[5]).resolve())
    elif cmd == "cb14":
        cb14(out, Path(sys.argv[3]).resolve())
    elif cmd == "neu14":
        neu14(out, Path(sys.argv[3]).resolve())
    elif cmd == "qwen14":
        qwen14(out, Path(sys.argv[3]).resolve())
    elif cmd == "round14":
        return round14(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve(),
                       Path(sys.argv[5]).resolve() if len(sys.argv) > 5 else None)
    elif cmd == "vox13one":
        vox13one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve())
    elif cmd == "round13":
        return round13(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    elif cmd == "vox12one":
        vox12one(out, int(sys.argv[3]), Path(sys.argv[4]).resolve())
    elif cmd == "round12":
        return round12(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    elif cmd == "vox11one":
        vox11one(out, int(sys.argv[3]), Path(sys.argv[4]).resolve())
    elif cmd == "round11":
        return round11(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    elif cmd == "vox10one":
        vox10one(out, int(sys.argv[3]))
    elif cmd == "round10":
        return round10(out, Path(sys.argv[3]).resolve())
    elif cmd == "vox4one":
        vox4one(out, sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]).resolve())
    elif cmd == "round4":
        return round4(out, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

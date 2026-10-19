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


_NUMBERS = {"10": "ten", "3": "three"}       # the checker writes "10" for a spoken "ten": not a wrong word


def _analyze(asr, wav: Path, src: Path, gen: dict, text: str = TEXT) -> dict:
    """What a take really says (faster-whisper), how long it is, how high the voice is and how much it moves."""
    import numpy as np, librosa
    name = wav.stem
    ref_words = _words(re.sub(r"\[[a-z ]+\]|\([^)]*\)", " ", text))
    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    dur = len(y) / sr
    segs, _ = asr.transcribe(str(wav), language="en", beam_size=5, vad_filter=True)
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
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

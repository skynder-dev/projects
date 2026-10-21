"""Engine probe: can another free voice engine run the way the voice add-on runs (Windows, the program's Python 3.11,
CPU torch 2.8 - the add-on's own torch), and what exactly does it import?

Not the product. The owner is choosing between voices made by other free engines (voice lab round 14: CosyVoice3,
Chatterbox Multilingual V3, Qwen3-TTS Base, each cloning the program's 9_2 recording). Before one of them can go into
the add-on, this says on a real Windows runner: it installs, it says one sentence in 9_2's voice on torch 2.8, how
long that takes on a CPU, and the exact distributions it really imports (their versions) - the add-on installs only
those, as wheels, without dependency resolution (as it does for VoxCPM2).

  python engine_probe.py qwen|chatterbox <ref.wav> <out_dir>

Synthetic text only; the reference is the program's own assets/voice/host_9_2.flac (a designed voice, no person).
"""
from __future__ import annotations

import json, os, sys, time, traceback
from pathlib import Path

TEXT = ("Quick update for anyone planning a summer trip. Hotel prices usually drop about three weeks before the date, "
        "so don't book too early.")
REF_TEXT = ("Here's what you need to know this week. First, flights to Europe got almost twenty percent cheaper. "
            "Second, if you book before Friday, most airlines let you change the dates for free. "
            "And third, the best deals are on Tuesday and Wednesday. Save this, and send it to someone who's planning a trip.")


def _save(path: Path, audio, sr: int) -> None:
    import numpy as np, soundfile as sf
    a = audio.detach().cpu().float().numpy() if hasattr(audio, "detach") else audio
    sf.write(str(path), np.asarray(a, dtype="float32").squeeze(), int(sr))


def qwen(ref: Path, out: Path) -> dict:
    import torch
    from qwen_tts import Qwen3TTSModel
    t0 = time.time()
    try:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32)
    except TypeError:
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", torch_dtype=torch.float32)
    load_s = time.time() - t0
    prompt = m.create_voice_clone_prompt(ref_audio=str(ref), ref_text=REF_TEXT)
    torch.manual_seed(2401)
    t1 = time.time()
    wavs, sr = m.generate_voice_clone(text=TEXT, language="English", voice_clone_prompt=prompt)
    _save(out / "qwen.wav", wavs[0], sr)
    return {"load_s": round(load_s, 1), "make_s": round(time.time() - t1, 1), "sr": sr}


def chatterbox(ref: Path, out: Path) -> dict:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    t0 = time.time()
    m = ChatterboxMultilingualTTS.from_pretrained(device="cpu", t3_model="v3")
    load_s = time.time() - t0
    torch.manual_seed(2202)
    t1 = time.time()
    wav = m.generate(TEXT, language_id="en", audio_prompt_path=str(ref), exaggeration=0.5, cfg_weight=0.5)
    _save(out / "chatterbox.wav", wav, m.sr)
    return {"load_s": round(load_s, 1), "make_s": round(time.time() - t1, 1), "sr": m.sr}


def imported() -> dict:
    """The distributions behind every module imported now, with their versions."""
    import importlib.metadata as md
    pd = md.packages_distributions()
    tops = {n.split(".")[0] for n in list(sys.modules)}
    dists = sorted({d for t in tops for d in pd.get(t, [])}, key=str.lower)
    out = {}
    for d in dists:
        try:
            out[d] = md.version(d)
        except Exception:
            out[d] = "?"
    return out


def main() -> int:
    engine, ref, out = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    import torch
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    res = {"engine": engine, "python": sys.version.split()[0], "torch": torch.__version__, "platform": sys.platform}
    try:
        res.update({"qwen": qwen, "chatterbox": chatterbox}[engine](ref, out))
        res["ok"] = True
    except Exception as exc:
        res.update(ok=False, error=f"{type(exc).__name__}: {exc}", trace=traceback.format_exc()[-4000:])
    res["imported"] = imported()
    (out / f"probe_{engine}.json").write_text(json.dumps(res, indent=1), "utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("imported", "trace")}))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

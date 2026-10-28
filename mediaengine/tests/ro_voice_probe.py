"""A Romanian voice for Cartoon Studio? (a research probe, not part of the program)

  python tests/ro_voice_probe.py --out <dir>

Qwen3-TTS (the program's own voice) does not speak Romanian and VoxCPM2 said it poorly (the voice add-on check, run
40616952980: Whisper heard 3 of 7 words). This tries Piper's Romanian voices (rhasspy/piper-voices on Hugging Face,
ONNX, run on the processor): each voice's model card (its data and licence) is saved, the same three lines are said,
and faster-whisper "small" (the voice add-on's) hears them back in Romanian - the words it got are counted.
Writes ro_voice_probe.json, ro_voice_probe.md, <voice>.wav, <voice>_MODEL_CARD.txt. Nothing paid.
"""
from __future__ import annotations

import argparse, json, re, sys, time, unicodedata, urllib.request, wave
from pathlib import Path

LINES = ["Prețul este de patru ori mai mare decât pe piață.", "Și contractul este aprobat.",
         "Contribuabilii plătesc toată diferența.",
         "Primăria a plătit patru milioane de lei pentru un drum care s-a stricat după prima iarnă."]


def plain(t: str) -> list[str]:
    t = "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")
    return re.findall(r"[a-z]+", t)


def heard_share(said: str, heard: str) -> float:
    want, got = plain(said), plain(heard)
    left = list(got)
    hit = 0
    for w in want:
        if w in left:
            left.remove(w)
            hit += 1
    return round(hit / max(1, len(want)), 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    api = "https://huggingface.co/api/models/rhasspy/piper-voices"
    with urllib.request.urlopen(api + "?blobs=true", timeout=60) as r:
        info = json.load(r)
    rev = info["sha"]
    files = [s["rfilename"] for s in info.get("siblings") or [] if s["rfilename"].startswith("ro/")]
    voices = sorted({f.rsplit("/", 1)[0] for f in files if f.endswith(".onnx")})
    print("piper-voices", rev, "Romanian:", voices, flush=True)
    from faster_whisper import WhisperModel
    from piper import PiperVoice
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    report = {"piper_voices_rev": rev, "voices": {}}
    md = ["# A Romanian voice: Piper's voices heard back by Whisper small\n", f"rhasspy/piper-voices @ {rev}\n"]
    for d in voices:
        name = d.replace("/", "_")
        onnx = next(f for f in files if f.startswith(d + "/") and f.endswith(".onnx"))
        got = {}
        for f in (onnx, onnx + ".json", d + "/MODEL_CARD"):
            if f not in files:
                continue
            dst = out / (name + ("_MODEL_CARD.txt" if f.endswith("MODEL_CARD") else Path(f).suffix if not f.endswith(".json") else ".onnx.json"))
            urllib.request.urlretrieve(f"https://huggingface.co/rhasspy/piper-voices/resolve/{rev}/{f}", dst)
            got[f] = dst
        card = (out / f"{name}_MODEL_CARD.txt").read_text("utf-8", errors="replace") if (out / f"{name}_MODEL_CARD.txt").exists() else ""
        voice = PiperVoice.load(str(out / f"{name}.onnx"))
        rows = []
        for k, line in enumerate(LINES):
            wav = out / f"{name}_{k + 1}.wav"
            t0 = time.time()
            with wave.open(str(wav), "wb") as wf:
                (voice.synthesize_wav if hasattr(voice, "synthesize_wav") else voice.synthesize)(line, wf)
            took = time.time() - t0
            segs, _ = asr.transcribe(str(wav), language="ro", beam_size=5)
            heard = " ".join(s.text.strip() for s in segs)
            rows.append({"line": line, "heard": heard, "share": heard_share(line, heard), "s": round(took, 2)})
            print(f"  {name} {k + 1}: {rows[-1]['share']} {heard}", flush=True)
        (out / f"{name}.onnx").unlink(missing_ok=True)          # (the model is not kept in the results)
        share = round(sum(x["share"] for x in rows) / len(rows), 3)
        report["voices"][name] = {"lines": rows, "share": share, "card": card[:3000]}
        md += [f"## {name}: {share:.0%} of the words heard", "", "```", card.strip()[:1500], "```", ""]
        md += [f"- {x['share']:.0%} «{x['line']}» -> «{x['heard']}»" for x in rows] + [""]
    (out / "ro_voice_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    (out / "ro_voice_probe.md").write_text("\n".join(md), "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

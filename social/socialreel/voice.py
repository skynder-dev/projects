"""Narration: text normalization for speech + TTS backends.

Backends, best first: piper (local neural TTS, free) -> espeak-ng (robotic, free).
`silent_test` exists only for unit tests; acceptance rejects any video made with it.
"""
from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

from .common import PipelineError, sha256_file

PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def speech_text(text: str) -> str:
    t = text
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand)\b", r"\1 \2 dollars", t, flags=re.I)
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"(?i)\bgrants\.gov\b", "Grants dot gov", t)
    t = re.sub(r"501\(c\)\(3\)", "five oh one c three", t)
    t = t.replace("&", " and ").replace("–", " to ").replace("—", ", ")
    t = re.sub(r"[“”\"]", "", t)
    t = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2})\b",
               lambda m: f"{m[1]} {_ordinal(int(m[2]))}", t)
    return re.sub(r"\s+", " ", t).strip()


def _ordinal(n: int) -> str:
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def wav_duration(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / float(w.getframerate())


class Voice:
    name = "base"
    test_only = False

    def synth(self, text: str, out: Path) -> None:
        raise NotImplementedError

    def identity(self) -> dict:
        return {"backend": self.name, "test_only": self.test_only}


class PiperVoice(Voice):
    name = "piper"

    def __init__(self, voice_id: str, cache: Path, length_scale: float = 1.0):
        self.voice_id = voice_id
        self.length_scale = length_scale
        self.model = self._ensure_model(voice_id, cache)
        from piper import PiperVoice as _PV  # noqa: import inside: optional dependency
        self._v = _PV.load(str(self.model))

    @staticmethod
    def _ensure_model(voice_id: str, cache: Path) -> Path:
        lang_region, name, quality = voice_id.split("-", 2)
        lang = lang_region.split("_")[0]
        cache.mkdir(parents=True, exist_ok=True)
        model = cache / f"{voice_id}.onnx"
        for suffix in (".onnx", ".onnx.json"):
            p = cache / f"{voice_id}{suffix}"
            if not p.exists() or p.stat().st_size == 0:
                url = f"{PIPER_BASE}/{lang}/{lang_region}/{name}/{quality}/{voice_id}{suffix}"
                with urllib.request.urlopen(url, timeout=120) as r, open(p, "wb") as f:
                    shutil.copyfileobj(r, f)
        return model

    def synth(self, text: str, out: Path) -> None:
        with wave.open(str(out), "wb") as wf:
            if hasattr(self._v, "synthesize_wav"):              # piper-tts >= 1.3
                try:
                    from piper import SynthesisConfig
                    cfg = SynthesisConfig(length_scale=self.length_scale)
                    self._v.synthesize_wav(text, wf, syn_config=cfg)
                except ImportError:
                    self._v.synthesize_wav(text, wf)
            else:                                                 # piper-tts 1.2
                self._v.synthesize(text, wf, length_scale=self.length_scale)

    def identity(self) -> dict:
        return {"backend": "piper", "voice": self.voice_id, "model_sha256": sha256_file(self.model),
                "length_scale": self.length_scale, "test_only": False}


class EspeakVoice(Voice):
    name = "espeak-ng"

    def __init__(self, rate: int = 165):
        self.bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if not self.bin:
            raise PipelineError("espeak-ng not installed")
        self.rate = rate

    def synth(self, text: str, out: Path) -> None:
        subprocess.run([self.bin, "-v", "en-us", "-s", str(self.rate), "-w", str(out), text], check=True,
                       capture_output=True)

    def identity(self) -> dict:
        return {"backend": "espeak-ng", "rate": self.rate, "test_only": False}


class SilentTestVoice(Voice):
    """Unit tests only: silence sized like speech. Never accepted as a real Reel."""
    name = "silent_test"
    test_only = True

    def synth(self, text: str, out: Path) -> None:
        sr = 22050
        n = int(sr * max(1.0, len(text.split()) / 2.7))
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(struct.pack("<h", 0) * n)


def make_voice(cfg: dict, cache: Path) -> tuple[Voice, list[str]]:
    want = cfg.get("backend", "piper")
    notes = []
    order = {"piper": ["piper", "espeak"], "espeak": ["espeak"], "silent_test": ["silent_test"]}.get(want, [want])
    for b in order:
        try:
            if b == "piper":
                return PiperVoice(cfg.get("piper_voice", "en_US-ryan-high"), cache, float(cfg.get("length_scale", 1.0))), notes
            if b == "espeak":
                return EspeakVoice(int(cfg.get("espeak_rate", 165))), notes
            if b == "silent_test":
                return SilentTestVoice(), notes
        except Exception as e:
            notes.append(f"voice backend {b} unavailable: {type(e).__name__}: {str(e)[:200]}")
    raise PipelineError("no TTS backend available: " + " | ".join(notes))

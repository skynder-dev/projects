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

from .common import PipelineError, sha256_file, check_cancel, HIDDEN_PROCESS

PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def speech_text(text: str) -> str:
    t = text
    # Resolve ISO calendar dates before the range rule can turn their hyphens into "to".
    import datetime
    def iso_date(match):
        try:day=datetime.date.fromisoformat(match[0])
        except ValueError as error:raise PipelineError('Invalid ISO calendar date in narration; review before synthesis') from error
        months=('January','February','March','April','May','June','July','August','September','October','November','December')
        return f"{months[day.month-1]} {day.day}, {day.year}"
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b",iso_date,t)
    values={name:i for i,name in enumerate(('zero','one','two','three','four','five','six','seven','eight','nine','ten'))}
    def paired_number(match):
        if values[match[1].casefold()]!=int(match[2]):raise PipelineError('Written and parenthesized number disagree; review before synthesis')
        return match[1]
    t = re.sub(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+\((\d+)\)",paired_number,t,flags=re.I)
    t = re.sub(r"\u20ac\s?(\d+(?:,\d{3})*(?:\.\d+)?)",r"\1 euros",t)
    t = re.sub(r"\u00a3\s?(\d+(?:,\d{3})*(?:\.\d+)?)",r"\1 pounds",t)
    t = re.sub(r"(?<=\d)\s*%",' percent',t)
    t = re.sub(r"\$\s?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)\b", r"\1 \2 dollars", t, flags=re.I)
    t = re.sub(r"\$\s?(\d+(?:,\d{3})*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+\((\d+)\)", r"\1", t, flags=re.I)  # "one (1)"
    t = re.sub(r"(?i)\bgrants\.gov\b", "Grants dot gov", t)
    t = re.sub(r"501\(c\)\(3\)", "five oh one c three", t)
    t = t.replace("&", " and ")
    t = re.sub(r"(?<=\d)\s*[-–]\s*(?=\d)", " to ", t)
    t = re.sub(r"(?<=[A-Za-z])[-–](?=[A-Za-z])", " ", t)
    t = re.sub(r"[“”\"]", "", t)
    t = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2})\b",
               lambda m: f"{m[1]} {_ordinal(int(m[2]))}", t)
    t = re.sub(r"\b[A-Z]{2,8}\b", lambda m: " ".join(m[0]) if m[0] not in {"NASA"} else m[0], t)
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
                raise PipelineError(f"Piper model missing: {p}; runtime downloads forbidden")
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
                       capture_output=True, **HIDDEN_PROCESS)

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



def gather_voice_results(pipeline,text,voice,speed,cancel=None):
    """Cooperative checkpoints between engine yields; no claim of interrupting a native call."""
    cancel=cancel or check_cancel
    cancel();results=[]
    for result in pipeline(text,voice=voice,speed=speed):
        cancel();results.append(result)
    cancel()
    return results


class KokoroVoice(Voice):
    """Fixed female voice; explicit local files, CPU only, no runtime downloads."""
    name = "kokoro"

    def __init__(self, cfg, cache):
        self.cfg = cfg
        self.model_dir = Path(cfg["model_dir"])
        self.model = self.model_dir / "kokoro-v1_0.pth"
        self.pack = self.model_dir / "voices" / "af_heart.pt"
        for p in (self.model, self.pack, self.model_dir / "config.json"):
            if not p.is_file():
                raise PipelineError(f"Social Kokoro model missing: {p}; run authorized setup")
        self.cache = cache / "kokoro"
        self.cache.mkdir(parents=True, exist_ok=True)
        self._pipeline = None
        self.hits = 0
        self.legacy_hits = 0
        self._legacy = []

    def identity(self):
        return {"backend": "kokoro", "voice": "af_heart", "device": "cpu",
                "model_sha256": sha256_file(self.model), "voice_sha256": sha256_file(self.pack),
                "speed": float(self.cfg.get("speed", 1.0)), "test_only": False}

    def synth(self, text, out):
        check_cancel()
        import hashlib, json
        key = hashlib.sha256(json.dumps({"text": text, **self.identity()}, sort_keys=True).encode()).hexdigest()
        cached = self.cache / (key + ".wav")
        valid_cache = False
        if cached.is_file():
            try:
                with wave.open(str(cached), 'rb') as w:
                    valid_cache = w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == 24000 and w.getnframes()/24000 >= .4
            except (wave.Error, EOFError, OSError):
                pass
        metadata = cached.with_suffix('.json')
        if valid_cache and metadata.exists():
            from .common import read_json
            try:
                stamp=read_json(metadata)
                valid_cache=stamp.get('key')==key and stamp.get('sha256')==sha256_file(cached) and stamp.get('bytes')==cached.stat().st_size
            except (OSError,ValueError,AttributeError):valid_cache=False
            if not valid_cache:
                import uuid
                suffix='.corrupt_'+uuid.uuid4().hex
                cached.rename(cached.with_name(cached.name+suffix))
                metadata.rename(metadata.with_name(metadata.name+suffix))
        if os.environ.get('SOCIAL_CACHE_ONLY')=='1' and (not valid_cache or not metadata.is_file()):
            raise PipelineError('Kokoro verified cache-only miss; model not loaded')
        if valid_cache:
            check_cancel()
            shutil.copy2(cached, out)
            check_cancel()
            if not metadata.exists():
                self.legacy_hits += 1
                self._legacy.append((cached,key,Path(out)))
            self.hits += 1
            return
        if self._pipeline is None:
            import spacy
            if not spacy.util.is_package("en_core_web_sm"):
                raise PipelineError("Social English pronunciation model missing; runtime downloads forbidden")
            import torch
            from kokoro import KModel, KPipeline
            torch.set_num_threads(4)
            model = KModel(repo_id="hexgrad/Kokoro-82M", config=str(self.model_dir / "config.json"), model=str(self.model)).to("cpu").eval()
            self._pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", model=model, device="cpu")
        import numpy as np
        import soundfile as sf
        results=gather_voice_results(self._pipeline,text,str(self.pack),float(self.cfg.get('speed',1.0)))
        chunks=[r.audio.detach().cpu().numpy() for r in results]
        check_cancel()
        if not chunks:
            raise PipelineError("Kokoro produced no audio")
        audio = np.concatenate(chunks)
        if not np.isfinite(audio).all() or np.max(np.abs(audio)) < .001:
            raise PipelineError("Kokoro produced silent or invalid audio")
        import uuid
        partial = cached.with_name(cached.stem + '.' + uuid.uuid4().hex + '.partial.wav')
        try:
            check_cancel()
            sf.write(str(partial), audio, 24000, subtype="PCM_16")
            check_cancel()
            partial.replace(cached)
            from .common import write_json
            write_json(metadata,{'key':key,'sha256':sha256_file(cached),'bytes':cached.stat().st_size,'origin':'local synthesis'})
            check_cancel()
            shutil.copy2(cached, out)
            check_cancel()
        finally:
            # Only this invocation's UUID partial is owned here; never remove a
            # shared model, another process's cache, or a completed cached WAV.
            if partial.is_file():partial.unlink()

    def seal_verified(self):
        """Promote legacy cache only after actual ASR accepted its copied WAVs."""
        from .common import write_json
        sealed=0
        for cached,key,copied in self._legacy:
            if cached.is_file() and copied.is_file() and sha256_file(cached)==sha256_file(copied):
                write_json(cached.with_suffix('.json'),{'key':key,'sha256':sha256_file(cached),'bytes':cached.stat().st_size,'origin':'ASR-verified legacy WAV'})
                sealed+=1
        self._legacy=[]
        return sealed


def make_voice(cfg: dict, cache: Path) -> tuple[Voice, list[str]]:
    want = cfg.get("backend", "piper")
    notes = []
    order = {"piper": ["piper", "espeak"], "espeak": ["espeak"], "silent_test": ["silent_test"]}.get(want, [want])
    for b in order:
        try:
            if b == "kokoro":
                return KokoroVoice(cfg, cache), notes
            if b == "piper":
                return PiperVoice(cfg.get("piper_voice", "en_US-ryan-high"), cache, float(cfg.get("length_scale", 1.0))), notes
            if b == "espeak":
                return EspeakVoice(int(cfg.get("espeak_rate", 165))), notes
            if b == "silent_test":
                return SilentTestVoice(), notes
        except Exception as e:
            notes.append(f"voice backend {b} unavailable: {type(e).__name__}: {str(e)[:200]}")
    raise PipelineError("no TTS backend available: " + " | ".join(notes))


# Frozen historical transform: verification only, never an automatic fallback for a new script.
def _legacy_speech_text(text: str) -> str:
    t = text
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand)\b", r"\1 \2 dollars", t, flags=re.I)
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+\((\d+)\)", r"\1", t, flags=re.I)  # "one (1)"
    t = re.sub(r"(?i)\bgrants\.gov\b", "Grants dot gov", t)
    t = re.sub(r"501\(c\)\(3\)", "five oh one c three", t)
    t = t.replace("&", " and ")
    t = re.sub(r"(?<=\d)\s*[-–]\s*(?=\d)", " to ", t)
    t = re.sub(r"(?<=[A-Za-z])[-–](?=[A-Za-z])", " ", t)
    t = re.sub(r"[“”\"]", "", t)
    t = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2})\b",
               lambda m: f"{m[1]} {_ordinal(int(m[2]))}", t)
    t = re.sub(r"\b[A-Z]{2,8}\b", lambda m: " ".join(m[0]) if m[0] not in {"NASA"} else m[0], t)
    return re.sub(r"\s+", " ", t).strip()


def speech_for_script(script,text):
    version=script.get('speech_normalizer_version','social_speech_v1')
    if version=='social_speech_v1':return _legacy_speech_text(text)
    if version=='social_speech_v2':return speech_text(text)
    raise PipelineError('Unknown script speech normalization version; no guessed compatibility')

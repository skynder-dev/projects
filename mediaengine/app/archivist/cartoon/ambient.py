"""The sound of a place under a scene, made by the program itself (no files, nothing borrowed): wind, birds, a stream,
the sea, rain, crickets at night, a quiet room, a town in the distance. Kept quiet, under the voices and the music.
"""
from __future__ import annotations

import math
import re

import numpy as np

SR = 48000
KINDS = ("wind", "birds", "stream", "sea", "rain", "night", "room", "town", "fire")
# words in a scene's picture -> its sounds (a story's scene without its own "sound")
WORDS = [
    (r"\b(sea|ocean|wave|waves|ship|deck|harbou?r|shore|beach)\b", ("sea", "wind")),
    (r"\b(storm|thunder|rain|raining|downpour)\b", ("rain", "wind")),
    (r"\b(creek|stream|river|brook|watermill|mill wheel|waterfall)\b", ("stream", "birds")),
    (r"\b(night|moon|stars|dark sky|midnight)\b", ("night",)),
    (r"\b(fire|fireplace|campfire|hearth)\b", ("fire", "room")),
    (r"\b(meadow|field|garden|forest|woods|tree|grass|village|road|path|hill)\b", ("birds", "wind")),
    (r"\b(street|town|city|market|square)\b", ("town",)),
    (r"\b(room|attic|kitchen|house|hall|indoors|inside|table|bed|window)\b", ("room",)),
]


def guess(text: str) -> list:
    """The sounds of a place from the words that describe it (the first match wins)."""
    t = str(text or "").lower()
    for rx, kinds in WORDS:
        if re.search(rx, t):
            return list(kinds)
    return []


def _lowpass(x: np.ndarray, k: float) -> np.ndarray:
    """A one-pole low-pass filter's sound (k: 0..1, higher lets more through), done in one go by its frequency response
    (no loop over the samples; numpy only)."""
    n = len(x)
    if n < 2:
        return x.astype(np.float32)
    w = np.linspace(0, math.pi, n // 2 + 1)
    h = k / np.abs(1 - (1 - k) * np.exp(-1j * w))
    return np.fft.irfft(np.fft.rfft(x) * h, n).astype(np.float32)


def _noise(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n).astype(np.float32)


def _slow(n: int, rng, period: float, depth: float = 0.6) -> np.ndarray:
    """A slow wandering level 1-depth .. 1 (gusts, swells)."""
    pts = max(4, int(n / SR / period) + 3)
    v = rng.random(pts).astype(np.float32)
    x = np.linspace(0, pts - 1.001, n)
    i = x.astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    return (1 - depth) + depth * (v[i] * (1 - f) + v[i + 1] * f)


def _chirp(rng) -> np.ndarray:
    """A small bird's call: a few quick falling or rising whistles."""
    out = []
    f0 = rng.uniform(2600, 4200)
    for _ in range(int(rng.integers(2, 6))):
        d = rng.uniform(0.04, 0.11)
        n = int(SR * d)
        t = np.arange(n) / SR
        f = f0 * (1 + rng.uniform(-0.35, 0.35) * t / d)
        ph = 2 * math.pi * np.cumsum(f) / SR
        env = np.sin(np.pi * t / d) ** 2
        out.append((np.sin(ph) * env).astype(np.float32))
        out.append(np.zeros(int(SR * rng.uniform(0.03, 0.09)), np.float32))
    return np.concatenate(out)


def make(kind: str, seconds: float, seed: int = 0) -> np.ndarray:
    """One place's sound, `seconds` long, about -24 dB (mixed lower still)."""
    n = max(1, int(seconds * SR))
    rng = np.random.default_rng(1000 + seed * 31 + KINDS.index(kind) if kind in KINDS else seed)
    if kind == "wind":
        x = _lowpass(_noise(n, rng), 0.012) * 6.0
        return x * _slow(n, rng, 3.5, 0.75) * 0.5
    if kind == "sea":
        x = _lowpass(_noise(n, rng), 0.05) * 2.0
        sw = 0.5 + 0.5 * np.sin(2 * math.pi * np.arange(n) / SR / 7.0 + rng.uniform(0, 6)) ** 2
        return x * sw * _slow(n, rng, 9.0, 0.4) * 0.5
    if kind == "stream":
        x = _noise(n, rng)
        x = _lowpass(x, 0.25) - _lowpass(x, 0.03)          # (a band: the hiss of running water)
        bub = np.zeros(n, np.float32)
        for _ in range(int(seconds * 9)):                  # (little bubbles: short rising tones)
            i, d = int(rng.integers(0, n)), int(SR * rng.uniform(0.01, 0.03))
            t = np.arange(min(d, n - i)) / SR
            bub[i:i + len(t)] += np.sin(2 * math.pi * rng.uniform(500, 1400) * (1 + 30 * t) * t) * np.exp(-t * 150) * 0.25
        return (x * 0.9 * _slow(n, rng, 2.0, 0.3) + bub) * 0.5
    if kind == "rain":
        x = _noise(n, rng)
        x = x - _lowpass(x, 0.15)
        drops = (rng.random(n) < 0.0007).astype(np.float32) * rng.uniform(0.3, 1.0, n).astype(np.float32)
        drops = _lowpass(drops, 0.5)
        return (x * 0.35 + drops * 2.0) * 0.45
    if kind == "birds":
        out = np.zeros(n, np.float32)
        t = rng.uniform(0.3, 1.5)
        while t < seconds - 0.8:
            c = _chirp(rng) * rng.uniform(0.15, 0.4)
            i = int(t * SR)
            out[i:i + len(c)] += c[:n - i]
            t += rng.uniform(0.6, 3.5)
        return out * 0.45
    if kind == "night":                                    # (crickets: a high trill pulsing)
        t = np.arange(n) / SR
        tone = np.sin(2 * math.pi * 4400 * t)
        pulse = (np.sin(2 * math.pi * 28 * t) > 0.2).astype(np.float32)
        group = (np.sin(2 * math.pi * 0.9 * t + rng.uniform(0, 6)) > -0.1).astype(np.float32)
        x = tone * _lowpass(pulse * group, 0.05) * 0.12
        return (x + _lowpass(_noise(n, rng), 0.01) * 0.6).astype(np.float32) * 0.5
    if kind == "room":                                     # (the quiet of a room: a soft air tone, a creak now and then)
        x = _lowpass(_noise(n, rng), 0.006) * 2.5
        for _ in range(int(seconds / 6)):
            i, d = int(rng.integers(0, n)), int(SR * 0.25)
            t = np.arange(min(d, n - i)) / SR
            x[i:i + len(t)] += (np.sin(2 * math.pi * (160 + 60 * np.sin(20 * t)) * t) * np.exp(-t * 12) * 0.05).astype(np.float32)
        return x * 0.4
    if kind == "town":                                     # (a town far away: a low rumble, voices blurred)
        x = _lowpass(_noise(n, rng), 0.004) * 6.0
        v = _lowpass(_noise(n, rng), 0.06) * _slow(n, rng, 0.7, 0.9)
        return (x + v * 0.4) * 0.45
    if kind == "fire":
        x = _lowpass(_noise(n, rng), 0.02) * 2.0
        cr = (rng.random(n) < 0.002).astype(np.float32) * rng.uniform(0.2, 1.0, n).astype(np.float32)
        return (x * 0.5 + _lowpass(cr, 0.7) * 1.5) * 0.45
    return np.zeros(n, np.float32)


def bed(kinds: list, seconds: float, seed: int = 0) -> np.ndarray:
    """A scene's sounds together, faded in and out (half a second), at a level that sits under speech."""
    n = max(1, int(seconds * SR))
    out = np.zeros(n, np.float32)
    for i, k in enumerate(kinds or []):
        if k in KINDS:
            out += make(k, seconds, seed + i)[:n]
    if not out.any():
        return out
    rms = float(np.sqrt(np.mean(out ** 2))) or 1.0
    out *= 0.035 / rms                                     # (about -29 dB: heard, never over a voice)
    f = min(n // 2, int(SR * 0.6))
    if f > 0:
        ramp = np.linspace(0, 1, f, dtype=np.float32)
        out[:f] *= ramp
        out[-f:] *= ramp[::-1]
    return np.clip(out, -0.3, 0.3)

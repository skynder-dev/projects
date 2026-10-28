"""Background music for a cartoon: a light bed made by the program itself (chords, a plucked arpeggio, a soft bass and
light drums - nothing borrowed, the same every time for the same mood and length), or the owner's own music file
looped; either kept quiet and ducked under the voices.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

SR = 48000
MOODS = {
    # (beats a minute, the chords' roots in semitones above A2, minor chord?, how busy the drums are)
    "light": (96, [3, 10, 0, 8], [False, False, True, False], 1.0),        # C G Am F
    "suspense": (84, [0, 8, 5, 7], [True, False, True, False], 0.5),       # Am F Dm E
    "calm": (76, [8, 3, 0, 10], [False, False, True, False], 0.0),         # F C Am G
}
A2 = 110.0


def _f(semi: float) -> float:
    return A2 * 2 ** (semi / 12.0)


def _tone(freq: float, dur: float, kind: str = "pluck") -> np.ndarray:
    n = max(1, int(dur * SR))
    t = np.arange(n) / SR
    if kind == "pluck":                                   # a soft marimba-like note
        w = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t) + 0.08 * np.sin(6 * np.pi * freq * t)
        env = np.exp(-t * 7.0) * np.minimum(1.0, t / 0.004)
    elif kind == "pad":                                   # a warm held chord tone
        w = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * freq * 2.003 * t)
        env = np.minimum(1.0, t / 0.35) * np.minimum(1.0, (dur - t) / 0.4).clip(0, 1)
    else:                                                 # bass
        w = np.tanh(1.6 * np.sin(2 * np.pi * freq * t))
        env = np.exp(-t * 2.5) * np.minimum(1.0, t / 0.01)
    return (w * env).astype(np.float32)


def _kick(dur: float = 0.18) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)).astype(np.float32)


def _hat(dur: float = 0.035, seed: int = 0) -> np.ndarray:
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n).astype(np.float32)
    x = np.diff(x, prepend=0.0).astype(np.float32)         # (brighter)
    return x * np.exp(-np.arange(n) / SR * 90).astype(np.float32) * 0.5


def made(seconds: float, mood: str = "light") -> np.ndarray:
    """The program's own music for a film of `seconds`, faded in and out (mono float32, 48 kHz)."""
    bpm, roots, minor, drums = MOODS.get(mood, MOODS["light"])
    beat = 60.0 / bpm
    bar = 4 * beat
    loop_bars = 8
    loop = np.zeros(int(loop_bars * bar * SR) + SR, np.float32)

    def put(a, at, g):
        i = int(at * SR)
        n = min(len(a), len(loop) - i)
        if n > 0:
            loop[i:i + n] += a[:n] * g
    for b in range(loop_bars):
        root = roots[b % len(roots)]
        third = 3 if minor[b % len(roots)] else 4
        chord = [root + 12, root + 12 + third, root + 19]
        t0 = b * bar
        for k, semi in enumerate(chord):                   # the pad
            put(_tone(_f(semi), bar, "pad"), t0, 0.05)
        pattern = [0, 1, 2, 1, 0, 2, 1, 2] if b % 2 == 0 else [0, 2, 1, 2, 0, 1, 2, 3]
        for s_, idx in enumerate(pattern):                 # the arpeggio, in eighths
            semi = (chord + [chord[0] + 12])[idx] + 12
            put(_tone(_f(semi), beat * 0.9, "pluck"), t0 + s_ * beat / 2, 0.10 if s_ % 2 == 0 else 0.07)
        for beat_i in (0, 2):                              # the bass
            put(_tone(_f(root), beat * 1.8, "bass"), t0 + beat_i * beat, 0.16)
        if drums > 0:
            for beat_i in range(4):
                if beat_i in (0, 2):
                    put(_kick(), t0 + beat_i * beat, 0.22 * drums)
                for half in (0, 1):
                    if drums >= 1.0 or half == 1:
                        put(_hat(seed=b * 8 + beat_i * 2 + half), t0 + (beat_i + 0.5 * half) * beat, 0.05 * drums)
    loop = loop[: int(loop_bars * bar * SR)]
    total = int(seconds * SR)
    out = np.tile(loop, total // len(loop) + 1)[:total]
    return _fade(out)


def _fade(a: np.ndarray, fin: float = 1.0, fout: float = 2.0) -> np.ndarray:
    a = a.astype(np.float32).copy()
    n_in, n_out = min(len(a), int(fin * SR)), min(len(a), int(fout * SR))
    if n_in:
        a[:n_in] *= np.linspace(0, 1, n_in, dtype=np.float32)
    if n_out:
        a[-n_out:] *= np.linspace(1, 0, n_out, dtype=np.float32)
    peak = float(np.max(np.abs(a))) if len(a) else 0.0
    return a / peak * 0.5 if peak > 0 else a


def from_file(path: str, seconds: float, ffmpeg: str) -> np.ndarray:
    """The owner's music file, looped to the film's length (mono float32, 48 kHz). OSError when it cannot be read."""
    if not Path(path).is_file():
        raise OSError("the music file is not there any more")
    try:                                                   # (decoded once, at most ten minutes of it, looped here)
        cp = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
                             "-t", f"{min(600.0, max(1.0, seconds)):.3f}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                            capture_output=True, timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise OSError("the music took too long to read")
    a = np.frombuffer(cp.stdout or b"", np.float32)
    if cp.returncode != 0 or len(a) < SR // 2:
        raise OSError("the music could not be read")
    total = int(seconds * SR)
    return _fade(np.tile(a, total // len(a) + 1)[:total])


def duck(music: np.ndarray, voice: np.ndarray, level: float = 0.22, under: float = 0.35) -> np.ndarray:
    """The music at `level`, lowered to `under` of that while someone speaks (smooth: 0.15 s down, 0.5 s up)."""
    n = min(len(music), len(voice))
    hop = int(0.05 * SR)
    frames = max(1, n // hop)
    env = np.array([float(np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2))) if (i + 1) * hop <= len(voice) else 0.0
                    for i in range(frames)])
    talk = (env > 0.02).astype(np.float32)
    g = np.ones(frames, np.float32)
    cur = 1.0
    for i in range(frames):                                # attack fast, release slow
        target = under if talk[i] else 1.0
        rate = 0.33 if target < cur else 0.1
        cur += (target - cur) * rate
        g[i] = cur
    gain = np.repeat(g, hop)
    gain = np.pad(gain, (0, max(0, len(music) - len(gain))), constant_values=g[-1] if len(g) else 1.0)[:len(music)]
    return (music * gain * level).astype(np.float32)


def bed(kind: str, seconds: float, voice: np.ndarray, mood: str = "light", path: str = "", ffmpeg: str = "ffmpeg") -> np.ndarray | None:
    """The film's music track (None: no music)."""
    if kind == "made":
        m = made(seconds, mood)
    elif kind == "file":
        m = from_file(path, seconds, ffmpeg)
    else:
        return None
    if len(m) < len(voice):
        m = np.pad(m, (0, len(voice) - len(m)))
    return duck(m[:len(voice)], voice)

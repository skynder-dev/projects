"""The beat of the reel's own music, and cuts placed on it.

detect(wav) -> {"beats": [s...], "bpm", "confidence", "strength_db", "clear", "shifted"}
  onset strength (positive change of 40 log-spaced band energies in dB, 10.7 ms steps), the tempo from its
  autocorrelation (55-140 BPM, around 100 preferred: a fast song is found at half its tempo), the beats by dynamic
  programming (D. Ellis, "Beat tracking by dynamic programming", 2007), and beat or off-beat decided by the kick drum
  and the bass (below 250 Hz).
  numpy only, a few hundred ms for a minute of music. clear: the onsets repeat with the beat period and are loud
  enough on the beats (not for a drone, noise, speech or quiet ambient music - then the cuts are left as they were).

snap_use(...) -> the length of one segment so that its cut (a hard cut, or the middle of a dissolve) falls on the
  nearest beat, within limits that keep the moment and the reel's length (never longer than the clip).
"""
from __future__ import annotations

import math, wave
from pathlib import Path

import numpy as np

HOP, NFFT = 512, 2048
MIN_PERIODIC = 0.15        # normalised autocorrelation of the onsets at the beat period (noise, speech: < 0.1)
MIN_STRENGTH_DB = 2.0      # mean onset on the beats, dB per band (a drone: < 1)


def _mono(path: Path):
    with wave.open(str(path), "rb") as w:
        sr, ch, n, width = w.getframerate(), w.getnchannels(), w.getnframes(), w.getsampwidth()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError("BEATS_WAV_NOT_16_BIT")
    x = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, ch).mean(axis=1) / 32768.0
    return x, sr


def _bands(sr: int, n_bands: int = 40, fmin: float = 30.0, fmax: float = 16000.0) -> np.ndarray:
    """Log-spaced frequency bands (like a mel scale): a kick drum counts as much as a hi-hat."""
    freqs = np.fft.rfftfreq(NFFT, 1.0 / sr)
    edges = np.geomspace(fmin, min(fmax, sr / 2 - 1), n_bands + 2)
    m = np.zeros((n_bands, len(freqs)), np.float32)
    for k in range(n_bands):
        lo, mid, hi = edges[k], edges[k + 1], edges[k + 2]
        up = (freqs - lo) / max(1e-9, mid - lo)
        down = (hi - freqs) / max(1e-9, hi - mid)
        m[k] = np.maximum(0.0, np.minimum(up, down))
        if m[k].sum() == 0:                                  # a band narrower than one bin: the nearest bin
            m[k, int(np.argmin(np.abs(freqs - mid)))] = 1.0
    return m / m.sum(axis=1, keepdims=True)


LOW_HZ = 250.0


def _norm(env: np.ndarray, sr: int) -> np.ndarray:
    if env.size == 0:
        return env
    # minus the local mean (about 0.5 s): loudness changes of the whole song are not beats
    w = max(3, int(round(0.5 * sr / HOP)) | 1)
    if len(env) < w:                                         # shorter than half a second: nothing to compare with
        return np.zeros_like(env)
    loc = np.convolve(env, np.ones(w, np.float32) / w, mode="same")
    env = np.maximum(0.0, env - loc)
    s = float(env.std())
    return env / s if s > 1e-9 else env


def envelopes(x: np.ndarray, sr: int):
    """Onset strength of all bands and of the bands below LOW_HZ (kick drum, bass): the positive change of the band
    energies in dB, averaged over the bands, one value per HOP samples (frame i: the change into window i+1);
    normalised, and (third) the raw values in dB."""
    if len(x) < NFFT * 4:
        return np.zeros(0, np.float32), np.zeros(0, np.float32), np.zeros(0, np.float32)
    win = np.hanning(NFFT).astype(np.float32)
    fb = _bands(sr)
    centers = (fb * np.fft.rfftfreq(NFFT, 1.0 / sr)).sum(axis=1)
    low = centers < LOW_HZ
    starts = np.arange(0, len(x) - NFFT + 1, HOP)
    prev, f_all, f_low = None, [], []
    for k in range(0, len(starts), 1024):                  # bounded memory for a long song
        fr = np.stack([x[s:s + NFFT] for s in starts[k:k + 1024]]) * win
        power = np.abs(np.fft.rfft(fr, axis=1)) ** 2
        db = (10.0 * np.log10(np.maximum(1e-10, power @ fb.T))).astype(np.float32)
        db = np.maximum(db, db.max() - 80.0)                 # silence is not a change
        both = db if prev is None else np.vstack([prev, db])
        pos = np.maximum(0.0, np.diff(both, axis=0))
        f_all.append(pos.mean(axis=1)); f_low.append(pos[:, low].mean(axis=1))
        prev = db[-1:]
    raw = np.concatenate(f_all).astype(np.float32)
    return _norm(raw.copy(), sr), _norm(np.concatenate(f_low).astype(np.float32), sr), raw


def onset_envelope(x: np.ndarray, sr: int) -> np.ndarray:
    return envelopes(x, sr)[0]


def _around(env: np.ndarray, frames, r: int = 2) -> float:
    vals = [float(env[max(0, int(i) - r):int(i) + r + 1].max()) for i in frames if 0 <= int(i) < len(env)]
    return float(np.mean(vals)) if vals else 0.0


def _frame_time(i, sr: int) -> float:
    # flux frame i compares window i with window i+1: the onset is heard around the middle of window i+1
    return ((np.asarray(i, np.float64) + 1) * HOP + NFFT / 2) / sr + 0.013


def tempo_period(env: np.ndarray, fps: float) -> float:
    """Beat period in frames: the autocorrelation peak between 55 and 140 BPM, weighted towards ~100 BPM. A fast song
    is found at half its tempo - every cut is still on a beat; twice the tempo would put cuts between the beats."""
    n = len(env)
    f = np.fft.rfft(env - env.mean(), 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    lo, hi = int(fps * 60 / 140), min(n - 1, int(math.ceil(fps * 60 / 55)))
    if hi <= lo + 2:
        return 0.0
    lags = np.arange(lo, hi + 1)
    bpm = 60.0 * fps / lags
    weight = np.exp(-0.5 * (np.log2(bpm / 100.0) / 0.9) ** 2)
    sc = ac[lo:hi + 1] * weight
    k = int(np.argmax(sc))
    p = float(lags[k])
    if 0 < k < len(sc) - 1:                                  # parabolic refinement of the peak
        a, b, c = sc[k - 1], sc[k], sc[k + 1]
        den = a - 2 * b + c
        if abs(den) > 1e-12:
            p += 0.5 * (a - c) / den
    return p


def track(env: np.ndarray, period: float, tightness: float = 100.0) -> list[int]:
    """Ellis 2007: the best chain of beats, each about one period after the previous one and on strong onsets."""
    n = len(env)
    if n == 0 or period <= 1:
        return []
    score = env.astype(np.float64).copy()
    back = np.full(n, -1, np.int64)
    lo_off, hi_off = int(round(2 * period)), max(1, int(round(period / 2)))
    for t in range(n):
        a, b = t - lo_off, t - hi_off
        if b < 0:
            continue
        prev = np.arange(max(0, a), b + 1)
        cand = score[prev] - tightness * np.log((t - prev) / period) ** 2
        k = int(np.argmax(cand))
        if cand[k] > 0:
            score[t] = env[t] + cand[k]
            back[t] = prev[k]
    # the last beat: the last local maximum of the score that is clearly a beat chain
    peaks = [i for i in range(1, n - 1) if score[i] >= score[i - 1] and score[i] > score[i + 1]]
    if not peaks:
        return []
    med = float(np.median([score[i] for i in peaks]))
    last = max(i for i in peaks if score[i] >= 0.5 * med)
    beats = [last]
    while back[beats[-1]] >= 0:
        beats.append(int(back[beats[-1]]))
    return beats[::-1]


def detect(wav: Path) -> dict:
    x, sr = _mono(Path(wav))
    none = {"beats": [], "bpm": 0.0, "confidence": 0.0, "strength_db": 0.0, "clear": False, "shifted": False}
    if len(x) < 4 * sr:                                      # a jingle or a sound effect: no beat to follow
        return none
    env, low, raw = envelopes(x, sr)
    fps = sr / HOP
    if len(env) < fps * 3:
        return none
    p = tempo_period(env, fps)
    fr = track(env, p) if p > 0 else []
    if len(fr) < 4:
        return none
    # beat or off-beat: a hi-hat between the beats can be as strong as the beat itself; the kick drum and the bass
    # are on the beat - when they are clearly stronger half way between the found beats, those are the beats
    mids = [(a + b) / 2.0 for a, b in zip(fr, fr[1:])]
    shifted = _around(low, mids) > 1.5 * max(1e-9, _around(low, fr)) and _around(low, mids) > 0.5
    if shifted:
        fr = []
        for m in mids:
            i0, i1 = max(0, int(round(m)) - 3), min(len(env), int(round(m)) + 4)
            fr.append(i0 + int(np.argmax(env[i0:i1])))
    # a clear beat: the onsets repeat with this period (normalised autocorrelation) and are loud enough on the beats
    # (a drone, noise, speech or quiet ambient music: no - the cuts stay as they were)
    e = env - env.mean()
    f = np.fft.rfft(e, 2 * len(e))
    ac = np.fft.irfft(f * np.conj(f))[:len(e)]
    periodic = float(ac[int(round(p))] / max(1e-9, ac[0]))
    strength = _around(raw, fr)
    clear = periodic >= MIN_PERIODIC and strength >= MIN_STRENGTH_DB and strength >= 1.8 * float(raw.mean())
    beats = [round(float(t), 4) for t in _frame_time(fr, sr)]
    return {"beats": beats, "bpm": round(float(60.0 * fps / p), 2), "confidence": round(periodic, 3), "strength_db": round(strength, 2),
            "clear": bool(clear), "shifted": bool(shifted)}


def repeat(beats: list[float], song_s: float, total_s: float) -> list[float]:
    """The music is repeated when the reel is longer than the song: so are its beats."""
    if not beats or song_s <= 0:
        return list(beats)
    out = []
    k = 0
    while k * song_s < total_s + 2:
        out += [b + k * song_s for b in beats if b < song_s]
        k += 1
    return out


def snap_use(start_s: float, planned_use: float, td_out: float, td_in: float, clip_max: float, beats: list[float], fps: int = 30,
             planned_cut: float | None = None, max_off: float = 1.0):
    """Length (a whole number of frames when rendered) of a segment starting at start_s (reel time) so that its cut - a
    hard cut, or the middle of the dissolve td_out into the next segment - is on a beat: the beat nearest to where the
    PLAN has this cut (planned_cut: the planned reel timeline, so earlier snaps never add up - the reel stays within
    about a beat of its planned length). Limits: never shorter than 1 s (or 60% of the plan) or than its dissolves,
    never longer than the clip or 1 s more than planned, the beat at most max_off from the planned cut (about a beat
    and a half: moments used to their full clip length can only get shorter, so the reel may end up to that much
    shorter than planned). Returns (use_s, beat_s or None)."""
    if planned_cut is None:
        planned_cut = start_s + planned_use - td_out / 2.0
    lo = max(1.0, 0.6 * planned_use, td_in + td_out + 0.4)
    hi = min(float(clip_max), planned_use + 1.0)
    if hi < lo:
        return planned_use, None
    # a beat; when none can be reached (a moment used to its full length can only get shorter), half way between two
    # beats - still in time with the music
    halves = [(a + b) / 2.0 for a, b in zip(beats, beats[1:])]
    for cands in (beats, halves):
        for b in sorted((b for b in cands if abs(b - planned_cut) <= max_off), key=lambda b: abs(b - planned_cut)):
            frames = round((b - start_s + td_out / 2.0) * fps)
            if lo - 1e-6 <= frames / fps <= hi + 1e-6:
                # a quarter frame less: the segment is cut with "-t" at 3 decimals and ends after the frame that
                # starts before that time - exactly `frames` frames (5.367 s for 161 frames gave 162)
                return (frames - 0.25) / fps, b
    return planned_use, None


def period(beats: list[float]) -> float:
    return float(np.median(np.diff(beats))) if len(beats) > 2 else 0.5


def max_offset(beats: list[float]) -> float:
    return max(1.0, 1.5 * period(beats))


def plan(durations: list[float], transitions: list[float], clip_max: list[float], beats: list[float], fps: int = 30) -> list:
    """The whole reel planned at once (for checks; the engine does the same segment by segment with the real lengths):
    [(use_s, beat_s or None)]."""
    out, start, plan_t = [], 0.0, 0.0
    for i, d in enumerate(durations):
        td_in = transitions[i - 1] if i > 0 else 0.0
        td_out = transitions[i] if i < len(durations) - 1 else 0.0
        use, hit = snap_use(start, d, td_out, td_in, clip_max[i], beats, fps, plan_t + d - td_out / 2.0, max_offset(beats))
        frames = round(((hit - start + td_out / 2.0) if hit is not None else use) * fps)
        out.append((frames / fps, hit))
        start += frames / fps - td_out
        plan_t += d - td_out
    return out

from __future__ import annotations
import math
import numpy as np

ALGO_VERSION = "P11_CAMERA_DROP_TRIM_SHADOW_V1"

def choose_camera_drop_trim(rows, min_retained_s=2.5, max_trim_fraction=0.35):
    """Detect a sustained terminal downward-camera / dark foreground obstruction.

    Required row fields:
      t, quality, exposure, bottom_dark_fraction, lower_upper_ratio

    This function accepts no BENCH target/reject timestamps.
    """
    if len(rows) < 10:
        return {"trim": False, "reason": "insufficient_samples", "algorithm": ALGO_VERSION}

    cols = {}
    for key in ("t", "quality", "exposure", "bottom_dark_fraction", "lower_upper_ratio"):
        cols[key] = np.asarray([float(r[key]) for r in rows], dtype=float)
        if not np.isfinite(cols[key]).all():
            return {"trim": False, "reason": "non_finite", "algorithm": ALGO_VERSION}

    t = cols["t"]
    if np.any(np.diff(t) <= 0):
        return {"trim": False, "reason": "non_monotonic_time", "algorithm": ALGO_VERSION}

    step = float(np.median(np.diff(t)))
    start = float(t[0])
    end = float(t[-1] + step)
    duration = end - start
    if duration <= min_retained_s + step:
        return {"trim": False, "reason": "candidate_too_short", "algorithm": ALGO_VERSION}

    dark = cols["bottom_dark_fraction"]
    ratio = cols["lower_upper_ratio"]
    quality = cols["quality"]
    exposure = cols["exposure"]

    # Baseline is intentionally taken before the terminal search zone.
    baseline_n = max(4, int(math.floor(len(rows) * 0.55)))
    base_dark = float(np.median(dark[:baseline_n]))
    base_ratio = float(np.median(ratio[:baseline_n]))

    # Generic geometric obstruction contract:
    # - bottom quarter becomes materially darker than its own baseline;
    # - lower half simultaneously becomes materially darker than upper half.
    dark_threshold = max(0.30, base_dark + 0.20)
    ratio_threshold = min(0.70, base_ratio - 0.15)
    warning_ratio_threshold = min(0.82, base_ratio - 0.08)

    full = []
    warning = []
    for d, r in zip(dark, ratio):
        full.append(bool(d >= dark_threshold and r <= ratio_threshold))
        warning.append(bool(d >= dark_threshold or r <= warning_ratio_threshold))

    search_lo = max(4, int(math.floor(len(rows) * 0.55)))
    full_onset = None
    # Require at least 3 consecutive obstructed samples: 0.75 s at 4 fps.
    for i in range(search_lo, len(rows) - 2):
        if all(full[i:i + 3]):
            full_onset = i
            break

    if full_onset is None:
        return {
            "trim": False,
            "reason": "no_sustained_terminal_camera_drop",
            "algorithm": ALGO_VERSION,
            "base_dark": round(base_dark, 6),
            "dark_threshold": round(dark_threshold, 6),
            "base_ratio": round(base_ratio, 6),
            "ratio_threshold": round(ratio_threshold, 6),
        }

    # If the immediately preceding sample already shows a warning transition,
    # treat it as transition onset. Cut one sample before that onset so the
    # exported clip ends on a fully clean frame rather than inside the motion.
    transition = full_onset
    if full_onset - 1 >= search_lo and warning[full_onset - 1]:
        transition = full_onset - 1

    cut_i = max(search_lo - 1, transition - 1)
    cut_s = float(t[cut_i])
    retained_s = cut_s - start
    trimmed_s = end - cut_s

    if retained_s < min_retained_s:
        return {"trim": False, "reason": "min_retained_guard", "algorithm": ALGO_VERSION}
    if trimmed_s / duration > max_trim_fraction:
        return {"trim": False, "reason": "max_trim_fraction_guard", "algorithm": ALGO_VERSION}

    return {
        "trim": True,
        "reason": "sustained_terminal_camera_drop",
        "algorithm": ALGO_VERSION,
        "cut_s": round(cut_s, 3),
        "transition_s": round(float(t[transition]), 3),
        "full_onset_s": round(float(t[full_onset]), 3),
        "sample_step_s": round(step, 6),
        "retained_s": round(retained_s, 3),
        "trimmed_s": round(trimmed_s, 3),
        "base_dark": round(base_dark, 6),
        "dark_threshold": round(dark_threshold, 6),
        "base_ratio": round(base_ratio, 6),
        "ratio_threshold": round(ratio_threshold, 6),
        "warning_ratio_threshold": round(warning_ratio_threshold, 6),
        "transition_metrics": {
            "bottom_dark_fraction": round(float(dark[transition]), 6),
            "lower_upper_ratio": round(float(ratio[transition]), 6),
            "quality": round(float(quality[transition]), 6),
            "exposure": round(float(exposure[transition]), 6),
        },
    }

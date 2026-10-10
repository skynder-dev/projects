"""Technical acceptance of the final MP4 using ffprobe/ffmpeg (no trust in the renderer's own report)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def probe(mp4: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def verify_video(mp4: Path, expected_s: float, review_dir: Path, mids: list[float]) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    if not shutil.which("ffprobe"):
        return {"pass": False, "checks": [{"check": "ffprobe", "pass": False, "detail": "missing"}]}
    check("file_exists", mp4.exists() and mp4.stat().st_size > 50_000, f"{mp4.stat().st_size if mp4.exists() else 0} bytes")
    info = probe(mp4)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0))
    check("video_stream_h264", v and v.get("codec_name") == "h264", v and v.get("codec_name"))
    check("dimensions_1080x1920", v and (v["width"], v["height"]) == (1080, 1920), v and f"{v['width']}x{v['height']}")
    check("pix_fmt_yuv420p", v and v.get("pix_fmt") == "yuv420p", v and v.get("pix_fmt"))
    fr = v and v.get("avg_frame_rate", "0/1")
    fps = (lambda n, d: float(n) / float(d) if float(d) else 0)(*fr.split("/")) if fr else 0
    check("fps_30", abs(fps - 30) < 0.05, round(fps, 3))
    check("audio_stream_aac", a and a.get("codec_name") == "aac", a and a.get("codec_name"))
    check("duration_matches_timeline", abs(dur - expected_s) <= 0.35, f"{dur:.2f}s vs timeline {expected_s:.2f}s")
    check("duration_reel_range", 15 <= dur <= 90, f"{dur:.2f}s")
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "null", "-"], capture_output=True, text=True)
    check("full_decode_no_errors", dec.returncode == 0 and not dec.stderr.strip(), dec.stderr.strip()[:300] or "clean")
    vol = subprocess.run(["ffmpeg", "-i", str(mp4), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", vol)
    peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", vol)
    mv = float(mean[1]) if mean else -999.0
    check("audio_not_silent", mv > -40, f"mean {mv} dB, peak {peak[1] if peak else '?'} dB")
    # frames for human review + contact sheet
    review_dir.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for i, t in enumerate(mids, 1):
        p = review_dir / f"frame_{i:02d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", str(p)],
                       check=True)
        thumbs.append(p)
    check("review_frames_extracted", all(p.exists() for p in thumbs), len(thumbs))
    sheet = contact_sheet(thumbs, review_dir / "contact_sheet.jpg")
    return {"pass": all(c["pass"] for c in checks), "duration_s": round(dur, 3), "fps": round(fps, 3),
            "mean_volume_db": mv, "checks": checks, "contact_sheet": sheet.name if sheet else None,
            "ffprobe": {"format": {k: info["format"].get(k) for k in ("format_name", "duration", "size", "bit_rate")},
                        "video": v and {k: v.get(k) for k in ("codec_name", "profile", "width", "height", "pix_fmt", "avg_frame_rate")},
                        "audio": a and {k: a.get(k) for k in ("codec_name", "sample_rate", "channels")}}}


def contact_sheet(frames: list[Path], out: Path, cols: int = 4, tw: int = 270, th: int = 480):
    if not frames:
        return None
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 12, rows * th + (rows + 1) * 12), (20, 20, 20))
    for i, p in enumerate(frames):
        im = Image.open(p).convert("RGB").resize((tw, th))
        sheet.paste(im, (12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 12)))
    sheet.save(out, quality=88)
    return out


def asr_check(narration: Path, expected: str, model_name: str = "base.en") -> dict | None:
    """Transcribe the narration and confirm it actually says the script. None if ASR is not installed."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(narration), language="en", beam_size=5)
    text = " ".join(s.text for s in segs).strip()

    def words(t):
        return [w for w in re.findall(r"[a-z]+", t.lower()) if len(w) >= 4]

    exp, got = words(expected), set(words(text))
    recall = sum(1 for w in exp if w in got) / max(1, len(exp))
    nums_exp = set(re.findall(r"\d[\d,]*", expected.replace(",", "")))
    nums_got = set(re.findall(r"\d[\d,]*", text.replace(",", "")))
    return {"check": "narration_asr_matches_script", "pass": recall >= 0.85,
            "detail": f"content-word recall {recall:.2f} (model {model_name}); numbers heard "
                      f"{sorted(nums_exp & nums_got)} of {sorted(nums_exp)}",
            "transcript": text}

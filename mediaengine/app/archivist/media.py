from __future__ import annotations
from .platform_adapter import process_kwargs

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


def _run(*args, **kwargs):
    return subprocess.run(*args, **process_kwargs(kwargs))

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".3gp", ".mts", ".m2ts", ".wmv", ".mpg", ".mpeg"}

NOISE_SEGMENTS = {
    "$recycle.bin", "system volume information", "windows", "program files", "program files (x86)",
    "programdata", "perflogs", "recovery", "$winreagent", "appdata", "node_modules", "__pycache__",
    ".git", ".cache", "cache", "caches", "temp", "tmp", "steam", "steamlibrary", "steamapps",
    "xboxgames", "games", "game", "epic games", "epicgames", "riot games", "riotgames", "ubisoft", "battle.net",
    "battlenet", "ea games", "eagames", "origin games", "gog galaxy", "gog games",
}


def media_type_for(path_or_name: str | Path) -> str | None:
    ext = Path(str(path_or_name)).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def should_skip_dir(path: Path, ignore_noise: bool) -> bool:
    if not ignore_noise:
        return False
    parts = {p.lower() for p in path.parts}
    return any(seg in parts for seg in NOISE_SEGMENTS)


def walk_media(root: Path, ignore_noise=True, min_image_bytes=0, min_video_bytes=0, errors: list | None = None):
    if root.is_file():
        mt = media_type_for(root)
        if mt:
            try:
                sz = root.stat().st_size
                if (mt == "image" and sz < min_image_bytes) or (mt == "video" and sz < min_video_bytes):
                    return
            except Exception:
                return
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root, onerror=(errors.append if errors is not None else None)):
        dp = Path(dirpath)
        if ignore_noise:
            # Only the folder's own name matters: a source root such as D:\Games\Clips or a path
            # under a "Temp" parent must not hide everything below it.
            dirnames[:] = [d for d in dirnames if not should_skip_dir(Path(d), True)]
        for name in filenames:
            p = dp / name
            mt = media_type_for(p)
            if not mt:
                continue
            try:
                size = p.stat().st_size
            except Exception:
                continue
            if mt == "image" and size < min_image_bytes:
                continue
            if mt == "video" and size < min_video_bytes:
                continue
            yield p


def sha256_file(path: Path, chunk=8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _ffmpeg_exe() -> str | None:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def probe_rights_flags(path: Path, media_type: str) -> dict:
    """Cheap local rights-risk hints. Never returns a legal conclusion.

    We intentionally keep this conservative: detect whether the user's own video
    still contains an audio stream and look for a few explicit venue/performance
    clues in local metadata/path text. Location/property permission is ultimately a
    human-context question, so the UI lets the user tag/clear it manually.
    """
    out = {"audio_present": False, "hints": []}
    hay = str(path).lower()
    if media_type != "video":
        return out
    exe = _ffmpeg_exe()
    stderr = ""
    if exe:
        try:
            r = _run([exe, "-hide_banner", "-i", str(path)], capture_output=True, text=True, timeout=25, errors="replace")
            stderr = r.stderr or ""
            out["audio_present"] = bool(re.search(r"\bAudio:\s", stderr))
            hay += "\n" + stderr.lower()
        except Exception:
            pass
    if "gatorland" in hay:
        out["hints"].append("gatorland")
    if "bellagio" in hay:
        out["hints"].append("bellagio")
    if "exosphere" in hay or ("sphere" in hay and ("vegas" in hay or "las vegas" in hay)):
        out["hints"].append("sphere_exterior")
    perf = ("concert", "performance", "show", "fountain", "parade", "fireworks", "festival")
    if out["audio_present"] and any(k in hay for k in perf):
        out["hints"].append("possible_performance_audio")
    return out


def probe_duration(path: Path) -> float | None:
    exe = _ffmpeg_exe()
    if not exe:
        return None
    try:
        r = _run([exe, "-hide_banner", "-i", str(path)], capture_output=True, text=True, timeout=30, errors="replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
        if not m:
            return _measured_duration(exe, Path(path)) if Path(path).suffix.lower() in (".webm", ".mkv") else None
        h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mnt * 60 + sec
    except Exception:
        return None


_MEASURED: dict = {}


def _measured_duration(exe: str, path: Path) -> float | None:
    """A browser / screen recording often has no length written in the file ("Duration: N/A"): read the file once
    without decoding and take the time of the last picture. Cached per file state."""
    try:
        st = path.stat()
        key = (str(path), st.st_size, st.st_mtime_ns)
        if key not in _MEASURED:
            r = _run([exe, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
                     capture_output=True, text=True, timeout=600, errors="replace")
            t = re.findall(r"time=\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
            _MEASURED[key] = (int(t[-1][0]) * 3600 + int(t[-1][1]) * 60 + float(t[-1][2])) if t and r.returncode == 0 else None
        return _MEASURED[key] or None
    except Exception:
        return None


def make_thumbnail(path: Path, media_type: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if media_type == "image":
        try:
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except Exception:
                pass
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((480, 360))
                im.save(dest, "JPEG", quality=82)
            return True
        except Exception:
            return False
    exe = _ffmpeg_exe()
    if not exe:
        return False
    duration = probe_duration(path) or 1.0
    seek = max(0.2, min(5.0, duration * 0.12))
    try:
        # Use the same multi-attempt seek strategy as storyboards. Phone/VFR
        # files that reject one fast seek still get an accurate/earlier fallback.
        return _storyboard_extract_frame(exe, path, seek, dest, duration)
    except Exception:
        return False



def _storyboard_extract_frame(exe: str, path: Path, ts: float, dest: Path, duration: float) -> bool:
    """Extract one preview frame with fast-seek first and a more accurate fallback."""
    safe_ts = max(0.0, min(float(ts), max(0.0, float(duration) - 0.03)))
    attempts = [
        # Fast seek: cheap for long phone/drone videos.
        [exe, "-hide_banner", "-loglevel", "error", "-threads", "2",
         "-ss", f"{safe_ts:.3f}", "-i", str(path), "-map", "0:v:0",
         "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", "-q:v", "5", "-y", str(dest)],
        # Accurate seek: slower, but fixes files where pre-input seek lands on an unusable GOP/keyframe.
        [exe, "-hide_banner", "-loglevel", "error", "-threads", "2",
         "-i", str(path), "-ss", f"{safe_ts:.3f}", "-map", "0:v:0",
         "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", "-q:v", "5", "-y", str(dest)],
    ]
    # Near the end, some VFR/phone files report a duration a little beyond the last decodable frame.
    if safe_ts > 0.25:
        earlier = max(0.0, safe_ts - min(0.45, max(0.08, duration * 0.01)))
        attempts.extend([
            [exe, "-hide_banner", "-loglevel", "error", "-threads", "2",
             "-ss", f"{earlier:.3f}", "-i", str(path), "-map", "0:v:0",
             "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", "-q:v", "5", "-y", str(dest)],
            [exe, "-hide_banner", "-loglevel", "error", "-threads", "2",
             "-i", str(path), "-ss", f"{earlier:.3f}", "-map", "0:v:0",
             "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", "-q:v", "5", "-y", str(dest)],
        ])
    for cmd in attempts:
        try:
            dest.unlink(missing_ok=True)
            r = _run(cmd, capture_output=True, timeout=100)
            if r.returncode == 0 and dest.exists() and dest.stat().st_size > 100:
                return True
        except Exception:
            pass
    dest.unlink(missing_ok=True)
    return False


def make_storyboard(path: Path, dest_dir: Path, frames: int = 8, fingerprint: str | None = None) -> dict | None:
    """Create a consistent sparse storyboard for fast browsing.

    The target is exactly N frames (8 by default). Each requested timestamp gets a
    fast seek plus an accurate fallback. If a damaged/very-short file still cannot
    decode every requested position, the nearest successfully decoded frame is
    copied into the missing slot so the Library UI remains structurally consistent.
    Originals are never modified.
    """
    exe = _ffmpeg_exe()
    if not exe or not path.exists():
        return None
    duration = probe_duration(path)
    if not duration or duration <= 0:
        duration = 1.0
    target = max(4, min(12, int(frames or 8)))

    # Avoid the first/last few percent where phones often contain pocket/black frames.
    lo = min(duration * 0.08, max(0.15, duration * 0.15))
    hi = max(lo, duration * 0.92)
    if duration < 3:
        lo, hi = duration * 0.12, duration * 0.88
    times = [lo + (hi - lo) * i / (target - 1) for i in range(target)]

    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = dest_dir.with_name(dest_dir.name + ".part")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    extracted: dict[int, tuple[Path, float, float]] = {}
    try:
        for i, ts in enumerate(times):
            out = tmp_dir / f"slot_{i:02d}.jpg"
            if not _storyboard_extract_frame(exe, path, ts, out, float(duration)):
                continue
            b, d = _frame_metrics(out)
            if b is None or d is None:
                score = -999.0
            else:
                score = float(d) * 1.6 - abs(float(b) - 128.0) * 0.22
                if b < 24 or b > 238:
                    score -= 90.0
                elif b < 42 or b > 225:
                    score -= 25.0
            extracted[i] = (out, float(ts), float(score))

        if not extracted:
            return None

        # Always return the configured number of slots. Normally every slot is a real
        # independently decoded frame. Only genuinely troublesome/very-short files
        # reuse the nearest successful frame, and the metadata records that fallback.
        successful = sorted(extracted)
        final_frames = []
        fallback_slots = []
        scored = []
        for i, ts in enumerate(times):
            if i in extracted:
                src, actual_ts, score = extracted[i]
            else:
                nearest = min(successful, key=lambda j: abs(j - i))
                src, actual_ts, score = extracted[nearest]
                fallback_slots.append(i)
            dst = tmp_dir / f"story_{i:02d}.jpg"
            # Always copy from slot_*.jpg. Several missing positions may need the
            # same nearest successful source, so moving it early would break later
            # fallback slots.
            shutil.copy2(src, dst)
            final_frames.append({"index": i, "time": round(float(ts), 3), "file": dst.name})
            scored.append((score, i))

        for stray in tmp_dir.glob("slot_*.jpg"):
            stray.unlink(missing_ok=True)

        scored.sort(reverse=True)
        best_compact = int(scored[0][1]) if scored else 0
        meta = {
            "version": 2,
            "duration": round(float(duration), 3),
            "fingerprint": fingerprint or "",
            "target_frames": int(target),
            "best_index": best_compact,
            "fallback_slots": fallback_slots,
            "frames": final_frames,
        }
        (tmp_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        tmp_dir.replace(dest_dir)
        return meta
    finally:
        if tmp_dir.exists() and tmp_dir != dest_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


EXPLICIT_CLASSES = {
    "BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED",
}
_detector = None
_detector_error = None


def _detector_instance():
    global _detector, _detector_error
    if _detector is not None:
        return _detector
    if _detector_error is not None:
        return None
    try:
        from nudenet import NudeDetector
        _detector = NudeDetector()
        return _detector
    except Exception as e:
        _detector_error = str(e)
        return None


def _score(detections):
    best = 0.0
    kept = []
    for d in detections or []:
        cls = str(d.get("class") or d.get("label") or "").upper()
        score = float(d.get("score") or 0)
        if cls in EXPLICIT_CLASSES:
            best = max(best, score)
            kept.append({"class": cls, "score": round(score, 4)})
    return best, kept


def _read_image_array(image_path: Path):
    """Decode an image to a BGR array; works for non-ASCII Windows paths and HEIC when pillow_heif exists."""
    import numpy as np
    try:
        import cv2
        data = np.fromfile(str(image_path), dtype=np.uint8)
        arr = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
        if arr is not None:
            return arr
    except Exception:
        pass
    try:
        try:
            import pillow_heif  # optional
            pillow_heif.register_heif_opener()
        except Exception:
            pass
        from PIL import Image
        with Image.open(str(image_path)) as im:
            rgb = np.asarray(im.convert("RGB"))
        return rgb[:, :, ::-1].copy()
    except Exception:
        return None


def _detect_path(detector, image_path: Path):
    """Detections for one image, or None when the image could not be examined (privacy must then fail closed)."""
    arr = _read_image_array(image_path)
    if arr is not None:
        try:
            return detector.detect(arr) or []
        except Exception:
            pass
    try:
        # NudeNet v3 also accepts a file path (fails on some non-ASCII paths on Windows).
        res = detector.detect(str(image_path))
        return res or []
    except Exception:
        return None


def analyze_privacy(path: Path, media_type: str, samples: int = 10) -> tuple[float | None, list, str | None]:
    detector = _detector_instance()
    if detector is None:
        return None, [], "privacy_detector_unavailable"
    if media_type == "image":
        try:
            det = _detect_path(detector, path)
            if det is None:
                return None, [], "privacy_unreadable"
            score, kept = _score(det)
            return score, kept, None
        except Exception as e:
            return None, [], f"privacy_error:{e}"

    exe = _ffmpeg_exe()
    if not exe:
        return None, [], "ffmpeg_unavailable"
    duration = probe_duration(path)
    samples = max(4, min(24, int(samples or 10)))
    with tempfile.TemporaryDirectory(prefix="archivist_frames_") as td:
        out_pattern = str(Path(td) / "frame_%03d.jpg")
        if duration and duration > 0:
            fps = min(2.0, max(0.02, samples / duration))
            vf = f"fps={fps:.6f},scale='min(720,iw)':-2"
        else:
            vf = "fps=1/8,scale='min(720,iw)':-2"
        try:
            r = _run([
                exe, "-hide_banner", "-loglevel", "error", "-threads", "2", "-i", str(path), "-vf", vf,
                "-frames:v", str(samples), "-q:v", "5", "-y", out_pattern
            ], capture_output=True, timeout=900)
            frames = sorted(Path(td).glob("frame_*.jpg"))
            if not frames:
                return None, [], "video_decode_failed"
            best = 0.0
            all_kept = []
            failed = 0
            for i, frame in enumerate(frames):
                det = _detect_path(detector, frame)
                if det is None:
                    failed += 1
                    continue
                sc, kept = _score(det)
                best = max(best, sc)
                for k in kept:
                    all_kept.append({**k, "sample": i + 1})
            if failed:
                return None, [], f"privacy_unreadable:{failed}/{len(frames)}"
            return best, all_kept[:40], None
        except subprocess.TimeoutExpired:
            return None, [], "video_decode_timeout"
        except Exception as e:
            return None, [], f"privacy_error:{e}"


def _frame_metrics(image_path: Path) -> tuple[float | None, float | None]:
    """Return brightness (0-255) and edge-detail score (0-100-ish)."""
    try:
        from PIL import ImageStat, ImageFilter
        with Image.open(image_path) as im:
            im = ImageOps.exif_transpose(im).convert("L")
            im.thumbnail((640, 640))
            brightness = float(ImageStat.Stat(im).mean[0])
            edges = im.filter(ImageFilter.FIND_EDGES)
            stat = ImageStat.Stat(edges)
            # Std-dev of edge response is a cheap blur/detail proxy; do not treat it as aesthetics.
            detail = min(100.0, float(stat.stddev[0]) * 4.0)
            return brightness, detail
    except Exception:
        return None, None


def technical_quality(path: Path, media_type: str, samples: int = 5) -> tuple[float | None, str, str]:
    """Cheap technical triage, never an aesthetic judgment.

    Returns score, status(ok/review/unavailable), reason. It is deliberately conservative:
    low light / extreme exposure / very low detail can trigger review, but never deletion.
    """
    frames: list[Path] = []
    tmp = None
    try:
        if media_type == "image":
            frames = [path]
        else:
            exe = _ffmpeg_exe()
            if not exe:
                return None, "unavailable", "ffmpeg_unavailable"
            duration = probe_duration(path)
            samples = max(3, min(8, int(samples or 5)))
            tmp = tempfile.TemporaryDirectory(prefix="archivist_quality_")
            pattern = str(Path(tmp.name) / "q_%03d.jpg")
            if duration and duration > 0:
                fps = max(0.01, min(1.0, samples / duration))
                vf = f"fps={fps:.6f},scale='min(640,iw)':-2"
            else:
                vf = "fps=1/10,scale='min(640,iw)':-2"
            r = _run([exe, "-hide_banner", "-loglevel", "error", "-threads", "2", "-i", str(path), "-vf", vf,
                      "-frames:v", str(samples), "-q:v", "6", "-y", pattern],
                     capture_output=True, timeout=600)
            frames = sorted(Path(tmp.name).glob("q_*.jpg"))
            if r.returncode != 0 or not frames:
                return None, "unavailable", "video_sample_failed"

        vals = [_frame_metrics(f) for f in frames]
        vals = [(b, d) for b, d in vals if b is not None and d is not None]
        if not vals:
            return None, "unavailable", "quality_metrics_failed"
        brightness = sum(v[0] for v in vals) / len(vals)
        detail = sum(v[1] for v in vals) / len(vals)
        score = 100.0
        reasons = []
        if brightness < 28:
            score -= 38; reasons.append("very_dark")
        elif brightness < 48:
            score -= 18; reasons.append("dark")
        elif brightness > 235:
            score -= 35; reasons.append("very_bright")
        elif brightness > 220:
            score -= 15; reasons.append("bright")
        if detail < 10:
            score -= 35; reasons.append("very_low_detail")
        elif detail < 18:
            score -= 15; reasons.append("low_detail")
        score = max(0.0, min(100.0, score))
        status = "review" if score < 55 else "ok"
        return round(score, 1), status, ",".join(reasons) if reasons else "technical_ok"
    except Exception as exc:
        return None, "unavailable", f"quality_error:{exc}"
    finally:
        if tmp is not None:
            try: tmp.cleanup()
            except Exception: pass



def analyze_combined(path: Path, media_type: str, privacy_enabled: bool = True,
                     privacy_threshold: float = 0.42, privacy_samples: int = 10,
                     quality_enabled: bool = True, quality_review_below: float = 55,
                     ffmpeg_threads: int = 2, cancel_cb=None, progress_cb=None) -> dict:
    """Privacy + technical triage from one shared representative sample set.

    For video, do *fast random seeks* instead of decoding the whole timeline through an
    fps filter. This is important for long 4K clips: ten representative frames should
    cost roughly ten seeks, not an hour-long decode. Privacy and quality then reuse the
    same JPEGs. cancel_cb is checked between samples and detector calls.
    """
    result = {
        "privacy_score": None,
        "privacy_status": "safe" if not privacy_enabled else "review",
        "privacy_reason": "privacy_disabled" if not privacy_enabled else "privacy_not_run",
        "quality_score": None,
        "quality_status": "unreviewed" if not quality_enabled else "unavailable",
        "quality_reason": "quality_disabled" if not quality_enabled else "quality_not_run",
    }

    detector = _detector_instance() if privacy_enabled else None
    if privacy_enabled and detector is None:
        result["privacy_status"] = "review"
        result["privacy_reason"] = "privacy_detector_unavailable"

    tmp = None
    if media_type == "image":
        frames = [path]
    else:
        exe = _ffmpeg_exe()
        if not exe:
            if privacy_enabled:
                result["privacy_status"] = "review"; result["privacy_reason"] = "ffmpeg_unavailable"
            if quality_enabled:
                result["quality_status"] = "unavailable"; result["quality_reason"] = "ffmpeg_unavailable"
            return result

        count = max(privacy_samples if privacy_enabled else 0, 5 if quality_enabled else 0, 3)
        count = max(3, min(16, int(count)))
        duration = probe_duration(path)
        if duration and duration > 0:
            # Midpoints avoid intros/outros while still covering the complete clip.
            times = [max(0.0, min(duration - 0.05, duration * (i + 0.5) / count)) for i in range(count)]
        else:
            fallback = [0.0, 2.0, 5.0, 10.0, 20.0, 35.0, 55.0, 80.0, 120.0, 180.0, 300.0, 480.0, 720.0, 1000.0, 1400.0, 1800.0]
            times = fallback[:count]

        tmp = tempfile.TemporaryDirectory(prefix="archivist_analysis_")
        frames = []
        try:
            for idx, ts in enumerate(times, 1):
                if cancel_cb and cancel_cb():
                    raise RuntimeError("cancelled")
                out = Path(tmp.name) / f"a_{idx:03d}.jpg"
                # -ss before -i performs input/keyframe seeking and avoids decoding the
                # full clip merely to obtain sparse representative frames.
                r = _run([
                    exe, "-hide_banner", "-loglevel", "error", "-threads", str(max(1, int(ffmpeg_threads))),
                    "-ss", f"{ts:.3f}", "-i", str(path), "-frames:v", "1",
                    "-vf", "scale='min(720,iw)':-2", "-q:v", "5", "-y", str(out),
                ], capture_output=True, timeout=75)
                if r.returncode == 0 and out.exists() and out.stat().st_size:
                    frames.append(out)
                if progress_cb:
                    try: progress_cb(idx, len(times), "sampling")
                    except Exception: pass
            if not frames:
                if privacy_enabled:
                    result["privacy_status"] = "review"; result["privacy_reason"] = "video_decode_failed"
                if quality_enabled:
                    result["quality_status"] = "unavailable"; result["quality_reason"] = "video_decode_failed"
                return result
        except subprocess.TimeoutExpired:
            if privacy_enabled:
                result["privacy_status"] = "review"; result["privacy_reason"] = "video_decode_timeout"
            if quality_enabled:
                result["quality_status"] = "unavailable"; result["quality_reason"] = "video_decode_timeout"
            return result
        except RuntimeError:
            raise
        except Exception as exc:
            if privacy_enabled:
                result["privacy_status"] = "review"; result["privacy_reason"] = f"video_decode_error:{exc}"
            if quality_enabled:
                result["quality_status"] = "unavailable"; result["quality_reason"] = f"video_decode_error:{exc}"
            return result

    try:
        if privacy_enabled and detector is not None:
            best = 0.0
            limit = min(len(frames), max(1, int(privacy_samples)))
            unreadable = 0
            for idx, frame in enumerate(frames[:limit], 1):
                if cancel_cb and cancel_cb():
                    raise RuntimeError("cancelled")
                det = _detect_path(detector, frame)
                if det is None:
                    unreadable += 1
                    continue
                sc, _ = _score(det)
                best = max(best, sc)
                if progress_cb:
                    try: progress_cb(idx, limit, "privacy")
                    except Exception: pass
            result["privacy_score"] = best
            if unreadable:
                # Fail closed: an image we could not examine is never declared safe.
                result["privacy_status"] = "review"; result["privacy_reason"] = f"privacy_unavailable:{unreadable}/{limit}"
            elif best >= float(privacy_threshold):
                result["privacy_status"] = "review"; result["privacy_reason"] = "privacy_candidate"
            else:
                result["privacy_status"] = "safe"; result["privacy_reason"] = "privacy_clear"

        if quality_enabled:
            if cancel_cb and cancel_cb():
                raise RuntimeError("cancelled")
            vals = [_frame_metrics(f) for f in frames[:5]]
            vals = [(b, d) for b, d in vals if b is not None and d is not None]
            if not vals:
                result["quality_status"] = "unavailable"; result["quality_reason"] = "quality_metrics_failed"
            else:
                brightness = sum(v[0] for v in vals) / len(vals)
                detail = sum(v[1] for v in vals) / len(vals)
                score = 100.0; reasons = []
                if brightness < 28: score -= 38; reasons.append("very_dark")
                elif brightness < 48: score -= 18; reasons.append("dark")
                elif brightness > 235: score -= 35; reasons.append("very_bright")
                elif brightness > 220: score -= 15; reasons.append("bright")
                if detail < 10: score -= 35; reasons.append("very_low_detail")
                elif detail < 18: score -= 15; reasons.append("low_detail")
                score = round(max(0.0, min(100.0, score)), 1)
                result["quality_score"] = score
                result["quality_status"] = "review" if score < float(quality_review_below) else "ok"
                result["quality_reason"] = ",".join(reasons) if reasons else "technical_ok"
            if progress_cb:
                try: progress_cb(1, 1, "quality")
                except Exception: pass
        return result
    finally:
        if media_type != "image" and tmp is not None:
            try: tmp.cleanup()
            except Exception: pass

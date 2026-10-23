from __future__ import annotations
from .platform_adapter import keep_awake, process_kwargs

import json, os, re, shutil, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path

from .config import HOME, load_config
from .db import db
from .media import _ffmpeg_exe, probe_duration

PRESETS = {
    "share_1080p": {"label": "Share 1080p", "crf": 24, "cap": 1920, "audio_k": 128, "suffix": "share_1080p"},
    "small_720p": {"label": "Small 720p", "crf": 27, "cap": 1280, "audio_k": 96, "suffix": "small_720p"},
    "hq_1080p": {"label": "High Quality 1080p", "crf": 20, "cap": 1920, "audio_k": 160, "suffix": "hq_1080p"},
    "keep_resolution": {"label": "Original Resolution", "crf": 23, "cap": None, "audio_k": 160, "suffix": "keep"},
}

_LOCK = threading.Lock()
_CURRENT_PROCESS = None
_CURRENT_PROCESS_JOB_ID = None
_EXITING = threading.Event()     # the app is quitting: a stopped FFmpeg is not a failed video (the job resumes next start)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _flags():
    kw = process_kwargs()
    return int(kw.get("creationflags", 0) or 0), kw.get("startupinfo")

def _local_path(row):
    for key in ("staging_path", "archive_path"):
        raw = row[key] if key in row.keys() else None
        if raw and Path(raw).exists():
            return Path(raw)
    raw = row["path"] if "path" in row.keys() else None
    if raw and Path(raw).exists():
        return Path(raw)
    return None


def output_folder() -> Path:
    """Where converted videos go: the folder chosen on the Convert page, else Converted in the data folder."""
    raw = str((load_config().get("convert") or {}).get("output_dir") or "").strip()
    return Path(raw) if raw else HOME / "Converted"


# the names this converter gives (a sweep in a folder of the person's own touches only these)
_OUR_NAME = re.compile(r"_(?:share_1080p|small_720p|hq_1080p|keep|target_\d+mb)(?:_\d+)?(?:\.part)?\.mp4$", re.I)


def _sweep_ours(folder: Path) -> None:
    """A chosen output folder after a restart: only this converter's half-written files (.part.mp4) and the empty
    names it had reserved go; nothing else in the folder is touched."""
    try:
        for f in folder.glob("*.mp4"):
            try:
                if _OUR_NAME.search(f.name) and (f.name.lower().endswith(".part.mp4") or f.stat().st_size == 0):
                    f.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _unique_output(source: Path, preset: str, target_mb: int | None, output_dir: Path | None = None, tag: str = "") -> Path:
    """A new output name, reserved at once (an empty file): two conversions never pick the same name. A very long
    source name is shortened (the whole name must stay within 255 characters)."""
    cfg = PRESETS[preset]
    # Never write next to the source: it may be an SD card, a phone folder or another app's archive.
    folder = output_dir or (HOME / "Converted")
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        folder = HOME / "Converted"
        folder.mkdir(parents=True, exist_ok=True)
    suffix = f"target_{int(target_mb)}mb" if target_mb else cfg["suffix"]
    stem = source.stem[:150] + (f"_{tag}" if tag else "")
    n = 1
    while True:
        p = folder / (f"{stem}_{suffix}.mp4" if n == 1 else f"{stem}_{suffix}_{n}.mp4")
        try:
            with open(p, "xb"):
                return p
        except FileExistsError:
            n += 1
            if n > 100000:
                raise RuntimeError("No free output name in " + str(folder))


def _sweep_converted(folder: Path | None = None) -> None:
    """At start (nothing converts yet): names reserved by a conversion the app was closed during (empty files) and
    half-written .part files go; finished conversions are never touched."""
    folder = folder or (HOME / "Converted")
    try:
        for f in folder.glob("*.mp4"):
            try:
                if f.name.endswith(".part.mp4") or f.stat().st_size == 0:
                    f.unlink()
            except OSError:
                pass
        for pat in ("ffmpeg2pass-*", "join-*.txt"):     # two-pass logs / part lists of a conversion that did not finish
            for f in (HOME / "data").glob(pat):
                try:
                    f.unlink()
                except OSError:
                    pass
    except OSError:
        pass


HDR_TO_SDR = {   # same conversion as the Auto Edit engine (engine_p11/p11_folder_to_reel_r3.py)
    "HLG": "zscale=tin=arib-std-b67:t=bt709:pin=bt2020:p=bt709:min=bt2020nc:m=bt709:r=tv,format=yuv420p",
    "PQ": "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p",
}


def _is_interlaced(ffmpeg, source) -> bool:
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, **process_kwargs())
        line = next((l for l in (cp.stderr or "").splitlines() if "Video:" in l), "")
        return any(x in line for x in ("top first", "bottom first", "top coded first", "bottom coded first"))
    except Exception:
        return False


def _hdr_kind(ffmpeg, source) -> str | None:
    """'HLG' / 'PQ' for HDR phone video, else None. A normal H.264 file must not keep the HDR numbers as-is (grey, dark)."""
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, **process_kwargs())
        line = next((l for l in (cp.stderr or "").splitlines() if "Video:" in l), "")
        kind = "HLG" if "arib-std-b67" in line else ("PQ" if "smpte2084" in line else None)
        if kind:
            filt = subprocess.run([str(ffmpeg), "-hide_banner", "-filters"], capture_output=True, text=True, timeout=60, **process_kwargs())
            if " zscale " not in (filt.stdout or ""):
                return None
        return kind
    except Exception:
        return None


def _scale_args(preset: str, hdr: str | None = None, interlaced: bool = False):
    cap = PRESETS[preset]["cap"]
    parts = ["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if interlaced else []   # camcorder fields -> frames
    parts += [HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []
    if cap:
        # Cap the long edge. 1920 => 1920x1080 landscape or 1080x1920 portrait.
        parts.append(f"scale='min({int(cap)},iw)':'min({int(cap)},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2")
    if not parts:
        return []
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if hdr in HDR_TO_SDR else []
    return ["-vf", ",".join(parts), *tags]


def _cancelled(job_id: int | None):
    if not job_id:
        return False
    with db() as con:
        r = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (int(job_id),)).fetchone()
    return bool(r and r["cancel_requested"])


def _run_progress(cmd, duration_s: float, progress_cb=None, cancel_cb=None, phase_base=0.0, phase_span=1.0, job_id=None):
    with keep_awake():   # a long conversion must not be cut by Windows going to sleep
        return _run_progress_inner(cmd, duration_s, progress_cb, cancel_cb, phase_base, phase_span, job_id)


def _run_progress_inner(cmd, duration_s: float, progress_cb=None, cancel_cb=None, phase_base=0.0, phase_span=1.0, job_id=None):
    global _CURRENT_PROCESS, _CURRENT_PROCESS_JOB_ID
    if _EXITING.is_set():                  # the app is quitting: nothing new starts (the job resumes at the next start)
        raise RuntimeError("cancelled")
    flags, si = _flags()
    full = [str(x) for x in cmd[:-1]] + ["-progress", "pipe:1", "-nostats", str(cmd[-1])]
    errors = []
    p = subprocess.Popen(
        full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        creationflags=flags, startupinfo=si, close_fds=True
    )
    try:                                   # Windows: FFmpeg dies with the app (never a second writer after a restart)
        from .auto_edit import _attach_job_object
        _attach_job_object(p)
    except Exception:
        pass
    with _LOCK:
        _CURRENT_PROCESS = p
        _CURRENT_PROCESS_JOB_ID = int(job_id) if job_id else None
    if job_id:
        ts=_now()
        with db() as con:
            con.execute("UPDATE jobs SET worker_pid=?,heartbeat_at=?,progress_at=? WHERE id=?",(int(p.pid),ts,ts,int(job_id)));con.commit()
    try:
        if p.stdout:
            for raw in p.stdout:
                line = raw.strip()
                if cancel_cb and cancel_cb():
                    try:
                        p.terminate()
                        p.wait(15)                 # (the .part file is deleted next: Windows needs the writer gone)
                    except Exception:
                        try:
                            p.kill(); p.wait(15)
                        except Exception:
                            pass
                    raise RuntimeError("cancelled")
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k in ("out_time_us", "out_time_ms"):
                        try:
                            sec = float(v) / 1_000_000.0
                            frac = 0 if duration_s <= 0 else max(0.0, min(1.0, sec / duration_s))
                            if progress_cb:
                                progress_cb((phase_base + phase_span * frac) * 100.0)
                        except Exception:
                            pass
                    elif k == "progress" and v == "end" and progress_cb:
                        progress_cb((phase_base + phase_span) * 100.0)
                elif line:
                    errors.append(line[-500:])
                    if len(errors) > 12:
                        errors.pop(0)
        code = p.wait()
        if code != 0:
            raise RuntimeError(("FFmpeg failed: " + " | ".join(errors[-4:]))[:1200])
    finally:
        with _LOCK:
            if _CURRENT_PROCESS is p:
                _CURRENT_PROCESS = None
                _CURRENT_PROCESS_JOB_ID = None
        try:
            from .auto_edit import _JOB_HANDLES
            h = _JOB_HANDLES.pop(p.pid, None)
            if h is not None:
                import ctypes
                from ctypes import wintypes
                ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
        except Exception:
            pass
        if job_id:
            with db() as con:
                con.execute("UPDATE jobs SET worker_pid=NULL,heartbeat_at=? WHERE id=? AND worker_pid=?",(_now(),int(job_id),int(p.pid)));con.commit()


def convert_file(source, preset="share_1080p", target_mb=None, progress_cb=None, cancel_cb=None, output_dir=None, job_id=None,
                 cut=None, mute=False):
    """One video converted (cut = (start, end) in seconds: only that part)."""
    source = Path(source)
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(str(source))
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available")
    duration = float(probe_duration(source) or 0.0)
    if duration <= 0:
        raise RuntimeError("Could not read video duration")
    input_args, tag = ["-i", str(source)], ""
    if cut:
        start, end = float(cut[0]), min(float(cut[1]), duration)
        if not (0 <= start < end) or end - start < 0.5:
            raise ValueError("The cut must be at least half a second inside the video")
        # FFmpeg seeks to the start (the picture from exactly there: everything is re-encoded) and reads that long
        input_args, tag, duration = ["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(source)], "cut", end - start
    out, made_on = _encode(ffmpeg, input_args, source, duration, preset, target_mb, progress_cb, cancel_cb, output_dir, job_id, tag=tag,
                           mute=bool(mute))
    src_size = source.stat().st_size
    if cut:                                    # the part's share of the file (the saving of the part, not of the whole)
        src_size = int(src_size * min(1.0, duration / max(0.001, float(probe_duration(source) or duration))))
    out_size = out.stat().st_size
    return {
        "source": str(source),
        "output": str(out),
        "source_bytes": src_size,
        "output_bytes": out_size,
        "saved_percent": round(max(0.0, (1.0 - out_size / max(1, src_size)) * 100.0), 1),
        "preset": preset,
        "target_mb": int(target_mb) if target_mb else None,
        "made_on": made_on,
        **({"mute": True} if mute else {}),
        **({"cut": [round(float(cut[0]), 3), round(min(float(cut[1]), float(probe_duration(source) or cut[1])), 3)]} if cut else {}),
    }


# Parts of one recording. A camera splits a long recording into files of about 4 GB (GoPro: GX010044.MP4,
# GX020044.MP4 ... - chapter 01, 02 of recording 0044; older GoPros: GOPR0044.MP4 then GP010044.MP4 ...). Joined
# in the order of the recording, everything else by name (numbers as numbers: clip 2 before clip 10).
_GOPRO_PART = re.compile(r"^G[XHP](\d{2})(\d{4})$", re.I)
_GOPRO_FIRST = re.compile(r"^GOPR(\d{4})$", re.I)


def _natural(text: str) -> tuple:
    return tuple((1, int(t), "") if t.isdigit() else (0, 0, t) for t in re.split(r"(\d+)", text.casefold()) if t)


def part_key(name: str) -> tuple:
    """Sort key of one file for joining: GoPro recordings by recording number and chapter, other files by name."""
    stem = Path(str(name)).stem
    m = _GOPRO_PART.match(stem)
    if m:
        return (0, m.group(2), int(m.group(1)), stem.casefold())
    m = _GOPRO_FIRST.match(stem)
    if m:
        return (0, m.group(1), 0, stem.casefold())
    return (1, _natural(stem), 0, stem.casefold())


def _folder_of(it) -> str:
    return os.path.normcase(str(Path(it[2]).parent)) if it[2] else ""


def join_groups(items) -> list:
    """The videos made by a join, each a list of job items in order: parts of GoPro recordings - one video per
    recording (a card with recordings 0044 and 0045 gives two videos; the same number in another folder - another
    card, another day - is another recording); recordings of one file each, or any other videos - one video of all."""
    keys = [part_key(it[1]) for it in items]
    if items and all(k[0] == 0 for k in keys):
        groups: dict = {}
        for it, k in sorted(zip(items, keys), key=lambda x: (_folder_of(x[0]), x[1])):
            groups.setdefault((_folder_of(it), k[1]), []).append(it)
        if any(len(g) > 1 for g in groups.values()):
            return list(groups.values())
    items = sorted(items, key=lambda it: part_key(it[1]))
    return [items] if items else []


def gopro_recording(names) -> str | None:
    """The recording number when the files are two or more parts of one GoPro recording, else None."""
    recs, parts = set(), set()
    for n in names:
        k = part_key(n)
        if k[0] != 0:
            return None
        recs.add(k[1]); parts.add(k[2])
    names = list(names)
    return recs.pop() if len(recs) == 1 and len(names) >= 2 and len(parts) == len(names) else None


_SIZE_RE = re.compile(r"(?<![\dx])(\d{2,5})x(\d{2,5})(?![\dx])")
_PIX_RE = re.compile(r"\b((?:yuvj?|nv|p0|gbr|rgb|bgr|gray|ya)[a-z0-9_]*)\b")
_ROT_RE = re.compile(r"rotation of (-?\d+(?:\.\d+)?) degrees")


def media_sig(ffmpeg, source) -> dict:
    """What has to be the same in every part for a join: the picture (codec, pixel format, size, rotation) and the
    sound (codec, rate, channels; or none). The frame rate is told too (a recording with a varying rate may differ a
    little from part to part; that joins fine). Read from FFmpeg's own description."""
    cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=60, **process_kwargs())
    text = (cp.stderr or "").split("Stream mapping:", 1)[0]
    lines = text.splitlines()
    v = next((l for l in lines if " Video: " in l and "attached pic" not in l), "")
    a = next((l for l in lines if " Audio: " in l), "")
    if not v:
        raise RuntimeError("No picture in " + Path(str(source)).name)
    vc = v.split(" Video: ", 1)[1]
    size = _SIZE_RE.search(vc)
    pix = _PIX_RE.search(vc.split(",", 1)[1] if "," in vc else "")
    fps = re.search(r"([\d.]+) (?:fps|tbr)", vc)
    rot = _ROT_RE.search(text)
    sar = re.search(r"SAR (\d+):(\d+)", vc)
    sig = {"video": vc.split()[0].strip(","), "pix": pix.group(1) if pix else "", "size": size.group(0) if size else "",
           "sar": f"{sar.group(1)}:{sar.group(2)}" if sar else "",
           "fps": round(float(fps.group(1)), 2) if fps else 0.0, "rotation": int(round(float(rot.group(1)))) % 360 if rot else 0}
    if a:
        ac = a.split(" Audio: ", 1)[1]
        hz = re.search(r"(\d+) Hz", ac)
        lay = ac.split(",")[2].strip() if len(ac.split(",")) > 2 else ""
        sig.update(audio=ac.split()[0].strip(","), hz=int(hz.group(1)) if hz else 0, channels=lay)
    else:
        sig.update(audio=None, hz=0, channels="")
    return sig


def join_check(ffmpeg, sources, beat=None) -> None:
    """Raises ValueError naming the first part that differs from the first one (they could not be joined as they are)."""
    sources = [Path(x) for x in sources]
    first = media_sig(ffmpeg, sources[0])
    for src in sources[1:]:
        if beat:
            beat()
        other = media_sig(ffmpeg, src)
        if {k: v for k, v in other.items() if k != "fps"} != {k: v for k, v in first.items() if k != "fps"}:
            raise ValueError("Only videos of the same kind (picture size and format, sound) can be joined into one - like "
                             "parts of one recording. Different: " + src.name)


def join_files(sources, preset="share_1080p", target_mb=None, progress_cb=None, cancel_cb=None, output_dir=None, job_id=None,
               beat=None, mute=False):
    """Several parts of one recording, in the given order, as ONE converted video (FFmpeg's concat demuxer: the parts
    follow each other with their own timing; the picture and sound are then made like any converted video)."""
    sources = [Path(x) for x in sources]
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    if len(sources) < 2:
        raise ValueError("Choose at least two videos to join into one")
    for src in sources:
        if not src.is_file():
            raise FileNotFoundError(str(src))
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available")
    join_check(ffmpeg, sources, beat)
    duration = 0.0
    for src in sources:
        if beat:
            beat()
        d = float(probe_duration(src) or 0.0)
        if d <= 0:
            raise RuntimeError("Could not read video duration")
        duration += d
    listfile = (HOME / "data" / f"join-{os.getpid()}-{threading.get_ident()}.txt").resolve()
    listfile.parent.mkdir(parents=True, exist_ok=True)
    # one line per part; inside '...' nothing is special except the quote itself
    listfile.write_text("".join("file '" + str(src.resolve()).replace("'", "'\\''") + "'\n" for src in sources), "utf-8")
    try:
        out, made_on = _encode(ffmpeg, ["-f", "concat", "-safe", "0", "-i", str(listfile)], sources[0], duration, preset, target_mb,
                               progress_cb, cancel_cb, output_dir, job_id, tag="joined", mute=bool(mute))
    finally:
        try:
            listfile.unlink()
        except OSError:
            pass
    src_size = sum(src.stat().st_size for src in sources)
    out_size = out.stat().st_size
    return {
        "source": str(sources[0]),
        "sources": [str(src) for src in sources],
        "joined": len(sources),
        **({"mute": True} if mute else {}),
        "output": str(out),
        "source_bytes": src_size,
        "output_bytes": out_size,
        "saved_percent": round(max(0.0, (1.0 - out_size / max(1, src_size)) * 100.0), 1),
        "preset": preset,
        "target_mb": int(target_mb) if target_mb else None,
        "made_on": made_on,
    }


# An NVIDIA card makes a smaller copy of a big video much faster: it decodes the 4K picture, scales it down and
# encodes it; only the small picture passes through the processor (for the exact TV levels of the picture, as the
# processor path makes them). Used only for what it does surely: H.264 / HEVC, 8-bit 4:2:0, square pixels, upright,
# not HDR, not interlaced, made smaller (a 1080p / 720p preset), no size target. Tried once whether this PC's FFmpeg
# can encode on the card; any error, or a result of the wrong length: the same conversion on the processor.
# Off with the setting convert.gpu = false.
_GPU: list = []
_GPU_CQ_STEP = 3           # NVIDIA's constant quality N gives about the size of x264's CRF N-3
_GPU_FAILS: list = [0]     # attempts on the card that failed in a row: after two, the processor only (until a restart)
_TIME_RE = re.compile(r"time=\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def _picture_seconds(ffmpeg, path) -> float:
    """How long the picture itself is (its packets read without decoding; the file's length can be the sound's)."""
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, **process_kwargs())
        m = _TIME_RE.findall(cp.stderr or "")
        return int(m[-1][0]) * 3600 + int(m[-1][1]) * 60 + float(m[-1][2]) if m else 0.0
    except Exception:
        return 0.0


def _watchdog_pending(job_id) -> bool:
    if not job_id:
        return False
    with db() as con:
        r = con.execute("SELECT watchdog_retry_requested FROM jobs WHERE id=?", (int(job_id),)).fetchone()
    return bool(r and int(r["watchdog_retry_requested"] or 0))


def gpu_ok() -> bool:
    if (load_config().get("convert") or {}).get("gpu") is False or _GPU_FAILS[0] >= 2:
        return False
    if not _GPU:
        ok = False
        try:
            cp = subprocess.run([str(_ffmpeg_exe()), "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                                 "color=c=gray:s=256x256:r=25:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                                capture_output=True, timeout=60, **process_kwargs())
            ok = cp.returncode == 0
        except Exception:
            ok = False
        _GPU.append(ok)
    return _GPU[0]


def gpu_plan(sig: dict, preset: str, hdr=None, interlaced=False) -> dict | None:
    """The card's way for this video and preset, or None (the processor makes it)."""
    cap = PRESETS[preset]["cap"]
    if not cap or hdr or interlaced or sig.get("rotation") or sig.get("sar") not in ("", "1:1"):
        return None
    if sig.get("video") not in ("h264", "hevc") or sig.get("pix") not in ("yuv420p", "yuvj420p", "nv12"):
        return None
    try:
        w, h = (int(x) for x in str(sig.get("size") or "").split("x"))
    except ValueError:
        return None
    if max(w, h) <= cap:
        return None                            # not made smaller: the processor path is as quick
    k = cap / max(w, h)
    W, H = (cap, int(h * k) // 2 * 2) if w >= h else (int(w * k) // 2 * 2, cap)
    return {"pre": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
            "vf": f"scale_cuda={W}:{H},hwdownload,format=nv12,scale=in_range=auto:out_range=tv,format=yuv420p",
            "codec": ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr",
                      "-cq", str(int(PRESETS[preset]["crf"]) + _GPU_CQ_STEP), "-b:v", "0", "-profile:v", "high"],
            "size": (W, H)}


def _encode(ffmpeg, input_args, source: Path, duration: float, preset, target_mb, progress_cb, cancel_cb, output_dir, job_id,
            tag: str = "", mute: bool = False) -> Path:
    """The picture and sound made with the preset (or to a size, two passes) into a new file in Converted; returns it
    and where the picture was made ("nvidia" / "cpu")."""
    hdr = _hdr_kind(ffmpeg, source)
    interlaced = _is_interlaced(ffmpeg, source)
    target_mb = int(target_mb) if target_mb else None
    tag = "_".join(x for x in (tag, "nosound" if mute else "") if x)
    out = _unique_output(source, preset, target_mb, Path(output_dir) if output_dir else None, tag)   # reserved (empty)
    amap = [] if mute else ["-map", "0:a?"]                # "Without sound": no sound in the copy at all
    aenc = (lambda k: ["-an"]) if mute else (lambda k: ["-c:a", "aac", "-b:a", f"{int(k)}k"])
    part = out.with_name(out.stem + ".part.mp4")       # its own name: the output name is this conversion's alone
    passlog = None
    made_on = "cpu"
    try:
        cfg = PRESETS[preset]
        common = [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", *input_args,
            "-map", "0:v:0", *amap, *_scale_args(preset, hdr, interlaced),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        ]

        if target_mb:
            audio_k = 0 if mute else int(cfg["audio_k"])
            total_bits = float(target_mb) * 1024 * 1024 * 8 * 0.94
            video_k = max(250, int(total_bits / duration / 1000.0 - audio_k))
            passlog = str((HOME / "data" / f"ffmpeg2pass-{os.getpid()}-{threading.get_ident()}").resolve())
            Path(passlog).parent.mkdir(parents=True, exist_ok=True)
            pass1 = [
                str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", *input_args,
                "-map", "0:v:0", *_scale_args(preset, hdr, interlaced),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "1", "-passlogfile", passlog, "-an", "-f", "null", os.devnull
            ]
            _run_progress(pass1, duration, progress_cb, cancel_cb, 0.0, 0.48, job_id=job_id)
            pass2 = common + [
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "2", "-passlogfile", passlog,
                *aenc(audio_k), "-movflags", "+faststart", str(part)
            ]
            _run_progress(pass2, duration, progress_cb, cancel_cb, 0.50, 0.50, job_id=job_id)
        else:
            plan = None
            try:
                plan = gpu_plan(media_sig(ffmpeg, source), preset, hdr, interlaced) if gpu_ok() else None
            except Exception:
                plan = None
            if plan:
                gcmd = [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-xerror", *plan["pre"], *input_args,
                        "-map", "0:v:0", *amap, "-vf", plan["vf"], *plan["codec"],
                        *aenc(cfg["audio_k"]), "-movflags", "+faststart", str(part)]
                try:
                    _run_progress(gcmd, duration, progress_cb, cancel_cb, job_id=job_id)
                    got = float(probe_duration(part) or 0.0)
                    pic = _picture_seconds(ffmpeg, part)
                    if abs(got - duration) > max(0.5, 0.01 * duration) or pic < got - max(0.5, 0.01 * got):
                        raise RuntimeError(f"length {got:.2f} s (picture {pic:.2f} s) instead of {duration:.2f} s")
                    made_on = "nvidia"
                    _GPU_FAILS[0] = 0
                except Exception as exc:
                    if str(exc).lower() == "cancelled" or (cancel_cb and cancel_cb()) or _EXITING.is_set() or _watchdog_pending(job_id):
                        raise                  # stopped, quitting, or the watchdog's restart: not the card's failure
                    _GPU_FAILS[0] += 1
                    try:
                        part.unlink(missing_ok=True)
                    except Exception:
                        pass
                    if progress_cb:
                        progress_cb(0.0)
            if made_on != "nvidia":
                cmd = common + [
                    "-crf", str(int(cfg["crf"])),
                    *aenc(cfg["audio_k"]),
                    "-movflags", "+faststart", str(part)
                ]
                _run_progress(cmd, duration, progress_cb, cancel_cb, job_id=job_id)

        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        part.replace(out)
        return out, made_on
    except BaseException:
        # never leave a half-written .part file behind (it would be re-discovered as media), nor the empty reserved name
        try:
            part.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            if out.is_file() and out.stat().st_size == 0:
                out.unlink()
        except Exception:
            pass
        raise
    finally:
        if passlog:                        # two-pass logs (with .temp files while a pass runs): also after Cancel
            for f in Path(passlog).parent.glob(Path(passlog).name + "*"):
                try:
                    f.unlink()
                except Exception:
                    pass


def _job_update(job_id, **fields):
    if not fields:
        return
    ts=_now()
    fields.setdefault("heartbeat_at",ts)
    fields.setdefault("progress_at",ts)
    cols = ",".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [int(job_id)]
    with db() as con:
        con.execute(f"UPDATE jobs SET {cols} WHERE id=?", vals)
        con.commit()


def _consume_watchdog_request(job_id):
    with db() as con:
        r=con.execute("SELECT watchdog_retry_requested FROM jobs WHERE id=?",(int(job_id),)).fetchone()
        code=int(r["watchdog_retry_requested"] or 0) if r else 0
        if code: con.execute("UPDATE jobs SET watchdog_retry_requested=0 WHERE id=?",(int(job_id),));con.commit()
    return code


def terminate_current_process(job_id):
    with _LOCK:
        p=_CURRENT_PROCESS
        owner=_CURRENT_PROCESS_JOB_ID
    if not p or owner!=int(job_id):
        return False
    try:
        if os.name=="nt":
            flags,si=_flags()
            subprocess.run(["taskkill","/PID",str(int(p.pid)),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           timeout=10,creationflags=flags,startupinfo=si,close_fds=True)
        else:
            p.terminate()
        return True
    except Exception:
        try:p.kill();return True
        except Exception:return False


def _job_items(inventory_ids, paths):
    """The job's videos in its order: (key, file name, local file or None, size). Library videos by their id (their
    local file found now), files chosen on this PC by their path."""
    items = []
    ids = [int(i) for i in (inventory_ids or [])]
    if ids:
        with db() as con:
            rows = con.execute(
                f"SELECT * FROM inventory WHERE id IN ({','.join('?' for _ in ids)}) AND excluded=0 AND media_type='video' AND COALESCE(analysis_status,'')<>'private' AND private_path IS NULL",
                ids,
            ).fetchall()
        by_id = {int(r["id"]): r for r in rows}
        for i in ids:
            r = by_id.get(i)
            if r is None:
                continue
            src = _local_path(r)
            items.append((i, r["filename"], src, int(r["size_bytes"] or (src.stat().st_size if src and src.exists() else 0))))
    for raw in paths or []:
        src = Path(str(raw))
        there = src.is_file()
        items.append(("p:" + str(src), src.name, src if there else None, src.stat().st_size if there else 0))
    return items


def _options(preset, target_mb, inventory_ids, paths, join, done, outputs, output_dir=None, cuts=None, mute=False) -> str:
    return json.dumps({"preset": preset, "target_mb": target_mb, "inventory_ids": list(inventory_ids or []),
                       "paths": [str(x) for x in (paths or [])], "join": bool(join),
                       **({"output_dir": str(output_dir)} if output_dir else {}),
                       **({"cuts": cuts} if cuts else {}), **({"mute": True} if mute else {}),
                       "finished_ids": sorted(k for k in done if isinstance(k, int)),
                       "finished_paths": sorted(k[2:] for k in done if isinstance(k, str)),
                       "outputs": outputs}, ensure_ascii=False)


def _convert_worker(job_id: int, inventory_ids: list[int], preset: str, target_mb: int | None, paths=None, join=False,
                    sweep_first=None):
    with db() as con:
        jr=con.execute("SELECT options_json FROM jobs WHERE id=?",(int(job_id),)).fetchone()
    try: prior=json.loads(jr["options_json"] or "{}") if jr else {}
    except Exception: prior={}
    outputs=list(prior.get("outputs") or [])
    done=set()
    for x in (prior.get("finished_ids") or []):
        try:done.add(int(x))
        except Exception:pass
    for x in (prior.get("finished_paths") or []):
        done.add("p:"+str(x))
    success=sum(1 for x in outputs if not x.get("error"))
    failed=sum(1 for x in outputs if x.get("error"))
    processed_bytes = 0
    output_dir=str(prior.get("output_dir") or "") or None
    if sweep_first:                        # resumed in a folder of the person's own: its leftovers first (in this thread:
        _sweep_ours(Path(sweep_first))     # a slow network folder never holds up the start; nothing is written meanwhile)
    cuts=prior.get("cuts") if isinstance(prior.get("cuts"),dict) else {}
    mute=prior.get("mute") is True
    opts=lambda: _options(preset,target_mb,inventory_ids,paths,join,done,outputs,output_dir,cuts,mute)
    try:
        ordered = _job_items(inventory_ids, paths)
        total_bytes = sum(size for _, _, _, size in ordered)
        _RUN_START[int(job_id)] = (time.time(), sum(size for key, _, _, size in ordered if key in done) if not join else
                                   sum(sum(it[3] for it in g) for g in join_groups(ordered) if all(it[0] in done for it in g)))
        if join:
            groups = join_groups(ordered)           # GoPro: one video per recording; other videos: one video of all
            n_groups = len(groups)
            _job_update(job_id, total=n_groups, bytes_total=total_bytes, bytes_done=0, stage="converting",
                        message=(f"Joining {len(ordered)} parts into one video…" if n_groups == 1
                                 else f"Joining the parts of {n_groups} recordings…"))
            for gi, grp in enumerate(groups, start=1):
                gsize = sum(it[3] for it in grp)
                if all(it[0] in done for it in grp):
                    processed_bytes += gsize
                    continue
                if _cancelled(job_id):
                    raise RuntimeError("cancelled")
                parts = [src for _, _, src, _ in grp]
                missing = [name for _, name, src, _ in grp if not src]
                if missing and n_groups == 1:
                    raise RuntimeError("A part is not on this computer now: " + missing[0])

                def prog_join(pct, gi=gi, n=len(grp), base=processed_bytes, gsize=gsize):
                    _job_update(job_id, bytes_done=base + int(gsize * max(0.0, min(100.0, pct)) / 100.0),
                                message=(f"Joining {n} parts · {pct:.0f}%" if n_groups == 1 else
                                         f"Recording {gi}/{n_groups} · {n} parts · {pct:.0f}%" if n > 1 else
                                         f"Recording {gi}/{n_groups} · {pct:.0f}%"))
                while True:
                    try:
                        if missing:
                            raise RuntimeError("A part is not on this computer now: " + missing[0])
                        if len(parts) == 1:              # a recording of one file: converted as it is
                            res = convert_file(parts[0], preset, target_mb, progress_cb=prog_join, cancel_cb=lambda: _cancelled(job_id),
                                               job_id=job_id, output_dir=output_dir, mute=mute)
                        else:
                            res = join_files(parts, preset, target_mb, progress_cb=prog_join, cancel_cb=lambda: _cancelled(job_id),
                                             job_id=job_id, output_dir=output_dir, beat=lambda: _job_update(job_id, stage="converting"),
                                             mute=mute)
                        outputs.append(res)
                        success += 1
                        break
                    except Exception as exc:
                        if str(exc).lower() == "cancelled" or _EXITING.is_set():
                            raise
                        request=_consume_watchdog_request(job_id)
                        if request==1:
                            _job_update(job_id,stage="watchdog_retry",message="Converter stalled; process restarted automatically",error=None)
                            continue
                        if request==2:
                            _job_update(job_id,stage="watchdog_app_restart",message="Converter stalled; restarting MediaEngine automatically…",error=None)
                            return
                        failed += 1
                        first = parts[0] if parts[0] else Path(grp[0][1])
                        outputs.append({"source": str(first), "sources": [str(x) for x in parts if x], "joined": len(grp), "error": str(exc)[:1000]})
                        break
                for it in grp:
                    done.add(it[0])
                processed_bytes += gsize
                _job_update(job_id, done=gi, success=success, failed=failed, bytes_done=processed_bytes, options_json=opts())
            ordered = []
        for r in ordered:
            if r[0] in done:
                processed_bytes += r[3]
        if not join:
            _job_update(job_id, total=len(ordered) or 1, bytes_total=total_bytes, bytes_done=processed_bytes if ordered else total_bytes,
                        stage="converting", **({"message": f"Preparing {len(ordered)} video(s)…"} if ordered else {}))
        for index, (key, filename, src, size) in enumerate(ordered, start=1):
            if key in done:
                continue
            if _cancelled(job_id):
                raise RuntimeError("cancelled")
            if not src:
                failed += 1
                _job_update(job_id, failed=failed, done=index, message=f"Skipped missing local file: {filename}")
                continue
            _job_update(job_id, current_inventory_id=key if isinstance(key, int) else None, current_filename=filename,
                        message=f"Converting {index}/{len(ordered)} · {filename}")
            def prog(pct):
                approx = processed_bytes + int(size * max(0.0, min(100.0, pct)) / 100.0)
                _job_update(job_id, bytes_done=approx,
                            message=f"Converting {index}/{len(ordered)} · {pct:.0f}% · {filename}")
            while True:
                try:
                    result = convert_file(src, preset, target_mb, progress_cb=prog, cancel_cb=lambda: _cancelled(job_id), job_id=job_id,
                                          output_dir=output_dir, cut=cuts.get(str(key)) if isinstance(key, int) else None, mute=mute)
                    outputs.append(result); success += 1
                    break
                except Exception as exc:
                    if str(exc).lower() == "cancelled" or _EXITING.is_set():
                        raise
                    request=_consume_watchdog_request(job_id)
                    if request==1:
                        _job_update(job_id,stage="watchdog_retry",message=f"Converter stalled; process restarted automatically · {index}/{len(ordered)}",error=None)
                        continue
                    if request==2:
                        _job_update(job_id,stage="watchdog_app_restart",message="Converter stalled; restarting MediaEngine automatically…",error=None)
                        return
                    failed += 1
                    outputs.append({"source": str(src), "error": str(exc)[:1000]})
                    break
            done.add(key)
            processed_bytes += size
            _job_update(job_id, done=len(done), success=success, failed=failed, bytes_done=processed_bytes, options_json=opts())
        status = "finished" if failed == 0 else ("finished" if success else "failed")
        n_items = len(join_groups(_job_items(inventory_ids, paths))) if join else len(done)
        _job_update(job_id, status=status, stage="done", finished_at=_now(), current_inventory_id=None,
                    current_filename=None, done=n_items, success=success, failed=failed, bytes_done=total_bytes,
                    message=(f"Joined {len(done)} parts into one video" if join and success and not failed and n_items == 1 else
                             f"Joined into {success} videos ({len(done)} parts)" if join and success and not failed else
                             f"Converted {success}; failed {failed}"),
                    options_json=opts())
        _notify_end(job_id, success, failed, len(done) if join and n_items == 1 else 0)
    except Exception as exc:
        if _EXITING.is_set():
            return                         # the app quits: the job stays 'running' and resumes at the next start
        cancelled = str(exc).lower() == "cancelled"
        _job_update(job_id, status="cancelled" if cancelled else "failed", stage="cancelled" if cancelled else "error",
                    finished_at=_now(), error=None if cancelled else str(exc)[:1500],
                    message="Conversion cancelled" if cancelled else f"Conversion failed: {str(exc)[:300]}",
                    options_json=opts())
        if not cancelled:
            _notify_end(job_id, success, max(1, failed), 0)
    finally:
        _RUN_START.pop(int(job_id), None)


def _notify_end(job_id, ok, failed, joined) -> None:
    """A Windows notification when a conversion that took more than a minute ends (Settings: notifications)."""
    try:
        from . import notify
        from .config import APP_PORT
        from .i18n import ui_language
        with db() as con:
            r = con.execute("SELECT started_at FROM jobs WHERE id=?", (int(job_id),)).fetchone()
        t0 = _RUN_START.get(int(job_id), (time.time(), 0))[0]
        try:
            t0 = min(t0, datetime.fromisoformat(str(r["started_at"])).timestamp()) if r and r["started_at"] else t0
        except Exception:
            pass
        notify.convert_finished(ok, failed, joined, time.time() - t0, f"http://127.0.0.1:{APP_PORT}/convert", ui_language() == "ru")
    except Exception:
        pass


def recover_convert_jobs():
    """Resume durable converter jobs after an app restart.

    New converter jobs persist inventory_ids. Legacy interrupted jobs that lack
    those ids are closed with an explicit message instead of being routed to the
    generic worker as an unknown job kind.
    """
    with db() as con:
        # Repair the exact legacy failure exposed by job #5.
        con.execute(
            "UPDATE jobs SET stage='interrupted',message='Conversion interrupted by app restart. Start it again.',"
            "error='interrupted_by_restart',finished_at=COALESCE(finished_at,?) "
            "WHERE kind='convert' AND status='failed' AND (message='Unknown job kind' OR error LIKE 'Unknown job kind convert%')",
            (_now(),),
        )
        rows=con.execute("SELECT * FROM jobs WHERE kind='convert' AND status IN ('running','queued') AND cancel_requested=0 ORDER BY id").fetchall()
        con.commit()
    _sweep_converted()
    resumed=0; interrupted=0
    for row in rows:
        d={k:row[k] for k in row.keys()}
        try:
            opts=json.loads(d.get("options_json") or "{}")
        except Exception:
            opts={}
        ids=[]
        for x in (opts.get("inventory_ids") or []):
            try:
                i=int(x)
            except Exception:
                continue
            if i>0 and i not in ids: ids.append(i)
        paths=[str(x) for x in (opts.get("paths") or []) if str(x).strip()]
        preset=str(opts.get("preset") or "")
        target_mb=opts.get("target_mb")
        own = str(opts["output_dir"]) if opts.get("output_dir") and Path(str(opts["output_dir"])) != HOME / "Converted" else None
        if (ids or paths) and preset in PRESETS:
            _job_update(int(d["id"]),status="running",stage="resuming",message="Resuming conversion after restart…",
                        started_at=d.get("started_at") or _now(),finished_at=None,error=None,worker_pid=None,watchdog_retry_requested=0)
            threading.Thread(target=_convert_worker,args=(int(d["id"]),ids,preset,target_mb,paths,bool(opts.get("join")),own),daemon=True,
                             name=f"ArchivistConvert{int(d['id'])}").start()
            resumed+=1
        else:
            _job_update(int(d["id"]),status="failed",stage="interrupted",
                        message="Conversion interrupted by app restart. Start it again.",
                        error="interrupted_by_restart",finished_at=_now())
            interrupted+=1
    return {"resumed":resumed,"interrupted":interrupted}



def _ffprobe_meta(source: Path):
    ffmpeg=_ffmpeg_exe()
    candidates=[]
    if ffmpeg:
        fp=Path(ffmpeg)
        candidates.append(fp.with_name('ffprobe.exe' if fp.suffix.lower()=='.exe' else 'ffprobe'))
    found=shutil.which('ffprobe')
    if found: candidates.append(Path(found))
    ffprobe=next((p for p in candidates if p and Path(p).exists()),None)
    duration_ms=0; width=0; height=0
    if ffprobe:
        flags,si=_flags()
        try:
            rr=subprocess.run([str(ffprobe),'-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(source)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,
                creationflags=flags,startupinfo=si,close_fds=True)
            if rr.returncode==0 and rr.stdout:
                data=json.loads(rr.stdout); streams=data.get('streams') or []
                if streams:
                    width=int(streams[0].get('width') or 0); height=int(streams[0].get('height') or 0)
                sec=float((data.get('format') or {}).get('duration') or 0)
                if sec>0: duration_ms=max(1,int(round(sec*1000)))
        except Exception: pass
    if (width<=0 or height<=0) and ffmpeg:
        import re
        flags,si=_flags()
        try:
            rr=subprocess.run([str(ffmpeg),'-hide_banner','-i',str(source)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=flags,startupinfo=si,close_fds=True)
            txt=(rr.stderr or '')+'\n'+(rr.stdout or '')
            m=re.search(r'Video:[^\n]*?[, ](\d{2,5})x(\d{2,5})(?:[ ,\[])',txt,re.I)
            if m:
                width=int(m.group(1));height=int(m.group(2))
        except Exception: pass
    if duration_ms<=0:
        try:
            sec=float(probe_duration(source) or 0)
            if sec>0: duration_ms=max(1,int(round(sec*1000)))
        except Exception: pass
    return {'duration_ms':duration_ms,'width':width,'height':height}

def probe_local_media_meta(inventory_ids):
    ids=[]; seen=set()
    for x in inventory_ids:
        try:i=int(x)
        except Exception:continue
        if i>0 and i not in seen: ids.append(i);seen.add(i)
    if not ids:return {}
    with db() as con:
        rows=con.execute(f"SELECT id,duration_ms,width,height,path,staging_path,archive_path,source_kind FROM inventory WHERE id IN ({','.join('?' for _ in ids)}) AND excluded=0 AND media_type='video'",ids).fetchall()
    out={}; updates=[]
    for row in rows:
        iid=int(row['id']); ms=int(row['duration_ms'] or 0); w=int(row['width'] or 0); h=int(row['height'] or 0)
        if ms<=0 or w<=0 or h<=0:
            local=_local_path(row)
            if local and local.exists():
                meta=_ffprobe_meta(local)
                if ms<=0: ms=int(meta.get('duration_ms') or 0)
                if w<=0: w=int(meta.get('width') or 0)
                if h<=0: h=int(meta.get('height') or 0)
                updates.append((ms,w,h,iid))
        out[str(iid)]={'duration_ms':ms,'width':w,'height':h}
    if updates:
        with db() as con:
            con.executemany("UPDATE inventory SET duration_ms=?,width=?,height=? WHERE id=?",updates); con.commit()
    return out

def probe_local_durations(inventory_ids):
    return {k:int(v.get('duration_ms') or 0) for k,v in probe_local_media_meta(inventory_ids).items()}

MAX_FILES = 50
_RUN_START: dict = {}          # job id -> (when this run started, bytes done then): the time left is measured from it


def eta_seconds(job: dict) -> int | None:
    """About how long the running job still needs (from its pace in this run), or None while that is not known yet."""
    try:
        if str(job.get("status")) != "running":
            return None
        t0, b0 = _RUN_START.get(int(job["id"])) or (None, 0)
        total, done = int(job.get("bytes_total") or 0), int(job.get("bytes_done") or 0)
        if t0 is None or total <= 0:
            return None
        el, moved = time.time() - t0, done - b0
        if el < 15 or moved <= 0 or moved < 0.02 * max(1, total - b0):
            return None
        return int(el * max(0, total - done) / moved)
    except Exception:
        return None


def _clean_cuts(cuts, ids) -> dict:
    """{"<library id>": [start, end]} for the selected videos only; numbers, start before end, at least half a second,
    not after the video's end (an end a moment after it is the end)."""
    out = {}
    if not cuts:
        return out
    if not isinstance(cuts, dict):
        raise ValueError("Unknown cut")
    durations = {}
    if ids:
        with db() as con:
            for r in con.execute(f"SELECT id,duration_ms,filename FROM inventory WHERE id IN ({','.join('?' for _ in ids)})", ids):
                durations[int(r["id"])] = (int(r["duration_ms"] or 0) / 1000.0, r["filename"])
    for k, v in cuts.items():
        try:
            i, start, end = int(k), float(v[0]), float(v[1])
        except (TypeError, ValueError, IndexError, KeyError):
            raise ValueError("Unknown cut")
        if i not in ids:
            continue
        if not (start == start and end == end) or start < 0 or end > 360000:
            raise ValueError("Unknown cut")
        dur, name = durations.get(i, (0.0, str(i)))
        if dur > 0:
            if start >= dur - 0.5:
                raise ValueError("The cut starts after the end of the video: " + name)
            end = min(end, dur)
        if end - start < 0.5:
            raise ValueError("The cut must be at least half a second: " + name)
        out[str(i)] = [round(start, 3), round(end, 3)]
    return out


def start_convert_job(inventory_ids=None, preset="share_1080p", target_mb=None, paths=None, join=False, cuts=None, mute=False):
    ids = []
    seen = set()
    for x in inventory_ids or []:
        try:
            i = int(x)
        except Exception:
            continue
        if i > 0 and i not in seen:
            ids.append(i); seen.add(i)
    files, seen_f = [], set()
    for x in paths or []:
        f = Path(str(x))
        k = os.path.normcase(str(f))
        if k in seen_f:
            continue
        if not f.is_file():
            raise ValueError("This video is not there: " + f.name)
        files.append(f); seen_f.add(k)
    if not ids and not files:
        raise ValueError("Select at least one video")
    if len(ids) + len(files) > MAX_FILES:
        raise ValueError(f"Convert up to {MAX_FILES} videos at once")
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    target_mb = int(target_mb) if target_mb else None
    if target_mb is not None and not (50 <= target_mb <= 100000):
        raise ValueError("Target size must be between 50 MB and 100000 MB")
    join = bool(join)
    cuts = _clean_cuts(cuts, ids)
    if cuts and join:
        raise ValueError("A cut works when the videos are converted one by one (not joined into one).")
    n_groups = 0
    if join:
        if len(ids) + len(files) < 2:
            raise ValueError("Choose at least two videos to join into one")
        items = _job_items(ids, [str(f) for f in files])
        if len(items) < len(ids) + len(files):
            raise ValueError("None of the selected videos can be converted (private, rejected or removed)")
        missing = [name for _, name, src, _ in items if not src]
        if missing:
            raise ValueError("This video is not there: " + missing[0])
        groups = join_groups(items)                            # the order of each recording (GoPro), else by name
        ffmpeg = _ffmpeg_exe()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is not available")
        for g in groups:
            if len(g) > 1:
                join_check(ffmpeg, [src for _, _, src, _ in g])   # said now, not after an hour
        items = [it for g in groups for it in g]
        n_groups = len(groups)
        ids = [k for k, _, _, _ in items if isinstance(k, int)]
        files = [Path(k[2:]) for k, _, _, _ in items if isinstance(k, str)]
    with db() as con:
        con.execute("BEGIN IMMEDIATE")     # the "nothing runs" check and the new job as one step (two clicks: one job)
        if ids:
            ok_ids = {int(r["id"]) for r in con.execute(
                f"SELECT id FROM inventory WHERE id IN ({','.join('?' for _ in ids)}) AND excluded=0 AND media_type='video' "
                "AND COALESCE(analysis_status,'')<>'private' AND private_path IS NULL AND rejected_path IS NULL", ids).fetchall()}
            if join and len(ok_ids) < len(ids):
                raise ValueError("None of the selected videos can be converted (private, rejected or removed)")
            ids = [i for i in ids if i in ok_ids]
        if not ids and not files:
            raise ValueError("None of the selected videos can be converted (private, rejected or removed)")
        busy = con.execute("SELECT id,kind FROM jobs WHERE status IN ('running','queued') ORDER BY id LIMIT 1").fetchone()
        if busy:
            raise RuntimeError(f"Job #{busy['id']} ({busy['kind']}) is already running")
        n = len(ids) + len(files)
        cur = con.execute(
            "INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("convert", "running", _now(), _now(), "starting", "Starting converter…", n_groups if join else n, 0, 0, 0, 0, 0,
             _options(preset, target_mb, ids, [str(f) for f in files], join, set(), [], output_folder(), cuts, bool(mute)))
        )
        job_id = int(cur.lastrowid)
        con.commit()
    threading.Thread(target=_convert_worker, args=(job_id, ids, preset, target_mb, [str(f) for f in files], join), daemon=True,
                     name=f"ArchivistConvert{job_id}").start()
    return job_id


def shutdown() -> None:
    """The app quits: the running FFmpeg is stopped (no orphan writing on); the job resumes at the next start."""
    _EXITING.set()
    with _LOCK:
        p = _CURRENT_PROCESS
    if p is not None:
        try:
            p.kill(); p.wait(10)
        except Exception:
            pass


def convert_job_snapshot(job_id=None):
    with db() as con:
        if job_id:
            r = con.execute("SELECT * FROM jobs WHERE id=? AND kind='convert'", (int(job_id),)).fetchone()
        else:
            r = con.execute("SELECT * FROM jobs WHERE kind='convert' ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    d = {k: r[k] for k in r.keys()}
    try:
        d["options"] = json.loads(d.get("options_json") or "{}")
    except Exception:
        d["options"] = {}
    total_bytes = int(d.get("bytes_total") or 0)
    done_bytes = int(d.get("bytes_done") or 0)
    d["percent"] = round(done_bytes * 100.0 / total_bytes, 1) if total_bytes else (100.0 if d.get("status") == "finished" else 0.0)
    d["eta_s"] = eta_seconds(d)
    return d

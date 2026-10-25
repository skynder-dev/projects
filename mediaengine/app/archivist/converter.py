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


def save_frame(source, t: float, output_dir=None, clock=False) -> Path:
    """One picture of a video at t seconds - the picture shown at that moment (the last one at or before t) - at the
    video's full size, as a JPEG next to the converted videos ('<name>_frame_1m05s.jpg'; never over another file).
    Upright as the video is shown, square pixels, camcorder fields made whole, HDR made normal, the colors of an HD
    video kept (its YUV goes through RGB into the JPEG's own). clock: the date and time of that moment on it."""
    source = Path(os.path.abspath(str(source)))
    if not source.is_file():
        raise FileNotFoundError(str(source))
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available")
    duration = float(probe_duration(source) or 0.0)
    t = float(t)
    if not (t == t) or t < 0 or (duration > 0 and t > duration + 0.05):
        raise ValueError("That moment is not in the video")
    folder = Path(output_dir) if output_dir else output_folder()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = HOME / "Converted"                     # the chosen folder is not there now (a disk not connected)
        folder.mkdir(parents=True, exist_ok=True)
    stem = f"{source.stem[:150]}_frame_{int(t) // 60}m{int(t) % 60:02d}s"
    for n in range(1, 1000):
        out = folder / (f"{stem}.jpg" if n == 1 else f"{stem}_{n}.jpg")
        try:
            with open(out, "xb"):
                break
        except FileExistsError:
            continue
    else:
        raise RuntimeError("No free name in " + str(folder))
    out = Path(os.path.abspath(str(out)))
    # from a little before t to t: every picture overwrites the file, so the last one at or before t stays (the one
    # the player shows; also at the very end, where the sound may run a moment longer than the picture)
    start = max(0.0, t - 1.1)
    cwd = None
    try:
        if clock:                          # the clock of the moment (its subtitles and font in a folder of their own)
            from datetime import timedelta
            when, _how = recording_start(ffmpeg, source, duration)
            cwd = (HOME / "data" / f"clock-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}").resolve()
            cwd.mkdir(parents=True, exist_ok=True)
            (cwd / "clock.ass").write_text(clock_ass([(0.0, t - start + 1.0, when + timedelta(seconds=start) if when else None)], 1,
                                                     _out_size(media_sig(ffmpeg, source), "keep_resolution", 0, "")), "utf-8")
            from .textfx import install_fonts
            install_fonts(cwd)
    except BaseException:
        try:
            out.unlink()
        except OSError:
            pass
        if cwd:
            shutil.rmtree(cwd, ignore_errors=True)
        raise
    hdr = _hdr_kind(ffmpeg, source)
    vf = (["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if _is_interlaced(ffmpeg, source) else []) \
        + ([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []) \
        + ["scale='trunc(iw*sar/2)*2':ih", "setsar=1"] + (["ass=clock.ass:fontsdir=fonts"] if cwd else []) \
        + ["format=gbrp", "format=yuvj420p"]
    try:
        cp = subprocess.run([str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(source),
                             "-t", f"{t - start + 0.001:.3f}", "-map", "0:v:0", "-vf", ",".join(vf), "-q:v", "2", "-update", "1",
                             str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                            cwd=str(cwd) if cwd else None, **process_kwargs())
        if cp.returncode != 0 or not out.is_file() or out.stat().st_size < 100:
            raise RuntimeError("There is no picture at that moment")
    except BaseException:
        try:
            out.unlink()
        except OSError:
            pass
        raise
    finally:
        if cwd:
            shutil.rmtree(cwd, ignore_errors=True)
    return out


FRAME_STEPS = (5, 10, 30, 60)


# containers with an index FFmpeg seeks exactly in (to the key picture before a moment); others (MPEG-TS / PS: camcorder
# MTS, DVD VOB / MOD; FLV ...) land on any packet - their pictures are taken by decoding the whole video
_SEEKABLE = re.compile(r"^Input #0, (mov,mp4,m4a,3gp,3g2,mj2|matroska,webm|avi|asf),", re.M)
_SEEK_PROCS: set = set()                   # the FFmpegs of a picture each (Quit and the watchdog stop them too)


def _seekable(ffmpeg, source) -> bool:
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, **process_kwargs())
        return bool(_SEEKABLE.search(cp.stderr or ""))
    except Exception:
        return False


def _pictures_by_seeking(ffmpeg, source, every, duration, interlaced, tail, folder, name_of, progress_cb, cancel_cb, cwd,
                         job_id=None) -> list:
    """Pictures at 0, N, 2N ... s, each read by a seek (the first picture at or after that moment), three at a time:
    [(file, moment)], or [] when this video is not read that way (then it is decoded whole): a container without an
    exact seek, interlaced video (its fields need the picture before), or any seek that failed."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    if interlaced or not _seekable(ffmpeg, source):
        return []
    times = [k * every for k in range(int(duration // every) + 1) if k * every < duration - 0.02]

    def stopped():
        return bool((cancel_cb and cancel_cb()) or _EXITING.is_set())

    def one(t):
        if stopped():
            return None
        out = folder / f"{name_of(t)}.jpg"
        # (showinfo: the picture's own time after the seek - a stretch without any picture, in a video with gaps, gets
        # none; the clock's subtitles count from the video's start: the picture's own time put back after the seek)
        vf = ["showinfo"] + ([f"setpts=PTS+{t}/TB"] if cwd else []) + tail
        try:
            pr = subprocess.Popen([str(ffmpeg), "-y", "-hide_banner", "-loglevel", "info", "-nostats",
                                   *(["-ss", f"{t:.3f}"] if t > 0 else []), "-i", str(source), "-map", "0:v:0", "-frames:v", "1",
                                   "-vf", ",".join(vf), "-q:v", "2", "-update", "1", str(out)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=str(cwd) if cwd else None, **process_kwargs())
        except OSError:
            return False
        try:                               # Windows: it dies with the app
            from .auto_edit import _attach_job_object
            _attach_job_object(pr)
        except Exception:
            pass
        with _LOCK:
            _SEEK_PROCS.add(pr)
        err, t_end = b"", time.time() + 120
        try:
            while True:
                try:
                    _, err = pr.communicate(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    if stopped() or time.time() > t_end:          # Stop, Quit, or a seek that hangs
                        pr.kill()
                        pr.communicate()
                        return None if stopped() else False
        finally:
            with _LOCK:
                _SEEK_PROCS.discard(pr)
        if pr.returncode != 0:
            return False
        if not (out.is_file() and out.stat().st_size > 100):
            return None                                   # (no picture there: the end)
        m = re.search(rb"pts_time:\s*(-?[\d.]+)", err or b"")
        dt = float(m.group(1)) if m else 0.0
        if dt >= every - 0.001:                           # the next picture is in a later stretch: none for this one
            try:
                out.unlink()
            except OSError:
                pass
            return None
        return out, float(t) + max(0.0, dt)

    got, failed, n = {}, 0, max(1, len(times))
    with _Keepalive(job_id), ThreadPoolExecutor(3) as ex:
        futs = {ex.submit(one, t): t for t in times}
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            if r is False:
                failed += 1
            elif r:
                got[futs[f]] = r
            if progress_cb:
                progress_cb(100.0 * (i + 1) / n)
    made = [got[t] for t in sorted(got)]
    if stopped():
        for fpath, _ in made:
            try:
                fpath.unlink()
            except OSError:
                pass
        raise RuntimeError("cancelled")
    if failed or (times and not made):                # not read this way: the whole video instead
        for fpath, _ in made:
            try:
                fpath.unlink()
            except OSError:
                pass
        return []
    return made


def _pictures_by_decoding(ffmpeg, source, every, duration, interlaced, tail, folder, name_of, progress_cb, cancel_cb, job_id, cwd) -> list:
    """The whole video decoded once, the first picture of each N-second stretch kept: [(file, moment)]. Each chosen
    picture's own time is written by FFmpeg (metadata print) - right for videos with a varying frame rate too."""
    own = None
    if not cwd:                            # (the times' file by a relative name: no path to escape in the filter)
        own = cwd = (HOME / "data" / f"pics-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}").resolve()
        cwd.mkdir(parents=True, exist_ok=True)
    try:
        times_f = Path(cwd) / "times.txt"
        times_f.unlink(missing_ok=True)
        # the choice first (whole fields are needed for it), then only the chosen pictures are converted (HDR is slow)
        vf = (["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if interlaced else []) \
            + [f"select='isnan(prev_selected_t)+gt(floor(t/{every})\\,floor(prev_selected_t/{every}))'",
               "metadata=mode=add:key=me:value=1", "metadata=mode=print:file=times.txt"] + tail
        pattern = str(folder).replace("%", "%%") + os.sep + "p_%05d.jpg"    # a % in a name is not a number pattern
        _run_progress([str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-map", "0:v:0", "-vf", ",".join(vf),
                       "-fps_mode", "vfr", "-q:v", "2", pattern], duration, progress_cb, cancel_cb, job_id=job_id, cwd=cwd)
        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        stamps = [float(x) for x in re.findall(r"pts_time:\s*(-?[\d.]+)", times_f.read_text("utf-8", "replace"))] \
            if times_f.is_file() else []
    finally:
        if own:
            shutil.rmtree(own, ignore_errors=True)
    def num(f):                            # (by the number: p_100000 comes after p_99999)
        try:
            return int(f.stem.split("_", 1)[1])
        except (ValueError, IndexError):
            return -1
    pics = sorted(folder.glob("p_*.jpg"), key=lambda f: (num(f), f.name))
    # each picture named by its stretch (each is the first of a later stretch than the one before)
    used, prev, made = set(), -1, []
    for i, f in enumerate(pics):
        ts = stamps[i] if i < len(stamps) else float(i * every)
        k = max(prev + 1, int((ts + 1e-6) // every))
        prev = k
        name = name_of(k * every)
        while name in used:
            name += "_2"
        used.add(name)
        dst = folder / f"{name}.jpg"
        f.replace(dst)
        made.append((dst, max(0.0, ts)))
    return made


def save_frames_every(source, every: int, output_dir=None, progress_cb=None, cancel_cb=None, job_id=None, clock=False,
                      title: str = "") -> dict:
    """A picture every N seconds of a video (for a report): the first picture of each N-second stretch (0-N, N-2N,
    ...), at the video's full size, in a new folder next to the converted videos ('<name>_pictures_every_10s'), each
    named by the start of its stretch ('<name>_01m30s.jpg'); clock: the date and time of that moment on it."""
    source = Path(os.path.abspath(str(source)))
    if not source.is_file():
        raise FileNotFoundError(str(source))
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available")
    duration = float(probe_duration(source) or 0.0)
    if duration <= 0:
        raise RuntimeError("Could not read video duration")
    every = int(every)
    base = Path(output_dir) if output_dir else output_folder()
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = HOME / "Converted"                       # the chosen folder is not there now (a disk not connected)
        base.mkdir(parents=True, exist_ok=True)
    stem = source.stem[:80]                              # folder and file names well inside Windows' path length
    for n in range(1, 1000):
        folder = base / (f"{stem}_pictures_every_{every}s" + ("" if n == 1 else f"_{n}"))
        try:
            folder.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError("No free name in " + str(base))
    folder = Path(os.path.abspath(str(folder)))
    cwd, how, parts = None, "", []
    try:
        hdr = _hdr_kind(ffmpeg, source)
        if clock:                          # the clock's subtitles and font in a folder of their own (FFmpeg runs there)
            parts, how = clock_parts(ffmpeg, [source], [duration])
            cwd = (HOME / "data" / f"clock-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}").resolve()
            cwd.mkdir(parents=True, exist_ok=True)
            (cwd / "clock.ass").write_text(clock_ass(parts, 1, _out_size(media_sig(ffmpeg, source), "keep_resolution", 0, "")), "utf-8")
            from .textfx import install_fonts
            install_fonts(cwd)
        interlaced = _is_interlaced(ffmpeg, source)
        tail = ([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []) \
            + ["scale='trunc(iw*sar/2)*2':ih", "setsar=1"] + (["ass=clock.ass:fontsdir=fonts"] if cwd else []) \
            + ["format=gbrp", "format=yuvj420p"]
        wid = 3 if duration >= 6000 else 2
        name_of = lambda t: f"{stem}_{t // 60:0{wid}d}m{t % 60:02d}s"
        # each picture by itself: FFmpeg goes to the stretch's start and decodes only from the key picture before it
        # (the same picture as decoding the whole video, about ten times faster for a long 4K video); a video that
        # will not be read that way: the whole video decoded once and the pictures chosen on the way
        made = _pictures_by_seeking(ffmpeg, source, every, duration, interlaced, tail, folder, name_of, progress_cb, cancel_cb, cwd,
                                    job_id)
        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        if not made:
            made = _pictures_by_decoding(ffmpeg, source, every, duration, interlaced, tail, folder, name_of, progress_cb, cancel_cb,
                                         job_id, cwd)
        if not made:
            raise RuntimeError("No pictures were made")
        pics = [m[0] for m in made]
        total = sum(m[0].stat().st_size for m in made)
        pdf = None
        try:                               # all of them on A4 pages, for a report (the pictures stay without it)
            pdf = pictures_pdf(folder / f"{stem}_pictures.pdf", made, source.name, every, parts[0][2] if parts else None,
                               progress_cb, cancel_cb, report=title)
        except Exception as exc:
            if str(exc) == "cancelled" or (cancel_cb and cancel_cb()):
                raise
            pdf = None
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        if cwd:
            shutil.rmtree(cwd, ignore_errors=True)
    return {"source": str(source), "output": str(folder), "frames": len(pics), "every": every,
            "source_bytes": source.stat().st_size, "output_bytes": total, "saved_percent": 0.0, **({"clock": how} if how else {}),
            **({"pdf": str(pdf)} if pdf else {})}


def _pdf_of_jpegs(path: Path, pages, dpi: int = 150) -> None:
    """A PDF written in one pass: each page one JPEG picture (as it is, DCTDecode) filling the page. pages yields
    (jpeg bytes, width px, height px); only one page is in memory at a time."""
    offsets, kids = {}, []
    with open(path, "wb") as f:
        def obj(n: int, body: bytes, stream: bytes | None = None) -> None:
            offsets[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + body)
            if stream is not None:
                f.write(b"\nstream\n" + stream + b"\nendstream")
            f.write(b"\nendobj\n")
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        n = 3
        for jpg, w, h in pages:
            pw, ph = w * 72.0 / dpi, h * 72.0 / dpi
            obj(n, f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB /BitsPerComponent 8 "
                   f"/Filter /DCTDecode /Length {len(jpg)} >>".encode(), jpg)
            draw = f"q {pw:.2f} 0 0 {ph:.2f} 0 0 cm /Im0 Do Q".encode()
            obj(n + 1, f"<< /Length {len(draw)} >>".encode(), draw)
            obj(n + 2, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.2f} {ph:.2f}] /Resources << /XObject << /Im0 {n} 0 R >> >> "
                       f"/Contents {n + 1} 0 R >>".encode())
            kids.append(n + 2)
            n += 3
        obj(2, f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode())
        xref = f.tell()
        f.write(f"xref\n0 {n}\n0000000000 65535 f \n".encode())
        for i in range(1, n):
            f.write(f"{offsets[i]:010d} 00000 n \n".encode())
        f.write(f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())


def pictures_pdf(path: Path, pics: list, title: str, every: int, start=None, progress_cb=None, cancel_cb=None,
                 report: str = "") -> Path | None:
    """The pictures of one video on A4 pages (150 dpi): the video's name, how often, and under each picture its moment
    in the video (and the clock's time when it is known). Written in one pass, page by page (a long video's hundreds
    of pictures never sit in memory together; each page tells the job it is alive; Stop stops it). In the program's
    language."""
    if not pics:
        return None
    from PIL import Image, ImageDraw, ImageFont
    from datetime import timedelta
    from .textfx import FONT_DIR
    try:
        from .i18n import ui_language, ru_plural
        ru = ui_language() == "ru"
    except Exception:
        ru, ru_plural = False, None
    def font(name, px):
        try:
            return ImageFont.truetype(str(FONT_DIR / name), px)
        except OSError:
            return ImageFont.load_default()
    W, H, M, GAP, CAP = 1240, 1754, 60, 24, 34
    f_title, f_sub, f_cap = font("Montserrat-ExtraBold.ttf", 34), font("Montserrat-SemiBold.ttf", 22), font("Montserrat-SemiBold.ttf", 20)
    with Image.open(pics[0][0]) as im0:
        aspect = im0.width / max(1, im0.height)
    cols = 2 if aspect >= 1.2 else 3
    cw = (W - 2 * M - (cols - 1) * GAP) // cols
    ph = int(cw / aspect)
    top, bottom = M + 110, M + 40
    rows = max(1, (H - top - bottom + GAP) // (ph + CAP + GAP))
    per = cols * rows
    pages = (len(pics) + per - 1) // per
    n = len(pics)
    count = (f"{n} " + ru_plural(n, "кадр", "кадра", "кадров")) if ru and ru_plural else f"{n} picture{'s' if n != 1 else ''}"
    sub = (f"Кадры каждые {every} с · {count}" if ru else f"Pictures every {every} s · {count}") \
        + ((" · снято " if ru else " · filmed ") + f"{start:%d.%m.%Y %H:%M:%S}" if start else "")
    if report:                             # the report's own title on top; the video's name goes under it
        title, sub = report, f"{title} · {sub}"
    tmp = path.with_name(path.stem + ".part.pdf")
    probe_d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while len(title) > 8 and probe_d.textlength(title, font=f_title) > W - 2 * M:     # a long name: shortened with …
        title = title[:-6] + "…"
    while len(sub) > 8 and probe_d.textlength(sub, font=f_sub) > W - 2 * M:
        sub = sub[:-6] + "…"

    def made_pages():
        import io
        for pg in range(pages):
            if cancel_cb and cancel_cb():
                raise RuntimeError("cancelled")
            page = Image.new("RGB", (W, H), "white")
            d = ImageDraw.Draw(page)
            d.text((M, M), title, font=f_title, fill=(20, 20, 20))
            d.text((M, M + 50), sub, font=f_sub, fill=(90, 90, 90))
            for k, (pic, t) in enumerate(pics[pg * per:(pg + 1) * per]):
                x = M + (k % cols) * (cw + GAP)
                y = top + (k // cols) * (ph + CAP + GAP)
                try:
                    with Image.open(pic) as im:
                        im.draft("RGB", (cw, ph))
                        th = im.convert("RGB").resize((cw, ph), Image.LANCZOS)
                    page.paste(th, (x, y))
                except (OSError, ValueError):      # (a picture that cannot be read: its place stays grey)
                    d.rectangle((x, y, x + cw, y + ph), fill=(225, 225, 225))
                ti = int(t)
                cap = f"{ti // 3600}:{ti // 60 % 60:02d}:{ti % 60:02d}" if ti >= 3600 else f"{ti // 60}:{ti % 60:02d}"
                if start:
                    cap += f"   {start + timedelta(seconds=t):%d.%m.%Y %H:%M:%S}"
                d.text((x, y + ph + 6), cap, font=f_cap, fill=(40, 40, 40))
            foot = (f"стр. {pg + 1} из {pages}" if ru else f"page {pg + 1} of {pages}")
            d.text((W - M - d.textlength(foot, font=f_cap), H - M - 10), foot, font=f_cap, fill=(120, 120, 120))
            buf = io.BytesIO()
            page.save(buf, "JPEG", quality=85)
            page.close()
            if progress_cb:
                progress_cb(100.0)
            yield buf.getvalue(), W, H
    try:
        _pdf_of_jpegs(tmp, made_pages())
        os.replace(tmp, path)
        return path
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _stream_time_base(ffmpeg, source) -> float:
    """Seconds per number of -frame_pts: one frame at the video's rate (e.g. 1/30; 29.97 fps -> 1001/30000)."""
    cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=60, **process_kwargs())
    line = next((l for l in (cp.stderr or "").splitlines() if " Video: " in l), "")
    m = re.search(r"(\d+(?:\.\d+)?)(k?) fps", line) or re.search(r"(\d+(?:\.\d+)?)(k?) tbr", line)
    if not m:
        return 1 / 30
    v = float(m.group(1)) * (1000 if m.group(2) else 1)
    if abs(v - 29.97) < 0.01 or abs(v - 59.94) < 0.01 or abs(v - 23.98) < 0.01:
        v = {29.97: 30000 / 1001, 59.94: 60000 / 1001, 23.98: 24000 / 1001}[round(v, 2)]
    return 1.0 / v if v > 0 else 1 / 30


# the names this converter gives (a sweep in a folder of the person's own touches only these)
_OUR_FRAME = re.compile(r"_frame_\d+m\d\ds(?:_\d+)?\.jpg$", re.I)
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
        for f in folder.glob("*_frame_*.jpg"):
            try:
                if _OUR_FRAME.search(f.name) and f.stat().st_size == 0:
                    f.unlink()
            except OSError:
                pass
        _sweep_pdf_parts(folder)
    except OSError:
        pass


def _sweep_pdf_parts(folder: Path) -> None:
    """A pictures PDF the app was closed while writing (in a pictures folder of ours)."""
    for d in folder.glob("*_pictures_every_*s*"):
        for f in d.glob("*_pictures.part.pdf") if d.is_dir() else []:
            try:
                f.unlink()
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
        for f in folder.glob("*_frame_*.jpg"):              # a picture being saved when the app closed
            try:
                if _OUR_FRAME.search(f.name) and f.stat().st_size == 0:
                    f.unlink()
            except OSError:
                pass
        for pat in ("ffmpeg2pass-*", "join-*.txt"):     # two-pass logs / part lists of a conversion that did not finish
            for f in (HOME / "data").glob(pat):
                try:
                    f.unlink()
                except OSError:
                    pass
        for f in [*(HOME / "data").glob("clock-*"), *(HOME / "data").glob("pics-*")]:   # (clock fonts; picture times)
            if f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
        _sweep_pdf_parts(folder)
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


TURNS = {90: "transpose=1", 270: "transpose=2", 180: "hflip,vflip"}   # clockwise degrees -> FFmpeg filter


def _scale_args(preset: str, hdr: str | None = None, interlaced: bool = False, turn: int = 0):
    cap = PRESETS[preset]["cap"]
    parts = ["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if interlaced else []   # camcorder fields -> frames
    parts += [HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []
    parts += [TURNS[turn]] if turn in TURNS else []           # "Turn the picture" (after the video's own rotation)
    # TV levels in every copy (16-235, as players, TVs and messengers expect): a camera's full-range picture (GoPro,
    # phones: yuvj420p) is converted. FFmpeg 7.1 negotiates the range and would keep full range otherwise (seen on
    # the Windows runner: Y 2..240 in a converted GoPro-like clip; FFmpeg 7.0 converted it by itself).
    if cap:
        # Cap the long edge. 1920 => 1920x1080 landscape or 1080x1920 portrait.
        parts.append(f"scale='min({int(cap)},iw)':'min({int(cap)},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"
                     ":out_range=tv")
    else:
        parts.append("scale=out_range=tv")
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if hdr in HDR_TO_SDR else []
    return ["-vf", ",".join(parts), *tags]


def _cancelled(job_id: int | None):
    if not job_id:
        return False
    with db() as con:
        r = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (int(job_id),)).fetchone()
    return bool(r and r["cancel_requested"])


def _run_progress(cmd, duration_s: float, progress_cb=None, cancel_cb=None, phase_base=0.0, phase_span=1.0, job_id=None, cwd=None):
    with keep_awake():   # a long conversion must not be cut by Windows going to sleep
        return _run_progress_inner(cmd, duration_s, progress_cb, cancel_cb, phase_base, phase_span, job_id, cwd)


def _run_progress_inner(cmd, duration_s: float, progress_cb=None, cancel_cb=None, phase_base=0.0, phase_span=1.0, job_id=None, cwd=None):
    global _CURRENT_PROCESS, _CURRENT_PROCESS_JOB_ID
    if _EXITING.is_set():                  # the app is quitting: nothing new starts (the job resumes at the next start)
        raise RuntimeError("cancelled")
    flags, si = _flags()
    full = [str(x) for x in cmd[:-1]] + ["-progress", "pipe:1", "-nostats", str(cmd[-1])]
    errors = []
    p = subprocess.Popen(
        full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        creationflags=flags, startupinfo=si, close_fds=True, cwd=str(cwd) if cwd else None
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
    finishing = None                       # from 99 %: the file's end (and +faststart's rewrite) may take minutes, silently
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
                            if frac >= 0.99 and finishing is None and job_id:
                                finishing = _Keepalive(job_id).__enter__()
                        except Exception:
                            pass
                    elif k == "progress" and v == "end":
                        if progress_cb:
                            progress_cb((phase_base + phase_span) * 100.0)
                        if finishing is None and job_id:
                            finishing = _Keepalive(job_id).__enter__()
                elif line:
                    errors.append(line[-500:])
                    if len(errors) > 12:
                        errors.pop(0)
        code = p.wait()
        if code != 0:
            raise RuntimeError(("FFmpeg failed: " + " | ".join(errors[-4:]))[:1200])
    finally:
        if finishing is not None:
            finishing.__exit__()
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
                 cut=None, mute=False, turn=0, prefer=None, extra=None):
    """One video converted (cut = (start, end) in seconds: only that part). extra {"frames": N}: pictures every N s
    instead of a video."""
    if extra and extra.get("frames"):
        return save_frames_every(source, int(extra["frames"]), output_dir, progress_cb, cancel_cb, job_id, clock=bool(extra.get("clock")),
                                 title=str(extra.get("title") or ""))
    source = Path(os.path.abspath(str(source)))          # (FFmpeg may run in another folder: the clock's)
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
    clock, how = (clock_parts(ffmpeg, [source], [float(probe_duration(source) or duration)], cut) if extra and extra.get("clock")
                  else (None, ""))
    out, made_on, short = _encode(ffmpeg, input_args, source, duration, preset, target_mb, progress_cb, cancel_cb, output_dir, job_id, tag=tag,
                           mute=bool(mute), turn=turn, prefer=prefer, extra=extra, clock=clock)
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
        **({"turn": int(turn)} if int(turn or 0) in TURNS else {}),
        **({"extra": shown_extra(extra, mute)} if extra else {}),
        **({"cut": [round(float(cut[0]), 3), round(min(float(cut[1]), float(probe_duration(source) or cut[1])), 3)]} if cut else {}),
        **({"clock": how} if how else {}),
        **({"short": short} if short else {}),
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
               beat=None, mute=False, turn=0, extra=None):
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
    duration, durs = 0.0, []
    for src in sources:
        if beat:
            beat()
        d = float(probe_duration(src) or 0.0)
        if d <= 0:
            raise RuntimeError("Could not read video duration")
        duration += d
        durs.append(d)
    clock, how = clock_parts(ffmpeg, sources, durs) if extra and extra.get("clock") else (None, "")
    listfile = (HOME / "data" / f"join-{os.getpid()}-{threading.get_ident()}.txt").resolve()
    listfile.parent.mkdir(parents=True, exist_ok=True)
    # one line per part; inside '...' nothing is special except the quote itself
    listfile.write_text("".join("file '" + str(src.resolve()).replace("'", "'\\''") + "'\n" for src in sources), "utf-8")
    try:
        out, made_on, short = _encode(ffmpeg, ["-f", "concat", "-safe", "0", "-i", str(listfile)], sources[0], duration, preset, target_mb,
                               progress_cb, cancel_cb, output_dir, job_id, tag="joined", mute=bool(mute), turn=turn, extra=extra,
                               clock=clock)
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
        **({"turn": int(turn)} if int(turn or 0) in TURNS else {}),
        **({"extra": shown_extra(extra, mute)} if extra else {}),
        "output": str(out),
        "source_bytes": src_size,
        "output_bytes": out_size,
        "saved_percent": round(max(0.0, (1.0 - out_size / max(1, src_size)) * 100.0), 1),
        "preset": preset,
        "target_mb": int(target_mb) if target_mb else None,
        "made_on": made_on,
        **({"clock": how} if how else {}),
        **({"short": short} if short else {}),
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
_GPU_FAILS_EXTRA: list = [0]   # the same for the More options / turned way on the card (never stops the plain way)
_GPU_LAST_ERROR: list = [""]
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
    """The card is tried for a conversion: not turned off, not failed twice in a row, not shown slower or different
    by "Check this PC -> Test converting on the graphics card", and this FFmpeg can encode on an NVIDIA card."""
    if (load_config().get("convert") or {}).get("gpu") is False or _GPU_FAILS[0] >= 2:
        return False
    t = gpu_test_saved()
    if t and t.get("use") is False:
        return False
    return _nvenc_works()


def gpu_extra_ok() -> bool:
    """The card for turned videos and the More options too: only after the card test made them on it with the same
    picture and faster (Check this PC / Convert -> Test converting on the graphics card)."""
    return gpu_test_saved().get("extra_use") is True and _GPU_FAILS_EXTRA[0] < 2


def _nvenc_works() -> bool:
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


# "Check this PC -> Test converting on the graphics card": a 5-second 4K HEVC test clip made smaller with the processor
# and with the card; the times and how alike the two pictures are (PSNR). Saved in the settings; a card that was
# slower or gave a different picture is not used for conversions (until tested again). No video of the person's used.
_GT = {"running": False, "started": 0.0, "step": "", "result": None}
_GT_LOCK = threading.Lock()


def gpu_test_saved() -> dict:
    try:
        return dict((load_config().get("convert") or {}).get("gpu_test") or {})
    except Exception:
        return {}


def gpu_test_state() -> dict:
    with _GT_LOCK:
        return {"running": _GT["running"], "step": _GT["step"],
                "elapsed_s": round(time.time() - _GT["started"], 1) if _GT["running"] else 0.0}


def _psnr(ffmpeg, a, b) -> float | None:
    cp = subprocess.run([str(ffmpeg), "-hide_banner", "-nostdin", "-i", str(a), "-i", str(b), "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, **process_kwargs())
    m = re.search(r"average:([\d.]+|inf)", cp.stderr or "")
    return (99.0 if m.group(1) == "inf" else float(m.group(1))) if m else None


def run_gpu_test(folder, step=lambda s: None, save=None) -> dict:
    folder = Path(folder)
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    res = {"tested_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "use": False, "gpu": []}
    try:
        from .hwdecode import gpu_names_cached
        res["gpu"] = gpu_names_cached()
    except Exception:
        pass
    try:
        step("Making a 4K test clip")
        clip = folder / "test_4k_hevc.mp4"
        subprocess.run([str(ffmpeg), "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=3840x2160:rate=60:d=5",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:d=5", "-c:v", "libx265", "-preset", "ultrafast",
                        "-x265-params", "log-level=error:keyint=60", "-tag:v", "hvc1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(clip)], check=True, capture_output=True, timeout=900, **process_kwargs())
        _GPU.clear(); _GPU_FAILS[0] = 0; _GPU_LAST_ERROR[0] = ""
        step("Converting with the processor")
        t0 = time.time()
        c = convert_file(clip, "share_1080p", output_dir=folder / "out", prefer="cpu")
        res["cpu_s"] = round(time.time() - t0, 1)
        if not _nvenc_works():
            res["error"] = "no NVIDIA graphics card that this FFmpeg can encode on"
            return res
        step("Converting with the graphics card")
        t1 = time.time()
        g = convert_file(clip, "share_1080p", output_dir=folder / "out", prefer="gpu")
        res["gpu_s"] = round(time.time() - t1, 1)
        if g.get("made_on") != "nvidia":
            res["error"] = "the graphics card could not convert: " + (_GPU_LAST_ERROR[0] or "?")
            return res
        step("Comparing the pictures")
        res["psnr"] = _psnr(ffmpeg, g["output"], c["output"])
        res["use"] = bool(res["psnr"] and res["psnr"] >= 30 and res["gpu_s"] < res["cpu_s"])
        if not res["use"]:
            return res
        if save:                           # (the plain result kept even if the second part never ends)
            save(dict(res))
        # the More options and a turned picture on the card (decoded and made smaller there, the rest as on the
        # processor): a full-range clip (as GoPro films), a part of it, turned, at 2x, with a logo and the date and
        # time - both ways, compared
        try:
            step("Making a second test clip")
            clip2 = folder / "test_4k_hevc_full.mp4"
            subprocess.run([str(ffmpeg), "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=3840x2160:rate=60:d=4", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:d=4",
                            "-c:v", "libx265", "-preset", "ultrafast", "-x265-params", "log-level=error:keyint=60", "-tag:v", "hvc1",
                            "-pix_fmt", "yuvj420p", "-color_range", "pc", "-c:a", "aac", "-shortest", str(clip2)],
                           check=True, capture_output=True, timeout=900, **process_kwargs())
            logo = folder / "test_logo.png"
            from PIL import Image
            Image.new("RGBA", (300, 100), (255, 0, 255, 255)).save(logo)
            ex = {**clean_extra({"speed": 2, "clock": True}), "logo": {"path": str(logo), "corner": "bottom-right", "size": 12}}
            step("More options with the processor")
            t2 = time.time()
            ce = convert_file(clip2, "share_1080p", output_dir=folder / "out", prefer="cpu", turn=90, extra=ex, cut=(0.5, 3.5))
            res["extra_cpu_s"] = round(time.time() - t2, 1)
            step("More options with the graphics card")
            t3 = time.time()
            ge = convert_file(clip2, "share_1080p", output_dir=folder / "out", prefer="gpu", turn=90, extra=ex, cut=(0.5, 3.5))
            res["extra_gpu_s"] = round(time.time() - t3, 1)
            if ge.get("made_on") != "nvidia":
                res["extra_error"] = "the graphics card could not do it: " + (_GPU_LAST_ERROR[0] or "?")
            else:
                res["extra_psnr"] = _psnr(ffmpeg, ge["output"], ce["output"])
                res["extra_use"] = bool(res["extra_psnr"] and res["extra_psnr"] >= 30 and res["extra_gpu_s"] < res["extra_cpu_s"])
        except Exception as exc:
            res["extra_error"] = str(exc)[-300:]
        return res
    except Exception as exc:
        res["error"] = str(exc)[-300:]
        return res
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        _GPU.clear(); _GPU_FAILS[0] = 0


def start_gpu_test(folder) -> bool:
    with _GT_LOCK:
        if _GT["running"]:
            return False
        _GT.update(running=True, started=time.time(), step="", result=None)

    def work():
        try:
            from .config import update_config
            def keep(r):
                update_config(lambda cfg: cfg.setdefault("convert", {}).__setitem__("gpu_test", r))
            r = run_gpu_test(folder, step=lambda s: _GT.__setitem__("step", s), save=keep)
            keep(r)
            _GT["result"] = r
        finally:
            with _GT_LOCK:
                _GT["running"] = False
    threading.Thread(target=work, daemon=True, name="ConvertGpuTest").start()
    return True


def gpu_test_summary(r: dict) -> str:
    """One line for Check this PC."""
    if not r:
        return "Not tested yet."
    if r.get("use"):
        line = (f"Used: {r.get('gpu_s')} s instead of {r.get('cpu_s')} s on the processor "
                f"({round(float(r.get('cpu_s') or 0) / max(0.1, float(r.get('gpu_s') or 1)), 1)}x faster), the same picture.")
        if r.get("extra_use"):
            line += (f" With the More options too: {r.get('extra_gpu_s')} s instead of {r.get('extra_cpu_s')} s.")
        elif "extra_use" in r or r.get("extra_error"):
            line += " The More options stay on the processor."
        else:                              # (a test from before the More options could go to the card)
            line += " Test again to use the card for the More options too."
        return line
    if r.get("gpu_s") and r.get("psnr") is not None:
        return (f"Not used: {r.get('gpu_s')} s on the graphics card, {r.get('cpu_s')} s on the processor"
                + (" - a different picture." if float(r.get("psnr") or 0) < 30 else " - not faster."))
    return "Not used: " + str(r.get("error") or "the graphics card could not convert") + "."


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
    W, H = (cap, int(round(h * k / 2)) * 2) if w >= h else (int(round(w * k / 2)) * 2, cap)   # (FFmpeg: the nearest even)
    return {"pre": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
            "vf": f"scale_cuda={W}:{H},hwdownload,format=nv12,scale=in_range=auto:out_range=tv,format=yuv420p",
            # (the More options: decoded and made smaller on the card, the small picture then through the same filters
            # as on the processor - turn, speed, Brighter, the logo, the clock)
            "head": f"scale_cuda={W}:{H},hwdownload,format=nv12",
            "codec": ["-color_range", "tv", "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr",
                      "-cq", str(int(PRESETS[preset]["crf"]) + _GPU_CQ_STEP), "-b:v", "0", "-profile:v", "high"],
            "size": (W, H)}


# More options of Convert ("extra"): speed (faster, or slow motion), vertical 9:16, a logo, less wind noise, an even sound.
SPEEDS = (1, 2, 4, 8, 0.5, 0.25)
# the sound made even: quiet speech louder, loud parts softer (EBU R128, -16 LUFS as phones and players play it), back
# at 48 kHz (loudnorm works at 192 kHz)
LOUD = ["loudnorm=I=-16:TP=-1.5:LRA=11", "aresample=48000"]
BRIGHTER = "normalize=blackpt=black:whitept=white:smoothing=30:independence=0,eq=gamma=1.15"
VERTICALS = ("", "crop", "blur")
LOGO_CORNERS = ("bottom-right", "bottom-left", "top-right", "top-left")
LOGO_FILE = "convert_logo.png"


def logo_saved() -> dict:
    """The logo chosen once on the Convert page (a PNG kept in the data folder), its corner and size (% of the width)."""
    cfg = dict((load_config().get("convert") or {}).get("logo") or {})
    f = HOME / "data" / LOGO_FILE
    if not f.is_file():
        return {}
    corner = cfg.get("corner") if cfg.get("corner") in LOGO_CORNERS else "bottom-right"
    try:
        size = min(40, max(5, int(cfg.get("size") or 12)))
    except (TypeError, ValueError):
        size = 12
    return {"path": str(f), "corner": corner, "size": size}


def clean_extra(extra) -> dict:
    """The page's choices, checked: {"speed": 2|4|8|0.5|0.25, "vertical": "crop"|"blur", "logo": {...}, "wind": True,
    "loud": True} (only what is chosen); or {"frames": N} (with "clock": True when chosen) alone."""
    out = {}
    if not extra:
        return out
    if not isinstance(extra, dict):
        raise ValueError("Unknown option")
    sp = extra.get("speed", 1)
    if isinstance(sp, bool) or not isinstance(sp, (int, float, str)):
        raise ValueError("Unknown speed")
    try:
        spf = float(sp)
    except (TypeError, ValueError, OverflowError):
        spf = -1.0
    sp = next((x for x in SPEEDS if abs(spf - x) < 1e-9), None)     # (NaN / inf match nothing)
    if sp is None:
        raise ValueError("Unknown speed")
    if sp != 1:
        out["speed"] = sp
    v = extra.get("vertical") or ""
    if v not in VERTICALS:
        raise ValueError("Unknown vertical")
    if v:
        out["vertical"] = v
    if extra.get("logo") is True or isinstance(extra.get("logo"), dict):
        lg = job_logo()
        if not lg:
            raise ValueError("Choose a logo first")
        out["logo"] = lg                        # the job's own copy (a later change of the logo is not this job's)
    if extra.get("wind") is True:
        out["wind"] = True
    if extra.get("loud") is True:
        out["loud"] = True
    if extra.get("clock") is True:
        out["clock"] = True
    if extra.get("bright") is True:
        out["bright"] = True
    fr = extra.get("frames")
    if fr not in (None, 0, "", False):
        try:
            fr = int(fr) if not isinstance(fr, bool) and float(fr) == int(float(fr)) else -1
        except (TypeError, ValueError, OverflowError):
            fr = -1
        if fr not in FRAME_STEPS:
            raise ValueError("Unknown option")
        title = re.sub(r"[\x00-\x1f\x7f]+", " ", extra.get("title")).strip()[:120] if isinstance(extra.get("title"), str) else ""
        out = {"frames": fr, **({"clock": True} if extra.get("clock") is True else {}),      # pictures: the clock and
               **({"title": title} if title else {})}                                        # the report's title apply
    return out


def _sar(sig: dict) -> float:
    try:
        a, b = (int(x) for x in str(sig.get("sar") or "1:1").split(":"))
        return a / b if a > 0 and b > 0 else 1.0
    except ValueError:
        return 1.0


def _out_size(sig: dict, preset: str, turn: int, vertical: str) -> tuple[int, int]:
    """The size of the converted picture (as the filters below make it: square pixels first), for the logo's size."""
    cap = PRESETS[preset]["cap"]
    if vertical:
        return (720, 1280) if cap == 1280 else (1080, 1920)
    try:
        w, h = (int(x) for x in str(sig.get("size") or "1920x1080").split("x"))
    except ValueError:
        w, h = 1920, 1080
    w = int(w * _sar(sig)) // 2 * 2                      # the picture as shown (HDV 1440x1080 at 4:3 pixels: 1920)
    if int(sig.get("rotation") or 0) in (90, 270):
        w, h = h, w
    if turn in (90, 270):
        w, h = h, w
    if cap and max(w, h) > cap:
        k = cap / max(w, h)
        w, h = int(round(w * k / 2)) * 2, int(round(h * k / 2)) * 2
    return w, h


def job_logo() -> dict:
    """The logo as it is now, copied for one job (a logo removed or replaced while the job waits or runs changes
    nothing for it): {"path", "corner", "size"} or {}."""
    lg = logo_saved()
    if not lg:
        return {}
    import hashlib
    data = Path(lg["path"]).read_bytes()
    d = HOME / "data" / "convert_logos"
    d.mkdir(parents=True, exist_ok=True)
    f = d / (hashlib.sha256(data).hexdigest()[:20] + ".png")
    if not f.is_file():
        tmp = f.with_suffix(".part")
        tmp.write_bytes(data)
        os.replace(tmp, f)
    return {"path": str(f), "corner": lg["corner"], "size": lg["size"]}


# Date and time of the recording in a corner (Convert → More): when it was filmed, every second, as the clock of the
# place showed it. Cameras (GoPro, DJI, other cameras, dashcams) write their own clock's time marked as UTC - shown as
# written. Phones write real UTC - shown in this PC's time zone: an iPhone also writes the local time with its zone
# (shown as written); an Android phone writes the time the recording STOPPED (its length is taken off). Without a
# time in the file: the file's own date (the end of the recording) minus its length.
_PHONE_TAG = re.compile(r"^\s*(com\.android\.[\w.]*|com\.apple\.[\w.]*)\s*:", re.M)
_TIME_TAG = re.compile(r"^\s*(creation_time|com\.apple\.quicktime\.creationdate)\s*:\s*(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)", re.M)


def recording_start(ffmpeg, source, duration: float | None = None) -> tuple:
    """(naive datetime of the first picture as the local clock showed it, "camera" | "phone" | "file")."""
    source = Path(str(source))
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, **process_kwargs())
        text = (cp.stderr or "").split("Stream mapping:", 1)[0]
    except Exception:
        text = ""
    found = {}
    for m in _TIME_TAG.finditer(text):
        try:
            when = datetime(*(int(x) for x in m.groups()[1:]))
        except ValueError:
            continue
        if 1995 <= when.year <= 2100:                  # (an unset camera clock gives 1904 / 1970 / 2000-01-01)
            found.setdefault(m.group(1), when)
    def length():
        return float(duration if duration is not None else (probe_duration(source) or 0.0))
    if "com.apple.quicktime.creationdate" in found:
        return found["com.apple.quicktime.creationdate"], "phone"
    if "creation_time" in found:
        phone = {m.group(1).split(".")[1] for m in _PHONE_TAG.finditer(text)}   # (tags only - never the file's name or folder)
        if not phone:
            return found["creation_time"], "camera"
        when = found["creation_time"]
        if "android" in phone and "apple" not in phone:
            from datetime import timedelta
            try:
                when -= timedelta(seconds=round(max(0.0, length())))
            except (OSError, ValueError, OverflowError):
                pass
        return when.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None), "phone"
    try:
        d = length()
        return datetime.fromtimestamp(source.stat().st_mtime - max(0.0, d)).replace(microsecond=0), "file"
    except (OSError, ValueError, OverflowError):
        return None, ""


def _ass_time(cs: int) -> str:
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clock_ass(parts, speed: float, size: tuple, corner: str = "bottom-left") -> str:
    """Subtitles showing the date and time, a line per second: parts = [(where in the copy before any speed change,
    seconds, the clock at that moment)]; the copy's times divided by the speed."""
    W, H = int(size[0]), int(size[1])
    fs = max(14, int(round(min(W, H) * 0.045)))
    m = max(6, int(round(min(W, H) * 0.03)))
    align = {"bottom-left": 1, "bottom-right": 3, "top-left": 7, "top-right": 9}.get(corner, 1)
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
           "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Clock,Montserrat SemiBold,{fs},&H00FFFFFF,&H00FFFFFF,&H5A000000,&H5A000000,0,0,0,0,100,100,0,0,3,"
           f"{max(2, fs // 5)},0,{align},{m},{m},{m},1", "", "[Events]",
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    from datetime import timedelta
    sp = float(speed or 1) or 1.0
    for at, length, when in parts:
        if when is None or length <= 0:
            continue
        frac = when.microsecond / 1e6
        shown = when.replace(microsecond=0)
        t, nxt = 0.0, (1.0 - frac) if frac > 0 else 1.0
        while t < length - 1e-6:
            end = min(length, nxt)
            a, b = int(round((at + t) / sp * 100)), int(round((at + end) / sp * 100))
            if b > a:
                out.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Clock,,0,0,0,,{shown:%d.%m.%Y}  {shown:%H:%M:%S}")
            t, nxt, shown = end, nxt + 1.0, shown + timedelta(seconds=1)
    return "\n".join(out) + "\n"


def clock_parts(ffmpeg, sources, durations, cut=None) -> tuple:
    """The clock of a copy: ([(where, seconds, clock)], how). Parts of one GoPro recording follow each other (the
    first part's time); other joined videos each with their own time; a cut starts at its start."""
    sources = [Path(str(x)) for x in sources]
    if len(sources) > 1 and gopro_recording([x.name for x in sources]):
        first, how = recording_start(ffmpeg, sources[0], durations[0])
        from datetime import timedelta
        parts, at = [], 0.0
        for d in durations:
            parts.append((at, d, first + timedelta(seconds=at) if first else None))
            at += d
        return parts, how
    parts, hows, at = [], [], 0.0
    for src, d in zip(sources, durations):
        when, how = recording_start(ffmpeg, src, d)
        hows.append(how)
        if cut and len(sources) == 1:
            from datetime import timedelta
            when = when + timedelta(seconds=float(cut[0])) if when else None
            d = float(cut[1]) - float(cut[0])
        parts.append((at, d, when))
        at += d
    return parts, ("file" if "file" in hows else hows[0] if hows else "")


def shown_extra(extra, mute=False) -> dict:
    """The options as the copy has them: without sound (Without sound, 4x, 8x, ¼×) no "less wind" / "even sound"."""
    ex = dict(extra or {})
    if mute or float(ex.get("speed") or 1) not in (0.5, 1, 2):
        ex.pop("wind", None)
        ex.pop("loud", None)
    return ex


def _speed_filters(sig: dict, speed: float) -> list[str]:
    """Faster: the picture's times divided, 30 pictures a second (pictures between them left out). Slow motion: the
    times multiplied - every picture of a 60 fps video shown at 30 a second (½×), of a 120 fps one at ¼×; 50 fps at
    ½×: 25 a second; at most 60 a second (120 fps at ½×); a 30 fps video at ½× shows each picture twice."""
    if speed > 1:
        return [f"setpts=PTS/{int(speed)}", "fps=30"]
    if 0 < speed < 1:
        k = int(round(1 / speed))
        try:
            fps = float(sig.get("fps") or 0)
        except (TypeError, ValueError):
            fps = 0.0
        # every picture once: the source's rate / k (50 fps at ½×: 25 a second, not 25 padded to 30); at most 60; a
        # source too slow for that (30 fps at ½×): 30 a second, pictures shown twice
        rate = round(min(60.0, fps / k), 3) if fps / k >= 23.5 else 30
        return [f"setpts=PTS*{k}", f"fps={rate:g}"]
    return []


def _extra_graph(sig: dict, preset: str, hdr, interlaced: bool, turn: int, extra: dict, mute: bool, logo_index: int,
                 gpu_head: str | None = None):
    """The filter graph for the More options: [v] and, when the sound is changed (speed, wind), [a]; also without
    the sound branch (the first pass of a size target). Returns (graph with sound, graph without sound, sound kept,
    sound through the graph)."""
    speed = float(extra.get("speed") or 1)
    vert = extra.get("vertical") or ""
    lg = extra.get("logo") if isinstance(extra.get("logo"), dict) else (logo_saved() if extra.get("logo") else {})
    if extra.get("logo") and not (lg and Path(str(lg.get("path") or "")).is_file()):
        raise RuntimeError("The logo of this conversion is not there any more - choose the logo again and convert again")
    square = (vert or lg or extra.get("clock")) and abs(_sar(sig) - 1.0) > 0.01   # 4:3 pixels of HDV / DV: square first
    if gpu_head:                           # the card decoded and scaled it (never HDR, interlaced, 4:3 pixels or 9:16)
        if vert or interlaced or hdr or square:
            raise ValueError("not for the graphics card")
        pre = [gpu_head] + ([TURNS[turn]] if turn in TURNS else []) + _speed_filters(sig, speed)
        g = f"[0:v:0]{','.join(pre)}[vb]"
        vert = ""
    pre = (["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if interlaced else []) \
        + ([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []) \
        + (["scale='trunc(iw*sar/2)*2':ih", "setsar=1"] if square else []) \
        + ([TURNS[turn]] if turn in TURNS else []) \
        + _speed_filters(sig, speed)
    cap = PRESETS[preset]["cap"]
    if gpu_head:
        pass
    elif vert:
        VW, VH = (720, 1280) if cap == 1280 else (1080, 1920)
        if vert == "crop":                 # the middle of the picture, the sides cut off
            g = f"[0:v:0]{','.join(pre + [f'scale={VW}:{VH}:force_original_aspect_ratio=increase', f'crop={VW}:{VH}', 'setsar=1'])}[vb]"
        else:                              # the whole picture on a blurred, enlarged copy of itself
            head = ",".join(pre) if pre else "null"
            g = (f"[0:v:0]{head},split[va][vf0];"
                 f"[va]scale={VW // 4}:{VH // 4}:force_original_aspect_ratio=increase,crop={VW // 4}:{VH // 4},boxblur=6:2,"
                 f"scale={VW}:{VH},setsar=1[bg];[vf0]scale={VW}:{VH}:force_original_aspect_ratio=decrease,setsar=1[fg];"
                 f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vb]")
    else:
        body = pre + ([f"scale='min({int(cap)},iw)':'min({int(cap)},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"]
                      if cap else [])
        g = f"[0:v:0]{','.join(body) if body else 'null'}[vb]"
    last = "vb"
    if extra.get("bright"):                # a dark video lighter: its own darkest-to-brightest stretched over the whole
        g += f";[{last}]{BRIGHTER}[vbr]"   # range (smoothed over a second), then a little gamma lift
        last = "vbr"
    if lg:
        W, H = _out_size(sig, preset, turn, vert)
        lw = max(16, int(W * lg["size"] / 100) // 2 * 2)
        lh = max(16, int(H * 0.3) // 2 * 2)                # a tall logo never covers more than 30 % of the height
        m = max(8, int(min(W, H) * 0.03))
        x = f"W-w-{m}" if lg["corner"].endswith("right") else f"{m}"
        y = f"H-h-{m}" if lg["corner"].startswith("bottom") else f"{m}"
        g += (f";[{logo_index}:v]scale={lw}:{lh}:force_original_aspect_ratio=decrease,format=rgba[lg];"
              f"[{last}][lg]overlay={x}:{y}:format=auto:eof_action=repeat[vl]")
        last = "vl"
    if extra.get("clock"):                 # the date and time (subtitles in the job's own folder, the program's font)
        g += f";[{last}]ass=clock.ass:fontsdir=fonts[vk]"
        last = "vk"
    g += f";[{last}]scale=out_range=tv,format=yuv420p[v]"
    sound = not mute and bool(sig.get("audio")) and speed in (0.5, 1, 2)
    # the sound at 2x / half speed: atempo, its start moved like the picture's (setpts) - else a sound that starts after
    # the picture would be late (or early) in the copy; a gap in the sound (between joined parts) filled first, as
    # atempo counts its samples from the start
    af = (["highpass=f=100", "afftdn=nf=-25"] if extra.get("wind") else []) \
        + (LOUD if extra.get("loud") else []) \
        + ({2: ["aresample=async=1", "atempo=2.0", "asetpts=PTS-STARTPTS/2"],
            0.5: ["aresample=async=1", "atempo=0.5", "asetpts=PTS+STARTPTS"]}.get(speed) or [])
    through = sound and bool(af)                          # unchanged sound: every track kept as it is mapped
    ga = g + (f";[0:a:0]{','.join(af)}[a]" if through else "")
    return ga, g, sound, through


def _encode(ffmpeg, input_args, source: Path, duration: float, preset, target_mb, progress_cb, cancel_cb, output_dir, job_id,
            tag: str = "", mute: bool = False, turn: int = 0, prefer: str | None = None, extra: dict | None = None,
            clock=None) -> Path:
    """The picture and sound made with the preset (or to a size, two passes) into a new file in Converted; returns it
    and where the picture was made ("nvidia" / "cpu")."""
    hdr = _hdr_kind(ffmpeg, source)
    interlaced = _is_interlaced(ffmpeg, source)
    target_mb = int(target_mb) if target_mb else None
    turn = int(turn or 0) if int(turn or 0) in TURNS else 0
    extra = dict(extra or {})
    speed = float(extra.get("speed") or 1)
    sp_tag = f"x{int(speed)}" if speed > 1 else (f"slow{int(round(1 / speed))}x" if 0 < speed < 1 else "")
    keeps_sound = not mute and speed in (0.5, 1, 2)       # (4x, 8x, ¼×: no sound - no "less wind" / "even sound")
    tag = "_".join(x for x in (tag, sp_tag, "vertical" if extra.get("vertical") else "",
                                  "logo" if extra.get("logo") else "", "lesswind" if extra.get("wind") and keeps_sound else "",
                                  "evensound" if extra.get("loud") and keeps_sound else "", "clock" if extra.get("clock") else "",
                                  "brighter" if extra.get("bright") else "",
                                  "turned" if turn else "", "nosound" if mute else "") if x)
    duration = duration / speed                            # the copy's own length (faster: shorter; slow motion: longer)
    out = Path(os.path.abspath(_unique_output(source, preset, target_mb, Path(output_dir) if output_dir else None, tag)))   # reserved
    amap = [] if mute else ["-map", "0:a?"]                # "Without sound": no sound in the copy at all
    aenc = (lambda k: ["-an"]) if mute else (lambda k: ["-c:a", "aac", "-b:a", f"{int(k)}k"])
    part = out.with_name(out.stem + ".part.mp4")       # its own name: the output name is this conversion's alone
    passlog = None
    made_on = "cpu"
    cwd = None                                             # the clock's folder (FFmpeg runs there: no path to escape)
    try:
        cfg = PRESETS[preset]
        vsel = ["-map", "0:v:0", *amap, *_scale_args(preset, hdr, interlaced, turn)]     # the picture as before
        vsel1 = ["-map", "0:v:0", *_scale_args(preset, hdr, interlaced, turn)]            # (first pass: no sound)
        logo_in = []
        through = False
        if extra:                                                   # More options: one filter graph
            sig = media_sig(ffmpeg, source)
            if extra.get("logo"):
                lgx = extra["logo"] if isinstance(extra.get("logo"), dict) else logo_saved()
                if not (lgx and Path(str(lgx.get("path") or "")).is_file()):
                    raise RuntimeError("The logo of this conversion is not there any more - choose the logo again and convert again")
                logo_in = ["-i", str(lgx["path"])]
            if extra.get("clock"):
                parts = clock if clock is not None else clock_parts(ffmpeg, [source], [duration * speed])[0]
                lgc = (extra.get("logo") or {}).get("corner") if isinstance(extra.get("logo"), dict) else ""
                cwd = (HOME / "data" / f"clock-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}").resolve()
                cwd.mkdir(parents=True, exist_ok=True)
                (cwd / "clock.ass").write_text(clock_ass(parts, speed, _out_size(sig, preset, turn, extra.get("vertical") or ""),
                                                         "bottom-right" if lgc == "bottom-left" else "bottom-left"), "utf-8")
                from .textfx import install_fonts
                install_fonts(cwd)
            ga, gv, sound, through = _extra_graph(sig, preset, hdr, interlaced, turn, extra, mute, 1)
            vsel = [*logo_in, "-filter_complex", ga, "-map", "[v]",
                    *((["-map", "[a]"] if through else ["-map", "0:a?"]) if sound else [])]
            vsel1 = [*logo_in, "-filter_complex", gv, "-map", "[v]"]
            if not sound:
                mute = True
                aenc = lambda k: ["-an"]
        common = [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", *input_args, *vsel,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-color_range", "tv", "-preset", "veryfast",
        ]

        if target_mb:
            # the sound's share: each sound track the copy will have (none: a drone video, Without sound, 4x)
            tracks = 0 if mute else (1 if through else _audio_tracks(ffmpeg, source))
            audio_k = int(cfg["audio_k"]) * tracks
            total_bits = float(target_mb) * 1024 * 1024 * 8 * 0.94
            video_k = max(250, int(total_bits / duration / 1000.0 - audio_k))
            passlog = str((HOME / "data" / f"ffmpeg2pass-{os.getpid()}-{threading.get_ident()}").resolve())
            Path(passlog).parent.mkdir(parents=True, exist_ok=True)
            pass1 = [
                str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", *input_args, *vsel1,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-color_range", "tv", "-preset", "veryfast",
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "1", "-passlogfile", passlog, "-fps_mode", "cfr", "-an", "-f", "null", os.devnull
            ]
            _run_progress(pass1, duration, progress_cb, cancel_cb, 0.0, 0.48, job_id=job_id, cwd=cwd)
            pass2 = common + [
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "2", "-passlogfile", passlog, "-fps_mode", "cfr",   # (the frames of pass 1, also with gaps)
                *aenc(cfg["audio_k"]), "-movflags", "+faststart", str(part)
            ]
            _run_progress(pass2, duration, progress_cb, cancel_cb, 0.50, 0.50, job_id=job_id, cwd=cwd)
        else:
            plan = None
            filtered = bool(turn or extra)     # turned, or More options: the card's way only once the card test proved it
            fails = _GPU_FAILS_EXTRA if filtered else _GPU_FAILS
            gcmd = []
            try:
                # prefer: "cpu" / "gpu" only for the card test of Check this PC (both ways on the same clip)
                use = _nvenc_works() if prefer == "gpu" else False if prefer == "cpu" else (gpu_ok() and (not filtered or gpu_extra_ok()))
                sig_g = media_sig(ffmpeg, source) if use else {}
                plan = gpu_plan(sig_g, preset, hdr, interlaced) if use and not extra.get("vertical") else None
                if plan and filtered:
                    ga_g, _gv, sound_g, through_g = _extra_graph(sig_g, preset, hdr, interlaced, turn, extra, mute, 1, gpu_head=plan["head"])
                    gcmd = [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-xerror", *plan["pre"], *input_args, *logo_in,
                            "-filter_complex", ga_g, "-map", "[v]",
                            *((["-map", "[a]"] if through_g else ["-map", "0:a?"]) if sound_g else []), *plan["codec"],
                            *aenc(cfg["audio_k"]), "-movflags", "+faststart", str(part)]
                elif plan:
                    gcmd = [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-xerror", *plan["pre"], *input_args,
                            "-map", "0:v:0", *amap, "-vf", plan["vf"], *plan["codec"],
                            *aenc(cfg["audio_k"]), "-movflags", "+faststart", str(part)]
            except Exception:
                plan = None
            if plan and gcmd:
                try:
                    _run_progress(gcmd, duration, progress_cb, cancel_cb, job_id=job_id, cwd=cwd if filtered else None)
                    with _Keepalive(job_id):
                        got = float(probe_duration(part) or 0.0)
                        pic = _picture_seconds(ffmpeg, part)
                    if abs(got - duration) > max(0.5, 0.01 * duration) or pic < got - max(0.5, 0.01 * got):
                        raise RuntimeError(f"length {got:.2f} s (picture {pic:.2f} s) instead of {duration:.2f} s")
                    made_on = "nvidia"
                    fails[0] = 0
                except Exception as exc:
                    if str(exc).lower() == "cancelled" or (cancel_cb and cancel_cb()) or _EXITING.is_set() or _watchdog_pending(job_id):
                        raise                  # stopped, quitting, or the watchdog's restart: not the card's failure
                    fails[0] += 1
                    _GPU_LAST_ERROR[0] = str(exc)[-300:]
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
                _run_progress(cmd, duration, progress_cb, cancel_cb, job_id=job_id, cwd=cwd)

        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        short = None
        with _Keepalive(job_id):
            if not mute:                   # a copy shorter than the video: a damaged or half-copied source (said, kept)
                try:
                    got = float(probe_duration(part) or 0.0)
                    if 0 < got < duration - max(1.0, 0.02 * duration):
                        short = [round(got, 1), round(duration, 1)]
                except Exception:
                    pass
            for k in range(20):            # (Windows: Explorer or an antivirus may hold the name a moment)
                try:
                    part.replace(out)
                    break
                except OSError:
                    if k == 19:
                        raise
                    time.sleep(0.5)
        return out, made_on, short
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
        if cwd:
            shutil.rmtree(cwd, ignore_errors=True)
        if passlog:                        # two-pass logs (with .temp files while a pass runs): also after Cancel
            for f in Path(passlog).parent.glob(Path(passlog).name + "*"):
                try:
                    f.unlink()
                except Exception:
                    pass


class _Keepalive:
    """The job told alive every 15 s while it does a silent step that is not stuck (FFmpeg moving its index to the
    front of a big file on a slow disk, the checks of a finished file): the watchdog restarts only a stalled job.
    Bounded (30 min) - a step that never ends still counts as stalled after that."""
    def __init__(self, job_id, limit_s: float = 1800.0, every: float = 15.0):
        self.job_id, self.limit_s, self.every = job_id, limit_s, every
        self.stop = threading.Event()

    def __enter__(self):
        if self.job_id:
            t_end = time.time() + self.limit_s
            def beat():
                while not self.stop.wait(self.every) and time.time() < t_end:
                    try:
                        ts = _now()
                        with db() as con:
                            con.execute("UPDATE jobs SET progress_at=?,heartbeat_at=? WHERE id=? AND status='running'",
                                        (ts, ts, int(self.job_id)))
                            con.commit()
                    except Exception:
                        pass
            threading.Thread(target=beat, daemon=True, name="ConvertKeepalive").start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        return False


def _audio_tracks(ffmpeg, source) -> int:
    """How many sound tracks a video has (FFmpeg's own description)."""
    try:
        cp = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(source)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, **process_kwargs())
        return sum(1 for l in (cp.stderr or "").split("Stream mapping:", 1)[0].splitlines() if " Audio: " in l)
    except Exception:
        return 1


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


def _options(preset, target_mb, inventory_ids, paths, join, done, outputs, output_dir=None, cuts=None, mute=False, turn=0,
             extra=None) -> str:
    return json.dumps({"preset": preset, "target_mb": target_mb, "inventory_ids": list(inventory_ids or []),
                       "paths": [str(x) for x in (paths or [])], "join": bool(join),
                       **({"output_dir": str(output_dir)} if output_dir else {}),
                       **({"cuts": cuts} if cuts else {}), **({"mute": True} if mute else {}),
                       **({"turn": int(turn)} if int(turn or 0) in TURNS else {}),
                       **({"extra": extra} if extra else {}),
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
    turn=int(prior.get("turn") or 0) if str(prior.get("turn") or 0).isdigit() and int(prior.get("turn") or 0) in TURNS else 0
    extra=prior.get("extra") if isinstance(prior.get("extra"),dict) else {}
    opts=lambda: _options(preset,target_mb,inventory_ids,paths,join,done,outputs,output_dir,cuts,mute,turn,extra)
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
                                               job_id=job_id, output_dir=output_dir, mute=mute, turn=turn, extra=extra)
                        else:
                            res = join_files(parts, preset, target_mb, progress_cb=prog_join, cancel_cb=lambda: _cancelled(job_id),
                                             job_id=job_id, output_dir=output_dir, beat=lambda: _job_update(job_id, stage="converting"),
                                             mute=mute, turn=turn, extra=extra)
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
            if not src:                    # (a card not put back yet): said with its name, kept after a restart too
                failed += 1
                outputs.append({"source": str(filename), "error": "This video is not on this computer now"})
                done.add(key)
                processed_bytes += size
                _job_update(job_id, failed=failed, done=len(done), bytes_done=processed_bytes, options_json=opts(),
                            message=f"Skipped missing local file: {filename}")
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
                                          output_dir=output_dir, cut=cuts.get(str(key)) if isinstance(key, int) else None, mute=mute,
                                          turn=turn, extra=extra)
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
    _queue_runner_start()                  # conversions that waited in line when the app closed go on
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


def start_convert_job(inventory_ids=None, preset="share_1080p", target_mb=None, paths=None, join=False, cuts=None, mute=False,
                      turn=0, extra=None):
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
    try:
        turn = int(turn) if isinstance(turn, (int, float, str)) and not isinstance(turn, bool) and float(turn) == int(float(turn)) else -1
    except (TypeError, ValueError, OverflowError):
        turn = -1
    if turn not in (0, *TURNS):
        raise ValueError("Unknown turn")
    cuts = _clean_cuts(cuts, ids)
    extra = clean_extra(extra)
    if extra.get("frames") and (join or cuts):
        raise ValueError("Pictures are taken from whole videos, one by one (not joined, not cut).")
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
        # something runs (or conversions wait already): this one waits in line and starts by itself after them
        busy = con.execute("SELECT id,kind FROM jobs WHERE status IN ('running','queued') OR (kind='convert' AND status='waiting' "
                           "AND cancel_requested=0) ORDER BY id LIMIT 1").fetchone() or (True if _GT.get("running") else None)
        n = len(ids) + len(files)
        cur = con.execute(
            "INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("convert", "waiting" if busy else "running", _now(), None if busy else _now(), "waiting" if busy else "starting",
             "Waiting for the job before it" if busy else "Starting converter…", n_groups if join else n, 0, 0, 0, 0, 0,
             _options(preset, target_mb, ids, [str(f) for f in files], join, set(), [], output_folder(), cuts, bool(mute), turn, extra))
        )
        job_id = int(cur.lastrowid)
        con.commit()
    if busy:
        _queue_runner_start()
    else:
        threading.Thread(target=_convert_worker, args=(job_id, ids, preset, target_mb, [str(f) for f in files], join), daemon=True,
                         name=f"ArchivistConvert{job_id}").start()
    return job_id


# Conversions started while something else runs wait in line (status "waiting" - never "queued", which the library's
# worker takes) and start one by one, by themselves, when nothing runs; Remove (cancel) takes one out of the line.
_QLOCK = threading.Lock()
_QUEUE: dict = {"thread": None}


def dispatch_waiting():
    """The first conversion waiting in line started, when no job runs: its id, else None."""
    if _EXITING.is_set() or _GT.get("running"):          # (the card test of Check this PC runs: after it)
        return None
    with db() as con:                      # (a plain look first: no write lock every 2 s while a job runs)
        if con.execute("SELECT 1 FROM jobs WHERE status IN ('running','queued') LIMIT 1").fetchone() or not con.execute(
                "SELECT 1 FROM jobs WHERE kind='convert' AND status='waiting' AND cancel_requested=0 LIMIT 1").fetchone():
            return None
    try:                                   # a reel, an order, AI+ preparing, a Composer render or an update: after it
        from .watchdog import _other_work
        if _other_work():
            return None
    except Exception:
        pass
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        if con.execute("SELECT 1 FROM jobs WHERE status IN ('running','queued') LIMIT 1").fetchone():
            con.commit()
            return None
        r = con.execute("SELECT * FROM jobs WHERE kind='convert' AND status='waiting' AND cancel_requested=0 ORDER BY id LIMIT 1").fetchone()
        if not r:
            con.commit()
            return None
        ts = _now()
        con.execute("UPDATE jobs SET status='running',stage='starting',message='Starting converter…',started_at=?,progress_at=?,"
                    "heartbeat_at=? WHERE id=? AND status='waiting'", (ts, ts, ts, int(r["id"])))
        con.commit()
    jid = int(r["id"])
    try:
        opts = json.loads(r["options_json"] or "{}")
    except Exception:
        opts = {}
    ids = [int(x) for x in (opts.get("inventory_ids") or []) if str(x).isdigit() and int(x) > 0]
    paths = [str(x) for x in (opts.get("paths") or []) if str(x).strip()]
    preset = str(opts.get("preset") or "")
    if not (ids or paths) or preset not in PRESETS:
        _job_update(jid, status="failed", stage="done", message="Nothing to convert", error="nothing_to_convert", finished_at=_now())
        return None
    threading.Thread(target=_convert_worker, args=(jid, ids, preset, opts.get("target_mb"), paths, bool(opts.get("join"))),
                     daemon=True, name=f"ArchivistConvert{jid}").start()
    return jid


def _queue_loop():
    while not _EXITING.is_set():
        try:
            dispatch_waiting()
        except Exception:
            pass
        with _QLOCK:                       # (the last look and "no runner" as one step: a job added meanwhile starts one)
            try:
                with db() as con:
                    left = con.execute("SELECT 1 FROM jobs WHERE kind='convert' AND status='waiting' AND cancel_requested=0 LIMIT 1").fetchone()
            except Exception:
                left = True
            if not left:
                _QUEUE["thread"] = None
                return
        time.sleep(2)


def _queue_runner_start() -> None:
    with _QLOCK:
        t = _QUEUE.get("thread")
        if t is not None and t.is_alive():
            return
        t = threading.Thread(target=_queue_loop, daemon=True, name="ArchivistConvertQueue")
        _QUEUE["thread"] = t
        t.start()


def shutdown() -> None:
    """The app quits: the running FFmpeg is stopped (no orphan writing on); the job resumes at the next start."""
    _EXITING.set()
    with _LOCK:
        seeks = list(_SEEK_PROCS)
    for sp in seeks:                       # (the pictures' FFmpegs too)
        try:
            sp.kill()
        except Exception:
            pass
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

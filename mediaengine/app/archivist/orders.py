"""Orders from other programs: a folder put into "MediaEngine Data\\Orders\\Inbox" becomes a finished video in
"Orders\\Done". The format is ORDERS.md (next to this file; a copy is kept in the Orders folder). Nothing here
contacts the internet or publishes.

An order is a folder Inbox\\<order id>\\ with order.json (written LAST, once every other file of the order is there)
or a single file Inbox\\<order id>.json. MediaEngine takes it (moves it to Orders\\Received\\<order id>, where its
files stay), does it and writes the answer as ONE folder that appears complete:
  Orders\\Done\\<order id>\\    video.mp4 + result.json (what was made, SHA-256, checks) + order.json
  Orders\\Failed\\<order id>\\  result.json (code + reason) + order.json
Kinds:
  reel_from_videos  the usual reel (MediaEngine chooses the moments) from a folder, from chosen videos or from the
                    Library's videos of a theme; it is also a normal Auto Edit project (variants, edits, export).
  render_plan       an exact plan made by another program: pictures and/or pieces of videos with their times plus a
                    sound track (a narration, for example) -> one MP4. Only files inside the order folder are used.
Private / Rejected videos are never used: the reel engine skips them, and a plan can only use the order's own files.
Orders run one at a time; new ones start at once or wait for the owner's OK ("Run new orders at once").
"""
from __future__ import annotations

import json, math, os, re, shutil, subprocess, threading, time
from pathlib import Path

from . import auto_edit as ae
from .config import APP_PORT, BUILD, HOME, VERSION, load_config, update_config
from .db import now_iso
from .platform_adapter import process_kwargs

SCHEMA = "mediaengine.order/1"
RESULT_SCHEMA = "mediaengine.result/1"
KINDS = ("reel_from_videos", "render_plan")
SETTLE_S = 3.0            # an order is taken only when nothing in it changed for this long (still being copied)
POLL_S = 3.0
MAX_PLAN_S = 600.0        # a plan of at most 10 minutes
MAX_CLIPS = 300
MAX_SIDE = 4096
MAX_STILL_PIXELS = 50_000_000   # a bigger picture (a tiny file can say 40000x40000) would need gigabytes to decode
MAX_VIDEO_SIDE = 8192
MAX_ATTEMPTS = 3          # an order that was started this many times without an answer (crash, restart) waits for the owner
# what FFmpeg may read for a plan: plain media files only. A playlist (HLS .m3u8, concat) could name ANY file on the PC,
# so it is refused, and every input is opened with the demuxer found here (a file swapped later cannot become one).
STILL_FORMATS = {"png_pipe", "jpeg_pipe", "webp_pipe", "bmp_pipe", "tiff_pipe", "image2"}
VIDEO_FORMATS = {"mov", "matroska", "avi", "mpeg", "mpegts", "asf", "flv", "dv"}
AUDIO_FORMATS = {"wav", "mp3", "mov", "flac", "ogg", "aac", "matroska", "w64", "aiff", "asf"}
_INPUT_RE = re.compile(r"^Input #0, (.+?), from ", re.M)
# FFmpeg may not even OPEN another container while a file is checked (a playlist opens the files it names first)
FORMAT_WHITELIST = ",".join(sorted(STILL_FORMATS | VIDEO_FORMATS | AUDIO_FORMATS))
STILL_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_ID = re.compile(r"^[^\W_][\w.\- ()]{0,79}$")
_IGNORED_SUFFIX = (".tmp", ".part", ".partial", ".crdownload")

_LOCK = threading.Lock()          # one order at a time (the watcher and a button press never run two)
_MOVE_LOCK = threading.RLock()    # taking an order and writing an answer (short; buttons never wait for a render)
_CUR_LOCK = threading.Lock()      # the order being done now, its Stop flag and its FFmpeg - read and changed together
_BACKOFF: dict = {}               # Inbox id -> time before which it is not tried again (a folder Windows cannot move now)
_STATE_LOCK = threading.Lock()
_WAKE = threading.Event()
_STOP_ALL = threading.Event()
_RUN_NOW: set = set()             # ids the owner pressed "Run" for (when new orders wait for an OK)
_CURRENT: dict = {"id": "", "proc": None, "stop": threading.Event(), "done": 0, "total": 0, "step": ""}
_WATCHER: dict = {"thread": None}
_DOCS: dict = {}                  # README.txt / ORDERS.md written once per app start


class OrderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


# ---------------------------------------------------------------- places

def root() -> Path:
    return HOME / "Orders"


def inbox_dir() -> Path:
    return root() / "Inbox"


def received_dir() -> Path:
    return root() / "Received"


def done_dir() -> Path:
    return root() / "Done"


def failed_dir() -> Path:
    return root() / "Failed"


README = """MediaEngine orders / Заказы MediaEngine

Inbox     - put an order here: a folder <order id> with order.json written LAST (or one file <order id>.json).
            Сюда другая программа кладёт заказ: папку <номер заказа> с order.json (его пишут последним).
Received  - orders MediaEngine has taken, with their files.  /  Принятые заказы с их файлами.
Done      - the answers: <order id>\\video.mp4 + result.json.  /  Готовые: видео и квитанция.
Failed    - orders that could not be done: <order id>\\result.json says why.  /  Не выполненные и причина.

Format: ORDERS.md in this folder. Nothing is published or sent anywhere by MediaEngine.
Формат заказа описан в ORDERS.md в этой папке. MediaEngine ничего не публикует и никуда не отправляет.
"""


def ensure_dirs() -> None:
    for d in (inbox_dir(), received_dir(), done_dir(), failed_dir()):
        d.mkdir(parents=True, exist_ok=True)
    if _DOCS.get("root") == str(root()):
        return
    _DOCS["root"] = str(root())
    for name, data in (("README.txt", README.encode("utf-8")), ("ORDERS.md", _doc_bytes())):
        target = root() / name
        try:      # the description of the format, for whoever writes the program that orders
            if data and (not target.is_file() or target.read_bytes() != data):
                target.write_bytes(data)
        except OSError:
            pass


def _doc_bytes() -> bytes:
    try:
        return (Path(__file__).resolve().parent / "ORDERS.md").read_bytes()
    except OSError:
        return b""


def auto_run() -> bool:
    try:
        return (load_config().get("orders") or {}).get("auto_run", True) is not False
    except Exception:
        return True


def set_auto_run(on: bool) -> None:
    update_config(lambda c: c.setdefault("orders", {}).__setitem__("auto_run", bool(on)))
    _WAKE.set()


# ---------------------------------------------------------------- small helpers

def _sha(path: Path) -> str:
    return ae.sha256_file(path)


def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise OrderError("ORDER_FILE_MISSING", f"{Path(path).name} is missing")
    except (OSError, UnicodeError, ValueError) as exc:
        raise OrderError("ORDER_JSON_INVALID", f"{Path(path).name} is not valid JSON ({str(exc)[:120]})")


def _write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _newest_mtime(p: Path, limit: int = 3000) -> float:
    try:
        t = p.stat().st_mtime
    except OSError:
        return time.time()
    if p.is_dir():
        n = 0
        for dirpath, dirnames, filenames in os.walk(p):
            for name in dirnames + filenames:
                n += 1
                if n > limit:
                    return t
                try:
                    t = max(t, os.stat(os.path.join(dirpath, name)).st_mtime)
                except OSError:
                    return time.time()     # a file vanished or is locked: still being written
    return t


def _settled(p: Path) -> bool:
    return time.time() - _newest_mtime(p) >= SETTLE_S


def valid_id(oid: str) -> bool:
    return bool(_ID.match(oid)) and not oid.endswith((".", " ")) and oid.split(".")[0].upper() not in ae._WIN_RESERVED


def _safe_id(oid: str) -> str:
    s = re.sub(r"[^\w.\- ()]", "_", oid)[:80].strip(" .") or "order"
    return s if s[0].isalnum() else "order " + s


def _unique(base: Path, name: str) -> Path:
    """base/name, or base/"name (2)", "name (3)"... - a name no order has in Received, Done or Failed."""
    def used(x: str) -> bool:
        return any((d / x).exists() for d in (received_dir(), done_dir(), failed_dir())) or (base / f".{x}.partial").exists()
    x, n = name, 2
    while used(x):
        x, n = f"{name} ({n})", n + 1
    return base / x


def _move(src: Path, dst: Path, tries: int = 40) -> None:
    """Rename (same drive, one step: never half a folder); a file held open for a moment (antivirus, Explorer, the
    writing program) is retried for 20 s, then the error is raised and the order is taken / answered later."""
    for k in range(tries):
        try:
            os.replace(src, dst)
            return
        except FileNotFoundError:
            raise
        except OSError:
            if k == tries - 1:
                raise
            time.sleep(0.5)


def _clean_path(raw: str) -> str:
    return str(raw).strip().strip('"').strip()


def _no_network(raw: str, field: str) -> None:
    """\\\\server\\share, //server/share, \\\\?\\UNC\\..., quoted or not: Windows would send the owner's sign-in there."""
    s = _clean_path(raw).replace("/", "\\")
    if s.startswith("\\\\") or s.startswith("\\??\\"):
        raise OrderError("ORDER_NETWORK_PATH", f"{field}: network paths are not used (Windows would sign in to that server)")


def _inside(base: Path, rel, field: str) -> Path:
    """A file named by the order: a relative path inside the order folder, nothing outside it."""
    if not isinstance(rel, str) or not rel.strip():
        raise OrderError("ORDER_FIELD_INVALID", f"{field} must be the name of a file in the order folder")
    _no_network(rel, field)
    r = Path(_clean_path(rel).replace("\\", "/"))
    if r.is_absolute() or r.drive or any(part == ".." for part in r.parts):
        raise OrderError("ORDER_PATH_OUTSIDE", f"{field}: only files inside the order folder can be used ({rel})")
    p = (base / r).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        raise OrderError("ORDER_PATH_OUTSIDE", f"{field}: only files inside the order folder can be used ({rel})")
    if not p.is_file():
        raise OrderError("ORDER_FILE_MISSING", f"{field}: {rel} is not in the order folder")
    return p


def _own_path(base: Path, raw, field: str) -> Path:
    """A video, folder or music file of the owner: an absolute path on this PC, or a path inside the order folder."""
    if not isinstance(raw, str) or not raw.strip():
        raise OrderError("ORDER_FIELD_INVALID", f"{field} must be a path")
    _no_network(raw, field)
    s = _clean_path(raw)
    p = Path(s)
    if p.is_absolute():
        return p
    r = Path(s.replace("\\", "/"))
    if r.drive or any(part == ".." for part in r.parts):
        raise OrderError("ORDER_PATH_OUTSIDE", f"{field}: a relative path must stay inside the order folder ({raw})")
    return (base / r).resolve()


def _num(v, field: str, lo: float, hi: float) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise OrderError("ORDER_FIELD_INVALID", f"{field} must be a number")
    x = float(v)
    if x < lo or x > hi:
        raise OrderError("ORDER_FIELD_INVALID", f"{field} must be between {lo:g} and {hi:g}")
    return x


def _text(v, field: str, limit: int = 120) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        raise OrderError("ORDER_FIELD_INVALID", f"{field} must be text")
    return " ".join(v.replace("\x00", " ").split())[:limit]


def _ffmpeg() -> str:
    return ae._ffmpeg() or "ffmpeg"


def _input_args(fmt: str) -> list[str]:
    return ["-f", fmt, *(["-pattern_type", "none"] if fmt == "image2" else [])]


def _decode_info(path: Path, video_frames: int | None = None, timeout: int = 300, fmt: str = "") -> dict:
    """Read a picture / sound / video with FFmpeg (the same FFmpeg that renders): its streams and decoded length."""
    import sys
    if str(ae.ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ae.ENGINE_DIR))
    import medeng_media_probe_v41 as probe_mod  # the engine's FFmpeg-only probe (Windows has no ffprobe)
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-format_whitelist", FORMAT_WHITELIST, *(_input_args(fmt) if fmt else []), "-i", str(path)]
    if video_frames:
        cmd += ["-frames:v", str(video_frames)]
    cmd += ["-f", "null", "-"]
    try:
        cp = subprocess.run(cmd, **process_kwargs(dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                                        errors="replace", timeout=timeout, check=False)))
    except subprocess.TimeoutExpired:
        return {"ok": False, "streams": [], "seconds": 0.0, "error": "timeout"}
    text = cp.stderr or ""
    head = text
    for mark in ("\nOutput #", "\nStream mapping:"):
        head = head.split(mark, 1)[0]
    streams = []
    for raw in head.splitlines():
        sm = probe_mod._STREAM_RE.match(raw)
        if not sm:
            continue
        row = {"type": sm.group(2).lower(), "codec": sm.group(3).lower()}
        zm = probe_mod._SIZE_RE.search(raw) if row["type"] == "video" else None
        if zm:
            row["width"], row["height"] = int(zm.group(1)), int(zm.group(2))
        streams.append(row)
    times = ae._TIME_RE.findall(text)
    secs = (int(times[-1][0]) * 3600 + int(times[-1][1]) * 60 + float(times[-1][2])) if times else 0.0
    return {"ok": cp.returncode == 0, "streams": streams, "seconds": secs, "error": text.strip().splitlines()[-1:] if cp.returncode else []}


def _header(path: Path, timeout: int = 60) -> dict:
    """What FFmpeg says about a file without decoding it: its container (demuxer) and streams with picture sizes."""
    import sys
    if str(ae.ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ae.ENGINE_DIR))
    import medeng_media_probe_v41 as probe_mod
    try:
        cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-format_whitelist", FORMAT_WHITELIST, "-i", str(path)],
                            **process_kwargs(dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                                  errors="replace", timeout=timeout, check=False)))
        text = cp.stderr or ""
    except (subprocess.TimeoutExpired, OSError):
        text = ""
    m = _INPUT_RE.search(text)
    streams = []
    for raw in text.splitlines():
        sm = probe_mod._STREAM_RE.match(raw)
        if not sm:
            continue
        row = {"type": sm.group(2).lower(), "codec": sm.group(3).lower()}
        zm = probe_mod._SIZE_RE.search(raw) if row["type"] == "video" else None
        if zm:
            row["width"], row["height"] = int(zm.group(1)), int(zm.group(2))
        streams.append(row)
    return {"format": m.group(1).split(",")[0].strip() if m else "", "streams": streams,
            "blocked": "not on whitelist" in text}       # a playlist / manifest (refused) - not just a damaged file


def _first(info: dict, kind: str) -> dict | None:
    return next((s for s in info["streams"] if s["type"] == kind), None)


# ---------------------------------------------------------------- reading and checking an order

def validate(order, base: Path) -> dict:
    if not isinstance(order, dict):
        raise OrderError("ORDER_JSON_INVALID", "order.json must hold one JSON object")
    if order.get("schema") != SCHEMA:
        raise OrderError("ORDER_SCHEMA_UNKNOWN", f'"schema" must be "{SCHEMA}"')
    kind = order.get("kind")
    if kind not in KINDS:
        raise OrderError("ORDER_KIND_UNKNOWN", 'kind must be "reel_from_videos" or "render_plan"')
    spec = {"kind": kind, "from": _text(order.get("from"), "from", 60) or "?", "title": _text(order.get("title"), "title", 80)}
    spec.update(_plan_spec(order, base) if kind == "render_plan" else _reel_spec(order, base))
    return spec


def _plan_spec(order: dict, base: Path) -> dict:
    plan = order.get("plan")
    if isinstance(plan, str):
        plan = _read_json(_inside(base, plan, "plan"))
    if not isinstance(plan, dict):
        raise OrderError("ORDER_FIELD_INVALID", "plan must be an object or the name of a JSON file in the order folder")
    w = int(_num(plan.get("width", 1080), "plan.width", 160, MAX_SIDE))
    h = int(_num(plan.get("height", 1920), "plan.height", 160, MAX_SIDE))
    if w % 2 or h % 2:
        raise OrderError("ORDER_FIELD_INVALID", "plan.width and plan.height must be even numbers")
    fps = _num(plan.get("fps", 30), "plan.fps", 1, 60)
    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        raise OrderError("ORDER_FIELD_INVALID", "plan.clips must be a list with at least one clip")
    if len(clips) > MAX_CLIPS:
        raise OrderError("PLAN_TOO_MANY_CLIPS", f"a plan can have at most {MAX_CLIPS} clips")
    out, t, prev_frame = [], 0.0, 0
    for i, c in enumerate(clips, 1):
        if not isinstance(c, dict):
            raise OrderError("ORDER_FIELD_INVALID", f"clip {i} must be an object")
        start = _num(c.get("start_s"), f"clip {i} start_s", 0, MAX_PLAN_S + 1)
        end = _num(c.get("end_s"), f"clip {i} end_s", 0, MAX_PLAN_S + 1)
        if abs(start - t) > 0.05:
            raise OrderError("PLAN_TIMES_INVALID", f"clip {i} starts at {start:g} s; it must start where the clip before it "
                                                   f"ends ({t:g} s) - clips follow each other without gaps")
        if end - start < 0.1:
            raise OrderError("PLAN_TIMES_INVALID", f"clip {i} is shorter than 0.1 s")
        if end > MAX_PLAN_S:
            raise OrderError("PLAN_TOO_LONG", f"a plan can be at most {MAX_PLAN_S:.0f} s long")
        frame = int(round(end * fps))
        if frame <= prev_frame:
            raise OrderError("PLAN_TIMES_INVALID", f"clip {i} is shorter than one frame")
        has_still, has_video = c.get("still") is not None, c.get("video") is not None
        if has_still == has_video:
            raise OrderError("ORDER_FIELD_INVALID", f'clip {i} needs exactly one of "still" (a picture) or "video"')
        fit = c.get("fit", "fit" if has_still else "fill")
        if fit not in ("fit", "fill"):
            raise OrderError("ORDER_FIELD_INVALID", f'clip {i} fit must be "fit" (whole picture) or "fill" (cropped)')
        row = {"n": i, "start_s": start, "end_s": end, "frames": frame - prev_frame, "fit": fit}
        if has_still:
            p = _inside(base, c["still"], f"clip {i} still")
            hd = _header(p)
            v = _first(hd, "video")
            if hd["format"] not in STILL_FORMATS or not v or (hd["format"] == "image2" and p.suffix.lower() not in STILL_SUFFIXES):
                raise OrderError("PLAN_IMAGE_UNREADABLE", f"clip {i}: {c['still']} is not a picture that can be read "
                                                          "(PNG, JPEG, WebP, BMP or TIFF)")
            if int(v.get("width") or 0) * int(v.get("height") or 0) > MAX_STILL_PIXELS:
                raise OrderError("PLAN_IMAGE_TOO_BIG", f"clip {i}: {c['still']} is {v.get('width')}x{v.get('height')} "
                                                       f"(at most {MAX_STILL_PIXELS // 1_000_000} megapixels)")
            info = _decode_info(p, video_frames=1, timeout=60, fmt=hd["format"])
            if not info["ok"] or not _first(info, "video"):
                raise OrderError("PLAN_IMAGE_UNREADABLE", f"clip {i}: {c['still']} is not a picture that can be read")
            row.update(still=p, fmt=hd["format"])
        else:
            p = _inside(base, c["video"], f"clip {i} video")
            from_s = _num(c.get("from_s", 0), f"clip {i} from_s", 0, 24 * 3600)
            hd = _header(p)
            v = _first(hd, "video")
            if hd["format"] not in VIDEO_FORMATS or not v:
                raise OrderError("PLAN_VIDEO_UNREADABLE", f"clip {i}: {c['video']} is not a video file that can be used "
                                                          f"(container: {hd['format'] or 'unknown'})")
            if max(int(v.get("width") or 0), int(v.get("height") or 0)) > MAX_VIDEO_SIDE:
                raise OrderError("PLAN_VIDEO_UNREADABLE", f"clip {i}: {c['video']} is larger than {MAX_VIDEO_SIDE} pixels")
            try:
                pr = ae.probe_any(p)
                dur = float(pr.get("format", {}).get("duration") or 0)
                ok = any(s.get("codec_type") == "video" for s in pr.get("streams", []))
            except Exception:
                dur, ok = 0.0, False
            if not ok or dur <= 0:
                raise OrderError("PLAN_VIDEO_UNREADABLE", f"clip {i}: {c['video']} is not a video that can be read")
            if from_s >= dur:
                raise OrderError("PLAN_TIMES_INVALID", f"clip {i}: from_s {from_s:g} s is after the end of {c['video']} ({dur:.1f} s)")
            row.update(video=p, from_s=from_s, source_s=dur, fmt=hd["format"])
        out.append(row)
        t, prev_frame = end, frame
    audio = plan.get("audio")
    apath, afmt = None, ""
    if audio not in (None, ""):
        apath = _inside(base, audio, "plan.audio")
        afmt = _header(apath)["format"]
        info = _decode_info(apath, timeout=300, fmt=afmt) if afmt in AUDIO_FORMATS else {"ok": False}
        if not info["ok"] or not _first(info, "audio") or info["seconds"] <= 0:
            raise OrderError("PLAN_AUDIO_UNREADABLE", f"plan.audio: {audio} is not a sound file that can be read")
    return {"width": w, "height": h, "fps": fps, "clips": out, "audio": apath, "audio_fmt": afmt, "frames": prev_frame,
            "total_s": round(prev_frame / fps, 3)}


def _reel_spec(order: dict, base: Path) -> dict:
    v = order.get("videos")
    if not isinstance(v, dict):
        raise OrderError("ORDER_FIELD_INVALID", 'videos must be an object: {"folder": ...}, {"files": [...]} or {"library_theme": ...}')
    keys = [k for k in ("folder", "files", "library_theme") if v.get(k) not in (None, "", [])]
    if len(keys) != 1:
        raise OrderError("ORDER_FIELD_INVALID", 'videos needs exactly one of "folder", "files" or "library_theme"')
    raw = {"length": order.get("length", 30), "format": order.get("format", "social_hd"), "sound": order.get("sound", "auto"),
           "mode": order.get("mode", "semantic"), "theme": order.get("theme") or "", "framing": order.get("framing", "fill")}
    text = order.get("text") or {}
    if not isinstance(text, dict):
        raise OrderError("ORDER_FIELD_INVALID", 'text must be an object: {"title": ..., "subtitle": ...}')
    raw["title"], raw["subtitle"] = _text(text.get("title"), "text.title", 200), _text(text.get("subtitle"), "text.subtitle", 200)
    spec = {"folder": None, "files": None, "library_theme": ""}
    if keys[0] == "folder":
        spec["folder"] = _own_path(base, v["folder"], "videos.folder")
    elif keys[0] == "files":
        if not isinstance(v["files"], list) or not all(isinstance(x, str) for x in v["files"]):
            raise OrderError("ORDER_FIELD_INVALID", "videos.files must be a list of paths")
        if len(v["files"]) > ae.MAX_INPUTS:
            raise OrderError("ORDER_FIELD_INVALID", f"at most {ae.MAX_INPUTS} videos in one reel")
        spec["files"] = [_own_path(base, x, "videos.files") for x in v["files"]]
    else:
        th = v["library_theme"]
        if th not in ae.THEMES:
            raise OrderError("ORDER_FIELD_INVALID", "videos.library_theme must be one of: " + ", ".join(ae.THEMES))
        spec["library_theme"] = th
        if order.get("mode") in (None, "", "semantic_plus"):      # a Library theme reel: AI+ with that theme, as in the Library
            raw["mode"], raw["theme"] = "semantic_plus", raw["theme"] or th
    if raw["mode"] == "semantic_plus" and not ae.aiplus_status()["ready"]:
        raise OrderError("AIPLUS_NOT_READY", "The AI+ model is not on this PC yet: download it once on 'Check this PC'")
    # the videos the engine will open: plain media files only (a manifest saved under a video name could make FFmpeg
    # fetch another file - a Private one, or one on a network share)
    spec["left_out"] = []
    if spec["files"] or (spec["folder"] and spec["folder"].is_dir()):
        try:
            paths = [Path(x) for x in (spec["files"] or ae.list_videos(spec["folder"]))]
        except OSError:
            paths = []
        keep, left_out = [], []
        for vp in paths:
            if not vp.is_file() or ae.cloud_only(vp):
                keep.append(vp)            # the build says it is missing / only in the cloud - never read here
                continue
            hd = _header(vp)
            if hd["format"] in VIDEO_FORMATS:
                keep.append(vp)
            elif hd.get("blocked"):
                raise OrderError("VIDEOS_NOT_USABLE", f"{vp.name} is not a plain video file (a playlist or manifest)")
            else:
                left_out.append(vp.name)   # damaged or unreadable: left out, as a reel from the app leaves it out
        if paths and not keep:
            raise OrderError("VIDEOS_NOT_USABLE", "None of the videos can be read")
        if left_out:                       # the engine gets exactly the readable files
            spec["files"], spec["folder"], spec["left_out"] = keep, None, left_out
    music = order.get("music")
    if music not in (None, ""):
        mp_ = _own_path(base, music, "music")
        if mp_.is_file() and _header(mp_)["format"] not in AUDIO_FORMATS:
            raise OrderError("ORDER_FIELD_INVALID", f"music: {mp_.name} is not a plain sound file")
        raw["music"] = str(mp_)
        if order.get("music_mode") == "music":
            raw["music_mode"] = "music"
        if order.get("beat_sync") is False:
            raw["beat_sync"] = False
    try:
        settings = ae.normalize_settings(raw, model_ready=ae.model_status()["ready"])
    except ValueError as exc:
        raise OrderError("ORDER_FIELD_INVALID", str(exc))
    spec["settings"] = settings
    return spec


# ---------------------------------------------------------------- the inbox

def inbox() -> list[dict]:
    """Orders waiting in Inbox, oldest first: {id, path, ready, waiting_for} (ready = order.json there and settled)."""
    ensure_dirs()
    out = []
    try:
        entries = list(inbox_dir().iterdir())
    except OSError:
        return []
    for p in entries:
        name = p.name
        if name.startswith((".", "~", "_")) or name.lower().endswith(_IGNORED_SUFFIX):
            continue
        try:
            if p.is_dir():
                oid, oj = name, p / "order.json"
            elif p.is_file() and p.suffix.lower() == ".json":
                oid, oj = p.stem, p
            else:
                continue
            mt = p.stat().st_mtime
        except OSError:
            continue
        has = oj.is_file()
        out.append({"id": oid, "path": p, "ready": has and _settled(p), "waiting_for": "" if has else "order.json", "mtime": mt})
    out.sort(key=lambda x: (x["mtime"], x["id"]))
    return out


def _peek(entry: dict) -> dict:
    """What a waiting order says (for the page), without taking it."""
    p = entry["path"]
    oj = p / "order.json" if p.is_dir() else p
    try:
        o = json.loads(oj.read_text(encoding="utf-8-sig"))
        return o if isinstance(o, dict) else {}
    except Exception:
        return {}


def _take(entry: dict, tries: int = 4) -> tuple[str, Path | None]:
    """Move a waiting order to Received. Returns (id, received folder) or (id, None) when it was refused at once
    (bad or already used id): then its answer is already in Failed."""
    oid, src = entry["id"], entry["path"]
    if not valid_id(oid):
        return _refuse_unreceived(src, _safe_id(oid), "ORDER_ID_INVALID",
                                  "The order id (folder or file name) may only have letters, digits, spaces, . - _ ( ) "
                                  "and at most 80 characters")
    if any((d / oid).exists() for d in (received_dir(), done_dir(), failed_dir())):
        return _refuse_unreceived(src, oid, "ORDER_ID_ALREADY_USED",
                                  f"An order with the id {oid!r} was already received. Every order needs a new id.")
    dst = received_dir() / oid
    if src.is_dir():
        _move(src, dst, tries)
    else:
        tmp = received_dir() / f".{oid}.taking"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        _move(src, tmp / "order.json", tries)
        _move(tmp, dst)
    _reset_state(dst, {"received_at": now_iso()})       # MediaEngine's own notes, never anything the order brought
    return oid, dst


def _refuse_unreceived(src: Path, name: str, code: str, message: str) -> tuple[str, None]:
    final = _unique(failed_dir(), name)
    part = failed_dir() / f".{final.name}.partial"
    shutil.rmtree(part, ignore_errors=True)
    part.mkdir(parents=True)
    _move(src, part / ("order" if src.is_dir() else "order.json"))
    order = None
    try:
        oj = part / "order" / "order.json" if (part / "order").is_dir() else part / "order.json"
        order = json.loads(oj.read_text(encoding="utf-8-sig"))
    except Exception:
        pass
    _write_json(part / "result.json", _result(final.name, order if isinstance(order, dict) else {}, "failed",
                                              error={"code": code, "message": message}, retry=False))
    _move(part, final)
    return final.name, None


# ---------------------------------------------------------------- state of an order being done

def _state_file(rdir: Path) -> Path:
    """MediaEngine's notes about an order (project, job, attempts) - kept OUTSIDE the order's folder: a file the
    ordering program put into its folder can never pose as them (it could name one of the owner's projects)."""
    return received_dir() / ".state" / f"{rdir.name}.json"


def _reset_state(rdir: Path, d: dict) -> None:
    with _STATE_LOCK:
        try:
            _state_file(rdir).parent.mkdir(parents=True, exist_ok=True)
            _write_json(_state_file(rdir), d)
        except OSError:
            pass


def _read_state(rdir: Path) -> dict:
    try:
        d = json.loads(_state_file(rdir).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write_state(rdir: Path, change: dict) -> dict:
    with _STATE_LOCK:
        d = _read_state(rdir)
        d.update(change)
        try:
            _state_file(rdir).parent.mkdir(parents=True, exist_ok=True)
            _write_json(_state_file(rdir), d)
        except OSError:
            pass
        return d


def _result(oid: str, order: dict, status: str, *, video: dict | None = None, checks=None, error=None, extra=None,
            received_at: str = "", started_at: str = "", retry: bool = True, order_sha: str = "") -> dict:
    r = {"schema": RESULT_SCHEMA, "order_id": oid, "status": status,
         "kind": order.get("kind") if order.get("kind") in KINDS else None,
         "from": str(order.get("from") or "")[:60], "title": str(order.get("title") or "")[:80],
         "order_sha256": order_sha or None, "received_at": received_at or None, "started_at": started_at or None,
         "finished_at": now_iso(), "mediaengine": {"version": VERSION, "build": BUILD}}
    if video:
        r["video"] = video
    if checks is not None:
        r["checks"] = checks
    if error:
        r["error"] = error
        r["can_retry"] = bool(retry)
    if extra:
        r.update(extra)
    return r


# ---------------------------------------------------------------- doing an order

def _stopped() -> bool:
    return _CURRENT["stop"].is_set() or _STOP_ALL.is_set()


def _process(oid: str) -> str:
    """Do the received order `oid`; returns "done" or "failed" (its answer is then in Done / Failed)."""
    rdir = received_dir() / oid
    st = _write_state(rdir, {"started_at": now_iso(), "attempts": int(_read_state(rdir).get("attempts") or 0) + 1})
    with _CUR_LOCK:      # a Stop pressed right now is never lost, nor applied to the next order
        _CURRENT["stop"] = threading.Event()
        _CURRENT.update(id=oid, proc=None, done=0, total=0, step="")
    order, order_sha, spec = {}, "", None
    for old in rdir.glob(".work*"):      # an earlier attempt's pieces (a crash, a stop)
        shutil.rmtree(old, ignore_errors=True)
    work = rdir / f".work-{int(time.time() * 1000)}"     # a new folder each attempt: nothing left over can mix in
    try:
        oj = rdir / "order.json"
        if oj.is_file():
            order_sha = _sha(oj)
        order = _read_json(oj)
        spec = validate(order, rdir)
        _write_state(rdir, {"kind": spec["kind"], "title": spec["title"], "from": spec["from"]})
        if spec["kind"] == "render_plan":
            work.mkdir(parents=True, exist_ok=True)
            video_path, extra = _render_plan(spec, rdir, work), {"plan": {"width": spec["width"], "height": spec["height"],
                                                                          "fps": spec["fps"], "clips": len(spec["clips"]),
                                                                          "audio": bool(spec["audio"])}}
            want = {"width": spec["width"], "height": spec["height"], "seconds": spec["total_s"], "audio": True,
                    "tolerance": max(0.1, 1.5 / spec["fps"])}
            move = True
        else:
            video_path, extra, want = _reel(spec, rdir)
            move = False
        checks = _check_output(video_path, want)
        if not all(c["pass"] for c in checks):
            bad = "; ".join(c["check"] + ": " + c["detail"] for c in checks if not c["pass"])
            raise OrderError("OUTPUT_CHECK_FAILED", "The finished video did not pass its checks (" + bad + ")")
        _publish_done(oid, order, order_sha, video_path, move, checks, extra, st)
        return "done"
    except OrderError as exc:
        if _STOP_ALL.is_set() and not _CURRENT["stop"].is_set():
            return "interrupted"      # the app is closing: no answer - the order is done again at the next start
        _publish_failed(oid, order, order_sha, exc.code, exc.message, st, retry=exc.code not in ("REJECTED_BY_OWNER",))
        return "failed"
    except Exception as exc:          # never leave an order half-done without an answer
        if _STOP_ALL.is_set():
            return "interrupted"
        _publish_failed(oid, order, order_sha, "INTERNAL_ERROR", (type(exc).__name__ + ": " + str(exc))[:300], st)
        return "failed"
    finally:
        shutil.rmtree(work, ignore_errors=True)
        with _CUR_LOCK:
            _CURRENT.update(id="", proc=None, step="")


def _video_entry(path: Path) -> dict:
    info = ae._probe(path)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"file": "video.mp4", "sha256": _sha(path), "bytes": path.stat().st_size,
            "duration_s": round(float(info.get("format", {}).get("duration") or 0), 3),
            "width": int(v.get("width") or 0), "height": int(v.get("height") or 0)}


def _publish_done(*a) -> None:
    _publish_done_now(*a)          # copies and hashes outside the lock; only the final rename takes it


def _publish_failed(*a, **k) -> None:
    _publish_failed_now(*a, **k)


def _publish_done_now(oid, order, order_sha, video_path: Path, move: bool, checks, extra, st) -> None:
    final = done_dir() / oid
    part = done_dir() / f".{oid}.partial"
    shutil.rmtree(part, ignore_errors=True)
    part.mkdir(parents=True)
    dst = part / "video.mp4"
    if move:
        _move(video_path, dst)
    else:
        shutil.copy2(video_path, dst)
    entry = _video_entry(dst)
    if not move and entry["sha256"] != _sha(video_path):
        raise OrderError("OUTPUT_COPY_FAILED", "The copy of the finished video is not the same as the video (disk full?)")
    try:
        shutil.copy2(received_dir() / oid / "order.json", part / "order.json")
    except OSError:
        pass
    _write_json(part / "result.json", _result(oid, order, "done", video=entry, checks=checks, extra=extra,
                                              received_at=st.get("received_at", ""), started_at=st.get("started_at", ""),
                                              order_sha=order_sha))
    with _MOVE_LOCK:
        if final.exists():             # a crash after a finished answer: the newer answer replaces it
            _retire(final)
        _move(part, final)
        _write_state(received_dir() / oid, {"finished": "done", "attempts": 0})
    _notify(oid, order, True)


def _publish_failed_now(oid, order, order_sha, code, message, st, retry=True) -> None:
    shutil.rmtree(done_dir() / f".{oid}.partial", ignore_errors=True)
    final = failed_dir() / oid
    part = failed_dir() / f".{oid}.partial"
    shutil.rmtree(part, ignore_errors=True)
    part.mkdir(parents=True)
    try:
        shutil.copy2(received_dir() / oid / "order.json", part / "order.json")
    except OSError:
        pass
    _write_json(part / "result.json", _result(oid, order if isinstance(order, dict) else {}, "failed",
                                              error={"code": code, "message": message}, retry=retry,
                                              received_at=st.get("received_at", ""), started_at=st.get("started_at", ""),
                                              order_sha=order_sha, extra=_project_extra(received_dir() / oid)))
    with _MOVE_LOCK:
        if final.exists():
            _retire(final)
        _move(part, final)
        _write_state(received_dir() / oid, {"finished": "failed", "attempts": 0})
    if code not in ("REJECTED_BY_OWNER", "STOPPED_BY_OWNER"):
        _notify(oid, order if isinstance(order, dict) else {}, False)


def _retire(folder: Path) -> None:
    """An answer folder taken back: first renamed to a hidden name (it disappears in one step for a program that
    watches Done / Failed), then deleted."""
    gone = folder.with_name(f".{folder.name}.retired.{int(time.time() * 1000)}")
    try:
        os.replace(folder, gone)
    except OSError:
        gone = folder
    shutil.rmtree(gone, ignore_errors=True)


def _project_extra(rdir: Path) -> dict | None:
    pid = _read_state(rdir).get("project_id")
    return {"project": {"id": int(pid), "url": f"http://127.0.0.1:{APP_PORT}/auto/p/{int(pid)}"}} if pid else None


def _notify(oid: str, order: dict, ok: bool) -> None:
    """A Windows notification when an order is finished and nothing else is waiting (a reel order's own
    "reel ready" notification is not repeated)."""
    try:
        from . import notify
        if not notify.enabled() or (ok and order.get("kind") == "reel_from_videos"):
            return
        if any(e["ready"] for e in inbox()) and auto_run():
            return
        ru = ae.ui_language() == "ru"
        title = ("Заказ готов" if ru else "Order done") if ok else ("Заказ не выполнен" if ru else "Order failed")
        text = (str(order.get("title") or oid)[:80]) + (" · нажми, чтобы открыть" if ru else " · click to open")
        threading.Thread(target=notify.show, args=(title, text, f"http://127.0.0.1:{APP_PORT}/auto/orders"),
                         daemon=True, name="notify").start()
    except Exception:
        pass


# ---------------------------------------------------------------- render_plan

X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high"]


def _run_ffmpeg(cmd: list[str], log: Path, timeout_s: float) -> None:
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        lf.write("\n$ " + " ".join(cmd) + "\n")
        lf.flush()
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                **process_kwargs(below_normal=True))
        ae._attach_job_object(proc)         # Windows: FFmpeg dies with the app (no orphan writing after a restart)
        _CURRENT["proc"] = proc
        t0 = time.time()
        try:
            while proc.poll() is None:
                if _stopped():
                    proc.kill(); proc.wait(30)
                    raise OrderError("STOPPED_BY_OWNER", "Stopped on the Orders page")
                if time.time() - t0 > timeout_s:
                    proc.kill(); proc.wait(30)
                    raise OrderError("RENDER_FAILED", "FFmpeg took too long")
                time.sleep(0.2)
        finally:
            _CURRENT["proc"] = None
            h = ae._JOB_HANDLES.pop(proc.pid, None)
            if h is not None:
                try:
                    import ctypes
                    from ctypes import wintypes
                    ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
                except Exception:
                    pass
    if _stopped():               # Stop killed FFmpeg itself (the loop above may not have seen the flag first)
        raise OrderError("STOPPED_BY_OWNER", "Stopped on the Orders page")
    if proc.returncode != 0:
        tail = ""
        try:
            tail = [x for x in log.read_text(encoding="utf-8", errors="replace").strip().splitlines() if x.strip()][-1][:200]
        except Exception:
            pass
        raise OrderError("RENDER_FAILED", "FFmpeg could not make the video (" + tail + ")")


def _render_plan(spec: dict, base: Path, work: Path) -> Path:
    """Every clip as a piece with exactly its number of frames (no drift over many clips), the pieces joined without
    re-encoding, then the sound (cut or filled with silence to the exact length). Pieces are MP4: the bundled FFmpeg
    7.0.2 build crashed reading MPEG-TS pieces back (found 2026-10-17)."""
    ff, w, h, fps = _ffmpeg(), spec["width"], spec["height"], spec["fps"]
    rate = f"{fps:.6f}".rstrip("0").rstrip(".")
    log = work / "render.log"
    pieces = []
    _CURRENT.update(total=len(spec["clips"]) + 1, done=0, step="clips")
    for c in spec["clips"]:
        out = work / f"piece_{c['n']:03d}.mp4"
        size = (f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
                if c["fit"] == "fit" else
                f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}")
        if "still" in c:
            cmd = [ff, "-hide_banner", "-nostdin", "-y", *_input_args(c["fmt"]), "-framerate", rate, "-stream_loop", "-1",
                   "-i", str(c["still"]), "-vf", f"{size},format=yuv420p,setsar=1"]
        else:
            cmd = [ff, "-hide_banner", "-nostdin", "-y", "-ss", f"{c['from_s']:.3f}", *_input_args(c["fmt"]), "-i", str(c["video"]),
                   "-vf", f"{size},fps={rate},tpad=stop_mode=clone:stop=-1,format=yuv420p,setsar=1"]
        cmd += ["-an", "-frames:v", str(c["frames"]), "-r", rate, *X264, "-g", str(max(1, int(round(fps * 2)))),
                "-f", "mp4", str(out)]
        _run_ffmpeg(cmd, log, 1800)
        pieces.append(out)
        _CURRENT["done"] += 1
    lst = work / "pieces.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in pieces), encoding="utf-8")
    final = work / "video.mp4"
    total = f"{spec['total_s']:.3f}"
    cmd = [ff, "-hide_banner", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if spec["audio"]:
        cmd += [*_input_args(spec["audio_fmt"]), "-i", str(spec["audio"])]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-ac", "2", "-t", total, "-movflags", "+faststart", str(final)]
    _CURRENT["step"] = "join"
    _run_ffmpeg(cmd, log, 1800)
    _CURRENT["done"] += 1
    return final


# ---------------------------------------------------------------- reel_from_videos

def _reel(spec: dict, rdir: Path) -> tuple[Path, dict, dict]:
    st = _read_state(rdir)
    pid = st.get("project_id")
    if not (pid and ae.project(int(pid))):
        title = spec["title"] or ("Order " + rdir.name)
        try:
            if spec["library_theme"]:
                from . import aiplus_library as al
                if not ae.aiplus_status()["ready"]:
                    raise OrderError("AIPLUS_NOT_READY", "The AI+ model is not on this PC yet: download it once on 'Check this PC'")
                files = al.reel_files(spec["library_theme"], ae.MAX_INPUTS)
                if not files:
                    raise OrderError("NO_VIDEOS", "No video of this theme is in the Library on this PC")
                pid = ae.create_project(None, title=title, files=files)
            elif spec["files"]:
                pid = ae.create_project(None, title=title, files=[str(x) for x in spec["files"]])
            else:
                pid = ae.create_project(str(spec["folder"]), title=title)
        except ValueError as exc:
            raise OrderError("VIDEOS_NOT_USABLE", str(exc))
        _write_state(rdir, {"project_id": int(pid)})
    _CURRENT.update(step="reel", total=100, done=0)
    try:
        jid = ae.start_job(int(pid), spec["settings"])
    except ValueError as exc:
        raise OrderError("REEL_NOT_STARTED", str(exc))
    _write_state(rdir, {"job_id": int(jid)})
    while True:
        j = ae.job(jid) or {"status": "failed", "error": "The reel build disappeared"}
        _CURRENT["done"] = int(j.get("percent") or 0)
        if j["status"] == "done":
            break
        if j["status"] == "failed":
            raise OrderError("REEL_FAILED", str(j.get("error") or "The reel could not be built"))
        if j["status"] == "cancelled":
            raise OrderError("STOPPED_BY_OWNER", "The reel was cancelled")
        if _STOP_ALL.is_set() and not _CURRENT["stop"].is_set():
            raise OrderError("STOPPED_BY_OWNER", "The app is closing")     # no answer: done again at the next start
        if _CURRENT["stop"].is_set():
            ae.cancel_job(jid)
            for _ in range(120):
                if (ae.job(jid) or {}).get("status") not in ("queued", "running"):
                    break
                time.sleep(0.5)
            raise OrderError("STOPPED_BY_OWNER", "Stopped on the Orders page")
        time.sleep(1.0)
    rev = ae.revision(int(j["revision_id"]))
    if not rev or not Path(rev["video_path"]).is_file():
        raise OrderError("REEL_FAILED", "The finished reel file is missing")
    size = ae.FORMATS[spec["settings"]["format"]].get("size")
    used = sorted({str(sg.get("source_name")) for sg in (rev.get("result") or {}).get("segments") or [] if sg.get("source_name")})
    extra = {"project": {"id": int(pid), "url": f"http://127.0.0.1:{APP_PORT}/auto/p/{int(pid)}", "version": int(rev["number"])},
             "settings": spec["settings"], "videos_used": used, "moments": len((rev.get("result") or {}).get("segments") or []),
             # the reel's names (a second DJI_0001.MP4 is "DJI_0001 (2).MP4") with each video's SHA-256
             "inputs": [{"name": x.get("name"), "sha256": x.get("sha256")} for x in (rev.get("result") or {}).get("inputs") or []],
             **({"videos_left_out": spec["left_out"]} if spec.get("left_out") else {})}
    want = {"width": size[0] if size else int(rev.get("width") or 0), "height": size[1] if size else int(rev.get("height") or 0),
            "seconds": float(rev.get("duration_s") or 0), "tolerance": 0.15, "sha256": rev["video_sha256"]}
    return Path(rev["video_path"]), extra, want


# ---------------------------------------------------------------- the finished file is checked, not trusted

def _check_output(path: Path, want: dict) -> list[dict]:
    checks = []
    try:
        info = ae._probe(path)
    except Exception as exc:
        return [{"check": "readable", "pass": False, "detail": str(exc)[:200]}]
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(info.get("format", {}).get("duration") or 0)
    checks.append({"check": "video", "pass": bool(v and v.get("codec_name") == "h264"),
                   "detail": (v or {}).get("codec_name", "no video")})
    if want.get("width"):
        got = f"{(v or {}).get('width')}x{(v or {}).get('height')}"
        checks.append({"check": "size", "pass": got == f"{want['width']}x{want['height']}", "detail": got})
    if want.get("seconds"):
        checks.append({"check": "length", "pass": abs(dur - want["seconds"]) <= want.get("tolerance", 0.1),
                       "detail": f"{dur:.3f} s (planned {want['seconds']:.3f} s)"})
    if want.get("audio"):
        checks.append({"check": "sound", "pass": a is not None, "detail": (a or {}).get("codec_name", "no sound track")})
    if want.get("sha256"):
        checks.append({"check": "same_as_reel", "pass": _sha(path) == want["sha256"], "detail": "SHA-256 of the project's version"})
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-i", str(path), "-f", "null", "-"]
    try:
        cp = subprocess.run(cmd, **process_kwargs(dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                                        errors="replace", timeout=1800, check=False)))
        errs = [x for x in (cp.stderr or "").splitlines() if x.strip()]
        checks.append({"check": "plays_to_the_end", "pass": cp.returncode == 0 and not errs,
                       "detail": "decoded completely" if cp.returncode == 0 and not errs else (errs[-1:] or ["decode failed"])[0][:200]})
    except subprocess.TimeoutExpired:
        checks.append({"check": "plays_to_the_end", "pass": False, "detail": "decoding took too long"})
    return checks


# ---------------------------------------------------------------- what is waiting, running, finished

def unfinished() -> list[str]:
    """Received orders without an answer yet (being done now, or interrupted by a restart: done again)."""
    out = []
    try:
        for d in sorted(received_dir().iterdir(), key=lambda p: p.stat().st_mtime):
            if d.is_dir() and not d.name.startswith(".") and not (done_dir() / d.name).exists() and not (failed_dir() / d.name).exists():
                if _read_state(d).get("finished"):      # answered (the program moved its answer away): never again
                    continue
                out.append(d.name)
    except OSError:
        pass
    return out


def stuck(oid: str) -> bool:
    """Started MAX_ATTEMPTS times without an answer (the app was closed or crashed each time): not started again
    by itself - the owner presses Try again or Delete."""
    return _CURRENT.get("id") != oid and int(_read_state(received_dir() / oid).get("attempts") or 0) >= MAX_ATTEMPTS


def busy() -> str:
    """The order being done now ('' when none): Quit / Restart / switching builds ask first."""
    return str(_CURRENT.get("id") or "")


def _next() -> tuple[str, Path] | None:
    left = [x for x in unfinished() if not stuck(x)]
    if left:
        return left[0], received_dir() / left[0]
    go = auto_run()
    now = time.time()
    for entry in inbox():
        if entry["ready"] and (go or entry["id"] in _RUN_NOW) and _BACKOFF.get(entry["id"], 0) <= now:
            try:
                oid, rdir = _take(entry)
            except OSError:               # Windows cannot move it now (a file open in it): the others go first
                _BACKOFF[entry["id"]] = now + 30
                continue
            _RUN_NOW.discard(entry["id"])
            _BACKOFF.pop(entry["id"], None)
            if rdir is None:
                continue                  # refused at once (bad / used id): its answer is in Failed
            return oid, rdir
    return None


def process_next() -> str | None:
    """Do the next order (if any). Returns its id, or None when nothing is to be done."""
    if not _LOCK.acquire(blocking=False):
        return None
    try:
        ensure_dirs()
        with _MOVE_LOCK:
            nxt = _next()
        if not nxt:
            return None
        _process(nxt[0])
        return nxt[0]
    finally:
        _LOCK.release()


def _loop() -> None:
    while not _STOP_ALL.is_set():
        try:
            if process_next():
                continue
        except Exception:
            time.sleep(POLL_S)
        _WAKE.wait(POLL_S)
        _WAKE.clear()


def start() -> None:
    """Start watching the Inbox (once per app process; daemon: stops with the app)."""
    with _STATE_LOCK:
        t = _WATCHER["thread"]
        if t is not None and t.is_alive():
            return
        _STOP_ALL.clear()
        t = threading.Thread(target=_loop, name="orders-watcher", daemon=True)
        _WATCHER["thread"] = t
        t.start()


def shutdown() -> None:
    _STOP_ALL.set()
    _WAKE.set()
    p = _CURRENT.get("proc")
    if p is not None:
        try:
            p.kill()
        except Exception:
            pass


# ---------------------------------------------------------------- owner's buttons

def run_now(oid: str) -> None:
    _RUN_NOW.add(str(oid))
    _WAKE.set()


def reject(oid: str) -> bool:
    """A waiting order the owner does not want: answered in Failed (REJECTED_BY_OWNER), never done."""
    with _MOVE_LOCK:
        entry = next((x for x in inbox() if x["id"] == oid), None)
        if not entry:
            return False
        _RUN_NOW.discard(oid)
        try:
            oid2, rdir = _take(entry)
        except OSError:
            return False
        if rdir is None:
            return True
        _write_state(rdir, {"finished": "rejected"})       # never done, even if writing the answer fails
        order = {}
        try:
            order = _read_json(rdir / "order.json")
        except OrderError:
            pass
        _publish_failed(oid2, order if isinstance(order, dict) else {}, "", "REJECTED_BY_OWNER",
                        "The owner rejected this order on the Orders page", _read_state(rdir), retry=False)
        return True


def stop(oid: str) -> bool:
    with _CUR_LOCK:
        if _CURRENT.get("id") != oid:
            return False
        _CURRENT["stop"].set()
        p = _CURRENT.get("proc")
    if p is not None:
        try:
            p.kill()
        except Exception:
            pass
    return True


def retry(oid: str) -> bool:
    """A failed (or stuck) order is done again (its files are still in Received)."""
    with _MOVE_LOCK:
        if oid in unfinished() and stuck(oid):
            _write_state(received_dir() / oid, {"attempts": 0, "retried_at": now_iso()})
            _WAKE.set()
            return True
        f = failed_dir() / oid
        if not f.is_dir() or not (received_dir() / oid).is_dir():
            return False
        try:
            if json.loads((f / "result.json").read_text(encoding="utf-8")).get("can_retry") is False:
                return False
        except Exception:
            pass
        _retire(f)
        _write_state(received_dir() / oid, {"finished": None, "attempts": 0, "retried_at": now_iso()})
    _WAKE.set()
    return True


def delete(oid: str) -> bool:
    """Forget a finished order: its folders in Orders (never the owner's videos elsewhere, never a project)."""
    with _MOVE_LOCK:
        if not oid or "/" in oid or "\\" in oid or oid in (".", "..") or busy() == oid:
            return False
        if oid in unfinished() and not stuck(oid):
            return False
        gone = False
        for d in (received_dir(), done_dir(), failed_dir()):
            p = d / oid
            if p.is_dir() and p.resolve().parent == d.resolve():
                shutil.rmtree(p, ignore_errors=True)
                gone = True
        if gone:
            try:
                _state_file(received_dir() / oid).unlink(missing_ok=True)
            except OSError:
                pass
        return gone


def overview(limit: int = 100) -> dict:
    """Everything for the Orders page / API."""
    ensure_dirs()
    items = []
    for entry in inbox():
        o = _peek(entry)
        items.append({"id": entry["id"], "state": "new" if entry["ready"] else "arriving", "kind": o.get("kind"),
                      "from": str(o.get("from") or "")[:60], "title": str(o.get("title") or "")[:80],
                      "waiting_for": entry["waiting_for"], "time": entry["mtime"]})
    for oid in unfinished():
        rdir = received_dir() / oid
        st = _read_state(rdir)
        cur = _CURRENT.get("id") == oid
        prog = ""
        if cur and _CURRENT.get("step") == "reel":
            prog = f"{_CURRENT.get('done', 0)}%"
        elif cur and _CURRENT.get("total"):
            prog = f"{_CURRENT.get('done', 0)}/{_CURRENT.get('total', 0)}"
        it = {"id": oid, "state": "working" if cur else "waiting", "kind": st.get("kind"), "from": st.get("from") or "",
              "title": st.get("title") or "", "progress": prog, "project_id": st.get("project_id"), "time": _mtime(rdir)}
        if not cur and stuck(oid):
            it.update(state="stuck", can_retry=True, finished_at=st.get("started_at"),
                      error={"code": "INTERRUPTED", "message": f"Started {st.get('attempts')} times without finishing "
                                                               "(MediaEngine was closed or stopped each time)"})
        items.append(it)
    try:          # answered, and the program took its answer away: listed (with Delete) so its files can go
        for d in received_dir().iterdir():
            if (d.is_dir() and not d.name.startswith(".") and not (done_dir() / d.name).exists()
                    and not (failed_dir() / d.name).exists()):
                st = _read_state(d)
                if st.get("finished"):
                    items.append({"id": d.name, "state": "taken", "kind": st.get("kind"), "from": st.get("from") or "",
                                  "title": st.get("title") or "", "answer": st.get("finished"), "project_id": st.get("project_id"),
                                  "time": _mtime(d)})
    except OSError:
        pass
    for state, d in (("done", done_dir()), ("failed", failed_dir())):
        try:
            dirs = sorted((p for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")), key=_mtime, reverse=True)[:limit]
        except OSError:
            dirs = []
        for p in dirs:
            try:
                r = json.loads((p / "result.json").read_text(encoding="utf-8"))
            except Exception:
                r = {}
            items.append({"id": p.name, "state": state, "kind": r.get("kind"), "from": r.get("from") or "", "title": r.get("title") or "",
                          "video": r.get("video"), "error": r.get("error"), "can_retry": r.get("can_retry", True) and (received_dir() / p.name).is_dir(),
                          "project_id": (r.get("project") or {}).get("id"), "finished_at": r.get("finished_at"),
                          "checks": r.get("checks"), "time": _mtime(p)})
    order = {"working": 0, "waiting": 1, "new": 2, "arriving": 3, "stuck": 4, "failed": 4, "done": 4, "taken": 5}
    items.sort(key=lambda x: (order.get(x["state"], 9), -float(x.get("time") or 0)))
    return {"auto_run": auto_run(), "inbox": str(inbox_dir()), "root": str(root()), "items": items,
            "counts": {s: sum(1 for x in items if x["state"] == s) for s in ("new", "arriving", "working", "waiting", "stuck", "done", "failed", "taken")}}


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def result_video(oid: str) -> Path | None:
    p = done_dir() / oid / "video.mp4"
    return p if valid_id(oid) and p.is_file() else None


def order_folder(oid: str) -> Path | None:
    for d in (done_dir(), failed_dir(), received_dir()):
        p = d / oid
        if p.is_dir() and p.resolve().parent == d.resolve():
            return p
    return None

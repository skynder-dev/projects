from __future__ import annotations
from .platform_adapter import process_kwargs

import io
import os
import hashlib
import re
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps


def _run(*args, **kwargs):
    return subprocess.run(*args, **process_kwargs(kwargs))

def find_adb() -> str | None:
    p = shutil.which("adb")
    if p:
        return p
    if os.name != "nt":
        return None
    candidates = []
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if local:
        candidates.extend([
            local / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            local / "Microsoft" / "WinGet" / "Links" / "adb.exe",
        ])
        pkgroot = local / "Microsoft" / "WinGet" / "Packages"
        if pkgroot.exists():
            try:
                for pkg in pkgroot.glob("Google.PlatformTools*"):
                    candidates.extend(pkg.rglob("adb.exe"))
            except Exception:
                pass
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


_device_cache_lock = threading.Lock()
_device_cache = {"at": 0.0, "devices": [], "error": None, "adb": None}

def adb_devices(adb: str | None = None, refresh: bool = False) -> tuple[list[dict], str | None]:
    adb = adb or find_adb()
    now = time.time()
    with _device_cache_lock:
        if not refresh and adb and _device_cache["adb"] == adb and now - _device_cache["at"] < 4.0:
            return list(_device_cache["devices"]), _device_cache["error"]
    if not adb:
        return [], "ADB not installed"
    try:
        _run([adb, "start-server"], capture_output=True, timeout=20)
        r = _run([adb, "devices", "-l"], capture_output=True, text=True, timeout=20, errors="replace")
        devices = []
        for line in r.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            meta = {}
            for token in parts[2:]:
                if ":" in token:
                    k, v = token.split(":", 1)
                    meta[k] = v
            devices.append({
                "serial": serial,
                "state": state,
                "model": meta.get("model", ""),
                "product": meta.get("product", ""),
            })
        err = r.stderr.strip() or None
        with _device_cache_lock:
            _device_cache.update({"at": time.time(), "devices": list(devices), "error": err, "adb": adb})
        return devices, err
    except Exception as e:
        err = str(e)
        with _device_cache_lock:
            _device_cache.update({"at": time.time(), "devices": [], "error": err, "adb": adb})
        return [], err


_KEY_RE = re.compile(r"(?:^|, )([A-Za-z0-9_]+)=")


def parse_content_rows(text: str) -> list[dict]:
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("Row:"):
            continue
        # Drop "Row: N " prefix.
        m = re.match(r"Row:\s*\d+\s+(.*)$", line)
        if not m:
            continue
        body = m.group(1)
        matches = list(_KEY_RE.finditer(body))
        row = {}
        for i, mm in enumerate(matches):
            key = mm.group(1)
            start = mm.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            val = body[start:end].strip()
            if val.endswith(","):
                val = val[:-1].rstrip()
            row[key] = None if val in {"NULL", "null", "None"} else val
        if row:
            rows.append(row)
    return rows


def _content_query(adb: str, serial: str, uri: str, projections: list[list[str]], timeout: int = 180) -> tuple[list[dict], str | None]:
    last_err = None
    for columns in projections:
        try:
            args = [adb, "-s", serial, "shell", "content", "query", "--uri", uri, "--projection", ":".join(columns)]
            r = _run(args, capture_output=True, text=True, timeout=timeout, errors="replace")
            # Error banners start a line; a media file or folder merely named "...Exception..." must not fail the listing.
            failed_banner = any(ln.lstrip().startswith(("Error while accessing provider", "java.lang.", "Exception")) for ln in (r.stdout or "").splitlines()[:5])
            if r.returncode == 0 and not failed_banner:
                return parse_content_rows(r.stdout), None
            last_err = (r.stderr or r.stdout).strip()[-1000:]
        except Exception as e:
            last_err = str(e)
    return [], last_err


def _int(v):
    try:
        return int(v) if v not in (None, "") else None
    except Exception:
        return None

def _nonneg_int(v):
    x = _int(v)
    return x if x is not None and x >= 0 else None


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def _remote_path(row: dict) -> str | None:
    p = row.get("_data") or row.get("data")
    if p:
        return p
    rel = row.get("relative_path") or ""
    name = row.get("_display_name") or row.get("display_name")
    if name:
        return "/storage/emulated/0/" + rel.lstrip("/") + name
    return None


def _thumb_map(adb: str, serial: str, media_type: str) -> dict[str, dict]:
    if media_type == "video":
        uri = "content://media/external/video/thumbnails"
        link_col = "video_id"
    else:
        uri = "content://media/external/images/thumbnails"
        link_col = "image_id"
    rows, _ = _content_query(adb, serial, uri, [["_id", link_col, "_data", "width", "height"], ["_id", link_col, "_data"], ["_id", link_col]], 120)
    out = {}
    for r in rows:
        link = r.get(link_col)
        tid = r.get("_id")
        if not link or not tid:
            continue
        out[str(link)] = {
            "thumb_uri": f"{uri}/{tid}",
            "thumb_path": r.get("_data"),
        }
    return out


def list_media(adb: str, serial: str) -> tuple[list[dict], list[str]]:
    """Use Android MediaStore instead of crawling /sdcard.

    This gives metadata without downloading files and avoids app/game artwork.
    """
    errors = []
    result = []
    specs = [
        ("video", "content://media/external/video/media"),
        ("image", "content://media/external/images/media"),
    ]
    for media_type, uri in specs:
        if media_type == "video":
            rich = ["_id", "_data", "_display_name", "_size", "date_modified", "datetaken", "duration", "width", "height", "mime_type", "relative_path"]
            basic = ["_id", "_data", "_display_name", "_size", "date_modified", "duration", "mime_type"]
        else:
            rich = ["_id", "_data", "_display_name", "_size", "date_modified", "datetaken", "width", "height", "mime_type", "relative_path"]
            basic = ["_id", "_data", "_display_name", "_size", "date_modified", "mime_type"]
        rows, err = _content_query(adb, serial, uri, [rich, basic, ["_id", "_display_name", "_size", "date_modified", "duration", "mime_type", "relative_path"] if media_type == "video" else ["_id", "_display_name", "_size", "date_modified", "mime_type", "relative_path"], ["_id", "_data", "_display_name", "_size"], ["_id", "_display_name", "_size"]], 240)
        if err and not rows:
            errors.append(f"{media_type}: {err}")
        # Do not enumerate the entire legacy thumbnail table during Discover.
        # Modern thumbnails are requested lazily per visible item by the single preview worker.
        tmap = {}
        for r in rows:
            mid = str(r.get("_id") or "")
            if not mid:
                continue
            path = _remote_path(r)
            name = r.get("_display_name") or (Path(path).name if path else f"{media_type}_{mid}")
            size = _nonneg_int(r.get("_size"))
            mtime = _float(r.get("date_modified"))
            date_taken = _float(r.get("datetaken") or r.get("date_taken"))
            if date_taken and date_taken > 10_000_000_000:
                date_taken /= 1000.0
            thumb = tmap.get(mid, {})
            result.append({
                "media_type": media_type,
                "media_id": mid,
                "path": path,
                "content_uri": f"{uri}/{mid}",
                "filename": name,
                "ext": Path(name).suffix.lower(),
                "mime_type": r.get("mime_type"),
                "size_bytes": size,
                "mtime": mtime,
                "date_taken": date_taken,
                "duration_ms": _nonneg_int(r.get("duration")),
                "width": _nonneg_int(r.get("width")),
                "height": _nonneg_int(r.get("height")),
                "remote_thumb_uri": thumb.get("thumb_uri"),
                "remote_thumb_path": thumb.get("thumb_path"),
            })
    if not result:
        # Compatibility fallback for devices that block MediaStore queries from adb shell.
        # One shell process gathers size + mtime; no media bytes are copied.
        try:
            cmd = r"""find /sdcard -type f 2>/dev/null | while IFS= read -r f; do case "${f##*.}" in mp4|MP4|mov|MOV|mkv|MKV|avi|AVI|webm|WEBM|m4v|M4V|3gp|3GP|mts|MTS|m2ts|M2TS|wmv|WMV|mpg|MPG|mpeg|MPEG|jpg|JPG|jpeg|JPEG|png|PNG|webp|WEBP|heic|HEIC|heif|HEIF) toybox stat -c '%s\t%Y\t%n' "$f" 2>/dev/null ;; esac; done"""
            r = _run([adb, "-s", serial, "shell", cmd], capture_output=True, text=True, timeout=300, errors="replace", stdin=subprocess.DEVNULL)
            for line in r.stdout.splitlines():
                parts = line.rstrip('\r').split('\t', 2)
                if len(parts) != 3:
                    continue
                size_s, mtime_s, path = parts
                low = path.lower()
                if any(x in low for x in ('/android/data/', '/android/obb/', '/.thumbnails/', '/cache/', '/caches/')):
                    continue
                ext = Path(path).suffix.lower()
                media_type = 'video' if ext in {'.mp4','.mov','.mkv','.avi','.webm','.m4v','.3gp','.mts','.m2ts','.wmv','.mpg','.mpeg'} else 'image'
                pseudo = 'path-' + hashlib.sha1(path.encode('utf-8','ignore')).hexdigest()[:16]
                result.append({
                    'media_type': media_type, 'media_id': pseudo, 'path': path, 'content_uri': None,
                    'filename': Path(path).name, 'ext': ext, 'mime_type': None,
                    'size_bytes': _nonneg_int(size_s), 'mtime': _float(mtime_s), 'date_taken': None,
                    'duration_ms': None, 'width': None, 'height': None,
                    'remote_thumb_uri': None, 'remote_thumb_path': None,
                })
            if result:
                errors.append('MediaStore unavailable; used filesystem compatibility mode')
        except Exception as exc:
            errors.append(f'fallback: {exc}')
    return result, errors


def _save_image_bytes_as_jpg(data: bytes, dest: Path, max_size=(480, 360)) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail(max_size)
            dest.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest, "JPEG", quality=82)
        return True
    except Exception:
        return False


def _legacy_thumb_for_item(adb: str, serial: str, media_type: str, media_id: str | None) -> tuple[str | None, str | None]:
    if not media_id:
        return None, None
    if media_type == "video":
        uri, link_col = "content://media/external/video/thumbnails", "video_id"
    else:
        uri, link_col = "content://media/external/images/thumbnails", "image_id"
    try:
        r = _run([adb, "-s", serial, "shell", "content", "query", "--uri", uri,
                  "--projection", "_id:_data", "--where", f"{link_col}={media_id}"],
                 capture_output=True, text=True, timeout=30, errors="replace")
        rows = parse_content_rows(r.stdout or "")
        if rows:
            tid = rows[0].get("_id")
            path = rows[0].get("_data")
            return (f"{uri}/{tid}" if tid else None), path
    except Exception:
        pass
    return None, None


def fetch_thumbnail(adb: str, serial: str, item: dict, dest: Path) -> bool:
    """Fetch only a small Android-generated thumbnail when possible.

    Modern Android (API 29+) no longer reliably exposes the legacy thumbnails
    table. MediaProvider still exposes the per-item /thumbnail URI used by
    ContentResolver.loadThumbnail(), so ask the provider for that first.

    For images, the final fallback reads the original only when it is reasonably
    small. Full videos are never pulled by this function.
    """
    # Modern MediaProvider path. Opening this URI asks Android to generate/cache
    # a thumbnail on-device instead of sending the original video to the PC.
    content_uri = item.get("content_uri")
    if content_uri:
        direct_thumb_uri = content_uri.rstrip("/") + "/thumbnail"
        try:
            r = _run(
                [adb, "-s", serial, "exec-out", "content", "read", "--uri", direct_thumb_uri],
                capture_output=True, timeout=90,
            )
            if r.returncode == 0 and len(r.stdout) > 100 and _save_image_bytes_as_jpg(r.stdout, dest):
                return True
        except Exception:
            pass

    # Legacy thumbnail table fallback for older/vendor Android builds, queried
    # only for this visible item instead of scanning the whole table at Discover.
    uri = item.get("remote_thumb_uri")
    remote_thumb = item.get("remote_thumb_path")
    if not uri and not remote_thumb:
        uri, remote_thumb = _legacy_thumb_for_item(adb, serial, item.get("media_type") or "video", item.get("media_id"))
    if uri:
        try:
            r = _run([adb, "-s", serial, "exec-out", "content", "read", "--uri", uri], capture_output=True, timeout=60)
            if r.returncode == 0 and len(r.stdout) > 100 and _save_image_bytes_as_jpg(r.stdout, dest):
                return True
        except Exception:
            pass
    if remote_thumb:
        tmp = dest.with_suffix(".remote")
        try:
            r = _run([adb, "-s", serial, "pull", remote_thumb, str(tmp)], capture_output=True, timeout=60)
            if r.returncode == 0 and tmp.exists():
                data = tmp.read_bytes()
                ok = _save_image_bytes_as_jpg(data, dest)
                tmp.unlink(missing_ok=True)
                if ok:
                    return True
        except Exception:
            tmp.unlink(missing_ok=True)
    if item.get("media_type") == "image" and item.get("content_uri") and (item.get("size_bytes") or 0) <= 25 * 1024 * 1024:
        try:
            r = _run([adb, "-s", serial, "exec-out", "content", "read", "--uri", item["content_uri"]], capture_output=True, timeout=90)
            if r.returncode == 0 and len(r.stdout) > 100 and _save_image_bytes_as_jpg(r.stdout, dest):
                return True
        except Exception:
            pass
    return False


def pull_original(adb: str, serial: str, remote_path: str | None, content_uri: str | None, dest: Path, timeout=3600) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if remote_path:
        try:
            r = _run([adb, "-s", serial, "pull", remote_path, str(dest)], capture_output=True, timeout=timeout)
            if r.returncode == 0 and dest.exists():
                return True
        except Exception:
            pass
    if content_uri:
        try:
            with dest.open("wb") as f:
                r = _run([adb, "-s", serial, "exec-out", "content", "read", "--uri", content_uri], stdout=f, stderr=subprocess.PIPE, timeout=timeout)
            if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                return True
        except Exception:
            pass
    dest.unlink(missing_ok=True)
    return False


def remote_sha256(adb: str, serial: str, remote_path: str | None) -> str | None:
    if not remote_path:
        return None
    q = shlex.quote(remote_path)
    cmd = f"sha256sum {q} 2>/dev/null || toybox sha256sum {q} 2>/dev/null"
    try:
        # adb joins extra arguments with spaces WITHOUT quoting, so "sh -c <cmd>" would run
        # sha256sum on stdin. Pass the whole command as one string to the device shell.
        r = _run([adb, "-s", serial, "shell", cmd], capture_output=True, text=True, timeout=600, errors="replace", stdin=subprocess.DEVNULL)
        m = re.search(r"\b([0-9a-fA-F]{64})\b", r.stdout)
        return m.group(1).lower() if m else None
    except Exception:
        return None


def _popen_hidden(args, **kwargs):
    return subprocess.Popen(args, **process_kwargs(kwargs))

def pull_original_progress(adb: str, serial: str, remote_path: str | None, content_uri: str | None,
                           dest: Path, progress_cb=None, timeout: int = 7200, cancel_cb=None) -> tuple[bool, str | None]:
    """Copy one Android original while reporting destination-file growth.

    Uses adb pull first because it is the most compatible path for normal DCIM/Movies files.
    Falls back to MediaStore content read if the raw path is unavailable.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    started = time.time()

    def monitor(proc):
        while proc.poll() is None:
            if cancel_cb and cancel_cb():
                try: proc.kill()
                except Exception: pass
                return "cancelled"
            if timeout and time.time() - started > timeout:
                try: proc.kill()
                except Exception: pass
                return "timeout"
            try:
                if progress_cb:
                    progress_cb(dest.stat().st_size if dest.exists() else 0)
            except Exception:
                pass
            time.sleep(0.35)
        try:
            if progress_cb:
                progress_cb(dest.stat().st_size if dest.exists() else 0)
        except Exception:
            pass
        return None

    errors = []
    if remote_path:
        try:
            proc = _popen_hidden([adb, "-s", serial, "pull", remote_path, str(dest)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            timed = monitor(proc)
            out, err = proc.communicate(timeout=5)
            if timed == "cancelled":
                errors.append("cancelled")
            elif timed == "timeout":
                errors.append("adb pull timeout")
            elif proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                return True, None
            else:
                msg = (err or out or b"").decode("utf-8", "replace")[-700:]
                errors.append(msg.strip() or f"adb pull exit {proc.returncode}")
        except Exception as exc:
            errors.append(f"adb pull: {exc}")
        dest.unlink(missing_ok=True)

    if content_uri:
        try:
            with dest.open("wb") as f:
                proc = _popen_hidden([adb, "-s", serial, "exec-out", "content", "read", "--uri", content_uri],
                                     stdout=f, stderr=subprocess.PIPE)
                timed = monitor(proc)
                _, err = proc.communicate(timeout=5)
            if timed == "cancelled":
                errors.append("cancelled")
            elif timed == "timeout":
                errors.append("MediaStore read timeout")
            elif proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                return True, None
            else:
                msg = (err or b"").decode("utf-8", "replace")[-700:]
                errors.append(msg.strip() or f"MediaStore read exit {proc.returncode}")
        except Exception as exc:
            errors.append(f"MediaStore read: {exc}")

    dest.unlink(missing_ok=True)
    return False, " | ".join(e for e in errors if e) or "Android copy failed"

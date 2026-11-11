"""Shared helpers: hashing, stable JSON, dates, paths."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # social/
ASSETS = ROOT / "assets"
CONTRACT = "SOCIAL_REAL_REELS_V1"
PACKAGE_SCHEMA = "social_reel_package_v1"


class PipelineError(RuntimeError):
    """A stage could not produce a valid result. Never swallowed into fake success."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_json(p: Path, obj) -> str:
    """Write deterministic JSON and return its sha256."""
    p.parent.mkdir(parents=True, exist_ok=True)
    data = stable_json(obj).encode("utf-8")
    atomic_bytes(p, data)
    return sha256_bytes(data)


def write_text(p: Path, text: str) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    atomic_bytes(p, data)
    return sha256_bytes(data)


def read_json(p: Path | str):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def utc_now() -> dt.datetime:
    fixed = os.environ.get("SOCIAL_FIXED_NOW")  # deterministic tests / re-runs
    if fixed:
        return dt.datetime.fromisoformat(fixed).astimezone(dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
_MON3 = {k[:3]: v for k, v in _MONTHS.items()}


def parse_date(value) -> dt.date | None:
    """Parse the date formats Grants.gov is known to use. Returns None if unsure."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return _safe_date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return _safe_date(int(m[3]), int(m[1]), int(m[2]))
    m = re.match(r"^(\d{2})(\d{2})(\d{4})$", s)          # MMDDYYYY
    if m:
        return _safe_date(int(m[3]), int(m[1]), int(m[2]))
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", s)  # Nov 17, 2026 ...
    if m and m[1][:3].lower() in _MON3:
        return _safe_date(int(m[3]), _MON3[m[1][:3].lower()], int(m[2]))
    return None


def _safe_date(y: int, mo: int, d: int) -> dt.date | None:
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def human_date(d: dt.date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def money(n) -> str:
    """Exact source amount; use a short unit only when it preserves every cent."""
    from decimal import Decimal, InvalidOperation
    try:
        value = Decimal(str(n))
    except InvalidOperation as e:
        raise PipelineError('Invalid source amount') from e
    if not value.is_finite():
        raise PipelineError('Non-finite source amount')
    for unit, label in ((Decimal(1000000000), 'billion'), (Decimal(1000000), 'million')):
        short = value / unit
        if value >= unit and short.quantize(Decimal('.01')) * unit == value:
            text = format(short.quantize(Decimal('.01')), 'f').rstrip('0').rstrip('.')
            return f'${text} {label}'
    if value == value.to_integral_value():
        return f'${int(value):,}'
    decimals = max(2, -value.as_tuple().exponent)
    return '${:,.{}f}'.format(value, decimals)


def slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:n].strip("-") or "x"


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    import html
    # Grants.gov can return twice-encoded entities. Bound normalization and remove
    # markup after each decode so encoded script/style content never becomes text.
    for _ in range(4):
        before=s
        s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
        s = re.sub(r"(?i)<br\s*/?>|</p>|</li>", " ", s)
        s = re.sub(r"<[^>]+>", " ", s)
        s = html.unescape(s)
        if s==before:break
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Runtime downloads are forbidden; model installation is a separate preparation step.
RUNTIME_PATHS={};RUNTIME_PATHS_ERROR=None
_runtime_file=Path(os.environ.get('SOCIAL_RUNTIME_PATHS',str(ROOT/'runtime-paths.json')))
try:
    if _runtime_file.exists():
        RUNTIME_PATHS=read_json(_runtime_file)
        if not isinstance(RUNTIME_PATHS,dict):raise ValueError('Runtime paths must be an object')
except (OSError,ValueError) as error:RUNTIME_PATHS_ERROR=type(error).__name__+': '+str(error)
AI_HOME = Path(os.environ.get('SOCIAL_AI_HOME', RUNTIME_PATHS.get('ai_home','CI_UNCONFIGURED/runtime-0')))
os.environ.setdefault('HF_HOME',str(AI_HOME/'hf-cache'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ.setdefault('SOCIAL_VOICE_CACHE',str(AI_HOME/'audio-cache'))
if os.name=='nt' and not any(n in RUNTIME_PATHS for n in ('ffmpeg','ffprobe')):
    bins=list((AI_HOME/'ffmpeg').glob('*/bin/ffmpeg.exe'))
    if bins:os.environ['PATH']=str(bins[0].parent)+os.pathsep+os.environ.get('PATH','')

def resolve_tool(name):
    import shutil
    if RUNTIME_PATHS_ERROR:raise PipelineError('Runtime path configuration unavailable: '+RUNTIME_PATHS_ERROR)
    if name in RUNTIME_PATHS:
        value=Path(RUNTIME_PATHS[name]);value=value if value.is_absolute() else ROOT/value
        return str(value.resolve()) if value.is_file() else None
    return shutil.which(name)

def check_cancel():
    marker = os.environ.get("SOCIAL_CANCEL_FILE")
    if marker and Path(marker).is_file():
        raise PipelineError("Social run cancelled")

HIDDEN_PROCESS = {"creationflags": 0x08000000} if os.name == "nt" else {}


def atomic_bytes(path, data):
    """Readers see the previous complete file or the next complete file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers may briefly deny DELETE sharing on the old JSON file.
        # Retry only known sharing/access races, with a bounded1.26s wait; never bypass ACLs.
        import time
        for attempt,delay in enumerate((.02,.04,.08,.16,.32,.64,0)):
            try:os.replace(name,path);break
            except PermissionError as error:
                if os.name!='nt' or getattr(error,'winerror',None) not in (5,32,33) or delay==0:raise
                time.sleep(delay)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def progress(stage, run_dir=None, **details):
    check_cancel()
    path = os.environ.get("SOCIAL_PROGRESS_FILE")
    if path:
        write_json(Path(path), {"stage": stage, "updated_at": utc_now().isoformat(),
                                "run_dir": str(run_dir) if run_dir else None, **details})

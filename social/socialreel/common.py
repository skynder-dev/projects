"""Shared helpers: hashing, stable JSON, dates, paths."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
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
    p.write_bytes(data)
    return sha256_bytes(data)


def write_text(p: Path, text: str) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    p.write_bytes(data)
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


def money(n: float) -> str:
    """$650,000 / $24.75 million / $1.2 billion — exact, never rounded away."""
    n = float(n)
    if n >= 1_000_000_000 and _exact(n, 1_000_000_000):
        return f"${_trim(n / 1_000_000_000)} billion"
    if n >= 1_000_000 and _exact(n, 1_000_000):
        return f"${_trim(n / 1_000_000)} million"
    if n == int(n):
        return f"${int(n):,}"
    return f"${n:,.2f}"


def _exact(n: float, unit: int) -> bool:
    # representable with at most 2 decimals in that unit
    return abs(round(n / unit, 2) * unit - n) < 0.5


def _trim(x: float) -> str:
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s


def slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:n].strip("-") or "x"


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", s).strip()

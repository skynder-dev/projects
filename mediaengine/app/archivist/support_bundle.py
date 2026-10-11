from __future__ import annotations

import json
import os
import platform
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA, LOGS, VERSION

SUPPORT_DIR = DATA / "support"
MAX_LOG_INPUT_BYTES = 128 * 1024
MAX_LOG_OUTPUT_BYTES = 64 * 1024
MAX_LOG_LINES = 500
MAX_BUNDLE_UNCOMPRESSED_BYTES = 256 * 1024

_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(access_token|refresh_token|client_secret|password|code_verifier|authorization|cookie)\b\s*[:=]\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/=]{6,}")
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b")
_WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\[^\r\n\"'<>]+")
_UNIX_HOME_RE = re.compile(r"(?:/Users|/home)/[^/\s]+(?:/[^\s\"'<>]*)?")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"(https?://[^\s?#]+)(?:[?#][^\s]*)?")

def _redact_text(value: str) -> str:
    text = str(value or "")
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _JWT_RE.sub("[REDACTED_JWT]", text)
    text = _SECRET_ASSIGN_RE.sub(lambda m: m.group(1) + "=[REDACTED]", text)
    text = _WINDOWS_PATH_RE.sub("<LOCAL_PATH>", text)
    text = _UNIX_HOME_RE.sub("<LOCAL_PATH>", text)
    text = _EMAIL_RE.sub("<EMAIL>", text)
    text = _URL_RE.sub(lambda m: m.group(1), text)
    return text

def _safe_log_tail(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > MAX_LOG_INPUT_BYTES:
                f.seek(size - MAX_LOG_INPUT_BYTES)
            raw = f.read(MAX_LOG_INPUT_BYTES)
    except Exception:
        return ""
    text = raw.decode("utf-8", errors="replace")
    cleaned = [_redact_text(line[:2000]) for line in text.splitlines()[-MAX_LOG_LINES:]]
    out = "\n".join(cleaned)
    data = out.encode("utf-8")
    if len(data) > MAX_LOG_OUTPUT_BYTES:
        data = data[-MAX_LOG_OUTPUT_BYTES:]
        out = data.decode("utf-8", errors="ignore")
    return out

def _health_summary() -> dict:
    return {
        "app_version": VERSION,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "telemetry_enabled": False,
        "automatic_upload": False,
    }

def _update_summary() -> dict:
    path = DATA / "update_status.json"
    allowed = ("status", "version", "from_version", "to_version", "target")
    if not path.exists():
        return {}
    try:
        if path.stat().st_size > 64 * 1024:
            return {"status": "update_status_too_large"}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {key: _redact_text(str(raw[key]))[:200] for key in allowed if key in raw}
    except Exception:
        return {"status": "update_status_unreadable"}

def _bundle_parts(log_path: Path) -> dict[str, bytes]:
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "app_version": VERSION,
        "explicit_local_user_action": True,
        "automatic_upload": False,
        "raw_media_included": False,
        "database_dump_included": False,
        "credential_store_included": False,
        "full_paths_included": False,
        "log_input_max_bytes": MAX_LOG_INPUT_BYTES,
        "log_output_max_bytes": MAX_LOG_OUTPUT_BYTES,
        "bundle_uncompressed_max_bytes": MAX_BUNDLE_UNCOMPRESSED_BYTES,
        "entries": ["manifest.json", "health.json", "sanitized.log"],
    }
    health = _health_summary()
    health["update"] = _update_summary()
    parts = {
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        "health.json": json.dumps(health, indent=2, sort_keys=True).encode("utf-8"),
        "sanitized.log": _safe_log_tail(log_path).encode("utf-8"),
    }
    total = sum(len(v) for v in parts.values())
    if total > MAX_BUNDLE_UNCOMPRESSED_BYTES:
        raise RuntimeError("Support bundle content exceeds bounded size")
    return parts

def create_support_bundle(output_dir: Path | None = None) -> Path:
    target_dir = Path(output_dir) if output_dir is not None else SUPPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final = target_dir / f"archivist_support_{stamp}.zip"
    temp = final.with_suffix(".zip.__new__")
    parts = _bundle_parts(LOGS / "archivist.log")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name in ("manifest.json", "health.json", "sanitized.log"):
            zf.writestr(name, parts[name])
    if temp.stat().st_size > MAX_BUNDLE_UNCOMPRESSED_BYTES:
        temp.unlink(missing_ok=True)
        raise RuntimeError("Support bundle archive exceeds bounded size")
    os.replace(temp, final)
    return final

def run_contract_self_test() -> dict:
    canaries = {
        "token": "access_token=SUPPORT_CANARY_TOKEN_123456",
        "bearer": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
        "path": r"C:\Users\Alice\Private\video.mp4",
        "email": "alice.private@example.com",
        "url": "https://example.test/callback?code=VERY_SECRET_CODE&state=PRIVATE_STATE",
    }
    with tempfile.TemporaryDirectory(prefix="archivist_support_contract_") as td:
        root = Path(td)
        log = root / "canary.log"
        log.write_text("\n".join(canaries.values()), encoding="utf-8")
        parts = _bundle_parts(log)
        combined = b"\n".join(parts.values()).decode("utf-8", errors="replace")
        forbidden = [
            "SUPPORT_CANARY_TOKEN_123456",
            "abcdefghijklmnopqrstuvwxyz123456",
            "C:\\Users\\Alice",
            "Alice\\Private",
            "alice.private@example.com",
            "VERY_SECRET_CODE",
            "PRIVATE_STATE",
        ]
        leaked = [value for value in forbidden if value in combined]
        if leaked:
            raise RuntimeError("support redaction leak: " + ",".join(leaked))
        if "<LOCAL_PATH>" not in combined or "[REDACTED]" not in combined:
            raise RuntimeError("support redaction markers missing")
        out = root / "out"
        out.mkdir()
        final = out / "fixture.zip"
        with zipfile.ZipFile(final, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for name, data in parts.items():
                zf.writestr(name, data)
        with zipfile.ZipFile(final) as zf:
            names = sorted(zf.namelist())
            if names != ["health.json", "manifest.json", "sanitized.log"]:
                raise RuntimeError("unexpected support bundle entries")
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        return {
            "schema_version": manifest["schema_version"],
            "entries": names,
            "explicit_local_user_action": manifest["explicit_local_user_action"],
            "automatic_upload": manifest["automatic_upload"],
            "raw_media_included": manifest["raw_media_included"],
            "database_dump_included": manifest["database_dump_included"],
            "credential_store_included": manifest["credential_store_included"],
            "full_paths_included": manifest["full_paths_included"],
            "redaction_canaries_leaked": 0,
            "log_input_max_bytes": MAX_LOG_INPUT_BYTES,
            "log_output_max_bytes": MAX_LOG_OUTPUT_BYTES,
            "bundle_bytes": final.stat().st_size,
        }

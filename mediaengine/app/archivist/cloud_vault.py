from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

from .config import DB_PATH

VAULT_SCHEMA_VERSION = "cloud_vault_v1"
UPLOAD_MODES = ("exports_only", "selected_media", "full_archive_mirror")


class CloudVaultError(ValueError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_mode(mode: str) -> str:
    mode = str(mode or "").strip()
    if mode not in UPLOAD_MODES:
        raise CloudVaultError("invalid Cloud Vault mode")
    return mode


def ensure_schema(db_path: Path | str = DB_PATH) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(
            """
            create table if not exists cloud_vault_objects (
                id integer primary key autoincrement,
                content_hash text not null,
                local_source_id text not null,
                local_path_ref text not null,
                provider text not null,
                account_ref text,
                remote_object_key text not null,
                remote_path text,
                mode text not null,
                state text not null,
                bytes_total integer not null,
                bytes_uploaded integer not null default 0,
                local_checksum text not null,
                remote_checksum text,
                upload_session_ref text,
                uploaded_at integer,
                verified_at integer,
                last_error text,
                auto_delete_local integer not null default 0,
                created_at integer not null,
                updated_at integer not null
            );
            create unique index if not exists cloud_vault_objects_provider_key_uq
            on cloud_vault_objects(provider, remote_object_key);
            """
        )
        con.commit()
    finally:
        con.close()


def register_local_object(
    *,
    local_path: Path | str,
    local_source_id: str,
    provider: str,
    remote_object_key: str,
    mode: str,
    account_ref: str = "",
    remote_path: str = "",
    db_path: Path | str = DB_PATH,
) -> int:
    mode = validate_mode(mode)
    path = Path(local_path)
    if not path.is_file():
        raise CloudVaultError("local source file missing")
    provider = str(provider or "").strip()
    key = str(remote_object_key or "").strip()
    if not provider or not key:
        raise CloudVaultError("provider and remote object key required")
    size = path.stat().st_size
    checksum = _sha256_file(path)
    now = int(time.time())
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    try:
        cur = con.execute(
            """
            insert into cloud_vault_objects(
                content_hash,local_source_id,local_path_ref,provider,account_ref,
                remote_object_key,remote_path,mode,state,bytes_total,bytes_uploaded,
                local_checksum,remote_checksum,upload_session_ref,uploaded_at,
                verified_at,last_error,auto_delete_local,created_at,updated_at
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                checksum, str(local_source_id), str(path), provider,
                str(account_ref or ""), key, str(remote_path or ""), mode,
                "registered", int(size), 0, checksum, None, None, None, None,
                None, 0, now, now,
            ),
        )
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()


def registry_row(object_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "select * from cloud_vault_objects where id=?",
            (int(object_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def mark_uploaded_verified(
    object_id: int,
    *,
    bytes_uploaded: int,
    remote_checksum: str,
    db_path: Path | str = DB_PATH,
) -> dict:
    row = registry_row(object_id, db_path)
    if not row:
        raise CloudVaultError("registry object missing")
    if int(bytes_uploaded) != int(row["bytes_total"]):
        raise CloudVaultError("remote byte count mismatch")
    if str(remote_checksum or "") != str(row["local_checksum"]):
        raise CloudVaultError("remote checksum mismatch")
    now = int(time.time())
    con = sqlite3.connect(Path(db_path))
    try:
        con.execute(
            """
            update cloud_vault_objects
            set state='verified', bytes_uploaded=?, remote_checksum=?,
                uploaded_at=?, verified_at=?, last_error=null,
                auto_delete_local=0, updated_at=?
            where id=?
            """,
            (int(bytes_uploaded), str(remote_checksum), now, now, now, int(object_id)),
        )
        con.commit()
    finally:
        con.close()
    out = registry_row(object_id, db_path)
    if not out:
        raise CloudVaultError("registry object disappeared")
    return out


def list_registry(db_path: Path | str = DB_PATH) -> list[dict]:
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in con.execute(
                "select * from cloud_vault_objects order by id"
            ).fetchall()
        ]
    finally:
        con.close()


class FakeS3Adapter:
    """Synthetic/local S3-compatible transport. Never performs network I/O."""

    provider = "fake_s3"
    endpoint = "fake-s3://local"
    real_cloud = False

    def __init__(self):
        self._objects: dict[str, bytes] = {}

    def put_object(self, key: str, data: bytes) -> dict:
        key = str(key or "").strip()
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise CloudVaultError("invalid object key")
        if not isinstance(data, (bytes, bytearray)):
            raise CloudVaultError("object data must be bytes")
        payload = bytes(data)
        self._objects[key] = payload
        return {
            "key": key,
            "bytes": len(payload),
            "checksum": _sha256_bytes(payload),
            "endpoint": self.endpoint,
        }

    def head_object(self, key: str) -> dict:
        if key not in self._objects:
            raise CloudVaultError("remote object missing")
        payload = self._objects[key]
        return {
            "key": key,
            "bytes": len(payload),
            "checksum": _sha256_bytes(payload),
            "endpoint": self.endpoint,
        }

    def get_object(self, key: str) -> bytes:
        if key not in self._objects:
            raise CloudVaultError("remote object missing")
        return bytes(self._objects[key])


def upload_registered_object(
    object_id: int,
    adapter: FakeS3Adapter,
    *,
    db_path: Path | str = DB_PATH,
) -> dict:
    if getattr(adapter, "real_cloud", True):
        raise CloudVaultError("CLOUD-100 accepts fake/local transport only")
    row = registry_row(object_id, db_path)
    if not row:
        raise CloudVaultError("registry object missing")
    source = Path(row["local_path_ref"])
    if not source.is_file():
        raise CloudVaultError("local source file missing")
    before_size = source.stat().st_size
    before_hash = _sha256_file(source)
    data = source.read_bytes()
    if _sha256_bytes(data) != row["local_checksum"]:
        raise CloudVaultError("local checksum changed before upload")
    put = adapter.put_object(row["remote_object_key"], data)
    head = adapter.head_object(row["remote_object_key"])
    if put["checksum"] != head["checksum"] or put["bytes"] != head["bytes"]:
        raise CloudVaultError("fake S3 endpoint integrity mismatch")
    updated = mark_uploaded_verified(
        object_id,
        bytes_uploaded=head["bytes"],
        remote_checksum=head["checksum"],
        db_path=db_path,
    )
    if not source.exists() or source.stat().st_size != before_size or _sha256_file(source) != before_hash:
        raise CloudVaultError("local/source original changed during upload")
    if int(updated.get("auto_delete_local") or 0) != 0:
        raise CloudVaultError("automatic local deletion must remain disabled")
    return updated


def run_contract_self_test() -> dict:
    import tempfile

    payloads = {
        "exports_only": b"synthetic-export-v1",
        "selected_media": b"synthetic-selected-media-v1",
        "full_archive_mirror": b"synthetic-full-archive-v1",
    }
    adapter = FakeS3Adapter()
    with tempfile.TemporaryDirectory(prefix="archivist_cloud100_") as td:
        root = Path(td)
        db_path = root / "vault.db"
        ensure_schema(db_path)
        ids = []
        sources = []
        for mode, payload in payloads.items():
            source = root / (mode + ".bin")
            source.write_bytes(payload)
            sources.append(source)
            object_id = register_local_object(
                local_path=source,
                local_source_id="synthetic-" + mode,
                provider=adapter.provider,
                remote_object_key="synthetic/" + mode + ".bin",
                mode=mode,
                db_path=db_path,
            )
            ids.append(object_id)
            row = upload_registered_object(object_id, adapter, db_path=db_path)
            if row["state"] != "verified":
                raise CloudVaultError("registry verification state failed")
            if adapter.get_object(row["remote_object_key"]) != payload:
                raise CloudVaultError("fake S3 round-trip failed")

        rows = list_registry(db_path)
        if len(rows) != 3 or {row["mode"] for row in rows} != set(UPLOAD_MODES):
            raise CloudVaultError("registry/mode coverage failed")
        if any(int(row.get("auto_delete_local") or 0) != 0 for row in rows):
            raise CloudVaultError("auto-delete invariant failed")
        if not all(path.exists() for path in sources):
            raise CloudVaultError("source preservation failed")
        if any(row["local_checksum"] != row["remote_checksum"] for row in rows):
            raise CloudVaultError("checksum verification failed")

        tamper_rejected = False
        try:
            mark_uploaded_verified(
                ids[0],
                bytes_uploaded=rows[0]["bytes_total"],
                remote_checksum="0" * 64,
                db_path=db_path,
            )
        except CloudVaultError:
            tamper_rejected = True
        if not tamper_rejected:
            raise CloudVaultError("checksum mismatch was not rejected")

        return {
            "schema_version": VAULT_SCHEMA_VERSION,
            "provider": adapter.provider,
            "endpoint": adapter.endpoint,
            "real_cloud": False,
            "real_credentials": False,
            "personal_media_upload": False,
            "modes": list(UPLOAD_MODES),
            "registry_rows": len(rows),
            "verified_rows": sum(1 for row in rows if row["state"] == "verified"),
            "checksum_verified": True,
            "checksum_tamper_rejected": True,
            "source_originals_preserved": True,
            "auto_delete_local": False,
        }

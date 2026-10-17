from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH, ensure_dirs


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


_DIRS_AT = [0.0]


def _fold(x):
    """Case-insensitive search for every alphabet (SQLite's own LIKE folds only A-Z: "отпуск" did not find "Отпуск")."""
    return str(x).casefold() if x is not None else None


def connect() -> sqlite3.Connection:
    import time as _t
    if _t.monotonic() - _DIRS_AT[0] > 60:      # the data folders: checked once a minute, not on every query
        ensure_dirs()
        _DIRS_AT[0] = _t.monotonic()
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.create_function("fold", 1, _fold, deterministic=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    return con


@contextmanager
def db():
    con = connect()
    try:
        yield con
    finally:
        con.close()


def _cols(con: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(con: sqlite3.Connection, table: str, name: str, decl: str) -> None:
    if name not in _cols(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def init_db() -> None:
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                source_key TEXT UNIQUE NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT,
                source_label TEXT NOT NULL,
                path TEXT,
                content_uri TEXT,
                media_id TEXT,
                filename TEXT NOT NULL,
                ext TEXT,
                media_type TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                mtime REAL,
                date_taken REAL,
                duration_ms INTEGER,
                width INTEGER,
                height INTEGER,
                discovered_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                preview_status TEXT NOT NULL DEFAULT 'pending',
                preview_path TEXT,
                remote_thumb_uri TEXT,
                remote_thumb_path TEXT,
                analysis_status TEXT NOT NULL DEFAULT 'unreviewed',
                privacy_score REAL,
                privacy_reason TEXT,
                sha256 TEXT,
                archive_path TEXT,
                excluded INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_inv_source ON inventory(source_label);
            CREATE INDEX IF NOT EXISTS idx_inv_kind ON inventory(source_kind);
            CREATE INDEX IF NOT EXISTS idx_inv_type ON inventory(media_type);
            CREATE INDEX IF NOT EXISTS idx_inv_analysis ON inventory(analysis_status);
            CREATE INDEX IF NOT EXISTS idx_inv_size ON inventory(size_bytes);
            CREATE INDEX IF NOT EXISTS idx_inv_mtime ON inventory(mtime);
            CREATE INDEX IF NOT EXISTS idx_inv_sha ON inventory(sha256);

            CREATE TABLE IF NOT EXISTS ignored_hashes (
                sha256 TEXT PRIMARY KEY,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ignored_source_keys (
                source_key TEXT PRIMARY KEY,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                stats_json TEXT,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                stage TEXT NOT NULL DEFAULT 'queued',
                message TEXT,
                total INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                bytes_total INTEGER NOT NULL DEFAULT 0,
                bytes_done INTEGER NOT NULL DEFAULT 0,
                current_inventory_id INTEGER,
                current_filename TEXT,
                options_json TEXT,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, id);

            CREATE TABLE IF NOT EXISTS job_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                inventory_id INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                phase TEXT NOT NULL DEFAULT 'queued',
                bytes_total INTEGER NOT NULL DEFAULT 0,
                bytes_done INTEGER NOT NULL DEFAULT 0,
                result_status TEXT,
                error TEXT,
                started_at TEXT,
                finished_at TEXT,
                UNIQUE(job_id, inventory_id)
            );
            CREATE INDEX IF NOT EXISTS idx_job_items_job ON job_items(job_id, seq);
            CREATE INDEX IF NOT EXISTS idx_job_items_status ON job_items(status);
            """
        )
        # Forward migrations from Archivist 1.x. Never discard the user's existing catalog.
        _add_col(con, "inventory", "staging_path", "TEXT")
        _add_col(con, "inventory", "imported_at", "TEXT")
        _add_col(con, "inventory", "import_status", "TEXT NOT NULL DEFAULT 'not_imported'")
        _add_col(con, "inventory", "import_error", "TEXT")
        _add_col(con, "inventory", "quality_status", "TEXT NOT NULL DEFAULT 'unreviewed'")
        _add_col(con, "inventory", "quality_score", "REAL")
        _add_col(con, "inventory", "quality_reason", "TEXT")
        _add_col(con, "inventory", "analysis_version", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "inventory", "private_path", "TEXT")
        _add_col(con, "inventory", "rejected_path", "TEXT")
        _add_col(con, "inventory", "source_fingerprint", "TEXT")
        _add_col(con, "inventory", "last_job_id", "INTEGER")
        _add_col(con, "inventory", "preview_attempted_at", "TEXT")
        _add_col(con, "inventory", "preview_error", "TEXT")
        _add_col(con, "inventory", "storyboard_status", "TEXT NOT NULL DEFAULT 'pending'")
        _add_col(con, "inventory", "storyboard_frames", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "inventory", "storyboard_best_index", "INTEGER")
        _add_col(con, "inventory", "storyboard_attempted_at", "TEXT")
        _add_col(con, "inventory", "storyboard_error", "TEXT")
        _add_col(con, "inventory", "work_selected", "INTEGER NOT NULL DEFAULT 0")
        # Rights-risk triage is deliberately separate from privacy/quality. It is a
        # workflow aid, not a legal conclusion. Manual decisions are never silently
        # overwritten by later automatic scans.
        _add_col(con, "inventory", "rights_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _add_col(con, "inventory", "rights_reason", "TEXT")
        _add_col(con, "inventory", "rights_place", "TEXT")
        _add_col(con, "inventory", "rights_source_url", "TEXT")
        _add_col(con, "inventory", "rights_notes", "TEXT")
        _add_col(con, "inventory", "rights_audio_present", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "inventory", "rights_manual", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "inventory", "rights_checked_at", "TEXT")
        _add_col(con, "jobs", "cancel_requested", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "jobs", "import_completed_at", "TEXT")
        _add_col(con, "jobs", "source_releasable", "INTEGER NOT NULL DEFAULT 0")
        # 3.1 watchdog metadata. These are deliberately local-only operational
        # fields; remote incidents never include filenames or paths.
        _add_col(con, "jobs", "heartbeat_at", "TEXT")
        _add_col(con, "jobs", "progress_at", "TEXT")
        _add_col(con, "jobs", "worker_pid", "INTEGER")
        _add_col(con, "jobs", "watchdog_retry_requested", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "jobs", "watchdog_process_restarts", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "jobs", "watchdog_app_restarts", "INTEGER NOT NULL DEFAULT 0")
        _add_col(con, "jobs", "watchdog_last_action", "TEXT")
        _add_col(con, "jobs", "watchdog_last_incident_at", "TEXT")
        _add_col(con, "job_items", "transfer_required", "INTEGER NOT NULL DEFAULT 0")
        con.execute("""CREATE TABLE IF NOT EXISTS watchdog_incidents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            kind TEXT,
            action TEXT NOT NULL,
            reason TEXT,
            process_restarts INTEGER NOT NULL DEFAULT 0,
            app_restarts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_watchdog_incidents_job ON watchdog_incidents(job_id,id)")
        con.executescript(
            """CREATE TABLE IF NOT EXISTS social_provider_connections(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                account_id TEXT NOT NULL,
                display_name TEXT,
                granted_scopes_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'disconnected',
                secret_store_ref TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_authenticated_at TEXT,
                last_sync_at TEXT,
                UNIQUE(provider,account_id)
            );
            CREATE INDEX IF NOT EXISTS idx_social_provider_connections_provider
                ON social_provider_connections(provider,status);
            CREATE TABLE IF NOT EXISTS social_oauth_attempts(
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                state_sha256 TEXT NOT NULL,
                verifier_secret_ref TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                scopes_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                terminal_error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_social_oauth_attempts_status
                ON social_oauth_attempts(status,expires_at);
            """
        )
        # 1.x staged files are real imports even though no explicit import_status existed.
        con.execute("UPDATE inventory SET import_status='imported' WHERE staging_path IS NOT NULL AND staging_path<>'' AND import_status='not_imported'")
        # Backfill the Work Set from historical explicit import choices (an old 1.x database) - ONCE: run at every
        # start it put back every video the user had removed from the Library (QA review 2026-10-17)
        con.execute("CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT)")
        if not con.execute("SELECT 1 FROM app_meta WHERE key='work_set_backfill_v1'").fetchone():
            if not con.execute("SELECT 1 FROM app_meta WHERE key='library_membership_v2'").fetchone():
                con.execute("UPDATE inventory SET work_selected=1 WHERE id IN (SELECT ji.inventory_id FROM job_items ji JOIN jobs j ON j.id=ji.job_id WHERE j.kind IN ('import','import_analyze') AND j.status='finished')")
            con.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('work_set_backfill_v1',?)", (now_iso(),))
        # 2.5.1: Library membership is explicit. Import is the source browser for Android,
        # SD/USB and configured local folders. Preserve already-imported/archive media and
        # local files the user has actually worked on, but do not auto-add every newly
        # discovered fixed-folder file to Library.
        con.execute("CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT)")
        if not con.execute("SELECT 1 FROM app_meta WHERE key='library_membership_v2'").fetchone():
            # Undo the old Remove-from-Library-as-global-exclusion behavior for neutral items.
            con.execute("UPDATE inventory SET excluded=0 WHERE excluded=1 AND private_path IS NULL AND rejected_path IS NULL AND analysis_status<>'private'")
            con.execute("UPDATE inventory SET work_selected=1 WHERE excluded=0 AND (staging_path IS NOT NULL OR archive_path IS NOT NULL)")
            con.execute("""UPDATE inventory SET work_selected=1
                           WHERE excluded=0 AND source_kind='fixed' AND work_selected=0
                             AND (analysis_status<>'unreviewed' OR quality_status<>'unreviewed'
                                  OR rights_manual=1 OR sha256 IS NOT NULL)""")
            con.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('library_membership_v2',?)",(now_iso(),))
        con.execute("CREATE INDEX IF NOT EXISTS idx_inv_work_selected ON inventory(work_selected)")
        con.commit()


def upsert_inventory(con: sqlite3.Connection, row: dict) -> None:
    ts = now_iso()
    source_fp = row.get("source_fingerprint") or "|".join([
        str(row.get("source_key") or ""), str(row.get("size_bytes") or ""), str(row.get("mtime") or "")
    ])
    payload = {
        "source_key": row["source_key"],
        "source_kind": row["source_kind"],
        "source_id": row.get("source_id"),
        "source_label": row["source_label"],
        "path": row.get("path"),
        "content_uri": row.get("content_uri"),
        "media_id": row.get("media_id"),
        "filename": row["filename"],
        "ext": row.get("ext"),
        "media_type": row["media_type"],
        "mime_type": row.get("mime_type"),
        "size_bytes": row.get("size_bytes"),
        "mtime": row.get("mtime"),
        "date_taken": row.get("date_taken"),
        "duration_ms": row.get("duration_ms"),
        "width": row.get("width"),
        "height": row.get("height"),
        "discovered_at": ts,
        "last_seen_at": ts,
        "remote_thumb_uri": row.get("remote_thumb_uri"),
        "remote_thumb_path": row.get("remote_thumb_path"),
        "source_fingerprint": source_fp,
    }
    forked = False
    if payload["source_kind"] in ("removable", "android"):
        # Cards and phones reuse paths (DCIM/100CANON/IMG_0001.JPG after a counter reset or on another
        # card). A different file at a known path must NOT inherit the old row's local copy, or it would
        # look imported while only the old picture exists in Staging.
        # Any different file gets a row of its own - also when the old one was only Rejected, removed, selected or
        # had a picture: a swapped card's VID_0001.MP4 must not come in hidden, Private or with the old thumbnail.
        old = con.execute("SELECT id,size_bytes,mtime FROM inventory WHERE source_key=?", (payload["source_key"],)).fetchone()
        if old is not None:
            def _differs(a, b):
                return a is not None and b is not None and str(a) != str(b)

            def _mtime_differs(a, b):
                if a is None or b is None:
                    return False
                try:            # FAT32 cards: 2-second times, shifted by an hour across a daylight-saving change
                    dt = abs(float(a) - float(b))
                    return not (dt <= 2.0 or abs(dt - 3600.0) <= 2.0)
                except (TypeError, ValueError):
                    return str(a) != str(b)
            if _differs(old["size_bytes"], payload["size_bytes"]) or _mtime_differs(old["mtime"], payload["mtime"]):
                gone_key = f'{payload["source_key"]}#superseded:{int(old["id"])}'
                con.execute("UPDATE inventory SET source_key=? WHERE id=?", (gone_key, int(old["id"])))
                try:            # "Private forever" belongs to the old file
                    con.execute("UPDATE ignored_source_keys SET source_key=? WHERE source_key=?", (gone_key, payload["source_key"]))
                except sqlite3.Error:
                    pass
                forked = True
    cols = list(payload)
    updates = ",".join(
        f"{c}=COALESCE(excluded.{c},inventory.{c})" if c in {
            "path","content_uri","media_id","mime_type","size_bytes","mtime","date_taken",
            "duration_ms","width","height","remote_thumb_uri","remote_thumb_path","source_fingerprint"
        } else f"{c}=excluded.{c}"
        for c in cols if c not in {"source_key", "discovered_at"}
    )
    con.execute(
        f"INSERT INTO inventory ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) "
        f"ON CONFLICT(source_key) DO UPDATE SET {updates}",
        [payload[c] for c in cols],
    )
    if not forked:  # a new file at a reused path is judged by its own content hash, not the old path
        con.execute(
            "UPDATE inventory SET analysis_status='private',privacy_reason='private_forever' "
            "WHERE source_key=? AND EXISTS(SELECT 1 FROM ignored_source_keys WHERE source_key=?)",
            (payload["source_key"], payload["source_key"]),
        )


def create_job(kind: str, ids: list[int], options: dict | None = None) -> int:
    # Preserve user order but never let duplicate IDs break a durable job.
    seen = set()
    ids = [int(x) for x in ids if not (int(x) in seen or seen.add(int(x)))]
    if not ids:
        raise ValueError("No files selected")
    with db() as con:
        rows = con.execute(
            f"SELECT id,size_bytes,source_kind,staging_path,archive_path,private_path,path FROM inventory WHERE excluded=0 AND id IN ({','.join('?' for _ in ids)})"
            + ("" if kind in ("private", "reject") else " AND COALESCE(analysis_status,'')<>'private'") + " ORDER BY id",
            ids,
        ).fetchall()
        existing = {int(r["id"]): r for r in rows}
        ordered = [i for i in ids if i in existing]
        if not ordered:
            raise ValueError("Selected files are no longer in the catalog")

        # bytes_total means bytes that actually need to cross from a removable/Android source.
        # Local fixed files and already-imported files are not counted as transfer bytes.
        transfer_total = 0
        if kind in ("import", "import_analyze"):
            for i in ordered:
                r = existing[i]
                already_local = any(r[k] for k in ("staging_path", "archive_path", "private_path"))
                if not already_local and r["source_kind"] in ("android", "removable"):
                    transfer_total += int(r["size_bytes"] or 0)

        cur = con.execute(
            "INSERT INTO jobs(kind,status,created_at,stage,message,total,bytes_total,options_json,cancel_requested,source_releasable) VALUES(?,?,?,?,?,?,?,?,0,0)",
            (kind, "queued", now_iso(), "queued", "Queued", len(ordered), transfer_total, json.dumps(options or {})),
        )
        jid = int(cur.lastrowid)
        for seq, inv_id in enumerate(ordered, 1):
            con.execute(
                "INSERT INTO job_items(job_id,inventory_id,seq,bytes_total,transfer_required) VALUES(?,?,?,?,?)",
                (jid, inv_id, seq, int(existing[inv_id]["size_bytes"] or 0), 1 if (kind in ("import","import_analyze") and not any(existing[inv_id][k] for k in ("staging_path","archive_path","private_path")) and existing[inv_id]["source_kind"] in ("android","removable")) else 0),
            )
            if kind in ("import", "import_analyze"):
                con.execute("UPDATE inventory SET last_job_id=?,work_selected=1 WHERE id=?", (jid, inv_id))
            else:
                con.execute("UPDATE inventory SET last_job_id=? WHERE id=?", (jid, inv_id))
        con.commit()
        return jid

def recover_jobs() -> None:
    # A crash/restart must not lose a multi-hour job. Cancelled jobs stay cancelled;
    # unfinished jobs resume from durable item state and already-imported staging files.
    with db() as con:
        con.execute(
            "UPDATE jobs SET status='cancelled',stage='done',message='Cancelled',finished_at=COALESCE(finished_at,?) "
            "WHERE cancel_requested=1 AND status IN ('running','queued')",
            (now_iso(),),
        )
        con.execute(
            "UPDATE job_items SET status='skipped',phase='cancelled',finished_at=COALESCE(finished_at,?) "
            "WHERE job_id IN (SELECT id FROM jobs WHERE cancel_requested=1) AND status NOT IN ('done','error','skipped')",
            (now_iso(),),
        )
        # Converter jobs have their own durable recovery path. Never feed them
        # into the generic worker, which does not own kind='convert'.
        con.execute(
            "UPDATE jobs SET status='queued',stage='queued',message='Resuming after restart',started_at=NULL,worker_pid=NULL,watchdog_retry_requested=0 "
            "WHERE cancel_requested=0 AND status IN ('running','queued') AND kind<>'convert'"
        )
        con.execute(
            "UPDATE job_items SET status='queued',phase=CASE WHEN phase='imported' THEN 'imported' ELSE 'queued' END,started_at=NULL "
            "WHERE job_id IN (SELECT id FROM jobs WHERE cancel_requested=0 AND status='queued' AND kind<>'convert') "
            "AND status IN ('running','queued','importing','analyzing','archiving')"
        )
        ts=now_iso()
        con.execute("UPDATE jobs SET worker_pid=NULL,watchdog_retry_requested=0,heartbeat_at=COALESCE(heartbeat_at,?),progress_at=COALESCE(progress_at,?) WHERE status IN ('queued','running')",(ts,ts))
        con.commit()


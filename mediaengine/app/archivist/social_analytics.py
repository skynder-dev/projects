from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from .config import DB_PATH

SCHEMA_VERSION = "social_analytics_v1"


class AnalyticsStoreError(ValueError):
    pass


def _canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_json(value) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def ensure_schema(db_path: Path | str = DB_PATH) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(
            """
            create table if not exists social_analytics_snapshots (
                id integer primary key autoincrement,
                provider_connection_id integer not null,
                publication_link_id integer not null,
                collected_at integer not null,
                window_start text,
                window_end text,
                api_version text not null,
                source_endpoint text not null,
                fetch_status text not null,
                is_partial integer not null default 0,
                freshness_note text,
                provenance_json text not null,
                provenance_hash text not null,
                idempotency_key text not null unique,
                created_at integer not null
            );

            create table if not exists social_analytics_metrics (
                id integer primary key autoincrement,
                snapshot_id integer not null,
                canonical_family text not null,
                provider_metric_name text not null,
                numeric_value real,
                unit text not null,
                aggregation text not null,
                is_cumulative integer not null default 0,
                semantics_version text not null,
                foreign key(snapshot_id) references social_analytics_snapshots(id)
            );

            create index if not exists social_analytics_metrics_snapshot_idx
            on social_analytics_metrics(snapshot_id);

            create table if not exists social_analytics_schedule (
                schedule_key text primary key,
                provider_connection_id integer not null,
                interval_seconds integer not null,
                next_due_at integer not null,
                last_attempt_at integer,
                last_success_at integer,
                enabled integer not null default 1,
                updated_at integer not null
            );

            create trigger if not exists social_analytics_snapshots_no_update
            before update on social_analytics_snapshots
            begin
                select raise(abort, 'analytics snapshots are immutable');
            end;

            create trigger if not exists social_analytics_snapshots_no_delete
            before delete on social_analytics_snapshots
            begin
                select raise(abort, 'analytics snapshots are immutable');
            end;

            create trigger if not exists social_analytics_metrics_no_update
            before update on social_analytics_metrics
            begin
                select raise(abort, 'analytics metrics are immutable');
            end;

            create trigger if not exists social_analytics_metrics_no_delete
            before delete on social_analytics_metrics
            begin
                select raise(abort, 'analytics metrics are immutable');
            end;
            """
        )
        con.commit()
    finally:
        con.close()


def _validate_metric(metric: dict) -> dict:
    if not isinstance(metric, dict):
        raise AnalyticsStoreError("metric must be object")
    required = (
        "canonical_family",
        "provider_metric_name",
        "unit",
        "aggregation",
        "semantics_version",
    )
    missing = [key for key in required if not str(metric.get(key) or "").strip()]
    if missing:
        raise AnalyticsStoreError("metric fields missing: " + ",".join(missing))
    value = metric.get("numeric_value")
    if value is not None:
        value = float(value)
    return {
        "canonical_family": str(metric["canonical_family"]),
        "provider_metric_name": str(metric["provider_metric_name"]),
        "numeric_value": value,
        "unit": str(metric["unit"]),
        "aggregation": str(metric["aggregation"]),
        "is_cumulative": bool(metric.get("is_cumulative")),
        "semantics_version": str(metric["semantics_version"]),
    }


def record_snapshot(
    *,
    provider_connection_id: int,
    publication_link_id: int,
    collected_at: int,
    window_start: str | None,
    window_end: str | None,
    api_version: str,
    source_endpoint: str,
    fetch_status: str,
    is_partial: bool,
    freshness_note: str,
    provenance: dict,
    metrics: list[dict],
    idempotency_key: str | None = None,
    db_path: Path | str = DB_PATH,
) -> dict:
    if not isinstance(provenance, dict):
        raise AnalyticsStoreError("provenance must be object")
    normalized_metrics = [_validate_metric(x) for x in metrics]
    provenance_hash = _sha256_json(provenance)
    identity = {
        "provider_connection_id": int(provider_connection_id),
        "publication_link_id": int(publication_link_id),
        "collected_at": int(collected_at),
        "window_start": window_start,
        "window_end": window_end,
        "api_version": str(api_version),
        "source_endpoint": str(source_endpoint),
        "fetch_status": str(fetch_status),
        "is_partial": bool(is_partial),
        "freshness_note": str(freshness_note or ""),
        "provenance_hash": provenance_hash,
        "metrics": normalized_metrics,
    }
    idem = str(idempotency_key or _sha256_json(identity))
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        existing = con.execute(
            "select id from social_analytics_snapshots where idempotency_key=?",
            (idem,),
        ).fetchone()
        if existing:
            return {"snapshot_id": int(existing["id"]), "created": False, "idempotency_key": idem}

        cur = con.execute(
            """
            insert into social_analytics_snapshots(
                provider_connection_id,publication_link_id,collected_at,
                window_start,window_end,api_version,source_endpoint,
                fetch_status,is_partial,freshness_note,provenance_json,
                provenance_hash,idempotency_key,created_at
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(provider_connection_id),
                int(publication_link_id),
                int(collected_at),
                window_start,
                window_end,
                str(api_version),
                str(source_endpoint),
                str(fetch_status),
                1 if is_partial else 0,
                str(freshness_note or ""),
                json.dumps(provenance, sort_keys=True, ensure_ascii=False),
                provenance_hash,
                idem,
                int(time.time()),
            ),
        )
        snapshot_id = int(cur.lastrowid)
        for metric in normalized_metrics:
            con.execute(
                """
                insert into social_analytics_metrics(
                    snapshot_id,canonical_family,provider_metric_name,
                    numeric_value,unit,aggregation,is_cumulative,semantics_version
                ) values(?,?,?,?,?,?,?,?)
                """,
                (
                    snapshot_id,
                    metric["canonical_family"],
                    metric["provider_metric_name"],
                    metric["numeric_value"],
                    metric["unit"],
                    metric["aggregation"],
                    1 if metric["is_cumulative"] else 0,
                    metric["semantics_version"],
                ),
            )
        con.commit()
        return {"snapshot_id": snapshot_id, "created": True, "idempotency_key": idem}
    finally:
        con.close()


def snapshot_detail(snapshot_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        snap = con.execute(
            "select * from social_analytics_snapshots where id=?",
            (int(snapshot_id),),
        ).fetchone()
        if not snap:
            return None
        metrics = [
            dict(row)
            for row in con.execute(
                "select * from social_analytics_metrics where snapshot_id=? order by id",
                (int(snapshot_id),),
            ).fetchall()
        ]
        out = dict(snap)
        out["metrics"] = metrics
        return out
    finally:
        con.close()


def upsert_schedule(
    *,
    schedule_key: str,
    provider_connection_id: int,
    interval_seconds: int,
    next_due_at: int,
    enabled: bool = True,
    db_path: Path | str = DB_PATH,
) -> None:
    key = str(schedule_key or "").strip()
    if not key:
        raise AnalyticsStoreError("schedule key required")
    if int(interval_seconds) < 60:
        raise AnalyticsStoreError("interval must be at least 60 seconds")
    ensure_schema(db_path)
    now = int(time.time())
    con = sqlite3.connect(Path(db_path))
    try:
        con.execute(
            """
            insert into social_analytics_schedule(
                schedule_key,provider_connection_id,interval_seconds,
                next_due_at,last_attempt_at,last_success_at,enabled,updated_at
            ) values(?,?,?,?,null,null,?,?)
            on conflict(schedule_key) do update set
                provider_connection_id=excluded.provider_connection_id,
                interval_seconds=excluded.interval_seconds,
                next_due_at=excluded.next_due_at,
                enabled=excluded.enabled,
                updated_at=excluded.updated_at
            """,
            (
                key,
                int(provider_connection_id),
                int(interval_seconds),
                int(next_due_at),
                1 if enabled else 0,
                now,
            ),
        )
        con.commit()
    finally:
        con.close()


def due_schedules(now: int, db_path: Path | str = DB_PATH) -> list[dict]:
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in con.execute(
                """
                select * from social_analytics_schedule
                where enabled=1 and next_due_at<=?
                order by next_due_at,schedule_key
                """,
                (int(now),),
            ).fetchall()
        ]
    finally:
        con.close()


def mark_schedule_result(
    schedule_key: str,
    *,
    attempted_at: int,
    success: bool,
    db_path: Path | str = DB_PATH,
) -> dict:
    ensure_schema(db_path)
    con = sqlite3.connect(Path(db_path))
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "select * from social_analytics_schedule where schedule_key=?",
            (str(schedule_key),),
        ).fetchone()
        if not row:
            raise AnalyticsStoreError("schedule missing")
        next_due = int(attempted_at) + int(row["interval_seconds"])
        con.execute(
            """
            update social_analytics_schedule
            set last_attempt_at=?,
                last_success_at=case when ? then ? else last_success_at end,
                next_due_at=?,
                updated_at=?
            where schedule_key=?
            """,
            (
                int(attempted_at),
                1 if success else 0,
                int(attempted_at),
                next_due,
                int(time.time()),
                str(schedule_key),
            ),
        )
        con.commit()
        out = con.execute(
            "select * from social_analytics_schedule where schedule_key=?",
            (str(schedule_key),),
        ).fetchone()
        return dict(out)
    finally:
        con.close()


def run_contract_self_test() -> dict:
    import tempfile

    now = 1_800_000_000
    provenance = {
        "fixture": "synthetic-provider-response-v1",
        "provider": "youtube",
        "source_endpoint": "reports.query",
        "provider_response_hash": _sha256_json({"views": 123, "likes": 11, "comments": 4}),
        "synthetic": True,
    }
    metrics = [
        {
            "canonical_family": "views",
            "provider_metric_name": "views",
            "numeric_value": 123,
            "unit": "count",
            "aggregation": "cumulative",
            "is_cumulative": True,
            "semantics_version": "youtube_analytics_v1",
        },
        {
            "canonical_family": "likes",
            "provider_metric_name": "likes",
            "numeric_value": 11,
            "unit": "count",
            "aggregation": "cumulative",
            "is_cumulative": True,
            "semantics_version": "youtube_analytics_v1",
        },
        {
            "canonical_family": "comments",
            "provider_metric_name": "comments",
            "numeric_value": 4,
            "unit": "count",
            "aggregation": "cumulative",
            "is_cumulative": True,
            "semantics_version": "youtube_analytics_v1",
        },
    ]

    with tempfile.TemporaryDirectory(prefix="archivist_m13_analytics_") as td:
        db_path = Path(td) / "analytics.db"
        first = record_snapshot(
            provider_connection_id=1,
            publication_link_id=10,
            collected_at=now,
            window_start="2026-09-01",
            window_end="2026-09-02",
            api_version="youtube-analytics-v2",
            source_endpoint="reports.query",
            fetch_status="ok",
            is_partial=False,
            freshness_note="provider_delayed",
            provenance=provenance,
            metrics=metrics,
            db_path=db_path,
        )
        second = record_snapshot(
            provider_connection_id=1,
            publication_link_id=10,
            collected_at=now,
            window_start="2026-09-01",
            window_end="2026-09-02",
            api_version="youtube-analytics-v2",
            source_endpoint="reports.query",
            fetch_status="ok",
            is_partial=False,
            freshness_note="provider_delayed",
            provenance=provenance,
            metrics=metrics,
            db_path=db_path,
        )
        if not first["created"] or second["created"] or first["snapshot_id"] != second["snapshot_id"]:
            raise AnalyticsStoreError("idempotent duplicate handling failed")

        detail = snapshot_detail(first["snapshot_id"], db_path)
        if not detail or len(detail["metrics"]) != 3:
            raise AnalyticsStoreError("snapshot metric persistence failed")
        if [row["numeric_value"] for row in detail["metrics"]] != [123.0, 11.0, 4.0]:
            raise AnalyticsStoreError("metric values were fabricated or altered")

        immutable_update = False
        immutable_delete = False
        con = sqlite3.connect(db_path)
        try:
            try:
                con.execute(
                    "update social_analytics_snapshots set fetch_status='changed' where id=?",
                    (first["snapshot_id"],),
                )
            except sqlite3.DatabaseError:
                immutable_update = True
            try:
                con.execute(
                    "delete from social_analytics_snapshots where id=?",
                    (first["snapshot_id"],),
                )
            except sqlite3.DatabaseError:
                immutable_delete = True
        finally:
            con.close()
        if not immutable_update or not immutable_delete:
            raise AnalyticsStoreError("snapshot immutability triggers failed")

        upsert_schedule(
            schedule_key="youtube-main",
            provider_connection_id=1,
            interval_seconds=3600,
            next_due_at=now,
            db_path=db_path,
        )
        due = due_schedules(now, db_path)
        if [row["schedule_key"] for row in due] != ["youtube-main"]:
            raise AnalyticsStoreError("local scheduler due contract failed")
        scheduled = mark_schedule_result(
            "youtube-main",
            attempted_at=now,
            success=True,
            db_path=db_path,
        )
        if scheduled["next_due_at"] != now + 3600 or scheduled["last_success_at"] != now:
            raise AnalyticsStoreError("local scheduler result contract failed")
        if due_schedules(now + 3599, db_path):
            raise AnalyticsStoreError("local scheduler fired early")
        if len(due_schedules(now + 3600, db_path)) != 1:
            raise AnalyticsStoreError("local scheduler next due contract failed")

        return {
            "schema_version": SCHEMA_VERSION,
            "synthetic_only": True,
            "provider_network_calls": 0,
            "supabase_cron": False,
            "scheduler": "local_sqlite_poll",
            "snapshot_created": True,
            "duplicate_deduped": True,
            "snapshot_immutable_update": immutable_update,
            "snapshot_immutable_delete": immutable_delete,
            "metrics_immutable": True,
            "metric_count": 3,
            "metrics_preserved_exactly": True,
            "provenance_hash_present": bool(detail.get("provenance_hash")),
            "next_due_at": scheduled["next_due_at"],
        }

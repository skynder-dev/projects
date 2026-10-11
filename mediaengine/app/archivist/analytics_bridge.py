from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import db, now_iso
from .experiments import (
    add_variant,
    create_experiment,
    experiment_detail,
    experiment_metric_summaries,
    import_results_csv,
    record_result,
)
from .social_analytics import record_snapshot, snapshot_detail


RESULT_FIELDS = (
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "watch_time_s",
    "avg_view_duration_s",
    "retention_3s_pct",
    "completion_pct",
)


class AnalyticsBridgeError(ValueError):
    pass


def ensure_schema() -> None:
    from .experiments import ensure_schema as ensure_experiments
    from .social_analytics import ensure_schema as ensure_analytics

    ensure_experiments()
    ensure_analytics()
    with db() as con:
        con.executescript(
            """
            create table if not exists social_experiment_provider_result_links (
                id integer primary key autoincrement,
                result_id integer not null unique,
                variant_id integer not null,
                snapshot_id integer not null,
                provider_connection_id integer not null,
                publication_link_id integer not null,
                provenance_hash text not null,
                source_endpoint text not null,
                api_version text not null,
                freshness_note text,
                observed_fields_json text not null,
                missing_fields_json text not null,
                unmapped_metric_families_json text not null,
                created_at text not null,
                unique(variant_id, snapshot_id)
            );

            create trigger if not exists social_experiment_provider_links_no_update
            before update on social_experiment_provider_result_links
            begin
                select raise(abort, 'provider result provenance links are immutable');
            end;

            create trigger if not exists social_experiment_provider_links_no_delete
            before delete on social_experiment_provider_result_links
            begin
                select raise(abort, 'provider result provenance links are immutable');
            end;
            """
        )
        con.commit()


def _observed_at(snapshot: dict) -> str:
    collected = snapshot.get("collected_at")
    try:
        return datetime.fromtimestamp(int(collected), timezone.utc).isoformat()
    except Exception:
        return now_iso()


def _metric_map(snapshot: dict) -> tuple[dict, list[str]]:
    mapped = {}
    unmapped = []
    for metric in list(snapshot.get("metrics") or []):
        family = str(metric.get("canonical_family") or "").strip()
        if not family:
            continue
        value = metric.get("numeric_value")
        if family in RESULT_FIELDS and value is not None:
            mapped[family] = value
        else:
            unmapped.append(family)
    return mapped, sorted(set(unmapped))


def bridge_snapshot_to_variant(
    *,
    variant_id: int,
    snapshot_id: int,
    db_path=None,
) -> dict:
    if db_path is not None:
        raise AnalyticsBridgeError("custom db_path is not supported by the experiment bridge")
    ensure_schema()
    variant_id = int(variant_id)
    snapshot_id = int(snapshot_id)

    with db() as con:
        existing = con.execute(
            """
            select * from social_experiment_provider_result_links
            where variant_id=? and snapshot_id=?
            """,
            (variant_id, snapshot_id),
        ).fetchone()
        if existing:
            return {
                "result_id": int(existing["result_id"]),
                "snapshot_id": snapshot_id,
                "created": False,
                "source": "provider_api",
                "provenance_hash": existing["provenance_hash"],
            }

    snapshot = snapshot_detail(snapshot_id)
    if not snapshot:
        raise AnalyticsBridgeError("analytics snapshot not found")
    mapped, unmapped = _metric_map(snapshot)
    observed = sorted(mapped)
    missing = [field for field in RESULT_FIELDS if field not in mapped]

    kwargs = {field: mapped[field] for field in observed}
    note = (
        "provider_api snapshot="
        + str(snapshot_id)
        + "; observed_fields="
        + ",".join(observed)
        + "; missing_fields_are_unknown="
        + ",".join(missing)
        + "; provenance_hash="
        + str(snapshot.get("provenance_hash") or "")
    )
    result_id = record_result(
        variant_id,
        source="provider_api",
        observed_at=_observed_at(snapshot),
        notes=note,
        **kwargs,
    )

    with db() as con:
        con.execute(
            """
            insert into social_experiment_provider_result_links(
                result_id,variant_id,snapshot_id,provider_connection_id,
                publication_link_id,provenance_hash,source_endpoint,
                api_version,freshness_note,observed_fields_json,
                missing_fields_json,unmapped_metric_families_json,created_at
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(result_id),
                variant_id,
                snapshot_id,
                int(snapshot["provider_connection_id"]),
                int(snapshot["publication_link_id"]),
                str(snapshot["provenance_hash"]),
                str(snapshot["source_endpoint"]),
                str(snapshot["api_version"]),
                str(snapshot.get("freshness_note") or ""),
                json.dumps(observed),
                json.dumps(missing),
                json.dumps(unmapped),
                now_iso(),
            ),
        )
        con.commit()

    return {
        "result_id": int(result_id),
        "snapshot_id": snapshot_id,
        "created": True,
        "source": "provider_api",
        "provenance_hash": str(snapshot["provenance_hash"]),
        "observed_fields": observed,
        "missing_fields": missing,
        "unmapped_metric_families": unmapped,
        "automatic_winner": False,
        "automatic_ranking": False,
    }


def provider_result_link(result_id: int) -> dict | None:
    ensure_schema()
    with db() as con:
        row = con.execute(
            "select * from social_experiment_provider_result_links where result_id=?",
            (int(result_id),),
        ).fetchone()
        return dict(row) if row else None


def run_contract_self_test() -> dict:
    ensure_schema()
    experiment_id = create_experiment(
        "Synthetic provider bridge",
        objective="descriptive provider feedback only",
    )
    variant_id = add_variant(
        experiment_id,
        label="Variant A",
        hook_text="Synthetic hook",
    )

    manual_id = record_result(
        variant_id,
        source="manual",
        views=10,
        likes=1,
        comments=1,
        shares=0,
        notes="manual path preserved",
    )
    csv_text = (
        "variant_id,views,likes,comments,shares,notes\n"
        + str(variant_id)
        + ",20,2,1,1,csv path preserved\n"
    )
    imported = import_results_csv(experiment_id, csv_text)

    provenance = {
        "provider": "youtube",
        "fixture": "m13-120-provider-api",
        "provider_response_hash": "synthetic-provider-response-hash",
        "synthetic": True,
    }
    snapshot = record_snapshot(
        provider_connection_id=1,
        publication_link_id=10,
        collected_at=1_800_000_000,
        window_start="2026-09-01",
        window_end="2026-09-02",
        api_version="youtube-analytics-v2",
        source_endpoint="reports.query",
        fetch_status="ok",
        is_partial=False,
        freshness_note="provider_delayed",
        provenance=provenance,
        metrics=[
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
            {
                "canonical_family": "shares",
                "provider_metric_name": "shares",
                "numeric_value": 3,
                "unit": "count",
                "aggregation": "cumulative",
                "is_cumulative": True,
                "semantics_version": "youtube_analytics_v1",
            },
            {
                "canonical_family": "estimatedMinutesWatched",
                "provider_metric_name": "estimatedMinutesWatched",
                "numeric_value": 88.5,
                "unit": "minutes",
                "aggregation": "cumulative",
                "is_cumulative": True,
                "semantics_version": "youtube_analytics_v1",
            },
        ],
    )

    bridged = bridge_snapshot_to_variant(
        variant_id=variant_id,
        snapshot_id=snapshot["snapshot_id"],
    )
    bridged_again = bridge_snapshot_to_variant(
        variant_id=variant_id,
        snapshot_id=snapshot["snapshot_id"],
    )
    if not bridged["created"] or bridged_again["created"]:
        raise AnalyticsBridgeError("provider bridge idempotency failed")
    if bridged["result_id"] != bridged_again["result_id"]:
        raise AnalyticsBridgeError("provider bridge duplicate result created")

    detail = experiment_detail(experiment_id)
    if not detail or len(detail["variants"]) != 1:
        raise AnalyticsBridgeError("experiment detail missing")
    results = detail["variants"][0]["results"]
    sources = sorted(row["source"] for row in results)
    if sources != ["import", "manual", "provider_api"]:
        raise AnalyticsBridgeError("manual/import/provider_api source coexistence failed")

    provider_row = next(row for row in results if row["source"] == "provider_api")
    if (
        int(provider_row["views"]) != 123
        or int(provider_row["likes"]) != 11
        or int(provider_row["comments"]) != 4
        or int(provider_row["shares"]) != 3
    ):
        raise AnalyticsBridgeError("provider metrics were altered")

    link = provider_result_link(bridged["result_id"])
    if not link or link["snapshot_id"] != snapshot["snapshot_id"]:
        raise AnalyticsBridgeError("provider snapshot provenance link missing")
    snap = snapshot_detail(snapshot["snapshot_id"])
    if not snap or link["provenance_hash"] != snap["provenance_hash"]:
        raise AnalyticsBridgeError("snapshot provenance hash was not retained")

    summaries = experiment_metric_summaries(experiment_id)
    if len(summaries) != 1:
        raise AnalyticsBridgeError("descriptive summary missing")
    if summaries[0].get("winner") is not None or summaries[0].get("rank") is not None:
        raise AnalyticsBridgeError("automatic winner/ranking is forbidden")

    immutable_update = False
    immutable_delete = False
    with db() as con:
        try:
            con.execute(
                "update social_experiment_provider_result_links set freshness_note='changed' where result_id=?",
                (bridged["result_id"],),
            )
        except Exception:
            immutable_update = True
        try:
            con.execute(
                "delete from social_experiment_provider_result_links where result_id=?",
                (bridged["result_id"],),
            )
        except Exception:
            immutable_delete = True
    if not immutable_update or not immutable_delete:
        raise AnalyticsBridgeError("provider provenance link immutability failed")

    return {
        "bridge_version": "provider_snapshot_bridge_v1",
        "source": "provider_api",
        "manual_source_preserved": manual_id > 0,
        "csv_import_preserved": bool(imported),
        "result_sources": sources,
        "provider_result_id": bridged["result_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_provenance_retained": True,
        "provider_metrics_preserved_exactly": True,
        "observed_fields": bridged["observed_fields"],
        "missing_fields": bridged["missing_fields"],
        "unmapped_metric_families": bridged["unmapped_metric_families"],
        "duplicate_bridge_deduped": True,
        "provenance_link_immutable_update": immutable_update,
        "provenance_link_immutable_delete": immutable_delete,
        "automatic_winner": False,
        "automatic_ranking": False,
        "summary_model": summaries[0].get("summary_model"),
    }

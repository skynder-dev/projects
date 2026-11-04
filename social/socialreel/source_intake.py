"""Common source -> record -> claims -> existing concept core; never generation."""
from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

from . import concept_core, grants, studentaid, usagov
from .claims import build_claims as grant_claims
from .common import ROOT, PipelineError, read_json, sha256_bytes, utc_now, write_json

TOPICS_SCHEMA = "social_topics_v2"
SOURCE_TYPES = ("grants", "usagov", "studentaid", "scorecard")


def acquire(source_type: str, out: Path, *, page: str | None = None, school_id: str | None = None,
            fixture: Path | None = None) -> tuple[dict, list[dict], list[dict]]:
    if source_type == "usagov":
        if not page:
            raise PipelineError("USA.gov requires --page (a page name from socialreel/usagov.py PAGES or an official URL)")
        client = usagov.USAGovClient(out / "source")
        record, receipt = client.page(page, fixture=fixture)
        rows = usagov.build_claims(record, receipt)
    elif source_type == "studentaid":
        if not page:
            raise PipelineError("Student aid requires --page (pell, fafsa_deadlines or official URL)")
        client = studentaid.StudentAidClient(out / "source")
        record, receipt = client.page(page, fixture=fixture)
        rows = studentaid.build_claims(record, receipt)
    elif source_type == "scorecard":
        if not school_id:
            raise PipelineError("College Scorecard requires --college-id")
        client = studentaid.CollegeScorecardClient(out / "source")
        record, receipt = client.school(school_id, fixture=fixture)
        rows = studentaid.build_claims(record, receipt)
    else:
        raise PipelineError("Unsupported public source type")
    return record, rows, client.calls


def _prefix_receipts(value):
    if isinstance(value, list):
        return [_prefix_receipts(v) for v in value]
    if isinstance(value, dict):
        return {k: "grants/" + v if k == "file" and isinstance(v, str) and v.startswith("source/")
                else _prefix_receipts(v) for k, v in value.items()}
    return copy.deepcopy(value)


def _public_score(record: dict, scoring: dict, seen: set[str]) -> dict:
    present = {key: bool(record.get(key)) for key in ("who_it_is_for", "how_to_apply", "what_you_get", "conditions")}
    parts = {}
    for name, field, weight in (("audience", "who_it_is_for", "audience"),
                                ("actionability", "how_to_apply", "actionability"),
                                ("benefit_text", "what_you_get", "benefit_text"),
                                ("conditions", "conditions", "conditions")):
        parts[name] = {"points": scoring[weight] if present[field] else 0,
                       "reason": f"Full source sections for {field} are retained; not proof of individual eligibility" if present[field]
                                 else f"{field} unknown; no source value inferred"}
    parts["timing"] = {"points": 0, "reason": "Deadline text retained where present; no normalized close date/current availability inferred", "days_left": None}
    used = record["topic_id"] in seen
    parts["novelty"] = {"points": 0 if used else scoring["novelty"], "reason": "Already seen" if used else "ID absent from seen file", "seen": used}
    missing = [key for key, known in present.items() if not known]
    parts["missing_data"] = {"points": -len(missing) * scoring["missing_penalty"],
                              "reason": ", ".join(missing) if missing else "No missing section categories"}
    return {"total": sum(c["points"] for c in parts.values()), "components": parts, "missing_data": missing}


def discover_topics(cfg: dict, out: Path, source_types: list[str], *, fixture: Path | None = None,
                    as_of: str | None = None, config_dir: Path | None = None) -> dict:
    from . import topics
    if not source_types or any(source not in SOURCE_TYPES for source in source_types):
        raise PipelineError("--sources supports grants,usagov,studentaid,scorecard")
    source_types = list(dict.fromkeys(source_types))
    today = dt.datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else utc_now().date()
    catalog = topics._merge(read_json(ROOT / "public_sources_config.json"), cfg.get("public_sources", {}))
    seen = set()
    seen_path = topics.configuration(cfg).get("seen_file")
    if seen_path:
        seen_path = Path(seen_path)
        if not seen_path.is_absolute():
            seen_path = (config_dir or ROOT) / seen_path
        if seen_path.exists():
            values = read_json(seen_path)
            if not isinstance(values, list) or any(isinstance(v, bool) or not isinstance(v, (str, int)) for v in values):
                raise PipelineError("Seen file must be a JSON array of topic IDs")
            seen = {str(value) for value in values}
    manifest = read_json(fixture) if fixture is not None else None
    if manifest is not None and (not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list)):
        raise PipelineError("Multi-source fixture requires a manifest with sources entries")
    ranked, dropped, receipts = [], [], []
    detail_count = 0
    if "grants" in source_types:
        grant_fixture = None
        if manifest is not None:
            if not manifest.get("grants_fixture"):
                raise PipelineError("Offline grants source requires grants_fixture in the manifest")
            grant_fixture = fixture.parent / manifest["grants_fixture"]
        grant_cfg = copy.deepcopy(cfg)
        grant_cfg.setdefault("topics", {})["seen_file"] = None
        result = topics.run(grant_cfg, out / "grants", fixture=grant_fixture, as_of=today.isoformat(), config_dir=config_dir)
        for target, items in ((ranked, result["topics"]), (dropped, result["excluded"])):
            for original in items:
                item = _prefix_receipts(original)
                item.update(source_type="grants", topic_id="grants:" + item["opportunity_id"])
                if item["topic_id"] in seen or item["opportunity_id"] in seen:
                    novelty = item["score"]["components"]["novelty"]
                    item["score"]["total"] -= novelty["points"]
                    novelty.update(points=0, reason="ID already in seen file", seen=True)
                target.append(item)
        receipts.extend(_prefix_receipts(result["sources"]))
        detail_count = result["detail_fetch_count"]
    jobs = []
    if manifest is not None:
        for entry in manifest["sources"]:
            if not isinstance(entry, dict) or entry.get("source_type") not in SOURCE_TYPES[1:] or not entry.get("fixture"):
                raise PipelineError("Each public fixture entry requires source_type and a fixture path")
            if entry["source_type"] in source_types:
                jobs.append({**entry, "fixture": fixture.parent / entry["fixture"]})
        if any(source != "grants" and not any(job["source_type"] == source for job in jobs) for source in source_types):
            raise PipelineError("Requested source has no offline fixture entry; live fallback forbidden")
    else:
        for source in source_types:
            if source in {"usagov", "studentaid"}:
                jobs.extend({"source_type": source, "page": page} for page in catalog[source]["pages"])
            elif source == "scorecard":
                schools = catalog[source]["schools"]
                if not schools:
                    raise PipelineError("Scorecard topics require public_sources.scorecard.schools in --config")
                jobs.extend({"source_type": source, "school_id": str(school)} for school in schools)
    ids = {item["topic_id"] for item in ranked + dropped}
    for job in jobs:
        record, claims, calls = acquire(job["source_type"], out, page=job.get("page"),
                                        school_id=job.get("school_id"), fixture=job.get("fixture"))
        receipts.extend(calls)
        programs = []
        if record["source_type"] == "usagov":
            from .usagov_facts import select_for_core
            from .usagov_programs import program_units
            programs = program_units(record, claims)
        for program in programs or [None]:
            scoring_record, selection = record, None
            if record["source_type"] == "usagov":
                scoring_record, _, selection = select_for_core(record, claims, cfg, program=program["name"] if program else None)
            topic_id = record["topic_id"] + ":" + program["name"] if program else record["topic_id"]
            if topic_id in ids:
                raise PipelineError("Duplicate public topic ID in configured sources")
            ids.add(topic_id)
            excluded = bool(selection and selection["state"] == "refused")
            item = {"source_type": record["source_type"], "topic_id": topic_id, "opportunity_id": None,
                    "title": program["title"] if program else record["title"], "agency": record["source_label"], "source_url": record["source_url"],
                    "close_date": record["close_date"], "rubric": record["rubric"],
                    "eligible_applicant_types": None, "score": _public_score(scoring_record, catalog["scoring"], seen),
                    "exclusion": {"excluded": excluded, "code": "no_current_complete_facts" if excluded else None,
                                  "reason": selection["reason"] if excluded else None},
                    "provenance": record["provenance"], "record": record, "claims": claims}
            if selection is not None:
                item["claim_selection"] = selection
            if program:
                item["program"] = program["name"]
            (dropped if excluded else ranked).append(item)
    ranked.sort(key=lambda row: (-row["score"]["total"], row["topic_id"]))
    dropped.sort(key=lambda row: row["topic_id"])
    result = {"schema": TOPICS_SCHEMA, "mode": "fixture" if fixture is not None else "live", "as_of": today.isoformat(),
              "source_types": source_types, "topics": ranked, "excluded": dropped, "sources": receipts,
              "detail_fetch_count": detail_count, "seen_ids_count": len(seen),
              "limitations": ["format not checked live", "Scores are editorial priorities, not benefit eligibility or guarantees.",
                              "Use source --topics to feed these typed topics to the unchanged concept core."]}
    write_json(out / "topics.json", result)
    return result


def _saved_snapshot(root: Path, receipt: dict, out: Path) -> bytes:
    relative = Path(receipt["file"])
    source = (root / relative).resolve()
    if relative.is_absolute() or not source.is_relative_to(root.resolve()):
        raise PipelineError("Snapshot path escapes the topics bundle")
    raw = source.read_bytes()
    if sha256_bytes(raw) != receipt.get("sha256"):
        raise PipelineError("Saved topic snapshot SHA-256 differs; no record replayed")
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return raw


def replay_topic(path: Path, out: Path, topic_id: str | None = None):
    import json
    data = read_json(path)
    if not isinstance(data, dict) or data.get("schema") != TOPICS_SCHEMA:
        raise PipelineError("source --topics requires social_topics_v2 output from --sources")
    rows = data.get("topics") or []
    item = next((row for row in rows if row.get("topic_id") == topic_id), None) if topic_id else (rows[0] if rows else None)
    if not item or item.get("exclusion", {}).get("excluded") is not False:
        raise PipelineError("No matching non-excluded topic")
    if item["source_type"] == "grants":
        if "fixture" in item["provenance"]:
            receipt = item["provenance"]["fixture"]
            rows = json.loads(_saved_snapshot(path.parent, receipt, out))
            rows = rows if isinstance(rows, list) else rows["records"]
            row = next(row for row in rows if topics_id(row["normalized_facts"]["opportunity_id"]) == item["opportunity_id"])
            record = grants.from_fixture(row)
            record["source_type"] = "grants"
            return record, grant_claims(record, receipt, utc_now().date())
        search, detail = item["provenance"]["search"], item["provenance"]["detail"]
        hits = json.loads(_saved_snapshot(path.parent, search, out))["data"]["oppHits"]
        hit = next(h for h in hits if topics_id(h["id"]) == item["opportunity_id"])
        actual = json.loads(_saved_snapshot(path.parent, detail, out))["data"]
        record = grants.normalize(hit, actual, search_snapshot=search, detail_snapshot=detail)
        record["source_type"] = "grants"
        return record, grant_claims(record, detail, utc_now().date())
    record = copy.deepcopy(item["record"])
    receipt = record["provenance"]
    _saved_snapshot(path.parent, receipt, out)
    # Reparse the verified bytes, rather than trusting editable claims in topics.json.
    parsed, claims, _ = acquire(item["source_type"], out, page=receipt["url"], school_id=record.get("school_id"),
                                fixture=out / receipt["file"])
    if item["source_type"] == "usagov" and item["topic_id"] != parsed["topic_id"]:
        from .usagov_programs import program_units
        names = {parsed["topic_id"] + ":" + p["name"]: p["name"] for p in program_units(parsed, claims)}
        if item["topic_id"] not in names:
            raise PipelineError("USA.gov program topic differs from verified snapshot headings")
        parsed["requested_program"] = names[item["topic_id"]]
    return parsed, claims


def topics_id(value):
    from .topics import opportunity_id
    return opportunity_id(value)


def write_bundle(record: dict, claims: list[dict], out: Path, cfg: dict, *, prepare_request: bool = False, program=None) -> dict:
    # A failed/new preparation must never leave an older, runnable request beside new inputs.
    for name in ("concept_request.json", "concept_inputs.json", "concept_record.json", "concept_claims.json",
                 "claim_selection.json", "request_status.json"):
        (out / name).unlink(missing_ok=True)
    if program is not None and record["source_type"] != "usagov":
        raise PipelineError("--program is supported only for USA.gov")
    write_json(out / "record.json", record)
    write_json(out / "claims.json", claims)
    result = {"source_type": record["source_type"], "claims": len(claims), "accepted": False, "model_called": False}
    if record["source_type"] == "usagov":
        from .usagov_facts import select_for_core
        try:
            record, claims, selection = select_for_core(record, claims, cfg, program=program)
        except PipelineError as error:
            status = {"state": "refused", "reason": str(error), "model_called": False}
            write_json(out / "claim_selection.json", status)
            write_json(out / "request_status.json", status)
            raise
        write_json(out / "concept_record.json", record)
        write_json(out / "concept_claims.json", claims)
        write_json(out / "claim_selection.json", selection)
        result["selected_claims"] = len(claims)
        if "program_selection" in selection:
            result["program"] = selection["chosen_program"]
            result["program_selection"] = selection["program_selection"]
            result["program_selection_note"] = selection.get("program_selection_note", "Whole page fits; no single program selected")
            result["left_out_programs"] = selection["left_out_programs"]
        if selection["state"] == "refused":
            write_json(out / "request_status.json", {"state": "refused", "reason": selection["reason"], "model_called": False})
            result["request_refused"] = True
            return result
    inputs = concept_core.inputs(record, claims, cfg)
    write_json(out / "concept_inputs.json", inputs)
    status = {"state": "not_requested", "model_called": False}
    if prepare_request:
        try:
            request = concept_core.build_request(record, claims, cfg)
        except PipelineError as error:
            status = {"state": "refused", "reason": str(error), "model_called": False}
            result["request_refused"] = True
        else:
            write_json(out / "concept_request.json", request)
            status = {"state": "prepared_not_executed", "model_called": False}
    write_json(out / "request_status.json", status)
    return result

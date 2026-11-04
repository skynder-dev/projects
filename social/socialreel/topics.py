"""Transparent topic discovery. Source values are copied whole, never rewritten.

Eligibility codes and rubric/search/scoring rules live in topics_config.json.
The legacy code table is provisional (needs check against Grants.gov docs);
repository fixtures corroborate descriptions, not the full numeric mapping.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import re
from pathlib import Path

from . import grants
from .common import ROOT, PipelineError, parse_date, read_json, sha256_bytes, strip_html, utc_now, write_json

SCHEMA = "social_topics_v1"


def _merge(base: dict, changes: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def configuration(cfg: dict) -> dict:
    result = _merge(read_json(ROOT / "topics_config.json"), cfg.get("topics", {}))
    for key in ("max_detail_fetch", "search_rows"):
        if type(result[key]) is not int or result[key] < 1:
            raise PipelineError(f"topics.{key} must be a positive integer")
    timing = result["timing"]
    if (type(timing["min_days"]) is not int or type(timing["max_days"]) is not int
            or not 0 <= timing["min_days"] <= timing["max_days"]):
        raise PipelineError("Invalid topics timing window")
    for name, rubric in result["rubrics"].items():
        if rubric.get("enabled") is False:
            continue
        if not rubric.get("keywords") or not rubric.get("eligibility_codes"):
            raise PipelineError(f"Empty topic rubric: {name}")
        if any(code not in result["eligibility_codes"] for code in rubric["eligibility_codes"]):
            raise PipelineError(f"Unknown eligibility code in rubric: {name}")
    return result


def opportunity_id(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise PipelineError("Opportunity ID must be a positive decimal integer")
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]+", text) or int(text) <= 0:
        raise PipelineError("Opportunity ID must be a positive decimal integer")
    return str(int(text))


def _present(value) -> bool:
    return value is not None and value != [] and (not isinstance(value, str) or bool(value.strip()))


def _text_present(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _record(hit: dict, detail: dict | None, search_snapshot: dict | None,
            detail_snapshot: dict | None) -> dict:
    """Copy exact source fields, including original applicant dictionaries and HTML."""
    detail = detail or {}
    oid = opportunity_id(hit["id"])
    if _present(detail.get("id")) and opportunity_id(detail["id"]) != oid:
        raise PipelineError("Grants.gov search/detail opportunity IDs differ; no hybrid topic")
    source_name = "synopsis" if detail.get("synopsis") else "forecast"
    source = detail.get(source_name) or {}
    rec = {"opportunity_id": oid, "source_url": grants.PUBLIC_URL.format(id=oid),
           "provenance": {"search": copy.deepcopy(search_snapshot), "detail": copy.deepcopy(detail_snapshot)},
           "field_provenance": {}, "discovered_via": []}

    def pick(name, *candidates):
        for path, value, snapshot in candidates:
            if _present(value):
                rec[name] = copy.deepcopy(value)
                rec["field_provenance"][name] = {"field": path, "snapshot": copy.deepcopy(snapshot)}
                return
        rec[name] = None

    pick("title", ("detail.opportunityTitle", detail.get("opportunityTitle"), detail_snapshot),
         ("hit.title", hit.get("title"), search_snapshot))
    pick("agency", ("detail.agencyDetails.agencyName", (detail.get("agencyDetails") or {}).get("agencyName"), detail_snapshot),
         ("hit.agency", hit.get("agency"), search_snapshot))
    pick("close_date", (f"{source_name}.responseDate", source.get("responseDate"), detail_snapshot),
         ("hit.closeDate", hit.get("closeDate"), search_snapshot))
    pick("status", ("hit.oppStatus", hit.get("oppStatus"), search_snapshot))
    for name, key in (("eligible_applicant_types", "applicantTypes"),
                      ("eligibility_text", "applicantEligibilityDesc"), ("synopsis", "synopsisDesc"),
                      ("award_floor", "awardFloor"), ("award_ceiling", "awardCeiling")):
        actual = "forecastDesc" if source_name == "forecast" and name == "synopsis" else key
        pick(name, (f"{source_name}.{actual}", source.get(actual), detail_snapshot),
             (f"hit.{key}", hit.get(key), search_snapshot))
    return rec


def _categories(rec: dict, cfg: dict) -> tuple[set[str], bool]:
    raw = rec.get("eligible_applicant_types")
    if not _present(raw):
        return set(), True
    values = raw if isinstance(raw, list) else [raw]
    labels = {label.casefold(): code for code, label in cfg["eligibility_codes"].items()}
    labels.update({label.casefold(): code for label, code in cfg["description_aliases"].items()})
    codes, unknown = set(), False
    for value in values:
        code = None
        if isinstance(value, dict):
            identifier = value.get("id")
            if identifier is not None:
                code = str(identifier).zfill(2)
            else:
                code = labels.get(str(value.get("description", "")).casefold())
        elif isinstance(value, str):
            code = labels.get(value.casefold())
        if code in cfg["eligibility_codes"]:
            codes.add(code)
        else:
            unknown = True
    return codes, unknown


def _profession_matches(rec: dict, cfg: dict) -> list[dict]:
    if not cfg["rubrics"].get("profession", {}).get("enabled", False):
        return []
    matches = []
    for name, profession in cfg["professions"].items():
        evidence = []
        for field in ("title", "synopsis", "eligibility_text"):
            raw = rec.get(field)
            if not isinstance(raw, str):
                continue
            # Analysis only. The complete original HTML/text remains in output.
            text = strip_html(raw)
            for keyword in profession["keywords"]:
                pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in keyword.split()) + r"(?!\w)"
                if re.search(pattern, text, re.IGNORECASE):
                    evidence.append({"field": field, "keyword": keyword})
        if evidence:
            matches.append({"profession": name,
                            "points": profession["breadth_points"] + profession["clarity_points"],
                            "breadth_points": profession["breadth_points"], "clarity_points": profession["clarity_points"],
                            "evidence": evidence})
    return sorted(matches, key=lambda item: -item["points"])


def _recurring(rec: dict, cfg: dict) -> dict:
    evidence = []
    for field in ("title", "synopsis"):
        raw = rec.get(field)
        if isinstance(raw, str):
            for pattern in cfg["recurring_program_patterns"]:
                if re.search(pattern, strip_html(raw), re.IGNORECASE):
                    evidence.append({"field": field, "pattern": pattern})
    return {"recurring_program": True if evidence else None, "recurring_program_evidence": evidence,
            "recurring_program_reason": ("Explicit annual/fiscal-year marker; next opening date remains unknown" if evidence
                                         else "No annual/fiscal-year evidence; recurrence unknown")}


def _rubric(rec: dict, cfg: dict) -> str | None:
    codes, _ = _categories(rec, cfg)
    options = []
    for name, rules in cfg["rubrics"].items():
        if rules.get("enabled") is False:
            continue
        if name == "profession":
            professions = _profession_matches(rec, cfg)
            if professions:
                options.append((professions[0]["points"], name))
            continue
        matched = codes.intersection(rules["eligibility_codes"])
        if matched:
            points = max(cfg["audience_points"].get(code, 0) for code in matched)
            options.append((points, name))
    # Config order is the tie-breaker; one ranked row per opportunity ID.
    return max(options, key=lambda item: item[0])[1] if options else None


def score(rec: dict, cfg: dict, today: dt.date, seen: set[str]) -> dict:
    """Return an additive score; lack of evidence never earns a presence point."""
    codes, unknown = _categories(rec, cfg)
    rubric = _rubric(rec, cfg)
    matched = codes.intersection(cfg["rubrics"][rubric]["eligibility_codes"]) if rubric else set()
    audience = min(cfg["audience_max_points"],
                   max((cfg["audience_points"].get(c, 0) for c in matched), default=0)
                   + max(0, len(matched - {"99"}) - 1) * cfg["audience_extra_type_points"])
    mixed = (cfg.get("mixed_list_rule") or {})
    share = len(matched) / len(codes) if codes and matched else 1.0
    mixed_note = ""
    if matched and share < mixed.get("min_share", 0):
        audience = round(audience * share)
        mixed_note = f"; wanted categories are {len(matched)} of {len(codes)} listed, mostly institutions: points x{share:.2f}"
    components = {"audience": {"points": audience,
                  "reason": ("Source lists target applicant categories: " + ", ".join(sorted(matched))
                             + mixed_note if matched else "No confirmed target applicant category; search filter is not evidence"),
                  "matched_codes": sorted(matched)}}
    if rubric == "profession":
        profession = _profession_matches(rec, cfg)[0]
        components["audience"] = {"points": min(cfg["audience_max_points"], profession["points"]),
                                  "reason": "Exact profession evidence: " + profession["profession"]
                                            + "; configured breadth priority plus exact-source clarity, no audience size measured; applicant is not assumed to be a person",
                                  "breadth_points": profession["breadth_points"], "clarity_points": profession["clarity_points"],
                                  "profession": profession["profession"], "evidence": profession["evidence"]}
    if unknown:
        components["audience"]["reason"] += "; some or all applicant types are unknown"
    missing = []
    for field in ("title", "agency", "eligibility_text", "synopsis"):
        if not _text_present(rec.get(field)):
            missing.append(field)
    if not _present(rec.get("eligible_applicant_types")):
        missing.append("eligible_applicant_types")
    if unknown:
        missing.append("recognized_applicant_types")
    close = parse_date(rec.get("close_date"))
    days = (close - today).days if close else None
    timing = cfg["timing"]
    if days is None:
        points, reason = 0, "Close date missing or unparseable; days left unknown"
        missing.append("close_date")
    elif days < 0:
        points, reason = 0, f"Closed {abs(days)} days ago"
    elif days < timing["min_days"]:
        points, reason = timing["soon_points"], f"{days} days left; below preferred minimum {timing['min_days']}"
    elif days > timing["max_days"]:
        points, reason = timing["far_points"], f"{days} days left; beyond preferred maximum {timing['max_days']}"
    else:
        points, reason = timing["ideal_points"], f"{days} days left; within preferred window"
    components["timing"] = {"points": points, "reason": reason, "days_left": days}
    amount = False
    for key in ("award_floor", "award_ceiling"):
        value = rec.get(key)
        if isinstance(value, bool):
            continue
        try:
            number = float(str(value).replace(",", "").replace("$", ""))
            amount = amount or (math.isfinite(number) and number > 0)
        except (ValueError, TypeError):
            pass
    if not amount:
        missing.append("award_amount")
    evidence = {"award_amount": amount, "eligibility_text": _text_present(rec.get("eligibility_text")),
                "synopsis": _text_present(rec.get("synopsis"))}
    checks = [{"field": name, "present": present,
               "points": cfg["concreteness_points"][name] if present else 0,
               "reason": "Source value present" if present else "Missing or unusable; no value inferred"}
              for name, present in evidence.items()]
    components["concreteness"] = {"points": sum(check["points"] for check in checks),
                                  "reason": "; ".join(f"{c['field']}: {c['reason']}" for c in checks),
                                  "checks": checks}
    used = rec["opportunity_id"] in seen
    components["novelty"] = {"points": 0 if used else cfg["novelty_points"],
                              "reason": "ID already in seen file" if used else "ID absent from seen file", "seen": used}
    components["missing_data"] = {"points": -cfg["missing_data_penalty"] * len(missing),
                                  "reason": "Missing or unusable fields: " + ", ".join(missing) if missing else "No missing scoring fields"}
    return {"total": sum(c["points"] for c in components.values()),
            "components": components, "missing_data": missing}


def _research_markers(rec: dict, cfg: dict) -> list[str]:
    rule = cfg.get("research_rule") or {}
    text = " ".join(str(rec.get(k) or "") for k in ("title", "agency", "synopsis")).casefold()
    return [m for m in rule.get("markers", []) if re.search(r"(?<![a-z0-9])" + re.escape(m.casefold()) + r"(?![a-z0-9])", text)]


def _exclusion(rec: dict, cfg: dict, today: dt.date, *, final: bool) -> dict:
    codes, unknown = _categories(rec, cfg)
    profession = _profession_matches(rec, cfg)
    profession_enabled = cfg["rubrics"].get("profession", {}).get("enabled", False)
    if (codes and not unknown and codes.issubset(cfg["institution_codes"]) and not profession
            and (final or not profession_enabled)):
        return {"excluded": True, "code": "institution_only",
                "reason": "Listed applicant types are only educational, government, tribal or other institutions"}
    research = _research_markers(rec, cfg)
    if final and research and not profession and not codes.intersection({"21", "23"}):
        return {"excluded": True, "code": "research_program",
                "reason": "Research program (" + ", ".join(research) + ") without individuals or small businesses "
                          "listed and without an exact profession; not for an ordinary viewer"}
    close = parse_date(rec.get("close_date"))
    if close and close < today:
        return {"excluded": True, "code": "closed", "reason": "Source close date is before the scoring date"}
    if final and not _rubric(rec, cfg):
        return {"excluded": True, "code": "target_eligibility_unconfirmed",
                "reason": "Neither target applicant categories nor an exact professional audience are confirmed by source fields; no eligibility inferred"}
    return {"excluded": False, "code": None, "reason": None}


def _finish(rec: dict, cfg: dict, today: dt.date, seen: set[str], exclusion: dict) -> dict:
    rubric = _rubric(rec, cfg)
    professions = _profession_matches(rec, cfg)
    return {**rec, "rubric": rubric, "score": score(rec, cfg, today, seen),
            "audience_profession": professions[0]["profession"] if rubric == "profession" else None,
            "profession_evidence": professions, **_recurring(rec, cfg),
            "exclusion": exclusion,
            "eligibility_note": "Applicant categories are source metadata; individual eligibility and US-specific conditions are not verified. Read the complete source conditions."}


def _rank_key(rec: dict):
    return (-rec["score"]["total"], rec["opportunity_id"])


def _fixture_records(path: Path, out: Path) -> tuple[list[dict], dict]:
    raw = path.read_bytes()
    data = json.loads(raw)
    rows = data if isinstance(data, list) else data.get("records") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise PipelineError("Topics fixture must be a normalized export list or an object with records")
    snapshot = out / "source" / "topics_fixture.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(raw)
    meta = {"file": "source/topics_fixture.json", "sha256": sha256_bytes(raw), "bytes": len(raw),
            "note": "Exact offline fixture bytes; normalized export, not a fresh official API response"}
    records = []
    fields = {"title": "title", "agency": "agency_name", "close_date": "close_date", "status": "status",
              "eligible_applicant_types": "applicant_types", "eligibility_text": "applicant_eligibility_desc",
              "synopsis": "description", "award_floor": "award_floor", "award_ceiling": "award_ceiling"}
    seen_ids = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("normalized_facts"), dict):
            raise PipelineError("Each fixture record must contain normalized_facts")
        facts = row["normalized_facts"]
        oid = opportunity_id(facts.get("opportunity_id"))
        if oid in seen_ids:
            raise PipelineError(f"Duplicate fixture opportunity ID: {oid}")
        seen_ids.add(oid)
        rec = {"opportunity_id": oid, "source_url": row.get("source_url"),
               "provenance": {"fixture": copy.deepcopy(meta)}, "field_provenance": {}, "discovered_via": []}
        for key, original in fields.items():
            rec[key] = copy.deepcopy(facts.get(original))
            if _present(rec[key]):
                prefix = "" if isinstance(data, list) else "records"
                rec["field_provenance"][key] = {"field": f"{prefix}[{index}].normalized_facts.{original}",
                                                 "snapshot": copy.deepcopy(meta)}
        records.append(rec)
    return records, meta


def run(cfg: dict, out: Path, *, fixture: Path | None = None, as_of: str | None = None,
        config_dir: Path | None = None) -> dict:
    rules = configuration(cfg)
    if as_of is None:
        today = utc_now().date()
    else:
        try:
            today = dt.datetime.strptime(as_of, "%Y-%m-%d").date()
        except ValueError as error:
            raise PipelineError("--as-of must be YYYY-MM-DD") from error
    seen = set()
    seen_path = rules.get("seen_file")
    if seen_path:
        seen_path = Path(seen_path)
        if not seen_path.is_absolute():
            seen_path = (config_dir or ROOT) / seen_path
        if seen_path.exists():
            used = read_json(seen_path)
            if not isinstance(used, list):
                raise PipelineError("Topics seen file must be a JSON array of opportunity IDs")
            seen = {opportunity_id(value) for value in used}
    out.mkdir(parents=True, exist_ok=True)
    ranked, dropped, calls = [], [], []
    detail_count = 0
    if fixture is not None:
        records, receipt = _fixture_records(fixture, out)
        calls = [receipt]
        # All fixture details are already local, so the live request budget is irrelevant.
        for rec in records:
            exclusion = _exclusion(rec, rules, today, final=True)
            item = _finish(rec, rules, today, seen, exclusion)
            (dropped if exclusion["excluded"] else ranked).append(item)
    else:
        client = grants.GrantsGovClient(out / "source")
        candidates = {}
        searches = {}
        for rubric, settings in rules["rubrics"].items():
            if settings.get("enabled") is False:
                continue
            eligibilities = "|".join(settings["eligibility_codes"])
            for keyword in dict.fromkeys(settings["keywords"]):
                query = (keyword, eligibilities)
                if query not in searches:
                    searches[query] = client.search(keyword, rules["search_rows"], rules["statuses"],
                                                     eligibilities=eligibilities)
                hits, receipt = searches[query]
                for hit in hits:
                    oid = opportunity_id(hit.get("id"))
                    if oid not in candidates:
                        candidates[oid] = (_record(hit, None, receipt, None), copy.deepcopy(hit), receipt)
                    rec = candidates[oid][0]
                    rec["discovered_via"].append({"rubric": rubric, "keyword": keyword,
                                                   "search_snapshot": copy.deepcopy(receipt)})
        pending = []
        for rec, hit, receipt in candidates.values():
            exclusion = _exclusion(rec, rules, today, final=False)
            if exclusion["excluded"]:
                dropped.append(_finish(rec, rules, today, seen, exclusion))
            else:
                pending.append((_finish(rec, rules, today, seen, exclusion), hit, receipt))
        pending.sort(key=lambda candidate: _rank_key(candidate[0]))
        for index, (preliminary, hit, receipt) in enumerate(pending):
            if index >= rules["max_detail_fetch"]:
                preliminary["exclusion"] = {"excluded": True, "code": "detail_limit",
                                             "reason": "Outside configured detail budget; eligibility remains unverified"}
                dropped.append(preliminary)
                continue
            detail, detail_receipt = client.detail(preliminary["opportunity_id"])
            detail_count += 1
            rec = _record(hit, detail, receipt, detail_receipt)
            rec["discovered_via"] = preliminary["discovered_via"]
            exclusion = _exclusion(rec, rules, today, final=True)
            item = _finish(rec, rules, today, seen, exclusion)
            (dropped if exclusion["excluded"] else ranked).append(item)
        calls = copy.deepcopy(client.calls)
    ranked.sort(key=_rank_key)
    dropped.sort(key=lambda item: item["opportunity_id"])
    result = {"schema": SCHEMA, "mode": "fixture" if fixture is not None else "live", "as_of": today.isoformat(),
              "config": rules, "seen_ids_count": len(seen), "seen_file_exists": bool(seen_path and seen_path.exists()),
              "detail_fetch_count": detail_count, "topics": ranked, "excluded": dropped, "sources": calls,
              "limitations": ["Rule scores rank source metadata, not suitability or actual eligibility for a viewer.",
                              "Eligibility code table needs check against Grants.gov docs.",
                              "Live API behavior and editorial topic quality are not established by offline tests."]}
    write_json(out / "topics.json", result)
    return result


def top_opportunity_id(path: Path) -> str:
    """Read only a ranked, non-excluded topic; never silently fall back to search."""
    data = read_json(path)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise PipelineError("Unsupported topics.json schema")
    rows = data.get("topics")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise PipelineError("topics.json has no ranked topic")
    exclusion = rows[0].get("exclusion")
    if not isinstance(exclusion, dict) or exclusion.get("excluded") is not False:
        raise PipelineError("Top topic is excluded or lacks an exclusion decision")
    return opportunity_id(rows[0].get("opportunity_id"))

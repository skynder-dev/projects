"""Federal Student Aid HTML and key-protected College Scorecard JSON.

Formats not checked live. Scorecard field names follow the known public data
dictionary; institutional recipient rates never establish individual aid offers.
"""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlencode

from .common import PipelineError, sha256_bytes
from .public_sources import SourceClient, html_claims, html_record

HOSTS = ("studentaid.gov", "www.studentaid.gov")
PAGES = {"pell": "https://studentaid.gov/understand-aid/types/grants/pell",
         "fafsa_deadlines": "https://studentaid.gov/apply-for-aid/fafsa/fafsa-deadlines"}
SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools.json"
KEY_ENV = "COLLEGE_SCORECARD_API_KEY"
FIELDS = ("id", "school.name", "school.state", "school.school_url", "latest.aid.pell_grant_rate", "latest.aid.federal_loan_rate")


class StudentAidClient(SourceClient):
    def page(self, page: str, *, fixture: Path | None = None) -> tuple[dict, dict]:
        url = PAGES.get(page, page)
        raw, receipt = self.read(url, "studentaid", HOSTS, fixture=fixture)
        record = html_record(raw, receipt, "studentaid")
        key = next((name for name, value in PAGES.items() if value == url), sha256_bytes(url.encode("utf-8"))[:16])
        record.update(topic_id="studentaid:" + key, rubric="education")
        return record, receipt


def _school_id(value) -> str:
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise PipelineError("College Scorecard school ID must be a positive integer")
    return str(value)


def _field(row: dict, name: str, index: int):
    if name in row:
        return row[name], f"/results/{index}/{name}"
    parts = name.split(".")
    value = row
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return None, None
        value = value[part]
    return value, f"/results/{index}/" + "/".join(parts)


class CollegeScorecardClient(SourceClient):
    def school(self, school_id: str, *, fixture: Path | None = None) -> tuple[dict, dict]:
        school_id = _school_id(school_id)
        key = None if fixture is not None else os.environ.get(KEY_ENV)
        if fixture is None and (not key or not key.strip()):
            raise PipelineError(f"College Scorecard requires environment variable {KEY_ENV}; no request made")
        # api.data.gov accepts X-Api-Key; keep the credential out of URLs, receipts and errors.
        url = SCORECARD_URL + "?" + urlencode({"id": school_id, "fields": ",".join(FIELDS), "per_page": 1})
        raw, receipt = self.read(url, "scorecard", ("api.data.gov",), fixture=fixture,
                                 headers={"X-Api-Key": key} if key else None, secret=key, suffix="json")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise PipelineError("College Scorecard returned invalid JSON; raw snapshot retained") from None
        rows = data.get("results") if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise PipelineError("Expected exactly one College Scorecard school; format not checked live")
        row = rows[0]
        if str(row.get("id")) != school_id:
            raise PipelineError("College Scorecard returned a different school ID; no hybrid record")
        facts = {}
        for name in FIELDS:
            value, pointer = _field(row, name, 0)
            if value is not None:
                if name in {"latest.aid.pell_grant_rate", "latest.aid.federal_loan_rate"}:
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                        raise PipelineError("College Scorecard aid rate must be a finite number in [0, 1]")
                facts[name] = {"value": copy.deepcopy(value), "locator": {"json_pointer": pointer}}
        title = facts.get("school.name", {}).get("value")
        if not isinstance(title, str) or not title.strip():
            raise PipelineError("College Scorecard school name missing; no title inferred")
        record = {"source_type": "scorecard", "source_label": "College Scorecard", "source_url": receipt["url"],
                  "topic_id": "scorecard:" + school_id, "school_id": school_id, "title": title, "rubric": "education",
                  "facts": facts, "provenance": receipt, "description": None, "applicant_eligibility_desc": None,
                  "who_it_is_for": None, "what_you_get": None, "how_to_apply": None, "conditions": None,
                  "deadlines": None, "close_date": None, "state_rules_differ": None, "state_rules_note": None,
                  "aid": {name: fact["value"] for name, fact in facts.items() if name.startswith("latest.aid.")},
                  "unknowns": ["Current aid offers, individual eligibility, conditions, amounts and deadlines are not supplied by these institution-level rates.",
                               "The reporting year behind latest is not inferred; check the Scorecard documentation and college."],
                  "fixture_only": fixture is not None, "format_note": "format not checked live"}
        return record, receipt


def build_claims(record: dict, snapshot=None, today=None) -> list[dict]:
    if snapshot is not None and snapshot != record.get("provenance"):
        raise PipelineError("Student aid snapshot differs from the saved record")
    if record.get("source_type") == "studentaid":
        return html_claims(record, "studentaid")
    if record.get("source_type") != "scorecard" or record.get("source_label") != "College Scorecard":
        raise PipelineError("Student aid source kind/label mismatch")
    receipt = record["provenance"]
    claims = []
    for index, (name, fact) in enumerate(record["facts"].items()):
        value = fact["value"]
        source = {"kind": "json_field", "url": record["source_url"], "snapshot_file": receipt["file"],
                  "snapshot_sha256": receipt["sha256"], "fields": ["scorecard." + name],
                  "locator": copy.deepcopy(fact["locator"])}
        statement = f"College Scorecard reports {name}: {json.dumps(value, ensure_ascii=False)}."
        if name.startswith("latest.aid."):
            statement += " This institution-level recipient rate is not an individual aid offer or eligibility decision."
        claim = {"key": "identity" if name == "id" else f"scorecard_{index:04d}",
                 "statement": statement, "values": {"field": name, "value": value}, "source": source}
        if receipt.get("fetched_at"):
            source["observed_at"] = receipt["fetched_at"]
            claim["observed_at"] = receipt["fetched_at"]
        claims.append(claim)
    return claims

"""Grants.gov live connector (public, keyless API) + normalization.

Raw API responses are saved byte-for-byte; every downstream claim points back to
the snapshot file and the JSON field it came from.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

from .common import PipelineError, parse_date, sha256_bytes, strip_html, utc_now

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
DETAIL_URL = "https://api.grants.gov/v1/api/fetchOpportunity"
PUBLIC_URL = "https://www.grants.gov/search-results-detail/{id}"
UA = "SocialReels/1.0 (low-volume research; github.com/skynder-dev/projects)"

# Top-level federal agency names by Grants.gov agency-code prefix.
AGENCY_PREFIX = {
    "USDA": "U.S. Department of Agriculture",
    "DOC": "U.S. Department of Commerce",
    "DOD": "U.S. Department of Defense",
    "ED": "U.S. Department of Education",
    "DOE": "U.S. Department of Energy",
    "HHS": "U.S. Department of Health and Human Services",
    "DHS": "U.S. Department of Homeland Security",
    "HUD": "U.S. Department of Housing and Urban Development",
    "DOI": "U.S. Department of the Interior",
    "DOJ": "U.S. Department of Justice",
    "DOL": "U.S. Department of Labor",
    "DOS": "U.S. Department of State",
    "DOT": "U.S. Department of Transportation",
    "USDOT": "U.S. Department of Transportation",
    "TREAS": "U.S. Department of the Treasury",
    "VA": "U.S. Department of Veterans Affairs",
    "EPA": "U.S. Environmental Protection Agency",
    "NASA": "NASA",
    "NSF": "U.S. National Science Foundation",
    "SBA": "U.S. Small Business Administration",
    "NEA": "National Endowment for the Arts",
    "NEH": "National Endowment for the Humanities",
    "IMLS": "Institute of Museum and Library Services",
    "USAID": "U.S. Agency for International Development",
    "AC": "AmeriCorps",
    "CNCS": "AmeriCorps",
    "DOC-NOAA": "National Oceanic and Atmospheric Administration",
}


class GrantsGovClient:
    def __init__(self, snapshot_dir: Path, pause_s: float = 0.4, timeout: int = 40):
        self.dir = snapshot_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pause_s = pause_s
        self.timeout = timeout
        self.calls: list[dict] = []

    def _post(self, url: str, body: dict, name: str) -> tuple[dict, dict]:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA})
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw = r.read()
                    status = r.status
                break
            except Exception as e:  # network hiccup: retry, then fail loudly
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise PipelineError(f"Grants.gov request failed: {url}: {last}")
        p = self.dir / name
        p.write_bytes(raw)
        meta = {"file": f"source/{name}", "url": url, "request": body, "http_status": status,
                "sha256": sha256_bytes(raw), "bytes": len(raw), "fetched_at": utc_now().isoformat()}
        self.calls.append(meta)
        time.sleep(self.pause_s)
        try:
            data = json.loads(raw)
        except ValueError as e:
            raise PipelineError(f"Grants.gov returned non-JSON for {url}") from e
        if int(data.get("errorcode", 0) or 0) != 0:
            raise PipelineError(f"Grants.gov API error {data.get('errorcode')}: {data.get('msg')}")
        return data, meta

    def search(self, keyword: str, rows: int, statuses: str) -> tuple[list[dict], dict]:
        body = {"rows": rows, "oppStatuses": statuses, "startRecordNum": 0}
        if keyword:
            body["keyword"] = keyword
        data, meta = self._post(SEARCH_URL, body, f"search_{_safe(keyword or 'all')}.json")
        hits = ((data.get("data") or {}).get("oppHits")) or []
        return hits, meta

    def detail(self, opp_id: str) -> tuple[dict, dict]:
        data, meta = self._post(DETAIL_URL, {"opportunityId": int(opp_id)}, f"opportunity_{opp_id}.json")
        return data.get("data") or {}, meta


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s)[:40]


def _list(v, n=40) -> list[str]:
    out = []
    for x in (v or [])[:n]:
        if isinstance(x, dict):
            x = x.get("description") or x.get("programTitle") or x.get("alnNumber")
        x = str(x or "").strip()
        if x:
            out.append(x)
    return out


def _num(v):
    if v in (None, "", "none", "None"):
        return None
    try:
        n = float(str(v).replace("$", "").replace(",", ""))
    except ValueError:
        return None
    return n if n > 0 else None


def _bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "yes", "y", "1"):
        return True
    if s in ("false", "no", "n", "0"):
        return False
    return None


def top_agency(code: str | None) -> str | None:
    if not code:
        return None
    code = code.upper()
    for k in sorted(AGENCY_PREFIX, key=len, reverse=True):
        if code == k or code.startswith(k + "-"):
            return AGENCY_PREFIX[k]
    return None


def normalize(hit: dict, detail: dict | None) -> dict:
    """Map search hit + detail into one flat record. `fields` records where each value came from."""
    detail = detail or {}
    syn = detail.get("synopsis") or {}
    fc = detail.get("forecast") or {}
    src = syn or fc
    srcname = "synopsis" if syn else ("forecast" if fc else None)
    fields: dict[str, str] = {}

    def pick(key, *cands):
        for path, val in cands:
            if val not in (None, "", []):
                fields[key] = path
                return val
        return None

    oid = str(hit.get("id") or detail.get("id") or "").strip()
    rec = {
        "opportunity_id": oid,
        "number": pick("number", ("detail.opportunityNumber", detail.get("opportunityNumber")), ("hit.number", hit.get("number"))),
        "title": pick("title", ("detail.opportunityTitle", detail.get("opportunityTitle")), ("hit.title", hit.get("title"))),
        "agency_code": pick("agency_code", ("detail.owningAgencyCode", detail.get("owningAgencyCode")), ("hit.agencyCode", hit.get("agencyCode"))),
        # NB: synopsis.agencyName is NOT reliable (it often holds the contact person, e.g. "Lynn Bailey Grantor").
        "agency_name": pick("agency_name", ("detail.agencyDetails.agencyName", (detail.get("agencyDetails") or {}).get("agencyName")),
                            ("hit.agency", hit.get("agency"))),
        "top_agency_name": pick("top_agency_name", ("detail.topAgencyDetails.agencyName", (detail.get("topAgencyDetails") or {}).get("agencyName"))),
        "status": pick("status", ("hit.oppStatus", hit.get("oppStatus"))),
        "doc_type": pick("doc_type", ("hit.docType", hit.get("docType")), ("detail.docType", detail.get("docType"))),
        "open_date": pick("open_date", ("hit.openDate", hit.get("openDate")), (f"{srcname}.postingDate", src.get("postingDate"))),
        "close_date": pick("close_date", ("hit.closeDate", hit.get("closeDate")), (f"{srcname}.responseDate", src.get("responseDate"))),
        "description": strip_html(pick("description", ("synopsis.synopsisDesc", syn.get("synopsisDesc")), ("forecast.forecastDesc", fc.get("forecastDesc")))),
        "applicant_types": _list(pick("applicant_types", (f"{srcname}.applicantTypes", src.get("applicantTypes")))),
        "applicant_eligibility_desc": strip_html(pick("applicant_eligibility_desc", (f"{srcname}.applicantEligibilityDesc", src.get("applicantEligibilityDesc")))),
        "funding_instruments": _list(pick("funding_instruments", (f"{srcname}.fundingInstruments", src.get("fundingInstruments")))),
        "funding_categories": _list(pick("funding_categories", (f"{srcname}.fundingActivityCategories", src.get("fundingActivityCategories")))),
        "award_ceiling": _num(pick("award_ceiling", (f"{srcname}.awardCeiling", src.get("awardCeiling")))),
        "award_floor": _num(pick("award_floor", (f"{srcname}.awardFloor", src.get("awardFloor")))),
        "estimated_total_program_funding": _num(pick("estimated_total_program_funding", (f"{srcname}.estimatedFunding", src.get("estimatedFunding")))),
        "expected_number_of_awards": _num(pick("expected_number_of_awards", (f"{srcname}.expectedNumberOfAwards", src.get("expectedNumberOfAwards")),
                                               (f"{srcname}.numberOfAwards", src.get("numberOfAwards")))),
        "cost_sharing": _bool(pick("cost_sharing", (f"{srcname}.costSharing", src.get("costSharing")))),
        "detail_fetched": bool(detail),
    }
    rec["top_agency"] = clean_agency(rec.get("top_agency_name")) or top_agency(rec["agency_code"])
    if not rec.get("top_agency_name") and rec["top_agency"]:
        fields["top_agency"] = "agency_code prefix map"
    elif rec["top_agency"]:
        fields["top_agency"] = fields.get("top_agency_name", "")
    rec["source_url"] = PUBLIC_URL.format(id=oid)
    rec["fields"] = fields
    return rec


def from_fixture(row: dict) -> dict:
    """Records exported from the retired Supabase connector (already normalized)."""
    nf = dict(row["normalized_facts"])
    nf["description"] = strip_html(nf.get("description"))
    nf.setdefault("applicant_eligibility_desc", "")
    nf["top_agency"] = top_agency(nf.get("agency_code"))
    nf["source_url"] = row.get("source_url") or PUBLIC_URL.format(id=nf["opportunity_id"])
    nf["fields"] = {k: f"supabase_export.normalized_facts.{k}" for k in nf if k not in ("fields",)}
    return nf


def clean_agency(name: str | None) -> str | None:
    """Readable agency name or None (rejects codes like '69A350 OSDBU' and multi-line contact blocks)."""
    if not name:
        return None
    n = " ".join(str(name).split())
    n = re.sub(r"\s+-\s+[A-Z]{2,8}$", "", n)          # "Centers for Disease Control and Prevention - ERA"
    if "\n" in str(name).strip() or re.search(r"\bgrantor\b|@|\d{3}[-.)\s]\d{3}", n, re.I):
        return None
    if re.match(r"^[0-9A-Z]{4,}\s", n) or len(n) < 3 or n.isupper() and len(n) > 12:
        return None
    return n


def is_closing_after(rec: dict, min_date) -> bool:
    d = parse_date(rec.get("close_date"))
    return bool(d and d >= min_date)

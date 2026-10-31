"""Grants.gov live connector (public, keyless API) + normalization.

Raw API responses are saved byte-for-byte; every downstream claim points back to
the snapshot file and the JSON field it came from.
"""
from __future__ import annotations

import json
import re
import time
import ssl
import socket
try:
    import truststore
except ImportError:
    truststore = None
import urllib.request
import urllib.error
from pathlib import Path

from .common import PipelineError, parse_date, sha256_bytes, strip_html, utc_now, check_cancel,write_json,read_json,atomic_bytes,stable_json

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


class GrantsGovUnavailable(PipelineError):
    host_unavailable=True


class GrantsGovClient:
    def __init__(self, snapshot_dir: Path, pause_s: float = 0.4, timeout: int = 40, history_path=None):
        self.dir = snapshot_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pause_s = pause_s
        self.timeout = timeout
        self.calls: list[dict] = []
        ledger=self.dir/"request_attempts.json"
        if ledger.exists():
            saved=read_json(ledger)
            if not isinstance(saved,dict):raise PipelineError('Wire-attempt ledger shape invalid; no source request')
            payload={k:v for k,v in saved.items() if k!='ledger_sha256'}
            if saved.get('schema')!='SOCIAL_GRANTS_WIRE_ATTEMPTS_V1' or saved.get('ledger_sha256')!=sha256_bytes(stable_json(payload).encode()) or not isinstance(saved.get('attempts'),list):raise PipelineError('Wire-attempt ledger changed; no source request')
            self.attempts=saved['attempts']
        else:self.attempts=[]
        self.initial_attempt_count=len(self.attempts)
        from .common import ROOT
        self.observation_history=Path(history_path) if history_path is not None else ROOT/'data/jobs/history.json'
        if (self.observation_history.parent/'queue.sqlite3').is_file():
            from .connector_observations import recover
            self.recovered_observations=recover(self.observation_history)
        else:self.recovered_observations=[]

    def _persist_attempts(self):
        payload={'schema':'SOCIAL_GRANTS_WIRE_ATTEMPTS_V1','attempts':self.attempts}
        write_json(self.dir/'request_attempts.json',{**payload,'ledger_sha256':sha256_bytes(stable_json(payload).encode())})

    def _post(self, url: str, body: dict, name: str) -> tuple[dict, dict]:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA})
        if url not in {SEARCH_URL,DETAIL_URL}:raise PipelineError('Only fixed Grants.gov API endpoints allowed')
        attempt={'url':url,'request':body,'request_sha256':sha256_bytes(stable_json(body).encode()),'snapshot_name':name,'started_at':utc_now().isoformat(),'phase':'intent'}
        self.attempts.append(attempt);self._persist_attempts()
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise PipelineError('Grants.gov redirect rejected; no destination request or hidden attempt')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=(truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if truststore else ssl.create_default_context())))
        try:
            with opener.open(req,timeout=self.timeout) as r:
                raw=r.read(8*1024*1024+1);status=r.status
                if len(raw)>8*1024*1024:raise PipelineError('Grants.gov response exceeds8MiB')
        except (urllib.error.URLError,PipelineError,TimeoutError,OSError) as error:
            host_blocked=(isinstance(error,urllib.error.URLError) and isinstance(error.reason,socket.gaierror)) or getattr(error,'code',None) in {401,403,429}
            attempt.update(phase='failed',finished_at=utc_now().isoformat(),error=type(error).__name__+': '+str(error)[:250],http_status=getattr(error,'code',None),host_unavailable=host_blocked)
            self._persist_attempts()
            failure=(GrantsGovUnavailable if host_blocked else PipelineError)('Grants.gov request failed after one wire attempt; no hidden retry: '+str(error)[:200]);failure.code=getattr(error,'code',None)
            raise failure from error
        p=self.dir/name
        meta={'file':f'source/{name}','url':url,'request':body,'http_status':status,'sha256':sha256_bytes(raw),'bytes':len(raw),'fetched_at':utc_now().isoformat()}
        attempt.update(phase='received',finished_at=utc_now().isoformat(),snapshot_meta=meta)
        # Persist receipt identity before bytes: interruption can recover only exact
        # received bytes, never guess a fresh observation or reissue an uncertain call.
        self._persist_attempts()
        atomic_bytes(p,raw);write_json(self.dir/(name+'.meta.json'),meta)
        self.calls.append(meta)
        time.sleep(self.pause_s)
        try:
            data = json.loads(raw)
        except ValueError as e:
            if url==DETAIL_URL:self._deliver_detail_receipt(str(body.get('opportunityId')),meta)
            raise PipelineError(f"Grants.gov returned non-JSON for {url}") from e
        if not isinstance(data,dict) or (data.get("data") is not None and not isinstance(data["data"],dict)):
            if url==DETAIL_URL:self._deliver_detail_receipt(str(body.get("opportunityId")),meta)
            raise PipelineError("Grants.gov response has an invalid object schema")
        try:
            code=int(data.get("errorcode",0) or 0)
        except (TypeError,ValueError) as error:
            raise PipelineError("Grants.gov response has an invalid error code") from error
        if code != 0:
            raise PipelineError(f"Grants.gov API error {data.get('errorcode')}: {data.get('msg')}")
        return data, meta

    def search(self, keyword: str, rows: int, statuses: str, start: int = 0) -> tuple[list[dict], dict]:
        if type(rows) is not int or not 1<=rows<=1000 or type(start) is not int or start<0:raise PipelineError('Invalid bounded search rows/offset before request')
        body = {"rows": rows, "oppStatuses": statuses, "startRecordNum": start}
        if keyword:
            body["keyword"] = keyword
        data, meta = self._post(SEARCH_URL, body, f"search_{_safe(keyword or 'all')}_{sha256_bytes(json.dumps(body, sort_keys=True).encode())[:12]}.json")
        from .source_responses import search_payload
        hits,paging=search_payload(data,rows,start)
        if paging is not None:meta={**meta,'pagination':paging}
        return hits,meta

    def detail(self, opp_id: str) -> tuple[dict, dict]:
        from .source_responses import requested_id
        opp_id=requested_id(opp_id)
        data, meta = self._post(DETAIL_URL, {"opportunityId": int(opp_id)}, f"opportunity_{opp_id}.json")
        self._deliver_detail_receipt(opp_id,meta)
        from .source_responses import detail_envelope
        return detail_envelope(data,opp_id),meta

    def _deliver_detail_receipt(self,opp_id,meta):
        from .connector_observations import deliver
        self.last_observation=deliver(self.observation_history,self.dir,opp_id,meta,mode='live')

    def replay_detail(self, opp_id, meta):
        """Replay exact saved receipt through the same durable sink; no HTTP/currentness claim."""
        from .connector_observations import deliver,raw_at
        raw=raw_at(self.dir,meta)
        self.last_observation=deliver(self.observation_history,self.dir,opp_id,meta,mode='replay')
        try:data=json.loads(raw)
        except ValueError as error:raise PipelineError('Malformed saved replay retained; not applied') from error
        from .source_responses import detail_envelope
        return detail_envelope(data,opp_id), {**meta,'observation_mode':'replay','live_currentness_proved':False}


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
    import math
    return n if math.isfinite(n) and n > 0 else None


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
    if hit.get('id') is not None and detail.get('id') is not None and str(hit['id'])!=str(detail['id']):raise PipelineError('Search/detail identity mismatch; cannot mix facts from another opportunity')
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
        "status": pick("status", ("detail.ost", detail.get("ost")), ("hit.oppStatus", hit.get("oppStatus"))),
        "doc_type": pick("doc_type", ("detail.docType", detail.get("docType")), ("hit.docType", hit.get("docType"))),
        "open_date": pick("open_date", (f"{srcname}.postingDate", src.get("postingDate")), ("hit.openDate", hit.get("openDate"))),
        "close_date": pick("close_date", (f"{srcname}.responseDate", src.get("responseDate")), ("hit.closeDate", hit.get("closeDate"))),
        "full_announcement_url": pick("full_announcement_url", (f"{srcname}.fundingDescLinkUrl", src.get("fundingDescLinkUrl"))),
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
    from .grant_attachments import discover as discover_attachments, discover_pdf
    rec["announcement_attachments"] = discover_attachments(detail, oid)+discover_pdf(detail, oid)
    if rec["announcement_attachments"]:
        fields["announcement_attachments"] = "detail.synopsisAttachmentFolders"
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



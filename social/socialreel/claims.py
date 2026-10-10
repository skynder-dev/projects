"""Claim ledger built deterministically from official fields, plus the grounding validator.

No LLM ever creates a claim. Writers may only *cite* claims; the validator rejects any
number, amount or date in the script that is not carried by a cited claim.
"""
from __future__ import annotations

import datetime as dt
import re

from .common import human_date, money, parse_date

BROAD_APPLICANTS = ("small business", "nonprofit", "individual", "city", "county", "township",
                    "tribal", "independent school", "public housing", "special district",
                    "state government", "higher education", "for profit")


def _src(rec, snap, *keys):
    return {
        "url": rec["source_url"],
        "snapshot_file": snap.get("file"),
        "snapshot_sha256": snap.get("sha256"),
        "fields": [rec.get("fields", {}).get(k, k) for k in keys],
    }


def first_sentence(text: str, max_words: int = 40) -> str | None:
    if not text:
        return None
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = (m.group(1) if m else text).strip()
    if len(s.split()) > max_words or len(s.split()) < 6:
        return None
    return s


def build_claims(rec: dict, snap: dict, today: dt.date) -> list[dict]:
    """Return the claim ledger. Each claim is a single checkable statement."""
    C: list[dict] = []
    agency = rec.get("agency_name") or ""
    if re.match(r"^\s*[0-9A-Z]{4,}\s", agency or ""):       # e.g. "69A350 OSDBU" -> not a readable name
        agency = ""
    top = rec.get("top_agency")
    display_agency = agency if agency and not agency.isupper() else (top or agency or rec.get("agency_code") or "")

    def add(key, statement, values, *fields):
        C.append({"key": key, "statement": statement, "values": values, "source": _src(rec, snap, *fields)})

    add("identity",
        f"Grants.gov lists \"{rec['title']}\" as funding opportunity {rec.get('number') or rec['opportunity_id']}.",
        {"title": rec["title"], "number": rec.get("number"), "opportunity_id": rec["opportunity_id"]},
        "title", "number")
    if display_agency:
        add("agency", f"The listing agency is {display_agency}.",
            {"agency": display_agency, "agency_code": rec.get("agency_code"), "parent_agency": top},
            "agency_name", "agency_code")
    if top and top != display_agency:
        add("parent_agency", f"The agency code {rec.get('agency_code')} belongs to the {top}.",
            {"parent_agency": top, "agency_code": rec.get("agency_code")}, "agency_code")
    if rec.get("status"):
        add("status", f"The opportunity status on Grants.gov is \"{rec['status']}\".",
            {"status": rec["status"]}, "status")
    od = parse_date(rec.get("open_date"))
    if od:
        add("posted", f"Grants.gov lists the posting date as {human_date(od)}.",
            {"date": od.isoformat()}, "open_date")
    cd = parse_date(rec.get("close_date"))
    if cd and cd >= today:
        add("deadline", f"Grants.gov lists the close date as {human_date(cd)}.",
            {"date": cd.isoformat(), "days_left_at_build": (cd - today).days}, "close_date")
    lo, hi = rec.get("award_floor"), rec.get("award_ceiling")
    if hi and lo and lo < hi:
        add("award_range", f"Grants.gov lists individual awards from {money(lo)} to {money(hi)}.",
            {"award_floor": lo, "award_ceiling": hi}, "award_floor", "award_ceiling")
    elif hi:
        add("award_ceiling", f"Grants.gov lists an award ceiling of {money(hi)} per award.",
            {"award_ceiling": hi}, "award_ceiling")
    tot = rec.get("estimated_total_program_funding")
    if tot:
        add("total_funding", f"Grants.gov lists estimated total program funding of {money(tot)}.",
            {"estimated_total_program_funding": tot}, "estimated_total_program_funding")
    n = rec.get("expected_number_of_awards")
    if n and n == int(n):
        add("expected_awards", f"Grants.gov lists {int(n)} expected awards.",
            {"expected_number_of_awards": int(n)}, "expected_number_of_awards")
    apps = rec.get("applicant_types") or []
    specific = [a for a in apps if not a.lower().startswith("others")]
    if specific:
        add("eligibility", "Eligible applicant types listed: " + "; ".join(specific) + ".",
            {"applicant_types": specific, "has_additional_conditions": len(specific) != len(apps)},
            "applicant_types")
    note = first_sentence(rec.get("applicant_eligibility_desc") or "", max_words=45)
    if note:
        add("eligibility_note", f"The listing's eligibility information says: \"{note}\"", {"quote": note},
            "applicant_eligibility_desc")
    if not specific and apps:
        add("eligibility_restricted",
            "Grants.gov does not list a standard applicant type; eligibility is defined in the "
            "listing's additional eligibility information.",
            {"applicant_types": apps}, "applicant_types")
    inst = rec.get("funding_instruments") or []
    if inst:
        add("instrument", "Funding instrument: " + ", ".join(inst) + ".", {"funding_instruments": inst},
            "funding_instruments")
    cats = rec.get("funding_categories") or []
    if cats:
        add("category", "Funding category: " + ", ".join(cats) + ".", {"funding_categories": cats},
            "funding_categories")
    cs = rec.get("cost_sharing")
    if cs is not None:
        add("cost_sharing", "Cost sharing or matching is " + ("required." if cs else "not required."),
            {"cost_sharing_required": cs}, "cost_sharing")
    q = first_sentence(rec.get("description") or "")
    if q:
        add("purpose_quote", f"The official synopsis says: \"{q}\"", {"quote": q}, "description")
    return C


def audience_score(rec: dict) -> int:
    apps = " ".join(rec.get("applicant_types") or []).lower()
    return sum(1 for k in BROAD_APPLICANTS if k in apps)


# ---------------------------------------------------------------- grounding validator

_MON = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
_MONTH_NUM = {m[:3].lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand|[MBK])?\b", re.I)
MONEY_WORD_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand)?\s*dollars\b", re.I)
DATE_RE = re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I)
NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
VAGUE_RE = re.compile(r"\b(hundreds|thousands|millions|billions|dozens)\s+of\b|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\b(?=\s+(thousand|million|billion|hundred|dollars|awards|grants|percent))", re.I)
BANNED = [r"\bfree money\b", r"\bguarantee[ds]?\b", r"\byou qualify\b", r"\byou(?:'re| are) eligible\b",
          r"\banyone can\b", r"\beveryone can\b", r"\beasy money\b", r"\bno strings\b",
          r"\blast chance\b", r"\bact now\b", r"\bdon'?t miss\b", r"\bsecret\b", r"\bcure[sd]?\b"]
_UNIT = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9}


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def extract_tokens(text: str) -> dict:
    """Pull every amount, date and bare number out of text."""
    t = text
    out = {"money": [], "dates": [], "numbers": []}
    for m in MONEY_RE.finditer(t):
        out["money"].append(_f(m[1]) * _UNIT.get((m[2] or "").lower(), 1))
    for m in MONEY_WORD_RE.finditer(t):
        out["money"].append(_f(m[1]) * _UNIT.get((m[2] or "").lower(), 1))
    t2 = MONEY_WORD_RE.sub(" ", MONEY_RE.sub(" ", t))
    for m in DATE_RE.finditer(t2):
        out["dates"].append((_MONTH_NUM[m[1][:3].lower()], int(m[2]), int(m[3]) if m[3] else None))
    t3 = DATE_RE.sub(" ", t2)
    for m in NUM_RE.finditer(t3):
        out["numbers"].append(m[0].replace(",", ""))
    return out


def allowed_tokens(claims: list[dict]) -> dict:
    money_v, dates, nums = set(), set(), set()
    for c in claims:
        tk = extract_tokens(c["statement"])
        money_v.update(tk["money"])
        dates.update(tk["dates"])
        nums.update(tk["numbers"])
        for k, v in (c.get("values") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                money_v.add(float(v))
                nums.add(str(int(v)) if float(v) == int(v) else str(v))
            if isinstance(v, str):
                d = parse_date(v)
                if d and k == "date":
                    dates.add((d.month, d.day, d.year))
                    nums.add(str(d.year))
                for m in NUM_RE.finditer(v):
                    nums.add(m[0].replace(",", ""))
                for m in re.finditer(r"\d+", v):
                    nums.add(m[0])
    for (mo, d, y) in list(dates):
        if y:
            nums.add(str(y))
    return {"money": money_v, "dates": dates, "numbers": nums}


def _money_ok(v: float, allowed: set) -> bool:
    return any(abs(v - a) <= max(0.005 * a, 0.5) for a in allowed if a > 0)


def validate_script(script: dict, claims: list[dict]) -> list[str]:
    """Return a list of problems. Empty list == every fact is carried by a cited claim."""
    errs: list[str] = []
    by_key = {c["key"]: c for c in claims}
    segs = script.get("segments") or []
    if not (4 <= len(segs) <= 10):
        errs.append(f"segment count {len(segs)} outside 4..10")
    for i, s in enumerate(segs):
        tag = f"segment {i + 1}"
        keys = s.get("claim_keys") or []
        if not keys:
            errs.append(f"{tag}: cites no claim")
        unknown = [k for k in keys if k not in by_key]
        if unknown:
            errs.append(f"{tag}: unknown claim keys {unknown}")
        cited = [by_key[k] for k in keys if k in by_key]
        allow = allowed_tokens(cited)
        scr = s.get("on_screen") or {}
        text = " ".join([s.get("voiceover", "")] + [str(scr.get(k, "")) for k in ("kicker", "big", "headline", "sub")])
        if not s.get("voiceover", "").strip():
            errs.append(f"{tag}: empty voiceover")
        tk = extract_tokens(text)
        for v in tk["money"]:
            if not _money_ok(v, allow["money"]):
                errs.append(f"{tag}: amount {v:,.0f} not in cited claims {keys}")
        for (mo, d, y) in tk["dates"]:
            ok = any(mo == a[0] and d == a[1] and (y is None or y == a[2]) for a in allow["dates"])
            if not ok:
                errs.append(f"{tag}: date {mo}/{d}/{y or '?'} not in cited claims {keys}")
        for n in tk["numbers"]:
            if n not in allow["numbers"] and not _money_ok(_f(n), allow["money"]):
                errs.append(f"{tag}: number {n} not in cited claims {keys}")
        if VAGUE_RE.search(text):
            errs.append(f"{tag}: vague or spelled-out quantity: '{VAGUE_RE.search(text)[0]}'")
        for pat in BANNED:
            if re.search(pat, text, re.I):
                errs.append(f"{tag}: banned phrasing /{pat}/")
        if re.search(r"\b(just posted|brand[- ]new|newly posted)\b", text, re.I) and "posted" not in keys:
            errs.append(f"{tag}: recency claim without the 'posted' claim")
    if segs:
        last = " ".join([segs[-1].get("voiceover", "")] + [str(v) for v in (segs[-1].get("on_screen") or {}).values()])
        if not re.search(r"grants\.gov", last, re.I) or not re.search(r"\b(check|verify|confirm|read|official)\w*", last, re.I):
            errs.append("last segment must point to Grants.gov and tell viewers to check the official listing")
    words = sum(len((s.get("voiceover") or "").split()) for s in segs)
    if not (55 <= words <= 170):
        errs.append(f"narration length {words} words outside 55..170 (~20-60 s)")
    return errs

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
    sources = []
    for key in keys:
        meta = rec.get('_field_sources', {}).get(key, snap)
        sources.append({'field': rec.get('fields', {}).get(key, key),
                        'snapshot_file': meta.get('file'), 'snapshot_sha256': meta.get('sha256'),
                        'opportunity_id': rec.get('opportunity_id')})
    first = sources[0] if sources else {'snapshot_file': snap.get('file'), 'snapshot_sha256': snap.get('sha256')}
    return {'url': rec['source_url'], 'snapshot_file': first['snapshot_file'],
            'snapshot_sha256': first['snapshot_sha256'], 'fields': [source['field'] for source in sources],
            'field_sources': sources}


BOILERPLATE = re.compile(r"notice of funding|\bNOFO\b|funding opportunity announcement|announces the availability|"
                         r"this (?:announcement|opportunity|solicitation) (?:is|will)|please (?:see|refer|read)|"
                         r"see the full|attached|click|webinar|passcode|https?://", re.I)


def source_sentences(text):
    """Contiguous source sentences; abbreviations and open parentheses are not cut."""
    start=0;out=[]
    for match in re.finditer(r"[.!?](?=[\"')\]]*(?:\s|$))",text):
        end=match.end()
        while end<len(text) and text[end] in '\"\')]' :end+=1
        candidate=text[start:end].strip()
        if re.search(r'(?:e\.g|i\.e|u\.s|u\.k|dr|mr|mrs|ms|prof|vs|etc)\.$',text[:match.end()],re.I):continue
        if candidate.count('(')>candidate.count(')') or candidate.count('[')>candidate.count(']'):continue
        if candidate:out.append(candidate)
        start=end
    tail=text[start:].strip()
    if tail:out.append(tail)
    return out

def first_sentence(text: str, max_words: int = 40, title: str = "") -> str | None:
    """First informative sentence (skips NOFO boilerplate and sentences that just repeat the title)."""
    if not text:
        return None
    sentences = source_sentences(text)[:5]
    tw = set(re.findall(r"[a-z]{4,}", title.lower()))
    for s in sentences:
        s = s.strip()
        n = len(s.split())
        if n < 8 or n > max_words or BOILERPLATE.search(s):
            continue
        words = set(re.findall(r"[a-z]{4,}", s.lower()))
        if tw and words and len(words & tw) / len(words) > 0.6:
            continue
        return s
    return None


def build_claims(rec: dict, snap: dict, today: dt.date) -> list[dict]:
    """Return the claim ledger. Each claim is a single checkable statement."""
    if rec.get("editorial_brief"):
        import copy
        return copy.deepcopy(rec["editorial_brief"]["claims"])
    C: list[dict] = []
    from .grants import clean_agency
    agency = clean_agency(rec.get("agency_name")) or ""
    top = rec.get("top_agency")
    display_agency = agency or top or ""

    def add(key, statement, values, *fields):
        C.append({"key": key, "statement": statement, "values": values, "source": _src(rec, snap, *fields)})

    agency_fields = ("agency_name", "agency_code") if agency else ("top_agency",)
    add("identity",
        f"Grants.gov lists \"{rec['title']}\" as funding opportunity {rec.get('number') or rec['opportunity_id']}.",
        {"title": rec["title"], "number": rec.get("number"), "opportunity_id": rec["opportunity_id"]},
        "title", "number")
    if display_agency:
        add("agency", f"The listing agency is {display_agency}.",
            {"agency": display_agency, "agency_code": rec.get("agency_code"), "parent_agency": top},
            *agency_fields)
    if top and top != display_agency:
        add("parent_agency", f"The listing agency is part of the {top}.",
            {"parent_agency": top, "agency_code": rec.get("agency_code")}, "top_agency")
    if rec.get("status"):
        add("status", f"The opportunity status on Grants.gov is \"{rec['status']}\".",
            {"status": rec["status"]}, "status")
    od = parse_date(rec.get("open_date"))
    if od:
        add("posted", f"Grants.gov lists the posting date as {human_date(od)}.",
            {"date": od.isoformat()}, "open_date")
    cd = parse_date(rec.get("close_date"))
    if rec.get('application_deadline_policy'):
        policy=rec['application_deadline_policy'];cd=parse_date(policy.get('next_new_application_date'))
    if cd and cd >= today:
        deadline_statement=(f"The NIH full announcement sets the next new-application deadline as {human_date(cd)} at 5:00 PM applicant organization local time." if rec.get('application_deadline_policy') else f"Grants.gov lists the close date as {human_date(cd)}.")
        add("deadline", deadline_statement,
            {"date": cd.isoformat(), "days_left_at_build": (cd - today).days}, 'application_schedule' if rec.get('application_deadline_policy') else 'close_date')
    if rec.get('publisher_deadline'):
        deadline=rec['publisher_deadline'];meta=rec['announcement_source'];date=human_date(parse_date(deadline['date']))
        C.append({'key':'full_proposal_deadline','statement':f"Full proposal deadline: {date}, due by 5 p.m. submitter's local time.",'values':deadline,'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Full NSF proposal deadline header and explicit/annual date rule'],'clock_quote':deadline['clock_quote'],'date_basis':deadline['date_basis']}})
    lo, hi = rec.get("award_floor"), rec.get("award_ceiling")
    if rec.get('project_budget_unconfirmed'):lo=hi=None
    if rec.get('project_budget_scope'):
        lo=hi=None
        budget=rec['project_budget_scope'];meta=rec['announcement_source'];classes=budget['classes']
        statement='; '.join(c['name']+' project total budget up to '+money(c['total_project_budget_usd'])+', duration up to '+str(c['max_years'])+' years' for c in classes)+'.'
        C.append({'key':'project_budget','statement':statement,'values':{'classes':classes,**{c['name']+'_max_years':c['max_years'] for c in classes}},
                  'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Full NSF primary Pilot/Implementation project classes'],'exact_quotes':budget['source_quotes']}})
    if rec.get('budget_scope'):
        lo=hi=None
        budget=rec['budget_scope'];meta=rec['announcement_source']
        C.append({'key':'phase_budget','statement':budget['quote'],'values':{'quote':budget['quote'],'annual_direct_cost_limits':budget['phases']},
                  'source':{'url':meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Full NIH Award Budget: annual phase direct costs']}})
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
        add("expected_awards", f"Grants.gov lists {int(n)} expected award{'s' if int(n) != 1 else ''}.",
            {"expected_number_of_awards": int(n)}, "expected_number_of_awards")
    conditions=rec.get('publisher_eligibility')
    if conditions:
        meta=rec['announcement_source']
        for key,field in [('proposer_restriction','restriction_quote'),('proposer_policy','policy_reference_quote'),('proposal_cap','proposal_cap_quote')]:
            quote=conditions.get(field)
            if quote:
                C.append({'key':key,'statement':quote,'values':{'quote':quote},'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Full NSF IV. Eligibility Information: '+field]}})
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
    q = purpose_excerpt(rec.get("description") or "", title=rec.get("title", ""))
    if q:
        add("purpose_quote", f"The official synopsis says: \"{q}\"", {"quote": q}, "description")
        C[-1]['source']['excerpt']={'text':q,'start':rec['description'].find(q),'end':rec['description'].find(q)+len(q),'basis':'Contiguous normalized synopsis.description; raw snapshot remains linked by hash'}
    steps = rec.get('submission_steps')
    if steps:
        first, full = steps['Grants.gov'], steps['JustGrants']
        meta = rec['submission_steps_source']
        C.append({'key': 'submission_steps',
                  'statement': f"The official NOFO sets the Grants.gov deadline as {human_date(parse_date(first['date']))} at {first['time']} ET and the full JustGrants application deadline as {human_date(parse_date(full['date']))} at {full['time']} ET.",
                  'values': {'grants_date': first['date'], 'full_date': full['date'], 'grants_time': first['time'], 'full_time': full['time']},
                  'source': {'url': meta['url'], 'snapshot_file': meta['file'], 'snapshot_sha256': meta['sha256'],
                             'fields': ['PDF page 1 explicit Grants.gov and JustGrants deadlines']}})
    if rec.get("primary_conditions"):
        from .structured_script import claims as primary_claims
        C+=primary_claims(rec)
    if rec.get('source_conditions_unconfirmed') or rec.get('track_conditions'):
        withheld={'deadline','full_proposal_deadline','award_range','award_ceiling','total_funding','expected_awards','cost_sharing','eligibility','eligibility_note','eligibility_restricted','proposer_restriction','proposer_policy','proposal_cap','submission_steps','project_budget','phase_budget'}
        C=[c for c in C if c['key'] not in withheld]
        meta=rec.get('announcement_source') or {**snap,'url':rec['source_url']}
        C.append({'key':'source_review_status','statement':'Funding, eligibility and submission conditions require full announcement review. No applicant qualification or funding amount is established by this draft.',
                  'values':{'review_complete':False},'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Local source-validation result: typed conditions unsupported; not an agency eligibility claim']}})
    if rec.get('track_conditions'):
        from .track_script import claims as track_claims
        C+=track_claims(rec['track_conditions'])
        for claim in C:
            if claim['key']=='source_review_status':claim['statement']='Track-specific source facts are recorded. Remaining linked-policy and partner-specific conditions, and individual applicant qualification, are not established.'
    if rec.get('source_dependencies'):
        from .source_dependencies import claims as dependency_claims
        C+=dependency_claims(rec['source_dependencies'])
        if not any(c['key']=='source_review_status' for c in C):
            meta=rec['announcement_source']
            C.append({'key':'source_review_status','statement':'Source overview review complete','values':{'overview_review_complete':True},'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Local linked-source review result; no individual eligibility decision']}})
        for claim in C:
            if claim['key']=='source_review_status':claim['values']={'overview_review_complete':True};claim['statement']='Primary track facts and linked policy conditions needed for a neutral overview were reviewed as of the saved source snapshot. Individual eligibility and future policy versions are not established.'
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
BANNED = [r"\byou\s+(?:can|may|are able to)\s+apply\b", r"\bfree money\b", r"\bguarantee[ds]?\b", r"\byou qualify\b", r"\byou(?:'re| are) eligible\b",
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
                if k in {"award_floor","award_ceiling","estimated_total_program_funding"}:
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
    return any(abs(v - a) <= 0.005 for a in allowed if a > 0)


def validate_script(script: dict, claims: list[dict], *, _structure=True, _metadata=True) -> list[str]:
    """Finite structure/numeric/source-binding checks; no semantic or production approval."""
    errs: list[str] = []
    by_key = {c["key"]: c for c in claims}
    reconciled=script.get("editorial_contract")=="SOCIAL_FACT_RECONCILED_SOURCE_V1"
    if _structure and reconciled:
        from .source_materialization import validate
        errs.extend(validate(script,claims))
    if _structure and script.get('editorial_contract')=='SOCIAL_SOURCE_DECISION_REEL_V1':
        required={'identity','tracks_track_order','track_E_eligibility','track_E_submission','tracks_TP_prior_funding','tracks_lead_organizations','tracks_PI_appointments','source_review_status'}
        if not required.issubset(by_key):errs.append('TTP source-decision contract requires its original source-scoped ledger')
        roles={s.get('role'):s for s in script.get('segments',[])}
        if script.get('decision_profile')=='nsf_ttp_prior_award_decision_v2' and ('purpose_quote' not in by_key or 'purpose_quote' not in roles.get('hook',{}).get('claim_keys',[])):errs.append('Decision hook must keep its source-bound research-to-practice purpose')
        for role,keys in [('hook',{'identity','tracks_track_order'}),('track_E',{'track_E_eligibility','track_E_submission'}),('tracks_TP',{'tracks_TP_prior_funding'}),('who',{'tracks_lead_organizations','tracks_PI_appointments'}),('cta',{'identity','source_review_status'})]:
            if not keys.issubset(roles.get(role,{}).get('claim_keys',[])):errs.append('Decision scene loses required evidence binding: '+role)
        for key,ids in [('track_E_eligibility',{'NSF TTP-E'}),('track_E_submission',{'NSF TTP-E'}),('tracks_TP_prior_funding',{'NSF TTP-T','NSF TTP-P'})]:
            if key in by_key and set(by_key[key].get('values',{}).get('track_ids',[]))!=ids:errs.append('Decision ledger belongs to another track scope: '+key)
    if _structure and any(c.get('values',{}).get('track_ids') for c in claims):
        from .track_script import validate_scopes
        errs+=validate_scopes(script,claims)
    segs = script.get("segments") or []
    if _structure and not (4 <= len(segs) <= 10):
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
        eligibility_assertions=re.finditer(r'\b(?P<category>individuals|individual applicants|people|small businesses)\s+(?:(?:can|may)\s+apply|are\s+eligible(?:\s+to\s+apply)?)\b',text,re.I)
        cited_types=[str(value).strip().lower() for claim in cited if claim.get('key')=='eligibility' or claim.get('key')=='listing_applicant_types' and (claim.get('conversion_origin') or {}).get('rule')=='grants_saved_field_typed_v1'
                     for value in claim.get('values',{}).get('applicant_types',[])]
        for assertion in eligibility_assertions:
            category=assertion.group('category').lower()
            prefix='small businesses' if category=='small businesses' else 'individuals'
            listed=any(value.startswith(prefix) or value.startswith('unrestricted') for value in cited_types)
            verbatim=False
            for claim in cited:
                quote=claim.get('values',{}).get('quote') if claim.get('key')=='eligibility_note' or claim.get('key')=='listing_applicant_eligibility_desc' and (claim.get('conversion_origin') or {}).get('rule')=='grants_saved_field_typed_v1' else None
                if isinstance(quote,str) and quote:
                    verbatim=verbatim or any(match.start()<=assertion.start() and assertion.end()<=match.end()
                                              for match in re.finditer(re.escape(quote),text))
            if not listed and not verbatim:
                errs.append(f'{tag}: applicant assertion for {category} not supported by cited eligibility types or verbatim source conditions')
        if not s.get("voiceover", "").strip():
            errs.append(f"{tag}: empty voiceover")
        match_claims=list(re.finditer(r'(?P<no>\bno\s+)?\bcost\s+(?:match|sharing)\s+(?:is\s+)?(?P<not>not\s+)?required',text,re.I))
        for assertion in match_claims:
            if 'cost_sharing' not in keys:
                errs.append(f'{tag}: cost match assertion lacks cited cost_sharing claim')
            else:
                expected=by_key.get('cost_sharing',{}).get('values',{}).get('cost_sharing_required')
                said_required=not bool(assertion.group('no') or assertion.group('not'))
                if not isinstance(expected,bool) or expected!=said_required:
                    errs.append(f'{tag}: cost match assertion contradicts cited requirement')
        from .term_guard import errors as typed_term_errors
        errs.extend(tag+': '+e for e in typed_term_errors(text,cited))
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
        count_number=r'(\d[\d,]*(?:\.\d+)?)'
        count_patterns=[r'\b(?:expects?|anticipates?|estimates?)\s+(?:to\s+(?:make|issue)\s+)?(?:about\s+|up to\s+)?'+count_number+r'\s+awards?\b',
                        r'(?<![\w$])'+count_number+r'\s+expected\s+awards?\b',
                        r'(?<![\w$])'+count_number+r'\s+awards?\s+(?:are\s+)?expected\b',
                        r'\bexpected\s+(?:number\s+of\s+)?awards?\s*(?:is|:)?\s*'+count_number+r'\b']
        count_assertions=[match for pattern in count_patterns for match in re.finditer(pattern,text,re.I)]
        allowed_counts={float(c['values']['expected_number_of_awards']) for c in cited if 'expected_number_of_awards' in c.get('values',{})}
        bad_counts=set()
        for assertion in count_assertions:
            count=_f(assertion.group(1));verbatim=False
            for claim in cited:
                quote=claim.get('values',{}).get('quote')
                if isinstance(quote,str) and quote:
                    verbatim=verbatim or any(match.start()<=assertion.start() and assertion.end()<=match.end()
                                              for match in re.finditer(re.escape(quote),text))
            if count not in allowed_counts and not verbatim:bad_counts.add(count)
        for count in sorted(bad_counts):
            errs.append(f'{tag}: expected award count {count:,.0f} not in cited expected_awards claim')
        if any(c['key']=='primary_budget' for c in cited) and re.search(r'\bannual(?:ly)?\b|\bper\s+(?:year|month|person|individual)\b',text,re.I):
            errs.append(f'{tag}: total project request misrepresented as annual or personal funding')
        if any(c['key']=='primary_applicant' for c in cited) and re.search(r'\b(?:people|individuals|members)\s+(?:are eligible|qualify|can apply|may apply)\b',text,re.I):
            errs.append(f'{tag}: individual group membership does not establish organization eligibility')
        if any(c['key']=='project_budget' for c in cited) and re.search(r'\bper\s+(?:award|person|year|month|recipient)|\bannual(?:ly)?\b',text,re.I):
            errs.append(f'{tag}: project-class total budget misrepresented as per-award/personal/annual amount')
        if any(c['key']=='phase_budget' for c in cited):
            spans=[m.span() for c in cited if c['key']=='phase_budget' for m in re.finditer(re.escape(c['values']['quote']),text)]
            for m in list(MONEY_RE.finditer(text))+list(MONEY_WORD_RE.finditer(text)):
                if not any(start<=m.start() and m.end()<=end for start,end in spans):
                    errs.append(f'{tag}: annual phase/direct-cost budget must retain its intact scoped source quote')
        totals={float(c['values']['estimated_total_program_funding']) for c in cited if 'estimated_total_program_funding' in c.get('values',{})}
        awards={float(c['values'][k]) for c in cited for k in ('award_floor','award_ceiling') if k in c.get('values',{})}
        for match in list(MONEY_RE.finditer(text)) + list(MONEY_WORD_RE.finditer(text)):
            values=extract_tokens(match.group(0))['money']
            context=text[max(0,match.start()-35):min(len(text),match.end()+35)]
            if values and values[0] in totals and values[0] not in awards and re.search(r'\b(?:per|each)\s+(?:award|applicant|person|recipient|organization)\b',context,re.I):
                errs.append(f'{tag}: program total misrepresented as per-applicant payment')
        if re.search(r'\b(?:you|people|individuals|everyone|anyone)\s+(?:(?:can|will|may)\s+)?(?:get|receive|collect|claim)\b.{0,40}(?:\$|\bdollars\b)',text,re.I):
            errs.append(f'{tag}: personal payment promise is not applicant eligibility')
        if VAGUE_RE.search(text):
            errs.append(f"{tag}: vague or spelled-out quantity: '{VAGUE_RE.search(text)[0]}'")
        for pat in BANNED:
            if re.search(pat, text, re.I):
                # A cited unknown balance can say "no guaranteed result"; it is
                # not an affirmative promise. Reuse the existing finite scope
                # detector and keep bare/conditional/mixed/double negatives held.
                if pat==r"\bguarantee[ds]?\b" and 'individual_unknown' in keys:
                    from .narrative_checks import guarantee_mentions
                    mentions=guarantee_mentions(text)
                    if mentions and len(mentions)==len(re.findall(pat,text,re.I)) and all(m['state']=='negated' for m in mentions):continue
                errs.append(f"{tag}: banned phrasing /{pat}/")
        if re.search(r"\b(just posted|brand[- ]new|newly posted)\b", text, re.I) and "posted" not in keys:
            errs.append(f"{tag}: recency claim without the 'posted' claim")
    if _structure and segs:
        last = " ".join([segs[-1].get("voiceover", "")] + [str(v) for v in (segs[-1].get("on_screen") or {}).values()])
        if script.get("editorial_contract") not in {"SOCIAL_BENEFIT_REEL_V1","SOCIAL_FACT_RECONCILED_SOURCE_V1"} and (not re.search(r"grants\.gov", last, re.I) or not re.search(r"\b(check|verify|confirm|read|official)\w*", last, re.I)):
            errs.append("last segment must point to Grants.gov and tell viewers to check the official listing")
    words = sum(len((s.get("voiceover") or "").split()) for s in segs)
    short=script.get("editorial_contract") in {"SOCIAL_BENEFIT_REEL_V1","SOCIAL_SOURCE_DECISION_REEL_V1"}
    if _structure and short:
        from .scene_coherence import validate as validate_coherence
        errs.extend(validate_coherence(script))
        if not 25<=words<=50:errs.append("Short benefit narration must stay within25..50words and measured20..30second budget")
    if _structure and not short and not reconciled and not (55 <= words <= 170):
        errs.append(f"narration length {words} words outside 55..170 (~20-60 s)")
    if _metadata:
        from urllib.parse import urlsplit
        def canonical_url(value):
            parsed=urlsplit(value)
            host=parsed.netloc.lower()
            if host.startswith('www.'):host=host[4:]
            return parsed._replace(netloc=host,fragment='').geturl().rstrip('/')
        known_urls=set()
        for claim in claims:
            source=claim.get('source') or {}
            for item in [source]+list(source.get('field_sources') or []):
                if item.get('url'):
                    try:known_urls.add(canonical_url(item['url']))
                    except (ValueError,TypeError,AttributeError):errs.append('Claim source URL is invalid')
        if script.get('editorial_contract') in {'SOCIAL_SOURCE_DECISION_REEL_V1','SOCIAL_FACT_RECONCILED_SOURCE_V1'}:
            # Literal URLs inside exact source-bound quotations are references,
            # not newly fetched/verified destinations or new factual assertions.
            for detail in script.get('description_details') or []:
                claim=by_key.get(detail.get('claim_key'))
                if claim and detail.get('text')==claim.get('statement') and detail.get('source')==claim.get('source'):
                    for url in re.findall(r'https?://[^\s<>"\']+',detail['text'],re.I):
                        known_urls.add(canonical_url(url.rstrip('.,);]')))
        for field in ('title','hook','description','source_note'):
            value=script.get(field)
            if value is None or value=='':continue
            if not isinstance(value,str):
                errs.append(field+': expected text');continue
            pseudo={'segments':[{'voiceover':value,'on_screen':{},'claim_keys':list(by_key)}]}
            issues=validate_script(pseudo,claims,_structure=False,_metadata=False)
            errs.extend(field+': '+issue for issue in issues)
            for url in re.findall(r'https?://[^\s<>"\']+',value,re.I):
                url=url.rstrip('.,);]')
                try:known=canonical_url(url) in known_urls
                except (ValueError,TypeError,AttributeError):known=False
                if not known:errs.append(field+': source URL is not present in the claim ledger')
    return errs



def purpose_excerpt(text, title=''):
    """Prefer an exact short objective clause over award-duration boilerplate."""
    # Prefer the actual primary purpose before an enabling-benefit clause. No word
    # truncation: keep an exact complete objective clause and reject conditional
    # sentences rather than dropping qualifications beyond the selected clause.
    for sentence in source_sentences(text or '')[:5]:
        match=re.search(r"\b(?:This (?:program|solicitation)|The program)\s+(?:seeks|aims)\s+(to\s+[^.!?]{15,600}?)\s+to\s+(?:enable|transform|advance|improve)\b",sentence,re.I)
        if match and not re.search(r"\b(?:if|unless|only|except|provided|subject to|contingent|eligible|eligibility|must|not|cannot)\b",sentence,re.I):
            quote=match.group(1).strip()
            if 8<=len(quote.split())<=32 and not re.search(r'https?://',quote,re.I):return quote
    # Contiguous source substring: no paraphrase, new target group or synthesized claim.
    for sentence in source_sentences(text or ''):
        match=re.search(r'\bto\s+(?:establish|operate|provide|support|improve|expand|develop|fund|reduce|increase|assist)\b',sentence,re.I)
        if not match:continue
        guarded=bool(re.search(r'\b(?:if|unless|only|except|provided|subject to|contingent|eligible|eligibility|must|not|cannot)\b',sentence,re.I))
        # A contiguous suffix can still erase who/where/when a benefit applies.
        # Keep the whole qualified sentence, or decline the excerpt if too long.
        quote=(sentence if guarded else sentence[match.start():]).strip()
        if guarded and not (5<=len(quote.split())<=45):continue
        if 5<=len(quote.split())<=45 and not re.search(r'https?://|passcode|password',quote,re.I):return quote
    fallback=first_sentence(text,title=title)
    if fallback and re.search(r'\b(?:award|base year|option years|project period|deadline|applications? close|cost shar)\b',fallback,re.I) and not re.search(r'\b(?:deliver|provide|support|train|improve|reduce|develop|prevent|assist)\b',fallback,re.I):return None
    return fallback

"""Existing product dispatcher: explicit ollama uses local_editorial.propose.
Template composition stays explicit; local adapter failures never fall back.
Historical remote helpers below are not an authorized local product route.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from .claims import validate_script
from .common import PipelineError, human_date, money, parse_date

SHORT_APPLICANT = [
    (r"^unrestricted", "Unrestricted (any applicant type)"),
    (r"^small businesses?", "Small businesses"),
    (r"^individuals", "Individuals"),
    (r"^nonprofits having a 501\(c\)\(3\)", "Nonprofits (501(c)(3), excluding colleges)"),
    (r"^nonprofits that do not have a 501\(c\)\(3\)", "Other nonprofits (excluding colleges)"),
    (r"^private institutions of higher education", "Private colleges & universities"),
    (r"^public and state controlled institutions of higher education", "Public colleges & universities"),
    (r"^state governments", "State governments"),
    (r"^county governments", "County governments"),
    (r"^city or township governments", "City & township governments"),
    (r"^special district governments", "Special districts"),
    (r"^independent school districts", "School districts"),
    (r"^native american tribal governments", "Federally recognized Tribal governments"),
    (r"^native american tribal organizations", "Tribal organizations"),
    (r"^public housing authorities", "Public housing authorities"),
    (r"^for profit organizations other than small businesses", "For-profit companies"),
]


def short_applicant(a: str) -> str:
    for pat, short in SHORT_APPLICANT:
        if re.search(pat, a, re.I):
            return short
    return a if len(a) <= 48 else a[:45].rsplit(" ", 1)[0] + "…"


def _agency_phrase(name: str) -> str:
    if not name:
        return ""
    return name if (name.isupper() or name.startswith("NASA")) else "the " + name


def template_script(rec: dict, claims: list[dict], audience="general_us") -> dict:
    from .benefit_reel import make
    return make(rec,claims,audience)

def reference_script(rec: dict, claims: list[dict]) -> dict:
    if rec.get('track_conditions'):
        from .track_script import script
        return script(rec,claims)
    if rec.get("primary_conditions"):
        from .structured_script import script
        return script(rec,claims)
    by = {c["key"]: c for c in claims}
    v = lambda k, f: (by.get(k) or {}).get("values", {}).get(f)
    agency = v("agency", "agency")
    segs = []

    hi = v("award_range", "award_ceiling") or v("award_ceiling", "award_ceiling")
    tot = v("total_funding", "estimated_total_program_funding")
    money_key = "award_range" if "award_range" in by else ("award_ceiling" if "award_ceiling" in by else None)
    # 1 hook
    if 'project_budget' in by:
        segs.append(dict(role='hook',visual='hook',voiceover="The official program has separate project-budget classes.",
                         on_screen={'kicker':'PROJECT FUNDING','headline':'Separate project-budget classes','sub':rec['title']},claim_keys=['project_budget','identity']))
    elif 'phase_budget' in by:
        segs.append(dict(role='hook',visual='hook',voiceover=by['phase_budget']['statement'],
                         on_screen={'kicker':'NIH PHASE BUDGETS','headline':'Annual direct-cost limits','sub':'UG3 and UH3 have separate limits'},claim_keys=['phase_budget']))
    elif hi:
        segs.append(dict(role="hook", visual="hook",
                         voiceover=f"Up to {money(hi)} per award" + (f", from {_agency_phrase(agency)}." if agency else "."),
                         on_screen={"kicker": "FEDERAL FUNDING · UP TO", "big": money(hi), "headline": "per award",
                                    "sub": agency or ""},
                         claim_keys=[money_key] + (["agency"] if agency else [])))
    elif tot:
        segs.append(dict(role="hook", visual="hook",
                         voiceover=f"Estimated total program funding is {money(tot)}" + (f", from {_agency_phrase(agency)}." if agency else "."),
                         on_screen={"kicker": "FEDERAL FUNDING", "big": money(tot), "headline": "estimated total",
                                    "sub": agency or ""},
                         claim_keys=["total_funding"] + (["agency"] if agency else [])))
    else:
        if not rec.get('source_conditions_unconfirmed'):raise PipelineError("template writer needs an award amount or total funding claim")
        segs.append(dict(role='hook',visual='hook',voiceover='A source-backed program overview, with unresolved conditions kept out of the claims.',on_screen={'kicker':'RESEARCH DRAFT','headline':'Conditions need review','sub':rec['title']},claim_keys=['identity','source_review_status']))

    # 2 what
    title = rec["title"]
    inst = (v("instrument", "funding_instruments") or [None])[0]
    spoken = f"The program: {title}." if len(title.split()) <= 14 else "Here is the official program title."
    if inst:
        spoken = f"It's a {inst.lower()}. " + spoken
    segs.append(dict(role="what", visual="title", voiceover=spoken,
                     on_screen={"kicker": "THE PROGRAM", "headline": title,
                                "sub": f"Opportunity {rec.get('number') or rec['opportunity_id']}"},
                     claim_keys=["identity"] + (["instrument"] if inst else [])))

    if 'source_review_status' in by:
        segs.append(dict(role='source_review',visual='quote',voiceover=by['source_review_status']['statement'],on_screen={'kicker':'REVIEW REQUIRED','headline':'Full conditions not established','sub':'No eligibility or funding promise'},claim_keys=['source_review_status']))

    # 3 money detail
    lo = v("award_range", "award_floor")
    n = v("expected_awards", "expected_number_of_awards")
    if 'project_budget' in by:
        budget=by['project_budget'];classes=budget['values']['classes']
        vo=' '.join(c['name']+' projects: total budget up to '+money(c['total_project_budget_usd'])+' over up to '+str(c['max_years'])+' years.' for c in classes)
        segs.append(dict(role='money',visual='list',voiceover=vo,on_screen={'kicker':'TOTAL PROJECT BUDGET LIMITS','headline':'\n'.join(c['name']+': '+money(c['total_project_budget_usd'])+' / up to '+str(c['max_years'])+' years' for c in classes),'sub':'Caps vary by project class'},claim_keys=['project_budget']))
    elif tot and (lo or hi):
        vo = f"Estimated total funding is {money(tot)}"
        vo += f", with individual awards from {money(lo)} to {money(hi)}." if lo else f", with awards up to {money(hi)}."
        keys = ["total_funding", money_key]
        sub = f"Awards: {money(lo)} – {money(hi)}" if lo else f"Up to {money(hi)} per award"
        if n:
            vo += f" Grants.gov expects {n} award{'s' if n != 1 else ''}."
            keys.append("expected_awards")
            sub += f" · {n} expected award{'s' if n != 1 else ''}"
        segs.append(dict(role="money", visual="stat", voiceover=vo,
                         on_screen={"kicker": "THE MONEY", "big": money(tot), "headline": "estimated total funding",
                                    "sub": sub}, claim_keys=keys))
    elif lo and hi:
        segs.append(dict(role="money", visual="stat",
                         voiceover=f"Individual awards range from {money(lo)} to {money(hi)}.",
                         on_screen={"kicker": "THE MONEY", "big": f"{money(lo)} – {money(hi)}",
                                    "headline": "per award", "sub": ""}, claim_keys=["award_range"]))

    # 4 who
    if 'proposer_restriction' in by and 'proposer_policy' in by:
        segs.append(dict(role='who',visual='quote',voiceover=by['proposer_restriction']['statement']+" Check eligible proposer categories in NSF's PAPPG, Chapter I.E.",
                         on_screen={'kicker':'CHECK PROPOSER ELIGIBILITY','headline':by['proposer_restriction']['statement'],'sub':'Proposer categories: NSF PAPPG, Chapter I.E.'},claim_keys=['proposer_restriction','proposer_policy']))
    elif "eligibility" in by:
        types = list(dict.fromkeys(short_applicant(a) for a in v("eligibility", "applicant_types")))
        prio = [x[1] for x in SHORT_APPLICANT]          # broad, familiar audiences first
        types.sort(key=lambda t: prio.index(t) if t in prio else len(prio))
        spoken = [t if i == 0 or t[:2].isupper() else t[0].lower() + t[1:] for i, t in enumerate(types[:4])]
        if len(types) > 4:
            vo = "Who can apply? " + ", ".join(spoken) + ", and other listed types."
        else:
            vo = "Who can apply? " + _join(spoken) + "."
        keys = ["eligibility"]
        if v("eligibility", "has_additional_conditions") or "eligibility_note" in by:
            vo += " Read the eligibility details before applying."
        segs.append(dict(role="who", visual="list", voiceover=vo,
                         on_screen={"kicker": "WHO CAN APPLY", "headline": "\n".join(types[:6]),
                                    "sub": "Eligibility details: official listing"}, claim_keys=keys))
    elif "eligibility_note" in by:
        q = v("eligibility_note", "quote")
        segs.append(dict(role="who", visual="quote",
                         voiceover=f"Eligibility is restricted. The listing says: {q}",
                         on_screen={"kicker": "WHO CAN APPLY", "headline": f"“{q}”", "sub": "From the official listing"},
                         claim_keys=["eligibility_note"] + (["eligibility_restricted"] if "eligibility_restricted" in by else [])))
    elif "eligibility_restricted" in by:
        segs.append(dict(role="who", visual="list",
                         voiceover="Eligibility is restricted. The official listing defines who can apply, so read that section first.",
                         on_screen={"kicker": "WHO CAN APPLY", "headline": "Restricted eligibility",
                                    "sub": "See “Additional Information on Eligibility”"},
                         claim_keys=["eligibility_restricted"]))

    if 'proposal_cap' in by:
        segs.append(dict(role='restriction',visual='quote',voiceover=by['proposal_cap']['statement'],
                         on_screen={'kicker':'PROPOSAL LIMIT','headline':by['proposal_cap']['statement'],'sub':'Full NSF eligibility section'},claim_keys=['proposal_cap']))

    # 5 purpose
    q = v("purpose_quote", "quote")
    if q and len(q.split()) <= 32:
        segs.append(dict(role="purpose", visual="quote", voiceover=f"In the agency's words: {q}",
                         on_screen={"kicker": "FROM THE SYNOPSIS", "headline": f"“{q}”", "sub": "Official Grants.gov synopsis"},
                         claim_keys=["purpose_quote"]))

    # 6 deadline
    if "deadline" in by:
        d = parse_date(v("deadline", "date"))
        vo = (by["deadline"]["statement"] if rec.get("application_deadline_policy") else f"The Grants.gov listing closes {human_date(d)}. Check the full announcement for all submission steps.")
        keys = ["deadline"]
        if 'submission_steps' in by:
            steps = by['submission_steps']['values']
            vo = f"Submit the Grants.gov step by {human_date(parse_date(steps['grants_date']))}. The full JustGrants application is due {human_date(parse_date(steps['full_date']))}."
            keys.append('submission_steps')
        sub = ""
        cs = v("cost_sharing", "cost_sharing_required")
        if cs is not None:
            vo += " A cost match is required." if cs else " No cost match is required."
            sub = "Cost match required" if cs else "No cost match required"
            keys.append("cost_sharing")
        if 'submission_steps' in by:
            sub = "Full JustGrants application: " + human_date(parse_date(by['submission_steps']['values']['full_date'])) + ("\n" + sub if sub else '')
        segs.append(dict(role="deadline", visual="date", voiceover=vo,
                         on_screen={"kicker": "NEXT NEW APPLICATION" if rec.get("application_deadline_policy") else "GRANTS.GOV STEP", "big": d.strftime("%b ") + str(d.day),
                                    "headline": str(d.year), "sub": sub}, claim_keys=keys))

    # 7 cta / source
    segs.append(dict(role="cta", visual="source",
                     voiceover="Search the opportunity number on Grants.gov, and check the official listing before you apply.",
                     on_screen={"kicker": "CHECK THE OFFICIAL LISTING", "headline": rec.get("number") or rec["opportunity_id"],
                                "sub": "grants.gov · verify details before applying"},
                     claim_keys=["identity"]))
    for i, s in enumerate(segs, 1):
        s["id"] = f"s{i}"
    script = {
        "writer": "template_v1",
        "title": _clip(f"{money(hi) if hi else ('NSF project classes:' if 'project_budget' in by else ('NIH phase budgets:' if 'phase_budget' in by else (money(tot) if tot else 'Source review:')))} federal funding: {title}", 140),
        "hook": segs[0]["voiceover"],
        "segments": segs,
        "description": _description(rec, by),
        "source_note": f"Source: Grants.gov opportunity {rec.get('number') or rec['opportunity_id']} ({rec['source_url']}). "
                       "Details can change; always verify the official listing before applying.",
    }

    if rec.get('project_budget_scope') and rec.get('publisher_deadline'):
        from .compact_script import compact_project_script
        script=compact_project_script(script,rec,claims)
    return script


def _join(xs):
    xs = list(xs)
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + (", and " if len(xs) > 2 else " and ") + xs[-1]


def _clip(s, n):
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def _description(rec, by):
    lines = [rec["title"], ""]
    for k in ("source_review_status", "agency", "purpose_quote", "project_budget", "phase_budget", "award_range", "award_ceiling", "total_funding", "expected_awards", "full_proposal_deadline", "deadline", "submission_steps", "proposer_restriction", "proposer_policy", "proposal_cap", "eligibility",
              "eligibility_note"):
        if k in by:
            lines.append("• " + by[k]["statement"])
    lines += ["", f"Official listing: {rec['source_url']}", "Always verify current details on Grants.gov before applying.",
              "#grants #federalfunding" + (" #smallbusiness" if any(a.lower().startswith('small businesses') for a in rec.get('applicant_types', [])) else '')]
    return "\n".join(lines)


# ------------------------------------------------------------------- LLM writer

SYSTEM = """You write short vertical-video (Reel) scripts about U.S. federal funding opportunities.
You may ONLY use the facts in the supplied claim ledger. Hard rules:
- Every segment must list the claim_keys it relies on; every amount, date and number you write must appear in those claims.
- Write all amounts and numbers with digits exactly as in the claims (e.g. $650,000, $24.75 million). No rounding, no "about", no spelled-out numbers, no "thousands of".
- Never tell the viewer they qualify or are eligible; describe eligibility only as the claims state it.
- No hype that changes meaning: no "free money", "guaranteed", "act now", "last chance", "secret".
- Do not say "just posted" or "new" unless you cite the 'posted' claim.
- The last segment must send viewers to Grants.gov and tell them to check the official listing before applying.
- 5 to 8 segments, 70 to 150 spoken words in total. Plain, energetic, clear American English.
- on_screen text is short: kicker <= 4 words (uppercase), big <= 14 characters (a number or date), headline <= 12 words, sub <= 10 words.
Return the script by calling submit_reel_script."""

SCHEMA = {
    "type": "object",
    "required": ["title", "segments", "description"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "segments": {
            "type": "array", "minItems": 4, "maxItems": 9,
            "items": {
                "type": "object",
                "required": ["role", "visual", "voiceover", "on_screen", "claim_keys"],
                "properties": {
                    "role": {"type": "string", "enum": ["hook", "what", "money", "who", "purpose", "deadline", "cta"]},
                    "visual": {"type": "string", "enum": ["hook", "title", "stat", "list", "quote", "date", "source"]},
                    "voiceover": {"type": "string"},
                    "on_screen": {"type": "object", "properties": {
                        "kicker": {"type": "string"}, "big": {"type": "string"},
                        "headline": {"type": "string"}, "sub": {"type": "string"}}},
                    "claim_keys": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                },
            },
        },
    },
}


def llm_available(cfg: dict) -> tuple[bool, str]:
    llm = cfg.get("llm", {})
    if not llm.get("allow_spend"):
        return False, "llm.allow_spend is false (owner has not authorized spend)"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False, "ANTHROPIC_API_KEY not present"
    return True, "ok"


def _call_anthropic(cfg, messages):
    llm = cfg["llm"]
    body = {"model": llm.get("model", "claude-sonnet-5-5"), "max_tokens": int(llm.get("max_output_tokens", 2500)),
            "system": SYSTEM, "messages": messages,
            "tools": [{"name": "submit_reel_script", "description": "Submit the final Reel script.", "input_schema": SCHEMA}],
            "tool_choice": {"type": "tool", "name": "submit_reel_script"}}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    tool = next((c for c in data.get("content", []) if c.get("type") == "tool_use"), None)
    if not tool:
        raise PipelineError("LLM returned no tool_use block")
    return tool["input"], data.get("usage", {}), data.get("model")


def llm_script(rec: dict, claims: list[dict], cfg: dict, log: list) -> dict | None:
    ledger = [{"key": c["key"], "statement": c["statement"]} for c in claims]
    user = ("Claim ledger (the only facts you may use):\n" + json.dumps(ledger, indent=2) +
            f"\n\nOpportunity title: {rec['title']}\nOfficial number: {rec.get('number')}\n"
            "Write the strongest honest Reel script you can from these claims.")
    messages = [{"role": "user", "content": user}]
    max_calls = int(cfg["llm"].get("max_calls_per_run", 2))
    for attempt in range(max_calls):
        try:
            out, usage, model = _call_anthropic(cfg, messages)
        except Exception as e:
            log.append({"llm_attempt": attempt + 1, "error": str(e)[:500]})
            return None
        for i, s in enumerate(out.get("segments", []), 1):
            s["id"] = f"s{i}"
            s.setdefault("on_screen", {})
        errs = validate_script(out, claims)
        log.append({"llm_attempt": attempt + 1, "model": model, "usage": usage, "validation_errors": errs})
        if not errs:
            out["writer"] = f"llm:{model}"
            out["hook"] = out["segments"][0]["voiceover"]
            out["source_note"] = (f"Source: Grants.gov opportunity {rec.get('number') or rec['opportunity_id']} "
                                  f"({rec['source_url']}). Details can change; always verify the official listing before applying.")
            return out
        messages += [{"role": "assistant", "content": [{"type": "text", "text": json.dumps(out)}]},
                     {"role": "user", "content": "The validator rejected the script:\n- " + "\n- ".join(errs) +
                      "\nFix every problem and call submit_reel_script again."}]
    return None


def write_script(rec: dict, claims: list[dict], cfg: dict) -> tuple[dict, dict]:
    """Return (script, writer_report). Never returns an unvalidated script."""
    from .source_brief import adapt
    rec=adapt(rec,audience=cfg.get("selection",{}).get("audience","general_us"))
    from .audience_selection import require
    audience=cfg.get("selection",{}).get("audience","general_us")
    require(rec,audience)
    from .writer_contract import route,script_fields
    report = {"requested": cfg.get("writer", "auto"), "llm_log": [],"writer_route":route(cfg)}
    def finish(script):
        report['common_field_contract']=script_fields(script)
        if not report['common_field_contract']['common_fields_valid']:raise PipelineError('Common spoken/visible writer-field contract failed')
        return script,report
    mode = cfg.get("writer", "auto")
    if mode not in {'auto', 'template', 'llm', 'ollama'}:
        raise PipelineError(f'Unknown writer: {mode}')
    if cfg.get('llm', {}).get('allow_spend'):
        raise PipelineError('Paid providers are not authorized for this local Social route')
    if mode=='ollama':
        from .local_editorial import propose
        base=template_script(rec,claims,audience)
        candidate,evidence=propose(rec,claims,cfg,base)
        report.update(evidence)
        return finish(candidate)
    if rec.get("editorial_brief"):
        if mode in {"ollama","llm"}:
            raise PipelineError('Explicit model writer unavailable for this fixed reviewed composition; no reviewed alternate phrasing/order is implemented and no template substitution or model request was made')
        report.update(model_started=False,automation_kind='deterministic_source_bound_composition',model_skipped_reason='Fixed reviewed wording/order; no model-authored script or approved alternative bank is implemented')
        s=template_script(rec,claims,audience)
        errs=validate_script(s,claims)
        if errs:raise PipelineError("Reviewed brief failed grounding: "+"; ".join(errs))
        report["used"]=s["writer"]
        return finish(s)
    if mode == "ollama":
        if cfg.get("generation_hold"):
            # Preparation must select template explicitly; direct writer calls
            # cannot turn a saved operator hold into a local model request.
            raise PipelineError("Model writer held: "+str(cfg["generation_hold"]))
        from .ollama_writer import qwen_script
        result=qwen_script(template_script(rec, claims, audience), claims, cfg, report)
        if result.get('editorial_contract')!='SOCIAL_BENEFIT_REEL_V1':raise PipelineError('Model returned a legacy long-form structure; short synchronized contract required')
        return finish(result)
    if mode in ("auto", "llm"):
        ok, why = llm_available(cfg)
        report["llm_available"] = ok
        report["llm_reason"] = why
        if ok:
            s = llm_script(rec, claims, cfg, report["llm_log"])
            if s and s.get("editorial_contract")=="SOCIAL_BENEFIT_REEL_V1":
                report["used"] = s["writer"]
                return finish(s)
            if s:report["llm_log"].append({"editorial_rejected":"Legacy long-form structure cannot bypass short synchronized contract"})
            if mode == "llm":
                raise PipelineError("LLM writer failed validation and writer=llm forbids fallback")
        elif mode == "llm":
            raise PipelineError(f"writer=llm but {why}")
    s = template_script(rec, claims, audience)
    errs = validate_script(s, claims)
    if errs:
        raise PipelineError("template script failed grounding validation: " + "; ".join(errs))
    report["used"] = s["writer"]
    return finish(s)


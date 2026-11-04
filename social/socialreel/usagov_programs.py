"""Heading-bound program groups; exact facts and admission limits stay unchanged.

Format not checked live. Names below identify source headings, not benefit rules.
Unrecognized or ambiguous material remains page-wide; it is never guessed away.
"""
from __future__ import annotations

import re

from .common import PipelineError, slug
from .usagov_facts import _select_units

NAMES = {
    "liheap": re.compile(r"\bLIHEAP\b|\blow income home energy assistance program\b", re.I),
    "wap": re.compile(r"\bWAP\b|\bweatherization assistance program\b", re.I),
    "disconnected": re.compile(r"\butilit(?:y|ies)\b[^.!?]*\bdisconnect\w*\b|\bdisconnect\w*\b[^.!?]*\butilit(?:y|ies)\b", re.I),
}
ELIGIBILITY_HEADING = re.compile(r"^find out if you are eligible for (.+?)(?: and apply)?[.!?]?$", re.I)


def _names(text):
    return [name for name, pattern in NAMES.items() if pattern.search(text)]


def program_units(record, claims):
    """Recognize two or more explicit programs and own all facts below their headings.

    Named headings win. A prose section naming just one known program can label
    an otherwise generic heading and its descendants. Repeated headings for the
    same named program belong to the same group, regardless of HTML position.
    """
    roots = {}
    headings = {}
    for row in claims:
        for heading in row.get("locator", {}).get("heading_path", []):
            headings[heading["path"]] = heading
    for path, heading in headings.items():
        found = _names(heading["text"])
        generic = ELIGIBILITY_HEADING.fullmatch(heading["text"])
        if len(found) == 1:
            roots[path] = found[0]
        elif not found and generic:
            roots[path] = slug(generic[1], 64)
    for row in claims:
        path = row.get("locator", {}).get("heading_path", [])
        if row.get("kind") != "section" or not path or any(h["path"] in roots for h in path):
            continue
        found = _names(row["quote"])
        if len(found) == 1:
            roots[path[-1]["path"]] = found[0]
    groups = {}
    for row in claims:
        matches = [h for h in row.get("locator", {}).get("heading_path", []) if h["path"] in roots]
        if not matches:
            continue
        heading = matches[-1]
        name = roots[heading["path"]]
        if name not in groups:
            groups[name] = {"name": name, "index": len(groups) + 1, "title": heading["text"],
                            "heading": heading, "claim_keys": []}
        groups[name]["claim_keys"].append(row["key"])
    return list(groups.values()) if len(groups) >= 2 else []


def _chosen(programs, value):
    name = str(value).strip().casefold()
    if name.isdecimal():
        index = int(name)
        if 1 <= index <= len(programs):
            return programs[index - 1]
    else:
        for item in programs:
            if name in {item["name"].casefold(), item["title"].casefold()}:
                return item
    choices = ", ".join(f'{p["index"]}={p["name"]}' for p in programs)
    raise PipelineError("Unknown USA.gov program; choose --program " + choices)


def select_program(record, claims, cfg, *, program=None):
    programs = program_units(record, claims)
    requested = program if program is not None else record.get("requested_program")
    mode = "explicit" if program is not None else "topic" if requested is not None else "automatic_first_fitting"
    if requested is not None and not programs:
        raise PipelineError("This USA.gov page has no separate recognized programs; omit --program")
    if not programs:
        return _select_units(record, claims, cfg)
    if program is not None and record.get("requested_program") is not None:
        if _chosen(programs, program)["name"] != _chosen(programs, record["requested_program"])["name"]:
            raise PipelineError("--program differs from the selected program topic; choose that topic explicitly")
    # On a multi-program page, a whole-page result must retain every active fact,
    # including list-item exceptions that the legacy greedy rule could leave out.
    whole = _select_units(record, claims, cfg, required_keys={c["key"] for c in claims if not c["expired"]})
    if requested is None and whole[2]["state"] == "selected":
        whole[2].update(scope="page", program_selection="whole_page", chosen_program=None, programs=programs,
                        left_out_programs=[])
        return whole
    candidates = [_chosen(programs, requested)] if requested is not None else programs
    program_keys = {key for item in programs for key in item["claim_keys"]}
    shared = {c["key"] for c in claims if c["key"] not in program_keys}
    # Keep every unassigned fact, not just sentences recognized by a condition
    # keyword heuristic: an ambiguous page-wide exception must not disappear.
    shared_conditions = shared
    attempts, selected, result = {}, None, None
    for item in candidates:
        keys = set(item["claim_keys"])
        info = {key: item[key] for key in ("name", "index", "title", "heading")}
        result = _select_units(record, claims, cfg, allowed_keys=shared | keys,
                               required_keys=keys | shared_conditions, program_info=info)
        current = any(c["key"] in keys and not c["expired"] and
                      (c["kind"] != "section" or c["quote"] != c["values"].get("heading")) for c in claims)
        if not current:
            # Do not let a shared state note make an expired program look current.
            result = _select_units(record, claims, cfg, allowed_keys=set(), required_keys=set(), program_info=info)
            attempts[item["name"]] = "no_current_program_facts"
        elif result[2]["state"] != "selected":
            attempts[item["name"]] = "complete_program_budget_or_dependency"
        else:
            selected = item
            break
    rec, rows, report = result
    left_out = [{"name": item["name"], "index": item["index"], "title": item["title"],
                 "reason": attempts.get(item["name"], ("other_program_explicitly_selected" if selected else "not_requested")
                                        if requested is not None else "first_fitting_program_selected")}
                for item in programs if selected is None or item["name"] != selected["name"]]
    report.update(scope="program", program_selection=mode,
                  chosen_program={key: selected[key] for key in ("name", "index", "title", "heading")} if selected else None,
                  requested_program=str(requested) if requested is not None else None,
                  whole_page_state=whole[2]["state"], whole_page_reason=whole[2].get("reason"),
                  programs=programs, left_out_programs=left_out,
                  page_wide_condition_keys=[c["key"] for c in claims if c["key"] in shared_conditions],
                  program_selection_note=(f'First fitting program in source order: {selected["name"]}' if mode == "automatic_first_fitting"
                                          else f'Chosen program: {selected["name"]}') if selected else "No complete requested program fits")
    report["rule"] = "One complete program with all its active facts and dependencies, page identity and page-wide conditions; no clipping"
    other_keys = program_keys - (set(selected["claim_keys"]) if selected else set())
    for row in report["dropped"]:
        if row["key"] in other_keys and row["reason"] != "expired":
            row["reason"] = "other_program" if selected else "no_complete_program_selected"
    rec["fact_projection"]["rule"] = report["rule"]
    return rec, rows, report

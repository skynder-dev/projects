"""SBA information pages; URL and HTML format not checked live."""
from pathlib import Path
import copy
import re

from .common import PipelineError, sha256_bytes
from .public_sources import SourceClient, html_record
from .usagov_facts import USAGovHTML, build_claims as structural_claims, _select_units

HOSTS = ("www.sba.gov", "sba.gov")
PAGES = {
    # URL not checked live (each catalog entry).
    "loans": "https://www.sba.gov/funding-programs/loans",  # URL not checked live
    "7a": "https://www.sba.gov/funding-programs/loans/7a-loans",  # URL not checked live
    "microloans": "https://www.sba.gov/funding-programs/loans/microloans",  # URL not checked live
    "sbir_sttr": "https://www.sba.gov/funding-programs/grants/sbir-sttr",  # URL not checked live
    "grants": "https://www.sba.gov/funding-programs/grants",  # URL not checked live
    "local_assistance": "https://www.sba.gov/local-assistance",  # URL not checked live
    "disaster": "https://www.sba.gov/funding-programs/disaster-assistance",  # URL not checked live
    "contracting": "https://www.sba.gov/federal-contracting/contracting-guide/basic-requirements",  # URL not checked live
}


class SBAHTML(USAGovHTML):
    @classmethod
    def skipped(cls, node):
        return (super().skipped(node) or node.tag == "header" or
                bool(re.search(r"breadcrumb|related-content|related-links", " ".join(
                    str(node.attrs.get(k, "")) for k in ("id", "class", "aria-label")), re.I)))


class SBAClient(SourceClient):
    def page(self, page, *, fixture: Path | None = None):
        url = PAGES.get(page, page)
        raw, receipt = self.read(url, "sba", HOSTS, fixture=fixture)
        record = html_record(raw, receipt, "sba", parser_type=SBAHTML)
        name = next((name for name, value in PAGES.items() if value == receipt["url"]), None)
        record.update(topic_id="sba:" + (name or sha256_bytes(receipt["url"].encode())[:16]),
                      rubric="small_business_nonprofit", url_note="URL not checked live")
        return record, receipt


def build_claims(record, snapshot=None, today=None):
    if snapshot is not None and snapshot != record.get("provenance"):
        raise PipelineError("SBA snapshot differs from saved record")
    return structural_claims(record, source_type="sba", source_label="SBA.gov")


def program_units(record, claims):
    """Only explicitly named program headings; never infer a program from prose."""
    patterns = {"7a": r"7\s*\(a\)", "microloans": r"microloans?", "sbir_sttr": r"SBIR|STTR|America.s Seed Fund",
                "sbdc": r"SBDC|Small Business Development Centers?", "score": r"\bSCORE\b",
                "wbc": r"Women.s Business Centers?|\bWBC\b", "disaster": r"disaster loans?"}
    groups = {}
    for row in claims:
        headings = row.get("locator", {}).get("heading_path", [])
        for heading in reversed(headings):
            matches = [name for name, pattern in patterns.items() if re.search(pattern, heading["text"], re.I)]
            if len(matches) != 1:
                continue
            name = matches[0]
            group = groups.setdefault(name, {"name": name, "index": len(groups) + 1,
                "title": heading["text"], "heading": copy.deepcopy(heading), "claim_keys": []})
            group["claim_keys"].append(row["key"])
            break
    return list(groups.values()) if len(groups) >= 2 else []


def select_for_core(record, claims, cfg, *, program=None):
    groups = program_units(record, claims)
    requested = program if program is not None else record.get("requested_program")
    whole = _select_units(record, claims, cfg, required_keys={c["key"] for c in claims if not c["expired"]})
    if not groups:
        if requested is not None:
            raise PipelineError("This SBA page has no separate recognized programs; omit --program")
        return whole
    if requested is None and whole[2]["state"] == "selected":
        return whole
    candidates = groups
    if requested is not None:
        candidates = [g for g in groups if str(requested).casefold() in
                      {g["name"].casefold(), g["title"].casefold(), str(g["index"])}]
        if not candidates:
            raise PipelineError("Unknown SBA program; choose " + ", ".join(g["name"] for g in groups))
    owned = {k for g in groups for k in g["claim_keys"]}
    shared = {c["key"] for c in claims} - owned
    chosen = None
    for group in candidates:
        keys = shared | set(group["claim_keys"])
        result = _select_units(record, claims, cfg, allowed_keys=keys, required_keys=keys,
                               program_info={k: group[k] for k in ("name", "index", "title", "heading")})
        if any(c["key"] in group["claim_keys"] and not c["expired"] for c in result[1]) and result[2]["state"] == "selected":
            chosen = group
            break
        result = _select_units(record, claims, cfg, allowed_keys=set(), required_keys=set())
    result[2].update(program_selection="explicit" if requested is not None else "automatic_first_fitting",
                     chosen_program=chosen, programs=groups,
                     left_out_programs=[g for g in groups if g is not chosen],
                     page_wide_condition_keys=sorted(shared))
    return result

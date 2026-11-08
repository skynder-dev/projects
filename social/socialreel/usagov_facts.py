"""USA.gov structural units and complete-unit selection; no live format verification.

Quotes use the existing HTML text_content extraction (entities decoded, LF
between block elements), never rewritten sentences or abbreviated text.
"""
from __future__ import annotations

import copy
import re

from .claims import _src
from .common import PipelineError, sha256_bytes, slug, stable_json
from .public_sources import MainHTML, Node, SECTION_RULES, STATE_RULES

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
INLINE = {"a", "span", "strong", "em", "small", "code", "b", "i", "u", "sup", "sub", "abbr", "time", "br"}
NOISE_IDS = {"breadcrumbs", "breadcrumb", "usa-breadcrumb", "usa-breadcrumb__list", "page-feedback",
             "page-helpful", "usagov-feedback", "usagov-chat", "usagov-call", "footer", "usa-footer"}
NOISE_TEXT = re.compile(r"^(?:was this page helpful\??|call usagov|chat with usagov|last updated:?)(?:\s|$)", re.I)
CONDITIONS = re.compile(r"\b(?:must|only|unless|except\w*|exclud\w*|eligib\w*|income|requirements?|conditions?|rules differ|vary by state|not guaranteed|does not|may not|cannot|limited|subject to)\b", re.I)
EXPIRED = re.compile(r"\b(?:has|have) ended\b|\b(?:is|are) no longer (?:available|accepting applications)\b|\b(?:claim|application) period (?:has )?ended\b", re.I)


class USAGovHTML(MainHTML):
    @classmethod
    def skipped(cls, node):
        if super().skipped(node) or node.tag in {"footer", "nav"}:
            return True
        attrs = node.attrs
        tokens = set((str(attrs.get("id", "")) + " " + str(attrs.get("class", ""))).lower().split())
        label = str(attrs.get("aria-label", ""))
        return bool(tokens.intersection(NOISE_IDS) or attrs.get("role") in {"navigation", "contentinfo"}
                    or re.search(r"breadcrumb|page feedback|was this page helpful|call usagov|chat with usagov", label, re.I))

    def extract(self):
        nodes = list(self.nodes())
        mains = [n for n in nodes if n.tag == "main" or n.attrs.get("role") == "main"]
        if not mains:
            mains = [n for n in nodes if n.tag == "article"]
        mains = [n for n in mains if not any(n.path.startswith(other.path + "/") for other in mains if n is not other)]
        if len(mains) != 1:
            raise PipelineError("Expected one readable USA.gov main/article; format not checked live")
        main = mains[0]
        title = next((n for n in self.nodes(main) if n.tag == "h1" and self.text(n).strip()), None)
        if title is None:
            raise PipelineError("USA.gov page has no main h1 title; format not checked live")
        units, heading_path, pending, pending_paths = [], [], [], []
        heading_open, suppressed_level = False, None
        counts = {}

        def emit(kind, text, locator, label=None):
            if not text or NOISE_TEXT.match(text.strip()):
                return
            names = [h["text"] for h in heading_path]
            identity = [kind, names, label or ""]
            base = kind + "_" + slug(" ".join(names + ([label] if label else [])), 48)
            digest = sha256_bytes(stable_json(identity).encode())[:10]
            key = base + "_" + digest
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > 1:
                key += "_" + str(counts[key])
            locator = {"main": main.path, "heading_path": copy.deepcopy(heading_path), **locator}
            units.append({"key": key, "kind": kind, "heading": heading_path[-1]["text"] if heading_path else None,
                          "heading_path": copy.deepcopy(heading_path), "text": text, "locator": locator})

        def flush():
            nonlocal pending, pending_paths, heading_open
            if pending or heading_open:
                pieces = ([heading_path[-1]["text"]] if heading_path else []) + pending
                paths = ([heading_path[-1]["path"]] if heading_path else []) + pending_paths
                emit("section" if heading_path else "lead", "\n".join(pieces), {"blocks": paths})
            pending, pending_paths = [], []
            heading_open = False

        def add_text(node, text):
            if text and not NOISE_TEXT.match(text):
                pending.append(text)
                pending_paths.append(node.path)

        def descendants(node, tag):
            return [n for n in self.nodes(node) if n.tag == tag]

        def table(node):
            # A layout table containing headings is a container, not a single fact.
            if node.attrs.get("role") in {"presentation", "none"} or any(n.tag in HEADINGS for n in self.nodes(node)):
                return False
            rows = [r for r in descendants(node, "tr") if not any(r.path.startswith(other.path + "/") for other in descendants(node, "table"))]
            if not rows:
                return False
            flush()
            headers = []
            caption = next((self.text(n).strip() for n in self.nodes(node) if n.tag == "caption"), None)
            for row_number, row in enumerate(rows, 1):
                cells = [c for c in row.children if isinstance(c, Node) and c.tag in {"th", "td"}]
                if not cells:
                    continue
                if all(c.tag == "th" for c in cells):
                    headers = cells
                    continue
                columns = [{"column": i + 1, "path": cell.path, "text": self.text(cell).strip(),
                            "header": self.text(headers[i]).strip() if i < len(headers) else None,
                            "header_path": headers[i].path if i < len(headers) else None}
                           for i, cell in enumerate(cells)]
                quote = "\n".join(c["text"] for c in columns)
                emit("table_row", quote, {"table": node.path, "caption": caption, "row": row.path,
                                           "row_number": row_number, "columns": columns}, columns[0]["text"])
            return True

        def walk(node):
            nonlocal heading_open, suppressed_level
            if self.skipped(node):
                return
            text = self.text(node).strip()
            if node.tag in {"section", "div", "aside", "form"} and NOISE_TEXT.match(text):
                return
            if node.tag in HEADINGS:
                level = int(node.tag[1])
                if suppressed_level is not None:
                    if level > suppressed_level:
                        return
                    suppressed_level = None
                if NOISE_TEXT.match(text):
                    flush()
                    suppressed_level = level
                    return
                flush()
                if node is title:
                    return
                while heading_path and heading_path[-1]["level"] >= level:
                    heading_path.pop()
                heading_path.append({"level": level, "text": text, "path": node.path})
                heading_open = True
                return
            if suppressed_level is not None and not any(n.tag in HEADINGS for n in self.nodes(node)):
                return
            if node.tag == "table" and table(node):
                return
            if node.tag in {"ul", "ol"}:
                flush()
                items = [c for c in node.children if isinstance(c, Node) and c.tag == "li" and not self.skipped(c)]
                for item in items:
                    label_node = next((n for n in self.nodes(item) if n.tag in {"a", "strong", "b"} and self.text(n).strip()), None)
                    quote = self.text(item).strip()
                    emit("list_item", quote, {"list": node.path, "item": item.path},
                         self.text(label_node).strip() if label_node else quote)
                return
            if node.tag in self.BLOCKS and not any(n.tag in HEADINGS or n.tag in {"ul", "ol", "table"} for n in self.nodes(node)):
                add_text(node, text)
                return
            inline = []
            for child in node.children:
                if isinstance(child, str):
                    inline.append(child)
                elif child.tag in INLINE:
                    inline.append(self.text(child))
                else:
                    add_text(node, "".join(inline).strip())
                    inline = []
                    walk(child)
            add_text(node, "".join(inline).strip())

        walk(main)
        flush()
        if not units:
            raise PipelineError("USA.gov page has no readable facts; format not checked live")
        # Each row/option inherits complete prose in its heading ancestry. Global
        # conditions remain mandatory later even when an unrelated option is dropped.
        for unit in units:
            paths = [h["path"] for h in unit["heading_path"]]
            unit["required_context_keys"] = [other["key"] for other in units if other is not unit
                and other["kind"] == "section" and other["heading_path"]
                and [h["path"] for h in other["heading_path"]] == paths[:len(other["heading_path"])]]
        return self.text(title).strip(), title.path, units


def build_claims(record, *, source_type="usagov", source_label="USA.gov"):
    if record.get("source_type") != source_type or record.get("source_label") != source_label:
        raise PipelineError(f"{source_label} source kind/label mismatch")
    receipt = record["provenance"]
    lead_units = [u for u in record["sections"] if u["kind"] == "lead"]
    lead = "\n".join(u["text"] for u in lead_units)
    quote = record["title"] + ("\n" + lead if lead else "")
    page_locator = {"title": record["title_locator"], "lead_blocks": [p for u in lead_units for p in u["locator"]["blocks"]]}

    def claim(key, text, kind, locator, **values):
        expired = bool(EXPIRED.search(text))
        source = {"kind": "html_text_content", "url": record["source_url"], "snapshot_file": receipt["file"],
                  "snapshot_sha256": receipt["sha256"], "locator": copy.deepcopy(locator),
                  "quote": text, "excerpt_sha256": sha256_bytes(text.encode("utf-8"))}
        row = {"key": key, "kind": kind, "statement": text, "quote": text, "locator": copy.deepcopy(locator),
               "expired": expired, "values": {"text": text, "expired": expired, **values}, "source": source}
        if receipt.get("fetched_at"):
            row["observed_at"] = receipt["fetched_at"]
        return row

    page = claim("identity", quote, "page", page_locator, title=record["title"], lead=lead)
    page["statement"] = source_label + " page:\n" + quote
    rows = [page]
    for unit in record["sections"]:
        if unit["kind"] == "lead":
            continue
        rows.append(claim(unit["key"], unit["text"], unit["kind"], unit["locator"],
                          heading=unit["heading"], required_context_keys=unit["required_context_keys"]))
    expired = {row["key"] for row in rows if row["expired"]}
    while True:
        inherited = {row["key"] for row in rows if "identity" in expired or
                     expired.intersection(row["values"].get("required_context_keys", []))}
        if inherited <= expired:
            break
        expired.update(inherited)
    for row in rows:
        row["expired"] = row["values"]["expired"] = row["key"] in expired
    page["source_context"] = [{"field": "description", "text": record["description"],
                               "text_sha256": sha256_bytes(record["description"].encode()),
                               "representation": "normalized_record_field", "source": _src(record, receipt, "description")}]
    return rows


def _select_units(record, claims, cfg, *, allowed_keys=None, required_keys=None, program_info=None):
    """Choose complete units + mandatory conditions, with a recorded, bounded ledger."""
    from . import concept_core as core, concept_admission as admission
    cap = (cfg.get("usagov_facts") or {}).get("max_claims", 16)
    if type(cap) is not int or cap < 1:
        raise PipelineError("usagov_facts.max_claims must be a positive integer")
    expired = {c["key"] for c in claims if c.get("expired")}
    # Expired ancestry cannot become current simply because a row omits the date.
    changed = True
    while changed:
        before = len(expired)
        expired.update(c["key"] for c in claims if set(c["values"].get("required_context_keys", [])).intersection(expired))
        changed = len(expired) != before
    active = [c for c in claims if c["key"] not in expired and (allowed_keys is None or c["key"] in allowed_keys)]
    mandatory = ({c["key"] for c in active if c["kind"] == "page" or
                  c["kind"] == "section" and (CONDITIONS.search(c["quote"]) or CONDITIONS.search(str(c["values"].get("heading") or "")))}
                 if required_keys is None else set(required_keys) - expired)

    def dependencies(keys):
        result = set(keys)
        while True:
            extra = {key for c in claims if c["key"] in result for key in c["values"].get("required_context_keys", [])}
            if extra <= result:
                return result
            result.update(extra)

    mandatory = dependencies(mandatory)
    report = {"rule": "Whole units only: page/conditions mandatory, then table rows, application/search sections, list items, remaining sections; dependencies mandatory for each choice",
              "max_claims": cap, "context_cap_bytes": core.SOURCE_CONTEXT_BYTES,
              # Reserve the same 14 KB for system text and request metadata;
              # the actual unchanged admission still checks the complete body.
              "non_system_wire_cap_bytes": admission.BASE_BYTES - 14000 if program_info else min(18000, admission.BASE_BYTES - 14000),
              "selected_keys": [], "dropped_keys": [], "dropped": [], "expired_keys": sorted(expired)}

    def projection(keys):
        rows = [copy.deepcopy(c) for c in claims if c["key"] in keys]
        rec = copy.deepcopy(record)
        rec["description"] = "\n\n".join(c["quote"] for c in rows)
        rec["sections"] = [copy.deepcopy(u) for u in record["sections"] if u["key"] in keys or
                           (u["kind"] == "lead" and "identity" in keys)]
        for name, pattern in SECTION_RULES.items():
            rec[name] = [copy.deepcopy(u) for u in rec["sections"] if re.search(pattern, u["text"], re.I)]
        rec["state_rules_note"] = [copy.deepcopy(u) for u in rec["sections"] if re.search(STATE_RULES, u["text"], re.I)]
        rec["state_rules_differ"] = True if rec["state_rules_note"] else None
        rec["fields"]["description"] = "html.main.selected_complete_facts"
        rec["extraction"] = "Selected complete HTML text_content units; full original record and claims retained separately"
        rec["fact_projection"] = {"selected_keys": [c["key"] for c in rows], "rule": report["rule"]}
        if program_info is not None and rows:
            rec["selected_program"] = copy.deepcopy(program_info)
            rec["topic_id"] = record["topic_id"] + ":" + program_info["name"]
            rec["fact_projection"]["program"] = program_info["name"]
        for c in rows:
            c.pop("source_context", None)
        if rows:
            text = rec["description"]
            rows[0]["source_context"] = [{"field": "description", "text": text,
                "text_sha256": sha256_bytes(text.encode()), "representation": "normalized_record_field",
                "source": _src(rec, rec["provenance"], "description")}]
        return rec, rows

    def fits(keys):
        if not keys or len(keys) > cap or keys.intersection(expired) or (allowed_keys is not None and not keys <= allowed_keys):
            return False
        rec, rows = projection(keys)
        if len(rec["description"].encode("utf-8")) > core.SOURCE_CONTEXT_BYTES:
            return False
        data = core.inputs(rec, rows, cfg)
        cf = cfg.get("concept_first") or {}
        if "topic_direction" in cf:
            data["topic_direction"] = cf["topic_direction"]
        if "unknowns" in cf:
            data["forbidden_assumptions"] = cf["unknowns"]
        data["input_identity"] = core.digest(data)
        request_data = copy.deepcopy(data)
        for row in request_data["factual_core"]:
            row["source"] = core.project_source(row["source"])
        for row in request_data["source_context"].get("condition_fields", []):
            row["source"] = core.project_source(row["source"])
        schema = core.schema([c["key"] for c in rows], data["language_contract"],
                             result_contract=data.get("result_contract", core.VERSION), input_identity=data["input_identity"])
        wire = stable_json({"prompt": stable_json(request_data), "format": schema}).encode()
        return len(wire) <= report["non_system_wire_cap_bytes"]

    def priority(c):
        if c["kind"] == "table_row":
            return 0
        if re.search(r"apply|how to|where to|search|claim", str(c["values"].get("heading") or ""), re.I):
            return 1
        return 2 if c["kind"] == "list_item" else 3

    selected = set(mandatory)
    viable = fits(selected)
    if viable:
        for c in sorted(active, key=priority):
            trial = dependencies(selected | {c["key"]})
            if not trial.intersection(expired) and fits(trial):
                selected = trial
    current_fact = any(c["kind"] != "page" and c["key"] in selected and
                       (c["kind"] != "section" or c["quote"] != c["values"].get("heading")) for c in active)
    if not viable or (expired and not current_fact):
        selected = set()
        report["state"] = "refused"
        report["reason"] = "No current facts fit with their complete mandatory conditions; no clipping or admission bypass"
    else:
        report["state"] = "selected"
    report["selected_keys"] = [c["key"] for c in claims if c["key"] in selected]
    report["dropped"] = [{"key": c["key"], "reason": "expired" if c["key"] in expired else "complete_unit_budget_or_dependency"}
                         for c in claims if c["key"] not in selected]
    report["dropped_keys"] = [row["key"] for row in report["dropped"]]
    rec, rows = projection(selected)
    return rec, rows, report


def select_for_core(record, claims, cfg, *, program=None):
    from .usagov_programs import select_program
    return select_program(record, claims, cfg, program=program)

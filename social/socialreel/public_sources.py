"""Shared, standard-library public-source intake and source-bound claim ledger.

HTML/API format not checked live. HTML extraction is explicitly text_content,
not original HTML bytes; complete bytes always stay in the hashed snapshot.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.parse
import urllib.request

from .claims import _src
from .common import PipelineError, sha256_bytes, utc_now

LABELS = {"usagov": "USA.gov", "studentaid": "Federal Student Aid", "scorecard": "College Scorecard", "sba": "SBA.gov"}
HTML_HOSTS = {"usagov": ("www.usa.gov", "usa.gov"), "studentaid": ("studentaid.gov", "www.studentaid.gov")}
HTML_HOSTS["sba"] = ("www.sba.gov", "sba.gov")
SECTION_RULES = {
    "who_it_is_for": r"\b(who|eligib\w*|qualif\w*|income|students?|households?|workers?)\b",
    "what_you_get": r"\b(benefits?|help|assistance|aid|grants?|receive|provides?|payments?)\b",
    "how_to_apply": r"\b(apply|application|contact|claim|search|find|submit|fafsa)\b",
    "conditions": r"\b(may|must|only|unless|except|eligible|eligibility|income|limits?|requirements?|conditions?|state)\b",
    "deadlines": r"\b(deadlines?|due|closing date|apply by|submit by)\b",
}
STATE_RULES = r"\b(?:rules|requirements|eligibility|benefits)\b[^.!?]*\b(?:vary|differ)\b[^.!?]*\bstates?\b|\beach state\b[^.!?]*\b(?:rules|requirements|eligibility)\b"


def official_url(url: str, hosts: tuple[str, ...], *, query: bool = False) -> str:
    parts = urllib.parse.urlsplit(url)
    try:
        valid_port = parts.port in (None, 443)
    except ValueError:
        valid_port = False
    if (parts.scheme != "https" or parts.hostname not in hosts or not valid_port
            or parts.username or parts.password or parts.fragment or (parts.query and not query)):
        raise PipelineError("Source requires an approved official HTTPS URL without credentials or fragments")
    return url


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate before following, including before forwarding a data.gov key.
        official_url(newurl, self.hosts, query=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SourceClient:
    def __init__(self, snapshot_dir: Path, *, transport=None, timeout: int = 40):
        self.dir = Path(snapshot_dir)
        self.transport = transport
        self.timeout = timeout
        self.calls = []

    def read(self, url: str, source_type: str, hosts: tuple[str, ...], *, fixture: Path | None = None,
             headers: dict | None = None, secret: str | None = None, suffix: str = "html") -> tuple[bytes, dict]:
        official_url(url, hosts, query=source_type == "scorecard")
        if fixture is not None:
            raw = Path(fixture).read_bytes()
            status, final_url = None, url
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "SocialReels/1.0 (public source research)",
                                                           "Accept": "application/json" if suffix == "json" else "text/html",
                                                           **(headers or {})})
            open_request = self.transport or urllib.request.build_opener(OfficialRedirects(hosts)).open
            try:
                with open_request(request, timeout=self.timeout) as response:
                    final_url = response.geturl() if hasattr(response, "geturl") else url
                    official_url(final_url, hosts, query=source_type == "scorecard")
                    status = response.status
                    if status != 200:
                        raise PipelineError("Source did not return HTTP 200")
                    raw = response.read()
            except Exception:
                # Never echo exception strings, request headers, or an API key.
                raise PipelineError(f"{LABELS[source_type]} request failed; no source record produced") from None
        if secret and (secret.encode("utf-8") in raw or secret in final_url):
            raise PipelineError("API response contains the credential; response was not saved")
        digest = sha256_bytes(raw)
        name = f"{source_type}_{digest}.{suffix}"
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / name).write_bytes(raw)
        receipt = {"file": f"source/{name}", "url": final_url, "sha256": digest, "bytes": len(raw),
                   "http_status": status, "mode": "fixture" if fixture is not None else "live",
                   "format_note": "format not checked live"}
        if fixture is None:
            receipt["fetched_at"] = utc_now().isoformat()
        self.calls.append(copy.deepcopy(receipt))
        return raw, receipt


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    path: str = ""
    children: list = field(default_factory=list)


class MainHTML(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    SKIP = {"script", "style", "template", "noscript", "nav"}
    BLOCKS = {"p", "li", "dt", "dd", "blockquote", "pre", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1]
        index = 1 + sum(isinstance(c, Node) and c.tag == tag for c in parent.children)
        node = Node(tag, dict(attrs), f"{parent.path}/{tag}[{index}]")
        parent.children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    @classmethod
    def skipped(cls, node):
        # Keep accordion/aside/form conditions even if initially hidden by the UI.
        return node.tag in cls.SKIP

    @classmethod
    def text(cls, node):
        if cls.skipped(node):
            return ""
        if node.tag == "br":
            return "\n"
        parts = []
        for child in node.children:
            text = child if isinstance(child, str) else cls.text(child)
            block = isinstance(child, Node) and child.tag in cls.BLOCKS
            if block and parts and not parts[-1].endswith(("\n", " ")):
                parts.append("\n")
            parts.append(text)
            if block and text and not text.endswith("\n"):
                parts.append("\n")
        return "".join(parts)

    def nodes(self, root=None):
        root = root or self.root
        for child in root.children:
            if isinstance(child, Node) and not self.skipped(child):
                yield child
                yield from self.nodes(child)

    def extract(self):
        all_nodes = list(self.nodes())
        mains = [n for n in all_nodes if n.tag == "main" or n.attrs.get("role") == "main"]
        if not mains:
            mains = [n for n in all_nodes if n.tag == "article"]
        # Nested role=main/main is one root, not two independent articles.
        mains = [n for n in mains if not any(n.path.startswith(other.path + "/") for other in mains if n is not other)]
        if len(mains) != 1:
            raise PipelineError("Expected one readable main/article; format not checked live (possibly a JavaScript shell)")
        main = mains[0]
        title = next((n for n in self.nodes(main) if n.tag == "h1" and self.text(n).strip()), None)
        if title is None:
            raise PipelineError("Official page has no main h1 title; format not checked live")
        events = []

        def walk(node):
            if self.skipped(node):
                return
            if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"} | self.BLOCKS:
                text = self.text(node).strip()
                if text:
                    events.append((node, text))
                return
            # Plain text in a semantic container must not silently disappear.
            pending = []
            for child in node.children:
                if isinstance(child, str):
                    pending.append(child)
                elif child.tag in {"a", "span", "strong", "em", "small", "code", "b", "i", "u", "sup", "sub", "abbr", "time", "br"}:
                    pending.append(self.text(child))
                else:
                    if "".join(pending).strip():
                        events.append((node, "".join(pending).strip()))
                    pending = []
                    walk(child)
            if "".join(pending).strip():
                events.append((node, "".join(pending).strip()))

        walk(main)
        sections, heading, paths, pieces = [], None, [], []

        def flush():
            if pieces or heading:
                text = "\n".join(([heading] if heading else []) + pieces)
                sections.append({"heading": heading, "text": text, "locator": {"main": main.path, "blocks": list(paths)}})

        for node, text in events:
            if node.tag.startswith("h") and node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                flush()
                heading, paths, pieces = (None if node is title else text), [node.path], []
            else:
                paths.append(node.path)
                pieces.append(text)
        flush()
        if not sections:
            raise PipelineError("Page has no readable main text; format not checked live (possibly a JavaScript shell)")
        return self.text(title).strip(), title.path, sections


def html_record(raw: bytes, receipt: dict, source_type: str, *, parser_type=MainHTML) -> dict:
    if source_type not in HTML_HOSTS:
        raise PipelineError("Unsupported HTML source type")
    official_url(receipt["url"], HTML_HOSTS[source_type])
    try:
        # USA.gov/StudentAid pages are expected to be UTF-8. Fail rather than replace characters.
        parser = parser_type()
        parser.feed(raw.decode("utf-8-sig"))
        parser.close()
    except UnicodeError:
        raise PipelineError("Official HTML is not UTF-8; no replacement or text repair performed") from None
    title, title_path, sections = parser.extract()
    description = "\n\n".join(section["text"] for section in sections)
    rec = {"source_type": source_type, "source_label": LABELS[source_type], "source_url": receipt["url"],
           "title": title, "description": description, "applicant_eligibility_desc": None,
           "sections": sections, "fields": {"title": "html.main.title", "description": "html.main.text"},
           "field_provenance": {"title": copy.deepcopy(receipt), "description": copy.deepcopy(receipt)},
           "provenance": copy.deepcopy(receipt), "title_locator": title_path,
           "close_date": None, "format_note": "format not checked live",
           "extraction": "HTML text_content; entities decoded, complete sections joined with LF; raw HTML snapshot retained",
           "fixture_only": receipt["mode"] == "fixture"}
    for name, pattern in SECTION_RULES.items():
        rec[name] = [copy.deepcopy(s) for s in sections if re.search(pattern, s["text"], re.I)]
    state = [copy.deepcopy(s) for s in sections if re.search(STATE_RULES, s["text"], re.I)]
    rec["state_rules_differ"] = True if state else None
    rec["state_rules_note"] = state
    rec["unknowns"] = ["Individual eligibility, payment amount and source currentness are not established by this page extraction."]
    if not rec["deadlines"]:
        rec["unknowns"].append("No deadline text identified; no deadline inferred.")
    return rec


def html_claims(record: dict, expected_type: str) -> list[dict]:
    if record.get("source_type") != expected_type or record.get("source_label") != LABELS[expected_type]:
        raise PipelineError("Source kind/label mismatch; no substitute Grants.gov claims")
    snapshot = record["provenance"]
    title = record["title"]
    source = _src(record, snapshot, "title")
    source.update(kind="html_text_content", locator={"path": record["title_locator"]}, quote=title,
                  excerpt_sha256=sha256_bytes(title.encode("utf-8")))
    rows = [{"key": "identity", "statement": f'{LABELS[expected_type]} page: "{title}".',
             "values": {"title": title, "source_type": expected_type}, "source": source}]
    for index, section in enumerate(record["sections"]):
        text = section["text"]
        source = {"kind": "html_text_content", "url": record["source_url"], "snapshot_file": snapshot["file"],
                  "snapshot_sha256": snapshot["sha256"], "locator": copy.deepcopy(section["locator"]),
                  "quote": text, "excerpt_sha256": sha256_bytes(text.encode("utf-8"))}
        rows.append({"key": f"section_{index:04d}", "statement": text,
                     "values": {"text": text, "heading": section["heading"]}, "source": source})
    text = record["description"]
    rows[0]["source_context"] = [{"field": "description", "text": text,
                                 "text_sha256": sha256_bytes(text.encode("utf-8")),
                                 "representation": "normalized_record_field", "source": _src(record, snapshot, "description")}]
    for row in rows:
        if snapshot.get("fetched_at"):
            row["observed_at"] = snapshot["fetched_at"]
    return rows

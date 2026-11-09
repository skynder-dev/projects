"""Conservative, stdlib-only intake of allowlisted federal information pages.

HTML format not checked live. Quotes are text_content, never rewritten facts.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path

from .common import ROOT, PipelineError, read_json, sha256_bytes
from .public_sources import Node, HTML_HOSTS, LABELS, OfficialRedirects, SourceClient, html_record, official_url
from .usagov_facts import USAGovHTML, build_claims as structural_claims, _select_units


def allowed_hosts():
    data = read_json(ROOT / "public_sources_config.json")
    section = data.get("govpage") if isinstance(data, dict) else None
    hosts = section.get("hosts") if isinstance(section, dict) else None
    if (not isinstance(hosts, list) or not hosts or
            any(not isinstance(h, str) or h not in HTML_HOSTS["govpage"] for h in hosts)):
        raise PipelineError("govpage allowlist must be a nonempty subset of the supported official hosts")
    return tuple(hosts)


INTERACTIVE = re.compile(r"(?:^|[/_.-])(?:log-?in|sign-?in|login|signin|auth|account|payments?|pay|tools?|calculators?|calculate|estimators?|forms?)(?:$|[/_.-])", re.I)
JS_SHELL = re.compile(r"(?:enable|requires?|turn on)\s+(?:your\s+)?javascript|javascript\s+(?:is\s+)?(?:required|disabled)", re.I)
RELATED = re.compile(r"(?:^|[\s_-])(?:related|breadcrumb|navigation|menu|sidebar|social-share|page-feedback)(?:$|[\s_-])", re.I)


def page_url(url, hosts=None):
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url) or "\\" in url:
        raise PipelineError("govpage requires an official HTTPS URL without whitespace")
    official_url(url, hosts or allowed_hosts())
    parts = urllib.parse.urlsplit(url)
    # Even empty query/fragment markers are outside this source contract.
    if "?" in url or "#" in url:
        raise PipelineError("govpage URLs must have no query string or fragment")
    path = urllib.parse.unquote(parts.path)
    if INTERACTIVE.search(path):
        raise PipelineError("govpage refuses forms/login/payment/tools/calculators; use an information page")
    return url


RELATED_TOKENS = {"related", "breadcrumb", "breadcrumbs", "navigation", "menu", "sidebar", "social-share", "page-feedback"}


def related_label(attrs):
    """08.11.2026: irs.gov puts "layout-sidebar-first" on <body>; a substring match dropped the whole page.
    Match whole id/class tokens (and the aria-label as words) instead."""
    tokens = set((str(attrs.get("id", "")) + " " + str(attrs.get("class", ""))).lower().split())
    if tokens & RELATED_TOKENS or any(t.startswith(("related-", "breadcrumb")) for t in tokens):
        return True
    return bool(re.search(r"\b(related|breadcrumbs?|sidebar|social share|page feedback)\b", str(attrs.get("aria-label", "")), re.I))


class GovPageRedirects(OfficialRedirects):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        page_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GovPageHTML(USAGovHTML):
    @classmethod
    def skipped(cls, node):
        attrs = node.attrs
        label = " ".join(str(attrs.get(k, "")) for k in ("id", "class", "aria-label"))
        return (super().skipped(node) or node.tag in {"header", "footer"}
                or attrs.get("role") in {"banner", "navigation", "contentinfo", "search"}
                or (node.tag not in {"html", "body", "main"} and related_label(attrs)))

    def extract(self):
        nodes = list(self.nodes())
        mains = [n for n in nodes if n.tag == "main" or n.attrs.get("role") == "main"]
        mains = [n for n in mains if not any(n.path.startswith(o.path + "/") for o in mains if n is not o)]
        if len(mains) != 1:
            raise PipelineError("govpage requires one readable main; possible JavaScript shell")
        main = mains[0]
        if main.tag == "form":
            raise PipelineError("govpage refuses interactive forms/login/payment pages")
        content = list(self.nodes(main))
        # Search boxes are navigation, not evidence; other interactive forms fail closed.
        for node in content:
            if node.tag == "form" or node.attrs.get("role") == "form":
                raise PipelineError("govpage refuses interactive forms/login/payment pages")
            if node.tag in {"input", "select", "textarea"}:
                raise PipelineError("govpage refuses interactive tools/calculators")
        if not any(n.tag == "h1" and self.text(n).strip() for n in self.nodes(main)):
            # 08.11.2026: irs.gov renders the page title <h1> in a block just before <main>. Use it only when the whole
            # document has exactly one distinct non-empty h1 text; the locator still says it came from outside main.
            outside = {re.sub(r"\s+", " ", self.text(n)).strip() for n in nodes if n.tag == "h1"} - {""}
            if len(outside) == 1:
                main.children.insert(0, Node("h1", {"data-social-title": "outside-main"}, main.path + "/h1[0]",
                                             [next(iter(outside))]))
        if JS_SHELL.search(self.text(main)):
            raise PipelineError("govpage refuses a JavaScript-dependent shell")
        title, locator, units = super().extract()
        body = "\n".join(u["text"] for u in units)
        # H1/heading-only shells and short navigation fragments are not source facts.
        prose = [u for u in units if u["kind"] != "section" or u["text"] != u["heading"]]
        if len(body) < 250 or len(body.split()) < 45 or not prose:
            raise PipelineError("govpage has too little readable main text (250 characters / 45 words required)")
        return title, locator, units


class GovPageClient(SourceClient):
    def page(self, url, *, fixture: Path | None = None):
        hosts = allowed_hosts()
        page_url(url, hosts)
        # Validate each redirect before a request, rather than only its final destination.
        original = self.transport
        if original is None:
            self.transport = urllib.request.build_opener(GovPageRedirects(hosts)).open
        try:
            raw, receipt = self.read(url, "govpage", hosts, fixture=fixture)
        finally:
            self.transport = original
        page_url(receipt["url"], hosts)
        record = html_record(raw, receipt, "govpage", parser_type=GovPageHTML)
        record.update(topic_id="govpage:" + sha256_bytes(receipt["url"].encode())[:16], rubric="help_people")
        return record, receipt


def build_claims(record, snapshot=None, today=None):
    page_url(record["source_url"])
    if snapshot is not None and snapshot != record["provenance"]:
        raise PipelineError("govpage snapshot receipt mismatch")
    return structural_claims(record, source_type="govpage", source_label=LABELS["govpage"])


def select_for_core(record, claims, cfg):
    return _select_units(record, claims, cfg)

"""USA.gov help pages. HTML format not checked live; no entitlement inference."""
from pathlib import Path
from urllib.parse import urlsplit

from .common import PipelineError, sha256_bytes
from .public_sources import SourceClient, html_record
from .usagov_facts import USAGovHTML, build_claims as fact_claims

HOSTS = ("www.usa.gov", "usa.gov")
PAGES = {
    "energy": "https://www.usa.gov/help-with-energy-bills",
    "unclaimed": "https://www.usa.gov/unclaimed-money",
    "wage_laws": "https://www.usa.gov/wage-laws",
    "unclaimed_tax_refunds": "https://www.usa.gov/unclaimed-tax-refunds",
    "workers_comp": "https://www.usa.gov/workers-compensation",
}


class USAGovClient(SourceClient):
    def page(self, page: str, *, fixture: Path | None = None) -> tuple[dict, dict]:
        parsed = urlsplit(page)
        if page == "wages" or (parsed.hostname in HOSTS and parsed.path.rstrip("/") == "/unpaid-wages"):
            raise PipelineError("USA.gov page 'wages' was removed (dead URL); use wage_laws or workers_comp")
        url = PAGES.get(page, page)
        raw, receipt = self.read(url, "usagov", HOSTS, fixture=fixture)
        record = html_record(raw, receipt, "usagov", parser_type=USAGovHTML)
        topic = next((name for name, value in PAGES.items() if value == url), None)
        record["topic_id"] = "usagov:" + (topic or sha256_bytes(url.encode("utf-8"))[:16])
        record["rubric"] = "help_people"
        intent = {"energy": "energy", "unclaimed": "unclaimed", "wage_laws": "wages", "unclaimed_tax_refunds": "unclaimed"}.get(topic)
        if intent:
            # Preserve the core's existing explicit energy/wages/unclaimed contract.
            record["public_reference_topic"] = intent
            record["public_money_source"] = {"kind": intent, "provider": "USA.gov"}
        return record, receipt


def build_claims(record: dict, snapshot=None, today=None) -> list[dict]:
    if snapshot is not None and snapshot != record.get("provenance"):
        raise PipelineError("USA.gov snapshot differs from the saved record")
    return fact_claims(record)

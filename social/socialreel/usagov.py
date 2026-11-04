"""USA.gov help pages. HTML format not checked live; no entitlement inference."""
from pathlib import Path

from .common import PipelineError, sha256_bytes
from .public_sources import SourceClient, html_claims, html_record

HOSTS = ("www.usa.gov", "usa.gov")
PAGES = {
    "energy": "https://www.usa.gov/help-with-energy-bills",
    "unclaimed": "https://www.usa.gov/unclaimed-money",
    "wages": "https://www.usa.gov/unpaid-wages",
}


class USAGovClient(SourceClient):
    def page(self, page: str, *, fixture: Path | None = None) -> tuple[dict, dict]:
        url = PAGES.get(page, page)
        raw, receipt = self.read(url, "usagov", HOSTS, fixture=fixture)
        record = html_record(raw, receipt, "usagov")
        topic = next((name for name, value in PAGES.items() if value == url), None)
        record["topic_id"] = "usagov:" + (topic or sha256_bytes(url.encode("utf-8"))[:16])
        record["rubric"] = "help_people"
        if topic:
            # Preserve the core's existing explicit energy/wages/unclaimed contract.
            record["public_reference_topic"] = topic
            record["public_money_source"] = {"kind": topic, "provider": "USA.gov"}
        return record, receipt


def build_claims(record: dict, snapshot=None, today=None) -> list[dict]:
    if snapshot is not None and snapshot != record.get("provenance"):
        raise PipelineError("USA.gov snapshot differs from the saved record")
    return html_claims(record, "usagov")

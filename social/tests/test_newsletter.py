"""Synthetic source bundles; network and inference forbidden."""
import datetime as dt
import json
from unittest.mock import patch

from socialreel import newsletter, usagov
from socialreel.common import read_json, write_json
from socialreel.source_intake import write_bundle
from tests.test_usagov import OfflineSourceCase
from tests.test_concept_offline import config


class NewsletterTests(OfflineSourceCase):
    def bundle(self, name, extra="", url=None):
        out = self.home / name
        fixture = self.home / (name + ".html")
        fixture.write_text('<main><h1>' + name + '</h1><p>Help may be available. Rules differ by state.</p>'
                           '<h2>Who may use it</h2><p>Only eligible households may apply. Applicants must contact their state office.</p>'
                           '<table><tr><th>Place</th><th>Rule</th></tr><tr><td>State unclaimed property office</td><td>You must prove ownership.</td></tr></table>'
                           + extra + '</main>', encoding="utf-8")
        rec, receipt = usagov.USAGovClient(out / "source").page(url or "https://www.usa.gov/unclaimed-" + name, fixture=fixture)
        write_bundle(rec, usagov.build_claims(rec, receipt), out, config())
        return out

    def test_every_fact_condition_title_traced_no_affiliates_and_thin_report(self):
        bundle = self.bundle("one")
        out = self.home / "out"
        result = newsletter.render("draft", [bundle], out, as_of="2026-11-08", store=self.home / "missing")
        self.assertEqual(result["items"], 1)
        trace = read_json(out / "trace.json")
        text = (out / "newsletter.md").read_text(encoding="utf-8")
        self.assertIn(newsletter.NOTICE, text)
        self.assertIn("[SENDER POSTAL ADDRESS]", text)
        self.assertIn("[UNSUBSCRIBE LINK]", text)
        self.assertNotIn(newsletter.SLOT, text)
        self.assertFalse(trace["sponsor_enabled"])
        self.assertTrue(read_json(out / "summary_ru.json")["мало_материала"])
        rebuilt, claims = newsletter.verified(bundle, dt.date(2026, 11, 8))
        keys = {c["key"] for c in claims}
        for item in trace["items"]:
            self.assertIn(item["title"], item["title_source"]["quote"])
            for fact in item["facts"] + item["conditions"]:
                self.assertIn(fact["claim_key"], keys)
                self.assertIn(fact["quote"], text.replace("\n> ", "\n").replace("> ", ""))
                self.assertIn(fact["source_url"], text)
        self.assertIn("Rules differ by state", text)
        self.assertIn("Only eligible households", text)

    def test_expired_and_past_dates_omitted_and_reported(self):
        bundle = self.bundle("past", '<h2>Ended option</h2><p>The program has ended.</p>'
                             '<h2>Old deadline</h2><p>Apply by November 1, 2026.</p>')
        out = self.home / "past-out"
        newsletter.render("draft", [bundle], out, as_of="2026-11-08")
        text = (out / "newsletter.md").read_text()
        self.assertNotIn("November 1", text)
        self.assertNotIn("has ended", text)
        self.assertGreaterEqual(len(read_json(out / "summary_ru.json")["пропущено"]), 2)

    def test_owner_priority_requires_matching_claim_statement(self):
        a, b = self.bundle("a"), self.bundle("b")
        rec, claims = newsletter.verified(b, dt.date(2026, 11, 8))
        picks = {rec["source_url"]: {claims[0]["key"]: claims[0]["statement"]}}
        with patch.object(newsletter, "owner_picks", return_value=(picks, [])):
            newsletter.render("draft", [a, b], self.home / "picked", as_of="2026-11-08", store=self.home)
        trace = read_json(self.home / "picked/trace.json")
        self.assertEqual(trace["items"][0]["title"], "b")
        self.assertTrue(trace["items"][0]["owner_picked"])
        bad, _ = newsletter.collect([b], dt.date(2026, 11, 8), {rec["source_url"]: {"identity": "invented"}})
        self.assertFalse(bad[0]["picked"])

    def test_real_store_current_pick_is_read_via_existing_verifier(self):
        from tests.test_concept_choose import ConceptChooseTests
        from socialreel import concept_choose
        helper = ConceptChooseTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        job = helper.modified_trial(helper.make_trial())
        view = concept_choose.show(helper.store, job)
        concept = view["proposal"]["concepts"][0]["id"]
        concept_choose.decide(helper.store, job, view["revision"], pick=concept, note="Synthetic owner choice")
        picks, _ = newsletter.owner_picks(helper.store.root)
        self.assertTrue(picks)
        self.assertTrue(next(iter(picks.values())))

    def test_date_guards_and_missing_conditions(self):
        today = dt.date(2026, 11, 8)
        for text in ("2026-11-01", "November 1, 2026", "Nov 1, 2026", "October 1", "11/01/2026", "01.11.2026", "A program from 2020"):
            self.assertTrue(newsletter.past(text, today))
        self.assertFalse(newsletter.past("November 17, 2026", today))

    def test_checklist_complete_rows_html_escape_and_limits(self):
        bundle = self.bundle("places", '<table><tr><td>Expired place</td><td>This program has ended.</td></tr></table>')
        out = self.home / "checklist"
        newsletter.render("checklist", [bundle], out, as_of="2026-11-08")
        text = (out / "checklist.html").read_text(encoding="utf-8")
        self.assertIn("State unclaimed property office", text)
        self.assertIn("You must prove ownership", text)
        self.assertNotIn("Expired place", text)
        self.assertIn('href="https://www.usa.gov/', text)
        self.assertIn("Истёкший", json.dumps(read_json(out / "summary_ru.json"), ensure_ascii=False))

    def test_snapshot_tamper_and_edited_ledger_not_trusted(self):
        b = self.bundle("tamper")
        write_json(b / "claims.json", [{"key": "fake", "statement": "Everyone gets money"}])
        newsletter.render("draft", [b], self.home / "safe", as_of="2026-11-08")
        self.assertNotIn("Everyone gets money", (self.home / "safe/newsletter.md").read_text())
        rec = read_json(b / "record.json")
        (b / rec["provenance"]["file"]).write_bytes(b"changed")
        result = newsletter.render("draft", [b], self.home / "bad", as_of="2026-11-08")
        self.assertEqual(result["items"], 0)

    def test_grants_fixture_rebuilt_from_source_bytes(self):
        from socialreel.common import ROOT, sha256_bytes
        from socialreel import grants
        from socialreel.claims import build_claims
        b = self.home / "grant"; (b / "source").mkdir(parents=True)
        raw = (ROOT / "fixtures/grants_gov_normalized_20261003.json").read_bytes()
        (b / "source/fixture.json").write_bytes(raw)
        original = json.loads(raw)[0]
        rec = grants.from_fixture(original)
        receipt = {"file": "source/fixture.json", "sha256": sha256_bytes(raw)}
        write_json(b / "record.json", rec)
        write_json(b / "claims.json", build_claims(rec, receipt, dt.date(2026, 10, 10)))
        verified, claims = newsletter.verified(b, dt.date(2026, 10, 10))
        self.assertEqual(verified["title"], rec["title"])
        self.assertTrue(claims)

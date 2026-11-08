"""Synthetic SBA integration: real network forbidden."""
import contextlib
import io
from unittest.mock import patch

from socialreel import sba, topics
from socialreel.__main__ import main
from socialreel.common import ROOT, PipelineError, read_json, sha256_bytes, write_json
from socialreel.source_intake import discover_topics, replay_topic, write_bundle
from tests.test_usagov import OfflineSourceCase
from tests.test_concept_offline import config

FIX = ROOT / "fixtures/sba_programs_synthetic.html"


class SBATests(OfflineSourceCase):
    def page(self):
        return sba.SBAClient(self.home / "source").page("loans", fixture=FIX)

    def test_catalog_identity_quotes_and_hashes(self):
        self.assertEqual(len(sba.PAGES), 8)
        rec, receipt = self.page()
        self.assert_receipt(receipt, FIX.read_bytes())
        rows = sba.build_claims(rec, receipt)
        self.assertEqual(rec["rubric"], "small_business_nonprofit")
        self.assertEqual(rec["url_note"], "URL not checked live")
        self.assertTrue(rows[0]["statement"].startswith("SBA.gov page:"))
        self.assertIn("Most SBA grants are not for starting a business", rows[0]["quote"])
        self.assertTrue(any(c["kind"] == "table_row" for c in rows))
        self.assertTrue(any(c["kind"] == "list_item" for c in rows))
        for row in rows:
            self.assertEqual(row["source"]["snapshot_sha256"], receipt["sha256"])
            self.assertEqual(row["source"]["excerpt_sha256"], sha256_bytes(row["quote"].encode()))
            self.assertTrue(row["source"]["locator"])
            self.assertNotIn("noise", row["quote"])
        with self.assertRaises(PipelineError):
            sba.build_claims({**rec, "source_label": "USA.gov"})
        with self.assertRaises(PipelineError):
            sba.SBAClient(self.home).page("https://evil.test/loans", fixture=FIX)

    def test_each_program_keeps_page_conditions_no_clipping(self):
        rec, receipt = self.page()
        claims = sba.build_claims(rec, receipt)
        for program in ("7a", "microloans", "1", "2"):
            selected, rows, report = sba.select_for_core(rec, claims, config(), program=program)
            self.assertEqual(report["state"], "selected")
            self.assertIn("Most SBA grants are not for starting a business", selected["description"])
            self.assertIn("Only eligible businesses may apply", selected["description"])
            for c in rows:
                self.assertEqual(c["quote"], next(x["quote"] for x in claims if x["key"] == c["key"]))
        with self.assertRaises(PipelineError):
            sba.select_for_core(rec, claims, config(), program="invented")
        cfg = config(); cfg["usagov_facts"] = {"max_claims": 1}
        self.assertEqual(sba.select_for_core(rec, claims, cfg, program="7a")[2]["state"], "refused")

    def test_cli_and_multisource_replay(self):
        out = self.home / "cli"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = main(["source", "--source", "sba", "--page", "loans", "--program", "microloans",
                       "--fixture", str(FIX), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertFalse(read_json(out / "request_status.json")["model_called"])
        self.assertEqual(read_json(out / "record.json")["source_type"], "sba")
        manifest = self.home / "manifest.json"
        write_json(manifest, {"sources": [{"source_type": "sba", "page": "loans", "fixture": str(FIX)}]})
        found = discover_topics(config(), self.home / "topics", ["sba"], fixture=manifest)
        self.assertEqual(len(found["topics"]), 2)
        rec, claims = replay_topic(self.home / "topics/topics.json", self.home / "replayed")
        result = write_bundle(rec, claims, self.home / "replayed", config())
        self.assertFalse(result.get("request_refused"))

    def test_small_business_main_and_sba_preference(self):
        rules = topics.configuration({})
        rules["small_business_channel"] = True
        for values, expected in ((["23"], True), (["23", "25"], True),
                                 (["23", "25", "00"], False), (["25"], False), (["23", "99"], False)):
            rec = {"eligible_applicant_types": [{"id": v} for v in values]}
            self.assertEqual(topics.small_business_main(rec, rules), expected)
            if not expected:
                self.assertNotEqual(topics._rubric(rec, rules), "small_business_nonprofit")
        sba_row = {"rubric": "small_business_nonprofit", "source_type": "sba", "score": {"total": 1}, "topic_id": "sba:loans"}
        grant = {**sba_row, "source_type": "grants", "score": {"total": 999}, "topic_id": "grants:1"}
        self.assertEqual(sorted([grant, sba_row], key=topics.public_rank_key)[0], sba_row)

    def test_business_channel_filters_grants_and_prefers_sba_end_to_end(self):
        manifest = self.home / "mixed.json"
        write_json(manifest, {"grants_fixture": str(ROOT / "fixtures/grants_gov_normalized_20261003.json"),
            "sources": [{"source_type": "sba", "page": "loans", "fixture": str(FIX)}]})
        result = discover_topics(config(), self.home / "mixed", ["grants", "sba"],
                                 fixture=manifest, as_of="2026-10-10")
        self.assertEqual(result["topics"][0]["source_type"], "sba")
        rules = topics.configuration({})
        for row in result["topics"]:
            if row["source_type"] == "grants" and row["rubric"] == "small_business_nonprofit":
                self.assertTrue(topics.small_business_main(row, rules))

    def test_expired_units_marked_and_excluded(self):
        raw = FIX.read_text().replace("This synthetic loan program", "This program has ended. This synthetic loan program")
        path = self.home / "expired.html"; path.write_text(raw)
        rec, receipt = sba.SBAClient(self.home / "source").page("loans", fixture=path)
        claims = sba.build_claims(rec, receipt)
        self.assertTrue(any(c["expired"] for c in claims))
        self.assertEqual(sba.select_for_core(rec, claims, config(), program="7a")[2]["state"], "refused")

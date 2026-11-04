"""Synthetic HTML, actual parsers/claim producers and core; real network forbidden."""
import contextlib
import copy
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

from socialreel import concept_core as core, topics, usagov
from socialreel.__main__ import main
from socialreel.common import ROOT, PipelineError, read_json, sha256_bytes, write_json
from socialreel.public_sources import MainHTML, OfficialRedirects, html_record
from socialreel.source_intake import replay_topic, write_bundle
from tests.test_concept_offline import config
from tests.test_concept_source_cards import inspect_request

FIX = ROOT / "fixtures"


class Response:
    status = 200

    def __init__(self, raw, url):
        self.raw, self.url = raw, url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.raw

    def geturl(self):
        return self.url


class OfflineSourceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        for target in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
                       "urllib.request.urlopen", "urllib.request.OpenerDirector.open"):
            guard = patch(target, side_effect=AssertionError("Real network forbidden in source tests"))
            guard.start()
            self.addCleanup(guard.stop)

    def assert_receipt(self, receipt, original):
        raw = (self.home / receipt["file"]).read_bytes()
        self.assertEqual(raw, original)
        self.assertEqual(sha256_bytes(raw), receipt["sha256"])
        self.assertEqual(len(raw), receipt["bytes"])


class USAGovTests(OfflineSourceCase):
    def acquire(self, page="energy"):
        fixture_name = "wages" if page == "wage_laws" else page
        return usagov.USAGovClient(self.home / "source").page(page, fixture=FIX / f"usagov_{fixture_name}_synthetic.html")

    def test_fixture_raw_bytes_hash_and_complete_conditions_in_claims(self):
        record, receipt = self.acquire()
        self.assert_receipt(receipt, (FIX / "usagov_energy_synthetic.html").read_bytes())
        self.assertTrue(record["fixture_only"])
        self.assertTrue(record["conditions"])
        self.assertTrue(record["state_rules_differ"])
        rows = usagov.build_claims(record, receipt)
        text = "\n".join(row["statement"] for row in rows)
        for phrase in ("may qualify only if", "$25,000", "not a national limit", "Rules differ by state",
                       "Only the responsible office", "excluded unless", "Only eligible households may apply"):
            self.assertIn(phrase, text)
        for row in rows:
            self.assertEqual(row["source"]["snapshot_sha256"], receipt["sha256"])
            self.assertTrue(row["source"]["locator"])
            self.assertEqual(sha256_bytes(row["source"]["quote"].encode()), row["source"]["excerpt_sha256"])

    def test_never_labelled_grants_and_never_everyone_gets_money(self):
        record, _ = self.acquire()
        rows = usagov.build_claims(record)
        text = "\n".join(row["statement"] for row in rows)
        self.assertTrue(rows[0]["statement"].startswith("USA.gov page:"))
        self.assertNotIn("Grants.gov", text)
        self.assertNotIn("Everyone gets money automatically", text)
        self.assertIn("Help is not guaranteed", text)
        self.assertEqual(record["source_type"], "usagov")

    def test_wages_keeps_recovery_identity_and_exclusions(self):
        record, _ = self.acquire("wage_laws")
        rows = usagov.build_claims(record)
        text = "\n".join(row["statement"] for row in rows)
        self.assertIn("only if the Wage and Hour Division recovered wages", text)
        self.assertIn("You must prove your identity", text)
        self.assertIn("does not cover wages the agency has not recovered", text)
        self.assertIsNone(record["state_rules_differ"])

    def test_unclaimed_keeps_ownership_and_state_rules(self):
        record, _ = self.acquire("unclaimed")
        text = "\n".join(row["statement"] for row in usagov.build_claims(record))
        self.assertIn("proof of ownership", text)
        self.assertIn("Requirements vary by state", text)
        self.assertTrue(record["state_rules_differ"])

    def test_actual_core_inputs_and_request_keep_conditions_and_explicit_topic(self):
        record, _ = self.acquire()
        rows = usagov.build_claims(record)
        cfg = config()
        cfg["selection"] = {"public_reference_topic": "energy"}
        before = copy.deepcopy((record, rows, cfg))
        captured = inspect_request(record, rows, cfg)
        prompt = json.loads(captured["body"]["prompt"])
        text = prompt["source_context"]["condition_fields"][0]["text"]
        self.assertIn("Rules differ by state", text)
        self.assertIn("excluded unless", text)
        self.assertNotIn(str(self.home), captured["body"]["prompt"])
        self.assertEqual(prompt["topic_intent"], "energy")
        self.assertEqual(before, (record, rows, cfg))
        cfg["selection"] = {"public_reference_topic": "wages"}
        with self.assertRaisesRegex(PipelineError, "differs"):
            core.inputs(record, rows, cfg)

    def test_fake_live_transport_saves_exact_html(self):
        raw = (FIX / "usagov_energy_synthetic.html").read_bytes() + b"\r\n "
        requests = []
        def transport(request, **kwargs):
            requests.append(request)
            return Response(raw, request.full_url)
        record, receipt = usagov.USAGovClient(self.home / "source", transport=transport).page("energy")
        self.assert_receipt(receipt, raw)
        self.assertFalse(record["fixture_only"])
        self.assertEqual(len(requests), 1)

    def test_official_host_validation_redirect_and_mislabelled_replay_rejected(self):
        with self.assertRaises(PipelineError):
            usagov.USAGovClient(self.home / "source").page("https://example.invalid/energy")
        redirect = OfficialRedirects(("www.usa.gov",))
        with self.assertRaises(PipelineError):
            redirect.redirect_request(urllib.request.Request(usagov.PAGES["energy"]), None, 302, "", {}, "https://example.invalid/source")
        record, receipt = self.acquire()
        with self.assertRaises(PipelineError):
            html_record((FIX / "usagov_energy_synthetic.html").read_bytes(), {**receipt, "url": "https://studentaid.gov/fake"}, "usagov")
        with self.assertRaises(PipelineError):
            usagov.build_claims({**record, "source_type": "grants"})

    def test_js_shell_ambiguous_main_invalid_utf8_fail_without_fabrication(self):
        for raw in (b"<html><div id='root'></div><script>render()</script></html>",
                    b"<main><h1>A</h1><p>A</p></main><main><h1>B</h1><p>B</p></main>", b"\xff"):
            path = self.home / "bad.html"
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(PipelineError):
                usagov.USAGovClient(self.home / "source").page("energy", fixture=path)

    def test_long_source_is_kept_and_existing_core_refuses_without_clipping(self):
        raw = b"<main><h1>Synthetic</h1><p>" + b"Only eligible households may apply. " * 500 + b"</p></main>"
        path = self.home / "long.html"
        path.write_bytes(raw)
        record, receipt = usagov.USAGovClient(self.home / "source").page("energy", fixture=path)
        rows = usagov.build_claims(record)
        self.assert_receipt(receipt, raw)
        self.assertIn("Only eligible households may apply. " * 499, rows[0]["quote"])
        with self.assertRaisesRegex(PipelineError, str(core.SOURCE_CONTEXT_BYTES) + ".*no clipping"):
            core.build_request(record, rows, config())

    def test_source_cli_writes_same_downstream_inputs_without_model(self):
        out = self.home / "bundle"
        with contextlib.redirect_stdout(io.StringIO()):
            status = main(["source", "--source", "usagov", "--page", "energy", "--fixture",
                           str(FIX / "usagov_energy_synthetic.html"), "--out", str(out)])
        self.assertEqual(status, 0)
        self.assertEqual(read_json(out / "record.json")["source_type"], "usagov")
        self.assertTrue(read_json(out / "claims.json"))
        self.assertIn("factual_core", read_json(out / "concept_inputs.json"))
        self.assertFalse((out / "concept_request.json").exists())

    def test_existing_admission_refusal_is_reported_and_never_bypassed(self):
        record, _ = self.acquire()
        rows = usagov.build_claims(record)
        with patch("socialreel.concept_admission.admit", side_effect=PipelineError("Synthetic admission refusal")) as admit:
            result = write_bundle(record, rows, self.home / "bundle", config(), prepare_request=True)
        admit.assert_called_once()
        self.assertTrue(result["request_refused"])
        self.assertFalse(result["model_called"])
        self.assertFalse((self.home / "bundle" / "concept_request.json").exists())
        self.assertEqual(read_json(self.home / "bundle" / "request_status.json")["state"], "refused")

    def test_inline_main_text_and_nested_paragraphs_keep_word_boundaries(self):
        path = self.home / "inline.html"
        path.write_bytes(b"<main><h1>Synthetic</h1><div>You <strong>may</strong> apply <em>only</em> if eligible.</div>"
                         b"<ul><li><p>You must qualify.</p><p>Exceptions apply.</p></li></ul></main>")
        record, _ = usagov.USAGovClient(self.home / "source").page("energy", fixture=path)
        self.assertIn("You may apply only if eligible.", record["description"])
        self.assertIn("You must qualify.\nExceptions apply.", record["description"])

    def test_custom_page_topic_id_stable_across_content_updates(self):
        path = self.home / "page.html"
        client = usagov.USAGovClient(self.home / "source")
        ids = []
        for text in ("You may apply only if eligible.", "You must check updated conditions."):
            path.write_text(f"<main><h1>Synthetic</h1><p>{text}</p></main>", encoding="utf-8")
            record, _ = client.page("https://www.usa.gov/synthetic-page", fixture=path)
            ids.append(record["topic_id"])
        self.assertEqual(ids[0], ids[1])

    def test_failed_preparation_removes_previous_request_without_changing_core(self):
        record, _ = self.acquire()
        rows = usagov.build_claims(record)
        out = self.home / "bundle"
        write_json(out / "concept_request.json", {"old": "request must not remain"})
        with patch("socialreel.concept_admission.admit", side_effect=PipelineError("Synthetic refusal")):
            write_bundle(record, rows, out, config(), prepare_request=True)
        self.assertFalse((out / "concept_request.json").exists())

    def test_multisource_topics_fixture_and_replay_are_deterministic_and_bound(self):
        cfg = {"topics": {"seen_file": None}}
        outputs = []
        for name in ("first", "second"):
            outputs.append(topics.run(cfg, self.home / name, sources=["usagov", "studentaid"],
                                      fixture=FIX / "public_sources_synthetic.json", as_of="2026-11-04"))
        self.assertEqual(outputs[0], outputs[1])
        result = outputs[0]
        self.assertEqual({row["rubric"] for row in result["topics"]}, {"help_people", "education"})
        self.assertEqual({row["source_type"] for row in result["topics"]}, {"usagov", "studentaid"})
        for receipt in result["sources"]:
            self.assertEqual(sha256_bytes((self.home / "first" / receipt["file"]).read_bytes()), receipt["sha256"])
        record, rows = replay_topic(self.home / "first" / "topics.json", self.home / "replay", "usagov:energy")
        self.assertEqual(record["source_type"], "usagov")
        self.assertIn("Rules differ by state", str(rows))
        core.inputs(record, rows, config())
        receipt = result["topics"][0]["provenance"]
        (self.home / "first" / receipt["file"]).write_bytes(b"changed")
        with self.assertRaisesRegex(PipelineError, "SHA-256 differs"):
            replay_topic(self.home / "first" / "topics.json", self.home / "bad-replay")

    def test_fixture_manifest_never_falls_back_to_live_source(self):
        path = self.home / "manifest.json"
        write_json(path, {"sources": []})
        with self.assertRaisesRegex(PipelineError, "live fallback forbidden"):
            topics.run({}, self.home / "out", sources=["usagov"], fixture=path)

    def test_replay_rebuilds_claims_instead_of_trusting_edited_topic_text(self):
        out = self.home / "topics"
        data = topics.run({}, out, sources=["usagov"], fixture=FIX / "public_sources_synthetic.json", as_of="2026-11-04")
        item = next(row for row in data["topics"] if row["topic_id"] == "usagov:energy")
        item["record"]["description"] = "Everyone gets money."
        item["record"]["public_reference_topic"] = "wages"
        item["claims"][0]["statement"] = "Invented statement"
        write_json(out / "topics.json", data)
        record, rows = replay_topic(out / "topics.json", self.home / "replay", "usagov:energy")
        self.assertEqual(record["public_reference_topic"], "energy")
        self.assertNotIn("Invented statement", str(rows))
        self.assertNotIn("Everyone gets money.", record["description"])

    def test_mixed_grants_and_public_fixture_replays_existing_grant_path(self):
        out = self.home / "topics"
        data = topics.run({}, out, sources=["grants", "usagov", "studentaid", "scorecard"],
                          fixture=FIX / "public_sources_synthetic.json", as_of="2026-11-04")
        grant = next(row for row in data["topics"] if row["source_type"] == "grants")
        record, rows = replay_topic(out / "topics.json", self.home / "replay", grant["topic_id"])
        self.assertEqual(record["source_type"], "grants")
        self.assertTrue(rows[0]["statement"].startswith("Grants.gov lists"))
        core.inputs(record, rows, config())
        for receipt in data["sources"]:
            self.assertEqual(sha256_bytes((out / receipt["file"]).read_bytes()), receipt["sha256"])

    def test_namespaced_seen_topic_loses_novelty_points(self):
        write_json(self.home / "seen.json", ["usagov:energy"])
        data = topics.run({"topics": {"seen_file": "seen.json"}}, self.home / "out", sources=["usagov"],
                          fixture=FIX / "public_sources_synthetic.json", as_of="2026-11-04", config_dir=self.home)
        rows = {row["topic_id"]: row for row in data["topics"]}
        self.assertLess(rows["usagov:energy"]["score"]["total"], rows["usagov:wage_laws"]["score"]["total"])
        self.assertTrue(rows["usagov:energy"]["score"]["components"]["novelty"]["seen"])

    def test_real_network_guard_is_active(self):
        with self.assertRaisesRegex(AssertionError, "Real network forbidden"):
            socket.create_connection(("example.invalid", 443))


if __name__ == "__main__":
    unittest.main()

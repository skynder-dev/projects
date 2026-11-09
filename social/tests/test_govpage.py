"""Synthetic federal HTML and demand integration; no real network or models."""
import ast
import contextlib
import importlib.util
import io
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

from socialreel import govpage
from socialreel.__main__ import main
from socialreel.common import ROOT, PipelineError, read_json, sha256_bytes, write_json
from socialreel.demand_channels import CHANNELS, bundle_audience
from socialreel.source_intake import write_bundle
from tests.test_usagov import OfflineSourceCase, Response
from tests.test_concept_offline import config


def load_picker():
    spec = importlib.util.spec_from_file_location("demand_picker_test", ROOT / "trial/demand_pick.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GovPageTests(OfflineSourceCase):
    def page(self, agency="irs", url=None):
        url = url or f"https://www.{agency}.gov/benefit-information"
        return govpage.GovPageClient(self.home / "source").page(
            url, fixture=ROOT / f"fixtures/govpage_{agency}_synthetic.html")

    def test_irs_layout_sidebar_body_and_title_before_main(self):
        # 08.11.2026 live irs.gov: <body class="layout-sidebar-first"> and the page h1 just before <main>
        rec, receipt = govpage.GovPageClient(self.home / "source").page(
            "https://www.irs.gov/refunds", fixture=ROOT / "fixtures/govpage_irs_layout_synthetic.html")
        self.assertEqual(rec["title"], "Synthetic IRS information guide")
        text = rec["description"]
        self.assertIn("Help is not guaranteed", text)
        self.assertNotIn("RELATED NOISE", text)
        self.assertTrue(govpage.build_claims(rec, receipt))

    def test_four_agencies_exact_provenance_and_complete_conditions(self):
        for agency in ("irs", "ssa", "sba", "va"):
            with self.subTest(agency=agency):
                rec, receipt = self.page(agency)
                self.assert_receipt(receipt, (ROOT / f"fixtures/govpage_{agency}_synthetic.html").read_bytes())
                rows = govpage.build_claims(rec, receipt)
                self.assertEqual(rec["source_type"], "govpage")
                self.assertTrue(rows[0]["statement"].startswith("U.S. government page:"))
                self.assertNotIn("USA.gov page:", rows[0]["statement"])
                text = "\n".join(c["quote"] for c in rows)
                for phrase in ("only if", "not guaranteed", "must keep", "does not establish eligibility"):
                    self.assertIn(phrase, text)
                for noise in ("HEADER NOISE", "NAV NOISE", "RELATED NOISE", "FOOTER NOISE", "SEARCH NOISE"):
                    self.assertNotIn(noise, text)
                self.assertIn("Accordion condition", text)
                for c in rows:
                    self.assertEqual(c["source"]["snapshot_sha256"], receipt["sha256"])
                    self.assertEqual(sha256_bytes(c["quote"].encode()), c["source"]["excerpt_sha256"])
                    self.assertTrue(c["source"]["locator"])
                with self.assertRaises(PipelineError):
                    govpage.build_claims({**rec, "source_type": "usagov"})
                with self.assertRaises(PipelineError):
                    govpage.build_claims(rec, {**receipt, "sha256": "0" * 64})

    def test_refuses_shell_and_form_without_record(self):
        for name in ("js_shell", "form_login"):
            out = self.home / name
            with contextlib.redirect_stderr(io.StringIO()) as err:
                rc = main(["source", "--source", "govpage", "--url", "https://www.irs.gov/information",
                           "--fixture", str(ROOT / f"fixtures/govpage_{name}_synthetic.html"), "--out", str(out)])
            self.assertEqual(rc, 2)
            self.assertIn("SOURCE FAILED", err.getvalue())
            self.assertFalse((out / "record.json").exists())
            self.assertFalse((out / "concept_request.json").exists())

    def test_small_ambiguous_article_only_invalid_html_refused(self):
        for raw in (b"<main><h1>Only a title</h1><p>Too short.</p></main>",
                    b"<main><h1>A</h1></main><main><h1>B</h1></main>",
                    b"<article><h1>Article without main</h1><p>Text</p></article>", b"\xff"):
            path = self.home / "bad.html"
            path.write_bytes(raw)
            with self.assertRaises(PipelineError):
                govpage.GovPageClient(self.home / "source").page("https://www.irs.gov/info", fixture=path)

    def test_urls_and_redirects_rejected_before_fetch(self):
        for url in ("http://www.irs.gov/info", "https://irs.gov/info", "https://www.irs.gov.evil.test/info",
                    "https://www.irs.gov/info?q=x", "https://www.irs.gov/info?", "https://www.irs.gov/info#x",
                    "https://me@www.irs.gov/info", "https://www.irs.gov:444/info", "https://www.irs.gov/login",
                    "https://www.irs.gov/payments", "https://www.irs.gov/tools/check", "https://www.ssa.gov/calculator",
                    "https://www.irs.gov/%66orms", "https://www.irs.gov/a\nb"):
            with self.subTest(url=url), self.assertRaises((PipelineError, ValueError)):
                govpage.GovPageClient(self.home / "source").page(url)
            with self.assertRaises((PipelineError, ValueError)):
                govpage.GovPageRedirects(govpage.allowed_hosts()).redirect_request(
                    __import__("urllib.request", fromlist=["Request"]).Request("https://www.irs.gov/info"),
                    None, 302, "", {}, url)
        self.assertFalse((self.home / "record.json").exists())
        self.assertEqual(len(govpage.allowed_hosts()), 8)
        with patch.object(govpage, "read_json", return_value={"govpage": {"hosts": ["example.org"]}}):
            with self.assertRaises(PipelineError):
                govpage.allowed_hosts()
        for value in ({}, {"govpage": None}, {"govpage": {"hosts": []}}):
            with patch.object(govpage, "read_json", return_value=value), self.assertRaises(PipelineError):
                govpage.allowed_hosts()

    def test_fake_live_final_url_and_transport_errors(self):
        raw = (ROOT / "fixtures/govpage_irs_synthetic.html").read_bytes()
        for final in ("https://www.irs.gov/information?q=x", "https://www.irs.gov/forms"):
            with self.assertRaises(PipelineError):
                govpage.GovPageClient(self.home / "source", transport=lambda *a, **k: Response(raw, final)).page(
                    "https://www.irs.gov/information")
        client = govpage.GovPageClient(self.home / "source", transport=lambda req, **k: Response(raw, req.full_url))
        rec, receipt = client.page("https://www.irs.gov/information")
        self.assertFalse(rec["fixture_only"])
        self.assert_receipt(receipt, raw)
        self.assertEqual(len(client.calls), 1)

    def test_cli_and_existing_core_bundle(self):
        out = self.home / "bundle"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = main(["source", "--source", "govpage", "--url", "https://www.irs.gov/benefit-information",
                       "--fixture", str(ROOT / "fixtures/govpage_irs_synthetic.html"), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertEqual(read_json(out / "claim_selection.json")["state"], "selected")
        self.assertTrue(read_json(out / "concept_inputs.json")["factual_core"])
        self.assertFalse(read_json(out / "request_status.json")["model_called"])
        rec, receipt = self.page()
        cfg = config()
        cfg["usagov_facts"] = {"max_claims": 1}
        result = write_bundle(rec, govpage.build_claims(rec, receipt), out, cfg)
        self.assertTrue(result["request_refused"])
        self.assertFalse((out / "concept_request.json").exists())

    def test_demand_ranking_skip_used_failures_duplicates_channels_and_bundles(self):
        picker = load_picker()
        used = self.home / "used.json"
        write_json(used, ["https://www.irs.gov/used/"])
        pages = [
            {"url": "https://www.irs.gov/used", "channel": "Помощь людям", "views_30d": 1000},
            {"url": "https://www.irs.gov/shell", "channel": "Помощь людям", "views_30d": 900},
            {"url": "https://www.irs.gov/low", "channel": "Помощь людям", "views_30d": 20},
            {"url": "https://www.irs.gov/high", "channel": "Помощь людям", "views_30d": 300},
            {"url": "https://www.irs.gov/high/", "channel": "Помощь людям", "views_30d": 200},
            {"url": "https://www.irs.gov/ignored", "channel": "Помощь людям", "views_30d": 5},
            {"url": "https://evil.example/info", "channel": "Учёба", "views_30d": 9999},
        ]
        for i, channel in enumerate(list(CHANNELS)[1:]):
            pages.append({"url": f"https://www.sba.gov/info-{i}", "channel": channel, "views_30d": 100 + i})
        pages.append({"url": "https://www.usa.gov/synthetic-guide", "channel": "Учёба", "views_30d": 2})
        requested = []
        class FixtureClient:
            def __init__(self, kind, directory):
                self.kind, self.directory = kind, directory
            def page(self, url):
                requested.append(url)
                from socialreel import usagov
                client = govpage.GovPageClient(self.directory) if self.kind == "govpage" else usagov.USAGovClient(self.directory)
                name = "js_shell" if url.endswith("shell") else "irs"
                return client.page(url, fixture=ROOT / f"fixtures/govpage_{name}_synthetic.html")
        result = picker.pick({"pages": pages}, self.home / "picked", per_channel=2,
                             used_path=used, client_factory=FixtureClient, cfg=config())
        selected = [p["url"] for p in result["picks"] if p["channel"] == "Помощь людям"]
        self.assertEqual(selected, ["https://www.irs.gov/high", "https://www.irs.gov/low"])
        self.assertNotIn("https://www.irs.gov/used", requested)
        self.assertNotIn("https://www.irs.gov/high/", requested)
        self.assertNotIn("https://www.irs.gov/ignored", requested)
        self.assertEqual({p["channel"] for p in result["picks"]}, set(CHANNELS))
        self.assertIn("usagov", {p["source_type"] for p in result["picks"]})
        self.assertEqual(read_json(used), ["https://www.irs.gov/used/"])
        self.assertTrue(any("JavaScript" in s["reason"] for s in result["skipped"]))
        for p in result["picks"]:
            b = self.home / "picked" / p["bundle"]
            self.assertEqual(read_json(b / "concept_record.json")["channel"], p["channel"])
            self.assertEqual(read_json(b / "record.json")["channel"], p["channel"])
            self.assertEqual(read_json(b / "claim_selection.json")["state"], "selected")

    def test_bundle_trial_and_card_preserve_explicit_channel_without_network(self):
        # Execute actual --bundle path until core request capture; stop before inference.
        rec, receipt = self.page("sba")
        rec["channel"] = "Малый бизнес и НКО"
        bundle, out = self.home / "bundle", self.home / "trial"
        write_bundle(rec, govpage.build_claims(rec, receipt), bundle, config())
        from socialreel import concept_admission
        with patch.object(sys, "argv", ["concept_trial.py", str(ROOT), str(out), "--bundle", str(bundle)]), \
                patch.object(concept_admission, "admit", side_effect=PipelineError("test_stop_before_inference")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / "trial/concept_trial.py"), run_name="__main__")
        trial = read_json(out / "trial.json")
        self.assertEqual(trial["state"], "admission_refused")
        self.assertEqual(trial["stages"]["source"]["api_calls"], 0)
        self.assertEqual(trial["stages"]["topic_audience"]["channel"], rec["channel"])
        self.assertTrue(trial["stages"]["claims"])
        # Load only the pure card-routing function; no model discovery at import.
        tree = ast.parse((ROOT / "trial/make_cards.py").read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "channel")
        ns = {"re": __import__("re"), "json": json, "PAGES_RU": {"financial_aid": "Учёба"}}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "make_cards.py", "exec"), ns)
        for channel in CHANNELS:
            audience = bundle_audience({"channel": channel})
            self.assertEqual(ns["channel"]({"topic_audience": audience, "source": {"title": "Student aid"}}), channel)
        self.assertEqual(ns["channel"]({"topic_audience": {"people": True}, "source": {"title": "Student aid"}}), "Учёба")

    def test_picker_bad_input_and_empty_success(self):
        picker = load_picker()
        for value in (0, -1, True):
            with self.assertRaises(PipelineError):
                picker.pick({"pages": []}, self.home, per_channel=value)
        with self.assertRaises(PipelineError):
            picker.pick([], self.home)
        result = picker.pick({"pages": []}, self.home, used_path=self.home / "missing.json", cfg=config())
        self.assertEqual(result["picks"], [])
        self.assertFalse(result["model_called"])
        result = picker.pick({"pages": [{"url": "https://www.irs.gov/info", "channel": [], "views_30d": 1},
                                      {"url": "https://www.irs.gov/info", "channel": "Учёба", "views_30d": float("nan")} ]},
                             self.home, used_path=self.home / "missing.json", cfg=config())
        self.assertEqual(result["picks"], [])
        self.assertEqual(len(result["skipped"]), 2)

"""Structural USA.gov fixtures and bounded whole-fact handoff; network forbidden."""
import contextlib
import copy
import io
import json
from unittest.mock import patch

from socialreel import concept_admission as admission, topics, usagov
from socialreel.__main__ import main
from socialreel.common import PipelineError, read_json, sha256_bytes, stable_json, write_json
from socialreel.source_intake import write_bundle
from socialreel.usagov_facts import select_for_core
from tests.test_concept_offline import config
from tests.test_concept_source_cards import inspect_request
from tests.test_usagov import FIX, OfflineSourceCase


class USAGovFactsTests(OfflineSourceCase):
    def acquire(self, structure, page="unclaimed"):
        record, receipt = usagov.USAGovClient(self.home / "source").page(
            page, fixture=FIX / f"usagov_{structure}_synthetic.html")
        return record, usagov.build_claims(record), receipt

    def raw_page(self, html):
        path = self.home / "synthetic.html"
        path.write_text("<!-- SYNTHETIC OFFLINE -->" + html, encoding="utf-8")
        record, receipt = usagov.USAGovClient(self.home / "source").page("unclaimed", fixture=path)
        return record, usagov.build_claims(record), receipt

    def test_sections_are_separate_with_exact_quotes_and_hierarchy(self):
        record, rows, _ = self.acquire("sections")
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["quote"], "Synthetic assistance\nSynthetic lead & exact introductory text.")
        self.assertEqual(rows[1]["quote"], "Who can apply\nHouseholds may apply only if they meet the office's requirements.")
        self.assertEqual(rows[2]["quote"], "Proof\nYou must provide identity documents. Exceptions depend on the office.")
        path = rows[2]["locator"]["heading_path"]
        self.assertEqual([(h["level"], h["text"]) for h in path], [(2, "Who can apply"), (3, "Proof")])
        self.assertIn(rows[1]["key"], rows[2]["values"]["required_context_keys"])
        self.assertEqual(rows[-1]["quote"], "Only eligible applicants may apply")
        self.assertEqual(len(record["sections"]), 6)  # lead plus five headed sections

    def test_list_options_keep_complete_conditions_as_separate_facts(self):
        _, rows, _ = self.acquire("list")
        self.assertEqual(len(rows), 5)
        options = [r for r in rows if r["kind"] == "list_item"]
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0]["quote"], "Recovered wages — Search the official service. You must prove your identity.")
        self.assertEqual(options[1]["quote"], "Tax refunds\nAsk the tax agency about your refund.\nOnly the agency can determine whether it owes a refund.")
        self.assertIn(" & follow", options[2]["quote"])
        for row in options:
            self.assertTrue(row["locator"]["list"].endswith("/ul[1]"))
            self.assertIn("/li[", row["locator"]["item"])
            self.assertEqual(row["values"]["required_context_keys"], [rows[1]["key"]])

    def test_table_rows_have_columns_headers_caption_and_exact_quote(self):
        _, rows, _ = self.acquire("table")
        facts = [r for r in rows if r["kind"] == "table_row"]
        self.assertEqual(len(rows), 6)
        self.assertEqual(len(facts), 4)
        first = facts[0]
        self.assertEqual(first["quote"], "Employers\nUnpaid wages — Search the Department of Labor's database. You may claim only if the agency recovered wages for you.")
        loc = first["locator"]
        self.assertEqual(loc["row_number"], 2)  # includes the header row
        self.assertEqual(loc["caption"], "Synthetic search options")
        self.assertEqual([c["header"] for c in loc["columns"]], ["Holder", "Search and conditions"])
        self.assertEqual([c["column"] for c in loc["columns"]], [1, 2])
        self.assertTrue(loc["columns"][0]["path"].endswith("/th[1]"))
        self.assertTrue(loc["columns"][1]["path"].endswith("/td[1]"))
        self.assertTrue(loc["columns"][1]["header_path"].endswith("/th[2]"))
        self.assertEqual(first["quote"], "\n".join(c["text"] for c in loc["columns"]))

    def test_every_fact_binds_exact_quote_locator_and_original_snapshot(self):
        for structure in ("sections", "list", "table"):
            with self.subTest(structure=structure):
                _, rows, receipt = self.acquire(structure)
                self.assert_receipt(receipt, (FIX / f"usagov_{structure}_synthetic.html").read_bytes())
                for row in rows:
                    self.assertEqual(row["source"]["snapshot_sha256"], receipt["sha256"])
                    self.assertEqual(row["source"]["quote"], row["quote"])
                    self.assertEqual(row["source"]["locator"], row["locator"])
                    self.assertEqual(row["source"]["excerpt_sha256"], sha256_bytes(row["quote"].encode("utf-8")))
                    if row["kind"] != "page":
                        self.assertEqual(row["statement"], row["quote"])

    def test_navigation_breadcrumbs_feedback_call_chat_footer_not_facts(self):
        record, rows, _ = self.acquire("sections")
        text = record["description"] + "\n" + "\n".join(r["quote"] for r in rows)
        for noise in ("sentinel", "Was this page helpful", "Call USAGov", "Chat with USAGov"):
            self.assertNotIn(noise, text)
        self.assertIn("Rules differ by state", text)  # hidden conditions remain

    def test_keys_survive_inserting_unrelated_table_row(self):
        raw = (FIX / "usagov_table_synthetic.html").read_text(encoding="utf-8")
        _, before, _ = self.raw_page(raw)
        raw = raw.replace("<tbody>", "<tbody><tr><th>Other holder</th><td>Other search.</td></tr>")
        _, after, _ = self.raw_page(raw)
        self.assertEqual({r["quote"]: r["key"] for r in before},
                         {r["quote"]: r["key"] for r in after if r["quote"] in {b["quote"] for b in before}})
        old = next(r for r in before if r["kind"] == "table_row")
        new = next(r for r in after if r["key"] == old["key"])
        self.assertNotEqual(old["locator"]["row"], new["locator"]["row"])

    def test_list_keys_survive_unrelated_option_insertion(self):
        raw = (FIX / "usagov_list_synthetic.html").read_text(encoding="utf-8")
        _, before, _ = self.raw_page(raw)
        _, after, _ = self.raw_page(raw.replace("<ul>", "<ul><li><b>Other</b> — Another option.</li>"))
        keys = {r["quote"]: r["key"] for r in after}
        for row in before:
            self.assertEqual(row["key"], keys[row["quote"]])

    def test_layout_table_does_not_swallow_headings(self):
        _, rows, _ = self.raw_page("<main><h1>Synthetic</h1><table role='presentation'><tr><td>"
            "<h2>First</h2><p>First complete section.</p><h2>Second</h2><p>Second complete section.</p>"
            "</td></tr></table></main>")
        self.assertEqual([r["kind"] for r in rows], ["page", "section", "section"])
        self.assertEqual(rows[-1]["quote"], "Second\nSecond complete section.")

    def test_expired_row_retained_in_ledger_but_absent_from_concept_handoff(self):
        record, rows, _ = self.acquire("table")
        expired = next(r for r in rows if "Stimulus checks" in r["quote"])
        self.assertIs(expired["expired"], True)
        out = self.home / "bundle"
        result = write_bundle(record, rows, out, config())
        self.assertFalse(result.get("request_refused", False))
        self.assertIn(expired, read_json(out / "claims.json"))
        report = read_json(out / "claim_selection.json")
        self.assertIn(expired["key"], report["expired_keys"])
        self.assertIn({"key": expired["key"], "reason": "expired"}, report["dropped"])
        for name in ("concept_record.json", "concept_claims.json", "concept_inputs.json"):
            self.assertNotIn("Stimulus", (out / name).read_text(encoding="utf-8"))
            self.assertNotIn("has ended", (out / name).read_text(encoding="utf-8"))
        selected_record, selected, _ = select_for_core(record, rows, config())
        body = inspect_request(selected_record, selected, config())["body"]
        self.assertNotIn("Stimulus", body["prompt"])
        self.assertLess(len(stable_json(body).encode()), admission.BASE_BYTES)

    def test_expired_ancestor_marks_children_and_refuses_current_help(self):
        record, rows, _ = self.raw_page("<main><h1>Synthetic</h1><p>Historical source.</p>"
            "<h2>Past program</h2><p>The application period has ended.</p>"
            "<ul><li><b>Old option</b> — Contact the former program.</li></ul></main>")
        self.assertTrue(all(r["expired"] for r in rows[1:]))
        out = self.home / "bundle"
        write_json(out / "concept_inputs.json", {"stale": True})
        write_json(out / "concept_request.json", {"stale": True})
        result = write_bundle(record, rows, out, config(), prepare_request=True)
        self.assertTrue(result["request_refused"])
        self.assertFalse((out / "concept_inputs.json").exists())
        self.assertFalse((out / "concept_request.json").exists())
        self.assertEqual(read_json(out / "concept_claims.json"), [])
        self.assertEqual(len(read_json(out / "claims.json")), 3)

    def test_expired_only_table_not_offered_as_current_topic(self):
        path = self.home / "expired.html"
        path.write_text("<!-- SYNTHETIC --><main><h1>Synthetic</h1><p>Historical source.</p>"
            "<h2>Where to search</h2><table><tr><td>Old program</td><td>The claim period has ended.</td></tr></table></main>", encoding="utf-8")
        manifest = self.home / "manifest.json"
        write_json(manifest, {"sources": [{"source_type": "usagov", "page": "unclaimed", "fixture": path.name}]})
        data = topics.run({}, self.home / "topics", sources=["usagov"], fixture=manifest, as_of="2026-11-04")
        self.assertEqual(data["topics"], [])
        self.assertEqual(data["excluded"][0]["exclusion"]["code"], "no_current_complete_facts")
        with contextlib.redirect_stdout(io.StringIO()):
            status = main(["source", "--source", "usagov", "--page", "unclaimed", "--fixture", str(path), "--out", str(self.home / "cli")])
        self.assertEqual(status, 2)

    def test_mixed_topic_lists_current_keys_and_keeps_expired_archive(self):
        manifest = self.home / "manifest.json"
        write_json(manifest, {"sources": [{"source_type": "usagov", "page": "unclaimed",
                                           "fixture": str(FIX / "usagov_table_synthetic.html")}]})
        data = topics.run({}, self.home / "topics", sources=["usagov"], fixture=manifest, as_of="2026-11-04")
        item = data["topics"][0]
        expired = {r["key"] for r in item["claims"] if r["expired"]}
        self.assertTrue(expired)
        self.assertTrue(expired.isdisjoint(item["claim_selection"]["selected_keys"]))
        self.assertFalse(item["exclusion"]["excluded"])

    def test_selection_is_deterministic_complete_and_prioritizes_table_rows(self):
        html = "<main><h1>Synthetic</h1><p>Complete lead.</p><h2>Conditions</h2><p>You must meet the requirements.</p>"
        html += "<h2>Background</h2><p>Background information.</p><h2>Where to search</h2><table>"
        html += "".join(f"<tr><td>Holder {i}</td><td>Search office {i}. Follow its instructions.</td></tr>" for i in range(20))
        html += "</table><h2>Other options</h2><ul><li>Other full option.</li></ul></main>"
        record, rows, _ = self.raw_page(html)
        cfg = config()
        cfg["usagov_facts"] = {"max_claims": 6}
        before = copy.deepcopy((record, rows, cfg))
        first = select_for_core(record, rows, cfg)
        self.assertEqual(first, select_for_core(record, rows, cfg))
        self.assertEqual(before, (record, rows, cfg))
        rec, selected, report = first
        self.assertEqual(report["state"], "selected")
        self.assertEqual(len(selected), 6)
        self.assertEqual(sum(r["kind"] == "table_row" for r in selected), 3)
        self.assertNotIn("Background information", rec["description"])
        self.assertIn("You must meet the requirements.", rec["description"])
        originals = {r["key"]: r for r in rows}
        for row in selected:
            self.assertEqual(row["quote"], originals[row["key"]]["quote"])
            self.assertEqual(row["source"], originals[row["key"]]["source"])
            self.assertTrue(set(row["values"].get("required_context_keys", [])) <= set(report["selected_keys"]))
        self.assertEqual(set(report["selected_keys"]) | set(report["dropped_keys"]), set(originals))
        body = inspect_request(rec, selected, cfg)["body"]
        self.assertLess(len(stable_json(body).encode("utf-8")), admission.BASE_BYTES)
        out = self.home / "bundle"
        write_bundle(record, rows, out, cfg)
        self.assertEqual(read_json(out / "claim_selection.json"), report)
        self.assertEqual(read_json(out / "claims.json"), rows)

    def test_large_indivisible_condition_refused_without_clipping_or_admission(self):
        quote = "You must keep every complete condition. " * 300
        record, rows, _ = self.raw_page("<main><h1>Synthetic</h1><h2>Conditions</h2><p>" + quote + "</p></main>")
        out = self.home / "bundle"
        with patch("socialreel.concept_admission.admit") as admit:
            result = write_bundle(record, rows, out, config(), prepare_request=True)
        admit.assert_not_called()
        self.assertTrue(result["request_refused"])
        self.assertIn(quote.strip(), read_json(out / "claims.json")[1]["quote"])
        self.assertEqual(read_json(out / "concept_claims.json"), [])

    def test_wire_budget_applies_before_claim_count_limit(self):
        record, rows, _ = self.raw_page("<main><h1>Synthetic</h1><p>Lead.</p><h2>Where to search</h2><table>" +
            "".join(f"<tr><td>Holder {i}</td><td>" + "Complete search details. " * 25 + "</td></tr>" for i in range(18)) + "</table></main>")
        rec, selected, report = select_for_core(record, rows, config())
        self.assertGreater(len(selected), 2)
        self.assertLess(len(selected), report["max_claims"])
        self.assertTrue(report["dropped_keys"])
        body = inspect_request(rec, selected, config())["body"]
        self.assertLess(len(stable_json(body).encode()), admission.BASE_BYTES)

    def test_catalog_and_new_pages_keep_explicit_topics_and_conditions(self):
        self.assertEqual(set(usagov.PAGES), {"energy", "unclaimed", "wage_laws", "unclaimed_tax_refunds", "workers_comp"})
        self.assertEqual(read_json(FIX.parent / "public_sources_config.json")["usagov"]["pages"], list(usagov.PAGES))
        for page, fixture, intent in (("wage_laws", "wages", "wages"), ("unclaimed_tax_refunds", "unclaimed_tax_refunds", "unclaimed"),
                                       ("workers_comp", "workers_comp", None)):
            record, rows, _ = self.acquire(fixture, page=page)
            self.assertEqual(record["topic_id"], "usagov:" + page)
            self.assertEqual(record.get("public_reference_topic"), intent)
            rec, selected, report = select_for_core(record, rows, config())
            self.assertEqual(report["state"], "selected")
            self.assertTrue(selected)
            inspect_request(rec, selected, config())
            if page == "wage_laws":
                self.assertIn("does not cover wages the agency has not recovered", rec["description"])
                self.assertIn("You must prove your identity", rec["description"])

    def test_dead_wages_rejected_before_transport_or_snapshot(self):
        with patch.object(usagov.USAGovClient, "read") as read:
            client = usagov.USAGovClient(self.home / "source")
            for name in ("wages", "https://www.usa.gov/unpaid-wages", "https://usa.gov/unpaid-wages", "https://www.usa.gov/unpaid-wages/?old=1"):
                with self.subTest(name=name), self.assertRaisesRegex(PipelineError, "removed.*wage_laws"):
                    client.page(name)
            read.assert_not_called()
        self.assertFalse((self.home / "source").exists())

    def test_invalid_selection_cap_fails_clearly(self):
        record, rows, _ = self.acquire("table")
        for cap in (0, -1, True, "5"):
            cfg = {"usagov_facts": {"max_claims": cap}}
            with self.subTest(cap=cap), self.assertRaisesRegex(PipelineError, "positive integer"):
                select_for_core(record, rows, cfg)

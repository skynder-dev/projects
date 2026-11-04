"""Offline multi-program regressions; real source, socket and model calls forbidden."""
import contextlib
import copy
import io
import json
from unittest.mock import patch

from socialreel import concept_admission as admission, concept_core as core, topics, usagov
from socialreel.__main__ import main
from socialreel.common import PipelineError, read_json, sha256_bytes, stable_json, write_json
from socialreel.source_intake import replay_topic, write_bundle
from socialreel.usagov_facts import _select_units, select_for_core
from socialreel.usagov_programs import program_units
from tests.test_concept_offline import config
from tests.test_concept_source_cards import inspect_request
from tests.test_usagov import FIX, OfflineSourceCase

ENERGY = FIX / "usagov_energy_programs_synthetic.html"
MANIFEST = FIX / "usagov_energy_programs_manifest_synthetic.json"


class USAGovProgramTests(OfflineSourceCase):
    def acquire(self, path=ENERGY, page="energy"):
        record, receipt = usagov.USAGovClient(self.home / "source").page(page, fixture=path)
        return record, usagov.build_claims(record), receipt

    def html(self, raw):
        path = self.home / "synthetic.html"
        path.write_text("<!-- SYNTHETIC OFFLINE -->" + raw, encoding="utf-8")
        return self.acquire(path)

    def test_three_program_groups_own_sections_lists_and_documents(self):
        record, rows, receipt = self.acquire()
        programs = program_units(record, rows)
        self.assertEqual([(p["index"], p["name"]) for p in programs], [(1, "liheap"), (2, "wap"), (3, "disconnected")])
        self.assertEqual([len(p["claim_keys"]) for p in programs], [5, 5, 5])
        keys = [k for p in programs for k in p["claim_keys"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(rows), 17)
        for program in programs:
            self.assertEqual(sum(r["kind"] == "list_item" and r["key"] in program["claim_keys"] for r in rows), 3)
        self.assert_receipt(receipt, ENERGY.read_bytes())

    def test_whole_page_refused_but_default_complete_program_fits(self):
        record, rows, _ = self.acquire()
        before = copy.deepcopy((record, rows))
        self.assertEqual(_select_units(record, rows, config())[2]["state"], "refused")
        rec, selected, report = select_for_core(record, rows, config())
        self.assertEqual(report["whole_page_state"], "refused")
        self.assertEqual(report["state"], "selected")
        self.assertEqual(report["program_selection"], "automatic_first_fitting")
        self.assertEqual(report["chosen_program"]["name"], "liheap")
        self.assertIn("First fitting program", report["program_selection_note"])
        self.assertEqual(rec["topic_id"], "usagov:energy:liheap")
        self.assertEqual(len(selected), 7)
        self.assertEqual({p["name"] for p in report["left_out_programs"]}, {"wap", "disconnected"})
        self.assertTrue(all(p["reason"] == "first_fitting_program_selected" for p in report["left_out_programs"]))
        self.assertEqual(before, (record, rows))
        self.assertEqual((rec, selected, report), select_for_core(record, rows, config()))

    def test_every_program_keeps_own_complete_facts_page_note_sources_and_quotes(self):
        record, rows, receipt = self.acquire()
        originals = {r["key"]: r for r in rows}
        for program in program_units(record, rows):
            with self.subTest(program=program["name"]):
                rec, selected, report = select_for_core(record, rows, config(), program=program["name"])
                self.assertEqual(report["state"], "selected")
                own = set(program["claim_keys"])
                selected_keys = {r["key"] for r in selected}
                self.assertTrue(own <= selected_keys)
                self.assertTrue(set(report["page_wide_condition_keys"]) <= selected_keys)
                self.assertIn("Rules differ by state.", rec["description"])
                self.assertIn("Only that office can decide", rec["description"])
                foreign = {key for p in report["programs"] if p["name"] != program["name"] for key in p["claim_keys"]}
                self.assertTrue(foreign.isdisjoint(selected_keys))
                self.assertTrue(all(r["reason"] == "other_program" for r in report["dropped"] if r["key"] in foreign))
                for row in selected:
                    self.assertEqual(row["quote"], originals[row["key"]]["quote"])
                    self.assertEqual(row["statement"], originals[row["key"]]["statement"])
                    self.assertEqual(row["source"], originals[row["key"]]["source"])
                    self.assertEqual(row["locator"], originals[row["key"]]["locator"])
                    self.assertEqual(row["source"]["snapshot_sha256"], receipt["sha256"])
                    self.assertEqual(row["source"]["excerpt_sha256"], sha256_bytes(row["quote"].encode()))
                    self.assertTrue(set(row["values"].get("required_context_keys", [])) <= selected_keys)
                prompt = inspect_request(rec, selected, config())["body"]
                self.assertLess(len(stable_json(prompt).encode()), admission.BASE_BYTES)
                self.assertIn("Rules differ by state.", prompt["prompt"])
                self.assertEqual({r["claim_key"] for r in json.loads(prompt["prompt"])["factual_core"]}, selected_keys)
                cfg_v2 = config()
                cfg_v2["concept_first"]["result_contract"] = core.RESULT_V2
                rec_v2, rows_v2, report_v2 = select_for_core(record, rows, cfg_v2, program=program["name"])
                self.assertEqual(report_v2["state"], "selected")
                body_v2 = inspect_request(rec_v2, rows_v2, cfg_v2)["body"]
                self.assertLess(len(stable_json(body_v2).encode()), admission.BASE_BYTES)

    def test_explicit_names_case_and_one_based_indices_choose_same_program(self):
        record, rows, _ = self.acquire()
        for name, index in (("liheap", "1"), ("wap", "2"), ("disconnected", "3")):
            by_name = select_for_core(record, rows, config(), program=name)
            for value in (index, name.upper()):
                rec, selected, report = select_for_core(record, rows, config(), program=value)
                self.assertEqual(rec, by_name[0])
                self.assertEqual(selected, by_name[1])
                self.assertEqual(report["chosen_program"]["name"], name)
                self.assertEqual(report["program_selection"], "explicit")

    def test_unknown_program_rejected_with_available_choices(self):
        record, rows, _ = self.acquire()
        for name in ("other", "0", "-1", "4", ""):
            with self.subTest(name=name), self.assertRaisesRegex(PipelineError, "1=liheap, 2=wap, 3=disconnected"):
                select_for_core(record, rows, config(), program=name)

    def test_automatic_skips_oversized_program_without_clipping_or_mixing(self):
        text = ENERGY.read_text(encoding="utf-8")
        huge = "Only complete LIHEAP conditions may be used. " * 500
        record, rows, _ = self.html(text.replace("The synthetic LIHEAP example", huge + "The synthetic LIHEAP example"))
        rec, selected, report = select_for_core(record, rows, config())
        self.assertEqual(report["chosen_program"]["name"], "wap")
        reason = next(p["reason"] for p in report["left_out_programs"] if p["name"] == "liheap")
        self.assertEqual(reason, "complete_program_budget_or_dependency")
        self.assertNotIn(huge, rec["description"])
        self.assertIn(huge, "\n".join(r["quote"] for r in rows))
        refused = select_for_core(record, rows, config(), program="liheap")
        self.assertEqual(refused[2]["state"], "refused")
        self.assertEqual(refused[1], [])  # explicit choice must never substitute WAP

    def test_own_list_conditions_are_mandatory_even_when_count_cap_would_drop_them(self):
        record, rows, _ = self.acquire()
        cfg = config()
        cfg["usagov_facts"] = {"max_claims": 6}
        rec, selected, report = select_for_core(record, rows, cfg, program="liheap")
        self.assertEqual(report["state"], "refused")
        self.assertEqual(selected, [])
        self.assertEqual(rec["description"], "")
        self.assertEqual(set(report["dropped_keys"]), {r["key"] for r in rows})

    def test_expired_program_not_revived_by_shared_state_note(self):
        raw = ENERGY.read_text(encoding="utf-8").replace("The synthetic LIHEAP example", "The LIHEAP application period has ended. The synthetic LIHEAP example")
        record, rows, _ = self.html(raw)
        own = program_units(record, rows)[0]["claim_keys"]
        self.assertTrue(all(r["expired"] for r in rows if r["key"] in own))
        rec, selected, report = select_for_core(record, rows, config())
        # All other active programs do not fit as one complete page.
        self.assertEqual(report["chosen_program"]["name"], "wap")
        explicit = select_for_core(record, rows, config(), program="liheap")
        self.assertEqual(explicit[2]["state"], "refused")
        self.assertEqual(explicit[2]["left_out_programs"][0]["reason"], "no_current_program_facts")
        self.assertTrue(set(own).isdisjoint(report["selected_keys"]))

    def test_named_program_parent_and_generic_subheadings_keep_scope(self):
        record, rows, _ = self.html("<main><h1>Synthetic</h1><p>Lead.</p>"
            "<h2>LIHEAP bill help</h2><p>LIHEAP may help with bills.</p><h3>Eligibility</h3><p>You must meet bill-help requirements.</p>"
            "<ul><li>Only eligible bill applicants may apply.</li></ul>"
            "<h2>WAP weatherization</h2><p>WAP may help with work.</p><h3>Eligibility</h3><p>You must meet work requirements.</p>"
            "<ul><li>Only eligible repair applicants may apply.</li></ul><h2>State note</h2><p>Rules differ by state.</p>"
            "<h2>Before you begin</h2><p>Ask which documentation your locality accepts.</p></main>")
        groups = program_units(record, rows)
        self.assertEqual([len(p["claim_keys"]) for p in groups], [3, 3])
        rec, selected, report = select_for_core(record, rows, config(), program="liheap")
        self.assertEqual(report["state"], "selected")
        self.assertIn("bill-help requirements", rec["description"])
        self.assertNotIn("work requirements", rec["description"])
        self.assertNotIn("eligible repair applicants", rec["description"])
        self.assertIn("Ask which documentation your locality accepts.", rec["description"])

    def test_generic_program_names_and_unique_named_intro_are_source_bound(self):
        record, rows, _ = self.html("<main><h1>Synthetic</h1><p>Lead.</p><h2>Bill assistance</h2><p>LIHEAP may help with bills.</p>"
            "<h3>Apply</h3><p>You must contact the LIHEAP office.</p>"
            "<h2>Find out if you are eligible for Synthetic Example and apply</h2><p>You must ask the example office.</p></main>")
        groups = program_units(record, rows)
        self.assertEqual([p["name"] for p in groups], ["liheap", "synthetic-example"])
        self.assertEqual(len(groups[0]["claim_keys"]), 2)
        self.assertEqual(select_for_core(record, rows, config(), program="synthetic-example")[2]["state"], "selected")

    def test_small_multi_program_page_stays_whole_without_explicit_choice(self):
        record, rows, _ = self.html("<main><h1>Synthetic</h1><p>Lead.</p><h2>LIHEAP</h2><p>You must ask the LIHEAP office.</p>"
            "<h2>WAP</h2><p>You must ask the WAP office.</p><h2>State note</h2><p>Rules differ by state.</p></main>")
        rec, selected, report = select_for_core(record, rows, config())
        self.assertEqual(report["scope"], "page")
        self.assertEqual(report["program_selection"], "whole_page")
        self.assertEqual(rec["topic_id"], "usagov:energy")
        self.assertEqual({r["key"] for r in selected}, {r["key"] for r in rows})
        self.assertEqual(report["left_out_programs"], [])

    def test_unclaimed_and_tax_refund_fixtures_keep_exact_previous_behavior(self):
        for fixture, page in (("usagov_unclaimed_synthetic.html", "unclaimed"),
                              ("usagov_table_synthetic.html", "unclaimed"),
                              ("usagov_unclaimed_tax_refunds_synthetic.html", "unclaimed_tax_refunds")):
            record, rows, _ = self.acquire(FIX / fixture, page=page)
            self.assertEqual(program_units(record, rows), [])
            self.assertEqual(select_for_core(record, rows, config()), _select_units(record, rows, config()))
            with self.assertRaisesRegex(PipelineError, "no separate recognized programs"):
                select_for_core(record, rows, config(), program="1")

    def test_bundle_records_full_ledger_chosen_program_and_left_out_reasons(self):
        record, rows, _ = self.acquire()
        out = self.home / "bundle"
        result = write_bundle(record, rows, out, config(), program="wap")
        self.assertEqual(result["program"]["name"], "wap")
        self.assertEqual(result["program_selection"], "explicit")
        self.assertFalse(result["model_called"])
        self.assertEqual(read_json(out / "record.json"), record)
        self.assertEqual(read_json(out / "claims.json"), rows)
        report = read_json(out / "claim_selection.json")
        self.assertEqual({p["name"] for p in report["left_out_programs"]}, {"liheap", "disconnected"})
        self.assertEqual(read_json(out / "concept_record.json")["selected_program"]["name"], "wap")
        inputs = read_json(out / "concept_inputs.json")
        self.assertEqual({r["claim_key"] for r in inputs["factual_core"]}, set(report["selected_keys"]))
        self.assertFalse((out / "concept_request.json").exists())

    def test_cli_program_name_index_and_automatic_note(self):
        for value, chosen in ((None, "liheap"), ("WAP", "wap"), ("3", "disconnected")):
            stdout = io.StringIO()
            args = ["source", "--source", "usagov", "--page", "energy", "--fixture", str(ENERGY), "--out", str(self.home / str(value))]
            with contextlib.redirect_stdout(stdout):
                status = main(args + (["--program", value] if value is not None else []))
            self.assertEqual(status, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["program"]["name"], chosen)
            self.assertIn("First fitting" if value is None else "Chosen program", result["program_selection_note"])

    def test_cli_rejects_program_for_studentaid_before_reading_source(self):
        with patch("socialreel.source_intake.acquire") as acquire, contextlib.redirect_stderr(io.StringIO()) as stderr:
            status = main(["source", "--source", "studentaid", "--page", "pell", "--program", "1", "--out", str(self.home / "out")])
        self.assertEqual(status, 2)
        acquire.assert_not_called()
        self.assertIn("only for USA.gov", stderr.getvalue())

    def test_refusal_or_invalid_program_cannot_leave_stale_runnable_bundle(self):
        record, rows, _ = self.acquire()
        out = self.home / "bundle"
        write_bundle(record, rows, out, config())
        write_json(out / "concept_request.json", {"stale": True})
        with self.assertRaises(PipelineError):
            write_bundle(record, rows, out, config(), program="invalid")
        for name in ("concept_request.json", "concept_inputs.json", "concept_record.json", "concept_claims.json"):
            self.assertFalse((out / name).exists())
        self.assertEqual(read_json(out / "claim_selection.json")["state"], "refused")

    def test_actual_core_admission_refusal_stays_a_refusal_for_program_bundle(self):
        record, rows, _ = self.acquire()
        with patch("socialreel.concept_admission.admit", side_effect=PipelineError("Synthetic admission refusal")) as admit:
            result = write_bundle(record, rows, self.home / "bundle", config(), program="wap", prepare_request=True)
        admit.assert_called_once()
        self.assertTrue(result["request_refused"])
        self.assertFalse(result["model_called"])
        self.assertFalse((self.home / "bundle" / "concept_request.json").exists())

    def test_program_topics_are_stable_and_fetch_one_page_once(self):
        first = topics.run({}, self.home / "first", sources=["usagov"], fixture=MANIFEST, as_of="2026-11-04")
        second = topics.run({}, self.home / "second", sources=["usagov"], fixture=MANIFEST, as_of="2026-11-04")
        self.assertEqual(first, second)
        self.assertEqual({r["topic_id"] for r in first["topics"]}, {"usagov:energy:liheap", "usagov:energy:wap", "usagov:energy:disconnected"})
        self.assertEqual(first["excluded"], [])
        self.assertEqual(len(first["sources"]), 1)
        for row in first["topics"]:
            self.assertEqual(row["claim_selection"]["chosen_program"]["name"], row["program"])
            self.assertEqual(len(row["claims"]), 17)  # full archive accompanies selected keys

    def test_program_topic_replay_reparses_and_preserves_requested_program(self):
        out = self.home / "topics"
        data = topics.run({}, out, sources=["usagov"], fixture=MANIFEST, as_of="2026-11-04")
        wap = next(r for r in data["topics"] if r["program"] == "wap")
        wap["program"] = "liheap"
        wap["claims"][0]["quote"] = "Invented text"
        wap["claim_selection"]["chosen_program"]["name"] = "liheap"
        write_json(out / "topics.json", data)
        record, rows = replay_topic(out / "topics.json", self.home / "replay", "usagov:energy:wap")
        self.assertEqual(record["requested_program"], "wap")
        self.assertNotIn("Invented text", str(rows))
        report = select_for_core(record, rows, config())[2]
        self.assertEqual(report["program_selection"], "topic")
        self.assertEqual(report["chosen_program"]["name"], "wap")
        with contextlib.redirect_stdout(io.StringIO()):
            status = main(["source", "--topics", str(out / "topics.json"), "--topic-id", "usagov:energy:wap",
                           "--out", str(self.home / "cli-replay")])
        self.assertEqual(status, 0)
        self.assertEqual(read_json(self.home / "cli-replay" / "claim_selection.json")["chosen_program"]["name"], "wap")
        with self.assertRaisesRegex(PipelineError, "differs from the selected program topic"):
            select_for_core(record, rows, config(), program="liheap")
        wap["topic_id"] = "usagov:energy:invented"
        write_json(out / "topics.json", data)
        with self.assertRaisesRegex(PipelineError, "verified snapshot headings"):
            replay_topic(out / "topics.json", self.home / "bad", "usagov:energy:invented")

    def test_program_topics_seen_history_applies_to_individual_program(self):
        write_json(self.home / "seen.json", ["usagov:energy:wap"])
        data = topics.run({"topics": {"seen_file": "seen.json"}}, self.home / "topics", sources=["usagov"],
                          fixture=MANIFEST, config_dir=self.home, as_of="2026-11-04")
        for row in data["topics"]:
            self.assertEqual(row["score"]["components"]["novelty"]["seen"], row["program"] == "wap")

"""Topic discovery through real producers and fake transports; no real sockets."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from socialreel import grants, topics
from socialreel.__main__ import main
from socialreel.common import ROOT, PipelineError, read_json, sha256_bytes, write_json

TODAY = dt.date(2026, 11, 2)
CFG = {"topics": {"seen_file": None}}


def hit(oid="101", **changes):
    return {"id": oid, "title": "Synthetic opportunity <kept whole>", "agency": "Synthetic agency",
            "closeDate": "12/15/2026", "oppStatus": "posted", **changes}


def detail(oid="101", codes=("21",), **changes):
    table = topics.configuration(CFG)["eligibility_codes"]
    synopsis = {"responseDate": "12/15/2026", "awardCeiling": "25000",
                "applicantTypes": [{"id": code, "description": table[code]} for code in codes],
                "applicantEligibilityDesc": "<p>Individuals in State X only. Others must not apply.</p>\n" + "Complete conditions. " * 60,
                "synopsisDesc": "<p>Synthetic support program.</p>\n" + "Full original description. " * 60}
    synopsis.update(changes)
    return {"id": int(oid), "opportunityTitle": "Synthetic official title", "synopsis": synopsis}


def fixture_row(oid="101", **changes):
    facts = {"opportunity_id": oid, "title": "Synthetic title", "agency_name": "Synthetic agency",
             "close_date": "12/15/2026", "applicant_types": ["Individuals"], "award_ceiling": 25000,
             "applicant_eligibility_desc": "<p>Only synthetic State X applicants may apply.</p>\n",
             "description": "<p>Full original synthetic program synopsis.</p>\n"}
    facts.update(changes)
    return {"source_url": grants.PUBLIC_URL.format(id=oid), "normalized_facts": facts}


class Response:
    status = 200

    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.raw


class Transport:
    def __init__(self, hits, details):
        self.hits, self.details = hits, details
        self.requests, self.raw = [], {}

    def __call__(self, request, **kwargs):
        body = json.loads(request.data)
        self.requests.append((request.full_url, body))
        if request.full_url == grants.SEARCH_URL:
            data = {"oppHits": copy.deepcopy(self.hits)}
        elif request.full_url == grants.DETAIL_URL:
            data = copy.deepcopy(self.details[str(body["opportunityId"])])
        else:
            raise AssertionError("Unexpected API endpoint")
        # Deliberate whitespace/CRLF/Unicode to catch any snapshot reserialization.
        raw = ("  " + json.dumps({"errorcode": 0, "data": data}, ensure_ascii=False, indent=1) + "\r\n").encode("utf-8")
        self.raw[(request.full_url, json.dumps(body, sort_keys=True))] = raw
        return Response(raw)


class TopicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        for target in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex", "urllib.request.urlopen"):
            guard = patch(target, side_effect=AssertionError("Real network forbidden in topic tests"))
            guard.start()
            self.addCleanup(guard.stop)
        pause = patch("socialreel.grants.time.sleep")
        pause.start()
        self.addCleanup(pause.stop)

    def offline(self, rows, *, cfg=None, name="out"):
        path = self.home / "fixture.json"
        path.write_bytes(("  " + json.dumps(rows, ensure_ascii=False) + "\r\n").encode("utf-8"))
        return topics.run(cfg or CFG, self.home / name, fixture=path, as_of=TODAY.isoformat())

    def live(self, transport, cfg=None, name="out"):
        with patch("urllib.request.urlopen", side_effect=transport):
            return topics.run(cfg or CFG, self.home / name, as_of=TODAY.isoformat())

    def test_live_run_20261104_research_programs_do_not_reach_the_top(self):
        # Synthetic records with the exact titles from the first live run (04.11.2026).
        table = topics.configuration(CFG)["eligibility_codes"]
        rows = [fixture_row("320753", title="Science of Learning and Augmented Intelligence (SL)",
                            agency_name="U.S. National Science Foundation", applicant_types=[table["99"]]),
                fixture_row("344634", title="Social Psychology", agency_name="U.S. National Science Foundation",
                            applicant_types=[table["99"]]),
                fixture_row("352741", title="NRL Long Range Broad Agency Announcement (BAA) for Basic and Applied Research",
                            agency_name="Naval Research Laboratory", applicant_types=[table["99"]]),
                fixture_row("359671", title="Small Business Innovation Research (SBIR)", agency_name="NIH",
                            applicant_types=[table["23"]]),
                fixture_row("101")]
        result = self.offline(rows)
        kept = [r["opportunity_id"] for r in result["topics"]]
        self.assertNotIn("320753", kept); self.assertNotIn("344634", kept); self.assertNotIn("352741", kept)
        self.assertIn("359671", kept)  # research, but small businesses are listed
        self.assertIn("101", kept)
        codes = {r["opportunity_id"]: r["exclusion"]["code"] for r in result["excluded"]}
        self.assertEqual(codes.get("344634"), "research_program")

    def test_live_run_20261104b_research_mentioning_a_profession_is_not_a_profession_topic(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        rows = [fixture_row("361169", title="Agriculture and Food Research Initiative Competitive Grants Program",
                            applicant_types=[table["06"], table["12"]],
                            description="<p>Supports research and workforce training for future scientists.</p>"),
                fixture_row("362325", title="Updated National Dislocated Worker Grant Program Guidance",
                            applicant_types=[table["00"], table["12"]],
                            description="<p>Helps dislocated workers return to work.</p>")]
        result = self.offline(rows)
        kept = [r["opportunity_id"] for r in result["topics"]]
        self.assertNotIn("361169", kept)
        self.assertIn("362325", kept)

    def test_live_run_20261104_mixed_institution_list_gets_reduced_audience(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        many = [table[c] for c in ("00", "01", "02", "06", "07", "20", "12", "13")]
        result = self.offline([fixture_row("345738", title="National Center for Workplace Training Translation",
                                           applicant_types=many),
                               fixture_row("101", applicant_types=[table["12"]])])
        by = {r["opportunity_id"]: r for r in result["topics"]}
        mixed = by["345738"]["score"]["components"]["audience"]
        self.assertLess(mixed["points"], by["101"]["score"]["components"]["audience"]["points"])
        self.assertIn("mostly institutions", mixed["reason"])

    def test_institution_only_excluded_and_individual_kept(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        for code in ("00", "01", "02", "04", "05", "06", "07", "08", "11", "20"):
            with self.subTest(code=code):
                result = self.offline([fixture_row("100", applicant_types=[table[code]]), fixture_row()])
                self.assertEqual([r["opportunity_id"] for r in result["topics"]], ["101"])
                excluded = result["excluded"][0]
                self.assertEqual(excluded["exclusion"]["code"], "institution_only")
                self.assertTrue(excluded["exclusion"]["reason"])

    def test_small_business_and_nonprofit_rubric_keeps_mixed_institution_record(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        for code in ("12", "13", "23"):
            with self.subTest(code=code):
                result = self.offline([fixture_row(applicant_types=[table["06"], table[code]])])
                self.assertEqual(result["topics"][0]["rubric"], "small_business_nonprofit")
                self.assertFalse(result["excluded"])

    def test_missing_award_lowers_concreteness_and_all_components_have_reasons(self):
        result = self.offline([fixture_row("101"), fixture_row("102", award_ceiling=None)])
        complete, missing = result["topics"]
        self.assertGreater(complete["score"]["components"]["concreteness"]["points"],
                           missing["score"]["components"]["concreteness"]["points"])
        self.assertIn("award_amount", missing["score"]["missing_data"])
        for record in result["topics"]:
            score = record["score"]
            self.assertEqual(set(score["components"]), {"audience", "timing", "concreteness", "novelty", "missing_data"})
            self.assertEqual(score["total"], sum(c["points"] for c in score["components"].values()))
            self.assertTrue(all(c["reason"] for c in score["components"].values()))

    def test_seen_id_below_equal_new_id_and_relative_config_path(self):
        write_json(self.home / "seen.json", ["00101"])
        source = self.home / "fixture.json"
        write_json(source, [fixture_row("101"), fixture_row("102")])
        result = topics.run({"topics": {"seen_file": "seen.json"}}, self.home / "out", fixture=source,
                            config_dir=self.home, as_of=TODAY.isoformat())
        self.assertEqual([r["opportunity_id"] for r in result["topics"]], ["102", "101"])
        self.assertTrue(result["topics"][1]["score"]["components"]["novelty"]["seen"])

    def test_fixture_cli_deterministic_and_byte_exact_provenance(self):
        source = self.home / "original.json"
        raw = (" [" + json.dumps(fixture_row("102"), ensure_ascii=False) + ",\r\n"
               + json.dumps(fixture_row("101"), ensure_ascii=False) + "] \r\n").encode("utf-8")
        source.write_bytes(raw)
        config = self.home / "config.json"
        write_json(config, CFG)
        with patch.object(grants, "GrantsGovClient", side_effect=AssertionError("Fixture must not create a live client")):
            for name in ("first", "second"):
                with contextlib.redirect_stdout(io.StringIO()):
                    status = main(["topics", "--config", str(config), "--out", str(self.home / name),
                                   "--fixture", str(source), "--as-of", TODAY.isoformat()])
                self.assertEqual(status, 0)
        first, second = self.home / "first", self.home / "second"
        self.assertEqual((first / "topics.json").read_bytes(), (second / "topics.json").read_bytes())
        result = read_json(first / "topics.json")
        self.assertEqual([r["opportunity_id"] for r in result["topics"]], ["101", "102"])
        for item in result["topics"]:
            receipt = item["provenance"]["fixture"]
            self.assertEqual((first / receipt["file"]).read_bytes(), raw)
            self.assertEqual(receipt["sha256"], sha256_bytes(raw))
            self.assertEqual(item["synopsis"], fixture_row()["normalized_facts"]["description"])
            self.assertIn("normalized_facts.description", item["field_provenance"]["synopsis"]["field"])

    def test_live_filters_every_rubric_multiple_keywords_and_deduplicates(self):
        transport = Transport([hit()], {"101": detail()})
        result = self.live(transport)
        searches = [body for url, body in transport.requests if url == grants.SEARCH_URL]
        rules = topics.configuration(CFG)
        expected = {(keyword, "|".join(rubric["eligibility_codes"]))
                    for rubric in rules["rubrics"].values() for keyword in rubric["keywords"]}
        self.assertEqual({(s["keyword"], s["eligibilities"]) for s in searches}, expected)
        self.assertEqual(len(result["topics"]), 1)
        self.assertEqual(result["detail_fetch_count"], 1)
        self.assertEqual(len(result["topics"][0]["discovered_via"]), len(expected))
        for receipt in result["sources"]:
            raw = (self.home / "out" / receipt["file"]).read_bytes()
            self.assertEqual(raw, transport.raw[(receipt["url"], json.dumps(receipt["request"], sort_keys=True))])
            self.assertEqual(sha256_bytes(raw), receipt["sha256"])

    def test_live_detail_excludes_university_and_does_not_trust_filter(self):
        transport = Transport([hit("100"), hit()], {"100": detail("100", ("20",)), "101": detail()})
        result = self.live(transport)
        self.assertEqual(result["excluded"][0]["exclusion"]["code"], "institution_only")
        self.assertEqual(result["topics"][0]["opportunity_id"], "101")

    def test_filtered_keyword_filename_collisions_preserve_every_receipt(self):
        transport = Transport([hit()], {"101": detail()})
        cfg = {"topics": {"seen_file": None, "rubrics": {"help_people": {"keywords": ["a b", "a-b"]}}}}
        result = self.live(transport, cfg)
        files = [receipt["file"] for receipt in result["sources"]]
        self.assertEqual(len(files), len(set(files)))
        for receipt in result["sources"]:
            self.assertEqual(sha256_bytes((self.home / "out" / receipt["file"]).read_bytes()), receipt["sha256"])

    def test_identical_queries_shared_across_rubrics_use_one_snapshot(self):
        cfg = {"topics": {"seen_file": None, "rubrics": {
            "help_people": {"keywords": ["same", "same"], "eligibility_codes": ["99"]},
            "small_business_nonprofit": {"keywords": ["same"], "eligibility_codes": ["99"]},
            "profession": {"enabled": False}}}}
        transport = Transport([hit()], {"101": detail(codes=("99",))})
        result = self.live(transport, cfg)
        self.assertEqual(len(result["sources"]), 2)  # one search, one detail
        self.assertEqual(len(result["topics"][0]["discovered_via"]), 2)

    def test_missing_identity_and_nontext_conditions_reduce_score(self):
        result = self.offline([fixture_row("101"), fixture_row("102", title=None, agency_name=None,
                                                                    applicant_eligibility_desc=False, description=17)])
        complete, incomplete = result["topics"]
        self.assertGreater(complete["score"]["total"], incomplete["score"]["total"])
        self.assertTrue({"title", "agency", "eligibility_text", "synopsis"}.issubset(incomplete["score"]["missing_data"]))

    def test_live_details_budget_and_preliminary_timing_ranking(self):
        transport = Transport([hit("100", closeDate="11/03/2026"), hit("101"), hit("102", closeDate="12/01/2027")],
                              {"101": detail()})
        result = self.live(transport, {"topics": {"seen_file": None, "max_detail_fetch": 1}})
        self.assertEqual([body["opportunityId"] for url, body in transport.requests if url == grants.DETAIL_URL], [101])
        self.assertEqual(result["detail_fetch_count"], 1)
        self.assertEqual({r["exclusion"]["code"] for r in result["excluded"]}, {"detail_limit"})

    def test_known_institution_and_closed_hit_do_not_consume_detail_budget(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        transport = Transport([hit("100", applicantTypes=[table["20"]]),
                               hit("99", closeDate="11/01/2026"), hit()], {"101": detail()})
        result = self.live(transport, {"topics": {"seen_file": None, "rubrics": {"profession": {"enabled": False}}}})
        self.assertEqual(result["detail_fetch_count"], 1)
        self.assertEqual({r["exclusion"]["code"] for r in result["excluded"]}, {"institution_only", "closed"})

    def test_fire_department_kept_for_firefighters_and_pure_university_research_excluded(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        result = self.offline([
            fixture_row("100", title="Equipment grants for fire departments", applicant_types=[table["02"]]),
            fixture_row("101", title="University biochemistry research", applicant_types=[table["20"]])])
        self.assertEqual(len(result["topics"]), 1)
        item = result["topics"][0]
        self.assertEqual(item["rubric"], "profession")
        self.assertEqual(item["audience_profession"], "firefighters")
        self.assertEqual(item["eligible_applicant_types"], [table["02"]])
        self.assertIn("no audience size measured", item["score"]["components"]["audience"]["reason"])
        self.assertEqual(result["excluded"][0]["exclusion"]["code"], "institution_only")

    def test_profession_match_uses_exact_words_and_phrases_not_search_hits(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        result = self.offline([
            fixture_row("100", title="Farmersville schooling research", applicant_types=[table["20"]]),
            fixture_row("101", title="Fire recovery for a department", applicant_types=[table["02"]]),
            fixture_row("102", title="Support for a FIRE DEPARTMENT", applicant_types=[table["02"]])])
        self.assertEqual([r["opportunity_id"] for r in result["topics"]], ["102"])
        self.assertEqual(len(result["excluded"]), 2)

    def test_profession_in_synopsis_keeps_institution_hit_after_detail(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        transport = Transport([hit(applicantTypes=[table["20"]])],
                              {"101": detail(codes=("20",), synopsisDesc="Training nurses in rural clinics.")})
        result = self.live(transport)
        item = result["topics"][0]
        self.assertEqual(result["detail_fetch_count"], 1)
        self.assertEqual(item["audience_profession"], "medical_staff")
        self.assertTrue(any(e["field"] == "synopsis" for e in item["profession_evidence"][0]["evidence"]))

    def test_profession_in_eligibility_text_preserves_exact_html(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        text = "<p>Only rural <b>clinics</b> can apply. Full conditions remain here.</p>\n"
        result = self.offline([fixture_row(applicant_types=[table["20"]], applicant_eligibility_desc=text)])
        self.assertEqual(result["topics"][0]["audience_profession"], "medical_staff")
        self.assertEqual(result["topics"][0]["eligibility_text"], text)

    def test_forecasted_search_and_annual_marker_keep_unknown_deadline_unknown(self):
        transport = Transport([hit(oppStatus="forecasted", closeDate=None)],
                              {"101": detail(codes=("02",), responseDate=None,
                                             synopsisDesc="Annual grants for fire departments. Next round not announced.")})
        result = self.live(transport)
        self.assertTrue(all(body["oppStatuses"] == "posted|forecasted" for url, body in transport.requests if url == grants.SEARCH_URL))
        item = result["topics"][0]
        self.assertEqual(item["status"], "forecasted")
        self.assertTrue(item["recurring_program"])
        self.assertIsNone(item["close_date"])
        self.assertIsNone(item["score"]["components"]["timing"]["days_left"])
        self.assertIn("next opening date remains unknown", item["recurring_program_reason"])

    def test_recurring_program_requires_annual_or_fiscal_year_source_marker(self):
        for marker in ("Annual program", "Program returns annually", "Fiscal-year program", "FY2027 grants"):
            with self.subTest(marker=marker):
                result = self.offline([fixture_row(title=marker)])
                self.assertTrue(result["topics"][0]["recurring_program"])
                self.assertTrue(result["topics"][0]["recurring_program_evidence"])
        result = self.offline([fixture_row(title="One program in 2027", applicant_eligibility_desc="Annual certification required.")])
        self.assertIsNone(result["topics"][0]["recurring_program"])

    def test_profession_table_handles_all_requested_audiences(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        for title, profession in (("Rural clinics", "medical_staff"), ("Farms", "farmers"),
                                  ("Schools", "teachers"), ("Veterans programs", "veterans"),
                                  ("Workforce training", "workers"), ("Police training", "police")):
            with self.subTest(title=title):
                result = self.offline([fixture_row(title=title, applicant_types=[table["02"]])])
                self.assertEqual(result["topics"][0]["audience_profession"], profession)

    def test_unknown_types_and_others_never_infer_eligibility_from_text(self):
        table = topics.configuration(CFG)["eligibility_codes"]
        result = self.offline([fixture_row("100", applicant_types=None),
                               fixture_row("101", applicant_types=["Universities and individuals maybe"]),
                               fixture_row("102", applicant_types=[table["25"]],
                                           applicant_eligibility_desc="Small businesses may apply.")])
        self.assertFalse(result["topics"])
        self.assertEqual(len(result["excluded"]), 3)
        self.assertTrue(all(r["exclusion"]["code"] == "target_eligibility_unconfirmed" for r in result["excluded"]))

    def test_live_source_text_and_applicant_dicts_are_never_shortened_or_cleaned(self):
        det = detail()
        det["synopsis"]["applicantTypes"] = det["synopsis"]["applicantTypes"] * 45
        result = self.live(Transport([hit()], {"101": det}))
        item = result["topics"][0]
        self.assertEqual(item["eligible_applicant_types"], det["synopsis"]["applicantTypes"])
        self.assertEqual(item["eligibility_text"], det["synopsis"]["applicantEligibilityDesc"])
        self.assertEqual(item["synopsis"], det["synopsis"]["synopsisDesc"])
        self.assertEqual(item["field_provenance"]["title"]["snapshot"]["url"], grants.DETAIL_URL)
        self.assertEqual(item["field_provenance"]["agency"]["snapshot"]["url"], grants.SEARCH_URL)

    def test_mismatched_detail_id_fails_without_topics_file(self):
        with self.assertRaisesRegex(PipelineError, "IDs differ"):
            self.live(Transport([hit()], {"101": detail("202")}))
        self.assertFalse((self.home / "out" / "topics.json").exists())

    def test_timing_windows_missing_dates_and_expired(self):
        result = self.offline([fixture_row("100", close_date="11/03/2026"), fixture_row("101"),
                               fixture_row("102", close_date="12/01/2027"), fixture_row("103", close_date="unknown"),
                               fixture_row("104", close_date="11/01/2026")])
        by_id = {row["opportunity_id"]: row for row in result["topics"]}
        timing = lambda oid: by_id[oid]["score"]["components"]["timing"]["points"]
        self.assertGreater(timing("101"), timing("100"))
        self.assertGreater(timing("101"), timing("102"))
        self.assertEqual(timing("103"), 0)
        self.assertIsNone(by_id["103"]["score"]["components"]["timing"]["days_left"])
        self.assertEqual(by_id["103"]["close_date"], "unknown")
        self.assertEqual(result["excluded"][0]["exclusion"]["code"], "closed")

    def test_zero_nonfinite_and_unusable_awards_not_invented(self):
        for value in (None, "", 0, "0", "NaN", "inf", -1, True):
            with self.subTest(value=value):
                result = self.offline([fixture_row(award_ceiling=value)])
                self.assertIn("award_amount", result["topics"][0]["score"]["missing_data"])
                self.assertEqual(result["topics"][0]["award_ceiling"], value)

    def test_legacy_search_body_and_snapshot_name_unchanged(self):
        transport = Transport([], {})
        with patch("urllib.request.urlopen", side_effect=transport):
            client = grants.GrantsGovClient(self.home / "source", pause_s=0)
            _, receipt = client.search("community", 25, "posted")
        self.assertEqual(transport.requests[0][1], {"rows": 25, "oppStatuses": "posted", "startRecordNum": 0, "keyword": "community"})
        self.assertEqual(receipt["file"], "source/search_community.json")

    def test_top_topic_selection_rejects_empty_excluded_invalid_or_wrong_schema(self):
        path = self.home / "topics.json"
        for data in ({}, {"schema": topics.SCHEMA, "topics": []},
                     {"schema": topics.SCHEMA, "topics": [{"opportunity_id": "101", "exclusion": {"excluded": True}}]},
                     {"schema": topics.SCHEMA, "topics": [{"opportunity_id": "../101", "exclusion": {"excluded": False}}]}):
            with self.subTest(data=data):
                write_json(path, data)
                with self.assertRaises(PipelineError):
                    topics.top_opportunity_id(path)

    def test_trial_topics_uses_top_id_and_skips_keyword_search(self):
        result = self.offline([fixture_row("202"), fixture_row("101")])
        transport = Transport([], {"101": detail()})
        argv = [str(ROOT / "trial" / "concept_trial.py"), str(ROOT), str(self.home / "trial"),
                "--topics", str(self.home / "out" / "topics.json")]
        self.assertEqual(topics.top_opportunity_id(self.home / "out" / "topics.json"), result["topics"][0]["opportunity_id"])
        with patch.object(sys, "argv", argv), patch("urllib.request.urlopen", side_effect=transport), \
                patch("socialreel.claims.build_claims", side_effect=PipelineError("Stop after source for offline trial test")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / "trial" / "concept_trial.py"), run_name="__main__")
        self.assertEqual(transport.requests, [(grants.DETAIL_URL, {"opportunityId": 101})])
        report = read_json(self.home / "trial" / "trial.json")
        self.assertEqual(report["stages"]["source"]["opportunity_id"], "101")

    def test_trial_without_topics_keeps_original_search(self):
        # Far-future synthetic deadline keeps this regression independent of the wall clock.
        transport = Transport([hit(closeDate="12/15/2099")], {"101": detail()})
        argv = [str(ROOT / "trial" / "concept_trial.py"), str(ROOT), str(self.home / "trial")]
        with patch.object(sys, "argv", argv), patch("urllib.request.urlopen", side_effect=transport), \
                patch("socialreel.claims.build_claims", side_effect=PipelineError("Stop after source for offline trial test")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / "trial" / "concept_trial.py"), run_name="__main__")
        self.assertEqual(transport.requests[0], (grants.SEARCH_URL,
                         {"rows": 25, "oppStatuses": "posted", "startRecordNum": 0, "keyword": "community"}))
        self.assertEqual(transport.requests[1], (grants.DETAIL_URL, {"opportunityId": 101}))

    def test_trial_preserves_base_branch_opportunity_flag(self):
        transport = Transport([], {"101": detail()})
        argv = [str(ROOT / "trial" / "concept_trial.py"), str(ROOT), str(self.home / "trial"), "--opportunity", "101"]
        with patch.object(sys, "argv", argv), patch("urllib.request.urlopen", side_effect=transport), \
                patch("socialreel.claims.build_claims", side_effect=PipelineError("Stop after source")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / "trial" / "concept_trial.py"), run_name="__main__")
        self.assertEqual(transport.requests, [(grants.DETAIL_URL, {"opportunityId": 101})])

    def test_trial_preserves_base_branch_keyword_and_skip_flags(self):
        skip = self.home / "skip.txt"
        skip.write_text("100\n", encoding="utf-8")
        transport = Transport([hit("100", closeDate="12/15/2099"), hit(closeDate="12/15/2099")], {"101": detail()})
        argv = [str(ROOT / "trial" / "concept_trial.py"), str(ROOT), str(self.home / "trial"),
                "--keyword", "teacher", "--skip", str(skip)]
        with patch.object(sys, "argv", argv), patch("urllib.request.urlopen", side_effect=transport), \
                patch("socialreel.claims.build_claims", side_effect=PipelineError("Stop after source")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT / "trial" / "concept_trial.py"), run_name="__main__")
        self.assertEqual(transport.requests[0][1]["keyword"], "teacher")
        self.assertEqual(transport.requests[1], (grants.DETAIL_URL, {"opportunityId": 101}))

    def test_invalid_cli_date_and_config_return_clear_failure(self):
        config = self.home / "config.json"
        write_json(config, CFG)
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            status = main(["topics", "--config", str(config), "--out", str(self.home / "out"), "--as-of", "invalid"])
        self.assertEqual(status, 2)
        self.assertIn("TOPICS FAILED", errors.getvalue())
        for change in ({"max_detail_fetch": 0}, {"timing": {"min_days": 200, "max_days": 10}}):
            with self.subTest(change=change), self.assertRaises(PipelineError):
                topics.configuration({"topics": change})

    def test_real_network_guard_is_active(self):
        with self.assertRaisesRegex(AssertionError, "Real network forbidden"):
            socket.create_connection(("example.invalid", 443))


if __name__ == "__main__":
    unittest.main()

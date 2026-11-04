"""Synthetic student aid HTML/JSON; key handling and unchanged-core regressions."""
import contextlib
import copy
import io
import json
import os
import urllib.error
from unittest.mock import patch
import unittest

from socialreel import concept_core as core, studentaid, topics
from socialreel.__main__ import main
from socialreel.common import PipelineError, read_json, write_json
from socialreel.source_intake import replay_topic
from tests.test_concept_offline import config
from tests.test_concept_source_cards import inspect_request
from tests.test_usagov import FIX, OfflineSourceCase, Response


class StudentAidTests(OfflineSourceCase):
    def html(self):
        return studentaid.StudentAidClient(self.home / "source").page("pell", fixture=FIX / "studentaid_pell_synthetic.html")

    def school(self):
        return studentaid.CollegeScorecardClient(self.home / "source").school("999001", fixture=FIX / "scorecard_synthetic.json")

    def test_html_bytes_deadlines_and_conditions_survive_claims_and_actual_core(self):
        record, receipt = self.html()
        self.assert_receipt(receipt, (FIX / "studentaid_pell_synthetic.html").read_bytes())
        rows = studentaid.build_claims(record)
        text = "\n".join(row["statement"] for row in rows)
        for phrase in ("may receive aid only if", "must submit the FAFSA", "June 30, 2027", "earlier deadlines", "exceptions may apply"):
            self.assertIn(phrase, text)
        self.assertTrue(record["deadlines"])
        self.assertIsNone(record["close_date"])
        prompt = json.loads(inspect_request(record, rows, config())["body"]["prompt"])
        self.assertIn("earlier deadlines", prompt["source_context"]["condition_fields"][0]["text"])
        self.assertNotIn("Grants.gov lists", text)
        self.assertTrue(rows[0]["statement"].startswith("Federal Student Aid page:"))

    def test_scorecard_fixture_needs_no_key_and_keeps_json_locators(self):
        with patch.dict(os.environ, {}, clear=True):
            record, receipt = self.school()
        self.assert_receipt(receipt, (FIX / "scorecard_synthetic.json").read_bytes())
        rows = studentaid.build_claims(record)
        self.assertEqual(record["aid"]["latest.aid.pell_grant_rate"], 0.42)
        self.assertEqual(record["aid"]["latest.aid.federal_loan_rate"], 0)
        self.assertIsNone(record["conditions"])
        self.assertIsNone(record["deadlines"])
        self.assertIsNone(record["who_it_is_for"])
        self.assertTrue(record["unknowns"])
        for row in rows:
            self.assertTrue(row["source"]["locator"]["json_pointer"].startswith("/results/0/"))
            self.assertEqual(row["source"]["snapshot_sha256"], receipt["sha256"])
        self.assertIn("not an individual aid offer", "\n".join(row["statement"] for row in rows))
        before = copy.deepcopy((record, rows))
        captured = inspect_request(record, rows, config())
        self.assertIn("College Scorecard", captured["body"]["prompt"])
        self.assertEqual(before, (record, rows))

    def test_missing_key_clear_error_before_request_or_snapshot(self):
        called = []
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(PipelineError, "COLLEGE_SCORECARD_API_KEY.*no request made"):
            studentaid.CollegeScorecardClient(self.home / "source", transport=lambda *a, **k: called.append(a)).school("999001")
        self.assertFalse(called)
        self.assertFalse((self.home / "source").exists())

    def test_key_header_only_never_in_files_urls_claims_or_logs(self):
        key = "SYNTHETIC_PRIVATE_CREDENTIAL_NEVER_SAVE"
        raw = (FIX / "scorecard_synthetic.json").read_bytes() + b"\r\n "
        calls = []
        def transport(request, **kwargs):
            calls.append(request)
            self.assertEqual(request.get_header("X-api-key"), key)
            self.assertNotIn(key, request.full_url)
            return Response(raw, request.full_url)
        with patch.dict(os.environ, {studentaid.KEY_ENV: key}), contextlib.redirect_stdout(io.StringIO()) as logs:
            record, receipt = studentaid.CollegeScorecardClient(self.home / "source", transport=transport).school("999001")
            rows = studentaid.build_claims(record)
        self.assert_receipt(receipt, raw)
        self.assertEqual(len(calls), 1)
        self.assertNotIn(key, json.dumps([record, receipt, rows]) + logs.getvalue())
        for path in self.home.rglob("*"):
            if path.is_file():
                self.assertNotIn(key.encode(), path.read_bytes())

    def test_http_error_cannot_leak_key_through_exception_or_cli(self):
        key = "SYNTHETIC_PRIVATE_CREDENTIAL_NEVER_SAVE"
        def transport(*args, **kwargs):
            raise urllib.error.HTTPError("https://api.data.gov/?api_key=" + key, 403, key, {}, None)
        with patch.dict(os.environ, {studentaid.KEY_ENV: key}), self.assertRaises(PipelineError) as caught:
            studentaid.CollegeScorecardClient(self.home / "source", transport=transport).school("999001")
        self.assertNotIn(key, str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertFalse((self.home / "source").exists())

    def test_response_echoing_key_not_written(self):
        key = "SYNTHETIC_PRIVATE_CREDENTIAL_NEVER_SAVE"
        def transport(request, **kwargs):
            return Response(json.dumps({"error": key}).encode(), request.full_url)
        with patch.dict(os.environ, {studentaid.KEY_ENV: key}), self.assertRaisesRegex(PipelineError, "credential.*not saved"):
            studentaid.CollegeScorecardClient(self.home / "source", transport=transport).school("999001")
        self.assertFalse((self.home / "source").exists())

    def test_scorecard_wrong_school_empty_result_invalid_rates_and_missing_title_fail(self):
        original = read_json(FIX / "scorecard_synthetic.json")
        variants = []
        for value in (True, -0.1, 1.1, "0.4"):
            data = copy.deepcopy(original)
            data["results"][0]["latest.aid.pell_grant_rate"] = value
            variants.append(data)
        data = copy.deepcopy(original); data["results"][0]["id"] = 999002; variants.append(data)
        data = copy.deepcopy(original); data["results"][0]["school.name"] = None; variants.append(data)
        variants.append({"results": []})
        for data in variants:
            path = self.home / "invalid.json"
            write_json(path, data)
            with self.subTest(data=data), self.assertRaises(PipelineError):
                studentaid.CollegeScorecardClient(self.home / "source").school("999001", fixture=path)

    def test_nested_scorecard_response_supported_with_exact_pointer(self):
        path = self.home / "nested.json"
        write_json(path, {"results": [{"id": 999001, "school": {"name": "Synthetic nested school"},
                                      "latest": {"aid": {"pell_grant_rate": 0.25}}}]})
        record, _ = studentaid.CollegeScorecardClient(self.home / "source").school("999001", fixture=path)
        self.assertEqual(record["facts"]["latest.aid.pell_grant_rate"]["locator"]["json_pointer"], "/results/0/latest/aid/pell_grant_rate")
        self.assertNotIn("latest.aid.federal_loan_rate", record["aid"])

    def test_multisource_cli_and_offline_replay_scorecard(self):
        out = self.home / "topics"
        with contextlib.redirect_stdout(io.StringIO()):
            status = main(["topics", "--out", str(out), "--sources", "usagov,studentaid,scorecard",
                           "--fixture", str(FIX / "public_sources_synthetic.json"), "--as-of", "2026-11-04"])
        self.assertEqual(status, 0)
        result = read_json(out / "topics.json")
        self.assertEqual(len(result["topics"]), 5)
        item = next(row for row in result["topics"] if row["source_type"] == "scorecard")
        self.assertEqual(item["rubric"], "education")
        self.assertIsNone(item["opportunity_id"])
        with patch.dict(os.environ, {}, clear=True):
            record, rows = replay_topic(out / "topics.json", self.home / "replay", "scorecard:999001")
        self.assertEqual(record["source_type"], "scorecard")
        core.inputs(record, rows, config())
        with self.assertRaisesRegex(PipelineError, "Unsupported topics.json schema"):
            topics.top_opportunity_id(out / "topics.json")

    def test_source_cli_missing_key_returns_failure_without_key_or_request(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as errors:
            status = main(["source", "--source", "scorecard", "--college-id", "999001", "--out", str(self.home / "out")])
        self.assertEqual(status, 2)
        self.assertIn(studentaid.KEY_ENV, errors.getvalue())


if __name__ == "__main__":
    unittest.main()

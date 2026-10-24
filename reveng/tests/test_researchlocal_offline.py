"""Portable contracts for existing ResearchLocal source, never live evidence.

Run with Python 3.10+:
  python -I -B reveng/tests/test_researchlocal_offline.py --source reveng/ResearchLocal

All records below are explicitly synthetic unit inputs. No source capture, model,
GUI, binary loading, or product/market-quality qualification is performed.
"""
from pathlib import Path
import argparse
import asyncio
import contextlib
import copy
import hashlib
import io
import json
import selectors
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--include-existing-tests", action="store_true",
                    help="Also run the two existing ResearchLocal unit-test files; fail if either is absent")
args = parser.parse_args()
SOURCE = args.source.resolve()
if not SOURCE.is_dir():
    parser.error("--source must name an existing ResearchLocal source directory")
sys.path.insert(0, str(SOURCE))


def offline_boundary(event, arguments):
    if event in {"socket.connect", "socket.connect_ex", "socket.bind",
                 "socket.getaddrinfo", "urllib.Request", "subprocess.Popen",
                 "os.system", "os.startfile", "os.exec", "os.posix_spawn"}:
        raise PermissionError("Offline contract tests forbid: " + event)
    if event == "import" and str(arguments[0]).split(".")[0] in {
        "torch", "transformers", "onnxruntime", "faster_whisper"
    }:
        raise PermissionError("Offline contract tests forbid model imports")


sys.addaudithook(offline_boundary)


class _BoundedOfflineSelector(selectors.DefaultSelector):
    """Poll thread completions without a network-backed self-pipe.

    Windows implements socket.socketpair using a loopback listener. These tests
    must not exempt loopback transport from the audit boundary merely to create
    an event loop. With no self-pipe, bounded selector waits keep real
    call_soon_threadsafe/to_thread completions responsive. Windows select also
    rejects an empty descriptor set, so an empty selector uses an ordinary sleep.
    """
    def select(self, timeout=None):
        timeout = 0.01 if timeout is None else max(0, min(timeout, 0.01))
        if not self.get_map():
            if timeout:
                time.sleep(timeout)
            return []
        return super().select(timeout)


class _OfflineEventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        super().__init__(selector=_BoundedOfflineSelector())

    def _make_self_pipe(self):
        self._ssock = self._csock = None

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        # Cross-thread callbacks are observed within the bounded selector wait.
        pass


class _OfflineEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return _OfflineEventLoop()


asyncio.set_event_loop_policy(_OfflineEventLoopPolicy())
import collector_capabilities
import commercial_review
import html_document_identity
import offline_entry
import quote_contract
import reveng_local_research
import runtime_diagnostics
import source_context


def source_inventory():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SOURCE.iterdir() if p.suffix in {".py", ".cs"}}


def observation():
    return {
        "evidence_id": "E1", "title": "Synthetic question for contract test",
        "url": "https://example.invalid/offline-unit-test", "source": "synthetic",
        "kind": "public_question_title", "excerpt": "Not a collected body",
    }


def candidate():
    row = {name: "Synthetic unverified hypothesis for a unit test."
           for name in ["title", "buyer", "problem_hypothesis", "solution_hypothesis",
                        "validation_step", "alternatives_and_limits"]}
    row.update(market_category="other", evidence_ids=["E1"],
               risks=["Synthetic risk is unverified."],
               missing_evidence=["No buyer or demand evidence was collected."],
               observations_used=[{
                   "evidence_id": "E1", "source_field": "title",
                   "quote": observation()["title"], "support": "source_quote",
               }])
    return row


class ResearchLocalOfflineContracts(unittest.TestCase):
    def test_event_loop_and_thread_completion_never_construct_socketpair(self):
        async def actual_async_work():
            await asyncio.sleep(0)
            return await asyncio.to_thread(lambda: "synthetic thread completion")

        with patch.object(socket, "socketpair", side_effect=AssertionError("No socketpair bootstrap")) as socketpair:
            self.assertEqual(asyncio.run(actual_async_work()), "synthetic thread completion")
            socketpair.assert_not_called()

    def test_literal_attribution_does_not_prove_hypothesis(self):
        result = quote_contract.verify(candidate()["observations_used"], [observation()], ["E1"])
        self.assertEqual(result["status"], "verified_literals")
        self.assertEqual(result["hypothesis_truth"], "unknown")
        self.assertIs(result["auto_admission"], False)

    def test_invented_quote_is_rejected(self):
        claims = candidate()["observations_used"]
        claims[0]["quote"] = "This sentence was never in the unit input."
        self.assertEqual(quote_contract.verify(claims, [observation()])["status"], "invalid")

    def test_duplicate_source_ids_are_ambiguous(self):
        result = quote_contract.verify(candidate()["observations_used"], [observation(), observation()])
        self.assertEqual(result["status"], "invalid")

    def test_title_only_is_not_upgraded_to_post_body(self):
        result = source_context.source_packet(observation())
        self.assertIsNone(result["observed_text"])
        self.assertEqual(result["content_scope"], "title_only")

    def test_card_validation_keeps_financial_unknowns(self):
        result = reveng_local_research.validate_cards({"hypotheses": [candidate()]}, [observation()])[0]
        for name in ["market_score", "profit", "sales"]:
            self.assertIsNone(result[name])
        self.assertEqual(result["status"], "unvalidated_hypothesis")
        self.assertEqual(result["observed_basis"], [observation()])

    def test_abstention_is_valid(self):
        self.assertEqual(reveng_local_research.validate_cards({"hypotheses": []}, []), [])

    def test_quotation_contract_cannot_be_omitted(self):
        row = candidate()
        del row["observations_used"]
        with self.assertRaises(ValueError):
            reveng_local_research.validate_cards({"hypotheses": [row]}, [observation()])

    def test_failed_source_technical_clock_is_not_revision(self):
        row = dict(candidate(), observed_basis=[], direct_alternatives={
            "classification": "source_unavailable", "error": "No offline cache",
            "observed_at": "2026-01-01T00:00:00Z", "expires": 1,
        })
        changed = copy.deepcopy(row)
        changed["direct_alternatives"].update(observed_at="2026-01-02T00:00:00Z", expires=2)
        self.assertEqual(commercial_review.revision(row), commercial_review.revision(changed))

    def test_nested_unknown_is_not_false(self):
        row = dict(candidate(), observed_basis=[], functional_comparisons=[{
            "plan_evidence_source_profile": {"price_scope": {"trial": {"status": "unknown", "value": None}}}
        }])
        changed = copy.deepcopy(row)
        changed["functional_comparisons"][0]["plan_evidence_source_profile"]["price_scope"]["trial"]["value"] = False
        self.assertNotEqual(commercial_review.revision(row), commercial_review.revision(changed))

    def test_direct_ai_gate_precedes_transport(self):
        with tempfile.TemporaryDirectory(prefix="reveng-unit-") as directory:
            root = Path(directory)
            run = root / "runs" / "disabled"
            run.mkdir(parents=True)
            with patch.object(reveng_local_research, "collect", side_effect=AssertionError("No collection")) as collect, \
                 patch.object(reveng_local_research, "ask_qwen", side_effect=AssertionError("No inference")) as model:
                with self.assertRaisesRegex(ValueError, "Direct AI execution is disabled"):
                    asyncio.run(reveng_local_research.pipeline(root, run))
                collect.assert_not_called()
                model.assert_not_called()
            self.assertFalse((root / "candidates.json").exists())

    def test_cached_result_checks_integrity_without_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="reveng-unit-") as directory:
            root = Path(directory)
            run = root / "runs" / "cache"
            run.mkdir(parents=True)
            record = {"version": reveng_local_research.VERSION, "status": "completed",
                      "cache_expires": time.time() + 60, "observations": [observation()],
                      "hypotheses": reveng_local_research.validate_cards({"hypotheses": [candidate()]}, [observation()])}
            record["cache_payload_sha256"] = reveng_local_research.sha(
                json.dumps(record, sort_keys=True, ensure_ascii=False).encode())
            reveng_local_research.dump(root / "latest-result.json", record)
            with patch.object(reveng_local_research, "collect", side_effect=AssertionError("No collection")), \
                 patch.object(reveng_local_research, "ask_qwen", side_effect=AssertionError("No inference")):
                asyncio.run(reveng_local_research.pipeline(root, run))
                result = json.loads((run / "result.json").read_text())
                self.assertIs(result["result_cache_hit"], True)
                self.assertEqual((result["source_requests"], result["model_requests"]), (0, 0))
                record["hypotheses"][0]["title"] = "Tampered unit fixture"
                reveng_local_research.dump(root / "latest-result.json", record)
                with self.assertRaisesRegex(ValueError, "integrity"):
                    asyncio.run(reveng_local_research.pipeline(root, run))

    def test_missing_html_is_not_missing_api_or_negative_evidence(self):
        unavailable = {name: False for name in ["bs4", "crawl4ai", "lxml"]}
        self.assertEqual(collector_capabilities.missing("api", unavailable), [])
        self.assertIn("bs4", collector_capabilities.missing("html", unavailable))
        self.assertIn("crawl4ai", collector_capabilities.missing("wordpress_listing", unavailable))

    def test_absent_private_quality_evidence_stays_unknown(self):
        with tempfile.TemporaryDirectory(prefix="reveng-unit-") as directory:
            result = runtime_diagnostics.diagnose(Path(directory))
            self.assertEqual(result["semantic_AI_readiness"], "UNKNOWN_QUALITY_EVIDENCE_UNAVAILABLE")
            self.assertIs(result["automatic_AI_enabled"], False)
            self.assertEqual((result["source_requests"], result["model_requests"], result["weights_loaded"]), (0, 0, 0))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_existing_offline_entry_rejects_missing_saved_evidence(self):
        with tempfile.TemporaryDirectory(prefix="reveng-unit-") as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(FileNotFoundError):
                offline_entry.main(["check", "--workspace", directory])
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_html_source_identity_is_required_without_crawler(self):
        url = "https://example.invalid/offline-unit-test"
        good = '<html><title>Controlled unit page</title><link rel="canonical" href="' + url + '"><p>Synthetic content</p></html>'
        self.assertEqual(html_document_identity.validate(url, good), good)
        with self.assertRaises(ValueError):
            html_document_identity.validate(url, good.replace(url, "https://other.invalid/unit"))
        denied = '<html><title>Access Denied</title><link rel="canonical" href="' + url + '"><p>Your request was blocked.</p></html>'
        with self.assertRaisesRegex(ValueError, "access-denied"):
            html_document_identity.validate(url, denied)


if __name__ == "__main__":
    before = source_inventory()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ResearchLocalOfflineContracts)
    if args.include_existing_tests:
        for name in ["test_commercial.py", "test_local_research.py"]:
            if not (SOURCE / name).is_file():
                raise FileNotFoundError("Required existing unit-test file absent: " + name)
        suite.addTests(unittest.defaultTestLoader.discover(str(SOURCE), pattern="test_*.py"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_inventory() != before:
        raise AssertionError("ResearchLocal source bytes changed during offline tests")
    print("Source bytes unchanged. Unit contracts only; no live, GUI, model or semantic-quality qualification.")
    raise SystemExit(not result.wasSuccessful())

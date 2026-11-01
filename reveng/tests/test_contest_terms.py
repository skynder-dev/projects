"""Offline synthetic contracts for contest_terms: quoted terms only, declared deadline, unverified prize/fee, kept out of
the ranking, no HTTP in offline mode, robots and HTML identity respected, sealed cache reused. No network, no models."""
from pathlib import Path
import argparse, asyncio, hashlib, json, os, sys, tempfile, unittest
from unittest.mock import patch
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True, type=Path); args = parser.parse_args()
SOURCE = args.source.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(SOURCE))
def inventory(): return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py', '.cs'}}
BEFORE = inventory()
def audit(event, a):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'urllib.Request'}: raise PermissionError('No network/process in offline tests: ' + event)
sys.addaudithook(audit)
import asyncio, selectors, time
class Selector(selectors.DefaultSelector):   # an event loop without a self-pipe socket (same as the price-cache suite)
    def select(self, timeout=None):
        timeout = .01 if timeout is None else max(0, min(timeout, .01))
        if not self.get_map(): time.sleep(timeout); return []
        return super().select(timeout)
class Loop(asyncio.SelectorEventLoop):
    def __init__(self): super().__init__(selector=Selector())
    def _make_self_pipe(self): self._ssock = self._csock = None
    def _close_self_pipe(self): pass
    def _write_to_self(self): pass
class Policy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self): return Loop()
asyncio.set_event_loop_policy(Policy())
import contest_terms as ct, reveng_local_research as m

URL = ct.CONTESTS['billion_ai_film_2027']['url']
PAGE = ('SYNTHETIC. Submissions close on 20 November 2026. The winner will receive a prize of US$1,000,000. Entry is free of charge. '
        'Each film runs between 5 and 7 minutes. At least 70% of the final film must be generated using Seedance as the primary tool. '
        'Applicants must be at least 18 years old. Format 16:9, 1080p, MOV or MP4. The organizer receives a non-exclusive license.')
def html(text, canonical=URL):
    return ('<html><head><title>SYNTHETIC</title><link rel="canonical" href="' + canonical + '"></head><body><main><p>' + text + '</p></main></body></html>').encode()

class ParseTests(unittest.TestCase):
    def test_terms_are_quoted_and_typed(self):
        r = ct.parse('billion_ai_film_2027', PAGE, '2026-10-31T00:00:00+00:00', 'a' * 64, today='2026-10-31')
        self.assertEqual(r['classification'], 'contest_terms_found')
        self.assertEqual(r['declared_deadline'], '2026-11-20'); self.assertEqual(r['deadline_status'], 'open')
        self.assertEqual(r['prize'], {'amount': 1000000.0, 'currency': 'USD', 'status': 'proposed_unverified'})
        self.assertEqual(r['fee']['amount'], 0.0); self.assertEqual(r['length_minutes'], [5, 7]); self.assertEqual(r['required_tool'], 'Seedance')
        self.assertFalse(r['automatic_admission']); self.assertEqual(r['global_ranking'], 'excluded'); self.assertEqual(r['kind'], 'official_contest_terms')
        for f in r['facts']:
            self.assertIn(' '.join(f['quote'].split()[:3]), PAGE); self.assertLessEqual(len(f['quote'].split()), ct.MAX_QUOTE_WORDS)
    def test_deadline_is_declared_not_observed_and_closes(self):
        r = ct.parse('billion_ai_film_2027', PAGE, '2026-12-01T00:00:00+00:00', 'a' * 64, today='2026-12-01')
        self.assertEqual(r['declared_deadline'], '2026-11-20'); self.assertEqual(r['deadline_status'], 'closed')
    def test_missing_terms_stay_unknown(self):
        r = ct.parse('billion_ai_film_2027', 'SYNTHETIC page about a festival with no stated terms.', 's', 'a' * 64)
        self.assertEqual(r['classification'], 'not_found_in_checked_source'); self.assertIsNone(r['prize']); self.assertIsNone(r['declared_deadline'])
        self.assertEqual(r['deadline_status'], 'unknown'); self.assertIn('deadline', r['unproven'])
    def test_dates_and_money_forms(self):
        self.assertEqual(ct.parse_date('deadline: Nov. 22, 2026'), '2026-11-22'); self.assertEqual(ct.parse_date('2027-02-15'), '2027-02-15')
        self.assertIsNone(ct.parse_date('deadline 31 February 2027')); self.assertIsNone(ct.parse_date('soon'))
        self.assertEqual(ct.parse_money('EUR 10,000')['amount'], 10000.0); self.assertEqual(ct.parse_money('€15')['currency'], 'EUR')
        self.assertEqual(ct.parse_money('RMB 2 million')['amount'], 2000000.0)
    def test_one_work_many_contests(self):
        a = ct.parse('billion_ai_film_2027', PAGE, 's', 'a' * 64, today='2026-10-31')
        b = dict(a, key='other', length_minutes=[5, 15], required_tool=None, facts=[])
        c = dict(a, key='longer', length_minutes=[10, 30], required_tool=None, facts=[])
        pairs = ct.compatible([a, b, c])
        self.assertEqual([p['contests'] for p in pairs], [['billion_ai_film_2027', 'other'], ['other', 'longer']])
        self.assertEqual(pairs[0]['shared_length_minutes'], [5, 7]); self.assertEqual(pairs[0]['check_exclusivity_terms_of'], ['billion_ai_film_2027'])

class CollectTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name).resolve(); self.run = self.root / 'runs' / 'r'; self.run.mkdir(parents=True)
        one = {'billion_ai_film_2027': ct.CONTESTS['billion_ai_film_2027']}   # one organizer page per collect test
        self.only = patch.object(ct, 'CONTESTS', one); self.only.start()
    def tearDown(self): self.only.stop(); self.t.cleanup()
    def fake(self, page):
        def read(url, stats, cap=1048576):
            stats['source_requests'] += 1
            return b'User-agent: *\nAllow: /\n' if url.endswith('/robots.txt') else page
        return read
    def test_offline_never_fetches(self):
        with patch.object(m, 'read_http', side_effect=AssertionError('HTTP in offline mode')):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}, offline=True))
        self.assertEqual(r['records'][0]['classification'], 'source_unavailable'); self.assertIn('no HTTP fallback', r['records'][0]['error'])
        self.assertEqual(r['model_requests'], 0)
    def test_fetch_seal_and_cache(self):
        stats = {'source_requests': 0}
        with patch.object(m, 'read_http', side_effect=self.fake(html(PAGE))):
            r = asyncio.run(ct.collect(self.root, self.run, stats))
        self.assertEqual(r['records'][0]['classification'], 'contest_terms_found'); self.assertEqual(stats['source_requests'], 2)
        saved = json.loads((self.root / 'contest-terms.json').read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256')
        self.assertEqual(claim, m.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False).encode()))
        self.assertEqual(len(list((self.root / 'contest-payloads').iterdir())), 1)
        with patch.object(m, 'read_http', side_effect=AssertionError('cache must be used')):
            r2 = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}, offline=True))
        self.assertEqual(r2['records'][0]['classification'], 'contest_terms_found')
    def test_robots_and_identity_are_respected(self):
        def denied(url, stats, cap=1048576):
            stats['source_requests'] += 1
            return b'User-agent: *\nDisallow: /\n' if url.endswith('/robots.txt') else html(PAGE)
        with patch.object(m, 'read_http', side_effect=denied):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}))
        self.assertIn('robots.txt denied', r['records'][0]['error'])
        with patch.object(m, 'read_http', side_effect=self.fake(html(PAGE, canonical='https://example.org/other'))):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}))
        self.assertEqual(r['records'][0]['classification'], 'source_unavailable'); self.assertIn('canonical', r['records'][0]['error'])

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

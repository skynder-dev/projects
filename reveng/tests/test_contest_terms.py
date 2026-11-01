"""Offline synthetic contracts for contest_terms: quoted terms only, declared deadline, unverified prize/fee, kept out of
the ranking, no HTTP in offline mode, robots and HTML identity respected, sealed cache reused; aggregator leads are a
secondary list read from organizer pages within the lead limit, listing hints never become terms, refused hosts are not
asked again, the window's view file carries the sealed payload, and no bs4 is needed. No network, no models."""
from pathlib import Path
import argparse, asyncio, hashlib, json, os, sys, tempfile, unittest, urllib.error
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
LEAD_PAGE = ('SYNTHETIC organizer page. Deadline: December 1, 2026. The grand prize is EUR 2,500. Entry fee: $10. '
             'Films must be no longer than 10 minutes. Open to filmmakers worldwide.')
AGG = 'https://agg.example/'
LISTING = ('<html><head><title>SYNTHETIC listing</title><meta property="og:url" content="https://agg.example"></head><body>'
           '<nav><a href="https://agg.example/browse">Browse</a></nav><main><h1>Listing</h1><ul>'
           '<li><a href="https://agg.example/contests/one">One Film Contest</a> Deadline Nov 20, 2026 &middot; $5,000 &middot; <a href="https://one.example/rules">Organizer site</a></li>'
           '<li><a href="https://two.example/contest?x=1#top">Two Shorts Festival</a> Deadline Dec 1, 2026</li>'
           '<li><a href="https://three.example/">Three Festival</a> Deadline Oct 1, 2026</li>'
           '<li><a href="' + URL + '">AI Film Award 2027</a> Nov 20, 2026</li>'
           '<li><a href="https://four.example/">Four Festival with a very long name that runs on and on and on and on</a></li>'
           '<li><a href="https://two.example/contest?x=1">Two Shorts again</a> Dec 1, 2026</li>'
           '<li><a href="http://five.example/">insecure</a> <a href="https://www.linkedin.com/in/x">credits</a> <a href="https://x.example/">eXchange</a></li>'
           '</ul></main><footer><a href="https://ruminatex.com">Crafted by</a></footer></body></html>').encode()
def html(text, canonical=URL):
    return ('<html><head><title>SYNTHETIC</title><link rel="canonical" href="' + canonical + '"></head><body><main><p>' + text + '</p></main></body></html>').encode()
def bare(text):
    return ('<html><head><title>SYNTHETIC</title></head><body><main><p>' + text + '</p></main></body></html>').encode()

class ParseTests(unittest.TestCase):
    def test_terms_are_quoted_and_typed(self):
        r = ct.parse('billion_ai_film_2027', PAGE, '2026-10-31T00:00:00+00:00', 'a' * 64, today='2026-10-31')
        self.assertEqual(r['classification'], 'contest_terms_found')
        self.assertEqual(r['declared_deadline'], '2026-11-20'); self.assertEqual(r['deadline_status'], 'open')
        self.assertEqual(r['prize'], {'amount': 1000000.0, 'currency': 'USD', 'status': 'proposed_unverified'})
        self.assertEqual(r['fee']['amount'], 0.0); self.assertEqual(r['length_minutes'], [5, 7]); self.assertEqual(r['required_tool'], 'Seedance')
        self.assertFalse(r['automatic_admission']); self.assertEqual(r['global_ranking'], 'excluded'); self.assertEqual(r['kind'], 'official_contest_terms')
        self.assertEqual(r['origin'], 'manual_seed')
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
    def test_page_text_without_bs4(self):
        source = (SOURCE / 'contest_terms.py').read_text(encoding='utf-8')
        self.assertNotIn('from bs4', source); self.assertNotIn('import bs4', source)
        text, how = ct.body_text(('<html><head><title>T</title><script>var x="hidden";</script></head><body><nav>menu</nav>'
                                  '<main><p>Deadline <b>Nov 20, 2026</b>.</p></main><footer>foot</footer></body></html>').encode(), 'https://x.example/')
        self.assertEqual(text, 'Deadline Nov 20, 2026 .'); self.assertEqual(how, 'exact_url_no_redirect_no_canonical_declared')
        text, how = ct.body_text(html('Hello &amp; welcome'), URL)
        self.assertEqual(text, 'Hello & welcome'); self.assertEqual(how, 'declared_canonical_matches')

class LeadTests(unittest.TestCase):
    def test_listing_links_become_leads_with_listed_hints(self):
        found, how = ct.leads(LISTING, AGG)
        self.assertEqual(how, 'declared_canonical_matches')
        self.assertEqual([l['url'] for l in found], ['https://one.example/rules', 'https://two.example/contest?x=1', 'https://three.example/', URL, 'https://four.example/', 'https://x.example/'])
        one, two, three, seed, four, x = found
        self.assertEqual(one['text'], 'Organizer site'); self.assertEqual(one['listed_deadline'], '2026-11-20'); self.assertEqual(one['listed_prize']['amount'], 5000.0)
        self.assertEqual(one['listed_status'], 'listed_by_aggregator_unverified')
        self.assertEqual(two['listed_deadline'], '2026-12-01'); self.assertEqual(three['listed_deadline'], '2026-10-01')
        self.assertIsNone(four['listed_deadline']); self.assertLessEqual(len(four['text'].split()), ct.MAX_QUOTE_WORDS)
        self.assertEqual(four['text'], 'Four Festival with a very long name that runs on and on and on')
        self.assertEqual(x['organizer_host'], 'x.example')   # an ignored host is matched by domain, not by prefix
    def test_lead_choice_is_bounded_and_ordered(self):
        found, _ = ct.leads(LISTING, AGG)
        with patch.object(ct, 'MAX_LEADS', 3):
            chosen = ct.choose(found, '2026-10-31', {URL})
        self.assertEqual([l['url'] for l in chosen], ['https://one.example/rules', 'https://two.example/contest?x=1', 'https://four.example/'])
        self.assertEqual({l['url']: l['status'] for l in found}, {
            'https://one.example/rules': 'checked_on_organizer_page', 'https://two.example/contest?x=1': 'checked_on_organizer_page',
            'https://four.example/': 'checked_on_organizer_page', URL: 'already_seeded',
            'https://x.example/': 'not_checked_this_run_lead_limit', 'https://three.example/': 'not_checked_this_run_lead_limit_listed_date_passed'})
        self.assertTrue(all(l['record_key'].startswith('lead-') for l in chosen))
        with patch.object(ct, 'MAX_LEADS', 5):
            chosen = ct.choose(ct.leads(LISTING, AGG)[0], '2026-10-31', {URL})
        self.assertEqual(chosen[-1]['url'], 'https://three.example/')   # a passed listing date only lowers the order; the organizer page decides

    def test_listing_dates_without_a_year(self):
        self.assertEqual(ct.listed_date('Wandura Drama Challenge today Oct 31', '2026-11-01'), ('2026-10-31', True))
        self.assertEqual(ct.listed_date('NEXTALE Award 43d Dec 14', '2026-11-01'), ('2026-12-14', True))
        self.assertEqual(ct.listed_date('Chroma 67d Jan 7', '2026-11-01'), ('2027-01-07', True))
        self.assertEqual(ct.listed_date('Deadline Nov 20, 2026', '2026-11-01'), ('2026-11-20', False))
        self.assertEqual(ct.listed_date('no date here', '2026-11-01'), (None, False))
        self.assertEqual(ct.listed_date('Feb 30', '2026-11-01'), (None, False))
    def test_closed_host_leads_do_not_use_the_budget(self):
        listing = LISTING.replace(b'https://two.example/contest?x=1#top', b'https://filmfreeway.com/SomeFest')
        found, _ = ct.leads(listing, AGG)
        chosen = ct.choose(found, '2026-10-31', {URL})
        self.assertNotIn('https://filmfreeway.com/SomeFest', [l['url'] for l in chosen])
        self.assertEqual([l['status'] for l in found if l['url'] == 'https://filmfreeway.com/SomeFest'], ['not_checked_host_closed_to_robots'])
    def test_mismatched_canonical_names_the_declared_address(self):
        with self.assertRaises(ValueError) as e:
            ct.body_text(html(PAGE, canonical='https://example.org/other'), URL)
        self.assertIn('mismatched', str(e.exception)); self.assertIn('https://example.org/other', str(e.exception))

class CollectTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name).resolve(); self.run = self.root / 'runs' / 'r'; self.run.mkdir(parents=True)
        one = {'billion_ai_film_2027': ct.CONTESTS['billion_ai_film_2027']}   # one organizer page per collect test, no listing unless a test adds one
        self.only = patch.object(ct, 'CONTESTS', one); self.only.start(); self.none = patch.object(ct, 'AGGREGATORS', {}); self.none.start()
    def tearDown(self): self.none.stop(); self.only.stop(); self.t.cleanup()
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
    def test_view_file_carries_the_sealed_payload(self):
        with patch.object(m, 'read_http', side_effect=self.fake(html(PAGE))):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}))
        view = json.loads((self.root / 'contest-terms-view.json').read_text(encoding='utf-8'))
        self.assertEqual(view['schema'], ct.VIEW_SCHEMA); self.assertEqual(view['payload_sha256'], m.sha(view['payload_json'].encode('utf-8')))
        self.assertEqual(json.loads(view['payload_json']), json.loads(json.dumps(r, sort_keys=True)))
        saved = json.loads((self.root / 'contest-terms.json').read_text(encoding='utf-8')); saved.pop('integrity_sha256')
        self.assertEqual(json.loads(view['payload_json']), saved)
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
    def test_page_without_canonical_is_identified_by_exact_url_and_denials_refused(self):
        with patch.object(m, 'read_http', side_effect=self.fake(bare(PAGE))):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}))
        self.assertEqual(r['records'][0]['classification'], 'contest_terms_found')
        self.assertEqual(r['records'][0]['source_identity'], 'exact_url_no_redirect_no_canonical_declared')
        for f in (self.root / 'contest-cache').iterdir(): f.unlink()
        wall = b'<html><head><title>Access denied</title></head><body>SYNTHETIC blocked</body></html>'
        with patch.object(m, 'read_http', side_effect=self.fake(wall)):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}))
        self.assertEqual(r['records'][0]['classification'], 'source_unavailable')
    def pages(self, refuse=()):
        def read(url, stats, cap=1048576):
            stats['source_requests'] += 1
            host = url.split('/')[2]
            if host in refuse: raise urllib.error.HTTPError(url, 403, 'Forbidden', None, None)
            if url.endswith('/robots.txt'): return b'User-agent: *\nAllow: /\n'
            if url == AGG: return LISTING
            if url == URL: return html(PAGE)
            return bare(LEAD_PAGE)
        return read
    def test_leads_are_read_from_organizer_pages_within_the_limit(self):
        stats = {'source_requests': 0}
        with patch.object(ct, 'AGGREGATORS', {'agg': {'title': 'SYNTHETIC listing', 'url': AGG, 'seed': 'test', 'role': 'secondary_lead_list'}}), \
             patch.object(ct, 'MAX_LEADS', 2), patch.object(m, 'read_http', side_effect=self.pages()):
            r = asyncio.run(ct.collect(self.root, self.run, stats, today='2026-10-31'))
        self.assertEqual(r['lead_limit_per_run'], 2)
        item = r['listings']['agg']; self.assertEqual(item['classification'], 'listing_read'); self.assertEqual(item['role'], 'secondary_lead_list')
        self.assertEqual([l['status'] for l in item['leads']], ['checked_on_organizer_page', 'checked_on_organizer_page', 'not_checked_this_run_lead_limit_listed_date_passed',
                                                               'already_seeded', 'not_checked_this_run_lead_limit', 'not_checked_this_run_lead_limit'])
        self.assertEqual([x['origin'] for x in r['records']], ['manual_seed', 'aggregator_lead', 'aggregator_lead'])
        lead = r['records'][1]
        self.assertEqual(lead['key'], ct.lead_key('https://one.example/rules')); self.assertEqual(lead['organizer'], 'one.example'); self.assertEqual(lead['title'], 'Organizer site')
        self.assertEqual(lead['classification'], 'contest_terms_found'); self.assertEqual(lead['declared_deadline'], '2026-12-01')
        self.assertEqual(lead['prize'], {'amount': 2500.0, 'currency': 'EUR', 'status': 'proposed_unverified'})   # the organizer page, not the listing's $5,000
        self.assertEqual(lead['lead'], {'aggregator': 'agg', 'listed_deadline': '2026-11-20', 'listed_prize': {'amount': 5000.0, 'currency': 'USD', 'status': 'proposed_unverified'}, 'listed_text': 'Organizer site'})
        self.assertEqual(lead['fee']['amount'], 10.0); self.assertEqual(lead['length_minutes'], [10, 10]); self.assertFalse(lead['automatic_admission'])
        self.assertEqual(lead['seed'], 'lead from ' + AGG + ' (secondary list)')
        # seed: robots + page; listing: robots + page; two leads on two new hosts: robots + page each
        self.assertEqual(stats['source_requests'], 8); self.assertEqual(r['source_requests'], 8); self.assertEqual(r['model_requests'], 0)
        with patch.object(ct, 'AGGREGATORS', {'agg': {'title': 'SYNTHETIC listing', 'url': AGG, 'seed': 'test', 'role': 'secondary_lead_list'}}), \
             patch.object(ct, 'MAX_LEADS', 2), patch.object(m, 'read_http', side_effect=AssertionError('cache must be used')):
            r2 = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}, offline=True, today='2026-10-31'))
        self.assertEqual([x['classification'] for x in r2['records']], ['contest_terms_found'] * 3); self.assertEqual(r2['listings']['agg']['classification'], 'listing_read')
    def test_listing_unavailable_leaves_no_leads_and_seeds_intact(self):
        with patch.object(ct, 'AGGREGATORS', {'agg': {'title': 'SYNTHETIC listing', 'url': AGG, 'seed': 'test', 'role': 'secondary_lead_list'}}), \
             patch.object(m, 'read_http', side_effect=self.pages(refuse={'agg.example'})):
            r = asyncio.run(ct.collect(self.root, self.run, {'source_requests': 0}, today='2026-10-31'))
        self.assertEqual(r['listings']['agg']['classification'], 'source_unavailable'); self.assertIn('403', r['listings']['agg']['error']); self.assertEqual(r['listings']['agg']['leads'], [])
        self.assertEqual([x['origin'] for x in r['records']], ['manual_seed']); self.assertEqual(r['records'][0]['classification'], 'contest_terms_found')
    def test_refused_host_is_not_asked_again_in_the_same_run(self):
        listing = LISTING.replace(b'https://four.example/', b'https://one.example/other')   # two leads on the refusing host
        def read(url, stats, cap=1048576):
            if url == AGG: stats['source_requests'] += 1; return listing
            return self.pages(refuse={'one.example'})(url, stats, cap)
        stats = {'source_requests': 0}
        with patch.object(ct, 'AGGREGATORS', {'agg': {'title': 'SYNTHETIC listing', 'url': AGG, 'seed': 'test', 'role': 'secondary_lead_list'}}), \
             patch.object(ct, 'MAX_LEADS', 8), patch.object(m, 'read_http', side_effect=read):
            r = asyncio.run(ct.collect(self.root, self.run, stats, today='2026-10-31'))
        one = [x for x in r['records'] if x['organizer'] == 'one.example']
        self.assertEqual(len(one), 2); self.assertEqual([x['classification'] for x in one], ['source_unavailable', 'source_unavailable'])
        self.assertIn('403', one[0]['error']); self.assertIn('not asked again', one[1]['error'])
        # seed 2 + listing 2 + one.example robots (refused, 1) + two.example 2 + x.example 2 + three.example 2 = 11; the second one.example lead cost nothing
        self.assertEqual(stats['source_requests'], 11)

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

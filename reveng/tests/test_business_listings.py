"""Offline synthetic contracts for business_listings: rows keep the money and the work, nothing is dropped for needing
capital, ranking by money per hour and by payback, sealed result, phone cards, robots, offline. No network, no models."""
from pathlib import Path
import argparse, hashlib, json, sys, tempfile, unittest
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True, type=Path); args = parser.parse_args()
SOURCE = args.source.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(SOURCE))
def inventory(): return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py', '.cs'}}
BEFORE = inventory()
def audit(event, a):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'urllib.Request'}: raise PermissionError('No network/process: ' + event)
sys.addaudithook(audit)
import business_listings as bl, phone_cards as pc

def L(i, profit, hours, price, title, status='For Sale'):
    return {'id': 'id%d' % i, 'listing_number': 1000 + i, 'public_title': 'SYNTHETIC ' + title, 'listing_status': status, 'average_monthly_net_profit': profit,
            'average_monthly_gross_revenue': profit * 3, 'listing_price': price, 'unpriced': False, 'hours_worked_per_week': hours, 'profit_margin': 33,
            'net_profit_trend_percent': 5, 'net_profit_trend_percent_months': 12, 'first_made_money_at': '2021-05-01',
            'summary': '<p>This business earns from <b>affiliate</b> reviews. More text here.</p>', 'risks': ['Google updates may hit traffic. Details.'], 'work_required': ['Content']}
PAGE = {'data': {'listings': [L(1, 10000, 10, 400000, '$15K Per Month Display Advertising Site in the News Niche'), L(2, 2000, 8, 50000, '$3K Per Month SaaS Business in the Tools Niche'), L(3, 500, 40, 10000, 'Hard shop'),
                              L(4, -100, 5, 1000, 'Losing'), L(5, 30000, 1, None, '$90K Per Month Amazon FBA Business in the Outdoors Niche', 'Sold')], 'count': 5, 'page': 1, 'pages': 1}}
class Tests(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def read(self, denied=False):
        def r(url, stats, cap=1048576):
            stats['source_requests'] += 1
            if url.endswith('/robots.txt'): return b'User-agent: *\nDisallow: /\n' if denied else b'User-agent: *\nAllow: /\n'
            return json.dumps(PAGE).encode()
        return r
    def test_rows_and_rank(self):
        r = bl.collect(self.root, {'source_requests': 0}, read=self.read())
        self.assertEqual(r['status'], 'read'); self.assertEqual(r['read'], 4); self.assertEqual(r['for_sale'], 3); self.assertEqual(r['source_requests'], 2)
        top = {x['title']: x for x in r['top']}
        big, app, fba = (top['SYNTHETIC ' + k] for k in ('$15K Per Month Display Advertising Site in the News Niche', '$3K Per Month SaaS Business in the Tools Niche', '$90K Per Month Amazon FBA Business in the Outdoors Niche'))
        self.assertEqual(big['payback_months'], 40.0)                          # needs $400k: kept, not dropped
        self.assertEqual(app['profit_per_hour'], 57.7); self.assertIsNone(fba['profit_per_hour'])   # '1 h a week' gives no per-hour figure
        self.assertIsNone(fba['price']); self.assertEqual(app['how'], 'This business earns from affiliate reviews.')
        saved = json.loads((self.root / 'business-listings.json').read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256')
        self.assertEqual(claim, pc.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False)))
        ms = {x['model']: x for x in r['models']}
        self.assertEqual(ms['SaaS']['count'], 1); self.assertEqual(ms['Amazon FBA']['example']['monthly_net_profit'], 30000)
        cards = pc.business_cards(self.root)
        self.assertTrue(all(c['id'].startswith('rv_m_') for c in cards)); self.assertFalse(any('Продаётся' in l or 'окупится' in l for c in cards for l in c['lines']))
        saas = [c for c in cards if c['id'] == 'rv_m_SaaS'][0]
        self.assertEqual(saas['text'], 'Программа по подписке'); self.assertTrue(saas['lines'][0].startswith('1 прибыльных бизнесов так зарабатывают, обычно 2 000 USD'))
        self.assertIn('мес после старта', saas['lines'][2])
    def test_robots_and_offline(self):
        self.assertEqual(bl.collect(self.root, {'source_requests': 0}, read=self.read(True))['status'], 'source_unavailable')
        r = bl.collect(self.root, {'source_requests': 0}, offline=True); self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(r['source_requests'], 0)

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

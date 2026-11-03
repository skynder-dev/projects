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
PAGE = {'data': {'listings': [L(1, 10000, 10, 400000, 'Big content site'), L(2, 2000, 2, 50000, 'Small app'), L(3, 500, 40, 10000, 'Hard shop'),
                              L(4, -100, 5, 1000, 'Losing'), L(5, 30000, 20, None, 'Sold brand', 'Sold')], 'count': 5, 'page': 1, 'pages': 1}}
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
        self.assertIn('SYNTHETIC Big content site', top)                       # needs $400k: kept, not dropped
        self.assertEqual(top['SYNTHETIC Small app']['profit_per_hour'], 230.8); self.assertEqual(top['SYNTHETIC Big content site']['payback_months'], 40.0)
        self.assertIsNone(top['SYNTHETIC Sold brand']['price']); self.assertEqual(top['SYNTHETIC Small app']['how'], 'This business earns from affiliate reviews.')
        self.assertEqual(r['top'][0]['title'], 'SYNTHETIC Sold brand')        # best money per hour first (30 000 / 86.7 h)
        saved = json.loads((self.root / 'business-listings.json').read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256')
        self.assertEqual(claim, pc.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False)))
        cards = pc.business_cards(self.root)
        app = [c for c in cards if c['text'] == 'SYNTHETIC Small app'][0]
        self.assertEqual(app['lines'][0], 'Чистыми 2 000 USD в месяц (со слов продавца)'); self.assertIn('окупится за ~25.0 мес', app['lines'][2])
        self.assertTrue(app['id'].startswith('rv_b_')); self.assertIn('Google updates may hit traffic.', app['unknown'])
    def test_robots_and_offline(self):
        self.assertEqual(bl.collect(self.root, {'source_requests': 0}, read=self.read(True))['status'], 'source_unavailable')
        r = bl.collect(self.root, {'source_requests': 0}, offline=True); self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(r['source_requests'], 0)

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

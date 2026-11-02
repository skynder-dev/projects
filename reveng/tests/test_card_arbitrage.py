"""Offline synthetic contracts for card_arbitrage: both directions, assumed fees and shipping, one deal per card name,
deals feed deal_economics and the phone cards, robots respected, offline reads nothing. No network, no models."""
from pathlib import Path
import argparse, hashlib, json, sys, tempfile, unittest
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True, type=Path); args = parser.parse_args()
SOURCE = args.source.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(SOURCE))
def inventory(): return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py', '.cs'}}
BEFORE = inventory()
def audit(event, a):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'urllib.Request'}: raise PermissionError('No network/process: ' + event)
sys.addaudithook(audit)
import card_arbitrage as ca, deal_economics as de, phone_cards as pc

ECB = b"<gesmes:Envelope><Cube><Cube time='2026-10-30'><Cube currency='USD' rate='1.1000'/><Cube currency='JPY' rate='160'/></Cube></Cube></gesmes:Envelope>"
def card(name, setc, usd, eur): return {'id': name + setc, 'name': name, 'set': setc, 'scryfall_uri': 'https://scryfall.com/card/' + setc + '/1?utm=x', 'prices': {'usd': usd, 'eur': eur}}
PAGE = {'data': [card('SYNTHETIC Alpha', 'aaa', '100.00', '50.00'), card('SYNTHETIC Alpha', 'bbb', '90.00', '50.00'), card('SYNTHETIC Beta', 'ccc', '20.00', '60.00'),
                 card('SYNTHETIC Even', 'ddd', '30.00', '27.00'), card('SYNTHETIC NoEur', 'eee', '40.00', None)], 'has_more': False}
class Tests(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def read(self, denied=False):
        def r(url, stats, cap=1048576):
            stats['source_requests'] += 1
            if url.endswith('/robots.txt'): return b'User-agent: *\nDisallow: /\n' if denied else b'User-agent: *\nAllow: /\n'
            return ECB if 'ecb.europa.eu' in url else json.dumps(PAGE).encode()
        return r
    def test_rate(self): self.assertEqual(ca.ecb_rate(ECB), (1.1, '2026-10-30'))
    def test_deals_and_cards(self):
        stats = {'source_requests': 0}; r = ca.collect(self.root, stats, read=self.read())
        self.assertEqual(r['status'], 'read'); self.assertEqual(r['printings_with_both_prices'], 4); self.assertEqual(r['model_requests'], 0)
        names = [(d['name'], d['set'], d['buy'], d['left']) for d in r['deals']]
        # Alpha aaa: buy EU 55.00, sell US 100 -> 100*0.8675-55-6 = 25.75 ; Beta: buy US 20, sell EU 66 -> 66*0.95-20-6 = 36.70 ; Even: no gap
        self.assertEqual(names, [('SYNTHETIC Beta', 'CCC', 'US', 36.7), ('SYNTHETIC Alpha', 'AAA', 'EU', 25.75)])
        files = sorted((self.root / 'deals').glob('mtg-*.json')); self.assertEqual(len(files), 2)
        res = de.compute(json.loads(files[1].read_text(encoding='utf-8')))
        self.assertEqual(res['status'], 'computed_with_assumptions'); self.assertEqual(res['profit_per_unit'], 25.75)
        self.assertEqual(set(res['assumptions_used']), {'quantity', 'shipping_per_unit', 'sales_fees_pct_of_sell'})
        n, where = pc.write(self.root, self.root / 'absent', today='2026-11-02')
        cards = json.loads((self.root / 'phone-cards.json').read_text(encoding='utf-8'))['cards']
        self.assertEqual(cards[0]['lines'][0], 'Купить в США (TCGplayer): ~$20.00'); self.assertEqual(cards[1]['lines_en'][2], '~$25.75 left per card (fees 13.25% and shipping $6 assumed)')
        self.assertEqual(stats['source_requests'], 4)   # two robots files, the rate, one page
        r2 = ca.collect(self.root, {'source_requests': 0}, read=self.read())
        self.assertEqual(len(list((self.root / 'deals').glob('mtg-*.json'))), 2)   # replaced, not piled up
    def test_robots_and_offline(self):
        r = ca.collect(self.root, {'source_requests': 0}, read=self.read(denied=True)); self.assertEqual(r['status'], 'source_unavailable'); self.assertIn('robots', r['error'])
        r = ca.collect(self.root, {'source_requests': 0}, offline=True, read=lambda *a: (_ for _ in ()).throw(AssertionError('HTTP offline')))
        self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(r['source_requests'], 0)

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

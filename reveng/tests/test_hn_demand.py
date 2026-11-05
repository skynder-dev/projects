"""Offline synthetic contracts for hn_demand: only SEEKING FREELANCER answers, no contacts kept, kinds and money read,
sealed output, and the phone card from the sealed summary."""
import argparse, json, sys, tempfile, unittest
from pathlib import Path

a = argparse.ArgumentParser(); a.add_argument('--source', required=True); o, rest = a.parse_known_args()
sys.path.insert(0, str(Path(o.source).resolve())); sys.argv = [sys.argv[0]] + rest
import hn_demand as hd, phone_cards as pc

TREE = {'id': 5, 'children': [
    {'id': 6, 'type': 'comment', 'created_at': '2026-11-01T00:00:00Z', 'text': 'SEEKING FREELANCER | Remote<p>SYNTHETIC: need a video editor for YouTube shorts, $40/hr. Email me a@b.com https://x.y'},
    {'id': 7, 'type': 'comment', 'created_at': '2026-11-01T00:00:00Z', 'text': 'SEEKING WORK | SYNTHETIC designer'},
    {'id': 8, 'type': 'comment', 'created_at': '2026-11-02T00:00:00Z', 'text': 'Seeking freelancer: SYNTHETIC Shopify store setup, budget around $2k'}]}

class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name); hd.time.sleep = lambda s: None
    def tearDown(self): self.t.cleanup()
    def read(self, url, stats, cap=0):
        stats['source_requests'] += 1
        if url.endswith('robots.txt'): raise ValueError('HTTP Error 404: Not Found')
        if 'search_by_date' in url: return json.dumps({'hits': [{'objectID': '5', 'title': 'Ask HN: Freelancer? Seeking freelancer? (November 2026)', 'created_at': '2026-11-01T00:00:00Z'},
                                                                 {'objectID': '9', 'title': 'Ask HN: something else'}]}).encode()
        return json.dumps(TREE).encode()
    def test_collect_and_card(self):
        r = hd.collect(self.root, {'source_requests': 0}, read=self.read)
        self.assertEqual(r['status'], 'read'); self.assertEqual([x['id'] for x in r['requests']], ['hd6', 'hd8'])
        a, b = r['requests']
        self.assertIn('видео и нарезка', a['kinds']); self.assertEqual(a['rate_per_hour_usd'], 40); self.assertNotIn('@', a['text']); self.assertNotIn('http', a['text'])
        self.assertIn('сайты и магазины', b['kinds']); self.assertEqual(b['budget_usd'], 2000)
        self.assertEqual(r['summary']['requests'], 2); self.assertEqual(r['summary']['with_money'], 2); self.assertEqual(r['source_requests'], 3)
        card = pc.demand_card(self.root)[0]
        self.assertEqual(card['id'], 'rv_k_freelance_demand'); self.assertTrue(card['lines'][0].startswith('Суть: ')); self.assertLessEqual(len(card['lines']), 6)
        self.assertIn('Заказов в последних обсуждениях: 2, с указанной оплатой: 2', card['lines'])
    def test_offline(self):
        r = hd.collect(self.root, {'source_requests': 0}, offline=True)
        self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(pc.demand_card(self.root), [])

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    sys.exit(not result.wasSuccessful())

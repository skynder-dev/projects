"""Offline synthetic contracts for hn_income: monthly figures from Ask HN answers, sealed output, bounded reads."""
import argparse, json, sys, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path

a = argparse.ArgumentParser(); a.add_argument('--source', required=True); o, rest = a.parse_known_args()
sys.path.insert(0, str(Path(o.source).resolve())); sys.argv = [sys.argv[0]] + rest
import hn_income as hn, reveng_local_research as m


class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def test_money(self):
        self.assertEqual(hn.monthly_usd('I make about $4k/mo from a Chrome extension'), 4000)
        self.assertEqual(hn.monthly_usd('Revenue is $12,500 per month'), 12500)
        self.assertEqual(hn.monthly_usd('made $120k/year selling templates'), 10000)
        self.assertIsNone(hn.monthly_usd('$500/month'))
        self.assertIsNone(hn.monthly_usd('no money here'))
    def test_collect(self):
        tree = {'id': 7, 'children': [
            {'id': 8, 'type': 'comment', 'text': 'SYNTHETIC: <p>I sell stickers, $3k/mo', 'author': 'a', 'created_at': '2025-01-02T00:00:00Z',
             'children': [{'id': 9, 'type': 'comment', 'text': 'reply $9k/mo', 'children': []}]},
            {'id': 10, 'type': 'comment', 'text': 'SYNTHETIC nothing', 'children': []}]}
        def read(url, stats, cap=0):
            stats['source_requests'] += 1
            if url.endswith('robots.txt'): return b''
            if '/search?' in url: return json.dumps({'hits': [{'objectID': '7', 'title': 'Ask HN: SYNTHETIC', 'num_comments': 100}]}).encode()
            return json.dumps(tree).encode()
        hn.time.sleep = lambda s: None
        r = hn.collect(self.root, {'source_requests': 0}, read=read, now=datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertEqual(r['status'], 'read'); self.assertEqual([p['id'] for p in r['people']], ['hn8'])   # replies are not read
        self.assertEqual(r['people'][0]['monthly_usd'], 3000); self.assertNotIn('<p>', r['people'][0]['text'])
        saved = json.loads((self.root / 'hn-income.json').read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256')
        self.assertEqual(claim, m.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False).encode()))
        self.assertLessEqual(r['source_requests'], 24)
    def test_offline(self):
        r = hn.collect(self.root, {'source_requests': 0}, offline=True)
        self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(r['people'], [])

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    sys.exit(not result.wasSuccessful())

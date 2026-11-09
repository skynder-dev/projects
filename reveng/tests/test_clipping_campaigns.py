"""Offline synthetic contracts for clipping_campaigns: campaigns parsed from the board's embedded escaped JSON, sealed
output, robots honoured, and the phone card built from the sealed summary."""
import argparse, json, sys, tempfile, unittest
from pathlib import Path

a = argparse.ArgumentParser(); a.add_argument('--source', required=True); o, rest = a.parse_known_args()
sys.path.insert(0, str(Path(o.source).resolve())); sys.argv = [sys.argv[0]] + rest
import clipping_campaigns as cc, phone_cards as pc, reveng_local_research as m

def camp(i, brand, total, spent, rate, cat):
    c = {'campaign': {'availableBudgetRaw': total - spent, 'brand': brand, 'budgetSpentRaw': spent, 'budgetTotalRaw': total, 'category': cat,
                      'creatorCountRaw': 3, 'id': 'id%d' % i, 'platforms': ['tiktok', 'youtube'], 'title': 'SYNTHETIC %d' % i, 'payoutSortRaw': rate, 'type': 'cpm'},
         'metrics': {'approvedSubmissionCount': 10, 'budgetSpentCents': 1, 'leaderboard': [{'rank': 2, 'totalViews': 100000, 'username': 'x'}, {'rank': 1, 'totalViews': 500000, 'username': 'y'}], 'totalViews': 1000000}, 'servingId': 's'}
    return json.dumps(c)

PAGE = '<script>self.__next_f.push([1,"' + (('[' + ','.join([camp(1, 'A', 1000, 100, 1.0, 'Gaming'), camp(2, 'A', 3000, 0, 2.0, 'Music'),
                                                             camp(3, 'B', 500, 500, 0.5, 'Gaming'), camp(1, 'A', 1000, 100, 1.0, 'Gaming')]) + ']').replace('"', '\\"')) + '"])</script>'


class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def read(self, robots='User-Agent: *\nAllow: /\nDisallow: /api/\n'):
        def r(url, stats, cap=0):
            stats['source_requests'] += 1
            if url.endswith('robots.txt'): return robots.encode()
            if '/c/campaigns/id2' in url: return b'<a href="https://drive.google.com/drive/folders/x">raw</a> https://www.youtube.com/watch?v=1'
            if '/c/campaigns/' in url: return b'SYNTHETIC no links'
            return PAGE.encode()
        return r
    def test_parse_and_card(self):
        r = cc.collect(self.root, {'source_requests': 0}, read=self.read())
        self.assertEqual(r['status'], 'read'); self.assertEqual(len(r['campaigns']), 3)   # duplicate id dropped
        c1 = [c for c in r['campaigns'] if c['id'] == 'id1'][0]
        self.assertEqual(c1['top_views'], [500000, 100000]); self.assertEqual(c1['approved'], 10); self.assertEqual(c1['total_views'], 1000000)
        self.assertEqual(cc.earnings(c1), {'top_usd': [465, 93], 'per_clip_usd': 93.0, 'views_per_clip': 100000})   # rate $1, 7% fee
        self.assertNotIn('"username"', (self.root / 'clipping-campaigns.json').read_text(encoding='utf-8'))
        for k in ('median_per_clip_usd', 'median_views_per_clip', 'median_top_clipper_usd', 'best_top_clipper_usd'): r['summary'].pop(k)
        self.assertEqual(r['summary'], {'campaigns': 3, 'budget_usd': 4500, 'spent_usd': 600, 'median_per_1k_usd': 1.0, 'top_categories': ['Gaming', 'Music'], 'top_runners': ['A', 'B']})
        self.assertEqual(r['campaigns'][0]['platforms'], ['tiktok', 'youtube']); self.assertEqual(r['source_requests'], 2 + 3)   # board + 3 campaign pages
        c2 = [c for c in r['campaigns'] if c['id'] == 'id2'][0]; self.assertEqual(c2['file_hosts'], ['Google Drive']); self.assertTrue(c2['youtube_or_twitch'])
        c1 = [c for c in r['campaigns'] if c['id'] == 'id1'][0]; self.assertEqual(c1['file_hosts'], []); self.assertFalse(c1['youtube_or_twitch'])
        card = pc.clipping_card(self.root)[0]
        self.assertEqual(card['id'], 'rv_k_clipping_board'); self.assertTrue(card['lines'][0].startswith('Суть: '))
        self.assertEqual(card['lines'][2], 'Сейчас открыто кампаний: 3, общий бюджет 4 500 USD, уже выплачено 600 USD'); self.assertLessEqual(len(card['lines']), 6)
    def test_robots_denied(self):
        r = cc.collect(self.root, {'source_requests': 0}, read=self.read('User-Agent: *\nDisallow: /\n'))
        self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(pc.clipping_card(self.root), [])
    def test_tampered(self):
        cc.collect(self.root, {'source_requests': 0}, read=self.read())
        d = json.loads((self.root / 'clipping-campaigns.json').read_text(encoding='utf-8')); d['summary']['campaigns'] = 99
        (self.root / 'clipping-campaigns.json').write_text(json.dumps(d), encoding='utf-8')
        with self.assertRaises(ValueError): pc.clipping_card(self.root)

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    sys.exit(not result.wasSuccessful())

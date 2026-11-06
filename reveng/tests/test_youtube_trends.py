"""Offline synthetic contracts for youtube_trends: no key -> nothing read; the key never reaches the saved file;
counts by category and country; sealed output; phone card."""
import argparse, json, sys, tempfile, unittest
from pathlib import Path

a = argparse.ArgumentParser(); a.add_argument('--source', required=True); o, rest = a.parse_known_args()
sys.path.insert(0, str(Path(o.source).resolve())); sys.argv = [sys.argv[0]] + rest
import youtube_trends as yt, phone_cards as pc

KEY = 'AIza' + 'S' * 35

class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def read(self, url, stats, cap=0):
        stats['source_requests'] += 1
        cat = '20' if 'regionCode=US' in url else '10'
        return json.dumps({'items': [{'id': 'v%d' % stats['source_requests'], 'snippet': {'title': 'SYNTHETIC', 'channelTitle': 'c', 'categoryId': cat, 'publishedAt': '2026-11-05T00:00:00Z'},
                                      'statistics': {'viewCount': '1000'}, 'contentDetails': {'duration': 'PT45S'}}]}).encode()
    def test_no_key(self):
        r = yt.collect(self.root, {'source_requests': 0}, key=None, read=self.read)
        self.assertEqual(r['status'], 'source_unavailable'); self.assertEqual(r['source_requests'], 0); self.assertEqual(pc.youtube_card(self.root), [])
    def test_read_and_card(self):
        r = yt.collect(self.root, {'source_requests': 0}, key=KEY, read=self.read)
        self.assertEqual(r['status'], 'read'); self.assertEqual(r['summary']['videos'], len(yt.REGIONS)); self.assertEqual(r['source_requests'], len(yt.REGIONS))
        self.assertEqual(r['summary']['top_categories'][0], ['10', len(yt.REGIONS) - 1] if isinstance(r['summary']['top_categories'][0], list) else ('10', len(yt.REGIONS) - 1))
        self.assertEqual(r['summary']['under_a_minute'], len(yt.REGIONS))
        self.assertNotIn(KEY, (self.root / 'youtube-trends.json').read_text(encoding='utf-8'))
        card = pc.youtube_card(self.root)[0]
        self.assertEqual(card['id'], 'rv_k_youtube_trends'); self.assertTrue(card['lines'][0].startswith('Суть: ')); self.assertIn('US - игры', card['lines'][4])
    def test_key_file(self):
        p = self.root / 'k.txt'; p.write_text('﻿' + KEY + '\n', encoding='utf-8'); self.assertEqual(yt.read_key(p), KEY)
        p.write_text('junk', encoding='utf-8'); self.assertIsNone(yt.read_key(p)); self.assertIsNone(yt.read_key(self.root / 'none.txt'))
    def test_error_hides_key(self):
        def bad(url, stats, cap=0):
            stats['source_requests'] += 1; raise ValueError('HTTP Error 403 for ' + url)
        r = yt.collect(self.root, {'source_requests': 0}, key=KEY, read=bad)
        self.assertEqual(r['status'], 'source_unavailable'); self.assertNotIn(KEY, json.dumps(r))

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    sys.exit(not result.wasSuccessful())

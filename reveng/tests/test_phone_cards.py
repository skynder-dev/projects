"""Offline synthetic contracts for phone_cards: cards only from sealed contest results and computed deals, closed or
unreadable contests skipped, unknowns said on the card, ids the phone sync accepts. No network, no models."""
from pathlib import Path
import argparse, hashlib, json, re, sys, tempfile, unittest
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True, type=Path); args = parser.parse_args()
SOURCE = args.source.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(SOURCE))
def inventory(): return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py', '.cs'}}
BEFORE = inventory()
def audit(event, a):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'urllib.Request'}: raise PermissionError('No network/process: ' + event)
sys.addaudithook(audit)
import phone_cards as pc, deal_economics as de

def rec(key, cls, status, deadline):
    return {'key': key, 'title': 'SYNTHETIC ' + key, 'classification': cls, 'deadline_status': status, 'declared_deadline': deadline,
            'prize': {'amount': 1000000.0, 'currency': 'USD'}, 'fee': {'amount': 0.0}, 'length_minutes': [5, 7], 'required_tool': 'Seedance',
            'unproven': ['eligibility'], 'source_url': 'https://example.org/' + key}
class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name); self.phone = self.root / 'phone'; self.phone.mkdir()
        payload = json.dumps({'records': [rec('open', 'contest_terms_found', 'open', '2026-11-20'), rec('shut', 'contest_terms_found', 'closed', '2026-10-01'),
                                          rec('down', 'source_unavailable', 'unknown', None)]}, sort_keys=True)
        (self.root / 'contest-terms-view.json').write_text(json.dumps({'schema': 'contest-terms-view-v1', 'payload_sha256': pc.sha(payload), 'payload_json': payload}), encoding='utf-8')
        (self.root / 'deals').mkdir()
        (self.root / 'deals' / 'sheet.json').write_text(json.dumps({'schema': de.SCHEMA, 'title': 'SYNTHETIC sheet', 'currency': 'USD', 'figures': {
            'buy_price': {'value': 100, 'status': 'owner_stated'}, 'sell_price': {'value': 150, 'status': 'assumption'}, 'quantity': {'value': 10, 'status': 'owner_stated'}}}), encoding='utf-8')
        (self.root / 'deals' / 'half.json').write_text(json.dumps({'schema': de.SCHEMA, 'title': 'SYNTHETIC half', 'figures': {'buy_price': {'value': 1, 'status': 'owner_stated'}}}), encoding='utf-8')
    def tearDown(self): self.t.cleanup()
    def test_cards(self):
        n, where = pc.write(self.root, self.phone, today='2026-11-01')
        cards = json.loads((self.phone / 'reveng-cards.json').read_text(encoding='utf-8'))['cards']
        self.assertEqual(n, 3); self.assertEqual([c['id'] for c in cards], ['rv_c_open', 'rv_d_half', 'rv_d_sheet'])
        for c in cards: self.assertRegex(c['id'], r'^rv_[A-Za-z0-9_.-]{1,76}$'); self.assertEqual(c['kind'], 'reveng'); self.assertEqual(len(c['rev']), 12)
        self.assertEqual(cards[0]['lines'][:2], ['Подать до 20.11.2026 (осталось 19 дн.)', 'Приз: 1 000 000 USD (как на странице)'])
        self.assertIn('кто может', cards[0]['unknown'])
        self.assertEqual(cards[1]['lines'], ['Посчитать нельзя: не хватает sell_price, quantity'])
        self.assertEqual(cards[2]['lines'][0], 'Вложить на партию: 1 000 USD'); self.assertIn('Догадки в расчёте: sell_price', cards[2]['unknown'])
    def test_tampered_view_writes_nothing(self):
        p = self.root / 'contest-terms-view.json'; w = json.loads(p.read_text(encoding='utf-8')); w['payload_sha256'] = '0' * 64; p.write_text(json.dumps(w), encoding='utf-8')
        with self.assertRaises(ValueError): pc.write(self.root, self.phone)
        self.assertFalse((self.phone / 'reveng-cards.json').exists())
    def test_no_phone_folder_keeps_local_copy(self):
        n, where = pc.write(self.root, self.root / 'absent', today='2026-11-01')
        self.assertIn('not found', where); self.assertTrue((self.root / 'phone-cards.json').exists())
    def test_decisions_only_reveng(self):
        (self.phone / 'decisions.json').write_text(json.dumps({'rv_c_open': {'verdict': 'like'}, 'v4_tee': {'verdict': 'nope'}}), encoding='utf-8')
        self.assertEqual(pc.decisions(self.phone), {'rv_c_open': 'like'})

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

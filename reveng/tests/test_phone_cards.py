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
        self.assertEqual(n, 1); self.assertEqual([c['id'] for c in cards], ['rv_c_open'])   # single deals are not a model: no deck cards
        deals = pc.deal_cards(self.root); self.assertEqual([c['id'] for c in deals], ['rv_d_half', 'rv_d_sheet'])
        cards = cards + deals   # below: contest, half deal, full deal
        for c in cards: self.assertRegex(c['id'], r'^rv_[A-Za-z0-9_.-]{1,76}$'); self.assertEqual(c['kind'], 'reveng'); self.assertEqual(len(c['rev']), 12)
        self.assertTrue(cards[0]['lines'][0].startswith('Суть: ')); self.assertTrue(cards[0]['lines_en'][0].startswith('In short: '))
        self.assertEqual(cards[0]['lines'][1:3], ['Подать до 20.11.2026 (осталось 19 дн.)', 'Приз: 1 000 000 USD'])
        self.assertEqual(cards[0]['lines_en'][1:3], ['Deadline Nov 20, 2026 (19 days left)', 'Prize: 1 000 000 USD'])
        self.assertLessEqual(len(cards[0]['lines']), 6)
        self.assertEqual(cards[0]['unknown'], ''); self.assertEqual(cards[0]['prof_en'], 'contest')
        self.assertEqual(cards[1]['lines'], ['Посчитать нельзя: не хватает sell_price, quantity'])
        self.assertEqual(cards[2]['lines'][0], 'Вложить на партию: 1 000 USD'); self.assertIn('Догадки: sell_price', cards[2]['unknown']); self.assertEqual(cards[2]['lines_en'][0], 'Capital for the batch: 1 000 USD')
    def test_tampered_view_writes_nothing(self):
        p = self.root / 'contest-terms-view.json'; w = json.loads(p.read_text(encoding='utf-8')); w['payload_sha256'] = '0' * 64; p.write_text(json.dumps(w), encoding='utf-8')
        with self.assertRaises(ValueError): pc.write(self.root, self.phone)
        self.assertFalse((self.phone / 'reveng-cards.json').exists())
    def test_no_phone_folder_keeps_local_copy(self):
        n, where = pc.write(self.root, self.root / 'absent', today='2026-11-01')
        self.assertIn('not found', where); self.assertTrue((self.root / 'phone-cards.json').exists())
    def test_titles_cleaned_and_empty_contests_skipped(self):
        self.assertEqual(pc.clean_title('2026 AI Holiday Film Competition - Curious Refuge 34d'), '2026 AI Holiday Film Competition - Curious Refuge')
        self.assertEqual(pc.clean_title('Wandura Drama Challenge today Oct 31'), 'Wandura Drama Challenge')
        self.assertEqual(pc.clean_title('IASFF 9d Nov 10'), 'IASFF')
        self.assertEqual(pc.clean_title('AI Film Award 2027'), 'AI Film Award 2027')
        r = rec('bare', 'partial_terms', 'unknown', None); r['prize'] = None
        payload = json.dumps({'records': [r]}, sort_keys=True)
        (self.root / 'contest-terms-view.json').write_text(json.dumps({'schema': 'contest-terms-view-v1', 'payload_sha256': pc.sha(payload), 'payload_json': payload}), encoding='utf-8')
        self.assertEqual(pc.contest_cards(self.root, '2026-11-02'), [])
    def test_budget_limits_deals(self):
        (self.root / 'deals' / 'big.json').write_text(json.dumps({'schema': de.SCHEMA, 'title': 'SYNTHETIC big', 'currency': 'USD', 'figures': {
            'buy_price': {'value': 60000, 'status': 'owner_stated'}, 'sell_price': {'value': 90000, 'status': 'owner_stated'}, 'quantity': {'value': 2, 'status': 'owner_stated'}}}), encoding='utf-8')
        self.assertNotIn('rv_d_big', [c['id'] for c in pc.deal_cards(self.root)])
    def test_assistant_cards_are_marked(self):
        (self.root / 'assistant-analyses.json').write_text(json.dumps({'analyses': [{'id': 'rv_a_x', 'title': 'SYNTHETIC idea', 'lines': ['a', 'b'], 'unknown': 'u', 'sources': ['https://example.org/']},
                                                                                   {'id': 'bad id', 'title': 'no'}]}), encoding='utf-8')
        cards = pc.assistant_cards(self.root)
        self.assertEqual([c['id'] for c in cards], ['rv_a_x']); self.assertEqual(cards[0]['prof'], 'разбор ассистента'); self.assertEqual(cards[0]['url'], 'https://example.org/')
    def test_signal_cards(self):
        data = {'signals': [{'slug': 'alpha', 'name': 'SYNTHETIC Alpha', 'last30_usd': 4801, 'age_months': 3, 'what': 'does a thing', 'url': 'https://trustmrr.com/startup/alpha',
                             'profile': {'pricing': '$19 once', 'channels': 'Reddit', 'team': '1 person'}},
                            {'slug': 'old', 'name': 'Old', 'last30_usd': 9000, 'age_months': 40}, {'slug': 'small', 'name': 'Small', 'last30_usd': 300, 'age_months': 2},
                            {'slug': 'ageless', 'name': 'Ageless', 'last30_usd': 2000, 'age_months': None},
                            {'slug': 'done', 'name': 'Done', 'last30_usd': 5000, 'age_months': 2}]}
        (self.root / 'trustmrr-signals.json').write_text(json.dumps(dict(data, integrity_sha256=pc.sha(json.dumps(data, sort_keys=True, ensure_ascii=False)))), encoding='utf-8')
        data['signals'].append({'slug': 'blank', 'name': 'No plain words', 'last30_usd': 5000, 'age_months': 2})
        (self.root / 'trustmrr-signals.json').write_text(json.dumps(dict(data, integrity_sha256=pc.sha(json.dumps(data, sort_keys=True, ensure_ascii=False)))), encoding='utf-8')
        self.assertEqual(pc.signal_cards(self.root, {'done'}), [])   # no plain sentence yet: nothing shown
        plain = {'summaries': {k: {'ru': 'SYNTHETIC суть ' + k, 'en': 'SYNTHETIC gist ' + k, 'ai': {'verdict': 'keep', 'ru': 'SYNTHETIC держится', 'en': 'SYNTHETIC holds'}} for k in ('alpha', 'old', 'small', 'done', 'ageless')}}
        plain['summaries']['eaten'] = {'ru': 'x', 'en': 'x', 'ai': {'verdict': 'eaten', 'ru': 'x', 'en': 'x'}}
        (self.root / 'signal-summaries.json').write_text(json.dumps(plain), encoding='utf-8')
        cards = pc.signal_cards(self.root, {'done'})
        self.assertEqual([c['id'] for c in cards], ['rv_s_alpha', 'rv_s_ageless'])   # 'blank' has no plain sentence
        self.assertIn('возраст не указан', cards[1]['lines'][1]); cards = cards[:1]
        self.assertEqual(cards[0]['lines'], ['SYNTHETIC суть alpha', 'Заработал 4 801 USD за 30 дней, проекту 3 мес (выручка проверена TrustMRR)', 'Почему ИИ не съест: SYNTHETIC держится', 'Цена: $19 once', 'Откуда клиенты: Reddit', 'Команда: 1 person'])
        self.assertEqual(cards[0]['lines_en'][0], 'SYNTHETIC gist alpha'); self.assertIn('пересказ ассистента', cards[0]['unknown'])
    def test_hn_cards(self):
        data = {'people': [{'id': 'hn1', 'monthly_usd': 4000, 'text': 'SYNTHETIC', 'date': '2023-04-14', 'url': 'https://news.ycombinator.com/item?id=1'},
                           {'id': 'hn2', 'monthly_usd': 9000, 'text': 'SYNTHETIC no summary', 'date': '2023-04-14'}]}
        (self.root / 'hn-income.json').write_text(json.dumps(dict(data, integrity_sha256=pc.sha(json.dumps(data, sort_keys=True, ensure_ascii=False)))), encoding='utf-8')
        (self.root / 'signal-summaries.json').write_text(json.dumps({'summaries': {'hn1': {'title': 'SYNTHETIC t', 'ru': 'SYNTHETIC суть', 'en': 'SYNTHETIC gist', 'ai': {'verdict': 'keep', 'ru': 'SYNTHETIC держится', 'en': 'SYNTHETIC holds'}}, 'hn2': {'ru': 'x', 'en': 'x', 'ai': {'verdict': 'eaten', 'ru': 'x', 'en': 'x'}}}}), encoding='utf-8')
        self.assertEqual(pc.hn_cards(self.root, today='2026-11-05'), [])   # 2023 stories are too old
        cards = pc.hn_cards(self.root, today='2024-01-01')
        self.assertEqual([c['id'] for c in cards], ['rv_h_hn1']); self.assertEqual(cards[0]['text'], 'SYNTHETIC t')
        self.assertEqual(cards[0]['lines'], ['SYNTHETIC суть', 'Говорит, что получает 4 000 USD в месяц (со слов автора, не проверено)', 'Почему ИИ не съест: SYNTHETIC держится', 'Написал 14.04.2023 на Hacker News'])
        data['people'][0]['monthly_usd'] = 1   # tampered
        (self.root / 'hn-income.json').write_text(json.dumps(dict(data, integrity_sha256='x')), encoding='utf-8')
        with self.assertRaises(ValueError): pc.hn_cards(self.root)
    def test_decisions_only_reveng(self):
        (self.phone / 'decisions.json').write_text(json.dumps({'rv_c_open': {'verdict': 'like'}, 'v4_tee': {'verdict': 'nope'}}), encoding='utf-8')
        self.assertEqual(pc.decisions(self.phone), {'rv_c_open': 'like'})

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

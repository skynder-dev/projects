"""Offline synthetic contracts for deal_economics: arithmetic on stated figures only, missing required figures are never
filled in, quoted figures need their quote and source, assumptions are flagged. No network, no models."""
from pathlib import Path
import argparse, hashlib, sys, unittest
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True, type=Path); args = parser.parse_args()
SOURCE = args.source.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(SOURCE))
def inventory(): return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py', '.cs'}}
BEFORE = inventory()
def audit(event, a):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'urllib.Request'}: raise PermissionError('No network/process: ' + event)
sys.addaudithook(audit)
import deal_economics as de

def q(v, quote='SYNTHETIC listed at this price'): return {'value': v, 'status': 'quoted', 'quote': quote, 'url': 'https://example.org/listing'}
def deal(**figures): return {'schema': de.SCHEMA, 'title': 'SYNTHETIC aluminium sheet', 'currency': 'USD', 'figures': figures}

class Tests(unittest.TestCase):
    def test_full_arithmetic(self):
        r = de.compute(deal(buy_price=q(100), sell_price=q(150), quantity={'value': 10, 'status': 'owner_stated'},
                            shipping_per_unit=q(12), insurance_pct_of_buy=q(1), duty_pct_of_buy=q(5), sales_fees_pct_of_sell=q(10),
                            cash_cycle_days={'value': 45, 'status': 'owner_stated'}))
        self.assertEqual(r['status'], 'computed')
        self.assertEqual(r['landed_cost_per_unit'], 118.0)          # 100 + 12 + 1 + 5
        self.assertEqual(r['sales_fees_per_unit'], 15.0)
        self.assertEqual(r['profit_per_unit'], 17.0); self.assertEqual(r['margin_pct_of_sell'], 11.33)
        self.assertEqual(r['capital_needed'], 1180.0); self.assertEqual(r['profit_total'], 170.0)
        self.assertEqual(r['return_on_capital_pct'], 14.41); self.assertEqual(r['break_even_sell_price'], 131.1111)
        self.assertEqual(r['cash_cycle_days'], 45.0)
        self.assertIn('Остаётся с единицы: 17.0 USD', de.describe(r))
    def test_missing_required_is_never_filled(self):
        r = de.compute(deal(buy_price=q(100), quantity={'value': 10, 'status': 'owner_stated'}))
        self.assertEqual(r['status'], 'not_computable'); self.assertEqual(r['missing_required'], ['sell_price'])
        self.assertNotIn('profit_per_unit', r); self.assertIn('Ничего не подставлено', de.describe(r))
    def test_quoted_needs_quote_and_source(self):
        r = de.compute(deal(buy_price={'value': 100, 'status': 'quoted'}, sell_price=q(150), quantity={'value': 1, 'status': 'owner_stated'}))
        self.assertEqual(r['status'], 'not_computable'); self.assertIn('buy_price', r['invalid'][0])
    def test_bad_values_refused(self):
        for bad in (-1, float('nan'), float('inf'), True, '100'):
            r = de.compute(deal(buy_price={'value': bad, 'status': 'owner_stated'}, sell_price=q(150), quantity={'value': 1, 'status': 'owner_stated'}))
            self.assertEqual(r['status'], 'not_computable')
        r = de.compute(deal(buy_price={'value': 1, 'status': 'rumour'}, sell_price=q(150), quantity={'value': 1, 'status': 'owner_stated'}))
        self.assertEqual(r['status'], 'not_computable')
    def test_assumptions_and_unstated_costs_are_shown(self):
        r = de.compute(deal(buy_price=q(100), sell_price={'value': 130, 'status': 'assumption'}, quantity={'value': 2, 'status': 'owner_stated'}))
        self.assertEqual(r['status'], 'computed_with_assumptions'); self.assertEqual(r['assumptions_used'], ['sell_price'])
        text = de.describe(r)
        self.assertIn('догадки, не данные: sell_price', text); self.assertIn('Не указаны и посчитаны как ноль: shipping_per_unit', text)
        self.assertIn('Срок оборота денег: не указан', text)
    def test_loss_is_reported_as_loss(self):
        r = de.compute(deal(buy_price=q(100), sell_price=q(90), quantity={'value': 3, 'status': 'owner_stated'}))
        self.assertEqual(r['profit_per_unit'], -10.0); self.assertEqual(r['profit_total'], -30.0)
    def test_unknown_schema(self):
        with self.assertRaises(ValueError): de.compute({'schema': 'other'})

if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], '-v'], exit=False).result
    if inventory() != BEFORE: raise SystemExit('Source bytes changed during tests')
    raise SystemExit(0 if result.wasSuccessful() else 1)

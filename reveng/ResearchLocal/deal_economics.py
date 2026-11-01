"""Resale deal arithmetic (buy here, ship, sell there), first slice of the money side of RevEng (01.11.2026).

Every input is a separate figure with its own status: 'quoted' (an exact source quote and URL are attached),
'owner_stated' (the owner typed it) or 'assumption' (a labelled guess). A missing required figure is never filled in:
the result then says 'not_computable' and lists what is missing. Quoted figures are still not verified market facts
(a listed price is an offer, not a sale). No network, no model, no ranking; the output is arithmetic on stated inputs.

    python deal_economics.py <deal.json>
"""
import json, sys

SCHEMA = 'reveng-resale-deal-v1'
STATUSES = {'quoted', 'owner_stated', 'assumption'}
# per-unit money in the deal currency unless the name says pct (share of the buy or sell price) or days
REQUIRED = ['buy_price', 'sell_price', 'quantity']
OPTIONAL = {'shipping_per_unit': 0.0, 'insurance_pct_of_buy': 0.0, 'duty_pct_of_buy': 0.0, 'sales_fees_pct_of_sell': 0.0,
            'other_per_unit': 0.0, 'cash_cycle_days': None}


def figure(deal, name):
    """(value, status, problem). A figure is {'value': number, 'status': ..., 'quote'/'url' when quoted}."""
    f = (deal.get('figures') or {}).get(name)
    if f is None:
        return None, 'missing', None
    if not isinstance(f, dict) or f.get('status') not in STATUSES:
        return None, 'invalid', name + ': status must be one of ' + ', '.join(sorted(STATUSES))
    v = f.get('value')
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float('inf'), float('-inf')) or v < 0:
        return None, 'invalid', name + ': value must be a finite number, not negative'
    if f['status'] == 'quoted' and not (str(f.get('quote', '')).strip() and str(f.get('url', '')).startswith('https://')):
        return None, 'invalid', name + ': a quoted figure needs the exact quote and its https:// source'
    return float(v), f['status'], None


def compute(deal):
    if deal.get('schema') != SCHEMA:
        raise ValueError('unknown deal schema: ' + str(deal.get('schema')))
    used, missing, problems, assumed = {}, [], [], []
    for name in REQUIRED + list(OPTIONAL):
        v, status, problem = figure(deal, name)
        if problem:
            problems.append(problem)
        elif status == 'missing':
            if name in REQUIRED:
                missing.append(name)
            else:
                used[name] = {'value': OPTIONAL[name], 'status': 'not_given_counted_as_zero' if OPTIONAL[name] == 0.0 else 'not_given'}
        else:
            used[name] = {'value': v, 'status': status}
            if status == 'assumption':
                assumed.append(name)
    base = {'schema': SCHEMA + '-result', 'title': deal.get('title', ''), 'currency': deal.get('currency'), 'inputs': used,
            'missing_required': missing, 'invalid': problems, 'assumptions_used': assumed,
            'interpretation': 'Arithmetic on the stated figures only; quoted prices are offers, not sales; no demand, buyer or payment is established'}
    if missing or problems:
        return dict(base, status='not_computable')
    g = {k: used[k]['value'] for k in used if used[k]['value'] is not None}
    buy, sell, qty = g['buy_price'], g['sell_price'], g['quantity']
    landed = buy + g['shipping_per_unit'] + buy * (g['insurance_pct_of_buy'] + g['duty_pct_of_buy']) / 100 + g['other_per_unit']
    fees = sell * g['sales_fees_pct_of_sell'] / 100
    unit_profit = sell - fees - landed
    out = dict(base, status='computed_with_assumptions' if assumed else 'computed',
               landed_cost_per_unit=round(landed, 4), sales_fees_per_unit=round(fees, 4), profit_per_unit=round(unit_profit, 4),
               margin_pct_of_sell=round(unit_profit / sell * 100, 2) if sell else None,
               capital_needed=round(landed * qty, 2), profit_total=round(unit_profit * qty, 2),
               return_on_capital_pct=round(unit_profit / landed * 100, 2) if landed else None,
               break_even_sell_price=round(landed / (1 - g['sales_fees_pct_of_sell'] / 100), 4) if g['sales_fees_pct_of_sell'] < 100 else None)
    days = used['cash_cycle_days']['value']
    out['cash_cycle_days'] = days
    out['note_on_time'] = 'capital is tied up for the stated cycle' if days else 'cash cycle not given: time and repeat rate unknown'
    return out


def describe(r):
    """Plain Russian lines for the owner."""
    c = r.get('currency') or ''
    lines = ['РАСЧЁТ СДЕЛКИ (купить, привезти, продать): ' + r.get('title', ''),
             'Только арифметика по введённым цифрам. Цена в объявлении - предложение, не продажа; покупатель и спрос не установлены.']
    if r['status'] == 'not_computable':
        if r['missing_required']:
            lines.append('Посчитать нельзя: не хватает ' + ', '.join(r['missing_required']) + '. Ничего не подставлено.')
        for p in r['invalid']:
            lines.append('Ошибка в цифре: ' + p)
        return '\n'.join(lines)
    lines += ['Себестоимость единицы с доставкой, страховкой и пошлиной: %s %s' % (r['landed_cost_per_unit'], c),
              'Комиссии при продаже за единицу: %s %s' % (r['sales_fees_per_unit'], c),
              'Остаётся с единицы: %s %s (маржа %s%% от цены продажи)' % (r['profit_per_unit'], c, r['margin_pct_of_sell']),
              'Нужно вложить на всю партию: %s %s; прибыль с партии: %s %s; на вложенные деньги: %s%%' % (r['capital_needed'], c, r['profit_total'], c, r['return_on_capital_pct']),
              'Цена продажи, при которой выходим в ноль: %s %s' % (r['break_even_sell_price'], c),
              'Срок оборота денег: ' + ('%s дней' % r['cash_cycle_days'] if r['cash_cycle_days'] else 'не указан')]
    if r['assumptions_used']:
        lines.append('ВНИМАНИЕ: в расчёте догадки, не данные: ' + ', '.join(r['assumptions_used']))
    zero = [k for k, v in r['inputs'].items() if v['status'] == 'not_given_counted_as_zero']
    if zero:
        lines.append('Не указаны и посчитаны как ноль: ' + ', '.join(zero))
    return '\n'.join(lines)


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        result = compute(json.load(f))
    print(describe(result))

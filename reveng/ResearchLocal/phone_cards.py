"""RevEng's cards for the phone (01.11.2026): one short card per opportunity, to swipe on the phone's RevEng screen
(right = dig in, up = later, left = drop). The phone app and its link belong to Forge; RevEng only writes
reveng-cards.json into Forge's phone folder (when it exists on this PC), and reads the decisions back from there.

Cards come only from RevEng's own sealed results: open contests whose organizer page stated terms (contest-terms-view.json,
hash checked) and computed resale deals (deals/*.json through deal_economics). Lines say what the source says; what is
not known is said on the card. No network, no model.

    python phone_cards.py --root <research root> [--phone-dir <folder>]
"""
import argparse, hashlib, json, os, re
from datetime import date
from pathlib import Path

SCHEMA = 'reveng-phone-cards-v1'
# the card front keeps only what decides: a missing deadline or prize is said, the rest of the unknown stays on the PC
KEY_UNKNOWN = {'deadline': ('срок подачи', 'deadline'), 'prize': ('приз', 'prize')}
KIND_RU = {'deadline': 'срок', 'prize': 'приз', 'fee': 'взнос', 'length': 'длина', 'tools': 'инструмент', 'eligibility': 'кто может',
           'exclusivity': 'права', 'format': 'формат'}


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def money(p):
    if not p or p.get('amount') is None:
        return None
    a = p['amount']
    return ('{:,.0f}'.format(a) if a == int(a) else '{:,.2f}'.format(a)).replace(',', ' ') + (' ' + p['currency'] if p.get('currency') else '')


def card_id(prefix, key):
    return ('rv_' + prefix + '_' + re.sub(r'[^A-Za-z0-9_.-]', '_', key))[:79]


def finish(card):
    card['rev'] = sha(json.dumps(card, sort_keys=True, ensure_ascii=False))[:12]
    return card


def contest_cards(root, today):
    path = root / 'contest-terms-view.json'
    if not path.exists():
        return []
    wrap = json.loads(path.read_text(encoding='utf-8'))
    if wrap.get('schema') != 'contest-terms-view-v1' or sha(wrap.get('payload_json', '')) != wrap.get('payload_sha256'):
        raise ValueError('contest view hash or schema mismatch; no cards written from it')
    out = []
    for r in json.loads(wrap['payload_json'])['records']:
        if r.get('classification') not in ('contest_terms_found', 'partial_terms') or r.get('deadline_status') == 'closed':
            continue
        ru, en = [], []
        if r.get('declared_deadline'):
            d = date.fromisoformat(r['declared_deadline']); days = (d - date.fromisoformat(today)).days
            ru.append('Подать до ' + d.strftime('%d.%m.%Y') + ' (осталось ' + str(days) + ' дн.)'); en.append('Deadline ' + d.strftime('%b %d, %Y') + ' (' + str(days) + ' days left)')
        if money(r.get('prize')):
            ru.append('Приз: ' + money(r['prize'])); en.append('Prize: ' + money(r['prize']))
        fee = r.get('fee')
        if fee:
            ru.append('Взнос: бесплатно' if fee.get('amount') == 0 else 'Взнос: ' + (money(fee) or '?')); en.append('Entry: free' if fee.get('amount') == 0 else 'Entry fee: ' + (money(fee) or '?'))
        if r.get('length_minutes'):
            lo, hi = r['length_minutes']; span = str(lo) if lo == hi else str(lo) + '-' + str(hi)
            ru.append('Длина: ' + span + ' мин' + ('; программа: ' + r['required_tool'] if r.get('required_tool') else ''))
            en.append('Length: ' + span + ' min' + ('; tool: ' + r['required_tool'] if r.get('required_tool') else ''))
        if r.get('dig_in'):
            read = sum(1 for p in r.get('rules_pages', []) if p.get('classification') not in ('source_unavailable', 'not_checked_this_run_budget'))
            ru.append('Правила дочитаны: страниц ' + str(read) + ' (подробно - на ПК)'); en.append('Rules read: ' + str(read) + ' page(s) (details on the PC)')
        miss = [KEY_UNKNOWN[k] for k, f in (('deadline', 'declared_deadline'), ('prize', 'prize')) if not r.get(f)]
        out.append(finish({'id': card_id('c', r['key']), 'kind': 'reveng', 'prof': 'конкурс', 'prof_en': 'contest', 'text': r['title'][:70], 'lines': ru, 'lines_en': en,
                           'unknown': ('Не указан ' + ' и '.join(x[0] for x in miss) + '.') if miss else '',
                           'unknown_en': ('No ' + ' or '.join(x[1] for x in miss) + ' stated.') if miss else '',
                           'url': r['source_url']}))
    return out


def deal_cards(root):
    folder = root / 'deals'
    if not folder.is_dir():
        return []
    import deal_economics as de
    out = []
    for f in sorted(folder.glob('*.json')):
        r = de.compute(json.loads(f.read_text(encoding='utf-8')))
        c = r.get('currency') or ''
        if r['status'] == 'not_computable':
            lines = ['Посчитать нельзя: не хватает ' + ', '.join(r['missing_required'] or ['верных цифр'])]
        else:
            lines = ['Вложить на партию: ' + money({'amount': r['capital_needed'], 'currency': c}),
                     'Остаётся с партии: ' + money({'amount': r['profit_total'], 'currency': c}) + ' (' + str(r['return_on_capital_pct']) + '% на вложенное)',
                     'В ноль при цене продажи: ' + money({'amount': r['break_even_sell_price'], 'currency': c}),
                     'Оборот денег: ' + (str(int(r['cash_cycle_days'])) + ' дн.' if r.get('cash_cycle_days') else 'не указан')]
        if r['status'] == 'not_computable':
            en = ['Cannot compute: missing ' + ', '.join(r['missing_required'] or ['valid figures'])]
        else:
            en = ['Capital for the batch: ' + money({'amount': r['capital_needed'], 'currency': c}),
                  'Left from the batch: ' + money({'amount': r['profit_total'], 'currency': c}) + ' (' + str(r['return_on_capital_pct']) + '% on capital)',
                  'Break-even sell price: ' + money({'amount': r['break_even_sell_price'], 'currency': c}),
                  'Cash cycle: ' + (str(int(r['cash_cycle_days'])) + ' days' if r.get('cash_cycle_days') else 'not given')]
        guess = r.get('assumptions_used') or []
        out.append(finish({'id': card_id('d', f.stem), 'kind': 'reveng', 'prof': 'перепродажа', 'prof_en': 'resale', 'text': (r.get('title') or f.stem)[:70],
                           'lines': lines, 'lines_en': en,
                           'unknown': ('Догадки: ' + ', '.join(guess) + '. ' if guess else '') + 'Покупатель не найден.',
                           'unknown_en': ('Guesses: ' + ', '.join(guess) + '. ' if guess else '') + 'No buyer found yet.'}))
    return out


def phone_dir(given=None):
    if given:
        return Path(given)
    base = os.environ.get('LOCALAPPDATA')
    return Path(base) / 'MerchForge' / 'phone-sync' if base else None


def write(root, given_dir=None, today=None):
    """Writes the cards into the phone folder when it exists; returns (number of cards, where or why not)."""
    root = Path(root); today = today or date.today().isoformat()
    cards = contest_cards(root, today) + deal_cards(root)
    payload = {'schema': SCHEMA, 'cards': cards}
    (root / 'phone-cards.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    try:   # the owner's swipes kept in RevEng's own folder too, so they go into RevEng's export
        got = decisions(given_dir)
        if got:
            (root / 'phone-decisions.json').write_text(json.dumps({'schema': 'reveng-phone-decisions-v1', 'decisions': got}, ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception:
        pass
    target = phone_dir(given_dir)
    if not target or not target.is_dir():
        return len(cards), 'phone folder not found; cards kept in phone-cards.json only'
    tmp = target / 'reveng-cards.json.tmp'
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8'); os.replace(tmp, target / 'reveng-cards.json')
    return len(cards), str(target / 'reveng-cards.json')


def decisions(given_dir=None):
    """The phone's decisions on RevEng cards, as Forge's sync recorded them: {card id: verdict}."""
    target = phone_dir(given_dir)
    f = target / 'decisions.json' if target else None
    if not f or not f.exists():
        return {}
    return {k: v.get('verdict') for k, v in json.loads(f.read_text(encoding='utf-8-sig')).items() if k.startswith('rv_')}


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True); a.add_argument('--phone-dir')
    o = a.parse_args()
    n, where = write(o.root, o.phone_dir)
    print('cards', n, '->', where)
    print('decisions', json.dumps(decisions(o.phone_dir), ensure_ascii=False))

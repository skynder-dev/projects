"""Reverse engineering from profit (owner, 02.11.2026): start from businesses that already make money, see how, and
compare them - nothing is dropped because it needs capital, people or skills; that is written down as what it takes.

Source: Empire Flippers' public listings API (businesses for sale and sold, with the seller's monthly net profit,
revenue, expenses, asking price, hours of work per week, summary, risks, work required, trends). The figures are the
seller's and the marketplace's, not checked by RevEng. Same bounded transport (HTTPS, robots.txt, no redirects, request
budget). No model, no contact, no offer.

    python business_listings.py --root <research root> [--offline]
"""
import argparse, json, re
from pathlib import Path
from urllib.parse import urlsplit
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'reveng-business-listings-v1'
API = 'https://api.empireflippers.com/api/v1/listings/list?limit=100&page='
PAGES = 3
TOP = 8


def num(x):
    try:
        v = float(x)
        return v if v == v and abs(v) < 1e12 else None
    except (TypeError, ValueError):
        return None


def sentence(text, words=24):
    text = re.sub(r'<[^>]+>', ' ', str(text or '')); text = ' '.join(text.split())
    first = re.split(r'(?<=[.!?])\s', text, 1)[0]
    return ' '.join(first.split()[:words])


def row(x):
    """One listing as RevEng keeps it: the money, the work, what it is; derived figures say how they are derived."""
    profit, revenue, price, hours = (num(x.get(k)) for k in ('average_monthly_net_profit', 'average_monthly_gross_revenue', 'listing_price', 'hours_worked_per_week'))
    if not profit or profit <= 0:
        return None
    return {'id': str(x.get('id', '')), 'number': x.get('listing_number'), 'title': str(x.get('public_title') or '')[:90], 'status': x.get('listing_status'),
            'monthly_net_profit': profit, 'monthly_revenue': revenue, 'price': price if price and not x.get('unpriced') else None,
            'hours_per_week': hours, 'profit_per_hour': round(profit / (hours * 52 / 12), 1) if hours else None,
            'payback_months': round(price / profit, 1) if price and not x.get('unpriced') else None, 'margin_pct': num(x.get('profit_margin')),
            'profit_trend_pct': num(x.get('net_profit_trend_percent')), 'trend_months': x.get('net_profit_trend_percent_months'),
            'since': str(x.get('first_made_money_at') or '')[:7], 'how': sentence(x.get('summary')),
            'work_required': [str(w)[:80] for w in (x.get('work_required') or [])[:4]], 'risks': [sentence(r, 16) for r in (x.get('risks') or [])[:3]],
            'url': 'https://empireflippers.com/listing/' + str(x.get('listing_number')) + '/' if x.get('listing_number') else None,
            'figures_by': 'seller and Empire Flippers; not checked by RevEng'}


def rank(rows):
    """No filter by what we can do or afford; two plain orders: money per hour of work, and how fast the price comes back."""
    by_hour = sorted([r for r in rows if r['profit_per_hour']], key=lambda r: r['profit_per_hour'], reverse=True)
    by_payback = sorted([r for r in rows if r['payback_months']], key=lambda r: r['payback_months'])
    picked, seen = [], set()
    for r in [x for pair in zip(by_hour, by_payback) for x in pair] + by_hour + by_payback:
        if r['id'] not in seen:
            seen.add(r['id']); picked.append(r)
        if len(picked) >= TOP:
            break
    return picked


def collect(root, stats, offline=False, read=None):
    read = read or m.read_http; root = Path(root); result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'Empire Flippers public listings API'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        rp = robotparser.RobotFileParser(); rp.parse(read('https://' + urlsplit(API).netloc + '/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines())
        rows, total = [], None
        for page in range(1, PAGES + 1):
            if not rp.can_fetch(m.UA, API + str(page)):
                raise ValueError('robots.txt denied')
            data = json.loads(read(API + str(page), stats, 8388608).decode('utf-8')).get('data') or {}
            total = data.get('count', total)
            rows += [r for r in (row(x) for x in data.get('listings') or []) if r]
            if str(data.get('page')) == str(data.get('pages')):
                break
        result.update(status='read', listings_total=total, read=len(rows), top=rank(rows),
                      for_sale=sum(1 for r in rows if str(r['status']).lower().startswith('for sale')))
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), top=[])
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'business-listings.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'total', r.get('listings_total'), 'read', r.get('read'), 'for sale', r.get('for_sale'), 'requests', r['source_requests'])
    for x in r['top']:
        print('  $%s/mo' % int(x['monthly_net_profit']), x['hours_per_week'], 'h/wk', '$/h', x['profit_per_hour'], 'price', x['price'], 'payback', x['payback_months'], '|', x['title'], '|', x['how'][:90])
    try:
        import phone_cards
        print('phone cards', *phone_cards.write(o.root.resolve()))
    except Exception as ex:
        print('phone cards not written:', m.error_text(ex, 160))

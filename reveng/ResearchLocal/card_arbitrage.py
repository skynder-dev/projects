"""Trial of the deal search (owner's go 02.11.2026): the same Magic: The Gathering card priced on two markets, Europe
(Cardmarket, EUR) and the USA (TCGplayer, USD), as Scryfall's open API publishes them daily; converted at the ECB daily
reference rate; fees and shipping are labelled assumptions; only clear gaps become deals (deals/mtg-*.json) for
deal_economics and the phone cards. Same bounded transport as the rest of RevEng (HTTPS, robots.txt, no redirects,
request budget). No model, no purchase, no listing, no account.

The prices are Scryfall's daily market/trend figures, not offers anyone has to honour and not sales; card condition,
stock, customs and transit time are not known. This is a test of the mechanism, not a business verdict.

    python card_arbitrage.py --root <research root> [--offline]
"""
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'reveng-card-arbitrage-v1'
SEARCH = 'https://api.scryfall.com/cards/search?order=usd&dir=desc&unique=prints&q='
QUERY = 'usd>=8 usd<=150 eur>=1 -is:digital game:paper'   # rare cards over $150 sell too seldom for a daily average to mean much
PAGES = 3                                      # up to 175 printings a page
ECB = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
# labelled assumptions, never presented as found: a seller's total fees when selling on each market, and shipping one card
SELL_FEE_PCT = {'US': 13.25, 'EU': 5.0}       # TCGplayer ~10.75% + payment ~2.5%; Cardmarket ~5%
SHIPPING_USD = 6.0                             # one tracked letter between Europe and the USA, one card
MIN_PROFIT_USD = 5.0
MAX_DEALS = 8
MAX_RATIO = 2.5   # a price over 2.5x the other market's is taken as a data artefact (a lone listing, another printing), not a deal


def ecb_rate(raw):
    """USD per 1 EUR from the ECB daily XML, with the date it is for."""
    text = raw.decode('utf-8')
    rate = re.search(r"currency=['\"]USD['\"]\s+rate=['\"]([0-9.]+)['\"]", text); day = re.search(r"time=['\"](\d{4}-\d{2}-\d{2})['\"]", text)
    if not rate:
        raise ValueError('ECB file has no USD rate')
    return float(rate.group(1)), day.group(1) if day else None


def rows(pages):
    """(name, set, uri, usd, eur) for printings that have both prices."""
    out = []
    for page in pages:
        for c in page.get('data', []):
            p = c.get('prices') or {}
            try:
                usd, eur = float(p.get('usd') or 0), float(p.get('eur') or 0)
            except (TypeError, ValueError):
                continue
            if usd > 0 and eur > 0 and str(c.get('scryfall_uri', '')).startswith('https://'):
                out.append({'id': c.get('id', ''), 'name': c.get('name', ''), 'set': c.get('set', '').upper(), 'uri': c['scryfall_uri'].split('?')[0],
                            'usd': usd, 'eur': eur})
    return out


def suspicious(cards, rate):
    return sum(1 for c in cards if max(c['usd'], c['eur'] * rate) > MAX_RATIO * min(c['usd'], c['eur'] * rate))


def gaps(cards, rate, rate_day):
    """Both directions per printing; a deal only when what is left after the assumed fees and shipping clears the bar."""
    deals = []
    for c in cards:
        eu_in_usd = round(c['eur'] * rate, 2)
        for buy, sell, buy_usd, sell_usd, market in (('EU', 'US', eu_in_usd, c['usd'], 'US'), ('US', 'EU', c['usd'], eu_in_usd, 'EU')):
            left = sell_usd * (1 - SELL_FEE_PCT[market] / 100) - buy_usd - SHIPPING_USD
            if sell_usd > buy_usd * MAX_RATIO:
                continue
            if left >= MIN_PROFIT_USD:
                deals.append(dict(c, buy=buy, sell=sell, buy_usd=buy_usd, sell_usd=sell_usd, left=round(left, 2), rate=rate, rate_day=rate_day))
    deals.sort(key=lambda d: d['left'], reverse=True)
    seen, out = set(), []
    for d in deals:   # one deal per card name: the best printing
        if d['name'] in seen:
            continue
        seen.add(d['name']); out.append(d)
    return out[:MAX_DEALS]


def deal_file(d):
    """A deal_economics input: prices quoted from Scryfall's figures (with the ECB rate for euros), the rest assumptions."""
    eur_q = 'Scryfall eur ' + format(d['eur'], '.2f') + ' x ECB ' + str(d['rate']) + ' USD/EUR (' + str(d['rate_day']) + ')'
    usd_q = 'Scryfall usd ' + format(d['usd'], '.2f')
    buy_q, sell_q = (eur_q, usd_q) if d['buy'] == 'EU' else (usd_q, eur_q)
    where = {'EU': ('в Европе (Cardmarket)', 'in Europe (Cardmarket)'), 'US': ('в США (TCGplayer)', 'in the USA (TCGplayer)')}
    return {'schema': 'reveng-resale-deal-v1', 'title': 'MTG: ' + d['name'] + ' (' + d['set'] + ')', 'currency': 'USD', 'source': d['uri'],
            'origin': 'card_arbitrage trial: Scryfall daily prices, not sales',
            'lines_ru': ['Купить ' + where[d['buy']][0] + ': ~$' + format(d['buy_usd'], '.2f'), 'Продать ' + where[d['sell']][0] + ': ~$' + format(d['sell_usd'], '.2f'),
                         'Остаётся ~$' + format(d['left'], '.2f') + ' с карты (комиссии ' + str(SELL_FEE_PCT[d['sell']]) + '% и доставка $' + format(SHIPPING_USD, '.0f') + ' - допущения)'],
            'lines_en': ['Buy ' + where[d['buy']][1] + ': ~$' + format(d['buy_usd'], '.2f'), 'Sell ' + where[d['sell']][1] + ': ~$' + format(d['sell_usd'], '.2f'),
                         '~$' + format(d['left'], '.2f') + ' left per card (fees ' + str(SELL_FEE_PCT[d['sell']]) + '% and shipping $' + format(SHIPPING_USD, '.0f') + ' assumed)'],
            'figures': {'buy_price': {'value': d['buy_usd'], 'status': 'quoted', 'quote': buy_q, 'url': d['uri']},
                        'sell_price': {'value': d['sell_usd'], 'status': 'quoted', 'quote': sell_q, 'url': d['uri']},
                        'quantity': {'value': 1, 'status': 'assumption'},
                        'shipping_per_unit': {'value': SHIPPING_USD, 'status': 'assumption'},
                        'sales_fees_pct_of_sell': {'value': SELL_FEE_PCT[d['sell']], 'status': 'assumption'}}}


def allowed(url, stats, read, robots):
    host = urlsplit(url).netloc
    if host not in robots:
        rp = robotparser.RobotFileParser(); rp.parse(read('https://' + host + '/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines()); robots[host] = rp
    if not robots[host].can_fetch(m.UA, url):
        raise ValueError('robots.txt denied ' + host)


def collect(root, stats, offline=False, read=None):
    """Reads the ECB rate and the search pages (or nothing offline), writes deals/mtg-*.json (old ones replaced) and a
    sealed card-arbitrage.json with what was read and why each step ended."""
    read = read or m.read_http
    root = Path(root); folder = root / 'deals'; folder.mkdir(exist_ok=True); result = {'schema': SCHEMA, 'checked_at': m.now(), 'query': QUERY,
                                                                                       'assumptions': {'sell_fee_pct': SELL_FEE_PCT, 'shipping_usd': SHIPPING_USD, 'min_profit_usd': MIN_PROFIT_USD}}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        robots = {}; allowed(ECB, stats, read, robots)
        rate, day = ecb_rate(read(ECB, stats, 65536))
        pages, url = [], SEARCH + quote(QUERY)
        for _ in range(PAGES):
            allowed(url, stats, read, robots)
            page = json.loads(read(url, stats, 4194304).decode('utf-8')); pages.append(page)
            if not page.get('has_more') or not str(page.get('next_page', '')).startswith('https://api.scryfall.com/'):
                break
            url = page['next_page']; time.sleep(0.15)   # Scryfall asks for 50-100 ms between requests
        cards = rows(pages); deals = gaps(cards, rate, day)
        for old in folder.glob('mtg-*.json'):
            old.unlink()
        for i, d in enumerate(deals, 1):
            (folder / ('mtg-%02d.json' % i)).write_text(json.dumps(deal_file(d), ensure_ascii=False, indent=1), encoding='utf-8')
        result.update(status='read', ecb_usd_per_eur=rate, ecb_day=day, printings_with_both_prices=len(cards), dropped_as_suspicious=suspicious(cards, rate), deals=[{k: d[k] for k in ('name', 'set', 'buy', 'sell', 'buy_usd', 'sell_usd', 'left', 'uri')} for d in deals])
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), deals=[])
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'card-arbitrage.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'rate', r.get('ecb_usd_per_eur'), 'printings', r.get('printings_with_both_prices'), 'suspicious', r.get('dropped_as_suspicious'), 'requests', r['source_requests'])
    for d in r['deals']:
        print('  ', d['left'], d['buy'], '->', d['sell'], d['name'], d['set'], d['buy_usd'], d['sell_usd'])
    try:
        import phone_cards
        print('phone cards', *phone_cards.write(o.root.resolve()))
    except Exception as ex:
        print('phone cards not written:', m.error_text(ex, 160))

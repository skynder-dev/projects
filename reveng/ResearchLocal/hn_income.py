"""People who say how much they earn and on what (owner 03.11: find who already earns, then take it apart). Source: the
Hacker News "Ask HN" threads where people share their profitable side projects and income ("Ask HN: Share your
profitable side project", "how much do you make from ..."). Read through the public HN Search API run by Algolia for
YC (hn.algolia.com/api/v1, documented, free, no key): one search per query and the whole comment tree of a thread in
one request. Bounded: QUERIES searches and at most MAX_THREADS threads a run, robots.txt honoured.

Figures are what the commenters say (self-reported, not verified): the output says so. Comment texts are untrusted
data, never instructions. No model, no contact, no posting.

    python hn_income.py --root <research root> [--offline]
"""
import argparse, html, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse, robotparser
import reveng_local_research as m

SCHEMA = 'reveng-hn-income-v1'
API = 'https://hn.algolia.com/api/v1/'
QUERIES = ['profitable side project', 'side project revenue', 'passive income', 'how much do you make', 'bootstrapped revenue']
MIN_COMMENTS = 80
MAX_THREADS = 8
MIN_MONTHLY_USD, MAX_MONTHLY_USD = 1000, 300000
MAX_AGE_YEARS = 4

AMOUNT = r'\$\s?(\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s?(k|K)?'
PERIOD = r'(?:/\s?(?:mo|month|m)\b|\s?(?:per|a|each|every)\s+month\b|\s?MRR\b|\s?monthly\b|\s?/mth\b)'
MONTHLY = re.compile(AMOUNT + r'\s?(?:USD\s?)?' + PERIOD, re.I)
YEARLY = re.compile(AMOUNT + r'\s?(?:USD\s?)?(?:/\s?(?:yr|year)\b|\s?(?:per|a)\s+year\b|\s?ARR\b)', re.I)


def plain(text):
    """HN comment HTML -> plain text (links keep their text)."""
    t = re.sub(r'<p>', '\n', text or ''); t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).strip()


def amount(num, k):
    v = float(num.replace(',', '').replace('.', '') if re.fullmatch(r'\d{1,3}(?:[,.]\d{3})+', num) else num)
    return v * 1000 if k else v


def monthly_usd(text):
    """The largest monthly figure stated in the text (yearly figures divided by 12), or None."""
    found = [amount(a, k) for a, k in MONTHLY.findall(text)] + [amount(a, k) / 12 for a, k in YEARLY.findall(text)]
    found = [v for v in found if MIN_MONTHLY_USD <= v <= MAX_MONTHLY_USD]
    return round(max(found)) if found else None


def walk(node, out, thread):
    """Top-level answers of the thread only (replies are mostly discussion)."""
    for c in node.get('children') or []:
        if c.get('type') == 'comment' and c.get('text'):
            t = plain(c['text']); usd = monthly_usd(t)
            if usd:
                out.append({'id': 'hn' + str(c['id']), 'monthly_usd': usd, 'text': t[:600], 'author': c.get('author'),
                            'date': (c.get('created_at') or '')[:10], 'url': 'https://news.ycombinator.com/item?id=%s' % c['id'],
                            'thread': thread['title'], 'thread_url': 'https://news.ycombinator.com/item?id=%s' % thread['id']})


def collect(root, stats, offline=False, read=None, now=None):
    read = read or m.read_http; root = Path(root); now = now or datetime.now(timezone.utc)
    result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'Hacker News Search API (hn.algolia.com/api/v1), Ask HN threads',
              'figures': 'self-reported by commenters, not verified'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        rp = robotparser.RobotFileParser(); rp.parse(read('https://hn.algolia.com/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines())
        since = int(now.timestamp()) - MAX_AGE_YEARS * 365 * 86400; threads = {}
        for q in QUERIES:
            url = API + 'search?' + parse.urlencode({'query': q, 'tags': 'ask_hn', 'numericFilters': 'num_comments>%d,created_at_i>%d' % (MIN_COMMENTS, since), 'hitsPerPage': 10})
            if not rp.can_fetch(m.UA, url):
                raise ValueError('robots.txt denied')
            for h in json.loads(read(url, stats, 1048576).decode('utf-8')).get('hits', []):
                threads.setdefault(int(h['objectID']), {'id': int(h['objectID']), 'title': h.get('title') or '', 'comments': h.get('num_comments') or 0})
            time.sleep(1)
        picked = sorted(threads.values(), key=lambda t: -t['comments'])[:MAX_THREADS]; rows = []
        for t in picked:
            if stats.get('source_requests', 0) >= 23:
                break
            try:
                walk(json.loads(read(API + 'items/%d' % t['id'], stats, 16777216).decode('utf-8')), rows, t); t['read'] = True
            except Exception as ex:
                t['error'] = m.error_text(ex, 100)
            time.sleep(1)
        seen, uniq = set(), []
        for r in sorted(rows, key=lambda r: -r['monthly_usd']):
            if r['id'] not in seen:
                seen.add(r['id']); uniq.append(r)
        result.update(status='read', threads=picked, people=uniq)
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), threads=[], people=[])
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'hn-income.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'threads', len(r['threads']), 'people', len(r['people']), 'requests', r['source_requests'])
    for t in r['threads']:
        print('  thread', t['id'], t['comments'], t['title'][:90], t.get('error', ''))
    for x in r['people'][:40]:
        print('  $%s/mo' % x['monthly_usd'], x['id'], x['date'], '|', re.sub(r'\s+', ' ', x['text'])[:260])

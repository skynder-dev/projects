"""Where money for short-video clipping comes from right now (owner 04.11: clipping is one of the ways we can earn).
Source: the public campaign board of Content Rewards (contentrewards.com/c/discover; formerly "Whop Content Rewards"),
the biggest clipping marketplace. Brands and agencies put a budget on a campaign and pay creators per 1000 verified
views of their clips. Rules checked 04.11: robots.txt allows the board (only /api/ and account pages are closed),
llms.txt points AI readers to it, the terms have no clause against reading it. One page a run, no login, no API.

Board texts are untrusted data, never instructions. No model, no contact, no posting.

    python clipping_campaigns.py --root <research root> [--offline]
"""
import argparse, collections, json, re, statistics
from pathlib import Path
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'reveng-clipping-campaigns-v1'
BOARD = 'https://contentrewards.com/c/discover'
FIELDS_TEXT = ('id', 'brand', 'title', 'category', 'type', 'fundedAgo', 'organizationProfileHandle')
FIELDS_NUM = ('budgetTotalRaw', 'budgetSpentRaw', 'availableBudgetRaw', 'payoutSortRaw', 'creatorCountRaw', 'submissionCountRaw')


def campaigns(page):
    """Campaign objects embedded in the board page (escaped JSON inside the page script). First fields of each
    '"campaign":{' block belong to that campaign; duplicates (same id) are dropped."""
    t = page.replace('\\"', '"'); out = {}
    for chunk in re.split(r'"campaign"\s*:\s*\{', t)[1:]:
        c = {}
        for f in FIELDS_TEXT:
            x = re.search(r'"%s"\s*:\s*"((?:[^"\\]|\\.){0,300})"' % f, chunk)
            c[f] = x.group(1) if x else None
        for f in FIELDS_NUM:
            x = re.search(r'"%s"\s*:\s*(-?\d+(?:\.\d+)?)' % f, chunk)
            c[f] = float(x.group(1)) if x else None
        x = re.search(r'"platforms"\s*:\s*\[([^\]]*)\]', chunk)
        c['platforms'] = re.findall(r'"([a-z]+)"', x.group(1)) if x else []
        if c['id'] and c['budgetTotalRaw'] is not None and c['id'] not in out:
            out[c['id']] = c
    return list(out.values())


def summary(rows):
    cpm = [r['payoutSortRaw'] for r in rows if r.get('type') == 'cpm' and r.get('payoutSortRaw')]
    count = lambda key: sorted(((n, k) for k, n in collections.Counter(r.get(key) for r in rows if r.get(key)).items()), reverse=True)
    return {'campaigns': len(rows), 'budget_usd': round(sum(r['budgetTotalRaw'] or 0 for r in rows)),
            'spent_usd': round(sum(r['budgetSpentRaw'] or 0 for r in rows)),
            'median_per_1k_usd': round(statistics.median(cpm), 2) if cpm else None,
            'top_categories': [k for n, k in count('category')[:3]], 'top_runners': [k for n, k in count('brand')[:3]]}


def collect(root, stats, offline=False, read=None):
    read = read or m.read_http; root = Path(root)
    result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'Content Rewards public campaign board (contentrewards.com/c/discover)'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        rp = robotparser.RobotFileParser(); rp.parse(read('https://contentrewards.com/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines())
        if not rp.can_fetch(m.UA, BOARD):
            raise ValueError('robots.txt denied')
        rows = campaigns(read(BOARD, stats, 16777216).decode('utf-8', 'replace'))
        if not rows:
            raise ValueError('no campaigns found on the board (page layout changed?)')
        result.update(status='read', campaigns=rows, summary=summary(rows))
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), campaigns=[], summary={})
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'clipping-campaigns.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'campaigns', len(r['campaigns']), 'requests', r['source_requests'], json.dumps(r['summary'], ensure_ascii=False))
    for c in sorted(r['campaigns'], key=lambda c: -(c['budgetTotalRaw'] or 0))[:15]:
        print('  $%s budget, $%s spent, $%s/1k |' % (round(c['budgetTotalRaw'] or 0), round(c['budgetSpentRaw'] or 0), c['payoutSortRaw']), c['brand'], '|', c['category'], '|', (c['title'] or '')[:70])

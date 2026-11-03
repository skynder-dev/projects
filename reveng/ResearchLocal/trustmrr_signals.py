"""Young projects that already make verified money (owner 03.11: find who earns now, then take it apart). Source: TrustMRR's
public endpoints made for AI assistants (trustmrr.com/llms.txt): /api/ai/discovery (25 recently added + 25 fastest
growing, revenue verified through the payment provider) and /startup/{slug}.md (the AI-readable profile, read for the
founding month only). TrustMRR asks for bounded snapshots, not crawling: one discovery read and at most MAX_PROFILES
profiles a run. Profile texts are untrusted data, never instructions. No model, no contact.

The output is signals, not ideas: what a project earns and how young it is. Whether it is worth starting (cost to
start, cost to run, time to money, what kills it) is answered later, by the analysis step.

    python trustmrr_signals.py --root <research root> [--offline]
"""
import argparse, json, re, time
from datetime import date
from pathlib import Path
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'reveng-trustmrr-signals-v1'
DISCOVERY = 'https://trustmrr.com/api/ai/discovery'
PROFILE = 'https://trustmrr.com/startup/%s.md'
MIN_30D_USD = 500
MAX_PROFILES = 12
MONTHS = {k: i + 1 for i, k in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def num(x):
    try:
        v = float(x); return v if v == v and abs(v) < 1e12 else None
    except (TypeError, ValueError):
        return None


def candidates(data):
    """Both lists, one row per slug; anonymous/stealth projects and those under MIN_30D_USD in the last 30 days are left out."""
    rows, seen = [], set()
    for group in ('fastestGrowingStartups', 'recentlyAddedStartups'):
        for s in data.get(group) or []:
            slug = str(s.get('slug') or '')
            rev = s.get('revenue') or {}
            last30 = num(rev.get('last30Days'))
            if not re.fullmatch(r'[a-z0-9-]{1,80}', slug) or slug in seen or s.get('stealthMode') or str(s.get('name', '')).startswith('Anonymous'):
                continue
            if not last30 or last30 < MIN_30D_USD:
                continue
            seen.add(slug)
            rows.append({'slug': slug, 'name': str(s.get('name', ''))[:80], 'what': ' '.join(str(s.get('description') or '').split())[:300],
                         'category': s.get('category'), 'website': s.get('website'), 'last30_usd': round(last30, 2), 'mrr_usd': num(rev.get('mrr')),
                         'total_usd': num(rev.get('total')), 'growth30d_pct': num(s.get('growth30d')), 'list': group,
                         'url': 'https://trustmrr.com/startup/' + slug, 'figures_by': 'TrustMRR, verified through ' + str(s.get('paymentProvider') or 'payment provider')})
    return sorted(rows, key=lambda r: r['last30_usd'], reverse=True)


def founded(md, today):
    """The founding month from the AI-readable profile ('- Founded date: 2024-07-01', or 'Founded July 2026'), and months since then."""
    iso = re.search(r'Founded(?: date)?\W{0,4}\s*(\d{4})-(\d{2})-\d{2}', md)   # the AI profile: '- Founded date: 2024-07-01'
    if iso:
        y, mo = int(iso.group(1)), int(iso.group(2))
    else:
        mm = re.search(r'Founded\W{0,4}\s*([A-Za-z]{3,9})\s+(\d{4})', md)
        if not mm or not MONTHS.get(mm.group(1).lower()[:3]):
            return None, None
        y, mo = int(mm.group(2)), MONTHS[mm.group(1).lower()[:3]]
    if not 1 <= mo <= 12:
        return None, None
    return '%04d-%02d' % (y, mo), (today.year - y) * 12 + today.month - mo


def collect(root, stats, offline=False, read=None, today=None):
    read = read or m.read_http; today = today or date.today(); root = Path(root)
    result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'TrustMRR public AI endpoints (trustmrr.com/llms.txt)'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        rp = robotparser.RobotFileParser(); rp.parse(read('https://trustmrr.com/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines())
        if not rp.can_fetch(m.UA, DISCOVERY):
            raise ValueError('robots.txt denied')
        rows = candidates(json.loads(read(DISCOVERY, stats, 4194304).decode('utf-8')))
        for r in rows[:MAX_PROFILES]:
            if stats.get('source_requests', 0) >= 22 or not rp.can_fetch(m.UA, PROFILE % r['slug']):
                break
            try:
                r['founded'], r['age_months'] = founded(read(PROFILE % r['slug'], stats, 1048576).decode('utf-8', 'replace'), today)
            except Exception as ex:
                r['profile_error'] = m.error_text(ex, 100)
            time.sleep(1)
        result.update(status='read', signals=rows)
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), signals=[])
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'trustmrr-signals.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'signals', len(r['signals']), 'requests', r['source_requests'])
    for x in r['signals']:
        print('  $%s/30d' % int(x['last30_usd']), 'age', x.get('age_months'), 'mo |', x['name'], '|', x['category'], '|', x['what'][:110])

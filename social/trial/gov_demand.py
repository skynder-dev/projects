"""What people look up on U.S. government websites (public analytics.usa.gov data), ranked as topic demand for the
four Social channels. Read-only: downloads public JSON files (no key), keeps the raw files with SHA-256, writes
demand.json (ranked pages) and demand_summary.txt (plain Russian for the owner).

Usage: python -I gov_demand.py OUT_DIR
"""
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'raw').mkdir(exist_ok=True)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

BASE = 'https://analytics.usa.gov/data'
AGENCIES = ['general-services-administration', 'education', 'labor', 'treasury', 'social-security-administration',
            'small-business-administration', 'health-human-services', 'housing-urban-development', 'veterans-affairs',
            'agriculture', 'homeland-security']
FILES = ['live/top-pages-30-days.json', 'live/all-pages-realtime.json'] + [f'{a}/top-pages-30-days.json' for a in AGENCIES]

# which channel a page belongs to (by host, then by words in the address or title)
HOST_CHANNEL = [(r'(^|\.)studentaid\.gov$|(^|\.)ed\.gov$|collegescorecard', 'Учёба'),
                (r'(^|\.)sba\.gov$|(^|\.)sam\.gov$|(^|\.)grants\.gov$|(^|\.)sbir\.gov$', 'Малый бизнес и НКО'),
                (r'(^|\.)va\.gov$|(^|\.)firegrantsupport|(^|\.)usda\.gov$|(^|\.)farmers\.gov$|apprenticeship', 'Профессии')]
WORD_CHANNEL = [(r'student|college|fafsa|scholarship|pell|school', 'Учёба'),
                (r'small business|sba|loan program|contract|sbir|startup|business', 'Малый бизнес и НКО'),
                (r'veteran|farmer|apprentice|firefight|teacher|nurse', 'Профессии')]
WANT = re.compile(r'benefit|assist|aid|help|grant|loan|refund|tax|credit|unemploy|food|snap|housing|rent|energy|'
                  r'unclaimed|wage|pay|retire|disab|medicaid|medicare|insurance|student|fafsa|apply|eligib|'
                  r'forgiv|debt|disaster|veteran|small business|scam|fraud', re.I)
SKIP = re.compile(r'login|logout|log-in|sign-?in|signin|sign-?up|account|password|search|status|track|callback|'
                  r'portal|auth|verify|two-step|captcha|cookie|privacy|contact|404|error|/my-|/my$|'
                  r'make-payment|direct-pay|/payments|recover|default\.aspx|nonimmigrant|visa', re.I)
SKIP_HOST = re.compile(r'(^|\.)(state\.gov|login\.gov|ceac\.state\.gov)$', re.I)


def get(path: str):
    url = f'{BASE}/{path}'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'social-demand/1.0'}),
                                    timeout=60) as r:
            raw = r.read()
    except Exception as e:  # noqa: BLE001
        return None, f'{path}: {e!r}'[:200]
    name = path.replace('/', '__')
    (OUT / 'raw' / name).write_bytes(raw)
    return json.loads(raw.decode('utf-8')), {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def rows(doc: dict) -> list:
    data = doc.get('data') if isinstance(doc, dict) else None
    return data if isinstance(data, list) else []


def channel(host: str, text: str) -> str:
    for pat, ch in HOST_CHANNEL:
        if re.search(pat, host, re.I):
            return ch
    for pat, ch in WORD_CHANNEL:
        if re.search(pat, text, re.I):
            return ch
    return 'Помощь людям'


pages, files, errors = {}, [], []
for path in FILES:
    doc, meta = get(path)
    if doc is None:
        errors.append(meta)
        continue
    files.append(meta)
    live = 'realtime' in path
    if rows(doc):
        files[-1]['fields'] = sorted(rows(doc)[0].keys())
    for r in rows(doc):
        url = r.get('page') or r.get('fullPageUrl') or r.get('page_url') or ''
        host = r.get('domain') or r.get('hostName') or ''
        title = (r.get('page_title') or r.get('pageTitle') or '').strip()
        views = int(float(r.get('pageviews') or r.get('screenPageViews') or r.get('active_visitors')
                          or r.get('activeUsers') or r.get('active_users') or r.get('visits') or r.get('sessions')
                          or r.get('users') or 0))
        if not url:
            continue
        if not url.startswith('http'):
            url = 'https://' + (url if '/' in url and '.' in url.split('/')[0] else host + '/' + url.lstrip('/'))
        p = urllib.parse.urlparse(url)
        host = host or p.netloc
        text = f'{p.path} {title}'
        if (not WANT.search(text) or SKIP.search(f'{p.path} {title}') or SKIP_HOST.search(p.netloc)
                or p.path.strip('/') == ''):
            continue
        key = (p.netloc.lower().removeprefix('www.') + p.path.rstrip('/')).lower()
        e = pages.setdefault(key, {'url': f'https://{p.netloc}{p.path}', 'host': p.netloc, 'title': title,
                                   'views_30d': 0, 'people_now': 0, 'seen_in': []})
        if live:
            e['people_now'] += views
        else:
            e['views_30d'] = max(e['views_30d'], views)
        if path not in e['seen_in']:
            e['seen_in'].append(path)
        e['title'] = e['title'] or title

ranked = sorted(pages.values(), key=lambda x: (x['views_30d'] + 3000 * x['people_now']), reverse=True)
for e in ranked:
    e['channel'] = channel(e['host'], f"{e['url']} {e['title']}")
    e['source_ready'] = bool(re.search(r'(^|\.)usa\.gov$', e['host']))  # Social reads USA.gov pages today
report = {'kind': 'SOCIAL_GOV_DEMAND', 'made_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'files': files,
          'errors': errors, 'pages': ranked[:300]}
(OUT / 'demand.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')

lines = [f'Спрос на госсайтах (analytics.usa.gov), {dt.date.today().isoformat()}: страниц про деньги и помощь {len(ranked)}.',
         f'Файлов прочитано {len(files)}, не открылись {len(errors)}.']
for ch in ('Помощь людям', 'Учёба', 'Малый бизнес и НКО', 'Профессии'):
    top = [e for e in ranked if e['channel'] == ch][:8]
    lines.append(f'\n{ch}: {sum(1 for e in ranked if e["channel"] == ch)} страниц, сверху:')
    for e in top:
        mark = ' [читаем]' if e['source_ready'] else ''
        lines.append(f"  {e['views_30d']:>9} за 30 дн, {e['people_now']:>5} сейчас | {e['title'][:70]} | {e['url'][:90]}{mark}")
hosts = {}
for e in ranked[:150]:
    hosts[e['host']] = hosts.get(e['host'], 0) + 1
lines.append('\nСайты, чаще всего в спросе (что подключать следующим): ' +
             ', '.join(f'{h} {n}' for h, n in sorted(hosts.items(), key=lambda x: -x[1])[:12]))
lines.append('\nПоля файлов: ' + '; '.join(f"{m['path']}={','.join(m.get('fields', []))}" for m in files[:3]))
if errors:
    lines.append('\nНе открылись: ' + '; '.join(errors))
(OUT / 'demand_summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))

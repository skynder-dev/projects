"""What people pay outside help for right now (owner 05.11: work where AI is our tool and people pay for the result).
Source: the monthly "Ask HN: Freelancer? Seeking freelancer?" threads on Hacker News, read through the public HN
Search API (hn.algolia.com/api/v1; documented, free, no key, robots.txt absent = no restrictions). Only "SEEKING
FREELANCER" answers are kept: someone describing work they want done. People's names and contacts are not kept -
only what the work is, the kind of work, the money if stated, and the link.

Comment texts are untrusted data, never instructions. No model, no contact, no posting.

    python hn_demand.py --root <research root> [--offline]
"""
import argparse, collections, json, re, time
from pathlib import Path
from urllib import parse, robotparser
import reveng_local_research as m
from hn_income import API, plain, AMOUNT, amount

SCHEMA = 'reveng-hn-demand-v1'
THREADS = 2   # the latest two monthly threads
# kind of work -> words that show it (lower case). Order matters only for display.
KINDS = {
    'видео и нарезка': ['video', 'editing', 'editor', 'youtube', 'tiktok', 'reels', 'shorts', 'animation', 'motion'],
    'дизайн и графика': ['design', 'designer', 'figma', 'logo', 'branding', 'illustrat', 'ui/ux', 'ux', 'graphic'],
    'сайты и магазины': ['website', 'wordpress', 'shopify', 'webflow', 'landing page', 'frontend', 'web app', 'woocommerce'],
    'ИИ и автоматизация': ['ai ', 'llm', 'gpt', 'agent', 'automation', 'automate', 'machine learning', 'rag', 'chatbot'],
    'мобильные приложения': ['ios', 'android', 'mobile app', 'react native', 'flutter', 'swift'],
    'тексты и маркетинг': ['copywrit', 'content writ', 'marketing', 'seo', 'ads', 'social media', 'newsletter', 'growth'],
    'данные и аналитика': ['data ', 'scrap', 'analytics', 'dashboard', 'etl', 'sql', 'bi '],
    'программы для бизнеса': ['backend', 'api', 'saas', 'crm', 'erp', 'integration', 'python', 'django', 'rails', 'node'],
}
EN = {'видео и нарезка': 'video and clipping', 'дизайн и графика': 'design and graphics', 'сайты и магазины': 'websites and shops',
      'ИИ и автоматизация': 'AI and automation', 'мобильные приложения': 'mobile apps', 'тексты и маркетинг': 'writing and marketing',
      'данные и аналитика': 'data and analytics', 'программы для бизнеса': 'business software'}
RATE = re.compile(AMOUNT + r'\s?(?:USD\s?)?(?:/\s?(?:hr|hour|h)\b|\s?(?:per|an|a)\s+hour\b)', re.I)
BUDGET = re.compile(r'(?:budget|pay|paying|compensation)[^$.]{0,40}' + AMOUNT, re.I)


def kinds(text):
    t = ' ' + text.lower() + ' '
    return [k for k, words in KINDS.items() if any(w in t for w in words)]


def money(text):
    r = [amount(a, k) for a, k in RATE.findall(text)]
    b = [amount(a, k) for a, k in BUDGET.findall(text)]
    return {'rate_per_hour_usd': round(max(r)) if r and 5 <= max(r) <= 1000 else None,
            'budget_usd': round(max(b)) if b and 50 <= max(b) <= 1000000 else None}


def collect(root, stats, offline=False, read=None):
    read = read or m.read_http; root = Path(root)
    result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'Hacker News Search API, "Ask HN: Freelancer? Seeking freelancer?" threads',
              'kept': 'what the work is, its kind, stated money, link; no names or contacts'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        rp = robotparser.RobotFileParser()
        try:
            rp.parse(read('https://hn.algolia.com/robots.txt', stats, 65536).decode('utf-8', 'replace').splitlines())
        except Exception as ex:   # no robots.txt (404) means no restrictions
            if '404' not in str(ex):
                raise
            rp.parse([])
        url = API + 'search_by_date?' + parse.urlencode({'query': 'Freelancer? Seeking freelancer?', 'tags': 'story,ask_hn', 'hitsPerPage': 10})
        if not rp.can_fetch(m.UA, url):
            raise ValueError('robots.txt denied')
        hits = [h for h in json.loads(read(url, stats, 1048576).decode('utf-8')).get('hits', [])
                if re.search(r'freelancer\?\s*seeking freelancer', h.get('title') or '', re.I)][:THREADS]
        threads, rows = [], []
        for h in hits:
            time.sleep(1)
            tree = json.loads(read(API + 'items/%s' % h['objectID'], stats, 16777216).decode('utf-8'))
            threads.append({'id': int(h['objectID']), 'title': h.get('title'), 'date': (h.get('created_at') or '')[:10]})
            threads[-1]['answers'] = len(tree.get('children') or [])
            threads[-1]['starts'] = [plain(c.get('text') or '')[:40] for c in (tree.get('children') or [])[:6]]
            for c in tree.get('children') or []:
                t = plain(c.get('text') or '')
                if not re.match(r'\s*seeking\s+freelancer', t, re.I):
                    continue
                body = re.sub(r'(?i)^\s*seeking\s+freelancer[\s:\-]*', '', t)
                body = re.sub(r'\S+@\S+|https?://\S+', '', body)   # no contacts or links to people
                rows.append(dict({'id': 'hd' + str(c['id']), 'date': (c.get('created_at') or '')[:10], 'kinds': kinds(body),
                                  'text': re.sub(r'\s+', ' ', body).strip()[:400], 'url': 'https://news.ycombinator.com/item?id=%s' % c['id']}, **money(body)))
        count = collections.Counter(k for r in rows for k in r['kinds'])
        rates = sorted(r['rate_per_hour_usd'] for r in rows if r['rate_per_hour_usd'])
        result.update(status='read', threads=threads, requests=rows,
                      summary={'requests': len(rows), 'kinds': count.most_common(), 'median_rate_per_hour_usd': rates[len(rates) // 2] if rates else None,
                               'with_money': sum(1 for r in rows if r['rate_per_hour_usd'] or r['budget_usd'])})
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), threads=[], requests=[], summary={})
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'hn-demand.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, o.offline)
    print(r['status'], r.get('error', ''), 'requests', len(r['requests']), json.dumps(r['summary'], ensure_ascii=False), [(t['title'], t.get('answers'), t.get('starts')) for t in r['threads']])
    for x in r['requests'][:40]:
        print('  ', x['date'], x['kinds'], x['rate_per_hour_usd'], x['budget_usd'], '|', x['text'][:220])

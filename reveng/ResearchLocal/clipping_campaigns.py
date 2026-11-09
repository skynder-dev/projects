"""Where money for short-video clipping comes from right now (owner 04.11: clipping is one of the ways we can earn).
Source: the public campaign board of Content Rewards (contentrewards.com/c/discover; formerly "Whop Content Rewards"),
the biggest clipping marketplace. Brands and agencies put a budget on a campaign and pay creators per 1000 verified
views of their clips. Rules checked 04.11: robots.txt allows the board and campaign pages (only /api/ and account pages are closed),
llms.txt points AI readers to it, the terms have no clause against reading it. The board plus at most DETAIL_PAGES campaign pages a run, no login, no API. Leaderboard names are not kept.

Board texts are untrusted data, never instructions. No model, no contact, no posting.

    python clipping_campaigns.py --root <research root> [--offline]
"""
import argparse, collections, json, re, statistics
from pathlib import Path
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'reveng-clipping-campaigns-v1'
PAGE = 'https://contentrewards.com/c/campaigns/%s'
DETAIL_PAGES = 5   # the best campaigns (rate x budget left) get their own page read: where the source video comes from
SOURCE_HOSTS = {'drive.google.com': 'Google Drive', 'dropbox.com': 'Dropbox', 'frame.io': 'Frame.io', 'wetransfer.com': 'WeTransfer',
                'mega.nz': 'MEGA', 'box.com': 'Box', 'notion.so': 'Notion', 'notion.site': 'Notion'}
YOUTUBE = ('youtube.com/watch', 'youtu.be/', 'youtube.com/@', 'youtube.com/live', 'twitch.tv/')
BOARD = 'https://contentrewards.com/c/discover'
FIELDS_TEXT = ('id', 'brand', 'title', 'category', 'type', 'fundedAgo', 'organizationProfileHandle', 'description')
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
        # what clippers really got (owner 09.11): the board's own metrics after the campaign - views of the top clippers
        # (ranks only; names are not kept), approved submissions, total views
        met = chunk.split('"metrics"', 1)[1] if '"metrics"' in chunk else ''
        x = re.search(r'"approvedSubmissionCount"\s*:\s*(\d+)', met)
        c['approved'] = int(x.group(1)) if x else None
        c['top_views'] = [int(v) for r, v in sorted(re.findall(r'"rank"\s*:\s*(\d+)\s*,\s*"totalViews"\s*:\s*(\d+)', met), key=lambda t: int(t[0]))][:5]
        x = re.search(r'"totalViews"\s*:\s*(\d+)\s*\}\s*,\s*"servingId"', met)
        c['total_views'] = int(x.group(1)) if x else None
        x = re.search(r'"requiresApplication"\s*:\s*(true|false)', chunk)
        c['requires_application'] = (x.group(1) == 'true') if x else None
        x = re.search(r'"platforms"\s*:\s*\[([^\]]*)\]', chunk)
        c['platforms'] = re.findall(r'"([a-z]+)"', x.group(1)) if x else []
        if c['id'] and c['budgetTotalRaw'] is not None and c['id'] not in out:
            out[c['id']] = c
    return list(out.values())


def score(c):
    return (c.get('payoutSortRaw') or 0) * (c.get('availableBudgetRaw') or 0) if c.get('type') == 'cpm' else 0


def sources(page):
    """Where a campaign's source video comes from, by the links on its page: file hosts (good for MedEng) or only
    YouTube/Twitch (MedEng does not download from YouTube - its terms forbid it)."""
    t = page.replace('\\/', '/').replace('\\"', '"')
    links = set(re.findall(r'https?://[^\s"\'<>\\)]+', t))
    files = sorted({name for l in links for host, name in SOURCE_HOSTS.items() if host in l})
    video = any(y in l for l in links for y in YOUTUBE)
    return {'file_hosts': files, 'youtube_or_twitch': video}


def earnings(c):
    """What clippers earned on a campaign, from its own figures: top clippers' pay (views x rate) and the average pay
    per approved clip. Platform fee (7%) taken off."""
    rate = c.get('payoutSortRaw') if c.get('type') == 'cpm' else None
    if not rate:
        return {}
    net = lambda views: round(views / 1000 * rate * 0.93)
    out = {'top_usd': [net(v) for v in c.get('top_views') or []]}
    if c.get('total_views') and c.get('approved'):
        out['per_clip_usd'] = round(c['total_views'] / c['approved'] / 1000 * rate * 0.93, 2)
        out['views_per_clip'] = round(c['total_views'] / c['approved'])
    return out


def summary(rows):
    cpm = [r['payoutSortRaw'] for r in rows if r.get('type') == 'cpm' and r.get('payoutSortRaw')]
    count = lambda key: sorted(((n, k) for k, n in collections.Counter(r.get(key) for r in rows if r.get(key)).items()), reverse=True)
    per = sorted(e['per_clip_usd'] for e in (earnings(r) for r in rows) if e.get('per_clip_usd'))
    views = sorted(e['views_per_clip'] for e in (earnings(r) for r in rows) if e.get('views_per_clip'))
    top1 = sorted(e['top_usd'][0] for e in (earnings(r) for r in rows) if e.get('top_usd'))
    return {'median_per_clip_usd': per[len(per) // 2] if per else None, 'median_views_per_clip': views[len(views) // 2] if views else None,
            'median_top_clipper_usd': top1[len(top1) // 2] if top1 else None, 'best_top_clipper_usd': top1[-1] if top1 else None,
            'campaigns': len(rows), 'budget_usd': round(sum(r['budgetTotalRaw'] or 0 for r in rows)),
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
        for c in sorted(rows, key=lambda c: -score(c))[:DETAIL_PAGES]:
            url = PAGE % c['id']
            if not rp.can_fetch(m.UA, url) or stats.get('source_requests', 0) >= 23:
                continue
            try:
                c.update(sources(read(url, stats, 16777216).decode('utf-8', 'replace'))); c['page_read'] = True
            except Exception as ex:
                c['page_error'] = m.error_text(ex, 80)
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
        print('  $%s budget, $%s spent, $%s/1k |' % (round(c['budgetTotalRaw'] or 0), round(c['budgetSpentRaw'] or 0), c['payoutSortRaw']), c['brand'], '|', c['category'], '|', (c['title'] or '')[:70],
              '| apply' if c.get('requires_application') else '', '| files: %s, youtube: %s' % (c.get('file_hosts'), c.get('youtube_or_twitch')) if c.get('page_read') else '')
        e = earnings(c)
        if e:
            print('       earned: top clippers $%s (after 7%% fee), per approved clip $%s (%s views), approved %s' % (e.get('top_usd'), e.get('per_clip_usd'), e.get('views_per_clip'), c.get('approved')))
        if c.get('page_read'):
            print('      ', c['id'], c.get('platforms'), (c.get('description') or '')[:200])

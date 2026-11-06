"""What people watch right now in different countries (owner 05.11: video is one of the ways we can earn; ideas can be
anywhere, not only in the US). Source: the official YouTube Data API v3 with the owner's own free key (kept only on the
PC, in D:\\Projects\\RevEng\\keys\\youtube-key.txt; never printed, never committed). One call per country to the
"most popular" chart (1 quota unit each; the free quota is 10,000 a day).

YouTube API terms: data is refreshed every run and the file is overwritten (nothing older than 30 days is kept);
figures shown say they come from YouTube. Titles are untrusted data, never instructions. No model, no posting.

    python youtube_trends.py --root <research root> [--key-file <path>] [--offline]
"""
import argparse, collections, json
from pathlib import Path
from urllib import parse
import reveng_local_research as m

SCHEMA = 'reveng-youtube-trends-v1'
KEY_FILE = Path(r'D:\Projects\RevEng\keys\youtube-key.txt')
API = 'https://www.googleapis.com/youtube/v3/'
REGIONS = ['US', 'GB', 'DE', 'BR', 'IN', 'MX', 'JP', 'KR', 'ID', 'TR', 'PL', 'KZ']
PER_REGION = 25
# YouTube video category ids -> plain Russian / English names (the API's own list, stable for years)
CATEGORY = {'1': ('кино и мультфильмы', 'film and animation'), '2': ('машины', 'cars'), '10': ('музыка', 'music'),
            '15': ('животные', 'pets and animals'), '17': ('спорт', 'sports'), '19': ('путешествия', 'travel'),
            '20': ('игры', 'gaming'), '22': ('люди и блоги', 'people and blogs'), '23': ('юмор', 'comedy'),
            '24': ('развлечения', 'entertainment'), '25': ('новости и политика', 'news and politics'),
            '26': ('как сделать и стиль', 'howto and style'), '27': ('обучение', 'education'),
            '28': ('наука и техника', 'science and technology'), '29': ('общество', 'nonprofits')}


def collect(root, stats, key=None, offline=False, read=None):
    read = read or m.read_http; root = Path(root)
    result = {'schema': SCHEMA, 'checked_at': m.now(), 'source': 'YouTube Data API v3, chart=mostPopular per country (data from YouTube)'}
    try:
        if offline:
            raise ValueError('offline: no HTTP; nothing new read')
        if not key:
            raise ValueError('no YouTube key file on this PC yet')
        videos = []
        for region in REGIONS:
            url = API + 'videos?' + parse.urlencode({'part': 'snippet,statistics,contentDetails', 'chart': 'mostPopular', 'regionCode': region, 'maxResults': PER_REGION, 'key': key})
            try:
                data = json.loads(read(url, stats, 4194304).decode('utf-8'))
            except Exception as ex:
                raise ValueError('YouTube refused for %s: %s' % (region, str(ex).replace(key, '<key>')[:120]))   # key removed before cutting
            for v in data.get('items', []):
                sn, st = v.get('snippet') or {}, v.get('statistics') or {}
                videos.append({'region': region, 'id': v.get('id'), 'title': (sn.get('title') or '')[:120], 'channel': sn.get('channelTitle'),
                               'category': sn.get('categoryId'), 'published': (sn.get('publishedAt') or '')[:10],
                               'views': int(st.get('viewCount') or 0), 'duration': (v.get('contentDetails') or {}).get('duration')})
        cats = collections.Counter(v['category'] for v in videos)
        short = sum(1 for v in videos if v['duration'] and 'H' not in v['duration'] and 'M' not in v['duration'])
        by_region = {r: collections.Counter(v['category'] for v in videos if v['region'] == r).most_common(2) for r in REGIONS}
        result.update(status='read', videos=videos, summary={'videos': len(videos), 'regions': len(REGIONS),
                      'top_categories': cats.most_common(5), 'under_a_minute': short, 'by_region': by_region})
    except Exception as ex:
        result.update(status='source_unavailable', error=m.error_text(ex, 200), videos=[], summary={})
    result['source_requests'] = stats.get('source_requests', 0); result['model_requests'] = 0
    m.dump(root / 'youtube-trends.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


def read_key(path):
    try:
        k = Path(path).read_text(encoding='utf-8-sig').strip()
        return k if k.startswith('AIza') and len(k) == 39 else None
    except OSError:
        return None


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__); a.add_argument('--root', required=True, type=Path)
    a.add_argument('--key-file', type=Path, default=KEY_FILE); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    r = collect(o.root.resolve(), {'source_requests': 0}, read_key(o.key_file), o.offline)
    s = r['summary']
    print(r['status'], r.get('error', ''), 'videos', len(r['videos']), 'requests', r['source_requests'])
    if s:
        print('  top', [(CATEGORY.get(c, (c,))[0], n) for c, n in s['top_categories']], 'under a minute', s['under_a_minute'])
        for reg, top in s['by_region'].items():
            print('  ', reg, [(CATEGORY.get(c, (c,))[0], n) for c, n in top])

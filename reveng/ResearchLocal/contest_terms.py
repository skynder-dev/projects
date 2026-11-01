"""Open contests as opportunities (owner's idea, 31.10.2026): the organizer's own page, read with the same bounded
transport, robots check, HTML identity check and sealed cache as direct_alternatives; terms quoted, never inferred.

A contest is offer terms, not buyer pain: rows are kept out of PROBLEM_REPORT_KINDS, out of candidates and out of the
global ranking (automatic_admission=False). Prize and fee are what the page states (proposed_unverified), the deadline
is the date the page declares (not observed_at). No model, no ranking, no payout or eligibility conclusion.

Seeds come from the assistant's manual web search of 31.10.2026, not from RevEng discovery; each one is still read
from the organizer's page. Offline: no HTTP fallback.

    python contest_terms.py --root <research root> [--offline]
"""
import argparse, asyncio, json, re, time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib import robotparser
import reveng_local_research as m

SCHEMA = 'contest-terms-v1'
RULES_VERSION = 'contest-terms-rules-v1'
KIND = 'official_contest_terms'
CONTESTS = {
    'billion_ai_film_2027': {'organizer': '1 Billion Followers Summit', 'title': 'AI Film Award 2027',
                             'url': 'https://www.1billionsummit.com/ai-award-2027',
                             'seed': 'assistant manual web search 2026-10-31'},
    'waiff_cannes_2027': {'organizer': 'World AI Film Festival (WAIFF)', 'title': 'WAIFF Cannes 2027 (FilmFreeway listing)',
                          'url': 'https://filmfreeway.com/WAIFF', 'seed': 'assistant manual web search 2026-10-31'},
    'chroma_awards_s2': {'organizer': 'ElevenLabs Chroma Awards', 'title': 'Chroma Awards, season 2 (announcement)',
                         'url': 'https://elevenlabs.io/blog/chroma-awards-season-two-announcement', 'seed': 'assistant manual web search 2026-10-31'},
}
MAX_QUOTE_WORDS = 14
MONTHS = {k: i + 1 for i, k in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
MON = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?'
DATE = r'(?:' + MON + r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+' + MON + r',?\s+\d{4}|\d{4}-\d{2}-\d{2})'
MONEY = r'(?:US\$|USD\s?|\$|€|EUR\s?|£|GBP\s?|RMB\s?|¥)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|m\b|k\b|thousand))?'
RULES = {
    'deadline': r'(?:deadline|submissions?\s+(?:close|closes|are\s+due|due|end|ends)|submit\s+(?:by|before)|entries\s+(?:close|due)|open\s+until)[^.;]{0,60}?' + DATE,
    'prize': r'(?:(?:grand\s+)?prize|award|winner\w*\s+(?:will\s+)?(?:receive|receives|gets?|wins?))[^.;]{0,60}?' + MONEY + r'|' + MONEY + r'[^.;]{0,30}?(?:prize|award)',
    'fee': r'(?:entry|submission|application)\s+fee[^.;]{0,40}?(?:free|none|no\s+fee|' + MONEY + r')|free\s+(?:to\s+enter|entry|of\s+charge|submission)|no\s+(?:entry|submission)\s+fee',
    'length': r'\b\d{1,3}\s*(?:to|-|–|and)\s*\d{1,3}\s*minutes?\b|(?:no\s+(?:longer|more)\s+than|maximum(?:\s+of)?|up\s+to|under|at\s+most)\s+\d{1,3}\s*minutes?\b',
    # the tool name must really start with a capital letter even though the rest of the rule ignores case
    'tools': r'(?:at\s+least\s+\d{1,3}\s*%|must\s+be|required\s+to\s+be|primary)[^.;]{0,50}?(?:generated|created|made|produced)\s+(?:using|with|in|by)\s+(?-i:[A-Z][\w.\-]*(?:\s+[A-Z0-9][\w.\-]*){0,3})',
    'eligibility': r'(?:at\s+least|aged?)\s+\d{2}\s+years?(?:\s+old)?|open\s+to\s+[^.;]{0,50}?(?:worldwide|globally|all\s+countries|any\s+country|residents\s+of\s+[A-Z][\w ]{0,25})',
    'exclusivity': r'non-exclusive\s+licen[cs]e|exclusive\s+(?:rights|licen[cs]e|premiere)|world\s+premiere|must\s+not\s+have\s+been\s+(?:previously\s+)?(?:published|released|screened)',
    'format': r'\b(?:16:9|9:16|1080p|2160p|4K|MP4|MOV)\b(?:[^.;]{0,30}?\b(?:16:9|9:16|1080p|2160p|4K|MP4|MOV)\b)*',
}


def parse_date(text):
    """A declared date as ISO, or None (only explicit day + month + year)."""
    t = text.lower().replace(',', ' ')
    mm = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if mm:
        y, mo, d = map(int, mm.groups())
    else:
        mm = re.search(r'(' + MON + r')\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})', t) or re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(' + MON + r')\s+(\d{4})', t)
        if not mm:
            return None
        a, b, y = mm.groups()
        mon, d = (a, b) if not a[0].isdigit() else (b, a)
        mo, d, y = MONTHS.get(mon[:3]), int(d), int(y)
        if not mo:
            return None
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse_money(text):
    mm = re.search(r'(US\$|USD|\$|€|EUR|£|GBP|RMB|¥)\s?(\d[\d,]*(?:\.\d+)?)\s?(million|m\b|k\b|thousand)?', text, re.I)
    if not mm:
        return None
    cur = {'US$': 'USD', '$': 'USD', 'USD': 'USD', '€': 'EUR', 'EUR': 'EUR', '£': 'GBP', 'GBP': 'GBP', 'RMB': 'CNY', '¥': 'CNY'}[mm.group(1).upper() if mm.group(1).isalpha() else mm.group(1)]
    amount = float(mm.group(2).replace(',', ''))
    scale = (mm.group(3) or '').lower()
    amount *= 1_000_000 if scale in ('million', 'm') else 1_000 if scale in ('k', 'thousand') else 1
    return {'amount': amount, 'currency': cur, 'status': 'proposed_unverified'}


def parse(key, text, stamp, response_sha, today=None):
    spec = CONTESTS[key]
    text = ' '.join(text.split())
    facts = []

    def fact(kind):
        mm = re.search(RULES[kind], text, re.I)
        if not mm:
            return None
        quote = ' '.join(mm.group(0).split()[:MAX_QUOTE_WORDS])
        facts.append({'id': 'K' + str(len(facts) + 1), 'kind': kind, 'quote': quote})
        return quote

    q = {k: fact(k) for k in RULES}
    deadline = parse_date(q['deadline']) if q['deadline'] else None
    today = today or datetime.now(timezone.utc).date().isoformat()
    lengths = [int(x) for x in re.findall(r'\d{1,3}', q['length'] or '')]
    tools = re.search(r'(?i:using|with|in|by)\s+([A-Z][\w.\-]*(?:\s+[A-Z0-9][\w.\-]*){0,3})', q['tools'] or '')
    fee = None
    if q['fee']:
        fee = {'amount': 0.0, 'currency': None, 'status': 'proposed_unverified'} if re.search(r'free|none|no\s+(?:entry\s+|submission\s+)?fee', q['fee'], re.I) else parse_money(q['fee'])
    found = [k for k in RULES if q[k]]
    return {
        'schema': SCHEMA, 'rules_version': RULES_VERSION, 'kind': KIND, 'key': key, 'organizer': spec['organizer'],
        'title': spec['title'], 'source_url': spec['url'], 'seed': spec['seed'], 'observed_at': stamp,
        'response_sha256': response_sha, 'expires': time.time() + 43200, 'facts': facts,
        'declared_deadline': deadline,
        'deadline_status': 'unknown' if not deadline else 'open' if deadline >= today else 'closed',
        'prize': parse_money(q['prize']) if q['prize'] else None,
        'fee': fee,
        'length_minutes': [min(lengths), max(lengths)] if lengths else None,
        'required_tool': tools.group(1) if tools else None,
        'classification': 'contest_terms_found' if (q['deadline'] and q['prize']) else 'partial_terms' if found else 'not_found_in_checked_source',
        'unproven': [k for k in RULES if not q[k]],
        'automatic_admission': False, 'global_ranking': 'excluded',
        'interpretation': 'Terms as quoted from the organizer page; not a guarantee of eligibility, judging, payment or fit',
    }


def compatible(records):
    """Which open contests one finished work could enter: overlapping length ranges and no conflicting required tool.
    Exclusivity/premiere quotes are carried as a warning, never resolved automatically."""
    open_rows = [r for r in records if r.get('deadline_status') == 'open' and r.get('length_minutes')]
    out = []
    for i, a in enumerate(open_rows):
        for b in open_rows[i + 1:]:
            lo, hi = max(a['length_minutes'][0], b['length_minutes'][0]), min(a['length_minutes'][1], b['length_minutes'][1])
            tools = {t for t in (a.get('required_tool'), b.get('required_tool')) if t}
            if lo <= hi and len(tools) <= 1:
                warn = [r['key'] for r in (a, b) if any(f['kind'] == 'exclusivity' for f in r['facts'])]
                out.append({'contests': [a['key'], b['key']], 'shared_length_minutes': [lo, hi], 'required_tool': next(iter(tools), None),
                            'check_exclusivity_terms_of': warn})
    return out


def body_text(raw, url):
    import direct_alternatives
    return direct_alternatives.body_text(raw, url)


async def collect(root, run, stats, offline=False):
    cache = root / 'contest-cache'; cache.mkdir(exist_ok=True); out = []; robots = {}
    for key, spec in CONTESTS.items():
        m.cancelled(run)
        path = cache / (m.sha((SCHEMA + '|' + RULES_VERSION + '|' + spec['url']).encode()) + '.json')
        try:
            if path.exists():
                saved = json.loads(path.read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256', None)
                if claim == m.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False).encode()) and saved.get('expires', 0) > time.time():
                    out.append(saved); stats['source_cache_hits'] = stats.get('source_cache_hits', 0) + 1; continue
            if offline:
                raise ValueError('No fresh verified contest cache; no HTTP fallback')
            p = urlsplit(spec['url']); host = p.netloc
            if host not in robots:
                raw = await asyncio.to_thread(m.read_http, p.scheme + '://' + host + '/robots.txt', stats, 65536)
                rp = robotparser.RobotFileParser(); rp.parse(raw.decode('utf-8', 'replace').splitlines()); robots[host] = rp
            if not robots[host].can_fetch(m.UA, spec['url']):
                raise ValueError('robots.txt denied')
            raw = await asyncio.to_thread(m.read_http, spec['url'], stats)
            archive = root / 'contest-payloads'; archive.mkdir(exist_ok=True); (archive / (m.sha(raw) + '.raw')).write_bytes(raw)
            record = parse(key, body_text(raw, spec['url']), m.now(), m.sha(raw))
            m.dump(path, dict(record, integrity_sha256=m.sha(json.dumps(record, sort_keys=True, ensure_ascii=False).encode())))
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            record = {'schema': SCHEMA, 'rules_version': RULES_VERSION, 'kind': KIND, 'key': key, 'organizer': spec['organizer'],
                      'title': spec['title'], 'source_url': spec['url'], 'seed': spec['seed'], 'observed_at': m.now(),
                      'expires': time.time() + 900, 'classification': 'source_unavailable', 'error': m.error_text(ex, 180),
                      'facts': [], 'declared_deadline': None, 'deadline_status': 'unknown', 'automatic_admission': False,
                      'global_ranking': 'excluded', 'interpretation': 'Source could not be checked; no conclusion about this contest'}
        out.append(record)
    result = {'schema': SCHEMA, 'collected_at': m.now(), 'records': out, 'compatible': compatible(out),
              'source_requests': stats.get('source_requests', 0), 'model_requests': 0}
    m.dump(root / 'contest-terms.json', dict(result, integrity_sha256=m.sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())))
    return result


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--root', required=True, type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    root = o.root.resolve(); run = root / 'runs' / ('contests-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')); run.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(collect(root, run, {'source_requests': 0}, offline=o.offline))
    for r in result['records']:
        print(r['key'], r['classification'], r.get('declared_deadline'), (r.get('prize') or {}).get('amount'), r.get('error', ''))


if __name__ == '__main__':
    main()

"""Open contests as opportunities (owner's idea, 31.10.2026): the organizer's own page, read with the same bounded
transport, robots check, HTML identity check and sealed cache as direct_alternatives; terms quoted, never inferred.

A contest is offer terms, not buyer pain: rows are kept out of PROBLEM_REPORT_KINDS, out of candidates and out of the
global ranking (automatic_admission=False). Prize and fee are what the page states (proposed_unverified), the deadline
is the date the page declares (not observed_at). No model, no ranking, no payout or eligibility conclusion.

Two kinds of entry. Seeds (CONTESTS) come from the assistant's manual web search of 31.10.2026, not from RevEng
discovery. Leads come from an aggregator listing (AGGREGATORS, 01.11.2026), which is only a secondary list: the
listing's outgoing links are read, and each lead is still read from the organizer's own page; only what that page
states becomes terms. What the listing says next to a link (a date, an amount) is kept as 'listed' and never as terms.
At most MAX_LEADS leads are read per run, inside the transport's request budget; the rest are listed as not checked.

HTML is read with the standard library only (no bs4): visible text outside script/style/nav/footer, the <main>
element alone when the page has one. Offline: no HTTP fallback. Alongside the sealed contest-terms.json the collector
writes contest-terms-view.json (payload_json + payload_sha256) for the window.

    python contest_terms.py --root <research root> [--run <run folder>] [--offline]
"""
import argparse, asyncio, json, re, time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib import robotparser
import reveng_local_research as m
import html_document_identity as hid

SCHEMA = 'contest-terms-v2'
VIEW_SCHEMA = 'contest-terms-view-v1'
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
AGGREGATORS = {
    'aifilmcontests': {'title': 'AI Film Contests (listing)', 'url': 'https://aifilmcontests.com/',
                       'seed': 'assistant manual web search 2026-11-01', 'role': 'secondary_lead_list'},
}
# links on a listing that are never contest organizers: the listing's own site, social profiles, credits
IGNORE_HOSTS = {'linkedin.com', 'x.com', 'twitter.com', 'facebook.com', 'instagram.com', 'youtube.com', 'youtu.be', 'tiktok.com',
                'discord.gg', 'discord.com', 't.me', 'threads.net', 'reddit.com', 'medium.com', 'github.com', 'ruminatex.com',
                'google.com', 'apple.com', 'wikipedia.org', 'patreon.com', 'buymeacoffee.com', 'ko-fi.com', 'substack.com'}
MAX_LEADS = 8
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


def parse(key, text, stamp, response_sha, today=None, spec=None):
    spec = spec or CONTESTS[key]
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
        'title': spec['title'], 'source_url': spec['url'], 'seed': spec['seed'], 'origin': spec.get('origin', 'manual_seed'),
        'observed_at': stamp, 'response_sha256': response_sha, 'expires': time.time() + 43200, 'facts': facts,
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


class Page(HTMLParser):
    """Visible text and links of one HTML document, standard library only. Text outside script/style/nav/footer; the
    <main> element alone when the page has one. Each link keeps its own text and where it sits in the page text, so the
    listing's words next to it can be quoted: the enclosing list item/article/table row when there is one, else a few
    text pieces either side."""
    SKIP = {'script', 'style', 'nav', 'footer', 'noscript', 'template'}
    ITEM = {'li', 'article', 'tr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0; self.main = 0; self.parts = []; self.main_parts = []; self.links = []; self.href = None; self.anchor = []
        self.at = 0; self.items = []; self.open = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == 'main':
            self.main += 1
        elif tag in self.ITEM:
            self.items.append(len(self.parts))
        elif tag == 'a' and not self.skip:
            self.href = dict(attrs).get('href') or ''; self.anchor = []; self.at = len(self.parts)

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == 'main':
            self.main = max(0, self.main - 1)
        elif tag in self.ITEM and self.items:
            begin = self.items.pop()
            for link in self.open:
                if link['item'] == begin and link['end'] is None:
                    link['end'] = len(self.parts)
        elif tag == 'a' and self.href is not None:
            link = {'href': self.href, 'text': ' '.join(' '.join(self.anchor).split()), 'at': self.at,
                    'item': self.items[-1] if self.items else None, 'end': None}
            self.links.append(link); self.open.append(link); self.href = None

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(data)
        if self.main:
            self.main_parts.append(data)
        if self.href is not None:
            self.anchor.append(data)

    def text(self):
        return ' '.join(' '.join(self.main_parts or self.parts).split())

    def around(self, link, width=6):
        if link['item'] is not None and link['end'] is not None:
            return ' '.join(' '.join(self.parts[link['item']:link['end']]).split())
        return ' '.join(' '.join(self.parts[max(0, link['at'] - width):link['at'] + width]).split())


def identity(raw, url):
    """The page text and how its identity was established. A declared canonical/og:url must match (the shared HTML
    identity rule); many organizer pages declare none, and then the identity is the exact requested HTTPS URL, which the
    app's transport fetched without following any redirect. Challenge/access-denied pages are refused either way."""
    text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    meta = hid.Metadata(); meta.feed(text)
    if meta.urls or hid.denied(meta):
        hid.validate(url, text)
        return text, 'declared_canonical_matches'
    return text, 'exact_url_no_redirect_no_canonical_declared'


def body_text(raw, url):
    text, how = identity(raw, url)
    page = Page(); page.feed(text)
    return page.text(), how


def host_of(url):
    host = (urlsplit(url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def leads(raw, url):
    """Outgoing HTTPS links of a listing page as leads: the link text as the quoted title, the listing's own date and
    amount next to it as 'listed' hints (never terms). The listing's own pages, fragments and social/credit links are
    skipped; one lead per organizer URL, in page order."""
    text, how = identity(raw, url)
    page = Page(); page.feed(text); own = host_of(url); out = []; seen = set()
    for link in page.links:
        p = urlsplit(link['href'].strip())
        if p.scheme != 'https' or not p.hostname or p.username is not None or p.password is not None:
            continue
        host = host_of(link['href'])
        if host == own or any(host == h or host.endswith('.' + h) for h in IGNORE_HOSTS):
            continue
        target = urlunsplit(('https', p.hostname.lower(), p.path or '/', p.query, ''))
        if target in seen:
            continue
        seen.add(target); near = page.around(link)
        listed_date = re.search(DATE, near, re.I); listed_money = re.search(MONEY, near, re.I)
        out.append({'url': target, 'organizer_host': host, 'text': ' '.join(link['text'].split()[:MAX_QUOTE_WORDS]),
                    'listed_deadline': parse_date(listed_date.group(0)) if listed_date else None,
                    'listed_prize': parse_money(listed_money.group(0)) if listed_money else None,
                    'listed_status': 'listed_by_aggregator_unverified'})
    return out, how


def lead_key(url):
    return 'lead-' + m.sha(url.encode('utf-8'))[:12]


def choose(found, today, seeded):
    """Which leads to read this run: not already a seed, at most MAX_LEADS. Order: leads whose listing shows a full date
    that has not passed, soonest first; then leads without a date, in page order; then leads whose listed date has
    passed (the listing's date is a hint, not a term). Every lead gets a status the window can show."""
    fresh = [l for l in found if l['url'] not in seeded]
    ahead = sorted([l for l in fresh if l['listed_deadline'] and l['listed_deadline'] >= today], key=lambda l: l['listed_deadline'])
    undated = [l for l in fresh if not l['listed_deadline']]
    passed = sorted([l for l in fresh if l['listed_deadline'] and l['listed_deadline'] < today], key=lambda l: l['listed_deadline'], reverse=True)
    chosen = (ahead + undated + passed)[:MAX_LEADS]
    for lead in found:
        if lead['url'] in seeded:
            lead['status'] = 'already_seeded'
        elif any(l is lead for l in chosen):
            lead['status'] = 'checked_on_organizer_page'; lead['record_key'] = lead_key(lead['url'])
        else:
            lead['status'] = 'not_checked_this_run_lead_limit' + ('_listed_date_passed' if lead['listed_deadline'] and lead['listed_deadline'] < today else '')
    return chosen


def sealed(path):
    """A sealed cache entry when its hash still matches and it has not expired, else None."""
    if not path.exists():
        return None
    saved = json.loads(path.read_text(encoding='utf-8')); claim = saved.pop('integrity_sha256', None)
    if claim == m.sha(json.dumps(saved, sort_keys=True, ensure_ascii=False).encode()) and saved.get('expires', 0) > time.time():
        return saved
    return None


def seal(path, record):
    m.dump(path, dict(record, integrity_sha256=m.sha(json.dumps(record, sort_keys=True, ensure_ascii=False).encode())))


class Transport:
    """One run's bounded page reads: robots.txt once per host, no redirects, hosts that refused (HTTP 403/429) are not
    asked again in the same run, every raw response archived."""

    def __init__(self, root, stats, offline):
        self.root = root; self.stats = stats; self.offline = offline; self.robots = {}; self.refused = {}

    async def read(self, url):
        if self.offline:
            raise ValueError('No fresh verified contest cache; no HTTP fallback')
        p = urlsplit(url); host = p.netloc
        if host in self.refused:
            raise ValueError('host refused earlier in this run (' + self.refused[host] + '); not asked again')
        try:
            if host not in self.robots:
                raw = await asyncio.to_thread(m.read_http, p.scheme + '://' + host + '/robots.txt', self.stats, 65536)
                rp = robotparser.RobotFileParser(); rp.parse(raw.decode('utf-8', 'replace').splitlines()); self.robots[host] = rp
            if not self.robots[host].can_fetch(m.UA, url):
                raise ValueError('robots.txt denied')
            raw = await asyncio.to_thread(m.read_http, url, self.stats)
        except Exception as ex:
            if re.search(r'HTTP Error (?:403|429)', str(ex)):
                self.refused[host] = m.error_text(ex, 60)
            raise
        archive = self.root / 'contest-payloads'; archive.mkdir(exist_ok=True); (archive / (m.sha(raw) + '.raw')).write_bytes(raw)
        return raw


def unavailable(key, spec, ex, kind=KIND):
    return {'schema': SCHEMA, 'rules_version': RULES_VERSION, 'kind': kind, 'key': key, 'organizer': spec.get('organizer', ''),
            'title': spec['title'], 'source_url': spec['url'], 'seed': spec['seed'], 'origin': spec.get('origin', 'manual_seed'),
            'observed_at': m.now(), 'expires': time.time() + 900, 'classification': 'source_unavailable', 'error': m.error_text(ex, 180),
            'facts': [], 'declared_deadline': None, 'deadline_status': 'unknown', 'automatic_admission': False,
            'global_ranking': 'excluded', 'interpretation': 'Source could not be checked; no conclusion about this contest'}


async def terms(cache, transport, key, spec, run):
    """One contest record: the sealed cache when fresh, else the organizer page read now, else source_unavailable."""
    m.cancelled(run)
    path = cache / (m.sha((SCHEMA + '|' + RULES_VERSION + '|' + spec['url']).encode()) + '.json')
    try:
        saved = sealed(path)
        if saved:
            transport.stats['source_cache_hits'] = transport.stats.get('source_cache_hits', 0) + 1; return saved
        raw = await transport.read(spec['url'])
        text, how = body_text(raw, spec['url'])
        record = parse(key, text, m.now(), m.sha(raw), spec=spec); record['source_identity'] = how
        seal(path, record); return record
    except asyncio.CancelledError:
        raise
    except Exception as ex:
        return unavailable(key, spec, ex)


async def listing(cache, transport, key, spec, run):
    """One aggregator listing: its leads (sealed cache when fresh), else source_unavailable with no leads."""
    m.cancelled(run)
    path = cache / (m.sha((SCHEMA + '|aggregator|' + spec['url']).encode()) + '.json')
    try:
        saved = sealed(path)
        if saved:
            transport.stats['source_cache_hits'] = transport.stats.get('source_cache_hits', 0) + 1; return saved
        raw = await transport.read(spec['url'])
        found, how = leads(raw, spec['url'])
        record = {'schema': SCHEMA, 'kind': 'aggregator_listing', 'key': key, 'title': spec['title'], 'source_url': spec['url'],
                  'seed': spec['seed'], 'role': spec['role'], 'observed_at': m.now(), 'response_sha256': m.sha(raw),
                  'expires': time.time() + 43200, 'source_identity': how, 'classification': 'listing_read' if found else 'no_outgoing_links_found',
                  'leads': found, 'interpretation': 'Secondary list only; nothing here is a term until the organizer page states it'}
        seal(path, record); return record
    except asyncio.CancelledError:
        raise
    except Exception as ex:
        return dict(unavailable(key, spec, ex, kind='aggregator_listing'), role=spec['role'], leads=[])


async def collect(root, run, stats, offline=False, today=None):
    cache = root / 'contest-cache'; cache.mkdir(exist_ok=True); transport = Transport(root, stats, offline)
    today = today or datetime.now(timezone.utc).date().isoformat(); out = []
    for key, spec in CONTESTS.items():
        out.append(await terms(cache, transport, key, spec, run))
    listings = {}; seeded = {spec['url'] for spec in CONTESTS.values()}
    for key, spec in AGGREGATORS.items():
        listings[key] = await listing(cache, transport, key, spec, run)
    for key, item in listings.items():
        for lead in choose(item['leads'], today, seeded):
            spec = {'organizer': lead['organizer_host'], 'title': lead['text'] or lead['url'], 'url': lead['url'],
                    'seed': 'lead from ' + item['source_url'] + ' (secondary list)', 'origin': 'aggregator_lead'}
            record = await terms(cache, transport, lead['record_key'], spec, run)
            record['lead'] = {'aggregator': key, 'listed_deadline': lead['listed_deadline'], 'listed_prize': lead['listed_prize'], 'listed_text': lead['text']}
            out.append(record)
    result = {'schema': SCHEMA, 'collected_at': m.now(), 'today': today, 'records': out, 'compatible': compatible(out), 'listings': listings,
              'lead_limit_per_run': MAX_LEADS, 'source_requests': stats.get('source_requests', 0), 'model_requests': 0}
    seal(root / 'contest-terms.json', result)
    payload = json.dumps(result, sort_keys=True, ensure_ascii=False)
    m.dump(root / 'contest-terms-view.json', {'schema': VIEW_SCHEMA, 'written_at': m.now(), 'payload_sha256': m.sha(payload.encode('utf-8')), 'payload_json': payload})
    return result


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--root', required=True, type=Path); a.add_argument('--run', type=Path); a.add_argument('--offline', action='store_true')
    o = a.parse_args()
    root = o.root.resolve(); run = (o.run or root / 'runs' / ('contests-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))).resolve()
    run.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(collect(root, run, {'source_requests': 0}, offline=o.offline))
    for r in result['records']:
        print(r['key'], r['origin'], r['classification'], r.get('declared_deadline'), (r.get('prize') or {}).get('amount'), r.get('error', ''))
    for key, item in result['listings'].items():
        rows = item.get('leads', [])
        print('listing', key, item['classification'], 'leads', len(rows), 'checked', sum(1 for l in rows if l.get('status') == 'checked_on_organizer_page'), item.get('error', ''))
        for l in rows:
            print('  ', l.get('status'), l['url'], '|', l['text'], '|', l.get('listed_deadline'))
    print('source_requests', result['source_requests'], 'model_requests', result['model_requests'])


if __name__ == '__main__':
    main()

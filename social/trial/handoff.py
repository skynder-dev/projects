"""Owner-liked Social cards -> shared/videos/<id>.json for MedEng (video) and Forge.
Built by the program from the phone card (Russian lines) and the trial.json it came from (facts with quote, locator,
SHA-256). Never invents facts: a concept's facts are the claims it cites; a card without its trial is reported, not made.

Usage: python -I handoff.py CARDS_JSON DECISIONS_JSON OUT_DIR TRIAL_JSON [TRIAL_JSON ...]
"""
import hashlib
import json
import sys
from pathlib import Path

RULES = ('Only these facts; keep every condition; no promises; on-screen source link; the host shows the official page, '
         'never poses as an expert. End with one question viewers answer in one word (their state, or a pick of two).')


def job_of(trial: dict) -> str:
    st = trial.get('stages', {})
    prop = st.get('proposal') or {}
    title = str((st.get('source') or {}).get('title') or '')
    rev = hashlib.sha256(json.dumps(prop, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
    return hashlib.sha256((title + rev).encode('utf-8')).hexdigest()[:10]


def verdicts(raw) -> dict:
    items = raw.get('decisions', raw) if isinstance(raw, dict) else raw
    out = {}
    if isinstance(items, dict):
        for k, v in items.items():
            out[k] = v.get('verdict') if isinstance(v, dict) else v
    else:
        for r in items:
            out[r.get('id')] = (r.get('decision') or {}).get('verdict') if isinstance(r.get('decision'), dict) else r.get('verdict')
    return {k: v for k, v in out.items() if str(k).startswith('so_')}


def line(card: dict, prefix: str) -> str:
    for x in card.get('lines', []):
        if x.startswith(prefix):
            return x[len(prefix):].strip()
    return ''


def claims_of(trial: dict) -> dict:
    st = trial['stages']
    rows = st.get('claims') or []
    rows = rows.get('claims', rows) if isinstance(rows, dict) else rows
    src = st.get('source') or {}
    out = {}
    for c in rows if isinstance(rows, list) else []:
        key = c.get('key') or c.get('id') or c.get('claim_key')
        if key:
            out[key] = {'key': key, 'quote': c.get('quote') or c.get('text') or c.get('value'),
                        'locator': c.get('locator'),
                        'sha256': c.get('sha256') or (c.get('source') or {}).get('sha256') or (c.get('source') or {}).get('excerpt_sha256') or src.get('sha256'),
                        'source_url': c.get('source_url') or (c.get('source') or {}).get('url') or src.get('url')}
    return out


def page_claims(paths):
    """Fallback (11.11.2026): idea files of some runs were overwritten; facts rebuilt from the same official page.
    Maps 'host/path' -> list of claims (whole page, the concept's own key list is lost)."""
    out = {}
    for p in paths:
        try:
            d = json.loads(Path(p).read_text(encoding='utf-8'))
        except Exception:  # noqa: BLE001
            continue
        rows = d.get('claims', d) if isinstance(d, dict) else d
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict) or 'quote' not in rows[0]:
            continue
        for c in rows:
            u = str(c.get('source_url') or (c.get('source') or {}).get('url') or '')
            key = u.split('://')[-1].removeprefix('www.').rstrip('/')
            if key:
                out.setdefault(key, []).append({'key': c.get('key'), 'quote': c.get('quote'), 'locator': c.get('locator'),
                    'sha256': (c.get('source') or {}).get('sha256') or (c.get('source') or {}).get('excerpt_sha256'),
                    'source_url': u})
    return out


def main(argv):
    cards_path, dec_path, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    pages = page_claims([a for a in argv[3:] if 'claims' in Path(a).name])  # concept_claims.json from 'socialreel source'
    argv = [a for a in argv if 'claims' not in Path(a).name]
    out.mkdir(parents=True, exist_ok=True)
    cards = {c['id']: c for c in json.loads(cards_path.read_text(encoding='utf-8'))['cards']}
    dec = verdicts(json.loads(dec_path.read_text(encoding='utf-8')))
    trials = {}
    for p in argv[3:]:
        try:
            t = json.loads(Path(p).read_text(encoding='utf-8'))
        except Exception:  # noqa: BLE001
            continue
        if (t.get('stages') or {}).get('proposal', {}).get('concepts'):
            trials[job_of(t)] = t
    made, missing = [], []
    for cid, v in sorted(dec.items()):
        if v not in ('like', 'now') or (out / f'{cid}.json').exists():
            continue
        card = cards.get(cid)
        parts = cid.split('_')
        trial = trials.get(parts[1]) if len(parts) >= 3 else None
        src_line = line(card, 'Источник:') if card else ''
        concept, scope = None, 'concept'
        if card and trial:
            concept = next((c for c in trial['stages']['proposal']['concepts'] if c.get('id') == parts[-1]), None)
        if concept:
            claims = claims_of(trial)
            keys = concept.get('basis_claim_keys') or concept.get('claim_keys') or concept.get('claims') or concept.get('facts') or []
            keys = [k if isinstance(k, str) else (k.get('key') or k.get('claim_key')) for k in keys]
            facts = [claims[k] for k in keys if k in claims]
        elif card and src_line.removeprefix('www.').rstrip('/') in pages:
            facts, scope = pages[src_line.removeprefix('www.').rstrip('/')], 'whole_page'
            concept = {'angle_ru': ''}
            trial = {'stages': {'source': {'url': facts[0]['source_url']}}}
        else:
            missing.append(cid)
            continue
        if not facts:
            missing.append(cid + ' (no cited facts)')
            continue
        ch, _, topic = card.get('prof', '').partition(': ')
        doc = {'id': cid, 'channel': ch, 'topic': topic, 'audience': ch, 'hook': card.get('text'),
               'hook_ru': line(card, 'По-русски:'), 'angle_ru': concept.get('angle_ru', ''),
               'viewer_question_ru': next((x for x in card.get('lines', [])[1:2]), ''),
               'end_question_ru': card.get('ask_ru') or line(card, 'Вопрос в конце:'),
               'not_in_source_ru': card.get('unknown', ''), 'script': '',
               'source_url': (trial['stages'].get('source') or {}).get('url'), 'facts': facts,
               'facts_scope': scope, 'owner_decision': v, 'status': 'ready_for_script', 'rules': RULES}
        (out / f'{cid}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
        made.append(cid)
    print(f'handoff: made {len(made)}: {", ".join(made)}')
    if missing:
        print(f'handoff: not made (no card/trial/facts) {len(missing)}: {", ".join(missing)}')


if __name__ == '__main__':
    main(sys.argv[1:])

"""Owner 22.11.2026: the small idea model ignores style rules (acronyms, agencies, no money). The big local model rewrites
each concept's first line (hook) from the concept's own source facts, in the style of the owner's reference reels:
money or a number from the facts + an everyday situation + who it is for, nothing to decode. The program then checks
the new hook (no acronyms/agency words, a number present, every number appears in the facts, no negative start) and
writes it back into trial.json; concepts still failing keep their program-check issues and never reach the phone.

Usage: python -I rewrite_hooks.py --api URL --model qwen3.5:27b TRIAL_JSON [TRIAL_JSON ...]
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('trials', nargs='+')
ap.add_argument('--api', default='http://127.0.0.1:11435')
ap.add_argument('--model', default='qwen3.5:27b')
a = ap.parse_args()

SYSTEM = (
    'You write the first spoken line of a 30-second explainer cartoon for ordinary Americans scrolling short videos. '
    'Style of the channel owner\'s reference reels: open with money or a hard number and an everyday moment a person '
    'can picture, so the viewer stops scrolling. Use ONLY facts given to you; every number you write must appear in '
    'the facts. Never use acronyms, agency names, program names, form numbers or words like agency, department, '
    'nonprofit, organization. Never start with no/not/stop/don\'t/there is no. Say who it is for in plain words. '
    'At most 15 words. Examples of the TONE (not facts to reuse): "Your electric bill hit $400? Your state may pay part '
    'of it." / "Lost your job last month? You can get paid while you look for the next one." / "Parents: up to $2,000 '
    'per kid comes back at tax time." Reply JSON only.')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['hook', 'who', 'scene'],
          'properties': {'hook': {'type': 'string'}, 'who': {'type': 'string'}, 'scene': {'type': 'string'}}}
BAD = re.compile(r"(?i)\b(nonprofit|non-profit|ngo|agency|department|administration|bureau|organization)s?\b")
NEG = re.compile(r"(?i)^(there (are|is) no|no |not |stop |don'?t |you can'?t|there'?s no|it'?s not|never )")
OWNER = ('owner rule 22.11', 'owner rule 08.11')


def ask(facts: list, concept: dict) -> dict:
    prompt = json.dumps({'facts': facts, 'idea': concept.get('angle_ru', ''), 'old_hook': concept.get('hook', ''),
                         'task': 'Write hook (English), who (plain words), scene (one cartoon scene, Russian, <=20 words).'},
                        ensure_ascii=False)
    body = {'model': a.model, 'system': SYSTEM, 'prompt': prompt, 'format': SCHEMA, 'stream': False, 'think': False,
            'options': {'temperature': 0.4, 'num_ctx': 8192, 'num_predict': 300, 'num_gpu': 0, 'num_thread': 6}}
    req = urllib.request.Request(a.api + '/api/generate', data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(json.loads(r.read().decode('utf-8'))['response'])


def problems(hook: str, facts_text: str) -> list:
    out = []
    ac = [w for w in re.findall(r"\b[A-Z]{2,}s?\b", hook) if w not in ('US', 'USA', 'OK')]
    if ac:
        out.append(f'acronym {ac}')
    if BAD.search(hook):
        out.append('agency/organization word')
    if NEG.match(hook.strip()):
        out.append('negative start')
    nums = re.findall(r'\d[\d,.]*', hook)
    if not nums:
        out.append('no money or number')
    for n in nums:
        if n.rstrip('.,').replace(',', '') not in facts_text.replace(',', ''):
            out.append(f'number {n} not in facts')
    if len(hook.split()) > 15:
        out.append('longer than 15 words')
    return out


for path in a.trials:
    p = Path(path)
    d = json.loads(p.read_text(encoding='utf-8'))
    st = d.get('stages', {})
    concepts = (st.get('proposal') or {}).get('concepts') or []
    claims = st.get('claims') or []
    claims = claims.get('claims', claims) if isinstance(claims, dict) else claims
    by_key = {c.get('key'): str(c.get('quote') or '') for c in claims if isinstance(c, dict)}
    checks = list(st.get('program_checks') or [])
    for c in concepts:
        keys = c.get('basis_claim_keys') or []
        facts = [by_key[k] for k in keys if k in by_key] or list(by_key.values())[:8]
        facts_text = ' '.join(facts)
        if not re.search(r'\d', facts_text):
            print(f'{p.name} {c["id"]}: facts have no number - stays out')
            continue
        try:
            r = ask(facts, c)
        except Exception as e:  # noqa: BLE001
            print(f'{p.name} {c["id"]}: model error {e!r}'[:200])
            continue
        hook = str(r.get('hook', '')).strip().strip('"')
        bad = problems(hook, facts_text)
        if bad:
            print(f'{p.name} {c["id"]}: rewrite failed ({"; ".join(bad)}): {hook}')
            continue
        c['hook_original'] = c.get('hook')
        c['hook'] = hook
        c['who'] = str(r.get('who', ''))[:80]
        c['scene_ru'] = str(r.get('scene', ''))[:160]
        checks = [x for x in checks if not (x.startswith(c['id'] + ':') and any(o in x for o in OWNER))]
        print(f'{p.name} {c["id"]}: OK {hook} | who: {c["who"]} | scene: {c["scene_ru"]}')
    st['program_checks'] = checks
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')

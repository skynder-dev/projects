"""Phone cards for the owner from concept trial results, with plain Russian written by the local model.

The concept model (qwen3.5:9b) writes clumsy Russian, so a separate step asks a bigger local model (default
qwen3.5:27b) to rewrite ONLY the owner-facing Russian lines of each card: a natural translation of the English hook,
one short question (what the video is about), one short line of what the source does not say, and a short topic name.
The English hook and the facts are not changed. Every line is checked (Cyrillic, length); a card that fails is not
sent and is listed in the report.

Usage: python -I make_cards.py OUT_CARDS_JSON TRIAL_JSON... [--api URL] [--model NAME] [--merge EXISTING_JSON]
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('trials', nargs='+')
ap.add_argument('--api', default='http://127.0.0.1:11435')
ap.add_argument('--model', default='qwen3.5:27b')
ap.add_argument('--merge')
a = ap.parse_args()
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

PAGES_RU = {'financial_aid': 'Учёба'}
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'required': ['topic_ru', 'hook_ru', 'question_ru', 'missing_ru'],
          'properties': {k: {'type': 'string'} for k in ('topic_ru', 'hook_ru', 'question_ru', 'missing_ru')}}
LIMITS = {'topic_ru': 40, 'hook_ru': 140, 'question_ru': 120, 'missing_ru': 110}
SYSTEM = ('Ты редактор. Пиши простым разговорным русским, как говорят люди, без канцелярита, без кальки с английского и '
          'без английских слов (кроме названий программ вроде LIHEAP, FHA, IRS). Ничего не добавляй от себя и не обещай '
          'больше, чем сказано. Ответ только JSON по схеме.')


def channel(stages: dict) -> str:
    ta = stages.get('topic_audience') or {}
    title = str((stages.get('source') or {}).get('title') or '')
    if re.search(r'student|financial aid|college|school', title, re.I) and ta.get('people'):
        return 'Учёба'
    if ta.get('people'):
        page = str((stages.get('source') or {}).get('opportunity_id') or '')
        for k, v in PAGES_RU.items():
            if k in page or k in json.dumps(stages.get('source', {})):
                return v
        return 'Помощь людям'
    if ta.get('profession'):
        return 'Профессии'
    if ta.get('rubric') == 'small_business_nonprofit':
        return 'Малый бизнес и НКО'
    return 'Помощь людям'


def ask(card: dict, title: str) -> dict:
    prompt = json.dumps({
        'задача': ('Перепиши для владельца канала: topic_ru — тема в 2-4 словах; hook_ru — естественный перевод первой '
                   'фразы ролика (кавычки не нужны); question_ru — о чём ролик, один короткий вопрос до 12 слов; '
                   'missing_ru — чего источник не говорит, одна короткая строка до 12 слов.'),
        'название_источника': title, 'первая_фраза_англ': card['hook'],
        'вопрос_модели': card.get('viewer_question_ru', ''), 'чего_нет_модели': card.get('not_answered_ru', '')},
        ensure_ascii=False)
    body = {'model': a.model, 'system': SYSTEM, 'prompt': prompt, 'format': SCHEMA, 'stream': False, 'think': False,
            'options': {'temperature': 0.2, 'num_ctx': 4096, 'num_predict': 400, 'num_gpu': 0, 'num_thread': 6}}
    req = urllib.request.Request(a.api + '/api/generate', data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(json.loads(r.read().decode('utf-8'))['response'])


def check(t: dict) -> list:
    bad = []
    for k, lim in LIMITS.items():
        v = str(t.get(k, '')).strip()
        if not v or not re.search('[а-яё]', v, re.I):
            bad.append(f'{k}: empty or not Russian')
        elif len(v) > lim:
            bad.append(f'{k}: longer than {lim}')
        elif re.search(r'\b[a-z]{5,}\b', re.sub(r'\b[A-Z0-9]{2,}\b', '', v)):
            bad.append(f'{k}: English word inside')
    return bad


# the model must exist on this PC; otherwise the largest Qwen there is used and the report says so
try:
    with urllib.request.urlopen(a.api + '/api/tags', timeout=30) as r:
        _names = [m.get('name', '') for m in json.loads(r.read().decode('utf-8')).get('models', [])]
except Exception as e:  # noqa: BLE001
    _names = []
    print(f'model list failed: {e!r}')
print('models here: ' + ', '.join(_names))
if _names and a.model not in _names:
    _alt = [n for n in _names if 'qwen' in n and any(x in n for x in ('27b', '32b', '14b'))]
    if not _alt:
        print(f'model {a.model} not found and no bigger Qwen; no cards')
        sys.exit(0)
    print(f'model {a.model} not found, using {_alt[0]}')
    a.model = _alt[0]
cards, report = [], []
for path in a.trials:
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    st = d.get('stages', {})
    prop = st.get('proposal') or {}
    if d.get('state') != 'structure_valid_needs_review' or not prop.get('concepts'):
        report.append(f'{path}: skipped, state {d.get("state")}')
        continue
    checks = st.get('program_checks') or []
    title = str((st.get('source') or {}).get('title') or '')
    rev = hashlib.sha256(json.dumps(prop, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
    job = hashlib.sha256((title + rev).encode('utf-8')).hexdigest()[:10]
    url = str((st.get('source') or {}).get('url') or '')
    for c in prop['concepts']:
        mine = [x for x in checks if x.startswith(c['id'] + ':') and 'free money' not in x]
        if mine:
            report.append(f'{path} {c["id"]}: not sent, program check: {"; ".join(mine)}')
            continue
        try:
            t = ask(c, title)
        except Exception as e:  # noqa: BLE001
            report.append(f'{path} {c["id"]}: not sent, model error {e!r}'[:300])
            continue
        bad = check(t)
        if bad:
            report.append(f'{path} {c["id"]}: not sent, Russian check: {"; ".join(bad)}')
            continue
        lines = ['По-русски: ' + t['hook_ru'].strip(), t['question_ru'].strip()]
        if url:
            lines.append('Источник: ' + re.sub(r'^https?://(www\.)?', '', url))
        cards.append({'id': f'so_{job}_{c["id"]}', 'kind': 'social',
                      'prof': f'{channel(st)}: {t["topic_ru"].strip()}', 'text': c['hook'], 'lines': lines,
                      'unknown': 'Чего нет в источнике: ' + t['missing_ru'].strip(), 'rev': rev})
        report.append(f'{path} {c["id"]}: ok')

old = []
if a.merge and Path(a.merge).exists():
    try:
        old = json.loads(Path(a.merge).read_text(encoding='utf-8')).get('cards', [])
    except Exception:  # noqa: BLE001
        old = []
ids = {c['id'] for c in cards}
merged = [c for c in old if c.get('id') not in ids] + cards
Path(a.out).write_text(json.dumps({'cards': merged}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'cards: {len(cards)} new, {len(merged)} total')
print('\n'.join(report))

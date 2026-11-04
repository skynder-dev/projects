"""Пробный запуск позднего ядра концептов на одном живом источнике (Grants.gov) и локальной модели.

Это ДИАГНОСТИКА, не штатный запуск Social:
- допуск запроса (concept_admission.admit) не пройден: нет закреплённых файлов токенизатора.
  Вместо него после ответа сверяется ТОЧНОЕ число токенов запроса, которое сообщила сама модель
  (prompt_eval_count). Приблизительная оценка по символам не используется.
- результат не принят владельцем и не сохраняется в ConceptStore.
- никакой публикации, платных API и медиа.

Запуск: python -I concept_trial.py <папка social> <папка для результата> [адрес Ollama]
"""
import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path

import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('social'); _ap.add_argument('out'); _ap.add_argument('api', nargs='?', default='http://127.0.0.1:11435')
_ap.add_argument('--keyword', default='community')
# --audience: keep only records Grants.gov lists for individuals, small businesses or nonprofits (temporary filter
# until socialreel/topics.py exists); --skip: file with opportunity IDs already used, one per line
_ap.add_argument('--audience', action='store_true')
_ap.add_argument('--skip')
# --opportunity: use this exact Grants.gov record (for before/after comparisons on the same input)
_ap.add_argument('--opportunity')
_args = _ap.parse_args()
SOCIAL, OUT, API = Path(_args.social).resolve(), Path(_args.out).resolve(), _args.api
WANT = ('individual', 'small business', 'nonprofit')
SKIP = set(Path(_args.skip).read_text(encoding='utf-8').split()) if _args.skip and Path(_args.skip).exists() else set()
sys.path.insert(0, str(SOCIAL))
OUT.mkdir(parents=True, exist_ok=True)
try:
    sys.stdout.reconfigure(encoding='utf-8')  # Windows console is cp1252; -I ignores PYTHONIOENCODING
except Exception:  # noqa: BLE001
    pass

from socialreel import grants, concept_core as core, concept_admission  # noqa: E402
from socialreel.claims import build_claims  # noqa: E402
from socialreel.common import PipelineError, parse_date, stable_json, sha256_bytes  # noqa: E402
from socialreel.json_contract import strict_loads  # noqa: E402

report = {'kind': 'SOCIAL_CONCEPT_TRIAL_DIAGNOSTIC', 'admission': 'NOT_PASSED_tokenizer_assets_missing',
          'accepted_by_owner': False, 'stages': {}}
summary = []


def done(state):
    report['state'] = state
    (OUT / 'trial.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'summary.txt').write_text('\n'.join(summary + ['state: ' + state]) + '\n', encoding='utf-8')
    print('\n'.join(summary + ['state: ' + state]))
    sys.exit(0)


# 1. живой источник: одна текущая возможность Grants.gov, срок не раньше чем через 21 день
today = dt.date.today()
client = grants.GrantsGovClient(OUT / 'source')
rec = snap = None
try:
    if _args.opportunity:
        det, meta = client.detail(_args.opportunity)
        rec, snap = grants.normalize({'id': _args.opportunity}, det, search_snapshot=None, detail_snapshot=meta), meta
        raise StopIteration
    hits, search_snap = client.search(_args.keyword, 25, 'posted')
    hits = [h for h in hits if (parse_date(h.get('closeDate')) or today) >= today + dt.timedelta(days=21)
            and str(h.get('id')) not in SKIP]
    hits.sort(key=lambda h: parse_date(h.get('closeDate')))
    for h in hits[:(8 if _args.audience else 3)]:
        det, meta = client.detail(str(h['id']))
        r = grants.normalize(h, det, search_snapshot=search_snap, detail_snapshot=meta)
        types = ' '.join(r.get('applicant_types') or []).lower()
        if _args.audience and not any(w in types for w in WANT):
            continue
        if r.get('detail_fetched') and r.get('description') and (r.get('applicant_eligibility_desc') or _args.audience):
            rec, snap = r, meta
            break
        if not _args.audience:
            rec, snap = rec or r, snap or meta
except StopIteration:
    pass
except Exception as e:  # noqa: BLE001
    summary.append('source: FAILED ' + repr(e)[:300])
    done('source_failed')
if rec is None:
    summary.append('source: no current opportunity found')
    done('source_failed')
report['stages']['source'] = {'opportunity_id': rec.get('opportunity_id'), 'title': rec.get('title'),
                              'agency': rec.get('agency_name'), 'close_date': str(rec.get('close_date')),
                              'applicant_types': rec.get('applicant_types'), 'keyword': _args.keyword,
                              'api_calls': len(client.calls)}
summary.append(f"source: {rec.get('opportunity_id')} | {rec.get('title')} | closes {rec.get('close_date')}")
summary.append('applicants: ' + '; '.join(rec.get('applicant_types') or ['(not listed)'])[:300])

# 2. факты с происхождением
try:
    claims = build_claims(rec, snap, today)
except PipelineError as e:
    summary.append('claims: FAILED ' + str(e)[:300])
    done('claims_failed')
report['stages']['claims'] = claims
summary.append(f'claims: {len(claims)}')

# 3. запрос строит само ядро; допуск перехватывается и честно помечается как непройденный
cfg = {'writer': 'ollama', 'local_editorial': {'enabled': True, 'execution_authorized': True},
       'ollama': {'model': 'qwen3.5:9b'},
       'concept_first': {'enabled': True, 'result_contract': core.RESULT_V2,
                         'brief': {'hook_language': 'en'},
                         'topic_direction': (f'Current date: {today.isoformat()}. Viewer: people in the US who work in, volunteer for or run the kind of '
                                             'organization this program funds, or the professionals and residents it serves. '
                                             'What they can concretely learn, check or bring to their organization about this '
                                             'real federal funding opportunity, keeping every condition and exclusion'),
                         'unknowns': ['Whether any particular viewer or organization is eligible',
                                      'Whether any applicant will actually receive funding',
                                      'Whether the opportunity changed after the snapshot date',
                                      'How many organizations will apply']}}
captured = {}


class Stop(Exception):
    pass


def capture(body):
    captured['body'] = body
    try:
        captured['admission'] = 'passed: ' + json.dumps(concept_admission.admit.__wrapped_original__(body))
    except PipelineError as e:
        captured['admission'] = 'refused: ' + str(e)[:300]
    raise Stop


capture.__wrapped_original__ = concept_admission.admit
concept_admission.admit = capture
try:
    core.build_request(rec, claims, cfg)
except Stop:
    pass
except PipelineError as e:
    summary.append('request: FAILED ' + str(e)[:300])
    done('request_failed')
body, data = captured['body'], None
data = core.inputs(rec, claims, cfg)
data['topic_direction'] = cfg['concept_first']['topic_direction']
data['forbidden_assumptions'] = list(cfg['concept_first']['unknowns'])
data['input_identity'] = core.digest(data)
report['stages']['request'] = {'admission_result': captured.get('admission'),
                               'body_sha256': sha256_bytes(stable_json(body).encode('utf-8')),
                               'prompt_utf8_bytes': len(body['prompt'].encode('utf-8')),
                               'system_utf8_bytes': len(body['system'].encode('utf-8')),
                               'options': body['options'],
                               'non_owner_envelope_bytes': len(stable_json(body).encode('utf-8')), 'body': body}
summary.append('admission: ' + str(captured.get('admission')))
adm = str(captured.get('admission'))
if not ('offline_tokenizer_unavailable' in adm or 'unverifiable_offline_admission: FileNotFoundError' in adm):
    # любой другой отказ допуска (размер, режим, ресурсы) настоящий: не обходим
    summary.append('stop: admission refused for a reason other than missing tokenizer files; no model call')
    done('admission_refused')

# 4. локальная модель (бесплатно, на процессоре, 4 потока, как задано ядром)
t0 = time.time()
try:
    req = urllib.request.Request(API + '/api/generate', data=json.dumps(body).encode('utf-8'), method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5400) as r:
        g = json.loads(r.read().decode('utf-8'))
except Exception as e:  # noqa: BLE001
    summary.append('model: FAILED ' + repr(e)[:300])
    done('model_failed')
secs = round(time.time() - t0)
meta = {k: g.get(k) for k in ('model', 'done_reason', 'prompt_eval_count', 'eval_count', 'total_duration')}
meta['seconds'] = secs
report['stages']['model'] = {**meta, 'raw_response': g.get('response')}
summary.append(f"model: {secs}s, prompt tokens {g.get('prompt_eval_count')} of ctx {body['options']['num_ctx']}, "
               f"output {g.get('eval_count')} of {body['options']['num_predict']}, done {g.get('done_reason')}")
if not g.get('prompt_eval_count') or g['prompt_eval_count'] >= body['options']['num_ctx'] - body['options']['num_predict']:
    summary.append('limit: prompt may be cut by the context window; result not accepted')
    done('context_exceeded')
if g.get('done_reason') != 'stop':
    summary.append('limit: output stopped early; result not accepted')
    done('output_truncated')

# 5. проверка ответа самим ядром (структура и ссылки на факты, не качество)
try:
    proposal = strict_loads(g.get('response') or '')
    diag = core.validate(proposal, data)
except Exception as e:  # noqa: BLE001
    report['stages']['validate'] = {'error': str(e)[:500]}
    summary.append('validate: FAILED ' + str(e)[:300])
    done('validation_failed')
report['stages']['validate'] = diag
report['stages']['proposal'] = proposal
# program checks after the core (diagnostic only, nothing is rewritten): dates already past, pressure wording
import re as _re
_MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                         'september', 'october', 'november', 'december'], 1)}
_PRESSURE = ('secure your spot', "don't miss", 'do not miss', 'miss the chance', 'guaranteed', 'act now', 'free money',
             'hurry', 'last chance')
issues = []
for c in proposal.get('concepts', []):
    text = ' '.join(str(c.get(k, '')) for k in core.CARD_TEXT_FIELDS)
    low = text.lower()
    for m in _re.finditer(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?', low):
        y = int(m.group(3)) if m.group(3) else today.year
        try:
            d = dt.date(y, _MONTHS[m.group(1)], int(m.group(2)))
        except ValueError:
            continue
        if d < today:
            issues.append(f"{c['id']}: date already past: {m.group(0)}")
    for m in _re.finditer(r'(20\d\d)-(\d\d)-(\d\d)|(\d{1,2})\.(\d{1,2})\.(20\d\d)', low):
        try:
            d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m.group(1) else dt.date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        except ValueError:
            continue
        if d < today:
            issues.append(f"{c['id']}: date already past: {m.group(0)}")
    for w in _PRESSURE:
        if w in low:
            issues.append(f"{c['id']}: pressure wording: {w}")
report['stages']['program_checks'] = issues
summary.append('program checks: ' + ('; '.join(issues) if issues else 'no past dates, no pressure wording found'))
summary.append(f"validate: ok, {diag.get('result_state')}, concepts {diag.get('concept_count')}")
for c in proposal.get('concepts', []):
    summary.append(f"{c['id']}: {c['viewer_question_ru'][:160]} | hook: {c['hook'][:120]}")
done('structure_valid_needs_review')

"""Saved trial review through ConceptStore; no model, transport or publication."""
from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from . import concept_core as core, concept_decision_ledger as decisions, concept_owner_context as owner
from .common import PipelineError, sha256_bytes, stable_json, utc_now
from .concept_store import ConceptStore, RESULT_SCHEMA
from .json_contract import strict_loads


def _stamp():
    return utc_now().isoformat()


def _source(trial, data):
    reported = trial.get('stages', {}).get('source') or {}
    context = data.get('source_context') or {}
    reported = reported if isinstance(reported, dict) else {}
    context = context if isinstance(context, dict) else {}
    close = reported.get('close_date')
    return {'title': context.get('title') or reported.get('title'),
            'source_url': context.get('url') or reported.get('source_url'),
            'close_date': None if close in (None, '', 'None', 'null') else close,
            'source_identity': data.get('source_identity'), 'audience': data.get('audience'),
            'audience_description': context.get('audience_description'),
            'currentness_verified': False}


def _analyze(trial):
    """Reconstruct unprojected core inputs and validate; reported success is data."""
    stages = trial['stages']
    request = stages.get('request') if isinstance(stages.get('request'), dict) else {}
    model = stages.get('model') if isinstance(stages.get('model'), dict) else {}
    body = request.get('body')
    proposal, data, diagnostics = {}, {}, None
    request_hash = core.digest(body) if isinstance(body, dict) else None
    validation = {'valid': False, 'bindings_valid': False, 'structurally_valid': False,
                  'complete_result': trial.get('state') == 'structure_valid_needs_review' and
                                     model.get('done_reason') == 'stop',
                  'admission_verified': False, 'source_verified': False, 'errors': []}
    try:
        if not isinstance(body, dict) or request.get('body_sha256') != request_hash:
            raise PipelineError('Exact request body/hash missing or mismatched')
        decoded = strict_loads(body['prompt'])
        if not isinstance(decoded, dict) or decoded.get('schema') != core.VERSION or decoded.get('evidence_mode') == 'excerpts':
            raise PipelineError('Saved trial requires the existing claim-based core inputs')
        data = decoded
        claims = stages.get('claims')
        if not isinstance(claims, list) or not claims or len({c['key'] for c in claims}) != len(claims):
            raise PipelineError('Saved trial needs unique complete claims')
        expected = [{'claim_key': c['key'], 'statement': c['statement'], 'values': copy.deepcopy(c.get('values')),
                     'source': core.project_source(c.get('source') or {})} for c in claims]
        if data.get('factual_core') != expected or data.get('claims_identity') != core.digest(claims):
            raise PipelineError('Request differs from saved claims; no owner decision allowed')
        for target, original in zip(data['factual_core'], claims):
            target['source'] = copy.deepcopy(original.get('source') or {})
        context = [copy.deepcopy(row) for c in claims for row in c.get('source_context', [])]
        projected = [{**row, 'source': core.project_source(row['source'])} for row in context]
        if data['source_context'].get('condition_fields', []) != projected:
            raise PipelineError('Request condition context differs from saved claims')
        if context:
            data['source_context']['condition_fields'] = context
        if data.get('input_identity') != core.digest({k: v for k, v in data.items() if k != 'input_identity'}):
            raise PipelineError('Saved request input identity differs; rebuild required')
        if not re.fullmatch('[0-9a-f]{64}', str(data.get('source_identity') or '')):
            raise PipelineError('Source identity missing')
        expected_schema = core.schema([c['key'] for c in claims], data.get('language_contract'),
            result_contract=data.get('result_contract', core.VERSION), input_identity=data['input_identity'])
        if body.get('format') != expected_schema:
            raise PipelineError('Request schema differs from the unchanged core')
        validation['bindings_valid'] = True
        raw = model.get('raw_response')
        if not isinstance(raw, str):
            raise PipelineError('Raw model answer missing')
        decoded = strict_loads(raw)
        if not isinstance(decoded, dict):
            raise PipelineError('Model answer is not a concept object')
        proposal = decoded
        if 'proposal' in stages and stages['proposal'] != proposal:
            raise PipelineError('Reported proposal differs from raw model answer')
        diagnostics = core.validate(proposal, data)
        validation['structurally_valid'] = True
        if not validation['complete_result']:
            raise PipelineError('Trial did not finish with a complete reviewable result')
        validation['valid'] = True
    except (PipelineError, ValueError, KeyError, TypeError, AttributeError) as error:
        validation['errors'].append(str(error))
    validation['diagnostics'] = diagnostics
    return data, proposal, validation, request_hash


def import_trial(store: ConceptStore, path: Path):
    raw = Path(path).read_bytes()
    trial = strict_loads(raw.decode('utf-8-sig'))
    if not isinstance(trial, dict) or trial.get('kind') != 'SOCIAL_CONCEPT_TRIAL_DIAGNOSTIC' or not isinstance(trial.get('stages'), dict):
        raise PipelineError('Expected a concept_trial.py trial.json object')
    data, proposal, validation, request_hash = _analyze(trial)
    digest = sha256_bytes(raw)
    value = {'schema': RESULT_SCHEMA, 'job_id': digest[:32], 'parent_revision': 'absent', 'created_at': _stamp(),
             'operation': {'type': 'import'}, 'trial_sha256': digest, 'source': _source(trial, data),
             'request_sha256': request_hash, 'source_inputs': data, 'proposal': proposal,
             'validation': validation, 'decision_event': None}
    job, revision, imported = store.import_result(raw, value)
    return {'job_id': job, 'revision': revision, 'imported': imported,
            'message': 'Imported; owner review required' if imported else 'Already imported; no new revision'}


def show(store: ConceptStore, job):
    saved = store.result_snapshot(job)
    history = saved['history']
    if not history:
        return {'job_id': job, 'revision': 'absent', 'state': 'import_incomplete', 'import': saved['import'],
                'history': [], 'decision_history': [], 'owner_approved': False,
                'uncommitted_revisions': saved['uncommitted_revisions']}
    content = next((r for r in history if r['operation']['type'] in ('import', 'edit')), None)
    if content is None or saved['raw_trial'] is None:
        raise PipelineError('Saved result has no content revision or raw trial')
    events, decision_head, content_cursor = [], 'absent', None
    for row in reversed(history):
        operation = row['operation']['type']
        if operation in ('import', 'edit'):
            content_cursor = row['revision']
        event = row.get('decision_event')
        if event is None:
            if operation not in ('import', 'edit'):
                raise PipelineError('Saved decision revision has no event')
            continue
        if (operation != 'decision' or event.get('explicit_owner_decision') is not True or event.get('content_revision') != content_cursor
                or event.get('action') not in ('pick', 'reject_all') or not isinstance(event.get('note'), str) or not event['note'].strip()):
            raise PipelineError('Saved owner decision binding invalid')
        ids = {c['id'] for c in row['proposal'].get('concepts', [])}
        if (not row['validation']['valid'] or (event['action'] == 'pick' and event.get('selected') not in ids) or
                (event['action'] == 'reject_all' and event.get('selected') is not None)):
            raise PipelineError('Saved decision does not select a valid concept revision')
        events.append((event['request_id'], event))
        decision_head = decisions.digest(event)
    _, decision_history, _ = decisions.verify_events(job, events, decision_head)
    latest = decision_history[0] if decision_history else None
    current = latest if latest and latest['content_revision'] == content['revision'] else None
    state = ('invalid_result' if not history[0]['validation']['valid'] else
             'picked' if current and current['action'] == 'pick' else
             'rejected_all' if current else 'decision_stale' if latest else 'needs_owner_review')
    return {'job_id': job, 'revision': saved['revision'], 'content_revision': content['revision'], 'state': state,
            'source': history[0]['source'], 'request_sha256': history[0]['request_sha256'],
            'proposal': history[0]['proposal'], 'validation': history[0]['validation'],
            'current_decision': current, 'latest_decision': latest, 'decision_history': decision_history,
            'owner_approved': state == 'picked', 'approval_scope': 'editorial_choice_only', 'publication_approved': False,
            'trial': strict_loads(saved['raw_trial'].decode('utf-8-sig')), 'import': saved['import'],
            'history': history, 'uncommitted_revisions': saved['uncommitted_revisions'],
            'owner_context': owner.read(store, job)}


def list_jobs(store):
    return [show(store, row['id']) for row in store.result_jobs()]


def _next(view, operation):
    value = copy.deepcopy(view['history'][0])
    value.pop('revision')
    value.update(parent_revision=view['revision'], created_at=_stamp(), operation=operation, decision_event=None)
    return value


def decide(store, job, expected_revision, *, pick=None, reject_all=False, note):
    view = show(store, job)
    if expected_revision != view['revision']:
        raise PipelineError('Concept revision conflict; decision on an old revision refused')
    if not view.get('validation', {}).get('valid'):
        raise PipelineError('Owner decision requires a structurally valid, bound, complete result')
    if (pick is None) == (not reject_all) or not isinstance(note, str) or not note.strip():
        raise PipelineError('Choose one concept or reject all, with a nonempty owner note')
    if pick is not None and pick not in {c['id'] for c in view['proposal'].get('concepts', [])}:
        raise PipelineError('Chosen concept is absent from this revision')
    value = _next(view, {'type': 'decision'})
    event = {'job_id': job, 'scope': 'editorial_choice_only', 'approved': False, 'explicit_owner_decision': True,
             'request_id': uuid.uuid4().hex, 'parent_revision': view['latest_decision']['revision'] if view['latest_decision'] else 'absent',
             'content_revision': view['content_revision'], 'action': 'reject_all' if reject_all else 'pick',
             'selected': pick, 'note': note, 'created_at': value['created_at']}
    value['decision_event'] = event
    revision = store.append_result(job, expected_revision, value)
    return {'job_id': job, 'revision': revision, 'content_revision': view['content_revision'], 'decision': event}


def edit(store, job, concept_id, field, text, expected_revision):
    view = show(store, job)
    if expected_revision != view['revision']:
        raise PipelineError('Concept revision conflict; stale edit refused')
    if field not in core.CARD_TEXT_FIELDS or not isinstance(text, str):
        raise PipelineError('Edit allows only the five concept text fields; IDs, facts and provenance are immutable')
    if not view.get('validation', {}).get('bindings_valid') or not view['validation'].get('complete_result'):
        raise PipelineError('Cannot edit an unbound or incomplete model result')
    value = _next(view, {'type': 'edit', 'concept_id': concept_id, 'field': field, 'value': text})
    card = next((c for c in value['proposal'].get('concepts', []) if c['id'] == concept_id), None)
    if card is None:
        raise PipelineError('Concept not found in current revision')
    card[field] = text
    diagnostics = core.validate(value['proposal'], value['source_inputs'])
    value['validation'].update(valid=True, structurally_valid=True, diagnostics=diagnostics, errors=[])
    revision = store.append_result(job, expected_revision, value)
    return {'job_id': job, 'revision': revision, 'content_revision': revision, 'state': 'needs_owner_review', 'owner_approved': False}


def _decision_text(view):
    current = view.get('current_decision')
    if current:
        return ('Владелец выбрал ' + current['selected'] if current['action'] == 'pick' else 'Владелец отклонил все варианты') + '\n\nПричина: ' + current['note']
    if view.get('latest_decision'):
        return 'Предыдущее решение устарело после правки. Нужен новый выбор.\n\nПредыдущая причина: ' + view['latest_decision']['note']
    return 'Решения владельца нет. Нужен просмотр.'


def export_markdown(store, job, path):
    view = show(store, job)
    if not view['history']:
        raise PipelineError('Import is incomplete; retry import before exporting')
    source = view['source']
    link = ('[Официальная страница](<' + source['source_url'] + '>)') if isinstance(source.get('source_url'), str) else 'Ссылка неизвестна'
    lines = ['# ' + str(source.get('title') or 'Источник без заголовка'), '',
             'Источник: ' + link,
             '', 'Срок: ' + str(source.get('close_date') or 'Не указан'), '', '## Решение', '', _decision_text(view),
             '', 'Структура: ' + ('проверена; качество и актуальность не подтверждены.' if view['validation']['valid']
                                  else 'результат не прошёл проверку; решение недоступно.'),
             '', 'Ревизия: `' + view['revision'] + '`', '']
    labels = (('viewer_question_ru', 'Вопрос зрителя'), ('angle_ru', 'Подход'), ('what_viewer_learns_ru', 'Что узнает зритель'),
              ('not_answered_ru', 'Что осталось без ответа'), ('hook', 'Первая фраза'))
    for card in view['proposal'].get('concepts', []):
        lines.extend(['## ' + card['id'], ''])
        for field, label in labels:
            lines.extend(['**' + label + '**', '', str(card.get(field, '')), ''])
        lines.extend(['**Опорные факты:** ' + ', '.join(card.get('basis_claim_keys', [])), ''])
    if not view['proposal'].get('concepts'):
        lines.extend(['Варианты отсутствуют.', '', str(view['proposal'].get('reason_ru') or ''), ''])
        for gap in view['proposal'].get('missing_evidence_ru', []):
            lines.extend([gap, ''])
    if view['validation']['errors']:
        lines.extend(['## Диагностика', '', *view['validation']['errors'], ''])
    imported_claims = view['trial']['stages'].get('claims')
    claims = {c['key']: c for c in imported_claims if isinstance(c, dict) and isinstance(c.get('key'), str)} if isinstance(imported_claims, list) else {}
    cited = list(dict.fromkeys([k for c in view['proposal'].get('concepts', []) for k in c.get('basis_claim_keys', [])] +
                              view['proposal'].get('reviewed_basis_claim_keys', [])))
    if cited:
        lines.extend(['## Факты и происхождение', ''])
    for key in cited:
        claim = claims.get(key)
        if claim is None:
            lines.extend(['### ' + key, '', 'Факт отсутствует в сохранённом источнике.', ''])
            continue
        src = claim.get('source') or {}
        lines.extend(['### ' + key, '', claim['statement'], ''])
        if 'quote' in src:
            lines.extend(['**Точная цитата**', '', src['quote'], ''])
        try:
            provenance = core.project_source(src)
        except PipelineError:
            provenance = {'unverified_imported_source': src}
        lines.extend(['Происхождение:', '', '```json', stable_json(provenance).rstrip('\n'), '```', ''])
    store.export_result(job, view['revision'], Path(path), '\n'.join(lines).encode('utf-8'))
    return {'job_id': job, 'revision': view['revision'], 'markdown': str(Path(path))}


def _fact_source(source):
    projected = core.project_source(source)
    children = source.get('supporting_sources') or []
    if children:
        for child in children:
            _fact_source(child)
    elif (not re.fullmatch('[0-9a-f]{64}', str(source.get('snapshot_sha256') or '')) or
          not (source.get('quote') or source.get('fields') or source.get('locator'))):
        raise PipelineError('Cited fact requires an exact quote/locator and snapshot SHA-256')
    return projected


def handoff(store, job, out):
    view = show(store, job)
    if view.get('state') != 'picked' or not view.get('owner_approved'):
        raise PipelineError('Handoff requires an explicit owner pick on the current content revision')
    url = view['source'].get('source_url')
    parts = urlsplit(url) if isinstance(url, str) else None
    if parts is None or parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
        raise PipelineError('Source URL unknown or invalid; no handoff created')
    pick = view['current_decision']['selected']
    card = next(c for c in view['proposal']['concepts'] if c['id'] == pick)
    claims = {c['key']: c for c in view['trial']['stages']['claims']}
    facts = []
    for key in card['basis_claim_keys']:
        claim = copy.deepcopy(claims[key])
        claim['source'] = _fact_source(claim['source'])
        for context in claim.get('source_context', []):
            context['source'] = _fact_source(context['source'])
        facts.append(claim)
    identifier = job + '-' + view['current_decision']['revision'] + '-' + pick
    payload = {'id': identifier, 'topic': card['viewer_question_ru'],
               'audience': view['source'].get('audience_description') or view['source'].get('audience') or '',
               'script': '', 'source_url': url, 'facts': facts}
    path = Path(out) / (identifier + '.json')
    store.export_result(job, view['revision'], path, stable_json(payload).encode('utf-8'))
    return {'job_id': job, 'revision': view['revision'], 'handoff': str(path), 'id': identifier}

"""Synthetic saved-result lifecycle, stale writes and durable failure recovery; offline."""
import concurrent.futures
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from socialreel import concept_choose as choose, concept_core as core, usagov
from socialreel.__main__ import main
from socialreel.common import ROOT, PipelineError, read_json, sha256_bytes, stable_json
from socialreel.concept_store import ConceptStore
from tests.test_concept_offline import config
from tests.test_concept_source_cards import inspect_request

FIX = ROOT / 'fixtures'
TRIAL = FIX / 'concept_trial_synthetic.json'


class ConceptChooseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.store = ConceptStore(self.home / 'store')
        self.trial = read_json(TRIAL)
        for target in ('socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
                       'urllib.request.urlopen', 'urllib.request.OpenerDirector.open'):
            guard = patch(target, side_effect=AssertionError('Network/model calls forbidden'))
            guard.start()
            self.addCleanup(guard.stop)

    def imported(self):
        return choose.import_trial(self.store, TRIAL)['job_id']

    def snapshot(self, job):
        return choose.show(self.store, job)

    def modified_trial(self, trial, filename='modified.json'):
        path = self.home / filename
        path.write_text(stable_json(trial), encoding='utf-8')
        return choose.import_trial(self.store, path)['job_id']

    def make_trial(self, *, url='https://www.usa.gov/synthetic-review-fixture', missing_hash=False, source_context=False, contract=core.RESULT_V2):
        trial = copy.deepcopy(self.trial)
        claims = trial['stages']['claims']
        record = {'title': 'Synthetic source for saved concept review', 'source_url': url}
        if source_context:
            record, _ = usagov.USAGovClient(self.home / 'source').page('energy', fixture=FIX / 'usagov_energy_synthetic.html')
            claims = usagov.build_claims(record)
            for card in trial['stages']['proposal']['concepts']:
                card['basis_claim_keys'] = [claims[0]['key'], claims[-1]['key']]
        if missing_hash:
            claims[0]['source'].pop('snapshot_sha256')
        cfg = config()
        cfg['concept_first']['result_contract'] = contract
        result = inspect_request(record, claims, cfg)
        trial['stages']['claims'] = claims
        trial['stages']['source'] = {'title': record['title'], 'close_date': None}
        trial['stages']['request'].update(body=result['body'], body_sha256=core.digest(result['body']))
        trial['stages']['model']['raw_response'] = stable_json(trial['stages']['proposal'])
        return trial

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(['concepts', *args, '--store', str(self.store.root)])
        return code, out.getvalue(), err.getvalue()

    def test_import_stores_byte_exact_trial_bound_request_and_all_concepts(self):
        result = choose.import_trial(self.store, TRIAL)
        self.assertTrue(result['imported'])
        view = self.snapshot(result['job_id'])
        self.assertEqual(view['trial'], self.trial)
        self.assertEqual(view['proposal'], self.trial['stages']['proposal'])
        self.assertEqual(view['request_sha256'], core.digest(self.trial['stages']['request']['body']))
        self.assertEqual(view['source']['source_identity'], json.loads(self.trial['stages']['request']['body']['prompt'])['source_identity'])
        self.assertTrue(view['validation']['valid'])
        self.assertFalse(view['owner_approved'])
        self.assertFalse(view['validation']['admission_verified'])
        self.assertFalse(view['publication_approved'])
        path = self.store.folder(result['job_id']) / 'concept_results' / 'trial.json'
        self.assertEqual(path.read_bytes(), TRIAL.read_bytes())
        revision = view['history'][0]
        self.assertEqual(revision['operation']['type'], 'import')
        self.assertEqual(revision['parent_revision'], 'absent')

    def test_identical_bytes_reimport_is_noop_even_after_edit_and_decision(self):
        job = self.imported()
        original = self.snapshot(job)
        picked = choose.decide(self.store, job, original['revision'], pick='C2', note='Выбираю второй вариант.')
        edited = choose.edit(self.store, job, 'C2', 'hook', 'An exact owner edit.', picked['revision'])
        before = {p.name: p.read_bytes() for p in (self.store.folder(job) / 'concept_results' / 'revisions').glob('*.json')}
        clone = self.home / 'same-file-another-name.json'
        clone.write_bytes(TRIAL.read_bytes())
        result = choose.import_trial(self.store, clone)
        self.assertFalse(result['imported'])
        self.assertEqual(result['job_id'], job)
        self.assertEqual(result['revision'], edited['revision'])
        self.assertIn('no new revision', result['message'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.store.folder(job) / 'concept_results' / 'revisions').glob('*.json')})

    def test_cli_roundtrip_import_list_show_decide_edit_export_handoff(self):
        code, out, err = self.cli('import', str(TRIAL))
        self.assertEqual((code, err), (0, ''))
        job = json.loads(out)['job_id']
        code, out, _ = self.cli('list')
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn(self.trial['stages']['source']['title'], out)
        self.assertIn('\tneeds_owner_review\t3\tnone', out)
        code, out, _ = self.cli('show', job)
        self.assertEqual(code, 0)
        revision = json.loads(out)['revision']
        code, out, _ = self.cli('decide', job, '--pick', 'C2', '--note', 'Подходит зрителю.', '--revision', revision)
        self.assertEqual(code, 0)
        decision = json.loads(out)
        code, out, _ = self.cli('handoff', job, '--out', str(self.home / 'shared'))
        self.assertEqual(code, 0)
        self.assertTrue(Path(json.loads(out)['handoff']).exists())
        code, out, _ = self.cli('edit', job, 'C2', '--field', 'hook', '--value', 'Exact owner hook.\nSecond line.', '--revision', decision['revision'])
        self.assertEqual(code, 0)
        code, _, _ = self.cli('export', job, '--md', str(self.home / 'phone.md'))
        self.assertEqual(code, 0)
        self.assertIn('Exact owner hook.\nSecond line.', (self.home / 'phone.md').read_text(encoding='utf-8'))
        self.assertIn('устарело', (self.home / 'phone.md').read_text(encoding='utf-8'))

    def test_explicit_pick_and_reject_are_immutable_linked_decisions(self):
        job = self.imported()
        first = self.snapshot(job)
        picked = choose.decide(self.store, job, first['revision'], pick='C2', note='Выбираю C2.')
        view = self.snapshot(job)
        self.assertEqual(view['state'], 'picked')
        self.assertTrue(view['owner_approved'])
        self.assertEqual(view['current_decision']['content_revision'], first['revision'])
        self.assertFalse(view['current_decision']['approved'])  # never production approval
        self.assertEqual(view['history'][0]['parent_revision'], first['revision'])
        rejected = choose.decide(self.store, job, picked['revision'], reject_all=True, note='Отклоняю все: недостаточно пользы.')
        view = self.snapshot(job)
        self.assertEqual(view['state'], 'rejected_all')
        self.assertFalse(view['owner_approved'])
        self.assertEqual(len(view['decision_history']), 2)
        self.assertEqual(view['decision_history'][0]['parent_revision'], view['decision_history'][1]['revision'])
        self.assertEqual(view['history'][0]['parent_revision'], picked['revision'])
        self.assertEqual(view['proposal'], self.trial['stages']['proposal'])

    def test_edit_keeps_original_raw_answer_variants_and_stales_previous_pick(self):
        job = self.imported()
        before = self.snapshot(job)
        picked = choose.decide(self.store, job, before['revision'], pick='C2', note='Первый выбор.')
        change = 'Exact modified hook — no translation.\nKeep this second sentence.'
        edited = choose.edit(self.store, job, 'C2', 'hook', change, picked['revision'])
        view = self.snapshot(job)
        self.assertEqual(view['state'], 'decision_stale')
        self.assertIsNone(view['current_decision'])
        self.assertFalse(view['owner_approved'])
        self.assertEqual(view['content_revision'], edited['revision'])
        self.assertEqual(view['trial']['stages']['model']['raw_response'], self.trial['stages']['model']['raw_response'])
        self.assertEqual(view['history'][-1]['proposal'], self.trial['stages']['proposal'])
        self.assertEqual(view['proposal']['concepts'][1]['hook'], change)
        self.assertEqual(view['proposal']['concepts'][0], before['proposal']['concepts'][0])
        self.assertEqual(view['proposal']['concepts'][2], before['proposal']['concepts'][2])
        with self.assertRaisesRegex(PipelineError, 'old revision'):
            choose.decide(self.store, job, before['revision'], pick='C1', note='Устаревший выбор.')
        choose.decide(self.store, job, edited['revision'], pick='C2', note='Подтверждаю исправленный вариант.')
        self.assertEqual(self.snapshot(job)['current_decision']['content_revision'], edited['revision'])

    def test_stale_edit_after_another_save_refused_without_silent_merge(self):
        job = self.imported()
        start = self.snapshot(job)['revision']
        choose.edit(self.store, job, 'C1', 'hook', 'First saved hook.', start)
        with self.assertRaisesRegex(PipelineError, 'stale edit'):
            choose.edit(self.store, job, 'C2', 'hook', 'Stale second hook.', start)
        self.assertEqual(self.snapshot(job)['proposal']['concepts'][1]['hook'], self.trial['stages']['proposal']['concepts'][1]['hook'])

    def test_two_concurrent_writers_same_revision_only_one_succeeds(self):
        job = self.imported()
        start = self.snapshot(job)['revision']
        barrier = threading.Barrier(2)
        def write(text):
            barrier.wait()
            try:
                return choose.edit(self.store, job, 'C1', 'hook', text, start)
            except PipelineError as error:
                return error
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(write, ['Concurrent writer A.', 'Concurrent writer B.']))
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertEqual(sum(isinstance(r, PipelineError) for r in results), 1)
        self.assertEqual(len(self.snapshot(job)['history']), 2)

    def fail_head(self, job, callback):
        head = self.store.folder(job) / 'concept_results' / 'head.json'
        before = head.read_bytes()
        replace = os.replace
        def fail(source, target):
            if Path(target) == head:
                raise OSError('Injected head replacement failure')
            return replace(source, target)
        with patch('socialreel.concept_storage.os.replace', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'Injected'):
                callback()
        self.assertEqual(head.read_bytes(), before)

    def test_interrupted_edit_preserves_prior_revision_and_reports_orphan(self):
        job = self.imported()
        first = self.snapshot(job)
        self.fail_head(job, lambda: choose.edit(self.store, job, 'C1', 'hook', 'Uncommitted edit.', first['revision']))
        after = self.snapshot(job)
        self.assertEqual(after['revision'], first['revision'])
        self.assertEqual(after['proposal'], first['proposal'])
        self.assertEqual(len(after['uncommitted_revisions']), 1)
        orphan = self.store.folder(job) / 'concept_results' / 'revisions' / after['uncommitted_revisions'][0]
        raw = orphan.read_bytes()
        choose.edit(self.store, job, 'C1', 'hook', 'Fresh explicit edit.', first['revision'])
        self.assertEqual(orphan.read_bytes(), raw)
        self.assertEqual(len(self.snapshot(job)['history']), 2)

    def test_interrupted_decision_does_not_grant_owner_pick_or_break_ledger(self):
        job = self.imported()
        first = self.snapshot(job)
        self.fail_head(job, lambda: choose.decide(self.store, job, first['revision'], pick='C2', note='Uncommitted pick.'))
        after = self.snapshot(job)
        self.assertEqual(after['revision'], first['revision'])
        self.assertFalse(after['owner_approved'])
        self.assertEqual(after['decision_history'], [])
        self.assertEqual(len(after['uncommitted_revisions']), 1)
        with self.assertRaisesRegex(PipelineError, 'explicit owner pick'):
            choose.handoff(self.store, job, self.home / 'shared')

    def test_interrupted_fsync_keeps_previous_revision_readable(self):
        job = self.imported()
        first = self.snapshot(job)
        with patch('socialreel.concept_storage.os.fsync', side_effect=OSError('Injected sync failure')):
            with self.assertRaisesRegex(OSError, 'sync failure'):
                choose.edit(self.store, job, 'C2', 'hook', 'Unsynced edit.', first['revision'])
        self.assertEqual(self.snapshot(job)['revision'], first['revision'])
        choose.edit(self.store, job, 'C2', 'hook', 'New durable edit.', first['revision'])
        self.assertEqual(self.snapshot(job)['proposal']['concepts'][1]['hook'], 'New durable edit.')

    def test_interrupted_first_import_is_visible_and_explicit_retry_recovers(self):
        with patch('socialreel.concept_store.write_json', side_effect=OSError('Injected initial head failure')):
            with self.assertRaises(OSError):
                choose.import_trial(self.store, TRIAL)
        jobs = choose.list_jobs(self.store)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['state'], 'import_incomplete')
        retried = choose.import_trial(self.store, TRIAL)
        self.assertTrue(retried['imported'])
        self.assertEqual(self.snapshot(retried['job_id'])['state'], 'needs_owner_review')

    def test_export_contains_all_exact_fields_facts_and_current_decision(self):
        job = self.imported()
        first = self.snapshot(job)
        note = 'Выбор владельца.\nВторая строка причины без сокращения.'
        choose.decide(self.store, job, first['revision'], pick='C2', note=note)
        target = self.home / 'phone.md'
        choose.export_markdown(self.store, job, target)
        raw = target.read_bytes()
        text = raw.decode('utf-8')
        for card in first['proposal']['concepts']:
            for field in core.CARD_TEXT_FIELDS:
                self.assertIn(card[field], text)
            self.assertIn(card['id'], text)
            for key in card['basis_claim_keys']:
                self.assertIn(key, text)
        self.assertIn(note, text)
        self.assertIn('Владелец выбрал C2', text)
        self.assertIn('2026-12-31', text)
        self.assertIn(first['source']['source_url'], text)
        for claim in self.trial['stages']['claims']:
            if 'quote' in claim['source']:
                self.assertIn(claim['source']['quote'], text)
        choose.export_markdown(self.store, job, target)  # identical output is a no-op
        self.assertEqual(target.read_bytes(), raw)
        current = self.snapshot(job)
        choose.edit(self.store, job, 'C2', 'hook', 'Different export revision.', current['revision'])
        with self.assertRaisesRegex(PipelineError, 'Immutable file differs'):
            choose.export_markdown(self.store, job, target)
        self.assertEqual(target.read_bytes(), raw)

    def test_handoff_exact_schema_chosen_citations_quote_locator_and_hash(self):
        job = self.imported()
        choose.decide(self.store, job, self.snapshot(job)['revision'], pick='C2', note='Explicit fixture pick.')
        result = choose.handoff(self.store, job, self.home / 'shared')
        payload = read_json(result['handoff'])
        self.assertEqual(set(payload), {'id', 'topic', 'audience', 'script', 'source_url', 'facts'})
        self.assertEqual(Path(result['handoff']).name, payload['id'] + '.json')
        self.assertEqual(payload['script'], '')
        self.assertEqual(payload['topic'], self.trial['stages']['proposal']['concepts'][1]['viewer_question_ru'])
        self.assertEqual([f['key'] for f in payload['facts']], ['eligibility', 'apply'])
        originals = {c['key']: c for c in self.trial['stages']['claims']}
        for fact in payload['facts']:
            source = originals[fact['key']]['source']
            self.assertEqual(fact['source']['snapshot_sha256'], source['snapshot_sha256'])
            self.assertEqual(fact['statement'], originals[fact['key']]['statement'])
            self.assertNotIn('snapshot_file', fact['source'])
            self.assertEqual(fact['source'].get('quote'), source.get('quote'))
            self.assertEqual(fact['source'].get('fields'), source.get('fields'))
        self.assertEqual(choose.handoff(self.store, job, self.home / 'shared'), result)

    def test_handoff_refused_before_pick_after_edit_or_reject_and_when_url_unknown(self):
        job = self.imported()
        with self.assertRaises(PipelineError):
            choose.handoff(self.store, job, self.home / 'pending')
        picked = choose.decide(self.store, job, self.snapshot(job)['revision'], pick='C2', note='First pick.')
        choose.edit(self.store, job, 'C2', 'hook', 'Changed content.', picked['revision'])
        with self.assertRaises(PipelineError):
            choose.handoff(self.store, job, self.home / 'stale')
        choose.decide(self.store, job, self.snapshot(job)['revision'], reject_all=True, note='Reject after edit.')
        with self.assertRaises(PipelineError):
            choose.handoff(self.store, job, self.home / 'reject')
        unknown = self.modified_trial(self.make_trial(url=None))
        choose.decide(self.store, unknown, self.snapshot(unknown)['revision'], pick='C2', note='Review only; URL unknown.')
        with self.assertRaisesRegex(PipelineError, 'Source URL unknown'):
            choose.handoff(self.store, unknown, self.home / 'unknown')
        for name in ('pending', 'stale', 'reject', 'unknown'):
            self.assertFalse((self.home / name).exists())

    def test_handoff_does_not_invent_missing_snapshot_hash(self):
        job = self.modified_trial(self.make_trial(missing_hash=True))
        choose.decide(self.store, job, self.snapshot(job)['revision'], pick='C1', note='Fixture pick.')
        with self.assertRaisesRegex(PipelineError, 'snapshot SHA-256'):
            choose.handoff(self.store, job, self.home / 'shared')
        self.assertFalse((self.home / 'shared').exists())

    def test_handoff_cannot_write_stale_pick_when_edit_wins_export_race(self):
        job = self.imported()
        picked = choose.decide(self.store, job, self.snapshot(job)['revision'], pick='C2', note='Pick before race.')
        export = self.store.export_result
        def race(*args):
            choose.edit(self.store, job, 'C2', 'hook', 'Concurrent edit before export.', picked['revision'])
            return export(*args)
        with patch.object(self.store, 'export_result', side_effect=race):
            with self.assertRaisesRegex(PipelineError, 'conflict before export'):
                choose.handoff(self.store, job, self.home / 'shared')
        self.assertFalse((self.home / 'shared').exists())

    def test_legacy_contract_and_explicit_abstention_stay_reviewable_without_inference(self):
        legacy = self.modified_trial(self.make_trial(contract=core.VERSION), 'legacy.json')
        self.assertTrue(self.snapshot(legacy)['validation']['valid'])
        trial = copy.deepcopy(self.trial)
        data = json.loads(trial['stages']['request']['body']['prompt'])
        proposal = {'status': 'no_supported_concept', 'input_identity': data['input_identity'],
                    'reason_ru': 'Недостаточно сведений для идеи.', 'missing_evidence_ru': ['Нет конкретного условия.'],
                    'reviewed_basis_claim_keys': ['help']}
        trial['stages']['proposal'] = proposal
        trial['stages']['model']['raw_response'] = stable_json(proposal)
        job = self.modified_trial(trial, 'abstained.json')
        view = self.snapshot(job)
        self.assertTrue(view['validation']['valid'])
        self.assertEqual(view['proposal'].get('concepts', []), [])
        with self.assertRaisesRegex(PipelineError, 'absent'):
            choose.decide(self.store, job, view['revision'], pick='C1', note='No such card.')
        choose.decide(self.store, job, view['revision'], reject_all=True, note='Согласен с отказом.')
        target = self.home / 'abstention.md'
        choose.export_markdown(self.store, job, target)
        self.assertIn(proposal['reason_ru'], target.read_text(encoding='utf-8'))
        self.assertIn(proposal['missing_evidence_ru'][0], target.read_text(encoding='utf-8'))

    def test_real_html_claim_context_is_reconstructed_and_retained_for_handoff(self):
        job = self.modified_trial(self.make_trial(source_context=True))
        view = self.snapshot(job)
        self.assertTrue(view['validation']['valid'], view['validation'])
        choose.decide(self.store, job, view['revision'], pick='C2', note='Synthetic HTML pick.')
        handoff = read_json(choose.handoff(self.store, job, self.home / 'shared')['handoff'])
        text = handoff['facts'][0]['source_context'][0]['text']
        self.assertIn('Rules differ by state', text)
        self.assertIn('excluded unless', text)

    def test_reported_approval_and_validation_cannot_authorize_invalid_result(self):
        variants = []
        hash_error = copy.deepcopy(self.trial)
        hash_error['stages']['request']['body_sha256'] = '0' * 64
        variants.append(hash_error)
        unknown_ref = copy.deepcopy(self.trial)
        unknown_ref['stages']['proposal']['concepts'][0]['basis_claim_keys'] = ['invented']
        unknown_ref['stages']['model']['raw_response'] = stable_json(unknown_ref['stages']['proposal'])
        variants.append(unknown_ref)
        bad_answer = copy.deepcopy(self.trial)
        bad_answer['stages']['model']['raw_response'] = '{not JSON'
        variants.append(bad_answer)
        for index, trial in enumerate(variants):
            trial['accepted_by_owner'] = True
            trial['stages']['validate'] = {'accepted': True, 'structure_and_known_claim_references_valid': True}
            job = self.modified_trial(trial, f'invalid-{index}.json')
            view = self.snapshot(job)
            self.assertEqual(view['state'], 'invalid_result')
            self.assertFalse(view['owner_approved'])
            self.assertTrue(view['trial']['accepted_by_owner'])  # kept as untrusted original data
            with self.assertRaisesRegex(PipelineError, 'structurally valid'):
                choose.decide(self.store, job, view['revision'], reject_all=True, note='Cannot authorize invalid data.')
        job = self.modified_trial({**self.trial, 'accepted_by_owner': True}, 'reported-pick.json')
        self.assertFalse(self.snapshot(job)['owner_approved'])

    def test_unknown_fields_invalid_edits_blank_notes_and_unknown_jobs_fail(self):
        job = self.imported()
        revision = self.snapshot(job)['revision']
        for field in ('id', 'basis_claim_keys', 'source_url', 'owner_approved'):
            with self.assertRaises(PipelineError):
                choose.edit(self.store, job, 'C2', field, 'Invented', revision)
        for value in ('', 'x' * 801):
            with self.assertRaises(PipelineError):
                choose.edit(self.store, job, 'C2', 'hook', value, revision)
        with self.assertRaises(PipelineError):
            choose.decide(self.store, job, revision, pick='C2', note='  ')
        for unknown in ('f' * 32, '../outside'):
            with self.assertRaises(PipelineError):
                choose.show(self.store, unknown)
        self.assertEqual(self.snapshot(job)['revision'], revision)

    def test_incomplete_model_result_cannot_be_repaired_into_approval_by_edit(self):
        trial = copy.deepcopy(self.trial)
        trial['state'] = 'output_truncated'
        trial['stages']['model']['done_reason'] = 'length'
        job = self.modified_trial(trial)
        view = self.snapshot(job)
        self.assertFalse(view['validation']['valid'])
        with self.assertRaisesRegex(PipelineError, 'incomplete'):
            choose.edit(self.store, job, 'C2', 'hook', 'Cannot bless a truncated run.', view['revision'])

    def test_existing_research_jobs_not_listed_or_repurposed(self):
        with self.store.connect() as conn:
            conn.execute('INSERT INTO jobs(id,request_json,state,created,updated) VALUES(?,?,?,?,?)', ('f' * 32, '{}', 'synthetic_test_only', 0, 0))
        job = self.imported()
        self.assertEqual([row['job_id'] for row in choose.list_jobs(self.store)], [job])
        with self.assertRaises(PipelineError):
            choose.show(self.store, 'f' * 32)

    def test_corrupt_revision_fails_without_overwriting_or_repairing_it(self):
        job = self.imported()
        first = self.snapshot(job)
        path = self.store.folder(job) / 'concept_results' / 'revisions' / (first['revision'] + '.json')
        raw = b'{"corrupt":true}\n'
        path.write_bytes(raw)
        with self.assertRaisesRegex(PipelineError, 'integrity'):
            self.snapshot(job)
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()

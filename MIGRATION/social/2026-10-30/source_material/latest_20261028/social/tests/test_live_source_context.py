"""Actual original producers with synthetic transports; never live API or models."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from socialreel import claims, concept_core as core, concept_admission as admission, grants, pipeline
from socialreel.common import PipelineError, sha256_bytes, stable_json
from tests.test_concept_offline import config, proposal
from tests.test_concept_source_cards import inspect_request


TODAY = dt.date(2026, 10, 28)


def fixture():
    hit = {'id': '101', 'title': 'Synthetic consistent identity', 'number': 'S-101',
           'oppStatus': 'posted', 'openDate': '10/01/2026', 'closeDate': '12/15/2026'}
    detail = {'id': 101, 'opportunityTitle': 'Synthetic consistent identity',
              'opportunityNumber': 'S-101', 'synopsis': {'awardCeiling': '1500000',
              'responseDate': '11/15/2026', 'applicantTypes': [{'description': 'Nonprofits'}],
              'synopsisDesc': 'This synthetic program helps nonprofit organizations develop local research partnerships. Only organizations located in State X may apply.',
              'applicantEligibilityDesc': 'Nonprofit organizations may submit applications for this synthetic opportunity. Organizations outside State X are not eligible.'}}
    search = {'file': '/private/source/search.json', 'sha256': 'a' * 64, 'fetched_at': '2026-10-27T00:00:00Z'}
    detail_meta = {'file': '/private/source/detail.json', 'sha256': 'b' * 64, 'fetched_at': '2026-10-28T00:00:00Z'}
    return hit, detail, search, detail_meta


def discover(hit, detail, search, detail_meta, *, second=None, forced=None):
    class FakeClient:
        def __init__(self, source):
            self.calls = []
        def search(self, keyword, rows, statuses):
            value, receipt = second if keyword == 'second' and second else (hit, search)
            self.calls.append(copy.deepcopy(receipt))
            return [copy.deepcopy(value)], copy.deepcopy(receipt)
        def detail(self, opportunity):
            self.calls.append(copy.deepcopy(detail_meta))
            return copy.deepcopy(detail), copy.deepcopy(detail_meta)
    cfg = {'search': {'keywords': ['synthetic', 'second'] if second else ['synthetic']},
           'selection': {'min_days_left': 7}}
    with patch.object(grants, 'GrantsGovClient', FakeClient):
        result = pipeline.discover_live(cfg, Path('/tmp/synthetic-not-created'), TODAY, set(), forced)
    return result


def record_and_claims(*args, **kwargs):
    result = discover(*(args or fixture()), **kwargs)
    _, record, snapshot = result[0][0]
    return record, claims.build_claims(record, snapshot, TODAY), snapshot


def leaves(source):
    return source.get('supporting_sources') or [source]


class LiveFieldProvenance(unittest.TestCase):
    def test_actual_discovery_assigns_search_and_detail_fields_their_receipts(self):
        record, rows, snapshot = record_and_claims()
        by = {row['key']: row for row in rows}
        for key in ('status', 'posted', 'deadline'):
            self.assertEqual(by[key]['source']['snapshot_sha256'], 'a' * 64)
            self.assertEqual(by[key]['observed_at'], '2026-10-27T00:00:00Z')
        self.assertEqual(by['deadline']['values']['date'], '2026-12-15')
        self.assertEqual(by['award_ceiling']['source']['snapshot_sha256'], 'b' * 64)
        self.assertEqual(by['award_ceiling']['observed_at'], '2026-10-28T00:00:00Z')
        self.assertEqual(snapshot['sha256'], 'b' * 64)  # Existing discover return shape.
        self.assertEqual(record['field_provenance']['status']['sha256'], 'a' * 64)

    def test_repeated_hit_keeps_the_receipt_of_the_retained_first_hit(self):
        hit, detail, search, meta = fixture()
        other = {**hit, 'oppStatus': 'closed', 'closeDate': '01/01/2027'}
        later = {**search, 'sha256': 'c' * 64, 'file': 'second.json', 'fetched_at': '2026-10-28T00:00:00Z'}
        result = discover(hit, detail, search, meta, second=(other, later))
        self.assertEqual(result[3], 1)
        _, rec, snap = result[0][0]
        by = {c['key']: c for c in claims.build_claims(rec, snap, TODAY)}
        self.assertEqual(by['status']['values']['status'], 'posted')
        self.assertEqual(by['status']['source']['snapshot_sha256'], search['sha256'])
        self.assertEqual(by['status']['observed_at'], search['fetched_at'])

    def test_mixed_identity_and_agency_keep_every_field_bound_and_report_shape(self):
        hit, detail, search, meta = fixture()
        detail.pop('opportunityNumber')
        hit['agency'] = 'Synthetic Research Office'
        detail['owningAgencyCode'] = 'DOJ-TEST'
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        by = {c['key']: c for c in rows}
        for key in ('identity', 'agency'):
            source = by[key]['source']
            self.assertEqual(source['kind'], 'multi_snapshot_fields')
            self.assertNotIn('snapshot_sha256', source)
            self.assertNotIn('observed_at', by[key])
            self.assertIsInstance(', '.join(source['fields']), str)  # Existing report reader.
        origins = {field: row['snapshot_sha256'] for row in leaves(by['identity']['source']) for field in row['fields']}
        self.assertEqual(origins['hit.number'], search['sha256'])
        self.assertEqual(origins['detail.opportunityTitle'], meta['sha256'])
        self.assertEqual(origins['detail.id'], meta['sha256'])
        origins = {field: row['snapshot_sha256'] for row in leaves(by['agency']['source']) for field in row['fields']}
        self.assertEqual(origins['hit.agency'], search['sha256'])
        self.assertEqual(origins['detail.owningAgencyCode'], meta['sha256'])
        self.assertEqual(origins['agency_code prefix map'], meta['sha256'])
        captured = inspect_request(rec, rows, config())
        body = captured['body']
        self.assertNotIn('snapshot_file', body['prompt'])
        self.assertNotIn('/private/', body['prompt'])
        projected = {r['claim_key']: r for r in json.loads(body['prompt'])['factual_core']}
        self.assertEqual(projected['identity']['source']['fields'], by['identity']['source']['fields'])
        self.assertEqual({s['snapshot_sha256'] for s in leaves(projected['identity']['source'])}, {search['sha256'], meta['sha256']})

    def test_run_does_not_retimestamp_search_claims_with_detail_or_build_clock(self):
        hit, detail, search, meta = fixture()
        discovered = discover(hit, detail, search, meta)
        class StopBeforeWriter(Exception):pass
        cfg = {'selection': {'min_days_left': 7}, 'search': {'keywords': ['synthetic']}}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(pipeline, 'discover_live', return_value=discovered), patch.object(pipeline, 'write_script', side_effect=StopBeforeWriter):
                with self.assertRaises(StopBeforeWriter):pipeline.run(cfg, Path(temporary))
            saved = json.loads(next(Path(temporary).rglob('claims.json')).read_text())
            by = {c['key']: c for c in saved['claims']}
            self.assertEqual(by['status']['observed_at'], search['fetched_at'])
            self.assertEqual(by['award_ceiling']['observed_at'], meta['fetched_at'])
        search.pop('fetched_at');meta.pop('fetched_at')
        _, rows, _ = record_and_claims(hit, detail, search, meta)
        self.assertTrue(all('observed_at' not in c for c in rows))

    def test_mismatched_ids_fail_direct_normalization_and_actual_discovery(self):
        hit, detail, search, meta = fixture()
        detail.update(id=202, opportunityTitle='Different record', opportunityNumber='D-202')
        with self.assertRaisesRegex(PipelineError, 'IDs differ'):grants.normalize(hit, detail)
        with self.assertRaisesRegex(PipelineError, 'IDs differ'):discover(hit, detail, search, meta)

    def test_numeric_string_ids_match_without_inventing_absent_ids(self):
        for left, right in ((101, '101'), ('101', 101), ('00101', 101), (' 101 ', 101)):
            with self.subTest(left=left, right=right):
                self.assertEqual(grants.normalize({'id': left}, {'id': right})['opportunity_id'], str(left).strip())
        self.assertEqual(grants.normalize({}, {'id': 101})['opportunity_id'], '101')
        self.assertEqual(grants.normalize({'id': 101}, {})['opportunity_id'], '101')
        self.assertEqual(grants.normalize({}, {})['opportunity_id'], '')
        for bad in (True, 101.0, [], {}):
            with self.subTest(bad=bad), self.assertRaises(PipelineError):grants.normalize({'id': bad}, {'id': 101})

    def test_forced_request_uses_actual_detail_id_not_fake_search_provenance(self):
        hit, detail, search, meta = fixture()
        result = discover(hit, detail, search, meta, forced='101')
        self.assertEqual(len(result[2]), 1)
        _, rec, snap = result[0][0]
        rows = claims.build_claims(rec, snap, TODAY)
        self.assertNotIn('status', {r['key'] for r in rows})
        self.assertEqual(rows[0]['source']['snapshot_sha256'], meta['sha256'])
        self.assertIn('detail.id', rows[0]['source']['fields'])
        self.assertEqual({r['key']: r for r in rows}['deadline']['values']['date'], '2026-11-15')

    def test_missing_tracked_field_provenance_never_falls_back_to_detail(self):
        rec, _, snap = record_and_claims()
        del rec['field_provenance']['status']
        with self.assertRaisesRegex(PipelineError, 'originating snapshot'):claims.build_claims(rec, snap, TODAY)
        hit, detail, _, meta = fixture()
        with self.assertRaisesRegex(PipelineError, 'originating snapshot'):
            grants.normalize(hit, detail, detail_snapshot=meta)

    def test_derived_top_agency_uses_code_receipt_when_display_name_is_rejected(self):
        hit, detail, search, meta = fixture()
        hit['agencyCode'] = 'DOJ-TEST'
        detail['topAgencyDetails'] = {'agencyName': 'Invalid\ncontact name'}
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        self.assertEqual(rec['fields']['top_agency'], 'agency_code prefix map')
        agency = next(r for r in rows if r['key'] == 'agency')
        self.assertEqual(agency['source']['snapshot_sha256'], search['sha256'])

    def test_real_connector_with_synthetic_transport_keeps_original_snapshot_bytes(self):
        hit, detail, _, _ = fixture()
        search_raw = json.dumps({'data': {'oppHits': [hit]}}, indent=2).encode() + b'\n'
        detail_raw = json.dumps({'data': detail}, ensure_ascii=False).encode() + b' \n'
        class Response:
            status = 200
            def __init__(self, raw):self.raw = raw
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read(self):return self.raw
        def transport(request, **kwargs):
            return Response(search_raw if request.full_url == grants.SEARCH_URL else detail_raw)
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(grants.urllib.request, 'urlopen', side_effect=transport), patch.object(grants.time, 'sleep'):
                result = pipeline.discover_live({'search': {'keywords': ['synthetic']}, 'selection': {'min_days_left': 7}}, Path(temporary), TODAY, set(), None)
            self.assertEqual((Path(temporary) / 'search_synthetic.json').read_bytes(), search_raw)
            self.assertEqual((Path(temporary) / 'opportunity_101.json').read_bytes(), detail_raw)
            _, rec, snap = result[0][0]
            by = {r['key']: r for r in claims.build_claims(rec, snap, TODAY)}
            self.assertEqual(by['status']['source']['snapshot_sha256'], sha256_bytes(search_raw))
            self.assertEqual(by['award_ceiling']['source']['snapshot_sha256'], sha256_bytes(detail_raw))

    def test_multi_snapshot_projection_rejects_missing_or_misattributed_bindings(self):
        source = {'kind': 'multi_snapshot_fields', 'fields': ['hit.title', 'detail.id'],
                  'supporting_sources': [{'fields': ['hit.title'], 'snapshot_sha256': 'a' * 64},
                                         {'fields': ['detail.id'], 'snapshot_sha256': 'b' * 64}]}
        core.project_source(source)
        for update in ({'snapshot_sha256': 'b' * 64}, {'supporting_sources': []}, {'fields': ['hit.title']},
                       {'supporting_sources': [source['supporting_sources'][0], {'quote': 'Unbound'}]}):
            with self.subTest(update=update), self.assertRaises(PipelineError):core.project_source({**source, **update})


class FullConditionContext(unittest.TestCase):
    def test_real_discovery_to_request_retains_both_second_sentence_conditions(self):
        record, rows, _ = record_and_claims()
        before = copy.deepcopy((record, rows))
        captured = inspect_request(record, rows, config())
        data = json.loads(captured['body']['prompt'])
        conditions = {r['field']: r for r in data['source_context']['condition_fields']}
        self.assertIn('Only organizations located in State X may apply.', conditions['description']['text'])
        self.assertIn('Organizations outside State X are not eligible.', conditions['applicant_eligibility_desc']['text'])
        for row in conditions.values():
            self.assertEqual(row['representation'], 'raw_source_field')
            self.assertEqual(row['source']['snapshot_sha256'], 'b' * 64)
            self.assertEqual(row['text_sha256'], sha256_bytes(row['text'].encode()))
            self.assertNotIn('snapshot_file', row['source'])
        self.assertTrue(all('source_context' not in row for row in data['factual_core']))
        self.assertNotIn('State X', next(c for c in rows if c['key'] == 'eligibility_note')['statement'])
        self.assertEqual(before, (record, rows))

    def test_original_html_unicode_and_whitespace_are_not_called_normalized_quotes(self):
        hit, detail, search, meta = fixture()
        raw = '<p>Nonprofits may apply.&nbsp;</p>\n<p>Исключение: State X only.</p>  '
        detail['synopsis']['applicantEligibilityDesc'] = raw
        record, rows, _ = record_and_claims(hit, detail, search, meta)
        self.assertNotEqual(record['applicant_eligibility_desc'], raw)
        captured = inspect_request(record, rows, config())
        context = json.loads(captured['body']['prompt'])['source_context']['condition_fields']
        value = next(r for r in context if r['field'] == 'applicant_eligibility_desc')
        self.assertEqual(value['text'], raw)
        self.assertEqual(value['text_sha256'], sha256_bytes(raw.encode()))
        self.assertNotIn('quote', value)
        self.assertIn('possibly HTML', captured['body']['system'])

    def test_full_context_survives_when_short_sentence_filter_returns_nothing(self):
        hit, detail, search, meta = fixture()
        detail['synopsis']['applicantEligibilityDesc'] = 'State X only.'
        detail['synopsis']['synopsisDesc'] = 'Excluded: outside State X.'
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        self.assertNotIn('eligibility_note', {r['key'] for r in rows})
        self.assertNotIn('purpose_quote', {r['key'] for r in rows})
        context = json.loads(inspect_request(rec, rows, config())['body']['prompt'])['source_context']['condition_fields']
        self.assertEqual({r['text'] for r in context}, {'State X only.', 'Excluded: outside State X.'})

    def test_legacy_normalized_fixture_stays_explicitly_normalized(self):
        row = {'normalized_facts': {'opportunity_id': '101', 'title': 'Synthetic', 'number': 'S-101',
                                   'description': 'Legacy normalized description. State X only.',
                                   'applicant_eligibility_desc': 'Not outside State X.'}}
        rec = grants.from_fixture(row)
        snap = {'file': 'fixture:synthetic.json', 'sha256': 'c' * 64}
        rows = claims.build_claims(rec, snap, TODAY)
        context = json.loads(inspect_request(rec, rows, config())['body']['prompt'])['source_context']['condition_fields']
        self.assertEqual({r['representation'] for r in context}, {'normalized_record_field'})
        self.assertEqual({r['source']['snapshot_sha256'] for r in context}, {'c' * 64})
        self.assertNotIn('field_provenance', rec)

    def test_context_byte_bound_is_explicit_aggregate_and_never_truncates(self):
        hit, detail, search, meta = fixture()
        detail['synopsis']['synopsisDesc'] = 'é' * (core.SOURCE_CONTEXT_BYTES // 2)
        detail['synopsis'].pop('applicantEligibilityDesc')
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        inputs = core.inputs(rec, rows, config())
        self.assertEqual(inputs['source_context']['condition_fields'][0]['text'], detail['synopsis']['synopsisDesc'])
        detail['synopsis']['applicantEligibilityDesc'] = 'X'
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        before = copy.deepcopy(rows)
        with patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, '8192 UTF-8 bytes; no clipping'):
            core.build_request(rec, rows, config())
        admit.assert_not_called()
        self.assertEqual(rows, before)

    def test_existing_request_envelope_still_fails_without_truncating_context(self):
        hit, detail, search, meta = fixture()
        detail['synopsis']['synopsisDesc'] = 'x' * core.SOURCE_CONTEXT_BYTES
        detail['synopsis'].pop('applicantEligibilityDesc')
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        body = inspect_request(rec, rows, config())['body']
        self.assertGreater(len(stable_json(body).encode()), admission.BASE_BYTES)
        with self.assertRaisesRegex(PipelineError, 'non_owner_envelope_exceeded'):
            admission.admit(body)
        self.assertEqual(json.loads(body['prompt'])['source_context']['condition_fields'][0]['text'], 'x' * core.SOURCE_CONTEXT_BYTES)

    def test_later_sentence_edits_change_identity_and_reject_stale_selection(self):
        hit, detail, search, meta = fixture()
        rec, rows, _ = record_and_claims(hit, detail, search, meta)
        cfg = config();cfg['concept_first']['result_contract'] = core.RESULT_V2
        first = inspect_request(rec, rows, cfg)
        detail['synopsis']['applicantEligibilityDesc'] = detail['synopsis']['applicantEligibilityDesc'].replace('State X', 'State Y')
        changed_rec, changed_rows, _ = record_and_claims(hit, detail, search, meta)
        second = inspect_request(changed_rec, changed_rows, cfg)
        self.assertNotEqual(first['inputs']['input_identity'], second['inputs']['input_identity'])
        self.assertNotEqual(first['inputs']['claims_identity'], second['inputs']['claims_identity'])
        cfg['concept_first']['selection'] = {'input_identity': first['inputs']['input_identity']}
        with patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, 'selection stale'):
            core.build_request(changed_rec, changed_rows, cfg)
        admit.assert_not_called()
        mutated = copy.deepcopy(first['inputs'])
        mutated['source_context']['condition_fields'][0]['text'] += ' changed'
        p = proposal();p['concepts'][0]['basis_claim_keys'] = ['identity']
        with self.assertRaisesRegex(PipelineError, 'input identity changed'):core.validate(p, mutated)

    def test_context_hash_shape_and_duplicate_fields_fail_closed(self):
        rec, rows, _ = record_and_claims()
        for change in ('hash', 'duplicate', 'representation', 'path_field'):
            corrupt = copy.deepcopy(rows)
            context = corrupt[0]['source_context']
            if change == 'hash':context[0]['text'] += ' invented'
            elif change == 'duplicate':context[1] = copy.deepcopy(context[0])
            elif change == 'representation':context[0]['representation'] = 'verified_quote'
            else:context[0]['field'] = '/private/path'
            with self.subTest(change=change), self.assertRaises(PipelineError):core.inputs(rec, corrupt, config())

    def test_saved_claims_without_full_context_require_rebuild_not_silent_loss(self):
        rec, rows, _ = record_and_claims()
        for row in rows:row.pop('source_context', None)
        with patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, 'saved claims omit full source conditions; rebuild required'):
            core.build_request(rec, rows, config())
        admit.assert_not_called()

    def test_changed_record_text_cannot_rebind_stale_claim_context(self):
        original, rows, _ = record_and_claims()
        for change in ('both', 'normalized_only', 'raw_only', 'empty_raw'):
            rec = copy.deepcopy(original)
            if change in ('both', 'normalized_only'):
                rec['applicant_eligibility_desc'] = rec['applicant_eligibility_desc'].replace('State X', 'State Y')
            if change in ('both', 'raw_only'):
                rec['source_text_fields']['applicant_eligibility_desc'] = rec['source_text_fields']['applicant_eligibility_desc'].replace('State X', 'State Y')
            if change == 'empty_raw':rec['source_text_fields']['applicant_eligibility_desc'] = ''
            with self.subTest(change=change), patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, 'rebuild required'):
                core.build_request(rec, rows, config())
            admit.assert_not_called()

    def test_changed_condition_receipt_or_locator_requires_rebuild(self):
        original, rows, _ = record_and_claims()
        for change in ('sha256', 'fetched_at', 'locator'):
            rec = copy.deepcopy(original)
            if change == 'locator':rec['fields']['applicant_eligibility_desc'] = 'forecast.applicantEligibilityDesc'
            else:rec['field_provenance']['applicant_eligibility_desc'][change] = 'c' * 64 if change == 'sha256' else '2026-10-29T00:00:00Z'
            with self.subTest(change=change), self.assertRaisesRegex(PipelineError, 'provenance differs from record; rebuild required'):
                core.build_request(rec, rows, config())

    def test_rebuilt_rows_cannot_hide_nonempty_normalized_text_behind_empty_raw(self):
        original, _, snapshot = record_and_claims()
        for empty in ('', None):
            rec = copy.deepcopy(original)
            rec['source_text_fields']['applicant_eligibility_desc'] = empty
            rows = claims.build_claims(rec, snapshot, TODAY)
            with self.subTest(empty=empty), patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, 'record/source condition text differs; rebuild required'):
                core.build_request(rec, rows, config())
            admit.assert_not_called()


if __name__ == '__main__':unittest.main(verbosity=2)

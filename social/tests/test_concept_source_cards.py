"""Synthetic structured-source and exact-text regressions; no model execution."""
import copy
import datetime as dt
import json
import unittest
from unittest.mock import patch

from socialreel import concept_admission as admission
from socialreel import concept_core as core
from socialreel.claims import build_claims
from socialreel.common import PipelineError, sha256_bytes
from socialreel.grants import normalize
from socialreel.json_contract import validate_node
from tests.test_concept_offline import config, claims, proposal


class StoppedBeforeAdmission(Exception):
    pass


def inspect_request(record, claim_rows, cfg):
    """Observe the real builder, then raise: never simulate admitted success."""
    captured = {}
    original_inputs = core.inputs

    def observe(*args, **kwargs):
        value = original_inputs(*args, **kwargs)
        captured['inputs'] = value
        return value

    def stop(body):
        captured['body'] = copy.deepcopy(body)
        raise StoppedBeforeAdmission('No tokenizer success, dispatch or model run')

    with patch.object(core, 'inputs', side_effect=observe), patch.object(admission, 'admit', side_effect=stop):
        try:
            core.build_request(record, claim_rows, cfg)
        except StoppedBeforeAdmission:
            return captured
    raise AssertionError('Builder did not reach the inspection boundary')


def structured_claims():
    record = normalize({'id': '999', 'agencyCode': 'DOJ-TEST', 'oppStatus': 'posted'}, {
        'opportunityTitle': 'Synthetic field provenance',
        'opportunityNumber': 'SYN-999',
        'synopsis': {'awardCeiling': '1200', 'costSharing': 'Yes',
                     'applicantTypes': [{'description': 'Nonprofit organizations'}]}})
    snapshot = {'file': '/private/synthetic/opportunity.json',
                'sha256': sha256_bytes(b'Synthetic identity only; not a captured source')}
    return record, build_claims(record, snapshot, dt.date(2026, 10, 25))


class StructuredSourceRequest(unittest.TestCase):
    def test_real_normalizer_claims_builder_preserves_fields_and_snapshot(self):
        record, rows = structured_claims()
        cfg = config()
        before = copy.deepcopy((record, rows, cfg))
        captured = inspect_request(record, rows, cfg)
        prompt = json.loads(captured['body']['prompt'])
        for original, projected in zip(rows, prompt['factual_core']):
            with self.subTest(key=original['key']):
                self.assertEqual(projected['source']['fields'], original['source']['fields'])
                self.assertEqual(projected['source']['snapshot_sha256'], original['source']['snapshot_sha256'])
                self.assertEqual(projected['source']['source_identity'], core.digest(original['source']))
                self.assertEqual(projected['values'], original['values'])
                self.assertEqual(projected['statement'], original['statement'])
                self.assertNotIn('quote', projected['source'])
                self.assertNotIn('snapshot_file', projected['source'])
        self.assertEqual(captured['inputs']['claims_identity'], core.digest(rows))
        self.assertEqual(prompt['input_identity'], captured['inputs']['input_identity'])
        self.assertNotIn('/private/synthetic', captured['body']['prompt'])
        self.assertEqual(before, (record, rows, cfg))

    def test_prompt_distinguishes_locators_values_quotes_and_identity(self):
        record, rows = structured_claims()
        for contract in (core.VERSION, core.RESULT_V2):
            cfg = config()
            cfg['concept_first']['result_contract'] = contract
            system = inspect_request(record, rows, cfg)['body']['system']
            self.assertIn('source.fields are field locators, not quotes', system)
            self.assertIn('normalized values, not verbatim source text', system)
            self.assertIn('derived mapping rule, not a direct source field', system)
            self.assertIn('Snapshot hashes bind identity only', system)
            self.assertIn('do not verify source contents, currentness or factual support', system)

    def test_supported_normalized_locator_vocabularies_stay_exact(self):
        values = ['detail.opportunityTitle', 'hit.number', 'synopsis.awardCeiling',
                  'forecast.responseDate', 'supabase_export.normalized_facts.title',
                  'title', 'agency_code prefix map']
        source = {'fields': values, 'snapshot_sha256': 'a' * 64}
        result = core.project_source(source)
        self.assertEqual(result['fields'], values)
        self.assertIsNot(result['fields'], values)

    def test_locator_count_and_length_boundaries_no_clipping(self):
        source = {'fields': ['x' * 240] * 16, 'snapshot_sha256': 'a' * 64}
        result = core.project_source(source)
        self.assertEqual(result['fields'], source['fields'])
        for values in (['x'] * 17, ['x' * 241]):
            with self.subTest(values=values), self.assertRaisesRegex(PipelineError, 'locators invalid or exceed bound'):
                core.project_source({**source, 'fields': values})

    def test_bad_types_blank_paths_and_nested_locators_fail_closed(self):
        bad = [None, {}, 'detail.title', [], [None], [True], [3], [{}], [['detail.title']],
               [''], [' '], ['x\ny'], ['/private/source.json'], ['C:\\private\\source.json'],
               ['file:///private/source.json'], ['../source.json'], ['a..b'], ['\\\\host\\share']]
        for value in bad:
            with self.subTest(value=value), self.assertRaisesRegex(PipelineError, 'locators invalid or exceed bound'):
                core.project_source({'fields': value, 'snapshot_sha256': 'a' * 64})

    def test_structured_fields_require_typed_snapshot_identity(self):
        for value in (None, False, 123, {}, '', 'a' * 63, 'a' * 65, 'g' * 64, 'A' * 64):
            with self.subTest(value=value), self.assertRaisesRegex(PipelineError, 'snapshot SHA256 identity'):
                core.project_source({'fields': ['detail.title'], 'snapshot_sha256': value})
        with self.assertRaisesRegex(PipelineError, 'snapshot SHA256 identity'):
            core.project_source({'fields': ['detail.title']})

    def test_invalid_structured_source_rejected_before_admission(self):
        record, rows = structured_claims()
        for field, value in (('fields', ['/private/source']), ('snapshot_sha256', None)):
            invalid = copy.deepcopy(rows)
            invalid[0]['source'][field] = value
            with patch.object(admission, 'admit') as admit, self.assertRaises(PipelineError):
                core.build_request(record, invalid, config())
            admit.assert_not_called()

    def test_path_omission_still_binds_full_original_source(self):
        record, rows = structured_claims()
        first = inspect_request(record, rows, config())
        rows[0]['source']['snapshot_file'] = '/private/other/snapshot.json'
        second = inspect_request(record, rows, config())
        one = json.loads(first['body']['prompt'])['factual_core'][0]['source']
        two = json.loads(second['body']['prompt'])['factual_core'][0]['source']
        self.assertNotEqual(one['source_identity'], two['source_identity'])
        self.assertNotEqual(first['inputs']['input_identity'], second['inputs']['input_identity'])
        self.assertEqual(one['snapshot_sha256'], two['snapshot_sha256'])
        self.assertNotIn('/private/', second['body']['prompt'])

    def test_structured_source_edits_invalidate_selection_and_v2_identity(self):
        record, original = structured_claims()
        cfg = config()
        cfg['concept_first']['result_contract'] = core.RESULT_V2
        captured = inspect_request(record, original, cfg)
        data = captured['inputs']
        p = proposal()
        p['concepts'][0]['basis_claim_keys'] = [original[0]['key']]
        self.assertEqual(core.validate(p, data)['result_state'], 'concepts_proposed')
        for field, value in (('fields', ['hit.title']), ('snapshot_sha256', 'b' * 64)):
            changed = copy.deepcopy(original)
            changed[0]['source'][field] = value
            stale = copy.deepcopy(cfg)
            stale['concept_first']['selection'] = {'input_identity': data['input_identity']}
            with patch.object(admission, 'admit') as admit, self.assertRaisesRegex(PipelineError, 'selection stale'):
                core.build_request(record, changed, stale)
            admit.assert_not_called()
            changed_data = copy.deepcopy(data)
            changed_data['factual_core'][0]['source'][field] = value
            with self.assertRaisesRegex(PipelineError, 'input identity changed'):
                core.validate(p, changed_data)

    def test_mixed_and_supporting_evidence_keep_quotes_exact_without_path(self):
        quote = 'Synthetic organizations may apply; conditions remain unknown.'
        source = {'fields': ['synopsis.synopsisDesc'], 'snapshot_sha256': 'a' * 64,
                  'snapshot_file': '/private/source.json', 'quote': quote,
                  'excerpt_sha256': sha256_bytes(quote.encode()),
                  'supporting_sources': [{'fields': ['detail.title'], 'snapshot_sha256': 'b' * 64,
                                          'snapshot_file': '/private/support.json'}]}
        before = copy.deepcopy(source)
        result = core.project_source(source)
        self.assertEqual(result['quote'], quote)
        self.assertEqual(result['supporting_sources'][0]['fields'], ['detail.title'])
        self.assertEqual(result['supporting_sources'][0]['snapshot_sha256'], 'b' * 64)
        self.assertNotIn('/private/', json.dumps(result))
        self.assertEqual(source, before)
        source['quote'] += ' invented'
        with self.assertRaisesRegex(PipelineError, 'quote/hash mismatch'):
            core.project_source(source)

    def test_quote_only_legacy_source_needs_no_invented_fields_or_snapshot(self):
        source = claims()[0]['source']
        result = core.project_source(source)
        self.assertEqual(result['quote'], source['quote'])
        self.assertNotIn('fields', result)
        self.assertNotIn('snapshot_sha256', result)


class CardTextValidation(unittest.TestCase):
    TEXT_FIELDS = ('viewer_question_ru', 'angle_ru', 'what_viewer_learns_ru', 'not_answered_ru', 'hook')

    def inputs(self, contract):
        cfg = config()
        cfg['concept_first']['result_contract'] = contract
        rows = claims()
        rows.append({**copy.deepcopy(rows[0]), 'key': 'second_known_reference'})
        data = core.inputs({}, rows, cfg)
        if contract == core.RESULT_V2:
            data['input_identity'] = core.digest(data)
        return data

    def test_each_text_field_rejects_blank_in_both_contracts_without_repair(self):
        for contract in (core.VERSION, core.RESULT_V2):
            data = self.inputs(contract)
            for field in self.TEXT_FIELDS:
                for blank in ('', ' ', '\t\n\r', '\u00a0\u2003\u202f'):
                    p = proposal()
                    p['concepts'][0][field] = blank
                    before = copy.deepcopy(p)
                    with self.subTest(contract=contract, field=field, blank=blank), self.assertRaises(PipelineError):
                        core.validate(p, data)
                    self.assertEqual(p, before)

    def test_all_five_whitespace_fields_rejected(self):
        p = proposal()
        p['concepts'][0].update({field: ' \n\t' for field in self.TEXT_FIELDS})
        for contract in (core.VERSION, core.RESULT_V2):
            with self.assertRaises(PipelineError):
                core.validate(p, self.inputs(contract))

    def test_generated_schema_enforces_nonblank_in_both_reference_modes(self):
        for contract in (core.VERSION, core.RESULT_V2):
            for reference in ('basis_claim_keys', 'basis_excerpt_ids'):
                schema = core.schema(['synthetic_source'], reference_field=reference,
                                     result_contract=contract, input_identity='a' * 64)
                p = proposal()
                p['concepts'][0][reference] = p['concepts'][0].pop('basis_claim_keys')
                validate_node(schema, p)
                for field in self.TEXT_FIELDS:
                    invalid = copy.deepcopy(p)
                    invalid['concepts'][0][field] = '\u2003\n'
                    with self.subTest(contract=contract, reference=reference, field=field), self.assertRaises(ValueError):
                        validate_node(schema, invalid)

    def test_duplicate_text_with_different_ids_is_diagnosed_without_repair(self):
        for contract in (core.VERSION, core.RESULT_V2):
            p = proposal()
            p['concepts'].append({**copy.deepcopy(p['concepts'][0]), 'id': 'C2'})
            before = copy.deepcopy(p)
            with self.assertRaisesRegex(PipelineError, 'exact text-content duplicate: C2 repeats C1'):
                core.validate(p, self.inputs(contract))
            self.assertEqual(p, before)

    def test_different_citations_do_not_hide_identical_text(self):
        p = proposal()
        p['concepts'].append({**copy.deepcopy(p['concepts'][0]), 'id': 'C2',
                              'basis_claim_keys': ['second_known_reference']})
        for contract in (core.VERSION, core.RESULT_V2):
            with self.assertRaisesRegex(PipelineError, 'different IDs or references'):
                core.validate(p, self.inputs(contract))

    def test_nonadjacent_duplicate_is_diagnosed(self):
        p = proposal()
        p['concepts'].append({**copy.deepcopy(p['concepts'][0]), 'id': 'C2', 'hook': 'Another hook'})
        p['concepts'].append({**copy.deepcopy(p['concepts'][0]), 'id': 'C3'})
        with self.assertRaisesRegex(PipelineError, 'C3 repeats C1'):
            core.validate(p, self.inputs(core.VERSION))

    def test_nonblank_bytes_preserved_and_one_field_difference_not_quality_proof(self):
        for contract in (core.VERSION, core.RESULT_V2):
            p = proposal()
            p['concepts'][0]['hook'] = '  Synthetic hook\n'
            p['concepts'].append({**copy.deepcopy(p['concepts'][0]), 'id': 'C2', 'hook': 'Synthetic hook'})
            before = copy.deepcopy(p)
            result = core.validate(p, self.inputs(contract))
            self.assertEqual(p, before)
            for flag in ('quality_verified', 'semantic_entailment_verified', 'distinctness_verified',
                         'audience_interest_measured', 'language_verified'):
                self.assertFalse(result[flag])

    def test_abstention_stays_non_success_and_legacy_shape_unchanged(self):
        data = self.inputs(core.RESULT_V2)
        value = {'status': 'no_supported_concept', 'input_identity': data['input_identity'],
                 'reason_ru': 'Нет достаточных сведений.', 'missing_evidence_ru': ['Условия неизвестны.'],
                 'reviewed_basis_claim_keys': ['synthetic_source']}
        result = core.validate(value, data)
        self.assertEqual(result['concept_count'], 0)
        self.assertEqual(result['result_state'], 'no_supported_concept')
        self.assertFalse(result['accepted'])
        self.assertNotIn('oneOf', core.schema(['synthetic_source']))
        self.assertEqual(set(core.schema(['synthetic_source'])['properties']), {'concepts'})
        with self.assertRaises(PipelineError):
            core.validate(value, self.inputs(core.VERSION))


if __name__ == '__main__':
    unittest.main(verbosity=2)

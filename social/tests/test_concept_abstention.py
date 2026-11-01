"""Opt-in result-contract tests; request inspection stops before token admission."""
import copy
import unittest
from unittest.mock import patch
from socialreel import concept_core as core
from socialreel import concept_admission as admission
from socialreel import source_excerpt_projection as projection
from socialreel import source_excerpt_model_view as views
from socialreel.common import PipelineError,sha256_bytes
from tests.test_concept_offline import config, claims, proposal, synthetic_pdf


class StoppedBeforeAdmission(Exception):pass


class AbstentionContract(unittest.TestCase):
    def inputs(self):
        cfg=config();cfg['concept_first']['result_contract']=core.RESULT_V2
        data=core.inputs({'title':'Synthetic'},claims(),cfg)
        data['input_identity']=core.digest(data)
        return data

    def abstention(self,data,excerpt=False):
        return {'status':'no_supported_concept','input_identity':data['input_identity'],
                'reason_ru':'Источник не устанавливает ответ на вопрос.',
                'missing_evidence_ru':['Нет сведений о конкретном условии.'],
                ('reviewed_basis_excerpt_ids' if excerpt else 'reviewed_basis_claim_keys'):
                  [data['source_evidence']['excerpts'][0][0]] if excerpt else ['synthetic_source']}

    def test_existing_default_shape_remains_identical(self):
        data=core.inputs({},claims(),config());self.assertNotIn('result_contract',data)
        result=core.validate(proposal(),data);self.assertNotIn('result_state',result)
        self.assertNotIn('oneOf',core.schema(['synthetic_source']))
        with self.assertRaises(PipelineError):core.validate(self.abstention(self.inputs()),data)

    def test_opt_in_preserves_supported_cards(self):
        data=self.inputs();p=proposal();before=copy.deepcopy(p)
        result=core.validate(p,data)
        self.assertEqual(result['result_state'],'concepts_proposed');self.assertEqual(result['concept_count'],1)
        self.assertFalse(result['accepted']);self.assertFalse(result['quality_verified']);self.assertEqual(before,p)

    def test_abstention_is_explicit_non_success(self):
        data=self.inputs();result=core.validate(self.abstention(data),data)
        self.assertEqual(result['result_state'],'no_supported_concept');self.assertEqual(result['concept_count'],0)
        self.assertFalse(result['accepted']);self.assertFalse(result['quality_verified']);self.assertFalse(result['semantic_entailment_verified'])

    def test_empty_or_mixed_shapes_fail_closed(self):
        data=self.inputs()
        for p in [{'concepts':[]},{**self.abstention(data),'concepts':[]}, {'status':'no_supported_concept'}, {'concepts':proposal()['concepts'],'status':'no_supported_concept'}]:
            with self.subTest(p=p),self.assertRaises(PipelineError):core.validate(p,data)

    def test_reason_gaps_and_reviewed_refs_bounded(self):
        data=self.inputs();base=self.abstention(data)
        for key,value in [('reason_ru',''),('reason_ru',' '*3),('reason_ru','x'*801),('missing_evidence_ru',[]),('missing_evidence_ru',[' ']),('missing_evidence_ru',['x']*9),('reviewed_basis_claim_keys',[]),('reviewed_basis_claim_keys',['unknown']),('reviewed_basis_claim_keys',['synthetic_source']*2)]:
            with self.subTest(key=key,value=value),self.assertRaises(PipelineError):core.validate({**base,key:value},data)

    def test_wrong_result_identity_or_mutated_source_rejected(self):
        data=self.inputs();p=self.abstention(data)
        with self.assertRaises(PipelineError):core.validate({**p,'input_identity':'0'*64},data)
        data['factual_core'][0]['source']['quote']+=' altered'
        with self.assertRaisesRegex(PipelineError,'input identity changed'):core.validate(p,data)

    def test_unknown_contract_rejected_without_implicit_upgrade(self):
        cfg=config();cfg['concept_first']['result_contract']='future'
        with self.assertRaisesRegex(PipelineError,'Unknown concept result contract'):core.inputs({},claims(),cfg)
        data=self.inputs();data['result_contract']='future'
        with self.assertRaises(PipelineError):core.validate(proposal(),data)

    def capture_builder(self,cfg,record=None,claim_rows=None,bundle=None):
        captured={};original_inputs=core.inputs
        def observe_inputs(*a,**k):
            data=original_inputs(*a,**k);captured['inputs']=data;return data
        def stop(body):
            captured['body']=copy.deepcopy(body)
            raise StoppedBeforeAdmission('Inspection only; no token count or admitted request')
        with patch.object(core,'inputs',side_effect=observe_inputs),patch.object(admission,'admit',side_effect=stop):
            with self.assertRaises(StoppedBeforeAdmission):core.build_request(record or {},claims() if claim_rows is None else claim_rows,cfg,source_evidence=bundle)
        return captured

    def test_actual_builder_supplies_copyable_identity_and_scope_prompt(self):
        cfg=config();cfg['concept_first']['result_contract']=core.RESULT_V2
        result=self.capture_builder(cfg);data=result['inputs'];body=result['body']
        import json
        self.assertEqual(json.loads(body['prompt'])['input_identity'],data['input_identity'])
        self.assertEqual(body['format']['oneOf'][1]['properties']['input_identity']['const'],data['input_identity'])
        self.assertEqual(core.validate(self.abstention(data),data)['result_state'],'no_supported_concept')
        self.assertIn('conditions, exceptions',body['system']);self.assertIn('historical scope',body['system'])
        self.assertTrue(body['system'].startswith('Return one to three useful concept options only if'))
        self.assertIn('otherwise return the explicit no_supported_concept result',body['system'])
        self.assertIn('expected outcomes do not establish measured effects or causation',body['system'])
        self.assertIn('questions and hooks must not presuppose that they do',body['system'])
        legacy=self.capture_builder(config())['body']
        self.assertTrue(legacy['system'].startswith('Develop one to three'))
        self.assertNotIn('oneOf',legacy['format'])

    def test_actual_excerpt_projection_binding_and_abstention(self):
        raw=synthetic_pdf();record={'title':'Synthetic Opportunity','number':'SYN-001'}
        receipt={'url':'https://ojp.gov/synthetic-test.pdf','fetched_at':'2020-01-01T00:00:00+00:00','sha256':sha256_bytes(raw),'bytes':len(raw)}
        intent={'profile':projection.PROFILE,'audience':'organizational_applicants','topic':'program_purpose','source_title':record['title']}
        result=projection.project(raw,receipt,record,intent,full_input={});self.assertEqual(result['state'],'projected')
        ledger=result['packet'];bundle={'ledger':ledger,**views.compact(ledger)}
        cfg=config();cfg['selection']={'audience':'organizational_applicants'}
        cfg['concept_first'].update(result_contract=core.RESULT_V2,evidence_mode='excerpts',evidence_ledger_sha256=views.sha(ledger))
        captured=self.capture_builder(cfg,record,[],bundle);data=captured['inputs'];value=self.abstention(data,True)
        self.assertEqual(core.validate(value,data,source_evidence=bundle)['result_state'],'no_supported_concept')
        self.assertIn('reviewed_basis_excerpt_ids',captured['body']['system'])
        corrupt=copy.deepcopy(bundle);corrupt['view']['excerpts'][0][-1]+=' changed'
        with self.assertRaises(PipelineError):core.validate(value,data,source_evidence=corrupt)

    def test_missing_tokenizer_still_blocks_opt_in_builder(self):
        cfg=config();cfg['concept_first']['result_contract']=core.RESULT_V2
        with self.assertRaisesRegex(PipelineError,'no model request'):core.build_request({},claims(),cfg)


if __name__=='__main__':unittest.main(verbosity=2)

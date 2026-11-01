"""Synthetic offline core tests. No live source, model, UI, or quality claims."""
import copy
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from socialreel.common import PipelineError, read_json, sha256_bytes, stable_json
from socialreel import concept_core as core
from socialreel import concept_owner_context as owner
from socialreel import concept_decision_ledger as decisions
from socialreel import concept_admission as admission
from socialreel import source_excerpt_projection as projection
from socialreel import source_excerpt_model_view as views
from socialreel.concept_locks import motion_lock, MutationBusy
from socialreel.concept_storage import write_json
from socialreel.concept_store import ConceptStore


def config():
    return {'writer':'ollama','local_editorial':{'enabled':True,'execution_authorized':True},
            'concept_first':{'enabled':True,'brief':{'hook_language':'en'},
                             'topic_direction':'Explain the synthetic source','unknowns':['Eligibility is unknown']}}


def claims():
    quote='Synthetic organizations may apply.'
    return [{'key':'synthetic_source','statement':quote,'source':{'quote':quote,'excerpt_sha256':sha256_bytes(quote.encode())}}]


def proposal():
    return {'concepts':[{'id':'C1','viewer_question_ru':'Вопрос','angle_ru':'Подход',
                         'what_viewer_learns_ru':'Содержание','basis_claim_keys':['synthetic_source'],
                         'not_answered_ru':'Неизвестное','hook':'Synthetic hook'}]}


class ConceptCore(unittest.TestCase):
    def test_inputs_preserve_sources_and_unverified_owner(self):
        cfg=config();cfg['concept_first']['owner_context']={'scope':owner.SCOPE,'owner_approval':False,'source_evidence':False,'context':{'audience':'Synthetic'}}
        rec={'title':'Synthetic'};c=claims();before=copy.deepcopy((rec,c,cfg))
        result=core.inputs(rec,c,cfg)
        self.assertEqual((rec,c,cfg),before)
        self.assertFalse(result['owner_context']['owner_approval'])
        self.assertEqual(result['factual_core'][0]['source'],c[0]['source'])

    def test_owner_cannot_become_evidence_or_approval(self):
        for field in ['owner_approval','source_evidence']:
            cfg=config();cfg['concept_first']['owner_context']={'scope':owner.SCOPE,'owner_approval':False,'source_evidence':False,field:True}
            with self.assertRaises(PipelineError):core.inputs({},claims(),cfg)

    def test_duplicate_claims_rejected(self):
        with self.assertRaises(PipelineError):core.inputs({},claims()*2,config())

    def test_language_never_inferred(self):
        cfg=config();cfg['concept_first']['brief']={}
        self.assertEqual(core.language_contract(cfg)['state'],'unresolved')
        with self.assertRaisesRegex(PipelineError,'Hook language unresolved'):core.build_request({},claims(),cfg)

    def test_structural_validation_is_not_quality_proof(self):
        result=core.validate(proposal(),core.inputs({},claims(),config()))
        self.assertTrue(result['structure_and_known_claim_references_valid'])
        for key in ['quality_verified','semantic_entailment_verified','language_verified','distinctness_verified','audience_interest_measured']:self.assertFalse(result[key])

    def test_unknown_reference_and_duplicate_card_rejected(self):
        p=proposal();p['concepts'][0]['basis_claim_keys']=['missing']
        with self.assertRaises(PipelineError):core.validate(p,core.inputs({},claims(),config()))
        p=proposal();p['concepts']*=2
        with self.assertRaises(PipelineError):core.validate(p,core.inputs({},claims(),config()))

    def test_source_hash_and_no_clipping_bounds(self):
        source=claims()[0]['source'];self.assertEqual(core.project_source(source)['quote'],source['quote'])
        source['quote']+=' changed'
        with self.assertRaises(PipelineError):core.project_source(source)
        with self.assertRaises(PipelineError):core.project_source({'supporting_sources':[{}]*17})

    def test_missing_tokenizer_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(admission,'ASSETS',Path(tmp)):
            with self.assertRaisesRegex(PipelineError,'no model request'):core.build_request({},claims(),config())

    def test_resource_contract_rejected_before_tokenizer(self):
        with self.assertRaisesRegex(PipelineError,'unknown_model_or_mode'):admission.admit({'model':'other'})

    def test_hold_and_spend_block_request(self):
        for change in [{'generation_hold':True},{'llm':{'allow_spend':True}}]:
            cfg=config();cfg.update(change)
            with self.assertRaisesRegex(PipelineError,'policy/hold'):core.build_request({},claims(),cfg)

    def test_topic_mismatch_no_substitute(self):
        cfg=config();cfg['selection']={'public_reference_topic':'energy'}
        with self.assertRaises(PipelineError):core.inputs({'public_reference_topic':'wages'},claims(),cfg)


class OwnedStore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ConceptStore(Path(self.tmp.name)/'owned');self.job='a'*32
        with self.store.connect() as conn:conn.execute('INSERT INTO jobs(id,request_json,state,created,updated) VALUES(?,?,?,?,?)',(self.job,'{}','synthetic_test_only',0,0))

    def test_context_revision_and_conflict(self):
        self.assertEqual(owner.read(self.store,self.job)['revision'],'absent')
        first=owner.save(self.store,self.job,'absent',{'audience':'Synthetic audience'})
        self.assertFalse(first['owner_approval']);self.assertFalse(first['source_evidence'])
        with self.assertRaisesRegex(PipelineError,'conflict'):owner.save(self.store,self.job,'absent',{'audience':'stale'})
        second=owner.save(self.store,self.job,first['revision'],{'audience':'Revised'})
        self.assertEqual(second['parent_revision'],first['revision'])
        self.assertEqual(owner.read(self.store,self.job),second)
        self.assertTrue((self.store.folder(self.job)/'concept_owner_context/revisions'/ (first['revision']+'.json')).is_file())

    def test_context_tampering_fails_closed(self):
        saved=owner.save(self.store,self.job,'absent',{'audience':'Synthetic'})
        path=self.store.folder(self.job)/'concept_owner_context/revisions'/(saved['revision']+'.json')
        value=read_json(path);value['context']['audience']='tampered';write_json(path,value)
        with self.assertRaisesRegex(PipelineError,'integrity'):owner.read(self.store,self.job)

    def test_context_limits_and_unknown_fields(self):
        for bad in [{'audience':'x'*1001},{'owner_approval':'true'},{'audience':True}]:
            with self.assertRaises(PipelineError):owner.save(self.store,self.job,'absent',bad)
        self.assertEqual(owner.read(self.store,self.job)['revision'],'absent')

    def test_unknown_job_and_traversal_rejected(self):
        with self.assertRaises(PipelineError):owner.read(self.store,'b'*32)
        for job in ['../outside','A'*32,'a'*31]:
            with self.assertRaises(PipelineError):self.store.folder(job)

    def test_store_requires_explicit_root(self):
        with self.assertRaises(TypeError):ConceptStore()

    def test_atomic_failed_replace_preserves_original(self):
        p=Path(self.tmp.name)/'atomic.json';write_json(p,{'original':True})
        with patch('socialreel.concept_storage.os.replace',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):write_json(p,{'replacement':True})
        self.assertEqual(read_json(p),{'original':True});self.assertEqual(list(p.parent.glob('*.partial')),[])

    def test_lock_conflict_and_release(self):
        with motion_lock(self.store.root,'synthetic'):
            with self.assertRaises(MutationBusy):
                with motion_lock(self.store.root,'synthetic'):pass
        with motion_lock(self.store.root,'synthetic'):pass

    def event(self,parent='absent',key=None):
        key=key or uuid.uuid4().hex
        event={'job_id':self.job,'scope':'editorial_choice_only','approved':False,'request_id':key,'parent_revision':parent,'selected':None}
        home=self.store.folder(self.job)/'concept_decisions'
        write_json(home/'events'/(key+'.json'),event)
        revision=decisions.digest(event);write_json(home/'head.json',{'revision':revision})
        return home,revision,event

    def test_ledger_chain_read_only(self):
        _,first,_=self.event();home,second,_=self.event(first)
        before={p.name:p.read_bytes() for p in home.rglob('*.json')}
        _,head,history,requests=decisions.ledger(self.store,self.job)
        self.assertEqual(head,second);self.assertEqual([e['revision'] for e in history],[second,first]);self.assertEqual(len(requests),2)
        self.assertEqual(before,{p.name:p.read_bytes() for p in home.rglob('*.json')})

    def test_ledger_uncommitted_event_not_auto_retried(self):
        home,revision,_=self.event();self.event(revision);write_json(home/'head.json',{'revision':revision})
        with self.assertRaisesRegex(PipelineError,'Uncommitted'):decisions.ledger(self.store,self.job)

    def test_ledger_approval_escalation_rejected(self):
        home,_,event=self.event();event['approved']=True;write_json(home/'events'/(event['request_id']+'.json'),event)
        with self.assertRaisesRegex(PipelineError,'integrity'):decisions.ledger(self.store,self.job)

    def test_ledger_broken_parent_rejected(self):
        self.event('missing')
        with self.assertRaisesRegex(PipelineError,'chain integrity'):decisions.ledger(self.store,self.job)


def synthetic_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject,DictionaryObject,NameObject
    lines=['Synthetic Opportunity','Synthetic Opportunity','SYN-001','Purpose of the Funding','Organizations may study synthetic examples.','Funding Details','Synthetic amounts omitted.','Eligible Applicants','Organizations only; eligibility is not proven.','Cost Sharing (Match) Requirement:','Match may apply.','Limit on Number of Applications:','One synthetic application only.','3. PROGRAM DESCRIPTION','Agency Funding Priorities','See Application Resource Guide.','Unallowable Activities:','Must not infer eligibility.','Goals and Objectives of This Funding Opportunity','Explain a synthetic example.','Expected Outcomes','No real program claims.']
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    commands=['BT /F1 10 Tf 14 TL 40 750 Td']
    for line in lines:commands.append('('+line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj T*')
    commands.append('ET');stream=DecodedStreamObject();stream.set_data('\n'.join(commands).encode());page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


class SourceProjection(unittest.TestCase):
    def setUp(self):
        self.raw=synthetic_pdf();self.receipt={'url':'https://ojp.gov/synthetic-test.pdf','fetched_at':'2020-01-01T00:00:00+00:00','sha256':sha256_bytes(self.raw),'bytes':len(self.raw)}
        self.record={'title':'Synthetic Opportunity','number':'SYN-001','unknowns':['Eligibility unknown']}
        self.intent={'profile':projection.PROFILE,'audience':'organizational_applicants','topic':'program_purpose','source_title':self.record['title']}

    def project(self,**kwargs):return projection.project(self.raw,self.receipt,self.record,self.intent,full_input={},**kwargs)

    def test_actual_pdf_projection_and_lossless_view(self):
        original=copy.deepcopy((self.receipt,self.record,self.intent));result=self.project();self.assertEqual(result['state'],'projected',result)
        packet=result['packet'];derived=views.compact(packet);proof=views.verify_view(derived['view'],derived['binding'],packet)
        self.assertTrue(proof['all_quotes_reconstruct_exactly']);self.assertEqual(proof['excerpt_count'],7)
        self.assertFalse(packet['source_currentness_confirmed']);self.assertFalse(packet['owner_approval']);self.assertEqual(original,(self.receipt,self.record,self.intent))
        self.assertTrue(packet['unresolved_references']);self.assertTrue(packet['research_unknowns'])

    def test_budget_never_clips_required_source(self):
        result=self.project(max_quote_bytes=1);self.assertEqual(result['state'],'needs_narrower_topic');self.assertIsNone(result['packet'])

    def test_wrong_receipt_and_changed_normalization_rejected(self):
        self.receipt['sha256']='0'*64;self.assertEqual(self.project()['state'],'source_mismatch')
        self.receipt['sha256']=sha256_bytes(self.raw)
        self.assertEqual(self.project(expected_normalized_sha256='0'*64)['state'],'normalization_mismatch')

    def test_view_quote_tampering_rejected(self):
        packet=self.project()['packet'];derived=views.compact(packet);derived['view']['excerpts'][0][-1]+=' invented'
        with self.assertRaises(ValueError):views.verify_view(derived['view'],derived['binding'],packet)

    def test_view_rehash_cannot_grant_approval(self):
        packet=self.project()['packet'];derived=views.compact(packet);derived['view']['owner_approval']=True;derived['binding']['model_view_sha256']=views.sha(derived['view'])
        with self.assertRaisesRegex(ValueError,'grant acceptance'):views.verify_view(derived['view'],derived['binding'],packet)

    def test_compact_request_budget_not_execution(self):
        packet=self.project()['packet'];shell={k:{} for k in ['format','options']};shell.update(model='synthetic',system='Test only',stream=False,think=False,keep_alive=0,prompt='')
        result=views.build_request(packet,shell);self.assertEqual(result['state'],'budget_validated_not_dispatched')
        rejected=views.build_request(packet,shell,max_request_bytes=1);self.assertIsNone(rejected['request']);self.assertTrue(rejected['no_truncation'])


if __name__=='__main__':unittest.main(verbosity=2)

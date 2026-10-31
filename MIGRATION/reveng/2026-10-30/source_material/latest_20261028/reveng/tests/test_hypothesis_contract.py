"""Actual validator regressions on labelled synthetic inputs, not model-quality proof."""
from pathlib import Path
import argparse,copy,hashlib,json,os,sys,unittest
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path)
args=parser.parse_args();SOURCE=args.source.resolve();sys.dont_write_bytecode=True
if not SOURCE.is_dir():parser.error('Explicit canonical source copy is required')
sys.path.insert(0,str(SOURCE))
def inventory():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py','.cs'}}
BEFORE=inventory()
def offline(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Contract tests forbid transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise PermissionError('Contract tests forbid model imports')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).resolve();flags=args[2] or 0
  if (path==SOURCE or SOURCE in path.parents) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Canonical source writes forbidden')
sys.addaudithook(offline)
import reveng_local_research as m,commercial_review as commercial

TEXT_FIELDS=['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','alternatives_and_limits']
OBS=[{'evidence_id':'E1','title':'SYNTHETIC recurring export question','url':'https://fixture.example.test/one','source':'synthetic','kind':'public_question_title','excerpt':'SYNTHETIC unit fixture, not captured evidence'}]
LEGACY_REVISION='fdcbbd43acfd4a5c230c36a6fedc30f8622ebd48022f03677f3f0fc43c31f6bf'
def proposal():
 c={k:'SYNTHETIC hypothesis for a manual export service; not verified.' for k in TEXT_FIELDS}
 c.update(market_category='other',evidence_ids=['E1'],risks=[],missing_evidence=['Actual demand is unknown'],observations_used=[{'evidence_id':'E1','source_field':'title','quote':OBS[0]['title'],'support':'source_quote'}])
 return c
def offer(amount=10,currency='USD'):return {'status':'proposed_unverified','amount':amount,'currency':currency}
def validate(card):return m.validate_cards({'hypotheses':[card]},OBS)[0]

class HypothesisContractTests(unittest.TestCase):
 def test_legacy_single_report_proposal_does_not_require_demand_proof(self):
  row=validate(proposal());self.assertEqual(row['status'],'unvalidated_hypothesis');self.assertEqual(row['observed_basis'],OBS)
  for key in ['market_score','profit','sales']:self.assertIsNone(row[key])
  self.assertNotIn('price_experiment',row)
 def test_optional_offer_schema_does_not_make_up_unknown_amount_currency(self):
  schema=m.schema(['E1'])['properties']['hypotheses']['items']
  self.assertIn('price_experiment',schema['properties']);self.assertNotIn('price_experiment',schema['required'])
  c=proposal();c['price_experiment']=None;self.assertIsNone(validate(c)['price_experiment'])
 def test_typed_ten_dollar_offer_is_unverified_not_income(self):
  c=proposal();c['validation_step']='SYNTHETIC: request non-binding feedback on a proposed manual export test offer.';c['price_experiment']=offer()
  result=validate(c);self.assertEqual(result['price_experiment'],offer());self.assertEqual(result['status'],'unvalidated_hypothesis')
  for key in ['market_score','profit','sales']:self.assertIsNone(result[key])
  review=commercial.assess(result,[]);self.assertIsNone(review['buyer']['payment_evidence']);self.assertEqual(review['buyer']['status'],'model_hypothesis_not_customer');self.assertIsNone(review['estimated_revenue'])
 def test_zero_is_free_proposed_test_never_payment(self):
  c=proposal();c['price_experiment']=offer(0);result=validate(c)
  self.assertEqual(result['price_experiment']['amount'],0);self.assertIsNone(commercial.assess(result,[])['buyer']['payment_evidence'])
 def test_invalid_or_nonfinite_amounts_rejected(self):
  for value in [True,False,-1,-0.01,float('nan'),float('inf'),float('-inf'),'10',None,[],{}]:
   with self.subTest(value=repr(value)):
    c=proposal();c['price_experiment']=offer(value)
    with self.assertRaises(ValueError):validate(c)
 def test_currency_is_bounded_explicit_code_without_conversion(self):
  for currency in ['',None,'usd','US','USDD','USD\n',' USD','$',True,[],{'code':'USD'}]:
   with self.subTest(currency=currency):
    c=proposal();c['price_experiment']=offer(currency=currency)
    with self.assertRaises(ValueError):validate(c)
  c=proposal();c['price_experiment']=offer(12.5,'EUR');self.assertEqual(validate(c)['price_experiment'],offer(12.5,'EUR'))
 def test_offer_cannot_claim_established_state_or_extra_facts(self):
  invalid=[dict(offer(),status='verified_payment'),dict(offer(),payment_evidence=True),{'amount':10,'currency':'USD'},{'status':'proposed_unverified','currency':'USD'},{'status':'proposed_unverified','amount':10},[],True,'SYNTHETIC offer']
  for value in invalid:
   with self.subTest(value=value):
    c=proposal();c['price_experiment']=value
    with self.assertRaises(ValueError):validate(c)
 def test_exact_uncertainty_clauses_do_not_claim_financial_proof(self):
  for prefix in ['There is no','No']:
   for quality in ['proven','verified']:
    for subject in ['demand','profit','sales']:
     with self.subTest(prefix=prefix,quality=quality,subject=subject):
      c=proposal();c['missing_evidence']=[prefix+' '+quality+' '+subject+'.'];self.assertEqual(validate(c)['status'],'unvalidated_hypothesis')
  for text in ['Demand is not proven.','Profit is not verified.','Sales are not guaranteed.']:
   c=proposal();c['missing_evidence']=[text];validate(c)
 def test_adjacent_positive_guarantees_never_hidden_by_negation(self):
  for text in ['There is no proven demand. Guaranteed sales follow.','No proven demand; verified profit is established.','There is no proven demand, but proven sales exist.','Not only proven demand but verified sales exist.','Demand is not proven. https://invented.example.test is our proof.']:
   with self.subTest(text=text):
    c=proposal();c['missing_evidence']=[text];c['price_experiment']=offer()
    with self.assertRaises(ValueError):validate(c)
 def test_amount_and_guarantee_guard_still_applies_to_every_prose_field(self):
  for field in TEXT_FIELDS+['risks','missing_evidence']:
   for bad in ['SYNTHETIC unsupported price is $10 per month.','Guaranteed sales for the proposed service.','Proven demand for the proposed service.','A claim from https://invented.example.test']:
    with self.subTest(field=field,bad=bad):
     c=proposal();c[field]=[bad] if field in ['risks','missing_evidence'] else bad;c['price_experiment']=offer()
     with self.assertRaises(ValueError):validate(c)
 def test_arbitrary_dollar_prose_is_not_a_typed_offer(self):
  c=proposal();c['validation_step']='Ask about a $10 test offer; this is unverified, not observed revenue.'
  with self.assertRaisesRegex(ValueError,'price_experiment'):validate(c)
 def test_offer_does_not_repair_bad_source_reference_or_quote(self):
  for field,value in [('evidence_ids',['invented']),('observations_used',[{'evidence_id':'E1','source_field':'title','quote':'not in the synthetic title','support':'source_quote'}])]:
   c=proposal();c['price_experiment']=offer();c[field]=value
   with self.assertRaises(ValueError):validate(c)
 def test_absent_null_preserve_exact_public_baseline_revision(self):
  c=proposal();self.assertEqual(commercial.revision(validate(c)),LEGACY_REVISION)
  c['price_experiment']=None;self.assertEqual(commercial.revision(validate(c)),LEGACY_REVISION)
 def test_changed_offer_changes_review_revision_without_new_candidate_identity(self):
  c=proposal();base=validate(c);c['price_experiment']=offer();one=validate(c);c['price_experiment']=offer(20);two=validate(c);c['price_experiment']=offer(20,'EUR');three=validate(c)
  hashes={commercial.revision(x) for x in [base,one,two,three]};self.assertEqual(len(hashes),4)
  self.assertEqual(len({commercial.identity(x) for x in [base,one,two,three]}),1)
  first=commercial.merge_ledger([], [one]);second=commercial.merge_ledger(first,[two]);self.assertEqual(len(second),1);self.assertEqual(second[0]['history'][0]['price_experiment'],offer());self.assertNotEqual(first[0]['review_revision_hash'],second[0]['review_revision_hash'])
 def test_validation_preserves_inputs_and_allows_abstention(self):
  c=proposal();c['price_experiment']=offer();before=copy.deepcopy(c);validate(c);self.assertEqual(c,before)
  self.assertEqual(m.validate_cards({'hypotheses':[]},OBS),[])


class QuotationBudgetIdentityTests(unittest.TestCase):
 """Synthetic real-validator/review/export paths; identities never merge evidence rows."""
 def rows(self,second_words=13):
  def row(eid,slug,prefix,count):
   text=' '.join(prefix+str(i) for i in range(count))
   return dict(evidence_id=eid,title='SYNTHETIC saved question variant',url='https://webapps.stackexchange.com/questions/900000001/'+slug,source='webapps',kind='public_question_context',source_field='body',question_id=900000001,context_text=text,content_scope='question_body',body_available=True,author_id='webapps:7',observed_at='2026-10-28T00:00:00+00:00')
  return [row('E1','old-title','syntheticA',13),row('E2','changed-title','syntheticB',second_words)]
 def claim(self,row,field='observed_text'):
  return dict(evidence_id=row['evidence_id'],source_field=field,quote=row['answer_text'] if field=='answer_text' else row['context_text'],support='source_quote')
 def card(self,row,field='observed_text'):
  value=proposal();value['evidence_ids']=[row['evidence_id']];value['observations_used']=[self.claim(row,field)];return value
 def validate_rows(self,rows):return m.validate_cards({'hypotheses':[self.card(row) for row in rows]},rows)
 def test_changed_slug_same_question_shares_actual_multi_card_budget(self):
  rows=self.rows();self.assertEqual(commercial.row_report_identity(rows[0]),commercial.row_report_identity(rows[1]));self.assertNotEqual(commercial.canonical(rows[0]['url']),commercial.canonical(rows[1]['url']))
  with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(rows)
 def test_exact_same_url_and_same_card_aliases_cannot_reset_budget(self):
  rows=self.rows();rows[1]['url']=rows[0]['url']
  with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(rows)
  rows=self.rows();card=self.card(rows[0]);card['evidence_ids']=['E1','E2'];card['observations_used']=[self.claim(row) for row in rows]
  with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):m.validate_cards({'hypotheses':[card]},rows)
 def test_twenty_five_words_preserve_both_variants_and_original_bytes(self):
  rows=self.rows(12);before=json.dumps(rows,sort_keys=True,ensure_ascii=False).encode();cards=self.validate_rows(rows)
  self.assertEqual(len(cards),2);self.assertEqual([card['observed_basis'][0] for card in cards],rows);self.assertEqual(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode(),before);self.assertNotEqual(rows[0]['url'],rows[1]['url'])
 def test_distinct_question_ids_have_distinct_budgets(self):
  rows=self.rows();rows[1].update(url='https://webapps.stackexchange.com/questions/900000002/changed-title',question_id=900000002);self.assertEqual(len(self.validate_rows(rows)),2)
 def test_unknown_sites_and_unrecognized_question_shapes_are_not_aliased(self):
  variants=[('https://unknown.example.test/questions/900000001/old-title','https://unknown.example.test/questions/900000001/changed-title'),('https://webapps.stackexchange.com/questions/900000001/old-title?answer=1','https://webapps.stackexchange.com/questions/900000001/changed-title?answer=1'),('https://webapps.stackexchange.com/questions/900000001/123','https://webapps.stackexchange.com/questions/900000001/456')]
  for first,second in variants:
   with self.subTest(first=first,second=second):
    rows=self.rows();rows[0]['url']=first;rows[1]['url']=second;self.assertEqual(len(self.validate_rows(rows)),2)
 def test_contradictory_source_metadata_never_invents_question_equivalence(self):
  for key,value in [('source','travel'),('source_field','story_text'),('question_id',900000002),('kind','package_listing_not_demand')]:
   with self.subTest(key=key):
    rows=self.rows();rows[1][key]=value;self.assertEqual(len(self.validate_rows(rows)),2)
 def test_supported_question_hosts_share_only_their_own_question_budget(self):
  for host,source in [('superuser.com','superuser'),('graphicdesign.stackexchange.com','design'),('travel.stackexchange.com','travel')]:
   with self.subTest(host=host):
    rows=self.rows()
    for row in rows:row['url']=row['url'].replace('webapps.stackexchange.com',host);row['source']=source;row.pop('question_id',None)
    with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(rows)
  rows=self.rows();rows[1]['url']=rows[1]['url'].replace('webapps.stackexchange.com','travel.stackexchange.com');rows[1]['source']='travel';self.assertEqual(len(self.validate_rows(rows)),2)
 def test_generic_canonical_budget_is_not_weakened_by_role_or_fragment(self):
  for second in ['https://unknown.example.test/article?utm_source=second#part-two','https://unknown.example.test/article']:
   with self.subTest(second=second):
    rows=self.rows();rows[0]['url']='https://unknown.example.test/article?utm_source=first#part-one';rows[1].update(url=second,kind='package_listing_not_demand')
    with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(rows)
 def test_recognized_identity_never_splits_existing_same_url_budget(self):
  for change in [dict(source='travel'),dict(kind='package_listing_not_demand'),dict(fragment='#67890')]:
   with self.subTest(change=change):
    rows=self.rows();rows[1]['url']=rows[0]['url']
    if 'fragment' in change:rows[1]['url']+=change['fragment']
    else:rows[1].update(change)
    self.assertEqual(commercial.canonical(rows[0]['url']),commercial.canonical(rows[1]['url']))
    with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(rows)
 def test_alias_and_same_url_bridge_has_one_aggregate_budget(self):
  rows=self.rows();fallback=dict(rows[0],evidence_id='E3',source='travel',context_text=' '.join('syntheticC'+str(i) for i in range(10)));rows=[rows[0],fallback,rows[1]]
  for row in rows:row['context_text']=' '.join(row['context_text'].split()[:10])
  import itertools
  for ordered in itertools.permutations(rows):
   with self.subTest(order=[row['evidence_id'] for row in ordered]),self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):self.validate_rows(list(ordered))
 def test_newly_confirmed_alias_preserves_previously_shared_budget_words(self):
  import quote_contract
  rows=self.rows();fallback=dict(rows[0],source='travel');budget={};first=quote_contract.verify([self.claim(fallback)],[fallback],['E1'],budget);self.assertEqual(first['status'],'verified_literals');second=quote_contract.verify([self.claim(rows[1])],rows,['E2'],budget);self.assertEqual(second['status'],'invalid');self.assertEqual(sum(budget.values()),26)
 def test_question_and_answer_aliases_share_budget_but_not_attribution(self):
  import quote_contract
  rows=self.rows();rows[1].update(answer_text=rows[1]['context_text'],answer_url='https://webapps.stackexchange.com/a/900000003',answer_scope='one_community_answer_only_not_whole_thread',answer_author_id=9)
  cards=[self.card(rows[0]),self.card(rows[1],'answer_text')]
  with self.assertRaisesRegex(ValueError,'Source quote word budget exceeded'):m.validate_cards({'hypotheses':cards},rows)
  rows[1]['answer_text']=' '.join(rows[1]['answer_text'].split()[:12]);cards[1]=self.card(rows[1],'answer_text');m.validate_cards({'hypotheses':cards},rows);budget={};first=quote_contract.verify(cards[0]['observations_used'],rows,['E1'],budget);second=quote_contract.verify(cards[1]['observations_used'],rows,['E2'],budget)
  self.assertEqual(first['verified'][0]['source_url'],rows[0]['url']);self.assertEqual(second['verified'][0]['source_url'],rows[1]['answer_url']);self.assertEqual(second['verified'][0]['evidence_role'],'community_answer_not_verified_resolution_or_demand');self.assertEqual(list(budget.values()),[25])
 def test_saved_research_review_uses_shared_alias_budget_without_rewriting_rows(self):
  import research_review
  rows=self.rows();before=copy.deepcopy(rows);budget={};reviews=[research_review.assess(self.card(row),rows,[],quote_budgets=budget) for row in rows]
  self.assertEqual(reviews[0]['literal_support']['status'],'verified_literals');self.assertEqual(reviews[1]['literal_support']['status'],'invalid');self.assertIn('invalid_source_quote',{r['code'] for r in reviews[1]['reasons']});self.assertEqual(rows,before);self.assertTrue(all(review['auto_admission'] is False for review in reviews))
 def test_saved_over_budget_result_is_held_without_rewrite_or_repeat_dispatch(self):
  import tempfile,analysis_jobs,research_review
  rows=self.rows();request=m.build_model_request(rows)
  with tempfile.TemporaryDirectory(prefix='reveng-quote-history-synthetic-') as temporary:
   root=Path(temporary);run=root/'run';run.mkdir();m.dump(root/'candidates.json',[]);job=analysis_jobs.prepare(m,root,run,rows,[],[],9999999999,request);input_path=root/'analysis-inputs'/(job+'.json');result_path=root/'analysis-results'/(job+'.json');m.dump(result_path,{'model_output':{'source_job':job,'hypotheses':[self.card(row) for row in rows]},'synthetic_test_only':True});before={path:path.read_bytes() for path in [input_path,result_path,root/'candidates.json']}
   self.assertEqual(analysis_jobs.prepare(m,root,run,rows,[],[],9999999999,request),job);saved=analysis_jobs.load_queue(m,root)['jobs'][job];self.assertEqual(saved['status'],'completed_needs_review');self.assertFalse(saved['recovered_result_structurally_valid']);self.assertIn('Source quote word budget exceeded',saved['recovery_warning'])
   reviewed=research_review.refresh(m,root);self.assertEqual(len(reviewed['cards']),2);self.assertEqual(reviewed['cards'][1]['output_review']['literal_support']['status'],'invalid');self.assertEqual(reviewed['active_candidates_added'],0);self.assertEqual(reviewed['model_calls'],0)
   with self.assertRaisesRegex(ValueError,'Saved attempt/result exists'):analysis_jobs.assert_dispatchable(m,root,job)
   self.assertEqual(before,{path:path.read_bytes() for path in before})
 def test_actual_export_preserves_distinct_saved_urls_fields_and_original_data(self):
  import csv,io,tempfile,zipfile,research_export,source_ledger
  rows=self.rows(12);card=self.card(rows[0]);card['evidence_ids']=['E1','E2'];card['observations_used']=[self.claim(row) for row in rows];card=m.validate_cards({'hypotheses':[card]},rows)[0];card['candidate_id']='synthetic-quote-budget-only'
  with tempfile.TemporaryDirectory(prefix='reveng-quote-export-synthetic-') as temporary:
   root=Path(temporary)
   for name,value,signed in [('candidates.json',[card],False),('research-output-cards.json',{'cards':[]},True),('analysis-queue.json',{'jobs':{}},True)]:
    if signed:value=dict(value,integrity_sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest())
    (root/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
   source_ledger.write(root/'source-ledger-catalog.json',source_ledger.seal(source_ledger.build(root)));before={p.name:p.read_bytes() for p in root.glob('*.json')};target=root/'exports/synthetic.zip';receipt=research_export.export(root,target);self.assertEqual(receipt['status'],'exported');self.assertEqual(receipt['network_calls'],0);self.assertEqual(receipt['model_calls'],0)
   with zipfile.ZipFile(target) as archive:
    self.assertEqual(archive.read('candidates.json'),before['candidates.json']);summary=list(csv.DictReader(io.StringIO(archive.read('research-summary.csv').decode('utf-8-sig'))));refs=json.loads(summary[0]['source_references']);bodyrefs=[ref for ref in refs if ref['source_field']=='observed_text'];self.assertEqual([ref['source_url'] for ref in bodyrefs],[row['url'] for row in rows]);self.assertEqual([ref['evidence_id'] for ref in bodyrefs],['E1','E2']);self.assertTrue(all(ref['literal_claims'][0]['semantic_support']=='NOT_VERIFIED' for ref in bodyrefs))
   self.assertEqual(before,{p.name:p.read_bytes() for p in root.glob('*.json')})

def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Canonical source changed during tests')

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

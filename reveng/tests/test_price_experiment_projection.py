"""Actual local comparison/preview/ZIP+CSV tests using owned synthetic files only."""
from pathlib import Path
import argparse,copy,csv,hashlib,io,json,os,sys,tempfile,unittest,zipfile
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);parser.add_argument('--legacy-receipt',action='store_true');args=parser.parse_args()
SOURCE=args.source.resolve();sys.path.insert(0,str(SOURCE));sys.dont_write_bytecode=True
H=lambda value:hashlib.sha256(value).hexdigest()
def inventory():return {p.name:H(p.read_bytes()) for p in SOURCE.iterdir() if p.suffix in {'.py','.cs'}}
BEFORE=inventory()
def offline(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Offline projection test forbids transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise PermissionError('No model imports')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).resolve();flags=args[2] or 0
  if (path==SOURCE or SOURCE in path.parents) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Source writes forbidden')
sys.addaudithook(offline)
import reveng_local_research as m,comparison_data,social_idea_preview,research_export,source_ledger as ledger

def base():
 obs=[{'evidence_id':'SYN1','title':'SYNTHETIC export question','url':'https://fixture.example.test/one','source':'synthetic','kind':'public_question_title','excerpt':'SYNTHETIC unit test only'}]
 row={k:'SYNTHETIC manual export hypothesis, not verified.' for k in ['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','alternatives_and_limits']}
 row.update(market_category='other',evidence_ids=['SYN1'],risks=[],missing_evidence=['No market validation performed'],observations_used=[{'evidence_id':'SYN1','source_field':'title','quote':obs[0]['title'],'support':'source_quote'}])
 row=m.validate_cards({'hypotheses':[row]},obs)[0];row['candidate_id']='synthetic-projection-only';return row

def render(card):
 with tempfile.TemporaryDirectory(prefix='reveng-price-projection-unit-') as temp:
  root=Path(temp).resolve()
  for name,value,signed in [('candidates.json',[card],False),('research-output-cards.json',{'cards':[]},True),('analysis-queue.json',{'jobs':{}},True)]:
   if signed:value=dict(value,integrity_sha256=H(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()))
   (root/name).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False),encoding='utf8')
  ledger.write(root/'source-ledger-catalog.json',ledger.seal(ledger.build(root)))
  before={p.name:H(p.read_bytes()) for p in root.glob('*.json')}
  comparison=comparison_data.build(root);preview=social_idea_preview.preview(comparison,'legacy_hypothesis:synthetic-projection-only',ledger.catalog(root))
  social_idea_preview.validate(preview,comparison,ledger.catalog(root))
  output=root/'exports/synthetic.zip';receipt=research_export.export(root,output)
  if receipt['status']!='exported' or receipt['model_calls'] or receipt['network_calls']:raise AssertionError('Unexpected export status/actions')
  raw_csv=output.with_suffix('.csv').read_bytes()
  with zipfile.ZipFile(output) as archive:
   if archive.read('research-summary.csv')!=raw_csv:raise AssertionError('CSV differs from verified ZIP')
   if json.loads(archive.read('candidates.json'))!=[card]:raise AssertionError('Raw candidate changed')
  if before!={p.name:H(p.read_bytes()) for p in root.glob('*.json')}:raise AssertionError('Source data changed during projection')
  return comparison,preview,raw_csv

def digests(rendered):
 comparison,preview,raw_csv=rendered
 return {'comparison_rows':H(json.dumps(comparison['rows'],sort_keys=True,ensure_ascii=False).encode()),'preview':H(json.dumps(preview,sort_keys=True,ensure_ascii=False).encode()),'csv':H(raw_csv)}

if args.legacy_receipt:
 print(json.dumps(digests(render(base())),sort_keys=True));raise SystemExit(0)

import price_experiments
LEGACY_DIGESTS={'comparison_rows': 'cdfeb2586e7f05dbdfbcdd820c9acce55557464fe0bddcb546717d33c83615a8', 'csv': '403a52915fb8567cefff0e7978dc1c84188e4714f77bb934229b689038b80395', 'preview': '44507b043c9f3a1d52d1162b47e87b4a144186298a9aea3e5c33556cb71771dd'}
class ProjectionTests(unittest.TestCase):
 def test_absent_offer_keeps_exact_public_baseline_views(self):
  self.assertEqual(digests(render(base())),LEGACY_DIGESTS)
 def test_valid_offer_visible_in_actual_comparison_preview_and_verified_csv(self):
  c=base();c['price_experiment']={'status':'proposed_unverified','amount':10,'currency':'USD'};comparison,preview,raw_csv=render(c)
  a=comparison['rows'][0]['proposed_price_experiment'];b=preview['idea_hypotheses']['proposed_price_experiment']
  self.assertEqual(a,b);self.assertEqual(a['amount'],10);self.assertIn('UNVERIFIED',a['label']);self.assertIsNone(a['payment_evidence']);self.assertFalse(a['execution_authorized']);self.assertIn('10 USD',raw_csv.decode('utf-8-sig'))
  self.assertFalse(preview['ready_for_social']);self.assertFalse(preview['publication_authorized'])
  self.assertEqual(a['currency_validation'],'THREE_LETTER_SYNTAX_ONLY_NOT_VERIFIED_ISO')
 def test_null_offer_adds_no_offer_but_keeps_exact_changed_source_hash(self):
  c=base();old_comparison,_,baseline_csv=render(c);c['price_experiment']=None;comparison,preview,raw_csv=render(c)
  self.assertNotIn('proposed_price_experiment',comparison['rows'][0]);self.assertNotIn('proposed_price_experiment',preview['idea_hypotheses'])
  old=list(csv.DictReader(io.StringIO(baseline_csv.decode('utf-8-sig'))))[0];new=list(csv.DictReader(io.StringIO(raw_csv.decode('utf-8-sig'))))[0]
  old_refs=json.loads(old.pop('source_references'));new_refs=json.loads(new.pop('source_references'));self.assertEqual(old,new)
  self.assertNotEqual(old_comparison['inputs']['candidates.json'],comparison['inputs']['candidates.json'])
  for refs,expected in [(old_refs,old_comparison['inputs']['candidates.json']),(new_refs,comparison['inputs']['candidates.json'])]:
   for ref in refs:self.assertEqual(ref.pop('container_file_sha256'),expected)
  self.assertEqual(old_refs,new_refs)
 def test_malformed_saved_offer_withheld_in_real_views_not_trusted(self):
  c=base();c['price_experiment']={'status':'verified_payment','amount':'999999','currency':'BADLABEL'};comparison,preview,raw_csv=render(c)
  for value in [comparison['rows'][0]['proposed_price_experiment'],preview['idea_hypotheses']['proposed_price_experiment']]:
   self.assertEqual(value['status'],'malformed_untrusted_offer');self.assertNotIn('amount',value);self.assertFalse(value['execution_authorized']);self.assertIsNone(value['payment_evidence'])
  self.assertNotIn('999999',raw_csv.decode('utf-8-sig'));self.assertIn('withheld',raw_csv.decode('utf-8-sig'))
 def test_preview_rebuilds_label_and_never_trusts_caller_readiness(self):
  row={'proposed_price_experiment':{'status':'proposed_unverified','amount':5,'currency_label':'ZZZ','label':'VERIFIED MONEY','execution_authorized':True,'payment_evidence':'invented'}}
  out=price_experiments.preview_fields(row)['proposed_price_experiment'];self.assertNotIn('VERIFIED MONEY',out['label']);self.assertFalse(out['execution_authorized']);self.assertIsNone(out['payment_evidence']);self.assertEqual(out['currency_label'],'ZZZ');self.assertIn('unverified currency label',out['label'])
 def test_prompt_distinguishes_optional_proposed_offer_without_demand_gate(self):
  request=m.build_model_request(base()['observed_basis']);text=request['messages'][1]['content']
  self.assertIn('optional price_experiment',text);self.assertIn('Omit it or use null',text);self.assertIn('never an observed price, payment, revenue or demand',text);self.assertIn('no owner biography, contacts or industry mandate',text);self.assertIn('only one report',text)
 def test_projections_preserve_input_and_bound_display(self):
  c=base();c['price_experiment']={'status':'proposed_unverified','amount':10,'currency':'USD'};before=copy.deepcopy(c);price_experiments.comparison_fields(c);price_experiments.csv_uncertainties(c);self.assertEqual(c,before)
  self.assertEqual(price_experiments.projection({'status':'proposed_unverified','amount':10**100,'currency':'USD'})['status'],'malformed_untrusted_offer')

def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Canonical source changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

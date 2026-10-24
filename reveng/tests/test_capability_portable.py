"""Synthetic capability provenance tests, not Keploy execution or market evidence."""
from pathlib import Path
import sys,json,tempfile,hashlib,unittest,copy,ast,argparse,inspect
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',required=True,type=Path)
args=parser.parse_args();SOURCE=args.source.resolve()
if not SOURCE.is_dir():parser.error('--source must be an existing canonical source copy')
sys.path.insert(0,str(SOURCE))
def inventory():
 return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py','.cs'}}
BEFORE=inventory()
def no_external_actions(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:
  raise AssertionError('Portable test forbids network/process execution')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:
  raise AssertionError('Portable test forbids model imports')
sys.addaudithook(no_external_actions)
import api_capability as a,direct_alternatives as d,source_rules,reveng_local_research as m
POS="Keploy captures your app's API calls and turns them into test cases and mocks/stubs."

def synthetic_observations():
 text='SYNTHETIC API workflow request; no user, market or capability evidence.'
 return [{'evidence_id':'SYN1','source':'synthetic_protocol_only','title':'SYNTHETIC workflow','url':'https://fixture.example.test/workflow','context_text':text,'excerpt':text,'source_field':'synthetic_text','content_scope':'synthetic_only','kind':'synthetic_protocol_only','source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'context_truncated':False}]

def normalized_ast(value):
 """Stable Python 3.10+ structure; only absent/empty type_params is normalized."""
 if isinstance(value,ast.AST):
  result={'_type':type(value).__name__}
  for key,item in ast.iter_fields(value):
   if key=='type_params':
    if item:raise ValueError('Unexpected generic type parameters')
    continue
   result[key]=normalized_ast(item)
  return result
 if isinstance(value,list):return [normalized_ast(item) for item in value]
 return value

def ast_digest(node):
 return hashlib.sha256(json.dumps(normalized_ast(node),sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Tests(unittest.TestCase):
 def row(self,root,text=POS):
  raw=('<!doctype html><html><head><title>SYNTHETIC DOCUMENTATION FIXTURE</title><link rel="canonical" href="'+a.SOURCES['api_keploy_local']['url']+'"></head><body><main>'+text+'</main></body></html>').encode();sha=hashlib.sha256(raw).hexdigest();p=Path(root)/'direct-source-payloads';p.mkdir(exist_ok=True);(p/(sha+'.raw')).write_bytes(raw)
  return a.parse('api_keploy_local',d.body_text(raw,a.SOURCES['api_keploy_local']['url']),'2026-10-22T00:00:00+00:00',sha,d.SCHEMA)
 def test_registry_routes_existing_collector(self):
  self.assertEqual(d.SOURCES['api_keploy_local']['task'],a.TASK);self.assertIn(a.TASK,source_rules.TASKS)
 def test_bound_documented_claim_never_tested(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   row=self.row(root);v=a.attachment([row],root);doc=v['documents'][0]
   self.assertEqual(v['documented_capabilities'],['same_capture_tests_and_mocks']);self.assertFalse(doc['claims'][0]['tested']);self.assertEqual(v['tested_capabilities'],[]);self.assertEqual(v['executed_observations'],[]);self.assertEqual(doc['raw_sha256'],row['response_sha256']);self.assertEqual(doc['captured_at'],row['observed_at']);self.assertEqual(v['market_demand'],'unknown')
 def test_unavailable_stale_and_raw_tampering_unknown(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   original=self.row(root)
   for mutation in [{'error':'Blocked fixture'},{'expires':0},{'response_sha256':'0'*64},{'document_text':'changed'}]:
    row=dict(original,**mutation);v=a.attachment([row],root);self.assertEqual(v['documented_capabilities'],[]);self.assertEqual(v['documents'][0]['status'],'unknown')
 def test_contradictory_same_and_separate_documents_unknown(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   yes=self.row(root);both=self.row(root,POS+' It does not create tests and mocks.');no=self.row(root,'It does not create tests and mocks.')
   for rows in [[both],[yes,no]]:
    v=a.attachment(rows,root);self.assertEqual(v['documented_capabilities'],[]);self.assertIn('same_capture_tests_and_mocks',v['unknown_required_capabilities']);self.assertTrue(v['missing_evidence'])
 def test_popularity_and_forged_fact_metadata_not_capability(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   row=self.row(root,'100000 stars. 2000 downloads. Most popular tool.');row['facts']=[{'kind':'same_capture_tests_and_mocks','quote':POS,'tested':True}];row['stars']=100000
   v=a.attachment([row],root);self.assertEqual(v['documented_capabilities'],[]);self.assertNotIn('stars',json.dumps(v))
 def test_execution_spoof_rejected(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   row=self.row(root);row['executed_observations']=[{'tested':True}]
   with self.assertRaises(ValueError):a.attachment([row],root)
 def test_explicit_synthesis_attachment_preserves_old_source_parse(self):
  obs=synthetic_observations()
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   base=m.build_model_request(obs);row=self.row(root);enriched=m.build_model_request(obs,[row],root)
   self.assertEqual(base['format'],enriched['format']);self.assertEqual(base['options'],enriched['options']);self.assertIn('OFFICIAL CAPABILITY EVIDENCE',enriched['messages'][1]['content']);self.assertEqual(json.loads(base['messages'][1]['content'].split('SOURCE OBSERVATIONS:\n',1)[1]),json.loads(enriched['messages'][1]['content'].split('SOURCE OBSERVATIONS:\n',1)[1]))
 def test_default_builder_matches_original_ast_function(self):
  # Structural identity to the verified public baseline, not a runtime fallback.
  node=ast.parse(inspect.getsource(m.build_model_request)).body[0]
  self.assertEqual([x.arg for x in node.args.args],['observations','capability_records','capability_root'])
  self.assertEqual([ast.literal_eval(x) for x in node.args.defaults],[None,None])
  self.assertIsInstance(node.body[-2],ast.If)
  self.assertEqual(ast.dump(node.body[-2].test),"Compare(left=Name(id='capability_records', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])")
  node.args.args=node.args.args[:1];node.args.defaults=[];del node.body[-2]
  self.assertEqual(ast_digest(node),EXPECTED_DEFAULT_AST_SHA256)
 def test_ast_pin_normalizes_only_empty_version_field(self):
  node=ast.parse('def unchanged(x): return x').body[0]
  without=copy.deepcopy(node)
  if hasattr(without,'type_params'):delattr(without,'type_params')
  with_empty=copy.deepcopy(node);with_empty._fields=tuple(k for k in with_empty._fields if k!='type_params')+('type_params',);with_empty.type_params=[]
  self.assertEqual(ast_digest(without),ast_digest(with_empty))
  with_empty.type_params=[ast.Name(id='UnexpectedGeneric',ctx=ast.Load())]
  with self.assertRaises(ValueError):ast_digest(with_empty)
 def test_explicit_attachment_requires_explicit_root(self):
  with self.assertRaisesRegex(ValueError,'Explicit isolated capability root'):
   m.build_model_request(synthetic_observations(),[])
 def test_new_task_never_weakens_candidate_admission(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   original=self.row(root);before=copy.deepcopy(original);result=d.for_task(a.TASK,[original],card={})
   self.assertEqual(result['status'],'review_required');self.assertFalse(result['active_candidate_admission'])
   self.assertFalse(result['alternatives'][0]['active_candidate_admission']);self.assertEqual(result['alternatives'][0]['covered'],[])
   self.assertEqual(result['alternatives'][0]['task_fit_to_original'],'UNREVIEWED_FOR_THIS_SOURCE')
   self.assertEqual(result['market_demand'],'unknown');self.assertEqual(result['executed_observations'],[]);self.assertEqual(original,before)
 def test_invalid_raw_identity_cannot_authenticate_claim(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   original=self.row(root)
   for raw in [("<main>"+POS+"</main>").encode(),('<link rel="canonical" href="https://wrong.example.test/">'+POS).encode(),('<title>Access denied</title><link rel="canonical" href="'+original['source_url']+'">'+POS).encode()]:
    sha=hashlib.sha256(raw).hexdigest();(Path(root)/'direct-source-payloads'/(sha+'.raw')).write_bytes(raw)
    result=a.attachment([dict(original,response_sha256=sha)],root)
    self.assertEqual(result['documented_capabilities'],[]);self.assertEqual(result['documents'][0]['status'],'unknown')
 def test_oversize_raw_is_rejected_before_html_parse(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   original=self.row(root);raw=b'X'*1048577;sha=hashlib.sha256(raw).hexdigest();(Path(root)/'direct-source-payloads'/(sha+'.raw')).write_bytes(raw)
   result=a.attachment([dict(original,response_sha256=sha)],root)
   self.assertEqual(result['documented_capabilities'],[]);self.assertIn('unavailable or changed',result['documents'][0]['diagnostic'])
 def test_claim_quote_budget_and_binding_are_literal(self):
  text=POS+' Record real API interactions (and dependencies) and replay them deterministically in local or CI. Mocks dependencies automatically'
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   row=self.row(root,text);result=a.attachment([row],root);claims=result['documents'][0]['claims']
   self.assertLessEqual(sum(len(c['quote'].split()) for c in claims),25)
   for claim in claims:
    self.assertEqual(row['document_text'][claim['start']:claim['end']],claim['quote']);self.assertFalse(claim['tested'])
 def test_unknown_task_never_becomes_capability_evidence(self):
  with tempfile.TemporaryDirectory(prefix='reveng-api-unit-') as root:
   with self.assertRaises(ValueError):a.attachment([dict(task='SYNTHETIC_other_task')],root)

def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Canonical source bytes changed during offline tests')

EXPECTED_DEFAULT_AST_SHA256='59d752674740bf19a7d707ab35bb9558012e34762f107031f643022c554acbca'
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

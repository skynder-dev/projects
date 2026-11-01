"""Synthetic answer-cache regressions through real collection; no live/model access."""
from pathlib import Path
import argparse,asyncio,copy,hashlib,json,os,selectors,sys,tempfile,time,unittest
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
SOURCE=args.source.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE))
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
BEFORE=inventory(SOURCE)
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Answer-cache regressions forbid transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper','aiohttp','crawl4ai'}:raise PermissionError('Answer-cache regressions forbid models/live collectors')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=Path(os.fsdecode(args[0])).resolve()
  if (p==SOURCE or SOURCE in p.parents) and (args[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Source writes forbidden')
sys.addaudithook(audit)
class Selector(selectors.DefaultSelector):
 def select(self,timeout=None):
  timeout=.01 if timeout is None else max(0,min(timeout,.01))
  if not self.get_map():time.sleep(timeout);return []
  return super().select(timeout)
class Loop(asyncio.SelectorEventLoop):
 def __init__(self):super().__init__(selector=Selector())
 def _make_self_pipe(self):self._ssock=self._csock=None
 def _close_self_pipe(self):pass
 def _write_to_self(self):pass
class Policy(asyncio.DefaultEventLoopPolicy):
 def new_event_loop(self):return Loop()
asyncio.set_event_loop_policy(Policy())
import answer_context,reveng_local_research as m,source_context,model_packet,discovery_plan,observation_history as history
NOW=1792972800;STAMP='2026-10-26T00:00:00+00:00';QID=900000001
class AnswerCacheTests(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory(prefix='reveng-answer-synthetic-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);self.cache=self.root/'cache';self.cache.mkdir();self.run=self.root/'runs'/'synthetic';self.run.mkdir(parents=True)
  for target,value in [('time.time',NOW),('reveng_local_research.now',STAMP)]:
   p=patch(target,return_value=value);p.start();self.addCleanup(p.stop)
  self.source=copy.deepcopy(m.SOURCES[1]);self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0}
  obj={'items':[{'question_id':QID,'title':'SYNTHETIC question','body':'<p>SYNTHETIC original question with https://example.invalid/article</p>','link':'https://webapps.stackexchange.com/questions/'+str(QID)+'/synthetic','owner':{'user_id':7},'answer_count':2,'accepted_answer_id':42}]}
  self.rows=m.parse_api(self.source,json.dumps(obj).encode())
  for row in self.rows:row.update(source=self.source['id'],family=self.source['family'],observed_at=STAMP,source_endpoint=self.source['url'])
  self.primary=self.cache/(m.sha((m.VERSION+source_context.SCHEMA+self.source['url']).encode())+'.json');m.dump(self.primary,dict(url=self.source['url'],expires=NOW+3600,rows=self.rows,rows_sha256=m.sha(json.dumps(self.rows,sort_keys=True).encode())))
  self.endpoint='https://api.stackexchange.com/2.3/questions/'+str(QID)+'/answers?'+answer_context.urlencode({'site':'webapps','pagesize':100,'sort':'votes','order':'desc','filter':'withbody'})
  self.path=self.cache/'answer-context'/(m.sha((answer_context.SCHEMA+self.endpoint).encode())+'.json');self.path.parent.mkdir()
  self.payload={'items':[{'question_id':QID,'answer_id':41,'score':100,'body':'SYNTHETIC nonaccepted community advice','owner':{'user_id':8}},{'question_id':QID,'answer_id':42,'score':1,'body':'SYNTHETIC accepted community advice','owner':{'user_id':9},'is_accepted':True}],'has_more':False}
 def saved(self,expiry=NOW+300,**changes):
  data=dict(endpoint=self.endpoint,expires=expiry,payload=self.payload,response_sha256=m.sha(json.dumps(self.payload).encode()),observed_at=STAMP);data.update(changes);return dict(data,integrity_sha256=m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()))
 def run_collect(self,allow_transport=False):
  def transport(url,stats,*args):self.assertEqual(url,self.endpoint);stats['source_requests']+=1;return json.dumps(self.payload).encode()
  with patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'0'}),patch.object(m,'read_http',side_effect=transport if allow_transport else AssertionError('No HTTP')) as intercepted:
   result=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source]))
  if not allow_transport:intercepted.assert_not_called()
  return result,intercepted.call_count
 def assert_primary(self,observations):
  self.assertEqual(len(observations),1)
  for key in ['title','url','context_text','source','author_id','accepted_answer_id','linked_context_urls','source_text_sha256']:
   self.assertEqual(observations[0][key],self.rows[0][key],key)
 def assert_corrupt(self,raw):
  self.path.write_bytes(raw);primary=self.primary.read_bytes();(observations,errors,_),calls=self.run_collect(allow_transport=True)
  self.assertEqual(calls,0,'Damaged answer evidence must not trigger a replacement fetch');self.assertEqual(self.path.read_bytes(),raw);self.assertEqual(self.primary.read_bytes(),primary);self.assert_primary(observations);self.assertEqual(len(errors),1);self.assertEqual(errors[0]['scope'],'answer_context');self.assertTrue(errors[0]['primary_observations_preserved']);self.assertTrue(errors[0]['cache_bytes_preserved']);self.assertFalse(errors[0]['network_retry_performed']);self.assertFalse(errors[0]['retry']);self.assertEqual(observations[0]['answer_fetch_status'],'unavailable_unknown');self.assertFalse(observations[0]['answer_body_available']);self.assertIsNone(observations[0]['answer_text']);self.assertIn('Cached answer context unavailable',observations[0]['answer_collection_limitation']);self.assertEqual(self.stats['answer_cache_errors'],1);self.assertEqual(self.stats['source_cache_hits'],1)
 def test_checksum_mismatch_never_refetches_or_overwrites_primary_or_answer(self):
  self.assert_corrupt(json.dumps(dict(self.saved(),integrity_sha256='0'*64)).encode())
 def test_expired_corrupt_cache_is_not_a_refresh(self):
  self.assert_corrupt(json.dumps(dict(self.saved(expiry=NOW-1),integrity_sha256='0'*64)).encode())
 def test_malformed_cache_stays_enrichment_local_and_preserved(self):
  cases=[b'{broken',b'\xff',b'[]',b'null',json.dumps(self.saved(expires='future')).encode(),json.dumps(self.saved(expires=True)).encode(),json.dumps(self.saved(expires=float('nan'))).encode(),json.dumps(self.saved(endpoint='https://example.invalid/wrong')).encode(),json.dumps(self.saved(payload={})).encode(),json.dumps(self.saved(payload={'items':{}})).encode(),('{"endpoint":"duplicate",'+json.dumps(self.saved())[1:]).encode()]
  for raw in cases:
   with self.subTest(raw=raw[:80]):
    self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};self.assert_corrupt(raw)
 def test_valid_fresh_cache_preserves_answer_selection_and_source_relations(self):
  m.dump(self.path,self.saved());before=inventory(self.cache);(observations,errors,expiry),_=self.run_collect();self.assert_primary(observations);self.assertEqual(errors,[]);self.assertEqual(observations[0]['answer_id'],42);self.assertEqual(observations[0]['answer_author_id'],9);self.assertEqual(observations[0]['answer_selection'],'accepted_answer');self.assertEqual(expiry,NOW+300);self.assertEqual(self.stats['source_cache_hits'],2);self.assertEqual(inventory(self.cache),before)
  related=dict(observations[0],evidence_id='E2',url='https://webapps.stackexchange.com/questions/900000002/synthetic');source_context.annotate_relations([observations[0],related]);packet=model_packet.project([observations[0]])[0];self.assertEqual(packet['same_author_evidence_ids'],['E2']);self.assertEqual(packet['shared_context_evidence_ids'],['E2']);self.assertEqual(packet['observed_text'],self.rows[0]['context_text']);self.assertNotEqual(packet['author_id'],packet['answer_author_id'])
 def test_valid_expired_cache_and_absent_cache_use_normal_mocked_refresh(self):
  for exists in [True,False]:
   with self.subTest(exists=exists):
    if exists:m.dump(self.path,self.saved(expiry=NOW-1))
    else:self.path.unlink()
    self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};(observations,errors,expiry),calls=self.run_collect(allow_transport=True);self.assert_primary(observations);self.assertEqual(calls,1);self.assertEqual(errors,[]);self.assertEqual(observations[0]['answer_id'],42);self.assertEqual(expiry,NOW+3600);self.assertEqual(self.stats.get('answer_cache_errors',0),0);self.assertEqual(json.loads(self.path.read_bytes())['expires'],NOW+3600)
 def test_valid_expired_offline_cache_remains_limitation_not_corruption(self):
  m.dump(self.path,self.saved(expiry=NOW-1));before=self.path.read_bytes()
  with patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'1'}),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')) as transport:observations,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source]))
  transport.assert_not_called();self.assert_primary(observations);self.assertIn('No fresh answer cache',observations[0]['answer_collection_limitation']);self.assertEqual(self.stats.get('answer_cache_errors',0),0);self.assertEqual(self.path.read_bytes(),before)
 def test_unreadable_cache_is_preserved_without_fallback(self):
  m.dump(self.path,self.saved());before=self.path.read_bytes();original=Path.read_text
  def read(path,*args,**kwargs):
   if path==self.path:raise PermissionError('SYNTHETIC denied read')
   return original(path,*args,**kwargs)
  with patch.object(Path,'read_text',read):(observations,errors,_),calls=self.run_collect()
  self.assert_primary(observations);self.assertEqual(calls,0);self.assertEqual(self.path.read_bytes(),before);self.assertEqual(errors[0]['scope'],'answer_context');self.assertTrue(errors[0]['cache_bytes_preserved'])
 def test_unavailable_answer_cache_directory_does_not_drop_primary(self):
  self.path.parent.rmdir();self.path.parent.write_bytes(b'SYNTHETIC damaged cache directory entry');before=self.path.parent.read_bytes()
  (observations,errors,_),calls=self.run_collect();self.assert_primary(observations);self.assertEqual(calls,0);self.assertEqual(self.path.parent.read_bytes(),before);self.assertEqual(errors[0]['scope'],'answer_context');self.assertTrue(errors[0]['primary_observations_preserved'])
 def test_wrong_question_cache_is_validated_even_when_expired(self):
  self.assert_corrupt(json.dumps(self.saved(expiry=NOW-1,payload={'items':[{'question_id':999,'answer_id':42}]})).encode())
 def test_collect_only_pipeline_keeps_primary_and_surfaces_limitation_in_sealed_input(self):
  raw=json.dumps(dict(self.saved(),integrity_sha256='0'*64)).encode();self.path.write_bytes(raw)
  with patch.object(discovery_plan,'select',return_value=([self.source],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')) as transport,patch.object(m,'ask_qwen',side_effect=AssertionError('No model')):
   asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
  transport.assert_not_called();result=json.loads((self.run/'result.json').read_bytes());self.assertEqual(result['status'],'awaiting_analysis');self.assert_primary(result['observations']);self.assertEqual(len(result['source_errors']),1);self.assertEqual(result['source_errors'][0]['scope'],'answer_context');self.assertEqual(result['source_requests'],0);self.assertEqual(result['model_requests'],0);self.assertEqual(result['discovery_summary']['failed_sources'],0);self.assertEqual(result['discovery_summary']['enrichment_limited_sources'],1);self.assertEqual(result['discovery_summary']['captured_records'],1);self.assertEqual(self.path.read_bytes(),raw)
  inputs=list((self.root/'analysis-inputs').glob('*.json'));self.assertEqual(len(inputs),1);saved=json.loads(inputs[0].read_bytes());self.assertIn('Cached answer context unavailable',saved['observations'][0]['answer_collection_limitation']);self.assertEqual(saved['observations'][0]['context_text'],self.rows[0]['context_text'])
 def test_summary_counts_distinct_sources_not_rows_or_enrichment_failures(self):
  errors=[{'source':'webapps','scope':'answer_context','reason':'SYNTHETIC partial limitation'}]*2+[{'source':'bad','reason':'SYNTHETIC full source failure'}]*2
  rows=[dict(self.rows[0],evidence_id='E1')];selected,summary=history.commit(m,self.root,self.run,history.load(m,self.root),rows,errors,{'round':0,'scope':'SYNTHETIC_TEST_ONLY'},self.stats)
  self.assertEqual(summary['failed_sources'],1);self.assertEqual(summary['enrichment_limited_sources'],1);self.assertEqual(summary['captured_records'],1);self.assertEqual(len(selected),1)
 def test_unrelated_runtime_failure_is_not_disguised_as_cache_damage(self):
  with patch.object(m,'read_http',side_effect=RuntimeError('SYNTHETIC programming failure')),self.assertRaisesRegex(RuntimeError,'programming failure'):
   asyncio.run(answer_context.enrich(m,self.cache,self.run,self.stats,self.source,self.rows))
 def test_cancelled_answer_enrichment_propagates(self):
  (self.run/'cancel.request').touch()
  with patch.object(m,'read_http',side_effect=AssertionError('No HTTP')),self.assertRaises(asyncio.CancelledError):asyncio.run(answer_context.enrich(m,self.cache,self.run,self.stats,self.source,self.rows))
def tearDownModule():
 if inventory(SOURCE)!=BEFORE:raise AssertionError('Source bytes changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

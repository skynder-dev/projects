"""Synthetic stdlib regressions for actual history, collection and review queue flows.
Transport, model execution and native Windows publication are not qualified.
"""
from pathlib import Path
import argparse,asyncio,copy,hashlib,json,math,os,selectors,sys,tempfile,time,types,unittest
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
SOURCE=args.source.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE))
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
BEFORE=inventory(SOURCE)
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Collection regressions forbid transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper','aiohttp','crawl4ai'}:raise PermissionError('Collection regressions forbid models/live collectors')
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
import reveng_local_research as m,observation_history as history,analysis_jobs as jobs,source_context,model_packet,answer_context,commercial_review
# Import the actual queue and publisher, but never emulate/qualify Windows locking.
# Every native call is a hard failure; queue tests replace the publication boundary explicitly.
if os.name!='nt':
 native=types.ModuleType('msvcrt');native.LK_NBLCK=1;native.LK_UNLCK=0
 def deny_lock(*args):raise AssertionError('Native Windows locking is untested and forbidden here')
 native.locking=deny_lock
 sys.modules['msvcrt']=native
 try:import candidate_queue as queue,candidate_publication
 finally:sys.modules.pop('msvcrt',None)
else:import candidate_queue as queue,candidate_publication
import research_candidate_review as research
NOW=1792886400;STAMP='2026-10-25T00:00:00+00:00'
def row(number=1,source='hackernews'):
 body='SYNTHETIC recurring export question. Not real source capture.'
 return dict(evidence_id='E1',source=source,title='SYNTHETIC export question '+str(number),url='https://news.ycombinator.com/item?id='+str(900000000+number),kind='public_ask_post',context_text=body,excerpt=body,source_field='story_text',content_scope='original_ask_post',context_truncated=False,observed_at=STAMP,author_id='SYNTHETIC_AUTHOR',answer_text='SYNTHETIC community advice; not verified resolution.',answer_text_truncated=False,answer_id=1,answer_url='https://example.invalid/a/1',answer_author_id=9,answer_link_targets=['https://example.invalid/one'])
def legacy_revision(value):
 packet=source_context.source_packet(value);keys=['title','observed_text','answer_text','source_kind','content_scope','answer_status','answer_count','accepted_answer_id','author_id','media_references','link_targets','answer_media_references']
 return history.digest(m,{key:packet.get(key) for key in keys})
class IntegrityTests(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory(prefix='reveng-collection-synthetic-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);self.run=self.root/'runs'/'synthetic';self.run.mkdir(parents=True);self.cache=self.root/'cache';self.cache.mkdir()
  for target,value in [('time.time',NOW),('reveng_local_research.now',STAMP)]:
   p=patch(target,return_value=value);p.start();self.addCleanup(p.stop)
  self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0}
 def commit(self,rows,index=None):return history.commit(m,self.root,self.run,history.load(m,self.root) if index is None else index,rows,[],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'},self.stats)
 def prepare(self,rows):return jobs.prepare(m,self.root,self.run,rows,[],[],NOW+3600,m.build_model_request(rows))
 def cache_path(self,source):return self.cache/(m.sha((m.VERSION+source_context.SCHEMA+source['url']+('|wp-identity4' if source['kind']=='html' else '')).encode())+'.json')
 def source(self,name='hackernews'):return dict(id=name,url='https://example.invalid/'+name,kind='json',family='SYNTHETIC TEST ONLY')
 def saved(self,source,rows=None,expiry=NOW+300):
  rows=[row(source=source['id'])] if rows is None else rows
  return dict(url=source['url'],expires=expiry,rows=rows,rows_sha256=m.sha(json.dumps(rows,sort_keys=True).encode()))
 def collect(self,sources):
  with patch.object(m,'read_http',side_effect=AssertionError('No synthetic test HTTP')) as transport:
   result=asyncio.run(m.collect(self.cache,self.run,self.stats,sources));transport.assert_not_called();return result
 def test_six_model_packet_changes_are_real_history_deltas(self):
  initial=row();selected,_=self.commit([initial]);self.prepare(selected)
  for key,value in {'answer_author_id':10,'answer_id':2,'answer_url':'https://example.invalid/a/2','answer_link_targets':['https://example.invalid/two'],'context_truncated':True,'answer_text_truncated':True}.items():
   with self.subTest(field=key):
    changed=dict(initial,**{key:value});self.assertNotEqual(model_packet.project([initial]),model_packet.project([changed]));self.assertNotEqual(history.revision(m,initial),history.revision(m,changed))
    selected,summary=self.commit([changed]);self.assertEqual(summary['updated_existing'],1);self.assertEqual(len(selected),1)
    self.commit([initial])
 def test_additional_model_semantics_change_revision(self):
  initial=row()
  for key,value in {'source_field':'other_field','source_text_chars':999,'answer_body_available':True,'answer_scope':'partial_answer','answer_selection':'accepted','answer_api_is_accepted':True,'answer_score':4,'answer_fetch_status':'partial','answer_batch_has_more':True,'answers_returned_for_question':5,'accepted_answer_not_returned':True,'answer_resolution':'unknown','answer_collection_limitation':'SYNTHETIC limitation','media_reference_count':1,'media_element_count':1,'media_references_truncated':True,'link_target_count':2,'link_targets_truncated':True,'external_reference_scope':'incomplete','answer_media_reference_count':1,'answer_media_element_count':1,'answer_media_references_truncated':True,'answer_link_target_count':2,'answer_link_targets_truncated':True,'published_at':'2026-01-01T00:00:00Z','collection_limitations':['SYNTHETIC limitation']}.items():
   with self.subTest(field=key):
    changed=dict(initial,**{key:value});self.assertNotEqual(model_packet.project([initial]),model_packet.project([changed]));self.assertNotEqual(history.revision(m,initial),history.revision(m,changed))
 def test_recapture_and_derived_metadata_alone_do_not_reprepare(self):
  initial=row();selected,_=self.commit([initial]);self.prepare(selected)
  changed=dict(initial,observed_at='2026-10-26T00:00:00Z',context_observed_at='2026-10-26T00:00:00Z',answer_observed_at='2026-10-26T00:00:00Z',evidence_id='E9',first_observed_at='1999-01-01',novelty='updated_existing',prior_same_author_count=12,prior_same_author_urls=['https://example.invalid/other'],same_author_evidence_ids=['E10'],shared_context_evidence_ids=['E10'],response_sha256='b'*64)
  self.assertEqual(history.revision(m,initial),history.revision(m,changed));selected,summary=self.commit([changed]);self.assertEqual(selected,[]);self.assertEqual(summary['unchanged_seen'],1);self.assertEqual(summary['recovered_unprepared'],0)
 def test_policy_migration_keeps_sealed_bytes_jobs_decisions_and_legacy_refs(self):
  initial=row();old_hash=legacy_revision(initial);initial.update(source_revision_hash=old_hash,observation_id=history.identity(m,initial))
  payload=dict(schema='reveng-observation-snapshot',captured_at=STAMP,plan={'round':0},observations=[initial],source_errors=[],stats={},delta={});snapshot=history.digest(m,payload);m.dump(self.root/'observation-snapshots'/(snapshot+'.json'),dict(payload,integrity_sha256=snapshot))
  identifier=self.prepare([initial]);m.dump(self.root/'owner-decisions.json',{'SYNTHETIC_DECISION':{'job':identifier,'source_revision_hash':old_hash}});before=inventory(self.root)
  index=history.load(m,self.root);self.assertEqual(before,inventory(self.root));self.assertEqual(index['revision_policy'],history.REVISION_POLICY)
  refs=index['revision_references'][history.identity(m,initial)];self.assertTrue(any(r.get('recorded_revision_hash')==old_hash and r.get('input_sha256')==identifier for r in refs));self.assertTrue(any(r.get('recorded_revision_hash')==old_hash and r.get('observation_snapshot_id')==snapshot for r in refs));self.assertNotEqual(old_hash,index['records'][history.identity(m,initial)]['revision_hash'])
  selected,summary=self.commit([row()],index);self.assertEqual(selected,[]);self.assertEqual(summary['unchanged_seen'],1)
  for name,pin in before.items():
   if name not in {'runs/synthetic/discovery-summary.json','observation-index.json'}:self.assertEqual(inventory(self.root)[name],pin,name)
  self.assertIn(identifier,jobs.load_queue(m,self.root)['jobs'])
 def test_colliding_legacy_revisions_map_to_distinct_semantics(self):
  a=row();b=dict(a,answer_id=2);old=legacy_revision(a);self.assertEqual(old,legacy_revision(b))
  for value in [a,b]:value['source_revision_hash']=old;self.prepare([value])
  index=history.load(m,self.root);key=history.identity(m,a);self.assertEqual(len(index['prepared_revisions'][key]),2);refs=index['revision_references'][key];self.assertEqual({r['recorded_revision_hash'] for r in refs},{old});self.assertEqual(len({r['semantic_revision_hash'] for r in refs}),2)
 def test_new_snapshot_and_rows_label_policy(self):
  selected,summary=self.commit([row()]);self.assertEqual(selected[0]['source_revision_policy'],history.REVISION_POLICY);saved=json.loads((self.root/summary['snapshot_file']).read_bytes());self.assertEqual(saved['revision_policy'],history.REVISION_POLICY);self.assertEqual(summary['revision_policy'],history.REVISION_POLICY)
 def test_unprepared_unchanged_semantics_are_recovered_once(self):
  self.commit([row()]);selected,summary=self.commit([row()]);self.assertEqual(summary['recovered_unprepared'],1);self.prepare(selected);selected,summary=self.commit([row()]);self.assertEqual(selected,[]);self.assertEqual(summary['recovered_unprepared'],0)
 def test_damaged_cache_is_source_local_preserved_and_never_refetched(self):
  bad=self.source('bad');good=self.source();m.dump(self.cache_path(good),self.saved(good))
  variants=[b'{broken',b'\xff',b'['*10000+b'0'+b']'*10000,b'[]',b'null',b'42',json.dumps(dict(self.saved(bad),expires='future')).encode(),json.dumps(dict(self.saved(bad),expires=True)).encode(),json.dumps(dict(self.saved(bad),expires=float('nan'))).encode(),json.dumps(self.saved(bad,rows={})).encode(),json.dumps(self.saved(bad,rows=[None])).encode(),json.dumps(self.saved(bad,rows=[{}])).encode(),json.dumps(self.saved(bad,rows=[])).encode(),json.dumps(dict(self.saved(bad),rows_sha256='0'*64)).encode(),json.dumps(dict(self.saved(bad),url='https://example.invalid/wrong')).encode()]
  for raw in variants:
   with self.subTest(raw=raw[:80]):
    path=self.cache_path(bad);path.write_bytes(raw);self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};observations,errors,_=self.collect([bad,good]);self.assertEqual(len(observations),1);self.assertEqual(len(errors),1);self.assertEqual(errors[0]['source'],'bad');self.assertFalse(errors[0]['retry']);self.assertTrue(errors[0]['cache_bytes_preserved']);self.assertEqual(path.read_bytes(),raw);self.assertEqual(self.stats['source_requests'],0);self.assertEqual(self.stats['source_cache_hits'],1);self.assertEqual(self.stats['source_cache_errors'],1)
 def test_unreadable_cache_is_local_and_not_overwritten(self):
  bad=self.source('bad');good=self.source();path=self.cache_path(bad);m.dump(path,self.saved(bad));m.dump(self.cache_path(good),self.saved(good));before=path.read_bytes();original=Path.read_text
  def read(value,*args,**kwargs):
   if value==path:raise PermissionError('SYNTHETIC unreadable cache')
   return original(value,*args,**kwargs)
  with patch.object(Path,'read_text',read):observations,errors,_=self.collect([bad,good])
  self.assertEqual(len(observations),1);self.assertEqual(len(errors),1);self.assertEqual(path.read_bytes(),before);self.assertTrue(errors[0]['cache_bytes_preserved'])
 def test_valid_expired_cache_remains_a_normal_offline_miss(self):
  source=self.source();path=self.cache_path(source);m.dump(path,self.saved(source,expiry=NOW-1));before=path.read_bytes()
  with patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'1'}):observations,errors,_=self.collect([source])
  self.assertEqual(observations,[]);self.assertEqual(len(errors),1);self.assertIn('No fresh source cache',errors[0]['reason']);self.assertEqual(self.stats.get('source_cache_errors',0),0);self.assertEqual(path.read_bytes(),before)
 def test_enrichment_exception_is_source_local(self):
  bad=self.source('bad');good=self.source();m.dump(self.cache_path(bad),self.saved(bad));m.dump(self.cache_path(good),self.saved(good));original=answer_context.enrich
  async def enrich(module,cache,run,stats,source,rows,source_errors=None):
   if source['id']=='bad':raise ValueError('SYNTHETIC enrichment failure')
   return await original(module,cache,run,stats,source,rows,source_errors)
  with patch.object(answer_context,'enrich',enrich):observations,errors,_=self.collect([bad,good])
  self.assertEqual(len(observations),1);self.assertEqual(len(errors),1);self.assertIn('enrichment',errors[0]['reason'])
 def test_cancelled_enrichment_stays_cancellation(self):
  source=self.source();m.dump(self.cache_path(source),self.saved(source))
  async def cancel(*args):raise asyncio.CancelledError()
  with patch.object(answer_context,'enrich',cancel),self.assertRaises(asyncio.CancelledError):self.collect([source])
 def test_actual_pipeline_preserves_partial_sources_and_errors(self):
  import discovery_plan
  bad=self.source('bad');good=self.source();self.cache_path(bad).write_bytes(b'{broken');m.dump(self.cache_path(good),self.saved(good))
  with patch.object(discovery_plan,'select',return_value=([bad,good],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')),patch.object(m,'ask_qwen',side_effect=AssertionError('No model')):
   asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
  result=json.loads((self.run/'result.json').read_bytes());self.assertEqual(result['status'],'awaiting_analysis');self.assertEqual(len(result['observations']),1);self.assertEqual(len(result['source_errors']),1);self.assertEqual(result['discovery_summary']['failed_sources'],1);self.assertEqual(result['discovery_summary']['captured_records'],1);self.assertEqual(result['source_requests'],0);self.assertEqual(result['model_requests'],0);self.assertEqual(result['source_cache_errors'],1)
 def test_sparse_title_only_and_empty_title_api_rows_keep_existing_contract(self):
  import discovery_plan
  wordpress=copy.deepcopy(m.SOURCES[0]);hn=self.source();sparse=dict(source='wordpress',title='SYNTHETIC sparse topic title',url='https://wordpress.org/support/topic/synthetic-offline-test/',kind='public_topic_title');api=dict(source='hackernews',title='',url='https://news.ycombinator.com/item?id=900000009',kind='public_ask_post',context_text='SYNTHETIC original post with missing title')
  m.dump(self.cache_path(wordpress),self.saved(wordpress,rows=[sparse]));m.dump(self.cache_path(hn),self.saved(hn,rows=[api]))
  with patch.object(discovery_plan,'select',return_value=([wordpress,hn],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')):asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
  result=json.loads((self.run/'result.json').read_bytes());self.assertEqual(result['status'],'awaiting_analysis');self.assertEqual(len(result['observations']),2);self.assertEqual(result['source_errors'],[]);self.assertEqual(result['source_cache_hits'],2);self.assertEqual(result['source_requests'],0);packets=model_packet.project(result['observations']);self.assertEqual(packets[0]['content_scope'],'title_only');self.assertNotIn('observed_text',packets[0]);self.assertEqual(packets[1]['title'],'')
 def test_malformed_cached_row_cannot_escape_into_downstream_pipeline(self):
  import discovery_plan
  bad=self.source('bad');good=self.source();m.dump(self.cache_path(good),self.saved(good))
  cases=[dict(url='https:/questions/123/test'),dict(url='https://example.invalid:bad/test'),dict(url='https://user@example.invalid/test'),dict(linked_context_urls=[{}]),dict(linked_context_urls=None),dict(linked_context_urls='not-a-list'),dict(author_id={}),dict(title='SYNTHETIC \ud800'),dict(unrelated=float('inf'))]
  for change in cases:
   with self.subTest(change=change):
    path=self.cache_path(bad);path.write_text(json.dumps(self.saved(bad,rows=[dict(row(source='bad'),**change)])),encoding='utf-8');before=path.read_bytes()
    with patch.object(discovery_plan,'select',return_value=([good,bad],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')):asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
    result=json.loads((self.run/'result.json').read_bytes());self.assertEqual(len(result['source_errors']),1);self.assertEqual(result['discovery_summary']['failed_sources'],1);self.assertEqual(result['discovery_summary']['captured_records'],1);self.assertEqual(result['source_cache_errors'],1);self.assertEqual(result['source_requests'],0);self.assertEqual(path.read_bytes(),before)
 def test_corrupt_expired_and_duplicate_key_caches_are_not_refreshes(self):
  source=self.source();path=self.cache_path(source);saved=self.saved(source,expiry=NOW-1)
  variants=[json.dumps(dict(saved,rows_sha256='0'*64)).encode(),('{"url":"https://example.invalid/hackernews",'+json.dumps(saved)[1:]).encode(),json.dumps(dict(saved,rows=[dict(row(),context_text=[])])).encode()]
  for raw in variants:
   with self.subTest(raw=raw[:70]):
    path.write_bytes(raw);observations,errors,_=self.collect([source]);self.assertEqual(observations,[]);self.assertEqual(len(errors),1);self.assertTrue(errors[0]['cache_bytes_preserved']);self.assertEqual(path.read_bytes(),raw)
 def test_valid_expired_cache_still_uses_existing_refresh_path_with_synthetic_transport(self):
  source=self.source();path=self.cache_path(source);m.dump(path,self.saved(source,expiry=NOW-1));before=path.read_bytes();payload=json.dumps({'hits':[{'objectID':'900000001','title':'SYNTHETIC replacement','story_text':'SYNTHETIC replacement context','author':'SYNTHETIC'}]}).encode()
  def transport(url,stats,*args):self.assertEqual(url,source['url']);stats['source_requests']+=1;return payload
  with patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'0'}),patch.object(m,'read_http',side_effect=transport) as intercepted:
   observations,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[source]))
  self.assertEqual(intercepted.call_count,1);self.assertEqual(errors,[]);self.assertEqual(len(observations),1);self.assertNotEqual(path.read_bytes(),before);self.assertEqual(self.stats['source_requests'],1);self.assertEqual(self.stats.get('source_cache_errors',0),0)
 def test_all_damaged_sources_produce_no_job_and_accurate_failed_count(self):
  import discovery_plan
  sources=[self.source('bad1'),self.source('bad2')]
  for source in sources:self.cache_path(source).write_bytes(b'{broken')
  with patch.object(discovery_plan,'select',return_value=(sources,{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=AssertionError('No HTTP')),patch.object(m,'ask_qwen',side_effect=AssertionError('No model')):asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
  result=json.loads((self.run/'result.json').read_bytes());self.assertEqual(result['status'],'no_observations');self.assertEqual(len(result['source_errors']),2);self.assertEqual(result['discovery_summary']['failed_sources'],2);self.assertEqual(result['discovery_summary']['captured_records'],0);self.assertFalse((self.root/'analysis-queue.json').exists());self.assertEqual(result['source_cache_errors'],2)
 def test_tampered_snapshot_still_fails_closed_without_migration_writes(self):
  _,summary=self.commit([row()]);path=self.root/summary['snapshot_file'];data=json.loads(path.read_bytes());data['observations'][0]['answer_id']=99;m.dump(path,data);before=inventory(self.root)
  with self.assertRaisesRegex(ValueError,'snapshot integrity mismatch'):history.load(m,self.root)
  self.assertEqual(inventory(self.root),before)
 def test_queue_reports_research_pause_and_resumes_without_recollecting_completed_cards(self):
  card={key:'SYNTHETIC proposal not validated or collected.' for key in ['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','alternatives_and_limits']};card.update(market_category='other',observed_basis=[row()],evidence_ids=['E1'],risks=[],missing_evidence=[])
  card=commercial_review.merge_ledger([],[card])[0];m.dump(self.root/'candidates.json',[card]);data=dict(status='completed',hypotheses=[card]);m.dump(self.root/'latest-result.json',dict(data,cache_payload_sha256=queue.digest(data)))
  research_cards=[dict(card,research_id='SYNTHETIC_R1',observed_basis=[row(2)]),dict(card,research_id='SYNTHETIC_R2',observed_basis=[row(3)])];calls=[];phase=[0]
  async def collect(root,run,cards,stats,offline=False):
   value=cards[0];id=value.get('research_id','business');calls.append(id);url=value['observed_basis'][0]['url'];report=dict(source_url=url,facts=[],expires=NOW+300,observed_at=STAMP)
   if id=='SYNTHETIC_R2' and phase[0]==0:report['error']='Source request budget exhausted'
   return {url:report}
  async def direct(*args,**kwargs):return []
  def publish(root,run,before_cards,before_latest,cards,data):
   self.assertEqual((root/'candidates.json').read_bytes(),before_cards);self.assertEqual((root/'latest-result.json').read_bytes(),before_latest);m.dump(root/'candidates.json',cards);m.dump(root/'latest-result.json',data)
  with patch.object(candidate_publication,'recover',return_value=False),patch.object(candidate_publication,'publish',side_effect=publish) as publication,patch.object(queue.research_review,'refresh',return_value={'cards':research_cards}),patch.object(queue.buyer,'collect',collect),patch.object(queue.direct,'collect',direct):
   asyncio.run(queue.execute(self.root,self.run,offline=True));first=json.loads((self.run/'result.json').read_bytes());progress=json.loads((self.root/'candidate-progress.json').read_bytes());self.assertEqual(first['status'],'paused_budget',(first.get('research_public_review'),calls));self.assertEqual(progress['status'],'paused_budget');self.assertEqual(first['research_public_review']['completed'],1);self.assertEqual(first['research_public_review']['eligible'],2);self.assertEqual(publication.call_count,1)
   saved=json.loads((self.root/'candidates.json').read_bytes());self.assertIn('buyer_demand_review',saved[0]);self.assertEqual(saved[0]['candidate_id'],card['candidate_id']);self.assertEqual(progress['items'][card['candidate_id']]['signature'],queue.signature(saved[0]));version_before=copy.deepcopy(research.load(self.root)['items']['SYNTHETIC_R1']['research_versions']);phase[0]=1
   asyncio.run(queue.execute(self.root,self.run,offline=True));final=json.loads((self.run/'result.json').read_bytes());self.assertEqual(final['status'],'completed');self.assertEqual(final['candidate_cache_hits'],1);self.assertEqual(final['research_public_review']['completed'],2);self.assertEqual(calls.count('business'),1);self.assertEqual(calls.count('SYNTHETIC_R1'),1);self.assertEqual(calls.count('SYNTHETIC_R2'),2);self.assertEqual(research.load(self.root)['items']['SYNTHETIC_R1']['research_versions'],version_before)

class ApiRowIsolationTests(unittest.TestCase):
 setUp=IntegrityTests.setUp
 cache_path=IntegrityTests.cache_path
 saved=IntegrityTests.saved
 def source(self,name='webapps'):
  return copy.deepcopy(next(s for s in m.SOURCES if s['id']==name))
 def good(self,**changes):
  return dict(title='SYNTHETIC valid original question',link='https://webapps.stackexchange.com/questions/900000001/synthetic',question_id=900000001,body='<p>SYNTHETIC healthy question retained.</p>',owner={'user_id':7},answer_count=0,**changes)
 def parse(self,items,source=None):
  rejected=[];rows=source_context.parse_api(source or self.source(),{'items':items},rejected);return rows,rejected
 def collect_payload(self,payload,sources=None):
  source=self.source();payload=payload if isinstance(payload,bytes) else json.dumps(payload).encode();calls=[]
  def transport(url,stats,*args):
   calls.append(url);stats['source_requests']+=1
   return b'{"items":[]}' if '/answers?' in url else payload
  with patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'0'}),patch.object(m,'read_http',side_effect=transport),patch.object(asyncio,'sleep',new=__import__('unittest.mock',fromlist=['AsyncMock']).AsyncMock()):
   result=asyncio.run(m.collect(self.cache,self.run,self.stats,sources or [source]))
  return result,calls,payload
 def test_malformed_row_keeps_healthy_sibling_in_both_orders(self):
  for bad in [None,{}, {'title':'Broken'},dict(self.good(),owner=[]),dict(self.good(),answer_count='2'),dict(self.good(),body={}),dict(self.good(),link='https://webapps.stackexchange.com/questions/'+'1'*5000+'/x'),dict(self.good(),link='https://webapps.stackexchange.com/questions/900000001/\ud800')]:
   for items in [[self.good(),bad],[bad,self.good()]]:
    with self.subTest(items=items):
     original=copy.deepcopy(items);rows,rejected=self.parse(items);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['question_id'],900000001);self.assertEqual(len(rejected),1);self.assertEqual(items,original)
 def test_wrong_host_question_or_source_identity_is_rejected_not_guessed(self):
  variants=[{'link':'https://stackoverflow.com/questions/900000001/x'},{'question_id':2},{'question_id':True},{'question_id':'900000001'},{'link':'https://webapps.stackexchange.com/questions/900000001/42'},{'link':'https://webapps.stackexchange.com/a/900000001'},{'link':'https://user@webapps.stackexchange.com/questions/900000001/x'},{'link':'http://webapps.stackexchange.com/questions/900000001/x'},{'link':'https://webapps.stackexchange.com/questions/900000001/x#42'},{'link':'https://webapps.stackexchange.com/questions/900000001/x?answer=42'}]
  for changes in variants:
   with self.subTest(changes=changes):
    rows,rejected=self.parse([dict(self.good(),**changes),self.good()]);self.assertEqual(len(rows),1);self.assertEqual(len(rejected),1)
  for source in [dict(self.source(),site='travel'),dict(self.source(),id='unknown',site='webapps')]:
   rows,rejected=self.parse([self.good()],source);self.assertEqual(rows,[]);self.assertEqual(len(rejected),1)
 def test_known_sites_and_missing_legacy_question_id_remain_valid(self):
  for name,site in source_context.SE_SITES.items():
   source={'id':name,'site':site};host='superuser.com' if site=='superuser' else site+'.stackexchange.com';item=dict(self.good(),link='https://'+host+'/questions/900000001/new-slug?utm_source=test#top');item.pop('question_id')
   rows,rejected=self.parse([item],source);self.assertEqual(len(rows),1);self.assertEqual(rejected,[]);self.assertEqual(rows[0]['question_id'],900000001);self.assertNotIn('question_id',item)
 def test_sparse_deleted_owner_and_empty_title_still_accepted(self):
  item=dict(self.good(),title='',owner=None);item.pop('body');rows,rejected=self.parse([item]);self.assertEqual(rejected,[]);self.assertEqual(rows[0]['kind'],'public_question_title');self.assertEqual(rows[0]['title'],'');self.assertIsNone(rows[0]['author_id'])
 def test_other_api_provider_malformed_items_are_row_local(self):
  cases=[('hackernews','hits',{'objectID':'900000002','story_text':'SYNTHETIC healthy ask post'},[None,{}, {'objectID':'not/an/id'}]),('npm','objects',{'package':{'name':'@synthetic/test','description':'SYNTHETIC package'}},[None,{}, {'package':{'name':[]}}])]
  for name,key,good,bad in cases:
   rejected=[];rows=source_context.parse_api(self.source(name),{key:[bad[0],good,*bad[1:]]},rejected);self.assertEqual(len(rows),1);self.assertEqual(len(rejected),3)
 def test_unsafe_npm_name_does_not_create_misleading_package_url(self):
  for name in ['../other','@scope/../other','bad name','foo\\bar','@scope/..']:
   rejected=[];rows=source_context.parse_api(self.source('npm'),{'objects':[{'package':{'name':name}},{'package':{'name':'@synthetic/real-package'}}]},rejected);self.assertEqual(len(rows),1);self.assertEqual(len(rejected),1)
 def test_backoff_error_and_invalid_envelope_remain_batch_failures(self):
  for obj in [None,[],{}, {'items':{}},{'items':[self.good()],'backoff':1},{'items':[self.good()],'error_id':502}]:
   with self.subTest(obj=obj),self.assertRaises(ValueError):source_context.parse_api(self.source(),obj,[])
 def test_existing_five_item_bound_is_preserved(self):
  rows,rejected=self.parse([None]*5+[self.good()]);self.assertEqual(rows,[]);self.assertEqual(len(rejected),5)
 def test_unrelated_parser_exception_is_not_disguised_as_bad_row(self):
  with patch.object(source_context,'context',side_effect=RuntimeError('SYNTHETIC coding fault')),self.assertRaisesRegex(RuntimeError,'coding fault'):self.parse([self.good()])
 def test_partial_collect_retains_raw_and_replays_rejection_without_transport(self):
  (rows,errors,_),calls,payload=self.collect_payload({'items':[None,self.good()]});self.assertEqual(len(rows),1);self.assertEqual(len(calls),2);self.assertEqual(len(errors),1);failure=errors[0];self.assertEqual(failure['scope'],'primary_rows');self.assertEqual(failure['accepted_rows'],1);self.assertEqual(failure['rejected_rows'],1);self.assertTrue(failure['primary_observations_preserved']);self.assertEqual((self.cache/failure['response_receipt']['raw_file']).read_bytes(),payload);before=inventory(self.cache)
  with patch.object(m,'read_http',side_effect=AssertionError('No fallback')):again=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(again[1],errors);self.assertEqual(again[0],rows);self.assertEqual(inventory(self.cache),before)
 def test_all_rejected_keeps_raw_without_primary_or_answer_cache(self):
  (rows,errors,_),calls,payload=self.collect_payload({'items':[None,{'title':'Broken'}]});self.assertEqual(rows,[]);self.assertEqual(len(calls),1);self.assertEqual(len(errors),1);self.assertEqual(errors[0]['rejected_rows'],2);self.assertEqual(errors[0]['accepted_rows'],0);self.assertFalse(errors[0]['retry']);self.assertEqual((self.cache/errors[0]['response_receipt']['raw_file']).read_bytes(),payload);self.assertFalse(self.cache_path(self.source()).exists());self.assertFalse((self.cache/'answer-context').exists())
 def test_error_backoff_and_bad_json_raw_are_retained_without_retry(self):
  for payload in [b'{broken',b'{"items":[],"backoff":1}',b'{"error_id":502,"items":[]}']:
   (rows,errors,_),calls,raw=self.collect_payload(payload);self.assertEqual(rows,[]);self.assertEqual(len(calls),1);self.assertEqual(len(errors),1);self.assertFalse(errors[0]['retry']);self.assertEqual((self.cache/errors[0]['response_receipt']['raw_file']).read_bytes(),raw)
 def test_cache_wrong_provider_identity_preserved_even_when_expired(self):
  source=self.source();parsed=self.parse([self.good()])[0][0]
  for changes in [{'url':'https://stackoverflow.com/questions/900000001/x'},{'question_id':2}]:
   values=[dict(parsed,source=source['id'],**changes)];path=self.cache_path(source);m.dump(path,self.saved(source,rows=values,expiry=NOW-1));before=path.read_bytes()
   with patch.object(m,'read_http',side_effect=AssertionError('No fallback')):rows,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[source]))
   self.assertEqual(rows,[]);self.assertEqual(len(errors),1);self.assertTrue(errors[0]['cache_bytes_preserved']);self.assertEqual(path.read_bytes(),before)
 def test_valid_legacy_cache_missing_id_is_not_rewritten(self):
  source=self.source();value=self.parse([self.good()])[0][0];value.update(source=source['id']);value.pop('question_id');path=self.cache_path(source);m.dump(path,self.saved(source,rows=[value]));before=path.read_bytes()
  (rows,errors,_),calls,_=self.collect_payload({'items':[]});self.assertEqual(len(calls),1);self.assertEqual(errors,[]);self.assertEqual(path.read_bytes(),before);self.assertNotIn('question_id',rows[0])
 def test_cancellation_propagates_without_retry_or_source_failure(self):
  with patch.object(m,'read_http',side_effect=asyncio.CancelledError()),self.assertRaises(asyncio.CancelledError):asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(list(self.cache.iterdir()),[])
 def test_later_enrichment_failure_does_not_double_count_partial_rows(self):
  async def broken(*args):raise RuntimeError('SYNTHETIC later enrichment failure')
  with patch.object(answer_context,'enrich',broken):(rows,errors,_),calls,payload=self.collect_payload({'items':[None,self.good()]})
  self.assertEqual(rows,[]);self.assertEqual(len(errors),1);self.assertFalse(errors[0]['primary_observations_preserved']);self.assertEqual(errors[0]['accepted_rows'],1);self.assertEqual(errors[0]['rejected_rows'],1)
  _,summary=history.commit(m,self.root,self.run,history.load(m,self.root),rows,errors,{'round':0},self.stats);self.assertEqual(summary['partial_sources'],0);self.assertEqual(summary['failed_sources'],1);self.assertEqual(summary['rejected_rows'],1)
 def test_real_collect_only_pipeline_reports_partial_not_failed_source(self):
  import discovery_plan
  source=self.source();payload=json.dumps({'items':[None,self.good()]}).encode()
  def transport(url,stats,*args):stats['source_requests']+=1;return b'{"items":[]}' if '/answers?' in url else payload
  with patch.object(discovery_plan,'select',return_value=([source],{'round':0,'scope':'SYNTHETIC_TEST_ONLY'})),patch.object(m,'read_http',side_effect=transport),patch.object(m,'ask_qwen',side_effect=AssertionError('No model')),patch.object(asyncio,'sleep',new=__import__('unittest.mock',fromlist=['AsyncMock']).AsyncMock()):asyncio.run(m.pipeline(self.root,self.run,collect_only=True))
  result=json.loads((self.run/'result.json').read_bytes());summary=result['discovery_summary'];self.assertEqual(result['status'],'awaiting_analysis');self.assertEqual(summary['captured_records'],1);self.assertEqual(summary['failed_sources'],0);self.assertEqual(summary['partial_sources'],1);self.assertEqual(summary['rejected_rows'],1);self.assertEqual(summary['enrichment_limited_sources'],0);self.assertEqual(result['model_requests'],0)
  snapshot=json.loads((self.root/summary['snapshot_file']).read_bytes());self.assertEqual(snapshot['source_errors'][0]['scope'],'primary_rows');self.assertEqual(snapshot['observations'][0]['question_id'],900000001)

class HtmlNormalizationTests(unittest.TestCase):
 setUp=IntegrityTests.setUp
 cache_path=IntegrityTests.cache_path
 saved=IntegrityTests.saved
 source=ApiRowIsolationTests.source
 good=ApiRowIsolationTests.good
 parse=ApiRowIsolationTests.parse
 collect_payload=ApiRowIsolationTests.collect_payload
 commit=IntegrityTests.commit
 prepare=IntegrityTests.prepare
 def answer_cache(self,parser_version=None,expiry=NOW+300):
  source=self.source();endpoint='https://api.stackexchange.com/2.3/questions/900000001/answers?'+answer_context.urlencode({'site':'webapps','pagesize':100,'sort':'votes','order':'desc','filter':'withbody'})
  payload={'items':[{'question_id':900000001,'answer_id':42,'body':'<p>un<strong>paid</strong> costs $1<span>,000</span></p>'}]}
  saved=dict(endpoint=endpoint,expires=expiry,payload=payload,response_sha256=m.sha(json.dumps(payload).encode()),observed_at=STAMP)
  if parser_version is not None:saved['text_parser_version']=parser_version
  path=self.cache/'answer-context'/(m.sha((answer_context.SCHEMA+endpoint).encode())+'.json');m.dump(path,dict(saved,integrity_sha256=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode())));return path,endpoint,payload
 def primary(self,legacy=False):
  source=self.source();value=self.parse([dict(self.good(),body='<p>un<strong>paid</strong> costs $1<span>,000</span></p>')])[0][0];value.update(source=source['id'],observed_at=STAMP)
  if legacy:
   value.update(source_context.context('<p>un<strong>paid</strong> costs $1<span>,000</span></p>','body','question_body',parser_version=source_context.LEGACY_TEXT_PARSER));value.pop('text_parser_version');value.pop('title_text_parser_version',None);value.pop('api_parser_version',None)
  path=self.cache_path(source);m.dump(path,self.saved(source,rows=[value]));return path,value
 def test_inline_words_numbers_entities_links_and_scripts(self):
  cases={'un<strong>paid</strong>':'unpaid','<p>$1<span>,000</span> per month</p>':'$1,000 per month','<span>12</span><i>.</i><b>50</b>':'12.50','caf<b>é</b> &amp; tea':'café & tea','x<strong> y </strong>z':'x y z','https://example.<em>invalid</em>/path':'https://example.invalid/path','un<script>fake text</script><style>fake style</style>paid':'unpaid','hello<!-- hidden -->world':'helloworld'}
  for raw,expected in cases.items():
   with self.subTest(raw=raw):self.assertEqual(source_context.text(raw),expected)
 def test_block_boundaries_remain_separators_not_joined_words(self):
  for tag in ['p','div','li','pre','h1','h6','blockquote','section','article','td','th','dt','dd','figcaption','table']:
   with self.subTest(tag=tag):self.assertEqual(source_context.text('<'+tag+'>one</'+tag+'><'+tag+'>two</'+tag+'>'),'one two')
  self.assertEqual(source_context.text('one<br/>two<hr>three'),'one two three')
 def test_legacy_parser_reproduces_old_inline_and_incomplete_tag_behavior(self):
  self.assertEqual(source_context.text('un<strong>paid</strong> $1<span>,000</span>',source_context.LEGACY_TEXT_PARSER),'un paid $1 ,000');self.assertEqual(source_context.text('text <unfinished',source_context.LEGACY_TEXT_PARSER),'text')
  with self.assertRaises(ValueError):source_context.text('text','unknown-parser')
 def test_hashes_truncation_and_reference_metadata_bind_new_text(self):
  raw='<p>$1<span>,000</span> '+('x'*12010)+'</p><a href="https://example.invalid">linked</a><img src="https://example.invalid/x.png">';result=source_context.context(raw,'body','question_body');full=source_context.text(raw)
  self.assertEqual(result['text_parser_version'],source_context.TEXT_PARSER);self.assertEqual(result['source_text_sha256'],m.sha(full.encode()));self.assertEqual(result['context_text_sha256'],m.sha(full[:12000].encode()));self.assertEqual(result['context_text'],full[:12000]);self.assertEqual(result['excerpt'],full[:2000]);self.assertTrue(result['context_truncated']);self.assertEqual(result['link_targets'],['https://example.invalid']);self.assertEqual(result['media_reference_count'],1)
 def test_plain_descriptions_are_not_reparsed_as_html(self):
  value=source_context.context('literal un<strong>paid</strong>  2','description','package_description_only',False);self.assertEqual(value['context_text'],'literal un<strong>paid</strong> 2');self.assertEqual(value['text_parser_version'],'plain-whitespace-v1')
 def test_real_api_collection_labels_corrected_question_and_title(self):
  item=dict(self.good(),title='un<strong>paid</strong> question',body='<p>$1<span>,000</span> per month</p>');(rows,errors,_),calls,raw=self.collect_payload({'items':[item]});self.assertEqual(errors,[]);self.assertEqual(rows[0]['title'],'unpaid question');self.assertEqual(rows[0]['context_text'],'$1,000 per month');self.assertEqual(rows[0]['text_parser_version'],source_context.TEXT_PARSER);self.assertEqual(rows[0]['title_text_parser_version'],source_context.TEXT_PARSER);self.assertEqual(rows[0]['observed_at'],STAMP);self.assertEqual((self.cache/'source-payloads'/(m.sha(raw)+'.raw')).read_bytes(),raw)
 def test_legacy_primary_and_answer_cache_preserve_text_dates_and_bytes(self):
  primary,value=self.primary(True);path,endpoint,payload=self.answer_cache();before=inventory(self.cache)
  with patch.object(m,'read_http',side_effect=AssertionError('No recapture')):rows,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(errors,[]);self.assertEqual(rows[0]['context_text'],'un paid costs $1 ,000');self.assertEqual(rows[0]['answer_text'],'un paid costs $1 ,000');self.assertNotIn('text_parser_version',rows[0]);self.assertEqual(rows[0]['answer_text_parser_version'],source_context.LEGACY_TEXT_PARSER);self.assertEqual(rows[0]['observed_at'],STAMP);self.assertEqual(rows[0]['answer_observed_at'],STAMP);self.assertEqual(inventory(self.cache),before)
 def test_recorded_current_answer_parser_is_used_on_reuse(self):
  self.primary();path,endpoint,payload=self.answer_cache(source_context.TEXT_PARSER);before=inventory(self.cache)
  with patch.object(m,'read_http',side_effect=AssertionError('No recapture')):rows,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(errors,[]);self.assertEqual(rows[0]['answer_text'],'unpaid costs $1,000');self.assertEqual(rows[0]['answer_text_parser_version'],source_context.TEXT_PARSER);self.assertEqual(inventory(self.cache),before)
 def test_unknown_answer_parser_is_local_limitation_without_replacement(self):
  self.primary();path,endpoint,payload=self.answer_cache('future-unknown',NOW-1);before=inventory(self.cache)
  with patch.object(m,'read_http',side_effect=AssertionError('No recapture')):rows,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(len(rows),1);self.assertEqual(len(errors),1);self.assertEqual(errors[0]['scope'],'answer_context');self.assertIn('parser version',errors[0]['reason']);self.assertEqual(inventory(self.cache),before)
 def test_valid_expired_answer_refresh_records_current_parser_not_new_old_date(self):
  self.primary(True);path,endpoint,payload=self.answer_cache(expiry=NOW-1);stamp='2026-10-25T00:01:00+00:00'
  def transport(url,stats,*args):self.assertEqual(url,endpoint);stats['source_requests']+=1;return json.dumps(payload).encode()
  with patch.object(m,'read_http',side_effect=transport),patch.object(m,'now',return_value=stamp):rows,errors,_=asyncio.run(m.collect(self.cache,self.run,self.stats,[self.source()]))
  self.assertEqual(errors,[]);self.assertEqual(rows[0]['context_text'],'un paid costs $1 ,000');self.assertEqual(rows[0]['observed_at'],STAMP);self.assertEqual(rows[0]['answer_text'],'unpaid costs $1,000');self.assertEqual(rows[0]['answer_observed_at'],stamp);self.assertEqual(json.loads(path.read_bytes())['text_parser_version'],source_context.TEXT_PARSER)
 def test_version_metadata_alone_is_not_semantic_novelty_or_model_text(self):
  original=dict(self.primary()[1],evidence_id='E1');changed=dict(original,text_parser_version=source_context.LEGACY_TEXT_PARSER,title_text_parser_version='legacy',answer_text_parser_version='legacy')
  self.assertEqual(model_packet.project([original]),model_packet.project([changed]));self.assertEqual(history.revision(m,original),history.revision(m,changed));self.assertEqual(source_context.source_packet(original)['text_parser_version'],source_context.TEXT_PARSER)
 def test_changed_normalized_text_is_new_revision_without_rewriting_old_evidence(self):
  old=dict(self.primary(True)[1],evidence_id='E1');selected,summary=self.commit([old]);identifier=self.prepare(selected);snapshot=self.root/summary['snapshot_file'];input_path=self.root/'analysis-inputs'/(identifier+'.json');before={p:p.read_bytes() for p in [snapshot,input_path]}
  new=dict(old,**source_context.context('<p>un<strong>paid</strong> costs $1<span>,000</span></p>','body','question_body'));new['observed_at']='2026-10-25T00:01:00+00:00';selected,next_summary=self.commit([new]);self.assertEqual(next_summary['updated_existing'],1);self.assertEqual(len(selected),1);self.assertNotEqual(history.revision(m,old),history.revision(m,new))
  rebuilt=history.load(m,self.root);self.assertEqual(rebuilt['records'][history.identity(m,new)]['revision_hash'],history.revision(m,new))
  for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
 def test_legacy_wordpress_checkpoint_reused_without_parser_or_transport(self):
  import wp_context_checkpoint,wordpress_identity
  url='https://wordpress.org/support/topic/synthetic/';folder=self.cache/'topic-context';folder.mkdir();path=folder/(m.sha((source_context.SCHEMA+'|wp'+str(wordpress_identity.CONTRACT)+'|'+url).encode())+'.json');value=source_context.context('un<strong>paid</strong>','original_post_html','original_post_only',parser_version=source_context.LEGACY_TEXT_PARSER);value.pop('text_parser_version');value.update(context_observed_at=STAMP,context_cache_expires=NOW+300,wordpress_parser_contract=wordpress_identity.CONTRACT);saved=dict(url=url,expires=NOW+300,context=value);m.dump(path,dict(saved,integrity_sha256=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode())));before=path.read_bytes();rows=[dict(url=url,title='SYNTHETIC topic')]
  with patch.object(source_context,'wordpress',side_effect=AssertionError('No legacy reparse')),patch.object(m,'read_http',side_effect=AssertionError('No recapture')):asyncio.run(wp_context_checkpoint.enrich(m,self.cache,self.run,self.stats,None,rows))
  self.assertEqual(rows[0]['context_text'],'un paid');self.assertEqual(rows[0]['context_observed_at'],STAMP);self.assertNotIn('text_parser_version',rows[0]);self.assertEqual(path.read_bytes(),before)

class BuyerNormalizationTests(unittest.TestCase):
 def setUp(self):
  import buyer_evidence
  self.b=buyer_evidence;self.tmp=tempfile.TemporaryDirectory(prefix='buyer-normalization-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.run=self.root/'run';self.run.mkdir();self.url='https://webapps.stackexchange.com/questions/900000001/synthetic';self.stamp='2026-10-28T00:00:00Z';self.cards=[{'observed_basis':[{'url':self.url}]}]
 def extract(self,body,**kw):return self.b.extract(body,self.url,self.stamp,'0'*64,**kw)
 def collect(self,body,url=None):
  url=url or self.url;host=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(url).hostname
  payload=({'id':900000001,'text':body,'created_at':self.stamp,'children':[]} if host=='news.ycombinator.com' else {'items':[{'question_id':900000001,'link':url,'body':body,'creation_date':123,'is_answered':False}]});raw=json.dumps(payload).encode();stats={'source_requests':0,'source_cache_hits':0};calls=[]
  def transport(request,stats,cap):calls.append(request);stats['source_requests']+=1;return raw
  with patch.object(m,'read_http',side_effect=transport):result=asyncio.run(self.b.collect(self.root,self.run,[{'observed_basis':[{'url':url}]}],stats))
  return result[url],raw,calls,stats
 def test_inline_money_quote_and_hash_exact(self):
  result=self.extract('<p>I pay $1<span>,000</span> per month for an existing service.</p>');self.assertEqual(result['monetary_source_text'],'I pay $1,000 per month for an existing service.');self.assertTrue(result['facts']);self.assertIn('$1,000',result['facts'][0]['quote']);self.assertEqual(result['monetary_source_field_sha256'],m.sha(result['monetary_source_text'].encode()));self.assertEqual(result['buyer_text_contract'],2);self.assertEqual(result['buyer_text_parser'],source_context.TEXT_PARSER);self.assertIsNotNone(self.b.monetary_context(result))
 def test_inline_negation_remains_negation(self):
  result=self.extract('<p>I do n<strong>ot</strong> pay $100 for this.</p>');self.assertIn('not pay',result['monetary_source_text']);self.assertFalse(any(f['kind']=='existing_expense_self_report' for f in result['facts']))
 def test_blocks_scripts_styles_and_entities(self):
  result=self.extract('<p>I pay $1<span>,000</span> &amp; taxes.</p><script>I pay $99999</script><style>I pay $88888</style><p>un<strong>paid</strong> work</p>');self.assertEqual(result['monetary_source_text'],'I pay $1,000 & taxes. unpaid work')
 def test_plain_normalized_text_not_reparsed(self):
  body='I pay $100 for <custom> records &amp; templates.';result=self.extract(body,is_html=False);self.assertEqual(result['monetary_source_text'],body);self.assertEqual(result['buyer_text_parser'],'plain-whitespace-v1')
 def test_limit_is_recorded_not_turned_into_full_capture(self):
  body='I pay $100. '+('word '*5000);full=source_context.text(body);result=self.extract(body);self.assertEqual(result['monetary_source_text'],full[:20000]);self.assertEqual(result['buyer_source_text_chars'],len(full));self.assertTrue(result['buyer_source_text_truncated']);self.assertLessEqual(sum(len(f['quote'].split()) for f in result['facts']),25)
 def test_real_stackexchange_collection_receipt_and_context(self):
  body='<p>I pay $1<span>,000</span> per month for an existing service.</p>';result,raw,calls,stats=self.collect(body);self.assertEqual(len(calls),1);self.assertNotIn('error',result);self.assertEqual(result['monetary_source_text'],result['original_context']['context_text']);self.assertEqual(result['response_sha256'],m.sha(raw));self.assertEqual((self.root/result['source_payload_file']).read_bytes(),raw);self.assertEqual(result['source_identity_status'],'verified_response_identity');self.assertEqual(stats['source_requests'],1);self.assertFalse(result['payer_verified']);self.assertFalse(result['customer_verified']);self.assertIsNone(result['payment_for_proposed_solution'])
 def test_real_hn_collection_uses_original_html(self):
  url='https://news.ycombinator.com/item?id=900000001';result,raw,calls,stats=self.collect('<p>We currently pay $1<span>,500</span> for exports.</p>',url);self.assertEqual(len(calls),1);self.assertEqual(result['monetary_source_text'],result['original_context']['context_text']);self.assertIn('$1,500',result['facts'][0]['quote']);self.assertEqual((self.root/result['source_payload_file']).read_bytes(),raw)
 def test_wordpress_collect_preserves_normalized_literal_angles(self):
  url='https://wordpress.org/support/topic/synthetic/';normalized='I pay $100 for <custom> records &amp; templates.';context=source_context.context(normalized,'original_post_html','original_post_only',is_html=False);context['answer_status']='unknown';raw=b'<html>SYNTHETIC only</html>';stats={'source_requests':0,'source_cache_hits':0};calls=[]
  def transport(request,stats,cap):calls.append(request);stats['source_requests']+=1;return b'User-agent: *\nAllow: /\n' if request.endswith('robots.txt') else raw
  # WordPress parsing requires unavailable bs4: mock only that parser/identity seam,
  # exercise real buyer collect, archive, normalization dispatch and report assembly.
  with patch.object(m,'read_http',side_effect=transport),patch.object(self.b,'check_wordpress_identity'),patch.object(source_context,'wordpress',return_value=context):result=asyncio.run(self.b.collect(self.root,self.run,[{'observed_basis':[{'url':url}]}],stats))[url]
  self.assertEqual(len(calls),2);self.assertEqual(result['monetary_source_text'],normalized);self.assertEqual(result['buyer_text_parser'],'plain-whitespace-v1');self.assertEqual((self.root/result['source_payload_file']).read_bytes(),raw)
 def test_wordpress_prebounded_context_keeps_original_truncation(self):
  url='https://wordpress.org/support/topic/synthetic-long/';full='I pay $100. '+('word '*3000);context=source_context.context(full,'original_post_html','original_post_only',is_html=False);context['answer_status']='unknown';stats={'source_requests':0,'source_cache_hits':0}
  def transport(request,stats,cap):stats['source_requests']+=1;return b'User-agent: *\nAllow: /\n' if request.endswith('robots.txt') else b'SYNTHETIC raw'
  with patch.object(m,'read_http',side_effect=transport),patch.object(self.b,'check_wordpress_identity'),patch.object(source_context,'wordpress',return_value=context):result=asyncio.run(self.b.collect(self.root,self.run,[{'observed_basis':[{'url':url}]}],stats))[url]
  self.assertTrue(result['buyer_source_text_truncated']);self.assertEqual(result['buyer_source_text_chars'],context['source_text_chars']);self.assertLessEqual(len(result['monetary_source_text']),12000);self.assertEqual(result['original_context']['source_text_sha256'],m.sha(' '.join(full.split()).encode()))
 def test_new_cache_replayed_without_reextract_or_transport(self):
  first,raw,calls,stats=self.collect('<p>I pay $1<span>,000</span> per month.</p>');before=inventory(self.root)
  with patch.object(m,'read_http',side_effect=AssertionError('No refetch')),patch.object(self.b,'extract',side_effect=AssertionError('No reparse')):replay=asyncio.run(self.b.collect(self.root,self.run,self.cards,{'source_requests':0,'source_cache_hits':0},offline=True))[self.url]
  self.assertEqual(replay,first);self.assertEqual(inventory(self.root),before)
 def test_legacy_cache_bytes_and_dates_unchanged(self):
  first,raw,calls,stats=self.collect('<p>I pay $1<span>,000</span> per month.</p>');path=self.root/'buyer-source-cache'/(m.sha(self.url.encode())+'.json');saved=json.loads(path.read_bytes());saved.pop('integrity_sha256');legacy='I pay $1 ,000 per month.'
  for key in ['buyer_text_contract','buyer_text_parser','buyer_source_text_chars','buyer_source_text_truncated']:saved.pop(key)
  saved['monetary_source_text']=legacy;saved['monetary_source_field_sha256']=m.sha(legacy.encode());saved['monetary_utterances']=__import__('monetary_utterances').extract(legacy,'webapps.stackexchange.com',None,'buyer_original_normalized_text',self.url,saved['observed_at'])['events']
  for fact in saved['facts']:fact['quote']=fact['quote'].replace('$1,000','$1 ,000')
  saved['integrity_sha256']=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode());m.dump(path,saved);before=inventory(self.root)
  with patch.object(m,'read_http',side_effect=AssertionError('No refresh')),patch.object(self.b,'extract',side_effect=AssertionError('No legacy reparse')):replay=asyncio.run(self.b.collect(self.root,self.run,self.cards,{'source_requests':0,'source_cache_hits':0},offline=True))[self.url]
  self.assertEqual(replay['monetary_source_text'],legacy);self.assertEqual(replay['observed_at'],saved['observed_at']);self.assertEqual(replay['facts'],saved['facts']);self.assertNotIn('buyer_text_contract',replay);self.assertEqual(inventory(self.root),before)
 def test_unknown_policy_quarantines_no_retry_no_rewrite(self):
  first,raw,calls,stats=self.collect('I pay $100.');path=self.root/'buyer-source-cache'/(m.sha(self.url.encode())+'.json');saved=json.loads(path.read_bytes());saved.pop('integrity_sha256');saved['buyer_text_contract']=999;saved['integrity_sha256']=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode());m.dump(path,saved);before=inventory(self.root)
  with patch.object(m,'read_http',side_effect=AssertionError('No refresh')):report=asyncio.run(self.b.collect(self.root,self.run,self.cards,{'source_requests':0,'source_cache_hits':0}))[self.url]
  self.assertEqual(report['source_identity_status'],'integrity_failure_no_refetch');self.assertFalse(report['network_retry_performed']);self.assertEqual(inventory(self.root),before)
 def test_collection_identity_mismatch_remains_quarantined(self):
  raw=json.dumps({'items':[{'question_id':2,'link':self.url,'body':'I pay $100.'}]}).encode();stats={'source_requests':0,'source_cache_hits':0};calls=[]
  def transport(request,stats,cap):calls.append(request);stats['source_requests']+=1;return raw
  with patch.object(m,'read_http',side_effect=transport):report=asyncio.run(self.b.collect(self.root,self.run,self.cards,stats))[self.url]
  self.assertEqual(len(calls),1);self.assertEqual(report['facts'],[]);self.assertEqual(report['source_identity_status'],'quarantined_unusable_response');self.assertEqual((self.root/report['received_payloads'][0]['payload_file']).read_bytes(),raw)
 def test_review_keeps_self_report_not_offer_payment(self):
  report=self.extract('<p>I pay $1<span>,000</span> per month.</p>');before=copy.deepcopy(report);result=self.b.review(self.cards[0],{self.url:report});self.assertIsNone(result['payment_evidence']);self.assertEqual(result['payer_status'],'unknown');self.assertEqual(result['raw_original_reports'][0],before);self.assertIn('$1,000',result['self_reported_signals'][0]['quote']);self.assertEqual(report,before)

def tearDownModule():
 if inventory(SOURCE)!=BEFORE:raise AssertionError('Source bytes changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

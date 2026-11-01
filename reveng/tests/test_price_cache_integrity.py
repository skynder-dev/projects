"""Synthetic price-cache regressions through real collection; no live/model access."""
from pathlib import Path
import argparse,asyncio,copy,hashlib,json,os,selectors,sys,tempfile,time,unittest
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
SOURCE=args.source.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE))
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
BEFORE=inventory(SOURCE)
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Price-cache regressions forbid transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper','aiohttp','crawl4ai'}:raise PermissionError('Price-cache regressions forbid models/live collectors')
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
import reveng_local_research as m,official_html,html_document_identity,commercial_review
NOW=1792972800;STAMP='2026-10-26T00:00:00+00:00'
class PriceCacheTests(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory(prefix='reveng-price-synthetic-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);self.cache=self.root/'cache';self.cache.mkdir();self.run=self.root/'run';self.run.mkdir();self.source=copy.deepcopy(m.PRICE_SOURCES[0]);self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0}
  for target,value in [('time.time',NOW),('reveng_local_research.now',STAMP)]:
   p=patch(target,return_value=value);p.start();self.addCleanup(p.stop)
  self.text='SYNTHETIC standard plan $8/mo. Not a captured offer.'
 def path(self,source=None):return self.cache/(m.sha(('price-v2-html1'+(source or self.source)['url']).encode())+'.price.json')
 def raw(self,source=None):return ('<html><head><link rel="canonical" href="'+(source or self.source)['url']+'"><title>SYNTHETIC price fixture</title></head><body>'+self.text+'</body></html>').encode()
 def metadata(self):return dict(official_HTML_contract=official_html.CONTRACT,HTML_identity_contract=html_document_identity.CONTRACT,source_role='official_pricing_document_not_question_or_reply',source_text_sha256=m.sha(self.text.encode()),source_text_chars=len(self.text),source_text_truncated=False)
 def saved(self,source=None,expiry=NOW+300):
  source=source or self.source;raw=self.raw(source);receipt=official_html.save(self.cache,raw,source['url'],STAMP);rows=m.parse_prices(self.text,source,STAMP,m.sha(raw),text_scope='SYNTHETIC supplied text only')
  for row in rows:row.update(self.metadata(),HTML_receipt=receipt)
  return dict(self.metadata(),HTML_receipt=receipt,records=rows,expires=expiry,sha256=m.sha(json.dumps(rows,sort_keys=True).encode()))
 def negative(self,expiry=NOW+300):return {'error':{'source':self.source['provider'],'url':self.source['url'],'reason':'SYNTHETIC source unavailable','retry':False,'received_HTML_receipt':None},'expires':expiry}
 def collect(self,sources=None,allow_transport=False,offline=False):
  def transport(url,stats,*args):
   stats['source_requests']+=1
   return b'User-agent: *\nAllow: /\n' if url.endswith('/robots.txt') else self.raw()
  # Success-path HTML extraction is an explicit boundary mock, not a substitute
  # parser. Actual identity/receipt validation, literal-price parsing and writes run.
  with patch.object(m,'PRICE_SOURCES',sources or [self.source]),patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'1' if offline else '0'}),patch.object(m,'read_http',side_effect=transport if allow_transport else AssertionError('No HTTP')) as intercepted,patch.object(official_html,'extract',return_value=(self.text,self.metadata())):
   result=asyncio.run(m.collect_prices(self.cache,self.run,self.stats))
  if not allow_transport:intercepted.assert_not_called()
  return result,intercepted.call_count
 def assert_corrupt(self,raw):
  path=self.path();path.write_bytes(raw);(records,errors),calls=self.collect(allow_transport=True);self.assertEqual(calls,0,'Damaged pricing evidence must not be refetched');self.assertEqual(path.read_bytes(),raw,'Damaged evidence must not be replaced by negative cache');self.assertEqual(records,[]);self.assertEqual(len(errors),1);error=errors[0];self.assertEqual(error['source'],self.source['provider']);self.assertIn('Cached pricing source unavailable',error['reason']);self.assertTrue(error['cache_bytes_preserved']);self.assertFalse(error['network_retry_performed']);self.assertFalse(error['retry']);self.assertEqual(self.stats['price_cache_errors'],1)
  card=dict(title='SYNTHETIC price test',buyer='Unknown proposed buyer',problem_hypothesis='SYNTHETIC unverified proposal',validation_step='SYNTHETIC verify price later',observed_basis=[],market_category=self.source['category']);review=commercial_review.assess(card,records,errors);self.assertIsNone(review['income_score']);self.assertIsNone(review['estimated_revenue']);self.assertIsNone(review['buyer']['payment_evidence']);self.assertTrue(any('incomplete' in issue.lower() for issue in review['unknowns']));self.assertTrue(any('unknown' in issue.lower() for issue in review['unknowns']))
 def test_malformed_saved_price_evidence_is_not_replaced_by_negative_cache(self):self.assert_corrupt(b'{SYNTHETIC damaged pricing evidence')
 def test_checksum_invalid_fresh_and_expired_prices_are_not_refreshes(self):
  for expiry in [NOW+300,NOW-1]:
   with self.subTest(expiry=expiry):
    self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};self.assert_corrupt(json.dumps(dict(self.saved(expiry=expiry),sha256='0'*64)).encode())
 def test_malformed_shapes_identity_and_expiry_remain_preserved(self):
  saved=self.saved();bad_error=self.negative();bad_error['error']['url']='https://example.invalid/wrong'
  cases=[b'\xff',b'[]',b'null',json.dumps(dict(saved,expires='future')).encode(),json.dumps(dict(saved,expires=True)).encode(),json.dumps(dict(saved,expires=float('nan'))).encode(),json.dumps(dict(saved,records={})).encode(),json.dumps(dict(self.negative(),error='broken')).encode(),json.dumps(bad_error).encode(),('{"expires":0,'+json.dumps(saved)[1:]).encode()]
  for raw in cases:
   with self.subTest(raw=raw[:80]):
    self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};self.assert_corrupt(raw)
 def test_missing_consumed_price_identity_is_local_not_downstream_failure(self):
  for field in ['provider','category']:
   with self.subTest(field=field):
    saved=self.saved();saved['records'][0].pop(field);saved['sha256']=m.sha(json.dumps(saved['records'],sort_keys=True).encode());self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};self.assert_corrupt(json.dumps(saved).encode())
 def test_damaged_raw_receipt_is_preserved_even_when_price_cache_expired(self):
  saved=self.saved(expiry=NOW-1);raw_path=self.cache/saved['HTML_receipt']['payload_file'];damaged=b'SYNTHETIC damaged raw receipt';raw_path.write_bytes(damaged);self.assert_corrupt(json.dumps(saved).encode());self.assertEqual(raw_path.read_bytes(),damaged)
 def test_unreadable_cache_does_not_rewrite_or_drop_other_price_sources(self):
  bad=self.path();m.dump(bad,self.saved());other=copy.deepcopy(m.PRICE_SOURCES[1]);m.dump(self.path(other),self.saved(other));before=bad.read_bytes();read=Path.read_text
  def denied(path,*args,**kwargs):
   if path==bad:raise PermissionError('SYNTHETIC denied read')
   return read(path,*args,**kwargs)
  with patch.object(Path,'read_text',denied):(records,errors),calls=self.collect([self.source,other])
  self.assertEqual(calls,0);self.assertEqual(bad.read_bytes(),before);self.assertTrue(records);self.assertEqual({r['provider'] for r in records},{other['provider']});self.assertEqual(len(errors),1);self.assertTrue(errors[0]['cache_bytes_preserved'])
 def test_positive_receipt_is_read_once_before_policy_reuse(self):
  saved=self.saved();m.dump(self.path(),saved);raw_path=self.cache/saved['HTML_receipt']['payload_file'];read=Path.read_bytes;calls=[]
  def once(path,*args,**kwargs):
   if path==raw_path:
    calls.append(path)
    if len(calls)>1:raise PermissionError('SYNTHETIC second read unavailable')
   return read(path,*args,**kwargs)
  with patch.object(Path,'read_bytes',once):(records,errors),transport=self.collect()
  self.assertEqual(len(calls),1);self.assertEqual(transport,0);self.assertEqual(records,saved['records']);self.assertEqual(errors,[])
 def test_negative_receipt_corruption_is_not_refreshed_or_replaced(self):
  receipt=official_html.save(self.cache,b'SYNTHETIC access denied page, not valid source HTML',self.source['url'],STAMP);path=self.cache/receipt['payload_file'];path.write_bytes(b'SYNTHETIC damaged negative raw evidence')
  for expiry in [NOW+300,NOW-1]:
   with self.subTest(expiry=expiry):
    saved=self.negative(expiry);saved['error']['received_HTML_receipt']=receipt;self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};self.assert_corrupt(json.dumps(saved).encode());self.assertEqual(path.read_bytes(),b'SYNTHETIC damaged negative raw evidence')
 def test_intact_negative_denied_document_is_a_valid_error_not_a_source_claim(self):
  saved=self.negative();saved['error']['received_HTML_receipt']=official_html.save(self.cache,b'SYNTHETIC access denied page without canonical identity',self.source['url'],STAMP);m.dump(self.path(),saved);before=inventory(self.cache);(records,errors),calls=self.collect();self.assertEqual(records,[]);self.assertEqual(errors,[saved['error']]);self.assertEqual(calls,0);self.assertEqual(inventory(self.cache),before)
 def test_valid_fresh_positive_cache_reuses_exact_records_and_bytes(self):
  saved=self.saved();m.dump(self.path(),saved);before=inventory(self.cache);(records,errors),calls=self.collect();self.assertEqual(records,saved['records']);self.assertEqual(errors,[]);self.assertEqual(calls,0);self.assertEqual(self.stats['source_cache_hits'],1);self.assertEqual(inventory(self.cache),before)
 def test_valid_fresh_negative_cache_reuses_error_without_transport_or_rewrite(self):
  saved=self.negative();m.dump(self.path(),saved);before=inventory(self.cache);(records,errors),calls=self.collect();self.assertEqual(records,[]);self.assertEqual(errors,[saved['error']]);self.assertEqual(calls,0);self.assertEqual(self.stats['source_cache_hits'],1);self.assertEqual(inventory(self.cache),before)
 def test_valid_expired_positive_negative_and_absent_entries_refresh(self):
  for saved in [self.saved(expiry=NOW-1),self.negative(expiry=NOW-1),None]:
   with self.subTest(cache='absent' if saved is None else 'negative' if 'error' in saved else 'positive'):
    if saved is not None:m.dump(self.path(),saved)
    elif self.path().exists():self.path().unlink()
    self.stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};(records,errors),calls=self.collect(allow_transport=True);self.assertTrue(records);self.assertEqual(errors,[]);self.assertEqual(calls,2);self.assertEqual(self.stats.get('price_cache_errors',0),0);self.assertTrue(official_html.valid_cached(self.cache,json.loads(self.path().read_bytes()),self.source['url']))
 def test_intact_older_parser_contract_refreshes_instead_of_claiming_corruption(self):
  saved=self.saved();saved['HTML_identity_contract']=html_document_identity.CONTRACT-1;m.dump(self.path(),saved);(records,errors),calls=self.collect(allow_transport=True);self.assertTrue(records);self.assertEqual(errors,[]);self.assertEqual(calls,2);self.assertEqual(self.stats.get('price_cache_errors',0),0)
 def test_valid_expired_offline_cache_is_not_replaced(self):
  saved=self.saved(expiry=NOW-1);m.dump(self.path(),saved);before=self.path().read_bytes();(records,errors),calls=self.collect(offline=True);self.assertEqual(records,[]);self.assertEqual(calls,0);self.assertIn('No fresh price cache',errors[0]['reason']);self.assertEqual(self.path().read_bytes(),before);self.assertEqual(self.stats.get('price_cache_errors',0),0)
 def test_new_transport_failure_still_has_normal_negative_cache_behavior(self):
  with patch.object(m,'PRICE_SOURCES',[self.source]),patch.dict(os.environ,{'REVENG_OFFLINE_REPLAY':'0'}),patch.object(m,'read_http',side_effect=ValueError('SYNTHETIC HTTP failure')):
   records,errors=asyncio.run(m.collect_prices(self.cache,self.run,self.stats))
  self.assertEqual(records,[]);saved=json.loads(self.path().read_bytes());self.assertEqual(saved['error'],errors[0]);self.assertEqual(saved['expires'],NOW+900)
 def test_cancellation_during_fetch_propagates_without_checkpoint(self):
  with patch.object(m,'PRICE_SOURCES',[self.source]),patch.object(m,'read_http',side_effect=asyncio.CancelledError()),self.assertRaises(asyncio.CancelledError):asyncio.run(m.collect_prices(self.cache,self.run,self.stats))
  self.assertFalse(self.path().exists())
def tearDownModule():
 if inventory(SOURCE)!=BEFORE:raise AssertionError('Source bytes changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

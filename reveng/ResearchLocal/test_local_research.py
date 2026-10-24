import asyncio, copy, importlib.util, json, pathlib, tempfile, time, unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('local',pathlib.Path(__file__).with_name('reveng_local_research.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OBS=[{'evidence_id':'E1','title':'Fixture observed title','url':'https://example.org/fixture','source':'fixture','kind':'public_question_title','excerpt':'Fixture excerpt'}]
def cards():
 c={k:'Fixture hypothesis text, unverified.' for k in ['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','alternatives_and_limits']}
 c.update(market_category='other',evidence_ids=['E1'],risks=['Fixture risk is not verified','Another unverified risk'],missing_evidence=['Buyer willingness is unknown','Actual demand is still unknown'],observations_used=[{'evidence_id':'E1','source_field':'title','quote':'Fixture observed title','support':'source_quote'}])
 return {'hypotheses':[copy.deepcopy(c) for _ in range(3)]}
class Tests(unittest.TestCase):
 def test_failed_price_is_cached_without_retry(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);run=root/'runs'/'price';run.mkdir(parents=True);cache=root/'cache';cache.mkdir();stats={'source_requests':0,'source_cache_hits':0,'model_requests':0}
   source={'provider':'Fixture','category':'other','url':'https://example.org/pricing'}
   with patch.object(m,'PRICE_SOURCES',[source]),patch.object(m,'read_http',side_effect=ValueError('HTTP 429')) as http:
    asyncio.run(m.collect_prices(cache,run,stats));asyncio.run(m.collect_prices(cache,run,stats));self.assertEqual(http.call_count,1);self.assertEqual(stats['source_cache_hits'],1)
 def test_fragmented_response_and_byte_cap(self):
  class Stream:
   def __init__(self,chunks):self.chunks=list(chunks)
   async def read(self,n):return self.chunks.pop(0) if self.chunks else b''
  self.assertEqual(asyncio.run(m.read_bounded(Stream([b'{"a":',b'1}']),30)),b'{"a":1}')
  with self.assertRaises(ValueError):asyncio.run(m.read_bounded(Stream([b'123',b'456']),5))
 def test_real_attribution_only(self):
  result=m.validate_cards(cards(),OBS);self.assertEqual(result[0]['observed_basis'],OBS);self.assertIsNone(result[0]['market_score']);self.assertIsNone(result[0]['sales']);self.assertIsNone(result[0]['profit'])
 def test_invented_ref(self):
  value=cards();value['hypotheses'][0]['evidence_ids']=['E999']
  with self.assertRaises(ValueError):m.validate_cards(value,OBS)
 def test_no_citation(self):
  value=cards();value['hypotheses'][0]['evidence_ids']=[]
  with self.assertRaises(ValueError):m.validate_cards(value,OBS)
 def test_fake_finance_and_links(self):
  for bad in ['Guaranteed sales $999','A fact from https://invented.example','Proven demand for this fixture']:
   value=cards();value['hypotheses'][0]['problem_hypothesis']=bad
   with self.assertRaises(ValueError):m.validate_cards(value,OBS)
 def test_incomplete(self):
  value=cards();del value['hypotheses'][0]['risks']
  with self.assertRaises(ValueError):m.validate_cards(value,OBS)
 def test_schema_enum(self):
  s=m.schema(['E1','E2']);self.assertEqual(s['properties']['hypotheses']['items']['properties']['evidence_ids']['items']['enum'],['E1','E2'])
 def test_direct_ai_gate_precedes_empty_or_failed_source_dispatch(self):
  for raises in [False,True]:
   with tempfile.TemporaryDirectory() as t:
    root=pathlib.Path(t);run=root/'runs'/'empty';run.mkdir(parents=True)
    def fake(*args):
     if raises:raise ValueError('HTTP 429; no retry')
     return b'{"items":[]}'
    with patch.object(m,'read_http',side_effect=fake)as http,patch.object(m,'ask_qwen',side_effect=AssertionError('No model allowed'))as model:
     with self.assertRaisesRegex(ValueError,'Direct AI execution is disabled'):asyncio.run(m.pipeline(root,run))
     http.assert_not_called();model.assert_not_called()
    self.assertFalse((run/'result.json').exists());self.assertFalse((root/'candidates.json').exists())
 def test_pre_cancel_no_requests(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);run=root/'runs'/'cancel';run.mkdir(parents=True);(run/'cancel.request').write_text('cancel')
   with patch.object(m,'read_http',side_effect=AssertionError('No HTTP allowed')):asyncio.run(m.execute(root,run,False))
   self.assertEqual(json.loads((run/'result.json').read_text())['status'],'cancelled')
 def test_result_cache_integrity_and_zero_dispatch(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);run=root/'runs'/'cached';run.mkdir(parents=True)
   obj={'version':m.VERSION,'status':'completed','cache_expires':time.time()+60,'hypotheses':m.validate_cards(cards(),OBS),'observations':OBS}
   obj['cache_payload_sha256']=m.sha(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode());m.dump(root/'latest-result.json',obj)
   with patch.object(m,'collect',side_effect=AssertionError('No source dispatch')),patch.object(m,'ask_qwen',side_effect=AssertionError('No model dispatch')):asyncio.run(m.pipeline(root,run))
   result=json.loads((run/'result.json').read_text());self.assertTrue(result['result_cache_hit']);self.assertEqual(result['source_requests'],0);self.assertEqual(result['model_requests'],0)
   obj['hypotheses'][0]['evidence_ids']=['E999'];m.dump(root/'latest-result.json',obj)
   with self.assertRaises(ValueError):asyncio.run(m.pipeline(root,run))
if __name__=='__main__':unittest.main(verbosity=2)

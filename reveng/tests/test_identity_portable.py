import sys,json,copy,unittest,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
if len(sys.argv)!=2:raise SystemExit('Usage: test_identity_portable.py <canonical-source-copy>')
runtime=Path(sys.argv.pop(1)).resolve()
if not runtime.is_dir():raise SystemExit('Explicit source directory is missing')
def inventory():
 return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.iterdir() if p.suffix in {'.py','.cs'}}
BEFORE=inventory()
def offline_boundary(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise AssertionError('Identity tests forbid network/process execution')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise AssertionError('Identity tests forbid model imports')
sys.addaudithook(offline_boundary)
def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Canonical source bytes changed during identity tests')
sys.path.insert(0,str(runtime))
import commercial_review as c
base={'url':'https://softwarerecs.stackexchange.com/questions/95686/synthetic-title','evidence_id':'E29','source':'softwarerecs','kind':'public_question_context','title':'SYNTHETIC recurring export question','excerpt':'SYNTHETIC recurring export question','author_id':None,'observed_at':'2026-10-15T00:00:00+00:00'}
class IdentityTests(unittest.TestCase):
 def assess(self,urls):
  rows=[dict(copy.deepcopy(base),url=u,evidence_id='E'+str(i+1)) for i,u in enumerate(urls)]
  original=copy.deepcopy(rows)
  result=c.assess({'title':'SYNTHETIC identity regression','buyer':'Unknown; not a customer','validation_step':'No action','observed_basis':rows},[])
  self.assertEqual(rows,original);self.assertEqual(result['corroboration']['independence'],'not_established');self.assertIsNone(result['income_score'])
  self.assertEqual([x['url'] for x in result['observed_problem']],urls)
  return result
 def test_historical_exact_source_slug_aliases(self):
  urls=[base['url'],'https://softwarerecs.stackexchange.com/questions/95686/older-title']
  r=self.assess(urls);self.assertEqual(r['corroboration']['distinct_posts'],1);self.assertFalse(r['corroboration']['lexical_repetition'])
 def test_known_question_aliases(self):
  origin=base['url']
  for alias in [origin+'/',origin+'?utm_source=SYNTHETIC',origin+'#top',origin.replace('softwarerecs.stackexchange.com','SOFTWARERECS.STACKEXCHANGE.COM'),origin.replace('synthetic-title','SYNTHETIC-TITLE')]:
   with self.subTest(alias=alias):
    self.assertNotEqual(origin,alias,'Alias must be a distinct URL, not a no-op substitution')
    result=self.assess([origin,alias]);self.assertEqual(result['corroboration']['distinct_posts'],1);self.assertFalse(result['corroboration']['lexical_repetition'])
 def test_non_equivalence_boundaries(self):
  for alias in [base['url'].replace('/95686/','/95687/'),base['url'].replace('softwarerecs.','webapps.'),base['url']+'/12345',base['url']+'#12345',base['url']+'?answer=12345',base['url'].replace('/questions/95686/','/q/95686/'),base['url'].replace('https:','http:'),'https://unknown.example.test/questions/95686/old','https://www.softwarerecs.stackexchange.com/questions/95686/old']:
   with self.subTest(alias=alias):
    result=self.assess([base['url'],alias])
    # The unchanged synthetic row still says source=softwarerecs when only
    # its URL is switched to webapps. Under row-aware validation this row is
    # unresolved, not a second known report; it must remain retained.
    if alias.startswith('https://webapps.stackexchange.com/'):
     self.assertEqual(result['corroboration']['distinct_posts'],1);self.assertTrue(any('unresolved' in x for x in result['unknowns']))
    else:self.assertEqual(result['corroboration']['distinct_posts'],2)
 def test_unknown_question_like_urls_remain_distinct(self):
  self.assertEqual(self.assess(['https://fixture.example.test/questions/10/a','https://fixture.example.test/questions/10/b'])['corroboration']['distinct_posts'],2)
 def test_separate_answer_fragments(self):
  self.assertEqual(self.assess([base['url']+'#12345',base['url']+'#67890'])['corroboration']['distinct_posts'],2)
 def test_numeric_answer_like_path_not_guessed_as_slug(self):
  self.assertNotEqual(c.report_identity(base['url']),c.report_identity('https://softwarerecs.stackexchange.com/questions/95686/12345'))
 def test_same_identity_retains_changed_capture_and_body(self):
  rows=[copy.deepcopy(base),dict(copy.deepcopy(base),url='https://softwarerecs.stackexchange.com/questions/95686/older-title',evidence_id='SYNTHETIC-ALIAS',context_text='SYNTHETIC different saved content',observed_at='2026-10-14T00:00:00+00:00')]
  before=copy.deepcopy(rows);unique,notes=c.deduplicate(rows)
  self.assertEqual(unique,rows);self.assertEqual(rows,before);self.assertTrue(notes)
 def test_http_and_redirect_aliases_not_inferred(self):
  self.assertNotEqual(c.report_identity(base['url']),c.report_identity(base['url'].replace('https:','http:')))
  self.assertNotEqual(c.report_identity(base['url']),c.report_identity('https://softwarerecs.stackexchange.com/q/95686'))
 def test_missing_urls_unresolved_not_one_invented_report(self):
  r=self.assess(['','']);self.assertEqual(r['corroboration']['distinct_posts'],0);self.assertFalse(r['corroboration']['lexical_repetition']);self.assertTrue(any('unresolved' in x for x in r['unknowns']))
if __name__=='__main__':unittest.main(verbosity=2)

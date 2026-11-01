"""Actual saved-preference/compare/preview/archive checks; no native GUI qualification."""
from pathlib import Path
import argparse,csv,hashlib,io,json,os,sys,tempfile,unittest,zipfile
from unittest.mock import patch
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
SOURCE=a.source.resolve();sys.path.insert(0,str(SOURCE));sys.dont_write_bytecode=True
H=lambda b:hashlib.sha256(b).hexdigest()
def inventory():return {p.name:H(p.read_bytes()) for p in SOURCE.iterdir() if p.is_file()}
BEFORE=inventory()
def offline(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Offline owner-preference test forbids transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise PermissionError('No model imports')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).resolve();flags=args[2] or 0
  if SOURCE in path.parents and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Application source writes forbidden')
sys.addaudithook(offline)
import reveng_local_research as m,comparison_data as comparison,source_ledger as ledger,decision_recovery as recovery,research_export,archive_preview,social_idea_preview,research_reviews,commercial_review

class OwnerPreferenceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='reveng-owner-preference-unit-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  obs=[{'evidence_id':'SYN1','title':'SYNTHETIC saved question','url':'https://fixture.example.test/one','source':'synthetic','kind':'public_question_title','excerpt':'SYNTHETIC unit input only'}]
  card={k:'SYNTHETIC unverified proposal.' for k in ['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','alternatives_and_limits']}
  card.update(market_category='other',evidence_ids=['SYN1'],risks=[],missing_evidence=['No market validation'],observations_used=[{'evidence_id':'SYN1','source_field':'title','quote':obs[0]['title'],'support':'source_quote'}])
  self.card=m.validate_cards({'hypotheses':[card]},obs)[0];self.card.update(candidate_id='synthetic-owner-preference',review_revision_hash='f'*64);self.key='legacy_hypothesis:'+self.card['candidate_id']
  self.write('candidates.json',[self.card])
  for name,value in [('research-output-cards.json',{'cards':[]}),('analysis-queue.json',{'jobs':{}})]:self.write(name,dict(value,integrity_sha256=H(json.dumps(value,sort_keys=True,ensure_ascii=False).encode())))
  ledger.write(self.root/'source-ledger-catalog.json',ledger.seal(ledger.build(self.root)))
  self.before=comparison.build(self.root);self.original=(self.root/'candidates.json').read_bytes()
 def write(self,name,value):
  (self.root/name).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False),encoding='utf-8')
 def note(self,choice='keep',revision=None,**extra):
  entry={'decision':choice,'revision_hash':revision or self.card['review_revision_hash'],'decided_at':'2026-10-26T00:00:00Z','meaning':'owner preference only; not customer/payment evidence',**extra}
  self.write('review-notes.json',{self.card['candidate_id']:entry});return entry
 def overlay(self):return comparison.build(self.root)['owner_preferences']
 def pref(self):return self.overlay()['by_candidate'][self.key]
 def test_current_keep_and_separate_preview(self):
  entry=self.note(note='SYNTHETIC owner note retained');data=comparison.build(self.root);overlay=data['owner_preferences'];pref=overlay['by_candidate'][self.key]
  self.assertEqual(pref['binding'],'CURRENT_EXACT_REVISION');self.assertEqual(pref['current_choice'],'keep');self.assertEqual(pref['saved_entry'],entry)
  self.assertEqual(overlay['inputs']['review-notes.json']['sha256'],H((self.root/'review-notes.json').read_bytes()));self.assertNotIn('review-notes.json',data['inputs'])
  preview=social_idea_preview.preview(data,self.key,ledger.catalog(self.root));self.assertEqual(preview['saved_owner_preference']['current_choice'],'keep')
  self.assertEqual(preview['owner_decision'],'NO_EXPLICIT_REVISION_BOUND_DECISION');self.assertFalse(preview['ready_for_social']);self.assertFalse(preview['publication_authorized'])
 def test_current_reject(self):
  self.note('reject');self.assertEqual(self.pref()['current_choice'],'reject');self.assertEqual(self.pref()['binding'],'CURRENT_EXACT_REVISION')
 def test_stale_preference_retained_not_applied(self):
  entry=self.note(revision='e'*64,note='Earlier saved choice');pref=self.pref();self.assertEqual(pref['binding'],'HISTORICAL_OR_UNBOUND');self.assertIsNone(pref['current_choice']);self.assertEqual(pref['saved_entry'],entry)
 def test_changed_candidate_revision_never_carries_old_keep_forward(self):
  self.card['review_revision_hash']=commercial_review.revision(self.card);self.write('candidates.json',[self.card]);ledger.write(self.root/'source-ledger-catalog.json',ledger.seal(ledger.build(self.root)))
  entry=self.note();before=(self.root/'review-notes.json').read_bytes();self.assertEqual(self.pref()['current_choice'],'keep')
  self.card['solution_hypothesis']='SYNTHETIC changed proposed solution, not verified';self.card['review_revision_hash']=commercial_review.revision(self.card);self.write('candidates.json',[self.card]);ledger.write(self.root/'source-ledger-catalog.json',ledger.seal(ledger.build(self.root)))
  self.assertEqual(self.pref()['binding'],'HISTORICAL_OR_UNBOUND');self.assertIsNone(self.pref()['current_choice']);self.assertEqual(self.pref()['saved_entry'],entry);self.assertEqual((self.root/'review-notes.json').read_bytes(),before)
 def test_consistent_note_copy_change_preserves_candidate_and_existing_evidence_review(self):
  self.protect(self.note(note='First note'));data=comparison.build(self.root);rev=data['research_chain']['review_revisions'][self.key]
  record={'schema':'reveng-research-review-entry-v1','candidate_key':self.key,'revision_sha256':rev['revision_sha256'],'snapshot':rev['snapshot'],'condition_reviews':[{'source_id':f['id'],'field_id':f['metadata'].get('source_field','text'),'status':'UNKNOWN','unclosed_conditions':['SYNTHETIC open condition'],'rationale':'SYNTHETIC incomplete review'} for f in rev['snapshot']['source_fields']],'open_questions':['SYNTHETIC unresolved question'],'decision':{'choice':'DEFERRED','rationale':'SYNTHETIC declared review only','basis_claim_ids':[]},'declarant':'DECLARED_OWNER_REVIEW_IDENTITY_NOT_AUTHENTICATED','automatic_admission':False,'execution_authorized':False,'semantic_PASS':False}
  research_reviews.append(self.root,record,None);first=comparison.build(self.root)
  prior=H((self.root/'review-notes.json').read_bytes());self.protect(self.note(note='Edited note only'),prior);second=comparison.build(self.root)
  self.assertNotEqual(first['owner_preferences']['snapshot_sha256'],second['owner_preferences']['snapshot_sha256'])
  self.assertEqual(first['rows'],second['rows']);self.assertEqual(first['inputs'],second['inputs']);self.assertEqual(first['research_chain'],second['research_chain'])
  self.assertEqual(second['research_chain']['candidate_links'][self.key]['revision_review']['decision'],'DEFERRED')
  self.assertEqual(second['owner_preferences']['by_candidate'][self.key]['current_choice'],'keep');self.assertEqual((self.root/'candidates.json').read_bytes(),self.original)
 def test_missing_notes_is_explicit_and_old_preview_remains_compatible(self):
  self.assertEqual(self.overlay()['status'],'ABSENT');self.assertEqual(self.pref()['binding'],'NO_SAVED_OWNER_DECISION')
  self.assertTrue(all(pin['state']=='absent' for pin in self.overlay()['inputs'].values()))
  self.assertNotIn('saved_owner_preference',social_idea_preview.preview(self.before,self.key,ledger.catalog(self.root)))
 def test_corrupt_primary_remains_readable_as_unavailable_not_no_decision(self):
  raw=b'{BROKEN SYNTHETIC';(self.root/'review-notes.json').write_bytes(raw);data=comparison.build(self.root)
  self.assertTrue(data['rows']);self.assertEqual(data['owner_preferences']['status'],'UNAVAILABLE');self.assertEqual(self.pref()['binding'],'UNAVAILABLE_NOT_CURRENT');self.assertIsNone(self.pref()['current_choice']);self.assertEqual((self.root/'review-notes.json').read_bytes(),raw)
 def test_deep_corrupt_primary_localized_without_losing_healthy_comparison(self):
  raw=b'{"nested":'+b'['*10000+b'0'+b']'*10000+b'}';(self.root/'review-notes.json').write_bytes(raw);data=comparison.build(self.root)
  self.assertTrue(data['rows']);self.assertEqual(data['owner_preferences']['status'],'UNAVAILABLE');self.assertIn('RecursionError',str(data['owner_preferences']['issues']));self.assertIsNone(data['owner_preferences']['by_candidate'][self.key]['current_choice']);self.assertEqual((self.root/'review-notes.json').read_bytes(),raw)
 def test_missing_primary_with_previous_copy_not_restored(self):
  entry=self.note();(self.root/'review-notes.json').rename(self.root/'review-notes.prev');self.assertEqual(self.overlay()['status'],'RECOVERY_CONFLICT');self.assertIsNone(self.pref()['current_choice']);self.assertFalse((self.root/'review-notes.json').exists());self.assertEqual(json.loads((self.root/'review-notes.prev').read_bytes())[self.card['candidate_id']],entry)
 def protect(self,entry,expected_primary=None):
  payload={'schema':'reveng-decision-recovery-v1','status':'RECOVERY_COPY_NOT_CURRENT_AUTHORITY','expected_primary_sha256':expected_primary,'decisions':{self.card['candidate_id']:entry}}
  self.write(recovery.NAME,ledger.seal(payload))
 def test_recovery_conflict_keeps_primary_entry_but_never_current(self):
  entry=self.note();self.protect(dict(entry,decision='reject'));pref=self.pref();self.assertEqual(self.overlay()['status'],'RECOVERY_CONFLICT');self.assertEqual(pref['saved_entry'],entry);self.assertIsNone(pref['current_choice']);self.assertEqual(pref['saved_revision_binding'],'CURRENT_EXACT_REVISION')
 def test_matching_protected_copy_does_not_hide_preference(self):
  entry=self.note();self.protect(entry);self.assertEqual(self.overlay()['status'],'READABLE');self.assertEqual(self.pref()['current_choice'],'keep')
 def test_primary_only_note_edit_with_protected_copy_is_not_current(self):
  self.protect(self.note(note='Protected note'));protected=(self.root/recovery.NAME).read_bytes();entry=self.note(note='Primary-only edited note');pref=self.pref()
  self.assertEqual(self.overlay()['status'],'RECOVERY_CONFLICT');self.assertIsNone(pref['current_choice']);self.assertEqual(pref['saved_entry'],entry);self.assertEqual((self.root/recovery.NAME).read_bytes(),protected)
 def test_preference_change_during_capture_rejected(self):
  self.note();original=recovery._capture_preference_file;count=0
  def capture(root,name):
   nonlocal count
   value=original(root,name)
   if name=='review-notes.json':
    count+=1
    if count==1:self.note('reject')
   return value
  with patch.object(recovery,'_capture_preference_file',side_effect=capture):
   with self.assertRaisesRegex(ValueError,'preferences changed'):comparison.build(self.root)
 def test_discussion_export_rejects_changed_displayed_preference_not_evidence(self):
  self.note();shown=comparison.build(self.root);pin=shown['owner_preferences']['snapshot_sha256'];revision=shown['research_chain']['review_revisions'][self.key]['revision_sha256'];self.note('reject')
  self.assertEqual(comparison.build(self.root)['research_chain']['review_revisions'][self.key]['revision_sha256'],revision)
  output=self.root/'exports/stale-view.json'
  with self.assertRaisesRegex(ValueError,'owner preference snapshot is stale'):social_idea_preview.export_local(self.root,self.key,output,revision,pin)
  self.assertFalse(output.exists())
 def test_verified_archive_preserves_exact_notes_and_historical_overlay(self):
  self.note(note='SYNTHETIC archive note');raw=(self.root/'review-notes.json').read_bytes();path=self.root/'exports/owner.zip';research_export.export(self.root,path)
  with zipfile.ZipFile(path) as z:self.assertEqual(z.read('review-notes.json'),raw)
  receipt=archive_preview.preview(self.root,path);restored=Path(receipt['preview_root']);self.assertEqual((restored/'review-notes.json').read_bytes(),raw)
  data=comparison.build(restored);self.assertEqual(data['owner_preferences']['workspace_scope'],'HISTORICAL_READ_ONLY_ARCHIVE');self.assertEqual(data['owner_preferences']['by_candidate'][self.key]['saved_entry']['decision'],'keep');self.assertEqual((self.root/'review-notes.json').read_bytes(),raw)
  preview=social_idea_preview.preview(data,self.key,ledger.catalog(restored));self.assertEqual(preview['saved_owner_preference']['workspace_scope'],'HISTORICAL_READ_ONLY_ARCHIVE');self.assertFalse(preview['publication_authorized'])
 def test_actual_native_compare_consumes_separate_overlay(self):
  text=(SOURCE/'EvidenceComparison.cs').read_text(encoding='utf-8')
  self.assertIn('ValidatePreferenceOverlay(preferenceOverlay);',text);self.assertIn('OwnerPreferenceDescription(D(V(row.Data,"owner_preference")))',text)
  self.assertIn('V(D(V(preferenceOverlay,"by_candidate")),key)',text)
 def test_native_full_verification_cannot_be_bypassed_by_missing_stored_chain(self):
  text=(SOURCE/'EvidenceComparison.cs').read_text(encoding='utf-8');reload=text.split('string Reload(){',1)[1].split('void ValidateField(',1)[0]
  self.assertNotIn('if(V(data,"research_chain")!=null)',reload)
  self.assertIn('Path.Combine(tools,"comparison_data.py")',reload);self.assertIn('" --verify"',reload)
  self.note();real=comparison.build(self.root);tampered=json.loads(json.dumps(real));tampered['research_chain']=None;tampered['owner_preferences']['by_candidate'][self.key]['current_choice']='reject'
  self.assertNotEqual(comparison.build(self.root),tampered)

def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Application source changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

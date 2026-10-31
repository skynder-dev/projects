"""Actual saved-input selection/preparation-stage tests. Never token/model admission."""
from pathlib import Path
import argparse,ast,copy,hashlib,json,os,shutil,sys,tempfile,time,unittest
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
SOURCE=args.source.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE))
H=lambda raw:hashlib.sha256(raw).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():H(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
BEFORE=inventory(SOURCE)
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.startfile','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('Saved-context tests forbid transport/processes')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise PermissionError('Saved-context tests forbid models/tokenizers')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).resolve();flags=args[2] or 0
  if (path==SOURCE or SOURCE in path.parents) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Canonical source writes forbidden')
sys.addaudithook(audit)
import reveng_local_research as m,analysis_jobs as jobs,observation_history as history,saved_analysis_context as context
NOW=1792800000
STAMP='2026-10-24T00:00:00+00:00'

def row(number,author='SYNTHETIC_SAME_AUTHOR',eid='E1'):
 text='SYNTHETIC recurring export report '+str(number)+'. This is a unit input, not a real source capture.'
 return {'evidence_id':eid,'source':'softwarerecs','title':'SYNTHETIC export question '+str(number),'url':'https://softwarerecs.stackexchange.com/questions/'+str(900000000+number)+'/synthetic-unit-input','kind':'public_question_context','context_text':text,'excerpt':text,'context_text_sha256':H(text.encode()),'source_text_sha256':H(text.encode()),'source_field':'body','content_scope':'question_body','context_truncated':False,'observed_at':'2026-10-23T00:00:00+00:00' if number==1 else STAMP,'published_at':None,'author_id':author}

def prepared(root,rows,expiry,errors=None,request=None):
 run=root/('run-'+str(len(list(root.glob('run-*')))));run.mkdir()
 identifier=jobs.prepare(m,root,run,rows,[],errors or [],expiry,request or m.build_model_request(rows))
 path=root/'analysis-inputs'/(identifier+'.json');data=json.loads(path.read_bytes())
 return {'input_sha256':identifier,'input_file_sha256':H(path.read_bytes())},data,run

def select(current,old,data,eids=None):
 eids=eids or [r['evidence_id'] for r in data['observations']]
 refs=[{'evidence_id':r['evidence_id'],'row_sha256':context.row_sha256(r)} for r in data['observations'] if r['evidence_id'] in eids]
 return {'current_input':current,'selected_inputs':[dict(old,rows=refs)]}

class ContextTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory(prefix='reveng-context-unit-');self.addCleanup(temp.cleanup);self.outer=Path(temp.name).resolve();self.root=self.outer/'workspace';self.root.mkdir()
  self.clock=patch('time.time',return_value=NOW);self.clock.start();self.addCleanup(self.clock.stop)
  self.stamp=patch.object(m,'now',return_value=STAMP);self.stamp.start();self.addCleanup(self.stamp.stop)
 def pair(self,old_expiry=NOW+1800,current_expiry=NOW+3600,author='SYNTHETIC_SAME_AUTHOR'):
  old,old_data,_=prepared(self.root,[row(1,author)],old_expiry);current,current_data,run=prepared(self.root,[row(2,author)],current_expiry)
  return select(current,old,old_data),current_data,run
 def boundary(self,selection,current,run,expiry=None):
  return jobs.prepare(m,self.root,run,current['observations'],current['public_price_records'],current['source_errors'],current['source_expires'] if expiry is None else expiry,current['request'],saved_context=selection)
 def test_actual_two_round_delta_can_propose_old_context_without_new_capture(self):
  first_run=self.root/'round-old';first_run.mkdir();second_run=self.root/'round-new';second_run.mkdir()
  old_row=row(1);new_row=row(2)
  one,_=history.commit(m,self.root,first_run,history.load(m,self.root),[old_row],[],{'round':0,'scope':'SYNTHETIC_ONLY'},{'source_requests':0,'model_requests':0})
  old,old_data,_=prepared(self.root,one,NOW+1800)
  two,summary=history.commit(m,self.root,second_run,history.load(m,self.root),[old_row,new_row],[],{'round':1,'scope':'SYNTHETIC_ONLY'},{'source_requests':0,'model_requests':0})
  self.assertEqual(len(two),1);self.assertEqual(summary['captured_records'],2);self.assertEqual(two[0]['url'],new_row['url'])
  current,current_data,run=prepared(self.root,two,NOW+3600);selection=select(current,old,old_data);before=inventory(self.root)
  with self.assertRaises(context.TokenAdmissionRequired) as blocked:self.boundary(selection,current_data,run)
  proposal=blocked.exception.proposal;packets=proposal['source_packets'];self.assertEqual({p['title'] for p in packets},{old_row['title'],new_row['title']})
  self.assertEqual(proposal['effective_source_expires'],NOW+1800);self.assertFalse(proposal['source_dates_renewed']);self.assertFalse(proposal['queue_written']);self.assertIsNone(proposal['token_admission']['token_count'])
  self.assertEqual(inventory(self.root),before);self.assertEqual({p['observed_at'] for p in packets},{old_row['observed_at'],new_row['observed_at']})
  self.assertEqual([p['source_kind'] for p in packets],['public_question_context']*2)
  self.assertTrue(all(p['same_author_evidence_ids'] for p in packets));self.assertTrue(all(p['analysis_context']['independence']=='NOT_ESTABLISHED' for p in packets))
  request=proposal['request_proposal'];actual=json.loads(request['messages'][1]['content'].split('SOURCE OBSERVATIONS:\n',1)[1]);self.assertEqual(actual,packets)
  for original in [old_row,new_row]:self.assertIn(original['context_text'],request['messages'][1]['content'])
 def test_colliding_original_ids_get_explicit_alias_and_origin_map(self):
  selection,_,_=self.pair();out=context.proposal(m,self.root,selection)
  self.assertEqual([x['evidence_id'] for x in out['source_packets']],['E1','H1'])
  self.assertEqual([x['origins'][0]['original_evidence_id'] for x in out['selection_manifest']],['E1','E1'])
  self.assertNotEqual(out['selection_manifest'][0]['origins'][0]['input_sha256'],out['selection_manifest'][1]['origins'][0]['input_sha256'])
 def test_duplicate_selections_are_deterministic_not_additional_reports(self):
  selection,_,_=self.pair();selection['selected_inputs']*=2;out=context.proposal(m,self.root,selection);self.assertEqual(len(out['source_packets']),2)
  reversed_selection=copy.deepcopy(selection);reversed_selection['selected_inputs'].reverse();self.assertEqual(context.proposal(m,self.root,reversed_selection),out)
 def test_exact_same_row_from_different_jobs_keeps_all_origins_once(self):
  old,old_data,_=prepared(self.root,[row(1)],NOW+1800);other,other_data,_=prepared(self.root,[row(1)],NOW+900,errors=[{'reason':'SYNTHETIC different preparation metadata'}]);current,_,_=prepared(self.root,[row(2)],NOW+3600)
  selection=select(current,old,old_data);selection['selected_inputs'].append(select(current,other,other_data)['selected_inputs'][0]);out=context.proposal(m,self.root,selection)
  self.assertEqual(len(out['source_packets']),2);self.assertEqual(len(out['selection_manifest'][1]['origins']),2);self.assertEqual(out['effective_source_expires'],NOW+900)
 def test_unknown_authors_stay_unknown_not_independent(self):
  selection,_,_=self.pair(author=None);out=context.proposal(m,self.root,selection)
  for packet in out['source_packets']:
   self.assertNotIn('same_author_evidence_ids',packet);self.assertEqual(packet['analysis_context']['independence'],'NOT_ESTABLISHED')
 def test_expired_context_is_comparison_only_no_request_or_queue(self):
  selection,current,run=self.pair(old_expiry=NOW-1);before=inventory(self.root);view=context.proposal(m,self.root,selection)
  self.assertEqual(view['status'],'EXPIRED_SELECTION_READ_ONLY');self.assertNotIn('request_proposal',view);self.assertEqual(len(view['source_packets']),2)
  with self.assertRaisesRegex(ValueError,'Expired saved context'):self.boundary(selection,current,run)
  self.assertEqual(before,inventory(self.root))
 def test_expiry_during_construction_withholds_request(self):
  selection,_,_=self.pair()
  with patch('time.time',side_effect=[NOW,NOW+3601]):out=context.proposal(m,self.root,selection)
  self.assertEqual(out['status'],'EXPIRED_SELECTION_READ_ONLY');self.assertNotIn('request_proposal',out)
 def test_repinning_changed_file_cannot_bypass_sealed_payload_identity(self):
  selection,_,_=self.pair();locator=selection['selected_inputs'][0];path=self.root/'analysis-inputs'/(locator['input_sha256']+'.json')
  data=json.loads(path.read_bytes());data['source_expires']=NOW+999999;path.write_bytes(json.dumps(data).encode());locator['input_file_sha256']=H(path.read_bytes())
  with self.assertRaisesRegex(ValueError,'integrity mismatch'):context.proposal(m,self.root,selection)
 def test_no_caller_expiry_override_or_fake_token_admission(self):
  selection,current,run=self.pair();before=inventory(self.root)
  with self.assertRaisesRegex(ValueError,'no caller expiry override'):self.boundary(selection,current,run,expiry=NOW+99999)
  selection['token_count']=1
  with self.assertRaises(ValueError):self.boundary(selection,current,run)
  self.assertEqual(inventory(self.root),before)
 def test_missing_eid_wrong_row_hash_and_extra_fields_fail_before_writes(self):
  selection,current,run=self.pair();before=inventory(self.root)
  for change in ['missing','hash','extra']:
   value=copy.deepcopy(selection);ref=value['selected_inputs'][0]['rows'][0]
   if change=='missing':ref['evidence_id']='MISSING'
   elif change=='hash':ref['row_sha256']='0'*64
   else:ref['trusted']=True
   with self.subTest(change=change),self.assertRaises(ValueError):self.boundary(value,current,run)
  self.assertEqual(inventory(self.root),before)
 def test_raw_file_tamper_and_path_traversal_are_rejected(self):
  selection,current,run=self.pair();path=self.root/'analysis-inputs'/(selection['selected_inputs'][0]['input_sha256']+'.json');path.write_bytes(path.read_bytes()+b' ');before=inventory(self.root)
  with self.assertRaisesRegex(ValueError,'hash/size mismatch'):self.boundary(selection,current,run)
  selection['selected_inputs'][0]['input_sha256']='../outside'
  with self.assertRaisesRegex(ValueError,'SHA256'):self.boundary(selection,current,run)
  self.assertEqual(inventory(self.root),before)
 def test_row_and_file_count_bounds_fail_without_clipping(self):
  selection,current,run=self.pair();selection['selected_inputs']*=4
  with self.assertRaises(ValueError):self.boundary(selection,current,run)
  selection,_,_=self.pair();selection['selected_inputs'][0]['rows']*=context.MAX_SELECTED_ROWS
  with self.assertRaisesRegex(ValueError,'row count'):context.proposal(m,self.root,selection)
 def test_exact_combined_byte_cap_fails_without_truncating_source(self):
  large=row(1);large['context_text']='SYNTHETIC '+('Ж'*30000);large['excerpt']=large['context_text'];large['context_text_sha256']=H(large['context_text'].encode());large['source_text_sha256']=large['context_text_sha256']
  old,data,_=prepared(self.root,[large],NOW+1800);current,_,_=prepared(self.root,[row(2)],NOW+3600);before=inventory(self.root)
  with self.assertRaisesRegex(ValueError,'byte cap'):context.proposal(m,self.root,select(current,old,data))
  self.assertEqual(inventory(self.root),before)
 def test_oversized_input_file_rejected_before_parse(self):
  selection,_,_=self.pair();path=self.root/'analysis-inputs'/(selection['selected_inputs'][0]['input_sha256']+'.json')
  with path.open('ab') as stream:stream.truncate(context.MAX_INPUT_BYTES+1)
  with self.assertRaisesRegex(ValueError,'bounded size'):context.proposal(m,self.root,selection)
 def test_owned_file_and_directory_links_fail_closed(self):
  selection,_,_=self.pair();identifier=selection['selected_inputs'][0]['input_sha256'];path=self.root/'analysis-inputs'/(identifier+'.json');target=self.outer/'owned-outside.json';path.rename(target)
  try:path.symlink_to(target)
  except OSError as error:self.fail('Owned symlink test prerequisite unavailable, containment not qualified: '+str(error))
  original=H(target.read_bytes())
  with self.assertRaisesRegex(ValueError,'reparse/symlink'):context.proposal(m,self.root,selection)
  self.assertEqual(H(target.read_bytes()),original);path.unlink();target.rename(path)
  folder=self.root/'analysis-inputs';outside=self.outer/'owned-inputs';folder.rename(outside)
  try:folder.symlink_to(outside,target_is_directory=True)
  except OSError as error:self.fail('Owned directory link prerequisite unavailable: '+str(error))
  with self.assertRaisesRegex(ValueError,'reparse/symlink'):context.proposal(m,self.root,selection)
 def test_nonpublic_or_unrelated_metadata_not_promoted_into_packet(self):
  private=row(1);private['source']='private_contacts';old,data,_=prepared(self.root,[private],NOW+1800);current,_,_=prepared(self.root,[row(2)],NOW+3600)
  with self.assertRaisesRegex(ValueError,'public-source'):context.proposal(m,self.root,select(current,old,data))
  public=row(1);public['owner_email']='SYNTHETIC_PRIVATE_EXTRA@example.test';old,data,_=prepared(self.root,[public],NOW+1800);out=context.proposal(m,self.root,select(current,old,data))
  self.assertNotIn('owner_email',json.dumps(out));self.assertNotIn('SYNTHETIC_PRIVATE_EXTRA',json.dumps(out))
 def test_nondefault_current_request_is_not_silently_replaced(self):
  old,data,_=prepared(self.root,[row(1)],NOW+1800);request=m.build_model_request([row(2)]);request['messages'][1]['content']='SYNTHETIC extra attachment\n'+request['messages'][1]['content'];current,_,_=prepared(self.root,[row(2)],NOW+3600,request=request)
  with self.assertRaisesRegex(ValueError,'Non-default current request'):context.proposal(m,self.root,select(current,old,data))
 def test_default_prepare_body_matches_public97fc_normalized_ast(self):
  node=next(n for n in ast.parse((SOURCE/'analysis_jobs.py').read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
  self.assertEqual([a.arg for a in node.args.kwonlyargs],['saved_context'])
  self.assertEqual(ast.dump(node.args.kw_defaults[0]),ast.dump(ast.Constant(value=None)))
  expected=ast.parse("if saved_context is not None:\n import saved_analysis_context\n return saved_analysis_context.preparation_boundary(m,root,observations,prices,errors,expiry,request,saved_context)").body[0]
  self.assertEqual(ast.dump(node.body[0],include_attributes=False),ast.dump(expected,include_attributes=False))
  node.args.kwonlyargs=[];node.args.kw_defaults=[];node.body=node.body[1:]
  for part in ast.walk(node):
   if hasattr(part,'type_params'):
    self.assertFalse(part.type_params)
    part._fields=tuple(field for field in part._fields if field!='type_params')
  self.assertEqual(H(ast.dump(node,include_attributes=False).encode()),'d7cc54915b720a5d76807dce4e7b2b024dc757b339c4b860ab6a7e57ca201e7a')
 def test_default_prepare_public97fc_input_id_and_saved_output_pins(self):
  # Actual public97fc prepare output with identical fixed arguments and time.
  # Queue text normalizes only platform newline translation; immutable input is raw bytes.
  request={'messages':[{'role':'user','content':'SYNTHETIC deterministic prepare compatibility fixture; never dispatched.'}],'stream':False}
  locator,_,_=prepared(self.root,[row(2)],NOW+3600,request=request)
  self.assertEqual(locator['input_sha256'],'af417249c6da1275d3ce214f5f02aaebfe80e05d80592101276cdb92e8204bee')
  self.assertEqual(locator['input_file_sha256'],'bd6d56e540eaa0a881b13ac87e308080ddcd29fe19baa58d74ab644e9a67ec7c')
  self.assertEqual(H((self.root/'analysis-queue.json').read_text(encoding='utf-8').encode()),'1730394697cd7819da855954ace20c95ea10829a8f88f34b2b204f4c9d8c1f2d')
 def test_default_prepare_optional_none_matches_same_immutable_job(self):
  rows=[row(2)];request=m.build_model_request(rows);one,data,run=prepared(self.root,rows,NOW+3600);before=inventory(self.root)
  same=jobs.prepare(m,self.root,run,rows,[],[],NOW+3600,request,saved_context=None)
  self.assertEqual(same,one['input_sha256']);self.assertEqual(json.loads((self.root/'analysis-inputs'/(same+'.json')).read_bytes()),data);self.assertEqual(inventory(self.root),before)

def tearDownModule():
 if inventory(SOURCE)!=BEFORE:raise AssertionError('Source bytes changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

"""Concept-only review and local production preflight; no render/IPC/publishing."""
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,stable_json,atomic_bytes,utc_now
from .preparation import verify_preparation
from .source_quality import inspect_directory

def inspect(store,job_id):
 folder=store.folder(job_id);job=store.get(job_id)
 if job.get('state')!='prepared' or job.get('preparation_integrity_pass') is not True:raise PipelineError('A verified source preparation is required for concept review')
 root=Path(job['run_dir']);manifest=verify_preparation(root);script=read_json(root/'script.json');quality=inspect_directory(root);inputs={name:(sha256_file(root/name) if (root/name).is_file() else None) for name in ['script.json','storyboard.json','claims.json','description.md','sources.json']}
 ledger=read_json(root/'claims.json')['claims'];evidence=[{'claim_key':c['key'],'statement':c['statement'],'quote':c['source'].get('quote'),'url':c['source'].get('url'),'scope':'Saved source evidence for review; no individual entitlement or publication approval'} for c in ledger]
 concept={'schema':'SOCIAL_PRODUCTION_CONCEPT_V1','preparation_id':manifest['preparation_id'],'fact_version':script.get('fact_version'),'claim_evidence':evidence,'title':script['title'],'script':script,'description':((root/'description.md').read_text(encoding='utf-8') if (root/'description.md').is_file() else script.get('description','')),'input_sha256':inputs,'scope':'Source concept only; no generated audio/video or production/publication permission'}
 from .source_revisions import state as source_state
 source_history=source_state(store,job_id)
 if source_history['history']:concept['source_history_hash']=source_history['latest_hash']
 from .fact_versions import view as fact_view
 facts=fact_view(store,job_id)
 if facts['fact_version']:concept['adopted_fact_version']=facts['fact_version']
 version=sha256_bytes(stable_json(concept).encode('utf-8'));blockers=[]
 if inputs['description.md'] is None:blockers.append('Legacy preparation has no sealed description.md; embedded script description is reference only')
 if quality.get('editorial_integrity_pass') is not True:blockers.extend(quality.get('errors') or ['Editorial inputs are inconsistent'])
 if (quality.get('source_observation') or {}).get('state')!='verified_http_receipt':blockers.append('Concept approval needs a byte-verified authentic source receipt; reconstructed content is review-only')
 if script.get('synthetic'):blockers.append('Synthetic material cannot become an approved production concept')
 if (folder/'manual_script_draft.json').exists():blockers.append('A separate manual revision exists; materialize/revalidate the intended version instead of approving the original by accident')
 if facts['fact_version']:blockers.append('Accepted fact version requires a new aligned script/preparation and a new exact concept approval; fact acceptance is not scenario approval')
 if source_history['requires_review']:blockers.append('Changed source observations require reconciliation; source decisions do not approve facts')
 path=folder/'concept_review.json';revision=sha256_file(path) if path.exists() else 'absent';decision={'state':'pending','approved':False}
 if path.exists():
  try:
   saved=read_json(path);valid=saved.get('schema')=='SOCIAL_CONCEPT_REVIEW_V1' and saved.get('scope')=='production_concept' and saved.get('concept_version')==version
   decision={'state':saved.get('decision','pending') if valid else 'concept_version_mismatch','approved':valid and not blockers and saved.get('decision')=='approved' and saved.get('source_reviewed') is True,'reason':saved.get('reason'),'reviewer':saved.get('reviewer'),'source_reviewed':saved.get('source_reviewed') is True,'concept_version':saved.get('concept_version'),'scope':'production_concept','production_authorized':False,'publication_authorized':False}
   if blockers and decision['state']=='approved':decision['state']='approval_blocked_by_current_inputs'
  except (ValueError,TypeError,AttributeError):decision={'state':'review_record_unreadable','approved':False}
 return {'job_id':job_id,'concept':concept,'concept_version':version,'concept_reviewable':not blockers,'review_blockers':blockers,'revision':revision,'decision':decision,'source_observation':quality.get('source_observation'),'runtime_generation_blockers':quality.get('generation_blockers',[]),'models_started':False,'production_authorized':False,'publication_authorized':False}

def record(store,job_id,concept_version,expected_revision,decision,reviewer,reason,source_reviewed=False,rotation_scope=None):
 store.folder(job_id)
 if decision not in {'pending','approved','rejected','changes_requested'}:raise PipelineError('Unknown concept decision')
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120:raise PipelineError('Explicit concept reviewer required')
 if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Concept decision requires a reason up to2000 characters')
 from .motion_state import motion_lock
 with motion_lock(store.root,'concept_'+job_id,wait=5):
  current=inspect(store,job_id)
  if concept_version!=current['concept_version']:raise PipelineError('Concept version changed; reopen before reviewing')
  if expected_revision!=current['revision']:raise PipelineError('Concept review changed; refresh before saving')
  if decision=='approved' and (not current['concept_reviewable'] or source_reviewed is not True):raise PipelineError('Concept approval requires explicit source review and reviewable current inputs: '+'; '.join(current['review_blockers']))
  path=store.folder(job_id)/'concept_review.json'
  if path.exists():atomic_bytes(store.folder(job_id)/'concept_review_history'/(current['revision']+'.json'),path.read_bytes())
  write_json(path,{'schema':'SOCIAL_CONCEPT_REVIEW_V1','scope':'production_concept','job_id':job_id,'concept_version':concept_version,'preparation_id':current['concept']['preparation_id'],'decision':decision,'source_reviewed':source_reviewed is True,'reviewer':reviewer.strip(),'reason':reason.strip(),'at':utc_now().isoformat(),'previous_revision':current['revision'],'production_authorized':False,'publication_authorized':False,'audio_video_review_implied':False,'topic_rotation_scope':rotation_scope})
 return inspect(store,job_id)

def order_preflight(store,job_id):
 current=inspect(store,job_id);blockers=[]
 if not current['decision']['approved']:blockers.append('Exact concept approval missing or invalid')
 blockers.extend(current['review_blockers']);blockers.extend(current['runtime_generation_blockers'])
 root=Path(store.get(job_id)['run_dir']);assembly=read_json(root/'assembly-input.json') if (root/'assembly-input.json').is_file() else {};assets=assembly.get('assets') or {}
 missing=[role for role,key in [('narration_wav','wav'),('captions_srt','srt'),('measured_timing','timing')] if assets.get(key) is None];missing.append('agreed_visual_assets_or_exact_production_inputs')
 blockers.extend('Missing required production input: '+role for role in missing);blockers.append('Actual receiver capabilities/profile/IPC handshake have not been agreed or observed')
 return {'schema':'SOCIAL_LOCAL_ORDER_PREFLIGHT_V1','scope':'planning_only_no_handoff','job_id':job_id,'concept_version':current['concept_version'],'concept_review_revision':current['revision'],'concept_approved':current['decision']['approved'],'operation':'produce_video','proposed_profile':'assemble_measured_assets_v1','profile_confirmed_by_receiver':False,'expected_outputs':{'final_video':{'width':1080,'height':1920,'container':'mp4','duration_seconds_target':[20,30],'audio_required':True},'result_manifest':{'identity_and_hashes_required':True}},'acceptance_criteria':['Exact concept/input/output identities and hashes','Declared playable video with measured media properties','No silent script/caption/accent changes','Result requires separate listening and visual review'],'missing_input_roles':missing,'blockers':list(dict.fromkeys(blockers)),'ready_to_submit':False,'receiver_contacted':False,'job_or_attempt_created':False,'models_started':False,'publication_authorized':False}
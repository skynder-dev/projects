"""Finite source-bound NSF TTP decision-angle proposal; no approval or production."""
import copy,re,json,zipfile,tempfile
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,stable_json
from .source_revisions import digest
from .audience_selection import assess
from .claims import validate_script
from .track_script import validate_scopes
from .source_description import compose
from .editorial import storyboard
from .topic_rotation import snapshot
from .motion_state import motion_lock

PROFILE='nsf_ttp_prior_award_decision_v2'
REQUIRED=('purpose_quote','identity','tracks_track_order','track_E_eligibility','track_E_submission','tracks_TP_prior_funding','tracks_lead_organizations','tracks_PI_appointments','source_review_status')
def proposal(store,id,draft):
 store=snapshot(store);job=store.get(id)
 if not(job.get('preparation_integrity_pass') is True or job.get('package_integrity_pass') is True):raise PipelineError('Verified saved source/script required')
 root=Path(job['run_dir']);topic=read_json(root/'topic.json');rec=topic.get('selected') or topic;data=rec.get('track_conditions') or {};claims=read_json(root/'claims.json')['claims'];by={c['key']:c for c in claims};blocked=[]
 if data.get('schema')!='SOURCE_TRACK_CONDITIONS_V1' or data.get('prefix')!='NSF TTP':blocked.append('No finite reviewed decision-angle profile for this saved topic')
 if draft.get('adopted_fact_version') or (draft.get('source_history') or {}).get('requires_review'):blocked.append('Source/fact changes need aligned factual preparation before reusing this original-ledger proposal')
 if any(k not in by for k in REQUIRED):blocked.append('Required source-bound track/eligibility claims missing')
 fit=assess(rec,'institutional')
 if not fit.get('suitable'):blocked.append('Saved institutional audience profile not established')
 result={'schema':'SOCIAL_TRACK_ANGLE_PROPOSAL_V1','profile':PROFILE,'topic_supported':data.get('schema')=='SOURCE_TRACK_CONDITIONS_V1' and data.get('prefix')=='NSF TTP','job_id':id,'audience':'institutional','audience_fit':fit,'status':'blocked' if blocked else 'proposal_only','blocked_reasons':blocked,'original':draft['original'],'manual_revision':draft['revision'],'source_revision':(draft.get('source_history') or {}).get('latest_hash'),'source_currentness':'saved_only_not_rechecked','owner_decision_created':False,'concept_approved':False,'production_authorized':False,'publication_authorized':False,'models_started':False,'tts_started':False}
 if blocked:return result
 # The short hook must explain what this program is for, using saved evidence.
 purpose=by['purpose_quote'];quote=(purpose.get('values') or {}).get('quote','');src=purpose.get('source') or {};file=(root/str(src.get('snapshot_file',''))).resolve()
 if not quote or 'research to practice' not in quote.lower() or purpose.get('statement')!='The official synopsis says: "'+quote+'"' or src.get('url')!=rec.get('source_url') or not file.is_relative_to(root.resolve()) or not file.is_file() or file.stat().st_size>8*1024*1024 or sha256_file(file)!=src.get('snapshot_sha256'):raise PipelineError('Research-to-practice purpose evidence is missing or not bound to this saved source')
 body=read_json(file);detail=body.get('data') or {}
 from .common import strip_html
 synopsis=detail.get('synopsis') or {};text=re.sub(r'\s+',' ',strip_html(synopsis.get('synopsisDesc') or '')).strip()
 if str(detail.get('id'))!=str(rec.get('opportunity_id')) or quote not in text:raise PipelineError('Purpose quotation does not match the exact saved program synopsis')
 prefix=data['prefix'];all_ids=[prefix+'-'+s for s in 'ETP'];e=data['tracks'].get(prefix+'-E') or {};details=(e.get('eligibility') or {}).get('details') or {}
 if details.get('active_eligible_NSF_award_required') is not True or details.get('prior_email_approval_required') is not True:raise PipelineError('Explore active-award/prior-approval conditions are not established')
 if (e.get('submission') or {}).get('state')!='known':raise PipelineError('Explore invitation/submission evidence missing')
 text=' '.join(by['tracks_TP_prior_funding']['statement'].lower().split())
 if 'prior federal funding is not a requirement for submission' not in text:raise PipelineError('Exact saved Translate/Partner prior-funding exception is not established')
 if 'invitation' not in by['track_E_submission']['statement'].lower():raise PipelineError('Explore invitation evidence missing')
 for k,ids in [('track_E_eligibility',{prefix+'-E'}),('track_E_submission',{prefix+'-E'}),('tracks_TP_prior_funding',{prefix+'-T',prefix+'-P'})]:
  if set(by[k].get('values',{}).get('track_ids',[]))!=ids or by[k]['source'].get('snapshot_sha256')!=data['source']['sha256'] or by[k]['source'].get('url')!=(data['source'].get('final_url') or data['source'].get('url')):raise PipelineError('Track evidence scope/source binding differs: '+k)
 segs=[]
 def add(role,voice,accent,keys,ids):
  start=voice.find(accent)
  if start<0 or voice.count(accent)!=1 or len(accent.split())>9:raise PipelineError('Proposal accent is not an exact short spoken span')
  segs.append({'id':'a'+str(len(segs)+1),'role':role,'visual':'quote','voiceover':voice,'on_screen':{'headline':accent,'kicker':'','sub':''},'screen_anchor':{'start_char':start,'end_char':start+len(accent),'text':accent},'claim_keys':keys,'track_ids':ids,'delivery':{'native_audio_required':True,'post_atempo':1.0,'measured_timing_required':True,'status':'not_synthesized'}})
 add('hook','Research to practice: do all TTP tracks require prior NSF funding?','do all TTP tracks require prior NSF funding?',['purpose_quote','identity','tracks_track_order'],all_ids)
 add('track_E','Explore: prior approval and invitation required, with an active, eligible NSF award.','Explore: prior approval and invitation required',['track_E_eligibility','track_E_submission'],[prefix+'-E'])
 add('tracks_TP',"Translate and Partner don't require prior federal funding.","Translate and Partner don't require prior federal funding",['tracks_TP_prior_funding'],[prefix+'-T',prefix+'-P'])
 add('who','Institutional eligibility rules still apply.','Institutional eligibility rules still apply',['tracks_lead_organizations','tracks_PI_appointments'],all_ids)
 add('cta','Check Grants.gov; sources below.','Check Grants.gov',['identity','source_review_status'],all_ids)
 desc=[{'claim_key':c['key'],'text':c['statement'],'source':c['source']} for c in claims if c['key'].startswith(('track_','tracks_','dependency_')) or c['key'] in {'source_review_status','purpose_quote'}]
 script={'writer':PROFILE,'editorial_contract':'SOCIAL_SOURCE_DECISION_REEL_V1','decision_profile':PROFILE,'audience':'institutional','spoken_delivery':{'post_atempo':1.0},'background_policy':'Source-review storyboard only; no generated assets or audio','title':rec['title']+' — prior-award decision DRAFT','segments':segs,'description_detail_policy':'all_scoped_track_and_purpose_claims_v2','description_details':desc,'description':'\n\n'.join(s['voiceover'] for s in segs)+'\n\nFull source-bound track and policy conditions:\n'+'\n\n'.join(d['text'] for d in desc),'track_schema':data['schema'],'source_note':'Saved source-bound proposal only. No live currentness, individual eligibility or scenario approval. Review all track, invitation, partner, training and linked-policy conditions.'}
 errors=validate_script(script,claims)+validate_scopes(script,claims)
 from .meaning_review import accent_issues
 errors+=[issue for seg in segs for issue in accent_issues(seg['voiceover'],seg['on_screen']['headline'])]
 if errors:raise PipelineError('Decision-angle source/scene checks: '+'; '.join(dict.fromkeys(errors)))
 description=compose(script,claims,rec);_,board=storyboard(script,claims,rec)
 spoken=' '.join(s['voiceover'] for s in segs)
 expansions={'NSF':'N S F','TTP':'T T P','Grants.gov':'Grants dot gov'}
 for token,expanded_text in expansions.items():spoken=re.sub(r'\b'+re.escape(token)+r'\b',expanded_text,spoken)
 expanded=len(spoken.split())
 if expanded>48:raise PipelineError('Decision-angle expanded text exceeds conservative48-word source draft budget')
 result.update(script=script,description=description,storyboard=board,text_budget={'whitespace_words':sum(len(s['voiceover'].split()) for s in segs),'expanded_known_acronym_words':expanded,'expansions':expansions,'measured_audio_duration':None,'speech_or_pronunciation_tested':False},benefit='Compare track entry requirements instead of applying the Explore prior-award rule to the whole program',claim_evidence=[by[k] for k in REQUIRED],scope_warning='Prior federal funding not required does not establish applicant eligibility; this is an institutional program, not a personal money offer',claims_sha256=sha256_file(root/'claims.json'),original_script_sha256=sha256_file(root/'script.json'),checks={'claim_scope_and_number_checks':True,'exact_spoken_screen_spans':True,'complete_primary_track_policy_description':True,'semantic_entailment_approved':False},format_status='Five-scene source proposal; no measured20–30s duration or finished reel claimed',requires_new_preparation_and_concept_review=True)
 result['proposal_version']=digest(result)
 return result

def _version(value):
 if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise PipelineError('Invalid proposal version')
 return value

def verify_zip(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if sum(i.file_size for i in z.infolist())>65*1024*1024 or z.getinfo('proposal_manifest.json').file_size>1024*1024:raise PipelineError('Proposal archive exceeds bounded review size')
  if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts or ':' in n or '\\' in n for n in names):raise PipelineError('Unsafe proposal ZIP paths')
  manifest=json.loads(z.read('proposal_manifest.json'))
  if manifest.get('schema')!='SOCIAL_SOURCE_ANGLE_REVIEW_ZIP_V1' or manifest.get('production_authorized') is not False:raise PipelineError('Wrong proposal review format')
  if set(names)!={e['path'] for e in manifest['files']}|{'proposal_manifest.json'}:raise PipelineError('Proposal ZIP entry set changed')
  for item in manifest['files']:
   data=z.read(item['path'])
   if sha256_bytes(data)!=item['sha256'] or len(data)!=item['bytes']:raise PipelineError('Proposal ZIP bytes changed')
  value=json.loads(z.read('proposal.json'))
  if value.get('job_id')!=manifest.get('job_id') or value.get('profile')!=manifest.get('profile') or any(value.get(k) is not False for k in ('production_authorized','publication_authorized','concept_approved','models_started','owner_decision_created')):raise PipelineError('Proposal context/approval flags changed')
  if value.get('proposal_version')!=manifest.get('proposal_version') or digest({k:v for k,v in value.items() if k!='proposal_version'})!=manifest['proposal_version']:raise PipelineError('Proposal identity changed')
  if json.loads(z.read('script.json'))!=value['script'] or z.read('description.md').decode('utf-8')!=value['description'] or json.loads(z.read('storyboard.json'))!=value['storyboard']:raise PipelineError('Proposal review projections disagree')
  if sha256_bytes(z.read('claims.json'))!=value['claims_sha256']:raise PipelineError('Proposal ledger changed')
 return manifest

def export(store,id,value,expected_version):
 if value.get('status')!='proposal_only' or value.get('proposal_version')!=expected_version:raise PipelineError('Proposal/source/manual context changed; reopen before exporting')
 _version(expected_version);job=store.get(id);root=Path(job['run_dir']);parent=read_json(root/('prepared.json' if (root/'prepared.json').is_file() else 'package_manifest.json'));content={}
 def json_data(value):return stable_json(value).encode('utf-8')
 content['proposal.json']=json_data(value);content['script.json']=json_data(value['script']);content['description.md']=value['description'].encode('utf-8');content['storyboard.json']=json_data(value['storyboard']);content['claims.json']=(root/'claims.json').read_bytes();content['sources.json']=(root/'sources.json').read_bytes()
 for entry in parent['files']:
  name=entry['path']
  if not name.startswith(('source/','source_recheck/')):continue
  if Path(name).is_absolute() or '..' in Path(name).parts or ':' in name:raise PipelineError('Invalid parent source locator')
  p=(root/name).resolve()
  if not p.is_relative_to(root.resolve()) or sha256_file(p)!=entry['sha256']:raise PipelineError('Parent saved source changed')
  content[name]=p.read_bytes()
 if sum(len(b) for b in content.values())>64*1024*1024:raise PipelineError('Proposal review ZIP exceeds64MiB source limit')
 manifest={'schema':'SOCIAL_SOURCE_ANGLE_REVIEW_ZIP_V1','job_id':id,'proposal_version':expected_version,'profile':PROFILE,'files':[{'path':name,'sha256':sha256_bytes(data),'bytes':len(data)} for name,data in sorted(content.items())],'production_authorized':False,'concept_approved':False,'publication_authorized':False,'models_started':False}
 target=store.root/'angle_proposals'/(id+'_'+expected_version+'.zip');target.parent.mkdir(exist_ok=True)
 with motion_lock(store.root,'angle_export_'+id+'_'+expected_version[:12],wait=5):
  if not target.exists():
   with tempfile.TemporaryDirectory(prefix='_angle_',dir=target.parent) as folder:
    temp=Path(folder)/'review.zip'
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
     for name,data in content.items():z.writestr(name,data)
     z.writestr('proposal_manifest.json',json_data(manifest))
    verify_zip(temp);temp.rename(target)
  if verify_zip(target)!=manifest:raise PipelineError('Cached proposal review differs from exact current source context; preserved without overwrite')
  if not target.with_suffix('.receipt.json').exists():write_json(target.with_suffix('.receipt.json'),{'proposal_version':expected_version,'sha256':sha256_file(target),'bytes':target.stat().st_size})
  return download(store,id,expected_version)

def download(store,id,version):
 _version(version);store.folder(id);p=store.root/'angle_proposals'/(id+'_'+version+'.zip');receipt=read_json(p.with_suffix('.receipt.json'))
 if sha256_file(p)!=receipt['sha256']:raise PipelineError('Saved angle review archive changed')
 manifest=verify_zip(p)
 if manifest['job_id']!=id or manifest['proposal_version']!=version:raise PipelineError('Proposal archive belongs to another context')
 return {'path':str(p),'sha256':receipt['sha256'],'bytes':p.stat().st_size,'proposal_version':version,'state':'source_review_DRAFT','production_authorized':False}

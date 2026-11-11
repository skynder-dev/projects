"""Bound manual script drafts. Never mutate a sealed package, render or approve."""
from pathlib import Path
import copy,json,re
from socialreel.common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,stable_json,utc_now
from socialreel.motion_state import motion_lock
from socialreel.manual_draft_integrity import read as read_manual_draft

def original(store,id):
 job=store.get(id)
 root=Path(job['run_dir']);script=root/'script.json'
 if job.get('state')=='prepared' and job.get('preparation_integrity_pass') is True:
  from socialreel.preparation import verify_preparation
  manifest=verify_preparation(root)
  return {'package_id':manifest['preparation_id'],'preparation_id':manifest['preparation_id'],'kind':'source_preparation','script_sha256':sha256_file(script)},read_json(script)
 if job.get('package_integrity_pass') is not True:raise PipelineError('Verified original package or source preparation required for editing')
 package=read_json(root/'package_manifest.json')['package_id']
 return {'package_id':package,'script_sha256':sha256_file(script)},read_json(script)

def review_projection(store,id,identity,base,current):
 root=Path(store.get(id)['run_dir'])
 ledger=read_json(root/'claims.json');claims={c['key']:c for c in ledger.get('claims',[])}
 source=read_json(root/'sources.json').get('selected_snapshot') or {}
 scenes=[]
 for old,new in zip(base['segments'],current['segments']):
  changed=old['voiceover']!=new['voiceover'];headline=(new.get('on_screen') or {}).get('headline');anchor=new.get('screen_anchor') or {}
  a,b=anchor.get('start_char'),anchor.get('end_char');exact=isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(new['voiceover']) and new['voiceover'][a:b]==headline==anchor.get('text')
  evidence=[{'claim_key':key,'original_statement':claims[key].get('statement'),'source':claims[key].get('source'),'scope':'original evidence reference; not confirmation of edited narration'} for key in old.get('claim_keys',[]) if key in claims]
  from socialreel.meaning_review import accent_issues,change_review
  from socialreel.narrative_checks import screen_field
  meaning={'visible_text':screen_field(headline) if headline is not None else {'preparation_valid':False,'errors':['Missing current screen accent']},'narration_change':change_review(old['voiceover'],new['voiceover']),'screen_issues':accent_issues(new['voiceover'],headline),'semantic_approval_implied':False}
  scenes.append({'meaning_review':meaning,'id':new['id'],'voiceover':new['voiceover'],'headline':headline,'screen_anchor':anchor if exact else None,'screen_text_status':'exact_current_spoken_span_unreviewed' if exact else 'missing_or_invalid_current_spoken_span','source_confirmation':'unverified_user_edit' if changed else 'unchanged_original_wording_not_new_source_verification','original_evidence':evidence,'requires_factual_review':changed})
 rejection=None;path=store.folder(id)/'editorial_review.json'
 if path.is_file():
  review=read_json(path)
  rejection={'decision':review.get('decision'),'reason':review.get('reason'),'package_id':review.get('package_id'),'applies_to_original_package':review.get('package_id')==identity['package_id'],'applies_to_manual_revision':False}
 return {'scenes':scenes,'source_currentness':'not_rechecked','last_observed_at':source.get('fetched_at'),'source_url':source.get('url'),'original_editorial_decision':rejection,'ready_for_generation':False,'ready_for_assembly':False,'description_status':'original_reference_requires_review_if_narration_changed'}

def publication_review(base,current,text=''):
 return {'description_draft':{'text':text,'status':'unverified_manual_text' if text else 'missing_for_manual_revision'},'original_description_reference':{'text':base.get('description',''),'details':base.get('description_details',[]),'scope':'original version reference only; not current manual description'},'cta_scenes':[{'id':s['id'],'text':s['voiceover'],'status':'requires_review_against_current_description_and_sources'} for s in current['segments'] if s.get('role') in {'cta','one_action','next_step'}],'numbers_conditions_urls_confirmed':False,'ready_for_publication':False}

def derive_publication(store,id,base,current,text=''):
 root=Path(store.get(id)['run_dir']);claims=read_json(root/'claims.json')['claims'];topic=read_json(root/'topic.json');record=topic.get('selected',topic)
 from socialreel.source_description import automatic_manual_description
 result=publication_review(base,current,text);automatic=automatic_manual_description(base,current,claims,record)
 result.update(automatic)
 from socialreel.source_urls import manual_links
 result['link_review']=manual_links(text,record)
 if not text:result['description_draft']['status']='automatic_from_unchanged_saved_facts'
 for cta in result['cta_scenes']:
  cta['status']='requires_review_due_to_edited_facts' if automatic['conflicts'] else 'unchanged_saved_action_requires_currentness_review'
  cta['conflicting_claim_keys']=automatic['excluded_claim_keys']
 return result

def isolate_publication_text(script,text='',automatic=None):
 script=copy.deepcopy(script)
 script.pop('description',None);script.pop('description_details',None)
 inherited=script.get('original_editorial_metadata_reference') or {'scope':'original version reference only; not confirmed for manual narration','fields':{}}
 for key in ('money_benefit','concrete_use','audience_description','audience_fit','source_note'):
  if key in script:inherited['fields'][key]=script.pop(key)
 script['original_editorial_metadata_reference']=inherited
 script['production_status']='manual_source_and_publication_text_review_required'
 if text:script['description']=text
 script['description_details']=[]
 script['publication_text_review_required']=True
 script['description_status']='unverified_manual_text' if text else 'missing_for_manual_revision'
 script['cta_review_required']=True
 if automatic:
  if not text:
   script['description']=automatic['automatic_description']
   script['description_status']='automatic_from_unchanged_saved_facts_requires_currentness_review'
  script['fact_version']=automatic['fact_version']
  money=automatic['money_metadata'];script['money_metadata_status']=money['state']
  if money['value'] is not None:script['money_benefit']=money['value']
  script['fact_conflicts']=automatic['conflicts']
 return script

def load(store,id):
 identity,script=original(store,id);path=store.folder(id)/'manual_script_draft.json'
 out={'state':'original_script','original':identity,'script':script,'revision':'absent','publication_authorized':False,'rendered':False,'worker_started':False}
 if path.exists():
  draft=read_manual_draft(path,identity,script)
  publication=draft.get('publication_text') or {}
  text=(publication.get('description_draft') or {}).get('text','')
  automatic=derive_publication(store,id,script,draft['script'],text)
  out.update(state='unrendered_script_draft',script=isolate_publication_text(draft['script'],text,automatic),revision=sha256_file(path),draft_id=draft['draft_id'])
  out['publication_text']=automatic
 from socialreel.source_revisions import state as source_state
 history=source_state(store,id)
 out['source_history']={'latest_hash':history['latest_hash'],'requires_review':history['requires_review'],'facts_approved':False}
 from socialreel.fact_versions import view as fact_view
 facts=fact_view(store,id)
 out['adopted_fact_version']=facts['fact_version']
 out['fact_revalidation_required']=bool(facts['fact_version'])
 out['review']=review_projection(store,id,identity,script,out['script'])
 if out.get('publication_text'):out['review']['description_status']=out['publication_text']['description_draft']['status']
 return out

def save(store,id,package,revision,voiceovers,screen_accents=None,description_text=None):
 with motion_lock(store.root,'scriptdraft_'+id,wait=5):
  identity,script=original(store,id);before=load(store,id)
  if package!=identity['package_id']:raise PipelineError('Wrong original package; draft not saved')
  input_intent=sha256_bytes(stable_json({'package':package,'voiceovers':voiceovers,'screen_accents':screen_accents,'description_text':description_text}).encode())
  if not isinstance(revision,str) or revision!=before['revision']:
   path=store.folder(id)/'manual_script_draft.json';saved=read_json(path) if path.exists() else {}
   if isinstance(revision,str) and saved.get('previous_revision')==revision and saved.get('input_intent_sha256')==input_intent:return {**before,'save_replayed':True}
   raise PipelineError('Script draft changed; refresh before saving')
  segments=script.get('segments') or []
  if not isinstance(voiceovers,list) or len(voiceovers)!=len(segments):raise PipelineError('All original segment identities must be preserved')
  if any(not isinstance(x,str) or not x.strip() or len(x)>3000 or any(ord(c)<32 and c not in '\n\t' for c in x) for x in voiceovers):raise PipelineError('Each segment needs plain nonempty text up to 3000 characters')
  if screen_accents is not None and (not isinstance(screen_accents,list) or len(screen_accents)!=len(segments) or any(not isinstance(x,str) for x in screen_accents)):raise PipelineError('Provide one plain screen accent per scene')
  value=copy.deepcopy(script)
  # Partial/legacy clients may omit the accent field. Preserve the saved manual
  # accent only while its narration is unchanged; a new voice line must rebind it.
  if screen_accents is None and before['state']=='unrendered_script_draft':
   previous=before['script']['segments']
   for segment,saved,line in zip(value['segments'],previous,voiceovers):
    if line.strip()==saved['voiceover']:
     segment['on_screen']=copy.deepcopy(saved.get('on_screen') or {})
     for key in ('screen_anchor','screen_accent_status','screen_accent_review_required'):
      if key in saved:segment[key]=copy.deepcopy(saved[key])
      else:segment.pop(key,None)
  for index,(segment,text) in enumerate(zip(value['segments'],voiceovers)):
   revised=text.strip()
   if revised!=segment['voiceover']:
    segment['voiceover']=revised
    preserved=screen_accents is None and before['state']=='unrendered_script_draft' and revised==before['script']['segments'][index]['voiceover']
    if not preserved:
     segment['on_screen']={}
     segment.pop('screen_anchor',None)
    segment['screen_accent_review_required']=True
    segment['claim_revalidation_required']=True
   if screen_accents is not None:
    accent=screen_accents[index].strip()
    if accent:
     if len(accent)>200 or len(accent.split())>9 or any(ord(c)<32 for c in accent):raise PipelineError('Screen accent must be at most 9 spoken words on one line')
     positions=[m.start() for m in re.finditer(r'(?<!\w)'+re.escape(accent)+r'(?!\w)',revised)]
     if len(positions)!=1:raise PipelineError('Scene '+str(index+1)+': screen accent must occur exactly once in its current narration, using the same spelling')
     from socialreel.meaning_review import accent_issues
     issues=accent_issues(revised,accent)
     if issues:raise PipelineError('Scene '+str(index+1)+': '+'; '.join(issues)+'; choose a short honest spoken phrase')
     start=positions[0];segment['on_screen']={'headline':accent,'kicker':'','sub':''};segment['screen_anchor']={'start_char':start,'end_char':start+len(accent),'text':accent}
     segment['screen_accent_status']='exact_current_spoken_span_unreviewed'
    else:
     segment['on_screen']={};segment.pop('screen_anchor',None);segment['screen_accent_status']='missing_current_spoken_span'
    # A valid text span restores synchronization intent only, never factual or visual approval.
    segment['screen_accent_review_required']=True
  # Original factual evidence remains a reference only. Changed narration invalidates its screen accent; no stale text is treated as synchronized output.
  if description_text is None:description_text=((before.get('publication_text') or {}).get('description_draft') or {}).get('text','')
  if not isinstance(description_text,str) or len(description_text)>12000 or any(ord(c)<32 and c not in '\n\t\r' for c in description_text):raise PipelineError('Manual description must be plain text up to 12000 characters')
  publication=derive_publication(store,id,script,value,description_text)
  value=isolate_publication_text(value,description_text,publication)
  identity_input={'original':identity,'script':value,'publication_text':publication};draft_id=sha256_bytes(stable_json(identity_input).encode())
  path=store.folder(id)/'manual_script_draft.json'
  saved_value={'schema':'SOCIAL_MANUAL_SCRIPT_DRAFT_V1','previous_revision':before['revision'],'input_intent_sha256':input_intent,**identity_input,'draft_id':draft_id,'saved_at':utc_now().isoformat(),'state':'unrendered_script_draft','new_voice_required':True,'new_captions_required':True,'new_render_required':True,'factual_revalidation_required':True,'editorial_approved':False,'publication_authorized':False}
  from socialreel.manual_draft_integrity import validate as validate_manual_draft
  validate_manual_draft(saved_value,identity,script)
  if path.exists():
   from socialreel.common import atomic_bytes
   previous=path.read_bytes();history=store.folder(id)/'manual_script_draft_history'/(before['revision']+'.json')
   if sha256_bytes(previous)!=before['revision']:raise PipelineError('Manual draft changed before save; refresh without overwriting')
   if history.exists() and history.read_bytes()!=previous:raise PipelineError('Manual history identity conflict; both files preserved')
   if not history.exists():atomic_bytes(history,previous)
  write_json(path,saved_value)
  return load(store,id)

"""Persistent review rotation of existing verified cards, no discovery or production."""
from pathlib import Path
from .common import read_json,write_json,sha256_file,PipelineError,utc_now
from .source_revisions import state as source_state,digest
from .audience_selection import assess,AUDIENCES
from .motion_state import motion_lock

def audience(value):
 if value not in AUDIENCES:raise PipelineError('Choose a known topic audience')
 return value

class SnapshotStore:
 def __init__(self,store):self.store=store;self.root=store.root;self.cache={}
 def get(self,id):
  if id not in self.cache:self.cache[id]=self.store.get(id)
  return self.cache[id]
 def folder(self,id):return self.store.folder(id)
 def connect(self):return self.store.connect()

def snapshot(store):return store if isinstance(store,SnapshotStore) else SnapshotStore(store)

def scope(store,id,group,original=False):
 store=snapshot(store)
 audience(group);job=store.get(id)
 if not(job.get('preparation_integrity_pass') is True or job.get('package_integrity_pass') is True):raise PipelineError('Topic rotation requires verified saved inputs')
 root=Path(job['run_dir']);topic=read_json(root/'topic.json');record=topic.get('selected') or topic;script=read_json(root/'script.json');claims=read_json(root/'claims.json')['claims'];notes=[]
 if not original:
  history=source_state(store,id)
  if history['history']:claims=history['history'][-1]['observation']['claims'];notes.append('Changed saved source candidates require review; not newly approved')
  from .fact_versions import view as fact_view
  facts=fact_view(store,id)
  if facts['fact_version'] and facts['manifest']['source_revision']==history['latest_hash']:
   claims=facts['_claims'];notes.append('Explicit fact revision exists; scenario/concept revalidation still required')
  path=store.folder(id)/'manual_script_draft.json'
  if path.exists():
   from .manual_draft_integrity import read as read_manual_draft
   name='prepared.json' if job.get('preparation_integrity_pass') else 'package_manifest.json';manifest=read_json(root/name)
   identity={'package_id':manifest.get('preparation_id') if name=='prepared.json' else manifest.get('package_id'),'script_sha256':sha256_file(root/'script.json')}
   if name=='prepared.json':identity.update(preparation_id=manifest['preparation_id'],kind='source_preparation')
   draft=read_manual_draft(path,identity,script)
   script=draft['script'];notes.append('Manual script revision requires factual review')
 facts=[]
 for c in claims:
  values=c.get('values') or {};values={k:v for k,v in values.items() if k not in {'previous','days_left_at_build'}} if isinstance(values,dict) else values
  facts.append({'key':c['key'],'statement':c.get('statement'),'values':values})
 content={'claims':sorted(facts,key=lambda c:c['key']),'scenes':[{'id':s['id'],'voiceover':s.get('voiceover'),'screen':s.get('on_screen')} for s in script.get('segments',[])],'description':script.get('description'),'details':[{'claim_key':x.get('claim_key'),'text':x.get('text')} for x in script.get('description_details',[])]}
 return {'opportunity_id':str(record['opportunity_id']),'basis':digest(content),'audience':group,'job_id':id,'original_only':original,'title':record.get('title'),'fit':assess(record,group),'notes':notes}

def _load(store):
 p=store.root/'topic_review_rotation.json'
 value=read_json(p) if p.exists() else {'schema':'SOCIAL_TOPIC_ROTATION_V1','events':[],'visits':{},'last_selected':{},'rounds':{},'imports':[],'selected_audience':'general_us'}
 if not isinstance(value,dict):raise PipelineError('Topic review journal invalid; original preserved')
 value.setdefault('last_selected',{})
 if value.get('schema')!='SOCIAL_TOPIC_ROTATION_V1' or any(not isinstance(value.get(k),list) for k in ('events','imports')) or any(not isinstance(value.get(k),dict) for k in ('visits','rounds','last_selected')):raise PipelineError('Topic review journal invalid; original preserved')
 return value
def selected_audience(store):return audience(_load(store).get('selected_audience','general_us'))
def _key(value):return value['audience']+'|'+value['opportunity_id']+'|'+value['basis']
def _cards(store,group):
 with store.connect() as c:ids=[r[0] for r in c.execute("SELECT id FROM jobs ORDER BY updated DESC")]
 cards=[];unavailable=[]
 for id in ids:
  try:cards.append(scope(store,id,group))
  except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:unavailable.append({'job_id':id,'reason':str(error)[:180]})
 # Same saved factual/editorial basis appears once, without deleting any story.
 unique={}
 for card in cards:unique.setdefault(_key(card),card)
 return list(unique.values()),unavailable,ids

def _reconcile(store,data,ids):
 records=[];unscoped=[]
 for id in ids:
  folder=store.folder(id)
  paths=[folder/'concept_review.json',folder/'editorial_review.json']
  paths+=list((folder/'concept_review_history').glob('*.json'))+list((folder/'editorial_history').glob('*.json'))
  for p in paths:
   if not p.is_file():continue
   value=read_json(p);ref=sha256_file(p);saved=value.get('topic_rotation_scope')
   if not saved:
    if value.get('decision') in {'rejected','changes_requested'}:
     try:old=scope(store,id,'general_us',original=True)
     except (PipelineError,OSError,ValueError,KeyError,TypeError):old={}
     unscoped.append({'job_id':id,'review_sha256':ref,'opportunity_id':old.get('opportunity_id'),'basis':old.get('basis'),'decision':value['decision'],'reason':value.get('reason'),'at':value.get('at',''),'note':'Legacy review has no audience scope; same basis is held for explicit confirmation, not silently assigned to an audience'})
    continue
   records.append((value.get('at',''),id,ref,saved,value))
 for _,id,ref,saved,value in sorted(records,key=lambda r:(r[0],r[1],r[2])):
   if ref in data['imports'] or saved.get('audience') not in AUDIENCES or saved.get('job_id')!=id:continue
   try:expected=scope(store,id,saved['audience'],original=True)
   except (PipelineError,OSError,ValueError,KeyError,TypeError):continue
   if any(saved.get(k)!=expected[k] for k in ('opportunity_id','basis')):continue
   decision={'rejected':'rejected','changes_requested':'deferred','pending':'deferred'}.get(value.get('decision'))
   if not decision:continue
   data['events'].append({'scope':saved,'decision':decision,'reviewer':value.get('reviewer'),'reason':value.get('reason'),'source_review_hash':ref,'at':value.get('at'),'skip_until':data['rounds'].get(saved['audience'],0)+2 if decision=='deferred' else None,'approval_inherited':False})
   data['imports'].append(ref)
 data['events'].sort(key=lambda e:e.get('at',''))
 return unscoped

def view(store,group=None):
 store=snapshot(store)
 group=audience(group or selected_audience(store));data=_load(store);cards,unavailable,ids=_cards(store,group);legacy=_reconcile(store,data,ids);round=data['rounds'].get(group,0);rows=[]
 for card in cards:
  exact=[e for e in data['events'] if _key(e['scope'])==_key(card)];previous=[e for e in data['events'] if e['scope']['audience']==group and e['scope']['opportunity_id']==card['opportunity_id']];last=exact[-1] if exact else None
  returned=last and last['decision']=='returned';state='available';explanation='Saved topic; audience/source/meaning still require review'
  if last and last['decision']=='rejected':state='rejected_same_basis';explanation=last['reason']
  elif last and last['decision']=='deferred' and round<last['skip_until']:state='deferred';explanation=last['reason']+'; returns after bounded selection passes'
  elif last and last['decision']=='deferred':explanation='Deferral elapsed; unresolved reason: '+last['reason']
  elif returned:explanation='Explicitly returned for review: '+last['reason']
  elif not last and previous:explanation='Material source/editorial basis changed; review again. Previous reason: '+previous[-1]['reason']
  old_legacy=[e for e in legacy if e.get('opportunity_id')==card['opportunity_id']]
  same_legacy=[e for e in old_legacy if e.get('basis')==card['basis']]
  if state=='available' and same_legacy and (not returned or any(e['review_sha256'] not in last.get('confirmed_legacy_hashes',[]) for e in same_legacy)):
   state='legacy_refusal_needs_scope';explanation='Legacy refusal is held for explicit audience/version confirmation: '+str(same_legacy[-1].get('reason'))
  elif state=='available' and not last and old_legacy and not same_legacy:explanation='Material basis differs from legacy refusal; review again. Previous reason: '+str(old_legacy[-1].get('reason'))
  if returned and not card['fit']['suitable']:explanation+='; audience fit still not established: '+card['fit']['reason']
  if state=='available' and not card['fit']['suitable'] and not returned:
   state='audience_fit_not_established';explanation=(explanation+'; audience fit not established: '+card['fit']['reason']) if (not last and (previous or old_legacy)) else card['fit']['reason']
  rows.append({**card,'state':state,'explanation':explanation,'last_decision':last,'visits':data['visits'].get(_key(card),0),'last_selected_pass':data['last_selected'].get(_key(card),-1),'editorial_approved':False})
 rows.sort(key=lambda r:(r['last_selected_pass'],r['opportunity_id'],r['job_id']))
 available=[r for r in rows if r['state']=='available']
 revision=digest({'data':data,'cards':rows})
 return {'schema':'SOCIAL_TOPIC_ROTATION_V1','audience':group,'round':round,'version':revision,'cards':rows,'next':available[0] if available else None,'empty_reason':None if available else 'all_deferred_for_this_pass' if any(r['state']=='deferred' for r in rows) else 'no_suitable_unrejected_saved_topic','unavailable':unavailable,'legacy_unscoped_decisions':legacy,'all_stories_preserved':True,'facts_approved':False,'models_started':False,'_data':data,'_store':store}

def public(value):return {k:v for k,v in value.items() if not k.startswith('_')}
def decide(store,id,group,basis,expected_version,decision,reviewer,reason):
 if decision not in {'rejected','deferred','returned'}:raise PipelineError('Unknown topic review decision')
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120 or not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Explicit reviewer and reason required')
 with motion_lock(store.root,'topic_rotation',wait=5):
  current=view(store,group)
  if current['version']!=expected_version:raise PipelineError('Topic queue changed; reopen before saving')
  wanted=scope(current['_store'],id,group)
  card=next((c for c in current['cards'] if c['opportunity_id']==wanted['opportunity_id'] and c['basis']==basis==wanted['basis']),None)
  if not card:raise PipelineError('Topic basis changed or duplicate representative; reopen saved card queue')
  data=current['_data'];data['events'].append({'scope':{k:card[k] for k in ('opportunity_id','basis','audience','job_id')},'decision':decision,'reviewer':reviewer.strip(),'reason':reason.strip(),'confirmed_legacy_hashes':[e['review_sha256'] for e in current['legacy_unscoped_decisions'] if e.get('opportunity_id')==card['opportunity_id'] and e.get('basis')==card['basis']] if decision=='returned' else [],'at':utc_now().isoformat(),'skip_until':current['round']+2 if decision=='deferred' else None,'approval_inherited':False});data['selected_audience']=group;write_json(store.root/'topic_review_rotation.json',data)
 return public(view(store,group))
def advance(store,group,expected_version):
 with motion_lock(store.root,'topic_rotation',wait=5):
  current=view(store,group)
  if current['version']!=expected_version:raise PipelineError('Topic queue changed; reopen before selecting')
  data=current['_data'];chosen=current['next'];data['selected_audience']=group
  if chosen:
   data['visits'][_key(chosen)]=chosen['visits']+1;data['last_selected'][_key(chosen)]=current['round']
  if chosen or current['empty_reason']=='all_deferred_for_this_pass':data['rounds'][group]=current['round']+1
  write_json(store.root/'topic_review_rotation.json',data)
 return {'selected':chosen,'empty_reason':current['empty_reason'],'queue':public(view(store,group)),'models_started':False,'publication_authorized':False}


def set_audience(store,previous,group,expected_version):
 audience(group)
 with motion_lock(store.root,'topic_rotation',wait=5):
  current=view(store,previous)
  if current['version']!=expected_version:raise PipelineError('Topic queue changed; reopen audience selection')
  data=current['_data'];data['selected_audience']=group;write_json(store.root/'topic_review_rotation.json',data)
 return public(view(store,group))

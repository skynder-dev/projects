"""Source-preserving manual review versions; never production/assembly approval."""
import hashlib,json,os,tempfile,zipfile
from pathlib import Path
from socialreel.common import PipelineError,read_json,sha256_file,sha256_bytes,stable_json
from local_script_draft import load,original

def version(store,id,expected_revision):
 draft=load(store,id)
 if draft['state']!='unrendered_script_draft' or draft['revision']!=expected_revision:raise PipelineError('Saved script revision changed; reopen before exporting')
 identity,base=original(store,id);root=Path(store.get(id)['run_dir']).resolve()
 name='prepared.json' if identity.get('kind')=='source_preparation' else 'package_manifest.json'
 manifest=read_json(root/name);content={}
 # Only declared original source/editorial material, never old media or undeclared files.
 selected={'sources.json','topic.json','claims.json','script.json','storyboard.json','description.md','editorial_source_brief.json','source_quality.json'}
 for e in manifest.get('files',[]):
  rel=e['path'];p=(root/rel).resolve()
  if rel not in selected and not rel.startswith('source/'):continue
  if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size!=e['bytes'] or sha256_file(p)!=e['sha256']:raise PipelineError('Original review source changed: '+rel)
  content['original/'+rel]=p.read_bytes()
 if not {'original/script.json','original/claims.json','original/sources.json'}.issubset(content):raise PipelineError('Declared original script/claim/source evidence required')
 content['original/'+name]=(root/name).read_bytes()
 changes=[];scenes=[]
 for before,after in zip(base['segments'],draft['script']['segments']):
  changed=before['voiceover']!=after['voiceover'];screen_changed=before.get('on_screen')!=after.get('on_screen') or before.get('screen_anchor')!=after.get('screen_anchor')
  if changed or screen_changed:changes.append({'scene_id':after['id'],'before':before['voiceover'],'after':after['voiceover'],'original_claim_keys_reference_only':before.get('claim_keys',[]),'source_confirmation':'unverified_user_edit' if changed else 'unchanged_original_wording_not_new_source_verification','change_kind':'narration' if changed else 'screen_accent_only','requires':['factual_revalidation','description_review','screen_accent_review','new_audio_and_alignment'] if changed else ['screen_accent_review','new_visual_review']})
  scenes.append({'id':after['id'],'voiceover':after['voiceover'],'caption_text':after['voiceover'],'headline':(after.get('on_screen') or {}).get('headline'),'screen_anchor':after.get('screen_anchor'),'screen_text_status':draft['review']['scenes'][len(scenes)]['screen_text_status'],'source_confirmation':'unverified_user_edit' if changed else 'unchanged_original_wording_not_new_source_verification','original_claim_keys_reference_only':before.get('claim_keys',[]),'timing':None})
 publication=draft['publication_text'];description=publication['description_draft']['text']
 if description:changes.append({'change_kind':'manual_description','text':description,'source_confirmation':'unverified_user_edit','requires':['factual_revalidation','link_and_conditions_review','cta_review']})
 if not changes:raise PipelineError('No narration, screen-accent or description changes; export the original package instead')
 def add(name,value):content[name]=stable_json(value).encode('utf-8')
 add('publication_text_review.json',publication)
 content['description_review.md']=('UNVERIFIED MANUAL DESCRIPTION - NOT APPROVED FOR PUBLICATION\n\n'+description if description else 'AUTOMATIC CANDIDATE FROM UNCHANGED SAVED FACTS - CURRENTNESS NOT RECHECKED; EDITED FACTS EXCLUDED\n\n'+publication['automatic_description']).encode('utf-8')
 add('manual_script.json',draft['script']);add('changes.json',changes);add('editorial_review_context.json',draft['review'])
 add('storyboard_review.json',{'state':'requires_editorial_review','scenes':scenes,'ready_for_assembly':False})
 metadata={'schema':'SOCIAL_MANUAL_REVIEW_PACKAGE_V1','parent':identity,'manual_revision':draft['revision'],'draft_id':draft['draft_id'],'state':'manual_source_review_required','accepted':False,'ready_for_generation':False,'ready_for_assembly':False,'publication_authorized':False,'source_currentness_confirmed':False,'source_claims_for_changed_text_confirmed':False,'description_scope':'automatic unchanged-fact candidate or unverified manual override; edited facts flagged; original reference preserved','assets':{'wav':None,'srt':None,'mp4':None,'timing':None},'files':[{'path':k,'bytes':len(v),'sha256':sha256_bytes(v)} for k,v in sorted(content.items())]}
 metadata['version_id']=sha256_bytes(stable_json(metadata).encode('utf-8'));add('manual_review.json',metadata)
 return metadata,content

def verify(path,expected=None):
 try:
  with zipfile.ZipFile(path) as z:
   names=z.namelist()
   if len(names)!=len(set(names)) or z.testzip():raise PipelineError('Manual review archive damaged or duplicate')
   m=json.loads(z.read('manual_review.json'));entries=m['files']
   from socialreel.draft_check import entry_errors
   if entry_errors(entries):raise PipelineError('Unsafe manual review manifest')
   if set(names)!={e['path'] for e in entries}|{'manual_review.json'}:raise PipelineError('Manual review archive contents differ')
   if m.get('schema')!='SOCIAL_MANUAL_REVIEW_PACKAGE_V1' or any(m.get(k) is not False for k in ['accepted','ready_for_generation','ready_for_assembly','publication_authorized','source_currentness_confirmed','source_claims_for_changed_text_confirmed']):raise PipelineError('Manual review is not an approved production package')
   check=dict(m);identity=check.pop('version_id')
   if sha256_bytes(stable_json(check).encode('utf-8'))!=identity:raise PipelineError('Manual review identity mismatch')
   if expected and m!=expected:raise PipelineError('Manual review belongs to another saved revision')
   for e in entries:
    data=z.read(e['path'])
    if len(data)!=e['bytes'] or sha256_bytes(data)!=e['sha256']:raise PipelineError('Manual review input bytes changed')
   return m
 except (zipfile.BadZipFile,KeyError,ValueError) as error:raise PipelineError('Manual review unavailable: '+str(error)) from error

def exported(store,id,revision,create=False):
 if create:
  from socialreel.fact_versions import view as fact_view
  if fact_view(store,id)['fact_version']:raise PipelineError('Accepted fact version requires aligned script/evidence revalidation before a new manual export; historical pinned exports remain references')
 metadata,content=version(store,id,revision);target=store.root/'manual_exports'/(id+'_'+metadata['version_id']+'.zip')
 if not target.exists():
  if not create:raise PipelineError('Export the saved manual revision first')
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='_manual_',dir=target.parent) as folder:
   temp=Path(folder)/'draft.zip'
   with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(content.items()):z.writestr(name,data)
   verify(temp,metadata);os.link(temp,target)
 verify(target,metadata)
 return {'path':str(target),'sha256':sha256_file(target),'bytes':target.stat().st_size,'version_id':metadata['version_id'],'manual_revision':revision,'integrity_verified':True,'state':metadata['state'],'accepted':False,'ready_for_generation':False,'ready_for_assembly':False}

def download_revision(store,id,revision):
 """An old download link must never silently select a newly edited revision."""
 if not isinstance(revision,str) or len(revision)!=64 or any(c not in '0123456789abcdef' for c in revision):raise PipelineError('Exact exported manual revision required; export this saved version first')
 return exported(store,id,revision,create=False)

"""Current material differs from a verified historical preview. No inherited approval."""
from pathlib import Path
from .common import read_json,sha256_file,PipelineError

def status(store,id,job):
 folder=store.folder(id);reasons=[];manual=folder/'manual_script_draft.json';revision='absent';saved=False;valid=None
 if manual.exists():
  saved=True;reasons.append('Saved manual revision requires factual/screen/description and new-media review')
  try:
   revision=sha256_file(manual)
   if manual.stat().st_size>1024*1024:raise ValueError('Draft exceeds diagnostic bound')
   value=read_json(manual);valid=isinstance(value,dict) and isinstance(value.get('script'),dict) and isinstance(value.get('original'),dict)
   if not valid:raise ValueError('Manual draft shape invalid')
   root=Path(job['run_dir']);basehash=sha256_file(root/'script.json')
   name='prepared.json' if job.get('preparation_integrity_pass') else 'package_manifest.json';manifest=read_json(root/name);identity=manifest.get('preparation_id') if name=='prepared.json' else manifest.get('package_id')
   valid=value['original'].get('script_sha256')==basehash and value['original'].get('package_id')==identity
   if not valid:reasons.append('Manual revision belongs to stale original inputs; preserved without adoption')
   from .manual_draft_integrity import read as read_manual_draft
   identity={'package_id':identity,'script_sha256':basehash}
   if name=='prepared.json':identity.update(preparation_id=manifest['preparation_id'],kind='source_preparation')
   read_manual_draft(manual,identity,read_json(root/'script.json'))
  except (OSError,ValueError,TypeError,KeyError,AttributeError,PipelineError):valid=False;reasons.append('Manual revision unreadable/unbound; preserved, never silently fall back to approved original')
 head=folder/'fact_adoption/head.json';fact=None
 if head.exists():
  try:
   value=read_json(head)
   if not isinstance(value,dict) or 'fact_version' not in value:raise ValueError('Invalid fact head')
   fact=value['fact_version']
   if fact is not None and (not isinstance(fact,str) or len(fact)!=64 or any(c not in '0123456789abcdef' for c in fact)):raise ValueError('Invalid fact identity')
   if fact:reasons.append('Accepted fact version needs a new aligned scenario and exact review')
  except (OSError,ValueError,TypeError,AttributeError):reasons.append('Fact head unreadable; current material review required')
 history=folder/'source_revisions'
 if history.exists() and any(history.glob('*.json')):reasons.append('Source observations differ from the original preparation; reconcile the intended version')
 return {'schema':'SOCIAL_CURRENT_MATERIAL219','manual_draft_saved':saved,'manual_revision':revision,'manual_original_binding_valid':valid,'adopted_fact_version':fact,'requires_review':bool(reasons),'reasons':reasons,'ready_for_generation':False if reasons else job.get('ready_for_generation',False),'old_media_scope':'original_inputs_reference_only' if reasons else 'current_saved_inputs','publication_authorized':False}

def effective_decision(original,material):
 if not material['requires_review']:return original
 original=original or {}
 return {**original,'state':'pending','approved':False,'package_bound':False,'listening_attested':False,'visual_review_attested':False,'reason':'Current material is unreviewed: '+'; '.join(material['reasons']),'approval_invalid_reasons':list(material['reasons']),'historical_package_decision_preserved':True,'manual_revision':material['manual_revision'],'publication_authorized':False}

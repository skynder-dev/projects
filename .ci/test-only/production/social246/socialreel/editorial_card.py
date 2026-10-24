"""Visible saved-evidence brief; never automatic entailment or editorial approval."""
from pathlib import Path
from .common import read_json,PipelineError,sha256_bytes,stable_json
from .meaning_review import accent_issues,change_review,signals
from .audience_selection import assess

def evidence(claim):
 source=claim.get('source') or {}
 return {'claim_key':claim['key'],'statement':claim.get('statement'),'values':claim.get('values'),'source_url':source.get('url'),'snapshot_sha256':source.get('snapshot_sha256'),'fields':source.get('fields',[]),'quote':source.get('quote') or source.get('exact_quotes') or source.get('quotes'),'constraints':signals(claim.get('statement') or ''),'scope':'saved evidence reference; not current verification or confirmation of manual text'}

def inspect(store,id,draft):
 job=store.get(id)
 if not (job.get('preparation_integrity_pass') is True or job.get('package_integrity_pass') is True):raise PipelineError('Editorial card requires verified saved source/script inputs')
 root=Path(job['run_dir']);topic=read_json(root/'topic.json');record=topic.get('selected') or topic
 base=read_json(root/'script.json');claims=read_json(root/'claims.json')['claims'];by={c['key']:c for c in claims};script=draft['script'];segments=script.get('segments') or []
 if not segments:raise PipelineError('No saved script scenes')
 hook=next((s for s in segments if s.get('role')=='hook'),segments[0]);old=next((s for s in base.get('segments',[]) if s['id']==hook['id']),{})
 keys=hook.get('claim_keys',[]);proof=[evidence(by[k]) for k in keys if k in by];missing=[k for k in keys if k not in by]
 description=script.get('description','')
 if draft['state']=='original_script' and (root/'description.md').is_file():description=(root/'description.md').read_text(encoding='utf-8')
 details=script.get('description_details',[]);mapped=[d for d in details if d.get('claim_key') in keys];mapped_keys={d['claim_key'] for d in mapped};unmapped=[k for k in keys if k not in mapped_keys]
 warnings=[]
 if not keys:warnings.append('Hook has no explicit claim references')
 if missing:warnings.append('Hook references missing claims: '+', '.join(missing))
 screen=(hook.get('on_screen') or {}).get('headline','')
 from .editorial_integrity import inspect_screen,script_alignment
 hook_alignment=inspect_screen(hook.get('voiceover',''),screen,claims)
 screen_issues=[] if hook_alignment['correspondence']=='conservative_correspondence' else accent_issues(hook.get('voiceover',''),screen)
 if screen_issues==['Screen emphasis does not occur in current narration']:screen_issues=['Screen paraphrase requires semantic review; nonliteral wording alone is not a factual contradiction']
 warnings.extend(screen_issues)
 if not screen:warnings.append('Hook screen accent is missing')
 change=change_review(old.get('voiceover',''),hook.get('voiceover',''))
 if change['text_changed']:warnings.append('Hook differs from sealed source version; original evidence does not verify edited text')
 if not description:warnings.append('Description is missing for this version')
 elif unmapped:warnings.append('Description has no explicit claim mapping for: '+', '.join(unmapped)+'; compare the saved text below')
 for detail in mapped:
  if detail.get('text')!=by.get(detail['claim_key'],{}).get('statement'):warnings.append('Description text differs from saved claim: '+detail['claim_key'])
  if detail.get('source')!=by.get(detail['claim_key'],{}).get('source'):warnings.append('Description source binding differs from saved claim: '+detail['claim_key'])
 configured=record.get('_selection_audience');p=root/'preparation_config.json'
 if p.is_file():configured=(read_json(p).get('selection') or {}).get('audience',configured)
 fits={name:assess(record,name) for name in ('general_us','small_business','institutional')}
 applicant=[evidence(c) for c in claims if c['key'] in {'primary_applicant','eligibility','eligibility_note','eligibility_restricted','proposer_restriction','proposer_policy'} or c['key'].startswith('track_') and 'eligib' in c['key']]
 purpose=[evidence(c) for c in claims if c['key'] in {'primary_purpose','purpose_quote','program_purpose','concrete_use'}]
 brief=record.get('editorial_brief') or {}
 angle={'audience_description':brief.get('audience_description'),'concrete_use':brief.get('concrete_use'),'money_scope':brief.get('money_benefit'),'scope':'saved editorial interpretation, not a new verified fact or individual eligibility decision'}
 if not purpose and not angle['concrete_use']:warnings.append('No explicit saved purpose/use claim; title and award amount do not establish viewer benefit')
 decisions=[]
 for name in ('concept_review.json','editorial_review.json'):
  p=store.folder(id)/name
  if p.is_file():
   saved=read_json(p);decisions.append({'scope':saved.get('scope') or saved.get('schema'),'decision':saved.get('decision'),'reviewer':saved.get('reviewer'),'reason':saved.get('reason'),'concept_version':saved.get('concept_version'),'package_id':saved.get('package_id'),'scope_note':'Saved decision reference; current version validity is checked by the existing review controls'})
 value={'schema':'SOCIAL_EDITORIAL_CARD_V1','job_id':id,'script_state':draft['state'],'manual_revision':draft['revision'],'configured_audience':configured or 'not_recorded','audience_fit':fits,'saved_editorial_angle':angle,'applicant_evidence':applicant,'benefit_evidence':purpose,'benefit_scope':'Applicant eligibility is not a personal entitlement; beneficiary/use remains unknown unless evidenced above','hook':{'scene_id':hook['id'],'voiceover':hook.get('voiceover'),'screen_text':screen,'evidence':proof,'missing_claim_keys':missing,'critical_changes':change,'source_constraints_require_human_comparison':True},'description':{'text':description,'mapped_hook_claims':mapped,'unmapped_hook_claims':unmapped,'mapping_is_not_semantic_approval':True},'warnings':list(dict.fromkeys(warnings)),'saved_decisions':decisions,'source_revision_pending':(draft.get('source_history') or {}).get('requires_review',False),'evidence_currentness':'saved_only_not_rechecked','semantic_entailment_verified':False,'editorial_approved':False,'publication_authorized':False,'predicted_engagement_or_virality':None}
 alignment=script_alignment(script,claims)
 value['screen_alignment']=alignment;value['hook']['screen_relation_audit']=hook_alignment;value['diagnostic_revision']='editorial-metadata252'
 for row in alignment['scenes']:
  if row.get('missing_screen'):value['warnings'].append('Scene '+str(row['scene_id'])+': screen field missing')
  for field,audit in row['fields'].items():
   if audit['correspondence']!='conservative_correspondence' or audit['findings'] or audit.get('integrity_error'):value['warnings'].append('Scene '+str(row['scene_id'])+'.'+field+': screen correspondence requires semantic review')
 model_path=root/'editorial_analysis.json'
 if model_path.is_file():
  if model_path.stat().st_size>512*1024:raise PipelineError('Saved model editorial evidence exceeds review budget')
  model=read_json(model_path);value['local_model_editorial']={'analysis':model.get('editorial_analysis'),'presentation':model.get('editorial_presentation'),'program_metadata':model.get('editorial_metadata'),'execution':model.get('local_editorial'),'scope':'Saved model advice and alternatives; not source fact, approved script or measured engagement'}
 value['version']=sha256_bytes(stable_json({'diagnostic_revision':'editorial-metadata252','original':draft['original'],'manual_revision':draft['revision'],'source_history':draft.get('source_history'),'script':script}).encode())
 from .owner_locale import present
 return present(value)

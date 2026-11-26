"""Read-only editorial checks, separate from byte integrity and model execution."""
from pathlib import Path
from .common import read_json,PipelineError,sha256_file

def assess(record,script,claims,board,config,source_observation=None):
 errors=[];blocks=[]
 if script.get('model_editorial_review_required'):
  from .local_editorial import HOLD
  blocks.append(HOLD)
  if script.get('model_topic_decision')=='reject':blocks.append('Local editorial analysis rejected this topic; owner review required')
 short=script.get('editorial_contract')=='SOCIAL_BENEFIT_REEL_V1'
 if not short:blocks.append('Legacy script needs current audience and synchronized-story review; bytes are preserved')
 from .audience_selection import assess as audience_fit
 fit=audience_fit(record,config.get('selection',{}).get('audience','general_us'))
 if not fit.get('suitable'):blocks.append('No suitable topic for configured audience')
 from .claims import validate_script
 errors.extend(validate_script(script,claims))
 if script.get('editorial_contract')=='SOCIAL_FACT_RECONCILED_SOURCE_V1':
  from .source_materialization import board as reconciled_board,HOLD
  if board!=reconciled_board(script):errors.append('Reconciled source storyboard differs from saved scenario')
  blocks.append(HOLD)
 from .source_description import compose
 try:compose(script,claims,record)
 except (PipelineError,KeyError,TypeError,ValueError) as e:errors.append('Description invalid: '+str(e)[:250])
 if short:
  from .scene_coherence import board as build_board
  try:
   expected=build_board(script,claims)
   if board.get('scenes')!=expected['scenes']:errors.append('Stored storyboard does not match current script, accents and claim sources')
  except (PipelineError,KeyError,TypeError,ValueError) as e:errors.append('Storyboard invalid: '+str(e)[:250])
  brief=record.get('editorial_brief')
  if brief:
   from .editorial_brief import factual_claim_payload
   if [factual_claim_payload(c) for c in claims]!=[factual_claim_payload(c) for c in brief.get('claims',[])]:errors.append('Claim ledger differs from source-bound editorial brief')
   from .source_description import fact_version
   if script.get('fact_version') is not None and script['fact_version']!=fact_version(claims):errors.append('Script fact version differs from current source claim ledger')
   if script.get('money_benefit')!=brief.get('money_benefit'):errors.append('Money metadata differs from this version of the source-bound editorial brief')
   keys=brief.get('main_facts') or {};by={c['key']:c for c in claims}
   for segment in script.get('segments',[]):
    key=keys.get(segment.get('role'));claim=by.get(key,{})
    if segment.get('claim_keys')!=[key]:errors.append('Narration claim scope differs from source-bound brief: '+str(segment.get('id')))
    if segment.get('voiceover')!=claim.get('statement'):
     if script.get('model_editorial_review_required'):blocks.append('Model narration differs from reviewed source wording; entailment remains unverified: '+str(segment.get('id')))
     else:errors.append('Narration differs from source-bound reviewed wording: '+str(segment.get('id')))
   if brief.get('live_verified') is not True:blocks.append('Actual live ingest not verified; supplied/reconstructed source is draft-only')
  if script.get('synthetic'):blocks.append('Synthetic fixture is never production material')
  if script.get('spoken_delivery',{}).get('post_atempo')!=1.0:blocks.append('Mechanical audio acceleration is not an editorial fix')
  voice=config.get('voice') or {}
  if voice.get('backend')!='kokoro':blocks.append('Short Social narration requires fixed local Kokoro; no fallback voice')
  if voice.get('voice','af_heart')!='af_heart':blocks.append('Permanent English female voice is af_heart')
  try:
   if float(voice.get('speed',1.0))!=1.0:blocks.append('Voice speed changes need separate listening review; expected 1.0')
  except (TypeError,ValueError):blocks.append('Invalid voice speed')
 if record.get('source_conditions_unconfirmed') is True:blocks.append('Full source conditions remain unconfirmed')
 if config.get('generation_hold'):blocks.append(str(config['generation_hold']))
 if source_observation and source_observation.get('state')=='verified_http_receipt':blocks=[('Official page HTTP receipt verified; factual/currentness acceptance remains required' if x=='Actual live ingest not verified; supplied/reconstructed source is draft-only' else x) for x in blocks]
 if source_observation and source_observation.get('state')=='invalid_receipt':errors.append('Transport receipt integrity failed: '+source_observation.get('detail','Unknown mismatch'))
 return {'source_observation':source_observation or {'state':'not_checked'},'schema':'SOCIAL_SOURCE_QUALITY_V1','editorial_integrity_pass':not errors,'errors':list(dict.fromkeys(errors)),
  'generation_blockers':list(dict.fromkeys(blocks+errors)),'ready_for_generation':not (errors or blocks),'audience_fit':fit,
  'actual_audio_verified':False,'ready_for_assembly':False,'publication_authorized':False,
  'scope':'Current source/editorial policy only; source freshness and execution authorization remain separate checks'}

def inspect_observation(directory,record):
 """Transport proof only; never infer factual approval/current entitlement from HTTP200."""
 if not record.get('public_money_source'):
  from .federal_source_receipt import inspect
  return inspect(directory,record)
 root=Path(directory).resolve()
 try:
  snapshot=read_json(root/'sources.json').get('selected_snapshot') or {}
  ref=snapshot.get('receipt_file')
  if not ref:return {'state':'reconstructed_fixture' if snapshot.get('reconstructed') else 'supplied_content_without_http_receipt','fetched_at':None,'current_source_confirmed':False,'source_facts_confirmed':False}
  def bound(name,digest):
   if not isinstance(name,str) or not isinstance(digest,str):raise PipelineError('Missing bound source receipt path/hash')
   path=(root/name).resolve()
   if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size>2*1024*1024 or sha256_file(path)!=digest:raise PipelineError('Source observation bytes missing, changed or outside package')
   return path
  receipt=read_json(bound(ref,snapshot.get('receipt_sha256')))
  if receipt.get('schema')!='SOCIAL_PUBLIC_PAGE_RECEIPT_V1' or receipt.get('state')!='received' or receipt.get('status')!=200 or receipt.get('source_facts_confirmed') is not False:raise PipelineError('Invalid source transport receipt schema/state')
  from .public_page import allowed
  if receipt.get('source_catalog')=='general_us_information_v1':
   from .automatic_research import allowed as catalog_allowed
   kind=receipt.get('source_kind')
   if kind not in {'energy','wages','unclaimed'} or not catalog_allowed(receipt.get('request_url',''),kind) or not catalog_allowed(receipt.get('final_url',''),kind):raise PipelineError('Automatic catalog receipt URL mismatch')
  elif not allowed(receipt.get('request_url','')) or not allowed(receipt.get('final_url','')):raise PipelineError('Receipt official URL mismatch')
  raw=bound(snapshot.get('raw_file'),receipt.get('raw_sha256'));decoded=bound(snapshot.get('file'),receipt.get('decoded_sha256'))
  if snapshot.get('raw_sha256')!=receipt['raw_sha256'] or snapshot.get('sha256')!=receipt['decoded_sha256'] or record['public_money_source'].get('content_sha256')!=receipt['decoded_sha256']:raise PipelineError('Receipt/raw/decoded/parsed source identity mismatch')
  encoding=receipt.get('encoding')
  if encoding not in {'utf-8','utf-8-sig'} or raw.read_bytes().decode(encoding).encode('utf-8')!=decoded.read_bytes():raise PipelineError('Decoded source differs from exact raw bytes/declared encoding')
  mode=receipt.get('mode')
  if mode=='fixture':
   if receipt.get('http_observed') is not False or receipt.get('fetched_at') is not None or snapshot.get('reconstructed') is not True:raise PipelineError('Fixture observation cannot attest live HTTP')
   state='verified_fixture_receipt'
  elif mode=='live':
   if receipt.get('http_observed') is not True or not receipt.get('fetched_at') or snapshot.get('not_http_observation') is not False or snapshot.get('reconstructed') is not False:raise PipelineError('Live observation flags missing or contradictory')
   state='verified_http_receipt'
  else:raise PipelineError('Unknown receipt mode')
  return {'state':state,'receipt_integrity_pass':True,'source_facts_confirmed':False,'current_source_confirmed':False,'fetched_at':receipt.get('fetched_at'),'page_updated':snapshot.get('source_updated'),'http_last_modified':receipt.get('last_modified'),'raw_sha256':receipt['raw_sha256'],'decoded_sha256':receipt['decoded_sha256'],'receipt_sha256':snapshot['receipt_sha256'],'scope':'Saved transport/byte identity only; no eligibility, factual/currentness or production approval'}
 except (OSError,ValueError,KeyError,TypeError,AttributeError,UnicodeError,PipelineError) as error:
  return {'state':'invalid_receipt','receipt_integrity_pass':False,'detail':str(error)[:250],'source_facts_confirmed':False,'current_source_confirmed':False}

def inspect_directory(directory,config_override=None):
 root=Path(directory)
 try:
  topic=read_json(root/'topic.json');record=topic.get('selected',topic)
  claims=read_json(root/'claims.json');claims=claims.get('claims') if isinstance(claims,dict) else claims
  for claim in claims:
   if claim.get('listing_scope'):
    from .listing_claims import verify_typed
    verify_typed(root,claim)
  script=read_json(root/'script.json')
  result=assess(record,script,claims,read_json(root/'storyboard.json'),config_override if config_override is not None else read_json(root/'preparation_config.json'),source_observation=inspect_observation(root,record))
  if (root/'source/dependencies/dependency_graph.json').is_file():
   from .source_dependencies import verify
   dependencies=verify(root/'source/dependencies')
   result['source_dependencies']=dependencies
   if not dependencies['overview_source_review_complete']:
    result['generation_blockers'].extend('Linked policy unresolved: '+e for e in dependencies['errors']);result['ready_for_generation']=False
  if (root/'assembly-input.json').is_file():
   assembly=read_json(root/'assembly-input.json');expected={'script':'script.json','claims':'claims.json','storyboard':'storyboard.json','description':'description.md','source_quality':'source_quality.json'}
   valid=assembly.get('schema')=='SOCIAL_ASSEMBLY_INPUT_V1' and assembly.get('state')=='source_only' and assembly.get('ready_for_assembly') is False
   valid=valid and assembly.get('script')==script and assembly.get('storyboard')==read_json(root/'storyboard.json')
   assets=assembly.get('assets') or {}
   valid=valid and set(assembly.get('inputs',{}))==set(expected) and set(assets)=={'wav','srt','mp4','timing','raw_asr'} and all(v is None for v in assets.values())
   valid=valid and assembly.get('synthetic') is bool(script.get('synthetic')) and assembly.get('source_quality')==read_json(root/'source_quality.json')
   if valid:
    for key,name in expected.items():
     entry=assembly['inputs'].get(key) or {}
     if entry.get('path')!=name or entry.get('sha256')!=sha256_file(root/name):valid=False;break
   if not valid:
    result['errors'].append('Assembly source input differs from bound script/files or invents generated media');result['generation_blockers'].append(result['errors'][-1]);result['editorial_integrity_pass']=False;result['ready_for_generation']=False
   result['assembly_source_input_integrity_pass']=valid
  if (root/'description.md').is_file():
   from .source_description import compose
   if (root/'description.md').read_text(encoding='utf-8').strip()!=compose(script,claims,record).strip():
    result['errors'].append('Stored description does not match current bound script and conditions')
    result['generation_blockers'].append(result['errors'][-1]);result['editorial_integrity_pass']=False;result['ready_for_generation']=False
  return result
 except (OSError,ValueError,KeyError,TypeError,AttributeError,PipelineError) as e:
  return {'schema':'SOCIAL_SOURCE_QUALITY_V1','editorial_integrity_pass':False,'errors':[str(e)[:300]],'generation_blockers':['Source-package inputs unavailable; preserve original and review'],'ready_for_generation':False,'ready_for_assembly':False,'publication_authorized':False}

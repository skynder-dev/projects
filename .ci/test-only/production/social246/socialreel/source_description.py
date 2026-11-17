"""One complete source-bound description for draft, export and local release plan."""
from urllib.parse import urlsplit
from .common import PipelineError

def compose(script,claims,record=None):
 from .source_urls import official_url,https_url
 if record and record.get('source_url'):official_url(record['source_url'],record)
 if script.get('publication_text_review_required') is True:raise PipelineError('Manual description and CTA require factual/link review; original description cannot be reused as current publication text')
 by={c['key']:c for c in claims};paragraphs=[];links=[];example_links=[]
 if script.get('description_detail_policy')=='all_active_fact_claims_v1':
  present=[d.get('claim_key') for d in script.get('description_details',[])]
  if set(present)!=set(by) or len(present)!=len(by):raise PipelineError('All active accepted facts must remain in this description')
 if script.get('description_detail_policy')=='all_primary_claims_v1':
  required={k for k in by if k.startswith('primary_')};present=[d.get('claim_key') for d in script.get('description_details',[])]
  if not required or set(present)!=required or len(present)!=len(required):raise PipelineError('Complete source-bound primary conditions must remain in this description')
 if script.get('description_detail_policy') in {'all_scoped_track_claims_v1','all_scoped_track_and_purpose_claims_v2'}:
  required={k for k in by if k.startswith(('track_','tracks_','dependency_')) or k=='source_review_status' or k=='purpose_quote' and script.get('description_detail_policy')=='all_scoped_track_and_purpose_claims_v2'};present=[d.get('claim_key') for d in script.get('description_details',[])]
  if not required or set(present)!=required or len(present)!=len(required):raise PipelineError('Track-specific and linked-policy conditions must remain in this description')
 intro=script.get('description')
 if script.get('editorial_contract')=='SOCIAL_BENEFIT_REEL_V1':
  expected='\n'.join(d['text'] for d in script.get('description_details') or [])
  if intro!=expected:raise PipelineError('Description intro differs from this version of the source-bound description claims')
  intro=expected
 if intro:paragraphs.append(intro.strip())
 for detail in script.get('description_details') or []:
  c=by.get(detail.get('claim_key'))
  if not c or detail.get('text')!=c.get('statement') or detail.get('source')!=c.get('source'):raise PipelineError('Description detail differs from its bound claim')
  text=detail['text'].strip()
  if text and not any(text in p for p in paragraphs):paragraphs.append(text)
  for example in (c.get('source') or {}).get('example_sources',[]):
   for route in example.get('links',[]):
    url=route.get('url');parts=https_url(url)
    if parts.scheme!='https' or not (parts.hostname or '').endswith('.gov'):raise PipelineError('Example route is not an evidenced HTTPS government link')
    item=(example.get('agency') or example.get('category') or 'Official route',url)
    if item not in example_links:example_links.append(item)
  sources=[c.get('source') or {}]+list((c.get('source') or {}).get('supporting_sources') or [])
  for src in sources:
   url=src.get('url')
   if url and url not in links:
    parts=urlsplit(url)
    official_url(url)
    links.append(url)
 if record and record.get('source_url') and record['source_url'] not in links:
  url=record['source_url'];parts=urlsplit(url)
  official_url(url,record)
  links.insert(0,url)
 if links:paragraphs.append('Sources:\n'+'\n'.join(links))
 if example_links:paragraphs.append('Official example routes:\n'+'\n'.join(label+': '+url for label,url in example_links))
 directories=(record or {}).get('public_money_source',{}).get('state_directories',[])
 for directory in directories:
  url=directory.get('url','');parts=https_url(url)
  if parts.scheme=='https' and parts.hostname in {'unclaimed.org','www.unclaimed.org'} and directory.get('government_domain') is False:paragraphs.append('State directory (external, not a government domain): '+url)
 if script.get('synthetic'):paragraphs.insert(0,'SYNTHETIC TEST ONLY — NOT A REAL PROGRAM. DO NOT PUBLISH.')
 elif (record or {}).get('editorial_brief',{}).get('reconstructed_source'):paragraphs.append('Draft based on supplied research and a reconstructed parser fixture. No authentic live ingest or voice verification is implied.')
 return '\n\n'.join(paragraphs).strip()


def fact_version(claims):
 from .common import stable_json,sha256_bytes
 from .editorial_brief import factual_claim_payload
 return sha256_bytes(stable_json([factual_claim_payload(c) for c in claims]).encode('utf-8'))

def automatic_manual_description(base,current,claims,record):
 # Equality here detects whether saved wording was modified; it is not new source verification.
 # Original inputs/ledger have already been hash-verified by the caller.
 changed=[];blocked=set()
 for old,new in zip(base['segments'],current['segments']):
  if old['voiceover']!=new['voiceover']:
   keys=old.get('claim_keys',[]);blocked.update(keys)
   changed.append({'scene_id':new['id'],'claim_keys':keys,'status':'unverified_user_edit','original_wording_reference':old['voiceover'],'current_wording':new['voiceover']})
 by={c['key']:c for c in claims};details=[]
 for d in base.get('description_details') or []:
  c=by.get(d['claim_key'])
  if not c or d['text']!=c.get('statement') or d['source']!=c.get('source'):raise PipelineError('Original description detail is not bound to saved fact version')
  if d['claim_key'] not in blocked:details.append(d)
 candidate={'editorial_contract':base.get('editorial_contract'),'description':'\n'.join(d['text'] for d in details),'description_details':details,'synthetic':base.get('synthetic',False)}
 text=compose(candidate,claims,record)
 substantive=[c for c in changed if next((s.get('role') for s in base['segments'] if s['id']==c['scene_id']),None)!='cta']
 return {'fact_version':fact_version(claims),'automatic_description':text,'included_claim_keys':[d['claim_key'] for d in details],'conflicts':changed,'excluded_claim_keys':sorted(blocked),'scope':'Automatically composed from unchanged hash-bound saved facts; currentness not rechecked; no confirmation of edited facts','money_metadata':{'state':'requires_review_due_to_edited_facts' if substantive else 'unchanged_saved_fact_lineage','value':None if substantive else base.get('money_benefit'),'original_reference':base.get('money_benefit') if substantive else None},'cta_review_required':bool(changed),'ready_for_publication':False}

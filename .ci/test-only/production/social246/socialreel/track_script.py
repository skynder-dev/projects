"""Track-scoped claim and script projection of a source-span ledger."""
from .common import money,human_date,parse_date

def claims(data):
 out=[];all_ids=list(data['tracks']);meta=data['source']
 def add(key,statement,field,ids,values=None):
  if field.get('state')!='known':return
  out.append({'key':key,'statement':statement,'values':{'track_ids':ids,'track_names':{k:v['name'] for k,v in data['tracks'].items()},**(values or {})},'source':{'url':meta.get('final_url') or meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Track-scoped primary document'],'source_spans':field['evidence']+[e for id in ids for e in data['tracks'][id]['declaration'].get('evidence',[])],'normalized_text_sha256':data['normalized_text_sha256']}})
 for id,t in data['tracks'].items():
  suffix=id.rsplit('-',1)[1];b=t['budget']
  if b['state']=='known':
   qualifier='approximately (estimated award size)' if b['amount_kind']=='approximate_award_estimate' else 'maximum per award'
   add('track_'+suffix+'_budget',id+': '+money(b['amount_usd'])+' '+qualifier+', duration up to '+str(b['duration_max_months'])+' months.',b,[id],{k:b[k] for k in ['amount_usd','amount_kind','duration_max_months']})
  for fieldname in ['eligibility','submission','partner_personnel']:
   f=t.get(fieldname)
   if f:add('track_'+suffix+'_'+fieldname,' '.join(dict.fromkeys(e['quote'] for e in f['evidence'])),f,[id])
  schedule=t.get('schedule')
  if schedule and schedule['state']=='known':
   if suffix=='E':statement=id+': Proposals may be submitted anytime.'
   else:statement=id+': '+schedule['groups'][2]+' '+schedule['groups'][3]+' in '+' and '.join(schedule['recurrence']['months'])+' annually; '+schedule['time']+' '+schedule['timezone_basis']+'. Next date as of '+schedule['as_of']+': '+human_date(parse_date(schedule['next_date']))+'.'
   evidence={**schedule,'evidence':schedule['evidence']+(t.get('submission') or {}).get('evidence',[])}
   add('track_'+suffix+'_schedule',statement,evidence,[id],{k:v for k,v in schedule.items() if k not in ['evidence','groups','state']})
 for key,f in data['shared'].items():
  ids=[id for id in all_ids if id[-1] in 'TP'] if key.startswith('TP_') else all_ids
  add('tracks_'+key,' '.join(dict.fromkeys(e['quote'] for e in f['evidence'])),f,ids,{'training_budget_usd':int(f['groups'][0].replace(',',''))} if key=='TP_training_budget' and f['state']=='known' else None)
 return out

def script(rec,ledger):
 data=rec['track_conditions'];by={c['key']:c for c in ledger};prefix=data['prefix'];all_ids=[prefix+'-'+letter for letter in 'ETP'];segs=[]
 def add(role,voice,keys,headline,ids=all_ids,sub=''):
  keys=[k for k in keys if k in by]
  if not keys:keys=['identity','source_review_status']
  segs.append({'id':'s'+str(len(segs)+1),'role':role,'visual':'quote','voiceover':voice,'on_screen':{'kicker':'TRACK-SPECIFIC SOURCE FACTS','headline':headline,'sub':sub},'claim_keys':keys,'track_ids':ids})
 add('hook','This program has distinct tracks, subject to funding availability.'+(' Tracks are not prerequisites.' if 'tracks_track_order' in by else '') if 'tracks_availability' in by else 'This program has distinct tracks; funding availability needs review.',['identity','tracks_availability','tracks_track_order'],rec['title'])
 lead_known=all(k in by for k in ['tracks_lead_organizations','tracks_PI_appointments'])
 add('who',('Listed lead types include specified U.S. colleges and non-academic research/education nonprofits. PIs need stated appointments.') if lead_known else 'Lead-applicant or PI requirements remain unconfirmed.',['tracks_lead_organizations','tracks_PI_appointments'],'U.S. higher education; research/education nonprofits' if lead_known else 'Lead/PI eligibility UNKNOWN',sub='Tenure/tenure-track OR full-time paid research/teaching appointment; stated exceptions' if lead_known else 'Full primary conditions need review')
 for letter in 'ETP':
  id=prefix+'-'+letter;t=data['tracks'][id];b=t['budget'];keys=['track_'+letter+'_budget'];voice=t['name']+': funding remains unconfirmed.';screen='Funding: unknown'
  if b['state']=='known':
   amount=money(b['amount_usd']);qual='approximately ' if b['amount_kind']=='approximate_award_estimate' else 'up to '
   voice=t['name']+': '+qual+amount+', up to '+str(b['duration_max_months'])+' months.';screen=qual+amount+' / up to '+str(b['duration_max_months'])+' months'
  if b['state']!='known':keys.append('source_review_status')
  if letter=='E':
   if all(k in by for k in ['track_E_eligibility','track_E_submission']):
    voice+=' Eligible active NSF award, prior Program Officer approval and invitation required.';keys+=['track_E_eligibility','track_E_submission'];detail=t['eligibility']['details'];screen+='\nShould have at least '+str(detail['remaining_award_years_min'])+' year left and '+str(detail['approved_annual_reports_range'][0])+'-'+str(detail['approved_annual_reports_range'][1])+' approved annual reports. Excluded: '+', '.join(detail['excluded_award_types'])+'. Request: '+str(detail['description_pages_range'][0])+'-'+str(detail['description_pages_range'][1])+' pages; prior email approval.'
   else:voice+=' Eligibility or approval conditions remain unconfirmed.';keys+=['source_review_status'];screen+='\nEligibility/approval UNKNOWN'
  elif letter=='T':
   if 'tracks_TP_prior_funding' in by:voice+=' Prior federal funding is not required.';keys+=['tracks_TP_prior_funding']
   if 'tracks_partnership_optional_required' in by:voice+=' Partnerships are optional.';keys+=['tracks_partnership_optional_required']
  else:
   if 'track_P_partner_personnel' in by:voice+=' Partner-affiliated co-PI or senior/key personnel required.';keys+=['track_P_partner_personnel']
   else:voice+=' Partner-personnel conditions remain unconfirmed.';keys+=['source_review_status']
   if 'tracks_TP_prior_funding' in by:voice+=' Prior federal funding is not required.';keys+=['tracks_TP_prior_funding']
  if not keys or keys==['track_'+letter+'_budget'] and keys[0] not in by:keys=['identity','source_review_status']
  add('track_'+letter,voice,keys,screen,[id])
 add('when_E','Explore submissions: anytime, after required Program Officer approval.' if all(k in by for k in ['track_E_schedule','track_E_submission']) else 'Explore submission timing or approval conditions remain unconfirmed.',['track_E_schedule','track_E_submission'],'Explore: anytime is not an automatic invitation' if all(k in by for k in ['track_E_schedule','track_E_submission']) else 'Explore submission UNKNOWN',[prefix+'-E'])
 schedule=data['tracks'][prefix+'-T']['schedule'];voice='Translate and Partner timing remains unconfirmed.';headline='T/P schedule unknown'
 if schedule['state']=='known':
  voice='Translate and Partner: '+schedule['recurrence']['ordinal'].lower()+' '+schedule['recurrence']['weekday']+'s of '+' and '.join(schedule['recurrence']['months'])+', '+str(schedule['clock_hour_12'])+' p.m. submitting-organization local time. Snapshot-next: '+human_date(parse_date(schedule['next_date']))+'.';headline='T/P: '+human_date(parse_date(schedule['next_date']))+' · '+schedule['time']+' submitting-organization local time'
 add('when_TP',voice,['track_T_schedule','track_P_schedule'],headline,[prefix+'-T',prefix+'-P'])
 training=data['shared']['TP_training_budget'];training_amount=money(int(training['groups'][0].replace(',',''))) if training['state']=='known' else None
 add('training',('Translate and Partner require I-Corps; stated waivers may apply. Normally budget '+training_amount+'. Voluntary committed cost sharing is prohibited.') if training_amount and data['shared']['TP_training']['state']=='known' and data['shared']['cost_sharing']['state']=='known' else 'Training, budget allocation or cost-sharing conditions remain unconfirmed.',['tracks_TP_training','tracks_TP_training_budget','tracks_cost_sharing'],'Training allocation: '+str(training_amount or 'unknown')+'; waiver conditions apply',[prefix+'-T',prefix+'-P'])
 add('limits','One proposal per PI or co-PI at a time; await determination. A single institution submits.' if all(k in by for k in ['tracks_proposal_limit','tracks_single_institution']) else 'Proposal limits or organization-submission conditions remain unconfirmed.',['tracks_proposal_limit','tracks_single_institution'],'One at a time across tracks; linked separate submissions returned without review' if all(k in by for k in ['tracks_proposal_limit','tracks_single_institution']) else 'Submission limits UNKNOWN')
 add('cta','Review complete conditions and linked policies. This is not an eligibility decision. Verify the official listing before applying.',['identity','source_review_status'],'grants.gov · '+str(rec['number']),sub='Remaining linked-policy/DCL conditions unknown; no approval')
 if rec.get('source_dependencies') and data.get('dependency_review',{}).get('overview_source_review_complete'):
  cta=segs[-1];cta.update(voiceover='Follow proposal guides, security certifications and data-sharing requirements. Partner DCL terms may apply. Check the official listing on Grants.gov; eligibility is unassessed.',claim_keys=['identity','dependency_base_version','dependency_version_rule','dependency_security','dependency_dmsp','dependency_direct_partners','source_review_status']);cta['on_screen']['sub']='PAPPG 24-1 plus applicable supplements; snapshot review, no individual approval'
  segs[1]['on_screen']['sub']+='; medical research, including clinical trials, is not responsive'
  segs[1]['claim_keys'].append('dependency_medical_scope')
 details=[{'claim_key':c['key'],'text':c['statement'],'source':c['source']} for c in ledger if c['key'].startswith(('track_','tracks_','dependency_')) or c['key']=='source_review_status']
 complete_description='\n\n'.join(s['voiceover'] for s in segs)+'\n\nFull source-bound track and policy conditions:\n'+'\n\n'.join(d['text'] for d in details)
 return {'writer':'template_tracks_v2','description_detail_policy':'all_scoped_track_claims_v1','description_details':details,'title':rec['title']+' — track-specific draft','segments':segs,'description':complete_description,'source_note':('Pinned primary and linked-policy snapshots verified for neutral overview; recheck versions and DCLs before actual submission. Individual eligibility is unassessed.' if rec.get('source_dependencies') else 'Pinned official source; track facts are distinct. Linked policies/individual eligibility remain unconfirmed.'),'track_schema':data['schema']}

def validate_scopes(script,ledger):
 import re
 errors=[];by={c['key']:c for c in ledger};aliases={}
 for claim in ledger:aliases.update((claim.get('values') or {}).get('track_names') or {})
 for i,segment in enumerate(script.get('segments') or []):
  ids=set(segment.get('track_ids') or []);cited=[by[k] for k in segment.get('claim_keys',[]) if k in by];scoped=[c for c in cited if c.get('values',{}).get('track_ids')]
  if not scoped:continue
  if not ids:errors.append('segment '+str(i+1)+': track identity missing');continue
  text=segment.get('voiceover','')+' '+' '.join(str(v) for v in (segment.get('on_screen') or {}).values())
  schedule_union=set(x for c in scoped if c['key'].endswith('_schedule') for x in c['values']['track_ids'])
  schedule_kinds={c['values'].get('kind') for c in scoped if c['key'].endswith('_schedule')}
  if len(schedule_kinds)>1:errors.append('segment '+str(i+1)+': anytime and deadline tracks must remain separate')
  for c in scoped:
   scope=set(c['values']['track_ids'])
   if c['key'].endswith('_schedule'):
    if ids!=schedule_union:errors.append('segment '+str(i+1)+': schedule belongs to a different track')
   elif not ids.issubset(scope):errors.append('segment '+str(i+1)+': '+c['key']+' crosses track scope')
   values=c['values']
   if c['key'].endswith('_budget') and 'amount_kind' in values:
    if len(ids)!=1:errors.append('segment '+str(i+1)+': per-track budgets must remain separate')
    if re.search(r'\b(?:per year|annually|annual (?:budget|award|limit))\b',text,re.I):errors.append('segment '+str(i+1)+': per-award limit converted to annual amount')
    if values['amount_kind']=='approximate_award_estimate':
     if re.search(r'\b(?:up to|cap|maximum)\s+(?:approximately\s+)?\$',text,re.I):errors.append('segment '+str(i+1)+': estimate converted to cap')
     if '$' in segment.get('voiceover','') and not re.search(r'approx|estimat',segment['voiceover'],re.I):errors.append('segment '+str(i+1)+': spoken estimate qualifier missing')
   if c['key'].endswith('_schedule') and values.get('timezone_basis'):
    if re.search(r'\b(?:UTC|Eastern|Pacific|ET)\b',text,re.I):errors.append('segment '+str(i+1)+': organization-local deadline converted to unsupported zone')
    if not re.search(r'local time',text,re.I):errors.append('segment '+str(i+1)+': deadline timezone basis missing')
  for id,name in aliases.items():
   if re.search(r'\b(?:'+re.escape(id)+'|'+re.escape(id.replace('NSF ',''))+'|'+re.escape(name)+r')\b',text,re.I) and id not in ids:errors.append('segment '+str(i+1)+': named track differs from declared scope')
 return errors

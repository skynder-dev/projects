"""Offline evidence/field diagnostics. Model statements never become approvals."""
import hashlib,json,re
from .narrative_checks import guarantee_mentions,screen_field

def stable(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(stable(value).encode()).hexdigest()
def source_index(claims):
 out={}
 for claim in claims:
  key=claim['key'];source=claim.get('source') or {}
  for origin,text in [('statement',claim.get('statement','')),('source_quote',claim.get('source_quote') or source.get('quote',''))]:
   if isinstance(text,str) and text:
    id=key+':'+origin+':'+hashlib.sha256(text.encode()).hexdigest()[:16]
    out[id]={'claim_key':key,'origin':origin,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'scope':'saved statement/excerpt, not fresh source or owner approval'}
 return out

def matching_state(text):
 """Finite operator patterns, no general NLP. Preserve negation; unknown stays unknown."""
 t=re.sub(r'\s+',' ',text.casefold().replace('-',' '));subject=r'(?:matching(?: funds| contributions)?|cost shar(?:e|ing)(?: funds| contributions)?)'
 permissive=bool(re.search(subject+r' (?:is |are |will be )?(?:allowed|permitted|accepted|optional)\b',t) or re.search(subject+r' (?:is |are )?not (?:prohibited|forbidden)\b',t))
 prohibition=bool(re.search(subject+r' (?:is |are |will |shall )?(?:be )?(?:not (?:be )?(?:accepted|allowed|permitted|included)|never accepted|prohibited|forbidden)\b',t))
 prohibition|=bool(re.search(r'\b(?:do not|must not|cannot|may not) include (?:any |voluntary )?'+subject,t))
 notrequired=bool(re.search(r'\bno '+subject+r' (?:is |are )?required\b|'+subject+r' (?:is |are )?not required\b',t))
 if permissive and prohibition:return 'conflicting'
 if permissive:return 'permitted'
 if prohibition:return 'conditional_prohibition' if re.search(r'\b(?:if|unless|only|except)\b',t) else 'prohibited'
 if notrequired:return 'not_required_only'
 return 'unclassified'

def prohibited_source(claims):
 return any(c.get('values',{}).get('cost_sharing_mode')=='prohibited' or c.get('key')=='primary_cost_share' and 'not be accepted if voluntarily offered' in c.get('statement','').lower() for c in claims)

def fields(draft,description):
 out={'voice':draft.get('voice',''),'description':description}
 for i,s in enumerate(draft.get('screens',[])):out['screen:'+str(i)]=s
 return out

def finite_findings(text,field,claims):
 """Review findings grounded in observed regressions, not a complete truth checker."""
 findings=[];keys={c['key'] for c in claims};t=text.lower()
 def add(kind,claim_keys,classification):findings.append({'field':field,'quote':text,'kind':kind,'claim_keys':claim_keys,'classification':classification})
 if prohibited_source(claims):
  state=matching_state(text)
  if state=='not_required_only':add('matching_prohibition_weakened',['primary_cost_share','primary_share_exclusion'],'material_actionable_weakening')
  if state in {'permitted','conflicting'}:add('matching_operator_conflict',['primary_cost_share'],'source_operator_conflict')
  if state=='conditional_prohibition':add('matching_condition_review',['primary_cost_share'],'contextual_scope_review')
  if re.search(r'\bmoney waiting\b',t):add('grant_to_owed_money',['primary_budget','primary_applicant'],'benefit_mechanism_conflict')
  if re.search(r'\bevery tribal member\b|\beach year\b|\bannually\b',t):add('recipient_or_recurrence_review',['primary_budget','primary_applicant'],'scope_review_required')
 if 'individual_unknown' in keys:
  guarantees=[m for m in guarantee_mentions(text) if m['state']!='negated']
  if guarantees:add('certainty_escalation',['individual_unknown'],'unsupported_certainty')
  if re.search(r'[$£€]\s*\d',text):add('unestablished_personal_amount',['individual_unknown'],'unsupported_amount_review')
 return findings

def inspect_screen(voice,screen,claims,spoken_quote=None):
 if not isinstance(voice,str) or not isinstance(screen,str) or len(voice)>4000 or len(screen)>1000:
  return {'correspondence':'requires_semantic_review','integrity_error':'Screen/voice type or diagnostic size bound','findings':[],'approved':False,'source_entailment_verified':False}
 value={'screen':screen,'voice_sha256':hashlib.sha256(voice.encode()).hexdigest(),'screen_sha256':hashlib.sha256(screen.encode()).hexdigest(),'source_digest':digest(claims),'correspondence':'requires_semantic_review','findings':finite_findings(screen,'screen',claims),'format':{'words':len(screen.split()),'legacy9word_fit':len(screen.split())<=9},'source_entailment_verified':False,'approved':False}
 visible=screen_field(screen);value['visible_text']=visible
 if not visible['preparation_valid']:
  value['integrity_error']='Visible wording/staging separation requires review';return value
 if spoken_quote is not None:
  if not isinstance(spoken_quote,str) or not spoken_quote or voice.count(spoken_quote)!=1:
   value['integrity_error']='Spoken reference absent/ambiguous; cannot inherit prior screen proof';return value
  value['spoken_quote']=spoken_quote
 try:
  from .screen_relation import bind
  allow=any(c['key']=='insurance_scope' and 'FHA' in c.get('statement','') for c in claims)
  proof=bind(voice,screen,allow_fha_short=allow)
  if spoken_quote is not None:
   start=voice.index(spoken_quote);end=start+len(spoken_quote);ref=proof['spoken_reference']
   if not start<=ref['start_char']<ref['end_char']<=end:raise ValueError('Screen evidence outside declared spoken reference')
  if not value['findings']:value.update(correspondence='conservative_correspondence',proof=proof)
 except (ValueError,TypeError,RuntimeError) as error:value['relation_note']=str(error)
 # Scope loss is a context question, never silently normalized into a proven label.
 if re.search(r'\bunclaimed pensions?\b',voice,re.I) and re.search(r'\bpensions?\b',screen,re.I) and not re.search(r'\bunclaimed\b',screen,re.I):
  value['findings'].append({'field':'screen','kind':'pension_qualifier_context_review','classification':'contextual_scope_review','quote':screen});value['correspondence']='requires_semantic_review'
 return value

def script_alignment(script,claims):
 rows=[]
 for seg in script.get('segments',[]):
  screens=seg.get('on_screen') or {};row={'scene_id':seg.get('id'),'fields':{}}
  for key in ['kicker','big','headline','sub']:
   text=screens.get(key,'')
   if text:row['fields'][key]=inspect_screen(seg.get('voiceover',''),text,claims)
  if not row['fields']:row['missing_screen']=True
  rows.append(row)
 return {'schema':'SOCIAL_ALL_SCENE_SCREEN_AUDIT218','scenes':rows,'screen_fields_examined':sum(len(x['fields']) for x in rows),'source_entailment_verified':False,'approved':False,'publication_authorized':False}

def audience_action_role(text):
 if not isinstance(text,str) or not text.strip() or re.match(r'(?i)^(?:none(?: required)?|no (?:changes?|edits?) (?:needed|required))\b',text.strip()):return 'missing'
 if re.match(r'(?i)^(?:delete|remove|re-add|restore|revise|rewrite|replace|shorten|edit|correct|rephrase)\b',text.strip()) and re.search(r'(?i)\b(?:claim|qualifiers?|script|voice|screen|draft|wording|phrase|text)\b',text):return 'editorial_advice'
 return 'viewer_action_candidate_requires_review'

def audit_critic(case,drafts,report):
 """Accumulate independently inspectable defects, preserving raw useful findings."""
 by={d['draft_id']:d for d in drafts};claims=case['claims'];index=source_index(claims);validkeys={c['key'] for c in claims};rows=[];seen=set();global_errors=[]
 modelrows=report.get('drafts',[]) if isinstance(report,dict) else []
 if not isinstance(modelrows,list):modelrows=[];global_errors.append('drafts is not an array')
 if len(modelrows)>32:global_errors.append('Draft diagnostic bound exceeded; remainder not examined');modelrows=modelrows[:32]
 for item in modelrows:
  if not isinstance(item,dict):global_errors.append('Non-object draft row');continue
  id=item.get('draft_id');errors=[]
  if not isinstance(id,str) or id not in by or id in seen:global_errors.append('Unknown/duplicate draft:'+str(id));continue
  seen.add(id);draft=by[id];allfields=fields(draft,case['description']);independent=[]
  for field,text in allfields.items():
   if field!='description':independent.extend(finite_findings(text,field,claims))
  issue_rows=[];derived_material=False
  if not isinstance(item.get('issues'),list):errors.append('issues is not an array')
  issues=item.get('issues',[]) if isinstance(item.get('issues',[]),list) else []
  if len(issues)>32:errors.append('Issue diagnostic bound exceeded; remainder not examined');issues=issues[:32]
  for issue in issues:
   if not isinstance(issue,dict):errors.append('Non-object issue');continue
   bound=[];f=issue.get('field');quote=issue.get('quote');issuekeys=issue.get('claim_keys',[])
   targets=[allfields[f]] if isinstance(f,str) and f in allfields else [v for k,v in allfields.items() if k.startswith('screen:')] if f=='screen' else []
   if not isinstance(quote,str) or not quote or not any(quote in t for t in targets):bound.append('Quote absent from named field')
   if not isinstance(issuekeys,list) or not issuekeys or any(not isinstance(k,str) or k not in validkeys for k in issuekeys):bound.append('Unknown/missing claim binding');issuekeys=[]
   refs=issue.get('source_refs')
   if refs is None:
    q=issue.get('source_quote');matches=[v for v in index.values() if v['claim_key'] in issuekeys and isinstance(q,str) and q and q in v['text']]
    if not matches:bound.append('Legacy source_quote is not one exact bound excerpt; composite/ellipsis quotes are not repaired silently')
   elif not isinstance(refs,list) or not refs:bound.append('Missing source_refs')
   else:
    if len(refs)>8:bound.append('Source reference bound exceeded')
    for ref in refs[:8]:
     proof=index.get(ref.get('evidence_id')) if isinstance(ref,dict) and isinstance(ref.get('evidence_id'),str) else None
     if not proof or proof['claim_key'] not in issuekeys or not isinstance(ref.get('quote'),str) or not ref['quote'] or ref['quote'] not in proof['text']:bound.append('Invalid source reference')
   kind=issue.get('kind')
   if not isinstance(kind,str):bound.append('Invalid issue kind');kind='invalid'
   if kind not in {'unsupported','contradiction','material_weakening','uncertain'}:bound.append('Unknown issue kind')
   derived_material|=kind in {'unsupported','contradiction','material_weakening'}
   countercheck=None
   if prohibited_source(claims) and isinstance(f,str) and (f=='voice' or f.startswith('screen')) and isinstance(quote,str) and matching_state(quote)=='prohibited' and 'voluntar' in str(issue.get('reason','')).lower():countercheck='Explicit prohibition includes voluntary matching; missing literal voluntary word is not by itself weakening. Review model criticism, not automatic source approval.'
   issue_rows.append({'raw_issue':issue,'binding_errors':bound,'binding_valid':not bound,'countercheck':countercheck})
  if 'material_error' in item and (type(item['material_error']) is not bool or item['material_error']!=derived_material):errors.append('Material boolean inconsistent with issue kinds; uncertain alone never material approval/error')
  fieldreviews=item.get('field_reviews')
  if isinstance(fieldreviews,list):
   reviewed=[x.get('field_id') for x in fieldreviews if isinstance(x,dict) and isinstance(x.get('field_id'),str)]
   if set(reviewed)!=set(allfields) or len(reviewed)!=len(set(reviewed)) or len(reviewed)!=len(fieldreviews):errors.append('Exact field coverage incomplete/duplicated')
   for check in fieldreviews:
    if not isinstance(check,dict) or not isinstance(check.get('status'),str) or check['status'] not in {'checked_no_issue','issue','uncertain'} or not isinstance(check.get('reason'),str) or not check['reason']:errors.append('Invalid field review');continue
    mentioned=any(x['raw_issue'].get('field')==check.get('field_id') for x in issue_rows)
    if check['status']=='issue' and not mentioned:errors.append('Field issue status lacks a bound finding')
    if check['status']=='checked_no_issue' and mentioned:errors.append('Field no-issue status conflicts with finding')
  else:errors.append('Field-level coverage unrecorded; legacy boundary IDs are not proof each screen was checked')
  audience_action=item.get('audience_next_action')
  role=audience_action_role(audience_action)
  if role=='missing':errors.append('Concrete audience next action absent; edit recommendation is not viewer utility')
  if role=='editorial_advice':errors.append('Audience next action is script-editing advice, not viewer utility')
  rows.append({'draft_id':id,'raw_material_error':item.get('material_error'),'derived_material_error':derived_material,'classification_scope':'Derived from model issue categories only, not backend proof of factual error','protocol_errors':errors,'issues':issue_rows,'independent_findings':independent,'model_advice_preserved':True,'audience_action_role':role,'creative_review':{'state':'model_comment_only_requires_owner_review','story_comment':item.get('story_weakness') or ((item.get('editorial') or {}).get('problem') if isinstance(item.get('editorial') or {},dict) else None),'creative_quality_verified':False,'engagement_measured':False},'semantic_accuracy_verified':False,'approved':False})
 missing=sorted(set(by)-seen)
 if missing:global_errors.append('Missing drafts:'+','.join(missing))
 return {'schema':'SOCIAL_PARTIAL_REVIEW_AUDIT218','drafts':rows,'errors':global_errors,'raw_report_digest':digest(report),'source_digest':digest(claims),'description_digest':digest(case['description']),'structural_errors_are_not_fact_errors':True,'semantic_accuracy_verified':False,'production_ready':False,'publication_authorized':False}

"""Evidence-bound editorial brief to deterministic conversational source package.

Only locally reviewed plain-language claims are accepted. External source text is
data, never an instruction. Synthetic fixtures cannot be production material.
"""
import hashlib,re
from .common import PipelineError

SCHEMA='SOCIAL_EDITORIAL_BRIEF_V1'
ROLES=('money_hook','use_case','advantage','key_caveat','cta')
UNCLAIMED_ROLES=('money_hook','concrete_examples','guide','one_action','cta')
def roles_for(brief):
 if brief.get('money_benefit',{}).get('kind')=='return_of_recovered_wages':return ('money_hook','recovered_funds','one_action','holding_period','cta')
 if brief.get('money_benefit',{}).get('kind')=='energy_assistance_information':return ('money_hook','use_case','key_caveat','one_action','cta')
 return UNCLAIMED_ROLES if brief.get('money_benefit',{}).get('kind')=='return_of_owned_money' else ROLES

def factual_claim_payload(claim):
 return {k:v for k,v in claim.items() if k not in {'observed_at','materialized_at'}}

def inspect(rec,audience):
 b=rec.get('editorial_brief') or {};errors=[]
 if b.get('live_verified') is True and (b.get('synthetic') or b.get('reconstructed_source')):errors.append('Synthetic/reconstructed source cannot be promoted to live verification')
 if b.get('schema')!=SCHEMA:errors.append('Missing reviewed editorial brief')
 category=b.get('category');expected={'general_us':'personal_money','small_business':'small_business','institutional':'institutional'}.get(audience)
 if category!=expected:errors.append('Audience/category mismatch')
 if not b.get('audience_description') or not b.get('concrete_use'):errors.append('Audience and concrete use required')
 benefit=b.get('money_benefit') or {}
 if benefit.get('kind') not in ('bill_support','reimbursement','project_funding','cost_reduction','return_of_owned_money','energy_assistance_information','return_of_recovered_wages') or benefit.get('scope') not in ('per_household','per_business','per_project','individual_balance','local_program_determined') or not benefit.get('limit_claim_key'):errors.append('Money benefit kind, recipient scope and limit evidence required')
 if b.get('review',{}).get('scope')!='facts_and_plain_language_entailment' or not b.get('review',{}).get('reviewer'):errors.append('Local factual/paraphrase review required')
 claims=b.get('claims') or [];by={c.get('key'):c for c in claims}
 if len(by)!=len(claims):errors.append('Duplicate claim keys')
 if benefit.get('limit_claim_key') not in by:errors.append('Money limit lacks evidence')
 facts=b.get('main_facts') or {}
 if set(facts)!=set(roles_for(b)):errors.append('Five main fact roles required')
 for role,key in facts.items():
  c=by.get(key,{})
  text=c.get('statement','');source=c.get('source') or {};quote=source.get('quote','');excerpt=source.get('excerpt','')
  if not text or len(text.split())>14:errors.append(role+': short complete reviewed sentence required')
  if not quote or quote not in excerpt or source.get('excerpt_sha256')!=hashlib.sha256(excerpt.encode()).hexdigest():errors.append(role+': source quote/hash mismatch')
  if not source.get('url') or not source.get('locator'):errors.append(role+': source URL/location required')
  if c.get('reviewed_statement_sha256')!=hashlib.sha256(text.encode()).hexdigest():errors.append(role+': edited statement needs renewed review')
  if re.search(r'ignore .*instructions|system prompt|\b(?:NOFO|PAPPG|SAM|UEI)\b',text,re.I):errors.append(role+': prompt/administrative jargon is not narration')
  accent=c.get('accent','')
  if not accent or accent not in text or len(accent.split())>9:errors.append(role+': same-line short accent required')
 if not b.get('description_claim_keys') or any(k not in by for k in b.get('description_claim_keys',[])):errors.append('Full conditions must remain in description')
 for c in claims:
  text=c.get('statement','');source=c.get('source') or {};excerpt=source.get('excerpt','');quote=source.get('quote','')
  if not quote or quote not in excerpt or source.get('excerpt_sha256')!=hashlib.sha256(excerpt.encode()).hexdigest() or not source.get('url') or not source.get('locator'):errors.append('Description/source evidence incomplete: '+str(c.get('key')))
  if b.get('live_verified') is True and source.get('reconstructed') is True:errors.append('Reconstructed claim evidence cannot support a live source')
  if c.get('reviewed_statement_sha256')!=hashlib.sha256(text.encode()).hexdigest():errors.append('Description statement changed after review: '+str(c.get('key')))
  if c.get('must_disclose') and c.get('key') not in b.get('description_claim_keys',[]):errors.append('Required condition omitted: '+c['key'])
 if benefit.get('kind')=='return_of_owned_money':
  example=by.get(facts.get('concrete_examples'),{})
  if len(example.get('source',{}).get('example_sources',[]))<2:errors.append('Unclaimed-money story needs at least two evidenced money types; no generic filler fallback')
 if b.get('synthetic') is not True:
  # This local marker cannot be populated by a model or publisher HTML. A source
  # adapter must bind its own reviewed profile and source hash before admission.
  if rec.get('_local_reviewed_brief_sha256')!=hashlib.sha256(__import__('json').dumps(b,sort_keys=True).encode()).hexdigest():errors.append('Real brief lacks local reviewed-source binding')
 return {'suitable':not errors,'errors':errors,'category':category,'synthetic':b.get('synthetic') is True,'source_evidence_ready':not errors and not b.get('synthetic') and not b.get('reconstructed_source') and b.get('live_verified') is True,'production_allowed':False,'individual_eligibility_assessed':False,'publication_authorized':False,'scope':'Topic relevance and source evidence only; runtime authorization, audition and release review are separate'}

def make(rec,claims,audience):
 verdict=inspect(rec,audience)
 if not verdict['suitable']:raise PipelineError('Editorial brief: '+'; '.join(verdict['errors']))
 if [factual_claim_payload(c) for c in claims]!=[factual_claim_payload(c) for c in rec['editorial_brief']['claims']]:raise PipelineError('Claim ledger differs from reviewed editorial brief')
 b=rec['editorial_brief'];by={c['key']:c for c in claims};segments=[]
 for i,role in enumerate(roles_for(b),1):
  key=b['main_facts'][role];c=by[key];text=c['statement'];accent=c['accent'];start=text.index(accent)
  segments.append({'id':'s'+str(i),'role':role,'visual':'quote','voiceover':text,'claim_keys':[key],
   'on_screen':{'kicker':'','headline':accent,'sub':''},'screen_anchor':{'start_char':start,'end_char':start+len(accent),'text':accent},
   'delivery':{'tone':'curious question' if role=='money_hook' else 'conversational','semantic_stress':accent,'notes_are_direction_not_engine_emotion_control':True}})
 details=[{'claim_key':k,'text':by[k]['statement'],'source':by[k]['source']} for k in b['description_claim_keys']]
 from .voice import speech_text
 from .subtitles import normalized_words
 from .duration_profile import PROFILE
 words=sum(len(normalized_words(speech_text(s['voiceover']))) for s in segments)
 upper=words/PROFILE['conservative_unknown_words_per_second']+len(segments)*.6+.68+2
 if upper>30:raise PipelineError('Reviewed short story exceeds conservative 30-second budget; shorten text, never accelerate audio')
 from .source_description import fact_version
 return {'fact_version':fact_version(claims),'writer':'reviewed_benefit_composer_v1','editorial_contract':'SOCIAL_BENEFIT_REEL_V1','title':rec['title'],
  'segments':segments,'description':'\n'.join(x['text'] for x in details),'description_details':details,
  'source_note':'SYNTHETIC TEST ONLY - NOT A REAL PROGRAM' if b.get('synthetic') else ('Reconstructed research fixture; not authentic fetched HTML or live ingest.' if b.get('reconstructed_source') else 'Reviewed source snapshot; recheck before production.'),
  'audience_fit':verdict,'live_verified':bool(b.get('live_verified')),'money_benefit':b['money_benefit'],'audience_description':b['audience_description'],'concrete_use':b['concrete_use'],
  'target_duration_seconds':[20,30],'spoken_delivery':{'voice':'af_heart','speed':1.0,'post_atempo':1.0,'engine_emotion_control':False,'audition_required':True},
  'background_policy':'Existing background unrestricted; no competing factual text','caption_contract':'Exact measured spoken words; same-scene accents only',
  'synthetic':bool(b.get('synthetic')),'production_status':'synthetic_source_only' if b.get('synthetic') else 'draft_requires_audio_and_editorial_review'}

def assembly_contract(script,board):
 return {'schema':'SOCIAL_ASSEMBLY_INPUT_V1','state':'source_only','synthetic':bool(script.get('synthetic')),
  'ready_for_assembly':False,'script':script,'storyboard':board,
  'required_before_assembly':['non-synthetic reviewed facts with source hashes and audience fit','measured WAV per scene and combined narration with hashes','matching scene IDs/order and measured speech/caption boundaries','raw ASR plus explained and approved normalization only','full SRT matching audible words; no unspoken headlines','20–30 second actual duration; clipping/silence checks','human voice/prosody and final visual review'],
  'ownership':{'Social':'facts, audience, script, voice plan, captions, release review','assembly':'consume versioned inputs; return output hash/status/error; no silent script edits'},
  'transport':'No external assembler inspected or invoked; submit/ack/result adapter remains unverified',
  'cancellation':'Future adapter must acknowledge cancel, stop partial work and never mark partial output complete',
  'assets':{'wav':None,'srt':None,'mp4':None,'timing':None,'raw_asr':None},'background':'any existing background; do not spend effort changing it'}

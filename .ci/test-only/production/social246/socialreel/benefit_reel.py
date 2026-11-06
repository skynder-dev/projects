"""Short, audience-specific money stories. Full rules belong to sourced description."""
import re
from .common import PipelineError,money

CONTRACT='SOCIAL_BENEFIT_REEL_V1'

def topic_fit(rec,audience="general_us"):
 from .audience_selection import assess
 fit=assess(rec,audience)
 if not fit.get("suitable"):return {"supported":False,"audience":audience,"general_public_money_offer":False,"reason":fit.get("reason") or "; ".join(fit.get("errors",[])),"topic_type":"audience_mismatch"}
 p=rec.get('primary_conditions') or {}
 if p.get('profile')=='imls_native_library_organization_v2':
  return {'supported':True,'audience':'Managers of library/archive services for federally recognized Tribes','general_public_money_offer':False,'reason':'A concrete project budget for an identified institutional audience; not personal cash','topic_type':'tribal_library_project'}
 if rec.get('track_conditions'):return {'supported':False,'audience':'Eligible U.S. research institutions and qualified investigators','general_public_money_offer':False,'reason':'Reviewed track facts are retained for the institutional audience, but this short benefit composer has no approved track-specific story profile; no lack of source value or personal eligibility is inferred'}
 return {'supported':False,'audience':'Not established by a reviewed benefit profile','general_public_money_offer':False,'reason':'No reviewed short money-benefit profile; do not invent benefits or fall back to a long eligibility lecture'}

def make(rec,claims,audience="general_us"):
 from .audience_selection import require
 require(rec,audience)
 if rec.get("editorial_brief"):
  from .editorial_brief import make as compose
  return compose(rec,claims,audience)
 fit=topic_fit(rec,audience)
 if not fit['supported']:raise PipelineError('Editorial topic-fit blocked: '+fit['reason'])
 by={c['key']:c for c in claims};p=rec['primary_conditions'];required=['primary_budget','primary_applicant','primary_cost_share','primary_purpose','primary_lead_applicant','identity']
 if any(k not in by for k in required):raise PipelineError('Short benefit story lacks verified primary claims')
 if p['cost_sharing_policy']['mode'] not in ('optional','prohibited'):raise PipelineError('Matching-funds statement is not established')
 if p['cost_sharing_policy']['mode']=='prohibited':
  if 'primary_share_exclusion' not in by:raise PipelineError('Prohibited cost share needs its explicit source exclusion')
  share=('Do not include matching funds.','Do not include matching funds',['primary_cost_share','primary_share_exclusion'])
 else:share=('No matching funds are required.','No matching funds are required',['primary_cost_share'])
 maximum=p['budget']['max_usd'];lines=[
  ('money_hook',f'Up to ${maximum:,} for your tribal library?',f'Up to ${maximum:,}',['primary_budget','primary_applicant']),
  ('benefit','Build better library services for your community.','Better library services',['primary_purpose']),
  ('budget_advantage',*share),
  ('one_caveat','Federally recognized Native Communities must offer library or archival services.','library or archival services',['primary_applicant','primary_lead_applicant']),
  ('cta','Check the official link below.','Official link below',['identity'])]
 segments=[]
 for i,(role,voice,accent,keys) in enumerate(lines,1):
  start=voice.lower().find(accent.lower());assert start>=0
  segments.append({'id':'s'+str(i),'role':role,'visual':'quote','voiceover':voice,'on_screen':{'kicker':'','headline':voice[start:start+len(accent)],'sub':''},'claim_keys':keys,'screen_anchor':{'start_char':start,'end_char':start+len(accent),'text':voice[start:start+len(accent)]},'delivery':{'tone':'inviting question' if i==1 else 'plain conversational explanation','semantic_stress':accent,'notes_are_direction_not_engine_emotion_control':True}})
 details=[]
 for c in claims:
  if c['key'].startswith('primary_'):details.append({'claim_key':c['key'],'text':c['statement'],'source':c['source']})
 from .source_description import fact_version
 return {'fact_version':fact_version(claims),'writer':'benefit_template_v2','description_detail_policy':'all_primary_claims_v1','editorial_contract':CONTRACT,'title':rec['title']+' — short audience-specific draft','segments':segments,'description':'\n'.join(d['text'] for d in details),'description_details':details,'source_note':'Saved official snapshot; eligibility is not assessed for an individual applicant. Recheck official status before production/publication.','audience_fit':fit,'target_duration_seconds':[20,30],'spoken_delivery':{'voice':'af_heart','speed':1.0,'post_atempo':1.0,'new_voice_test_required':True,'intonation_improvement_not_verified':True},'caption_contract':'Exact spoken words after measured alignment; unexplained lexical mismatch blocks assembly','background_policy':'Any existing background is allowed; it must not introduce competing factual text','production_status':'draft_no_audio_or_video_generated'}

"""A headline is an anchored accent of this voice line, never an independent fact block."""
import re,difflib
from .common import PipelineError
from .benefit_reel import CONTRACT

def validate(script):
 errors=[]
 decision=script.get('editorial_contract')=='SOCIAL_SOURCE_DECISION_REEL_V1'
 if script.get('editorial_contract')!=CONTRACT and not decision:return errors
 from .writer_contract import script_fields
 common=script_fields(script)
 if not common['common_fields_valid']:errors.append('Common spoken/visible writer-field contract failed')
 for row in common['screens']:
  if not row['visible_text']['preparation_valid']:errors.append('Visible '+row['field']+' wording/staging separation requires review')
 if decision:
  if script.get('decision_profile') not in {'nsf_ttp_prior_award_decision_v1','nsf_ttp_prior_award_decision_v2'} or script.get('audience')!='institutional':errors.append('Source decision reel requires the finite institutional TTP profile')
  if script.get('money_benefit'):errors.append('Source decision profile must not become a personal payout offer')
  roles={s.get('role'):s for s in script.get('segments',[])}
  if len(script.get('segments',[]))!=5 or set(roles)!={'hook','track_E','tracks_TP','who','cta'}:errors.append('TTP decision profile requires its five evidence-scoped scenes')
  if script.get('decision_profile')=='nsf_ttp_prior_award_decision_v2' and ('research to practice' not in roles.get('hook',{}).get('voiceover','').lower() or 'purpose_quote' not in roles.get('hook',{}).get('claim_keys',[])):errors.append('Decision hook loses the evidenced purpose of the program')
  e=roles.get('track_E',{}).get('voiceover','');tp=roles.get('tracks_TP',{}).get('voiceover','')
  if not all(re.search(r'\b'+word+r'\b',e,re.I) for word in ('Explore','prior','approval','active','eligible','NSF','award','invitation')) or re.search(r'\b(?:not|never|without)\b',e,re.I):errors.append('Explore must retain active eligible NSF award and invitation requirements')
  if not all(re.search(r'\b'+word+r'\b',tp,re.I) for word in ('Translate','Partner','prior','federal','funding')) or not re.search(r"don't require prior federal funding|prior federal funding.*not.*required",tp,re.I):errors.append('Translate/Partner must preserve the no-prior-federal-funding requirement exception')
  if '?' not in roles.get('hook',{}).get('voiceover','') or 'institutional' not in roles.get('who',{}).get('voiceover','').lower():errors.append('Decision hook must remain a question with institutional audience limits')
  if any(re.search(r'[$€£]|\byou (?:qualify|are eligible|will receive)\b',s.get('voiceover',''),re.I) for s in script.get('segments',[])):errors.append('Decision-angle narration cannot promise money or individual eligibility')
 segs=script.get('segments') or []
 if not 3<=len(segs)<=6:errors.append('Short benefit reel needs3..6single-idea scenes')
 if script.get('spoken_delivery',{}).get('post_atempo')!=1.0:errors.append('Do not speed up a long draft to meet the short-story budget')
 for i,s in enumerate(segs,1):
  voice=s.get('voiceover','');screen=s.get('on_screen') or {};anchor=s.get('screen_anchor') or {};a,b=anchor.get('start_char',-1),anchor.get('end_char',-1)
  if not (0<=a<b<=len(voice)) or voice[a:b]!=anchor.get('text'):errors.append(f'Scene{i}: screen accent is not anchored in its current spoken line');continue
  headline=screen.get('headline','')
  if headline.casefold()!=voice[a:b].casefold():errors.append(f'Scene{i}: headline adds or replaces spoken meaning')
  if screen.get('sub') or screen.get('kicker'):errors.append(f'Scene{i}: unspoken supporting conditions/labels must move to description')
  from .meaning_review import accent_issues
  errors.extend(f'Scene{i}: '+issue for issue in accent_issues(voice,headline))
  if len(headline.split())>9:errors.append(f'Scene{i}: accent is a paragraph, not a short spoken emphasis')
  if len(voice.split())>14:errors.append(f'Scene{i}: split the speech into one idea per scene')
 if not decision and segs and script.get('money_benefit',{}).get('kind') not in {'return_of_owned_money','energy_assistance_information','return_of_recovered_wages'} and not re.search(r'up to\s*\$',segs[0].get('voiceover',''),re.I):errors.append('Money benefit with its limit qualifier must open the story')
 if script.get('money_benefit',{}).get('kind')=='return_of_owned_money' and (script['money_benefit'].get('amount') is not None or not re.search(r'could|might|may',segs[0].get('voiceover',''),re.I)):
  errors.append('Unclaimed money must stay conditional, with unknown individual balance')
 if segs and script.get('money_benefit',{}).get('kind')=='return_of_owned_money' and not re.search(r'\b(could|might|may)\b',(segs[0].get('on_screen') or {}).get('headline',''),re.I):
  errors.append('Conditional owed-money headline must preserve its spoken might/could/may qualifier; no standalone payout promise')
 if script.get('money_benefit',{}).get('kind')=='energy_assistance_information':
  text=' '.join(s.get('voiceover','') for s in segs)
  if script['money_benefit'].get('amount') is not None or not re.search(r'\bmay\b',text,re.I):errors.append('Energy information must keep local amount unknown and assistance conditional')
 if script.get('money_benefit',{}).get('kind')=='return_of_recovered_wages':
  benefit=script['money_benefit']
  if benefit.get('amount') is not None or benefit.get('calendar_deadline') is not None or not re.search(r'could|might|may',segs[0].get('voiceover',''),re.I):errors.append('Recovered wages need conditional matching and unknown balance; holding period is not a calendar deadline')
 if not script.get('description_details'):errors.append('Full sourced conditions cannot be discarded')
 return errors

def board(script,claims):
 errors=validate(script)
 if errors:raise PipelineError('; '.join(errors))
 by={c['key']:c for c in claims};scenes=[]
 for s in script['segments']:
  scenes.append({'id':s['id'],'voiceover':s['voiceover'],'headline':s['on_screen']['headline'],'screen_anchor':s['screen_anchor'],'claim_keys':s['claim_keys'],'sources':[by[k]['source'] for k in s['claim_keys']],'visual':s['visual'],'visual_direction':'Emphasize the quoted words in this same voice line; background unrestricted; no other conditions/text','caption_text':s['voiceover'],'timing':None,'timing_requirement':'Measured future WAV/word alignment only; match scene IDs and native assembly boundaries','delivery':s['delivery']})
 return {'schema':'SOCIAL_SYNCHRONOUS_STORYBOARD_V1','scenes':scenes,'background_policy':script['background_policy'],'no_generated_assets':True,'real_audio_timing_available':False,'assembly_adapter':'not invoked or verified; this is a Social source-material contract'}

def observed_gate(script,report,timing):
 if script.get('editorial_contract') not in {CONTRACT,'SOCIAL_SOURCE_DECISION_REEL_V1'}:return {'pass':True,'applicable':False}
 from .voice import speech_text, speech_for_script
 from .subtitles import normalized_words
 if [s['id'] for s in script['segments']]!=[t['id'] for t in timing]:return {'pass':False,'applicable':True,'reason':'Measured scene IDs/order do not match current voice/script'}
 checks=[];observed=report.get('segments') or []
 for s,t in zip(script['segments'],timing):
  actual=' '.join(w['word'] for part in observed for w in part.get('words',[]) if t['start_s']<=(w['start']+w['end'])/2<t['end_s'])
  expected=normalized_words(speech_for_script(script,s['voiceover']));heard=normalized_words(actual)
  checks.append({'scene_id':s['id'],'pass':expected==heard,'expected':expected,'observed':heard,'reason':None if expected==heard else 'Unexplained lexical mismatch; retain raw ASR and stop for review, do not render guessed subtitles'})
 return {'schema':'SOCIAL_SPOKEN_SCENE_ALIGNMENT_V1','applicable':True,'pass':len(timing)==len(script['segments']) and all(c['pass'] for c in checks),'checks':checks,'subjective_listening_implied':False}

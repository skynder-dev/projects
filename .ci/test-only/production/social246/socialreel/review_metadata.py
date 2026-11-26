"""Program observations and UI codec, separate from unverified model opinion."""
import copy,re,hashlib
from .common import PipelineError,stable_json
VERSION='SOCIAL_REVIEW_METADATA257'
def digest(v):return hashlib.sha256(stable_json(v).encode()).hexdigest()
def act(scene):
 voice=scene['voiceover'];role=scene.get('role')
 if '?' in voice.rstrip()[:-1]:return 'unclassified','internal question punctuation; structural review required'
 if voice.rstrip().endswith('?') and re.match(r'^(Could|Might|May)\b',voice):return 'conditional_question','validated conditional question text'
 if re.match(r'^You (might|could|may)\b',voice) and '?' not in voice:return 'conditional_statement','literal cautious opening without question punctuation'
 if re.match(r'^(Start|Search|Check|Look|Use|Visit|Read|Open|Find)\b',voice):return 'viewer_search_instruction','literal imperative opening'
 if role=='concrete_examples':return 'listed_examples','declared evidence-bound example scene'
 if role in {'guide','source_guide'}:return 'source_guide_reference','declared source guide scene'
 if role in {'cta','call_to_action'} and re.search(r'\bdescription\b',voice,re.I):return 'program_description_reference','literal pointer to description'
 return 'unclassified','no structural rule; human comparison required'
def build(out,scripts,artifact,journal):
 original=digest(out);observations={};mismatches=[];note_flags=[];presentation=copy.deepcopy(out);by={x['id']:x for x in presentation['candidates']}
 model_checks=journal[-1].get('scene_evidence_checks',{}) if journal else {}
 for cid,script in scripts.items():
  scenes=[];voices=[]
  for s in script['segments']:
   effective,method=act(s);model=model_checks.get(cid,{}).get(s['id'],{});unverified=model.get('act',model.get('speech_act'));screen=(s.get('on_screen') or {}).get('headline','')
   if unverified and unverified!=effective:mismatches.append({'candidate':cid,'scene':s['id'],'computed_act':effective,'unverified_model_act':unverified})
   anchor=s.get('screen_anchor') or {};start=anchor.get('start_char');end=anchor.get('end_char');literal=type(start)is int and type(end)is int and 0<=start<end<=len(s['voiceover']) and s['voiceover'][start:end]==screen
   scenes.append({'id':s['id'],'computed_speech_act':effective,'basis':method,'unverified_model_act':unverified,'model_source_verdict_unverified':model.get('decision',model.get('source_verdict')),'spoken_words':len(s['voiceover'].split()),'screen_exact_spoken_span':literal,'screen_is_entire_narration':screen==s['voiceover'],'voice_sha256':hashlib.sha256(s['voiceover'].encode()).hexdigest()})
   voices.append(s['voiceover'])
  hook=script['segments'][0]['voiceover'];warnings=[]
  if '?' in hook.rstrip()[:-1]:warnings.append('INTERNAL_QUESTION_PUNCTUATION')
  if cid=='B' and '?' in hook:warnings.append('STATEMENT_CANDIDATE_HAS_QUESTION_PUNCTUATION')
  observations[cid]={'spoken_words':sum(x['spoken_words'] for x in scenes),'hook_is_question':hook.rstrip().endswith('?'),'scenes':scenes,'interest_status':'NOT_MEASURED','structural_warnings':warnings,'alternative_structure_status':'requires_correction' if warnings else 'no_known_structural_warning_not_semantic_approval'}
  candidate=by[cid];notes=candidate.get('self_review',candidate.get('critique',{}));candidate['segments']=[{'id':s['id'],'voiceover':s['voiceover'],'headline':(s.get('on_screen') or {}).get('headline',''),'claim_keys':s['claim_keys']} for s in script['segments']];candidate['critique']=copy.deepcopy(notes);candidate.pop('self_review',None)
  for field in ['clarity','factual_risks','improvements']:
   text=notes.get(field,'');note_flags.append({'candidate':cid,'field':field,'characters':len(text),'at_contract_char_bound':len(text)==160,'may_be_incomplete':not text.rstrip().endswith(('.','!','?','…')),'status':'UNVERIFIED_MODEL_COMMENTARY'})
 if digest(out)!=original:raise PipelineError('Metadata projection mutated original model output')
 return {'schema':VERSION,'program_observations':observations,'model_act_mismatches':mismatches,'free_text_note_flags':note_flags,'description_artifact_sha256':artifact['text_sha256'],'description_link_lines':len(artifact['literal_link_excerpts']),'model_original_sha256':original,'original_model_data_untouched':True,'source_entailment_verified_by_code':False,'owner_approved':False,'publication_authorized':False},presentation

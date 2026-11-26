"""Replayable visual-only revision of a source preparation; never approve new facts."""
import copy,json,re
from .common import PipelineError,sha256_bytes,stable_json,read_json,sha256_file

def factual_identity(claims):
 from .editorial_brief import factual_claim_payload
 values=[]
 for claim in claims:
  item=factual_claim_payload(claim);item.pop('accent',None);values.append(item)
 return sha256_bytes(stable_json(values).encode('utf-8'))

def build_recipe(manifest,base,claims,current,manual_revision,description_override=''):
 if base.get('editorial_contract')!='SOCIAL_BENEFIT_REEL_V1':raise PipelineError('Visual-only materialization supports the short source-bound story contract')
 if description_override:raise PipelineError('Manual description needs factual/link review; it cannot be silently treated as a visual-only edit')
 if not isinstance(manual_revision,str) or not re.fullmatch('[0-9a-f]{64}',manual_revision):raise PipelineError('Exact saved manual revision required')
 before=base.get('segments') or [];after=current.get('segments') or []
 if len(before)!=len(after):raise PipelineError('Manual scene identities changed; factual review required')
 overrides=[];changed=False
 for old,new in zip(before,after):
  if any(new.get(key)!=old.get(key) for key in ['id','role','voiceover','claim_keys']):raise PipelineError('Narration/claim/scene identity changed; visual-only path cannot verify new facts')
  anchor=new.get('screen_anchor') or {};headline=(new.get('on_screen') or {}).get('headline');a,b=anchor.get('start_char'),anchor.get('end_char');voice=old['voiceover']
  if not isinstance(headline,str) or not headline or len(headline.split())>9 or type(a) is not int or type(b) is not int or not 0<=a<b<=len(voice) or voice[a:b]!=headline or anchor.get('text')!=headline:raise PipelineError('Current exact spoken screen anchor required for every scene')
  if voice.find(headline)!=a or voice.count(headline)!=1:raise PipelineError('Screen accent must identify one unambiguous current spoken phrase')
  if (new.get('on_screen') or {}).get('kicker') or (new.get('on_screen') or {}).get('sub'):raise PipelineError('Unspoken supporting text is not a visual-only accent')
  if len(old.get('claim_keys') or [])!=1:raise PipelineError('Exactly one source-bound claim per scene required')
  overrides.append({'id':old['id'],'role':old['role'],'claim_key':old['claim_keys'][0],'voiceover_sha256':sha256_bytes(voice.encode('utf-8')),'headline':headline,'screen_anchor':anchor})
  changed=changed or headline!=(old.get('on_screen') or {}).get('headline') or anchor!=old.get('screen_anchor')
 if not changed:raise PipelineError('No screen accent changes; the original immutable preparation already represents this text')
 from .scene_coherence import validate
 errors=validate({**base,'segments':after})
 if errors:raise PipelineError('Visual-only story review: '+'; '.join(errors))
 return {'schema':'SOCIAL_VISUAL_REVISION_V1','parent_preparation_id':manifest['preparation_id'],'parent_script_sha256':next(e['sha256'] for e in manifest['files'] if e['path']=='script.json'),'factual_identity':factual_identity(claims),'manual_revision':manual_revision,'scene_overrides':overrides,'scope':'Unchanged factual wording and source evidence; exact screen accents/editorial stress only; no production approval'}

def validate_parent(parent,recipe):
 from .preparation import verify_preparation
 parent=__import__('pathlib').Path(parent);manifest=verify_preparation(parent)
 if not isinstance(recipe,dict) or recipe.get('schema')!='SOCIAL_VISUAL_REVISION_V1' or recipe.get('parent_preparation_id')!=manifest['preparation_id']:raise PipelineError('Visual revision parent identity mismatch')
 if recipe.get('parent_script_sha256')!=sha256_file(parent/'script.json') or recipe.get('factual_identity')!=factual_identity(read_json(parent/'claims.json')['claims']):raise PipelineError('Visual revision differs from the pinned parent facts/script')
 return manifest

def apply(record,recipe):
 expected={'schema','parent_preparation_id','parent_script_sha256','factual_identity','manual_revision','scene_overrides','scope'}
 if not isinstance(recipe,dict) or set(recipe)!=expected or recipe.get('schema')!='SOCIAL_VISUAL_REVISION_V1':raise PipelineError('Unknown visual revision recipe')
 result=copy.deepcopy(record);brief=result.get('editorial_brief')
 if not brief or factual_identity(brief.get('claims',[]))!=recipe['factual_identity']:raise PipelineError('Source factual version changed; preserved screen override requires review, not silent adoption')
 from .editorial_brief import roles_for
 roles=roles_for(brief);overrides=recipe.get('scene_overrides');by={c['key']:c for c in brief['claims']}
 if not isinstance(overrides,list) or len(overrides)!=len(roles):raise PipelineError('Visual revision scene count mismatch')
 for i,(role,o) in enumerate(zip(roles,overrides),1):
  if set(o)!={'id','role','claim_key','voiceover_sha256','headline','screen_anchor'} or o['id']!='s'+str(i) or o['role']!=role or o['claim_key']!=brief['main_facts'][role]:raise PipelineError('Visual revision scene identity mismatch')
  claim=by[o['claim_key']];voice=claim['statement'];anchor=o['screen_anchor'];a,b=anchor.get('start_char'),anchor.get('end_char')
  if sha256_bytes(voice.encode('utf-8'))!=o['voiceover_sha256'] or type(a) is not int or type(b) is not int or not 0<=a<b<=len(voice) or voice[a:b]!=o['headline'] or anchor.get('text')!=o['headline'] or len(o['headline'].split())>9:raise PipelineError('Visual override does not belong to current source wording')
  if voice.find(o['headline'])!=a or voice.count(o['headline'])!=1:raise PipelineError('Ambiguous repeated screen phrase cannot be silently moved on replay')
  claim['accent']=o['headline']
 result['_local_reviewed_brief_sha256']=sha256_bytes(json.dumps(brief,sort_keys=True).encode('utf-8'))
 result['_visual_revision']=copy.deepcopy(recipe)
 return result
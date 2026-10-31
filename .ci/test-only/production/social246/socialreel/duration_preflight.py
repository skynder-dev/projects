"""Cheap source-script length gate before Kokoro inference. No audio/model loading."""
import hashlib
from pathlib import Path
from .voice import speech_text, speech_for_script
from .subtitles import normalized_words
from .common import PipelineError,sha256_file
from .duration_profile import PROFILE

def assess(script,voice_cfg,identity=None):
 if voice_cfg.get('backend')!='kokoro':return {'applicable':False,'pass':True,'reason':'Measured profile only covers fixed local Kokoro voice'}
 if voice_cfg.get('speed',1.0)!=PROFILE['speed']:return {'applicable':True,'pass':False,'reason':'No calibrated duration profile for requested voice speed; prepare/review a bounded script before inference','seconds':None}
 if identity is None:
  directory=Path(voice_cfg.get('model_dir',''))
  try:identity={'model_sha256':sha256_file(directory/'kokoro-v1_0.pth'),'voice_sha256':sha256_file(directory/'voices/af_heart.pt')}
  except OSError:return {'applicable':True,'pass':False,'reason':'Voice model/pack unavailable; duration calibration cannot be bound','seconds':None}
 if any(identity.get(k)!=PROFILE[k] for k in ['model_sha256','voice_sha256']):return {'applicable':True,'pass':False,'reason':'Voice/model bytes differ from measured duration calibration; review required before inference','seconds':None}
 known={p['speech_sha256']:p for p in PROFILE['samples']};items=[]
 for seg in script.get('segments',[]):
  text=speech_for_script(script,seg['voiceover']);key=hashlib.sha256(text.encode()).hexdigest();words=len(normalized_words(text));sample=known.get(key)
  seconds=sample['seconds'] if sample else words/PROFILE['conservative_unknown_words_per_second']
  items.append({'id':seg['id'],'expanded_words':words,'speech_seconds':seconds,'basis':'exact previously measured text/model/voice/speed' if sample else 'conservative estimate for unseen text; not measured audio'})
 if not items:return {'applicable':True,'pass':False,'reason':'No script segments','seconds':None}
 total=sum(s['speech_seconds'] for s in items)+len(items)*PROFILE['fixed_pause_seconds_per_segment']+PROFILE['last_extra_pause_seconds'];all_measured=all(s['basis'].startswith('exact') for s in items);reserve=0 if all_measured else PROFILE['estimate_reserve_seconds'];passed=total+reserve<=PROFILE['maximum_seconds']
 return {'schema':'SOCIAL_DURATION_PREFLIGHT_V1','applicable':True,'pass':passed,'seconds':round(total,3),'reserve_seconds':reserve,'maximum_seconds':PROFILE['maximum_seconds'],'all_text_durations_measured':all_measured,'segments':items,'reason':None if passed else 'Narration plus native pauses exceeds safe Reel duration budget; shorten/review script before voice inference','profile_source_package':PROFILE['source_package_id'],'scope':PROFILE['scope']}

def require(script,voice_cfg):
 result=assess(script,voice_cfg)
 if not result['pass']:raise PipelineError(result['reason']+': '+str(result.get('seconds'))+'s + reserve '+str(result.get('reserve_seconds',0))+'s')
 return result

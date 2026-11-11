"""Verify explicit cached-audio DSP lineage. Never treats it as fresh ASR."""
from pathlib import Path
import wave,hashlib
from .common import read_json,sha256_file,PipelineError

def verify(report,narration,speech,timing,package):
 root=Path(package).resolve();lineage=report['input_lineage']
 if lineage.get('schema')!='SOCIAL_ASR_DERIVED_AUDIO_V1' or (report.get('model_inference_started') is not False or report.get('fresh_ASR') is not False):raise PipelineError('Invalid derived-audio ASR scope')
 from .asr_lineage import audio_inputs
 if lineage['current_inputs']!=audio_inputs(narration,speech,timing,root):raise PipelineError('Derived audio/script/timing bytes changed')
 parent=(root/lineage['parent_root']).resolve()
 if not parent.is_relative_to(root) or parent==root:raise PipelineError('Derived source parent escapes package')
 from .packages import verify_package
 parent_check=verify_package(parent)
 if not parent_check['pass'] or read_json(parent/'package_manifest.json')['package_id']!=lineage['parent_package_id']:raise PipelineError('Derived source package differs')
 if sha256_file(parent/'asr.json')!=lineage['parent_asr_sha256']:raise PipelineError('Parent ASR differs')
 recipe=root/'audio_derivation.json'
 if sha256_file(recipe)!=lineage['recipe_sha256']:raise PipelineError('DSP recipe changed')
 recipe=read_json(recipe)
 if recipe['parent_package_id']!=lineage['parent_package_id'] or len(recipe['clips'])!=len(timing):raise PipelineError('DSP source/segment identity mismatch')
 for clip,span in zip(recipe['clips'],timing):
  if clip['id']!=span['id'] or not 1.0<=clip['atempo']<=1.15:raise PipelineError('Unsupported tempo or segment identity')
  source=(parent/clip['source_relative']).resolve();out=(root/span['audio']).resolve();trim=(root/clip['trimmed_input']).resolve()
  if not source.is_relative_to(parent) or not out.is_relative_to(root) or not trim.is_relative_to(root):raise PipelineError('DSP path escape')
  if sha256_file(source)!=clip['source_sha256'] or sha256_file(out)!=clip['output_sha256'] or sha256_file(trim)!=clip['trimmed_sha256']:raise PipelineError('DSP audio bytes differ')
  with wave.open(str(source),'rb') as w:
   params=(w.getnchannels(),w.getsampwidth(),w.getframerate());count=w.getnframes();a,b=clip['keep_start_frame'],clip['keep_end_frame']
   if not 0<=a<b<=count:raise PipelineError('Invalid source cut')
   w.setpos(a);pcm=w.readframes(b-a)
  with wave.open(str(trim),'rb') as w:
   if params!=(w.getnchannels(),w.getsampwidth(),w.getframerate()) or w.readframes(w.getnframes())!=pcm:raise PipelineError('Trimmed PCM is not the declared source slice')
  with wave.open(str(out),'rb') as w:
   if params!=(w.getnchannels(),w.getsampwidth(),w.getframerate()):raise PipelineError('DSP output format differs')
   duration=w.getnframes()/w.getframerate()
  if abs(duration-clip['retained_seconds']/clip['atempo'])>.08:raise PipelineError('DSP duration differs from bounded atempo recipe')
  if b<count:
   import array,math
   tail=array.array('h',pcm[-round(params[2]*.04)*params[0]*params[1]:]);rms=math.sqrt(sum(v*v for v in tail)/len(tail))
   if rms>=100:raise PipelineError('Cut boundary remains voiced; clipped word risk')
  if clip['filter']!='atempo='+str(clip['atempo']) or clip['new_inference'] is not False:raise PipelineError('DSP filter/inference scope differs')
 from .subtitles import choose_observation
 old=read_json(parent/'asr.json');old_timing=read_json(parent/'timing.json')['segments']
 expected_full=project(old['full_narration_asr'],recipe['clips'],old_timing,timing)
 expected_parts=project(old['per_segment_asr'],recipe['clips'],old_timing,timing)
 if report['full_narration_asr']!=expected_full or report['per_segment_asr']!=expected_parts:raise PipelineError('Derived word observations do not reproduce source time mapping')
 expected=choose_observation(expected_full,expected_parts,speech,timing)
 if not expected['pass'] or abs(expected['word_agreement']-report['word_agreement'])>1e-9 or expected['segments']!=report['segments']:raise PipelineError('Derived transcript/caption gates do not reproduce')
 return True

def project(observations,clips,old_timing,timing):
 result=[]
 for observation in observations:
  for clip,old,new in zip(clips,old_timing,timing):
   words=[];lower=old['speech_start_s'];upper=lower+clip['retained_seconds'];scale=clip['actual_seconds']/clip['retained_seconds']
   for word in observation.get('words',[]):
    mid=(word['start']+word['end'])/2
    if not old['start_s']<=mid<old['end_s'] or mid<lower-.2 or mid>=upper:continue
    if word['end']>upper+.05:raise PipelineError('DSP cut intersects source word')
    a=max(0.,word['start']-lower);b=min(clip['retained_seconds'],max(a,word['end']-lower));words.append({**word,'start':new['speech_start_s']+a*scale,'end':new['speech_start_s']+b*scale})
   if words:result.append({'start':words[0]['start'],'end':words[-1]['end'],'text':''.join(w['word'] for w in words),'words':words,'source_audio':new['audio']})
 return sorted(result,key=lambda v:v['start'])

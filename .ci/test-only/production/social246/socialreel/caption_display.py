"""Caption display endpoints from existing PCM and raw observed word boundaries; no ASR."""
import array,math,re,wave
from pathlib import Path
from .common import read_json,sha256_file,PipelineError

def parse(path):
 def sec(s):
  h,m,x=s.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(x)
 result=[]
 for block in Path(path).read_text(encoding='utf-8').strip().split('\n\n'):
  lines=block.splitlines();a,b=lines[1].split(' --> ');result.append({'start':sec(a),'end':sec(b),'text':' '.join(lines[2:])})
 return result

def quiet_end(audio,observed_end,next_start):
 # Do not add reading-time padding: follow existing trailing PCM to stable quiet.
 # Each of six consecutive 10ms windows must be below -50.3dBFS RMS.
 with wave.open(str(audio),'rb') as w:
  if (w.getnchannels(),w.getsampwidth())!=(1,2):raise PipelineError('Caption release detector requires mono PCM16')
  sr=w.getframerate();duration=w.getnframes()/sr
  for i in range(46):
   start=observed_end+i*.01
   if start+.08>=min(duration,next_start-.1):break
   w.setpos(round(start*sr));pcm=array.array('h',w.readframes(round(.06*sr)));size=round(.01*sr);levels=[math.sqrt(sum(x*x for x in pcm[j:j+size])/len(pcm[j:j+size])) for j in range(0,len(pcm),size)]
   if len(levels)==6 and max(levels)<100:return round(start+.02,3),{'quiet_start':round(start,3),'max_10ms_RMS':max(levels),'threshold_RMS':100,'sustained_quiet_s':.06,'after_quiet_padding_s':.02}
 raise PipelineError('No bounded stable quiet endpoint; keep manual review')

def build(parent):
 parent=Path(parent);old=parse(parent/'subtitles.srt');new=[dict(c) for c in old];asr=read_json(parent/'asr.json');words=[w for s in asr['segments'] for w in s['words']];changes=[]
 for number in [2,5,12,28]:
  cue=new[number-1];before=dict(cue)
  if number==28:
   and_word=[w for w in words if w['word'].strip()=='and' and 79<w['start']<80]
   cert=[w for w in words if w['word'].strip()=='certifications,' and 78<w['start']<79]
   if len(and_word)!=1 or len(cert)!=1 or not new[26]['text'].endswith(' and data'):raise PipelineError('Source phrase boundary differs; no guessed regroup')
   new[26]['text']=new[26]['text'].removesuffix(' and data');new[26]['end']=round(cert[0]['end'],3);cue['start']=round(and_word[0]['start'],3);cue['text']='and data '+cue['text']
  cue['end'],evidence=quiet_end(parent/'audio/narration.wav',before['end'],old[number]['start'])
  changes.append({'cue':number,'before':before,'after':dict(cue),'release_evidence':evidence,'next_onset':old[number]['start'],'reason':'Align premature ASR display endpoint to trailing PCM speech release; regroup the complete and data sharing requirements phrase' if number==28 else 'Align premature ASR display endpoint to trailing PCM speech release; onset unchanged'})
 if ' '.join(c['text'] for c in old)!=' '.join(c['text'] for c in new):raise PipelineError('Caption words changed')
 previous=0.
 for cue in new:
  if not previous<=cue['start']<cue['end']:raise PipelineError('Display overlap/order changed')
  previous=cue['end']
 return new,{'schema':'SOCIAL_CAPTION_DISPLAY_FIX_V1','source_audio_sha256':sha256_file(parent/'audio/narration.wav'),'source_ASR_sha256':sha256_file(parent/'asr.json'),'source_SRT_sha256':sha256_file(parent/'subtitles.srt'),'source_cues':old,'new_cues':new,'changes':changes,'word_sequence_unchanged':True,'new_inference':False,'subjective_listening':False,'scope':'Signal-derived display releases, not a correction of raw ASR observations or an auditory judgment'}

def write(cues,root):
 from .subtitles import timestamp
 from .common import write_text
 srt=[];vtt=['WEBVTT','']
 for i,c in enumerate(cues,1):
  srt += [str(i),timestamp(c['start'],',')+' --> '+timestamp(c['end'],','),c['text'],'']
  vtt += [timestamp(c['start'],'.')+' --> '+timestamp(c['end'],'.'),c['text'],'']
 write_text(Path(root)/'subtitles.srt','\n'.join(srt)+'\n');write_text(Path(root)/'subtitles.vtt','\n'.join(vtt)+'\n')

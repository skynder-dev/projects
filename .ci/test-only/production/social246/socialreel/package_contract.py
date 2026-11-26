"""CPU-only semantic checks for the existing Social Reel package contract."""
import math
import re
import wave
from pathlib import Path
from .common import read_json, sha256_file, PipelineError

REQUIRED = ('sources.json','topic.json','claims.json','script.json','script.md',
            'timing.json','voice.txt','visual_plan.json','media_manifest.json',
            'subtitles.srt','subtitles.vtt','asr.json','audio/narration.wav',
            'final/reel.mp4','mediaengine_handoff/timeline.json')

def semantic_errors(root, entries):
    declared={str(e['path']).replace('\\','/') for e in entries}
    errors=[]
    def file(name, base=root):
        path=(base/str(name).replace('\\','/')).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Missing or unsafe package reference: '+str(name))
        if path.relative_to(root).as_posix() not in declared:
            raise ValueError('Undeclared package reference: '+str(name))
        return path
    def close(a,b):
        return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=.002
    for name in REQUIRED:
        file(name)
    script=read_json(root/'script.json')
    timing=read_json(root/'timing.json')
    visual=read_json(root/'visual_plan.json')['segments']
    handoff=root/'mediaengine_handoff'
    timeline=read_json(handoff/'timeline.json')
    parent=read_json(root/'package_manifest.json').get('lineage',{}).get('parent_preparation_id')
    if parent:
        from .production_origin import verify_origin
        file('production_origin.json')
        try:verify_origin(root,declared,parent)
        except PipelineError as error:errors.append(str(error))
    asr=read_json(root/'asr.json')
    if 'input_lineage' in asr or read_json(root/'package_manifest.json').get('lineage',{}).get('asr_input_schema'):
        from .asr_lineage import verify_audio_inputs
        from .voice import speech_text, speech_for_script
        try:verify_audio_inputs(asr,root/'audio/narration.wav',[speech_for_script(script,s['voiceover']) for s in script['segments']],timing['segments'],root)
        except PipelineError as error:errors.append(str(error))
    spans=timing['segments']
    ids=[s['id'] for s in spans]
    if not ids or len(set(ids))!=len(ids) or ids!=[s['id'] for s in script['segments']] or ids!=[s['id'] for s in visual]:
        errors.append('Script, timing and visual segment identity/order mismatch')
    clips=timeline['clips']
    if len(clips)!=len(spans):errors.append('Handoff clip count mismatch')
    if timeline['fps']!=timing['fps'] or not close(timeline['target_seconds'],timing['total_s']):
        errors.append('Handoff timing metadata mismatch')
    pcm=[]; parameters=None; cursor=0.
    for i,span in enumerate(spans):
        audio=file(span['audio'])
        with wave.open(str(audio),'rb') as w:
            params=(w.getnchannels(),w.getsampwidth(),w.getframerate())
            frames=w.readframes(w.getnframes());duration=w.getnframes()/w.getframerate()
        if parameters is None:parameters=params
        if params!=parameters:errors.append('Segment WAV formats differ')
        tail=1.1 if i==len(spans)-1 else .42
        if not (close(span['start_s'],cursor) and close(span.get('speech_start_s',float(span['start_s'])+.18),cursor+.18)
                and close(span['speech_s'],duration) and close(span['end_s'],cursor+.18+duration+tail)):
            errors.append('Segment audio/timing mismatch: '+span['id'])
        cursor+=.18+duration+tail
        ch,sw,sr=params
        pcm.extend([bytes(int(sr*.18)*ch*sw),frames,bytes(int(sr*tail)*ch*sw)])
        if i<len(clips):
            clip=clips[i]
            if not close(clip['start_s'],span['start_s']) or not close(clip['end_s'],span['end_s']):
                errors.append('Handoff clip timing mismatch: '+span['id'])
            if sha256_file(file(clip['voice'],handoff))!=sha256_file(audio):
                errors.append('Handoff voice mismatch: '+span['id'])
            if i<len(visual) and sha256_file(file(clip['still'],handoff))!=sha256_file(file(visual[i]['still'])):
                errors.append('Handoff still mismatch: '+span['id'])
    narration=file('audio/narration.wav')
    with wave.open(str(narration),'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=parameters or w.readframes(w.getnframes())!=b''.join(pcm):
            errors.append('Narration PCM does not equal ordered segment audio and pauses')
    if not close(cursor,timing['total_s']):errors.append('Total audio timing mismatch')
    if sha256_file(file(timeline['audio'],handoff))!=sha256_file(narration):
        errors.append('Handoff narration mismatch')
    def cues(path,vtt=False):
        text=path.read_text(encoding='utf-8-sig').replace('\r\n','\n').strip()
        blocks=text.split('\n\n')
        if vtt:
            if blocks.pop(0)!='WEBVTT':raise ValueError('Invalid VTT header')
        result=[];previous=0.
        pattern=r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3}) --> (\d{2}):(\d{2}):(\d{2})[,.](\d{3})'
        for i,block in enumerate(blocks,1):
            lines=block.splitlines()
            if not vtt and lines.pop(0)!=str(i):raise ValueError('Invalid SRT cue index')
            match=re.fullmatch(pattern,lines.pop(0))
            if not match or not lines:raise ValueError('Invalid subtitle cue')
            h,m,s,ms,H,M,S,MS=map(int,match.groups())
            start=h*3600+m*60+s+ms/1000;end=H*3600+M*60+S+MS/1000
            if max(m,M,s,S)>=60 or start<previous-.002 or end<=start or end>cursor+.25:
                raise ValueError('Subtitle timing outside narration or overlapping')
            previous=end;result.append((start,end,' '.join(lines)))
        if not result:raise ValueError('Empty subtitles')
        return result
    if cues(file('subtitles.srt'))!=cues(file('subtitles.vtt'),True):
        errors.append('SRT and VTT content/timing mismatch')
    from .claims import validate_script
    errors.extend('Script claims: '+e for e in validate_script(script,read_json(root/'claims.json')['claims']))
    return errors

"""Manual draft byte/shape integrity, never factual or production approval."""
import json
from .common import PipelineError,sha256_bytes,stable_json

def validate(value,identity,base):
    if len(stable_json(value).encode())>1024*1024:raise PipelineError('Manual draft exceeds1MiB; prior bytes preserved')
    if not isinstance(value,dict) or value.get('schema')!='SOCIAL_MANUAL_SCRIPT_DRAFT_V1':raise PipelineError('Manual draft schema invalid; original preserved')
    if value.get('original')!=identity:raise PipelineError('Manual draft belongs to another original; preserved without adoption')
    if not isinstance(value.get('script'),dict) or not isinstance(value.get('publication_text'),dict):raise PipelineError('Manual draft payload missing; preserved')
    expected=sha256_bytes(stable_json({k:value[k] for k in ('original','script','publication_text')}).encode())
    if value.get('draft_id')!=expected:raise PipelineError('Manual draft content identity mismatch; original bytes preserved')
    old=base.get('segments');new=value['script'].get('segments')
    if not isinstance(old,list) or not isinstance(new,list) or len(old)!=len(new):raise PipelineError('Manual draft scene count differs from original; preserved')
    for a,b in zip(old,new):
        if not isinstance(b,dict) or any(a.get(k)!=b.get(k) for k in ('id','role','claim_keys')):raise PipelineError('Manual draft scene identity/order/scope differs; preserved')
        voice=b.get('voiceover')
        if not isinstance(voice,str) or not voice.strip() or len(voice)>3000 or any(ord(c)<32 and c not in '\n\t' for c in voice):raise PipelineError('Manual draft narration shape invalid; preserved')
    if value.get('editorial_approved') is not False or value.get('publication_authorized') is not False:raise PipelineError('Manual draft cannot inherit editorial/publication approval')
    return value

def read(path,identity,base):
    data=path.read_bytes()
    if len(data)>1024*1024:raise PipelineError('Manual draft exceeds1MiB; original preserved')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise PipelineError('Duplicate manual JSON key; original preserved')
            result[key]=value
        return result
    try:value=json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (ValueError,UnicodeError) as error:raise PipelineError('Manual draft unreadable; original bytes preserved') from error
    return validate(value,identity,base)

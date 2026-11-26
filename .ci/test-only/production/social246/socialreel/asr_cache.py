"""Hash-bound raw ASR observations; every read is revalidated by current gates."""
import json,importlib.metadata,sys
from pathlib import Path
from .common import AI_HOME,PipelineError,sha256_bytes,stable_json,atomic_bytes,write_json
DEFAULT_CACHE_DIR=AI_HOME/'asr-cache'
DECODING={'language':'en','beam_size':5,'temperature':0.0,'word_timestamps':True,'condition_on_previous_text':False,'full_vad':False,'per_segment_vad':True}

def identity_for(sealed):
    versions={name:importlib.metadata.version(name) for name in ('faster-whisper','ctranslate2')}
    return {'schema':'SOCIAL_RAW_ASR_IDENTITY_V1','inputs':sealed,'decoding':DECODING,'versions':versions}

def key_for(identity):return sha256_bytes(stable_json(identity).encode())

def load_observations(identity,cache_dir=None):
    key=key_for(identity);path=Path(cache_dir or DEFAULT_CACHE_DIR)/(key+'.json')
    if not path.exists():return None
    try:
        with path.open('rb') as source:raw=source.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise ValueError('Cache exceeds8MiB')
        wrapper=json.loads(raw);payload=wrapper['payload']
        if sha256_bytes(stable_json(payload).encode())!=wrapper['sha256'] or payload['identity']!=identity or payload['key']!=key:raise ValueError('Cache hash/identity differs')
        if not all(isinstance(payload.get(name),list) and all(isinstance(s,dict) and isinstance(s.get('words'),list) for s in payload[name]) for name in ('full','parts')):raise ValueError('Cache observations invalid')
        return payload['full'],payload['parts'],{'key':key,'file':str(path),'payload_sha256':wrapper['sha256']}
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        raise PipelineError('ASR cache corrupt; original preserved; no model fallback: '+str(error)[:200]) from error

def save_observations(identity,full,parts,cache_dir=None,origin=None):
    key=key_for(identity);directory=Path(cache_dir or DEFAULT_CACHE_DIR);directory.mkdir(parents=True,exist_ok=True);path=directory/(key+'.json')
    if path.exists():
        load_observations(identity,directory)
        return {'key':key,'file':str(path),'reused':True}
    payload={'schema':'SOCIAL_RAW_ASR_CACHE_V1','key':key,'identity':identity,'full':full,'parts':parts,'origin':origin or 'Exact local inference inputs; raw observations, not acceptance'}
    atomic_bytes(path,stable_json({'payload':payload,'sha256':sha256_bytes(stable_json(payload).encode())}).encode())
    return {'key':key,'file':str(path),'reused':False}

def install_cache_only_guard(path):
    attempts=[];path=Path(path)
    write_json(path,{'scope':'Owned cache-only worker Python imports','forbidden_model_import_attempts':attempts})
    def audit(event,args):
        if event=='import' and str(args[0]).split('.')[0] in {'torch','kokoro','faster_whisper','ctranslate2','transformers','onnxruntime'}:
            attempts.append(str(args[0]));write_json(path,{'scope':'Owned cache-only worker Python imports','forbidden_model_import_attempts':attempts})
            raise PipelineError('Cache-only worker forbids model import: '+str(args[0]))
    sys.addaudithook(audit)

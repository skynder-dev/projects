"""Local pinned-Qwen admission only. No network, transport, truncation or fallback."""
import copy,json,hashlib
from pathlib import Path
from .common import PipelineError,stable_json
ASSETS=Path(__file__).resolve().parents[1]/'assets'/'concept-tokenizer'
PINS={'qwen-tokenizer-resolved.json':'5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42','qwen-chat_template.jinja':'a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715'}
BASE_BYTES=16384
# Existing owner API: three fields *1000 Unicode characters. Two nested JSON
# serializations need <=12 bytes/character (conservative including controls).
# Technical owner revision envelope (without context) is separately bounded.
OWNER_FIELDS={'audience','editorial_preference','desired_angle'}
OWNER_CHARACTERS=3*1000
OWNER_ENVELOPE_BYTES=1024
OWNER_WIRE_SYNTAX_BYTES=256
TRANSPORT_BYTES=BASE_BYTES+12*OWNER_CHARACTERS+2*OWNER_ENVELOPE_BYTES+OWNER_WIRE_SYNTAX_BYTES
CONTEXT=8192
OUTPUT=1500
GUARD=64

def fail(reason):raise PipelineError('Concept admission: '+reason+'; no model request')

def admit(body):
    try:
        wire=stable_json(body).encode('utf-8')
        if len(wire)>TRANSPORT_BYTES:fail('transport_size_exceeded')
        if body.get('model')!='qwen3.5:9b' or body.get('think') is not False or body.get('stream') is not False:fail('unknown_model_or_mode')
        if any(body.get('options',{}).get(k)!=v for k,v in {'num_ctx':CONTEXT,'num_predict':OUTPUT,'num_gpu':0,'num_thread':4}.items()):fail('unknown_resource_contract')
        data=json.loads(body['prompt']);owner=data.get('owner_context')
        if owner is not None:
            if not isinstance(owner,dict) or owner.get('scope')!='unverified_owner_editorial_context' or owner.get('owner_approval') is not False or owner.get('source_evidence') is not False:fail('invalid_owner_envelope')
            context=owner.get('context');metadata={k:v for k,v in owner.items() if k!='context'}
            if not isinstance(context,dict) or set(context)-OWNER_FIELDS or any(not isinstance(v,str) or len(v)>1000 for v in context.values()):fail('owner_field_limit')
            if set(metadata)-{'scope','source_evidence','owner_approval','revision','schema','job_id','parent_revision'} or any(not isinstance(v,(str,bool)) or (isinstance(v,str) and len(v)>64) for v in metadata.values()):fail('owner_metadata_shape')
            if len(stable_json(metadata).encode('utf-8'))>OWNER_ENVELOPE_BYTES:fail('owner_metadata_limit')
        # Preserve the pre-existing complete non-owner evidence/brief bound.
        # Same inner formatting as the builder; this body is measured, never sent.
        without=copy.deepcopy(body);data.pop('owner_context',None)
        without['prompt']=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')) if data.get('evidence_mode')=='excerpts' else stable_json(data)
        if len(stable_json(without).encode('utf-8'))>BASE_BYTES:fail('non_owner_envelope_exceeded')
        try:
            from tokenizers import Tokenizer
            from jinja2 import Environment
        except ImportError as e:fail('offline_tokenizer_unavailable: '+str(e))
        assets={}
        for name,expected in PINS.items():
            raw=(ASSETS/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=expected:fail('tokenizer_or_template_hash_mismatch')
            assets[name]=raw
        tokenizer=Tokenizer.from_str(assets['qwen-tokenizer-resolved.json'].decode('utf-8'))
        env=Environment();env.globals['raise_exception']=lambda x:(_ for _ in ()).throw(ValueError(x))
        rendered=env.from_string(assets['qwen-chat_template.jinja'].decode('utf-8')).render(messages=[{'role':'system','content':body['system']},{'role':'user','content':body['prompt']}],add_generation_prompt=True,enable_thinking=False,tools=None)
        ids=tokenizer.encode(rendered,add_special_tokens=False).ids
        if tokenizer.decode(ids,skip_special_tokens=False)!=rendered:fail('tokenizer_roundtrip_mismatch')
        if len(ids)+OUTPUT+GUARD>CONTEXT:fail('context_capacity_exceeded')
        return {'transport_bytes':len(wire),'transport_cap':TRANSPORT_BYTES,'prompt_tokens':len(ids),'output_reserved':OUTPUT,'guard_reserved':GUARD,'context':CONTEXT,'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'runtime_enforcement_verified':False}
    except PipelineError:raise
    except Exception as e:fail('unverifiable_offline_admission: '+type(e).__name__)

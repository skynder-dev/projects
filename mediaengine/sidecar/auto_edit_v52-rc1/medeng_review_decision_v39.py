#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, time
from pathlib import Path
import medeng_approval_v36 as approval
import medeng_variant_comparison_v37 as comparison

CANDIDATE='MEDENG_REVIEW_DECISION_V39_RC1'
SCHEMA_VERSION=1
MODE_MAP={'AUTO':'auto','ALT_A':'alt-a','ALT_B':'alt-b','OVERRIDE':'latest-override'}

class DecisionError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def atomic_json(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.part')
    t.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8'); os.replace(t,p)

def atomic_text(p:Path,s:str):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.part'); t.write_text(s,encoding='utf-8'); os.replace(t,p)

def read_json(p:Path)->dict:
    try:o=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:raise DecisionError(f'JSON_READ_FAILED:{p}:{type(e).__name__}') from e
    if not isinstance(o,dict):raise DecisionError(f'JSON_OBJECT_REQUIRED:{p}')
    return o

def source_for(job:Path,key:str)->dict:
    try:
        if key=='AUTO': return approval.source_auto(job)
        if key=='ALT_A': return approval.source_alternative(job,'ALT_A')
        if key=='ALT_B': return approval.source_alternative(job,'ALT_B')
        if key=='OVERRIDE': return approval.source_override(job)
    except Exception as e:
        raise DecisionError(f'SOURCE_INVALID:{key}:{e}') from e
    raise DecisionError('CHOICE_MODE_INVALID:'+key)

def available(job:Path)->tuple[dict,list[dict]]:
    cmp=comparison.validate(job)
    if not cmp: raise DecisionError('VARIANT_COMPARISON_INVALID_OR_MISSING')
    rows=[]
    for key in ('AUTO','ALT_A','ALT_B','OVERRIDE'):
        try:src=source_for(job,key)
        except DecisionError:
            # Alternatives are intentionally best-effort: short/simple footage may have
            # no distinct ALT_A/ALT_B. AUTO remains reviewable and approvable.
            if key in ('ALT_A','ALT_B','OVERRIDE'): continue
            raise
        fp=approval.approval_fingerprint(src)
        rows.append({'key':key,'approval_mode':MODE_MAP[key],'approval_fingerprint':fp,'source_manifest':str(Path(src['source_manifest']).resolve()),'source_manifest_sha256':sha256_file(Path(src['source_manifest']))})
    return cmp,rows

def context_payload(job:Path)->dict:
    cmp,rows=available(job)
    payload={'candidate':CANDIDATE,'schema_version':SCHEMA_VERSION,'job_outdir':str(job.resolve()),'comparison_content_sha256':cmp['comparison_content_sha256'],'available_choices':rows,'semantic_selection_claim':False}
    core=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    payload['context_sha256']=hashlib.sha256(core).hexdigest()
    return payload

def archive_if_exists(review:Path,name:str):
    p=review/name
    if not p.exists():return
    hist=review/'_ChoiceHistory'; hist.mkdir(exist_ok=True)
    dst=hist/f'{p.stem}.{int(time.time())}.{os.getpid()}{p.suffix}'
    os.replace(p,dst)

def prepare(job:Path,default='AUTO')->dict:
    job=job.resolve(); review=job/'Review'; review.mkdir(parents=True,exist_ok=True)
    ctx=context_payload(job)
    keys=[x['key'] for x in ctx['available_choices']]
    if default not in keys: default='AUTO' if 'AUTO' in keys else keys[0]
    cp=review/'CHOICE_CONTEXT.json'; tp=review/'CHOICE.txt'
    oldctx=None
    if cp.is_file():
        try:oldctx=read_json(cp)
        except Exception:oldctx=None
    # Preserve an existing editable choice only when it belongs to the exact same review context.
    same=bool(oldctx and oldctx.get('context_sha256')==ctx['context_sha256'])
    if not same:
        archive_if_exists(review,'CHOICE_CONTEXT.json');archive_if_exists(review,'CHOICE.txt')
        atomic_json(cp,ctx)
        lines=['# MediaEngine Review Choice','# Change ONLY the value after CHOICE=, then save and run Apply Review Choice.',f"CHOICE={default}",f"# AVAILABLE={','.join(keys)}",f"# CONTEXT_SHA256={ctx['context_sha256']}",'']
        atomic_text(tp,'\n'.join(lines))
    elif not tp.is_file():
        atomic_text(tp,f"CHOICE={default}\n# AVAILABLE={','.join(keys)}\n# CONTEXT_SHA256={ctx['context_sha256']}\n")
    return {'candidate':CANDIDATE,'status':'PASS','choice_file':str(tp),'context_file':str(cp),'available':keys,'context_sha256':ctx['context_sha256'],'resume_status':'SKIPPED_EXACT_CONTEXT' if same else None}

def parse_choice(tp:Path)->str:
    if not tp.is_file():raise DecisionError('CHOICE_FILE_MISSING')
    found=[]
    for raw in tp.read_text(encoding='utf-8').splitlines():
        s=raw.strip()
        if not s or s.startswith('#'):continue
        m=re.fullmatch(r'CHOICE\s*=\s*([A-Za-z0-9_-]+)',s)
        if not m:raise DecisionError('CHOICE_FILE_INVALID_LINE:'+s[:80])
        found.append(m.group(1).upper().replace('-','_'))
    if len(found)!=1:raise DecisionError('CHOICE_FILE_REQUIRES_EXACTLY_ONE_CHOICE')
    if found[0] not in MODE_MAP:raise DecisionError('CHOICE_MODE_INVALID:'+found[0])
    return found[0]

def validate_context(job:Path,ctx:dict)->tuple[str,dict]:
    expected=context_payload(job)
    # Stored context itself must be internally intact and match exact current review/source identities.
    stored=dict(ctx);stored_hash=stored.pop('context_sha256',None)
    calc=hashlib.sha256(json.dumps(stored,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if not stored_hash or calc!=stored_hash:raise DecisionError('CHOICE_CONTEXT_SELF_HASH_MISMATCH')
    if expected['context_sha256']!=stored_hash:raise DecisionError('CHOICE_STALE_CONTEXT')
    key=parse_choice(job/'Review'/'CHOICE.txt')
    rec=next((x for x in expected['available_choices'] if x['key']==key),None)
    if not rec:raise DecisionError('CHOICE_NOT_AVAILABLE:'+key)
    return key,rec

def apply(job:Path,global_pointer:Path|None=None)->dict:
    job=job.resolve();review=job/'Review';cp=review/'CHOICE_CONTEXT.json'
    if not cp.is_file():raise DecisionError('CHOICE_CONTEXT_MISSING')
    key,rec=validate_context(job,read_json(cp))
    approved=approval.build(job,MODE_MAP[key],global_pointer)
    amp=job/'Approved'/'APPROVED_MANIFEST.json'
    if not amp.is_file():raise DecisionError('APPROVED_MANIFEST_MISSING_AFTER_APPLY')
    if approved.get('approval_fingerprint')!=rec['approval_fingerprint']:raise DecisionError('APPROVAL_FINGERPRINT_CHANGED')
    record={'candidate':CANDIDATE,'schema_version':SCHEMA_VERSION,'status':'PASS','choice':key,'approval_mode':MODE_MAP[key],'context_sha256':read_json(cp)['context_sha256'],'approval_fingerprint':approved['approval_fingerprint'],'approved_manifest':str(amp.resolve()),'approved_manifest_sha256':sha256_file(amp),'applied_at_unix':time.time(),'semantic_selection_claim':False}
    prev=review/'APPLIED_CHOICE.json'
    if prev.is_file():
        try:p=read_json(prev)
        except Exception:p={}
        if p.get('choice')==key and p.get('approval_fingerprint')==record['approval_fingerprint'] and p.get('approved_manifest_sha256')==record['approved_manifest_sha256']:
            record['resume_status']='SKIPPED_EXACT_COMPLETED';return record
        archive_if_exists(review,'APPLIED_CHOICE.json')
    atomic_json(prev,record)
    return record

def status(job:Path)->dict:
    job=job.resolve(); review=job/'Review'; out={'candidate':CANDIDATE,'job_outdir':str(job),'choice':None,'choice_context_valid':False,'applied':None}
    if (review/'CHOICE.txt').is_file():
        try:out['choice']=parse_choice(review/'CHOICE.txt')
        except Exception as e:out['choice_error']=str(e)
    if (review/'CHOICE_CONTEXT.json').is_file():
        try:validate_context(job,read_json(review/'CHOICE_CONTEXT.json'));out['choice_context_valid']=True
        except Exception as e:out['context_error']=str(e)
    if (review/'APPLIED_CHOICE.json').is_file():
        try:out['applied']=read_json(review/'APPLIED_CHOICE.json')
        except Exception as e:out['applied_error']=str(e)
    return out

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('prepare');p.add_argument('--job-outdir',required=True);p.add_argument('--default',default='AUTO')
    p=sub.add_parser('apply');p.add_argument('--job-outdir',required=True);p.add_argument('--global-pointer')
    p=sub.add_parser('status');p.add_argument('--job-outdir',required=True)
    a=ap.parse_args()
    try:
        if a.cmd=='prepare':r=prepare(Path(a.job_outdir),str(a.default).upper().replace('-','_'))
        elif a.cmd=='apply':r=apply(Path(a.job_outdir),Path(a.global_pointer) if a.global_pointer else None)
        else:r=status(Path(a.job_outdir))
        print(json.dumps(r,indent=2,sort_keys=True))
    except Exception as e:
        print(json.dumps({'candidate':CANDIDATE,'status':'FAIL','error':str(e)},indent=2));raise SystemExit(1)
if __name__=='__main__':main()

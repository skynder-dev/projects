#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, time
from pathlib import Path
import medeng_approval_v36 as approval

CANDIDATE='MEDENG_AUTO_APPROVAL_V39_RC1'
SCHEMA_VERSION=1
POLICIES={'manual','auto'}

class AutoApprovalError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def atomic_json(p:Path,obj:object):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+'.tmp')
    t.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8')
    os.replace(t,p)

def atomic_text(p:Path,s:str):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+'.tmp')
    t.write_text(s,encoding='utf-8')
    os.replace(t,p)

def write_record(job:Path,record:dict)->None:
    atomic_json(job/'Review'/'AUTO_APPROVAL_V39.json',record)

def pointer_payload(job:Path,approved:Path,fp:str)->dict:
    return {
        'candidate': approval.CANDIDATE,
        'job_outdir': str(job.resolve()),
        'approved_manifest': str((approved/'APPROVED_MANIFEST.json').resolve()),
        'approval_fingerprint': fp,
        'updated_at_unix': time.time(),
        'auto_approval_candidate': CANDIDATE,
    }

def existing_manifest_evidence(approved:Path)->dict:
    mp=approved/'APPROVED_MANIFEST.json'
    out={'approved_exists':approved.exists(),'approved_manifest_exists':mp.is_file()}
    if mp.is_file():
        try:
            out['approved_manifest_sha256']=sha256_file(mp)
            obj=json.loads(mp.read_text(encoding='utf-8'))
            if isinstance(obj,dict):
                out['existing_approval_mode']=obj.get('approval_mode')
                out['existing_approval_fingerprint']=obj.get('approval_fingerprint')
        except Exception as e:
            out['approved_manifest_error']=type(e).__name__+': '+str(e)
    return out

def ensure(job:Path, policy:str='manual', global_pointer:Path|None=None)->dict:
    job=job.resolve(); policy=str(policy).strip().lower()
    if policy not in POLICIES: raise AutoApprovalError('AUTO_APPROVAL_POLICY_INVALID:'+policy)
    base={
        'candidate':CANDIDATE,'schema_version':SCHEMA_VERSION,'policy':policy,
        'job_outdir':str(job),'semantic_selection_claim':False,'updated_at_unix':time.time(),
    }
    if policy=='manual':
        rec={**base,'status':'MANUAL_REVIEW_REQUIRED','mutated_approved':False}
        approved=job/'Approved'; existing=approval.existing_approved_manifest(approved) if approved.exists() else None
        if existing:
            _cm,_cp=approval.desired_cover_policy(job); rec['cover_assets']=approval.ensure_approved_covers(approved,existing.get('outputs') or [],_cm,_cp)
        write_record(job,rec); return rec
    src=approval.source_auto(job)
    fp=approval.approval_fingerprint(src)
    approved=job/'Approved'
    exact=approval.current_exact(approved,fp)
    if exact:
        _cm,_cp=approval.desired_cover_policy(job); covers=approval.ensure_approved_covers(approved,exact.get('outputs') or [],_cm,_cp)
        if global_pointer: atomic_json(global_pointer,pointer_payload(job,approved,fp))
        rec={**base,'status':'SKIPPED_EXACT_AUTO','approval_fingerprint':fp,
             'approved_manifest':str((approved/'APPROVED_MANIFEST.json').resolve()),
             'approved_manifest_sha256':sha256_file(approved/'APPROVED_MANIFEST.json'),
             'cover_assets':covers,'mutated_approved':False}
        write_record(job,rec); return rec
    if approved.exists():
        existing=approval.existing_approved_manifest(approved)
        _cm,_cp=approval.desired_cover_policy(job); covers=approval.ensure_approved_covers(approved,existing.get('outputs') or [],_cm,_cp) if existing else None
        rec={**base,'status':'BLOCKED_EXISTING_APPROVAL','approval_fingerprint':fp,
             'mutated_approved':False,**existing_manifest_evidence(approved)}
        if covers is not None: rec['cover_assets']=covers
        write_record(job,rec); return rec

    tmp=job/f'.Approved.auto-v39.tmp.{os.getpid()}.{int(time.time()*1000)}'
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        outputs=[]
        for src_rec in src['outputs']:
            fn=f"approved_reel_{src_rec['profile']}.mp4"
            dst=tmp/fn
            approval.atomic_copy(src_rec['path'],dst,src_rec['sha256'],src_rec['bytes'])
            outputs.append({'profile':src_rec['profile'],'filename':fn,'bytes':dst.stat().st_size,'sha256':sha256_file(dst)})
        _cm,_cp=approval.desired_cover_policy(job); covers=approval.ensure_approved_covers(tmp,outputs,_cm,_cp)
        source_manifest_sha=sha256_file(src['source_manifest'])
        manifest={
            'candidate':approval.CANDIDATE,'schema_version':approval.SCHEMA_VERSION,'status':'PASS',
            'approval_mode':src['mode'],'approval_fingerprint':fp,'source_id':src['source_id'],
            'source_manifest':str(src['source_manifest']),'source_manifest_sha256':source_manifest_sha,
            'semantic_selection_claim':False,'outputs':outputs,'approved_at_unix':time.time(),
            'original_automatic_reels_overwritten':False,'approval_policy':'AUTO_OPT_IN_V39',
        }
        atomic_json(tmp/'APPROVED_MANIFEST.json',manifest)
        atomic_text(tmp/'APPROVED.txt',
            'MediaEngine Approved Delivery\nMode: AUTO\nApproval policy: AUTO_OPT_IN_V39\n'
            f'Approval fingerprint: {fp}\n16:9: approved_reel_16x9.mp4\n9:16: approved_reel_9x16.mp4\n'
            'Original automatic, alternative and override reels remain unchanged.\n')
        # Atomic publish only if Approved is still absent. We never archive/replace a competing human approval.
        try:
            os.rename(tmp,approved)
        except OSError:
            if tmp.exists(): shutil.rmtree(tmp,ignore_errors=True)
            exact=approval.current_exact(approved,fp)
            if exact:
                _cm,_cp=approval.desired_cover_policy(job); race_covers=approval.ensure_approved_covers(approved,exact.get('outputs') or [],_cm,_cp)
                if global_pointer: atomic_json(global_pointer,pointer_payload(job,approved,fp))
                rec={**base,'status':'SKIPPED_EXACT_AUTO_RACE','approval_fingerprint':fp,
                     'approved_manifest':str((approved/'APPROVED_MANIFEST.json').resolve()),
                     'approved_manifest_sha256':sha256_file(approved/'APPROVED_MANIFEST.json'),
                     'cover_assets':race_covers,'mutated_approved':False}
                write_record(job,rec); return rec
            rec={**base,'status':'BLOCKED_EXISTING_APPROVAL_RACE','approval_fingerprint':fp,
                 'mutated_approved':False,**existing_manifest_evidence(approved)}
            write_record(job,rec); return rec
        if global_pointer: atomic_json(global_pointer,pointer_payload(job,approved,fp))
        rec={**base,'status':'AUTO_APPROVED','approval_fingerprint':fp,
             'approved_manifest':str((approved/'APPROVED_MANIFEST.json').resolve()),
             'approved_manifest_sha256':sha256_file(approved/'APPROVED_MANIFEST.json'),
             'cover_assets':covers,'mutated_approved':True}
        write_record(job,rec); return rec
    except Exception:
        if tmp.exists(): shutil.rmtree(tmp,ignore_errors=True)
        raise

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--job-outdir',required=True)
    ap.add_argument('--policy',choices=sorted(POLICIES),default='manual');ap.add_argument('--global-pointer')
    a=ap.parse_args()
    try:
        r=ensure(Path(a.job_outdir),a.policy,Path(a.global_pointer) if a.global_pointer else None)
        print(json.dumps(r,indent=2,sort_keys=True))
    except Exception as e:
        print(json.dumps({'candidate':CANDIDATE,'status':'FAIL','error':type(e).__name__+': '+str(e)},indent=2))
        raise SystemExit(1)
if __name__=='__main__': main()

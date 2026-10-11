#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from types import SimpleNamespace
from pathlib import Path
import medeng_auto_approval_v39 as aa
import medeng_drop_queue_v40 as queue

def sha(p:Path)->str:
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def tree_hash(root:Path)->str:
    h=hashlib.sha256()
    if not root.exists(): return 'MISSING'
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        h.update(str(p.relative_to(root)).replace('\\','/').encode()); h.update(b'\0'); h.update(p.read_bytes()); h.update(b'\0')
    return h.hexdigest()

def mkjob(root:Path,name='job')->Path:
    job=root/name; job.mkdir(parents=True)
    a=job/'reel_16x9.mp4'; b=job/'reel_9x16.mp4'
    a.write_bytes(b'V39-AUTO-16X9-'+name.encode()); b.write_bytes(b'V39-AUTO-9X16-'+name.encode())
    result={
        'candidate':'MEDENG_DROP_QUEUE_V40_RC1','schema_version':1,'status':'PASS','job_id':name,'fingerprint':'fp-'+name,
        'semantic_selection_claim':False,
        'outputs':[
            {'profile':'16x9','filename':a.name,'bytes':a.stat().st_size,'sha256':sha(a)},
            {'profile':'9x16','filename':b.name,'bytes':b.stat().st_size,'sha256':sha(b)},
        ]
    }
    (job/'JOB_RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return job

def check(cond:bool,name:str,checks:dict):
    checks[name]=bool(cond)
    if not cond: raise AssertionError(name)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--keep-temp',action='store_true'); a=ap.parse_args()
    td=Path(tempfile.mkdtemp(prefix='medeng_v42_logic_')); checks={}
    try:
        # Config contract: default manual; explicit auto accepted; invalid policy rejected.
        cfg,_,_=queue.load_job_config(None,30,False); check(cfg['approval_mode']=='manual','config_default_manual',checks); check(cfg['max_attempts']==1,'config_default_single_attempt',checks); check(float(cfg['retry_backoff_seconds'])==30.0,'config_default_retry_backoff',checks)
        cp=td/'AUTO_EDIT.json';cp.write_text(json.dumps({'schema_version':1,'target_seconds':30,'ready_mode':'settle','approval_mode':'auto'}))
        cfg2,h2,_=queue.load_job_config(cp,30,False);check(cfg2['approval_mode']=='auto' and bool(h2),'config_auto_opt_in',checks)
        cp.write_text(json.dumps({'schema_version':1,'approval_mode':'replace'}))
        try: queue.load_job_config(cp,30,False); bad=False
        except ValueError as e: bad='AUTO_EDIT_JSON_APPROVAL_MODE' in str(e)
        check(bad,'config_invalid_policy_fail_closed',checks)

        # Bounded recovery contract: explicit only, tightly bounded, invalid values fail closed.
        cp.write_text(json.dumps({'schema_version':1,'approval_mode':'auto','max_attempts':3,'retry_backoff_seconds':12}))
        cfg3,h3,_=queue.load_job_config(cp,30,False);check(cfg3['max_attempts']==3 and cfg3['retry_backoff_seconds']==12.0 and bool(h3),'config_bounded_retry_opt_in',checks)
        cp.write_text(json.dumps({'schema_version':1,'max_attempts':5}))
        try: queue.load_job_config(cp,30,False); bad_attempts=False
        except ValueError as e: bad_attempts='AUTO_EDIT_JSON_MAX_ATTEMPTS_RANGE_1_4' in str(e)
        check(bad_attempts,'config_retry_limit_fail_closed',checks)
        cp.write_text(json.dumps({'schema_version':1,'retry_backoff_seconds':-1}))
        try: queue.load_job_config(cp,30,False); bad_backoff=False
        except ValueError as e: bad_backoff='AUTO_EDIT_JSON_RETRY_BACKOFF_RANGE_0_3600' in str(e)
        check(bad_backoff,'config_backoff_fail_closed',checks)

        # Pure failure transition: default quarantines immediately; opt-in retry waits, then exhaustion quarantines.
        base={'job_id':'fail-job','fingerprint':'fail-fp','attempt':1,'status':'processing'}
        ft1=queue.failure_transition(base,{'max_attempts':1,'retry_backoff_seconds':30},'RuntimeError: boom',now=100.0)
        check(ft1['status']=='quarantined' and ft1['attempt']==1,'default_failure_quarantines',checks)
        ft2=queue.failure_transition(base,{'max_attempts':3,'retry_backoff_seconds':12},'RuntimeError: boom',now=100.0)
        check(ft2['status']=='retry_wait' and ft2['next_retry_at_unix']==112.0,'bounded_retry_wait_scheduled',checks)
        base3={**base,'attempt':3}
        ft3=queue.failure_transition(base3,{'max_attempts':3,'retry_backoff_seconds':12},'RuntimeError: boom',now=100.0)
        check(ft3['status']=='quarantined' and ft3['attempt']==3,'bounded_retry_exhaustion_quarantines',checks)

        # Manual is no-op for Approved.
        j1=mkjob(td,'manual'); r=aa.ensure(j1,'manual',td/'manual-pointer.json')
        check(r['status']=='MANUAL_REVIEW_REQUIRED','manual_status',checks)
        check(not (j1/'Approved').exists(),'manual_no_approved_mutation',checks)
        check(not (td/'manual-pointer.json').exists(),'manual_no_global_pointer',checks)

        # AUTO creates exact Approved and pointer.
        j2=mkjob(td,'auto'); gp=td/'latest-approved.json'; r=aa.ensure(j2,'auto',gp)
        check(r['status']=='AUTO_APPROVED','auto_approved',checks)
        amp=j2/'Approved'/'APPROVED_MANIFEST.json'; m=json.loads(amp.read_text())
        check(m['approval_mode']=='AUTO' and m['approval_policy']=='AUTO_OPT_IN_V39','auto_manifest_policy',checks)
        check(m['semantic_selection_claim'] is False,'semantic_claim_false',checks)
        check(gp.is_file() and json.loads(gp.read_text())['approval_fingerprint']==m['approval_fingerprint'],'global_pointer_exact',checks)
        before=tree_hash(j2/'Approved'); r2=aa.ensure(j2,'auto',gp); after=tree_hash(j2/'Approved')
        check(r2['status']=='SKIPPED_EXACT_AUTO' and before==after,'auto_idempotent_exact',checks)

        # Existing approval always wins; no replacement/archive.
        j3=mkjob(td,'human-wins'); ad=j3/'Approved';ad.mkdir();(ad/'approved_reel_16x9.mp4').write_bytes(b'HUMAN16');(ad/'approved_reel_9x16.mp4').write_bytes(b'HUMAN9')
        hm={'candidate':'MEDENG_APPROVAL_V36_RC1','schema_version':1,'status':'PASS','approval_mode':'ALTERNATIVE_ALT_A','approval_fingerprint':'human-fp','outputs':[
            {'profile':'16x9','filename':'approved_reel_16x9.mp4','bytes':7,'sha256':sha(ad/'approved_reel_16x9.mp4')},
            {'profile':'9x16','filename':'approved_reel_9x16.mp4','bytes':6,'sha256':sha(ad/'approved_reel_9x16.mp4')},
        ]}
        (ad/'APPROVED_MANIFEST.json').write_text(json.dumps(hm,indent=2));hb=tree_hash(ad); r3=aa.ensure(j3,'auto',td/'blocked-pointer.json');ha=tree_hash(ad)
        check(r3['status']=='BLOCKED_EXISTING_APPROVAL' and hb==ha,'existing_approval_preserved',checks)
        check(not (td/'blocked-pointer.json').exists(),'blocked_does_not_move_pointer',checks)
        check(not (j3/'_ApprovedHistory').exists(),'auto_never_archives_human_approval',checks)

        # Source tamper must stop approval before Approved exists.
        j4=mkjob(td,'tamper');(j4/'reel_16x9.mp4').write_bytes(b'TAMPERED')
        try: aa.ensure(j4,'auto'); tamper_failed=False
        except Exception: tamper_failed=True
        check(tamper_failed and not (j4/'Approved').exists(),'tampered_source_fail_closed',checks)

        # Simulate competing approval appearing at the atomic publish boundary.
        j5=mkjob(td,'race'); real_rename=aa.os.rename
        def racing_rename(src,dst):
            srcp,dstp=Path(src),Path(dst)
            if srcp.name.startswith('.Approved.auto-v39.tmp.') and dstp.name=='Approved':
                dstp.mkdir(parents=True,exist_ok=True);(dstp/'HUMAN_WON.txt').write_text('human approval appeared first')
                raise FileExistsError('synthetic approval race')
            return real_rename(src,dst)
        aa.os.rename=racing_rename
        try: rr=aa.ensure(j5,'auto',td/'race-pointer.json')
        finally: aa.os.rename=real_rename
        check(rr['status']=='BLOCKED_EXISTING_APPROVAL_RACE','race_fail_closed',checks)
        check((j5/'Approved'/'HUMAN_WON.txt').read_text()=='human approval appeared first','race_human_bytes_preserved',checks)
        check(not (td/'race-pointer.json').exists(),'race_does_not_move_pointer',checks)

        # Queue adapter returns structured error instead of converting a completed render into a failed render.
        j6=mkjob(td,'queue-adapter');(j6/'reel_9x16.mp4').unlink()
        qr=queue.apply_approval_policy(j6,td,{'approval_mode':'auto'})
        check(qr['status']=='ERROR' and qr['mutated_approved'] is False,'queue_approval_error_is_downstream_state',checks)

        # Changing an already-rendered exact job from manual -> auto reconciles approval without re-rendering.
        outbox=td/'retro-out'; qroot=td/'retro-queue'; inbox=td/'retro-in'; outbox.mkdir();qroot.mkdir();inbox.mkdir()
        retro=mkjob(outbox,'retro-job'); cfgp=td/'retro-AUTO_EDIT.json';cfgp.write_text(json.dumps({'schema_version':1,'target_seconds':30,'ready_mode':'settle','approval_mode':'auto'}))
        srcfile=td/'retro-source.mp4';srcfile.write_bytes(b'unchanged-source')
        sp=qroot/'jobs'/'retro-job'/'job_state.json';sp.parent.mkdir(parents=True)
        sp.write_text(json.dumps({'candidate':'MEDENG_DROP_QUEUE_V40_RC1','job_id':'retro-job','label':'retro','fingerprint':'retro-fp','status':'passed','attempt':1,'target_seconds':30}))
        cand=queue.CandidateJob(label='retro',source_key='retro/',files=[srcfile],batch_root=None,config_path=cfgp)
        args=SimpleNamespace(target_seconds=30,settle_seconds=0,require_batch_ready_marker=False,batch_settle_seconds=0,queue_root=qroot,outbox=outbox,per_file_timeout_s=1,job_hard_timeout_s=0)
        old_settle,old_fp,old_valid=queue.is_settled,queue.fingerprint_job,queue.validate_published
        queue.is_settled=lambda *a,**k: True; queue.fingerprint_job=lambda *a,**k: ('retro-fp',[]); queue.validate_published=lambda *a,**k: True
        try: retro_result=queue.process_candidate(cand,args,Path('unused-engine.py'),'engine-sha',{}, {})
        finally: queue.is_settled,queue.fingerprint_job,queue.validate_published=old_settle,old_fp,old_valid
        check(retro_result['status']=='skipped_exact_completed_auto_approved','retroactive_auto_without_rerender',checks)
        check((retro/'Approved'/'APPROVED_MANIFEST.json').is_file(),'retroactive_approved_created',checks)
        retro_state=json.loads(sp.read_text());check(retro_state['approval_policy']['status']=='AUTO_APPROVED','retroactive_state_persisted',checks)
        check((outbox/'LATEST_APPROVED.json').is_file(),'retroactive_global_pointer',checks)

        # V39 legacy failed state migrates to quarantine without invoking the engine.
        lout=td/'legacy-out'; lq=td/'legacy-queue'; lin=td/'legacy-in'; lout.mkdir();lq.mkdir();lin.mkdir()
        lsrc=td/'legacy-source.mp4';lsrc.write_bytes(b'legacy-source')
        lsp=lq/'jobs'/'legacy-job'/'job_state.json';lsp.parent.mkdir(parents=True)
        lsp.write_text(json.dumps({'candidate':'MEDENG_DROP_QUEUE_V39_RC1','job_id':'legacy-job','label':'legacy','fingerprint':'legacy-fp','status':'failed','attempt':1,'target_seconds':30,'error':'old failure'}))
        lcand=queue.CandidateJob(label='legacy',source_key='legacy/',files=[lsrc],batch_root=None,config_path=None)
        largs=SimpleNamespace(target_seconds=30,settle_seconds=0,require_batch_ready_marker=False,batch_settle_seconds=0,queue_root=lq,outbox=lout,per_file_timeout_s=1,job_hard_timeout_s=0)
        old_settle,old_fp=queue.is_settled,queue.fingerprint_job
        queue.is_settled=lambda *a,**k: True; queue.fingerprint_job=lambda *a,**k: ('legacy-fp',[])
        try: legacy_result=queue.process_candidate(lcand,largs,Path('must-not-run.py'),'engine-sha',{}, {})
        finally: queue.is_settled,queue.fingerprint_job=old_settle,old_fp
        legacy_state=json.loads(lsp.read_text())
        check(legacy_result['status']=='skipped_quarantined' and legacy_state['status']=='quarantined','legacy_failed_migrates_to_quarantine',checks)
        check((lq/'quarantine'/'legacy-job'/'attempt-1.json').is_file(),'legacy_quarantine_record_written',checks)

        # Quarantine records are durable; targeted retry requires exact fingerprint and is consumed atomically.
        qq=td/'qrec'; oo=td/'orec'; qq.mkdir(); oo.mkdir(); st={**ft1,'label':'fail','sources':[]}
        queue.write_quarantine_record(qq,oo,st)
        check((qq/'quarantine'/'fail-job'/'attempt-1.json').is_file() and (oo/'_Quarantine'/'fail-job.txt').is_file(),'quarantine_record_written',checks)
        sp2=qq/'jobs'/'fail-job'/'job_state.json';sp2.parent.mkdir(parents=True);sp2.write_text(json.dumps(st))
        (sp2.parent/'RETRY.request').write_text(json.dumps({'job_id':'fail-job','fingerprint':'wrong'}))
        ok,err=queue.consume_targeted_retry(sp2,st,'fail-fp',qq);check((not ok) and err=='fingerprint_mismatch' and (sp2.parent/'RETRY.request').is_file(),'retry_wrong_fingerprint_not_consumed',checks)
        (sp2.parent/'RETRY.request').write_text(json.dumps({'job_id':'fail-job','fingerprint':'fail-fp'}))
        ok,err=queue.consume_targeted_retry(sp2,st,'fail-fp',qq);check(ok and err is None and not (sp2.parent/'RETRY.request').exists(),'retry_exact_fingerprint_consumed',checks)
        check((sp2.parent/'RETRY.consumed.attempt-2.json').is_file(),'retry_consumption_audited',checks)
        queue.mark_quarantine_resolved(qq,oo,st)
        check((qq/'quarantine'/'fail-job'/'RESOLVED.json').is_file() and not (oo/'_Quarantine'/'fail-job.txt').exists(),'quarantine_resolution_recorded',checks)

        out={'candidate':'MEDENG_V42_PER_JOB_PACING_LOGIC_SELFTEST','status':'PASS','passed':sum(checks.values()),'total':len(checks),'checks':checks,'semantic_best_moment_claim':False}
        print(json.dumps(out,indent=2,sort_keys=True))
    finally:
        if a.keep_temp: print('temp='+str(td))
        else: shutil.rmtree(td,ignore_errors=True)
if __name__=='__main__': main()

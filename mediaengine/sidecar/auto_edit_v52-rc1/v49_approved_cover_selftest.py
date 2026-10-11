#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
    cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90,check=False)
    if cp.returncode:raise RuntimeError('CMD_FAIL:'+str(cp.returncode)+':'+cp.stderr[-1200:])

def make_reel(ff: str, path: Path, size: str, color: str):
    run([ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c={color}:size={size}:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',str(path)])

def output_rows(job:Path):
    rows=[]
    for profile,fn in [('16x9','reel_16x9.mp4'),('9x16','reel_9x16.mp4')]:
        p=job/fn;rows.append({'profile':profile,'filename':fn,'bytes':p.stat().st_size,'sha256':sha(p)})
    return rows

def write_job_result(job:Path, cover_mode:str='auto'):
    obj={'candidate':'MEDENG_DROP_QUEUE_V40_RC1','schema_version':1,'status':'PASS','job_id':job.name,'fingerprint':'fp-'+job.name,'semantic_selection_claim':False,'outputs':output_rows(job),'cover_assets':{'candidate':'MEDENG_COVER_ASSETS_V48_RC1','status':'PASS' if cover_mode=='auto' else 'OFF','cover_mode':cover_mode,'semantic_selection_claim':False}}
    (job/'JOB_RESULT.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args();root=Path(a.package_root);ff=str(Path(a.ffmpeg));os.environ['MEDENG_FFMPEG']=ff;sys.path.insert(0,str(root))
    approval=load('v49approval',root/'medeng_approval_v36.py');sys.modules['medeng_approval_v36']=approval
    auto=load('v49auto',root/'medeng_auto_approval_v39.py')
    checks=[]
    def ck(n,v,d=None):checks.append({'name':n,'pass':bool(v),**({'detail':d} if d is not None else {})});
    with tempfile.TemporaryDirectory(prefix='v49_approved_covers_') as td:
        td=Path(td);job=td/'job_auto';job.mkdir();make_reel(ff,job/'reel_16x9.mp4','960x540','red');make_reel(ff,job/'reel_9x16.mp4','540x960','blue');write_job_result(job,'auto')
        m1=approval.build(job,'auto');appr=job/'Approved';cmp=appr/'Covers'/'APPROVED_COVER_MANIFEST.json';cm=json.loads(cmp.read_text())
        ck('auto_approved_covers_pass',cm.get('status')=='PASS' and cm.get('candidate')=='MEDENG_APPROVED_COVERS_V49_RC1')
        ck('auto_two_covers',len(cm.get('covers') or [])==2)
        ck('auto_cover_dimensions',[(x['width'],x['height']) for x in cm['covers']]==[(960,540),(540,960)])
        ck('auto_cover_semantic_false',cm.get('semantic_selection_claim') is False)
        am=appr/'APPROVED_MANIFEST.json';am_sha=sha(am);fp=m1['approval_fingerprint'];reel_hashes={x['profile']:x['sha256'] for x in json.loads(am.read_text())['outputs']}
        ck('cover_source_binds_approved_reels',all(x['source_approved_reel_sha256']==reel_hashes[x['profile']] for x in cm['covers']))
        cover_hashes={x['profile']:x['sha256'] for x in cm['covers']}
        m2=approval.build(job,'auto');cm2=json.loads(cmp.read_text());ck('exact_resume_same_fingerprint',m2['approval_fingerprint']==fp);ck('exact_resume_cover_hashes',cover_hashes=={x['profile']:x['sha256'] for x in cm2['covers']})
        write_job_result(job,'off');m3=approval.build(job,'auto');ck('off_keeps_approval_fingerprint',m3['approval_fingerprint']==fp);ck('off_removes_managed_covers',not (appr/'Covers').exists());ck('off_keeps_approved_manifest_bytes',sha(am)==am_sha)
        write_job_result(job,'auto');r=auto.ensure(job,'auto');ck('auto_reconcile_status',r.get('status')=='SKIPPED_EXACT_AUTO',r);ck('auto_reconcile_recreates_covers',(appr/'Covers'/'APPROVED_COVER_MANIFEST.json').is_file());ck('auto_reconcile_no_approval_manifest_change',sha(am)==am_sha)
        # Human override: covers must bind to approved override reels, not AUTO reels.
        job2=td/'job_override';job2.mkdir();make_reel(ff,job2/'reel_16x9.mp4','960x540','black');make_reel(ff,job2/'reel_9x16.mp4','540x960','black');write_job_result(job2,'auto')
        rd=job2/'Override'/'renders'/'r1';rd.mkdir(parents=True);make_reel(ff,rd/'override_reel_16x9.mp4','960x540','green');make_reel(ff,rd/'override_reel_9x16.mp4','540x960','yellow')
        orows=[]
        for profile,fn in [('16x9','override_reel_16x9.mp4'),('9x16','override_reel_9x16.mp4')]:
            p=rd/fn;orows.append({'profile':profile,'filename':fn,'bytes':p.stat().st_size,'sha256':sha(p)})
        om={'candidate':'MEDENG_REVIEW_OVERRIDE_V36_RC1','schema_version':1,'status':'PASS','render_id':'r1','user_override':True,'semantic_selection_claim':False,'selection_mode':'EXPLICIT_HUMAN_EVENT_ID_ORDER','outputs':orows,'selected_events':[]}
        omp=rd/'OVERRIDE_MANIFEST.json';omp.write_text(json.dumps(om,indent=2));(job2/'Override'/'LATEST_OVERRIDE.json').write_text(json.dumps({'manifest':str(omp.resolve())}))
        hm=approval.build(job2,'latest-override');ham=json.loads((job2/'Approved'/'APPROVED_MANIFEST.json').read_text());hcm=json.loads((job2/'Approved'/'Covers'/'APPROVED_COVER_MANIFEST.json').read_text());h_reels={x['profile']:x['sha256'] for x in ham['outputs']}
        ck('override_approval_mode',hm.get('approval_mode')=='OVERRIDE')
        ck('override_covers_bind_override_reels',all(x['source_approved_reel_sha256']==h_reels[x['profile']] for x in hcm['covers']))
        auto_reels={x['profile']:x['sha256'] for x in output_rows(job2)};ck('override_covers_not_auto_reels',all(x['source_approved_reel_sha256']!=auto_reels[x['profile']] for x in hcm['covers']))
        ck('approval_manifest_has_only_reel_outputs',len(ham.get('outputs') or [])==2 and all(x['filename'].startswith('approved_reel_') for x in ham['outputs']))
        # Foreign Covers content is never deleted or overwritten.
        foreign=td/'foreign';foreign.mkdir();make_reel(ff,foreign/'approved_reel_16x9.mp4','960x540','purple');make_reel(ff,foreign/'approved_reel_9x16.mp4','540x960','orange');frows=[]
        for profile,fn in [('16x9','approved_reel_16x9.mp4'),('9x16','approved_reel_9x16.mp4')]:
            p=foreign/fn;frows.append({'profile':profile,'filename':fn,'bytes':p.stat().st_size,'sha256':sha(p)})
        (foreign/'Covers').mkdir();(foreign/'Covers'/'user.txt').write_text('foreign')
        try: approval.ensure_approved_covers(foreign,frows,'auto'); blocked=False
        except approval.ApprovalError as e: blocked='FOREIGN_CONTENT' in str(e)
        ck('foreign_covers_fail_closed',blocked)
    ok=all(x['pass'] for x in checks);print(json.dumps({'candidate':'MEDENG_APPROVED_COVERS_V49_SELFTEST','status':'PASS' if ok else 'FAIL','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()

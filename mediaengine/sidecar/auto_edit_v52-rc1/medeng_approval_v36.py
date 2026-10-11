#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path

CANDIDATE='MEDENG_APPROVAL_V36_RC1'
SCHEMA_VERSION=1
APPROVED_COVER_CANDIDATE='MEDENG_APPROVED_COVERS_V49_RC1'
APPROVED_COVER_POLICY='MIDPOINT_TECHNICAL_APPROVED_COVER_V49'


class ApprovalError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def atomic_json(path:Path,obj:object):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8')
    os.replace(tmp,path)

def atomic_text(path:Path,s:str):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp'); tmp.write_text(s,encoding='utf-8'); os.replace(tmp,path)

def atomic_copy(src:Path,dst:Path,expected_sha:str,expected_bytes:int):
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_name(dst.name+'.part'); tmp.unlink(missing_ok=True)
    shutil.copy2(src,tmp)
    if tmp.stat().st_size!=expected_bytes or sha256_file(tmp)!=expected_sha:
        tmp.unlink(missing_ok=True); raise ApprovalError(f'COPY_IDENTITY_MISMATCH:{src.name}')
    os.replace(tmp,dst)

def load_json(p:Path):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: raise ApprovalError(f'INVALID_JSON:{p}:{type(e).__name__}')

def validate_file(p:Path,sha:str,size:int):
    if not p.is_file(): raise ApprovalError(f'SOURCE_FILE_MISSING:{p}')
    if p.stat().st_size!=int(size): raise ApprovalError(f'SOURCE_SIZE_MISMATCH:{p.name}')
    actual=sha256_file(p)
    if actual!=sha: raise ApprovalError(f'SOURCE_SHA256_MISMATCH:{p.name}:{actual}')

def desired_cover_policy(job:Path)->tuple[str,float]:
    jp=job/'JOB_RESULT.json'
    if not jp.is_file(): return 'off',0.5
    try: jr=load_json(jp)
    except Exception: return 'off',0.5
    c=jr.get('cover_assets') or {}
    mode=str(c.get('cover_mode') or '').strip().lower()
    if mode not in ('off','auto'): mode='auto' if c.get('status')=='PASS' else 'off'
    try: pos=float(c.get('cover_position',0.5))
    except Exception: pos=0.5
    if not (0.0 <= pos <= 1.0): pos=0.5
    return mode,pos

def desired_cover_mode(job:Path)->str:
    return desired_cover_policy(job)[0]

def desired_cover_position(job:Path)->float:
    return desired_cover_policy(job)[1]

def _approved_cover_decode_ok(ffmpeg:str,path:Path)->bool:
    try:
        cp=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(path),'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30,check=False)
        return cp.returncode==0
    except Exception:
        return False

def _probe_media(ffmpeg:str,path:Path)->dict:
    # Reuse V41 FFmpeg-only probe; external ffprobe remains unnecessary.
    from medeng_media_probe_v41 import probe_json
    return probe_json(path,ffmpeg,30)

def ensure_approved_covers(approved:Path, outputs:list[dict], cover_mode:str, cover_position:float=0.5, ffmpeg:str|None=None)->dict:
    cover_mode=str(cover_mode or 'off').strip().lower()
    if cover_mode not in ('off','auto'): raise ApprovalError('APPROVED_COVER_MODE_INVALID')
    try: cover_position=float(cover_position)
    except Exception: raise ApprovalError('APPROVED_COVER_POSITION_INVALID')
    if not (0.0 <= cover_position <= 1.0): raise ApprovalError('APPROVED_COVER_POSITION_RANGE_0_1')
    root=approved/'Covers'; mp=root/'APPROVED_COVER_MANIFEST.json'
    if cover_mode=='off':
        if root.exists():
            known=False
            if mp.is_file():
                try: known=load_json(mp).get('candidate')==APPROVED_COVER_CANDIDATE
                except Exception: known=False
            if not known: raise ApprovalError('APPROVED_COVERS_FOREIGN_CONTENT')
            shutil.rmtree(root)
            return {'candidate':APPROVED_COVER_CANDIDATE,'status':'OFF','cover_mode':'off','cover_position':cover_position,'mutated':True,'semantic_selection_claim':False}
        return {'candidate':APPROVED_COVER_CANDIDATE,'status':'OFF','cover_mode':'off','cover_position':cover_position,'mutated':False,'semantic_selection_claim':False}
    ffmpeg=str(ffmpeg or os.environ.get('MEDENG_FFMPEG') or 'ffmpeg')
    expected=[]
    for o in sorted(outputs,key=lambda x:str(x.get('profile'))):
        profile=str(o.get('profile') or '');fn=str(o.get('filename') or '');src=approved/fn
        if profile not in ('16x9','9x16') or not fn: raise ApprovalError('APPROVED_COVER_SOURCE_INVALID:'+profile)
        validate_file(src,str(o.get('sha256') or ''),int(o.get('bytes') or -1));expected.append((profile,src,str(o.get('sha256'))))
    if len(expected)!=2: raise ApprovalError('APPROVED_COVER_EXPECTED_TWO_REELS')
    if mp.is_file():
        try:
            old=load_json(mp);rows=old.get('covers') or []
            if old.get('candidate')==APPROVED_COVER_CANDIDATE and old.get('status')=='PASS' and abs(float(old.get('cover_position',0.5))-cover_position)<=1e-9 and len(rows)==2:
                good=True
                for r in rows:
                    cp=root/str(r.get('filename') or '');src=next((x for x in expected if x[0]==str(r.get('profile'))),None)
                    if not src or str(r.get('source_approved_reel_sha256'))!=src[2] or not cp.is_file() or cp.stat().st_size!=int(r.get('bytes') or -1) or sha256_file(cp)!=str(r.get('sha256') or '') or not _approved_cover_decode_ok(ffmpeg,cp): good=False;break
                if good:
                    old=dict(old);old['resume_status']='SKIPPED_EXACT_COMPLETED';old['mutated']=False;return old
        except Exception:
            pass
    if root.exists():
        known=False
        if mp.is_file():
            try: known=load_json(mp).get('candidate')==APPROVED_COVER_CANDIDATE
            except Exception: known=False
        if not known: raise ApprovalError('APPROVED_COVERS_FOREIGN_CONTENT')
    tmp=approved/f'.Covers.tmp.{os.getpid()}.{int(time.time()*1000)}'
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    rows=[]
    try:
        for profile,src,source_sha in expected:
            pr=_probe_media(ffmpeg,src);dur=float((pr.get('format') or {}).get('duration') or 0.0)
            if dur<=0: raise ApprovalError('APPROVED_COVER_SOURCE_DURATION_INVALID:'+profile)
            ss=min(max(0.0,dur*cover_position),max(0.0,dur-0.05));dst=tmp/f'cover_{profile}.jpg'
            cp=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',f'{ss:.3f}','-i',str(src),'-frames:v','1','-q:v','2',str(dst)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60,check=False)
            if cp.returncode!=0 or not dst.is_file() or dst.stat().st_size<=1000 or not _approved_cover_decode_ok(ffmpeg,dst):
                raise ApprovalError('APPROVED_COVER_EXTRACT_FAILED:'+profile+':'+(cp.stderr or b'')[-500:].decode('utf-8','replace'))
            dpr=_probe_media(ffmpeg,dst);vs=next((x for x in dpr.get('streams',[]) if x.get('codec_type')=='video'),{})
            rows.append({'profile':profile,'filename':dst.name,'bytes':dst.stat().st_size,'sha256':sha256_file(dst),'source_approved_reel_sha256':source_sha,'source_duration_s':dur,'cover_position':cover_position,'extraction_time_s':round(ss,3),'width':int(vs.get('width') or 0),'height':int(vs.get('height') or 0)})
        manifest={'candidate':APPROVED_COVER_CANDIDATE,'schema_version':1,'status':'PASS','cover_mode':'auto','cover_position':cover_position,'selection_policy':'POSITIONAL_TECHNICAL_APPROVED_COVER_V50','semantic_selection_claim':False,'covers':rows,'mutated':True,'updated_at_unix':time.time()}
        atomic_json(tmp/'APPROVED_COVER_MANIFEST.json',manifest)
        if root.exists(): shutil.rmtree(root)
        os.replace(tmp,root)
        return manifest
    except Exception:
        if tmp.exists(): shutil.rmtree(tmp,ignore_errors=True)
        raise

def source_auto(job:Path):
    jr=load_json(job/'JOB_RESULT.json')
    if jr.get('status')!='PASS': raise ApprovalError('JOB_RESULT_NOT_PASS')
    outputs=[]
    for rec in jr.get('outputs') or []:
        profile=rec.get('profile'); fn=rec.get('filename'); sha=rec.get('sha256'); size=rec.get('bytes')
        if profile not in ('16x9','9x16') or not fn or not sha or not size: continue
        p=job/fn; validate_file(p,sha,int(size)); outputs.append({'profile':profile,'path':p,'filename':fn,'sha256':sha,'bytes':int(size)})
    if {x['profile'] for x in outputs}!={'16x9','9x16'}: raise ApprovalError('AUTO_OUTPUT_PAIR_INCOMPLETE')
    return {'mode':'AUTO','source_manifest':job/'JOB_RESULT.json','source_id':str(jr.get('fingerprint') or jr.get('job_id') or ''),'outputs':outputs,'semantic_selection_claim':bool(jr.get('semantic_selection_claim',False))}

def source_override(job:Path):
    lp=job/'Override'/'LATEST_OVERRIDE.json'
    if not lp.is_file(): raise ApprovalError('LATEST_OVERRIDE_MISSING')
    latest=load_json(lp); mp=Path(str(latest.get('manifest') or ''))
    # Only accept a manifest physically under this job's Override/renders tree.
    try: mp_res=mp.resolve(); allowed=(job/'Override'/'renders').resolve(); mp_res.relative_to(allowed)
    except Exception: raise ApprovalError('LATEST_OVERRIDE_MANIFEST_OUTSIDE_JOB')
    if not mp.is_file(): raise ApprovalError('LATEST_OVERRIDE_MANIFEST_MISSING')
    m=load_json(mp)
    if m.get('status')!='PASS' or not m.get('user_override') or m.get('selection_mode')!='EXPLICIT_HUMAN_EVENT_ID_ORDER':
        raise ApprovalError('LATEST_OVERRIDE_NOT_APPROVABLE')
    outputs=[]
    for rec in m.get('outputs') or []:
        profile=rec.get('profile'); fn=rec.get('filename'); sha=rec.get('sha256'); size=rec.get('bytes')
        if profile not in ('16x9','9x16') or not fn or not sha or not size: continue
        p=mp.parent/fn; validate_file(p,sha,int(size)); outputs.append({'profile':profile,'path':p,'filename':fn,'sha256':sha,'bytes':int(size)})
    if {x['profile'] for x in outputs}!={'16x9','9x16'}: raise ApprovalError('OVERRIDE_OUTPUT_PAIR_INCOMPLETE')
    return {'mode':'OVERRIDE','source_manifest':mp,'source_id':str(m.get('render_id') or ''),'outputs':outputs,'semantic_selection_claim':bool(m.get('semantic_selection_claim',False)),'selected_events':m.get('selected_events') or []}

def source_alternative(job:Path, strategy_key:str):
    strategy_key=str(strategy_key).upper()
    if strategy_key not in ('ALT_A','ALT_B'): raise ApprovalError('ALTERNATIVE_STRATEGY_INVALID')
    lp=job/'Alternatives'/'LATEST_ALTERNATIVES.json'
    if not lp.is_file(): raise ApprovalError('LATEST_ALTERNATIVES_MISSING')
    latest=load_json(lp)
    rec=next((x for x in (latest.get('variants') or []) if str(x.get('strategy_key')).upper()==strategy_key),None)
    if not rec: raise ApprovalError('ALTERNATIVE_NOT_AVAILABLE:'+strategy_key)
    vid=str(rec.get('variant_id') or '')
    mp=job/'Alternatives'/'variants'/vid/'VARIANT_MANIFEST.json'
    try:
        mp.resolve().relative_to((job/'Alternatives'/'variants').resolve())
    except Exception:
        raise ApprovalError('ALTERNATIVE_MANIFEST_OUTSIDE_JOB')
    if not mp.is_file(): raise ApprovalError('ALTERNATIVE_MANIFEST_MISSING')
    m=load_json(mp)
    if m.get('candidate')!='MEDENG_AUTO_VARIANTS_V36_RC1' or m.get('status')!='PASS' or m.get('strategy_key')!=strategy_key or m.get('variant_id')!=vid:
        raise ApprovalError('ALTERNATIVE_MANIFEST_INVALID')
    outputs=[]
    for rec2 in m.get('outputs') or []:
        profile=rec2.get('profile'); fn=rec2.get('filename'); sha=rec2.get('sha256'); size=rec2.get('bytes')
        if profile not in ('16x9','9x16') or not fn or not sha or not size: continue
        p=mp.parent/fn; validate_file(p,sha,int(size)); outputs.append({'profile':profile,'path':p,'filename':fn,'sha256':sha,'bytes':int(size)})
    if {x['profile'] for x in outputs}!={'16x9','9x16'}: raise ApprovalError('ALTERNATIVE_OUTPUT_PAIR_INCOMPLETE')
    return {'mode':'ALTERNATIVE_'+strategy_key,'source_manifest':mp,'source_id':vid,'outputs':outputs,'semantic_selection_claim':False,'selected_events':m.get('selected_events') or []}

def approval_fingerprint(src:dict)->str:
    h=hashlib.sha256()
    h.update(src['mode'].encode()); h.update(b'\0'); h.update(src['source_id'].encode()); h.update(b'\0')
    for r in sorted(src['outputs'],key=lambda x:x['profile']):
        h.update(r['profile'].encode());h.update(b'\0');h.update(r['sha256'].encode());h.update(b'\0')
    return h.hexdigest()

def existing_approved_manifest(approved:Path)->dict|None:
    mp=approved/'APPROVED_MANIFEST.json'
    if not mp.is_file(): return None
    try: m=load_json(mp)
    except Exception: return None
    if m.get('candidate')!=CANDIDATE or m.get('status')!='PASS': return None
    rows=m.get('outputs') or []
    if len(rows)!=2 or {str(x.get('profile')) for x in rows}!={'16x9','9x16'}: return None
    try:
        for r in rows: validate_file(approved/str(r.get('filename') or ''),str(r.get('sha256') or ''),int(r.get('bytes') or -1))
    except Exception: return None
    return m

def current_exact(approved:Path,fp:str)->dict|None:
    m=existing_approved_manifest(approved)
    if not m or m.get('approval_fingerprint')!=fp:return None
    m['resume_status']='SKIPPED_EXACT_COMPLETED';return m

def build(job:Path,mode:str,global_pointer:Path|None=None):
    job=job.resolve()
    if not job.is_dir(): raise ApprovalError('JOB_OUTDIR_MISSING')
    if mode=='auto': src=source_auto(job)
    elif mode=='latest-override': src=source_override(job)
    elif mode=='alt-a': src=source_alternative(job,'ALT_A')
    elif mode=='alt-b': src=source_alternative(job,'ALT_B')
    else: raise ApprovalError('APPROVAL_MODE_INVALID')
    fp=approval_fingerprint(src); approved=job/'Approved'
    exact=current_exact(approved,fp)
    if exact:
        _cm,_cp=desired_cover_policy(job); exact['cover_assets']=ensure_approved_covers(approved,exact.get('outputs') or [],_cm,_cp)
        if global_pointer: atomic_json(global_pointer,{'candidate':CANDIDATE,'job_outdir':str(job),'approved_manifest':str((approved/'APPROVED_MANIFEST.json').resolve()),'approval_fingerprint':fp,'updated_at_unix':time.time()})
        return exact
    # If an existing approval is valid or partially present, preserve it before replacement.
    if approved.exists():
        hist=job/'_ApprovedHistory';hist.mkdir(exist_ok=True)
        dst=hist/f'Approved.{int(time.time())}.{os.getpid()}'
        os.replace(approved,dst)
    tmp=job/f'.Approved.tmp.{os.getpid()}.{int(time.time()*1000)}';tmp.mkdir(parents=True)
    outputs=[]
    for rec in src['outputs']:
        fn=f"approved_reel_{rec['profile']}.mp4"
        dst=tmp/fn;atomic_copy(rec['path'],dst,rec['sha256'],rec['bytes'])
        outputs.append({'profile':rec['profile'],'filename':fn,'bytes':dst.stat().st_size,'sha256':sha256_file(dst)})
    _cm,_cp=desired_cover_policy(job); cover_assets=ensure_approved_covers(tmp,outputs,_cm,_cp)
    source_manifest_sha=sha256_file(src['source_manifest'])
    m={'candidate':CANDIDATE,'schema_version':SCHEMA_VERSION,'status':'PASS','approval_mode':src['mode'],'approval_fingerprint':fp,'source_id':src['source_id'],'source_manifest':str(src['source_manifest']),'source_manifest_sha256':source_manifest_sha,'semantic_selection_claim':src.get('semantic_selection_claim',False),'outputs':outputs,'approved_at_unix':time.time(),'original_automatic_reels_overwritten':False}
    if src.get('selected_events') is not None:m['selected_events']=src['selected_events']
    atomic_json(tmp/'APPROVED_MANIFEST.json',m)
    atomic_text(tmp/'APPROVED.txt',f"MediaEngine Approved Delivery\nMode: {src['mode']}\nApproval fingerprint: {fp}\n16:9: approved_reel_16x9.mp4\n9:16: approved_reel_9x16.mp4\nOriginal automatic and override reels remain unchanged.\n")
    os.replace(tmp,approved)
    if global_pointer:atomic_json(global_pointer,{'candidate':CANDIDATE,'job_outdir':str(job),'approved_manifest':str((approved/'APPROVED_MANIFEST.json').resolve()),'approval_fingerprint':fp,'updated_at_unix':time.time()})
    m['cover_assets']=cover_assets
    return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--job-outdir',required=True);ap.add_argument('--mode',choices=['auto','latest-override','alt-a','alt-b'],required=True);ap.add_argument('--global-pointer')
    a=ap.parse_args();m=build(Path(a.job_outdir),a.mode,Path(a.global_pointer) if a.global_pointer else None)
    print(json.dumps({'candidate':m['candidate'],'status':m['status'],'approval_mode':m['approval_mode'],'approval_fingerprint':m['approval_fingerprint'],'outputs':m['outputs'],'resume_status':m.get('resume_status')},indent=2))
if __name__=='__main__':main()

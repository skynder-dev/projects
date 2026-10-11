#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path
import cv2
import numpy as np

CANDIDATE='MEDENG_V44_VERTICAL_FRAMING_CONTRACT'

def load(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def frame_at(path: Path, sec: float):
    cap=cv2.VideoCapture(str(path)); cap.set(cv2.CAP_PROP_POS_MSEC,max(0.0,sec)*1000.0); ok,fr=cap.read(); cap.release()
    if not ok: raise RuntimeError(f'FRAME_READ_FAILED:{path}:{sec}')
    return fr

def lap_var(img):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); return float(cv2.Laplacian(g,cv2.CV_64F).var())

def black_frac(img):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); return float((g<8).mean())

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ffmpeg',required=True); ap.add_argument('--package-root',required=True); a=ap.parse_args()
    root=Path(a.package_root).resolve(); ff=Path(a.ffmpeg).resolve()
    if not ff.is_file(): raise SystemExit('FFMPEG_MISSING')
    os.environ['MEDENG_FFMPEG']=str(ff); os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.path.insert(0,str(root))
    q=load('v44_q',root/'medeng_drop_queue_v40.py'); core=load('v44_core',root/'medeng_targeted_auto_edit_v26.py')
    checks=[]
    def ck(name, cond, detail=None): checks.append({'name':name,'pass':bool(cond),**({'detail':detail} if detail is not None else {})});
    def cfgrow(obj, media, engine_sha):
        p=media.parent/'AUTO_EDIT.json'; p.write_text(json.dumps(obj),encoding='utf-8')
        try:
            cfg,csha,rsha=q.load_job_config(p,15.0,False); job=q.CandidateJob(label='v44',source_key='fixture.mp4',files=[media]); fp,_=q.fingerprint_job(job,float(cfg['target_seconds']),engine_sha,{},rsha)
            return {'ok':True,'cfg':cfg,'config_sha256':csha,'render_sha256':rsha,'fingerprint':fp}
        except Exception as e: return {'ok':False,'error':str(e)}
    with tempfile.TemporaryDirectory(prefix='medeng_v44_selftest_') as td:
        td=Path(td); src=td/'fixture.mp4'
        cmd=[str(ff),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','6','-shortest','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',str(src)]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90); ck('fixture_encode',cp.returncode==0 and src.is_file() and src.stat().st_size>100000,(cp.stderr or '')[-600:])
        engine_sha=q.sha256_file(root/'medeng_video_to_reel_v26.py')
        omitted=cfgrow({'schema_version':1,'target_seconds':15},src,engine_sha)
        fill=cfgrow({'schema_version':1,'target_seconds':15,'vertical_framing':'fill'},src,engine_sha)
        blur=cfgrow({'schema_version':1,'target_seconds':15,'vertical_framing':'fit_blur'},src,engine_sha)
        auto=cfgrow({'schema_version':1,'target_seconds':15,'approval_mode':'auto'},src,engine_sha)
        invalid=cfgrow({'schema_version':1,'target_seconds':15,'vertical_framing':'smart_magic'},src,engine_sha)
        ck('omitted_defaults_fill',omitted['ok'] and omitted['cfg'].get('vertical_framing')=='fill')
        ck('explicit_fill_accepted',fill['ok'] and fill['cfg'].get('vertical_framing')=='fill')
        ck('omitted_explicit_fill_same_config',omitted.get('config_sha256')==fill.get('config_sha256'))
        ck('omitted_explicit_fill_same_fingerprint',omitted.get('fingerprint')==fill.get('fingerprint'))
        ck('default_render_policy_legacy_none',omitted.get('render_sha256') is None)
        ck('fit_blur_accepted',blur['ok'] and blur['cfg'].get('vertical_framing')=='fit_blur')
        ck('fit_blur_render_identity_material',bool(blur.get('render_sha256')))
        ck('fit_blur_fingerprint_changes',blur.get('fingerprint')!=fill.get('fingerprint'))
        ck('approval_policy_not_render_identity',auto.get('fingerprint')==fill.get('fingerprint'))
        ck('invalid_framing_fails_closed',not invalid['ok'] and 'VERTICAL_FRAMING' in invalid.get('error',''))
        event={'clip_path':str(src),'clip_sha256':core.sha256_file(src),'duration_s':6.0,'v22_metrics':{'saliency_cx':0.82,'saliency_cy':0.48}}
        fdir=td/'fill'; bdir=td/'blur'; fdir.mkdir(); bdir.mkdir()
        f16=core.make_segment(event,fdir/'16x9.mp4','16x9',5.0,-18.0,-2.0,'fill'); f9=core.make_segment(event,fdir/'9x16.mp4','9x16',5.0,-18.0,-2.0,'fill')
        b16=core.make_segment(event,bdir/'16x9.mp4','16x9',5.0,-18.0,-2.0,'fit_blur'); b9=core.make_segment(event,bdir/'9x16.mp4','9x16',5.0,-18.0,-2.0,'fit_blur')
        core.full_decode(Path(f16['path'])); core.full_decode(Path(f9['path'])); core.full_decode(Path(b16['path'])); core.full_decode(Path(b9['path']))
        ck('fill_16x9_byte_compatible',f16['sha256']==b16['sha256'])
        ck('fit_blur_changes_only_vertical_bytes',f9['sha256']!=b9['sha256'])
        ck('fill_vertical_is_smart_crop',f9['crop'].get('presentation')=='SMART_SALIENCY_CROP')
        ck('fit_blur_vertical_metadata',b9['crop'].get('presentation')=='FULL_FRAME_FIT_BLUR_BACKGROUND')
        pr=core.ffprobe(Path(b9['path'])); vs=[x for x in pr.get('streams',[]) if x.get('codec_type')=='video']; aus=[x for x in pr.get('streams',[]) if x.get('codec_type')=='audio']
        ck('fit_blur_vertical_dimensions',bool(vs) and int(vs[0].get('width',0))==540 and int(vs[0].get('height',0))==960,vs[0] if vs else None)
        ck('fit_blur_audio_preserved',bool(aus))
        ck('fit_blur_duration_5s',abs(float(b9['duration_s'])-5.0)<=0.05,b9['duration_s'])
        sframe=frame_at(src,3.0); oframe=frame_at(Path(b9['path']),2.5); fg_h=int(round(720*540/1280)); y0=(960-fg_h)//2
        expected=cv2.resize(sframe,(540,fg_h),interpolation=cv2.INTER_AREA); foreground=oframe[y0:y0+fg_h]
        mae=float(np.mean(np.abs(foreground.astype(np.float32)-expected.astype(np.float32))))
        top=oframe[:y0]; bottom=oframe[y0+fg_h:]; fg_lap=lap_var(foreground); top_lap=lap_var(top); bottom_lap=lap_var(bottom); top_black=black_frac(top); bottom_black=black_frac(bottom)
        ck('fit_blur_full_frame_foreground_preserved',mae<12.0,{'mae_0_255':round(mae,4),'foreground_height':fg_h,'y0':y0})
        ck('fit_blur_no_black_top',top_black<0.02,round(top_black,6)); ck('fit_blur_no_black_bottom',bottom_black<0.02,round(bottom_black,6))
        ck('fit_blur_background_visibly_blurred',max(top_lap,bottom_lap)<max(5.0,fg_lap*0.20),{'foreground_laplacian_variance':round(fg_lap,4),'top':round(top_lap,4),'bottom':round(bottom_lap,4)})
        passed=sum(1 for x in checks if x['pass']); out={'candidate':CANDIDATE,'status':'PASS' if passed==len(checks) else 'FAIL','passed':passed,'total':len(checks),'checks':checks,'semantic_selection_claim':False,'default_vertical_framing':'fill','optional_vertical_framing':'fit_blur'}
        print(json.dumps(out,indent=2)); raise SystemExit(0 if passed==len(checks) else 3)
if __name__=='__main__': main()

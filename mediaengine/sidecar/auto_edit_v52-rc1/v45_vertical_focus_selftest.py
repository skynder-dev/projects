#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import cv2
import numpy as np

CANDIDATE='MEDENG_VERTICAL_FOCUS_V45_RC1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ffmpeg',required=True); ap.add_argument('--package-root',required=True); a=ap.parse_args()
    root=Path(a.package_root).resolve(); ff=str(Path(a.ffmpeg).resolve())
    sys.path.insert(0,str(root));
    q=load('q45_focus',root/'medeng_drop_queue_v40.py'); c45=load('c45_focus',root/'medeng_targeted_auto_edit_v26.py')
    c45.FFMPEG=ff
    checks=[]
    def ck(name,ok,detail=None): checks.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail is not None else {})})
    def cfgrow(obj):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'AUTO_EDIT.json'; p.write_text(json.dumps(obj),encoding='utf-8')
            try:
                cfg,full,render=q.load_job_config(p,30.0,False); return {'ok':True,'cfg':cfg,'full':full,'render':render}
            except Exception as e: return {'ok':False,'error':str(e)}
    omitted=cfgrow({'schema_version':1,'target_seconds':30})
    mid=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':0.5})
    left=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':0.0})
    right=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':1.0})
    policy=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':0.0,'approval_mode':'auto','max_attempts':3,'retry_backoff_seconds':7})
    badlo=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':-0.01})
    badhi=cfgrow({'schema_version':1,'target_seconds':30,'vertical_focus_x':1.01})
    badblur=cfgrow({'schema_version':1,'target_seconds':30,'vertical_framing':'fit_blur','vertical_focus_x':0.2})
    ck('omitted_focus_default_half',omitted['ok'] and omitted['cfg']['vertical_focus_x']==0.5)
    ck('explicit_half_render_identity_same',mid['ok'] and mid['render']==omitted['render'])
    ck('left_render_identity_distinct',left['ok'] and left['render'] and left['render']!=omitted['render'])
    ck('right_render_identity_distinct',right['ok'] and right['render'] and right['render']!=left['render'])
    ck('policy_only_same_render_identity',policy['ok'] and policy['render']==left['render'])
    ck('focus_below_zero_fail_closed',not badlo['ok'] and 'VERTICAL_FOCUS_X_RANGE' in badlo.get('error',''),badlo)
    ck('focus_above_one_fail_closed',not badhi['ok'] and 'VERTICAL_FOCUS_X_RANGE' in badhi.get('error',''),badhi)
    ck('fit_blur_nondefault_focus_fail_closed',not badblur['ok'] and 'REQUIRES_FILL' in badblur.get('error',''),badblur)

    event={'clip_path':'x.mp4','duration_s':6.0,'v22_metrics':{'saliency_cx':0.5,'saliency_cy':0.5}}
    x0=c45.smart_crop_geometry(event,1280,720,0.0); xm=c45.smart_crop_geometry(event,1280,720,0.5); x1=c45.smart_crop_geometry(event,1280,720,1.0)
    ck('default_geometry_v44_compatible_expected',xm==(438,0,404,720),xm)
    ck('focus_left_hits_left_edge',x0[0]==0,x0)
    ck('focus_right_hits_right_edge',x1[0]==1280-x1[2],x1)
    ck('focus_order_monotonic',x0[0] < xm[0] < x1[0],{'left':x0[0],'auto':xm[0],'right':x1[0]})

    with tempfile.TemporaryDirectory(prefix='v45_focus_') as td:
        td=Path(td); src=td/'rgb.mp4'
        cmd=[ff,'-hide_banner','-loglevel','error','-y',
             '-f','lavfi','-i','color=c=red:s=426x720:r=30:d=6',
             '-f','lavfi','-i','color=c=green:s=428x720:r=30:d=6',
             '-f','lavfi','-i','color=c=blue:s=426x720:r=30:d=6',
             '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=6',
             '-filter_complex','[0:v][1:v][2:v]hstack=inputs=3[v]', '-map','[v]','-map','3:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        if cp.returncode: raise RuntimeError(cp.stderr[-4000:])
        event={'clip_path':str(src),'clip_sha256':sha(src),'event_id':'rgb','source_name':'rgb.mp4','duration_s':6.0,'v22_metrics':{'saliency_cx':0.5,'saliency_cy':0.5}}
        v45i=td/'v45_implicit.mp4'; v45m=td/'v45_default.mp4'; v45l=td/'v45_left.mp4'; v45r=td/'v45_right.mp4'; h45=td/'v45_horiz.mp4'; h45r=td/'v45_horiz_right.mp4'
        mi=c45.make_segment(event,v45i,'9x16',5.0,-18.0,-2.0,'fill')
        mm=c45.make_segment(event,v45m,'9x16',5.0,-18.0,-2.0,'fill',0.5)
        ml=c45.make_segment(event,v45l,'9x16',5.0,-18.0,-2.0,'fill',0.0)
        mr=c45.make_segment(event,v45r,'9x16',5.0,-18.0,-2.0,'fill',1.0)
        mh=c45.make_segment(event,h45,'16x9',5.0,-18.0,-2.0,'fill',0.5)
        mhr=c45.make_segment(event,h45r,'16x9',5.0,-18.0,-2.0,'fill',1.0)
        ck('implicit_default_equals_explicit_half_bytes',sha(v45i)==sha(v45m),{'implicit':sha(v45i),'half':sha(v45m)})
        ck('left_right_9x16_distinct',sha(v45l)!=sha(v45r),{'left':sha(v45l),'right':sha(v45r)})
        ck('focus_does_not_change_16x9',sha(h45)==sha(h45r),{'default':sha(h45),'right':sha(h45r)})
        ck('left_crop_metadata_zero',ml['crop'].get('x')==0 and ml['crop'].get('vertical_focus_x')==0.0,ml['crop'])
        ck('right_crop_metadata_right_edge',mr['crop'].get('x')==1280-mr['crop'].get('w') and mr['crop'].get('vertical_focus_x')==1.0,mr['crop'])
        def mean_frame(path):
            cap=cv2.VideoCapture(str(path)); cap.set(cv2.CAP_PROP_POS_MSEC,1000); ok,fr=cap.read(); cap.release()
            if not ok: raise RuntimeError('frame read failed')
            return fr.reshape(-1,3).mean(0) # B,G,R
        L=mean_frame(v45l); R=mean_frame(v45r)
        ck('pixel_left_is_red_dominant',L[2]>L[0]*2 and L[2]>L[1]*2,{'bgr':[round(float(x),2) for x in L]})
        ck('pixel_right_is_blue_dominant',R[0]>R[2]*2 and R[0]>R[1]*2,{'bgr':[round(float(x),2) for x in R]})
    passed=sum(1 for x in checks if x['pass']); out={'candidate':CANDIDATE,'status':'PASS' if passed==len(checks) else 'FAIL','passed':passed,'total':len(checks),'checks':checks,'semantic_selection_claim':False,'default_vertical_focus_x':0.5,'focus_semantics':'0.5=current smart crop; 0=left edge; 1=right edge; intermediate=blend'}
    print(json.dumps(out,indent=2))
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()

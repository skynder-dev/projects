#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,subprocess,sys,tempfile
from fractions import Fraction
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fps_value(stream):
    raw=str(stream.get('r_frame_rate') or stream.get('avg_frame_rate') or '0/1')
    try:return float(Fraction(raw))
    except Exception:return 0.0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args()
    root=Path(a.package_root).resolve();ff=str(Path(a.ffmpeg).resolve());sys.path.insert(0,str(root))
    q=load('q51_fps',root/'medeng_drop_queue_v40.py');c=load('c51_fps',root/'medeng_targeted_auto_edit_v26.py');c.FFMPEG=ff
    checks=[]
    def ck(n,ok,d=None):checks.append({'name':n,'pass':bool(ok),**({'detail':d} if d is not None else {})})
    def cfgrow(obj):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'AUTO_EDIT.json';p.write_text(json.dumps(obj))
            try:cfg,full,render=q.load_job_config(p,30.0,False);return {'ok':True,'cfg':cfg,'full':full,'render':render}
            except Exception as e:return {'ok':False,'error':str(e)}
    omitted=cfgrow({'schema_version':1,'target_seconds':30})
    f30=cfgrow({'schema_version':1,'target_seconds':30,'output_fps':30})
    f60=cfgrow({'schema_version':1,'target_seconds':30,'output_fps':60})
    policy=cfgrow({'schema_version':1,'target_seconds':30,'output_fps':60,'approval_mode':'auto','max_attempts':3})
    bad=cfgrow({'schema_version':1,'target_seconds':30,'output_fps':24})
    ck('omitted_default_30',omitted['ok'] and omitted['cfg']['output_fps']==30)
    ck('explicit_30_render_identity_same',f30['ok'] and f30['render']==omitted['render'])
    ck('60_render_identity_distinct',f60['ok'] and f60['render'] and f60['render']!=omitted['render'])
    ck('policy_only_60_identity_same',policy['ok'] and policy['render']==f60['render'])
    ck('invalid_24_fail_closed',not bad['ok'] and 'OUTPUT_FPS' in bad.get('error',''),bad)
    with tempfile.TemporaryDirectory(prefix='v51_fps_') as td:
        td=Path(td);src=td/'src.mp4'
        cmd=[ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=60:duration=2.4','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2.4','-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90);assert cp.returncode==0,cp.stderr
        ev={'clip_path':str(src),'clip_sha256':sha(src),'event_id':'src','source_name':'src.mp4','duration_s':2.4,'v22_metrics':{'saliency_cx':0.55,'saliency_cy':0.5}}
        _,_,_,vf30,_,_=c.segment_spec(ev,'9x16',1.8,'fill',0.5,'standard',30)
        _,_,_,vf60,_,_=c.segment_spec(ev,'9x16',1.8,'fill',0.5,'standard',60)
        _,_,_,vf60blur,_,_=c.segment_spec(ev,'9x16',1.8,'fit_blur',0.5,'social_hd',60)
        ck('filter_30_contract','fps=30' in vf30)
        ck('filter_60_contract','fps=60' in vf60)
        ck('fit_blur_60_contract','fps=60' in vf60blur and '1080:1920' in vf60blur)
        p30=td/'30_9.mp4';p60=td/'60_9.mp4';p60h=td/'60_16_hd.mp4'
        m30=c.make_segment(ev,p30,'9x16',1.8,-18,-2,'fill',0.5,'standard','source',30)
        m60=c.make_segment(ev,p60,'9x16',1.8,-18,-2,'fill',0.5,'standard','source',60)
        mh=c.make_segment(ev,p60h,'16x9',1.8,-18,-2,'fill',0.5,'social_hd','source',60)
        def vstream(p):return next(x for x in c.ffprobe(p)['streams'] if x.get('codec_type')=='video')
        s30,s60,sh=vstream(p30),vstream(p60),vstream(p60h)
        ck('real_30fps_encode',abs(fps_value(s30)-30.0)<0.1,s30)
        ck('real_60fps_encode',abs(fps_value(s60)-60.0)<0.1,s60)
        ck('social_hd_60fps_encode',abs(fps_value(sh)-60.0)<0.1 and (int(sh['width']),int(sh['height']))==(1920,1080),sh)
        ck('60_bytes_distinct_30',sha(p60)!=sha(p30))
        ck('60_segment_metadata',m60.get('output_fps')==60 and m60.get('identity',{}).get('output_fps')==60,m60)
        ck('30_segment_metadata_default_omitted','output_fps' not in m30 and 'output_fps' not in m30.get('identity',{}),m30)
    passed=sum(1 for x in checks if x['pass'])
    out={'candidate':'MEDENG_OUTPUT_FPS_V51_RC1','status':'PASS' if passed==len(checks) else 'FAIL','passed':passed,'total':len(checks),'checks':checks,'default_output_fps':30,'alternate_output_fps':60,'semantic_selection_claim':False}
    print(json.dumps(out,indent=2));raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args()
    root=Path(a.package_root).resolve();ff=str(Path(a.ffmpeg).resolve());sys.path.insert(0,str(root))
    q=load('q52_quality',root/'medeng_drop_queue_v40.py');c=load('c52_quality',root/'medeng_targeted_auto_edit_v26.py');c.FFMPEG=ff
    checks=[]
    def ck(n,ok,d=None):checks.append({'name':n,'pass':bool(ok),**({'detail':d} if d is not None else {})})
    def cfgrow(obj):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'AUTO_EDIT.json';p.write_text(json.dumps(obj))
            try:cfg,full,render=q.load_job_config(p,30.0,False);return {'ok':True,'cfg':cfg,'full':full,'render':render}
            except Exception as e:return {'ok':False,'error':str(e)}
    omitted=cfgrow({'schema_version':1,'target_seconds':30})
    standard=cfgrow({'schema_version':1,'target_seconds':30,'video_quality':'standard'})
    high=cfgrow({'schema_version':1,'target_seconds':30,'video_quality':'high'})
    policy=cfgrow({'schema_version':1,'target_seconds':30,'video_quality':'high','approval_mode':'auto','max_attempts':3})
    bad=cfgrow({'schema_version':1,'target_seconds':30,'video_quality':'ultra'})
    ck('omitted_default_standard',omitted['ok'] and omitted['cfg']['video_quality']=='standard')
    ck('explicit_standard_render_identity_same',standard['ok'] and standard['render']==omitted['render'])
    ck('high_render_identity_distinct',high['ok'] and high['render'] and high['render']!=omitted['render'])
    ck('policy_only_high_identity_same',policy['ok'] and policy['render']==high['render'])
    ck('invalid_quality_fail_closed',not bad['ok'] and 'VIDEO_QUALITY' in bad.get('error',''),bad)
    with tempfile.TemporaryDirectory(prefix='v52_quality_') as td:
        td=Path(td);src=td/'src.mp4'
        filt='testsrc2=size=960x540:rate=30:duration=3.0,noise=alls=18:allf=t+u'
        cmd=[ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',filt,'-f','lavfi','-i','sine=frequency=523:sample_rate=48000:duration=3.0','-map','0:v','-map','1:a','-c:v','libx264','-preset','ultrafast','-crf','0','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=120);assert cp.returncode==0,cp.stderr
        ev={'clip_path':str(src),'clip_sha256':sha(src),'event_id':'src','source_name':'src.mp4','duration_s':3.0,'v22_metrics':{'saliency_cx':0.5,'saliency_cy':0.5}}
        ps=td/'standard.mp4';ph=td/'high.mp4'
        ms=c.make_segment(ev,ps,'16x9',2.4,-18,-2,'fill',0.5,'standard','source',30,'standard')
        mh=c.make_segment(ev,ph,'16x9',2.4,-18,-2,'fill',0.5,'standard','source',30,'high')
        prs=c.ffprobe(ps);prh=c.ffprobe(ph)
        vs=next(x for x in prs['streams'] if x.get('codec_type')=='video');vh=next(x for x in prh['streams'] if x.get('codec_type')=='video')
        ck('same_dimensions', (vs.get('width'),vs.get('height'))==(vh.get('width'),vh.get('height'))==(960,540),{'standard':vs,'high':vh})
        ck('same_duration',abs(float(prs['format']['duration'])-float(prh['format']['duration']))<0.05,{'standard':prs['format']['duration'],'high':prh['format']['duration']})
        ck('high_hash_distinct',sha(ps)!=sha(ph))
        def psnr_avg(test):
            fc='[0:v]trim=start=0.3:duration=2.4,setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[test];[ref][test]psnr'
            cp=subprocess.run([ff,'-hide_banner','-i',str(src),'-i',str(test),'-filter_complex',fc,'-an','-f','null','-'],capture_output=True,text=True,timeout=90)
            import re
            m=re.findall(r'average:([0-9.]+)',cp.stderr)
            return float(m[-1]) if cp.returncode==0 and m else 0.0
        pstd=psnr_avg(ps); phigh=psnr_avg(ph)
        ck('high_psnr_improves',phigh>pstd+0.20,{'standard_psnr_db':pstd,'high_psnr_db':phigh,'delta_db':round(phigh-pstd,3),'standard_bytes':ps.stat().st_size,'high_bytes':ph.stat().st_size})
        ck('high_metadata_present',mh.get('video_quality')=='high' and mh.get('identity',{}).get('video_quality')=='high',mh)
        ck('standard_metadata_omitted','video_quality' not in ms and 'video_quality' not in ms.get('identity',{}),ms)
        # exact resume must reuse high-quality bytes, not silently downgrade
        mh2=c.make_segment(ev,ph,'16x9',2.4,-18,-2,'fill',0.5,'standard','source',30,'high')
        ck('high_exact_resume',mh2.get('sha256')==mh.get('sha256') and ph.stat().st_size==mh['bytes'])
    passed=sum(1 for x in checks if x['pass'])
    out={'candidate':'MEDENG_VIDEO_QUALITY_V52_RC1','status':'PASS' if passed==len(checks) else 'FAIL','passed':passed,'total':len(checks),'checks':checks,'default_video_quality':'standard','alternate_video_quality':'high','semantic_selection_claim':False}
    print(json.dumps(out,indent=2));raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()

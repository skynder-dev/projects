#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args();root=Path(a.package_root).resolve();ff=str(Path(a.ffmpeg).resolve());sys.path.insert(0,str(root));q=load('q46_resolution',root/'medeng_drop_queue_v40.py');c=load('c46_resolution',root/'medeng_targeted_auto_edit_v26.py');c.FFMPEG=ff
 checks=[]
 def ck(n,ok,d=None):checks.append({'name':n,'pass':bool(ok),**({'detail':d} if d is not None else {})})
 def cfgrow(obj):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'AUTO_EDIT.json';p.write_text(json.dumps(obj))
   try:cfg,full,render=q.load_job_config(p,30.0,False);return {'ok':True,'cfg':cfg,'render':render}
   except Exception as e:return {'ok':False,'error':str(e)}
 omitted=cfgrow({'schema_version':1,'target_seconds':30});std=cfgrow({'schema_version':1,'target_seconds':30,'output_resolution':'standard'});hd=cfgrow({'schema_version':1,'target_seconds':30,'output_resolution':'social_hd'});policy=cfgrow({'schema_version':1,'target_seconds':30,'output_resolution':'social_hd','approval_mode':'auto','max_attempts':3});bad=cfgrow({'schema_version':1,'target_seconds':30,'output_resolution':'4k_magic'})
 ck('omitted_default_standard',omitted['ok'] and omitted['cfg']['output_resolution']=='standard');ck('explicit_standard_identity_same',std['ok'] and std['render']==omitted['render']);ck('social_hd_identity_distinct',hd['ok'] and hd['render'] and hd['render']!=omitted['render']);ck('policy_only_hd_identity_same',policy['ok'] and policy['render']==hd['render']);ck('invalid_resolution_fail_closed',not bad['ok'] and 'OUTPUT_RESOLUTION' in bad.get('error',''),bad)
 ck('standard_16x9_dimensions_contract',c.output_dimensions('16x9','standard')==(960,540));ck('standard_9x16_dimensions_contract',c.output_dimensions('9x16','standard')==(540,960));ck('social_hd_16x9_dimensions_contract',c.output_dimensions('16x9','social_hd')==(1920,1080));ck('social_hd_9x16_dimensions_contract',c.output_dimensions('9x16','social_hd')==(1080,1920))
 # filter-string compatibility without expensive encodes
 fake={'clip_path':'x.mp4','duration_s':2.0,'v22_metrics':{'saliency_cx':0.55,'saliency_cy':0.5}}
 # segment_spec probes source, so use real short source below for filter contract + three encodes
 with tempfile.TemporaryDirectory(prefix='v46_res_') as td:
  td=Path(td);src=td/'src.mp4';cmd=[ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=24:duration=2','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2','-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)];cp=subprocess.run(cmd,capture_output=True,text=True,timeout=60);assert cp.returncode==0,cp.stderr
  ev={'clip_path':str(src),'clip_sha256':sha(src),'event_id':'src','source_name':'src.mp4','duration_s':2.0,'v22_metrics':{'saliency_cx':0.55,'saliency_cy':0.5}}
  _,_,_,vf_focus,_,_=c.segment_spec(ev,'9x16',1.5,'fill',0.0,'social_hd');_,_,_,vf_blur,_,_=c.segment_spec(ev,'9x16',1.5,'fit_blur',0.5,'social_hd')
  ck('social_hd_focus_filter_contract','scale=1080:1920' in vf_focus)
  ck('social_hd_fit_blur_filter_contract','scale=1080:1920' in vf_blur and 'crop=1080:1920' in vf_blur)
  std9=td/'std9.mp4';hd16=td/'hd16.mp4';hd9=td/'hd9.mp4'
  c.make_segment(ev,std9,'9x16',1.5,-18,-2,'fill',0.5,'standard');c.make_segment(ev,hd16,'16x9',1.5,-18,-2,'fill',0.5,'social_hd');c.make_segment(ev,hd9,'9x16',1.5,-18,-2,'fill',0.5,'social_hd')
  p=lambda x:c.ffprobe(x)['streams'][0]
  ck('social_hd_16x9_real_encode',(p(hd16)['width'],p(hd16)['height'])==(1920,1080),p(hd16));ck('social_hd_9x16_real_encode',(p(hd9)['width'],p(hd9)['height'])==(1080,1920),p(hd9));ck('social_hd_9x16_bytes_distinct_standard',sha(hd9)!=sha(std9))
 passed=sum(1 for x in checks if x['pass']);out={'candidate':'MEDENG_OUTPUT_RESOLUTION_V46_RC1','status':'PASS' if passed==len(checks) else 'FAIL','passed':passed,'total':len(checks),'checks':checks,'default_output_resolution':'standard','social_hd':{'16x9':[1920,1080],'9x16':[1080,1920]},'semantic_selection_claim':False};print(json.dumps(out,indent=2));raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def run(cmd,timeout=120):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False)
 if cp.returncode: raise RuntimeError('CMD_FAIL:'+str(cp.returncode)+':'+cp.stderr[-1000:])
 return cp

def mean_volume(ffmpeg,p):
 cp=subprocess.run([ffmpeg,'-hide_banner','-nostats','-i',str(p),'-af','volumedetect','-f','null','-'],capture_output=True,text=True,timeout=60,check=False)
 text=(cp.stdout or '')+(cp.stderr or '')
 import re
 m=re.search(r'mean_volume:\s*(-?inf|[-0-9.]+) dB',text)
 if not m:return None
 return -200.0 if m.group(1)=='-inf' else float(m.group(1))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args()
 root=Path(a.package_root);ff=str(Path(a.ffmpeg));core=load('v47core',root/'medeng_targeted_auto_edit_v26.py');q=load('v47q',root/'medeng_drop_queue_v40.py')
 checks=[]
 def ck(n,v,d=None):checks.append({'name':n,'pass':bool(v),**({'detail':d} if d is not None else {})})
 cfg0,_,rid0=q.load_job_config(None,15,False);ck('default_source',cfg0.get('audio_content')=='source');ck('default_render_identity_none',rid0 is None)
 with tempfile.TemporaryDirectory(prefix='v47_audio_') as td:
  td=Path(td);src=td/'src.mp4'
  run([ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=880:sample_rate=48000','-t','4','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k',str(src)])
  e={'clip_path':str(src),'clip_sha256':core.sha256_file(src),'start_s':0.0,'end_s':4.0,'duration_s':4.0,'v22_metrics':{'saliency_cx':0.5,'saliency_cy':0.5}}
  # make_segment only needs these fields for this path.
  e.update({'event_id':'0'*24,'source_name':'src.mp4','source_sha256':core.sha256_file(src)})
  os.environ['MEDENG_FFMPEG']=ff;core.FFMPEG=ff
  a1=td/'source.mp4';a2=td/'mute.mp4'
  core.make_segment(e,a1,'16x9',3.0,-18.0,-2.0,'fill',0.5,'standard','source')
  core.make_segment(e,a2,'16x9',3.0,-18.0,-2.0,'fill',0.5,'standard','mute')
  p1=core.ffprobe(a1);p2=core.ffprobe(a2)
  ck('source_has_audio_stream',any(x.get('codec_type')=='audio' for x in p1.get('streams',[])))
  ck('mute_has_audio_stream',any(x.get('codec_type')=='audio' for x in p2.get('streams',[])))
  v1=mean_volume(ff,a1);v2=mean_volume(ff,a2)
  ck('source_audible',v1 is not None and v1>-60,{'mean_db':v1})
  ck('mute_silent',v2 is not None and v2<-90,{'mean_db':v2})
  ck('mute_bytes_distinct',core.sha256_file(a1)!=core.sha256_file(a2))
  # config identities
  p=td/'AUTO_EDIT.json';p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'audio_content':'mute'}))
  cm,_,rm=q.load_job_config(p,15,False);ck('mute_config_parsed',cm['audio_content']=='mute');ck('mute_render_identity_present',bool(rm))
  p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'audio_content':'source','approval_mode':'auto'}))
  cs,_,rs=q.load_job_config(p,15,False);ck('explicit_source_identity_default',rs is None);ck('approval_policy_not_render_identity',rs is None)
  p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'audio_content':'bad'}))
  try:q.load_job_config(p,15,False);bad=False
  except Exception:bad=True
  ck('invalid_audio_content_fail_closed',bad)
 ok=all(x['pass'] for x in checks);print(json.dumps({'candidate':'MEDENG_AUDIO_CONTENT_V47_SELFTEST','status':'PASS' if ok else 'FAIL','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()

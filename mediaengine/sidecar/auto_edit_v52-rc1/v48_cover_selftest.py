#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def run(cmd):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90,check=False)
 if cp.returncode:raise RuntimeError(cp.stderr[-1000:])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args();root=Path(a.package_root);ff=str(Path(a.ffmpeg));os.environ['MEDENG_FFMPEG']=ff
 q=load('v48q',root/'medeng_drop_queue_v40.py');checks=[]
 def ck(n,v,d=None):checks.append({'name':n,'pass':bool(v),**({'detail':d} if d is not None else {})})
 with tempfile.TemporaryDirectory(prefix='v48_cover_') as td:
  td=Path(td);out=td/'job';out.mkdir()
  outputs=[]
  for profile,size in [('16x9','960x540'),('9x16','540x960')]:
   p=out/f'reel_{profile}.mp4';run([ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'testsrc2=size={size}:rate=30','-t','2','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-an',str(p)]);outputs.append({'profile':profile,'filename':p.name,'bytes':p.stat().st_size,'sha256':q.sha256_file(p)})
  c=q.ensure_cover_assets(out,outputs,'auto',ff);ck('cover_status_pass',c.get('status')=='PASS');ck('two_covers',len(c.get('covers') or [])==2);ck('semantic_claim_false',c.get('semantic_selection_claim') is False);ck('cover_dimensions',[(x['width'],x['height']) for x in c['covers']]==[(960,540),(540,960)])
  c2=q.ensure_cover_assets(out,outputs,'auto',ff);ck('cover_resume_exact',c2.get('resume_status')=='SKIPPED_EXACT_COMPLETED' and c2.get('mutated') is False)
  p=td/'AUTO_EDIT.json';p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'cover_mode':'auto'}));cfg,_,rid=q.load_job_config(p,15,False);ck('cover_config_parsed',cfg['cover_mode']=='auto');ck('cover_not_render_identity',rid is None)
  p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'cover_mode':'bad'}));
  try:q.load_job_config(p,15,False);bad=False
  except Exception:bad=True
  ck('invalid_cover_fail_closed',bad)
 ok=all(x['pass'] for x in checks);print(json.dumps({'candidate':'MEDENG_COVER_V48_SELFTEST','status':'PASS' if ok else 'FAIL','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys, tempfile, hashlib
from pathlib import Path

def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def run(cmd,timeout=90,binary=False):
 cp=subprocess.run(cmd,capture_output=True,text=not binary,timeout=timeout,check=False)
 if cp.returncode: raise RuntimeError('CMD_FAIL:'+str(cp.returncode)+':'+((cp.stderr[-1000:] if not binary else cp.stderr[-1000:].decode('utf-8','replace'))))
 return cp

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sample_rgb(ff,p):
 cp=run([ff,'-hide_banner','-loglevel','error','-i',str(p),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],binary=True)
 b=cp.stdout;return tuple(b[:3]) if len(b)>=3 else None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args();root=Path(a.package_root);ff=str(Path(a.ffmpeg));os.environ['MEDENG_FFMPEG']=ff;sys.path.insert(0,str(root))
 q=load('v50q',root/'medeng_drop_queue_v40.py');approval=load('v50approval',root/'medeng_approval_v36.py')
 checks=[]
 def ck(n,v,d=None):checks.append({'name':n,'pass':bool(v),**({'detail':d} if d is not None else {})})
 with tempfile.TemporaryDirectory(prefix='v50_cover_position_') as td:
  td=Path(td)
  cfg,_,rid=q.load_job_config(None,15,False);ck('default_position_half',cfg.get('cover_position')==0.5,cfg);ck('default_not_render_identity',rid is None,rid)
  p=td/'AUTO_EDIT.json';p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'cover_mode':'auto','cover_position':0.25}));c1,h1,r1=q.load_job_config(p,15,False);p.write_text(json.dumps({'schema_version':1,'target_seconds':15,'cover_mode':'auto','cover_position':0.75}));c2,h2,r2=q.load_job_config(p,15,False);ck('position_parses',c1['cover_position']==0.25 and c2['cover_position']==0.75);ck('position_changes_full_config',h1!=h2,(h1,h2));ck('position_not_render_identity',r1 is None and r2 is None,(r1,r2))
  p.write_text(json.dumps({'schema_version':1,'cover_position':1.1}));
  try:q.load_job_config(p,15,False);bad=False
  except Exception:bad=True
  ck('invalid_position_fail_closed',bad)
  # Build two temporally distinct reel fixtures: red first half, blue second half.
  job=td/'job';job.mkdir();outs=[]
  for profile,size in [('16x9','960x540'),('9x16','540x960')]:
   dst=job/f'reel_{profile}.mp4'
   run([ff,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c=red:size={size}:rate=30:d=2','-f','lavfi','-i',f'color=c=blue:size={size}:rate=30:d=2','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(dst)])
   outs.append({'profile':profile,'filename':dst.name,'bytes':dst.stat().st_size,'sha256':sha(dst)})
  c25=q.ensure_cover_assets(job,outs,'auto',ff,0.25);h25={x['profile']:x['sha256'] for x in c25['covers']};rgb25={x['profile']:sample_rgb(ff,job/'Covers'/x['filename']) for x in c25['covers']};ck('job_position_025_manifest',c25.get('cover_position')==0.25 and all(abs(x['cover_position']-0.25)<1e-9 for x in c25['covers']));ck('job_position_025_red',all(rgb and rgb[0]>rgb[2]*1.5 for rgb in rgb25.values()),rgb25)
  c75=q.ensure_cover_assets(job,outs,'auto',ff,0.75);h75={x['profile']:x['sha256'] for x in c75['covers']};rgb75={x['profile']:sample_rgb(ff,job/'Covers'/x['filename']) for x in c75['covers']};ck('job_position_075_manifest',c75.get('cover_position')==0.75 and all(abs(x['cover_position']-0.75)<1e-9 for x in c75['covers']));ck('job_position_075_blue',all(rgb and rgb[2]>rgb[0]*1.5 for rgb in rgb75.values()),rgb75);ck('job_cover_hashes_change',h25!=h75,(h25,h75))
  # Approved covers use the same normalized position while approved reel identities remain unchanged.
  approved=td/'Approved';approved.mkdir();aouts=[]
  for o in outs:
   src=job/o['filename'];fn=f"approved_reel_{o['profile']}.mp4";dst=approved/fn;dst.write_bytes(src.read_bytes());aouts.append({'profile':o['profile'],'filename':fn,'bytes':dst.stat().st_size,'sha256':sha(dst)})
  reels_before={x['profile']:x['sha256'] for x in aouts};a25=approval.ensure_approved_covers(approved,aouts,'auto',0.25,ff);ah25={x['profile']:x['sha256'] for x in a25['covers']};a75=approval.ensure_approved_covers(approved,aouts,'auto',0.75,ff);ah75={x['profile']:x['sha256'] for x in a75['covers']};reels_after={x['profile']:sha(approved/x['filename']) for x in aouts};ck('approved_position_changes_cover_hashes',ah25!=ah75,(ah25,ah75));ck('approved_reels_unchanged',reels_before==reels_after);ck('approved_position_075_manifest',a75.get('cover_position')==0.75 and a75.get('selection_policy')=='POSITIONAL_TECHNICAL_APPROVED_COVER_V50')
 ok=all(x['pass'] for x in checks);print(json.dumps({'candidate':'MEDENG_COVER_POSITION_V50_SELFTEST','status':'PASS' if ok else 'FAIL','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()

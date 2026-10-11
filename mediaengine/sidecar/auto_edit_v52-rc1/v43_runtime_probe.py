#!/usr/bin/env python3
import argparse, hashlib, json, platform, subprocess, sys
from pathlib import Path

REQUIRED_IMPORTS={'numpy':'numpy','opencv-python':'cv2','Pillow':'PIL'}
def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def exe_probe(path,args,timeout=15):
    p=Path(path)
    if not p.is_file(): return {'ok':False,'path':str(p),'error':'missing'}
    try:
        cp=subprocess.run([str(p),*args],capture_output=True,text=True,errors='replace',timeout=timeout)
        return {'ok':cp.returncode==0,'path':str(p),'sha256':sha256(p),'rc':cp.returncode,'stdout':cp.stdout[:2000],'stderr':cp.stderr[:2000]}
    except Exception as e:return {'ok':False,'path':str(p),'error':type(e).__name__+': '+str(e)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ffmpeg',required=True);ap.add_argument('--package-root',required=True);a=ap.parse_args()
    imports={}
    for dist,mod in REQUIRED_IMPORTS.items():
        try:
            m=__import__(mod);imports[dist]={'ok':True,'version':getattr(m,'__version__','unknown')}
        except Exception as e:imports[dist]={'ok':False,'error':type(e).__name__+': '+str(e)}
    root=Path(a.package_root).resolve();compile_results=[]
    for p in sorted(root.glob('medeng_*.py')):
        try:compile(p.read_text(encoding='utf-8'),str(p),'exec');compile_results.append({'file':p.name,'ok':True,'sha256':sha256(p)})
        except Exception as e:compile_results.append({'file':p.name,'ok':False,'error':type(e).__name__+': '+str(e)})
    ffmpeg=exe_probe(a.ffmpeg,['-version'])
    helper=(root/'medeng_media_probe_v41.py')
    helper_ok=helper.is_file() and any(x['file']=='medeng_media_probe_v41.py' and x['ok'] for x in compile_results)
    ok=(sys.version_info>=(3,10) and all(x['ok'] for x in imports.values()) and all(x['ok'] for x in compile_results) and ffmpeg['ok'] and helper_ok)
    out={'candidate':'MEDENG_V43_AUDIO_TARGET_RUNTIME_PROBE','ok':ok,'probe_backend':'FFMPEG_INPUT_METADATA_V41','external_ffprobe_required':False,
         'python':{'executable':sys.executable,'version':sys.version,'platform':platform.platform(),'sha256':sha256(Path(sys.executable)) if Path(sys.executable).is_file() else None},
         'imports':imports,'scripts':compile_results,'ffmpeg':ffmpeg,'media_probe_helper_sha256':sha256(helper) if helper.is_file() else None}
    print(json.dumps(out,indent=2));raise SystemExit(0 if ok else 2)
if __name__=='__main__':main()

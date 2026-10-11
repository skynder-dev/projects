#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
CODE_EXT={'.py','.ps1','.cmd','.vbs','.pyc','.pyd','.dll'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();root=Path(a.root).resolve();mp=root/'V52_PAYLOAD_MANIFEST.json'
 if not mp.is_file():raise SystemExit('V52_MANIFEST_MISSING')
 m=json.loads(mp.read_text(encoding='utf-8'));rows=[];ok=True
 for f in m['files']:
  p=root/f['path'];exists=p.is_file();size=p.stat().st_size if exists else None;digest=sha(p) if exists else None;good=exists and size==int(f['bytes']) and digest==f['sha256'];ok=ok and good;rows.append({'path':f['path'],'ok':good,'exists':exists,'size':size,'sha256':digest})
 allowed={str(f['path']).replace('\\','/').lower() for f in m['files']};unexpected=[]
 for p in root.rglob('*'):
  if p.is_file() and p.suffix.lower() in CODE_EXT:
   rel=str(p.relative_to(root)).replace('\\','/').lower()
   if rel not in allowed:unexpected.append(rel)
 if unexpected:ok=False
 print(json.dumps({'candidate':'MEDENG_V52_PAYLOAD_VERIFY','ok':bool(ok),'slot':m.get('slot'),'files':rows,'unexpected_code_files':unexpected},indent=2));raise SystemExit(0 if ok else 3)
if __name__=='__main__':main()

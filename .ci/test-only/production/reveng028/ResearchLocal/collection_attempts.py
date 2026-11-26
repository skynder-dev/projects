"""Durable current-attempt registration before research; no executor/network code.

The root marker is the start commit. A result/published pointer must carry its
unique token. Per-run copies retain history; the root marker remains authority
even if copying that trace is interrupted. Hashes are integrity, not permission.
"""
import json,os,uuid,hashlib
from pathlib import Path
from datetime import datetime,timezone
import response_diagnostics as rd
SCHEMA='reveng-collection-attempt-v1'
MARKER='current-collection-attempt.json'
LIMIT=8*1024*1024
MAX_RUNS=256
def sha(raw):return hashlib.sha256(raw).hexdigest()
def raw(path):
 p=Path(path)
 if p.stat().st_size>LIMIT:raise ValueError('Run file exceeds8MiB')
 with p.open('rb')as f:data=f.read(LIMIT+1)
 if len(data)>LIMIT:raise ValueError('Run file exceeds8MiB')
 return data
def local(path):
 p=Path(path).resolve()
 if str(path).startswith(('\\\\','//')):raise ValueError('Local attempt paths only')
 for a in [Path(path),*Path(path).parents]:
  if a.exists()and(a.is_symlink()or getattr(a.stat(follow_symlinks=False),'st_file_attributes',0)&0x400):raise ValueError('Reparse attempt path')
 return p
def directory(root,relative):
 p=local(root/relative)
 if p.parent!=local(root/'runs'):raise ValueError('Attempt must name one owned run directory')
 return p
def snapshot(root,exclude=None):
 result={};folder=root/'runs';entries=list(folder.iterdir())if folder.exists()else[]
 if len(entries)>MAX_RUNS:raise ValueError('Run journal scan limit; latest attempt cannot be established')
 for p in entries:
  local(p)
  if not p.is_dir()or p==exclude:continue
  f=p/'result.json'
  if f.exists():result[f.relative_to(root).as_posix()]=sha(raw(local(f)))
 return result
def atomic(path,data,prefix):
 path=Path(path);tmp=path.parent/(prefix+uuid.uuid4().hex+'.tmp')
 with tmp.open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def marker(root):
 p=root/MARKER
 if not p.exists():return None
 value=rd.strict_json(raw(local(p)).decode('utf-8'))
 if type(value)is not dict or set(value)!={'schema','attempt_id','run_directory','started_at','preexisting_results'}or value['schema']!=SCHEMA or type(value['attempt_id'])is not str or len(value['attempt_id'])!=32 or any(c not in '0123456789abcdef'for c in value['attempt_id'])or type(value['preexisting_results'])is not dict:raise ValueError('Invalid current attempt marker')
 directory(root,value['run_directory'])
 return value
def begin(root,run):
 root=local(root);run=local(run)
 if run.parent!=root/'runs':raise ValueError('Owned run directory required')
 if (run/'result.json').exists()or(run/'collection-attempt.json').exists():raise ValueError('Run already contains an attempt; do not overwrite/reuse')
 if list(root.glob('.collection-attempt-*.tmp')):raise ValueError('Unfinished attempt registration retained; resolve before starting new research')
 previous=marker(root)
 if previous:
  old=directory(root,previous['run_directory']);trace=old/'collection-attempt.json'
  if trace.exists()and raw(trace)!=rd.canonical(previous):trace=old/('collection-attempt-recovered-'+previous['attempt_id']+'.json')
  if not trace.exists():
   with trace.open('xb')as f:f.write(rd.canonical(previous));f.flush();os.fsync(f.fileno())
  elif raw(trace)!=rd.canonical(previous):raise ValueError('Conflicting archived attempt; do not overwrite history')
 value={'schema':SCHEMA,'attempt_id':uuid.uuid4().hex,'run_directory':run.relative_to(root).as_posix(),'started_at':datetime.now(timezone.utc).isoformat(),'preexisting_results':snapshot(root,run)}
 data=rd.canonical(value)
 # No pipeline/result write precedes this durable start commit.
 atomic(root/MARKER,data,'.collection-attempt-')
 with(run/'collection-attempt.json').open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
 return value
def attach(run,value):
 if run.parent.name!='runs':return value
 root=run.parent.parent;p=run/'collection-attempt.json'
 current=rd.strict_json(raw(local(p)).decode('utf-8'))if p.exists()else marker(root)
 if current and current.get('schema')==SCHEMA and directory(root,current['run_directory'])==local(run):value['collection_attempt_id']=current['attempt_id']
 return value
def publication(root,run,data):
 current=marker(root)
 if current is None:return {} # Legacy direct pipeline tooling; reader treats it as legacy.
 if directory(root,current['run_directory'])!=local(run):raise ValueError('A different current attempt exists; do not publish a stale run')
 if list(root.glob('.collection-attempt-*.tmp'))or snapshot(root,local(run))!=current['preexisting_results']:raise ValueError('Attempt journal changed/registration incomplete; no silent publication')
 result=rd.strict_json(data.decode('utf-8'))
 if result.get('collection_attempt_id')!=current['attempt_id']or result.get('status')in[None,'running']:raise ValueError('Result is not this attempt terminal record')
 return {'collection_attempt_id':current['attempt_id'],'attempt_schema':SCHEMA}

"""Immutable local preparation lineage, not authorization or business decisions."""
import json,re,os,tempfile
from pathlib import Path
def digest(m,obj):return m.sha(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode())
def write_new_json(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=None
 try:
  with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.immutable-',suffix='.tmp',delete=False) as stream:
   temp=Path(stream.name);stream.write(json.dumps(obj,ensure_ascii=False,indent=2).encode());stream.flush();os.fsync(stream.fileno())
  # Atomic create-if-absent, never replace an existing sealed file.
  os.link(temp,path)
 finally:
  if temp is not None and temp.exists():temp.unlink()
def events(m,root):
 root=Path(root);folder=root/'analysis-lineage';paths=list(folder.glob('*.json'));index=root/'analysis-lineage-index.json';expected=set()
 if index.exists():
  data=json.loads(index.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
  if claim!=digest(m,data):raise ValueError('Analysis lineage index integrity mismatch')
  expected=set(data.get('events',[]))
 if not expected<={p.stem for p in paths}:raise ValueError('Analysis lineage event missing; no dispatch permitted')
 out=[]
 for p in sorted(paths):
  if not re.fullmatch('[0-9a-f]{64}',p.stem):raise ValueError('Invalid analysis lineage filename')
  data=json.loads(p.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
  if claim!=p.stem or claim!=digest(m,data) or data.get('kind')!='preparation_superseded':raise ValueError('Analysis lineage event integrity mismatch')
  for key in ['superseded_input','completed_input']:
   if not re.fullmatch('[0-9a-f]{64}',str(data.get(key,''))):raise ValueError('Invalid lineage input identity')
  out.append((p.stem,data))
 return out
def apply(m,root,jobs):
 root=Path(root);seen={}
 for event_id,event in events(m,root):
  old=event['superseded_input'];new=event['completed_input']
  if old not in jobs or new not in jobs:raise ValueError('Lineage input missing; recover source artifacts, never redispatch')
  if old in seen and seen[old]!=new:raise ValueError('Ambiguous replacement lineage')
  seen[old]=new
  if (root/'analysis-results'/(old+'.json')).exists():raise ValueError('A completed result cannot be overwritten as a superseded preparation')
  for id,key in [(old,'superseded_input_sha256'),(new,'completed_input_sha256')]:
   path=root/'analysis-inputs'/(id+'.json')
   if m.sha(path.read_bytes())!=event[key]:raise ValueError('Lineage sealed input bytes changed')
  result=root/'analysis-results'/(new+'.json')
  if not result.exists() or m.sha(result.read_bytes())!=event['completed_result_sha256']:raise ValueError('Lineage completed result missing/changed; no repeat dispatch')
  record=json.loads(result.read_text(encoding='utf-8'))
  if record.get('model_output',{}).get('source_job')!=new:raise ValueError('Lineage result belongs to another source job')
  jobs[old].update(status='superseded_preparation',superseded_by=new,lineage_event='analysis-lineage/'+event_id+'.json',reason=event['reason'])
 return jobs
def record_supersession(m,root,old,new,reason):
 root=Path(root)
 if old==new or not all(re.fullmatch('[0-9a-f]{64}',x) for x in [old,new]):raise ValueError('Invalid replacement identity')
 if (root/'analysis-results'/(old+'.json')).exists():raise ValueError('Old preparation already has a result')
 result=root/'analysis-results'/(new+'.json');record=json.loads(result.read_text(encoding='utf-8'))
 if record.get('model_output',{}).get('source_job')!=new:raise ValueError('Replacement result attribution mismatch')
 import analysis_jobs
 for id in [old,new]:analysis_jobs.inspect_input(m,root,root/'analysis-inputs'/(id+'.json'))
 current=events(m,root);match=[(id,e) for id,e in current if e['superseded_input']==old]
 if match:
  if any(e['completed_input']!=new for _,e in match):raise ValueError('Preparation already has another replacement')
  id=match[0][0]
 else:
  payload={'kind':'preparation_superseded','superseded_input':old,'completed_input':new,'superseded_input_sha256':m.sha((root/'analysis-inputs'/(old+'.json')).read_bytes()),'completed_input_sha256':m.sha((root/'analysis-inputs'/(new+'.json')).read_bytes()),'completed_result_sha256':m.sha(result.read_bytes()),'recorded_at':m.now(),'reason':reason,'meaning':'Historical preparation replaced by an existing completed attempt; no approval, new model dispatch or candidate admission.'};id=digest(m,payload);write_new_json(root/'analysis-lineage'/(id+'.json'),dict(payload,integrity_sha256=id));current=events(m,root)
 index={'schema':'reveng-analysis-lineage-index-v1','events':sorted({key for key,_ in current})};m.dump(root/'analysis-lineage-index.json',dict(index,integrity_sha256=digest(m,index)))
 return id

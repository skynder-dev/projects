"""Content differences only. Never chooses a winner or merges owner work."""
from pathlib import Path
import hashlib,json
import comparison_data
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()
def records(root,validated):
 out={};root=Path(root)
 for name,kind,key in [('candidates.json','legacy_hypothesis','candidate_id'),('research-output-cards.json','model_hypothesis','research_id')]:
  raw=(root/name).read_bytes()
  if sha(raw)!=validated['inputs'][name]:raise ValueError('Workspace changed during archive comparison')
  obj=json.loads(raw.decode('utf-8-sig'));rows=obj['cards'] if isinstance(obj,dict) else obj
  for row in rows:
   identity=kind+':'+row[key]
   if identity in out:raise ValueError('Ambiguous candidate identity')
   out[identity]=row
 notes=root/'manual-hypotheses.json'
 if notes.exists():
  raw=notes.read_bytes()
  if sha(raw)!=validated['inputs']['manual-hypotheses.json']:raise ValueError('Manual work changed during archive comparison')
  payload=json.loads(json.loads(raw.decode('utf-8-sig'))['payload_json'])
  for note in payload['notes']:out['manual_hypothesis:'+note['payload_sha256']]=json.loads(note['payload_json'])
 return out
def compare(root,archive_root,archive_data):
 try:
  current_data=comparison_data.build(root);current=records(root,current_data);archived=records(archive_root,archive_data);rows=[]
  for id in sorted(set(current)|set(archived)):
   a=current.get(id);b=archived.get(id);state='ARCHIVE_ONLY' if a is None else 'CURRENT_ONLY' if b is None else 'IDENTICAL_CONTENT' if a==b else 'SAME_ID_DIFFERENT_CONTENT'
   rows.append({'identity':id,'title':(a or b).get('title'),'status':state,'current_snapshot_sha256':sha(canonical(a)) if a is not None else None,'archive_snapshot_sha256':sha(canonical(b)) if b is not None else None,'different_top_level_fields':sorted(k for k in set(a or {})|set(b or {}) if k not in a or k not in b or a[k]!=b[k]) if a is not None and b is not None else []})
  notes=[]
  for name in ['review-notes.json']:
   a=Path(root)/name;b=Path(archive_root)/name;ah=sha(a.read_bytes()) if a.exists() else None;bh=sha(b.read_bytes()) if b.exists() else None;notes.append({'file':name,'current_file_sha256':ah,'archive_file_sha256':bh,'byte_equal':ah==bh,'meaning':'File content comparison only; no owner decision applied or revalidated'})
  return {'status':'CONTENT_DIFFERENCE_ONLY_NO_MERGE','rows':rows,'counts':{state:sum(r['status']==state for r in rows) for state in ['IDENTICAL_CONTENT','SAME_ID_DIFFERENT_CONTENT','CURRENT_ONLY','ARCHIVE_ONLY']},'owner_note_files':notes,'merge_performed':False,'winner_selected':False,'meaning':'Same ID/different content requires explicit human reconciliation. Neither archive nor current data wins by date, score or age; no automatic writes or admission.'}
 except (ValueError,KeyError,TypeError,OSError) as ex:return {'status':'CURRENT_STATE_NOT_COMPARABLE','error':str(ex),'merge_performed':False,'winner_selected':False,'meaning':'Archive may be read separately; current data is not replaced or inferred to be worse.'}

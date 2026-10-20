"""Incomplete editor work: portable recovery only, never source/customer/model proof."""
import hashlib,json,re
FIELDS={'title','interpretation','assumptions','buyer_role','next_action','success','failure'}
def verify(fetch,names):
 paths=sorted(n for n in names if n.startswith('manual-editor-recovery/'))
 if len(paths)>20:raise ValueError('Too many incomplete editor recovery files')
 for path in paths:
  if not re.fullmatch(r'manual-editor-recovery/[0-9a-f]{32}\.json',path):raise ValueError('Invalid recovery path')
  raw=fetch(path)
  if len(raw)>1048576:raise ValueError('Recovery exceeds1MiB')
  wrap=json.loads(raw.decode('utf-8-sig'));payload=wrap.get('payload_json')
  if not isinstance(payload,str) or hashlib.sha256(payload.encode()).hexdigest()!=wrap.get('payload_sha256'):raise ValueError('Recovery hash mismatch')
  d=json.loads(payload)
  if d.get('schema')!='reveng-editor-recovery-v1' or d.get('status')!='INCOMPLETE_EDITOR_WORK_NOT_HYPOTHESIS' or d.get('auto_admission') is not False:raise ValueError('Recovery policy mismatch')
  if set(d)!={'schema','status','auto_admission','saved_at','source_snapshot','previous_id','start','end','fields'}:raise ValueError('Unexpected recovery property')
  if not isinstance(d['previous_id'],str) or d['previous_id'] and not re.fullmatch('[0-9a-f]{64}',d['previous_id']):raise ValueError('Invalid prior note identity')
  s=d['source_snapshot'];text=s.get('text')
  if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=s.get('text_sha256'):raise ValueError('Recovery source hash mismatch')
  fields=d['fields']
  if not isinstance(fields,dict) or set(fields)!=FIELDS or any(not isinstance(v,str) or len(v.encode('utf-16-le'))//2>(200 if k=='title' else 4000) for k,v in fields.items()):raise ValueError('Recovery fields invalid')
  a,b=d['start'],d['end']
  if type(a)is not int or type(b)is not int or not ((a,b)==(-1,-1) or 0<=a<b<=len(text) and b-a<=1000):raise ValueError('Recovery range invalid')
 return len(paths)

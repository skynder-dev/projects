"""Protected owner-decision copy only; never automatic merge or authority."""
import hashlib,re,json
from pathlib import Path
from manual_hypotheses import loads
NAME='decision-recovery-v1.json'
PREFERENCE_FILES=('review-notes.json',NAME,'review-notes.prev')
LIMIT=8*1024*1024

def _canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def _capture_preference_file(root,name):
 path=root/name
 try:
  if not path.resolve().is_relative_to(root):raise ValueError('Preference path outside workspace')
  if not path.exists():return {'state':'absent','sha256':None},None
  with path.open('rb') as stream:raw=stream.read(LIMIT+1)
  if len(raw)>LIMIT:raise ValueError('Preference file exceeds8MiB')
  return {'state':'captured','sha256':hashlib.sha256(raw).hexdigest()},raw
 except (OSError,ValueError) as ex:
  return {'state':'unavailable','sha256':None,'error':type(ex).__name__+': '+str(ex)},None

def preference_snapshot(root,cards,workspace_scope):
 """Separate read-only preference overlay; never an evidence-revision input."""
 root=Path(root).resolve();inputs={};raws={};issues=[];notes={};status='READABLE'
 for name in PREFERENCE_FILES:
  pin,raw=_capture_preference_file(root,name);inputs[name]=pin
  if raw is not None:raws[name]=raw
  if pin['state']=='unavailable':issues.append(name+': '+pin['error']);status='UNAVAILABLE'
 try:
  if 'review-notes.json' in raws:
   parsed=loads(raws['review-notes.json'].decode('utf-8-sig'))
   if not isinstance(parsed,dict):raise ValueError('Primary owner preferences must be an object')
   _canonical(parsed);notes=parsed
  if inputs['review-notes.json']['state']=='absent' and inputs['review-notes.prev']['state']!='absent':
   issues.append('Primary preferences missing; previous file retained for inspection, not applied.');status='RECOVERY_CONFLICT'
  if NAME in raws:
   verify(lambda name:raws[name],set(raws))
   protected=loads(loads(raws[NAME].decode('utf-8-sig'))['payload_json'])['decisions']
   if any(key not in notes or _canonical(notes[key])!=_canonical(value) for key,value in protected.items()):
    issues.append('Primary differs from protected decisions; no automatic merge or current preference authority.');status='RECOVERY_CONFLICT'
 except (ValueError,TypeError,KeyError,AttributeError,RecursionError) as ex:
  issues.append(type(ex).__name__+': '+str(ex));status='UNAVAILABLE'
  if not isinstance(notes,dict):notes={}
 if all(pin['state']=='absent' for pin in inputs.values()):status='ABSENT'
 import research_export
 by_candidate={}
 for card in cards:
  projection=research_export.owner_decision_projection(card,notes)
  projection['current_choice']=projection.get('saved_entry',{}).get('decision') if status=='READABLE' and projection['binding']=='CURRENT_EXACT_REVISION' else None
  if status not in ['READABLE','ABSENT']:
   projection['saved_revision_binding']=projection['binding'];projection['binding']=status+'_NOT_CURRENT'
  by_candidate['legacy_hypothesis:'+card['candidate_id']]=projection
 # Changes, including absent->present, reject this capture rather than mixing snapshots.
 for name,pin in inputs.items():
  if _capture_preference_file(root,name)[0]!=pin:raise ValueError('Owner preferences changed during comparison capture; refresh required')
 result={'schema':'reveng-owner-preference-overlay-v1','status':status,'workspace_scope':workspace_scope,'inputs':inputs,'by_candidate':by_candidate,'issues':issues,'meaning':'Saved owner preference only; separate from evidence review, market proof and execution authorization. Archive preferences never replace current workspace decisions.'}
 result['snapshot_sha256']=hashlib.sha256(_canonical(result)).hexdigest()
 return result


def verify(fetch,names):
 if NAME not in names:return 0
 raw=fetch(NAME)
 if len(raw)>8*1024*1024:raise ValueError('Decision recovery exceeds8MiB')
 wrapper=loads(raw.decode('utf-8-sig'));payload=wrapper.get('payload_json')
 if not isinstance(payload,str)or hashlib.sha256(payload.encode()).hexdigest()!=wrapper.get('payload_sha256'):raise ValueError('Decision recovery hash mismatch')
 value=loads(payload)
 if set(value)!={'schema','status','expected_primary_sha256','decisions'}or value['schema']!='reveng-decision-recovery-v1'or value['status']!='RECOVERY_COPY_NOT_CURRENT_AUTHORITY'or not isinstance(value['decisions'],dict):raise ValueError('Decision recovery is not current owner authority')
 pin=value['expected_primary_sha256']
 if pin is not None and(not isinstance(pin,str)or not re.fullmatch('[0-9a-fA-F]{64}',pin)):raise ValueError('Invalid decision recovery parent pin')
 return len(value['decisions'])

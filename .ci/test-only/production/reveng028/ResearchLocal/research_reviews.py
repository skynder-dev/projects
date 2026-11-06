"""Revision-bound declared review/decision log. No authentication or action authorization."""
from pathlib import Path
import json,os
import source_ledger as l
SCHEMA='reveng-research-reviews-v1'
CHOICES={'DEFERRED','REJECTED','REQUEST_MORE_EVIDENCE','APPROVE_RESEARCH_DIRECTION'}
def strict(value,keys):
 if type(value)is not dict or set(value)!=set(keys):raise ValueError('Exact review fields required')
def text(value):
 if type(value)is not str or not value.strip():raise ValueError('Explicit nonempty review text required')
def strings(value):
 if type(value)is not list:raise ValueError('Review list required')
 for v in value:text(v)
 if len(set(value))!=len(value):raise ValueError('Duplicate review item')
def candidate_field_materials(row):
 """Exact comparison input fields, kept distinct from source-ledger/global material identities."""
 result=[]
 for field in row['source_texts']:
  if 'source_snapshot' in field:continue
  if l.rawsha(field['text'].encode())!=field['field_sha256']:raise ValueError('Candidate field text/hash mismatch')
  reference={k:v for k,v in field.items() if k!='text'}
  identity='candidate-field:'+l.rawsha(l.canonical({'candidate_key':row['kind']+':'+row['id'],'reference':reference}))
  metadata={'source_field':field['container_field'],'comparison_source_field':field['source_field'],'kind':'EXACT_CONTAINER_SCOPED_FIELD_NOT_GLOBAL_SOURCE','author':field['reported_author'],'role':field['field_role'],'reference':reference,'automatic_admission':False}
  result.append({'id':identity,'text':field['text'],'text_sha256':field['field_sha256'],'metadata':metadata,'units':l.units(field['text'],identity)})
 return result
def revision(root,comparison,cat,key,claims):
 row=next(r for r in comparison['rows'] if r['kind']+':'+r['id']==key)
 root=Path(root)
 if row['kind']=='legacy_hypothesis':original=next(c for c in l.read(root/'candidates.json')[1] if c['candidate_id']==row['id'])
 elif row['kind']=='model_hypothesis':original=next(c for c in l.read(root/'research-output-cards.json')[1]['cards'] if c['research_id']==row['id'])
 else:
  data=l.unseal(l.read(root/'manual-hypotheses.json')[1]);original=next(l.unseal(n) for n in data['notes'] if n['payload_sha256']==row['id'])
 materials={m['id']:m for m in cat['materials']}
 ids={sid for sid,m in materials.items() if row['id'] in m['metadata'].get('card_ids',[])}
 if row['kind']=='manual_hypothesis':
  for ref in row['source_references']:
   s=ref.get('source_snapshot',{});sid=s.get('id')
   if sid in materials and l.same_manual_source_revision(cat,materials[sid],s):ids.add(sid)
 context={'input_hashes':comparison['inputs'],'comparison_rows_sha256':l.rawsha(l.canonical(comparison['rows']))}
 snapshot={'candidate_key':key,'candidate':original,'comparison_context':context,'source_fields':[materials[sid] for sid in sorted(ids)]+candidate_field_materials(row),
           'annotations':sorted([c for c in claims if c['source_id'] in ids and c['source_status']=='CURRENT_EXACT_REVISION'],key=lambda c:c['claim_id'])}
 return {'snapshot':snapshot,'revision_sha256':l.rawsha(l.canonical(snapshot))}
def validate_record(row):
 strict(row,['schema','candidate_key','revision_sha256','snapshot','condition_reviews','open_questions','decision','declarant','automatic_admission','execution_authorized','semantic_PASS'])
 if row['schema']!='reveng-research-review-entry-v1' or row['automatic_admission'] is not False or row['execution_authorized'] is not False or row['semantic_PASS'] is not False or row['declarant']!='DECLARED_OWNER_REVIEW_IDENTITY_NOT_AUTHENTICATED':raise ValueError('Review cannot establish identity, execution or semantic PASS')
 snapshot=row['snapshot'];strict(snapshot,['candidate_key','candidate','comparison_context','source_fields','annotations'])
 strict(snapshot['comparison_context'],['input_hashes','comparison_rows_sha256'])
 if snapshot['candidate_key']!=row['candidate_key'] or l.rawsha(l.canonical(snapshot))!=row['revision_sha256']:raise ValueError('Review revision snapshot mismatch')
 fields={m['id']:m for m in snapshot['source_fields']}
 if len(fields)!=len(snapshot['source_fields']):raise ValueError('Duplicate source field')
 for m in fields.values():
  if l.rawsha(m['text'].encode())!=m['text_sha256']:raise ValueError('Review source text hash mismatch')
 annotations={a['claim_id']:a for a in snapshot['annotations']}
 if len(annotations)!=len(snapshot['annotations']):raise ValueError('Duplicate annotation')
 for a in annotations.values():
  m=fields[a['source_id']]
  if type(a['start'])is not int or type(a['end'])is not int or not 0<=a['start']<a['end']<=len(m['text']) or m['text'][a['start']:a['end']]!=a['quote']:raise ValueError('Review annotation does not bind to its source')
 if type(row['condition_reviews'])is not list:raise ValueError('Field review list required')
 seen=set();closed=True
 for review in row['condition_reviews']:
  strict(review,['source_id','field_id','status','unclosed_conditions','rationale'])
  sid=review['source_id']
  if sid not in fields or sid in seen or review['field_id']!=fields[sid]['metadata'].get('source_field','text'):raise ValueError('Foreign or duplicate field review')
  seen.add(sid);strings(review['unclosed_conditions']);text(review['rationale'])
  if review['status'] not in ['REVIEWED_COMPLETE_DECLARATION','INCOMPLETE','UNKNOWN']:raise ValueError('Unknown coverage state')
  if review['status']!='REVIEWED_COMPLETE_DECLARATION' or review['unclosed_conditions']:closed=False
 if seen!=set(fields):raise ValueError('Every exact source field requires a review or explicit UNKNOWN')
 strings(row['open_questions']);decision=row['decision'];strict(decision,['choice','rationale','basis_claim_ids'])
 if decision['choice'] not in CHOICES:raise ValueError('Unknown declared owner decision')
 text(decision['rationale']);strings(decision['basis_claim_ids'])
 if not set(decision['basis_claim_ids'])<=set(annotations):raise ValueError('Decision basis outside exact revision annotations')
 if decision['choice']=='APPROVE_RESEARCH_DIRECTION' and (not fields or not annotations or not decision['basis_claim_ids'] or not closed or row['open_questions']):raise ValueError('Unclosed review cannot declare research direction approved')
 return row
def read(root):
 path=Path(root)/'research-reviews.json'
 if not path.exists():return {'schema':SCHEMA,'entries':[],'automatic_admission':False}
 data=l.unseal(l.read(path)[1]);strict(data,['schema','entries','automatic_admission'])
 if data['schema']!=SCHEMA or data['automatic_admission'] is not False or type(data['entries'])is not list:raise ValueError('Invalid review log')
 seen=set()
 for wrap in data['entries']:
  if wrap['payload_sha256'] in seen:raise ValueError('Duplicate review record')
  seen.add(wrap['payload_sha256']);validate_record(l.unseal(wrap))
 return data
def statuses(root,revisions):
 result={key:{'current_revision_sha256':rev['revision_sha256'],'history':[],'decision':'NO_EXPLICIT_REVISION_BOUND_DECISION','unclosed_conditions':[],'coverage':'NOT_ASSESSED'} for key,rev in revisions.items()}
 orphan=[]
 for w in read(root)['entries']:
  row=l.unseal(w);key=row['candidate_key'];rev=revisions.get(key)
  current=rev is not None and rev['snapshot']==row['snapshot'] and rev['revision_sha256']==row['revision_sha256']
  record={'entry_id':w['payload_sha256'],'revision_sha256':row['revision_sha256'],'binding':'CURRENT_EXACT_REVISION' if current else 'STALE_OR_ABSENT_REVISION','decision':row['decision'],'condition_reviews':row['condition_reviews'],'open_questions':row['open_questions'],'declarant':row['declarant']}
  if key not in result:orphan.append(dict(record,candidate_key=key));continue
  result[key]['history'].append(record)
  if current:
   result[key].update(decision=row['decision']['choice'],decision_rationale=row['decision']['rationale'],unclosed_conditions=[{'source_id':r['source_id'],'status':r['status'],'items':r['unclosed_conditions']} for r in row['condition_reviews'] if r['status']!='REVIEWED_COMPLETE_DECLARATION' or r['unclosed_conditions']],open_questions=row['open_questions'],coverage='DECLARED_REVIEW_ONLY_NOT_SEMANTIC_PROOF')
 return {'candidates':result,'orphan_history':orphan,'semantic_PASS':False,'execution_authorized':False}
def append(root,record,expected_sha256):
 l.require_writable(root)
 import comparison_data
 revisions=comparison_data.build(root)['research_chain']['review_revisions']
 validate_record(record);rev=revisions.get(record['candidate_key'])
 if rev is None or rev['snapshot']!=record['snapshot'] or rev['revision_sha256']!=record['revision_sha256']:raise ValueError('Cannot save a review for an obsolete research revision')
 root=Path(root).resolve();path=root/'research-reviews.json'
 with l.writer_lock(root/'.research-review-write-v2.lock'):
  current=l.rawsha(path.read_bytes()) if path.exists() else None
  if current!=expected_sha256:raise ValueError('Review log changed; reload before saving')
  data=read(root);w=l.seal(record)
  if any(e['payload_sha256']==w['payload_sha256'] for e in data['entries']):raise ValueError('Review already recorded')
  data['entries'].append(w);l.write(path,l.seal(data));return {'status':'SAVED_DECLARATION_ONLY','entry_id':w['payload_sha256'],'semantic_PASS':False,'execution_authorized':False}

def verify_summary(fetch,names,state):
 if 'research-reviews.json' not in names:return
 import csv,io
 rows=list(csv.DictReader(io.StringIO(fetch('research-summary.csv').decode('utf-8-sig'))))
 actual=[r for r in rows if r['record_kind'] in ['declared_revision_review_not_execution','historical_orphan_review_not_current']]
 expected=[]
 for key,status in state['candidates'].items():
  if not status['history']:continue
  expected.append({'record_kind':'declared_revision_review_not_execution','id':key,'title':'Exact research revision '+status['current_revision_sha256'],'review_status':status['coverage'],'unconfirmed':{'unclosed_conditions':status['unclosed_conditions'],'open_questions':status.get('open_questions',[])},'source_references':status['history'],'owner_decision':{'declared_choice':status['decision'],'rationale':status.get('decision_rationale'),'identity':'NOT_AUTHENTICATED','automatic_admission':False}})
 for history in state['orphan_history']:
  expected.append({'record_kind':'historical_orphan_review_not_current','id':history['candidate_key'],'title':'HISTORICAL','review_status':'STALE_OR_ABSENT_REVISION','unconfirmed':history['open_questions'],'source_references':history,'owner_decision':'NO_CURRENT_DECISION'})
 if len(actual)!=len(expected):raise ValueError('Review CSV inventory differs from revision history')
 for a,e in zip(actual,expected):
  for key,value in e.items():
   observed=json.loads(a[key]) if type(value) in [dict,list] else a[key]
   if observed!=value:raise ValueError('Review CSV overclaims or differs from exact revision history')

if __name__=='__main__':
 import argparse,comparison_data
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--inspect');p.add_argument('--record',type=Path);a=p.parse_args()
 if bool(a.inspect)==bool(a.record):raise ValueError('Choose inspect or explicit local review file')
 if a.inspect:
  print(json.dumps(comparison_data.build(a.root)['research_chain']['review_revisions'][a.inspect],ensure_ascii=True))
 else:
  if '://' in str(a.record) or str(a.record).startswith(('\\\\','//')):raise ValueError('Local review files only')
  from source_proposals import strict_json
  proposal=strict_json(l.read(a.record)[0].decode('utf-8-sig'));strict(proposal,['record','expected_log_sha256'])
  print(json.dumps(append(a.root,proposal['record'],proposal['expected_log_sha256'])))

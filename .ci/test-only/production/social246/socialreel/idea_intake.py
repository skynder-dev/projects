"""Offline intake of RevEng's published DISCUSSION snapshot, not a protocol/approval."""
import copy,json,re,os,uuid
from pathlib import Path
from .common import PipelineError,sha256_bytes,stable_json,write_json,read_json,sha256_file,utc_now
FOREIGN_SCHEMA='ISOLATED_IDEA_EXPORT_DISCUSSION_ONLY_NOT_PROTOCOL'
MAX_BYTES=2*1024*1024

def _pairs(pairs):
 out={}
 for key,value in pairs:
  if key in out:raise PipelineError('Duplicate idea JSON field: '+key)
  out[key]=value
 return out

def normalize_discussion_snapshot(raw):
 if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise PipelineError('Idea snapshot must be bounded UTF8 JSON bytes')
 try:value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_pairs,parse_constant=lambda x:(_ for _ in ()).throw(PipelineError('Nonfinite idea number')))
 except (UnicodeError,ValueError,RecursionError) as error:raise PipelineError('Idea snapshot JSON unavailable: '+str(error)[:150]) from error
 stack=[(value,0)];nodes=0
 while stack:
  item,depth=stack.pop();nodes+=1
  if depth>32 or nodes>50000:raise PipelineError('Idea snapshot exceeds structural budget')
  if isinstance(item,dict):stack.extend((v,depth+1) for v in item.values())
  elif isinstance(item,list):stack.extend((v,depth+1) for v in item)
 if not isinstance(value,dict) or value.get('schema')!=FOREIGN_SCHEMA:raise PipelineError('Unsupported foreign idea schema; do not guess production semantics')
 if value.get('ready_for_social') is not False or value.get('publication_authorized') is not False or value.get('semantic_PASS') is True:raise PipelineError('Discussion export cannot assert Social readiness, semantic PASS or publication authority')
 key=value.get('candidate_key');revision=value.get('revision_sha256')
 if not isinstance(key,str) or not re.fullmatch(r'(model_hypothesis|legacy_hypothesis):[0-9a-f]{8,64}',key) or not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{64}',revision):raise PipelineError('Opaque producer candidate/revision identity required')
 fields=value.get('source_fields');refs=value.get('source_references');review=value.get('revision_review');missing=value.get('missing_data');qualification=value.get('historical_qualification')
 if not isinstance(fields,list) or len(fields)>256 or not isinstance(refs,list) or len(refs)>256 or not isinstance(review,dict) or not isinstance(missing,dict) or not isinstance(qualification,dict):raise PipelineError('Idea source/review/qualification structure missing')
 history=review.get('history');unclosed=review.get('unclosed_conditions')
 if not isinstance(history,list) or len(history)>1000 or not isinstance(unclosed,list):raise PipelineError('Review history and unclosed-condition list required, even when empty')
 exact={};field_checks=[];blocked=[]
 for f in fields:
  if not isinstance(f,dict):raise PipelineError('Invalid source field')
  kind=f.get('binding')
  if kind=='EXACT_SAVED_MATERIAL':
   text=f.get('text');digest=f.get('text_sha256');id=f.get('source_id')
   if not isinstance(text,str) or not isinstance(f.get('metadata'),dict) or sha256_bytes(text.encode('utf-8'))!=digest or not isinstance(id,str):raise PipelineError('Exact saved material bytes/hash/identity mismatch')
   if id in exact and exact[id]!=text:raise PipelineError('Same producer source ID refers to different source text')
   exact[id]=text;field_checks.append({'binding':kind,'source_id':id,'text_hash_pass':True,'meaning':'Byte provenance only; not verified truth, customer or atomic condition'})
  elif kind=='CONTAINER_SCOPED_CANDIDATE_FIELD':
   text=f.get('text');ref=f.get('reference');id=f.get('review_source_id')
   if not isinstance(text,str) or not isinstance(ref,dict) or sha256_bytes(text.encode('utf-8'))!=ref.get('field_sha256') or ref.get('field_codepoints')!=len(text) or not isinstance(id,str):raise PipelineError('Container-scoped field text/hash/locator mismatch')
   field_checks.append({'binding':kind,'review_source_id':id,'text_hash_pass':True,'global_source_id_inferred':False,'meaning':'Container locator only; no global author/source equivalence inferred'})
  elif kind=='MANUAL_HYPOTHESIS_SNAPSHOT':
   if not isinstance(f.get('snapshot'),dict):raise PipelineError('Manual hypothesis snapshot missing')
   field_checks.append({'binding':kind,'text_hash_pass':False,'meaning':'Opaque unverified manual interpretation; not source fact'});blocked.append('Manual hypothesis snapshot is not independently source verified')
  else:raise PipelineError('Unknown source field binding: '+str(kind))
 literal_checks=[]
 for ref in refs:
  if not isinstance(ref,dict):raise PipelineError('Invalid condition reference')
  text=exact.get(ref.get('source_id'));a,b=ref.get('start'),ref.get('end');quote=ref.get('quote')
  if text is None or type(a) is not int or type(b) is not int or not isinstance(quote,str) or not 0<=a<b<=len(text) or text[a:b]!=quote or ref.get('source_text_sha256')!=sha256_bytes(text.encode('utf-8')):raise PipelineError('Condition reference is not bound to an available exact saved material span')
  literal_checks.append({'claim_id':ref.get('claim_id'),'source_id':ref.get('source_id'),'literal_span_exists':True,'semantic_entailment_verified':False})
 for name,state in missing.items():
  if type(state) is not bool:raise PipelineError('Missing-data flags must be explicit booleans')
  if state:blocked.append('Upstream missing: '+name)
 if review.get('current_revision_sha256')!=revision:blocked.append('Foreign review revision does not match supplied research revision')
 if review.get('coverage') in {None,'UNKNOWN','NOT_ASSESSED'}:blocked.append('Condition coverage has not been assessed; an empty unclosed list is not proof of completeness')
 if unclosed:blocked.append('Explicit unclosed conditions retained')
 if qualification.get('semantic_PASS_not_established') is not True:blocked.append('Foreign semantic qualification is unknown or contradictory; not adopted')
 blocked.append('Independent Social factual/editorial concept review is still required')
 payload=sha256_bytes(raw);identity=sha256_bytes(stable_json({'producer':'RevEng','candidate_key':key,'research_revision_sha256':revision,'payload_sha256':payload}).encode('utf-8'))
 return {'schema':'SOCIAL_RESEARCH_SNAPSHOT_INTAKE_V1','adapter':'reveng_discussion_snapshot_v0','snapshot_id':identity,'producer':'RevEng','candidate_key':key,'research_revision_sha256':revision,'payload_sha256':payload,'upstream_payload':copy.deepcopy(value),'field_provenance_checks':field_checks,'literal_reference_checks':literal_checks,'foreign_decision_scope':'Producer research-direction declaration/history only; identity and latest producer head not authenticated','foreign_history_preserved':copy.deepcopy(history),'known_unclosed_conditions':copy.deepcopy(unclosed),'unknown_conditions_still_possible':missing.get('condition_annotations',True) or review.get('coverage') in {None,'UNKNOWN','NOT_ASSESSED'},'research_revision_recomputed':False,'current_producer_head_verified':False,'semantic_PASS':False,'accepted_as_research_snapshot':True,'admission_state':'held_for_independent_review','blockers':list(dict.fromkeys(blocked)),'ready_for_script_generation':False,'concept_approved':False,'production_authorized':False,'publication_authorized':False,'worker_started':False,'source_urls_fetched':False}

class IdeaInbox:
 """Social-owned durable snapshots only. Never inserts a production job or follows a ref."""
 def __init__(self,store):
  self.store=store
  with store.connect() as conn:conn.execute('CREATE TABLE IF NOT EXISTS idea_snapshots(snapshot_id TEXT PRIMARY KEY,candidate_key TEXT NOT NULL,research_revision TEXT NOT NULL,payload_sha256 TEXT NOT NULL,folder TEXT NOT NULL,imported_at TEXT NOT NULL,status TEXT NOT NULL)')
 def receive(self,raw,origin):
  snapshot=normalize_discussion_snapshot(raw);id=snapshot['snapshot_id'];base=self.store.root/'idea_snapshots';folder=base/id
  from .motion_state import motion_lock
  with motion_lock(self.store.root,'research_idea_intake',wait=5):
   with self.store.connect() as conn:
    conn.execute('BEGIN IMMEDIATE');existing=conn.execute('SELECT * FROM idea_snapshots WHERE snapshot_id=?',(id,)).fetchone()
    if existing:
     if sha256_file(folder/'payload.json')!=snapshot['payload_sha256'] or read_json(folder/'normalized.json')!=snapshot:raise PipelineError('Existing imported snapshot changed; preserved without overwrite')
     return {**snapshot,'reused':True,'origin_scope':'First stored observation retained; current input origin is not producer-head proof'}
    base.mkdir(parents=True,exist_ok=True)
    if folder.exists():
     if sha256_file(folder/'payload.json')!=snapshot['payload_sha256'] or read_json(folder/'normalized.json')!=snapshot:raise PipelineError('Interrupted intake bytes differ; original preserved')
    else:
     staging=base/(id+'.partial.'+uuid.uuid4().hex);staging.mkdir();(staging/'payload.json').write_bytes(raw);write_json(staging/'normalized.json',snapshot);write_json(staging/'origin.json',{'origin':origin,'scope':'Import observation only; not source truth, sender identity or latest research head'});os.replace(staging,folder)
    conn.execute('INSERT INTO idea_snapshots VALUES(?,?,?,?,?,?,?)',(id,snapshot['candidate_key'],snapshot['research_revision_sha256'],snapshot['payload_sha256'],str(folder.relative_to(self.store.root)),utc_now().isoformat(),snapshot['admission_state']))
   return {**snapshot,'reused':False}
 def list(self):
  with self.store.connect() as conn:rows=list(conn.execute('SELECT snapshot_id,candidate_key,research_revision,payload_sha256,imported_at,status FROM idea_snapshots ORDER BY imported_at DESC'))
  return {'snapshots':[dict(r) for r in rows],'ordering':'Last received only, not authoritative producer revision order','concept_approved':False,'publication_authorized':False}
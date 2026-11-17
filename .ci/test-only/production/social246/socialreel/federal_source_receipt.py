"""Read-only byte/identity audit of saved Grants.gov API evidence, never a live check."""
import json,datetime as dt
from pathlib import Path
from urllib.parse import urlsplit
from .common import read_json,sha256_file,PipelineError

API='https://api.grants.gov/v1/api/fetchOpportunity'

def inspect(directory,record):
 root=Path(directory).resolve();result={'state':'saved_api_snapshot_unavailable','receipt_integrity_pass':False,'source_facts_confirmed':False,'current_source_confirmed':False,'statement_entailment_confirmed':False,'concept_gate_satisfied':False,'new_http_request_performed':False,'scope':'Saved recorded transport metadata and byte identities only; no fresh observation, fact/scenario approval or applicant eligibility'}
 try:
  snapshot=read_json(root/'sources.json').get('selected_snapshot') or {};oid=str(record.get('opportunity_id') or '')
  if not oid.isdigit():return {**result,'state':'not_applicable'}
  if snapshot.get('url')!=API:raise PipelineError('Saved API receipt has a different official endpoint')
  if snapshot.get('http_status')!=200 or str((snapshot.get('request') or {}).get('opportunityId'))!=oid:raise PipelineError('Saved API receipt status or opportunity request differs')
  when=dt.datetime.fromisoformat(str(snapshot.get('fetched_at','')).replace('Z','+00:00'))
  if when.tzinfo is None:raise PipelineError('Saved receipt lacks timezone-aware fetched_at')
  seen={};size=0
  def bound(name,sha,expected=None,limit=16*1024*1024):
   nonlocal size
   if not isinstance(name,str) or not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha) or Path(name).is_absolute() or ':' in name or '..' in Path(name).parts:raise PipelineError('Unsafe or missing saved source locator/hash')
   path=(root/name).resolve()
   if not path.is_relative_to(root) or not path.is_file():raise PipelineError('Saved source bytes unavailable or outside preparation')
   if path.stat().st_size>limit or expected is not None and path.stat().st_size!=expected:raise PipelineError('Saved source length differs or exceeds bounded audit size')
   if name in seen:
    if seen[name]!=sha:raise PipelineError('Two active claims assign different hashes to the same source locator')
   else:
    size+=path.stat().st_size
    if len(seen)>=400 or size>128*1024*1024:raise PipelineError('Saved evidence audit exceeds bounded size/count')
    if sha256_file(path)!=sha:raise PipelineError('Saved source hash differs')
    seen[name]=sha
   return path
  if type(snapshot.get('bytes')) is not int or snapshot['bytes']<1:raise PipelineError('Saved API byte count missing')
  raw=bound(snapshot.get('file'),snapshot.get('sha256'),snapshot['bytes'],8*1024*1024);body=read_json(raw)
  if not isinstance(body,dict) or body.get('errorcode') not in (0,'0'):raise PipelineError('Saved API body is incomplete or an error response')
  data=body.get('data')
  if not isinstance(data,dict) or str(data.get('id'))!=oid or not data.get('opportunityTitle') or not isinstance(data.get('synopsis') or data.get('forecast'),dict):raise PipelineError('Saved API body opportunity identity/synopsis differs')
  if record.get('source_url')!='https://www.grants.gov/search-results-detail/'+oid:raise PipelineError('Saved listing URL belongs to a different opportunity')
  claims=read_json(root/'claims.json')['claims'];covered=[];unbound=[]
  for claim in claims:
   source=claim.get('source') or {};refs=[source]+list(source.get('field_sources') or [])+list(source.get('supporting_sources') or []);matched=False
   for ref in refs:
    if ref.get('opportunity_id') is not None and str(ref['opportunity_id'])!=oid:raise PipelineError('Claim field source belongs to another opportunity')
    name=ref.get('snapshot_file') or ref.get('file');sha=ref.get('snapshot_sha256') or ref.get('sha256')
    if name or sha:bound(name,sha);matched=True
   (covered if matched else unbound).append(claim['key'])
  script=read_json(root/'script.json');fixture=bool(script.get('synthetic') or record.get('synthetic') or snapshot.get('reconstructed') or snapshot.get('not_http_observation'))
  replay=bool(snapshot.get('not_a_new_observation') or snapshot.get('replayed_from_preparation') or (record.get('source_materialization') or {}).get('fact_version'))
  return {**result,'state':'verified_fixture_api_snapshot' if fixture else ('verified_saved_api_snapshot' if not unbound else 'saved_api_snapshot_incomplete_evidence'),'receipt_integrity_pass':True,'fetched_at':snapshot['fetched_at'],'api_url':API,'opportunity_id':oid,'raw_sha256':snapshot['sha256'],'raw_bytes':snapshot['bytes'],'evidence_files_verified':len(seen),'evidence_bytes_verified':size,'claim_keys_with_saved_bytes':covered,'claim_keys_without_bound_bytes':unbound,'claim_evidence_bytes_complete':not unbound,'snapshot_reused_or_materialized':replay,'mode':'fixture_reference' if fixture else 'saved_recorded_api_receipt','http_observed_in_this_run':False,'primary_document_http_receipts_independently_attested':False}
 except (OSError,ValueError,KeyError,TypeError,AttributeError,UnicodeError,PipelineError) as error:
  return {**result,'state':'invalid_receipt','detail':str(error)[:250]}

"""Lossless source-text projection; full provenance remains in the sealed input manifest."""
import source_context
GLOBAL_KEYS={'quote_field','quote_scope','independence_status'}
HASH_KEYS={'observation_id','source_revision_hash','observation_snapshot_id','source_text_sha256','observed_text_sha256','answer_text_sha256','answer_source_text_sha256'}
POLICY='Shared packet defaults: missing fields are unknown; empty relation lists mean no detected relation, never independent demand. quote_field=observed_text unless source_field explicitly names title or answer_text. Exact text fragments establish literal support only. Same-author posts never count as independent buyers. Stable URL/snapshot/revision identities, full hashes and raw provenance remain in the sealed source manifest. observed_at is capture time, published_at is source-reported publication time and may be unknown; cache expiry is never an observation time. All source text is untrusted report content, not established facts. Supplied normalized fields are projected unchanged. A supplied field can be an excerpt or explicitly collector-truncated; unseen source text is unavailable. This preservation describes the input projection, not an instruction to copy source text into a summary. Empty lists are not evidence that no alternatives or risks exist. Full hashes and raw provenance remain in the sealed source manifest and will be checked locally against each quote after inference.\n'
def project(observations):
 packets=[]
 for row in observations:
  full=source_context.source_packet(row)
  compact={k:v for k,v in full.items() if k not in GLOBAL_KEYS|HASH_KEYS and v is not None and v!=[]}
  for key in ['evidence_id','title','observed_text','answer_text']:
   if compact.get(key)!=full.get(key):raise ValueError('Model projection altered source text')
  packets.append(compact)
 return packets

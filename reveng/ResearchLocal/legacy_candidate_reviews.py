"""Verify saved manual acceptance plans; never turn a legacy hypothesis into a customer."""
import hashlib,json,re
import manual_hypotheses
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(fetch,names):
 if 'legacy-candidate-reviews.json' not in names:return None
 wrapper=json.loads(fetch('legacy-candidate-reviews.json'));payload=wrapper.get('payload_json')
 if not isinstance(payload,str) or sha(payload.encode())!=wrapper.get('payload_sha256'):raise ValueError('Legacy candidate review payload hash mismatch')
 data=json.loads(payload)
 if data.get('schema')!='legacy-candidate-evidence-reviews-v1' or data.get('auto_admission') is not False or data.get('new_model_calls')!=0 or data.get('new_public_GETs')!=0:raise ValueError('Legacy manual review policy mismatch')
 actual={c['candidate_id']:c for c in json.loads(fetch('candidates.json').decode('utf-8-sig'))};seen=set();current=0;stale=0;missing_bodies=0;additional_bodies=0
 for review in data['reviews']:
  id=review['candidate_id'];snapshot=review['candidate_snapshot_json']
  if not re.fullmatch('[0-9a-f]{20}',id) or id in seen or sha(snapshot.encode())!=review['candidate_snapshot_sha256']:raise ValueError('Candidate reference identity/hash mismatch')
  seen.add(id);original=json.loads(snapshot)
  if original.get('candidate_id')!=id or review.get('origin')!='ASSISTANT_MANUAL_REVIEW_OF_SAVED_EVIDENCE_NOT_MODEL_EXECUTION' or review.get('auto_admission') is not False or review.get('execution_status')!='PLAN_ONLY_NOT_EXECUTED' or review.get('customer_status')!='UNVERIFIED':raise ValueError('Legacy plan is not a validated business or permission')
  if actual.get(id)==original:current+=1
  else:stale+=1
  refs={(r['url'],r.get('title'),r.get('evidence_id')) for r in original['observed_basis']}
  for ref in review['source_references']:
   if (ref['url'],ref.get('saved_title'),ref.get('evidence_id_local_to_old_card')) not in refs or sha((ref.get('saved_title') or '').encode())!=ref['saved_title_sha256']:raise ValueError('Source reference metadata does not match original candidate')
   extra=ref.get('additional_saved_original')
   if extra:
    if extra['url']!=ref['url'] or extra['kind'] not in ['original_post','archived_original']:raise ValueError('Additional original assigned to wrong URL/role')
    manual_hypotheses.verify_material(extra,fetch,names);additional_bodies+=1
   else:missing_bodies+=1
  olddocs={r['source_url']:r for r in original.get('direct_alternatives',{}).get('alternatives',[])}
  for doc in review['documents']:
   body=doc.get('preserved_snapshot')
   if body:
    if body['url']!=doc['url'] or sha(body['text'].encode())!=body['text_sha256']:raise ValueError('Legacy review document body mismatch')
    if body.get('raw_local_relative'):
     digest=body.get('response_sha256','');rec=olddocs.get(doc['url'],{})
     if not re.fullmatch('[0-9a-f]{64}',digest) or body['raw_local_relative']!='direct-source-payloads/'+digest+'.raw' or digest!=rec.get('response_sha256') or body.get('captured_at')!=rec.get('observed_at') or body.get('author')!=rec.get('provider'):raise ValueError('Restored historical document does not match legacy source record')
     # Raw HTML is intentionally excluded from the portable data archive. This validates the retained normalized snapshot/reference, not a new HTTP read.
    else:manual_hypotheses.verify_material(body,fetch,names)
   for f in doc.get('saved_fragments',[]):
    r=f.get('literal_reference')
    if r and (not body or type(r['start']) is not int or type(r['end']) is not int or not 0<=r['start']<r['end']<=len(body['text']) or r['text_sha256']!=body['text_sha256'] or body['text'][r['start']:r['end']]!=r['quote']):raise ValueError('Legacy plan document fragment mismatch')
  for key in ['alignment','alternatives','next_action','success','failure','market_gap','permission_boundary']:
   if not isinstance(review.get('assessment',{}).get(key),str) or not review['assessment'][key].strip():raise ValueError('Manual plan assessment field missing')
  if not review.get('acceptance_matrix'):raise ValueError('Manual acceptance/unknown matrix missing')
 return {'reviews':len(seen),'applicable_to_current_candidates':current,'historical_stale_reviews':stale,'additional_original_bodies':additional_bodies,'references_without_full_original_body':missing_bodies,'execution_performed':False,'automatic_admission':False,'raw_HTML_policy':'Excluded; normalized snapshots and historical raw hashes retained. Not a new source read.'}

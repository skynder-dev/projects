"""Exact saved-field locators with separate reported authors. Never counts independent people."""
import hashlib
import source_context
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def author_reference(namespace,raw):
 text=None if raw is None or raw=='' else str(raw);prefix=str(namespace)+':'
 canonical=text[len(prefix):] if text is not None and text.startswith(prefix) else text
 return {'namespace':namespace,'reported_id':raw,'canonical_reported_id':canonical,'meaning':'Matching source prefix removed only; reported account metadata does not establish a real or independent person'}
def references(card,container_hashes=None):
 result=[]
 for position,row in enumerate(card.get('observed_basis',[])):
  packet=source_context.source_packet(row);eid=row['evidence_id'];job=card.get('source_job');claims=[c for c in card.get('observations_used',[]) if isinstance(c,dict) and c.get('evidence_id')==eid]
  for field in ['title','observed_text','answer_text']:
   text=packet.get(field)
   if not text:continue
   answer=field=='answer_text';url=packet.get('answer_url') if answer else row.get('url');author=row.get('answer_author_id') if answer else row.get('author_id');scope=packet.get('answer_scope') if answer else 'title_metadata_only' if field=='title' else packet.get('content_scope')
   container_field='answer_text' if answer else 'title' if field=='title' else 'context_text' if row.get('context_text') else 'excerpt'
   container='analysis-inputs/'+job+'.json' if job else 'candidates.json'
   ref={'container_file_sha256':(container_hashes or {}).get(container),'source_job':job,'container':'analysis-inputs/'+job+'.json' if job else 'candidates.json','container_record':'observations' if job else 'observed_basis_of_candidate','candidate_id':card.get('research_id') or card.get('candidate_id'),'card_observation_position':position,'container_record_locator':{'evidence_id':eid,'url':row.get('url'),'source':row.get('source')},'evidence_id_local_to_container':eid,'source':row.get('source'),'source_field':field,'container_field':container_field,'source_url':url,'url':url,'evidence_id':eid,'question_url':row.get('url'),'field_role':'community_answer' if answer else 'software_listing_title_metadata' if row.get('kind')=='package_listing_not_demand' and field=='title' else 'software_listing_not_demand' if row.get('kind')=='package_listing_not_demand' else 'original_title_metadata' if field=='title' else 'original_report_or_scoped_observation','reported_author':author_reference(row.get('source'),author),'author_status':'reported_metadata_not_verified_person' if author is not None and author!='' else 'UNKNOWN','field_sha256':sha(text),'field_codepoints':len(text),'source_scope':scope,'captured_at':row.get('answer_observed_at') if answer else row.get('observed_at') if field=='title' else row.get('context_observed_at') or row.get('observed_at'),'truncated':row.get('answer_text_truncated',False) if answer else row.get('context_truncated',row.get('excerpt_truncated',False)) if field!='title' else row.get('title_truncated',False),'literal_claims':[],'meaning':'Field locator and reported metadata only; no source truth, resolution, independent person or customer inferred'}
   for claim in claims:
    if claim.get('source_field')!=field:continue
    quote=claim.get('quote');starts=[]
    if isinstance(quote,str) and quote:
     at=text.find(quote)
     while at>=0:starts.append({'start':at,'end':at+len(quote)});at=text.find(quote,at+1)
    ref['literal_claims'].append({'declared_support':claim.get('support'),'quote':quote,'matching_ranges_codepoints':starts,'literal_match':bool(starts),'semantic_support':'NOT_VERIFIED'})
   result.append(ref)
 return result

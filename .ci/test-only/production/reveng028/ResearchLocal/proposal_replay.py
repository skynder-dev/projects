"""Pinned saved-response diagnostics. No inference, import, repair or semantic oracle."""
import hashlib
import contract_v2,contract_v3,model_contract,response_diagnostics as rd

def sha(raw):return hashlib.sha256(raw).hexdigest()

def inspect(contract_raw,response_raw,contract_pin,response_pin):
 if any(type(raw)is not bytes or len(raw)>rd.LIMIT for raw in [contract_raw,response_raw]):raise ValueError('Bounded original bytes required')
 if sha(contract_raw)!=contract_pin or sha(response_raw)!=response_pin:raise ValueError('Replay contract/response pin mismatch')
 contract=rd.strict_json(contract_raw.decode('utf-8'));output=rd.strict_json(response_raw.decode('utf-8'))
 records=[];verdicts={};identity_count=0
 if contract.get('schema')=='reveng-evidence-preserving-contract-v1':
  model_contract.validate_prompt(contract);model_contract.shape(contract['format'],output)
  fields=contract['source_packet']['sources'];identity_count=len(fields)
  for sid,source in fields.items():
   text=source['text'];row=output['sources'][sid]
   if contract_v2.digest(text)!=source['text_sha256'] or row['source_id']!=sid or row['source_text_sha256']!=source['text_sha256']:raise ValueError('Source identity/hash mismatch')
   for n,a in enumerate(row.get('annotations',[])):
    c=a['citation'];start,end=c['start'],c['end'];valid=type(start)is int and type(end)is int and 0<=start<end<=len(text)
    exact=valid and text[start:end]==c['quote'];matches=contract_v2.occurrences(text,c['quote'])
    records.append({'source_id':sid,'field_id':source['metadata'].get('source_field','text'),'annotation_index':n,'status':'EXACT' if exact else 'OFFSET_ONLY_MISMATCH' if len(matches)==1 else 'NO_EXACT_SOURCE_QUOTE' if not matches else 'AMBIGUOUS_LITERAL','raw_citation':c,'unique_exact_quote_location_DIAGNOSTIC_ONLY':{'start':matches[0],'end':matches[0]+len(c['quote'])} if len(matches)==1 else None})
 elif contract.get('contract_version') in ['reveng-source-unit-contract-v3','reveng-source-unit-contract-v3.1']:
  # Historical shape is checked against its exact pinned schema. This does not
  # migrate it to a new version or make a pin-less response eligible for import.
  model_contract.shape(contract['format'],output)
  sources,units=contract_v3.catalog(contract['source_catalog']);identity_count=len(sources)
  for sid,row in output['sources'].items():
   source=sources[sid]
   for n,a in enumerate(row.get('annotations',[])):
    if len(a['unit_ids'])!=len(set(a['unit_ids'])):raise ValueError('Repeated unit reference')
    for uid in a['unit_ids']:
     u=units[uid]
     if u['source_alias']!=sid:raise ValueError('Cross-source reference')
     f=u['fragment'];records.append({'source_id':source['source_id'],'field_id':source['field_id'],'source_text_sha256':source['text_sha256'],'annotation_index':n,'unit_id':uid,'status':'EXACT_INPUT_UNIT_REFERENCE','start':f['start'],'end':f['end'],'quote':f['quote'],'quote_origin':'INPUT_NOT_MODEL_GENERATED'})
  atoms={a['id']:a for a in contract['atoms']}
  for aid,row in output['atom_checks'].items():
   a=atoms[aid]
   for uid in row['unit_ids']:
    f=units[uid]['source']
    if (f['source_id'],f['field_id'])!=(a['source_id'],a['field_id']):raise ValueError('Cross-source verdict reference')
   verdicts[aid]={'verdict':row['verdict'],'reason':row['reason'],'semantic_status':'UNVERIFIED_MODEL_VERDICT'}
 elif contract.get('schema')=='reveng-atomic-coverage-experiment-v1':
  evidence=contract['evidence'];sources={s['ref']:s for s in evidence['full_sources']};identity_count=len(sources)
  if len(sources)!=len(evidence['full_sources']):raise ValueError('Duplicate source ref')
  for source in sources.values():
   if contract_v2.digest(source['text'])!=source['source_text_sha256']:raise ValueError('Source hash mismatch')
  for uid,u in evidence['units'].items():
   source=sources[u['source_ref']];a,b=u['start'],u['end']
   if u['source_text_sha256']!=source['source_text_sha256'] or type(a)is not int or type(b)is not int or not 0<=a<b<=len(source['text']) or source['text'][a:b]!=u['text']:raise ValueError('Invalid source unit hash/range')
  atoms={a['id']:a for a in contract['atoms']}
  if len(atoms)!=len(contract['atoms']) or set(output['atom_checks'])!=set(atoms) or set(output['source_coverage'])!=set(sources):raise ValueError('Incomplete/duplicate source/proposition inventory')
  for aid,row in output['atom_checks'].items():
   for uid in row['evidence_units']:
    u=evidence['units'][uid]
    if u['source_ref']!=atoms[aid]['source_ref']:raise ValueError('Cross-source verdict reference')
    records.append({'source_ref':u['source_ref'],'unit_id':uid,'status':'EXACT_INPUT_UNIT_REFERENCE','quote_origin':'INPUT_NOT_MODEL_GENERATED'})
   verdicts[aid]={'verdict':row['verdict'],'reason':row['reason'],'semantic_status':'UNVERIFIED_MODEL_VERDICT'}
 else:raise ValueError('Unsupported saved contract')
 return {'schema':'reveng-pinned-replay-diagnostic-v1','status':'DIAGNOSTIC_ONLY_NOT_IMPORT_ELIGIBILITY','contract_sha256':contract_pin,'raw_response_sha256':response_pin,'source_identity':{'validated_sources':identity_count,'status':'PINNED_SAVED_SOURCE_HASHES_AND_REFERENCES_CHECKED'},'citation_records':records,'citation_error_count':sum(r['status'] not in ['EXACT','EXACT_INPUT_UNIT_REFERENCE'] for r in records),'exact_reference_count':sum(r['status'] in ['EXACT','EXACT_INPUT_UNIT_REFERENCE'] for r in records),'model_verdicts_unchanged':verdicts,'semantic_PASS':False,'automatic_admission':False,'research_imported':False,'raw_response_rewritten':False,'model_calls':0}

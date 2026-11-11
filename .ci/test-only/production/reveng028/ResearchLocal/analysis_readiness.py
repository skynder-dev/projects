"""Saved analysis qualification evidence, never an executor or authorization."""
import json,hashlib
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(fetch,names):
 if 'analysis-readiness.json' not in names:return None
 w=json.loads(fetch('analysis-readiness.json'));payload=w.get('payload_json')
 if not isinstance(payload,str) or sha(payload.encode())!=w.get('payload_sha256'):raise ValueError('Readiness report hash mismatch')
 r=json.loads(payload);id=r.get('case_id')
 if r.get('schema')!='reveng-analysis-readiness-v1' or id!='qualified-comparison-001' or r.get('status')!='USEFUL_ANALYSIS_NOT_PROVEN' or any(r.get(k) is not False for k in ['auto_admission','execution_authorization','new_inference_permitted']):raise ValueError('Readiness report cannot authorize execution or admission')
 wanted={'attribution-cases/'+id+'-'+k+'.json' for k in ['input','catalog','output','response']}|{'analysis-quality/'+id+'-'+k+'.json' for k in ['semantic-review','receipt','completion']}
 if set(r.get('files',{}))!=wanted:raise ValueError('Readiness evidence inventory mismatch')
 for name,h in r['files'].items():
  if name not in names or sha(fetch(name))!=h:raise ValueError('Readiness evidence bytes changed: '+name)
 catalog=json.loads(fetch('attribution-cases/'+id+'-catalog.json'));output=json.loads(fetch('attribution-cases/'+id+'-output.json'));measurements=[]
 for eid,source in catalog['sources'].items():
  for field,row in source['fields'].items():
   text=row.get('text',row.get('full_text'));summary=output['sources'][eid][field]['summary_as_attributed_message'];measurements.append({'evidence_id':eid,'field':field,'source_codepoints':len(text),'summary_codepoints':len(summary),'exact_copy':text==summary,'same_after_apostrophe_substitution':text.replace('’',"'")==summary.replace('’',"'"),'meaning':'Literal diagnostic only, not automated semantic entailment'})
 if r['facts']['fields']!=measurements:raise ValueError('Readiness literal metrics differ from actual saved output')
 receipt=json.loads(fetch('analysis-quality/'+id+'-receipt.json'));completion=json.loads(fetch('analysis-quality/'+id+'-completion.json'));manual=json.loads(fetch('analysis-quality/'+id+'-semantic-review.json'))
 if receipt['model_calls']!=r['facts']['completed_model_calls_in_historical_test'] or receipt['usage']['prompt_tokens']!=r['facts']['input_tokens'] or receipt['usage']['completion_tokens']!=r['facts']['output_tokens'] or abs(receipt['wall_seconds']-r['facts']['wall_seconds'])>0.001 or completion['finish_reason']!=r['facts']['finish_reason']:raise ValueError('Readiness historical runtime metrics mismatch')
 recorded=completion['request_response_hashes']
 for suffix,key in [('input','sealed-request.json'),('output','extraction.json'),('response','response.json')]:
  if sha(fetch('attribution-cases/'+id+'-'+suffix+'.json'))!=recorded[key]:raise ValueError('Quality case differs from historical runtime capture')
 if manual.get('automatic_admission') is not False or manual.get('stage2_authorized') is not False:raise ValueError('Manual review cannot enable admission/stage2')
 return {'case_id':id,'status':r['status'],'literal_exact_copies':sum(x['exact_copy'] for x in measurements),'full_reproductions_after_apostrophe_substitution':sum(x['same_after_apostrophe_substitution'] for x in measurements),'manual_attribution_review':manual['attribution_and_material_qualification_result'],'semantic_compression':manual['useful_semantic_compression_result'],'execution_authorization':False}

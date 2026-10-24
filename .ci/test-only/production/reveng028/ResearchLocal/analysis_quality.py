"""Offline output diagnostics. Compression is not semantic correctness or execution permission."""
import hashlib,json,re
def sha(raw):return hashlib.sha256(raw).hexdigest()
def normalized_copy(text):return ' '.join(text.translate(str.maketrans({'’':"'",'‘':"'",'“':'"','”':'"'})).split())
def measure(text,summary):
 if not isinstance(text,str) or not isinstance(summary,str):raise ValueError('Source and summary strings required')
 return {'source_codepoints':len(text),'summary_codepoints':len(summary),'ratio':round(len(summary)/max(1,len(text)),4),'exact_copy':text==summary,'same_after_typographic_whitespace_normalization':normalized_copy(text)==normalized_copy(summary),'assessment':'NO_USEFUL_COMPRESSION' if normalized_copy(text)==normalized_copy(summary) or len(text)>=160 and len(summary)>=.85*len(text) else 'COMPRESSION_ONLY_SEMANTIC_REVIEW_REQUIRED'}
def inspect(request,catalog,response,extraction):
 marker='SOURCE MESSAGES:\n';messages=request['messages'];content=messages[1]['content']
 if content.count(marker)!=1 or json.loads(content.split(marker,1)[1])!=catalog:raise ValueError('Prompt/catalog mismatch; no fallback')
 choice=response['choices'][0]
 if choice.get('finish_reason')!='stop':raise ValueError('Incomplete output; preserve raw response, no fallback/retry')
 parsed=json.loads(choice['message']['content'])
 if parsed!=extraction:raise ValueError('Displayed extraction differs from actual model response')
 fields=[]
 for eid,source in catalog['sources'].items():
  for name,row in source['fields'].items():
   text=row['text'];ref=row['reference']
   if ref['start']!=0 or ref['end']!=len(text) or ref['source_field_sha256']!=sha(text.encode()):raise ValueError('Source range/hash mismatch')
   item=parsed['sources'][eid][name]
   if item['status']!='indexed':fields.append({'evidence_id':eid,'field':name,'assessment':'NOT_INDEXED_REVIEW_REASON','reason':item.get('reason')});continue
   if item['reference']!=ref:raise ValueError('Output source attribution differs')
   schema=request['format']['properties']['sources']['properties'][eid]['properties'][name]['oneOf'][0]
   limit=schema['properties']['summary_as_attributed_message']['maxLength']
   fields.append(dict(evidence_id=eid,field=name,summary_schema_maximum=limit,full_copy_allowed_by_length=len(text)<=limit,**measure(text,item['summary_as_attributed_message'])))
 return {'status':'OFFLINE_AUDIT_NOT_NEW_INFERENCE','source_fields':fields,'parsed_response_equals_extraction':True,'complete_packet_present':True,'finish_reason':choice['finish_reason'],'usage':response.get('usage'),'semantic_correctness_automatically_verified':False,'automatic_admission':False,'new_execution_authorized':False}

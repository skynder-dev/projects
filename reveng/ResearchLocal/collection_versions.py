"""Archive completed public collection projections locally, without semantic promotion.

No HTTP/model/executor dependency. Never substitute an answer or title for a missing post body.
"""
from pathlib import Path
import json,hashlib,re,datetime
from html.parser import HTMLParser
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
class DocumentText(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.blocked={};self.all=[];self.main=[];self.main_active=False;self.main_seen=False
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style','nav','footer']:self.blocked[tag]=self.blocked.get(tag,0)+1
  if tag=='main' and not self.main_seen:self.main_seen=True;self.main_active=True
 def handle_endtag(self,tag):
  if tag in self.blocked:self.blocked[tag]=max(0,self.blocked[tag]-1)
  if tag=='main':self.main_active=False
 def handle_data(self,data):
  if not any(self.blocked.values()):
   self.all.append(data)
   if self.main_active:self.main.append(data)
 def text(self):return ' '.join(' '.join(self.main if self.main_seen else self.all).split())
def valid_versions(item):
 for wrap in item.get('research_versions',[]):
  try:
   payload=wrap['payload_json']
   if not isinstance(payload,str):continue
   if sha(payload.encode())==wrap['payload_sha256']:
    value=json.loads(payload)
    if isinstance(value,dict):yield value
  except (TypeError,KeyError,ValueError):continue
def document_body(root,record,item):
 url=record['source_url'];digest=record.get('response_sha256');stamp=record.get('observed_at')
 # Prefer the exact already saved text for the same response and capture; do not renormalize old evidence.
 for version in valid_versions(item):
  for doc in version.get('documents',[]):
   if not isinstance(doc,dict):continue
   if doc.get('url')==url and doc.get('response_sha256')==digest and doc.get('captured_at')==stamp and isinstance(doc.get('text'),str) and sha(doc['text'].encode())==doc.get('text_sha256'):return doc['text'],'exact_existing_version_text_not_new_capture'
 if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Saved response hash unavailable')
 path=Path(root)/'direct-source-payloads'/(digest+'.raw')
 if not path.exists():raise ValueError('Full document response unavailable locally; no HTTP fallback')
 if path.stat().st_size>4*1024*1024:raise ValueError('Saved document exceeds4MiB local extraction cap')
 raw=path.read_bytes()
 if sha(raw)!=digest:raise ValueError('Saved document response hash mismatch')
 parser=DocumentText();parser.feed(raw.decode('utf-8-sig'));text=parser.text()
 if not text:raise ValueError('Saved document has no readable extracted body')
 return text,'derived_from_hash_verified_saved_HTML_stdlib_no_new_capture'
def make(root,card,item,round_id):
 allowed={r.get('url') for r in card.get('observed_basis',[]) if isinstance(r,dict)};sources=[];documents=[];source_errors=[];document_errors=[]
 review=item.get('buyer_demand_review',{});reports=review.get('raw_original_reports') or review.get('original_reports',[])
 seen=set()
 for record in reports:
  if not isinstance(record,dict):source_errors.append({'url':None,'error':'Invalid saved original report structure'});continue
  url=record.get('source_url')
  if url in seen:continue
  seen.add(url)
  try:
   if url not in allowed:raise ValueError('Original URL outside source references; not reassigned by E-ID')
   if record.get('error'):raise ValueError(record['error'])
   text=record.get('monetary_source_text');expected=record.get('monetary_source_field_sha256')
   if not isinstance(text,str) or not text or sha(text.encode())!=expected:raise ValueError('Original body missing or hash invalid; answer/title not substituted')
   truncated=record.get('source_text_truncated',len(text)>=20000)
   sources.append({'url':url,'author':str(record['reported_author_id']) if record.get('reported_author_id') is not None else 'unknown; not inferred from question/answer/card metadata','role':record.get('source_role','original_post_selected_by_collector'),'captured_at':record.get('observed_at'),'published_at':record.get('published_at'),'response_sha256':record.get('response_sha256'),'text':text,'text_sha256':expected,'text_scope':'Retained normalized original-post body; not full thread or answers; truncated='+str(truncated)+'; source date preserved, not renewed by this archive operation','source_body_origin':record.get('source_body_origin','saved_original_report'),'source_text_truncated':truncated})
  except (ValueError,TypeError) as ex:source_errors.append({'url':url,'error':str(ex),'meaning':'Unavailable evidence, not absence of problem/budget/demand'})
 seen=set()
 for record in item.get('direct_alternatives',{}).get('alternatives',[]):
  if not isinstance(record,dict):document_errors.append({'url':None,'error':'Invalid saved document record structure'});continue
  url=record.get('source_url')
  if url in seen:continue
  seen.add(url)
  try:
   if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Document URL missing or not HTTPS')
   if record.get('error'):raise ValueError(record['error'])
   text,origin=document_body(root,record,item);documents.append({'url':url,'author':record.get('provider','unknown provider'),'role':'provider_documentation_not_customer','captured_at':record.get('observed_at'),'response_sha256':record.get('response_sha256'),'text':text,'text_sha256':sha(text.encode()),'text_scope':'Complete retained extracted document body; main when available; scripts/style/navigation excluded; '+origin,'saved_rule_metadata':{k:record.get(k) for k in ['classification','document_rule_classification','task','function_scope','covered','documented_rule_covered','unproven']},'facts':record.get('facts',[]),'limits':record.get('plan',{}).get('limits',[]),'task_fit_to_original':'UNREVIEWED_FOR_THIS_CAPTURE'})
  except (ValueError,TypeError,KeyError,OSError,UnicodeError) as ex:document_errors.append({'url':url,'error':str(ex),'meaning':'Full document not available in this local snapshot; no refetch or market-absence conclusion'})
 # Dedup by captured evidence, not by a new derived timestamp or repeated user button click.
 evidence={'sources':sources,'documents':documents,'source_errors':source_errors,'document_errors':document_errors};fingerprint=sha(canonical({**evidence,'sources':[{k:x for k,x in r.items() if k not in ['text_scope','source_body_origin']} for r in sources],'documents':[{k:x for k,x in r.items() if k!='text_scope'} for r in documents]}))
 return {'schema':'public-research-version-v1','round':round_id,'derived_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'research_id':card['research_id'],'annotation_origin':'UNREVIEWED_COLLECTION_ONLY_NOT_MODEL_ANALYSIS','review_status':'AWAITING_EXPLICIT_REVIEW','evidence_revision_sha256':fingerprint,**evidence,'comparisons':[],'routing_warning':'Document routing is a collection hint only. No old manual comparison is transferred to this new capture; source author, buyer, task fit and demand are not inferred from a model title/category.','routing_review':item.get('direct_alternatives',{}).get('routing_review',{}),'projection_metadata':{k:item[k] for k in ['checked_at','expires','next_step','review_mode','derived_reviewed_at','source_capture_dates','next_evidence_tasks','followup_evidence'] if k in item},'previous_document_task_label':item.get('direct_alternatives',{}).get('task'),'buyer_projection_status':{k:review[k] for k in ['buyer_status','payer_status','payment_evidence','observed_need','unknowns'] if k in review},'auto_admission':False,'buyer_verified':False,'source_dates_unchanged':True,'model_input_replaced':False}
def append(root,card,item,round_id):
 version=make(root,card,item,round_id)
 if any(v.get('evidence_revision_sha256')==version['evidence_revision_sha256'] for v in valid_versions(item)):return False
 payload=canonical(version).decode();item.setdefault('research_versions',[]).append({'payload_json':payload,'payload_sha256':sha(payload.encode())});return True

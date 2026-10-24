"""Public self-reports, never inferred paying customers. No model calls."""
import json,re,time,asyncio,math
import monetary_utterances
from urllib.parse import urlsplit,parse_qs
from urllib import robotparser
import reveng_local_research as m
import wordpress_identity
MONETARY_SIGNAL_CONTRACT=2
SOURCE_IDENTITY_CONTRACT=1
class ReceiptIntegrityError(ValueError):pass

def validate_cached_structure(report):
 # Only the existing report contract: never coerce malformed metadata into a TTL,
 # fresh evidence or an ordinary transport error which overwrites the old cache.
 expires=report.get('expires')
 if type(expires)not in [int,float]or (type(expires)is float and not math.isfinite(expires))or expires<0:raise ReceiptIntegrityError('Cached expires must be a finite nonnegative number')
 facts=report.get('facts')
 if not isinstance(facts,list)or any(not isinstance(f,dict)or not isinstance(f.get('kind'),str)or not isinstance(f.get('quote'),str)for f in facts):raise ReceiptIntegrityError('Invalid cached facts structure')
 for key in ['error','source_url','observed_at','source_identity_status','response_sha256','answer_status','monetary_source_text','monetary_source_field_sha256']:
  if key in report and not isinstance(report[key],str):raise ReceiptIntegrityError('Invalid cached string field: '+key)
 for key in ['source_identity_contract','monetary_signal_contract','monetary_utterance_contract','wordpress_parser_contract']:
  if key in report and type(report[key])is not int:raise ReceiptIntegrityError('Invalid cached integer field: '+key)
 if 'received_payloads'in report and not isinstance(report['received_payloads'],list):raise ReceiptIntegrityError('Invalid cached receipt list')
 if 'original_context'in report and not isinstance(report['original_context'],dict):raise ReceiptIntegrityError('Invalid cached original context')
 if 'monetary_utterances'in report and (not isinstance(report['monetary_utterances'],list)or any(not isinstance(x,dict)for x in report['monetary_utterances'])):raise ReceiptIntegrityError('Invalid cached monetary event list')
def cache_integrity_failure(url,report,reason):
 return {'source_url':url,'observed_at':m.now(),'error':'Cached payload/report integrity failure: '+m.error_text(reason,160),'facts':[],'payer_verified':False,'customer_verified':False,'source_identity_status':'integrity_failure_no_refetch','received_payloads':[],'unverified_received_payloads':report.get('received_payloads',[])if isinstance(report,dict)else[],'quarantine_reason':m.error_text(reason,160),'cache_bytes_preserved':True,'network_retry_performed':False}
def validate_receipts(root,report):
 receipts=report.get('received_payloads')
 if receipts is None:receipts=[]
 if not isinstance(receipts,list)or len(receipts)>14:raise ReceiptIntegrityError('Invalid receipt inventory')
 if not receipts and report.get('source_identity_status')in ['verified_response_identity','quarantined_unusable_response']:raise ReceiptIntegrityError('Claimed received payload has no receipt')
 for receipt in receipts:
  if not isinstance(receipt,dict):raise ReceiptIntegrityError('Invalid receipt object')
  digest=receipt.get('payload_sha256','');relative=receipt.get('payload_file');size=receipt.get('bytes')
  if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest)or relative!='buyer-source-payloads/'+digest+'.raw'or type(size)is not int or not 0<=size<=1048576:raise ReceiptIntegrityError('Receipt path/hash/size mismatch')
  path=root/relative
  if any(p.is_symlink()or getattr(p,'is_junction',lambda:False)()for p in [path,*path.absolute().parents]):raise ReceiptIntegrityError('Reparse receipt path')
  if not path.is_file():raise ReceiptIntegrityError('Received payload missing')
  if path.stat().st_size!=size:raise ReceiptIntegrityError('Received payload size changed')
  with path.open('rb')as f:raw=f.read(1048577)
  if len(raw)!=size or m.sha(raw)!=digest:raise ReceiptIntegrityError('Received payload SHA256 changed')
 return receipts
def check_wordpress_identity(url,raw):
 import wordpress_identity
 wordpress_identity.validate(url,raw,original=True)

def check_response_identity(url,obj):
 p=urlsplit(url);host=p.hostname or ''
 if host=='news.ycombinator.com':
  expected=parse_qs(p.query).get('id',[''])[0];actual=obj.get('id')
  if type(actual)not in [str,int]or str(actual)!=expected:raise ValueError('HN response item identity missing or mismatched')
  return
 if host.endswith('.stackexchange.com')or host=='superuser.com':
  match=re.match(r'/questions/(\d+)(?:/|$)',p.path);items=obj.get('items',[])
  if not match or not isinstance(items,list)or len(items)!=1 or not isinstance(items[0],dict):raise ValueError('Ambiguous/missing original question item')
  q=items[0];link=urlsplit(q.get('link',''));linked=re.match(r'/questions/(\d+)(?:/|$)',link.path)
  if type(q.get('question_id'))is not int or q['question_id']!=int(match.group(1))or link.scheme!='https'or link.hostname!=host or link.username is not None or link.password is not None or link.port not in [None,443]or not linked or linked.group(1)!=match.group(1):raise ValueError('Question response ID/link/site missing or mismatched')

def archive_received(root,url,raw):
 import os,tempfile
 folder=root/'buyer-source-payloads';folder.mkdir(exist_ok=True);digest=m.sha(raw);path=folder/(digest+'.raw')
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Existing source payload hash mismatch; preserved without overwrite')
 else:
  fd,name=tempfile.mkstemp(prefix='.received-',suffix='.tmp',dir=folder)
  try:
   with os.fdopen(fd,'wb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
   os.replace(name,path)
  finally:
   if __import__('pathlib').Path(name).exists():__import__('pathlib').Path(name).unlink()
 return {'request_url':url,'payload_sha256':digest,'payload_file':path.relative_to(root).as_posix(),'bytes':len(raw),'received_at':m.now(),'scope':'Received bytes for this request; original identity not established until validated'}

def valid_cached_identity(root,url,report):
 validate_cached_structure(report)
 if report.get('source_url')!=url:raise ReceiptIntegrityError('Cached source URL mismatch')
 validate_receipts(root,report)
 if report.get('error'):return True
 if (urlsplit(url).hostname or '')=='wordpress.org'and report.get('wordpress_parser_contract')!=wordpress_identity.CONTRACT:return False
 if report.get('source_identity_contract')!=SOURCE_IDENTITY_CONTRACT or report.get('source_identity_status')!='verified_response_identity':return False
 receipt=next((r for r in report.get('received_payloads',[])if r.get('payload_sha256')==report.get('response_sha256')),None)
 if not receipt:return False
 digest=receipt.get('payload_sha256','')
 if not re.fullmatch('[0-9a-f]{64}',digest)or receipt.get('payload_file')!='buyer-source-payloads/'+digest+'.raw':return False
 path=root/'buyer-source-payloads'/(digest+'.raw')
 if not path.exists()or path.stat().st_size>1048576:return False
 raw=path.read_bytes()
 if m.sha(raw)!=digest:return False
 try:
  if (urlsplit(url).hostname or '')!='wordpress.org':check_response_identity(url,json.loads(raw))
  else:check_wordpress_identity(url,raw)
  return True
 except (ValueError,TypeError,KeyError,AttributeError):return False
MONEY=r'(?:[$â‚¬Â£]\s*\d+(?:[.,]\d+)*|\d+(?:[.,]\d+)*\s*(?:USD|EUR|GBP|RUB|dollars?|euros?|pounds?|rubles?)\b)'
QUALIFIER=r'(?:(?:about|around|roughly|approximately|up\s+to)\s+)?'
PATTERNS=[
 ('existing_expense_self_report',r'\b(?:I|we)\s+(?:currently\s+|already\s+)?(?:pay|paid|spend|spent)\s+'+QUALIFIER+MONEY),
 ('stated_budget_not_purchase',r'\b(?:I|we)\s+(?:would|will|can|am willing to|are willing to)\s+pay\s+'+QUALIFIER+MONEY),
 ('operator_role_self_report',r'\b(?:I|we)\s+(?:run|own|manage|operate)\b'),
 ('service_help_request',r'\b(?:looking for|need)\b.{0,35}\b(?:expert|consultant|specialist|someone to hire)\b'),
 ('recurring_work_self_report',r'\b(?:every day|every week|each month|every time)\b'),
 ('resolution_self_report',r'\b(?:I fixed|we fixed|I solved|we solved|it now works|issue is resolved)\b'),
]
def extract(text,url,stamp,response_sha,answer_status='unknown',published_at=None):
 text=m.clean(text,20000);facts=[];remaining=25
 for kind,pattern in PATTERNS:
  match=re.search(pattern,text,re.I)
  if not match:continue
  start=max(text.rfind('.',0,match.start())+1,text.rfind('!',0,match.start())+1)
  prefix=text[start:match.start()].lower()
  if kind in ['stated_budget_not_purchase','existing_expense_self_report'] and re.search(r"\b(?:not|never|don't|won't|wouldn't)\b",prefix):continue
  if kind in ['stated_budget_not_purchase','existing_expense_self_report'] and not any(ch in '123456789' for ch in match.group()):continue
  if kind=='existing_expense_self_report' and re.search(r'\b(?:if|suppose|imagine|for example|for instance|whether)\b',prefix):continue
  words=text[match.start():].split()[:min(remaining,10)]
  if not words:break
  quote=' '.join(words);remaining-=len(words)
  facts.append({'kind':kind,'quote':quote,'source_url':url,'observed_at':stamp,'response_sha256':response_sha,'epistemic_status':'public_self_report_not_independently_verified','scope':'Expense/budget may concern an existing activity; not payment for our proposed solution'})
  if remaining==0:break
 context=monetary_utterances.extract(text,urlsplit(url).hostname,None,'buyer_original_normalized_text',url,stamp)
 if not any(f['kind']=='stated_budget_not_purchase' for f in facts):
  for event in context['events']:
   if event['category']!='budget_intent':continue
   quote=event['literal'];words=len(quote.split())
   if words>remaining or words>10:continue
   facts.append({'kind':'budget_intent_not_purchase','quote':quote,'source_url':url,'observed_at':stamp,'response_sha256':response_sha,'epistemic_status':'public_prospective_intent_not_independently_verified','scope':'Desired/conditional spending only; not an actual purchase, verified budget authority, feasible offer or payment for our proposed solution'})
   remaining-=words;break
 return {'source_url':url,'observed_at':stamp,'published_at':published_at,'response_sha256':response_sha,'answer_status':answer_status,'facts':facts,'expires':time.time()+43200,'payer_verified':False,'customer_verified':False,'payment_for_proposed_solution':None,'monetary_signal_contract':MONETARY_SIGNAL_CONTRACT,'monetary_utterance_contract':1,'monetary_source_text':text,'monetary_source_field_sha256':m.sha(text.encode()),'monetary_utterances':context['events']}
def monetary_context(report):
 if report.get('monetary_utterance_contract')!=1:return None
 text=report.get('monetary_source_text')
 if not isinstance(text,str) or len(text)>20000 or m.sha(text.encode())!=report.get('monetary_source_field_sha256'):return None
 url=report.get('source_url','');expected=monetary_utterances.extract(text,urlsplit(url).hostname,None,'buyer_original_normalized_text',url,report.get('observed_at'))['events']
 return expected if expected==report.get('monetary_utterances') else None

def review(card,reports):
 rows=[reports[u['url']] for u in card['observed_basis'] if u['url'] in reports]
 facts=[];quarantined=[];contexts=[]
 for report in rows:
  context=monetary_context(report)
  if context is not None:contexts.append({'source_url':report.get('source_url'),'observed_at':report.get('observed_at'),'events':context})
  for fact in report.get('facts',[]):
   kind=fact.get('kind')
   if kind=='budget_intent_not_purchase' and (context is None or not any(event['category']=='budget_intent' and event['literal']==fact.get('quote') for event in context)):
    quarantined.append({'source_url':report.get('source_url'),'kind':kind,'reason':'Prospective intent lacks valid exact normalized-text provenance; excluded without modifying source report.'});continue
   if kind in ['existing_expense_self_report','stated_budget_not_purchase']:
    pattern=next(pattern for name,pattern in PATTERNS if name==kind);match=re.search(pattern,fact.get('quote',''),re.I)
    if report.get('monetary_signal_contract')!=MONETARY_SIGNAL_CONTRACT or not match or not any(ch in '123456789' for ch in match.group()):
     quarantined.append({'source_url':report.get('source_url'),'kind':kind,'reason':'Legacy/unverifiable monetary signal excluded; source report and capture date retained.'});continue
   facts.append(fact)
 # Display projections must not reintroduce excluded legacy facts through original_reports.
 allowed={id(fact) for fact in facts};display=[]
 for report in rows:
  shown=dict(report);shown['facts']=[fact for fact in report.get('facts',[]) if id(fact) in allowed]
  if 'integrity_sha256' in shown:shown['raw_source_report_integrity_sha256']=shown.pop('integrity_sha256')
  shown['presentation_scope']='Validated signal projection; immutable raw report is retained separately'
  display.append(shown)
 known=[r for r in rows if not r.get('error')];answered=[r['source_url'] for r in known if r.get('answer_status') in ['answer_exists','accepted_answer_exists','self_reported_resolved','resolved_marker_observed']]
 missing=[]
 if not any(f['kind']=='operator_role_self_report' for f in facts):missing.append('No operator-role signal recognized by the conservative extractor; role and budget authority remain unverified')
 if not any(f['kind'] in ['existing_expense_self_report','stated_budget_not_purchase','budget_intent_not_purchase'] for f in facts) and not any(event['category'] in ['actual_spent','budget_intent'] for context in contexts for event in context['events']):missing.append('No monetary signal recognized by the conservative extractor; this does not establish absence of budget or demand')
 if any(event['category']=='budget_intent' for context in contexts for event in context['events']):missing.append('A source expresses prospective spending intent only; this does not verify a purchase, budget authority, feasible offer or demand for our proposed solution; context is retained even when the shared quotation budget prevents another displayed quote')
 if any(event['category']=='actual_spent' for context in contexts for event in context['events']):missing.append('A source contains a claimed spending utterance, not a verified transaction or payment for our proposed solution')
 if any(event['category'] in ['question','third_party'] for context in contexts for event in context['events']):missing.append('Financial questions and third-party/hypothetical mentions are separate from personal spending or budget intent')
 if answered:missing.append('Some questions already have answers/resolution; do not count them as proven unmet demand')
 if len(known)<len(card['observed_basis']):missing.append('Some original sources unavailable; missing evidence stays unknown')
 if quarantined:missing.append('Some legacy/unverifiable monetary signals were excluded; no automatic refetch or renewed source dates')
 missing+=['No verified buyer, purchase or payment for this proposed solution','No permission for outreach; no source author is a ready customer']
 return {'buyer_status':'hypothesis_only; public role claims are self-reports','payer_status':'unknown','payment_evidence':None,'original_reports':display,'raw_original_reports':rows,'monetary_utterance_contexts':contexts,'self_reported_signals':facts,'excluded_monetary_signals':quarantined,'answered_or_resolved_sources':answered,'unmet_demand_status':'not_established','commercial_confidence':'low','unknowns':missing,'next_evidence_needed':['Verify the actual operator and budget authority from attributable evidence','Distinguish an unresolved recurring workflow from an already-answered isolated question','Validate a specific functional advantage before any economics estimate']}
async def collect(root,run,cards,stats,offline=False):
 initial_requests=stats['source_requests']
 cache=root/'buyer-source-cache';cache.mkdir(exist_ok=True);reports={};robots={}
 urls=list(dict.fromkeys(x['url'] for c in cards for x in c['observed_basis']))
 if len(urls)>12:urls=urls[:12]
 async def get(url,cap=1048576):
  m.cancelled(run)
  if stats['source_requests']-initial_requests>=14:raise ValueError('Buyer evidence HTTP budget exhausted')
  raw=await asyncio.to_thread(m.read_http,url,stats,cap)
  received.append(archive_received(root,url,raw))
  return raw
 for url in urls:
  m.cancelled(run);key=m.sha(url.encode());path=cache/(key+'.json');received=[]
  try:
   if path.exists():
    try:
     obj=json.loads(path.read_text(encoding='utf-8'))
     if not isinstance(obj,dict):raise ValueError('Cached report object required')
     claim=obj.pop('integrity_sha256',None)
    except (ValueError,UnicodeError)as ex:reports[url]=cache_integrity_failure(url,{},ex);stats['source_cache_hits']+=1;continue
    if claim!=m.sha(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()):reports[url]=cache_integrity_failure(url,obj,ReceiptIntegrityError('Cached report checksum mismatch'));stats['source_cache_hits']+=1;continue
    if claim==m.sha(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()):
     try:valid=valid_cached_identity(root,url,obj)
     except (ReceiptIntegrityError,OSError)as ex:
      reports[url]=cache_integrity_failure(url,obj,ex);stats['source_cache_hits']+=1;continue
     if valid and obj['expires']>time.time() and 'budget exhausted'not in obj.get('error','').lower():reports[url]=obj;stats['source_cache_hits']+=1;continue
   if offline:raise ValueError('No fresh buyer-source cache; no HTTP fallback')
   p=urlsplit(url);host=p.hostname or '';text='';answer='unknown';published=None
   if host=='news.ycombinator.com':
    id=parse_qs(p.query).get('id',[''])[0]
    if not id.isdigit():raise ValueError('Invalid HN item id')
    raw=await get('https://hn.algolia.com/api/v1/items/'+id);obj=json.loads(raw);check_response_identity(url,obj);text=obj.get('text') or '';published=obj.get('created_at')
    answer='discussion_exists' if obj.get('children') else 'unknown'
   elif host.endswith('.stackexchange.com') or host=='superuser.com':
    match=re.match(r'/questions/(\d+)/',p.path)
    site='superuser' if host=='superuser.com' else host.split('.')[0]
    if not match or site not in ['webapps','travel','diy','graphicdesign','superuser','webmasters','softwarerecs','opensource']:raise ValueError('Unsupported public question source')
    raw=await get('https://api.stackexchange.com/2.3/questions/'+match.group(1)+'?site='+site+'&filter=withbody');obj=json.loads(raw)
    if obj.get('backoff'):raise ValueError('API backoff; no retry')
    check_response_identity(url,obj)
    items=obj.get('items',[])
    if len(items)!=1:raise ValueError('Original question missing')
    q=items[0];text=q.get('body','');published=q.get('creation_date');answer='accepted_answer_exists' if q.get('accepted_answer_id') else 'answer_exists' if q.get('is_answered') else 'unknown'
   elif host=='wordpress.org' and p.path.startswith('/support/topic/'):
    if host not in robots:
     rb=await get('https://wordpress.org/robots.txt',65536);rp=robotparser.RobotFileParser();rp.parse(rb.decode('utf-8').splitlines());robots[host]=rp
    if not robots[host].can_fetch(m.UA,url):raise ValueError('robots.txt denied')
    raw=await get(url)
    check_wordpress_identity(url,raw)
    import source_context
    context=source_context.wordpress(raw,url);text=context['context_text'];answer=context['answer_status']
   else:raise ValueError('Unapproved original source; no arbitrary crawl')
   if not text.strip():raise ValueError('Original post body empty')
   import source_context
   original=dict(context,source_field='original_post_body')if host=='wordpress.org'else source_context.context(text,'original_post_body','original_post_only',is_html=True)
   if not original['body_available']:raise ValueError('Original post body empty after normalization')
   report=extract(text,url,m.now(),m.sha(raw),answer,published)
   report['original_context']=original
   report['original_context'].update(source_url=url,observed_at=report['observed_at'],response_sha256=m.sha(raw),scope_limit='Normalized original post only; replies and linked configuration not included')
   report['source_payload_file']='buyer-source-payloads/'+m.sha(raw)+'.raw'
   report.update(received_payloads=received,source_identity_contract=SOURCE_IDENTITY_CONTRACT,source_identity_status='verified_response_identity')
   if any(f['kind']=='resolution_self_report' for f in report['facts']):report['answer_status']='self_reported_resolved'
   if host=='wordpress.org':report['wordpress_parser_contract']=wordpress_identity.CONTRACT
   saved=dict(report,integrity_sha256=m.sha(json.dumps(report,sort_keys=True,ensure_ascii=False).encode()));m.dump(path,saved);reports[url]=report
  except Exception as ex:
   report={'source_url':url,'observed_at':m.now(),'error':m.error_text(ex,180),'facts':[],'expires':time.time()+900,'payer_verified':False,'customer_verified':False,'received_payloads':received,'source_identity_contract':SOURCE_IDENTITY_CONTRACT,'source_identity_status':'quarantined_unusable_response'if received else'not_verified_no_payload','quarantine_reason':m.error_text(ex,180)};reports[url]=report
   if not offline and 'budget exhausted' not in str(ex).lower():m.dump(path,dict(report,integrity_sha256=m.sha(json.dumps(report,sort_keys=True,ensure_ascii=False).encode())))
 return reports

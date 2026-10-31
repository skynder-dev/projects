"""Bounded official-source alternatives; no model, ranking or customer inference."""
import asyncio,json,re,time,copy
from urllib.parse import urlsplit
from urllib import robotparser
import reveng_local_research as m
import source_rules
import html_document_identity as html_identity
SCHEMA='direct-alternatives-v1'
REVIEW_POLICY='current_input_bound_task_requirements_v5_no_category_dispatch'
SOURCES={
 'woo_cod':{'provider':'WooCommerce core documentation','task':'woocommerce_cod_checkout','url':'https://woocommerce.com/document/cash-on-delivery/'},
 'qatar_extra':{'provider':'Qatar Airways official baggage rules','task':'baggage_allowance_rules','url':'https://www.qatarairways.com/en/baggage/excess.html'},
 'lufthansa_baggage':{'provider':'Lufthansa official baggage page (attempted)','task':'baggage_allowance_rules','url':'https://www.lufthansa.com/us/en/baggage-overview'},
}
SOURCES.update(source_rules.SOURCES)
def parse(key,text,stamp,response_sha):
 if key in source_rules.SOURCES:return source_rules.parse(key,text,stamp,response_sha,SCHEMA)
 spec=SOURCES[key];text=' '.join(text.split());facts=[];remaining=25
 def fact(kind,pattern,words=10):
  nonlocal remaining
  match=re.search(pattern,text,re.I)
  if not match:return None
  quote=' '.join(match.group(0).split()[:min(words,remaining)])
  if not quote:return None
  remaining-=len(quote.split());id='D'+str(len(facts)+1);facts.append({'id':id,'kind':kind,'quote':quote});return id
 base={'schema':SCHEMA,'provider':spec['provider'],'task':spec['task'],'source_url':spec['url'],'observed_at':stamp,'response_sha256':response_sha,'expires':time.time()+86400,'facts':facts,'payment_evidence':None,'paying_customer_status':'unknown','market_demand':'not established'}
 if key=='woo_cod':
  setup=fact('task',r'steps to activate and configure Cash on Delivery \(COD\)',5)
  owner=fact('intended_operator',r'as the store owner',4)
  free=fact('plan',r'free,?\s+core WooCommerce plugin',5)
  title=fact('checkout_control',r'Title.{0,8}Choose the title shown to.{0,20}customers during checkout',6)
  shipping=fact('shipping_control',r'Enable for shipping methods.{0,8}Choose which shipping methods and rates will offer COD',5)
  exact=bool(setup and owner and title and shipping)
  base.update(classification='exact_task_alternative' if exact else 'partial_alternative' if setup else 'not_found_in_checked_source',function_scope='Manual activation/configuration checklist for core WooCommerce COD; checkout title and eligible shipping methods' if exact else 'COD setup coverage not fully established',buyer_match={'status':'documented_role_match' if owner else 'unknown','role':'WooCommerce store owner','evidence_ids':[owner] if owner else [],'limitation':'Role match only; no budget authority, small-business size or willingness to pay established'},plan={'status':'observed' if free else 'unknown','name':'core WooCommerce plugin','price_literal':'free' if free else None,'evidence_ids':[free] if free else [],'limits':['Core configuration and public documentation; not a paid diagnostic/support plan','Hosting, delivery collection, extensions and custom support costs not established']},covered=['enable COD','configure checkout title','restrict eligible shipping methods'] if exact else [],unproven=['Specific Pay Credit/Debit Card button defect and its cause','Compatibility with the user store or third-party extensions','Automatic diagnosis or guaranteed repair'],interpretation='Direct substitute for the proposed setup checklist, not proof that the original reported defect is configuration rather than a bug')
 elif key=='qatar_extra':
  scope=fact('limitation',r'apply to flights operated by Qatar Airways only',9)
  mixed=fact('limitation',r'If your itinerary includes flights operated by other airlines',10)
  extra=fact('task',r'(?:Purchasing|Purchase|buy|additional|extra) (?:extra |additional )?baggage',4)
  # Never infer mixed-carrier coverage from a carrier's own-route price table.
  base.update(classification='partial_alternative' if scope and extra else 'not_found_in_checked_source',function_scope='Official extra-baggage rules and fees for Qatar-operated flights',buyer_match={'status':'partial_role_match' if scope else 'unknown','role':'Qatar Airways passenger','evidence_ids':[scope] if scope else [],'limitation':'Mixed-carrier Lufthansa/Qatar itinerary coverage not established; passenger is not a verified paying customer of our idea'},plan={'status':'unknown','name':'route-specific additional baggage purchase','price_literal':None,'evidence_ids':[scope] if scope else [],'limits':['Page limits the listed conditions to Qatar-operated flights','No single fare or subscription price; route, booking, baggage and operating carrier matter','No purchase, booking lookup or fare calculation executed']},covered=['Qatar-operated additional baggage guidance'] if scope and extra else [],unproven=['Whether one second bag is charged once or twice across the actual mixed itinerary','Lufthansa / Vueling leg coverage','Single combined itinerary calculator or checklist'],interpretation='Partial official information source; not an exact replacement for a mixed-carrier calculator')
 else:base.update(classification='not_found_in_checked_source',function_scope='No supported function parser for this page',buyer_match={'status':'unknown'},plan={'status':'unknown','price_literal':None,'limits':[]},covered=[],unproven=['Exact task coverage'],interpretation='No matching solution established in this bounded check; not a market absence claim')
 return base
def rule_hash(key,spec):return m.sha(json.dumps({'source':spec,'task':source_rules.TASKS.get(spec['task']),'parser':SCHEMA+'|'+key,'HTML_identity_contract':html_identity.CONTRACT},sort_keys=True,ensure_ascii=False).encode())
def body_text(raw,expected_url):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html_identity.validate(expected_url,raw),'html.parser')
 for node in soup.select('script,style,nav,footer'):node.decompose()
 return (soup.select_one('main') or soup).get_text(' ',strip=True)
async def collect(root,run,tasks,stats,offline=False):
 cache=root/'direct-source-cache';cache.mkdir(exist_ok=True);out=[];robots={}
 for key,spec in SOURCES.items():
  if spec['task'] not in tasks:continue
  fingerprint=rule_hash(key,spec);m.cancelled(run);path=cache/(m.sha((SCHEMA+'|'+spec['url']+('|controls-v2' if key=='woo_cod' else '')).encode())+'.json')
  try:
   if path.exists():
    saved=json.loads(path.read_text(encoding='utf-8'));claim=saved.pop('integrity_sha256',None)
    if claim==m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode()) and saved.get('expires',0)>time.time() and 'budget exhausted' not in saved.get('error','').lower():
     if saved.get('source_rule_sha256')==fingerprint:out.append(saved);stats['source_cache_hits']+=1;continue
     digest=saved.get('response_sha256','');archive=root/'direct-source-payloads'/(digest+'.raw')
     if len(digest)==64 and archive.exists() and m.sha(archive.read_bytes())==digest:
      record=parse(key,body_text(archive.read_bytes(),spec['url']),saved['observed_at'],digest);record['expires']=saved['expires'];record['source_rule_sha256']=fingerprint
      m.dump(path,dict(record,integrity_sha256=m.sha(json.dumps(record,sort_keys=True,ensure_ascii=False).encode())));out.append(record);stats['source_cache_hits']+=1;continue
   if offline:raise ValueError('No fresh verified direct-source cache; no HTTP fallback')
   p=urlsplit(spec['url']);host=p.netloc
   if host not in robots:
    raw=await asyncio.to_thread(m.read_http,p.scheme+'://'+host+'/robots.txt',stats,65536);rp=robotparser.RobotFileParser();rp.parse(raw.decode('utf-8').splitlines());robots[host]=rp
   if not robots[host].can_fetch(m.UA,spec['url']):raise ValueError('robots.txt denied')
   raw=await asyncio.to_thread(m.read_http,spec['url'],stats)
   archive=root/'direct-source-payloads';archive.mkdir(exist_ok=True);(archive/(m.sha(raw)+'.raw')).write_bytes(raw)
   record=parse(key,body_text(raw,spec['url']),m.now(),m.sha(raw))
  except Exception as ex:
   record={'schema':SCHEMA,'provider':spec['provider'],'task':spec['task'],'source_url':spec['url'],'observed_at':m.now(),'expires':time.time()+900,'classification':'source_unavailable','error':m.error_text(ex,180),'facts':[],'function_scope':'Source unavailable or unverified; no absence conclusion','buyer_match':{'status':'unknown'},'plan':{'status':'unknown','limits':[]},'covered':[],'unproven':['All task/plan/buyer coverage'],'interpretation':'Source could not be checked; task coverage and market alternatives remain unknown'}
  record['source_rule_sha256']=fingerprint
  out.append(record)
  if not offline and 'budget exhausted' not in record.get('error','').lower():m.dump(path,dict(record,integrity_sha256=m.sha(json.dumps(record,sort_keys=True,ensure_ascii=False).encode())))
 return out
def review_cache_matches(value):
 return value.get('direct_schema')==SCHEMA and value.get('direct_review_policy')==REVIEW_POLICY

def for_task(task,records,card=None):
 # Lexical/model task routing and document capability rules are collection
 # scope, not a source-bound judgement that the author's actual task is solved.
 # Preserve the useful document findings and every limitation without accepting
 # the model's unverified problem framing (e.g. COD setup vs a wrong button).
 rows=[]
 for original in records:
  if original.get('task')!=task:continue
  row=copy.deepcopy(original);row['document_rule_classification']=row.get('document_rule_classification',row.get('classification'))
  row['documented_rule_covered']=row.get('documented_rule_covered',row.get('covered',[]));row['covered']=[]
  row['classification']='source_unavailable'if row.get('error')else'document_candidate_task_fit_unreviewed'
  row['task_fit_to_original']='UNREVIEWED_FOR_THIS_SOURCE';row['active_candidate_admission']=False
  row['interpretation']='Documented capabilities are retained; source task fit, diagnosis, buyer and advantage require separate contextual review.'
  rows.append(row)
 failed=[r for r in rows if r.get('error')]
 status='not_evaluated_no_document_scope'if not task else'no_document_body_verified'if not rows else'document_sources_unavailable'if len(failed)==len(rows)else'document_candidates_unreviewed'
 result={'schema':SCHEMA,'review_policy':REVIEW_POLICY,'status':status,'task':task,'alternatives':rows,'source_failures':[{'source_url':r.get('source_url'),'error':r['error']}for r in failed],'coverage':'incomplete_sources_unavailable'if failed else'no_selected_documents'if not rows else'document_rules_only_source_task_fit_unreviewed','active_candidate_admission':False,'scope':'Bounded document collection/rule check. No source-specific solution, market absence, verified buyer, revenue or comparative advantage established.'}
 if task=='api_traffic_regression_mocks':result.update(documented_capability_scope='publisher_claims_only_not_tested',executed_observations=[],market_demand='unknown')
 if card is not None:
  result['routing_review']=dict(source_rules.routing_review(card),selected_document_task=task)
  result['question_task_binding']=source_rules.question_task_binding(card,task,rows)
  for row in rows:
   row['document_rule_unproven']=row.get('unproven',[])
   row['unproven']=list(result['question_task_binding']['needed_evidence'])
  result['document_collection_status']=status;result['status']='review_required'
 return result

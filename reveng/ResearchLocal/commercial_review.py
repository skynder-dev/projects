"""Conservative evidence bookkeeping; none of this estimates revenue or proves a buyer."""
import hashlib, json, re, time
import capture_dates
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

PRICE_SOURCES=[
 {'provider':'Buffer','category':'social_operations','url':'https://buffer.com/pricing'},
 {'provider':'Wave','category':'bookkeeping','url':'https://www.waveapps.com/pricing'},
 {'provider':'Square Appointments','category':'appointments','url':'https://squareup.com/us/en/appointments/pricing'},
 {'provider':'mail-tester','category':'email_delivery','url':'https://mail-tester.com/manager/micro-payment.html'},
 {'provider':'BrowserStack','category':'browser_compatibility','url':'https://www.browserstack.com/pricing'},
 {'provider':'TripIt Pro','category':'travel_operations','url':'https://www.tripit.com/web/pro'},
 {'provider':'Jobber','category':'home_projects','url':'https://www.getjobber.com/pricing/'},
]
CATEGORIES=['website_maintenance','email_delivery','browser_compatibility','social_operations','bookkeeping','appointments','travel_operations','home_projects','creative_workflow','other']
# Only collector-defined original question/post observations can corroborate a problem.
PROBLEM_REPORT_KINDS=frozenset(['public_question_title','public_topic_title','public_ask_post','public_question_context','public_topic_context'])

STOP=set('these those their there where which would could should using about question support topic only fetched observed public title issue problem working needs asked request with from have your they them were will when what more than been make also into'.split())
def canonical(url):
 p=urlsplit(url);qs=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ['fbclid','gclid']]
 return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',urlencode(sorted(qs)),''))
def report_identity(url,kind=None):
 # Only collector-known HTTPS question URLs establish a slug equivalence.
 # No redirect, answer, unknown-site or unknown-query equivalence is inferred.
 p=urlsplit(url);host=p.hostname or ''
 if not host or p.scheme not in {'http','https'}:return None
 if kind is not None and kind not in PROBLEM_REPORT_KINDS:
  return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',p.query,p.fragment))+'|role:'+str(kind)
 sites={'webapps','webmasters','softwarerecs','opensource','diy','travel','graphicdesign'}
 known=host=='superuser.com' or host in {site+'.stackexchange.com' for site in sites}
 question=re.fullmatch(r'/questions/([1-9][0-9]*)(?:/([^/]+))?/?',p.path)
 query=parse_qsl(p.query,keep_blank_values=True)
 tracking=all(k.lower().startswith('utm_') or k.lower() in {'fbclid','gclid'} for k,v in query)
 if known and p.scheme=='https' and p.netloc.lower()==host and question and not (question.group(2) or '').isdigit() and tracking and p.fragment in {'','top'}:
  return 'https://'+host+'/questions/'+question.group(1)
 return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',p.query,p.fragment))

def row_report_identity(row):
 key=report_identity(row.get('url',''),row.get('kind'))
 if key is None:return None
 # A URL-derived question identity is usable only when supplied row metadata
 # does not contradict its source, original-question field or question ID.
 p=urlsplit(key);match=re.fullmatch(r'/questions/([1-9][0-9]*)',p.path)
 if match and row.get('kind') in PROBLEM_REPORT_KINDS:
  host=p.hostname or '';site='superuser' if host=='superuser.com' else host.split('.')[0]
  source='design' if site=='graphicdesign' else site
  if row.get('source') not in [None,'',source]:return None
  if row.get('source_field') not in [None,'','body','title']:return None
  qid=row.get('question_id')
  if qid is not None and (type(qid) not in [int,str] or str(qid)!=match.group(1)):return None
 return key

def deduplicate(rows):
 seen_urls={};seen_text={};unique=[];duplicates=[]
 for row in rows:
  key=row_report_identity(row) or 'unresolved:'+hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest();body='' if row.get('kind') in ['public_topic_title','public_question_title'] else row.get('context_text') or row.get('excerpt') or ''
  content=json.dumps([row.get('title',''),body],ensure_ascii=False)
  # Keep complete saved metadata, including links, capture fields and E-IDs.
  # Question aliases share an identity but retain original URL/metadata variants.
  # Metadata is never unioned into an earlier snapshot that did not contain it.
  signature=json.dumps(row,sort_keys=True,ensure_ascii=False)
  if key in seen_urls:
   if signature in seen_urls[key]['signatures']:
    duplicates.append({'url':row['url'],'duplicate_of':seen_urls[key]['url'],'reason':'same_canonical_url'});continue
   duplicates.append({'url':row['url'],'variant_of':seen_urls[key]['url'],'reason':'same_url_different_saved_fields; retained, not a separate problem report'})
   seen_urls[key]['signatures'].add(signature)
  if content in seen_text and row_report_identity(seen_text[content])!=key:duplicates.append({'url':row['url'],'possible_duplicate_of':seen_text[content]['url'],'reason':'identical_text_different_url; retained, independence unknown'})
  seen_urls.setdefault(key,{'url':row['url'],'signatures':{signature}});seen_text[content]=row;unique.append(dict(row))
 used={r['evidence_id']for r in unique if r.get('evidence_id')};next_id=1
 for row in unique:
  if row.get('evidence_id'):continue
  while 'E'+str(next_id) in used:next_id+=1
  row['evidence_id']='E'+str(next_id);used.add(row['evidence_id'])
 return unique,duplicates
def tokens(row):
 text=row.get('title','')
 if row.get('kind') not in ['public_topic_title','public_question_title']:text+=' '+row.get('excerpt','')
 return {x for x in re.findall('[a-z]{4,}',text.lower()) if x not in STOP}
def resolve_scope(card):
 rows=card['observed_basis'];sources=set(x.get('source') for x in rows);proposed=card.get('market_category','other')
 known={'wordpress':'website_maintenance','diy':'home_projects','travel':'travel_operations','design':'creative_workflow'}
 category=known.get(next(iter(sources))) if len(sources)==1 else None
 if not category:
  text=' '.join(x.get('title','')+' '+x.get('excerpt','') for x in rows).lower()
  for words,label in [('email|deliverability|spam','email_delivery'),('safari|youtube','browser_compatibility'),('invoice|bookkeeping|accounting','bookkeeping'),('appointment|scheduling','appointments'),('instagram|social media','social_operations')]:
   if re.search(words,text):category=label;break
 card['model_market_category']=proposed;card['market_category']=category or 'other';card['category_basis']='source scope/observed keywords, not verified buyer industry'
 return card
def publisher(url):
 host=urlsplit(url).hostname or ''
 if host.endswith('.stackexchange.com') or host=='stackoverflow.com':return 'stackexchange-network'
 return host.removeprefix('www.')
def amount_scope(text,start,end):
 # Immediate source wording only; nearby conditions are not a plan assignment.
 before=text[max(0,start-35):start];after=text[end:end+55]
 role='unclassified_amount_not_verified_base_tariff'
 if re.search(r'\bSave\s*$',before,re.I):role='savings_not_subscription'
 elif re.match(r'\s+per\s+(?:credit card|Amex)\s+transaction\b',after,re.I):role='transaction_fee_not_subscription'
 elif re.search(r'\bAdd users for\s*$',before,re.I)and re.match(r'\s+each\b',after,re.I):role='additional_user_charge_not_base_plan'
 a=max(0,start-90);b=min(len(text),end+130);conditions=[]
 pattern=r'\b(?:billed (?:yearly|annually|monthly)|(?:No|1 year) commitment|Includes \d+ users|\d+ channel|per channel|per user|free \d+-day trial|\d+-day free trial|for a year)\b'
 for m in re.finditer(pattern,text[a:b],re.I):conditions.append({'quote':m.group(0),'start':a+m.start(),'end':a+m.end()})
 return {'amount_role':role,'nearby_conditions':conditions,'condition_binding':'nearby_source_text_only; not assigned to this amount or plan','free_plan_status':'not_established; zero amount or a free trial does not prove an ongoing free plan','comparison_basis':'unknown; no currency conversion, annualization, per-seat/team normalization or task equivalence established'}

def retained_amount_scope(record):
 text=record.get('context');literal=record.get('displayed_price')
 if not isinstance(text,str)or not isinstance(literal,str)or not literal:return {}
 occurrences=[amount_scope(text,m.start(),m.end())for m in re.finditer(re.escape(literal),text)]
 if not occurrences:return {}
 roles={x['amount_role']for x in occurrences}
 return occurrences[0]if len(roles)==1 else {'amount_role':'unclassified_amount_not_verified_base_tariff'}

def parse_prices(text, source, observed_at, response_sha,text_scope='supplied_text_scope_not_proven'):
 # Literal occurrences, not offers/revenue. Do not collapse repeated prices:
 # the same amount may belong to different plans, taxes or commitments.
 out=[];total=0;text_hash=hashlib.sha256(text.encode('utf-8')).hexdigest()
 pattern=r'(?:(?P<symbol>[$£€₹])\s*(?P<amount>\d[\d,.]*)(?:\s*(?P<code>USD|CAD|EUR|GBP)\b)?|(?P<amount_only>\d[\d,.]*)\s*(?P<code_only>USD|CAD|EUR|GBP)\b)(?P<period>\s*/\s*(?:month|year|mo|yr)\b)?'
 for match in re.finditer(pattern,text,re.I):
  total+=1
  if len(out)>=64:continue
  literal=match.group(0);a=max(0,match.start()-90);b=min(len(text),match.end()+130);context=text[a:b];code=(match.group('code')or match.group('code_only')or'').upper()
  labels=re.findall(r'\b(?:Essentials|Team|Starter|Pro|Core|Plus|Grow|Connect|Premium|Business)\b',text[max(0,match.start()-180):match.start()],re.I)
  qualifiers=[q for q in ['billed yearly','billed annually','billed monthly','per channel','per user','commitment','promo']if q in context.lower()]
  out.append({'provider':source['provider'],'category':source['category'],'displayed_price':literal,'amount_literal':match.group('amount')or match.group('amount_only'),'currency':code or'unknown','currency_symbol_literal':match.group('symbol'),'billing':'explicit_in_literal'if match.group('period')else'not_established','billing_period_literal':match.group('period'),'plan_label_candidate':labels[-1]if labels else None,'billing_qualifiers_observed':qualifiers,'applicability':'broad category lead; buyer/feature equivalence unverified','plan_status':'not_established_from_snippet; inspect billing/region/fees','context':context,'source_url':source['url'],'observed_at':observed_at,'response_sha256':response_sha,'status':'literal_public_price_not_customer_payment','cache_expires':capture_dates.expiry(observed_at),'source_text_sha256':text_hash,'text_scope':text_scope,'citation':{'start':match.start(),'end':match.end(),'quote':literal},'context_citation':{'source_start':a,'source_end':b,'text_sha256':hashlib.sha256(context.encode()).hexdigest(),'price_start':match.start()-a,'price_end':match.end()-a},'binding_scope':'Exact supplied text/context; original HTTP response not authenticated by parser','occurrence_id':hashlib.sha256(json.dumps([source['url'],response_sha,text_hash,match.start(),match.end()]).encode()).hexdigest()})
 for row in out:
  row.update(amount_scope(text,row['citation']['start'],row['citation']['end']))
  row.update(extraction_total_matches=total,extraction_returned=len(out),extraction_truncated=total>len(out))
 return out

def assess(card, price_records, source_errors=()):
 rows=card['observed_basis'];unique,observation_duplicates=deduplicate(rows)
 reports=[r for r in unique if r.get('kind') in PROBLEM_REPORT_KINDS]
 other_observations=[r for r in unique if r.get('kind') not in PROBLEM_REPORT_KINDS]
 # Duplicate annotations involving software/document rows cannot establish or
 # suppress the independence of the actual question/post observations.
 _,duplicates=deduplicate([r for r in rows if r.get('kind') in PROBLEM_REPORT_KINDS]);meaningful=[];lexical_seen=set()
 report_count=len({key for r in reports for key in [row_report_identity(r)] if key is not None})
 for i,a in enumerate(reports):
  for b in reports[i+1:]:
   if row_report_identity(a) is None or row_report_identity(b) is None or row_report_identity(a)==row_report_identity(b):continue
   shared=tokens(a)&tokens(b)
   lexical_key=(tuple(sorted([row_report_identity(a),row_report_identity(b)])),tuple(sorted(shared)))
   if len(shared)>=2 and lexical_key not in lexical_seen:
    lexical_seen.add(lexical_key);meaningful.append({'urls':[a['url'],b['url']],'shared_observed_words':sorted(shared),'interpretation':'lexical repetition only; same underlying cause unverified'})
 pubs=sorted(set(publisher(r['url']) for r in reports));authors=sorted({(str(r.get('source')),str(r['author_id']))for r in reports if r.get('author_id')})
 # Different reported handles, publishers or URLs are metadata, not verified
 # independent people or independent underlying problem reports.
 independence='not_established'
 shared_relations={}
 observation_pin=lambda row:hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 targets={}
 for row in reports:
  identity=row_report_identity(row)
  if identity is not None:targets.setdefault(identity,{})[observation_pin(row)]=row
 for row in reports:
  from_url=row_report_identity(row)
  if from_url is None:continue
  for field in ['link_targets','linked_context_urls']:
   if not isinstance(row.get(field),(list,tuple)):continue
   for index,url in enumerate(row[field]):
    if not isinstance(url,str):continue
    try:target=report_identity(url)
    except ValueError:continue
    if target is None or target==from_url or target not in targets:continue
    key=(from_url,target)
    relation=shared_relations.setdefault(key,{'from_url':from_url,'referenced_report_url':target,
     'referenced_observation_json_sha256s':sorted(targets[target]),
     'referenced_observation_origins':[{'observation_json_sha256':pin,'saved_observation_url':item['url'],'evidence_id':item.get('evidence_id'),'source':item.get('source'),'source_field':item.get('source_field'),'observed_at':item.get('observed_at'),'context_observed_at':item.get('context_observed_at'),'observation_snapshot_id':item.get('observation_snapshot_id')}for pin,item in sorted(targets[target].items())],
     'metadata_origins':[],
     'provenance_scope':'Exact retained observation object and metadata field; object hash is not response-byte proof or authenticated identity',
     'meaning':'Explicit reference to another supplied report; citation/reference role and independence unverified'})
    origin={'observation_json_sha256':observation_pin(row),'evidence_id':row.get('evidence_id'),'source':row.get('source'),
     'saved_observation_url':row['url'],'observed_at':row.get('observed_at'),'context_observed_at':row.get('context_observed_at'),
     'metadata_field':field,'metadata_index':index,'saved_target_url':url}
    if origin not in relation['metadata_origins']:relation['metadata_origins'].append(origin)
 shared_origins=[]
 for key in sorted(shared_relations):
  relation=shared_relations[key];relation['metadata_origins'].sort(key=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False));shared_origins.append(relation)
 metadata_variety={'different_publishers_observed':len(pubs)>1,'different_reported_author_ids_observed':len(authors)>1,
                   'unknown_author_report_urls':sorted({r['url']for r in reports if not r.get('author_id')}),
                   'meaning':'Reported metadata only; handles are not authenticated people, publisher metadata does not establish buyer status, counts are not demand'}
 text=(card['title']+' '+card.get('problem_hypothesis','')).lower();category=card.get('market_category')
 if not category:category='browser_compatibility' if 'safari' in text else 'website_maintenance' if 'elementor' in text else 'email_delivery' if 'письм' in text or 'email' in text else 'other'
 scoped=[p for p in price_records if p['category']==category]
 nonbase=[p for p in scoped if retained_amount_scope(p).get('amount_role')in ['savings_not_subscription','transaction_fee_not_subscription','additional_user_charge_not_base_plan']]
 alternatives=[p for p in scoped if p not in nonbase]
 clock=time.time();fresh=[p for p in alternatives if capture_dates.current(p,'cache_expires',now=clock)]
 historical=[p for p in alternatives if not capture_dates.current(p,'cache_expires',now=clock)]
 issues=[]
 if any(row_report_identity(r) is None for r in reports):issues.append('Some report URLs or source metadata are unresolved; excluded from known report count, original records retained')
 if other_observations:issues.append('Software listings or unrecognized source roles retained separately; excluded from problem-report corroboration')
 if report_count<2:issues.append('Fewer than two distinct problem reports: not evidence of a repeatable market problem')
 if not meaningful:issues.append('No repeated specific title/excerpt wording established across supplied references')
 if any('possible_duplicate_of' in x for x in duplicates):issues.append('Different URLs contain identical text; do not count as independent confirmation')
 if any('variant_of'in x for x in duplicates):issues.append('Different saved fields from the same URL were retained; they are not separate reports and require comparison')
 if report_count>1 and len(authors)==1:issues.append('Several reports have the same public author; independent demand is not established')
 if independence=='not_established':issues.append('Independent confirmation is unknown')
 if shared_origins:issues.append('Some supplied reports explicitly reference another supplied report; do not count citation sites as independent confirmation')
 if nonbase:issues.append('Explicit savings, transaction fees and additional-user charges retained separately; not base subscription alternatives')
 if not fresh:issues.append('No current, matched public alternative price verified')
 issues+=['Who actually pays and willingness to pay are unverified','No completed purchase, representative demand or unit economics observed']
 freshness=[]
 for row in unique:
  try:age=time.time()-datetime.fromisoformat(row['observed_at']).timestamp();state='within_one_hour_application_policy' if 0<=age<=3600 else 'stale_or_future'
  except Exception:state='unknown_observation_date'
  freshness.append({'url':row['url'],'status':state})
 if any(x['status']!='within_one_hour_application_policy' for x in freshness):issues.append('Some observations are stale or undated; do not treat historical questions as current demand')
 if fresh:issues.append('Price snippets do not establish the applicable plan, region, billing commitment, taxes or feature equivalence')
 if source_errors:issues.append('Some requested sources failed; coverage is incomplete')
 if not reports:level='no_observed_problem_report'
 elif report_count==1:level='single_report_research_note'
 elif meaningful:level='repeated_wording_candidate; needs buyer validation'
 else:level='multiple_reports_unconfirmed_theme'
 return {'observed_problem':reports,'other_observations':other_observations,'observation_duplicate_annotations':observation_duplicates,'observation_freshness':freshness,'corroboration':{'scope_policy':'saved_problem_report_metadata_v2_no_independence_inference','distinct_posts':report_count,'publishers':pubs,'public_author_ids_count':len(authors),'independence':independence,'metadata_variety':metadata_variety,'possible_shared_origins':shared_origins,'lexical_repetition':meaningful,'duplicate_reports_removed':duplicates},'buyer':{'description':card['buyer'],'status':'model_hypothesis_not_customer','payment_evidence':None},'demand_indicators':[{'url':r['url'],'kind':'request_or_question_observed; not sale'} for r in reports],'non_base_price_observations':[dict(p,amount_role=retained_amount_scope(p)['amount_role'])for p in nonbase],'existing_solutions':fresh,'historical_or_unverified_solution_leads':historical,'competition':{'named_public_providers':sorted(set(p['provider'] for p in fresh)),'interpretation':'Offering/price exists; purchaser counts and our advantage unknown'},'validation_step':card['validation_step'],'unknowns':issues,'evidence_status':level,'commercial_confidence':'low; no proven buyer','income_score':None,'estimated_revenue':None}
def compare(baseline, new_cards, prices, errors):
 return {'baseline_version':baseline.get('version'),'previous':[{'title':c['title'],'commercial_review':assess(c,prices,errors)} for c in baseline.get('hypotheses',[])],'new':[{'title':c['title'],'evidence_status':c['commercial_review']['evidence_status']} for c in new_cards],'conclusion':'No winner or paid customer proven. More observations/alternatives do not establish profitability.'}
def identity(card):
 # Source overlap does not make two different proposed products the same candidate.
 # Title is presentation; exact buyer/problem/solution are the proposal identity.
 data={'category':card.get('market_category','other'),'basis':sorted({canonical(x['url']) for x in card['observed_basis']}),
       'proposal':{k:card.get(k) for k in ['buyer','problem_hypothesis','solution_hypothesis']}}
 return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
# Only clock/cache bookkeeping is excluded. Source captures, payload hashes,
# literal facts and complete functional comparisons remain revision evidence.
_TECHNICAL={'expires','cache_expires','context_cache_expires','checked_at','updated_at','completed_at','reviewed_at','functional_assessment_observed_until','stats'}
def semantic_review(value,path='',audit=None,failed=False):
 if isinstance(value,dict):
  failed=failed or bool(value.get('error'))or value.get('classification')=='source_unavailable'
  out={}
  for key,item in value.items():
   child=path+'/'+key
   if key=='review_revision_hash':continue
   if key in _TECHNICAL or failed and key in {'observed_at','captured_at','capture_started_at','capture_finished_at','record_sha256'}:
    if audit is not None:audit[child]=item
   else:out[key]=semantic_review(item,child,audit,failed)
  return out
 if isinstance(value,list):return [semantic_review(v,path+'/'+str(i),audit,failed)for i,v in enumerate(value)]
 return value
def revision_data(card,audit=None):
 data={k:card.get(k)for k in ['title','buyer','problem_hypothesis','solution_hypothesis','validation_step','evidence_ids','market_category','risks','missing_evidence','alternatives_and_limits']}
 data['evidence_revision_policy']='semantic_saved_observations_and_assessments_v4'
 for field in ['commercial_review','buyer_demand_review','direct_alternatives','functional_comparisons','observed_basis']:
  value=card.get(field)
  if field=='direct_alternatives'and isinstance(value,dict):value={k:v for k,v in value.items()if k!='candidate_id'}
  data[field]=semantic_review(value,field,audit)
 return data
def revision(card):return hashlib.sha256(json.dumps(revision_data(card),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def merge_ledger(existing,cards):
 import copy
 result={x['candidate_id']:copy.deepcopy(x) for x in existing}
 if len(result)!=len(existing):raise ValueError('Ambiguous duplicate existing candidate_id; records not merged')
 legacy_matches={}
 for id,old in result.items():legacy_matches.setdefault(identity(old),[]).append(id)
 for incoming in cards:
  card=copy.deepcopy(incoming);key=identity(card);matches=legacy_matches.get(key,[])
  if len(matches)>1:raise ValueError('Multiple saved identities for the same exact proposal; explicit review required')
  # Preserve an existing exact proposal ID, including pre-upgrade IDs and decisions.
  id=matches[0] if matches else key
  if id in result and identity(result[id])!=key:raise ValueError('Candidate identity collision; records not merged')
  card['candidate_id']=id;card['review_revision_hash']=revision(card)
  old=result.get(card['candidate_id']);history=list(old.get('history',[])) if old else []
  audit=list(old.get('review_audit_history',[]))if old else []
  if old and old.get('review_revision_hash')==card['review_revision_hash']:
   previous_meta={};current_meta={};revision_data(old,previous_meta);revision_data(card,current_meta)
   if previous_meta!=current_meta:audit.append({'revision_hash':card['review_revision_hash'],'previous_technical_metadata':previous_meta,'current_technical_metadata':current_meta})
  if audit:card['review_audit_history']=audit[-20:]

  if old and old.get('review_revision_hash')!=card['review_revision_hash']:
   history.append({k:v for k,v in old.items() if k!='history'})
  result[card['candidate_id']]=dict(card,history=history[-20:])
  legacy_matches[key]=[id]
 return list(result.values())

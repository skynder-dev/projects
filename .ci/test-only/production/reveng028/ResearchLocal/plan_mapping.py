"""Conservative official plan-section parser. Unknown never means absent."""
import re,time,copy
import capture_dates
SCHEMA='official-plan-v3'
def parse(text,vendor,url,stamp,response_sha):
 text=' '.join(text.split());links=[];reasons=[]
 def add(function,plan,price,billing,quote,method):
  links.append({'function':function,'plan':plan,'displayed_price':price,'billing':billing,'status':'observed','evidence_fragments':quote.split('; '),'binding_method':method,'source_url':url,'observed_at':stamp,'response_sha256':response_sha})
 if vendor=='TripIt Pro':
  intro=re.search(r'TripIt Pro gives you.{0,220}?for just (\$49/year)',text,re.I)
  section=re.search(r'TripIt Pro kicks into gear(.+?)Try TripIt Pro for your next trip',text,re.I)
  if intro and section:
   for term in ['Flight Status','Baggage Claim Info','Passport Renewal Reminder']:
    match=re.search(re.escape(term),section.group(1),re.I)
    if match:add(match.group(0),'TripIt Pro',intro.group(1),'yearly',match.group(0)+'; TripIt Pro; '+intro.group(1),'named single-plan introduction and its bounded feature section')
  else:reasons.append('Named Pro price introduction or bounded Pro feature section not found; page-wide co-occurrence is insufficient')
 elif vendor=='Wave':
  starter=re.search(r'STARTER Plan(.+?)Pro Plan',text,re.I)
  pro=re.search(r'Pro Plan(.+?)(?:STARTER Plan|Wave Advisors)',text,re.I)
  if starter and re.search(r'\$0\b',starter.group(1)):
   for term in ['invoices','bookkeeping records']:
    if re.search(r'Create unlimited estimates, invoices, bills, and bookkeeping records',starter.group(1),re.I):
     add(term,'Starter','$0','not established',term+'; STARTER Plan; $0','feature inside bounded Starter plan section')
     if pro and re.search(r'\$19\s+USD/month\s+Billed monthly',pro.group(1),re.I) and re.search(r'Everything in Starter, plus',pro.group(1),re.I):
      qualifiers=['billed monthly']
      if re.search(r'PROMO:',pro.group(1),re.I):qualifiers.append('promotional alternative displayed; not evaluated as ongoing price')
      if re.search(r'CAD/month',pro.group(1),re.I):qualifiers.append('CAD alternative displayed; customer region unknown')
      add(term,'Pro','$19 USD/month','; '.join(qualifiers),term+'; Pro Plan; $19 USD/month; Everything in Starter','explicit Starter inheritance inside bounded monthly Pro section')
  if not links:reasons.append('Starter section, included feature or explicit Pro inheritance/price not established')
 else:reasons.append('No supported structural parser for this vendor; no plan inferred')
 conditions=[];promo=None
 if vendor=='Wave':
  for kind,quote in [('tax_excluded','Prices do not include applicable tax.'),('new_subscriptions_only','Listed price for the Pro Plan applies to new subscriptions only'),('auto_renew','Subscriptions auto-renew.'),('subscription_unit','per business, not per owner')]:
   match=re.search(re.escape(quote),text,re.I)
   if match:conditions.append({'kind':kind,'quote':match.group(0),'start':match.start(),'end':match.end(),'scope':'Wave Pro terms on this page; not a universal price/feature qualifier'})
  match=re.search(r'Offer available from ([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4}) until ([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})',text)
  if match:
   from datetime import datetime
   start=datetime.strptime(re.sub(r'(\d)(?:st|nd|rd|th)',r'\1',match.group(1)),'%B %d, %Y').date();end=datetime.strptime(re.sub(r'(\d)(?:st|nd|rd|th)',r'\1',match.group(2)),'%B %d, %Y').date()
   try:day=datetime.fromisoformat(stamp.replace('Z','+00:00')).date();state='expired_at_capture'if day>end else'not_started_at_capture'if day<start else'within_displayed_dates_not_verified_offer'
   except (ValueError,TypeError,AttributeError):state='capture_date_unknown'
   promo={'start_date':start.isoformat(),'end_date':end.isoformat(),'status':state,'quote':match.group(0),'start':match.start(),'end':match.end(),'scope':'Displayed dated offer terms only; dynamic eligibility and checkout availability not tested'}
 return {'schema':SCHEMA,'status':'observed' if links else 'unknown','links':links,'page_conditions':conditions,'promotion_terms':promo,'unknown_reason':'; '.join(reasons) if reasons else None,'source_url':url,'observed_at':stamp,'response_sha256':response_sha,'expires':capture_dates.expiry(stamp),'scope':'Documented vendor functions only. Does not prove the hypothetical target task, customer payment, plan region, taxes or full cost.'}
def attach(row,doc):
 out=copy.deepcopy(row);old=row.get('source_profile');out['source_profile']=copy.deepcopy(old or doc)
 def identity(profile):
  if not profile:return None
  hashes={f.get('response_sha256')for f in profile.get('facts',[])if f.get('response_sha256')}
  digest=profile.get('response_sha256')or(next(iter(hashes))if len(hashes)==1 else None)
  return(profile.get('vendor'),profile.get('source_url'),digest,profile.get('observed_at'))
 coherent=bool(doc and doc.get('vendor')==row.get('vendor')and(not old or old.get('source_url')==doc.get('source_url')))
 candidate=copy.deepcopy(doc.get('plan_feature_mapping'))if coherent else None
 if candidate and ((candidate.get('source_url'),candidate.get('response_sha256'),candidate.get('observed_at'))!=identity(doc)[1:]or any(link.get('source_url')!=doc.get('source_url')or link.get('response_sha256')!=candidate.get('response_sha256')or link.get('observed_at')!=candidate.get('observed_at')for link in candidate.get('links',[]))):coherent=False;candidate=None
 retained=copy.deepcopy(row.get('plan_feature_mapping'))
 expected_url=(old or(doc if coherent else{})or{}).get('source_url')
 if retained and(retained.get('source_url')!=expected_url or any(link.get('source_url')!=expected_url or link.get('response_sha256')!=retained.get('response_sha256')or link.get('observed_at')!=retained.get('observed_at')for link in retained.get('links',[]))):out['historical_unbound_plan_mapping']=retained;retained=None
 mapping=candidate or retained
 different_plan_capture=bool(mapping and old and(mapping.get('source_url'),mapping.get('response_sha256'),mapping.get('observed_at'))!=identity(old)[1:])
 out['plan_and_assessment_capture_relation']='DIFFERENT_CAPTURES_DO_NOT_MERGE'if different_plan_capture else'SAME_CAPTURE_OR_UNKNOWN_LITERAL_BINDING_ONLY'
 observations=copy.deepcopy(row.get('plan_mapping_observations',[]))
 for value in [retained,candidate]:
  if value and value not in observations:observations.append(value)
 out['plan_mapping_observations']=observations
 changed=bool(old and doc and identity(old)!=identity(doc));stale=bool(doc and not capture_dates.current(doc))
 if not coherent or changed or stale or different_plan_capture:
  if 'historical_assessment'not in out:out['historical_assessment']={k:copy.deepcopy(row.get(k))for k in ['function_relation','buyer_relation','effective_function_relation','effective_buyer_relation','reason','evidence_ids']}
  out['effective_function_relation']='unknown';out['effective_buyer_relation']='unknown';out['assessment_state']='REQUIRES_REVIEW_OF_SOURCE_CAPTURE_AND_IDENTITY'
  note='Source capture changed, stale/undated, or wrong vendor/product URL; old judgement is historical and not renewed by plan refresh.'
  out['guard_notes']=list(out.get('guard_notes',[]))
  if note not in out['guard_notes']:out['guard_notes'].append(note)
 if candidate:out['plan_evidence_source_profile']=copy.deepcopy(doc)
 elif 'plan_evidence_source_profile'in out and mapping and identity(out['plan_evidence_source_profile'])[1:]!=(mapping.get('source_url'),mapping.get('response_sha256'),mapping.get('observed_at')):out['historical_unbound_plan_profile']=out.pop('plan_evidence_source_profile')
 if not coherent and doc:out['rejected_plan_source']={k:doc.get(k)for k in ['vendor','source_url','observed_at','response_sha256']}
 out['plan_feature_mapping']=mapping or {'schema':SCHEMA,'status':'unknown','links':[],'unknown_reason':'Official page unavailable or mapping not parsed; absence is not proof of no feature','source_url':(out.get('source_profile') or {}).get('source_url'),'checked_at':time.time(),'expires':time.time()+900}
 if mapping:
  out['plan_evidence_source_metadata']={k:mapping.get(k)for k in ['source_url','observed_at','response_sha256','expires']}
  out['plan_capture_state']='CURRENT_CAPTURE_NOT_TASK_PROOF'if capture_dates.current(mapping)else'HISTORICAL_OR_UNDATED_CAPTURE_NOT_RENEWED'
  if not candidate:out['plan_mapping_retention']='SAVED_MAPPING_RETAINED_AS_ITS_OWN_CAPTURE_NOT_REEXTRACTED'
 out['target_task_plan_mapping']={'status':'unknown','required_task_evidence':row.get('required_task_evidence',[]),'reason':'No explicit official plan evidence for the proposed task; listed vendor functions must not be substituted for it'}
 out['price_to_feature_mapping']='See plan_feature_mapping for documented vendor functions; target task remains unknown'
 return out

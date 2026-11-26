"""Automatic source-record projection and finite, evidence-bound notice adapter."""
import copy,hashlib,json,re

def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def adapt(record,snapshot=None,audience='general_us'):
 r=copy.deepcopy(record);snapshot=snapshot or {};facts={};unknown=[]
 if r.get('public_money_content'):
  from .public_money import parse,unclaimed_record,energy_record,wages_record
  payload=r['public_money_content'];parsed=parse(payload['content'],r['source_url'],reconstructed=payload.get('reconstructed',False),fetched_at=payload.get('fetched_at'),content_type=payload.get('content_type','html'),snapshot_file=payload.get('snapshot_file'))
  r['public_money_source']=parsed
  if parsed['kind'] in {'unclaimed','energy','wages'}:
   r.update({'unclaimed':unclaimed_record,'energy':energy_record,'wages':wages_record}[parsed['kind']](parsed))
   r['editorial_source_brief']={'schema':'SOCIAL_SOURCE_BRIEF_V1','status':'source_only_draft','editorial_brief_created':True,'facts':parsed['fields'],'unknown':parsed['unknown'],'live_verified':False,'reconstructed':parsed['reconstructed']}
   if r.get('_visual_revision') is not None:
    from .visual_revision import apply
    r=apply(r,r['_visual_revision'])
   return r
 mappings={'audience':'applicant_eligibility_desc','amount':'award_ceiling','purpose':'description','deadline':'close_date'}
 for target,field in mappings.items():
  value=r.get(field)
  meta=(r.get('_field_sources') or {}).get(field) or snapshot
  facts[target]={'value':value,'origin_field':field,'source_url':r.get('source_url'),'snapshot_file':meta.get('file'),'snapshot_sha256':meta.get('sha256'),'interpretation':'Listing value only; not personal benefit or eligibility proof'}
  if value is None or value=='':unknown.append(target)
 # Preserve reviewed publisher/primary constraints rather than flattening a
 # project ceiling into a personal payout.
 for key in ('primary_conditions','track_conditions','publisher_eligibility','project_budget_scope','announcement_source'):
  if r.get(key) is not None:facts[key]={'value':r[key],'origin_field':key,'source_url':r.get('source_url'),'interpretation':'Retained structured source evidence; original scope unchanged'}
 required=['personal_or_business_recipient_scope','eligible_geography','benefit_kind','per_recipient_limit','approved_concrete_use','key_caveat','application_action','full_conditions']
 projection={'schema':'SOCIAL_SOURCE_BRIEF_V1','audience_requested':audience,'facts':facts,'unknown':unknown+required,'status':'insufficient_audience_evidence','editorial_brief_created':False,'no_inferred_eligibility':True}
 r['editorial_source_brief']=projection
 notice=r.get('source_notice') or {};text=notice.get('text','')
 if not text:return r
 if notice.get('sha256')!=digest(text) or not notice.get('url') or not notice.get('snapshot_file'):
  projection['errors']=['Source notice identity/hash incomplete'];return r
 # Versioned labelled-notice grammar. Do not accept free-form model output or
 # infer household support from a Grants.gov individual-applicant label.
 labels=('Recipient','Maximum benefit','Use','Eligibility','Coverage','Conditions','Application')
 parsed={};quotes={}
 for label in labels:
  matches=list(re.finditer(r'^'+re.escape(label)+r': ([^\r\n]+)$',text,re.M))
  if len(matches)!=1:
   projection.setdefault('errors',[]).append('Missing/ambiguous notice field: '+label);continue
  parsed[label]=matches[0].group(1);quotes[label]=matches[0]
 if projection.get('errors'):return r
 # This rule has only been demonstrated on the explicit synthetic notice
 # grammar. Real publisher-specific parsers need official fixtures and review;
 # a matching label alone must not authorize a real payout story.
 if notice.get('synthetic') is not True:
  projection['errors']=['No reviewed real-publisher parser for this notice grammar'];return r
 maxmatch=re.fullmatch(r'Up to \$([0-9,]+) per household',parsed['Maximum benefit'])
 if parsed['Recipient']!='US households' or parsed['Use']!='Heating bills' or parsed['Coverage']!='Household heating costs' or not maxmatch:
  projection['errors']=['Unsupported recipient/use/amount scope; retained unknown'];return r
 if parsed['Eligibility']!='Income limits apply' or parsed['Application']!='Official application details below':
  projection['errors']=['Unsupported eligibility/action wording'];return r
 def claim(key,statement,accent,fields):
  blocks=[quotes[f].group(0) for f in fields];quote='\n'.join(blocks)
  return {'key':key,'statement':statement,'accent':accent,'values':{},'must_disclose':True,'reviewed_statement_sha256':digest(statement),'source':{'url':notice['url'],'snapshot_file':notice['snapshot_file'],'snapshot_sha256':notice['sha256'],'locator':'labelled notice: '+', '.join(fields),'origin_fields':fields,'origin_spans':[{'start':quotes[f].start(),'end':quotes[f].end(),'quote':quotes[f].group(0)} for f in fields],'quote':quote,'excerpt':quote,'excerpt_sha256':digest(quote),'rule':'synthetic_heating_notice_v1; finite scope-preserving templates'}}
 amount=int(maxmatch[1].replace(',',''))
 claims=[claim('money_hook',f'Up to ${amount:,} toward your heating bill?',f'Up to ${amount:,}',['Maximum benefit','Use']),claim('use_case','Help cover your household heating bill.','your household heating bill',['Use','Recipient']),claim('advantage','That support reduces your heating costs.','reduces your heating costs',['Coverage']),claim('key_caveat','Income limits apply, so check before applying.','Income limits apply',['Eligibility']),claim('cta','See the official details below.','official details below',['Application']),claim('full_conditions',parsed['Conditions'],parsed['Conditions'],['Conditions'])]
 roles=('money_hook','use_case','advantage','key_caveat','cta')
 brief={'schema':'SOCIAL_EDITORIAL_BRIEF_V1','synthetic':True,'category':'personal_money','audience_description':parsed['Recipient'],'concrete_use':parsed['Use'],'money_benefit':{'kind':'bill_support','scope':'per_household','limit_claim_key':'money_hook'},'review':{'reviewer':'deterministic synthetic_heating_notice_v1 adapter; fixture only','scope':'facts_and_plain_language_entailment'},'claims':claims,'main_facts':dict(zip(roles,roles)),'description_claim_keys':[c['key'] for c in claims]}
 r['editorial_brief']=brief;projection.update(status='synthetic_editorial_ready',editorial_brief_created=True,unknown=[],synthetic=True,parsed_fields=parsed,adapter_rule='synthetic_heating_notice_v1')
 return r

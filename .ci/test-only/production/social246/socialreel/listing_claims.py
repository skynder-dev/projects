"""Finite typed projections of accepted raw connector fields, saved evidence only."""
import copy,json,re,datetime as dt
from decimal import Decimal,InvalidOperation
from pathlib import Path
from .common import PipelineError,read_json,sha256_bytes,sha256_file,human_date
from .source_revisions import digest
from .connector_observations import project,FIELD_NAMES,timestamp

API='https://api.grants.gov/v1/api/fetchOpportunity'
MONEY={'award_floor','award_ceiling','estimated_total_program_funding'}
LISTS={'applicant_types','funding_instruments','funding_categories'}
DATES={'open_date','close_date'}
TEXT={'title','number','status','description','applicant_eligibility_desc','full_announcement_url'}
RULE='grants_saved_field_typed_v1'

def _json(raw):
 def unique(pairs):
  out={}
  for key,value in pairs:
   if key in out:raise PipelineError('Repeated JSON field makes the saved source ambiguous')
   out[key]=value
  return out
 return json.loads(raw,object_pairs_hook=unique)

def consistency(claims):
 by={(c.get('conversion_origin') or {}).get('field'):c for c in claims if c.get('listing_scope')}
 for left,right in [('award_floor','award_ceiling'),('open_date','close_date')]:
  if left not in by or right not in by:continue
  a,b=by[left],by[right];ae=a['conversion_origin']['event']['event_id'];be=b['conversion_origin']['event']['event_id']
  if ae!=be:raise PipelineError('Related listing bounds belong to different saved receipts; do not combine snapshots')
  av=a['values'][left] if left=='award_floor' else a['values']['date'];bv=b['values'][right] if right=='award_ceiling' else b['values']['date']
  if av>bv:raise PipelineError('Saved listing bounds contradict each other; keep the source conflict unresolved rather than invent a range or schedule')


def _text(value):
 if not isinstance(value,str) or not value.strip() or len(value)>12000 or any(ord(c)<32 and c not in '\n\r\t' for c in value):raise PipelineError('Expected complete bounded nonempty source text')
 return value

def _numeric(value,integer=False):
 if isinstance(value,bool) or not isinstance(value,(str,int,float)) or not re.fullmatch(r'\d+(?:\.\d{1,2})?',str(value)):raise PipelineError('Expected explicit nonnegative decimal source number, not boolean, exponent, quantity text or null')
 number=Decimal(str(value))
 if not number.is_finite() or number<0 or number>Decimal('1000000000000') or integer and number!=number.to_integral_value():raise PipelineError('Source number out of range or not an integer count')
 return int(number) if number==number.to_integral_value() else float(number)

def _date(value):
 _text(value)
 for pattern in ('%Y-%m-%d','%m/%d/%Y','%b %d, %Y','%B %d, %Y'):
  try:return dt.datetime.strptime(value,pattern).date()
  except ValueError:pass
 raise PipelineError('Unsupported or ambiguous date syntax; source date is preserved without guessing')

def _raw_field(detail,field):
 syn=detail.get('synopsis') or detail.get('forecast');prefix='synopsis' if detail.get('synopsis') else 'forecast'
 if not isinstance(syn,dict) or not syn:raise PipelineError('Incomplete synopsis/forecast receipt')
 if field in {'title','number','status'}:name={'title':'opportunityTitle','number':'opportunityNumber','status':'ost'}[field];return detail.get(name),'detail.'+name
 names=[FIELD_NAMES.get(field)]
 if field=='description' and prefix=='forecast':names=['forecastDesc']
 if field=='expected_number_of_awards':names=['expectedNumberOfAwards','numberOfAwards']
 found=[(name,syn[name]) for name in names if name and name in syn and syn[name] not in (None,'',[])]
 if not found:raise PipelineError('Exact raw field is absent; normalized null cannot be interpreted as zero or false')
 if len(found)>1 and digest(found[0][1])!=digest(found[1][1]):raise PipelineError('Conflicting alternate raw fields in the same receipt')
 return found[0][1],prefix+'.'+found[0][0]

def convert(claim,raw,event,oid):
 field=(claim.get('values') or {}).get('field');source=claim.get('source') or {};meta=event.get('receipt') or {}
 if claim.get('key')!='connector_field_'+str(field) or field not in MONEY|LISTS|DATES|TEXT|{'cost_sharing','expected_number_of_awards'}:raise PipelineError('No supported finite type rule for this connector field')
 if len(raw)>8*1024*1024 or event.get('schema')!='SOCIAL_CONNECTOR_OBSERVATION_V1' or event.get('mode') not in {'live','replay'}:raise PipelineError('Complete owned connector event required')
 timestamp(meta.get('fetched_at'))
 sha=sha256_bytes(raw);eid=digest({'oid':str(oid),'sha256':sha,'fetched_at':meta['fetched_at'],'mode':event['mode']})
 if event.get('event_id')!=eid or str(event.get('opportunity_id'))!=str(oid) or event.get('raw_sha256')!=sha or meta.get('sha256')!=sha or type(meta.get('bytes')) is not int or meta['bytes']!=len(raw) or meta.get('url')!=API or meta.get('http_status')!=200 or str((meta.get('request') or {}).get('opportunityId'))!=str(oid):raise PipelineError('Receipt/event/opportunity/hash/length binding differs')
 if source.get('snapshot_sha256')!=sha or source.get('snapshot_file')!='connector_observation_inbox/'+eid+'.raw' or source.get('url')!='https://www.grants.gov/search-results-detail/'+str(oid):raise PipelineError('Accepted raw claim belongs to another saved receipt')
 body=_json(raw)
 if not isinstance(body,dict) or type(body.get('errorcode')) not in (int,str) or body.get('errorcode') not in (0,'0'):raise PipelineError('Incomplete/error API body')
 detail=body.get('data')
 if not isinstance(detail,dict) or str(detail.get('id'))!=str(oid):raise PipelineError('Wrong API body opportunity')
 incoming=project(raw,oid)
 if digest(incoming[field])!=digest((claim.get('values') or {}).get('candidate')):raise PipelineError('Accepted normalized value differs from exact saved API projection')
 value,path=_raw_field(detail,field);normalized=incoming[field];values={};label=field.replace('_',' ')
 if field in MONEY:
  number=_numeric(value)
  if normalized is None or Decimal(str(normalized))!=Decimal(str(number)):raise PipelineError('Numeric source and accepted normalized value disagree')
  values[field]=number;shown='$'+format(number,',.2f' if not isinstance(number,int) else ',d')
 elif field=='expected_number_of_awards':
  number=_numeric(value,True)
  if normalized is None or Decimal(str(normalized))!=Decimal(number):raise PipelineError('Award count source and accepted value disagree')
  values[field]=number;shown=str(number)
 elif field in DATES:
  date=_date(value)
  if normalized!=date.isoformat():raise PipelineError('Raw and accepted normalized date disagree')
  values['date']=date.isoformat();shown=human_date(date);label='posting date' if field=='open_date' else 'response date'
 elif field=='cost_sharing':
  if type(value) is bool:boolean=value
  elif type(value) is str and value.strip().lower() in {'yes','true','y','1','no','false','n','0'}:boolean=value.strip().lower() in {'yes','true','y','1'}
  else:raise PipelineError('Cost-sharing source must have explicit boolean syntax')
  if type(normalized) is not bool or normalized!=boolean:raise PipelineError('Cost-sharing raw and accepted values disagree')
  values['cost_sharing_required']=boolean;shown='required' if boolean else 'not required'
 elif field in LISTS:
  if not isinstance(value,list) or not 1<=len(value)<=40:raise PipelineError('Expected full bounded source list; truncated or coerced lists are refused')
  labels=[]
  for item in value:
   if isinstance(item,dict):
    options=[item[k] for k in ('description','programTitle','alnNumber') if item.get(k) not in (None,'')]
    if not options or any(type(x) is not str for x in options):raise PipelineError('Source list member lacks explicit text label')
    item=options[0]
   labels.append(_text(item).strip())
  if sorted(labels)!=normalized or len(labels)!=len(set(labels)):raise PipelineError('Complete source list and accepted normalized list differ or duplicate labels')
  values[field]=labels;shown='; '.join(labels)
 else:
  _text(value);shown=_text(normalized)
  if field=='full_announcement_url':
   from urllib.parse import urlsplit
   url=urlsplit(shown)
   if url.scheme!='https' or not (url.hostname or '').endswith('.gov') or url.username:raise PipelineError('Announcement link is not an explicit official HTTPS government URL')
 statement='Saved Grants.gov '+label+': '+shown+'.'
 values['quote']=statement
 receipt={'schema':event['schema'],'event_id':eid,'opportunity_id':str(oid),'receipt':copy.deepcopy(meta),'mode':event['mode'],'raw_sha256':sha}
 origin={'rule':RULE,'raw_claim':copy.deepcopy(claim),'field':field,'json_path':path,'raw_value':copy.deepcopy(value),'accepted_normalized_value':copy.deepcopy(normalized),'accepted_claim_sha256':digest(claim),'event':receipt}
 typed={'key':'listing_'+field,'statement':statement,'values':values,'source':copy.deepcopy(source),'listing_scope':'saved_listing_field_only_no_primary_override','conversion_origin':origin}
 return {'raw_key':claim['key'],'typed_claim':typed,'raw_claim':copy.deepcopy(claim),'receipt':receipt,'rule':RULE,'opportunity_id':str(oid)}

def propose(store,id,claim):
 try:
  from .fact_versions import _relative
  job=store.get(id);topic=read_json(Path(job['run_dir'])/'topic.json');rec=topic.get('selected',topic);name=_relative((claim.get('source') or {}).get('snapshot_file'));file=(store.root/name).resolve()
  if not file.is_relative_to((store.root/'connector_observation_inbox').resolve()) or file.suffix!='.raw' or file.stat().st_size>8*1024*1024:raise PipelineError('Owned bounded connector inbox receipt required')
  eventfile=file.with_suffix('.json')
  if eventfile.stat().st_size>1024*1024:raise PipelineError('Connector event exceeds bounded metadata size')
  event=_json(eventfile.read_bytes());projection=convert(claim,file.read_bytes(),event,rec.get('opportunity_id'))
  return {**projection,'blocked_reason':None}
 except (OSError,ValueError,TypeError,KeyError,AttributeError,PipelineError) as error:return {'raw_key':claim.get('key'),'raw_claim':copy.deepcopy(claim),'blocked_reason':str(error)[:500]}

def pairs(claims,projections,required=()):
 result=[];by={c['key']:c for c in claims};forced={(p['candidate'],p['retained_claim']) for p in required}
 for p in projections:
  if p.get('blocked_reason'):continue
  raw=p['raw_claim'];field=raw['values']['field'];sourcefield=FIELD_NAMES[field]
  for prior in claims:
   if prior['key'].startswith('connector_field_'):continue
   aliases={sourcefield}
   if field=='expected_number_of_awards':aliases.add('expectedNumberOfAwards')
   same=any(str(f).split('.')[-1] in aliases for f in (prior.get('source') or {}).get('fields',[])) or (prior.get('conversion_origin') or {}).get('field')==field
   values=prior.get('values') or {};key=prior['key']
   semantic=(field in MONEY and (any(k in values for k in MONEY) or any(x in key for x in ('budget','funding','award_range','award_ceiling')))) or (field in DATES and (key in {'deadline','posted','full_proposal_deadline'} or any(x in key for x in ('deadline','submission','schedule')))) or (field in {'applicant_types','applicant_eligibility_desc'} and any(x in key for x in ('eligib','applicant','lead_organizations','PI_appointments'))) or (field=='cost_sharing' and 'cost_sharing_required' in values) or (field=='expected_number_of_awards' and 'expected_number_of_awards' in values) or (field in {'title','number'} and key=='identity') or (field=='status' and key=='status') or (field=='description' and any(x in key for x in ('purpose','objective')))
   if not(same or semantic or key in raw.get('related_claim_keys',[]) or (raw['key'],key) in forced):continue
   primary_key=key.startswith(('primary_','track_','tracks_','dependency_')) or key in {'project_budget','phase_budget','full_proposal_deadline'}
   listing=(prior.get('source') or {}).get('url')==raw['source']['url'] and same and not primary_key
   pair={'candidate':raw['key'],'prior':key,'candidate_statement':p['typed_claim']['statement'],'prior_statement':prior['statement'],'prior_is_same_listing_field':listing,'basis':'exact_field_binding' if same else 'potential_related_scope_requires_explicit_review','choices':['keep_prior_exclude_candidate','replace_prior_listing'] if listing else ['keep_prior_exclude_candidate','retain_distinct_scopes'],'candidate_sha256':digest(raw),'prior_sha256':digest(prior)}
   pair['pair_id']=digest(pair);result.append(pair)
 return sorted(result,key=lambda p:p['pair_id'])


def verify_typed(directory,claim):
 from .fact_versions import _relative
 root=Path(directory).resolve();origin=claim.get('conversion_origin') or {};raw_claim=origin.get('raw_claim')
 if not isinstance(raw_claim,dict):raise PipelineError('Typed listing claim lacks its exact original raw claim')
 file=(root/_relative((raw_claim.get('source') or {}).get('snapshot_file'))).resolve()
 if not file.is_relative_to(root) or file.stat().st_size>8*1024*1024:raise PipelineError('Typed listing evidence outside source scope or size bound')
 event=origin.get('event') or {};result=convert(raw_claim,file.read_bytes(),event,event.get('opportunity_id'))
 if digest(result['typed_claim'])!=digest(claim):raise PipelineError('Typed listing claim differs from deterministic saved-source interpretation')
 return True

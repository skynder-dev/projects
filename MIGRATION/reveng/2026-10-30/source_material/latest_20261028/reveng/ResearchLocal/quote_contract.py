"""Exact public-source quotation binding only, never semantic entailment."""
import hashlib
import source_context
import commercial_review
def index_observations(observations):
 if not isinstance(observations,list):raise ValueError('Observation inventory must be a list')
 byid={}
 for row in observations:
  if not isinstance(row,dict) or not isinstance(row.get('evidence_id'),str) or not row['evidence_id'].strip():raise ValueError('Observation needs an explicit E-ID')
  if row['evidence_id'] in byid:raise ValueError('Ambiguous duplicate E-ID: '+row['evidence_id'])
  byid[row['evidence_id']]=row
 return byid
def verify(claims,observations,allowed_ids=None,shared_budgets=None):
 try:byid=index_observations(observations)
 except ValueError as ex:return {'status':'invalid','verified':[],'errors':[str(ex)],'unknown':0,'hypothesis_truth':'unknown','auto_admission':False}
 verified=[];errors=[];unknown=0;budgets=shared_budgets if shared_budgets is not None else {}
 if not isinstance(claims,list):return {'status':'invalid','verified':[],'errors':['observations_used must be a list'],'unknown':0,'hypothesis_truth':'unknown'}
 if len(claims)>5:errors.append('At most five source fragments per card')
 # Preserve every old canonical-URL budget group, then add only confirmed
 # question aliases from the complete inventory. Per-row fallback must not split
 # a group when another row has contradictory metadata or an ambiguous fragment.
 source_keys={}
 for row in byid.values():
  if not isinstance(row.get('kind'),str) or row['kind'] not in commercial_review.PROBLEM_REPORT_KINDS or not isinstance(row.get('url'),str):continue
  try:
   original=commercial_review.canonical(row['url']);identity=commercial_review.row_report_identity(row)
  except ValueError:continue # Unresolved URL identity cannot add an alias.
  if not identity:continue
  resolved=commercial_review.canonical(identity)
  if resolved==original:continue
  if original in source_keys and source_keys[original]!=resolved:errors.append('Ambiguous quotation source identity');continue
  source_keys[original]=resolved
 # A caller may supply an existing budget before a confirmed alias was present.
 # Move its count, rather than giving the newly resolved source a fresh budget.
 for previous in list(budgets):
  resolved=source_keys.get(previous,previous)
  if resolved!=previous:budgets[resolved]=budgets.get(resolved,0)+budgets.pop(previous)
 for index,claim in enumerate(claims):
  if not isinstance(claim,dict) or set(claim)!={'evidence_id','source_field','quote','support'}:errors.append('Malformed observation entry '+str(index));continue
  if claim['evidence_id'] is not None and (claim['evidence_id'] not in byid or allowed_ids is not None and claim['evidence_id'] not in allowed_ids):errors.append('Quote reference outside the card evidence_ids');continue
  if claim['support']=='unknown':
   if claim['quote'] is not None:errors.append('Unknown support must not pretend to quote')
   if isinstance(claim['quote'],str) and len(claim['quote'].split())>25:errors.append('Quote word limit exceeded for '+str(claim['evidence_id'])+': '+str(len(claim['quote'].split()))+' > 25')
   if claim['source_field'] not in [None,'title','observed_text','answer_text']:errors.append('Unknown source field')
   unknown+=1;continue
  id=claim['evidence_id'];row=byid.get(id);field=claim['source_field'];quote=claim['quote']
  if claim['support']!='source_quote' or row is None or field not in ['title','observed_text','answer_text'] or not isinstance(quote,str) or not quote.strip() or len(quote)>220:errors.append('Invalid source/field/quote at '+str(index));continue
  packet=source_context.source_packet(row);text=packet[field]
  if not text or quote not in text:
   errors.append('Quote is not an exact fragment of '+str(id)+'.'+str(field))
   if len(quote.split())>25:errors.append('Quote word limit exceeded for '+str(id)+': '+str(len(quote.split()))+' > 25')
   continue
  source_url=packet.get('answer_url') if field=='answer_text' else row['url']
  if not source_url:errors.append('Missing source URL for answer quote');continue
  # The selected answer permalink and its question resolve to the same thread page.
  # Keep answer attribution separate, but share the page quotation budget.
  original=commercial_review.canonical(row['url']);key=source_keys.get(original,original)
  words=len(quote.split());budgets[key]=budgets.get(key,0)+words
  if budgets[key]>25:errors.append('Source quote word budget exceeded for '+str(id));continue
  start=text.index(quote);verified.append({'evidence_id':id,'source_field':field,'quote':quote,'start':start,'end':start+len(quote),'field_sha256':hashlib.sha256(text.encode()).hexdigest(),'source_url':source_url,'source_scope':packet.get('answer_scope') if field=='answer_text' else packet['content_scope'],'evidence_role':'community_answer_not_verified_resolution_or_demand' if field=='answer_text' else packet['evidence_role'],'meaning':'Literal fragment exists in the supplied source text; no causal, buyer, demand or profitability inference verified'})
 return {'status':'invalid' if errors else 'verified_literals' if verified else 'unknown','verified':verified,'errors':errors,'unknown':unknown,'hypothesis_truth':'unknown','auto_admission':False}

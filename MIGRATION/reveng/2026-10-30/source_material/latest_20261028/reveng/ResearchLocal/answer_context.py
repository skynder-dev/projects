"""One bounded documented answer batch/site; community advice is not verified resolution."""
import asyncio,json,math,re,time
import json_contract
from urllib.parse import urlsplit,urlencode
import source_context
SCHEMA='se-answer-context-v1'
SITES={'webapps':'webapps','diy':'diy','travel':'travel','design':'graphicdesign','superuser':'superuser','webmasters':'webmasters','softwarerecs':'softwarerecs','opensource':'opensource'}

def question_id(row):
 match=re.search(r'/questions/(\d+)(?:/|$)',urlsplit(row['url']).path)
 return int(match.group(1)) if match else None

def attach(rows,obj,endpoint,response_hash,observed_at,parser_version=source_context.TEXT_PARSER):
 if parser_version not in (source_context.TEXT_PARSER,source_context.LEGACY_TEXT_PARSER):raise ValueError('Unsupported answer text parser version')
 if obj.get('backoff'):raise ValueError('API backoff requested; no retry')
 if obj.get('error_id'):raise ValueError('StackExchange API error')
 groups={question_id(r):[] for r in rows}
 for answer in obj.get('items',[]):
  if answer.get('question_id') not in groups:raise ValueError('Answer belongs to an unrequested question')
  if not isinstance(answer.get('answer_id'),int):raise ValueError('Missing answer ID')
  groups[answer['question_id']].append(answer)
 for row in rows:
  answers=groups[question_id(row)];accepted=row.get('accepted_answer_id')
  answers.sort(key=lambda a:(a['answer_id']==accepted,a.get('score',0),-a['answer_id']),reverse=True)
  row.update(answer_fetch_status='batch_partial' if obj.get('has_more') else 'batch_complete',answer_batch_has_more=bool(obj.get('has_more')),answers_returned_for_question=len(answers),answer_endpoint=endpoint,answer_response_sha256=response_hash,answer_observed_at=observed_at,answer_text_parser_version=parser_version,answer_body_available=False,answer_text=None,answer_resolution='unknown_not_independently_verified')
  if not answers:
   row['answer_fetch_status']='no_answers_in_partial_batch' if obj.get('has_more') else 'no_answers_in_api_snapshot'
   continue
  selected=answers[0];context=source_context.context(selected.get('body'),'body','community_answer',parser_version=parser_version)
  # Link the answer itself, never quote community advice as if it were the question author.
  origin=urlsplit(row['url']);url=origin.scheme+'://'+origin.netloc+'/a/'+str(selected['answer_id'])
  row.update(answer_id=selected['answer_id'],answer_url=url,answer_text=context['context_text'] or None,answer_body_available=context['body_available'],answer_text_sha256=context['context_text_sha256'],answer_source_text_sha256=context['source_text_sha256'],answer_text_chars=context['source_text_chars'],answer_text_truncated=context['context_truncated'],answer_score=selected.get('score'),answer_api_is_accepted=selected.get('is_accepted'),answer_selection='accepted_answer' if selected['answer_id']==accepted else 'highest_vote_returned_answer',accepted_answer_not_returned=bool(accepted and all(a['answer_id']!=accepted for a in answers)),answer_author_id=selected.get('owner',{}).get('user_id'),answer_scope='one_community_answer_only_not_whole_thread')
  for key in ['media_references','media_reference_count','media_element_count','media_references_truncated','link_targets','link_target_count','link_targets_truncated']:
   row['answer_'+key]=context.get(key)
 return rows

async def enrich(m,cache,run,stats,source,rows,source_errors=None):
 if source['id'] not in SITES:return rows
 m.cancelled(run)
 ids=[question_id(r) for r in rows]
 if not ids or any(i is None for i in ids):raise ValueError('Missing selected question IDs')
 endpoint='https://api.stackexchange.com/2.3/questions/'+';'.join(map(str,sorted(ids)))+'/answers?'+urlencode({'site':SITES[source['id']],'pagesize':100,'sort':'votes','order':'desc','filter':'withbody'})
 folder=cache/'answer-context';path=folder/(m.sha((SCHEMA+endpoint).encode())+'.json');saved=None;cache_failure=True
 try:
  folder.mkdir(exist_ok=True)
  # An unreadable/damaged checkpoint is evidence, not an ordinary cache miss.
  # Validate it before TTL handling so expiry cannot silently authorize replacement.
  try:raw=path.read_text(encoding='utf-8')
  except FileNotFoundError:
   if path.is_symlink():raise ValueError('Dangling answer cache link')
   raw=None;cache_failure=False
  if raw is not None:
   data=json_contract.strict_loads(raw)
   if not isinstance(data,dict):raise ValueError('Answer cache must be an object')
   claim=data.pop('integrity_sha256',None)
   if claim!=m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()):raise ValueError('Answer cache checksum mismatch')
   if data.get('endpoint')!=endpoint:raise ValueError('Answer cache endpoint mismatch')
   expiry=data.get('expires')
   if type(expiry) not in (int,float) or not math.isfinite(expiry) or expiry<0:raise ValueError('Answer cache expiry must be a finite nonnegative number')
   if not isinstance(data.get('payload'),dict) or not isinstance(data['payload'].get('items'),list):raise ValueError('Answer cache payload must contain an items list')
   if not isinstance(data.get('response_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',data['response_sha256']) or not isinstance(data.get('observed_at'),str) or not data['observed_at']:raise ValueError('Answer cache provenance is incomplete')
   # Exercise the existing answer/question contract on copies, including expired
   # entries. Failed attachment must not partially mutate the primary records.
   attach([dict(r) for r in rows],data['payload'],endpoint,data['response_sha256'],data['observed_at'],data.get('text_parser_version',source_context.LEGACY_TEXT_PARSER))
   cache_failure=False
   if expiry>time.time():saved=data;stats['source_cache_hits']+=1
  if saved is None:
   if __import__('os').environ.get('REVENG_OFFLINE_REPLAY')=='1':raise ValueError('No fresh answer cache; no HTTP fallback')
   payload=await asyncio.to_thread(m.read_http,endpoint,stats);obj=json.loads(payload.decode('utf-8'))
   # Validate before checkpointing; no negative cache on failure/budget/backoff.
   attach([dict(r) for r in rows],obj,endpoint,m.sha(payload),m.now())
   archive=cache/'source-payloads';archive.mkdir(exist_ok=True);(archive/(m.sha(payload)+'.raw')).write_bytes(payload)
   saved={'endpoint':endpoint,'expires':time.time()+3600,'payload':obj,'response_sha256':m.sha(payload),'observed_at':m.now(),'text_parser_version':source_context.TEXT_PARSER}
   m.dump(path,dict(saved,integrity_sha256=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode())))
  enriched=attach([dict(r) for r in rows],saved['payload'],endpoint,saved['response_sha256'],saved['observed_at'],saved.get('text_parser_version',source_context.LEGACY_TEXT_PARSER))
  for row,value in zip(rows,enriched):row.update(value,answer_context_expires=saved['expires'])
 except (ValueError,TypeError,KeyError,AttributeError,OSError,OverflowError,RecursionError) as ex:
  reason=('Cached answer context unavailable: ' if cache_failure else 'Answer context unavailable: ')+type(ex).__name__+': '+' '.join(str(ex).split())[:200]
  if cache_failure:stats['answer_cache_errors']=stats.get('answer_cache_errors',0)+1
  for row in rows:row.update(answer_fetch_status='unavailable_unknown',answer_body_available=False,answer_text=None,answer_resolution='unknown',answer_collection_limitation=reason,answer_context_expires=time.time()+900)
  if source_errors is not None:
   failure={'source':source['id'],'scope':'answer_context','reason':reason,'retry':False,'primary_observations_preserved':True}
   if cache_failure:failure.update(cache_file=path.name,cache_bytes_preserved=True,network_retry_performed=False)
   source_errors.append(failure)
 return rows

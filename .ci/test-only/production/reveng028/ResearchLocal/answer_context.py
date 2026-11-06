"""One bounded documented answer batch/site; community advice is not verified resolution."""
import asyncio,json,re,time
from urllib.parse import urlsplit,urlencode
import source_context
SCHEMA='se-answer-context-v1'
SITES={'webapps':'webapps','diy':'diy','travel':'travel','design':'graphicdesign','superuser':'superuser','webmasters':'webmasters','softwarerecs':'softwarerecs','opensource':'opensource'}

def question_id(row):
 match=re.search(r'/questions/(\d+)(?:/|$)',urlsplit(row['url']).path)
 return int(match.group(1)) if match else None

def attach(rows,obj,endpoint,response_hash,observed_at):
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
  row.update(answer_fetch_status='batch_partial' if obj.get('has_more') else 'batch_complete',answer_batch_has_more=bool(obj.get('has_more')),answers_returned_for_question=len(answers),answer_endpoint=endpoint,answer_response_sha256=response_hash,answer_observed_at=observed_at,answer_body_available=False,answer_text=None,answer_resolution='unknown_not_independently_verified')
  if not answers:
   row['answer_fetch_status']='no_answers_in_partial_batch' if obj.get('has_more') else 'no_answers_in_api_snapshot'
   continue
  selected=answers[0];context=source_context.context(selected.get('body'),'body','community_answer')
  # Link the answer itself, never quote community advice as if it were the question author.
  origin=urlsplit(row['url']);url=origin.scheme+'://'+origin.netloc+'/a/'+str(selected['answer_id'])
  row.update(answer_id=selected['answer_id'],answer_url=url,answer_text=context['context_text'] or None,answer_body_available=context['body_available'],answer_text_sha256=context['context_text_sha256'],answer_source_text_sha256=context['source_text_sha256'],answer_text_chars=context['source_text_chars'],answer_text_truncated=context['context_truncated'],answer_score=selected.get('score'),answer_api_is_accepted=selected.get('is_accepted'),answer_selection='accepted_answer' if selected['answer_id']==accepted else 'highest_vote_returned_answer',accepted_answer_not_returned=bool(accepted and all(a['answer_id']!=accepted for a in answers)),answer_author_id=selected.get('owner',{}).get('user_id'),answer_scope='one_community_answer_only_not_whole_thread')
  for key in ['media_references','media_reference_count','media_element_count','media_references_truncated','link_targets','link_target_count','link_targets_truncated']:
   row['answer_'+key]=context.get(key)
 return rows

async def enrich(m,cache,run,stats,source,rows):
 if source['id'] not in SITES:return rows
 m.cancelled(run)
 ids=[question_id(r) for r in rows]
 if not ids or any(i is None for i in ids):raise ValueError('Missing selected question IDs')
 endpoint='https://api.stackexchange.com/2.3/questions/'+';'.join(map(str,sorted(ids)))+'/answers?'+urlencode({'site':SITES[source['id']],'pagesize':100,'sort':'votes','order':'desc','filter':'withbody'})
 folder=cache/'answer-context';folder.mkdir(exist_ok=True);path=folder/(m.sha((SCHEMA+endpoint).encode())+'.json');saved=None
 try:
  if path.exists():
   data=json.loads(path.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
   if data.get('endpoint')==endpoint and data.get('expires',0)>time.time() and claim==m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()):saved=data;stats['source_cache_hits']+=1
  if saved is None:
   if __import__('os').environ.get('REVENG_OFFLINE_REPLAY')=='1':raise ValueError('No fresh answer cache; no HTTP fallback')
   payload=await asyncio.to_thread(m.read_http,endpoint,stats);obj=json.loads(payload.decode('utf-8'))
   # Validate before checkpointing; no negative cache on failure/budget/backoff.
   attach([dict(r) for r in rows],obj,endpoint,m.sha(payload),m.now())
   archive=cache/'source-payloads';archive.mkdir(exist_ok=True);(archive/(m.sha(payload)+'.raw')).write_bytes(payload)
   saved={'endpoint':endpoint,'expires':time.time()+3600,'payload':obj,'response_sha256':m.sha(payload),'observed_at':m.now()}
   m.dump(path,dict(saved,integrity_sha256=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode())))
  attach(rows,saved['payload'],endpoint,saved['response_sha256'],saved['observed_at'])
  for row in rows:row['answer_context_expires']=saved['expires']
 except Exception as ex:
  for row in rows:row.update(answer_fetch_status='unavailable_unknown',answer_body_available=False,answer_text=None,answer_resolution='unknown',answer_collection_limitation=type(ex).__name__+': '+' '.join(str(ex).split())[:200],answer_context_expires=time.time()+900)
 return rows

"""Per-original-post checkpoints prevent re-fetching completed context after cancellation."""
import asyncio,json,time
import source_context,wordpress_identity
async def enrich(m,cache,run,stats,robots,rows):
 folder=cache/'topic-context';folder.mkdir(exist_ok=True);archive=cache/'source-payloads';archive.mkdir(exist_ok=True)
 for row in rows:
  m.cancelled(run);path=folder/(m.sha((source_context.SCHEMA+'|wp'+str(wordpress_identity.CONTRACT)+'|'+row['url']).encode())+'.json');saved=None
  try:
   if path.exists():
    data=json.loads(path.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
    if data.get('url')==row['url'] and data.get('expires',0)>time.time() and claim==m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()):saved=data;stats['source_cache_hits']+=1
   if saved is None:
    if not robots.can_fetch(m.UA,row['url']):raise ValueError('robots.txt denied original post')
    body=await asyncio.to_thread(m.read_http,row['url'],stats);context=source_context.wordpress(body,row['url']);(archive/(m.sha(body)+'.raw')).write_bytes(body)
    context.update(collection_limitations=[],context_response_sha256=m.sha(body),context_observed_at=m.now(),context_cache_expires=time.time()+3600)
    saved={'url':row['url'],'expires':context['context_cache_expires'],'context':context};m.dump(path,dict(saved,integrity_sha256=m.sha(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode())))
   row.update(saved['context'])
  except Exception as ex:
   row.setdefault('collection_limitations',[]).append('Original body unavailable: '+m.error_text(ex,140));row['context_cache_expires']=time.time()+900
 return rows

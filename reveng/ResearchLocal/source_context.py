"""Public source context with explicit scope/truncation. No interpretation of demand."""
import re,hashlib
from datetime import datetime,timezone
from html.parser import HTMLParser
SCHEMA='source-context-v1'
class Fragment(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style']:self.skip+=1
  if tag in ['p','br','div','li','pre']:self.parts.append(' ')
 def handle_endtag(self,tag):
  if tag in ['script','style'] and self.skip:self.skip-=1
  if tag in ['p','div','li','pre']:self.parts.append(' ')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def text(html):
 p=Fragment();p.feed(str(html or ''));return ' '.join(' '.join(p.parts).split())
def context(html,field,scope,is_html=True):
 full=text(html) if is_html else ' '.join(str(html or '').split());links=sorted(set(x.rstrip('.,);') for x in re.findall(r'https?://[^\s<>"\']+',full)))[:12]
 result={'context_text':full[:12000],'excerpt':full[:2000],'body_available':bool(full),'source_field':field,'content_scope':scope if full else 'title_only','source_text_chars':len(full),'context_truncated':len(full)>12000,'excerpt_truncated':len(full)>2000,'source_text_sha256':hashlib.sha256(full.encode()).hexdigest(),'context_text_sha256':hashlib.sha256(full[:12000].encode()).hexdigest(),'linked_context_urls':links}
 if is_html:
  import html_references
  result.update(html_references.extract(html))
 return result

def title_only(row):
 return dict(row,excerpt='',body_available=False,content_scope='title_only',source_field='title',answer_status='unknown_not_collected',answer_body_available=False,collection_limitations=['Original post body has not been collected; this is a collector limitation, not a user complaint'])
def parse_api(source,obj):
 rows=[]
 if source['id']=='webapps' or source.get('site'):
  if obj.get('backoff'):raise ValueError('API backoff requested; no retry')
  for x in obj.get('items',[])[:5]:
   data=context(x.get('body'),'body','question_body');available=data['body_available'];title=text(x['title']);data.update(title=title[:1000],title_truncated=len(title)>1000,url=x['link'],published_at=x.get('creation_date'),kind='public_question_context' if available else 'public_question_title',author_id=source['id']+':'+str(x['owner']['user_id']) if x.get('owner',{}).get('user_id') is not None else None,answer_count=x.get('answer_count'),api_is_answered=x.get('is_answered'),accepted_answer_id=x.get('accepted_answer_id'),answer_body_available=False,answer_status='accepted_answer_exists' if x.get('accepted_answer_id') else 'answer_exists' if x.get('answer_count',0)>0 else 'no_answer_in_api_snapshot')
   rows.append(data)
 elif source['id']=='hackernews':
  for x in obj.get('hits',[])[:5]:
   data=context(x.get('story_text'),'story_text','original_ask_post');data.update(title=text(x.get('title')),url='https://news.ycombinator.com/item?id='+str(x['objectID']),published_at=x.get('created_at'),kind='public_ask_post',author_id='hn:'+str(x['author']) if x.get('author') else None,discussion_count=x.get('num_comments'),answer_status='discussion_exists' if x.get('num_comments',0)>0 else 'unknown',answer_body_available=False);rows.append(data)
 elif source['id']=='npm':
  for x in obj.get('objects',[])[:5]:
   from urllib.parse import quote
   p=x['package'];data=context(p.get('description'),'description','package_description_only',is_html=False);data.update(title=p['name'],url='https://www.npmjs.com/package/'+quote(p['name'],safe='@/'),published_at=p.get('date'),kind='package_listing_not_demand',evidence_role='existing_software_not_customer',answer_status='not_applicable');rows.append(data)
 return rows
def wordpress(body,url):
 import wordpress_identity
 body=wordpress_identity.validate(url,body,original=True)
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(body,'html.parser');post=soup.select_one('.bbp-topic-content')
 if post is None:raise ValueError('Original WordPress post body not found; no whole-thread inference')
 data=context(str(post),'original_post_html','original_post_only')
 if not data['body_available']:raise ValueError('Original WordPress post body empty')
 data.update(wordpress_parser_contract=wordpress_identity.CONTRACT,original_url_verified=url,kind='public_topic_context',answer_body_available=False,answer_status='resolved_marker_observed' if soup.title and '[resolved]' in soup.title.get_text().lower() else 'unknown')
 return data
def source_packet(row):
 body=row.get('context_text') or row.get('excerpt') or None
 if row.get('kind') in ['public_topic_title','public_question_title']:body=None
 packet={'evidence_id':row['evidence_id'],'source':row['source'],'title':row['title'],'observed_text':body,'quote_field':'observed_text','quote_scope':'Exact fragment of supplied normalized text only; not semantic proof','source_kind':row['kind'],'content_scope':'title_only' if body is None else row.get('content_scope','source_excerpt'),'source_field':row.get('source_field'),'source_text_sha256':row.get('source_text_sha256'),'observed_text_sha256':hashlib.sha256(body.encode()).hexdigest() if body else None,'source_text_chars':row.get('source_text_chars'),'text_truncated':row.get('context_truncated',row.get('excerpt_truncated',False)),'answer_status':row.get('answer_status','unknown_not_collected'),'answer_count':row.get('answer_count'),'accepted_answer_id':row.get('accepted_answer_id'),'answer_body_available':row.get('answer_body_available',False),'author_id':row.get('author_id'),'same_author_evidence_ids':row.get('same_author_evidence_ids',[]),'shared_context_evidence_ids':row.get('shared_context_evidence_ids',[]),'independence_status':'not established; shared author is not a separate buyer','evidence_role':'existing_software_listing_not_demand' if row['kind']=='package_listing_not_demand' else 'public_report_not_customer','collection_limitations':row.get('collection_limitations',[])}
 for key in ['answer_text','answer_url','answer_id','answer_text_sha256','answer_source_text_sha256','answer_text_chars','answer_text_truncated','answer_scope','answer_selection','answer_author_id','answer_api_is_accepted','answer_score','answer_fetch_status','answer_batch_has_more','answers_returned_for_question','accepted_answer_not_returned','answer_resolution','answer_collection_limitation']:
  packet[key]=row.get(key)
 for key in ['media_references','media_reference_count','media_element_count','media_references_truncated','link_targets','link_target_count','link_targets_truncated','external_reference_scope','answer_media_references','answer_media_reference_count','answer_media_element_count','answer_media_references_truncated','answer_link_targets','answer_link_target_count','answer_link_targets_truncated']:
  packet[key]=row.get(key)
 for key in ['observation_id','source_revision_hash','novelty','first_observed_at','observation_snapshot_id','prior_same_author_urls','prior_same_author_count']:
  packet[key]=row.get(key)
 # Provenance dates are distinct from cache TTL, and never refreshed by projection.
 published=row.get('published_at')
 if isinstance(published,(int,float)):
  try:published=datetime.fromtimestamp(published,timezone.utc).isoformat()
  except (ValueError,OverflowError,OSError):published=None
 packet.update(published_at=published,observed_at=row.get('observed_at'),context_observed_at=row.get('context_observed_at'),answer_observed_at=row.get('answer_observed_at'))
 return packet

def annotate_relations(rows):
 for row in rows:
  same=[x for x in rows if x['evidence_id']!=row['evidence_id'] and row.get('author_id') and x.get('author_id')==row['author_id'] and x.get('source')==row.get('source')]
  row['same_author_evidence_ids']=[x['evidence_id'] for x in same]
  row['shared_context_evidence_ids']=[x['evidence_id'] for x in same if set(row.get('linked_context_urls',[]))&set(x.get('linked_context_urls',[]))]
 return rows

def saved_question_contexts(m,root):
 """Verified sealed inputs only; no model results, guessed bodies or URL-only E-ID joins."""
 import json,analysis_jobs
 from pathlib import Path
 folder=Path(root)/'analysis-inputs';index={};warnings=[]
 if any(p.is_symlink()or getattr(p,'is_junction',lambda:False)()for p in [folder,*folder.absolute().parents]):return {},['Reparse saved-input path; no automatic body refresh']
 paths=sorted(folder.glob('*.json'))
 if len(paths)>256:return {},['Saved input scan limit exceeded; no automatic body refresh']
 for path in paths:
  try:
   if path.is_symlink()or path.resolve().parent!=folder.resolve()or path.stat().st_size>8*1024*1024:raise ValueError('Unsafe or oversized saved input')
   id,meta=analysis_jobs.inspect_input(m,Path(root),path);data=json.loads(path.read_text(encoding='utf-8'))
   for row in data['observations']:
    body=row.get('context_text');stamp=row.get('context_observed_at')or row.get('observed_at')
    if not isinstance(body,str)or not body or row.get('context_truncated')is not False or row.get('source_text_chars')!=len(body)or row.get('content_scope')not in ['question_body','original_ask_post','original_post_only']:continue
    h=hashlib.sha256(body.encode()).hexdigest()
    if h!=row.get('context_text_sha256')or h!=row.get('source_text_sha256'):continue
    from capture_dates import timestamp
    at=timestamp(stamp)
    if at is None or at>__import__('time').time():continue
    index.setdefault(row['url'],[]).append({'row':row,'at':at,'origin':{'input_file':meta['input_file'],'input_file_sha256':meta['input_file_sha256'],'input_sha256':id,'original_evidence_id':row.get('evidence_id'),'scope':'Complete saved normalized question context; not raw response bytes'}})
  except (ValueError,KeyError,TypeError,OSError)as ex:warnings.append({'input':path.name,'reason':type(ex).__name__})
 return index,warnings

def refresh_saved_basis(card,index):
 import copy
 from capture_dates import timestamp
 out=copy.deepcopy(card);changes=[]
 for i,old in enumerate(card.get('observed_basis',[])):
  if old.get('body_available')and old.get('context_text')and not old.get('context_truncated'):continue
  candidates=[v for v in index.get(old['url'],[])if v['row'].get('source')==old.get('source')and v['at']>=(timestamp(old.get('context_observed_at')or old.get('observed_at'))or float('inf'))]
  if not candidates:continue
  newest=max(v['at']for v in candidates);latest=[v for v in candidates if v['at']==newest]
  if len({v['row']['context_text_sha256']for v in latest})!=1:changes.append({'url':old['url'],'status':'review_required_conflicting_saved_bodies'});continue
  chosen=latest[0];row=copy.deepcopy(chosen['row']);row['evidence_id']=old['evidence_id'];row['saved_context_origin']=copy.deepcopy(chosen['origin']);out['observed_basis'][i]=row;changes.append({'url':old['url'],'status':'complete_saved_context_recovered','origin':chosen['origin']})
 return out,changes

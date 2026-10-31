"""Public source context with explicit scope/truncation. No interpretation of demand."""
import re,hashlib
from datetime import datetime,timezone
from html.parser import HTMLParser
SCHEMA='source-context-v1'
# Cache keys stay stable: saved normalized fields are reused byte-for-byte. Only
# newly received HTML uses v2; raw answer checkpoints select their recorded policy.
TEXT_PARSER='html-inline-v2'
LEGACY_TEXT_PARSER='html-fragment-spaces-v1'
BLOCK_TAGS=frozenset('address article aside blockquote br caption dd details div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section summary table tbody td tfoot th thead tr ul'.split())
class Fragment(HTMLParser):
 def __init__(self,legacy=False):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0;self.legacy=legacy
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style']:self.skip+=1
  if tag in (['p','br','div','li','pre'] if self.legacy else BLOCK_TAGS):self.parts.append(' ')
 def handle_endtag(self,tag):
  if tag in ['script','style'] and self.skip:self.skip-=1
  if tag in (['p','div','li','pre'] if self.legacy else BLOCK_TAGS):self.parts.append(' ')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def text(html,parser_version=TEXT_PARSER):
 if parser_version not in (TEXT_PARSER,LEGACY_TEXT_PARSER):raise ValueError('Unsupported source text parser version')
 legacy=parser_version==LEGACY_TEXT_PARSER;p=Fragment(legacy);p.feed(str(html or ''))
 if not legacy:p.close()
 # Inline markup is not whitespace: un<strong>paid</strong> must remain unpaid.
 return ' '.join((' '.join(p.parts) if legacy else ''.join(p.parts)).split())
def context(html,field,scope,is_html=True,parser_version=TEXT_PARSER):
 full=text(html,parser_version) if is_html else ' '.join(str(html or '').split());links=sorted(set(x.rstrip('.,);') for x in re.findall(r'https?://[^\s<>"\']+',full)))[:12]
 result={'context_text':full[:12000],'excerpt':full[:2000],'body_available':bool(full),'source_field':field,'content_scope':scope if full else 'title_only','source_text_chars':len(full),'context_truncated':len(full)>12000,'excerpt_truncated':len(full)>2000,'source_text_sha256':hashlib.sha256(full.encode()).hexdigest(),'context_text_sha256':hashlib.sha256(full[:12000].encode()).hexdigest(),'linked_context_urls':links,'text_parser_version':parser_version if is_html else 'plain-whitespace-v1'}
 if is_html:
  import html_references
  result.update(html_references.extract(html))
 return result

def title_only(row):
 return dict(row,excerpt='',body_available=False,content_scope='title_only',source_field='title',answer_status='unknown_not_collected',answer_body_available=False,collection_limitations=['Original post body has not been collected; this is a collector limitation, not a user complaint'])
SE_SITES={'webapps':'webapps','diy':'diy','travel':'travel','design':'graphicdesign','superuser':'superuser','webmasters':'webmasters','softwarerecs':'softwarerecs','opensource':'opensource'}
API_PARSER='public-api-rows-v2'
class RejectedRow(ValueError):
 """Expected malformed source row, not an unrelated parser/programming error."""

def require(condition,reason):
 if not condition:raise RejectedRow(reason)

def question_identity(source,url,question_id=None):
 """Known collector site and original-question URL only; never redirects/answers."""
 from urllib.parse import urlsplit,parse_qsl
 site=SE_SITES.get(source['id'])
 require(site is not None and source.get('site',site)==site,'Unknown or conflicting StackExchange source/site')
 require(isinstance(url,str),'Question link must be text')
 try:url.encode('utf-8')
 except UnicodeError:raise RejectedRow('Invalid Unicode question link') from None
 try:p=urlsplit(url);port=p.port
 except ValueError:raise RejectedRow('Malformed question link') from None
 host='superuser.com' if site=='superuser' else site+'.stackexchange.com'
 match=re.fullmatch(r'/questions/([1-9][0-9]*)(?:/([^/]+))?/?',p.path)
 require(p.scheme=='https' and p.hostname==host and p.username is None and p.password is None and port in (None,443),'Question link does not match requested source host')
 require(match is not None and not (match.group(2) or '').isdigit(),'Not an original question URL')
 require(p.fragment in ('','top') and all(k.lower().startswith('utm_') or k.lower() in ('fbclid','gclid') for k,v in parse_qsl(p.query,keep_blank_values=True)),'Ambiguous question query or fragment')
 try:qid=int(match.group(1))
 except ValueError:raise RejectedRow('Unusable question ID') from None
 require(question_id is None or (type(question_id) is int and question_id==qid),'Question ID/link mismatch')
 return qid

def string_field(obj,key,required=False):
 value=obj.get(key)
 require(isinstance(value,str) if required else value is None or isinstance(value,str),'Invalid text field: '+key)
 if isinstance(value,str):
  try:value.encode('utf-8')
  except UnicodeError:raise RejectedRow('Invalid Unicode text field: '+key) from None
 return value

def count_field(obj,key):
 value=obj.get(key)
 require(value is None or (type(value) is int and value>=0),'Invalid count: '+key)
 return value

def api_row(source,x):
 require(isinstance(x,dict),'API row must be an object')
 if source['id'] in SE_SITES or source.get('site'):
  qid=question_identity(source,x.get('link'),x.get('question_id'))
  title=string_field(x,'title',True);body=string_field(x,'body');owner=x.get('owner');owner={} if owner is None else owner
  require(isinstance(owner,dict),'Invalid question owner')
  uid=owner.get('user_id');require(uid is None or type(uid) is int,'Invalid question author ID')
  count=count_field(x,'answer_count');accepted=count_field(x,'accepted_answer_id');published=count_field(x,'creation_date')
  require(x.get('is_answered') is None or type(x['is_answered']) is bool,'Invalid question answered flag')
  data=context(body,'body','question_body');available=data['body_available'];title=text(title)
  data.update(question_id=qid,title=title[:1000],title_truncated=len(title)>1000,url=x['link'],published_at=published,kind='public_question_context' if available else 'public_question_title',author_id=source['id']+':'+str(uid) if uid is not None else None,answer_count=count,api_is_answered=x.get('is_answered'),accepted_answer_id=accepted,answer_body_available=False,answer_status='accepted_answer_exists' if accepted else 'answer_exists' if count else 'no_answer_in_api_snapshot')
 elif source['id']=='hackernews':
  identifier=x.get('objectID');require(type(identifier) in (str,int) and re.fullmatch(r'[1-9][0-9]*',str(identifier)) is not None,'Invalid Ask HN object ID')
  title=string_field(x,'title');body=string_field(x,'story_text');author=string_field(x,'author');published=string_field(x,'created_at');count=count_field(x,'num_comments')
  data=context(body,'story_text','original_ask_post');data.update(title=text(title),url='https://news.ycombinator.com/item?id='+str(identifier),published_at=published,kind='public_ask_post',author_id='hn:'+author if author else None,discussion_count=count,answer_status='discussion_exists' if count else 'unknown',answer_body_available=False)
 elif source['id']=='npm':
  from urllib.parse import quote
  p=x.get('package');require(isinstance(p,dict),'Invalid package object')
  name=string_field(p,'name',True);segments=name[1:].split('/') if name.startswith('@') else name.split('/')
  require(len(segments)==(2 if name.startswith('@') else 1) and all(re.fullmatch(r'[A-Za-z0-9._~-]+',part) and part not in ('.','..') for part in segments),'Unsafe package name/path')
  description=string_field(p,'description');published=string_field(p,'date')
  data=context(description,'description','package_description_only',is_html=False);data.update(title=name,url='https://www.npmjs.com/package/'+quote(name,safe='@/'),published_at=published,kind='package_listing_not_demand',evidence_role='existing_software_not_customer',answer_status='not_applicable')
 else:raise ValueError('Unsupported API source')
 if source['id']!='npm':data['title_text_parser_version']=TEXT_PARSER
 data['api_parser_version']=API_PARSER
 return data

def parse_api(source,obj,rejections=None):
 # Envelopes/backoff are source-wide; malformed individual items are not.
 if not isinstance(obj,dict):raise ValueError('API response must be an object')
 if obj.get('backoff'):raise ValueError('API backoff requested; no retry')
 if obj.get('error_id'):raise ValueError('API error response; no retry')
 key='items' if source['id'] in SE_SITES or source.get('site') else 'hits' if source['id']=='hackernews' else 'objects' if source['id']=='npm' else None
 if key is None:raise ValueError('Unsupported API source')
 if not isinstance(obj.get(key),list):raise ValueError('API response must contain a '+key+' list')
 rows=[]
 for index,x in enumerate(obj[key][:5]):
  try:rows.append(api_row(source,x))
  except RejectedRow as ex:
   if rejections is not None:rejections.append({'row_index':index,'reason':str(ex)})
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
 for key in ['text_parser_version','title_text_parser_version','answer_text_parser_version']:
  packet[key]=row.get(key)
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

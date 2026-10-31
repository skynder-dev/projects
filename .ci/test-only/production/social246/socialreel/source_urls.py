"""Offline structure/identity validation of source links; no liveness assertion."""
import re
from urllib.parse import urlsplit
from .common import PipelineError

def https_url(url):
 if not isinstance(url,str) or not url or len(url)>3000 or any(ord(c)<33 for c in url) or '\\' in url:raise PipelineError('Source URL has invalid type/characters')
 try:
  parts=urlsplit(url);port=parts.port
 except ValueError as e:raise PipelineError('Malformed source URL') from e
 if parts.scheme!='https' or not parts.hostname or parts.username is not None or parts.password is not None or port not in (None,443):raise PipelineError('Source URL must use HTTPS without credentials or a custom port')
 return parts

def official_url(url,record=None):
 p=https_url(url);host=p.hostname.lower()
 if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+gov',host):raise PipelineError('Official source URL must be a well-formed government domain; external references need an explicit separate label')
 id=str((record or {}).get('opportunity_id') or '')
 if host in {'grants.gov','www.grants.gov'} and id.isascii() and id.isdigit():
  if p.path.rstrip('/')!='/search-results-detail/'+id:raise PipelineError('Official listing URL belongs to a different opportunity')
  if p.query:raise PipelineError('Canonical official listing link must not add unverified query parameters')
 if id=='USA-GOV-UNCLAIMED-MONEY' and (host not in {'usa.gov','www.usa.gov'} or p.path.rstrip('/')!='/unclaimed-money'):raise PipelineError('Official public-money URL belongs to another page')
 if id=='USA-GOV-UNCLAIMED-MONEY' and p.query:raise PipelineError('Canonical public-money page cannot add unverified query parameters')
 return url

def manual_links(text,record):
 found=[]
 for m in re.finditer(r'(?:https?://|javascript:|data:|file:)[^\s<>]+',text,re.I):
  url=m.group().rstrip('.,);]');issue=None
  try:official_url(url,record)
  except PipelineError as e:issue=str(e)
  found.append({'url':url,'start_char':m.start(),'issue':issue,'status':'requires_review' if issue else 'well_formed_official_reference_not_revalidated'})
 return {'links':found,'has_unverified_or_mismatched_links':any(x['issue'] for x in found),'currentness_checked':False,'publication_authorized':False,'manual_text_preserved':True}

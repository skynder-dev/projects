"""Saved official HTML extraction and receipt validation; no transport or model."""
import hashlib,json
from pathlib import Path
import html_document_identity
CONTRACT=1
def save(root,raw,url,stamp):
 root=Path(root);digest=hashlib.sha256(raw).hexdigest();folder=root/'official-html-payloads';folder.mkdir(parents=True,exist_ok=True);path=folder/(digest+'.raw')
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Official HTML archive hash collision/corruption')
 else:
  with path.open('xb')as stream:stream.write(raw)
 return {'requested_url':url,'observed_at':stamp,'response_sha256':digest,'bytes':len(raw),'payload_file':'official-html-payloads/'+digest+'.raw','transport_scope':'Legacy read_http returns bounded HTTP 200 body bytes; response headers not retained by this receipt'}
def extract(raw,url):
 text=html_document_identity.validate(url,raw)
 from crawl4ai import LXMLWebScrapingStrategy
 from bs4 import BeautifulSoup
 cleaned=LXMLWebScrapingStrategy().scrap(url,text,word_count_threshold=1,excluded_tags=['script','style','nav','footer'])
 text=BeautifulSoup(cleaned.cleaned_html,'html.parser').get_text(' ',strip=True)
 return text,{'official_HTML_contract':CONTRACT,'HTML_identity_contract':html_document_identity.CONTRACT,'source_role':'official_pricing_document_not_question_or_reply','source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'source_text_chars':len(text),'source_text_truncated':False}
def valid_cached(root,record,url):
 if record.get('official_HTML_contract')!=CONTRACT or record.get('HTML_identity_contract')!=html_document_identity.CONTRACT:return False
 receipt=record.get('HTML_receipt')or{}
 digest=receipt.get('response_sha256')
 if not isinstance(digest,str)or len(digest)!=64 or any(x not in '0123456789abcdef'for x in digest):return False
 if receipt.get('requested_url')!=url or receipt.get('payload_file')!='official-html-payloads/'+digest+'.raw':return False
 rows=record.get('records')if 'records'in record else [record]
 if not isinstance(rows,list)or not rows or any(not isinstance(row,dict)or row.get('response_sha256')!=digest or row.get('source_url')!=url or row.get('observed_at')!=receipt.get('observed_at')or row.get('source_text_sha256')!=record.get('source_text_sha256')for row in rows):return False
 path=Path(root)/receipt['payload_file']
 try:
  raw=path.read_bytes()
  return len(raw)==receipt.get('bytes')and hashlib.sha256(raw).hexdigest()==digest and bool(html_document_identity.validate(url,raw))
 except (OSError,ValueError,UnicodeError):return False

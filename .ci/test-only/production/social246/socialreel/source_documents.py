"""Deterministic text normalization for pinned official dependency bytes."""
from html.parser import HTMLParser
class Text(HTMLParser):
 def __init__(self):super().__init__();self.main=0;self.skip=0;self.parts=[];self.links=[];self.link=None
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='main':self.main+=1
  if t in ('script','style','nav','footer','del','s'):self.skip+=1
  if self.main and not self.skip:
   if t in ('p','div','h1','h2','h3','h4','li','br','tr','section'):self.parts.append('\n')
   if t=='a':self.link=[a.get('href',''),'']
 def handle_endtag(self,t):
  if t=='a' and self.link:self.links.append(self.link);self.link=None
  if t in ('script','style','nav','footer','del','s'):self.skip=max(0,self.skip-1)
  if self.main and not self.skip and t in ('p','div','h1','h2','h3','h4','li','tr','section'):self.parts.append('\n')
  if t=='main':self.main=max(0,self.main-1)
 def handle_data(self,x):
  if self.main and not self.skip:
   self.parts.append(x)
   if self.link:self.link[1]+=x
 def text(self):return '\n'.join(' '.join(x.split()) for x in ''.join(self.parts).splitlines() if x.strip())

def normalized_text(raw,meta):
 if meta['normalization'].startswith('NSF_SOLICITATION_HTML_V1'):
  from .nsf_document import parse_solicitation
  return parse_solicitation(raw,meta['final_url'])['text']
 if raw.startswith(b'%PDF'):
  from .common import PipelineError
  try:from pypdf import PdfReader
  except ImportError as error:raise PipelineError('Pinned PDF text verification requires pypdf in the configured interpreter; no download or model fallback attempted') from error
  import io
  try:return '\n'.join('[PAGE %s]\n%s'%(i+1,page.extract_text()) for i,page in enumerate(PdfReader(io.BytesIO(raw)).pages)).replace('\r\n','\n')
  except Exception as error:raise PipelineError('Pinned PDF text could not be verified: '+type(error).__name__) from error
 p=Text();p.feed(raw.decode('utf-8'));return p.text()

# Cache by the exact raw bytes and normalization identity, never by file path/mtime.
from functools import lru_cache
_normalize_uncached=normalized_text
@lru_cache(maxsize=24)
def _normalize_cached(raw,normalization,url):
 return _normalize_uncached(raw,{'normalization':normalization,'final_url':url})
def normalized_text(raw,meta):
 return _normalize_cached(raw,meta['normalization'],meta['final_url'])

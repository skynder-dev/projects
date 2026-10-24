"""Static public HTML identity and service-response checks; no transport."""
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
CONTRACT=2
class Metadata(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.urls=[];self.title=[];self.body=[];self.in_title=False;self.hidden=0;self.originals=0;self.challenge=False;self.author=False;self.post_date=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='title':self.in_title=True
  if tag in ['script','style']:self.hidden+=1
  if tag=='link'and'canonical'in(a.get('rel')or'').lower().split():self.urls.append(a.get('href'))
  if tag=='meta'and(a.get('property')or'').lower()=='og:url':self.urls.append(a.get('content'))
  classes=(a.get('class')or'').split()
  if 'bbp-topic-content'in classes:self.originals+=1
  if 'bbp-author-name'in classes:self.author=True
  if 'bbp-topic-post-date'in classes:self.post_date=True
  if a.get('id')in ['cf-error-details','challenge-form','challenge-running']:self.challenge=True
 def handle_endtag(self,tag):
  if tag=='title':self.in_title=False
  if tag in ['script','style']:self.hidden=max(0,self.hidden-1)
 def handle_data(self,value):
  if self.in_title:self.title.append(value)
  elif not self.hidden:self.body.append(value)
def denied(m):
 title=' '.join(' '.join(m.title).split()).lower();body=' '.join(' '.join(m.body).split()).lower()
 status=r'(?:access denied|403 forbidden|just a moment[.\u2026]*|verify you are human|attention required!)(?: - nginx)?'
 bare=bool(re.fullmatch(status,title))
 branded=bool(re.fullmatch(status+r'\s*[|–—]\s*.+',title))
 # Pronouns and question marks also occur on technical challenge pages.
 # A branded status title plus refusal requires actual topic structure, not
 # narrative vocabulary. Security-service refusal remains quarantined even
 # when a page carries plausible forum markup; this is not a universal detector.
 refusal=bool(re.search(r'access denied|\bforbidden\b|verify you are human|you (?:do not|don.t) have permission|request (?:was )?(?:blocked|denied)|checking (?:your )?browser',body))
 technical=bool(re.search(r'(?:your |this )?request (?:was |has been )?(?:blocked|denied)|security service|ray id|checking (?:your )?browser|verify you are human',body))
 topic_structure=m.originals==1 and m.author and m.post_date
 return m.challenge or bare or (branded and refusal and (technical or not topic_structure))

def validate(url,raw):
 text=raw.decode('utf-8')if isinstance(raw,bytes)else raw
 if not isinstance(text,str):raise ValueError('UTF-8 HTML required')
 def identity(value):
  u=urlsplit(value or '')
  if u.scheme!='https'or not u.hostname or u.username is not None or u.password is not None or u.port not in [None,443]:raise ValueError('HTTPS canonical source identity required')
  return (u.hostname,u.path.rstrip('/'),u.query)
 expected=identity(url);m=Metadata();m.feed(text)
 if denied(m):raise ValueError('HTML access-denied/challenge document is not source content')
 if not m.urls:raise ValueError('HTML canonical source identity missing')
 if any(identity(value)!=expected for value in m.urls):raise ValueError('HTML canonical source identity mismatched')
 return text

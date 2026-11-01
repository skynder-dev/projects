"""References found in public HTML, never downloaded, executed or visually inspected."""
from html.parser import HTMLParser
from urllib.parse import urlsplit
class References(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.media=[];self.links=[];self.skip=0;self.media_elements=0
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style']:self.skip+=1;return
  if self.skip:return
  a=dict(attrs)
  if tag in ['img','iframe','video','audio','source','svg','canvas']:self.media_elements+=1
  if tag=='a' and self.allowed(a.get('href')):self.links.append(a['href'])
  if tag in ['img','iframe','video','audio','source'] and self.allowed(a.get('src')):self.media.append({'tag':tag,'url':a['src'],'alt_text':a.get('alt','')[:500]})
 def handle_endtag(self,tag):
  if tag in ['script','style'] and self.skip:self.skip-=1
 @staticmethod
 def allowed(url):
  try:
   p=urlsplit(url or '');return p.scheme in ['http','https'] and bool(p.hostname) and not p.username and not p.password and len(url)<=2048
  except ValueError:return False
def extract(html):
 p=References();p.feed(str(html or ''));links=list(dict.fromkeys(p.links));media=[];seen=set()
 for item in p.media:
  key=(item['tag'],item['url'])
  if key not in seen:media.append(item);seen.add(key)
 return {'media_references':media[:12],'media_reference_count':len(media),'media_element_count':p.media_elements,'media_references_truncated':len(media)>12,'link_targets':links[:12],'link_target_count':len(links),'link_targets_truncated':len(links)>12,'external_reference_scope':'Reference metadata only; destinations not fetched, executed, authenticated or visually inspected; zero allowed external URLs does not mean no visual content'}

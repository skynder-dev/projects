"""Bounded rotating public-source windows, unrelated to owner biography or candidate decisions."""
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit
STACK_SITES={'superuser':'Computing workflows','webmasters':'Website operations','softwarerecs':'Requested software capabilities','opensource':'Open-source project workflows','webapps':'Productivity workflows','diy':'Home maintenance','travel':'Travel operations','graphicdesign':'Creative production'}
def select(base,round):
 # Four community sources per run; alternate groups, then head/backfill/head/backfill.
 sites=list(STACK_SITES);group=round%2;visit=round//2;page=1 if visit%2==0 else 2+(visit//2)%2
 chosen=sites[group*4:group*4+4];sources=[]
 for source in base:
  if source['id']=='webapps' or source.get('site'):continue
  source=dict(source)
  if source['id']=='hackernews':
   p=urlsplit(source['url']);q=dict(parse_qsl(p.query));q['page']=str(0 if round%2==0 else 1);source['url']=urlunsplit((p.scheme,p.netloc,p.path,urlencode(q),'') )
  sources.append(source)
 for site in chosen:
  id='design' if site=='graphicdesign' else site
  sources.append({'id':id,'site':site,'kind':'json','url':'https://api.stackexchange.com/2.3/questions?'+urlencode({'site':site,'pagesize':5,'sort':'creation','order':'desc','filter':'withbody','page':page}),'family':STACK_SITES[site],'policy':'https://api.stackexchange.com/docs/questions'})
 return sources,{'round':round,'community_sites':chosen,'page':page,'window':'latest_head' if page==1 else 'bounded_backfill','limit':'Five records per selected source, shared24GET budget; not representative market sampling. Newly observed is not newly published or an independent buyer.'}

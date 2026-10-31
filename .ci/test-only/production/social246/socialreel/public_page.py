"""Fixed USA.gov source-only input. Fixture != live transport != factual approval."""
from pathlib import Path
import json,shutil,os,urllib.request,urllib.error,urllib.parse
from .common import PipelineError,write_json,read_json,atomic_bytes,sha256_file,utc_now
URL='https://www.usa.gov/unclaimed-money'
LIMIT=2*1024*1024

def allowed(url):
 p=urllib.parse.urlsplit(url)
 return p.scheme=='https' and p.hostname in {'www.usa.gov','usa.gov'} and p.path.rstrip('/')=='/unclaimed-money' and not p.query and not p.fragment and not p.username and p.port in (None,443)

def validate(spec,cfg):
 if not isinstance(spec,dict) or spec.get('kind')!='usa_gov_unclaimed':raise PipelineError('Fixed USA.gov source kind required')
 mode=spec.get('mode');policy=cfg.get('public_page') or {}
 if mode=='live':
  if set(spec)!={'kind','mode'} or policy.get('enabled') is not True or policy.get('network_authorized') is not True:raise PipelineError('Public page network execution is not authorized in server policy')
 elif mode=='fixture':
  if set(spec)!={'kind','mode','fixture_path'} or policy.get('offline_fixture_enabled') is not True:raise PipelineError('Explicit offline fixture policy required')
 else:raise PipelineError('Unknown public input mode')
 from .local_editorial import authorized as editorial_authorized
 if (cfg.get('writer')!='template' and not editorial_authorized(cfg)) or (cfg.get('llm') or {}).get('allow_spend') is not False:raise PipelineError('Public input is template/source-only without paid/model providers')
 return mode

class Redirect(urllib.request.HTTPRedirectHandler):
 def __init__(self):self.count=0
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  self.count+=1
  if self.count>1 or not allowed(newurl):raise PipelineError('Unexpected public-page redirect; no destination request made')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def http_transport():
 redirect=Redirect();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),redirect)
 request=urllib.request.Request(URL,headers={'User-Agent':'Social source-only official-page review','Accept':'text/html','Accept-Encoding':'identity'})
 with opener.open(request,timeout=30) as response:
  headers=dict(response.headers.items());data=response.read(LIMIT+1)
  return {'status':response.status,'final_url':response.url,'headers':headers,'body':data,'redirects':redirect.count}

def verify_cache(folder):
 folder=Path(folder);r=read_json(folder/'receipt.json')
 if r.get('schema')!='SOCIAL_PUBLIC_PAGE_RECEIPT_V1' or r.get('mode') not in {'fixture','live'} or r.get('request_url')!=URL:raise PipelineError('Invalid public input receipt')
 if r.get('state')!='received':raise PipelineError('Saved public input failed; no automatic HTTP repeat: '+str(r.get('error')))
 if not allowed(r.get('final_url','')) or r.get('status')!=200 or r.get('source_facts_confirmed') is not False:raise PipelineError('Public transport receipt is not approved factual evidence')
 for field,name in [('raw_sha256','page.raw'),('decoded_sha256','page.html')]:
  p=folder/name
  if not p.is_file() or p.stat().st_size>LIMIT or sha256_file(p)!=r[field]:raise PipelineError('Public receipt bytes missing/changed')
 if r['mode']=='fixture' and (r.get('http_observed') is not False or r.get('fetched_at') is not None):raise PipelineError('Fixture cannot impersonate live receipt')
 return r

def _acquire(folder,spec,cfg,transport=None,cancel=None):
 mode=validate(spec,cfg);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 if mode=='live' and transport is not None:raise PipelineError('Injected offline transport cannot attest live receipt; use explicit fixture mode')
 if cancel and Path(cancel).exists():raise PipelineError('Public preparation cancelled before cached or new source work')
 if (folder/'receipt.json').exists():
  r=verify_cache(folder)
  if r['mode']!=mode:raise PipelineError('Cached mode differs; no fixture/live substitution')
  return r
 if mode=='live' and os.environ.get('SOCIAL_PUBLIC_PAGE_OFFLINE_ONLY')=='1':raise PipelineError('Offline replay requires an existing verified receipt; new HTTP acquisition prohibited')
 # Durable intent precedes any request. Interrupted acquisition has an uncertain outcome;
 # never silently issue another GET on restart.
 intent=folder/'intent.json'
 if intent.exists():raise PipelineError('Previous public acquisition interrupted/uncertain; inspect receipt before authorizing another request')
 if cancel and Path(cancel).exists():raise PipelineError('Public preparation cancelled before source acquisition')
 write_json(intent,{'schema':'SOCIAL_PUBLIC_INPUT_INTENT_V1','mode':mode,'url':URL,'started_at':utc_now().isoformat()})
 receipt={'schema':'SOCIAL_PUBLIC_PAGE_RECEIPT_V1','mode':mode,'request_url':URL,'source_facts_confirmed':False,'http_observed':False,'fetched_at':None,'state':'failed'}
 try:
  if mode=='fixture':
   body=Path(spec['fixture_path']).read_bytes();response=transport() if transport else {'status':200,'final_url':URL,'headers':{'Content-Type':'text/html; charset=utf-8'},'body':body,'redirects':0}
  else:response=(transport or http_transport)()
  headers={k.lower():v for k,v in response['headers'].items()};body=response['body'];ctype=headers.get('content-type','')
  receipt.update(status=response['status'],final_url=response['final_url'],content_type=ctype,redirects=response.get('redirects',0),response_date=headers.get('date'),last_modified=headers.get('last-modified'))
  if response['status']!=200 or not allowed(response['final_url']) or response.get('redirects',0)>1 or ctype.split(';')[0].strip().lower()!='text/html' or not isinstance(body,bytes) or not 0<len(body)<=LIMIT:raise PipelineError('Unexpected status, URL, content type or page size')
  # Strict UTF8: do not silently replace bytes/characters or claim equivalent quotes.
  encoding='utf-8-sig' if body.startswith(b'\xef\xbb\xbf') else 'utf-8'
  text=body.decode(encoding);decoded=text.encode('utf-8')
  if len(decoded)>LIMIT:raise PipelineError('Decoded source exceeds budget')
  atomic_bytes(folder/'page.raw',body);atomic_bytes(folder/'page.html',decoded)
  receipt.update(state='received',encoding=encoding,raw_sha256=sha256_file(folder/'page.raw'),decoded_sha256=sha256_file(folder/'page.html'),bytes=len(body),http_observed=mode=='live',fetched_at=utc_now().isoformat() if mode=='live' else None)
  write_json(folder/'receipt.json',receipt)
  if cancel and Path(cancel).exists():raise PipelineError('Public preparation cancelled after receipt; source cached for offline recovery')
  return verify_cache(folder)
 except Exception as error:
  if receipt['state']!='received':
   receipt['status']=getattr(error,'code',receipt.get('status'));receipt['error']=type(error).__name__+': '+str(error)[:400];write_json(folder/'receipt.json',receipt)
  raise

def acquire(folder,spec,cfg,transport=None,cancel=None):
 from .motion_state import motion_lock
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 with motion_lock(folder,'fixed_public_input',wait=3):return _acquire(folder,spec,cfg,transport,cancel)

def clone_cache(parent,child):
 parent=Path(parent);child=Path(child)
 if not parent.exists():return
 child.mkdir(parents=True,exist_ok=True)
 for name in ['intent.json','receipt.json','page.raw','page.html']:
  p=parent/name;q=child/name
  if p.exists():
   if q.exists() and q.read_bytes()!=p.read_bytes():raise PipelineError('Retry source cache differs; preserved')
   if not q.exists():shutil.copyfile(p,q)

def record(folder,src_dir,audience):
 folder=Path(folder);r=verify_cache(folder);src_dir=Path(src_dir);src_dir.mkdir(parents=True,exist_ok=True)
 for name,target in [('page.raw','public_page.raw'),('page.html','public_page.html'),('receipt.json','public_page_receipt.json')]:shutil.copyfile(folder/name,src_dir/target)
 from .source_brief import adapt
 rec=adapt({'source_url':URL,'public_money_content':{'content':(folder/'page.html').read_bytes().decode('utf-8'),'content_type':'html','reconstructed':r['mode']=='fixture','fetched_at':r['fetched_at'],'snapshot_file':'source/public_page.html'}},audience=audience)
 snap={'file':'source/public_page.html','sha256':r['decoded_sha256'],'url':URL,'fetched_at':r['fetched_at'],'reconstructed':r['mode']=='fixture','raw_file':'source/public_page.raw','raw_sha256':r['raw_sha256'],'receipt_file':'source/public_page_receipt.json','receipt_sha256':sha256_file(folder/'receipt.json'),'not_http_observation':not r['http_observed'],'source_facts_confirmed':False}
 return rec,snap,r

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--job-folder',required=True);p.add_argument('--history',required=True);a=p.parse_args();folder=Path(a.job_folder)
 cfg=read_json(folder/'config.json');request=read_json(folder/'public_request.json');spec=request['public_source']
 try:
  acquire(folder/'public_input',spec,cfg,cancel=folder/'cancel')
  from .pipeline import run
  run(cfg,folder/'runs',history_path=Path(a.history),stop_after='script',public_input=folder/'public_input')
 except Exception as error:
  import traceback
  write_json(folder/'public_error.json',{'type':type(error).__name__,'detail':str(error)[:600],'new_request_on_retry':False,'source_facts_confirmed':False,'traceback':traceback.format_exc(limit=10)});return 2
 return 0
if __name__=='__main__':raise SystemExit(main())
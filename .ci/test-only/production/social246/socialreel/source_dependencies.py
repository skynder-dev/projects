"""Offline, hash-bound source dependency graph. Never fetches or executes sources."""
from pathlib import Path
import datetime as dt
from .common import read_json,sha256_file,sha256_bytes,PipelineError

def verify(directory,graph=None):
 root=Path(directory).resolve();g=read_json(root/'dependency_graph.json') if graph is None else graph
 if not isinstance(g,dict):raise PipelineError('Dependency graph must be an object')
 if g.get('schema')!='SOCIAL_SOURCE_DEPENDENCIES_V1':raise PipelineError('Unknown dependency graph')
 docs=g['documents'];conditions=g['conditions'];errors=[]
 if not isinstance(docs,dict) or not 1<=len(docs)<=64 or not isinstance(conditions,dict) or not 1<=len(conditions)<=256:raise PipelineError('Dependency graph exceeds bounded64documents/256conditions contract')
 for key,m in docs.items():
  from urllib.parse import urlsplit
  for value in [m['url'],m['final_url']]:
   u=urlsplit(value)
   if u.scheme!='https' or u.username or u.port not in (None,443) or not (u.hostname=='nsf.gov' or (u.hostname or '').endswith('.nsf.gov')):raise PipelineError('Dependency source outside official NSF HTTPS scope')
  for name,digest in [('file','sha256'),('text_file','text_sha256')]:
   p=(root/m[name]).resolve()
   if not p.is_relative_to(root):raise PipelineError('Dependency path outside owned source directory: '+key)
   actual=sha256_bytes(p.read_text(encoding='utf-8').encode()) if name=='text_file' and p.is_file() else (sha256_file(p) if p.is_file() else None)
   if not p.is_relative_to(root) or not p.is_file() or actual!=m[digest]:raise PipelineError('Dependency bytes changed or unsafe: '+key)
  from .source_documents import normalized_text
  if normalized_text((root/m['file']).read_bytes(),m)!= (root/m['text_file']).read_text(encoding='utf-8'):raise PipelineError('Dependency text does not derive from captured raw bytes: '+key)
 if not set(g['required_for_scope']).issubset(conditions):raise PipelineError('Required dependency condition missing')
 for key,c in conditions.items():
  if not isinstance(c,dict) or not isinstance(c.get('depends_on',[]),list) or len(c.get('depends_on',[]))>256 or any(not isinstance(dep,str) for dep in c.get('depends_on',[])):raise PipelineError('Dependency prerequisites must be a bounded list of condition keys')
  if c.get('state')!='known':errors.append(key+': '+c.get('reason','unresolved'));continue
  if not c.get('evidence'):errors.append(key+': evidence absent')
  for e in c.get('evidence',[]):
   m=docs[e['document']];text=(root/m['text_file']).read_text(encoding='utf-8')
   if text[e['start']:e['end']]!=e['quote'] or e['raw_sha256']!=m['sha256'] or e['text_sha256']!=m['text_sha256']:raise PipelineError('Dependency span differs: '+key)
  for dep in c.get('depends_on',[]):
   if dep not in conditions:errors.append(key+': missing prerequisite '+dep)
 colors={}
 def visit(key):
  if colors.get(key)==1:raise PipelineError('Dependency cycle')
  if colors.get(key)==2:return
  colors[key]=1
  for dep in conditions[key].get('depends_on',[]):
   if dep in conditions:visit(dep)
  colors[key]=2
 for key in conditions:visit(key)
 if g.get('individual_eligibility_assessed') is not False or g.get('future_submission_version_guaranteed') is not False:raise PipelineError('Dependency scope improperly promoted to applicant/future assurance')
 asof=dt.date.fromisoformat(g['as_of']);primary=docs['primary']
 if primary['sha256']!=g['primary_sha256']:raise PipelineError('Primary dependency binding mismatch')
 for key,c in conditions.items():
  date=c.get('effective_from')
  if date and dt.date.fromisoformat(date)>asof:errors.append(key+': future policy cannot be adopted as already effective')
 return {'schema':'SOCIAL_SOURCE_DEPENDENCY_CHECK_V1','integrity_pass':True,'overview_source_review_complete':not errors,'errors':errors,'conditions_verified':len(conditions),'documents_verified':len(docs),'individual_eligibility_assessed':False,'future_submission_version_guaranteed':False,'scope':'Snapshot-backed neutral program overview; not application certification or approval'}

def apply(record,report,directory):
 root=Path(directory)/'dependencies';p=root/'dependency_graph.json'
 if not p.is_file():return
 graph=read_json(p);check=verify(root,graph)
 if graph['primary_sha256']!=record['announcement_source']['sha256']:raise PipelineError('Dependencies belong to another primary source')
 record['source_dependencies']=graph;report['source_dependencies']=check
 record['track_conditions']['dependency_review']=check
 # Individual qualification is outside a neutral program summary's source-review gate.
 if check['overview_source_review_complete']:
  old=record['track_conditions']['unresolved_conditions']
  remaining=[x for x in old if not x.startswith(('Linked PAPPG/','NSF-Direct partner DCL'))]
  record['track_conditions']['unresolved_conditions']=remaining
  record['track_conditions']['scope']='Track facts plus verified linked-policy snapshot; no individual eligibility or future-version assurance'
  report['unresolved_conditions']=remaining;report['checked']=not remaining
  report['reason']=('; '.join(remaining) if remaining else None)
  report['review_level']='Primary track facts and applicable linked policy conditions needed for a neutral overview verified as of dependency snapshot; no applicant qualification, future-version guarantee or publication approval'
  record['source_conditions_unconfirmed']=bool(remaining)

def claims(graph):
 result=[];conditions=graph['conditions'];memo={}
 def supported(key,trail=()):
  if key in memo:return memo[key]
  if key in trail:return False
  c=conditions.get(key,{})
  ok=c.get('state')=='known' and bool(c.get('evidence')) and all(supported(dep,trail+(key,)) for dep in c.get('depends_on',[]))
  memo[key]=ok;return ok
 for key,c in conditions.items():
  if not supported(key) or not c.get('script_statement'):continue
  e=c['evidence'][0];m=graph['documents'][e['document']]
  result.append({'key':'dependency_'+key,'statement':c['script_statement'],'values':{'dependency_scope':c['scope']},'source':{'url':m['final_url'],'snapshot_file':'source/dependencies/'+m['file'],'snapshot_sha256':m['sha256'],'fields':['Verified linked policy; bounded overview scope'],'source_spans':c['evidence'],'normalized_text_sha256':m['text_sha256']}})
 return result

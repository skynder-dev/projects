"""Immutable collection snapshots and stable source identities. No candidate/owner writes."""
import json,re
from pathlib import Path
from urllib.parse import urlsplit
import commercial_review,source_context
def digest(m,value):return m.sha(json.dumps(value,sort_keys=True,ensure_ascii=False).encode())
def identity(m,row):
 p=urlsplit(row['url']);match=re.match(r'/questions/(\d+)(?:/|$)',p.path)
 stable='https://'+p.netloc.lower()+'/questions/'+match.group(1) if match and (p.hostname.endswith('.stackexchange.com') or p.hostname=='superuser.com') else commercial_review.canonical(row['url'])
 return m.sha(stable.encode())
def revision(m,row):
 packet=source_context.source_packet(row);keys=['title','observed_text','answer_text','source_kind','content_scope','answer_status','answer_count','accepted_answer_id','author_id','media_references','link_targets','answer_media_references']
 return digest(m,{k:packet.get(k) for k in keys})
def apply(m,index,rows,stamp,snapshot=None):
 for row in rows:
  id=identity(m,row);old=index['records'].get(id);at=row.get('observed_at') or stamp
  index['records'][id]={'observation_id':id,'url':row['url'],'source':row['source'],'author_id':row.get('author_id'),'first_seen':old['first_seen'] if old else at,'last_seen':at,'revision_hash':revision(m,row),'last_snapshot':snapshot or (old.get('last_snapshot') if old else None)}
def rebuild(m,root):
 index={'schema':'reveng-observation-history','records':{},'snapshots':[],'completed_rounds':0,'seed_inputs':[],'prepared_revisions':{},'warnings':[]}
 import analysis_jobs
 seeds=[]
 for p in (root/'analysis-inputs').glob('*.json'):
  try:
   id,_=analysis_jobs.inspect_input(m,root,p);data=json.loads(p.read_text(encoding='utf-8'));seeds.append((data.get('prepared_at',''),id,data))
  except (ValueError,KeyError,TypeError,OSError) as ex:index['warnings'].append({'input':p.name,'error':type(ex).__name__})
 for stamp,id,data in sorted(seeds):
  apply(m,index,data['observations'],stamp);index['seed_inputs'].append(id)
  for row in data['observations']:
   key=identity(m,row);index['prepared_revisions'].setdefault(key,[])
   rev=revision(m,row)
   if rev not in index['prepared_revisions'][key]:index['prepared_revisions'][key].append(rev)
 snapshots=[]
 for p in (root/'observation-snapshots').glob('*.json'):
  data=json.loads(p.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
  if claim!=digest(m,data) or p.stem!=claim:raise ValueError('Immutable observation snapshot integrity mismatch')
  snapshots.append((data['captured_at'],p.stem,data))
 for stamp,id,data in sorted(snapshots):
  apply(m,index,data['observations'],stamp,id);index['snapshots'].append(id);index['completed_rounds']=max(index['completed_rounds'],data['plan']['round']+1)
 return index
def load(m,root):
 # The index is derived, not authority: verify immutable inputs/snapshots on every load.
 # Replaying also recovers a snapshot written just before an interrupted index commit.
 return rebuild(m,Path(root))
def commit(m,root,run,index,rows,errors,plan,stats):
 root=Path(root);stamp=m.now();selected=[];counts={'new_to_history':0,'updated_existing':0,'unchanged_seen':0,'recovered_unprepared':0};recorded=[]
 for original in rows:
  row=dict(original);id=identity(m,row);old=index['records'].get(id);rev=revision(m,row);kind='new_to_history' if old is None else 'updated_existing' if old['revision_hash']!=rev else 'unchanged_seen';counts[kind]+=1
  if kind=='unchanged_seen' and rev not in index['prepared_revisions'].get(id,[]):counts['recovered_unprepared']+=1
  related=[v['url'] for key,v in index['records'].items() if key!=id and row.get('author_id') and v.get('author_id')==row['author_id'] and v.get('source')==row.get('source')]
  row.update(observation_id=id,source_revision_hash=rev,novelty=kind,first_observed_at=old['first_seen'] if old else row.get('observed_at',stamp),prior_same_author_urls=related[:12],prior_same_author_count=len(related));recorded.append(row)
 payload={'schema':'reveng-observation-snapshot','captured_at':stamp,'plan':plan,'observations':recorded,'source_errors':errors,'stats':dict(stats),'delta':counts,'meaning':'New to this local corpus is not an independent buyer, new publication, demand or representative sample. Cached observed_at is not refreshed artificially.'};id=digest(m,payload);folder=root/'observation-snapshots';folder.mkdir(exist_ok=True);path=folder/(id+'.json')
 if not path.exists():m.dump(path,dict(payload,integrity_sha256=id))
 apply(m,index,recorded,stamp,id);index['snapshots']=list(dict.fromkeys(index['snapshots']+[id]));index['completed_rounds']=max(index['completed_rounds'],plan['round']+1);index['updated_at']=stamp
 m.dump(root/'observation-index.json',dict(index,integrity_sha256=digest(m,index)))
 for row in recorded:
  prepared=row['source_revision_hash'] in index['prepared_revisions'].get(row['observation_id'],[])
  if row['novelty']=='unchanged_seen' and prepared:continue
  row=dict(row,observation_snapshot_id=id,evidence_id='E'+str(len(selected)+1));selected.append(row)
 source_context.annotate_relations(selected)
 summary=dict(counts,snapshot_id=id,snapshot_file='observation-snapshots/'+id+'.json',captured_records=len(recorded),selected_for_analysis=len(selected),history_records=len(index['records']),failed_sources=len(errors),history_warnings=index.get('warnings',[]),plan=plan)
 m.dump(run/'discovery-summary.json',summary);return selected,summary

"""Evidence-backed old processed repair, READ-ONLY plan and non-runnable copy only."""
import copy,json,re,sqlite3
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_bytes,sha256_file,stable_json,atomic_bytes

def digest(value):return sha256_bytes(stable_json(value).encode())
def plan(history,evidence_paths):
    from .pipeline import family
    from .source_responses import search_payload
    if not isinstance(evidence_paths,(list,tuple)) or not 1<=len(evidence_paths)<=100:raise PipelineError('Repair needs1..100explicit owned evidence paths')
    history=Path(history).resolve();root=history.parent;cursor=history.with_name(history.stem+'_discovery.json')
    inputs={};input_bytes=0;protected_ids=set();protected_families=set();notes=[]
    def bound(path):
        nonlocal input_bytes
        path=Path(path).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size>8*1024*1024:raise PipelineError('Repair input missing/outside owned bounded source scope')
        if path.relative_to(root).as_posix() not in inputs:
            input_bytes+=path.stat().st_size
            if input_bytes>64*1024*1024:raise PipelineError('Repair input/copy budget exceeds64MiB; split evidence review')
        inputs[path.relative_to(root).as_posix()]=sha256_file(path)
        if len(inputs)>1000:raise PipelineError('Repair exceeds1000bounded inputs')
        return read_json(path)
    def protect(rows):
        if not isinstance(rows,list):raise PipelineError('Repair history list invalid; no assumption of unused material')
        for row in rows:
            if not isinstance(row,dict) or not row.get('opportunity_id') or not isinstance(row.get('title'),str) or not row['title'].strip():raise PipelineError('Incomplete protected material history; review before repair')
            protected_ids.add(str(row['opportunity_id']));protected_families.add(family(row['title']))
    protect(bound(history).get('runs'))
    reserved=history.with_name(history.stem+'_prepared.json')
    if reserved.exists():protect(bound(reserved).get('runs'))
    markers=list(root.glob('*/runs/*/prepared.json'))+list(root.glob('*/runs/*/package_manifest.json'))+list(root.glob('prepared_*/prepared.json'))
    if len(markers)>1000:raise PipelineError('Too many owned material markers; repair held')
    for marker in markers:
        manifest=bound(marker);topic=bound(marker.parent/'topic.json').get('selected')
        if not isinstance(manifest,dict) or not isinstance(topic,dict):raise PipelineError('Owned material marker unreadable; repair held')
        protect([topic]) # Protect even an unapproved/uncertain publication marker.
    db=root/'queue.sqlite3'
    if db.exists():
        wal=Path(str(db)+'-wal')
        if wal.exists() and wal.stat().st_size:raise PipelineError('Queue has active WAL; take a consistent offline copy before planning repair')
        input_bytes+=db.stat().st_size
        if input_bytes>64*1024*1024:raise PipelineError('Repair input/copy budget exceeds64MiB')
        inputs[db.name]=sha256_file(db)
        try:
            with sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True) as conn:rows=list(conn.execute('SELECT state,run_dir FROM jobs'))
        except sqlite3.Error as error:raise PipelineError('Queue index unavailable; no protected-material guess') from error
        for state,run in rows:
            if state in {'prepared','completed','review_required'}:
                if not run:raise PipelineError('Durable material has no owned location; repair held')
                directory=Path(run);directory=(directory if directory.is_absolute() else root/directory).resolve()
                if not directory.is_relative_to(root):raise PipelineError('Material index points outside owned scope; repair held')
                protect([bound(directory/'topic.json').get('selected')])
    old=bound(cursor);new=copy.deepcopy(old)
    if old.get('schema')!='SOCIAL_DISCOVERY_CURSOR_V1' or not isinstance(old.get('queries'),dict):raise PipelineError('Cursor schema unknown; no repair')
    eligible={}
    for path in evidence_paths:
        report=bound(path)
        if report.get('schema')!='SOCIAL_DISCOVERY_COVERAGE_V1':raise PipelineError('Repair evidence is not original discovery coverage')
        for row in report.get('excluded_or_deferred',[]):
            reason=row.get('excluded');why=row.get('reasons',[])
            if reason=='listing_deadline_policy' or reason=='detailed_selection_policy' and len(why)==1 and isinstance(why[0],str) and why[0].startswith('closes in '):eligible.setdefault(str(row.get('opportunity_id')),[]).append(str(Path(path).resolve().relative_to(root)))
    pages={}
    for path in sorted((root/'discovery_snapshots').glob('*')):
        if not path.is_file() or not re.fullmatch('[0-9a-f]{64}',path.name):continue
        if sha256_file(path)!=path.name:raise PipelineError('Repair source-cache hash conflict; no recovery')
        try:envelope=bound(path)
        except (ValueError,UnicodeError):notes.append({'source_sha256':path.name,'state':'unreadable_cache_not_used'});continue
        data=envelope.get('data') if isinstance(envelope,dict) else None
        if not isinstance(data,dict) or not isinstance(data.get('oppHits'),list):continue
        start=data.get('startRecord',0);hits,paging=search_payload(envelope,max(1,len(data['oppHits'])),start)
        for hit in hits:
            pages.setdefault(str(hit['id']),[]).append((hit,path.name,path.stat().st_size,paging,start))
    changes=[]
    for stream_id,stream in new['queries'].items():
        pending={str(item['hit'].get('id')) for item in stream['pending']}
        for oid in list(dict.fromkeys(stream['processed'])):
            oid=str(oid);candidates=pages.get(oid,[])
            if oid in protected_ids:notes.append({'id':oid,'state':'protected_material'});continue
            if oid in pending:notes.append({'id':oid,'state':'already_pending'});continue
            if oid not in eligible:notes.append({'id':oid,'state':'ambiguous_old_reason_not_restored'});continue
            if not candidates or any(c[0]!=candidates[0][0] for c in candidates):notes.append({'id':oid,'state':'missing_or_conflicting_raw_hit'});continue
            hit,sha,size,paging,start=candidates[0]
            if paging is None:notes.append({'id':oid,'state':'search_pagination_unconfirmed'});continue
            if family(hit.get('title','')) in protected_families:notes.append({'id':oid,'state':'protected_topic_family'});continue
            meta={'file':'source/recovered_search_'+sha[:16]+'.json','sha256':sha,'bytes':size,'url':'https://api.grants.gov/v1/api/search2','fetched_at':None,'observation_mode':'offline_processed_repair','live_currentness_proved':False,'pagination':paging,'original_query_unknown':True}
            stream['pending'].append({'hit':copy.deepcopy(hit),'snapshot':meta,'recovery_origin':{'policy_evidence':eligible[oid],'raw_search_sha256':sha,'current_source_confirmed':False}})
            stream['processed']=[v for v in stream['processed'] if str(v)!=oid];pending.add(oid);changes.append({'stream_id':stream_id,'id':oid,'title':hit.get('title'),'evidence':eligible[oid],'source_sha256':sha})
    from .discovery_cursor import verify_cursor,seal_cursor
    verify_cursor(old);seal_cursor(new)
    result={'schema':'SOCIAL_DISCOVERY_REPAIR_PLAN_V1','source_root':str(root),'history':history.name,'evidence_paths':[str(Path(p).resolve().relative_to(root)) for p in evidence_paths],'cursor':cursor.name,'input_hashes':inputs,'before_cursor_sha256':inputs[cursor.name],'after_cursor':new,'after_cursor_sha256':digest(new),'changes':changes,'held':notes,'protected_ids':sorted(protected_ids),'protected_families':sorted(protected_families),'input_bytes':input_bytes,'copy_only':True,'publication_authorized':False,'current_source_confirmed':False}
    result['plan_id']=digest(result);return result

def materialize_copy(value,destination):
    original=copy.deepcopy(value);key=original.pop('plan_id',None)
    if digest(original)!=key or value.get('copy_only') is not True:raise PipelineError('Repair plan identity invalid')
    root=Path(value['source_root']).resolve();target=Path(destination).resolve()
    if not isinstance(value.get('cursor'),str) or Path(value['cursor']).name!=value['cursor'] or ':' in value['cursor'] or '\\' in value['cursor']:raise PipelineError('Repair cursor locator invalid')
    if any(not isinstance(rel,str) or Path(rel).is_absolute() or '..' in Path(rel).parts or ':' in rel or rel.startswith(('\\','/')) for rel in value['input_hashes']):raise PipelineError('Repair input locator escaped relative scope')
    if target==root or target.is_relative_to(root) or root.is_relative_to(target):raise PipelineError('Repair writes only a separate review copy; live/source root is forbidden')
    marker=target/'MIGRATION_REVIEW_ONLY.json';journal=target/'repair_commit.json';cursor=target/value['cursor']
    expected={'schema':'SOCIAL_NONRUNNABLE_REPAIR_COPY_V1','plan_id':key,'source_root':str(root),'destination':str(target),'non_runnable_review_only':True}
    committed={'plan_id':key,'before':value['before_cursor_sha256'],'after':value['after_cursor_sha256'],'state':'committed','no_publication_or_worker':True}
    if journal.exists():
        try:saved_commit=read_json(journal)
        except (OSError,ValueError) as error:raise PipelineError('Repair commit journal unreadable; preserved') from error
        if saved_commit in [committed,{**committed,'state':'prepared'}] and cursor.is_file() and sha256_file(cursor)==value['after_cursor_sha256']:
            if not marker.exists() or read_json(marker)!=expected or not cursor.is_file() or sha256_file(cursor)!=value['after_cursor_sha256'] or sha256_file(target/'cursor_before_repair.json')!=value['before_cursor_sha256']:raise PipelineError('Committed review copy changed; no replacement')
            for rel,sha in value['input_hashes'].items():
                p=(target/rel).resolve()
                if not p.is_relative_to(target) or not p.is_file() or sha256_file(p)!=(value['after_cursor_sha256'] if rel==value['cursor'] else sha):raise PipelineError('Committed review-copy evidence changed; no replacement')
            if saved_commit['state']=='prepared':write_json(journal,committed)
            return {'plan_id':key,'state':'committed_on_review_copy_only','destination':str(target),'cursor_sha256':value['after_cursor_sha256'],'restored_ids':[r['id'] for r in value['changes']],'protected_materials_not_reissued':True,'source_currentness_confirmed':False,'worker_started':False,'publication_authorized':False}
    for rel,sha in value['input_hashes'].items():
        path=(root/rel).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256_file(path)!=sha:raise PipelineError('Repair source/evidence changed since plan; no copy commit')
    if plan(root/value['history'],[root/rel for rel in value['evidence_paths']])['plan_id']!=key:raise PipelineError('Protected-material index changed since plan; no repair commit')
    if not value['changes']:raise PipelineError('No unambiguously recoverable processed topics')
    marker=target/'MIGRATION_REVIEW_ONLY.json'
    if target.exists() and not marker.exists():raise PipelineError('Destination already exists without this copy identity; preserved')
    expected={'schema':'SOCIAL_NONRUNNABLE_REPAIR_COPY_V1','plan_id':key,'source_root':str(root),'destination':str(target),'non_runnable_review_only':True}
    if marker.exists():
        if read_json(marker)!=expected:raise PipelineError('Another repair copy owns destination')
    else:write_json(marker,expected)
    cursor=target/value['cursor'];after=stable_json(value['after_cursor']).encode();before=(root/value['cursor']).read_bytes()
    for rel,sha in value['input_hashes'].items():
        dest=(target/rel).resolve()
        if not dest.is_relative_to(target):raise PipelineError('Repair copy path escaped destination')
        if rel==value['cursor'] and dest.exists() and sha256_file(dest)==value['after_cursor_sha256']:continue
        if dest.exists():
            if sha256_file(dest)!=sha:raise PipelineError('Repair copy contains conflicting bytes; preserved')
        else:atomic_bytes(dest,(root/rel).read_bytes())
    backup=target/'cursor_before_repair.json'
    if backup.exists() and backup.read_bytes()!=before:raise PipelineError('Repair backup conflict')
    if not backup.exists():atomic_bytes(backup,before)
    journal=target/'repair_commit.json';record={'plan_id':key,'before':value['before_cursor_sha256'],'after':value['after_cursor_sha256'],'state':'prepared','no_publication_or_worker':True}
    if journal.exists():
        saved=read_json(journal)
        if saved not in [record,{**record,'state':'committed'}]:raise PipelineError('Repair commit journal changed; preserved without overwrite')
    current=sha256_file(cursor)
    if current not in {record['before'],record['after']}:raise PipelineError('Copy cursor changed; no overwrite')
    if plan(root/value['history'],[root/rel for rel in value['evidence_paths']])['plan_id']!=key:raise PipelineError('Source/protected material changed during copy; commit held')
    if current==record['before']:write_json(journal,record);atomic_bytes(cursor,after)
    record['state']='committed';write_json(journal,record)
    return {'plan_id':key,'state':'committed_on_review_copy_only','destination':str(target),'cursor_sha256':sha256_file(cursor),'restored_ids':[r['id'] for r in value['changes']],'protected_materials_not_reissued':True,'source_currentness_confirmed':False,'worker_started':False,'publication_authorized':False}

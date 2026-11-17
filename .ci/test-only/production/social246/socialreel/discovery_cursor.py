"""Bounded, durable continuation of the existing Grants.gov search connector."""
from pathlib import Path
import json,datetime as dt,time,re
from .common import PipelineError,read_json,write_json,sha256_bytes,sha256_file,atomic_bytes,parse_date,utc_now,stable_json
from .motion_state import motion_lock
from .discovery_transactions import fetch as transaction_fetch,DiscoveryTransactionError,operation_id

def cursor_digest(state):return sha256_bytes(stable_json({k:v for k,v in state.items() if k!='cursor_sha256'}).encode())
def verify_cursor(state):
    if not isinstance(state,dict):raise DiscoveryTransactionError('Discovery cursor shape invalid; preserved')
    if 'cursor_sha256' in state and state['cursor_sha256']!=cursor_digest(state):raise DiscoveryTransactionError('Discovery cursor content changed; preserved, no source request')
def seal_cursor(state):
    state['cursor_sha256']=cursor_digest(state);return state

def discover(cfg,directory,today,seen,forced,history):
    from . import grants
    from .pipeline import family,score_record,assess_audience,candidate_facets
    from .editorial import ranking_evidence
    directory=Path(directory);history=Path(history);sc=cfg['search'];queries=list(dict.fromkeys(sc['keywords']+([''] if sc.get('catalog_sample') else [])))
    identity=sha256_bytes(json.dumps({'queries':queries,'rows':sc['rows'],'statuses':sc.get('statuses','posted')},sort_keys=True).encode())
    path=history.with_name(history.stem+'_discovery.json');cache=path.parent/'discovery_snapshots';cache.mkdir(exist_ok=True,parents=True)
    audience=cfg.get('selection',{}).get('audience','general_us')
    started=time.monotonic();client=grants.GrantsGovClient(directory,timeout=8,history_path=history);recs=[];considered=[];notes=[];details=0;searches=0;encountered=set();found=0
    with motion_lock(path.parent,'discovery_cursor_'+sha256_bytes(str(path.resolve()).casefold().encode())[:16],wait=5):
        state=read_json(path) if path.exists() else {'schema':'SOCIAL_DISCOVERY_CURSOR_V1','queries':{}}
        verify_cursor(state)
        if state.get('schema')!='SOCIAL_DISCOVERY_CURSOR_V1':raise PipelineError('Unknown discovery cursor; original preserved')
        is_new=identity not in state['queries']
        stream=state['queries'].setdefault(identity,{'pages':{q:{'next':0,'done':False} for q in queries},'pending':[],'processed':[]})
        from .discovery_renewal import begin,age
        renewal,renewed=begin(stream,queries,sc,utc_now(),is_new)
        def save():write_json(path,seal_cursor(state))
        def reserve(kind,request,url,name,generation):
            key=operation_id(kind,request,url,name,generation);operations=stream.setdefault('receipt_operations',{})
            existing=key in operations
            if not existing:operations[key]={'kind':kind,'state':'reserved'}
            save();return key,not existing
        def snapshot(meta):
            if not isinstance(meta,dict) or not isinstance(meta.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',meta['sha256']):raise PipelineError('Discovery snapshot identity invalid; cursor preserved')
            src=cache/meta['sha256'];target=directory/Path(meta['file']).name
            if not src.is_file() or sha256_file(src)!=meta['sha256']:raise PipelineError('Discovery snapshot unavailable or changed; cursor preserved')
            atomic_bytes(target,src.read_bytes())
        def ingest():
            nonlocal searches,found
            if stream.get('host_retry_after') and utc_now()<dt.datetime.fromisoformat(stream['host_retry_after']):
                notes.append({'deferred':'official_api_dns_backoff','retry_after':stream['host_retry_after']});return False
            for q in queries:
                page=stream['pages'][q]
                if page['done']:continue
                if page.get('retry_after') and utc_now()<dt.datetime.fromisoformat(page['retry_after']):
                    notes.append({'query':q,'deferred':'search_transport_backoff','retry_after':page['retry_after']});continue
                if searches>=int(sc.get('max_search_requests',3)):return False
                offset=page['next'];searches+=1
                body={'rows':int(sc['rows']),'oppStatuses':sc.get('statuses','posted'),'startRecordNum':offset}
                if q:body['keyword']=q
                name='search_'+grants._safe(q or 'all')+'_'+sha256_bytes(json.dumps(body,sort_keys=True).encode())[:12]+'.json'
                op,allow_new=reserve('search',body,grants.SEARCH_URL,name,renewal['generation'])
                try:hits,meta=transaction_fetch(path.parent,identity,directory,client,'search',body,grants.SEARCH_URL,name,renewal['generation'],lambda:client.search(q,int(sc['rows']),sc.get('statuses','posted'),start=offset),allow_new=allow_new)
                except DiscoveryTransactionError:raise
                except PipelineError as error:
                    page['retry_after']=(utc_now()+dt.timedelta(minutes=10)).isoformat()
                    if getattr(error,'host_unavailable',False):stream['host_retry_after']=page['retry_after']
                    save();notes.append({'query':q,'deferred':'search_transport_error','reason':str(error)[:300]})
                    if getattr(error,'host_unavailable',False):return False
                    continue
                paging=meta.get('pagination') or {}
                if paging.get('start')!=offset or type(paging.get('total')) is not int:raise PipelineError('Search pagination metadata missing or inconsistent; offset preserved')
                atomic_bytes(cache/meta['sha256'],(directory/Path(meta['file']).name).read_bytes());found+=len(hits)
                existing={str(p['hit'].get('id')) for p in stream['pending']}|set(stream['processed'])
                for hit in hits:
                    oid=str(hit.get('id') or '')
                    previous=next((p for p in stream['pending'] if str(p['hit'].get('id'))==oid),None)
                    if previous is not None:
                        if previous['hit']!=hit:
                            old=previous.pop('detail_snapshot',None)
                            if old:previous['superseded_detail_snapshots']=(previous.get('superseded_detail_snapshots',[])+[old])[-4:]
                            previous.pop('retry_after',None)
                        previous.update(hit=hit,snapshot=meta);encountered.discard(oid)
                    if oid.isascii() and oid.isdigit() and oid not in existing:
                        stream['pending'].append({'hit':hit,'snapshot':meta});existing.add(oid)
                stream['receipt_operations'][op]['state']='received'
                page.update(next=offset+len(hits),done=not hits or offset+len(hits)>=paging['total'],reported_total=paging['total'])
                save();return True
            return False
        if renewed:
            save()
            if int(sc.get('max_search_requests',3))>0 and int(sc['max_detail_fetch'])>0:ingest()
        while details<int(sc['max_detail_fetch']) and len(recs)<int(sc['max_detail_fetch']):
            if time.monotonic()-started>=30:
                notes.append({'deferred':'discovery_time_budget','seconds':30});break
            def available_items():return sorted([p for p in stream['pending'] if str(p['hit'].get('id')) not in encountered],key=lambda p:((p.get('considered_counts') or {}).get(audience,0),not bool(p.get('detail_snapshot'))))
            available=available_items()
            # Previously considered but unsupported candidates must not pin the
            # cursor to page one forever. Keep them, rotate, and allow new pages.
            if available and all((p.get('considered_counts') or {}).get(audience,0)>0 for p in available) and searches<int(sc.get('max_search_requests',3)) and any(not p['done'] for p in stream['pages'].values()):
                if ingest():available=available_items()
            if not available:
                if stream['pending'] and all(p.get('retry_after') and utc_now()<dt.datetime.fromisoformat(p['retry_after']) for p in stream['pending']):break
                if searches>=int(sc.get('max_search_requests',3)) or not ingest():break
                available=available_items()
                if not available:continue
            item=available[0];hit=item['hit'];oid=str(hit.get('id') or '')
            # A mutable cursor hit must still be the exact hit in its hashed raw page
            # BEFORE date/family exclusions can discard the opportunity.
            snapshot(item['snapshot'])
            from .source_responses import search_payload
            meta=item['snapshot'];raw_search=read_json(directory/Path(meta['file']).name)
            start=(meta.get('request') or {}).get('startRecordNum',(meta.get('pagination') or {}).get('start',0))
            saved_hits,_=search_payload(raw_search,int(sc['rows']),start)
            bound=[h for h in saved_hits if str(h.get('id'))==oid]
            if len(bound)!=1 or bound[0]!=hit:raise PipelineError('Pending discovery hit differs from its saved search snapshot; cursor preserved without selection/exclusion')
            encountered.add(oid)
            listed_age=age(meta,utc_now())
            if listed_age is None or listed_age>=dt.timedelta(days=renewal['policy']['catalog_renewal_days']):
                item['renewal_review_required']='listing_time_unconfirmed' if listed_age is None else 'listing_expired_waiting_scan'
                notes.append({'opportunity_id':oid,'deferred':item['renewal_review_required']});save();continue
            item.pop('renewal_review_required',None)
            if not forced and (oid in seen or family(hit.get('title','')) in seen):reason='existing_history'
            elif forced and oid!=str(forced):reason='not_requested_identifier'
            else:
                close=parse_date(hit.get('closeDate'));reason='listing_deadline_policy' if not close or (close-today).days<int(cfg['selection']['min_days_left']) else None
            if reason=='listing_deadline_policy':
                # This is a caller's remaining-days policy, not permanent absence.
                counts=item.setdefault('considered_counts',{});counts[audience]=counts.get(audience,0)+1
                item['selection_policy_deferral']={'as_of':today.isoformat(),'min_days_left':int(cfg['selection']['min_days_left']),'listed_close_date':hit.get('closeDate')}
                notes.append({'opportunity_id':oid,'deferred':reason,'policy':item['selection_policy_deferral']});save();continue
            if reason:
                if reason=='existing_history':
                    notes.append({'opportunity_id':oid,'excluded':reason});stream['pending'].remove(item);stream['processed'].append(oid);stream.setdefault('processed_provenance',{})[oid]='existing_history'
                else:notes.append({'opportunity_id':oid,'deferred':reason})
                save();continue
            retry=item.get('retry_after')
            if retry and utc_now()<dt.datetime.fromisoformat(retry):notes.append({'opportunity_id':oid,'deferred':'transport_backoff','retry_after':retry});continue
            if not item.get('detail_snapshot') and stream.get('host_retry_after') and utc_now()<dt.datetime.fromisoformat(stream['host_retry_after']):
                item['retry_after']=stream['host_retry_after'];save();notes.append({'opportunity_id':oid,'deferred':'official_api_dns_backoff','retry_after':item['retry_after']});continue
            cached_age=age(item['detail_snapshot'],utc_now()) if item.get('detail_snapshot') else None
            if item.get('detail_snapshot') and cached_age is None:
                item['renewal_review_required']='detail_time_unconfirmed';notes.append({'opportunity_id':oid,'deferred':'detail_time_unconfirmed'});save();continue
            using_cached=bool(item.get('detail_snapshot') and sc.get('refresh_cached_details') is not True and cached_age<dt.timedelta(days=renewal['policy']['detail_cache_max_age_days']))
            try:
                if using_cached:
                    meta=item['detail_snapshot'];snapshot(meta);detail=(read_json(directory/Path(meta['file']).name).get('data') or {})
                    if hasattr(client,'replay_detail'):detail,meta=client.replay_detail(oid,meta)
                else:
                    details+=1
                    generation=item.get('detail_generation',0)
                    op,allow_new=reserve('detail',{'opportunityId':int(oid)},grants.DETAIL_URL,'opportunity_'+oid+'.json',generation)
                    detail,meta=transaction_fetch(path.parent,identity,directory,client,'detail',{'opportunityId':int(oid)},grants.DETAIL_URL,'opportunity_'+oid+'.json',generation,lambda:client.detail(oid),allow_new=allow_new)
                    stream['receipt_operations'][op]['state']='received'
                    item['detail_snapshot']=meta;item['detail_generation']=generation+1;save()
            except DiscoveryTransactionError:raise
            except PipelineError as error:
                if using_cached:
                    old=item.pop('detail_snapshot',None)
                    if old:item['unusable_detail_snapshots']=(item.get('unusable_detail_snapshots',[])+[old])[-4:]
                item['retry_after']=(utc_now()+dt.timedelta(minutes=10)).isoformat()
                if getattr(error,'host_unavailable',False):stream['host_retry_after']=item['retry_after']
                save();notes.append({'opportunity_id':oid,'deferred':'detail_transport_error','reason':str(error)[:300]});continue
            from .source_responses import detail_record
            try:detail_record(detail,oid)
            except PipelineError as error:
                old=item.pop('detail_snapshot',None)
                if old:item['unusable_detail_snapshots']=(item.get('unusable_detail_snapshots',[])+[old])[-4:]
                item['retry_after']=(utc_now()+dt.timedelta(minutes=10)).isoformat();save();notes.append({'opportunity_id':oid,'deferred':'detail_response_incomplete','reason':str(error)[:300]});continue
            receipt_age=age(meta,utc_now())
            if receipt_age is None or receipt_age>=dt.timedelta(days=renewal['policy']['detail_cache_max_age_days']):
                item['renewal_review_required']='detail_receipt_expired_or_time_unconfirmed';notes.append({'opportunity_id':oid,'deferred':item['renewal_review_required']});save();continue
            record=grants.normalize(hit,detail);record['_selection_min_days']=int(cfg['selection']['min_days_left']);record['audience_assessment']=assess_audience(record);record['selection_assessment']=candidate_facets(record,today,sc['keywords'],int(cfg['selection']['min_days_left']))
            record['_field_sources']={k:(item['snapshot'] if field.startswith('hit.') else meta) for k,field in record['fields'].items()}
            score,why=score_record(record,today,int(cfg['selection']['min_days_left']));rank=ranking_evidence(record,score,why,meta,audience=cfg.get('selection',{}).get('audience','general_us'),as_of=today);record['ranking_evidence']=rank
            counts=item.setdefault('considered_counts',{});counts[audience]=counts.get(audience,0)+1;save()
            recs.append((rank['score'],record,meta));considered.append({'opportunity_id':oid,'title':record['title'],'score':rank['score'],'why':why,'ranking':rank,'facets':record['selection_assessment']})
            if rank['score']<=-99:
                closing=parse_date(record.get('close_date'));opening=parse_date(record.get('open_date'))
                local_date_policy=closing is not None and (closing-today).days<int(cfg['selection']['min_days_left']) and (record.get('status') or '').lower()=='posted' and (record.get('doc_type') or '').lower()!='forecast' and (opening is None or opening<=today)
                if local_date_policy:
                    item['selection_policy_deferral']={'stage':'detailed','as_of':today.isoformat(),'min_days_left':int(cfg['selection']['min_days_left']),'detailed_close_date':record.get('close_date')}
                    notes.append({'opportunity_id':oid,'deferred':'detailed_deadline_policy','reasons':why,'policy':item['selection_policy_deferral']})
                else:
                    notes.append({'opportunity_id':oid,'deferred':'detailed_selection_policy','reasons':why});item['selection_policy_deferral']={'stage':'detailed','as_of':today.isoformat(),'reasons':why}
                save()
        save()
        coverage={'renewal':renewal,'legacy_processed_review_required':[str(i) for i in stream['processed'] if str(i) not in stream.get('processed_provenance',{})],'schema':'SOCIAL_DISCOVERY_COVERAGE_V1','search_requests':searches,'detail_requests':details,'wire_attempts':len(client.attempts)-getattr(client,'initial_attempt_count',0) if hasattr(client,'attempts') else None,'wire_attempts_in_saved_source':len(client.attempts) if hasattr(client,'attempts') else None,'wire_attempt_accounting':'durable one-attempt connector; journal recovery is not HTTP' if hasattr(client,'attempts') else 'injected fixture transport has no wire evidence','soft_time_budget_s':30,'request_timeout_s':8,'elapsed_s':round(time.monotonic()-started,3),'search_budget':int(sc.get('max_search_requests',3)),'detail_budget':int(sc['max_detail_fetch']),'pages':stream['pages'],'pending_hits':len(stream['pending']),'excluded_or_deferred':notes,'catalog_exhausted':all(p['done'] for p in stream['pages'].values()) and not stream['pending'],'queue_policy':'Audience-scoped consideration counts rotate retained candidates; new-page progress within existing budgets','scope':'Bounded configured-topic search only; not proof of no topics, demand or viewer eligibility'}
        write_json(directory/'discovery_coverage.json',coverage)
    return recs,considered,client.calls,found

def acknowledge(cfg,history,opportunity_ids):
    """Only selected or explicitly source-rejected records leave the candidate queue."""
    sc=cfg['search'];queries=list(dict.fromkeys(sc['keywords']+([''] if sc.get('catalog_sample') else [])))
    identity=sha256_bytes(json.dumps({'queries':queries,'rows':sc['rows'],'statuses':sc.get('statuses','posted')},sort_keys=True).encode());history=Path(history);path=history.with_name(history.stem+'_discovery.json')
    with motion_lock(path.parent,'discovery_cursor_'+sha256_bytes(str(path.resolve()).casefold().encode())[:16],wait=5):
        state=read_json(path);verify_cursor(state);stream=state['queries'][identity];ids={str(i) for i in opportunity_ids}
        stream.setdefault('processed_provenance',{}).update({i:'explicit_acknowledgment' for i in ids});stream['pending']=[p for p in stream['pending'] if str(p['hit'].get('id')) not in ids];stream['processed']=list(dict.fromkeys(stream['processed']+list(ids)));write_json(path,seal_cursor(state))

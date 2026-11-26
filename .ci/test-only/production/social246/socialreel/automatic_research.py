"""Finite personal-information fallback at the existing source-only research boundary."""
import datetime as dt,json,ssl,time,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from .common import PipelineError,write_json,read_json,atomic_bytes,sha256_file,utc_now,check_cancel
from .public_money import URLS,parse,unclaimed_record,energy_record,wages_record

CATALOG=(('energy','USA-GOV-ENERGY-BILLS'),('wages','DOL-WORKERS-OWED-WAGES'),('unclaimed','USA-GOV-UNCLAIMED-MONEY'))
CATALOG_VERSION='general_us_information_v1'
MAX_AGE_SECONDS=86400

def allowed(url,kind=None):
    if not isinstance(url,str):return False
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.query or p.fragment or '\\' in url or any(ord(c)<32 for c in url):return False
        return any(url.rstrip('/')==URLS[k].rstrip('/') for k,_ in CATALOG if kind is None or k==kind)
    except ValueError:return False

def eligible(cfg,stop_after,forced=None):
    return stop_after=='script' and cfg.get('writer')=='template' and cfg.get('selection',{}).get('audience','general_us')=='general_us' and forced is None and cfg.get('search',{}).get('public_reference_fallback',True) is True

def http_page(kind):
    """One bounded GET with at most one same-source redirect, no retries/login."""
    url=URLS[kind]
    class Redirect(urllib.request.HTTPRedirectHandler):
        count=0
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            self.count+=1
            if self.count>1 or not allowed(newurl,kind):raise PipelineError('Official reference redirect outside fixed source; stopped')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    try:
        import truststore
        context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:context=ssl.create_default_context()
    redirect=Redirect();opener=urllib.request.build_opener(redirect,urllib.request.HTTPSHandler(context=context))
    with opener.open(urllib.request.Request(url,headers={'User-Agent':'SocialReels/1.0 bounded automatic public-reference research','Accept':'text/html','Accept-Encoding':'identity'}),timeout=10) as r:
        body=r.read(2*1024*1024+1)
        return {'status':r.status,'final_url':r.url,'headers':dict(r.headers.items()),'body':body,'redirects':redirect.count}

class ReferencePersistenceError(PipelineError):
    """Owned storage failure; must not be reclassified as another source's absence."""

class ReferenceSourceUnavailable(PipelineError):
    """Bounded source transport failure; may defer to an independent catalog source."""

def acquire(kind,folder,transport=None):
    try:return _acquire(kind,folder,transport)
    except OSError as error:raise ReferencePersistenceError('Official-reference storage failed; no alternate source attempted: '+str(error)[:250]) from error

def _acquire(kind,folder,transport=None):
    """Durable intent prevents uncertain response-loss retries. Cache is byte-verified."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);receipt_path=folder/'receipt.json'
    if receipt_path.exists():
        receipt=read_json(receipt_path)
        if receipt.get('state')!='received':
            error=PipelineError('Previous reference acquisition failed/uncertain; no automatic repeat in this job');error.code=receipt.get('http_error_status');raise error
    else:
        intent=folder/'intent.json'
        if intent.exists():raise PipelineError('Previous reference request uncertain; no automatic repeat in this job')
        check_cancel();write_json(intent,{'kind':kind,'url':URLS[kind],'started_at':utc_now().isoformat(),'automatic':True})
        receipt={'schema':'SOCIAL_PUBLIC_PAGE_RECEIPT_V1','source_catalog':CATALOG_VERSION,'source_kind':kind,'state':'failed','mode':'fixture' if transport is not None else 'live','request_url':URLS[kind],'source_facts_confirmed':False,'http_observed':transport is None,'fetched_at':None}
        try:
            try:response=(transport or http_page)(kind)
            except (OSError,PipelineError) as error:
                unavailable=ReferenceSourceUnavailable(type(error).__name__+': '+str(error));unavailable.code=getattr(error,'code',None);raise unavailable from error
            headers={k.lower():v for k,v in response['headers'].items()};body=response['body'];ctype=headers.get('content-type','')
            if response['status']!=200 or not allowed(response['final_url'],kind) or response.get('redirects',0)>1 or ctype.split(';')[0].strip().lower()!='text/html' or not isinstance(body,bytes) or not 0<len(body)<=2*1024*1024:raise PipelineError('Reference status/URL/MIME/size mismatch')
            encoding='utf-8-sig' if body.startswith(b'\xef\xbb\xbf') else 'utf-8';decoded=body.decode(encoding).encode('utf-8')
            atomic_bytes(folder/'page.raw',body);atomic_bytes(folder/'page.html',decoded)
            receipt.update(state='received',status=response['status'],final_url=response['final_url'],content_type=ctype,redirects=response.get('redirects',0),encoding=encoding,raw_sha256=sha256_file(folder/'page.raw'),decoded_sha256=sha256_file(folder/'page.html'),last_modified=headers.get('last-modified'),fetched_at=utc_now().isoformat() if transport is None else None)
            write_json(receipt_path,receipt)
        except Exception as e:
            receipt.update(error=type(e).__name__+': '+str(e)[:250],http_error_status=getattr(e,'code',None));write_json(receipt_path,receipt);raise
    if receipt.get('source_catalog')!=CATALOG_VERSION or receipt.get('source_kind')!=kind or receipt.get('request_url')!=URLS[kind] or not allowed(receipt.get('final_url'),kind) or receipt.get('status')!=200 or receipt.get('source_facts_confirmed') is not False:raise PipelineError('Reference cache identity invalid')
    for name,key in [('page.raw','raw_sha256'),('page.html','decoded_sha256')]:
        p=folder/name
        if not p.is_file() or not 0<p.stat().st_size<=2*1024*1024 or sha256_file(p)!=receipt.get(key):raise PipelineError('Reference cache bytes changed')
    if receipt.get('mode')=='live':
        try:stamp=dt.datetime.fromisoformat(receipt['fetched_at']);age=(utc_now()-stamp).total_seconds()
        except (ValueError,TypeError,KeyError):raise PipelineError('Reference observation time invalid')
        if receipt.get('http_observed') is not True or not -300<=age<=MAX_AGE_SECONDS:raise PipelineError('Reference observation stale/future; not reused as current material')
    elif receipt.get('mode')!='fixture' or receipt.get('http_observed') is not False or receipt.get('fetched_at') is not None:raise PipelineError('Reference fixture cannot claim live observation')
    if receipt.get('encoding') not in {'utf-8','utf-8-sig'} or (folder/'page.raw').read_bytes().decode(receipt['encoding']).encode('utf-8')!=(folder/'page.html').read_bytes():raise PipelineError('Reference cache decoding mismatch')
    check_cancel();return receipt

def fallback(cfg,directory,seen,trigger,transport=None,history_path=None):
    directory=Path(directory);started=time.monotonic();rows=[];blocked_hosts=set()
    report={'schema':'SOCIAL_AUTOMATIC_REFERENCE_SELECTION_V1','catalog':CATALOG_VERSION,'trigger':trigger,'audience':'general_us','order':[k for k,_ in CATALOG],'entries':rows,'not_new_grant_or_personal_eligibility':True,'max_source_attempts':3,'max_total_seconds':45,'selected':None,'source_facts_approved':False}
    def save():
        try:write_json(directory/'automatic_reference_selection.json',report)
        except OSError as error:raise ReferencePersistenceError('Reference selection report could not be persisted; no source substitution') from error
    from .pipeline import family
    for kind,identity in CATALOG:
        check_cancel()
        if identity in seen:
            rows.append({'kind':kind,'opportunity_id':identity,'state':'duplicate','reason':'Topic ID already used/reserved; no source request'});continue
        if urlsplit(URLS[kind]).hostname in blocked_hosts:
            rows.append({'kind':kind,'opportunity_id':identity,'state':'unconfirmed','reason':'Official host returned authentication/rate restriction earlier in this pass; no retry or alternate route'});continue
        if time.monotonic()-started>=45:
            rows.append({'kind':kind,'state':'budget_exhausted'});break
        folder=directory/'automatic_references'/kind
        try:
            receipt=acquire(kind,folder,transport=transport);content=(folder/'page.html').read_bytes().decode('utf-8')
            parsed=parse(content,URLS[kind],reconstructed=receipt['mode']=='fixture',fetched_at=receipt.get('fetched_at'),snapshot_file='source/automatic_references/'+kind+'/page.html')
            record={'energy':energy_record,'wages':wages_record,'unclaimed':unclaimed_record}[kind](parsed)
            if record['opportunity_id']!=identity:raise PipelineError('Catalog/parser topic identity differs')
            if family(record['title']) in seen:
                rows.append({'kind':kind,'opportunity_id':identity,'state':'duplicate','reason':'Topic family already used/reserved; no repeated draft'});continue
            # Run actual existing audience/writer checks BEFORE selecting; one broken
            # source/format cannot starve the rest of this finite catalog.
            from .claims import build_claims
            from .writer import write_script
            from .audience_selection import require
            require(record,'general_us');write_script(record,build_claims(record,{},utc_now().date()),{'writer':'template','selection':{'audience':'general_us'}})
            record['public_money_content']={'content':content,'content_type':'html','reconstructed':receipt['mode']=='fixture','fetched_at':receipt.get('fetched_at'),'snapshot_file':'source/automatic_references/'+kind+'/page.html'}
            record['_automatic_reference']=True
            snap={'url':URLS[kind],'file':'source/automatic_references/'+kind+'/page.html','sha256':receipt['decoded_sha256'],'raw_file':'source/automatic_references/'+kind+'/page.raw','raw_sha256':receipt['raw_sha256'],'receipt_file':'source/automatic_references/'+kind+'/receipt.json','receipt_sha256':sha256_file(folder/'receipt.json'),'fetched_at':receipt.get('fetched_at'),'source_updated':parsed.get('source_updated'),'reconstructed':receipt['mode']=='fixture','not_http_observation':receipt['mode']!='live','source_facts_confirmed':False}
            reason='First unseen source in fixed catalog with bounded authentic/reconstructed receipt, supported source semantics, general_us fit and valid deterministic short draft; not personal qualification'
            row={'kind':kind,'opportunity_id':identity,'state':'selected','reason':reason,'money_type':record['editorial_brief']['money_benefit']['kind'],'fetched_at':receipt.get('fetched_at'),'source_url':URLS[kind]};rows.append(row);report['selected']=row;save()
            record['automatic_research_reason']=reason
            return 10,record,snap,{'checked':False,'reason':'Automatic official information snapshot; personal/local eligibility and factual/currentness acceptance remain required','automatic_reference_selection':report,'source':snap}
        except ReferencePersistenceError:raise
        except (PipelineError,ValueError,KeyError,TypeError) as e:
            if getattr(e,'code',None) in {401,403,429}:blocked_hosts.add(urlsplit(URLS[kind]).hostname)
            rows.append({'kind':kind,'opportunity_id':identity,'state':'unconfirmed','reason':type(e).__name__+': '+str(e)[:250]});save()
    if history_path is not None:
        from .reference_cycle import recheck
        renewed,cycle=recheck(cfg,directory,history_path,seen,transport=transport)
        report['reference_recheck']=cycle
        if renewed:
            record=renewed[1];kind=record['public_money_source']['kind']
            row={'kind':kind,'opportunity_id':record['opportunity_id'],'state':'selected','reason':record['automatic_research_reason'],'money_type':record['editorial_brief']['money_benefit']['kind'],'fetched_at':renewed[2].get('fetched_at'),'source_url':record['source_url'],'not_new_program':True}
            rows[:]=[row if r.get('kind')==kind else r for r in rows];report['selected']=row;report['status']='reference_material_revision_selected';save();renewed[3]['automatic_reference_selection']=report;return renewed
        report['status']='reference_recheck_not_due' if cycle['status']=='no_due_reference_check' else 'reference_recheck_no_new_material';save()
    else:
        report['status']='no_unseen_supported_reference' if rows and all(r['state']=='duplicate' for r in rows) else 'reference_sources_unconfirmed_or_exhausted';save()
    raise PipelineError('No unseen supported general_us reference or verified material revision in this bounded pass; see saved automatic selection/recheck and next due dates. Not proof no opportunities exist')

def select(cfg,directory,today,seen,forced,history_path,stop_after):
    """Only explicit no-result outcomes may activate fallback; IO/sync failures stop."""
    from .pipeline import discover_live
    from .announcements import select_source_candidate,SourceSelectionExhausted
    can_fallback=eligible(cfg,stop_after,forced);rejected=[];selected=None
    # Discovery owns source transport/cursor distinctions. An unexpected exception
    # is not evidence of semantic exhaustion and must not change the source route.
    recs,considered,calls,hits=discover_live(cfg,directory,today,seen,forced,history_path=history_path)
    good=sorted([r for r in recs if r[0]>-99],key=lambda r:(-r[0],str(r[1]['opportunity_id'])))
    if good:
        try:selected=select_source_candidate(good,directory,audience=cfg.get('selection',{}).get('audience','general_us'))
        except SourceSelectionExhausted as error:
            trigger={'kind':'grants_no_suitable_result','detail':str(error)[:350],'grants_evidence_preserved':True}
            diagnostic=directory/'publisher_rejections.json'
            if diagnostic.exists():rejected=read_json(diagnostic).get('rejected',[])
        else:rejected=selected[4]
    else:
        write_json(directory/'audience_selection.json',{'status':'no_candidates_in_bounded_pass','audience':cfg.get('selection',{}).get('audience','general_us'),'deferred':[],'format_deferred':[],'source_deferred':[],'global_opportunity_absence_established':False})
        trigger={'kind':'grants_no_suitable_result','detail':'No selectable Grants.gov candidate in this bounded pass; not a personal eligibility decision','grants_evidence_preserved':True}
    # This transaction is deliberately outside semantic/source exception handling.
    if cfg['search'].get('pagination') is True and not forced:
        from .discovery_cursor import acknowledge
        if selected:
            sync_record={'schema':'SOCIAL_SOURCE_SELECTION_SYNC_V1','state':'pending_cursor_sync','selected_opportunity_id':selected[1].get('opportunity_id'),'selected_title':selected[1].get('title'),'selected_snapshot':selected[2],'source_evidence_preserved':True,'fallback_attempted':False,'prepared_or_production_approved':False}
            write_json(directory/'selected_source_sync.json',sync_record)
        try:acknowledge(cfg,history_path,[r['opportunity_id'] for r in rejected])
        except (PipelineError,OSError) as error:
            identity=selected[1].get('opportunity_id') if selected else None
            raise PipelineError('Grants.gov cursor synchronization failed after selection/review; selected opportunity='+str(identity)+'; no public-reference fallback attempted. Source evidence preserved; retry only after synchronization is healthy. '+str(error)[:200]) from error
    if selected:
        if cfg['search'].get('pagination') is True and not forced:write_json(directory/'selected_source_sync.json',{**sync_record,'state':'cursor_synced'})
        score,record,snapshot,review,rejected=selected
        return score,record,snapshot,review,rejected,considered,calls,hits
    check_cancel()
    if not can_fallback:raise SourceSelectionExhausted(trigger['detail'])
    score,record,snapshot,review=fallback(cfg,directory,seen,trigger,history_path=history_path)
    return score,record,snapshot,review,rejected,considered,calls,hits

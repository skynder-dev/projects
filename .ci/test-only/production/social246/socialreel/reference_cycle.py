"""Refresh observations on demand; only supported factual changes earn a revised draft."""
import datetime as dt,hashlib,json,re
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl
from .common import PipelineError,read_json,write_json,utc_now
from .public_money import Page,parse,energy_record,wages_record,unclaimed_record,URLS
from .preparation import verify_preparation

INTERVAL=dt.timedelta(days=7)
BACKOFF=dt.timedelta(days=1)
SCHEMA='SOCIAL_REFERENCE_CYCLE_V1'
# Exact row wording attested by saved official223 receipt; additions to a row
# remain unclassified instead of becoming known just because its category matches.
KNOWN_ROW_TEXT={'unpaid wages': 'Unpaid wages – Search the Department of Labor’s database for back pay an employer might owe you.', 'pensions': 'Pensions from former employers – Use the Pension Benefit Guaranty Corporation (PBGC) search tool to find an unclaimed pension.', 'FHA insurance refunds': 'FHA insurance refunds – If you had a mortgage insured by the Federal Housing Administration (FHA), search the HUD database to see if you are eligible for a refund.', 'bank failures': 'Bank failures – Search the FDIC database for unclaimed funds from closed financial institutions.', 'savings bonds': 'Savings bonds Use TreasuryHunt.gov to find matured savings bonds that have stopped earning interest. You can also learn how to replace a lost or destroyed savings bond .'}
IDENTITIES={'energy':'USA-GOV-ENERGY-BILLS','wages':'DOL-WORKERS-OWED-WAGES','unclaimed':'USA-GOV-UNCLAIMED-MONEY'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def stamp(value):
    result=dt.datetime.fromisoformat(value)
    if result.tzinfo is None:raise ValueError('Reference cycle requires timezone')
    return result

def material(record):
    """Whitelist typed values and real routes; no HTML/mtime/title/version novelty."""
    p=record.get('public_money_source') or {};kind=p.get('kind')
    if kind not in URLS or record.get('source_url')!=URLS[kind] or record.get('opportunity_id')!=IDENTITIES[kind]:raise PipelineError('Reference material source/topic identity unknown')
    fields={k:v['value'] for k,v in p.get('fields',{}).items()}
    routes=[];query_context=[]
    for row in p.get('databases',[]):
        urls=[]
        for link in row.get('links',[]):
            u=urlsplit(link['url'])
            if u.scheme!='https' or u.username or u.password or u.port not in (None,443):raise PipelineError('Unsafe reference route')
            # Query/fragment/tracking changes cannot manufacture a new story.
            urls.append(u.scheme+'://'+u.hostname.lower()+u.path.rstrip('/'))
            unknown=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid','msclkid'}]
            if unknown:query_context.append({'route':urls[-1],'unclassified_query':sorted(unknown)})
        routes.append({'category':row['category'],'agency':row['agency'],'routes':sorted(set(urls))})
    projection={'kind':kind,'fields':fields,'routes':sorted(routes,key=lambda r:r['category']),'money_type':record['editorial_brief']['money_benefit'],'unknowns':p.get('unknown',[])}
    content=(record.get('public_money_content') or {}).get('content')
    context=None;unclassified=None
    if isinstance(content,str):
        page=Page();page.feed(content);text=page.text
        if kind=='energy':
            start=text.find('Find out if you are eligible for LIHEAP and apply');end=text.find('Find out if you are eligible for WAP and apply',start+1)
        elif kind=='wages':start=0;end=text.find('Search Employer')
        else:start=text.find('Find unclaimed funds held by the government that might be owed to you.');end=text.find('LAST UPDATED',start+1)
        if start>=0 and end>start:
            scoped=text[start:end];residual=scoped
            known=[v.get('source',{}).get('quote','') for v in p.get('fields',{}).values()]+[r.get('source',{}).get('quote','') for r in p.get('databases',[]) if re.findall(r'\w+',r.get('source',{}).get('quote','').casefold())==re.findall(r'\w+',KNOWN_ROW_TEXT.get(r.get('category'),'').casefold())]
            for quote in sorted(set(known),key=len,reverse=True):
                if quote:residual=residual.replace(quote,' ')
            unclassified=digest({'residual_tokens':re.findall(r'\w+',residual.casefold()),'route_queries':sorted(query_context,key=lambda q:q['route'])})
            context=digest({'text_tokens':re.findall(r'\w+',scoped.casefold()),'unclassified_route_queries':sorted(query_context,key=lambda q:q['route'])})
    return {'material_sha256':digest(projection),'projection':projection,'context_sha256':context,'unclassified_sha256':unclassified,'raw_sha256':p.get('content_sha256'),'source_observed_at':p.get('fetched_at')}

def latest(history,records):
    scope=Path(history).parent.resolve();result={}
    for row in records:
        value=row.get('directory')
        if not isinstance(value,str):continue
        root=Path(value).resolve()
        if not root.is_relative_to(scope):continue
        manifest=verify_preparation(root);record=read_json(root/'topic.json')['selected']
        if not record.get('public_money_source'):continue
        kind=record['public_money_source'].get('kind')
        if kind not in URLS:continue
        basis={**material(record),'prepared_at':manifest['prepared_at'],'preparation_id':manifest['preparation_id'],'directory':str(root)}
        if kind not in result or stamp(basis['prepared_at'])>stamp(result[kind]['prepared_at']):result[kind]=basis
    return result

def state_path(history):
    h=Path(history);return h.with_name(h.stem+'_reference_checks.json')

def change_status(old,current):
    if current['context_sha256'] is None or old['context_sha256'] is None:return 'context_basis_unconfirmed'
    if current.get('unclassified_sha256')!=old.get('unclassified_sha256'):return 'source_text_changed_needs_review'
    if current['material_sha256']==old['material_sha256']:
        return 'source_text_changed_needs_review' if old['context_sha256'] and current['context_sha256']!=old['context_sha256'] else 'no_material_change'
    if current['raw_sha256']==old['raw_sha256']:return 'local_projection_drift_not_source_novelty'
    if current['context_sha256']==old['context_sha256']:return 'route_or_projection_change_without_context_novelty'
    return 'supported_material_revision'

def state(history):
    path=state_path(history)
    try:
        data=read_json(path) if path.exists() else {'schema':SCHEMA,'topics':{}}
        if not isinstance(data,dict) or data.get('schema')!=SCHEMA or not isinstance(data.get('topics'),dict) or not set(data['topics'])<=set(URLS):raise ValueError('Unknown cycle schema')
        for row in data['topics'].values():
            if not isinstance(row,dict):raise ValueError('Cycle entry malformed')
            stamp(row['next_due_at'])
        return data
    except (OSError,ValueError,TypeError,KeyError) as e:raise PipelineError('Reference recheck state unreadable; no new HTTP or novelty inferred') from e

def commit(history,kind,row):
    from .motion_state import motion_lock
    path=state_path(history)
    with motion_lock(path.parent,'reference_cycle_'+digest(str(path.resolve()))[:16],wait=5):
        data=state(history);data['topics'][kind]=row;write_json(path,data)

def recheck(cfg,directory,history,seen,transport=None):
    """One oldest due consumed source per ordinary source-only job, no timers."""
    from .automatic_research import CATALOG,acquire,ReferencePersistenceError,ReferenceSourceUnavailable
    from .preparation_history import load_reservations
    directory=Path(directory);clock=utc_now();report={'schema':SCHEMA,'checked_at':clock.isoformat(),'cadence_days':7,'automatic_scheduler_created':False,'max_seen_sources_per_job':1,'entries':[],'new_program':False,'selected':None}
    if history is None:
        report['status']='verified_history_required';write_json(directory/'reference_recheck.json',report);return None,report
    reservations=load_reservations(history,directory.parent.parent)
    if reservations.get('problems'):raise PipelineError('Published reference history incomplete; cannot determine material novelty')
    bases=latest(history,reservations['runs']);ledger=state(history);due=[]
    for order,(kind,identity) in enumerate(CATALOG):
        if identity not in seen:continue
        old=bases.get(kind)
        if not old:
            report['entries'].append({'kind':kind,'state':'baseline_unconfirmed','reason':'Used topic has no verified owned preparation basis; do not invent newness'});continue
        checkpoint=ledger['topics'].get(kind)
        try:when=stamp(checkpoint['next_due_at']) if checkpoint else stamp(old.get('source_observed_at') or old['prepared_at'])+INTERVAL
        except (ValueError,TypeError):
            report['entries'].append({'kind':kind,'state':'baseline_time_unconfirmed','reason':'Old source observation time unconfirmed; no freshness or novelty inferred'});continue
        report['entries'].append({'kind':kind,'state':'not_due' if when>clock else 'due','next_due_at':when.isoformat(),'last_prepared_material_sha256':old['material_sha256']})
        if when<=clock:due.append((when,order,kind,old))
    if not due:
        report['status']='no_due_reference_check';write_json(directory/'reference_recheck.json',report);return None,report
    _,_,kind,old=min(due);folder=directory/'automatic_references'/kind
    result=None;revision=None
    # Only source/parse issues defer; persistence and sync errors propagate.
    try:
        receipt=acquire(kind,folder,transport=transport);content=(folder/'page.html').read_bytes().decode('utf-8')
        parsed=parse(content,URLS[kind],reconstructed=receipt['mode']=='fixture',fetched_at=receipt.get('fetched_at'),snapshot_file='source/automatic_references/'+kind+'/page.html')
        record={'energy':energy_record,'wages':wages_record,'unclaimed':unclaimed_record}[kind](parsed)
        record['public_money_content']={'content':content,'content_type':'html','reconstructed':receipt['mode']=='fixture','fetched_at':receipt.get('fetched_at'),'snapshot_file':'source/automatic_references/'+kind+'/page.html'}
        current=material(record)
        status=change_status(old,current)
        if status=='supported_material_revision':
            from .writer import write_script
            from .claims import build_claims
            write_script(record,build_claims(record,{},clock.date()),{'writer':'template','selection':{'audience':'general_us'}})
            changed=[k for k in current['projection'] if current['projection'][k]!=old['projection'][k]]
            revision={'schema':'SOCIAL_REFERENCE_MATERIAL_REVISION_V1','kind':kind,'previous_material_sha256':old['material_sha256'],'material_sha256':current['material_sha256'],'previous_preparation_id':old['preparation_id'],'changed_projection_fields':changed,'not_new_program':True,'observed_at':receipt.get('fetched_at'),'observation_kind':receipt['mode']}
            record['reference_revision']=revision;record['_automatic_reference']=True;record['automatic_research_reason']='Supported official-source material changed since the latest verified draft; revision of the same information topic, not a new program or personal entitlement'
            from .common import sha256_file
            snap={'url':URLS[kind],'file':'source/automatic_references/'+kind+'/page.html','sha256':receipt['decoded_sha256'],'raw_file':'source/automatic_references/'+kind+'/page.raw','raw_sha256':receipt['raw_sha256'],'receipt_file':'source/automatic_references/'+kind+'/receipt.json','receipt_sha256':sha256_file(folder/'receipt.json'),'fetched_at':receipt.get('fetched_at'),'source_updated':parsed.get('source_updated'),'reconstructed':receipt['mode']=='fixture','not_http_observation':receipt['mode']!='live','source_facts_confirmed':False}
            result=(10,record,snap,{'checked':False,'reason':'Supported same-topic material revision; full/personal eligibility and production acceptance remain unconfirmed','source':snap});status='supported_material_revision'
    except ReferencePersistenceError:raise
    except (PipelineError,ValueError,KeyError,TypeError) as e:status='source_unconfirmed';report['error']=type(e).__name__+': '+str(e)[:250]
    next_due=clock+(INTERVAL if status=='no_material_change' else BACKOFF)
    # This is a check ledger, not a publication ledger. Latest verified draft is
    # always recovered independently; a check never consumes a material version.
    row={'checked_at':clock.isoformat(),'next_due_at':next_due.isoformat(),'status':status,'last_prepared_material_sha256':old['material_sha256'],'source_conditions_approved':False}
    commit(history,kind,row);report.update(status=status,rechecked_kind=kind,next_due_at=next_due.isoformat(),selected=revision)
    write_json(directory/'reference_recheck.json',report)
    if result:result[3]['reference_recheck']=report
    return result,report

def allow_revision(temporary,history,records):
    """Called under existing publication lock; recompute, never trust a version flag."""
    root=Path(temporary);verify_preparation(root);record=read_json(root/'topic.json')['selected'];revision=record.get('reference_revision')
    if not isinstance(revision,dict) or revision.get('schema')!='SOCIAL_REFERENCE_MATERIAL_REVISION_V1' or revision.get('not_new_program') is not True:return False
    new=material(record)
    if revision.get('kind')!=new['projection']['kind']:return False
    old=latest(history,records).get(revision.get('kind'))
    if not old or change_status(old,new)!='supported_material_revision':return False
    if revision.get('previous_material_sha256')!=old['material_sha256'] or revision.get('material_sha256')!=new['material_sha256'] or revision.get('previous_preparation_id')!=old['preparation_id']:return False
    if revision.get('changed_projection_fields')!=[k for k in new['projection'] if new['projection'][k]!=old['projection'][k]]:return False
    from .source_quality import inspect_observation
    return inspect_observation(root,record).get('state') in {'verified_http_receipt','verified_fixture_receipt'}

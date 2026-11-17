"""On-demand bounded renewal; missing legacy provenance is a review state."""
import datetime as dt
from .common import PipelineError

def policy(search):
    result={k:search.get(k,7) for k in ('catalog_renewal_days','detail_cache_max_age_days')}
    if any(type(v) is not int or not 1<=v<=30 for v in result.values()):raise PipelineError('Discovery renewal/cache days must be integers1..30')
    return result

def age(meta,clock):
    try:
        stamp=dt.datetime.fromisoformat(meta['fetched_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None or (clock-stamp).total_seconds() < -300:return None
        return clock-stamp
    except (KeyError,ValueError,TypeError,AttributeError):return None

def begin(stream,queries,search,clock,is_new):
    p=policy(search);row=stream.get('renewal')
    if row is None:
        row={'schema':'SOCIAL_DISCOVERY_RENEWAL_V1','generation':0,'started_at':clock.isoformat() if is_new else None,'state':'active' if is_new else 'legacy_review_required'};stream['renewal']=row
    if not isinstance(row,dict) or row.get('schema')!='SOCIAL_DISCOVERY_RENEWAL_V1' or type(row.get('generation')) is not int or row['generation']<0:raise PipelineError('Renewal state identity invalid; review required')
    row['policy']=p
    elapsed=age({'fetched_at':row.get('started_at')},clock)
    if elapsed is None:
        row['state']='legacy_review_required';return row,False
    due=elapsed>=dt.timedelta(days=p['catalog_renewal_days'])
    if due and all(page['done'] for page in stream['pages'].values()):
        row.update(generation=row['generation']+1,started_at=clock.isoformat(),state='active')
        stream['pages']={q:{'next':0,'done':False} for q in queries}
        return row,True
    row['state']='due_after_current_scan' if due else 'active'
    return row,False

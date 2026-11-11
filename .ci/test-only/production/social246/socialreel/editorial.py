"""Source-backed editorial aids, not a trend or applicant eligibility classifier."""
import copy
import datetime as dt
from .common import PipelineError, parse_date


def ranking_evidence(rec, base_score, reasons, snapshot, audience=None, as_of=None):
    from .audience_selection import assess
    from .claims import purpose_excerpt
    import re
    audience=audience or rec.get('_selection_audience','general_us');fit=assess(rec,audience)
    facets=rec.get('selection_assessment') or {};matched=facets.get('topic_match',{}).get('matched_keywords',[])
    purpose=purpose_excerpt(rec.get('description') or '',title=rec.get('title',''))
    brief=rec.get('editorial_brief') or {};typed=rec.get('primary_conditions') or {}
    concrete=brief.get('concrete_use') if fit['suitable'] else None
    if not concrete and fit['suitable'] and (typed.get('conditions') or {}).get('purpose'):
        evidence=typed['conditions']['purpose'].get('evidence') or [];concrete=evidence[0].get('quote') if evidence else None
    digest=(snapshot or {}).get('sha256');identified=isinstance(digest,str) and bool(re.fullmatch('[0-9a-f]{64}',digest))
    parts={'identified_snapshot':2 if identified else 0,'source_url':1 if rec.get('source_url') else 0,'configured_topic_evidence':min(3,len(matched))*2,'reviewed_audience_fit':6 if fit['suitable'] else 0,'reviewed_concrete_use':3 if concrete else 0,'exact_purpose_excerpt':2 if purpose else 0}
    info=rec.get('public_money_source') or {}
    if info:parts['information_scope_priority']={'unclaimed':3,'energy':2,'wages':1}.get(info.get('kind'),0)
    freshness={'state':'not_assessed','snapshot_age_days':None,'publication_novelty':'not_established'}
    if as_of is not None:
        try:
            day=as_of.date() if isinstance(as_of,dt.datetime) else as_of;observed=dt.datetime.fromisoformat((snapshot or {}).get('fetched_at') or info['fetched_at']);age=(day-observed.date()).days
            freshness.update(state='future_timestamp' if age<0 else 'same_day_observation' if age==0 else 'older_saved_observation',snapshot_age_days=age)
        except (KeyError,TypeError,ValueError):freshness['state']='observation_date_unknown'
    return {'schema':'SOCIAL_EDITORIAL_RANKING_V2','score':sum(parts.values()) if base_score>-99 else -99,'components':parts,'legacy_completeness_score_not_ranked':base_score,'reasons':list(reasons),'matched_topics':matched,'topic_evidence':facets.get('topic_match',{}).get('evidence',[]),'audience_fit':fit,'concrete_use':concrete,'purpose_excerpt':purpose,'source':{'url':rec.get('source_url'),'snapshot':snapshot},'freshness':freshness,'novelty':{'history_deduplication':'separate upstream ID/family gate','public_newness':'not_established','trends_or_virality_measured':False},'limits':['Editorial rule only; no predicted engagement or virality','Identified snapshot is not verified fact/currentness','Audience gate and current source review still required','Description length and applicant-category breadth are not useful-benefit proof'],'rule':'Reviewed audience fit and concrete use, exact source purpose, configured-topic evidence; no award magnitude, category breadth or prose-length bonus','information_priority_basis':'Existing explicit local directory/household/case policy; not measured popularity' if info else None}


def production_gate(rec, snapshot, now, min_days=1, max_age_hours=24):
    """Recheck time-sensitive conditions immediately before expensive work."""
    errors=[]
    if rec.get('public_money_source'):
        info=rec['public_money_source']
        if info.get('live_verified') is not True:errors.append('Actual official-page ingest has not been accepted; supplied/reconstructed content remains draft-only')
        if info.get('reconstructed'):errors.append('Reconstructed content is not an authentic response snapshot')
        try:
            observed=dt.datetime.fromisoformat(info['fetched_at'])
            if observed.tzinfo is None or not -300<=(now-observed).total_seconds()<=max_age_hours*3600:errors.append('Official-page fetch time is stale/unconfirmed')
        except (ValueError,KeyError,TypeError):errors.append('No actual official-page fetched_at timestamp')
        return {'pass':not errors,'errors':errors,'checked_at':now.isoformat(),'scope':'Public information page; no invented application deadline, balance or local program opening'}
    if (rec.get('status') or '').lower() != 'posted':errors.append('Listing is not posted')
    close=parse_date(rec.get('close_date'))
    if close is None or (close-now.date()).days < min_days:errors.append('Listing has insufficient remaining application time')
    if rec.get('application_schedule') and rec.get('budget_scope'):
        from .nih_document import assess
        try:
            policy=assess({**rec['application_schedule'],'budget':rec['budget_scope']},rec,today=now.date(),min_days=min_days)
            if not policy['pass']:errors.append(policy['reason'])
        except (ValueError,KeyError,TypeError):errors.append('NIH application-type deadline policy cannot be established')
    opening=parse_date(rec.get('open_date'))
    if opening and opening > now.date():errors.append('Listing is not open yet')
    try:
        fetched=dt.datetime.fromisoformat(snapshot['fetched_at'])
        if fetched.tzinfo is None:raise ValueError('timezone required')
        age=(now-fetched).total_seconds()
        if age < -300 or age > max_age_hours*3600:errors.append('Source observation is stale or in the future')
    except (ValueError,KeyError,TypeError):errors.append('Cannot establish source observation time')
    for label,step in (rec.get('submission_steps') or {}).items():
        day=parse_date(step.get('date'))
        # On a deadline day without resolved UTC clock, block conservatively.
        if day is None or day <= now.date():errors.append('Submission stage expired or requires same-day clock review: '+label)
    return {'pass':not errors,'checked_at':now.isoformat(),'errors':errors,
            'max_age_hours':max_age_hours,'min_days_left':min_days,
            'scope':'Stored official observation and deadlines; no assertion of unchanged live listing'}


def require_gate(rec, snapshot, now, min_days):
    report=production_gate(rec,snapshot,now,min_days)
    if not report['pass']:raise PipelineError('Production source gate: '+'; '.join(report['errors']))
    return report


def storyboard(script, claims, rec):
    """Attach deterministic data glyphs; every value references its claim."""
    if script.get('editorial_contract') in {'SOCIAL_BENEFIT_REEL_V1','SOCIAL_SOURCE_DECISION_REEL_V1'}:
        from .scene_coherence import board
        return copy.deepcopy(script),board(script,claims)
    script=copy.deepcopy(script)
    by={c['key']:c for c in claims}
    scenes=[]
    for seg in script['segments']:
        diagram=None
        if seg['role']=='money' and not rec.get('primary_conditions'):
            total=(by.get('total_funding') or {}).get('values',{}).get('estimated_total_program_funding')
            amount=(by.get('award_range') or by.get('award_ceiling') or {}).get('values',{}).get('award_ceiling')
            if total and amount and 0<amount<=total:
                diagram={'kind':'funding_comparison','total':total,'award_ceiling':amount,
                         'claim_keys':['total_funding','award_range' if 'award_range' in by else 'award_ceiling'],
                         'note':'Estimated program budget compared with ceiling of one award; not a promised payout'}
        if seg['role'] in ('when','deadline') and rec.get('submission_steps'):
            diagram={'kind':'submission_stages','steps':[{'label':label,**value} for label,value in rec['submission_steps'].items()],
                     'claim_keys':[k for k in seg['claim_keys'] if k in by],'note':'Official application stages, not estimated processing time'}
        if diagram:seg['data_diagram']=diagram
        scenes.append({'id':seg['id'],'role':seg['role'],'visual':seg['visual'],
                       'diagram':diagram,'claim_keys':seg['claim_keys'],
                       'sources':[by[k]['source'] for k in seg['claim_keys'] if k in by]})
    return script,{'format':'source-backed motion infographics','photorealistic':False,'b_roll':False,
                   'scenes':scenes,'limits':'No photographic footage, presenter or trend proof'}

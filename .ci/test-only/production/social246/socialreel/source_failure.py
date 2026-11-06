"""Expose bounded owned source-selection blockers without reopening sources."""
from pathlib import Path
from .common import read_json,sha256_file

def _publisher_blockers(folder,job):
    folder=Path(folder).resolve();progress=job.get('progress')
    if progress is None:progress={}
    if not isinstance(progress,dict):return [{'kind':'source_evidence_unavailable','reason':'Saved progress is malformed; source outcome unknown','scope':'Not proof of no errors/topics or eligibility'}]
    value=progress.get('run_dir')
    if value is None or value=='':return []
    if not isinstance(value,str):return [{'kind':'source_evidence_unavailable','reason':'Saved source path has wrong type; outcome unknown'}]
    if any(ord(c)<32 for c in value):return [{'kind':'source_evidence_unavailable','reason':'Saved source path malformed; original evidence preserved'}]
    directory=Path(value).resolve()
    if not directory.is_relative_to(folder/'runs'):return []
    path=(directory/'source/publisher_rejections.json').resolve()
    if not path.is_relative_to(folder/'runs'):return []
    try:
        if path.stat().st_size>256*1024:return [{'kind':'source_evidence_unavailable','reason':'Saved source diagnostic exceeds bounded read; outcome unknown'}]
        data=read_json(path);result=[]
        if not isinstance(data,dict) or not isinstance(data.get('rejected'),list):raise ValueError('Incomplete source diagnostic schema')
        for item in data.get('rejected',[])[:20]:
            if not isinstance(item,dict):
                result.append({'kind':'source_evidence_unavailable','reason':'Malformed rejection entry; other saved entries retained'});continue
            review=item.get('source_review');review=review if isinstance(review,dict) else {}
            source=review.get('source');source=source if isinstance(source,dict) else {}
            if not item.get('opportunity_id') or not (item.get('reason') or review.get('reason')):
                result.append({'kind':'source_evidence_unavailable','reason':'Rejection identity/reason incomplete; not a confirmed publisher policy rejection'});continue
            result.append({'opportunity_id':str(item.get('opportunity_id',''))[:32],
                'kind':str(item.get('kind') or review.get('rejection_kind') or 'official_source_policy')[:100],
                'reason':str(item.get('reason') or review.get('reason') or 'Source review blocked')[:700],
                'source_sha256':source.get('sha256'),'document_version':source.get('document_version'),
                'evidence':str(path.relative_to(folder)),'evidence_sha256':sha256_file(path),
                'scope':'Saved source-selection evidence; no new current-source observation'})
        return result
    except FileNotFoundError:return []
    except (OSError,ValueError,TypeError,AttributeError):return [{'kind':'source_evidence_unavailable','reason':'Saved source diagnostic unreadable/incomplete; outcome unknown','scope':'No inference of source closure, eligibility or zero errors'}]


def discovery_coverage(folder,job):
    folder=Path(folder).resolve();progress=job.get('progress') or {};value=job.get('run_dir') or (progress.get('run_dir') if isinstance(progress,dict) else None)
    if not isinstance(value,str) or any(ord(c)<32 for c in value):return None
    path=(Path(value)/'source/discovery_coverage.json').resolve()
    if not path.is_relative_to(folder/'runs'):return None
    try:
        if path.stat().st_size>256*1024:return None
        report=read_json(path)
        if not isinstance(report,dict) or report.get('schema')!='SOCIAL_DISCOVERY_COVERAGE_V1':return None
        return {**report,'observation_phase':'Saved discovery before source selection/publication; not a live cursor read','evidence_sha256':sha256_file(path)}
    except (OSError,ValueError):return None


def source_selection_summary(folder,job):
    """Saved bounded-pass result, never a global no-opportunities claim."""
    folder=Path(folder).resolve();progress=job.get('progress')
    if not isinstance(progress,dict):progress={}
    value=progress.get('run_dir') or job.get('run_dir')
    if not isinstance(value,str) or not value or any(ord(c)<32 for c in value):return None
    path=(Path(value)/'source/audience_selection.json').resolve()
    if not path.is_relative_to(folder/'runs'):return None
    if not path.exists():return None
    unknown={'status':'source_outcome_unconfirmed','reason':'Saved audience/source-selection diagnostic unreadable or malformed; no eligibility or zero-topics inference','global_opportunity_absence_established':False}
    try:
        if path.stat().st_size>256*1024:return unknown
        data=read_json(path)
        meanings={
          'no_suitable_topic':'No audience-matching topic in this saved bounded pass; institutional sources are not personal offers.',
          'no_supported_format':'Audience-relevant facts retained, but the supported short format could not express them.',
          'source_review_unavailable':'Source conditions are unconfirmed; this does not establish closure or ineligibility.',
          'publisher_rejected':'Reviewed candidates were rejected by source policy; this is not all opportunities.',
          'no_candidates_in_bounded_pass':'No candidates in this saved bounded pass; this is not a complete search.'}
        if not isinstance(data,dict) or data.get('status') not in meanings or data.get('audience') not in {'general_us','small_business','institutional'}:return unknown
        groups={}
        for key in ('deferred','format_deferred','source_deferred'):
            rows=data.get(key,[])
            if not isinstance(rows,list):return unknown
            if any(not isinstance(r,dict) for r in rows):return unknown
            groups[key]=[{k:r[k] for k in ('opportunity_id','category','reason','outcome','error_type') if k in r} for r in rows[:20]]
        return {'status':data['status'],'audience':data['audience'],'reason':meanings[data['status']],**groups,'evidence':str(path.relative_to(folder)),'evidence_sha256':sha256_file(path),'global_opportunity_absence_established':False,'individual_eligibility_assessed':False,'scope':'Saved bounded selection; no fresh source read, local application availability or personal entitlement established'}
    except (OSError,ValueError,TypeError,AttributeError):return unknown


def source_blockers(folder,job):
    rows=_publisher_blockers(folder,job);selection=source_selection_summary(folder,job)
    automatic=automatic_reference_summary(folder,job)
    if automatic:rows.insert(0,{'kind':'automatic_reference_selection','reason':automatic['reason'],'selection':automatic,'scope':'Fixed catalog only; not a global absence/eligibility decision'})
    if selection:rows.insert(0,{'kind':'source_selection','reason':selection['reason'],'selection_status':selection['status'],'selection':selection,'scope':'Bounded pass only; not a publisher closure or individual eligibility decision'})
    return rows


def automatic_reference_summary(folder,job):
    folder=Path(folder).resolve();progress=job.get('progress')
    if not isinstance(progress,dict):progress={}
    value=progress.get('run_dir') or job.get('run_dir')
    if not isinstance(value,str) or not value or any(ord(c)<32 for c in value):return None
    path=(Path(value)/'source/automatic_reference_selection.json').resolve()
    if not path.is_relative_to(folder/'runs') or not path.exists():return None
    unknown={'status':'reference_outcome_unconfirmed','reason':'Saved automatic-reference result is malformed/unavailable; no eligibility or global absence inference','global_opportunity_absence_established':False}
    try:
        if path.stat().st_size>256*1024:return unknown
        data=read_json(path)
        if not isinstance(data,dict) or data.get('schema')!='SOCIAL_AUTOMATIC_REFERENCE_SELECTION_V1' or data.get('catalog')!='general_us_information_v1' or data.get('audience')!='general_us':return unknown
        entries=data.get('entries')
        if not isinstance(entries,list) or len(entries)>3 or any(not isinstance(r,dict) or r.get('kind') not in {'energy','wages','unclaimed'} or r.get('state') not in {'duplicate','unconfirmed','selected','budget_exhausted'} for r in entries):return unknown
        selected=data.get('selected')
        if selected is not None:
            if not isinstance(selected,dict) or selected not in entries or selected.get('state')!='selected':return unknown
            status='reference_material_revision_selected' if selected.get('not_new_program') is True else 'reference_selected';reason=('Supported official source material changed; revised existing information topic, not a new program or entitlement.' if selected.get('not_new_program') is True else 'Unseen supported personal-information topic selected after Grants.gov; not a new grant or entitlement.')
        elif data.get('status')=='reference_recheck_not_due':status=data['status'];reason='Supported topics already used; no repeat draft. Reference checks are not yet due; see next-check dates in saved cycle evidence.'
        elif data.get('status')=='reference_recheck_no_new_material':status=data['status'];reason='Bounded source recheck produced no supported new material; unchanged/cosmetic/unsupported changes are not a new story. See saved cycle diagnostics.'
        elif data.get('status')=='no_unseen_supported_reference' and len(entries)==3 and {r['kind'] for r in entries}=={'energy','wages','unclaimed'} and all(r['state']=='duplicate' for r in entries):status=data['status'];reason='All three supported personal-information topics were already used/reserved; no duplicate draft created.'
        elif data.get('status')=='reference_sources_unconfirmed_or_exhausted':status=data['status'];reason='No usable unseen reference in this bounded catalog pass; saved errors/deferrals remain. Not proof no opportunities exist.'
        else:return unknown
        safe=[{k:str(r[k])[:500] for k in ('kind','opportunity_id','state','reason','money_type','fetched_at','source_url') if k in r} for r in entries]
        return {'status':status,'reason':reason,'entries':safe,'global_opportunity_absence_established':False,'individual_eligibility_assessed':False,'reference_recheck':data.get('reference_recheck'),'evidence':str(path.relative_to(folder)),'evidence_sha256':sha256_file(path)}
    except (OSError,ValueError,TypeError,AttributeError):return unknown

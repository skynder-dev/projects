"""Official NIH HTML review in discovery and repeat-use source identity checks."""
import datetime as dt
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,utc_now,atomic_bytes
from .grant_attachments import fetch_html,discover
from .nih_document import parse_document,assess


def review_nih(record,directory,fetch=None):
    directory=Path(directory)
    try:
        descriptors=record.get('announcement_attachments') or []
        if len(descriptors)!=1:raise PipelineError('NIH full announcement HTML missing or ambiguous')
        snapshot=(record.get('_field_sources') or {}).get('announcement_attachments')
        if not snapshot:raise PipelineError('NIH attachment has no official detail snapshot provenance')
        raw,meta=(fetch or fetch_html)(descriptors[0],snapshot,directory)
        if sha256_bytes(raw)!=meta['sha256']:raise PipelineError('NIH attachment response hash differs')
        document=parse_document(raw,record)
        policy=assess(document,record,min_days=record.get('_selection_min_days',10))
        meta={**meta,'kind':'nih_html_attachment','content_sha256':document['content_sha256'],'canonical_schema':document['schema']}
        record.update(announcement_source=meta,application_schedule={k:v for k,v in document.items() if k in ('cycles','posted_date','application_open_date','expiration_date','deadline_time')},
                      budget_scope=document['budget'],application_deadline_policy=policy)
        record['fields']['application_schedule']='Full NIH HTML keyDatesContentTable application columns (not review/start dates)'
        record['fields']['budget_scope']='Full NIH HTML Award Budget and Award Project Period'
        record.setdefault('_field_sources',{}).update(application_schedule=meta,budget_scope=meta)
        atomic_bytes(directory/('attachment_'+descriptors[0]['attachment_id']+'.txt'),document['text'].encode())
        report={'checked':policy['pass'],'source':meta,'document_complete':True,'deadline_agreement':policy,
                'budget_scope':document['budget'],'selection_rejected':policy['selection_rejected'],
                'rejection_kind':policy['rejection_kind'],'explicitly_closed':False,'editorial_approved':False,
                'reason':policy['reason'],'review_level':'Full primary attachment identity, application-type dates and annual phase/direct-cost units; not individual eligibility or linked policy review'}
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        report={'checked':False,'selection_rejected':False,'explicitly_closed':False,'reason':'NIH full attachment unconfirmed: '+str(error)[:300]}
    write_json(directory/('announcement_check_'+str(record['opportunity_id'])+'.json'),report)
    return report


def document_check_nih(root,current,detail,evidence,fetch=None):
    root=Path(root).resolve();evidence=Path(evidence)
    result={'kind':'nih_html_attachment','current_content_confirmed':False,'changed':False,'differences':[]}
    try:
        saved=read_json(root/'topic.json')['selected'];previous=saved['announcement_source']
        old=(root/previous['file']).resolve()
        if not old.is_relative_to(root) or sha256_file(old)!=previous['sha256']:raise PipelineError('Saved NIH attachment missing or hash mismatch')
        olddoc=parse_document(old.read_bytes(),saved)
        if olddoc['content_sha256']!=previous['content_sha256']:raise PipelineError('Saved NIH content identity differs')
        descriptors=discover(detail,current['opportunity_id'])
        if descriptors!=[previous['descriptor']]:
            result['differences'].append({'kind':'announcement_attachment_membership','before':[previous['descriptor']],'after':descriptors})
            result['changed']=True
            result['reason']='Official attachment membership/metadata changed; new editorial review required'
            return result
        # The caller carries the just-fetched API metadata in memory, not a guessed old snapshot.
        snapshot=current.get('_detail_snapshot')
        if not snapshot:raise PipelineError('Current NIH detail snapshot provenance missing')
        evidence.mkdir(parents=True,exist_ok=True)
        source=evidence.parent/('opportunity_'+str(current['opportunity_id'])+'.json')
        if not source.is_file():raise PipelineError('Fresh NIH API evidence missing')
        atomic_bytes(evidence/source.name,source.read_bytes())
        raw,meta=(fetch or fetch_html)(descriptors[0],snapshot,evidence)
        if sha256_bytes(raw)!=meta['sha256']:raise PipelineError('Current NIH attachment hash differs')
        stamp=dt.datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(utc_now()-stamp).total_seconds()<=300:raise PipelineError('Current NIH observation not fresh')
        if meta['sha256']!=previous['sha256']:
            result['differences'].append({'kind':'document_bytes','before_sha256':previous['sha256'],'after_sha256':meta['sha256']})
            result['changed']=True
        document=parse_document(raw,current);policy=assess(document,current,min_days=saved.get('_selection_min_days',10))
        for key in ('cycles','budget','application_open_date','expiration_date'):
            if olddoc[key]!=document[key]:result['differences'].append({'kind':key,'before':olddoc[key],'after':document[key]})
        if not policy['listing_deadline_agreement']:result['differences'].append({'kind':'listing_document_conflict','detail':policy})
        result.update(changed=bool(result['differences']),current_document=meta,deadline_agreement=policy,budget_scope=document['budget'])
        result['current_content_confirmed']=not result['changed'] and policy['pass']
        result['reason']=policy['reason']
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        result['error']=type(error).__name__+': '+str(error)[:300]
    return result

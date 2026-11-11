"""Rebuild derived facts from the exact pinned raw sources, never mutate a parent."""
from pathlib import Path
from .common import PipelineError,read_json,sha256_file,write_json,utc_now
from .grants import normalize


def rebuild_saved_source(parent,directory,min_days=10):
    parent=Path(parent).resolve();directory=Path(directory)
    from .preparation import verify_preparation
    manifest=verify_preparation(parent);original=read_json(parent/'topic.json')['selected']
    snapshot=read_json(parent/'sources.json')['selected_snapshot']
    name=snapshot.get('file');entry=next((e for e in manifest['files'] if e['path']==name),None)
    if not isinstance(name,str) or not entry or entry['sha256']!=snapshot.get('sha256'):raise PipelineError('Pinned raw source reference is not bound to declared preparation bytes')
    raw=(parent/name).resolve()
    if not raw.is_relative_to(parent) or sha256_file(raw)!=snapshot['sha256']:raise PipelineError('Pinned raw source snapshot missing or changed')
    if original.get('public_money_source'):
        # An information page is not Grants.gov JSON. Replay exact pinned bytes
        # without fabricating a new observation, live status or approval.
        payload=original.get('public_money_content') or {}
        try:content=raw.read_bytes().decode('utf-8')
        except UnicodeDecodeError as error:raise PipelineError('Pinned supplied-page decoding differs; preserve and review encoding') from error
        candidate={'source_url':original['source_url'],'public_money_content':{
            'content':content,'content_type':payload.get('content_type','html'),
            'reconstructed':bool(original['public_money_source'].get('reconstructed')),
            'fetched_at':snapshot.get('fetched_at'),'snapshot_file':snapshot['file']}}
        from .source_brief import adapt
        record=adapt(candidate,audience=(read_json(parent/'preparation_config.json').get('selection') or {}).get('audience','general_us'))
        target=(directory.parent/snapshot['file']).resolve()
        if not target.is_relative_to(directory.resolve()):raise PipelineError('Pinned public source target is outside the child source directory')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw.read_bytes())
        review={'checked':False,'reason':'Pinned public-information bytes replayed; no new accepted live ingest','replayed_from_preparation':manifest['preparation_id'],'new_official_observation':False}
        code=Path(__file__).resolve().parent
        versions={name:sha256_file(code/name) for name in ('common.py','source_brief.py','public_money.py','editorial_brief.py','audience_selection.py','claims.py','writer.py','source_description.py','source_quality.py','rematerialize.py')}
        derivation={'schema':'SOCIAL_SOURCE_MATERIALIZATION_V1','rebuilt_at':utc_now().isoformat(),'parent_preparation_id':manifest['preparation_id'],'parent_script_sha256':sha256_file(parent/'script.json'),'raw_snapshot':snapshot,'code_sha256':versions,'new_official_observation':False,'scope':'Exact pinned supplied-page bytes reparsed; reconstruction and unknown observation time remain unchanged; no fresh source or editorial approval'}
        write_json(directory.parent/'source_materialization.json',derivation)
        return record,review,derivation
    detail=read_json(raw).get('data') or {}
    if str(detail.get('id'))!=str(original['opportunity_id']):raise PipelineError('Pinned raw source identity mismatch')
    record=normalize({'id':original['opportunity_id'],'oppStatus':original.get('status'),'docType':original.get('doc_type')},detail)
    record['_field_sources']={key:(original.get('_field_sources') or {}).get(key,snapshot) for key in record['fields']}
    record['_selection_min_days']=min_days
    for key in ('selection_assessment','audience_assessment','ranking_evidence'):
        if key in original:record[key]=original[key]
    source=original.get('announcement_source')
    if not source and record.get('agency_code')=='IMLS' and len(record.get('announcement_attachments') or [])==1:
        descriptor=record['announcement_attachments'][0];aid=descriptor['attachment_id'];name='source/attachment_'+aid+'.pdf'
        entries=[e for e in manifest['files'] if e['path']==name]
        if len(entries)==1:
            candidate=(parent/name).resolve();entry=entries[0]
            if not candidate.is_relative_to(parent) or sha256_file(candidate)!=entry['sha256'] or candidate.stat().st_size!=descriptor['bytes']:raise PipelineError('Pinned attachment recovery identity differs')
            receipt=parent/('source/attachment_'+aid+'_transport.json')
            if receipt.is_file():
                source=read_json(receipt)
                if source.get('descriptor')!=descriptor or source.get('sha256')!=entry['sha256']:raise PipelineError('Pinned transport receipt differs')
                source={**source,'kind':'structured_pdf_nofo'}
            else:
                source={'kind':'structured_pdf_nofo','descriptor':descriptor,'file':name,'sha256':entry['sha256'],'bytes':entry['bytes'],
                        'url':'https://apply07.grants.gov/grantsws/rest/opportunity/att/download/'+aid,
                        'transport_receipt_unavailable':True,'observation_time_unrecorded':True,'observation_no_later_than':manifest['prepared_at'],
                        'recovery_basis':'Exact declared PDF bytes and matching full-announcement association from hash-verified parent API; no HTTP status/time invented'}

    if source and source.get('kind') in ('nsf_html_solicitation','nih_html_attachment','structured_pdf_nofo'):
        document=(parent/source['file']).resolve()
        if not document.is_relative_to(parent) or sha256_file(document)!=source['sha256']:raise PipelineError('Pinned full announcement missing or changed')
        raw_document=document.read_bytes()
        def replay(*args):
            if source['kind'] in ('nih_html_attachment','structured_pdf_nofo') and args[0]!=source.get('descriptor'):raise PipelineError('Pinned HTML attachment association changed')
            target=Path(args[-1])/Path(source['file']).name
            target.write_bytes(raw_document)
            return raw_document,{**source,'replayed_from_preparation':manifest['preparation_id'],'not_a_new_observation':True}
        from .announcements import review_source
        review=review_source(record,directory,fetch=replay)
    else:
        # Unavailable source stays blocked; offline draft rebuild never fetches it.
        review=read_json(parent/'production_plan.json').get('source_review_note') or {'checked':False,'reason':'Pinned full source review unavailable'}
        if original.get('submission_steps'):
            # Existing OJP parsed fields are pinned; full current check remains required before models.
            for key in ('submission_steps','submission_steps_source'):record[key]=original[key]
    code=Path(__file__).resolve().parent
    versions={name:sha256_file(code/name) for name in ('common.py','grants.py','announcements.py','nsf_document.py','nsf_conditions.py','nsf_tracks.py','source_dependencies.py','source_documents.py','duration_preflight.py','duration_profile.py','track_script.py','benefit_reel.py','scene_coherence.py','audience_selection.py','editorial_brief.py','source_brief.py','public_money.py','source_quality.py','source_description.py','nih_document.py','nih_review.py','claims.py','writer.py','compact_script.py','rematerialize.py','structured_nofo.py','structured_script.py','editorial.py','nofo_terms.py','term_guard.py')}
    derivation={'schema':'SOCIAL_SOURCE_MATERIALIZATION_V1','rebuilt_at':utc_now().isoformat(),'parent_preparation_id':manifest['preparation_id'],
                'parent_script_sha256':sha256_file(parent/'script.json'),'raw_snapshot':snapshot,
                'full_announcement_source':source,'code_sha256':versions,'new_official_observation':False,
                'scope':'Derived facts/script rebuilt with current code from exact hash-verified pinned raw sources; not refreshed source currency or editorial approval'}
    write_json(directory.parent/'source_materialization.json',derivation)
    return record,review,derivation

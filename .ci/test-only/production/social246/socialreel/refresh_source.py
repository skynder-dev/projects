"""Refresh only a pinned owned draft's official identity, then use normal source review."""
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,utc_now

def refresh(parent,directory,min_days,history_path=None):
    from .grants import GrantsGovClient,normalize
    from .announcements import review_source
    parent=Path(parent);directory=Path(directory);original=read_json(parent/'topic.json')['selected'];manifest=read_json(parent/'prepared.json');client=GrantsGovClient(directory,history_path=history_path)
    detail,snapshot=client.detail(original['opportunity_id'])
    if str(detail.get('id'))!=str(original['opportunity_id']) or detail.get('opportunityNumber')!=original['number']:raise PipelineError('Pinned official identity changed; new review required')
    record=normalize({'id':original['opportunity_id'],'oppStatus':str(detail.get('ost') or '').lower(),'docType':detail.get('docType')},detail);record['_selection_min_days']=min_days;record['_field_sources']={key:snapshot for key in record['fields']}
    review=review_source(record,directory)
    material={'schema':'SOCIAL_PINNED_SOURCE_REFRESH_V1','parent_preparation_id':manifest['preparation_id'],'parent_script_sha256':sha256_file(parent/'script.json'),'refreshed_at':utc_now().isoformat(),'new_official_observation':True,'raw_snapshot':snapshot,'full_announcement_source':record.get('announcement_source'),'editorial_approved':False,'scope':'New official observations for the exact owned pinned opportunity; parent preserved, no new topic search'}
    write_json(directory.parent/'source_materialization.json',material)
    return record,review,material,snapshot,client.calls

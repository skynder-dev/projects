"""Separate publisher changes from old text materialization after parser updates."""
from pathlib import Path
from .common import PipelineError,read_json,sha256_file
from .grants import normalize


def compare_fields(root,saved,current,fields):
    def canonical(value):return sorted(str(v).strip() for v in value) if isinstance(value,list) else value
    different=[key for key in fields if canonical(current.get(key))!=canonical(saved.get(key))]
    text_fields={'description','applicant_eligibility_desc'}
    materialization=[];unconfirmed=[]
    if text_fields.intersection(different):
        try:
            root=Path(root).resolve();snapshot=read_json(root/'sources.json')['selected_snapshot']
            path=(root/snapshot['file']).resolve()
            if not path.is_relative_to(root) or sha256_file(path)!=snapshot['sha256']:raise PipelineError('Saved raw synopsis provenance invalid')
            detail=read_json(path)['data']
            if str(detail.get('id'))!=str(saved['opportunity_id']):raise PipelineError('Saved raw synopsis identity invalid')
            baseline=normalize({'id':detail['id'],'oppStatus':detail.get('ost')},detail)
            for key in text_fields.intersection(different):
                if canonical(current.get(key))==canonical(baseline.get(key)):
                    materialization.append(key)
        except (PipelineError,OSError,ValueError,KeyError,TypeError):
            unconfirmed=sorted(text_fields.intersection(different))
    return {'official_changed_fields':[key for key in different if key not in materialization and key not in unconfirmed],
            'materialization_changed_fields':sorted(materialization),'text_comparison_unconfirmed_fields':unconfirmed,
            'scope':'Re-normalize hash-verified saved raw synopsis using current parser; formatting drift requires rebuild, not a publisher-change claim'}

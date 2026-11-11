"""Fresh source checks before resumed preparation may enter any model stage."""
from pathlib import Path
import datetime as dt
from .common import PipelineError,read_json,write_json,utc_now,parse_date
from .grants import GrantsGovClient,normalize
from .recheck import FIELDS
from .nofo_review import document_check,revoke_owned_approval


def check_prepared_source(root,evidence,fetch=None,document_fetch=None):
    root=Path(root);evidence=Path(evidence)
    result={'schema':'SOCIAL_PREPARATION_SOURCE_CHECK_V1','checked_at':utc_now().isoformat(),
            'ready_for_model_stage':False,'changed_synopsis_fields':[],'reasons':[],
            'publication_authorized':False,'model_execution_started':False}
    try:
        from .preparation import verify_preparation
        manifest=verify_preparation(root);result['package_id']=manifest['preparation_id']
        saved=read_json(root/'topic.json')['selected']
        if (read_json(root/'production_plan.json').get('source_review_note') or {}).get('checked') is not True:
            raise PipelineError('Saved full source review was not confirmed; rebuild/review source before model execution')
        if fetch is None:detail,meta=GrantsGovClient(evidence,pause_s=0,timeout=8).detail(saved['opportunity_id'])
        else:detail,meta=fetch(saved['opportunity_id'])
        if str(detail.get('id'))!=str(saved['opportunity_id']):raise PipelineError('Current official identity mismatch')
        stamp=dt.datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(utc_now()-stamp).total_seconds()<=300:raise PipelineError('Current API observation is not fresh')
        current=normalize({'id':detail['id'],'oppStatus':detail.get('ost')},detail);current['_detail_snapshot']=meta
        result['official_observation']=meta
        from .source_comparison import compare_fields
        comparison=compare_fields(root,saved,current,FIELDS);result['synopsis_comparison']=comparison
        changed=comparison['official_changed_fields']
        if comparison['materialization_changed_fields']:result['reasons'].append('Saved text materialization differs under current normalizer; rebuild/review required')
        if comparison['text_comparison_unconfirmed_fields']:result['reasons'].append('Saved raw text comparison unconfirmed')
        result['changed_synopsis_fields']=changed
        result['reasons'].extend('Official field changed: '+key for key in changed)
        if str(current.get('status') or '').lower()!='posted':result['reasons'].append('Official listing is not posted')
        for field in ('open_date','close_date'):
            date=parse_date(current.get(field))
            if date is None or date!=parse_date(saved.get(field)):result['reasons'].append('Official '+field+' changed or unconfirmed')
        from .editorial import production_gate
        gate=production_gate(current,meta,utc_now(),saved.get('_selection_min_days',10))
        if not gate['pass']:result['reasons'].extend(gate['errors'])
        result['nofo']=document_check(root,current,detail,evidence/'nofo',fetch=document_fetch)
        if not result['nofo']['current_content_confirmed']:result['reasons'].append('Current full source is changed, unavailable or outside deadline policy')
        result['editorial_approval_revoked']=revoke_owned_approval(root,result)
        result['ready_for_model_stage']=not result['reasons']
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        result['reasons'].append(type(error).__name__+': '+str(error)[:300])
    write_json(evidence/'preparation_source_check.json',result)
    return result

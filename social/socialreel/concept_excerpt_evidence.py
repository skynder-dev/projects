"""Explicit excerpt evidence mode; bound ledger validation, no transport or claims."""
import copy
from .common import PipelineError,stable_json,sha256_bytes
from .source_excerpt_model_view import verify_view,sha

def checked(bundle,expected_hash):
    try:
        ledger=bundle['ledger'];view=bundle['view'];binding=bundle['binding']
        if sha(ledger)!=expected_hash or view['ledger_sha256']!=expected_hash:
            raise ValueError('Pinned ledger identity mismatch')
        verify_view(view,binding,ledger)
        if ledger['profile']!='OJP_ORGANIZATIONAL_HEADINGS_V1' or ledger['intent']['audience']!='organizational_applicants' or ledger['intent']['topic']!='program_purpose':
            raise ValueError('Only explicit organizational program-purpose evidence mode supported')
        if ledger['coverage_scope']['usage_boundary']!='Program-purpose concepts only; not complete application, budget or timeline guidance.':
            raise ValueError('Historical profile usage boundary differs')
        if view['source']['scope']!='historical_organizational_source_not_current_availability':raise ValueError('Historical scope changed')
        return ledger,view
    except (KeyError,TypeError,ValueError) as error:
        raise PipelineError('Excerpt evidence invalid: '+str(error)) from error

def source_inputs(record,claims,cfg,bundle,contract,version):
    settings=cfg.get('concept_first') or {}
    if settings.get('evidence_mode')!='excerpts' or claims:
        raise PipelineError('Explicit excerpt mode requires no mixed legacy claim ledger')
    ledger,view=checked(bundle,settings.get('evidence_ledger_sha256'))
    if ledger['record_sha256']!=sha(record) or ledger['intent']['source_title']!=record.get('title'):
        raise PipelineError('Record/source does not match pinned excerpt ledger')
    if (cfg.get('selection') or {}).get('audience')!='organizational_applicants':raise PipelineError('Excerpt audience must be explicit organizational applicants')
    # Existing finite public-topic intent cannot be silently replaced by OJP.
    if (cfg.get('selection') or {}).get('public_reference_topic') is not None:raise PipelineError('Public topic intent cannot be silently replaced by historical OJP')
    data={'schema':version,'evidence_mode':'excerpts','audience':'organizational_applicants',
          'language_contract':contract,'source_evidence':copy.deepcopy(view)}
    owner=settings.get('owner_context')
    if owner is not None:
        if not isinstance(owner,dict) or owner.get('scope')!='unverified_owner_editorial_context' or owner.get('source_evidence') is not False or owner.get('owner_approval') is not False:
            raise PipelineError('Owner context is separate unverified preference, never source evidence')
        data['owner_context']=copy.deepcopy(owner)
    return data

def keys(data,bundle):
    ledger,view=checked(bundle,data.get('source_evidence',{}).get('ledger_sha256'))
    if data.get('source_evidence')!=view:raise PipelineError('Concept source input/view differs from bound ledger')
    return [row[0] for row in view['excerpts']]

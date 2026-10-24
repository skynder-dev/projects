"""Audience fit is a prerequisite, never a bonus that money can outweigh."""
from .common import PipelineError
import re

AUDIENCES=('general_us','small_business','institutional')

def assess(record,audience='general_us'):
    if audience not in AUDIENCES:raise PipelineError('Unknown editorial audience: '+str(audience))
    if record.get('editorial_brief'):
        from .editorial_brief import inspect
        result=inspect(record,audience)
        reason='Saved editorial profile matches this audience category; individual eligibility is not established' if result['suitable'] else '; '.join(result.get('errors') or ['Audience fit not established'])
        return {**result,'reason':reason,'audience':audience,'amount_used_for_fit':False}
    profile=(record.get('primary_conditions') or {}).get('profile','')
    title=(record.get('title') or '').lower()
    institutional=bool(record.get('track_conditions')) or profile=='imls_native_library_organization_v2' or (record.get('publisher_eligibility') or {}).get('unaffiliated_individuals_eligible') is False or any(s in title for s in ('cybertraining','tribal librar','native american library','translation to practice'))
    # Categories describe the intended applicant, not an eligibility determination.
    text=(record.get('applicant_eligibility_desc') or '').lower()
    category='institutional' if institutional else ('small_business' if 'small business' in text else ('personal_money' if 'individual' in text else 'unclassified'))
    # No saved reviewed profile establishes a general personal benefit or a
    # small-business offer. Generic applicant labels/keywords cannot do that.
    primary=record.get('primary_conditions') or {};tracks=record.get('track_conditions') or {}
    pdf_hash=primary.get('pdf_sha256');track_hash=(tracks.get('source') or {}).get('sha256')
    reviewed_primary=profile=='imls_native_library_organization_v2' and isinstance(pdf_hash,str) and bool(re.fullmatch('[0-9a-f]{64}',pdf_hash)) and (record.get('announcement_source') or {}).get('sha256')==pdf_hash
    reviewed_tracks=tracks.get('schema')=='SOURCE_TRACK_CONDITIONS_V1' and bool(tracks.get('tracks')) and isinstance(track_hash,str) and bool(re.fullmatch('[0-9a-f]{64}',track_hash))
    verified_profile=institutional and (reviewed_primary or reviewed_tracks)
    fits=audience=='institutional' and category=='institutional' and verified_profile
    return {'audience':audience,'category':category,'suitable':fits,'reviewed_audience_profile':verified_profile,
            'reason':'Reviewed specialized institutional program; retain for its audience' if fits else 'No reviewed profile establishes a benefit for the configured audience',
            'general_personal_money_offer':False,'amount_used_for_fit':False}

def require(record,audience='general_us'):
    result=assess(record,audience)
    if not result['suitable']:raise PipelineError('Подходящая тема не найдена: '+result['reason'])
    return result

def select_saved(candidates,audience='general_us'):
    considered=[{'opportunity_id':r.get('opportunity_id'),'title':r.get('title'),**assess(r,audience)} for r in candidates]
    matched=[r for r,a in zip(candidates,considered) if a['suitable']]
    return {'status':'selected' if matched else 'no_suitable_topic','audience':audience,'selected':matched[0] if matched else None,'considered':considered,'preserve_specialized_candidates':True}

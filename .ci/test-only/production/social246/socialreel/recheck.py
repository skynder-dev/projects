"""Revalidate a saved delivery at time of use, independently of export-time metadata."""
import argparse
import json
import sqlite3
import uuid
from pathlib import Path
from .common import ROOT, PipelineError, read_json, utc_now, parse_date
from .packages import verify_package, source_freshness
from .grants import GrantsGovClient, normalize

FIELDS=('number','title','agency_code','award_ceiling','award_floor',
        'estimated_total_program_funding','expected_number_of_awards','cost_sharing',
        'applicant_types','applicant_eligibility_desc','funding_instruments',
        'funding_categories','description','full_announcement_url')

def observation_owner(root):
    """Resolve only the exact registered run; detached packages get no queue sink."""
    root=Path(root).resolve();folder=root.parent.parent
    if root.parent.name!='runs' or len(folder.name)!=32 or any(c not in '0123456789abcdef' for c in folder.name):return None
    db=folder.parent/'queue.sqlite3'
    if not db.is_file():raise PipelineError('Managed-looking package has no ownership index; review required')
    from contextlib import closing
    from .nofo_review import _owned_registered_run
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as connection:
        row=connection.execute('SELECT run_dir FROM jobs WHERE id=?',(folder.name,)).fetchone()
    if not row or not row[0] or not _owned_registered_run(db,row[0],root):raise PipelineError('Package/queue ownership unconfirmed; no connector request')
    return db.parent/'history.json'

def check_delivery(directory, *, online=True, now=None, evidence_dir=None, fetch=None, nofo_fetch=None):
    root=Path(directory).resolve();now=now or utc_now()
    report={'schema':'SOCIAL_DELIVERY_RECHECK_V1','checked_at':now.isoformat(),
            'integrity_pass':False,'current_status_confirmed':False,
            'ready_for_current_use':False,'publication_authorized':False,
            'live_observation':'not_requested','reasons':[],
            'scope':'Saved package integrity, current Grants.gov status/synopsis fields and exact official NOFO document/version comparison; no publication approval'}
    check=verify_package(root);report['integrity_pass']=check['pass']
    if not check['pass']:
        report['reasons']=['package_integrity_failed']+check['errors'];return report
    saved=read_json(root/'topic.json')['selected']
    report['opportunity_id']=str(saved['opportunity_id'])
    report['package_id']=read_json(root/'package_manifest.json')['package_id']
    report['source_as_of']=read_json(root/'sources.json').get('selected_snapshot',{}).get('fetched_at')
    if read_json(root/'result.json').get('editorial_approval_required') is True:
        report['reasons'].append('repaired_package_requires_new_editorial_approval')
    stored=source_freshness(root,now=now);report['stored_snapshot_freshness_now']=stored
    if not stored['fresh']:report['reasons'].extend('stored_snapshot: '+e for e in stored['reasons'])
    if not online:
        report['reasons'].append('live_status_unconfirmed_offline');return report
    evidence=Path(evidence_dir or root.parent/'rechecks'/uuid.uuid4().hex).resolve()
    try:
        owner=observation_owner(root)
        report['observation_ownership']='registered_package_queue' if owner else 'detached_package_no_queue'
        report['observation_history']=str(owner) if owner else None
        if owner is None and (evidence/'queue.sqlite3').exists():raise PipelineError('Detached evidence directory contains a queue; no implicit ownership')
        if fetch is None:
            client=GrantsGovClient(evidence,pause_s=0,timeout=8,history_path=owner or evidence/'history.json')
            detail,meta=client.detail(report['opportunity_id'])
        else:detail,meta=fetch(report['opportunity_id'])
        if str(detail.get('id'))!=report['opportunity_id']:raise ValueError('Official response identity mismatch')
        stamp=__import__('datetime').datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(now-stamp).total_seconds()<=300:
            raise ValueError('Live observation timestamp invalid or stale')
        current=normalize({'id':detail['id'],'oppStatus':detail.get('ost')},detail)
        current['_detail_snapshot']=meta
        report['live_observation']='received';report['official_observation']=meta
        report['evidence_directory']=str(evidence.resolve())
        report['current_status']=current['status'];report['current_close_date']=current['close_date']
        if (current.get('status') or '').lower()!='posted':report['reasons'].append('official_listing_not_posted')
        if (current.get('doc_type') or '').lower()!='synopsis':report['reasons'].append('official_listing_not_synopsis')
        for field in ('close_date','open_date'):
            actual=parse_date(current.get(field));previous=parse_date(saved.get(field))
            if actual is None:report['reasons'].append('official_'+field+'_unknown')
            elif field=='close_date' and actual<=now.date():report['reasons'].append('official_deadline_expired_or_same_day')
            elif field=='open_date' and actual>now.date():report['reasons'].append('official_listing_not_open_yet')
            if actual!=previous:report['reasons'].append('official_'+field+'_changed')
        from .source_comparison import compare_fields
        comparison=compare_fields(root,saved,current,FIELDS);report['synopsis_comparison']=comparison
        changed=comparison['official_changed_fields']
        if comparison['materialization_changed_fields']:report['reasons'].append('saved_text_materialization_requires_rebuild')
        if comparison['text_comparison_unconfirmed_fields']:report['reasons'].append('saved_raw_text_comparison_unconfirmed')
        report['changed_synopsis_fields']=changed
        report['reasons'].extend('official_field_changed: '+key for key in changed)
        report['current_status_confirmed']=bool(current.get('status'))
        from .nofo_review import document_check
        report['nofo']=document_check(root,current,detail,evidence/'nofo',fetch=nofo_fetch)
        if report['nofo']['current_content_confirmed'] is not True:
            report['reasons'].append('nofo_changed_requires_editorial_review' if report['nofo']['changed'] else 'current_nofo_content_unconfirmed')
        report['source_compatible_with_editorial_review']=report['nofo']['current_content_confirmed'] and not bool(changed or report['nofo']['changed'] or comparison['materialization_changed_fields'] or comparison['text_comparison_unconfirmed_fields']) and 'repaired_package_requires_new_editorial_approval' not in report['reasons']
        from .nofo_review import owned_approval
        try:
            approved=owned_approval(root,report['package_id'])
            report['editorial_approval_valid']=approved is True and report['source_compatible_with_editorial_review']
            report['editorial_approval_evidence']='Owned matching-package approval verified' if approved is True else 'No verified matching-package approval'
        except (sqlite3.Error,OSError,ValueError) as error:
            report['editorial_approval_valid']=False;report['editorial_approval_evidence']='Approval state unavailable: '+type(error).__name__
        report['ready_for_current_use_scope']='Technical package/current-source checks; editorial/publication approval is separate' 
        from .nofo_review import revoke_owned_approval
        try:
            report['editorial_approval_revoked']=revoke_owned_approval(root,report)
        except (sqlite3.Error,OSError,ValueError) as error:
            report['editorial_approval_valid']=False
            report['reasons'].append('editorial_revocation_failed: '+type(error).__name__+': '+str(error)[:200])
        report['ready_for_current_use']=not report['reasons']
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        report['live_observation']='unavailable'
        report['reasons'].append('live_status_unconfirmed: '+type(error).__name__+': '+str(error)[:300])
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description='Check saved Social delivery now. Offline or unavailable sources never confirm currency.')
    parser.add_argument('directory',nargs='?',default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args(argv)
    result=check_delivery(args.directory,online=not args.offline)
    print(json.dumps(result,indent=2))
    return 0 if result['ready_for_current_use'] else 2

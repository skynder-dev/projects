"""Atomic, portable export of a verified Social package. No models or network."""
import json
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path
from .common import ROOT, PipelineError, read_json, sha256_file, utc_now
from .packages import verify_package, source_freshness
from .recheck import check_delivery

PORTABLE_MODULES=('__init__.py','common.py','grants.py','packages.py','package_contract.py','claims.py','recheck.py','nofo.py','nofo_review.py','announcements.py','nsf_document.py','nsf_document_review.py','grant_attachments.py','nih_document.py','nih_review.py','source_comparison.py','nsf_conditions.py','nsf_tracks.py','track_script.py','source_dependencies.py','source_documents.py','duration_preflight.py','duration_profile.py','asr_lineage.py','derived_audio.py','voice.py','production_origin.py','structured_nofo.py','nofo_terms.py','term_guard.py','benefit_reel.py','scene_coherence.py','editorial_brief.py','audience_selection.py','source_brief.py','visual_revision.py','meaning_review.py','public_money.py','source_quality.py','public_page.py','source_description.py','subtitles.py','workflow.py','editorial.py')

def export_package(directory, destination=None, *, online=True):
    if type(online) is not bool:raise PipelineError('Export source-check mode must be boolean')
    root=Path(directory).resolve()
    check=verify_package(root)
    if not check['pass']:
        raise PipelineError('Cannot export invalid package: '+'; '.join(check['errors']))
    manifest=read_json(root/'package_manifest.json')
    media=read_json(root/'media_manifest.json')
    package_id=manifest['package_id']
    destination=Path(destination or ROOT/'runs'/'exports'/(root.name+'_'+package_id[:16]+'_v10.zip')).resolve()
    if destination.is_relative_to(root):
        raise PipelineError('Export destination must be outside the source package')
    names={str(e['path']).replace('\\','/') for e in manifest['files']+media['files']}
    names.update(('package_manifest.json','result.json'))
    if (root/'REVIEW.md').is_file():names.add('REVIEW.md')
    destination.parent.mkdir(parents=True,exist_ok=True)
    current_check=check_delivery(root) if online else check_delivery(root,online=False)
    checker={'.delivery_checker/socialreel/'+name:ROOT/'socialreel'/name for name in PORTABLE_MODULES}
    launcher=b"from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parent/'.delivery_checker'))\nfrom socialreel.recheck import main\nraise SystemExit(main([str(Path(__file__).resolve().parent)]+sys.argv[1:]))\n"
    checker_names=set(checker)|{'check_delivery.py'}
    # Never overwrite an existing delivery. Concurrent exporters race safely via hard link.
    if destination.exists():
        try:
            with zipfile.ZipFile(destination) as z:
                if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Archive contains duplicate names')
                if z.testzip() is not None or set(z.namelist())!=names|set(json.loads(z.read('export.json')).get('checker_files',{}))|{'export.json'}:
                    raise ValueError('Archive contents differ')
                previous_receipt=json.loads(z.read('export.json'))
                if previous_receipt['package_id']!=package_id:
                    raise ValueError('Archive identity differs')
                for name,digest in previous_receipt.get('checker_files',{}).items():
                    if hashlib.sha256(z.read(name)).hexdigest()!=digest:
                        raise ValueError('Portable checker bytes differ: '+name)
                for name in names:
                    if hashlib.sha256(z.read(name)).hexdigest()!=sha256_file(root/name):
                        raise ValueError('Archive bytes differ: '+name)
            return {'path':str(destination),'sha256':sha256_file(destination),
                    'bytes':destination.stat().st_size,'package_id':package_id,
                    'portable_verification_pass':True,'reused':True,'live_refetch':current_check.get('live_observation')=='received',
                    'source_freshness_at_export':previous_receipt['source_freshness_at_export'],
                    'historical_export_metadata':True,'delivery_check_now':current_check,
                    'ready_for_current_use':current_check['ready_for_current_use'],
                    'portable_checker_present':'check_delivery.py' in z.namelist()}
        except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
            raise PipelineError('Existing export differs or is damaged; preserved: '+str(error)) from error
    receipt={'schema':'SOCIAL_PORTABLE_EXPORT_V10','package_id':package_id,
             'exported_at':utc_now().isoformat(),'live_refetch':current_check.get('live_observation')=='received',
             'source_snapshot':read_json(root/'sources.json').get('selected_snapshot'),
             'source_freshness_at_export':source_freshness(root),
             'currency_metadata_scope':'Observation at export only; run check_delivery.py again at time of use',
             'delivery_check_at_export':current_check,
             'checker_files':{**{name:sha256_file(path) for name,path in checker.items()},
                              'check_delivery.py':hashlib.sha256(launcher).hexdigest()}}
    with tempfile.TemporaryDirectory(prefix='_export_',dir=destination.parent) as temporary:
        temporary=Path(temporary)
        archive=temporary/'package.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for name in sorted(names):z.write(root/name,name)
            for name,path in checker.items():z.write(path,name)
            z.writestr('check_delivery.py',launcher)
            z.writestr('export.json',json.dumps(receipt,indent=2))
        unpack=temporary/'verify';unpack.mkdir()
        with zipfile.ZipFile(archive) as z:
            if len(z.namelist())!=len(set(z.namelist())):raise PipelineError('Export archive duplicate names')
            if z.testzip() is not None:raise PipelineError('Export archive CRC failure')
            # names came only from the already verified manifest; normalize again before extraction.
            for item in z.infolist():
                target=(unpack/item.filename).resolve()
                if not target.is_relative_to(unpack):raise PipelineError('Unsafe export path')
            z.extractall(unpack)
        exported=verify_package(unpack)
        if not exported['pass']:raise PipelineError('Export changed during packaging: '+'; '.join(exported['errors']))
        for name in names:
            if sha256_file(root/name)!=sha256_file(unpack/name):
                raise PipelineError('Source changed during export: '+name)
        digest=sha256_file(archive);size=archive.stat().st_size
        os.link(archive,destination)
    return {'path':str(destination),'sha256':digest,'bytes':size,'package_id':package_id,
            'portable_verification_pass':True,'live_refetch':current_check.get('live_observation')=='received',
            'source_freshness_at_export':receipt['source_freshness_at_export'],
            'delivery_check_now':current_check,'ready_for_current_use':current_check['ready_for_current_use'],
            'portable_checker_present':True}

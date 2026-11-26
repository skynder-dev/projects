"""Minimal portable provenance for a production resumed from an immutable draft."""
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes

def create_origin(root,parent_manifest):
    root=Path(root);parent_files=[{'path':e['path'],'sha256':e['sha256']} for e in parent_manifest['files']]
    identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in parent_files).encode())
    if identity!=parent_manifest['preparation_id']:raise PipelineError('Parent preparation identity differs')
    report=read_json(root/'source_recheck/preparation_source_check.json')
    if report.get('ready_for_model_stage') is not True:raise PipelineError('Production origin requires the actually passing source check')
    api=report['official_observation'];document=report['nofo']['current_document']
    paths=[('official_listing','source_recheck/'+Path(api['file']).name,api['sha256']),
           ('official_document','source_recheck/nofo/'+Path(document['file']).name,document['sha256']),
           ('source_check','source_recheck/preparation_source_check.json',None)]
    if (root/'source_materialization.json').is_file():paths.append(('materialization','source_materialization.json',None))
    evidence=[]
    for role,name,expected in paths:
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():raise PipelineError('Production evidence missing: '+name)
        digest=sha256_file(path)
        if expected and digest!=expected:raise PipelineError('Production observation hash differs: '+name)
        evidence.append({'role':role,'path':name,'bytes':path.stat().st_size,'sha256':digest})
    origin={'schema':'SOCIAL_PRODUCTION_ORIGIN_V1','parent_preparation_id':identity,'parent_files':parent_files,
            'source_checked_at':report['checked_at'],'evidence':evidence,
            'editorial_approved_at_generation':False,'publication_authorized':False,
            'scope':'Exact draft identity and actual pre-model source observation; approval is never inferred, later owned package approval is separate'}
    write_json(root/'production_origin.json',origin)
    return ['production_origin.json']+[e['path'] for e in evidence]

def verify_origin(root,declared,expected_parent):
    root=Path(root);origin=read_json(root/'production_origin.json')
    if origin.get('schema')!='SOCIAL_PRODUCTION_ORIGIN_V1':raise PipelineError('Unknown production origin schema')
    identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in origin['parent_files']).encode())
    if identity!=origin.get('parent_preparation_id') or identity!=expected_parent:raise PipelineError('Parent preparation provenance identity differs')
    roles=set()
    for entry in origin['evidence']:
        path=(root/entry['path']).resolve();roles.add(entry['role'])
        if entry['path'] not in declared or not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size!=entry['bytes'] or sha256_file(path)!=entry['sha256']:raise PipelineError('Undeclared or changed production evidence: '+entry['path'])
    if not {'official_listing','official_document','source_check'}.issubset(roles):raise PipelineError('Production origin lacks required actual source evidence')
    if origin.get('editorial_approved_at_generation') is not False or origin.get('publication_authorized') is not False:raise PipelineError('Production origin cannot manufacture approval/publication')
    return True

"""Copy-on-repair of a proven citation-only defect; never change speech or media."""
import copy
import re
import shutil
import tempfile
from pathlib import Path
from .common import ROOT,PipelineError,read_json,write_json,sha256_file,sha256_bytes,utc_now
from .packages import verify_package
from .claims import validate_script

def repair_citations(directory,out_root=None):
    source=Path(directory).resolve();check=verify_package(source)
    allowed=re.compile(r'Script claims: segment \d+: cost match assertion lacks cited cost_sharing claim')
    if check['pass']:return {'changed':False,'directory':str(source),'reason':'No citation defect'}
    if not check['errors'] or any(not allowed.fullmatch(e) for e in check['errors']):
        raise PipelineError('Repair refused: package has errors beyond the known citation-only defect')
    script=read_json(source/'script.json');ledger=read_json(source/'claims.json')['claims']
    proposed=copy.deepcopy(script);changes=[]
    for segment in proposed['segments']:
        text=segment['voiceover']+' '+' '.join(str(v) for v in segment.get('on_screen',{}).values())
        if re.search(r'\bcost\s+(?:match|sharing)\s+(?:is\s+)?(?:not\s+)?required',text,re.I) and 'cost_sharing' not in segment['claim_keys']:
            changes.append({'segment_id':segment['id'],'before':list(segment['claim_keys']),'after':segment['claim_keys']+['cost_sharing']})
            segment['claim_keys'].append('cost_sharing')
    if not changes or validate_script(proposed,ledger):
        raise PipelineError('Repair refused: adding the existing citation does not fully ground the unchanged script')
    stripped=lambda s:[{k:v for k,v in x.items() if k!='claim_keys'} for x in s['segments']]
    if stripped(script)!=stripped(proposed):raise PipelineError('Repair must not alter spoken/on-screen content')
    manifest=read_json(source/'package_manifest.json');media=read_json(source/'media_manifest.json')
    old_id=manifest['package_id'];out_root=Path(out_root or ROOT/'runs/repairs').resolve()
    if out_root.is_relative_to(source):raise PipelineError('Repair output must be outside original package')
    out_root.mkdir(parents=True,exist_ok=True)
    destination=out_root/(source.name+'_citation_'+old_id[:12])
    if destination.exists():raise PipelineError('Repair destination exists; preserved without overwrite')
    temporary=Path(tempfile.mkdtemp(prefix='_incomplete_repair_',dir=out_root))
    try:
        names={str(e['path']).replace('\\','/') for e in manifest['files']+media['files']}
        names.update(('package_manifest.json','result.json'))
        if (source/'REVIEW.md').is_file():names.add('REVIEW.md')
        for name in sorted(names):
            target=temporary/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
        write_json(temporary/'script.json',proposed)
        from .pipeline import script_md
        record=read_json(source/'topic.json')['selected']
        (temporary/'script.md').write_text(script_md(proposed,ledger,record),encoding='utf-8')
        modified={x['segment_id']:x['after'] for x in changes}
        visual=read_json(temporary/'visual_plan.json')
        for segment in visual['segments']:
            if segment['id'] in modified:segment['claim_keys']=modified[segment['id']]
        write_json(temporary/'visual_plan.json',visual)
        if (temporary/'storyboard.json').is_file():
            board=read_json(temporary/'storyboard.json')
            claim=next(c for c in ledger if c['key']=='cost_sharing')
            for scene in board.get('scenes',[]):
                if scene['id'] in modified:
                    scene['claim_keys']=modified[scene['id']]
                    if claim['source'] not in scene.get('sources',[]):scene.setdefault('sources',[]).append(claim['source'])
            write_json(temporary/'storyboard.json',board)
        repair={'schema':'SOCIAL_CITATION_REPAIR_V1','repaired_at':utc_now().isoformat(),
                'original_package_id':old_id,'changes':changes,'spoken_content_changed':False,
                'media_changed':False,'current_source_refetched':False,'editorial_approval_required':True,
                'note':'Historical technical checks retained; current sources and new editorial approval required'}
        write_json(temporary/'citation_repair.json',repair)
        manifest['files'].append({'path':'citation_repair.json'})
        for entry in manifest['files']:
            p=temporary/entry['path'];entry.update(bytes=p.stat().st_size,sha256=sha256_file(p))
        identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in manifest['files']).encode())
        manifest['package_id']=identity;manifest['lineage'].update(package_id=identity,script_sha256=sha256_file(temporary/'script.json'))
        write_json(temporary/'package_manifest.json',manifest)
        result=read_json(temporary/'result.json');result.update(package_id=identity,editorial_approval_required=True)
        result.setdefault('log',{})['citation_repair']=repair
        write_json(temporary/'result.json',result)
        if (temporary/'REVIEW.md').exists():
            text=(temporary/'REVIEW.md').read_text(encoding='utf-8')
            text=text.replace(old_id,identity)
            (temporary/'REVIEW.md').write_text('Citation metadata repaired; fresh official-source check and NEW editorial approval required.\n\n'+text,encoding='utf-8')
        for entry in media['files']:
            if sha256_file(temporary/entry['path'])!=entry['sha256']:raise PipelineError('Repair altered media')
        verified=verify_package(temporary)
        if not verified['pass']:raise PipelineError('Repaired package failed verification: '+'; '.join(verified['errors']))
        temporary.rename(destination)
    except Exception:
        # Preserve only our failed work for diagnosis; never delete or replace user files.
        raise
    return {'changed':True,'directory':str(destination),'original_package_id':old_id,'package_id':identity,
            'media_changed':False,'spoken_content_changed':False,'editorial_approval_required':True,
            'ready_for_current_use':False,'changes':changes}

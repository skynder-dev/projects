"""Standalone DRAFT byte-integrity checker. Never asserts current official conditions."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

def entry_errors(files):
    errors=[];seen=set()
    if not isinstance(files,list) or not 1<=len(files)<=2048:return ['Draft manifest needs1..2048 entries']
    for entry in files:
        if not isinstance(entry,dict):errors.append('Draft entry must be an object');continue
        name=entry.get('path');size=entry.get('bytes');digest=entry.get('sha256')
        if not isinstance(name,str) or not name or len(name)>512:
            errors.append('Invalid draft path');continue
        parts=name.split('/')
        devices={'con','prn','aux','nul'}|{'com'+str(n) for n in range(1,10)}|{'lpt'+str(n) for n in range(1,10)}
        if any(p.split('.')[0].casefold() in devices for p in parts):errors.append('Reserved Windows device path: '+name)
        if ('\\' in name or ':' in name or name.startswith('/') or any(p in ('','.', '..') for p in parts)
                or str(PurePosixPath(name))!=name or any(ord(c)<32 for c in name)
                or any(p.endswith((' ','.')) for p in parts)
                or name.casefold() in {'prepared.json','check_draft.py','draft_export.json'}):
            errors.append('Unsafe/noncanonical/reserved draft path: '+name)
        if name.casefold() in {'audio/narration.wav','subtitles.srt','subtitles.vtt','asr.json','timing.json','final/reel.mp4'}:errors.append('Ungenerated source draft contains generated-media stage output: '+name)
        if name.casefold() in seen:errors.append('Duplicate/case-alias draft path: '+name)
        seen.add(name.casefold())
        if type(size) is not int or size<0:errors.append('Invalid draft byte size: '+name)
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):errors.append('Invalid draft hash: '+name)
    return errors

def check(directory):
    root=Path(directory).resolve();errors=[];as_of=None
    try:
        manifest=json.loads((root/'prepared.json').read_text(encoding='utf-8'))
        if manifest.get('schema')!='SOCIAL_PREPARATION_V1' or manifest.get('accepted') is not False or manifest.get('model_execution_started') is not False:
            errors.append('Invalid draft contract/state')
        files=manifest.get('files') or []
        manifest_errors=entry_errors(files)
        if manifest_errors:return {'artifact_type':'draft_source_and_plan','integrity_pass':False,'errors':manifest_errors,'accepted':False,'current_status_confirmed':False,'ready_for_current_use':False,'scope':'Invalid manifest; no referenced inputs opened'}
        required={'sources.json','topic.json','claims.json','script.json','storyboard.json','preparation_config.json','production_plan.json'}
        if not required.issubset({e['path'] for e in files}):errors.append('Required draft inputs missing')
        for entry in files:
            path=(root/entry['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size!=entry['bytes']:
                errors.append('Missing or unsafe input: '+entry['path']);continue
            if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:errors.append('Changed input: '+entry['path'])
        identity=hashlib.sha256('\n'.join(e['path']+' '+e['sha256'] for e in files).encode()).hexdigest()
        if identity!=manifest.get('preparation_id'):errors.append('Draft identity mismatch')
        as_of=json.loads((root/'sources.json').read_text(encoding='utf-8')).get('selected_snapshot',{}).get('fetched_at')
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:errors.append(type(error).__name__+': '+str(error)[:200])
    return {'artifact_type':'draft_source_and_plan','integrity_pass':not errors,'errors':errors,'source_as_of':as_of,
            'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'accepted':False,'current_status_confirmed':False,
            'ready_for_current_use':False,'scope':'Byte integrity only; draft is not generated media or current official-source approval'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',nargs='?',default=str(Path(__file__).resolve().parent))
    result=check(parser.parse_args().directory);print(json.dumps(result,indent=2));return 0 if result['integrity_pass'] else 2
if __name__=='__main__':raise SystemExit(main())

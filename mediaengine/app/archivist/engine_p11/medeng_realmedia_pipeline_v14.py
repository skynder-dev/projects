#!/usr/bin/env python3
"""
MediaEngine Real-Media Pipeline V14.

V14 keeps V13's one-command local discovery+preview workflow and fixes corrupt
completed-item handling so one damaged resume item cannot abort the whole batch.
Optional repair quarantines the corrupt generated item before rebuilding it.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, time
from pathlib import Path

from medeng_batch_supervisor_v10 import run_one
from medeng_event_export_v12 import load_discovery, cluster_events, export_one

CANDIDATE='MEDENG_REALMEDIA_PIPELINE_V14'


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def safe_name(path: Path, sha: str) -> str:
    s=re.sub(r'[^A-Za-z0-9._-]+','_',path.name)[:100] or 'media'
    return f'{s}__{sha[:12]}'


def atomic_json(path: Path, obj):
    tmp=path.with_name(path.name+'.part')
    tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    os.replace(tmp,path)


def validate_completed(final_dir: Path, source: Path, source_sha: str):
    rp=final_dir/'PIPELINE_RESULT.json'
    if not rp.is_file(): raise RuntimeError('RESUME_RESULT_MISSING')
    obj=json.loads(rp.read_text(encoding='utf-8'))
    if obj.get('candidate')!=CANDIDATE: raise RuntimeError('RESUME_CANDIDATE_MISMATCH')
    if obj.get('source_sha256')!=source_sha: raise RuntimeError('RESUME_SOURCE_SHA_MISMATCH')
    if Path(obj.get('source','')).resolve()!=source.resolve(): raise RuntimeError('RESUME_SOURCE_PATH_MISMATCH')
    if obj.get('selection_claim') is not False: raise RuntimeError('RESUME_SELECTION_CLAIM_INVALID')
    clips=obj.get('clips') or []
    if not clips: raise RuntimeError('RESUME_NO_CLIPS')
    for c in clips:
        p=final_dir/c['relative_path']
        if not p.is_file(): raise RuntimeError(f'RESUME_CLIP_MISSING:{c["relative_path"]}')
        if p.stat().st_size!=int(c['bytes']): raise RuntimeError(f'RESUME_CLIP_SIZE_MISMATCH:{c["relative_path"]}')
        if sha256_file(p)!=c['sha256']: raise RuntimeError(f'RESUME_CLIP_SHA_MISMATCH:{c["relative_path"]}')
    return obj


def prepare_work(root: Path, item_name: str, source: Path, source_sha: str):
    final=root/'items'/item_name; part=root/'items'/('.'+item_name+'.part')
    if final.exists(): return final,part,'final_exists'
    if part.exists():
        intent=part/'RUN_INTENT.json'; same=False
        if intent.is_file():
            try:
                o=json.loads(intent.read_text())
                same=(o.get('candidate')==CANDIDATE and o.get('source_sha256')==source_sha and Path(o.get('source','')).resolve()==source.resolve())
            except Exception: same=False
        if not same: raise RuntimeError(f'FOREIGN_STALE_PART:{part}')
        shutil.rmtree(part)
    part.mkdir(parents=True,exist_ok=False)
    atomic_json(part/'RUN_INTENT.json',{'candidate':CANDIDATE,'source':str(source),'source_sha256':source_sha})
    return final,part,'new'


def quarantine_completed(root: Path, final: Path, item_name: str, reason: str):
    qroot=root/'quarantine'; qroot.mkdir(parents=True,exist_ok=True)
    n=1
    while True:
        dest=qroot/f'{item_name}.corrupt.{n:03d}'
        if not dest.exists(): break
        n+=1
    os.replace(final,dest)
    atomic_json(dest/'QUARANTINE_REASON.json',{
        'candidate':CANDIDATE,'reason':reason,'original_item_name':item_name,
        'repair_action':'QUARANTINE_THEN_REBUILD_GENERATED_OUTPUT'
    })
    return dest


def run_source(source: Path, root: Path, timeout_s: float, ffmpeg: str, ffprobe: str,
               max_width: int, repair_corrupt_completed: bool):
    started=time.perf_counter(); source=source.resolve()
    if not source.is_file(): return {'source':str(source),'status':'missing','retry_count':0}
    sha=sha256_file(source); item=safe_name(source,sha); quarantine=None
    try:
        final,work,state=prepare_work(root,item,source,sha)
    except Exception as e:
        return {'source':str(source),'source_sha256':sha,'status':'preflight_failed','error':f'{type(e).__name__}:{e}','retry_count':0,'elapsed_s':round(time.perf_counter()-started,3)}

    if state=='final_exists':
        try:
            obj=validate_completed(final,source,sha)
            return {'source':str(source),'source_sha256':sha,'status':'skipped_exact_completed','item_dir':str(final),'clip_count':len(obj['clips']),'retry_count':0,'elapsed_s':round(time.perf_counter()-started,3)}
        except Exception as e:
            reason=f'{type(e).__name__}:{e}'
            if not repair_corrupt_completed:
                return {'source':str(source),'source_sha256':sha,'status':'corrupt_completed','item_dir':str(final),'error':reason,'repair_available':True,'retry_count':0,'elapsed_s':round(time.perf_counter()-started,3)}
            try:
                quarantine=quarantine_completed(root,final,item,reason)
                final,work,state=prepare_work(root,item,source,sha)
            except Exception as qe:
                return {'source':str(source),'source_sha256':sha,'status':'repair_preflight_failed','error':f'{type(qe).__name__}:{qe}','original_corruption':reason,'retry_count':0,'elapsed_s':round(time.perf_counter()-started,3)}

    try:
        discovery=work/'discovery'; discovery.mkdir()
        engine=Path(__file__).resolve().parent/'medeng_event_semantic_v7.py'
        dres=run_one(engine,source,discovery,'DISCOVER_EVENTS','FAST_LOCAL','',ffmpeg,ffprobe,timeout_s)
        if dres.get('status')!='passed':
            raise RuntimeError('DISCOVERY_'+str(dres.get('status')).upper()+':'+json.dumps(dres,sort_keys=True))
        event_path=Path(dres['result_path']); _,events=load_discovery(event_path,source); clusters=cluster_events(events,.25)
        clip_dir=work/'previews'/source.name; clip_dir.mkdir(parents=True)
        clips=[]
        for c in clusters:
            x=export_one(source,c,clip_dir,ffmpeg,ffprobe,max_width); p=Path(x['output_path'])
            x['relative_path']=str(p.relative_to(work)).replace('\\','/'); x.pop('output_path',None); clips.append(x)
        result={'candidate':CANDIDATE,'source':str(source),'source_size_bytes':source.stat().st_size,'source_sha256':sha,
          'mode':'DISCOVER_EVENTS_PLUS_TECHNICAL_REPRESENTATIVE_EXPORT','selection_claim':False,
          'representative_claim':'TECHNICAL_EVENT_REPRESENTATIVE_ONLY','network_during_analysis':False,'source_mutated':False,
          'discovery_event_count':len(events),'event_cluster_count':len(clusters),'clip_count':len(clips),
          'discovery_scout_elapsed_s':dres.get('scout_elapsed_s'),'clips':clips,'retry_count':0,
          'repair_from_quarantine':str(quarantine) if quarantine else None,
          'elapsed_s':round(time.perf_counter()-started,3),'verdict':'PASS'}
        atomic_json(work/'PIPELINE_RESULT.json',result); os.replace(work,final); validate_completed(final,source,sha)
        return {'source':str(source),'source_sha256':sha,'status':'passed','item_dir':str(final),'clip_count':len(clips),'event_count':len(events),'repaired_corrupt_completed':quarantine is not None,'quarantine_dir':str(quarantine) if quarantine else None,'elapsed_s':round(time.perf_counter()-started,3),'retry_count':0}
    except Exception as e:
        shutil.rmtree(work,ignore_errors=True)
        return {'source':str(source),'source_sha256':sha,'status':'failed','error':f'{type(e).__name__}:{e}','quarantine_dir':str(quarantine) if quarantine else None,'retry_count':0,'elapsed_s':round(time.perf_counter()-started,3)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('videos',nargs='+'); ap.add_argument('--output-root',required=True)
    ap.add_argument('--per-file-timeout-s',type=float,default=30.0); ap.add_argument('--max-width',type=int,default=960)
    ap.add_argument('--ffmpeg',default=os.environ.get('MEDENG_FFMPEG','ffmpeg')); ap.add_argument('--ffprobe',default=os.environ.get('MEDENG_FFPROBE','ffprobe'))
    ap.add_argument('--repair-corrupt-completed',action='store_true')
    args=ap.parse_args(); root=Path(args.output_root).resolve(); (root/'items').mkdir(parents=True,exist_ok=True)
    started=time.perf_counter(); results=[]
    for raw in args.videos:
        results.append(run_source(Path(raw),root,args.per_file_timeout_s,args.ffmpeg,args.ffprobe,args.max_width,args.repair_corrupt_completed))
    passed=sum(r['status'] in ('passed','skipped_exact_completed') for r in results)
    agg={'candidate':CANDIDATE,'selection_claim':False,'network_during_analysis':False,'retry_policy':'NONE',
         'repair_corrupt_completed':bool(args.repair_corrupt_completed),'total':len(results),'passed_or_resumed':passed,
         'failed':len(results)-passed,'elapsed_s':round(time.perf_counter()-started,3),'results':results,
         'verdict':'PASS' if passed==len(results) else 'PARTIAL_FAILURE'}
    atomic_json(root/'BATCH_RESULT.json',agg); print(json.dumps(agg,indent=2)); raise SystemExit(0 if passed==len(results) else 2)

if __name__=='__main__': main()

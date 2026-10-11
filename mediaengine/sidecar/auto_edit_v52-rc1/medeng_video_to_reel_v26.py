#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
CANDIDATE='MEDENG_VIDEO_TO_REEL_V26_SIDECAR'

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def stage(cmd,timeout):
    t=time.perf_counter(); cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False); elapsed=time.perf_counter()-t
    if cp.returncode: raise RuntimeError(f"STAGE_FAILED rc={cp.returncode}: {' '.join(map(str,cmd))}\nSTDOUT:\n{cp.stdout[-12000:]}\nSTDERR:\n{cp.stderr[-5000:]}")
    return {'elapsed_s':round(elapsed,3),'stdout_tail':cp.stdout[-3000:]}

def main():
    ap=argparse.ArgumentParser(description='Raw local videos -> events -> preview library -> targeted finished reels.')
    ap.add_argument('videos',nargs='+'); ap.add_argument('--output-root',required=True); ap.add_argument('--per-file-timeout-s',type=float,default=180); ap.add_argument('--max-width',type=int,default=960); ap.add_argument('--target-seconds',type=float,default=30); ap.add_argument('--clip-seconds',type=float,default=5); ap.add_argument('--transition',type=float,default=.25); ap.add_argument('--repair-corrupt-completed',action='store_true'); a=ap.parse_args()
    here=Path(__file__).resolve().parent; root=Path(a.output_root).resolve(); root.mkdir(parents=True,exist_ok=True); videos=[str(Path(v).resolve()) for v in a.videos]
    pipe=root/'local_pipeline'; lib=root/'event_library'; edit=root/'target_auto_edit_polish'; started=time.perf_counter()
    c1=[sys.executable,str(here/'medeng_realmedia_pipeline_v14.py'),'--output-root',str(pipe),'--per-file-timeout-s',str(a.per_file_timeout_s),'--max-width',str(a.max_width)]
    if a.repair_corrupt_completed:c1.append('--repair-corrupt-completed')
    c1+=videos; s1=stage(c1,max(300,int(a.per_file_timeout_s*len(videos)+180)))
    batch=json.loads((pipe/'BATCH_RESULT.json').read_text()); bad=[x for x in batch.get('results',[]) if x.get('status') not in ('passed','skipped_exact_completed')]
    if bad: raise RuntimeError('LOCAL_PIPELINE_NOT_ALL_PASS:'+json.dumps(bad,sort_keys=True))
    s2=stage([sys.executable,str(here/'medeng_event_library_v20.py'),str(pipe),'--output-dir',str(lib)],300)
    libp=lib/'EVENT_LIBRARY.json'; lo=json.loads(libp.read_text());
    if lo.get('verdict')!='PASS': raise RuntimeError('EVENT_LIBRARY_NOT_PASS')
    s3=stage([sys.executable,str(here/'medeng_targeted_auto_edit_v26.py'),'--event-library',str(libp),'--outdir',str(edit),'--target-seconds',str(a.target_seconds),'--clip-seconds',str(a.clip_seconds),'--transition',str(a.transition)],600)
    man=json.loads((edit/'AUTO_EDIT_V26_MANIFEST.json').read_text()); outputs=[]
    for o in man['outputs']:
        p=Path(o['path']); outputs.append({'profile':o['profile'],'path':str(p),'bytes':p.stat().st_size,'sha256':sha256_file(p),'expected_duration_s':o['expected_duration_s']})
    result={'candidate':CANDIDATE,'schema_version':1,'status':'PASS','semantic_model_used':False,'semantic_selection_claim':False,'target_duration_s':a.target_seconds,'input_count':len(videos),'inputs':videos,'event_count':lo['event_count'],'selected_count':len(man['selected_events']),'selected_sources':[x['source_name'] for x in man['selected_events']],'stage_elapsed_s':{'discover_export':s1['elapsed_s'],'event_library':s2['elapsed_s'],'target_auto_edit':s3['elapsed_s']},'total_elapsed_s':round(time.perf_counter()-started,3),'outputs':outputs,'audio_policy':'LOCAL_ORIGINAL_AMBIENCE_OR_GENERATED_SILENCE_ONLY','presentation_policy':'16x9_SOFT_LOCAL_BACKGROUND_WHEN_NEEDED__9x16_SMART_SALIENCY_CROP','external_audio_used':False,'limitations':['Generic aesthetic/technical AUTO_EDIT is functional end-to-end but is not a semantic best-moment claim.','Only original local source ambience is preserved; silent sources receive generated silence. No external music is introduced.']}
    (root/'VIDEO_TO_REEL_V26_RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__':main()

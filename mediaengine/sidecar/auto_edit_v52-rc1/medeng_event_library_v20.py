#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, os, subprocess
from pathlib import Path
from medeng_media_probe_v41 import probe_json as media_probe_json

CANDIDATE='MEDENG_EVENT_LIBRARY_V20'
ALLOWED={'MEDENG_EVENT_EXPORT_V12','MEDENG_REALMEDIA_PIPELINE_V14'}

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def canonical_sha(entries):
    return hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def probe(path:Path,ffprobe='ffprobe'):
    return media_probe_json(path, os.environ.get('MEDENG_FFMPEG','ffmpeg'), 30)

def verify_source(src:Path,o:dict,enabled=True):
    if not enabled: return
    if not src.is_file(): raise RuntimeError('SOURCE_MISSING:'+str(src))
    if src.stat().st_size!=int(o['source_size_bytes']): raise RuntimeError('SOURCE_SIZE_MISMATCH:'+str(src))
    if sha256_file(src)!=o['source_sha256']: raise RuntimeError('SOURCE_SHA_MISMATCH:'+str(src))

def entry_from_clip(o:dict, src:Path, cp:Path, c:dict, result_file:Path, ffprobe='ffprobe'):
    if not cp.is_file(): raise RuntimeError('CLIP_MISSING:'+str(cp))
    if cp.stat().st_size!=int(c['bytes']): raise RuntimeError('CLIP_SIZE_MISMATCH:'+str(cp))
    if sha256_file(cp)!=c['sha256']: raise RuntimeError('CLIP_SHA_MISMATCH:'+str(cp))
    po=probe(cp,ffprobe)
    vd=[s for s in po.get('streams',[]) if s.get('codec_type')=='video']
    if not vd: raise RuntimeError('CLIP_VIDEO_STREAM_MISSING:'+str(cp))
    start=float(c['start_s']); end=float(c['end_s'])
    material='|'.join([o['source_sha256'],f'{start:.6f}',f'{end:.6f}',c['sha256']])
    eid=hashlib.sha256(material.encode()).hexdigest()[:24]
    return {
      'event_id':eid,'source_name':src.name,'source_path':str(src),'source_sha256':o['source_sha256'],
      'source_size_bytes':int(o['source_size_bytes']),'event_manifest':str(result_file.resolve()),
      'event_manifest_candidate':o['candidate'],'cluster_index':int(c['cluster_index']),
      'cluster_start_s':float(c['cluster_start_s']),'cluster_end_s':float(c['cluster_end_s']),
      'start_s':start,'end_s':end,'duration_s':float(c.get('duration_s') or c.get('expected_duration_s') or (end-start)),
      'technical_prominence':float(c['technical_prominence']),'clip_path':str(cp.resolve()),
      'clip_bytes':int(c['bytes']),'clip_sha256':c['sha256'],'video_codec':c.get('video_codec'),
      'width':c.get('width'),'height':c.get('height'),'r_frame_rate':c.get('r_frame_rate'),
      'selection_claim':False,'semantic_status':'UNRANKED','eligible_for_select_best':True,
    }

def load_result(p:Path,verify_source_hash=True,ffprobe='ffprobe'):
    o=json.loads(p.read_text(encoding='utf-8'))
    cand=o.get('candidate')
    if cand not in ALLOWED: raise RuntimeError('RESULT_CANDIDATE_REJECTED:'+str(cand))
    if o.get('selection_claim') is not False: raise RuntimeError('RESULT_SELECTION_CLAIM_INVALID')
    if o.get('representative_claim')!='TECHNICAL_EVENT_REPRESENTATIVE_ONLY': raise RuntimeError('RESULT_REPRESENTATIVE_CLAIM_INVALID')
    if o.get('verdict')!='PASS': raise RuntimeError('RESULT_NOT_PASS')
    src=Path(o['source']).resolve(); verify_source(src,o,verify_source_hash)
    entries=[]
    for c in o.get('clips') or []:
        if cand=='MEDENG_EVENT_EXPORT_V12':
            cp=Path(c['output_path']).resolve()
        else:
            cp=(p.parent/c['relative_path']).resolve()
        entries.append(entry_from_clip(o,src,cp,c,p,ffprobe))
    if not entries: raise RuntimeError('RESULT_NO_CLIPS:'+str(p))
    return entries

def atomic_json(path:Path,obj):
    tmp=path.with_name(path.name+'.part'); tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8'); os.replace(tmp,path)

def discover_results(roots):
    found=[]
    for raw in roots:
        p=Path(raw)
        if p.is_file(): found.append(p)
        elif p.is_dir():
            found.extend(p.rglob('EVENT_EXPORT_MANIFEST.json'))
            found.extend(p.rglob('PIPELINE_RESULT.json'))
        else: raise RuntimeError('INPUT_MISSING:'+raw)
    return sorted(set(x.resolve() for x in found))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('roots',nargs='+'); ap.add_argument('--output-dir',required=True); ap.add_argument('--ffprobe',default=os.environ.get('MEDENG_FFPROBE','ffprobe')); ap.add_argument('--skip-source-rehash',action='store_true'); a=ap.parse_args()
    results=discover_results(a.roots)
    if not results: raise SystemExit('NO_RESULTS')
    entries=[]
    for p in results: entries.extend(load_result(p,not a.skip_source_rehash,a.ffprobe))
    ids=[x['event_id'] for x in entries]
    if len(ids)!=len(set(ids)): raise RuntimeError('DUPLICATE_EVENT_ID')
    entries=sorted(entries,key=lambda x:(x['source_sha256'],x['start_s'],x['end_s'],x['event_id']))
    source_shas=sorted(set(x['source_sha256'] for x in entries)); total_bytes=sum(x['clip_bytes'] for x in entries); content_sha=canonical_sha(entries)
    out=Path(a.output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    lib={'candidate':CANDIDATE,'schema_version':2,'selection_claim':False,'semantic_status':'UNRANKED','source_count':len(source_shas),'event_count':len(entries),'clip_bytes_total':total_bytes,'event_content_sha256':content_sha,'manifests':[str(p) for p in results],'verification':{'clip_hashes':True,'clip_ffprobe':False,'clip_probe_backend':'FFMPEG_INPUT_METADATA_V41','source_hashes':not a.skip_source_rehash},'events':entries,'verdict':'PASS'}
    atomic_json(out/'EVENT_LIBRARY.json',lib)
    cols=['event_id','source_name','source_sha256','start_s','end_s','duration_s','technical_prominence','clip_path','clip_bytes','clip_sha256','semantic_status','eligible_for_select_best']
    tmp=out/'EVENT_LIBRARY.csv.part'
    with tmp.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows({k:e.get(k) for k in cols} for e in entries)
    os.replace(tmp,out/'EVENT_LIBRARY.csv')
    print(json.dumps({k:lib[k] for k in ('candidate','source_count','event_count','clip_bytes_total','event_content_sha256','verdict')},indent=2))
if __name__=='__main__': main()

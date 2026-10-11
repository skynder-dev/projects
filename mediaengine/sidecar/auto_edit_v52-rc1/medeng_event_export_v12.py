#!/usr/bin/env python3
"""
MediaEngine Event Export V12.

Exports technically representative windows from V7 DISCOVER_EVENTS output.
This is event deduplication, NOT semantic best-moment selection.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path
from medeng_media_probe_v41 import probe_json as media_probe_json


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def safe_stem(name: str) -> str:
    return (re.sub(r'[^A-Za-z0-9._-]+','_',name)[:120] or 'media')


def load_discovery(path: Path, source: Path):
    obj=json.loads(path.read_text(encoding='utf-8'))
    if obj.get('candidate')!='MEDENG_EVENT_SEMANTIC_V7':
        raise RuntimeError('EVENT_SOURCE_CANDIDATE_MISMATCH')
    if obj.get('mode')!='DISCOVER_EVENTS' or obj.get('selection_claim') is not False:
        raise RuntimeError('EVENT_SOURCE_NOT_DISCOVERY_ONLY')
    reports=obj.get('reports')
    if not isinstance(reports,list) or len(reports)!=1:
        raise RuntimeError('EVENT_SOURCE_REPORT_COUNT')
    r=reports[0]
    if r.get('mode')!='DISCOVER_EVENTS' or r.get('selection_claim') is not False:
        raise RuntimeError('EVENT_REPORT_NOT_DISCOVERY_ONLY')
    if Path(r.get('video','')).resolve()!=source.resolve():
        raise RuntimeError('EVENT_SOURCE_VIDEO_IDENTITY_MISMATCH')
    events=r.get('events')
    if not isinstance(events,list) or not events:
        raise RuntimeError('EVENT_SOURCE_EMPTY')
    clean=[]
    for i,e in enumerate(events,1):
        s=float(e['start_s']); t=float(e['end_s'])
        if not (0<=s<t): raise RuntimeError(f'INVALID_EVENT_INTERVAL:{i}')
        clean.append({**e,'start_s':s,'end_s':t})
    return r,sorted(clean,key=lambda x:(x['start_s'],x['end_s']))


def cluster_events(events, max_gap_s=0.25):
    clusters=[]; cur=[]; right=None
    for e in events:
        if not cur or e['start_s']<=float(right)+float(max_gap_s):
            cur.append(e); right=e['end_s'] if right is None else max(float(right),e['end_s'])
        else:
            clusters.append(cur); cur=[e]; right=e['end_s']
    if cur: clusters.append(cur)
    out=[]
    for idx,c in enumerate(clusters,1):
        def prominence(e):
            return (.50*float(e.get('event_signal',0)) +
                    .35*float(e.get('novelty_signal',0)) +
                    .15*float(e.get('technical_quality',0)))
        rep=max(c,key=prominence)
        out.append({
            'cluster_index':idx,
            'cluster_start_s':round(min(float(e['start_s']) for e in c),3),
            'cluster_end_s':round(max(float(e['end_s']) for e in c),3),
            'source_window_count':len(c),
            'representative':rep,
            'representative_prominence':round(prominence(rep),6),
            'selection_claim':False,
            'representative_claim':'TECHNICAL_EVENT_REPRESENTATIVE_ONLY',
        })
    return out


def ffprobe_clip(path: Path, ffprobe='ffprobe', ffmpeg='ffmpeg'):
    obj=media_probe_json(path, ffmpeg, 15); st=next((x for x in obj.get('streams',[]) if x.get('codec_type')=='video'),{})
    return {'duration_s':float(obj['format']['duration']),'video_codec':st.get('codec_name'),
            'width':st.get('width'),'height':st.get('height'),'r_frame_rate':st.get('r_frame_rate')}


def export_one(source: Path, cluster: dict, out_dir: Path, ffmpeg='ffmpeg', ffprobe='ffprobe', max_width=960):
    rep=cluster['representative']; s=float(rep['start_s']); e=float(rep['end_s']); dur=e-s
    ms0=int(round(s*1000)); ms1=int(round(e*1000)); ci=int(cluster['cluster_index'])
    base=f'cluster_{ci:03d}_{ms0:08d}_{ms1:08d}'
    final=out_dir/f'{base}.mp4'; part=out_dir/f'{base}.part.mp4'
    if final.exists() or part.exists(): raise RuntimeError(f'OUTPUT_EXISTS:{final.name}')
    src_probe=media_probe_json(source,ffmpeg,15)
    has_audio=any(x.get('codec_type')=='audio' for x in src_probe.get('streams',[]))
    vf=f"setpts=PTS-STARTPTS,scale='min(iw,{int(max_width)})':-2"
    cmd=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n',
         '-ss',f'{s:.3f}','-i',str(source),'-t',f'{dur:.3f}',
         '-map','0:v:0']
    if has_audio:
        cmd += ['-map','0:a:0','-af','asetpts=PTS-STARTPTS']
    cmd += ['-map_metadata','-1','-vf',vf,
         '-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p',
         '-c:a','aac','-b:a','128k','-movflags','+faststart',str(part)]
    t0=time.perf_counter(); cp=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=60)
    elapsed=time.perf_counter()-t0
    if cp.returncode!=0:
        part.unlink(missing_ok=True); raise RuntimeError(f'FFMPEG_EXPORT_FAILED:{ci}:{cp.stderr[-1000:]}')
    if not part.is_file() or part.stat().st_size<1024:
        part.unlink(missing_ok=True); raise RuntimeError(f'EXPORT_MISSING_OR_SMALL:{ci}')
    probe=ffprobe_clip(part,ffprobe,ffmpeg)
    if abs(probe['duration_s']-dur)>max(.35,dur*.06):
        part.unlink(missing_ok=True); raise RuntimeError(f'EXPORT_DURATION_MISMATCH:{ci}')
    os.replace(part,final)
    return {
        'cluster_index':ci,'cluster_start_s':cluster['cluster_start_s'],'cluster_end_s':cluster['cluster_end_s'],
        'source_window_count':cluster['source_window_count'],'start_s':round(s,3),'end_s':round(e,3),
        'expected_duration_s':round(dur,3),'technical_prominence':cluster['representative_prominence'],
        'representative_claim':cluster['representative_claim'],'selection_claim':False,
        'output_path':str(final),'bytes':final.stat().st_size,'sha256':sha256_file(final),
        'encode_elapsed_s':round(elapsed,3),**probe,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True); ap.add_argument('--events-json',required=True)
    ap.add_argument('--output-dir',required=True); ap.add_argument('--expected-source-sha256',default='')
    ap.add_argument('--ffmpeg',default=os.environ.get('MEDENG_FFMPEG','ffmpeg')); ap.add_argument('--ffprobe',default=os.environ.get('MEDENG_FFPROBE','ffprobe'))
    ap.add_argument('--max-width',type=int,default=960); ap.add_argument('--cluster-gap-s',type=float,default=.25)
    args=ap.parse_args()
    source=Path(args.source).resolve(); events_path=Path(args.events_json).resolve(); root=Path(args.output_dir).resolve()
    if not source.is_file(): raise RuntimeError('SOURCE_MISSING')
    source_sha=sha256_file(source)
    if args.expected_source_sha256 and source_sha.lower()!=args.expected_source_sha256.lower():
        raise RuntimeError('SOURCE_SHA256_MISMATCH')
    report,events=load_discovery(events_path,source); clusters=cluster_events(events,args.cluster_gap_s)
    target=root/safe_stem(source.name); target.mkdir(parents=True,exist_ok=True)
    mf=target/'EVENT_EXPORT_MANIFEST.json'; mp=target/'EVENT_EXPORT_MANIFEST.json.part'
    if mf.exists() or mp.exists(): raise RuntimeError('MANIFEST_EXISTS')
    created=[]; t0=time.perf_counter()
    try:
        for c in clusters: created.append(export_one(source,c,target,args.ffmpeg,args.ffprobe,args.max_width))
    except Exception:
        for x in created: Path(x['output_path']).unlink(missing_ok=True)
        for p in target.glob('*.part.mp4'): p.unlink(missing_ok=True)
        raise
    manifest={
      'candidate':'MEDENG_EVENT_EXPORT_V12','mode':'DISCOVER_EVENTS_CLUSTER_REPRESENTATIVE',
      'source':str(source),'source_size_bytes':source.stat().st_size,'source_sha256':source_sha,
      'event_source':str(events_path),'event_source_candidate':'MEDENG_EVENT_SEMANTIC_V7',
      'selection_claim':False,'representative_claim':'TECHNICAL_EVENT_REPRESENTATIVE_ONLY',
      'source_event_window_count':len(events),'cluster_count':len(clusters),'exported_clip_count':len(created),
      'cluster_gap_s':args.cluster_gap_s,'max_width':args.max_width,'network_during_export':False,
      'source_mutated':False,'elapsed_s':round(time.perf_counter()-t0,3),'clips':created,'verdict':'PASS'}
    mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8'); os.replace(mp,mf)
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()

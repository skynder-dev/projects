#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, time, shutil
from pathlib import Path
from itertools import combinations
from collections import Counter
import cv2
import numpy as np
from medeng_media_probe_v41 import probe_json as media_probe_json

CANDIDATE='MEDENG_TARGETED_AUTO_EDIT_V26_SIDECAR'
SCHEMA_VERSION=1
SCORER_VERSION='V22_GENERIC_AESTHETIC_1'
DEFAULT_CLIP_SECONDS=5.0
DEFAULT_TRANSITION_SECONDS=0.25
DEFAULT_AUDIO_LUFS=-18.0
DEFAULT_AUDIO_TRUE_PEAK_DB=-2.0
DEFAULT_VERTICAL_FRAMING='fill'
DEFAULT_VERTICAL_FOCUS_X=0.5
DEFAULT_OUTPUT_RESOLUTION='standard'
DEFAULT_OUTPUT_FPS=30
DEFAULT_VIDEO_QUALITY='standard'
DEFAULT_AUDIO_CONTENT='source'
FFMPEG=os.environ.get('MEDENG_FFMPEG','ffmpeg')

class V22Error(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def run(cmd,timeout=180):
    cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
    if cp.returncode:
        raise V22Error(f"command failed rc={cp.returncode}: {' '.join(map(str,cmd))}\n{cp.stderr[-4000:]}")
    return cp

def ffprobe(path:Path)->dict:
    return media_probe_json(path, FFMPEG, 30)

def full_decode(path:Path):
    run([FFMPEG,'-v','error','-i',str(path),'-f','null','-'],180)

def robust01(vals):
    a=np.asarray(vals,dtype=float)
    lo=float(np.quantile(a,.10)); hi=float(np.quantile(a,.90))
    if not np.isfinite(hi-lo) or hi-lo<1e-9: return np.full_like(a,.5)
    return np.clip((a-lo)/(hi-lo),0,1)

def frame_metrics(frame:np.ndarray)->dict:
    small=cv2.resize(frame,(320,max(90,int(frame.shape[0]*320/frame.shape[1]))),interpolation=cv2.INTER_AREA)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    mean=float(gray.mean()); std=float(gray.std())
    dark=float((gray<16).mean()); bright=float((gray>239).mean())
    exposure=float(np.clip(1.0-abs(mean-128.0)/128.0-0.8*(dark+bright),0,1))
    sharp=float(cv2.Laplacian(gray,cv2.CV_64F).var())
    edge=float((cv2.Canny(gray,80,160)>0).mean())
    hist=cv2.calcHist([gray],[0],None,[64],[0,256]).ravel(); prob=hist/(hist.sum()+1e-9)
    entropy=float(-(prob[prob>0]*np.log2(prob[prob>0])).sum()/6.0)
    B,G,R=[small[:,:,i].astype(np.float32) for i in range(3)]
    rg=R-G; yb=.5*(R+G)-B
    color=float(np.sqrt(np.var(rg)+np.var(yb))+.3*np.sqrt(np.mean(rg)**2+np.mean(yb)**2))
    # Generic saliency proxy: edges + local contrast. Used for composition and smart crop only.
    lap=np.abs(cv2.Laplacian(gray,cv2.CV_32F))
    grad=cv2.magnitude(cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3),cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3))
    sal=lap+0.6*grad
    sal=cv2.GaussianBlur(sal,(0,0),3)
    total=float(sal.sum())
    if total<=1e-6:
        cx=cy=.5
    else:
        yy,xx=np.mgrid[0:sal.shape[0],0:sal.shape[1]]
        cx=float((sal*xx).sum()/total/max(1,sal.shape[1]-1)); cy=float((sal*yy).sum()/total/max(1,sal.shape[0]-1))
    anchors=[(.5,.5),(1/3,1/3),(2/3,1/3),(1/3,2/3),(2/3,2/3)]
    dist=min(math.hypot(cx-x,cy-y) for x,y in anchors)
    composition=float(np.clip(1.0-dist/.45,0,1))
    return dict(exposure=exposure,sharp_raw=sharp,contrast_raw=std,color_raw=color,entropy=entropy,edge_raw=edge,cx=cx,cy=cy)

def sample_clip(path:Path,sample_hz=2.0)->dict:
    cap=cv2.VideoCapture(str(path))
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 30.0); n=float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step=max(1,int(round(fps/sample_hz)))
    rows=[]; diffs=[]; prev=None; idx=0
    while True:
        ok,fr=cap.read()
        if not ok: break
        if idx%step==0:
            m=frame_metrics(fr); rows.append(m)
            gray=cv2.cvtColor(cv2.resize(fr,(160,90),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
            if prev is not None: diffs.append(float(np.mean(cv2.absdiff(gray,prev))/255.0))
            prev=gray
        idx+=1
    cap.release()
    if not rows: raise V22Error('NO_SAMPLE_FRAMES:'+str(path))
    # Ending quality uses final 25% frames; scoring dimensions are normalized across events later.
    tail=rows[max(0,int(len(rows)*.75)):]
    return {
      'frame_count_sampled':len(rows),
      'exposure':float(np.mean([r['exposure'] for r in rows])),
      'sharp_raw':float(np.mean([r['sharp_raw'] for r in rows])),
      'contrast_raw':float(np.mean([r['contrast_raw'] for r in rows])),
      'color_raw':float(np.mean([r['color_raw'] for r in rows])),
      'entropy':float(np.mean([r['entropy'] for r in rows])),
      'edge_raw':float(np.mean([r['edge_raw'] for r in rows])),
      'composition':float(np.mean([frame_metrics_dummy if False else r['exposure']*0 + (1.0-min(math.hypot(r['cx']-x,r['cy']-y) for x,y in [(.5,.5),(1/3,1/3),(2/3,1/3),(1/3,2/3),(2/3,2/3)])/.45) for r in rows])),
      'saliency_cx':float(np.median([r['cx'] for r in rows])),
      'saliency_cy':float(np.median([r['cy'] for r in rows])),
      'tail_exposure':float(np.mean([r['exposure'] for r in tail])),
      'tail_sharp_raw':float(np.mean([r['sharp_raw'] for r in tail])),
      'motion_diff_raw':float(np.mean(diffs) if diffs else 0.0),
    }

def load_library(path:Path)->tuple[dict,list[dict]]:
    obj=json.loads(path.read_text(encoding='utf-8'))
    if obj.get('selection_claim') is not False or obj.get('verdict')!='PASS': raise V22Error('EVENT_LIBRARY_INVALID')
    events=[]
    for e in obj.get('events') or []:
        if not e.get('eligible_for_select_best',False): continue
        p=Path(e['clip_path'])
        if not p.is_file(): raise V22Error('EVENT_CLIP_MISSING:'+str(p))
        if p.stat().st_size!=int(e['clip_bytes']) or sha256_file(p)!=e['clip_sha256']: raise V22Error('EVENT_CLIP_IDENTITY_MISMATCH:'+str(p))
        events.append(dict(e))
    if len(events)<1: raise V22Error('NO_ELIGIBLE_EVENTS')
    return obj,events

def score_events(events:list[dict],cache_path:Path)->list[dict]:
    cache={}
    if cache_path.is_file():
        try:
            o=json.loads(cache_path.read_text(encoding='utf-8'))
            if o.get('scorer_version')==SCORER_VERSION: cache=o.get('events') or {}
        except Exception: cache={}
    raw=[]; changed=False
    for e in events:
        key=e['event_id']; cached=cache.get(key)
        if cached and cached.get('clip_sha256')==e['clip_sha256']:
            m=dict(cached['metrics'])
        else:
            m=sample_clip(Path(e['clip_path'])); cache[key]={'clip_sha256':e['clip_sha256'],'metrics':m}; changed=True
        raw.append((e,m))
    # Normalize comparative dimensions only after all events are sampled.
    sharp=robust01([m['sharp_raw'] for _,m in raw]); contrast=robust01([m['contrast_raw'] for _,m in raw])
    color=robust01([m['color_raw'] for _,m in raw]); edge=robust01([m['edge_raw'] for _,m in raw]); tailsharp=robust01([m['tail_sharp_raw'] for _,m in raw])
    motion=robust01([m['motion_diff_raw'] for _,m in raw])
    out=[]
    for i,(e,m) in enumerate(raw):
        stability=float(np.clip(1.0-abs(float(motion[i])-.42)/.58,0,1))
        ending=.55*float(m['tail_exposure'])+.45*float(tailsharp[i])
        comp=float(np.clip(m['composition'],0,1))
        score=(.35*float(e['technical_prominence']) + .12*m['exposure'] + .12*float(sharp[i]) + .08*float(contrast[i]) + .08*float(color[i]) + .06*m['entropy'] + .08*comp + .06*ending + .05*stability)
        z=dict(e)
        z['v22_score']=round(float(score),6); z['v22_metrics']={**m,'sharp_n':float(sharp[i]),'contrast_n':float(contrast[i]),'color_n':float(color[i]),'edge_n':float(edge[i]),'ending_quality':float(ending),'stability':stability}
        out.append(z)
    cache_obj={'candidate':CANDIDATE,'scorer_version':SCORER_VERSION,'events':cache}
    tmp=cache_path.with_suffix(cache_path.suffix+'.part'); tmp.parent.mkdir(parents=True,exist_ok=True); tmp.write_text(json.dumps(cache_obj,indent=2),encoding='utf-8'); os.replace(tmp,cache_path)
    return out

def diversity_priority(events:list[dict])->list[dict]:
    groups={}
    for e in sorted(events,key=lambda x:(-x['v22_score'],x['event_id'])): groups.setdefault(e['source_sha256'],[]).append(e)
    first=sorted((xs[0] for xs in groups.values()),key=lambda x:(-x['v22_score'],x['source_name']))
    rest=sorted((e for xs in groups.values() for e in xs[1:]),key=lambda x:(-x['v22_score'],x['source_name']))
    return first+rest

def used_duration(e,clip_seconds): return min(float(clip_seconds),float(e.get('duration_s') or (float(e['end_s'])-float(e['start_s']))))

def expected_duration(prefix:list[dict],clip_seconds,transition):
    if not prefix:return 0.0
    return sum(used_duration(e,clip_seconds) for e in prefix)-transition*max(0,len(prefix)-1)

def choose_for_target(events:list[dict],target,clip_seconds,transition,max_events=30)->list[dict]:
    ranked=sorted(events,key=lambda x:(-x['v22_score'],x['source_name'],x['event_id']))[:max_events]
    if len(ranked)<1: raise V22Error('NO_RANKED_EVENTS')
    if len(ranked)==1: return ranked
    sources=sorted(set(e['source_sha256'] for e in ranked)); total_sources=len(sources)
    nominal=max(1,int(round((target-transition)/max(.1,clip_seconds-transition))))
    sizes=range(max(1,nominal-2),min(len(ranked),nominal+2)+1)
    best=None
    for n in sizes:
        for combo in combinations(ranked,n):
            counts=Counter(e['source_sha256'] for e in combo); unique=len(counts)
            # Generic diversity rule: short reels use distinct sources; long reels include every available source.
            if n<=total_sources and unique!=n: continue
            if n>total_sources and unique!=total_sources: continue
            dur=expected_duration(list(combo),clip_seconds,transition)
            dur_err=abs(dur-target)
            quality=sum(e['v22_score'] for e in combo)/n
            repeat_pen=sum(max(0,c-1)**2 for c in counts.values())/max(1,n-1)
            # discourage multiple neighboring events from the same source
            near=0.0
            by={}
            for e in combo: by.setdefault(e['source_sha256'],[]).append(e)
            for xs in by.values():
                xs=sorted(xs,key=lambda e:float(e['start_s']))
                for a,b in zip(xs,xs[1:]):
                    gap=float(b['start_s'])-float(a['end_s'])
                    if gap<5.0: near += (5.0-max(0.0,gap))/5.0
            objective=quality - .45*(dur_err/max(1.0,clip_seconds)) - .10*repeat_pen - .04*near
            key=(objective,-dur_err,quality,-repeat_pen)
            if best is None or key>best[0]: best=(key,list(combo),dur,repeat_pen,near)
    if best is None:
        raise V22Error('NO_DIVERSE_TARGET_COMBINATION')
    return best[1]

def signature(path:Path,at:float)->np.ndarray:
    cap=cv2.VideoCapture(str(path)); cap.set(cv2.CAP_PROP_POS_MSEC,max(0,at)*1000); ok,fr=cap.read(); cap.release()
    if not ok:return np.zeros(8,np.float32)
    fr=cv2.resize(fr,(160,90),interpolation=cv2.INTER_AREA); hsv=cv2.cvtColor(fr,cv2.COLOR_BGR2HSV); gray=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY)
    x=np.concatenate([hsv.reshape(-1,3).mean(0),hsv.reshape(-1,3).std(0),[gray.mean(),(cv2.Canny(gray,80,160)>0).mean()*255]]).astype(np.float32)
    return x/np.array([180,255,255,90,90,90,255,255],np.float32)

def order_continuity(selected:list[dict])->list[dict]:
    sig={e['event_id']:(signature(Path(e['clip_path']),.25),signature(Path(e['clip_path']),max(.25,float(e['duration_s'])-.25))) for e in selected}
    remain=selected[:]; cur=max(remain,key=lambda e:e['v22_score']); order=[cur]; remain.remove(cur)
    while remain:
        end=sig[cur['event_id']][1]
        cur=min(remain,key=lambda e:.72*float(np.linalg.norm(end-sig[e['event_id']][0]))+.28*(1.0-e['v22_score']))
        order.append(cur); remain.remove(cur)
    return order

def output_dimensions(profile:str,output_resolution:str=DEFAULT_OUTPUT_RESOLUTION)->tuple[int,int]:
    output_resolution=str(output_resolution or DEFAULT_OUTPUT_RESOLUTION).strip().lower()
    if output_resolution not in ('standard','social_hd'): raise V22Error('OUTPUT_RESOLUTION_INVALID')
    if profile=='16x9': return (960,540) if output_resolution=='standard' else (1920,1080)
    if profile=='9x16': return (540,960) if output_resolution=='standard' else (1080,1920)
    raise V22Error('PROFILE_INVALID')

def smart_crop_geometry(e:dict,w:int,h:int,vertical_focus_x:float=DEFAULT_VERTICAL_FOCUS_X)->tuple[int,int,int,int]:
    m=e['v22_metrics']; cx=float(m['saliency_cx']); cy=float(m['saliency_cy']); target=9/16
    vertical_focus_x=float(vertical_focus_x)
    if not (0.0 <= vertical_focus_x <= 1.0): raise V22Error('VERTICAL_FOCUS_X_RANGE_0_1')
    if w/h>=target:
        cw=max(2,int(round(h*target))//2*2); ch=h
        auto_x=int(round(cx*w-cw/2)); auto_x=max(0,min(w-cw,auto_x)); right=max(0,w-cw)
        if vertical_focus_x < 0.5:
            blend=(0.5-vertical_focus_x)/0.5; x=int(round(auto_x*(1.0-blend)))
        elif vertical_focus_x > 0.5:
            blend=(vertical_focus_x-0.5)/0.5; x=int(round(auto_x*(1.0-blend)+right*blend))
        else: x=auto_x
        x=max(0,min(right,x)); y=0
    else:
        cw=w; ch=max(2,int(round(w/target))//2*2); y=int(round(cy*h-ch/2)); y=max(0,min(h-ch,y)); x=0
    return x,y,cw,ch

def segment_spec(e,profile,clip_seconds,vertical_framing=DEFAULT_VERTICAL_FRAMING,vertical_focus_x:float=DEFAULT_VERTICAL_FOCUS_X,output_resolution:str=DEFAULT_OUTPUT_RESOLUTION,output_fps:int=DEFAULT_OUTPUT_FPS):
    vertical_framing=str(vertical_framing or DEFAULT_VERTICAL_FRAMING).strip().lower(); vertical_focus_x=float(vertical_focus_x); output_resolution=str(output_resolution or DEFAULT_OUTPUT_RESOLUTION).strip().lower(); output_fps=int(output_fps)
    if vertical_framing not in ('fill','fit_blur'): raise V22Error('VERTICAL_FRAMING_INVALID')
    if output_fps not in (30,60): raise V22Error('OUTPUT_FPS_INVALID')
    ow,oh=output_dimensions(profile,output_resolution)
    if not (0.0 <= vertical_focus_x <= 1.0): raise V22Error('VERTICAL_FOCUS_X_RANGE_0_1')
    if vertical_framing=='fit_blur' and abs(vertical_focus_x-DEFAULT_VERTICAL_FOCUS_X)>1e-9: raise V22Error('VERTICAL_FOCUS_X_REQUIRES_FILL')
    src=Path(e['clip_path']); pr=ffprobe(src); vs=[s for s in pr['streams'] if s.get('codec_type')=='video'][0]; iw=int(vs['width']); ih=int(vs['height'])
    dur=float(e.get('duration_s') or pr['format']['duration']); use=min(float(clip_seconds),max(.5,dur)); ss=max(0,(dur-use)/2)
    if profile=='16x9':
        ratio=iw/max(1,ih); target=16/9
        if abs(ratio-target)/target>.08:
            vf=f'[0:v]split=2[bg][fg];[bg]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},boxblur=8:1,eq=brightness=-0.08:saturation=0.85[bg2];[fg]scale={ow}:{oh}:force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2,fps={output_fps},format=yuv420p[v]'
            crop={'presentation':'SOFT_LOCAL_BACKGROUND_FILL','source_width':iw,'source_height':ih}; complex_v=True
        else:
            vf=f'scale={ow}:{oh}:force_original_aspect_ratio=decrease,pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=0x101010,fps={output_fps},format=yuv420p'; crop={'presentation':'FULL_FRAME_FIT','source_width':iw,'source_height':ih}; complex_v=False
    else:
        if vertical_framing=='fit_blur':
            vf=f'[0:v]split=2[bg][fg];[bg]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},boxblur=12:2,eq=brightness=-0.12:saturation=0.80[bg2];[fg]scale={ow}:{oh}:force_original_aspect_ratio=decrease:force_divisible_by=2[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2,fps={output_fps},format=yuv420p,setsar=1[v]'
            crop={'presentation':'FULL_FRAME_FIT_BLUR_BACKGROUND','source_width':iw,'source_height':ih}; complex_v=True
        else:
            x,y,cw,ch=smart_crop_geometry(e,iw,ih,vertical_focus_x); vf=f'crop={cw}:{ch}:{x}:{y},scale={ow}:{oh},fps={output_fps},format=yuv420p'; crop={'presentation':'SMART_SALIENCY_CROP','x':x,'y':y,'w':cw,'h':ch,'saliency_cx':e['v22_metrics']['saliency_cx'],'saliency_cy':e['v22_metrics']['saliency_cy']}; crop.update({'vertical_focus_x':vertical_focus_x} if abs(vertical_focus_x-DEFAULT_VERTICAL_FOCUS_X)>1e-9 else {}); complex_v=False
    return src,ss,use,vf,crop,complex_v

def make_segment(e,out:Path,profile:str,clip_seconds:float,audio_lufs:float=DEFAULT_AUDIO_LUFS,audio_true_peak_db:float=DEFAULT_AUDIO_TRUE_PEAK_DB,vertical_framing:str=DEFAULT_VERTICAL_FRAMING,vertical_focus_x:float=DEFAULT_VERTICAL_FOCUS_X,output_resolution:str=DEFAULT_OUTPUT_RESOLUTION,audio_content:str=DEFAULT_AUDIO_CONTENT,output_fps:int=DEFAULT_OUTPUT_FPS,video_quality:str=DEFAULT_VIDEO_QUALITY)->dict:
    vertical_framing=str(vertical_framing or DEFAULT_VERTICAL_FRAMING).strip().lower(); vertical_focus_x=float(vertical_focus_x)
    src,ss,use,vf,crop,complex_v=segment_spec(e,profile,clip_seconds,vertical_framing,vertical_focus_x,output_resolution,output_fps)
    audio_lufs=float(audio_lufs); audio_true_peak_db=float(audio_true_peak_db); output_fps=int(output_fps); audio_content=str(audio_content or DEFAULT_AUDIO_CONTENT).strip().lower(); video_quality=str(video_quality or DEFAULT_VIDEO_QUALITY).strip().lower()
    if output_fps not in (30,60): raise V22Error('OUTPUT_FPS_INVALID')
    if video_quality not in ('standard','high'): raise V22Error('VIDEO_QUALITY_INVALID')
    if not (-24.0 <= audio_lufs <= -12.0): raise V22Error('AUDIO_LUFS_RANGE_-24_-12')
    if audio_content not in ('source','mute'): raise V22Error('AUDIO_CONTENT_INVALID')
    if not (-6.0 <= audio_true_peak_db <= -1.0): raise V22Error('AUDIO_TRUE_PEAK_DB_RANGE_-6_-1')
    pr=ffprobe(src); has_audio=any(x.get('codec_type')=='audio' for x in pr.get('streams',[]))
    side=out.with_suffix('.json'); ident={'source_sha256':e['clip_sha256'],'profile':profile,'clip_seconds':clip_seconds,'scorer_version':SCORER_VERSION,'ss':round(ss,6),'use':round(use,6),'crop':crop,'complex_video_filter':complex_v,'audio_policy':'ORIGINAL_AMBIENCE_OR_SILENCE_V1','source_has_audio':has_audio}
    if audio_content!='source': ident['audio_content']=audio_content
    use_source_audio=bool(has_audio and audio_content=='source')
    if abs(audio_lufs-DEFAULT_AUDIO_LUFS)>1e-9 or abs(audio_true_peak_db-DEFAULT_AUDIO_TRUE_PEAK_DB)>1e-9:
        ident.update({'audio_lufs':audio_lufs,'audio_true_peak_db':audio_true_peak_db})
    if vertical_framing!=DEFAULT_VERTICAL_FRAMING:
        ident['vertical_framing']=vertical_framing
    if abs(vertical_focus_x-DEFAULT_VERTICAL_FOCUS_X)>1e-9:
        ident['vertical_focus_x']=vertical_focus_x
    if str(output_resolution)!=DEFAULT_OUTPUT_RESOLUTION:
        ident['output_resolution']=str(output_resolution)
    if int(output_fps)!=DEFAULT_OUTPUT_FPS:
        ident['output_fps']=int(output_fps)
    if video_quality!=DEFAULT_VIDEO_QUALITY:
        ident['video_quality']=video_quality
    if out.is_file() and side.is_file():
        try:
            o=json.loads(side.read_text())
            if o.get('identity')==ident and o.get('bytes')==out.stat().st_size and o.get('sha256')==sha256_file(out): return o
        except Exception: pass
    out.parent.mkdir(parents=True,exist_ok=True); tmp=out.with_name(out.stem+'.part.mp4')
    if tmp.exists(): tmp.unlink()
    fade_out=max(0.0,use-.16)
    if use_source_audio:
        af=f'aresample=48000,loudnorm=I={audio_lufs:g}:TP={audio_true_peak_db:g}:LRA=11,afade=t=in:st=0:d=0.10,afade=t=out:st={fade_out:.3f}:d=0.16'
        base=[FFMPEG,'-hide_banner','-loglevel','error','-y','-ss',f'{ss:.3f}','-t',f'{use:.3f}','-i',str(src)]
        if complex_v:
            cmd=base+['-filter_complex',vf,'-map','[v]','-map','0:a:0','-af',af]
        else:
            cmd=base+['-vf',vf,'-map','0:v:0','-map','0:a:0','-af',af]
        venc=['-preset','ultrafast','-crf','20'] if video_quality=='standard' else ['-preset','veryfast','-crf','16']
        cmd+=['-c:v','libx264']+venc+['-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',str(tmp)]
    else:
        base=[FFMPEG,'-hide_banner','-loglevel','error','-y','-ss',f'{ss:.3f}','-t',f'{use:.3f}','-i',str(src),'-f','lavfi','-t',f'{use:.3f}','-i','anullsrc=r=48000:cl=stereo']
        if complex_v:
            cmd=base+['-filter_complex',vf,'-map','[v]','-map','1:a:0']
        else:
            cmd=base+['-vf',vf,'-map','0:v:0','-map','1:a:0']
        venc=['-preset','ultrafast','-crf','20'] if video_quality=='standard' else ['-preset','veryfast','-crf','16']
        cmd+=['-c:v','libx264']+venc+['-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',str(tmp)]
    run(cmd,150); os.replace(tmp,out); full_decode(out)
    q=ffprobe(out); aud=[x for x in q.get('streams',[]) if x.get('codec_type')=='audio']
    if not aud: raise V22Error('SEGMENT_AUDIO_STREAM_MISSING:'+str(out))
    meta={'identity':ident,'path':str(out),'sha256':sha256_file(out),'bytes':out.stat().st_size,'duration_s':use,'crop':crop,'source_has_audio':has_audio,'audio_stream_verified':True}
    if int(output_fps)!=DEFAULT_OUTPUT_FPS: meta['output_fps']=int(output_fps)
    if video_quality!=DEFAULT_VIDEO_QUALITY: meta['video_quality']=video_quality
    if audio_content!='source': meta.update({'audio_content':audio_content,'source_audio_used':False})
    st=side.with_suffix(side.suffix+'.part'); st.write_text(json.dumps(meta,indent=2),encoding='utf-8'); os.replace(st,side); return meta

def concat(segs:list[Path],durs:list[float],out:Path,transition:float,video_quality:str=DEFAULT_VIDEO_QUALITY):
    if not segs: raise V22Error('NO_SEGMENTS_TO_CONCAT')
    video_quality=str(video_quality or DEFAULT_VIDEO_QUALITY).strip().lower()
    if video_quality not in ('standard','high'): raise V22Error('VIDEO_QUALITY_INVALID')
    if len(segs)==1:
        out.parent.mkdir(parents=True,exist_ok=True)
        tmp=out.with_name(out.stem+'.part.mp4')
        if tmp.exists(): tmp.unlink()
        shutil.copy2(segs[0],tmp); os.replace(tmp,out); full_decode(out)
        pr=ffprobe(out)
        if not any(x.get('codec_type')=='audio' for x in pr.get('streams',[])): raise V22Error('FINAL_AUDIO_STREAM_MISSING:'+str(out))
        return durs[0]
    args=[FFMPEG,'-hide_banner','-loglevel','error','-y']; [args.extend(['-i',str(p)]) for p in segs]
    filters=[]; vprev='0:v'; aprev='0:a'; cumulative=durs[0]
    for i in range(1,len(segs)):
        vl=f'v{i}'; al=f'a{i}'; off=max(0,cumulative-transition)
        filters.append(f'[{vprev}][{i}:v]xfade=transition=fade:duration={transition:.3f}:offset={off:.3f}[{vl}]')
        filters.append(f'[{aprev}][{i}:a]acrossfade=d={transition:.3f}:c1=tri:c2=tri[{al}]')
        vprev=vl; aprev=al; cumulative+=durs[i]-transition
    venc=['-preset','ultrafast','-crf','20'] if video_quality=='standard' else ['-preset','veryfast','-crf','16']
    args += ['-filter_complex',';'.join(filters),'-map',f'[{vprev}]','-map',f'[{aprev}]','-c:v','libx264']+venc+['-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','2','-movflags','+faststart',str(out)]
    run(args,300); full_decode(out)
    pr=ffprobe(out)
    if not any(x.get('codec_type')=='audio' for x in pr.get('streams',[])): raise V22Error('FINAL_AUDIO_STREAM_MISSING:'+str(out))
    return cumulative

def validate_resume(outdir,event_library_sha,target,clip_seconds,transition,audio_lufs=DEFAULT_AUDIO_LUFS,audio_true_peak_db=DEFAULT_AUDIO_TRUE_PEAK_DB,vertical_framing=DEFAULT_VERTICAL_FRAMING,vertical_focus_x=DEFAULT_VERTICAL_FOCUS_X,output_resolution=DEFAULT_OUTPUT_RESOLUTION,audio_content=DEFAULT_AUDIO_CONTENT,output_fps=DEFAULT_OUTPUT_FPS,video_quality=DEFAULT_VIDEO_QUALITY):
    mp=outdir/'AUTO_EDIT_V26_MANIFEST.json'
    if not mp.is_file(): return None
    try:
        o=json.loads(mp.read_text());
        if o.get('candidate')!=CANDIDATE or o.get('source_event_library_sha256')!=event_library_sha or float(o.get('target_duration_s'))!=float(target) or float(o.get('clip_seconds'))!=float(clip_seconds) or float(o.get('transition_seconds'))!=float(transition) or float(o.get('audio_lufs',DEFAULT_AUDIO_LUFS))!=float(audio_lufs) or float(o.get('audio_true_peak_db',DEFAULT_AUDIO_TRUE_PEAK_DB))!=float(audio_true_peak_db) or str(o.get('vertical_framing',DEFAULT_VERTICAL_FRAMING))!=str(vertical_framing) or float(o.get('vertical_focus_x',DEFAULT_VERTICAL_FOCUS_X))!=float(vertical_focus_x) or str(o.get('output_resolution',DEFAULT_OUTPUT_RESOLUTION))!=str(output_resolution) or int(o.get('output_fps',DEFAULT_OUTPUT_FPS))!=int(output_fps) or str(o.get('audio_content',DEFAULT_AUDIO_CONTENT))!=str(audio_content) or str(o.get('video_quality',DEFAULT_VIDEO_QUALITY))!=str(video_quality) or o.get('scorer_version')!=SCORER_VERSION:return None
        for q in o.get('outputs') or []:
            p=Path(q['path']);
            if not p.is_file() or p.stat().st_size!=q['bytes'] or sha256_file(p)!=q['sha256']:return None
            full_decode(p)
        o['resume_status']='SKIPPED_EXACT_COMPLETED'; return o
    except Exception:return None

def build(event_library:Path,outdir:Path,target=30.0,clip_seconds=5.0,transition=.25,audio_lufs=DEFAULT_AUDIO_LUFS,audio_true_peak_db=DEFAULT_AUDIO_TRUE_PEAK_DB,vertical_framing=DEFAULT_VERTICAL_FRAMING,vertical_focus_x=DEFAULT_VERTICAL_FOCUS_X,output_resolution=DEFAULT_OUTPUT_RESOLUTION,audio_content=DEFAULT_AUDIO_CONTENT,output_fps=DEFAULT_OUTPUT_FPS,video_quality=DEFAULT_VIDEO_QUALITY):
    audio_lufs=float(audio_lufs); audio_true_peak_db=float(audio_true_peak_db); vertical_framing=str(vertical_framing or DEFAULT_VERTICAL_FRAMING).strip().lower(); vertical_focus_x=float(vertical_focus_x); output_resolution=str(output_resolution or DEFAULT_OUTPUT_RESOLUTION).strip().lower(); output_fps=int(output_fps); audio_content=str(audio_content or DEFAULT_AUDIO_CONTENT).strip().lower(); video_quality=str(video_quality or DEFAULT_VIDEO_QUALITY).strip().lower()
    if vertical_framing not in ('fill','fit_blur'): raise V22Error('VERTICAL_FRAMING_INVALID')
    if output_resolution not in ('standard','social_hd'): raise V22Error('OUTPUT_RESOLUTION_INVALID')
    if output_fps not in (30,60): raise V22Error('OUTPUT_FPS_INVALID')
    if video_quality not in ('standard','high'): raise V22Error('VIDEO_QUALITY_INVALID')
    if not (0.0 <= vertical_focus_x <= 1.0): raise V22Error('VERTICAL_FOCUS_X_RANGE_0_1')
    if vertical_framing=='fit_blur' and abs(vertical_focus_x-DEFAULT_VERTICAL_FOCUS_X)>1e-9: raise V22Error('VERTICAL_FOCUS_X_REQUIRES_FILL')
    libsha=sha256_file(event_library); resumed=validate_resume(outdir,libsha,target,clip_seconds,transition,audio_lufs,audio_true_peak_db,vertical_framing,vertical_focus_x,output_resolution,audio_content,output_fps,video_quality)
    if resumed:return resumed
    _,events=load_library(event_library); outdir.mkdir(parents=True,exist_ok=True)
    scored=score_events(events,outdir/'V22_SCORE_CACHE.json')
    selected=choose_for_target(scored,target,clip_seconds,transition); ordered=order_continuity(selected)
    result={'candidate':CANDIDATE,'schema_version':1,'scorer_version':SCORER_VERSION,'semantic_model_used':False,'semantic_selection_claim':False,'audio_policy':('LOCAL_SOURCE_LOUDNORM_TARGET_V43' if audio_content=='source' else 'MUTED_SILENT_AAC_V47'),'audio_lufs':audio_lufs,'audio_true_peak_db':audio_true_peak_db,'external_audio_used':False,'presentation_policy':('16x9_SOFT_LOCAL_BACKGROUND_WHEN_NEEDED__9x16_SMART_SALIENCY_CROP' if vertical_framing=='fill' else '16x9_SOFT_LOCAL_BACKGROUND_WHEN_NEEDED__9x16_FULL_FRAME_FIT_BLUR_BACKGROUND'),'selection_mode':'GENERIC_AESTHETIC_TECHNICAL_TARGETED_SOURCE_DIVERSITY','target_duration_s':target,'clip_seconds':clip_seconds,'transition_seconds':transition,'source_event_library':str(event_library),'source_event_library_sha256':libsha,'ranked_events':[{k:e[k] for k in ('event_id','source_name','start_s','end_s','technical_prominence','v22_score')} for e in sorted(scored,key=lambda x:-x['v22_score'])],'selected_events':[],'outputs':[]}
    if vertical_framing!=DEFAULT_VERTICAL_FRAMING: result['vertical_framing']=vertical_framing
    if abs(vertical_focus_x-DEFAULT_VERTICAL_FOCUS_X)>1e-9: result['vertical_focus_x']=vertical_focus_x
    if output_resolution!=DEFAULT_OUTPUT_RESOLUTION: result['output_resolution']=output_resolution
    if output_fps!=DEFAULT_OUTPUT_FPS: result['output_fps']=output_fps
    if video_quality!=DEFAULT_VIDEO_QUALITY: result['video_quality']=video_quality
    if audio_content!=DEFAULT_AUDIO_CONTENT: result['audio_content']=audio_content
    for i,e in enumerate(ordered,1):
        d=used_duration(e,clip_seconds); off=max(0,(float(e['duration_s'])-d)/2); result['selected_events'].append({'sequence':i,'event_id':e['event_id'],'source_name':e['source_name'],'source_sha256':e['source_sha256'],'source_interval_s':[e['start_s'],e['end_s']],'final_trim_source_interval_s':[round(float(e['start_s'])+off,3),round(float(e['start_s'])+off+d,3)],'v22_score':e['v22_score'],'technical_prominence':e['technical_prominence'],'metrics':e['v22_metrics']})
    for profile in ('16x9','9x16'):
        segs=[]; metas=[]
        for i,e in enumerate(ordered,1):
            p=outdir/'work'/profile/f'{i:02d}_{e["event_id"]}.mp4'; meta=make_segment(e,p,profile,clip_seconds,audio_lufs,audio_true_peak_db,vertical_framing,vertical_focus_x,output_resolution,audio_content,output_fps,video_quality); segs.append(p); metas.append(meta)
        final=outdir/f'MEDENG_TARGET_REEL_V26_{profile}.mp4'; expected=concat(segs,[m['duration_s'] for m in metas],final,transition,video_quality); pr=ffprobe(final)
        result['outputs'].append({'profile':profile,'path':str(final),'bytes':final.stat().st_size,'sha256':sha256_file(final),'expected_duration_s':round(expected,3),'probe':pr})
    tmp=outdir/'AUTO_EDIT_V26_MANIFEST.json.part'; tmp.write_text(json.dumps(result,indent=2),encoding='utf-8'); os.replace(tmp,outdir/'AUTO_EDIT_V26_MANIFEST.json'); return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--event-library',required=True); ap.add_argument('--outdir',required=True); ap.add_argument('--target-seconds',type=float,default=30); ap.add_argument('--clip-seconds',type=float,default=5); ap.add_argument('--transition',type=float,default=.25); a=ap.parse_args()
    audio_lufs=float(os.environ.get('MEDENG_AUDIO_LUFS',str(DEFAULT_AUDIO_LUFS))); audio_true_peak_db=float(os.environ.get('MEDENG_AUDIO_TRUE_PEAK_DB',str(DEFAULT_AUDIO_TRUE_PEAK_DB))); vertical_framing=str(os.environ.get('MEDENG_VERTICAL_FRAMING',DEFAULT_VERTICAL_FRAMING)).strip().lower(); vertical_focus_x=float(os.environ.get('MEDENG_VERTICAL_FOCUS_X',str(DEFAULT_VERTICAL_FOCUS_X))); output_resolution=str(os.environ.get('MEDENG_OUTPUT_RESOLUTION',DEFAULT_OUTPUT_RESOLUTION)).strip().lower(); output_fps=int(os.environ.get('MEDENG_OUTPUT_FPS',str(DEFAULT_OUTPUT_FPS))); audio_content=str(os.environ.get('MEDENG_AUDIO_CONTENT',DEFAULT_AUDIO_CONTENT)).strip().lower(); video_quality=str(os.environ.get('MEDENG_VIDEO_QUALITY',DEFAULT_VIDEO_QUALITY)).strip().lower()
    t=time.perf_counter(); r=build(Path(a.event_library).resolve(),Path(a.outdir).resolve(),a.target_seconds,a.clip_seconds,a.transition,audio_lufs,audio_true_peak_db,vertical_framing,vertical_focus_x,output_resolution,audio_content,output_fps,video_quality); print(json.dumps({'candidate':r['candidate'],'resume_status':r.get('resume_status'),'target_duration_s':r['target_duration_s'],'selected_count':len(r['selected_events']),'selected_sources':[x['source_name'] for x in r['selected_events']],'outputs':[{k:o[k] for k in ('profile','path','bytes','sha256','expected_duration_s')} for o in r['outputs']],'elapsed_s':round(time.perf_counter()-t,3)},indent=2))
if __name__=='__main__': main()

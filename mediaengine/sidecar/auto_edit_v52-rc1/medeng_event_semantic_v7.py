#!/usr/bin/env python3
"""
MediaEngine real-media event discovery + semantic selection V7.

Pipeline:
1) Adaptive-budget FFmpeg fast-seek scout (parallel; ~48 frames max by default).
2) Candidate event windows from visual novelty + technical/event score.
3) Local semantic rerank (FAST_LOCAL or QUALITY_LOCAL).
4) Dense 4 fps technical refinement only on semantic top-3.

No benchmark target timestamps are embedded. No network I/O is allowed during analysis.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, os, subprocess, time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from medeng_media_probe_v41 import duration as media_duration

POSITIVE_PROMPTS = (
    "a cinematic b-roll shot",
    "a visually striking scenic moment",
    "a dramatic natural event",
    "an interesting travel shot",
    "a strong composition with a clear focal point",
    "a memorable moment with strong leading lines",
    "an energetic visually interesting moment",
)
NEGATIVE_PROMPTS = (
    "a boring uneventful frame",
    "a weak composition with no clear subject",
    "an accidental camera movement",
    "a blurry low quality frame",
    "a camera pointed at a dashboard or interior obstruction",
)

def robust01(values):
    a=np.asarray(values,dtype=float)
    if len(a)==0: return a
    lo=float(np.nanquantile(a,.10)); hi=float(np.nanquantile(a,.90))
    if not np.isfinite(hi-lo) or hi-lo<1e-12:
        return np.full_like(a,.5)
    return np.clip((a-lo)/(hi-lo),0,1)

def ffprobe_duration(path: Path, ffprobe="ffprobe", ffmpeg="ffmpeg"):
    return media_duration(path, ffmpeg, 30)

def extract_seek_jpeg(path: Path, t: float, ffmpeg="ffmpeg", width=384):
    cp=subprocess.run(
        [ffmpeg,"-hide_banner","-loglevel","error","-ss",f"{t:.3f}",
         "-i",str(path),"-frames:v","1","-vf",f"scale={width}:-2",
         "-f","image2pipe","-vcodec","mjpeg","pipe:1"],
        capture_output=True
    )
    if cp.returncode!=0 or not cp.stdout:
        return t,None
    arr=np.frombuffer(cp.stdout,dtype=np.uint8)
    return t,cv2.imdecode(arr,cv2.IMREAD_COLOR)

def adaptive_scout_step(duration: float, target_frames: int = 48, min_step: float = 1.0) -> float:
    """Bound scout decode cost for long clips while preserving 1 Hz on short clips."""
    if target_frames < 8:
        raise ValueError("target_frames must be >= 8")
    return max(float(min_step), float(duration) / float(target_frames))

def parallel_scout_frames(path: Path, step=1.0, workers=8, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    duration=ffprobe_duration(path,ffprobe,ffmpeg)
    times=np.arange(0,max(0.0,duration-.05)+1e-9,step)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        vals=list(ex.map(lambda t: extract_seek_jpeg(path,float(t),ffmpeg),times))
    vals=[x for x in vals if x[1] is not None]
    vals.sort(key=lambda x:x[0])
    if len(vals)<3:
        raise RuntimeError("SCOUT_INSUFFICIENT_FRAMES")
    # Fail if a decoder bug returns duplicate frames for most timestamps.
    hashes=[hashlib.sha256(x[1].tobytes()).hexdigest() for x in vals]
    unique_ratio=len(set(hashes))/len(hashes)
    if unique_ratio<0.70:
        raise RuntimeError(f"SCOUT_DUPLICATE_FRAME_RATIO:{unique_ratio:.3f}")
    return duration,vals,unique_ratio

def feature_table(vals):
    rows=[]; prev=None; prev_hist=None; prev_dir=None
    for t,frame in vals:
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        hist=cv2.calcHist([hsv],[0,1],None,[24,16],[0,180,0,256])
        cv2.normalize(hist,hist)
        hist_delta=0.0 if prev_hist is None else float(
            cv2.compareHist(prev_hist,hist,cv2.HISTCMP_BHATTACHARYYA)
        )
        diff=flow=coh=orient=0.0
        direction=0.0
        if prev is not None:
            diff=float(cv2.absdiff(gray,prev).mean()/255.0)
            fl=cv2.calcOpticalFlowFarneback(prev,gray,None,.5,3,15,3,5,1.2,0)
            mag,ang=cv2.cartToPolar(fl[...,0],fl[...,1])
            flow=float(np.percentile(mag,75))
            mask=mag>np.percentile(mag,55)
            if mask.any():
                ww=mag[mask]+1e-6
                c=float(np.sum(np.cos(ang[mask])*ww))
                ss=float(np.sum(np.sin(ang[mask])*ww))
                direction=float(np.arctan2(ss,c))
                coh=float(np.hypot(c,ss)/(float(ww.sum())+1e-9))
                if prev_dir is not None:
                    orient=float(abs(np.angle(np.exp(1j*(direction-prev_dir))))/np.pi)
        rows.append({
            "t":float(t),
            "sharp":float(cv2.Laplacian(gray,cv2.CV_64F).var()),
            "std":float(gray.std()),
            "sat":float(hsv[:,:,1].mean()),
            "edge":float((cv2.Canny(gray,80,160)>0).mean()),
            "exposure":max(0.0,1-abs(float(gray.mean())-128)/128
                           -.75*(float((gray<16).mean())+float((gray>239).mean()))),
            "hist_delta":hist_delta,
            "diff":diff,
            "flow":flow,
            "coh":coh,
            "orient":orient,
        })
        prev=gray; prev_hist=hist.copy(); prev_dir=direction

    for c in ("sharp","std","sat","edge","hist_delta","diff","flow","orient"):
        norm=robust01([r[c] for r in rows])
        for r,v in zip(rows,norm): r[c+"_n"]=float(v)
    for r in rows:
        r["quality"]=(.38*r["sharp_n"]+.22*r["exposure"]+.17*r["std_n"]+.13*r["edge_n"]+.10*r["sat_n"])
        r["novelty"]=(.45*r["hist_delta_n"]+.35*r["orient_n"]+.20*r["diff_n"])
        r["eventness"]=(.45*r["flow_n"]+.30*r["diff_n"]+.15*r["orient_n"]+.10*r["coh"])
        r["scout_score"]=(.45*r["quality"]+.35*r["eventness"]+.20*r["novelty"])
    return rows

def event_candidates(d, duration, window=5.5, max_candidates=8):
    # Match the former pandas nlargest/concat/drop_duplicates pipeline with
    # deterministic pure-Python ordering so DISCOVER_EVENTS has no pandas dependency.
    eligible=[r for r in d if float(r["t"])>0]
    top_novelty=sorted(eligible,key=lambda r:float(r["novelty"]),reverse=True)[:max_candidates*2]
    top_score=sorted(eligible,key=lambda r:float(r["scout_score"]),reverse=True)[:max_candidates*2]
    ranks=[]; seen=set()
    for r in top_novelty+top_score:
        t=float(r["t"])
        if t in seen: continue
        seen.add(t)
        x=dict(r); x["priority"]=.55*float(r["novelty"])+.45*float(r["scout_score"]); ranks.append(x)
    ranks.sort(key=lambda r:float(r["priority"]),reverse=True)

    picked=[]
    for r in ranks:
        center=float(r["t"])
        if all(abs(center-x["center_s"])>=2.0 for x in picked):
            start=min(max(0.0,center-window/2),max(0.0,duration-window))
            start=round(start*2)/2
            end=min(duration,start+window)
            picked.append({
                "center_s":center,
                "start_s":round(start,3),
                "end_s":round(end,3),
                "scout_priority":round(float(r["priority"]),6),
                "scout_quality":round(float(r["quality"]),6),
                "scout_eventness":round(float(r["eventness"]),6),
                "scout_novelty":round(float(r["novelty"]),6),
            })
        if len(picked)>=max_candidates:
            break
    return picked

def nearest_scout_image(vals,t):
    ts=np.asarray([x[0] for x in vals])
    idx=int(np.argmin(np.abs(ts-float(t))))
    bgr=vals[idx][1]
    return Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))

def load_semantic(profile, model_root: Path):
    # Validate architecture + processor contract before loading model runtime.
    from validate_p11_model_contract import validate as validate_model_contract
    profile_dir = model_root / profile
    validate_model_contract(profile, profile_dir)

    if profile=="FAST_LOCAL":
        import p11_fast_onnx_adapter as a
        processor,sess,ident=a.load_runtime(model_root/"FAST_LOCAL")
        def score(images):
            logits=a.semantic_logits(processor,sess,images,POSITIVE_PROMPTS+NEGATIVE_PROMPTS)
            return a.semantic_margin(logits,len(POSITIVE_PROMPTS))
        return ident,score

    import p11_quality_semantic_adapter as q
    model_dir=model_root/"QUALITY_LOCAL"
    ident=q.verify_model_dir(model_dir)
    torch,processor,model=q.load_semantic_model(model_dir)
    def score(images):
        inputs=processor(text=list(POSITIVE_PROMPTS+NEGATIVE_PROMPTS),
                         images=images,return_tensors="pt",padding=True)
        with torch.inference_mode():
            logits=model(**inputs).logits_per_image.detach().cpu().float().numpy()
        return q.semantic_margins(torch,processor,model,images) if False else _margin(logits)
    return ident,score

def _margin(logits):
    posn=len(POSITIVE_PROMPTS)
    out=[]
    for row in np.asarray(logits,float):
        pos=np.sort(row[:posn])[-2:].mean()
        neg=np.max(row[posn:])
        out.append(float(pos-neg))
    return out

def semantic_rerank(candidates,vals,score_images):
    images=[]; owners=[]
    for i,c in enumerate(candidates):
        s=float(c["start_s"]); e=float(c["end_s"])
        for frac in (.20,.50,.80):
            images.append(nearest_scout_image(vals,s+(e-s)*frac))
            owners.append(i)
    margins=score_images(images)
    per=[[] for _ in candidates]
    for i,m in zip(owners,margins):
        per[i].append(float(m))
    raw=np.asarray([np.mean(x) if x else -1e9 for x in per],float)
    sem=robust01(raw)
    scout=robust01([c["scout_priority"] for c in candidates])
    ranked=[]
    for i,c in enumerate(candidates):
        initial=.68*float(sem[i])+.32*float(scout[i])
        ranked.append({
            **c,
            "semantic_margin_raw":round(float(raw[i]),6),
            "semantic_score_0_1":round(float(sem[i]),6),
            "semantic_scout_score":round(initial,6),
        })
    ranked.sort(key=lambda x:x["semantic_scout_score"],reverse=True)
    return ranked

def dense_window_quality(path,start,end,ffmpeg="ffmpeg",fps=4,width=384):
    # Decode only one candidate window after semantic triage.
    duration=max(.1,float(end)-float(start))
    # Use independent exact seeks so malformed HEVC keyframe decoding cannot
    # silently repeat a single frame across the candidate window.
    ts=np.linspace(start,end,num=max(5,int(duration*fps)),endpoint=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        vals=list(ex.map(lambda t: extract_seek_jpeg(path,float(t),ffmpeg,width),ts))
    vals=[x for x in vals if x[1] is not None]
    if len(vals)<5: raise RuntimeError("DENSE_INSUFFICIENT_FRAMES")
    d=feature_table(vals)
    quality=float(np.mean([r["quality"] for r in d]))
    event=float(np.quantile([r["eventness"] for r in d],.80))
    edge_n=max(1,len(d)//5)
    begin=float(np.mean([r["quality"] for r in d[:edge_n]]))
    ending=float(np.mean([r["quality"] for r in d[-edge_n:]]))
    boundary=min(begin,ending)
    return {
        "dense_quality":round(quality,6),
        "dense_eventness":round(event,6),
        "dense_boundary_quality":round(boundary,6),
        "dense_score":round(.55*quality+.25*event+.20*boundary,6),
        "dense_frames":len(vals),
    }

def analyze_video(path: Path, mode: str, profile: str, model_root: Path,
                  ffmpeg="ffmpeg", ffprobe="ffprobe"):
    if mode not in ("DISCOVER_EVENTS","SELECT_BEST"):
        raise ValueError("unsupported mode")

    # Only SELECT_BEST may make a semantic selection claim, and it must verify
    # the exact local semantic model before reading media.
    semantic_identity=None
    score_images=None
    if mode=="SELECT_BEST":
        semantic_identity,score_images=load_semantic(profile,model_root)

    scout_started=time.perf_counter()
    probed_duration=ffprobe_duration(path,ffprobe,ffmpeg)
    scout_step=adaptive_scout_step(probed_duration,target_frames=48,min_step=1.0)
    duration,vals,unique_ratio=parallel_scout_frames(
        path,step=scout_step,ffmpeg=ffmpeg,ffprobe=ffprobe
    )
    scout_elapsed=time.perf_counter()-scout_started
    d=feature_table(vals)
    candidates=event_candidates(d,duration)

    report={
        "video":str(path),
        "duration_s":round(duration,6),
        "scout_frame_count":len(vals),
        "scout_step_s":round(scout_step,3),
        "scout_unique_ratio":round(unique_ratio,4),
        "scout_elapsed_s":round(scout_elapsed,3),
        "candidates":candidates,
        "profile":profile,
        "semantic_model_identity":semantic_identity,
    }
    if mode=="DISCOVER_EVENTS":
        events=[]
        for c in sorted(candidates,key=lambda x: float(x["start_s"])):
            events.append({
                "start_s":c["start_s"],
                "end_s":c["end_s"],
                "center_s":c["center_s"],
                "event_signal":c["scout_eventness"],
                "novelty_signal":c["scout_novelty"],
                "technical_quality":c["scout_quality"],
                "selection_claim":False,
            })
        report["mode"]="DISCOVER_EVENTS"
        report["selection_claim"]=False
        report["events"]=events
        report.pop("candidates",None)
        return report

    semantic_started=time.perf_counter()
    ranked=semantic_rerank(candidates,vals,score_images)
    semantic_elapsed=time.perf_counter()-semantic_started
    dense_started=time.perf_counter()
    for c in ranked[:3]:
        c.update(dense_window_quality(path,c["start_s"],c["end_s"],ffmpeg))
        c["final_score"]=round(.70*c["semantic_scout_score"]+.30*c["dense_score"],6)
    dense_elapsed=time.perf_counter()-dense_started
    # Non-refined lower candidates remain below top-3 unless their initial score is higher.
    for c in ranked[3:]:
        c["final_score"]=round(.70*c["semantic_scout_score"],6)
    ranked.sort(key=lambda x:x["final_score"],reverse=True)
    report["mode"]="SELECT_BEST"
    report["selection_claim"]=True
    report["semantic_elapsed_s"]=round(semantic_elapsed,3)
    report["dense_refine_elapsed_s"]=round(dense_elapsed,3)
    report["ranked"]=ranked
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("videos",nargs="+")
    ap.add_argument("--mode",choices=("DISCOVER_EVENTS","SELECT_BEST"),required=True)
    ap.add_argument("--profile",choices=("FAST_LOCAL","QUALITY_LOCAL"),default="FAST_LOCAL")
    ap.add_argument("--model-root",default="")
    ap.add_argument("--ffmpeg",default=os.environ.get("MEDENG_FFMPEG","ffmpeg"))
    ap.add_argument("--ffprobe",default=os.environ.get("MEDENG_FFPROBE","ffprobe"))
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    if a.mode=="SELECT_BEST" and not a.model_root:
        raise SystemExit("--model-root required for SELECT_BEST")
    reports=[analyze_video(Path(v),a.mode,a.profile,Path(a.model_root),a.ffmpeg,a.ffprobe)
             for v in a.videos]
    obj={
        "candidate":"MEDENG_EVENT_SEMANTIC_V7",
        "network_during_analysis":False,
        "mode":a.mode,
        "selection_claim":a.mode=="SELECT_BEST",
        "reports":reports
    }
    Path(a.out).write_text(json.dumps(obj,indent=2),encoding="utf-8")
    print(json.dumps(obj,indent=2))
if __name__=="__main__":
    main()

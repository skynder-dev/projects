from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np

CONTRACT_VERSION = "P11_FOLDER_TO_REEL_R3"
SUPPORTED = {".mp4",".mov",".m4v",".avi",".mkv",".webm"}

SEMANTIC_HOOK_SHA = "2b15303eba5b02b7f949cb560e58b2dbee09ff4576e21ad4b25b2d3111b02d5c"
MODEL_SHA = "844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600"
MODEL_BYTES = 24281512
ADAPTER_SHA = "d7ef56b5b67e90179cecca366206eddd3b5ae4222ed4bc2f145a8b3f755eff36"
VALIDATOR_SHA = "00e14d0d69b7f06cb5ef0841bee6c12809c6950a4ea3a677db9f7f715a107a22"
SUPPORT_SHA = {
    "config.json":"0ca46b868f12305e959a1cfa2b8085e7bffd521f68769ec3bf2999986b55bec3",
    "merges.txt":"9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a",
    "preprocessor_config.json":"5df7e578c37e907a431daf47fd592fc49fa50d23ed4c41285a0a34a58a9d2e06",
    "special_tokens_map.json":"92e1e31d71a7f63cd75b4dfa1469377bd2cd6b8292cf70b3ff5b7082b0edc1c9",
    "tokenizer.json":"6d9109cc838977f3ca94a379eec36aecc7c807e1785cd729660ca2fc0171fb35",
    "tokenizer_config.json":"f97b07bf147d9e4dbdb5f98941d35fc0b9412263a183483f73893adf756ede3e",
    "vocab.json":"5047b556ce86ccaf6aa22b3ffccfc52d391ea4accdab9c2f2407da5b742d4363",
}

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".part")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(tmp,path)

_PROGRESS_PATH=None
def progress(stage,done=0,total=0,message=""):
    """Write the current stage for the app. Never raises: progress must not break a render."""
    if _PROGRESS_PATH is None: return
    try: atomic_json(_PROGRESS_PATH,{"stage":stage,"done":int(done),"total":int(total),"message":str(message)[:300],"at":time.time()})
    except Exception: pass

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def discover_input(folder, probe=None, skipped=None, skip_sha=None, paths=None):
    """Input videos: every supported file in <folder>, or exactly <paths> (files the user chose; names must be unique)."""
    if paths is not None:
        vids=[]
        for raw in paths:
            p=Path(raw).resolve()
            if not p.is_file():
                if skipped is not None: skipped.append({"name":p.name,"reason":"MISSING"})
                continue
            if p.suffix.lower() in SUPPORTED: vids.append(p)
        vids=sorted(vids,key=lambda p:p.name.lower())
        if len({p.name.lower() for p in vids})!=len(vids): raise RuntimeError("INPUT_NAMES_NOT_UNIQUE")
    else:
        folder=Path(folder).resolve()
        if not folder.is_dir(): raise RuntimeError("INPUT_FOLDER_MISSING")
        vids=sorted([p for p in folder.iterdir() if not p.name.startswith("._") and p.suffix.lower() in SUPPORTED and p.is_file()],key=lambda p:p.name.lower())
    if not vids: raise RuntimeError("NO_SUPPORTED_VIDEO_FILES")
    if len(vids)>64: raise RuntimeError("TOO_MANY_INPUT_FILES")
    rows=[]; seen={}
    for i,p in enumerate(vids,1):
        progress("inputs",i-1,len(vids),p.name)
        try:
            size=p.stat().st_size; dur=0.0
            if size<1024: raise RuntimeError("FILE_TOO_SMALL")
            if probe is not None:
                info=probe(p)
                if not any(x.get("codec_type")=="video" for x in info.get("streams",[])): raise RuntimeError("NO_VIDEO_STREAM")
                dur=float(info.get("format",{}).get("duration") or 0)
                if dur<0.5: raise RuntimeError("TOO_SHORT")
            digest=sha256_file(p)
        except Exception as exc:
            if skipped is not None: skipped.append({"name":p.name,"reason":type(exc).__name__+":"+str(exc)[:160]})
            continue
        if skip_sha and digest in skip_sha:
            if skipped is not None: skipped.append({"name":p.name,"reason":"PRIVATE"})
            continue
        if digest in seen:
            if skipped is not None: skipped.append({"name":p.name,"reason":"DUPLICATE_OF:"+seen[digest]})
            continue
        seen[digest]=p.name
        rows.append({"name":p.name,"path":str(p),"bytes":size,"sha256":digest,"duration_s":dur})
    if not rows: raise RuntimeError("NO_READABLE_VIDEO_FILES")
    return rows

def load_skip_sha(path):
    """SHA-256 values the app says must never be used (media marked Private). Missing file = none."""
    if not path: return set()
    try: return {x.strip().lower() for x in Path(path).read_text(encoding="utf-8").split() if len(x.strip())==64}
    except FileNotFoundError: return set()

def input_fingerprint(rows):
    raw=json.dumps([{"name":r["name"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in rows],
                   sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def robust01(vals):
    a=np.asarray(vals,float)
    if a.size==0: return a
    lo=float(np.nanquantile(a,.10)); hi=float(np.nanquantile(a,.90))
    if not np.isfinite(hi-lo) or hi-lo<1e-12: return np.full_like(a,.5)
    return np.clip((a-lo)/(hi-lo),0,1)

def semantic_runtime_preflight(runtime, model_root, adapter_root):
    hook=runtime/"medeng_event_semantic_v7.py"
    model=model_root/"FAST_LOCAL"/"model_int8.onnx"
    support=model_root/"FAST_LOCAL"/"support_9463a9c508a344c837ffefe9d724f3827bf2dc79"
    adapter=adapter_root/"p11_fast_onnx_adapter.py"
    validator=adapter_root/"validate_p11_model_contract.py"
    checks={
        "hook": hook.is_file() and sha256_file(hook)==SEMANTIC_HOOK_SHA,
        "model": model.is_file() and model.stat().st_size==MODEL_BYTES and sha256_file(model)==MODEL_SHA,
        "adapter": adapter.is_file() and sha256_file(adapter)==ADAPTER_SHA,
        "validator": validator.is_file() and sha256_file(validator)==VALIDATOR_SHA,
        "support": support.is_dir() and all((support/n).is_file() and sha256_file(support/n)==s for n,s in SUPPORT_SHA.items()),
    }
    return {
        "pass":all(checks.values()),
        "checks":checks,
        "hook_sha256":sha256_file(hook) if hook.is_file() else None,
        "model_sha256":sha256_file(model) if model.is_file() else None,
        "adapter_sha256":sha256_file(adapter) if adapter.is_file() else None,
        "validator_sha256":sha256_file(validator) if validator.is_file() else None,
        "model_root":str(model_root),
        "adapter_root":str(adapter_root),
    }

def extract_candidate_clip(v52, src, source_sha, source_name, c, out_dir):
    start=float(c["start_s"]); end=float(c["end_s"]); dur=max(.25,end-start)
    raw=f"{source_sha}|{start:.3f}|{end:.3f}|SEMANTIC_V2".encode()
    eid=hashlib.sha256(raw).hexdigest()[:24]
    out_dir.mkdir(parents=True,exist_ok=True)
    clip=out_dir/f"{eid}.mp4"
    meta=out_dir/f"{eid}.json"
    if clip.is_file() and meta.is_file():
        try:
            m=json.loads(meta.read_text())
            if m.get("clip_sha256")==sha256_file(clip) and m.get("source_sha256")==source_sha:
                return m
        except Exception:
            pass
        # damaged cache entry (power loss, disk error): rebuild it instead of failing the project forever
        clip.unlink(missing_ok=True); meta.unlink(missing_ok=True)
    tmp=out_dir/f".{eid}.tmp.mp4"
    if tmp.exists(): tmp.unlink()
    cmd=[v52.FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",f"{start:.3f}","-i",str(src),"-t",f"{dur:.3f}",
         "-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","fast","-crf","18",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
         "-movflags","+faststart",str(tmp)]
    cp=subprocess.run(cmd,capture_output=True,text=True)
    if cp.returncode!=0: raise RuntimeError("SEMANTIC_CANDIDATE_EXTRACT_FAILED:"+cp.stderr[-800:])
    os.replace(tmp,clip)
    pr=v52.ffprobe(clip); actual=float(pr["format"]["duration"])
    m={
        "event_id":eid,
        "source_name":source_name,
        "source_sha256":source_sha,
        "source_path":str(src),
        "start_s":round(start,3),
        "end_s":round(end,3),
        "center_s":round(float(c["center_s"]),3),
        "duration_s":round(actual,6),
        "clip_path":str(clip),
        "clip_bytes":clip.stat().st_size,
        "clip_sha256":sha256_file(clip),
        "technical_prominence":round(.50*float(c["scout_eventness"])+.35*float(c["scout_novelty"])+.15*float(c["scout_quality"]),6),
        "semantic_margin_raw":float(c["semantic_margin_raw"]),
        "semantic_source_final_score":float(c["final_score"]),
        "semantic_scout_score":float(c["semantic_scout_score"]),
        "semantic_source_rank":int(c["_source_rank"]),
    }
    atomic_json(meta,m)
    return m

def build_semantic_candidates(runtime,input_rows,work_dir,v52,model_root,adapter_root,skipped=None):
    if str(adapter_root) not in sys.path: sys.path.insert(0,str(adapter_root))
    sem=load_module("medeng_event_semantic_v7",runtime/"medeng_event_semantic_v7.py")
    reports_dir=work_dir/"semantic_reports"; reports_dir.mkdir(parents=True,exist_ok=True)
    candidates_dir=work_dir/"semantic_candidates"
    specs=[]
    reports=[]
    kept=[]
    for idx,row in enumerate(input_rows):
        progress("analyze",idx,len(input_rows),row["name"])
        rp=reports_dir/(row["sha256"]+".json")
        report=None
        if rp.is_file():
            try:
                obj=json.loads(rp.read_text())
                if (obj.get("source_sha256")==row["sha256"] and
                    obj.get("hook_sha256")==SEMANTIC_HOOK_SHA and
                    obj.get("model_sha256")==MODEL_SHA):
                    report=obj["report"]
            except Exception:
                report=None   # damaged cache file: analyse again
        try:
            if report is None:
                report=sem.analyze_video(Path(row["path"]),"SELECT_BEST","FAST_LOCAL",model_root,
                                         v52.FFMPEG,os.environ.get("MEDENG_FFPROBE","ffprobe"))
                atomic_json(rp,{"source_sha256":row["sha256"],"hook_sha256":SEMANTIC_HOOK_SHA,
                                "model_sha256":MODEL_SHA,"report":report})
            row_specs=[]
            for rank,c in enumerate(report.get("ranked",[]),1):
                cc=dict(c); cc["_source_rank"]=rank
                row_specs.append(extract_candidate_clip(v52,Path(row["path"]),row["sha256"],row["name"],cc,candidates_dir))
        except Exception as exc:
            # one unreadable file must not sink the whole reel: skip it and say so
            if skipped is not None: skipped.append({"name":row["name"],"reason":"ANALYSIS_FAILED:"+(str(exc).split(":",1)[0] or type(exc).__name__)[:60]})
            continue
        if not row_specs:
            if skipped is not None: skipped.append({"name":row["name"],"reason":"NO_MOMENTS"})
            continue
        kept.append(row)
        reports.append({"source_name":row["name"],"source_sha256":row["sha256"],
                        "rank1":report["ranked"][0] if report.get("ranked") else None})
        specs.extend(row_specs)
    if not specs: raise RuntimeError("NO_SEMANTIC_CANDIDATES")
    technical=v52.score_events(specs,work_dir/"SEMANTIC_CANDIDATE_V22_SCORE_CACHE.json")
    # Shadow selection score: exact semantic per-source final score is primary, accepted V52 technical score is tie-break.
    for e in technical:
        e["technical_v22_score"]=float(e["v22_score"])
        e["v22_score"]=round(.80*float(e["semantic_source_final_score"])+.20*float(e["technical_v22_score"]),6)
        e["selection_score_kind"]="SEMANTIC_80_TECHNICAL_20_SHADOW_V1"
    return technical,reports,kept

def valid_event_cache(path,input_rows):
    p=Path(path)
    if not p.is_file(): return False,None
    try: lib=json.loads(p.read_text())
    except Exception: return False,None
    if lib.get("verdict")!="PASS": return False,None
    expected=sorted((r["name"],r["sha256"]) for r in input_rows)
    got=sorted(set((str(e.get("source_name")),str(e.get("source_sha256"))) for e in lib.get("events",[])))
    if expected!=got: return False,None
    for e in lib.get("events",[]):
        cp=Path(e.get("clip_path",""))
        if not cp.is_file() or cp.stat().st_size!=int(e.get("clip_bytes",0)): return False,None
    return True,lib

def apply_manual_trims(v52,selected,trims,work_dir):
    """User mark-in/mark-out in SOURCE time. Re-extracted from the source so a moment can also be widened."""
    out=[]; tdir=work_dir/"manual_trims"; tdir.mkdir(parents=True,exist_ok=True)
    for e in selected:
        eid=str(e["event_id"])
        if eid not in trims: out.append(e); continue
        a,b=trims[eid]; src=Path(e.get("source_path") or "")
        if not src.is_file(): raise RuntimeError("EDIT_SOURCE_MISSING:"+eid)
        dur=float(v52.ffprobe(src)["format"]["duration"])
        a=max(0.0,min(float(a),dur)); b=max(0.0,min(float(b),dur))
        if b-a<0.5: raise RuntimeError("EDIT_TRIM_TOO_SHORT:"+eid)
        key=hashlib.sha256(f'{e.get("source_sha256")}|{a:.3f}|{b:.3f}|MANUALTRIM1'.encode()).hexdigest()[:20]
        clip=tdir/f"{key}.mp4"
        if not clip.is_file():
            tmp=tdir/f".{key}.tmp.mp4"
            cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y","-ss",f"{a:.3f}","-i",str(src),"-t",f"{b-a:.3f}",
                               "-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
                               "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
            if cp.returncode!=0: raise RuntimeError("EDIT_TRIM_FAILED:"+cp.stderr[-600:])
            os.replace(tmp,clip)
        x=dict(e); x["clip_path"]=str(clip); x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha256_file(clip)
        x["duration_s"]=float(v52.ffprobe(clip)["format"]["duration"]); x["start_s"]=round(a,3); x["end_s"]=round(a+x["duration_s"],3)
        x["manual_trim"]=[round(a,3),round(b,3)]
        out.append(x)
    return out

def realmedia_item_name(path,sha):
    """Item folder name used by medeng_realmedia_pipeline_v14.safe_name (kept in sync; used for progress only)."""
    s=re.sub(r'[^A-Za-z0-9._-]+','_',Path(path).name)[:100] or 'media'
    return f'{s}__{sha[:12]}'

def _analysis_skip_reason(r):
    """Short machine reason for a file the technical analysis could not use (no paths, no logs)."""
    err=str((r or {}).get("error") or (r or {}).get("status") or "NOT_ANALYSED")
    if "NO_CLIPS" in err: return "NO_MOMENTS"
    if "DUPLICATE_FRAME_RATIO" in err: return "STATIC_VIDEO"
    if "INSUFFICIENT_FRAMES" in err: return "TOO_SHORT_FOR_ANALYSIS"
    if "TIMEOUT" in err.upper() or "TIMED_OUT" in err.upper(): return "ANALYSIS_TIMEOUT"
    codes=re.findall(r"(?:Error|Exception):\s*([A-Z][A-Z0-9_]{3,})",err)
    return "ANALYSIS_FAILED:"+(codes[-1] if codes else err.split(":",1)[0])[:60]

def build_event_library(runtime_dir,input_rows,work_dir,skipped=None):
    """Technical analysis (accepted V52 path). Returns (library path, library, cache status, analysed input rows).

    R3 changes against R2, all outside the pinned runtime modules:
    - the library is built only from the CURRENT inputs' results (R2 scanned every item ever analysed in this work
      folder, so a removed, replaced or Private file broke every later build);
    - a file the analysis cannot handle is skipped and reported instead of failing the whole reel;
    - progress is reported per file; the per-file timeout grows with the longest video (R2: fixed 120 s).
    """
    realmedia=work_dir/"realmedia"; eventdir=work_dir/"event_library"; libpath=eventdir/"EVENT_LIBRARY.json"
    ok,lib=valid_event_cache(libpath,input_rows)
    if ok: return libpath,lib,"reused_exact_cache",input_rows
    (realmedia/"items").mkdir(parents=True,exist_ok=True)
    batch_path=realmedia/"BATCH_RESULT.json"; batch_path.unlink(missing_ok=True)
    longest=max([float(r.get("duration_s") or 0) for r in input_rows]+[0.0])
    timeout=max(120.0,min(3600.0,3.0*longest))
    names=[realmedia_item_name(r["path"],r["sha256"]) for r in input_rows]
    cmd=[sys.executable,str(runtime_dir/"medeng_realmedia_pipeline_v14.py"),*[r["path"] for r in input_rows],
         "--output-root",str(realmedia),"--per-file-timeout-s",f"{timeout:g}","--max-width","960"]
    with (work_dir/"realmedia.stdout.log").open("w",encoding="utf-8",errors="replace") as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        try:
            while True:
                try: rc=proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired: rc=None
                done=sum((realmedia/"items"/n).is_dir() for n in names)
                if rc is not None: break
                i=min(done,len(names)-1)
                progress("analyze",i,len(names),input_rows[i]["name"])
        except BaseException:
            proc.kill(); raise
    try: batch=json.loads(batch_path.read_text(encoding="utf-8"))
    except Exception: batch=None
    if rc not in (0,2) or not batch: raise RuntimeError("REALMEDIA_PIPELINE_FAILED")
    by_src={}
    for r in batch.get("results",[]):
        try: by_src[str(Path(r["source"]).resolve())]=r
        except Exception: pass
    kept=[]; results=[]
    for row in input_rows:
        r=by_src.get(str(Path(row["path"]).resolve()))
        if r and r.get("status") in ("passed","skipped_exact_completed") and r.get("source_sha256")==row["sha256"] and r.get("item_dir"):
            kept.append(row); results.append(str(Path(r["item_dir"])/"PIPELINE_RESULT.json"))
        elif skipped is not None:
            skipped.append({"name":row["name"],"reason":_analysis_skip_reason(r)})
    if not kept: raise RuntimeError("NO_ANALYZABLE_VIDEO_FILES")
    progress("analyze",len(input_rows),len(input_rows),"building moment library")
    cp=subprocess.run([sys.executable,str(runtime_dir/"medeng_event_library_v20.py"),*results,
                       "--output-dir",str(eventdir)],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    (work_dir/"event_library.stdout.log").write_text((cp.stdout or "")+"\n"+(cp.stderr or ""),encoding="utf-8")
    if cp.returncode!=0: raise RuntimeError("EVENT_LIBRARY_FAILED")
    ok,lib=valid_event_cache(libpath,kept)
    if not ok: raise RuntimeError("EVENT_LIBRARY_POSTVERIFY_FAILED")
    return libpath,lib,"built",kept

def pairwise(v52,events):
    p={}; sig_start={}; sig_end={}
    for e in events:
        eid=str(e["event_id"]); clip=Path(e["clip_path"]); dur=float(e["duration_s"])
        sig_start[eid]=v52.signature(clip,min(.25,max(.05,dur*.1)))
        sig_end[eid]=v52.signature(clip,max(.05,dur-min(.25,max(.05,dur*.1))))
    for a in events:
        for b in events:
            ia,ib=str(a["event_id"]),str(b["event_id"])
            if ia!=ib: p[ia+"->"+ib]=float(np.linalg.norm(sig_end[ia]-sig_start[ib])/math.sqrt(8))
    return p

def camera_drop_rows(path,step=.25):
    cap=cv2.VideoCapture(str(path))
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 30.0); n=float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    dur=(n/fps) if fps>0 and n>0 else 0.0
    rows=[]; t=0.0
    while t < max(0.0,dur-1e-6):
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000.0); ok,fr=cap.read()
        if not ok: t+=step; continue
        gray=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); h,w=gray.shape
        mean=float(gray.mean()); dark=float((gray<16).mean()); bright=float((gray>239).mean())
        exposure=float(np.clip(1.0-abs(mean-128.0)/128.0-.8*(dark+bright),0,1))
        bottom=gray[3*h//4:]; upper=float(gray[:h//2].mean()); lower=float(gray[h//2:].mean())
        quality=float(.6*exposure+.4*np.clip(cv2.Laplacian(gray,cv2.CV_64F).var()/600.0,0,1))
        rows.append({"t":round(t,6),"quality":quality,"exposure":exposure,
                     "bottom_dark_fraction":float((bottom<50).mean()),
                     "lower_upper_ratio":float(lower/(upper+1e-9))})
        t+=step
    cap.release()
    return dur,rows

def apply_camera_drop(v52,dropmod,selected,work_dir):
    out=[]; decisions=[]; bdir=work_dir/"boundary_sanitized"; bdir.mkdir(parents=True,exist_ok=True)
    for e in selected:
        dur,rows=camera_drop_rows(e["clip_path"],.25)
        dec=dropmod.choose_camera_drop_trim(rows)
        decisions.append({"event_id":e["event_id"],"source_name":e["source_name"],"decision":dec})
        if not dec.get("trim"):
            out.append(e); continue
        cut=float(dec["cut_s"])
        if cut >= dur-.05:
            out.append(e); continue
        key=hashlib.sha256(f'{e["clip_sha256"]}|{cut:.3f}|CAMDROPV1'.encode()).hexdigest()[:20]
        clip=bdir/f"{key}.mp4"
        if not clip.is_file():
            tmp=bdir/f".{key}.tmp.mp4"
            cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y",
                               "-i",str(e["clip_path"]),"-t",f"{cut:.3f}",
                               "-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","fast","-crf","18",
                               "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
                               "-movflags","+faststart",str(tmp)],capture_output=True,text=True)
            if cp.returncode!=0: raise RuntimeError("CAMERA_DROP_PRETRIM_FAILED:"+cp.stderr[-800:])
            os.replace(tmp,clip)
        x=dict(e); x["clip_path"]=str(clip); x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha256_file(clip)
        x["duration_s"]=float(v52.ffprobe(clip)["format"]["duration"])
        x["end_s"]=round(float(x["start_s"])+x["duration_s"],3)
        x["camera_drop_trim"]=dec
        out.append(x)
    # Boundary correction is intentionally downstream of selection/ranking.
    # Never renormalize V52/semantic metrics here: a trim may change clip bytes/duration
    # and transition signatures, but it must not change the already-frozen selection score.
    return out,decisions

def video_seconds(ffmpeg,path,fps=30.0):
    """Exact length of a constant-30-fps segment's picture, by counting decoded frames (no ffprobe needed)."""
    cp=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(path),"-map","0:v:0","-vf","scale=8:8",
                       "-f","rawvideo","-pix_fmt","gray","-"],capture_output=True)
    n=len(cp.stdout)//64
    if cp.returncode!=0 or n<=0: raise RuntimeError("SEGMENT_DECODE_FAILED:"+str(path))
    return n/float(fps)

# R3 render assembly (R2 had A/V drift): the accepted V52 segments can carry up to ~0.1 s more or less sound than
# picture. R2 laid the sound of the next segment right after the previous sound, so the difference added up at every
# join (measured 0.39 s at the end of a 30 s reel on Windows). R3 first makes every segment's sound exactly as long as
# its picture (silence pad / trim), cross-fades with the same durations as the picture, and joins blocks with the
# concat filter, which keeps both streams aligned.
def _fit_audio(i,dur):
    return f"[{i}:a]aresample=48000,apad,atrim=end={dur:.6f},asetpts=N/SR/TB[n{i}]"

def full_quality_clip(v52,e,work_dir):
    """Technical mode: moments are found and scored on the accepted V12 preview clips (max 960 px wide, re-timed to
    25 fps, sound and picture re-zeroed separately -> sound up to ~45 ms early). The reel itself is cut from the
    ORIGINAL at the same source interval (as R2 already does in AI mode), so it keeps full resolution, the source
    frame rate and exact sync. Selection, order, pacing and boundary decisions are unchanged."""
    src=Path(e.get("source_path") or "")
    a=float(e.get("start_s") or 0.0); b=float(e.get("end_s") or 0.0)
    if not src.is_file() or b-a<0.3: return e
    key=hashlib.sha256(f'{e.get("source_sha256")}|{a:.3f}|{b:.3f}|FULLRES1'.encode()).hexdigest()[:20]
    d=work_dir/"full_quality"; d.mkdir(parents=True,exist_ok=True)
    clip=d/f"{key}.mp4"
    if not clip.is_file():
        tmp=d/f".{key}.tmp.mp4"
        cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y","-ss",f"{a:.3f}","-i",str(src),"-t",f"{b-a:.3f}",
                           "-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
                           "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
        if cp.returncode!=0:
            tmp.unlink(missing_ok=True); return e      # keep the preview clip rather than fail the reel
        os.replace(tmp,clip)
    x=dict(e); x["preview_clip_path"]=e.get("clip_path"); x["clip_path"]=str(clip)
    x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha256_file(clip)
    return x

def render_dissolve_block(v52,segs,durs,trans,out):
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    args=[v52.FFMPEG,"-hide_banner","-loglevel","error","-y"]
    for p in segs: args += ["-i",str(p)]
    if len(segs)==1:
        args += ["-filter_complex",_fit_audio(0,float(durs[0])),"-map","0:v","-map","[n0]","-c:v","copy",
                 "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(out)]
        cp=subprocess.run(args,capture_output=True,text=True)
        if cp.returncode!=0: raise RuntimeError("DISSOLVE_BLOCK_RENDER_FAILED:"+cp.stderr[-800:])
        return float(durs[0])
    filters=[_fit_audio(i,float(d)) for i,d in enumerate(durs)]; vprev="0:v"; aprev="n0"; cum=float(durs[0])
    for i in range(1,len(segs)):
        td=float(trans[i-1]["duration_s"]); vl=f"v{i}"; al=f"a{i}"; off=max(0.0,cum-td)
        if td<=0:
            # hard cut inside a block is not produced by the pacing plan, but keep it exact if it ever is
            filters.append(f"[{vprev}][{i}:v]concat=n=2:v=1:a=0[{vl}]")
            filters.append(f"[{aprev}][n{i}]concat=n=2:v=0:a=1[{al}]")
        else:
            filters.append(f"[{vprev}][{i}:v]xfade=transition=fade:duration={td:.3f}:offset={off:.3f}[{vl}]")
            filters.append(f"[{aprev}][n{i}]acrossfade=d={td:.3f}:c1=tri:c2=tri[{al}]")
        vprev=vl; aprev=al; cum+=float(durs[i])-max(0.0,td)
    args += ["-filter_complex",";".join(filters),"-map",f"[{vprev}]","-map",f"[{aprev}]",
             "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(out)]
    cp=subprocess.run(args,capture_output=True,text=True)
    if cp.returncode!=0: raise RuntimeError("DISSOLVE_BLOCK_RENDER_FAILED:"+cp.stderr[-800:])
    return cum

def render_mixed(v52,segs,durs,transitions,out,work):
    blocks=[]; start=0
    for i,tr in enumerate(transitions):
        if tr["kind"]=="HARD_CUT": blocks.append((start,i+1)); start=i+1
    blocks.append((start,len(segs)))
    bdir=Path(work)/"blocks"; bdir.mkdir(parents=True,exist_ok=True)
    bfs=[]; bds=[]
    for bi,(a,b) in enumerate(blocks,1):
        bp=bdir/f"block_{bi:02d}.mp4"
        dur=render_dissolve_block(v52,segs[a:b],durs[a:b],transitions[a:b-1] if b-a>1 else [],bp)
        bfs.append(bp); bds.append(dur)
    args=[v52.FFMPEG,"-hide_banner","-loglevel","error","-y"]
    for bp in bfs: args += ["-i",str(bp)]
    fc="".join(f"[{k}:v][{k}:a]" for k in range(len(bfs)))+f"concat=n={len(bfs)}:v=1:a=1[v][a]"
    cp=subprocess.run(args+["-filter_complex",fc,"-map","[v]","-map","[a]",
                            "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
                            "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(out)],
                      capture_output=True,text=True)
    if cp.returncode!=0: raise RuntimeError("FINAL_RENDER_FAILED:"+cp.stderr[-800:])
    dec=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-i",str(out),"-f","null","-"],capture_output=True,text=True)
    if dec.returncode!=0: raise RuntimeError("FINAL_DECODE_FAILED:"+dec.stderr[-800:])
    return sum(bds)

def resolve_profile(v52,requested,selected):
    requested=str(requested).lower()
    if requested in ("16x9","9x16"): return requested,"explicit"
    portrait=0
    for e in selected:
        vs=[x for x in v52.ffprobe(e["clip_path"])["streams"] if x.get("codec_type")=="video"][0]
        if int(vs["height"])>int(vs["width"]): portrait+=1
    if portrait*2>len(selected): return "9x16","auto_majority_portrait_%d_of_%d"%(portrait,len(selected))
    return "16x9","auto_majority_landscape_%d_of_%d"%(len(selected)-portrait,len(selected))

SELECTION_COMBINATION_BUDGET=10_000_000   # 30 s and shorter: exactly the R2/V52 search (max 8.65 M combinations)

def search_size(target,clip,trans,m):
    nominal=max(1,int(round((float(target)-trans)/max(.1,clip-trans))))
    return sum(math.comb(m,n) for n in range(max(1,nominal-2),min(m,nominal+2)+1))

def drop_overlapping(events,limit=.5):
    """Never show the same piece of a video twice: of two windows from one source that overlap by more than
    half of the shorter one, keep the higher-scored. (R2 could pick both; documented R3 change.)"""
    keep=[]; removed=[]
    for e in sorted(events,key=lambda x:(-float(x["v22_score"]),str(x["source_name"]),str(x["event_id"]))):
        a0,a1=float(e["start_s"]),float(e["end_s"]); clash=False
        for k in keep:
            if k["source_sha256"]!=e["source_sha256"]: continue
            b0,b1=float(k["start_s"]),float(k["end_s"])
            if min(a1,b1)-max(a0,b0) > limit*max(1e-6,min(a1-a0,b1-b0)): clash=True; break
        (removed if clash else keep).append(e)
    return keep,removed

def choose_moments(v52,events,target,warnings,exclude=(),clip=5.0,trans=.25):
    """V52 choose_for_target, bounded so a 60 s reel cannot hang for hours, with an honest shorter reel
    (warning LIMITED_TOTAL_FOOTAGE) when the footage cannot fill the requested length."""
    events,removed=drop_overlapping(events)   # before exclusions: a removed moment's near-twin never comes back
    if removed: warnings.append("OVERLAPPING_MOMENTS_DROPPED:%d"%len(removed))
    events=[e for e in events if str(e["event_id"]) not in exclude]
    if not events: raise RuntimeError("NO_MOMENTS_LEFT_AFTER_EXCLUSIONS")
    t=float(target)
    while True:
        m=min(30,len(events))
        while m>2 and search_size(t,clip,trans,m)>SELECTION_COMBINATION_BUDGET: m-=1
        try:
            sel=v52.choose_for_target(events,t,clip,trans,max_events=m)
        except Exception as exc:
            if "NO_DIVERSE_TARGET_COMBINATION" not in str(exc) or t<=clip: raise
            t=max(clip,t-(clip-trans)); continue
        if m<min(30,len(events)): warnings.append("SELECTION_SEARCH_TOP_%d"%m)
        if t<float(target): warnings.append("LIMITED_TOTAL_FOOTAGE")
        return sel

def manual_selection(pool,ids):
    byid={str(e["event_id"]):e for e in pool}
    missing=[i for i in ids if i not in byid]
    if missing: raise RuntimeError("EDIT_UNKNOWN_MOMENT:"+",".join(missing[:5]))
    if len(set(ids))!=len(ids): raise RuntimeError("EDIT_DUPLICATE_MOMENT")
    return [byid[i] for i in ids]

def run(args):
    global _PROGRESS_PATH
    started=time.perf_counter()
    _PROGRESS_PATH=Path(args.progress_file).resolve() if getattr(args,"progress_file",None) else None
    exclude={x.strip() for x in str(getattr(args,"exclude_events","") or "").split(",") if x.strip()}
    edits=json.loads(Path(args.edits).read_text(encoding="utf-8")) if getattr(args,"edits","") else {}
    manual=[str(x) for x in (edits.get("selection") or [])]
    trims={str(k):(float(v[0]),float(v[1])) for k,v in (edits.get("trims") or {}).items()}
    runtime=Path(args.runtime_dir).resolve()
    if str(runtime) not in sys.path: sys.path.insert(0,str(runtime))
    input_list=[x.strip() for x in Path(args.input_list).read_text(encoding="utf-8-sig").splitlines() if x.strip()] if args.input_list else None
    if (input_list is None)==(not args.input_dir): raise RuntimeError("GIVE_EXACTLY_ONE_OF_INPUT_DIR_OR_INPUT_LIST")
    input_dir=Path(args.input_dir or Path(input_list[0]).parent).resolve(); output_dir=Path(args.output_dir).resolve(); work_dir=Path(args.work_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True); work_dir.mkdir(parents=True,exist_ok=True)
    final_video=output_dir/"MediaEngine Reel.mp4"; final_result=output_dir/"MediaEngine Result.json"
    if final_video.exists() or final_result.exists(): raise RuntimeError("OUTPUT_ALREADY_EXISTS")

    if str(args.resolution)=="social_hd" and str(args.profile)=="16x9":
        raise RuntimeError("PRESET_NOT_ACCEPTED:social_hd is vertical 1080x1920 only")
    v52=load_module("medeng_targeted_auto_edit_v26",runtime/"medeng_targeted_auto_edit_v26.py")
    skipped_inputs=[]; warnings=[]
    input_rows=discover_input(input_dir,probe=v52.ffprobe,skipped=skipped_inputs,skip_sha=load_skip_sha(args.skip_sha_file),paths=input_list); fingerprint=input_fingerprint(input_rows)
    seqmod=load_module("p11_montage_sequence_shadow_v4",runtime/"p11_montage_sequence_shadow_v4.py")
    pacemod=load_module("p11_montage_pacing_shadow_v1",runtime/"p11_montage_pacing_shadow_v1.py")
    audiomod=load_module("p11_audio_coherence_shadow_v2",runtime/"p11_audio_coherence_shadow_v2.py")
    dropmod=load_module("p11_camera_drop_trim_shadow_v1",runtime/"p11_camera_drop_trim_shadow_v1.py")

    model_root=Path(os.environ.get("MEDENG_P11_MODEL_ROOT",r"D:\Archivist\sidecars\auto_edit\models"))
    adapter_root=Path(os.environ.get("MEDENG_P11_ADAPTER_ROOT",r"D:\Archivist\sidecars\auto_edit\shadow\P11_FAST_LOCAL_ADAPTER_V1"))
    semantic_preflight=semantic_runtime_preflight(runtime,model_root,adapter_root)
    semantic_mode=str(args.semantic).lower()
    if semantic_mode=="required" and not semantic_preflight["pass"]:
        raise RuntimeError("SEMANTIC_RUNTIME_REQUIRED_BUT_NOT_EXACT")
    use_semantic=semantic_mode!="off" and semantic_preflight["pass"]

    semantic_reports=[]
    if use_semantic:
        candidates,semantic_reports,input_rows=build_semantic_candidates(runtime,input_rows,work_dir,v52,model_root,adapter_root,skipped_inputs)
        pool=candidates
        progress("select",0,1,"choosing moments")
        selected=manual_selection(pool,manual) if manual else choose_moments(v52,candidates,float(args.target_seconds),warnings,exclude)
        selection_mode="FAST_LOCAL_SEMANTIC_SHADOW_V1"
        event_count=len(candidates); cache_status="semantic_candidate_cache"
    else:
        progress("analyze",0,len(input_rows),"technical analysis")
        libpath,lib,cache_status,input_rows=build_event_library(runtime,input_rows,work_dir,skipped_inputs)
        _,events=v52.load_library(libpath)
        scored=v52.score_events(events,work_dir/"V22_SCORE_CACHE.json")
        pool=scored
        progress("select",0,1,"choosing moments")
        selected=manual_selection(pool,manual) if manual else choose_moments(v52,scored,float(args.target_seconds),warnings,exclude)
        selection_mode="ACCEPTED_V52_TECHNICAL_AESTHETIC"
        event_count=int(lib["event_count"])
    if not selected: raise RuntimeError("NO_EVENTS_SELECTED")
    fingerprint=input_fingerprint(input_rows)   # files skipped during analysis are not part of this reel

    progress("trim",0,1,"checking clip boundaries")
    auto_part=[e for e in selected if str(e["event_id"]) not in trims]
    auto_part,boundary_decisions=apply_camera_drop(v52,dropmod,auto_part,work_dir)
    fixed={str(e["event_id"]):e for e in auto_part}
    selected=apply_manual_trims(v52,[fixed.get(str(e["event_id"]),e) for e in selected],trims,work_dir)
    profile,profile_reason=resolve_profile(v52,args.profile,selected)
    resolution=str(args.resolution)
    baseline=v52.order_continuity(selected); p=pairwise(v52,selected)
    if manual:
        seq={"algorithm":"MANUAL_ORDER","changed":False,"reason":"user_order","improvement":0.0,"guards":None,"order":[str(e["event_id"]) for e in selected]}
    else:
        seq=seqmod.plan_sequence(baseline,p,min_improvement=.025)
    by={str(e["event_id"]):e for e in selected}; order=[by[eid] for eid in seq["order"]]
    if sorted(seq["order"])!=sorted(str(e["event_id"]) for e in selected): raise RuntimeError("SEQUENCE_MEMBERSHIP_CHANGED")

    audio_rows=[]
    for e in order:
        a=audiomod.probe_audio_activity(e["clip_path"],ffmpeg=v52.FFMPEG,ffprobe=os.environ.get("MEDENG_FFPROBE","ffprobe"))
        audio_rows.append({"event_id":e["event_id"],"source_name":e["source_name"],**a})
    audio_decision=audiomod.plan_audio(audio_rows,args.audio); audio_mode=audio_decision["mode"]
    pace=pacemod.plan_pacing(order,float(args.target_seconds),p)
    if pace["event_ids"]!=[str(e["event_id"]) for e in order]: raise RuntimeError("PACING_ORDER_CHANGED")
    if trims:
        pace["durations_s"]=[round(float(e["duration_s"]),3) if str(e["event_id"]) in trims else d for e,d in zip(order,pace["durations_s"])]
        pace["manual_trim_ids"]=sorted(trims)
        planned=sum(pace["durations_s"])-sum(float(t["duration_s"]) for t in pace["transitions"])
        pace["expected_duration_s"]=round(planned,3); pace["target_error_s"]=round(abs(float(args.target_seconds)-planned),3)

    segcache=work_dir/"segment_cache_v2"; segcache.mkdir(parents=True,exist_ok=True)
    segs=[]; durs=[]; seg_meta=[]
    render_source="AI_CANDIDATE_CLIPS_FROM_ORIGINAL" if use_semantic else "ORIGINAL_FULL_QUALITY_RECUT"
    for si,(e,use) in enumerate(zip(order,pace["durations_s"])):
        progress("render",si,len(order),str(e["source_name"]))
        if not use_semantic and str(e["event_id"]) not in trims:   # manual trims are already cut from the original
            e=full_quality_clip(v52,e,work_dir)
        key=hashlib.sha256(json.dumps({"clip_sha256":e["clip_sha256"],"use_s":round(float(use),3),
                                     "audio":audio_mode,"profile":profile,"resolution":resolution,"fps":30,"quality":"high"},
                                    sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]
        seg=segcache/f"{key}.mp4"; meta_path=segcache/f"{key}.json"
        meta=None
        if seg.is_file() and meta_path.is_file():
            try:
                meta=json.loads(meta_path.read_text())
                if meta.get("sha256")!=sha256_file(seg): meta=None
            except Exception:
                meta=None
            if meta is None:   # damaged cache entry: rebuild this segment
                seg.unlink(missing_ok=True); meta_path.unlink(missing_ok=True)
        if meta is None:
            tmp=segcache/f".{key}.tmp.mp4"
            meta=v52.make_segment(e,tmp,profile,float(use),audio_content=audio_mode,
                                  output_resolution=resolution,output_fps=30,video_quality="high")
            os.replace(tmp,seg); meta["sha256"]=sha256_file(seg); atomic_json(meta_path,meta)
        segs.append(seg); durs.append(video_seconds(v52.FFMPEG,seg)); seg_meta.append(meta)

    progress("finish",0,1,"joining segments and verifying")
    render_dir=work_dir/"final_v2"; render_dir.mkdir(parents=True,exist_ok=True)
    temp_final=render_dir/(fingerprint+".mp4")
    if temp_final.exists(): temp_final.unlink()
    render_mixed(v52,segs,durs,pace["transitions"],temp_final,render_dir/(fingerprint+"_render"))
    fpr=v52.ffprobe(temp_final); actual=float(fpr["format"]["duration"]); video_sha=sha256_file(temp_final)
    if actual < float(args.target_seconds)-1.0 and "LIMITED_TOTAL_FOOTAGE" not in warnings:
        warnings.append("SHORTER_THAN_REQUESTED")
    fvs=[x for x in fpr["streams"] if x.get("codec_type")=="video"][0]; out_w,out_h=int(fvs["width"]),int(fvs["height"])
    if (out_w,out_h)!=tuple(v52.output_dimensions(profile,resolution)): raise RuntimeError("OUTPUT_DIMENSIONS_MISMATCH:%dx%d"%(out_w,out_h))
    os.replace(temp_final,final_video)
    if sha256_file(final_video)!=video_sha: raise RuntimeError("FINAL_COPY_VERIFY_FAILED")

    timeline=[]; t=0.0
    for i,(e,meta,d) in enumerate(zip(order,seg_meta,durs)):
        clip_dur=float(e.get("duration_s") or d); use=float(d)
        src_in=float(e.get("start_s") or 0.0)+max(0.0,(clip_dur-use)/2.0)
        if i>0: t-=float(pace["transitions"][i-1]["duration_s"])
        timeline.append({"position":i+1,"event_id":str(e["event_id"]),"source_name":e["source_name"],
                         "source_in_s":round(src_in,3),"source_out_s":round(src_in+use,3),
                         "reel_in_s":round(max(0.0,t),3),"reel_out_s":round(t+use,3),
                         "score":round(float(e["v22_score"]),6),"manual_trim":e.get("manual_trim"),
                         "camera_drop_trim":bool(e.get("camera_drop_trim",{}).get("trim")) if isinstance(e.get("camera_drop_trim"),dict) else False})
        t+=use
    chosen={x["event_id"] for x in timeline}
    pool_rows=sorted([{"event_id":str(e["event_id"]),"source_name":e.get("source_name"),
                       "start_s":round(float(e.get("start_s") or 0),3),"end_s":round(float(e.get("end_s") or 0),3),
                       "score":round(float(e.get("v22_score") or 0),6),"selected":str(e["event_id"]) in chosen,
                       "excluded":str(e["event_id"]) in exclude} for e in pool],key=lambda r:-r["score"])
    result={
        "contract":CONTRACT_VERSION,"status":"PASS",
        "segments":timeline,"candidate_pool":pool_rows,"excluded_event_ids":sorted(exclude),"manual_edits":edits,
        "skipped_inputs":skipped_inputs,"warnings":warnings,"render_source":render_source,
        "engine":{"orchestrator_sha256":sha256_file(Path(__file__)),"semantic_hook_sha256":SEMANTIC_HOOK_SHA},
        "input_folder":str(input_dir),"input_list":input_list,"input_fingerprint":fingerprint,"input_count":len(input_rows),
        "inputs":[{"name":r["name"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in input_rows],
        "target_seconds":float(args.target_seconds),"actual_duration_s":round(actual,3),
        "target_error_s":round(abs(actual-float(args.target_seconds)),3),
        "selection_mode":selection_mode,"semantic_requested":semantic_mode,
        "semantic_runtime":semantic_preflight,"semantic_reports":semantic_reports if use_semantic else [],
        "event_count":event_count,"event_cache":cache_status,
        "selected_count":len(order),"selected_sources":[e["source_name"] for e in order],
        "selected_event_ids":[str(e["event_id"]) for e in order],
        "selected_scores":[round(float(e["v22_score"]),6) for e in order],
        "boundary":{"algorithm":dropmod.ALGO_VERSION,
                    "trimmed_count":sum(bool(x["decision"].get("trim")) for x in boundary_decisions),
                    "decisions":boundary_decisions},
        "sequence":{"algorithm":seq["algorithm"],"changed":seq["changed"],"reason":seq["reason"],
                    "improvement":seq.get("improvement",0.0),"guards":seq.get("guards")},
        "pacing":{"algorithm":pace["algorithm"],"changed":pace["changed"],"reason":pace["reason"],
                  "durations_s":pace["durations_s"],"transitions":pace["transitions"],
                  "baseline_target_error_s":pace["baseline_target_error_s"],
                  "planned_target_error_s":pace["target_error_s"]},
        "audio":{"requested":args.audio,"applied":audio_mode,"decision":audio_decision,"activity":audio_rows},
        "output":{"name":final_video.name,"bytes":final_video.stat().st_size,"sha256":video_sha,
                  "profile":profile,"resolution":resolution,"fps":30,
                  "profile_requested":str(args.profile),"profile_reason":profile_reason,
                  "width":out_w,"height":out_h},
        "source_mutated":False,"network_request_performed":False,
        "semantic_best_moment_claim":bool(use_semantic),
        "claim_scope":"current run only; shadow prototype",
        "elapsed_s":round(time.perf_counter()-started,3),
    }
    atomic_json(final_result,result)
    names=sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names!=["MediaEngine Reel.mp4","MediaEngine Result.json"]: raise RuntimeError("OUTPUT_CONTRACT_VIOLATION:"+repr(names))
    progress("done",1,1,"ready")
    print(json.dumps({"status":"PASS","video":str(final_video),"result":str(final_result),
                      "selection_mode":selection_mode,"semantic":use_semantic,
                      "boundary_trimmed":result["boundary"]["trimmed_count"],
                      "duration_s":result["actual_duration_s"],"target_error_s":result["target_error_s"],
                      "selected_count":len(order),"audio":audio_mode},indent=2))
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",default=""); ap.add_argument("--output-dir",required=True)
    ap.add_argument("--input-list",default="",help="text file, one video path per line (instead of --input-dir)")
    ap.add_argument("--work-dir",required=True); ap.add_argument("--runtime-dir",required=True)
    ap.add_argument("--target-seconds",type=float,default=30.0)
    ap.add_argument("--audio",choices=("auto","source","mute"),default="auto")
    ap.add_argument("--semantic",choices=("auto","required","off"),default="auto")
    ap.add_argument("--profile",choices=("16x9","9x16","auto"),default="16x9")
    ap.add_argument("--resolution",choices=("standard","social_hd"),default="standard")
    ap.add_argument("--progress-file",default="")
    ap.add_argument("--exclude-events",default="")
    ap.add_argument("--skip-sha-file",default="",help="text file, one SHA-256 per line: inputs never to use (Private)")
    ap.add_argument("--edits",default="",help="JSON file: {selection:[event ids in order], trims:{id:[source_in_s,source_out_s]}}")
    a=ap.parse_args()
    try: run(a)
    except Exception as exc:
        progress("failed",0,0,type(exc).__name__+":"+str(exc))
        print(json.dumps({"status":"FAIL","error":type(exc).__name__+":"+str(exc)},indent=2)); raise

if __name__=="__main__":
    main()

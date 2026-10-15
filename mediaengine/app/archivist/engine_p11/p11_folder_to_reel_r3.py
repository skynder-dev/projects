from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path
import cv2
import numpy as np

CONTRACT_VERSION = "P11_FOLDER_TO_REEL_R3"
SUPPORTED = {".mp4",".mov",".m4v",".avi",".mkv",".webm",".mts",".m2ts",".ts",".3gp",".mpg",".mpeg",   # + camcorder / old phone
             ".wmv",".asf",".flv",".vob",".mod",".tod",".m2t",".dv"}                               # + older Windows, web, DVD, tape

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
    # own temp name per process and thread: caches shared by projects (and threads) never write the same temp file
    tmp=path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.part")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    for k in range(8):     # Windows: a virus scanner or the indexer may hold the file for a moment
        try:
            os.replace(tmp,path); return
        except PermissionError:
            if k==7: raise
            time.sleep(0.25*(k+1))

def _reused_sha(clip):
    """A cached cut is reused only when its bytes are what was written (a power cut or a virus scanner can leave a
    damaged file of the right size): its SHA-256, or None (then it is made again)."""
    clip=Path(clip)
    if not clip.is_file(): return None
    sha=sha256_file(clip)
    side=clip.with_name(clip.name+".sha256")
    try: want=side.read_text(encoding="utf-8").strip()
    except OSError: want=sha                       # cut before this check existed: taken as it is
    if sha==want: return sha
    clip.unlink(missing_ok=True); side.unlink(missing_ok=True)
    return None

def _made_sha(clip):
    sha=sha256_file(clip)
    try: Path(clip).with_name(Path(clip).name+".sha256").write_text(sha,encoding="utf-8")
    except OSError: pass
    return sha

_PROGRESS_PATH=None
_STAGE_T={"stage":None,"t":None,"seconds":{}}
_NO_ETA=object()
def progress(stage,done=0,total=0,message="",eta_s=_NO_ETA):
    """Write the current stage for the app. Never raises: progress must not break a render.
    Also keeps the time spent per stage (result.stage_seconds) so slow steps on a real PC can be seen.
    eta_s: seconds left in this stage as the engine sees it (None = not known yet); left out = the app estimates."""
    now=time.perf_counter()
    if _STAGE_T["stage"]!=stage:
        if _STAGE_T["stage"] is not None:
            sec=_STAGE_T["seconds"]; sec[_STAGE_T["stage"]]=round(sec.get(_STAGE_T["stage"],0.0)+now-_STAGE_T["t"],2)
        _STAGE_T["stage"]=stage; _STAGE_T["t"]=now
    if _PROGRESS_PATH is None: return
    d={"stage":stage,"done":int(done),"total":int(total),"message":str(message)[:300],"at":time.time()}
    if eta_s is not _NO_ETA: d["eta_s"]=None if eta_s is None else max(0.0,round(float(eta_s),1))
    try: atomic_json(_PROGRESS_PATH,d)
    except Exception: pass

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _load_sha_cache(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    except (OSError,ValueError): return {}

def _cached_sha(p,size,cache):
    """SHA-256 of a source video, from the work folder's list when its size and change time are as when it was read
    (a variant or another length of the same reel does not read every video again: minutes on a big folder)."""
    key=str(p); mt=p.stat().st_mtime_ns; c=cache.get(key) if isinstance(cache,dict) else None
    if isinstance(c,dict) and c.get("bytes")==size and c.get("mtime_ns")==mt and len(str(c.get("sha256") or ""))==64:
        return c["sha256"]
    digest=sha256_file(p)
    if isinstance(cache,dict): cache[key]={"bytes":size,"mtime_ns":mt,"sha256":digest}
    return digest

def discover_input(folder, probe=None, skipped=None, skip_sha=None, paths=None, sha_cache=None, sha_seed=None):
    """Input videos: every supported file in <folder>, or exactly <paths> (files the user chose; names must be unique).
    sha_cache: a JSON file in the work folder that remembers the SHA-256 of each source by size and change time."""
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
    rows=[]; seen={}; cache=_load_sha_cache(sha_cache); cache0=json.dumps(cache,sort_keys=True)
    if sha_seed:      # the project's own list from before the list was shared
        for k,v in _load_sha_cache(sha_seed).items(): cache.setdefault(k,v)
    for i,p in enumerate(vids,1):
        progress("inputs",i-1,len(vids),p.name)
        try:
            size=p.stat().st_size; dur=0.0; wh=(0,0)
            if size<1024: raise RuntimeError("FILE_TOO_SMALL")
            if probe is not None:
                info=probe(p)
                vs=[x for x in info.get("streams",[]) if x.get("codec_type")=="video"]
                if not vs: raise RuntimeError("NO_VIDEO_STREAM")
                wh=(int(vs[0].get("width") or 0),int(vs[0].get("height") or 0))
                dur=float(info.get("format",{}).get("duration") or 0)
                if dur<0.5: raise RuntimeError("TOO_SHORT")
            digest=_cached_sha(p,size,cache)
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
        rows.append({"name":p.name,"path":str(p),"bytes":size,"sha256":digest,"duration_s":dur,"width":wh[0],"height":wh[1]})
    if sha_cache and json.dumps(cache,sort_keys=True)!=cache0:
        try: atomic_json(sha_cache,cache)
        except OSError: pass                     # only a speed-up: never a reason to fail the build
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

_AUDIO_MAP={}

def sound_args(v52,src,dur):
    """Sound of a cut from the original: the first audio track FFmpeg can decode (a track it cannot read, e.g. an
    iPhone "spatial audio" track, must not fail the cut - "-map 0:a?" took every track), padded with silence to the
    picture's length (sound ending before the moment ends gave an empty or short segment)."""
    key=str(src)
    if key not in _AUDIO_MAP:
        try:
            st=[x for x in v52.ffprobe(Path(src))["streams"] if x.get("codec_type")=="audio"]
            ok=[x for x in st if str(x.get("codec_name") or "none") not in ("none","unknown")]
            _AUDIO_MAP[key]=f"0:{ok[0]['index']}" if ok else None
        except Exception:
            _AUDIO_MAP[key]="0:a:0?"
    m=_AUDIO_MAP[key]
    return ["-map",m,"-af",f"apad=whole_dur={float(dur):.3f}"] if m else []

# AI moments are cut from the original once and the reel is rendered from these clips: the same settings as the
# full-quality recut. Measured on 4K (H.264 100 Mbit/s and HEVC 10-bit): 1.9-2.2x faster than "fast"/crf 18, with
# a slightly better picture (SSIM 0.9963 vs 0.9955) and ~9 % larger files; 4K clips were most of the AI analysis time.
# sync-lookahead=0: x264's threaded lookahead made the same cut differ now and then (FFmpeg 7, sound in the same
# command: 2-3 runs in 12 on one clip); without it 30 of 30 were bit-identical, at the same speed on 4K. A clip cut
# again (the shared cache removed it) is then the same clip, with the same measurements and the same choice.
CANDIDATE_X264=("-preset","veryfast","-crf","16","-x264-params","sync-lookahead=0")

_CLIP_STATS={"cut":0,"reused":0}
_CLIP_LOCK=threading.Lock()

def _adopt(legacy_dir,out_dir,names):
    """Cache files a project made before the cache was shared: moved into the shared place (same drive: a rename), so
    the videos analysed for it are not analysed again, and nothing is kept twice."""
    if not legacy_dir: return
    for n in names:
        a=Path(legacy_dir)/n; b=Path(out_dir)/n
        if a.is_file() and not b.exists():
            try: os.replace(a,b)
            except OSError:
                try: shutil.copyfile(a,b)
                except OSError: pass

def extract_candidate_clip(v52, src, source_sha, source_name, c, out_dir, tag="SEMANTIC_V2", legacy_dir=None, origin_sha=None):
    start=float(c["start_s"]); end=float(c["end_s"]); dur=max(.25,end-start)
    raw=f"{source_sha}|{start:.3f}|{end:.3f}|{tag}".encode()
    eid=hashlib.sha256(raw).hexdigest()[:24]
    out_dir.mkdir(parents=True,exist_ok=True)
    clip=out_dir/f"{eid}.mp4"
    meta=out_dir/f"{eid}.json"
    if legacy_dir and not clip.is_file(): _adopt(legacy_dir,out_dir,(clip.name,meta.name))
    if clip.is_file() and meta.is_file():
        try:
            m=json.loads(meta.read_text())
            if m.get("clip_sha256")==sha256_file(clip) and m.get("source_sha256")==source_sha:
                with _CLIP_LOCK: _CLIP_STATS["reused"]+=1
                try: os.utime(meta)          # last use: the app removes the longest unused clips when the cache is big
                except OSError: pass
                # same content, maybe under a new name or in a new place (another project, a moved data folder):
                # report where it is now
                return dict(m,source_name=source_name,source_path=str(src),clip_path=str(clip))
        except Exception:
            pass
        # damaged cache entry (power loss, disk error): rebuild it instead of failing the project forever
        clip.unlink(missing_ok=True); meta.unlink(missing_ok=True)
    tmp=out_dir/f".{eid}.{os.getpid()}.{threading.get_ident()}.tmp.mp4"
    if tmp.exists(): tmp.unlink()
    cmd=[v52.FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",f"{start:.3f}","-i",str(src),"-t",f"{dur:.3f}",
         "-map","0:v:0",*sound_args(v52,src,dur),"-c:v","libx264",*CANDIDATE_X264,
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
    if origin_sha and origin_sha!=source_sha: m["origin_sha256"]=origin_sha   # a stand-in (camcorder remux): the real file
    atomic_json(meta,m)
    with _CLIP_LOCK: _CLIP_STATS["cut"]+=1
    return m

def _shared_root():
    """Where the app keeps what the AI found in each video for every project (MEDENG_AI_SHARED_CACHE), or None."""
    v=os.environ.get("MEDENG_AI_SHARED_CACHE")
    return Path(v) if v else None

def _prefill_v22(v52,specs,cache_path,shared=None):
    """The accepted scorer (v52.score_events) measures every moment clip again, one after another (OpenCV reads each
    clip; 4K clips take seconds each). Its measurements depend on the clip alone: kept per clip SHA-256 in the shared
    cache, the missing ones measured in parallel, all written into the project's score cache in the scorer's own
    format - score_events then finds every clip there and computes exactly as before."""
    cache_path=Path(cache_path); cache={}
    try:
        o=json.loads(cache_path.read_text(encoding="utf-8"))
        if o.get("scorer_version")==v52.SCORER_VERSION: cache=o.get("events") or {}
    except Exception:
        cache={}
    need={}
    for e in specs:
        if (cache.get(e["event_id"]) or {}).get("clip_sha256")!=e["clip_sha256"]: need[e["event_id"]]=e
    if not need: return 0      # clips measured now (not found in either cache)
    mdir=(shared/"v22_metrics") if shared else None
    measured=[]
    def get(e):
        f=(mdir/(e["clip_sha256"]+".json")) if mdir else None
        if f is not None and f.is_file():
            try:
                o=json.loads(f.read_text(encoding="utf-8"))
                if o.get("scorer_version")==v52.SCORER_VERSION and o.get("clip_sha256")==e["clip_sha256"]: return e,o["metrics"]
            except Exception:
                pass
        m=v52.sample_clip(Path(e["clip_path"])); measured.append(1)
        if f is not None:
            try: atomic_json(f,{"scorer_version":v52.SCORER_VERSION,"clip_sha256":e["clip_sha256"],"metrics":m})
            except OSError: pass
        return e,m
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(4,(os.cpu_count() or 2)//2))) as ex:
        got=list(ex.map(get,need.values()))
    for e,m in got: cache[e["event_id"]]={"clip_sha256":e["clip_sha256"],"metrics":m}
    tmp=cache_path.with_name(f"{cache_path.name}.{os.getpid()}.part")
    try:       # only a speed-up: a virus scanner holding the file must not fail the build (score_events measures then)
        tmp.parent.mkdir(parents=True,exist_ok=True)
        tmp.write_text(json.dumps({"candidate":v52.CANDIDATE,"scorer_version":v52.SCORER_VERSION,"events":cache},indent=2),encoding="utf-8")
        os.replace(tmp,cache_path)
    except OSError:
        try: tmp.unlink(missing_ok=True)
        except OSError: pass
    return len(measured)

def _share_fast_session():
    """The accepted hook opens the AI model for every video (file checks and a new ONNX session: ~1-2 s, and with
    videos in parallel three sessions using all cores each). One session for the whole build instead - the hook and
    the adapter files stay as accepted (hash-checked), the session is the same, so are the results. ONNX Runtime
    sessions may be run from several threads at once."""
    try:
        import p11_fast_onnx_adapter as fa
    except Exception:
        return
    if getattr(fa.load_runtime,"_medeng_shared",False): return
    orig=fa.load_runtime; cache={}; lock=threading.Lock()
    def shared(profile_dir):
        key=str(Path(profile_dir).resolve())
        with lock:
            if key not in cache: cache[key]=orig(profile_dir)
            return cache[key]
    shared._medeng_shared=True
    fa.load_runtime=shared

def build_semantic_candidates(runtime,input_rows,work_dir,v52,model_root,adapter_root,skipped=None):
    if str(adapter_root) not in sys.path: sys.path.insert(0,str(adapter_root))
    sem=load_module("medeng_event_semantic_v7",runtime/"medeng_event_semantic_v7.py")
    _share_fast_session()
    # what the AI found in each video (by its SHA-256) and the moment clips: shared by all projects when the app says
    # where - a new reel from videos analysed for another reel analyses and cuts nothing again
    shared=_shared_root()
    legacy_reports=work_dir/"semantic_reports"; legacy_cands=work_dir/"semantic_candidates"
    reports_dir=(shared/"semantic_reports") if shared else legacy_reports; reports_dir.mkdir(parents=True,exist_ok=True)
    candidates_dir=(shared/"semantic_candidates") if shared else legacy_cands
    legacy_c=legacy_cands if shared and legacy_cands.is_dir() else None
    stats0=dict(_CLIP_STATS)
    specs=[]
    reports=[]
    kept=[]

    timing={"analyse_s":0.0,"clips_s":0.0,"videos_analysed":0,"workers":1}
    tlock=threading.Lock()

    def one(row):
        """One video: its AI report (cached by SHA-256) and its candidate clips. Returns (report, row_specs, skip)."""
        if 0<float(row.get("duration_s") or 0)<2.0:
            # under 2 s the accepted scout gets fewer than its 3 frames (1 s apart) and always refuses: say so at once
            # (seen: five 1-2 s drone shots tried again at every variant)
            return None,None,{"name":row["name"],"reason":"TOO_SHORT_FOR_ANALYSIS"}
        rp=reports_dir/(row["sha256"]+".json")
        if shared and not rp.is_file(): _adopt(legacy_reports,reports_dir,(rp.name,))
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
                t_=time.perf_counter()
                report=sem.analyze_video(Path(row["path"]),"SELECT_BEST","FAST_LOCAL",model_root,
                                         v52.FFMPEG,os.environ.get("MEDENG_FFPROBE","ffprobe"))
                atomic_json(rp,{"source_sha256":row["sha256"],"hook_sha256":SEMANTIC_HOOK_SHA,
                                "model_sha256":MODEL_SHA,"report":report})
                if row.get("origin_sha256") and row["origin_sha256"]!=row["sha256"]:
                    # a stand-in (camcorder remux): which real file it is, so the app can forget it with the real file
                    try: rp.with_suffix(".origin").write_text(row["origin_sha256"],encoding="utf-8")
                    except OSError: pass
                with tlock: timing["analyse_s"]+=time.perf_counter()-t_; timing["videos_analysed"]+=1
            row_specs=[]
            t_=time.perf_counter()
            for rank,c in enumerate(report.get("ranked",[]),1):
                cc=dict(c); cc["_source_rank"]=rank
                row_specs.append(extract_candidate_clip(v52,Path(row["path"]),row["sha256"],row["name"],cc,candidates_dir,
                                                        legacy_dir=legacy_c,origin_sha=row.get("origin_sha256")))
            with tlock: timing["clips_s"]+=time.perf_counter()-t_
        except Exception as exc:
            # one unreadable file must not sink the whole reel: skip it and say so
            return None,None,{"name":row["name"],"reason":_semantic_skip_reason(exc,row)}
        if not row_specs:
            return report,None,{"name":row["name"],"reason":"NO_MOMENTS"}
        return report,row_specs,None

    # Several videos at once on a PC with many cores and enough memory (each video is analysed on its own, so the
    # moments are the same as one after another; R2 took them one by one and left most of a 16-core PC idle).
    workers=max(1,min(3,(os.cpu_count() or 2)//4,int(_total_ram_gb()//6) or 1,len(input_rows)))
    try: workers=max(1,int(os.environ.get("MEDENG_SEMANTIC_WORKERS") or workers))
    except ValueError: pass
    results=[None]*len(input_rows)
    timing["workers"]=workers
    # videos analysed before (a report in the cache) or too short to try go first and take seconds; the time left is
    # measured on the new ones only: their average time x how many are left / how many run at once (a mix of 12 known
    # and 6 new 4K videos once said "less than a minute" for 10 minutes of work)
    def known(row):
        try:
            if 0<float(row.get("duration_s") or 0)<2.0: return True
        except (TypeError,ValueError): pass
        n=row["sha256"]+".json"
        for f in ((reports_dir/n),)+(((legacy_reports/n),) if shared is not None else ()):
            try:          # valid as one() takes it (a stale report means analysing again: not quick)
                obj=json.loads(f.read_text())
                if obj.get("source_sha256")==row["sha256"] and obj.get("hook_sha256")==SEMANTIC_HOOK_SHA and obj.get("model_sha256")==MODEL_SHA:
                    return True
            except Exception:
                pass
        return False
    flags=[known(r) for r in input_rows]
    order=[i for i in range(len(input_rows)) if flags[i]]+[i for i in range(len(input_rows)) if not flags[i]]
    n_known=sum(flags); new_total=len(input_rows)-n_known; durs=[]
    def eta(k):
        if new_total==0: return _NO_ETA          # nothing new: the app estimates from the rate of this stage
        if not durs: return None
        left=new_total-k
        return 0.0 if left<=0 else (sum(durs)/len(durs))*max(1.0,left/max(1,workers))
    def timed(idx):
        t0=time.perf_counter(); r=one(input_rows[idx]); return r,time.perf_counter()-t0
    done_n=0
    for idx in order[:n_known]:
        progress("analyze",done_n,len(input_rows),input_rows[idx]["name"],eta_s=(_NO_ETA if new_total==0 else None))
        results[idx]=one(input_rows[idx]); done_n+=1
    rest=order[n_known:]
    if workers<=1:
        for k,idx in enumerate(rest):
            progress("analyze",done_n,len(input_rows),input_rows[idx]["name"],eta_s=eta(k))
            results[idx],d=timed(idx); durs.append(d); done_n+=1
    else:
        import concurrent.futures
        # the same video twice (a copy under another name) shares its report and clip files: only the first one is
        # analysed in parallel, the copies afterwards from the cache (two threads never write the same file)
        seen=set(); first=[]; copies=[]
        for idx in rest:
            (copies if input_rows[idx]["sha256"] in seen else first).append(idx); seen.add(input_rows[idx]["sha256"])
        progress("analyze",done_n,len(input_rows),"analysing videos",eta_s=None)
        k=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs={ex.submit(timed,idx):idx for idx in first}
            for fut in concurrent.futures.as_completed(futs):
                results[futs[fut]],d=fut.result(); durs.append(d); done_n+=1; k+=1
                progress("analyze",done_n,len(input_rows),"analysing videos",eta_s=eta(k))
        for idx in copies:
            results[idx]=one(input_rows[idx]); done_n+=1; k+=1
            progress("analyze",done_n,len(input_rows),"analysing videos",eta_s=eta(k))
    for row,(report,row_specs,skip) in zip(input_rows,results):
        if skip is not None:
            if skipped is not None: skipped.append(skip)
            continue
        kept.append(row)
        reports.append({"source_name":row["name"],"source_sha256":row["sha256"],
                        "rank1":report["ranked"][0] if report.get("ranked") else None})
        specs.extend(row_specs)
    if not specs: raise RuntimeError("NO_SEMANTIC_CANDIDATES")
    t_=time.perf_counter()
    progress("analyze",len(input_rows),len(input_rows),"measuring the moments",eta_s=None)
    timing["clips_measured"]=_prefill_v22(v52,specs,work_dir/"SEMANTIC_CANDIDATE_V22_SCORE_CACHE.json",shared)
    technical=v52.score_events(specs,work_dir/"SEMANTIC_CANDIDATE_V22_SCORE_CACHE.json")
    timing["score_s"]=time.perf_counter()-t_
    timing["clips_cut"]=_CLIP_STATS["cut"]-stats0["cut"]; timing["clips_cached"]=_CLIP_STATS["reused"]-stats0["reused"]
    timing["shared_cache"]=bool(shared)
    SEM_TIMING.clear(); SEM_TIMING.update(timing)
    # Shadow selection score: exact semantic per-source final score is primary, accepted V52 technical score is tie-break.
    for e in technical:
        e["technical_v22_score"]=float(e["v22_score"])
        e["v22_score"]=round(.80*float(e["semantic_source_final_score"])+.20*float(e["technical_v22_score"]),6)
        e["selection_score_kind"]="SEMANTIC_80_TECHNICAL_20_SHADOW_V1"
    return technical,reports,kept

def _semantic_skip_reason(exc,row):
    """Like _analysis_skip_reason, for the AI modes: a clip of a second or two (a drone's short shots) is "too short",
    not "could not be analysed" (seen: 5 of 18 drone videos, 1.5-2.6 s, the folder page already said "too short")."""
    err=str(exc)
    if "SCOUT_INSUFFICIENT_FRAMES" in err: return "TOO_SHORT_FOR_ANALYSIS"
    if "DUPLICATE_FRAME_RATIO" in err: return "STATIC_VIDEO"
    try:      # too few frames in the closer look at a moment: too short only for a video of a few seconds
        if "INSUFFICIENT_FRAMES" in err and 0<float(row.get("duration_s") or 0)<2.5: return "TOO_SHORT_FOR_ANALYSIS"
    except (TypeError,ValueError): pass
    return "ANALYSIS_FAILED:"+(err.split(":",1)[0] or type(exc).__name__)[:60]

def _total_ram_gb():
    """Installed memory (GB); 16 when it cannot be read."""
    try:
        if os.name=="nt":
            import ctypes
            class MS(ctypes.Structure):
                _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),("ullTotalPhys",ctypes.c_ulonglong),
                          ("ullAvailPhys",ctypes.c_ulonglong),("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
                          ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
            m=MS(); m.dwLength=ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)): return m.ullTotalPhys/1e9
        else:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"): return int(line.split()[1])/1e6
    except Exception:
        pass
    return 16.0

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

# ---------------------------------------------------------------- AI+ (PE-Core L/14): a separate, optional mode
def pe_model_dir(model_root):
    return Path(os.environ.get("MEDENG_P13_PE_DIR") or (Path(model_root)/"PE_CORE_L14"))

def pe_runtime_preflight(pe_dir):
    """The AI+ model files with their exact sizes and SHA-256 (p13_pe_core_contract)."""
    try:
        import p13_pe_core_contract as pc
        ident=pc.validate(Path(pe_dir),True)
        return {"pass":True,"model_dir":str(pe_dir),"identity":ident}
    except Exception as exc:
        return {"pass":False,"model_dir":str(pe_dir),"error":str(exc)[:200]}

def make_pe_scorer(pe_dir):
    import p13_pe_core_adapter as pa
    # every logical CPU (the engine runs below normal priority): measured in the model lab on Windows,
    # 1.46 s per frame instead of 1.66 s with onnxruntime's default; never slower on Linux
    return pa.PECoreScorer(Path(pe_dir),full_check=False,threads=os.cpu_count() or None)   # files were checked by the preflight

class AiplusLoadError(RuntimeError):
    pass

class PeTextCache:
    """Text embeddings of the fixed AI+ descriptions, kept on disk per model and code version: after the first build
    the text part of the model (355 MB) is not opened again - less memory and a faster start. Exact float32 values,
    so rankings are the same as with the model."""
    def __init__(self,path,load,identity):
        self.path=Path(path); self.load=load; self._identity=identity; self.data={}
        try:
            with np.load(self.path,allow_pickle=False) as z:
                self.data={k:np.asarray(z[k],np.float32) for k in z.files}
        except Exception:
            self.data={}
    @staticmethod
    def _key(text):
        return "t"+hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
    @property
    def identity(self):
        return self._identity()
    def encode_text(self,texts):
        texts=list(texts)
        missing=[t for t in texts if self._key(t) not in self.data]
        if missing:
            emb=np.asarray(self.load().encode_text(missing),np.float32)
            for t,row in zip(missing,emb): self.data[self._key(t)]=row
            self._save()
        return np.stack([self.data[self._key(t)] for t in texts]).astype(np.float32)
    def _save(self):
        """Best effort (a busy or read-only disk only means the text part is opened again next time); merges what
        another build wrote meanwhile; own temp name, so two builds never write the same temp file."""
        tmp=self.path.with_name(f"{self.path.stem}.{os.getpid()}.{time.time_ns()}.tmp.npz")
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            try:
                with np.load(self.path,allow_pickle=False) as z:
                    for k in z.files: self.data.setdefault(k,np.asarray(z[k],np.float32))
            except Exception:
                pass
            np.savez(tmp,**self.data)
            for attempt in range(5):
                try:
                    os.replace(tmp,self.path); return
                except PermissionError:
                    time.sleep(.2*(attempt+1))
        except Exception:
            pass
        finally:
            try: tmp.unlink(missing_ok=True)
            except Exception: pass

SEM_TIMING={}    # where the AI / AI+ analysis time goes (result.semantic_timing)

def build_semantic_candidates_pe(runtime,input_rows,work_dir,v52,pe_dir,skipped=None,theme=None,warnings=None):
    """Like build_semantic_candidates, with the AI+ hook. Own caches and moment ids, so AI and AI+ never mix.
    Every scout frame is embedded once per video (semantic_scout_pe/<sha>.json + .npy); a ranking per theme is cached
    on top (semantic_reports_pe/<sha>.<theme>.json) - a new theme for analysed videos needs no frame encoding."""
    import p13_event_semantic_pe as hook
    import p13_pe_core_contract as pc
    v7=load_module("medeng_event_semantic_v7",runtime/"medeng_event_semantic_v7.py")
    here=Path(hook.__file__)
    # what the model saw depends on the adapter, the contract, the scout step and the model - not on the ranking
    scout_key=hook.scout_key()
    tkey=theme or "general"
    rank_key=scout_key+"|"+sha256_file(here)+"|"+hook.prompt_key(theme)
    SEM_TIMING.clear(); SEM_TIMING.update(scout_embed_s=0.0,rank_s=0.0,clips_s=0.0,clips_cut=0,clips_cached=0,score_s=0.0)
    # what the model saw in each video (by its SHA-256): shared by all projects when the app says where
    # (MEDENG_P13_SCOUT_CACHE) - a new reel from videos analysed for another reel needs no frame looked at again
    scout_dir=Path(os.environ.get("MEDENG_P13_SCOUT_CACHE") or (work_dir/"semantic_scout_pe")); scout_dir.mkdir(parents=True,exist_ok=True)
    reports_dir=work_dir/"semantic_reports_pe"; reports_dir.mkdir(parents=True,exist_ok=True)
    shared=_shared_root(); legacy_cands=work_dir/"semantic_candidates_pe"
    candidates_dir=(shared/"semantic_candidates_pe") if shared else legacy_cands      # the moment clips: for every project
    legacy_c=legacy_cands if shared and legacy_cands.is_dir() else None
    state={"scorer":None}
    def scorer_with(part):
        try:
            if state["scorer"] is None:
                state["scorer"]=make_pe_scorer(pe_dir)
            getattr(state["scorer"],part)     # opens that part of the model now: a failure is the model, not a video
        except Exception as exc:     # memory, damaged runtime: one clear error, not "no moments" for every video
            raise AiplusLoadError("AIPLUS_MODEL_LOAD_FAILED:"+type(exc).__name__+":"+str(exc)[:160]) from exc
        return state["scorer"]
    def identity():
        if state["scorer"] is not None: return getattr(state["scorer"],"identity",None)
        if "identity" not in state:
            try:
                state["identity"]=dict(pc.validate(Path(pe_dir),False)); state["identity"]["adapter"]="P13_PE_CORE_ONNX_ADAPTER_V1"
            except Exception:
                state["identity"]={"profile":pc.PROFILE}
        return state["identity"]
    # shared by all projects when the app says where (MEDENG_P13_TEXT_CACHE), else next to the other caches
    text_dir=Path(os.environ.get("MEDENG_P13_TEXT_CACHE") or (work_dir/"semantic_text_pe"))
    texts=PeTextCache(text_dir/(scout_key[:24]+".npz"),lambda: scorer_with("text"),identity)
    specs=[]; reports=[]; kept=[]; deferred=[]
    def make_spec(row,cc,rank):
        t_=time.perf_counter(); n_=_CLIP_STATS["cut"]
        spec=extract_candidate_clip(v52,Path(row["path"]),row["sha256"],row["name"],cc,candidates_dir,"SEMANTIC_PE1",legacy_dir=legacy_c,
                                    origin_sha=row.get("origin_sha256"))
        SEM_TIMING["clips_s"]+=time.perf_counter()-t_
        SEM_TIMING["clips_cut" if _CLIP_STATS["cut"]>n_ else "clips_cached"]+=1
        # a cached clip keeps its cut; its scores always come from the current ranking (theme, descriptions)
        spec.update({"semantic_margin_raw":float(cc["semantic_margin_raw"]),"semantic_source_final_score":float(cc["final_score"]),
                     "semantic_scout_score":float(cc["semantic_scout_score"]),"semantic_source_rank":int(rank),
                     "technical_prominence":round(.50*float(cc["scout_eventness"])+.35*float(cc["scout_novelty"])+.15*float(cc["scout_quality"]),6)})
        return spec
    # videos the model has seen before (in the shared cache, or ranked for this theme) go first and take seconds; the
    # time left is measured on the others (their average time x how many are left); results stay in the input order
    n_rows=len(input_rows)
    def seen_before(row):
        # a valid report for this theme: then only its clips are checked (a scout file alone still means ranking and
        # cutting every moment clip - most of the time on 4K)
        try:
            if 0<float(row.get("duration_s") or 0)<2.0: return True
            obj=json.loads((reports_dir/f"{row['sha256']}.{tkey}.json").read_text())
            return obj.get("source_sha256")==row["sha256"] and obj.get("key")==rank_key
        except Exception:
            return False
    flags=[seen_before(r) for r in input_rows]
    order=[i for i in range(n_rows) if flags[i]]+[i for i in range(n_rows) if not flags[i]]
    new_total=n_rows-sum(flags); durs=[]
    def eta():
        if new_total==0: return _NO_ETA          # nothing new: the app estimates from the rate of this stage
        if not durs: return None
        return (sum(durs)/len(durs))*max(0,new_total-len(durs))
    outcome={}
    for pos,idx in enumerate(order):
        row=input_rows[idx]; fresh=not flags[idx]; t_row=time.perf_counter()
        progress("analyze",pos,n_rows,row["name"],eta_s=eta())
        row_deferred=[]
        try:
            rp=reports_dir/f"{row['sha256']}.{tkey}.json"
            report=None
            if rp.is_file():
                try:
                    obj=json.loads(rp.read_text())
                    if obj.get("source_sha256")==row["sha256"] and obj.get("key")==rank_key: report=obj["report"]
                except Exception:
                    report=None
            if report is None:
                info,emb=hook.read_scout(scout_dir,row["sha256"],scout_key)
                if info is None:
                    if state["scorer"] is None or state["scorer"]._vision is None:
                        progress("analyze",pos,n_rows,"loading the AI+ model",eta_s=eta())
                    sc=scorer_with("vision")
                    progress("analyze",pos,n_rows,row["name"],eta_s=eta())
                    t_=time.perf_counter()
                    info,emb=hook.scout(v7,sc,Path(row["path"]),v52.FFMPEG,os.environ.get("MEDENG_FFPROBE","ffprobe"))
                    SEM_TIMING["scout_embed_s"]+=time.perf_counter()-t_
                    hook.write_scout(scout_dir,row["sha256"],scout_key,info,emb)
                t_=time.perf_counter()
                report=hook.rank(v7,texts,Path(row["path"]),info,emb,theme,v52.FFMPEG)
                SEM_TIMING["rank_s"]+=time.perf_counter()-t_
                atomic_json(rp,{"source_sha256":row["sha256"],"key":rank_key,"report":report})
            row_specs=[]
            for rank,c in enumerate(report.get("ranked",[]),1):
                cc=dict(c); cc["_source_rank"]=rank
                if theme and float(cc["semantic_margin_raw"])<=0:
                    row_deferred.append((row,cc,rank)); continue      # cut only if too few moments match the theme
                row_specs.append(make_spec(row,cc,rank))
        except AiplusLoadError:
            raise
        except Exception as exc:
            outcome[idx]=("skip",{"name":row["name"],"reason":_semantic_skip_reason(exc,row)})
            continue
        finally:
            if fresh: durs.append(time.perf_counter()-t_row)
        if not row_specs and not (theme and report.get("ranked")):     # with a theme: maybe nothing in it matches
            outcome[idx]=("skip",{"name":row["name"],"reason":"NO_MOMENTS"}); continue
        outcome[idx]=("ok",report,row_specs,row_deferred)
    for idx,row in enumerate(input_rows):          # in the input order, as when they were taken one after another
        o=outcome.get(idx)
        if o is None: continue
        if o[0]=="skip":
            if skipped is not None: skipped.append(o[1])
            continue
        _,report,row_specs,row_deferred=o
        deferred.extend(row_deferred)
        kept.append(row)
        reports.append({"source_name":row["name"],"source_sha256":row["sha256"],"theme":theme or "",
                        "rank1":report["ranked"][0] if report.get("ranked") else None})
        specs.extend(row_specs)
    if theme and len(specs)<3:          # too few moments match the theme: the others are cut after all
        for i_,(row,cc,rank) in enumerate(deferred):
            progress("analyze",i_,len(deferred),row["name"])
            try:
                specs.append(make_spec(row,cc,rank))
            except Exception:
                continue
    progress("analyze",n_rows,n_rows,"measuring the moments",eta_s=None)
    if not specs: raise RuntimeError("NO_SEMANTIC_CANDIDATES")
    t_=time.perf_counter()
    _prefill_v22(v52,specs,work_dir/"SEMANTIC_PE_CANDIDATE_V22_SCORE_CACHE.json",shared)
    technical=v52.score_events(specs,work_dir/"SEMANTIC_PE_CANDIDATE_V22_SCORE_CACHE.json")
    SEM_TIMING["score_s"]+=time.perf_counter()-t_
    if not theme:
        # how clearly a moment shows something worth seeing is compared across ALL videos too (absolute margins): the
        # best window of a video of twigs or a sign no longer counts as much as the best window of a wedding dance
        # (real-footage check, 2026-10-13); the video's own ranking and the accepted technical score keep their say
        gm=robust01([float(e["semantic_margin_raw"]) for e in technical])
        for e,g in zip(technical,gm):
            e["technical_v22_score"]=float(e["v22_score"])
            e["semantic_global_0_1"]=round(float(g),6)
            e["v22_score"]=round(.45*float(g)+.35*float(e["semantic_source_final_score"])+.20*float(e["technical_v22_score"]),6)
            e["selection_score_kind"]="PE_GLOBAL_45_SOURCE_35_TECHNICAL_20_V1"
        return technical,reports,kept
    # a theme: how well a moment matches is compared across ALL videos (absolute margins), so a folder's sea shots win
    # over another video's best non-sea moment; moments that do not match at all are left out when enough match
    tn=robust01([float(e["semantic_margin_raw"]) for e in technical])
    for e,t in zip(technical,tn):
        e["technical_v22_score"]=float(e["v22_score"])
        e["theme_match_0_1"]=round(float(t),6)
        e["v22_score"]=round(.55*float(t)+.25*float(e["semantic_source_final_score"])+.20*float(e["technical_v22_score"]),6)
        e["selection_score_kind"]="PE_THEME_55_FINAL_25_TECHNICAL_20_V1"
    matching=[e for e in technical if float(e["semantic_margin_raw"])>0]
    if warnings is not None:
        warnings.append("THEME:%s:%d_MATCHING_MOMENTS"%(theme,len(matching)))
    if len(matching)>=3:
        return matching,reports,kept
    if warnings is not None: warnings.append("THEME_FEW_MATCHES:%s"%theme)
    return technical,reports,kept

def apply_manual_trims(v52,selected,trims,work_dir):
    """User mark-in/mark-out in SOURCE time. Re-extracted from the source so a moment can also be widened."""
    out=[]; tdir=work_dir/"manual_trims"; tdir.mkdir(parents=True,exist_ok=True)
    for e in selected:
        eid=str(e["event_id"])
        if eid not in trims: out.append(e); continue
        a,b=trims[eid]; src=Path(e.get("recut_path") or e.get("source_path") or "")   # recut_path: MP4 stand-in of a camcorder stream
        if not src.is_file(): raise RuntimeError("EDIT_SOURCE_MISSING:"+eid)
        dur=float(v52.ffprobe(src)["format"]["duration"])
        a=max(0.0,min(float(a),dur)); b=max(0.0,min(float(b),dur))
        if b-a<0.5: raise RuntimeError("EDIT_TRIM_TOO_SHORT:"+eid)
        key=hashlib.sha256(f'{e.get("source_sha256")}|{a:.3f}|{b:.3f}|MANUALTRIM1'.encode()).hexdigest()[:20]
        clip=tdir/f"{key}.mp4"
        sha=_reused_sha(clip)
        if sha is None:
            tmp=tdir/f".{key}.tmp.mp4"
            cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y","-ss",f"{a:.3f}","-i",str(src),"-t",f"{b-a:.3f}",
                               "-map","0:v:0",*sound_args(v52,src,b-a),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
                               "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
            if cp.returncode!=0 or "Video:" not in _video_line(v52.FFMPEG,tmp):
                tmp.unlink(missing_ok=True); raise RuntimeError("EDIT_TRIM_FAILED:"+(cp.stderr or "no picture in the cut")[-600:])
            os.replace(tmp,clip); sha=_made_sha(clip)
        x=dict(e); x["clip_path"]=str(clip); x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha
        x["duration_s"]=float(v52.ffprobe(clip)["format"]["duration"]); x["start_s"]=round(a,3); x["end_s"]=round(a+x["duration_s"],3)
        x["manual_trim"]=[round(a,3),round(b,3)]
        out.append(x)
    return out

def realmedia_item_name(path,sha):
    """Item folder name used by medeng_realmedia_pipeline_v14.safe_name (kept in sync; used for progress only)."""
    s=re.sub(r'[^A-Za-z0-9._-]+','_',Path(path).name)[:100] or 'media'
    return f'{s}__{sha[:12]}'

_CONTENT_VERDICTS=("NO_MOMENTS","STATIC_VIDEO","TOO_SHORT_FOR_ANALYSIS")

def _analysis_skip_reason(r):
    """Short machine reason for a file the technical analysis could not use (no paths, no logs)."""
    err=str((r or {}).get("error") or (r or {}).get("status") or "NOT_ANALYSED")
    if "NO_CLIPS" in err: return "NO_MOMENTS"
    if "DUPLICATE_FRAME_RATIO" in err: return "STATIC_VIDEO"
    if "INSUFFICIENT_FRAMES" in err: return "TOO_SHORT_FOR_ANALYSIS"
    if "TIMEOUT" in err.upper() or "TIMED_OUT" in err.upper(): return "ANALYSIS_TIMEOUT"
    codes=re.findall(r"(?:Error|Exception):\s*([A-Z][A-Z0-9_]{3,})",err)
    return "ANALYSIS_FAILED:"+(codes[-1] if codes else err.split(":",1)[0])[:60]

REMUX_EXT={".mts",".m2ts",".ts",".mpg",".mpeg",".vob",".mod",".tod",".m2t"}   # MPEG-2 program/transport streams

def _remux_alias(r,alias):
    """Camcorder transport streams (.MTS/.M2TS/.TS/.MPG): OpenCV inside the accepted analysis cannot count or seek their
    frames (the scout reports too few frames), so they are analysed as an MP4 with the same pictures (video stream
    copied; sound to AAC). The reel itself is still cut from the original."""
    ff=os.environ.get("MEDENG_FFMPEG","ffmpeg")
    tmp=alias.with_name(alias.stem+".part.mp4"); tmp.unlink(missing_ok=True)
    for vcodec in (["-c:v","copy"],["-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p"]):
        cp=subprocess.run([ff,"-hide_banner","-loglevel","error","-y","-i",r["path"],"-map","0:v:0","-map","0:a:0?",*vcodec,
                           "-c:a","aac","-b:a","192k","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
        if cp.returncode==0 and tmp.is_file() and tmp.stat().st_size>1024:
            os.replace(tmp,alias); return True
    tmp.unlink(missing_ok=True); return False

def _even_alias(r,alias):
    """A picture with an odd width or height (a video cropped in a phone's gallery, 1079x1917): H.264 4:2:0 cannot
    store it, so the accepted analysis and every cut failed. Analysed and cut from a copy one pixel smaller."""
    ff=os.environ.get("MEDENG_FFMPEG","ffmpeg")
    tmp=alias.with_name(alias.stem+".part.mp4"); tmp.unlink(missing_ok=True)
    cp=subprocess.run([ff,"-hide_banner","-loglevel","error","-y","-i",r["path"],"-map","0:v:0","-map","0:a:0?",
                       "-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2","-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",
                       "-c:a","aac","-b:a","192k","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
    if cp.returncode==0 and tmp.is_file() and tmp.stat().st_size>1024:
        os.replace(tmp,alias); return True
    tmp.unlink(missing_ok=True); return False

def analysis_aliases(rows,work_dir,long_names=True):
    """Stand-ins the accepted analysis can handle, mapped back to the real files afterwards.
    - Windows without long-path support (the default) cannot reach the analysis files of a video with a long name:
      the accepted pipeline names its folders after the video (up to ~330 characters, limit 260). Such videos are
      analysed under a short name: a hard link (same drive), else a copy (up to 4 GB).
    - Camcorder transport streams are analysed as an MP4 remux (see _remux_alias); pictures with an odd width or
      height as a copy one pixel smaller (see _even_alias).
    Returns (rows for the analysis, {stand-in name: original row})."""
    force=os.environ.get("MEDENG_FORCE_SHORT_ALIAS")=="1"
    realmedia=work_dir/"realmedia"; adir=work_dir/"in"
    out=[]; back={}; wanted=set()
    for r in rows:
        name=r["name"]; ext=Path(name).suffix.lower()
        projected=len(str(realmedia))+10+min(len(name),100)+14+10+len(name)+45   # realmedia\gN\items\<item>\previews\<name>\...
        odd=bool(int(r.get("width") or 0)%2 or int(r.get("height") or 0)%2)
        remux=ext in REMUX_EXT or odd
        if not remux and not (long_names and (force or (os.name=="nt" and projected>240))):
            out.append(r); continue
        alias_name=f"v_{r['sha256'][:12]}{'.mp4' if remux else ext}"
        alias=adir/alias_name; use=None; sha=r["sha256"]; size=int(r["bytes"])
        try:
            adir.mkdir(parents=True,exist_ok=True)
            if remux:
                side=alias.with_name(alias.name+".sha256")
                if not (alias.is_file() and side.is_file()):
                    side.unlink(missing_ok=True)
                    if (_even_alias(r,alias) if odd else _remux_alias(r,alias)):
                        side.write_text(sha256_file(alias),encoding="utf-8")
                if alias.is_file() and side.is_file():
                    use=str(alias); sha=side.read_text(encoding="utf-8").strip(); size=alias.stat().st_size
                    wanted.add(side.name)
            elif alias.is_file() and alias.stat().st_size==int(r["bytes"]):
                use=str(alias)
            else:
                alias.unlink(missing_ok=True)
                try:
                    os.link(r["path"],alias); use=str(alias)
                except OSError:
                    # no 8.3 short path here: the analysis resolves it back to the long name (the long-path problem
                    # returns and the library no longer matches the input) - a copy is used instead
                    if int(r["bytes"])<=(4<<30):
                        shutil.copyfile(r["path"],alias); use=str(alias)
        except OSError:
            use=None
        if use:
            wanted.add(alias_name)
            a=dict(r,name=Path(use).name,path=use,sha256=sha,bytes=size,origin_sha256=r["sha256"]); out.append(a); back[a["name"]]=r
        else:
            out.append(r)
    try:
        for f in adir.iterdir():
            if f.name not in wanted: f.unlink(missing_ok=True)   # e.g. a video since marked Private or removed
    except OSError:
        pass
    return out,back

def build_event_library(runtime_dir,input_rows,work_dir,skipped=None):
    """Technical analysis (accepted V52 path). Returns (library path, library, cache status, analysed input rows).

    R3 changes against R2, all outside the pinned runtime modules:
    - the library is built only from the CURRENT inputs' results (R2 scanned every item ever analysed in this work
      folder, so a removed, replaced or Private file broke every later build);
    - a file the analysis cannot handle is skipped and reported instead of failing the whole reel;
    - progress is reported per file; the per-file timeout grows with the longest video (R2: fixed 120 s).
    """
    realmedia=work_dir/"realmedia"; eventdir=work_dir/"event_library"; libpath=eventdir/"EVENT_LIBRARY.json"
    skipfile=eventdir/"ANALYSIS_SKIPPED.json"   # files the analysis could not use last time (same name + SHA-256)
    # what the video itself is (no moments, a still image, too short) is remembered for good; a failure that may go
    # away (disk full, out of memory, a locked file, a time-out) only for 6 hours - then it is tried again
    try: before={(x["name"],x["sha256"]):x["reason"] for x in json.loads(skipfile.read_text(encoding="utf-8"))
                 if x["reason"] in _CONTENT_VERDICTS or time.time()-float(x.get("at") or 0)<6*3600}
    except Exception: before={}
    known=[r for r in input_rows if (r["name"],r["sha256"]) not in before]
    if known:
        ok,lib=valid_event_cache(libpath,known)
        if ok:
            # an unusable file (e.g. a 1 s accidental clip) must not make every later build analyse everything again
            if skipped is not None:
                skipped.extend({"name":r["name"],"reason":before[(r["name"],r["sha256"])]} for r in input_rows if (r["name"],r["sha256"]) in before)
            return libpath,lib,"reused_exact_cache",known
    longest=max([float(r.get("duration_s") or 0) for r in input_rows]+[0.0])
    timeout=max(120.0,min(6*3600.0,3.0*longest))   # an hour-long 4K 60 fps video can take over an hour on a slow PC
    # Several analysis processes in parallel (R2: one after another). A video always goes to the same group
    # (by its SHA-256), so a later build reuses its finished analysis.
    try: k_env=int(os.environ.get("MEDENG_ANALYSIS_WORKERS") or 0)
    except ValueError: k_env=0
    # not limited by the number of inputs: adding or removing a video must not move the others to another group
    # (that analysed them again); empty groups are simply not started
    K=max(1,k_env or max(1,min(4,(os.cpu_count() or 2)//2)))
    groups=[[] for _ in range(K)]
    for r in input_rows: groups[int(r["sha256"][:8],16)%K].append(r)
    names=[(realmedia/f"g{int(r['sha256'][:8],16)%K}"/"items"/realmedia_item_name(r["path"],r["sha256"])) for r in input_rows]
    procs=[]; logs=[]; waiting=[]
    # how many groups run AT ONCE: each runs 8 FFmpeg readers, a 4K HEVC reader takes ~0.5 GB - on an 8 GB PC four
    # groups at once swapped or lost frames. The groups themselves (which video goes where) stay the same.
    at_once=max(1,min(K,int(_total_ram_gb()//4) or 1))
    try:
        for k,g in enumerate(groups):
            if not g: continue
            root=realmedia/f"g{k}"; (root/"items").mkdir(parents=True,exist_ok=True)
            (root/"BATCH_RESULT.json").unlink(missing_ok=True)
            # a run cancelled earlier may have left a half-made item (".name.part"); the accepted pipeline refuses one
            # it did not start itself (another path): removed here - nothing else works in this project's folder now
            for part in (root/"items").glob(".*.part"):
                shutil.rmtree(part,ignore_errors=True)
            # --repair-corrupt-completed: a finished analysis that no longer fits (the folder was moved, a file of it
            # was damaged) is analysed again instead of failing every later build; no effect when all is well
            cmd=[sys.executable,str(runtime_dir/"medeng_realmedia_pipeline_v14.py"),*[r["path"] for r in g],
                 "--output-root",str(root),"--per-file-timeout-s",f"{timeout:g}","--max-width","960","--repair-corrupt-completed"]
            waiting.append((k,root,cmd))
        def launch(k,root,cmd):
            log=(work_dir/f"realmedia.g{k}.log").open("w",encoding="utf-8",errors="replace"); logs.append(log)
            procs.append((root,subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)))
        while True:
            while waiting and sum(1 for _,pr in procs if pr.poll() is None)<at_once:
                launch(*waiting.pop(0))
            running=[pr for _,pr in procs if pr.poll() is None]
            done=sum(n.is_dir() for n in names)
            if not running and not waiting: break
            i=min(done,len(names)-1)
            progress("analyze",i,len(names),"analysing videos" if K>1 else input_rows[i]["name"])
            time.sleep(1.0)
    except BaseException:
        for _,pr in procs:
            try: pr.kill()
            except Exception: pass
        raise
    finally:
        for log in logs: log.close()
    by_src={}
    for root,pr in procs:
        try: batch=json.loads((root/"BATCH_RESULT.json").read_text(encoding="utf-8"))
        except Exception: batch=None
        if pr.returncode not in (0,2) or not batch: raise RuntimeError("REALMEDIA_PIPELINE_FAILED")
        for r in batch.get("results",[]):
            try: by_src[str(Path(r["source"]).resolve())]=r
            except Exception: pass
    kept=[]; results=[]; unusable=[]
    for row in input_rows:
        r=by_src.get(str(Path(row["path"]).resolve()))
        if r and r.get("status") in ("passed","skipped_exact_completed") and r.get("source_sha256")==row["sha256"] and r.get("item_dir"):
            kept.append(row); results.append(str(Path(r["item_dir"])/"PIPELINE_RESULT.json"))
        else:
            unusable.append({"name":row["name"],"sha256":row["sha256"],"reason":_analysis_skip_reason(r)})
            if skipped is not None: skipped.append({"name":row["name"],"reason":unusable[-1]["reason"]})
    if not kept: raise RuntimeError("NO_ANALYZABLE_VIDEO_FILES")
    progress("analyze",len(input_rows),len(input_rows),"building moment library")
    cp=subprocess.run([sys.executable,str(runtime_dir/"medeng_event_library_v20.py"),*results,
                       "--output-dir",str(eventdir)],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    (work_dir/"event_library.stdout.log").write_text((cp.stdout or "")+"\n"+(cp.stderr or ""),encoding="utf-8")
    if cp.returncode!=0: raise RuntimeError("EVENT_LIBRARY_FAILED")
    ok,lib=valid_event_cache(libpath,kept)
    if not ok: raise RuntimeError("EVENT_LIBRARY_POSTVERIFY_FAILED")
    for root,_ in procs:          # repaired items keep their broken old copy in quarantine: not needed any more
        shutil.rmtree(root/"quarantine",ignore_errors=True)
    try: atomic_json(skipfile,[dict(x,at=round(time.time())) for x in unusable if x["reason"]!="ANALYSIS_TIMEOUT"])   # a slow PC may manage next time
    except OSError: pass
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

def _camera_drop_row(t,fr):
    gray=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); h,w=gray.shape
    mean=float(gray.mean()); dark=float((gray<16).mean()); bright=float((gray>239).mean())
    exposure=float(np.clip(1.0-abs(mean-128.0)/128.0-.8*(dark+bright),0,1))
    bottom=gray[3*h//4:]; upper=float(gray[:h//2].mean()); lower=float(gray[h//2:].mean())
    quality=float(.6*exposure+.4*np.clip(cv2.Laplacian(gray,cv2.CV_64F).var()/600.0,0,1))
    return {"t":round(t,6),"quality":quality,"exposure":exposure,
            "bottom_dark_fraction":float((bottom<50).mean()),
            "lower_upper_ratio":float(lower/(upper+1e-9))}

def _drop_times(cap,step):
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 30.0); n=float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    dur=(n/fps) if fps>0 and n>0 else 0.0
    times=[]; t=0.0
    while t < max(0.0,dur-1e-6):
        times.append(t); t+=step
    return fps,dur,times

def camera_drop_rows(path,step=.25):
    """Picture rows every <step> s of a clip, each by a seek (the accepted way: every seek decodes from the clip's start
    when the clip is one GOP - a 4K clip took ~20 s on a CI runner)."""
    cap=cv2.VideoCapture(str(path))
    fps,dur,times=_drop_times(cap,step)
    rows=[]
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000.0); ok,fr=cap.read()
        if not ok: continue
        rows.append(_camera_drop_row(t,fr))
    cap.release()
    return dur,rows

def _seek_row(path,t):
    cap=cv2.VideoCapture(str(path))
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000.0); ok,fr=cap.read()
        return _camera_drop_row(t,fr) if ok else None
    finally:
        cap.release()

def camera_drop_rows_fast(path,step=.25):
    """The same rows from ONE pass through the clip: a seek to t lands on frame int(t*fps+0.5) (OpenCV's FFmpeg reader).
    Checked on every clip: two of the rows (the second and the middle one) are measured again by a real seek and
    must be identical, else the clip is measured the accepted way - the result is always the accepted one."""
    cap=cv2.VideoCapture(str(path))
    fps,dur,times=_drop_times(cap,step)
    want={}
    for t in times: want.setdefault(int(t*fps+0.5),[]).append(t)
    got={}; i=0; last=max(want) if want else -1
    while i<=last:
        ok,fr=cap.read()
        if not ok: break
        for t in want.get(i,()): got[t]=_camera_drop_row(t,fr)
        i+=1
    cap.release()
    kept_t=[t for t in times if t in got]; rows=[got[t] for t in kept_t]
    missing=[t for t in times if t not in got]
    # a time past the last frame (29.97 fps: 165 frames are 5.505 s, so 5.5 s is asked for): the seek finds nothing
    # there either and the accepted way leaves it out - checked by a real seek like the rows
    if missing and (len(missing)>2 or _seek_row(path,missing[0]) is not None):
        return camera_drop_rows(path,step)
    for k in sorted({1,len(rows)//2}):
        if k<len(rows):
            r=_seek_row(path,kept_t[k])
            if r is None or r!=rows[k]:
                return camera_drop_rows(path,step)
    return dur,rows

def camera_drop_rows_cached(path,sha,cache_dir,step=.25):
    """camera_drop_rows of a clip, remembered by the clip's SHA-256 (a variant or another length looks at the same
    clips again: about a second each). The same numbers as measuring again."""
    f=Path(cache_dir)/f"{sha}_{step:g}.json" if sha else None
    if f is not None:
        try:
            d=json.loads(f.read_text(encoding="utf-8")); return float(d["dur"]),list(d["rows"])
        except (OSError,ValueError,KeyError,TypeError): pass
    dur,rows=camera_drop_rows_fast(path,step)
    if f is not None:
        try: atomic_json(f,{"dur":dur,"rows":rows})
        except OSError: pass
    return dur,rows

def apply_camera_drop(v52,dropmod,selected,work_dir):
    out=[]; decisions=[]; bdir=work_dir/"boundary_sanitized"; bdir.mkdir(parents=True,exist_ok=True)
    for e in selected:
        # by the clip's SHA-256: shared by all projects when the app says where (a new reel from the same moments)
        sh_=_shared_root()
        dur,rows=camera_drop_rows_cached(e["clip_path"],e.get("clip_sha256"),(sh_/"camera_drop_rows") if sh_ else work_dir/"camera_drop_rows",.25)
        dec=dropmod.choose_camera_drop_trim(rows)
        decisions.append({"event_id":e["event_id"],"source_name":e["source_name"],"decision":dec})
        if not dec.get("trim"):
            out.append(e); continue
        cut=float(dec["cut_s"])
        if cut >= dur-.05:
            out.append(e); continue
        key=hashlib.sha256(f'{e["clip_sha256"]}|{cut:.3f}|CAMDROPV1'.encode()).hexdigest()[:20]
        clip=bdir/f"{key}.mp4"
        sha=_reused_sha(clip)
        if sha is None:
            tmp=bdir/f".{key}.tmp.mp4"
            cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y",
                               "-i",str(e["clip_path"]),"-t",f"{cut:.3f}",
                               "-map","0:v:0","-map","0:a:0?","-c:v","libx264","-preset","fast","-crf","18",
                               "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
                               "-movflags","+faststart",str(tmp)],capture_output=True,text=True)
            if cp.returncode!=0: raise RuntimeError("CAMERA_DROP_PRETRIM_FAILED:"+cp.stderr[-800:])
            os.replace(tmp,clip); sha=_made_sha(clip)
        x=dict(e); x["clip_path"]=str(clip); x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha
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

def video_frames(ffmpeg,path):
    """The frames really stored in a segment (no frame repeated to fill a gap): a segment cut by the accepted cutter
    can start one frame late (its first frame at 0.033 s - seen with the Windows FFmpeg build), and video_seconds then
    counts that gap as a frame."""
    cp=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(path),"-map","0:v:0","-fps_mode","passthrough","-vf","scale=8:8",
                       "-f","rawvideo","-pix_fmt","gray","-"],capture_output=True)
    n=len(cp.stdout)//64
    if cp.returncode!=0 or n<=0: raise RuntimeError("SEGMENT_DECODE_FAILED:"+str(path))
    return n

# R3 render assembly (R2 had A/V drift): the accepted V52 segments can carry up to ~0.1 s more or less sound than
# picture. R2 laid the sound of the next segment right after the previous sound, so the difference added up at every
# join (measured 0.39 s at the end of a 30 s reel on Windows). R3 first makes every segment's sound exactly as long as
# its picture (silence pad / trim), cross-fades with the same durations as the picture, and joins blocks with the
# concat filter, which keeps both streams aligned.
def _fit_audio(i,dur):
    # sample-exact: time-based apad/atrim left the sound up to ~60 ms short per segment
    # async + first_pts=0: sound that starts after the picture (or has a gap) keeps its place in time - silence is put
    # in front / in the gap. "asetpts=N/SR/TB" alone moved such sound to the start (measured: every beep 336 ms early
    # for a clip whose sound began 0.378 s after its picture).
    n=max(1,int(round(float(dur)*48000)))
    return f"[{i}:a]aresample=48000:async=1:first_pts=0,apad=whole_len={n},atrim=end_sample={n},asetpts=N/SR/TB[n{i}]"

# HDR phone video (iPhone HLG / Dolby Vision 8.4, Android HDR10 PQ) shown on a normal screen: convert, do not just
# re-encode the 10-bit numbers as if they were normal video (that looks grey and dark).
HDR_TO_SDR={
    "HLG":"zscale=tin=arib-std-b67:t=bt709:pin=bt2020:p=bt709:min=bt2020nc:m=bt709:r=tv,format=yuv420p",
    "PQ":"zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p",
}
_HDR_CACHE={}; _ZSCALE=[]

def zscale_available(ffmpeg):
    if not _ZSCALE:
        try:
            cp=subprocess.run([ffmpeg,"-hide_banner","-filters"],capture_output=True,text=True,timeout=60)
            _ZSCALE.append(" zscale " in (cp.stdout or ""))
        except Exception:
            _ZSCALE.append(False)
    return _ZSCALE[0]

def _video_line(ffmpeg,src):
    key=str(src)
    if key not in _HDR_CACHE:
        try:
            cp=subprocess.run([ffmpeg,"-hide_banner","-i",key],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
            _HDR_CACHE[key]=next((l for l in (cp.stderr or "").splitlines() if "Video:" in l),"")
        except Exception:
            _HDR_CACHE[key]=""
    return _HDR_CACHE[key]

def hdr_kind(ffmpeg,src):
    """'HLG', 'PQ' or None, from the transfer characteristic ffmpeg reports for the first video stream."""
    line=_video_line(ffmpeg,src)
    return "HLG" if "arib-std-b67" in line else ("PQ" if "smpte2084" in line else None)

def is_interlaced(ffmpeg,src):
    """Camcorder (AVCHD .MTS, DV, broadcast) video stored as fields: shown on a computer it needs de-interlacing."""
    line=_video_line(ffmpeg,src)
    return any(x in line for x in ("top first","bottom first","top coded first","bottom coded first"))

def pixel_aspect(ffmpeg,src):
    """Sample (pixel) aspect ratio of the first video stream, 1.0 = square pixels. Camcorder and disc video often
    stores a wide picture in narrow pixels: HDV/AVCHD 1440x1080 (4:3 -> 16:9), DVD/DV 720x576 or 720x480
    (16:15, 64:45, 8:9, 32:27). The accepted render scales stored pixels, so such video came out squeezed."""
    m=re.search(r"SAR (\d+):(\d+)",_video_line(ffmpeg,src))
    if not m: return 1.0
    a,b=int(m.group(1)),int(m.group(2))
    return a/b if a>0 and b>0 else 1.0

def is_anamorphic(ffmpeg,src):
    return abs(pixel_aspect(ffmpeg,src)-1.0)>0.02     # 404:405 after a phone crop is not worth a re-encode

SQUARE_PIXELS="scale=w=trunc(iw*sar/2+0.5)*2:h=ih,setsar=1"   # widen to the picture's real shape (1440x1080 4:3 -> 1920x1080)

_FQ_FALLBACK=[]   # sources whose moments had to stay at analysis-preview quality (reported, not hidden)

def full_quality_clip(v52,e,work_dir,hdr=None,deinterlace=False,square=False):
    """Technical mode: moments are found and scored on the accepted V12 preview clips (max 960 px wide, re-timed to
    25 fps, sound and picture re-zeroed separately -> sound up to ~45 ms early). The reel itself is cut from the
    ORIGINAL at the same source interval (as R2 already does in AI mode), so it keeps full resolution, the source
    frame rate and exact sync. Selection, order, pacing and boundary decisions are unchanged."""
    src=Path(e.get("recut_path") or e.get("source_path") or "")   # recut_path: MP4 stand-in of a camcorder stream
    a=float(e.get("start_s") or 0.0); b=float(e.get("end_s") or 0.0)
    if b-a<0.3: return e
    if not src.is_file():
        _FQ_FALLBACK.append(str(e.get("source_name"))); return e
    key=hashlib.sha256(f'{e.get("source_sha256")}|{a:.3f}|{b:.3f}|FULLRES1|{hdr or "SDR"}{"|DEINT" if deinterlace else ""}{"|SQ" if square else ""}'.encode()).hexdigest()[:20]
    d=work_dir/"full_quality"; d.mkdir(parents=True,exist_ok=True)
    clip=d/f"{key}.mp4"
    sha=_reused_sha(clip)
    if sha is None:
        tmp=d/f".{key}.tmp.mp4"
        chain=(["bwdif=mode=send_frame:parity=auto:deint=interlaced"] if deinterlace else [])+([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else [])+([SQUARE_PIXELS] if square else [])
        conv=(["-vf",",".join(chain)] if chain else [])+(["-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709"] if hdr in HDR_TO_SDR else [])
        cp=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-y","-ss",f"{a:.3f}","-i",str(src),"-t",f"{b-a:.3f}",
                           "-map","0:v:0",*sound_args(v52,src,b-a),*conv,"-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",
                           "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(tmp)],capture_output=True,text=True)
        if cp.returncode!=0 or "Video:" not in _video_line(v52.FFMPEG,tmp):
            tmp.unlink(missing_ok=True); _FQ_FALLBACK.append(str(e.get("source_name"))); return e   # keep the preview clip rather than fail the reel
        os.replace(tmp,clip); sha=_made_sha(clip)
    x=dict(e); x["preview_clip_path"]=e.get("clip_path"); x["clip_path"]=str(clip)
    x["clip_bytes"]=clip.stat().st_size; x["clip_sha256"]=sha
    return x

# ---------------------------------------------------------------- titles and own music (optional, the owner's choice)
MUSIC_EXT={".mp3",".m4a",".aac",".wav",".flac",".ogg",".opus",".wma"}
def _font_files(bold):
    """Windows fonts with Cyrillic first (segoeui, arial), then Linux (CI) ones."""
    win=Path(os.environ.get("WINDIR") or r"C:\Windows")/"Fonts"
    names=("segoeuib.ttf","arialbd.ttf") if bold else ("segoeui.ttf","arial.ttf")
    linux=("DejaVuSans-Bold.ttf",) if bold else ("DejaVuSans.ttf",)
    return [str(win/n) for n in names]+[f"{d}/{n}" for n in linux for d in ("/usr/share/fonts/truetype/dejavu","/usr/share/fonts/dejavu")]

TITLE_SHOW_S=3.2

def music_wav(ffmpeg,music,seconds,out):
    """The music decoded once (48 kHz stereo PCM, at most `seconds`): loops cleanly (an AAC song repeated straight
    from the file had a gap of its encoder delay at every repeat). Returns its length in seconds."""
    cp=subprocess.run([ffmpeg,"-v","error","-y","-i",str(music),"-map","0:a:0","-vn","-ac","2","-ar","48000","-t",f"{seconds:.3f}",
                       "-c:a","pcm_s16le",str(out)],capture_output=True,text=True,timeout=600)
    if cp.returncode!=0: raise RuntimeError("MUSIC_FILE_NO_SOUND:"+cp.stderr[-300:])
    n=(Path(out).stat().st_size-44)//4
    if n<48000*0.05: raise RuntimeError("MUSIC_FILE_NO_SOUND")
    return n/48000.0

def load_dress(path,ffmpeg):
    """--dress JSON {title, subtitle, music, music_mode, beat_sync}: nothing set = None (the reel is exactly as without it).
    beat_sync (default on): with own music, the cuts are placed on its beats (p13_beats)."""
    if not path: return None
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    clean=lambda t:" ".join(str(t or "").replace("\x00"," ").split())[:80]
    out={"title":clean(d.get("title")),"subtitle":clean(d.get("subtitle")),"music":str(d.get("music") or "").strip(),
         "music_mode":"music" if d.get("music_mode")=="music" else "mix","beat_sync":d.get("beat_sync",True) is not False}
    if out["music"]:
        p=Path(out["music"])
        if not p.is_file(): raise RuntimeError("MUSIC_FILE_MISSING")
        if p.suffix.lower() not in MUSIC_EXT: raise RuntimeError("MUSIC_FILE_NOT_AUDIO")
        # decode the first second: a file with a header but no sound (or protected, or damaged) is refused now,
        # not after the whole build (and never loops forever)
        cp=subprocess.run([ffmpeg,"-v","error","-i",str(p),"-map","0:a:0","-t","1","-ac","1","-ar","8000","-f","s16le","-"],
                          capture_output=True,timeout=120)
        if cp.returncode!=0 or len(cp.stdout)<2*400: raise RuntimeError("MUSIC_FILE_NO_SOUND")
        out["music_sha256"]=sha256_file(p); out["music_name"]=p.name
    return out if (out["title"] or out["subtitle"] or out["music"]) else None

def _font(bold,size):
    from PIL import ImageFont
    for c in _font_files(bold)+_font_files(not bold):
        if Path(c).is_file():
            try: return ImageFont.truetype(c,size)
            except Exception: continue
    return None

def title_text(t):
    """Emoji, pictographs and joiners have no glyph in the title fonts (they became boxes in the picture): left out."""
    import unicodedata
    keep=[]
    for ch in str(t or ""):
        o=ord(ch)
        if o>=0x1F000 or 0x2600<=o<=0x27BF or 0x2B00<=o<=0x2BFF or o in (0x200D,0xFE0F,0xFE0E,0x20E3) or 0xE000<=o<=0xF8FF:
            continue
        if unicodedata.category(ch) in ("Cc","Cf","Co","Cs"): continue
        keep.append(ch)
    return " ".join("".join(keep).split())

def _split_long(draw,word,font,maxw):
    """A word wider than the line (no spaces in it) is broken by letters."""
    parts=[]; cur=""
    for ch in word:
        if cur and draw.textlength(cur+ch,font=font)>maxw: parts.append(cur); cur=ch
        else: cur+=ch
    return parts+([cur] if cur else [])

def _wrap(draw,text,font,maxw):
    words=[]
    for w in text.split():
        words+=_split_long(draw,w,font,maxw) if draw.textlength(w,font=font)>maxw else [w]
    lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if not cur or draw.textlength(t,font=font)<=maxw: cur=t
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines

def title_png(title,subtitle,w,h,out):
    """The title (and a second line) as a transparent picture of the reel's size: white text with a soft shadow in
    the lower third. Returns False when no font is found (the reel is made without the title, with a warning)."""
    from PIL import Image, ImageDraw, ImageFilter
    base=min(w,h); maxw=int(w*.88)
    probe=Image.new("RGBA",(8,8)); dr=ImageDraw.Draw(probe)
    blocks=[]
    for text,bold,size,maxlines in ((title,True,int(base*.085),2),(subtitle,False,int(base*.05),1)):
        if not text: continue
        while True:
            f=_font(bold,max(10,size))
            if f is None: return False
            lines=_wrap(dr,text,f,maxw)
            if (len(lines)<=maxlines and all(dr.textlength(x,font=f)<=maxw for x in lines)) or size<=max(12,base//40): break
            size=int(size*.9)
        if len(lines)>maxlines:                     # still too long at a readable size: the end is cut with "…"
            lines=lines[:maxlines]
            while lines[-1] and dr.textlength(lines[-1]+"…",font=f)>maxw: lines[-1]=lines[-1][:-1]
            lines[-1]=lines[-1].rstrip()+"…"
        blocks.append((lines,f,size))
    gap=int(base*.02); heights=[len(ls)*int(sz*1.18) for ls,_,sz in blocks]
    total=sum(heights)+gap*(len(blocks)-1)
    y=y0=int(h*(.70 if h>w else .72))-total//2
    pad=int(base*.06)                     # a soft dark band behind the text: readable on a bright sky or snow too
    band=Image.new("RGBA",(w,h),(0,0,0,0))
    ImageDraw.Draw(band).rectangle((0,y0-pad,w,y0+total+pad),fill=(0,0,0,85))
    band=band.filter(ImageFilter.GaussianBlur(max(4,base//28)))
    shadow=Image.new("RGBA",(w,h),(0,0,0,0)); text_l=Image.new("RGBA",(w,h),(0,0,0,0))
    ds=ImageDraw.Draw(shadow); dt=ImageDraw.Draw(text_l)
    for (ls,f,sz),hh in zip(blocks,heights):
        for i,line in enumerate(ls):
            lw=dt.textlength(line,font=f); x=int((w-lw)/2); yy=y+i*int(sz*1.18)
            ds.text((x+max(1,sz//24),yy+max(1,sz//18)),line,font=f,fill=(0,0,0,200))
            dt.text((x,yy),line,font=f,fill=(255,255,255,255))
        y+=hh+gap
    shadow=Image.alpha_composite(band,shadow.filter(ImageFilter.GaussianBlur(max(2,base//160))))
    Image.alpha_composite(shadow,text_l).save(out)
    return True

def dress_filters(dress,first_input,vin,ain,total):
    """Extra inputs and filters that put the title over the first seconds and the music under the reel - in the same
    single encode as the reel itself (no second generation)."""
    args=[]; filters=[]; vout,aout=vin,ain; k=first_input
    if dress.get("title_png"):
        show=min(TITLE_SHOW_S,max(1.0,total-.4))
        args+=["-loop","1","-framerate","30","-t",f"{show:.3f}","-i",str(dress["title_png"])]
        filters.append(f"[{k}:v]format=rgba,fade=t=in:st=0.15:d=0.45:alpha=1,fade=t=out:st={max(.7,show-.55):.3f}:d=0.5:alpha=1[ttl]")
        filters.append(f"[{vin}][ttl]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[vdr]")
        vout="vdr"; k+=1
    if dress.get("music_wav"):
        n=max(1,int(round(total*48000)))
        loops=max(0,int(math.ceil(total/max(.05,float(dress["music_s"]))))-1)     # a finite number of repeats
        args+=["-stream_loop",str(loops),"-i",str(dress["music_wav"])]
        # asetpts after loudnorm: it leaves a gap in the time stamps when it flushes (the sound came out longer
        # than the picture)
        filters.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=end_sample={n},asetpts=N/SR/TB,"
                       f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asetpts=N/SR/TB,afade=t=in:d=0.6,"
                       f"afade=t=out:st={max(0.0,total-1.8):.3f}:d=1.8,apad=whole_len={n},atrim=end_sample={n}[mus]")
        if dress.get("music_mode")=="music":
            filters.append(f"[{ain}]anullsink")      # the videos' own sound is not used
            aout="mus"
        else:   # music + the videos' own sound, quieter
            filters.append(f"[{ain}]volume=0.35[vsd]")
            filters.append(f"[vsd][mus]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1,apad=whole_len={n},atrim=end_sample={n}[amx]")
            aout="amx"
        k+=1
    return args,filters,vout,aout

FFMPEG_STALL_S=180.0

def run_ffmpeg_watched(args,stall_s=None,tries=2):
    """An FFmpeg encode that is started again when it stops making progress: the final encode of a reel with cuts on
    the beat stood still for good now and then on Windows (CI b95/b97, inside FFmpeg). Its own progress report is
    read; when the encoded time does not move for FFMPEG_STALL_S seconds it is stopped and run once more.
    The output is the same as from one undisturbed run."""
    import tempfile,threading
    stall_s=float(stall_s or FFMPEG_STALL_S)
    a=list(args); at=a.index("-y")+1 if "-y" in a else 1
    a[at:at]=["-nostdin","-progress","pipe:1","-nostats"]
    last=""
    for attempt in range(max(1,int(tries))):
        errf=tempfile.TemporaryFile()
        proc=subprocess.Popen(a,stdout=subprocess.PIPE,stderr=errf,stdin=subprocess.DEVNULL)
        state={"t":time.monotonic()}
        def reader():
            # a report comes every half second even when nothing moves: only a new frame count or encoded time counts
            for raw in proc.stdout:
                line=raw.decode("utf-8","replace").strip(); key=line.split("=",1)[0]
                if key in ("frame","out_time_us") and state.get(key)!=line:
                    state[key]=line; state["t"]=time.monotonic()
                elif line=="progress=end":
                    state["t"]=time.monotonic()
        th=threading.Thread(target=reader,daemon=True); th.start()
        stalled=False
        while proc.poll() is None:
            if time.monotonic()-state["t"]>stall_s:
                stalled=True; proc.kill(); break
            time.sleep(0.5)
        proc.wait(); th.join(5)
        errf.seek(0); last=errf.read().decode("utf-8","replace"); errf.close()
        if not stalled:
            return subprocess.CompletedProcess(a,proc.returncode,"",last)
        progress("finish",0,1,"joining segments again (the encoder stood still)")
    raise RuntimeError("FINAL_RENDER_STALLED:"+last[-400:])

def render_dissolve_block(v52,segs,durs,trans,out,dress=None,frames=None):
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    args=[v52.FFMPEG,"-hide_banner","-loglevel","error","-y"]
    for i,p in enumerate(segs):
        # a segment cut to a number of frames (cuts on the beat): its file is read only a little past them, so FFmpeg
        # never keeps reading a file whose rest the graph does not take (same frames and sound as before)
        if frames and i in frames: args += ["-t",f"{(int(frames[i])+2)/30.0:.6f}"]
        args += ["-i",str(p)]
    if len(segs)==1 and not dress:
        args += ["-filter_complex",_fit_audio(0,float(durs[0])),"-map","0:v","-map","[n0]","-c:v","copy",
                 "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(out)]
        cp=run_ffmpeg_watched(args)
        if cp.returncode!=0: raise RuntimeError("DISSOLVE_BLOCK_RENDER_FAILED:"+cp.stderr[-800:])
        return float(durs[0])
    # segments of different sources can differ in pixel aspect (e.g. SAR 404:405 after a crop) and time base;
    # fades and joins need them identical
    # frames: {segment: number of frames} (cuts on the beat): the segment's frames numbered again from 0 at exactly
    # 30 fps (a segment that starts one frame late would move every later cut), then only these first frames
    cut=lambda i:f"setpts=N/30/TB,trim=end_frame={int(frames[i])},fps=30," if frames and i in frames else ""
    # a segment's own sound cut at the beat ends inside its fade-out: a short fade at the new end (no click)
    fit=lambda i,d:(_fit_audio(i,d)[:-len(f"[n{i}]")]+f",afade=t=out:st={max(0.0,d-0.03):.6f}:d=0.03[n{i}]") if frames and i in frames else _fit_audio(i,d)
    filters=[fit(i,float(d)) for i,d in enumerate(durs)]+[f"[{i}:v]{cut(i)}setsar=1,format=yuv420p,settb=AVTB[w{i}]" for i in range(len(segs))]
    vprev="w0"; aprev="n0"; cum=float(durs[0])
    for i in range(1,len(segs)):
        td=float(trans[i-1]["duration_s"]); vl=f"v{i}"; al=f"a{i}"; off=max(0.0,cum-td)
        if td<=0:
            # hard cut: plain join, sound and picture of both sides already have equal lengths
            filters.append(f"[{vprev}][w{i}]concat=n=2:v=1:a=0[{vl}]")
            filters.append(f"[{aprev}][n{i}]concat=n=2:v=0:a=1[{al}]")
        else:
            # 6 decimals and a hair earlier: "9.467" for 9.4667 s made xfade start one frame late (sound 33 ms early)
            filters.append(f"[{vprev}][w{i}]xfade=transition=fade:duration={td:.6f}:offset={max(0.0,off-0.0005):.6f}[{vl}]")
            filters.append(f"[{aprev}][n{i}]acrossfade=ns={max(1,int(round(td*48000)))}:c1=tri:c2=tri[{al}]")
        vprev=vl; aprev=al; cum+=float(durs[i])-max(0.0,td)
    if dress:
        dargs,dfilt,vprev,aprev=dress_filters(dress,len(segs),vprev,aprev,cum)
        args += dargs; filters += dfilt
    args += ["-filter_complex",";".join(filters),"-map",f"[{vprev}]","-map",f"[{aprev}]",
             "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(out)]
    cp=run_ffmpeg_watched(args)
    if cp.returncode!=0: raise RuntimeError("DISSOLVE_BLOCK_RENDER_FAILED:"+cp.stderr[-800:])
    return cum

def render_mixed(v52,segs,durs,transitions,out,work,dress=None,frames=None):
    """Whole reel in ONE encode: dissolves (xfade/acrossfade) and hard cuts (concat) in a single filter graph.
    R2 encoded every dissolve block and then the joined reel again (two full encodes, about twice the time).
    A title and own music (optional) go into the same encode."""
    total=render_dissolve_block(v52,segs,durs,transitions,out,dress,frames)
    dec=subprocess.run([v52.FFMPEG,"-hide_banner","-loglevel","error","-i",str(out),"-f","null","-"],capture_output=True,text=True)
    if dec.returncode!=0: raise RuntimeError("FINAL_DECODE_FAILED:"+dec.stderr[-800:])
    return total

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

def choose_moments(v52,events,target,warnings,exclude=(),clip=5.0,trans=.25,cache_dir=None):
    """V52 choose_for_target, bounded so a 60 s reel cannot hang for hours, with an honest shorter reel
    (warning LIMITED_TOTAL_FOOTAGE) when the footage cannot fill the requested length.
    cache_dir: the same choice for the same moments and length is remembered (a format, sound or music variant of a
    2-minute reel searched about a minute again); the result is exactly what the search gives."""
    events,removed=drop_overlapping(events)   # before exclusions: a removed moment's near-twin never comes back
    if removed: warnings.append("OVERLAPPING_MOMENTS_DROPPED:%d"%len(removed))
    events=[e for e in events if str(e["event_id"]) not in exclude]
    if not events: raise RuntimeError("NO_MOMENTS_LEFT_AFTER_EXCLUSIONS")
    cf=None
    if cache_dir is not None:
        ident=[[str(e["event_id"]),float(e["v22_score"]),str(e["source_name"]),str(e["source_sha256"]),float(e.get("start_s") or 0),
                float(e.get("end_s") or 0),float(e.get("duration_s") or 0)] for e in events]
        key=hashlib.sha256(json.dumps({"v":1,"events":ident,"target":float(target),"clip":clip,"trans":trans,
                                       "budget":SELECTION_COMBINATION_BUDGET},sort_keys=True).encode()).hexdigest()[:24]
        cf=Path(cache_dir)/f"{key}.json"
        try:
            d=json.loads(cf.read_text(encoding="utf-8")); by={str(e["event_id"]):e for e in events}
            if all(i in by for i in d["ids"]):
                warnings.extend(d["warnings"]); return [by[i] for i in d["ids"]]
        except (OSError,ValueError,KeyError,TypeError): pass
    before=len(warnings)
    sel=_choose_moments_search(v52,events,target,warnings,clip,trans)
    if cf is not None:
        try: atomic_json(cf,{"ids":[str(e["event_id"]) for e in sel],"warnings":warnings[before:]})
        except OSError: pass
    return sel

def _choose_moments_search(v52,events,target,warnings,clip,trans):
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
    if input_list is not None and not input_list: raise RuntimeError("NO_SUPPORTED_VIDEO_FILES")   # e.g. all cloud-only
    input_dir=Path(args.input_dir or Path(input_list[0]).parent).resolve(); output_dir=Path(args.output_dir).resolve(); work_dir=Path(args.work_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True); work_dir.mkdir(parents=True,exist_ok=True)
    final_video=output_dir/"MediaEngine Reel.mp4"; final_result=output_dir/"MediaEngine Result.json"
    if final_video.exists() or final_result.exists(): raise RuntimeError("OUTPUT_ALREADY_EXISTS")

    # 16x9 + social_hd = horizontal Full HD 1920x1080 (the engine's own size; offered since the owner asked, 2026-10-13)
    v52=load_module("medeng_targeted_auto_edit_v26",runtime/"medeng_targeted_auto_edit_v26.py")
    dress=load_dress(getattr(args,"dress",""),v52.FFMPEG)   # title / own music: a bad music file is refused now, not after the build
    skipped_inputs=[]; warnings=[]
    # the SHA-256 of each source by path, size and change time: shared by all projects when the app says where (a new
    # reel from the same 29 GB folder does not read every byte again)
    sh_=_shared_root()
    input_rows=discover_input(input_dir,probe=v52.ffprobe,skipped=skipped_inputs,skip_sha=load_skip_sha(args.skip_sha_file),paths=input_list,
                              sha_cache=(sh_/"source_sha256.json") if sh_ else work_dir/"source_sha256.json",
                              sha_seed=(work_dir/"source_sha256.json") if sh_ else None); fingerprint=input_fingerprint(input_rows)
    seqmod=load_module("p11_montage_sequence_shadow_v4",runtime/"p11_montage_sequence_shadow_v4.py")
    pacemod=load_module("p11_montage_pacing_shadow_v1",runtime/"p11_montage_pacing_shadow_v1.py")
    audiomod=load_module("p11_audio_coherence_shadow_v2",runtime/"p11_audio_coherence_shadow_v2.py")
    dropmod=load_module("p11_camera_drop_trim_shadow_v1",runtime/"p11_camera_drop_trim_shadow_v1.py")

    model_root=Path(os.environ.get("MEDENG_P11_MODEL_ROOT",r"D:\Archivist\sidecars\auto_edit\models"))
    adapter_root=Path(os.environ.get("MEDENG_P11_ADAPTER_ROOT",r"D:\Archivist\sidecars\auto_edit\shadow\P11_FAST_LOCAL_ADAPTER_V1"))
    semantic_mode=str(args.semantic).lower()
    semantic_model=str(getattr(args,"semantic_model","fast_local") or "fast_local").lower()
    if semantic_model=="pe_core_l14" and semantic_mode!="off":     # AI+: its own model, never a silent fallback
        pe_dir=pe_model_dir(model_root)
        theme=str(getattr(args,"theme","") or "")
        if theme:
            import p13_event_semantic_pe as _hook
            if theme not in _hook.THEMES: raise RuntimeError("UNKNOWN_THEME:"+theme[:40])
        semantic_preflight=pe_runtime_preflight(pe_dir)
        if not semantic_preflight["pass"]:
            raise RuntimeError("AIPLUS_MODEL_NOT_READY:"+str(semantic_preflight.get("error"))[:160])
    else:
        semantic_model="fast_local"
        semantic_preflight=semantic_runtime_preflight(runtime,model_root,adapter_root)
        if semantic_mode=="required" and not semantic_preflight["pass"]:
            raise RuntimeError("SEMANTIC_RUNTIME_REQUIRED_BUT_NOT_EXACT")
    use_semantic=semantic_mode!="off" and semantic_preflight["pass"]

    semantic_reports=[]
    if use_semantic:
        sem_rows,sem_back=analysis_aliases(input_rows,work_dir,long_names=False)   # camcorder streams only
        sem_skipped=[]
        if semantic_model=="pe_core_l14":
            candidates,semantic_reports,kept=build_semantic_candidates_pe(runtime,sem_rows,work_dir,v52,pe_dir,sem_skipped,
                                                                          theme=(getattr(args,"theme","") or None),warnings=warnings)
        else:
            candidates,semantic_reports,kept=build_semantic_candidates(runtime,sem_rows,work_dir,v52,model_root,adapter_root,sem_skipped)
        for x in sem_skipped:
            skipped_inputs.append(dict(x,name=sem_back[x["name"]]["name"]) if x["name"] in sem_back else x)
        input_rows=[sem_back.get(r["name"],r) for r in kept]
        for c in list(candidates)+list(semantic_reports):
            o=sem_back.get(str(c.get("source_name")))
            if o:
                c["source_name"]=o["name"]
                if "source_path" in c: c["recut_path"]=c["source_path"]; c["source_path"]=o["path"]
        pool=candidates
        progress("select",0,1,"choosing moments")
        selected=manual_selection(pool,manual) if manual else choose_moments(v52,candidates,float(args.target_seconds),warnings,exclude,
                                                                             cache_dir=work_dir/"selection_cache")
        selection_mode="PE_CORE_L14_SEMANTIC_V1" if semantic_model=="pe_core_l14" else "FAST_LOCAL_SEMANTIC_SHADOW_V1"
        event_count=len(candidates); cache_status="semantic_candidate_cache"
    else:
        progress("analyze",0,len(input_rows),"technical analysis")
        analysis_rows,alias_back=analysis_aliases(input_rows,work_dir)
        skipped_analysis=[]
        libpath,lib,cache_status,analysed=build_event_library(runtime,analysis_rows,work_dir,skipped_analysis)
        for x in skipped_analysis:
            skipped_inputs.append(dict(x,name=alias_back[x["name"]]["name"]) if x["name"] in alias_back else x)
        input_rows=[alias_back.get(r["name"],r) for r in analysed]
        _,events=v52.load_library(libpath)
        # where the videos are NOW (a moved data or source folder: the library still has the old paths; same name +
        # SHA-256 = same video). Nothing moved: the same paths as before.
        now_at={(r["name"],r["sha256"]):r["path"] for r in analysis_rows}
        for ev in events:
            o=alias_back.get(str(ev.get("source_name")))
            here=now_at.get((str(ev.get("source_name")),str(ev.get("source_sha256"))))
            if o:
                ev["recut_path"]=here or ev.get("source_path")   # stand-in: camcorder remux, or a short name Windows can open
                ev["source_name"]=o["name"]; ev["source_path"]=o["path"]
            elif here:
                ev["source_path"]=here
        scored=v52.score_events(events,work_dir/"V22_SCORE_CACHE.json")
        pool=scored
        progress("select",0,1,"choosing moments")
        selected=manual_selection(pool,manual) if manual else choose_moments(v52,scored,float(args.target_seconds),warnings,exclude,
                                                                             cache_dir=work_dir/"selection_cache")
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

    # Dissolves are rendered with whole-frame lengths: a 0.25 s fade (7.5 frames) made the picture start up to half a
    # frame after its sound at every dissolve. The pacing decision itself is kept as planned (result.pacing).
    render_trans=[dict(t,duration_s=(max(1,round(float(t["duration_s"])*30))/30.0 if t["kind"]!="HARD_CUT" and float(t["duration_s"])>0 else 0.0))
                  for t in pace["transitions"]]
    render_dir=work_dir/"final_v2"; render_dir.mkdir(parents=True,exist_ok=True)
    beats=None; beat_info=None; beat_max_off=1.0
    # where the plan has each cut (reel time): every cut is moved to the beat nearest to its PLANNED place, so earlier
    # moves never add up
    plan_cuts=[]; _t=0.0
    for i,d in enumerate(pace["durations_s"]):
        td=float(render_trans[i]["duration_s"]) if i<len(pace["durations_s"])-1 else 0.0
        plan_cuts.append(_t+float(d)-td/2.0); _t+=float(d)-td
    if dress and dress["music"]:
        if not Path(dress["music"]).is_file(): raise RuntimeError("MUSIC_FILE_MISSING")
        wav=render_dir/(fingerprint+"_music.wav")
        planned=sum(float(d) for d in pace["durations_s"])-sum(float(t["duration_s"]) for t in render_trans)
        need=planned+3.0     # cuts on the beat move the end by at most about a beat and a half (decoded again if not enough)
        # the song's own stated length: an AAC file decodes with a little silence of padding at its end (a gap at
        # every repeat) - cut at the stated length it repeats seamlessly
        info=subprocess.run([v52.FFMPEG,"-hide_banner","-i",str(dress["music"])],capture_output=True,text=True,encoding="utf-8",errors="replace").stderr
        m=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",info)
        stated=(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))) if m else 0.0
        dress["music_s"]=music_wav(v52.FFMPEG,dress["music"],min(need,stated) if stated>0.2 else need,wav); dress["music_wav"]=str(wav)
        if dress.get("beat_sync"):
            progress("render",0,len(order),"finding the beat of the music")
            beatmod=load_module("p13_beats",runtime/"p13_beats.py")
            try:
                beat_info=beatmod.detect(wav)
            except Exception as exc:     # the beat is a nicety: never a failed reel because of it
                beat_info={"beats":[],"bpm":0.0,"confidence":0.0,"clear":False,"error":type(exc).__name__}
            if beat_info["clear"]:
                beats=beatmod.repeat(beat_info["beats"],dress["music_s"],need)
                beat_max_off=beatmod.max_offset(beats)
            else:
                warnings.append("MUSIC_NO_CLEAR_BEAT")
    segcache=work_dir/"segment_cache_v2"; segcache.mkdir(parents=True,exist_ok=True)
    segs=[]; durs=[]; seg_meta=[]; on_beat=[]; exact={}; asked={}
    framing=str(getattr(args,"vertical_framing","fill") or "fill") if profile=="9x16" else "fill"
    def make_seg(e,use):
        """One segment of `use` seconds (cached by clip, length and output settings): (file, meta, picture length)."""
        key=hashlib.sha256(json.dumps({"clip_sha256":e["clip_sha256"],"use_s":round(float(use),3),
                                     "audio":audio_mode,"profile":profile,"resolution":resolution,"fps":30,"quality":"high",
                                     **({"framing":framing} if framing!="fill" else {})},
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
                                  output_resolution=resolution,output_fps=30,video_quality="high",
                                  **({"vertical_framing":framing} if framing!="fill" else {}))
            os.replace(tmp,seg); meta["sha256"]=sha256_file(seg); atomic_json(meta_path,meta)
        # the picture length of a cached segment is remembered with it (counting its frames again took ~1 s each)
        side=segcache/f"{key}.seconds.json"
        try:
            sd=json.loads(side.read_text(encoding="utf-8"))
            if sd.get("sha256")==meta["sha256"]: return seg,meta,float(sd["seconds"])
        except (OSError,ValueError,KeyError,TypeError): pass
        secs=video_seconds(v52.FFMPEG,seg)
        try: atomic_json(side,{"sha256":meta["sha256"],"seconds":secs})
        except OSError: pass
        return seg,meta,secs

    render_source="AI_CANDIDATE_CLIPS_FROM_ORIGINAL" if use_semantic else "ORIGINAL_FULL_QUALITY_RECUT"
    hdr_sources={}; deinterlaced=[]; widened={}
    for si,(e,use) in enumerate(zip(order,pace["durations_s"])):
        progress("render",si,len(order),str(e["source_name"]))
        probe_src=e.get("recut_path") or e.get("source_path")
        hdr=hdr_kind(v52.FFMPEG,probe_src) if probe_src else None
        deint=bool(probe_src) and is_interlaced(v52.FFMPEG,probe_src)
        if deint and str(e["source_name"]) not in deinterlaced: deinterlaced.append(str(e["source_name"]))
        if hdr:
            hdr_sources[str(e["source_name"])]=hdr
            if not zscale_available(v52.FFMPEG):
                hdr=None
                if "HDR_NOT_CONVERTED" not in warnings: warnings.append("HDR_NOT_CONVERTED")
        sq=bool(probe_src) and is_anamorphic(v52.FFMPEG,probe_src)
        if hdr or deint or sq or (not use_semantic and str(e["event_id"]) not in trims):   # manual trims are already cut from the original
            e2=full_quality_clip(v52,e,work_dir,hdr,deint,sq)
            if sq and e2 is not e: widened[str(e["source_name"])]=round(pixel_aspect(v52.FFMPEG,probe_src),4)
            e=e2
        hit=None
        if beats and str(e["event_id"]) not in trims:   # a moment the user trimmed keeps its exact length
            start=sum(float(d) for d in durs)-sum(float(render_trans[j]["duration_s"]) for j in range(si))
            td_in=float(render_trans[si-1]["duration_s"]) if si>0 else 0.0
            td_out=float(render_trans[si]["duration_s"]) if si<len(order)-1 else 0.0
            use,hit=beatmod.snap_use(start,float(use),td_out,td_in,float(e.get("duration_s") or use),beats,30,plan_cuts[si],beat_max_off)
            on_beat.append(hit)
        seg,meta,dur=make_seg(e,use)
        if beats:
            # cuts on the beat: every segment of the reel is used by its real frames (numbered again in the final
            # encode). The accepted segment cutter trims the source and then sets 30 fps: depending on the source's own
            # frame times it gives a frame or two more or less than asked (a 25 fps video: steps of two). The final
            # encode takes exactly the frames up to the beat; a segment that came out short is made again a bit longer.
            got=video_frames(v52.FFMPEG,seg)
            if hit is not None:
                want=round((hit-start+td_out/2.0)*30)
                if got<want:
                    use=float(use)+(want-got+0.5)/30.0
                    seg,meta,dur=make_seg(e,use); got=video_frames(v52.FFMPEG,seg)
                if got>=want:
                    asked[si]=float(meta.get("use") or use); got=want
                else:
                    on_beat[-1]=None          # the moment is too short to reach the beat: left as it is
            exact[si]=got; dur=got/30.0
        segs.append(seg); durs.append(dur); seg_meta.append(meta)

    if _FQ_FALLBACK:
        warnings.append("PREVIEW_QUALITY_USED:"+",".join(sorted(set(_FQ_FALLBACK))))
    progress("finish",0,1,"joining segments and verifying")
    temp_final=render_dir/(fingerprint+".mp4")
    if temp_final.exists(): temp_final.unlink()
    if dress and dress.get("music_wav") and beats:
        total_now=sum(float(d) for d in durs)-sum(float(t["duration_s"]) for t in render_trans)
        if total_now+0.5>dress["music_s"] and total_now+0.5<=float(stated or 0):   # cut too short for this reel: again
            dress["music_s"]=music_wav(v52.FFMPEG,dress["music"],min(total_now+2.0,stated),Path(dress["music_wav"]))
    beat_sync=None
    if beat_info is not None:
        # where the cuts really are (the middle of a dissolve, a hard cut, the end) and the nearest beat to each
        offs=[]; half=[]; t0=0.0
        halves=[(a+b)/2.0 for a,b in zip(beats,beats[1:])] if beats else []
        for i,d in enumerate(durs):
            td=float(render_trans[i]["duration_s"]) if i<len(durs)-1 else 0.0
            cut=t0+float(d)-td/2.0
            if beats:
                offs.append(min(abs(cut-b) for b in beats)); half.append(min(abs(cut-b) for b in halves) if halves else 9.0)
            t0+=float(d)-td
        beat_sync={"bpm":beat_info["bpm"],"clear":beat_info["clear"],"confidence":beat_info["confidence"],
                   "cuts":len(durs),"cuts_on_beat":sum(1 for o in offs if o<=0.025),
                   "cuts_half_way_between_beats":sum(1 for o,h in zip(offs,half) if o>0.025 and h<=0.025),
                   "snapped":sum(1 for h in on_beat if h is not None),
                   "max_offset_s":round(max(offs),4) if offs else None,"cut_offsets_s":[round(o,4) for o in offs]}
    if dress and (dress["title"] or dress["subtitle"]):
        if title_text(dress["title"])!=dress["title"] or title_text(dress["subtitle"])!=dress["subtitle"]:
            warnings.append("TITLE_CHARACTERS_LEFT_OUT")
        ow,oh=v52.output_dimensions(profile,resolution)
        png=render_dir/(fingerprint+"_title.png")
        if not (title_text(dress["title"]) or title_text(dress["subtitle"])): pass
        elif title_png(title_text(dress["title"]),title_text(dress["subtitle"]),int(ow),int(oh),png): dress["title_png"]=str(png)
        else: warnings.append("TITLE_FONT_MISSING")
    render_mixed(v52,segs,durs,render_trans,temp_final,render_dir/(fingerprint+"_render"),dress,exact or None)
    for x in ("title_png","music_wav"):
        if dress and dress.get(x): Path(dress[x]).unlink(missing_ok=True)
    fpr=v52.ffprobe(temp_final); actual=float(fpr["format"]["duration"]); video_sha=sha256_file(temp_final)
    # cuts on the beat may end the reel up to about a beat and a half early: that is not "too little footage"
    if actual < float(args.target_seconds)-1.0-(beat_max_off+0.1 if beats else 0.0) and "LIMITED_TOTAL_FOOTAGE" not in warnings:
        warnings.append("SHORTER_THAN_REQUESTED")
    fvs=[x for x in fpr["streams"] if x.get("codec_type")=="video"][0]; out_w,out_h=int(fvs["width"]),int(fvs["height"])
    if (out_w,out_h)!=tuple(v52.output_dimensions(profile,resolution)): raise RuntimeError("OUTPUT_DIMENSIONS_MISMATCH:%dx%d"%(out_w,out_h))
    for k in range(10):        # a virus scanner may still be reading the new reel
        try: os.replace(temp_final,final_video); break
        except PermissionError:
            if k==9: raise
            time.sleep(1.0)
    if sha256_file(final_video)!=video_sha: raise RuntimeError("FINAL_COPY_VERIFY_FAILED")
    shutil.rmtree(render_dir/(fingerprint+"_render"),ignore_errors=True)   # join blocks are temporary, never reused

    timeline=[]; t=0.0
    for i,(e,meta,d) in enumerate(zip(order,seg_meta,durs)):
        clip_dur=float(e.get("duration_s") or d); use=float(d)
        # a segment trimmed to a beat: cut centred for the length asked, then its end taken off
        src_in=float(e.get("start_s") or 0.0)+max(0.0,(clip_dur-float(asked.get(i,use)))/2.0)
        if i>0: t-=float(render_trans[i-1]["duration_s"])
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
        "skipped_inputs":skipped_inputs,"warnings":warnings,"render_source":render_source,"hdr_sources":hdr_sources,"deinterlaced_sources":deinterlaced,"widened_sources":widened,
        "rendered_transition_s":[round(float(x["duration_s"]),6) for x in render_trans],
        "engine":{"orchestrator_sha256":sha256_file(Path(__file__)),"semantic_hook_sha256":SEMANTIC_HOOK_SHA},
        "input_folder":str(input_dir),"input_list":input_list,"input_fingerprint":fingerprint,"input_count":len(input_rows),
        "inputs":[{"name":r["name"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in input_rows],
        "target_seconds":float(args.target_seconds),"actual_duration_s":round(actual,3),
        "target_error_s":round(abs(actual-float(args.target_seconds)),3),
        "selection_mode":selection_mode,"semantic_requested":semantic_mode,"semantic_model":semantic_model if use_semantic else None,
        "theme":(str(getattr(args,"theme","") or "") or None) if (use_semantic and semantic_model=="pe_core_l14") else None,
        "semantic_runtime":semantic_preflight,
        "semantic_timing":({k:(round(v,2) if isinstance(v,float) else v) for k,v in SEM_TIMING.items()} if use_semantic else None),"semantic_reports":semantic_reports if use_semantic else [],
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
                  "width":out_w,"height":out_h,**({"vertical_framing":framing} if framing!="fill" else {})},
        **({"beat_sync":beat_sync} if beat_sync is not None else {}),
        "dress":({"title":dress["title"] or None,"subtitle":dress["subtitle"] or None,"title_shown":bool(dress.get("title_png")),
                  "music":({"name":dress["music_name"],"sha256":dress["music_sha256"],"mode":dress["music_mode"]} if dress["music"] else None)}
                 if dress else None),
        "source_mutated":False,"network_request_performed":False,
        "semantic_best_moment_claim":bool(use_semantic),
        "claim_scope":"current run only; shadow prototype",
        "elapsed_s":round(time.perf_counter()-started,3),
        "stage_seconds":dict(_STAGE_T["seconds"],**({_STAGE_T["stage"]:round(_STAGE_T["seconds"].get(_STAGE_T["stage"],0.0)+time.perf_counter()-_STAGE_T["t"],2)} if _STAGE_T["stage"] else {})),
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
    ap.add_argument("--semantic-model",choices=("fast_local","pe_core_l14"),default="fast_local",help="AI = fast_local (accepted), AI+ = pe_core_l14")
    ap.add_argument("--theme",default="",help="AI+ only: a theme key of p13_event_semantic_pe.THEMES (empty = no theme)")
    ap.add_argument("--profile",choices=("16x9","9x16","auto"),default="16x9")
    ap.add_argument("--vertical-framing",choices=("fill","fit_blur"),default="fill")   # vertical reel: crop, or whole picture on blurred edges
    ap.add_argument("--resolution",choices=("standard","social_hd"),default="standard")
    ap.add_argument("--progress-file",default="")
    ap.add_argument("--exclude-events",default="")
    ap.add_argument("--skip-sha-file",default="",help="text file, one SHA-256 per line: inputs never to use (Private)")
    ap.add_argument("--edits",default="",help="JSON file: {selection:[event ids in order], trims:{id:[source_in_s,source_out_s]}}")
    ap.add_argument("--dress",default="",help="JSON file: {title, subtitle, music (audio file path), music_mode: mix|music, beat_sync: true|false}")
    a=ap.parse_args()
    try: run(a)
    except Exception as exc:
        progress("failed",0,0,type(exc).__name__+":"+str(exc))
        print(json.dumps({"status":"FAIL","error":type(exc).__name__+":"+str(exc)},indent=2)); raise

if __name__=="__main__":
    main()

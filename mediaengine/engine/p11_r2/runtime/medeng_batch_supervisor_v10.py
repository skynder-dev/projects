#!/usr/bin/env python3
"""
MediaEngine isolated per-file batch supervisor V10.

V10 fixes the V9 runtime deadlock observed on real DJI footage:
V9 captured worker stdout/stderr with PIPE. A descendant process retaining an
inherited pipe descriptor could keep communicate() blocked even after the
worker had already written its result .part file.

V10 invariants:
- one input file = one fresh worker process group
- worker stdout/stderr go to ordinary files, never PIPE
- parent waits on the worker PID only
- timeout cleanup is fully bounded; no unbounded communicate()/wait()
- whole process group/tree kill on timeout
- no retry
- .part result + atomic os.replace
- failed/timed-out file does not prevent later files from running
- per-file SHA-256 provenance
- local-only; no network action
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, signal, subprocess, sys, time
from pathlib import Path


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def safe_stem(path: Path) -> str:
    stem=re.sub(r"[^A-Za-z0-9._-]+","_",path.name)
    return stem[:140] or "media"


def read_tail(path: Path, max_chars: int = 4000) -> str:
    try:
        text=path.read_text(encoding="utf-8",errors="replace")
        return text[-max_chars:]
    except Exception as e:
        return f"<log read failed {type(e).__name__}:{e}>"


def parse_child_result(path: Path, expected_video: Path):
    obj=json.loads(path.read_text(encoding="utf-8"))
    if obj.get("candidate")!="MEDENG_EVENT_SEMANTIC_V7":
        raise RuntimeError("CHILD_CANDIDATE_MISMATCH")
    reports=obj.get("reports")
    if not isinstance(reports,list) or len(reports)!=1:
        raise RuntimeError("CHILD_REPORT_COUNT")
    report=reports[0]
    if Path(report.get("video","")).resolve()!=expected_video.resolve():
        raise RuntimeError("CHILD_VIDEO_IDENTITY_MISMATCH")
    return obj


def _bounded_wait(proc: subprocess.Popen, timeout_s: float) -> bool:
    try:
        proc.wait(timeout=max(0.05,float(timeout_s)))
        return True
    except subprocess.TimeoutExpired:
        return False


def _kill_tree(proc: subprocess.Popen) -> str:
    """Best-effort process-tree kill with bounded subprocess calls only."""
    if os.name=="nt":
        try:
            killer=subprocess.run(
                ["taskkill","/PID",str(proc.pid),"/T","/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            return f"windows_taskkill_rc={killer.returncode}"
        except subprocess.TimeoutExpired:
            return "windows_taskkill_timeout"
        except Exception as e:
            return f"windows_taskkill_error={type(e).__name__}"
    try:
        os.killpg(os.getpgid(proc.pid),signal.SIGKILL)
        return "posix_killpg_sigkill"
    except ProcessLookupError:
        return "posix_group_already_gone"
    except Exception as e:
        return f"posix_killpg_error={type(e).__name__}"


def run_process_tree(cmd, timeout_s: float, stdout_path: Path, stderr_path: Path):
    """Run one worker without PIPEs; all waits and cleanup are time-bounded."""
    stdout_path.parent.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    kwargs={}
    if os.name=="nt":
        kwargs["creationflags"]=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
    else:
        kwargs["start_new_session"]=True

    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc=subprocess.Popen(cmd,stdout=out_f,stderr=err_f,**kwargs)
        if _bounded_wait(proc,timeout_s):
            return {
                "timed_out":False,
                "returncode":proc.returncode,
                "tree_kill":"not_needed",
                "termination_complete":True,
                "elapsed_s":round(time.perf_counter()-start,3),
                "stdout_tail":read_tail(stdout_path),
                "stderr_tail":read_tail(stderr_path),
            }

        tree_kill=_kill_tree(proc)
        termination_complete=_bounded_wait(proc,5.0)
        if not termination_complete and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
            termination_complete=_bounded_wait(proc,2.0)

    return {
        "timed_out":True,
        "returncode":proc.returncode,
        "tree_kill":tree_kill,
        "termination_complete":termination_complete,
        "elapsed_s":round(time.perf_counter()-start,3),
        "stdout_tail":read_tail(stdout_path),
        "stderr_tail":read_tail(stderr_path),
    }


def run_one(engine: Path, media: Path, output_dir: Path, mode: str, profile: str,
            model_root: str, ffmpeg: str, ffprobe: str, timeout_s: float):
    started=time.perf_counter()
    ident={
        "input_path":str(media),
        "size_bytes":media.stat().st_size,
        "sha256":sha256_file(media),
    }
    base=safe_stem(media)
    suffix=mode.lower()
    final=output_dir/f"{base}.{suffix}.json"
    part=output_dir/f"{base}.{suffix}.json.part"
    logs=output_dir/"_worker_logs"
    stdout_path=logs/f"{base}.{suffix}.stdout.log"
    stderr_path=logs/f"{base}.{suffix}.stderr.log"
    if part.exists():
        part.unlink()

    cmd=[
        sys.executable,str(engine),str(media),
        "--mode",mode,
        "--profile",profile,
        "--ffmpeg",ffmpeg,
        "--ffprobe",ffprobe,
        "--out",str(part),
    ]
    if mode=="SELECT_BEST":
        if not model_root:
            raise RuntimeError("MODEL_ROOT_REQUIRED")
        cmd += ["--model-root",model_root]

    pr=run_process_tree(cmd,float(timeout_s),stdout_path,stderr_path)
    common={
        **ident,
        "worker_stdout_log":str(stdout_path),
        "worker_stderr_log":str(stderr_path),
        "worker_elapsed_s":pr["elapsed_s"],
        "retry_count":0,
    }

    if pr["timed_out"]:
        if part.exists():
            part.unlink()
        return {
            **common,
            "status":"timeout",
            "timeout_s":float(timeout_s),
            "tree_kill":pr["tree_kill"],
            "termination_complete":pr["termination_complete"],
            "stderr_tail":pr["stderr_tail"],
            "elapsed_s":round(time.perf_counter()-started,3),
        }

    if pr["returncode"]!=0:
        if part.exists():
            part.unlink()
        return {
            **common,
            "status":"failed",
            "returncode":pr["returncode"],
            "stderr_tail":pr["stderr_tail"],
            "elapsed_s":round(time.perf_counter()-started,3),
        }

    try:
        obj=parse_child_result(part,media)
    except Exception as e:
        if part.exists():
            part.unlink()
        return {
            **common,
            "status":"invalid_result",
            "error":f"{type(e).__name__}:{e}",
            "elapsed_s":round(time.perf_counter()-started,3),
        }

    os.replace(part,final)
    report=obj["reports"][0]
    return {
        **common,
        "status":"passed",
        "result_path":str(final),
        "mode":report.get("mode"),
        "selection_claim":report.get("selection_claim"),
        "event_count":len(report.get("events",[])) if report.get("mode")=="DISCOVER_EVENTS" else None,
        "ranked_count":len(report.get("ranked",[])) if report.get("mode")=="SELECT_BEST" else None,
        "scout_elapsed_s":report.get("scout_elapsed_s"),
        "elapsed_s":round(time.perf_counter()-started,3),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("videos",nargs="+")
    ap.add_argument("--mode",choices=("DISCOVER_EVENTS","SELECT_BEST"),required=True)
    ap.add_argument("--profile",choices=("FAST_LOCAL","QUALITY_LOCAL"),default="FAST_LOCAL")
    ap.add_argument("--model-root",default="")
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--per-file-timeout-s",type=float,default=120.0)
    ap.add_argument("--ffmpeg",default=os.environ.get("MEDENG_FFMPEG","ffmpeg"))
    ap.add_argument("--ffprobe",default=os.environ.get("MEDENG_FFPROBE","ffprobe"))
    args=ap.parse_args()

    root=Path(args.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    engine=Path(__file__).resolve().parent/"medeng_event_semantic_v7.py"

    results=[]
    batch_started=time.perf_counter()
    for raw in args.videos:
        media=Path(raw).resolve()
        if not media.is_file():
            results.append({"input_path":str(media),"status":"missing","retry_count":0})
            continue
        results.append(run_one(
            engine,media,root,args.mode,args.profile,args.model_root,
            args.ffmpeg,args.ffprobe,args.per_file_timeout_s
        ))

    passed=sum(r["status"]=="passed" for r in results)
    aggregate={
        "candidate":"MEDENG_BATCH_SUPERVISOR_V10",
        "mode":args.mode,
        "profile":args.profile,
        "network_during_analysis":False,
        "retry_policy":"NONE",
        "per_file_process_isolation":True,
        "worker_pipe_policy":"LOG_FILES_NO_PIPE",
        "bounded_cleanup":True,
        "per_file_timeout_s":args.per_file_timeout_s,
        "total":len(results),
        "passed":passed,
        "failed":len(results)-passed,
        "batch_elapsed_s":round(time.perf_counter()-batch_started,3),
        "results":results,
        "verdict":"PASS" if passed==len(results) else "PARTIAL_FAILURE",
    }
    tmp=root/"batch_result.json.part"
    final=root/"batch_result.json"
    tmp.write_text(json.dumps(aggregate,indent=2),encoding="utf-8")
    os.replace(tmp,final)
    print(json.dumps(aggregate,indent=2))
    raise SystemExit(0 if passed==len(results) else 2)


if __name__=="__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from medeng_delivery_bundle_v36 import build_delivery_bundle, validate_delivery_bundle
from medeng_auto_variants_v36 import build as build_auto_variants, validate_public_alternatives
from medeng_variant_comparison_v37 import build as build_variant_comparison, validate as validate_variant_comparison
from medeng_auto_approval_v39 import ensure as ensure_auto_approval
from medeng_media_probe_v41 import probe_json as media_probe_json

CANDIDATE = "MEDENG_DROP_QUEUE_V40_RC1"
SCHEMA_VERSION = 1
SUPPORTED = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(src, tmp)
    if tmp.stat().st_size != src.stat().st_size or sha256_file(tmp) != sha256_file(src):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"PUBLISH_COPY_IDENTITY_MISMATCH:{src}")
    os.replace(tmp, dst)


def append_history(queue_root: Path, event: str, state: dict, extra: dict | None = None) -> None:
    history = queue_root / "HISTORY.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "event": event,
        "at_unix": time.time(),
        "job_id": state.get("job_id"),
        "label": state.get("label"),
        "fingerprint": state.get("fingerprint"),
        "status": state.get("status"),
        "attempt": state.get("attempt"),
        "target_seconds": state.get("target_seconds"),
    }
    if extra:
        row.update(extra)
    with history.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()
        with contextlib.suppress(Exception):
            os.fsync(f.fileno())


def human_seconds(v: object) -> str:
    try:
        return f"{float(v):.1f}s"
    except Exception:
        return "?"


def write_result_card(outdir: Path, result: dict) -> None:
    lines = [
        "MediaEngine Auto Edit — COMPLETED",
        "=" * 40,
        f"Job: {result.get('job_id','')}",
        f"Target: {human_seconds(result.get('target_duration_s'))}",
        f"Pacing: clip={human_seconds(result.get('clip_seconds'))}  transition={human_seconds(result.get('transition_seconds'))}",
        f"Audio target: {result.get('audio_lufs','?')} LUFS  TP={result.get('audio_true_peak_db','?')} dBTP  content={result.get('audio_content','source')}",
        f"Vertical framing: {result.get('vertical_framing','fill')}  focus_x={result.get('vertical_focus_x',0.5)}  resolution={result.get('output_resolution','standard')}",
        f"Engine time: {human_seconds(result.get('engine_elapsed_s'))}",
        "Selection: automatic technical/aesthetic heuristic (semantic best-scene model not claimed)",
        "",
        "Sources:",
    ]
    for src in result.get("source_files", []):
        lines.append(f"  - {src.get('name','?')}  [{src.get('bytes','?')} bytes]  sha256={str(src.get('sha256',''))[:16]}…")
    lines += ["", "Outputs:"]
    for o in result.get("outputs", []):
        lines.append(f"  - {o.get('profile','?')}: {o.get('filename','?')}  [{o.get('bytes','?')} bytes]  sha256={str(o.get('sha256',''))[:16]}…")
    delivery = result.get("delivery_bundle") or {}
    if delivery:
        lines += [
            "",
            "Review bundle:",
            "  - Review\\SUMMARY.txt",
            "  - Review\\CONTACT_SHEET.jpg",
            "  - Review\\SELECTIONS.csv",
            "  - Review\\PROVENANCE.json",
            f"  - bundle sha256={delivery.get('bundle_content_sha256','')}",
        ]
    covers = result.get("cover_assets") or {}
    if covers.get("status")=="PASS":
        lines += ["", "Covers:"]
        for c in covers.get("covers", []): lines.append(f"  - {c.get('profile','?')}: Covers\\{c.get('filename','?')}  sha256={str(c.get('sha256',''))[:16]}…")
    alternatives = result.get("automatic_alternatives") or {}
    if alternatives:
        lines += ["", f"Automatic alternatives: {alternatives.get('variant_count',0)}"]
        for v in alternatives.get("variants", []):
            lines.append(f"  - {v.get('strategy_key','?')}: {v.get('strategy_name','')}  variant={v.get('variant_id','')}")
    comparison = result.get("variant_comparison") or {}
    if comparison:
        lines += ["", "Variant comparison:", r"  - Review\VariantComparison\COMPARE_16x9.jpg", r"  - Review\VariantComparison\COMPARE_9x16.jpg", f"  - comparison sha256={comparison.get('comparison_content_sha256','')}"]
    lines += ["", "Status: PASS", ""]
    (outdir / "RESULT.txt").write_text("\n".join(lines), encoding="utf-8")


def write_failure_card(queue_root: Path, outbox: Path, state: dict) -> None:
    job_id = str(state.get("job_id") or "unknown")
    lines = [
        "MediaEngine Auto Edit — FAILED",
        "=" * 40,
        f"Job: {job_id}",
        f"Label: {state.get('label','')}",
        f"Attempt: {state.get('attempt','')}",
        f"Target: {human_seconds(state.get('target_seconds'))}",
        f"Pacing: clip={human_seconds((state.get('job_config') or {}).get('clip_seconds'))}  transition={human_seconds((state.get('job_config') or {}).get('transition_seconds'))}",
        f"Audio target: {(state.get('job_config') or {}).get('audio_lufs','?')} LUFS  TP={(state.get('job_config') or {}).get('audio_true_peak_db','?')} dBTP",
        f"Vertical framing: {(state.get('job_config') or {}).get('vertical_framing','fill')}  focus_x={(state.get('job_config') or {}).get('vertical_focus_x',0.5)}  resolution={(state.get('job_config') or {}).get('output_resolution','standard')}  fps={(state.get('job_config') or {}).get('output_fps',30)}  quality={(state.get('job_config') or {}).get('video_quality','standard')}",
        f"Error: {state.get('error','unknown')}",
        "",
        "Source files:",
    ]
    for s in state.get("sources", []):
        lines.append(f"  - {s.get('name','?')}  [{s.get('bytes','?')} bytes]  sha256={str(s.get('sha256',''))[:16]}…")
    lines += [
        "",
        "This job will NOT retry forever.",
        f"To retry only this exact job, run RETRY_FAILED_JOB_V52.ps1 -JobId '{job_id}'.",
        "",
    ]
    text = "\n".join(lines)
    job_dir = queue_root / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "FAILED.txt").write_text(text, encoding="utf-8")
    failed_dir = outbox / "_Failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    (failed_dir / f"{job_id}.txt").write_text(text, encoding="utf-8")


def failure_transition(processing: dict, job_config: dict, error_text: str, now: float | None = None) -> dict:
    now = time.time() if now is None else float(now)
    attempt = int(processing.get("attempt") or 0)
    max_attempts = int(job_config.get("max_attempts") or 1)
    backoff = float(job_config.get("retry_backoff_seconds") or 0.0)
    base = {**processing, "updated_at_unix": now, "error": error_text, "max_attempts": max_attempts}
    if attempt < max_attempts:
        return {**base, "status": "retry_wait", "next_retry_at_unix": now + backoff}
    return {**base, "status": "quarantined", "quarantined_at_unix": now}


def write_quarantine_record(queue_root: Path, outbox: Path, state: dict) -> None:
    job_id = str(state.get("job_id") or "unknown")
    attempt = int(state.get("attempt") or 0)
    qdir = queue_root / "quarantine" / job_id
    qdir.mkdir(parents=True, exist_ok=True)
    record = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "fingerprint": state.get("fingerprint"),
        "status": "QUARANTINED",
        "attempt": attempt,
        "max_attempts": state.get("max_attempts"),
        "error": state.get("error"),
        "source_key": state.get("source_key"),
        "sources": state.get("sources") or [],
        "quarantined_at_unix": state.get("quarantined_at_unix") or time.time(),
        "semantic_selection_claim": False,
    }
    atomic_json(qdir / f"attempt-{attempt}.json", record)
    atomic_json(qdir / "LATEST.json", record)
    marker = outbox / "_Quarantine" / f"{job_id}.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        "MediaEngine Auto Edit — QUARANTINED\n"
        + "=" * 40 + "\n"
        + f"Job: {job_id}\nAttempt: {attempt}/{state.get('max_attempts')}\n"
        + f"Error: {state.get('error','unknown')}\n\n"
        + f"Exact retry only: RETRY_FAILED_JOB_V52.ps1 -JobId '{job_id}'\n",
        encoding="utf-8",
    )


def mark_quarantine_resolved(queue_root: Path, outbox: Path, state: dict) -> None:
    job_id = str(state.get("job_id") or "unknown")
    qdir = queue_root / "quarantine" / job_id
    if qdir.is_dir():
        atomic_json(qdir / "RESOLVED.json", {
            "candidate": CANDIDATE,
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "fingerprint": state.get("fingerprint"),
            "status": "RESOLVED",
            "resolved_at_unix": time.time(),
            "semantic_selection_claim": False,
        })
    (outbox / "_Quarantine" / f"{job_id}.txt").unlink(missing_ok=True)


def consume_targeted_retry(sp: Path, state: dict, fp: str, queue_root: Path) -> tuple[bool, str | None]:
    retry_request = sp.parent / "RETRY.request"
    if not retry_request.is_file():
        return False, None
    req = read_json(retry_request) or {}
    if req.get("fingerprint") not in (None, "", fp):
        return False, "fingerprint_mismatch"
    consumed = sp.parent / f"RETRY.consumed.attempt-{int(state.get('attempt',0))+1}.json"
    os.replace(retry_request, consumed)
    append_history(queue_root, "retry_consumed", state, {"request": str(consumed)})
    return True, None


def collect_job_states(queue_root: Path) -> list[dict]:
    rows = []
    jobs = queue_root / "jobs"
    if jobs.is_dir():
        for p in jobs.glob("*/job_state.json"):
            obj = read_json(p)
            if obj:
                rows.append(obj)
    rows.sort(key=lambda x: float(x.get("updated_at_unix") or x.get("started_at_unix") or 0), reverse=True)
    return rows


def write_status_files(queue_root: Path, outbox: Path, summary: dict | None = None) -> None:
    rows = collect_job_states(queue_root)
    counts: dict[str, int] = {}
    for r in rows:
        s = str(r.get("status") or "unknown")
        counts[s] = counts.get(s, 0) + 1
    payload = {
        "candidate": CANDIDATE,
        "updated_at_unix": time.time(),
        "worker_locked": (queue_root / "worker.lock").exists(),
        "counts": counts,
        "jobs": rows,
        "last_scan": summary,
    }
    atomic_json(queue_root / "STATUS.json", payload)
    lines = [
        "MediaEngine Auto Edit Queue",
        "=" * 40,
        f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['updated_at_unix']))}",
        f"Worker: {'RUNNING' if payload['worker_locked'] else 'STOPPED'}",
        "Counts: " + (", ".join(f"{k}={v}" for k,v in sorted(counts.items())) if counts else "no jobs yet"),
        "",
        "Recent jobs:",
    ]
    for r in rows[:20]:
        job_id = str(r.get("job_id") or "?")
        status = str(r.get("status") or "?").upper()
        label = str(r.get("label") or "")
        target = human_seconds(r.get("target_seconds"))
        attempt = r.get("attempt", "?")
        lines.append(f"  [{status:10}] {job_id}  label={label}  target={target}  attempt={attempt}")
        if r.get("error"):
            lines.append(f"               error={r.get('error')}")
        if r.get("published_result"):
            lines.append(f"               result={r.get('published_result')}")
    if summary and summary.get("results"):
        lines += ["", "Current inbox scan:"]
        for x in summary.get("results", [])[:50]:
            extra=[]
            if x.get("target_seconds") is not None: extra.append(f"target={human_seconds(x.get('target_seconds'))}")
            if x.get("ready_mode"): extra.append(f"ready={x.get('ready_mode')}")
            suffix=("  "+"  ".join(extra)) if extra else ""
            lines.append(f"  [{str(x.get('status','?')).upper():24}] {x.get('label','')}{suffix}")
    lines += [
        "",
        f"Inbox: {summary.get('inbox') if summary else ''}",
        f"Output: {summary.get('outbox') if summary else str(outbox)}",
        f"History: {queue_root / 'HISTORY.jsonl'}",
        "",
    ]
    (queue_root / "STATUS.txt").write_text("\n".join(lines), encoding="utf-8")


def path_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False

def validate_roots(inbox: Path, outbox: Path, queue_root: Path) -> None:
    roots=[inbox.resolve(),outbox.resolve(),queue_root.resolve()]
    names=['inbox','outbox','queue_root']
    for i in range(len(roots)):
        for j in range(i+1,len(roots)):
            if roots[i] == roots[j] or path_under(roots[i],roots[j]) or path_under(roots[j],roots[i]):
                raise RuntimeError(f"V37_ROOTS_OVERLAP:{names[i]}:{names[j]}")

def slug(s: str) -> str:
    x = re.sub(r"[^A-Za-z0-9._-]+", "-", s.strip()).strip("-._")
    return (x or "job")[:80]


def supported_files(root: Path, recursive: bool) -> list[Path]:
    it = root.rglob("*") if recursive else root.iterdir()
    return sorted(
        [p.resolve() for p in it if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("MEDENG_")],
        key=lambda p: str(p).lower(),
    )


def is_settled(paths: Iterable[Path], settle_seconds: float, settle_cache: dict) -> bool:
    now=time.time(); rows=list(paths)
    if not rows:return False
    ready=True
    for p in rows:
        try: st=p.stat()
        except FileNotFoundError:return False
        if st.st_size<=0:return False
        key=str(p); old=settle_cache.get(key) if isinstance(settle_cache,dict) else None
        same=bool(old and int(old.get('bytes',-1))==st.st_size and int(old.get('mtime_ns',-1))==st.st_mtime_ns)
        stable_since=float(old.get('stable_since_unix')) if same and old.get('stable_since_unix') is not None else now
        settle_cache[key]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'stable_since_unix':stable_since,'last_seen_unix':now}
        if p.name.endswith((".part",".tmp",".crdownload")) or now-stable_since < settle_seconds: ready=False
    return ready


@dataclass
class CandidateJob:
    label: str
    source_key: str
    files: list[Path]
    batch_root: Path | None = None
    config_path: Path | None = None


def scan_inbox(inbox: Path) -> list[CandidateJob]:
    jobs: list[CandidateJob] = []
    # Loose files are intentionally independent jobs. A folder is one batch job.
    for p in sorted(inbox.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith(".") or p.name.startswith("_"):
            continue
        if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("MEDENG_"):
            jobs.append(CandidateJob(label=p.stem, source_key=p.name, files=[p.resolve()], batch_root=None, config_path=None))
        elif p.is_dir():
            files = supported_files(p, recursive=True)
            if files:
                jobs.append(CandidateJob(label=p.name, source_key=p.name + "/", files=files, batch_root=p.resolve(), config_path=((p / "AUTO_EDIT.json").resolve() if (p / "AUTO_EDIT.json").is_file() else None)))
    return jobs



def folder_inventory_signature(root: Path) -> tuple[str, list[dict]]:
    """Return a deterministic signature for files that affect batch intake readiness.

    Supported media plus common in-progress transfer files are included.  The
    signature changes when a file is added/removed/renamed/resized or its mtime
    changes, so a batch folder cannot start while its inventory is still moving.
    """
    rows=[]
    if not root.is_dir():
        return "", rows
    for p in sorted(root.rglob("*"), key=lambda x: str(x).lower()):
        if not p.is_file():
            continue
        rel=str(p.relative_to(root)).replace("\\","/")
        low=p.name.lower()
        relevant=(p.suffix.lower() in SUPPORTED or low.endswith((".part",".tmp",".crdownload")) or low in ("auto_edit.ready","auto_edit.json"))
        if not relevant:
            continue
        try:
            st=p.stat()
        except FileNotFoundError:
            continue
        rows.append({"rel":rel,"bytes":int(st.st_size),"mtime_ns":int(st.st_mtime_ns)})
    raw=json.dumps(rows,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode()).hexdigest(), rows


def is_folder_inventory_settled(root: Path, settle_seconds: float, settle_cache: dict, require_ready_marker: bool=False) -> bool:
    now=time.time()
    if not root.is_dir():
        return False
    if require_ready_marker and not (root / "AUTO_EDIT.READY").is_file():
        return False
    sig, rows=folder_inventory_signature(root)
    if not rows:
        return False
    # A stable transfer-temp file is still an incomplete transfer.  Do not
    # process a batch until all .part/.tmp/.crdownload artifacts are gone.
    if any(str(r.get("rel","")).lower().endswith((".part",".tmp",".crdownload")) for r in rows):
        key="folder::"+str(root.resolve())
        settle_cache[key]={
            "inventory_sha256":sig,
            "file_count":len(rows),
            "stable_since_unix":now,
            "last_seen_unix":now,
            "blocked_transfer_temp":True,
            "require_ready_marker":bool(require_ready_marker),
        }
        return False
    key="folder::"+str(root.resolve())
    old=settle_cache.get(key) if isinstance(settle_cache,dict) else None
    same=bool(old and old.get("inventory_sha256")==sig)
    stable_since=float(old.get("stable_since_unix")) if same and old.get("stable_since_unix") is not None else now
    settle_cache[key]={
        "inventory_sha256":sig,
        "file_count":len(rows),
        "stable_since_unix":stable_since,
        "last_seen_unix":now,
        "require_ready_marker":bool(require_ready_marker),
    }
    # Explicit READY is an extra authorization signal, not a shortcut around
    # observing stable bytes.  Both conditions must hold.
    return now-stable_since >= settle_seconds


def load_job_config(path: Path | None, default_target: float, global_require_marker: bool) -> tuple[dict, str | None, str | None]:
    cfg={"schema_version":1,"target_seconds":float(default_target),"clip_seconds":5.0,"transition_seconds":0.25,"audio_lufs":-18.0,"audio_true_peak_db":-2.0,"vertical_framing":"fill","vertical_focus_x":0.5,"output_resolution":"standard","output_fps":30,"video_quality":"standard","audio_content":"source","cover_mode":"off","cover_position":0.5,"ready_mode":"marker" if global_require_marker else "settle","approval_mode":"manual","max_attempts":1,"retry_backoff_seconds":30.0}
    if path is None:
        return cfg, None, None
    raw=path.read_bytes()
    try:
        obj=json.loads(raw.decode("utf-8-sig"))
    except Exception as e:
        raise ValueError("AUTO_EDIT_JSON_INVALID:"+type(e).__name__)
    if not isinstance(obj,dict):
        raise ValueError("AUTO_EDIT_JSON_OBJECT_REQUIRED")
    allowed={"schema_version","target_seconds","clip_seconds","transition_seconds","audio_lufs","audio_true_peak_db","vertical_framing","vertical_focus_x","output_resolution","output_fps","video_quality","audio_content","cover_mode","cover_position","ready_mode","approval_mode","max_attempts","retry_backoff_seconds"}
    unknown=sorted(set(obj)-allowed)
    if unknown:
        raise ValueError("AUTO_EDIT_JSON_UNKNOWN_KEYS:"+",".join(unknown))
    if int(obj.get("schema_version",1))!=1:
        raise ValueError("AUTO_EDIT_JSON_SCHEMA_VERSION")
    try: target=float(obj.get("target_seconds",default_target))
    except Exception: raise ValueError("AUTO_EDIT_JSON_TARGET_INVALID")
    if not (5.0 <= target <= 120.0):
        raise ValueError("AUTO_EDIT_JSON_TARGET_RANGE_5_120")
    try: clip_seconds=float(obj.get("clip_seconds",5.0))
    except Exception: raise ValueError("AUTO_EDIT_JSON_CLIP_SECONDS_INVALID")
    if not (1.5 <= clip_seconds <= 12.0):
        raise ValueError("AUTO_EDIT_JSON_CLIP_SECONDS_RANGE_1_5_12")
    try: transition_seconds=float(obj.get("transition_seconds",0.25))
    except Exception: raise ValueError("AUTO_EDIT_JSON_TRANSITION_SECONDS_INVALID")
    max_transition=min(1.5,clip_seconds*0.40)
    if transition_seconds < 0.0 or transition_seconds > max_transition:
        raise ValueError("AUTO_EDIT_JSON_TRANSITION_SECONDS_RANGE")
    try: audio_lufs=float(obj.get("audio_lufs",-18.0))
    except Exception: raise ValueError("AUTO_EDIT_JSON_AUDIO_LUFS_INVALID")
    if not (-24.0 <= audio_lufs <= -12.0):
        raise ValueError("AUTO_EDIT_JSON_AUDIO_LUFS_RANGE_-24_-12")
    try: audio_true_peak_db=float(obj.get("audio_true_peak_db",-2.0))
    except Exception: raise ValueError("AUTO_EDIT_JSON_AUDIO_TRUE_PEAK_DB_INVALID")
    if not (-6.0 <= audio_true_peak_db <= -1.0):
        raise ValueError("AUTO_EDIT_JSON_AUDIO_TRUE_PEAK_DB_RANGE_-6_-1")
    vertical_framing=str(obj.get("vertical_framing","fill")).strip().lower()
    if vertical_framing not in ("fill","fit_blur"):
        raise ValueError("AUTO_EDIT_JSON_VERTICAL_FRAMING")
    try: vertical_focus_x=float(obj.get("vertical_focus_x",0.5))
    except Exception: raise ValueError("AUTO_EDIT_JSON_VERTICAL_FOCUS_X_INVALID")
    if not (0.0 <= vertical_focus_x <= 1.0):
        raise ValueError("AUTO_EDIT_JSON_VERTICAL_FOCUS_X_RANGE_0_1")
    if vertical_framing=="fit_blur" and abs(vertical_focus_x-0.5)>1e-9:
        raise ValueError("AUTO_EDIT_JSON_VERTICAL_FOCUS_X_REQUIRES_FILL")
    output_resolution=str(obj.get("output_resolution","standard")).strip().lower()
    if output_resolution not in ("standard","social_hd"):
        raise ValueError("AUTO_EDIT_JSON_OUTPUT_RESOLUTION")
    try: output_fps=int(obj.get("output_fps",30))
    except Exception: raise ValueError("AUTO_EDIT_JSON_OUTPUT_FPS_INVALID")
    if output_fps not in (30,60):
        raise ValueError("AUTO_EDIT_JSON_OUTPUT_FPS")
    video_quality=str(obj.get("video_quality","standard")).strip().lower()
    if video_quality not in ("standard","high"):
        raise ValueError("AUTO_EDIT_JSON_VIDEO_QUALITY")
    audio_content=str(obj.get("audio_content","source")).strip().lower()
    if audio_content not in ("source","mute"):
        raise ValueError("AUTO_EDIT_JSON_AUDIO_CONTENT")
    cover_mode=str(obj.get("cover_mode","off")).strip().lower()
    if cover_mode not in ("off","auto"):
        raise ValueError("AUTO_EDIT_JSON_COVER_MODE")
    try: cover_position=float(obj.get("cover_position",0.5))
    except Exception: raise ValueError("AUTO_EDIT_JSON_COVER_POSITION_INVALID")
    if not (0.0 <= cover_position <= 1.0):
        raise ValueError("AUTO_EDIT_JSON_COVER_POSITION_RANGE_0_1")
    mode=str(obj.get("ready_mode", "marker" if global_require_marker else "settle")).strip().lower()
    if mode not in ("settle","marker"):
        raise ValueError("AUTO_EDIT_JSON_READY_MODE")
    if global_require_marker:
        mode="marker"
    approval_mode=str(obj.get("approval_mode","manual")).strip().lower()
    if approval_mode not in ("manual","auto"):
        raise ValueError("AUTO_EDIT_JSON_APPROVAL_MODE")
    
    try:
        max_attempts=int(obj.get("max_attempts",1))
    except Exception:
        raise ValueError("AUTO_EDIT_JSON_MAX_ATTEMPTS_INVALID")
    if max_attempts < 1 or max_attempts > 4:
        raise ValueError("AUTO_EDIT_JSON_MAX_ATTEMPTS_RANGE_1_4")
    try:
        retry_backoff_seconds=float(obj.get("retry_backoff_seconds",30.0))
    except Exception:
        raise ValueError("AUTO_EDIT_JSON_RETRY_BACKOFF_INVALID")
    if retry_backoff_seconds < 0 or retry_backoff_seconds > 3600:
        raise ValueError("AUTO_EDIT_JSON_RETRY_BACKOFF_RANGE_0_3600")
    cfg={"schema_version":1,"target_seconds":target,"clip_seconds":clip_seconds,"transition_seconds":transition_seconds,"audio_lufs":audio_lufs,"audio_true_peak_db":audio_true_peak_db,"vertical_framing":vertical_framing,"vertical_focus_x":vertical_focus_x,"output_resolution":output_resolution,"output_fps":output_fps,"video_quality":video_quality,"audio_content":audio_content,"cover_mode":cover_mode,"cover_position":cover_position,"ready_mode":mode,"approval_mode":approval_mode,"max_attempts":max_attempts,"retry_backoff_seconds":retry_backoff_seconds}
    canonical=json.dumps(cfg,sort_keys=True,separators=(",",":"))
    config_sha256=hashlib.sha256(canonical.encode()).hexdigest()
    render_policy={}
    if abs(clip_seconds-5.0)>1e-9 or abs(transition_seconds-0.25)>1e-9:
        render_policy.update({"clip_seconds":clip_seconds,"transition_seconds":transition_seconds})
    if abs(audio_lufs-(-18.0))>1e-9 or abs(audio_true_peak_db-(-2.0))>1e-9:
        render_policy.update({"audio_lufs":audio_lufs,"audio_true_peak_db":audio_true_peak_db})
    if vertical_framing!="fill":
        render_policy["vertical_framing"]=vertical_framing
    if abs(vertical_focus_x-0.5)>1e-9:
        render_policy["vertical_focus_x"]=vertical_focus_x
    if output_resolution!="standard":
        render_policy["output_resolution"]=output_resolution
    if output_fps!=30:
        render_policy["output_fps"]=output_fps
    if video_quality!="standard":
        render_policy["video_quality"]=video_quality
    if audio_content!="source":
        render_policy["audio_content"]=audio_content
    render_identity=None
    if render_policy:
        render_canonical=json.dumps(render_policy,sort_keys=True,separators=(",",":"))
        render_identity=hashlib.sha256(render_canonical.encode()).hexdigest()
    return cfg, config_sha256, render_identity

def write_intake_error(queue_root: Path, label: str, error: str, config_path: Path | None) -> None:
    d=queue_root/"intake_errors"; d.mkdir(parents=True,exist_ok=True)
    p=d/(slug(label)+".txt")
    text="MediaEngine Auto Edit — INTAKE CONFIG ERROR\
"+"="*40+f"\
Job: {label}\
Error: {error}\
Config: {config_path or '(none)'}\
\
Fix AUTO_EDIT.json; media was not processed.\
"
    p.write_text(text,encoding="utf-8")

def cached_source_sha(p: Path, cache: dict) -> str:
    st=p.stat(); key=str(p)
    row=cache.get(key) if isinstance(cache,dict) else None
    if row and int(row.get('bytes',-1))==st.st_size and int(row.get('mtime_ns',-1))==st.st_mtime_ns and row.get('sha256'):
        return str(row['sha256'])
    digest=sha256_file(p)
    cache[key]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest,'updated_at_unix':time.time()}
    return digest

def fingerprint_job(job: CandidateJob, target_seconds: float, engine_sha256: str, hash_cache: dict, config_sha256: str | None=None) -> tuple[str, list[dict]]:
    entries = []
    identities = []
    for p in job.files:
        st = p.stat()
        digest = cached_source_sha(p, hash_cache)
        row = {"path": str(p), "name": p.name, "bytes": st.st_size, "sha256": digest}
        entries.append(row)
        identities.append((int(st.st_size), digest))
    h = hashlib.sha256()
    h.update(f"schema={SCHEMA_VERSION}\0target={float(target_seconds):.6f}\0engine={engine_sha256}\0config={config_sha256 or 'none'}\0".encode())
    for size, digest in sorted(identities):
        h.update(str(size).encode()); h.update(b"\0"); h.update(digest.encode()); h.update(b"\0")
    return h.hexdigest(), entries


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_published_result(outdir: Path, state: dict) -> dict | None:
    res = outdir / "JOB_RESULT.json"
    if not res.is_file():
        return None
    obj = read_json(res)
    if not obj or obj.get("status") != "PASS" or obj.get("fingerprint") != state.get("fingerprint"):
        return None
    for o in obj.get("outputs", []):
        p = outdir / o["filename"]
        if not p.is_file() or p.stat().st_size != int(o["bytes"]) or sha256_file(p) != o["sha256"]:
            return None
    return obj


def delivery_ref(bundle: dict) -> dict:
    return {
        "review_dir": "Review",
        "manifest": "Review/DELIVERY_MANIFEST.json",
        "bundle_content_sha256": bundle.get("bundle_content_sha256"),
        "selected_count": bundle.get("selected_count"),
        "asset_count": len(bundle.get("assets") or []),
    }


def alternatives_ref(summary: dict) -> dict:
    return {
        "root": "Alternatives",
        "manifest": "Alternatives/ALTERNATIVES_MANIFEST.json",
        "variant_count": int(summary.get("variant_count", 0)),
        "variants": [
            {
                "strategy_key": v.get("strategy_key"),
                "strategy_name": v.get("strategy_name"),
                "variant_id": v.get("variant_id"),
                "selected_event_ids": list(v.get("selected_event_ids") or []),
            }
            for v in (summary.get("variants") or [])
        ],
    }

def comparison_ref(m: dict) -> dict:
    return {
        "root": "Review/VariantComparison",
        "manifest": "Review/VariantComparison/COMPARISON_MANIFEST.json",
        "variant_count": int(m.get("variant_count", 0)),
        "comparison_content_sha256": m.get("comparison_content_sha256"),
    }

def validate_published(outdir: Path, state: dict) -> bool:
    obj = read_published_result(outdir, state)
    if not obj:
        return False
    alternatives = validate_public_alternatives(outdir)
    if not alternatives:
        return False
    bundle = validate_delivery_bundle(outdir, state.get("fingerprint"))
    if not bundle:
        return False
    comparison = validate_variant_comparison(outdir)
    if not comparison:
        return False
    ref = obj.get("delivery_bundle") or {}
    aref = obj.get("automatic_alternatives") or {}
    cref = obj.get("variant_comparison") or {}
    return (ref.get("bundle_content_sha256") == bundle.get("bundle_content_sha256")
            and int(aref.get("variant_count", -1)) == int(alternatives.get("variant_count", -2))
            and cref.get("comparison_content_sha256") == comparison.get("comparison_content_sha256"))



def pid_alive(pid: int, host: str):
    if host and host != socket.gethostname():
        return None
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            cp = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5, check=False)
            text = (cp.stdout or "") + (cp.stderr or "")
            return cp.returncode == 0 and str(pid) in text and "No tasks are running" not in text
        except Exception:
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None

def acquire_lock(path: Path, stale_seconds: float, recover_stale: bool) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate": CANDIDATE,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at_unix": time.time(),
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload
    except FileExistsError:
        old = read_json(path) or {}
        age = time.time() - float(old.get("created_at_unix") or path.stat().st_mtime)
        alive = pid_alive(int(old.get("pid") or 0), str(old.get("host") or ""))
        # A dead PID on the same host is safe to recover immediately after a crash/reboot.
        stale_ok = (alive is False) or (recover_stale and age >= stale_seconds)
        if stale_ok:
            stale = path.with_name(f"worker.lock.stale.{int(time.time())}.{os.getpid()}")
            try:
                os.replace(path, stale)
            except OSError:
                raise RuntimeError("QUEUE_LOCKED")
            return acquire_lock(path, stale_seconds, False)
        raise RuntimeError("QUEUE_LOCKED")


def release_lock(path: Path, payload: dict) -> None:
    old = read_json(path)
    if old and old.get("pid") == payload.get("pid") and old.get("host") == payload.get("host"):
        path.unlink(missing_ok=True)


def kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
        except Exception:
            with contextlib.suppress(Exception): proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            with contextlib.suppress(Exception): proc.kill()
    with contextlib.suppress(Exception):
        proc.wait(timeout=10)

def run_engine(engine: Path, videos: list[Path], work: Path, target: float, clip_seconds: float, transition_seconds: float, audio_lufs: float, audio_true_peak_db: float, vertical_framing: str, vertical_focus_x: float, output_resolution: str, output_fps: int, video_quality: str, audio_content: str, per_file_timeout: float, logdir: Path, job_hard_timeout_s: float) -> tuple[int, float]:
    logdir.mkdir(parents=True, exist_ok=True)
    stdout_p = logdir / "engine.stdout.log"
    stderr_p = logdir / "engine.stderr.log"
    cmd = [
        sys.executable, str(engine), "--output-root", str(work), "--target-seconds", str(target),
        "--clip-seconds", str(clip_seconds), "--transition", str(transition_seconds),
        "--per-file-timeout-s", str(per_file_timeout), *[str(x) for x in videos],
    ]
    started = time.perf_counter()
    timeout = float(job_hard_timeout_s) if job_hard_timeout_s > 0 else max(180.0, per_file_timeout * max(1, len(videos)) + 120.0)
    popen_kw = {}
    run_env=os.environ.copy()
    run_env["MEDENG_AUDIO_LUFS"]=f"{float(audio_lufs):.6f}"
    run_env["MEDENG_AUDIO_TRUE_PEAK_DB"]=f"{float(audio_true_peak_db):.6f}"
    run_env["MEDENG_VERTICAL_FRAMING"]=str(vertical_framing)
    run_env["MEDENG_VERTICAL_FOCUS_X"]=f"{float(vertical_focus_x):.6f}"
    run_env["MEDENG_OUTPUT_RESOLUTION"]=str(output_resolution)
    run_env["MEDENG_OUTPUT_FPS"]=str(int(output_fps))
    run_env["MEDENG_VIDEO_QUALITY"]=str(video_quality)
    run_env["MEDENG_AUDIO_CONTENT"]=str(audio_content)
    if os.name == "nt":
        popen_kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kw["start_new_session"] = True
    with stdout_p.open("ab") as out, stderr_p.open("ab") as err:
        proc = subprocess.Popen(cmd, stdout=out, stderr=err, env=run_env, **popen_kw)
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            err.write((f"\nV27_QUEUE_HARD_TIMEOUT seconds={timeout} pid={proc.pid}\n").encode())
            err.flush()
            kill_process_tree(proc)
            rc = 124
    return rc, time.perf_counter() - started


def publish_job(job_id: str, fingerprint: str, sources: list[dict], work: Path, outdir: Path, engine_result: dict, elapsed_s: float, clip_seconds: float, transition_seconds: float, audio_lufs: float, audio_true_peak_db: float, vertical_framing: str, vertical_focus_x: float, output_resolution: str, output_fps: int, video_quality: str, audio_content: str, cover_mode: str, cover_position: float) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    profile_names = {"16x9": "reel_16x9.mp4", "9x16": "reel_9x16.mp4"}
    outputs = []
    for o in engine_result.get("outputs", []):
        profile = o.get("profile")
        filename = profile_names.get(profile, f"reel_{slug(str(profile))}.mp4")
        src = Path(o["path"])
        if not src.is_file():
            raise RuntimeError(f"ENGINE_OUTPUT_MISSING:{src}")
        src_sha = sha256_file(src)
        if src_sha != o.get("sha256") or src.stat().st_size != int(o.get("bytes", -1)):
            raise RuntimeError(f"ENGINE_OUTPUT_IDENTITY_MISMATCH:{src}")
        dst = outdir / filename
        if dst.is_file():
            if dst.stat().st_size != src.stat().st_size or sha256_file(dst) != src_sha:
                raise RuntimeError(f"OUTBOX_COLLISION:{dst}")
        else:
            atomic_copy(src, dst)
        outputs.append({"profile": profile, "filename": filename, "bytes": dst.stat().st_size, "sha256": sha256_file(dst)})
    if len(outputs) < 2:
        raise RuntimeError("EXPECTED_TWO_PROFILE_OUTPUTS")
    covers = ensure_cover_assets(outdir, outputs, cover_mode, cover_position=cover_position)
    alternatives = build_auto_variants(work, outdir, 2)
    bundle = build_delivery_bundle(
        work=work,
        outdir=outdir,
        job_id=job_id,
        fingerprint=fingerprint,
        sources=sources,
        published_outputs=outputs,
        engine_elapsed_s=elapsed_s,
    )
    # Variant comparison validates AUTO identity through JOB_RESULT.json.
    # Publish a provisional PASS result first, then attach the comparison reference.
    # The comparison's AUTO source identity is the canonical output pair, not the JOB_RESULT file hash,
    # so the final metadata update cannot stale the comparison.
    result = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "job_id": job_id,
        "fingerprint": fingerprint,
        "source_files": sources,
        "engine_candidate": engine_result.get("candidate"),
        "engine_elapsed_s": round(elapsed_s, 3),
        "target_duration_s": engine_result.get("target_duration_s"),
        "clip_seconds": float(clip_seconds),
        "transition_seconds": float(transition_seconds),
        "audio_lufs": float(audio_lufs),
        "audio_true_peak_db": float(audio_true_peak_db),
        "audio_policy": ("LOCAL_SOURCE_LOUDNORM_TARGET_V43" if audio_content=="source" else "MUTED_SILENT_AAC_V47"),
        "semantic_selection_claim": False,
        "outputs": outputs,
        "cover_assets": covers,
        "delivery_bundle": delivery_ref(bundle),
        "automatic_alternatives": alternatives_ref(alternatives),
        "completed_at_unix": time.time(),
    }
    if vertical_framing!="fill":
        result["vertical_framing"]=vertical_framing
    if abs(float(vertical_focus_x)-0.5)>1e-9:
        result["vertical_focus_x"]=float(vertical_focus_x)
    if str(output_resolution)!="standard":
        result["output_resolution"]=str(output_resolution)
    if int(output_fps)!=30:
        result["output_fps"]=int(output_fps)
    if video_quality!="standard":
        result["video_quality"]=video_quality
    if str(audio_content)!="source":
        result["audio_content"]=str(audio_content)
    atomic_json(outdir / "JOB_RESULT.json", result)
    comparison = build_variant_comparison(outdir)
    result["variant_comparison"] = comparison_ref(comparison)
    atomic_json(outdir / "JOB_RESULT.json", result)
    write_result_card(outdir, result)
    return result


def state_path(queue_root: Path, job_id: str) -> Path:
    return queue_root / "jobs" / job_id / "job_state.json"


def load_existing_by_fingerprint(queue_root: Path) -> dict[str, tuple[Path, dict]]:
    found = {}
    jobs = queue_root / "jobs"
    if not jobs.is_dir():
        return found
    for p in jobs.glob("*/job_state.json"):
        obj = read_json(p)
        if obj and obj.get("fingerprint"):
            found[obj["fingerprint"]] = (p, obj)
    return found




COVER_CANDIDATE = "MEDENG_COVER_ASSETS_V48_RC1"

def _cover_decode_ok(ffmpeg: str, path: Path) -> bool:
    try:
        cp=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(path),"-f","null","-"],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30,check=False)
        return cp.returncode==0
    except Exception:
        return False

def ensure_cover_assets(outdir: Path, outputs: list[dict], cover_mode: str, ffmpeg: str | None = None, cover_position: float = 0.5) -> dict:
    cover_mode=str(cover_mode or "off").strip().lower()
    if cover_mode not in ("off","auto"):
        raise RuntimeError("COVER_MODE_INVALID")
    try: cover_position=float(cover_position)
    except Exception: raise RuntimeError("COVER_POSITION_INVALID")
    if not (0.0 <= cover_position <= 1.0): raise RuntimeError("COVER_POSITION_RANGE_0_1")
    if cover_mode=="off":
        root=outdir/"Covers";mp=root/"COVER_MANIFEST.json";mutated=False
        if root.exists():
            known=False
            if mp.is_file():
                try: known=(read_json(mp) or {}).get("candidate")==COVER_CANDIDATE
                except Exception: known=False
            if not known: raise RuntimeError("COVER_FOREIGN_CONTENT")
            shutil.rmtree(root);mutated=True
        return {"candidate":COVER_CANDIDATE,"status":"OFF","cover_mode":"off","cover_position":cover_position,"mutated":mutated,"semantic_selection_claim":False}
    ffmpeg=str(ffmpeg or os.environ.get("MEDENG_FFMPEG") or "ffmpeg")
    root=outdir/"Covers"; mp=root/"COVER_MANIFEST.json"
    expected=[]
    for o in sorted(outputs,key=lambda x:str(x.get("profile"))):
        profile=str(o.get("profile") or "");fn=str(o.get("filename") or "");src=outdir/fn
        if profile not in ("16x9","9x16") or not fn or not src.is_file():
            raise RuntimeError("COVER_SOURCE_OUTPUT_INVALID:"+profile)
        if src.stat().st_size!=int(o.get("bytes",-1)) or sha256_file(src)!=str(o.get("sha256") or ""):
            raise RuntimeError("COVER_SOURCE_IDENTITY_MISMATCH:"+profile)
        expected.append((profile,src,str(o.get("sha256"))))
    if len(expected)!=2:
        raise RuntimeError("COVER_EXPECTED_TWO_REELS")
    if mp.is_file():
        try:
            old=read_json(mp)
            if old and old.get("candidate")==COVER_CANDIDATE and old.get("status")=="PASS" and abs(float(old.get("cover_position",0.5))-cover_position)<=1e-9:
                rows=old.get("covers") or []
                if len(rows)==2:
                    good=True
                    for r in rows:
                        cp=root/str(r.get("filename") or "")
                        src=next((x for x in expected if x[0]==str(r.get("profile"))),None)
                        if not src or str(r.get("source_reel_sha256"))!=src[2] or not cp.is_file() or cp.stat().st_size!=int(r.get("bytes",-1)) or sha256_file(cp)!=str(r.get("sha256") or "") or not _cover_decode_ok(ffmpeg,cp):good=False;break
                    if good:
                        old=dict(old);old["resume_status"]="SKIPPED_EXACT_COMPLETED";old["mutated"]=False;return old
        except Exception:
            pass
    root.mkdir(parents=True,exist_ok=True)
    rows=[]
    for profile,src,source_sha in expected:
        pr=media_probe_json(src,ffmpeg,30);dur=float((pr.get("format") or {}).get("duration") or 0.0)
        if dur<=0:raise RuntimeError("COVER_SOURCE_DURATION_INVALID:"+profile)
        ss=min(max(0.0,dur*cover_position),max(0.0,dur-0.05))
        dst=root/f"cover_{profile}.jpg";tmp=root/f".{dst.name}.tmp.jpg";tmp.unlink(missing_ok=True)
        cmd=[ffmpeg,"-hide_banner","-loglevel","error","-y","-ss",f"{ss:.3f}","-i",str(src),"-frames:v","1","-q:v","2",str(tmp)]
        cp=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60,check=False)
        if cp.returncode!=0 or not tmp.is_file() or tmp.stat().st_size<=1000 or not _cover_decode_ok(ffmpeg,tmp):
            tmp.unlink(missing_ok=True);raise RuntimeError("COVER_EXTRACT_FAILED:"+profile+":"+(cp.stderr or b"")[-500:].decode("utf-8","replace"))
        os.replace(tmp,dst)
        dpr=media_probe_json(dst,ffmpeg,30);vs=next((x for x in dpr.get("streams",[]) if x.get("codec_type")=="video"),{})
        rows.append({"profile":profile,"filename":dst.name,"bytes":dst.stat().st_size,"sha256":sha256_file(dst),"source_reel_sha256":source_sha,"source_duration_s":dur,"cover_position":cover_position,"extraction_time_s":round(ss,3),"width":int(vs.get("width") or 0),"height":int(vs.get("height") or 0)})
    manifest={"candidate":COVER_CANDIDATE,"schema_version":1,"status":"PASS","cover_mode":"auto","cover_position":cover_position,"selection_policy":"POSITIONAL_TECHNICAL_COVER_V50","semantic_selection_claim":False,"covers":rows,"mutated":True,"updated_at_unix":time.time()}
    atomic_json(mp,manifest);return manifest

def apply_approval_policy(outdir: Path, outbox: Path, job_config: dict) -> dict:
    policy=str(job_config.get("approval_mode") or "manual").strip().lower()
    try:
        return ensure_auto_approval(outdir, policy, outbox / "LATEST_APPROVED.json")
    except Exception as e:
        return {
            "candidate":"MEDENG_AUTO_APPROVAL_V39_RC1",
            "policy":policy,
            "status":"ERROR",
            "error":type(e).__name__+": "+str(e),
            "mutated_approved":False,
            "semantic_selection_claim":False,
        }

def process_candidate(c: CandidateJob, args, engine: Path, engine_sha256: str, hash_cache: dict, settle_cache: dict) -> dict:
    settle_inputs=list(c.files) + ([c.config_path] if c.config_path is not None else [])
    if not is_settled(settle_inputs, args.settle_seconds, settle_cache):
        return {"label": c.label, "status": "waiting_settle"}
    try:
        job_config, config_sha256, render_config_sha256 = load_job_config(c.config_path, args.target_seconds, args.require_batch_ready_marker)
    except Exception as e:
        err=str(e); write_intake_error(args.queue_root,c.label,err,c.config_path)
        return {"label":c.label,"status":"invalid_job_config","error":err}
    with contextlib.suppress(Exception):
        (args.queue_root / "intake_errors" / (slug(c.label)+".txt")).unlink(missing_ok=True)
    effective_target=float(job_config["target_seconds"])
    effective_clip_seconds=float(job_config["clip_seconds"])
    effective_transition_seconds=float(job_config["transition_seconds"])
    effective_audio_lufs=float(job_config["audio_lufs"])
    effective_audio_true_peak_db=float(job_config["audio_true_peak_db"])
    effective_vertical_framing=str(job_config["vertical_framing"])
    effective_vertical_focus_x=float(job_config["vertical_focus_x"])
    effective_output_resolution=str(job_config["output_resolution"])
    effective_output_fps=int(job_config["output_fps"])
    effective_video_quality=str(job_config["video_quality"])
    effective_audio_content=str(job_config["audio_content"])
    effective_cover_mode=str(job_config["cover_mode"] )
    effective_cover_position=float(job_config["cover_position"])
    require_marker=job_config["ready_mode"]=="marker"
    folder_settle = args.settle_seconds if require_marker else args.batch_settle_seconds
    if c.batch_root is not None and not is_folder_inventory_settled(c.batch_root, folder_settle, settle_cache, require_marker):
        return {"label": c.label, "status": "waiting_folder_settle", "target_seconds": effective_target, "ready_mode": job_config["ready_mode"]}
    fp, sources = fingerprint_job(c, effective_target, engine_sha256, hash_cache, render_config_sha256)
    existing = load_existing_by_fingerprint(args.queue_root)
    if fp in existing:
        sp, state = existing[fp]
        job_id = state["job_id"]
        outdir = args.outbox / job_id
        if state.get("status") == "passed":
            if validate_published(outdir, state):
                prior=read_json(outdir / "JOB_RESULT.json") or {}
                covers=ensure_cover_assets(outdir,list(prior.get("outputs") or state.get("outputs") or []),str(job_config.get("cover_mode") or "off"),cover_position=float(job_config.get("cover_position",0.5)))
                prior["cover_assets"]=covers;prior["completed_at_unix"]=time.time();atomic_json(outdir/"JOB_RESULT.json",prior);write_result_card(outdir,prior)
                apol=apply_approval_policy(outdir,args.outbox,job_config)
                refreshed={**state,"job_config":job_config,"config_sha256":config_sha256,"render_config_sha256":render_config_sha256,"cover_assets":covers,"approval_policy":apol,"updated_at_unix":time.time()}
                atomic_json(sp,refreshed)
                append_history(args.queue_root,"approval_policy_reconciled",refreshed,{"outbox":str(outdir),"approval_status":apol.get("status")})
                status="skipped_exact_completed"
                if apol.get("status") in ("AUTO_APPROVED","SKIPPED_EXACT_AUTO","SKIPPED_EXACT_AUTO_RACE"): status="skipped_exact_completed_auto_approved"
                elif str(apol.get("status") or "").startswith("BLOCKED_"): status="skipped_exact_completed_auto_approval_blocked"
                elif apol.get("status")=="ERROR": status="skipped_exact_completed_auto_approval_error"
                return {"job_id": job_id, "label": c.label, "status": status, "fingerprint": fp,"approval_policy":apol}
            prior = read_published_result(outdir, state)
            if prior:
                try:
                    alternatives = build_auto_variants(sp.parent / "work", outdir, 2)
                    bundle = build_delivery_bundle(
                        work=sp.parent / "work", outdir=outdir, job_id=job_id, fingerprint=fp,
                        sources=list(prior.get("source_files") or state.get("sources") or sources),
                        published_outputs=list(prior.get("outputs") or []),
                        engine_elapsed_s=prior.get("engine_elapsed_s"),
                    )
                    comparison = build_variant_comparison(outdir)
                    prior["candidate"] = CANDIDATE
                    prior["delivery_bundle"] = delivery_ref(bundle)
                    prior["automatic_alternatives"] = alternatives_ref(alternatives)
                    prior["variant_comparison"] = comparison_ref(comparison)
                    prior["completed_at_unix"] = time.time()
                    atomic_json(outdir / "JOB_RESULT.json", prior)
                    write_result_card(outdir, prior)
                    repaired = {**state, "candidate": CANDIDATE, "status": "passed", "updated_at_unix": time.time(), "delivery_bundle": delivery_ref(bundle), "automatic_alternatives": alternatives_ref(alternatives), "variant_comparison": comparison_ref(comparison)}
                    atomic_json(sp, repaired)
                    append_history(args.queue_root, "variant_comparison_repaired", repaired, {"outbox": str(outdir)})
                    return {"job_id": job_id, "label": c.label, "status": "repaired_variant_comparison_bundle", "fingerprint": fp, "outbox": str(outdir)}
                except Exception:
                    pass
        if state.get("status") in ("failed", "retry_wait", "quarantined"):
            targeted_retry, retry_error = consume_targeted_retry(sp, state, fp, args.queue_root)
            if retry_error == "fingerprint_mismatch":
                return {"job_id": job_id, "label": c.label, "status": "retry_request_fingerprint_mismatch", "fingerprint": fp}
            if targeted_retry:
                append_history(args.queue_root, "targeted_retry_authorized", state)
            elif state.get("status") == "retry_wait":
                due = float(state.get("next_retry_at_unix") or 0.0)
                if time.time() < due:
                    return {
                        "job_id": job_id, "label": c.label, "status": "waiting_retry_backoff", "fingerprint": fp,
                        "attempt": int(state.get("attempt") or 0), "max_attempts": int(state.get("max_attempts") or job_config.get("max_attempts") or 1),
                        "next_retry_at_unix": due,
                    }
                append_history(args.queue_root, "bounded_auto_retry_due", state, {"next_retry_at_unix": due})
            else:
                # V39 legacy failed states and V40 quarantined states never retry implicitly.
                if state.get("status") == "failed":
                    migrated = {**state, "candidate": CANDIDATE, "status": "quarantined", "max_attempts": int(state.get("attempt") or 1), "quarantined_at_unix": time.time(), "updated_at_unix": time.time()}
                    atomic_json(sp, migrated)
                    append_history(args.queue_root, "legacy_failed_quarantined", migrated)
                    write_quarantine_record(args.queue_root, args.outbox, migrated)
                    state = migrated
                return {"job_id": job_id, "label": c.label, "status": "skipped_quarantined", "fingerprint": fp, "attempt": int(state.get("attempt") or 0)}
    else:
        job_id = f"{slug(c.label)}-{fp[:12]}"
        sp = state_path(args.queue_root, job_id)
        state = {}
    job_dir = sp.parent
    work = job_dir / "work"
    logdir = job_dir / "logs"
    outdir = args.outbox / job_id
    attempt = int(state.get("attempt", 0)) + 1
    now = time.time()
    processing = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "label": c.label,
        "source_key": c.source_key,
        "job_config": job_config,
        "config_sha256": config_sha256,
        "render_config_sha256": render_config_sha256,
        "fingerprint": fp,
        "sources": sources,
        "status": "processing",
        "attempt": attempt,
        "target_seconds": effective_target,
        "engine_sha256": engine_sha256,
        "started_at_unix": now,
        "updated_at_unix": now,
    }
    atomic_json(sp, processing)
    (sp.parent / "FAILED.txt").unlink(missing_ok=True)
    append_history(args.queue_root, "processing", processing)
    try:
        rc, elapsed = run_engine(engine, c.files, work, effective_target, effective_clip_seconds, effective_transition_seconds, effective_audio_lufs, effective_audio_true_peak_db, effective_vertical_framing, effective_vertical_focus_x, effective_output_resolution, effective_output_fps, effective_video_quality, effective_audio_content, args.per_file_timeout_s, logdir, args.job_hard_timeout_s)
        if rc != 0:
            raise RuntimeError(f"ENGINE_FAILED_RC_{rc}")
        rp = work / "VIDEO_TO_REEL_V26_RESULT.json"
        eng = read_json(rp)
        if not eng or eng.get("status") != "PASS":
            raise RuntimeError("ENGINE_RESULT_NOT_PASS")
        published = publish_job(job_id, fp, sources, work, outdir, eng, elapsed, effective_clip_seconds, effective_transition_seconds, effective_audio_lufs, effective_audio_true_peak_db, effective_vertical_framing, effective_vertical_focus_x, effective_output_resolution, effective_output_fps, effective_video_quality, effective_audio_content, effective_cover_mode, effective_cover_position)
        apol=apply_approval_policy(outdir,args.outbox,job_config)
        final = {**processing, "status": "passed", "updated_at_unix": time.time(), "published_result": str(outdir / "JOB_RESULT.json"), "outputs": published["outputs"], "delivery_bundle": published.get("delivery_bundle"), "automatic_alternatives": published.get("automatic_alternatives"), "variant_comparison": published.get("variant_comparison"), "approval_policy":apol, "engine_elapsed_s": round(elapsed, 3)}
        atomic_json(sp, final)
        append_history(args.queue_root, "passed", final, {"outbox": str(outdir)})
        failed_marker = args.outbox / "_Failed" / f"{job_id}.txt"
        failed_marker.unlink(missing_ok=True)
        mark_quarantine_resolved(args.queue_root, args.outbox, final)
        atomic_json(args.outbox / "LATEST.json", {"candidate": CANDIDATE, "job_id": job_id, "fingerprint": fp, "outbox": str(outdir), "updated_at_unix": time.time()})
        result_status="passed"
        if apol.get("status")=="AUTO_APPROVED": result_status="passed_auto_approved"
        elif str(apol.get("status") or "").startswith("BLOCKED_"): result_status="passed_auto_approval_blocked"
        elif apol.get("status")=="ERROR": result_status="passed_auto_approval_error"
        return {"job_id": job_id, "label": c.label, "status": result_status, "fingerprint": fp, "engine_elapsed_s": round(elapsed, 3), "outbox": str(outdir),"approval_policy":apol}
    except Exception as e:
        error_text = type(e).__name__ + ": " + str(e)
        fail = failure_transition(processing, job_config, error_text)
        atomic_json(sp, fail)
        if fail["status"] == "retry_wait":
            append_history(args.queue_root, "retry_wait", fail, {"next_retry_at_unix": fail.get("next_retry_at_unix")})
            write_failure_card(args.queue_root, args.outbox, fail)
            return {
                "job_id": job_id, "label": c.label, "status": "retry_wait", "fingerprint": fp, "error": fail["error"],
                "attempt": fail["attempt"], "max_attempts": fail["max_attempts"], "next_retry_at_unix": fail["next_retry_at_unix"],
            }
        append_history(args.queue_root, "quarantined", fail)
        write_failure_card(args.queue_root, args.outbox, fail)
        write_quarantine_record(args.queue_root, args.outbox, fail)
        return {
            "job_id": job_id, "label": c.label, "status": "quarantined", "fingerprint": fp, "error": fail["error"],
            "attempt": fail["attempt"], "max_attempts": fail["max_attempts"],
        }


def run_scan(args, engine: Path, engine_sha256: str) -> dict:
    args.inbox.mkdir(parents=True, exist_ok=True)
    args.outbox.mkdir(parents=True, exist_ok=True)
    args.queue_root.mkdir(parents=True, exist_ok=True)
    cache_path=args.queue_root/'source_hash_cache.json'
    settle_path=args.queue_root/'settle_observations.json'
    hash_cache=read_json(cache_path) or {}
    settle_cache=read_json(settle_path) or {}
    candidates = scan_inbox(args.inbox)
    rows = []
    for c in candidates:
        rows.append(process_candidate(c, args, engine, engine_sha256, hash_cache, settle_cache))
    atomic_json(cache_path, hash_cache)
    atomic_json(settle_path, settle_cache)
    summary = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "scanned_at_unix": time.time(),
        "inbox": str(args.inbox),
        "outbox": str(args.outbox),
        "queue_root": str(args.queue_root),
        "default_target_seconds": args.target_seconds,
        "jobs_seen": len(candidates),
        "results": rows,
    }
    atomic_json(args.queue_root / "LAST_SCAN.json", summary)
    write_status_files(args.queue_root, args.outbox, summary)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Local-only drop-folder queue with folder-inventory settle safety for MediaEngine AUTO_EDIT V26.")
    ap.add_argument("--inbox", required=True)
    ap.add_argument("--outbox", required=True)
    ap.add_argument("--queue-root", required=True)
    ap.add_argument("--engine", default="")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    ap.add_argument("--target-seconds", type=float, default=30)
    ap.add_argument("--per-file-timeout-s", type=float, default=180)
    ap.add_argument("--job-hard-timeout-s", type=float, default=0, help="0 = computed from per-file timeout and job size")
    ap.add_argument("--settle-seconds", type=float, default=5.0)
    ap.add_argument("--batch-settle-seconds", type=float, default=30.0, help="Quiet window for batch-folder inventory; marker mode uses --settle-seconds")
    ap.add_argument("--poll-seconds", type=float, default=3.0)
    ap.add_argument("--require-batch-ready-marker", action="store_true", help="Batch folders require AUTO_EDIT.READY in addition to folder/file settle")
    ap.add_argument("--stale-lock-seconds", type=float, default=21600)
    ap.add_argument("--recover-stale-lock", action="store_true")
    a = ap.parse_args()
    a.inbox = Path(a.inbox).resolve(); a.outbox = Path(a.outbox).resolve(); a.queue_root = Path(a.queue_root).resolve()
    validate_roots(a.inbox,a.outbox,a.queue_root)
    here = Path(__file__).resolve().parent
    engine = Path(a.engine).resolve() if a.engine else here / "medeng_video_to_reel_v26.py"
    if not engine.is_file():
        raise SystemExit("V37_ENGINE_MISSING")
    engine_sha256 = sha256_file(engine)
    if a.target_seconds <= 0 or a.per_file_timeout_s <= 0 or a.job_hard_timeout_s < 0 or a.settle_seconds < 0 or a.batch_settle_seconds < 0 or a.poll_seconds <= 0:
        raise SystemExit("V37_INVALID_ARGUMENT")
    lock = a.queue_root / "worker.lock"
    try:
        lp = acquire_lock(lock, a.stale_lock_seconds, a.recover_stale_lock)
    except RuntimeError as e:
        print(json.dumps({"candidate": CANDIDATE, "status": "LOCKED", "error": str(e)}))
        raise SystemExit(8)
    try:
        stop = a.queue_root / "STOP.request"
        if stop.exists():
            stop.unlink()
        if a.once:
            summary = run_scan(a, engine, engine_sha256)
            waiting=[str(x.get('status','')) for x in summary.get('results',[])]
            if any(x.startswith('waiting_') for x in waiting):
                sleep_s=a.settle_seconds
                if 'waiting_folder_settle' in waiting and not a.require_batch_ready_marker:
                    sleep_s=max(sleep_s,a.batch_settle_seconds)
                if sleep_s>0:
                    time.sleep(sleep_s)
                    summary = run_scan(a, engine, engine_sha256)
            print(json.dumps(summary, indent=2))
            return
        while True:
            summary = run_scan(a, engine, engine_sha256)
            print(json.dumps({"candidate": CANDIDATE, "watch_scan": summary}, indent=2), flush=True)
            if stop.exists():
                stop.unlink(missing_ok=True)
                atomic_json(a.queue_root / "WORKER_STOPPED.json", {"candidate": CANDIDATE, "stopped_at_unix": time.time(), "reason": "STOP.request"})
                write_status_files(a.queue_root, a.outbox, summary)
                return
            time.sleep(a.poll_seconds)
    finally:
        release_lock(lock, lp)
        with contextlib.suppress(Exception):
            write_status_files(a.queue_root, a.outbox, read_json(a.queue_root / "LAST_SCAN.json"))


if __name__ == "__main__":
    main()

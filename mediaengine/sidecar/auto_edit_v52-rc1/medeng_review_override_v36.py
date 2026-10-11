#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

import medeng_targeted_auto_edit_v26 as core

CANDIDATE = "MEDENG_REVIEW_OVERRIDE_V36_RC1"
SCHEMA_VERSION = 1
EVENT_ID_RE = re.compile(r"^[0-9a-f]{24}$")

class OverrideError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def parse_selection(path: Path) -> list[str]:
    if not path.is_file():
        raise OverrideError("SELECTION_REQUEST_MISSING")
    ids = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not EVENT_ID_RE.fullmatch(line):
            raise OverrideError(f"INVALID_EVENT_ID:{line}")
        if line in ids:
            raise OverrideError(f"DUPLICATE_EVENT_ID:{line}")
        ids.append(line)
    if not ids:
        raise OverrideError("SELECTION_EMPTY")
    if len(ids) > 30:
        raise OverrideError("SELECTION_TOO_LARGE")
    return ids


def validate_resume(render_dir: Path, request_sha: str, lib_sha: str, core_sha: str) -> dict | None:
    mp = render_dir / "OVERRIDE_MANIFEST.json"
    if not mp.is_file():
        return None
    try:
        o = json.loads(mp.read_text(encoding="utf-8"))
        if o.get("candidate") != CANDIDATE or o.get("status") != "PASS":
            return None
        if o.get("request_sha256") != request_sha or o.get("event_library_sha256") != lib_sha or o.get("renderer_sha256") != core_sha:
            return None
        for q in o.get("outputs", []):
            p = render_dir / q["filename"]
            if not p.is_file() or p.stat().st_size != int(q["bytes"]) or sha256_file(p) != q["sha256"]:
                return None
            core.full_decode(p)
        o["resume_status"] = "SKIPPED_EXACT_COMPLETED"
        return o
    except Exception:
        return None


def _quarantine_invalid(render_dir: Path, override_root: Path) -> Path | None:
    if not render_dir.exists():
        return None
    qroot = override_root / "_CorruptRenders"
    qroot.mkdir(parents=True, exist_ok=True)
    dst = qroot / f"{render_dir.name}.{int(time.time())}.{os.getpid()}"
    os.replace(render_dir, dst)
    return dst


def build(work: Path, outdir: Path, selection_file: Path) -> dict:
    work = Path(work).resolve(); outdir = Path(outdir).resolve(); selection_file = Path(selection_file).resolve()
    event_library = work / "event_library" / "EVENT_LIBRARY.json"
    edit_dir = work / "target_auto_edit_polish"
    auto_manifest = edit_dir / "AUTO_EDIT_V26_MANIFEST.json"
    score_cache = edit_dir / "V22_SCORE_CACHE.json"
    if not event_library.is_file() or not auto_manifest.is_file():
        raise OverrideError("RETAINED_WORK_EVIDENCE_MISSING")
    req_ids = parse_selection(selection_file)
    request_sha = sha256_file(selection_file)
    lib_sha = sha256_file(event_library)
    renderer_path = Path(core.__file__).resolve()
    core_sha = sha256_file(renderer_path)
    render_id = f"{request_sha[:12]}-{lib_sha[:8]}"
    override_root = outdir / "Override"
    renders_root = override_root / "renders"
    render_dir = renders_root / render_id
    resumed = validate_resume(render_dir, request_sha, lib_sha, core_sha)
    if resumed:
        atomic_json(override_root / "LATEST_OVERRIDE.json", {"candidate": CANDIDATE, "render_id": render_id, "manifest": str((render_dir/'OVERRIDE_MANIFEST.json').resolve()), "updated_at_unix": time.time()})
        return resumed
    # Never render into the public final path. If a stale/partial older render is
    # present, preserve it outside renders/ before starting the replacement.
    if render_dir.exists():
        _quarantine_invalid(render_dir, override_root)

    auto = json.loads(auto_manifest.read_text(encoding="utf-8"))
    _, events = core.load_library(event_library)
    scored = core.score_events(events, score_cache)
    by_id = {e["event_id"]: e for e in scored}
    missing = [eid for eid in req_ids if eid not in by_id]
    if missing:
        raise OverrideError("UNKNOWN_EVENT_ID:" + ",".join(missing))
    selected = [by_id[eid] for eid in req_ids]
    clip_seconds = float(auto.get("clip_seconds") or 5.0)
    transition = float(auto.get("transition_seconds") or 0.25)
    audio_lufs = float(auto.get("audio_lufs", -18.0))
    audio_true_peak_db = float(auto.get("audio_true_peak_db", -2.0))
    vertical_framing = str(auto.get("vertical_framing", "fill")).strip().lower()
    vertical_focus_x = float(auto.get("vertical_focus_x", 0.5))
    output_resolution = str(auto.get("output_resolution", "standard")).strip().lower()
    output_fps = int(auto.get("output_fps", 30))
    video_quality = str(auto.get("video_quality", "standard")).strip().lower()
    audio_content = str(auto.get("audio_content", "source")).strip().lower()

    renders_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = renders_root / f".{render_id}.tmp.{os.getpid()}.{int(time.time()*1000)}"
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    try:
        outputs = []
        selected_rows = []
        for i, e in enumerate(selected, 1):
            dur = core.used_duration(e, clip_seconds)
            off = max(0.0, (float(e["duration_s"]) - dur) / 2.0)
            selected_rows.append({
                "sequence": i,
                "event_id": e["event_id"],
                "source_name": e["source_name"],
                "source_sha256": e["source_sha256"],
                "source_interval_s": [float(e["start_s"]), float(e["end_s"])],
                "final_trim_source_interval_s": [round(float(e["start_s"])+off,3), round(float(e["start_s"])+off+dur,3)],
                "score": e["v22_score"],
                "technical_prominence": e["technical_prominence"],
            })

        for profile in ("16x9", "9x16"):
            segs=[]; metas=[]
            for i,e in enumerate(selected,1):
                p=tmp_dir/"work"/profile/f"{i:02d}_{e['event_id']}.mp4"
                meta=core.make_segment(e,p,profile,clip_seconds,audio_lufs,audio_true_peak_db,vertical_framing,vertical_focus_x,output_resolution,audio_content,output_fps,video_quality); segs.append(p); metas.append(meta)
            final=tmp_dir/f"override_reel_{profile}.mp4"
            expected=core.concat(segs,[m['duration_s'] for m in metas],final,transition,video_quality)
            pr=core.ffprobe(final)
            core.full_decode(final)
            outputs.append({"profile":profile,"filename":final.name,"bytes":final.stat().st_size,"sha256":sha256_file(final),"expected_duration_s":round(expected,3),"probe":pr})

        manifest={
            "candidate":CANDIDATE,"schema_version":SCHEMA_VERSION,"status":"PASS","render_id":render_id,
            "request_file":str(selection_file),"request_sha256":request_sha,"event_library_sha256":lib_sha,"renderer_sha256":core_sha,
            "user_override":True,"semantic_selection_claim":False,"selection_mode":"EXPLICIT_HUMAN_EVENT_ID_ORDER",
            "atomic_publish":True,"clip_seconds":clip_seconds,"transition_seconds":transition,"audio_lufs":audio_lufs,"audio_true_peak_db":audio_true_peak_db,"audio_policy":("LOCAL_SOURCE_LOUDNORM_TARGET_V43" if audio_content=="source" else "MUTED_SILENT_AAC_V47"),**({"vertical_framing":vertical_framing} if vertical_framing!="fill" else {}),**({"vertical_focus_x":vertical_focus_x} if abs(vertical_focus_x-0.5)>1e-9 else {}),**({"output_resolution":output_resolution} if output_resolution!="standard" else {}),**({"output_fps":output_fps} if output_fps!=30 else {}),**({"video_quality":video_quality} if video_quality!="standard" else {}),**({"audio_content":audio_content} if audio_content!="source" else {}),"selected_events":selected_rows,"outputs":outputs,"completed_at_unix":time.time(),
        }
        atomic_json(tmp_dir/"OVERRIDE_MANIFEST.json",manifest)
        lines=["MediaEngine Auto Edit — USER OVERRIDE", "="*44, f"Render: {render_id}", f"Scenes: {len(selected_rows)}", "Atomic publish: YES", "Original reels were NOT overwritten.", ""]
        for r in selected_rows: lines.append(f"  {r['sequence']:02d}. {r['source_name']}  {r['final_trim_source_interval_s'][0]:.2f}-{r['final_trim_source_interval_s'][1]:.2f}s  event={r['event_id']}")
        lines += ["", "Outputs:"]
        for o in outputs: lines.append(f"  - {o['profile']}: {o['filename']}  sha256={o['sha256']}")
        atomic_text(tmp_dir/"OVERRIDE_RESULT.txt","\n".join(lines)+"\n")
        # Validate the complete temporary tree before publishing it.
        complete = validate_resume(tmp_dir, request_sha, lib_sha, core_sha)
        if not complete:
            raise OverrideError("ATOMIC_TEMP_VALIDATION_FAILED")
        # Handle a concurrent publisher or a final path created between render and commit.
        if render_dir.exists():
            exact = validate_resume(render_dir, request_sha, lib_sha, core_sha)
            if exact:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                atomic_json(override_root/"LATEST_OVERRIDE.json",{"candidate":CANDIDATE,"render_id":render_id,"manifest":str((render_dir/'OVERRIDE_MANIFEST.json').resolve()),"updated_at_unix":time.time()})
                return exact
            _quarantine_invalid(render_dir, override_root)
        os.replace(tmp_dir, render_dir)
        atomic_json(override_root/"LATEST_OVERRIDE.json",{"candidate":CANDIDATE,"render_id":render_id,"manifest":str((render_dir/'OVERRIDE_MANIFEST.json').resolve()),"updated_at_unix":time.time()})
        return manifest
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def main():
    ap=argparse.ArgumentParser(description="Render an explicit local selection override from retained MediaEngine event previews without rediscovery.")
    ap.add_argument("--work",required=True); ap.add_argument("--outdir",required=True); ap.add_argument("--selection-file",required=True)
    a=ap.parse_args(); t=time.perf_counter() if False else None
    r=build(Path(a.work),Path(a.outdir),Path(a.selection_file))
    print(json.dumps({"candidate":r["candidate"],"status":r["status"],"render_id":r["render_id"],"selected_count":len(r["selected_events"]),"outputs":[{k:o[k] for k in ("profile","filename","bytes","sha256","expected_duration_s")} for o in r["outputs"]],"resume_status":r.get("resume_status")},indent=2))

if __name__=="__main__": main()

#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

CANDIDATE = "MEDENG_DELIVERY_BUNDLE_V36_RC1"
SCHEMA_VERSION = 1
REVIEW_DIRNAME = "Review"
CANDIDATE_LIMIT = 12
DEFAULT_FFMPEG = os.environ.get("MEDENG_FFMPEG", "ffmpeg")

class DeliveryError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DeliveryError(f"JSON_READ_FAILED:{path}:{type(e).__name__}:{e}") from e
    if not isinstance(obj, dict):
        raise DeliveryError(f"JSON_OBJECT_REQUIRED:{path}")
    return obj


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


def safe_rel(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError as e:
        raise DeliveryError(f"PATH_ESCAPES_BUNDLE:{path}") from e


def file_record(base: Path, path: Path, role: str) -> dict:
    if not path.is_file():
        raise DeliveryError(f"BUNDLE_ASSET_MISSING:{path}")
    return {
        "path": safe_rel(base, path),
        "role": role,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def verify_reels(outdir: Path, outputs: list[dict]) -> list[dict]:
    rows = []
    for o in outputs:
        fn = str(o.get("filename") or "")
        p = outdir / fn
        if not fn or not p.is_file():
            raise DeliveryError(f"PUBLISHED_REEL_MISSING:{fn}")
        if p.stat().st_size != int(o.get("bytes", -1)):
            raise DeliveryError(f"PUBLISHED_REEL_SIZE_MISMATCH:{fn}")
        digest = sha256_file(p)
        if digest != o.get("sha256"):
            raise DeliveryError(f"PUBLISHED_REEL_SHA_MISMATCH:{fn}")
        rows.append({
            "profile": o.get("profile"),
            "filename": fn,
            "bytes": p.stat().st_size,
            "sha256": digest,
        })
    if len(rows) < 2:
        raise DeliveryError("EXPECTED_TWO_PUBLISHED_REELS")
    return rows


def extract_thumb(ffmpeg: str, clip: Path, duration_s: float, out: Path) -> None:
    if not clip.is_file():
        raise DeliveryError(f"EVENT_CLIP_MISSING:{clip}")
    ss = max(0.0, min(float(duration_s) * 0.5, max(0.0, float(duration_s) - 0.05)))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part.jpg")
    tmp.unlink(missing_ok=True)
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{ss:.3f}", "-i", str(clip), "-frames:v", "1",
        "-vf", "scale=640:-2:force_original_aspect_ratio=decrease",
        "-q:v", "2", str(tmp),
    ]
    try:
        cp = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=45, check=False)
    except subprocess.TimeoutExpired as e:
        raise DeliveryError(f"THUMBNAIL_FFMPEG_TIMEOUT:{clip}") from e
    if cp.returncode != 0 or not tmp.is_file() or tmp.stat().st_size <= 0:
        err = (cp.stderr or b"")[-1200:].decode("utf-8", "replace")
        raise DeliveryError(f"THUMBNAIL_FFMPEG_FAILED:{clip}:{err}")
    try:
        with Image.open(tmp) as im:
            im.verify()
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise DeliveryError(f"THUMBNAIL_IMAGE_INVALID:{clip}:{e}") from e
    os.replace(tmp, out)


def build_contact_sheet(thumb_rows: list[dict], out: Path) -> None:
    if not thumb_rows:
        raise DeliveryError("NO_THUMBNAILS")
    cols = min(3, len(thumb_rows))
    rows = (len(thumb_rows) + cols - 1) // cols
    cell_w, image_h, label_h = 360, 202, 52
    cell_h = image_h + label_h
    canvas = Image.new("RGB", (cell_w * cols, cell_h * rows), "#111111")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for idx, row in enumerate(thumb_rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        with Image.open(row["thumb_path"]).convert("RGB") as im:
            fitted = ImageOps.contain(im, (cell_w - 8, image_h - 8))
            px = x + (cell_w - fitted.width) // 2
            py = y + 4 + (image_h - 8 - fitted.height) // 2
            canvas.paste(fitted, (px, py))
        label1 = f"#{row['sequence']}  {row['source_name']}"
        a, b = row["trim_interval"]
        label2 = f"{a:.2f}s - {b:.2f}s   score={row['score']:.3f}"
        draw.text((x + 8, y + image_h + 6), label1, fill="white", font=font)
        draw.text((x + 8, y + image_h + 26), label2, fill="#bbbbbb", font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part.jpg")
    canvas.save(tmp, format="JPEG", quality=90, optimize=True)
    os.replace(tmp, out)


def canonical_bundle_hash(engine_manifest_sha: str, event_library_sha: str, reels: list[dict], assets: list[dict], fingerprint: str) -> str:
    payload = {
        "engine_manifest_sha256": engine_manifest_sha,
        "event_library_sha256": event_library_sha,
        "fingerprint": fingerprint,
        "reels": sorted(reels, key=lambda x: str(x.get("profile"))),
        "assets": sorted(assets, key=lambda x: x["path"]),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_delivery_bundle(outdir: Path, expected_fingerprint: str | None = None) -> dict | None:
    review = outdir / REVIEW_DIRNAME
    manifest_path = review / "DELIVERY_MANIFEST.json"
    if not manifest_path.is_file():
        return None
    try:
        m = read_json(manifest_path)
        if m.get("candidate") != CANDIDATE or m.get("status") != "PASS":
            return None
        if expected_fingerprint and m.get("fingerprint") != expected_fingerprint:
            return None
        for a in m.get("assets", []):
            p = review / str(a.get("path", ""))
            if not p.is_file() or p.stat().st_size != int(a.get("bytes", -1)) or sha256_file(p) != a.get("sha256"):
                return None
        for r in m.get("reels", []):
            p = outdir / str(r.get("filename", ""))
            if not p.is_file() or p.stat().st_size != int(r.get("bytes", -1)) or sha256_file(p) != r.get("sha256"):
                return None
        expected = canonical_bundle_hash(
            str(m.get("engine_manifest_sha256", "")),
            str(m.get("event_library_sha256", "")),
            list(m.get("reels", [])),
            list(m.get("assets", [])),
            str(m.get("fingerprint", "")),
        )
        if expected != m.get("bundle_content_sha256"):
            return None
        return m
    except Exception:
        return None


def build_delivery_bundle(*, work: Path, outdir: Path, job_id: str, fingerprint: str, sources: list[dict], published_outputs: list[dict], engine_elapsed_s: float | None = None, ffmpeg: str = DEFAULT_FFMPEG) -> dict:
    work = Path(work).resolve()
    outdir = Path(outdir).resolve()
    engine_manifest = work / "target_auto_edit_polish" / "AUTO_EDIT_V26_MANIFEST.json"
    event_library = work / "event_library" / "EVENT_LIBRARY.json"
    if not engine_manifest.is_file():
        raise DeliveryError("ENGINE_MANIFEST_MISSING")
    if not event_library.is_file():
        raise DeliveryError("EVENT_LIBRARY_MISSING")
    eng = read_json(engine_manifest)
    lib = read_json(event_library)
    engine_manifest_sha = sha256_file(engine_manifest)
    event_library_sha = sha256_file(event_library)
    if str(eng.get("source_event_library_sha256")) != event_library_sha:
        raise DeliveryError("ENGINE_EVENT_LIBRARY_SHA_MISMATCH")
    reels = verify_reels(outdir, published_outputs)

    existing = validate_delivery_bundle(outdir, fingerprint)
    if existing and existing.get("engine_manifest_sha256") == engine_manifest_sha and existing.get("event_library_sha256") == event_library_sha:
        existing = dict(existing)
        existing["resume_status"] = "SKIPPED_EXACT_COMPLETED"
        return existing

    events = {str(e.get("event_id")): e for e in lib.get("events", []) if isinstance(e, dict)}
    selected = list(eng.get("selected_events") or [])
    if not selected:
        raise DeliveryError("ENGINE_SELECTED_EVENTS_EMPTY")

    tmp = outdir / f".{REVIEW_DIRNAME}.part.{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    (tmp / "Thumbnails").mkdir()

    selection_rows = []
    thumb_rows = []
    selected_thumb_by_event = {}
    for s in selected:
        eid = str(s.get("event_id"))
        e = events.get(eid)
        if not e:
            raise DeliveryError(f"SELECTED_EVENT_NOT_IN_LIBRARY:{eid}")
        clip = Path(str(e.get("clip_path"))).resolve()
        if not clip.is_file() or clip.stat().st_size != int(e.get("clip_bytes", -1)) or sha256_file(clip) != e.get("clip_sha256"):
            raise DeliveryError(f"EVENT_CLIP_IDENTITY_MISMATCH:{eid}")
        seq = int(s.get("sequence"))
        thumb = tmp / "Thumbnails" / f"scene_{seq:02d}.jpg"
        extract_thumb(ffmpeg, clip, float(e.get("duration_s") or 0.0), thumb)
        trim = s.get("final_trim_source_interval_s") or [s.get("source_interval_s", [0,0])[0], s.get("source_interval_s", [0,0])[1]]
        row = {
            "sequence": seq,
            "event_id": eid,
            "source_name": str(s.get("source_name")),
            "source_sha256": str(s.get("source_sha256")),
            "source_start_s": float((s.get("source_interval_s") or [0,0])[0]),
            "source_end_s": float((s.get("source_interval_s") or [0,0])[1]),
            "trim_start_s": float(trim[0]),
            "trim_end_s": float(trim[1]),
            "score": float(s.get("v22_score") or 0.0),
            "technical_prominence": float(s.get("technical_prominence") or 0.0),
            "thumb_filename": f"Thumbnails/{thumb.name}",
        }
        selection_rows.append(row)
        thumb_rows.append({
            "sequence": seq,
            "source_name": row["source_name"],
            "trim_interval": [row["trim_start_s"], row["trim_end_s"]],
            "score": row["score"],
            "thumb_path": thumb,
        })
        selected_thumb_by_event[eid] = thumb

    selection_rows.sort(key=lambda x: x["sequence"])
    thumb_rows.sort(key=lambda x: x["sequence"])

    csv_path = tmp / "SELECTIONS.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fields = ["sequence","event_id","source_name","source_sha256","source_start_s","source_end_s","trim_start_s","trim_end_s","score","technical_prominence","thumb_filename"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(selection_rows)

    contact = tmp / "CONTACT_SHEET.jpg"
    build_contact_sheet(thumb_rows, contact)

    # Candidate gallery: immutable top-ranked alternatives for human review.
    selected_ids = {r["event_id"] for r in selection_rows}
    ranked = list(eng.get("ranked_events") or [])[:CANDIDATE_LIMIT]
    candidate_rows = []
    candidate_thumb_rows = []
    (tmp / "Candidates").mkdir()
    for rank, r in enumerate(ranked, 1):
        eid = str(r.get("event_id"))
        e = events.get(eid)
        if not e:
            raise DeliveryError(f"RANKED_EVENT_NOT_IN_LIBRARY:{eid}")
        clip = Path(str(e.get("clip_path"))).resolve()
        if not clip.is_file() or clip.stat().st_size != int(e.get("clip_bytes", -1)) or sha256_file(clip) != e.get("clip_sha256"):
            raise DeliveryError(f"CANDIDATE_CLIP_IDENTITY_MISMATCH:{eid}")
        ct = tmp / "Candidates" / f"rank_{rank:02d}_{eid}.jpg"
        if eid in selected_thumb_by_event:
            shutil.copy2(selected_thumb_by_event[eid], ct)
        else:
            extract_thumb(ffmpeg, clip, float(e.get("duration_s") or 0.0), ct)
        crow = {
            "rank": rank, "event_id": eid, "source_name": str(r.get("source_name")),
            "start_s": float(r.get("start_s") or 0.0), "end_s": float(r.get("end_s") or 0.0),
            "score": float(r.get("v22_score") or 0.0), "technical_prominence": float(r.get("technical_prominence") or 0.0),
            "selected": eid in selected_ids, "thumb_filename": f"Candidates/{ct.name}",
        }
        candidate_rows.append(crow)
        candidate_thumb_rows.append({
            "sequence": rank,
            "source_name": ("[SELECTED] " if crow["selected"] else "") + crow["source_name"],
            "trim_interval": [crow["start_s"], crow["end_s"]],
            "score": crow["score"],
            "thumb_path": ct,
        })
    c_csv = tmp / "CANDIDATES.csv"
    with c_csv.open("w", newline="", encoding="utf-8") as f:
        fields = ["rank","event_id","source_name","start_s","end_s","score","technical_prominence","selected","thumb_filename"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(candidate_rows)
    candidate_sheet = tmp / "CANDIDATE_SHEET.jpg"
    build_contact_sheet(candidate_thumb_rows, candidate_sheet)
    template_lines = [
        "# MediaEngine V36 selection override template",
        "# One event_id per line, in the desired final order.",
        "# Available event IDs are listed in CANDIDATES.csv.",
        "# Use the V36 'Edit Latest Auto Edit Selection' command to copy this template into an explicit request.",
        "# The original reels are never overwritten by an override.",
        "",
    ] + [r["event_id"] for r in selection_rows] + [""]
    atomic_text(tmp / "SELECTION_OVERRIDE_TEMPLATE.txt", "\n".join(template_lines))

    # Automatic alternatives are built from the same retained event previews before Review.
    alternatives_src = outdir / "Alternatives" / "ALTERNATIVES_MANIFEST.json"
    alternatives_rows = []
    if not alternatives_src.is_file():
        raise DeliveryError("AUTO_ALTERNATIVES_MANIFEST_MISSING")
    alternatives_obj = read_json(alternatives_src)
    if alternatives_obj.get("candidate") != "MEDENG_AUTO_VARIANTS_V36_RC1" or alternatives_obj.get("status") != "PASS":
        raise DeliveryError("AUTO_ALTERNATIVES_MANIFEST_INVALID")
    for rec in alternatives_obj.get("variants") or []:
        key = str(rec.get("strategy_key") or "")
        vid = str(rec.get("variant_id") or "")
        mp = outdir / "Alternatives" / "variants" / vid / "VARIANT_MANIFEST.json"
        if not key or not vid or not mp.is_file():
            raise DeliveryError("AUTO_ALTERNATIVE_VARIANT_MISSING")
        vm = read_json(mp)
        if vm.get("status") != "PASS" or vm.get("strategy_key") != key or vm.get("variant_id") != vid:
            raise DeliveryError("AUTO_ALTERNATIVE_VARIANT_INVALID")
        outs=[]
        for o in vm.get("outputs") or []:
            p = mp.parent / str(o.get("filename") or "")
            if not p.is_file() or p.stat().st_size != int(o.get("bytes", -1)) or sha256_file(p) != o.get("sha256"):
                raise DeliveryError("AUTO_ALTERNATIVE_OUTPUT_IDENTITY_MISMATCH")
            outs.append({k:o.get(k) for k in ("profile","filename","bytes","sha256","expected_duration_s")})
        if {x.get("profile") for x in outs} != {"16x9","9x16"}:
            raise DeliveryError("AUTO_ALTERNATIVE_OUTPUT_PAIR_INCOMPLETE")
        alternatives_rows.append({
            "strategy_key": key,
            "strategy_name": str(rec.get("strategy_name") or vm.get("strategy_name") or ""),
            "variant_id": vid,
            "manifest": str(mp.resolve()),
            "selected_event_ids": [str(x) for x in rec.get("selected_event_ids") or []],
            "outputs": outs,
        })
    alt_review_obj={
        "candidate":"MEDENG_AUTO_VARIANTS_V36_RC1",
        "variant_count":len(alternatives_rows),
        "semantic_selection_claim":False,
        "variants":alternatives_rows,
    }
    atomic_json(tmp / "AUTO_ALTERNATIVES.json", alt_review_obj)
    alt_lines=[
        "MediaEngine Auto Alternatives",
        "="*40,
        f"Variants: {len(alternatives_rows)}",
        "These are automatic alternatives from retained event previews; no semantic best-moment claim is made.",
        "Original automatic/override/approved reels are not overwritten.",
        "",
    ]
    for r in alternatives_rows:
        alt_lines.append(f"{r['strategy_key']} — {r['strategy_name']} — scenes={len(r['selected_event_ids'])}")
        alt_lines.append("  events: " + ", ".join(r['selected_event_ids']))
    atomic_text(tmp / "AUTO_ALTERNATIVES.txt", "\n".join(alt_lines)+"\n")

    summary_lines = [
        "MediaEngine Auto Edit — REVIEW BUNDLE",
        "=" * 48,
        f"Job: {job_id}",
        f"Target duration: {float(eng.get('target_duration_s') or 0):.1f}s",
        f"Selected scenes: {len(selection_rows)}",
        f"Source files: {len(sources)}",
        f"Automatic alternatives: {len(alternatives_rows)}",
        f"Engine time: {float(engine_elapsed_s or 0):.1f}s",
        "Selection claim: generic aesthetic/technical AUTO_EDIT; semantic best-moment claim is NOT made.",
        "Audio: local original ambience when present; generated silence only for silent sources.",
        "External media/audio/network use: none.",
        "",
        "Selected scenes:",
    ]
    for r in selection_rows:
        summary_lines.append(f"  {r['sequence']:02d}. {r['source_name']}  {r['trim_start_s']:.2f}-{r['trim_end_s']:.2f}s  score={r['score']:.3f}")
    summary_lines += ["", "Published reels:"]
    for r in reels:
        summary_lines.append(f"  - {r['profile']}: {r['filename']}  {r['bytes']} bytes  sha256={r['sha256']}")
    summary_lines += ["", "See CONTACT_SHEET.jpg / SELECTIONS.csv for the current cut.\nSee CANDIDATE_SHEET.jpg / CANDIDATES.csv for ranked alternatives.\nSELECTION_OVERRIDE_TEMPLATE.txt is an immutable template for explicit human overrides.", ""]
    atomic_text(tmp / "SUMMARY.txt", "\n".join(summary_lines))

    provenance = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "fingerprint": fingerprint,
        "engine_manifest_sha256": engine_manifest_sha,
        "event_library_sha256": event_library_sha,
        "semantic_selection_claim": False,
        "sources": sources,
        "selected_events": selection_rows,
        "candidate_limit": CANDIDATE_LIMIT,
        "candidate_events": candidate_rows,
        "automatic_alternatives": alternatives_rows,
    }
    atomic_json(tmp / "PROVENANCE.json", provenance)

    assets = []
    for p, role in [
        (tmp / "SUMMARY.txt", "human_summary"),
        (tmp / "SELECTIONS.csv", "selection_table"),
        (tmp / "CONTACT_SHEET.jpg", "contact_sheet"),
        (tmp / "CANDIDATES.csv", "candidate_table"),
        (tmp / "CANDIDATE_SHEET.jpg", "candidate_sheet"),
        (tmp / "SELECTION_OVERRIDE_TEMPLATE.txt", "override_template"),
        (tmp / "AUTO_ALTERNATIVES.txt", "automatic_alternatives_summary"),
        (tmp / "AUTO_ALTERNATIVES.json", "automatic_alternatives_manifest"),
        (tmp / "PROVENANCE.json", "provenance"),
    ]:
        assets.append(file_record(tmp, p, role))
    for t in sorted((tmp / "Thumbnails").glob("*.jpg")):
        assets.append(file_record(tmp, t, "selected_scene_thumbnail"))
    for t in sorted((tmp / "Candidates").glob("*.jpg")):
        assets.append(file_record(tmp, t, "candidate_scene_thumbnail"))

    manifest = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "job_id": job_id,
        "fingerprint": fingerprint,
        "created_at_unix": time.time(),
        "engine_manifest_sha256": engine_manifest_sha,
        "event_library_sha256": event_library_sha,
        "semantic_selection_claim": False,
        "selected_count": len(selection_rows),
        "candidate_count": len(candidate_rows),
        "automatic_alternative_count": len(alternatives_rows),
        "source_count": len(sources),
        "reels": reels,
        "assets": assets,
    }
    manifest["bundle_content_sha256"] = canonical_bundle_hash(engine_manifest_sha, event_library_sha, reels, assets, fingerprint)
    atomic_json(tmp / "DELIVERY_MANIFEST.json", manifest)

    final = outdir / REVIEW_DIRNAME
    if final.exists():
        quarantine = outdir / "_ReviewCorrupt"
        quarantine.mkdir(exist_ok=True)
        dst = quarantine / f"Review.{int(time.time())}.{os.getpid()}"
        os.replace(final, dst)
    os.replace(tmp, final)

    checked = validate_delivery_bundle(outdir, fingerprint)
    if not checked:
        raise DeliveryError("DELIVERY_BUNDLE_POSTWRITE_VERIFY_FAILED")
    return checked


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--fingerprint", required=True)
    ap.add_argument("--job-result", required=True, help="Existing queue JOB_RESULT.json with source_files/outputs")
    ap.add_argument("--ffmpeg", default=DEFAULT_FFMPEG)
    a = ap.parse_args()
    jr = read_json(Path(a.job_result))
    result = build_delivery_bundle(
        work=Path(a.work), outdir=Path(a.outdir), job_id=a.job_id, fingerprint=a.fingerprint,
        sources=list(jr.get("source_files") or []), published_outputs=list(jr.get("outputs") or []),
        engine_elapsed_s=jr.get("engine_elapsed_s"), ffmpeg=a.ffmpeg,
    )
    print(json.dumps({"candidate":result["candidate"],"status":result["status"],"selected_count":result["selected_count"],"bundle_content_sha256":result["bundle_content_sha256"],"resume_status":result.get("resume_status")}, indent=2))

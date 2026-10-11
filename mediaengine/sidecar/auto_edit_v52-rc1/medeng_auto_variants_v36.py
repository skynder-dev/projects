#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import medeng_targeted_auto_edit_v26 as core

CANDIDATE = "MEDENG_AUTO_VARIANTS_V36_RC1"
SCHEMA_VERSION = 1
STRATEGIES = {
    "ALT_A": {
        "name": "QUALITY_ALTERNATIVE",
        "alt_bonus": 0.16,
        "repeat_penalty": 0.035,
        "auto_penalty": 0.00,
    },
    "ALT_B": {
        "name": "DIVERSITY_ALTERNATIVE",
        "alt_bonus": 0.34,
        "repeat_penalty": 0.085,
        "auto_penalty": 0.035,
    },
}

class VariantError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
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


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise VariantError(f"JSON_READ_FAILED:{path}:{type(e).__name__}:{e}") from e
    if not isinstance(obj, dict):
        raise VariantError(f"JSON_OBJECT_REQUIRED:{path}")
    return obj


def validate_output_pair(base: Path, outputs: list[dict]) -> bool:
    try:
        if {str(o.get("profile")) for o in outputs} != {"16x9", "9x16"}:
            return False
        for o in outputs:
            p = base / str(o.get("filename", ""))
            if not p.is_file() or p.stat().st_size != int(o.get("bytes", -1)):
                return False
            if sha256_file(p) != o.get("sha256"):
                return False
            core.full_decode(p)
        return True
    except Exception:
        return False


def validate_variant(render_dir: Path, *, strategy_key: str, library_sha: str, auto_sha: str, renderer_sha: str) -> dict | None:
    mp = render_dir / "VARIANT_MANIFEST.json"
    if not mp.is_file():
        return None
    try:
        m = read_json(mp)
        if m.get("candidate") != CANDIDATE or m.get("status") != "PASS":
            return None
        if m.get("strategy_key") != strategy_key:
            return None
        if m.get("event_library_sha256") != library_sha or m.get("auto_manifest_sha256") != auto_sha or m.get("renderer_sha256") != renderer_sha:
            return None
        if not validate_output_pair(render_dir, list(m.get("outputs") or [])):
            return None
        m["resume_status"] = "SKIPPED_EXACT_COMPLETED"
        return m
    except Exception:
        return None


def quarantine_invalid(path: Path, root: Path) -> Path | None:
    if not path.exists():
        return None
    qroot = root / "_CorruptVariants"
    qroot.mkdir(parents=True, exist_ok=True)
    dst = qroot / f"{path.name}.{int(time.time())}.{os.getpid()}"
    os.replace(path, dst)
    return dst


def source_counts(events: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in events:
        out[e["source_sha256"]] = out.get(e["source_sha256"], 0) + 1
    return out


def temporal_distance_bonus(candidate: dict, picked: list[dict], clip_seconds: float) -> float:
    same = [p for p in picked if p["source_sha256"] == candidate["source_sha256"]]
    if not same:
        return 0.05
    d = min(abs(float(candidate["start_s"]) - float(p["start_s"])) for p in same)
    return min(0.08, 0.08 * d / max(clip_seconds * 3.0, 1.0))


def select_variant(scored: list[dict], auto_ids: set[str], n: int, clip_seconds: float, strategy: dict, banned_sets: set[tuple[str, ...]]) -> list[dict] | None:
    if n <= 0:
        return None
    ranked = sorted(scored, key=lambda e: (-float(e["v22_score"]), e["source_name"], e["event_id"]))
    picked: list[dict] = []
    counts: dict[str, int] = {}
    while len(picked) < n:
        best = None
        best_key = None
        for e in ranked:
            if e in picked:
                continue
            # Avoid near-duplicate windows from the same source inside one variant.
            too_near = any(
                p["source_sha256"] == e["source_sha256"] and abs(float(p["start_s"]) - float(e["start_s"])) < clip_seconds * 0.75
                for p in picked
            )
            if too_near:
                continue
            src_count = counts.get(e["source_sha256"], 0)
            alt = 1.0 if e["event_id"] not in auto_ids else 0.0
            utility = (
                float(e["v22_score"])
                + float(strategy["alt_bonus"]) * alt
                - float(strategy["repeat_penalty"]) * src_count
                - float(strategy["auto_penalty"]) * (1.0 - alt)
                + temporal_distance_bonus(e, picked, clip_seconds)
            )
            key = (utility, float(e["v22_score"]), alt, -src_count, e["event_id"])
            if best_key is None or key > best_key:
                best_key = key
                best = e
        if best is None:
            break
        picked.append(best)
        counts[best["source_sha256"]] = counts.get(best["source_sha256"], 0) + 1
    if len(picked) != n:
        return None
    chosen = tuple(sorted(e["event_id"] for e in picked))
    if chosen in banned_sets:
        # Deterministic one-swap search to avoid duplicate variant sets.
        base = list(picked)
        alternatives = [e for e in ranked if e["event_id"] not in {x["event_id"] for x in base}]
        for idx in range(len(base) - 1, -1, -1):
            for alt in alternatives:
                trial = base[:idx] + [alt] + base[idx+1:]
                if len({x["event_id"] for x in trial}) != n:
                    continue
                near = False
                for i, a in enumerate(trial):
                    for b in trial[i+1:]:
                        if a["source_sha256"] == b["source_sha256"] and abs(float(a["start_s"]) - float(b["start_s"])) < clip_seconds * 0.75:
                            near = True
                if near:
                    continue
                tset = tuple(sorted(x["event_id"] for x in trial))
                if tset not in banned_sets:
                    picked = trial
                    chosen = tset
                    break
            else:
                continue
            break
        if chosen in banned_sets:
            return None
    # Keep MediaEngine's existing continuity ordering after set selection.
    return core.order_continuity(picked)


def render_variant(*, strategy_key: str, strategy: dict, selected: list[dict], alternatives_root: Path, library_sha: str, auto_sha: str, renderer_sha: str, clip_seconds: float, transition: float, audio_lufs: float, audio_true_peak_db: float, vertical_framing: str, vertical_focus_x: float, output_resolution: str, audio_content: str, output_fps: int, video_quality: str) -> dict:
    selection_material = "|".join(e["event_id"] for e in selected)
    variant_id = f"{strategy_key.lower()}-{hashlib.sha256(selection_material.encode()).hexdigest()[:12]}"
    render_dir = alternatives_root / "variants" / variant_id
    resumed = validate_variant(render_dir, strategy_key=strategy_key, library_sha=library_sha, auto_sha=auto_sha, renderer_sha=renderer_sha)
    if resumed:
        return resumed
    if render_dir.exists():
        quarantine_invalid(render_dir, alternatives_root)
    renders_root = alternatives_root / "variants"
    renders_root.mkdir(parents=True, exist_ok=True)
    tmp = renders_root / f".{variant_id}.tmp.{os.getpid()}.{int(time.time()*1000)}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        selected_rows = []
        for i, e in enumerate(selected, 1):
            d = core.used_duration(e, clip_seconds)
            off = max(0.0, (float(e["duration_s"]) - d) / 2.0)
            selected_rows.append({
                "sequence": i,
                "event_id": e["event_id"],
                "source_name": e["source_name"],
                "source_sha256": e["source_sha256"],
                "source_interval_s": [float(e["start_s"]), float(e["end_s"])],
                "final_trim_source_interval_s": [round(float(e["start_s"]) + off, 3), round(float(e["start_s"]) + off + d, 3)],
                "score": float(e["v22_score"]),
                "technical_prominence": float(e["technical_prominence"]),
            })
        outputs = []
        for profile in ("16x9", "9x16"):
            segs = []
            metas = []
            for i, e in enumerate(selected, 1):
                p = tmp / "work" / profile / f"{i:02d}_{e['event_id']}.mp4"
                meta = core.make_segment(e, p, profile, clip_seconds, audio_lufs, audio_true_peak_db, vertical_framing, vertical_focus_x, output_resolution, audio_content, output_fps, video_quality)
                segs.append(p)
                metas.append(meta)
            final = tmp / f"variant_{strategy_key.lower()}_{profile}.mp4"
            expected = core.concat(segs, [m["duration_s"] for m in metas], final, transition, video_quality)
            probe = core.ffprobe(final)
            core.full_decode(final)
            outputs.append({
                "profile": profile,
                "filename": final.name,
                "bytes": final.stat().st_size,
                "sha256": sha256_file(final),
                "expected_duration_s": round(expected, 3),
                "probe": probe,
            })
        manifest = {
            "candidate": CANDIDATE,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "variant_id": variant_id,
            "strategy_key": strategy_key,
            "strategy_name": strategy["name"],
            "automatic_alternative": True,
            "semantic_selection_claim": False,
            "selection_mode": "AUTO_ALTERNATIVE_FROM_RETAINED_EVENT_PREVIEWS",
            "event_library_sha256": library_sha,
            "auto_manifest_sha256": auto_sha,
            "renderer_sha256": renderer_sha,
            "clip_seconds": clip_seconds,
            "transition_seconds": transition,
            "audio_lufs": audio_lufs,
            "audio_true_peak_db": audio_true_peak_db,
            "audio_policy": ("LOCAL_SOURCE_LOUDNORM_TARGET_V43" if audio_content=="source" else "MUTED_SILENT_AAC_V47"),
            **({"vertical_framing": vertical_framing} if vertical_framing != "fill" else {}),
            **({"vertical_focus_x": vertical_focus_x} if abs(float(vertical_focus_x)-0.5)>1e-9 else {}),
            **({"output_resolution": output_resolution} if str(output_resolution)!="standard" else {}),
            **({"output_fps": int(output_fps)} if int(output_fps)!=30 else {}),
            **({"video_quality": video_quality} if str(video_quality)!="standard" else {}),
            **({"audio_content": audio_content} if str(audio_content)!="source" else {}),
            "selected_events": selected_rows,
            "outputs": outputs,
            "atomic_publish": True,
            "completed_at_unix": time.time(),
        }
        atomic_json(tmp / "VARIANT_MANIFEST.json", manifest)
        lines = [
            f"MediaEngine Auto Alternative {strategy_key}",
            "=" * 44,
            f"Strategy: {strategy['name']}",
            f"Scenes: {len(selected_rows)}",
            "Semantic best-moment claim: NO",
            "Original auto/override/approved files overwritten: NO",
            "",
        ]
        for row in selected_rows:
            a, b = row["final_trim_source_interval_s"]
            lines.append(f"  {row['sequence']:02d}. {row['source_name']}  {a:.2f}-{b:.2f}s  event={row['event_id']}")
        atomic_text(tmp / "VARIANT_RESULT.txt", "\n".join(lines) + "\n")
        complete = validate_variant(tmp, strategy_key=strategy_key, library_sha=library_sha, auto_sha=auto_sha, renderer_sha=renderer_sha)
        if not complete:
            raise VariantError("ATOMIC_TEMP_VALIDATION_FAILED")
        if render_dir.exists():
            exact = validate_variant(render_dir, strategy_key=strategy_key, library_sha=library_sha, auto_sha=auto_sha, renderer_sha=renderer_sha)
            if exact:
                shutil.rmtree(tmp, ignore_errors=True)
                return exact
            quarantine_invalid(render_dir, alternatives_root)
        os.replace(tmp, render_dir)
        return manifest
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def build(work: Path, outdir: Path, max_variants: int = 2) -> dict:
    work = work.resolve(); outdir = outdir.resolve()
    lib_path = work / "event_library" / "EVENT_LIBRARY.json"
    edit_dir = work / "target_auto_edit_polish"
    auto_path = edit_dir / "AUTO_EDIT_V26_MANIFEST.json"
    score_cache = edit_dir / "V22_SCORE_CACHE.json"
    if not lib_path.is_file() or not auto_path.is_file():
        raise VariantError("RETAINED_WORK_EVIDENCE_MISSING")
    auto = read_json(auto_path)
    _, events = core.load_library(lib_path)
    scored = core.score_events(events, score_cache)
    by_id = {e["event_id"]: e for e in scored}
    auto_ids_list = [str(r.get("event_id")) for r in auto.get("selected_events") or []]
    auto_ids = {x for x in auto_ids_list if x in by_id}
    n = len(auto_ids_list)
    if n <= 0:
        raise VariantError("AUTO_SELECTION_EMPTY")
    library_sha = sha256_file(lib_path)
    auto_sha = sha256_file(auto_path)
    renderer_sha = sha256_file(Path(core.__file__).resolve())
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
    alternatives_root = outdir / "Alternatives"
    banned = {tuple(sorted(auto_ids))}
    variants = []
    for strategy_key in ("ALT_A", "ALT_B")[:max(0, max_variants)]:
        selected = select_variant(scored, auto_ids, n, clip_seconds, STRATEGIES[strategy_key], banned)
        if not selected:
            continue
        keyset = tuple(sorted(e["event_id"] for e in selected))
        banned.add(keyset)
        m = render_variant(
            strategy_key=strategy_key,
            strategy=STRATEGIES[strategy_key],
            selected=selected,
            alternatives_root=alternatives_root,
            library_sha=library_sha,
            auto_sha=auto_sha,
            renderer_sha=renderer_sha,
            clip_seconds=clip_seconds,
            transition=transition,
            audio_lufs=audio_lufs,
            audio_true_peak_db=audio_true_peak_db,
            vertical_framing=vertical_framing,
            vertical_focus_x=vertical_focus_x,
            output_resolution=output_resolution,
            audio_content=audio_content,
            output_fps=output_fps,
            video_quality=video_quality,
        )
        variants.append(m)
    summary = {
        "candidate": CANDIDATE,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "semantic_selection_claim": False,
        "auto_selected_event_ids": auto_ids_list,
        "variant_count": len(variants),
        "variants": [
            {
                "strategy_key": m["strategy_key"],
                "strategy_name": m["strategy_name"],
                "variant_id": m["variant_id"],
                "manifest": str((alternatives_root / "variants" / m["variant_id"] / "VARIANT_MANIFEST.json").resolve()),
                "selected_event_ids": [r["event_id"] for r in m["selected_events"]],
                "outputs": [{k:o[k] for k in ("profile", "filename", "bytes", "sha256", "expected_duration_s")} for o in m["outputs"]],
                "resume_status": m.get("resume_status"),
            }
            for m in variants
        ],
        "insufficient_alternatives_is_error": False,
        "completed_at_unix": time.time(),
    }
    atomic_json(alternatives_root / "ALTERNATIVES_MANIFEST.json", summary)
    if variants:
        atomic_json(alternatives_root / "LATEST_ALTERNATIVES.json", {
            "candidate": CANDIDATE,
            "variants": [{"strategy_key": v["strategy_key"], "variant_id": v["variant_id"], "manifest": str((alternatives_root/'variants'/v['variant_id']/'VARIANT_MANIFEST.json').resolve())} for v in variants],
            "updated_at_unix": time.time(),
        })
    return summary



def validate_public_alternatives(outdir: Path) -> dict | None:
    try:
        outdir=Path(outdir).resolve(); root=outdir/'Alternatives'; sp=root/'ALTERNATIVES_MANIFEST.json'
        if not sp.is_file(): return None
        summary=read_json(sp)
        if summary.get('candidate')!=CANDIDATE or summary.get('status')!='PASS': return None
        variants=list(summary.get('variants') or [])
        if int(summary.get('variant_count',-1))!=len(variants): return None
        for rec in variants:
            key=str(rec.get('strategy_key') or ''); vid=str(rec.get('variant_id') or '')
            if key not in STRATEGIES or not vid: return None
            mp=root/'variants'/vid/'VARIANT_MANIFEST.json'
            if not mp.is_file(): return None
            m=read_json(mp)
            if m.get('candidate')!=CANDIDATE or m.get('status')!='PASS' or m.get('strategy_key')!=key or m.get('variant_id')!=vid: return None
            if not validate_output_pair(mp.parent,list(m.get('outputs') or [])): return None
        return summary
    except Exception:
        return None

def validate_alternatives(work: Path, outdir: Path) -> dict | None:
    try:
        work = Path(work).resolve(); outdir = Path(outdir).resolve()
        lib_path = work / "event_library" / "EVENT_LIBRARY.json"
        auto_path = work / "target_auto_edit_polish" / "AUTO_EDIT_V26_MANIFEST.json"
        if not lib_path.is_file() or not auto_path.is_file():
            return None
        library_sha = sha256_file(lib_path); auto_sha = sha256_file(auto_path); renderer_sha = sha256_file(Path(core.__file__).resolve())
        root = outdir / "Alternatives"
        sp = root / "ALTERNATIVES_MANIFEST.json"
        if not sp.is_file():
            return None
        summary = read_json(sp)
        if summary.get("candidate") != CANDIDATE or summary.get("status") != "PASS":
            return None
        variants = list(summary.get("variants") or [])
        if int(summary.get("variant_count", -1)) != len(variants):
            return None
        for rec in variants:
            key = str(rec.get("strategy_key") or "")
            vid = str(rec.get("variant_id") or "")
            if key not in STRATEGIES or not vid:
                return None
            render_dir = root / "variants" / vid
            m = validate_variant(render_dir, strategy_key=key, library_sha=library_sha, auto_sha=auto_sha, renderer_sha=renderer_sha)
            if not m:
                return None
            expected_ids = [str(x) for x in rec.get("selected_event_ids") or []]
            actual_ids = [str(x.get("event_id")) for x in m.get("selected_events") or []]
            if expected_ids != actual_ids:
                return None
        return summary
    except Exception:
        return None

def main() -> None:
    ap = argparse.ArgumentParser(description="Build automatic alternative cuts from retained MediaEngine event previews without rediscovery.")
    ap.add_argument("--work", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--max-variants", type=int, default=2)
    a = ap.parse_args()
    result = build(Path(a.work), Path(a.outdir), a.max_variants)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

"""End-to-end run: live topic -> claims -> script -> voice -> video -> verification -> hashed package."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path

from . import grants
from .claims import audience_score, build_claims, validate_script
from .common import (CONTRACT, PACKAGE_SCHEMA, PipelineError, ROOT, human_date, parse_date, read_json,
                     sha256_file, slug, utc_now, write_json, write_text)
from .render import build_audio, render_video
from .verify import verify_video
from .voice import make_voice, speech_text, wav_duration
from .writer import write_script


# ------------------------------------------------------------------ topic selection

def score_record(rec: dict, today: dt.date, min_days: int) -> tuple[int, list[str]]:
    why = []
    if (rec.get("status") or "").lower() != "posted":
        return -99, ["not posted"]
    cd = parse_date(rec.get("close_date"))
    if not cd:
        return -99, ["no parseable close date"]
    days = (cd - today).days
    if days < min_days:
        return -99, [f"closes in {days} days (< {min_days})"]
    hi, tot = rec.get("award_ceiling"), rec.get("estimated_total_program_funding")
    if not (hi or tot):
        return -99, ["no award amount or total funding listed"]
    s = 0
    s += 3 if hi else 0; why.append("award ceiling" if hi else "no ceiling")
    s += 2 if tot else 0
    s += 1 if rec.get("award_floor") else 0
    s += 2 if rec.get("expected_number_of_awards") else 0
    a = audience_score(rec)
    s += min(a, 3) * 2; why.append(f"audience breadth {a}")
    if all((x or "").lower().startswith("others") for x in rec.get("applicant_types") or ["others"]):
        s -= 2; why.append("restricted applicant type")
    s += 2 if 14 <= days <= 75 else (1 if days <= 120 else 0); why.append(f"{days} days left")
    s += 1 if len(rec.get("description") or "") > 150 else 0
    s += 1 if (tot or 0) >= 5_000_000 else 0
    return s, why


def discover_live(cfg: dict, src_dir: Path, today: dt.date, seen: set, forced: str | None):
    client = grants.GrantsGovClient(src_dir)
    hits = {}
    sc = cfg["search"]
    if forced:
        hits[forced] = {"id": forced}
    else:
        for kw in sc["keywords"]:
            hs, _ = client.search(kw, int(sc.get("rows", 25)), sc.get("statuses", "posted"))
            for h in hs:
                hid = str(h.get("id") or "")
                if hid and hid not in hits:
                    hits[hid] = h
    # pre-filter on search-hit fields before spending detail calls
    pre = []
    for hid, h in hits.items():
        if hid in seen and not forced:
            continue
        cd = parse_date(h.get("closeDate"))
        if not forced and (not cd or (cd - today).days < int(cfg["selection"]["min_days_left"])):
            continue
        pre.append(h)
    pre.sort(key=lambda h: (parse_date(h.get("closeDate")) or dt.date.max))
    recs, considered = [], []
    for h in pre[: int(sc.get("max_detail_fetch", 14))]:
        det, meta = client.detail(str(h["id"]))
        rec = grants.normalize(h, det)
        s, why = score_record(rec, today, int(cfg["selection"]["min_days_left"]))
        recs.append((s, rec, meta))
        considered.append({"opportunity_id": rec["opportunity_id"], "title": rec["title"], "score": s, "why": why})
    return recs, considered, client.calls, len(hits)


def discover_fixture(path: Path, today: dt.date, cfg: dict, seen: set, forced: str | None):
    rows = read_json(path)
    fsha = sha256_file(path)
    recs, considered = [], []
    for row in rows:
        rec = grants.from_fixture(row)
        if forced and rec["opportunity_id"] != forced:
            continue
        if rec["opportunity_id"] in seen and not forced:
            continue
        s, why = score_record(rec, today, int(cfg["selection"]["min_days_left"]))
        meta = {"file": f"fixture:{path.name}", "sha256": fsha, "url": rec["source_url"],
                "note": "Supabase export of a 2026-10-03 live Grants.gov fetch (fixture mode, not live)"}
        recs.append((s, rec, meta))
        considered.append({"opportunity_id": rec["opportunity_id"], "title": rec["title"], "score": s, "why": why})
    return recs, considered, [{"file": f"fixture:{path.name}", "sha256": fsha}], len(rows)


# ------------------------------------------------------------------ main run

def run(cfg: dict, out_root: Path, fixture: Path | None = None, opportunity: str | None = None,
        history_path: Path | None = None) -> Path:
    now = utc_now()
    today = now.date()
    history = read_json(history_path) if history_path and history_path.exists() else {"runs": []}
    seen = {r["opportunity_id"] for r in history.get("runs", [])}
    tmp = out_root / f"_incomplete_{now.strftime('%Y%m%dT%H%M%S')}"
    if tmp.exists():
        shutil.rmtree(tmp)
    src_dir = tmp / "source"
    src_dir.mkdir(parents=True)
    log = {"started_at": now.isoformat(), "mode": "fixture" if fixture else "live", "notes": []}

    # 1. topic
    if fixture:
        recs, considered, calls, n_hits = discover_fixture(fixture, today, cfg, seen, opportunity)
    else:
        recs, considered, calls, n_hits = discover_live(cfg, src_dir, today, seen, opportunity)
    good = sorted([r for r in recs if r[0] > -99], key=lambda r: -r[0])
    if not good:
        write_json(tmp / "topic.json", {"error": "no eligible topic", "considered": considered})
        raise PipelineError(f"no eligible topic among {len(recs)} detailed / {n_hits} found")
    score, rec, snap = good[0]
    run_id = f"{now.strftime('%Y%m%d')}_{rec['opportunity_id']}_{slug(rec['title'], 32)}"
    write_json(tmp / "sources.json", {"mode": log["mode"], "api_calls": calls, "selected_snapshot": snap,
                                      "public_url": rec["source_url"]})
    write_json(tmp / "topic.json", {"run_id": run_id, "selected": {k: v for k, v in rec.items()},
                                     "score": score, "found": n_hits, "considered": considered,
                                     "excluded_previously_used": sorted(seen), "selected_at": now.isoformat()})

    # 2. claims
    claims = build_claims(rec, snap, today)
    for c in claims:
        c["observed_at"] = snap.get("fetched_at") or log["started_at"]
    write_json(tmp / "claims.json", {"contract": CONTRACT, "opportunity_id": rec["opportunity_id"],
                                      "built_from": snap, "claims": claims,
                                      "rule": "claims are copied from official fields only; writers can cite, never add"})

    # 3. script
    script, wreport = write_script(rec, claims, cfg)
    errs = validate_script(script, claims)
    if errs:
        raise PipelineError("script failed grounding: " + "; ".join(errs))
    write_json(tmp / "script.json", script)
    write_text(tmp / "script.md", script_md(script, claims, rec))
    log["writer"] = wreport

    # 4. voice
    cache = Path(os.environ.get("SOCIAL_VOICE_CACHE", Path.home() / ".cache" / "socialreel" / "voices"))
    voice, vnotes = make_voice(cfg["voice"], cache)
    log["notes"] += vnotes
    adir = tmp / "audio"
    adir.mkdir()
    wavs, speech = [], []
    for i, seg in enumerate(script["segments"], 1):
        st = speech_text(seg["voiceover"])
        p = adir / f"segment_{i:02d}.wav"
        voice.synth(st, p)
        if wav_duration(p) < 0.4:
            raise PipelineError(f"TTS produced no speech for segment {i}")
        wavs.append(p)
        speech.append(st)
    write_text(tmp / "voice.txt", "\n\n".join(f"[{s['id']}] {t}" for s, t in zip(script["segments"], speech)) + "\n")
    narration = adir / "narration.wav"
    durs = build_audio(wavs, narration)
    t, timing = 0.0, []
    for i, (seg, d) in enumerate(zip(script["segments"], durs), 1):
        timing.append({"id": seg["id"], "role": seg["role"], "start_s": round(t, 3), "end_s": round(t + d, 3),
                       "speech_s": round(wav_duration(wavs[i - 1]), 3), "audio": f"audio/segment_{i:02d}.wav"})
        t += d
    write_json(tmp / "timing.json", {"fps": 30, "total_s": round(t, 3), "segments": timing,
                                      "rule": "timing is measured from the synthesized audio, not guessed"})

    # 5. visuals + render
    footer = (f"Source: Grants.gov listing {rec['opportunity_id']}\n"
              f"Data as of {human_date(today)} · verify before applying")
    write_json(tmp / "visual_plan.json", {"canvas": "1080x1920@30", "footer": footer, "segments": [
        {"id": s["id"], "visual": s["visual"], "on_screen": s.get("on_screen", {}),
         "still": f"mediaengine_handoff/stills/segment_{i:02d}.png", "claim_keys": s["claim_keys"]}
        for i, s in enumerate(script["segments"], 1)]})
    me = tmp / "mediaengine_handoff"
    final = tmp / "final"
    final.mkdir()
    mp4 = final / "reel.mp4"
    rinfo = render_video(script["segments"], durs, narration, mp4, footer, me / "stills")
    for i, w in enumerate(wavs, 1):
        (me / "audio").mkdir(parents=True, exist_ok=True)
        shutil.copy2(w, me / "audio" / w.name)
    shutil.copy2(narration, me / "audio" / "narration.wav")
    write_json(me / "timeline.json", {"preset": "social_hd", "width": 1080, "height": 1920, "fps": 30,
                                       "target_seconds": round(t, 3), "audio": "audio/narration.wav",
                                       "clips": [{"still": f"stills/segment_{i:02d}.png", "start_s": x["start_s"],
                                                  "end_s": x["end_s"], "voice": x["audio"]}
                                                 for i, x in enumerate(timing, 1)]})
    write_text(me / "README.md", MEDIAENGINE_README)

    # 6. verification of the actual file
    mids = [(x["start_s"] + x["end_s"]) / 2 for x in timing]
    ver = verify_video(mp4, t, tmp / "review", mids)
    if voice.test_only:
        ver["checks"].append({"check": "real_voice", "pass": False, "detail": "silent_test voice is test-only"})
        ver["pass"] = False
    if log["mode"] != "live":
        ver["checks"].append({"check": "live_source", "pass": False, "detail": "fixture mode: not a live topic"})
        ver["pass"] = False

    # 7. manifests
    media_files = sorted([p for p in (tmp / "audio").glob("*.wav")] + list((me / "stills").glob("*.png")) + [mp4])
    write_json(tmp / "media_manifest.json", {"files": [_fe(tmp, p) for p in media_files], "render": rinfo,
                                              "voice": voice.identity()})
    pkg_files = ["sources.json", "topic.json", "claims.json", "script.json", "script.md", "timing.json",
                 "voice.txt", "visual_plan.json", "media_manifest.json"]
    pkg_files += sorted(str(p.relative_to(tmp)) for p in src_dir.glob("*.json"))
    pkg_files += sorted(str(p.relative_to(tmp)) for p in me.rglob("*") if p.is_file())
    entries = [_fe(tmp, tmp / f) for f in pkg_files]
    from .common import sha256_bytes
    package_id = sha256_bytes("\n".join(f"{e['path']} {e['sha256']}" for e in entries).encode())
    video_sha = sha256_file(mp4)
    lineage = {"source_snapshot": snap, "claims_sha256": sha256_file(tmp / "claims.json"),
               "script_sha256": sha256_file(tmp / "script.json"), "timing_sha256": sha256_file(tmp / "timing.json"),
               "narration_sha256": sha256_file(narration), "package_id": package_id, "video_sha256": video_sha}
    write_json(tmp / "package_manifest.json", {"schema": PACKAGE_SCHEMA, "contract": CONTRACT, "run_id": run_id,
                                                "package_id": package_id, "files": entries, "lineage": lineage})
    result = {"run_id": run_id, "contract": CONTRACT, "mode": log["mode"], "accepted": ver["pass"],
              "package_id": package_id, "video": {"path": "final/reel.mp4", "sha256": video_sha,
                                                  "bytes": mp4.stat().st_size},
              "verification": ver, "writer": wreport.get("used"), "voice": voice.identity(), "log": log,
              "finished_at": utc_now().isoformat()}
    write_json(tmp / "result.json", result)
    write_text(tmp / "REVIEW.md", review_md(result, rec, script, claims, timing))
    dest = out_root / run_id
    if dest.exists():
        shutil.rmtree(dest)
    tmp.rename(dest)
    if history_path and result["accepted"]:
        history.setdefault("runs", []).append({"run_id": run_id, "opportunity_id": rec["opportunity_id"],
                                               "date": today.isoformat(), "package_id": package_id,
                                               "video_sha256": video_sha, "writer": result["writer"]})
        write_json(history_path, history)
    return dest


def _fe(root: Path, p: Path) -> dict:
    return {"path": str(p.relative_to(root)), "sha256": sha256_file(p), "bytes": p.stat().st_size}


def script_md(script, claims, rec) -> str:
    by = {c["key"]: c for c in claims}
    out = [f"# {script['title']}", "", f"Writer: `{script['writer']}` · Opportunity {rec.get('number')} · {rec['source_url']}", ""]
    for s in script["segments"]:
        out.append(f"## {s['id']} · {s['role']} · visual `{s['visual']}`")
        out.append(f"**Voiceover:** {s['voiceover']}")
        scr = s.get("on_screen") or {}
        out.append("**On screen:** " + " | ".join(f"{k}: {v}" for k, v in scr.items() if v).replace("\n", " / "))
        out.append("**Claims:** " + "; ".join(f"`{k}` — {by[k]['statement']}" for k in s["claim_keys"] if k in by))
        out.append("")
    out += ["## Description", "", script.get("description", ""), "", "## Source note", "", script.get("source_note", "")]
    return "\n".join(out) + "\n"


def review_md(result, rec, script, claims, timing) -> str:
    v = result["verification"]
    lines = [f"# Reel review — {rec['title']}", "",
             f"- Accepted: **{'YES' if result['accepted'] else 'NO'}** (mode: {result['mode']})",
             f"- Video: `final/reel.mp4` — {v.get('duration_s')} s, sha256 `{result['video']['sha256']}`",
             f"- Package id: `{result['package_id']}`",
             f"- Writer: `{result['writer']}` · Voice: `{result['voice'].get('backend')}` {result['voice'].get('voice', '')}",
             f"- Source: {rec['source_url']} (opportunity {rec.get('number')})", "",
             "## Checks", ""]
    lines += [f"- {'PASS' if c['pass'] else 'FAIL'} `{c['check']}` — {c['detail']}" for c in v["checks"]]
    lines += ["", "## Script with claim lineage", ""]
    by = {c["key"]: c for c in claims}
    for s, tm in zip(script["segments"], timing):
        lines.append(f"**{tm['start_s']:.1f}–{tm['end_s']:.1f}s · {s['role']}** — {s['voiceover']}")
        for k in s["claim_keys"]:
            lines.append(f"  - `{k}`: {by[k]['statement']} ({', '.join(by[k]['source']['fields'])})")
    lines += ["", "Nothing was published. Review frames: `review/contact_sheet.jpg`."]
    return "\n".join(lines) + "\n"


MEDIAENGINE_README = """# MediaEngine handoff

Social already rendered `final/reel.mp4` with its built-in renderer. This folder carries the same
package in a renderer-neutral form so MediaEngine (Social HD preset, 1080x1920) can re-render it:

- `stills/segment_NN.png` — final composed frame for each segment (1080x1920)
- `audio/segment_NN.wav` — narration per segment; `audio/narration.wav` — full track with pauses
- `timeline.json` — start/end of every clip in seconds (measured from the audio)

Exact package identity: see `../package_manifest.json` (SHA-256 of every file, including these).
"""


def rebuild(run_dir: Path) -> dict:
    """Re-render the video from the stored package and compare hashes (repeatability proof)."""
    script = read_json(run_dir / "script.json")
    timing = read_json(run_dir / "timing.json")
    vp = read_json(run_dir / "visual_plan.json")
    durs = [x["end_s"] - x["start_s"] for x in timing["segments"]]
    out = run_dir / "_rebuild"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    render_video(script["segments"], durs, run_dir / "audio" / "narration.wav", out / "reel.mp4", vp["footer"], out / "stills")
    a, b = sha256_file(run_dir / "final" / "reel.mp4"), sha256_file(out / "reel.mp4")
    stills_same = all(sha256_file(p) == sha256_file(run_dir / "mediaengine_handoff" / "stills" / p.name)
                      for p in (out / "stills").glob("*.png"))
    res = {"original_sha256": a, "rebuild_sha256": b, "byte_identical": a == b, "stills_identical": stills_same}
    shutil.rmtree(out)
    return res

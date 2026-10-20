"""End-to-end run: live topic -> claims -> script -> voice -> video -> verification -> hashed package."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from . import grants
from .claims import audience_score, build_claims, validate_script
from .common import (CONTRACT, PACKAGE_SCHEMA, PipelineError, ROOT, human_date, parse_date, read_json,
                     sha256_file, slug, utc_now, write_json, write_text, progress, check_cancel)
from .render import build_audio, render_video
from .verify import verify_video
from .voice import make_voice, speech_text, wav_duration, speech_for_script
from .writer import write_script


# ------------------------------------------------------------------ topic selection

def family(title: str) -> str:
    """Same program in another region / fiscal year counts as the same topic."""
    t = re.sub(r"\([A-Z0-9&/-]{2,12}\)", " ", title or "").lower()   # drop acronyms like (SBTTAC)
    t = re.sub(r"\((?:region|area|zone)?\s*[\divx]+\)|\b(?:region|area|zone)\s*[\divx]+\b", " ", t)
    t = re.sub(r"\bfy\s*\d{2,4}\b|\bfiscal year\b|\(\d{4}\)|\b(19|20)\d{2}\b", " ", t)
    return " ".join(re.findall(r"[a-z]+", t))


def score_record(rec: dict, today: dt.date, min_days: int) -> tuple[int, list[str]]:
    why = []
    if rec.get("public_money_source"):
        data=rec["public_money_source"]
        if data.get("status") not in {"information_available","national_information_available"}:return -99,["Public information status not established"]
        if not rec.get("editorial_brief"):return -99,["No audience-ready source brief"]
        return 10,["Public information, not a grant; no invented balance or calendar deadline"]
    if (rec.get("status") or "").lower() != "posted":
        return -99, ["not posted"]
    opening = parse_date(rec.get("open_date"))
    if opening and opening > today:
        return -99, ["future posting/opening date"]
    if (rec.get("doc_type") or "").lower() == "forecast":
        return -99, ["forecast is not a posted application opportunity"]
    cd = parse_date(rec.get("close_date"))
    if not cd:
        return -99, ["no parseable close date"]
    days = (cd - today).days
    if days < min_days:
        return -99, [f"closes in {days} days (< {min_days})"]
    import math
    for field in ('award_floor','award_ceiling','estimated_total_program_funding','expected_number_of_awards'):
        value=rec.get(field)
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value < 0):
            return -99, ['invalid numeric source field: '+field]
    if rec.get('award_floor') and rec.get('award_ceiling') and rec['award_floor'] > rec['award_ceiling']:
        return -99, ['award floor exceeds ceiling']
    count=rec.get('expected_number_of_awards')
    if count is not None and count != int(count):
        return -99, ['noninteger expected award count']
    audience=assess_audience(rec)
    if audience['explicit_foreign_only']:
        return -99, ['explicit foreign-only applicant restriction; unsuitable for default US audience']
    hi, tot = rec.get("award_ceiling"), rec.get("estimated_total_program_funding")
    if not (hi or tot):
        why.append("No listing amount: retain for source review; no payout inferred")
    s = 0
    s += 3 if hi else 0; why.append("award ceiling" if hi else "no ceiling")
    s += 2 if tot else 0
    s += 1 if rec.get("award_floor") else 0
    s += 2 if rec.get("expected_number_of_awards") else 0
    a = audience_score(rec)
    s += min(a, 3) * 2; why.append(f"listed applicant category breadth {a}; individual eligibility unverified")
    if all((x or "").lower().startswith("others") for x in rec.get("applicant_types") or ["others"]):
        s -= 2; why.append("restricted applicant type")
    s += 2 if 14 <= days <= 75 else (1 if days <= 120 else 0); why.append(f"{days} days left")
    s += 1 if len(rec.get("description") or "") > 150 else 0
    return s, why


def discover_live(cfg: dict, src_dir: Path, today: dt.date, seen: set, forced: str | None, history_path=None):
    if cfg["search"].get("pagination") is True and not forced:
        from .discovery_cursor import discover
        return discover(cfg,src_dir,today,seen,forced,history_path or src_dir.parent/"history.json")
    client = grants.GrantsGovClient(src_dir,history_path=history_path)
    hits = {}
    sc = cfg["search"]
    hit_sources = {}
    queries = list(sc["keywords"]) + ([""] if sc.get("catalog_sample") is True else [])
    for kw in dict.fromkeys(queries):
        hs, search_meta = client.search(kw, int(sc.get("rows", 25)), sc.get("statuses", "posted"))
        for h in hs:
            hid = str(h.get("id") or "")
            if hid and hid not in hits and (not forced or hid == str(forced)):
                hits[hid] = h
                hit_sources[hid] = search_meta
    if forced and str(forced) not in hits:
        raise PipelineError('Selected opportunity absent from current posted discovery; status is not assumed')
    # pre-filter on search-hit fields before spending detail calls
    pre = []
    for hid, h in hits.items():
        if not forced and (hid in seen or family(h.get("title", "")) in seen):
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
        rec['_selection_min_days']=int(cfg['selection']['min_days_left'])
        rec['audience_assessment'] = assess_audience(rec)
        rec['selection_assessment'] = candidate_facets(rec,today,sc['keywords'],int(cfg['selection']['min_days_left']))
        rec['_field_sources'] = {key: (hit_sources[str(h['id'])] if field.startswith('hit.') else meta)
                                 for key, field in rec['fields'].items()}
        s, why = score_record(rec, today, int(cfg["selection"]["min_days_left"]))
        from .editorial import ranking_evidence
        rank = ranking_evidence(rec, s, why, meta,audience=cfg.get('selection',{}).get('audience','general_us'),as_of=today)
        rec["ranking_evidence"] = rank
        s = rank["score"]
        recs.append((s, rec, meta))
        considered.append({"opportunity_id": rec["opportunity_id"], "title": rec["title"], "score": s, "why": why, "ranking": rank, "facets": rec.get("selection_assessment")})
    return recs, considered, client.calls, len(hits)


def discover_fixture(path: Path, today: dt.date, cfg: dict, seen: set, forced: str | None):
    rows = read_json(path)
    public_fixture=isinstance(rows,dict) and rows.get("schema")=="SOCIAL_SOURCE_CONTENT_FIXTURE_V1"
    if public_fixture:rows=rows.get("records")
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise PipelineError("Source fixture needs1..100 records")
    if public_fixture and len(rows)>3:raise PipelineError("Public content fixture supports at most3 official pages")
    fsha = sha256_file(path)
    recs, considered = [], []
    for row in rows:
        if public_fixture:
            if not isinstance(row,dict) or not isinstance(row.get("public_money_content"),dict) or row["public_money_content"].get("reconstructed") is not True:
                raise PipelineError("Public content fixtures must contain explicitly reconstructed content; no self-declared live record")
            row={"source_url":row.get("source_url"),"public_money_content":row["public_money_content"]}
            from .source_brief import adapt
            rec=adapt(row,audience=cfg.get("selection",{}).get("audience","general_us"))
            if not rec.get("public_money_source"):raise PipelineError("Public-content fixture did not yield a supported source")
        else:rec = grants.from_fixture(row)
        if forced and rec["opportunity_id"] != forced:
            continue
        if not forced and (rec["opportunity_id"] in seen or family(rec["title"]) in seen):
            continue
        rec["selection_assessment"] = {"source_kind":"public_information","audience_requires_separate_gate":True} if public_fixture else candidate_facets(rec,today,cfg["search"]["keywords"],int(cfg["selection"]["min_days_left"]))
        s, why = score_record(rec, today, int(cfg["selection"]["min_days_left"]))
        meta = {"file": f"fixture:{path.name}", "sha256": fsha, "url": rec["source_url"],
                "note": "Supplied/reconstructed public content; not live ingest" if public_fixture else "Archived Grants.gov fixture; not a new official observation"}
        from .editorial import ranking_evidence
        rank = ranking_evidence(rec, s, why, meta,audience=cfg.get('selection',{}).get('audience','general_us'),as_of=today)
        rec["ranking_evidence"] = rank
        s = rank["score"]
        recs.append((s, rec, meta))
        considered.append({"opportunity_id": rec["opportunity_id"], "title": rec["title"], "score": s, "why": why, "ranking": rank, "facets": rec["selection_assessment"]})
    return recs, considered, [{"file": f"fixture:{path.name}", "sha256": fsha}], len(rows)


# ------------------------------------------------------------------ main run

def run(cfg: dict, out_root: Path, fixture: Path | None = None, opportunity: str | None = None,
        history_path: Path | None = None, stop_after: str | None = None, resume_prepared: Path | None = None, public_input: Path | None = None, visual_revision: dict | None = None) -> Path:
    from .runtime import validate_config
    guarded=[Path(out_root).resolve()]+([Path(resume_prepared).resolve()] if resume_prepared else [])+([Path(history_path).resolve().parent] if history_path else [])
    if any((parent/'MIGRATION_REVIEW_ONLY.json').is_file() for root in guarded for parent in (root,*root.parents)):raise PipelineError('Review-only discovery migration copy cannot enter pipeline')
    if visual_revision is not None and (stop_after!='script' or not resume_prepared):raise PipelineError('New visual revision requires an immutable source parent and script-only target')
    if public_input and (stop_after!='script' or fixture or resume_prepared or opportunity):raise PipelineError('Public receipt input is source-only and cannot combine with other source overrides')
    if resume_prepared and (fixture is not None or opportunity is not None):
        raise PipelineError("Cannot combine prepared resume with fixture/opportunity override")
    if stop_after not in (None,"script"):raise PipelineError("Unsupported stop-after boundary")
    from .local_editorial import authorized as editorial_authorized
    if stop_after and cfg.get("writer")!="template" and not editorial_authorized(cfg):
        raise PipelineError("Model-free preparation requires explicit writer=template; no silent fallback")
    validate_config(cfg,require_models=stop_after is None)
    if stop_after is None and cfg.get('generation_hold'):raise PipelineError(cfg['generation_hold'])
    now = utc_now()
    today = now.date()
    history_path = Path(history_path) if history_path else out_root / "history.json"
    history = read_json(history_path) if history_path and history_path.exists() else {"runs": []}
    if stop_after:
        from .preparation_history import load_reservations
        reservations=load_reservations(history_path,out_root)
        from .automatic_research import eligible as reference_eligible
        if reservations.get('problems') and reference_eligible(cfg,stop_after,opportunity):raise PipelineError('Verified prepared-topic history is incomplete; automatic research cannot infer an unseen topic. Originals preserved')
        history={"runs":history.get("runs",[])+reservations["runs"]}
    seen = {r["opportunity_id"] for r in history.get("runs", [])} | \
           {family(r["title"]) for r in history.get("runs", []) if r.get("title")}
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"_incomplete_{now.strftime('%Y%m%dT%H%M%S%f')}_", dir=out_root))
    src_dir = tmp / "source"
    src_dir.mkdir(parents=True)
    log = {"started_at": now.isoformat(), "mode": "fixture" if fixture else "live", "notes": []}

    if resume_prepared:
        from .preparation import verify_preparation
        source=Path(resume_prepared).resolve();prepared=verify_preparation(source)
        visual_recipe=None
        if visual_revision is not None:
            from .visual_revision import validate_parent
            validate_parent(source,visual_revision);visual_recipe=visual_revision
        elif 'visual_revision.json' in {e['path'] for e in prepared['files']}:
            visual_recipe=read_json(source/'visual_revision.json')
        if visual_recipe is not None:
            cfg={**cfg,'preparation_refresh_source':False};log['visual_revision']=visual_recipe

        if stop_after is None:
            from .source_quality import inspect_directory
            pinned_quality=inspect_directory(source,config_override=cfg)
            if not pinned_quality['ready_for_generation']:
                raise PipelineError('Pinned draft blocked before source/model work: '+'; '.join(pinned_quality['generation_blockers']))
        for entry in prepared['files']:
            if entry['path'] in {'production_plan.json','preparation_config.json'}:continue
            target=tmp/entry['path'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/entry['path'],target)
        rec=read_json(source/'topic.json')['selected']
        snap=read_json(source/'sources.json')['selected_snapshot']
        run_id=f"{now.strftime('%Y%m%d')}_{rec['opportunity_id']}_{slug(rec['title'],32)}"
        log['mode']=prepared['mode'];log['source_inputs_reused']=True
        log['original_preparation_id']=prepared['preparation_id']
        log['nofo_check']=read_json(source/'production_plan.json').get('source_review_note')
        if stop_after=='script' and prepared['mode']=='live' and cfg.get('preparation_refresh_source') is True:
            from .refresh_source import refresh
            rec,log['nofo_check'],log['source_materialization'],snap,calls=refresh(source,src_dir,int(cfg['selection']['min_days_left']),history_path=history_path)
            write_json(tmp/'sources.json',{'mode':'live','api_calls':calls,'selected_snapshot':snap,'public_url':rec['source_url']})
        elif stop_after=='script' and prepared['mode']=='live':
            from .rematerialize import rebuild_saved_source
            rec,log['nofo_check'],log['source_materialization']=rebuild_saved_source(source,src_dir,int(cfg['selection']['min_days_left']))
        if rec.get('public_money_source'):public_original_snapshot=dict(snap)
        topic=read_json(tmp/'topic.json');topic.update(run_id=run_id,resumed_at=now.isoformat(),selected=rec)
        write_json(tmp/'topic.json',topic)
    else:
        progress("sources", tmp)
        # 1. topic
        research_selected=False
        if public_input:
            from .public_page import record as public_record
            rec,snap,transport_receipt=public_record(public_input,src_dir,cfg.get('selection',{}).get('audience','general_us'))
            public_original_snapshot=dict(snap)
            log['mode']='public_page_fixture' if transport_receipt['mode']=='fixture' else 'public_page_observed'
            recs=[(1,rec,snap)];considered=[{'opportunity_id':rec['opportunity_id'],'reason':'Explicit fixed official page; no Grants.gov discovery or forced eligibility'}];calls=[];n_hits=1
        elif fixture:
            recs, considered, calls, n_hits = discover_fixture(fixture, today, cfg, seen, opportunity)
        else:
            from .automatic_research import select as select_research
            score,rec,snap,source_review,publisher_rejections,considered,calls,n_hits=select_research(cfg,src_dir,today,seen,opportunity,history_path,stop_after)
            recs=[(score,rec,snap)];research_selected=True
            if rec.get('_automatic_reference'):
                log['mode']='automatic_public_reference';public_original_snapshot=dict(snap)
                log['automatic_research']=source_review.get('automatic_reference_selection')
        good = sorted([r for r in recs if r[0] > -99], key=lambda r: (-r[0], str(r[1]["opportunity_id"])))
        if not good:
            write_json(tmp / "topic.json", {"error": "no selectable candidate in bounded pass", "considered": considered, "individual_eligibility_assessed": False})
            write_json(src_dir/'audience_selection.json', {'status':'no_candidates_in_bounded_pass','audience':cfg.get('selection',{}).get('audience','general_us'),'deferred':[],'format_deferred':[],'source_deferred':[],'selection_stage':'upstream_discovery_score_filter','global_opportunity_absence_established':False})
            if not fixture and cfg['search'].get('pagination') is True:
                raise PipelineError('No selectable candidate in this bounded discovery pass; deferred/unreviewed sources may remain. Personal eligibility and global opportunity absence are not established')
            raise PipelineError(f"No selectable candidate in this bounded pass ({len(recs)} detailed / {n_hits} search hits); not a personal eligibility decision or complete opportunity search")
        if not research_selected:
            score,rec,snap=good[0];source_review={'checked':False,'reason':'Authentic transport receipt is separate from factual/source-currentness review' if public_input else 'fixture'};publisher_rejections=[]
        log["publisher_rejections"]=publisher_rejections
        run_id = f"{now.strftime('%Y%m%d')}_{rec['opportunity_id']}_{slug(rec['title'], 32)}"
        write_json(tmp / "sources.json", {"mode": log["mode"], "api_calls": calls, "selected_snapshot": snap,
                                          "public_url": rec["source_url"]})
        write_json(tmp / "topic.json", {"run_id": run_id, "selected": {k: v for k, v in rec.items()},
                                         "score": score, "found": n_hits, "considered": considered,"publisher_rejections":publisher_rejections,
                                         "excluded_previously_used": sorted(seen), "selected_at": now.isoformat()})
        log['nofo_check'] = source_review
        # Preserve supplemental official source metadata in the topic record.
        if rec.get('submission_steps'):
            topic = read_json(tmp / 'topic.json')
            topic['selected'] = rec
            write_json(tmp / 'topic.json', topic)
        # same-family siblings found in this run are not repeated later either


    if rec.get('public_money_content'):
        payload=rec['public_money_content'];name='source/public_money_supplied.html' if payload.get('content_type','html')=='html' else 'source/public_money_supplied.txt'
        digest=write_text(tmp/name,payload['content'])
        if digest!=rec['public_money_source']['content_sha256']:raise PipelineError('Supplied source content changed before preparation')
        payload['snapshot_file']=name
        from .source_brief import adapt as adapt_public_content
        rec=adapt_public_content(rec,audience=cfg.get('selection',{}).get('audience','general_us'))
        data=rec['public_money_source'];snap={'file':name,'sha256':digest,'url':rec['source_url'],'fetched_at':data.get('fetched_at'),'source_updated':data.get('source_updated'),'reconstructed':data['reconstructed'],'not_http_observation':True}
        if public_input or rec.get('_automatic_reference') or (resume_prepared and rec.get('public_money_source')):snap.update({k:v for k,v in public_original_snapshot.items() if k not in {'file','sha256'}})
        write_json(tmp/'sources.json',{'mode':log['mode'],'api_calls':[],'selected_snapshot':snap,'public_url':rec['source_url']})
        topic=read_json(tmp/'topic.json');topic['selected']=rec;write_json(tmp/'topic.json',topic)

    if not stop_after and not fixture:
        from .editorial import require_gate
        log['early_source_gate']=require_gate(rec,snap,utc_now(),int(cfg['selection']['min_days_left']))
        if (log.get('nofo_check') or {}).get('checked') is not True:
            raise PipelineError('Full official announcement review unavailable before model stage')
        if resume_prepared:
            from .preparation_source import check_prepared_source
            log['resume_source_check']=check_prepared_source(source,tmp/'source_recheck')
            if not log['resume_source_check']['ready_for_model_stage']:
                raise PipelineError('Current resumed source blocked before model stage: '+'; '.join(log['resume_source_check']['reasons']))

    if not fixture and (log.get('nofo_check') or {}).get('checked') is not True:
        rec['source_conditions_unconfirmed']=True
        topic=read_json(tmp/'topic.json');topic['selected']=rec;write_json(tmp/'topic.json',topic)

    from .source_brief import adapt as adapt_editorial_source
    rec=adapt_editorial_source(rec,snap,cfg.get("selection",{}).get("audience","general_us"))
    if log.get('visual_revision') is not None:
        from .visual_revision import apply as apply_visual_revision
        rec=apply_visual_revision(rec,log['visual_revision'])
        topic=read_json(tmp/'topic.json');topic['selected']=rec;write_json(tmp/'topic.json',topic)
        write_json(tmp/'visual_revision.json',log['visual_revision'])
        write_json(tmp/'visual_materialization.json',{'schema':'SOCIAL_VISUAL_MATERIALIZATION_V1','parent_preparation_id':log['original_preparation_id'],'manual_revision':log['visual_revision']['manual_revision'],'factual_wording_unchanged':True,'source_observation_refreshed':False,'models_started':False})
    write_json(tmp/"editorial_source_brief.json",rec["editorial_source_brief"])
    from .audience_selection import require as require_audience
    log["audience_fit"]=require_audience(rec,cfg.get("selection",{}).get("audience","general_us"))

    progress("claims", tmp)
    # 2. claims
    claims = build_claims(rec, snap, today)
    for c in claims:
        c["observed_at"] = snap.get("fetched_at")
        c["materialized_at"] = log["started_at"]
    write_json(tmp / "claims.json", {"contract": CONTRACT, "opportunity_id": rec["opportunity_id"],
                                      "built_from": snap, "claims": claims,
                                      "rule": "claims are copied from official fields only; writers can cite, never add"})

    progress("script", tmp)
    # 3. script
    script, wreport = write_script(rec, claims, cfg)
    script["speech_normalizer_version"]="social_speech_v2"
    errs = validate_script(script, claims)
    if errs:
        raise PipelineError("script failed grounding: " + "; ".join(errs))
    from .editorial import storyboard, require_gate
    script, board = storyboard(script, claims, rec)
    write_json(tmp / "storyboard.json", board)
    write_json(tmp / "script.json", script)
    write_text(tmp / "script.md", script_md(script, claims, rec))
    from .source_description import compose as compose_description
    write_text(tmp/"description.md",compose_description(script,claims,rec))
    if resume_prepared and stop_after is None and sha256_file(tmp/'script.json')!=sha256_file(Path(resume_prepared)/'script.json'):
        raise PipelineError('Pinned script differs under current writer; rebuild and review an immutable draft before model execution')
    if wreport.get("editorial_analysis") is not None:write_json(tmp/"editorial_analysis.json",wreport)
    log["writer"] = wreport

    from .source_quality import assess as assess_editorial,inspect_observation
    log["source_quality"]=assess_editorial(rec,script,claims,board,cfg,source_observation=inspect_observation(tmp,rec))
    write_json(tmp/"source_quality.json",log["source_quality"])
    if stop_after is None and not log["source_quality"]["ready_for_generation"]:
        raise PipelineError("Source/editorial readiness: "+"; ".join(log["source_quality"]["generation_blockers"]))
    if not fixture:
        if stop_after is None:
            log["pre_voice_source_gate"] = require_gate(rec, snap, utc_now(), int(cfg["selection"]["min_days_left"]))
        else:
            from .editorial import production_gate
            log["pre_voice_source_gate"]=production_gate(rec,snap,utc_now(),int(cfg["selection"]["min_days_left"]))
    if stop_after == "script":
        from .preparation import save_preparation
        destination=save_preparation(tmp,out_root,run_id,rec,script,cfg,log,history_path,allow_repeat=bool(resume_prepared or public_input))
        if not fixture and not public_input and not resume_prepared and not rec.get('public_money_source') and cfg['search'].get('pagination') is True and not opportunity:
            from .discovery_cursor import acknowledge
            acknowledge(cfg,history_path,[rec['opportunity_id']])
        return destination
    if not fixture and log.get("mode")=="live" and (log.get("nofo_check") or {}).get("checked") is not True:
        raise PipelineError("Full official announcement review unavailable; source/script preserved, generation not started")
    from .duration_preflight import assess as assess_duration
    log['duration_preflight']=assess_duration(script,cfg['voice'])
    write_json(tmp/'duration_preflight.json',log['duration_preflight'])
    if not log['duration_preflight']['pass']:raise PipelineError(log['duration_preflight']['reason'])
    if script.get("money_benefit") and script.get("live_verified") is not True:
        raise PipelineError("Source-only draft lacks actual live ingest; model/assembly execution forbidden")
    if script.get("synthetic"):
        raise PipelineError("Synthetic editorial fixtures are source-only; model/assembly execution forbidden")
    progress("voice", tmp)
    # 4. voice
    cache = Path(os.environ.get("SOCIAL_VOICE_CACHE", Path.home() / ".cache" / "socialreel" / "voices"))
    voice, vnotes = make_voice(cfg["voice"], cache)
    log["notes"] += vnotes
    adir = tmp / "audio"
    adir.mkdir()
    wavs, speech = [], []
    for i, seg in enumerate(script["segments"], 1):
        progress("voice", tmp, segment=i, total_segments=len(script["segments"]))
        st = speech_for_script(script,seg["voiceover"])
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
                       "speech_s": round(wav_duration(wavs[i - 1]), 3), "speech_start_s": round(t + .18, 3), "audio": f"audio/segment_{i:02d}.wav"})
        t += d
    write_json(tmp / "timing.json", {"fps": 30, "total_s": round(t, 3), "segments": timing,
                                      "rule": "timing is measured from the synthesized audio, not guessed"})

    # Required offline ASR and subtitles before rendering, never silently skipped.
    progress("subtitles", tmp)
    from .subtitles import inspect_narration
    asr = inspect_narration(narration, speech, timing, cfg["asr"], tmp)
    if not asr or not asr["pass"]:
        raise PipelineError("narration verification failed: " + (asr.get("detail", "no ASR result") if asr else "no ASR result"))
    from .scene_coherence import observed_gate
    scene_alignment=observed_gate(script,asr,timing)
    write_json(tmp/'scene_alignment.json',scene_alignment)
    if not scene_alignment['pass']:raise PipelineError('Spoken scene/caption mismatch; preserve audio for review, no assembly started')
    if hasattr(voice,"seal_verified"):
        log["voice_cache_sealed"] = voice.seal_verified()
        log["legacy_voice_cache_hits"] = voice.legacy_hits
    log["voice_cache_hits"] = getattr(voice, "hits", 0)

    if not fixture:
        log["pre_render_source_gate"] = require_gate(rec, snap, utc_now(), int(cfg["selection"]["min_days_left"]))
        write_json(tmp / "production_source_gate.json", log["pre_render_source_gate"])
    progress("render", tmp)
    # 5. visuals + render
    footer = (f"Source: Grants.gov - {rec['opportunity_id']}\n"
              f"Checked {human_date(today)}\nVerify before applying")
    if cfg.get('artifact_purpose')=='technical_preview':
        footer=f"Grants.gov | TEST PREVIEW\nChecked {human_date(today)}\nNot editorially approved"
    write_json(tmp / "visual_plan.json", {"canvas": "1080x1920@30", "footer": footer, "segments": [
        {"id": s["id"], "visual": s["visual"], "on_screen": s.get("on_screen", {}),
         "still": f"mediaengine_handoff/stills/segment_{i:02d}.png", "claim_keys": s["claim_keys"]}
        for i, s in enumerate(script["segments"], 1)]})
    me = tmp / "mediaengine_handoff"
    final = tmp / "final"
    final.mkdir()
    mp4 = final / "reel.mp4"
    rinfo = render_video(script["segments"], durs, narration, mp4, footer, me / "stills", tmp / "subtitles.srt" if (tmp / "subtitles.srt").exists() else None)
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

    progress("verify", tmp)
    # 6. verification of the actual file
    mids = [(x["start_s"] + x["end_s"]) / 2 for x in timing]
    ver = verify_video(mp4, t, tmp / "review", mids)
    if not fixture:
        from .editorial import production_gate
        gate=production_gate(rec,snap,utc_now(),int(cfg['selection']['min_days_left']))
        log['pre_package_source_gate']=gate
        ver['checks'].append({'check':'production_source_freshness','pass':gate['pass'],'detail':gate})
        ver['pass']=ver['pass'] and gate['pass']
    # ASR already measured offline before rendering.
    if asr:
        write_text(tmp / "review" / "narration_transcript.txt", asr["transcript"] + "\n")
        ver["checks"].append(asr)
        ver["pass"] = ver["pass"] and asr["pass"]
    if voice.test_only:
        ver["checks"].append({"check": "real_voice", "pass": False, "detail": "silent_test voice is test-only"})
        ver["pass"] = False
    if log["mode"] != "live":
        ver["checks"].append({"check": "live_source", "pass": False, "detail": "fixture mode: not a live topic"})
        ver["pass"] = False

    progress("package", tmp)
    # 7. manifests
    media_files = sorted([p for p in (tmp / "audio").glob("*.wav")] + list((me / "stills").glob("*.png")) + [mp4])
    write_json(tmp / "media_manifest.json", {"files": [_fe(tmp, p) for p in media_files], "render": rinfo,
                                              "voice": voice.identity()})
    pkg_files = ["sources.json", "topic.json", "claims.json", "script.json", "script.md", "timing.json",
                 "voice.txt", "visual_plan.json", "media_manifest.json", "storyboard.json"]
    pkg_files += ["subtitles.srt", "subtitles.vtt", "asr.json"]
    pkg_files += [f for f in ("production_source_gate.json",) if (tmp / f).is_file()]
    pkg_files += sorted(str(p.relative_to(tmp)) for p in src_dir.rglob("*") if p.is_file())
    pkg_files += sorted(str(p.relative_to(tmp)) for p in me.rglob("*") if p.is_file())
    if resume_prepared and log['mode']=='live':
        from .production_origin import create_origin
        pkg_files+=create_origin(tmp,prepared)
    pkg_files=list(dict.fromkeys(pkg_files))
    entries = [_fe(tmp, tmp / f) for f in pkg_files]
    from .common import sha256_bytes
    package_id = sha256_bytes("\n".join(f"{e['path']} {e['sha256']}" for e in entries).encode())
    video_sha = sha256_file(mp4)
    lineage = {"parent_preparation_id":log.get('original_preparation_id') if (tmp/'production_origin.json').is_file() else None,"asr_input_schema":(asr.get("input_lineage") or {}).get("schema"),"source_snapshot": snap, "claims_sha256": sha256_file(tmp / "claims.json"),
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
        dest = out_root / (run_id + "_" + now.strftime("%H%M%S%f"))
    from .packages import verify_package
    package_check = verify_package(tmp)
    if not package_check["pass"]:
        raise PipelineError("Package failed before publication: " + "; ".join(package_check["errors"]))
    tmp.rename(dest)
    if history_path and result["accepted"]:
        history.setdefault("runs", []).append({"run_id": run_id, "opportunity_id": rec["opportunity_id"],
                                               "title": rec["title"],
                                               "date": today.isoformat(), "package_id": package_id,
                                               "video_sha256": video_sha, "writer": result["writer"]})
        write_json(history_path, history)
    progress("completed", dest, accepted=result["accepted"])
    return dest


def _fe(root: Path, p: Path) -> dict:
    return {"path": str(p.relative_to(root)), "sha256": sha256_file(p), "bytes": p.stat().st_size}


def script_md(script, claims, rec) -> str:
    by = {c["key"]: c for c in claims}
    out = [f"# {script['title']}", "", f"Writer: `{script['writer']}` · Source: {rec['source_url']}", ""]
    for s in script["segments"]:
        out.append(f"## {s['id']} · {s['role']} · visual `{s['visual']}`")
        out.append(f"**Voiceover:** {s['voiceover']}")
        scr = s.get("on_screen") or {}
        out.append("**On screen:** " + " | ".join(f"{k}: {v}" for k, v in scr.items() if v).replace("\n", " / "))
        out.append("**Claims:** " + "; ".join(f"`{k}` — {by[k]['statement']}" for k in s["claim_keys"] if k in by))
        out.append("")
    out += ["## Description", "", __import__("socialreel.source_description",fromlist=["compose"]).compose(script,claims,rec), "", "## Source note", "", script.get("source_note", "")]
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


## Captions in the current Social renderer

The verified `../final/reel.mp4` includes measured, burned captions.
The static frames here are scene bases; they do not contain changing captions or progress animations.
The complete package includes `../subtitles.srt` and `../subtitles.vtt` with actual word timings.
No downstream application was invoked or tested in this pilot. Use the verified final MP4 for review.

Exact package identity: see `../package_manifest.json` (SHA-256 of every file, including these).
"""


def rebuild(run_dir: Path) -> dict:
    """Re-render the video from the stored package and compare hashes (repeatability proof)."""
    from .packages import verify_package
    integrity = verify_package(run_dir)
    if not integrity['pass']:
        raise PipelineError('Package integrity failed before rebuild: ' + '; '.join(integrity['errors']))
    script = read_json(run_dir / "script.json")
    timing = read_json(run_dir / "timing.json")
    vp = read_json(run_dir / "visual_plan.json")
    durs = [x["end_s"] - x["start_s"] for x in timing["segments"]]
    out = Path(tempfile.mkdtemp(prefix="_rebuild_", dir=run_dir))
    render_video(script["segments"], durs, run_dir / "audio" / "narration.wav", out / "reel.mp4", vp["footer"], out / "stills", run_dir / "subtitles.srt" if (run_dir / "subtitles.srt").exists() else None)
    a, b = sha256_file(run_dir / "final" / "reel.mp4"), sha256_file(out / "reel.mp4")
    stills_same = all(sha256_file(p) == sha256_file(run_dir / "mediaengine_handoff" / "stills" / p.name)
                      for p in (out / "stills").glob("*.png"))
    res = {"original_sha256": a, "rebuild_sha256": b, "byte_identical": a == b, "stills_identical": stills_same}
    shutil.rmtree(out)
    return res


def assess_audience(rec):
    text=rec.get('applicant_eligibility_desc') or ''
    mixed=bool(re.search(r'\b(?:U\.?S\.?|United States|domestic)\s+(?:and|or)\s+(?:foreign|non[- ]U\.?S\.?)',text,re.I))
    patterns=[r'\b(?:only|exclusively)\s+(?:(?:registered|eligible)\s+)?(?:foreign|non[- ]U\.?S\.?)\s+(?:organizations|entities|applicants)',
              r'\b(?:applicants|organizations|entities)\s+(?:must|shall)\s+be\s+(?:based|located|registered)\s+outside\s+(?:the\s+)?(?:United States|U\.?S\.?)']
    match=next((m for pattern in patterns if (m:=re.search(pattern,text,re.I)) and not text[max(0,m.start()-5):m.start()].strip().lower().endswith('not')),None)
    return {'intended_market':'US','source_scope':'US federal listing',
            'explicit_foreign_only':bool(match) and not mixed,'restriction_evidence':match.group(0) if match else None,
            'domestic_eligibility_proven':False,'suitability':'unsuitable_explicit_foreign_only' if match and not mixed else 'unknown','mixed_categories':mixed,
            'rule':'Federal source does not prove US applicant eligibility; listing categories and full conditions govern'}


def candidate_facets(rec,today,keywords,min_days):
    fields={'title':rec.get('title') or '', 'description':rec.get('description') or '',
            'applicant_types':' | '.join(rec.get('applicant_types') or [])}
    matched=[];evidence=[]
    for keyword in keywords:
        parts=re.findall(r'[a-z]+',keyword.lower())
        source_matches=[]
        for name,value in fields.items():
            tokens=set(re.findall(r'[a-z]+',value.lower()))
            if parts and all(word in tokens or word+'s' in tokens or word+'es' in tokens for word in parts):
                position=next((m.start() for m in re.finditer(r'\b'+re.escape(parts[0])+r'(?:s|es)?\b',value,re.I)),0)
                source_matches.append({'field':name,'excerpt':value[max(0,position-50):position+190],
                                       'official_url':rec.get('source_url')})
        if source_matches:
            matched.append(keyword);evidence.append({'keyword':keyword,'matches':source_matches})
    close=parse_date(rec.get('close_date'));opening=parse_date(rec.get('open_date'))
    valid=(rec.get('status') or '').lower()=='posted' and (rec.get('doc_type') or '').lower()!='forecast' and close is not None and (close-today).days>=min_days and (opening is None or opening<=today)
    audience=assess_audience(rec)
    return {'topic_match':{'state':'lexical_match' if matched else 'unverified','matched_keywords':matched,'evidence':evidence,'search_terms':list(keywords),'trend_proven':False},
            'date_status':{'eligible_for_selection':valid,'source_status':rec.get('status'),'close_date':close.isoformat() if close else None,'days_left':(close-today).days if close else None,'as_of':today.isoformat()},
            'applicant_categories':{'listed':list(rec.get('applicant_types') or []),'specific_viewer_eligible':False},'target_audience':audience}

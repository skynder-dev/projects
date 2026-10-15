"""AI+ theme "Aerial view (drone)" on REAL drone videos (public Wikimedia Commons videos, free licences - never the
owner's videos) on Windows CI.

  python tests/drone_theme_check.py <work_dir> --out <results_dir> [--manifest tests/drone_manifest.json]

Drone videos often start and end on the ground (take-off and landing: grass, feet, the pilot, the drone itself).
The theme has to prefer the view from above. For every video:
- every frame the AI+ model looks at (about one per second, at most 48) with its theme score: with the theme's own
  bad descriptions (THEME_NEGATIVES, used by the app) and without them (only the general bad descriptions) - green
  border: the frame matches the theme, red: it does not;
- the windows the theme ranking picks (P1, P2, ...);
- with a pinned manifest whose videos mark their ground parts ("ground": [[from_s, to_s], ...], looked at on the
  sheets of an earlier run), a check that none of the best three picks is centred on the ground.
Then through the app: "Prepare in advance" of the folder for AI+ with the aerial theme, the reel made after it
(a 30 s vertical reel; its time and contact sheet), and the same length with AI (the accepted model, no theme) for
comparison.
Results: the sheets, JSON and ATTRIBUTION.md (results branch); the reels (CI artifact). Not a quality proof: the
owner's own drone videos are the real test.
"""
from __future__ import annotations

import json, os, shutil, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402
from real_footage_check import api, contact_sheet, download, free_licence, strip_html  # noqa: E402

TOPICS = ["drone take off", "drone footage", "aerial drone video", "DJI Phantom", "DJI Mavic", "quadcopter flight",
          "drone landing", "aerial view drone beach"]
PER_TOPIC = 3
MAX_VIDEOS = 10
THEME = "aerial"


def discover() -> list[dict]:
    """Commons search: free-licence drone videos of 15-300 s (transcodes of at most 720p)."""
    picked, seen = [], set()
    for topic in TOPICS:
        res = api({"action": "query", "generator": "search", "gsrsearch": f"filetype:video {topic}", "gsrnamespace": 6,
                   "gsrlimit": 30, "prop": "imageinfo|videoinfo", "iiprop": "url|size|mime|extmetadata|sha1",
                   "viprop": "derivatives|size"})
        pages = sorted(res.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
        n = 0
        for p in pages:
            title = p.get("title", "")
            if title in seen or not p.get("imageinfo"):
                continue
            ii = p["imageinfo"][0]
            vi = (p.get("videoinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            dur = float(vi.get("duration") or ii.get("duration") or 0)
            if not free_licence(lic) or not (15 <= dur <= 300):
                continue
            ders = vi.get("derivatives") or []
            pick = None
            for key in ("720p.vp9.webm", "480p.vp9.webm", "720p.webm", "480p.webm"):
                pick = next((d for d in ders if str(d.get("transcodekey", "")).endswith(key)), None)
                if pick:
                    break
            if not pick:
                continue
            seen.add(title)
            picked.append({"title": title, "topic": topic, "duration_s": dur, "url": pick["src"], "page": ii.get("descriptionurl"),
                           "licence": lic, "licence_url": strip_html((meta.get("LicenseUrl") or {}).get("value", "")),
                           "author": strip_html((meta.get("Artist") or {}).get("value", ""))[:200],
                           "original_sha1": ii.get("sha1"), "ground": None})
            n += 1
            if n >= PER_TOPIC or len(picked) >= MAX_VIDEOS:
                break
        if len(picked) >= MAX_VIDEOS:
            break
        time.sleep(1)
    return picked


def frame_sheet(path: Path, rows: list, margins, generic, picks: list, out: Path, title: str) -> None:
    """Every scout frame with its time and theme score (theme's own bad descriptions / general ones only)."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    tw, th, cols = 224, 126, 8
    n = len(rows)
    nrows = -(-n // cols)
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, nrows * (th + 40) + 46), (18, 20, 26))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    d.text((8, 10), title, fill=(240, 240, 240), font=font)
    centres = {}
    for k, pk in enumerate(picks):
        i = min(range(n), key=lambda j: abs(float(rows[j]["t"]) - float(pk["center_s"])))
        centres.setdefault(i, []).append(k + 1)
    cap = cv2.VideoCapture(str(path))
    for i, r in enumerate(rows):
        t = float(r["t"])
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, bgr = cap.read()
        x, y = 6 + (i % cols) * (tw + 6), 40 + (i // cols) * (th + 40)
        m, g = float(margins[i]), float(generic[i])
        d.rectangle([x - 3, y - 3, x + tw + 2, y + th + 2], fill=(40, 200, 90) if m > 0 else (210, 60, 60))
        if ok:
            sheet.paste(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).resize((tw, th)), (x, y))
        lab = f"{t:5.1f}s  {m:+.1f} / {g:+.1f}"
        if i in centres:
            lab += "  P" + ",".join(map(str, centres[i]))
        d.text((x + 2, y + th + 6), lab, fill=(255, 230, 90) if i in centres else (220, 220, 220), font=font)
    cap.release()
    sheet.save(out, quality=86)


def main():
    work = Path(sys.argv[1]).resolve()
    outd = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    manifest = Path(sys.argv[sys.argv.index("--manifest") + 1]) if "--manifest" in sys.argv else HERE / "drone_manifest.json"
    outd.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    report = {"checks": [], "timings": {}, "theme": THEME}

    def check(name, ok, detail=None):
        report["checks"].append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def save():
        (outd / "drone_theme.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # 1. the videos
    t0 = time.time()
    items = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else discover()
    report["source"] = "pinned manifest" if manifest.is_file() else "Commons search"
    folder = work / "Drone videos"
    vids = download(items, folder)
    report["videos"] = vids
    report["timings"]["download_s"] = round(time.time() - t0, 1)
    (outd / "drone_manifest.json").write_text(json.dumps([{k: v for k, v in x.items() if k not in ("file", "bytes")} for x in vids],
                                                        indent=2, ensure_ascii=False), encoding="utf-8")
    att = ["# Videos used (Wikimedia Commons, free licences)", "",
           "Used only to test MediaEngine's AI+ theme 'Aerial view (drone)'; the sheets and reels are made from them.", ""]
    for v in vids:
        att.append(f"- **{v['title']}** — {v['author'] or 'unknown author'} — {v['licence']} ({v['licence_url'] or 'see page'}) — {v['page']}")
    (outd / "ATTRIBUTION.md").write_text("\n".join(att) + "\n", encoding="utf-8")
    check("enough_drone_videos", len(vids) >= 4, len(vids))
    save()
    if len(vids) < 2:
        return 1

    # 2. the AI+ model, downloaded by the app (the same public, pinned files the owner gets)
    home = work / "home"
    shutil.rmtree(home, ignore_errors=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    sys.path.insert(0, str(ROOT / "app"))
    from real_models_check import FAST_REPO, FAST_REV, FAST_SUPPORT, fetch
    from archivist.web import create_app
    from archivist import auto_edit as ae
    fast = home / "models" / "FAST_LOCAL"
    fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/onnx/model_int8.onnx", fast / "model_int8.onnx")
    for n in FAST_SUPPORT:
        fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/{n}", fast / f"support_{FAST_REV}" / n)
    t0 = time.time()
    for _attempt in range(2):
        ae.aiplus_download_start()
        while ae._AIPLUS_DL["state"] == "running" and time.time() - t0 < 900:
            time.sleep(2)
        if ae._AIPLUS_DL["state"] == "done":
            break
    check("models_ready", ae.model_status()["ready"] and ae.aiplus_status()["ready"], (ae.model_status(), ae._AIPLUS_DL))
    if not ae.aiplus_status()["ready"]:
        save(); return 1

    # 3. what the model sees in every frame (the engine's own code: scout, scores, theme windows)
    eng = ROOT / "app" / "archivist" / "engine_p11"
    sys.path.insert(0, str(eng))
    import importlib.util
    import numpy as np
    import p13_event_semantic_pe as hook
    import p13_pe_core_adapter as pa
    spec = importlib.util.spec_from_file_location("medeng_event_semantic_v7", eng / "medeng_event_semantic_v7.py")
    v7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7)
    scorer = pa.PECoreScorer(ae.aiplus_dir(), full_check=False, threads=os.cpu_count() or None)
    pos, neg_theme = hook.prompts_for(THEME)
    tp = scorer.encode_text(list(pos)); tn = scorer.encode_text(list(neg_theme)); tg = scorer.encode_text(list(hook.NEGATIVE_PROMPTS))
    per = []
    t0 = time.time()
    for v in vids:
        path = folder / v["file"]
        try:
            info, emb = hook.scout(v7, scorer, path, ff, ff)
        except Exception as exc:
            per.append({"file": v["file"], "error": f"{type(exc).__name__}: {exc}"[:300]}); continue
        lp = 100.0 * emb @ tp.T
        top2 = np.sort(lp, axis=1)[:, -2:].mean(axis=1)
        margins = top2 - (100.0 * emb @ tn.T).max(axis=1)
        generic = top2 - (100.0 * emb @ tg.T).max(axis=1)
        rows = info["rows"]
        rep = hook.rank(v7, scorer, path, info, emb, THEME, ff)
        picks = [{k: c[k] for k in ("start_s", "end_s", "center_s", "semantic_margin_raw", "final_score")} for c in rep["ranked"]]
        frames = [{"t": round(float(r["t"]), 2), "margin": round(float(m), 2), "margin_generic_bad_only": round(float(g), 2)}
                  for r, m, g in zip(rows, margins, generic)]
        item = {"file": v["file"], "title": v["title"], "duration_s": info["duration_s"], "frames": frames, "picks": picks,
                "frames_matching": int((margins > 0).sum()), "frames_matching_generic_bad_only": int((generic > 0).sum()),
                "ground": v.get("ground")}
        ground = v.get("ground") or []
        if ground:      # labelled video: the best three picks are not centred on the ground
            on_ground = lambda t: any(float(a) <= t <= float(b) for a, b in ground)
            gf = [f for f in frames if on_ground(f["t"])]
            item["ground_frames_matching"] = sum(f["margin"] > 0 for f in gf)
            item["ground_frames_matching_generic_bad_only"] = sum(f["margin_generic_bad_only"] > 0 for f in gf)
            bad = [p for p in picks[:3] if on_ground(float(p["center_s"]))]
            check(f"no_ground_pick:{v['file']}", not bad, bad)
        per.append(item)
        frame_sheet(path, rows, margins, generic, picks[:3], outd / (Path(v["file"]).stem + ".frames.jpg"),
                    f"{v['file']} - green: matches 'aerial' (score with the theme's bad descriptions / general bad only) - P = picks")
        report["frames"] = per
        save()
    report["timings"]["frames_s"] = round(time.time() - t0, 1)
    del scorer
    check("frames_scored", sum(1 for x in per if "frames" in x) >= max(2, len(vids) - 1), [x.get("error") for x in per])

    # 4. through the app: prepare the folder in advance (AI+, aerial), then the reel; and an AI reel for comparison
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}

    def wait(jid, limit=5400):
        t = time.time()
        while time.time() - t < limit and ae.job(jid)["status"] in ("queued", "running"):
            time.sleep(2)
        return ae.job(jid), time.time() - t

    reels = {}

    def take(key, j, dt):
        rev = ae.revision(j.get("revision_id") or 0) if j["status"] == "done" else None
        check(f"{key}_built", rev is not None, (j["status"], j.get("error")))
        if not rev:
            return
        res = rev["result"]
        reel = Path(rev["video_path"]) if rev.get("video_path") else None
        reels[key] = {"revision_id": rev["id"], "seconds": round(dt, 1), "selection_mode": res.get("selection_mode"),
                      "theme": res.get("theme"), "stage_seconds": res.get("stage_seconds"), "duration_s": res.get("actual_duration_s"),
                      "segments": [{k: s_[k] for k in ("source_name", "source_in_s", "source_out_s", "reel_in_s", "reel_out_s", "score")}
                                   for s_ in res.get("segments", [])]}
        lab = {x["file"]: x.get("ground") or [] for x in vids}
        on_ground = [s_ for s_ in res.get("segments", []) if any(float(a) <= (float(s_["source_in_s"]) + float(s_["source_out_s"])) / 2 <= float(b)
                                                                for a, b in lab.get(str(s_["source_name"]), []))]
        reels[key]["moments_centred_on_ground"] = len(on_ground)
        if reel and reel.is_file():
            shutil.copy2(reel, outd / f"{key}.mp4")
            contact_sheet(ff, reel, res.get("segments", []), outd / f"{key}.jpg",
                          f"{key} - {res.get('selection_mode')} {res.get('theme') or ''} - {len(res.get('segments', []))} moments")

    with app.test_client() as c:
        page = c.get("/auto/new?folder=" + urllib.parse.quote(str(folder)), headers=H).get_data(as_text=True)
        check("prepare_button_offered", "name='prepare'" in page, page[:300])
        r = c.post("/auto/create", data={"folder": str(folder), "length": "30", "format": "vertical", "sound": "auto",
                                         "mode": "semantic_plus", "theme": THEME, "prepare": "1"}, headers=H)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1]) if r.status_code == 302 else None
        check("prepare_project_created", pid, (r.status_code, r.data[:300]))
        if not pid:
            save(); return 1
        j, dt = wait(ae.project(pid)["jobs"][0]["id"])
        info = ae.prepared_info(j["id"]) or {}
        report["prepare"] = {"seconds": round(dt, 1), "status": j["status"], "error": j.get("error"), "info": info}
        check("prepared", j["status"] == "done" and info.get("prepared") and not j.get("revision_id")
              and ae.project(pid)["state"] == "PREPARED", (j["status"], j.get("error"), info))
        pg = c.get(f"/auto/p/{pid}", headers=H).get_data(as_text=True)
        check("prepared_card_and_build_form_shown", "Prepared in advance" in pg and f"/auto/p/{pid}/variant" in pg, pg[:300])
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"length": "30", "format": "vertical", "sound": "auto", "mode": "semantic_plus",
                                               "theme": THEME}, headers=H)
        jobs = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        if jobs:
            j, dt = wait(jobs[0]["id"])
            take("aiplus_aerial_30s_after_prepare", j, dt)
            st = (reels.get("aiplus_aerial_30s_after_prepare") or {}).get("stage_seconds") or {}
            # prepared: finding moments again is reading what is kept (seconds), not looking at the videos again
            check("build_after_prepare_reuses_analysis", float(st.get("analyze") or 0) < max(30.0, 0.15 * float(report["prepare"]["seconds"])),
                  (st, report["prepare"]["seconds"]))
        else:
            check("aiplus_aerial_30s_after_prepare_started", False, "no job")
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        base = (reels.get("aiplus_aerial_30s_after_prepare") or {}).get("revision_id")
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": base or "", "length": "30", "format": "vertical", "sound": "auto",
                                               "mode": "semantic", "theme": ""}, headers=H)
        jobs = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        if jobs:
            j, dt = wait(jobs[0]["id"])
            take("ai_30s", j, dt)
        report["reels"] = reels
        save()
    labelled = any(v.get("ground") for v in vids)
    if labelled and "aiplus_aerial_30s_after_prepare" in reels:
        check("aerial_reel_avoids_ground", reels["aiplus_aerial_30s_after_prepare"]["moments_centred_on_ground"] == 0,
              reels["aiplus_aerial_30s_after_prepare"]["moments_centred_on_ground"])
    save()
    print(json.dumps({"passed": sum(x["pass"] for x in report["checks"]), "total": len(report["checks"]), "videos": len(vids),
                      "labelled": labelled, "prepare_s": (report.get("prepare") or {}).get("seconds"),
                      "reels": {k: (v["seconds"], len(v["segments"]), v["moments_centred_on_ground"]) for k, v in reels.items()}},
                     ensure_ascii=False))
    return 0 if all(x["pass"] for x in report["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())

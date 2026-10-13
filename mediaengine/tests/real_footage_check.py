"""Reels from REAL amateur footage (public Wikimedia Commons videos with free licences) on Windows CI.

  python tests/real_footage_check.py <work_dir> --out <results_dir> [--manifest tests/real_footage_manifest.json]

Not the owner's videos (those stay on his PC) and not a quality proof - a look at what the app picks from real
people, children, beaches, animals, parties and streets instead of synthetic test patterns:
1. the videos: a pinned list (manifest) or, without one, found by a Commons search ("filetype:video" + a topic;
   only CC0 / public domain / CC BY / CC BY-SA, 6-180 s) - the list found is written to the results so it can be
   pinned; downloaded once (720p/480p transcode or the original), SHA-256 recorded;
2. both AI models downloaded like real_models_check.py (public, pinned, checked);
3. through the app routes: a 30 s reel with AI, the same with AI+, AI+ reels for the themes kids / sea / animals /
   party (15 s);
4. for every reel a contact sheet (one frame from the middle of every moment, with its source and time) and the
   moments as JSON; ATTRIBUTION.md lists every video with its author, licence and page.
Results: contact sheets + JSON + attribution (results branch); the reels themselves (CI artifact).
"""
from __future__ import annotations

import html, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402

UA = {"User-Agent": "MediaEngine-CI/1.0 (https://github.com/skynder-dev/projects; automated test, small number of requests)"}
API = "https://commons.wikimedia.org/w/api.php"
TOPICS = ["children playing", "kids beach", "family picnic", "birthday party", "wedding dance", "dog playing", "cat",
          "beach waves", "sea boat", "mountains hiking", "snow sledding", "sunset", "city street walk", "fireworks",
          "festival crowd", "cycling", "football match", "cooking food", "road trip car", "swimming pool"]
FREE = ("cc0", "public domain", "pd", "cc by ", "cc by-sa", "cc-by", "cc-by-sa", "cc by 2", "cc by 3", "cc by 4")
PER_TOPIC = 2
MAX_VIDEOS = 36


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if k == 2:
                raise
            time.sleep(5)


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def free_licence(name: str) -> bool:
    n = name.lower().strip()
    return ("nc" not in n.replace("-", " ").split() and "nd" not in n.replace("-", " ").split()
            and (n.startswith("cc0") or n.startswith("public domain") or n.startswith("pd") or n.startswith("cc by")))


def discover() -> list[dict]:
    """Commons search: per topic the first free-licence videos of a fitting length."""
    picked, seen = [], set()
    for topic in TOPICS:
        res = api({"action": "query", "generator": "search", "gsrsearch": f"filetype:video {topic}", "gsrnamespace": 6,
                   "gsrlimit": 25, "prop": "imageinfo|videoinfo", "iiprop": "url|size|mime|extmetadata|sha1",
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
            if not free_licence(lic) or not (6 <= dur <= 180):
                continue
            ders = vi.get("derivatives") or []
            pick = None
            for key in ("720p.vp9.webm", "480p.vp9.webm", "720p.webm", "480p.webm", "360p.vp9.webm"):
                pick = next((d for d in ders if str(d.get("transcodekey", "")).endswith(key)), None)
                if pick:
                    break
            src = pick.get("src") if pick else (ii.get("url") if int(ii.get("size") or 0) < 120_000_000 else None)
            if not src:
                continue
            seen.add(title)
            picked.append({"title": title, "topic": topic, "duration_s": dur, "url": src, "page": ii.get("descriptionurl"),
                           "licence": lic, "licence_url": strip_html((meta.get("LicenseUrl") or {}).get("value", "")),
                           "author": strip_html((meta.get("Artist") or {}).get("value", ""))[:200],
                           "original_sha1": ii.get("sha1")})
            n += 1
            if n >= PER_TOPIC or len(picked) >= MAX_VIDEOS:
                break
        if len(picked) >= MAX_VIDEOS:
            break
        time.sleep(1)
    return picked


def safe_name(i: int, title: str, url: str) -> str:
    base = re.sub(r"[^\w\-]+", "_", Path(title.split(":", 1)[-1]).stem)[:50].strip("_") or "video"
    ext = ".webm" if ".webm" in url.lower() else Path(urllib.parse.urlparse(url).path).suffix.lower() or ".webm"
    return f"{i:02d}_{base}{ext}"


def download(items: list[dict], folder: Path) -> list[dict]:
    import hashlib
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, it in enumerate(items, 1):
        dst = folder / safe_name(i, it["title"], it["url"])
        try:
            if not dst.exists():
                tmp = dst.with_name(dst.name + ".part")
                with urllib.request.urlopen(urllib.request.Request(it["url"], headers=UA), timeout=180) as r, tmp.open("wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
                os.replace(tmp, dst)
            h = hashlib.sha256(dst.read_bytes()).hexdigest()
            if it.get("sha256") and it["sha256"] != h:
                print("SKIP changed file:", it["title"]); dst.unlink(); continue
            out.append({**it, "file": dst.name, "sha256": h, "bytes": dst.stat().st_size})
        except Exception as exc:
            print("SKIP not downloaded:", it["title"], exc)
        time.sleep(0.5)
    return out


def contact_sheet(ff: str, reel: Path, segments: list[dict], out: Path, title: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    tw, th = 216, 384
    cols = min(6, max(1, len(segments)))
    rows = -(-len(segments) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 44) + 40), (18, 20, 26))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    d.text((8, 10), title, fill=(240, 240, 240), font=font)
    for k, s in enumerate(segments):
        t = (float(s["reel_in_s"]) + float(s["reel_out_s"])) / 2
        cp = subprocess.run([ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(reel), "-frames:v", "1", "-vf", f"scale={tw}:{th}",
                             "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        x, y = (k % cols) * tw, 40 + (k // cols) * (th + 44)
        if cp.stdout:
            import io
            sheet.paste(Image.open(io.BytesIO(cp.stdout)).convert("RGB").resize((tw, th)), (x, y))
        name = re.sub(r"^\d+_", "", str(s["source_name"]))[:26]
        d.text((x + 4, y + th + 4), f"{k + 1}. {name}", fill=(230, 230, 230), font=font)
        d.text((x + 4, y + th + 22), f"{float(s['source_in_s']):.1f}-{float(s['source_out_s']):.1f} s", fill=(160, 170, 185), font=font)
    sheet.save(out, quality=88)


def main():
    work = Path(sys.argv[1]).resolve()
    outd = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    manifest = Path(sys.argv[sys.argv.index("--manifest") + 1]) if "--manifest" in sys.argv else HERE / "real_footage_manifest.json"
    outd.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    report = {"checks": [], "timings": {}}

    def check(name, ok, detail=None):
        report["checks"].append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def save():
        (outd / "real_footage.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # 1. the videos
    t0 = time.time()
    items = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else discover()
    report["source"] = "pinned manifest" if manifest.is_file() else "Commons search"
    vids = download(items, work / "Commons videos")
    report["videos"] = vids
    report["timings"]["download_s"] = round(time.time() - t0, 1)
    (outd / "real_footage_manifest.json").write_text(json.dumps([{k: v for k, v in x.items() if k not in ("file", "bytes")} for x in vids],
                                                               indent=2, ensure_ascii=False), encoding="utf-8")
    att = ["# Videos used (Wikimedia Commons, free licences)", "",
           "Used only to test MediaEngine; the contact sheets and reels are made from them.", ""]
    for v in vids:
        att.append(f"- **{v['title']}** — {v['author'] or 'unknown author'} — {v['licence']} ({v['licence_url'] or 'see page'}) — {v['page']}")
    (outd / "ATTRIBUTION.md").write_text("\n".join(att) + "\n", encoding="utf-8")
    check("enough_real_videos", len(vids) >= 12, len(vids))
    save()
    if len(vids) < 6:
        return 1

    # 2. models (the same public, pinned files as real_models_check.py)
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
    ae.aiplus_download_start()
    while ae._AIPLUS_DL["state"] == "running" and time.time() - t0 < 900:
        time.sleep(2)
    check("models_ready", ae.model_status()["ready"] and ae.aiplus_status()["ready"], (ae.model_status(), ae._AIPLUS_DL))

    # 3. reels through the app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    folder = work / "Commons videos"

    def wait(jid, limit=5400):
        t = time.time()
        while time.time() - t < limit and ae.job(jid)["status"] in ("queued", "running"):
            time.sleep(2)
        return ae.job(jid), time.time() - t

    reels = {}
    with app.test_client() as c:
        r = c.post("/auto/create", data={"folder": str(folder), "length": "30", "format": "vertical", "sound": "auto", "mode": "semantic"}, headers=H)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1]) if r.status_code == 302 else None
        check("project_created", pid, (r.status_code, r.data[:300]))
        if not pid:
            save(); return 1
        plan = [("ai_30s", {"length": "30", "mode": "semantic"}), ("aiplus_30s", {"length": "30", "mode": "semantic_plus"})] + \
               [(f"aiplus_{t}_15s", {"length": "15", "mode": "semantic_plus", "theme": t}) for t in ("kids", "sea", "animals", "party")]
        first = True
        for key, s in plan:
            before = {x["id"] for x in ae.project(pid)["jobs"]}
            if not first:
                base = next(iter(reels.values()))["revision_id"] if reels else None
                c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": base or "", "format": "vertical", "sound": "auto", **s}, headers=H)
            jobs = [x for x in ae.project(pid)["jobs"] if x["id"] not in before] if not first else [ae.project(pid)["jobs"][0]]
            first = False
            if not jobs:
                check(f"{key}_started", False, "no job"); continue
            j, dt = wait(jobs[0]["id"])
            rev = ae.revision(j.get("revision_id") or 0) if j["status"] == "done" else None
            check(f"{key}_built", rev is not None, (j["status"], j.get("error")))
            if not rev:
                continue
            res = rev["result"]
            reel = Path(rev["video_path"]) if rev.get("video_path") else None
            if not reel or not reel.is_file():
                reel = next((Path(x) for x in (rev.get("path"), rev.get("video")) if x and Path(x).is_file()), None)
            reels[key] = {"revision_id": rev["id"], "seconds": round(dt, 1), "selection_mode": res.get("selection_mode"),
                          "theme": res.get("theme"), "warnings": res.get("warnings"), "stage_seconds": res.get("stage_seconds"),
                          "duration_s": res.get("actual_duration_s"),
                          "segments": [{k: s_[k] for k in ("source_name", "source_in_s", "source_out_s", "reel_in_s", "reel_out_s", "score")}
                                       for s_ in res.get("segments", [])]}
            if reel and reel.is_file():
                shutil.copy2(reel, outd / f"{key}.mp4")
                contact_sheet(ff, reel, res.get("segments", []), outd / f"{key}.jpg",
                              f"{key} - {res.get('selection_mode')} {res.get('theme') or ''} - {len(res.get('segments', []))} moments")
            report["reels"] = reels
            save()
    check("all_reels_built", len(reels) == len(plan), sorted(reels))
    save()
    print(json.dumps({"passed": sum(x["pass"] for x in report["checks"]), "total": len(report["checks"]),
                      "videos": len(vids), "reels": {k: (v["seconds"], len(v["segments"])) for k, v in reels.items()}}, ensure_ascii=False))
    return 0 if all(x["pass"] for x in report["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())

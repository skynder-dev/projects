"""The real AI models on Windows CI, through the app (needs internet once for the downloads; not an AI quality test).

  python tests/real_models_check.py <fixtures_dir> <home_dir> [--out report.json]

1. FAST_LOCAL (the accepted AI model) is downloaded from its public, pinned Hugging Face commit - the exact files the
   engine checks by SHA-256 - and the AI+ model (PE-Core L/14) is downloaded with the app's own "Download AI+ model"
   code (the button on Check this PC).
2. "Check this PC" test reels with AI and with AI+ (the real engine, semantic=required).
3. A reel from the 7-video folder with AI+ through the app routes, then an AI variant of the same project, and a blind
   comparison of the two - the way the owner compares them. Analysis times are recorded.
"""
from __future__ import annotations

import json, os, shutil, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAST_REPO = "onnx-community/TinyCLIP-ViT-8M-16-Text-3M-YFCC15M-ONNX"
FAST_REV = "9463a9c508a344c837ffefe9d724f3827bf2dc79"
FAST_SUPPORT = ("config.json", "merges.txt", "preprocessor_config.json", "special_tokens_map.json", "tokenizer.json",
                "tokenizer_config.json", "vocab.json")


def fetch(url: str, dst: Path, tries: int = 3) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MediaEngine-CI"}), timeout=120) as r, tmp.open("wb") as fh:
                shutil.copyfileobj(r, fh, 1 << 20)
            os.replace(tmp, dst)
            return
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(10)


def main():
    fx, home = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out_json = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist import auto_edit as ae
    checks, timings = [], {}

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:800]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    # 1. models
    fast = home / "models" / "FAST_LOCAL"
    t0 = time.time()
    fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/onnx/model_int8.onnx", fast / "model_int8.onnx")
    for n in FAST_SUPPORT:
        fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/{n}", fast / f"support_{FAST_REV}" / n)
    timings["download_fast_local_s"] = round(time.time() - t0, 1)
    ms = ae.model_status()
    check("fast_local_from_public_commit_is_the_exact_model", ms["ready"], ms)
    t0 = time.time()
    for _attempt in range(2):                       # the app's own download (one retry: a network hiccup is not a bug)
        ae.aiplus_download_start()
        while ae._AIPLUS_DL["state"] == "running" and time.time() - t0 < 1800:
            time.sleep(2)
        if ae._AIPLUS_DL["state"] == "done":
            break
        print("AI+ download attempt failed:", ae._AIPLUS_DL.get("error"))
    timings["download_aiplus_s"] = round(time.time() - t0, 1)
    ap = ae.aiplus_status()
    check("aiplus_downloaded_by_the_app_and_verified", ap["ready"] and ae._AIPLUS_DL["state"] == "done", (ap, ae._AIPLUS_DL))

    # 2. Check this PC test reels
    for mode, prefix in (("semantic", "FAST_LOCAL"), ("semantic_plus", "PE_CORE")):
        t = ae.quick_selftest(mode=mode, timeout_s=1800)
        timings[f"test_reel_{mode}_s"] = t.get("seconds")
        check(f"test_reel_{mode}", t["ok"] and str(t.get("selection_mode", "")).startswith(prefix), (t.get("error"), t.get("selection_mode")))

    # 3. a real project: AI+ first, then an AI variant, then a blind comparison
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    src = home.parent / "real_models_videos"
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(fx / "seven", src)

    def wait(jid, limit=3600):
        t0 = time.time()
        while time.time() - t0 < limit:
            j = ae.job(jid)
            if j["status"] in ("done", "failed", "cancelled"):
                return j, time.time() - t0
            time.sleep(1)
        return ae.job(jid), time.time() - t0

    with app.test_client() as c:
        page = c.get("/auto/new", query_string={"folder": str(src)}, headers=H).data.decode("utf-8", "replace")
        check("setup_offers_ai_and_aiplus", "value='semantic'" in page and "value='semantic_plus'" in page)
        r = c.post("/auto/create", data={"folder": str(src), "length": "15", "format": "social_hd", "sound": "auto", "mode": "semantic_plus"}, headers=H)
        ok = r.status_code == 302 and "/auto/p/" in r.headers.get("Location", "")
        check("aiplus_project_created", ok, r.status_code)
        if not ok:
            return finish(checks, timings, out_json)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        j, dt = wait(ae.project(pid)["jobs"][0]["id"])
        timings["aiplus_first_build_s"] = round(dt, 1)
        rev = ae.revision(j.get("revision_id") or 0) if j["status"] == "done" else None
        check("aiplus_reel_built", rev and rev["result"].get("selection_mode") == "PE_CORE_L14_SEMANTIC_V1", (j.get("status"), j.get("error")))
        timings["aiplus_stage_seconds"] = (rev or {}).get("result", {}).get("stage_seconds")
        if not rev:
            return finish(checks, timings, out_json)
        r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev["id"], "length": "15", "format": "social_hd", "sound": "auto",
                                                   "mode": "semantic"}, headers=H)
        jobs = [x for x in ae.project(pid)["jobs"] if x["id"] != j["id"]]
        j2, dt2 = wait(jobs[0]["id"]) if jobs else ({"status": "missing"}, 0)
        timings["ai_variant_build_s"] = round(dt2, 1)
        timings["ai_stage_seconds"] = (ae.revision(j2.get("revision_id") or 0) or {}).get("result", {}).get("stage_seconds") if j2.get("revision_id") else None
        rev2 = ae.revision(j2.get("revision_id") or 0) if j2.get("status") == "done" else None
        check("ai_variant_of_the_same_project", rev2 and rev2["result"].get("selection_mode", "").startswith("FAST_LOCAL"),
              (j2.get("status"), j2.get("error")))
        page = c.get(f"/auto/p/{pid}", query_string={"rev": rev["id"]}, headers=H).data.decode("utf-8", "replace")
        check("review_says_aiplus", "AI+ moments (PE-Core L/14)" in page)
        if rev2:
            r = c.post(f"/auto/p/{pid}/compare", data={"a": rev["id"], "b": rev2["id"]}, headers=H)
            check("blind_compare_ai_vs_aiplus_starts", r.status_code == 302 and "/auto/review/" in r.headers.get("Location", ""), r.status_code)
            m1 = {s["source_name"] for s in rev["result"]["segments"]}
            m2 = {s["source_name"] for s in rev2["result"]["segments"]}
            timings["aiplus_sources"] = sorted(m1)
            timings["ai_sources"] = sorted(m2)
    return finish(checks, timings, out_json)


def finish(checks, timings, out_json):
    out = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "timings": timings, "checks": checks}
    if out_json:
        out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("passed", "total", "timings")}, ensure_ascii=False))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

"""Library through the app routes, like a user: add a folder, import + analyse its videos, mark one Private.

  python tests/library_flow_check.py <fixtures_dir> <work_dir>

- a folder added on the Import page is scanned: every video in it is listed (names with ' [ ] and Cyrillic);
- "Import + analyse" finishes; the videos are in the Library with thumbnails and an item page; a screen recording
  without a written length gets its real length;
- a video marked Private leaves the Library, its original stays where it was, unchanged (a local folder is only
  read), and a reel built from that folder never uses it;
- the Library pages render in Russian too; no source file is changed by any of this;
- the data folder itself has Cyrillic letters (as under the Windows user folder of a Cyrillic user name), so previews, caches and the reel
  engine's work folder are all checked under such a path.
"""
from __future__ import annotations

import hashlib, html, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    # the data folder has Cyrillic letters too (C:\Users\Дмитрий\MediaEngine\... on a PC without D:\Archivist):
    # previews, caches and the reel engine's work folder all live under it
    os.environ["ARCHIVIST_HOME"] = str(work / "Данные пользователя")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    from media_measure import ffmpeg_exe
    src = work / "Мои видео 'тест' [1]"
    src.mkdir()
    for f in sorted((fx / "two").glob("*.mp4"))[:2]:
        shutil.copy2(f, src / f.name)
    phone = fx / "phone" / "IMG_0042.MOV"
    if phone.exists():
        shutil.copy2(phone, src / "Отпуск [пляж] 'день 2'.MOV")
    rec = src / "screen recording.webm"
    with rec.open("wb") as fh:
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25,hue=h=t*40", "-t", "6",
                        "-c:v", "libvpx", "-deadline", "realtime", "-b:v", "500k", "-live", "1", "-f", "webm", "pipe:1"], stdout=fh, check=False)
    if rec.stat().st_size < 2000:
        rec.unlink()
        print("SKIP recording without a length: this ffmpeg cannot write WebM")
    before = {p.name: sha(p) for p in src.iterdir()}
    names = sorted(before)

    from archivist.web import create_app
    from archivist.db import db
    from archivist import service, auto_edit as ae
    app = create_app()
    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def rows():
        with db() as con:
            return [dict(r) for r in con.execute("SELECT * FROM inventory WHERE path LIKE ? ORDER BY filename", (str(src) + "%",)).fetchall()]

    def wait_job(jid, limit=900):
        t0 = time.time()
        while time.time() - t0 < limit:
            with db() as con:
                j = dict(con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone())
            if j["status"] in ("finished", "partial", "failed", "cancelled"):
                return j
            time.sleep(1)
        return j

    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    with app.test_client() as c:
        r = c.post("/import/add-source", data={"path": str(src), "label": "Мои тестовые видео"}, headers=H)
        check("add_folder_source", r.status_code == 302, r.status_code)
        t0 = time.time()
        while time.time() - t0 < 180 and (len(rows()) < len(names) or service.DISCOVERY_LOCK.locked()):
            if not service.DISCOVERY_LOCK.locked() and len(rows()) < len(names):
                service.start_discovery()
            time.sleep(1)
        found = sorted(r_["filename"] for r_ in rows())
        check("every_video_found", found == names, (found, names))
        r = c.get("/import", query_string={"source_kind": "fixed"}, headers=H)
        page = html.unescape(r.data.decode("utf-8", "replace"))
        check("import_page_lists_them", r.status_code == 200 and all(n in page for n in names), r.status_code)

        ids = [r_["id"] for r_ in rows()]
        r = c.post("/api/selection-action", json={"action": "import_analyze", "ids": ids}, headers=H)
        jid = (r.get_json() or {}).get("job_id")
        check("import_analyse_started", r.status_code == 200 and jid, r.data[:300])
        j = wait_job(jid) if jid else {}
        check("import_analyse_finished", j.get("status") == "finished", (j.get("status"), j.get("message"), j.get("error")))
        inv = {r_["filename"]: r_ for r_ in rows()}
        check("all_in_working_set_and_analysed", all(r_["work_selected"] == 1 and r_.get("analysis_version") == 4 for r_ in inv.values()),
              [(k, v["work_selected"], v.get("analysis_version"), v.get("analysis_status"), v.get("error")) for k, v in inv.items()])
        check("library_knows_every_length", all(int(r_.get("duration_ms") or 0) > 2000 for r_ in inv.values()),
              [(k, v.get("duration_ms")) for k, v in inv.items()])
        if rec.exists():     # a screen recording without a written length: analysed and cut into clips like any video
            rr = inv.get(rec.name, {})
            r = c.post("/api/selection-action", json={"action": "media_brain", "ids": [rr.get("id")]}, headers=H)
            mj = wait_job((r.get_json() or {}).get("job_id") or 0, 600)
            with db() as con:
                spans = [tuple(x) for x in con.execute("SELECT start_ms,end_ms FROM virtual_clips WHERE inventory_id=?", (rr.get("id"),)).fetchall()]
            check("recording_without_length_analysed_and_clipped", rr.get("quality_status") == "ok" and not rr.get("error")
                  and mj.get("status") == "finished" and spans and max(e for _, e in spans) >= 4000,
                  (rr.get("quality_status"), rr.get("error"), mj.get("status"), mj.get("message"), spans))
        r = c.get("/library", headers=H)
        page = html.unescape(r.data.decode("utf-8", "replace"))
        check("library_lists_them", r.status_code == 200 and all(n in page for n in names), r.status_code)
        thumbs_ok = []
        for n, r_ in inv.items():
            ok = False
            for _ in range(60):
                t = c.get(f"/thumb/{r_['id']}", headers=H)
                if t.status_code == 200 and t.mimetype.startswith("image/") and len(t.data) > 500:
                    ok = True
                    break
                time.sleep(1)
            thumbs_ok.append((n, ok))
        check("thumbnails", all(ok for _, ok in thumbs_ok), thumbs_ok)
        bad_items = [n for n, r_ in inv.items() if c.get(f"/item/{r_['id']}", headers=H).status_code != 200]
        check("item_pages", not bad_items, bad_items)

        # mark one Private: it leaves the Library, the original stays, a reel never uses it
        priv = inv[names[0]]
        r = c.post("/api/selection-action", json={"action": "private", "ids": [priv["id"]]}, headers=H)
        pj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
        after = {r_["filename"]: r_ for r_ in rows()}.get(names[0], {})
        check("private_job_finished", pj.get("status") == "finished" and after.get("analysis_status") == "private", (pj.get("status"), after.get("analysis_status")))
        page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
        check("private_left_the_library", names[0] not in page and names[1] in page)
        check("private_original_stays_unchanged", (src / names[0]).is_file() and sha(src / names[0]) == before[names[0]])
        r = c.post("/auto/create", data={"folder": str(src), "length": "5", "format": "vertical", "sound": "auto", "mode": "technical"}, headers=H)
        okc = r.status_code == 302 and "/auto/p/" in r.headers.get("Location", "")
        check("reel_from_the_same_folder_starts", okc, r.status_code)
        if okc:
            pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
            jid2 = ae.project(pid)["jobs"][0]["id"]
            t0 = time.time()
            while time.time() - t0 < 900 and ae.job(jid2)["status"] in ("queued", "running"):
                time.sleep(1)
            aj = ae.job(jid2)
            rv = ae.revision(aj.get("revision_id") or 0) if aj["status"] == "done" else None
            used = {s["source_name"] for s in (rv or {}).get("result", {}).get("segments", [])}
            check("reel_never_uses_the_private_video", rv and used and names[0] not in used, (aj["status"], aj.get("error"), used))

        # archive a copy (Cyrillic names must survive), reject another: originals stay where they are, unchanged
        from archivist.config import load_config, save_config
        cfg = load_config(); cfg["archive_root"] = str(work / "Архив"); save_config(cfg)
        cyr = next((n for n in names if not n.isascii()), None)
        if cyr:
            r = c.post("/api/selection-action", json={"action": "archive", "ids": [inv[cyr]["id"]]}, headers=H)
            aj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
            arow = {r_["filename"]: r_ for r_ in rows()}.get(cyr, {})
            ap = Path(arow.get("archive_path") or "")
            check("archive_copy_keeps_the_names", aj.get("status") == "finished" and ap.is_file() and ap.name == cyr
                  and ap.parent.name == "Мои тестовые видео" and sha(ap) == before[cyr] and sha(src / cyr) == before[cyr],
                  (aj.get("status"), str(ap)))
        if rec.exists():
            r = c.post("/api/selection-action", json={"action": "reject", "ids": [inv[rec.name]["id"]]}, headers=H)
            rj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
            page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
            check("rejected_leaves_the_library_original_kept", rj.get("status") == "finished" and rec.name not in page
                  and sha(rec) == before[rec.name], rj.get("status"))

        # the same pages in Russian
        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = {u: c.get(u, headers=H) for u in ("/library", "/import?source_kind=fixed", f"/item/{inv[names[1]]['id']}", "/jobs", "/media")}
        check("library_pages_in_russian", all(x.status_code == 200 and "<html lang='ru'>" in x.data.decode("utf-8", "replace") for x in ru.values()),
              {u: x.status_code for u, x in ru.items()})
        c.post("/lang", data={"lang": "en"}, headers=H)

    service.STOP_EVENT.set()
    now = {p.name: sha(p) for p in src.iterdir() if p.is_file()}
    check("sources_unchanged", now == before, sorted(set(now.items()) ^ set(before.items()))[:4])
    out = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks}
    (work / "library_flow.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"]}))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

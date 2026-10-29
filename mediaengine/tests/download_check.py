"""Checks of "Download by a link" (downloader.py, download_web.py) with a stand-in yt-dlp (fake_ytdlp.py): no network.

  python tests/download_check.py <work_dir>   -> JSON with passed / total; exit 1 when a check fails

Install with the button (the files served by a stand-in fetch: a wrong checksum refused), a video and a profile looked
at, chosen videos downloaded into the Downloaded folder with their progress, studied after (Cartoon Studio), a private
video and a site asking to sign in said plainly, too many videos refused, Stop and Try again, the page in Russian.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS: list = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {str(detail)[:600]}"), flush=True)


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(HERE.parent / "app"))
    from archivist import auto_edit as ae, downloader as D, voice as vo
    from archivist.web import create_app
    ff = vo._ffmpeg()
    clip = work / "clip.mp4"
    subprocess.run([ff, "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x568:d=4:r=25", "-f", "lavfi", "-i",
                    "sine=frequency=500:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip)],
                   check=True, capture_output=True, timeout=120)
    os.environ["FAKE_YTDLP_VIDEO"] = str(clip)
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}

    def wait_job(jid, limit=120):
        t0 = time.time()
        while time.time() - t0 < limit:
            j = D.read_job(jid)
            if j["state"] not in ("working", "waiting"):
                return j
            time.sleep(0.2)
        return D.read_job(jid)

    with app.test_client() as c:
        # 1. install with the button: yt-dlp and deno from their releases (here a stand-in fetch), checksums checked
        home0 = c.get("/media/download", headers=H).get_data(as_text=True)
        ydl, dz = b"MZ fake yt-dlp " * 1000, io.BytesIO()
        with zipfile.ZipFile(dz, "w") as z:
            z.writestr("deno.exe", b"MZ fake deno " * 2000)
        served = {D.YTDLP["url"]: ydl, D.DENO["url"]: dz.getvalue()}
        real = (ae._fetch_resumable, D._version, dict(D.YTDLP), dict(D.DENO))

        def fetch(url, part, size, progress, tries=4, stop=None):
            data = served[url]
            Path(part).write_bytes(data)
            progress(len(data))
        ae._fetch_resumable = fetch
        D._version = lambda exe: "2026.10.26"
        D.YTDLP.update(size=len(ydl), sha256="0" * 64)            # a wrong checksum first
        D.DENO.update(size=len(dz.getvalue()), sha256=hashlib.sha256(dz.getvalue()).hexdigest())
        try:
            c.post("/media/download/install", headers=H)
            t0 = time.time()
            while D.INSTALL["state"] == "running" and time.time() - t0 < 30:
                time.sleep(0.1)
            bad = dict(D.INSTALL)
            D.YTDLP.update(sha256=hashlib.sha256(ydl).hexdigest())
            c.post("/media/download/install", headers=H)
            t0 = time.time()
            while D.INSTALL["state"] == "running" and time.time() - t0 < 30:
                time.sleep(0.1)
            good = dict(D.INSTALL)
            inst_ok = D.installed() and (D.ROOT / "deno.exe").read_bytes().startswith(b"MZ fake deno")
            man = json.loads((D.ROOT / "addon.json").read_text("utf-8"))
        finally:
            ae._fetch_resumable, D._version = real[0], real[1]
            D.YTDLP.clear(); D.YTDLP.update(real[2]); D.DENO.clear(); D.DENO.update(real[3])
        check("install with the button: a file with a wrong checksum refused; then yt-dlp and deno in the data folder",
              "Install the downloader" in home0 and bad["state"] == "failed" and "checksum" in bad["error"] and good["state"] == "done"
              and inst_ok and man.get("version") == "2026.10.26", (bad, good, inst_ok))

        # the stand-in yt-dlp from here on
        os.environ["MEDENG_YTDLP"] = f"{sys.executable}|{HERE / 'fake_ytdlp.py'}"
        home1 = c.get("/media/download", headers=H).get_data(as_text=True)
        one = c.post("/media/download/look", data={"url": "https://www.youtube.com/watch?v=one001"}, headers=H).get_data(as_text=True)
        prof = c.post("/media/download/look", data={"url": "https://www.youtube.com/@fakecartoons/videos"}, headers=H)
        ptxt = prof.get_data(as_text=True)
        check("a link: one video shown with its title; a profile listed (title, length, views) with quick choices",
              "A link" in home1 and "Show the videos" in home1 and "One cartoon about roads" in one and "Download" in one
              and prof.status_code == 200 and ptxt.count("name='pick'") == 35 and "Episode 34 - how a city pays twice" in ptxt
              and "The 10 most viewed" in ptxt and "The first 10" in ptxt, (prof.status_code, ptxt.count("name='pick'")))
        bot = c.post("/media/download/look", data={"url": "https://www.youtube.com/watch?v=bot1"}, headers=H)
        bad_url = c.post("/media/download/look", data={"url": "ftp://example.com/x"}, headers=H)
        check("a site asking to sign in, and a link that is not a web address, are said plainly",
              bot.status_code == 400 and b"took the program for a robot" in bot.data and bad_url.status_code == 400
              and b"starts with https://" in bad_url.data, (bot.status_code, bad_url.status_code))

        # 2. three chosen videos downloaded, each then studied for its rhythm (Cartoon Studio)
        form = {"source": "https://www.youtube.com/@fakecartoons/videos", "author": "Fake Cartoons", "study": "1", "pick": ["0", "3", "7"]}
        for n in (0, 3, 7):
            form[f"u{n}"] = f"https://www.youtube.com/watch?v=vid{n:03d}"
            form[f"t{n}"] = f"Episode {n}"
        st = c.post("/media/download/start", data=form, headers=H)
        jid = D.list_jobs()[0]["id"]
        j = wait_job(jid)
        files = [Path(f["file"]) for f in (j.get("result") or {}).get("files") or []]
        studies = [x for x in vo.list_jobs(50) if x.get("kind") == "cartoon_study"]
        t0 = time.time()                                    # (the studies themselves: writer_check; here they finish)
        while any(vo.read_job(x["id"])["state"] in ("waiting", "working") for x in studies) and time.time() - t0 < 240:
            time.sleep(0.3)
        page = c.get("/media/download", headers=H).get_data(as_text=True)
        check("three chosen videos downloaded into the Downloaded folder, each studied for its rhythm after; the page offers "
              "to study, retell or show each",
              st.status_code == 302 and j["state"] == "done" and len(files) == 3 and all(p.is_file() for p in files)
              and all(p.parent == D.folder() for p in files) and len(studies) == 3
              and page.count("Study its rhythm") == 3 and "Write a story from it" in page and "Show in folder" in page,
              (j["state"], j.get("result"), len(studies)))

        # their common style (an author's), from the download's row; pressed twice: still one
        from archivist.cartoon import reference as R
        frm = re.search(r"<form method='post' action='/auto/cartoon/style/new'.*?</form>", page, re.S)
        fields: dict = {}
        for k, v in re.findall(r"<input type='hidden' name='(\w+)' value='([^']*)'>", frm.group(0) if frm else ""):
            fields.setdefault(k, []).append(v)
        mk1 = c.post("/auto/cartoon/style/new", data=fields, headers=H)
        mk2 = c.post("/auto/cartoon/style/new", data=fields, headers=H)
        sts = R.styles()
        page_s = c.get("/media/download", headers=H).get_data(as_text=True)
        check("the three studied: their common style made from the download's row (the author's name, the three videos), "
              "pressed twice still one; the row then links it",
              "Fake Cartoons</span> · <span translate='no'>3</span> <span>videos</span>" in page and "Studied:" in page and frm is not None
              and mk1.status_code == 302 and mk2.headers.get("Location") == mk1.headers.get("Location") and len(sts) == 1
              and sts[0]["name"] == "Fake Cartoons" and len(sts[0]["refs"]) == 3 and sts[0]["source"] == f"download:{jid}"
              and "Their common style" in page_s and f"/auto/cartoon/style/{sts[0]['id']}" in page_s
              and R.author_style(sts[0]["id"]).get("videos") == 3,
              (frm is not None, mk1.status_code, mk1.headers.get("Location"), mk2.headers.get("Location"), sts))

        # 3. a private video among them: said plainly, the others downloaded; Try again
        form2 = {"pick": ["0", "1"], "u0": "https://www.youtube.com/watch?v=private1", "t0": "Secret",
                 "u1": "https://www.youtube.com/watch?v=vid010", "t1": "Episode 10"}
        c.post("/media/download/start", data=form2, headers=H)
        j2 = wait_job(D.list_jobs()[0]["id"])
        r2 = j2.get("result") or {}
        check("a private video is said plainly (not public), the other one downloaded",
              len(r2.get("files") or []) == 1 and len(r2.get("errors") or []) == 1
              and "not public" in r2["errors"][0]["error"], r2)

        # 4. too many at once refused; Stop and Try again
        many = {"pick": [str(n) for n in range(D.MAX_VIDEOS + 1)]}
        for n in range(D.MAX_VIDEOS + 1):
            many[f"u{n}"] = f"https://www.youtube.com/watch?v=v{n:03d}"
        too = c.post("/media/download/start", data=many, headers=H)
        os.environ["FAKE_YTDLP_SLOW"] = "1"
        c.post("/media/download/start", data={"pick": ["0", "1"], "u0": "https://www.youtube.com/watch?v=slow01",
                                               "u1": "https://www.youtube.com/watch?v=slow02"}, headers=H)
        sid = D.list_jobs()[0]["id"]
        t0 = time.time()
        while D.read_job(sid)["state"] != "working" and time.time() - t0 < 10:
            time.sleep(0.05)
        time.sleep(0.8)
        c.post(f"/media/download/{sid}/stop", headers=H)
        js = wait_job(sid)
        os.environ.pop("FAKE_YTDLP_SLOW")
        c.post(f"/media/download/{sid}/retry", headers=H)
        jr = wait_job(sid)
        check("too many at once refused; Stop ends a download, Try again finishes it",
              too.status_code == 400 and b"At most" in too.data and js["state"] == "stopped"
              and jr["state"] == "done" and len((jr.get("result") or {}).get("files") or []) == 2, (too.status_code, js["state"], jr["state"]))

        # 5. the page in Russian: no English left; a video with a Russian title into the Russian folder name
        c.post("/lang", data={"lang": "ru"}, headers=H)
        os.environ["FAKE_YTDLP_TITLE"] = "Как город платит дважды"
        c.post("/media/download/start", data={"pick": ["0"], "u0": "https://www.youtube.com/watch?v=ruvid1", "t0": "Как город"}, headers=H)
        jru = wait_job(D.list_jobs()[0]["id"])
        os.environ.pop("FAKE_YTDLP_TITLE")
        fru = [Path(f["file"]) for f in (jru.get("result") or {}).get("files") or []]
        check("a video with a Russian title, downloaded into the Russian-named folder (Скачанные), is found and kept",
              jru["state"] == "done" and len(fru) == 1 and fru[0].is_file() and "Как город платит дважды" in fru[0].name
              and fru[0].parent.name == "Скачанные", (jru["state"], jru.get("result")))
        ru = (c.get("/media/download", headers=H).get_data(as_text=True)
              + c.post("/media/download/look", data={"url": "https://www.youtube.com/@fakecartoons/videos"}, headers=H).get_data(as_text=True)
              + c.get("/media", headers=H).get_data(as_text=True))
        body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
        body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
        txt = re.sub(r"<[^>]+>", "\n", body)
        left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                       and x.strip() not in ("MediaEngine", "Social Lab", "JSON", "YouTube", "TikTok") and "querySelectorAll" not in x})
        ph = [p for p in re.findall(r"placeholder='([^']*)'", ru) if not re.search(r"[А-Яа-я]", p)]
        check("pages: in Russian, no English left (the download page, a profile's list, the Media page)", not left and not ph, (left[:12], ph))
        c.post("/lang", data={"lang": "en"}, headers=H)

        # 6. delete a download from the list: its videos stay
        c.post(f"/media/download/{jid}/delete", headers=H)
        check("a download removed from the list: its videos stay in the folder", not (D.JOBS / jid).exists() and all(p.is_file() for p in files), "")

    passed = sum(1 for r in RESULTS if r["ok"])
    out = {"passed": passed, "total": len(RESULTS)}
    (work / "download_check.json").write_text(json.dumps({**out, "checks": RESULTS}, indent=1), "utf-8")
    print(json.dumps(out))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())

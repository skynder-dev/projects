"""Cartoon Studio's story writer (cartoon/writer.py) without its model: the installation (downloads checked, the
server unpacked and started for a test), stories written from a topic, from a text and retold for another country,
a broken answer asked again, Stop, the processor when the graphics card fails, the pages in both languages, removal.
A stand-in for llama.cpp's server (fake_llama_server.py) answers with fixed stories; the real model is checked in
mediaengine-writer-addon.yml.

  python tests/writer_check.py <work_dir>        -> JSON with passed / total; exit 1 when a check fails
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wait(vo, jid: str, limit: float = 300) -> dict:
    t0 = time.time()
    while vo.read_job(jid)["state"] in ("waiting", "working") and time.time() - t0 < limit:
        time.sleep(0.3)
    return vo.read_job(jid)


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    os.environ.setdefault("MEDIAENGINE_NO_BROWSER", "1")
    os.environ.setdefault("MEDIAENGINE_UPDATES", "off")
    os.environ["MEDENG_WRITER_SERVER"] = f"{sys.executable}|{HERE / 'fake_llama_server.py'}"
    os.environ["FAKE_LLAMA_RECORD"] = str(work / "asked")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import auto_edit as ae, voice as vo
    from archivist.cartoon import textscript as T, writer as W

    # the downloads: a llama.cpp zip and a model file made here, served by a stand-in for the download
    dl = work / "downloads"
    dl.mkdir()
    znames = {"vulkan": "llama-b9999-bin-win-vulkan-x64.zip", "cpu": "llama-b9999-bin-win-cpu-x64.zip"}
    for build, zn in znames.items():
        with zipfile.ZipFile(dl / zn, "w") as z:
            z.writestr("llama-server.exe", b"MZ stand-in " + build.encode())
            z.writestr(f"ggml-{build}.dll", b"stand-in")
    (dl / "Test-Q8_0.gguf").write_bytes(b"GGUF" + os.urandom(4096))
    W.LLAMA.clear()
    W.LLAMA.update(tag="b9999", builds={b: {"name": zn, "size": (dl / zn).stat().st_size, "sha256": sha(dl / zn)}
                                        for b, zn in znames.items()})
    W.MODEL.update(repo="test/Test-GGUF", rev="0123abc", file="Test-Q8_0.gguf", size=(dl / "Test-Q8_0.gguf").stat().st_size,
                   sha256=sha(dl / "Test-Q8_0.gguf"))
    asked_urls = []
    broken = {"on": False}

    def fetch(url, part, size, progress, tries=4, stop=None):
        asked_urls.append(url)
        data = (dl / url.rsplit("/", 1)[-1]).read_bytes()
        if broken["on"]:
            data = data[:-1] + b"!"
        Path(part).write_bytes(data)
        progress(len(data))
    ae._fetch_resumable = fetch

    from archivist.web import create_app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    with app.test_client() as c:
        home = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        no = c.post("/auto/cartoon/write", data={"about": "Why a hospital pays more"}, headers=H)
        check("not installed: the page offers both models (the smaller first on a PC with no known graphics card), "
              "the data folder; writing is refused",
              "Install with" in home and "Qwen3-14B" in home and 0 < home.find("Qwen3-4B") < home.find("Qwen3-14B")
              and str(W.ROOT) in home and no.status_code == 400 and b"Install the story writer first" in no.data, (no.status_code,))

        broken["on"] = True
        c.post("/auto/cartoon/writer/install", headers=H)
        t0 = time.time()
        while W.installing() and time.time() - t0 < 60:
            time.sleep(0.2)
        bad = W.status()
        check("installation: a download that is not the exact file is refused, nothing installed",
              bad["state"] == "failed" and "not the exact file" in bad["error"] and not W.installed(), bad.get("error"))
        broken["on"] = False
        c.post("/auto/cartoon/writer/install", headers=H)
        t0 = time.time()
        running = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        while W.installing() and time.time() - t0 < 120:
            time.sleep(0.2)
        st = c.get("/api/cartoon/writer", headers=H).get_json() or {}
        m = W.manifest()
        check("installation: llama.cpp from its GitHub release and the model from Hugging Face at the pinned commit, checked, "
              "unpacked, started for a test",
              W.installed() and st.get("installed") and st.get("state") == "done" and m.get("gpu") == "Fake GPU 3000"
              and all(f"https://github.com/ggml-org/llama.cpp/releases/download/b9999/{zn}" in asked_urls for zn in znames.values())
              and any(u == "https://huggingface.co/test/Test-GGUF/resolve/0123abc/Test-Q8_0.gguf" for u in asked_urls)
              and (W.BIN / "vulkan" / "llama-server.exe").is_file() and (W.BIN / "cpu" / "llama-server.exe").is_file()
              and not (W.ROOT / "tmp").exists(),
              (st, m, asked_urls[-2:], "wrInstall" in running))
        home = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        check("installed: the page has the story form (what about, language, country, length, format) and says where it runs",
              "Write the story" in home and "name='about'" in home and "value='ro'" in home and "name='country'" in home
              and "name='secs'" in home and "Fake GPU 3000" in home, "")

        # a story from a topic
        r = c.post("/auto/cartoon/write", data={"about": "Why a city hospital pays three times more for the same medicine",
                                                "lang": "en", "country": "Moldova", "secs": "75", "format": "vertical"}, headers=H)
        jid = (r.headers.get("Location") or "").rstrip("/").split("/")[-1]
        j = wait(vo, jid) if re.fullmatch(r"[0-9-a-f]{22}", jid) else {}
        res = j.get("result") or {}
        story = W.story_of(jid) if jid else ""
        req = json.loads(sorted((work / "asked").glob("request_*.json"))[-1].read_text("utf-8"))
        ask = req["messages"][-1]["content"]
        sc = T.parse(story)
        check("a topic: the free model's story in the program's format (scenes, people, pictures), the markdown taken off",
              r.status_code == 302 and j.get("state") == "done" and res.get("scenes") == 7 and res.get("attempts") == 1
              and story.startswith("Title: Why the Hospital") and "```" not in story and len(sc["scenes"]) == 7
              and sc["scenes"][3]["visual"]["kind"] == "contract" and res.get("device") == "Fake GPU 3000",
              (r.status_code, j.get("state"), res))
        check("a topic: the request names the topic, the language, the length, the viewers' money and the format's rules",
              "TOPIC: Why a city hospital pays three times more" in ask and "LANGUAGE: English" in ask and "Moldovan lei" in ask
              and "== <Background> | <visual>" in ask and "EXAMPLE of the format" in ask and "Format: vertical" in ask
              and req["messages"][0]["role"] == "system", ask[:300])
        page = c.get(f"/auto/cartoon/{jid}", headers=H).get_data(as_text=True)
        check("a story's page: the story to read and change, Make the cartoon, another version, another country",
              "Title: Why the Hospital Pays Three Times More" in page and "Make the cartoon" in page
              and f"/auto/cartoon/{jid}/rewrite" in page and "name='mode' value='adapt'" in page, "")
        time.sleep(0.5)
        check("the writer's server is stopped after the story (its port closed, nothing left running)",
              not vo._CURRENT.get("proc") and "listening" in (vo._job_dir(jid) / "server.log").read_text("utf-8", errors="replace"), "")

        # made into a cartoon (a preview without voices)
        mk = c.post("/auto/cartoon/new", data={"text": story, "format": "vertical", "captions": "1"}, headers=H)
        fid = next((x["id"] for x in vo.list_jobs() if x.get("kind") == "cartoon_make"), "")
        fj = wait(vo, fid, 900) if fid else {}
        check("the story written becomes a cartoon (7 scenes)", mk.status_code == 302 and fj.get("state") == "done"
              and (fj.get("result") or {}).get("scenes") == 7, (mk.status_code, fj.get("state"), (fj.get("result") or {}).get("error")))

        # a broken answer: asked again once
        r2 = c.post("/auto/cartoon/write", data={"about": "broken", "lang": "en"}, headers=H)
        j2 = wait(vo, (r2.headers.get("Location") or "").rstrip("/").split("/")[-1])
        check("an answer that is not a story is asked again once, saying what was wrong",
              j2.get("state") == "done" and (j2.get("result") or {}).get("attempts") == 2, j2.get("result"))

        # a text to retell
        text = ("The education department of a region bought 2,000 laptops for schools at 1,450 dollars each through a tender "
                "open for six days, won by the only bidder, a firm registered eight months earlier whose co-owner is a relative "
                "of the deputy head. The same model cost about 600 dollars in shops. Auditors found a third of them were never "
                "delivered.")
        r3 = c.post("/auto/cartoon/write", data={"about": text, "lang": "en", "format": "horizontal"}, headers=H)
        j3 = wait(vo, (r3.headers.get("Location") or "").rstrip("/").split("/")[-1])
        req3 = json.loads(sorted((work / "asked").glob("request_*.json"))[-1].read_text("utf-8"))
        ask3 = req3["messages"][-1]["content"]
        story3 = W.story_of(j3["id"])
        check("a pasted text: retold as a story (not copied), wide format kept",
              j3.get("mode") == "text" and j3.get("state") == "done" and "TEXT:" in ask3 and "2,000 laptops" in ask3
              and "do not copy its sentences" in ask3 and "Format: horizontal" in story3, (j3.get("mode"), j3.get("state")))

        # retold for another country and language
        r4 = c.post("/auto/cartoon/write", data={"mode": "adapt", "source": T.ROAD_TEXT, "lang": "ru", "country": "Россия",
                                                 "format": "vertical", "title": "How a City Loses Millions"}, headers=H)
        j4 = wait(vo, (r4.headers.get("Location") or "").rstrip("/").split("/")[-1])
        req4 = json.loads(sorted((work / "asked").glob("request_*.json"))[-1].read_text("utf-8"))
        ask4 = req4["messages"][-1]["content"]
        sc4 = T.parse(W.story_of(j4["id"]))
        check("another country: the story retold in Russian (names, roubles), its scenes and pictures kept",
              j4.get("state") == "done" and j4.get("title") == "How a City Loses Millions (Русский)" and sc4["language"] == "ru"
              and "Retell this cartoon script for viewers in Россия, in Russian" in ask4 and "roubles" in ask4
              and "Kate (wave, happy)" in ask4 and len(sc4["scenes"]) == 10, (j4.get("title"), sc4.get("language"), ask4[:200]))

        # Stop while it writes
        r5 = c.post("/auto/cartoon/write", data={"about": "slow", "lang": "en"}, headers=H)
        jid5 = (r5.headers.get("Location") or "").rstrip("/").split("/")[-1]
        t0 = time.time()
        while time.time() - t0 < 60 and not (vo.read_job(jid5)["state"] == "working" and vo._CURRENT.get("step") == "writing"
                                              and float(vo._CURRENT.get("progress") or 0) > 0.06):
            time.sleep(0.1)
        proc = vo._CURRENT.get("proc")
        c.post(f"/auto/cartoon/{jid5}/stop", headers=H)
        j5 = wait(vo, jid5, 60)
        time.sleep(0.5)
        check("Stop: the story is not finished, the writer's server is killed",
              j5.get("state") == "failed" and (j5.get("result") or {}).get("error") == "Stopped."
              and proc is not None and proc.poll() is not None, (j5.get("state"), j5.get("result")))

        # the graphics card fails: the processor
        os.environ["FAKE_LLAMA_GPU_FAIL"] = "1"
        r6 = c.post("/auto/cartoon/write", data={"about": "Why a city hospital pays more", "lang": "en"}, headers=H)
        j6 = wait(vo, (r6.headers.get("Location") or "").rstrip("/").split("/")[-1])
        os.environ.pop("FAKE_LLAMA_GPU_FAIL")
        check("a graphics card that fails to start: the story is written on the processor",
              j6.get("state") == "done" and (j6.get("result") or {}).get("device") == "", j6.get("result"))

        # a video on this PC: without the voice add-on refused; with it (a stand-in Whisper here) heard, noted, written
        vid = work / "talk.mp4"
        vid.write_bytes(b"not really a video")
        nv = c.post("/auto/cartoon/write", data={"video": str(vid), "lang": "en"}, headers=H)
        real = (vo.installed, vo.transcribe, vo._check_video)
        said = ("The council paid a company owned by the mayor's cousin two million for a bridge that was never built. " * 70).split()
        vo.installed = lambda: True
        vo._check_video = lambda p, need_sound=False: None
        vo.transcribe = lambda wjob, work, timeout=0, on_line=None: (on_line({"progress": 0.5}) if on_line else None,
                                                                    {"ok": True, "words": [{"w": w, "s": 0, "e": 0} for w in said]})[1]
        try:
            before = set(p.name for p in (work / "asked").glob("request_*.json"))
            rv = c.post("/auto/cartoon/write", data={"video": str(vid), "lang": "en", "secs": "75"}, headers=H)
            jv = wait(vo, (rv.headers.get("Location") or "").rstrip("/").split("/")[-1])
        finally:
            vo.installed, vo.transcribe, vo._check_video = real
        new_asks = [json.loads(p.read_text("utf-8")) for p in sorted((work / "asked").glob("request_*.json")) if p.name not in before]
        notes_asks = [a_ for a_ in new_asks if "part 1 of" in a_["messages"][-1]["content"] or "part 2 of" in a_["messages"][-1]["content"]]
        dv = vo._job_dir(jv["id"])
        check("a video on this PC: refused without the voice add-on; with it heard once, its facts noted in parts, "
              "a new story written from the notes",
              nv.status_code == 400 and b"needs the voice add-on" in nv.data and jv.get("state") == "done"
              and jv.get("mode") == "video" and (dv / "heard.txt").is_file() and (dv / "notes.txt").is_file()
              and len(notes_asks) >= 2 and "TEXT:" in new_asks[-1]["messages"][-1]["content"] and jv.get("title") == "talk",
              (nv.status_code, jv.get("state"), (jv.get("result") or {}).get("error"), len(notes_asks), len(new_asks)))
        vpage = c.get(f"/auto/cartoon/{jv['id']}", headers=H).get_data(as_text=True)
        check("a video's story page says what was heard", "Retelling a video" in vpage and "bridge that was never built" in vpage, "")

        # the other model: only it is downloaded (the program stays), the first one deleted after
        (dl / "Big-Q4_K_M.gguf").write_bytes(b"GGUF" + os.urandom(8192))
        W.MODELS["big"].update(repo="test/Big-GGUF", rev="0456def", file="Big-Q4_K_M.gguf",
                               size=(dl / "Big-Q4_K_M.gguf").stat().st_size, sha256=sha(dl / "Big-Q4_K_M.gguf"))
        n_asked = len(asked_urls)
        sw = c.post("/auto/cartoon/writer/install", data={"which": "big"}, headers=H)
        t0 = time.time()
        while W.installing() and time.time() - t0 < 120:
            time.sleep(0.2)
        new_urls = asked_urls[n_asked:]
        home2 = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        check("another model: only the model is downloaded, the one before deleted; the page says which writes",
              sw.status_code == 302 and W.installed() and W.which() == "big" and new_urls == [
                  "https://huggingface.co/test/Big-GGUF/resolve/0456def/Big-Q4_K_M.gguf"]
              and not (W.MODEL_DIR / "Test-Q8_0.gguf").exists() and (W.MODEL_DIR / "Big-Q4_K_M.gguf").is_file()
              and "(Qwen3-14B)" in home2 and "Use</span> <span translate='no'>Qwen3-4B" in home2, (W.status().get("error"), new_urls))

        rw = c.post(f"/auto/cartoon/{jid}/rewrite", headers=H)
        nid = (rw.headers.get("Location") or "").rstrip("/").split("/")[-1]
        jn = wait(vo, nid)
        check("Write another version: a new story of the same topic and settings", rw.status_code == 302 and nid != jid
              and jn.get("topic") == j.get("topic") and jn.get("country") == "Moldova" and jn.get("state") == "done", (rw.status_code, nid))
        lst = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        check("the list shows the stories with their state", "Story:" in lst and "Read it and make the cartoon" in lst
              and "Cartoons and stories" in lst, "")
        empty = c.post("/auto/cartoon/write", data={"about": " ", "lang": "en"}, headers=H)
        check("an empty topic is refused clearly", empty.status_code == 400 and b"Write what the cartoon is about" in empty.data,
              empty.status_code)

        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = (c.get("/auto/cartoon", headers=H).get_data(as_text=True) + c.get(f"/auto/cartoon/{jid}", headers=H).get_data(as_text=True)
              + c.get(f"/auto/cartoon/{jid5}", headers=H).get_data(as_text=True))
        body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
        body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
        txt = re.sub(r"<[^>]+>", "\n", body)
        left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                       and x.strip() not in ("MediaEngine", "Social Lab", "JSON", "YouTube") and "querySelectorAll" not in x})
        ph = re.findall(r"placeholder='([^']*)'", ru)
        check("pages: in Russian, no English left (the story writer, a story, a stopped story)",
              "Написать сюжет" in ru and not left and not [p for p in ph if re.search(r"[A-Za-z]{4,}", p)], (left[:12], ph))
        c.post("/lang", data={"lang": "en"}, headers=H)

        rm = c.post("/auto/cartoon/writer/remove", headers=H)
        check("Remove: the story writer's files are gone, the stories stay", rm.status_code == 302 and not W.installed()
              and not W.BIN.exists() and not W.MODEL_DIR.exists() and W.story_of(jid), rm.status_code)
    rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks}
    (work / "writer_check.json").write_text(json.dumps(rep, indent=1), "utf-8")
    print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
    return 0 if rep["passed"] == rep["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

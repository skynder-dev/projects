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
        W._DEVICES.clear()
        os.environ["FAKE_LLAMA_NO_DEVICE"] = "1"
        r7 = c.post("/auto/cartoon/write", data={"about": "Why a city hospital pays more", "lang": "en"}, headers=H)
        j7 = wait(vo, (r7.headers.get("Location") or "").rstrip("/").split("/")[-1])
        os.environ.pop("FAKE_LLAMA_NO_DEVICE")
        no_card = W.gpu_name()
        W._DEVICES.clear()
        check("a graphics card that fails to start: the story is written on the processor; no card the Vulkan build "
              "sees: the processor at once; a card it sees is named",
              j6.get("state") == "done" and (j6.get("result") or {}).get("device") == "" and j7.get("state") == "done"
              and (j7.get("result") or {}).get("device") == "" and no_card == "" and W.gpu_name() == "Fake GPU 3000",
              (j6.get("result"), j7.get("result"), no_card))
        # the card stops in the middle of a story (a driver reset): written on the processor, remembered
        os.environ["FAKE_LLAMA_GPU_CRASH"] = "1"
        r8 = c.post("/auto/cartoon/write", data={"about": "Why a city hospital pays more", "lang": "en"}, headers=H)
        j8 = wait(vo, (r8.headers.get("Location") or "").rstrip("/").split("/")[-1])
        r9 = c.post("/auto/cartoon/write", data={"about": "Why a city hospital pays more", "lang": "en"}, headers=H)
        j9 = wait(vo, (r9.headers.get("Location") or "").rstrip("/").split("/")[-1])
        os.environ.pop("FAKE_LLAMA_GPU_CRASH")
        card_page = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        remembered = W.gpu_failed()
        again_gpu = c.post("/auto/cartoon/writer/gpu-again", headers=H)
        check("a graphics card that stops in the middle of a story: the story is finished on the processor (the cut-off "
              "answer not taken for a story), the card is not tried again for the next ones (the page says so) until "
              "'Try the graphics card again'",
              j8.get("state") == "done" and (j8.get("result") or {}).get("device") == "" and remembered
              and j9.get("state") == "done" and (j9.get("result") or {}).get("device") == ""
              and (vo._job_dir(j8["id"]) / "server-cpu.log").is_file() and not (vo._job_dir(j9["id"]) / "server-cpu.log").is_file()
              and "stopped while writing a story" in card_page and "Try the graphics card again" in card_page
              and (j8.get("result") or {}).get("attempts") == 1 and again_gpu.status_code == 302 and not W.gpu_failed(),
              (j8.get("result"), j9.get("result"), remembered))

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
        check("a video's story page says what was heard and shows the facts noted from it",
              "Retelling a video" in vpage and "bridge that was never built" in vpage
              and "The facts noted from the video" in vpage and "check them before you publish" in vpage, "")

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
        # a series: a story for every line, each cartoon made at once (here without voices: no voice add-on)
        topics = ("Hospital pills that cost three times more", "A bridge that was never built")
        rs_ = c.post("/auto/cartoon/write", data={"topics": "\n".join(topics) + "\nx\n", "lang": "en", "secs": "60",
                                                   "make": "1", "style": "box"}, headers=H)
        series = [j_ for j_ in vo.list_jobs(80) if j_.get("kind") == "cartoon_write" and j_.get("topic") in topics]
        done = [wait(vo, j_["id"]) for j_ in series]
        made = [vo.read_job(x["result"]["film"]) for x in done if (x.get("result") or {}).get("film")]
        for f_ in made:
            vo.cancel_job(f_["id"])                        # (the films themselves are drawn in cartoon_check)
        spage2 = c.get(f"/auto/cartoon/{done[0]['id']}", headers=H).get_data(as_text=True) if done else ""
        both = c.post("/auto/cartoon/write", data={"about": "One story", "topics": "\n".join(topics), "lang": "en"}, headers=H)
        lst2 = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        check("a series: a story for every topic line (a too short one left out), each with its cartoon made at once "
              "(captions, the program's music; no voices without the add-on); the story shows its cartoon",
              rs_.status_code == 302 and len(series) == 2 and all(x.get("state") == "done" for x in done) and len(made) == 2
              and all(f_.get("kind") == "cartoon_make" and not f_.get("voices") and (f_.get("captions") or {}).get("style") == "box"
                      and (f_.get("music") or {}).get("kind") == "made" and (f_.get("script") or {}).get("camera") == "close"
                      for f_ in made)
              and "Its cartoon:" in spage2 and "Read the story" in lst2 and "A series: several topics at once" in lst2
              and both.status_code == 400 and b"not both" in both.data,
              (rs_.status_code, len(series), [x.get("state") for x in done], [(f_.get("voices"), f_.get("captions"), f_.get("music")) for f_ in made]))
        p_en = W.prompt({"mode": "topic", "topic": "Road repair", "lang": "en"})
        p_ru = W.prompt({"mode": "topic", "topic": "Ремонт дороги", "lang": "ru"})
        p_uk = W.prompt({"mode": "topic", "topic": "Road repair", "lang": "en", "country": "UK"})
        check("measures by the viewers' country: miles for the United States (English's default), kilometres for Russia, "
              "miles for roads in Britain; the example story in miles",
              "measures: miles, feet, gallons" in p_en and "never kilometres" in p_en and "measures: kilometres" in p_ru
              and "miles for roads" in p_uk and "a mile of road" in T.ROAD_TEXT and "kilomet" not in T.ROAD_TEXT, "")
        empty = c.post("/auto/cartoon/write", data={"about": " ", "lang": "en"}, headers=H)
        check("an empty topic is refused clearly", empty.status_code == 400 and b"Write what the cartoon is about" in empty.data,
              empty.status_code)

        # Reference Lab: a video studied for its rhythm - its shots, a picture of each, its colours and (a stand-in Whisper
        # here) what is said, how fast, how soon; then a new story written with that rhythm
        import subprocess, wave
        import numpy as np
        ff = vo._ffmpeg()
        liked = work / "liked.mp4"
        cols = ("0x202860", "0xf0d040", "0xd03030", "0x90f0a0")     # (navy, yellow, red, light green: cut by their brightness)
        cmd = [ff, "-hide_banner", "-v", "error"]
        for col in cols:
            cmd += ["-f", "lavfi", "-i", f"color=c={col}:s=360x640:d=3:r=25"]
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=12", "-filter_complex",
                "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]", "-map", "[v]", "-map", "4:a", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-y", str(liked)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        said2 = ("Why does a city pay three times more? Nobody asks. The tender lasts five days and only one firm applies. "
                 "The price is double. The road breaks in a year. Who wrote the rules?").split()

        def fake_listen(wjob, work_, timeout=0, on_line=None):
            sr = 16000                                     # (the sound file Whisper makes: here a steady tone - music)
            tone = (0.2 * np.sin(2 * np.pi * 440 * np.arange(12 * sr) / sr) * 32767).astype(np.int16)
            with wave.open(str(wjob["wav16"]), "wb") as w_:
                w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(sr); w_.writeframes(tone.tobytes())
            if on_line:
                on_line({"progress": 0.5})
            out, t = [], 0.4
            for w_ in said2:                               # (a word every quarter second, a pause after a sentence)
                out.append({"w": w_, "s": round(t, 2), "e": round(t + 0.22, 2)})
                t += 0.25 + (0.6 if w_[-1] in ".?" else 0)
            return {"ok": True, "language": "en", "words": out}
        real = (vo.installed, vo.transcribe)
        vo.installed, vo.transcribe = (lambda: True), fake_listen
        try:
            rs = c.post("/auto/cartoon/study", data={"video": str(liked), "listen": "1"}, headers=H)
            sid = (rs.headers.get("Location") or "").rstrip("/").split("/")[-1]
            js = wait(vo, sid)
        finally:
            vo.installed, vo.transcribe = real
        from archivist.cartoon import reference as R
        ref = R.reference_of(sid)
        shots = ref.get("shots") or []
        reds = [x for x in ref.get("palette") or [] if int(x["hex"][1:3], 16) > 170 and int(x["hex"][3:5], 16) < 90]
        check("Reference Lab: a video studied - its four shots found, a picture of each, its colours; what is said in each "
              "shot, how fast, how soon, the opening question, music under the words",
              js.get("state") == "done" and len(shots) == 4 and all(x.get("frame") for x in shots) and bool(reds)
              and shots[0]["text"].startswith("Why does a city") and 2.0 < ref.get("wps", 0) < 3.0
              and ref.get("first_words_at") == 0.4 and ref.get("opening", "").endswith("more?") and ref.get("between") == "music"
              and ref.get("format") == "vertical" and 2.5 < ref.get("shot_avg", 0) < 3.5,
              ((js.get("result") or {}).get("error"), len(shots), ref.get("palette"), ref.get("wps"), ref.get("between"),
               ref.get("opening"), ref.get("shot_avg")))
        soft = work / "soft.mp4"                           # a cross-fade, then a hard cut; and a busy picture without cuts
        subprocess.run([ff, "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=360x640:d=3.5:r=25", "-f", "lavfi",
                        "-i", "color=c=0xd03030:s=360x640:d=3:r=25", "-f", "lavfi", "-i", "color=c=0x202860:s=360x640:d=3:r=25",
                        "-filter_complex", "[0:v]format=yuv420p,setsar=1[a];[1:v]format=yuv420p,setsar=1[b];"
                        "[2:v]format=yuv420p,setsar=1[c];[a][b]xfade=transition=fade:duration=0.5:offset=3[ab];"
                        "[ab][c]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(soft)],
                       check=True, capture_output=True, timeout=180)
        busy = work / "busy.mp4"
        subprocess.run([ff, "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=8:r=30", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-y", str(busy)], check=True, capture_output=True, timeout=180)
        soft_cuts = R._cuts(soft, 9.0, ff, lambda: False)
        busy_cuts = R._cuts(busy, 8.0, ff, lambda: False)
        import time as _t
        t_stop = _t.time()
        stopped = R._cuts(busy, 8.0, ff, lambda: True)     # (Stop: the scan ends at once, whatever FFmpeg does)
        t_stop = _t.time() - t_stop
        check("Reference Lab: a cross-fade and a hard cut are both found; a busy moving picture is not taken for cuts",
              len(soft_cuts) == 2 and 2.9 <= soft_cuts[0] <= 3.6 and abs(soft_cuts[1] - 6.0) < 0.3 and busy_cuts == []
              and stopped == [] and t_stop < 10, (soft_cuts, busy_cuts, stopped, round(t_stop, 1)))
        spage = c.get(f"/auto/cartoon/{sid}", headers=H).get_data(as_text=True)
        fr = c.get(f"/auto/cartoon/{sid}/frame/{shots[0]['frame']}", headers=H) if shots else None
        bad = c.get(f"/auto/cartoon/{sid}/frame/..%2Fjob.json", headers=H)
        bad2 = c.get(f"/auto/cartoon/{sid}/frame/job.json", headers=H)      # (the page's own guard: only its pictures)
        bad3 = c.get(f"/auto/cartoon/{sid}/frame/9999.jpg", headers=H)
        check("the study's page: the rhythm (a strip of the shots), the colours, a storyboard with the pictures and the "
              "words; a form to write with this rhythm", "Storyboard" in spage and "The rhythm" in spage
              and spage.count("href='#shot") == 4 and "id='shot4'" in spage and all(x.get("color") for x in shots) and "Write a story with this rhythm" in spage
              and f"/auto/cartoon/{sid}/frame/0000.jpg" in spage and "Why does a city" in spage and fr is not None
              and fr.status_code == 200 and fr.mimetype == "image/jpeg" and bad.status_code == 404 and bad2.status_code == 404
              and bad3.status_code == 404, (fr and fr.status_code, bad.status_code, bad2.status_code, bad3.status_code))
        before = set(p.name for p in (work / "asked").glob("request_*.json"))
        rr = c.post("/auto/cartoon/write", data={"about": "School meals that cost twice as much", "lang": "en", "secs": "45",
                                                 "ref": sid}, headers=H)
        jr = wait(vo, (rr.headers.get("Location") or "").rstrip("/").split("/")[-1])
        asks = [json.loads(p.read_text("utf-8")) for p in sorted((work / "asked").glob("request_*.json")) if p.name not in before]
        ask_r = asks[0]["messages"][-1]["content"] if asks else ""
        rpage = c.get(f"/auto/cartoon/{jr['id']}", headers=H).get_data(as_text=True)
        check("a story written with the studied rhythm: as many scenes for its quick cuts, an opening question; the story "
              "page says whose rhythm", jr.get("state") == "done" and (jr.get("style") or {}).get("ref") == sid
              and "13 to 14 scenes (count them" in ask_r and "1 or 2 lines in each" in ask_r and "with a question" in ask_r and "8 to 10 scenes" not in ask_r
              and "rhythm like" in rpage and "School meals" in ask_r and "<option value='quick' selected>" in rpage,
              (jr.get("state"), jr.get("style"), ask_r[:300]))
        slow = {"shot_avg": 10.0, "wps": 1.5, "first_at": 3.0, "opens": "statement"}   # (a calm reference: long shots, slow words)
        rules_slow, w_slow = R.rules_of(slow, 60)
        story_slow = "Title: X\nNarrator: Kate (woman)\n\n" + "".join(f"== Office | bag: money\nKate: {'word ' * 9}one.\n\n" for _ in range(6))
        _i, prob_slow = W.judge(story_slow, 60, slow)
        _i, prob_usual = W.judge(story_slow, 60)
        check("the rhythm follows the reference's shots and the story's own length: a calm one asks for fewer scenes and "
              "words, and the writer's own check asks no more than that",
              "6 to 7 scenes" in rules_slow and "a calm pace" in rules_slow and "grabs attention" not in rules_slow
              and w_slow == 78 and prob_slow == "" and "too short" in prob_usual
              and "13 to 14 scenes" in R.rules_of({"shot_avg": 3.0, "wps": 2.8}, 45)[0]
              and "quick cuts" in R.rules_of({"shot_avg": 3.0}, 120)[0] and "11 to 13 scenes" in R.rules_of({"shot_avg": 10.0}, 120)[0] and "2 or 3 lines" in R.rules_of({"shot_avg": 10.0}, 120)[0]
              and "an even pace" in R.rules_of({"shot_avg": 6.0}, 75)[0], (rules_slow, w_slow, prob_slow, prob_usual))
        home3 = c.get("/auto/cartoon", headers=H).get_data(as_text=True)
        check("the home page: a video to study, the studies listed, the rhythm to choose for a story",
              "Study a cartoon you like" in home3 and "Study:" in home3 and "See the storyboard" in home3
              and f"<option value='{sid}'" in home3, "")

        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = (c.get("/auto/cartoon", headers=H).get_data(as_text=True) + c.get(f"/auto/cartoon/{jid}", headers=H).get_data(as_text=True)
              + c.get(f"/auto/cartoon/{jid5}", headers=H).get_data(as_text=True)
              + c.get(f"/auto/cartoon/{sid}", headers=H).get_data(as_text=True)
              + c.get(f"/auto/cartoon/{jr['id']}", headers=H).get_data(as_text=True))
        body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
        body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
        txt = re.sub(r"<[^>]+>", "\n", body)
        left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                       and x.strip() not in ("MediaEngine", "Social Lab", "JSON", "YouTube") and "querySelectorAll" not in x})
        ph = re.findall(r"placeholder='([^']*)'", ru)
        check("pages: in Russian, no English left (the story writer, a story, a stopped story, a study)",
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

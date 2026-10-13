"""Titles and own music in a reel, through the real engine (technical mode, synthetic videos).

  python tests/dress_check.py <fixtures_dir> <work_dir>

The R3 orchestrator runs in-process on the 2-video fixture: a reel without anything, then the same reel with a
title (Cyrillic) and a second line, with own music (a 1 kHz tone shorter than the reel, so it must loop) in both
modes, and a one-moment reel with both. Checks: the title is in the picture at the start and gone later, the reel's
length is unchanged, sound and picture end together, "music only" is the music (1 kHz), "music + sound" has both,
the music fades in, a missing or non-audio music file is a clear error, nothing set = exactly the reel without it.
"""
from __future__ import annotations

import argparse, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
from media_measure import av_durations, ffmpeg_exe  # noqa: E402


def frame(ff, video, t, w=96):
    """Gray picture (w x w*16/9) at time t."""
    h = w * 16 // 9
    cp = subprocess.run([ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                         "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    return np.frombuffer(cp.stdout, np.uint8).reshape(h, w).astype(np.float32)


def audio(ff, video, start=0.0, dur=None):
    cmd = [ff, "-v", "error", "-ss", f"{start:.3f}", "-i", str(video)] + (["-t", f"{dur:.3f}"] if dur else []) + \
          ["-map", "0:a:0", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.int16).astype(np.float32) / 32768.0


def peak_hz(x):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return float(np.fft.rfftfreq(len(x), 1 / 48000)[int(np.argmax(spec[20:])) + 20])


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "models"))
    spec = importlib.util.spec_from_file_location("r3_dress", R3 / "p11_folder_to_reel_r3.py")
    r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    src = work / "in"
    shutil.copytree(fx / "two", src)
    music = work / "Моя музыка" / "песня 1kHz.m4a"          # Cyrillic names on purpose
    music.parent.mkdir()
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100", "-t", "4",
                    "-c:a", "aac", "-b:a", "128k", str(music)], check=True)
    text = work / "notes.txt"
    text.write_text("not music", encoding="utf-8")

    def run(out, dress=None, target=10.0):
        dfile = ""
        if dress is not None:
            dfile = str(work / (out + ".dress.json"))
            Path(dfile).write_text(json.dumps(dress, ensure_ascii=False), encoding="utf-8")
        a = argparse.Namespace(input_dir=str(src), input_list="", output_dir=str(work / out), work_dir=str(work / "w"),
                               runtime_dir=str(R3), target_seconds=target, audio="auto", semantic="off", semantic_model="fast_local",
                               theme="", profile="9x16", resolution="standard", progress_file="", exclude_events="", edits="",
                               skip_sha_file="", dress=dfile)
        r3.run(a)
        return work / out / "MediaEngine Reel.mp4", json.loads((work / out / "MediaEngine Result.json").read_text(encoding="utf-8"))

    base, rb = run("plain")
    check("plain_reel_has_no_dress", rb.get("dress") is None, rb.get("dress"))
    same, rs = run("empty_dress", {"title": "  ", "subtitle": "", "music": ""})
    check("nothing_set_is_the_plain_reel", rs.get("dress") is None and rs["output"]["sha256"] == rb["output"]["sha256"],
          (rs.get("dress"), rs["output"]["sha256"][:12], rb["output"]["sha256"][:12]))
    vb, ab = av_durations(base, ff)

    titled, rt = run("title", {"title": "Лето у моря 2026", "subtitle": "14 июля 2026"})
    vt, at = av_durations(titled, ff)
    f0, f1 = frame(ff, base, 1.5), frame(ff, titled, 1.5)
    h = f0.shape[0]
    lower = slice(int(h * .55), int(h * .85))
    d_title = float(np.abs(f0[lower] - f1[lower]).mean())
    d_late = float(np.abs(frame(ff, base, vb - 1.5) - frame(ff, titled, vb - 1.5)).mean())
    check("title_is_shown_at_the_start", rt["dress"]["title_shown"] and d_title > 4.0, (rt["dress"], d_title))
    check("title_is_gone_later", d_late < 2.5, d_late)
    check("title_keeps_the_length", abs(vt - vb) < 0.05 and at is not None and abs(vt - at) <= 0.05, (vb, vt, at))

    only, ro = run("music_only", {"music": str(music), "music_mode": "music"})
    vo, ao = av_durations(only, ff)
    mid = audio(ff, only, 5.0, 1.0)                           # after the 4 s tone looped
    check("music_only_is_the_music_and_loops", abs(peak_hz(mid) - 1000) < 15 and float(np.abs(mid).mean()) > 0.02,
          (peak_hz(mid), float(np.abs(mid).mean())))
    check("music_ends_with_the_picture", ao is not None and abs(vo - ao) <= 0.05 and abs(vo - vb) < 0.05, (vb, vo, ao))
    check("music_only_result_length_is_the_pictures", abs(float(ro["actual_duration_s"]) - vo) <= 0.05, (ro["actual_duration_s"], vo))
    # the 4 s AAC song repeats without a gap (its encoder delay used to leave ~26 ms of silence at every repeat)
    whole = audio(ff, only, 0.0, None)
    win = 480
    rms = np.sqrt(np.mean(whole[: len(whole) // win * win].reshape(-1, win) ** 2, axis=1))
    steady = rms[int(1.0 * 100): int((vo - 2.0) * 100)]
    check("music_repeats_without_a_gap", steady.size and float(steady.min()) > 0.5 * float(np.median(steady)),
          (float(steady.min()) if steady.size else None, float(np.median(steady)) if steady.size else None))
    head = audio(ff, only, 0.0, 0.1); body = audio(ff, only, 2.0, 0.1)
    check("music_fades_in", float(np.abs(head).mean()) < 0.6 * float(np.abs(body).mean()),
          (float(np.abs(head).mean()), float(np.abs(body).mean())))
    check("music_named_in_the_result", ro["dress"]["music"] == {"name": music.name, "sha256": ro["dress"]["music"]["sha256"], "mode": "music"}
          and len(ro["dress"]["music"]["sha256"]) == 64, ro["dress"])

    mixed, rm = run("music_mix", {"music": str(music), "music_mode": "mix"})
    vm, am = av_durations(mixed, ff)
    x = audio(ff, mixed, 3.0, 2.0)
    spec = np.abs(np.fft.rfft(x)); fr = np.fft.rfftfreq(len(x), 1 / 48000)
    tone = float(spec[(fr > 990) & (fr < 1010)].max()); rest = float(spec[(fr > 100) & ((fr < 900) | (fr > 1100)) & (fr < 8000)].max())
    base_x = audio(ff, base, 3.0, 2.0)
    check("music_mix_has_the_music_and_the_videos_sound", tone > 0 and rest > 0.05 * tone and float(np.abs(base_x).mean()) > 0.001,
          (tone, rest))
    check("music_mix_ends_with_the_picture", am is not None and abs(vm - am) <= 0.05 and abs(float(rm["actual_duration_s"]) - vm) <= 0.05,
          (vm, am, rm["actual_duration_s"]))

    one, r1 = run("one_moment", {"title": "Один момент", "music": str(music)}, target=3.0)
    v1, a1 = av_durations(one, ff)
    check("one_moment_reel_with_title_and_music", r1["selected_count"] >= 1 and r1["dress"]["title_shown"] and a1 is not None
          and abs(v1 - a1) <= 0.05, (r1["selected_count"], v1, a1))

    # emoji in the title are left out (they would be boxes), a word longer than the frame is broken, not cut off
    em, re_ = run("emoji_title", {"title": "Лето 2026 🌊☀️🏖", "subtitle": "Ш" * 80})
    check("emoji_left_out_and_said", re_["dress"]["title_shown"] and "TITLE_CHARACTERS_LEFT_OUT" in re_["warnings"], re_.get("warnings"))
    from PIL import Image
    png = work / "long.png"
    r3.title_png("Ш" * 80, "", 540, 960, png)
    box = Image.open(png).split()[-1].point(lambda a: 255 if a > 200 else 0).getbbox()
    check("long_word_stays_in_the_frame", box and box[0] > 5 and box[2] < 535, box)
    empty = work / "empty.wav"
    empty.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
    for name, dress, code in (("missing", {"music": str(work / "nope.mp3")}, "MUSIC_FILE_MISSING"),
                              ("not_audio", {"music": str(text)}, "MUSIC_FILE_NOT_AUDIO"),
                              ("without_sound", {"music": str(empty)}, "MUSIC_FILE_NO_SOUND")):
        try:
            run("bad_" + name, dress)
            err = ""
        except RuntimeError as exc:
            err = str(exc)
        check(f"music_{name}_is_a_clear_error", err.startswith(code), err)
    check("music_file_unchanged", music.stat().st_size > 0 and subprocess.run([ff, "-v", "error", "-i", str(music), "-f", "null", "-"]).returncode == 0)
    app_part(work, src, music, check)
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


def app_part(work, src, music, check):
    """The same through the app, like a user: new reel with a title and music, variants, the editor keeps them."""
    import html, time
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    from archivist.web import create_app
    from archivist import auto_edit as ae
    from i18n_coverage import english_left, page_texts
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}

    def wait(jid, limit=600):
        t0 = time.time()
        while time.time() - t0 < limit and ae.job(jid)["status"] in ("queued", "running"):
            time.sleep(0.5)
        return ae.job(jid)

    with app.test_client() as c:
        page = c.get("/auto/new", query_string={"folder": str(src)}, headers=H).data.decode("utf-8", "replace")
        check("setup_offers_music_and_title", "name='reel_title'" in page and "name='music'" in page and "data-pick-music" in page)
        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = c.get("/auto/new", query_string={"folder": str(src)}, headers=H).data.decode("utf-8", "replace")
        c.post("/lang", data={"lang": "en"}, headers=H)
        left = [t.strip()[:80] for t in page_texts(ru) if english_left(html.unescape(t))]
        check("music_and_title_in_russian", "Музыка и надпись" in ru and not left, left[:8])
        r = c.post("/auto/create", data={"folder": str(src), "length": "15", "format": "vertical", "sound": "auto", "mode": "technical",
                                         "reel_title": "Наше лето", "reel_subtitle": "июль 2026", "music": str(music), "music_mode": "mix"}, headers=H)
        ok = r.status_code == 302 and "/auto/p/" in r.headers.get("Location", "")
        check("reel_with_title_and_music_created", ok, (r.status_code, r.data[:300]))
        if not ok:
            return
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        j1 = wait(ae.project(pid)["jobs"][0]["id"])
        rev1 = ae.revision(j1.get("revision_id") or 0) if j1["status"] == "done" else None
        d1 = (rev1 or {}).get("result", {}).get("dress") or {}
        check("revision_has_title_and_music", d1.get("title") == "Наше лето" and d1.get("title_shown") and (d1.get("music") or {}).get("mode") == "mix",
              (j1["status"], j1.get("error"), d1))
        if not rev1:
            return
        pg = c.get(f"/auto/p/{pid}", headers=H).data.decode("utf-8", "replace")
        check("review_names_title_and_music", "Наше лето" in pg and music.name in html.unescape(pg))
        # only the music changes: a new version without a new analysis
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev1["id"], "length": "15", "format": "vertical", "sound": "auto",
                                               "mode": "technical", "reel_title": "Наше лето", "reel_subtitle": "июль 2026",
                                               "music": str(music), "music_mode": "music"}, headers=H)
        j2 = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        j2 = wait(j2[0]["id"]) if j2 else {"status": "missing"}
        rev2 = ae.revision(j2.get("revision_id") or 0) if j2.get("status") == "done" else None
        st2 = (rev2 or {}).get("result", {}).get("stage_seconds") or {}
        st1 = rev1["result"].get("stage_seconds") or {}
        check("music_change_is_a_quick_new_version", rev2 and rev2["result"]["dress"]["music"]["mode"] == "music"
              and [s_["event_id"] for s_ in rev2["result"]["segments"]] == [s_["event_id"] for s_ in rev1["result"]["segments"]]
              and float(st2.get("analyze", 0)) <= max(3.0, 0.5 * float(st1.get("analyze", 0))),
              (j2.get("status"), j2.get("error"), st1, st2))
        # the editor (remove one moment) keeps the title and the music
        segs = rev2["result"]["segments"] if rev2 else []
        if len(segs) >= 2:
            form = {"revision_id": str(rev2["id"]), "length": "15", "format": "vertical", "sound": "auto", "mode": "technical",
                    "row": [s_["event_id"] for s_ in segs], "remove": [segs[-1]["event_id"]]}
            for s_ in segs:
                form[f"def_in_{s_['event_id']}"] = f"{s_['source_in_s']:.1f}"; form[f"def_out_{s_['event_id']}"] = f"{s_['source_out_s']:.1f}"
            before = {x["id"] for x in ae.project(pid)["jobs"]}
            c.post(f"/auto/p/{pid}/edit", data=form, headers=H)
            j3 = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
            j3 = wait(j3[0]["id"]) if j3 else {"status": "missing"}
            rev3 = ae.revision(j3.get("revision_id") or 0) if j3.get("status") == "done" else None
            d3 = (rev3 or {}).get("result", {}).get("dress") or {}
            check("editor_keeps_title_and_music", d3.get("title") == "Наше лето" and (d3.get("music") or {}).get("mode") == "music",
                  (j3.get("status"), j3.get("error"), d3))
        # "No music" and an empty title: the plain reel again
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev1["id"], "length": "15", "format": "vertical", "sound": "auto",
                                               "mode": "technical", "reel_title": "", "reel_subtitle": "", "music": "", "music_mode": "mix"}, headers=H)
        j4 = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        j4 = wait(j4[0]["id"]) if j4 else {"status": "missing"}
        rev4 = ae.revision(j4.get("revision_id") or 0) if j4.get("status") == "done" else None
        check("removing_music_and_title_gives_the_plain_reel", rev4 and rev4["result"].get("dress") is None, (j4.get("status"), j4.get("error")))
        r = c.post("/auto/create", data={"folder": str(src), "length": "15", "format": "vertical", "sound": "auto", "mode": "technical",
                                         "music": str(work / "nope.mp3")}, headers=H)
        check("missing_music_refused_before_building", r.status_code != 302 and b"Music file not found" in r.data, r.status_code)


if __name__ == "__main__":
    sys.exit(main())

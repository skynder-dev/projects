"""Titles and own music in a reel, through the real engine (technical mode, synthetic videos).

  python tests/dress_check.py <fixtures_dir> <work_dir>

The R3 orchestrator runs in-process on the 2-video fixture: a reel without anything, then the same reel with a
title (Cyrillic) and a second line, with own music (a 1 kHz tone shorter than the reel, so it must loop) in both
modes, and a one-moment reel with both. Checks: the title is in the picture at the start and gone later, the reel's
length is unchanged, sound and picture end together, "music only" is the music (1 kHz), "music + sound" has both,
the music fades in, a missing or non-audio music file is a clear error, nothing set = exactly the reel without it.
Cuts on the beat: a drum song (AAC, known beat times) under a 20 s reel of 7 videos - every cut where a beat is, in
the result, in the picture and in the reel's own sound; a tone (no beat) or beat_sync off leaves the cuts unchanged.
"""
from __future__ import annotations

import argparse, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R3))
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

    def run(out, dress=None, target=10.0, folder=None, work_dir=None):
        dfile = ""
        if dress is not None:
            dfile = str(work / (out + ".dress.json"))
            Path(dfile).write_text(json.dumps(dress, ensure_ascii=False), encoding="utf-8")
        a = argparse.Namespace(input_dir=str(folder or src), input_list="", output_dir=str(work / out), work_dir=str(work_dir or (work / "w")),
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
    # a tone has no beat: the cuts stay exactly where they were, and the result says why
    check("music_without_a_clear_beat_keeps_the_cuts", "MUSIC_NO_CLEAR_BEAT" in ro["warnings"]
          and [x["reel_out_s"] for x in ro["segments"]] == [x["reel_out_s"] for x in rb["segments"]], (ro["warnings"], ro.get("beat_sync")))
    beat_part(work, fx, ff, run, check)
    app_part(work, src, music, check)
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


def drum_song(path: Path, ff: str, bpm: float, offset: float, seconds: float) -> list[float]:
    """A drum pattern (kick, snare, hi-hat between the beats) over quiet chords and a little noise, saved as AAC.
    Returns the true beat times."""
    sr = 48000
    rng = np.random.default_rng(11)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    x = 0.08 * np.sin(2 * np.pi * 220 * t) + 0.06 * np.sin(2 * np.pi * 277 * t) + 0.05 * np.sin(2 * np.pi * 330 * t)
    f = np.fft.rfft(rng.standard_normal(n)); f /= np.maximum(1, np.arange(len(f))) ** 0.5
    bed = np.fft.irfft(f, n); x += 0.02 * bed / np.abs(bed).max()
    per = 60.0 / bpm
    beats, b, k = [], offset, 0
    while b < seconds - 0.3:
        i = int(b * sr); m = np.arange(min(int(0.25 * sr), n - i))
        if k % 2 == 0:
            x[i:i + len(m)] += 0.6 * np.sin(2 * np.pi * (55 + 70 * np.exp(-m / (0.03 * sr))) * m / sr) * np.exp(-m / (0.09 * sr))
        else:
            x[i:i + len(m)] += 0.35 * rng.standard_normal(len(m)) * np.exp(-m / (0.05 * sr))
        j = int((b + per / 2) * sr); h = int(0.04 * sr)
        if j + h < n:
            x[j:j + h] += 0.08 * rng.standard_normal(h) * np.exp(-np.arange(h) / (0.008 * sr))
        beats.append(round(b, 4)); b += per; k += 1
    pcm = (np.clip(x * 0.8, -1, 1) * 32767).astype(np.int16)
    raw = path.with_suffix(".raw")
    raw.write_bytes(np.stack([pcm, pcm], 1).tobytes())
    subprocess.run([ff, "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", str(raw), "-c:a", "aac", "-b:a", "192k",
                    str(path)], check=True)
    raw.unlink()
    return beats


def cut_times(res) -> list[float]:
    """Where the reel's cuts are, from its result: the middle of each dissolve (or the hard cut), and the end."""
    segs, tr = res["segments"], res["rendered_transition_s"]
    return [float(s["reel_out_s"]) - (float(tr[i]) / 2.0 if i < len(tr) else 0.0) for i, s in enumerate(segs)]


def picture_cuts(ff, video, expected, fps=30):
    """The cuts as seen in the picture, near each expected cut: the burst of frame-to-frame change (one frame for a
    hard cut, the frames of a dissolve), its middle. A hard cut at c is measured at c - half a frame."""
    w, h = 64, 112
    raw = subprocess.run([ff, "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))      # d[k]: change into frame k+1 (shown at (k+1)/fps)
    out = []
    for c in expected:
        i0, i1 = max(0, int((c - 0.4) * fps)), min(len(d), int((c + 0.4) * fps))
        seg = d[i0:i1]
        if seg.size < 3:
            out.append(None); continue
        base, top = float(np.median(seg)), float(seg.max())
        k = int(np.argmax(seg))
        lo = hi = k
        while lo > 0 and seg[lo - 1] > base + 0.5 * (top - base):
            lo -= 1
        while hi < len(seg) - 1 and seg[hi + 1] > base + 0.5 * (top - base):
            hi += 1
        into = (np.arange(i0 + lo, i0 + hi + 1) + 1) / fps
        out.append(float(into.mean() - 0.5 / fps))
    return out


def beat_part(work, fx, ff, run, check):
    """Own music with a clear beat: every cut on a beat of the music (where the picture really changes, and where the
    music really is in the finished reel), the reel's length about the same, sound and picture end together; switched
    off: the cuts stay where they were."""
    folder = work / "seven"
    shutil.copytree(fx / "seven", folder)
    song = work / "Моя музыка" / "барабаны 118.m4a"
    truth = np.array(drum_song(song, ff, 118.0, 0.27, 40.0))
    plain, rp = run("beat_plain", None, 20.0, folder, work / "w7")
    off, roff = run("beat_off", {"music": str(song), "music_mode": "music", "beat_sync": False}, 20.0, folder, work / "w7")
    check("beat_sync_off_keeps_the_cuts", "beat_sync" not in roff and [x["reel_out_s"] for x in roff["segments"]] == [x["reel_out_s"] for x in rp["segments"]],
          roff.get("beat_sync"))
    on, ron = run("beat_on", {"music": str(song), "music_mode": "music"}, 20.0, folder, work / "w7")
    bs = ron.get("beat_sync") or {}
    check("beat_found_in_the_music", bs.get("clear") and abs(float(bs.get("bpm") or 0) - 118.0) < 1.0, bs)
    cuts = cut_times(ron)
    offs = [float(np.min(np.abs(truth - c))) for c in cuts]
    on_beat = sum(1 for o in offs if o <= 0.04)
    check("cuts_on_the_beat", len(cuts) >= 3 and on_beat >= len(cuts) - 1 and bs.get("cuts_on_beat") >= len(cuts) - 1, (cuts, offs, bs))
    seen = picture_cuts(ff, on, cuts[:-1])
    pic = [abs(a - b) for a, b in zip(seen, cuts[:-1]) if a is not None]
    check("picture_changes_on_the_beat", len(pic) == len(cuts) - 1 and max(pic) <= 0.04, (seen, cuts[:-1]))
    # the music in the finished reel is where its beats were found (no delay from decoding or loudness filters)
    import p13_beats as beatmod
    wav = work / "beat_on_audio.wav"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(on), "-map", "0:a:0", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)], check=True)
    heard = np.array(beatmod.detect(wav)["beats"])
    lag = [float(np.min(np.abs(truth - h))) for h in heard[2:-2]] if heard.size > 4 else [1.0]
    check("music_in_the_reel_is_on_time", float(np.median(lag)) <= 0.015, (float(np.median(lag)), heard[:6], truth[:6]))
    v, a = av_durations(on, ff)
    check("beat_reel_length_kept_sound_ends_with_picture", a is not None and abs(v - a) <= 0.05 and abs(v - float(rp["actual_duration_s"])) <= 1.0,
          (v, a, rp["actual_duration_s"]))
    # a song shorter than the reel repeats - so do its beats: the cuts follow them into the repeats
    short = work / "Моя музыка" / "барабаны 100 короткая.m4a"
    t_short = drum_song(short, ff, 100.0, 0.15, 7.0)
    loop, rl = run("beat_loop", {"music": str(short), "music_mode": "mix"}, 20.0, folder, work / "w7")
    stated = 7.0
    rep = np.array([b + k * stated for k in range(5) for b in t_short])
    cuts_l = cut_times(rl)
    offs_l = [float(np.min(np.abs(rep - c))) for c in cuts_l]
    vl, al_ = av_durations(loop, ff)
    check("beats_follow_a_repeated_short_song", (rl.get("beat_sync") or {}).get("clear") and sum(o <= 0.04 for o in offs_l) >= len(cuts_l) - 1
          and al_ is not None and abs(vl - al_) <= 0.05, (cuts_l, offs_l, rl.get("beat_sync")))


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
        check("setup_offers_music_and_title", "name='reel_title'" in page and "name='music'" in page and "data-pick-music" in page
              and "name='beat_sync' value='1' checked" in page)
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
        check("review_names_title_and_music", "Наше лето" in pg and music.name in html.unescape(pg)
              and "the music has no clear beat, so the cuts were left where they were" in pg)
        # cuts on the beat switched off (the checkbox is not sent when off): kept in the settings, not asked of the engine
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev1["id"], "length": "15", "format": "vertical", "sound": "auto",
                                               "mode": "technical", "reel_title": "Наше лето", "reel_subtitle": "июль 2026",
                                               "music": str(music), "music_mode": "mix", "beat_sync_shown": "1"}, headers=H)
        jb = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        jb = wait(jb[0]["id"]) if jb else {"status": "missing"}
        revb = ae.revision(jb.get("revision_id") or 0) if jb.get("status") == "done" else None
        check("beat_sync_off_from_the_form", revb and revb["settings"].get("beat_sync") is False and "beat_sync" not in revb["result"]
              and "MUSIC_NO_CLEAR_BEAT" not in revb["result"]["warnings"], (jb.get("status"), jb.get("error"), revb and revb["settings"]))
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
        # horizontal Full HD 1920x1080 (offered since 2026-10-13), with the title drawn for that size
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev1["id"], "length": "15", "format": "horizontal_hd", "sound": "auto",
                                               "mode": "technical", "reel_title": "Наше лето", "reel_subtitle": "", "music": "", "music_mode": "mix"}, headers=H)
        j5 = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        j5 = wait(j5[0]["id"]) if j5 else {"status": "missing"}
        rev5 = ae.revision(j5.get("revision_id") or 0) if j5.get("status") == "done" else None
        check("horizontal_full_hd_variant", rev5 and (rev5["width"], rev5["height"]) == (1920, 1080) and rev5["result"]["dress"]["title_shown"],
              (j5.get("status"), j5.get("error"), rev5 and (rev5["width"], rev5["height"])))
        r = c.post("/auto/create", data={"folder": str(src), "length": "15", "format": "vertical", "sound": "auto", "mode": "technical",
                                         "music": str(work / "nope.mp3")}, headers=H)
        check("missing_music_refused_before_building", r.status_code != 302 and b"Music file not found" in r.data, r.status_code)
        # horizontal videos in a vertical reel: the whole picture on blurred edges (a choice; cropping stays the default)
        before = {x["id"] for x in ae.project(pid)["jobs"]}
        c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev1["id"], "format": "vertical", "framing": "fit_blur"}, headers=H)
        j6 = [x for x in ae.project(pid)["jobs"] if x["id"] not in before]
        j6 = wait(j6[0]["id"]) if j6 else {"status": "missing"}
        rev6 = ae.revision(j6.get("revision_id") or 0) if j6.get("status") == "done" else None
        edge = mid = None
        if rev6:
            f6 = frame(ff, Path(rev6["video_path"]), 2.0)
            h6 = f6.shape[0]
            sharp = lambda a: float(np.abs(np.diff(a, axis=1)).mean())
            edge, mid = sharp(f6[: int(h6 * .2)]), sharp(f6[int(h6 * .4): int(h6 * .6)])
        check("vertical_with_blurred_edges", rev6 and rev6["settings"].get("framing") == "fit_blur"
              and rev6["result"]["output"].get("vertical_framing") == "fit_blur" and rev6["result"].get("segments")
              and [s_["event_id"] for s_ in rev6["result"]["segments"]] == [s_["event_id"] for s_ in rev1["result"]["segments"]]
              and edge is not None and edge < mid * 0.5, (j6.get("status"), j6.get("error"), edge, mid))


if __name__ == "__main__":
    sys.exit(main())

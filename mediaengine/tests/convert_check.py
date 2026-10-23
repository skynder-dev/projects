"""Full-video Convert (existing Archivist feature, contract §9): whole video, original order and frame rate, H.264.

  python tests/convert_check.py <fixtures_dir> <work_dir>

Converts with the app's own converter.convert_file: a 1440p 60 fps clip -> High Quality 1080p, the rotated phone clip and
the VFR clip from <fixtures_dir>/phone. Checks: output size cap, frame rate kept, duration and frame count match the source
(no cut, no drop), full decode clean, upright portrait stays upright, audio kept, source bytes unchanged, no .part left.
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import av_durations, ffmpeg_exe  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def frames(ff, path):
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", "scale=8:8", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return len(raw) // 64


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.converter import convert_file
    from archivist.auto_edit import _probe
    ff = ffmpeg_exe()
    src_dir = work / "src"
    src_dir.mkdir(exist_ok=True)
    big = src_dir / "walkthrough_1440p60.mp4"
    if not big.exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=2560x1440:rate=60", "-f", "lavfi", "-i",
                        "sine=frequency=330:sample_rate=48000", "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(big)], check=True)
    cases = [(big, "hq_1080p", (1920, 1080), 60.0), (fx / "phone" / "Отпуск — пляж.mp4", "hq_1080p", (720, 1280), 30.0),
             (fx / "phone" / "переменная частота.mp4", "share_1080p", (640, 360), None)]
    checks = []

    def check(name, ok, detail=None):
        checks.append(ok)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    out_dir = work / "Converted"
    for src, preset, dims, fps in cases:
        before = sha(src)
        res = convert_file(src, preset, output_dir=out_dir)
        out = Path(res["output"])
        info = _probe(out)
        v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"][0]
        a = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        tag = src.stem[:20]
        check(f"convert_{tag}_h264_size", v.get("codec_name") == "h264" and (int(v["width"]), int(v["height"])) == dims, (v.get("codec_name"), v.get("width"), v.get("height")))
        if fps:
            num, den = (v.get("r_frame_rate") or "0/1").split("/")
            check(f"convert_{tag}_fps_kept", abs(float(num) / float(den) - fps) < 0.01, v.get("r_frame_rate"))
        fs, fo = frames(ff, src), frames(ff, out)
        check(f"convert_{tag}_no_frames_lost", fo >= fs - 1, (fs, fo))
        vd_s, ad_s = av_durations(src, ff, fps or 30.0)
        vd_o, ad_o = av_durations(out, ff, fps or 30.0)
        check(f"convert_{tag}_full_length", abs(float(info["format"]["duration"]) - float(_probe(src)["format"]["duration"])) <= 0.15
              and bool(a) == bool(ad_s), (info["format"]["duration"], _probe(src)["format"]["duration"]))
        dec = subprocess.run([ff, "-v", "error", "-i", str(out), "-f", "null", "-"], capture_output=True, text=True)
        check(f"convert_{tag}_decodes_clean", dec.returncode == 0 and not dec.stderr.strip(), dec.stderr[-300:])
        check(f"convert_{tag}_source_unchanged", sha(src) == before)
        if dims == (720, 1280):   # portrait phone clip: never upscaled, stays upright
            raw = subprocess.run([ff, "-v", "error", "-ss", "2", "-i", str(out), "-frames:v", "1", "-vf", "scale=90:160", "-f", "rawvideo",
                                  "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            top, bot = raw[: 90 * 10 * 3], raw[-90 * 10 * 3:]
            red_top = sum(top[0::3]) > sum(top[2::3]) + 60 * 900 and sum(bot[2::3]) > sum(bot[0::3]) + 60 * 900
            check(f"convert_{tag}_upright", red_top)
    hlg = fx / "hdr" / "hlg" / "hlg.mov"
    if hlg.is_file():
        res = convert_file(hlg, "share_1080p", output_dir=out_dir)
        raw = subprocess.run([ff, "-v", "error", "-ss", "2", "-i", res["output"], "-frames:v", "1", "-vf", "scale=128:72", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        px = lambda x, y: tuple(raw[(y * 128 + x) * 3:(y * 128 + x) * 3 + 3]) if len(raw) == 128 * 72 * 3 else None
        red, grey = px(12, 8), px(115, 8)
        check("convert_hdr_hlg_normal_colours", red and grey and red[0] >= 160 and red[1] <= 70 and 100 <= grey[1] <= 160, (red, grey))
    # the NVIDIA way taken where this PC has no such card (as on the test machine): the conversion is made on the
    # processor instead, whole and right
    from archivist import converter as cv0
    cv0._GPU[:] = [True]
    try:
        gres = convert_file(big, "share_1080p", output_dir=out_dir)
    finally:
        cv0._GPU[:] = []
    gv = [x for x in _probe(Path(gres["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    gdur = float(_probe(Path(gres["output"]))["format"]["duration"])
    check("convert_card_failure_falls_back_to_processor", gres["made_on"] in ("cpu", "nvidia") and (int(gv["width"]), int(gv["height"])) == (1920, 1080)
          and abs(gdur - 8.0) <= 0.15 and frames(ff, gres["output"]) >= frames(ff, big) - 1, (gres["made_on"], gv.get("width"), gv.get("height"), gdur))
    check("convert_no_part_files", not list(out_dir.glob("*.part*")))
    # two conversions of one video at the same moment: two outputs (each name reserved), both whole
    import threading
    from archivist import converter as cv
    small = fx / "phone" / "переменная частота.mp4"
    both, errs = [], []

    def one():
        try:
            both.append(convert_file(small, "small_720p", output_dir=out_dir)["output"])
        except Exception as exc:
            errs.append(repr(exc))
    ts = [threading.Thread(target=one) for _ in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]
    clean = [subprocess.run([ff, "-v", "error", "-i", o, "-f", "null", "-"], capture_output=True, text=True).stderr.strip() == "" for o in both]
    check("convert_twice_at_once_two_whole_outputs", len(set(both)) == 2 and all(clean) and not errs, (both, clean, errs))
    # "Fit under N MB" (two passes) cancelled half way: no .part, no empty reserved name, no pass logs left
    calls = {"n": 0}

    def cancel_soon():
        calls["n"] += 1
        return calls["n"] > 6
    out2 = work / "Converted cancel"
    try:
        convert_file(big, "share_1080p", target_mb=60, cancel_cb=cancel_soon, output_dir=out2)
        cancelled = False
    except RuntimeError as exc:
        cancelled = str(exc) == "cancelled"
    left = [x.name for x in out2.glob("*")] + [x.name for x in (work / "home" / "data").glob("ffmpeg2pass-*")]
    check("convert_cancel_leaves_nothing", cancelled and not left, (cancelled, left))
    # at the next start: names reserved by a conversion the app was closed during go, finished conversions stay
    (out_dir / "x_share_1080p.mp4").write_bytes(b"")
    (out_dir / "y_share_1080p.part.mp4").write_bytes(b"0" * 100)
    cv._sweep_converted(out_dir)
    check("convert_start_sweeps_interrupted_names_only", not (out_dir / "x_share_1080p.mp4").exists()
          and not (out_dir / "y_share_1080p.part.mp4").exists() and all(Path(o).is_file() for o in both))
    # parts of one recording, as a GoPro splits a long one (GX010077, GX020077, GX030077), joined into one video: the
    # whole length, every frame, the sound in step after every join; the parts in a folder with an apostrophe
    from archivist.converter import join_files, join_check, part_key, gopro_recording, start_convert_job, convert_job_snapshot
    sys.path.insert(0, str(HERE))
    from av_sync_check import flashes, beeps
    whole = src_dir / "whole_sync.mp4"
    if not whole.exists():
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30", "-f", "lavfi", "-i",
                        "aevalsrc='0.3*sin(2*PI*260*t)+if(lt(mod(t-0.3,1),0.04),0.9*sin(2*PI*1000*t),0)':s=48000", "-t", "14",
                        "-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t-0.3,1),0.0333)'",
                        "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", str(whole)], check=True)
    rec = src_dir / "O'Brien — части"
    rec.mkdir(exist_ok=True)
    for f in rec.glob("*"):
        f.unlink()
    subprocess.run([ff, "-v", "error", "-y", "-i", str(whole), "-map", "0", "-c", "copy", "-f", "segment", "-segment_times", "4.6,9.4",
                    "-segment_start_number", "1", "-reset_timestamps", "1", str(rec / "GX%02d0077.MP4")], check=True)
    parts = sorted(rec.glob("GX*.MP4"), key=lambda q: part_key(q.name), reverse=False)
    check("join_parts_in_recording_order", [q.name for q in parts] == ["GX010077.MP4", "GX020077.MP4", "GX030077.MP4"]
          and gopro_recording([q.name for q in parts]) == "0077", [q.name for q in parts])
    res = join_files(parts, "share_1080p", output_dir=out_dir)
    jo = Path(res["output"])
    dur = float(_probe(jo)["format"]["duration"])
    check("join_whole_length_one_file", abs(dur - 14.0) <= 0.15 and res["joined"] == 3 and "_joined_" in jo.name
          and res["source_bytes"] == sum(q.stat().st_size for q in parts), (dur, jo.name, res["source_bytes"]))
    fs, fo = frames(ff, whole), frames(ff, jo)
    check("join_every_frame", abs(fo - fs) <= 2, (fs, fo))
    fl, bp = flashes(ff, jo), beeps(ff, jo)
    offs = [min((b - f for b in bp), key=abs) for f in fl] if bp else []
    n_src = len(flashes(ff, whole))       # (a flash frame may fall between frames in the source too)
    check("join_sound_in_step_after_every_join", n_src >= 10 and len(fl) == n_src and bool(offs) and all(-0.025 <= o <= 0.040 for o in offs),
          (n_src, len(fl), [round(o, 3) for o in offs]))
    vd_j, ad_j = av_durations(jo, ff, 30.0)
    dec = subprocess.run([ff, "-v", "error", "-i", str(jo), "-f", "null", "-"], capture_output=True, text=True)
    check("join_sound_as_long_as_picture_decodes_clean", ad_j is not None and abs(vd_j - ad_j) <= 0.1 and not dec.stderr.strip(),
          (vd_j, ad_j, dec.stderr[-300:]))
    other = fx / "phone" / "Отпуск — пляж.mp4"
    try:
        join_check(ff, [parts[0], other])
        refused = None
    except ValueError as exc:
        refused = str(exc)
    check("join_refuses_different_videos_naming_one", bool(refused) and refused.endswith("Different: " + other.name), refused)
    # the same through a converter job of files chosen on this PC (not in the library), given in the wrong order
    from archivist.db import init_db
    init_db()

    def wait_job(jid):
        for _ in range(600):
            j = convert_job_snapshot(jid)
            if j["status"] in ("finished", "failed", "cancelled"):
                return j
            time.sleep(0.5)
        return convert_job_snapshot(jid)
    jj = wait_job(start_convert_job([], "small_720p", paths=[str(q) for q in reversed(parts)], join=True))
    outs = (jj.get("options") or {}).get("outputs") or []
    check("join_job_of_chosen_files", jj["status"] == "finished" and len(outs) == 1 and outs[0].get("joined") == 3
          and [Path(x).name for x in outs[0].get("sources", [])] == ["GX010077.MP4", "GX020077.MP4", "GX030077.MP4"]
          and jj["message"] == "Joined 3 parts into one video" and Path(outs[0]["output"]).is_file()
          and (jj["done"], jj["total"]) == (1, 1), (jj["status"], jj["message"], jj["done"], jj["total"], outs))
    # a cut: only 3.3 s .. 9.3 s of the video, from exactly there, the sound in step
    cres = convert_file(whole, "share_1080p", output_dir=out_dir, cut=(3.3, 9.3))
    cdur = float(_probe(Path(cres["output"]))["format"]["duration"])
    cfl, cbp = flashes(ff, cres["output"]), beeps(ff, cres["output"])
    coffs = [min((b - f for b in cbp), key=abs) for f in cfl] if cbp else []
    check("convert_cut_only_that_part_in_step", abs(cdur - 6.0) <= 0.1 and cres["cut"] == [3.3, 9.3] and "_cut_" in Path(cres["output"]).name
          and len(cfl) >= 5 and abs(cfl[0]) <= 0.04 and all(-0.025 <= o <= 0.040 for o in coffs), (cdur, cres.get("cut"), [round(x, 3) for x in cfl], [round(o, 3) for o in coffs]))
    # "Save this picture": a photo of one moment at the video's full size, upright, next to the converted videos
    from archivist.converter import save_frame
    from PIL import Image
    ph = save_frame(whole, 3.3, out_dir)
    with Image.open(ph) as im:
        psize, light = im.size, sum(im.convert("L").resize((8, 8)).tobytes()) / 64
    up = save_frame(fx / "phone" / "Отпуск — пляж.mp4", 1.0, out_dir)
    with Image.open(up) as im:
        usize = im.size
    try:
        save_frame(whole, 99, out_dir); beyond = None
    except ValueError as exc:
        beyond = str(exc)
    # the picture shown at the moment (a 1-picture-a-second clip at 2.5 s: picture 2, not 3); the very end; square
    # pixels (HDV 1440x1080 with 4:3 pixels -> 1920x1080)
    slow = src_dir / "one_per_second.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=1:d=6", "-vf",
                    "drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:enable='eq(n,2)'", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", str(slow)], check=True)
    from archivist.media import probe_duration as _pd
    with Image.open(save_frame(slow, 2.5, out_dir)) as im:
        at25 = sum(im.convert("L").resize((8, 8)).tobytes()) / 64
    last = save_frame(whole, float(_pd(whole)), out_dir)
    with Image.open(save_frame(fx / "anamorphic" / "HDV_1440.mp4", 1.0, out_dir)) as im:
        hdv = im.size
    check("save_the_picture_shown_at_that_moment", at25 > 200 and last.is_file() and last.stat().st_size > 100 and hdv == (1920, 1080),
          (at25, last.name, hdv))
    check("save_a_picture_of_a_moment", ph.name == "whole_sync_frame_0m03s.jpg" and psize == (640, 360) and light > 200
          and usize == (720, 1280) and beyond == "That moment is not in the video", (ph.name, psize, light, usize, beyond))
    # "Turn the picture": 90° right (a landscape video becomes portrait; a phone video turned after its own rotation)
    tr = convert_file(whole, "share_1080p", output_dir=out_dir, turn=90)
    tv = [x for x in _probe(Path(tr["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    tp = convert_file(fx / "phone" / "Отпуск — пляж.mp4", "share_1080p", output_dir=out_dir, turn=90)
    tpv = [x for x in _probe(Path(tp["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    t1 = subprocess.run([ff, "-v", "error", "-ss", "1", "-i", tr["output"], "-frames:v", "1", "-vf", "scale=36:64", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    t0 = subprocess.run([ff, "-v", "error", "-ss", "1", "-i", str(whole), "-frames:v", "1", "-vf", "transpose=1,scale=36:64", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    diff = sum(abs(a - b) for a, b in zip(t0, t1)) / max(1, len(t0))
    check("convert_turn_the_picture", (int(tv["width"]), int(tv["height"])) == (360, 640) and (int(tpv["width"]), int(tpv["height"])) == (1280, 720)
          and tr.get("turn") == 90 and "_turned_" in Path(tr["output"]).name and len(t0) == len(t1) == 36 * 64 * 3 and diff < 20,
          (tv.get("width"), tv.get("height"), tpv.get("width"), tpv.get("height"), Path(tr["output"]).name, diff))
    # "Without sound": the copy has no sound at all (one video, and joined parts)
    mres = convert_file(parts[0], "small_720p", output_dir=out_dir, mute=True)
    jm = join_files(parts, "small_720p", output_dir=out_dir, mute=True)
    no_a = lambda f: not [x for x in _probe(Path(f)).get("streams", []) if x.get("codec_type") == "audio"]
    check("convert_without_sound", no_a(mres["output"]) and no_a(jm["output"]) and mres.get("mute") is True and jm.get("mute") is True
          and "_nosound_" in Path(mres["output"]).name and "_joined_nosound_" in Path(jm["output"]).name
          and abs(float(_probe(Path(jm["output"]))["format"]["duration"]) - 14.0) <= 0.15, (mres["output"], jm["output"]))
    # a card with two recordings (0078 in two parts, 0079 in one): one video per recording, each in its order
    card = src_dir / "card"
    card.mkdir(exist_ok=True)
    for f in card.glob("*"):
        f.unlink()
    subprocess.run([ff, "-v", "error", "-y", "-i", str(whole), "-map", "0", "-c", "copy", "-f", "segment", "-segment_times", "7",
                    "-segment_start_number", "1", "-reset_timestamps", "1", str(card / "GX%02d0078.MP4")], check=True)
    import shutil as _sh
    _sh.copy(parts[0], card / "GX010079.MP4")
    jg = wait_job(start_convert_job([], "small_720p", paths=[str(x) for x in sorted(card.glob("*.MP4"), reverse=True)], join=True))
    og = (jg.get("options") or {}).get("outputs") or []
    durs = [round(float(_probe(Path(o["output"]))["format"]["duration"]), 1) for o in og if o.get("output")]
    check("join_one_video_per_recording", jg["status"] == "finished" and len(og) == 2 and og[0].get("joined") == 2
          and [Path(x).name for x in og[0].get("sources", [])] == ["GX010078.MP4", "GX020078.MP4"] and not og[1].get("joined")
          and Path(og[1]["source"]).name == "GX010079.MP4" and abs(durs[0] - 14.0) <= 0.2 and (jg["done"], jg["total"]) == (2, 2)
          and jg["message"] == "Joined into 2 videos (3 parts)", (jg["status"], jg["message"], jg["done"], jg["total"], durs, og))
    # GoPro-like parts: 4K 60 fps HEVC, full-range picture, stereo sound, a timecode track; split as the camera does,
    # joined into one 1080p video - whole length, every frame, TV levels
    gp = src_dir / "gopro4k"
    gp.mkdir(exist_ok=True)
    for f in gp.glob("*"):
        f.unlink()
    gw = gp / "whole.mov"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=3840x2160:rate=60", "-f", "lavfi", "-i",
                    "sine=frequency=500:sample_rate=48000", "-t", "4", "-c:v", "libx265", "-preset", "ultrafast", "-x265-params",
                    "log-level=error:keyint=60", "-tag:v", "hvc1", "-pix_fmt", "yuvj420p", "-color_range", "pc", "-c:a", "aac", "-ac", "2",
                    "-timecode", "00:00:00:00", "-f", "mov", str(gw)], check=True)
    subprocess.run([ff, "-v", "error", "-y", "-i", str(gw), "-map", "0:v", "-map", "0:a", "-c", "copy", "-f", "segment", "-segment_times", "2",
                    "-segment_start_number", "1", "-reset_timestamps", "1", "-segment_format", "mp4", str(gp / "GX%02d0012.MP4")], check=True)
    gw.unlink()
    def levels(y):                         # the darkest and brightest 1 % of the picture (an encoder's ringing aside)
        ys = sorted(y)
        return (ys[len(ys) // 100], ys[-len(ys) // 100]) if ys else (None, None)

    def tv_of(src, t, out, t_out):
        """The copy's levels are the source's full-range levels put into 16-235 (not kept full range)."""
        sy = subprocess.run([ff, "-v", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1", "-vf", "scale=960:540",
                             "-f", "rawvideo", "-pix_fmt", "yuvj420p", "-"], capture_output=True).stdout[: 960 * 540]
        desc = subprocess.run([ff, "-hide_banner", "-i", str(out)], capture_output=True, text=True).stderr
        vline = next((x for x in desc.splitlines() if " Video: " in x), "")
        full = "(pc" in vline or "yuvj" in vline          # tagged full range: not what a copy must be
        # the stored values as they are (read in the tagged range: no conversion by the reading FFmpeg either)
        oy = subprocess.run([ff, "-v", "error", "-ss", str(t_out), "-i", str(out), "-frames:v", "1", "-vf",
                             "scale=960:540:in_range=tv:out_range=tv", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                            capture_output=True).stdout[: 960 * 540]
        (slo, shi), (olo, ohi) = levels(sy), levels(oy)
        want = (16 + slo * 219 / 255, 16 + shi * 219 / 255)
        return (not full and abs(olo - want[0]) <= 6 and abs(ohi - want[1]) <= 6 and shi - want[1] > 8), (vline.strip()[:90], slo, shi, olo, ohi)
    gparts = sorted(gp.glob("GX*.MP4"), key=lambda q: part_key(q.name))
    t0 = time.time()
    g4 = join_files(gparts, "share_1080p", output_dir=out_dir)
    g4s = time.time() - t0
    g4v = [x for x in _probe(Path(g4["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    g4d = float(_probe(Path(g4["output"]))["format"]["duration"])
    g4ok, g4lv = tv_of(gparts[0], 1, g4["output"], 1)
    check("join_gopro_like_4k_hevc_parts", len(gparts) == 2 and (int(g4v["width"]), int(g4v["height"])) == (1920, 1080) and abs(g4d - 4.0) <= 0.1
          and frames(ff, g4["output"]) >= 239 and g4ok, ([q.name for q in gparts], g4v.get("width"), g4d, frames(ff, g4["output"]), g4lv))
    print(f"INFO 4K HEVC 60 fps, 4 s in two parts -> 1080p: {g4s:.1f} s on this machine ({g4.get('made_on')})", flush=True)
    gk = convert_file(gparts[0], "keep_resolution", output_dir=out_dir, cut=(0.5, 1.5))
    gkok, gklv = tv_of(gparts[0], 1.0, gk["output"], 0.5)
    check("convert_full_range_camera_video_to_tv_levels_without_resize", gkok, gklv)
    # the Auto Edit reel and a finished video (Voice-over and text) from a camera's full-range pieces: TV levels too
    import types
    sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))
    import p11_folder_to_reel_r3 as r3
    reel2 = out_dir / "reel_two_pieces.mp4"
    r3.render_dissolve_block(types.SimpleNamespace(FFMPEG=ff), [str(gparts[0]), str(gparts[1])], [2.0, 2.0],
                             [{"duration_s": 0.5}], reel2)
    reel1 = out_dir / "reel_one_piece.mp4"
    r3.render_dissolve_block(types.SimpleNamespace(FFMPEG=ff), [str(gparts[0])], [2.0], [], reel1)
    ok2, lv2 = tv_of(gparts[0], 0.5, reel2, 0.5)
    ok1, lv1 = tv_of(gparts[0], 0.5, reel1, 0.5)
    from archivist import voice as vo
    fin = out_dir / "finish_probe"
    shutil.rmtree(fin, ignore_errors=True); fin.mkdir()
    vo._burn(Path(gparts[0]), None, [], fin, keep_sound=True, offset=0.0)
    ok3, lv3 = tv_of(gparts[0], 0.5, fin / "video.mp4", 0.5)
    check("reel_and_finished_video_from_full_range_footage_at_tv_levels", ok1 and ok2 and ok3, (lv1, lv2, lv3))
    # (not counted) the Auto Edit engine's way of making a piece ("-vf ...,format=yuv420p ... -pix_fmt yuv420p"): does
    # this FFmpeg keep a camera's full range there? Reported for the next step.
    eng = out_dir / "engine_way_probe.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-ss", "0.5", "-i", str(gparts[0]), "-t", "1", "-vf", "scale=1920:1080,format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(eng)], check=False)
    if eng.is_file():
        eok, elv = tv_of(gparts[0], 1.0, eng, 0.5)
        print(f"INFO the engine's way with a full-range camera video: {'TV levels' if eok else 'FULL RANGE KEPT'} {elv}", flush=True)
        eng.unlink()
    jn = wait_job(start_convert_job([], "small_720p", paths=[str(parts[0]), str(parts[1])]))
    outs = (jn.get("options") or {}).get("outputs") or []
    check("convert_job_of_chosen_files_one_by_one", jn["status"] == "finished" and len(outs) == 2 and not any(o.get("joined") for o in outs)
          and all(Path(o["output"]).is_file() for o in outs), (jn["status"], outs))
    # a folder of the person's own for the converted videos: the job writes there (and keeps it when resumed)
    from archivist.config import update_config
    own = work / "Мои сжатые видео"
    update_config(lambda c: c.setdefault("convert", {}).update(output_dir=str(own)))
    try:
        jo2 = wait_job(start_convert_job([], "small_720p", paths=[str(parts[2])]))
    finally:
        update_config(lambda c: c["convert"].pop("output_dir", None))
    o2 = ((jo2.get("options") or {}).get("outputs") or [{}])[0]
    check("convert_into_a_chosen_folder", jo2["status"] == "finished" and Path(o2.get("output", "")).parent == own
          and Path(o2["output"]).is_file() and (jo2.get("options") or {}).get("output_dir") == str(own), (jo2["status"], o2))
    # the app closed during a conversion into that folder: at the next start the job resumes there, its own leftovers
    # (a reserved empty name, a half-written .part) go, the person's files stay
    from archivist.converter import recover_convert_jobs
    from archivist.db import db as _db, now_iso as _now
    (own / "GX030077_small_720p_9.mp4").write_bytes(b"")
    (own / "GX030077_small_720p_8.part.mp4").write_bytes(b"x" * 50)
    (own / "notes.mp4").write_bytes(b"")
    with _db() as con:
        rj = con.execute("INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) "
                         "VALUES('convert','running',?,?,'converting','x',1,0,0,0,1,0,?)",
                         (_now(), _now(), json.dumps({"preset": "small_720p", "paths": [str(parts[1])], "output_dir": str(own), "outputs": []}))).lastrowid
        con.commit()
    rr = recover_convert_jobs()
    jr = wait_job(rj)
    ro = ((jr.get("options") or {}).get("outputs") or [{}])[0]
    left = sorted(x.name for x in own.iterdir())
    check("convert_resumed_in_a_chosen_folder_sweeps_only_its_own", rr.get("resumed") == 1 and jr["status"] == "finished"
          and Path(ro.get("output", "")).parent == own and "notes.mp4" in left and "GX030077_small_720p_9.mp4" not in left
          and "GX030077_small_720p_8.part.mp4" not in left, (rr, jr["status"], ro, left))
    try:
        start_convert_job([], "small_720p", paths=[str(parts[0]), str(other)], join=True)
        said = None
    except ValueError as exc:
        said = str(exc)
    check("join_job_refused_at_once", bool(said) and other.name in said, said)
    check("join_leaves_no_part_list", not list((work / "home" / "data").glob("join-*.txt")))
    # the card's result is checked by the picture's own length (a file's length can be its sound's)
    short_pic = src_dir / "pic2_sound6.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:d=2", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=48000:d=6", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(short_pic)], check=True)
    from archivist.media import probe_duration
    ps = cv0._picture_seconds(ff, short_pic)
    check("convert_picture_length_read_apart_from_sound", abs(ps - 2.0) <= 0.1 and abs(float(probe_duration(short_pic)) - 6.0) <= 0.1,
          (ps, probe_duration(short_pic)))
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

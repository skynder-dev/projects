"""Full-video Convert (existing Archivist feature, contract §9): whole video, original order and frame rate, H.264.

  python tests/convert_check.py <fixtures_dir> <work_dir>

Converts with the app's own converter.convert_file: a 1440p 60 fps clip -> High Quality 1080p, the rotated phone clip and
the VFR clip from <fixtures_dir>/phone. Checks: output size cap, frame rate kept, duration and frame count match the source
(no cut, no drop), full decode clean, upright portrait stays upright, audio kept, source bytes unchanged, no .part left.
"""
from __future__ import annotations

import hashlib, json, os, re, shutil, subprocess, sys, time
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
    # More options: speed (2x with its sound in step, 4x without sound), vertical 9:16 (cut / blurred background), a logo
    # in a corner, less wind noise (a 50 Hz hum taken down)
    from archivist import converter as cvx
    from archivist.config import HOME as _H
    no_a = lambda f: not [x for x in _probe(Path(f)).get("streams", []) if x.get("codec_type") == "audio"]
    s2 = convert_file(whole, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 2}))
    s2d = float(_probe(Path(s2["output"]))["format"]["duration"])
    # (a one-frame flash may be one of the frames a faster copy leaves out: the beeps are compared with their times,
    # every second at k + 0.3 s in the source -> (k + 0.3) / 2 in the copy)
    b2 = beeps(ff, s2["output"])
    f2 = [(k + 0.3) / 2 for k in range(14)]
    o2 = [min((b - f for b in b2), key=abs) for f in f2] if b2 else []
    s4 = convert_file(whole, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 4}))
    s4d = float(_probe(Path(s4["output"]))["format"]["duration"])
    # (a sound that starts 1 s after its picture - as cameras do - stays in step at 2x too)
    late = src_dir / "late_sound_1s.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(whole), "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", "atrim=start=1.0",
                    "-c:a", "aac", str(late)], check=True)
    sl = convert_file(late, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 2}))
    bl = beeps(ff, sl["output"])
    ol = [min((b - f for b in bl), key=abs) for f in [(k + 0.3) / 2 for k in range(1, 13)]] if bl else []
    o2 = o2 + ol
    check("convert_faster_2x_in_step_4x_without_sound", abs(s2d - 7.0) <= 0.1 and len(f2) >= 10 and o2 and all(-0.03 <= o <= 0.045 for o in o2)
          and abs(s4d - 3.5) <= 0.1 and no_a(s4["output"]) and "_x4_" in Path(s4["output"]).name,
          (s2d, len(f2), [round(o, 3) for o in o2], s4d, Path(s4["output"]).name))
    vc = convert_file(whole, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"vertical": "crop"}))
    vb = convert_file(whole, "small_720p", output_dir=out_dir, extra=cvx.clean_extra({"vertical": "blur"}))
    vcs = [x for x in _probe(Path(vc["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    vbs = [x for x in _probe(Path(vb["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    # 4:3 pixels (HDV 1440x1080 shown 1920x1080): squared before the vertical cut - a circle stays round
    hv = convert_file(fx / "anamorphic" / "HDV_1440.mp4", "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"vertical": "blur"}))
    hvs = [x for x in _probe(Path(hv["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    tt = convert_file(fx / "formats" / "two_tracks.mp4", "small_720p", output_dir=out_dir, extra=cvx.clean_extra({"vertical": "crop"}))
    tracks = len([x for x in _probe(Path(tt["output"])).get("streams", []) if x.get("codec_type") == "audio"])
    check("convert_vertical_9_16", (int(vcs["width"]), int(vcs["height"])) == (1080, 1920) and (int(vbs["width"]), int(vbs["height"])) == (720, 1280)
          and (int(hvs["width"]), int(hvs["height"])) == (1080, 1920) and str(hvs.get("sample_aspect_ratio") or "1:1") in ("1:1", "N/A")
          and tracks == 2
          and abs(float(_probe(Path(vc["output"]))["format"]["duration"]) - 14.0) <= 0.15, (vcs.get("width"), vcs.get("height"), vbs.get("width"), vbs.get("height"), hvs, tracks))
    (_H / "data").mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (300, 100), (255, 0, 255, 255)).save(_H / "data" / cvx.LOGO_FILE)
    lgo = convert_file(whole, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"logo": True}))
    px = subprocess.run([ff, "-v", "error", "-ss", "2", "-i", lgo["output"], "-frames:v", "1", "-vf", "crop=8:8:iw-40:ih-20", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    mag = (sum(px[0::3]) / 64, sum(px[1::3]) / 64, sum(px[2::3]) / 64) if len(px) == 192 else None
    check("convert_logo_in_the_corner", mag and mag[0] > 180 and mag[2] > 180 and mag[1] < 80 and "_logo_" in Path(lgo["output"]).name, mag)
    hum = src_dir / "hum.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:d=4", "-f", "lavfi", "-i",
                    "aevalsrc='0.5*sin(2*PI*50*t)+0.2*sin(2*PI*1000*t)':s=48000:d=4", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    "-shortest", str(hum)], check=True)
    def low_rms(f):
        t = subprocess.run([ff, "-hide_banner", "-i", str(f), "-map", "0:a:0", "-af", "lowpass=f=80,astats=metadata=0", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        m = re.findall(r"RMS level dB:\s*(-?[\d.]+|-inf)", t)
        return float(m[-1]) if m and m[-1] != "-inf" else -200.0
    wnd = convert_file(hum, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"wind": True}))
    before, after = low_rms(hum), low_rms(wnd["output"])
    check("convert_less_wind_noise", before - after >= 12 and not no_a(wnd["output"]), (before, after))
    # slow motion: a 60 fps video at half speed - every picture shown, at 30 a second, twice as long, its sound in step;
    # 120 fps at half speed: 60 a second; at a quarter: 4x as long, no sound
    s60 = src_dir / "sync_60fps.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=60", "-f", "lavfi", "-i",
                    "aevalsrc='0.3*sin(2*PI*260*t)+if(lt(mod(t-0.3,1),0.04),0.9*sin(2*PI*1000*t),0)':s=48000", "-t", "5",
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "60", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(s60)], check=True)
    h2 = convert_file(s60, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 0.5}))
    h2v = [x for x in _probe(Path(h2["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    h2d = float(_probe(Path(h2["output"]))["format"]["duration"])
    bh = beeps(ff, h2["output"])
    oh = [min((b - (k + 0.3) * 2 for b in bh), key=abs) for k in range(5)] if bh else []
    h4 = convert_file(s60, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 0.25, "loud": True}))
    h4d = float(_probe(Path(h4["output"]))["format"]["duration"])
    s120 = src_dir / "fast_120fps.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=120", "-t", "2", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(s120)], check=True)
    h1 = convert_file(s120, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 0.5}))
    h1v = [x for x in _probe(Path(h1["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    check("convert_slow_motion", abs(h2d - 10.0) <= 0.15 and h2v.get("r_frame_rate") == "30/1" and frames(ff, h2["output"]) >= frames(ff, s60) - 1
          and len(oh) == 5 and all(-0.03 <= o <= 0.045 for o in oh) and "_slow2x_" in Path(h2["output"]).name
          and abs(h4d - 20.0) <= 0.2 and no_a(h4["output"]) and "_slow4x_" in Path(h4["output"]).name
          and "evensound" not in Path(h4["output"]).name and h4["extra"] == {"speed": 0.25}
          and h1v.get("r_frame_rate") == "60/1" and frames(ff, h1["output"]) >= frames(ff, s120) - 1,
          (h2d, h2v.get("r_frame_rate"), frames(ff, h2["output"]), frames(ff, s60), [round(o, 3) for o in oh], h4d, h1v.get("r_frame_rate"),
           frames(ff, h1["output"]), frames(ff, s120)))
    # two videos joined at ½× (the second one's sound starts 1 s after its picture): the second one in step too
    hj = join_files([whole, late], "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"speed": 0.5}))
    bj = beeps(ff, hj["output"])
    oj = [min((b - t for b in bj), key=abs) for t in [(k + 0.3) * 2 for k in range(14)] + [(14 + k + 0.3) * 2 for k in range(1, 13)]] if bj else []
    check("convert_joined_at_half_speed_in_step", len(oj) == 26 and all(-0.04 <= o <= 0.06 for o in oj)
          and abs(float(_probe(Path(hj["output"]))["format"]["duration"]) - 56.0) <= 0.3, [round(o, 3) for o in oj])
    # "Even out the sound": a quiet recording (sound starting 1 s after the picture) made as loud as players play it
    # (-16 LUFS), in step; at 2x with less wind too
    def lufs(f):
        t = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(f), "-map", "0:a:0", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        m = re.findall(r"I:\s*(-?[\d.]+) LUFS", t)
        return float(m[-1]) if m else 0.0
    def a_start(f):
        st = [x for x in _probe(Path(f)).get("streams", []) if x.get("codec_type") == "audio"]
        return float(st[0].get("start_time") or 0) if st else 0.0
    quiet = src_dir / "quiet_late_sound.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(whole), "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af",
                    "atrim=start=1.0,volume=0.03", "-c:a", "aac", str(quiet)], check=True)
    ev = convert_file(quiet, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"loud": True}))
    bq = [b + a_start(ev["output"]) for b in beeps(ff, ev["output"])]
    oq = [min((b - (k + 0.3) for b in bq), key=abs) for k in range(1, 13)] if bq else []
    ev2 = convert_file(quiet, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"loud": True, "speed": 2, "wind": True}))
    l0, l1, l2 = lufs(quiet), lufs(ev["output"]), lufs(ev2["output"])
    check("convert_even_out_the_sound", l0 < -35 and abs(l1 + 16) <= 1.5 and abs(l2 + 16) <= 2.0 and len(oq) == 12
          and all(-0.03 <= o <= 0.045 for o in oq) and "_evensound_" in Path(ev["output"]).name
          and abs(float(_probe(Path(ev2["output"]))["format"]["duration"]) - 7.0) <= 0.15,
          (l0, l1, l2, [round(o, 3) for o in oq], Path(ev["output"]).name))
    # "Brighter": a video filmed in the dark comes out lighter (also with a logo on it); a normal one is not washed out
    dark = src_dir / "dark.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30,eq=brightness=-0.3:contrast=0.5", "-t", "3",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(dark)], check=True)
    def yavg(f):
        t = subprocess.run([ff, "-hide_banner", "-i", str(f), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                            "-f", "null", "-"], capture_output=True, text=True).stdout
        v = re.findall(r"YAVG=([\d.]+)", t)
        return sum(float(x) for x in v) / len(v) if v else 0.0
    br = convert_file(dark, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"bright": True}))
    brl = convert_file(dark, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"bright": True, "logo": True}))
    brn = convert_file(whole, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"bright": True}))
    y0, y1, y2, yn0, yn1 = yavg(dark), yavg(br["output"]), yavg(brl["output"]), yavg(whole), yavg(brn["output"])
    check("convert_brighter", y1 - y0 >= 25 and y2 - y0 >= 25 and yn1 - yn0 <= 25 and "_brighter_" in Path(br["output"]).name,
          (round(y0, 1), round(y1, 1), round(y2, 1), round(yn0, 1), round(yn1, 1)))
    # the More options and a turned picture on the card's way (decoded and made smaller there, the rest as on the
    # processor) - the card stood in for by the processor (no NVIDIA card on the test machine): the graph, the sound in
    # step at 2x, the logo, the clock, Brighter, the turn - all on the "card" picture
    sync_big = src_dir / "sync_1440p.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=2560x1440:rate=30", "-f", "lavfi", "-i",
                    "aevalsrc='0.3*sin(2*PI*260*t)+if(lt(mod(t-0.3,1),0.04),0.9*sin(2*PI*1000*t),0)':s=48000", "-t", "6",
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(sync_big)],
                   check=True)
    real_g = (cvx.gpu_plan, cvx.gpu_ok, cvx.gpu_extra_ok)
    def stand_in(sig_, preset_, hdr_=None, interlaced_=False):
        pl = real_g[0](sig_, preset_, hdr_, interlaced_)
        if not pl:
            return None
        W_, H_ = pl["size"]
        return {**pl, "pre": [], "head": f"scale={W_}:{H_},format=nv12",
                "codec": ["-color_range", "tv", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"]}
    cvx.gpu_plan, cvx.gpu_ok, cvx.gpu_extra_ok = stand_in, (lambda: True), (lambda: True)
    try:
        gx = convert_file(sync_big, "share_1080p", output_dir=out_dir, turn=90,
                          extra=cvx.clean_extra({"speed": 2, "clock": True, "bright": True, "logo": True}))
        gv_ = [x for x in _probe(Path(gx["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
        gd_ = float(_probe(Path(gx["output"]))["format"]["duration"])
        gb_ = beeps(ff, gx["output"])
        go_ = [min((b - (k + 0.3) / 2 for b in gb_), key=abs) for k in range(6)] if gb_ else []
        gvert = convert_file(sync_big, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"vertical": "crop"}))
    finally:
        cvx.gpu_plan, cvx.gpu_ok, cvx.gpu_extra_ok = real_g
    check("more_options_on_the_card_way", gx.get("made_on") == "nvidia" and (int(gv_["width"]), int(gv_["height"])) == (1080, 1920)
          and abs(gd_ - 3.0) <= 0.15 and len(go_) == 6 and all(-0.03 <= o <= 0.045 for o in go_) and gvert.get("made_on") == "cpu",
          (gx.get("made_on"), gv_.get("width"), gv_.get("height"), gd_, [round(o, 3) for o in go_], gvert.get("made_on")))
    # "Date and time in the corner": the recording's time read as each maker writes it (GoPro / DJI: their clock as
    # written; a phone: UTC shown in this PC's zone; an iPhone: its local time; nothing: the file's date minus the
    # length), shown every second - at 2x the clock runs twice as fast, a cut starts at its start, joined videos each
    # with their own time, parts of one GoPro recording one after another
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    def tagged(name, *meta, d=4):
        f = src_dir / name
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x808080:size=640x360:rate=30", "-t", str(d), *meta,
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(f)], check=True)
        return f
    cg = tagged("camera_clock.mp4", "-metadata", "creation_time=2026-10-23T14:05:07Z", "-metadata:s:v", "handler_name=GoPro H.265")
    pfold = src_dir / "GoPro backup"                    # (a folder's name says nothing of the video)
    pfold.mkdir(exist_ok=True)
    cp = tagged("GoPro backup/phone_android.mp4", "-movflags", "use_metadata_tags", "-metadata", "com.android.version=14",
                "-metadata", "creation_time=2026-10-23T11:05:11Z")
    cc = tagged("dashcam.mp4", "-metadata", "creation_time=2026-10-23T14:05:07Z")
    ci = tagged("iphone.mov", "-movflags", "use_metadata_tags", "-metadata", "com.apple.quicktime.creationdate=2026-10-23T14:05:07+0300",
                "-metadata", "creation_time=2026-10-23T11:05:07Z")
    cn = tagged("no_time.mp4", "-map_metadata", "-1", "-fflags", "+bitexact")
    os.utime(cn, (1792764000, 1792764000))
    later = tagged("later.mp4", "-metadata", "creation_time=2026-10-23T15:00:00Z", "-metadata:s:v", "handler_name=GoPro H.265", d=2)
    rs = [cvx.recording_start(ff, x) for x in (cg, cp, ci, cn, cc)]
    # (an Android phone writes when the recording stopped: 11:05:11 UTC, 4 s long -> started 11:05:07 UTC)
    want_rs = [(_dt(2026, 10, 23, 14, 5, 7), "camera"), (_dt(2026, 10, 23, 11, 5, 7, tzinfo=_tz.utc).astimezone().replace(tzinfo=None), "phone"),
               (_dt(2026, 10, 23, 14, 5, 7), "phone"), (_dt.fromtimestamp(1792764000 - 4), "file"), (_dt(2026, 10, 23, 14, 5, 7), "camera")]
    jp, jh = cvx.clock_parts(ff, [cg, later], [4.0, 2.0])
    cut_p, _h = cvx.clock_parts(ff, [cg], [4.0], (1.5, 3.0))
    ass2 = cvx.clock_ass([(0.0, 3.0, _dt(2026, 10, 23, 23, 59, 58, 500000))], 2, (1920, 1080))
    lines2 = [x for x in ass2.splitlines() if x.startswith("Dialogue:")]
    ck = convert_file(cg, "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"clock": True}))
    plain = convert_file(cg, "share_1080p", output_dir=out_dir)
    def corner(f, t, x0):
        return subprocess.run([ff, "-v", "error", "-ss", str(t), "-i", str(f), "-frames:v", "1", "-vf", f"crop=200:40:{x0}:310", "-f", "rawvideo",
                               "-pix_fmt", "gray", "-"], capture_output=True).stdout
    cdiff = lambda a, b: sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))
    # (a grey picture: the box shows, and only its seconds change)
    c05, c15, p05 = corner(ck["output"], 0.5, 0), corner(ck["output"], 1.5, 0), corner(plain["output"], 0.5, 0)
    hc = convert_file(fx / "anamorphic" / "HDV_1440.mp4", "share_1080p", output_dir=out_dir, extra=cvx.clean_extra({"clock": True}))
    # pictures for a report with the date and time on them
    pk, pn = cvx.save_frames_every(cg, 2, out_dir, clock=True), cvx.save_frames_every(cg, 2, out_dir)
    def pcorner(folder):
        fs = sorted(Path(folder).glob("*.jpg"))
        with Image.open(fs[0]) as im:
            return im.convert("L").crop((0, 310, 200, 350)).tobytes(), len(fs)
    (pkc, pkn), (pnc, pnn) = pcorner(pk["output"]), pcorner(pn["output"])
    def fcorner(f):
        with Image.open(f) as im:
            return im.convert("L").crop((0, 310, 200, 350)).tobytes()
    fk, fn = fcorner(save_frame(cg, 1.5, out_dir, clock=True)), fcorner(save_frame(cg, 1.5, out_dir))
    hcs = [x for x in _probe(Path(hc["output"])).get("streams", []) if x.get("codec_type") == "video"][0]
    check("convert_date_and_time_in_the_corner", rs == want_rs and jh == "camera"
          and [(round(a, 2), round(b, 2), w) for a, b, w in jp] == [(0.0, 4.0, _dt(2026, 10, 23, 14, 5, 7)), (4.0, 2.0, _dt(2026, 10, 23, 15, 0))]
          and cut_p == [(0.0, 1.5, _dt(2026, 10, 23, 14, 5, 8, 500000))]
          and lines2 == ["Dialogue: 0,0:00:00.00,0:00:00.25,Clock,,0,0,0,,23.10.2026  23:59:58",
                         "Dialogue: 0,0:00:00.25,0:00:00.75,Clock,,0,0,0,,23.10.2026  23:59:59",
                         "Dialogue: 0,0:00:00.75,0:00:01.25,Clock,,0,0,0,,24.10.2026  00:00:00",
                         "Dialogue: 0,0:00:01.25,0:00:01.50,Clock,,0,0,0,,24.10.2026  00:00:01"]
          and ck.get("clock") == "camera" and "_clock_" in Path(ck["output"]).name and cdiff(c05, p05) > 10 and cdiff(c05, c15) > 0.2
          and not list((_H / "data").glob("clock-*")) and (int(hcs["width"]), int(hcs["height"])) == (1920, 1080)
          and str(hcs.get("sample_aspect_ratio") or "1:1") in ("1:1", "N/A")
          and pk.get("clock") == "camera" and pkn == pnn == 2 and cdiff(pkc, pnc) > 10 and "clock" not in pn and cdiff(fk, fn) > 10,
          (rs, jh, jp, cut_p, lines2, ck.get("clock"), cdiff(c05, p05), cdiff(c05, c15), hcs.get("width"), hcs.get("sample_aspect_ratio"),
           pk.get("clock"), pkn, pnn, cdiff(pkc, pnc), cdiff(fk, fn)))
    # pictures every N seconds (a report): a folder of JPEGs named by their moment, through a converter job
    jf = wait_job(start_convert_job([], "share_1080p", paths=[str(whole)], extra={"frames": 5}))
    of = ((jf.get("options") or {}).get("outputs") or [{}])[0]
    pics = sorted(x.name for x in Path(of.get("output", "/nonexistent")).glob("*.jpg")) if of.get("output") else []
    with Image.open(Path(of["output"]) / pics[0]) if pics else Image.new("RGB", (1, 1)) as im0:
        psz = im0.size
    try:
        start_convert_job([], "share_1080p", paths=[str(parts[0]), str(parts[1])], join=True, extra={"frames": 10}); fj = None
    except ValueError as exc:
        fj = str(exc)
    pct = src_dir / "Sale 20% off.mp4"                  # a % in the name is not a number pattern
    shutil.copy(slow, pct)
    pp = cvx.save_frames_every(pct, 2, out_dir)
    pdfb = Path(of["pdf"]).read_bytes() if of.get("pdf") and Path(of["pdf"]).is_file() else b""
    # (a long video: 2160 pictures on 270 pages, written in one pass, in about the time of the pictures themselves)
    many = [(Path(of["output"]) / pics[k % len(pics)], float(k * 5)) for k in range(2160)] if pics else []
    t_pdf = time.time()
    bigp = cvx.pictures_pdf(work / "many_pictures.pdf", many, "three hours.mp4", 5, None, report="Site 7 - roof, October") if many else None
    t_pdf = time.time() - t_pdf
    bigb = bigp.read_bytes() if bigp else b""
    check("pictures_in_one_pdf", pdfb[:5] == b"%PDF-" and len(re.findall(rb"/Type\s*/Page(?!s)", pdfb)) == 1
          and len(re.findall(rb"/Type\s*/Page(?!s)", bigb)) == 270 and b"/Count 270" in bigb and t_pdf < 240
          and Path(of["pdf"]).parent == Path(of["output"]) and Path(of["pdf"]).name == "whole_sync_pictures.pdf", (of.get("pdf"), len(pdfb), len(bigb), round(t_pdf, 1)))
    # pictures by seeking (each read from the key picture before its moment) = the same pictures as decoding the
    # whole video; a video with a 3 s gap in its pictures: no picture for the empty stretches, by either way
    gapv = src_dir / "gap_3s.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:d=4", "-vf",
                    "setpts='if(gte(T,2),PTS+3/TB,PTS)'", "-fps_mode", "vfr", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(gapv)], check=True)
    def both(src, every):
        dur_ = float(_pd(src)); tail_ = ["scale='trunc(iw*sar/2)*2':ih", "setsar=1", "format=gbrp", "format=yuvj420p"]
        got = []
        for mode in ("seek", "dec"):
            d = work / "pics_both" / f"{src.stem}_{mode}"
            shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
            nm = lambda t: f"p{int(t):05d}"
            got.append(cvx._pictures_by_seeking(ff, src, every, dur_, False, tail_, d, nm, None, None, None) if mode == "seek" else
                       cvx._pictures_by_decoding(ff, src, every, dur_, False, tail_, d, nm, None, None, None, None))
        same = len(got[0]) == len(got[1]) and all(a[0].name == b[0].name and a[0].read_bytes() == b[0].read_bytes() for a, b in zip(*got))
        return same, [x[0].name for x in got[0]], [x[0].name for x in got[1]]
    bw, bg = both(whole, 5), both(gapv, 1)
    # (a % in the name is a name; a DVD file - no exact seek in its container - and interlaced video are decoded whole)
    pctv = src_dir / "100% done.mp4"
    shutil.copy(whole, pctv)
    tl_ = ["scale='trunc(iw*sar/2)*2':ih", "setsar=1", "format=gbrp", "format=yuvj420p"]
    d_ = work / "pics_both" / "pct"
    shutil.rmtree(d_, ignore_errors=True); d_.mkdir(parents=True)
    by_seek_pct = cvx._pictures_by_seeking(ff, pctv, 5, 14.0, False, tl_, d_, lambda t: f"q{int(t):05d}", None, None, None)
    dvd = fx / "anamorphic" / "DVD_169.mpg"
    no_seek = [cvx._seekable(ff, dvd) if dvd.is_file() else False,
               cvx._pictures_by_seeking(ff, whole, 5, 14.0, True, tl_, d_, lambda t: f"r{int(t):05d}", None, None, None)]
    check("pictures_by_seeking_are_the_same", bw[0] and bw[1] == ["p00000.jpg", "p00005.jpg", "p00010.jpg"] and bg[0]
          and bg[1] == ["p00000.jpg", "p00001.jpg", "p00005.jpg", "p00006.jpg"] and len(by_seek_pct) == 3 and no_seek == [False, []]
          and cvx._seekable(ff, whole), (bw, bg, len(by_seek_pct), no_seek))
    check("pictures_every_n_seconds", jf["status"] == "finished" and of.get("frames") == 3 and pics == ["whole_sync_00m00s.jpg", "whole_sync_00m05s.jpg",
          "whole_sync_00m10s.jpg"] and psz == (640, 360) and Path(of["output"]).name == "whole_sync_pictures_every_5s"
          and sorted(x.name for x in Path(pp["output"]).glob("*.jpg")) == ["Sale 20% off_00m00s.jpg", "Sale 20% off_00m02s.jpg", "Sale 20% off_00m04s.jpg"]
          and fj and "whole videos" in fj, (jf["status"], of, pics, psz, fj))
    # two conversions started one after the other: the second waits in line and starts by itself when the first ends
    qa = start_convert_job([], "small_720p", paths=[str(whole)])
    qb = start_convert_job([], "small_720p", paths=[str(parts[0])], extra={"frames": 5})
    qb_first = convert_job_snapshot(qb)["status"]
    ja, jb = wait_job(qa), wait_job(qb)
    check("conversions_wait_in_line", qb_first == "waiting" and ja["status"] == "finished" and jb["status"] == "finished"
          and str(jb.get("started_at") or "") >= str(ja.get("finished_at") or "~")
          and ((jb.get("options") or {}).get("outputs") or [{}])[0].get("frames") == 1,
          (qb_first, ja["status"], jb["status"], ja.get("finished_at"), jb.get("started_at")))
    # a video gone before its job starts (a card not put back yet): a "Failed" line with its name, counted as done
    qa2 = start_convert_job([], "small_720p", paths=[str(whole)])
    gone = src_dir / "gone soon.mp4"
    shutil.copy(parts[0], gone)
    qb2 = start_convert_job([], "small_720p", paths=[str(parts[1]), str(gone)])
    qb2_first = convert_job_snapshot(qb2)["status"]
    gone.unlink()
    jb2 = wait_job(qb2); wait_job(qa2)
    outs2 = (jb2.get("options") or {}).get("outputs") or []
    check("a_missing_video_is_named", qb2_first == "waiting" and jb2["status"] == "finished" and (jb2["done"], jb2["total"]) == (2, 2)
          and jb2["failed"] == 1 and any(o.get("error") == "This video is not on this computer now" and o.get("source") == "gone soon.mp4"
                                          for o in outs2), (qb2_first, jb2["status"], jb2["done"], jb2["total"], jb2["failed"], outs2))
    # a size target: a phone video with a varying frame rate, joined chapters whose sound runs a little longer than
    # the picture (both used to fail: two passes saw different frames), a video without sound (its share not taken)
    tvfr = convert_file(fx / "phone" / "переменная частота.mp4", "share_1080p", target_mb=1, output_dir=out_dir)
    chd = src_dir / "chapters_long_sound"
    chd.mkdir(exist_ok=True)
    for f in chd.glob("*"):
        f.unlink()
    for n in (1, 2):
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:d=3", "-f", "lavfi", "-i",
                        "sine=frequency=500:sample_rate=48000:d=3.05", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", str(chd / f"GX0{n}0044.MP4")], check=True)
    tjn = join_files(sorted(chd.glob("*.MP4")), "share_1080p", target_mb=2, output_dir=out_dir)
    sil = src_dir / "drone_no_sound.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:d=20", "-c:v", "libx264", "-preset",
                    "ultrafast", "-pix_fmt", "yuv420p", str(sil)], check=True)
    tsil = convert_file(sil, "share_1080p", target_mb=3, output_dir=out_dir)
    sil_mb = Path(tsil["output"]).stat().st_size / 2**20
    check("size_target_with_gaps_and_without_sound", Path(tvfr["output"]).is_file() and Path(tjn["output"]).is_file()
          and abs(float(_probe(Path(tjn["output"]))["format"]["duration"]) - 6.05) <= 0.2 and 2.4 <= sil_mb <= 3.1,
          (tvfr.get("output"), tjn.get("output"), round(sil_mb, 2)))
    # a half-copied video (its index at the front, as a messenger download has): the copy is made and says it is short
    front = src_dir / "front_index.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(whole), "-c", "copy", "-movflags", "+faststart", str(front)], check=True)
    halfv = src_dir / "half copied.mp4"
    halfv.write_bytes(front.read_bytes()[: front.stat().st_size // 2])
    hshort, hfull = convert_file(halfv, "small_720p", output_dir=out_dir), convert_file(front, "small_720p", output_dir=out_dir)
    check("a_half_copied_video_is_said_short", isinstance(hshort.get("short"), list) and hshort["short"][0] < 10
          and hshort["short"][1] >= 13.5 and "short" not in hfull, (hshort.get("short"), hfull.get("short")))
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
        print(f"INFO a raw engine piece (before the reel render puts it into TV levels): {'TV levels' if eok else 'full range'} {elv}", flush=True)
        eng.unlink()
    # "Check this PC -> Test converting on the graphics card": on a machine without an NVIDIA card the processor's time
    # is measured, the card is said to be missing, and conversions do not try it afterwards
    from archivist import converter as cvt
    from archivist.config import update_config as _uc2
    t0 = time.time()
    assert cvt.start_gpu_test(work / "gpu_test")
    while cvt.gpu_test_state()["running"] and time.time() - t0 < 900:
        time.sleep(1)
    gt = cvt.gpu_test_saved()
    print(f"INFO card test: {gt} ({time.time() - t0:.0f} s)", flush=True)
    check("convert_card_test_said_and_remembered", bool(gt.get("tested_at")) and gt.get("cpu_s", 0) > 0
          and (gt.get("use") is True or (gt.get("use") is False and bool(gt.get("error") or gt.get("psnr") is not None)))
          and (cvt.gpu_ok() is False if gt.get("use") is False else True) and not (work / "gpu_test").exists(), gt)
    _uc2(lambda c: c.setdefault("convert", {}).pop("gpu_test", None))
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

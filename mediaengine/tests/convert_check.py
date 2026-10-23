"""Full-video Convert (existing Archivist feature, contract §9): whole video, original order and frame rate, H.264.

  python tests/convert_check.py <fixtures_dir> <work_dir>

Converts with the app's own converter.convert_file: a 1440p 60 fps clip -> High Quality 1080p, the rotated phone clip and
the VFR clip from <fixtures_dir>/phone. Checks: output size cap, frame rate kept, duration and frame count match the source
(no cut, no drop), full decode clean, upright portrait stays upright, audio kept, source bytes unchanged, no .part left.
"""
from __future__ import annotations

import hashlib, json, os, subprocess, sys, time
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

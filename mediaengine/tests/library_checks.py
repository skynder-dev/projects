"""Library (Media Brain / Composer): re-analysing a video must not destroy the user's work.

  python tests/library_checks.py <fixtures_dir> <work_dir>

A video is analysed into virtual clips; one clip is put into a composition, another gets a hand-made crop.
Re-analysing the same video keeps both (before: the clips were deleted and the deletion cascaded into the
composition and the crops), and does not duplicate the kept moments.
"""
from __future__ import annotations

import os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.config import ensure_dirs
    from archivist.db import db, init_db, now_iso
    from archivist import media_brain as mb, composer
    ensure_dirs(); init_db(); mb.ensure_schema(); composer.ensure_schema()
    import subprocess
    sys.path.insert(0, str(HERE))
    from media_measure import ffmpeg_exe
    video = work / "three scenes.mp4"      # hard scene changes -> several virtual clips
    parts = [fx / "seven" / f"clip_{n}.mp4" for n in (1, 3, 5)]
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", *sum((["-i", str(x)] for x in parts), []), "-filter_complex",
                    "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)], check=True)
    with db() as con:
        ts = now_iso()
        con.execute("INSERT INTO inventory(id,source_key,source_kind,source_label,path,filename,ext,media_type,discovered_at,last_seen_at) "
                    "VALUES(1,'fixed:clip_1','fixed','test',?,?,?,?,?,?)", (str(video), video.name, ".mp4", "video", ts, ts))
        con.commit()
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    mb.analyze_video_into_clips(1, video)
    clips = mb.clips_for_inventory(1)
    check("analysis_makes_clips", len(clips) >= 2, len(clips))
    if len(clips) < 2:
        return 1
    used, cropped = clips[0], clips[1]
    cid = composer.create_composition([used["id"]], next(iter(composer.ASPECTS)), "my edit")
    mb.save_crop_trajectory(cropped["id"], next(iter(mb.ASPECTS)), [{"time_ms": 0, "x": 0.1, "y": 0.0, "w": 0.32, "h": 1.0, "locked": True}], source="manual")
    mb.analyze_video_into_clips(1, video)
    after = mb.clips_for_inventory(1)
    ids = {c["id"] for c in after}
    spans = [(c["start_ms"], c["end_ms"]) for c in after]
    detail = composer.composition_detail(cid)
    check("composition_keeps_its_clip", used["id"] in ids and detail and len(detail.get("items", [])) == 1, detail and detail.get("items"))
    check("hand_made_crop_kept", cropped["id"] in ids and mb.trajectories_for_clip(cropped["id"]))
    check("no_duplicate_moments", len(spans) == len(set(spans)), spans)

    # Composer: a new render replaces the earlier MP4 (no pile in Exports); the order is kept while a render runs; a
    # video made Private during a render - the new MP4 is not kept
    two = composer.create_composition([after[0]["id"], after[1]["id"]], "9:16", "two moments")
    r1 = composer.render_composition(two)
    r2 = composer.render_composition(two)
    check("composer_second_render_replaces_the_first", Path(r2["output"]).is_file() and not Path(r1["output"]).exists()
          and r1["output"] != r2["output"], (r1["output"], r2["output"]))
    with db() as con:
        con.execute("UPDATE compositions SET status='rendering' WHERE id=?", (two,)); con.commit()
    composer._ACTIVE.add(int(two))          # (as start_render marks a render running in this process)
    try:
        composer.move_item(two, 1, "down"); moved = "moved"
    except ValueError as exc:
        moved = str(exc)
    finally:
        composer._ACTIVE.discard(int(two))
    order_now = [x["id"] for x in composer.composition_detail(two)["items"]]
    with db() as con:
        con.execute("UPDATE compositions SET status='finished' WHERE id=?", (two,)); con.commit()
    check("composer_order_kept_while_rendering", "Wait until" in moved and order_now == [after[0]["id"], after[1]["id"]], (moved, order_now))
    with db() as con:
        was_status = con.execute("SELECT analysis_status FROM inventory WHERE id=1").fetchone()[0]
    real_concat = composer._concat_segments

    def concat_then_private(parts_, out_):
        real_concat(parts_, out_)
        with db() as con:
            con.execute("UPDATE inventory SET analysis_status='private' WHERE id=1"); con.commit()
    composer._concat_segments = concat_then_private
    try:
        try:
            composer.render_composition(two); late = "kept"
        except ValueError as exc:
            late = str(exc)
    finally:
        composer._concat_segments = real_concat
        with db() as con:
            st_ = con.execute("SELECT status,output_path FROM compositions WHERE id=?", (two,)).fetchone()
            con.execute("UPDATE inventory SET analysis_status=? WHERE id=1", (was_status,)); con.commit()
    left = sorted(x.name for x in composer.EXPORTS.glob(f"composition_{two}_*.mp4"))
    check("composer_private_during_render_not_kept", "made Private" in late and st_["status"] == "failed"
          and left == [Path(r2["output"]).name], (late, dict(st_), left))
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

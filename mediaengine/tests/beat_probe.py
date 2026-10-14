"""Diagnostics for cuts on the beat on a real Windows runner (workflow mediaengine-probe): builds the beat reel of
tests/dress_check.py and writes, for every segment of the final encode, its frame count and first / last frame times,
the final filter graph, and the reel's frame times and frame-to-frame change around every cut.

  python tests/beat_probe.py <fixtures_dir> <work_dir> <out_json>
"""
from __future__ import annotations

import argparse, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(R3))
from media_measure import ffmpeg_exe  # noqa: E402
from dress_check import drum_song, cut_times, picture_cuts  # noqa: E402


def frames_info(ff, path, limit=None):
    cp = subprocess.run([ff, "-hide_banner", "-i", str(path), "-map", "0:v:0", "-vf", "showinfo", "-f", "null", "-"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    pts = [float(m.group(1)) for m in re.finditer(r"pts_time:\s*([-\d.]+)", cp.stderr)]
    head = [l for l in cp.stderr.splitlines() if "Stream #0:0" in l or "Duration" in l][:3]
    return {"frames": len(pts), "first": pts[:3], "last": pts[-3:], "stream": head}


def main():
    fx, work, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    ff = ffmpeg_exe()
    os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "models"))
    spec = importlib.util.spec_from_file_location("r3_probe", R3 / "p11_folder_to_reel_r3.py")
    r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
    seen = {}
    real = r3.render_dissolve_block

    def spy(v52, segs, durs, trans, outp, dress=None, frames=None):
        seen.update(segs=[str(s) for s in segs], durs=[float(d) for d in durs], trans=[float(t["duration_s"]) for t in trans],
                    frames={str(k): int(v) for k, v in (frames or {}).items()})
        real_run = r3.run_ffmpeg_watched

        def run(args, *a, **k):
            if "-filter_complex" in args:
                seen["graph"] = args[args.index("-filter_complex") + 1]
            return real_run(args, *a, **k)
        r3.run_ffmpeg_watched = run
        try:
            return real(v52, segs, durs, trans, outp, dress, frames)
        finally:
            r3.run_ffmpeg_watched = real_run
    r3.render_dissolve_block = spy
    folder = work / "seven"
    shutil.copytree(fx / "seven", folder)
    song = work / "music" / "drums 118.m4a"; song.parent.mkdir()
    truth = drum_song(song, ff, 118.0, 0.27, 40.0)
    d = work / "d.json"; d.write_text(json.dumps({"music": str(song), "music_mode": "music"}), encoding="utf-8")
    a = argparse.Namespace(input_dir=str(folder), input_list="", output_dir=str(work / "out"), work_dir=str(work / "w"), runtime_dir=str(R3),
                           target_seconds=20.0, audio="auto", semantic="off", semantic_model="fast_local", theme="", profile="9x16",
                           resolution="standard", progress_file="", exclude_events="", edits="", skip_sha_file="", dress=str(d))
    r3.run(a)
    res = json.loads((work / "out" / "MediaEngine Result.json").read_text(encoding="utf-8"))
    reel = work / "out" / "MediaEngine Reel.mp4"
    cuts = cut_times(res)
    report = {"ffmpeg": subprocess.run([ff, "-version"], capture_output=True, text=True).stdout.splitlines()[0],
              "beat_sync": res.get("beat_sync"), "cuts": cuts, "truth_near": [min(truth, key=lambda t: abs(t - c)) for c in cuts],
              "picture_cuts": picture_cuts(ff, reel, cuts[:-1]), "render": seen,
              "segments": [frames_info(ff, s) for s in seen.get("segs", [])], "reel": frames_info(ff, reel)}
    w, h = 64, 112
    raw = subprocess.run([ff, "-v", "error", "-i", str(reel), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    dd = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    report["change_around_cuts"] = {f"{c:.3f}": [[round((k + 1) / 30, 3), round(float(dd[k]), 1)] for k in range(max(0, int(c * 30) - 6), min(len(dd), int(c * 30) + 6))]
                                    for c in cuts[:-1]}
    report["decoded_frames"] = int(fr.shape[0])
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

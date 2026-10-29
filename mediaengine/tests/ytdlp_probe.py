"""Does yt-dlp (the free downloader a "Download by a link" button would use) work from here, with the arguments the
program would give it? (a research probe, not part of the program)

  python tests/ytdlp_probe.py --exe <yt-dlp> --ffmpeg <ffmpeg> --out <dir>

For a few public test videos (yt-dlp's own test videos on YouTube and Vimeo, a public-domain film on archive.org) and
a channel's list of videos: the time, whether it worked, the file's size, length and picture (or yt-dlp's own words
when it did not). Only these figures are kept - never the videos themselves (the results go to a public branch).
Writes ytdlp_probe.json and ytdlp_probe.txt.
"""
from __future__ import annotations

import argparse, json, shutil, subprocess, sys, time
from pathlib import Path

VIDEOS = [
    ("youtube_test", "https://www.youtube.com/watch?v=BaW_jenozKc"),      # yt-dlp's own test video (10 s)
    ("vimeo_test", "https://vimeo.com/56015672"),                          # yt-dlp's own test video on Vimeo
    ("archive_org", "https://archive.org/details/Popeye_forPresident"),    # public domain (a cartoon, ~6 min)
]
LISTS = [
    ("youtube_channel", "https://www.youtube.com/@NASA/videos"),
    ("vimeo_channel", "https://vimeo.com/channels/staffpicks"),
]
FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b"


def run(cmd: list, timeout: float) -> tuple[int, str, str, float]:
    t0 = time.time()
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return cp.returncode, cp.stdout, cp.stderr, round(time.time() - t0, 1)
    except subprocess.TimeoutExpired as exc:
        return -9, str(exc.stdout or ""), "timed out", round(time.time() - t0, 1)


def probe_file(ffmpeg: str, p: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        rc, out, _e, _s = run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,codec_name",
                               "-of", "json", str(p)], 60)
        try:
            return json.loads(out)
        except ValueError:
            return {}
    rc, _o, err, _s = run([ffmpeg, "-hide_banner", "-i", str(p)], 60)        # (its info on stderr)
    return {"ffmpeg_info": [ln.strip() for ln in err.splitlines() if "Duration" in ln or "Stream #" in ln][:6]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True); ap.add_argument("--ffmpeg", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = out.parent / "ytdlp_downloads"                  # (outside the published folder: the videos are not kept)
    work.mkdir(parents=True, exist_ok=True)
    rep: dict = {"version": "", "videos": [], "lists": []}
    rc, so, se, s = run([a.exe, "--version"], 120)
    rep["version"] = so.strip() or se.strip()[-300:]
    lines = [f"yt-dlp {rep['version']} (rc {rc}, {s} s)"]
    for name, url in VIDEOS:
        dst = work / name
        dst.mkdir(exist_ok=True)
        cmd = [a.exe, "--no-playlist", "--no-config", "--ignore-config", "-f", FORMAT, "--merge-output-format", "mp4",
               "--ffmpeg-location", a.ffmpeg, "--no-part", "--restrict-filenames", "--max-filesize", "400M",
               "-o", str(dst / "%(id)s.%(ext)s"), "--print", "after_move:filepath", "--newline", url]
        rc, so, se, s = run(cmd, 900)
        files = [Path(x.strip()) for x in so.splitlines() if x.strip() and Path(x.strip()).is_file()]
        row = {"name": name, "url": url, "rc": rc, "seconds": s, "ok": rc == 0 and bool(files),
               "error": "" if rc == 0 else "\n".join(se.strip().splitlines()[-4:])[-800:]}
        if files:
            row.update(size=files[0].stat().st_size, ext=files[0].suffix, info=probe_file(a.ffmpeg, files[0]))
        rep["videos"].append(row)
        lines.append(f"{'PASS' if row['ok'] else 'FAIL'} {name}: rc {rc}, {s} s, {row.get('size')} bytes {row.get('error', '')[:300]}")
    for name, url in LISTS:
        cmd = [a.exe, "--no-config", "--flat-playlist", "--playlist-end", "15", "-J", url]
        rc, so, se, s = run(cmd, 300)
        try:
            d = json.loads(so)
        except ValueError:
            d = {}
        ents = d.get("entries") or []
        keys = sorted({k for e in ents for k, v in e.items() if v not in (None, "", [])})
        row = {"name": name, "url": url, "rc": rc, "seconds": s, "count": len(ents), "fields": keys,
               "sample": [{k: e.get(k) for k in ("id", "title", "duration", "view_count", "upload_date", "url")} for e in ents[:3]],
               "error": "" if rc == 0 else "\n".join(se.strip().splitlines()[-4:])[-800:]}
        rep["lists"].append(row)
        lines.append(f"{'PASS' if rc == 0 and ents else 'FAIL'} {name}: {len(ents)} entries, {s} s, fields {keys} {row['error'][:300]}")
    (out / "ytdlp_probe.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), "utf-8")
    (out / "ytdlp_probe.txt").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

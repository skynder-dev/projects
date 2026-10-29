"""A stand-in for yt-dlp in the checks of "Download by a link" (download_check.py): the same command line, the same
kind of answers, no network.

  --version                      -> a version
  --flat-playlist -J <url>       -> a profile's list (a url with /@, /channel/, playlist: FAKE_YTDLP_COUNT videos) or one
                                    video; a url with "bot" -> the site asks to sign in
  -o <template> --print ... <url> -> the video FAKE_YTDLP_VIDEO copied as the template says, with progress lines
                                    (FAKE_YTDLP_SLOW=1: slowly); a url with "private" -> a private video's error
"""
from __future__ import annotations

import json, os, re, shutil, sys, time
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if "--version" in args:
        print("2026.10.26")
        return 0
    url = args[-1] if args else ""
    if "bot" in url:
        print("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies", file=sys.stderr)
        return 1
    if "--flat-playlist" in args and "-J" in args:
        if re.search(r"/@|/channel/|playlist", url):
            n = int(os.environ.get("FAKE_YTDLP_COUNT") or 35)
            ents = [{"_type": "url", "ie_key": "Youtube", "id": f"vid{k:03d}", "title": f"Episode {k} - how a city pays twice",
                     "url": f"https://www.youtube.com/watch?v=vid{k:03d}", "duration": 60 + 7 * k, "view_count": (k * 7919) % 100000 + 100}
                    for k in range(n)]
            print(json.dumps({"_type": "playlist", "id": "UCfake", "title": "Fake Cartoons - Videos", "uploader": "Fake Cartoons",
                              "entries": ents}))
        else:
            print(json.dumps({"_type": "video", "id": "one001", "title": "One cartoon about roads", "uploader": "Fake Cartoons",
                              "duration": 75, "view_count": 12345, "upload_date": "20261020", "webpage_url": url}))
        return 0
    if "private" in url:
        print("[youtube] Extracting URL: " + url)
        print("ERROR: [youtube] priv01: Private video. Sign in if you've been granted access to this video")
        return 1
    tpl = args[args.index("-o") + 1]
    vid = (re.search(r"v=([\w-]+)", url) or re.search(r"([\w-]+)$", url)).group(1)[:20]
    path = (tpl.replace("%(uploader).40s", "Fake Cartoons").replace("%(title).70s", os.environ.get("FAKE_YTDLP_TITLE") or f"Video {vid}")
            .replace("%(id)s", vid).replace("%(ext)s", "mp4"))
    slow = os.environ.get("FAKE_YTDLP_SLOW") == "1"
    for pct in (0.0, 12.5, 37.5, 62.5, 87.5, 100.0):
        print(f"[download] {pct:5.1f}% of 1.00MiB at 1.00MiB/s ETA 00:01", flush=True)
        time.sleep(0.6 if slow else 0.02)
    shutil.copy2(os.environ["FAKE_YTDLP_VIDEO"], path)
    pr = args[args.index("--print") + 1] if "--print" in args else ""
    if pr.startswith("after_move:"):
        print(pr[len("after_move:"):].replace("%(filepath)s", str(Path(path))), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

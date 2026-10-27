"""What OpenCV's face finders see in the synthetic shots of clips_check.py (Windows; the sandbox's OpenCV has none).

  python tests/clips_probe.py <work_dir>                  -> JSON on stdout
  python tests/clips_probe.py <work_dir> --real <out_dir> -> real footage: sheets, JSON, ATTRIBUTION.md in out_dir

For each shot (A one face, B two apart, C three, D a streamer's small camera over a "game") and analysis width
(640 / 960): the faces the program's finder finds (YuNet), the people they make (clips._people), and the plan
clips.plan_shots makes of each clip of clips_check. Not a check: it tells how to tune the framing (mediaengine-clips-probe.yml).

--real: the same framing on REAL people talking - public-domain videos only (NASA and other US government works on
Wikimedia Commons: interviews, a crew talking with reporters), found by a Commons search. For three moments of each
video: the plan of a 20 s vertical clip, a sheet with the original pictures (the faces found boxed) next to the
vertical clip's pictures at the same times, the plan as JSON. ATTRIBUTION.md lists every video with its page.
"""
from __future__ import annotations

import json, os, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


UA = {"User-Agent": "MediaEngine-CI/1.0 (https://github.com/skynder-dev/projects; automated test, small number of requests)"}
API = "https://commons.wikimedia.org/w/api.php"
SEARCHES = ['filetype:video "Astronauts Discuss Life In Space"', 'filetype:video "Crew Members Discuss"',
            'filetype:video "Discusses Life In Space"', "filetype:video NASA interview", "filetype:video podcast NASA"]
KIDS = __import__("re").compile(r"(?i)student|school|kid|child|youth|scout|camp|teen|girl|boy")   # (no children's faces)
PER_SEARCH = 2                                            # (two or three people side by side first: the split layouts)


def _api(params: dict) -> dict:
    import time, urllib.parse, urllib.request
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if k == 2:
                raise
            time.sleep(5)


def _plain(s) -> str:
    import html, re
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def _public_domain(lic: str) -> bool:
    n = lic.lower().strip()
    return n.startswith("public domain") or n.startswith("pd") or n.startswith("cc0")


def discover(limit: int = 5) -> list[dict]:
    """Public-domain videos of people talking (60 s - 25 min), a 720p (or 480p) copy each."""
    import time
    picked, seen = [], set()
    for q in SEARCHES:
        n_q = 0
        res = _api({"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 20,
                    "prop": "imageinfo|videoinfo", "iiprop": "url|size|mime|extmetadata|sha1", "viprop": "derivatives|size"})
        for pg in sorted(res.get("query", {}).get("pages", []), key=lambda x: x.get("index", 0)):
            title = pg.get("title", "")
            if title in seen or not pg.get("imageinfo") or KIDS.search(title):
                continue
            ii, vi = pg["imageinfo"][0], (pg.get("videoinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = _plain((meta.get("LicenseShortName") or {}).get("value", ""))
            dur = float(vi.get("duration") or ii.get("duration") or 0)
            if not _public_domain(lic) or not (60 <= dur <= 1500):
                continue
            ders = vi.get("derivatives") or []
            pick = None
            for key in ("720p.vp9.webm", "720p.webm", "480p.vp9.webm", "480p.webm"):
                pick = next((d for d in ders if str(d.get("transcodekey", "")).endswith(key)), None)
                if pick:
                    break
            if not pick:
                continue
            seen.add(title)
            picked.append({"title": title, "search": q, "duration_s": dur, "url": pick["src"], "page": ii.get("descriptionurl"),
                           "licence": lic, "author": _plain((meta.get("Artist") or {}).get("value", ""))[:200],
                           "credit": _plain((meta.get("Credit") or {}).get("value", ""))[:200], "original_sha1": ii.get("sha1")})
            n_q += 1
            if len(picked) >= limit:
                return picked
            if n_q >= PER_SEARCH:
                break
        time.sleep(1)
    return picked


def real(work: Path, out: Path) -> int:
    import hashlib, shutil, time, urllib.request
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    from archivist import clips as cl
    from media_measure import ffmpeg_exe
    ff = ffmpeg_exe()
    out.mkdir(parents=True, exist_ok=True)
    vids = work / "real"
    vids.mkdir(parents=True, exist_ok=True)
    items = discover()
    finder = cl.face_finder()
    report: dict = {"opencv": cv2.__version__, "finder": getattr(finder, "kind", None), "videos": []}
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    att = ["# Real footage used by the clips probe", "", "Public-domain videos from Wikimedia Commons (not the owner's videos).", ""]
    for n, it in enumerate(items, 1):
        dst = vids / f"real_{n}.webm"
        try:
            with urllib.request.urlopen(urllib.request.Request(it["url"], headers=UA), timeout=600) as r, dst.open("wb") as fh:
                shutil.copyfileobj(r, fh, 1 << 20)
        except Exception as exc:
            report["videos"].append({**it, "error": f"not downloaded: {exc}"})
            continue
        it = {**it, "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(), "bytes": dst.stat().st_size}
        att.append(f"- real_{n}: [{it['title']}]({it['page']}) - {it['licence']}; {it['author'] or it['credit']}")
        info = cl._video_info(dst)
        moments = []
        for share in (0.15, 0.45, 0.75):
            s = round(max(0.0, info["duration"] * share), 1)
            dur = min(20.0, max(4.0, info["duration"] - s - 0.5))
            t0 = time.time()
            plan = cl.plan_shots(dst, s, dur, info, 1080 / 1920, "face", split_ok=True)
            took = round(time.time() - t0, 1)
            graph, ow, oh = cl._graph(plan, info, (540, 960))
            clip = vids / f"real_{n}_{int(s)}.mp4"
            subprocess.run([ff, "-v", "error", "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", str(dst), "-filter_complex", graph,
                            "-map", "[pv]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", str(clip)], check=True)
            row = []
            for t in (dur * 0.1, dur * 0.5, dur * 0.9):
                src_png, v_png = vids / "s.png", vids / "v.png"
                subprocess.run([ff, "-v", "error", "-y", "-ss", f"{s + t:.3f}", "-i", str(dst), "-frames:v", "1", str(src_png)], check=True)
                subprocess.run([ff, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(clip), "-frames:v", "1", str(v_png)], check=True)
                im = Image.open(src_png).convert("RGB")
                fwid = int(getattr(finder, "width", 960) or 960)
                bgr = cv2.cvtColor(np.asarray(im.resize((fwid, int(round(im.height * fwid / im.width / 2)) * 2))), cv2.COLOR_RGB2BGR)
                found = finder.find(bgr) if finder else []
                shown = im.resize((480, int(round(im.height * 480 / im.width))))
                dr = ImageDraw.Draw(shown)
                for (x, y, w, h) in found:
                    q = 480 / fwid
                    dr.rectangle([x * q, y * q, (x + w) * q, (y + h) * q], outline=(255, 220, 0), width=2)
                row.append((shown, Image.open(v_png).convert("RGB").resize((152, 270)),
                            [[int(v) for v in r] for r in found]))
            moments.append({"start": s, "seconds": dur, "analysis_s": took, "shots": plan["shots"], "row": row})
        # the sheet: per moment one row (original with the faces found | the vertical clip), three times
        rh = 270
        sheet = Image.new("RGB", (3 * (480 + 152 + 12), len(moments) * (rh + 30) + 10), (18, 20, 26))
        d = ImageDraw.Draw(sheet)
        for r_, m in enumerate(moments):
            y = r_ * (rh + 30) + 26
            lay = ", ".join(f"{sh['layout']}@{sh['s']:.1f}" for sh in m["shots"])[:150]
            d.text((6, y - 22), f"real_{n} from {m['start']:.0f} s ({m['analysis_s']} s to analyse): {lay}", fill=(230, 230, 230), font=font)
            for c, (shown, vert, _) in enumerate(m["row"]):
                x = c * (480 + 152 + 12)
                sheet.paste(shown, (x, y + (rh - shown.height) // 2))
                sheet.paste(vert, (x + 480, y))
        sheet.save(out / f"real_{n}.png")
        for m in moments:
            m["faces_found"] = [r[2] for r in m.pop("row")]
        report["videos"].append({**it, "info": info, "moments": moments})
        dst.unlink()
    (out / "ATTRIBUTION.md").write_text("\n".join(att) + "\n", "utf-8")
    (out / "real_probe.json").write_text(json.dumps(report, indent=1), "utf-8")
    return 0


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    if "--real" in sys.argv:
        return real(work, Path(sys.argv[sys.argv.index("--real") + 1]).resolve())
    import cv2
    from PIL import Image
    from archivist import clips as cl
    from media_measure import ffmpeg_exe
    out: dict = {"opencv": cv2.__version__}
    face = Image.open(HERE / "assets" / "face_pd.jpg").convert("RGB")
    big, small = face.resize((520, 600)), face.resize((240, 276))

    def shot(bg, places, img):
        im = Image.new("RGB", (1920, 1080), bg)
        for x, y in places:
            im.paste(img, (x, y))
        return im
    shots = {"A": shot((0x40, 0x50, 0x60), [(1252, 240)], big), "B": shot((0xa0, 0x80, 0x60), [(60, 240), (1300, 240)], big),
             "C": shot((0x30, 0x50, 0x30), [(32, 240), (700, 240), (1368, 240)], big),
             "D": shot((0x20, 0x28, 0x30), [(40, 40)], small)}
    finder = cl.face_finder()
    out["finder"] = getattr(finder, "kind", None)
    for name, im in shots.items():
        rgb = np.asarray(im)
        for fw in (640, 960):
            fh = int(round(fw * 1080 / 1920 / 2)) * 2
            f = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (fw, fh), interpolation=cv2.INTER_AREA)
            both = finder.find(f) if finder else []
            people = cl._people([(float(x + w / 2) / fw, float(w) / fw, float(y + h / 2) / fh) for (x, y, w, h) in both], fw, fh)
            out[f"{name}_{fw}"] = {"finder": [list(map(int, r)) for r in both], "people": [[round(v, 4) for v in p] for p in people]}
    # the plans of the clips of clips_check (the same synthetic video)
    ff = ffmpeg_exe()
    src = work / "probe.mp4"
    face_p = HERE / "assets" / "face_pd.jpg"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x405060:s=1920x1080:r=30:d=20",
                    "-f", "lavfi", "-i", "color=c=0xa08060:s=1920x1080:r=30:d=20",
                    "-f", "lavfi", "-i", "color=c=0x305030:s=1920x1080:r=30:d=20", "-loop", "1", "-i", str(face_p),
                    "-f", "lavfi", "-i", "color=c=0x202830:s=1920x1080:r=30:d=20",
                    "-filter_complex", "[3:v]scale=520:600,split=6[f1][f2][f3][f4][f5][f6];[0:v][f1]overlay=1252:240:shortest=1[a];"
                                       "[1:v][f2]overlay=60:240:shortest=1[b0];[b0][f3]overlay=1300:240:shortest=1[b];"
                                       "[2:v][f4]overlay=32:240:shortest=1[c0];[c0][f5]overlay=700:240:shortest=1[c1];"
                                       "[c1][f6]overlay=1368:240:shortest=1[c];"
                                       "[4:v]drawbox=x='mod(t*300,1700)':y=700:w=160:h=160:color=white:t=fill[g0];"
                                       "[3:v]scale=240:276[fc];[g0][fc]overlay=40:40:shortest=1[dd];"
                                       "[a][b][c][dd]concat=n=4:v=1:a=0,format=yuv420p[v]",
                    "-map", "[v]", "-t", "80", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(src)], check=True)
    info = {"w": 1920, "h": 1080, "sar": 1.0}
    for s, e in ((1.0, 17.0), (22.0, 38.0), (12.0, 28.0), (42.0, 58.0), (62.0, 78.0)):
        out[f"plan_{s:g}_{e:g}"] = cl.plan_shots(src, s, e - s, info, 1080 / 1920, "face", split_ok=True)["shots"]
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

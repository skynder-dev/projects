"""What OpenCV's face finders see in the synthetic shots of clips_check.py (Windows; the sandbox's OpenCV has none).

  python tests/clips_probe.py <work_dir>   -> JSON on stdout

For each shot (A one face, B two apart, C three, D a streamer's small camera over a "game") and analysis width
(480 / 960): the front and side finds, the people they make (clips._people), and the plan clips.plan_shots makes of
each clip of clips_check. Not a check: it tells how to tune the framing (mediaengine-clips-probe.yml).
"""
from __future__ import annotations

import json, os, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
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
    out["finder"] = finder is not None
    for name, im in shots.items():
        g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
        for fw in (480, 960):
            fh = int(round(fw * 1080 / 1920 / 2)) * 2
            f = cv2.resize(g, (fw, fh), interpolation=cv2.INTER_AREA)
            ms = max(24, fh // (12 if fw == 480 else 24))
            kw = dict(scaleFactor=1.12, minNeighbors=5, minSize=(ms, ms))
            front = [list(map(int, r)) for r in finder.front.detectMultiScale(f, **kw)] if finder else []
            side = [list(map(int, r)) for r in finder.side.detectMultiScale(f, **kw)] if finder and finder.side else []
            mirror = [list(map(int, r)) for r in finder.side.detectMultiScale(np.ascontiguousarray(f[:, ::-1]), **kw)] \
                if finder and finder.side else []
            both = finder.detectMultiScale(f, **kw) if finder else []
            people = cl._people([(float(x + w / 2) / fw, float(w) / fw, float(y + h / 2) / fh) for (x, y, w, h) in both], fw, fh)
            out[f"{name}_{fw}"] = {"front": front, "side": side, "side_mirrored": mirror, "finder": [list(map(int, r)) for r in both],
                                   "people": [[round(v, 4) for v in p] for p in people]}
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

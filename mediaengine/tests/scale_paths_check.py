"""Many files, long names and a deep data folder, through the app routes.

  python tests/scale_paths_check.py <work_dir> [--count 64] [--seconds 15]

Makes <count> short clips with long, partly Cyrillic names (about 90 characters) in a source folder, uses a deep
data folder, and builds a reel (technical mode). Half the names are long English, half long Russian. On Windows run it with long-path support OFF
(the Windows default) to see what a normal PC does. Reports total time and the longest internal path used.
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402

SRCS = ["testsrc2", "mandelbrot", "life=mold=10:ratio=0.3", "cellauto=rule=110", "rgbtestsrc", "smptehdbars", "testsrc"]


def main():
    work = Path(sys.argv[1]).resolve()
    count = int(sys.argv[sys.argv.index("--count") + 1]) if "--count" in sys.argv else 64
    seconds = sys.argv[sys.argv.index("--seconds") + 1] if "--seconds" in sys.argv else "15"
    ff = ffmpeg_exe()
    src = work / "Видео с телефона за лето 2026 года" / "Поездка на море с семьёй и друзьями"
    src.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        name = (f"{i + 1:02d} Summer trip 2026 beach sunset walk along the shore in the evening with kids and dog {i + 1:02d}.mp4"
                if i % 2 == 0 else f"{i + 1:02d} Отпуск 2026 пляж закат прогулка вдоль берега вечером с детьми и собакой {i + 1:02d}.mp4")
        dst = src / name
        if dst.exists():
            continue
        base = SRCS[i % len(SRCS)]
        kind, _, opts = base.partition("=")
        lav = f"{kind}=size=320x180:rate=30" + (":" + opts if opts else "")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", lav, "-f", "lavfi", "-i", f"sine=frequency={200 + 7 * i}:sample_rate=48000",
                        "-t", "3", "-vf", f"hue=h=t*{20 + i},rotate=0.1*sin(t*{1 + i % 5})", "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(dst)], check=True)
    home = work / "MediaEngine Data"      # the default data folder name next to a release
    shutil.rmtree(home, ignore_errors=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist import auto_edit as ae
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    app = create_app()
    t0 = time.time()
    with app.test_client() as c:
        r = c.get("/auto/new", query_string={"folder": str(src)}, headers=H)
        check("scan_many_long_names", r.status_code == 200 and f"{count} usable video(s)".encode() in r.data, r.status_code)
        r = c.post("/auto/create", data={"folder": str(src), "length": seconds, "format": "social_hd", "sound": "auto", "mode": "technical"}, headers=H)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        jid = ae.project(pid)["jobs"][0]["id"]
        while True:
            j = ae.job(jid)
            if j["status"] in ("done", "failed", "cancelled") or time.time() - t0 > 3600:
                break
            time.sleep(1)
        dt = time.time() - t0
        longest = max((len(str(p)) for p in home.rglob("*")), default=0)
        check("build_done", j["status"] == "done", (j.get("status"), j.get("error")))
        if j["status"] == "done":
            rev = ae.revision(j["revision_id"])
            check("reel_uses_several_sources", len({s["source_name"] for s in rev["result"]["segments"]}) >= 3)
            check("no_input_skipped_for_path_length", not [x for x in rev["result"].get("skipped_inputs", []) if "ANALYSIS" in x["reason"]],
                  rev["result"].get("skipped_inputs"))
        else:
            log = home / "data" / "auto_edit" / f"p{pid}" / "jobs" / f"j{jid}.log"
            print(log.read_text(encoding="utf-8", errors="replace")[-2500:] if log.exists() else "no log")
    print(json.dumps({"files": count, "build_s": round(dt, 1), "longest_internal_path": longest,
                      "passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

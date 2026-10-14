"""Cuts on the beat with REAL music (public Wikimedia Commons recordings with free licences) - CI only.

  python tests/real_music_check.py <work_dir> --out <results_dir> [--fixtures <dir with 'seven'>] [--manifest tests/real_music_manifest.json]

Not the owner's music. For every track (a pinned list, or found by a Commons search "filetype:audio" + a style;
CC0 / public domain / CC BY / CC BY-SA, 20-600 s):
1. the first 60 s decoded like the engine does (48 kHz stereo PCM);
2. MediaEngine's beat finder (app/archivist/engine_p11/p13_beats.py) and, as an independent reference, librosa's
   beat tracker (pip, CI only - not a dependency of the program);
3. agreement: the share of MediaEngine's beats within 70 ms of a librosa beat (a found beat is a real beat; finding
   every other beat is fine for cuts) and the share that sits half way between librosa's beats (off-beat lock);
   the tempo agreement (same, half or double);
4. for a few tracks with a clear beat, a 20 s reel of the synthetic fixtures with that music through the real engine:
   where its cuts are against MediaEngine's and librosa's beats.
Results: JSON + ATTRIBUTION.md (results branch). Fails when the beat finder breaks (an error), when tracks with a
clear beat disagree with librosa (median agreement below 0.8, or an off-beat lock on more than one track), or when a
reel's cuts are not in time with its music.
"""
from __future__ import annotations

import argparse, importlib.util, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R3 = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(R3))
from media_measure import ffmpeg_exe  # noqa: E402
from real_footage_check import UA, api, free_licence, strip_html  # noqa: E402

STYLES = ["pop song", "rock song", "electronic dance music", "drum beat", "hip hop instrumental", "funk", "disco",
          "reggae", "jazz", "latin music", "folk song", "country music", "piano solo", "ambient music", "orchestra"]
PER_STYLE = 2
MAX_TRACKS = 24


def discover() -> list[dict]:
    picked, seen = [], set()
    for style in STYLES:
        res = api({"action": "query", "generator": "search", "gsrsearch": f"filetype:audio {style}", "gsrnamespace": 6,
                   "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata|sha1"})
        pages = sorted(res.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
        n = 0
        for p in pages:
            title = p.get("title", "")
            if title in seen or not p.get("imageinfo"):
                continue
            ii = p["imageinfo"][0]
            meta = ii.get("extmetadata") or {}
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            mime = str(ii.get("mime") or "")
            dur = float(ii.get("duration") or 0)
            if not free_licence(lic) or not mime.startswith(("audio/", "application/ogg")) or "midi" in mime:
                continue
            if dur and not (20 <= dur <= 600):
                continue
            if int(ii.get("size") or 0) > 40_000_000:
                continue
            seen.add(title)
            picked.append({"title": title, "style": style, "url": ii.get("url"), "page": ii.get("descriptionurl"), "licence": lic,
                           "licence_url": strip_html((meta.get("LicenseUrl") or {}).get("value", "")),
                           "author": strip_html((meta.get("Artist") or {}).get("value", ""))[:200], "original_sha1": ii.get("sha1")})
            n += 1
            if n >= PER_STYLE or len(picked) >= MAX_TRACKS:
                break
        if len(picked) >= MAX_TRACKS:
            break
        time.sleep(1)
    return picked


def fetch(items: list[dict], folder: Path) -> list[dict]:
    import hashlib
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, it in enumerate(items, 1):
        ext = Path(urllib.parse.urlparse(it["url"]).path).suffix.lower() or ".ogg"
        dst = folder / f"{i:02d}{ext}"
        try:
            if not dst.exists():
                tmp = dst.with_name(dst.name + ".part")
                with urllib.request.urlopen(urllib.request.Request(it["url"], headers=UA), timeout=180) as r, tmp.open("wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
                os.replace(tmp, dst)
            h = hashlib.sha256(dst.read_bytes()).hexdigest()
            if it.get("sha256") and it["sha256"] != h:
                print("SKIP changed file:", it["title"]); dst.unlink(); continue
            out.append({**it, "file": dst.name, "sha256": h, "bytes": dst.stat().st_size})
        except Exception as exc:
            print("SKIP not downloaded:", it["title"], exc)
        time.sleep(0.5)
    return out


_REF = ("import json,sys,numpy as np,librosa\n"
        "y,sr=librosa.load(sys.argv[1],sr=22050,mono=True)\n"
        "t,b=librosa.beat.beat_track(y=y,sr=sr,units='time')\n"
        "print(json.dumps({'bpm':float(np.atleast_1d(t)[0]),'beats':[float(x) for x in b]}))")


def librosa_beats(wav: Path):
    """librosa's beat tracker in its own Python (MEDENG_REF_PYTHON: a separate venv, so its numba / numpy pins never
    touch the program's): (bpm, beat times)."""
    py = os.environ.get("MEDENG_REF_PYTHON") or sys.executable
    cp = subprocess.run([py, "-c", _REF, str(wav)], capture_output=True, text=True, timeout=600)
    if cp.returncode != 0:
        raise RuntimeError("librosa failed: " + cp.stderr[-400:])
    d = json.loads(cp.stdout.strip().splitlines()[-1])
    return float(d["bpm"]), np.asarray(d["beats"], float)


def near(a, b, tol=0.07) -> float:
    """Share of the times a that are within tol of one of b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size == 0 or b.size == 0:
        return 0.0
    return float(np.mean([np.min(np.abs(b - x)) <= tol for x in a]))


def main():
    work = Path(sys.argv[1]).resolve()
    outd = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    fx = Path(sys.argv[sys.argv.index("--fixtures") + 1]).resolve() if "--fixtures" in sys.argv else None
    manifest = Path(sys.argv[sys.argv.index("--manifest") + 1]) if "--manifest" in sys.argv else HERE / "real_music_manifest.json"
    work.mkdir(parents=True, exist_ok=True); outd.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    import p13_beats as beats
    items = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else discover()
    tracks = fetch(items, work / "music")
    (outd / "real_music_manifest.json").write_text(json.dumps([{k: v for k, v in x.items() if k not in ("file", "bytes")} for x in tracks],
                                                              indent=2, ensure_ascii=False), encoding="utf-8")
    rows, errors = [], []
    for t in tracks:
        src = work / "music" / t["file"]
        wav = work / (src.stem + ".wav")
        cp = subprocess.run([ff, "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-vn", "-ac", "2", "-ar", "48000", "-t", "60",
                             "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True)
        if cp.returncode != 0 or not wav.is_file() or wav.stat().st_size < 48000 * 4 * 10:
            print("SKIP undecodable or under 10 s:", t["title"]); continue
        try:
            t0 = time.perf_counter(); me = beats.detect(wav); dt = time.perf_counter() - t0
        except Exception as exc:
            errors.append(f"{t['title']}: {type(exc).__name__}: {exc}"); continue
        try:
            tempo, lb = librosa_beats(wav)
        except Exception as exc:
            errors.append(f"reference {t['title']}: {exc}"); continue
        mids = (lb[:-1] + lb[1:]) / 2 if lb.size > 1 else lb
        mine = np.asarray(me["beats"], float)
        inner = mine[(mine > 2) & (mine < (lb[-1] if lb.size else 0) - 1)] if lb.size else mine
        ratio = (me["bpm"] / tempo) if tempo else 0
        alt = beats.detect(wav, comb=not beats.TEMPO_COMB)            # the other tempo score, for comparison
        am = np.asarray(alt["beats"], float)
        am = am[(am > 2) & (am < (lb[-1] if lb.size else 0) - 1)] if lb.size else am
        rows.append({"title": t["title"], "style": t["style"], "file": t["file"], "seconds_s": round(dt, 2),
                     "mediaengine": {k: me[k] for k in ("bpm", "clear", "confidence", "strength_db", "shifted")},
                     "librosa_bpm": round(tempo, 2),
                     "tempo_relation": min(("same", 1.0), ("half", 0.5), ("double", 2.0), ("2/3", 2 / 3), ("3/2", 1.5),
                                           key=lambda r: abs(np.log(max(1e-6, ratio) / r[1])))[0] if ratio else "none",
                     "on_librosa_beats": round(near(inner, lb), 3), "on_librosa_offbeats": round(near(inner, mids), 3),
                     "beats_compared": int(inner.size),
                     "other_tempo_score": {"comb": not beats.TEMPO_COMB, "bpm": alt["bpm"], "clear": alt["clear"],
                                           "on_librosa_beats": round(near(am, lb), 3), "on_librosa_offbeats": round(near(am, mids), 3)}})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    clear = [r for r in rows if r["mediaengine"]["clear"] and r["beats_compared"] >= 10]
    agree = [r["on_librosa_beats"] for r in clear]
    offbeat = [r for r in clear if r["on_librosa_offbeats"] > 0.6 and r["on_librosa_beats"] < 0.4]
    other = [r["other_tempo_score"]["on_librosa_beats"] for r in rows if r["other_tempo_score"]["clear"] and r["beats_compared"] >= 10]
    summary = {"tracks": len(rows), "clear_beat": len(clear), "median_agreement": round(float(np.median(agree)), 3) if agree else None,
               "mean_agreement": round(float(np.mean(agree)), 3) if agree else None,
               "other_tempo_score": {"comb": not beats.TEMPO_COMB, "clear_beat": len(other),
                                     "mean_agreement": round(float(np.mean(other)), 3) if other else None,
                                     "agreement_over_0_8": sum(1 for a in other if a >= 0.8)},
               "agreement_over_0_8": sum(1 for a in agree if a >= 0.8), "offbeat_locks": [r["title"] for r in offbeat], "errors": errors}

    # a reel with real music through the engine: its cuts against the beats
    reels = []
    if fx and (fx / "seven").is_dir() and clear:
        os.environ.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3), MEDENG_P11_MODEL_ROOT=str(work / "models"))
        spec = importlib.util.spec_from_file_location("r3_music", R3 / "p11_folder_to_reel_r3.py")
        r3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r3)
        for k, r in enumerate(sorted(clear, key=lambda r: -r["on_librosa_beats"])[:3]):
            song = work / "music" / r["file"]
            dfile = work / f"reel{k}.dress.json"
            dfile.write_text(json.dumps({"music": str(song), "music_mode": "music"}), encoding="utf-8")
            a = argparse.Namespace(input_dir=str(fx / "seven"), input_list="", output_dir=str(work / f"reel{k}"), work_dir=str(work / "w"),
                                   runtime_dir=str(R3), target_seconds=20.0, audio="auto", semantic="off", semantic_model="fast_local",
                                   theme="", profile="9x16", resolution="standard", progress_file="", exclude_events="", edits="",
                                   skip_sha_file="", dress=str(dfile))
            try:
                r3.run(a)
                res = json.loads((work / f"reel{k}" / "MediaEngine Result.json").read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"reel {r['title']}: {exc}"); continue
            segs, tr = res["segments"], res["rendered_transition_s"]
            cuts = [float(s["reel_out_s"]) - (float(tr[i]) / 2.0 if i < len(tr) else 0.0) for i, s in enumerate(segs)]
            _, lb = librosa_beats(work / (song.stem + ".wav"))
            reels.append({"title": r["title"], "beat_sync": res.get("beat_sync"), "cuts_s": [round(c, 3) for c in cuts],
                          "cuts_on_librosa_beats": round(near(cuts, lb, 0.05), 3), "warnings": res.get("warnings")})
            print(json.dumps(reels[-1], ensure_ascii=False), flush=True)
    summary["reels"] = reels
    # every reel with a clear beat: its cuts in time with the music (on a beat, or half way between two when a moment
    # could not get longer), all but at most one
    off_time = [r["title"] for r in reels if (r.get("beat_sync") or {}).get("clear") and
                int(r["beat_sync"].get("cuts_on_beat") or 0) + int(r["beat_sync"].get("cuts_half_way_between_beats") or 0) < int(r["beat_sync"]["cuts"]) - 1]
    summary["reels_with_cuts_off_the_beat"] = off_time
    ok = not errors and not off_time and (not clear or (summary["median_agreement"] >= 0.8 and len(offbeat) <= 1))
    summary["pass"] = ok
    (outd / "real_music.json").write_text(json.dumps({"summary": summary, "tracks": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    att = ["# Music used by the real-music check", "", "Public Wikimedia Commons recordings with free licences (not included in MediaEngine).", ""]
    for t in tracks:
        att.append(f"- [{t['title']}]({t.get('page')}) - {t.get('author') or 'unknown author'} - {t.get('licence')}")
    (outd / "ATTRIBUTION.md").write_text("\n".join(att) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

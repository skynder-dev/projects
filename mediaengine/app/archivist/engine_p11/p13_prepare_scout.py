"""'Prepare AI+ for the whole Library': what the AI+ model sees in each video, ahead of time.

  python p13_prepare_scout.py --list FILES.txt --cache DIR --runtime-dir DIR --pe-dir DIR --progress FILE
                              [--stop FILE] [--skip-sha FILE] [--skipped FILE]

--list: one video per line, "id<TAB>sha256<TAB>path" (the Library's id and SHA-256; a bare path also works).
For every video: its SHA-256, and - unless the shared cache already has it - the accepted scout frames (about one
per second, at most 48), their features and the AI+ embedding of every frame, stored exactly like the engine stores
them (p13_event_semantic_pe.write_scout, same key). A later AI+ reel or theme with these videos looks at no frame
again. Progress: a small JSON file; a stop file (or the app ending the process) stops between videos; what is done
stays done. --skip-sha (read again before every video): SHA-256 of videos marked Private - never looked at.
Left to the reel itself (the engine analyses a converted copy of them, under another SHA-256), and listed with the
reason in --skipped ({id: reason}): camcorder streams, pictures with an odd width or height. Also listed there:
videos that cannot be read, and videos whose content changed since the Library analysed them (prepared under their
new SHA-256, which the Library does not know yet).
"""
from __future__ import annotations

import argparse, importlib.util, json, os, re, subprocess, sys, time
from pathlib import Path

LEAVE_TO_REEL = {".mts", ".m2ts", ".ts", ".mpg", ".mpeg", ".vob", ".mod", ".tod", ".m2t"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _write(path: Path | None, obj) -> None:
    """Best effort (Windows: the app or a virus scanner may have the file open for a moment) - never ends the run."""
    if not path:
        return
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    for k in range(6):
        try:
            tmp.write_text(json.dumps(obj), encoding="utf-8")
            os.replace(tmp, path)
            return
        except OSError:
            time.sleep(0.1 * (k + 1))
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass


def _odd_size(ffmpeg: str, path: Path) -> bool:
    """A picture with an odd width or height (a video cropped in a phone's gallery): the engine analyses a copy one
    pixel smaller."""
    try:
        cp = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=60)
        line = next((l for l in (cp.stderr or "").splitlines() if "Video:" in l), "")
        m = re.search(r",\s*(\d{2,5})x(\d{2,5})", line)
        return bool(m) and (int(m.group(1)) % 2 == 1 or int(m.group(2)) % 2 == 1)
    except Exception:
        return False


def _private(skip_sha: Path | None) -> set:
    if not skip_sha:
        return set()
    try:
        return {x.strip().lower() for x in skip_sha.read_text(encoding="utf-8").splitlines() if x.strip()}
    except OSError:
        return set()


def parse_list(lines) -> list[tuple[str, str, Path]]:
    out = []
    for line in lines:
        line = line.strip("\r\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        out.append((parts[0], parts[1].strip().lower(), Path(parts[2])) if len(parts) >= 3 else ("", "", Path(line.strip())))
    return out


def prepare(files, cache: Path, runtime: Path, make_scorer, progress: Path | None = None, stop: Path | None = None,
            ffmpeg="ffmpeg", ffprobe="ffprobe", skip_sha: Path | None = None, skipped_file: Path | None = None) -> dict:
    """The work itself (also used in-process by the checks with a stand-in scorer). files: paths or (id, sha, path)."""
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import p13_event_semantic_pe as hook
    v7 = _load("medeng_event_semantic_v7", runtime / "medeng_event_semantic_v7.py")
    key = hook.scout_key()
    items = [x if isinstance(x, tuple) else ("", "", Path(x)) for x in files]
    done = looked = 0
    skipped: dict = {}
    scorer = None
    started = time.time()
    t_looked = 0.0

    def skip(vid, path, reason):
        skipped[vid or str(path)] = reason
        _write(skipped_file, skipped)
        print("skipped:", path.name, reason, flush=True)

    for i, (vid, want_sha, p) in enumerate(items):
        if stop and stop.exists():
            _write(progress, {"state": "stopped", "done": i, "total": len(items), "looked": looked, "file": ""})
            return {"state": "stopped", "done": i, "looked": looked, "skipped": skipped}
        eta = round(t_looked / looked * (len(items) - i)) if looked else None
        _write(progress, {"state": "running", "done": i, "total": len(items), "looked": looked, "file": p.name, "eta_s": eta})
        if p.suffix.lower() in LEAVE_TO_REEL:
            skip(vid, p, "camcorder_stream"); continue
        private = _private(skip_sha)
        if want_sha and want_sha in private:
            continue                         # marked Private meanwhile: never looked at (and not counted)
        try:
            if not p.is_file():
                raise FileNotFoundError(str(p))
            if _odd_size(ffmpeg, p):
                skip(vid, p, "odd_size"); continue
            sha = hook._sha256(p)
            info, _ = hook.read_scout(cache, sha, key)
        except OSError as exc:               # unplugged drive, locked file: the next run tries again
            skip(vid, p, "unreadable:" + type(exc).__name__); continue
        if sha in private:
            continue
        if info is None:
            if scorer is None:                # the model cannot start: the run ends with that error (not 'skipped' x N)
                scorer = make_scorer()
                getattr(scorer, "vision")
            t0 = time.time()
            try:
                info, emb = hook.scout(v7, scorer, p, ffmpeg, ffprobe)
            except MemoryError:
                raise
            except Exception as exc:          # one video the analysis cannot read does not stop the rest
                skip(vid, p, "analysis_failed:" + type(exc).__name__); continue
            for k in range(4):
                try:
                    hook.write_scout(cache, sha, key, info, emb)
                    break
                except OSError:
                    if k == 3:
                        info = None
                    time.sleep(0.2 * (k + 1))
            if info is None:
                skip(vid, p, "cache_not_writable"); continue
            t_looked += time.time() - t0
            looked += 1
        if want_sha and sha != want_sha:
            skip(vid, p, "changed_since_analysis")    # prepared, but under a SHA-256 the Library does not know yet
            continue
        done += 1
    _write(progress, {"state": "done", "done": len(items), "total": len(items), "looked": looked, "skipped": len(skipped), "file": "",
                      "seconds": round(time.time() - started, 1)})
    return {"state": "done", "done": done, "looked": looked, "skipped": skipped}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--runtime-dir", required=True); ap.add_argument("--pe-dir", required=True)
    ap.add_argument("--progress", default=""); ap.add_argument("--stop", default="")
    ap.add_argument("--skip-sha", default=""); ap.add_argument("--skipped", default="")
    a = ap.parse_args()
    runtime = Path(a.runtime_dir).resolve()
    sys.path.insert(0, str(runtime))
    files = parse_list(Path(a.list).read_text(encoding="utf-8-sig").splitlines())
    progress = Path(a.progress) if a.progress else None

    def make_scorer():
        import p13_pe_core_contract as pc, p13_pe_core_adapter as pa
        pc.validate(Path(a.pe_dir), True)                  # the exact model files, every SHA-256
        return pa.PECoreScorer(Path(a.pe_dir), full_check=False, threads=os.cpu_count() or None)
    try:
        r = prepare(files, Path(a.cache), runtime, make_scorer, progress, Path(a.stop) if a.stop else None,
                    os.environ.get("MEDENG_FFMPEG", "ffmpeg"), os.environ.get("MEDENG_FFPROBE", "ffprobe"),
                    Path(a.skip_sha) if a.skip_sha else None, Path(a.skipped) if a.skipped else None)
    except Exception as exc:
        _write(progress, {"state": "failed", "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
        raise
    print(json.dumps({k: v for k, v in r.items() if k != "skipped"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

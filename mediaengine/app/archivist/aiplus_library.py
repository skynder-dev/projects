"""Library search by theme with the AI+ model (PE-Core L/14), on this PC.

Each video in the Library is indexed once: the AI+ model looks at its preview frames (the same 8 storyboard frames
the Library shows) and keeps one embedding per frame. A search for a theme ("sea", "children", ...) then compares
those embeddings with the theme's descriptions - plain arithmetic, no model run, instant. Private, rejected and
excluded videos are never indexed or shown (rows of a video that becomes one of them are removed). Nothing leaves
the PC.

"Prepare AI+ for the whole Library" does this and then a second, longer step (in the engine, below normal priority):
what the AI+ model sees in each video for a reel (about one frame per second, at most 48) is stored in the shared
cache every AI+ build uses - a later AI+ reel or theme with these videos looks at no frame again. Both steps wait
while a reel is being built (one AI+ model at a time) and continue afterwards; what is done stays done.
"""
from __future__ import annotations

import atexit, hashlib, json, os, subprocess, sys, threading, time
from pathlib import Path

import numpy as np

from .db import db, now_iso

_STATE = {"state": "idle", "done": 0, "total": 0, "error": "", "file": "", "waiting": False, "t0": 0.0, "n0": 0,
          "phase": "", "deep_eta": None}
_LOCK = threading.Lock()
_STOP = threading.Event()
_KEY: dict = {}
_PROC: dict = {}            # the running engine step of "for reels" (stopped with the app)
_SCOUT_MEMO: dict = {}      # sha -> ((mtime, size), key) of the shared cache's files: status() reads each file once

VERSION = "AIPLUS_LIBRARY_V2"
LOAD_FAILED = "The AI+ model could not be started (not enough memory?). Close other programs and try again."
FILES_BAD = "The AI+ model files are missing or changed. Download the AI+ model again on 'Check this PC'."
INTERRUPTED = "The AI+ preparation ended unexpectedly. Press the button again: it continues where it stopped."
# what the reel itself prepares (the engine looks at them as a converted copy): camcorder streams
LEFT_TO_REEL = {".mts", ".m2ts", ".ts", ".mpg", ".mpeg", ".vob", ".mod", ".tod", ".m2t"}


def ensure_schema() -> None:
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS aiplus_frames(
            inventory_id INTEGER PRIMARY KEY REFERENCES inventory(id) ON DELETE CASCADE, model_key TEXT NOT NULL,
            times TEXT NOT NULL, emb BLOB NOT NULL, source_fingerprint TEXT, indexed_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS aiplus_texts(
            model_key TEXT NOT NULL, theme TEXT NOT NULL, pos BLOB NOT NULL, neg BLOB NOT NULL, PRIMARY KEY(model_key, theme))""")
        con.commit()


def _ae():
    from . import auto_edit as ae
    return ae


def _engine_path() -> None:
    import sys
    ae = _ae()
    if str(ae.ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ae.ENGINE_DIR))


def _hook():
    _engine_path()
    import p13_event_semantic_pe as hook
    return hook


def frames_key() -> str:
    """The exact model files + the code that turns a picture into numbers: another model or another adapter means
    the stored frames are not comparable any more (they are looked at again)."""
    ident = _ae().aiplus_identity()
    if _KEY.get("ident") != ident:
        _engine_path()
        import p13_pe_core_adapter as pa, p13_pe_core_contract as pc
        h = hashlib.sha256()
        for part in (VERSION, ident, Path(pa.__file__).read_bytes(), Path(pc.__file__).read_bytes()):
            h.update(part if isinstance(part, bytes) else str(part).encode())
        _KEY.update(ident=ident, key=h.hexdigest()[:32])
    return _KEY["key"]


def text_key(theme: str) -> str:
    """frames_key + the theme's exact descriptions (good and bad): changed descriptions are encoded again."""
    return frames_key() + "|" + _hook().prompt_key(theme)


# exactly the Library page's set (web.gallery): the working set, available on this PC, not Private / rejected / excluded
_VISIBLE = ("media_type='video' AND work_selected=1 AND excluded=0 AND COALESCE(analysis_status,'')<>'private' "
            "AND private_path IS NULL AND rejected_path IS NULL "
            "AND (source_kind='fixed' OR staging_path IS NOT NULL OR archive_path IS NOT NULL)")
_VISIBLE_I = ("i.media_type='video' AND i.work_selected=1 AND i.excluded=0 AND COALESCE(i.analysis_status,'')<>'private' "
              "AND i.private_path IS NULL AND i.rejected_path IS NULL "
              "AND (i.source_kind='fixed' OR i.staging_path IS NOT NULL OR i.archive_path IS NOT NULL)")


def _videos():
    with db() as con:
        return [dict(r) for r in con.execute(f"SELECT id,filename,source_fingerprint FROM inventory WHERE {_VISIBLE} ORDER BY id").fetchall()]


def _texts_missing() -> int:
    hook = _hook()
    with db() as con:
        have = {(r["model_key"], r["theme"]) for r in con.execute("SELECT model_key,theme FROM aiplus_texts").fetchall()}
    return sum(1 for t in hook.THEMES if (text_key(t), t) not in have)


def status() -> dict:
    ensure_schema()
    ae = _ae()
    ready = ae.aiplus_status()["ready"]
    vids = _videos()
    indexed, texts_missing = 0, 0
    if ready:
        key = frames_key()
        if vids:
            with db() as con:
                done = {int(r["inventory_id"]): r["source_fingerprint"] for r in
                        con.execute("SELECT inventory_id,source_fingerprint FROM aiplus_frames WHERE model_key=?", (key,)).fetchall()}
            indexed = sum(1 for v in vids if v["id"] in done and (done[v["id"]] or "") == (v["source_fingerprint"] or ""))
        texts_missing = _texts_missing()
    deep = _deep_videos() if ready else []
    if deep:
        left = _skipped()
        deep = [v for v in deep if _vid(v) not in left]
    deep_ready = len(_prepared({v["sha256"] for v in deep})) if deep else 0
    snap = dict(_STATE)     # one consistent picture of the running index
    eta = None              # seconds left, from the pace of this run (after the first video)
    if snap["state"] == "running" and not snap["waiting"]:
        if snap["phase"] == "reels":
            eta = snap["deep_eta"]
        elif snap["t0"] and snap["done"] > snap["n0"]:
            pace = max(0.0, time.time() - snap["t0"]) / (snap["done"] - snap["n0"])
            eta = round(pace * max(0, snap["total"] - snap["done"]))
    return {"model_ready": ready, "videos": len(vids), "indexed": indexed, "texts_missing": texts_missing, "eta_s": eta,
            "reels_videos": len(deep), "reels_ready": deep_ready,
            **{k: snap[k] for k in ("state", "done", "total", "error", "file", "waiting", "phase")}}


def search_needs_preparing(st: dict) -> bool:
    return st["videos"] > st["indexed"] or (st["texts_missing"] > 0 and st["videos"] > 0)


def needs_preparing(st: dict) -> bool:
    """Anything left: the search or what AI+ reels need."""
    return search_needs_preparing(st) or st.get("reels_videos", 0) > st.get("reels_ready", 0)


def running() -> bool:
    return _STATE["state"] == "running"


def start() -> bool:
    ae = _ae()
    if not ae.aiplus_status()["ready"]:
        raise ValueError("The AI+ model is not on this computer yet. Download it once on 'Check this PC'.")
    with _LOCK:
        if _STATE["state"] == "running":
            return False
        _STATE.update(state="running", done=0, total=0, error="", file="", waiting=False, t0=0.0, n0=0, phase="search", deep_eta=None)
    _STOP.clear()
    threading.Thread(target=_run, name="aiplus-library-index", daemon=True).start()
    return True


def stop() -> None:
    """Stop pressed: the worker ends the engine step within a second (it owns the process and its job handle)."""
    _STOP.set()


def shutdown() -> None:
    """The app is quitting: the engine step goes at once (on Windows its job object would end it anyway)."""
    _STOP.set()
    p = _PROC.get("p")
    if p is not None and p.poll() is None:
        try:
            p.kill() if os.name == "nt" else _ae()._kill_tree(p)
        except Exception:
            pass


atexit.register(shutdown)


def _scorer():
    _engine_path()
    import os
    import p13_pe_core_adapter as pa
    sc = pa.PECoreScorer(_ae().aiplus_dir(), full_check=False)
    model_dir = sc.model_dir

    def session(name):
        # inside the app (normal priority): one CPU left for the app, and idle model threads do not spin
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)
        so.add_session_config_entry("session.intra_op.allow_spinning", "0")
        return ort.InferenceSession(str(model_dir / name), so, providers=["CPUExecutionProvider"])
    sc._session = session
    return sc


def _load(part: str):
    """The model with the needed part opened now (opening is where memory runs out): one clear message."""
    try:
        sc = _scorer()
    except Exception as exc:
        raise RuntimeError(FILES_BAD if str(exc).startswith("P13_") else LOAD_FAILED) from exc
    try:
        getattr(sc, part)
    except Exception as exc:
        raise RuntimeError(LOAD_FAILED) from exc
    return sc


def _theme_texts(sc) -> None:
    """Text embeddings of every theme (and the bad descriptions), kept in the database: searches need no model."""
    hook = _hook()
    with db() as con:
        have = {(r["model_key"], r["theme"]) for r in con.execute("SELECT model_key,theme FROM aiplus_texts").fetchall()}
    neg = None
    for theme, (_name, prompts) in hook.THEMES.items():
        key = text_key(theme)
        if (key, theme) in have:
            continue
        neg = sc.encode_text(list(hook.NEGATIVE_PROMPTS)) if neg is None else neg
        pos = sc.encode_text(list(prompts))
        with db() as con:
            con.execute("DELETE FROM aiplus_texts WHERE theme=? AND model_key<>?", (theme, key))
            con.execute("INSERT OR REPLACE INTO aiplus_texts(model_key,theme,pos,neg) VALUES(?,?,?,?)",
                        (key, theme, pos.astype(np.float32).tobytes(), neg.astype(np.float32).tobytes()))
            con.commit()


def _reel_building() -> bool:
    """A reel build or the AI+ test reel of Check this PC is running."""
    if getattr(_ae(), "SELFTEST_RUNNING", None) is not None and _ae().SELFTEST_RUNNING.is_set():
        return True
    try:
        with db() as con:
            return con.execute("SELECT 1 FROM ae_jobs WHERE status='running' LIMIT 1").fetchone() is not None
    except Exception:
        return False


def _wait_for_reel() -> bool:
    """A reel is being built: it gets the computer (and its memory) first; the search waits. True if it waited."""
    if not _reel_building():
        return False
    _STATE.update(waiting=True, file="")
    while _reel_building() and not _STOP.is_set():
        time.sleep(2)
    _STATE.update(waiting=False)
    if _STOP.is_set():
        raise RuntimeError("Stopped.")
    return True


def _purge(key: str) -> None:
    """Rows of videos that are no longer in the Library (Private, rejected, removed) or of another model go."""
    with db() as con:
        con.execute(f"DELETE FROM aiplus_frames WHERE model_key<>? OR inventory_id NOT IN (SELECT id FROM inventory WHERE {_VISIBLE})", (key,))
        con.commit()


def _run() -> None:
    from .platform_adapter import keep_awake
    with keep_awake():                       # it may run all night: Windows must not go to sleep meanwhile
        _run_all()


def _run_all() -> None:
    sc = None
    try:
        from PIL import Image
        from . import service
        ensure_schema()
        key = frames_key()
        _purge(key)
        vids = _videos()
        with db() as con:
            done = {int(r["inventory_id"]): r["source_fingerprint"] for r in
                    con.execute("SELECT inventory_id,source_fingerprint FROM aiplus_frames WHERE model_key=?", (key,)).fetchall()}
        todo = [v for v in vids if not (v["id"] in done and (done[v["id"]] or "") == (v["source_fingerprint"] or ""))]
        _STATE.update(total=len(todo), done=0)
        if _texts_missing():
            _wait_for_reel()
            sc = _load("text")
            _theme_texts(sc)
            sc = None                                  # the text part is not needed for the frames: memory back
        for i, v in enumerate(todo):
            if _STOP.is_set():
                raise RuntimeError("Stopped.")
            if _reel_building():
                sc = None                         # the model's memory back to the reel BEFORE waiting for it
                import gc
                gc.collect()
            if _wait_for_reel():
                sc = None
                _STATE.update(t0=0.0)
            if not _STATE["t0"]:
                _STATE.update(t0=time.time(), n0=i)
            _STATE.update(done=i, file=v["filename"])
            try:
                info = service.cached_storyboard(v["id"]) or service.ensure_storyboard(v["id"])
            except Exception:
                info = None
            frames = (info or {}).get("frames") or []
            fallback = set((info or {}).get("fallback_slots") or [])   # a copy of a neighbour frame: its time is not its picture
            images, times = [], []                  # times: [preview frame number, second] of every frame looked at
            for k, fr in enumerate(frames):
                if k in fallback:
                    continue
                try:
                    with Image.open(fr["path"]) as im:
                        images.append(im.convert("RGB"))
                    times.append([k, float(fr["time"])])
                except Exception:
                    continue
            if not images:
                continue                      # no preview frames (file unavailable): tried again next time
            if sc is None:
                sc = _load("vision")
            try:
                emb = sc.encode_images(images).astype(np.float16)
            except MemoryError as exc:
                raise RuntimeError(LOAD_FAILED) from exc
            with db() as con:                 # only if the video is still in the Library, unchanged
                con.execute(f"INSERT OR REPLACE INTO aiplus_frames(inventory_id,model_key,times,emb,source_fingerprint,indexed_at) "
                            f"SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM inventory WHERE id=? AND {_VISIBLE} "
                            f"AND COALESCE(source_fingerprint,'')=COALESCE(?,''))",
                            (v["id"], key, json.dumps(times), emb.tobytes(), v["source_fingerprint"], now_iso(), v["id"], v["source_fingerprint"]))
                con.commit()
        sc = None                                      # memory back before the engine loads the model itself
        _deep()
        _STATE.update(state="done", file="", phase="")
    except Exception as exc:
        msg = str(exc)
        _STATE.update(state="stopped" if msg == "Stopped." else "failed", error="" if msg == "Stopped." else msg[:300], file="",
                      waiting=False, phase="")
    finally:
        sc = None


# ---- for reels: what the AI+ model sees in each video, ahead of time (engine script p13_prepare_scout.py) ----------

def _scout_dir() -> Path:
    return _ae().SHARED / "semantic_scout_pe"


def _deep_videos() -> list[dict]:
    """Library videos this step is for: in the Library, SHA-256 known (analysed), not Private, not a camcorder stream
    or a picture with an odd size (the reel analyses those as a converted copy)."""
    with db() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT id,filename,sha256,width,height,path,staging_path,archive_path,private_path,rejected_path,source_kind,source_fingerprint "
            f"FROM inventory WHERE {_VISIBLE} ORDER BY id").fetchall()]
    private = set(_ae()._private_hashes())
    out = []
    for r in rows:
        sha = str(r.get("sha256") or "").strip().lower()
        if not sha or sha in private or Path(r.get("filename") or "").suffix.lower() in LEFT_TO_REEL:
            continue
        if int(r.get("width") or 0) % 2 or int(r.get("height") or 0) % 2:
            continue
        out.append(dict(r, sha256=sha))
    return out


def _prepared(shas) -> set:
    """Which of these videos the shared cache has, for the current model and code."""
    d = _scout_dir()
    if not d.is_dir():
        return set()
    key = _hook().scout_key()
    ok = set()
    for sha in shas:
        j = d / (sha + ".json")
        try:
            st = j.stat()
        except OSError:
            _SCOUT_MEMO.pop(sha, None)
            continue
        m = _SCOUT_MEMO.get(sha)
        if not m or m[0] != (st.st_mtime_ns, st.st_size):
            k = ""
            kf = d / (sha + ".key")          # written last by write_scout: 64 bytes instead of the whole description
            try:
                if kf.stat().st_mtime_ns >= st.st_mtime_ns:
                    k = kf.read_text(encoding="utf-8").strip()
            except OSError:
                k = ""
            if not k:                         # an entry from before the key file existed
                try:
                    k = json.loads(j.read_text(encoding="utf-8")).get("key", "")
                except Exception:
                    k = ""
            m = ((st.st_mtime_ns, st.st_size), k)
            _SCOUT_MEMO[sha] = m
        if m[1] == key and (d / (sha + ".npy")).is_file():
            ok.add(sha)
    return ok


def _run_dir() -> Path:
    d = _ae().AE_ROOT / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _vid(v: dict) -> str:
    """A video in the list for the engine step and in its 'skipped' answer: the Library id and the file's
    fingerprint (a changed file is tried again)."""
    return f"{v['id']}|{v.get('source_fingerprint') or ''}"


# reasons the engine step gives for a video it leaves to the reel itself (not tried again until the file changes);
# any other reason (not readable now, cache not writable) is tried again on the next run
_FOR_GOOD = ("camcorder_stream", "odd_size", "analysis_failed", "changed_since_analysis", "no_length")
_SKIP_MEMO: dict = {}


def _skipped(for_good_only: bool = False) -> set:
    f = _run_dir() / "aiplus_prepare.skipped.json"
    try:
        st = f.stat()
    except OSError:
        return set()
    if _SKIP_MEMO.get("m") != (st.st_mtime_ns, st.st_size):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        _SKIP_MEMO.update(m=(st.st_mtime_ns, st.st_size), d=d if isinstance(d, dict) else {})
    d = _SKIP_MEMO.get("d") or {}
    return {k for k, r in d.items() if not for_good_only or str(r).split(":")[0] in _FOR_GOOD}


def _remember_skipped(new: dict, forget_transient: bool = False) -> None:
    f = _run_dir() / "aiplus_prepare.skipped.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        d = d if isinstance(d, dict) else {}
    except Exception:
        d = {}
    if forget_transient:                     # a new run tries them again (they come back if they fail again)
        d = {k: r for k, r in d.items() if str(r).split(":")[0] in _FOR_GOOD}
    d.update(new)
    tmp = f.with_name(f.name + ".tmp")
    try:
        tmp.write_text(json.dumps(d), encoding="utf-8")
        os.replace(tmp, f)
    except OSError:
        pass


def _deep_script() -> list[str]:
    ae = _ae()
    return [ae.engine_python(), "-B", "-s", "-E", "-X", "utf8", str(ae.ENGINE_DIR / "p13_prepare_scout.py")]


def _deep_command(list_file: Path, progress: Path, stop_file: Path) -> list[str]:
    ae = _ae()
    d = _run_dir()
    return [*_deep_script(), "--list", str(list_file),
            "--cache", str(_scout_dir()), "--runtime-dir", str(ae.ENGINE_DIR), "--pe-dir", str(ae.aiplus_dir()),
            "--progress", str(progress), "--stop", str(stop_file),
            "--skip-sha", str(d / "aiplus_prepare.private.txt"), "--skipped", str(d / "aiplus_prepare.run_skipped.json")]


def _deep_todo() -> list[str]:
    """Lines for the engine step: "id|fingerprint<TAB>sha256<TAB>path" of the videos still to prepare."""
    ae = _ae()
    from .service import _existing_local_path
    vids = _deep_videos()
    done = _prepared({v["sha256"] for v in vids})
    gone = _skipped(for_good_only=True)
    out, missing = [], {}
    for v in vids:
        if v["sha256"] in done or _vid(v) in gone:
            continue
        p = _existing_local_path(v)
        if not p:
            missing[_vid(v)] = "unreadable:not_on_this_pc"
            continue
        if ae.length_missing(p):          # the reel uses a copy with its length written (another SHA-256)
            missing[_vid(v)] = "no_length"
            continue
        out.append(f"{_vid(v)}\t{v['sha256']}\t{p}")
    if missing:
        _remember_skipped(missing)
    return out


def _write_private(path: Path, last: list) -> list:
    hashes = _ae()._private_hashes()
    if hashes != last:
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_text("\n".join(hashes), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            return last
    return hashes


def _deep() -> None:
    """Runs the engine step over the videos still to do; while a reel is being built it is ended (the reel gets the
    computer and its memory) and started again afterwards with what is left. Videos marked Private meanwhile are never
    looked at (the list of their SHA-256 is read again before every video) and leave the shared cache afterwards."""
    ae = _ae()
    ae.tidy_shared_cache(ae._private_hashes())
    run_dir = _run_dir()
    list_file, progress, stop_file, log_file = (run_dir / f"aiplus_prepare.{x}" for x in ("list.txt", "json", "stop", "log"))
    private_file, run_skipped = run_dir / "aiplus_prepare.private.txt", run_dir / "aiplus_prepare.run_skipped.json"
    first = True
    total = None
    _remember_skipped({}, forget_transient=True)
    _STATE.update(phase="reels", file="", deep_eta=None)
    while True:
        if _STOP.is_set():
            raise RuntimeError("Stopped.")
        _wait_for_reel()
        todo = _deep_todo()
        if total is None:
            total = len(todo)
        _STATE.update(phase="reels", total=total, done=max(0, total - len(todo)), file="", deep_eta=None)
        if not todo:
            return
        list_file.write_text("\n".join(todo) + "\n", encoding="utf-8")
        for f in (progress, stop_file, run_skipped):
            f.unlink(missing_ok=True)
        private = _write_private(private_file, None)
        kw = process_kw()
        paused = False
        with log_file.open("w" if first else "a", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(_deep_command(list_file, progress, stop_file), stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=ae._engine_env(), cwd=str(ae.ENGINE_DIR), **kw)
            ae._attach_job_object(proc)
            _PROC["p"] = proc
            first = False
            try:
                tick = 0
                while proc.poll() is None:
                    if _STOP.is_set() or _reel_building():
                        paused = not _STOP.is_set()
                        ae._kill_tree(proc)
                        try:
                            proc.wait(30)
                        except subprocess.TimeoutExpired:
                            pass
                        break
                    _pump(progress, total - len(todo), total)
                    tick += 1
                    if tick % 5 == 0:                 # Private marked meanwhile: the engine step reads this again
                        private = _write_private(private_file, private)
                    time.sleep(1)
            finally:
                _PROC.pop("p", None)
                h = ae._JOB_HANDLES.pop(proc.pid, None)
                if h is not None:
                    try:
                        import ctypes
                        from ctypes import wintypes
                        ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
                    except Exception:
                        pass
                try:
                    d = json.loads(run_skipped.read_text(encoding="utf-8"))
                    if isinstance(d, dict) and d:
                        _remember_skipped(d)
                except Exception:
                    pass
                try:
                    ae.tidy_shared_cache(ae._private_hashes())
                except Exception:
                    pass
        if _STOP.is_set():                 # ended by Stop: not an error
            raise RuntimeError("Stopped.")
        if paused:
            continue
        _pump(progress, total - len(todo), total)
        try:
            d = json.loads(progress.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        if proc.returncode != 0 or d.get("state") == "failed":
            err = str(d.get("error") or "")
            raise RuntimeError(FILES_BAD if "P13_" in err else LOAD_FAILED if ("MemoryError" in err or "alloc" in err.lower())
                               else "AI+ preparation failed: " + err[:200] if err else INTERRUPTED)
        return


def process_kw() -> dict:
    from .platform_adapter import process_kwargs
    return process_kwargs(below_normal=True) if os.name == "nt" else {"start_new_session": True}


def _pump(progress: Path, before: int, total: int) -> None:
    try:
        d = json.loads(progress.read_text(encoding="utf-8"))
    except Exception:
        return
    _STATE.update(done=min(total, before + int(d.get("done") or 0)), file=str(d.get("file") or ""), deep_eta=d.get("eta_s"))


def search(theme: str, limit: int | None = None) -> list[dict]:
    """Library videos for a theme, best first: [{inventory_id, filename, best_s, frame, score}] (score > 0 = matches;
    frame = the number of the preview frame of the best moment)."""
    hook = _hook()
    if theme not in hook.THEMES:
        raise ValueError("Unknown theme")
    ensure_schema()
    key = frames_key()
    with db() as con:
        t = con.execute("SELECT pos,neg FROM aiplus_texts WHERE model_key=? AND theme=?", (text_key(theme), theme)).fetchone()
        rows = con.execute(f"SELECT f.inventory_id,f.times,f.emb,i.filename FROM aiplus_frames f JOIN inventory i ON i.id=f.inventory_id "
                           f"WHERE f.model_key=? AND {_VISIBLE_I} AND COALESCE(f.source_fingerprint,'')=COALESCE(i.source_fingerprint,'')",
                           (key,)).fetchall()
    if not t or not rows:
        return []
    pos = np.frombuffer(t["pos"], np.float32).reshape(-1, 1024)
    neg = np.frombuffer(t["neg"], np.float32).reshape(-1, 1024)
    out = []
    for r in rows:
        emb = np.frombuffer(r["emb"], np.float16).astype(np.float32).reshape(-1, 1024)
        times = json.loads(r["times"])
        lp, ln = 100.0 * emb @ pos.T, 100.0 * emb @ neg.T
        k = min(2, lp.shape[1])
        margin = np.sort(lp, axis=1)[:, -k:].mean(axis=1) - ln.max(axis=1)
        i = int(np.argmax(margin))
        at = times[i] if i < len(times) else [i, 0.0]
        frame, best = (int(at[0]), float(at[1])) if isinstance(at, list) else (i, float(at))
        out.append({"inventory_id": int(r["inventory_id"]), "filename": r["filename"], "best_s": best, "frame": frame,
                    "score": round(float(margin[i]), 3)})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out if limit is None else out[: max(1, int(limit))]


def reel_files(theme: str, limit: int = 64) -> list[str]:
    """The videos of a theme search for a new reel: best first, files that are on this PC, one per file name (a reel
    refers to its sources by name), at most `limit`. Stops as soon as it has enough (no look at the rest)."""
    from .service import _existing_local_path
    good = [r for r in search(theme) if r["score"] > 0]
    picked, names = [], set()
    for k in range(0, len(good), 200):
        part = good[k:k + 200]
        with db() as con:
            rows = {int(r["id"]): dict(r) for r in con.execute(
                f"SELECT * FROM inventory WHERE {_VISIBLE} AND id IN ({','.join('?' for _ in part)})", [r["inventory_id"] for r in part]).fetchall()}
        for r in part:
            row = rows.get(r["inventory_id"])
            local = _existing_local_path(row) if row else None
            if local and local.name.lower() not in names:
                names.add(local.name.lower()); picked.append(str(local))
                if len(picked) >= limit:
                    return picked
    return picked

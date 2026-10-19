"""Voice-over and captions (an add-on of MediaEngine, installed with a button).

What it does
  * text -> a voice-over WAV in one voice (VoxCPM2, Apache-2.0), every piece listened to (faster-whisper, MIT) and
    made again when words are missing; captions (SRT, and ASS with the word being said highlighted) from the real
    times of the words
  * the voice-over onto a video: the video's own sound ducked under the voice (or muted), captions burned in, checked
  * captions for a video's own speech (any of Whisper's languages)

Where it lives
  DATA\\addons\\voice\\site      the add-on's Python packages (pip --target with the program's own Python 3.11:
                                torch with CUDA when the PC has an NVIDIA card, CPU torch otherwise)
  DATA\\addons\\voice\\models    the two models at pinned Hugging Face commits, every file checked (SHA-256 / git hash)
  DATA\\voice\\<id>\\            each voice-over or captions job: job.json, result.json, voice.wav, captions.srt/.ass,
                                the finished video

Nothing of it is in the program folder, so updates of MediaEngine keep it; the program never imports these packages
- the work runs in voice_worker.py, a separate Python process that sees only the add-on folder (-S). MediaEngine goes
online for it only when the owner presses "Install" (PyPI, download.pytorch.org, huggingface.co).
"""
from __future__ import annotations

import difflib, hashlib, json, os, re, shutil, subprocess, sys, threading, time, uuid
from pathlib import Path

from .config import HOME, load_config
from .db import now_iso
from .platform_adapter import process_kwargs

ADDON_VERSION = 1
# The Voice-over button on the Auto Edit page: on since a real install through the page and a real voice-over in voice
# 3.1, put onto a video with captions, passed on Windows (mediaengine-voice-addon.yml run 39247474464, 11/11).
SHOW_ON_HOME = True
ROOT = HOME / "addons" / "voice"
SITE = ROOT / "site"
MODELS = ROOT / "models"
MANIFEST = ROOT / "addon.json"
JOBS = HOME / "voice"
WORKER = Path(__file__).resolve().with_name("voice_worker.py")
ASSETS = Path(__file__).resolve().parent / "assets" / "voice"

TORCH = "2.8.0"
# Exactly the packages a voice-over really imports (measured on Windows: a VoxCPM2 voice-over in voice 3.1 and its
# Whisper check, run 39244854463), with their versions, installed without dependency resolution (--no-deps) and only
# as ready-made wheels: VoxCPM2's own list also pulls a web UI, a denoiser and cloud SDKs, five of them only as
# source code that needs a compiler on the PC. torch / torchaudio come from torch's CUDA index on an NVIDIA PC.
PACKAGES = [
    "annotated-types==0.8.0", "anyio==4.15.1", "audioread==3.1.0", "av==18.1.0", "brotli==1.2.0", "certifi==2026.10.18",
    "cffi==2.1.1", "charset-normalizer==3.5.2", "cloudpickle==3.1.2", "colorama==0.4.6", "ctranslate2==4.8.3",
    "decorator==5.3.1", "dill==0.3.8", "einops==0.8.2", "faster-whisper==1.2.1", "filelock==4.2.4", "fsspec==2025.3.0",
    "h11==0.16.0", "hf-xet==1.7.0", "httpcore2==2.14.0", "httpx2==2.14.0", "huggingface-hub==2.2.0", "idna==3.20",
    "jinja2==3.1.6", "joblib==1.6.0", "lazy-loader==0.6", "librosa==0.11.0", "llvmlite==0.50.0", "markupsafe==3.0.4",
    "mpmath==1.3.0", "msgpack==1.2.3", "networkx==3.6.1", "numba==0.68.0", "numpy==2.4.6", "onnxruntime==1.31.0",
    "packaging==26.3", "pillow==12.3.0", "platformdirs==4.13.5", "pooch==1.9.0", "pycparser==3.11", "pydantic==2.14.1",
    "pydantic-core==2.50.1", "pyyaml==6.0.3", "regex==2026.9.29", "requests==2.34.2", "safetensors==0.8.0",
    "scipy==1.17.1", "setuptools==84.0.0", "soundfile==0.14.0", "soxr==1.1.0", "sympy==1.14.0", "tokenizers==0.23.3",
    f"torch=={TORCH}", f"torchaudio=={TORCH}", "tqdm==4.70.1", "transformers==5.20.1", "truststore==0.10.5",
    "typing-extensions==4.16.0", "typing-inspection==0.4.4", "urllib3==2.8.0", "voxcpm==2.0.3", "xxhash==4.0.2",
]
CUDA_INDEX = "https://download.pytorch.org/whl/cu126"      # GTX 10xx - RTX 40xx (torch's CUDA 12.6 build)
CUDA_INDEX_NEW = "https://download.pytorch.org/whl/cu128"  # RTX 50xx (Blackwell needs CUDA 12.8)
VOXCPM_REPO, VOXCPM_REV = "openbmb/VoxCPM2", "32279effe8c19989596f05d353d1447f51d9e915"
WHISPER_REPO, WHISPER_REV = "Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120"
NEED_FREE = 20 * 10 ** 9            # packages (2.8 GB with CPU torch, ~5 GB with CUDA) + models (5.4 GB) + room
MAX_TEXT = 5000

_LOCK = threading.Lock()
INSTALL = {"state": "idle", "step": "", "done": 0, "total": 0, "error": "", "detail": "", "started": 0.0}
_STOP = threading.Event()
_QUEUE: list[str] = []
_CURRENT: dict = {}
_WAKE = threading.Event()
_THREAD: list[threading.Thread] = []

# The owner's picks from the voice lab (round 4, 2026-10-19 15:41: "4_4 will do, 4_2 OK"; 3.1 "sounds like sex",
# its locked copy "too squeaky for business info"): the very takes 4_4 and 4_2 ship with the program (FLAC) and every
# voice-over in them is that same voice (VoxCPM2 ultimate cloning: the recording, its exact words, the same recording
# as the timbre). Both recordings say this text:
HOST_REF_TEXT = ("Okay... so here's something nobody tells you about packing for a beach trip. "
                 "You don't need ten outfits. Seriously. You need, like, three. And one really good hat. "
                 "We tried it last summer and, honestly? It changed everything. "
                 "Less stuff... more time in the water. So, would you try it? Tell me in the comments!")
VOICES = {
    "host_4_4": {"label": "Host - the voice of 4_4", "ref": "host_4_4.flac", "ref_text": HOST_REF_TEXT},
    "host_4_2": {"label": "Host - the voice of 4_2", "ref": "host_4_2.flac", "ref_text": HOST_REF_TEXT},
    "describe": {"label": "My description of a voice (English works best)"},
    "own": {"label": "A voice from a recording (a person who agreed to it)"},
}
DEFAULT_VOICE = "host_4_4"
# "microphone" finishing (round 4: the same take was "too tired" as made and "will do" with it): a gentle roll-off of
# the highest frequencies (where a neural vocoder's glassy sheen is), a touch of tape-like saturation, a small room,
# light compression. Nothing is cut or moved in time (the captions' word times stay right).
MIC_CHAIN = ("highpass=f=80,lowpass=f=11000:p=1,asoftclip=type=tanh:threshold=0.9,aecho=0.9:0.9:23|37|53:0.06|0.045|0.03,"
             "acompressor=threshold=-22dB:ratio=2:attack=10:release=150:makeup=1.3,")


class VoiceError(Exception):
    pass


# ---------------------------------------------------------------- the add-on: there or not, installing

def _python() -> str:
    """The program's own python.exe (not pythonw: pip and the worker print), the same 3.11 the add-on was made for."""
    exe = Path(sys.executable)
    cand = exe.with_name("python.exe") if os.name == "nt" else exe
    return str(cand if cand.is_file() else exe)


def manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text("utf-8"))
    except Exception:
        return {}


def installed() -> bool:
    m = manifest()
    return bool(m.get("version") == ADDON_VERSION and m.get("python") == f"{sys.version_info[0]}.{sys.version_info[1]}"
                and SITE.is_dir() and (MODELS / "voxcpm").is_dir() and (MODELS / "whisper").is_dir())


def status() -> dict:
    m = manifest()
    s = dict(INSTALL)
    s.update(installed=installed(), manifest=m, needs_reinstall=bool(m) and not installed() and s["state"] != "running",
             nvidia=_nvidia_name(), free=_free(ROOT))
    return s


def _free(p: Path) -> int:
    q = p
    while not q.exists() and q != q.parent:
        q = q.parent
    try:
        return shutil.disk_usage(q).free
    except OSError:
        return 0


_GPU: list = []


def _nvidia_name() -> str:
    if not _GPU:
        try:
            from .hwdecode import gpu_names_cached
            names = gpu_names_cached()
        except Exception:
            names = []
        _GPU.append(next((n.split(" - ")[0] for n in names if "nvidia" in n.lower()), ""))
    return _GPU[0]


def installing() -> bool:
    return INSTALL["state"] == "running"


def why_not_install() -> str:
    if os.environ.get("MEDIAENGINE_VOICE") == "off":
        return "The voice add-on is turned off on this PC (MEDIAENGINE_VOICE=off)."
    if sys.version_info[:2] != (3, 11):
        return "The voice add-on needs MediaEngine's own Python 3.11."
    return ""


def start_install(cpu: bool = False) -> None:
    why = why_not_install()
    if why:
        raise VoiceError(why)
    with _LOCK:
        if INSTALL["state"] == "running":
            raise VoiceError("The voice add-on is already being installed.")
        if installed() and not cpu:
            raise VoiceError("The voice add-on is already installed.")
        if busy():
            raise VoiceError("A voice-over is being made. Install when it is ready.")
        INSTALL.update(state="running", step="checking", done=0, total=0, error="", detail="", started=time.time())
    _STOP.clear()
    threading.Thread(target=_install, args=(cpu,), name="voice-install", daemon=True).start()


def cancel_install() -> None:
    _STOP.set()


def _hf_files(repo: str, rev: str) -> list[tuple[str, int, str, str]]:
    """(path, size, kind, hash) of every file of the model at its pinned commit: kind 'sha256' (LFS) or 'git' (blob)."""
    import urllib.request
    url = f"https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MediaEngine"}), timeout=60) as r:
        info = json.load(r)
    if info.get("sha") != rev:
        raise VoiceError(f"huggingface.co did not give the pinned version of {repo}.")
    out = []
    for s in info.get("siblings") or []:
        name = str(s.get("rfilename") or "")
        if not name or name.startswith(".") or "/." in name or ".." in Path(name).parts or name.lower().endswith((".md", ".png", ".jpg", ".gif")):
            continue
        lfs = s.get("lfs") or {}
        if lfs.get("sha256"):
            out.append((name, int(lfs.get("size") or s.get("size") or 0), "sha256", lfs["sha256"]))
        elif s.get("blobId"):
            out.append((name, int(s.get("size") or 0), "git", s["blobId"]))
    if not out:
        raise VoiceError(f"huggingface.co listed no files for {repo}.")
    return out


def _file_ok(p: Path, size: int, kind: str, want: str) -> bool:
    if not p.is_file() or p.stat().st_size != size:
        return False
    h = hashlib.sha256() if kind == "sha256" else hashlib.sha1(b"blob %d\0" % size)
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == want


def _pip(site_dir: Path, cpu: bool, log: Path) -> None:
    from . import auto_edit as ae
    tmp = ROOT / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    cmd = [_python(), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "--no-input",
           "--progress-bar", "off", "--no-cache-dir", "--only-binary", ":all:", "--no-deps", "--target", str(site_dir),
           "--index-url", "https://pypi.org/simple"]
    if not cpu:
        cmd += ["--extra-index-url", CUDA_INDEX_NEW if re.search(r"RTX\s*50\d0", _nvidia_name(), re.I) else CUDA_INDEX]
    cmd += PACKAGES
    env = dict(os.environ, TMP=str(tmp), TEMP=str(tmp), PIP_NO_INPUT="1", PYTHONNOUSERSITE="1")
    env.pop("PYTHONPATH", None)
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        lf.write("\n$ " + " ".join(cmd) + "\n")
        lf.flush()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                encoding="utf-8", errors="replace", env=env, **process_kwargs(below_normal=True))
        ae._attach_job_object(proc)
        threading.Thread(target=lambda: (_STOP.wait(), proc.poll() is None and proc.kill()), daemon=True).start()
        for line in proc.stdout:
            lf.write(line)
            m = re.match(r"\s*(Collecting|Downloading|Installing collected packages|Successfully installed)\s*(\S*)", line)
            if m:
                word = {"Collecting": "Looking for", "Downloading": "Downloading", "Installing collected packages": "Installing",
                        "Successfully installed": "Installed"}[m.group(1)]
                INSTALL.update(detail=(word + " " + m.group(2).split("/")[-1])[:160])
            if _STOP.is_set():
                proc.kill()
                break
        proc.wait()
    if _STOP.is_set():
        raise VoiceError("Installation cancelled.")
    if proc.returncode != 0:
        raise VoiceError("The add-on's Python parts could not be installed. Check the internet connection and try again "
                         "(details for support: install.log in the add-on folder).")


def _install(cpu: bool) -> None:
    from .platform_adapter import keep_awake
    with keep_awake():                       # a PC that sleeps drops the download (pip would start over)
        _install_now(cpu)


def _install_now(cpu: bool) -> None:
    import http.client, socket, urllib.error
    from . import auto_edit as ae
    log = ROOT / "install.log"
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        if _free(ROOT) < NEED_FREE:
            raise VoiceError("Not enough free space on the disk of the data folder: the voice add-on needs about 20 GB free.")
        gpu = "" if cpu else _nvidia_name()
        new_site = ROOT / "site.__install__"
        if new_site.exists():
            shutil.rmtree(new_site, ignore_errors=True)
        INSTALL.update(step="packages", detail="")
        _pip(new_site, cpu or not gpu, log)
        INSTALL.update(step="models", detail="")
        files = []
        for key, repo, rev in (("voxcpm", VOXCPM_REPO, VOXCPM_REV), ("whisper", WHISPER_REPO, WHISPER_REV)):
            files += [(key, repo, rev, *f) for f in _hf_files(repo, rev)]
        total = sum(f[4] for f in files)
        if _free(ROOT) < total + 1_000_000_000:
            raise VoiceError("Not enough free space left for the voice models.")
        INSTALL.update(total=total, done=0)
        done = 0
        for key, repo, rev, name, size, kind, want in files:
            dst = MODELS / (key + ".__install__") / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            INSTALL.update(detail=Path(name).name)
            have = MODELS / key / name
            if not _file_ok(dst, size, kind, want) and _file_ok(have, size, kind, want):
                ae._replace_retry(have, dst)              # from an earlier install: moved, not downloaded again
            if not _file_ok(dst, size, kind, want):
                part = dst.with_name(dst.name + ".part")
                base = done
                ae._fetch_resumable(f"https://huggingface.co/{repo}/resolve/{rev}/{name}", part, size,
                                    lambda have, base=base: INSTALL.update(done=base + have), stop=_STOP)
                if not _file_ok(part, size, kind, want):
                    part.unlink(missing_ok=True)
                    raise VoiceError("A downloaded model file is not the exact file (" + Path(name).name + "). Try again.")
                ae._replace_retry(part, dst)
            done += size
            INSTALL.update(done=done)
        INSTALL.update(step="checking_addon", detail="")
        for key in ("voxcpm", "whisper"):
            fin = MODELS / key
            if fin.exists():
                shutil.rmtree(fin, ignore_errors=True)
            ae._replace_retry(MODELS / (key + ".__install__"), fin, tries=30)
        old = None
        if SITE.exists():
            old = ROOT / f"site.__old__{int(time.time())}"
            ae._replace_retry(SITE, old, tries=30)
        try:
            ae._replace_retry(new_site, SITE, tries=30)
        except Exception:
            if old is not None and not SITE.exists():
                ae._replace_retry(old, SITE, tries=30)          # the add-on as it was
            raise
        if old is not None:
            shutil.rmtree(old, ignore_errors=True)
        test = _run_worker({"task": "selftest"}, ROOT / "selftest", timeout=600)
        if not test.get("ok"):
            raise VoiceError("The voice add-on was installed but does not start: " + str(test.get("error") or "")[:300])
        m = {"version": ADDON_VERSION, "python": f"{sys.version_info[0]}.{sys.version_info[1]}", "packages": PACKAGES,
             "torch": test.get("torch"), "cuda": bool(test.get("cuda")), "gpu": test.get("gpu") or "",
             "vram_gb": test.get("vram_gb") or 0, "models": {"voxcpm": [VOXCPM_REPO, VOXCPM_REV],
                                                             "whisper": [WHISPER_REPO, WHISPER_REV]},
             "installed_at": now_iso(), "bytes": _tree_bytes(ROOT)}
        tmp = MANIFEST.with_suffix(".tmp")
        tmp.write_text(json.dumps(m, indent=1), "utf-8")
        os.replace(tmp, MANIFEST)
        shutil.rmtree(ROOT / "tmp", ignore_errors=True)
        INSTALL.update(state="done", step="", detail="", done=INSTALL["total"])
    except Exception as exc:
        msg = str(exc)
        if _STOP.is_set():
            msg = "Installation cancelled."
        elif isinstance(exc, urllib.error.HTTPError):
            msg = f"The download answered HTTP {exc.code}. Try again later."
        elif isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException)):
            msg = "No connection to the internet (or the site did not answer). Check the connection and try again."
        INSTALL.update(state="failed", error=msg[:400], failed_at=time.time())
        try:
            with log.open("a", encoding="utf-8") as lf:
                lf.write(f"\nFAILED: {exc!r}\n")
        except Exception:
            pass


def _tree_bytes(p: Path) -> int:
    n = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                n += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return n


def remove_addon() -> None:
    """Delete the add-on (packages and models; the voice-overs made with it stay)."""
    if installing() or busy():
        raise VoiceError("The voice add-on is busy. Wait until it has finished.")
    for name in ("site", "models", "site.__install__", "tmp", "selftest"):
        shutil.rmtree(ROOT / name, ignore_errors=True)
    for old in ROOT.glob("site.__old__*"):
        shutil.rmtree(old, ignore_errors=True)
    MANIFEST.unlink(missing_ok=True)
    INSTALL.update(state="idle", step="", error="", detail="", done=0, total=0)


# ---------------------------------------------------------------- the worker process

def _run_worker(job: dict, work: Path, timeout: float = 3600, on_line=None) -> dict:
    from . import auto_edit as ae
    work.mkdir(parents=True, exist_ok=True)
    job = dict(job, site=str(SITE), model_dir=str(MODELS / "voxcpm"), whisper_dir=str(MODELS / "whisper"),
               work_dir=str(work))
    jf = work / "worker_job.json"
    jf.write_text(json.dumps(job, ensure_ascii=False, indent=1), "utf-8")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "HF_", "TRANSFORMERS"))
           and k.upper() not in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    log = work.parent / "worker.log"          # next to the work folder: kept when the pieces are cleaned away
    res: dict = {}
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        proc = subprocess.Popen([_python(), "-S", "-E", "-B", "-X", "utf8", str(WORKER), str(jf)], stdout=subprocess.PIPE,
                                stderr=lf, stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=env,
                                cwd=str(work), **process_kwargs(below_normal=True))
        ae._attach_job_object(proc)
        _CURRENT["proc"] = proc
        t0 = time.time()
        killer = threading.Timer(timeout, proc.kill)
        killer.start()
        try:
            for line in proc.stdout:
                lf.write(line)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if "result" in msg:
                    res = msg["result"] or {}
                elif on_line:
                    on_line(msg)
            proc.wait()
        finally:
            killer.cancel()
            _CURRENT.pop("proc", None)
    if not res:
        cut = time.time() - t0 >= timeout
        res = {"ok": False, "error": "The voice worker took too long and was stopped." if cut else
               "The voice worker stopped without an answer (details: worker.log in the job folder)."}
    return res


# ---------------------------------------------------------------- text, captions

def chunks(text: str, limit: int = 220) -> list[dict]:
    """The text in pieces the model says well (sentences, at most ~220 characters), each with the pause after it."""
    text = str(text or "").replace("\r\n", "\n").strip()
    out: list[dict] = []
    for para in re.split(r"\n\s*\n", text):
        para = re.sub(r"\s+", " ", para).strip()
        if not para:
            continue
        sentences = re.split(r"(?<=[.!?…])\s+", para)
        cur = ""
        for s in sentences:
            while len(s) > limit:                    # a very long sentence: cut at a comma / space
                cut = max(s.rfind(", ", 0, limit), s.rfind("; ", 0, limit))
                cut = cut + 1 if cut > limit // 3 else (s.rfind(" ", 0, limit) if s.rfind(" ", 0, limit) > 0 else limit)
                head, s = s[:cut].strip(), s[cut:].strip()
                if cur:
                    out.append({"text": cur, "pause_after": 0.3}); cur = ""
                out.append({"text": head, "pause_after": 0.2})
            if cur and len(cur) + 1 + len(s) > limit:
                out.append({"text": cur, "pause_after": 0.35}); cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            out.append({"text": cur, "pause_after": 0.35})
        if out:
            out[-1]["pause_after"] = 0.6                 # a new paragraph: a longer breath
    if out:
        out[-1]["pause_after"] = 0.4
    return out


def _norm(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower().replace("’", "'"))


def align(script: str, heard: list[dict]) -> list[dict]:
    """The script's own words (as written) with the times the listener heard them; words it did not hear get times
    between their neighbours. Without a script: what was heard."""
    toks = [t for t in re.split(r"\s+", re.sub(r"\([^)]*\)|\[[a-z ]+\]", " ", str(script or ""))) if _norm(t)]
    if not toks:
        return [{"w": h["w"], "s": h["s"], "e": h["e"]} for h in heard if _norm(h["w"])]
    hw = [h for h in heard if _norm(h["w"])]
    a, b = [_norm(t) for t in toks], [_norm(h["w"]) for h in hw]
    times: list[tuple[float, float] | None] = [None] * len(toks)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                times[i1 + k] = (hw[j1 + k]["s"], hw[j1 + k]["e"])
        elif tag == "replace" and j2 > j1:           # n script words for m heard words: spread over their time
            s, e = hw[j1]["s"], hw[j2 - 1]["e"]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (s + (e - s) * k / n, s + (e - s) * (k + 1) / n)
    i = 0
    while i < len(times):                          # words not heard: spread evenly between their neighbours
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        prev = times[i - 1][1] if i > 0 else (times[j][0] - 0.3 * (j - i) if j < len(times) else 0.0)
        prev = max(0.0, prev)
        nxt = times[j][0] if j < len(times) else prev + 0.3 * (j - i)
        step = max(0.05, (nxt - prev) / (j - i)) if nxt > prev else 0.05
        for k in range(i, j):
            s0 = prev + step * (k - i)
            times[k] = (s0, s0 + step)
        i = j
    return [{"w": t, "s": round(times[i][0], 3), "e": round(max(times[i][1], times[i][0] + 0.05), 3)} for i, t in enumerate(toks)]


def cues(words: list[dict], max_words: int = 4, max_s: float = 1.8) -> list[dict]:
    """Words grouped into short captions (a few words, a phrase ends at punctuation), never overlapping."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["e"] - cur[0]["s"] > max_s or w["s"] - cur[-1]["e"] > 0.6):
            out.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.!?…,;:]$", w["w"]):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    res = []
    for i, c in enumerate(out):
        end = max(c[-1]["e"] + 0.15, c[0]["s"] + 0.3)       # long enough to read...
        if i + 1 < len(out):                                 # ...but never over the next caption (two lines would stack)
            end = min(end, out[i + 1][0]["s"] - 0.01)
        res.append({"s": c[0]["s"], "e": max(end, c[0]["s"] + 0.05), "words": c})
    return res


def _ts(t: float, sep: str = ",") -> str:
    t = max(0.0, t)
    h, rem = divmod(int(round(t * 1000)), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def srt(cs: list[dict], offset: float = 0.0) -> str:
    rows = []
    for i, c in enumerate(cs, 1):
        rows.append(f"{i}\n{_ts(c['s'] + offset)} --> {_ts(c['e'] + offset)}\n{' '.join(w['w'] for w in c['words'])}\n")
    return "\n".join(rows)


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _ass_text(t: str) -> str:
    return t.replace("\\", "⧵").replace("{", "(").replace("}", ")").replace("\n", " ")


def ass(cs: list[dict], width: int, height: int, offset: float = 0.0, position: str = "bottom") -> str:
    """Captions for burning in: big bold white words with a dark outline; the word being said turns yellow."""
    size = max(18, int(min(width, height) * (0.075 if height > width else 0.06)))
    margin = int(height * (0.20 if position == "bottom" else 0.42 if position == "middle" else 0.10))
    align_no = 2 if position == "bottom" else 5 if position == "middle" else 8
    head = ("[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
            f"PlayResX: {width}\nPlayResY: {height}\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Cap,Arial,{size},&H0000E5FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,"
            f"{max(2, size // 14)},{max(1, size // 28)},{align_no},{int(width * 0.08)},{int(width * 0.08)},{margin},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = []
    for c in cs:
        parts, t = [], c["s"]
        for w in c["words"]:
            gap = max(0.0, w["s"] - t)
            if gap > 0.005:
                parts.append("{\\k%d}" % round(gap * 100))
            parts.append("{\\k%d}%s " % (max(1, round((w["e"] - max(w["s"], t)) * 100)), _ass_text(w["w"])))
            t = max(t, w["e"])
        lines.append(f"Dialogue: 0,{_ass_time(c['s'] + offset)},{_ass_time(c['e'] + offset)},Cap,,0,0,0,,{''.join(parts).rstrip()}")
    return head + "\n".join(lines) + "\n"


# ---------------------------------------------------------------- jobs (one at a time, in a background thread)

def _job_dir(jid: str) -> Path:
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}", str(jid or "")):
        raise VoiceError("No such voice-over.")
    return JOBS / jid


def read_job(jid: str) -> dict:
    d = _job_dir(jid)
    try:
        job = json.loads((d / "job.json").read_text("utf-8"))
    except Exception:
        raise VoiceError("No such voice-over.")
    try:
        job["result"] = json.loads((d / "result.json").read_text("utf-8"))
    except Exception:
        job["result"] = None
    job["dir"] = str(d)
    job["state"] = ("working" if _CURRENT.get("id") == jid else "waiting" if jid in _QUEUE else
                    ("done" if (job["result"] or {}).get("ok") else "failed") if job["result"] else "interrupted")
    if job["state"] == "working":
        job["progress"] = _CURRENT.get("progress", 0.0)
        job["step"] = _CURRENT.get("step", "")
    return job


def list_jobs(limit: int = 50) -> list[dict]:
    out = []
    try:
        names = sorted((p.name for p in JOBS.iterdir() if p.is_dir()), reverse=True)[:limit]
    except OSError:
        names = []
    for n in names:
        try:
            out.append(read_job(n))
        except VoiceError:
            pass
    return out


def busy() -> str:
    """The voice-over job running now or waiting ('' when none): Quit / Restart / switching builds ask first."""
    return str(_CURRENT.get("id") or (_QUEUE[0] if _QUEUE else "") or ("install" if installing() else ""))


def _new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def _need_addon() -> None:
    if not installed():
        raise VoiceError("Install the voice add-on first.")


def _submit(job: dict) -> str:
    _need_addon()
    if installing():
        raise VoiceError("The voice add-on is being installed. Wait until it is ready.")
    jid = _new_id()
    d = JOBS / jid
    d.mkdir(parents=True, exist_ok=True)
    job = dict(job, id=jid, created_at=now_iso())
    with _LOCK:                         # written and queued in one step: a page never sees it "interrupted"
        (d / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=1), "utf-8")
        _QUEUE.append(jid)
        if not _THREAD or not _THREAD[0].is_alive():
            _THREAD[:] = [threading.Thread(target=_loop, name="voice-jobs", daemon=True)]
            _THREAD[0].start()
    _WAKE.set()
    return jid


def new_voiceover(text: str, voice: str, description: str = "", ref_path: str = "", ref_text: str = "",
                  language: str = "", mic: bool = True) -> str:
    _need_addon()
    text = str(text or "").strip()
    if not text:
        raise VoiceError("Type the text of the voice-over first.")
    if len(text) > MAX_TEXT:
        raise VoiceError("The text is too long for one voice-over (at most 5000 characters): split it into parts.")
    if voice not in VOICES:
        raise VoiceError("Choose a voice.")
    v: dict = {"key": voice}
    if VOICES[voice].get("ref"):
        ref = ASSETS / VOICES[voice]["ref"]
        if not ref.is_file():
            raise VoiceError("The recording of this voice is missing from this version of MediaEngine.")
        v.update(ref_wav=str(ref), ref_text=VOICES[voice]["ref_text"])
    elif voice == "describe":
        description = re.sub(r"[()\r\n]+", " ", str(description or "")).strip()
        if len(description) < 10:
            raise VoiceError("Describe the voice in a few words (for example: a calm man in his forties, deep voice).")
        v["description"] = description[:400]
    elif voice == "own":
        p = Path(str(ref_path or "").strip().strip('"'))
        if not p.is_file():
            raise VoiceError("Choose the recording of the voice (a WAV, MP3 or M4A of 5-30 seconds of one person speaking).")
        v.update(ref_source=str(p), ref_text=re.sub(r"\s+", " ", str(ref_text or "")).strip()[:1000])
    lang = str(language or "").strip().lower()
    if lang and not re.fullmatch(r"[a-z]{2}", lang):
        lang = ""
    return _submit({"kind": "voiceover", "text": text, "voice": v, "language": lang or None, "mic": bool(mic),
                    "title": re.sub(r"\s+", " ", text)[:60]})


def new_captions(source: str, language: str = "", position: str = "bottom") -> str:
    _need_addon()
    p = Path(str(source or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose a video (its full path) to make captions for.")
    return _submit({"kind": "captions", "source": str(p), "language": (language or "").strip().lower()[:2] or None,
                    "position": position if position in ("bottom", "middle", "top") else "bottom", "title": p.name[:60]})


def new_dub(jid: str, video: str, keep_sound: bool = True, captions: bool = True, position: str = "bottom",
            start_s: float = 0.3) -> str:
    """The voice-over `jid` onto a video: a new MP4 (the video itself is only read)."""
    _need_addon()
    src = read_job(jid)
    if not (src.get("result") or {}).get("ok") or src.get("kind") != "voiceover":
        raise VoiceError("This voice-over is not ready.")
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the video (its full path).")
    try:
        start_s = max(0.0, min(60.0, float(str(start_s).strip().replace(",", ".") or 0.3)))
    except (TypeError, ValueError):
        raise VoiceError("The start of the voice must be a number of seconds, for example 0.5.")
    return _submit({"kind": "dub", "voiceover": jid, "video": str(p), "keep_sound": bool(keep_sound),
                    "captions": bool(captions), "position": position if position in ("bottom", "middle", "top") else "bottom",
                    "start_s": start_s, "title": p.name[:60]})


def _loop() -> None:
    while True:
        with _LOCK:
            jid = _QUEUE[0] if _QUEUE else None
        if not jid:
            _WAKE.wait(5)
            _WAKE.clear()
            with _LOCK:
                if not _QUEUE:
                    _THREAD.clear()
                    return
            continue
        _CURRENT.clear()
        _CURRENT.update(id=jid, progress=0.0, step="starting")
        try:
            from .platform_adapter import keep_awake
            with keep_awake():
                res = _do(jid)
        except Exception as exc:
            res = {"ok": False, "error": str(exc)[:500]}
        res["finished_at"] = now_iso()
        try:
            d = JOBS / jid
            tmp = d / "result.json.tmp"
            tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
            os.replace(tmp, d / "result.json")
        except OSError:
            pass
        with _LOCK:
            if _QUEUE and _QUEUE[0] == jid:
                _QUEUE.pop(0)
        _CURRENT.clear()


def _progress(msg: dict) -> None:
    if "progress" in msg:
        _CURRENT["progress"] = float(msg["progress"])
    if msg.get("step"):
        _CURRENT["step"] = str(msg["step"]) + (f" {msg['chunk']}/{msg['chunks']}" if msg.get("chunk") else "")


def _ffmpeg() -> str:
    from .media import _ffmpeg_exe
    ff = _ffmpeg_exe()
    if not ff:
        raise VoiceError("FFmpeg is missing from this MediaEngine.")
    return ff


def _do(jid: str) -> dict:
    d = JOBS / jid
    job = json.loads((d / "job.json").read_text("utf-8"))
    if job["kind"] == "voiceover":
        v = dict(job["voice"])
        if v.get("ref_source"):                      # the owner's recording: a clean mono WAV of at most 30 s
            ref = d / "reference.wav"
            cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", v["ref_source"], "-t", "30",
                                 "-ac", "1", "-ar", "24000", str(ref)], **process_kwargs(dict(capture_output=True, timeout=120)))
            if cp.returncode != 0 or not ref.is_file():
                return {"ok": False, "error": "The recording of the voice could not be read."}
            v["ref_wav"] = str(ref)
        cfg = (load_config().get("voice") or {})
        device = cfg.get("device") or ("cuda" if manifest().get("cuda") else "cpu")
        res = _run_worker({"task": "tts", "chunks": chunks(job["text"]), "voice": v, "language": job.get("language"),
                           "out_wav": str(d / "voice_raw.wav"), "seed": int(cfg.get("seed") or 1),
                           "steps": cfg.get("steps"), "device": device}, d / "work", timeout=6 * 3600,
                          on_line=_progress)
        if not res.get("ok"):
            return res
        _CURRENT.update(step="finishing", progress=0.97)
        cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(d / "voice_raw.wav"),
                             "-af", (MIC_CHAIN if job.get("mic", True) else "") + "loudnorm=I=-16:TP=-1.5:LRA=11",
                             "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
                             str(d / "voice.wav")], **process_kwargs(dict(capture_output=True, timeout=600)))
        if cp.returncode != 0:
            return {"ok": False, "error": "The voice-over could not be finished (loudness)."}
        words = align(job["text"], res.get("words") or [])
        (d / "words.json").write_text(json.dumps(words, ensure_ascii=False), "utf-8")
        (d / "captions.srt").write_text(srt(cues(words)), "utf-8")
        if not cfg.get("keep_work"):                      # the pieces and tries (kept only when asked, for support)
            shutil.rmtree(d / "work", ignore_errors=True)
        n = max(1, len(re.findall(r"[\w']+", job["text"])))
        return {"ok": True, "seconds": res.get("seconds"), "device": res.get("device"), "said": res.get("said"),
                "word_errors": res.get("word_errors"), "words": n, "chunks": res.get("chunks"), "load_s": res.get("load_s"),
                "steps": res.get("steps"), "language": res.get("language"),
                "files": {"voice": "voice.wav", "srt": "captions.srt"}}
    if job["kind"] == "captions":
        res = _run_worker({"task": "transcribe", "source": job["source"], "wav16": str(d / "sound16k.wav"),
                           "ffmpeg": _ffmpeg(), "language": job.get("language")}, d / "work", timeout=6 * 3600,
                          on_line=_progress)
        (d / "sound16k.wav").unlink(missing_ok=True)
        if not res.get("ok"):
            return res
        words = align("", res.get("words") or [])
        if not words:
            return {"ok": False, "error": "No speech was found in this video."}
        cs = cues(words)
        (d / "captions.srt").write_text(srt(cs), "utf-8")
        out = _burn(Path(job["source"]), None, cs, d, keep_sound=True, position=job.get("position") or "bottom", offset=0.0)
        return {"ok": True, "said": res.get("said"), "language": res.get("language"), "words": len(words), **out}
    if job["kind"] == "dub":
        vo = JOBS / job["voiceover"]
        words = json.loads((vo / "words.json").read_text("utf-8"))
        cs = cues(words) if job.get("captions") else []
        out = _burn(Path(job["video"]), vo / "voice.wav", cs, d, keep_sound=job.get("keep_sound", True),
                    position=job.get("position") or "bottom", offset=float(job.get("start_s") or 0.0))
        return {"ok": True, **out}
    return {"ok": False, "error": "Unknown job."}


def _caption_font(d: Path) -> bool:
    """Windows: Arial Bold copied next to the captions (fonts/), so the subtitle renderer finds it whatever its font
    set-up is (FFmpeg's fontconfig has no configuration on Windows). Elsewhere the system's fonts are used."""
    if os.name != "nt":
        return False
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("arialbd.ttf", "arial.ttf"):
        if (fonts / name).is_file():
            try:
                (d / "fonts").mkdir(exist_ok=True)
                shutil.copy2(fonts / name, d / "fonts" / name)
                return True
            except OSError:
                return False
    return False


def _burn(video: Path, voice_wav: Path | None, cs: list[dict], d: Path, keep_sound: bool, position: str,
          offset: float) -> dict:
    """The video with the voice (its own sound ducked under it, or none) and the captions burned in -> d/video.mp4,
    checked (H.264 + AAC, plays to the end)."""
    from . import auto_edit as ae, orders as od
    _CURRENT.update(step="video", progress=0.5)
    try:
        info = ae._probe(video)
    except Exception as exc:
        raise VoiceError("The video could not be read: " + str(exc)[:200])
    streams = info.get("streams", []) if isinstance(info, dict) else []
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not vs:
        raise VoiceError("This file has no picture: choose a video.")
    vlen = float((info.get("format") or {}).get("duration") or 0)
    if vlen <= 0:
        vlen = float(od._decode_info(video, timeout=1800).get("seconds") or 0)
    if vlen <= 0:
        raise VoiceError("The length of this video could not be read.")
    w, h = int(vs.get("width") or 1080), int(vs.get("height") or 1920)
    if int(info.get("rotation") or 0) in (90, 270):          # a phone video stored on its side: shown upright
        w, h = h, w
    voice_len = 0.0
    if voice_wav is not None:
        voice_len = float(od._decode_info(voice_wav, timeout=300).get("seconds") or 0)
    length = max(vlen, offset + voice_len + 0.5) if voice_wav is not None else vlen
    vf = []
    if length > vlen + 0.05:
        vf.append(f"tpad=stop_mode=clone:stop_duration={length - vlen:.3f}")
    if cs:
        (d / "captions.ass").write_text(ass(cs, w, h, offset=offset, position=position), "utf-8")
        (d / "captions.srt").write_text(srt(cs, offset=offset), "utf-8")
        vf.append("ass=captions.ass" + (":fontsdir=fonts" if _caption_font(d) else ""))
    if w % 2 or h % 2:                    # H.264 (4:2:0) needs an even width and height
        vf.insert(0, "scale=trunc(iw/2)*2:trunc(ih/2)*2")
        w, h = w // 2 * 2, h // 2 * 2
    vf.append("format=yuv420p")
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-i", str(video)]
    fc = [f"[0:v]{','.join(vf)}[v]"]
    if voice_wav is not None:
        cmd += ["-i", str(voice_wav)]
        ms = int(offset * 1000)
        fc.append(f"[1:a]adelay={ms}|{ms},apad=whole_dur={length:.3f},asplit=2[vo][sc]")
        if keep_sound and has_audio:
            fc.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={length:.3f},volume=-4dB[bg]")
            fc.append("[bg][sc]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[bgd]")
            fc.append("[bgd][vo]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        else:
            fc.append("[sc]anullsink;[vo]aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        amap = "[a]"
    else:
        amap = "0:a?" if keep_sound else None
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]"]
    if amap:
        cmd += ["-map", amap]
    cmd += ["-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "video.mp4"]
    log = d / "ffmpeg.log"
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        lf.write("$ " + " ".join(cmd) + "\n")
        lf.flush()
        cp = subprocess.run(cmd, cwd=str(d), stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            **process_kwargs(dict(timeout=6 * 3600)))
    shutil.rmtree(d / "fonts", ignore_errors=True)
    if cp.returncode != 0 or not (d / "video.mp4").is_file():
        tail = [x for x in log.read_text("utf-8", errors="replace").splitlines() if x.strip()][-1:] or ["?"]
        raise VoiceError("FFmpeg could not make the video (" + tail[0][:200] + ").")
    _CURRENT.update(step="checking", progress=0.9)
    with_sound = voice_wav is not None or (keep_sound and has_audio)
    checks = od._check_output(d / "video.mp4", {"seconds": length, "tolerance": 0.25, "audio": with_sound})
    if not all(c["pass"] for c in checks):
        bad = next(c for c in checks if not c["pass"])
        (d / "video.mp4").replace(d / "video_failed_check.mp4")
        raise VoiceError(f"The new video did not pass its check ({bad['check']}: {bad['detail']}).")
    saved = _save_copy(d / "video.mp4", video.stem, "voice" if voice_wav is not None else "captions")
    return {"files": {"video": "video.mp4", **({"srt": "captions.srt"} if cs else {})}, "seconds": round(length, 2),
            "checks": checks, "captions": len(cs), "width": w, "height": h, "saved": saved}


def _save_copy(src: Path, stem: str, what: str) -> str:
    """A copy next to the saved reels (Exports, or the folder used last), never over another file: '<name> - voice.mp4'."""
    from . import auto_edit as ae
    try:
        folder = ae.default_export_dir()
        folder.mkdir(parents=True, exist_ok=True)
        word = {"voice": "озвучка", "captions": "субтитры"}[what] if ae._ui_ru() else what
        base = ae.safe_filename(f"{stem[:60]} - {word}", "MediaEngine " + what)
        dst = folder / f"{base}.mp4"
        n = 2
        while dst.exists():
            dst = folder / f"{base} ({n}).mp4"
            n += 1
        shutil.copy2(src, dst)
        return str(dst)
    except Exception:
        return ""


def resume_after_restart() -> None:
    """Jobs left without an answer by a closed program are made again once (their files were not finished)."""
    if not installed():
        return
    for j in list_jobs(200):
        if j["state"] == "interrupted" and not j.get("resumed"):
            try:
                d = JOBS / j["id"]
                job = json.loads((d / "job.json").read_text("utf-8"))
                job["resumed"] = True
                (d / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=1), "utf-8")
                with _LOCK:
                    _QUEUE.append(j["id"])
            except Exception:
                pass
    if _QUEUE:
        with _LOCK:
            if not _THREAD or not _THREAD[0].is_alive():
                _THREAD[:] = [threading.Thread(target=_loop, name="voice-jobs", daemon=True)]
                _THREAD[0].start()


def retry_job(jid: str) -> None:
    """Make again a job that was interrupted (or failed): its own settings, its own folder."""
    j = read_job(jid)
    if j["state"] in ("working", "waiting"):
        return
    _need_addon()
    d = _job_dir(jid)
    with _LOCK:
        (d / "result.json").unlink(missing_ok=True)
        job = json.loads((d / "job.json").read_text("utf-8"))
        job["resumed"] = False
        (d / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=1), "utf-8")
        _QUEUE.append(jid)
        if not _THREAD or not _THREAD[0].is_alive():
            _THREAD[:] = [threading.Thread(target=_loop, name="voice-jobs", daemon=True)]
            _THREAD[0].start()
    _WAKE.set()


def delete_job(jid: str) -> None:
    d = _job_dir(jid)
    if _CURRENT.get("id") == jid:
        raise VoiceError("This one is being made now.")
    with _LOCK:
        if jid in _QUEUE:
            _QUEUE.remove(jid)
    shutil.rmtree(d, ignore_errors=True)

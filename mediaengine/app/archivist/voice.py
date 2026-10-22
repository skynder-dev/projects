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

from . import textfx as tf
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
# The owner's pick (2026-10-21, voice lab round 14: "14_5" over the program's VoxCPM2 voice and CosyVoice3 /
# Chatterbox): Qwen3-TTS 1.7B Base (Alibaba, Apache-2.0) cloning 9_2's recording. It says every voice cloned from a
# recording (the ready 9_2, saved voices, a recording) in the languages it knows; VoxCPM2 stays for a voice from a
# description (and languages Qwen3-TTS does not speak). Its own folder of packages, put first for its worker: exactly
# the distributions it imported on Windows (engine probe run 39601510428) that the main folder does not have in the
# same version (transformers 4.57.3 there, 5.20.1 here); torch, numpy, librosa ... come from the main folder. Its
# 'sox' (imported by its 25 Hz tokenizer, never used by the 12 Hz model) has no wheel: a stub stands in (_SOX_STUB).
QWEN_VERSION = 1
SITE_QWEN = ROOT / "site_qwen"
QWEN_REPO, QWEN_REV = "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "fd4b254389122332181a7c3db7f27e918eec64e3"   # 4.54 GB
QWEN_PACKAGES = [
    "accelerate==1.12.0", "filelock==3.32.3", "huggingface-hub==0.36.2", "narwhals==2.27.1", "opentelemetry-api==1.45.1",
    "pandas==3.0.6", "protobuf==7.36.2", "psutil==7.2.2", "python-dateutil==2.9.0.post0", "pytz==2026.5",
    "qwen-tts==0.1.1", "rich==15.0.0", "scikit-learn==1.9.1", "six==1.17.0", "threadpoolctl==3.7.0",
    "tokenizers==0.22.2", "transformers==4.57.3",
]
# the languages it speaks (the form's codes -> its names; '' = it finds out by itself)
QWEN_LANGS = {"": None, "en": "English", "ru": "Russian", "de": "German", "fr": "French", "es": "Spanish",
              "it": "Italian", "pt": "Portuguese", "zh": "Chinese", "ja": "Japanese", "ko": "Korean"}
_SOX_STUB = ('"""Stand-in for the \'sox\' package (no wheel): Qwen3-TTS imports it for its 25 Hz tokenizer, which the 12 Hz '
             'model never uses."""\n\n\nclass Transformer:\n    def __init__(self, *a, **k):\n        raise RuntimeError('
             '"SoX is not part of MediaEngine\'s voice add-on")\n')
NEED_FREE = 26 * 10 ** 9            # packages (2.8 GB with CPU torch, ~5 GB with CUDA) + models (10 GB) + room
NEED_FREE_QWEN = 8 * 10 ** 9        # the new engine alone: its packages (~0.2 GB) + its model (4.5 GB) + room
MAX_TEXT = 5000

_LOCK = threading.Lock()
INSTALL = {"state": "idle", "step": "", "done": 0, "total": 0, "error": "", "detail": "", "started": 0.0, "mode": "full"}
_STOP = threading.Event()
_QUEUE: list[str] = []
_CURRENT: dict = {}
_WAKE = threading.Event()
_THREAD: list[threading.Thread] = []

# The owner's pick from the voice lab (2026-10-20 18:03 / 18:16): 9_2 - "a cleaner voice, not bad" (9_3 was better but
# "lisping" on s / sh / ch, which a de-esser did not cure; 4_4 "robot in the lows", 4_2 "squeaky", 3.1 "sounds like
# sex"). Its very take (voice lab round 9, r9_design_t11: 4_2's recipe with another seed) ships with the program (FLAC)
# and every voice-over in it is that same voice: since 2026-10-21 said by Qwen3-TTS from the recording and its exact
# words (his pick 14_5 - "livelier" than VoxCPM2's ultimate cloning, which stays when Qwen3-TTS is not there yet);
# each piece kept near its pitch by the worker. The recording says this text:
HOST_REF_TEXT = ("Here's what you need to know this week. First, flights to Europe got almost twenty percent cheaper. "
                 "Second, if you book before Friday, most airlines let you change the dates for free. "
                 "And third, the best deals are on Tuesday and Wednesday. Save this, and send it to someone who's planning a trip.")
VOICES = {
    # cfg 1.6 (the setting 9_2 itself was made with): "a little more pleasant" than 2.0 (voice lab round 13, 23:39)
    "host_9_2": {"label": "Host - the voice of 9_2", "ref": "host_9_2.flac", "ref_text": HOST_REF_TEXT, "cfg": 1.6},
    "describe": {"label": "My description of a voice (English works best)"},
    "own": {"label": "A voice from a recording (a person who agreed to it)"},
}
DEFAULT_VOICE = "host_9_2"
# Finishing: loudness only. A "microphone" finishing (roll-off, saturation, small room, compression) was tried and
# dropped - the owner heard no difference (round 5, 2026-10-19: "what the hell is the difference between 5_1 and 5_2");
# shifting the finished voice's pitch was rejected outright ("as if drowned in a toilet") - never done here.


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


_QWEN_LATIN = set("ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝàáâãäåæçèéêëìíîïñòóôõöøùúûüýÿßŒœ")


def qwen_can_say(text: str) -> bool:
    """With the language left to be found: every letter is one of Qwen3-TTS's ten languages (English, German, French,
    Spanish, Italian, Portuguese with their accents; Russian Cyrillic - no і ї є ґ ў; Chinese, Japanese, Korean).
    Ukrainian, Polish, Czech, Turkish ... text goes to VoxCPM2."""
    for ch in str(text or ""):
        if not ch.isalpha():
            continue
        o = ord(ch)
        if ch.isascii() or ch in _QWEN_LATIN or 0x410 <= o <= 0x44F or ch in "Ёё" or 0x4E00 <= o <= 0x9FFF \
                or 0x3040 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF or 0x3400 <= o <= 0x4DBF:
            continue
        return False
    return True


def _script(text: str) -> str:
    """The writing a text is mostly in: 'cyr', 'lat', 'cjk' ('' without letters)."""
    n = {"cyr": 0, "lat": 0, "cjk": 0}
    for ch in str(text or ""):
        if not ch.isalpha():
            continue
        o = ord(ch)
        n["cyr" if 0x400 <= o <= 0x4FF else "lat" if o < 0x250 else "cjk"] += 1
    best = max(n, key=n.get)
    return best if n[best] else ""


def qwen_icl(text: str, ref_text: str) -> bool:
    """Qwen3-TTS continues the voice's recording and its words only in the same writing as those words; otherwise it
    takes the voice's timbre alone. Voice lab round 15 (run 39696944139): 9_2's English recording continued in Russian
    carried the English accent (14 of 82 words heard wrong, "голоса" as "Галлесса"); the timbre alone 7 of 82."""
    return bool(ref_text) and _script(text) == _script(ref_text)


def qwen_installed() -> bool:
    """The engine of the voices cloned from a recording (Qwen3-TTS) is there, beside an installed add-on."""
    q = manifest().get("qwen") or {}
    return bool(installed() and q.get("version") == QWEN_VERSION and SITE_QWEN.is_dir() and (MODELS / "qwen3tts").is_dir())


def status() -> dict:
    m = manifest()
    s = dict(INSTALL)
    s.update(installed=installed(), qwen=qwen_installed(), manifest=m,
             needs_reinstall=bool(m) and not installed() and s["state"] != "running",
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
        if installed() and qwen_installed() and not cpu:
            raise VoiceError("The voice add-on is already installed.")
        if busy():
            raise VoiceError("A voice-over is being made. Install when it is ready.")
        INSTALL.update(state="running", step="checking", done=0, total=0, error="", detail="", started=time.time(),
                       mode="full" if cpu or not installed() else "engine")
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


def _pip(site_dir: Path, cpu: bool, log: Path, packages: list[str] | None = None) -> None:
    from . import auto_edit as ae
    tmp = ROOT / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    cmd = [_python(), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "--no-input",
           "--progress-bar", "off", "--no-cache-dir", "--only-binary", ":all:", "--no-deps", "--target", str(site_dir),
           "--index-url", "https://pypi.org/simple"]
    if not cpu:
        cmd += ["--extra-index-url", CUDA_INDEX_NEW if re.search(r"RTX\s*50\d0", _nvidia_name(), re.I) else CUDA_INDEX]
    cmd += list(packages or PACKAGES)
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
    log = ROOT / "install.log"
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        core = cpu or not installed()           # the main part (VoxCPM2, Whisper, torch) - kept when it is there
        INSTALL.update(mode="full" if core else "engine")
        if _free(ROOT) < (NEED_FREE if core else NEED_FREE_QWEN):
            raise VoiceError("Not enough free space on the disk of the data folder: the voice add-on needs about "
                             + ("26" if core else "8") + " GB free.")
        if core:                                # whole and working first: a failure of the new engine keeps it
            _install_core(cpu, log)
        _install_qwen(log)
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


def _models(parts: list[tuple[str, str, str]]) -> None:
    """The models' files at their pinned commits into MODELS/<key>.__install__ (a file already there, or in the
    installed model, is kept, not downloaded again), then each folder put in place of the old one."""
    from . import auto_edit as ae
    files = []
    for key, repo, rev in parts:
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
    for key, _repo, _rev in parts:
        fin = MODELS / key
        if fin.exists():
            shutil.rmtree(fin, ignore_errors=True)
        ae._replace_retry(MODELS / (key + ".__install__"), fin, tries=30)


def _swap(new: Path, final: Path) -> None:
    """A freshly installed package folder in place of the old one (the old one back if that fails)."""
    from . import auto_edit as ae
    old = None
    if final.exists():
        old = ROOT / f"{final.name}.__old__{int(time.time())}"
        ae._replace_retry(final, old, tries=30)
    try:
        ae._replace_retry(new, final, tries=30)
    except Exception:
        if old is not None and not final.exists():
            ae._replace_retry(old, final, tries=30)          # the add-on as it was
        raise
    if old is not None:
        shutil.rmtree(old, ignore_errors=True)


def _install_core(cpu: bool, log: Path) -> None:
    """The add-on's main part: its packages (torch, VoxCPM2, faster-whisper), VoxCPM2 and Whisper - checked and
    recorded on its own (installed() from here on)."""
    gpu = "" if cpu else _nvidia_name()
    new_site = ROOT / "site.__install__"
    if new_site.exists():
        shutil.rmtree(new_site, ignore_errors=True)
    INSTALL.update(step="packages", detail="")
    _pip(new_site, cpu or not gpu, log)
    INSTALL.update(step="models", detail="")
    _models([("voxcpm", VOXCPM_REPO, VOXCPM_REV), ("whisper", WHISPER_REPO, WHISPER_REV)])
    INSTALL.update(step="checking_addon", detail="")
    _swap(new_site, SITE)
    test = _run_worker({"task": "selftest"}, ROOT / "selftest", timeout=600)
    if not test.get("ok"):
        raise VoiceError("The voice add-on was installed but does not start: " + str(test.get("error") or "")[:300])
    m = {"version": ADDON_VERSION, "python": f"{sys.version_info[0]}.{sys.version_info[1]}", "packages": PACKAGES,
         "torch": test.get("torch"), "cuda": bool(test.get("cuda")), "gpu": test.get("gpu") or "",
         "vram_gb": test.get("vram_gb") or 0, "models": {"voxcpm": [VOXCPM_REPO, VOXCPM_REV],
                                                         "whisper": [WHISPER_REPO, WHISPER_REV]},
         "installed_at": now_iso(), "bytes": _tree_bytes(ROOT)}
    _write_manifest(m)


def _install_qwen(log: Path) -> None:
    """The new engine beside an installed main part: its packages (no torch: from the main part - so never the CUDA
    index), its 'sox' stand-in, its model; checked, then added to the add-on's record."""
    m = manifest()
    if not m.get("version"):
        raise VoiceError("The voice add-on's record could not be read. Try again.")
    if _free(ROOT) < NEED_FREE_QWEN:
        raise VoiceError("Not enough free space on the disk of the data folder: the voice add-on needs about 8 GB free.")
    new_qsite = ROOT / "site_qwen.__install__"
    if new_qsite.exists():
        shutil.rmtree(new_qsite, ignore_errors=True)
    INSTALL.update(step="qwen_packages", detail="", total=0, done=0)
    _pip(new_qsite, True, log, QWEN_PACKAGES)
    (new_qsite / "sox").mkdir(parents=True, exist_ok=True)
    (new_qsite / "sox" / "__init__.py").write_text(_SOX_STUB, "utf-8")
    INSTALL.update(step="qwen_models", detail="")
    _models([("qwen3tts", QWEN_REPO, QWEN_REV)])
    INSTALL.update(step="checking_addon", detail="")
    _swap(new_qsite, SITE_QWEN)
    test = _run_worker({"task": "selftest", "engine": "qwen"}, ROOT / "selftest", timeout=600)
    if not test.get("ok"):
        raise VoiceError("The new voice engine was installed but does not start: " + str(test.get("error") or "")[:300])
    m["qwen"] = {"version": QWEN_VERSION, "packages": QWEN_PACKAGES, "model": [QWEN_REPO, QWEN_REV],
                 "qwen_tts": test.get("qwen_tts"), "installed_at": now_iso()}
    m["bytes"] = _tree_bytes(ROOT)
    _write_manifest(m)


def _write_manifest(m: dict) -> None:
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, indent=1), "utf-8")
    os.replace(tmp, MANIFEST)


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
    for name in ("site", "site_qwen", "models", "site.__install__", "site_qwen.__install__", "tmp", "selftest"):
        shutil.rmtree(ROOT / name, ignore_errors=True)
    for old in list(ROOT.glob("site.__old__*")) + list(ROOT.glob("site_qwen.__old__*")):
        shutil.rmtree(old, ignore_errors=True)
    MANIFEST.unlink(missing_ok=True)
    INSTALL.update(state="idle", step="", error="", detail="", done=0, total=0)


# ---------------------------------------------------------------- the worker process

def _run_worker(job: dict, work: Path, timeout: float = 3600, on_line=None) -> dict:
    from . import auto_edit as ae
    work.mkdir(parents=True, exist_ok=True)
    job = dict(job, site=str(SITE), model_dir=str(MODELS / "voxcpm"), whisper_dir=str(MODELS / "whisper"),
               site_qwen=str(SITE_QWEN), qwen_dir=str(MODELS / "qwen3tts"), work_dir=str(work))
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

# How fast the voice speaks and how long it breathes between sentences (the model has one pace of its own): the
# finished voice is made a little faster or slower by FFmpeg's atempo - the pitch stays (never a shifted voice: the owner
# heard one "as if drowned in a toilet") - and the pauses between the model's pieces are made shorter or longer.
# The captions follow (the words' times are scaled with the voice).
SPEEDS = {"slower": 0.92, "normal": 1.0, "faster": 1.08, "fastest": 1.15}
PAUSES = {"short": 0.6, "normal": 1.0, "long": 1.6}


def pace(speed: str = "", pauses: str = "") -> tuple[str, str]:
    """The chosen speed and pauses, each one of the known choices (anything else: normal)."""
    return (speed if speed in SPEEDS else "normal"), (pauses if pauses in PAUSES else "normal")


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
    toks = [t for t in re.split(r"\s+", str(script or "")) if _norm(t)]      # words in brackets are said too
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


def ass(cs: list[dict], width: int, height: int, offset: float = 0.0, position: str = "bottom", style: str | None = None,
        texts: list[dict] | None = None, color: str | None = None, size: str | None = None) -> str:
    """Captions (and text blocks) for burning in, in one of the styles of textfx (Montserrat, shipped)."""
    return tf.document(width, height, cs, texts, tf.options(style, color, size, position), offset)


def style_cues(words: list[dict], opts: dict | None) -> list[dict]:
    """The words grouped into captions the way the style shows them (fewer words for big capitals)."""
    st = tf.STYLES[tf.options(**(opts or {}))["style"]]
    return cues(words, max_words=st["words"])


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
    out.sort(key=lambda j: (j["id"][:15], int(j.get("created_ns") or 0)), reverse=True)   # newest first, exactly
    return out


def busy() -> str:
    """The voice-over job running now or waiting ('' when none): Quit / Restart / switching builds ask first."""
    return str(_CURRENT.get("id") or (_QUEUE[0] if _QUEUE else "") or ("install" if installing() else ""))


def _new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def _need_addon() -> None:
    if not installed():
        raise VoiceError("Install the voice add-on first.")


_LAST_NS = [0]


def _write_job(d: Path, job: dict) -> None:
    """job.json replaced in one step: a page reading the list at that moment never sees half a file."""
    tmp = d / f"job.json.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1), "utf-8")
    for i in range(20):                 # Windows: a reader holding the file a moment
        try:
            os.replace(tmp, d / "job.json")
            return
        except PermissionError:
            time.sleep(0.05 * (i + 1))
    os.replace(tmp, d / "job.json")


def _submit(job: dict, addon: bool = True) -> str:
    if addon:
        _need_addon()
        if installing():
            raise VoiceError("The voice add-on is being installed. Wait until it is ready.")
    with _LOCK:                         # named, written and queued in one step: a page never sees it "interrupted",
        jid = _new_id()                 # and the order within one second too is strictly increasing (Windows' clock
        d = JOBS / jid                  # can give two jobs made one after the other the same reading)
        d.mkdir(parents=True, exist_ok=True)
        ns = max(time.time_ns(), _LAST_NS[0] + 1)
        _LAST_NS[0] = ns
        job = dict(job, id=jid, created_at=now_iso(), created_ns=ns)
        _write_job(d, job)
        _QUEUE.append(jid)
        if not _THREAD or not _THREAD[0].is_alive():
            _THREAD[:] = [threading.Thread(target=_loop, name="voice-jobs", daemon=True)]
            _THREAD[0].start()
    _WAKE.set()
    return jid


MY_VOICES = HOME / "voices"
MY_MAX = 20


def my_voices() -> dict:
    """Voices saved from recordings (of people who agreed to it; "my_<id>"): the recording (a clean mono WAV of at most 30 s) and,
    when given, its exact words. Newest last."""
    out = {}
    try:
        dirs = sorted((d for d in MY_VOICES.iterdir() if d.is_dir() and (d / "voice.wav").is_file()), key=lambda d: d.name)
    except OSError:
        dirs = []
    for d in dirs:
        try:
            meta = json.loads((d / "voice.json").read_text("utf-8"))
        except Exception:
            meta = {}
        out["my_" + d.name] = {"label": str(meta.get("name") or d.name)[:60], "ref_path": str(d / "voice.wav"),
                               "ref_text": str(meta.get("ref_text") or ""), "mine": True}
    return out


def all_voices() -> dict:
    """The ready voices, then my saved ones, then a voice from a description or from a recording."""
    ready = {k: v for k, v in VOICES.items() if v.get("ref")}
    return {**ready, **my_voices(), **{k: v for k, v in VOICES.items() if not v.get("ref")}}


def save_my_voice(source: str, name: str, ref_text: str = "") -> str:
    """A recording kept as one of my voices (converted once: mono, 24 kHz, at most 30 s); returns its key."""
    p = Path(str(source or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the recording of the voice (a WAV, MP3 or M4A of 5-30 seconds of one person speaking).")
    name = " ".join(tf.clean_text(name, 60).split())
    if not name:
        raise VoiceError("Give the voice a name.")
    if len(my_voices()) >= MY_MAX:
        raise VoiceError("There are already 20 saved voices: delete one first.")
    vid = _new_id()
    d = MY_VOICES / vid
    d.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(p), "-t", "30", "-ac", "1",
                         "-ar", "24000", str(d / "voice.wav")], **process_kwargs(dict(capture_output=True, timeout=120)))
    if cp.returncode != 0 or not (d / "voice.wav").is_file() or (d / "voice.wav").stat().st_size < 24000 * 2 * 3:
        shutil.rmtree(d, ignore_errors=True)
        raise VoiceError("The recording of the voice could not be read (it needs at least a few seconds of speech).")
    (d / "voice.json").write_text(json.dumps({"name": name, "ref_text": re.sub(r"\s+", " ", str(ref_text or "")).strip()[:1000],
                                              "source": p.name, "created_at": now_iso()}, ensure_ascii=False), "utf-8")
    return "my_" + vid


def delete_my_voice(key: str) -> None:
    if not re.fullmatch(r"my_\d{8}-\d{6}-[0-9a-f]{6}", str(key or "")):
        raise VoiceError("No such voice.")
    shutil.rmtree(MY_VOICES / key[3:], ignore_errors=True)


def new_voiceover(text: str, voice: str, description: str = "", ref_path: str = "", ref_text: str = "",
                  language: str = "", save_as: str = "", speed: str = "", pauses: str = "") -> str:
    _need_addon()
    text = str(text or "").strip()
    if not text:
        raise VoiceError("Type the text of the voice-over first.")
    if len(text) > MAX_TEXT:
        raise VoiceError("The text is too long for one voice-over (at most 5000 characters): split it into parts.")
    if voice == "own" and str(save_as or "").strip():          # the recording kept as one of my voices, then used
        voice = save_my_voice(ref_path, save_as, ref_text)
    voices = all_voices()
    if voice not in voices:
        raise VoiceError("Choose a voice.")
    v: dict = {"key": voice}
    if voices[voice].get("ref") or voices[voice].get("ref_path"):
        pv = voices[voice]
        ref = ASSETS / pv["ref"] if pv.get("ref") else Path(pv["ref_path"])
        if not ref.is_file():
            raise VoiceError("The recording of this voice is missing from this version of MediaEngine.")
        v.update(ref_wav=str(ref))
        if pv.get("ref_text"):                # its recording continued (ultimate cloning) - or, without, the timbre only
            v["ref_text"] = pv["ref_text"]
        if pv.get("style"):                   # the timbre + a note on the manner (controllable cloning)
            v["style"] = pv["style"]
        if pv.get("cfg"):
            v["cfg"] = float(pv["cfg"])
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
    sk, pk = pace(speed, pauses)
    try:                                           # the next form starts with this voice, speed and pauses
        from .config import update_config
        update_config(lambda c: c.setdefault("voice", {}).update(last=voice, speed=sk, pauses=pk))
    except Exception:
        pass
    return _submit({"kind": "voiceover", "text": text, "voice": v, "language": lang or None,
                    "speed": SPEEDS[sk], "pauses": PAUSES[pk], "pace": [sk, pk],
                    "title": re.sub(r"\s+", " ", text)[:60]})


def new_captions(source: str, language: str = "", position: str = "bottom", opts: dict | None = None,
                 texts: list[dict] | None = None) -> str:
    _need_addon()
    p = Path(str(source or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose a video (its full path) to make captions for.")
    _check_video(p, need_sound=True)                  # a video with sound, said now rather than after listening
    o = tf.options(**{**(opts or {}), "position": position if position in tf.POSITIONS else (opts or {}).get("position")})
    return _submit({"kind": "captions", "source": str(p), "language": (language or "").strip().lower()[:2] or None,
                    "position": o["position"], "opts": o, "texts": list(texts or []), "title": p.name[:60]})


def new_dub(jid: str, video: str, keep_sound: bool = True, captions: bool = True, position: str = "bottom",
            start_s: float = 0.3, opts: dict | None = None, texts: list[dict] | None = None) -> str:
    """The voice-over `jid` onto a video: a new MP4 (the video itself is only read)."""
    _need_addon()
    src = read_job(jid)
    if not (src.get("result") or {}).get("ok") or src.get("kind") != "voiceover":
        raise VoiceError("This voice-over is not ready.")
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the video (its full path).")
    _check_video(p)
    try:
        start_s = max(0.0, min(60.0, float(str(start_s).strip().replace(",", ".") or 0.3)))
    except (TypeError, ValueError):
        raise VoiceError("The start of the voice must be a number of seconds, for example 0.5.")
    o = tf.options(**{**(opts or {}), "position": position if position in tf.POSITIONS else (opts or {}).get("position")})
    return _submit({"kind": "dub", "voiceover": jid, "video": str(p), "keep_sound": bool(keep_sound),
                    "captions": bool(captions), "position": o["position"], "opts": o, "texts": list(texts or []),
                    "start_s": start_s, "title": p.name[:60]})


def _clean_cues(raw) -> list[dict]:
    """Captions sent back by the editor: numbers and words only, in time order, never overlapping."""
    out = []
    import math
    for c in (raw or [])[:3000]:
        try:
            words = [{"w": tf.clean_text(w.get("w"), 60).replace("*", ""), "s": float(w["s"]), "e": float(w["e"]),
                      **({"em": True} if w.get("em") is True else {})} for w in c.get("words") or []]
            float(c.get("e") or 0)
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
            continue
        words = [w for w in words if w["w"] and -60 <= w["s"] <= w["e"] < 36000 and math.isfinite(w["e"])]
        if words:
            s0 = min(w["s"] for w in words)
            ce = float(c.get("e") or 0)
            e0 = max(ce if math.isfinite(ce) and ce < 36000 else 0, max(w["e"] for w in words))
            out.append({"s": s0, "e": e0, "words": words})
    out.sort(key=lambda c: c["s"])
    for i in range(len(out) - 1):                      # a caption ends before the next one starts (no stacking)
        out[i]["e"] = max(out[i]["s"] + 0.05, min(out[i]["e"], out[i + 1]["s"] - 0.01))
    return out


def new_render(video: str, cues_: list[dict] | None = None, opts: dict | None = None, texts: list[dict] | None = None,
               voice_from: str = "", start_s: float = 0.0, keep_sound: bool = True, title: str = "",
               captions_on: bool = True, music: str = "", music_level: str = "medium") -> str:
    """A video with text and/or (edited) captions, and the voice of a made voice-over if any: no add-on needed (nothing
    is spoken or listened to - the words and their times are already there)."""
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the video (its full path).")
    if voice_from:
        src = read_job(voice_from)
        if src.get("kind") != "voiceover" or not (_job_dir(voice_from) / "voice.wav").is_file():
            raise VoiceError("This voice-over is not ready.")
    cs = _clean_cues(cues_)
    tx = list(texts or [])
    if not (cs and captions_on) and not tx and not voice_from and not music:
        raise VoiceError("Add a text (or captions) first.")
    start_s = max(0.0, min(60.0, float(start_s or 0)))
    late = [t for t in tx if t.get("start") is not None and not t.get("at_end")]
    if late:                                   # a text after the end would be left out without a word
        from . import orders as od
        length = video_size(p)[2]
        if voice_from:
            length = max(length, start_s + float(od._decode_info(_job_dir(voice_from) / "voice.wav", timeout=300)
                                                 .get("seconds") or 0) + 0.5)
        if any(float(t["start"]) >= length - 0.2 for t in late):
            raise VoiceError(f"A text starts after the end of the video (the video is {length:.1f} s long).")
    music = _check_music(music)
    return _submit({"kind": "render", "video": str(p), "cues": cs, "captions_on": bool(captions_on),
                    "opts": tf.options(**(opts or {})), "texts": tx, "voice_from": voice_from or "",
                    "start_s": start_s, "keep_sound": bool(keep_sound), "music": music,
                    "music_level": music_level if music_level in ("quiet", "medium", "loud") else "medium",
                    "title": (title or p.name)[:60]}, addon=False)


def _finish_shared(voice: str = "none", voice_from: str = "", captions: str = "none", texts: list[dict] | None = None,
                   start_s=0.3, music: str = "", music_level: str = "medium", script: str = "") -> dict:
    """The choices that are the same for every video, checked once (nothing made yet; a new voice-over is made by the
    caller)."""
    voice = voice if voice in ("none", "made", "new") else "none"
    captions = captions if captions in ("none", "voice", "speech") else "none"
    try:
        start = max(0.0, min(60.0, float(str(start_s).strip().replace(",", ".") or 0.3)))
    except (TypeError, ValueError):
        raise VoiceError("The start of the voice must be a number of seconds, for example 0.5.")
    voice_seconds = 0.0
    if voice == "made":
        if not voice_from:
            raise VoiceError("Choose the voice-over.")
        voiceover_words(voice_from)                     # ready, with its words (or said in words)
    elif voice != "new":
        voice_from, start = "", 0.0                     # no voice: no start to wait for
    if captions == "voice" and voice == "none":
        raise VoiceError("Captions of the voice need a voice: choose one, or captions of the video's speech.")
    if captions == "speech" or voice == "new":
        _need_addon()
        if installing():
            raise VoiceError("The voice add-on is being installed. Wait until it is ready.")
    tx = list(texts or [])
    music = _check_music(music)
    script = str(script or "").strip()[:MAX_TEXT] if captions == "speech" else ""
    if voice == "none" and captions == "none" and not tx and not music:
        raise VoiceError("Add a text, captions, a voice or music first.")
    timed = voice != "new" and any(t.get("start") is not None and not t.get("at_end") for t in tx)
    if timed and voice_from:                            # a text may run on while the voice still speaks
        from . import orders as od
        voice_seconds = float(od._decode_info(_job_dir(voice_from) / "voice.wav", timeout=300).get("seconds") or 0)
    return {"voice": voice, "voice_from": voice_from or "", "captions": captions, "start": start, "texts": tx,
            "music": music, "music_level": music_level if music_level in ("quiet", "medium", "loud") else "medium",
            "script": script, "timed": timed, "voice_seconds": voice_seconds}


def _finish_video(video: str, sh: dict, opts: dict | None, keep_sound: bool) -> dict:
    """One video's job with the shared choices: the video itself checked (a picture; sound for captions of its
    speech; every timed text inside it)."""
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the video (its full path).")
    if sh["captions"] == "speech":
        _check_video(p, need_sound=True)
    length = video_size(p)[2]                           # a picture to put things on (and its length)
    if sh["timed"]:
        if sh["voice_from"]:
            length = max(length, sh["start"] + sh["voice_seconds"] + 0.5)
        tx = sh["texts"]
        if any(float(t["start"]) >= length - 0.2 for t in tx if t.get("start") is not None and not t.get("at_end")):
            raise VoiceError(f"A text starts after the end of the video (the video is {length:.1f} s long).")
    return {"kind": "render", "video": str(p), "cues": [], "captions_on": sh["captions"] in ("voice", "speech"),
            "captions_from": sh["captions"] if sh["captions"] in ("voice", "speech") else None,
            "needs_addon": sh["captions"] == "speech", "opts": tf.options(**(opts or {})), "texts": sh["texts"],
            "voice_from": sh["voice_from"], "start_s": sh["start"], "keep_sound": bool(keep_sound),
            "music": sh["music"], "music_level": sh["music_level"], "script": sh["script"], "title": p.name[:60]}


def _check_video(p: Path, need_sound: bool = False) -> None:
    """A file with a picture (and sound, for captions of its speech) - said before a job is made of it."""
    from . import auto_edit as ae
    try:
        info = ae._probe(p)
    except Exception as exc:
        raise VoiceError("The video could not be read: " + str(exc)[:200])
    streams = info.get("streams", []) if isinstance(info, dict) else []
    if not any(x.get("codec_type") == "video" for x in streams):
        raise VoiceError("This file has no picture: choose a video.")
    if need_sound and not any(x.get("codec_type") == "audio" for x in streams):
        raise VoiceError("This video has no sound, so there is no speech to make captions of.")


def _new_voice_for(nv: dict | None) -> str:
    nv = nv or {}
    return new_voiceover(nv.get("text", ""), nv.get("voice", ""), nv.get("description", ""),
                         nv.get("ref_path", ""), nv.get("ref_text", ""), nv.get("language", ""),
                         speed=nv.get("speed", ""), pauses=nv.get("pauses", ""))


def new_finish(video: str, voice: str = "none", voice_from: str = "", new_voice: dict | None = None,
               captions: str = "none", opts: dict | None = None, texts: list[dict] | None = None, start_s=0.3,
               keep_sound: bool = True, music: str = "", music_level: str = "medium", script: str = "") -> str:
    """Everything for one video in one go: a voice (none / a voice-over made already / a new one, made first), captions
    (none / the voice's words / the video's own speech, heard when the video is made), a look and texts. A new voice
    and captions of the speech need the add-on; the rest does not."""
    if not Path(str(video or "").strip().strip('"')).is_file():
        raise VoiceError("Choose the video (its full path).")
    sh = _finish_shared(voice, voice_from, captions, texts, start_s, music, music_level, script)
    job = _finish_video(video, sh, opts, keep_sound)
    if sh["voice"] == "new":                              # made first: the jobs run one after another, in order
        job["voice_from"] = _new_voice_for(new_voice)
    return _submit(job, addon=False)


FINISH_MANY_MAX = 30


def _same_file_key(v: str) -> str:
    return os.path.normcase(os.path.abspath(v))


def new_finish_many(videos: list[str], voice: str = "none", voice_from: str = "", new_voice: dict | None = None,
                    captions: str = "none", opts: dict | None = None, texts: list[dict] | None = None, start_s=0.3,
                    keep_sound: bool = True, music: str = "", music_level: str = "medium", script: str = "") -> list[str]:
    """Several videos finished the same way (the same voice, captions, look, texts and music): the shared choices and
    then every video are checked first - nothing is made unless all of them can be - then one job per video, in order.
    A new voice-over is made once and put on each of them. Captions of the speech are each video's own speech; the
    exact text of a speech is for one video only."""
    paths, seen = [], set()
    for v in videos or []:
        v = str(v or "").strip().strip('"')
        if v and _same_file_key(v) not in seen:         # the same file written two ways counts once
            seen.add(_same_file_key(v))
            paths.append(v)
    if not paths:
        raise VoiceError("Choose the video (its full path).")
    if len(paths) > FINISH_MANY_MAX:
        raise VoiceError(f"At most {FINISH_MANY_MAX} videos at once: split them into groups.")
    if len(paths) == 1:
        return [new_finish(paths[0], voice, voice_from, new_voice, captions, opts, texts, start_s, keep_sound,
                           music, music_level, script)]
    if captions == "speech" and str(script or "").strip():
        raise VoiceError("The exact text of the speech is for one video: clear it, or finish the videos one by one.")
    for v in paths:
        if not Path(v).is_file():
            raise VoiceError(f"This video is not there: {v}")
    sh = _finish_shared(voice, voice_from, captions, texts, start_s, music, music_level, "")
    jobs = []
    for v in paths:
        try:
            jobs.append(_finish_video(v, sh, opts, keep_sound))
        except VoiceError as exc:
            raise VoiceError(f"{exc} ({Path(v).name})")
    if sh["voice"] == "new":                              # one new voice-over, made first, on every video
        vf = _new_voice_for(new_voice)
        for j in jobs:
            j["voice_from"] = vf
    return [_submit(j, addon=False) for j in jobs]


MUSIC_EXT = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma"}


def _check_music(music: str) -> str:
    """A song under the video: a sound file that really plays (its first second decodes), or '' for none."""
    m = str(music or "").strip().strip('"')
    if not m:
        return ""
    p = Path(m)
    if not p.is_file():
        raise VoiceError("Choose the music file (its full path).")
    if p.suffix.lower() not in MUSIC_EXT:
        raise VoiceError("The music must be a sound file (MP3, M4A, WAV, FLAC, OGG).")
    cp = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(p), "-map", "0:a:0", "-t", "1", "-ac", "1", "-ar", "8000",
                         "-f", "s16le", "-"], capture_output=True, **process_kwargs(dict(timeout=120)))
    if cp.returncode != 0 or len(cp.stdout) < 800:
        raise VoiceError("This music file has no sound that can be played.")
    return str(p)


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
        if _CURRENT.get("cancel"):
            res = {"ok": False, "error": "Stopped."}
        if res.get("_requeue"):                          # behind the job it waits for (no result written)
            with _LOCK:
                if _QUEUE and _QUEUE[0] == jid:
                    _QUEUE.pop(0)
                    _QUEUE.append(jid)
            _CURRENT.clear()
            continue
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
        elif v.get("ref_wav"):                       # a voice of the program: its file in THIS build (a job made by an
            pv = all_voices().get(v.get("key")) or {}       # older build keeps that build's path, maybe removed since)
            if pv.get("ref"):
                v["ref_wav"] = str(ASSETS / pv["ref"])
            if not Path(v["ref_wav"]).is_file():     # a voice this version no longer has (3.1), or a saved voice deleted
                return {"ok": False, "error": "The recording of this voice is no longer there (a saved voice deleted, "
                                              "or a voice this version of MediaEngine does not have)."}
        cfg = (load_config().get("voice") or {})
        device = cfg.get("device") or ("cuda" if manifest().get("cuda") else "cpu")
        lang = str(job.get("language") or "")
        engine = ("qwen" if v.get("ref_wav") and lang in QWEN_LANGS and (lang or qwen_can_say(job["text"]))
                  and qwen_installed() else "voxcpm")
        pf = min(2.0, max(0.3, float(job.get("pauses") or 1.0)))
        pieces = [dict(c, pause_after=round(float(c["pause_after"]) * pf, 3)) for c in chunks(job["text"].replace("*", ""))]
        res = _run_worker({"task": "tts", "chunks": pieces, "voice": v, "language": job.get("language"),
                           "out_wav": str(d / "voice_raw.wav"), "seed": int(cfg.get("seed") or 1),
                           "steps": cfg.get("steps"), "device": device, "cfg": v.get("cfg") or cfg.get("cfg"),
                           "engine": engine, "qwen_language": QWEN_LANGS.get(lang),
                           "qwen_icl": qwen_icl(job["text"], v.get("ref_text") or "")},
                          d / "work", timeout=6 * 3600,
                          on_line=_progress)
        if not res.get("ok"):
            return res
        _CURRENT.update(step="finishing", progress=0.97)
        sp = min(1.25, max(0.8, float(job.get("speed") or 1.0)))
        sp = 1.0 if abs(sp - 1.0) < 0.001 else sp
        cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(d / "voice_raw.wav"),
                             "-af", (f"atempo={sp:.3f}," if sp != 1.0 else "") + "loudnorm=I=-16:TP=-1.5:LRA=11",
                             "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
                             str(d / "voice.wav")], **process_kwargs(dict(capture_output=True, timeout=600)))
        if cp.returncode != 0:
            return {"ok": False, "error": "The voice-over could not be finished (loudness)."}
        heard = [dict(w, s=round(float(w["s"]) / sp, 3), e=round(float(w["e"]) / sp, 3)) for w in (res.get("words") or [])]
        words = tf.mark_emphasis(align(job["text"], heard))   # *words* -> shown in the color
        (d / "words.json").write_text(json.dumps(words, ensure_ascii=False), "utf-8")
        (d / "captions.srt").write_text(srt(cues(words)), "utf-8")
        if not cfg.get("keep_work"):                      # the pieces and tries (kept only when asked, for support)
            shutil.rmtree(d / "work", ignore_errors=True)
        n = max(1, len(re.findall(r"[\w']+", job["text"])))
        secs = res.get("seconds")
        return {"ok": True, "seconds": round(float(secs) / sp, 2) if secs else secs, "device": res.get("device"),
                "said": res.get("said"), "speed": sp, "engine": engine,
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
        (d / "words.json").write_text(json.dumps(words, ensure_ascii=False), "utf-8")     # for the editor
        opts = job.get("opts") or tf.options(position=job.get("position"))
        cs = style_cues(words, opts)
        (d / "captions.srt").write_text(srt(cs), "utf-8")
        out = _burn(Path(job["source"]), None, cs, d, keep_sound=True, offset=0.0, opts=opts, texts=job.get("texts"))
        return {"ok": True, "said": res.get("said"), "language": res.get("language"), "words": len(words), **out}
    if job["kind"] == "dub":
        vo = JOBS / job["voiceover"]
        words = json.loads((vo / "words.json").read_text("utf-8"))
        opts = job.get("opts") or tf.options(position=job.get("position"))
        cs = style_cues(words, opts) if job.get("captions") else []
        out = _burn(Path(job["video"]), vo / "voice.wav", cs, d, keep_sound=job.get("keep_sound", True),
                    offset=float(job.get("start_s") or 0.0), opts=opts, texts=job.get("texts"))
        return {"ok": True, **out}
    if job["kind"] == "render":
        voice = None
        if job.get("voice_from"):
            vj = read_job(job["voice_from"]) if (JOBS / job["voice_from"]).is_dir() else {"state": "gone"}
            if vj["state"] == "waiting":                 # its voice-over is still to be made: after it
                return {"_requeue": True}
            if vj["state"] not in ("done", "gone"):     # failed, interrupted or still waiting: not made
                return {"ok": False, "error": "The voice-over was not made, so this video was not made either: "
                                              + str((vj.get("result") or {}).get("error") or "")[:300]}
            voice = _job_dir(job["voice_from"]) / "voice.wav"
            if not voice.is_file():
                return {"ok": False, "error": "The voice-over of this video was deleted."}
        if job.get("captions_from") and not job.get("cues"):          # captions decided when the video is made
            opts = tf.options(**(job.get("opts") or {}))
            if job["captions_from"] == "voice":
                words = voiceover_words(job["voice_from"])
            else:
                res = _run_worker({"task": "transcribe", "source": job["video"], "wav16": str(d / "sound16k.wav"),
                                   "ffmpeg": _ffmpeg(), "language": None}, d / "work", timeout=6 * 3600, on_line=_progress)
                (d / "sound16k.wav").unlink(missing_ok=True)
                if not res.get("ok"):
                    return res
                words = align(job.get("script") or "", res.get("words") or [])   # my text, timed to the speech
                words = tf.mark_emphasis(words) if job.get("script") else words
                if not words:
                    return {"ok": False, "error": "No speech was found in this video."}
                sh = float(job.get("start_s") or 0.0)    # the video's own times; captions are drawn at +start_s
                words = [{**w, "s": w["s"] - sh, "e": w["e"] - sh} for w in words]
            job["cues"] = style_cues(words, opts)          # kept: the editor of this video starts from them
            _write_job(d, job)
        if job.get("music") and not Path(job["music"]).is_file():
            return {"ok": False, "error": "The music file is no longer there: " + str(job["music"])}
        out = _burn(Path(job["video"]), voice, (job.get("cues") or []) if job.get("captions_on", True) else [], d,
                    keep_sound=job.get("keep_sound", True), music=job.get("music") or None,
                    music_level=job.get("music_level") or "medium",
                    offset=float(job.get("start_s") or 0.0), opts=job.get("opts"), texts=job.get("texts"))
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


def _burn(video: Path, voice_wav: Path | None, cs: list[dict], d: Path, keep_sound: bool, offset: float,
          opts: dict | None = None, texts: list[dict] | None = None, position: str | None = None,
          music: str | None = None, music_level: str = "medium") -> dict:
    """The video with the voice (its own sound ducked under it, or none) and the captions burned in -> d/video.mp4,
    checked (H.264 + AAC, plays to the end)."""
    from . import auto_edit as ae, orders as od
    _CURRENT.update(step="video", progress=0.5)
    try:
        info = _probe_video(video)
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
    sw, sh = int(vs.get("width") or 1080), int(vs.get("height") or 1920)
    w, h = _display_size(vs, info)                         # upright, square pixels: as a player shows it
    voice_len = 0.0
    if voice_wav is not None:
        voice_len = float(od._decode_info(voice_wav, timeout=300).get("seconds") or 0)
    length = max(vlen, offset + voice_len + 0.5) if voice_wav is not None else vlen
    # its last picture held to the end, whatever the picture's own length (a picture can end before its sound, and the
    # file's length is the longer of the two): the new video is cut at `length` (-t)
    vf = [f"tpad=stop_mode=clone:stop_duration={length:.3f}"]
    # the size of the new video: what Reels / TikTok / Shorts show (a short side of at most 1080: a 4K phone video is
    # made several times faster), always even (H.264 4:2:0); the text is laid out for exactly this size
    k = min(1.0, MAX_SHORT_SIDE / max(1, min(w, h)))
    tw, th = int(w * k) // 2 * 2, int(h * k) // 2 * 2
    turned = int(info.get("rotation") or 0) in (90, 270)
    if (tw, th) != ((sh, sw) if turned else (sw, sh)) or _sar(vs) != 1.0:
        vf.append(f"scale={tw}:{th}:flags=lanczos,setsar=1")
    w, h = tw, th
    o = tf.options(**{**(opts or {}), **({"position": position} if position else {})})
    tx = tf.resolve_texts(texts, length)
    if cs or tx:
        (d / "captions.ass").write_text(tf.document(w, h, cs, tx, o, offset), "utf-8")
        if cs:
            (d / "captions.srt").write_text(srt(cs, offset=offset), "utf-8")
        fonts = tf.install_fonts(d)
        fonts = _caption_font(d) or fonts           # Windows: Arial too, for a letter Montserrat does not have
        vf.append("ass=captions.ass" + (":fontsdir=fonts" if fonts else ""))
    vf.append("format=yuv420p")
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-i", str(video)]
    fc = [f"[0:v]{','.join(vf)}[v]"]
    mus = Path(music) if music else None
    if voice_wav is None and mus is None:
        amap = "0:a?" if keep_sound else None
    else:
        parts, n_in = [], 1                                    # the streams mixed, each ducked under the voice
        bed = (keep_sound and has_audio) + (mus is not None)
        if voice_wav is not None:
            cmd += ["-i", str(voice_wav)]
            ms = int(offset * 1000)
            fc.append(f"[{n_in}:a]adelay={ms}|{ms},aformat=channel_layouts=stereo,apad=whole_dur={length:.3f},"
                      f"asplit={bed + 1}" + "".join(f"[sc{i}]" for i in range(bed)) + "[vo]")
            n_in += 1
            parts.append("[vo]")
        k = 0

        def duck(label: str) -> str:
            nonlocal k
            if voice_wav is None:
                return label
            fc.append(f"{label}[sc{k}]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[d{k}]")
            k += 1
            return f"[d{k - 1}]"
        if keep_sound and has_audio:
            fc.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={length:.3f},"
                      f"volume={'-4dB' if voice_wav is not None else '0dB'}[bg]")
            parts.append(duck("[bg]"))
        if mus is not None:
            cmd += ["-stream_loop", "-1", "-i", str(mus)]
            # with a voice: the music's own level where nobody speaks (about -22 / -19 / -16 LUFS), pressed down under
            # the voice by the sidechain - measured 15 / 13 / 10 dB under the voice; it comes back up when the voice
            # stops (it used to sit at -32 / -27 / -22 LUFS and stay there: the end of a video went nearly silent)
            gain = {"quiet": -6, "medium": -3, "loud": 0}.get(music_level, -3) if voice_wav is not None else \
                {"quiet": -12, "medium": -7, "loud": -2}.get(music_level, -7)
            fc.append(f"[{n_in}:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{length:.3f},"
                      f"asetpts=N/SR/TB,loudnorm=I=-16:TP=-2:LRA=11,aresample=48000,volume={gain}dB,afade=t=in:d=0.6,"
                      f"afade=t=out:st={max(0.0, length - 1.6):.3f}:d=1.5,apad=whole_dur={length:.3f}[mu]")
            n_in += 1
            parts.append(duck("[mu]"))
        only_music = voice_wav is None and not (keep_sound and has_audio)
        target = {"quiet": -22, "medium": -18, "loud": -14}.get(music_level, -18) if only_music else -14
        fc.append("".join(parts) + (f"amix=inputs={len(parts)}:duration=longest:normalize=0," if len(parts) > 1 else "")
                  + f"loudnorm=I={target}:TP=-1.5:LRA=11[a]")     # music alone: its loudness is the one chosen
        amap = "[a]"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]"]
    if amap:
        cmd += ["-map", amap]
    # a new file, put in place of video.mp4 only when made and checked: the copy saved next to the reels is a second
    # name of the earlier video.mp4 (os.link) - writing into video.mp4 itself would change (or break) that copy
    new_out = d / "video.new.mp4"
    new_out.unlink(missing_ok=True)
    tail_args = ["-t", f"{length:.3f}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", new_out.name]
    cpu = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    gpu = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-profile:v", "high"]
    log = d / "ffmpeg.log"
    tries = ([gpu] if nvenc_ok() else []) + [cpu]           # an NVIDIA card makes the picture; any failure: the processor
    rc = -1
    for i, enc in enumerate(tries):
        rc = _run_ffmpeg(cmd + enc + tail_args, d, log, 6 * 3600)
        if rc == 0 and new_out.is_file() and new_out.stat().st_size > 1000:
            break
        new_out.unlink(missing_ok=True)
        if _CURRENT.get("cancel"):
            break
    shutil.rmtree(d / "fonts", ignore_errors=True)
    if _CURRENT.get("cancel"):
        new_out.unlink(missing_ok=True)
        raise VoiceError("Stopped.")
    if rc != 0 or not new_out.is_file():
        lines = [x for x in log.read_text("utf-8", errors="replace").splitlines() if x.strip()]
        why = next((x for x in reversed(lines) if not re.match(r"\s*(frame=|size=|\$ )", x)), lines[-1] if lines else "?")
        raise VoiceError("FFmpeg could not make the video (" + why[:200] + ").")
    _CURRENT.update(step="checking", progress=0.9)
    with_sound = voice_wav is not None or (keep_sound and has_audio) or bool(music)
    checks = od._check_output(new_out, {"seconds": length, "tolerance": 0.25, "audio": with_sound})
    if not all(c["pass"] for c in checks):
        bad = next(c for c in checks if not c["pass"])
        os.replace(new_out, d / "video_failed_check.mp4")
        raise VoiceError(f"The new video did not pass its check ({bad['check']}: {bad['detail']}).")
    os.replace(new_out, d / "video.mp4")
    saved = _save_copy(d / "video.mp4", video.stem, "voice" if voice_wav is not None else "captions" if cs else
                       "text" if tx else "music" if music else "text")
    return {"files": {"video": "video.mp4", **({"srt": "captions.srt"} if cs else {})}, "seconds": round(length, 2),
            "checks": checks, "captions": len(cs), "texts": len(tx), "width": w, "height": h, "saved": saved}


_SAR_RE = re.compile(r"Video:.*?\[SAR (\d+):(\d+)")


def _probe_video(video: Path) -> dict:
    """The program's probe, with the shape of the picture's pixels (SAR) of its first video stream added from the
    same FFmpeg answer (the probe itself leaves it out)."""
    from . import auto_edit as ae
    info = ae._probe(video)
    text = (getattr(ae._PROBE_TEXT, "text", "") or "").split("Stream mapping:", 1)[0]
    m = _SAR_RE.search(text)
    if m and isinstance(info, dict):
        for st in info.get("streams", []) or []:
            if st.get("codec_type") == "video":
                st.setdefault("sample_aspect_ratio", f"{m.group(1)}:{m.group(2)}")
                break
    return info


def _sar(vs: dict) -> float:
    """The shape of a stored pixel (1 = square; a 1440x1080 camcorder video with 4:3 pixels is shown 1920 wide)."""
    try:
        a, b = (int(x) for x in str(vs.get("sample_aspect_ratio") or "1:1").split(":"))
        r = a / b if a > 0 and b > 0 else 1.0
    except (ValueError, ZeroDivisionError):
        r = 1.0
    return r if 0.25 <= r <= 4.0 and abs(r - 1.0) > 0.01 else 1.0


def _display_size(vs: dict, info: dict) -> tuple[int, int]:
    """Width and height as a player shows the picture: square pixels, a phone video stored on its side upright."""
    w, h = int(vs.get("width") or 1080), int(vs.get("height") or 1920)
    w = int(round(w * _sar(vs)))
    if int(info.get("rotation") or 0) in (90, 270):
        w, h = h, w
    return w, h


def _run_ffmpeg(cmd: list[str], cwd: Path, log: Path, timeout: float) -> int:
    """FFmpeg as a child that ends with the program (a Windows job object; Quit and Stop kill it) - its return code."""
    from . import auto_edit as ae
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        lf.write("$ " + " ".join(cmd) + "\n")
        lf.flush()
        proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                **process_kwargs({}))
        ae._attach_job_object(proc)
        _CURRENT["proc"] = proc
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        finally:
            _CURRENT.pop("proc", None)
    return proc.returncode


_CHILDREN: set = set()


def _run_child(cmd: list[str], timeout: float) -> int:
    """A longer FFmpeg run outside the job queue (the small copy): it too ends with the program."""
    from . import auto_edit as ae
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                            **process_kwargs({}))
    ae._attach_job_object(proc)
    _CHILDREN.add(proc)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    finally:
        _CHILDREN.discard(proc)
    return proc.returncode


def cancel_job(jid: str) -> None:
    """Stop: a job being made is stopped (its FFmpeg or voice worker killed, said 'Stopped.'); a waiting one leaves the
    queue. A stopped job can be made again with Try again."""
    with _LOCK:
        if _CURRENT.get("id") == jid:
            _CURRENT["cancel"] = True
            p = _CURRENT.get("proc")
        elif jid in _QUEUE:
            _QUEUE.remove(jid)
            p = None
            d = _job_dir(jid)
            tmp = d / "result.json.tmp"
            tmp.write_text(json.dumps({"ok": False, "error": "Stopped.", "finished_at": now_iso()}), "utf-8")
            os.replace(tmp, d / "result.json")
            return
        else:
            return
    if p is not None:
        try:
            p.kill()
        except Exception:
            pass


def shutdown() -> None:
    """Quit: the voice worker or FFmpeg being run now ends with the program (the job is made again at the next start)."""
    for p in [_CURRENT.get("proc"), *list(_CHILDREN)]:
        if p is not None:
            try:
                p.kill()
            except Exception:
                pass


PREVIEWS = HOME / "voice_previews"
MAX_SHORT_SIDE = 1080


def _words_from_srt(text: str) -> list[dict]:
    """Captions made before their words were kept (only the SRT): each line's words share its time by length."""
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)\s*\n(.+)", block, re.S)
        if not m:
            continue
        g = [int(x) for x in m.groups()[:8]]
        s0 = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        e0 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        cue = tf.retime({"words": [{"w": "x", "s": s0, "e": e0}]}, " ".join(m.group(9).split()))
        out += (cue or {}).get("words", [])
    return out


def voiceover_words(jid: str) -> list[dict]:
    """The timed words of a finished voice-over (for captions and a preview before its video is made)."""
    j = read_job(jid)
    d = _job_dir(jid)
    if j.get("kind") != "voiceover" or j["state"] != "done" or not (d / "words.json").is_file():
        raise VoiceError("This voice-over is not ready.")
    return json.loads((d / "words.json").read_text("utf-8"))


def editor_base(jid: str) -> dict:
    """What the text-and-captions editor starts from for a made video: the source video, the voice (if any) and its
    start, the captions grouped as its style shows them, its texts."""
    j = read_job(jid)
    if j["state"] != "done" or j.get("kind") not in ("dub", "captions", "render"):
        raise VoiceError("Only a finished video can be edited.")
    d = _job_dir(jid)
    opts = tf.options(**(j.get("opts") or {"position": j.get("position")}))
    base = {"jid": jid, "opts": opts, "texts": list(j.get("texts") or []), "voice_from": "", "start_s": 0.0,
            "keep_sound": True, "captions_on": True, "title": j.get("title") or ""}
    if j["kind"] == "dub":
        vo_dir = _job_dir(j["voiceover"])
        if not (vo_dir / "voice.wav").is_file() or not (vo_dir / "words.json").is_file():
            raise VoiceError("The voice-over of this video was deleted, so the video cannot be made again with its voice.")
        words = json.loads((vo_dir / "words.json").read_text("utf-8"))
        base.update(video=j["video"], voice_from=j["voiceover"],
                    start_s=float(j.get("start_s") or 0), keep_sound=bool(j.get("keep_sound", True)),
                    captions_on=bool(j.get("captions", True)), cues=style_cues(words, opts))
    elif j["kind"] == "captions":
        if (d / "words.json").is_file():
            words = json.loads((d / "words.json").read_text("utf-8"))
        else:
            words = _words_from_srt((d / "captions.srt").read_text("utf-8")) if (d / "captions.srt").is_file() else []
        base.update(video=j["source"], cues=style_cues(words, opts))
    else:
        if j.get("voice_from") and not (_job_dir(j["voice_from"]) / "voice.wav").is_file():
            raise VoiceError("The voice-over of this video was deleted, so the video cannot be made again with its voice.")
        m_ = j.get("music") or ""
        base.update(music=m_ if m_ and Path(m_).is_file() else "", music_level=j.get("music_level") or "medium")
        base.update(video=j["video"], voice_from=j.get("voice_from") or "", start_s=float(j.get("start_s") or 0),
                    keep_sound=bool(j.get("keep_sound", True)), cues=list(j.get("cues") or []),
                    captions_on=bool(j.get("cues")) and bool(j.get("captions_on", True)))
    if not Path(base["video"]).is_file():
        raise VoiceError("The video of this one is no longer there: " + str(base["video"]))
    return base


def video_size(video: Path, picture_len: bool = False):
    """Width and height as shown (a phone video stored on its side counts upright) and the length in seconds; with
    picture_len also the length of the picture itself (its sound can run longer than its last frame)."""
    from . import auto_edit as ae, orders as od
    try:
        info = _probe_video(video)
    except Exception as exc:
        raise VoiceError("The video could not be read: " + str(exc)[:200])
    streams = info.get("streams", []) if isinstance(info, dict) else []
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not vs:
        raise VoiceError("This file has no picture: choose a video.")
    vlen = float((info.get("format") or {}).get("duration") or 0)
    if vlen <= 0:
        vlen = float(od._decode_info(video, timeout=1800).get("seconds") or 0)
    w, h = _display_size(vs, info)
    if picture_len:
        try:
            plen = float(vs.get("duration") or 0)
        except (TypeError, ValueError):
            plen = 0.0
        return w, h, vlen, (min(plen, vlen) if plen > 0 else vlen)
    return w, h, vlen


def preview_frame(video: str, cues_: list[dict] | None, opts: dict | None, texts: list[dict] | None,
                  offset: float = 0.0, at: float = 1.0, voice_from: str = "", safe: bool = False, full: bool = False) -> Path:
    """One picture of the finished video at `at` seconds - the same captions and texts, the same fonts - in a second
    or two instead of a whole render. Kept in voice_previews (the ten newest)."""
    from . import orders as od
    p = Path(str(video or "").strip().strip('"'))
    if not p.is_file():
        raise VoiceError("Choose the video (its full path).")
    w, h, vlen, plen = video_size(p, picture_len=True)
    length = vlen
    if voice_from:
        wav = _job_dir(voice_from) / "voice.wav"
        if wav.is_file():
            length = max(vlen, offset + float(od._decode_info(wav, timeout=300).get("seconds") or 0) + 0.5)
    t = max(0.0, min(float(at or 0), max(0.0, length - 0.05)))
    seek = max(0.0, min(t, plen - 0.15))             # past the last picture: the last picture (as the video holds it)
    d = PREVIEWS / _new_id()
    d.mkdir(parents=True, exist_ok=True)
    doc = tf.document(w, h, _clean_cues(cues_), tf.resolve_texts(texts, length), tf.options(**(opts or {})), offset)
    (d / "preview.ass").write_text(doc, "utf-8")
    fonts = tf.install_fonts(d)
    fonts = _caption_font(d) or fonts
    boxes = "".join(f",drawbox=x={x}:y={y}:w={bw}:h={bh}:color=red@0.28:t=fill" for x, y, bw, bh in tf.safe_boxes(w, h)) \
        if safe else ""                       # where the platforms put their buttons and text (a tall video)
    vf = (f"setpts=PTS-STARTPTS+{t:.3f}/TB,ass=preview.ass" + (":fontsdir=fonts" if fonts else "") + boxes
          + ("" if full else ",scale=-2:'min(ih,960)'"))    # a cover: the video's own size
    ff = _ffmpeg()
    run = lambda args: subprocess.run([ff, "-hide_banner", "-nostdin", "-y", "-v", "error", *args], cwd=str(d),
                                      capture_output=True, **process_kwargs(dict(timeout=120)))
    cp = run(["-ss", f"{seek:.3f}", "-i", str(p), "-vf", vf, "-frames:v", "1", "-q:v", "3", "frame.jpg"])
    if not (cp.returncode == 0 and (d / "frame.jpg").is_file()):
        # past the last picture (its sound runs longer; the stream's own length is not known here): the last
        # picture of the last seconds, then the text drawn on it - as the finished video holds that picture
        run(["-ss", f"{max(0.0, seek - 8):.3f}", "-i", str(p), "-an", "-update", "1", "-q:v", "2", "last.jpg"])
        if (d / "last.jpg").is_file():
            cp = run(["-loop", "1", "-i", "last.jpg", "-vf", vf, "-frames:v", "1", "-q:v", "3", "frame.jpg"])
    shutil.rmtree(d / "fonts", ignore_errors=True)
    if cp.returncode != 0 or not (d / "frame.jpg").is_file():
        raise VoiceError("The picture could not be made (" + (cp.stderr.decode("utf-8", "replace").strip()[-200:] or "?") + ").")
    try:                                   # only the ten newest previews are kept
        old = sorted((x for x in PREVIEWS.iterdir() if x.is_dir()), key=lambda x: x.name)[:-10]
        for x in old:
            shutil.rmtree(x, ignore_errors=True)
    except OSError:
        pass
    return d / "frame.jpg"


def small_copy(jid: str) -> str:
    """A small copy of a made video for messengers (long side at most 1280 px, a lower bit rate), next to the reels:
    the same encode as Auto Edit's small copy."""
    from . import auto_edit as ae
    j = read_job(jid)
    src = _job_dir(jid) / "video.mp4"
    if j["state"] != "done" or not src.is_file():
        raise VoiceError("Only a finished video can be copied.")
    d = PREVIEWS / _new_id()
    d.mkdir(parents=True, exist_ok=True)
    L = getattr(ae, "SMALL_LONG_SIDE", 1280)
    out = d / "small.mp4"
    rc = _run_child([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-map", "0:v:0",
                     "-map", "0:a:0?", "-vf", f"scale='if(gte(iw,ih),min(iw,{L}),-2)':'if(gte(iw,ih),-2,min(ih,{L}))'",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac",
                     "-b:a", "128k", "-movflags", "+faststart", str(out)], 1800)
    if rc != 0 or not out.is_file() or out.stat().st_size < 1000:
        shutil.rmtree(d, ignore_errors=True)
        raise VoiceError("The small copy could not be made.")
    stem = Path(str(j.get("video") or j.get("source") or j.get("title") or "video")).stem
    saved = _save_copy(out, stem, "small")
    shutil.rmtree(d, ignore_errors=True)
    if not saved:
        raise VoiceError("The small copy could not be made.")
    return saved


def save_cover(video: str, cues_: list[dict] | None, opts: dict | None, texts: list[dict] | None, offset: float = 0.0,
               at: float = 1.0, voice_from: str = "") -> str:
    """The picture at `at` with its texts (and captions), full size, saved next to the reels as a cover."""
    pic = preview_frame(video, cues_, opts, texts, offset=offset, at=at, voice_from=voice_from, full=True)
    saved = _save_copy(pic, Path(str(video).strip().strip('"')).stem, "cover")
    if not saved:
        raise VoiceError("The cover could not be saved.")
    return saved


_NVENC: list = []


def nvenc_ok() -> bool:
    """Can this PC's FFmpeg encode H.264 on an NVIDIA card (tried once: a fraction of a second of picture)? Turned
    off with the setting voice.encoder = "cpu"."""
    if (load_config().get("voice") or {}).get("encoder") == "cpu":
        return False
    if not _NVENC:
        ok = False
        try:
            cp = subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                                 "color=c=gray:s=256x256:r=25:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                                capture_output=True, **process_kwargs(dict(timeout=60)))
            ok = cp.returncode == 0
        except Exception:
            ok = False
        _NVENC.append(ok)
    return _NVENC[0]


def _save_copy(src: Path, stem: str, what: str) -> str:
    """A copy next to the saved reels (Exports, or the folder used last), never over another file: '<name> - voice.mp4'
    (a cover: '<name> - cover.jpg')."""
    from . import auto_edit as ae
    try:
        folder = ae.default_export_dir()
        folder.mkdir(parents=True, exist_ok=True)
        word = {"voice": "озвучка", "captions": "субтитры", "text": "текст", "cover": "обложка", "music": "музыка",
                "small": "маленькая копия"}[what] \
            if ae._ui_ru() else what
        base = ae.safe_filename(f"{stem[:60]} - {word}", "MediaEngine " + what)
        ext = src.suffix.lower() or ".mp4"
        dst = folder / f"{base}{ext}"
        n = 2
        while dst.exists():
            dst = folder / f"{base} ({n}){ext}"
            n += 1
        try:                                   # the same disk: one file with two names (no second copy on the disk)
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        return str(dst)
    except Exception:
        return ""


_RESUME_DONE: list = []


def resume_after_restart() -> None:
    """Jobs left without an answer by a closed program are made again once (their files were not finished)."""
    with _LOCK:                                                 # once per start, whoever asks first
        if _RESUME_DONE:
            return
        _RESUME_DONE.append(1)
    have = installed()
    for j in reversed(list_jobs(500)):                          # oldest first: a voice before the video using it
        if j["state"] == "interrupted" and not j.get("resumed") and (
                have or (j.get("kind") == "render" and not j.get("needs_addon"))):
            try:
                d = JOBS / j["id"]
                job = json.loads((d / "job.json").read_text("utf-8"))
                job["resumed"] = True
                _write_job(d, job)
                with _LOCK:
                    if j["id"] not in _QUEUE:
                        _QUEUE.append(j["id"])
            except Exception:
                pass
    if _QUEUE:
        with _LOCK:
            if not _THREAD or not _THREAD[0].is_alive():
                _THREAD[:] = [threading.Thread(target=_loop, name="voice-jobs", daemon=True)]
                _THREAD[0].start()


def retry_job(jid: str) -> None:
    """Make again a job that was interrupted (or failed): its own settings, its own folder. A voice-over made again
    takes along the videos that were to get it and stopped because it was not made (one Try again, not one per
    video)."""
    j = read_job(jid)
    if j["state"] in ("working", "waiting", "done"):     # (done: a page left open long ago - nothing to make again)
        return
    if j.get("kind") != "render" or j.get("needs_addon"):
        _need_addon()
        if installing():                  # (an installed add-on getting the new engine is busy all the same)
            raise VoiceError("The voice add-on is being installed. Wait until it is ready.")
    again = [jid]
    if j.get("kind") == "voiceover":
        waiting_for_it = [x for x in list_jobs(500) if x.get("kind") == "render" and x.get("voice_from") == jid
                          and (x["state"] == "interrupted" or (x["state"] == "failed" and str((x.get("result") or {})
                               .get("error") or "").startswith("The voice-over was not made")))]
        again += [x["id"] for x in sorted(waiting_for_it, key=lambda x: (x["id"][:15], int(x.get("created_ns") or 0)))]
    with _LOCK:
        for k in again:
            d = _job_dir(k)
            (d / "result.json").unlink(missing_ok=True)
            job = json.loads((d / "job.json").read_text("utf-8"))
            job["resumed"] = False
            _write_job(d, job)
            if k in _QUEUE and k != _CURRENT.get("id"):       # a video waiting already goes behind its voice-over
                _QUEUE.remove(k)
            if k not in _QUEUE:
                vf = job.get("voice_from") if job.get("kind") == "render" else ""
                if vf and vf in _QUEUE and vf != _CURRENT.get("id"):
                    _QUEUE.insert(_QUEUE.index(vf) + 1, k)     # its voice-over waits: right after it
                else:
                    _QUEUE.append(k)
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

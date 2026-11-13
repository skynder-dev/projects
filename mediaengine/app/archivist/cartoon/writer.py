"""Cartoon Studio's story writer: a small free language model on this PC writes the plain-text story (textscript) of a
cartoon - from a topic, from a text to retell, or a story retold for viewers of another country and language.

The model: Qwen3-4B-Instruct-2507 (Alibaba, Apache-2.0) as a Q8_0 GGUF; run by llama.cpp's server (MIT, the release's
ready-made Windows build with the Vulkan backend: the graphics card of any maker through its own driver, the processor
when there is none). Both are downloaded once, on the owner's press, pinned and SHA-256 checked, into
DATA\\addons\\writer (about 4.4 GB). The server is started for one story at a time, on 127.0.0.1 with a random port
and key, and stopped after it; it is never online. Nothing paid, nothing sent anywhere. A story is a job of the
program's queue (one heavy thing at a time: the voices and the writer share the graphics card).
"""
from __future__ import annotations

import hashlib, json, os, re, secrets, shutil, socket, subprocess, threading, time, urllib.request, zipfile
from pathlib import Path

from ..config import HOME
from ..db import now_iso
from ..platform_adapter import process_kwargs
from . import textscript as T

VERSION = 1
ROOT = HOME / "addons" / "writer"
BIN = ROOT / "bin"
MODEL_DIR = ROOT / "model"
MANIFEST = ROOT / "addon.json"
# llama.cpp's release with ready-made builds (github.com/ggml-org/llama.cpp, MIT): its Windows x64 builds - Vulkan
# (the graphics card of any maker through its own driver) and the processor's (a PC without a Vulkan driver)
LLAMA = {"tag": "b11941", "builds": {
    "vulkan": {"name": "llama-b11941-bin-win-vulkan-x64.zip", "size": 37230602,
               "sha256": "3383efca87453d1d1e564b91d95db16d5b511ec72fad4983fd99ea8774649fd6"},
    "cpu": {"name": "llama-b11941-bin-win-cpu-x64.zip", "size": 24306304,
            "sha256": "67549a639ceca9ac971333b7d5c0a93d080579e1a345b4427deff309c605d864"}}}
# the models (the repository's commit and the file's SHA-256), one installed at a time:
# small - Qwen3-4B-Instruct-2507 as a Q8_0 GGUF made by llama.cpp's own people (ggml-org): any PC, quick
# big   - Qwen3-14B as Qwen's own Q4_K_M GGUF: clearly better Russian and Romanian and lengths kept (the writer probe,
#         run 40618245131); for a graphics card with 12 GB (slow on a processor)
MODELS = {
    "small": {"label": "Qwen3-4B", "repo": "ggml-org/Qwen3-4B-Instruct-2507-Q8_0-GGUF",
              "rev": "e6f794d44f9395d0184a966c27b5ae99ea356fcb", "file": "qwen3-4b-instruct-2507-q8_0.gguf",
              "size": 4280403520, "sha256": "ae916ede1c010a26955ee8ae2e908bf8815a3f135ec860439ab924701c69d5f1"},
    "big": {"label": "Qwen3-14B", "repo": "Qwen/Qwen3-14B-GGUF", "rev": "530227a7d994db8eca5ab5ced2fb692b614357fd",
            "file": "Qwen3-14B-Q4_K_M.gguf", "size": 9001752960,
            "sha256": "500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0"},
}
MODEL = MODELS["small"]                  # (the one a check of an older version names)
NEED_FREE = 6 * 10 ** 9
CTX = 12288                               # (a film's treatment and its storyboard fit: story.py)
LANGS = {"en": "English", "ru": "Russian", "ro": "Romanian"}
COUNTRY = {"en": "the United States", "ru": "Russia", "ro": "Romania"}
MONEY = {"united states": "dollars", "usa": "dollars", "us": "dollars", "america": "dollars", "canada": "Canadian dollars",
         "united kingdom": "pounds", "uk": "pounds", "england": "pounds", "britain": "pounds", "ireland": "euros",
         "germany": "euros", "france": "euros", "italy": "euros", "spain": "euros", "romania": "lei", "moldova": "Moldovan lei",
         "russia": "roubles", "ukraine": "hryvnias", "kazakhstan": "tenge", "belarus": "Belarusian roubles",
         "россия": "roubles", "рф": "roubles", "молдова": "Moldovan lei", "румыния": "lei", "казахстан": "tenge",
         "україна": "hryvnias", "украина": "hryvnias", "беларусь": "Belarusian roubles", "românia": "lei", "romania ": "lei"}
US_NAMES = ("united states", "usa", "u.s.", "us", "america", "сша", "америка", "statele unite", "sua")
UK_NAMES = ("united kingdom", "uk", "england", "britain", "great britain", "scotland", "wales", "великобритания", "англия",
            "marea britanie", "anglia")
MAX_TOPIC = 600
MAX_SOURCE = 5000

_LOCK = threading.Lock()
INSTALL = {"state": "idle", "step": "", "done": 0, "total": 0, "error": "", "detail": "", "started": 0.0}
_STOP = threading.Event()


class WriterError(Exception):
    pass


# ------------------------------------------------------------------------------------------------- the add-on

def manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text("utf-8"))
    except Exception:
        return {}


def _llama_bytes() -> int:
    return sum(int(b["size"]) for b in LLAMA["builds"].values())


def _server_exe(build: str = "vulkan") -> Path | None:
    d = BIN / build
    if not d.is_dir():
        return None
    for name in ("llama-server.exe", "llama-server"):
        hits = sorted(d.rglob(name))
        if hits:
            return hits[0]
    return None


def which() -> str:
    """The model installed ("small" or "big")."""
    w = manifest().get("which") or "small"
    return w if w in MODELS else "small"


def _model_path(key: str | None = None) -> Path:
    return MODEL_DIR / Path(MODELS[key or which()]["file"] or "model.gguf").name


def _binaries_ok() -> bool:
    return manifest().get("llama") == LLAMA["tag"] and all(_server_exe(b) is not None for b in LLAMA["builds"])


def installed() -> bool:
    m = manifest()
    md = MODELS[which()]
    return bool(m.get("version") == VERSION and m.get("model") == [md["repo"], md["rev"], md["file"]] and _binaries_ok()
                and _model_path().is_file())


def still_needed(key: str) -> int:
    """Bytes still to download for a model (what is already on disk - a checked file by its size, a part - counted)."""
    md = MODELS[key]
    p = _model_path(key)
    need = 0 if (p.is_file() and p.stat().st_size == int(md["size"])) else \
        int(md["size"]) - (p.with_name(p.name + ".part").stat().st_size if p.with_name(p.name + ".part").is_file() else 0)
    if not _binaries_ok():
        for z_ in LLAMA["builds"].values():
            z = ROOT / "tmp" / z_["name"]
            have = z.stat().st_size if z.is_file() else (z.with_name(z.name + ".part").stat().st_size
                                                          if z.with_name(z.name + ".part").is_file() else 0)
            need += max(0, int(z_["size"]) - have)
    return max(0, need)


def _vram_gb() -> float:
    """The graphics card's memory as the voice add-on measured it (0 when not known)."""
    try:
        from .. import voice as vo
        return float(vo.manifest().get("vram_gb") or 0)
    except Exception:
        return 0.0


def recommend() -> str:
    return "big" if _vram_gb() >= 10 else "small"


def installing() -> bool:
    return INSTALL["state"] == "running"


def _free(p: Path) -> int:
    q = p
    while not q.exists() and q != q.parent:
        q = q.parent
    try:
        return shutil.disk_usage(q).free
    except OSError:
        return 0


def status() -> dict:
    s = dict(INSTALL)
    m = manifest()
    s.update(installed=installed(), manifest=m, free=_free(ROOT), which=which() if m else "", recommend=recommend(),
             needed={k: still_needed(k) for k in MODELS},
             sizes={k: _llama_bytes() + int(v["size"]) for k, v in MODELS.items()}, labels={k: v["label"] for k, v in MODELS.items()},
             vram_gb=_vram_gb(), gpu=str((m or {}).get("gpu") or ""),
             needs_update=bool(m) and not installed() and s["state"] != "running")
    s["size"] = s["sizes"][s["which"] or s["recommend"]]
    return s


def start_install(key: str = "") -> None:
    """Install the story writer with a model ("small" / "big"), or change to the other model when it is installed."""
    from .. import voice as vo
    key = key if key in MODELS else recommend()
    if os.environ.get("MEDIAENGINE_WRITER") == "off":
        raise WriterError("The story writer is turned off on this PC (MEDIAENGINE_WRITER=off).")
    with _LOCK:
        if INSTALL["state"] == "running":
            raise WriterError("The story writer is already being installed.")
        if installed() and which() == key:
            raise WriterError("The story writer is already installed.")
        if _writing() or _stories_waiting():
            raise WriterError("A story is being written. Install when it is ready.")
        INSTALL.update(state="running", step="checking", done=0, total=0, error="", detail="", started=time.time(), which=key)
    _STOP.clear()
    threading.Thread(target=_install, args=(key,), name="writer-install", daemon=True).start()


def cancel_install() -> None:
    _STOP.set()


def _writing() -> bool:
    from .. import voice as vo
    jid = str(vo._CURRENT.get("id") or "")
    try:
        return bool(jid) and json.loads((vo.JOBS / jid / "job.json").read_text("utf-8")).get("kind") == "cartoon_write"
    except Exception:
        return False


def _stories_waiting() -> bool:
    """A story to write is waiting in the queue."""
    from .. import voice as vo
    for jid in list(vo._QUEUE):
        try:
            if json.loads((vo.JOBS / jid / "job.json").read_text("utf-8")).get("kind") == "cartoon_write":
                return True
        except Exception:
            pass
    return False


def remove() -> None:
    if installing() or _writing():
        raise WriterError("The story writer is busy. Wait until it has finished.")
    for name in ("bin", "model", "bin.__install__", "tmp", "selftest"):
        shutil.rmtree(ROOT / name, ignore_errors=True)
    MANIFEST.unlink(missing_ok=True)
    INSTALL.update(state="idle", step="", error="", detail="", done=0, total=0)


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ok(p: Path, size: int, sha: str) -> bool:
    return p.is_file() and p.stat().st_size == size and _sha256(p) == sha


def _install(key: str = "small") -> None:
    from ..platform_adapter import keep_awake
    with keep_awake():
        _install_now(key)


def _install_now(key: str = "small") -> None:
    import http.client, urllib.error
    from .. import auto_edit as ae
    log = ROOT / "install.log"
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        MODEL = MODELS[key]
        if not (LLAMA["tag"] and MODEL["rev"]):
            raise WriterError("This MediaEngine has no story writer to install yet.")
        have_bin = _binaries_ok()                          # (changing the model: the program stays)
        total = (0 if have_bin else _llama_bytes()) + int(MODEL["size"])
        need = still_needed(key)
        if _free(ROOT) < need + 1_500_000_000:
            raise WriterError("Not enough free space on the disk of the data folder: the story writer needs about "
                              f"{round((need + 1_500_000_000) / 1e9)} GB free.")
        INSTALL.update(total=total, done=0)
        tmp = ROOT / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        # llama.cpp's servers (zips from github.com), checked, unpacked beside, then put in place together
        new_bin = ROOT / "bin.__install__"
        shutil.rmtree(new_bin, ignore_errors=True)
        done = 0
        for build, z_ in ({} if have_bin else LLAMA["builds"]).items():
            INSTALL.update(step="program", detail=z_["name"])
            z = tmp / z_["name"]
            if not _ok(z, z_["size"], z_["sha256"]):
                part = z.with_name(z.name + ".part")
                ae._fetch_resumable(f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA['tag']}/{z_['name']}",
                                    part, z_["size"], lambda have, done=done: INSTALL.update(done=done + have), stop=_STOP)
                if not _ok(part, z_["size"], z_["sha256"]):
                    part.unlink(missing_ok=True)
                    raise WriterError("The downloaded llama.cpp is not the exact file. Try again.")
                ae._replace_retry(part, z)
            done += int(z_["size"])
            with zipfile.ZipFile(z) as zf:
                for info in zf.infolist():
                    name = info.filename.replace("\\", "/")
                    if name.startswith("/") or ".." in name.split("/"):
                        raise WriterError("The llama.cpp download has an unexpected file in it.")
                zf.extractall(new_bin / build)
            if not any((new_bin / build).rglob("llama-server.exe")) and not any((new_bin / build).rglob("llama-server")):
                raise WriterError("The llama.cpp download has no server in it.")
        if not have_bin:
            if BIN.exists():
                shutil.rmtree(BIN, ignore_errors=True)
            ae._replace_retry(new_bin, BIN, tries=30)
        # the model (a file from huggingface.co at the pinned commit)
        INSTALL.update(step="model", detail=MODEL["file"])
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        dst = _model_path(key)
        base = 0 if have_bin else _llama_bytes()
        if not _ok(dst, MODEL["size"], MODEL["sha256"]):
            part = dst.with_name(dst.name + ".part")
            ae._fetch_resumable(f"https://huggingface.co/{MODEL['repo']}/resolve/{MODEL['rev']}/{MODEL['file']}", part,
                                MODEL["size"], lambda have: INSTALL.update(done=base + have), stop=_STOP)
            INSTALL.update(step="checking_model", detail="")
            if not _ok(part, MODEL["size"], MODEL["sha256"]):
                part.unlink(missing_ok=True)
                raise WriterError("The downloaded model is not the exact file. Try again.")
            ae._replace_retry(part, dst, tries=30)
        INSTALL.update(step="testing", detail="", done=total)
        _remember_gpu(None)                                # (installed again: the card is tried again, and tested now)
        test = selftest(dst, _STOP.is_set)
        if _STOP.is_set():
            raise WriterError("Installation cancelled.")
        for old in MODEL_DIR.glob("*.gguf"):                    # (the other model, or one of an earlier version)
            if old.name != dst.name:
                try:
                    old.unlink(missing_ok=True)
                except OSError:                                # (Windows: still open - removed at the next install)
                    pass
        m = {"version": VERSION, "llama": LLAMA["tag"], "llama_zips": {k: [b["name"], b["sha256"]] for k, b in LLAMA["builds"].items()},
             "which": key, "model": [MODEL["repo"], MODEL["rev"], MODEL["file"]], "model_sha256": MODEL["sha256"],
             "gpu": test.get("gpu") or "", "speed": test.get("speed"), "installed_at": now_iso()}
        tmpm = MANIFEST.with_suffix(".tmp")
        tmpm.write_text(json.dumps(m, indent=1), "utf-8")
        os.replace(tmpm, MANIFEST)
        shutil.rmtree(tmp, ignore_errors=True)
        INSTALL.update(state="done", step="", detail="")
    except Exception as exc:
        msg = str(exc)
        if _STOP.is_set():
            msg = "Installation cancelled."
        elif isinstance(exc, urllib.error.HTTPError):
            msg = f"The download answered HTTP {exc.code}. Try again later."
        elif isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException)):
            msg = "No connection to the internet (or the site did not answer). Check the connection and try again."
        elif isinstance(exc, OSError) and (getattr(exc, "errno", None) == 28 or getattr(exc, "winerror", None) in (39, 112)):
            msg = "The disk of the data folder is full. Free some space and press Try again - what was downloaded is kept."
        INSTALL.update(state="failed", error=msg[:400], failed_at=time.time())
        try:
            with log.open("a", encoding="utf-8") as lf:
                lf.write(f"\n{now_iso()} FAILED: {exc!r}\n")
        except Exception:
            pass


# ------------------------------------------------------------------------------------------------- the server

def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    """llama.cpp's server for one story: started, asked, stopped. gpu=False: the processor only."""

    def __init__(self, gpu: bool = True, track: bool = True, log: Path | None = None, model: Path | None = None,
                 extra: list | None = None):
        self.gpu, self.track = gpu, track
        self.extra = list(extra or [])                    # (more of the server's options: a model that sees pictures)
        self.model = model or _model_path()
        self.build = "vulkan" if gpu else "cpu"
        self.port, self.key = _port(), secrets.token_hex(16)
        self.log = log or (ROOT / "server.log")
        self.proc = None
        self.device = ""

    def _cmd(self) -> list[str]:
        fake = os.environ.get("MEDENG_WRITER_SERVER")         # (the checks: a stand-in server, never set for a person)
        base = fake.split("|") if fake else [str(_server_exe(self.build) or "llama-server")]
        cmd = base + ["-m", str(self.model), "-c", str(CTX), "--host", "127.0.0.1", "--port", str(self.port),
                      "--api-key", self.key, "-np", "1", "--jinja", "--no-webui"]
        # the graphics card: as many layers as fit (the server's own 'auto'); the processor: no card at all
        return cmd + self.extra + ([] if self.gpu else ["-ngl", "0", "--device", "none"])

    def start(self, stop=lambda: False, timeout: float = 600) -> "Server":
        from .. import auto_edit as ae, voice as vo
        self.log.parent.mkdir(parents=True, exist_ok=True)
        lf = self.log.open("w", encoding="utf-8", errors="replace")
        try:
            self.proc = subprocess.Popen(self._cmd(), stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                         cwd=str(_server_exe(self.build).parent if _server_exe(self.build) else
                                                 ROOT if ROOT.is_dir() else self.log.parent),
                                         **process_kwargs(below_normal=False))
        except OSError as exc:
            lf.close()
            raise WriterError(f"The story writer could not be started: {exc}")
        lf.close()
        ae._attach_job_object(self.proc)
        if self.track:
            vo._track(self.proc)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if stop():
                self.close()
                raise WriterError("Stopped.")
            if self.proc.poll() is not None:
                tail = self._tail()
                self.close()
                raise WriterError("The story writer stopped while starting: " + tail)
            try:
                with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.port}/health",
                                                                   headers={"Authorization": f"Bearer {self.key}"}), timeout=5) as r:
                    if r.status == 200:
                        self.device = self._device()
                        return self
            except Exception:
                pass
            time.sleep(0.5)
        self.close()
        raise WriterError("The story writer did not start in time.")

    def _tail(self, n: int = 6) -> str:
        try:
            lines = [x.strip() for x in self.log.read_text("utf-8", errors="replace").splitlines() if x.strip()]
            return " | ".join(lines[-n:])[-600:]
        except OSError:
            return "?"

    def _device(self) -> str:
        """The graphics card the model is on (from the server's own log), '' for the processor."""
        try:
            txt = self.log.read_text("utf-8", errors="replace")
        except OSError:
            return ""
        if not self.gpu or not re.search(r"offloaded\s+[1-9]\d*/\d+\s+layers\s+to\s+GPU", txt):
            return ""
        m = (re.search(r"ggml_vulkan:\s*\d+\s*=\s*([^|\n(]+)", txt) or re.search(r"Device\s+\d+:\s*([^,\n]+)", txt))
        return (m.group(1).strip(" :|") if m else "graphics card")[:80]

    def chat(self, messages: list[dict], max_tokens: int = 2400, temperature: float = 0.7, seed: int = 0,
             on_piece=None, stop=lambda: False, timeout: float = 3600) -> dict:
        body = {"messages": messages, "temperature": temperature, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                "repeat_penalty": 1.05, "max_tokens": max_tokens, "stream": True, "seed": seed or secrets.randbelow(10 ** 6),
                "stream_options": {"include_usage": True},
                "chat_template_kwargs": {"enable_thinking": False}}    # (a model that can think first answers at once)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", json.dumps(body).encode("utf-8"),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        out, n, finish, usage, timings = [], 0, "", {}, {}
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=max(300.0, timeout)) as r:
            for raw in r:
                if stop():
                    raise WriterError("Stopped.")
                if time.time() - t0 > timeout:
                    raise WriterError("The story writer took too long.")
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    msg = json.loads(data)
                except ValueError:
                    continue
                usage = msg.get("usage") or usage
                timings = msg.get("timings") or timings
                for c in msg.get("choices") or []:
                    piece = (c.get("delta") or {}).get("content") or ""
                    if piece:
                        out.append(piece)
                        n += 1
                        if on_piece:
                            on_piece(n)
                    finish = c.get("finish_reason") or finish
                if msg.get("error"):                       # (the server's own error in the stream)
                    raise WriterError("The story writer stopped while writing (" + str(msg.get("error"))[:200] + ").")
            else:
                if not finish:                             # (cut off without its end: the server went away)
                    import http.client
                    raise http.client.IncompleteRead(b"".join(x.encode("utf-8") for x in out))
        return {"text": "".join(out), "pieces": n, "finish": finish, "usage": usage, "timings": timings,
                "s": round(time.time() - t0, 1)}

    def close(self) -> None:
        from .. import voice as vo
        p = self.proc
        if p is None:
            return
        try:
            if p.poll() is None:
                vo._kill(p)
                try:
                    p.wait(timeout=20)
                except Exception:
                    pass
        finally:
            vo._untrack(p, self.track)
            self.proc = None


_DEVICES: dict = {}


def gpu_name() -> str | None:
    """The graphics card llama.cpp's Vulkan build sees (its own --list-devices: "Vulkan0: NAME (12288 MiB, ...)");
    '' when it sees none, None when it could not be asked. Asked once per run of the program."""
    fake = os.environ.get("MEDENG_WRITER_SERVER")
    exe = fake.split("|") if fake else ([str(_server_exe("vulkan"))] if _server_exe("vulkan") else [])
    if not exe:
        return None
    key = "|".join(exe)
    if key not in _DEVICES:
        from .. import auto_edit as ae
        _DEVICES[key] = None                               # (asked once: a driver that hangs is not asked again)
        try:
            proc = subprocess.Popen(exe + ["--list-devices"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, cwd=str(Path(exe[-1]).parent), **process_kwargs(below_normal=False))
            ae._attach_job_object(proc)                    # (ends with the program)
            try:
                out, _ = proc.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=10)
                return None
            txt = (out or b"").decode("utf-8", errors="replace")
        except Exception:
            return None
        if "Available devices" not in txt:
            return None
        names = re.findall(r"^\s*(?:Vulkan|CUDA|ROCm|SYCL|OpenCL)\d+:\s*(.+?)\s*\(\d+ MiB", txt, re.M)
        _DEVICES[key] = names[0][:80] if names else ""
    return _DEVICES[key]


def gpu_failed() -> bool:
    """The graphics card stopped while writing a story on this PC (remembered until the writer is installed or its
    model changed): the stories are written on the processor."""
    try:
        from ..config import load_config
        return (load_config().get("writer") or {}).get("gpu") is False
    except Exception:
        return False


def _remember_gpu(ok: bool | None) -> None:
    try:
        from ..config import update_config

        def change(c):
            w = c.setdefault("writer", {})
            if ok is None:
                w.pop("gpu", None)
            else:
                w["gpu"] = bool(ok)
        update_config(change)
    except Exception:
        pass


def open_server(stop=lambda: False, track: bool = True, log: Path | None = None, model: Path | None = None,
                extra: list | None = None) -> Server:
    """On the graphics card when there is one and it starts; the processor otherwise."""
    card = gpu_name()
    if card == "" or gpu_failed():                         # (no card the Vulkan build can use, or one that failed: the processor)
        return Server(False, track, log, model, extra).start(stop)
    try:
        srv = Server(True, track, log, model, extra).start(stop)
        if card:
            srv.device = card
        return srv
    except WriterError as exc:
        if str(exc) == "Stopped.":
            raise
        first = str(exc)
    try:
        return Server(False, track, log, model, extra).start(stop)
    except WriterError as exc:
        if str(exc) == "Stopped.":
            raise
        raise WriterError(f"{exc} (with the graphics card: {first})")


def selftest(model: Path | None = None, stop=lambda: False) -> dict:
    """The server starts and answers a short question (installation)."""
    srv = open_server(stop, track=False, log=ROOT / "selftest.log", model=model)
    try:
        r = srv.chat([{"role": "user", "content": "Answer with one word: ready"}], max_tokens=8, temperature=0.0, seed=1,
                     stop=stop)
        if not r["text"].strip():
            raise WriterError("The story writer started but wrote nothing.")
        return {"gpu": srv.device, "speed": (r.get("timings") or {}).get("predicted_per_second")}
    finally:
        srv.close()


# ------------------------------------------------------------------------------------------------- the prompts

SYSTEM = ("You are a screenwriter of short animated explainer cartoons about money: how a scheme works, who pays and who "
          "profits. You write in a fixed plain-text format that a program turns into an animated film. You answer with "
          "the script only, nothing before or after it, no markdown.")

FORMAT = """THE FORMAT (keep these English keywords exactly as written here, whatever the language of the story):
Title: <the film's title>
Format: {fmt}
Narrator: <name> (woman or man, narrator)
<Name> (woman or man, <role>)      <- 3 to 5 more characters, one per line: people only, never a company or a thing

== <Background> | <visual>
<Name> (<gesture>, <feeling>): <what they say>
<Name> (<gesture>, <feeling>) [bubble]: <a short exclamation shown in a speech bubble>

Every scene starts with a line "== <Background> | <visual>" (or "== <Background>" alone).
Backgrounds (exactly one of): City street, Office, City hall, Road, Bank, Night, Board, Paper, Hospital, School, Shop, Home, Building site
  (Home is a block of flats; a court or a ministry: City hall; a pharmacy: Shop; numbers and schemes: Board)
Gestures (one of): talk, explain, point, point up, shrug, cross, think, wave, hands up, rubs hands, present, facepalm, fist, sneaky,
  thumbs up, hands on hips, scratches head, phone, shows money, shows paper, sits (sits on a chair or a bench the whole scene)
Feelings (one of): neutral, happy, angry, sad, surprised, sly, worried, laughing, scared

Visuals - what appears on the screen in that scene, written after "|" (a scene may have none):
  title: <main title> / <subtitle>                          (the first scene only)
  flow: <A> -> <B> <amount>; <B> -> <C> <amount>; ...         (where the money goes: 2 to 4 arrows)
  contract: CONTRACT; price <amount>; stamp APPROVED; <a condition>
  tender: TENDER; <condition>; <condition>; <condition>
  bars: <label> <number>, <label> <number> <unit>             (2 or 3 numbers compared)
  counter: <amount> <label>                                  (a sum counting up)
  compare: <thing> <price> vs <thing> <price>
  list: <title>; <item>; <item>; <item>                      (for example the warning signs, at the end)
  bag: <text>                                                (a bag of money)
  magnifier: <word>                                          (someone checks the papers)
  percent: <number>% <label>                                 (a share of the whole, e.g. 30% kickback)
  timeline: <date> <event>; <date> <event>; <date> <event>   (what happened when, 3 to 5 steps)
  road | road: repair | road: holes back                     (only in a story about a road)"""

RULES = """RULES:
- Invent everything: the town, the people, the companies. No real people, no real companies.
- The narrator tells the story and says about half of the lines; the other characters act it out with short lines.
- 8 to 10 scenes, 2 or 3 lines in each; every line one or two short sentences (at most 16 words).
- About {words} spoken words in all ({secs} seconds read aloud).
- In what is said, write numbers as words (four point eight million); in the visuals use digits ($4.8M).
- A clear story: the problem, the trick, who gains, who pays, what happens in the end, and how a viewer can spot it.
- At least five different visuals; never the same visual in two scenes in a row; no kind of visual more than twice.
- Every scene moves the story on: no scene repeats what an earlier one showed.
- The last scene ends with a short lesson for the viewer."""


def _lang_rule(lang: str) -> str:
    n = LANGS.get(lang, "English")
    if lang == "en":
        return "LANGUAGE: English."
    return (f"LANGUAGE: {n}. Everything that is said, the title, the names and every label in the visuals are in {n}; "
            "only the format's keywords stay in English (Title, Format, Narrator, woman, man, the backgrounds, the visual "
            "kinds, CONTRACT, TENDER, APPROVED, price, stamp, the gestures, the feelings).")


def _example() -> str:
    return ("EXAMPLE of the format (a different story: do not reuse its people, its plot or its sentences):\n\n"
            + T.ROAD_TEXT.strip())


def money_of(country: str) -> str:
    c = re.sub(r"\s+", " ", str(country or "").strip().lower())
    return MONEY.get(c) or next((v for k, v in MONEY.items() if len(k) > 3 and k in c), "the local money")


def measures_of(country: str) -> str:
    """The measures the viewers of a country use: miles and gallons in the United States, miles for roads in Britain,
    kilometres and litres elsewhere."""
    c = re.sub(r"\s+", " ", str(country or "").strip().lower()).removeprefix("the ")
    if c in US_NAMES or "united states" in c:
        return "miles, feet, gallons, pounds and degrees Fahrenheit (never kilometres or litres)"
    if c in UK_NAMES or "kingdom" in c:
        return "miles for roads and speeds, otherwise metres, litres and kilograms"
    return "kilometres, metres, litres, kilograms and degrees Celsius (never miles or gallons)"


_TRANSLIT = re.compile(r"zh|kh|shch|\b(?:kak|chto|pochemu|zachem|eto|dlya|kto|gde|kogda|ili|esli|tolko|ochen|nado|"
                       r"mozhno|nelzya|deneg|dengi|gorod\w*|platit|platyat|pro|bez|cherez|posle|kotor\w*)\b")


def _topic_note(topic: str, lang: str) -> str:
    """The topic typed in translit (the owner often types Russian in Latin letters): the model understands it, but
    then copied the translit as the title and gave the people Latin names (probe 40922999385). Said only for a topic
    that looks like translit - the note made the small model translate the format's keywords too (probe 40927742172)."""
    low = str(topic or "").lower()
    if re.search(r"[а-яё]", low) or not re.search(r"[a-z]", low) or not (lang == "ru" or _TRANSLIT.search(low)):
        return ""
    own = (" - for Russian, Cyrillic letters (Анна, not Anna), never translit" if lang == "ru" else "")
    return ("\n(The TOPIC may be Russian typed in Latin letters - translit, like 'kak gorod platit dvazhdy': understand "
            "what it means. The title, the people's names and everything said follow the LANGUAGE rule below, written in "
            f"that language's own letters{own}; the format's keywords stay in English.)")


def prompt(job: dict) -> str:
    """The request to the model for a job: mode 'topic', 'text' or 'adapt'."""
    lang, fmt = job.get("lang") or "en", job.get("format") or "vertical"
    secs = int(job.get("secs") or 75)
    words = int(secs * 1.9)                                # (the model writes about a third more than asked)
    style = job.get("style") if isinstance(job.get("style"), dict) else None
    extra = ""
    if style and job.get("mode") not in ("adapt", "translate"):     # the rhythm of a cartoon studied (reference.py)
        from . import reference as R
        extra, w = R.rules_of(style, secs)
        words = w or words
    rules = RULES.format(words=f"{words - 25} to {words + 25}", secs=secs)
    if extra:
        rules = re.sub(r"(?m)^- 8 to 10 scenes.*$", lambda m: extra, rules)
    try:                                                   # the same host as the earlier films in this language
        from . import library
        h = library.host(lang)
    except Exception:
        h = None
    if h and job.get("mode") not in ("adapt", "translate"):
        who = "woman" if (h.get("look") or {}).get("female") else "man"
        rules += (f"\n- The narrator is {h['name']} ({who}, narrator) - the same host as in the earlier films; write "
                  f"this name exactly as here.")
    country = str(job.get("country") or "").strip() or COUNTRY.get(lang, "")   # (English: the United States)
    where = (f"\nTHE VIEWERS: in {country}; names, money ({money_of(country)}) and offices usual there; measures: "
             f"{measures_of(country)}." if country else "")
    keywords = ("- Keep the format's keywords in English exactly: Title, Format, Narrator, woman, man, ==, the backgrounds "
                "(City street, Office, City hall, Road, Bank, Night, Board, Paper, Hospital, School, Shop, Home, Building site), the visual kinds (title, flow, contract, "
                "tender, bars, counter, compare, list, bag, magnifier, road, percent, timeline), CONTRACT, TENDER, APPROVED, price, stamp, [bubble], "
                "the gestures and the feelings in brackets.\n"
                "- In what is said, numbers as words; in the visuals, digits.")
    if job.get("mode") == "translate":                     # the same film in another language (Cartoon Studio → Change)
        n = LANGS.get(lang, "English")
        return "\n\n".join([
            f"Translate this cartoon script into {n}.",
            "RULES:\n"
            "- Keep everything else as it is: the scenes and their order, the backgrounds, the visuals and their numbers, "
            "who says each line, [bubble].\n"
            f"- Translate what is said and every label in the visuals into natural spoken {n} (not word for word), with "
            "the same meaning and about the same length.\n"
            f"- The same people in the same order: write each name as it sounds, in {n} letters"
            + (" (Kate - Кейт)" if lang == "ru" else "") + "; keep their roles.\n"
            "- Keep the money and the amounts as they are.\n" + keywords,
            "SCRIPT:\n\n" + str(job.get("source") or "").strip()[:MAX_SOURCE], f"Now write the whole script in {n}."])
    if job.get("mode") == "adapt":
        n = LANGS.get(lang, "English")
        country = country or COUNTRY.get(lang, "the United States")
        return "\n\n".join([
            f"Retell this cartoon script for viewers in {country}, in {n}.",
            "RULES:\n"
            "- Keep the scheme, the scenes, their order, the backgrounds and the kinds of visuals.\n"
            "- The same people in the same order (only their names change), the same men and women.\n"
            f"- Use first names and surnames usual in {country}, the local money ({money_of(country)}) with amounts that "
            f"make sense there, the local measures ({measures_of(country)}) and the local names of offices and jobs.\n"
            f"- Translate everything that is said and every label in the visuals into natural spoken {n} (not word for word).\n"
            + keywords,
            "SCRIPT:\n\n" + str(job.get("source") or "").strip()[:MAX_SOURCE], f"Now write the whole script in {n}."])
    if job.get("mode") == "facts":                         # (checked facts from an official page: nothing else)
        f = job.get("facts") or {}
        hook = (f.get("hook_ru") if lang == "ru" else f.get("hook")) or f.get("hook") or ""
        end = (f.get("end_question_ru") if lang == "ru" else "") or f.get("end_question") or ""
        return "\n\n".join([
            "Write a short cartoon script: a host presents what the official page says, to a viewer who needs it. Use ONLY "
            "the FACTS below (exact quotes from the official page), in simple spoken words.",
            FACTS_RULES.format(hook=hook, end=end or "one question viewers answer in one word (their state, or a pick of two)",
                               missing=f.get("not_in_source_ru") or f.get("not_in_source") or "-",
                               angle=f.get("angle_ru") or f.get("angle") or "-", rules=f.get("rules") or "-"),
            f"FACTS (from {f.get('source_url')}):\n\"\"\"\n{str(job.get('source') or '').strip()[:MAX_SOURCE]}\n\"\"\"",
            _lang_rule(lang), FORMAT.format(fmt=fmt), rules, _example(), "Now write the script from the FACTS."])
    if job.get("mode") == "text" and job.get("site"):      # (a web page about an opportunity: a short, useful review)
        return "\n\n".join(["Write a short cartoon script that presents the opportunity described in the TEXT (a web "
                            "page) to a viewer who could use it. Use only its facts and numbers, in your own words.",
                            REVIEW_RULES, f"TEXT:\n\"\"\"\n{str(job.get('source') or '').strip()[:MAX_SOURCE]}\n\"\"\"" + where,
                            _lang_rule(lang), FORMAT.format(fmt=fmt), rules, _example(), "Now write the script about the TEXT."])
    if job.get("mode") == "text":
        return "\n\n".join(["Write a new cartoon script that explains what the TEXT below is about. Use its facts and "
                            "numbers, but tell it in your own words as a story with invented characters; do not copy its "
                            "sentences.", f"TEXT:\n\"\"\"\n{str(job.get('source') or '').strip()[:MAX_SOURCE]}\n\"\"\"" + where,
                            _lang_rule(lang), FORMAT.format(fmt=fmt), rules, _example(), "Now write the script about the TEXT."])
    return "\n\n".join([f"Write a new cartoon script.\n\nTOPIC: {str(job.get('topic') or '').strip()[:MAX_TOPIC]}" + _topic_note(str(job.get('topic') or ''), lang) + where,
                        _lang_rule(lang), FORMAT.format(fmt=fmt), rules, _example(), "Now write the script about the TOPIC."])


FACTS_RULES = """RULES FOR THIS VIDEO (they come before everything else):
- The first scene is ONE line: the hook, said by the host, at most 12 words. It starts with the money or the thing the
  viewer gets, in plain words ("The government can pay part of your heating bill."; "Your old boss may still owe you
  money."), built on: "{hook}". Never a general "help is available", never "if you are...", never "stop", "don't", "no".
- Backgrounds show the topic (a Bank for a loan, a School for college, a Hospital for health, a Shop for a business, a
  Building site or a City street for work): at most one scene at Home or in an Office.
- Only what the FACTS say. Keep every condition they give (who, when, unless...). No promises ("you will get"), no
  advice beyond them, no numbers, names, dates or steps they do not have. The page itself is shown on screen, so NO line says
  "the official page says" - just tell the facts in plain words; only the last scene says where to read it. The host never claims to be an expert, a lawyer or an official.
- NOT IN THE SOURCE (never say or suggest it): {missing}
- The angle: {angle}
- 4 to 6 short scenes, one chain: hook - what it is - who it is for, with its conditions - what the page says to do -
  where to read it (the official page, shown).
- The last line, said by the host: {end}
- The channel's own rules: {rules}"""


REVIEW_RULES = """RULES FOR THIS REVIEW (they come before everything else):
- Every scene is for the viewer's benefit: who can get it, how much, how to apply, until when. Nothing else.
- Never discourage. Never say or show that it is hard, complicated, confusing or not worth it. If the TEXT names a
  difficulty, give it only together with the way through it ("three steps", "one form", "free help at ...").
- No history: no years it was created, no names of laws or politicians, no "since 1965", unless the viewer needs it to apply.
- The scenes are one chain: each scene answers the question the scene before it raises. Order: 1) a hook in the first
  line - the viewer's problem or the money ("College costs too much? Here is up to $X a year you never pay back."),
  2) what it is in one sentence, 3) who can get it, 4) how much, 5) how to apply, step by step, 6) the deadline and where to
  start. 6 to 8 scenes.
- Numbers only as the TEXT gives them; a number you are not sure of is left out, never guessed."""


NOTES = ("Below is part {k} of {n} of what is said in a video (heard by a speech recognizer: some words may be wrong). "
         "Write down its facts as short notes: who is involved, what happened, the numbers and the money, the scheme or "
         "trick, who gained and who paid, the result. Notes only, at most 12 short lines, in English.\n\n\"\"\"\n{text}\n\"\"\"")


def _pieces(text: str, size: int = 4000, most: int = 8) -> list[str]:
    """A long transcript in pieces of about `size` characters (cut after a sentence), at most `most`, spread over it."""
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(sent) > size:
            out.append(cur.strip())
            cur = ""
        cur += sent + " "
    if cur.strip():
        out.append(cur.strip())
    if len(out) > most:
        out = [out[round(i * (len(out) - 1) / (most - 1))] for i in range(most)]
    return out


def clean(answer: str, fmt: str = "", lang: str = "") -> str:
    """The story out of the model's answer: no code fences or markdown marks; the format and language asked for."""
    out = []
    answer = re.sub(r"(?s)<think>.*?</think>", "", str(answer or ""))
    for ln in answer.replace("\r", "").split("\n"):
        s = ln.strip()
        if s.startswith("```"):
            continue
        s = re.sub(r"\*\*|__", "", s)
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"^(?:[-*•]|\d{1,2}[.)])\s+(?=\S)", "", s)
        if fmt and re.match(r"(?i)^(format|формат)\s*:", s):
            s = f"Format: {fmt}"
        if lang and re.match(r"(?i)^(language|язык|limba|limbă)\s*:", s):
            continue                                       # (said once, below, as asked)
        out.append(s)
    text = "\n".join(out).strip()
    if fmt and not re.search(r"(?im)^(format|формат)\s*:", text):
        text = re.sub(r"(?im)^((?:title|название)\s*:.*)$", lambda m: m.group(1) + f"\nFormat: {fmt}", text, count=1)
    if lang in LANGS:                                      # (the language asked for, not one guessed from the letters)
        text = re.sub(r"(?im)^((?:format|формат)\s*:.*)$", lambda m: m.group(1) + f"\nLanguage: {lang}", text, count=1)
    return re.sub(r"\n{3,}", "\n\n", text) + "\n"


def judge(text: str, secs: int = 75, style: dict | None = None) -> tuple[dict, str]:
    """What the program reads from a story, and what is wrong with it for a film ('' when it is fine). style: a
    reference's rhythm (its scenes and words asked instead of the usual)."""
    lo, hi, asked = 8, 10, int(secs * 1.9)
    if style:
        from . import reference as R
        lo, hi, w = R.targets(style, secs)
        asked = w or asked
    sc = T.parse(text)
    scenes = [s for s in sc["scenes"] if s["lines"]]
    lines = sum(len(s["lines"]) for s in scenes)
    words = sum(len(ln["text"].split()) for s in scenes for ln in s["lines"])
    info = {"title": sc.get("title"), "scenes": len(scenes), "lines": lines, "words": words, "language": sc.get("language"),
            "cast": len(sc.get("cast") or {}), "visuals": sum(1 for s in scenes if s.get("visual"))}
    if len(scenes) < 5:
        return info, f"it has only {len(scenes)} scenes with lines ({lo} to {hi} are needed, each starting with ==)"
    if words < asked * 0.63:
        return info, f"it is too short: {words} spoken words (about {asked} are needed)"
    if info["visuals"] < 3:
        return info, "almost no scene shows a visual after | (title, flow, contract, bars, counter, list ...)"
    return info, ""


NUMBER_WORDS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
                "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20", "thirty": "30",
                "forty": "40", "fifty": "50", "sixty": "60", "hundred": "100", "thousand": "1000", "million": "1000000",
                "billion": "1000000000", "percent": "%", "half": "half", "double": "double", "triple": "triple"}


def judge_facts(text: str, f: dict) -> str:
    """What is wrong with a facts video's script against its facts ('' when it is fine): a number the facts do not
    have, a line left unfinished, "the official page says" in more than two lines."""
    sc = T.parse(text)
    said = [ln["text"] for s in sc["scenes"] for ln in s["lines"]]
    src = " ".join([x.get("quote", "") for x in f.get("facts") or []] + [f.get(k) or "" for k in ("hook", "end_question_ru", "rules")]
                   + ["a pick of two"]).lower()
    src_digits = set(re.findall(r"\d+(?:[.,]\d+)?", src))
    src_words = set(re.findall(r"[a-z]+", src))
    if said and _NEGATIVE_HOOK.match(said[0]) or _NEGATIVE_HOOK.match(sc.get("title") or ""):
        return ("the hook starts with \"stop / don't / no\": the first line says what the viewer CAN get or do")
    if said and (not _GAIN.search(" ".join(said[0].split()[:7])) or _WEAK_HOOK.search(said[0])):
        return ("the first line does not hook: it must name the money or the thing the viewer gets in its first words "
                "(pay, money, refund, owed, free, cash, $...), not \"help is available\"")
    alien = []
    for line in said:
        low = line.lower()
        for n in re.findall(r"\d+(?:[.,]\d+)?", low):
            if n not in src_digits:
                alien.append(n)
        for w in re.findall(r"[a-z]+", low):
            if w in NUMBER_WORDS and w not in src_words and NUMBER_WORDS[w] not in src_digits:
                alien.append(w)
    if alien:
        return ("it says numbers the FACTS do not have (" + ", ".join(dict.fromkeys(alien)) + "): say only what the FACTS "
                "say, or leave the number out")
    cut = [ln for ln in said if re.search(r"(\.\.\.|…)\s*$", ln.strip())]
    if cut:
        return f"a line is left unfinished (\"{cut[0][:60]}\"): every line is a whole sentence"
    body = [ln["text"] for s in sc["scenes"][:-1] for ln in s["lines"]]      # (the last scene shows where to read it)
    page = sum(1 for ln in body if _PAGE_RE.search(ln)) \
        - (1 if any(_PAGE_RE.search(ln) and _WHERE.search(ln) for ln in body) else 0)
    if page:
        return (f"\"the official page\" is said in {page} lines: the page is shown on screen, so no line says it - just "
                "tell the facts in plain words; only the last scene says where to read it")
    return ""


_PLACEHOLDER = re.compile(r"\s*(?:\$X+\b|\bX{2,}\b|\[[^\]]*\]|<[^>]*>)")
_FILLER = set("that this with your from have they there their what when will would could should about into only even "
            "still also just been were does here more some them then than very".split())


def _grams(key: str) -> set:
    """A line's two-word runs with a real word in them ("three years", "filing deadline")."""
    w = re.findall(r"[a-z0-9']+", key.lower())
    return {" ".join(w[i:i + 2]) for i in range(len(w) - 1)
            if any(len(x) > 4 and x not in _FILLER for x in w[i:i + 2])}


def _same_point(key: str, said: set) -> bool:
    """The same point said again in other words (the small model's "within three years of the filing deadline" three
    times): five or more of its real words, and nearly all of them, already in one earlier line."""
    mine = _grams(key)                       # (the same two words in two lines already: a third time is too many)
    if mine and any(sum(1 for k in said if g in _grams(k)) >= 2 for g in mine):
        return True
    words = {w for w in key.split() if len(w) > 3 and w not in _FILLER}
    if len(words) < 5:
        return False
    for k in said:
        other = {w for w in k.split() if len(w) > 3 and w not in _FILLER}
        if len(words & other) >= 5 and len(words & other) >= 0.7 * len(words):
            return True
    return False


_GAIN = re.compile(r"(?i)\b(?:pay|pays|paid|money|cash|refund|refunds|owe[sd]?|free|grant|loan|\$\d|dollars?|"
                   r"bills?|benefits?|check|wages?|pension|food|rent|coverage|insurance|save|discount)\b|\$")
_WEAK_HOOK = re.compile(r"(?i)^\W*if\b|help is available|there is help|help may be available|learn (?:about|more)|"
                        r"some programs|^\W*(?:former|current|are you|do you)\b")
_NEGATIVE_HOOK = re.compile(r"(?i)^\W*(?:stop|don'?t|do not|no\b|never|there (?:is|are) no|nothing|forget|quit)\b")
_PAGE_RE = re.compile(r"(?i)\b(?:official page|the (?:web ?)?(?:page|site)|this (?:web ?)?(?:page|site))\b")
_PAGE_PREFIX = re.compile(r"(?i)^(?:but |and |so |also )?(?:the |this )?(?:official )?(?:web ?)?(?:page|site) (?:also )?"
                          r"(?:says|shows|tells you|gives you|lists|explains|has)(?: that)?\s*[:,]?\s*")
_PAGE_ONLY = re.compile(r"(?i)^(?:this is what the official page says|the official page (?:has more details|is here|says)|"
                        r"you can read the full information on the official page|i can check the official page!?)\s*[.!…]*$")
_WHERE = re.compile(r"(?i)\bwhere\b|\bhere\b|usa\.gov|\.gov/|\bcheck (?:it|the|this)\b|\bread\b|\bvisit\b")
_SPEECH = re.compile(r"^([A-Z][\w .'-]*?)((?:\s*\([^)]*\))?(?:\s*\[bubble\])?)\s*:\s*(.*)$")


def tidy_facts(text: str, f: dict) -> str:
    """A facts video's script made to keep to its facts whatever the small model wrote: 'the official page says' kept
    only the first time (after that the fact is just said), a line with a number the facts do not have is left out
    (so is a picture's label with one), a line left unfinished is ended or left out, a line said twice is said once,
    a scene left with no line is left out. The last scene (where to read it, the question) is kept as written."""
    src = " ".join([x.get("quote", "") for x in f.get("facts") or []]
                   + [f.get(k) or "" for k in ("hook", "end_question_ru", "rules")] + ["a pick of two"]).lower()
    digits = set(re.findall(r"\d+(?:[.,]\d+)?", src))
    words = set(re.findall(r"[a-z]+", src))

    def alien(s):
        low = s.lower()
        return any(n not in digits for n in re.findall(r"\d+(?:[.,]\d+)?", low)) or \
            any(w in NUMBER_WORDS and w not in words and NUMBER_WORDS[w] not in digits for w in re.findall(r"[a-z]+", low))

    lines = text.split("\n")
    heads = [i for i, ln in enumerate(lines) if ln.startswith("==")]
    last = heads[-1] if heads else len(lines)
    end = heads[-2] if len(heads) > 1 else last           # (the end: where to read it, the question)
    out, said, page_said, where_said = [], set(), True, False      # (the page is on screen: no line says it before the last scene)
    for i, ln in enumerate(lines):
        if not heads or i < heads[0]:
            out.append(ln)
            continue
        if ln.startswith("=="):
            parts = [x.strip() for x in ln[2:].split("|")]
            parts = [re.sub(r"(?i)^(title:\s*[^/]*?)\s*/\s*[^/]*official[^/]*$", r"\1", x) for x in parts]
            parts = [_PLACEHOLDER.sub("", x).replace("  ", " ").strip() for x in parts]
            parts = [re.sub(r"(?i)^(title:\s*[^/]*?)\s*/.*$", r"\1", x) for x in parts]   # (no small print under a title)   # ("Employee $X": a blank)
            out.append("== " + " | ".join([parts[0]] + [x for x in parts[1:] if not alien(x)]))
            continue
        m = _SPEECH.match(ln)
        if not m:
            out.append(ln)
            continue
        who, how, body = m.group(1), m.group(2), m.group(3).strip()
        if _PAGE_RE.search(body) and _WHERE.search(body) and not where_said and i >= end:
            where_said = True                           # (the one line that says where to read it stays)
        elif _PAGE_RE.search(body):
            if page_said:
                if _PAGE_ONLY.match(body):
                    continue
                shows = re.match(r"(?i)^(?:but |and |so |also )?(?:the |this )?(?:official )?(?:web ?)?(?:page|site) (?:also )?(?:shows|gives you|lists)\b", body)
                body = _PAGE_PREFIX.sub("", body).strip()
                if re.match(r"(?i)to [a-z]", body):          # "it says to search ..." -> "Search ..."
                    body = body[3:]
                elif shows and re.match(r"(?i)(where|how|what)\b", body):
                    body = "Here is " + body[0].lower() + body[1:]
                elif shows and re.match(r"(?i)(you )?(the )?steps\b", body):
                    body = "Here are " + re.sub(r"(?i)^(you )?(the )?", "the ", body)
                if _PAGE_RE.search(body):
                    continue                            # (a line still about the page, not a fact: left out)
            elif _PAGE_ONLY.match(body):
                body = "This is what the official page says."
            page_said = True
        if len(body) > 1 and body[0] in "\"“'" and body[-1] in "\"”'":
            body = body[1:-1].strip()
        if re.search(r"(\.\.\.|…)$", body):
            body = re.sub(r"\s*(\.\.\.|…)$", "", body).rstrip(",;: ")
            if len(body.split()) < 4 or re.search(r"(?i)\b(if|because|when|and|or|but|the|a|to)$", body):
                continue
            body += "."
        if not body or alien(body):
            continue
        key = re.sub(r"[^a-z0-9]+", " ", body.lower()).strip()
        if key in said or (len(key) > 25 and any(key in k or k in key for k in said if len(k) > 25)) or _same_point(key, said):
            if out and _SPEECH.match(out[-1]) and out[-1].rstrip().endswith("?"):
                out.pop()                               # (a question whose answer was a repeat goes with it)
            continue                                    # (said before, or the same said again in other words)
        said.add(key)
        out.append(f"{who}{how}: {body[0].upper() + body[1:]}")
    keep, block = [], []                        # a scene with no line left is left out
    for ln in out + ["==END"]:
        if ln.startswith("=="):
            if block and (not block[0].startswith("==") or any(_SPEECH.match(x) for x in block[1:])):
                keep += block
            block = [ln]
        else:
            block.append(ln)
    return vary_places(_one_line_hook(_no_meta("\n".join(keep).rstrip() + "\n")), f)


def _one_line_hook(text: str) -> str:
    """The first scene: the hook alone (seven seconds of a still title and a general "help is available" before
    anything - the owner 13.11: "nobody stays to the part that matters"); its other lines open the next scene."""
    lines = text.split("\n")
    heads = [i for i, ln in enumerate(lines) if ln.startswith("== ")]
    if len(heads) < 2:
        return text
    a, b = heads[0], heads[1]
    speech = [i for i in range(a + 1, b) if _SPEECH.match(lines[i])]
    if len(speech) < 2:
        return text
    moved = [lines[i] for i in speech[1:]]
    rest = [ln for i, ln in enumerate(lines[:b]) if i not in speech[1:]]
    return "\n".join(rest + [lines[b]] + moved + lines[b + 1:])


_META_DROP = re.compile(r"(?i)^(?:that'?s all (?:it|the page) says|no (?:other|more) (?:steps|details) (?:are )?given|"
                        r"it (?:doesn'?t|does not) say|it only says|it'?s (?:all )?(?:written|right) (?:here|there)|"
                        r"no more,? no less)")
_META_PREFIX = re.compile(r"(?i)^(?:and |but |so )?(?:it|this|the rules?|the irs|they) (?:also )?(?:says?|tells? you|explains?)"
                          r"(?: that)?(?: to)?\s*[:,]?\s*")


def _no_meta(text: str) -> str:
    """The small model's talk about the page instead of the facts ("It says to learn...", "That's all it says") taken out:
    the viewer sees the page on screen; a line says the fact itself."""
    out = []
    for ln in text.split("\n"):
        m = re.match(r"^([^:=][^:]{0,40}?:\s*)(.*)$", ln)
        if not m or ln.lower().startswith(("title:", "site:", "cast:", "format:")):
            out.append(ln)
            continue
        who, body = m.group(1), m.group(2)
        plain = body.replace("\u2019", "'")
        if _META_DROP.match(plain) or re.match(r"(?i)^it(?:'s| is) written\b", plain):
            continue
        cut = re.sub(r"(?i),?\s*but (?:it|the page) (?:doesn'?t|does not) say\b.*$", ".", plain)
        if cut != plain:
            body = plain = cut
            continue
        new = _META_PREFIX.sub("", plain, count=1)
        if new != plain:
            if len(new.split()) < 3:
                continue
            body = new[0].upper() + new[1:]
        out.append(who + body)
    return "\n".join(out)


_TOPIC_PLACES = (                  # what a topic is about -> the backgrounds that show it (the owner: not all home and office)
    (r"health|medic|hospital|doctor|insurance|cobra|chip\b|injur|illness", ("Hospital", "City hall")),
    (r"school|college|student|teacher|fafsa|tuition|universit|educat|scholarship", ("School", "City hall")),
    (r"loan|bank|lender|credit|debt|money|savings?|retire|pension|refund|tax", ("Bank", "City hall")),
    (r"business|shop|store|startup|entrepreneur|sba\b|customer", ("Shop", "Bank")),
    (r"worker|wage|overtime|paycheck|job|employ|labor|construction", ("Building site", "City street")),
    (r"grant|program|benefit|government|federal|state|apply|application", ("City hall", "City street")),
)
_INDOOR = ("Home", "Office")


def vary_places(text: str, f: dict) -> str:
    """A facts video's backgrounds made to show its topic: the small model puts nearly every scene at Home or in an
    Office; after the first one, the next ones go to the places the topic is about (a bank for a loan, a school for
    college, a building site for wages...), the last scene stays where it is."""
    topic = " ".join([str(f.get(k) or "") for k in ("topic", "hook", "audience")] +
                     [x.get("quote", "") for x in (f.get("facts") or [])[:6]]).lower()
    want: list[str] = []
    for pat, places in _TOPIC_PLACES:
        if re.search(pat, topic):
            want += [p for p in places if p not in want]
    want = (want or ["City street", "City hall"]) + ["City street"]
    lines = text.split("\n")
    heads = [i for i, ln in enumerate(lines) if ln.startswith("== ")]
    seen_indoor, k = False, 0
    for i in heads[:-1]:
        m = re.match(r"^== ([^|]+?)\s*(\|.*)?$", lines[i])
        if not m or m.group(1).strip() not in _INDOOR:
            continue
        if not seen_indoor:
            seen_indoor = True
            continue
        lines[i] = "== " + want[k % len(want)] + (" " + m.group(2) if m.group(2) else "")
        k += 1
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------- the job

def do(jid: str, d: Path, job: dict) -> dict:
    """voice._do for a story to write (in the queue's thread)."""
    from .. import voice as vo
    stop = lambda: bool(vo._CURRENT.get("cancel"))      # noqa: E731
    while installing() and not stop():                    # (a model being changed: the story waits for it)
        vo._CURRENT.update(step="loading", progress=0.01)
        time.sleep(1.0)
    if not installed():
        return {"ok": False, "error": "The story writer is not installed: install it on the Cartoon Studio page."}
    job = dict(job)
    if job.get("mode") == "video":                        # a video on this PC: listened to first (the voice add-on)
        heard = _listen(d, job)
        if not heard.get("ok"):
            return heard
        job.update(mode="text", source=heard["text"])
    secs = int(job.get("secs") or 75)
    if job.get("mode") in ("adapt", "translate"):          # (a retelling or a translation: as long as the story)
        src = T.parse(str(job.get("source") or ""))
        secs = max(30, int(sum(len(ln["text"].split()) for s in src["scenes"] for ln in s["lines"]) / 2.2))
    expect = 1500 if job.get("mode") not in ("adapt", "translate") else max(800, len(str(job.get("source") or "")) // 2)
    vo._CURRENT.update(step="loading", progress=0.02)
    box = {"srv": open_server(stop, log=d / "server.log")}

    def ask(messages, **kw):
        """The model's answer; a graphics card that stops in the middle (a driver reset, its memory taken by another
        program) is remembered, and the story is asked again on the processor."""
        import http.client
        import urllib.error
        try:
            return box["srv"].chat(messages, **kw)
        except WriterError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            s = box["srv"]
            time.sleep(0.3)
            died = s.proc is not None and s.proc.poll() is not None
            tail = s._tail(3)
            s.close()
            on_card = s.gpu and bool(s.device)             # (the card really had the model)
            if (stop() or vo.QUITTING or not on_card or not died or isinstance(exc, urllib.error.HTTPError)):
                raise WriterError("Stopped." if stop() else
                                  "The story writer stopped while writing (" + (tail or str(exc))[:300] + ").")
            _remember_gpu(False)
            step = vo._CURRENT.get("step") or "writing"
            vo._CURRENT.update(step="loading")
            box["srv"] = Server(False, log=d / "server-cpu.log").start(stop)
            vo._CURRENT.update(step=step)
            return box["srv"].chat(messages, **kw)
    try:
        if len(str(job.get("source") or "")) > MAX_SOURCE and job.get("mode") == "text":   # a long video: its notes
            pieces, notes = _pieces(str(job["source"])), []
            for k, piece in enumerate(pieces):
                vo._CURRENT.update(step="notes", progress=round(0.4 + 0.2 * k / len(pieces), 3))
                r = ask([{"role": "user", "content": NOTES.format(k=k + 1, n=len(pieces), text=piece)}], max_tokens=400,
                        temperature=0.3, seed=int(job.get("seed") or 0) + k, stop=stop)
                notes.append(re.sub(r"(?s)<think>.*?</think>", "", r["text"]).strip())
            job["source"] = "\n".join(notes)[:MAX_SOURCE]
            (d / "notes.txt").write_text(job["source"], "utf-8")
        from . import story as ST
        if job.get("mode") == "story":                     # a film's treatment: its pictures, said over (story.py)
            messages = [{"role": "system", "content": ST.SYSTEM}, {"role": "user", "content": ST.prompt(job)}]
            expect = 3000
        else:
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt(job)}]
        best, best_info, best_problem, problem, used = "", {}, "", "", 0
        first = 0.6 if (d / "heard.txt").is_file() else 0.05
        tries = 3 if job.get("mode") == "facts" else 2
        for attempt in range(tries):
            used = attempt + 1
            base = first + (0.95 - first) / tries * attempt
            vo._CURRENT.update(step="writing", progress=base)
            r = ask(messages, max_tokens=3600 if job.get("mode") == "story" else 2600, seed=int(job.get("seed") or 0) + attempt,
                    on_piece=lambda n, base=base, span=(0.95 - first) / tries: vo._CURRENT.update(
                        progress=max(float(vo._CURRENT.get("progress") or 0),
                                     round(min(base + span, base + span * n / expect), 3))),
                    stop=stop)
            text = clean(r["text"], job.get("format") or "", job.get("lang") or "")
            if job.get("mode") == "story":
                info, problem = ST.judge(text, secs)
            else:
                info, problem = judge(text, secs, job.get("style") if isinstance(job.get("style"), dict)
                                      and job.get("mode") not in ("adapt", "translate") else None)
            if not problem and job.get("mode") == "facts":
                problem = judge_facts(text, job.get("facts") or {})
            if not problem and r.get("finish") == "length":
                problem = "it was cut off before its end (it is too long): write it shorter"
            rank = (not problem, info["scenes"], info["words"])
            if not best or rank > (not best_problem, best_info.get("scenes", 0), best_info.get("words", 0)):
                best, best_info, best_problem = text, info, problem
            if not problem:
                break
            messages += [{"role": "assistant", "content": r["text"]},
                         {"role": "user", "content": f"This {'storyboard' if job.get('mode') == 'story' else 'script'} "
                                                     f"cannot be used: {problem}. Write it all again, exactly in THE FORMAT."}]
    finally:
        box["srv"].close()
    srv = box["srv"]
    if best_info.get("scenes", 0) < 3:
        return {"ok": False, "error": "The model did not write a usable story (" + (best_problem or problem or "no scenes") + "). "
                                      "Press Try again, or say the topic in other words."}
    if job.get("site") and not re.search(r"(?im)^site\s*:", best):
        best = f"Site: {job['site']}\n" + best             # (the page the story is about: shown in the film's scenes)
    if job.get("mode") == "story" and (job.get("make") or {}).get("quality") == "better" and not re.search(r"(?im)^quality\s*:", best):
        best = re.sub(r"(?im)^(story\s*:.*)$", r"\1\nQuality: better", best, count=1)   # (the pictures drawn carefully)
    if job.get("mode") == "facts":
        best = tidy_facts(best, job.get("facts") or {})
        best_problem = judge_facts(best, job.get("facts") or {})
    (d / "story.txt").write_text(best, "utf-8")
    out = {"ok": True, "file": "story.txt", "title": best_info.get("title") or "", "scenes": best_info["scenes"],
           "words": best_info["words"], "lines": best_info["lines"], "attempts": used, "device": srv.device,
           **({"note": best_problem} if best_problem else {})}
    if isinstance(job.get("make"), dict) and not job["make"].get("hold") and not stop():   # the cartoon made at once
                                                                                          # (a series made while away)
        out.update(_make_film(best, job, best_info.get("title") or job.get("title") or ""))
    return out


def _make_settings(make: dict) -> dict:
    """How a story's cartoon is made at once: voices (when the voice add-on is there), captions, music, close-ups,
    the drawing style."""
    from . import jobs as cj
    from .draw import STYLES
    from .film import PACES
    music = make.get("music") if make.get("music") in ("made", "none", "file") else "made"
    look = make.get("caption_look") if isinstance(make.get("caption_look"), dict) else {}
    return {"voices": bool(make.get("voices", True)), "captions": make.get("captions") if make.get("captions") in cj.CAPTION_STYLES else None,
            "music": music, "mood": make.get("mood") if make.get("mood") in cj.MUSIC_MOODS else "light",
            **({"music_path": str(make.get("music_path") or "")[:500]} if music == "file" else {}),
            "camera": "still" if make.get("camera") == "still" else "close",
            "drawing": make.get("drawing") if make.get("drawing") in STYLES else "flat",
            **({"pace": make.get("pace")} if make.get("pace") in PACES else {}),
            **({"caption_look": {k: str(look[k])[:20] for k in ("color", "size", "position") if look.get(k)}} if look else {}),
            **({"hold": True} if make.get("hold") else {}),
            **({"quality": "better"} if make.get("quality") == "better" else {})}   # (a story's pictures drawn carefully)


def _make_film(story: str, job: dict, title: str) -> dict:
    """The cartoon of a story just written, put in the queue ({"film": id} or {"film_error": why})."""
    from .. import voice as vo
    from . import film as F, jobs as cj
    m = _make_settings(job.get("make") or {})
    script = T.parse(story)
    script["format"] = job.get("format") or script.get("format") or "vertical"
    script["camera"] = m["camera"]
    if job.get("site") and not script.get("site"):
        script["site"] = {"url": job["site"]}
    script["drawing"] = m["drawing"]
    if m.get("quality") == "better":
        script["quality"] = "better"
    from . import reference as R
    script["pace"] = m.get("pace") or R.pace_of(job.get("style"))   # (the rhythm of a reference: the film's pauses too)
    if job.get("mode") in ("adapt", "translate"):          # another language: its voices; the film's own people
        script["language"] = job.get("lang") or script.get("language") or "en"
        if isinstance(job.get("cast"), dict):
            script = F.keep_cast(script, job["cast"])
    music = ({"kind": "made", "mood": m["mood"]} if m["music"] == "made" else
             {"kind": "file", "path": m.get("music_path") or ""} if m["music"] == "file" else None)
    try:
        fid = cj.new_make(script, m["voices"] and vo.installed(),
                          {"style": m["captions"], **(m.get("caption_look") or {})} if m["captions"] else None,
                          title=title, music=music,
                          next_up=True)                    # (each cartoon right after its story, not after the series)
    except (F.FilmError, vo.VoiceError) as exc:
        return {"film_error": str(exc)}
    return {"film": fid}


def _listen(d: Path, job: dict) -> dict:
    """What is said in the job's video (Whisper, the voice add-on), kept in heard.txt (Try again does not listen again)."""
    from .. import voice as vo
    kept = d / "heard.txt"
    if kept.is_file() and kept.stat().st_size > 0:
        return {"ok": True, "text": kept.read_text("utf-8")}
    if not vo.installed():
        return {"ok": False, "error": "Listening to a video needs the voice add-on (Auto Edit → Voice-over → Install)."}
    src = Path(str(job.get("video") or ""))
    if not src.is_file():
        return {"ok": False, "error": "The video is not there any more: " + str(src)}
    vo._CURRENT.update(step="listening", progress=0.02)
    wav = d / "sound16k.wav"
    wjob = {"task": "transcribe", "source": str(src), "wav16": str(wav), "ffmpeg": vo._ffmpeg(), "language": None,
            "duration": vo._seconds(src), "piece_s": 1200.0}

    def line(msg):
        if "progress" in msg:
            vo._CURRENT.update(step="listening", progress=round(0.02 + 0.33 * float(msg["progress"]), 3))
    res = vo.transcribe(wjob, d / "work", timeout=6 * 3600, on_line=line)
    wav.unlink(missing_ok=True)
    shutil.rmtree(d / "work", ignore_errors=True)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "The video could not be listened to.")[:300]}
    text = re.sub(r"\s+", " ", " ".join(str(w.get("w") or "") for w in res.get("words") or [])).strip()
    if len(text.split()) < 20:
        return {"ok": False, "error": "Almost nothing is said in this video: there is no story to retell."}
    kept.write_text(text, "utf-8")
    return {"ok": True, "text": text}


def read_facts(data) -> dict:
    """A video's checked facts (a file of the owner's Social project: id, hook, source_url, facts [{quote, sha256}],
    rules ...), as a dict or its JSON text; what is wrong with it, as WriterError."""
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except ValueError:
            raise WriterError("The facts file is not a JSON file.")
    if not isinstance(data, dict):
        raise WriterError("The facts file is not a video's facts.")
    url = str(data.get("source_url") or "").strip()
    facts = [x for x in (data.get("facts") or []) if isinstance(x, dict) and str(x.get("quote") or "").strip()]
    if not re.match(r"https?://", url) or not facts:
        raise WriterError("The facts file has no official page (source_url) or no facts with quotes.")
    if str(data.get("status") or "").strip().lower() == "withdrawn":
        raise WriterError("This video was withdrawn by its owner (status: withdrawn): it is not made.")
    if str(data.get("owner_decision") or "like").strip().lower() not in ("like", "take", "yes"):
        raise WriterError("The owner has not taken this video (owner_decision is not like): it is not made.")
    keep = ("id", "channel", "topic", "audience", "hook", "hook_ru", "angle_ru", "viewer_question_ru", "end_question_ru",
            "not_in_source_ru", "rules")
    out = {k: str(data.get(k) or "")[:600] for k in keep if data.get(k)}
    out["id"] = re.sub(r"[^\w.-]", "", str(data.get("id") or "facts"))[:60] or "facts"
    out["source_url"] = url[:500]
    out["facts"] = [{"quote": re.sub(r"\s+", " ", str(x["quote"])).strip()[:1200], "sha256": str(x.get("sha256") or "")[:64]}
                    for x in facts[:20]]
    return out


def facts_text(f: dict) -> str:
    """The facts as the writer reads them: numbered quotes."""
    return "\n".join(f"{i}. \"{x['quote']}\"" for i, x in enumerate(f["facts"], 1))


def new_write(mode: str, lang: str = "en", fmt: str = "vertical", secs: int = 75, topic: str = "", source: str = "",
              country: str = "", title: str = "", video: str = "", style: dict | None = None,
              make: dict | None = None, cast: dict | None = None, site: str = "", facts: dict | None = None) -> str:
    """A story to write (a job of the queue). Mode "translate": a film's story in another language (the same people);
    "adapt": retold for viewers in another country. cast: the film's own people ({"cast": ..., "narrator": ...}) - the
    new story's people get their looks and voices (in the same order)."""
    from .. import voice as vo
    if not installed():
        raise WriterError("Install the story writer first.")
    if installing():
        raise WriterError("The story writer is being installed. Wait until it is ready.")
    mode = mode if mode in ("topic", "text", "adapt", "translate", "video", "story", "facts") else "topic"
    if mode == "facts":                                    # a video from checked facts (a file of the owner's Social project)
        facts = read_facts(facts)
        site = facts["source_url"]
        source = facts_text(facts)
        title = title or facts.get("topic") or facts.get("hook") or facts["id"]
    if mode == "video":
        p = Path(str(video or "").strip().strip('"'))
        if not p.is_file():
            raise WriterError("Choose a video (its full path) whose story to retell.")
        if not vo.installed():
            raise WriterError("Listening to a video needs the voice add-on (Auto Edit → Voice-over → Install).")
        vo._check_video(p, need_sound=True)
        video = str(p)
    from . import story as ST
    topic, source = str(topic or "").strip()[:MAX_TOPIC], str(source or "").strip()[:ST.MAX_SOURCE if mode == "story" else MAX_SOURCE]
    if mode == "topic" and len(topic) < 3:
        raise WriterError("Write what the cartoon is about.")
    if mode in ("text", "adapt", "translate", "story", "facts") and len(source) < 40:
        raise WriterError("The text is too short to make a story of it.")
    if mode in ("adapt", "translate") and not T.parse(source)["scenes"]:
        raise WriterError("The story to retell has no scenes.")
    lang = lang if lang in LANGS else "en"
    name = title or (topic if mode == "topic" else Path(video).stem if mode == "video" else source.split("\n", 1)[0])
    name = re.sub(r"(?i)^(title|название)\s*:\s*", "", name).strip()[:60] or "Story"
    return vo._submit({"kind": "cartoon_write", "mode": mode, "lang": lang, "format": fmt if fmt in ("vertical", "horizontal") else "vertical",
                       "secs": (max(60, min(600, int(secs or 300))) if mode == "story" else max(45, min(120, int(secs or 75)))),
                       "topic": topic, "source": source,
                       "country": str(country or "").strip()[:60], "title": name, "seed": secrets.randbelow(10 ** 6),
                       "video": video if mode == "video" else "",
                       **({"site": site} if site and mode in ("text", "facts") else {}),
                       **({"facts": facts} if mode == "facts" else {}),
                       **({"style": style} if isinstance(style, dict) and style and mode not in ("adapt", "translate") else {}),
                       **({"make": _make_settings(make)} if isinstance(make, dict) else {}),
                       **({"cast": cast} if isinstance(cast, dict) and isinstance(cast.get("cast"), dict) and mode in ("adapt", "translate")
                          else {}),
                       "needs_addon": False}, addon=False)


def story_of(jid: str) -> str:
    from .. import voice as vo
    try:
        return (vo._job_dir(jid) / "story.txt").read_text("utf-8")
    except Exception:
        return ""

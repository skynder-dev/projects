"""The picture add-on (Cartoon Studio, stage 2): a free picture model on this PC - FLUX.2 [klein] 4B (Black Forest Labs,
Apache-2.0) - draws a cartoon's characters (standing, talking, pointing, shrugging: from the first picture as the
reference, so it stays the same person) and its places once, into the art folder (art.py); the films then move them.

Installed into <HOME>/addons/pictures only when the owner presses Install: its Python parts (torch, diffusers,
transformers, accelerate - the versions that drew on the owner's RTX 3060) and the model at a pinned commit, each file
checked. It runs below normal priority on the graphics card (NVIDIA), about 20 s a picture on an RTX 3060.
MEDIAENGINE_PAINTER=standin: a stand-in that draws plain figures (checks without a graphics card or the model).
"""
from __future__ import annotations

import colorsys
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from ..config import HOME
from ..platform_adapter import process_kwargs
from . import art

ADDON_VERSION = 1
ROOT = HOME / "addons" / "pictures"
SITE = ROOT / "site"
MODEL = ROOT / "models" / "flux"
MANIFEST = ROOT / "addon.json"
WORKER = Path(__file__).resolve().with_name("painter_worker.py")
REPO, REV = "black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294"
MODEL_PARTS = ("model_index.json", "scheduler/", "text_encoder/", "tokenizer/", "transformer/", "vae/")
TORCH = "2.8.0"
PACKAGES = [f"torch=={TORCH}", "diffusers==0.42.1", "transformers==5.22.1", "accelerate==1.15.0", "safetensors",
            "pillow", "huggingface-hub"]
NEED_FREE = 32 * 10 ** 9            # packages (~5 GB) + the model (~16 GB) + room
SIZE_GB = 21

_LOCK = threading.Lock()
INSTALL = {"state": "idle", "step": "", "done": 0, "total": 0, "error": "", "detail": "", "started": 0.0}
PAINT = {"state": "idle", "done": 0, "total": 0, "error": "", "what": "", "job": ""}
_STOP = threading.Event()
_PSTOP = threading.Event()


class PainterError(Exception):
    pass


def standin() -> bool:
    return os.environ.get("MEDIAENGINE_PAINTER") == "standin"


def manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text("utf-8"))
    except Exception:
        return {}


def installed() -> bool:
    if standin():
        return True
    m = manifest()
    return bool(m.get("version") == ADDON_VERSION and SITE.is_dir() and (MODEL / "model_index.json").is_file())


def status() -> dict:
    from .. import voice as vo
    s = dict(INSTALL)
    s.update(installed=installed(), nvidia=vo._nvidia_name(), free=vo._free(ROOT), paint=dict(PAINT))
    return s


def why_not_install() -> str:
    from .. import voice as vo
    if os.environ.get("MEDIAENGINE_PAINTER") == "off":
        return "The picture add-on is turned off on this PC (MEDIAENGINE_PAINTER=off)."
    if sys.version_info[:2] != (3, 11) and not standin():
        return "The picture add-on needs MediaEngine's own Python 3.11."
    if not vo._nvidia_name() and not standin():
        return "The picture add-on needs an NVIDIA graphics card (on the processor one picture would take an hour)."
    return ""


def start_install() -> None:
    why = why_not_install()
    if why:
        raise PainterError(why)
    with _LOCK:
        if INSTALL["state"] == "running":
            raise PainterError("The picture add-on is already being installed.")
        if installed():
            raise PainterError("The picture add-on is already installed.")
        INSTALL.update(state="running", step="checking", done=0, total=0, error="", detail="", started=time.time())
    _STOP.clear()
    threading.Thread(target=_install, name="painter-install", daemon=True).start()


def cancel_install() -> None:
    _STOP.set()


def remove() -> None:
    if INSTALL["state"] == "running" or PAINT["state"] == "running":
        raise PainterError("The picture add-on is busy. Try when it has finished.")
    shutil.rmtree(ROOT, ignore_errors=True)
    if ROOT.exists():
        raise PainterError("The picture add-on's folder is held by another program a moment. Try again.")


def _install() -> None:
    from ..platform_adapter import keep_awake
    with keep_awake():
        _install_now()


def _install_now() -> None:
    import http.client, socket, urllib.error
    from .. import auto_edit as ae, voice as vo
    log = ROOT / "install.log"
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        if vo._free(ROOT) < NEED_FREE:
            raise PainterError(f"Not enough free space on the disk of the data folder: the picture add-on needs about "
                               f"{NEED_FREE // 10 ** 9} GB free.")
        INSTALL.update(step="packages")
        new = ROOT / "site.__install__"
        shutil.rmtree(new, ignore_errors=True)
        _pip(new, log)
        vo_swap(new, SITE)
        INSTALL.update(step="model")
        files = [f for f in vo._hf_files(REPO, REV) if any(f[0] == p or f[0].startswith(p) for p in MODEL_PARTS)]
        total = sum(f[1] for f in files)
        if vo._free(ROOT) < total + 1_000_000_000:
            raise PainterError("Not enough free space left for the picture model.")
        INSTALL.update(total=total, done=0)
        tmp = MODEL.with_name("flux.__install__")
        done = 0
        for name, size, kind, want in files:
            dst = tmp / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            INSTALL.update(detail=Path(name).name)
            have = MODEL / name
            if not vo._file_ok(dst, size, kind, want) and vo._file_ok(have, size, kind, want):
                ae._replace_retry(have, dst)
            if not vo._file_ok(dst, size, kind, want):
                part = dst.with_name(dst.name + ".part")
                base = done
                ae._fetch_resumable(f"https://huggingface.co/{REPO}/resolve/{REV}/{name}", part, size,
                                    lambda h, base=base: INSTALL.update(done=base + h), stop=_STOP)
                if not vo._file_ok(part, size, kind, want):
                    part.unlink(missing_ok=True)
                    raise PainterError("A downloaded model file is not the exact file (" + Path(name).name + "). Try again.")
                ae._replace_retry(part, dst)
            done += size
            INSTALL.update(done=done)
        if MODEL.exists():
            shutil.rmtree(MODEL, ignore_errors=True)
        ae._replace_retry(tmp, MODEL, tries=30)
        MANIFEST.write_text(json.dumps({"version": ADDON_VERSION, "repo": REPO, "rev": REV, "packages": PACKAGES,
                                        "gpu": vo._nvidia_name(), "installed": time.strftime("%Y-%m-%d %H:%M")}), "utf-8")
        shutil.rmtree(ROOT / "tmp", ignore_errors=True)
        INSTALL.update(state="done", step="", detail="")
    except Exception as exc:
        msg = str(exc)
        if _STOP.is_set():
            msg = "Installation cancelled."
        elif isinstance(exc, urllib.error.HTTPError):
            msg = f"The download answered HTTP {exc.code}. Try again later."
        elif isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException)):
            msg = "No connection to the internet (or the site did not answer). Check the connection and try again."
        INSTALL.update(state="failed", error=msg[:400])
        try:
            with log.open("a", encoding="utf-8") as lf:
                lf.write(f"\nFAILED: {exc!r}\n")
        except Exception:
            pass


def vo_swap(new: Path, final: Path) -> None:
    from .. import auto_edit as ae
    if final.exists():
        shutil.rmtree(final, ignore_errors=True)
    ae._replace_retry(new, final, tries=30)


def _pip(site_dir: Path, log: Path) -> None:
    """The packages with what they need (ready-made wheels only; torch's CUDA build) into the add-on's own folder."""
    from .. import auto_edit as ae, voice as vo
    tmp = ROOT / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    gpu = vo._nvidia_name()
    cmd = [vo._python(), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "--no-input",
           "--progress-bar", "off", "--no-cache-dir", "--only-binary", ":all:", "--target", str(site_dir),
           "--index-url", "https://pypi.org/simple", "--extra-index-url",
           vo.CUDA_INDEX_NEW if re.search(r"RTX\s*50\d0", gpu, re.I) else vo.CUDA_INDEX] + PACKAGES
    env = dict(os.environ, TMP=str(tmp), TEMP=str(tmp), PIP_NO_INPUT="1", PYTHONNOUSERSITE="1")
    env.pop("PYTHONPATH", None)
    with log.open("a", encoding="utf-8", errors="replace") as lf:
        lf.write("\n$ " + " ".join(cmd) + "\n")
        lf.flush()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                encoding="utf-8", errors="replace", env=env, **process_kwargs(below_normal=True))
        ae._attach_job_object(proc)
        for line in proc.stdout:
            lf.write(line)
            m = re.match(r"\s*(Collecting|Downloading|Successfully installed)\s*(\S*)", line)
            if m:
                INSTALL.update(detail=(m.group(1) + " " + m.group(2).split("/")[-1])[:160])
            if _STOP.is_set():
                proc.kill()
                break
        proc.wait()
    if _STOP.is_set():
        raise PainterError("Installation cancelled.")
    if proc.returncode != 0:
        raise PainterError("The add-on's Python parts could not be installed. Check the internet connection and try again "
                           "(details for support: install.log in the add-on folder).")


# ---------------------------------------------------------------- what to draw for a film

LOOK = ("flat vector cartoon illustration for an animated explainer video, clean bold dark outlines, flat colors, "
        "soft simple shading, friendly proportions")
PLAIN = "plain pure white background, no shadow, no floor, no text"
POSE_PROMPTS = [                                       # (file stem, what the reference becomes)
    ("talk_open", "standing facing the viewer, mouth wide open talking, arms down"),
    ("point", "pointing to the right with one arm stretched out, mouth closed"),
    ("point_open", "pointing to the right with one arm stretched out, mouth wide open talking"),
    ("shrug", "shrugging with both palms up, mouth closed"),
]
PLACES = {
    "office": "an office interior seen from the front, a desk, a big window with a city view, a plant, a shelf with folders",
    "city": "a city street seen from the front, sidewalk, a row of small shops and buildings, a lamp post, a few trees, daytime",
    "city_hall": "a city hall's grand hall seen from the front, columns, a flag, a wooden counter",
    "road": "a road going into the distance, fields and a few houses at the sides, traffic cones, daytime",
    "bank": "a bank hall seen from the front, counters with glass, a vault door in the back",
    "night": "a city street at night, lit windows, street lamps, dark blue sky",
    "hospital": "a hospital corridor seen from the front, a reception desk, doors, a bench",
    "school": "a school classroom seen from the front, a blackboard, desks, windows",
    "shop": "a small shop seen from inside, shelves with goods, a counter with a cash register",
    "home": "a block of flats seen from the yard, balconies, a bench, a tree, daytime",
    "site": "a building site, an unfinished concrete building, a crane, piles of bricks, fences",
}
_COLORS = [(0, "red"), (25, "orange"), (50, "yellow"), (90, "green"), (165, "teal"), (205, "blue"), (260, "purple"), (320, "pink"), (360, "red")]


def color_word(hexc: str) -> str:
    try:
        r, g, b = (int(str(hexc).lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return ""
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.18:
        return "white" if l > 0.85 else "light grey" if l > 0.6 else "grey" if l > 0.3 else "dark grey" if l > 0.15 else "black"
    name = next(n for deg, n in _COLORS if h * 360 <= deg + 12)
    return ("dark " if l < 0.32 else "light " if l > 0.72 else "") + name


def describe(c: dict) -> str:
    """A character's look in words, from its description (chars.make): the same words every time."""
    woman = bool(c.get("female"))
    role = str(c.get("role") or "").strip()
    hair = {"bald": "bald", "buzz": "very short", "short": "short", "side": "side-parted", "spiky": "spiky", "bob": "bob-cut",
            "curly": "curly", "ponytail": "ponytail", "long": "long"}.get(c.get("hair_style"), "short")
    outfit = {"suit": "suit with a tie", "blazer": "blazer", "dress": "dress", "shirt": "shirt", "hoodie": "hoodie",
              "vest": "work clothes with an orange safety vest", "sweater": "sweater", "coat": "white doctor's coat over blue scrubs"
              }.get(c.get("outfit"), "shirt")
    bits = [("a woman" if woman else "a man"), (f"({role})" if role and role not in ("narrator",) else ""),
            {"thin": "slim", "heavy": "stout"}.get(c.get("build"), ""),
            (f"{color_word(c.get('hair', ''))} {hair} hair" if c.get("hair_style") != "bald" else "bald"),
            {"mustache": "a mustache", "stubble": "stubble", "full": "a full beard"}.get(c.get("beard"), ""),
            "glasses" if c.get("glasses") else "", f"{color_word(c.get('cloth', ''))} {outfit}",
            f"{color_word(c.get('pants', ''))} trousers" if c.get("outfit") != "dress" else "",
            "a yellow hard hat" if c.get("hat") == "hardhat" else ""]
    return ", ".join(b for b in bits if b)


def plan(film: dict, again: bool = False) -> list:
    """The pictures a film still needs: [{"out", "prompt", "ref" (the base picture of that character), "w", "h"}]
    (again: all of them anew)."""
    from .library import key_of
    root = art.root()
    wide = film.get("format") == "horizontal"
    out = []
    for name in sorted({s["bg"] for s in film["scenes"]} & set(PLACES)):
        p = root / "backgrounds" / (name + ("_wide" if wide else "") + ".png")
        if again or not p.is_file():
            out.append({"out": str(p), "prompt": f"Empty {PLACES[name]}, no people, {LOOK}, "
                        f"{'wide' if wide else 'vertical'} composition, no text, no letters, no signs", "ref": None,
                        "w": 1344 if wide else 768, "h": 768 if wide else 1344, "what": name})
    for key, c in film["cast"].items():
        d = root / "characters" / key_of(c.get("name") or key)
        base = d / "base.png"
        who = describe(c)
        if again or not base.is_file():
            out.append({"out": str(base), "prompt": f"Full body character, {who}, standing straight facing the viewer, arms "
                        f"down, mouth closed, the whole figure from head to shoes in the frame, {LOOK}, isolated on a {PLAIN}",
                        "ref": None, "w": 768, "h": 1344, "what": c.get("name") or key})
        for stem, pose in POSE_PROMPTS:
            p = d / (stem + ".png")
            if again or not p.is_file():
                out.append({"out": str(p), "prompt": f"The same character ({who}), same face, same clothes, same style, {pose}, "
                            f"full body, {PLAIN}", "ref": str(base), "w": 768, "h": 1344, "what": c.get("name") or key})
    return out


def start_paint(film: dict, job: str = "", again: bool = False) -> int:
    """Draws what the film still needs (a thread); the number of pictures to draw."""
    if not installed():
        raise PainterError("Install the picture add-on first.")
    with _LOCK:
        if PAINT["state"] == "running":
            raise PainterError("Pictures are being drawn for another cartoon. Wait until they are ready.")
        todo = plan(film, again)
        if not todo:
            return 0
        PAINT.update(state="running", done=0, total=len(todo), error="", what="", job=job)
    _PSTOP.clear()
    threading.Thread(target=_paint, args=(todo,), name="painter", daemon=True).start()
    return len(todo)


def cancel_paint() -> None:
    _PSTOP.set()


def _paint(todo: list) -> None:
    """The worker draws the pictures; if it stops on its own (the graphics card's driver, memory), it is started again
    for the pictures not drawn yet - up to three times - so one bad moment does not lose the rest."""
    from .. import auto_edit as ae, voice as vo
    work = ROOT / "work"
    left, done, tries, log, started = list(todo), 0, 0, [], time.time()
    try:
        work.mkdir(parents=True, exist_ok=True)
        while left:
            req = work / f"paint-{int(time.time())}.json"
            req.write_text(json.dumps({"model": str(MODEL), "pictures": left, "standin": standin()}), "utf-8")
            env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONPATH=str(SITE), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
            cmd = [sys.executable if standin() else vo._python(), str(WORKER), str(req)]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                    encoding="utf-8", errors="replace", env=env, **process_kwargs(below_normal=True))
            ae._attach_job_object(proc)
            got = 0
            for line in proc.stdout:
                log = (log + [line.rstrip()])[-40:]
                m = re.match(r"PIC (\d+) (.*)", line)
                if m:
                    got = int(m.group(1))
                    PAINT.update(done=done + got, what=m.group(2).strip()[:80])
                if _PSTOP.is_set():
                    proc.kill()
                    break
            proc.wait()
            log.append(f"(the worker ended with {proc.returncode})")
            (work / "last.log").write_text("\n".join(log), "utf-8")
            if _PSTOP.is_set():
                raise PainterError("Stopped. The pictures drawn so far are kept.")
            done += got
            left = [x for x in left if not (Path(x["out"]).is_file() and Path(x["out"]).stat().st_mtime >= started - 1)]
            if proc.returncode == 0 and not left:
                break
            tries += 1
            if tries > 3 or (got == 0 and tries > 1):
                raise PainterError("The picture model stopped (details for support: work/last.log in the add-on folder).")
        PAINT.update(state="done", done=done)
    except Exception as exc:
        PAINT.update(state="failed", error=str(exc)[:300])
    finally:
        art.forget()


def remove_pictures(film: dict) -> int:
    """The film's places and people drawn by the add-on (or put there by hand) taken away: drawn by the program again."""
    from .library import key_of
    root, n = art.root(), 0
    for name in {s["bg"] for s in film["scenes"]}:
        for p in (root / "backgrounds").glob(name + ".*"):
            p.unlink(missing_ok=True)
            n += 1
        for p in (root / "backgrounds").glob(name + "_wide.*"):
            p.unlink(missing_ok=True)
            n += 1
    for key, c in film["cast"].items():
        d = root / "characters" / key_of(c.get("name") or key)
        if d.is_dir():
            n += len(list(d.iterdir()))
            shutil.rmtree(d, ignore_errors=True)
    art.forget()
    return n

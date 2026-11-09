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
DEPTH = ROOT / "models" / "depth"                      # (how far each part of a picture is: the camera moves in depth)
DEPTH_REPO, DEPTH_REV = "depth-anything/Depth-Anything-V2-Small-hf", "5426e4f0f36572d16453bbda7a8389317b1bef99"  # Apache-2.0
DEPTH_PARTS = ("config.json", "model.safetensors", "preprocessor_config.json")
# the better quality (an option: much slower): the undistilled klein (20 steps with guidance; the installed one's text
# model and image coder) and a model that looks at each picture for broken bodies and letters
BASE = ROOT / "models" / "flux-base"
BASE_REPO, BASE_REV = "black-forest-labs/FLUX.2-klein-base-4B", "a3b4f4849157f664bdbc776fd7453c2783562f4d"   # Apache-2.0
BASE_PARTS = ("transformer/config.json", "transformer/diffusion_pytorch_model.safetensors")
CHECK = ROOT / "models" / "check"
CHECK_REPO, CHECK_REV = "Qwen/Qwen3-VL-8B-Instruct-GGUF", "f982a07559d4a2f6c8744d840bf6fccab30eea96"        # Apache-2.0
CHECK_PARTS = ("Qwen3VL-8B-Instruct-Q4_K_M.gguf", "mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf")
QUALITIES = ("fast", "better")
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
    ("blink", "standing facing the viewer, arms down, mouth closed, both eyes closed (blinking), otherwise exactly the same"),
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


STORY = ("hand-painted 2D animated film still, soft painterly textures, warm muted colors, gentle light, cinematic "
         "composition, storybook feeling, no text, no letters, no captions, no watermark")


def _depth_out(pic: Path) -> str:
    return str(pic.with_name(pic.stem + "_depth.png"))


def story_ref(name: str) -> Path:
    """Where a story's person is drawn once (all their scenes are drawn from it, so they look the same)."""
    from .library import key_of
    return art.root() / "story" / key_of(name) / "ref.png"


def plan(film: dict, again: bool = False, only: str = "") -> list:
    """The pictures a film still needs: [{"out", "prompt", "refs" (pictures it is drawn from), "w", "h", "depth" (where
    its depth map goes)}] and depth maps still missing ({"out", "depth_of"}). again: all of them anew; only: one scene's
    picture (its background's name), drawn anew."""
    from .library import key_of
    root = art.root()
    wide = film.get("format") == "horizontal"
    W_, H_ = (1344, 768) if wide else (768, 1344)
    out = []
    names = {s["bg"] for s in film["scenes"]}
    for name in sorted(names & set(PLACES)):
        p = root / "backgrounds" / (name + ("_wide" if wide else "") + ".png")
        if (again or not p.is_file()) and not only:
            out.append({"out": str(p), "prompt": f"Empty {PLACES[name]}, no people, {LOOK}, "
                        f"{'wide' if wide else 'vertical'} composition, no text, no letters, no signs", "refs": [],
                        "w": W_, "h": H_, "what": name, "depth": _depth_out(p)})
    story = [s for s in film["scenes"] if s.get("draw")]
    if story:                                              # a story: its people drawn once, then every scene from them
        refs = {}
        for key, c in film["cast"].items():
            if not c.get("looks"):
                continue
            p = story_ref(c.get("name") or key)
            refs[key] = str(p)
            if (again or not p.is_file()) and not only:
                out.append({"out": str(p), "prompt": f"Character sheet: {c['looks']}, full body, standing, front view, "
                            f"plain white background, {STORY}", "refs": [], "w": 768, "h": 1344,
                            "what": c.get("name") or key, "seed": 11})
        for i, s in enumerate(story):
            p = root / "backgrounds" / (s["bg"] + ("_wide" if wide else "") + ".png")
            if only and s["bg"] != only:
                continue
            if again or only or not p.is_file():
                who = "; ".join(f"{film['cast'][k].get('name') or k}: {film['cast'][k]['looks']}" for k in s.get("with") or []
                                if film["cast"].get(k, {}).get("looks"))
                out.append({"out": str(p), "prompt": f"{s['draw']}" + (f". The people: {who}" if who else "") + f", {STORY}",
                            "refs": [refs[k] for k in s.get("with") or [] if k in refs],
                            "w": W_, "h": H_, "what": f"scene {i + 1}", "depth": _depth_out(p),
                            "seed": int(s.get("seed") or 0) or 7 + i})
    if film.get("on_screen") is not False and not only:   # (a voice-over film shows nobody standing in it)
        for key, c in film["cast"].items():
            d = root / "characters" / key_of(c.get("name") or key)
            base = d / "base.png"
            who = describe(c)
            if again or not base.is_file():
                out.append({"out": str(base), "prompt": f"Full body character, {who}, standing straight facing the viewer, arms "
                            f"down, mouth closed, the whole figure from head to shoes in the frame, {LOOK}, isolated on a {PLAIN}",
                            "refs": [], "w": 768, "h": 1344, "what": c.get("name") or key})
            for stem, pose in POSE_PROMPTS:
                p = d / (stem + ".png")
                if again or not p.is_file():
                    out.append({"out": str(p), "prompt": f"The same character ({who}), same face, same clothes, same style, {pose}, "
                                f"full body, {PLAIN}", "refs": [str(base)], "w": 768, "h": 1344, "what": c.get("name") or key})
    if not only:                                           # (pictures there already, without their depth yet)
        drawing = {x["out"] for x in out}
        for name in sorted(names):
            b = art.background(name, wide=wide)
            if b and str(b) not in drawing and not art.depth_of(b) and not b.stem.endswith("_depth"):
                out.append({"out": _depth_out(b), "depth_of": str(b), "what": name})
    return out


def start_paint(film: dict, job: str = "", again: bool = False, only: str = "", seed: int = 0) -> int:
    """Draws what the film still needs (a thread); the number of pictures to draw. only: one scene's picture anew (with
    another seed: another picture of the same words)."""
    if not installed():
        raise PainterError("Install the picture add-on first.")
    with _LOCK:
        if PAINT["state"] == "running":
            raise PainterError("Pictures are being drawn for another cartoon. Wait until they are ready.")
        todo = plan(film, again, only)
        if seed:
            for x in todo:
                x["seed"] = seed
        if not todo:
            return 0
        PAINT.update(state="running", done=0, total=len(todo), error="", what="", job=job)
    _PSTOP.clear()
    q = film.get("quality") if film.get("quality") in QUALITIES else "fast"
    threading.Thread(target=_paint, args=(todo, q), name="painter", daemon=True).start()
    return len(todo)


def cancel_paint() -> None:
    _PSTOP.set()


def _run_worker(left: list, quality: str, work: Path, state: dict) -> None:
    """The worker draws `left`; if it stops on its own (the graphics card's driver, memory), it is started again for the
    pictures not drawn yet - up to three times - so one bad moment does not lose the rest."""
    from .. import auto_edit as ae, voice as vo
    tries, log, started = 0, [], time.time()
    while left:
        while (vo._CURRENT.get("id") and vo._CURRENT.get("step") != "waiting for pictures"   # (one waiting for us:
               and not _PSTOP.is_set()):                                                       # not waited for)
            PAINT.update(what="waiting for the voice-over or cartoon being made")   # (the card is theirs first)
            time.sleep(2)
        req = work / f"paint-{int(time.time())}.json"
        req.write_text(json.dumps({"model": str(MODEL), "pictures": left, "standin": standin(), "site": str(SITE),
                                   "depth_model": str(DEPTH), "quality": quality, "base": str(BASE)}), "utf-8")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
        env.pop("PYTHONPATH", None)
        # (like the voice add-on's worker: without the program's own packages (-S), only the add-on's folder - a
        # mix of the two crashed in the graphics card's code on the owner's PC)
        cmd = ([sys.executable, str(WORKER), str(req)] if standin() else
               [vo._python(), "-S", "-E", "-B", "-X", "utf8", str(WORKER), str(req)])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                encoding="utf-8", errors="replace", env=env, **process_kwargs(below_normal=True))
        ae._attach_job_object(proc)
        got = 0
        for line in proc.stdout:
            log = (log + [line.rstrip()])[-40:]
            m = re.match(r"PIC (\d+) (.*)", line)
            if m:
                got = int(m.group(1))
                PAINT.update(done=state["done"] + got, what=m.group(2).strip()[:80])
            if _PSTOP.is_set():
                proc.kill()
                break
        proc.wait()
        log.append(f"(the worker ended with {proc.returncode})")
        (work / "last.log").write_text("\n".join(log), "utf-8")
        if _PSTOP.is_set():
            raise PainterError("Stopped. The pictures drawn so far are kept.")
        state["done"] += got
        left = [x for x in left if not (Path(x["out"]).is_file() and Path(x["out"]).stat().st_mtime >= started - 1)
                and not x.get("depth_of")]                 # (a depth map that failed: not a reason to start again)
        if proc.returncode == 0 and not left:
            break
        tries += 1
        if tries > 3 or (got == 0 and tries > 1):
            raise PainterError("The picture model stopped (details for support: work/last.log in the add-on folder).")


def _paint(todo: list, quality: str = "fast") -> None:
    """Draws the pictures; in the better quality each picture of people is then looked at by a model that sees pictures
    (extra or missing limbs, twisted bodies, broken faces, letters) and drawn again with another seed up to three times.
    What is still wrong is written down (checks.json) and shown on the film's page."""
    work = ROOT / "work"
    left, state = list(todo), {"done": 0}
    try:
        work.mkdir(parents=True, exist_ok=True)
        if any(x.get("depth") or x.get("depth_of") for x in left) and not standin():
            try:
                PAINT.update(what="the depth model (once, 100 MB)")
                _ensure_depth()
            except Exception as exc:                       # (no depth: the pictures still drawn, the camera as before)
                (work / "depth.log").write_text(repr(exc), "utf-8")
                left = [dict(x, depth=None) for x in left if not x.get("depth_of")]
        if quality == "better" and not standin():
            try:
                PAINT.update(what="the better quality's models (once, 13 GB)")
                _ensure(BASE_REPO, BASE_REV, BASE, BASE_PARTS)
                _ensure(CHECK_REPO, CHECK_REV, CHECK, CHECK_PARTS)
            except PainterError:
                raise
            except Exception as exc:
                raise PainterError(f"The better quality's models could not be downloaded: {exc}")
        _run_worker(left, quality, work, state)
        if quality == "better":
            looked = [x for x in todo if not x.get("depth_of") and x.get("check", True)]
            report = _checks()
            for rnd in range(3):
                PAINT.update(what=f"looking at the pictures ({rnd + 1}/3)")
                bad = []
                for x in _look(looked):
                    report[x["out"]] = x["problems"]
                    if x["problems"]:
                        bad.append(x)
                _save_checks(report)
                if not bad:
                    break
                again = [dict(x["item"], seed=int(x["item"].get("seed") or 7) + 1000 * (rnd + 1),
                              prompt=_unwritten(x["item"]["prompt"]) if any(str(q).startswith("letters") for q in x["problems"])
                              else x["item"]["prompt"]) for x in bad]
                PAINT.update(total=PAINT["total"] + len(again))
                _run_worker(again, quality, work, state)
                looked = [x["item"] for x in bad]
        PAINT.update(state="done", done=state["done"])
    except Exception as exc:
        PAINT.update(state="failed", error=str(exc)[:300])
    finally:
        art.forget()


# the checker is asked twice: it writes out what it can read (letters are drawn wrong by the picture model, and the
# words of a film are put on the picture by the program, never drawn - any it reads is a fault: measured on the owner's
# PC it read every garbled title and calendar), then it goes through the people one by one (weaker: it passed most
# broken hands it was shown - a second look, not a guarantee)
ASK_TEXT = ("Write out every letter, word or number you can see anywhere in this picture, exactly as it looks, even if it "
            "is garbled. If there is none, answer NONE.")
ASK_BODIES = ("For each person in this picture, one line: who they are, how many arms, hands and legs you can see, and "
              "whether any hand, finger, arm, leg or face looks deformed, melted, doubled, extra, missing or bent in an "
              "impossible way. Be strict and look closely; small figures too. End with a last line: VERDICT: OK or "
              "VERDICT: BROKEN.")


def _unwritten(prompt: str) -> str:
    """A picture's words with nothing to write on it: quoted words, 'the word X', 'labeled/reading ...' taken out, and
    blank surfaces asked for (the model draws letters wherever words ask for them - the same words drew them again)."""
    t = re.sub(r"[\"“”«»][^\"“”«»]{0,60}[\"“”«»]", "", str(prompt or ""))
    t = re.sub(r"(?i)\b(with|showing|reading|that reads|labell?ed|written|marked|titled|saying)\b[^,.;]{0,40}?\b(word|words|text|letters|title|sign)\b[^,.;]*", "", t)
    t = re.sub(r"(?i:\b(labell?ed|reading|that reads|saying|marked|titled|written|with)\b)\s+[A-Z][A-Z' -]{1,30}\b", "", t)
    t = re.sub(r"(?i)\b(calendar|book|page|paper|sign|poster|letter|newspaper)\b", r"blank \1", t)
    return re.sub(r"\s+", " ", t).strip(" ,") + ", every surface plain and blank, absolutely no writing, no letters, no numbers"


def _checks() -> dict:
    try:
        return json.loads((art.root() / "checks.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save_checks(report: dict) -> None:
    p = art.root() / "checks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".part")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    os.replace(tmp, p)


def problems_of(pic) -> list:
    """What the picture check found wrong in a picture (empty: nothing, or not looked at)."""
    return list(_checks().get(str(pic)) or [])


def _verdict(text: str, bodies: str) -> list:
    """The problems from the checker's two answers ([] for a good picture)."""
    probs = []
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if t and not re.fullmatch(r"(?i)[\W_]*none[\W_]*", t) and re.search(r"[^\W_]", t):
        probs.append("letters drawn in the picture: " + t[:80])
    m = re.search(r"VERDICT\s*:\s*(OK|BROKEN)", str(bodies or ""), re.I)
    if m and m.group(1).upper() == "BROKEN":
        why = [ln.strip(" -*") for ln in str(bodies).splitlines() if re.search(r"(?i)deform|extra|missing|melt|doubl|twist|impossib", ln)
               and not re.search(r"(?i)\bno (deform|extra|missing)|none|normal", ln)]
        probs.append(("a broken body: " + why[0][:90]) if why else "a broken body")
    return probs


def _look(items: list) -> list:
    """Each picture looked at by the checking model (Qwen3-VL 8B through the story writer's llama.cpp server):
    [{"item", "out", "problems"}]. MEDIAENGINE_PAINTER=standin: a stand-in that finds an extra hand in pictures whose
    words say 'juggling' the first time (the checks)."""
    import base64
    out = []
    if standin():
        for x in items:
            seen = x["out"] + ".seen"
            bad = "juggling" in x.get("prompt", "") and not os.path.exists(seen)
            Path(seen).write_text("1", "utf-8")
            out.append({"item": x, "out": x["out"], "problems": ["an extra hand"] if bad else []})
        return out
    from . import writer as W
    model = CHECK / CHECK_PARTS[0]
    srv = W.open_server(lambda: _PSTOP.is_set(), track=False, log=ROOT / "work" / "check.log", model=model,
                        extra=["--mmproj", str(CHECK / CHECK_PARTS[1])])
    try:
        for x in items:
            if _PSTOP.is_set():
                raise PainterError("Stopped. The pictures drawn so far are kept.")
            if not os.path.isfile(x["out"]):
                continue
            b64 = base64.b64encode(Path(x["out"]).read_bytes()).decode("ascii")
            said = []
            try:
                for ask in (ASK_TEXT, ASK_BODIES):
                    msg = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                                                        {"type": "text", "text": ask}]}]
                    r = srv.chat(msg, max_tokens=400, temperature=0.0, seed=1, stop=lambda: _PSTOP.is_set(), timeout=600)
                    said.append(r.get("text") or "")
                probs = _verdict(said[0], said[1])
            except W.WriterError as exc:
                if str(exc) == "Stopped.":
                    raise PainterError("Stopped. The pictures drawn so far are kept.")
                probs = []
            out.append({"item": x, "out": x["out"], "problems": probs})
    finally:
        srv.close()
    return out


def _ensure(repo: str, rev: str, folder: Path, parts: tuple) -> None:
    """A model's files, downloaded once (checked against their pinned version)."""
    from .. import auto_edit as ae, voice as vo
    files = [f for f in vo._hf_files(repo, rev) if f[0] in parts]
    if len(files) < len(parts):
        raise PainterError("The model's files were not found where they should be.")
    for name, size, kind, want in files:
        dst = folder / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if vo._file_ok(dst, size, kind, want):
            continue
        part = dst.with_name(dst.name + ".part")
        PAINT.update(what=f"downloading {Path(name).name} ({size / 1e9:.1f} GB, once)")
        ae._fetch_resumable(f"https://huggingface.co/{repo}/resolve/{rev}/{name}", part, size, lambda h: None, stop=_PSTOP)
        if not vo._file_ok(part, size, kind, want):
            part.unlink(missing_ok=True)
            raise PainterError("A downloaded model file is not the exact file.")
        ae._replace_retry(part, dst)


def better_ready() -> bool:
    return all((BASE / n).is_file() for n in BASE_PARTS) and all((CHECK / n).is_file() for n in CHECK_PARTS)


def _ensure_depth() -> None:
    """The depth model's three files, downloaded once (checked against their pinned version)."""
    from .. import auto_edit as ae, voice as vo
    files = [f for f in vo._hf_files(DEPTH_REPO, DEPTH_REV) if f[0] in DEPTH_PARTS]
    DEPTH.mkdir(parents=True, exist_ok=True)
    for name, size, kind, want in files:
        dst = DEPTH / name
        if vo._file_ok(dst, size, kind, want):
            continue
        part = dst.with_name(dst.name + ".part")
        ae._fetch_resumable(f"https://huggingface.co/{DEPTH_REPO}/resolve/{DEPTH_REV}/{name}", part, size, lambda h: None,
                            stop=_PSTOP)
        if not vo._file_ok(part, size, kind, want):
            part.unlink(missing_ok=True)
            raise PainterError("The depth model's file is not the exact file.")
        ae._replace_retry(part, dst)


def depth_ready() -> bool:
    return all((DEPTH / n).is_file() for n in DEPTH_PARTS)


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
        for p in list((root / "backgrounds").glob(name + "_depth.*")) + list((root / "backgrounds").glob(name + "_wide_depth.*")):
            p.unlink(missing_ok=True)
    for key, c in film["cast"].items():
        d = root / "characters" / key_of(c.get("name") or key)
        if d.is_dir():
            n += len(list(d.iterdir()))
            shutil.rmtree(d, ignore_errors=True)
    art.forget()
    return n

"""Video decoding on the graphics card - used only where THIS PC has shown that it gives exactly the same picture.

Most of the time of an AI reel from 4K videos is decoding them (the owner's PC, b117: cutting the 90 previews of 13
drone videos took 15 min on the processor). Graphics cards decode H.264 and HEVC (the standards define the decoded
picture exactly), but drivers and the way FFmpeg hands the frames over differ, so nothing is assumed:

  "Check this PC" -> "Test the graphics card" makes three short 4K test clips (H.264, HEVC, HEVC 10-bit), cuts a
  piece of each as the engine does - with the processor and with every hardware method this FFmpeg offers - and
  compares every frame (MD5 of the full picture and of the 960-px preview) and the time.

A method is used (MEDENG_HWACCEL for the engine: previews and full-quality pieces, plain cuts only) when every frame
was identical in every clip and it was clearly faster; a different FFmpeg or graphics driver means testing again.
Any FFmpeg error with it: the engine makes the same cut on the processor. Local only, nothing is sent anywhere.
"""
from __future__ import annotations

import hashlib, os, subprocess, threading, time
from pathlib import Path

# hardware methods worth trying, best first (Windows: Direct3D 11 works with Intel, AMD and NVIDIA; then the vendors')
CANDIDATES = ("d3d11va", "cuda", "qsv", "d3d12va", "dxva2", "vaapi", "videotoolbox")
MIN_SPEEDUP = 1.3            # less is not worth a second code path
PREVIEW_VF = "scale=w='min(960,iw)':h=-2"     # the engine's preview size (p11_folder_to_reel_r3.PREVIEW_VF)
# name, the processor decoder's picture format, encoder settings - like phone and drone footage: H.264 High profile
# (CABAC, B-frames), HEVC Main and Main 10 (B-frames), a keyframe every 2 s
CLIPS = (
    ("h264_4k.mp4", "yuv420p", ["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-crf", "23", "-g", "60",
                                "-bf", "2", "-pix_fmt", "yuv420p"]),
    ("hevc_4k.mp4", "yuv420p", ["-c:v", "libx265", "-preset", "superfast", "-crf", "26",
                                "-x265-params", "log-level=error:keyint=60:bframes=3", "-pix_fmt", "yuv420p", "-tag:v", "hvc1"]),
    ("hevc10_4k.mp4", "yuv420p10le", ["-c:v", "libx265", "-preset", "superfast", "-crf", "26",
                                      "-x265-params", "log-level=error:keyint=60:bframes=3", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1"]),
)
NATIVE = {name: pix for name, pix, _ in CLIPS}

_LOCK = threading.Lock()
_STATE = {"running": False, "started": 0.0, "step": "", "result": None}


def _run(cmd, timeout=300):
    from .platform_adapter import process_kwargs
    return subprocess.run(cmd, **process_kwargs({"capture_output": True, "timeout": timeout}, below_normal=False))


def ffmpeg_version(ff: str) -> str:
    try:
        return _run([ff, "-hide_banner", "-version"], 30).stdout.decode("utf-8", "replace").splitlines()[0].strip()
    except Exception:
        return ""


def offered_methods(ff: str) -> list[str]:
    """Hardware methods this FFmpeg build knows (not yet whether this PC has the hardware)."""
    try:
        out = _run([ff, "-hide_banner", "-hwaccels"], 30).stdout.decode("utf-8", "replace").split()
    except Exception:
        return []
    return [m for m in CANDIDATES if m in out]


def gpu_names() -> list[str]:
    """Graphics adapters and their driver versions (Windows), e.g. 'NVIDIA GeForce RTX 3060 - 32.0.15.6094'."""
    if os.name != "nt":
        return []
    try:
        cp = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                   "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                   "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + ' - ' + $_.DriverVersion }"], 30)
        return [x.strip() for x in cp.stdout.decode("utf-8", "replace").splitlines() if x.strip()]
    except Exception:
        return []


def make_clips(ff: str, folder: Path) -> list[Path]:
    """The test clips (made once, ~10 s each; kept in the data folder)."""
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for name, _pix, enc in CLIPS:
        dst = folder / name
        if not dst.is_file() or dst.stat().st_size < 10000:
            tmp = folder / (name + ".part.mp4")
            cp = _run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=3840x2160:rate=30",
                       "-t", "4", "-vf", "noise=alls=6:allf=t", *enc, "-an", str(tmp)], 600)
            if cp.returncode != 0 or not tmp.is_file():
                tmp.unlink(missing_ok=True)
                continue                      # this FFmpeg cannot make it (no x265): tested with the others
            os.replace(tmp, dst)
        out.append(dst)
    return out


def _cut(ff: str, clip: Path, hw: str | None, vf: str) -> tuple[float, str | None, str]:
    """A piece cut as the engine cuts (seek, 2.5 s), frames as MD5s: (seconds, MD5 of all frame MD5s or None, error).
    With the card, its frames are first turned into the processor decoder's format - as the engine does (run_cut)."""
    if hw:
        vf = f"format={NATIVE.get(clip.name, 'yuv420p')}," + vf
    cmd = [ff, "-hide_banner", "-loglevel", "error", *(["-hwaccel", hw] if hw else []), "-ss", "1.0", "-i", str(clip),
           "-t", "2.5", "-map", "0:v:0", "-vf", vf, "-f", "framemd5", "-"]
    t0 = time.perf_counter()
    try:
        cp = _run(cmd, 300)
    except Exception as exc:
        return time.perf_counter() - t0, None, str(exc)[:200]
    dt = time.perf_counter() - t0
    if cp.returncode != 0:
        return dt, None, cp.stderr.decode("utf-8", "replace").strip()[-300:]
    lines = [ln for ln in cp.stdout.decode("ascii", "replace").splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 30:
        return dt, None, f"only {len(lines)} frames"
    md5s = [ln.split(",")[-1].strip() for ln in lines]
    return dt, hashlib.md5("\n".join(md5s).encode()).hexdigest(), ""


def _parallel(ff: str, clip: Path, hw: str | None, vf: str, k: int) -> tuple[float, bool]:
    """k cuts at once (a build cuts several videos' moments at the same time): (seconds for all, all good)."""
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.perf_counter()
    with ThreadPoolExecutor(k) as ex:
        outs = list(ex.map(lambda _: _cut(ff, clip, hw, vf), range(k)))
    return time.perf_counter() - t0, all(md5 and not err for _, md5, err in outs)


def run_test(ff: str, folder: Path, step=lambda s: None) -> dict:
    """Processor vs every offered hardware method on every test clip. Never raises."""
    t_start = time.time()
    res = {"tested_at": time.strftime("%Y-%m-%d %H:%M"), "ffmpeg": ffmpeg_version(ff), "gpu": gpu_names(), "methods": {}, "use": ""}
    try:
        step("making 4K test clips")
        clips = make_clips(ff, folder)
        res["clips"] = [c.name for c in clips]
        if not clips:
            res["error"] = "no test clip could be made"
            return res
        views = {"full": "format=yuv420p", "preview": PREVIEW_VF + ",format=yuv420p"}
        sw = {}
        for c in clips:
            for vk, vf in views.items():
                step(f"processor: {c.name}")
                times, md5 = [], None
                for _ in range(2):           # the faster of two runs (the first one also reads the file from disk)
                    dt, md5, err = _cut(ff, c, None, vf)
                    times.append(dt)
                sw[(c.name, vk)] = (min(times), md5)
        clips = [c for c in clips if all(sw[(c.name, vk)][1] for vk in views)]     # the processor itself must cut it
        for m in offered_methods(ff):
            mres = {"clips": {}, "identical": True, "decoded": 0}
            sw_total = hw_total = 0.0
            for c in clips:
                cres = {}
                for vk, vf in views.items():
                    step(f"{m}: {c.name}")
                    times, md5, err = [], None, ""
                    for _ in range(2):
                        dt, md5, err = _cut(ff, c, m, vf)
                        times.append(dt)
                        if err:
                            break
                    s_t, s_md5 = sw[(c.name, vk)]
                    same = (md5 is not None and md5 == s_md5)
                    cres[vk] = {"sw_s": round(s_t, 3), "hw_s": round(min(times), 3), "identical": same, "error": err or None}
                    if err:
                        continue                 # cannot decode this one here: the engine cuts it on the processor
                    if not same:
                        mres["identical"] = False
                    sw_total += s_t; hw_total += min(times)
                mres["clips"][c.name] = cres
                if all(not v["error"] for v in cres.values()):
                    mres["decoded"] += 1
            mres["speedup_single"] = round(sw_total / hw_total, 2) if hw_total > 0 else 0.0
            mres["speedup"] = mres["speedup_single"]
            if mres["identical"] and mres["decoded"]:
                # under load, as in a build (several moments cut at once while the AI looks at other videos): the
                # card takes the decoding off the processor - one cut alone on an idle 16-thread processor says little
                k = max(2, min(4, (os.cpu_count() or 4) // 4))
                sw_par = hw_par = 0.0
                for c in clips:
                    cr = mres["clips"].get(c.name) or {}
                    if any(v.get("error") for v in cr.values()):
                        continue
                    step(f"{m}: {c.name} x{k}")
                    if (c.name, "par") not in sw:
                        sw[(c.name, "par")] = _parallel(ff, c, None, views["preview"], k)
                    st, sok = sw[(c.name, "par")]
                    ht, hok = _parallel(ff, c, m, views["preview"], k)
                    if sok and hok:
                        sw_par += st; hw_par += ht
                        cr["loaded"] = {"cuts_at_once": k, "sw_s": round(st, 3), "hw_s": round(ht, 3)}
                if hw_par > 0:
                    mres["speedup_loaded"] = round(sw_par / hw_par, 2)
                    mres["speedup"] = mres["speedup_loaded"]
            res["methods"][m] = mres
        res["use"] = choose(res)
        for c in clips:                      # ~100 MB of test video: made again for the next test
            c.unlink(missing_ok=True)
    except Exception as exc:
        res["error"] = f"{type(exc).__name__}: {exc}"[:300]
    finally:
        res["seconds"] = round(time.time() - t_start, 1)
    return res


def choose(res: dict) -> str:
    """The method to use: identical frames everywhere it decoded, the H.264 clip decoded, clearly faster; best first."""
    best, best_speed = "", 0.0
    for m in CANDIDATES:
        r = (res.get("methods") or {}).get(m)
        if not r or not r.get("identical") or not r.get("decoded"):
            continue
        h264 = (r.get("clips") or {}).get("h264_4k.mp4") or {}
        if not h264 or any(v.get("error") for v in h264.values()):
            continue
        if float(r.get("speedup") or 0) >= MIN_SPEEDUP and float(r["speedup"]) > best_speed:
            best, best_speed = m, float(r["speedup"])
    return best


# ---------------------------------------------------------------- remembered result (settings) and the app's use of it
def saved() -> dict:
    try:
        from .config import load_config
        return dict((load_config().get("auto_edit") or {}).get("hw_decode") or {})
    except Exception:
        return {}


def save(res: dict) -> None:
    from .config import update_config
    update_config(lambda cfg: cfg.setdefault("auto_edit", {}).__setitem__("hw_decode", res))


def stale(r: dict, ff: str | None) -> bool:
    """FFmpeg or the graphics driver changed since the test: test again before using the card."""
    if not ff or r.get("ffmpeg") != ffmpeg_version(ff):
        return True
    return bool(os.name == "nt" and r.get("gpu") and r.get("gpu") != gpu_names_cached())


def proven_kinds(r: dict, m: str) -> list[str]:
    """The kinds of video the method decoded identically, both views, without an error ('h264', 'hevc', 'hevc10'):
    only those go to the card (a 10-bit clip it could not decode in the test is never sent to it)."""
    out = []
    for name, kind in (("h264_4k.mp4", "h264"), ("hevc_4k.mp4", "hevc"), ("hevc10_4k.mp4", "hevc10")):
        c = ((r.get("methods") or {}).get(m) or {}).get("clips", {}).get(name) or {}
        if c and all(v.get("identical") and not v.get("error") for v in c.values()):
            out.append(kind)
    return out


def method_for_engine(ff: str | None) -> str:
    """The method the engine may use now, or '' (not tested, not proven, turned off, or FFmpeg / driver changed)."""
    r = saved()
    m = str(r.get("use") or "")
    if not m or r.get("off") or stale(r, ff):
        return ""
    return m


_GPU_CACHE: dict = {}


def gpu_names_cached() -> list[str]:
    """gpu_names() once per run of the app (PowerShell takes a second)."""
    if "v" not in _GPU_CACHE:
        _GPU_CACHE["v"] = gpu_names()
    return _GPU_CACHE["v"]


def start(ff: str, folder: Path) -> bool:
    """The test in the background (Check this PC can be left meanwhile)."""
    with _LOCK:
        if _STATE["running"]:
            return False
        _STATE.update(running=True, started=time.time(), step="", result=None)

    def step(s):
        with _LOCK:
            _STATE["step"] = s

    def go():
        res = run_test(ff, folder, step)
        if saved().get("off"):
            res["off"] = True                # "Do not use the graphics card" stays the owner's choice
        try:
            save(res)
        except Exception:
            pass
        _GPU_CACHE.pop("v", None)
        with _LOCK:
            _STATE.update(running=False, result=res)
    threading.Thread(target=go, daemon=True, name="hwdecode-test").start()
    return True


def state() -> dict:
    with _LOCK:
        st = dict(_STATE)
    st["elapsed_s"] = round(time.time() - st["started"], 1) if st["running"] else 0.0
    return st


def summary(res: dict, ff: str | None = None) -> tuple[bool, str]:
    """(used, one line for Check this PC)."""
    if not res:
        return False, "not tested yet - press 'Test the graphics card' below (about a minute, your videos are not used)"
    if res.get("off"):
        return False, "turned off"
    if res.get("error") and not res.get("methods"):
        return False, "not used: the test could not be finished - test again"
    m = res.get("use") or ""
    if m and ff is not None and stale(res, ff):
        return False, "not used: FFmpeg or the graphics driver changed since the test - test again"
    if m:
        sp = (res.get("methods") or {}).get(m, {}).get("speedup")
        return True, f"used ({m}): {sp}x faster than the processor, every frame identical"
    meths = res.get("methods") or {}
    if not meths:
        return False, "not used: this FFmpeg cannot decode video on a graphics card"
    decoded = [r for r in meths.values() if r.get("decoded")]
    if not decoded:
        return False, "not used: the graphics card cannot decode these videos here"
    same = [r for r in decoded if r.get("identical")]
    if not same:
        return False, "not used: the picture is not exactly the same as the processor's"
    best = max(float(r.get("speedup") or 0) for r in same)
    return False, f"not used: not faster than the processor ({best}x)"

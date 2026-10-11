"""Assemble a self-contained Windows package of the MediaEngine candidate (run on Windows, CPython 3.11).

  python mediaengine/tools/build_windows_package.py <out_dir>

Layout (side-by-side with a stable D:\\Archivist install; nothing outside its own folder is touched except
its own desktop shortcut "MediaEngine RC"):

  MediaEngine-<version>/
    Start MediaEngine.vbs      one obvious launch (no console)
    README.txt  BUILD.txt      what this is / exact source commit
    launcher.py  app/  requirements.txt  version.txt  port.txt (8775)  shortcut_name.txt
    .venv/Scripts/             relocatable CPython 3.11 + pinned packages (python.exe / pythonw.exe)
                               + app-local Microsoft VC++ runtime DLLs (OpenCV / onnxruntime need them)

The folder name has no build id on purpose: extracting a newer build over the old folder keeps data/,
projects and exports. The build id is in BUILD.txt and in the CI artifact name.

Model weights are NOT included; the app finds FAST_LOCAL in a neighbouring Archivist install or lets the
user choose the folder (exact hashes verified before use).
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys, sysconfig
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # mediaengine/
PORT = 8775
SHORTCUT = "MediaEngine RC"


def version() -> str:
    for line in (ROOT / "app" / "archivist" / "config.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("VERSION = "):
            return line.split('"')[1]
    raise SystemExit("VERSION not found")


def main(out_dir: Path) -> None:
    if os.name != "nt":
        raise SystemExit("Build on Windows (relocatable CPython is copied from the running interpreter)")
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Build with CPython 3.11 (the pinned 3.12.42 environment)")
    ver = version()
    pkg = out_dir / f"MediaEngine-{ver}"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    # 1. relocatable CPython 3.11 at .venv/Scripts (the launcher looks for .venv\Scripts\pythonw.exe)
    base = Path(sys.base_prefix)
    py_dir = pkg / ".venv" / "Scripts"
    shutil.copytree(base, py_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "Doc", "test", "tests", "idlelib", "turtledemo",
                                                                 "tcl", "tkinter", "Tools", "site-packages"))
    # app-local VC++ runtime: a clean Windows PC without the redistributable cannot load cv2 / onnxruntime
    sysdir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    vc = []
    for dll in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "concrt140.dll"):
        if not (py_dir / dll).exists() and (sysdir / dll).exists():
            shutil.copy2(sysdir / dll, py_dir / dll)
        if (py_dir / dll).exists():
            vc.append(dll)
    (py_dir / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    py = py_dir / "python.exe"
    subprocess.run([str(py), "-m", "ensurepip", "--default-pip"], check=True, capture_output=True)
    subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "-q",
                    "-r", str(ROOT / "requirements.txt")], check=True)

    # 2. app + launcher + markers
    shutil.copytree(ROOT / "app", pkg / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "requirements.txt", pkg / "requirements.txt")
    shutil.copy2(ROOT / "app" / "archivist" / "launcher_v2.py", pkg / "launcher.py")
    (pkg / "version.txt").write_text(ver, encoding="utf-8")
    (pkg / "port.txt").write_text(str(PORT), encoding="utf-8")
    (pkg / "shortcut_name.txt").write_text(SHORTCUT, encoding="utf-8")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.platform_adapter import launcher_vbs_text   # the same file the app repairs at start
    (pkg / "Start MediaEngine.vbs").write_text(launcher_vbs_text(), encoding="utf-16")
    sha = os.environ.get("GITHUB_SHA") or subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (pkg / "BUILD.txt").write_text(f"MediaEngine {ver}\ncommit {sha}\nbuilt {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
                                   f"run {os.environ.get('GITHUB_RUN_ID', 'local')}\n", encoding="utf-8")
    (pkg / "README.txt").write_text(f"""MediaEngine {ver} (release candidate)

Start: double-click "Start MediaEngine.vbs". A MediaEngine window opens; a desktop shortcut
"{SHORTCUT}" is created for next time. No console, no Python install needed. The first start
can take a minute (Windows checks the new files). "Quit" in the top bar stops MediaEngine.

Newer build: Quit MediaEngine, then extract the new zip over this folder. Your projects,
data and exports stay.

Auto Edit: open "Auto Edit", choose a folder with your videos, pick Length / Format / Sound, press
"Create reel". Review the result, Accept it, then Export MP4 (saved to the Exports folder here).

AI model: if this folder sits next to an existing Archivist install (for example D:\\Archivist),
the FAST_LOCAL model is found automatically. Otherwise use "Choose model folder" on the Auto Edit page.
Without the model the app offers the clearly labelled "Technical only" mode.

This candidate runs on port {PORT} and keeps its own data, archive and exports inside this folder.
It does not change a stable Archivist install. To remove it: close the window and delete this folder
and the "{SHORTCUT}" desktop shortcut.
""", encoding="utf-8")

    # 3. manifest (outside the package folder: evidence, not user-facing)
    files = []
    for p in sorted(pkg.rglob("*")):
        if p.is_file() and ".venv" not in p.relative_to(pkg).parts:
            files.append({"path": str(p.relative_to(pkg)).replace("\\", "/"), "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    venv_bytes = sum(p.stat().st_size for p in (pkg / ".venv").rglob("*") if p.is_file())
    frozen = subprocess.run([str(py), "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    manifest = {"product": "MediaEngine", "version": ver, "commit": sha, "port": PORT, "shortcut": SHORTCUT, "python": sys.version.split()[0],
                "python_source": str(base), "vc_runtime_app_local": vc, "packages": frozen, "app_files": files, "venv_bytes": venv_bytes}
    (out_dir / f"MediaEngine-{ver}.manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"package": str(pkg), "version": ver, "app_files": len(files), "venv_mb": round(venv_bytes / 1e6, 1)}))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


TARGET_PLATFORMS = ("Windows", "macOS", "Android", "iOS")


def is_windows() -> bool:
    return os.name == "nt"


def process_kwargs(existing: dict | None = None, *, detached: bool = False, below_normal: bool = True, hidden: bool = True) -> dict:
    kw = dict(existing or {})
    if not is_windows():
        return kw
    flags = int(kw.get("creationflags", 0) or 0)
    if hidden:
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if detached:
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    if below_normal:
        flags |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    kw["creationflags"] = flags
    if hidden and "startupinfo" not in kw:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        si.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kw["startupinfo"] = si
    return kw


def python_executable(home: Path, *, windowless: bool = True) -> Path:
    home = Path(home)
    if is_windows():
        preferred = home / ".venv" / "Scripts" / ("pythonw.exe" if windowless else "python.exe")
        fallback = home / ".venv" / "Scripts" / "python.exe"
        return preferred if preferred.exists() else (fallback if fallback.exists() else Path(sys.executable))
    for p in (home / ".venv" / "bin" / "python3", home / ".venv" / "bin" / "python"):
        if p.exists():
            return p
    return Path(sys.executable)


def set_background_priority() -> None:
    """Preserve the accepted Windows background-priority behavior."""
    if not is_windows():
        return
    try:
        import ctypes
        below_normal_priority_class = 0x00004000
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), below_normal_priority_class)
    except Exception:
        pass
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")


def install_launchers(home: Path) -> None:
    """Repair the current platform launcher. Windows is the only validated desktop adapter today."""
    if not is_windows():
        return
    home = Path(home)
    try:
        src = Path(__file__).resolve().parent / "launcher_v2.py"
        root_launcher = home / "launcher.py"
        if src.exists():
            shutil.copy2(src, root_launcher)
        wrapper_dir = home / "launcher"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / "ArchivistLauncher.pyw"
        wrapper.write_text(
            "import runpy, pathlib\nrunpy.run_path(str(pathlib.Path(__file__).resolve().parents[1]/'launcher.py'), run_name='__main__')\n",
            encoding="utf-8",
        )
        vbs = home / "Archivist.vbs"
        vbs.write_text(
            'Set s=CreateObject("WScript.Shell")\r\n'
            'root=CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)\r\n'
            's.Run Chr(34) & root & "\\.venv\\Scripts\\pythonw.exe" & Chr(34) & " " & Chr(34) & root & "\\launcher.py" & Chr(34),0,False\r\n',
            encoding="utf-8",
        )
        maker = home / "data" / "make_shortcut.vbs"
        maker.parent.mkdir(parents=True, exist_ok=True)
        maker.write_text(
            'Set sh=CreateObject("WScript.Shell")\r\n'
            'desktop=sh.SpecialFolders("Desktop")\r\n'
            'Set sc=sh.CreateShortcut(desktop & "\\Archivist.lnk")\r\n'
            'sc.TargetPath="wscript.exe"\r\n'
            'sc.Arguments=Chr(34) & "' + str(vbs).replace('"', '""') + '" & Chr(34)\r\n'
            'sc.WorkingDirectory="' + str(home).replace('"', '""') + '"\r\n'
            'sc.Description="Archivist"\r\n'
            'sc.Save\r\n',
            encoding="utf-8",
        )
        subprocess.run(["wscript.exe", str(maker)], timeout=15, **process_kwargs(detached=True))
    except Exception:
        pass


def detach_from_legacy_console_if_needed(home: Path) -> bool:
    if not is_windows() or os.environ.get("ARCHIVIST_V2_CHILD") == "1":
        return False
    if Path(sys.executable).name.lower() != "python.exe":
        return False
    pyw = Path(sys.executable).with_name("pythonw.exe")
    if not pyw.exists():
        return False
    env = os.environ.copy()
    env["ARCHIVIST_V2_CHILD"] = "1"
    env["ARCHIVIST_HOME"] = str(home)
    main = Path(__file__).resolve().parents[1] / "main.py"
    args = [str(pyw), str(main)]
    if os.environ.get("ARCHIVIST_SUPPRESS_BROWSER") == "1":
        args.append("--no-browser")
    else:
        args.append("--open-browser")
    subprocess.Popen(args, cwd=str(home), env=env, close_fds=True, **process_kwargs(detached=True))
    return True


def spawn_app_launcher(home: Path, mode: str) -> None:
    if not is_windows():
        raise RuntimeError("App restart/update adapter is not implemented for this platform yet")
    home = Path(home)
    exe = python_executable(home, windowless=True)
    launcher = home / "launcher.py"
    if not exe.exists() or not launcher.exists():
        raise RuntimeError("Permanent launcher is missing")
    subprocess.Popen(
        [str(exe), str(launcher), "--no-browser", "--update" if mode == "update" else "--restart"],
        cwd=str(home),
        close_fds=True,
        **process_kwargs(detached=True),
    )


def default_archive_root() -> str:
    """Return the platform default only; user configuration remains authoritative."""
    if is_windows() and Path("D:/").exists():
        return r"D:\\MediaArchive"
    return str(Path.home() / "Videos" / "MediaArchive")


def filesystem_capabilities() -> dict:
    return {
        "adapter": "windows_pathlib" if is_windows() else "portable_pathlib",
        "implemented": True,
        "validated": is_windows(),
        "configurable_roots": True,
        "atomic_replace": True,
        "default_archive_strategy": "platform_adapter",
        "path_style": "windows" if is_windows() else "posix",
    }


def secret_store_capabilities() -> dict:
    from .secret_store import capabilities
    return capabilities()


def background_work_capabilities() -> dict:
    return {
        "adapter": "desktop_local_threads_processes" if is_windows() else "not_implemented",
        "implemented": is_windows(),
        "validated": is_windows(),
        "long_running_local_jobs": is_windows(),
        "mobile_os_managed_constraints": not is_windows(),
    }


def macos_adapter_contract() -> dict:
    """Declare the macOS target honestly without claiming unvalidated support."""
    return {
        "platform": "macOS",
        "declaration_version": 1,
        "support_status": "contract_only",
        "support_claimed": False,
        "real_hardware_validated": False,
        "real_mac_gate": "pending",
        "filesystem": {
            "target_adapter": "macos_pathlib",
            "implementation_status": "portable_contract_present",
            "validated": False,
        },
        "secret_store": {
            "target_adapter": "macos_keychain",
            "implementation_status": "not_implemented",
            "validated": False,
        },
        "background_work": {
            "target_adapter": "macos_local_processes",
            "implementation_status": "not_implemented",
            "validated": False,
        },
        "app_control": {
            "target_adapter": "macos",
            "implementation_status": "not_implemented",
            "validated": False,
        },
        "desktop_launcher": {
            "target_adapter": "macos",
            "implementation_status": "not_implemented",
            "validated": False,
        },
        "required_real_mac_checks": [
            "install_launch",
            "filesystem_default_archive_and_atomic_replace",
            "keychain_write_read_delete",
            "background_job_cancel_restart",
            "launcher_restart_update_lifecycle",
            "no_windows_subprocess_keys",
        ],
    }


def platform_capabilities() -> dict:
    import platform
    system = platform.system() or "Unknown"
    machine = platform.machine() or "Unknown"
    filesystem = filesystem_capabilities()
    secret_store = secret_store_capabilities()
    background_work = background_work_capabilities()
    return {
        "system": system,
        "machine": machine,
        "windows_validated": is_windows(),
        "targets": list(TARGET_PLATFORMS),
        "app_control_adapter": "windows" if is_windows() else "not_implemented",
        "desktop_launcher_adapter": "windows" if is_windows() else "not_implemented",
        "filesystem_adapter": filesystem["adapter"],
        "secret_store_adapter": secret_store["adapter"],
        "background_work_adapter": background_work["adapter"],
        "filesystem": filesystem,
        "secret_store": secret_store,
        "background_work": background_work,
        "macos_contract": macos_adapter_contract(),
    }

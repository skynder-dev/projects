from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


TARGET_PLATFORMS = ("Windows", "macOS", "Android", "iOS")


def is_windows() -> bool:
    return os.name == "nt"


class keep_awake:
    """While a long build or conversion runs, Windows must not go to sleep (the screen may still turn off).
    Per-thread flag (SetThreadExecutionState): set and cleared in the thread that does the work. No-op elsewhere."""
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001

    def __enter__(self):
        self.ok = False
        if os.name == "nt":
            try:
                import ctypes
                self.ok = bool(ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED))
            except Exception:
                self.ok = False
        return self

    def __exit__(self, *exc):
        if self.ok:
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            except Exception:
                pass
        return False


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


def launcher_vbs_text() -> str:
    """Start the launcher with the bundled runtime, no console. -s -E: ignore other Python installs' settings.
    -B: never write bytecode into the program folder (compiled at build time; the folder stays as installed)."""
    return ('Set s=CreateObject("WScript.Shell")\r\n'
            'root=CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)\r\n'
            's.Run Chr(34) & root & "\\.venv\\Scripts\\pythonw.exe" & Chr(34) & " -B -s -E " & Chr(34) & root & "\\launcher.py" & Chr(34),0,False\r\n')


# ---- Windows shortcuts (.lnk) through IShellLinkW --------------------------------------------------------------
# WScript.Shell's CreateShortcut stores paths in the ANSI code page: a release in a folder such as
# "D:\\Видео\\MediaEngine" got a shortcut to "D:\\?????\\MediaEngine" on an English Windows (seen in CI).
# The shell's own Unicode interface has no such limit.
_CLSID_SHELLLINK = "{00021401-0000-0000-C000-000000000046}"
_IID_ISHELLLINKW = "{000214F9-0000-0000-C000-000000000046}"
_IID_IPERSISTFILE = "{0000010B-0000-0000-C000-000000000046}"


def _com_call(obj, index: int, restype, *args):
    import ctypes
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *[type(a) for a in args])
    return proto(vtbl[index])(obj, *args)


def _shell_link_session(fn):
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

    ole32 = ctypes.OleDLL("ole32")

    def guid(text):
        g = GUID()
        ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(g))
        return g
    init = ctypes.windll.ole32.CoInitializeEx(None, 2)          # STA; S_FALSE if this thread already has COM
    link = ctypes.c_void_p()
    pf = ctypes.c_void_p()
    try:
        clsid, iid_link, iid_file = guid(_CLSID_SHELLLINK), guid(_IID_ISHELLLINKW), guid(_IID_IPERSISTFILE)
        ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid_link), ctypes.byref(link))   # CLSCTX_INPROC_SERVER
        _com_call(link, 0, ctypes.HRESULT, ctypes.c_void_p(ctypes.addressof(iid_file)), ctypes.c_void_p(ctypes.addressof(pf)))  # QueryInterface
        return fn(link, pf)
    finally:
        for o in (pf, link):
            if o.value:
                _com_call(o, 2, ctypes.c_ulong)              # Release
        if init in (0, 1):
            ctypes.windll.ole32.CoUninitialize()


_IID_IPROPERTYSTORE = "{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}"
_PKEY_APP_USER_MODEL_ID = ("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}", 5)


def _set_link_app_id(link, app_id: str) -> None:
    """System.AppUserModel.ID on the shortcut (what Setup's AppUserModelID does): Windows then names the app's
    notifications "MediaEngine". Errors come back as OSError (HRESULT) and are the caller's to ignore."""
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):          # vt + 3 reserved words + the 16-byte union (24 bytes on x64)
        _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                    ("p", ctypes.c_void_p), ("p2", ctypes.c_void_p)]

    ole32 = ctypes.OleDLL("ole32")
    iid = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p(_IID_IPROPERTYSTORE), ctypes.byref(iid))
    key = PROPERTYKEY()
    ole32.CLSIDFromString(ctypes.c_wchar_p(_PKEY_APP_USER_MODEL_ID[0]), ctypes.byref(key.fmtid))
    key.pid = _PKEY_APP_USER_MODEL_ID[1]
    text = ctypes.create_unicode_buffer(app_id)
    var = PROPVARIANT()
    var.vt = 31                                   # VT_LPWSTR; the store copies the text
    var.p = ctypes.cast(text, ctypes.c_void_p).value
    ps = ctypes.c_void_p()
    _com_call(link, 0, ctypes.HRESULT, ctypes.c_void_p(ctypes.addressof(iid)), ctypes.c_void_p(ctypes.addressof(ps)))  # QueryInterface
    try:
        _com_call(ps, 6, ctypes.HRESULT, ctypes.c_void_p(ctypes.addressof(key)), ctypes.c_void_p(ctypes.addressof(var)))  # SetValue
        _com_call(ps, 7, ctypes.HRESULT)                                                                                  # Commit
    finally:
        if ps.value:
            _com_call(ps, 2, ctypes.c_ulong)                                                                              # Release


def write_shell_link(lnk: Path, target: str, arguments: str = "", workdir: str = "", icon: str = "", description: str = "",
                     app_id: str = "") -> None:
    """Create or replace a Windows shortcut with full Unicode paths."""
    import ctypes

    def go(link, pf):
        W = ctypes.c_wchar_p
        _com_call(link, 20, ctypes.HRESULT, W(str(target)))                     # SetPath
        _com_call(link, 11, ctypes.HRESULT, W(str(arguments)))                  # SetArguments
        if workdir:
            _com_call(link, 9, ctypes.HRESULT, W(str(workdir)))                 # SetWorkingDirectory
        if description:
            _com_call(link, 7, ctypes.HRESULT, W(str(description)))             # SetDescription
        if icon:
            _com_call(link, 17, ctypes.HRESULT, W(str(icon)), ctypes.c_int(0))  # SetIconLocation
        if app_id:
            try:
                _set_link_app_id(link, app_id)
            except OSError:
                pass                                                            # a shortcut without the id still starts the app
        _com_call(pf, 6, ctypes.HRESULT, W(str(lnk)), ctypes.c_int(1))          # IPersistFile::Save
    _shell_link_session(go)


def read_shell_link(lnk: Path) -> dict:
    """{'target', 'arguments', 'workdir'} of a shortcut, read through the same Unicode interface."""
    import ctypes

    def go(link, pf):
        _com_call(pf, 5, ctypes.HRESULT, ctypes.c_wchar_p(str(lnk)), ctypes.c_ulong(0))   # IPersistFile::Load, STGM_READ
        out = {}
        for key, idx, extra in (("target", 3, True), ("workdir", 8, False), ("arguments", 10, False)):
            buf = ctypes.create_unicode_buffer(32768)
            if extra:   # GetPath(buf, cch, WIN32_FIND_DATAW* = NULL, SLGP_RAWPATH = 4)
                _com_call(link, idx, ctypes.HRESULT, ctypes.cast(buf, ctypes.c_void_p), ctypes.c_int(32768), ctypes.c_void_p(), ctypes.c_ulong(4))
            else:
                _com_call(link, idx, ctypes.HRESULT, ctypes.cast(buf, ctypes.c_void_p), ctypes.c_int(32768))
            out[key] = buf.value
        return out
    return _shell_link_session(go)


def _link_runs(lnk: Path, arguments: str) -> bool:
    """True when the shortcut already starts exactly this (wscript with these arguments)."""
    try:
        got = read_shell_link(lnk)
        return (str(got.get("arguments") or "").strip().lower() == arguments.strip().lower()
                and Path(str(got.get("target") or "")).name.lower() == "wscript.exe")
    except Exception:
        return False


def shell_folder(csidl: int) -> Path | None:
    """Desktop (0x10) or Start-menu Programs (0x02) of this user, wherever Windows / OneDrive put them."""
    import ctypes
    buf = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) != 0 or not buf.value:
        return None
    return Path(buf.value)


def autostart_link() -> Path | None:
    """The shortcut in this Windows user's Startup folder that starts MediaEngine at sign-in (the owner's choice in
    Settings; off unless he turns it on)."""
    if not is_windows():
        return None
    d = shell_folder(0x07)                                              # CSIDL_STARTUP
    return d / "MediaEngine.lnk" if d is not None else None


def autostart_on() -> bool:
    try:
        lnk = autostart_link()
        return bool(lnk and lnk.is_file())
    except Exception:
        return False


def _autostart_args(home: Path) -> str:
    return f'-B -s -E "{Path(home) / "launcher.py"}" --no-browser'


def set_autostart(home: Path, on: bool) -> bool:
    """Start this build at sign-in in the background (no window: the tray icon shows it runs, a reel queue left
    from before a restart goes on) - or not. Returns whether it is on now."""
    lnk = autostart_link()
    if lnk is None:
        return False
    if not on:
        lnk.unlink(missing_ok=True)
        return False
    home = Path(home)
    pyw = home / ".venv" / "Scripts" / "pythonw.exe"
    if not pyw.is_file() or not (home / "launcher.py").is_file():
        raise OSError("this MediaEngine is not an installed build")
    icon = home / "MediaEngine.ico"
    lnk.parent.mkdir(parents=True, exist_ok=True)
    write_shell_link(lnk, str(pyw), _autostart_args(home), str(home), str(icon) if icon.is_file() else "", "MediaEngine")
    return True


def sync_autostart(home: Path) -> None:
    """When start at sign-in is on, it starts the build that ran last (like the desktop shortcut)."""
    try:
        lnk = autostart_link()
        if lnk is None or not lnk.is_file():
            return
        got = read_shell_link(lnk)
        if str(got.get("arguments") or "").strip().lower() != _autostart_args(home).lower():
            set_autostart(home, True)
    except Exception:
        pass


def install_launchers(home: Path) -> None:
    """Repair the current platform launcher. Windows is the only validated desktop adapter today."""
    if not is_windows():
        return
    home = Path(home)
    side_by_side = (home / "port.txt").exists()
    try:
        src = Path(__file__).resolve().parent / "launcher_v2.py"
        root_launcher = home / "launcher.py"
        if src.exists() and not (root_launcher.is_file() and root_launcher.read_bytes() == src.read_bytes()):
            shutil.copy2(src, root_launcher)          # only when it differs: an installed folder stays untouched
        if side_by_side:
            # A side-by-side install (release candidate) has exactly one start file and never creates the
            # stable install's Archivist.vbs / launcher folder names.
            vbs = home / "Start MediaEngine.vbs"
        else:
            wrapper_dir = home / "launcher"
            wrapper_dir.mkdir(parents=True, exist_ok=True)
            wrapper = wrapper_dir / "ArchivistLauncher.pyw"
            wrapper.write_text(
                "import runpy, pathlib\nrunpy.run_path(str(pathlib.Path(__file__).resolve().parents[1]/'launcher.py'), run_name='__main__')\n",
                encoding="utf-8",
            )
            vbs = home / "Archivist.vbs"
        want = launcher_vbs_text().encode("utf-16")
        if not (vbs.is_file() and vbs.read_bytes() == want):
            vbs.write_bytes(want)
        # A side-by-side install ships shortcut_name.txt so it never repoints the stable "Archivist" shortcut.
        try:
            name = (home / "shortcut_name.txt").read_text(encoding="utf-8-sig").strip()
        except Exception:
            name = ""
        name = "".join(ch for ch in name if ch.isalnum() or ch in " ._-")[:60].strip()
        if side_by_side and (not name or name.lower() == "archivist"):
            name = "MediaEngine RC"
        name = name or "Archivist"
        icon = home / "MediaEngine.ico"
        wscript = str(Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "wscript.exe")
        try:
            desk = shell_folder(0x10)                                   # CSIDL_DESKTOPDIRECTORY
            if desk is None:
                raise OSError("desktop folder not found")
            write_shell_link(desk / f"{name}.lnk", wscript, f'"{vbs}"', str(home), str(icon) if icon.is_file() else "", name)
        except Exception:
            desk = None                                                 # fall back to the script below (ANSI paths only)
        if desk is not None:
            if side_by_side:
                # the Start-menu entry made by the installer follows the build started last, like the desktop shortcut;
                # a failure here must not send the (good) desktop shortcut through the ANSI fallback
                try:
                    progs = shell_folder(0x02)                          # CSIDL_PROGRAMS
                    sm = progs / "MediaEngine.lnk" if progs is not None else None
                    if sm is not None and sm.is_file() and not _link_runs(sm, f'"{vbs}"'):
                        # only when it points elsewhere; the app id (as Setup sets it) names MediaEngine in notifications
                        from .notify import AUMID_APP
                        write_shell_link(sm, wscript, f'"{vbs}"', str(home), str(icon) if icon.is_file() else "", "MediaEngine",
                                         app_id=AUMID_APP)
                except Exception:
                    pass
                sync_autostart(home)
            return
        # temp folder, not <home>\data: a side-by-side release folder must stay exactly as it was unpacked
        import tempfile
        maker = Path(tempfile.gettempdir()) / f"MediaEngine_make_shortcut_{os.getpid()}.vbs"
        # UTF-16 with BOM: wscript reads the script as Unicode (its shortcut object still stores ANSI paths).

        def point(var: str) -> str:
            return ('{0}.TargetPath="wscript.exe"\r\n'
                    '{0}.Arguments=Chr(34) & "{1}" & Chr(34)\r\n'
                    '{0}.WorkingDirectory="{2}"\r\n'.format(var, str(vbs).replace('"', '""'), str(home).replace('"', '""'))
                    + ('{0}.IconLocation="{1},0"\r\n'.format(var, str(icon).replace('"', '""')) if icon.is_file() else '')
                    + var + '.Save\r\n')
        text = ('Set sh=CreateObject("WScript.Shell")\r\n'
                'desktop=sh.SpecialFolders("Desktop")\r\n'
                'Set sc=sh.CreateShortcut(desktop & "\\' + name + '.lnk")\r\n'
                'sc.Description="' + name + '"\r\n' + point("sc"))
        if side_by_side:
            # the Start-menu entry made by the installer follows the build started last, like the desktop shortcut
            text += ('Set fso=CreateObject("Scripting.FileSystemObject")\r\n'
                     'sm=sh.SpecialFolders("Programs") & "\\MediaEngine.lnk"\r\n'
                     'If fso.FileExists(sm) Then\r\n'
                     'Set s2=sh.CreateShortcut(sm)\r\n' + point("s2") + 'End If\r\n')
        maker.write_text(text, encoding="utf-16")
        try:
            subprocess.run(["wscript.exe", str(maker)], timeout=15, **process_kwargs(detached=True))
        finally:
            maker.unlink(missing_ok=True)
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
    args = [str(pyw), "-B", "-s", "-E", str(main)]
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
        [str(exe), "-B", "-s", "-E", str(launcher), "--no-browser", "--update" if mode == "update" else "--restart"],
        cwd=str(home),
        close_fds=True,
        **process_kwargs(detached=True),
    )


def _is_fixed_drive(root: str) -> bool:
    """True only for a fixed local disk (never an SD card / USB stick / network drive)."""
    try:
        import ctypes
        return int(ctypes.windll.kernel32.GetDriveTypeW(str(root))) == 3  # DRIVE_FIXED
    except Exception:
        return False


def default_archive_root() -> str:
    """Return the platform default only; user configuration remains authoritative."""
    if is_windows() and Path("D:/").exists() and _is_fixed_drive("D:\\"):
        return "D:\\MediaArchive"
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

"""MediaEngine in the Windows notification area (tray): Open and Quit, like other programs.

Closing the MediaEngine window does not stop the program (a reel being built goes on); the icon shows that it runs,
"Open" brings its window back and "Quit" stops it. Plain Win32 through ctypes - no new package. Never raises: in a
session without a taskbar there is simply no icon (STATE says why).

The program's windows are the Edge app windows whose title ends with " · MediaEngine" (every page's title; the stable
Archivist install uses " · Archivist", a normal browser tab adds " - Microsoft Edge"), owned by msedge.exe.
"""
from __future__ import annotations

import os, subprocess, threading, time
from pathlib import Path

STATE = {"state": "off", "error": ""}          # off / starting / shown / no_taskbar / failed - for checks (/api/ping)
WINDOW_CLASS = "MediaEngineTray"
TITLE_SUFFIX = " · MediaEngine"
ID_OPEN, ID_QUIT = 1001, 1002                   # menu commands (a check can post WM_COMMAND with them)
_W = {}                                         # Win32 handles and callbacks of the tray thread (kept alive here)
_LOCK = threading.Lock()


def _api():
    """ctypes Win32 functions with exact argument types (64-bit handles must not be cut to int)."""
    if _W.get("api"):
        return _W["api"]
    import ctypes
    from ctypes import wintypes as wt
    u, k, s = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("shell32")
    LRESULT = wt.LPARAM
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
    ENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    class GUID(ctypes.Structure):
        _fields_ = [("a", wt.DWORD), ("b", wt.WORD), ("c", wt.WORD), ("d", ctypes.c_ubyte * 8)]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
                    ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", ctypes.c_wchar * 128),
                    ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", ctypes.c_wchar * 256),
                    ("uVersion", wt.UINT), ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wt.DWORD),
                    ("guidItem", GUID), ("hBalloonIcon", wt.HICON)]

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                    ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                    ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]

    def f(dll, name, res, *args):
        fn = getattr(dll, name); fn.restype = res; fn.argtypes = list(args); return fn

    a = {
        "ctypes": ctypes, "wt": wt, "WNDPROC": WNDPROC, "ENUMPROC": ENUMPROC, "NID": NOTIFYICONDATAW, "WC": WNDCLASSEXW,
        "DefWindowProcW": f(u, "DefWindowProcW", LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM),
        "RegisterClassExW": f(u, "RegisterClassExW", wt.ATOM, ctypes.POINTER(WNDCLASSEXW)),
        "CreateWindowExW": f(u, "CreateWindowExW", wt.HWND, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID),
        "RegisterWindowMessageW": f(u, "RegisterWindowMessageW", wt.UINT, wt.LPCWSTR),
        "GetMessageW": f(u, "GetMessageW", wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT),
        "TranslateMessage": f(u, "TranslateMessage", wt.BOOL, ctypes.POINTER(wt.MSG)),
        "DispatchMessageW": f(u, "DispatchMessageW", LRESULT, ctypes.POINTER(wt.MSG)),
        "PostMessageW": f(u, "PostMessageW", wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM),
        "PostQuitMessage": f(u, "PostQuitMessage", None, ctypes.c_int),
        "CreatePopupMenu": f(u, "CreatePopupMenu", wt.HMENU),
        "AppendMenuW": f(u, "AppendMenuW", wt.BOOL, wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR),
        "SetMenuDefaultItem": f(u, "SetMenuDefaultItem", wt.BOOL, wt.HMENU, wt.UINT, wt.UINT),
        "TrackPopupMenu": f(u, "TrackPopupMenu", ctypes.c_int, wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, wt.HWND, wt.LPVOID),
        "DestroyMenu": f(u, "DestroyMenu", wt.BOOL, wt.HMENU),
        "GetCursorPos": f(u, "GetCursorPos", wt.BOOL, ctypes.POINTER(wt.POINT)),
        "SetForegroundWindow": f(u, "SetForegroundWindow", wt.BOOL, wt.HWND),
        "ShowWindow": f(u, "ShowWindow", wt.BOOL, wt.HWND, ctypes.c_int),
        "IsIconic": f(u, "IsIconic", wt.BOOL, wt.HWND),
        "IsWindowVisible": f(u, "IsWindowVisible", wt.BOOL, wt.HWND),
        "LoadImageW": f(u, "LoadImageW", wt.HANDLE, wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT),
        "LoadIconW": f(u, "LoadIconW", wt.HICON, wt.HINSTANCE, wt.LPVOID),
        "GetSystemMetrics": f(u, "GetSystemMetrics", ctypes.c_int, ctypes.c_int),
        "SetTimer": f(u, "SetTimer", ctypes.c_size_t, wt.HWND, ctypes.c_size_t, wt.UINT, wt.LPVOID),
        "MessageBoxW": f(u, "MessageBoxW", ctypes.c_int, wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.UINT),
        "EnumWindows": f(u, "EnumWindows", wt.BOOL, ENUMPROC, wt.LPARAM),
        "GetClassNameW": f(u, "GetClassNameW", ctypes.c_int, wt.HWND, wt.LPWSTR, ctypes.c_int),
        "GetWindowTextW": f(u, "GetWindowTextW", ctypes.c_int, wt.HWND, wt.LPWSTR, ctypes.c_int),
        "GetWindowThreadProcessId": f(u, "GetWindowThreadProcessId", wt.DWORD, wt.HWND, ctypes.POINTER(wt.DWORD)),
        "GetModuleHandleW": f(k, "GetModuleHandleW", wt.HMODULE, wt.LPCWSTR),
        "OpenProcess": f(k, "OpenProcess", wt.HANDLE, wt.DWORD, wt.BOOL, wt.DWORD),
        "QueryFullProcessImageNameW": f(k, "QueryFullProcessImageNameW", wt.BOOL, wt.HANDLE, wt.DWORD, wt.LPWSTR,
                                        ctypes.POINTER(wt.DWORD)),
        "CloseHandle": f(k, "CloseHandle", wt.BOOL, wt.HANDLE),
        "Shell_NotifyIconW": f(s, "Shell_NotifyIconW", wt.BOOL, wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)),
    }
    _W["api"] = a
    return a


# ---- the program's windows ---------------------------------------------------------------------------------------
def is_app_window_title(title: str) -> bool:
    """A MediaEngine page shown in an Edge app window (not a browser tab, not the stable Archivist)."""
    t = str(title or "")
    return t.endswith(TITLE_SUFFIX) and t != TITLE_SUFFIX.strip() and "Microsoft" not in t


def app_windows() -> list:
    """Handles of the visible Edge app windows that show MediaEngine pages."""
    if os.name != "nt":
        return []
    a = _api(); ct = a["ctypes"]; wt = a["wt"]; found = []

    def exe_of(hwnd):
        pid = wt.DWORD(0); a["GetWindowThreadProcessId"](hwnd, ct.byref(pid))
        h = a["OpenProcess"](0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf = ct.create_unicode_buffer(1024); n = wt.DWORD(1024)
            return os.path.basename(buf.value).lower() if a["QueryFullProcessImageNameW"](h, 0, buf, ct.byref(n)) else ""
        finally:
            a["CloseHandle"](h)

    def each(hwnd, _):
        try:
            if not a["IsWindowVisible"](hwnd):
                return True
            cls = ct.create_unicode_buffer(64); a["GetClassNameW"](hwnd, cls, 64)
            if cls.value != "Chrome_WidgetWin_1":
                return True
            title = ct.create_unicode_buffer(512); a["GetWindowTextW"](hwnd, title, 512)
            if is_app_window_title(title.value) and exe_of(hwnd) == "msedge.exe":
                found.append(hwnd)
        except Exception:
            pass
        return True
    cb = a["ENUMPROC"](each)
    a["EnumWindows"](cb, 0)
    return found


def close_app_windows() -> int:
    """Close the program's windows (Quit closes them like any program does). Returns how many were asked to close."""
    try:
        a = _api(); ws = app_windows()
        for h in ws:
            a["PostMessageW"](h, 0x0010, 0, 0)                     # WM_CLOSE
        return len(ws)
    except Exception:
        return 0


def _edge_paths():
    env = os.environ
    for base in (env.get("LOCALAPPDATA"), env.get("PROGRAMFILES(X86)"), env.get("PROGRAMFILES")):
        if base:
            p = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if p.is_file():
                yield p


def show_window(url: str) -> str:
    """Bring the program's window to the front, or open one (an Edge app window, as the launcher does)."""
    try:
        a = _api(); ws = app_windows()
        if ws:
            h = ws[0]
            if a["IsIconic"](h):
                a["ShowWindow"](h, 9)                              # SW_RESTORE
            a["SetForegroundWindow"](h)
            return "focused"
    except Exception:
        pass
    for edge in _edge_paths():
        try:
            # normal priority (this process runs below normal; Edge must not inherit it - playback would stutter),
            # detached, cwd outside the program folder (as the launcher)
            subprocess.Popen([str(edge), f"--app={url}", "--start-maximized"], cwd=str(edge.parent), close_fds=True,
                             creationflags=0x00000008 | 0x00000020)   # DETACHED_PROCESS | NORMAL_PRIORITY_CLASS
            return "opened"
        except Exception:
            continue
    try:
        os.startfile(url)                                          # no Edge: the default browser
        return "browser"
    except Exception:
        return "failed"


# ---- the icon ----------------------------------------------------------------------------------------------------
def _menu_text(t: str) -> str:
    return str(t).replace("&", "&&")[:120]


def start(*, url: str, icon: Path, version: str, ru, status, busy, quit_app, hint_flag: Path | None = None) -> bool:
    """Show the icon (Windows only; a thread with its own message loop). ru() -> bool: Russian texts;
    status(ru) -> one line on what runs ('' = nothing); busy() -> what a Quit would stop ('' = nothing);
    quit_app() stops the program. hint_flag: a file that marks "the first-start hint was shown"."""
    if os.name != "nt" or os.environ.get("MEDIAENGINE_NO_TRAY") == "1":
        return False
    with _LOCK:
        if STATE["state"] in ("starting", "shown"):
            return True
        STATE.update(state="starting", error="")
    threading.Thread(target=_run, name="tray", daemon=True,
                     kwargs=dict(url=url, icon=Path(icon), version=version, ru=ru, status=status, busy=busy,
                                 quit_app=quit_app, hint_flag=hint_flag)).start()
    return True


def remove() -> None:
    """Take the icon away (before the process ends - else a dead icon stays until the mouse passes over it)."""
    try:
        nid = _W.get("nid")
        if nid is not None:
            a = _api()
            a["Shell_NotifyIconW"](2, a["ctypes"].byref(nid))       # NIM_DELETE
            _W["nid"] = None
            STATE["state"] = "off"
    except Exception:
        pass


def _run(*, url, icon, version, ru, status, busy, quit_app, hint_flag):
    try:
        a = _api(); ct = a["ctypes"]; wt = a["wt"]
        WM_TRAY = 0x8001                                         # WM_APP + 1
        taskbar_created = a["RegisterWindowMessageW"]("TaskbarCreated")
        hinst = a["GetModuleHandleW"](None)
        st = {"last_open": 0.0, "tip": "", "dialog": False, "added": False, "tries": 0}

        def texts():
            r = False
            try:
                r = bool(ru())
            except Exception:
                pass
            return r

        def tip_text():
            line = ""
            try:
                line = status(texts()) or ""
            except Exception:
                pass
            t = f"MediaEngine {version}".strip()
            return (t + ("\n" + line if line else ""))[:127]

        def notify(op, nid):
            return bool(a["Shell_NotifyIconW"](op, ct.byref(nid)))

        def add():
            nid = a["NID"](); nid.cbSize = ct.sizeof(a["NID"]); nid.hWnd = hwnd; nid.uID = 1
            nid.uFlags = 0x1 | 0x2 | 0x4                            # NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = WM_TRAY; nid.hIcon = hicon; st["tip"] = tip_text(); nid.szTip = st["tip"]
            if notify(0, nid):                                      # NIM_ADD
                _W["nid"] = nid; st["added"] = True; STATE.update(state="shown", error="")
                hint(nid)
                return True
            STATE.update(state="no_taskbar", error=f"Shell_NotifyIcon failed ({ct.get_last_error()})")
            return False

        def hint(nid):
            """Once: where the program is now, and how to quit it (Windows 11 hides new icons under the ^ arrow)."""
            try:
                if hint_flag is None or Path(hint_flag).exists():
                    return
                r = texts()
                nid.uFlags = 0x10                                    # NIF_INFO
                nid.szInfoTitle = "MediaEngine работает в трее" if r else "MediaEngine is in the tray"
                nid.szInfo = ("Закрытое окно не выключает программу. Выйти: правой кнопкой по значку MediaEngine → «Выход». "
                              "Если значка не видно, он под стрелкой ^ рядом с часами." if r else
                              "Closing the window does not stop the program. To quit: right-click the MediaEngine icon → Quit. "
                              "If the icon is not shown, it is under the ^ arrow next to the clock.")
                nid.dwInfoFlags = 0x1                                # NIIF_INFO
                notify(1, nid)                                       # NIM_MODIFY
                nid.uFlags = 0x1 | 0x2 | 0x4; nid.szInfo = ""; nid.szInfoTitle = ""
                Path(hint_flag).parent.mkdir(parents=True, exist_ok=True); Path(hint_flag).write_text(version, encoding="utf-8")
            except Exception:
                pass

        def do_open():
            if time.time() - st["last_open"] < 1.5:                 # a double click is two clicks: one window
                return
            st["last_open"] = time.time()
            show_window(url)

        def do_quit():
            r = texts(); reason = ""
            try:
                reason = busy() or ""
            except Exception:
                pass
            if reason:
                line = ""
                try:
                    line = status(r) or ""
                except Exception:
                    pass
                q = ((line or "Сейчас идёт работа.") + "\n\nВсё равно выйти? Собираемый ролик будет отмечен как прерванный "
                     "(повтор использует готовый анализ); задачи Библиотеки, конвертация и заказы продолжатся при "
                     "следующем запуске.") if r else ((line or reason) + "\n\nQuit anyway? A reel being made is marked "
                     "interrupted (Retry reuses its analysis); Library tasks, conversions and orders go on at the next start.")
                st["dialog"] = True
                try:
                    yes = a["MessageBoxW"](hwnd, q, "MediaEngine", 0x4 | 0x20 | 0x40000 | 0x10000) == 6   # YESNO|QUESTION|TOPMOST|FOREGROUND
                finally:
                    st["dialog"] = False
                if not yes:
                    return
            close_app_windows()
            remove()
            quit_app()

        def menu():
            r = texts(); hm = a["CreatePopupMenu"](); cmd = 0
            try:
                line = ""
                try:
                    line = status(r) or ""
                except Exception:
                    pass
                if line:
                    a["AppendMenuW"](hm, 0x1, 0, _menu_text(line))           # MF_GRAYED: what runs right now
                    a["AppendMenuW"](hm, 0x800, 0, None)                     # MF_SEPARATOR
                a["AppendMenuW"](hm, 0x0, ID_OPEN, "Открыть MediaEngine" if r else "Open MediaEngine")
                a["AppendMenuW"](hm, 0x800, 0, None)
                a["AppendMenuW"](hm, 0x0, ID_QUIT, "Выход" if r else "Quit")
                a["SetMenuDefaultItem"](hm, ID_OPEN, 0)
                pt = wt.POINT(); a["GetCursorPos"](ct.byref(pt))
                a["SetForegroundWindow"](hwnd)                       # else the menu does not close on a click elsewhere
                cmd = a["TrackPopupMenu"](hm, 0x0002 | 0x0100 | 0x0080, pt.x, pt.y, 0, hwnd, None)   # RIGHTBUTTON|RETURNCMD|NONOTIFY
                a["PostMessageW"](hwnd, 0, 0, 0)                     # WM_NULL (documented TrackPopupMenu quirk)
            finally:
                a["DestroyMenu"](hm)
            return cmd

        def wndproc(h, msg, wp, lp):
            try:
                if msg == WM_TRAY:
                    ev = lp & 0xFFFF
                    if not st["dialog"]:
                        if ev in (0x0202, 0x0203, 0x0405):           # left click, double click, click on the hint
                            do_open()
                        elif ev in (0x0205, 0x007B):                 # right click / context menu
                            cmd = menu()
                            if cmd == ID_OPEN:
                                do_open()
                            elif cmd == ID_QUIT:
                                do_quit()
                    return 0
                if msg == 0x0111:                                    # WM_COMMAND (also how a check presses the menu)
                    cmd = wp & 0xFFFF
                    if cmd == ID_OPEN:
                        do_open()
                    elif cmd == ID_QUIT and not st["dialog"]:
                        do_quit()
                    return 0
                if msg == 0x0113:                                    # WM_TIMER: the hover text follows the work
                    if not st["added"]:
                        st["tries"] += 1
                        if st["tries"] <= 60:                        # the taskbar may come up after this program
                            add()
                    elif _W.get("nid") is not None:
                        t = tip_text()
                        if t != st["tip"]:
                            nid = _W["nid"]; nid.uFlags = 0x4; nid.szTip = t; st["tip"] = t
                            notify(1, nid); nid.uFlags = 0x1 | 0x2 | 0x4
                    return 0
                if msg == taskbar_created and taskbar_created:       # Explorer restarted: the icon is gone, add it again
                    st["added"] = False; _W["nid"] = None; add()
                    return 0
                if msg == 0x0002:                                    # WM_DESTROY
                    a["PostQuitMessage"](0)
                    return 0
            except Exception as exc:
                STATE["error"] = f"{type(exc).__name__}: {exc}"[:300]
            return a["DefWindowProcW"](h, msg, wp, lp)

        proc = a["WNDPROC"](wndproc); _W["proc"] = proc             # kept: a collected callback crashes the process
        wc = a["WC"](); wc.cbSize = ct.sizeof(a["WC"]); wc.lpfnWndProc = proc; wc.hInstance = hinst
        wc.lpszClassName = WINDOW_CLASS
        if not a["RegisterClassExW"](ct.byref(wc)):
            raise OSError(f"RegisterClassEx failed ({ct.get_last_error()})")
        hwnd = a["CreateWindowExW"](0, WINDOW_CLASS, "MediaEngine tray", 0, 0, 0, 0, 0, None, None, hinst, None)
        if not hwnd:
            raise OSError(f"CreateWindowEx failed ({ct.get_last_error()})")
        _W["hwnd"] = hwnd
        size = a["GetSystemMetrics"](49) or 16                     # SM_CXSMICON
        hicon = a["LoadImageW"](None, str(icon), 1, size, size, 0x10) if Path(icon).is_file() else None   # IMAGE_ICON, LR_LOADFROMFILE
        if not hicon:
            hicon = a["LoadIconW"](None, ct.c_void_p(32512))         # IDI_APPLICATION
        add()
        a["SetTimer"](hwnd, 1, 5000, None)
        msg = wt.MSG()
        while a["GetMessageW"](ct.byref(msg), None, 0, 0) > 0:
            a["TranslateMessage"](ct.byref(msg)); a["DispatchMessageW"](ct.byref(msg))
    except Exception as exc:
        STATE.update(state="failed", error=f"{type(exc).__name__}: {exc}"[:300])

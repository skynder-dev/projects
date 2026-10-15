"""A Windows notification when a long build has finished, so the page need not be watched (an AI reel from a folder
of 4K videos took an hour on the owner's PC). Local only: Windows' own notifications, no network, no account.

Shown under the name "MediaEngine" when the Start-menu shortcut made by Setup carries the app id (Setup from build
b102 on); otherwise under "Windows PowerShell", which Windows always accepts. A click opens the reel's page.
Off with auto_edit.notify = false in the settings (Settings page checkbox)."""
from __future__ import annotations

import os, subprocess, threading
from pathlib import Path
from xml.sax.saxutils import escape

AUMID_APP = "MediaEngine.Desktop"       # the same id is set on the Start-menu shortcut by Setup (mediaengine_setup.iss)
AUMID_POWERSHELL = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
MIN_SECONDS = 60                         # a build that took less was watched anyway

_PS = (
    "$ErrorActionPreference='Stop';"
    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
    "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
    "$x = New-Object Windows.Data.Xml.Dom.XmlDocument; $x.LoadXml($env:ME_TOAST_XML);"
    "$t = New-Object Windows.UI.Notifications.ToastNotification $x;"
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:ME_TOAST_APP).Show($t)"
)


def toast_xml(title: str, text: str, url: str = "") -> str:
    launch = f' activationType="protocol" launch="{escape(url, {chr(34): "&quot;"})}"' if url else ""
    return (f"<toast{launch}><visual><binding template=\"ToastGeneric\"><text>{escape(title)}</text>"
            f"<text>{escape(text)}</text></binding></visual></toast>")


def _shortcut_has_app_id() -> bool:
    """The Start-menu shortcut Setup made carries AUMID_APP (stored inside the .lnk as UTF-16 text)."""
    base = os.environ.get("APPDATA")
    if not base:
        return False
    lnk = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "MediaEngine.lnk"
    try:
        return AUMID_APP.encode("utf-16-le") in lnk.read_bytes()
    except OSError:
        return False


def app_id() -> str:
    return AUMID_APP if _shortcut_has_app_id() else AUMID_POWERSHELL


def show(title: str, text: str, url: str = "", timeout_s: float = 20) -> bool:
    """Shows the notification now (Windows only). Never raises; False when it could not be shown."""
    if os.name != "nt":
        return False
    try:
        from .platform_adapter import process_kwargs
        env = dict(os.environ, ME_TOAST_XML=toast_xml(title, text, url), ME_TOAST_APP=app_id())
        cp = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _PS],
                            env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout_s,
                            **process_kwargs({}, below_normal=False))
        return cp.returncode == 0
    except Exception:
        return False


def enabled() -> bool:
    try:
        from .config import load_config
        return (load_config().get("auto_edit") or {}).get("notify", True) is not False
    except Exception:
        return True


def reel_finished(project_title: str, ok: bool, elapsed_s: float, url: str, ru: bool, prepared: bool = False) -> bool:
    """In the background (never holds up the next build): True when a notification was started. prepared: a
    "Prepare in advance" job (the videos were analysed; no reel yet)."""
    if not enabled() or float(elapsed_s or 0) < MIN_SECONDS:
        return False
    if prepared:
        title = (("Видео подготовлены" if ru else "Your videos are prepared") if ok else
                 ("Подготовка не удалась" if ru else "Preparing the videos failed"))
    elif ok:
        title = "Ролик готов" if ru else "Your reel is ready"
    else:
        title = "Ролик не собрался" if ru else "The reel could not be made"
    text = (project_title or "MediaEngine") + (" · нажми, чтобы открыть" if ru else " · click to open")
    threading.Thread(target=show, args=(title, text, url), daemon=True, name="notify").start()
    return True

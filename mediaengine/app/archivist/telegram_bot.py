"""The owner's phone, through his own Telegram bot: what he shares to the bot (a link, a topic, a short video) goes
into the Inbox (inbox.py) on this PC, and the bot says when a download started from it is finished.

Off until the owner pastes his bot's token (Settings → Phone): he makes the bot himself with @BotFather - free, no
other account. MediaEngine then asks Telegram for new messages (long polling, api.telegram.org over HTTPS): nothing on
this PC is opened to the internet. Only ONE chat is served - the one that sent the pairing code shown in Settings;
every other chat is ignored. The token is kept in the Windows credential store (a file in the data folder elsewhere),
never written to a log. Nothing is published; the bot only answers the owner.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("MEDENG_TELEGRAM_API") or "https://api.telegram.org"
SECRET = "telegram/bot_token"
MAX_FILE = 20 * 1024 * 1024           # what Telegram lets a bot download
_TOKEN_RE = re.compile(r"^[0-9]{5,12}:[A-Za-z0-9_-]{30,60}$")
_STATE: dict = {"thread": None, "stop": threading.Event(), "error": "", "seen_at": "", "running": False}
_LOCK = threading.Lock()


class BotError(Exception):
    pass


# ---------------------------------------------------------------- settings and the token

def _cfg() -> dict:
    from .config import load_config
    try:
        return dict(load_config().get("telegram") or {})
    except Exception:
        return {}


def _set(**kw) -> None:
    from .config import update_config
    update_config(lambda cfg: cfg.setdefault("telegram", {}).update(kw))


def _token_file() -> Path:
    from .config import HOME
    return HOME / "telegram" / "token"


def _windows_store() -> bool:
    return os.name == "nt" and not os.environ.get("MEDENG_TELEGRAM_TOKEN_FILE")


def _save_token(token: str) -> None:
    if _windows_store():
        from . import secret_store
        secret_store.set_secret(SECRET, token)
    else:
        p = _token_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(token, "utf-8")
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass


def _load_token() -> str:
    try:
        if _windows_store():
            from . import secret_store
            return str(secret_store.get_secret(SECRET) or "")
        return _token_file().read_text("utf-8").strip()
    except Exception:
        return ""


def _drop_token() -> None:
    try:
        if _windows_store():
            from . import secret_store
            secret_store.delete_secret(SECRET)
        else:
            _token_file().unlink(missing_ok=True)
    except Exception:
        pass


def status() -> dict:
    c = _cfg()
    return {"configured": bool(c.get("bot")) and bool(_load_token()), "bot": c.get("bot") or "",
            "paired": bool(c.get("chat_id")), "chat": c.get("chat_name") or "", "code": c.get("code") or "",
            "running": bool(_STATE["running"]), "error": _STATE["error"], "seen_at": _STATE["seen_at"]}


# ---------------------------------------------------------------- talking to Telegram

def _call(method: str, params: dict | None = None, token: str = "", timeout: float = 20) -> object:
    token = token or _load_token()
    if not token:
        raise BotError("The bot is not set up.")
    req = urllib.request.Request(f"{API}/bot{token}/{method}", json.dumps(params or {}).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = {"ok": False, "description": f"HTTP {exc.code}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise BotError("Telegram could not be reached: " + str(getattr(exc, "reason", exc))[:120])
    if not isinstance(data, dict) or not data.get("ok"):
        raise BotError(str((data or {}).get("description") or "Telegram refused the request")[:200])
    return data.get("result")


def _ru() -> bool:
    try:
        from . import i18n
        return i18n.ui_language() == "ru"
    except Exception:
        return False


def _say(key: str, **kw) -> str:
    ru = _ru()
    t = {
        "paired": ("Готово: этот чат подключён к MediaEngine на компьютере. Присылай сюда ссылки на видео, темы и короткие "
                   "видео — всё попадёт во «Входящие».",
                   "Done: this chat is connected to MediaEngine on your PC. Send links to videos, topics and short videos "
                   "here - they go into the Inbox."),
        "need_code": ("Чтобы подключить этот чат, отправь код из MediaEngine (Настройки → Телефон): /start 123456",
                      "To connect this chat, send the code from MediaEngine (Settings → Phone): /start 123456"),
        "help": ("Пришли ссылку на видео или профиль — она попадёт во «Входящие» MediaEngine. Пришли текст — это тема для "
                 "сюжета. Короткое видео (до 20 МБ) — сохранится в «Скачанные». /status — что делает компьютер.",
                 "Send a link to a video or a profile - it goes into MediaEngine's Inbox. Send text - a topic for a story. "
                 "A short video (up to 20 MB) is saved into Downloaded. /status - what the PC is doing."),
        "links": ("Во «Входящих»: {n}. Открой MediaEngine → Входящие.", "In the Inbox: {n}. Open MediaEngine → Inbox."),
        "topic": ("Тема во «Входящих».", "The topic is in the Inbox."),
        "file": ("Видео сохранено и лежит во «Входящих»: {name}", "The video is saved and in the Inbox: {name}"),
        "too_big": ("Это видео больше 20 МБ: Telegram не отдаёт ботам такие файлы. Пришли ссылку на него или перекинь дома.",
                    "This video is over 20 MB: Telegram does not give such files to bots. Send a link to it, or copy it at home."),
        "file_failed": ("Видео не удалось сохранить: {why}", "The video could not be saved: {why}"),
        "dl_done": ("Готово: скачано видео — {n}. MediaEngine → Скачать по ссылке.", "Done: {n} video(s) downloaded. MediaEngine → Download by a link."),
        "dl_failed": ("Не скачалось: {why}", "Not downloaded: {why}"),
        "status": ("Компьютер: {what}", "The PC: {what}"),
        "idle": ("ничего не делает", "nothing running"),
    }[key]
    return (t[0] if ru else t[1]).format(**kw)


def send(text: str) -> bool:
    """A message to the owner's paired chat (False when the bot is not set up or Telegram is not reachable)."""
    chat = _cfg().get("chat_id")
    if not chat:
        return False
    try:
        _call("sendMessage", {"chat_id": chat, "text": str(text)[:3500], "disable_web_page_preview": True})
        return True
    except BotError:
        return False


# ---------------------------------------------------------------- setting up

def set_token(token: str) -> dict:
    """The owner's bot token: checked with Telegram (getMe), kept, a new pairing code made, the bot started."""
    token = str(token or "").strip()
    if not _TOKEN_RE.fullmatch(token):
        raise BotError("This is not a bot token. It looks like 1234567890:AAH... (from @BotFather).")
    me = _call("getMe", token=token)
    if not isinstance(me, dict) or not me.get("is_bot"):
        raise BotError("Telegram did not confirm this token.")
    stop()
    _save_token(token)
    _set(bot="@" + str(me.get("username") or ""), chat_id=0, chat_name="", code=f"{secrets.randbelow(900000) + 100000}", offset=0)
    start()
    return status()


def new_code() -> str:
    code = f"{secrets.randbelow(900000) + 100000}"
    _set(code=code)
    return code


def forget() -> None:
    """The bot switched off here: its token and the paired chat forgotten (the bot itself stays in Telegram)."""
    stop()
    _drop_token()
    _set(bot="", chat_id=0, chat_name="", code="", offset=0)


def unpair() -> None:
    _set(chat_id=0, chat_name="", code=f"{secrets.randbelow(900000) + 100000}")


# ---------------------------------------------------------------- the messages

def _safe_name(name: str) -> str:
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(name or "")).strip(" .")[:90]
    return n or "video.mp4"


def _save_file(f: dict, caption: str) -> str:
    """A video sent to the bot: into Downloaded\\Telegram, and an Inbox item."""
    from . import downloader as D, inbox
    size = int(f.get("file_size") or 0)
    if size > MAX_FILE:
        return _say("too_big")
    try:
        info = _call("getFile", {"file_id": f.get("file_id")})
        path = str((info or {}).get("file_path") or "")
        if not path or ".." in path:
            raise BotError("Telegram gave no file.")
        dst_dir = D.folder() / "Telegram"
        dst_dir.mkdir(parents=True, exist_ok=True)
        name = _safe_name(f.get("file_name") or Path(path).name or "video.mp4")
        if not Path(name).suffix:
            name += Path(path).suffix or ".mp4"
        dst = dst_dir / name
        k = 2
        while dst.exists():
            dst = dst_dir / f"{Path(name).stem} ({k}){Path(name).suffix}"
            k += 1
        part = dst.with_suffix(dst.suffix + ".part")
        url = f"{API}/file/bot{_load_token()}/{urllib.parse.quote(path)}"
        got = 0
        with urllib.request.urlopen(url, timeout=120) as r, open(part, "wb") as out:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                got += len(chunk)
                if got > MAX_FILE + 1024:
                    raise BotError("the file is bigger than Telegram said")
                out.write(chunk)
        os.replace(part, dst)
    except (BotError, OSError, urllib.error.URLError) as exc:
        try:
            part.unlink(missing_ok=True)           # (a half file never stays)
        except Exception:
            pass
        return _say("file_failed", why=str(exc)[:120])
    inbox.add("file", file=str(dst), text=caption, source="telegram")
    return _say("file", name=dst.name)


def _what_runs() -> str:
    parts = []
    try:
        from . import downloader as D
        n = sum(1 for j in D.list_jobs(20) if j.get("state") in ("working", "waiting"))
        if n:
            parts.append(("загрузки: " if _ru() else "downloads: ") + str(n))
    except Exception:
        pass
    try:
        from . import voice as vo
        b = vo.busy()
        if b:
            j = vo.read_job(b) if b != "install" else {}
            parts.append(str(j.get("title") or j.get("kind") or b))
    except Exception:
        pass
    return ", ".join(parts) or _say("idle")


def handle(msg: dict) -> str | None:
    """One message: what the bot answers (None: no answer). Only the paired chat is served."""
    from . import inbox
    if not isinstance(msg, dict) or not isinstance(msg.get("chat"), dict):
        return None
    c = _cfg()
    chat = msg["chat"].get("id")
    text = str(msg.get("text") or msg.get("caption") or "").strip()
    paired = c.get("chat_id")
    if not paired:
        m = re.match(r"^/start(?:@\w+)?\s+([0-9]{6})$", text)
        if m and c.get("code") and secrets.compare_digest(m.group(1), str(c.get("code"))):
            who = " ".join(str(msg["chat"].get(k) or "") for k in ("first_name", "last_name")).strip() or str(msg["chat"].get("username") or "")
            _set(chat_id=chat, chat_name=who[:60], code="")
            return _say("paired")
        return _say("need_code") if text.startswith("/start") else None
    if chat != paired:
        return None                                   # (someone else's chat: never answered)
    if re.match(r"^/(start|help)\b", text):
        return _say("help")
    if re.match(r"^/status\b", text):
        return _say("status", what=_what_runs())
    f = msg.get("video") or msg.get("animation") or msg.get("video_note")
    doc = msg.get("document") or {}
    if not f and str(doc.get("mime_type") or "").startswith("video/"):
        f = doc
    if f:
        return _save_file(f, text)
    links = inbox.links_in(text)
    if links:
        rest = text
        for u in links:
            rest = rest.replace(u, " ")
        try:
            inbox.add("link", links=links, text=rest, source="telegram")
        except inbox.InboxError as exc:
            return str(exc)
        return _say("links", n=len(links))
    if text and not text.startswith("/"):
        inbox.add("topic", text=text, source="telegram")
        return _say("topic")
    return None


def _check_downloads() -> None:
    """Tell the phone once when a download started from an Inbox item is finished."""
    from . import downloader as D, inbox
    for it in inbox.items(100):
        for jid in it.get("jobs") or []:
            if jid in (it.get("notified") or []):
                continue
            try:
                j = D.read_job(jid)
            except Exception:
                continue
            if j.get("state") in ("working", "waiting"):
                continue
            res = j.get("result") or {}
            ok = j.get("state") == "done"
            text = (_say("dl_done", n=len(res.get("files") or [])) if ok else
                    _say("dl_failed", why=str(res.get("error") or j.get("state") or "")[:200]))
            if send(text) or not _cfg().get("chat_id"):
                inbox.mark_notified(it["id"], jid)


# ---------------------------------------------------------------- the loop

def _loop(stop_ev: threading.Event) -> None:
    _STATE["running"] = True
    wait = 2.0
    try:
        while not stop_ev.is_set():
            try:
                off = int(_cfg().get("offset") or 0)
                ups = _call("getUpdates", {"offset": off, "timeout": 25, "allowed_updates": ["message"]}, timeout=40) or []
                _STATE["seen_at"] = time.strftime("%Y-%m-%d %H:%M")
                _STATE["error"] = ""
                for u in ups:
                    off = max(off, int(u.get("update_id") or 0) + 1)
                    _set(offset=off)                      # (a message is never handled twice, even after a crash)
                    try:
                        answer = handle(u.get("message") or {})
                    except Exception as exc:              # never let one odd message stop the bot
                        answer = None
                        _STATE["error"] = type(exc).__name__ + ": " + str(exc)[:160]
                    if answer:
                        chat = (u.get("message") or {}).get("chat", {}).get("id")
                        try:
                            _call("sendMessage", {"chat_id": chat, "text": answer[:3500], "disable_web_page_preview": True})
                        except BotError:
                            pass
                _check_downloads()
                wait = 2.0
            except BotError as exc:
                _STATE["error"] = str(exc)
                if "Unauthorized" in str(exc) or "Not Found" in str(exc):
                    stop_ev.wait(300)                      # (a revoked token: try rarely)
                else:
                    stop_ev.wait(wait)
                    wait = min(120.0, wait * 2)
            except Exception as exc:
                _STATE["error"] = type(exc).__name__ + ": " + str(exc)[:160]
                stop_ev.wait(wait)
                wait = min(120.0, wait * 2)
    finally:
        if _STATE.get("stop") is stop_ev:                 # (an older loop ending late does not hide the new one)
            _STATE["running"] = False


def start() -> None:
    """The bot's loop, when it is set up (at the app's start and after the token is pasted)."""
    with _LOCK:
        t = _STATE.get("thread")
        if t and t.is_alive():
            return
        if not (_cfg().get("bot") and _load_token()):
            return
        ev = threading.Event()
        _STATE["stop"] = ev
        t = threading.Thread(target=_loop, args=(ev,), daemon=True, name="telegram")
        _STATE["thread"] = t
        t.start()


def stop(wait: float = 3.0) -> None:
    with _LOCK:
        _STATE["stop"].set()
        t = _STATE.get("thread")
    if t and t.is_alive():
        t.join(wait)

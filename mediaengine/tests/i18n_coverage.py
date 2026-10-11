"""Russian interface coverage: open every page of the app in Russian and list visible English that is left.

  python tests/i18n_coverage.py <archivist_home> [<archivist_home> ...] [--json out.json] [--max N]

Every GET page (ids taken from the database of each given home) is rendered with the interface set to Russian.
Text that still contains English words is reported, except names that stay as they are (MediaEngine, Android,
FFmpeg, file names, paths, user content marked translate='no', codes in <code>/<pre>). Exit code 1 when more
than --max texts are left (default 0).
"""
from __future__ import annotations

import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

KEEP = {  # stays English in Russian too (names, units, formats)
    "MediaEngine", "Archivist", "Social Lab", "Android", "FFmpeg", "FAST_LOCAL", "Social HD", "MP4", "HDR", "HEVC", "AI",
    "OK", "ID", "GB", "MB", "KB", "TB", "fps", "px", "Edge", "Windows", "USB", "SD", "SD/USB", "ADB", "JSON", "CSV", "ONNX",
    "OpenCV", "numpy", "YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "VK", "Google", "Supabase", "GoDog",
    "English", "Русский", "MOV", "MTS", "WebM", "Private", "Rejected", "Staging", "Exports", "HD", "Social", "FAST", "LOCAL",
    "SHA", "Runtime", "MP", "rc", "ZIP", "zscale", "iPhone", "iOS", "Share", "Lab", "OAuth", "Client", "API", "AAC", "Reel", "MediaStore",
}
SKIP_PREFIX = ("/api/", "/static", "/media/", "/thumb/", "/storyboard/", "/clip-preview/", "/export-file/", "/composition-file/",
               "/diagnostics/fixture", "/auto/rev/")
SKIP_PART = ("/video", "/thumb", ".jpg", "/source")      # files, not pages
_PROTECT = re.compile(r"""<(\w+)\b[^>]*(?:translate=['"]no['"]|class=['"][^'"]*\b(?:ae-path|path|mono)\b[^'"]*['"])[^>]*>.*?</\1>""", re.S)
_DROP = re.compile(r"<(script|style|code|pre|textarea)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"""<(?:[^>"']|"[^"]*"|'[^']*')+>""")
USER_CONTENT = {"two", "seven", "phone", "other", "my edit", "test", "three scenes"}   # fixture names / titles typed by the user
_ATTR = re.compile(r"""\b(?:placeholder|title)=(['"])(.*?)\1""", re.S)


def english_left(text: str) -> bool:
    t = re.sub(r"\s+", " ", text).strip()
    if not t or not re.search(r"[A-Za-z]{2,}", t):
        return False
    if t in KEEP or t in USER_CONTENT or any(t.startswith(u + " · MediaEngine") for u in USER_CONTENT):
        return False
    if re.fullmatch(r"(MediaEngine )?v\d+\.\d+\.\d+[\w.-]*( b\d+)?", t) or re.fullmatch(r"[\w ]+\.mp4 [\d:.–]+", t):
        return False
    if any(u in t for u in ("· — · —", "/tmp/", ":\\", "0 B/0 B")) or t.startswith("Последний экспорт:") or t.endswith(".mp4 · MediaEngine"):
        return False
    if re.fullmatch(r"[\w.\- ()]+\.(mp4|mov|mts|m2ts|avi|mkv|jpg|png|json|txt|db|log|zip|vbs|exe)", t, re.I):
        return False          # a file name
    if re.fullmatch(r"([A-Za-z]:\\|/|\\\\).*", t):
        return False          # a path
    if re.fullmatch(r"R\d{3}\b.*", t) and not re.search(r"[A-Za-z]{3,}", t[4:]):
        return False
    words = re.findall(r"[A-Za-z]{2,}", t)
    return any(w not in KEEP for w in words)


def page_texts(html: str):
    html = _PROTECT.sub(" ", html)
    attrs = [m.group(2) for m in _ATTR.finditer(html)]
    html = _DROP.sub(" ", html)
    for part in _TAG.split(html):
        yield part
    yield from attrs


def _has(con, table):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def urls_for(app, con):
    def ids(sql):
        try:
            return [r[0] for r in con.execute(sql).fetchall()][:3]
        except Exception:
            return []
    fill = {
        "inv_id": ids("SELECT id FROM inventory ORDER BY id"), "clip_id": ids("SELECT id FROM virtual_clips ORDER BY id"),
        "cid": ids("SELECT id FROM compositions ORDER BY id"), "composition_id": ids("SELECT id FROM compositions ORDER BY id"),
        "jid": ids("SELECT id FROM jobs ORDER BY id"), "experiment_id": ids("SELECT id FROM social_experiments ORDER BY id"),
        "pid": ids("SELECT id FROM ae_projects ORDER BY id"), "rid": ids("SELECT id FROM ae_revisions ORDER BY id"),
        "index": [0],
    }
    out = []
    for rule in app.url_map.iter_rules():
        if "GET" not in rule.methods or rule.rule.startswith(SKIP_PREFIX) or rule.endpoint == "static" or any(x in rule.rule for x in SKIP_PART):
            continue
        local = dict(fill)
        if rule.rule.startswith("/auto/review/"):
            local["rid"] = ids("SELECT id FROM ae_reviews ORDER BY id")
        args = list(rule.arguments)
        if not args:
            out.append(rule.rule)
            continue
        if any(not local.get(a) for a in args):
            continue
        for k in range(max(len(local[a]) for a in args)):
            url = rule.rule
            for a in args:
                v = local[a][min(k, len(local[a]) - 1)]
                url = re.sub(r"<(?:\w+:)?" + a + ">", str(v), url)
            out.append(url)
    out += ["/auto/check", "/library?view=grid", "/import?source=all", "/jobs?status=all", "/help/guide", "/welcome",
            "/auto/new?folder=Z:/no/such/folder", "/auto/p/999999"]
    for pid, eid in con.execute("SELECT project_id, id FROM ae_exports ORDER BY id LIMIT 2").fetchall() if _has(con, "ae_exports") else []:
        out.append(f"/auto/p/{pid}?exported={eid}")
    return sorted(set(out))


def main():
    homes = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 0
    left: dict[str, str] = {}
    pages = 0
    for home in homes:
        os.environ["ARCHIVIST_HOME"] = str(Path(home).resolve())
        for m in [m for m in list(sys.modules) if m == "archivist" or m.startswith("archivist.")]:
            del sys.modules[m]
        from archivist.web import create_app
        from archivist import i18n
        from archivist.db import db
        app = create_app()
        i18n.set_ui_language("ru")
        H = {"Host": "127.0.0.1:8765"}
        with app.test_client() as c, db() as con:
            for url in urls_for(app, con):
                r = c.get(url, headers=H)
                if r.mimetype != "text/html" or r.status_code >= 500:
                    if r.status_code >= 500:
                        left.setdefault(f"HTTP {r.status_code} on {url}", url)
                    continue
                pages += 1
                for t in page_texts(r.get_data(as_text=True)):
                    import html as _h
                    t = re.sub(r"\s+", " ", _h.unescape(t)).strip()
                    if english_left(t):
                        left.setdefault(t, url)
        i18n.set_ui_language("en")
    for t, url in sorted(left.items(), key=lambda kv: (kv[1], kv[0])):
        print(f"{url}\t{t}")
    print(json.dumps({"pages": pages, "english_left": len(left)}))
    if out_json:
        Path(out_json).write_text(json.dumps(left, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if len(left) <= limit else 1


if __name__ == "__main__":
    sys.exit(main())

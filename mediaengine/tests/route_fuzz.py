"""Every page and button of the app with odd input: no server error (HTTP 500), no request that hangs.

A typed URL, an old bookmark, a page left open across an update or a damaged form must give a page that says what is
wrong (or a 400/404), never "Internal Server Error". Runs on a copy of a home with real projects (e2e_auto_edit's
home), so ids that exist are hit too.

  python tests/route_fuzz.py --home <home with data, or empty dir> [--out report.json]

Routes that open windows on the PC (folder pickers, Explorer), switch or remove app builds, quit the app or download
from the internet are not called.
"""
from __future__ import annotations

import argparse, json, os, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PORT = 18779

# without a "path" these open a Windows folder window (it waits for a person): only odd paths are sent to them
PATH_ONLY = ("/api/auto/model/import", "/api/auto/aiplus/import")
SKIP_RULES = ("/api/app-control", "/api/auto/pick-", "/auto/check/use-build", "/auto/check/remove-build",
              "/api/auto/model/download", "/api/auto/aiplus/download", "/auto/check/hwtest", "/auto/exports/open",
              "/auto/orders/open-", "/static/", "/diagnostics/fixture.mp4")
SKIP_ACTIONS = ("open", "reveal", "open-folder")          # <action> values that start Explorer / a player
INTS = ["1", "2", "0", "999999", str(2 ** 63 + 5)]
STRS = ["x", "..", "con", "a b", "%00", "%E2%80%A8", "'\"<>"]
ODD = ["", "x", "-1", "0", "1e309", "nan", "99999999999999999999999", "\\\\server\\share\\v.mp4", "../../etc", "C:\\nope\\x.mp4",
       "<script>", "{", "[1,2", "\u2028", "\x00", "a" * 3000]
FIELDS = ["folder", "files", "ids", "id", "length", "format", "sound", "mode", "theme", "title", "name", "path", "dest", "aspect",
          "action", "value", "on", "auto_run", "selection", "exclude", "trims", "start", "end", "q", "music", "music_mode", "lang",
          "framing", "text", "subtitle", "choice", "note", "rid", "side", "page", "type", "limit", "offset", "status", "source",
          "days", "day", "state", "prepare", "beat_sync", "beat_sync_shown", "rights", "kind", "preset", "preset_choice",
          "presetChoice", "clip_ids", "order", "csv", "metric", "views", "url", "folder_id", "key", "to", "from", "position"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--out", default="")
    ap.add_argument("--seconds", type=float, default=1500, help="stop after this long (a report of what was done)")
    a = ap.parse_args()
    os.environ["ARCHIVIST_HOME"] = str(Path(a.home).resolve()); os.environ["ARCHIVIST_PORT"] = str(PORT)
    os.environ["MEDIAENGINE_NO_BROWSER"] = "1"; os.environ["MEDIAENGINE_UPDATES"] = "off"
    sys.path.insert(0, str(ROOT / "app"))
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from archivist.web import create_app
    app = create_app()
    app.testing = False                       # an error becomes the 500 a user would see
    app.config["PROPAGATE_EXCEPTIONS"] = False
    c = app.test_client()
    H = {"Host": f"127.0.0.1:{PORT}", "Origin": f"http://127.0.0.1:{PORT}"}
    bad, slow, n = [], [], 0
    t_end = time.time() + a.seconds

    def hit(method, url, **kw):
        nonlocal n
        if time.time() > t_end:          # (the time limit holds inside a route with many odd inputs too)
            return
        n += 1
        t = time.time()
        try:
            r = c.open(url, method=method, headers=H, **kw)
            code = r.status_code
            body = r.get_data()[:300].decode("utf-8", "replace") if code >= 500 else ""
            r.close()
        except Exception as exc:              # (with PROPAGATE_EXCEPTIONS off this is a bug of the test client use)
            code, body = 599, repr(exc)[:300]
        dt = time.time() - t
        if code >= 500:
            bad.append({"method": method, "url": url[:300], "code": code, "data": str(kw.get("data") or kw.get("json") or "")[:200],
                        "body": body})
            print(f"FAIL {code} {method} {url[:160]} {str(kw.get('data') or kw.get('json') or '')[:120]}", flush=True)
        if dt > 15:
            slow.append({"method": method, "url": url[:300], "seconds": round(dt, 1)})
            print(f"SLOW {dt:.0f}s {method} {url[:160]}", flush=True)

    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    for rule in rules:
        if time.time() > t_end:
            break
        if rule.rule.startswith(SKIP_RULES) or rule.rule.endswith(("/open", "/reveal", "/open-folder")) or rule.endpoint == "static":
            continue
        if rule.rule in PATH_ONLY:
            for v in ODD:
                if v:                                  # ("" = no path: the folder window)
                    hit("POST", rule.rule, json={"path": v})
            continue
        args = list(rule.arguments)
        urls = []
        for k in range(max(len(INTS), len(STRS)) if args else 1):
            u = rule.rule
            skip = False
            for name in args:
                conv = re.search(r"<(\w+):" + name + ">", rule.rule)
                vals = INTS if conv and conv.group(1) == "int" else STRS
                if name == "action":
                    vals = ["run", "reject", "retry", "stop", "delete", "accept", "x", ".."]
                if name in ("state", "aspect", "side", "lang"):
                    vals = ["x", "16:9", "9:16", "left", "right", "queued", "posted", ".."]
                v = vals[k % len(vals)]
                if name == "action" and v in SKIP_ACTIONS:
                    skip = True
                u = re.sub(r"<(?:\w+:)?" + name + ">", v, u)
            if not skip:
                urls.append(u)
        for i, u in enumerate(dict.fromkeys(urls)):
            full = i == 0                     # every odd input on the first URL (an id that may exist); the odd ids plainly
            for m in sorted(rule.methods - {"HEAD", "OPTIONS"}):
                if not full:
                    hit(m, u)
                    if m != "GET":
                        hit(m, u, data={f: "x" for f in FIELDS})
                    continue
                if m == "GET":
                    hit("GET", u)
                    for v in ODD[:8]:
                        q = "&".join(f"{f}={v}" for f in ("page", "ids", "folder", "q", "type", "limit", "offset", "view",
                                                         "status", "source", "exported", "same", "theme", "files", "id", "day"))
                        hit("GET", u + "?" + q)
                else:
                    hit(m, u)                                      # no form at all
                    for v in ODD:
                        hit(m, u, data={f: v for f in FIELDS})
                    hit(m, u, data={f: [v for v in ODD[:4]] for f in FIELDS})      # every field given several times
                    hit(m, u, json={f: {"x": [1]} for f in FIELDS})              # a JSON body of the wrong shape
                    hit(m, u, json=[1, 2, 3])
                    hit(m, u, data=b"\xff\xfe{not json", content_type="application/json")
    out = {"requests": n, "server_errors": bad, "slow": slow, "pass": not bad and not slow}
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"requests": n, "server_errors": len(bad), "slow": len(slow)}))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

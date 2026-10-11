"""Disconnected source drive and no network, through the app routes.

  python tests/reliability_checks.py <fixtures_dir> <work_dir>

- The source folder disappears after a build (drive unplugged): the project says so, nothing is deleted, the accepted
  reel can still be watched and exported, a new build is refused with a clear message; when the folder is back, builds work.
- No network: every outgoing connection from the app process to a non-loopback address is blocked and recorded;
  the whole Auto Edit flow must not try any. (The engine subprocess is checked with a firewall rule in Windows CI.)
"""
from __future__ import annotations

import os, shutil, socket, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

ATTEMPTS = []
_real_connect = socket.socket.connect


def _guard(self, address):
    host = address[0] if isinstance(address, tuple) else str(address)
    if host not in ("127.0.0.1", "::1", "localhost") and not str(host).startswith("127."):
        ATTEMPTS.append(host)
        raise OSError("network disabled by test")
    return _real_connect(self, address)


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    socket.socket.connect = _guard
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist import auto_edit as ae
    src = work / "Card D"
    shutil.copytree(fx / "two", src)
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def wait(jid, limit=1800):
        t0 = time.time()
        while time.time() - t0 < limit:
            j = ae.job(jid)
            if j["status"] in ("done", "failed", "cancelled"):
                return j
            time.sleep(0.5)
        return {"status": "timeout"}

    app = create_app()
    with app.test_client() as c:
        r = c.post("/auto/create", data={"folder": str(src), "length": "5", "format": "social_hd", "sound": "auto", "mode": "technical"}, headers=H)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        j = wait(ae.project(pid)["jobs"][0]["id"])
        check("build_done", j["status"] == "done", j)
        rid = j.get("revision_id")
        c.post(f"/auto/p/{pid}/accept", data={"revision_id": rid}, headers=H)

        gone = work / "Card D (unplugged)"
        src.rename(gone)
        r = c.get(f"/auto/p/{pid}", headers=H)
        check("unplugged_project_says_so", r.status_code == 200 and b"not available" in r.data)
        r = c.get("/auto", headers=H)
        check("unplugged_home_card_says_so", b"Source videos are not available" in r.data)
        r = c.get(f"/auto/rev/{rid}/video", headers={**H, "Range": "bytes=0-99"})
        check("unplugged_reel_still_plays", r.status_code == 206)
        r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rid, "length": "5", "format": "horizontal", "sound": "auto"}, headers=H)
        check("unplugged_new_build_refused_clearly", r.status_code == 400 and b"not available" in r.data, r.status_code)
        r = c.post(f"/auto/p/{pid}/export", headers=H)
        p = ae.project(pid)
        check("unplugged_export_still_works", r.status_code == 302 and p["exports"] and Path(p["exports"][0]["path"]).is_file())
        check("unplugged_nothing_deleted", len(p["revisions"]) == 1 and p["accepted_revision_id"] == rid)

        gone.rename(src)
        r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rid, "length": "5", "format": "horizontal", "sound": "auto"}, headers=H)
        j2 = wait(ae.project(pid)["jobs"][0]["id"])
        check("plugged_back_build_works", r.status_code == 302 and j2["status"] == "done", j2)

    check("no_network_attempts", not ATTEMPTS, ATTEMPTS[:5])
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

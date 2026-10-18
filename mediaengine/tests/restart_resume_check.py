"""A reel being made when the app stops WITHOUT quitting (a restart of the PC at night, a crash) is made again by
itself at the next start - once; after Quit it stays interrupted (Retry). Real app processes, real engine.

  python tests/restart_resume_check.py <fixtures_dir> <work_dir>

fixtures_dir/two: two short videos (tests/make_fixtures.py). Each step is its own Python process on the same data,
as the app's processes are; "the PC restarts" = the process group is killed while the build runs.
"""
from __future__ import annotations

import json, os, shutil, signal, subprocess, sys, textwrap, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18783

STEP = textwrap.dedent(r"""
    import json, os, sys, time
    sys.path.insert(0, sys.argv[1]); mode = sys.argv[2]; folder = sys.argv[3]
    from archivist.web import create_app
    from archivist import auto_edit as ae
    from archivist.db import db
    app = create_app(); c = app.test_client(); H = {"Host": "127.0.0.1:%s" % os.environ["ARCHIVIST_PORT"],
                                                  "Origin": "http://127.0.0.1:%s" % os.environ["ARCHIVIST_PORT"]}
    c.get("/api/ping", headers=H)                       # the first request: what the app does at its start
    def jobs():
        with db() as con:
            return [dict(r) for r in con.execute("SELECT id, status, error, auto_resumed FROM ae_jobs ORDER BY id").fetchall()]
    print("JOBS " + json.dumps(jobs()), flush=True)
    if mode == "create":
        r = c.post("/auto/create", data={"folder": folder, "length": "15", "format": "social_hd", "sound": "auto",
                                        "mode": "technical"}, headers=H)
        print("CREATED %s" % r.status_code, flush=True)
    if mode in ("create", "resume", "resume_quit"):
        end = time.time() + 600                          # wait until a build really runs, then say so (the parent kills us)
        while time.time() < end:
            js = jobs()
            if js and js[-1]["status"] == "running":
                with db() as con:
                    st = con.execute("SELECT stage FROM ae_jobs WHERE id=?", (js[-1]["id"],)).fetchone()["stage"]
                if st in ("analyze", "render", "trim", "select"):
                    print("RUNNING " + json.dumps(js[-1]), flush=True)
                    if mode == "resume_quit":               # Quit on purpose while it runs (what Quit does first)
                        ae.mark_clean_exit(); print("QUIT", flush=True)
                    break
            time.sleep(0.3)
        time.sleep(600)
""")


def main() -> int:
    fixtures, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    folder = work / "videos"; shutil.copytree(fixtures / "two", folder)
    step = work / "step.py"; step.write_text(STEP, encoding="utf-8")
    env = dict(os.environ, ARCHIVIST_HOME=str(work / "home"), ARCHIVIST_PORT=str(PORT), MEDIAENGINE_NO_BROWSER="1")
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def run_until(mode, word, timeout=900):
        """Run a step until it prints `word` (a build runs), then kill its whole process group (the PC restarts)."""
        p = subprocess.Popen([sys.executable, str(step), str(ROOT / "app"), mode, str(folder)], env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=os.name != "nt")
        lines, end = [], time.time() + timeout
        try:
            while time.time() < end:
                ln = p.stdout.readline()
                if not ln:
                    break
                lines.append(ln.rstrip())
                if ln.startswith(word):
                    break
        finally:
            if os.name == "nt":       # the whole tree, as a restart of the PC would (the engine is in the app's job object)
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
            else:
                os.killpg(p.pid, signal.SIGKILL)
            p.wait()
        return lines

    def jobs_after(mode="look"):
        p = subprocess.run([sys.executable, str(step), str(ROOT / "app"), mode, str(folder)], env=env, text=True,
                           capture_output=True, timeout=300)
        for ln in p.stdout.splitlines():
            if ln.startswith("JOBS "):
                return json.loads(ln[5:]), p.stdout
        return [], p.stdout + p.stderr[-800:]

    # 1. a build runs, the PC "restarts": the next start makes it again by itself
    out = run_until("create", "RUNNING")
    check("a build was running when the app stopped", any(l.startswith("RUNNING") for l in out), out[-8:])
    out = run_until("resume", "RUNNING")
    js = [json.loads(l[5:]) for l in out if l.startswith("JOBS ")][0]
    first = js[0]
    check("next start: the stopped build is marked as stopped unexpectedly", first["status"] == "failed"
          and "made again by itself" in (first["error"] or ""), first)
    run = [json.loads(l[8:]) for l in out if l.startswith("RUNNING ")]
    check("...and made again by itself (once)", bool(run) and run[0]["id"] != first["id"] and run[0]["auto_resumed"] == 1, out[-8:])
    # 2. it stops unexpectedly again: no endless loop, it waits for Retry
    js, raw = jobs_after()
    last = js[-1] if js else {}
    check("a second unexpected stop: interrupted, Retry (no loop)", last.get("status") == "failed" and last.get("auto_resumed") == 1
          and "Press Retry" in (last.get("error") or "") and not any(j["status"] in ("queued", "running") for j in js), raw[-800:])
    # 3. Quit on purpose while a build runs: interrupted, not made again
    from_retry = subprocess.run([sys.executable, "-c", textwrap.dedent(f"""
        import sys; sys.path.insert(0, {str(ROOT / 'app')!r})
        from archivist.web import create_app
        from archivist import auto_edit as ae
        app = create_app(); c = app.test_client()
        H = {{"Host": "127.0.0.1:{PORT}", "Origin": "http://127.0.0.1:{PORT}"}}
        c.get("/api/ping", headers=H)
        j = ae.project(ae.list_projects()[0]["id"])["jobs"][0]
        r = c.post(f"/auto/job/{{j['id']}}/retry", headers=H); print("RETRY", r.status_code, flush=True)
    """)], env=env, text=True, capture_output=True, timeout=120)
    check("Retry queues it", "RETRY 302" in from_retry.stdout, from_retry.stdout + from_retry.stderr[-500:])
    out = run_until("resume_quit", "QUIT")
    check("the retried build runs, then Quit", any(l.startswith("RUNNING") for l in out) and any(l.startswith("QUIT") for l in out), out[-6:])
    js, raw = jobs_after()
    last = js[-1] if js else {}
    check("after Quit: interrupted (Retry), not made again by itself", last.get("status") == "failed"
          and "Press Retry" in (last.get("error") or "") and not any(j["status"] in ("queued", "running") for j in js), raw[-800:])
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

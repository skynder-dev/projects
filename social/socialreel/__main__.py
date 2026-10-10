import argparse
import json
import sys
import unittest
from pathlib import Path

from .common import ROOT, PipelineError, read_json


def main(argv=None):
    ap = argparse.ArgumentParser(prog="socialreel")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="produce one Reel end-to-end")
    r.add_argument("--config", default=str(ROOT / "config.json"))
    r.add_argument("--out", default=str(ROOT / "runs"))
    r.add_argument("--fixture", help="use exported records instead of live Grants.gov (never accepted)")
    r.add_argument("--opportunity", help="force a specific Grants.gov opportunity id")
    r.add_argument("--history", help="history.json used to avoid repeating topics")
    r.add_argument("--voice", help="override voice backend (piper|espeak|silent_test)")
    r.add_argument("--writer", help="override writer (auto|template|llm)")
    b = sub.add_parser("rebuild", help="re-render a finished run and compare hashes")
    b.add_argument("run_dir")
    sub.add_parser("selftest", help="run unit tests")
    ix = sub.add_parser("index", help="write README.md index for a results folder")
    ix.add_argument("results_dir")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        res = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if res.wasSuccessful() else 1
    if a.cmd == "index":
        write_index(Path(a.results_dir))
        return 0
    if a.cmd == "rebuild":
        from .pipeline import rebuild
        res = rebuild(Path(a.run_dir))
        print(json.dumps(res, indent=2))
        return 0 if res["byte_identical"] else 3
    cfg = read_json(a.config)
    if a.voice:
        cfg["voice"]["backend"] = a.voice
    if a.writer:
        cfg["writer"] = a.writer
    from .pipeline import run
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        d = run(cfg, out, Path(a.fixture) if a.fixture else None, a.opportunity, Path(a.history) if a.history else None)
    except PipelineError as e:
        print(f"PIPELINE FAILED: {e}", file=sys.stderr)
        return 2
    res = read_json(d / "result.json")
    print(json.dumps({"run_dir": str(d), "accepted": res["accepted"], "video_sha256": res["video"]["sha256"],
                      "duration_s": res["verification"].get("duration_s"), "writer": res["writer"],
                      "failed_checks": [c["check"] for c in res["verification"]["checks"] if not c["pass"]]}, indent=2))
    return 0 if res["accepted"] else 1


def write_index(pub: Path):
    rows = []
    runs = pub / "runs"
    found = [(read_json(d / "result.json"), d) for d in (runs.iterdir() if runs.is_dir() else []) if (d / "result.json").exists()]
    for r, d in sorted(found, key=lambda x: x[0].get("finished_at", ""), reverse=True):
        if True:
            rows.append(f"| [{d.name}](runs/{d.name}/REVIEW.md) | {r['verification'].get('duration_s')} s | {r['writer']} "
                        f"| `{r['video']['sha256'][:16]}` | [mp4](runs/{d.name}/reel.mp4) |")
    extra = "\nRetracted runs: see [RETRACTED.md](RETRACTED.md).\n" if (pub / "RETRACTED.md").exists() else ""
    (pub / "README.md").write_text(
        "# Social Reels — results\n\nAccepted Reels (newest first). `latest/` = full package of the newest one; "
        "full packages of every run are in that run's Actions artifact.\n" + extra + "\n"
        "| Run | Length | Writer | Video SHA-256 | Video |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")


if __name__ == "__main__":
    sys.exit(main())

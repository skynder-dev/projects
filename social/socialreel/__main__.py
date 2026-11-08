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
    t = sub.add_parser("topics", help="discover and rank official topics without generating media")
    t.add_argument("--config", default=str(ROOT / "config.json"))
    t.add_argument("--out", required=True, help="directory for topics.json and exact source snapshots")
    t.add_argument("--fixture", help="offline Grants.gov export or multi-source manifest; no API request")
    t.add_argument("--as-of", help="scoring date, YYYY-MM-DD (default: current UTC date)")
    t.add_argument("--sources", help="comma-separated grants,usagov,studentaid,scorecard,sba (default: grants)")
    s = sub.add_parser("source", help="official source to record, claims and existing concept-core inputs")
    origin = s.add_mutually_exclusive_group(required=True)
    origin.add_argument("--source", choices=("usagov", "studentaid", "scorecard", "sba"))
    origin.add_argument("--topics", type=Path, help="replay a typed topics.json bundle offline")
    s.add_argument("--topic-id", help="topic_id from --topics; default is the first ranked topic")
    s.add_argument("--page", help="configured page name or approved official URL")
    s.add_argument("--program", help="USA.gov program name or 1-based index; default: whole page, otherwise first complete program that fits")
    s.add_argument("--college-id", help="College Scorecard school ID")
    s.add_argument("--fixture", type=Path, help="offline HTML/JSON bytes for a single source")
    s.add_argument("--out", required=True, type=Path)
    s.add_argument("--config", default=str(ROOT / "config.json"))
    s.add_argument("--prepare-request", action="store_true", help="attempt existing core admission; never calls a model")
    from .concept_choose_cli import add_parser
    add_parser(sub)
    a = ap.parse_args(argv)

    if a.cmd == "concepts":
        from .concept_choose_cli import run as run_concepts
        return run_concepts(a)
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
    if a.cmd == "source":
        from .source_intake import acquire, replay_topic, write_bundle
        try:
            if a.program is not None and a.source and a.source not in {"usagov", "sba"}:
                raise PipelineError("--program is supported only for USA.gov and SBA.gov")
            if a.topics:
                if a.fixture:
                    raise PipelineError("--topics replays its own snapshots; do not combine with --fixture")
                record, claims = replay_topic(a.topics, a.out, a.topic_id)
            else:
                if a.topic_id:
                    raise PipelineError("--topic-id requires --topics")
                record, claims, _ = acquire(a.source, a.out, page=a.page, school_id=a.college_id, fixture=a.fixture)
            result = write_bundle(record, claims, a.out, read_json(a.config), prepare_request=a.prepare_request, program=a.program)
        except (PipelineError, OSError, ValueError) as error:
            print(f"SOURCE FAILED: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2))
        return 2 if result.get("request_refused") else 0
    if a.cmd == "topics":
        from .topics import run as run_topics
        try:
            result = run_topics(read_json(a.config), Path(a.out),
                                fixture=Path(a.fixture) if a.fixture else None,
                                as_of=a.as_of, config_dir=Path(a.config).resolve().parent,
                                sources=[source.strip() for source in a.sources.split(",")] if a.sources else None)
        except (PipelineError, OSError, ValueError) as e:
            print(f"TOPICS FAILED: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"topics_file": str(Path(a.out) / "topics.json"),
                          "ranked": len(result["topics"]), "excluded": len(result["excluded"]),
                          "mode": result["mode"]}, indent=2))
        return 0
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

"""The choice of moments on several cores gives exactly the accepted choice.

  python tests/selection_parallel_check.py [--cases N] [--big]

Random moment sets (ties in the scores on purpose, overlapping windows of one video, few and many videos, every reel
length) are chosen by the accepted medeng_targeted_auto_edit_v26.choose_for_target and by
p11_selection_parallel.choose_for_target (forced onto several processes even for small searches): the same moments in
the same order, or the same error. --big also times the largest 30 s search (8.65 million combinations) both ways.
"""
from __future__ import annotations

import json, random, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENG = ROOT / "app" / "archivist" / "engine_p11"
sys.path.insert(0, str(ENG))


def events(rng, n_ev, n_src, ties):
    out = []
    for i in range(n_ev):
        src = rng.randrange(n_src)
        start = round(rng.uniform(0, 60), 3)
        dur = rng.choice([2.0, 3.5, 5.0, 5.5, 6.0])
        score = round(rng.uniform(.3, .9), 2 if ties else 6)
        out.append({"event_id": f"e{i:03d}{rng.randrange(1 << 20):05x}", "source_name": f"v{src:02d}.mp4", "source_sha256": f"s{src:02d}",
                    "start_s": start, "end_s": round(start + dur, 3), "duration_s": dur if rng.random() < .8 else None,
                    "v22_score": score})
    return out


def main():
    import medeng_targeted_auto_edit_v26 as v52
    import p11_selection_parallel as sp
    cases = int(sys.argv[sys.argv.index("--cases") + 1]) if "--cases" in sys.argv else 300
    rng = random.Random(20261016)
    bad = []
    n_par = 0
    for k in range(cases):
        n_ev = rng.randint(2, 18)
        evs = events(rng, n_ev, rng.randint(1, min(n_ev, 9)), ties=rng.random() < .6)
        target = rng.choice([5, 15, 30, 60, 120])
        m = min(30, len(evs))
        try:
            a = [e["event_id"] for e in v52.choose_for_target(evs, target, 5.0, .25, max_events=m)]
        except Exception as exc:
            a = "ERR:" + str(exc)
        try:
            b = [e["event_id"] for e in sp.choose_for_target(v52, evs, target, 5.0, .25, max_events=m, workers=3, min_parallel=0)]
            n_par += 1
        except Exception as exc:
            b = "ERR:" + str(exc)
        if a != b:
            bad.append({"case": k, "target": target, "accepted": a, "parallel": b})
    res = {"cases": cases, "parallel_runs": n_par, "different": len(bad), "first_differences": bad[:3]}
    if "--big" in sys.argv:
        evs = events(random.Random(7), 30, 12, ties=True)
        t0 = time.perf_counter(); a = [e["event_id"] for e in v52.choose_for_target(evs, 30, 5.0, .25, max_events=30)]
        ta = time.perf_counter() - t0
        t0 = time.perf_counter(); b = [e["event_id"] for e in sp.choose_for_target(v52, evs, 30, 5.0, .25, max_events=30)]
        tb = time.perf_counter() - t0
        res["big"] = {"accepted_s": round(ta, 2), "parallel_s": round(tb, 2), "same": a == b}
        if a != b:
            bad.append({"case": "big", "accepted": a, "parallel": b})
    print(json.dumps(res, indent=1))
    print(("PASS" if not bad else "FAIL") + " parallel choice of moments == accepted choice")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

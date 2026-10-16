"""The accepted choice of moments (medeng_targeted_auto_edit_v26.choose_for_target, unchanged) searched on several
processor cores - the same result, found faster.

The accepted search tries every combination of the best moments (up to 8.65 million for a 30 s reel) one after another
in one Python thread: 31 s on the owner's 16-thread PC for every new length. Here the same combinations, in the same
order, are split by their first moments into parts; every part is searched by the accepted loop (copied line for line
below: the same arithmetic in the same order, so the same numbers) in its own process; the parts' best results are
then compared in the accepted order with the accepted strict ">", so the first best combination wins exactly as in one
long loop. Checked against the accepted function on random moment sets (tests/selection_parallel_check.py) and on
every engine regression run (R2 calls the accepted function directly).
"""
from __future__ import annotations

import math, os
from collections import Counter
from itertools import combinations

_EV = None          # the ranked moments of the current search, set once per worker process
LAST = {"kind": ""}  # how the last search ran: "parallel" or "accepted" (the accepted function itself)


def _init(ev):
    global _EV
    _EV = ev


def _search(task):
    """The accepted inner loop over the combinations of size n that start with `prefix` (in the accepted order).
    Returns (key, indices) of the first best one, or None."""
    n, prefix, target, clip_seconds, transition, total_sources = task
    ranked = _EV
    best = None
    start = prefix[-1] + 1 if prefix else 0
    pre = tuple(ranked[i] for i in prefix)
    for rest in combinations(ranked[start:], n - len(prefix)):
        combo = pre + rest
        counts = Counter(e['source_sha256'] for e in combo); unique = len(counts)
        # Generic diversity rule: short reels use distinct sources; long reels include every available source.
        if n <= total_sources and unique != n: continue
        if n > total_sources and unique != total_sources: continue
        dur = (sum(e['_used'] for e in combo) - transition * max(0, len(combo) - 1)) if combo else 0.0
        dur_err = abs(dur - target)
        quality = sum(e['v22_score'] for e in combo) / n
        repeat_pen = sum(max(0, c - 1) ** 2 for c in counts.values()) / max(1, n - 1)
        # discourage multiple neighboring events from the same source
        near = 0.0
        by = {}
        for e in combo: by.setdefault(e['source_sha256'], []).append(e)
        for xs in by.values():
            xs = sorted(xs, key=lambda e: float(e['start_s']))
            for a, b in zip(xs, xs[1:]):
                gap = float(b['start_s']) - float(a['end_s'])
                if gap < 5.0: near += (5.0 - max(0.0, gap)) / 5.0
        objective = quality - .45 * (dur_err / max(1.0, clip_seconds)) - .10 * repeat_pen - .04 * near
        key = (objective, -dur_err, quality, -repeat_pen)
        if best is None or key > best[0]: best = (key, combo)
    return None if best is None else (best[0], tuple(e['_i'] for e in best[1]))


def _tasks(n, size, depth):
    """Prefixes of length `depth` of the size-n combinations of range(size), in the accepted (lexicographic) order."""
    d = min(depth, n)
    for p in combinations(range(size), d):
        if size - (p[-1] + 1 if p else 0) >= n - d:
            yield p


def choose_for_target(v52, events, target, clip_seconds, transition, max_events=30, workers=None, min_parallel=1_500_000):
    """Exactly v52.choose_for_target(events, target, clip_seconds, transition, max_events)."""
    ranked = sorted(events, key=lambda x: (-x['v22_score'], x['source_name'], x['event_id']))[:max_events]
    if len(ranked) < 1: raise v52.V22Error('NO_RANKED_EVENTS')
    if len(ranked) == 1: return ranked
    sources = sorted(set(e['source_sha256'] for e in ranked)); total_sources = len(sources)
    nominal = max(1, int(round((target - transition) / max(.1, clip_seconds - transition))))
    sizes = range(max(1, nominal - 2), min(len(ranked), nominal + 2) + 1)
    total = sum(math.comb(len(ranked), n) for n in sizes)
    workers = workers if workers is not None else max(1, min(8, (os.cpu_count() or 2) // 2))
    if workers <= 1 or total < min_parallel:
        LAST["kind"] = "accepted"
        return v52.choose_for_target(events, target, clip_seconds, transition, max_events=max_events)
    LAST["kind"] = "parallel"
    # what the loop reads of each moment, with its used length computed by the accepted function
    light = [{'source_sha256': e['source_sha256'], 'v22_score': e['v22_score'], 'start_s': e['start_s'], 'end_s': e['end_s'],
              '_used': v52.used_duration(e, clip_seconds), '_i': i} for i, e in enumerate(ranked)]
    tasks = []
    for n in sizes:
        depth = 1 if math.comb(len(ranked), n) < 50_000 else (2 if math.comb(len(ranked), n) < 2_000_000 else 3)
        tasks.extend((n, p, target, clip_seconds, transition, total_sources) for p in _tasks(n, len(ranked), depth))
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    # "spawn" everywhere: what Windows does, so the Linux checks run the same way
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(light,),
                             mp_context=multiprocessing.get_context("spawn")) as ex:
        parts = list(ex.map(_search, tasks, chunksize=max(1, len(tasks) // (workers * 8))))
    best = None
    for part in parts:          # in the accepted order: the first best combination wins, as in one loop
        if part is not None and (best is None or part[0] > best[0]): best = part
    if best is None:
        raise v52.V22Error('NO_DIVERSE_TARGET_COMBINATION')
    return [ranked[i] for i in best[1]]

from __future__ import annotations
from itertools import permutations
import math
import numpy as np

ALGO_VERSION = "P11_MONTAGE_SEQUENCE_SHADOW_V4"
REQUIRED_METRICS = ("composition","stability","ending_quality")
FIXED_NEAR = 0.06
FIXED_SIMILAR = 0.10
FIXED_FAR = 0.22

def _id(e): return str(e["event_id"])
def _m(e,k): return float((e.get("v22_metrics") or {})[k])
def _q(e): return float(e["v22_score"])

def _opener(e):
    return .62*_q(e)+.18*_m(e,"composition")+.20*_m(e,"stability")

def _closer(e):
    return .50*_q(e)+.30*_m(e,"ending_quality")+.20*_m(e,"stability")

def _d(a,b,pairwise):
    if not pairwise: return None
    k=_id(a)+"->"+_id(b)
    if k in pairwise: return float(pairwise[k])
    rk=_id(b)+"->"+_id(a)
    return float(pairwise[rk]) if rk in pairwise else None

def _distance_profile(events,pairwise):
    vals=[]
    for a in events:
        for b in events:
            if _id(a)==_id(b): continue
            d=_d(a,b,pairwise)
            if d is not None and math.isfinite(d):
                vals.append(max(0.0,min(1.0,d)))
    if len(vals)<3:
        return {"q25":FIXED_NEAR,"q50":.12,"q90":.28}
    a=np.asarray(vals,float)
    return {"q25":float(np.quantile(a,.25)),
            "q50":float(np.quantile(a,.50)),
            "q90":float(np.quantile(a,.90))}

def _adjacency(a,b,pairwise):
    d=_d(a,b,pairwise)
    continuity=0.0 if d is None else max(0.0,min(1.0,1.0-d))
    source_switch=1.0 if str(a["source_sha256"])!=str(b["source_sha256"]) else 0.0
    return .55*continuity+.25*source_switch+.20*min(_q(a),_q(b))

def _source_switches(order):
    return sum(1 for a,b in zip(order,order[1:]) if str(a["source_sha256"])!=str(b["source_sha256"]))

def _same_source(order):
    return max(0,len(order)-1)-_source_switches(order)

def _repeat_source(order):
    return _same_source(order)/max(1,len(order)-1)

def _displacement(order,baseline):
    pos={_id(e):i for i,e in enumerate(baseline)}
    n=max(1,len(order)-1)
    return sum(abs(i-pos[_id(e)])/n for i,e in enumerate(order))/len(order)

def _adaptive_monotony(order,pairwise,profile):
    if len(order)<2: return (0.0,0.0,0.0)
    q25=max(1e-6,profile["q25"]); q90=min(.999999,profile["q90"])
    near=[]; far=[]
    for a,b in zip(order,order[1:]):
        d=_d(a,b,pairwise)
        if d is None: continue
        d=max(0.0,min(1.0,d))
        near.append(max(0.0,(q25-d)/q25))
        far.append(max(0.0,(d-q90)/max(1e-6,1.0-q90)))
    two=[]
    for a,c in zip(order,order[2:]):
        d=_d(a,c,pairwise)
        if d is None: continue
        d=max(0.0,min(1.0,d))
        two.append(max(0.0,(q25-d)/q25))
    return (sum(near)/max(1,len(near)),
            sum(two)/max(1,len(two)),
            sum(far)/max(1,len(far)))

def _fixed_counts(order,pairwise):
    adj=[_d(a,b,pairwise) for a,b in zip(order,order[1:])]
    two=[_d(a,c,pairwise) for a,c in zip(order,order[2:])]
    adj=[float(x) for x in adj if x is not None]
    two=[float(x) for x in two if x is not None]
    return {
        "near_adj_lt_0_06":sum(x<FIXED_NEAR for x in adj),
        "similar_adj_lt_0_10":sum(x<FIXED_SIMILAR for x in adj),
        "two_step_repeat_lt_0_10":sum(x<FIXED_SIMILAR for x in two),
        "far_jump_gt_0_22":sum(x>FIXED_FAR for x in adj),
        "source_switches":_source_switches(order),
        "same_source_adjacent":_same_source(order),
    }

def _guard_map(order,baseline,pairwise,profile):
    eps=1e-12
    bn,bt,bf=_adaptive_monotony(baseline,pairwise,profile)
    n,t,f=_adaptive_monotony(order,pairwise,profile)
    bc=_fixed_counts(baseline,pairwise); c=_fixed_counts(order,pairwise)
    return {
        "opener_nonregression":_opener(order[0])+eps>=_opener(baseline[0]),
        "closer_nonregression":_closer(order[-1])+eps>=_closer(baseline[-1]),
        "adaptive_near_nonregression":n<=bn+eps,
        "adaptive_two_step_nonregression":t<=bt+eps,
        "adaptive_far_nonregression":f<=bf+eps,
        "fixed_near_count_nonregression":c["near_adj_lt_0_06"]<=bc["near_adj_lt_0_06"],
        "fixed_similar_count_nonregression":c["similar_adj_lt_0_10"]<=bc["similar_adj_lt_0_10"],
        "fixed_two_step_count_nonregression":c["two_step_repeat_lt_0_10"]<=bc["two_step_repeat_lt_0_10"],
        "fixed_far_count_nonregression":c["far_jump_gt_0_22"]<=bc["far_jump_gt_0_22"],
        "source_switch_nonregression":c["source_switches"]>=bc["source_switches"],
        "same_source_nonregression":c["same_source_adjacent"]<=bc["same_source_adjacent"],
    }

def _guards_pass(g): return all(bool(x) for x in g.values())

def validate(events):
    if not isinstance(events,list) or not events: return False,"no_events"
    ids=[]
    for e in events:
        try:
            ids.append(_id(e)); _=str(e["source_sha256"])
            if not math.isfinite(_q(e)): return False,"nonfinite_quality"
            for k in REQUIRED_METRICS:
                if not math.isfinite(_m(e,k)): return False,"nonfinite_metric"
        except Exception: return False,"missing_required_fields"
    if len(ids)!=len(set(ids)): return False,"duplicate_event_id"
    return True,"ok"

def objective(order,baseline,pairwise=None,profile=None):
    if not order: return -1e9
    profile=profile or _distance_profile(baseline,pairwise)
    adj=sum(_adjacency(a,b,pairwise) for a,b in zip(order,order[1:]))/max(1,len(order)-1)
    near,two,far=_adaptive_monotony(order,pairwise,profile)
    return (.22*_opener(order[0])+.22*_closer(order[-1])+.38*adj
            -.06*_repeat_source(order)-.03*_displacement(order,baseline)
            -.10*near-.08*two-.04*far)

def plan_sequence(events,pairwise=None,min_improvement=.025,max_exact=8):
    """Conservative reorder-only planner with hard baseline non-regression.

    The selected event set is immutable. Candidate orders are rejected when
    they worsen any frozen montage-health metric versus exact V52 baseline:
    opener, closer, adaptive near/two-step/far severity, fixed 0.06/0.10/0.22
    counters, source switches, or same-source adjacency.
    """
    ok,reason=validate(events); baseline=list(events)
    if not ok:
        return {"algorithm":ALGO_VERSION,"changed":False,"reason":"fallback_"+reason,
                "order":[_id(e) for e in baseline] if isinstance(events,list) else []}
    profile=_distance_profile(baseline,pairwise)
    base=objective(baseline,baseline,pairwise,profile)
    if len(events)<3 or len(events)>max_exact:
        return {"algorithm":ALGO_VERSION,"changed":False,
                "reason":"small_or_large_sequence_keep_baseline",
                "baseline_score":round(base,8),"planned_score":round(base,8),
                "improvement":0.0,"order":[_id(e) for e in baseline],
                "baseline_order":[_id(e) for e in baseline]}

    best=baseline; best_score=base; eligible=0
    for perm in permutations(events):
        perm=list(perm); g=_guard_map(perm,baseline,pairwise,profile)
        if not _guards_pass(g): continue
        eligible+=1
        s=objective(perm,baseline,pairwise,profile)
        ids=tuple(_id(e) for e in perm); bestids=tuple(_id(e) for e in best)
        if s>best_score+1e-12 or (abs(s-best_score)<=1e-12 and ids<bestids):
            best=perm; best_score=s

    gain=best_score-base
    if gain<float(min_improvement):
        best=baseline; best_score=base; changed=False
        why="insufficient_guarded_gain_keep_baseline"
    else:
        changed=[_id(e) for e in best]!=[_id(e) for e in baseline]
        why="guarded_objective_gain" if changed else "baseline_already_best"

    return {
        "algorithm":ALGO_VERSION,"changed":bool(changed),"reason":why,
        "baseline_score":round(base,8),"planned_score":round(best_score,8),
        "improvement":round(best_score-base,8),"eligible_permutations":eligible,
        "distance_profile":profile,
        "baseline_fixed_counts":_fixed_counts(baseline,pairwise),
        "planned_fixed_counts":_fixed_counts(best,pairwise),
        "guards":_guard_map(best,baseline,pairwise,profile),
        "order":[_id(e) for e in best],
        "baseline_order":[_id(e) for e in baseline],
        "selected_set_preserved":sorted(_id(e) for e in best)==sorted(_id(e) for e in baseline),
    }

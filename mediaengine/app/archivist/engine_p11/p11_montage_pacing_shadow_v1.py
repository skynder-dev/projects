from __future__ import annotations
import math
import numpy as np

ALGO_VERSION = "P11_MONTAGE_PACING_SHADOW_V1"
BASE_CLIP_SECONDS = 5.0
BASE_TRANSITION_SECONDS = 0.25

def _id(e): return str(e["event_id"])
def _m(e,k): return float((e.get("v22_metrics") or {})[k])
def _q(e): return float(e["v22_score"])
def _used(e, seconds=BASE_CLIP_SECONDS):
    return min(float(seconds), float(e.get("duration_s") or 0.0))

def _hold(e):
    return (
        .45*_q(e)
        + .20*_m(e,"stability")
        + .20*_m(e,"ending_quality")
        + .15*_m(e,"composition")
    )

def _distance(a,b,pairwise):
    if not pairwise: return None
    k=_id(a)+"->"+_id(b)
    if k in pairwise: return float(pairwise[k])
    rk=_id(b)+"->"+_id(a)
    return float(pairwise[rk]) if rk in pairwise else None

def _transition(a,b,pairwise):
    d=_distance(a,b,pairwise)
    sa=_m(a,"stability"); sb=_m(b,"stability")
    s=min(sa,sb)
    if d is None or not math.isfinite(d):
        return {"kind":"DISSOLVE","duration_s":BASE_TRANSITION_SECONDS,"reason":"missing_distance_baseline"}
    d=max(0.0,min(1.0,d))
    if d < .06:
        return {"kind":"HARD_CUT","duration_s":0.0,"reason":"near_duplicate_avoid_mush","distance":round(d,6)}
    if d > .22:
        return {"kind":"HARD_CUT","duration_s":0.0,"reason":"large_visual_jump_avoid_ghosting","distance":round(d,6)}
    closeness=max(0.0,min(1.0,1.0-abs(d-.13)/.10))
    dur=.11 + .09*closeness + .08*max(0.0,min(1.0,s))
    if s < .28:
        dur=min(dur,.15)
    dur=max(.10,min(.28,dur))
    return {
        "kind":"DISSOLVE",
        "duration_s":round(dur,3),
        "reason":"stability_scaled_dissolve",
        "distance":round(d,6),
        "min_stability":round(s,6),
    }

def _allocate(order,target_sum):
    baseline=[_used(e) for e in order]
    mins=[]
    maxs=[]
    for i,(e,b) in enumerate(zip(order,baseline)):
        source_max=float(e.get("duration_s") or b)
        lo=max(2.75,b-1.50)
        if i in (0,len(order)-1):
            lo=max(lo,min(b,3.75))
        lo=min(lo,source_max)
        hi=min(source_max,b+0.50,5.50)
        hi=max(lo,hi)
        mins.append(lo); maxs.append(hi)
    if target_sum < sum(mins)-1e-9 or target_sum > sum(maxs)+1e-9:
        return None, {"reason":"target_outside_duration_bounds","min_sum":sum(mins),"max_sum":sum(maxs)}

    holds=np.asarray([_hold(e) for e in order],float)
    med=float(np.median(holds))
    weights=np.exp(1.6*(holds-med))
    if len(order)>=2:
        weights[0]*=1.08
        weights[-1]*=1.10

    x=np.asarray(mins,float)
    hi=np.asarray(maxs,float)
    remaining=float(target_sum-x.sum())

    # Bounded weighted water-fill.
    for _ in range(64):
        if remaining <= 1e-9: break
        room=hi-x
        active=room>1e-9
        if not active.any(): break
        w=weights*active
        if w.sum()<=0: break
        proposal=remaining*w/w.sum()
        delta=np.minimum(room,proposal)
        used=float(delta.sum())
        x+=delta
        remaining-=used
        if used<=1e-10: break

    if abs(float(x.sum())-target_sum) > 1e-5:
        return None, {"reason":"waterfill_residual","residual":target_sum-float(x.sum())}

    # Millisecond-ish deterministic rounding with bounded residual correction.
    x=np.round(x,3)
    residual=round(target_sum-float(x.sum()),3)
    if abs(residual)>0:
        candidates=sorted(range(len(x)), key=lambda i:(weights[i],-i), reverse=True)
        for i in candidates:
            y=x[i]+residual
            if mins[i]-1e-9 <= y <= maxs[i]+1e-9:
                x[i]=round(y,3); residual=0.0; break

    if abs(target_sum-float(x.sum())) > .002:
        return None, {"reason":"rounding_residual","residual":target_sum-float(x.sum())}

    return [float(v) for v in x], {
        "baseline_durations":[round(v,3) for v in baseline],
        "min_durations":[round(v,3) for v in mins],
        "max_durations":[round(v,3) for v in maxs],
        "hold_scores":[round(float(v),6) for v in holds],
    }

def plan_pacing(order,target_seconds,pairwise=None):
    """Plan durations + boundary types for an already-selected, already-ordered reel.

    No event may be added, removed, or reordered. If target/bounds cannot be
    satisfied or final duration error is worse than V52 baseline, return the
    exact V52 5.0s / 0.25s dissolve pacing.
    """
    if not isinstance(order,list) or not order:
        return {"algorithm":ALGO_VERSION,"changed":False,"reason":"no_events","event_ids":[]}

    ids=[_id(e) for e in order]
    baseline_durs=[_used(e) for e in order]
    baseline_trans=[BASE_TRANSITION_SECONDS]*max(0,len(order)-1)
    baseline_final=sum(baseline_durs)-sum(baseline_trans)
    baseline_err=abs(float(target_seconds)-baseline_final)

    trans=[_transition(a,b,pairwise) for a,b in zip(order,order[1:])]
    trans_total=sum(float(t["duration_s"]) for t in trans)
    target_segment_sum=float(target_seconds)+trans_total

    durs,alloc_meta=_allocate(order,target_segment_sum)
    if durs is None:
        return {
            "algorithm":ALGO_VERSION,"changed":False,"reason":"fallback_"+alloc_meta["reason"],
            "event_ids":ids,"durations_s":[round(x,3) for x in baseline_durs],
            "transitions":[{"kind":"DISSOLVE","duration_s":BASE_TRANSITION_SECONDS,"reason":"v52_fallback"} for _ in baseline_trans],
            "expected_duration_s":round(baseline_final,3),
            "target_error_s":round(baseline_err,3),
            "baseline_expected_duration_s":round(baseline_final,3),
            "baseline_target_error_s":round(baseline_err,3),
            "selected_set_preserved":True,"order_preserved":True,
        }

    final=sum(durs)-trans_total
    err=abs(float(target_seconds)-final)

    guards={
        "target_error_nonregression":err <= baseline_err+1e-6,
        "event_count_preserved":len(durs)==len(order),
        "order_preserved":True,
        "all_duration_bounds":all(
            alloc_meta["min_durations"][i]-1e-6 <= durs[i] <= alloc_meta["max_durations"][i]+1e-6
            for i in range(len(durs))
        ),
        "transition_bounds":all(
            (t["kind"]=="HARD_CUT" and abs(float(t["duration_s"]))<1e-9) or
            (t["kind"]=="DISSOLVE" and .10-1e-9 <= float(t["duration_s"]) <= .28+1e-9)
            for t in trans
        ),
    }
    if not all(guards.values()):
        return {
            "algorithm":ALGO_VERSION,"changed":False,"reason":"fallback_guard_failure",
            "event_ids":ids,"durations_s":[round(x,3) for x in baseline_durs],
            "transitions":[{"kind":"DISSOLVE","duration_s":BASE_TRANSITION_SECONDS,"reason":"v52_fallback"} for _ in baseline_trans],
            "expected_duration_s":round(baseline_final,3),"target_error_s":round(baseline_err,3),
            "baseline_expected_duration_s":round(baseline_final,3),"baseline_target_error_s":round(baseline_err,3),
            "guards":guards,"selected_set_preserved":True,"order_preserved":True,
        }

    changed=(
        any(abs(a-b)>.005 for a,b in zip(durs,baseline_durs))
        or any(t["kind"]!="DISSOLVE" or abs(float(t["duration_s"])-BASE_TRANSITION_SECONDS)>.005 for t in trans)
    )
    return {
        "algorithm":ALGO_VERSION,
        "changed":bool(changed),
        "reason":"targeted_dynamic_pacing" if changed else "baseline_already_suitable",
        "event_ids":ids,
        "durations_s":[round(v,3) for v in durs],
        "transitions":trans,
        "expected_duration_s":round(final,3),
        "target_error_s":round(err,3),
        "baseline_expected_duration_s":round(baseline_final,3),
        "baseline_target_error_s":round(baseline_err,3),
        "duration_meta":alloc_meta,
        "guards":guards,
        "selected_set_preserved":True,
        "order_preserved":True,
    }

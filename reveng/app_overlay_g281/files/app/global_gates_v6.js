((root,factory)=>{
  const R=(typeof module==='object'&&module.exports)?require('./global_ranking_v6.js'):root&&root.RevEngGlobalRankingV6;
  const api=factory(R);
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngGlobalGatesV6=api;
})(typeof window!=='undefined'?window:globalThis,(V6)=>{
  'use strict';
  if(!V6||V6.CONTRACT_ID!=='reveng_global_ranking_v6_independent_v1') throw new Error('REVENG_GLOBAL_RANKING_V6_REQUIRED');
  // Hard gates and the final decision for the GLOBAL path. Pure functions, no I/O.
  // Rules carried over from the tested reference engine (50/50 tests) and from the first live scan:
  //  - an idea is compared with the CHEAPEST credible alternative (free tools, open source, DIY, status quo), not with the dearest incumbent;
  //  - a "fatal" deep-screen reason kills only when it cites provider-verified evidence; an uncited fatal reason is an unresolved condition;
  //  - a winner is never manufactured: the verdict is one of no_winner | conditional_winner | winner.
  const CONTRACT_ID='reveng_global_gates_v6_v1';
  const freeze=Object.freeze;
  const DEFAULTS=freeze({
    maxStartupCashUsd:10000,maxDaysToFirstRevenue:365,maxOwnerHoursPerWeek:40,minRelativeEdgeImprovement:0.25,
    minEvidenceItems:3,minVerifiedItems:2,requiredEvidenceKinds:freeze(['incumbent_price','demand','constraint']),
    minMarginPoints:5,minDeepScreened:5,majorKillReasonsSoftLimit:3
  });
  const ALT_KINDS=freeze(['paid_incumbent','free_tool','open_source','diy_or_status_quo']);
  const FREE_KINDS=freeze(['free_tool','open_source','diy_or_status_quo']);
  const COVERS=freeze(['full','partial','none']);
  const CRITERIA=freeze(['cash_cost','owner_time','cycle_time','step_count','channel_reach','required_tool_count']);
  const DIRECTIONS=freeze(['lower_is_better','higher_is_better']);
  const OWNER_LEAK=freeze([
    /\bmy (network|contacts|friends|company|truck|license|experience)\b/i,/\bthe owner'?s\b/i,/\bowner (has|already has|owns|knows)\b/i,
    /\bwarm (network|intro)/i,/\bprior (trucking|industry) experience\b/i,/\bcurrent user\b/i
  ]);
  const isNum=x=>typeof x==='number'&&Number.isFinite(x);
  const https=u=>/^https:\/\//i.test(String(u||''));
  const verified=x=>x&&x.evidenceClass==='verified';
  const R=(passed,reason)=>freeze({passed,reason});

  function gateReferenceEntrant(c,g){
    const r=c.referenceEntrant||{}, bad=[];
    if(!isNum(r.startupCashUsd)||!isNum(r.daysToFirstRevenue)||!isNum(r.ownerHoursPerWeek)) return R(false,'reference_entrant_missing_numbers');
    if(r.startupCashUsd>g.maxStartupCashUsd) bad.push(`startup_cash ${r.startupCashUsd}>${g.maxStartupCashUsd}`);
    if(r.daysToFirstRevenue>g.maxDaysToFirstRevenue) bad.push(`days_to_revenue ${r.daysToFirstRevenue}>${g.maxDaysToFirstRevenue}`);
    if(r.ownerHoursPerWeek>g.maxOwnerHoursPerWeek) bad.push(`owner_hours ${r.ownerHoursPerWeek}>${g.maxOwnerHoursPerWeek}`);
    return R(!bad.length,bad.join(';')||'ok');
  }

  // The cheapest-alternative check. Returns {passed, reason, cheapest, unresolved[]}. `unresolved` holds claims that are not provider-verified.
  function gateCheapestAlternative(c,g){
    const s=c.alternativesSurvey;
    if(!s||typeof s!=='object') return freeze({passed:false,reason:'no_alternatives_survey',cheapest:null,unresolved:freeze([])});
    if(s.freeSearchPerformed!==true) return freeze({passed:false,reason:'free_alternatives_not_searched',cheapest:null,unresolved:freeze([])});
    const alts=Array.isArray(s.alternatives)?s.alternatives:[];
    for(const a of alts){
      if(!ALT_KINDS.includes(a.kind)) return freeze({passed:false,reason:`alternative_bad_kind:${a.kind}`,cheapest:null,unresolved:freeze([])});
      if(!COVERS.includes(a.coversWedge)) return freeze({passed:false,reason:`alternative_bad_coverage:${a.coversWedge}`,cheapest:null,unresolved:freeze([])});
      if(!https(a.sourceLocator)) return freeze({passed:false,reason:'alternative_source_not_https',cheapest:null,unresolved:freeze([])});
    }
    const hasFreeKind=alts.some(a=>FREE_KINDS.includes(a.kind));
    if(!hasFreeKind&&!(s.noFreeAlternativeFound&&s.noFreeAlternativeFound.evidenceRef)) return freeze({passed:false,reason:'no_free_alternative_listed_and_absence_not_evidenced',cheapest:null,unresolved:freeze([])});
    const unresolved=[];
    // A free alternative that covers the whole wedge is fatal when verified, an unresolved condition when it is only claimed.
    for(const a of alts.filter(a=>FREE_KINDS.includes(a.kind)&&a.coversWedge==='full'&&Number(a.metrics&&a.metrics.cash_cost!==undefined?a.metrics.cash_cost:a.costUsdPerMonth)===0)){
      if(verified(a)) return freeze({passed:false,reason:`free_alternative_covers_wedge:${a.label}`,cheapest:a,unresolved:freeze(unresolved)});
      unresolved.push(`free_alternative_claimed_to_cover_wedge:${a.label}`);
    }
    const e=c.edgeMeasurement;
    if(!e||typeof e!=='object') return freeze({passed:false,reason:'no_edge_measurement',cheapest:null,unresolved:freeze(unresolved)});
    if(!CRITERIA.includes(e.criterionKey)) return freeze({passed:false,reason:'bad_criterion',cheapest:null,unresolved:freeze(unresolved)});
    if(!DIRECTIONS.includes(e.direction)) return freeze({passed:false,reason:'bad_direction',cheapest:null,unresolved:freeze(unresolved)});
    if(!String(e.falsifier||'').trim()) return freeze({passed:false,reason:'no_falsifier',cheapest:null,unresolved:freeze(unresolved)});
    const metric=a=>e.criterionKey==='cash_cost'?(a.metrics&&a.metrics.cash_cost!==undefined?a.metrics.cash_cost:a.costUsdPerMonth):(a.metrics||{})[e.criterionKey];
    const rivals=alts.filter(a=>a.coversWedge!=='none'&&isNum(metric(a)));
    if(!rivals.length) return freeze({passed:false,reason:'no_comparable_alternative_for_criterion',cheapest:null,unresolved:freeze(unresolved)});
    const best=rivals.reduce((m,a)=>{const better=e.direction==='lower_is_better'?metric(a)<metric(m):metric(a)>metric(m);return better?a:m;});
    const bestValue=metric(best);
    if(!isNum(e.incumbentValue)||!isNum(e.entrantValue)) return freeze({passed:false,reason:'edge_values_not_numeric',cheapest:best,unresolved:freeze(unresolved)});
    const worseThanBest=e.direction==='lower_is_better'?e.incumbentValue>bestValue:e.incumbentValue<bestValue;
    if(worseThanBest) return freeze({passed:false,reason:`edge_measured_against_non_best_alternative(compared=${e.incumbentValue},best=${bestValue}:${best.label})`,cheapest:best,unresolved:freeze(unresolved)});
    const delta=e.direction==='lower_is_better'?bestValue-e.entrantValue:e.entrantValue-bestValue;
    if(delta<=0) return freeze({passed:false,reason:`no_measured_advantage_over_best_alternative(best=${bestValue},entrant=${e.entrantValue})`,cheapest:best,unresolved:freeze(unresolved)});
    if(bestValue===0) return freeze({passed:false,reason:`best_alternative_is_free_on_${e.criterionKey}`,cheapest:best,unresolved:freeze(unresolved)});
    const rel=delta/Math.abs(bestValue);
    if(rel<g.minRelativeEdgeImprovement) return freeze({passed:false,reason:`improvement_below_threshold(${rel.toFixed(3)}<${g.minRelativeEdgeImprovement})`,cheapest:best,unresolved:freeze(unresolved)});
    return freeze({passed:true,reason:`relative_improvement_vs_best_alternative=${rel.toFixed(2)}`,cheapest:best,unresolved:freeze(unresolved)});
  }

  function gateEdgeEvidence(c){const g=V6.edgeGate(c.entrantEdge,Array.isArray(c.evidence)?c.evidence:[]);return R(g.passed,g.reason);}

  function gateEvidenceDepth(c,g){
    const ev=(Array.isArray(c.evidence)?c.evidence:[]).filter(x=>!V6.EXCLUDED_SOURCE_TYPES.includes(x&&x.sourceType));
    const nv=ev.filter(verified), kinds=new Set(nv.map(x=>x.kind)), r=[];
    if(ev.length<g.minEvidenceItems) r.push(`items ${ev.length}<${g.minEvidenceItems}`);
    if(nv.length<g.minVerifiedItems) r.push(`verified_items ${nv.length}<${g.minVerifiedItems}`);
    const miss=g.requiredEvidenceKinds.filter(k=>!kinds.has(k)); if(miss.length) r.push('missing_verified_kinds:'+miss.join(','));
    return R(!r.length,r.join(';')||'ok');
  }

  function gateOwnerLeak(c){
    const txt=['name','buyer','pain','wedge'].map(k=>String(c[k]||'')).join(' ')+' '+String((c.entrantEdge||{}).statement||'');
    const hits=OWNER_LEAK.filter(p=>p.test(txt)).map(String);
    return R(!hits.length,hits.length?'owner_specific_language:'+hits.join(','):'ok');
  }

  // Deep-screen kill: fatal AND provider-verified reference.
  function normalizeKillReasons(list){
    return (Array.isArray(list)?list:[]).filter(x=>x&&typeof x==='object'&&String(x.reason||'').trim()).map(x=>freeze({
      reason:String(x.reason).trim(),severity:['fatal','major','minor'].includes(x.severity)?x.severity:'minor',refClass:x.refClass||'unverified',ref:x.ref??null}));
  }
  function gateDeepKill(c){
    const k=normalizeKillReasons(c.deep&&c.deep.killReasons).filter(x=>x.severity==='fatal'&&x.refClass==='verified');
    return R(!k.length,k.length?'deep_screen_fatal:'+k.map(x=>x.reason).join(' | ').slice(0,400):'ok');
  }

  const ORDER=freeze([['reference_entrant',gateReferenceEntrant],['entrant_edge',gateEdgeEvidence],['evidence_depth',gateEvidenceDepth],['owner_leak',gateOwnerLeak],['deep_kill',gateDeepKill]]);
  function validate(c){
    const e=[];
    if(!c||typeof c!=='object'||Array.isArray(c)) return ['not_an_object'];
    for(const k of ['id','name','family','buyer','pain','wedge']) if(!String(c[k]??'').trim()) e.push('missing:'+k);
    return e;
  }
  function runGates(c,cfg={}){
    const g={...DEFAULTS,...cfg}, res={}, errs=validate(c);
    res.schema=R(!errs.length,errs.slice(0,5).join(';')||'ok');
    if(errs.length) return freeze({passed:false,gates:freeze(res),failed:freeze(['schema']),unresolved:freeze([])});
    const alt=gateCheapestAlternative(c,g);
    res.cheapest_alternative=R(alt.passed,alt.reason);
    for(const [n,fn] of ORDER) res[n]=fn(c,g);
    const failed=Object.keys(res).filter(k=>!res[k].passed);
    return freeze({passed:!failed.length,gates:freeze(res),failed:freeze(failed),unresolved:alt.unresolved,cheapestAlternative:alt.cheapest?alt.cheapest.label:null});
  }

  // ---- decision -------------------------------------------------------------------------------------------------------------
  // scan: output of RevEngGlobalScanV6.assess (valid scan or not). rows: V6.score() outputs. gateById: runGates() outputs. candidatesById: raw candidates (deep data).
  function decide({scan,rows,gateById,candidatesById,cfg={},provisional=false}){
    const t={...DEFAULTS,...cfg}, reasons=[], hard=[];
    const chk=(ok,msg,isHard=true)=>{if(!ok){reasons.push(msg);if(isHard)hard.push(msg);}};
    chk(!!scan&&scan.valid===true,`scan_not_valid:${scan?scan.reasons.join('|'):'missing'}`);
    const integrity=[];
    for(const r of rows) for(const v of V6.integrity(r)) integrity.push(`${r.id}:${v}`);
    chk(!integrity.length,`score_integrity_violations:${integrity.slice(0,3).join('|')}`);
    chk(!provisional,'provisional_run:evidence_not_engine_verified');
    const survivors=rows.filter(r=>gateById[r.id]&&gateById[r.id].passed&&r.deep_screen_eligible);
    const ranking=V6.rank(survivors);
    chk(survivors.length>0,'no_candidate_survived_hard_gates');
    const top=ranking[0], second=ranking[1];
    let margin=null;
    if(top){
      const tc=candidatesById[top.id]||{}, deep=tc.deep||{};
      chk(!!(deep.done&&deep.complete),`top_candidate_not_deep_screened(${top.id})`);
      const deepCount=Object.values(candidatesById).filter(x=>x.deep&&x.deep.complete).length;
      chk(deepCount>=Math.min(t.minDeepScreened,survivors.length),`deep_screened ${deepCount}<${Math.min(t.minDeepScreened,survivors.length)}`);
      margin=second?Math.round((top.adjusted_score-second.adjusted_score)*1000)/1000:null;
      chk(second===undefined||margin>=t.minMarginPoints,`margin_over_runner_up ${margin}<${t.minMarginPoints}`,false);
      chk(!!(deep.economics&&deep.economics.survivesPessimistic),'top_fails_or_lacks_pessimistic_economics',false);
      const kr=normalizeKillReasons(deep.killReasons);
      const unresolved=kr.filter(k=>k.severity==='fatal'&&k.refClass!=='verified'), majors=kr.filter(k=>k.severity==='major');
      chk(!unresolved.length,`top_has_uncited_fatal_claims(${unresolved.length}):${unresolved.map(k=>k.reason).join(' | ').slice(0,300)}`,false);
      chk(majors.length<t.majorKillReasonsSoftLimit,`top_has_${majors.length}_major_kill_reasons`,false);
      const gu=(gateById[top.id]||{}).unresolved||[];
      chk(!gu.length,`top_has_unresolved_free_alternative_claims(${gu.length})`,false);
    }
    const verdict=hard.length?'no_winner':(reasons.length?'conditional_winner':'winner');
    return freeze({
      verdict,leader:verdict==='no_winner'?null:(top?top.id:null),unmet_conditions:freeze(reasons),hard_blockers:freeze(hard),
      margin_adjusted_points:margin,survivors:survivors.length,
      ranking:freeze(ranking.map(r=>freeze({id:r.id,family:r.family,adjusted_score:r.adjusted_score,raw_score:r.raw_score}))),integrity_violations:freeze(integrity)
    });
  }
  return freeze({CONTRACT_ID,DEFAULTS,ALT_KINDS,runGates,normalizeKillReasons,decide,gateCheapestAlternative});
});

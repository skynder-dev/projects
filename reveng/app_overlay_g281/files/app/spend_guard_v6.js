((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngSpendGuardV6=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  // Production-side counterpart of the simulation-only advisory budget ledger (G224). Pure functions: the caller owns persistence and passes the ledger in.
  // Rules: (1) no paid call without an EXPLICIT dollar authorization confirmed by the owner; (2) spend is cumulative per scope across runs, retries and reruns;
  // (3) every attempt reserves its maximum estimate BEFORE the call; (4) a fatal provider error (credits, auth) blocks all further attempts until a new authorization;
  // (5) simulated or implied authorization never counts.
  const CONTRACT_ID='reveng_spend_guard_v6_v1';
  const freeze=Object.freeze;
  const money=v=>{const n=Number(v);return Number.isFinite(n)&&n>=0?Math.round((n+Number.EPSILON)*1e6)/1e6:null;};
  const ok=(extra)=>freeze({ok:true,...extra});
  const no=(reason,extra={})=>freeze({ok:false,reason,...extra});
  // Calibration measured on the first live scan (30 calls): 1,595,644 input / 250,633 output tokens, 90 searches, Sonnet 5.5 at $2/$10 per MTok and $0.01/search = $6.597618.
  const CALIBRATION=freeze({source:'live_scan_1_measured',calls:30,inputTokens:1595644,outputTokens:250633,searches:90,usd:6.597618,
    perCall:freeze({inputTokens:1595644/30,outputTokens:250633/30,searches:3}),prices:freeze({inPerMTok:2,outPerMTok:10,perSearch:0.01})});
  const SAFETY=1.5;
  // Estimate of a planned run. Prices must be supplied for any model other than the measured one; they are never guessed.
  function estimateRun({calls,prices=CALIBRATION.prices,perCall=CALIBRATION.perCall}={}){
    const n=Number(calls);
    if(!Number.isInteger(n)||n<1) return no('calls_must_be_positive_integer');
    for(const k of ['inPerMTok','outPerMTok','perSearch']) if(!Number.isFinite(prices[k])||prices[k]<0) return no('price_missing:'+k);
    const per=perCall.inputTokens/1e6*prices.inPerMTok+perCall.outputTokens/1e6*prices.outPerMTok+perCall.searches*prices.perSearch;
    return ok({calls:n,expectedUsd:money(per*n),maxUsd:money(per*n*SAFETY),perCallUsd:money(per),basis:prices===CALIBRATION.prices&&perCall===CALIBRATION.perCall?CALIBRATION.source:'caller_supplied',safetyFactor:SAFETY});
  }
  const entries=l=>Array.isArray(l&&l.entries)?l.entries:[];
  function totals(ledger,scopeKey){
    let spent=0,reserved=0,fatalAt=null;
    const settled=new Set(entries(ledger).filter(e=>e.scopeKey===scopeKey&&e.kind==='actual').map(e=>e.attemptId));
    for(const e of entries(ledger)){
      if(e.scopeKey!==scopeKey) continue;
      if(e.kind==='actual') spent+=money(e.usd)||0;
      else if(e.kind==='reservation'&&!settled.has(e.attemptId)) reserved+=money(e.usd)||0;
      else if(e.kind==='provider_fatal') fatalAt=e.at;
    }
    return {spent:money(spent),reserved:money(reserved),fatalAt};
  }
  function validAuthorization(a){
    if(!a||typeof a!=='object') return 'no_authorization';
    if(a.simulated===true) return 'simulated_authorization_never_counts';
    if(!String(a.scopeKey||'').trim()) return 'scope_key_required';
    const amt=money(a.amountUsd); if(amt===null||amt<=0) return 'explicit_positive_dollar_amount_required';
    if(a.confirmedByOwner!==true) return 'owner_confirmation_missing';
    if(!String(a.confirmationText||'').trim()) return 'owner_confirmation_text_missing';
    if(Number.isNaN(Date.parse(a.confirmedAt))) return 'confirmed_at_required';
    return null;
  }
  // Reserve the maximum cost of one attempt. Returns {ok, ledger} (new ledger) or {ok:false, reason}.
  function reserve({authorization,ledger,attemptId,estimatedMaxUsd}){
    const bad=validAuthorization(authorization); if(bad) return no(bad);
    const id=String(attemptId||'').trim(); if(!id) return no('attempt_id_required');
    const est=money(estimatedMaxUsd); if(est===null||est<=0) return no('estimate_required');
    const scope=authorization.scopeKey, t=totals(ledger,scope);
    if(t.fatalAt&&!(Date.parse(authorization.confirmedAt)>Date.parse(t.fatalAt))) return no('provider_fatal_blocks_calls_until_new_authorization',{fatalAt:t.fatalAt});
    const dup=entries(ledger).find(e=>e.scopeKey===scope&&e.attemptId===id&&e.kind==='reservation');
    if(dup) return ok({ledger,idempotent:true});
    const remaining=money(authorization.amountUsd-t.spent-t.reserved);
    if(est>remaining) return no('would_exceed_authorized_amount',{authorizedUsd:authorization.amountUsd,spentUsd:t.spent,reservedUsd:t.reserved,remainingUsd:Math.max(0,remaining),requestedUsd:est});
    return ok({ledger:freeze({entries:freeze([...entries(ledger),freeze({kind:'reservation',scopeKey:scope,attemptId:id,usd:est,at:authorization.confirmedAt})])}),remainingAfterUsd:money(remaining-est)});
  }
  // Settle an attempt with the provider-reported usage cost (an estimate until a billing receipt confirms it).
  function settle({ledger,scopeKey,attemptId,actualUsd,at}){
    const a=money(actualUsd); if(a===null) return no('actual_usd_required');
    if(!entries(ledger).some(e=>e.scopeKey===scopeKey&&e.attemptId===attemptId&&e.kind==='reservation')) return no('no_reservation_for_attempt');
    if(entries(ledger).some(e=>e.scopeKey===scopeKey&&e.attemptId===attemptId&&e.kind==='actual')) return ok({ledger,idempotent:true});
    return ok({ledger:freeze({entries:freeze([...entries(ledger),freeze({kind:'actual',scopeKey,attemptId,usd:a,usdBasis:'provider_usage_estimate_not_billing_receipt',at:at||null})])})});
  }
  function recordFatal({ledger,scopeKey,at,message}){
    return freeze({entries:freeze([...entries(ledger),freeze({kind:'provider_fatal',scopeKey,at,message:String(message||'').slice(0,300)})])});
  }
  return freeze({CONTRACT_ID,CALIBRATION,SAFETY,estimateRun,totals,validAuthorization,reserve,settle,recordFatal});
});

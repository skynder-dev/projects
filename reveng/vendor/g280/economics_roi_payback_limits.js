(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RevEngEconomicsRoiPaybackLimits=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const CONTRACT_ID='reveng_roi_payback_limits_v1';
  const frozen=o=>Object.freeze(o);
  const finite=v=>{if(v===null||v===undefined||v==='')return null;const n=typeof v==='number'?v:Number(v);return Number.isFinite(n)?n:null;};
  const positive=v=>{const n=finite(v);return n!==null&&n>0?n:null;};
  const clean=v=>v===null||v===undefined?null:String(v).trim()||null;
  function normalizePeriod(input){
    const months=positive(input?.months??input?.periodMonths);
    if(months===null)return frozen({known:false,months:null,unit:'months',status:'unknown',reason:'period_missing_or_invalid'});
    return frozen({known:true,months,unit:'months',status:'explicit',reason:null});
  }
  function normalizeSalesRate(mapped,provenance){
    const row=mapped?.fields?.volume||{}; const prov=provenance?.rows?.volume||{};
    if(row.known!==true)return frozen({known:false,value:null,unit:'units_per_month',period:'month',status:'unknown',sourceRef:null,reason:row.unknownReason||'sales_rate_missing'});
    const status=['verified','assumed'].includes(String(prov.status||''))?String(prov.status):'unknown';
    return frozen({known:true,value:finite(row.value),unit:'units_per_month',period:'month',status,sourceRef:clean(prov.sourceRef)||clean(row.sourceKey),reason:status==='unknown'?'sales_rate_provenance_unknown':null});
  }
  function metric(status,value,unit,period,reason){return frozen({status,value,known:value!==null,unit,period,reason:reason||null});}
  function evaluate(monthlyReference,mapped,provenance,opts={}){
    const period=normalizePeriod(opts.period||opts);
    const salesRate=normalizeSalesRate(mapped,provenance);
    const startupRow=mapped?.legacy?.startup||{};
    const startup=startupRow.known===true?finite(startupRow.value):null;
    const contribution=monthlyReference?.status==='verified'?finite(monthlyReference?.reference?.contributionUsdPerMonth):null;
    const referenceStatus=String(monthlyReference?.status||'unverified');
    let status='evaluated',reason=null;
    if(referenceStatus==='bug'){status='blocked_reference_bug';reason='monthly_contribution_reference_bug';}
    else if(contribution===null){status='unverified';reason='cash_contribution_unverified';}
    else if(startup===null){status='unverified';reason='startup_cash_missing';}
    else if(!period.known){status='unverified';reason=period.reason;}
    else if(!salesRate.known){status='unverified';reason=salesRate.reason;}
    else if(salesRate.status==='unknown'){status='unverified';reason='sales_rate_provenance_unknown';}
    let roi=metric('unverified',null,'percent',period.known?`${period.months}_months`:'unknown_period',reason);
    let payback=metric('unverified',null,'months','payback',reason);
    if(status==='evaluated'){
      if(startup===0){
        roi=metric('not_applicable',null,'percent',`${period.months}_months`,'zero_startup_denominator');
        payback=metric('not_applicable',null,'months','payback','no_startup_cash_to_recover');
      }else{
        const roiValue=((contribution*period.months-startup)/startup)*100;
        roi=metric('calculated',Math.round(roiValue*10)/10,'percent',`${period.months}_months`,null);
        if(contribution>0){
          payback=metric('calculated',Math.round((startup/contribution)*10)/10,'months','payback',null);
        }else{
          payback=metric('no_payback',null,'months','payback','non_positive_cash_contribution');
        }
      }
    }
    return frozen({
      contractId:CONTRACT_ID,status,reason,
      period,salesRate,
      startupCash:frozen({known:startup!==null,value:startup,unit:'usd',period:'one_time',sourceKey:startupRow.sourceKey||null}),
      cashContribution:frozen({known:contribution!==null,value:contribution,unit:'usd',period:'month',referenceStatus}),
      firstPeriodStartupRoi:roi,startupPayback:payback,
      zeroStartupProducesInfiniteRoi:false,
      nonPositiveContributionProducesFinitePayback:false,
      missingInputsProduceZero:false,
      salesRateIsDemandProof:false,
      marketValidationAuthority:false,
      legacyMetricsMutated:false
    });
  }
  return frozen({CONTRACT_ID,normalizePeriod,normalizeSalesRate,evaluate});
});

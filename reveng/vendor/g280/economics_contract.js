(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RevEngEconomicsContract=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const INPUT_KEYS=['price','units','revenue','cashCost','contribution','ownerHours','startup','automation','launchDays'];
  const SCHEMA=Object.freeze({
    price:{category:'input',unit:'usd',period:'per_unit'},
    units:{category:'input',unit:'count',period:'month'},
    revenue:{category:'input',unit:'usd',period:'month'},
    cashCost:{category:'input',unit:'usd',period:'month'},
    contribution:{category:'input',unit:'usd',period:'month'},
    ownerHours:{category:'input',unit:'hours',period:'month'},
    startup:{category:'input',unit:'usd',period:'one_time'},
    automation:{category:'input',unit:'percent',period:'snapshot'},
    launchDays:{category:'input',unit:'days',period:'launch'},
    cashMargin:{category:'derived',unit:'percent',period:'month'},
    profitOwnerHour:{category:'derived',unit:'usd_per_hour',period:'month'},
    startupPayback:{category:'derived',unit:'months',period:'payback'},
    firstYearStartupRoi:{category:'derived',unit:'percent',period:'first_year'}
  });

  const own=(o,k)=>Object.prototype.hasOwnProperty.call(o||{},k);
  const finiteNumber=(v)=>{
    if(v===null||v===undefined||v==='')return null;
    const n=typeof v==='number'?v:Number(v);
    return Number.isFinite(n)?n:null;
  };
  const unknown=(key,source,reason)=>Object.freeze({
    key,value:null,known:false,source,period:SCHEMA[key].period,category:SCHEMA[key].category,unit:SCHEMA[key].unit,unknown_reason:reason||'not_loaded'
  });
  const known=(key,value,source)=>Object.freeze({
    key,value,known:true,source,period:SCHEMA[key].period,category:SCHEMA[key].category,unit:SCHEMA[key].unit,unknown_reason:null
  });
  const inputMetric=(raw,key,source,loaded)=>{
    if(!loaded)return unknown(key,source,'source_not_loaded');
    if(!own(raw,key))return unknown(key,source,'field_missing');
    const n=finiteNumber(raw[key]);
    return n===null?unknown(key,source,'invalid_or_empty'):known(key,n,source);
  };
  const derive=(key,deps,source,fn,guard)=>{
    if(deps.some(m=>!m.known))return unknown(key,`derived:${source}`,'dependency_unknown');
    const values=deps.map(m=>m.value);
    if(guard && !guard(...values))return unknown(key,`derived:${source}`,'formula_not_applicable');
    const value=fn(...values);
    return Number.isFinite(value)?known(key,value,`derived:${source}`):unknown(key,`derived:${source}`,'invalid_derived_value');
  };

  function normalize(raw,opts={}){
    const source=String(opts.source||'unknown_source');
    const loaded=opts.loaded!==false;
    const sourceRaw=raw&&typeof raw==='object'?raw:{};
    const out={};
    for(const key of INPUT_KEYS)out[key]=inputMetric(sourceRaw,key,source,loaded);
    out.cashMargin=derive('cashMargin',[out.contribution,out.revenue],source,(c,r)=>Math.round((c/r)*100),(_c,r)=>r>0);
    out.profitOwnerHour=derive('profitOwnerHour',[out.contribution,out.ownerHours],source,(c,h)=>Math.round(c/h),(_c,h)=>h>0);
    out.startupPayback=derive('startupPayback',[out.startup,out.contribution],source,(s,c)=>Math.round((s/c)*10)/10,(s,c)=>s>0&&c>0);
    out.firstYearStartupRoi=derive('firstYearStartupRoi',[out.contribution,out.startup],source,(c,s)=>Math.round(((c*12-s)/s)*100),(_c,s)=>s>0);
    return Object.freeze(out);
  }

  function backendRowToRaw(row){
    if(!row||typeof row!=='object')return {};
    const map={
      price:'price_per_unit',units:'units_per_month',revenue:'gross_revenue',cashCost:'total_cash_cost',contribution:'cash_contribution',ownerHours:'recurring_owner_hours',startup:'startup_cash_cost',automation:'automation_pct',launchDays:'time_to_launch_days'
    };
    const out={};
    for(const [target,source] of Object.entries(map))if(own(row,source))out[target]=row[source];
    return out;
  }

  return Object.freeze({schema:SCHEMA,inputKeys:Object.freeze([...INPUT_KEYS]),normalize,backendRowToRaw});
});

((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngGlobalScanV6=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  // Validity rules for a GLOBAL discovery scan. This is a separate mode next to the mandate-bound bounded pilot scope
  // (reveng_bounded_discovery_scope_v1: max 12 candidates, mandate-bound), which is unchanged.
  // A scan that is too small, too narrow, duplicated, mixed-protocol or owner-tainted is invalid and can never produce a winner.
  const CONTRACT_ID='reveng_global_scan_v6_v1';
  const freeze=Object.freeze;
  const REQUIRED_FAMILIES=freeze(['games','saas_or_micro_saas','ecommerce_or_dropshipping','services','marketplaces','digital_or_data_products','physical_products','media_or_content']);
  const EXTRA_FAMILIES=freeze(['affiliate_or_referral','local_businesses','b2b_operations','consumer_products','education_training','b2b_api_devtools']);
  const ALL_FAMILIES=freeze([...REQUIRED_FAMILIES,...EXTRA_FAMILIES]);
  const DEFAULTS=freeze({minRaw:30,minFamilies:8,minPerRequiredFamily:3});
  const OWNER_KEYS=freeze(new Set(['owner','ownername','biography','personalnetwork','contacts','mandate','userfit','ownerfit','email','phone','employer','privateaccess','priorindustryexperience']));
  const norm=k=>String(k).toLowerCase().replace(/[^a-z0-9]/g,'');
  const nameKey=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();

  function assess(candidates,cfg={}){
    const t={...DEFAULTS,...cfg}, reasons=[];
    const list=Array.isArray(candidates)?candidates:[];
    const byFamily={}, ids=new Set(), names=new Set(), dupIds=[], dupNames=[], unknownFamilies=new Set(), tainted=[], protocols=new Set();
    for(const c of list){
      const f=String((c&&c.family)||'');
      byFamily[f]=(byFamily[f]||0)+1;
      if(f&&!ALL_FAMILIES.includes(f)) unknownFamilies.add(f);
      if(ids.has(c&&c.id)) dupIds.push(c.id); else ids.add(c&&c.id);
      const nk=nameKey(c&&c.name); if(nk){ if(names.has(nk)) dupNames.push(c.name); else names.add(nk); }
      if(c&&typeof c==='object'&&Object.keys(c).some(k=>OWNER_KEYS.has(norm(k)))) tainted.push(c.id);
      protocols.add(String((c&&c.researchProtocol)||'unspecified'));
    }
    const represented=Object.keys(byFamily).filter(f=>ALL_FAMILIES.includes(f)&&byFamily[f]>0);
    const thin=REQUIRED_FAMILIES.filter(f=>(byFamily[f]||0)<t.minPerRequiredFamily);
    if(list.length<t.minRaw) reasons.push(`raw_candidates ${list.length}<${t.minRaw}`);
    if(represented.length<t.minFamilies) reasons.push(`families ${represented.length}<${t.minFamilies}`);
    if(thin.length) reasons.push(`required_families_underrepresented(<${t.minPerRequiredFamily}):${thin.join(',')}`);
    if(dupIds.length) reasons.push(`duplicate_ids:${dupIds.join(',')}`);
    if(dupNames.length) reasons.push(`duplicate_names:${dupNames.slice(0,5).join(',')}`);
    if(unknownFamilies.size) reasons.push(`unknown_families:${[...unknownFamilies].join(',')}`);
    if(tainted.length) reasons.push(`owner_context_in_candidates:${tainted.join(',')}`);
    if(protocols.size>1) reasons.push(`mixed_research_protocols:${[...protocols].sort().join(',')}`);
    return freeze({contract:CONTRACT_ID,valid:reasons.length===0,reasons:freeze(reasons),rawCandidates:list.length,familiesRepresented:represented.length,byFamily:freeze(byFamily),thinFamilies:freeze(thin)});
  }
  return freeze({CONTRACT_ID,REQUIRED_FAMILIES,EXTRA_FAMILIES,ALL_FAMILIES,DEFAULTS,assess});
});

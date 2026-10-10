((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngEvidenceProtocolV6=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  // Two-phase, provider-agnostic evidence protocol + the legal source policy. Pure functions: this module never performs I/O.
  //  Phase 1 (provider web search ON): research notes; the PROVIDER attaches citations {url,title,cited_text}.
  //  Phase 2 (search OFF): the model returns JSON in which every evidence item is a REFERENCE (C# = citation excerpt, S# = search-result URL).
  //  Evidence text and URLs therefore come from the provider, never from model memory; invented references are dropped.
  //  Classes: verified (C#) > search_confirmed (S#) > agent_reported > unverified. Classes are never promoted.
  // The source policy mirrors reveng.pilot_allowed_sources (pinned in server/REVA2_G281_SOURCE_POLICY_SNAPSHOT.json).
  const CONTRACT_ID='reveng_evidence_protocol_v6_v1';
  const freeze=Object.freeze;
  const KINDS=freeze(['incumbent_price','demand','constraint','other']);
  // Collection methods. Only the first group is ever allowed; the second group is forbidden regardless of any option.
  const ALLOWED_METHODS=freeze({
    provider_search_citation:'public_web_search',      // provider's own search tool returns citations; we never open the page ourselves
    manual_public_review:'public_marketplace_review',  // a person (or the agent as a normal reader) reads public pages; no automation
    official_api_documented:'official_api'              // blocked until a concrete API, credentials and terms are configured
  });
  const FORBIDDEN_METHODS=freeze(['http_scrape','headless_browser_scrape','bulk_download','login_bypass','paywall_bypass','captcha_bypass','robots_ignored','undocumented_endpoint']);
  const FATAL_PROVIDER=/credit balance|anthropic_http_(401|403)|invalid x-api-key|authentication_error|permission_error|insufficient_quota|billing_hard_limit/i;
  const host=u=>{try{return new URL(u).hostname.replace(/^www\./,'');}catch(_){return '';}};
  const https=u=>/^https:\/\//i.test(String(u||''));

  function policyFor(snapshot,sourceKey){return (snapshot&&snapshot.sources||[]).find(s=>s.source_key===sourceKey)||null;}
  // Is a collection method allowed under the pinned policy? Returns {allowed, reason, sourceKey, eligibility}.
  function checkMethod(snapshot,method){
    if(FORBIDDEN_METHODS.includes(method)) return freeze({allowed:false,reason:'forbidden_method',sourceKey:null,eligibility:null});
    const key=ALLOWED_METHODS[method];
    if(!key) return freeze({allowed:false,reason:'unknown_method',sourceKey:null,eligibility:null});
    const p=policyFor(snapshot,key);
    if(!p) return freeze({allowed:false,reason:'source_not_in_policy',sourceKey:key,eligibility:null});
    if(p.activation_state==='not_configured') return freeze({allowed:false,reason:'source_not_configured',sourceKey:key,eligibility:p.evidence_eligibility});
    if(p.evidence_eligibility==='hypothesis_only'||p.evidence_eligibility==='workspace_private_only') return freeze({allowed:false,reason:`not_global_evidence:${p.evidence_eligibility}`,sourceKey:key,eligibility:p.evidence_eligibility});
    return freeze({allowed:true,reason:'ok',sourceKey:key,eligibility:p.evidence_eligibility});
  }
  function assertMethod(snapshot,method){const r=checkMethod(snapshot,method);if(!r.allowed){const e=new Error(`REVENG_SOURCE_METHOD_REFUSED:${method}:${r.reason}`);e.code='REVENG_SOURCE_METHOD_REFUSED';throw e;}return r;}

  // Build the reference index from a provider response {citations:[{url,title,cited_text}], searchResults:[{url,title,page_age}]}.
  function buildRefIndex(res,limits={excerpts:70,results:40}){
    const excerpts=[],results=[],seen=new Set(),seenU=new Set();
    for(const c of (res&&res.citations)||[]){
      const k=c.url+'|'+c.cited_text;
      if(c.cited_text&&https(c.url)&&!seen.has(k)){seen.add(k);excerpts.push({id:'C'+(excerpts.length+1),url:c.url,title:c.title||'',cited_text:String(c.cited_text).slice(0,600)});}
    }
    for(const r of (res&&res.searchResults)||[]) if(https(r.url)&&!seenU.has(r.url)){seenU.add(r.url);results.push({id:'S'+(results.length+1),url:r.url,title:r.title||'',page_age:r.page_age||null});}
    const ex=excerpts.slice(0,limits.excerpts), rs=results.slice(0,limits.results);
    return freeze({excerpts:ex,results:rs,byId:freeze(Object.fromEntries([...ex,...rs].map(x=>[x.id,x])))});
  }
  // Resolve phase-2 items [{ref:'C3',kind,shows}] against the index. Unknown refs / kinds are dropped and counted.
  function resolveEvidence(items,idx,idPrefix){
    const evidence=[],map={};let dropped=0;
    (Array.isArray(items)?items:[]).forEach((it,i)=>{
      const ref=it&&String(it.ref||'').trim(), src=ref&&idx.byId[ref];
      if(!src||!KINDS.includes(it.kind)){dropped++;return;}
      const isC=ref[0]==='C', id=`${idPrefix}${evidence.length+1}`;
      evidence.push(freeze({id,url:src.url,publisher:src.title||host(src.url),date:src.page_age||'undated',quote:isC?src.cited_text:null,shows:String(it.shows||''),kind:it.kind,
        evidenceClass:isC?'verified':'search_confirmed',sourceType:'public_web_search',method:isC?'provider_citation_excerpt':'provider_search_result_url'}));
      map[`E${i+1}`]=id;
    });
    return freeze({evidence:freeze(evidence),map:freeze(map),dropped});
  }
  // Evidence that arrives without provider verification (manual notes, imported JSON) is labelled, never promoted.
  function markAgentReported(items,idPrefix){
    return freeze((Array.isArray(items)?items:[]).map((x,i)=>freeze({id:x.id||`${idPrefix}${i+1}`,url:x.url||null,quote:x.quote||null,shows:String(x.shows||''),kind:KINDS.includes(x.kind)?x.kind:'other',
      evidenceClass:'agent_reported',sourceType:x.sourceType==='owner_provided'?'owner_provided':'manual_public_review',method:'manual_note_not_checked'})));
  }
  const classifyProviderError=msg=>FATAL_PROVIDER.test(String(msg||''))?'fatal':'transient';
  return freeze({CONTRACT_ID,KINDS,ALLOWED_METHODS,FORBIDDEN_METHODS,FATAL_PROVIDER,policyFor,checkMethod,assertMethod,buildRefIndex,resolveEvidence,markAgentReported,classifyProviderError});
});

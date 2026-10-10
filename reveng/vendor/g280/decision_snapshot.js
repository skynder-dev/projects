((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RevEngDecisionSnapshot=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  const CONTRACT_ID='reveng_decision_snapshot_v1';
  const STATES=Object.freeze(['verified','unverified','unknown','stale']);
  const SECTIONS=Object.freeze(['buyer','channel','economics','resources','risks','openQuestions']);
  const clean=v=>String(v??'').trim();
  const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
  const deepFreeze=v=>{if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);Object.values(v).forEach(deepFreeze);}return v;};
  const stable=v=>{if(v===undefined)return 'null';if(Array.isArray(v))return '['+v.map(stable).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';return JSON.stringify(v);};
  const digest=v=>{let h=0x811c9dc5;for(const ch of stable(v)){h^=ch.charCodeAt(0);h=Math.imul(h,0x01000193)>>>0;}return 'fnv1a:'+h.toString(16).padStart(8,'0');};
  const rejected=(reason,extra={})=>deepFreeze({contractId:CONTRACT_ID,status:'rejected',reason,...extra,decisionAuthority:false,recommendationAuthority:false,winnerAuthority:false,acceptedStateMutationAllowed:false});

  function sourceBinding(raw={}){
    const contractId=clean(raw.contractId),objectId=clean(raw.objectId),dg=clean(raw.digest);
    const version=Number(raw.version);
    if(!contractId||!objectId||!dg||!Number.isInteger(version)||version<1)return null;
    return deepFreeze({contractId,objectId,version,digest:dg});
  }
  function row(raw,index){
    const key=clean(raw?.key)||`row_${index+1}`;
    const label=clean(raw?.label)||key;
    const state=clean(raw?.state);
    if(!STATES.includes(state))throw new Error(`REVENG_DECISION_SNAPSHOT_STATE_INVALID_${key}`);
    const reason=clean(raw?.reason)||null;
    const sourceRef=clean(raw?.sourceRef)||null;
    let value=Object.prototype.hasOwnProperty.call(raw||{},'value')?clone(raw.value):null;
    if(state==='unknown')value=null;
    return deepFreeze({key,label,state,value,reason,sourceRef,claimable:state==='verified'});
  }
  function section(name,raw={}){
    const source=sourceBinding(raw.source);
    if(!source)throw new Error(`REVENG_DECISION_SNAPSHOT_SOURCE_INVALID_${name}`);
    const rows=Array.isArray(raw.rows)?raw.rows.map(row):[];
    if(!rows.length)throw new Error(`REVENG_DECISION_SNAPSHOT_ROWS_REQUIRED_${name}`);
    const seen=new Set();
    for(const r of rows){if(seen.has(r.key))throw new Error(`REVENG_DECISION_SNAPSHOT_DUPLICATE_KEY_${name}_${r.key}`);seen.add(r.key);}
    return deepFreeze({name,source,rows});
  }
  function build(input={}){
    const workspaceId=clean(input.workspaceId),opportunityId=clean(input.opportunityId),revisionId=clean(input.revisionId);
    const revisionVersion=Number(input.revisionVersion);
    if(!workspaceId||!opportunityId||!revisionId||!Number.isInteger(revisionVersion)||revisionVersion<1)return rejected('scope_or_revision_binding_invalid');
    const built={};
    try{for(const name of SECTIONS)built[name]=section(name,input[name]);}
    catch(err){return rejected('section_invalid',{detail:String(err?.message||err)});}
    const claimableFacts=[]; const unresolved=[];
    for(const name of SECTIONS){
      for(const r of built[name].rows){
        const ref={section:name,key:r.key,state:r.state,source:built[name].source};
        if(r.claimable)claimableFacts.push({...ref,value:clone(r.value)});
        else unresolved.push({...ref,reason:r.reason||null});
      }
    }
    const core={
      contractId:CONTRACT_ID,
      workspaceId,opportunityId,revisionId,revisionVersion,
      capturedAt:clean(input.capturedAt)||null,
      sections:built,
      claimableFacts,
      unresolved,
      claimRule:'verified_only',
      unknownValueRule:'unknown_requires_null',
      exactVersionProvenanceRequired:true,
      currentWorkspaceAssemblyDeferred:true,
      decisionAuthority:false,
      recommendationAuthority:false,
      winnerAuthority:false,
      probabilityOfSuccess:false,
      acceptedStateMutationAllowed:false,
      persistenceAllowed:false
    };
    return deepFreeze({...core,snapshotDigest:digest(core),status:'snapshot_defined'});
  }
  function validate(snapshot){
    if(!snapshot||snapshot.contractId!==CONTRACT_ID)return deepFreeze({valid:false,reasons:['contract_invalid']});
    const rebuilt=build(snapshot.sections?{
      workspaceId:snapshot.workspaceId,opportunityId:snapshot.opportunityId,revisionId:snapshot.revisionId,revisionVersion:snapshot.revisionVersion,capturedAt:snapshot.capturedAt,
      ...Object.fromEntries(SECTIONS.map(name=>[name,snapshot.sections[name]]))
    }:{});
    if(rebuilt.status==='rejected')return deepFreeze({valid:false,reasons:[rebuilt.reason,rebuilt.detail||null].filter(Boolean)});
    const reasons=[];
    if(snapshot.snapshotDigest!==rebuilt.snapshotDigest)reasons.push('snapshot_digest_mismatch');
    if(snapshot.claimRule!=='verified_only')reasons.push('claim_rule_invalid');
    if(snapshot.unknownValueRule!=='unknown_requires_null')reasons.push('unknown_rule_invalid');
    if(snapshot.decisionAuthority!==false||snapshot.recommendationAuthority!==false||snapshot.winnerAuthority!==false)reasons.push('authority_boundary_invalid');
    return deepFreeze({valid:reasons.length===0,reasons});
  }
  return deepFreeze({CONTRACT_ID,STATES,SECTIONS,build,validate,sourceBinding,digest});
});

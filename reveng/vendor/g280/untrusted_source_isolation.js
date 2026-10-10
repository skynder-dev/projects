((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.RevEngUntrustedSourceIsolation=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  const CONTRACT_ID='reveng_untrusted_source_isolation_v1';
  const clean=(v,max=20000)=>String(v??'').trim().slice(0,max);
  const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
  const deepFreeze=v=>{if(!v||typeof v!=='object'||Object.isFrozen(v))return v;Object.freeze(v);Object.values(v).forEach(deepFreeze);return v;};
  const stable=v=>{if(Array.isArray(v))return '['+v.map(stable).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';return JSON.stringify(v);};
  const digest=v=>{let h=0x811c9dc5;for(const ch of stable(v)){h^=ch.charCodeAt(0);h=Math.imul(h,0x01000193)>>>0;}return 'fnv1a:'+h.toString(16).padStart(8,'0');};
  const bool=v=>v===true;
  function authoritySnapshot(raw={},scope={}){
    return deepFreeze({
      scope:deepFreeze({workspaceId:clean(scope.workspaceId,240)||null,opportunityId:clean(scope.opportunityId,240)||null,sourceRevisionId:clean(scope.sourceRevisionId,240)||null}),
      toolPermissions:deepFreeze([...new Set((Array.isArray(raw.toolPermissions)?raw.toolPermissions:[]).map(x=>clean(x,120)).filter(Boolean))].sort()),
      externalExecutionAllowed:bool(raw.externalExecutionAllowed),
      publicationAllowed:bool(raw.publicationAllowed),
      providerAuthority:bool(raw.providerAuthority),
      spendAuthority:bool(raw.spendAuthority),
      acceptedStateMutationAllowed:bool(raw.acceptedStateMutationAllowed)
    });
  }
  function instructionSignals(text){
    const s=clean(text).toLowerCase();
    const patterns=[
      /ignore\s+(all\s+)?(previous|prior|system|developer)\s+instructions?/,/system\s+prompt/,/developer\s+message/,
      /tool\s*permissions?/,/grant\s+.*permission/,/publish\s+(this|now|directly)/,/external\s+execution/,
      /provider\s+authority/,/spend\s+authority/,/override\s+.*scope/,/change\s+.*scope/,/accepted\s+state/,
      /call\s+(the\s+)?(tool|provider|api)/,/send\s+.*(email|message|request)/
    ];
    return patterns.flatMap((p,i)=>p.test(s)?[`signal_${i+1}`]:[]);
  }
  function build(raw={},trustedAuthority={}){
    const scope=raw.scope&&typeof raw.scope==='object'?raw.scope:{};
    const authority=authoritySnapshot(trustedAuthority,scope);
    const sourceText=clean(raw.sourceText??raw.text??raw.excerpt??raw.content,20000);
    const sourceRef=clean(raw.sourceRef??raw.locator??raw.url,2000)||null;
    const content={sourceRef,evidenceId:clean(raw.evidenceId,240)||null,claimRef:clean(raw.claimRef,240)||null,sourceText};
    const signals=instructionSignals(sourceText);
    const core={contractId:CONTRACT_ID,status:'isolated_untrusted_source',trustClass:'untrusted_source_content',content:clone(content),instructionLikeContentDetected:signals.length>0,instructionSignals:signals,effectiveAuthority:clone(authority),sourceTextMayChangeAuthority:false,sourceTextMayChangeScope:false,sourceTextMayChangePublicationRules:false,sourceTextMayTriggerTools:false,sourceTextMayGrantProviderAuthority:false,sourceTextMayGrantSpendAuthority:false,sourceTextMayMutateAcceptedState:false,contentIsEvidenceDataOnly:true};
    return deepFreeze({...core,contentDigest:digest(content),authorityDigest:digest(authority),packetDigest:digest(core)});
  }
  function validate(packet,trustedAuthority={}){
    if(!packet||packet.contractId!==CONTRACT_ID||packet.status!=='isolated_untrusted_source')return deepFreeze({valid:false,reason:'isolation_contract_invalid'});
    const scope=packet.effectiveAuthority?.scope||{};
    const expected=authoritySnapshot(trustedAuthority,scope);
    if(packet.authorityDigest!==digest(expected)||stable(packet.effectiveAuthority)!==stable(expected))return deepFreeze({valid:false,reason:'trusted_authority_mismatch'});
    if(packet.contentDigest!==digest(packet.content))return deepFreeze({valid:false,reason:'source_content_digest_mismatch'});
    const core=clone(packet);delete core.contentDigest;delete core.authorityDigest;delete core.packetDigest;
    if(packet.packetDigest!==digest(core))return deepFreeze({valid:false,reason:'isolation_packet_digest_mismatch'});
    const guards=['sourceTextMayChangeAuthority','sourceTextMayChangeScope','sourceTextMayChangePublicationRules','sourceTextMayTriggerTools','sourceTextMayGrantProviderAuthority','sourceTextMayGrantSpendAuthority','sourceTextMayMutateAcceptedState'];
    if(guards.some(k=>packet[k]!==false)||packet.contentIsEvidenceDataOnly!==true)return deepFreeze({valid:false,reason:'isolation_guard_invalid'});
    return deepFreeze({valid:true,reason:'ok',authorityDigest:packet.authorityDigest,contentDigest:packet.contentDigest});
  }
  return deepFreeze({CONTRACT_ID,build,validate,authoritySnapshot,instructionSignals});
});

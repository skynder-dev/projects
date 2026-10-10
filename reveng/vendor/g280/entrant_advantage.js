(() => {
  'use strict';
  const CONTRACT_ID='reveng_entrant_advantage_evidence_v1';
  const CRITERIA=Object.freeze([
    'cash_cost','owner_time','cycle_time','step_count','channel_reach','required_tool_count'
  ]);
  const DIRECTIONS=Object.freeze(['lower_is_better','higher_is_better']);
  const VERIFICATION_MODES=Object.freeze(['runtime_measurement','verified_product_fact','verified_process_fact']);
  const GENERIC_ONLY=Object.freeze(new Set([
    'ai','uses ai','ai powered','ai-powered','cheaper','better ux','better user experience','better experience'
  ]));
  const clean=v=>String(v??'').trim();
  const finite=(v,label)=>{const n=Number(v);if(!Number.isFinite(n))throw new Error(`${label} must be a finite number.`);return n;};
  const observedAt=v=>{const s=clean(v);if(!s||Number.isNaN(Date.parse(s)))throw new Error('observedAt must be an ISO date/time.');return s;};
  const https=v=>{const s=clean(v);if(!/^https:\/\//i.test(s))throw new Error('Incumbent evidence requires an exact public HTTPS source locator.');return s;};
  const digest=v=>{const s=clean(v).toLowerCase();if(!/^[a-f0-9]{64}$/.test(s))throw new Error('entrant artifactSha256 must be an exact SHA-256 digest.');return s;};
  function assertCandidate(candidate){
    if(!candidate||candidate.contract!=='reveng_discovery_candidate_normalization_v1')throw new Error('Entrant-advantage assessment requires one normalized discovery candidate.');
    return candidate;
  }
  function normalize(raw={}){
    if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('Entrant-advantage evidence must be an object.');
    const criterionKey=clean(raw.criterionKey);
    if(!CRITERIA.includes(criterionKey))throw new Error(`criterionKey must be one of: ${CRITERIA.join(', ')}.`);
    const direction=clean(raw.direction);
    if(!DIRECTIONS.includes(direction))throw new Error(`direction must be one of: ${DIRECTIONS.join(', ')}.`);
    const unit=clean(raw.unit); if(!unit)throw new Error('A concrete comparison unit is required.');
    const claim=clean(raw.claim); if(!claim)throw new Error('A concrete entrant-advantage claim is required.');
    const genericClaimOnly=GENERIC_ONLY.has(claim.toLowerCase());
    const falsifier=clean(raw.falsifier); if(!falsifier)throw new Error('A falsifier is required so the advantage hypothesis can fail.');
    const inc=raw.incumbentEvidence||{};
    if(inc.sourceVerified!==true)throw new Error('Incumbent evidence must be explicitly source-verified.');
    const incumbentEvidence=Object.freeze({
      value:finite(inc.value,'incumbentEvidence.value'),
      evidenceRef:clean(inc.evidenceRef),
      statement:clean(inc.statement),
      sourcePublisher:clean(inc.sourcePublisher),
      sourceLocator:https(inc.sourceLocator),
      observedAt:observedAt(inc.observedAt),
      sourceVerified:true,
      syntheticEvidence:inc.syntheticEvidence===true
    });
    if(!incumbentEvidence.evidenceRef||!incumbentEvidence.statement||!incumbentEvidence.sourcePublisher)throw new Error('Incumbent evidence requires evidenceRef, statement, and sourcePublisher.');
    const ent=raw.entrantEvidence||{};
    const verificationMode=clean(ent.verificationMode);
    if(!VERIFICATION_MODES.includes(verificationMode))throw new Error(`entrant verificationMode must be one of: ${VERIFICATION_MODES.join(', ')}.`);
    const entrantEvidence=Object.freeze({
      value:finite(ent.value,'entrantEvidence.value'),
      evidenceRef:clean(ent.evidenceRef),
      statement:clean(ent.statement),
      artifactRef:clean(ent.artifactRef),
      artifactSha256:digest(ent.artifactSha256),
      observedAt:observedAt(ent.observedAt),
      verificationMode,
      syntheticEvidence:ent.syntheticEvidence===true
    });
    if(!entrantEvidence.evidenceRef||!entrantEvidence.statement||!entrantEvidence.artifactRef)throw new Error('Entrant evidence requires evidenceRef, statement, and exact artifactRef.');
    return Object.freeze({criterionKey,direction,unit,claim,falsifier,genericClaimOnly,incumbentEvidence,entrantEvidence});
  }
  function evaluate(candidate,raw={}){
    assertCandidate(candidate);const e=normalize(raw);
    const incumbent=e.incumbentEvidence.value, entrant=e.entrantEvidence.value;
    const absoluteDelta=e.direction==='lower_is_better'?incumbent-entrant:entrant-incumbent;
    const denominator=Math.abs(incumbent);
    const relativeImprovement=denominator===0?null:absoluteDelta/denominator;
    const measuredAdvantage=absoluteDelta>0;
    const productionEvidence=!e.incumbentEvidence.syntheticEvidence&&!e.entrantEvidence.syntheticEvidence;
    const supported=measuredAdvantage&&!e.genericClaimOnly&&productionEvidence;
    const reasons=[];
    if(e.genericClaimOnly)reasons.push('generic_positioning_is_not_evidence');
    if(!measuredAdvantage)reasons.push('measured_comparison_does_not_show_advantage');
    if(!productionEvidence)reasons.push('synthetic_evidence_cannot_support_market_claim');
    return Object.freeze({
      contract:CONTRACT_ID,candidateIdentityKey:candidate.identityKey,criterionKey:e.criterionKey,direction:e.direction,unit:e.unit,
      claim:e.claim,falsifier:e.falsifier,incumbentEvidence:e.incumbentEvidence,entrantEvidence:e.entrantEvidence,
      comparison:Object.freeze({incumbentValue:incumbent,entrantValue:entrant,absoluteDelta,relativeImprovement,measuredAdvantage}),
      status:supported?'supported_advantage_hypothesis':'insufficient_entrant_advantage_evidence',supportedAdvantageHypothesis:supported,
      reasons,genericPositioningAcceptedAsProof:false,exactEntrantArtifactRequired:true,advantageProven:false,durableBusinessProven:false,
      requiresFurtherValidation:true,rankingAuthority:false,winnerAuthority:false,shortlistAuthority:false,commercialReadinessAuthority:false,decisionReady:false
    });
  }
  window.RevEngEntrantAdvantage=Object.freeze({CONTRACT_ID,CRITERIA,DIRECTIONS,VERIFICATION_MODES,normalize,evaluate});
})();

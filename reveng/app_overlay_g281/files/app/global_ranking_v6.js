((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngGlobalRankingV6=api;
})(typeof window!=='undefined'?window:globalThis,()=>{
  'use strict';
  // reveng_v6_independent: the GLOBAL ranking path. Pure functions, no I/O, no owner/user input is read.
  // Weights, multipliers, hard-gate cap and arithmetic mirror the database row reveng.scoring_versions['reveng_v6_independent']
  // and the trigger reveng.validate_score_run_integrity (raw = round(sum(score*weight)/10,4); adjusted = round(coalesce(capped,raw)*multiplier,4)).
  const CONTRACT_ID='reveng_global_ranking_v6_independent_v1';
  const VERSION='reveng_v6_independent';
  const freeze=Object.freeze;
  const WEIGHTS=freeze({
    entrant_edge:16,customer_problem_or_value:14,distribution_advantage:10,defensibility:10,absolute_gross_profit_potential:10,
    willingness_to_pay:8,repeat_ltv_potential:8,competition_adjusted_gap:8,market_depth:6,end_to_end_automation:4,capital_risk:3,owner_time_support:3
  });
  const DIMENSIONS=freeze(Object.keys(WEIGHTS));
  const MULTIPLIERS=freeze({A:1,B:0.9,C:0.75,D:0.6});
  const HARD_GATE_CAP=45;
  const SCORE_MIN=0, SCORE_MAX=10;
  // A grade can never be better than the verified evidence behind it (evidence classes are never promoted).
  const GRADE_BY_VERIFIED=freeze([[4,'A'],[3,'B'],[2,'C'],[0,'D']]);
  const ACCEPTABLE_EDGE_TYPES=freeze([
    'privileged_or_low_cac_distribution','proprietary_or_compounding_data','embedded_workflow_or_system_of_record',
    'network_effect_or_marketplace_liquidity','exclusive_or_difficult_supply_or_access','regulatory_license_intrinsic_to_model',
    'structural_unit_economics_advantage','unique_recovery_or_outcome_based_economics','acquirable_owned_audience_or_partner_channel'
  ]);
  const NOT_EDGE_TYPES=freeze([
    'ai','automation','better_ux','cheaper','faster','all_in_one','niche_focus','generic_personalization','generic_managed_service',
    'current_user_network','current_user_biography'
  ]);
  const EXCLUDED_SOURCE_TYPES=freeze(['owner_provided','owner_provided_retracted','user_memory','personal_context']);
  const OWNER_KEYS=freeze(new Set([
    'owner','ownername','owneridentity','createdby','email','phone','bio','biography','profile','profiledata','privatecontext','savedmemory',
    'memory','employmenthistory','workhistory','resume','cv','personalcontext','usermemory','userfit','ownerfit','mandate','mandatefit',
    'network','personalnetwork','contacts','location','capital','licenses','employer','priorindustryexperience','privateaccess','geography'
  ]));
  const ALLOWED_INPUT=freeze(new Set(['id','family','name','componentScores','confidenceGrade','entrantEdge','evidence']));
  const EVIDENCE_CLASSES=freeze(['verified','search_confirmed','agent_reported','unverified']);
  const norm=k=>String(k).toLowerCase().replace(/[^a-z0-9]/g,'');
  const r4=x=>Math.round((x+Number.EPSILON)*1e4)/1e4;
  const isNum=x=>typeof x==='number'&&Number.isFinite(x);
  const fail=(code,detail)=>{const e=new Error(detail?`${code}: ${detail}`:code);e.code=code;return e;};

  function verify(){
    const f=[];
    if(DIMENSIONS.length!==12) f.push('dimension_count');
    if(DIMENSIONS.reduce((a,k)=>a+WEIGHTS[k],0)!==100) f.push('weight_total');
    if(Object.keys(MULTIPLIERS).join('')!=='ABCD') f.push('multiplier_grades');
    return freeze({ok:!f.length,failures:freeze(f)});
  }
  const V=verify(); if(!V.ok) throw fail('REVENG_V6_CONTRACT_INVALID',V.failures.join(','));

  // Remove everything that is not on the allow-list; report owner-specific fields that were present so the audit trail shows they were ignored.
  function sanitizeInput(input){
    if(!input||typeof input!=='object'||Array.isArray(input)) throw fail('REVENG_V6_INPUT_NOT_OBJECT');
    const clean={}, ignoredOwnerFields=[], ignoredOtherFields=[];
    for(const k of Object.keys(input)){
      if(ALLOWED_INPUT.has(k)) clean[k]=input[k];
      else if(OWNER_KEYS.has(norm(k))) ignoredOwnerFields.push(k);
      else ignoredOtherFields.push(k);
    }
    let ev=Array.isArray(clean.evidence)?clean.evidence:[];
    const droppedEvidence=[];
    ev=ev.filter(x=>{
      const st=x&&x.sourceType;
      if(EXCLUDED_SOURCE_TYPES.includes(st)){droppedEvidence.push({id:x.id??null,sourceType:st});return false;}
      return !!x&&typeof x==='object';
    });
    clean.evidence=ev;
    return {clean,ignoredOwnerFields:ignoredOwnerFields.sort(),ignoredOtherFields:ignoredOtherFields.sort(),droppedEvidence};
  }
  function canonical(v){
    if(Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
    if(v&&typeof v==='object') return `{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${canonical(v[k])}`).join(',')}}`;
    return JSON.stringify(v);
  }
  function fnv1a(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;}return h.toString(16).padStart(8,'0');}
  const verifiedCount=ev=>ev.filter(x=>x.evidenceClass==='verified').length;
  function maxGrade(ev){const n=verifiedCount(ev);for(const [min,g] of GRADE_BY_VERIFIED) if(n>=min) return g;return 'D';}
  const gradeRank=g=>'ABCD'.indexOf(g);

  // The hard gate: no evidenced, independent, structural edge -> score is capped and the candidate cannot go to deep screen.
  function edgeGate(edge,evidence){
    const e=edge&&typeof edge==='object'?edge:null;
    if(!e) return freeze({passed:false,reason:'no_entrant_edge'});
    if(NOT_EDGE_TYPES.includes(e.type)) return freeze({passed:false,reason:`edge_type_not_an_edge:${e.type}`});
    if(!ACCEPTABLE_EDGE_TYPES.includes(e.type)) return freeze({passed:false,reason:`edge_type_unknown:${e.type}`});
    if(e.status!=='evidenced_independent') return freeze({passed:false,reason:`edge_status_${e.status||'missing'}`});
    if(!String(e.statement||'').trim()) return freeze({passed:false,reason:'edge_statement_missing'});
    const ids=Array.isArray(e.evidenceIds)?e.evidenceIds:[];
    const backing=evidence.filter(x=>ids.includes(x.id)&&x.evidenceClass==='verified');
    if(!backing.length) return freeze({passed:false,reason:'edge_has_no_verified_independent_evidence'});
    return freeze({passed:true,reason:'ok'});
  }

  function score(input){
    const {clean,ignoredOwnerFields,ignoredOtherFields,droppedEvidence}=sanitizeInput(input);
    const cs=clean.componentScores;
    if(!cs||typeof cs!=='object') throw fail('REVENG_V6_COMPONENT_SCORES_MISSING');
    const keys=Object.keys(cs);
    const missing=DIMENSIONS.filter(k=>!(k in cs)), extra=keys.filter(k=>!(k in WEIGHTS));
    if(missing.length||extra.length) throw fail('REVENG_V6_COMPONENT_KEYS_MISMATCH',`missing=[${missing}] extra=[${extra}]`);
    for(const k of DIMENSIONS) if(!isNum(cs[k])||cs[k]<SCORE_MIN||cs[k]>SCORE_MAX) throw fail('REVENG_V6_COMPONENT_OUT_OF_RANGE',k);
    const evidence=clean.evidence.map(x=>({...x,evidenceClass:EVIDENCE_CLASSES.includes(x.evidenceClass)?x.evidenceClass:'unverified'}));
    const component_scores={};for(const k of DIMENSIONS) component_scores[k]=cs[k];
    const raw=r4(DIMENSIONS.reduce((a,k)=>a+cs[k]*WEIGHTS[k],0)/10);
    const asked=String(clean.confidenceGrade||'D').toUpperCase();
    if(!(asked in MULTIPLIERS)) throw fail('REVENG_V6_BAD_CONFIDENCE_GRADE',asked);
    const allowed=maxGrade(evidence);
    const grade=gradeRank(asked)<gradeRank(allowed)?allowed:asked;
    const gradeCapped=grade!==asked;
    const gate=edgeGate(clean.entrantEdge,evidence);
    const capped=gate.passed?null:Math.min(raw,HARD_GATE_CAP);
    const mult=MULTIPLIERS[grade];
    const adjusted=r4((capped===null?raw:capped)*mult);
    const hashInput={id:clean.id??null,family:clean.family??null,componentScores:component_scores,grade,entrantEdge:clean.entrantEdge??null,evidence:evidence.map(x=>[x.id??null,x.evidenceClass,x.sourceType??null]).sort()};
    return freeze({
      id:clean.id??null,family:clean.family??null,name:clean.name??null,
      algorithm_version:VERSION,component_scores:freeze(component_scores),raw_score:raw,
      confidence_grade:grade,confidence_multiplier:mult,
      cap_reason:gate.passed?null:`entrant_edge_hard_gate:${gate.reason}`,capped_score:capped,adjusted_score:adjusted,
      deep_screen_eligible:gate.passed,
      input_hash:fnv1a(canonical(hashInput)),
      audit:freeze({ignoredOwnerFields:freeze(ignoredOwnerFields),ignoredOtherFields:freeze(ignoredOtherFields),droppedEvidence:freeze(droppedEvidence),
        gradeRequested:asked,gradeCappedByEvidence:gradeCapped,verifiedEvidenceCount:verifiedCount(evidence),edgeGate:gate})
    });
  }

  // Same checks as the database trigger. Returns a list of violations (empty = consistent).
  function integrity(row){
    const v=[];
    if(!row||row.algorithm_version!==VERSION) return ['wrong_algorithm_version'];
    const cs=row.component_scores||{};
    const keys=Object.keys(cs);
    if(keys.length!==DIMENSIONS.length||DIMENSIONS.some(k=>!(k in cs))) v.push('component_keys_do_not_match_weights');
    else{
      const exp=r4(DIMENSIONS.reduce((a,k)=>a+Number(cs[k])*WEIGHTS[k],0)/10);
      if(Math.abs(Number(row.raw_score)-exp)>0.01) v.push(`raw_score_mismatch:${row.raw_score}!=${exp}`);
    }
    const em=MULTIPLIERS[row.confidence_grade];
    if(em===undefined) v.push('unknown_confidence_grade');
    else if(Math.abs(Number(row.confidence_multiplier)-em)>0.0001) v.push(`confidence_multiplier_mismatch:${row.confidence_multiplier}!=${em}`);
    if(row.capped_score!==null&&row.capped_score!==undefined&&Number(row.capped_score)>Number(row.raw_score)+0.01) v.push('capped_score_exceeds_raw');
    const base=(row.capped_score===null||row.capped_score===undefined)?Number(row.raw_score):Number(row.capped_score);
    if(em!==undefined){const ea=r4(base*em);if(Math.abs(Number(row.adjusted_score)-ea)>0.01) v.push(`adjusted_score_mismatch:${row.adjusted_score}!=${ea}`);}
    return v;
  }
  function rank(rows){
    return [...rows].sort((a,b)=>(b.adjusted_score-a.adjusted_score)||(String(a.id)<String(b.id)?-1:1)).map((r,i)=>freeze({...r,rank:i+1}));
  }
  return freeze({CONTRACT_ID,VERSION,WEIGHTS,DIMENSIONS,MULTIPLIERS,HARD_GATE_CAP,ACCEPTABLE_EDGE_TYPES,NOT_EDGE_TYPES,EXCLUDED_SOURCE_TYPES,EVIDENCE_CLASSES,verify,sanitizeInput,edgeGate,score,integrity,rank,maxGrade});
});

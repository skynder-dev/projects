import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire(import.meta.url);
const ROOT=new URL('../../',import.meta.url).pathname;
const V6=require(ROOT+'app/global_ranking_v6.js');
const snap=JSON.parse(fs.readFileSync(new URL('./fixtures/g281_v6_db_snapshot.json',import.meta.url)));
let checks=0; const t=(c,m)=>{assert.ok(c,m);checks++;};

// 1. constants equal the database row
t(JSON.stringify(Object.fromEntries(Object.entries(V6.WEIGHTS).sort()))===JSON.stringify(Object.fromEntries(Object.entries(snap.weights).sort())),'weights equal DB');
t(JSON.stringify(V6.MULTIPLIERS)===JSON.stringify(snap.confidence_multipliers),'multipliers equal DB');
t(V6.HARD_GATE_CAP===snap.hard_gate_cap,'cap equals DB');
t(V6.verify().ok&&Object.values(V6.WEIGHTS).reduce((a,b)=>a+b,0)===100,'weights total 100');

// 2. the DB trigger arithmetic accepts every real v6 row and rejects tampered ones
for(const r of snap.rows){ assert.deepEqual(V6.integrity(r),[],`row ${r.id}`); checks++; }
const bad={...snap.rows[0],raw_score:60}; t(V6.integrity(bad).some(x=>x.startsWith('raw_score_mismatch')),'tampered raw detected');
const bad2={...snap.rows[0],adjusted_score:45}; t(V6.integrity(bad2).some(x=>x.startsWith('adjusted_score_mismatch')),'tampered adjusted detected');
const bad3={...snap.rows[0],capped_score:90}; t(V6.integrity(bad3).includes('capped_score_exceeds_raw'),'cap above raw detected');
const bad4={...snap.rows[0],component_scores:{...snap.rows[0].component_scores,extra:1}}; t(V6.integrity(bad4).includes('component_keys_do_not_match_weights'),'extra key detected');

// 3. score() reproduces the DB rows from raw component scores when the edge gate fails (all real rows were capped at 45)
for(const r of snap.rows){
  const out=V6.score({id:'x'+r.id,componentScores:r.component_scores,confidenceGrade:r.confidence_grade,evidence:Array(4).fill(0).map((_,i)=>({id:'E'+i,evidenceClass:'verified'})),entrantEdge:null});
  t(Math.abs(out.raw_score-r.raw_score)<=0.01,`raw ${r.id}`);
  t(out.capped_score===r.capped_score,`cap ${r.id}`);
  t(Math.abs(out.adjusted_score-r.adjusted_score)<=0.01,`adjusted ${r.id}`);
  t(out.deep_screen_eligible===false,`not deep-screen eligible ${r.id}`);
  assert.deepEqual(V6.integrity(out),[],`own output integrity ${r.id}`); checks++;
}

// 4. a candidate with a genuinely evidenced independent edge is not capped
const ev=[1,2,3,4].map(i=>({id:'E'+i,evidenceClass:'verified',sourceType:'public_primary_source'}));
const good={id:'G1',family:'saas',componentScores:{...snap.rows[0].component_scores,entrant_edge:7,distribution_advantage:6},confidenceGrade:'A',evidence:ev,
  entrantEdge:{type:'proprietary_or_compounding_data',status:'evidenced_independent',statement:'Holds a licensed dataset competitors cannot copy',evidenceIds:['E1']}};
const g=V6.score(good);
t(g.capped_score===null&&g.cap_reason===null&&g.deep_screen_eligible===true,'evidenced edge passes gate');
t(g.confidence_grade==='A'&&g.adjusted_score===g.raw_score,'grade A, multiplier 1');
assert.deepEqual(V6.integrity(g),[]);checks++;

// 5. edge-gate failure modes
const edgeCases={
  'edge_type_not_an_edge:cheaper':{type:'cheaper',status:'evidenced_independent',statement:'x',evidenceIds:['E1']},
  'edge_type_not_an_edge:current_user_network':{type:'current_user_network',status:'evidenced_independent',statement:'x',evidenceIds:['E1']},
  'edge_status_claimed':{type:'proprietary_or_compounding_data',status:'claimed',statement:'x',evidenceIds:['E1']},
  'edge_has_no_verified_independent_evidence':{type:'proprietary_or_compounding_data',status:'evidenced_independent',statement:'x',evidenceIds:['NOPE']},
  'edge_statement_missing':{type:'proprietary_or_compounding_data',status:'evidenced_independent',statement:' ',evidenceIds:['E1']},
};
for(const [reason,e] of Object.entries(edgeCases)){ const o=V6.score({...good,entrantEdge:e}); t(o.cap_reason==='entrant_edge_hard_gate:'+reason,reason); t(o.capped_score<=45,'capped '+reason); }
t(V6.score({...good,entrantEdge:undefined}).cap_reason==='entrant_edge_hard_gate:no_entrant_edge','missing edge');

// 6. evidence classes are never promoted: a better grade than the verified evidence allows is downgraded
const weak=V6.score({...good,confidenceGrade:'A',evidence:[{id:'E1',evidenceClass:'search_confirmed'},{id:'E2',evidenceClass:'agent_reported'}]});
t(weak.confidence_grade==='D'&&weak.audit.gradeCappedByEvidence===true,'grade capped by verified count');
t(weak.cap_reason&&weak.cap_reason.includes('no_verified_independent_evidence'),'unverified evidence cannot back the edge');
t(V6.score({...good,evidence:ev.slice(0,2)}).confidence_grade==='C','two verified -> C at best');

// 7. owner/user context can neither raise nor lower the global score
const base=V6.score(good);
const withOwner=V6.score({...good,owner:'Alex',email:'a@b.c',biography:'20 years trucking',personalNetwork:['x','y'],location:'Chicago',capital:50000,licenses:['CDL'],
  mandate:{capital_budget_usd:1},userFit:99,employer:'Z',privateAccess:true,priorIndustryExperience:'logistics',unknownField:1});
t(withOwner.raw_score===base.raw_score&&withOwner.adjusted_score===base.adjusted_score&&withOwner.input_hash===base.input_hash,'identical score and hash with owner context');
t(withOwner.audit.ignoredOwnerFields.length>=10,'owner fields reported as ignored');
t(withOwner.audit.ignoredOtherFields.includes('unknownField'),'unknown fields reported');
const owned=V6.score({...good,evidence:[...ev,{id:'O1',evidenceClass:'verified',sourceType:'owner_provided'},{id:'O2',evidenceClass:'verified',sourceType:'user_memory'}],
  entrantEdge:{...good.entrantEdge,evidenceIds:['O1']}});
t(owned.audit.droppedEvidence.length===2,'owner-sourced evidence dropped');
t(owned.cap_reason&&owned.cap_reason.includes('no_verified_independent_evidence'),'edge backed only by owner evidence fails gate');

// 8. input validation
const bads=[
  [{...good,componentScores:{...good.componentScores,entrant_edge:11}},'REVENG_V6_COMPONENT_OUT_OF_RANGE'],
  [{...good,componentScores:{...good.componentScores,extra:1}},'REVENG_V6_COMPONENT_KEYS_MISMATCH'],
  [{...good,componentScores:{entrant_edge:5}},'REVENG_V6_COMPONENT_KEYS_MISMATCH'],
  [{...good,componentScores:undefined},'REVENG_V6_COMPONENT_SCORES_MISSING'],
  [{...good,confidenceGrade:'Z'},'REVENG_V6_BAD_CONFIDENCE_GRADE'],
];
for(const [inp,code] of bads){ assert.throws(()=>V6.score(inp),e=>e.code===code,code); checks++; }
assert.throws(()=>V6.score(null),e=>e.code==='REVENG_V6_INPUT_NOT_OBJECT'); checks++;

// 9. ranking is deterministic and does not depend on input order
const rows=[V6.score({...good,id:'B'}),V6.score({...good,id:'A'}),V6.score({...good,id:'C',componentScores:{...good.componentScores,entrant_edge:1}})];
const r1=V6.rank(rows).map(x=>x.id).join(','), r2=V6.rank([...rows].reverse()).map(x=>x.id).join(',');
t(r1===r2&&r1==='A,B,C','deterministic ranking with id tie-break');
console.log(`reva2_g281_global_ranking_v6 PASS ${checks} checks`);

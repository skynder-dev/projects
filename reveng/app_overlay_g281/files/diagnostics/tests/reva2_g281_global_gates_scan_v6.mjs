import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ROOT=new URL('../../',import.meta.url).pathname;
const V6=require(ROOT+'app/global_ranking_v6.js'), G=require(ROOT+'app/global_gates_v6.js'), S=require(ROOT+'app/global_scan_v6.js');
let checks=0; const t=(c,m)=>{assert.ok(c,m);checks++;};
const U='https://example.com/p';
const ev=(kind,cls='verified')=>({id:'E-'+kind+cls,kind,evidenceClass:cls,sourceType:'public_primary_source'});
const alt=(o={})=>({label:'FreeTool',kind:'free_tool',costUsdPerMonth:0,coversWedge:'partial',sourceLocator:U,evidenceClass:'verified',...o});
const mk=(o={})=>({id:'C1',name:'Idea',family:'services',buyer:'dental offices',pain:'no-shows',wedge:'sms recall',
  referenceEntrant:{startupCashUsd:500,daysToFirstRevenue:30,ownerHoursPerWeek:10},
  alternativesSurvey:{freeSearchPerformed:true,alternatives:[alt({coversWedge:'partial'}),alt({label:'Paid',kind:'paid_incumbent',costUsdPerMonth:40,coversWedge:'full'})]},
  edgeMeasurement:{criterionKey:'owner_time',direction:'lower_is_better',incumbentValue:10,entrantValue:2,falsifier:'a pilot takes >5h/wk',},
  entrantEdge:{type:'structural_unit_economics_advantage',status:'evidenced_independent',statement:'Per-recall cost is structurally lower',evidenceIds:['E-demandverified']},
  evidence:[ev('incumbent_price'),ev('demand'),ev('constraint')],...o});
// owner_time metrics on the alternative so the comparison is against the BEST alternative
const withMetrics=(c,v)=>{c.alternativesSurvey.alternatives=c.alternativesSurvey.alternatives.map(a=>({...a,metrics:{owner_time:v}}));return c;};

// ---- cheapest alternative gate
let c=withMetrics(mk(),10); let r=G.runGates(c);
t(r.passed&&r.gates.cheapest_alternative.reason.startsWith('relative_improvement_vs_best_alternative'),'baseline idea passes');
t(!G.runGates(mk({alternativesSurvey:undefined})).passed&&G.runGates(mk({alternativesSurvey:undefined})).gates.cheapest_alternative.reason==='no_alternatives_survey','survey required');
t(G.runGates(mk({alternativesSurvey:{freeSearchPerformed:false,alternatives:[]}})).gates.cheapest_alternative.reason==='free_alternatives_not_searched','free search required');
let noFree=mk(); noFree.alternativesSurvey.alternatives=[alt({label:'Paid',kind:'paid_incumbent',costUsdPerMonth:40,coversWedge:'full'})];
t(G.runGates(noFree).gates.cheapest_alternative.reason==='no_free_alternative_listed_and_absence_not_evidenced','absence of free alternative must be evidenced');
noFree.alternativesSurvey.noFreeAlternativeFound={evidenceRef:'S3'}; noFree.alternativesSurvey.alternatives[0].metrics={owner_time:10};
t(G.runGates(noFree).gates.cheapest_alternative.passed,'evidenced absence accepted');
// the exact failure that killed the first 8 deep-screened ideas: compared with a dear incumbent while a free tool exists
let dear=withMetrics(mk(),10); dear.alternativesSurvey.alternatives[0].metrics={owner_time:3};
t(G.runGates(dear).gates.cheapest_alternative.reason.startsWith('edge_measured_against_non_best_alternative'),'edge against non-best alternative rejected');
let ok2=withMetrics(mk(),10); ok2.alternativesSurvey.alternatives[0].metrics={owner_time:3}; ok2.edgeMeasurement.incumbentValue=3; ok2.edgeMeasurement.entrantValue=1;
t(G.runGates(ok2).gates.cheapest_alternative.passed,'edge vs best alternative with real improvement passes (3->1 = 0.67)');
ok2.edgeMeasurement.entrantValue=2.5; t(G.runGates(ok2).gates.cheapest_alternative.reason.startsWith('improvement_below_threshold'),'below 25% rejected');
ok2.edgeMeasurement.entrantValue=4; t(G.runGates(ok2).gates.cheapest_alternative.reason.startsWith('no_measured_advantage'),'worse than best rejected');
// free AND full cover: verified -> hard fail, claimed -> unresolved condition only
let fullFree=withMetrics(mk(),10); fullFree.alternativesSurvey.alternatives[0]={...fullFree.alternativesSurvey.alternatives[0],coversWedge:'full'};
t(G.runGates(fullFree).gates.cheapest_alternative.reason.startsWith('free_alternative_covers_wedge'),'verified free full cover kills');
fullFree.alternativesSurvey.alternatives[0].evidenceClass='agent_reported';
let rr=G.runGates(fullFree); t(rr.unresolved.length===1&&!rr.gates.cheapest_alternative.reason.startsWith('free_alternative_covers_wedge'),'claimed free cover is unresolved, not a kill');
// cash_cost: best alternative free => no cash edge possible
let cash=mk({edgeMeasurement:{criterionKey:'cash_cost',direction:'lower_is_better',incumbentValue:0,entrantValue:0,falsifier:'x'}});
t(G.runGates(cash).gates.cheapest_alternative.reason.startsWith('no_measured_advantage'),'cash edge vs free alternative impossible');
// bad shapes
t(G.runGates(mk({alternativesSurvey:{freeSearchPerformed:true,alternatives:[alt({sourceLocator:'http://x'})]}})).gates.cheapest_alternative.reason==='alternative_source_not_https','https required');
t(G.runGates(mk({alternativesSurvey:{freeSearchPerformed:true,alternatives:[alt({kind:'weird'})]}})).gates.cheapest_alternative.reason==='alternative_bad_kind:weird','bad kind');
t(G.runGates(mk({edgeMeasurement:{...c.edgeMeasurement,falsifier:''}})).gates.cheapest_alternative.reason==='no_falsifier','falsifier required');

// ---- other gates
t(G.runGates({...c,referenceEntrant:{startupCashUsd:50000,daysToFirstRevenue:30,ownerHoursPerWeek:10}}).failed.includes('reference_entrant'),'reference entrant cash');
t(G.runGates({...c,evidence:[ev('demand')]}).failed.includes('evidence_depth'),'evidence depth');
t(G.runGates({...c,evidence:[ev('incumbent_price','search_confirmed'),ev('demand','search_confirmed'),ev('constraint','search_confirmed')]}).failed.includes('evidence_depth'),'search_confirmed is not verified');
t(G.runGates({...c,pain:'uses my network and my contacts'}).failed.includes('owner_leak'),'owner leak');
t(G.runGates({...c,entrantEdge:{type:'cheaper',status:'evidenced_independent',statement:'x',evidenceIds:['E-demandverified']}}).failed.includes('entrant_edge'),'generic edge fails');
// deep kill: fatal + verified kills; fatal uncited does not
const killV={...c,deep:{killReasons:[{reason:'free app covers it',severity:'fatal',refClass:'verified',ref:'C2'}]}};
t(G.runGates(killV).failed.includes('deep_kill'),'fatal verified kills');
const killU={...c,deep:{killReasons:[{reason:'seems saturated',severity:'fatal',refClass:'agent_reported'}]}};
t(!G.runGates(killU).failed.includes('deep_kill'),'fatal uncited does not kill');
t(G.runGates({...c,id:''}).failed[0]==='schema','schema gate');

// ---- scan validity
const fam=S.REQUIRED_FAMILIES, mkScan=(n,per)=>{const out=[];let i=0;for(const f of fam)for(let k=0;k<per;k++)out.push({id:'X'+(i++),name:'Idea '+(i),family:f,researchProtocol:'p2'});while(out.length<n)out.push({id:'X'+(i++),name:'Idea '+(i),family:fam[0],researchProtocol:'p2'});return out;};
t(S.assess(mkScan(40,4)).valid,'40 ideas/8 families valid');
t(!S.assess(mkScan(24,3)).valid&&S.assess(mkScan(24,3)).reasons[0].startsWith('raw_candidates 24<30'),'24 ideas invalid');
t(!S.assess(mkScan(32,4).filter(x=>x.family!=='games')).valid,'missing a required family invalid');
const mixed=mkScan(40,4); mixed[3].researchProtocol='other'; t(S.assess(mixed).reasons.some(x=>x.startsWith('mixed_research_protocols')),'mixed protocols');
const dups=mkScan(40,4); dups[5].id=dups[4].id; dups[7].name=dups[6].name; const dr=S.assess(dups).reasons.join('|'); t(dr.includes('duplicate_ids')&&dr.includes('duplicate_names'),'duplicates');
const tainted=mkScan(40,4); tainted[0].biography='x'; t(S.assess(tainted).reasons.some(x=>x.startsWith('owner_context_in_candidates')),'owner-tainted candidate');
t(S.assess(mkScan(40,4).map(x=>({...x,family:'made_up'}))).reasons.some(x=>x.startsWith('unknown_families')),'unknown families');

// ---- decision: never manufactures a winner
const base={componentScores:{entrant_edge:7,customer_problem_or_value:7,distribution_advantage:6,defensibility:6,absolute_gross_profit_potential:6,willingness_to_pay:6,repeat_ltv_potential:6,competition_adjusted_gap:6,market_depth:6,end_to_end_automation:6,capital_risk:6,owner_time_support:6},confidenceGrade:'A'};
const E4=['incumbent_price','demand','constraint','other'].map(k=>({id:'E-'+k,kind:k,evidenceClass:'verified',sourceType:'public_primary_source'}));
const row=(id,over={})=>V6.score({...base,id,family:'services',evidence:E4,entrantEdge:{type:'structural_unit_economics_advantage',status:'evidenced_independent',statement:'x',evidenceIds:['E-demand']},...over});
const goodCand=id=>({...mk({id,evidence:E4,entrantEdge:{type:'structural_unit_economics_advantage',status:'evidenced_independent',statement:'x',evidenceIds:['E-demand']}}),deep:{done:true,complete:true,economics:{survivesPessimistic:true},killReasons:[]}});
const cands={},rows=[],gates={};
for(let i=0;i<6;i++){const id='Z'+i;const cc=withMetrics(goodCand(id),10);cands[id]=cc;rows.push(row(id,{componentScores:{...base.componentScores,entrant_edge:i===0?10:5-i*0.5}}));gates[id]=G.runGates(cc);}
const validScan=S.assess(mkScan(40,4));
let d=G.decide({scan:validScan,rows,gateById:gates,candidatesById:cands});
t(d.verdict==='winner'&&d.leader==='Z0'&&d.unmet_conditions.length===0,'clean case yields winner Z0: '+JSON.stringify(d.unmet_conditions));
d=G.decide({scan:S.assess(mkScan(24,3)),rows,gateById:gates,candidatesById:cands}); t(d.verdict==='no_winner'&&d.leader===null&&d.hard_blockers[0].startsWith('scan_not_valid'),'invalid scan => no winner');
d=G.decide({scan:validScan,rows,gateById:gates,candidatesById:cands,provisional:true}); t(d.verdict==='no_winner','provisional evidence => no winner');
const failedAll=Object.fromEntries(Object.keys(gates).map(k=>[k,{passed:false}])); d=G.decide({scan:validScan,rows,gateById:failedAll,candidatesById:cands}); t(d.verdict==='no_winner'&&d.survivors===0,'nobody survives => no winner');
const notDeep={...cands,Z0:{...cands.Z0,deep:{done:false}}}; d=G.decide({scan:validScan,rows,gateById:gates,candidatesById:notDeep}); t(d.verdict==='no_winner'&&d.hard_blockers.some(x=>x.startsWith('top_candidate_not_deep_screened')),'top not deep screened => no winner');
const unc={...cands,Z0:{...cands.Z0,deep:{...cands.Z0.deep,killReasons:[{reason:'saturated',severity:'fatal',refClass:'agent_reported'}]}}}; d=G.decide({scan:validScan,rows,gateById:gates,candidatesById:unc}); t(d.verdict==='conditional_winner'&&d.unmet_conditions.some(x=>x.startsWith('top_has_uncited_fatal_claims')),'uncited fatal => conditional');
const tight=rows.map(r=>r.id==='Z1'?row('Z1',{componentScores:{...base.componentScores,entrant_edge:9.8}}):r); d=G.decide({scan:validScan,rows:tight,gateById:gates,candidatesById:cands}); t(d.verdict==='conditional_winner','thin margin => conditional');
const tamper=rows.map(r=>r.id==='Z0'?{...r,adjusted_score:99}:r); d=G.decide({scan:validScan,rows:tamper,gateById:gates,candidatesById:cands}); t(d.verdict==='no_winner'&&d.integrity_violations.length>0,'tampered score => no winner');
const capped=[row('Q0',{entrantEdge:null})]; d=G.decide({scan:validScan,rows:capped,gateById:{Q0:{passed:true}},candidatesById:{Q0:cands.Z0}}); t(d.verdict==='no_winner'&&d.survivors===0,'edge-gate-capped candidate is not a survivor');
console.log(`reva2_g281_global_gates_scan_v6 PASS ${checks} checks`);

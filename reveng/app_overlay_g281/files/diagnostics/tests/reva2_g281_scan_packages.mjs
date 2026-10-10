import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ROOT=new URL('../../',import.meta.url).pathname;
const V6=require(ROOT+'app/global_ranking_v6.js'), G=require(ROOT+'app/global_gates_v6.js'), Scan=require(ROOT+'app/global_scan_v6.js'), View=require(ROOT+'app/global_ranking_view.js');
const rd=p=>JSON.parse(fs.readFileSync(ROOT+p,'utf8'));
let checks=0; const t=(c,m)=>{assert.ok(c,m);checks++;};
const P={2:{count:32,families:8,per:4,validAlone:true,deep:8,rechecks:95,confirmed:93,partial:2},3:{count:30,families:6,per:5,validAlone:false,deep:4,rechecks:76,confirmed:72,partial:4}};
const pkg1=rd('server/REVA2_G281_SCAN1_IMPORT.json');
const allFp=new Set(pkg1.candidates.map(c=>c.fingerprint)), allKeys=new Set(pkg1.candidates.map(c=>c.candidate_key));
const srcAll={};
const bad=k=>['workspace_id','workspace_key','user_id','owner_id','owner_name','private_context','private_notes','personalization','personal_context','profile','profile_context','mandate','mandate_context','memory','connector_payload','connector_context'].includes(k.toLowerCase())||/^(private|personal|workspace|owner|user)_/i.test(k);
for(const N of [2,3]){
  const E=P[N], base=`samples/g281_scan${N}/`;
  const pkg=rd(`server/REVA2_G281_SCAN${N}_IMPORT.json`), agg=rd(base+'aggregate.json'), rows=pkg.candidates;
  const src=[]; for(const f of fs.readdirSync(ROOT+base+'candidates').sort()) src.push(...rd(base+'candidates/'+f).candidates);
  const byId=Object.fromEntries(src.map(c=>[c.id,c])); Object.assign(srcAll,byId);
  const deeps=Object.fromEntries(fs.readdirSync(ROOT+base+'deep').filter(f=>f.endsWith('.json')).map(f=>[f.replace('.json',''),rd(base+'deep/'+f)]));
  const tag=`scan${N}: `;
  // shape
  t(rows.length===E.count&&src.length===E.count,tag+'candidate count');
  const fam={}; for(const r of rows) fam[r.metadata.family]=(fam[r.metadata.family]||0)+1;
  t(Object.keys(fam).length===E.families&&Object.values(fam).every(n=>n===E.per),tag+'families x per-family');
  t(N!==2||Scan.REQUIRED_FAMILIES.every(f=>fam[f]===4),tag+'8 required families x 4');
  t(new Set(rows.map(r=>r.candidate_key)).size===E.count&&rows.every(r=>r.candidate_key.startsWith(`G281-SCAN${N}-`)),tag+'unique keys');
  t(new Set(rows.map(r=>r.fingerprint)).size===E.count,tag+'unique fingerprints');
  t(rows.every(r=>!allFp.has(r.fingerprint)&&!allKeys.has(r.candidate_key)),tag+'no collision with earlier scans (all packages can be imported together)');
  rows.forEach(r=>{allFp.add(r.fingerprint);allKeys.add(r.candidate_key);});
  // validity rules
  const sc=Scan.assess(src.map(c=>({id:c.id,name:c.name,family:c.family,researchProtocol:`scan${N}_manual_edge_first_agent_reported`})));
  t(sc.valid===E.validAlone&&sc.rawCandidates===E.count&&sc.familiesRepresented===E.families,tag+'validity alone is '+E.validAlone+': '+sc.reasons.join('|'));
  if(N===3){ const cm=pkg.run.metadata.combined_with_extended; t(pkg.run.metadata.extends==='g281-scan2-manual-edge-first-20261010'&&cm.valid&&cm.rawCandidates===62&&cm.familiesRepresented===14,'scan3 is valid only combined with scan 2: 62 raw, 14 families');
    t(!agg.scan.valid&&agg.combinedWithScan2.valid,'aggregate agrees'); }
  // statuses follow the final verdict (deep screen overrides first pass)
  const fin=id=>deeps[id]?deeps[id].verdict:byId[id].researcherVerdict;
  t(rows.every(r=>r.metadata.final_verdict===fin(r.metadata.engine_id)&&(r.status==='rejected')===(fin(r.metadata.engine_id)==='killed')),tag+'status follows the final verdict');
  t(rows.filter(r=>r.status==='research_queue').length===rows.filter(r=>fin(r.metadata.engine_id)!=='killed').length,tag+'queue size');
  t(!rows.some(r=>fin(r.metadata.engine_id)==='survives'),tag+'no candidate survives');
  t(rows.every(r=>r.status!=='rejected'||(r.rejection_reason&&r.rejection_reason.length>40&&r.metadata.rejection_basis==='independent_manual_reading_agent_reported')),tag+'every rejection has reason and honest basis');
  // deep screen
  t(Object.keys(deeps).length===E.deep,tag+'deep screens present');
  for(const [id,d] of Object.entries(deeps)){ const r=rows.find(x=>x.metadata.engine_id===id);
    t(byId[id].researcherVerdict==='uncertain','only uncertain ideas were deep-screened: '+id);
    t(r.metadata.researcher_verdict==='uncertain'&&r.metadata.final_verdict===d.verdict&&r.metadata.deep_screen.second_pass===true,'deep metadata '+id);
    t(r.status==='research_queue'?d.verdict!=='killed':r.rejection_reason.startsWith('KILLED_AFTER_DEEP_SCREEN'),'deep reason '+id);
    t(d.newEvidence.every(e=>r.evidence_hints.some(h=>h.url===e.url&&h.stage==='deep')),'deep evidence carried '+id);
    t(d.killReasons.every(k=>r.metadata.kill_reasons.some(x=>x.ref===k.ref&&x.severity===k.severity)),'deep kill reasons carried '+id);
    t(r.metadata.deep_screen.economics.pessimistic_profit365_usd===d.economics.pessimisticProfit365&&r.metadata.deep_screen.economics.survives_pessimistic===d.economics.survivesPessimistic,'deep economics '+id); }
  // evidence is never promoted
  const ev=rows.flatMap(r=>r.evidence_hints);
  t(ev.every(e=>/^https:\/\//.test(e.url)&&e.evidence_class==='agent_reported'&&String(e.signal).length>=10),tag+'all evidence https and agent_reported');
  t(rows.every(r=>r.evidence_hints.filter(h=>h.stage==='scan').length>=3),tag+'>=3 scan evidence items each');
  const rc=ev.filter(e=>e.recheck);
  t(rc.length===E.rechecks&&rc.filter(e=>e.recheck.status==='confirmed').length===E.confirmed&&rc.filter(e=>e.recheck.status==='partially_supported').length===E.partial&&rc.every(e=>['confirmed','partially_supported'].includes(e.recheck.status)),tag+`${E.rechecks} independent re-reads: ${E.confirmed} confirmed, ${E.partial} partial, none contradicted`);
  const ir=pkg.run.metadata.independent_recheck; t(ir.checked===E.rechecks&&ir.contradicted_or_missing===0,tag+'run metadata matches');
  // scoring honesty
  t(rows.every(r=>r.metadata.v6_component_scores===null&&r.metadata.v6_provisional&&r.metadata.v6_provisional.grade==='D'),tag+'component scores only as provisional, grade D');
  for(const r of rows){ const c=byId[r.metadata.engine_id]; const row=V6.score({...c,evidence:c.evidence.map(x=>({...x,sourceType:'public_web_search'}))});
    t(row.raw_score===r.metadata.v6_provisional.raw&&row.adjusted_score===r.metadata.v6_provisional.adjusted,'provisional score reproduces: '+c.id);
    t(V6.integrity(row).length===0,'score row integrity '+c.id);
    t(r.metadata.v6_provisional.adjusted<=27+1e-9&&/entrant_edge_hard_gate/.test(r.metadata.v6_provisional.cap_reason||''),'capped by the edge hard gate: '+c.id);
    t(r.metadata.entrant_edge.status!=='evidenced_independent','no edge claimed as independently evidenced: '+c.id); }
  // gates and decision
  const gates=Object.fromEntries(src.map(c=>[c.id,G.runGates(c)]));
  t(Object.values(gates).every(g=>!g.passed&&g.failed.includes('entrant_edge')&&g.failed.includes('evidence_depth')),tag+'no candidate passes the hard gates');
  const dec=G.decide({scan:sc,rows:src.map(c=>V6.score({...c,evidence:c.evidence.map(x=>({...x,sourceType:'public_web_search'}))})),gateById:gates,candidatesById:byId,provisional:true});
  t(dec.verdict==='no_winner'&&dec.leader===null&&dec.survivors===0,tag+'decision: no winner');
  t(agg.decision.verdict==='no_winner'&&agg.counts.killed+agg.counts.uncertain===E.count,tag+'aggregate matches');
  // view model
  const m=View.build(pkg);
  t(m.verdict.state==='no_winner'&&m.verdict.winner===null&&m.scan.valid===E.validAlone&&m.counts.queued===0&&m.counts.rejected_unverified===E.count&&m.counts.rejected_verified===0&&m.counts.gate_rejected===0,tag+'view counts');
  t(m.v6Ranked===0&&m.v6Provisional===E.count&&m.verdict.reasons.some(r=>r.includes('provisional')&&r.includes('no v6 ranking exists')),tag+'view says provisional, no v6 rank');
  t(m.rows.filter(r=>r.deep).length===E.deep&&m.rows.every(r=>r.researcherVerdict==='killed')&&(N===3?m.extension&&m.extension.combined.valid:m.extension===null),tag+'view deep/extension fields');
  const order=View.filter(m,{}); t(order.every((r,i)=>i===0||order[i-1].provisional.raw>=r.provisional.raw),tag+'ordered by provisional raw');
  t(m.rows.every(r=>r.lensScore===null&&r.provisional),tag+'no lens score mixed in');
  // privacy (mirrors reveng.guard_global_catalog_candidate_metadata_v1)
  t(rows.every(r=>Object.keys(r.metadata).every(k=>!bad(k))),tag+'metadata keys pass the global-catalog privacy guard');
  t(!/"(owner|biography|mandate|contacts)"\s*:/i.test(JSON.stringify(rows)),tag+'no owner-context fields');
  // dry-run SQL cannot write
  const sql=fs.readFileSync(ROOT+`server/REVA2_G281_SCAN${N}_IMPORT_DRYRUN.sql`,'utf8');
  t(/\nROLLBACK;\n?$/.test(sql)&&!/\bCOMMIT\b/i.test(sql.replace(/--.*$/gm,'')),tag+'SQL ends with ROLLBACK, no COMMIT');
  t((sql.match(/INSERT INTO reveng\.catalog_candidate_inbox/g)||[]).length===E.count,tag+'inbox inserts');
}
// across both scans: no id reused, 62 distinct ideas, 14 families, nothing survives
t(Object.keys(srcAll).length===62,'62 distinct candidate ids over scans 2+3');
t(Object.values(srcAll).every(c=>c.researcherVerdict!=='survives'),'no first-pass survivor');
console.log(`reva2_g281_scan_packages PASS ${checks} checks`);

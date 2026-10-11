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

// ---- scan 1: second pass (manual deep screen of the 24 queued ideas, agent_reported)
{
  const rows=pkg1.candidates, tag='scan1 deep: ', base='samples/g281_scan1/';
  const st=rd(base+'deep_status.json');
  const deeps=Object.fromEntries(fs.readdirSync(ROOT+base+'deep').filter(f=>f.endsWith('.json')).map(f=>[f.replace('.json',''),rd(base+'deep/'+f)]));
  const byEng=Object.fromEntries(rows.map(r=>[r.metadata.engine_id,r]));
  t(rows.length===40&&Object.keys(deeps).length===22,tag+'40 candidates, 22 deep results');
  // second attempt (deep2/): appended evidence, later verdict/economics win
  const deep2=Object.fromEntries(fs.readdirSync(ROOT+base+'deep2').filter(f=>f.endsWith('.json')).map(f=>[f.replace('.json',''),rd(base+'deep2/'+f)]));
  t(JSON.stringify(Object.keys(deep2).sort())===JSON.stringify(['PHY-01','SAS-02']),tag+'two second-attempt results merged');
  for(const [id,b] of Object.entries(deep2)){ const a=deeps[id]; a.newEvidence=a.newEvidence.concat(b.newEvidence); a.economics=b.economics; a.verdict=b.verdict; a.killReasons=a.killReasons.concat(b.killReasons.filter(k=>!a.killReasons.some(x=>x.reason===k.reason))); t(b.newEvidence.every(e=>new RegExp('^'+id+'-D2\\d+$|^'+id+'-D[3-9]\\d$').test(e.id)),tag+id+' second-attempt evidence ids do not collide'); }
  // independent quote re-read (66 checks: 65 confirmed, 1 not_found = minor SVC-04-D11)
  const rr=fs.readdirSync(ROOT+base+'verify').filter(f=>/^deep_result_\d+\.json$/.test(f)).flatMap(f=>rd(base+'verify/'+f).results);
  t(rr.length===66&&rr.filter(x=>x.status==='confirmed').length===65&&rr.filter(x=>x.status==='not_found').length===1&&rr.every(x=>['confirmed','not_found','partially_supported','contradicted','unreachable'].includes(x.status)),tag+'quote re-read 66 checks');
  const nf=rr.find(x=>x.status==='not_found'); const nfk=deeps[nf.candidateId].killReasons.find(k=>k.ref===nf.evidenceId); t(nfk&&nfk.severity==='minor'&&deeps[nf.candidateId].killReasons.filter(k=>k.severity==='major').length>=2,tag+'not_found quote only backs a minor reason, kill keeps two major reasons');
  for(const x of rr){ const h=byEng[x.candidateId].evidence_hints.find(e=>e.stage==='deep'&&e.url===x.url&&e.recheck&&e.recheck.status===x.status); t(h,tag+x.evidenceId+' recheck attached to evidence, class unchanged'); t(h.evidence_class==='agent_reported',tag+x.evidenceId+' re-read does not promote evidence'); }
  const kv={killed:0,uncertain:0,survives:0};
  for(const [id,d] of Object.entries(deeps)){
    const r=byEng[id]; t(r,tag+id+' present'); kv[d.verdict]++;
    t(r.metadata.deep_screen.second_pass===true&&r.metadata.deep_screen.done&&r.metadata.deep_screen.complete&&r.metadata.deep_screen.method==='manual_reading_agent_reported',tag+id+' deep_screen flags');
    t(r.metadata.final_verdict===d.verdict&&r.metadata.deep_screen.verdict===d.verdict,tag+id+' final verdict mirrors source');
    t(r.metadata.deep_screen.economics.pessimistic_profit365_usd===d.economics.pessimisticProfit365&&r.metadata.deep_screen.economics.survives_pessimistic===d.economics.survivesPessimistic,tag+id+' economics mirror source');
    if(d.verdict==='killed'){
      t(r.status==='rejected'&&r.rejection_reason.startsWith('KILLED_AFTER_DEEP_SCREEN (agent_reported)')&&r.metadata.rejection_basis==='independent_manual_reading_agent_reported',tag+id+' killed → rejected, agent_reported basis');
      t(r.metadata.kill_reasons.length>=1&&r.metadata.alternatives.length>=1,tag+id+' kill reasons and alternatives kept');
      t(d.economics.survivesPessimistic===false||d.killReasons.some(k=>k.severity==='major'||k.severity==='critical'),tag+id+' killed on economics or on a major/critical reason');
      t(r.metadata.kill_reasons.length===d.killReasons.length,tag+id+' all kill reasons carried over');
    } else { t(r.status==='research_queue',tag+id+' uncertain stays queued'); }
    const dv=r.evidence_hints.filter(e=>e.stage==='deep');
    t(dv.length===d.newEvidence.length&&dv.every(e=>e.evidence_class==='agent_reported'&&/^https:\/\//.test(e.url)),tag+id+' deep evidence all agent_reported https, never promoted');
    t(r.evidence_hints.filter(e=>e.stage!=='deep').every(e=>e.evidence_class==='verified'||e.evidence_class==='search_confirmed')&&r.metadata.rejection_basis!=='verified_provider_citation',tag+id+' first-pass provider evidence untouched, kill basis never claims verified');
  }
  t(kv.killed===19&&kv.uncertain===3&&kv.survives===0,tag+'19 killed / 3 uncertain / 0 survive: '+JSON.stringify(kv));
  t(JSON.stringify(Object.keys(st.not_screened).sort())===JSON.stringify(['GAM-02','MED-03']),tag+'two unscreened ideas recorded');
  for(const id of Object.keys(st.not_screened)){ const r=byEng[id]; t(r.status==='research_queue'&&!r.metadata.deep_screen.second_pass&&typeof r.metadata.deep_screen_not_screened==='string'&&!r.metadata.final_verdict,tag+id+' stays queued, not screened, no invented verdict'); }
  const cnt={}; for(const r of rows) cnt[r.status]=(cnt[r.status]||0)+1;
  t(cnt.rejected===35&&cnt.research_queue===5,tag+'35 rejected / 5 queued '+JSON.stringify(cnt));
  t(pkg1.run.metadata.deep_screened===22&&pkg1.run.metadata.final_verdicts_after_deep_screen.killed===19&&pkg1.run.metadata.final_verdicts_after_deep_screen.uncertain===3&&pkg1.run.metadata.deep_screen_not_screened.length===2,tag+'run metadata');
  t(rows.every(r=>Object.keys(r.metadata).every(k=>!bad(k))),tag+'metadata keys pass the global-catalog privacy guard');
  const sql=fs.readFileSync(ROOT+'server/REVA2_G281_SCAN1_IMPORT_DRYRUN.sql','utf8');
  t(/\nROLLBACK;\n?$/.test(sql)&&!/^\s*(COMMIT|END)\s*;/im.test(sql)&&/35 rejected, 5 research_queue/.test(sql),tag+'SQL ends with ROLLBACK, expectation line matches');
  const m=View.build(pkg1); t(m.counts.queued===5&&m.counts.rejected_unverified===27&&m.counts.gate_rejected===8&&View.filter(m,{status:'queued'}).length===5,tag+'view counts');
}
console.log(`reva2_g281_scan_packages PASS ${checks} checks`);

import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ROOT=new URL('../../',import.meta.url).pathname;
const V=require(ROOT+'app/global_ranking_view.js');
const pkg=JSON.parse(fs.readFileSync(ROOT+'server/REVA2_G281_SCAN1_IMPORT.json'));
let checks=0; const t=(c,m)=>{assert.ok(c,m);checks++;};
const m=V.build(pkg);
t(m.scan.valid&&m.scan.rawCandidates===40&&m.scan.familiesRepresented===10,'scan valid 40/10');
t(m.verdict.state==='no_winner'&&m.verdict.winner===null,'no winner');
t(m.v6Ranked===0&&m.verdict.reasons.some(r=>r.includes('no v6 ranking exists')),'no v6 ranking invented');
t(m.counts.total===40&&m.counts.queued===24&&m.counts.gate_rejected===8&&m.counts.rejected_unverified===8&&m.counts.rejected_verified===0,'status counts '+JSON.stringify(m.counts));
t(m.rows.every(r=>r.lensLabel==='g280_balanced_v1_lens_NOT_reveng_v6'),'every score is labelled as the v1 lens, never v6');
t(m.spend.authorizedUsd===0&&m.spend.paidCallsAllowed===false&&Math.abs(m.spend.estimate.expectedUsd-6.597618)<1e-6,'spend blocked, estimate from measured scan');
t(V.filter(m,{status:'queued'}).length===24&&V.filter(m,{family:'games'}).length===4&&V.filter(m,{q:'wyzant'}).length>=1,'filters');
const sorted=V.filter(m,{}); t(sorted.every((r,i)=>i===0||(sorted[i-1].lensScore??-1)>=(r.lensScore??-1)),'sorted by lens score desc');
// the same data can never produce a v6 rank or a winner: tampering with the verdict inputs changes nothing without v6 scores
const noQueued=V.build({...pkg,candidates:pkg.candidates.filter(c=>c.status==='rejected')}); t(noQueued.verdict.state==='no_winner','still no winner');
const small=V.build({...pkg,candidates:pkg.candidates.slice(0,10)}); t(!small.scan.valid&&small.verdict.reasons[0].startsWith('scan_not_valid'),'small scan flagged invalid');
// statusOf rules
t(V.statusOf({status:'research_queue'})==='queued'&&V.statusOf({status:'rejected',metadata:{rejection_basis:'engine_hard_gate'}})==='gate_rejected'
 &&V.statusOf({status:'rejected',metadata:{rejection_basis:'verified_provider_citation'}})==='rejected_verified'&&V.statusOf({status:'rejected',metadata:{}})==='rejected_unverified','statusOf');
// escaping helpers
t(V.esc('<a href="x">&\'')==='&lt;a href=&quot;x&quot;&gt;&amp;&#39;','esc');
t(V.safeUrl('https://a.com/x')==='https://a.com/x'&&V.safeUrl('javascript:alert(1)')===null&&V.safeUrl('http://a.com')===null&&V.safeUrl(null)===null,'safeUrl');
assert.throws(()=>V.build(null),/REVENG_VIEW_PACKAGE_INVALID/); checks++;
assert.throws(()=>V.build({candidates:'x'}),/REVENG_VIEW_PACKAGE_INVALID/); checks++;
console.log(`reva2_g281_global_ranking_view PASS ${checks} checks`);

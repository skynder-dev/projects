// Validator for a scan-2 candidate file. Usage: node validate.mjs out/<FAMILY>.json
// Checks structure, runs the G281 scorer and gates, prints problems. Never touches the network.
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const A=new URL('../../app/',import.meta.url).pathname;
const V6=require(A+'global_ranking_v6.js'), G=require(A+'global_gates_v6.js'), S=require(A+'global_scan_v6.js');
const file=process.argv[2]; const data=JSON.parse(fs.readFileSync(file,'utf8'));
const list=Array.isArray(data)?data:data.candidates; const problems=[];
const need=(c,m)=>{if(!c)problems.push(m);};
need(Array.isArray(list)&&list.length>=4,'need an array "candidates" with at least 4 entries');
const famOk=new Set(S.ALL_FAMILIES);
for(const c of list||[]){
  const p=m=>problems.push(`${c.id||'?'}: ${m}`);
  for(const k of ['id','name','family','buyer','pain','wedge']) if(!String(c[k]||'').trim()) p('missing '+k);
  if(!famOk.has(c.family)) p('family must be one of '+S.ALL_FAMILIES.join(','));
  const r=c.referenceEntrant||{}; for(const k of ['startupCashUsd','daysToFirstRevenue','ownerHoursPerWeek']) if(typeof r[k]!=='number') p('referenceEntrant.'+k+' must be a number');
  const e=c.entrantEdge||{}; if(!V6.ACCEPTABLE_EDGE_TYPES.includes(e.type)&&!V6.NOT_EDGE_TYPES.includes(e.type)) p('entrantEdge.type must be one of '+[...V6.ACCEPTABLE_EDGE_TYPES,...V6.NOT_EDGE_TYPES].join(','));
  if(!['claimed','evidenced_independent','none'].includes(e.status)) p('entrantEdge.status must be claimed|evidenced_independent|none');
  const ev=Array.isArray(c.evidence)?c.evidence:[]; need(ev.length>=3,`${c.id}: need >=3 evidence items`);
  const ids=new Set(); for(const x of ev){ if(ids.has(x.id)) p('duplicate evidence id '+x.id); ids.add(x.id);
    if(!/^https:\/\//.test(x.url||'')) p(`evidence ${x.id}: url must be https`); if(String(x.quote||'').trim().length<15) p(`evidence ${x.id}: quote must be text you actually read on the page (>=15 chars)`);
    if(!['incumbent_price','demand','constraint','other'].includes(x.kind)) p(`evidence ${x.id}: bad kind`); if(x.evidenceClass!=='agent_reported') p(`evidence ${x.id}: evidenceClass must be "agent_reported"`);
    if(!String(x.date||'').trim()) p(`evidence ${x.id}: date (or "undated")`); }
  for(const id of e.evidenceIds||[]) if(!ids.has(id)) p('entrantEdge.evidenceIds references unknown '+id);
  const s=c.alternativesSurvey||{}; if(s.freeSearchPerformed!==true) p('alternativesSurvey.freeSearchPerformed must be true (you must actually search for free/open-source/DIY alternatives)');
  for(const a of s.alternatives||[]){ if(!G.ALT_KINDS.includes(a.kind)) p('alternative kind '+a.kind); if(!['full','partial','none'].includes(a.coversWedge)) p('alternative coversWedge'); if(!/^https:\/\//.test(a.sourceLocator||'')) p('alternative '+a.label+': sourceLocator https'); if(typeof a.costUsdPerMonth!=='number') p('alternative '+a.label+': costUsdPerMonth number (0 = free)'); if(a.evidenceRef&&!ids.has(a.evidenceRef)) p('alternative evidenceRef unknown '+a.evidenceRef); }
  need((s.alternatives||[]).length>=3,`${c.id}: list at least 3 alternatives`);
  const cs=c.componentScores||{}; for(const k of V6.DIMENSIONS) if(typeof cs[k]!=='number'||cs[k]<0||cs[k]>10) p('componentScores.'+k+' must be number 0..10'); for(const k of V6.DIMENSIONS) if(!String((c.componentReasons||{})[k]||'').trim()) p('componentReasons.'+k+' missing');
  if(!['survives','killed','uncertain'].includes(c.researcherVerdict)) p('researcherVerdict must be survives|killed|uncertain');
  if(c.researcherVerdict!=='survives'&&!String(c.verdictReason||'').trim()) p('verdictReason required when killed/uncertain');
  if(!Array.isArray(c.legalNotes)||!c.legalNotes.length) p('legalNotes: at least one note (licenses, platform ToS, regulation) with evidence id');
  if(c.deep&&Array.isArray(c.deep.killReasons)) for(const k of c.deep.killReasons) if(!['fatal','major','minor'].includes(k.severity)) p('killReason severity');
  try{ const row=V6.score({...c,evidence:ev.map(x=>({...x,sourceType:'public_web_search'}))}); const g=G.runGates(c); c.__preview={raw:row.raw_score,adjusted:row.adjusted_score,grade:row.confidence_grade,cap:row.cap_reason,gatesFailed:g.failed}; }catch(err){ p('scoring failed: '+err.message); }
}
const fams=new Set((list||[]).map(c=>c.family)); need(fams.size===1,'one family per file'); 
if(problems.length){ console.log('PROBLEMS ('+problems.length+'):\n'+problems.slice(0,40).join('\n')); process.exit(1); }
console.log('OK '+list.length+' candidates'); for(const c of list) console.log(c.id,c.researcherVerdict,JSON.stringify(c.__preview));

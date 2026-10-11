import fs from 'node:fs';
const file=process.argv[2]; const d=JSON.parse(fs.readFileSync(file,'utf8')); const P=[]; const p=m=>P.push(m);
const id=d.id; if(!/^[A-Z0-9]{3}-\d{2}$/.test(id||'')) p('bad id');
let src=null; try{ src=JSON.parse(fs.readFileSync(new URL(`../../samples/g281_scan1/cases/${id}.json`,import.meta.url).pathname,'utf8')); }catch(e){ p('case file not found for '+id); }
const old=new Set((src?src.evidence:[]).map(e=>e.id).filter(Boolean));
if(!['killed','uncertain','survives'].includes(d.verdict)) p('verdict must be killed|uncertain|survives');
if(String(d.verdictReason||'').trim().length<40||String(d.verdictReason).length>700) p('verdictReason 40..700 chars');
const ids=new Set(); const ev=Array.isArray(d.newEvidence)?d.newEvidence:[]; if(ev.length<4) p('need >= 4 new evidence items');
for(const e of ev){ if(!new RegExp('^'+id+'-D\\d+$').test(e.id||'')) p('evidence id must be '+id+'-D#: '+e.id); if(ids.has(e.id)) p('dup id '+e.id); ids.add(e.id);
  if(!/^https:\/\//.test(e.url||'')) p(e.id+': url https'); if(String(e.quote||'').trim().length<15) p(e.id+': quote >=15 chars'); if(!['incumbent_price','demand','constraint','other'].includes(e.kind)) p(e.id+': kind'); if(e.evidenceClass!=='agent_reported') p(e.id+': evidenceClass agent_reported'); if(!String(e.date||'').trim()) p(e.id+': date'); }
const known=x=>ids.has(x)||old.has(x);
if(!Array.isArray(d.answers)||!d.answers.length) p('answers required'); else for(const a of d.answers){ if(!String(a.question||'').trim()||!String(a.answer||'').trim()) p('answer needs question+answer'); for(const r of a.evidenceIds||[]) if(!known(r)) p('answer cites unknown evidence '+r); }
for(const a of d.newAlternatives||[]){ if(!['free_tool','open_source','diy_or_status_quo','cheap_paid','paid_incumbent'].includes(a.kind)) p('alt kind '+a.kind); if(!['full','partial','none'].includes(a.coversWedge)) p('alt covers'); if(!/^https:\/\//.test(a.sourceLocator||'')) p('alt url'); if(typeof a.costUsdPerMonth!=='number') p('alt cost'); if(a.evidenceRef&&!known(a.evidenceRef)) p('alt evidenceRef unknown'); }
if(!Array.isArray(d.killReasons)) p('killReasons array'); else for(const k of d.killReasons){ if(!['fatal','major','minor'].includes(k.severity)) p('kill severity'); if(k.refClass!=='agent_reported') p('kill refClass'); if(!known(k.ref)) p('kill ref unknown '+k.ref); }
if(d.verdict==='killed'&&!(d.killReasons||[]).some(k=>k.severity==='fatal')&&(d.killReasons||[]).filter(k=>k.severity==='major').length<2) p('killed needs a fatal or two major reasons');
const e=d.economics||{}; for(const k of ['revenue365','cost365','pessimisticProfit365']) if(typeof e[k]!=='number') p('economics.'+k+' number'); if(typeof e.survivesPessimistic!=='boolean') p('economics.survivesPessimistic bool'); if(!Array.isArray(e.assumptions)||!e.assumptions.length) p('economics.assumptions');
if(d.verdict==='survives'&&!e.survivesPessimistic) p('survives requires positive pessimistic economics');
if(!Array.isArray(d.legalNotes)||!d.legalNotes.length) p('legalNotes'); if(!Array.isArray(d.unverified)) p('unverified array');
if(P.length){console.log('PROBLEMS ('+P.length+'):\n'+P.slice(0,30).join('\n'));process.exit(1);} console.log('OK',id,d.verdict);

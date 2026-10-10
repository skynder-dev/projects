// Aggregate scan-2 or scan-3 candidates (samples/g281_scanN/candidates) with the G281 v6 modules; writes samples/g281_scan2/aggregate.json. No network, no DB.
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const A=new URL('../../app/',import.meta.url).pathname;
const V6=require(A+'global_ranking_v6.js'), G=require(A+'global_gates_v6.js'), S=require(A+'global_scan_v6.js');
const N=Number(process.argv[2]||2); if(![2,3].includes(N)){console.error('usage: node aggregate_scan_g281.mjs <2|3>');process.exit(2);}
const SAMPLES=new URL('../../samples/',import.meta.url).pathname, dir=SAMPLES+'g281_scan'+N+'/';
const PROTOCOL='scan'+N+'_manual_edge_first_agent_reported';
const cands=[];
for(const f of fs.readdirSync(dir+'candidates').filter(x=>x.endsWith('.json')).sort()){
  const d=JSON.parse(fs.readFileSync(dir+'candidates/'+f,'utf8')); for(const c of d.candidates) cands.push(c);
}
const scan=S.assess(cands.map(c=>({id:c.id,name:c.name,family:c.family,researchProtocol:PROTOCOL})));
const rows=[], gateById={}, byId={}, summary=[];
for(const c of cands){
  const ev=c.evidence.map(x=>({...x,sourceType:'public_web_search'}));
  const row=V6.score({...c,evidence:ev});
  const g=G.runGates(c); rows.push(row); gateById[c.id]=g; byId[c.id]=c;
  const alts=(c.alternativesSurvey.alternatives||[]);
  summary.push({id:c.id,name:c.name,family:c.family,verdict:c.researcherVerdict,verdictReason:c.verdictReason||null,
    raw:row.raw_score,adjusted:row.adjusted_score,grade:row.confidence_grade,cap:row.cap_reason,
    edgeType:c.entrantEdge.type,edgeStatus:c.entrantEdge.status,gatesFailed:g.failed,cheapestAlternative:g.cheapestAlternative||null,
    unresolved:(g.unresolved||[]).length,evidenceCount:c.evidence.length,altCount:alts.length,
    altFull:alts.filter(a=>a.coversWedge==='full').map(a=>a.label),
    pessimisticOk:!!(c.deep&&c.deep.economics&&c.deep.economics.survivesPessimistic),
    killReasons:(c.deep&&c.deep.killReasons||[]).map(k=>({severity:k.severity,reason:k.reason,ref:k.ref}))});
}
let combined=null;
if(N===3){ const other=[]; for(const f of fs.readdirSync(SAMPLES+'g281_scan2/candidates').sort()) for(const c of JSON.parse(fs.readFileSync(SAMPLES+'g281_scan2/candidates/'+f,'utf8')).candidates) other.push(c);
  const all=[...other,...cands].map(c=>({id:c.id,name:c.name,family:c.family,researchProtocol:'manual_edge_first_agent_reported'})); const ca=S.assess(all); combined={withScan:2,valid:ca.valid,reasons:ca.reasons,rawCandidates:ca.rawCandidates,familiesRepresented:ca.familiesRepresented}; }
const dec=G.decide({scan,rows,gateById,candidatesById:byId,provisional:true});
const counts={}; for(const s of summary) counts[s.verdict]=(counts[s.verdict]||0)+1;
const out={scanId:'g281_scan'+N,protocol:PROTOCOL,generatedAt:new Date().toISOString(),scan,decision:dec,counts,combinedWithScan2:combined,candidates:summary};
fs.writeFileSync(dir+'aggregate.json',JSON.stringify(out,null,1));
console.log('scan valid:',scan.valid,scan.reasons.join('|'),'raw',scan.rawCandidates,'families',scan.familiesRepresented);
console.log('verdict counts',JSON.stringify(counts),'decision',dec.verdict,'leader',dec.leader,'hard',dec.hard_blockers.join(' ; ').slice(0,300));
for(const s of summary) console.log(s.id.padEnd(6),s.verdict.padEnd(9),String(s.raw).padStart(5),s.edgeType.padEnd(40),'full-alt:',s.altFull.length,'pess:',s.pessimisticOk);

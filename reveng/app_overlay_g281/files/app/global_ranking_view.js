((root,factory)=>{
  const Scan=(typeof module==='object'&&module.exports)?require('./global_scan_v6.js'):root&&root.RevEngGlobalScanV6;
  const Spend=(typeof module==='object'&&module.exports)?require('./spend_guard_v6.js'):root&&root.RevEngSpendGuardV6;
  const api=factory(Scan,Spend);
  if(typeof module==='object'&&module.exports) module.exports=api;
  if(root) root.RevEngGlobalRankingView=api;
})(typeof window!=='undefined'?window:globalThis,(Scan,Spend)=>{
  'use strict';
  // Pure view-model for the global ranking page. No DOM here: the page only renders what this returns.
  // It never invents a ranking: v6 needs 12 judged component scores per candidate; without them the page says so and shows no v6 rank.
  const CONTRACT_ID='reveng_global_ranking_view_v1';
  const freeze=Object.freeze;
  const STATUS_LABEL=freeze({queued:'Queued for verification',gate_rejected:'Rejected by hard gate',rejected_unverified:'Rejected (basis not engine-verified)',rejected_verified:'Rejected (verified)'});
  function statusOf(c){
    const m=c.metadata||{};
    if(c.status!=='rejected') return 'queued';
    if(m.rejection_basis==='engine_hard_gate') return 'gate_rejected';
    if(m.rejection_basis==='verified_provider_citation') return 'rejected_verified';
    return 'rejected_unverified';
  }
  function build(pkg){
    if(!pkg||!Array.isArray(pkg.candidates)) throw new Error('REVENG_VIEW_PACKAGE_INVALID');
    const asScan=pkg.candidates.map(c=>({id:c.candidate_key,name:c.raw_name,family:(c.metadata||{}).family,researchProtocol:(c.metadata||{}).scan_run}));
    const scan=Scan.assess(asScan);
    const rows=pkg.candidates.map(c=>{
      const m=c.metadata||{}, hints=Array.isArray(c.evidence_hints)?c.evidence_hints:[];
      const st=statusOf(c);
      return freeze({
        key:c.candidate_key,id:m.engine_id||c.candidate_key,name:c.raw_name,family:m.family||'unknown',buyer:c.buyer_segment||'',pain:c.core_job||'',wedge:c.primary_outcome||'',
        status:st,statusLabel:STATUS_LABEL[st],rejectionReason:c.rejection_reason||null,rejectionBasis:m.rejection_basis||null,
        lensScore:m.engine_score&&typeof m.engine_score.adjusted==='number'?m.engine_score.adjusted:null,
        lensLabel:m.engine_score?m.engine_score.label:null,
        v6Ranked:!!m.v6_component_scores,
        provisional:m.v6_provisional&&typeof m.v6_provisional.raw==='number'?freeze({raw:m.v6_provisional.raw,adjusted:m.v6_provisional.adjusted,grade:m.v6_provisional.grade||'D',cap:m.v6_provisional.cap_reason||null,note:m.v6_provisional.note||null}):null,
        researcherVerdict:m.final_verdict||m.researcher_verdict||null,firstPassVerdict:m.researcher_verdict||null,
        deep:m.deep_screen&&m.deep_screen.second_pass?freeze({verdict:m.deep_screen.verdict||'',reason:m.deep_screen.reason||'',economics:m.deep_screen.economics?freeze({...m.deep_screen.economics}):null,answers:freeze((m.deep_screen.answers||[]).map(a=>freeze({question:String(a.question||''),answer:String(a.answer||'')}))),unverified:freeze((m.deep_screen.unverified||[]).map(String))}):null,verdictReason:m.verdict_reason?String(m.verdict_reason).replace(/^open question:\s*/i,''):null,
        edge:m.entrant_edge?freeze({type:m.entrant_edge.type||'',status:m.entrant_edge.status||'',statement:m.entrant_edge.statement||''}):null,
        alternatives:(Array.isArray(m.alternatives)?m.alternatives:[]).map(a=>freeze({label:a.label||'',usdPerMonth:typeof a.usd_per_month==='number'?a.usd_per_month:null,covers:a.covers_wedge||'',url:a.url||null})),
        killReasons:(Array.isArray(m.kill_reasons)?m.kill_reasons:[]).map(k=>freeze({severity:k.severity||'minor',reason:k.reason||'',ref:k.ref||null})),
        legalNotes:Array.isArray(m.legal_notes)?freeze(m.legal_notes.map(String)):freeze([]),
        deepNotScreened:(m.deep_screen_not_screened&&typeof m.deep_screen_not_screened==='object')?String(m.deep_screen_not_screened.reason||'').slice(0,400):(typeof m.deep_screen_not_screened==='string'?m.deep_screen_not_screened.slice(0,400):null),
        deepDone:!!(m.deep_screen&&m.deep_screen.done&&m.deep_screen.complete),
        evidence:hints.map(h=>freeze({url:h.url||null,signal:h.signal||'',source:h.source||'',evidenceClass:h.evidence_class||'unverified',kind:h.kind||'other',stage:h.stage||'scan',recheck:h.recheck&&h.recheck.status?freeze({status:String(h.recheck.status),note:String(h.recheck.note||'')}):null})),
        verifiedCount:hints.filter(h=>h.evidence_class==='verified').length,nextStep:m.next_step||null
      });
    });
    const v6Ranked=rows.filter(r=>r.v6Ranked).length, v6Provisional=rows.filter(r=>r.provisional).length;
    const counts={total:rows.length,queued:0,gate_rejected:0,rejected_unverified:0,rejected_verified:0};
    for(const r of rows) counts[r.status]++;
    const reasons=[];
    if(!scan.valid) for(const r of scan.reasons) reasons.push('scan_not_valid: '+r);
    if(v6Ranked===0) reasons.push(v6Provisional>0
      ?'v6 scores are provisional (judged from agent_reported evidence; the entrant-edge hard gate caps them), so no v6 ranking exists'
      :'no candidate has v6 component scores yet, so no v6 ranking exists');
    if(v6Provisional>0&&!rows.some(r=>r.status==='queued'&&r.edge&&r.edge.status==='evidenced_independent')) reasons.push('no candidate has an independently evidenced entrant edge (hard gate)');
    if(!rows.some(r=>r.status==='queued'&&r.deepDone)) reasons.push('no surviving candidate has completed a deep screen');
    const verdict={state:'no_winner',winner:null,reasons:freeze(reasons)};
    const est=Spend.estimateRun({calls:30});
    const spend=freeze({authorizedUsd:0,paidCallsAllowed:false,rule:'No paid call without an explicit dollar amount and your yes.',
      estimate:est.ok?freeze({calls:30,expectedUsd:est.expectedUsd,maxUsd:est.maxUsd,basis:est.basis}):null});
    const families=[...new Set(rows.map(r=>r.family))].sort();
    const rm=(pkg.run&&pkg.run.metadata)||{}; const extension=rm.extends?freeze({of:String(rm.extends),combined:rm.combined_with_extended?freeze({valid:!!rm.combined_with_extended.valid,rawCandidates:rm.combined_with_extended.rawCandidates,familiesRepresented:rm.combined_with_extended.familiesRepresented}):null}):null;
    return freeze({contract:CONTRACT_ID,scan,verdict,extension,counts:freeze(counts),rows:freeze(rows),families:freeze(families),spend,v6Ranked,v6Provisional});
  }
  // Filter rows; sorts by the labelled lens score (never presented as a v6 rank).
  function filter(model,{family='',status='',q=''}={}){
    const needle=String(q||'').trim().toLowerCase();
    const out=model.rows.filter(r=>(!family||r.family===family)&&(!status||r.status===status)&&(!needle||[r.name,r.buyer,r.id,r.family].join(' ').toLowerCase().includes(needle)));
    const key=r=>r.lensScore??(r.provisional?r.provisional.raw:-1);
    return out.sort((a,b)=>(key(b)-key(a))||(a.id<b.id?-1:1));
  }
  const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const safeUrl=u=>/^https:\/\//i.test(String(u||''))?String(u):null;
  return freeze({CONTRACT_ID,STATUS_LABEL,statusOf,build,filter,esc,safeUrl});
});

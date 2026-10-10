(() => {
  'use strict';
  const View=window.RevEngGlobalRankingView;
  // Scan snapshots: the first scan (REVENG_GLOBAL_VIEW_DATA) plus any later ones (REVENG_GLOBAL_VIEW_DATA_EXTRA). The newest is shown first.
  const runs=[window.REVENG_GLOBAL_VIEW_DATA].concat(Array.isArray(window.REVENG_GLOBAL_VIEW_DATA_EXTRA)?window.REVENG_GLOBAL_VIEW_DATA_EXTRA:[]).filter(d=>d&&Array.isArray(d.candidates));
  // Default: the newest scan that is valid on its own (an extension that is not valid alone never becomes the headline).
  const defaultIdx=(()=>{for(let i=runs.length-1;i>=0;i--){try{if(View&&View.build(runs[i]).scan.valid) return i;}catch(_){}}return runs.length-1;})();
  const data=runs[defaultIdx];
  const $=id=>document.getElementById(id);
  // DOM is built with createElement/textContent only: source text is never parsed as HTML.
  function h(tag,attrs,...kids){
    const el=document.createElement(tag);
    for(const [k,v] of Object.entries(attrs||{})){ if(v===null||v===undefined||v===false) continue; if(k==='class') el.className=v; else if(k==='text') el.textContent=v; else el.setAttribute(k,v===true?'':v); }
    for(const kid of kids.flat()) if(kid!==null&&kid!==undefined&&kid!==false) el.append(kid.nodeType?kid:document.createTextNode(String(kid)));
    return el;
  }
  const chipClass={queued:'info',gate_rejected:'bad',rejected_unverified:'warn',rejected_verified:'bad'};
  const evClass={verified:'good',search_confirmed:'info',agent_reported:'warn',unverified:'warn'};
  const FAMILY=f=>String(f).replace(/_/g,' ');
  if(!View||!data){ $('grVerdict').replaceChildren(h('h2',{text:'No scan data loaded'}),h('p',{text:'The scan snapshot could not be loaded, so nothing is shown. No ranking is invented.'})); return; }
  const money=v=>'$'+Number(v).toFixed(2);
  const usd0=v=>(Number(v)<0?'-':'')+'$'+Math.abs(Math.round(Number(v))).toLocaleString('en-US');
  const runSel=$('grRun'), famSel=$('grFamily'), stSel=$('grStatus'), q=$('grSearch');
  let model=null, redraw=null;
  function mount(pkg){
  model=View.build(pkg);
  $('grVerdict').replaceChildren(
    h('h2',{text:'No winner'}),
    h('p',{text:model.v6Provisional>0
      ?'No valid global winner exists yet. Scores below are provisional (judged by the researcher from agent_reported evidence, entrant edge not independently evidenced); they order the list but are not a v6 rank.'
      :'No valid global winner exists yet. This page lists what was scanned and why nothing qualifies; it does not rank by v6 because no candidate has v6 component scores.'}),
    h('ul',{},model.verdict.reasons.map(r=>h('li',{text:r}))));
  $('grScan').replaceChildren(...[h('h3',{text:'Scan validity'}),h('dl',{class:'gr-kv'},
    h('dt',{text:'Valid scan'}),h('dd',{text:model.scan.valid?'Yes':'No'}),
    h('dt',{text:'Raw candidates'}),h('dd',{text:`${model.scan.rawCandidates} (need ≥30)`}),
    h('dt',{text:'Families'}),h('dd',{text:`${model.scan.familiesRepresented} (need ≥8)`}),
    h('dt',{text:'v6 scored'}),h('dd',{text:`${model.v6Ranked} of ${model.counts.total}`}),
    model.v6Provisional>0?[h('dt',{text:'Provisional scores'}),h('dd',{text:`${model.v6Provisional} of ${model.counts.total}`})]:null),
    model.scan.valid?null:h('p',{class:'gr-note',text:model.scan.reasons.join('; ')}),
    model.extension?h('p',{class:'gr-note',text:`Extension of ${model.extension.of}: counts only together with it`+(model.extension.combined?` (combined ${model.extension.combined.rawCandidates} candidates, ${model.extension.combined.familiesRepresented} families, ${model.extension.combined.valid?'valid':'not valid'}).`:'.')}):null].filter(Boolean));
  $('grCounts').replaceChildren(h('h3',{text:'Outcome of the scan'}),h('dl',{class:'gr-kv'},
    ...['queued','gate_rejected','rejected_unverified','rejected_verified'].flatMap(k=>[h('dt',{text:View.STATUS_LABEL[k]}),h('dd',{text:String(model.counts[k])})])));
  const sp=model.spend;
  $('grSpend').replaceChildren(h('h3',{text:'Spend'}),h('dl',{class:'gr-kv'},
    h('dt',{text:'Authorized'}),h('dd',{text:money(sp.authorizedUsd)}),
    h('dt',{text:'Paid calls'}),h('dd',{text:sp.paidCallsAllowed?'Allowed':'Blocked'}),
    sp.estimate?[h('dt',{text:'Rerun estimate (30 calls)'}),h('dd',{text:`${money(sp.estimate.expectedUsd)} – ${money(sp.estimate.maxUsd)}`})]:null),
    h('p',{class:'gr-note',text:sp.rule+' The estimate is from the measured first scan and is not a quote.'}));
  famSel.replaceChildren(h('option',{value:'',text:'All families'}),...model.families.map(f=>h('option',{value:f,text:FAMILY(f)})));
  stSel.replaceChildren(h('option',{value:'',text:'All statuses'}),...Object.entries(View.STATUS_LABEL).map(([k,l])=>h('option',{value:k,text:l})));
  $('grNote').textContent=model.v6Provisional>0
    ?'Order: provisional v6 raw score (researcher-judged, edge unverified, capped by the entrant-edge hard gate). This is NOT a v6 rank and not a ranking of winners.'
    :'Order: G280 balanced-lens score from the first scan. This is NOT a v6 score and must not be read as a v6 rank.';
  function item(r){
    const link=e=>{const u=View.safeUrl(e.url);return h('li',{},h('span',{class:`gr-chip ${evClass[e.evidenceClass]||'warn'}`,text:e.evidenceClass.replace('_',' ')}),' ',e.stage==='deep'?[h('span',{class:'gr-chip',text:'deep'}),' ']:null,e.recheck?[h('span',{class:`gr-chip ${e.recheck.status==='confirmed'?'info':'warn'}`,text:'re-read: '+e.recheck.status.replace('_',' '),title:e.recheck.note}),' ']:null,u?h('a',{href:u,target:'_blank',rel:'noopener noreferrer',text:e.source||u}):h('span',{text:e.source||'no link'}),e.signal?h('span',{text:' – '+e.signal}):null);};
    return h('details',{class:'gr-item','data-status':r.status,'data-family':r.family},
      h('summary',{},h('span',{class:'gr-id',text:r.id}),h('span',{class:'gr-name',text:r.name}),
        h('span',{class:'gr-chips'},h('span',{class:'gr-chip',text:FAMILY(r.family)}),h('span',{class:`gr-chip ${chipClass[r.status]}`,text:r.statusLabel}),r.researcherVerdict?h('span',{class:`gr-chip ${r.researcherVerdict==='killed'?'bad':'warn'}`,text:r.researcherVerdict}):null,r.deep?h('span',{class:'gr-chip info',text:'deep screened'}):null,r.lensScore===null?null:h('span',{class:'gr-chip',text:`lens ${r.lensScore}`}),r.provisional?h('span',{class:'gr-chip',title:r.provisional.note||'',text:`provisional ${r.provisional.raw}`}):null)),
      h('div',{class:'gr-body-in'},
        h('h4',{text:'Buyer'}),h('p',{text:r.buyer}),h('h4',{text:'Pain'}),h('p',{text:r.pain}),h('h4',{text:'Entrant wedge'}),h('p',{text:r.wedge}),
        r.edge?[h('h4',{text:`Entrant edge (${r.edge.type.replace(/_/g,' ')} – ${r.edge.status})`}),h('p',{text:r.edge.statement})]:null,
        r.researcherVerdict==='uncertain'&&r.verdictReason?[h('h4',{text:'Open question'}),h('p',{text:r.verdictReason})]:null,
        r.deep?[h('h4',{text:`Deep screen (first pass: ${r.firstPassVerdict||'n/a'}, after deep screen: ${r.deep.verdict})`}),h('p',{text:r.deep.reason}),
          r.deep.economics?h('p',{class:'gr-note',text:`Year-1 model (assumption-based): revenue ${usd0(r.deep.economics.revenue365_usd)}, cost ${usd0(r.deep.economics.cost365_usd)}, pessimistic profit ${usd0(r.deep.economics.pessimistic_profit365_usd)}; survives pessimistic case: ${r.deep.economics.survives_pessimistic?'yes':'no'}.`}):null,
          r.deep.answers.length?h('ul',{class:'gr-ev'},r.deep.answers.map(a=>h('li',{},h('strong',{text:a.question+' '}),h('span',{text:a.answer})))):null,
          r.deep.unverified.length?[h('h4',{text:'Not verified'}),h('ul',{class:'gr-ev'},r.deep.unverified.map(u=>h('li',{text:u})))]:null]:null,
        r.alternatives.length?[h('h4',{text:'Cheapest alternatives checked'}),h('ul',{class:'gr-ev'},r.alternatives.map(a=>{const u=View.safeUrl(a.url);return h('li',{},u?h('a',{href:u,target:'_blank',rel:'noopener noreferrer',text:a.label}):h('span',{text:a.label}),h('span',{text:` – ${a.usdPerMonth===null?'price n/a':(a.usdPerMonth===0?'free':'$'+a.usdPerMonth+'/mo')}, covers wedge: ${a.covers}`}));}))]:null,
        r.killReasons.length?[h('h4',{text:'Kill reasons (agent reported)'}),h('ul',{class:'gr-ev'},r.killReasons.map(k=>h('li',{text:`[${k.severity}] ${k.reason}`})))]:null,
        r.legalNotes.length?[h('h4',{text:'Legal notes'}),h('ul',{class:'gr-ev'},r.legalNotes.map(n=>h('li',{text:n})))]:null,
        r.rejectionReason?[h('h4',{text:'Why rejected'}),h('p',{text:r.rejectionReason}),h('p',{class:'gr-note',text:'Basis: '+(r.rejectionBasis||'unknown').replace(/_/g,' ')})]:null,
        r.nextStep?[h('h4',{text:'Next step'}),h('p',{text:r.nextStep})]:null,
        h('h4',{text:`Evidence (${r.evidence.length}, verified ${r.verifiedCount})`}),h('ul',{class:'gr-ev'},r.evidence.map(link))));
  }
  function draw(){
    const rows=View.filter(model,{family:famSel.value,status:stSel.value,q:q.value});
    $('grCount').textContent=`${rows.length} of ${model.counts.total} candidates`;
    $('grList').replaceChildren(...rows.map(item));
  }
  famSel.value=''; stSel.value=''; q.value='';
  redraw=draw; draw();
  }
  function onFilter(){ if(redraw) redraw(); }
  [famSel,stSel].forEach(e=>e.addEventListener('change',onFilter)); q.addEventListener('input',onFilter);
  if(runs.length>1){
    runSel.replaceChildren(...runs.map((r,i)=>h('option',{value:String(i),text:`Scan ${i+1} · ${r.candidates.length} candidates`+((r.run&&r.run.metadata&&r.run.metadata.extends)?' · extension':'')})));
    runSel.value=String(defaultIdx); runSel.closest('label').hidden=false;
    runSel.addEventListener('change',()=>mount(runs[Number(runSel.value)]));
  }
  mount(data);
})();

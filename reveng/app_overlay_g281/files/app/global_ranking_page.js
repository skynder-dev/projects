(() => {
  'use strict';
  const View=window.RevEngGlobalRankingView, data=window.REVENG_GLOBAL_VIEW_DATA;
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
  const model=View.build(data);
  const money=v=>'$'+Number(v).toFixed(2);
  $('grVerdict').replaceChildren(
    h('h2',{text:'No winner'}),
    h('p',{text:'No valid global winner exists yet. This page lists what was scanned and why nothing qualifies; it does not rank by v6 because no candidate has v6 component scores.'}),
    h('ul',{},model.verdict.reasons.map(r=>h('li',{text:r}))));
  $('grScan').replaceChildren(...[h('h3',{text:'Scan validity'}),h('dl',{class:'gr-kv'},
    h('dt',{text:'Valid scan'}),h('dd',{text:model.scan.valid?'Yes':'No'}),
    h('dt',{text:'Raw candidates'}),h('dd',{text:`${model.scan.rawCandidates} (need ≥30)`}),
    h('dt',{text:'Families'}),h('dd',{text:`${model.scan.familiesRepresented} (need ≥8)`}),
    h('dt',{text:'v6 scored'}),h('dd',{text:`${model.v6Ranked} of ${model.counts.total}`})),
    model.scan.valid?null:h('p',{class:'gr-note',text:model.scan.reasons.join('; ')})].filter(Boolean));
  $('grCounts').replaceChildren(h('h3',{text:'Outcome of the scan'}),h('dl',{class:'gr-kv'},
    ...['queued','gate_rejected','rejected_unverified','rejected_verified'].flatMap(k=>[h('dt',{text:View.STATUS_LABEL[k]}),h('dd',{text:String(model.counts[k])})])));
  const sp=model.spend;
  $('grSpend').replaceChildren(h('h3',{text:'Spend'}),h('dl',{class:'gr-kv'},
    h('dt',{text:'Authorized'}),h('dd',{text:money(sp.authorizedUsd)}),
    h('dt',{text:'Paid calls'}),h('dd',{text:sp.paidCallsAllowed?'Allowed':'Blocked'}),
    sp.estimate?[h('dt',{text:'Rerun estimate (30 calls)'}),h('dd',{text:`${money(sp.estimate.expectedUsd)} – ${money(sp.estimate.maxUsd)}`})]:null),
    h('p',{class:'gr-note',text:sp.rule+' The estimate is from the measured first scan and is not a quote.'}));
  const famSel=$('grFamily'), stSel=$('grStatus'), q=$('grSearch');
  famSel.replaceChildren(h('option',{value:'',text:'All families'}),...model.families.map(f=>h('option',{value:f,text:FAMILY(f)})));
  stSel.replaceChildren(h('option',{value:'',text:'All statuses'}),...Object.entries(View.STATUS_LABEL).map(([k,l])=>h('option',{value:k,text:l})));
  $('grNote').textContent='Order: G280 balanced-lens score from the first scan. This is NOT a v6 score and must not be read as a v6 rank.';
  function item(r){
    const link=e=>{const u=View.safeUrl(e.url);return h('li',{},h('span',{class:`gr-chip ${evClass[e.evidenceClass]||'warn'}`,text:e.evidenceClass.replace('_',' ')}),' ',u?h('a',{href:u,target:'_blank',rel:'noopener noreferrer',text:e.source||u}):h('span',{text:e.source||'no link'}),e.signal?h('span',{text:' – '+e.signal}):null);};
    return h('details',{class:'gr-item','data-status':r.status,'data-family':r.family},
      h('summary',{},h('span',{class:'gr-id',text:r.id}),h('span',{class:'gr-name',text:r.name}),
        h('span',{class:'gr-chips'},h('span',{class:'gr-chip',text:FAMILY(r.family)}),h('span',{class:`gr-chip ${chipClass[r.status]}`,text:r.statusLabel}),r.lensScore===null?null:h('span',{class:'gr-chip',text:`lens ${r.lensScore}`}))),
      h('div',{class:'gr-body-in'},
        h('h4',{text:'Buyer'}),h('p',{text:r.buyer}),h('h4',{text:'Pain'}),h('p',{text:r.pain}),h('h4',{text:'Entrant wedge'}),h('p',{text:r.wedge}),
        r.rejectionReason?[h('h4',{text:'Why rejected'}),h('p',{text:r.rejectionReason}),h('p',{class:'gr-note',text:'Basis: '+(r.rejectionBasis||'unknown').replace(/_/g,' ')})]:null,
        r.nextStep?[h('h4',{text:'Next step'}),h('p',{text:r.nextStep})]:null,
        h('h4',{text:`Evidence (${r.evidence.length}, verified ${r.verifiedCount})`}),h('ul',{class:'gr-ev'},r.evidence.map(link))));
  }
  function draw(){
    const rows=View.filter(model,{family:famSel.value,status:stSel.value,q:q.value});
    $('grCount').textContent=`${rows.length} of ${model.counts.total} candidates`;
    $('grList').replaceChildren(...rows.map(item));
  }
  [famSel,stSel].forEach(e=>e.addEventListener('change',draw)); q.addEventListener('input',draw);
  draw();
})();

import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ROOT=new URL('../../',import.meta.url).pathname;
const E=require(ROOT+'app/evidence_protocol_v6.js'), S=require(ROOT+'app/spend_guard_v6.js'), V6=require(ROOT+'app/global_ranking_v6.js');
const pol=JSON.parse(fs.readFileSync(ROOT+'server/REVA2_G281_SOURCE_POLICY_SNAPSHOT.json'));
let checks=0; const t=(c,m)=>{assert.ok(c,m);checks++;};

// ---- legal source policy
t(pol.sources.length===9&&pol.pilot_key==='real_evidence_v1','policy snapshot has 9 sources');
let r=E.checkMethod(pol,'provider_search_citation'); t(r.allowed&&r.sourceKey==='public_web_search'&&r.eligibility==='review_required','provider citations allowed, review_required');
r=E.checkMethod(pol,'manual_public_review'); t(r.allowed,'manual public review allowed');
r=E.checkMethod(pol,'official_api_documented'); t(!r.allowed&&r.reason==='source_not_configured','official API blocked until configured');
for(const m of E.FORBIDDEN_METHODS){ t(!E.checkMethod(pol,m).allowed&&E.checkMethod(pol,m).reason==='forbidden_method','forbidden '+m); }
t(E.checkMethod(pol,'telepathy').reason==='unknown_method','unknown method refused');
assert.throws(()=>E.assertMethod(pol,'http_scrape'),e=>e.code==='REVENG_SOURCE_METHOD_REFUSED'); checks++;
// every scraping-type prohibition in the DB registry is covered by a forbidden method name
t(pol.sources.filter(s=>s.prohibited_use.some(x=>/scraping/.test(x))).length>=5,'registry prohibits automated scraping on public sources');
// internal synthesis / private inputs are never global evidence
const fakePol={sources:[{source_key:'public_web_search',activation_state:'available',evidence_eligibility:'hypothesis_only'}]};
t(E.checkMethod(fakePol,'provider_search_citation').reason==='not_global_evidence:hypothesis_only','hypothesis-only source refused');

// ---- two-phase evidence resolution
const res={citations:[{url:'https://a.com/pricing',title:'A',cited_text:'Plan $19/mo'},{url:'https://a.com/pricing',title:'A',cited_text:'Plan $19/mo'},{url:'http://insecure.com',title:'X',cited_text:'nope'},{url:'https://b.com',title:'B',cited_text:''}],
  searchResults:[{url:'https://c.com/x',title:'C',page_age:'2026-09'},{url:'https://c.com/x',title:'C'},{url:'ftp://d',title:'D'}]};
const idx=E.buildRefIndex(res);
t(idx.excerpts.length===1&&idx.excerpts[0].id==='C1','one https excerpt, deduplicated, empty excerpt dropped');
t(idx.results.length===1&&idx.results[0].id==='S1','one https search result, deduplicated');
const rv=E.resolveEvidence([{ref:'C1',kind:'incumbent_price',shows:'price'},{ref:'S1',kind:'demand',shows:'d'},{ref:'C9',kind:'demand'},{ref:'C1',kind:'bogus'},null],idx,'X-E');
t(rv.evidence.length===2&&rv.dropped===3,'invented ref, bad kind and null dropped');
t(rv.evidence[0].evidenceClass==='verified'&&rv.evidence[0].quote==='Plan $19/mo'&&rv.evidence[0].method==='provider_citation_excerpt','C# => verified with provider quote');
t(rv.evidence[1].evidenceClass==='search_confirmed'&&rv.evidence[1].quote===null,'S# => search_confirmed, no quote');
t(rv.map.E1==='X-E1'&&rv.map.E2==='X-E2','E# map');
// model-claimed class is ignored: nothing the model says can promote evidence
const promo=E.resolveEvidence([{ref:'S1',kind:'demand',class:'verified',evidenceClass:'verified'}],idx,'P'); t(promo.evidence[0].evidenceClass==='search_confirmed','model cannot promote S# to verified');
const ag=E.markAgentReported([{url:'https://z.com',quote:'q',kind:'demand',evidenceClass:'verified'},{sourceType:'owner_provided',kind:'weird'}],'M'); t(ag.every(x=>x.evidenceClass==='agent_reported')&&ag[1].kind==='other'&&ag[1].sourceType==='owner_provided','imported evidence stays agent_reported');
// evidence from this protocol feeds the v6 scorer with the right classes
const base={id:'P',componentScores:Object.fromEntries(V6.DIMENSIONS.map(k=>[k,5])),confidenceGrade:'A',evidence:[...rv.evidence,...ag],entrantEdge:null};
const sc=V6.score(base); t(sc.audit.verifiedEvidenceCount===1&&sc.confidence_grade==='D'&&sc.audit.droppedEvidence.length===1,'one verified item => grade D, owner-provided dropped');
t(E.classifyProviderError('Your credit balance is too low')==='fatal'&&E.classifyProviderError('anthropic_http_401')==='fatal'&&E.classifyProviderError('timeout')==='transient','fatal provider errors recognised');

// ---- spend guard
const auth=(o={})=>({scopeKey:'scan-1',amountUsd:5,confirmedByOwner:true,confirmationText:'yes, $5',confirmedAt:'2026-10-10T10:00:00Z',...o});
const L0={entries:[]};
for(const [o,why] of [[{amountUsd:undefined},'explicit_positive_dollar_amount_required'],[{amountUsd:0},'explicit_positive_dollar_amount_required'],[{amountUsd:'abc'},'explicit_positive_dollar_amount_required'],
  [{confirmedByOwner:false},'owner_confirmation_missing'],[{confirmationText:''},'owner_confirmation_text_missing'],[{simulated:true},'simulated_authorization_never_counts'],[{scopeKey:''},'scope_key_required'],[{confirmedAt:'x'},'confirmed_at_required']]){
  const x=S.reserve({authorization:auth(o),ledger:L0,attemptId:'a1',estimatedMaxUsd:1}); t(!x.ok&&x.reason===why,why); }
t(S.reserve({authorization:null,ledger:L0,attemptId:'a1',estimatedMaxUsd:1}).reason==='no_authorization','no authorization');
t(S.reserve({authorization:auth(),ledger:L0,attemptId:'',estimatedMaxUsd:1}).reason==='attempt_id_required','attempt id');
t(S.reserve({authorization:auth(),ledger:L0,attemptId:'a',estimatedMaxUsd:0}).reason==='estimate_required','estimate required');
let x=S.reserve({authorization:auth(),ledger:L0,attemptId:'a1',estimatedMaxUsd:2}); t(x.ok&&x.remainingAfterUsd===3,'reserve 2 of 5');
let L=x.ledger; x=S.reserve({authorization:auth(),ledger:L,attemptId:'a1',estimatedMaxUsd:2}); t(x.ok&&x.idempotent,'same attempt is idempotent');
x=S.reserve({authorization:auth(),ledger:L,attemptId:'a2',estimatedMaxUsd:3.5}); t(!x.ok&&x.reason==='would_exceed_authorized_amount'&&x.remainingUsd===3,'cannot exceed authorized amount');
// settle with a smaller actual frees headroom; cumulative across "runs" because the ledger is passed in again
x=S.settle({ledger:L,scopeKey:'scan-1',attemptId:'a1',actualUsd:1.2}); t(x.ok,'settle'); L=x.ledger;
t(S.totals(L,'scan-1').spent===1.2&&S.totals(L,'scan-1').reserved===0,'spent 1.2, reserved 0');
x=S.reserve({authorization:auth(),ledger:L,attemptId:'a2',estimatedMaxUsd:3.8}); t(x.ok,'3.8 fits in 3.8 remaining'); L=x.ledger;
x=S.reserve({authorization:auth(),ledger:L,attemptId:'a3',estimatedMaxUsd:0.01}); t(!x.ok,'nothing left after reservation (process restart does not reset the budget)');
t(S.settle({ledger:L,scopeKey:'scan-1',attemptId:'nope',actualUsd:1}).reason==='no_reservation_for_attempt','settle needs reservation');
t(S.settle({ledger:L,scopeKey:'scan-1',attemptId:'a2',actualUsd:-1}).reason==='actual_usd_required','settle needs actual');
// another scope is independent
x=S.reserve({authorization:auth({scopeKey:'scan-2'}),ledger:L,attemptId:'b1',estimatedMaxUsd:4}); t(x.ok,'other scope independent');
// fatal provider error (credits out) blocks until a NEW later authorization
const LF=S.recordFatal({ledger:L0,scopeKey:'scan-1',at:'2026-10-10T11:00:00Z',message:'Your credit balance is too low'});
x=S.reserve({authorization:auth(),ledger:LF,attemptId:'c1',estimatedMaxUsd:1}); t(!x.ok&&x.reason==='provider_fatal_blocks_calls_until_new_authorization','fatal blocks');
x=S.reserve({authorization:auth({confirmedAt:'2026-10-10T12:00:00Z'}),ledger:LF,attemptId:'c1',estimatedMaxUsd:1}); t(x.ok,'new later authorization clears fatal');
// estimate from measured data
const est=S.estimateRun({calls:30}); t(Math.abs(est.expectedUsd-6.597618)<0.001&&est.basis==='live_scan_1_measured','estimate reproduces the measured $6.5976 for 30 calls: '+est.expectedUsd);
t(est.maxUsd>est.expectedUsd&&Math.abs(est.maxUsd-est.expectedUsd*1.5)<0.001,'max = 1.5x expected');
t(S.estimateRun({calls:0}).reason==='calls_must_be_positive_integer','calls validated');
t(S.estimateRun({calls:5,prices:{inPerMTok:1}}).reason.startsWith('price_missing'),'prices never guessed');
t(S.estimateRun({calls:5,prices:{inPerMTok:1,outPerMTok:5,perSearch:0.01},perCall:{inputTokens:1000,outputTokens:1000,searches:0}}).basis==='caller_supplied','caller supplied basis');
// the guard cannot create evidence, scores or winners: it exposes no such functions
t(!('score' in S)&&!('decide' in S),'spend guard has no ranking authority');
console.log(`reva2_g281_evidence_spend_v6 PASS ${checks} checks`);

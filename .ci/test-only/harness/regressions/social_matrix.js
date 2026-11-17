'use strict';
// Independent, offline bounded scheduler. No candidate files are written.
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto');
const args=process.argv.slice(2),opt=k=>{const n=args.indexOf(k);return n<0?undefined:args[n+1]};
const sourcePath=path.resolve(opt('--source')||path.join(__dirname,'../../production/social246/app/local_binding.js'));
const out=path.resolve(opt('--out')||path.join(require('os').tmpdir(),'offline-editor-'+crypto.randomUUID()));
const clone=x=>JSON.parse(JSON.stringify(x)),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const shot=(job,n=0)=>({voiceovers:[`Saved narration ${job} ${n}`],screen_accents:[`Saved narration ${job} ${n}`],description:`Saved description ${job} ${n}`});
const A=(op,...v)=>({op,args:v});
const start=[A('open','A','g'),A('get','g')];
const scenarios=[];
function add(name,steps,known=null){scenarios.push({name,known,steps});}
for(const field of ['description','voice','accent'])for(const outcome of ['success','error','conflict','missing_revision']){
 add(`save_${field}_${outcome}_newer_text`,[...start,A('edit',field,'B'),A('save','s'),A('edit',field,'C'),...(outcome==='conflict'?[A('external','A')]:[]),A('reply', 's',outcome),A('unload'),A('save','retry'),A('reply','retry','success')]);
 for(const commitFirst of [false,true])for(const allow of [false,true]){
  if(commitFirst&&outcome==='conflict')continue; // A committed request cannot later be a server CAS refusal.
  add(`pending_revert_${field}_${outcome}_commit${commitFirst}_discard${allow}`,[...start,A('edit',field,'B'),A('save','s'),...(commitFirst?[A('commit','s')]:[]),A('edit',field,'@baseline'),A('unload'),A('close',allow),A('reply','s',outcome)],'F7_PENDING_BASELINE');
 }
}
for(const order of [[0,1],[1,0]])for(const jobs of [['A','A'],['A','B']]){
 add(`opens_${jobs.join('')}_${order.join('')}`,[A('open','A','x'),...(jobs[1]==='B'?[A('nav','B')]:[]),A('open',jobs[1],'y'),A('get',order[0]?'y':'x'),A('edit','description','C'),A('get',order[1]?'y':'x'),A('unload')]);
}
for(const field of ['description','voice','accent'])for(const consent of [false,true]){
 add(`reload_${field}_consent${consent}_new_text`,[...start,A('edit',field,'B'),A('consent',consent),A('open','A','reload'),A('edit',field,'C'),A('get','reload'),A('unload')]);
 add(`reload_${field}_typed_after_clean_request`,[...start,A('open','A','reload'),A('edit',field,'B'),A('get','reload'),A('unload')]);
}
for(const hadEditor of [false,true])for(const response of ['success','error']){
 add(`navigation_while_get_editor${hadEditor}_${response}`,[...(hadEditor?start:[]),A('open','A','late'),A('nav','B'),A('get','late',response)],'F8_NAVIGATION');
}
for(const result of ['success','error','conflict','missing_revision'])for(const other of [false,true])for(const allow of [false,true]){
 add(`discard_pending_${result}_other${other}_allow${allow}`,[...start,A('edit','description','B'),A('save','old'),A('close',allow),A('nav',other?'B':'A'),A('open',other?'B':'A','new'),A('get','new'),A('edit','description','C'),A('reply','old',result),A('unload')]);
}
for(const oldOutcome of ['success','error','conflict'])for(const other of [false,true]){
 add(`save_response_order_${oldOutcome}_other${other}`,[...start,A('edit','description','B'),A('save','old'),A('close',true),A('nav',other?'B':'A'),A('open',other?'B':'A','new'),A('get','new'),A('edit','description','C'),A('save','newsave'),A('reply','newsave','success'),A('reply','old',oldOutcome)]);
}
add('same_editor_double_save_suppressed',[...start,A('edit','description','B'),A('save','one'),A('save','two',true),A('edit','description','C'),A('reply','one','success'),A('save','three'),A('reply','three','success')]);
add('close_invalidates_pending_reload',[...start,A('open','A','late'),A('close',true),A('get','late')]);
add('commit_ack_separate_next_get_sees_committed_revision',[...start,A('edit','description','B'),A('save','s'),A('commit','s'),A('close',true),A('open','A','new'),A('get','new'),A('edit','description','C'),A('save','n'),A('reply','n','success'),A('reply','s','success')]);
add('uncertain_error_after_commit_then_baseline_revert',[...start,A('edit','description','B'),A('save','s'),A('commit','s'),A('edit','description','@baseline'),A('reply','s','error'),A('unload'),A('close',false)],'F7_PENDING_BASELINE');
for(const field of ['description','voice','accent'])add(`pending_revert_reopen_${field}`,[...start,A('edit',field,'B'),A('save','s'),A('edit',field,'@baseline'),A('consent',false),A('open','A','reload'),A('get','reload'),A('reply','s','success'),A('unload')],'F7_PENDING_BASELINE');

// v2 additions, defined after the locked v1 matrix was run against RC0008.
for(const hadEditor of [false,true])for(const response of ['success','error'])add(`navigation_ABA_editor${hadEditor}_${response}`,[...(hadEditor?start:[]),A('open','A','late'),A('nav','B'),A('nav','A'),A('get','late',response)],'F8_NAVIGATION');
add('restart_without_save',[...start,A('edit','description','B'),A('restart'),...start]);
add('restart_after_ack_then_local_edit',[...start,A('edit','description','B'),A('save','s'),A('reply','s','success'),...start,A('edit','description','C'),A('restart'),...start]);
add('restart_after_commit_before_ack',[...start,A('edit','description','B'),A('save','s'),A('commit','s'),A('restart'),...start]);

// Author extension v3: original 110 independent traces above remain unchanged.
for(const field of ['description','voice','accent'])for(const outcome of ['error','lost_after_commit','conflict','missing_revision']){
 add(`reconcile_${field}_${outcome}_read_then_explicit_save`,[...start,A('edit',field,'B'),A('save','s'),...(outcome==='lost_after_commit'?[A('commit','s')]:[]),...(outcome==='conflict'?[A('external','A')]:[]),A('edit',field,'@baseline'),A('reply','s',outcome==='lost_after_commit'?'error':outcome),A('unload'),A('close',false),A('check','read'),A('get','read'),A('unload'),A('save','retry'),A('reply','retry','success')]);
}
for(const field of ['description','voice','accent']){
 add(`reconcile_${field}_read_failure_then_retry`,[...start,A('edit',field,'B'),A('save','s'),A('commit','s'),A('edit',field,'@baseline'),A('reply','s','error'),A('check','badread'),A('get','badread','error'),A('unload'),A('close',false),A('check','read'),A('get','read'),A('save','retry'),A('reply','retry','success')]);
 add(`reconcile_${field}_new_text_while_read_waits`,[...start,A('edit',field,'B'),A('save','s'),A('commit','s'),A('reply','s','error'),A('check','read'),A('edit',field,'C'),A('get','read'),A('unload'),A('save','retry'),A('reply','retry','success')]);
}
add('reconcile_old_reply_after_explicit_discard',[...start,A('edit','description','B'),A('save','s'),A('commit','s'),A('reply','s','error'),A('check','oldread'),A('close',true),A('open','A','new'),A('get','new'),A('edit','description','C'),A('get','oldread'),A('unload')]);
if(args.includes('--list')){console.log(JSON.stringify(scenarios.map(s=>({name:s.name,actions:s.steps.length,known:s.known})),null,2));process.exit(0);}
const full=fs.readFileSync(sourcePath,'utf8');let evaluated=full;
const mutant=opt('--mutant');
const mutations={ack_discards:['if(editor.snapshot()!==submitted)','if(false)'],duplicate_save:['if(localScriptEditorState!==editor||editor.pending)return;','if(localScriptEditorState!==editor)return;'],wrong_revision:['revision:editor.revision,voiceovers:values.voiceovers','revision:d.revision,voiceovers:values.voiceovers'],baseline_follows_local:['editor.baseline=submitted;','editor.baseline=editor.snapshot();']};
if(mutant){if(!mutations[mutant])throw Error('Unknown calibration mutant');const [from,to]=mutations[mutant];if(!evaluated.includes(from))throw Error('CALIBRATION_ADAPTER_INCOMPATIBLE: RC0007 mutation anchor not present');evaluated=evaluated.replace(from,to);}
const begin=evaluated.indexOf('let localScriptEditorState='),end=evaluated.indexOf('async function localPollPreparation(',begin);
if(begin<0||end<0)throw Error('ADAPTER_INCOMPATIBLE: editor extraction markers missing; review adapter, not a product verdict');
const detailBegin=evaluated.indexOf('let localDetailRevision='),detailEnd=evaluated.indexOf('async function localReview(',detailBegin);
if(detailBegin<0||detailEnd<0)throw Error('ADAPTER_INCOMPATIBLE: detail/navigation extraction markers missing');
const code=evaluated.slice(detailBegin,detailEnd)+evaluated.slice(begin,end)+String.raw`
globalThis.__editorProbe=()=>{const e=localScriptEditorState;return e?{id:e.id,revision:e.revision,baseline:e.baseline,snapshot:e.snapshot(),pending:e.pending,generation:e.generation}:null};`;
let hostSerial=0;
function host(server){
 const id=++hostSerial,map=new Map(),listeners={},requests=[],prompts=[],tasks={},labels={},violations=[],trace=[],notes=[],taskErrors=[];
 let selected='A',render=0,closed=0,allow=false,step=-1,editorSeq=0,navEpoch=0;
 class Node{
  constructor(tag){this.tag=tag;this.children=[];this.value='';this.dataset={};this.style={};this.textContent='';this.disabled=false;this.readOnly=false;}
  set id(v){this._id=v;map.set(v,this)}get id(){return this._id}
  set innerHTML(v){this.children=[];if(this._id==='modalhost'){render++;editorSeq++;}for(const m of v.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)){const n=new Node(m[1]);n.id=m[2];this.append(n)}}
  append(...xs){this.children.push(...xs)}prepend(...xs){this.children.unshift(...xs)}setAttribute(){}
  all(){return this.children.flatMap(x=>x&&typeof x==='object'?[x,...x.all()]:[])}
  querySelectorAll(s){return this.all().filter(n=>{const m=s.match(/^(\w+)\[data-([a-z-]+)\]$/);if(m){const key=m[2].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return n.tag===m[1]&&Object.hasOwn(n.dataset,key)}return n.tag===s})}
 }
 const modal=new Node('section');modal.id='modalhost';const root=new Node('main');root.id='detail';const $=s=>map.get(s.slice(1));
 const record=(inv,detail)=>violations.push({invariant:inv,step,detail});
 const probe=()=>ctx.__editorProbe();
 const editorToken=()=>`${id}/${editorSeq}`;
 function payload(job){const s=server[job];return {revision:s.revision,original:{kind:'source_preparation',package_id:'pkg-'+job},script:{segments:s.content.voiceovers.map((voiceover,i)=>({voiceover,on_screen:{headline:s.content.screen_accents[i]}}))},review:{scenes:[]},publication_text:{description_draft:{text:s.content.description}},publication_authorized:false};}
 function request(kind,job,body){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});const r={kind,job,body,immutable:body?clone(body):null,captured:kind==='get'?payload(job):null,resolve,reject,promise,owner:editorToken(),navEpoch,ack:false,committed:false,editorAtDispatch:probe()};requests.push(r);return promise;}
 const workflow=()=>({artifacts:{},editorial_decision:{state:'pending'},stages:{script:'unavailable'},current_material:{manual_draft_saved:false},delivery_receipt:{state:'none'},waiting:{},content_quality:{},queue_state:'synthetic_idle'});
 const ctx={document:{createElement:t=>new Node(t)},$,ownerLabel:x=>x,ownerState:x=>x,ownerReason:x=>x,localOwnerNotice:()=>{},ownerStaticHTML:x=>x,esc:x=>String(x),console,LOCAL_TOKEN:'no-server',
  window:{addEventListener:(n,f)=>listeners[n]=f},confirm:m=>{prompts.push({step,message:m,answer:allow});return allow},
  closeModal:()=>{closed++;modal.children=[]},getNavState:()=>({object_id:selected}),frozenDetail:async(job)=>{root.children=[];notes.push({step,kind:'base_detail',job})},
  api:url=>url.startsWith('/local/workflow?')?Promise.resolve(workflow()):url.startsWith('/local/script-draft?')?request('get',decodeURIComponent(url.split('id=')[1])):Promise.reject(Error('ADAPTER_UNSUPPORTED_API '+url)),
  apiPost:(url,body)=>{if(url==='/local/select'){notes.push({step,kind:'selection_write',job:body.id});return Promise.resolve({});}if(url!=='/local/script-draft')throw Error('ADAPTER_UNSUPPORTED_API '+url);const e=probe();if(e&&body.revision!==e.revision)record('I3_NEXT_SAVE_REVISION','POST revision differs from active editor acknowledged revision');if(requests.some(r=>r.kind==='save'&&r.owner===editorToken()&&!r.ack))record('I2_SINGLE_IN_FLIGHT','concurrent save from one editor');return request('save',body.id,body)}
 };
 vm.createContext(ctx);vm.runInContext(code,ctx,{timeout:2000,filename:sourcePath});
 const tick=async()=>{for(let n=0;n<8;n++)await Promise.resolve()};
 const snap=e=>e?JSON.parse(e.snapshot):null;
 function risk(e,owner=editorToken()){if(!e)return false;const local=snap(e),base=JSON.parse(e.baseline);if(!same(local,base))return true;return requests.some(r=>r.kind==='save'&&r.owner===owner&&(!r.ack||r.committed&&!r.goodAck)&&!same(local,{voiceovers:r.immutable.voiceovers,screen_accents:r.immutable.screen_accents,description:r.immutable.description_text}));}
 function checkpoint(){const e=probe();if(e){const historical=server[e.id].history[e.revision];if(!historical||!same(JSON.parse(e.baseline),historical))record('I1_BASELINE_REVISION','baseline does not equal snapshot of its recorded server revision');}for(const r of requests)if(r.body&&!same(r.body,r.immutable))record('I0_IMMUTABLE_SUBMISSION','POST body changed after dispatch');}
 function advance(job,content){const s=server[job];s.counter++;s.content=content;s.revision=crypto.createHash('sha256').update(JSON.stringify({job,n:s.counter,content})).digest('hex');s.history[s.revision]=clone(s.content);}
 function commit(r){if(r.committed||r.conflict)return;const s=server[r.job];if(r.immutable.revision!==s.revision){r.conflict=true;return;}advance(r.job,{voiceovers:clone(r.immutable.voiceovers),screen_accents:clone(r.immutable.screen_accents),description:r.immutable.description_text});r.committed=true;r.receipt={revision:s.revision};}
 async function action(a,index){step=index;const [x,y,z]=a.args,before=probe(),beforeSnap=snap(before),beforeRender=render,beforeClosed=closed,beforePrompts=prompts.length,tokenBefore=editorToken();
  if(a.op==='open'){const n=requests.length;tasks[y]=ctx.editLocalScript(x).catch(e=>{notes.push({step,kind:'open_error',message:String(e)});if(!String(e).includes('Synthetic GET failure'))taskErrors.push(String(e.stack||e))});await tick();labels[y]=requests.slice(n).find(r=>r.kind==='get')||null;}
  else if(a.op==='get'){const r=labels[x];if(!r){notes.push({step,kind:'policy_skip',reason:'open refused/suppressed'});return;}if(r.ack)throw Error('SCHEDULER_ERROR GET already resolved');r.ack=true;if(y==='error')r.reject(Error('Synthetic GET failure'));else r.resolve(clone(r.captured));await tick();const e=probe();if(render>beforeRender&&e&&(e.id!==selected||r.navEpoch!==navEpoch))record('I6_NAVIGATION_FENCE','late GET rendered job '+e.id+' while selected '+selected);if(before&&render>beforeRender&&risk(before,tokenBefore)&&prompts.length===beforePrompts)record('I5_LOCAL_TEXT_PROTECTION','dirty/risky editor replaced without discard prompt');}
  else if(a.op==='edit'){const fields=$('#local-script-fields');if(!probe()||!fields){notes.push({step,kind:'policy_skip',reason:'no editor rendered yet'});return;}const selector=x==='voice'?'textarea[data-segment]':x==='accent'?'input[data-screen-accent]':'textarea[data-manual-description]';const n=fields.querySelectorAll(selector)[0];if(n.disabled||n.readOnly){notes.push({step,kind:'accepted_UX',reason:'editing disabled while request pending'});return;}const e=probe(),base=JSON.parse(e.baseline);n.value=y==='@baseline'?(x==='voice'?base.voiceovers[0]:x==='accent'?base.screen_accents[0]:base.description):`${x} ${y}`;}
  else if(a.op==='save'){const b=$('#local-script-save');if(!probe()||!b){notes.push({step,kind:'policy_skip',reason:'no active editor'});return;}const n=requests.length;if(!b.disabled||y===true)tasks[x]=Promise.resolve(b.onclick()).catch(e=>notes.push({step,kind:'handler_error',message:String(e)}));await tick();labels[x]=requests.slice(n).find(r=>r.kind==='save')||null;}

  else if(a.op==='check'){const b=$('#local-script-save'),n=requests.length;if(b&&!b.disabled)tasks[x]=Promise.resolve(b.onclick()).catch(e=>taskErrors.push(String(e)));await tick();const fresh=requests.slice(n);labels[x]=fresh.find(r=>r.kind==='get')||null;if(fresh.some(r=>r.kind==='save')||!labels[x])record('I10_READ_BEFORE_RETRY','uncertain check must issue GET only, no blind POST');}
  else if(a.op==='commit'){const r=labels[x];if(r)commit(r);}
  else if(a.op==='reply'){const r=labels[x];if(!r){notes.push({step,kind:'policy_skip',reason:'save suppressed or no active editor'});return;}if(r.ack)throw Error('SCHEDULER_ERROR SAVE already resolved');const e=probe(),local=snap(e),owner=editorToken(),msgBefore=$('#modalmsg')?.textContent||'';r.ack=true;
   if(y==='success'||y==='missing_revision'){commit(r);if(r.conflict)r.reject(Error('CONFLICT: Script draft changed; refresh before saving'));else {r.goodAck=y==='success';r.resolve(y==='missing_revision'?{}:clone(r.receipt));}}
   else if(y==='conflict'){if(server[r.job].revision===r.immutable.revision)advance(r.job,shot(r.job,server[r.job].counter+1));r.conflict=true;r.reject(Error('CONFLICT: Script draft changed; refresh before saving'));}
   else r.reject(Error(r.committed?'UNCERTAIN: transport failed after commit':'Synthetic write refusal; no commit'));
   await tick();const after=probe();
   const submitted={voiceovers:r.immutable.voiceovers,screen_accents:r.immutable.screen_accents,description:r.immutable.description_text};
   if(e&&r.owner===owner){if((!r.goodAck||!same(local,submitted))&&(!after||!same(snap(after),local)))record('I4_ACK_TEXT_OWNERSHIP','response discarded local text not acknowledged by this request');if(!r.goodAck&&after&&(after.revision!==e.revision||after.baseline!==e.baseline))record('I7_ERROR_NOT_SAVED','error/conflict advanced acknowledged baseline');if(r.goodAck&&after&&(after.revision!==r.receipt.revision||!same(JSON.parse(after.baseline),submitted)))record('I9_CURRENT_ACK_COMPLETENESS','successful current acknowledgement not represented by editor baseline/revision');}
   else if(e&&(!after||!same(snap(after),local)||closed!==beforeClosed||($('#modalmsg')?.textContent||'')!==msgBefore))record('I4_ACK_TEXT_OWNERSHIP','old-editor response changed newer editor');
  }
  else if(a.op==='nav'){selected=x;navEpoch++;await ctx.detail(x,true);}
  else if(a.op==='consent')allow=x;
  else if(a.op==='external')advance(x,shot(x,server[x].counter+1));
  else if(a.op==='unload'){const needed=risk(before),event={preventDefault(){this.prevented=true}};listeners.beforeunload?.(event);if(needed&&!event.prevented&&event.returnValue===undefined)record('I8_PENDING_WARNING','loss-risk state did not request beforeunload warning');}
  else if(a.op==='close'){allow=x;const needed=risk(before),b=$('#modalclose');if(b?.onclick)await b.onclick();await tick();const after=probe();if(needed&&(!after||closed>beforeClosed)&&prompts.length===beforePrompts)record('I8_PENDING_WARNING','risky close completed without discard decision');if(needed&&!allow&&(!after||!same(snap(after),beforeSnap)))record('I5_LOCAL_TEXT_PROTECTION','declined close lost local editor');}
  else throw Error('SCHEDULER_ERROR unknown action '+a.op);
  await tick();checkpoint();trace.push({step,action:a,selected,editor:probe(),render,closed,prompts:prompts.slice(beforePrompts),requests:requests.map(r=>({kind:r.kind,job:r.job,owner:r.owner,ack:r.ack,committed:r.committed,conflict:Boolean(r.conflict),revision:r.immutable?.revision}))});
 }
 return {action,violations,trace,notes,requests,probe,taskErrors};
}
async function main(){fs.mkdirSync(out,{recursive:true});const results=[];const filter=opt('--filter');for(const scenario of scenarios){if(filter&&!new RegExp(filter).test(scenario.name))continue;const server={};for(const j of ['A','B']){const content=shot(j);server[j]={counter:0,revision:'absent',content,history:{absent:clone(content)}};}let h=host(server);const hosts=[h];let error=null;try{for(let n=0;n<scenario.steps.length;n++){if(scenario.steps[n].op==='restart'){h.trace.push({step:n,action:scenario.steps[n],intentionalCrash:true});h=host(server);hosts.push(h);}else await h.action(scenario.steps[n],n);}}catch(e){error=String(e.stack||e);}if(hosts.some(x=>x.taskErrors.length))error=hosts.flatMap(x=>x.taskErrors).join('\n');const result={name:scenario.name,knownBaseline:scenario.known,violations:hosts.flatMap(x=>x.violations),error,notes:hosts.flatMap(x=>x.notes),trace:hosts.flatMap(x=>x.trace),unresolvedRequests:hosts.flatMap(x=>x.requests).filter(r=>!r.ack).map(r=>({kind:r.kind,job:r.job})),server};results.push(result);fs.writeFileSync(path.join(out,scenario.name+'.json'),JSON.stringify(result,null,2));}
 const summary={source:sourcePath,sourceSHA256:crypto.createHash('sha256').update(full).digest('hex'),memoryOnlyCalibrationMutant:mutant||null,node:process.version,scenarios:results.length,violatingScenarios:results.filter(r=>r.violations.length).length,scenarioErrors:results.filter(r=>r.error).map(r=>({name:r.name,error:r.error})),invariants:Object.fromEntries(['I0_IMMUTABLE_SUBMISSION','I1_BASELINE_REVISION','I2_SINGLE_IN_FLIGHT','I3_NEXT_SAVE_REVISION','I4_ACK_TEXT_OWNERSHIP','I5_LOCAL_TEXT_PROTECTION','I6_NAVIGATION_FENCE','I7_ERROR_NOT_SAVED','I8_PENDING_WARNING','I9_CURRENT_ACK_COMPLETENESS','I10_READ_BEFORE_RETRY'].map(k=>[k,results.flatMap(r=>r.violations).filter(v=>v.invariant===k).length])),failures:results.filter(r=>r.error||r.violations.length).map(r=>({name:r.name,knownBaseline:r.knownBaseline,invariants:[...new Set(r.violations.map(v=>v.invariant))],error:r.error})),scope:{mockServer:true,actualEditorHandlers:true,actualDetailHandler:true,fullAppNavigation:false,visualProof:false,physicalDiskDurability:false,models:0,network:0},matrix:'Explicit bounded families; no claim of exhaustive interleavings'};fs.writeFileSync(path.join(out,'SUMMARY.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));if(summary.scenarioErrors.length)process.exitCode=3;else if(summary.violatingScenarios&&!args.includes('--baseline'))process.exitCode=2;}
main().catch(e=>{console.error(e);process.exitCode=3});

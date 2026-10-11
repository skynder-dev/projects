'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync(require('node:path').join(__dirname,'..','GoDog_PC_LOCAL_01.user.js'),'utf8');
for(const required of [
  '// @name         GoDog GDCONST-010 DEFAULT-DISABLED canary',
  '// @namespace    GoDog.constitution',
  '// @version      7.0.3',
  '// @grant        none',
  '// @updateURL    http://127.0.0.1:43129/godog.meta.js',
  '// @downloadURL  http://127.0.0.1:43129/godog.user.js'
]) assert.ok(src.includes(required),'missing metadata '+required);
assert.ok(!src.includes('supabase.co'),'Supabase URL must not exist');
assert.ok(!src.includes('raw.githubusercontent.com'),'no GitHub client updates');
assert.ok(!/\bset(?:Interval|Timeout)\s*\(/.test(src),'No wait timers');
assert.ok(!/\b(?:fetch|XMLHttpRequest|GM_xmlhttpRequest)\s*\(/.test(src),'No network APIs');
new vm.Script(src,{filename:'GoDog_PC_LOCAL_01.user.js'});

class Element {
  constructor(name='DIV') {this.tagName=name;this.listeners={};this.dataset={};this.value=undefined;this.innerText='';this.textContent='';this.isConnected=false;this.disabled=false;this.attributes={};this.classList={toggle(){}};}
  removeAttribute(name) {delete this.attributes[name];}
  getAttribute(name) {return this.attributes[name]??null;}
  addEventListener(name,fn) {this.listeners[name]=fn;}
  focus() {}
  closest() {return null;}
  click() {this.listeners.click?.({ctrlKey:false});}
  querySelector() {return null;}
  appendChild(el) {el.isConnected=true;}
  replaceChildren() {}
  dispatchEvent() {return true;}
}
const buttons={
  '.cg-go':new Element('BUTTON'),
  '.cg-auto':new Element('BUTTON'),
  '.cg-new':new Element('BUTTON'),
  '.cg-stop':new Element('BUTTON'),
  '.cg-version':new Element('SPAN'),
  '.cg-project':new Element('SPAN'),
  '.cg-timer':new Element('SPAN'),
  '.cg-status':new Element('SPAN'),
  '.cg-update-dismiss':new Element('BUTTON'),
  '.cg-update-version':new Element('SPAN'),
  '.cg-update-time':new Element('SPAN')
};
const root=new Element('DIV');
root.querySelector=key=>buttons[key]??null;
const editor=new Element('DIV'); editor.attributes['aria-disabled']='false';
const send=new Element('BUTTON');
let submitted=[],stopNativeClicked=0,generating=false,observerCb=null,navCount=0;
let assistantMessages=[],userMessages=[];
send.click=()=>{
  submitted.push(editor.innerText);
  userMessages.push(Object.assign(new Element(),{innerText:editor.innerText,attributes:{'data-message-id':'U'+userMessages.length}}));
  editor.innerText='';
};
const nativeStop=new Element('BUTTON');nativeStop.click=()=>stopNativeClicked++;
const local=new Map(),session=new Map();
const storage=(map)=>({getItem(k){return map.get(k)??null;},setItem(k,v){map.set(k,String(v));},removeItem(k){map.delete(k);}});
const loc={href:'https://chatgpt.com/c/1234abcd-abcd-1234-abcd-1234abcdabcd', pathname:'/c/1234abcd-abcd-1234-abcd-1234abcdabcd',
  assign(url){navCount++;this.href=url;this.pathname='/';assistantMessages=[];userMessages=[];}};
const document={
  title:'GoDog test project',
  documentElement:new Element('HTML'),body:new Element('BODY'),
  getElementById(){return null;},
  createElement(tag){return tag==='div' ? root : new Element(tag.toUpperCase());},
  createRange(){return {selectNodeContents(){}};},
  execCommand(cmd,mode,data){assert.equal(cmd,'insertText');editor.innerText=data;return true;},
  querySelector(selector) {
    if(selector==='#prompt-textarea')return editor;
    if(selector.includes('send-button'))return send;
    if(selector.includes('stop-button'))return generating?nativeStop:null;
    return null;
  },
  querySelectorAll(selector) {
    if(selector.includes('data-message-author-role="assistant"'))return assistantMessages;
    if(selector.includes('data-message-author-role="user"'))return userMessages;
    return [];
  },
  addEventListener(){}
};
const win={};win.top=win;win.self=win;win.getSelection=()=>({removeAllRanges(){},addRange(){}});
const ctx={window:win,document,location:loc,sessionStorage:storage(session),localStorage:storage(local),
  queueMicrotask,MutationObserver:class{constructor(fn){observerCb=fn;}observe(){}},
  Event:class{},InputEvent:class{},KeyboardEvent:class{},console,
  HTMLTextAreaElement:class{},HTMLInputElement:class{}};
vm.runInNewContext(src,ctx,{timeout:3000});
assert.equal(buttons['.cg-status'].textContent,'PC LOCAL','script mounted');

// Direct GO is fully synchronous, one native click, zero waits.
buttons['.cg-go'].click();
assert.deepEqual(submitted,['GO']);
// STOP does not click native stop.
buttons['.cg-stop'].click();
assert.equal(stopNativeClicked,0);

// AUTO on idle dispatches once NOW, then once only after a finished assistant turn.
buttons['.cg-auto'].click();
assert.deepEqual(submitted,['GO','GO']);
generating=true;observerCb();
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await flush();
  assert.deepEqual(submitted,['GO','GO'],'must not send while generating');
  generating=false;
  assistantMessages.push(Object.assign(new Element(),{innerText:'Step completed',attributes:{'data-message-id':'A1'}}));
  observerCb();
  await flush();
  assert.deepEqual(submitted,['GO','GO','GO'],'one AUTO next turn');
  observerCb(); await flush();
  assert.deepEqual(submitted,['GO','GO','GO'],'same assistant turn must not resend');
  buttons['.cg-stop'].click();
  assistantMessages.push(Object.assign(new Element(),{innerText:'Second step',attributes:{'data-message-id':'A2'}}));
  observerCb(); await flush();
  assert.deepEqual(submitted,['GO','GO','GO'],'STOP must prevent next GO');
  assert.equal(stopNativeClicked,0,'STOP does not interrupt native ChatGPT');
  // NEW should navigate same tab immediately and send handoff exactly once upon fresh composer.
  buttons['.cg-new'].click();
  assert.equal(navCount,1,'NEW navigates in same tab');
  assert.equal(loc.href,'https://chatgpt.com/');
  assert.ok(session.has('godog-pc-local-v7-handoff'),'NEW snapshot local');
  observerCb(); await flush();
  assert.equal(submitted.length,4);
  assert.ok(submitted[3].startsWith('[GODOG LOCAL NEW / CONTINUE]'));
  assert.ok(!session.has('godog-pc-local-v7-handoff'),'handoff consumed once');
  observerCb(); await flush();
  assert.equal(submitted.length,4,'no duplicate handoff');
  console.log('GoDog PC LOCAL: direct GO, AUTO one-per-turn, STOP, NEW handoff, no timers/network: PASS');
})().catch(err=>{console.error(err);process.exitCode=1;});

'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync(require('node:path').join(__dirname,'..','GoDog_PC_LOCAL_01.user.js'),'utf8');
for(const required of [
  '// @name         GoDog GDCONST-010 DEFAULT-DISABLED canary',
  '// @name:en      GoDog',
  '// @name:ru      GoDog',
  '// @namespace    GoDog.constitution',
  '// @version      7.0.9',
  '// @grant        none',
  '// @updateURL    http://127.0.0.1:43129/godog.meta.js',
  '// @downloadURL  http://127.0.0.1:43129/godog.user.js'
]) assert.ok(src.includes(required),'missing metadata '+required);
assert.ok(!src.includes('supabase.co'),'Supabase URL must not exist');
assert.ok(!src.includes('raw.githubusercontent.com'),'no GitHub client updates');
assert.ok(!/\bset(?:Interval|Timeout)\s*\(/.test(src),'No wait timers');
assert.ok(!/\b(?:fetch|XMLHttpRequest|GM_xmlhttpRequest)\s*\(/.test(src),'No network APIs');
new vm.Script(src,{filename:'GoDog_PC_LOCAL_01.user.js'});
// This exact canonical name is required by the PC localhost updater and keeps
// Tampermonkey's existing installed script identity. Localized name is clean.
assert.match(src,/^\/\/ @name\s+GoDog GDCONST-010 DEFAULT-DISABLED canary$/m);
assert.match(src,/^\/\/ @name:en\s+GoDog$/m);
assert.ok(src.includes('function mountDogUnderComposer('),'frozen visual underlay glue required');
assert.ok(src.includes('button[aria-label="Stop"]'),'native Stop generating guard required');

class Element {
  constructor(name='DIV') {this.tagName=name;this.listeners={};this.dataset={};this.value=undefined;this.innerText='';this.textContent='';this.isConnected=false;this.disabled=false;this.attributes={};this.classList={toggle(){}};this.style={props:{},setProperty(n,v){this.props[n]=v;},removeProperty(n){delete this.props[n];},getPropertyValue(n){return this.props[n]||'';},getPropertyPriority(){return '';}};this.childNodes=[];this.parentElement=null;this.firstChild=null;this.rect={left:0,right:1200,top:0,bottom:36,width:1200,height:36};}
  removeAttribute(name) {delete this.attributes[name];}
  getAttribute(name) {return this.attributes[name]??null;}
  setAttribute(name,value) {this.attributes[name]=String(value);}
  getBoundingClientRect(){return this.rect;}
  addEventListener(name,fn) {this.listeners[name]=fn;}
  focus() {}
  closest() {return null;}
  click() {this.listeners.click?.({ctrlKey:false});}
  querySelector() {return null;}
  appendChild(el) {el.isConnected=true;el.parentElement=this;this.childNodes.push(el);this.firstChild=this.childNodes[0];return el;}
  insertBefore(el,next){el.isConnected=true;el.parentElement=this;this.childNodes.unshift(el);this.firstChild=this.childNodes[0];return el;}
  remove(){this.isConnected=false;if(this.parentElement){this.parentElement.childNodes=this.parentElement.childNodes.filter(x=>x!==this);this.parentElement=null;}}

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
const visualNodes=[];
let createdDivs=0;
const editor=new Element('DIV'); editor.attributes['aria-disabled']='false';
const composerSurface=new Element('DIV');
const composerParent=new Element('DIV');composerParent.isConnected=true;
composerParent.appendChild(composerSurface);
composerSurface.rect={left:130,right:1090,top:69,bottom:161,width:960,height:92};
editor.isConnected=true;
const submitForm=new Element('FORM');
submitForm.requestSubmit=()=>send.click();
editor.closest=selector=>selector==='[data-type="unified-composer"]' ? composerSurface : selector==='form' ? submitForm : null;

const send=new Element('BUTTON');
send.disabled=true; // React leaves native Send disabled until it accepts editor input.
send.rect={left:1030,right:1070,top:117,bottom:157,width:40,height:40};
let submitted=[],stopNativeClicked=0,generating=false,observerCb=null,navCount=0;
let assistantMessages=[],userMessages=[],findSend=true;
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
  createElement(tag){if(tag==='div'&&createdDivs++===0)return root;const el=new Element(tag.toUpperCase());visualNodes.push(el);return el;},
  createRange(){return {selectNodeContents(){}};},
  execCommand(cmd,mode,data){assert.equal(cmd,'insertText');editor.innerText=data;return true;},
  querySelector(selector) {
    if(selector==='#prompt-textarea')return editor;
    if(selector.includes('send-button'))return findSend?send:null;
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
const win={innerWidth:1220,innerHeight:250,addEventListener(){},getComputedStyle(el){return {position:'static',backgroundColor:'rgb(33, 33, 33)',borderTopLeftRadius:'26px',borderTopRightRadius:'26px',borderBottomLeftRadius:'26px',borderBottomRightRadius:'26px',borderLeftWidth:'1px',borderLeftColor:'rgba(255, 255, 255, 0.1)',borderRightWidth:'1px',borderRightColor:'rgba(255, 255, 255, 0.1)',borderBottomWidth:'1px',borderBottomColor:'rgba(255, 255, 255, 0.1)',borderTopWidth:'1px',borderTopColor:'rgba(255, 255, 255, 0.1)'}}};win.top=win;win.self=win;win.getSelection=()=>({removeAllRanges(){},addRange(){}});win.requestAnimationFrame=fn=>queueMicrotask(()=>fn(16));
const ctx={window:win,document,location:loc,sessionStorage:storage(session),localStorage:storage(local),
  queueMicrotask,MutationObserver:class{constructor(fn){observerCb=fn;}observe(){}},
  Event:class{},InputEvent:class{},KeyboardEvent:class{},console,
  HTMLTextAreaElement:class{},HTMLInputElement:class{}};
vm.runInNewContext(src,ctx,{timeout:3000});
assert.equal(buttons['.cg-status'].textContent,'DISARMED','restored original initial status');
assert.equal(buttons['.cg-version'].textContent,'GoDog 7.0.9','restored original version chip');
assert.equal(buttons['.cg-project'].textContent,'GoDog','restored original project chip');
assert.equal(buttons['.cg-auto'].textContent,'AUTO','restored original AUTO label');
assert.equal(buttons['.cg-timer'].textContent,'','no fake LOCAL timer');


// Native Send starts DISABLED, just like React's real input re-render.
buttons['.cg-go'].click();
assert.equal(editor.innerText,'GO','GO typed into native editor');
assert.deepEqual(submitted,[],'must NOT claim synthetic Enter sent the message');
assert.equal(buttons['.cg-status'].textContent,'GO → INPUT','no false CLICK before native submission');
buttons['.cg-go'].click(); // second GO before React commit must NOT duplicate
assert.deepEqual(submitted,[],'pending single-flight GO, no double send');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await flush();
  assert.deepEqual(submitted,[],'native button still disabled');
  // Actual React state commit: enable native Send and notify the observer.
  send.disabled=false;
  observerCb();
  await flush();
  assert.deepEqual(submitted,['GO'],'after React enables native Send, exactly one click');
  observerCb(); await flush();
  assert.deepEqual(submitted,['GO'],'repeated DOM updates must not duplicate a submitted GO');

  // STOP never clicks the native ChatGPT stop.
  buttons['.cg-stop'].click();
  assert.equal(stopNativeClicked,0);

  // AUTO sends exactly one native GO when idle.
  buttons['.cg-auto'].click();
  await flush();
  assert.deepEqual(submitted,['GO','GO']);
  generating=true;observerCb();
  await flush();
  assert.equal(root.style.props.left,'130px','dock aligned to composer left');
assert.equal(root.style.props.width,'960px','dock width equals composer, never full viewport');
  assert.equal(root.style.props.right,'auto','dock width explicitly constrained');
  assert.equal(root.style.props['max-width'],'calc(100vw - 16px)','failsafe prevents viewport-wide bar');
assert.ok(Math.abs(Number.parseInt(root.style.props.top,10)-160)<=2,'dock directly under composer');
assert.equal(root.style.props.bottom,'auto','dock not full-width bottom bar');
  assert.ok(src.includes("transform: translateY(2px) !important"),"preserve frozen 2px dock offset");
  assert.ok(src.includes("background: linear-gradient(to bottom, transparent 0 5px"),"preserve frozen top transparent seam");
  const underlay=visualNodes.find(e=>e.id==='chatgpt-go-watchdog-underlay');
  assert.ok(underlay,'original composer underlay restored');
  assert.equal(underlay.parentElement,composerParent,'underlay belongs UNDER composer host, not above it');
  assert.equal(underlay.style.props.background,'rgb(33, 33, 33)','composer color carried through to dock');
  assert.equal(underlay.style.props.display,'block','underlay visible');
  assert.equal(root.style.props['--cg-unified-surface'],'rgb(33, 33, 33)','root backdrop inherits composer color');
  assert.ok(visualNodes.some(e=>e.className?.includes('cg-composer-seam-cap')),'frozen seam caps restored');
  assert.ok(visualNodes.some(e=>e.className==='cg-fixed-side-bridge'),'frozen side bridges restored');
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
  // If ChatGPT changes the Send button markup, use its real form requestSubmit.
  findSend=false;
  buttons['.cg-go'].click();
  await flush();
  assert.deepEqual(submitted.length,5,'native requestSubmit fallback sends GO exactly once');
  assert.equal(submitted[4],'GO');
  observerCb();await flush();
  assert.equal(submitted.length,5,'requestSubmit must never double send');

  // Version 7.0.8 falsely reported GO CLICK after a synthetic keyboard event.
  assert.ok(!src.includes("new KeyboardEvent('keydown'"),'untrusted Enter is not a valid submit proof');
  console.log('GoDog PC LOCAL 7.0.9: disabled React Send → enabled native click, requestSubmit fallback, AUTO, STOP, NEW, frozen visual: PASS');
})().catch(err=>{console.error(err);process.exitCode=1;});

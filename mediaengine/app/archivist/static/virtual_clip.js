(() => {
  'use strict';
  const configNode = document.getElementById('clipConfig');
  if (!configNode) return;
  const cfg = JSON.parse(configNode.textContent);
  const START = Number(cfg.start), END = Number(cfg.end), LEN = Number(cfg.length);
  const SRC_RATIO = Number(cfg.sourceRatio), DEFAULT = cfg.defaultAspect, PLANS = cfg.plans || {};
  const SMART_CROP_V2 = Boolean(cfg.smartCropV2), TRAJECTORIES = cfg.trajectories || {};
  let NATURAL_RATIO = SRC_RATIO || 16 / 9, CURRENT = 'original', INITIALIZING = true, PUMPING = false, MANUAL_CROP = null;
  const CLIP_ID = Number(location.pathname.split('/').filter(Boolean).pop());
  const canvas = document.getElementById('clipCanvas'), ctx = canvas.getContext('2d');
  const v = document.getElementById('clipVideo'), vp = document.getElementById('cropViewport');
  const play = document.getElementById('playClip'), replay = document.getElementById('replayClip');
  const seek = document.getElementById('clipSeek'), seekWrap = document.getElementById('clipSeekWrap');
  const seekFill = document.getElementById('clipSeekFill'), seekThumb = document.getElementById('clipSeekThumb');
  const clock = document.getElementById('clipClock'), info = document.getElementById('cropInfo');
  const fmt = s => { s = Math.max(0, s); return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0'); };
  const activeTrajectory = () => SMART_CROP_V2 ? TRAJECTORIES[CURRENT] : null;
  const state = () => ({ready: v.readyState >= 2, aspect: CURRENT, currentTime: v.currentTime, relativeTime: Math.max(0, v.currentTime - START), start: START, end: END, paused: v.paused, smartCropV2: SMART_CROP_V2, trajectoryStatus: activeTrajectory() ? activeTrajectory().status : null, keyframeCount: activeTrajectory() ? (activeTrajectory().keyframes || []).length : 0, crop: normalizedCrop(), canvas: {width: canvas.width, height: canvas.height}});
  window.__ARCHIVIST_CLIP_DIAGNOSTICS__ = Object.freeze({version: 2, state});
  function syncSeekUI() { const p = Math.max(0, Math.min(1, Number(seek.value || 0) / 1000)), w = seekWrap.clientWidth || 0, tw = seekThumb.offsetWidth || 16; seekThumb.style.left = Math.round(p * Math.max(0, w - tw)) + 'px'; seekFill.style.width = (p * 100) + '%'; }
  function normalizedCrop() {
    if (CURRENT === 'original' || !PLANS[CURRENT]) return {x:0,y:0,w:1,h:1};
    if (MANUAL_CROP) return {...MANUAL_CROP};
    const trajectory = activeTrajectory(), keys = trajectory && Array.isArray(trajectory.keyframes) ? trajectory.keyframes : [];
    if (keys.length) {
      const t = Math.max(0, Math.min(LEN * 1000, (Number(v.currentTime) - START) * 1000));
      let a=keys[0], b=keys[keys.length-1];
      for(let i=0;i<keys.length-1;i++){if(t>=Number(keys[i].time_ms)&&t<=Number(keys[i+1].time_ms)){a=keys[i];b=keys[i+1];break}}
      const span=Math.max(1,Number(b.time_ms)-Number(a.time_ms));let q=Math.max(0,Math.min(1,(t-Number(a.time_ms))/span));q=q*q*(3-2*q);
      const mix=k=>Number(a[k])+(Number(b[k])-Number(a[k]))*q;
      return {x:mix('x'),y:mix('y'),w:mix('w'),h:mix('h')};
    }
    const p=PLANS[CURRENT]; return {x:Number(p.x)||0,y:Number(p.y)||0,w:Number(p.w)||1,h:Number(p.h)||1};
  }
  function cropRect() { const vw = v.videoWidth || 1, vh = v.videoHeight || 1; const p=normalizedCrop(); const x = Math.max(0, Math.min(.99, p.x)), y = Math.max(0, Math.min(.99, p.y)); const cw = Math.max(.05, Math.min(1 - x, p.w)), ch = Math.max(.05, Math.min(1 - y, p.h)); return [x * vw, y * vh, cw * vw, ch * vh]; }
  function resizeCanvas() { const r = vp.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1); const cw = Math.max(2, Math.round(r.width * d)), ch = Math.max(2, Math.round(r.height * d)); if (canvas.width !== cw || canvas.height !== ch) { canvas.width = cw; canvas.height = ch; } }
  function drawFrame() { if (v.readyState < 2 || !v.videoWidth || !v.videoHeight) return; resizeCanvas(); const q = cropRect(); try { ctx.drawImage(v, q[0], q[1], q[2], q[3], 0, 0, canvas.width, canvas.height); vp.style.backgroundImage = 'none'; } catch (_) {} }
  function pump() { if (PUMPING) return; PUMPING = true; const tick = () => { drawFrame(); if (!v.paused && !v.ended) requestAnimationFrame(tick); else PUMPING = false; }; requestAnimationFrame(tick); }
  function setAspect(a) { MANUAL_CROP=null; CURRENT = (a === 'original' || PLANS[a]) ? a : 'original'; document.querySelectorAll('.cropBtn').forEach(b => b.classList.toggle('ok', b.dataset.aspect === CURRENT)); if (CURRENT === 'original') { const nr = NATURAL_RATIO || 16 / 9; vp.style.aspectRatio = String(nr); vp.style.maxWidth = nr < 1 ? '460px' : '900px'; info.textContent = 'Original frame · no crop'; } else { const p = PLANS[CURRENT], parts = CURRENT.split(':').map(Number), ar = parts[0] / parts[1], trajectory=activeTrajectory(); vp.style.aspectRatio = String(ar); vp.style.maxWidth = ar < 1 ? '460px' : '900px'; info.textContent = (trajectory ? 'Smart Crop v2 ' + CURRENT + ' · ' + trajectory.status + ' · ' + (trajectory.keyframes||[]).length + ' keyframes' : 'Smart Crop ' + CURRENT + ' · ' + p.preset + ' · confidence ' + Math.round((p.confidence || 0) * 100) + '%'); } requestAnimationFrame(() => { resizeCanvas(); drawFrame(); }); }
  document.querySelectorAll('.cropBtn').forEach(b => b.onclick = () => setAspect(b.dataset.aspect));
  v.addEventListener('loadedmetadata', () => { v.pause(); if (v.videoWidth > 0 && v.videoHeight > 0) NATURAL_RATIO = v.videoWidth / v.videoHeight; seek.value = '0'; syncSeekUI(); clock.textContent = '0:00 / ' + fmt(LEN); play.textContent = 'Play'; INITIALIZING = true; const aspects = ['16:9', '4:5', '1:1', '9:16'].filter(a => PLANS[a]); const closest = aspects.length ? aspects.reduce((best, a) => { const q = a.split(':').map(Number), r = q[0] / q[1], b = best.split(':').map(Number), br = b[0] / b[1]; return Math.abs(r - NATURAL_RATIO) < Math.abs(br - NATURAL_RATIO) ? a : best; }, aspects[0]) : 'original'; setAspect(closest || DEFAULT || 'original'); try { v.currentTime = START; } catch (_) {} });
  v.addEventListener('seeked', () => { if (INITIALIZING) { INITIALIZING = false; seek.value = '0'; syncSeekUI(); clock.textContent = '0:00 / ' + fmt(LEN); } drawFrame(); });
  play.onclick = () => { if (v.currentTime < START - .02 || v.currentTime >= END - .03) { INITIALIZING = true; seek.value = '0'; syncSeekUI(); clock.textContent = '0:00 / ' + fmt(LEN); v.currentTime = START; } if (v.paused) { v.play().then(pump).catch(() => {}); play.textContent = 'Pause'; } else { v.pause(); play.textContent = 'Play'; drawFrame(); } };
  replay.onclick = () => { v.pause(); INITIALIZING = true; seek.value = '0'; syncSeekUI(); clock.textContent = '0:00 / ' + fmt(LEN); v.currentTime = START; v.play().then(pump).catch(() => {}); play.textContent = 'Pause'; };
  seek.oninput = () => { INITIALIZING = false; syncSeekUI(); const rel = (Number(seek.value) / 1000) * LEN; clock.textContent = fmt(rel) + ' / ' + fmt(LEN); v.currentTime = START + rel; };
  v.addEventListener('timeupdate', () => { if (INITIALIZING) return; if (v.currentTime < START - .05) { INITIALIZING = true; v.currentTime = START; return; } if (v.currentTime >= END - .015) { v.pause(); seek.value = '1000'; syncSeekUI(); clock.textContent = fmt(LEN) + ' / ' + fmt(LEN); play.textContent = 'Play'; drawFrame(); return; } const rel = Math.max(0, Math.min(LEN, v.currentTime - START)); seek.value = String(Math.round(1000 * rel / LEN)); syncSeekUI(); clock.textContent = fmt(rel) + ' / ' + fmt(LEN); });
  v.addEventListener('loadeddata', drawFrame); v.addEventListener('canplay', drawFrame); v.addEventListener('pause', () => { play.textContent = 'Play'; drawFrame(); }); v.addEventListener('play', () => { play.textContent = 'Pause'; pump(); });
  window.addEventListener('resize', () => requestAnimationFrame(() => { resizeCanvas(); syncSeekUI(); drawFrame(); }));
  const editorMessage=document.getElementById('editorMessage');
  const editorSay=t=>{if(editorMessage)editorMessage.textContent=t;};
  const requireFormat=()=>{if(CURRENT==='original'||!PLANS[CURRENT]){editorSay('Choose 16:9, 4:5, 1:1 or 9:16 first.');return false}return true};
  const clampCrop=p=>{p.w=Math.max(.05,Math.min(1,p.w));p.h=Math.max(.05,Math.min(1,p.h));p.x=Math.max(0,Math.min(1-p.w,p.x));p.y=Math.max(0,Math.min(1-p.h,p.y));return p};
  const beginManual=()=>{if(!requireFormat())return null;if(!MANUAL_CROP)MANUAL_CROP=clampCrop({...normalizedCrop()});return MANUAL_CROP};
  document.querySelectorAll('.cropNudge').forEach(b=>b.onclick=()=>{const p=beginManual();if(!p)return;p.x+=Number(b.dataset.dx||0);p.y+=Number(b.dataset.dy||0);clampCrop(p);drawFrame();editorSay('Adjusted '+CURRENT+' at '+fmt(Math.max(0,v.currentTime-START))+'. Lock the keyframe to save.');});
  const zoom=scale=>{const p=beginManual();if(!p)return;const cx=p.x+p.w/2,cy=p.y+p.h/2;p.w*=scale;p.h*=scale;p.x=cx-p.w/2;p.y=cy-p.h/2;clampCrop(p);drawFrame();editorSay('Zoom adjusted. Lock the keyframe to save.');};
  const zin=document.getElementById('cropZoomIn'),zout=document.getElementById('cropZoomOut');if(zin)zin.onclick=()=>zoom(.94);if(zout)zout.onclick=()=>zoom(1.06);
  const build=document.getElementById('buildTrajectory');if(build)build.onclick=async()=>{if(!requireFormat())return;build.disabled=true;editorSay('Building tracked '+CURRENT+' path from real frames…');try{const r=await fetch('/api/clip/'+CLIP_ID+'/track/'+encodeURIComponent(CURRENT),{method:'POST'}),x=await r.json();if(!r.ok)throw new Error(x.error||r.statusText);TRAJECTORIES[CURRENT]=x.trajectory;MANUAL_CROP=null;setAspect(CURRENT);editorSay('Tracked path built: '+(x.trajectory.keyframes||[]).length+' keyframes · draft.');}catch(e){editorSay('ERROR: '+e.message)}finally{build.disabled=false}};
  const save=document.getElementById('saveKeyframe');if(save)save.onclick=async()=>{if(!requireFormat())return;const trajectory=activeTrajectory();if(!trajectory){editorSay('Build a tracked path first.');return}const crop=beginManual()||normalizedCrop(),time=Math.max(0,Math.min(Math.round(LEN*1000),Math.round((v.currentTime-START)*1000))),map=new Map((trajectory.keyframes||[]).map(k=>[Number(k.time_ms),{...k}]));map.set(time,{time_ms:time,x:crop.x,y:crop.y,w:crop.w,h:crop.h,confidence:1,locked:1});const keys=[...map.values()].sort((a,b)=>a.time_ms-b.time_ms);save.disabled=true;try{const r=await fetch('/api/clip/'+CLIP_ID+'/trajectory/'+encodeURIComponent(CURRENT),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyframes:keys,preset:trajectory.preset||PLANS[CURRENT].preset,status:'draft',confidence:trajectory.confidence||0,smoothing:trajectory.smoothing||.35,max_pan_per_second:trajectory.max_pan_per_second||.22,max_zoom_per_second:trajectory.max_zoom_per_second||.12})}),x=await r.json();if(!r.ok)throw new Error(x.error||r.statusText);TRAJECTORIES[CURRENT]=x.trajectory;MANUAL_CROP=null;setAspect(CURRENT);editorSay('Locked keyframe saved at '+fmt(time/1000)+' · draft.');}catch(e){editorSay('ERROR: '+e.message)}finally{save.disabled=false}};
  document.querySelectorAll('.trajectoryStatus').forEach(b=>b.onclick=async()=>{if(!requireFormat())return;if(!activeTrajectory()){editorSay('Build or save a trajectory first.');return}const status=b.dataset.status;b.disabled=true;try{const r=await fetch('/api/clip/'+CLIP_ID+'/trajectory-status/'+encodeURIComponent(CURRENT),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})}),x=await r.json();if(!r.ok)throw new Error(x.error||r.statusText);TRAJECTORIES[CURRENT]=x.trajectory;setAspect(CURRENT);editorSay('Trajectory marked '+status+'.');}catch(e){editorSay('ERROR: '+e.message)}finally{b.disabled=false}});
})();

from __future__ import annotations
from .connectors import connector_catalog as m12_connector_catalog, connector_summary as m12_connector_summary, create_manual_handoff_for_composition
from .experiments import experiment_metric_summaries as get_experiment_metric_summaries, validate_results_csv as validate_experiment_results_csv, import_results_csv as import_experiment_results_csv
from .experiments import ensure_schema as ensure_experiment_schema, create_experiment as create_social_experiment, add_variant as add_social_variant, record_result as record_social_result, list_experiments as list_social_experiments, experiment_detail as get_social_experiment, experiment_stats
from .social_lab import enqueue_composition as enqueue_social_composition, list_queue as list_social_queue, set_queue_state as set_social_queue_state
from .social_lab import ensure_schema as ensure_social_schema, publication_stats, list_publications, recent_rendered_compositions, candidate_from_composition, evaluate_composition as evaluate_social_composition, record_composition as record_social_composition

import html, json, os, re, subprocess, threading, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, send_file

from . import android
from .config import APP_PORT, HOME, PRIVATE, REJECTED, STAGING, STORYBOARDS, THUMBS, VERSION, load_config, save_config
from .db import db, init_db
from .media_brain import (best_clips, build_tracked_trajectory, clip_by_id, clips_for_inventory,
                          ensure_schema as ensure_media_brain_schema, save_crop_trajectory,
                          trajectories_for_clip, trajectory_for_clip)
from .service import (STATE, cached_storyboard, cached_thumbnail, cancel_job, job_detail, latest_jobs, queue_job,
                      queue_storyboard, queue_thumbnail, remove_from_library, retry_failed, set_excluded, set_rights, set_rights_custom, start_discovery, storyboard_info, windows_drives)
from .converter import PRESETS as CONVERT_PRESETS, convert_job_snapshot, start_convert_job, probe_local_media_meta
from .semantic_search import search_library as semantic_search, capabilities as semantic_capabilities
from .visual_similarity import find_similar
from .clip_export import EXPORTS, export_by_id, export_clip
from .composer import EXPORTS as COMPOSER_EXPORTS, composition_detail, create_composition, ensure_schema as ensure_composer_schema, move_item as move_composer_item, start_render as start_composer_render
from .product_foundation import platform_snapshot, setup_catalog
from .beta_readiness import welcome_body, help_body, guide_body, connection_disclosure_html
from .platform_adapter import spawn_app_launcher
from .auto_edit_web import register as register_auto_edit


def e(v): return html.escape(str(v if v is not None else ""), quote=True)

def human_bytes(n):
    try: n=float(n)
    except Exception: return "—"
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB": return f"{n:.0f} {u}" if u in ("B","KB") else f"{n:.1f} {u}"
        n/=1024

def human_duration(ms):
    try: sec=int(ms)//1000
    except Exception: return "—"
    h,r=divmod(sec,3600); m,s=divmod(r,60); return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def _job_elapsed(j):
    try:
        start = j.get('started_at') or j.get('created_at')
        if not start:
            return ''
        a = datetime.fromisoformat(str(start).replace('Z','+00:00'))
        if a.tzinfo is None:
            a = a.replace(tzinfo=timezone.utc)
        end = j.get('finished_at')
        b = datetime.fromisoformat(str(end).replace('Z','+00:00')) if end else datetime.now(timezone.utc)
        if b.tzinfo is None:
            b = b.replace(tzinfo=timezone.utc)
        sec = max(0, int((b-a).total_seconds()))
        if sec < 60:
            return f"{sec}s"
        m,s = divmod(sec,60)
        if m < 60:
            return f"{m}m {s}s"
        h,m = divmod(m,60)
        return f"{h}h {m}m"
    except Exception:
        return ''



CSS=r'''
:root{color-scheme:dark;--bg:#090d12;--bg2:#0f151d;--card:#151b24;--card2:#1b232e;--line:#293442;--line2:#3a4758;--text:#f5f7fb;--muted:#94a1b2;--blue:#6d96ff;--blue2:#5177df;--green:#53c983;--orange:#d7a34a;--red:#d46b74;--violet:#a78bfa;--cyan:#67d7e8;--rose:#e78caf;--shadow:0 14px 40px #00000026}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(920px 520px at 8% -100px,#6d96ff20,transparent 62%),radial-gradient(760px 430px at 84% -80px,#a78bfa16,transparent 62%),radial-gradient(780px 520px at 55% 115%,#53c9830c,transparent 65%),linear-gradient(180deg,var(--bg2),var(--bg) 340px);color:var(--text);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit;text-decoration:none}nav{position:sticky;top:0;z-index:30;background:#0d1219df;border-bottom:1px solid #364253aa;backdrop-filter:blur(18px) saturate(120%)}.navin{max-width:1540px;margin:auto;padding:11px 20px;display:flex;align-items:center;gap:7px}.brand{font-weight:900;font-size:20px;letter-spacing:-.35px;margin-right:8px}.brand:before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;background:linear-gradient(135deg,var(--blue),var(--violet));box-shadow:0 0 18px #6d96ff88}.version{font-size:10px;background:#7b8aa81a;border:1px solid #8ea2c02d;padding:2px 6px;border-radius:999px;vertical-align:2px;color:#cbd6e7}.navlink{color:#bdc7d4!important;padding:8px 10px;border-radius:10px;white-space:nowrap;transition:.12s}.navlink:hover{background:#8aa1c314;color:#fff!important}.navlink.active{background:linear-gradient(135deg,#6d96ff20,#a78bfa18);border:1px solid #849cff28;color:#fff!important}.spacer{flex:1}.wrap{max-width:1540px;margin:auto;padding:24px 20px 42px}.card{background:linear-gradient(180deg,#1a202aee,#141a22ef);border:1px solid #344151c9;border-radius:15px;padding:15px;box-shadow:var(--shadow);backdrop-filter:blur(10px)}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.space{justify-content:space-between}.muted{color:var(--muted)}.eyebrow{color:#a9c1ff;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.lead{font-size:16px;color:#b8c2cf;max-width:780px;margin-top:5px}.pagehead{margin-bottom:16px}.pagehead h1{font-size:31px;letter-spacing:-.6px;margin:2px 0 0}.device{display:flex;gap:10px;align-items:center}.device-dot{width:10px;height:10px;border-radius:50%;background:#687383;box-shadow:0 0 0 4px #6873831c;flex:0 0 auto}.device-dot.online{background:#3dcc72;box-shadow:0 0 0 4px #3dcc7221,0 0 14px #3dcc7255}.device-status{font-weight:750}.source-card{display:flex;align-items:center;justify-content:space-between;gap:18px}.section-title{font-size:18px;margin:24px 0 10px}.callout{border:1px solid #6d96ff38;background:linear-gradient(135deg,#6d96ff15,#a78bfa0e 55%,#53c9830a)}button,.btn{border:1px solid #96adff22;border-radius:10px;padding:9px 13px;background:linear-gradient(180deg,#7099ff,#5278df);color:#fff;font-weight:780;cursor:pointer;box-shadow:0 6px 18px #264b9930}button:hover,.btn:hover{filter:brightness(1.07)}.btn2{background:#91a2bd14;border-color:#91a2bd25}.ok{background:linear-gradient(180deg,#58c987,#3aa86a);border-color:#8ee1aa28}.warn{background:linear-gradient(180deg,#d5a54e,#ae7b27);border-color:#f1c16e25}.danger{background:linear-gradient(180deg,#d66d77,#b44f5a);border-color:#ef9aa225}button:disabled{opacity:.5;cursor:not-allowed}input,select{background:#0e131a;color:#fff;border:1px solid #364150;border-radius:9px;padding:8px 9px;outline:none}input:focus,select:focus{border-color:#5b86d8;box-shadow:0 0 0 3px #4a82f420}.hero{display:grid;grid-template-columns:repeat(6,minmax(140px,1fr));gap:11px;margin:16px 0}.metric{min-height:96px;position:relative;overflow:hidden}.metric:after{content:'';position:absolute;width:100px;height:100px;border-radius:50%;right:-36px;top:-42px;filter:blur(1px);opacity:.42}.tone-blue{border-color:#6d96ff30;background:linear-gradient(145deg,#6d96ff12,#151b24 60%)}.tone-blue:after{background:#6d96ff28}.tone-mint{border-color:#53c9832d;background:linear-gradient(145deg,#53c98310,#151b24 60%)}.tone-mint:after{background:#53c98325}.tone-violet{border-color:#a78bfa2f;background:linear-gradient(145deg,#a78bfa12,#151b24 60%)}.tone-violet:after{background:#a78bfa26}.tone-amber{border-color:#d7a34a2f;background:linear-gradient(145deg,#d7a34a10,#151b24 60%)}.tone-amber:after{background:#d7a34a25}.tone-rose{border-color:#e78caf2f;background:linear-gradient(145deg,#e78caf10,#151b24 60%)}.tone-rose:after{background:#e78caf24}.tone-cyan{border-color:#67d7e82f;background:linear-gradient(145deg,#67d7e810,#151b24 60%)}.tone-cyan:after{background:#67d7e824}.metric b{font-size:27px;display:block;margin-top:4px;letter-spacing:-.5px}.metric span:first-child{font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}.media-card{position:relative;background:linear-gradient(180deg,#171e27,#131920);border:1px solid #334050;border-radius:14px;overflow:hidden;cursor:pointer;box-shadow:0 8px 22px #0002;transition:transform .12s,border-color .12s,box-shadow .12s}.media-card:hover{transform:translateY(-2px);border-color:#61718a;box-shadow:0 14px 30px #0005,0 0 0 1px #6d96ff10}.media-card.selected{outline:2px solid var(--blue);outline-offset:1px}.thumb{height:145px;background:#080b0f;display:flex;align-items:center;justify-content:center}.thumb img{width:100%;height:100%;object-fit:cover;transition:opacity .12s}.storybadge{position:absolute;left:7px;top:7px;z-index:3;background:#10151ddd;border:1px solid #536071;border-radius:999px;padding:2px 6px;font-size:10px;display:none}.storystrip{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:12px}.storyframe{position:relative;border:1px solid #303842;border-radius:8px;overflow:hidden;background:#090c10;cursor:pointer}.storyframe:hover{border-color:#58709a}.storyframe img{display:block;width:100%;aspect-ratio:16/10;object-fit:cover}.storytime{position:absolute;right:3px;bottom:3px;background:#000c;padding:1px 4px;border-radius:4px;font-size:10px}.meta{padding:9px}.name{font-weight:780;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.small{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.check{position:absolute;z-index:4;right:8px;top:8px;width:20px;height:20px;accent-color:var(--blue)}.badge{display:inline-block;font-size:11px;border-radius:999px;padding:3px 8px;background:#a9b7cd15;border:1px solid #a9b7cd1b;margin:5px 4px 0 0;box-shadow:inset 0 1px #ffffff08}.safe,.imported,.archived,.local,.quality-ok,.rights-cleared{background:#53c98316;border-color:#53c98329;color:#9be7b8}.review,.quality-review,.rights-review{background:#d7a34a16;border-color:#d7a34a2b;color:#edc979}.rights-permission{background:#e49b5517;border-color:#e49b552c;color:#efbd86}.private,.error,.cancelled,.rejected,.rights-blocked{background:#d66d7717;border-color:#d66d772d;color:#f1a2aa}.duplicate,.skipped_duplicate{background:#a78bfa17;border-color:#a78bfa2d;color:#c9b9ff}.ready,.audioflag{background:#67d7e815;border-color:#67d7e829;color:#9be9f2}.unreviewed,.rights-unknown{background:#9aabba12;border-color:#9aabba1e;color:#b8c3d0}.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}.toolpanel{background:#111821c9;border:1px solid #354253;border-radius:13px;padding:10px 11px;margin:12px 0;backdrop-filter:blur(12px)}.pagination{display:flex;gap:8px;align-items:center;margin:18px 0}.jobbar{position:sticky;top:59px;z-index:25;background:#151a20ee;border-bottom:1px solid var(--line);display:none;backdrop-filter:blur(8px)}.jobinner{max-width:1540px;margin:auto;padding:9px 20px}.progress{height:7px;background:#303741;border-radius:10px;overflow:hidden;margin-top:6px}.progress i{height:100%;display:block;background:linear-gradient(90deg,#6d96ff,#a78bfa,#67d7e8);width:0}.toast{position:fixed;right:18px;bottom:18px;z-index:100;background:#20262e;border:1px solid #3a4350;border-radius:10px;padding:11px 14px;display:none;max-width:440px;box-shadow:0 18px 50px #0008}.details{display:grid;grid-template-columns:minmax(340px,680px) minmax(300px,1fr);gap:18px}.preview{min-height:340px;background:#080a0d;border:1px solid #202833;border-radius:14px;display:flex;align-items:center;justify-content:center;overflow:hidden}.preview img,.preview video{max-width:100%;max-height:70vh}.kv{display:grid;grid-template-columns:150px 1fr;gap:8px 12px}.kv div:nth-child(odd){color:var(--muted)}.jobs{display:grid;gap:10px}.jobrow{display:grid;grid-template-columns:70px 130px 120px 1fr 180px;gap:10px;align-items:center}.errbox{white-space:pre-wrap;background:#27191a;border:1px solid #653537;padding:8px;border-radius:8px;color:#efb7b7}.about-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.about-hero{position:relative;overflow:hidden;padding:24px}.about-hero:after{content:'';position:absolute;width:340px;height:340px;border-radius:50%;right:-120px;top:-170px;background:radial-gradient(circle,#a78bfa35,transparent 68%);pointer-events:none}.principles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.principle{padding:13px;border:1px solid #3b4757;border-radius:13px;background:#111821aa}.principle b{display:block;margin-bottom:3px}.roadmap{display:grid;gap:8px}.roadmap-step{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #2c3744}.roadmap-step:last-child{border-bottom:0}.step-dot{width:9px;height:9px;border-radius:50%;margin-top:6px;flex:0 0 auto;background:linear-gradient(135deg,#6d96ff,#a78bfa);box-shadow:0 0 12px #6d96ff66}.about-list{display:grid;gap:9px}.about-list div{padding:10px 0;border-bottom:1px solid #29313d}.about-list div:last-child{border-bottom:0}.empty{padding:34px;text-align:center;border:1px dashed #394454;border-radius:14px;color:var(--muted);background:#11161d}.mode-note{font-size:13px;color:#aeb8c5}.softline{height:1px;background:var(--line);border:0;margin:18px 0}.hubgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.hubcard{display:flex;flex-direction:column;gap:7px;min-height:120px}.hubcard>b{font-size:18px}.hubcard>span,.hubcard>small{color:var(--muted)}.setupgrid{display:grid;gap:12px;margin-top:14px}.setupcard{display:grid;gap:12px}.setupmeta{display:grid;grid-template-columns:1fr 2fr;gap:12px}.setupmeta span{display:grid;gap:3px}.setupmeta small{color:var(--muted)}
@media(max-width:1000px){.hero{grid-template-columns:repeat(3,1fr)}.navin{overflow-x:auto}.navin::-webkit-scrollbar{display:none}}@media(max-width:850px){.hero{grid-template-columns:1fr 1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.details,.about-grid{grid-template-columns:1fr}.wrap{padding:14px}.jobrow{grid-template-columns:55px 1fr}.jobrow>*:nth-child(n+3){grid-column:2}.navin{gap:4px;padding:9px 10px}.navlink{padding:7px 8px}.thumb{height:120px}.pagehead h1{font-size:26px}}
'''

GLOBAL_JS=r'''
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let lastJobSample=null;
function toast(t){const x=document.getElementById('toast');if(x){x.style.display='block';x.textContent=t;setTimeout(()=>x.style.display='none',5000)}}
function fmtBytes(n){n=Number(n||0);const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<u.length-1){n/=1024;i++}return (i<2?Math.round(n):n.toFixed(1))+' '+u[i]}
function fmtEta(sec){if(!isFinite(sec)||sec<0)return'';sec=Math.round(sec);if(sec<60)return sec+'s';const m=Math.floor(sec/60),s=sec%60;if(m<60)return m+'m '+s+'s';return Math.floor(m/60)+'h '+(m%60)+'m'}
async function appControl(mode,force=false){
  const t=document.getElementById('toast');if(t){t.style.display='block';t.textContent=(mode==='update'?'Updating':'Restarting')+' Archivist… current tab will reconnect.'}
  try{
    const r=await fetch('/api/app-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,force})});
    if(r.status===409){const x=await r.json();if(confirm((x.error||'A job is running.')+'\n\nRestart/update anyway? The current file may need to restart.'))return appControl(mode,true);if(t)t.style.display='none';return}
    if(!r.ok){const x=await r.json();toast('ERROR: '+(x.error||r.statusText));return}
  }catch(e){}
  await sleep(900);
  for(let i=0;i<100;i++){try{const r=await fetch('/api/ping?x='+Date.now(),{cache:'no-store'});if(r.ok){location.reload();return}}catch(e){}await sleep(500)}
  if(t)t.textContent='Archivist is taking longer than expected. Start it again from the desktop shortcut; startup health-check will roll back a bad release.';
}
async function pollJob(){
  try{
    const r=await fetch('/api/status',{cache:'no-store'}),s=await r.json(),b=document.getElementById('jobbar'),txt=document.getElementById('jobtext'),sub=document.getElementById('jobsub'),bar=document.getElementById('jobpct');
    const j=s.active_job;
    if(j){
      b.style.display='block';let pct=j.total?Math.round(100*j.done/j.total):0;let progress=j.done+'/'+j.total;if(j.stage==='import'&&j.bytes_total)pct=Math.max(pct,Math.min(100,Math.round(100*j.bytes_done/j.bytes_total)));if(j.stage==='media_brain'){const mm=(j.message||'').match(/clip\s+(\d+)\/(\d+)/i);if(mm){pct=Math.min(99,Math.round(100*Number(mm[1])/Math.max(1,Number(mm[2]))));progress=mm[1]+'/'+mm[2]+' clips'}else if((j.message||'').includes('scene scan')){pct=2;progress='scene scan'}}
      let extra='';const now=Date.now()/1000;
      if(j.stage==='import'&&j.bytes_total){if(lastJobSample&&lastJobSample.id===j.id&&j.bytes_done>lastJobSample.bytes){const dt=now-lastJobSample.t,db=j.bytes_done-lastJobSample.bytes;if(dt>0){const sp=db/dt,eta=(j.bytes_total-j.bytes_done)/sp;extra=' · '+fmtBytes(sp)+'/s'+(eta>1?' · ETA '+fmtEta(eta):'')}lastJobSample={id:j.id,t:now,bytes:j.bytes_done}}else if(!lastJobSample||lastJobSample.id!==j.id){lastJobSample={id:j.id,t:now,bytes:j.bytes_done}}}
      else lastJobSample=null;
      txt.textContent='Job #'+j.id+' · '+j.stage+' · '+progress+' · '+pct+'%'+extra;
      const releasable=j.source_releasable&&j.status==='running';sub.textContent=(releasable?'SOURCE SAFE TO DISCONNECT · ':'')+(j.current_filename||j.message||'')+(j.failed?' · '+j.failed+' error(s)':'');bar.style.width=pct+'%';
    }else if(s.discovery&&s.discovery.running){b.style.display='block';txt.textContent='Discovering · '+(s.discovery.current_source||'');sub.textContent=s.discovery.found+' found';bar.style.width='0%';lastJobSample=null}else{b.style.display='none';lastJobSample=null}
  }catch(e){}
  setTimeout(pollJob,800)
}
async function pollSourceStatus(){
  const dots=[...document.querySelectorAll('[data-phone-dot]')],texts=[...document.querySelectorAll('[data-phone-text]')];if(!dots.length&&!texts.length)return;
  try{const r=await fetch('/api/source-status',{cache:'no-store'}),x=await r.json();for(const d of dots)d.classList.toggle('online',!!x.connected);for(const t of texts)t.textContent=x.connected?((x.model||x.serial||'Android')+' connected'):(x.error||'not connected')}catch(e){for(const d of dots)d.classList.remove('online');for(const t of texts)t.textContent='status unavailable'}
  setTimeout(pollSourceStatus,3000)
}
window.addEventListener('DOMContentLoaded',()=>{const r=document.getElementById('restartBtn'),u=document.getElementById('updateBtn');if(r)r.onclick=()=>appControl('restart');if(u)u.onclick=()=>appControl('update');pollJob();pollSourceStatus()});
'''


def _nav_link(href,label,active=False):
    cls='navlink active' if active else 'navlink'
    return f"<a class='{cls}' href='{href}'>{e(label)}</a>"


def layout(title,body,script="",script_srcs=()):
    path=request.path
    media_active=(path=='/media' or path.startswith(('/import','/convert','/library','/search','/best','/clip/','/composer','/item/','/similar/','/export-file/','/composition-file/')))
    social_active=path.startswith('/social')
    devices_active=path.startswith('/devices')
    cloud_active=path.startswith('/cloud')
    activity_active=(path.startswith('/activity') or path.startswith('/jobs'))
    settings_active=(path.startswith('/settings') or path.startswith('/about'))
    nav=''.join([
        _nav_link('/','Home',path=='/'),
        _nav_link('/auto','Auto Edit',path.startswith('/auto')),
        _nav_link('/media','Media',media_active),
        _nav_link('/social','Social Lab',social_active),
        _nav_link('/devices','Devices',devices_active),
        _nav_link('/cloud','Cloud',cloud_active),
        _nav_link('/activity','Activity',activity_active),
        _nav_link('/settings','Settings',settings_active),
    ])
    external_scripts=''.join(f"<script src='{e(src)}'></script>" for src in script_srcs)
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{e(title)} · MediaEngine</title><style>{CSS}</style></head><body>
<nav><div class='navin'><span class='brand'>MediaEngine <span class='version'>v{VERSION}</span></span>{nav}<span class='spacer'></span><button id='restartBtn' class='btn2'>Restart</button><button id='updateBtn' class='ok'>Update</button></div></nav>
<div id='jobbar' class='jobbar'><div class='jobinner'><div class='row space'><b id='jobtext'>Working…</b><a href='/activity' class='muted'>Open activity</a></div><div id='jobsub' class='muted'></div><div class='progress'><i id='jobpct'></i></div></div></div>
<div class='wrap'>{body}</div><div id='toast' class='toast'></div><script>{GLOBAL_JS}\n{script}</script>{external_scripts}</body></html>"""


def page_nav(page,pages,params=None):
    pages=max(1,int(pages or 1)); page=max(1,min(int(page or 1),pages))
    base={str(k):str(v) for k,v in (params or {}).items() if str(k)!='page' and v not in (None,'')}
    def href(p):
        return '?'+urllib.parse.urlencode({**base,'page':int(p)})
    nums={1,pages}
    for p in range(max(1,page-2),min(pages,page+2)+1):
        nums.add(p)
    nums=sorted(nums); links=[]; last=None
    for p in nums:
        if last is not None and p>last+1:
            links.append("<span class='muted'>…</span>")
        cls='btn' if p==page else 'btn btn2'
        links.append(f"<a class='{cls}' href='{href(p)}'>{p}</a>")
        last=p
    hidden=''.join(f"<input type='hidden' name='{e(k)}' value='{e(v)}'>" for k,v in base.items())
    return (f"<div class='pagination'><a class='btn btn2' href='{href(1)}'>First</a>"
            f"<a class='btn btn2' href='{href(max(1,page-1))}'>Previous</a>{''.join(links)}"
            f"<form method='get' class='row' style='margin:0'>{hidden}<span class='muted'>Page</span>"
            f"<input type='number' name='page' min='1' max='{pages}' value='{page}' style='width:78px'>"
            f"<span class='muted'>of {pages}</span><button class='btn2'>Go</button></form>"
            f"<a class='btn btn2' href='{href(min(pages,page+1))}'>Next</a>"
            f"<a class='btn btn2' href='{href(pages)}'>Last</a></div>")

def placeholder_svg(kind='video'):
    glyph='▶' if kind=='video' else '▧'; return f"<svg xmlns='http://www.w3.org/2000/svg' width='480' height='360'><rect width='100%' height='100%' fill='#0b0d10'/><text x='50%' y='50%' fill='#667180' font-size='54' text-anchor='middle' dominant-baseline='middle'>{glyph}</text></svg>"


def _spawn_launcher(mode):
    spawn_app_launcher(HOME, mode)


def _exit_soon(): time.sleep(.8); os._exit(0)


_ALLOWED_LOOPBACK_HOSTS = frozenset((f'127.0.0.1:{APP_PORT}',f'localhost:{APP_PORT}'))
_MUTATING_METHODS = frozenset(('POST','PUT','PATCH','DELETE'))

def _exact_loopback_origin(value):
    text=str(value or '').strip()
    if not text:
        return None
    try:
        parsed=urllib.parse.urlsplit(text)
        port=parsed.port
    except (TypeError, ValueError):
        return None
    host=(parsed.hostname or '').lower()
    if parsed.scheme.lower()!='http' or host not in ('127.0.0.1','localhost') or port!=APP_PORT:
        return None
    if parsed.username or parsed.password:
        return None
    return (parsed.scheme.lower(),host,port)


def create_app():
    init_db(); ensure_media_brain_schema(); app=Flask(__name__)

    @app.before_request
    def local_origin_guard():
        # Reject DNS-rebinding Host values before route dispatch. Browser mutations
        # must also come from the exact loopback origin; local service clients that
        # send no browser Origin/Referer remain compatible when Host is exact.
        host=(request.headers.get('Host') or '').strip().lower()
        if host not in _ALLOWED_LOOPBACK_HOSTS:
            return jsonify({'error':'Invalid Host'}),403
        if request.method not in _MUTATING_METHODS:
            return None
        origin=request.headers.get('Origin','')
        referer=request.headers.get('Referer','')
        if origin and _exact_loopback_origin(origin) is None:
            return jsonify({'error':'Cross-origin request blocked'}),403
        if not origin and referer and _exact_loopback_origin(referer) is None:
            return jsonify({'error':'Cross-origin request blocked'}),403
        return None

    @app.get('/api/ping')
    def ping(): return jsonify({'ok':True,'version':VERSION})

    @app.get('/diagnostics/fixture.mp4')
    def diagnostics_fixture():
        p=Path(__file__).resolve().parent/'assets'/'browser_fixture_h264.mp4'
        return send_file(p,mimetype='video/mp4',conditional=True)

    @app.get('/diagnostics/browser')
    def diagnostics_browser():
        # Self-contained real-browser fixture. It never touches user media.
        return """<!doctype html><html><head><meta charset="utf-8"><style>
        body{margin:0;background:#090d12;color:#fff;font:15px system-ui}.stage{width:720px;margin:30px auto}.viewport{background:#000;width:640px;aspect-ratio:16/9;overflow:hidden}.viewport canvas{width:100%;height:100%}.seek{position:relative;width:520px;height:26px;margin-top:20px}.track{position:absolute;left:0;right:0;top:11px;height:4px;background:#263244}.thumb{position:absolute;left:0;top:5px;width:16px;height:16px;border-radius:50%;background:#eaf7ff}.seek input{position:absolute;inset:0;width:100%;height:26px;opacity:0;margin:0;padding:0}video{position:fixed;width:2px;height:2px;opacity:.01;left:-10px}</style></head><body>
        <div class="stage"><div class="viewport" id="vp"><canvas id="cv"></canvas></div><div class="seek" id="seek"><div class="track"></div><div class="thumb" id="thumb"></div><input id="range" type="range" min="0" max="1000" value="0"></div></div>
        <video id="video" muted playsinline preload="auto" src="/diagnostics/fixture.mp4"></video><pre id="diag-result">running</pre>
        <script>
        (async()=>{const checks=[],video=document.getElementById('video'),canvas=document.getElementById('cv'),ctx=canvas.getContext('2d'),out=document.getElementById('diag-result');
        const add=(name,pass,detail)=>checks.push({name,pass:Boolean(pass),detail});const wait=(test,ms=8000)=>new Promise((resolve,reject)=>{const end=Date.now()+ms;(function tick(){if(test())return resolve();if(Date.now()>end)return reject(new Error('timeout'));setTimeout(tick,40)})()});
        try{await wait(()=>video.readyState>=1);add('metadata',video.videoWidth===640&&video.videoHeight===360,{w:video.videoWidth,h:video.videoHeight,duration:video.duration});
        await video.play();await wait(()=>video.currentTime>.35);canvas.width=640;canvas.height=360;ctx.drawImage(video,0,0);const px=ctx.getImageData(0,0,640,360).data;let bright=0,diff=0,prev=px[0];for(let i=0;i<px.length;i+=64){bright+=px[i]+px[i+1]+px[i+2];diff+=Math.abs(px[i]-prev);prev=px[i]}add('canvas_non_black',bright>250000&&diff>2000,{brightness:bright,difference:diff,time:video.currentTime});video.pause();
        video.currentTime=1.25;await wait(()=>Math.abs(video.currentTime-1.25)<.15);add('seek',true,{time:video.currentTime});video.currentTime=0;await video.play();await wait(()=>video.currentTime>.12);add('replay_from_zero',video.currentTime<.85,{time:video.currentTime});video.pause();
        const s=document.getElementById('seek').getBoundingClientRect(),t=document.getElementById('thumb').getBoundingClientRect();add('scrubber_physical_zero',Math.abs(t.left-s.left)<=.5,{delta:t.left-s.left});
        for(const pair of [[16,9],[4,5],[1,1],[9,16]]){canvas.width=pair[0]*40;canvas.height=pair[1]*40;add('aspect_'+pair.join(':'),Math.abs(canvas.width/canvas.height-pair[0]/pair[1])<.001,{w:canvas.width,h:canvas.height})}
        }catch(e){add('browser_exception',false,String(e))}const pass=checks.every(x=>x.pass);out.dataset.status=pass?'passed':'failed';out.textContent=JSON.stringify({status:pass?'passed':'failed',edge_version:navigator.userAgent,checks});})();
        </script></body></html>"""

    @app.get('/api/status')
    def status():
        snap=STATE.snapshot()
        with db() as con:
            j=con.execute("SELECT * FROM jobs WHERE status='running' ORDER BY id LIMIT 1").fetchone()
            if not j: j=con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
            queued=con.execute("SELECT COUNT(*) n FROM jobs WHERE status='queued'").fetchone()['n']
        snap['active_job']={k:j[k] for k in j.keys()} if j else None
        snap['queued_jobs']=queued
        return jsonify(snap)

    @app.post('/api/app-control')
    def app_control():
        payload=request.get_json(silent=True) or {};mode=payload.get('mode','restart');force=bool(payload.get('force'))
        if mode not in ('restart','update','stop'): return jsonify({'ok':False,'error':'bad mode'}),400
        with db() as con:
            busy=con.execute("SELECT id,kind,current_filename FROM jobs WHERE status='running' ORDER BY id LIMIT 1").fetchone()
        if busy and not force:
            return jsonify({'ok':False,'error':f"Job #{busy['id']} ({busy['kind']}) is running"}),409
        if mode!='stop': _spawn_launcher(mode)
        threading.Thread(target=_exit_soon,daemon=True).start(); return jsonify({'ok':True})

    def phone_snapshot():
        adb=android.find_adb()
        devs,err=android.adb_devices(adb) if adb else ([], 'ADB not installed')
        phone=next((d for d in devs if d.get('state')=='device'),None)
        return {
            'connected':bool(phone),
            'serial':phone.get('serial','') if phone else '',
            'model':phone.get('model','') if phone else '',
            'error':None if phone else (err or 'not connected'),
        }

    @app.get('/api/source-status')
    def source_status():
        return jsonify(phone_snapshot())

    @app.get('/')
    def dashboard():
        local_sql="excluded=0 AND work_selected=1 AND private_path IS NULL AND rejected_path IS NULL AND analysis_status<>'private' AND (source_kind='fixed' OR staging_path IS NOT NULL OR archive_path IS NOT NULL)"
        with db() as con:
            metrics=con.execute(f"""SELECT
                SUM(CASE WHEN excluded=0 AND private_path IS NULL AND analysis_status<>'private' THEN 1 ELSE 0 END) total,
                SUM(CASE WHEN {local_sql} THEN 1 ELSE 0 END) imported,
                SUM(CASE WHEN {local_sql} AND media_type='video' THEN 1 ELSE 0 END) videos,
                SUM(CASE WHEN excluded=0 AND work_selected=0 AND source_kind IN ('android','removable','fixed') AND private_path IS NULL AND rejected_path IS NULL AND analysis_status<>'private' THEN 1 ELSE 0 END) waiting,
                SUM(CASE WHEN {local_sql} AND analysis_status='review' THEN 1 ELSE 0 END) review,
                SUM(CASE WHEN {local_sql} AND rights_status IN ('review','permission','blocked') THEN 1 ELSE 0 END) rights_review,
                SUM(CASE WHEN excluded=0 AND (import_status='error' OR analysis_status='error') THEN 1 ELSE 0 END) errs
                FROM inventory""").fetchone()
            total=int(metrics['total'] or 0);imported=int(metrics['imported'] or 0);videos=int(metrics['videos'] or 0)
            waiting=int(metrics['waiting'] or 0);review=int(metrics['review'] or 0);rights=int(metrics['rights_review'] or 0);errs=int(metrics['errs'] or 0)
        phone=phone_snapshot(); phone_text=(phone.get('model') or phone.get('serial') or 'Android')+' connected' if phone['connected'] else (phone.get('error') or 'not connected')
        body=f"""<div class='pagehead row space'><div><div class='eyebrow'>Local-first media workspace</div><h1>Your footage, ready to work.</h1><div class='lead'>Browse Android, SD/USB and local folders in one place. Library stays clean: only media you explicitly add becomes part of the working collection.</div></div><div class='row'><a class='btn' href='/auto'>Auto Edit</a><a class='btn btn2' href='/welcome'>Start here</a><a class='btn btn2' href='/import'>Import new media</a><a class='btn btn2' href='/library'>Open Library</a></div></div>
<div class='hero'><div class='card metric tone-blue'><span class='muted'>On sources</span><b>{total}</b></div><div class='card metric tone-amber'><span class='muted'>Waiting to import</span><b>{waiting}</b></div><div class='card metric tone-mint'><span class='muted'>In Library</span><b>{imported}</b></div><div class='card metric tone-cyan'><span class='muted'>Library videos</span><b>{videos}</b></div><div class='card metric tone-rose'><span class='muted'>Privacy review</span><b>{review}</b></div><div class='card metric tone-violet'><span class='muted'>Rights review</span><b>{rights}</b></div></div>
<div class='card source-card'><div class='device'><span class='device-dot {'online' if phone['connected'] else ''}' data-phone-dot></span><div><div class='device-status'>Android source</div><div class='muted' data-phone-text>{e(phone_text)}</div></div></div><div class='row'><span class='badge {'error' if errs else 'safe'}'>{errs} errors</span><a class='btn btn2' href='/jobs'>Jobs</a></div></div>
<div class='section-title'>How it works</div><div class='card callout'>Browse every source in <b>Import</b> → select what you want → <b>Add to Library</b> or <b>Add + Analyze</b>. Local-folder files stay in place; Android/SD files copy to Staging. Private and Rejected media never appear in Library.</div>"""
        return layout('Dashboard',body)


    @app.get('/media')
    def media_hub():
        body="""<div class='pagehead'><div class='eyebrow'>Media workspace</div><h1>Media</h1><div class='lead'>Ingest, understand, find, convert and compose from the local working library. Existing media routes remain unchanged under this section.</div></div>
<div class='hubgrid'>
<a class='card hubcard tone-blue' href='/import'><b>Import</b><span>Browse folders, Android and removable sources.</span></a>
<a class='card hubcard tone-mint' href='/library'><b>Library</b><span>The media you explicitly selected for work.</span></a>
<a class='card hubcard tone-violet' href='/search'><b>Search</b><span>Local semantic signals and Find Similar.</span></a>
<a class='card hubcard tone-amber' href='/best'><b>Best Moments</b><span>Review Media Brain virtual clips.</span></a>
<a class='card hubcard tone-amber' href='/auto'><b>Auto Edit</b><span>Folder of videos → finished reel from the best moments.</span></a>
<a class='card hubcard tone-cyan' href='/composer'><b>Composer</b><span>Build nondestructive multi-clip compositions.</span></a>
<a class='card hubcard tone-rose' href='/convert'><b>Convert</b><span>Create local derived copies without altering originals.</span></a>
</div>"""
        return layout('Media',body)

    @app.get('/social')
    def social_hub():
        ensure_social_schema();stats=publication_stats();pubs=list_publications(10);comps=recent_rendered_compositions(10)
        body=f"<div class='pagehead'><div class='eyebrow'>M10 / Local-first</div><h1>Social Lab</h1><div class='lead'>Publication history and structural Novelty Guard are local. No social account is connected and nothing is published automatically.</div></div><div class='about-grid'><div class='card'><div class='kpi'>{int(stats['publications'])}</div><div class='muted'>history records</div></div><div class='card'><div class='kpi'>{int(stats['novelty_checks'])}</div><div class='muted'>novelty checks</div></div><div class='card'><b>Novelty Guard v1</b><div class='muted'>Exact hash + structural overlap + visual_dhash_v1 + local audio_spectrum_v1. Audio alone can request review but cannot block unless another strong similarity signal agrees.</div></div></div><div class='card' style='margin-top:14px'><h2>Rendered compositions</h2>"
        if not comps:body+="<div class='muted'>No finished local compositions yet.</div>"
        for c in comps:body+=f"<div class='row space' style='padding:8px 0;border-bottom:1px solid #223'><div><b>{e(c['title'])}</b><div class='muted'>{e(c['aspect'])}</div></div><form method='post' action='/social/check/{int(c['id'])}'><button class='btn btn2'>Check novelty</button></form><form method='post' action='/social/queue/{int(c['id'])}'><button class='btn btn2'>Queue</button></form></div>"
        body+="</div><div class='card' style='margin-top:14px'><h2>Publication history</h2>"
        if not pubs:body+="<div class='muted'>History is empty. A novelty check does not publish anything.</div>"
        for p in pubs:body+=f"<div class='row space' style='padding:8px 0;border-bottom:1px solid #223'><div><b>{e(p.get('title') or 'Untitled')}</b><div class='muted'>{e(p.get('status') or '')} - {e(p.get('platform') or 'local/manual')}</div></div><span class='badge'>{e(p.get('novelty_state') or 'recorded')}</span></div>"
        body+="</div><div class='card callout' style='margin-top:14px'><b>Privacy boundary:</b><div class='muted'>Publication history and detailed novelty signals stay in the local Archivist database. No raw media or fingerprints are sent to Supabase.</div></div>"
        queue=list_social_queue(30)
        body+="<div class='card' style='margin-top:14px'><h2>Content queue</h2>"
        if not queue:body+="<div class='muted'>Queue is empty.</div>"
        for q in queue:
            body+=f"<div class='row space' style='padding:8px 0;border-bottom:1px solid #223'><div><b>{e(q.get('title') or 'Untitled')}</b><div class='muted'>{e(q['queue_state'])} · novelty {e(q['novelty_state'])}</div></div>"
            if q['queue_state']=='review':body+=f"<form method='post' action='/social/queue-item/{int(q['id'])}/ready'><button class='btn btn2'>Mark ready</button></form>"
            elif q['queue_state']=='ready':body+=f"<form method='post' action='/social/queue-item/{int(q['id'])}/review'><button class='btn btn2'>Review</button></form>"
            elif q['queue_state']=='hold':body+="<span class='badge'>hold</span>"
            body+="</div>"
        body+="</div>"
        body+="<div class='card callout' style='margin-top:14px'><div class='row space'><div><b>M11 Experiments</b><div class='muted'>Plan hook/caption/cover/duration/order variants and record manual/import performance metrics locally.</div></div><a class='btn btn2' href='/social/experiments'>Open Experiments</a></div></div>"
        body+="<div class='card callout' style='margin-top:14px'><div class='row space'><div><b>M12 Manual Handoff</b><div class='muted'>Create a local manifest for manual upload. No provider API, token or automatic publishing is used.</div></div><a class='btn btn2' href='/social/manual-handoff'>Open Manual Handoff</a></div></div>"
        return layout('Social Lab',body)

    @app.post('/social/check/<int:composition_id>')
    def social_check(composition_id):
        try:
            x=candidate_from_composition(composition_id);r=evaluate_social_composition(composition_id);state=r['state']
            body=f"<div class='pagehead'><div class='eyebrow'>M10 / Novelty Guard</div><h1>{e(state)}</h1><div class='lead'>Compared locally with {int(r['compared_count'])} history records.</div></div><div class='card'><b>{e(x['title'])}</b><div class='muted'>Source overlap {float(r['source_overlap']):.0%} - sequence similarity {float(r['sequence_similarity']):.0%} - visual {float(r.get('max_visual_similarity') or 0):.0%} - audio {float(r.get('max_audio_similarity') or 0):.0%}</div><div style='margin-top:12px'><form method='post' action='/social/record/{int(composition_id)}'><button>Record in local history</button></form><a class='btn btn2' href='/social'>Back</a></div></div>"
            return layout('Novelty check',body)
        except Exception as exc:return layout('Novelty check failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/social'>Back</a></div>"),400

    @app.post('/social/record/<int:composition_id>')
    def social_record(composition_id):
        try:
            r=record_social_composition(composition_id,status='exported')
            return layout('Recorded',f"<div class='pagehead'><div class='eyebrow'>M10 / Local history</div><h1>Recorded</h1><div class='lead'>Added to local history only. Nothing was sent to a social platform.</div></div><div class='card'><b>Novelty state: {e(r['novelty']['state'])}</b><div style='margin-top:12px'><a class='btn btn2' href='/social'>Back to Social Lab</a></div></div>")
        except Exception as exc:return layout('Record failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/social'>Back</a></div>"),400

    @app.post('/social/queue/<int:composition_id>')
    def social_queue_add(composition_id):
        try:
            r=enqueue_social_composition(composition_id)
            return layout('Queued',f"<div class='pagehead'><div class='eyebrow'>M10 / Content Queue</div><h1>{e(r['queue_state'])}</h1><div class='lead'>Queued locally. Nothing was sent to any platform.</div></div><div class='card'><b>Novelty: {e(r['novelty']['state'])}</b><div style='margin-top:12px'><a class='btn btn2' href='/social'>Back to Social Lab</a></div></div>")
        except Exception as exc:return layout('Queue failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/social'>Back</a></div>"),400

    @app.post('/social/queue-item/<int:queue_id>/<state>')
    def social_queue_state(queue_id,state):
        try:
            set_social_queue_state(queue_id,state)
            return redirect('/social')
        except Exception as exc:return layout('Queue update failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/social'>Back</a></div>"),400


    @app.get('/social/manual-handoff')
    def social_manual_handoff():
        comps=recent_rendered_compositions(50);connectors=m12_connector_catalog()
        body="<div class='pagehead'><div class='eyebrow'>M12 / Safe fallback</div><h1>Manual social handoff</h1><div class='lead'>Generate a local JSON manifest beside your workflow. Archivist does not upload media, call a provider API or use credentials.</div></div><form class='card' method='post' action='/social/manual-handoff'><select name='composition_id' required><option value=''>Choose rendered composition</option>"
        for c in comps:body+=f"<option value='{int(c['id'])}'>{e(c['title'])} · {e(c['aspect'])}</option>"
        body+="</select><select name='platform_target'><option value='other'>Other / manual</option>"
        for c in connectors:body+=f"<option value='{e(c['id'])}'>{e(c['name'])}</option>"
        body+="</select><textarea name='caption_text' rows='4' style='width:100%;margin-top:8px' placeholder='Caption / notes'></textarea><div style='margin-top:8px'><button>Create local handoff manifest</button></div></form><div class='card callout' style='margin-top:12px'><b>No automatic publishing.</b><div class='muted'>Blocked Novelty Guard items cannot generate a handoff. Similar-review items require this explicit manual action.</div></div><a class='btn btn2' href='/social'>Back to Social Lab</a>"
        return layout('Manual social handoff',body)

    @app.post('/social/manual-handoff')
    def social_manual_handoff_create():
        try:
            result=create_manual_handoff_for_composition(int(request.form.get('composition_id') or 0),request.form.get('platform_target','other'),request.form.get('caption_text',''))
            body=f"<div class='pagehead'><div class='eyebrow'>M12 / Local manifest</div><h1>Handoff ready</h1><div class='lead'>Nothing was uploaded. Use the local rendered media plus this manifest for manual publishing.</div></div><div class='card'><b>Target: {e(result['platform_target'])}</b><div class='muted'>Manifest: {e(result['manifest_path'])}</div><div class='muted'>Media: {e(result['media_path'])}</div><div class='muted'>Novelty: {e(result['novelty_state'])}</div><div style='margin-top:10px'><a class='btn btn2' href='/social/manual-handoff'>Back</a></div></div>"
            return layout('Handoff ready',body)
        except Exception as exc:
            return layout('Handoff blocked',f"<div class='card'><div class='errbox'>{e(str(exc)[:1000])}</div><a class='btn btn2' href='/social/manual-handoff'>Back</a></div>"),400


    @app.get('/social/experiments')
    def social_experiments():
        ensure_experiment_schema();rows=list_social_experiments(50);comps=recent_rendered_compositions(30);stats=experiment_stats()
        body=f"<div class='pagehead'><div class='eyebrow'>M11 / Local experiments</div><h1>Experiments</h1><div class='lead'>Plan metadata variants and record manual/import performance results locally. No social account or publishing connector is used.</div></div><div class='about-grid'><div class='card'><b>{int(stats['experiments'])}</b><div class='muted'>experiments</div></div><div class='card'><b>{int(stats['variants'])}</b><div class='muted'>variants · {int(stats['results'])} result rows</div></div></div>"
        body+="<form class='card toolbar' method='post' action='/social/experiments/create'><input name='title' placeholder='Experiment title' maxlength='160'><input name='objective' placeholder='Objective / hypothesis' maxlength='500'><select name='composition_id'><option value=''>No base composition</option>"
        for c in comps:body+=f"<option value='{int(c['id'])}'>{e(c['title'])} · {e(c['aspect'])}</option>"
        body+="</select><button>Create</button></form><div class='jobs'>"
        if not rows:body+="<div class='empty'>No experiments yet.</div>"
        for x in rows:body+=f"<a class='card row space' href='/social/experiments/{int(x['id'])}'><div><b>{e(x['title'])}</b><div class='muted'>{e(x['status'])} · {int(x['variant_count'])} variants · {int(x['result_count'])} result rows</div></div><span class='btn btn2'>Open</span></a>"
        body+="</div><div style='margin-top:14px'><a class='btn btn2' href='/social'>Back to Social Lab</a></div>"
        return layout('Experiments',body)

    @app.post('/social/experiments/create')
    def social_experiment_create():
        try:
            eid=create_social_experiment(request.form.get('title',''),request.form.get('composition_id') or None,request.form.get('objective',''))
            return redirect(f'/social/experiments/{eid}')
        except Exception as exc:return layout('Experiment failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/social/experiments'>Back</a></div>"),400

    @app.get('/social/experiments/<int:experiment_id>')
    def social_experiment_detail(experiment_id):
        d=get_social_experiment(experiment_id)
        summaries=get_experiment_metric_summaries(experiment_id)
        if not d:return 'Not found',404
        x=d['experiment'];body=f"<div class='pagehead'><div class='eyebrow'>M11 / Experiment</div><h1>{e(x['title'])}</h1><div class='lead'>{e(x.get('objective') or 'No objective recorded')}</div></div>"
        body+="<form class='card' method='post' action='/social/experiments/%d/variant'><h2>Add variant</h2><div class='toolbar'><input name='label' placeholder='Variant label'><input name='hook_text' placeholder='Hook'><input name='caption_text' placeholder='Caption'><input name='cover_ref' placeholder='Cover ref'><input name='target_duration_s' type='number' min='0' max='180' step='0.1' placeholder='Duration s'><input name='clip_order' placeholder='Clip order: 3,2,1'><button>Add variant</button></div></form>"%int(experiment_id)
        for v in d['variants']:
            body+=f"<div class='card' style='margin-top:12px'><div class='row space'><div><b>{e(v['label'])}</b><div class='muted'>{e(v['status'])} · duration {e(v.get('target_duration_s') or '—')} · order {e(','.join(str(i) for i in v.get('clip_order',[])) or '—')}</div></div><span class='badge'>{len(v.get('results') or [])} results</span></div><div class='muted' style='margin-top:6px'>Hook: {e(v.get('hook_text') or '—')} · Caption: {e(v.get('caption_text') or '—')} · Cover: {e(v.get('cover_ref') or '—')}</div><form class='toolbar' method='post' action='/social/experiments/variant/{int(v['id'])}/result'><input name='views' type='number' min='0' placeholder='Views'><input name='likes' type='number' min='0' placeholder='Likes'><input name='comments' type='number' min='0' placeholder='Comments'><input name='shares' type='number' min='0' placeholder='Shares'><input name='saves' type='number' min='0' placeholder='Saves'><input name='avg_view_duration_s' type='number' min='0' step='0.1' placeholder='Avg view s'><input name='retention_3s_pct' type='number' min='0' max='100' step='0.1' placeholder='3s retention %'><input name='completion_pct' type='number' min='0' max='100' step='0.1' placeholder='Completion %'><button>Record manual result</button></form></div>"
        body+="<div class='card' style='margin-top:12px'><h2>Derived metric summaries</h2><div class='muted'>Descriptive totals and rates only. Archivist does not rank variants or choose a winner.</div>"
        if not summaries:body+="<div class='muted' style='margin-top:8px'>No result rows yet.</div>"
        for s in summaries:
            er="—" if s.get('engagement_rate_pct') is None else f"{float(s['engagement_rate_pct']):.2f}%"
            av="—" if s.get('avg_view_duration_s') is None else f"{float(s['avg_view_duration_s']):.2f}s"
            rt="—" if s.get('retention_3s_pct') is None else f"{float(s['retention_3s_pct']):.1f}%"
            cp="—" if s.get('completion_pct') is None else f"{float(s['completion_pct']):.1f}%"
            body+=f"<div class='row space' style='padding:8px 0;border-bottom:1px solid #223'><div><b>{e(s['label'])}</b><div class='muted'>{int(s['result_rows'])} rows · {int(s['views'])} views · {int(s['engagements'])} engagements</div></div><div class='muted'>ER {e(er)} · avg {e(av)} · 3s {e(rt)} · completion {e(cp)}</div></div>"
        body+="</div>"
        body+=f"<form class='card' style='margin-top:12px' method='post' action='/social/experiments/{int(experiment_id)}/csv-preview'><h2>CSV import preview</h2><div class='muted'>Required: variant_id plus at least one metric column. Preview never writes data; confirm import is a separate step. Max 200 rows / 128 KiB.</div><textarea name='csv_text' rows='8' style='width:100%;margin-top:8px' placeholder='variant_id,observed_at,views,likes,...'></textarea><div style='margin-top:8px'><button>Validate & preview</button></div></form>"
        body+="<div style='margin-top:14px'><a class='btn btn2' href='/social/experiments'>Back to Experiments</a></div>"
        return layout('Experiment',body)

    @app.post('/social/experiments/<int:experiment_id>/variant')
    def social_experiment_variant_add(experiment_id):
        try:
            add_social_variant(experiment_id,request.form.get('label',''),request.form.get('hook_text',''),request.form.get('caption_text',''),request.form.get('cover_ref',''),request.form.get('target_duration_s') or None,request.form.get('clip_order',''),request.form.get('notes',''))
            return redirect(f'/social/experiments/{experiment_id}')
        except Exception as exc:return layout('Variant failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div></div>"),400

    @app.post('/social/experiments/variant/<int:variant_id>/result')
    def social_experiment_result_add(variant_id):
        try:
            record_social_result(variant_id,'manual',views=request.form.get('views',0),likes=request.form.get('likes',0),comments=request.form.get('comments',0),shares=request.form.get('shares',0),saves=request.form.get('saves',0),avg_view_duration_s=request.form.get('avg_view_duration_s',0),retention_3s_pct=request.form.get('retention_3s_pct') or None,completion_pct=request.form.get('completion_pct') or None)
            with db() as con:r=con.execute('SELECT experiment_id FROM social_experiment_variants WHERE id=?',(int(variant_id),)).fetchone()
            return redirect(f"/social/experiments/{int(r['experiment_id'])}") if r else redirect('/social/experiments')
        except Exception as exc:return layout('Result failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:500])}</div></div>"),400


    @app.post('/social/experiments/<int:experiment_id>/csv-preview')
    def social_experiment_csv_preview(experiment_id):
        csv_text=request.form.get('csv_text','')
        p=validate_experiment_results_csv(experiment_id,csv_text)
        body=f"<div class='pagehead'><div class='eyebrow'>M11 / CSV preview</div><h1>{'Ready to import' if p['ok'] else 'Validation failed'}</h1><div class='lead'>Preview is read-only. No result rows were inserted.</div></div><div class='card'>"
        if p['errors']:
            body+="<div class='errbox'>"+e(' | '.join(p['errors'][:20]))+"</div>"
        else:
            body+=f"<b>{int(p['row_count'])} validated rows</b><div class='muted'>Source will be stored as import. No ranking or winner selection is performed.</div>"
            for row in p['rows'][:20]:
                body+=f"<div class='muted' style='padding:4px 0'>variant {int(row['variant_id'])} · views {int(row['views'])} · completion {e(row.get('completion_pct') if row.get('completion_pct') is not None else '—')}</div>"
            body+=f"<form method='post' action='/social/experiments/{int(experiment_id)}/csv-import'><textarea name='csv_text' hidden>{e(csv_text)}</textarea><button style='margin-top:10px'>Confirm import</button></form>"
        body+=f"<div style='margin-top:10px'><a class='btn btn2' href='/social/experiments/{int(experiment_id)}'>Back</a></div></div>"
        return layout('CSV preview',body), (200 if p['ok'] else 400)

    @app.post('/social/experiments/<int:experiment_id>/csv-import')
    def social_experiment_csv_import(experiment_id):
        try:
            result=import_experiment_results_csv(experiment_id,request.form.get('csv_text',''))
            body=f"<div class='pagehead'><div class='eyebrow'>M11 / CSV import</div><h1>Imported</h1><div class='lead'>{int(result['imported'])} new rows · {int(result['skipped_duplicates'])} exact duplicates skipped.</div></div><div class='card'><div class='muted'>No automatic ranking or winner selection was performed.</div><a class='btn btn2' href='/social/experiments/{int(experiment_id)}'>Back to experiment</a></div>"
            return layout('CSV imported',body)
        except Exception as exc:
            return layout('CSV import failed',f"<div class='card'><div class='errbox'>{e(str(exc)[:1000])}</div><a class='btn btn2' href='/social/experiments/{int(experiment_id)}'>Back</a></div>"),400


    @app.get('/welcome')
    def beta_welcome():
        return layout('First run',welcome_body(setup_catalog(load_config())))

    @app.get('/help')
    def beta_help():
        body=help_body()+"""<div class='card'><h3>Create a local support bundle</h3><p>Creates a bounded, sanitized ZIP on this PC only. It is never uploaded automatically and excludes raw media, credentials, database contents and full personal paths.</p><form method='post' action='/support/bundle'><button class='btn' type='submit'>Create support bundle</button></form></div>"""
        return layout('Help & recovery',body)

    @app.post('/support/bundle')
    def support_bundle_create():
        from .support_bundle import create_support_bundle
        try:
            path=create_support_bundle()
        except Exception:
            body="""<div class='pagehead'><div class='eyebrow'>Local diagnostics</div><h1>Support bundle could not be created</h1>
<div class='lead'>Archivist did not upload anything. The failure stayed on this PC.</div></div>
<div class='card'><div class='errbox'><b>Local bundle creation failed.</b><div class='muted' style='margin-top:5px'>Try again. If it still fails, restart Archivist and open Help &amp; Recovery. Raw error details, credentials and personal paths are not shown here.</div></div>
<form method='post' action='/support/bundle' style='margin-top:10px'><button class='btn' type='submit'>Try again</button></form>
<div style='margin-top:10px'><a class='btn btn2' href='/help'>Help &amp; Recovery</a></div></div>"""
            return layout('Support bundle failed',body),500
        return layout('Support bundle ready',f"<div class='card'><h3>Support bundle created locally</h3><p><b>{e(path.name)}</b></p><p>Location: Archivist local data/support folder. Nothing was uploaded.</p><a class='btn btn2' href='/help'>Back to Help</a></div>")

    @app.get('/help/guide')
    def beta_help_guide():
        return layout('Beta guide',guide_body())

    @app.get('/devices')
    def devices_hub():
        phone=phone_snapshot()
        phone_text=(phone.get('model') or phone.get('serial') or 'Android')+' connected' if phone['connected'] else (phone.get('error') or 'not connected')
        body=f"""<div class='pagehead'><div class='eyebrow'>Per-install device registry</div><h1>Devices</h1><div class='lead'>Media-source devices and the future Social Device Lab are separate capabilities. Nothing here hard-codes a personal phone model or account.</div></div>
<div class='hubgrid'>
<div class='card hubcard tone-mint'><b>Android · Media Source</b><span class='device'><i class='device-dot {'online' if phone['connected'] else ''}' data-phone-dot></i><span data-phone-text>{e(phone_text)}</span></span><small>Existing ADB/MediaStore ingest foundation.</small></div>
<div class='card hubcard'><b>Android · Social Device Lab</b><span>Planned for native QA, draft handoff and manual fallback.</span><small>Not implemented in this release.</small></div>
<div class='card hubcard'><b>iPhone / iOS</b><span>Separate future media-source and Social Device Lab adapters.</span><small>Not represented as implemented until real-device validation passes.</small></div>
</div>
<div class='card callout' style='margin-top:14px'><div class='row space'><div><b>Media-source recovery</b><div class='muted'>If Android or another local source is missing, recheck discovery. This only rescans source availability; it does not change device settings or delete media.</div></div><div class='row'><button id='deviceRecheck' class='btn2'>Recheck media sources</button><a class='btn btn2' href='/help'>Help &amp; Recovery</a></div></div></div>"""
        script="""const recheck=document.getElementById('deviceRecheck');
if(recheck)recheck.onclick=async()=>{
  if(recheck.disabled)return;
  const label=recheck.textContent;recheck.disabled=true;recheck.textContent='Rechecking…';
  try{
    const r=await fetch('/api/discover',{method:'POST'});
    let x={};try{x=await r.json()}catch(_){}
    if(!r.ok)throw new Error(x.error||('HTTP '+r.status));
    toast(x.message||'Source recheck started');
    setTimeout(()=>location.reload(),1200);
  }catch(err){
    toast('Could not start source recheck — '+((err&&err.message)||'open Help & Recovery'));
    recheck.disabled=false;recheck.textContent=label;
  }
};"""
        return layout('Devices',body,script)

    @app.get('/cloud')
    def cloud_hub():
        body="""<div class='pagehead'><div class='eyebrow'>Optional services</div><h1>Cloud</h1><div class='lead'>Cloud features remain opt-in. Local processing and local media are the default.</div></div>
<div class='about-grid'>
<div class='card'><h2 style='margin-top:0'>Cloud Vault</h2><span class='badge unreviewed'>Disabled</span><p class='muted'>Future modes: exports only, selected media, or full archive mirror. Enabling upload must never delete local/source originals.</p><a class='btn btn2' href='/settings/connections'>Setup & Connections</a></div>
<div class='card'><h2 style='margin-top:0'>Cloud Compute</h2><div class='row'><span class='badge safe'>Local · current</span><span class='badge unreviewed'>Cloud · planned</span><span class='badge unreviewed'>Auto · planned</span></div><p class='muted'>Supabase may coordinate identity/jobs/metadata later; heavy AI/FFmpeg belongs on dedicated workers, not the control plane.</p></div>
</div>"""
        return layout('Cloud',body)

    @app.get('/activity')
    def activity_hub():
        body="""<div class='pagehead'><div class='eyebrow'>Operations</div><h1>Activity</h1><div class='lead'>Jobs, failures and recovery history live here. Existing job details remain unchanged.</div></div>
<div class='hubgrid'>
<a class='card hubcard tone-blue' href='/jobs'><b>Jobs & errors</b><span>Open the existing durable job history.</span></a>
<a class='card hubcard' href='/help'><b>Recovery & support</b><span>Inspect failed jobs, retry safely, and review local diagnostic/support boundaries.</span></a>
<div class='card hubcard'><b>Publishing activity</b><span>Will appear here only after Social Lab publishing is implemented.</span></div>
</div>"""
        return layout('Activity',body)

    @app.get("/settings/connections")
    def setup_connections():
        from .connectors import list_provider_connections
        connectors = m12_connector_catalog()
        registry_unavailable = False
        try:
            rows = [dict(r) for r in list_provider_connections()]
        except Exception:
            rows = []
            registry_unavailable = True
        by_provider = {}
        for row in rows:
            provider_key = str(row.get("provider") or "").strip().lower()
            by_provider.setdefault(provider_key, []).append(row)
        cards = []
        for c in connectors:
            provider_id = str(c.get("id") or c.get("name") or "").strip().lower()
            provider_name = str(c.get("name") or provider_id.title() or "Provider")
            provider_rows = by_provider.get(provider_id, [])
            active_rows = [r for r in provider_rows if str(r.get("status") or "").lower() == "connected"]
            connect_available = bool(c.get("connect_available"))
            prereq_ready = bool(c.get("connection_prerequisites_ready", connect_available))
            official_ready = bool(c.get("official_connection_enabled"))
            credential_ready = bool(c.get("credential_storage_ready"))
            credential_raw = c.get("credential_status")
            credential_status = str(credential_raw or ("Ready" if credential_ready else "Unavailable"))
            blocker = str(c.get("connection_blocker") or c.get("blocker") or "")
            card_status = "Registry unavailable" if registry_unavailable else ("Connected" if active_rows else ("Preflight ready" if connect_available else "Blocked"))
            status_color = "#d7a34a" if registry_unavailable else ("#2f9e44" if active_rows else ("#b7791f" if connect_available else "#a0a0a0"))
            badges = [
                f'<span style="padding:3px 8px;border:1px solid #444;border-radius:999px">Credentials: {e(credential_status)}</span>',
                f'<span style="padding:3px 8px;border:1px solid #444;border-radius:999px">Preflight: {"Ready" if prereq_ready else "Blocked"}</span>',
                f'<span style="padding:3px 8px;border:1px solid #444;border-radius:999px">Official OAuth: {"Enabled" if official_ready else "Not enabled"}</span>',
            ]
            if "public_client_id_configured" in c:
                badges.append(f'<span style="padding:3px 8px;border:1px solid #444;border-radius:999px">Client ID: {"Configured" if c.get("public_client_id_configured") else "Missing"}</span>')
            account_parts = []
            for row in provider_rows:
                rid = row.get("id")
                row_status = str(row.get("status") or "unknown")
                account_name = str(row.get("display_name") or row.get("account_id") or "Connected account")
                action = ""
                if row_status.lower() == "connected" and rid is not None:
                    action = f'<form method="post" action="/settings/connections/disconnect?connection_id={e(str(rid))}" style="margin:0"><button type="submit">Disconnect</button></form>'
                else:
                    reason = blocker or "Reconnect is unavailable until official provider OAuth is enabled."
                    action = f'<button type="button" disabled title="{e(reason)}">Reconnect</button>'
                account_parts.append(f'<div style="display:flex;gap:12px;align-items:center;justify-content:space-between;padding:8px 0;border-top:1px solid #333"><span><strong>{e(account_name)}</strong><br><small>{e(row_status)}</small></span>{action}</div>')
            if not provider_rows:
                if registry_unavailable:
                    account_parts.append('<div style="padding-top:10px"><button type="button" disabled>Account state unavailable</button> <a class="btn btn2" href="/settings/connections">Retry</a></div>')
                else:
                    reason = blocker or ("Provider preflight is ready; live authorization is intentionally not started by this build." if connect_available else "Provider prerequisites are not ready.")
                    account_parts.append(f'<div style="padding-top:10px"><button type="button" disabled title="{e(reason)}">Connect</button></div>')
            blocker_html = f'<p class="muted" style="margin:8px 0 0">{e(blocker)}</p>' if blocker else ""
            cards.append(
                f'<div class="card" style="margin:12px 0"><div style="display:flex;justify-content:space-between;gap:16px;align-items:center"><h3 style="margin:0">{e(provider_name)}</h3><span style="color:{status_color}">{e(card_status)}</span></div>'
                + '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">' + "".join(badges) + "</div>"
                + blocker_html + "".join(account_parts) + "</div>"
            )
        registry_banner = (
            '<div class="errbox" style="margin:12px 0"><b>Connection registry temporarily unavailable</b>'
            '<div class="muted" style="margin-top:5px">Archivist could not read saved account state. No account data was changed. '
            'Try again or restart Archivist. Manual handoff and Analytics CSV remain available.</div>'
            '<div style="margin-top:8px"><a class="btn btn2" href="/settings/connections">Try again</a> '
            '<a class="btn btn2" href="/help">Help &amp; Recovery</a></div></div>'
            if registry_unavailable else ""
        )
        body = (
            "<h1>Setup &amp; Connections</h1>"
            + connection_disclosure_html()
            + registry_banner
            + "".join(cards)
            + '<div class="card" style="margin-top:16px"><h3>Manual fallback</h3><p class="muted">Manual handoff and Analytics CSV remain available while official provider OAuth is blocked or not registered.</p><p><a href="/social/manual-handoff">Manual handoff</a> &nbsp; <a href="/social/experiments">Analytics CSV</a></p></div>'
        )
        return layout("Setup & Connections", body)

    @app.post("/settings/connections/disconnect")
    def setup_connection_disconnect():
        from .connectors import disconnect_provider_connection
        connection_id = request.args.get("connection_id", type=int) or request.form.get("connection_id", type=int)
        if not connection_id:
            return redirect("/settings/connections")
        disconnect_provider_connection(connection_id)
        return redirect("/settings/connections", code=303)

    @app.post('/api/discover')
    def discover():
        started=start_discovery();return jsonify({'started':started,'message':'Discovery started' if started else 'Discovery is already running or paused while a foreground job is active'})

    def gallery(mode: str):
        is_import=mode=='import'
        page=max(1,int(request.args.get('page',1))); per=48
        media_type=request.args.get('media_type',''); status=request.args.get('status',''); rights=request.args.get('rights',''); source_kind=request.args.get('source_kind',''); source_id=request.args.get('source_id','').strip(); q=request.args.get('q','').strip(); sort=request.args.get('sort','date_desc')
        imported=request.args.get('imported','no' if is_import and 'imported' not in request.args else '')
        where=['excluded=0','private_path IS NULL','rejected_path IS NULL',"analysis_status<>'private'"]; args=[]
        if is_import:
            # Import is the single source browser: Android, SD/USB and configured local folders.
            where.append("source_kind IN ('android','removable','fixed')")
            if imported=='no': where.append("work_selected=0")
            elif imported=='yes': where.append("work_selected=1")
        else:
            # Library is an explicit working set, not every file that happens to live locally.
            where.append("work_selected=1")
            where.append("(source_kind='fixed' OR staging_path IS NOT NULL OR archive_path IS NOT NULL)")
        if media_type: where.append('media_type=?');args.append(media_type)
        if status: where.append('analysis_status=?');args.append(status)
        if rights=='flagged': where.append("rights_status IN ('review','permission','blocked')")
        elif rights in ('unknown','review','permission','cleared','blocked'): where.append('rights_status=?');args.append(rights)
        if source_kind in ('android','removable','fixed'): where.append('source_kind=?');args.append(source_kind)
        if source_id: where.append('source_id=?');args.append(source_id)
        if q: where.append('(filename LIKE ? OR source_label LIKE ?)');args += [f'%{q}%',f'%{q}%']
        order={'date_desc':'COALESCE(date_taken,mtime,0) DESC','date_asc':'COALESCE(date_taken,mtime,0) ASC','size_desc':'COALESCE(size_bytes,0) DESC','size_asc':'COALESCE(size_bytes,0) ASC','duration_desc':'COALESCE(duration_ms,0) DESC','quality_desc':'COALESCE(quality_score,-1) DESC','name':'filename COLLATE NOCASE'}.get(sort,'COALESCE(date_taken,mtime,0) DESC')
        wh=' AND '.join(where)
        with db() as con:
            source_choices=[]
            if not is_import:
                source_choices=con.execute("""SELECT source_kind,source_id,MAX(source_label) AS source_label,COUNT(*) AS n FROM inventory WHERE excluded=0 AND private_path IS NULL AND rejected_path IS NULL AND analysis_status<>'private' AND work_selected=1 AND source_id IS NOT NULL AND source_id<>'' AND (source_kind='fixed' OR staging_path IS NOT NULL OR archive_path IS NOT NULL) GROUP BY source_kind,source_id ORDER BY CASE source_kind WHEN 'android' THEN 1 WHEN 'removable' THEN 2 WHEN 'fixed' THEN 3 ELSE 9 END, source_label COLLATE NOCASE""").fetchall()
            total=con.execute(f'SELECT COUNT(*) n FROM inventory WHERE {wh}',args).fetchone()['n']
            pages=max(1,(total+per-1)//per);page=min(page,pages);off=(page-1)*per
            rows=con.execute(f'SELECT * FROM inventory WHERE {wh} ORDER BY {order} LIMIT ? OFFSET ?',[*args,per,off]).fetchall()
            next_ids=[]
            if page < pages:
                next_ids=[int(x['id']) for x in con.execute(f'SELECT id FROM inventory WHERE {wh} ORDER BY {order} LIMIT ? OFFSET ?',[*args,per,off+per]).fetchall()]
        for r in rows:
            queue_thumbnail(int(r['id']), priority=0)
            if not is_import and r['media_type']=='video': queue_storyboard(int(r['id']), priority=10)
        for inv_id in next_ids:
            queue_thumbnail(inv_id, priority=20)
            if not is_import: queue_storyboard(inv_id, priority=35)
        def opt(cur,val,label): return f"<option value='{e(val)}' {'selected' if cur==val else ''}>{e(label)}</option>"
        if is_import:
            cfg=load_config()
            phone=phone_snapshot()
            phone_text=(phone.get('model') or phone.get('serial') or 'Android')+' connected' if phone['connected'] else (phone.get('error') or 'not connected')
            local_sources=[s for s in cfg.get('sources',[]) if s.get('enabled',True) and (s.get('kind') or 'fixed')=='fixed']
            removable_now=[d for d in windows_drives() if d.get('kind')=='removable']
            source_error=request.args.get('source_error','').strip()
            source_rows=''.join(
                f"<div class='row space' style='padding:6px 0'><div><b>{e(s.get('label') or s.get('path'))}</b><div class='muted'>{e(s.get('path'))}</div></div>"
                f"<form method='post' action='/import/remove-source'><input type='hidden' name='index' value='{i}'><button class='btn2'>Remove source</button></form></div>"
                for i,s in enumerate(cfg.get('sources',[])) if s.get('enabled',True) and (s.get('kind') or 'fixed')=='fixed'
            )
            if not source_rows:
                source_rows="<div class='muted'>No local folders added yet.</div>"
            err_html=f"<div class='errbox' style='margin-top:8px'>{e(source_error)}</div>" if source_error else ''
            head=f"""<div class='pagehead row space'><div><div class='eyebrow'>Source browser</div><h1>Import</h1><div class='lead'>One place for Android, SD/USB and folders already on this computer. Choose what becomes part of Library.</div></div><div class='row'><div class='device'><span class='device-dot {'online' if phone['connected'] else ''}' data-phone-dot></span><span class='device-status'>Android: <span data-phone-text>{e(phone_text)}</span></span></div><span class='badge ready'>{len(local_sources)} local folder(s)</span><span class='badge'>{len(removable_now)} SD/USB mounted</span><button onclick=\"fetch('/api/discover',{{method:'POST'}}).then(r=>r.json()).then(x=>toast(x.message||'Discovery'))\">Discover all sources</button></div></div>
<div class='card' style='margin-bottom:12px'><div class='row space'><div><b>Import sources</b><div class='muted'>Local folders stay where they are. Android and SD/USB files are copied to Staging only after you select them.</div></div></div><div style='margin-top:8px'>{source_rows}</div><form method='post' action='/import/add-source' class='toolbar' style='margin-top:10px'><input name='label' placeholder='Label (optional)'><input name='path' style='min-width:360px' placeholder='C:\\Users\\User\\Videos or D:\\Footage'><button>Add folder + Discover</button></form>{err_html}</div>"""
            filters=f"""<form method='get' class='toolbar toolpanel'><input name='q' value='{e(q)}' placeholder='Search source media'><select name='media_type'>{opt(media_type,'','Photos + videos')}{opt(media_type,'video','Videos')}{opt(media_type,'image','Photos')}</select><select name='source_kind'>{opt(source_kind,'','All sources')}{opt(source_kind,'android','Android')}{opt(source_kind,'removable','SD/USB')}{opt(source_kind,'fixed','Local folders')}</select><select name='imported'>{opt(imported,'no','Not in Library')}{opt(imported,'yes','In Library')}{opt(imported,'','All source items')}</select><select name='sort'>{opt(sort,'date_desc','Newest')}{opt(sort,'date_asc','Oldest')}{opt(sort,'size_desc','Largest')}{opt(sort,'duration_desc','Longest')}{opt(sort,'name','Name')}</select><button>Apply</button></form>"""
            actions="""<div class='toolbar'><b id='selectedCount'>0 selected</b><span class='badge ready' id='previewCount'>Previews …</span><button class='btn2' id='selectPage'>Select page</button><button class='btn2' id='clearSel'>Clear</button><button id='importBtn'>Add to Library</button><button id='importAnalyzeBtn' class='ok'>Add + Analyze</button></div><div id='actionMsg' class='mode-note'>Local-folder files stay in place. Android/SD files are copied to Staging. Source originals are never deleted.</div>"""
        else:
            head=f"""<div class='pagehead row space'><div><div class='eyebrow'>Working collection</div><h1>Library</h1><div class='lead'>{total} local item(s). This is the media already selected/imported and available for work.</div></div><div class='row'><a class='btn btn2' href='/import'>Import more</a><a class='btn btn2' href='/jobs'>Jobs / errors</a></div></div>"""
            source_options=opt(source_id,'','By source: all')
            for s in source_choices:
                prefix={'android':'Android','removable':'SD/USB','fixed':'Folder'}.get(s['source_kind'],s['source_kind'])
                source_options+=opt(source_id,s['source_id'],f"{prefix}: {s['source_label']} ({s['n']})")
            filters=f"""<form method='get' class='toolbar toolpanel'><input name='q' value='{e(q)}' placeholder='Search Library'><select name='media_type'>{opt(media_type,'','Photos + videos')}{opt(media_type,'video','Videos')}{opt(media_type,'image','Photos')}</select><select name='source_kind'>{opt(source_kind,'','Any origin')}{opt(source_kind,'android','From Android')}{opt(source_kind,'removable','From SD/USB')}{opt(source_kind,'fixed','Existing local')}</select><select name='source_id'>{source_options}</select><select name='status'>{opt(status,'','Any privacy state')}{opt(status,'safe','Privacy safe')}{opt(status,'review','Privacy review')}{opt(status,'duplicate','Duplicate')}{opt(status,'error','Error')}</select><select name='rights'>{opt(rights,'','Any rights state')}{opt(rights,'flagged','Rights flagged')}{opt(rights,'unknown','Rights unknown')}{opt(rights,'review','Rights review')}{opt(rights,'permission','Permission needed')}{opt(rights,'cleared','Rights cleared')}{opt(rights,'blocked','Do not publish')}</select><select name='sort'>{opt(sort,'date_desc','Newest')}{opt(sort,'date_asc','Oldest')}{opt(sort,'size_desc','Largest')}{opt(sort,'size_asc','Smallest')}{opt(sort,'duration_desc','Longest')}{opt(sort,'quality_desc','Quality score')}{opt(sort,'name','Name')}</select><button>Apply</button></form>"""
            actions="""<div class='toolbar'><b id='selectedCount'>0 selected</b><span class='badge ready' id='previewCount'>Previews …</span><button class='btn2' id='selectPage'>Select page</button><button class='btn2' id='clearSel'>Clear</button><button id='analyzeBtn' class='btn2'>Analyze local</button><button id='mediaBrainBtn' class='btn2'>Media Brain</button><button id='convertBulkBtn' class='btn2'>Convert</button><button id='privateBtn' class='warn'>Private forever</button><button id='archiveBtn' class='ok'>Archive</button><button id='rejectBtn' class='danger'>Reject → quarantine</button><button id='removeBtn' class='danger'>Remove from Library</button><select id='rightsPreset'><option value=''>Rights…</option><option value='review'>Review rights</option><option value='permission'>Permission needed</option><option value='cleared'>Rights cleared</option><option value='blocked'>Do not publish</option><option value='reset'>Reset rights status</option></select><button id='rightsBtn' class='btn2'>Apply rights tag</button></div><div id='actionMsg' class='mode-note'>Hover over a video when its storyboard is ready to skim the clip without opening it.</div>"""
        body=head+filters+actions+"<div class='grid'>"
        for r in rows:
            if is_import:
                imp='in-library' if r['work_selected'] else ('local-source' if r['source_kind']=='fixed' else 'source')
            else:
                imp='archived' if r['archive_path'] else ('imported' if r['staging_path'] else ('local' if r['source_kind']=='fixed' else r['import_status']))
            qcls='quality-'+str(r['quality_status']) if r['quality_status'] in ('ok','review') else ''
            extra=(f"<span class='badge qualityBadge {qcls}'>quality {e(r['quality_status'])} {e(r['quality_score'])}</span>" if (not is_import and r['quality_status']!='unreviewed') else '')
            rights_badge=(f"<span class='badge rightsBadge rights-{e(r['rights_status'])}'>rights {e(r['rights_status'])}</span>" if not is_import else '')
            audio=("<span class='badge audioflag'>audio</span>" if (not is_import and r['rights_audio_present']) else '')
            analysis=(f"<span class='badge {e(r['analysis_status'])} analysisBadge'>{e(r['analysis_status'])}</span>" if not is_import else '')
            storyboard_err=("<span class='badge error' title='Open item for details'>preview error</span>" if (not is_import and r['media_type']=='video' and r['storyboard_status']=='unavailable') else '')
            story=(f"<span class='storybadge'>{int(r['storyboard_frames'] or 0)}/8 frames</span>" if (not is_import and r['media_type']=='video' and int(r['storyboard_frames'] or 0)>0) else ("<span class='storybadge'>preview…</span>" if (not is_import and r['media_type']=='video') else ''))
            body+=f"""<div class='media-card' data-id='{r['id']}' data-type='{e(r['media_type'])}'><input class='check itemCheck' type='checkbox' value='{r['id']}'>{story}<div class='thumb'><img class='mediaThumb' data-id='{r['id']}' loading='eager' decoding='async' src='/thumb/{r['id']}'></div><div class='meta'><div class='name' title='{e(r['filename'])}'>{e(r['filename'])}</div><div class='small'>{e(r['source_label'])} · {human_bytes(r['size_bytes'])} · {human_duration(r['duration_ms'])}</div><span class='badge {e(imp)} importBadge'>{e(imp)}</span>{analysis}{extra}{rights_badge}{audio}{storyboard_err}<div><a class='btn btn2 openLink' style='padding:4px 7px;font-size:11px' href='/item/{r['id']}'>Open</a></div></div></div>"""
        body+='</div>'
        if not rows: body+="<div class='empty'>Nothing here with the current filters.</div>"
        qs={k:v for k,v in request.args.items() if k!='page'}
        body+=page_nav(page,pages,qs)
        key='archivist.import.selected.v1' if is_import else 'archivist.library.selected.v3'
        mode_js='import' if is_import else 'library'
        script=f"""
const MODE={json.dumps(mode_js)};const KEY={json.dumps(key)};const cards=[...document.querySelectorAll('.media-card')],checks=[...document.querySelectorAll('.itemCheck')],count=document.getElementById('selectedCount'),msg=document.getElementById('actionMsg');
let selected=new Set();try{{selected=new Set(JSON.parse(localStorage.getItem(KEY)||'[]').map(String))}}catch(e){{}}
function save(){{localStorage.setItem(KEY,JSON.stringify([...selected]))}}function sync(){{cards.forEach((c,i)=>{{let id=String(checks[i].value),on=selected.has(id);checks[i].checked=on;c.classList.toggle('selected',on)}});if(count)count.textContent=selected.size+' selected'}}function setSel(ch,on){{let id=String(ch.value);on?selected.add(id):selected.delete(id);save();sync()}}
cards.forEach((c,i)=>c.addEventListener('click',ev=>{{if(ev.target.closest('.openLink')||ev.target===checks[i])return;setSel(checks[i],!selected.has(String(checks[i].value)))}}));checks.forEach(ch=>ch.addEventListener('change',()=>setSel(ch,ch.checked)));const sp=document.getElementById('selectPage'),cs=document.getElementById('clearSel');if(sp)sp.onclick=()=>{{checks.forEach(x=>selected.add(String(x.value)));save();sync()}};if(cs)cs.onclick=()=>{{selected.clear();save();sync()}};
let actionBusy=false;async function act(action,confirmText){{if(actionBusy)return;if(!selected.size){{toast('Select files first');return}}if(confirmText&&!confirm(confirmText))return;actionBusy=true;if(msg)msg.textContent='Creating durable job for '+selected.size+' selected files…';const ids=[...selected].map(Number);try{{let r=await fetch('/api/selection-action',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{action,ids}})}});let x=await r.json();if(!r.ok){{if(msg)msg.textContent='ERROR: '+(x.error||r.statusText);toast('ERROR: '+(x.error||r.statusText));return}}if(x.job_id){{selected.clear();save();sync();if(msg)msg.textContent='Job #'+x.job_id+' accepted.';toast('Job #'+x.job_id+' accepted')}}else{{if(msg)msg.textContent=x.message||'Done';toast(x.message||'Done');location.reload()}}}}finally{{actionBusy=false}}}}
const ib=document.getElementById('importBtn'),iab=document.getElementById('importAnalyzeBtn'),an=document.getElementById('analyzeBtn'),mb=document.getElementById('mediaBrainBtn'),cb=document.getElementById('convertBulkBtn'),pb=document.getElementById('privateBtn'),ab=document.getElementById('archiveBtn'),rbj=document.getElementById('rejectBtn'),rml=document.getElementById('removeBtn');if(ib)ib.onclick=()=>act('import');if(iab)iab.onclick=()=>act('import_analyze');if(an)an.onclick=()=>act('analyze');if(mb)mb.onclick=()=>act('media_brain');if(cb)cb.onclick=()=>{{const ids=cards.filter(c=>selected.has(c.dataset.id)&&c.dataset.type==='video').map(c=>c.dataset.id);if(!ids.length){{toast('Select local videos first');return}}location.href='/convert?ids='+encodeURIComponent(ids.join(','))}};if(pb)pb.onclick=()=>act('private','Mark selected Private forever?');if(ab)ab.onclick=()=>act('archive','Archive selected local/staged files? Source-device originals are never deleted.');if(rbj)rbj.onclick=()=>act('reject','Move selected Staging copies to Rejected quarantine and hide them? Phone/SD originals stay untouched.');if(rml)rml.onclick=()=>act('remove','Remove selected items from Library? Imported Staging copies move to the Rejected / Removed from Library folder (delete them there when you are sure). Source originals and local/archive files stay untouched.');sync();
async function tagRights(){{const el=document.getElementById('rightsPreset');if(!el)return;const preset=el.value;if(!preset){{toast('Choose a rights tag');return}}if(!selected.size){{toast('Select files first');return}}const ids=[...selected].map(Number);const r=await fetch('/api/selection-action',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{action:'rights',ids,preset}})}});const x=await r.json();if(!r.ok){{toast('ERROR: '+(x.error||r.statusText));return}}toast(x.message||'Rights updated');refreshVisible()}}const rbt=document.getElementById('rightsBtn');if(rbt)rbt.onclick=tagRights;
async function refreshVisible(){{try{{const ids=cards.map(c=>c.dataset.id).join(',');if(!ids)return;const r=await fetch('/api/items?ids='+ids,{{cache:'no-store'}}),data=await r.json();for(const c of cards){{const d=data[c.dataset.id];if(!d)continue;const ib=c.querySelector('.importBadge'),ab=c.querySelector('.analysisBadge');if(ib){{ib.textContent=d.import_state;ib.className='badge importBadge '+d.import_state}}if(ab){{ab.textContent=d.analysis_status;ab.className='badge analysisBadge '+d.analysis_status}}let qb=c.querySelector('.qualityBadge');if(d.quality_status&&d.quality_status!=='unreviewed'&&MODE==='library'){{if(!qb&&ab){{qb=document.createElement('span');qb.className='badge qualityBadge';ab.insertAdjacentElement('afterend',qb)}}if(qb){{qb.textContent='quality '+d.quality_status+(d.quality_score!=null?' '+d.quality_score:'');qb.className='badge qualityBadge quality-'+d.quality_status}}}}let rr=c.querySelector('.rightsBadge');if(rr){{rr.textContent='rights '+(d.rights_status||'unknown');rr.className='badge rightsBadge rights-'+(d.rights_status||'unknown')}}}}}}catch(e){{}}setTimeout(refreshVisible,1200)}}refreshVisible();
const previewCount=document.getElementById('previewCount'),previewImgs=[...document.querySelectorAll('.mediaThumb')];async function refreshPreviews(){{if(!previewImgs.length){{if(previewCount)previewCount.textContent='Previews 0/0';return}}try{{const ids=previewImgs.map(x=>x.dataset.id).join(',');const r=await fetch('/api/thumb-status?ids='+ids,{{cache:'no-store'}}),x=await r.json();const ready=new Set((x.ready||[]).map(String));for(const img of previewImgs){{const id=String(img.dataset.id);if(ready.has(id)&&img.dataset.ready!=='1'){{img.dataset.ready='1';img.src='/thumb/'+id+'?v='+(x.generation||Date.now())}}}}const unavailable=Number(x.unavailable_count||0),pending=Number(x.pending_count||0),readyN=Number(x.ready_count||0);if(previewCount)previewCount.textContent='Previews '+readyN+'/'+previewImgs.length+(unavailable?' · '+unavailable+' unavailable':pending?' · '+pending+' loading':'');if(pending>0)setTimeout(refreshPreviews,800)}}catch(e){{if(previewCount)previewCount.textContent='Previews status unavailable';setTimeout(refreshPreviews,2000)}}}}refreshPreviews();
if(MODE==='library'){{const videoCards=cards.filter(c=>c.dataset.type==='video');async function refreshStoryboards(){{if(!videoCards.length)return;try{{const ids=videoCards.map(c=>c.dataset.id).join(',');const r=await fetch('/api/storyboard-status?ids='+ids,{{cache:'no-store'}}),x=await r.json();for(const c of videoCards){{const st=(x.items||{{}})[c.dataset.id],b=c.querySelector('.storybadge');if(st&&st.ready&&st.count>1){{c.dataset.storyReady='1';c.dataset.storyCount=String(st.count);if(b){{b.style.display='block';b.textContent=st.count+' frames'}}}}}}if(Number(x.pending_count||0)>0)setTimeout(refreshStoryboards,1200)}}catch(e){{setTimeout(refreshStoryboards,2500)}}}}for(const c of videoCards){{let timer=null,idx=0;const img=c.querySelector('.mediaThumb');c.addEventListener('mouseenter',async()=>{{if(!img)return;const id=c.dataset.id;if(c.dataset.storyReady!=='1'){{try{{await fetch('/api/storyboard/'+id+'/queue',{{method:'POST'}})}}catch(e){{}}return}}const n=Number(c.dataset.storyCount||0);if(n<2)return;idx=0;clearInterval(timer);timer=setInterval(()=>{{img.src='/storyboard/'+id+'/'+idx+'?v='+Date.now();idx=(idx+1)%n}},420)}});c.addEventListener('mouseleave',()=>{{clearInterval(timer);timer=null;if(img)img.src='/thumb/'+c.dataset.id+'?v='+Date.now()}})}}refreshStoryboards();}}
"""
        return layout('Import' if is_import else 'Library',body,script)



    @app.get('/search')
    def smart_search():
        q=request.args.get('q','').strip()[:240]
        try: page=max(1,int(request.args.get('page','1') or 1))
        except Exception: page=1
        per=48
        data=semantic_search(q,limit=500) if q else {'results':[],'intents':[],'tokens':[],'index_count':0,'model':'signals_v1'}
        rows=data.get('results') or [];total=len(rows);pages=max(1,(total+per-1)//per);page=min(page,pages);shown=rows[(page-1)*per:page*per]
        examples=[('best vertical videos','Best vertical'),('high motion videos','High motion'),('dark videos','Dark / night'),('drone videos','Drone'),('long Android videos','Long Android')]
        chips=''.join(f"<a class='btn btn2' style='padding:6px 9px' href='/search?q={urllib.parse.quote_plus(x)}'>{e(label)}</a>" for x,label in examples)
        cap=', '.join(semantic_capabilities())
        body=f"""<div class='pagehead'><div class='eyebrow'>Local Search / M7</div><h1>Search your footage</h1>
<div class='lead'>Describe useful properties of the media. Search runs locally and uses Archivist's existing Media Brain and catalog signals.</div></div>
<form method='get' action='/search' class='card row' style='padding:12px'><input name='q' value='{e(q)}' autofocus style='min-width:min(680px,75vw);font-size:16px' placeholder='e.g. best vertical high-motion videos'><button>Search</button>{("<a class='btn btn2' href='/search'>Clear</a>" if q else "")}</form>
<div class='toolbar'>{chips}</div>
<div class='mode-note'>Understands: {e(cap)}. Exact people/objects/scenes that are not already in local text are not vision-indexed yet; this page is the stable foundation for a future optional local visual-embedding layer.</div>"""
        if q:
            intent_txt=', '.join(data.get('intents') or []) or 'text'
            body+=f"<div class='row space section-title'><span>{total} result(s)</span><span class='badge'>signals v1 · {e(intent_txt)}</span></div><div class='grid'>"
            for r in shown:
                why=' · '.join(r.get('why') or []) or 'text / Media Brain relevance'
                best=(f"<a class='btn btn2 openLink' style='padding:4px 7px;font-size:11px' href='/clip/{int(r['best_clip_id'])}?back=item'>Best clip</a>" if r.get('best_clip_id') else '')
                tags=''.join(f"<span class='badge'>{e(x.replace('_',' '))}</span>" for x in (r.get('tags') or [])[:5])
                body+=f"""<div class='media-card'><div class='thumb'><img loading='lazy' src='/thumb/{int(r['id'])}'></div><div class='meta'>
<div class='row space'><span class='badge ready'>match {float(r.get('semantic_score') or 0):.1f}</span><span class='small'>{human_duration(r.get('duration_ms'))}</span></div>
<div class='name' title='{e(r.get('filename'))}'>{e(r.get('filename'))}</div><div class='small'>{e(r.get('source_label'))} · {human_bytes(r.get('size_bytes'))}</div>
<div class='small' style='margin-top:5px' title='{e(why)}'>{e(why)}</div><div>{tags}</div>
<div class='row' style='margin-top:7px'><a class='btn btn2 openLink' style='padding:4px 7px;font-size:11px' href='/item/{int(r['id'])}'>Open</a>{best}</div></div></div>"""
            body+='</div>'
            if not shown:body+="<div class='empty'>No match yet. Try a property such as vertical, high motion, dark, drone, long, Android, audio, safe, or best. Object/people vision search comes in the next semantic layer.</div>"
            body+=page_nav(page,pages,{'q':q})
        else:
            body+="<div class='empty' style='margin-top:18px'>Try one of the examples above. Nothing leaves this computer.</div>"
        return layout('Search',body)

    @app.get('/api/search')
    def smart_search_api():
        q=request.args.get('q','').strip()[:240]
        try: limit=min(200,max(1,int(request.args.get('limit','50') or 50)))
        except Exception: limit=50
        data=semantic_search(q,limit=limit)
        out=[]
        for r in data.get('results') or []:
            out.append({'id':int(r['id']),'media_type':r.get('media_type'),'duration_ms':r.get('duration_ms'),
                        'semantic_score':r.get('semantic_score'),'why':r.get('why'),'tags':r.get('tags'),
                        'best_clip_id':r.get('best_clip_id'),'best_clip_score':r.get('best_clip_score')})
        return jsonify({'query':data.get('query'),'model':data.get('model'),'intents':data.get('intents'),
                        'tokens':data.get('tokens'),'index_count':data.get('index_count'),'results':out})

    @app.get('/best')
    def best_moments():
        rows=best_clips(160)
        body="<div class='pagehead row space'><div><div class='eyebrow'>Media Brain</div><h1>Best Moments</h1><div class='lead'>Virtual clips ranked from your existing footage. Nothing here creates a new video file.</div></div><a class='btn btn2' href='/library?media_type=video'>Videos</a></div><div class='grid'>"
        for r in rows:
            start=r['start_ms']/1000.0; end=r['end_ms']/1000.0
            body+=f"""<div class='media-card'><div class='thumb'><img loading='lazy' src='/clip-preview/{r['id']}'></div><div class='meta'><div class='row space'><span class='badge {'safe' if r['label']=='best' else 'ready'}'>{e(r['label'])} {e(r['score'])}</span><span class='small'>{int(start//60)}:{int(start%60):02d}–{int(end//60)}:{int(end%60):02d}</span></div><div class='name'>{e(r['filename'])}</div><div class='small'>{e(r['reason'])}</div><div><a class='btn btn2 openLink' style='padding:4px 7px;font-size:11px' href='/clip/{r['id']}?back=best'>Open clip</a></div></div></div>"""
        body+="</div>"
        if not rows: body+="<div class='empty'>No Media Brain clips yet. Select local videos in Library and run Media Brain.</div>"
        return layout('Best Moments',body)


    @app.get('/clip/<int:clip_id>')
    def virtual_clip(clip_id):
        with db() as con:
            r=con.execute("""SELECT vc.*,i.filename,i.width,i.height,i.source_label,i.media_type,i.work_selected,i.excluded,
                i.path,i.staging_path,i.archive_path,i.private_path,i.duration_ms
                FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id
                WHERE vc.id=? AND i.excluded=0""",(clip_id,)).fetchone()
            if not r:
                return 'Clip not found',404
            crops=[dict(x) for x in con.execute("""SELECT * FROM crop_plans WHERE clip_id=?
                ORDER BY CASE aspect WHEN '16:9' THEN 1 WHEN '4:5' THEN 2 WHEN '1:1' THEN 3 ELSE 4 END""",(clip_id,)).fetchall()]
        d=dict(r)
        inv_id=int(d['inventory_id'])
        start=float(d['start_ms'])/1000.0
        end=float(d['end_ms'])/1000.0
        clip_len=max(.05,end-start)
        ratios={'16:9':16/9,'4:5':4/5,'1:1':1.0,'9:16':9/16}
        try:
            src_ratio=float(d.get('width') or 0)/float(d.get('height') or 1)
            if src_ratio <= 0:
                src_ratio=16/9
        except Exception:
            src_ratio=16/9
        crop_map={x['aspect']:x for x in crops}
        default_aspect=min(crop_map.keys(),key=lambda a:abs(ratios.get(a,1)-src_ratio)) if crop_map else 'original'
        preset=(crops[0].get('preset') if crops else None) or 'general'
        back=request.args.get('back','best')
        back_url=f"/item/{inv_id}" if back=='item' else '/best'
        back_label='Video' if back=='item' else 'Best Moments'
        def mm(s):
            return f"{int(s//60)}:{int(s%60):02d}"
        plans={a:{'x':float(x['x']),'y':float(x['y']),'w':float(x['w']),'h':float(x['h']),
                  'confidence':float(x['confidence'] or 0),'preset':x['preset']} for a,x in crop_map.items()}
        v2_enabled=request.args.get('smart_crop_v2')=='1' or os.environ.get('ARCHIVIST_SMART_CROP_V2')=='1'
        trajectories=trajectories_for_clip(clip_id) if v2_enabled else {}
        trajectory_payload={a:{k:v for k,v in t.items() if k not in ('id','clip_id','created_at','updated_at')} for a,t in trajectories.items()}
        clip_config=json.dumps({'start':start,'end':end,'length':clip_len,'sourceRatio':src_ratio,
                                'defaultAspect':default_aspect,'plans':plans,'smartCropV2':v2_enabled,
                                'trajectories':trajectory_payload}).replace('<','\\u003c')
        body=render_template('virtual_clip.html',clip_config=clip_config,clip_id=clip_id,inv_id=inv_id,
                             filename=d['filename'],start_label=mm(start),end_label=mm(end),
                             length_label=mm(clip_len),clip_len=clip_len,score=d['score'],label=d['label'],
                             reason=d['reason'] or '',back_url=back_url,back_label=back_label,
                             src_ratio=src_ratio,plans=plans,preset=preset,show_car_rebuild=preset!='car',
                             smart_crop_v2=v2_enabled,trajectories=trajectory_payload,
                             review_url=f"/clip/{clip_id}?back={urllib.parse.quote(back)}&smart_crop_v2=1")
        export_opts="<option value='original'>Original framing</option>"+''.join(f"<option value='{e(a)}'>{e(a)} Smart Crop</option>" for a in ('16:9','4:5','1:1','9:16') if a in plans)
        body+=f"<div class='card' style='margin-top:12px'><div class='eyebrow'>M8 / Local Render</div><h3>Export clip</h3><div class='muted'>Create a new MP4 from this virtual clip. Original footage stays untouched. Smart Crop export uses the approved static crop plan for this first render layer.</div><form method='post' action='/clip/{clip_id}/export' class='toolbar'><select name='aspect'>{export_opts}</select><button>Export MP4</button></form></div>"
        return layout('Virtual clip',body,script_srcs=('/static/virtual_clip.js',))

    @app.post('/api/clip/<int:clip_id>/trajectory/<aspect>')
    def save_trajectory(clip_id,aspect):
        aspect=urllib.parse.unquote(aspect)
        p=request.get_json(silent=True) or {}
        try:
            result=save_crop_trajectory(clip_id,aspect,p.get('keyframes') or [],preset=str(p.get('preset') or 'general'),
                status=str(p.get('status') or 'draft'),confidence=float(p.get('confidence') or 0),
                smoothing=float(p.get('smoothing') or .35),max_pan_per_second=float(p.get('max_pan_per_second') or .35),
                max_zoom_per_second=float(p.get('max_zoom_per_second') or .25),source='manual')
            return jsonify({'ok':True,'trajectory':result})
        except ValueError as exc:
            return jsonify({'error':str(exc)}),400

    @app.post('/api/clip/<int:clip_id>/track/<aspect>')
    def track_trajectory(clip_id,aspect):
        aspect=urllib.parse.unquote(aspect)
        with db() as con:
            row=con.execute("""SELECT vc.*,i.path,i.staging_path,i.archive_path,i.private_path,i.duration_ms
                FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id WHERE vc.id=? AND i.excluded=0""",(clip_id,)).fetchone()
            plan=con.execute("SELECT * FROM crop_plans WHERE clip_id=? AND aspect=? ORDER BY id DESC LIMIT 1",(clip_id,aspect)).fetchone()
        if not row or not plan: return jsonify({'error':'Clip or crop plan not found'}),404
        local=next((Path(row[k]) for k in ('staging_path','archive_path','private_path','path') if row[k] and Path(row[k]).exists()),None)
        if not local: return jsonify({'error':'Local video file is unavailable'}),409
        try:
            duration=max(float(row['duration_ms'] or 0)/1000.0,float(row['end_ms'])/1000.0)
            result=build_tracked_trajectory(clip_id,aspect,dict(plan),local,float(row['start_ms'])/1000.0,float(row['end_ms'])/1000.0,duration,str(plan['preset'] or 'general'))
            return jsonify({'ok':True,'trajectory':result})
        except Exception as exc:
            return jsonify({'error':str(exc)[:500]}),400

    @app.post('/api/clip/<int:clip_id>/trajectory-status/<aspect>')
    def trajectory_status(clip_id,aspect):
        aspect=urllib.parse.unquote(aspect); p=request.get_json(silent=True) or {}; status=str(p.get('status') or '')
        current=trajectory_for_clip(clip_id,aspect)
        if not current: return jsonify({'error':'Build or save a trajectory first'}),404
        try:
            result=save_crop_trajectory(clip_id,aspect,current['keyframes'],preset=current['preset'],status=status,
                confidence=float(current.get('confidence') or 0),smoothing=float(current.get('smoothing') or .35),
                max_pan_per_second=float(current.get('max_pan_per_second') or .35),max_zoom_per_second=float(current.get('max_zoom_per_second') or .25),source='manual_review')
            return jsonify({'ok':True,'trajectory':result})
        except ValueError as exc:
            return jsonify({'error':str(exc)}),400


    @app.post('/clip/<int:clip_id>/export')
    def clip_export(clip_id):
        aspect=request.form.get('aspect','original')
        try:
            result=export_clip(clip_id,aspect)
            body=f"<div class='pagehead'><div class='eyebrow'>M8 / Local Render</div><h1>Export complete</h1><div class='lead'>A new derived MP4 was created in Archivist Exports. The source video was not modified.</div></div><div class='card'><div class='row space'><div><b>{e(aspect)}</b><div class='muted'>{human_bytes(result['output_bytes'])}</div></div><a class='btn' href='/export-file/{int(result['export_id'])}'>Open exported MP4</a></div><div style='margin-top:12px'><a class='btn btn2' href='/clip/{clip_id}'>Back to clip</a></div></div>"
            return layout('Export complete',body)
        except Exception as exc:
            return layout('Export failed',f"<div class='card'><h2>Export failed</h2><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/clip/{clip_id}'>Back</a></div>"),400

    @app.get('/export-file/<int:export_id>')
    def export_file(export_id):
        x=export_by_id(export_id)
        if not x:return 'Not found',404
        p=Path(x['output_path'])
        if not p.exists() or p.parent.resolve()!=EXPORTS.resolve():return 'Export unavailable',404
        return send_file(p,mimetype='video/mp4',conditional=True)


    @app.get('/composer')
    def composer_home():
        ensure_composer_schema();clips=best_clips(80)
        body="<div class='pagehead'><div class='eyebrow'>M8 / Content Composer</div><h1>Content Composer</h1><div class='lead'>Select existing Virtual Clips, choose one target aspect and build a local composition. Renders run locally in the background with normalized stereo audio; silent clips receive silence so every segment concatenates reliably. Originals stay untouched.</div></div><form method='post' action='/composer/create'><div class='card toolbar'><input name='title' placeholder='Composition title' maxlength='80'><select name='aspect'><option>16:9</option><option>9:16</option><option>4:5</option><option>1:1</option></select><button>Create composition</button><span class='muted'>Up to 20 clips / 180 seconds</span></div><div class='grid'>"
        for r in clips:
            st=float(r['start_ms'])/1000;en=float(r['end_ms'])/1000
            body+=f"<label class='media-card'><input class='check' type='checkbox' name='clip_id' value='{int(r['id'])}'><div class='thumb'><img loading='lazy' src='/clip-preview/{int(r['id'])}'></div><div class='meta'><div class='row space'><b>{e(r['label'])} {e(r['score'])}</b><span class='small'>{int(st//60)}:{int(st%60):02d}–{int(en//60)}:{int(en%60):02d}</span></div><div class='name'>{e(r['filename'])}</div></div></label>"
        body+="</div></form>"
        with db() as con: existing=[dict(x) for x in con.execute("SELECT id,title,aspect,status,output_bytes FROM compositions ORDER BY id DESC LIMIT 20").fetchall()]
        if existing:
            body+="<div class='section-title'>Recent compositions</div><div class='jobs'>"
            for x in existing:body+=f"<a class='card jobrow' href='/composer/{int(x['id'])}'><b>#{int(x['id'])}</b><span>{e(x['title'])}</span><span class='badge {e(x['status'])}'>{e(x['status'])}</span><span>{e(x['aspect'])} · {human_bytes(x['output_bytes']) if x['output_bytes'] else 'not rendered'}</span></a>"
            body+="</div>"
        return layout('Content Composer',body)

    @app.post('/composer/create')
    def composer_create():
        try:
            cid=create_composition(request.form.getlist('clip_id'),request.form.get('aspect','16:9'),request.form.get('title',''))
            return redirect(f'/composer/{cid}')
        except Exception as exc:return layout('Composer',f"<div class='card'><h2>Could not create composition</h2><div class='errbox'>{e(str(exc)[:500])}</div><a class='btn btn2' href='/composer'>Back</a></div>"),400

    @app.get('/composer/<int:cid>')
    def composer_detail_page(cid):
        c=composition_detail(cid)
        if not c:return 'Not found',404
        body=f"<div class='pagehead row space'><div><div class='eyebrow'>M8 / Content Composer</div><h1>{e(c['title'])}</h1><div class='lead'>{e(c['aspect'])} · {len(c['items'])} clips · {e(c['status'])}</div></div><a class='btn btn2' href='/composer'>Composer</a></div><div class='jobs'>"
        for x in c['items']:
            pos=int(x['position']);st=float(x['start_ms'])/1000;en=float(x['end_ms'])/1000
            body+=f"<div class='card jobrow'><b>{pos}</b><img src='/clip-preview/{int(x['id'])}' style='width:88px;height:50px;object-fit:cover;border-radius:7px'><span>{e(x['filename'])}<div class='muted'>{int(st//60)}:{int(st%60):02d}–{int(en//60)}:{int(en%60):02d}</div></span><span class='row'><form method='post' action='/composer/{cid}/move'><input type='hidden' name='position' value='{pos}'><input type='hidden' name='direction' value='up'><button class='btn2'>↑</button></form><form method='post' action='/composer/{cid}/move'><input type='hidden' name='position' value='{pos}'><input type='hidden' name='direction' value='down'><button class='btn2'>↓</button></form></span></div>"
        body+="</div><div class='card' style='margin-top:12px'><b>Render composition</b><div class='muted'>Local MP4 rendered in the background. Every segment is normalized to the target aspect and stereo AAC; silent clips receive a silent track. Existing Smart Crop plans are used when available.</div><form method='post' action='/composer/%d/render' style='margin-top:10px'><button>Render MP4</button></form>"%cid
        if c.get('output_path') and Path(c['output_path']).exists():body+=f"<a class='btn btn2' style='margin-left:8px' href='/composition-file/{cid}'>Open latest MP4</a>"
        if c.get('last_error'):body+=f"<div class='errbox'>{e(c['last_error'])}</div>"
        body+="</div>"
        script="setTimeout(()=>location.reload(),1500);" if c.get('status') in ('queued','rendering') else ''
        return layout('Composition',body,script)

    @app.post('/composer/<int:cid>/move')
    def composer_move(cid):
        move_composer_item(cid,request.form.get('position','1'),request.form.get('direction','down'));return redirect(f'/composer/{cid}')

    @app.post('/composer/<int:cid>/render')
    def composer_render(cid):
        try:start_composer_render(cid)
        except Exception:pass
        return redirect(f'/composer/{cid}')

    @app.get('/composition-file/<int:cid>')
    def composition_file(cid):
        c=composition_detail(cid)
        if not c or not c.get('output_path'):return 'Not found',404
        p=Path(c['output_path'])
        if not p.exists() or p.parent.resolve()!=COMPOSER_EXPORTS.resolve():return 'Unavailable',404
        return send_file(p,mimetype='video/mp4',conditional=True)

    @app.get('/import')
    def import_page():
        return gallery('import')


    @app.get('/convert')
    def convert_page():
        q=request.args.get('q','').strip()
        source_id=request.args.get('source_id','').strip()
        source_kind=request.args.get('source_kind','').strip()
        scope=request.args.get('scope','all').strip() or 'all'
        sort=request.args.get('sort','date_desc').strip() or 'date_desc'
        preselect_ids={int(x) for x in request.args.get('ids','').split(',') if x.strip().isdigit()}
        where=["excluded=0","media_type='video'","private_path IS NULL","rejected_path IS NULL","COALESCE(analysis_status,'')<>'private'"]
        args=[]
        if scope=='library': where.append("work_selected=1")
        if q:
            where.append("filename LIKE ?");args.append('%'+q+'%')
        if source_kind:
            where.append("source_kind=?");args.append(source_kind)
        if source_id:
            where.append("source_id=?");args.append(source_id)
        order_map={'date_desc':'COALESCE(date_taken,mtime,0) DESC,id DESC','date_asc':'COALESCE(date_taken,mtime,0) ASC,id ASC','size_desc':'COALESCE(size_bytes,0) DESC','size_asc':'COALESCE(size_bytes,0) ASC','duration_desc':'COALESCE(duration_ms,0) DESC','name':'LOWER(filename) ASC','source':"LOWER(COALESCE(source_label,source_id,'')) ASC,LOWER(filename) ASC"}
        order_sql=order_map.get(sort,order_map['date_desc'])
        page=max(1,int(request.args.get('page',1) or 1)); per=120
        where_sql=' AND '.join(where)
        with db() as con:
            source_rows=con.execute("SELECT source_id,MAX(source_label) source_label FROM inventory WHERE "+where_sql+" GROUP BY source_id ORDER BY LOWER(COALESCE(MAX(source_label),source_id,''))",args).fetchall()
            if preselect_ids:
                chosen=sorted(preselect_ids)
                marks=','.join('?' for _ in chosen)
                raw_rows=con.execute("SELECT * FROM inventory WHERE "+where_sql+" AND id IN ("+marks+") ORDER BY "+order_sql,args+chosen).fetchall()
                total_catalog=len(raw_rows); pages=1; page=1
            else:
                total_catalog=int(con.execute("SELECT COUNT(*) n FROM inventory WHERE "+where_sql,args).fetchone()['n'])
                pages=max(1,(total_catalog+per-1)//per); page=min(page,pages)
                raw_rows=con.execute("SELECT * FROM inventory WHERE "+where_sql+" ORDER BY "+order_sql+" LIMIT ? OFFSET ?",args+[per,(page-1)*per]).fetchall()
        available_paths={}
        for r in raw_rows:
            local_path=next((r[k] for k in ('staging_path','archive_path','path') if r[k] and Path(r[k]).exists()),None)
            if local_path: available_paths[int(r['id'])]=local_path
        local=[r for r in raw_rows if int(r['id']) in available_paths]
        sources={}
        for r in source_rows:
            sid=r['source_id'] or ''
            sources[sid]=r['source_label'] or sid or 'Local'
        skipped_preselected=max(0,len(preselect_ids)-len(local)) if preselect_ids else 0
        total_local=len(local)
        latest=convert_job_snapshot()
        srcopts="<option value=''>All local sources</option>"+''.join(f"<option value='{e(k)}' {'selected' if k==source_id else ''}>{e(v)}</option>" for k,v in sorted(sources.items(),key=lambda x:x[1].lower()))
        cards=''
        for r in local:
            local_path=available_paths.get(int(r['id']))
            available=bool(local_path)
            if available: queue_thumbnail(int(r['id']),priority=0)
            prechecked='checked' if (available and int(r['id']) in preselect_ids) else ''
            disabled='' if available else 'disabled'
            unavailable='' if available else "<div class='small error'>Local file unavailable — reconnect the source or restore the file.</div>"
            cards+=f"""<label class='card convertRow' data-size='{int(r['size_bytes'] or 0)}' data-duration-ms='{int(r['duration_ms'] or 0)}' data-width='{int(r['width'] or 0)}' data-height='{int(r['height'] or 0)}' style='display:grid;grid-template-columns:auto 92px 1fr auto;gap:12px;align-items:center;padding:10px;cursor:pointer;opacity:{1 if available else .55}'>
<input type='checkbox' name='ids' value='{int(r['id'])}' class='convertCheck' data-size='{int(r['size_bytes'] or 0)}' data-duration-ms='{int(r['duration_ms'] or 0)}' data-width='{int(r['width'] or 0)}' data-height='{int(r['height'] or 0)}' {prechecked} {disabled}>
<div class='convertThumbWrap' style='width:92px;height:58px;position:relative'><img class='convertThumb' data-id='{int(r['id'])}' src='/thumb/{int(r['id'])}' style='width:92px;height:58px;object-fit:cover;border-radius:7px;background:#090b0e'><span class='storybadge convertStoryBadge' style='left:4px;top:4px'></span></div>
<div style='min-width:0'><b style='display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{e(r['filename'])}</b>
<div class='small muted'>{e(r['source_label'])} · {human_duration(r['duration_ms'])} · {human_bytes(r['size_bytes'])}</div>{unavailable}</div>
<div style='text-align:right'><span class='badge'>#{int(r['id'])}</span><div class='small muted estimateOne' style='margin-top:5px'></div></div></label>"""
        if not cards:
            cards=("<div class='card muted'>None of the selected videos are currently accessible. Restore/reconnect the source, or choose another local video.</div>" if preselect_ids else "<div class='card muted'>No accessible videos on this catalog page. Reconnect/restore the source, choose another page, or clear the filter.</div>")
        selection_notice=(f"<div class='card' style='border-color:#6f5c31;background:#1d1a12'><b>{skipped_preselected} selected video{'s' if skipped_preselected!=1 else ''} skipped</b><div class='small muted'>The item is no longer eligible for Convert or its local file is not currently accessible, so it was skipped safely.</div></div>" if skipped_preselected else "")
        active=''
        if latest:
            terminal=str(latest.get('status') or '') in ('finished','failed','cancelled','partial')
            if terminal:
                tone='error' if str(latest.get('status')) in ('failed','cancelled') else 'ready'
                err=(f"<div class='small error' style='margin-top:6px'>{e(latest.get('error'))}</div>" if latest.get('error') and latest.get('error')!='interrupted_by_restart' else '')
                active=f"<div class='card'><div class='row space'><b>Last converter job #{int(latest['id'])}</b><span class='badge {tone}'>{e(latest.get('status'))}</span></div><div class='muted'>{e(latest.get('message') or latest.get('status'))}</div>{err}</div>"
            else:
                active=f"<div id='convertStatus' class='card' data-job='{int(latest['id'])}'><b>Converter job #{int(latest['id'])}</b><div class='muted' id='convertMsg'>{e(latest.get('message') or latest.get('status'))}</div><div class='progress'><i id='convertPct' style='width:{float(latest.get('percent') or 0):.1f}%'></i></div><div id='convertResults'></div></div>"
        body=f"""<div class='pagehead row space'><div><div class='eyebrow'>Local video utility</div><h1>Convert</h1><div class='lead'>Make smaller shareable copies without touching originals. Converted files go into the <b>Converted</b> folder of this installation; source folders and cards are never written to.</div></div><a class='btn btn2' href='/import'>Add / discover a folder</a></div>
<div class='card'><div class='row space'><div><b>Preset</b><div class='muted small'>Choose a preset. For messengers / sharing, Share 1080p is the balanced option.</div></div><span id='selectedCount' class='badge'>0 selected</span></div>
<div id='estimateSummary' class='card' style='margin-top:10px;padding:10px 12px;background:#111823'><b id='estimateOutput'>Select videos to see estimated output size.</b><div id='estimateNote' class='small muted' style='margin-top:3px'>Estimate is shown before conversion and may vary with image complexity.</div></div>
<style>.convertRow.convertSelected{{border-color:#6f91ff;box-shadow:0 0 0 1px #6f91ff inset;background:#192231}}.convertRow .estimateOne{{min-height:16px}}</style>
<div class='row' style='margin-top:10px;flex-wrap:wrap'>
<label class='card' style='padding:9px'><input type='radio' name='presetChoice' value='keep_resolution'> <b>Original Resolution</b><div class='small muted'>keep 4K / source resolution · lower bitrate</div></label>
<label class='card' style='padding:9px'><input type='radio' name='presetChoice' value='hq_1080p'> <b>High Quality 1080p</b><div class='small muted'>best-looking smaller 1080p copy</div></label>
<label class='card' style='padding:9px'><input type='radio' name='presetChoice' value='share_1080p'> <b>Share 1080p</b><div class='small muted'>balanced for messengers / sharing</div></label>
<label class='card' style='padding:9px'><input type='radio' name='presetChoice' value='small_720p'> <b>Small 720p</b><div class='small muted'>smallest practical share copy</div></label>
</div>
<div class='toolbar'><label>Fit under (optional) <input id='targetMb' type='number' min='50' step='50' placeholder='e.g. 500' style='width:120px'> MB</label><button id='startConvert' class='btn' disabled>Convert selected</button><span class='muted small'>Target size uses two-pass encoding and may take longer.</span></div></div>
{active}
{selection_notice}
<form class='toolbar' method='get' action='/convert'><input name='q' value='{e(q)}' placeholder='Search local videos'><select name='scope'><option value='all' {'selected' if scope=='all' else ''}>All accessible videos</option><option value='library' {'selected' if scope=='library' else ''}>Library only</option></select><select name='source_kind'><option value='' {'selected' if not source_kind else ''}>Any origin</option><option value='fixed' {'selected' if source_kind=='fixed' else ''}>Local folders</option><option value='android' {'selected' if source_kind=='android' else ''}>Android</option><option value='removable' {'selected' if source_kind=='removable' else ''}>SD/USB</option></select><select name='source_id'>{srcopts}</select><select name='sort'><option value='date_desc' {'selected' if sort=='date_desc' else ''}>Newest</option><option value='date_asc' {'selected' if sort=='date_asc' else ''}>Oldest</option><option value='size_desc' {'selected' if sort=='size_desc' else ''}>Largest</option><option value='size_asc' {'selected' if sort=='size_asc' else ''}>Smallest</option><option value='duration_desc' {'selected' if sort=='duration_desc' else ''}>Longest</option><option value='name' {'selected' if sort=='name' else ''}>Name</option><option value='source' {'selected' if sort=='source' else ''}>Source</option></select><button class='btn2'>Filter</button><a class='btn2' href='/convert'>Clear</a></form>
<div class='row space section-title'><span>{'Selected videos currently accessible' if preselect_ids else 'Accessible on this catalog page'} <span id='convertTotal' class='badge'>{total_local}</span></span>{"<a class='btn btn2' href='/convert'>Show all local videos</a>" if preselect_ids else ''}</div><div class='small muted' style='margin:-6px 0 10px'>{"Only the selected IDs were checked for local availability." if preselect_ids else f"{total_catalog} matching catalog videos · local availability is checked only for the current page."}</div><div style='display:grid;gap:8px'>{cards}</div>"""
        script="""const checks=()=>[...document.querySelectorAll('.convertCheck:checked')];
const allChecks=[...document.querySelectorAll('.convertCheck')];
const presetKbps={share_1080p:4800,small_720p:2400,hq_1080p:8500};
const presetFallback={share_1080p:.20,small_720p:.11,hq_1080p:.34,keep_resolution:.58};
function chosenPreset(){return (document.querySelector('input[name=presetChoice]:checked')||{}).value||''}
function estimateBytes(ch){
  const size=Number(ch.dataset.size||0),dur=Math.max(0,Number(ch.dataset.durationMs||0)/1000),target=Number(document.getElementById('targetMb').value||0)||0;
  if(target)return Math.min(size||Infinity,target*1024*1024);
  const p=chosenPreset();
  if(!p)return null;
  if(p==='keep_resolution'){
    const w=Number(ch.dataset.width||0),h=Number(ch.dataset.height||0),px=w*h;
    const kbps=(Math.max(w,h)>=3000||px>=7000000)?32000:(px>=1800000?12000:6000);
    return dur>0?kbps*1000/8*dur:size*presetFallback.keep_resolution;
  }
  const kbps=presetKbps[p]||4800;
  return dur>0?kbps*1000/8*dur:size*(presetFallback[p]||.20);
}
function updSel(){
  const xs=checks(),selectedSet=new Set(xs),n=xs.length,x=document.getElementById('selectedCount'),out=document.getElementById('estimateOutput'),note=document.getElementById('estimateNote');
  if(x)x.textContent=n+' selected';
  let src=0,est=0,unknown=0;
  for(const ch of allChecks){
    const row=ch.closest('.convertRow'),one=row&&row.querySelector('.estimateOne');
    if(selectedSet.has(ch)){
      const sz=Number(ch.dataset.size||0),eb=estimateBytes(ch);src+=sz;if(Number.isFinite(eb))est+=eb;if(Number(ch.dataset.durationMs||0)<=0)unknown++;
      if(row)row.classList.add('convertSelected');if(one)one.textContent=Number.isFinite(eb)?'≈ '+hb(eb):'choose preset';
    }else{if(row)row.classList.remove('convertSelected');if(one)one.textContent=''}
  }
  const preset=chosenPreset(),start=document.getElementById('startConvert');if(start)start.disabled=!(n&&preset);
  if(!n){if(out)out.textContent='Select videos to see estimated output size.';if(note)note.textContent='Estimate appears after you choose videos and a preset.';return}
  if(!preset){if(out)out.textContent=n+' video'+(n===1?'':'s')+' · '+hb(src)+' · choose a preset';if(note)note.textContent='No compression preset is selected yet.';return}
  const target=Number(document.getElementById('targetMb').value||0)||0;
  const delta=src-est,pct=src>0?Math.round(delta/src*100):0;
  if(target){
    if(out)out.textContent=n+' video'+(n===1?'':'s')+' · '+hb(src)+' → target ≤ '+hb(est)+' total';
    if(note)note.textContent=target+' MB per file · save up to '+hb(Math.max(0,delta))+(pct>0?' / '+pct+'%':'')+'.';
  }else{
    if(out)out.textContent=n+' video'+(n===1?'':'s')+' · '+hb(src)+' → estimated ≈ '+hb(est);
    if(note)note.textContent=(delta>=0?'Estimated saving '+hb(delta)+(pct>0?' / '+pct+'%':''):'Estimated output may be larger than source')+(unknown?' · refining from video duration…':' · actual size can vary by about 20–30%.');
  }
}
let probeBusy=false;
async function probeMissingDurations(){
  if(probeBusy)return;
  const missing=checks().filter(ch=>(Number(ch.dataset.durationMs||0)<=0||Number(ch.dataset.width||0)<=0||Number(ch.dataset.height||0)<=0)&&ch.dataset.probeState!=='done');
  if(!missing.length)return;
  probeBusy=true;missing.forEach(ch=>ch.dataset.probeState='pending');
  try{
    const r=await fetch('/api/convert/probe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:missing.map(ch=>Number(ch.value))})});
    const x=await r.json();
    for(const ch of missing){
      const meta=(x.items||{})[String(ch.value)]||{},ms=Number(meta.duration_ms||0),w=Number(meta.width||0),h=Number(meta.height||0);
      if(ms>0)ch.dataset.durationMs=String(ms);if(w>0)ch.dataset.width=String(w);if(h>0)ch.dataset.height=String(h);const row=ch.closest('.convertRow');if(row){if(ms>0)row.dataset.durationMs=String(ms);if(w>0)row.dataset.width=String(w);if(h>0)row.dataset.height=String(h)}
      ch.dataset.probeState='done';
    }
  }catch(e){missing.forEach(ch=>ch.dataset.probeState='done')}finally{probeBusy=false;updSel()}
}
allChecks.forEach(x=>x.addEventListener('change',()=>{updSel();probeMissingDurations()}));
document.querySelectorAll('input[name=presetChoice]').forEach(x=>{x.addEventListener('change',updSel);x.addEventListener('click',updSel)});
document.getElementById('targetMb').addEventListener('input',updSel);
updSel();probeMissingDurations();
const convertRows=[...document.querySelectorAll('.convertRow')],convertImgs=[...document.querySelectorAll('.convertThumb')];
async function refreshConvertPreviews(){
  if(!convertImgs.length)return;
  try{
    const ids=convertImgs.map(x=>x.dataset.id).join(','),r=await fetch('/api/thumb-status?ids='+ids,{cache:'no-store'}),x=await r.json(),ready=new Set((x.ready||[]).map(String));
    for(const img of convertImgs){
      const id=String(img.dataset.id);
      if(ready.has(id)&&img.dataset.ready!=='1'){img.dataset.ready='1';img.src='/thumb/'+id+'?v='+(x.generation||Date.now())}
    }
    const unavailable=new Set((x.unavailable||[]).map(String));
    if(Number(x.pending_count||0)>0)setTimeout(refreshConvertPreviews,800);
    else if(unavailable.size)setTimeout(()=>{for(const img of convertImgs){if(unavailable.has(String(img.dataset.id))){img.dataset.ready='';img.src='/thumb/'+img.dataset.id+'?retry='+Date.now()}}setTimeout(refreshConvertPreviews,1200)},30000)
  }catch(e){setTimeout(refreshConvertPreviews,1800)}
}
function setupConvertStoryHover(){
  for(const row of convertRows){
    const ch=row.querySelector('.convertCheck'),img=row.querySelector('.convertThumb'),badge=row.querySelector('.convertStoryBadge');
    if(!ch||ch.disabled||!img)continue;
    let timer=null,hover=false;
    async function ensure(){
      const id=ch.value;
      for(let tries=0;tries<12&&hover;tries++){
        try{
          const r=await fetch('/api/storyboard-status?ids='+id,{cache:'no-store'}),x=await r.json(),st=(x.items||{})[id];
          if(st&&st.ready&&st.count>1){
            if(badge){badge.style.display='block';badge.textContent=st.count+' frames'}
            let idx=0;clearInterval(timer);
            timer=setInterval(()=>{if(!hover)return;img.src='/storyboard/'+id+'/'+idx+'?v='+Date.now();idx=(idx+1)%st.count},420);
            return
          }
          if(tries===0)await fetch('/api/storyboard/'+id+'/queue',{method:'POST'})
        }catch(e){}
        await new Promise(r=>setTimeout(r,700))
      }
    }
    row.addEventListener('mouseenter',()=>{hover=true;ensure()});
    row.addEventListener('mouseleave',()=>{hover=false;clearInterval(timer);timer=null;img.src='/thumb/'+ch.value+'?v='+Date.now()})
  }
}
refreshConvertPreviews();setupConvertStoryHover();
async function startConv(){const ids=checks().map(x=>Number(x.value));if(!ids.length){toast('Select at least one video');return}
 const preset=(document.querySelector('input[name=presetChoice]:checked')||{}).value||'';if(!preset){toast('Choose a preset first');return}
 const target=Number(document.getElementById('targetMb').value||0)||null;
 const b=document.getElementById('startConvert');b.disabled=true;
 try{const r=await fetch('/api/convert/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids,preset,target_mb:target})});const x=await r.json();if(!r.ok)throw new Error(x.error||'Could not start');toast('Conversion started');location.href='/convert'}catch(e){toast(e.message||String(e));b.disabled=false}}
document.getElementById('startConvert').onclick=startConv;
function hb(n){n=Number(n||0);for(const u of ['B','KB','MB','GB','TB']){if(n<1024||u==='TB')return (u==='B'||u==='KB'?n.toFixed(0):n.toFixed(1))+' '+u;n/=1024}}
async function pollConvert(){const box=document.getElementById('convertStatus');if(!box)return;const id=box.dataset.job;try{const r=await fetch('/api/convert/status?id='+id,{cache:'no-store'});const x=await r.json();if(!x.job)return;const j=x.job;document.getElementById('convertMsg').textContent=j.message||j.status;document.getElementById('convertPct').style.width=(j.percent||0)+'%';if(['finished','failed','cancelled'].includes(j.status)){const outs=((j.options||{}).outputs||[]);let h='';for(const o of outs){if(o.error){h+="<div class='small error'>Failed: "+o.error+"</div>"}else{h+="<div class='small'><b>"+hb(o.source_bytes)+" → "+hb(o.output_bytes)+"</b> · saved "+o.saved_percent+"%<br><span class='muted'>"+o.output+"</span></div>"}}document.getElementById('convertResults').innerHTML=h;return}}catch(e){}setTimeout(pollConvert,1000)}
pollConvert();"""
        if not preselect_ids and pages>1:
            base={k:v for k,v in request.args.items() if k not in ('page','ids')}
            body+=page_nav(page,pages,base)
        return layout('Convert',body,script)

    @app.post('/api/convert/probe')
    def convert_probe():
        payload=request.get_json(silent=True) or {}
        return jsonify({'items':{str(k):v for k,v in probe_local_media_meta(payload.get('ids') or []).items()}})

    @app.post('/api/convert/start')
    def convert_start():
        payload=request.get_json(silent=True) or {}
        try:
            job_id=start_convert_job(payload.get('ids') or [],payload.get('preset') or 'share_1080p',payload.get('target_mb'))
            return jsonify({'ok':True,'job_id':job_id})
        except Exception as exc:
            return jsonify({'ok':False,'error':str(exc)}),409

    @app.get('/api/convert/status')
    def convert_status():
        raw=request.args.get('id','').strip()
        job=convert_job_snapshot(int(raw)) if raw.isdigit() else convert_job_snapshot()
        return jsonify({'job':job})


    @app.get('/library')
    def library():
        return gallery('library')

    @app.post('/api/selection-action')
    def selection_action():
        p=request.get_json(silent=True) or {}; action=p.get('action'); ids=[int(x) for x in p.get('ids',[]) if str(x).isdigit()]
        if not ids: return jsonify({'error':'No files selected'}),400
        try:
            if action=='import': return jsonify({'job_id':queue_job('import',ids,{'analyze':False})})
            if action=='import_analyze': return jsonify({'job_id':queue_job('import_analyze',ids,{'analyze':True})})
            if action=='analyze': return jsonify({'job_id':queue_job('analyze',ids)})
            if action=='media_brain': return jsonify({'job_id':queue_job('media_brain',ids,{'preset':str(p.get('preset') or 'general')})})
            if action=='archive': return jsonify({'job_id':queue_job('archive',ids)})
            if action=='private': return jsonify({'job_id':queue_job('private',ids)})
            if action=='reject': return jsonify({'job_id':queue_job('reject',ids)})
            if action=='remove':
                rr=remove_from_library(ids)
                msg=f"Removed {rr['removed']} item(s) from Library"
                if rr['staging_deleted']: msg+=f"; moved {rr['staging_deleted']} Staging copy/copies to Rejected/Removed from Library"
                if rr['errors']: msg+=f"; {len(rr['errors'])} failed"
                return jsonify({'message':msg,'removed':rr['removed'],'staging_deleted':rr['staging_deleted'],'errors':rr['errors']})
            if action=='rights':
                n=set_rights(ids,str(p.get('preset') or ''),str(p.get('notes') or '')); return jsonify({'message':f'Rights updated for {n} item(s)'})
            if action=='exclude': set_excluded(ids,True); return jsonify({'message':'Excluded'})
            return jsonify({'error':'Unknown action'}),400
        except Exception as exc: return jsonify({'error':str(exc)}),500

    @app.get('/api/items')
    def items_api():
        ids=[int(x) for x in request.args.get('ids','').split(',') if x.isdigit()][:200]
        if not ids:return jsonify({})
        with db() as con: rows=con.execute(f"SELECT id,analysis_status,import_status,source_kind,staging_path,archive_path,private_path,quality_status,quality_score,rights_status,rights_audio_present,error,import_error FROM inventory WHERE id IN ({','.join('?' for _ in ids)})",ids).fetchall()
        out={}
        for r in rows:
            imp='archived' if r['archive_path'] else ('private' if r['private_path'] else ('imported' if r['staging_path'] else ('local' if r['source_kind']=='fixed' else r['import_status'])))
            out[str(r['id'])]={'analysis_status':r['analysis_status'],'import_state':imp,'quality_status':r['quality_status'],'quality_score':r['quality_score'],'rights_status':r['rights_status'],'rights_audio_present':r['rights_audio_present'],'error':r['import_error'] or r['error']}
        return jsonify(out)

    @app.get('/api/thumb-status')
    def thumb_status():
        ids=[int(x) for x in request.args.get('ids','').split(',') if x.isdigit()][:200]
        if not ids:return jsonify({'ready':[],'ready_count':0,'pending_count':0,'unavailable_count':0,'generation':int(time.time())})
        with db() as con:
            rows=con.execute(f"SELECT id,preview_status,preview_path FROM inventory WHERE excluded=0 AND id IN ({','.join('?' for _ in ids)})",ids).fetchall()
        ready=[]; unavailable=[]
        for r in rows:
            p=Path(r['preview_path']) if r['preview_path'] else THUMBS / f"{int(r['id'])}.jpg"
            if p.exists(): ready.append(int(r['id']))
            elif r['preview_status']=='unavailable': unavailable.append(int(r['id']))
        ready_set=set(ready); unavailable_set=set(unavailable)
        pending=[i for i in ids if i not in ready_set and i not in unavailable_set]
        return jsonify({'ready':ready,'unavailable':unavailable,'ready_count':len(ready),'unavailable_count':len(unavailable),'pending_count':len(pending),'generation':int(time.time())})

    @app.get('/api/storyboard-status')
    def storyboard_status():
        ids=[int(x) for x in request.args.get('ids','').split(',') if x.isdigit()][:200]
        out={}; pending=0
        if not ids:return jsonify({'items':{},'pending_count':0})
        with db() as con:
            rows=con.execute(f"SELECT id,media_type,source_kind,path,staging_path,archive_path,private_path,rejected_path,storyboard_status,storyboard_frames,storyboard_best_index FROM inventory WHERE excluded=0 AND id IN ({','.join('?' for _ in ids)})",ids).fetchall()
        for r in rows:
            if r['media_type']!='video':continue
            info=cached_storyboard(int(r['id']))
            if info:
                out[str(r['id'])]={'ready':True,'count':len(info['frames']),'best_index':int(info.get('best_index') or 0),'times':[f['time'] for f in info['frames']]}
            else:
                local=bool((r['staging_path'] and Path(r['staging_path']).exists()) or (r['archive_path'] and Path(r['archive_path']).exists()) or (r['private_path'] and Path(r['private_path']).exists()) or (r['rejected_path'] and Path(r['rejected_path']).exists()) or (r['source_kind']=='fixed' and r['path'] and Path(r['path']).exists()))
                out[str(r['id'])]={'ready':False,'count':0,'local':local,'status':r['storyboard_status'] or 'pending'}
                if local and r['storyboard_status']!='unavailable':pending+=1
        return jsonify({'items':out,'pending_count':pending,'generation':int(time.time())})

    @app.post('/api/storyboard/<int:inv_id>/queue')
    def storyboard_queue(inv_id):
        queue_storyboard(inv_id,priority=-20)
        return jsonify({'ok':True})

    @app.get('/storyboard/<int:inv_id>/<int:index>')
    def storyboard_frame(inv_id,index):
        info=cached_storyboard(inv_id)
        if not info:
            queue_storyboard(inv_id,priority=-20)
            return Response(placeholder_svg('video'),mimetype='image/svg+xml')
        frames=info.get('frames') or []
        if index<0 or index>=len(frames):return Response(placeholder_svg('video'),mimetype='image/svg+xml'),404
        return send_file(frames[index]['path'],mimetype='image/jpeg',conditional=True)


    @app.get('/clip-preview/<int:clip_id>')
    def clip_preview(clip_id):
        c=clip_by_id(clip_id)
        if c and c.get('preview_path') and Path(c['preview_path']).exists():
            return send_file(c['preview_path'],mimetype='image/jpeg',conditional=True)
        if c:
            return redirect(f"/thumb/{c['inventory_id']}")
        return Response(placeholder_svg('video'),mimetype='image/svg+xml'),404

    @app.get('/thumb/<int:inv_id>')
    def thumb(inv_id):
        p=cached_thumbnail(inv_id)
        if p:return send_file(p,mimetype='image/jpeg',conditional=True)
        queue_thumbnail(inv_id, priority=-10)
        with db() as con:r=con.execute('SELECT media_type FROM inventory WHERE id=?',(inv_id,)).fetchone()
        return Response(placeholder_svg(r['media_type'] if r else 'video'),mimetype='image/svg+xml')


    @app.get('/api/similar/<int:inv_id>')
    def similar_api(inv_id):
        try:
            lim=max(1,min(100,int(request.args.get('limit','24') or 24)))
        except Exception: lim=24
        return jsonify(find_similar(inv_id,lim))

    @app.get('/similar/<int:inv_id>')
    def similar_page(inv_id):
        with db() as con:
            src=con.execute('SELECT id,filename FROM inventory WHERE id=?',(inv_id,)).fetchone()
        if not src:return 'Not found',404
        data=find_similar(inv_id,48); rows=data.get('results') or []
        body=f"<div class='pagehead'><div class='eyebrow'>Local visual similarity / M7</div><h1>Find Similar</h1><div class='lead'>Perceptual comparison uses cached local thumbnails only. Nothing is uploaded.</div></div><div class='card row space'><div><b>Reference</b><div class='muted'>{e(src['filename'])}</div></div><img src='/thumb/{inv_id}' style='width:132px;height:84px;object-fit:cover;border-radius:9px'></div><div class='grid'>"
        for r in rows:
            iid=int(r['inventory_id']); sc=round(100*float(r.get('visual_score') or 0))
            body+=f"<a class='media-card' href='/item/{iid}'><div class='thumb'><img loading='lazy' src='/thumb/{iid}'></div><div class='meta'><div class='row space'><b>{e(r.get('filename') or '')}</b><span class='badge ready'>{sc}% similar</span></div><div class='muted'>{e(r.get('source_label') or '')}</div></div></a>"
        body+="</div>"
        return layout('Find Similar',body)

    @app.get('/item/<int:inv_id>')
    def item(inv_id):
        with db() as con:r=con.execute('SELECT * FROM inventory WHERE id=?',(inv_id,)).fetchone()
        if not r:return 'Not found',404
        local=next((r[k] for k in ('staging_path','archive_path','private_path','rejected_path','path') if r[k] and Path(r[k]).exists()),None)
        preview=f"<img src='/thumb/{inv_id}'>"
        story_html=''
        brain_html=''
        if local and r['media_type']=='video':
            preview=f"<video id='mainVideo' controls preload='metadata' poster='/thumb/{inv_id}' src='/media/{inv_id}'></video>"
            queue_storyboard(inv_id,priority=-10)
            info=cached_storyboard(inv_id)
            if info:
                story_html="<div id='storyboardMount' class='storystrip' data-ready='1'>"+''.join(f"<div class='storyframe' data-time='{f['time']}'><img src='/storyboard/{inv_id}/{f['index']}'><span class='storytime'>{int(f['time']//60)}:{int(f['time']%60):02d}</span></div>" for f in info['frames'])+"</div>"
            else:
                story_html=f"<div id='storyboardMount' class='card' data-ready='0' style='margin-top:12px'><b>8 preview frames</b><div class='muted small'>Generating locally… They will appear here automatically; no reload and no Explorer needed.</div></div>"
            clips=clips_for_inventory(inv_id)
            brain_html="<div class='card' style='margin-top:12px'><div class='row space'><div><div class='eyebrow'>Media Brain</div><b>Virtual clips + Smart Crop</b></div><form method='post' action='/item/%d/media-brain' class='row'><select name='preset'><option value='general'>General</option><option value='car'>Car / dashboard</option></select><button class='btn2'>%s</button></form></div>" % (inv_id, "Rebuild" if clips else "Build")
            if clips:
                brain_html+="<div class='muted' style='margin:8px 0'>%d virtual clips. Use Open clip to play only that interval and preview its Smart Crop.</div><div class='storystrip'>" % len(clips)
                for c in clips:
                    st=c['start_ms']/1000.0; en=c['end_ms']/1000.0
                    crop=", ".join(x['aspect'] for x in c.get('crops',[]))
                    brain_html+=f"<div class='storyframe' id='clip-{c['id']}' data-time='{st}' style='min-width:150px'><img src='/clip-preview/{c['id']}'><span class='storytime'>{int(st//60)}:{int(st%60):02d}–{int(en//60)}:{int(en%60):02d}</span><div class='small' style='padding:5px'><b>{e(c['label'])} {e(c['score'])}</b><br>{e(crop)}<br><a class='btn btn2 openLink' style='margin-top:5px;padding:3px 7px;font-size:11px' href='/clip/{c['id']}?back=item'>Open clip</a></div></div>"
                brain_html+="</div>"
            else:
                brain_html+="<div class='muted' style='margin-top:8px'>Build scene/window clips, rank Best Moments and calculate static 16:9 / 4:5 / 1:1 / 9:16 crop suggestions.</div>"
            brain_html+="</div>"
            story_html+=brain_html
        body=f"<div class='details'><div><div class='preview'>{preview}</div>{story_html}</div><div class='card'><div class='row space'><h2>{e(r['filename'])}</h2><a class='btn btn2' href='/similar/{inv_id}'>Find similar</a></div><div class='kv'>"
        vals=[('Source',r['source_label']),('Type',r['media_type']),('Size',human_bytes(r['size_bytes'])),('Duration',human_duration(r['duration_ms'])),('Import',r['import_status']),('Staging',r['staging_path'] or '—'),('Privacy',r['analysis_status']),('Privacy reason',r['privacy_reason'] or '—'),('Quality',f"{r['quality_status']} {r['quality_score'] if r['quality_score'] is not None else ''}"),('Quality reason',r['quality_reason'] or '—'),('SHA-256',r['sha256'] or '—'),('Archive',r['archive_path'] or '—'),('Rejected',r['rejected_path'] or '—'),('Rights',r['rights_status'] or 'unknown'),('Rights place',r['rights_place'] or '—'),('Rights reason',r['rights_reason'] or '—'),('Audio present','yes' if r['rights_audio_present'] else 'no'),('Rights source',r['rights_source_url'] or '—'),('Rights notes',r['rights_notes'] or '—'),('Error',r['import_error'] or r['error'] or '—')]
        for k,v in vals:body+=f"<div>{e(k)}</div><div>{e(v)}</div>"
        body+=f"</div><div class='toolbar'><form method='post' action='/item/{inv_id}/remove' onsubmit=\"return confirm('Remove this item from Library? Its imported Staging copy moves to the Rejected / Removed from Library folder (delete it there when you are sure); the source original stays untouched.')\"><button class='danger'>Remove from Library</button></form></div><hr style='border-color:#303842;margin:18px 0'><h3>Rights / location risk</h3><div class='muted'>Triage only — not a legal determination. Manual tags are never overwritten by automatic analysis.</div><form method='post' action='/item/%d/rights' class='toolbar'><select name='status'><option value='unknown'>Unknown</option><option value='review'>Review</option><option value='permission'>Permission needed</option><option value='cleared'>Cleared</option><option value='blocked'>Do not publish</option></select><input name='place' placeholder='Place / venue' value='%s'><input name='source_url' placeholder='Policy/source URL' value='%s'><input name='notes' placeholder='Notes' value='%s'><button>Save rights status</button></form></div></div>" % (inv_id,e(r['rights_place'] or ''),e(r['rights_source_url'] or ''),e(r['rights_notes'] or ''));return layout(r['filename'],body,f"""function bindStoryFrames(){{document.querySelectorAll('#storyboardMount .storyframe').forEach(x=>x.onclick=()=>{{const v=document.getElementById('mainVideo');if(v){{v.currentTime=Number(x.dataset.time||0);v.play().catch(()=>{{}})}}}})}}
function fmtTime(t){{t=Math.max(0,Number(t||0));return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')}}
async function loadStoryboard(){{const m=document.getElementById('storyboardMount');if(!m||m.dataset.ready==='1'){{bindStoryFrames();return}};try{{const r=await fetch('/api/storyboard-status?ids={inv_id}',{{cache:'no-store'}}),x=await r.json(),it=(x.items||{{}})['{inv_id}'];if(it&&it.ready&&it.count){{let h="<div id='storyboardMount' class='storystrip' data-ready='1'>";for(let i=0;i<it.count;i++){{const t=(it.times||[])[i]||0;h+="<div class='storyframe' data-time='"+t+"'><img src='/storyboard/{inv_id}/"+i+"?g="+(x.generation||0)+"'><span class='storytime'>"+fmtTime(t)+"</span></div>"}}h+='</div>';m.outerHTML=h;bindStoryFrames();return}}if(it&&it.status==='unavailable'){{m.innerHTML="<b>8 preview frames</b><div class='muted small'>Preview generation is temporarily unavailable for this file. Archivist will retry later.</div>";return}}await fetch('/api/storyboard/{inv_id}/queue',{{method:'POST'}})}}catch(e){{}}setTimeout(loadStoryboard,1200)}}
bindStoryFrames();loadStoryboard();""")


    @app.post('/item/<int:inv_id>/media-brain')
    def item_media_brain(inv_id):
        preset='car' if request.form.get('preset')=='car' else 'general'
        try:
            jid=queue_job('media_brain',[inv_id],{'preset':preset})
            return redirect(f'/jobs/{jid}')
        except Exception as exc:
            return f'Media Brain failed: {e(exc)}',400

    @app.post('/item/<int:inv_id>/remove')
    def item_remove(inv_id):
        rr=remove_from_library([inv_id])
        if not rr['removed']:
            detail='; '.join(rr['errors']) if rr['errors'] else 'Not found or already removed'
            return e(detail),400 if rr['errors'] else 404
        return redirect('/library')

    @app.post('/item/<int:inv_id>/rights')
    def item_rights(inv_id):
        try:
            set_rights_custom(inv_id, request.form.get('status','unknown'), request.form.get('place','').strip(), request.form.get('notes','').strip(), request.form.get('source_url','').strip())
        except Exception as exc:
            return f'Rights update failed: {e(exc)}',400
        return redirect(f'/item/{inv_id}')

    @app.get('/media/<int:inv_id>')
    def media(inv_id):
        with db() as con:r=con.execute('SELECT staging_path,archive_path,private_path,rejected_path,path FROM inventory WHERE id=?',(inv_id,)).fetchone()
        if not r:return 'Not found',404
        for k in ('staging_path','archive_path','private_path','rejected_path','path'):
            if r[k] and Path(r[k]).exists():return send_file(r[k],conditional=True)
        return 'Not local',404

    @app.get('/jobs')
    def jobs():
        js=latest_jobs(30)
        active_any=any(j['status'] in ('queued','running') for j in js)
        body="<div class='row space'><div><h1 style='margin:0'>Jobs</h1><div class='muted'>Live queue. Running jobs refresh automatically; completed jobs keep their actual start, finish and elapsed time.</div></div></div><div class='jobs'>"
        for j in js:
            pct=round(100*j['done']/j['total']) if j['total'] else 0
            progress=f"{j['done']}/{j['total']}"
            if j['kind']=='media_brain' and j['status'] in ('queued','running'):
                mm=re.search(r'clip\s+(\d+)/(\d+)',j['message'] or '',re.I)
                if mm:
                    n,total=int(mm.group(1)),max(1,int(mm.group(2)))
                    pct=min(99,round(100*n/total));progress=f"clip {n}/{total}"
                elif 'scene scan' in (j['message'] or ''):
                    pct=2;progress='scene scan'
            elapsed=_job_elapsed(j)
            started=j.get('started_at') or j.get('created_at') or ''
            finished=j.get('finished_at') or ''
            timing=f"Started <span data-local-ts='{e(started)}'>{e(started)}</span>"
            if finished:
                timing+=f" · Finished <span data-local-ts='{e(finished)}'>{e(finished)}</span>"
            if elapsed:
                timing+=f" · Elapsed {e(elapsed)}"
            body+=f"<a class='card jobrow' href='/jobs/{j['id']}'><b>#{j['id']}</b><span>{e(j['kind'])}</span><span class='badge {e(j['status'])}'>{e(j['status'])}</span><span>{e(j['message'] or '')}<div class='muted'>{e(j['current_filename'] or '')}</div><div class='muted' style='margin-top:3px'>{timing}</div></span><span>{e(progress)} · {pct}% · {j['failed']} errors</span></a>"
        body+='</div>'
        script="""document.querySelectorAll('[data-local-ts]').forEach(x=>{try{const d=new Date(x.dataset.localTs);if(!isNaN(d))x.textContent=d.toLocaleTimeString([],{hour:'numeric',minute:'2-digit',second:'2-digit'})}catch(e){}});"""
        if active_any:
            script+="setTimeout(()=>location.reload(),1200);"
        return layout('Jobs',body,script)

    @app.get('/jobs/<int:jid>')
    def job_page(jid):
        d=job_detail(jid)
        if not d:return 'Not found',404
        j=d['job']
        safe=' · source can be disconnected' if j.get('source_releasable') and j['status']=='running' else ''
        body=f"<div class='row space'><div><h1>Job #{jid}</h1><div class='muted'>{e(j['kind'])} · {e(j['status'])} · {j['done']}/{j['total']} · {human_bytes(j['bytes_done'])}/{human_bytes(j['bytes_total'])}{safe}</div></div><div class='row'>"
        if j['failed']:
            body += f"<button onclick=\"jobAction(this,'/api/jobs/{jid}/retry','retry')\" class='warn'>Retry failed</button>"
        if j['status'] in ('queued','running'):
            body += f"<button onclick=\"jobAction(this,'/api/jobs/{jid}/cancel','cancel')\" class='danger'>Cancel job</button>"
        body+='</div></div><div class="jobs">'
        for x in d['items']:
            err=f"<div class='errbox'>{e(x['error'])}</div>" if x['error'] else ''
            body+=f"<div class='card'><div class='row space'><b>{x['seq']}. {e(x['filename'])}</b><span class='badge {e(x['status'])}'>{e(x['phase'])}</span></div><div class='muted'>{e(x['source_label'])} · {human_bytes(x['bytes_done'])}/{human_bytes(x['bytes_total'])} · {e(x['result_status'] or '')}</div>{err}</div>"
        body+='</div>'
        script="""window.jobActionBusy=false;
async function jobAction(btn,url,mode){
  if(window.jobActionBusy)return;
  window.jobActionBusy=true;
  const label=btn.textContent;
  btn.disabled=true;
  btn.textContent=mode==='retry'?'Retrying…':'Cancelling…';
  try{
    const r=await fetch(url,{method:'POST'});
    let x={};
    try{x=await r.json()}catch(_){}
    if(!r.ok)throw new Error(x.error||('HTTP '+r.status));
    if(mode==='retry'&&x.job_id){toast('Retry job #'+x.job_id);location.href='/jobs/'+x.job_id;return}
    if(mode==='cancel'&&x.ok){toast('Cancellation requested');setTimeout(()=>location.reload(),500);return}
    throw new Error(x.error||'Action did not complete');
  }catch(err){
    toast('Action outcome is unknown — check job status before trying again. '+((err&&err.message)||''));
    btn.disabled=false;
    btn.textContent='Check status';
    btn.onclick=()=>location.reload();
    window.jobActionBusy=false;
  }
}
"""
        if j['status'] in ('queued','running'):
            script+="setTimeout(()=>{if(!window.jobActionBusy)location.reload()},1500);"
        return layout(f'Job {jid}',body,script)

    @app.post('/api/jobs/<int:jid>/retry')
    def retry(jid):
        try:return jsonify({'job_id':retry_failed(jid)})
        except Exception as exc:return jsonify({'error':str(exc)}),400

    @app.post('/api/jobs/<int:jid>/cancel')
    def cancel(jid):
        try:
            ok=cancel_job(jid);return jsonify({'ok':ok,'error':None if ok else 'Job is already finished or not found'})
        except Exception as exc:return jsonify({'ok':False,'error':str(exc)}),400

    @app.get('/settings')
    def settings():
        cfg=load_config(); body=f"""<div class='pagehead'><div class='eyebrow'>Configuration</div><h1>Settings</h1><div class='lead'>Storage, privacy and local analysis behavior. External capabilities are managed separately in Setup & Connections.</div><div class='row' style='margin-top:10px'><a class='btn btn2' href='/settings/connections'>Setup & Connections</a><a class='btn btn2' href='/help'>Help & Recovery</a><a class='btn btn2' href='/about'>About</a></div></div><div class='about-grid'><div><div class='section-title'>Storage</div><div class='card about-list'><div><b>Staging</b><div class='muted'>{e(STAGING)}</div></div><div><b>Private</b><div class='muted'>{e(PRIVATE)}</div></div><div><b>Rejected quarantine</b><div class='muted'>{e(REJECTED)}</div></div><div><b>Archive</b><div class='muted'>{e(cfg['archive_root'])}</div></div></div></div><div><div class='section-title'>Behavior</div><form method='post' action='/settings/save' class='card'><label>Archive folder<br><input name='archive_root' style='width:100%;margin-top:5px' value='{e(cfg['archive_root'])}'></label><br><br><label>Free-space reserve GB<br><input name='min_free_gb' type='number' value='{e(cfg['ingest']['min_free_gb'])}' style='margin-top:5px'></label><br><br><label><input type='checkbox' name='privacy' {'checked' if cfg['privacy']['enabled'] else ''}> Privacy screening</label><br><label><input type='checkbox' name='quality' {'checked' if cfg['analysis']['technical_quality'] else ''}> Technical quality triage</label><br><br><button>Save settings</button></form></div></div><div class='section-title'>Existing local sources</div><div class='card'>"""
        for i,s in enumerate(cfg.get('sources',[])):
            body+=f"<div class='row space' style='padding:7px 0'><span><b>{e(s.get('label') or s.get('path'))}</b><div class='muted'>{e(s.get('path'))}</div></span><form method='post' action='/settings/remove-source'><input type='hidden' name='index' value='{i}'><button class='danger'>Remove</button></form></div>"
        body+=f"""<form method='post' action='/settings/add-source' class='toolbar'><input name='label' placeholder='Label'><input name='path' style='min-width:360px' placeholder='D:\\Videos'><button>Add source</button></form></div><div class='section-title'>Rights Guard</div><div class='card'>Privacy, technical quality and publishing-rights risk stay separate. Rights flags are conservative workflow hints, not legal determinations. Manual rights decisions are preserved across later analysis.</div>"""
        return layout('Settings',body)

    @app.get('/about')
    def about():
        cfg=load_config(); phone=phone_snapshot(); phone_text=(phone.get('model') or phone.get('serial') or 'Android')+' connected' if phone['connected'] else (phone.get('error') or 'not connected')
        body=f"""<div class='card about-hero tone-blue'><div class='eyebrow'>Why we built it</div><h1 style='font-size:36px;letter-spacing:-.8px;margin:4px 0 8px'>Archivist</h1><div class='lead' style='max-width:880px'>Your footage may already be spread across phones, cameras, cards and old folders while the useful moments stay buried inside thousands of files. Archivist is a private workspace designed to turn that mess into a usable creative library.</div><div class='row' style='margin-top:16px'><span class='badge ready'>local-first</span><span class='badge safe'>privacy-first</span><span class='badge duplicate'>AI-assisted</span><span class='badge audioflag'>built for video</span></div></div><div class='section-title'>Who is building it</div><div class='card tone-violet'><h2 style='margin-top:0'>Built local-first</h2><p class='lead' style='font-size:15px'>Archivist is being shaped around real mixed-device media workflows: explicit import, source safety, private local analysis, nondestructive editing and clear control over every optional external connection.</p><div class='muted'>The product identity is installation-neutral: no personal paths, devices, accounts or credentials are built into defaults.</div></div><div class='section-title'>The idea</div><div class='about-grid'><div class='card'><h2 style='margin-top:0'>One place between the camera and the final story.</h2><p class='lead' style='font-size:15px'>We do not want another photo viewer. We want Archivist to remember what we chose, protect what must stay private, understand what is inside long videos, and surface the clips that are actually worth using.</p><div class='principles'><div class='principle tone-mint'><b>Keep the originals safe</b><span class='muted'>Phone, SD and camera originals are never automatically deleted or rewritten.</span></div><div class='principle tone-rose'><b>Private means private</b><span class='muted'>Private Forever stays out of the normal Library and future creative workflows.</span></div><div class='principle tone-violet'><b>AI suggests, we decide</b><span class='muted'>Quality, privacy and rights checks help us review; they do not silently make destructive decisions.</span></div></div></div><div class='card'><h2 style='margin-top:0'>Where we are</h2><div class='roadmap'><div class='roadmap-step'><span class='step-dot'></span><div><b>Import → Library</b><div class='muted'>Browse Android, SD/USB and local folders in Import; only selected media becomes the working collection.</div></div></div><div class='roadmap-step'><span class='step-dot'></span><div><b>Understand video</b><div class='muted'>Storyboards and hover previews are the start; semantic tags and scene-level understanding come next.</div></div></div><div class='roadmap-step'><span class='step-dot'></span><div><b>Virtual clips</b><div class='muted'>Mark useful moments without cutting or duplicating the original file.</div></div></div><div class='roadmap-step'><span class='step-dot'></span><div><b>Content Composer</b><div class='muted'>The long-term goal: ask for a story or Reel and let the system find the right safe, useful moments from your own archive.</div></div></div></div></div></div><div class='section-title'>Our rules</div><div class='about-grid'><div class='card about-list'><div><b>Privacy, quality and publishing rights stay separate.</b><div class='muted'>A technically beautiful clip can still be private or need a rights review.</div></div><div><b>No mystery copies.</b><div class='muted'>Import is explicit. Library means the local working set.</div></div><div><b>No automatic source cleanup.</b><div class='muted'>Disconnect only after Archivist explicitly says the source is safe to disconnect.</div></div><div><b>No fake certainty.</b><div class='muted'>Rights Guard flags risk and context; it does not pretend every venue question has a simple legal yes/no answer.</div></div></div><div class='card'><h2 style='margin-top:0'>This installation</h2><div class='about-list'><div><b>Version</b><div class='muted'>Archivist v{e(VERSION)}</div></div><div><b>Android</b><div class='device' style='margin-top:5px'><span class='device-dot {'online' if phone['connected'] else ''}' data-phone-dot></span><span class='muted' data-phone-text>{e(phone_text)}</span></div></div><div><b>Archivist home</b><div class='muted'>{e(HOME)}</div></div><div><b>Staging</b><div class='muted'>{e(STAGING)}</div></div><div><b>Archive</b><div class='muted'>{e(cfg['archive_root'])}</div></div></div></div></div><div class='section-title'>Update safety</div><div class='card callout'><b>Updates should fail safe.</b><div class='muted' style='margin-top:4px'>The permanent launcher now health-checks a newly installed release and can restore the previous backup if the new build does not come up correctly.</div></div>"""
        return layout('About',body)

    @app.post('/import/add-source')
    def import_add_source():
        cfg=load_config(); p=request.form.get('path','').strip(); label=request.form.get('label','').strip() or p
        try:
            pp=Path(os.path.expandvars(p)).expanduser()
            if not p or not pp.exists() or not pp.is_dir():
                return redirect('/import?source_error='+urllib.parse.quote('Folder not found: '+(p or '(empty path)')))
            norm=str(pp.resolve())
            exists=any(str(Path(os.path.expandvars(str(s.get('path') or ''))).expanduser()).lower()==norm.lower() for s in cfg.get('sources',[]) if s.get('path'))
            if not exists:
                cfg.setdefault('sources',[]).append({'path':norm,'label':label or norm,'kind':'fixed','enabled':True})
                save_config(cfg)
            start_discovery()
            return redirect('/import?source_kind=fixed')
        except Exception as exc:
            return redirect('/import?source_error='+urllib.parse.quote(str(exc)))

    @app.post('/import/remove-source')
    def import_remove_source():
        cfg=load_config()
        try:
            cfg['sources'].pop(int(request.form.get('index','-1')))
            save_config(cfg)
        except Exception:
            pass
        return redirect('/import')

    @app.post('/settings/add-source')
    def add_source():
        cfg=load_config();p=request.form.get('path','').strip();label=request.form.get('label','').strip() or p
        if p:cfg.setdefault('sources',[]).append({'path':p,'label':label,'kind':'fixed','enabled':True});save_config(cfg)
        return redirect('/settings')

    @app.post('/settings/remove-source')
    def rem_source():
        cfg=load_config()
        try:cfg['sources'].pop(int(request.form.get('index','-1')));save_config(cfg)
        except Exception:pass
        return redirect('/settings')

    @app.post('/settings/save')
    def save_settings():
        cfg=load_config();ar=request.form.get('archive_root','').strip()
        if ar:cfg['archive_root']=ar
        try:cfg['ingest']['min_free_gb']=max(1,int(request.form.get('min_free_gb','10')))
        except Exception:pass
        cfg['privacy']['enabled']='privacy' in request.form;cfg['analysis']['technical_quality']='quality' in request.form;save_config(cfg);return redirect('/settings')

    register_auto_edit(app, layout, e, human_bytes)
    return app

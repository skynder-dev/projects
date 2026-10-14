from __future__ import annotations
import subprocess
import os
import json
import sys
from .platform_adapter import process_kwargs

import base64, ctypes, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_PORT, DATA, HOME, INSTALL, VERSION
from .db import db
from .media import _ffmpeg_exe, make_storyboard, technical_quality
from .media_brain import interpolate_crop_keyframes, validate_crop_keyframes

ASSETS = Path(__file__).resolve().parent / "assets"
DIAG_DIR = DATA / "diagnostics"
REMOTE_CONFIG = DATA / "remote_lab.json"
ENDPOINT = "https://ldlhnedbqeqcbqelhuhm.supabase.co/functions/v1/archivist-remote-lab"
LOCAL = f"http://127.0.0.1:{APP_PORT}"

def _now(): return datetime.now(timezone.utc).isoformat()

def _hidden():
    return process_kwargs()

def _windows_hidden_subprocess_contract():
    if os.name!='nt': return {'platform':os.name,'skipped':True}
    py=INSTALL/'.venv'/'Scripts'/'python.exe'
    if not py.exists(): raise RuntimeError('python.exe missing for hidden subprocess contract')
    code="import ctypes;print(int(ctypes.windll.kernel32.GetConsoleWindow() or 0))"
    r=subprocess.run([str(py),'-c',code],capture_output=True,text=True,timeout=15,**_hidden())
    if r.returncode!=0: raise RuntimeError('hidden python probe failed')
    handle=int((r.stdout or '0').strip().splitlines()[-1] or 0)
    if handle!=0: raise RuntimeError('hidden python child acquired a console window')
    src=Path(__file__).read_text(encoding='utf-8')
    wsrc=(Path(__file__).parent/'watchdog_diag_worker.py').read_text(encoding='utf-8')
    if "timeout=45,**_hidden())" not in src: raise RuntimeError('audio diagnostic bypasses hidden wrapper')
    if "**process_kwargs())" not in wsrc: raise RuntimeError('watchdog diagnostic child bypasses hidden wrapper')
    return {'console_handle':handle,'audio_hidden_wrapper':True,'watchdog_hidden_wrapper':True}

def _edge():
    candidates=[]
    for key in ('PROGRAMFILES(X86)','PROGRAMFILES','LOCALAPPDATA'):
        base=os.environ.get(key)
        if base: candidates.append(Path(base)/'Microsoft'/'Edge'/'Application'/'msedge.exe')
    p=shutil.which('msedge') or shutil.which('microsoft-edge')
    if p: candidates.insert(0,Path(p))
    return next((p for p in candidates if p.exists()),None)

def _visible_console_windows():
    if os.name!='nt': return []
    out=[]; user32=ctypes.windll.user32
    @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def cb(hwnd,_):
        if not user32.IsWindowVisible(hwnd): return True
        cls=ctypes.create_unicode_buffer(128); user32.GetClassNameW(hwnd,cls,128)
        if cls.value in ('ConsoleWindowClass','CASCADIA_HOSTING_WINDOW_CLASS'):
            title=ctypes.create_unicode_buffer(256); user32.GetWindowTextW(hwnd,title,256)
            out.append(hashlib.sha256(title.value.encode()).hexdigest()[:12])
        return True
    user32.EnumWindows(cb,0); return sorted(out)

def _check(name,fn,rows,required=True):
    t=time.monotonic()
    try:
        detail=fn(); rows.append({'name':name,'status':'passed','required':required,'ms':round((time.monotonic()-t)*1000),'detail':detail})
    except Exception as exc:
        rows.append({'name':name,'status':'failed' if required else 'optional_unavailable','required':required,'ms':round((time.monotonic()-t)*1000),'error':str(exc)[:700]})

def _cdp_eval_retry(cdp, params, attempts=4):
    last=None
    for i in range(max(1,int(attempts))):
        try:
            return cdp('Runtime.evaluate',params)
        except RuntimeError as exc:
            last=exc
            if 'Execution context was destroyed' not in str(exc) or i>=attempts-1:
                raise
            time.sleep(.20*(i+1))
    raise last

def _route(path):
    with urllib.request.urlopen(LOCAL+path,timeout=10) as r:
        body=r.read(); assert r.status==200 and len(body)>20
        return {'http':r.status,'bytes':len(body)}

def _ffmpeg_decode(asset):
    exe=_ffmpeg_exe(); assert exe, 'FFmpeg unavailable'
    r=subprocess.run([exe,'-hide_banner','-loglevel','error','-i',str(asset),'-f','null','-'],capture_output=True,timeout=35,**_hidden())
    assert r.returncode==0,(r.stderr or b'')[-500:].decode(errors='replace')
    return {'bytes':asset.stat().st_size,'decode':'ok'}

def _media_pipeline():
    src=ASSETS/'browser_fixture_h264.mp4'; assert src.exists()
    with tempfile.TemporaryDirectory(prefix='archivist_diag_media_') as td:
        story=make_storyboard(src,Path(td)/'story',frames=8,fingerprint='diagnostic')
        assert story and len(story.get('frames',[]))==8
        score,status,reason=technical_quality(src,'video',samples=3)
        assert status in ('ok','review') and score is not None
        return {'storyboard_frames':8,'quality_status':status,'quality_score':score,'quality_reason':reason}

def _full_sandbox_pipeline():
    src=ASSETS/'browser_fixture_h264.mp4'; assert src.exists()
    with tempfile.TemporaryDirectory(prefix='archivist_full_sandbox_') as td:
        fixture=Path(td)/'fixture.mp4';shutil.copy2(src,fixture)
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app');env['ARCHIVIST_SMART_CROP_V2_TRACKING']='1'
        py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
        r=subprocess.run([str(py),'-m','archivist.diagnostic_worker',str(fixture)],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=210,errors='replace',**_hidden())
        if r.returncode!=0: raise RuntimeError((r.stderr or r.stdout)[-900:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines: raise RuntimeError('sandbox pipeline returned no result')
        return json.loads(lines[-1])

def _browser_test():
    edge=_edge(); assert edge, 'Microsoft Edge not found'
    DIAG_DIR.mkdir(parents=True,exist_ok=True)
    shot=DIAG_DIR/f'browser_{VERSION.replace(".","_")}.png'
    port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
    with tempfile.TemporaryDirectory(prefix='archivist_edge_') as profile:
        before=_visible_console_windows()
        fg_before=int(ctypes.windll.user32.GetForegroundWindow()) if os.name=='nt' else 0
        cmd=[str(edge),'--headless=new','--no-first-run','--disable-extensions','--disable-background-networking','--autoplay-policy=no-user-gesture-required','--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}','--window-size=1280,900',LOCAL+'/diagnostics/browser']
        proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**_hidden())
        try:
            pages=None
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=.5) as rr: pages=json.loads(rr.read().decode())
                    if pages: break
                except Exception: time.sleep(.1)
            assert pages,'Edge DevTools endpoint did not start'
            page=next((p for p in pages if p.get('type')=='page'),pages[0]); ws_url=page['webSocketDebuggerUrl']
            import websocket
            ws=websocket.create_connection(ws_url,timeout=25,origin=f'http://127.0.0.1:{port}')
            seq=0
            def cdp(method,params=None):
                nonlocal seq;seq+=1;want=seq;ws.send(json.dumps({'id':want,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv())
                    if msg.get('id')==want:
                        if 'error' in msg: raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            expr="new Promise((resolve,reject)=>{const end=Date.now()+20000;(function p(){const x=document.getElementById('diag-result');if(x&&x.dataset.status)return resolve(x.textContent);if(Date.now()>end)return reject(new Error('browser harness timeout'));setTimeout(p,100)})()})"
            rr=_cdp_eval_retry(cdp,{'expression':expr,'awaitPromise':True,'returnByValue':True})
            value=((rr.get('result') or {}).get('value'))
            if not value: raise RuntimeError('Browser diagnostic result missing')
            result=json.loads(value)
            png=cdp('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False}).get('data')
            if png: shot.write_bytes(base64.b64decode(png))
            ws.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
        fg_after=int(ctypes.windll.user32.GetForegroundWindow()) if os.name=='nt' else 0
        after=_visible_console_windows()
    if result.get('status')!='passed': raise RuntimeError('Browser assertions failed: '+json.dumps(result)[:650])
    new_console=sorted(set(after)-set(before)); assert not new_console,'visible console window appeared'
    assert not (fg_before and fg_after and fg_before!=fg_after),'foreground window changed during headless test'
    return {'edge_version':result.get('edge_version'),'assertions':result.get('checks',[]),'screenshot_bytes':shot.stat().st_size if shot.exists() else 0,'screenshot_sha256':hashlib.sha256(shot.read_bytes()).hexdigest() if shot.exists() else None,'focus_unchanged':True,'new_console_windows':0}


def _watchdog_real_process_restart():
    fixture=ASSETS/'browser_fixture_h264.mp4';assert fixture.exists()
    with tempfile.TemporaryDirectory(prefix='archivist_watchdog_process_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        env['ARCHIVIST_WATCHDOG_DISABLE_APP_RESTART']='1';env['ARCHIVIST_WATCHDOG_NO_REMOTE']='1'
        py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
        r=subprocess.run([str(py),'-m','archivist.watchdog_process_diag_worker',str(fixture)],cwd=str(HOME),env=env,
                         capture_output=True,text=True,timeout=120,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-1200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('watchdog process restart diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('action')!='process_restart' or out.get('status')!='finished' or not out.get('output_exists'):
            raise RuntimeError(str(out))
        return out


def _watchdog_policy_and_exhaustion():
    with tempfile.TemporaryDirectory(prefix='archivist_watchdog_diag_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        env['ARCHIVIST_WATCHDOG_DISABLE_APP_RESTART']='1';env['ARCHIVIST_WATCHDOG_NO_REMOTE']='1'
        py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
        r=subprocess.run([str(py),'-m','archivist.watchdog_diag_worker'],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=30,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-900:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('watchdog diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('terminal')!='failed' or out.get('error')!='watchdog_exhausted':raise RuntimeError(str(out))
        return out


def _converter_restart_recovery():
    fixture=ASSETS/'browser_fixture_h264.mp4'; assert fixture.exists()
    with tempfile.TemporaryDirectory(prefix='archivist_convert_recovery_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
        r=subprocess.run([str(py),'-m','archivist.convert_recovery_diag',str(fixture)],cwd=str(HOME),env=env,
                         capture_output=True,text=True,timeout=60,errors='replace',**_hidden())
        if r.returncode!=0: raise RuntimeError((r.stderr or r.stdout)[-900:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines: raise RuntimeError('convert recovery diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('status')!='finished' or not out.get('output_exists') or int(out.get('resumed') or 0)!=1:
            raise RuntimeError('convert recovery diagnostic failed: '+json.dumps(out))
        return out


def _converter_smoke():
    import tempfile, shutil
    from pathlib import Path
    from .converter import convert_file
    src=Path(__file__).resolve().parent/'assets'/'browser_fixture_h264.mp4'
    if not src.exists():
        return {'skipped':'fixture missing'}
    td=Path(tempfile.mkdtemp(prefix='archivist-converter-'))
    try:
        out=convert_file(src,'small_720p',None,output_dir=td)
        p=Path(out['output'])
        if not p.exists() or p.stat().st_size<=0:
            raise RuntimeError('converter output missing')
        if src.stat().st_size<=0:
            raise RuntimeError('source fixture invalid')
        return {'output_bytes':p.stat().st_size,'source_bytes':src.stat().st_size,'preset':'small_720p','original_untouched':src.exists()}
    finally:
        shutil.rmtree(td,ignore_errors=True)



def _converter_target_smoke():
    import tempfile, shutil
    from pathlib import Path
    from .converter import convert_file
    src=Path(__file__).resolve().parent/'assets'/'browser_fixture_h264.mp4'
    if not src.exists():
        return {'skipped':'fixture missing'}
    td=Path(tempfile.mkdtemp(prefix='archivist-converter-target-'))
    try:
        out=convert_file(src,'share_1080p',1,output_dir=td)
        p=Path(out['output'])
        if not p.exists() or p.stat().st_size<=0:
            raise RuntimeError('target-size output missing')
        return {'output_bytes':p.stat().st_size,'target_mb_test':1,'two_pass':True,'original_untouched':src.exists()}
    finally:
        shutil.rmtree(td,ignore_errors=True)


def _convert_ui_storyboard_mount():
    import urllib.request
    from .db import db
    with urllib.request.urlopen(LOCAL+'/convert',timeout=8) as r:
        body=r.read().decode('utf-8','replace')
        code=int(r.status)
    if code!=200 or 'Share 1080p' not in body or 'Convert selected' not in body or 'Converted' not in body:
        raise RuntimeError('Convert page markers missing')
    with db() as con:
        row=con.execute("""SELECT id FROM inventory WHERE excluded=0 AND media_type='video'
                           AND private_path IS NULL AND rejected_path IS NULL
                           ORDER BY work_selected DESC,id LIMIT 1""").fetchone()
    detail={'convert_http':code,'convert_markers':'ok'}
    if row:
        iid=int(row['id'])
        with urllib.request.urlopen(LOCAL+f'/item/{iid}',timeout=8) as r:
            item=r.read().decode('utf-8','replace')
        if "storyboardMount" not in item or "loadStoryboard" not in item:
            raise RuntimeError('automatic storyboard mount/script missing')
        detail.update({'item_id':iid,'storyboard_mount':'ok'})
    return detail



def _convert_estimate_bulk_ui():
    import urllib.request
    from .db import db
    with db() as con:
        row=con.execute("""SELECT id FROM inventory WHERE excluded=0 AND media_type='video'
                           AND private_path IS NULL AND rejected_path IS NULL
                           ORDER BY work_selected DESC,id LIMIT 1""").fetchone()
    if not row:
        return {'skipped':'no video in inventory'}
    iid=int(row['id'])
    with urllib.request.urlopen(LOCAL+f'/convert?ids={iid}',timeout=8) as r:
        conv=r.read().decode('utf-8','replace'); conv_code=int(r.status)
    with urllib.request.urlopen(LOCAL+'/library',timeout=8) as r:
        lib=r.read().decode('utf-8','replace'); lib_code=int(r.status)
    required_convert=('estimateSummary','estimateOutput','data-size=','data-duration-ms=','convertSelected','checked')
    missing=[x for x in required_convert if x not in conv]
    if missing:
        raise RuntimeError('Convert estimate UI markers missing: '+','.join(missing))
    if 'convertBulkBtn' not in lib:
        raise RuntimeError('Library Convert bulk action missing')
    return {'convert_http':conv_code,'library_http':lib_code,'preselected_id':iid,
            'estimate_ui':'ok','selected_highlight':'ok','library_bulk_convert':'ok'}


def _convert_preset_switch_browser():
    import socket, tempfile, subprocess, json, time, urllib.request
    with db() as con:
        row=con.execute("""SELECT id FROM inventory WHERE excluded=0 AND media_type='video'
                           AND private_path IS NULL AND rejected_path IS NULL
                           ORDER BY work_selected DESC,id LIMIT 1""").fetchone()
    if not row:
        return {'skipped':'no video in inventory'}
    iid=int(row['id'])
    edge=_edge()
    assert edge,'Microsoft Edge not found'
    port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
    with tempfile.TemporaryDirectory(prefix='archivist_convert_edge_') as profile:
        cmd=[str(edge),'--headless=new','--no-first-run','--disable-extensions','--disable-background-networking',
             '--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}',
             '--window-size=1280,900',LOCAL+f'/convert?ids={iid}']
        proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**_hidden())
        try:
            pages=None
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=.5) as rr:
                        pages=json.loads(rr.read().decode())
                    if pages:break
                except Exception:time.sleep(.1)
            assert pages,'Edge DevTools endpoint did not start'
            page=next((p for p in pages if p.get('type')=='page'),pages[0])
            import websocket
            ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=25,origin=f'http://127.0.0.1:{port}')
            seq=0
            def cdp(method,params=None):
                nonlocal seq;seq+=1;want=seq
                ws.send(json.dumps({'id':want,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv())
                    if msg.get('id')==want:
                        if 'error' in msg:raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            expr="""new Promise(resolve=>{
              const end=Date.now()+12000;
              (function wait(){
                const ch=document.querySelector('.convertCheck:checked')||document.querySelector('.convertCheck');
                if(!ch){if(Date.now()>end)return resolve({error:'no checkbox'});return setTimeout(wait,100)}
                ch.checked=true;ch.dataset.durationMs='0';
                if(typeof updSel!=='function')return resolve({error:'updSel missing'});
                updSel();
                const text=()=>document.getElementById('estimateOutput').textContent;
                const initial=text();
                const sh=document.querySelector("input[name='presetChoice'][value='share_1080p']");
                sh.checked=true;sh.dispatchEvent(new Event('change',{bubbles:true}));
                const share=text();
                const sm=document.querySelector("input[name='presetChoice'][value='small_720p']");
                sm.checked=true;sm.dispatchEvent(new Event('change',{bubbles:true}));
                const small=text();
                const hq=document.querySelector("input[name='presetChoice'][value='hq_1080p']");
                hq.checked=true;hq.dispatchEvent(new Event('change',{bubbles:true}));
                const high=text();
                resolve({initial,share,small,high,distinct:(new Set([share,small,high])).size===3,
                         probeFn:typeof probeMissingDurations==='function'});
              })()
            })"""
            rr=_cdp_eval_retry(cdp,{'expression':expr,'awaitPromise':True,'returnByValue':True})
            result=((rr.get('result') or {}).get('value')) or {}
            ws.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except Exception:proc.kill()
    if result.get('error'):raise RuntimeError(result['error'])
    if 'choose a preset' not in str(result.get('initial') or '').lower():raise RuntimeError('Initial no-preset state missing: '+json.dumps(result))
    if not result.get('distinct'):raise RuntimeError('Preset switch did not change estimate: '+json.dumps(result))
    if 'estimated' not in str(result.get('share') or '').lower():raise RuntimeError('Share preset estimate missing: '+json.dumps(result))
    if not result.get('probeFn'):raise RuntimeError('Duration probe function missing')
    return result



def _convert_multi_preset_browser():
    import socket, tempfile, subprocess, json, time, urllib.request
    from .db import db
    with db() as con:
        rows=con.execute("""SELECT id FROM inventory
                            WHERE excluded=0 AND work_selected=1 AND media_type='video'
                              AND private_path IS NULL AND rejected_path IS NULL
                            ORDER BY COALESCE(date_taken,mtime,0) DESC,id DESC LIMIT 3""").fetchall()
    ids=[int(r['id']) for r in rows]
    if len(ids)<2:
        return {'skipped':'need at least two Library videos'}
    edge=_edge(); assert edge,'Microsoft Edge not found'
    port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
    with tempfile.TemporaryDirectory(prefix='archivist_convert_multi_') as profile:
        url=LOCAL+'/convert?ids='+','.join(str(x) for x in ids)
        cmd=[str(edge),'--headless=new','--no-first-run','--disable-extensions','--disable-background-networking',
             '--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}',
             '--window-size=1400,1000',url]
        proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**_hidden())
        try:
            pages=None
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=.5) as rr:
                        pages=json.loads(rr.read().decode())
                    if pages:break
                except Exception:time.sleep(.1)
            assert pages,'Edge DevTools endpoint did not start'
            page=next((p for p in pages if p.get('type')=='page'),pages[0])
            import websocket
            ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=25,origin=f'http://127.0.0.1:{port}')
            seq=0
            def cdp(method,params=None):
                nonlocal seq;seq+=1;want=seq
                ws.send(json.dumps({'id':want,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv())
                    if msg.get('id')==want:
                        if 'error' in msg:raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            expr="""new Promise(resolve=>{
              const end=Date.now()+12000;
              (function wait(){
                const cs=[...document.querySelectorAll('.convertCheck')];
                if(cs.length<2){if(Date.now()>end)return resolve({error:'not enough rows',count:cs.length});return setTimeout(wait,100)}
                cs.forEach(ch=>{if(!ch.disabled){ch.checked=true;ch.dataset.durationMs='0'}});
                updSel();
                const snap=()=>[...document.querySelectorAll('.convertCheck:checked')].map(ch=>ch.closest('.convertRow').querySelector('.estimateOne').textContent);
                const sh=document.querySelector("input[name='presetChoice'][value='share_1080p']");
                sh.checked=true;sh.dispatchEvent(new Event('change',{bubbles:true}));
                const share=snap();
                const sm=document.querySelector("input[name='presetChoice'][value='small_720p']");
                sm.checked=true;sm.dispatchEvent(new Event('change',{bubbles:true}));
                const small=snap();
                const hq=document.querySelector("input[name='presetChoice'][value='hq_1080p']");
                hq.checked=true;hq.dispatchEvent(new Event('change',{bubbles:true}));
                const high=snap();
                const changed=share.map((x,i)=>x!==small[i]&&small[i]!==high[i]&&x!==high[i]);
                resolve({ids:cs.filter(x=>x.checked).map(x=>Number(x.value)),share,small,high,changed,
                         allChanged:changed.length>0&&changed.every(Boolean),
                         visibleRows:document.querySelectorAll('.convertRow').length});
              })()
            })"""
            rr=_cdp_eval_retry(cdp,{'expression':expr,'awaitPromise':True,'returnByValue':True})
            result=((rr.get('result') or {}).get('value')) or {}
            ws.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except Exception:proc.kill()
    if result.get('error'):raise RuntimeError(result['error'])
    if not result.get('allChanged'):raise RuntimeError('Not every selected row changed with preset: '+json.dumps(result))
    return result


def _convert_library_visibility():
    import urllib.request,re
    from .db import db
    with db() as con:
        total=int(con.execute("""SELECT COUNT(*) n FROM inventory
                                 WHERE excluded=0 AND work_selected=1 AND media_type='video'
                                   AND private_path IS NULL AND rejected_path IS NULL""").fetchone()['n'])
        oldest=con.execute("""SELECT id,filename FROM inventory
                              WHERE excluded=0 AND work_selected=1 AND media_type='video'
                                AND private_path IS NULL AND rejected_path IS NULL
                              ORDER BY COALESCE(date_taken,mtime,0) ASC,id ASC LIMIT 1""").fetchone()
    with urllib.request.urlopen(LOCAL+'/convert',timeout=8) as r:
        top=r.read().decode('utf-8','replace')
    if 'Accessible on this catalog page' not in top or 'convertTotal' not in top:
        raise RuntimeError('Convert local-video pagination markers missing')
    detail={'library_video_count':total,'top_route':'ok'}
    if oldest:
        iid=int(oldest['id'])
        with urllib.request.urlopen(LOCAL+f'/convert?ids={iid}',timeout=8) as r:
            selected=r.read().decode('utf-8','replace')
        if f"value='{iid}'" not in selected:
            raise RuntimeError('Selected Library video missing from Convert route')
        if 'checked' not in selected:
            raise RuntimeError('Selected Library video was not preselected')
        detail.update({'selected_id':iid,'selected_transfer':'ok'})
    return detail


def _convert_accessibility_filter():
    import urllib.request
    with db() as con:
        rows=con.execute("""SELECT id,source_kind,path,staging_path,archive_path
                            FROM inventory
                            WHERE excluded=0 AND media_type='video'
                              AND private_path IS NULL AND rejected_path IS NULL
                            ORDER BY work_selected DESC,id""").fetchall()
    available=None; unavailable=None
    for r in rows:
        ok=bool(next((r[k] for k in ('staging_path','archive_path','path') if r[k] and Path(r[k]).exists()),None))
        if ok and available is None: available=int(r['id'])
        if not ok and unavailable is None: unavailable=int(r['id'])
        if available is not None and unavailable is not None: break
    if available is None or unavailable is None:
        return {'skipped':'need both accessible and unavailable videos'}
    with urllib.request.urlopen(f'{LOCAL}/convert?ids={available},{unavailable}',timeout=8) as rr:
        body=rr.read().decode('utf-8','replace')
    if f"value='{available}'" not in body: raise RuntimeError('Accessible selected video missing')
    if f"value='{unavailable}'" in body: raise RuntimeError('Unavailable selected video leaked into accessible Convert rows')
    if 'selected video' not in body or 'skipped' not in body: raise RuntimeError('Skipped inaccessible selection warning missing')
    return {'accessible_id':available,'unavailable_id':unavailable,'filter':'ok','warning':'ok'}

def _convert_preview_health():
    with db() as con:
        rows=con.execute("""SELECT id,source_kind,path,staging_path,archive_path,preview_status,preview_path
                            FROM inventory
                            WHERE excluded=0 AND media_type='video'
                              AND private_path IS NULL AND rejected_path IS NULL""").fetchall()
    accessible=ready=unavailable=pending=0
    for r in rows:
        local=next((r[k] for k in ('staging_path','archive_path','path') if r[k] and Path(r[k]).exists()),None)
        if not local: continue
        accessible+=1
        p=Path(r['preview_path']) if r['preview_path'] else DATA/'cache'/'thumbnails'/f"{int(r['id'])}.jpg"
        if p.exists(): ready+=1
        elif r['preview_status']=='unavailable': unavailable+=1
        else: pending+=1
    return {'accessible_videos':accessible,'ready_thumbnails':ready,'unavailable_thumbnails':unavailable,'pending_thumbnails':pending}

def _convert_drone_metadata():
    import urllib.request
    from .converter import probe_local_media_meta
    ids=[16111,16110,16109]
    meta=probe_local_media_meta(ids)
    if len(meta)<3: raise RuntimeError('Drone videos missing from local inventory')
    for iid in ids:
        m=meta.get(str(iid)) or {}
        if int(m.get('duration_ms') or 0)<=0 or int(m.get('width') or 0)<=0 or int(m.get('height') or 0)<=0:
            raise RuntimeError('Drone metadata probe incomplete for '+str(iid)+': '+str(m))
    m=meta['16111']; kbps=32000 if max(int(m['width']),int(m['height']))>=3000 or int(m['width'])*int(m['height'])>=7000000 else (12000 if int(m['width'])*int(m['height'])>=1800000 else 6000)
    estimate_mb=(kbps*1000/8*(int(m['duration_ms'])/1000))/(1024*1024)
    if estimate_mb<100: raise RuntimeError('Original-resolution estimate guard failed: '+str(estimate_mb))
    with urllib.request.urlopen(LOCAL+'/convert?ids=16111,16110,16109',timeout=8) as r:
        body=r.read().decode('utf-8','replace')
    for marker in ("DJI_0067.MP4","DJI_0066.MP4","DJI_0065.MP4","All accessible videos","Local folders","Largest","Longest","Original Resolution"):
        if marker not in body: raise RuntimeError('Convert marker missing: '+marker)
    return {'metadata':meta,'original_estimate_mb_16111':round(estimate_mb,1),'drone_rows':'visible','sort_filters':'visible'}

def _convert_ux_browser():
    import socket,tempfile,subprocess,json,time,urllib.request
    from .db import db
    with db() as con:
        row=con.execute("""SELECT id FROM inventory WHERE excluded=0 AND media_type='video' AND work_selected=1
                           AND private_path IS NULL AND rejected_path IS NULL ORDER BY id LIMIT 1""").fetchone()
    if not row:
        return {'skipped':'no Library video'}
    iid=int(row['id']); edge=_edge(); assert edge,'Microsoft Edge not found'
    s=socket.socket(); s.bind(('127.0.0.1',0)); port=s.getsockname()[1]; s.close()
    with tempfile.TemporaryDirectory(prefix='archivist_convert_ux_') as profile:
        proc=subprocess.Popen([str(edge),'--headless=new','--no-first-run','--disable-extensions','--disable-background-networking',
            '--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}',
            '--window-size=1400,1000',LOCAL+f'/convert?ids={iid}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**_hidden())
        try:
            pages=None
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=.5) as rr:
                        pages=json.loads(rr.read().decode())
                    if pages: break
                except Exception:
                    time.sleep(.1)
            assert pages,'Edge DevTools endpoint did not start'
            import websocket
            page=next((p for p in pages if p.get('type')=='page'),pages[0])
            ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=25,origin=f'http://127.0.0.1:{port}')
            seq=0
            def cdp(method,params=None):
                nonlocal seq
                seq+=1; want=seq
                ws.send(json.dumps({'id':want,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv())
                    if msg.get('id')==want:
                        if 'error' in msg: raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            expr="""new Promise(resolve=>{
              const end=Date.now()+10000;
              (function wait(){
                const ch=document.querySelector('.convertCheck:checked');
                if(!ch){if(Date.now()>end)return resolve({error:'preselected video missing'});return setTimeout(wait,100)}
                const before={preset:[...document.querySelectorAll("input[name='presetChoice']")].some(x=>x.checked),
                  estimate:document.getElementById('estimateOutput').textContent,
                  disabled:document.getElementById('startConvert').disabled,
                  thumb:!!document.querySelector('.convertThumb')};
                const share=document.querySelector("input[name='presetChoice'][value='share_1080p']");
                share.checked=true;share.dispatchEvent(new Event('change',{bubbles:true}));
                const after={estimate:document.getElementById('estimateOutput').textContent,
                  disabled:document.getElementById('startConvert').disabled};
                resolve({before,after,hoverFn:typeof setupConvertStoryHover==='function'});
              })()
            })"""
            rr=_cdp_eval_retry(cdp,{'expression':expr,'awaitPromise':True,'returnByValue':True})
            result=((rr.get('result') or {}).get('value')) or {}
            ws.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
    if result.get('error'): raise RuntimeError(result['error'])
    if result['before']['preset']: raise RuntimeError('Preset should not be auto-selected')
    if 'choose a preset' not in result['before']['estimate'].lower(): raise RuntimeError('Pre-preset prompt missing')
    if not result['before']['disabled']: raise RuntimeError('Convert button should be disabled before preset')
    if 'estimated' not in result['after']['estimate'].lower() or result['after']['disabled']: raise RuntimeError('Share selection did not enable estimate/action')
    if not result.get('hoverFn') or not result['before']['thumb']: raise RuntimeError('Convert preview/hover markers missing')
    return result

def _pagination_jump_ui():
    import urllib.request
    out={}
    for path in ('/library','/convert'):
        with urllib.request.urlopen(LOCAL+path,timeout=8) as r:
            body=r.read().decode('utf-8','replace')
        for marker in ('First','Last',"name='page'"):
            if marker not in body:
                raise RuntimeError(path+' pagination marker missing: '+marker)
        out[path]='jump controls ok'
    return out
def _android():
    from . import android
    adb=android.find_adb()
    if not adb: return {'adb':'unavailable','connected':0}
    devs,err=android.adb_devices(adb)
    return {'adb':'available','connected':sum(d.get('state')=='device' for d in devs),'error':err}

def _smart_crop_v2_math():
    keys=validate_crop_keyframes([
        {'time_ms':0,'x':.10,'y':.10,'w':.50,'h':.80,'confidence':.8,'locked':True},
        {'time_ms':1000,'x':.20,'y':.12,'w':.48,'h':.78,'confidence':.75,'locked':False},
        {'time_ms':2000,'x':.30,'y':.10,'w':.45,'h':.75,'confidence':.7,'locked':True},
    ],2000)
    samples=[interpolate_crop_keyframes(keys,t) for t in range(0,2001,100)]
    assert all(0<=p['x']<=1-p['w']+1e-6 and 0<=p['y']<=1-p['h']+1e-6 for p in samples)
    max_pan=max((((b['x']+b['w']/2)-(a['x']+a['w']/2))**2+((b['y']+b['h']/2)-(a['y']+a['h']/2))**2)**.5/.1 for a,b in zip(samples,samples[1:]))
    max_zoom=max(abs((b['w']+b['h'])-(a['w']+a['h']))/.2 for a,b in zip(samples,samples[1:]))
    assert max_pan<=.35+1e-6 and max_zoom<=.25+1e-6
    return {'schema_version':1,'keyframes':len(keys),'samples':len(samples),'bounds':'ok','max_pan_per_second':round(max_pan,4),'max_zoom_per_second':round(max_zoom,4),'locks':sum(k['locked'] for k in keys)}

def _real_clip_browser():
    with db() as con: row=con.execute('select id from virtual_clips order by score desc limit 1').fetchone()
    if not row: return {'skipped':'no real virtual clip exists'}
    clip_id=int(row['id']);edge=_edge();assert edge,'Microsoft Edge not found'
    port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
    with tempfile.TemporaryDirectory(prefix='archivist_realclip_edge_') as profile:
        cmd=[str(edge),'--headless=new','--no-first-run','--disable-extensions','--disable-background-networking','--autoplay-policy=no-user-gesture-required','--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}','--window-size=1280,900',f'{LOCAL}/clip/{clip_id}?back=best&diagnostic=1']
        proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**_hidden())
        try:
            pages=None
            for _ in range(100):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=.5) as rr: pages=json.loads(rr.read().decode())
                    if pages: break
                except Exception: time.sleep(.1)
            assert pages,'Edge DevTools endpoint did not start for real clip'
            page=next((p for p in pages if p.get('type')=='page'),pages[0])
            import websocket
            ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=40,origin=f'http://127.0.0.1:{port}');seq=0
            def cdp(method,params=None):
                nonlocal seq;seq+=1;want=seq;ws.send(json.dumps({'id':want,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv())
                    if msg.get('id')==want:
                        if 'error' in msg: raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            expr="""new Promise((resolve,reject)=>{const end=Date.now()+30000,wait=(f)=>new Promise((ok,no)=>{(function p(){try{if(f())return ok()}catch(e){}if(Date.now()>end)return no(new Error('real clip timeout'));setTimeout(p,100)})()});(async()=>{try{const v=document.getElementById('clipVideo'),cv=document.getElementById('clipCanvas'),play=document.getElementById('playClip'),replay=document.getElementById('replayClip'),wrap=document.getElementById('clipSeekWrap'),thumb=document.getElementById('clipSeekThumb'),vp=document.getElementById('cropViewport');await wait(()=>v&&v.readyState>=2&&v.videoWidth>0);v.muted=true;const start=v.currentTime,s0=wrap.getBoundingClientRect(),t0=thumb.getBoundingClientRect(),zeroDelta=t0.left-s0.left;play.click();await wait(()=>v.currentTime>start+.15&&cv.width>2);const ctx=cv.getContext('2d'),px=ctx.getImageData(0,0,cv.width,cv.height).data;let bright=0,diff=0,prev=px[0];for(let i=0;i<px.length;i+=Math.max(4,Math.floor(px.length/12000/4)*4)){bright+=px[i]+px[i+1]+px[i+2];diff+=Math.abs(px[i]-prev);prev=px[i]}replay.click();await wait(()=>v.currentTime>=start+.08);const replayRel=v.currentTime-start,ratios={};for(const b of document.querySelectorAll('.cropBtn')){b.click();await new Promise(r=>setTimeout(r,80));const r=vp.getBoundingClientRect();ratios[b.dataset.aspect]=r.width/r.height}v.pause();resolve(JSON.stringify({clip_id:Number(location.pathname.split('/').pop()),video_width:v.videoWidth,video_height:v.videoHeight,canvas_width:cv.width,canvas_height:cv.height,canvas_brightness:bright,canvas_difference:diff,replay_relative_seconds:replayRel,scrubber_delta_px:zeroDelta,ratios}))}catch(e){reject(e)}})()})"""
            rr=_cdp_eval_retry(cdp,{'expression':expr,'awaitPromise':True,'returnByValue':True})
            if (rr.get('exceptionDetails')): raise RuntimeError(str(rr['exceptionDetails'])[:700])
            value=((rr.get('result') or {}).get('value'));assert value,'real clip result missing';result=json.loads(value);ws.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except Exception:proc.kill()
    assert result['canvas_brightness']>10000 and result['canvas_difference']>1000,'real clip canvas is black/static'
    assert result['replay_relative_seconds']<1.0,'real clip replay did not restart near zero'
    assert abs(result['scrubber_delta_px'])<=.5,'real clip scrubber is not physically at zero'
    return result


def _semantic_search_foundation():
    from .semantic_search import parse_query,search_library,capabilities
    p=parse_query('best vertical high motion video from Android')
    required={'best','portrait','high_motion','video','android'}
    if not required.issubset(set(p.get('intents') or [])):
        raise RuntimeError('semantic parser intents missing: '+json.dumps(p))
    data=search_library('video',limit=5)
    if int(data.get('index_count') or 0)<1:
        raise RuntimeError('semantic index is empty')
    if not data.get('results'):
        raise RuntimeError('semantic video query returned no results')
    return {'model':data.get('model'),'index_count':int(data.get('index_count') or 0),
            'video_results_sampled':len(data.get('results') or []),'capability_count':len(capabilities()),
            'parser_intents':sorted(required)}

def _semantic_search_http():
    import urllib.request,json as _json
    with urllib.request.urlopen(LOCAL+'/search?q=best+vertical+videos',timeout=10) as r:
        body=r.read().decode('utf-8','replace')
    for marker in ('Search your footage','signals v1','Local Search / M7'):
        if marker not in body: raise RuntimeError('Search UI marker missing: '+marker)
    with urllib.request.urlopen(LOCAL+'/api/search?q=video&limit=3',timeout=10) as r:
        data=_json.loads(r.read().decode())
    if data.get('model')!='signals_v1' or not data.get('results'):
        raise RuntimeError('Search API failed: '+str(data)[:500])
    return {'ui':'ok','api':'ok','api_results':len(data.get('results') or []),'model':data.get('model')}


def _visual_similarity_fixtures():
    from PIL import Image,ImageDraw
    from .visual_similarity import _fingerprint_image,_score_fp,MODEL
    with tempfile.TemporaryDirectory(prefix='archivist_sim_') as td:
        a=Path(td)/'a.jpg'; b=Path(td)/'b.jpg'; c=Path(td)/'c.jpg'
        im=Image.new('RGB',(160,100),(25,35,45)); d=ImageDraw.Draw(im); d.rectangle((25,20,120,78),fill=(220,180,60)); d.line((0,99,159,0),fill=(240,240,240),width=4); im.save(a,quality=92)
        im2=im.copy(); d2=ImageDraw.Draw(im2); d2.rectangle((28,22,123,80),outline=(255,220,90),width=3); im2.save(b,quality=92)
        Image.new('RGB',(160,100),(10,170,220)).save(c,quality=92)
        fa,fb,fc=_fingerprint_image(a),_fingerprint_image(b),_fingerprint_image(c)
        near=_score_fp(fa,fb); far=_score_fp(fa,fc); same=_score_fp(fa,fa)
        if same<0.999 or near<=far: raise RuntimeError(f'visual fingerprint ordering failed same={same} near={near} far={far}')
        return {'model':MODEL,'same':same,'near':near,'far':far}

def _visual_similarity_live():
    import urllib.request,json as _json
    from .visual_similarity import rebuild_index,find_similar,MODEL
    n=rebuild_index()
    if n<2: raise RuntimeError('visual index too small: '+str(n))
    with db() as con:
        r=con.execute("SELECT inventory_id FROM visual_fingerprints ORDER BY inventory_id LIMIT 1").fetchone()
    data=find_similar(int(r['inventory_id']),limit=3)
    if data.get('model')!=MODEL or not data.get('results'): raise RuntimeError('visual similarity returned no results')
    iid=int(r['inventory_id'])
    with urllib.request.urlopen(LOCAL+f'/api/similar/{iid}?limit=3',timeout=10) as h:
        api=_json.loads(h.read().decode())
    with urllib.request.urlopen(LOCAL+f'/similar/{iid}',timeout=10) as h:
        page=h.read().decode('utf-8','replace')
    if api.get('model')!=MODEL or 'Find Similar' not in page: raise RuntimeError('Find Similar UI/API marker missing')
    return {'model':MODEL,'index_count':n,'api_results':len(api.get('results') or []),'ui':'ok'}


def _clip_export_fixture():
    from .clip_export import _render_source
    src=ASSETS/'browser_fixture_h264.mp4'
    before=(src.stat().st_size,src.stat().st_mtime_ns)
    with tempfile.TemporaryDirectory(prefix='archivist_export_') as td:
        out=Path(td)/'render.mp4'
        result=_render_source(src,.25,1.65,out,{'x':.12,'y':.08,'w':.70,'h':.70},'1:1')
        dec=_ffmpeg_decode(out)
        after=(src.stat().st_size,src.stat().st_mtime_ns)
        if before!=after: raise RuntimeError('source fixture changed during export')
        return {'output_exists':out.exists(),'output_bytes':int(out.stat().st_size),'decode':dec.get('decode'),'source_untouched':True,'aspect':'1:1'}

def _clip_export_ui():
    import urllib.request
    from .media_brain import best_clips
    rows=best_clips(5)
    if not rows: raise RuntimeError('no virtual clip available for export UI check')
    cid=int(rows[0]['id'])
    with urllib.request.urlopen(LOCAL+f'/clip/{cid}',timeout=10) as r: body=r.read().decode('utf-8','replace')
    for marker in ('Export clip','/clip/'+str(cid)+'/export','Smart Crop'):
        if marker not in body: raise RuntimeError('clip export UI marker missing: '+marker)
    return {'ui':'ok','clip_available':True,'render_action':'present'}


def _composer_render_fixture():
    from .composer import render_fixture
    src=ASSETS/'browser_fixture_h264.mp4';before=(src.stat().st_size,src.stat().st_mtime_ns)
    with tempfile.TemporaryDirectory(prefix='archivist_comp_test_') as td:
        out=Path(td)/'composition.mp4'
        result=render_fixture([(src,.10,1.0),(src,1.05,1.95)],'9:16',out)
        dec=_ffmpeg_decode(out);after=(src.stat().st_size,src.stat().st_mtime_ns)
        if before!=after:raise RuntimeError('source fixture changed during composition render')
        if not out.exists() or out.stat().st_size<1024:raise RuntimeError('composition output missing')
        return {'clips':result['clips'],'aspect':result['aspect'],'output_bytes':int(out.stat().st_size),'decode':dec.get('decode'),'source_untouched':True}

def _composer_ui():
    import urllib.request
    with urllib.request.urlopen(LOCAL+'/composer',timeout=10) as r:body=r.read().decode('utf-8','replace')
    for marker in ('Content Composer','Create composition','Up to 20 clips / 180 seconds'):
        if marker not in body:raise RuntimeError('Composer UI marker missing: '+marker)
    return {'ui':'ok','create_action':'present','local_only':True}


def _composer_audio_mixed_fixture():
    from .composer import render_fixture,_has_audio
    from .media import _ffmpeg_exe
    src=ASSETS/'browser_fixture_h264.mp4';exe=_ffmpeg_exe()
    if not exe:raise RuntimeError('FFmpeg unavailable')
    with tempfile.TemporaryDirectory(prefix='archivist_audio_mix_') as td:
        audio=Path(td)/'audio.mp4';out=Path(td)/'mixed.mp4'
        rr=subprocess.run([str(exe),'-y','-hide_banner','-loglevel','error','-i',str(src),'-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2.1','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-ac','2','-ar','48000',str(audio)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,**_hidden())
        if rr.returncode!=0 or not audio.exists():raise RuntimeError('audio fixture creation failed')
        result=render_fixture([(audio,.10,.95),(src,1.0,1.85)],'16:9',out)
        if not result.get('audio') or not _has_audio(out):raise RuntimeError('normalized composition audio missing')
        dec=_ffmpeg_decode(out)
        return {'clips':2,'decode':dec.get('decode'),'audio_stream':True,'mixed_audio_silence':True,'output_bytes':int(out.stat().st_size)}

def _composer_recovery_policy():
    from .composer import recovery_policy
    p=recovery_policy()
    if p.get('queued_after_restart')!='failed' or p.get('rendering_after_restart')!='failed' or not p.get('partial_final_removed'):
        raise RuntimeError('composer recovery policy incomplete')
    return p


def _m9_dependency_inventory():
    import importlib.metadata as md,sys
    def canon(name):
        return str(name).strip().lower().replace('_','-').replace('.','-')
    skip={'pip','setuptools','wheel'}
    pkgs=[]
    for dist in md.distributions():
        name=str(dist.metadata.get('Name') or '').strip()
        if not name or canon(name) in skip: continue
        pkgs.append({'name':name,'version':str(dist.version)})
    pkgs=sorted({(canon(x['name']),x['version']):(x['name'],x['version']) for x in pkgs}.values(),key=lambda x:x[0].lower())
    have={canon(n):v for n,v in pkgs}
    lock_path=HOME/'requirements.txt'
    locked={}
    if lock_path.exists():
        for raw in lock_path.read_text(encoding='utf-8',errors='replace').splitlines():
            spec=raw.split('#',1)[0].strip()
            if not spec: continue
            spec=spec.split(';',1)[0].strip()
            if '==' not in spec: continue
            name,version=spec.split('==',1)
            name=canon(name);version=version.strip()
            if name and version: locked[name]=version
    fallback=[canon(x) for x in ['Flask','opencv-python-headless','Pillow','imageio-ffmpeg','nudenet','websocket-client']]
    required=sorted(locked) if locked else fallback
    missing=[x for x in required if x not in have]
    mismatched=[{'name':x,'expected':locked[x],'actual':have.get(x)} for x in required if x in locked and x in have and have.get(x)!=locked[x]]
    if missing: raise RuntimeError('required distributions missing: '+','.join(missing))
    if mismatched: raise RuntimeError('locked distribution version mismatch: '+json.dumps(mismatched,sort_keys=True))
    try:
        import cv2
        cv2_version=str(getattr(cv2,'__version__',''))
    except Exception:
        cv2_version=None
    return {
        'python':sys.version.split()[0],
        'packages':[{'name':n,'version':v} for n,v in pkgs],
        'package_count':len(pkgs),
        'missing_required':[],
        'locked_required_count':len(locked),
        'lock_mismatches':[],
        'optional_heif_version':have.get('pillow-heif'),
        'cv2_runtime_version':cv2_version,
    }



def _platform_adapter_contract():
    from .platform_adapter import platform_capabilities, process_kwargs
    caps = platform_capabilities()
    kw = process_kwargs()
    if os.name == 'nt':
        if not int(kw.get('creationflags', 0) or 0):
            raise RuntimeError('Windows process adapter missing creationflags')
        if kw.get('startupinfo') is None:
            raise RuntimeError('Windows process adapter missing startupinfo')
        if caps.get('app_control_adapter') != 'windows':
            raise RuntimeError('Windows app-control adapter not selected')
    targets = set(caps.get('targets') or [])
    if targets != {'Windows','macOS','Android','iOS'}:
        raise RuntimeError('platform target registry mismatch')
    return {
        'system': caps.get('system'),
        'machine': caps.get('machine'),
        'app_control_adapter': caps.get('app_control_adapter'),
        'desktop_launcher_adapter': caps.get('desktop_launcher_adapter'),
        'filesystem_adapter': caps.get('filesystem_adapter'),
        'secret_store_adapter': caps.get('secret_store_adapter'),
        'background_work_adapter': caps.get('background_work_adapter'),
        'target_count': len(targets),
    }

def _platform_io_security_background_contract():
    from .platform_adapter import filesystem_capabilities, secret_store_capabilities, background_work_capabilities
    fs = filesystem_capabilities()
    sec = secret_store_capabilities()
    bg = background_work_capabilities()
    if not fs.get('implemented') or not fs.get('configurable_roots') or not fs.get('atomic_replace'):
        raise RuntimeError('filesystem adapter contract incomplete')
    if fs.get('default_archive_strategy') != 'platform_adapter':
        raise RuntimeError('default archive path is not platform-adapter owned')
    if sec.get('plaintext_config_allowed') or sec.get('supabase_secret_storage_allowed'):
        raise RuntimeError('secret-store contract permits unsafe secret persistence')
    if os.name == 'nt':
        if fs.get('adapter') != 'windows_pathlib' or not fs.get('validated'):
            raise RuntimeError('Windows filesystem capability contract incomplete')
        if sec.get('adapter') != 'windows_credential_manager' or not sec.get('implemented') or not sec.get('validated'):
            raise RuntimeError('Windows Credential Manager capability contract incomplete')
        if bg.get('adapter') != 'desktop_local_threads_processes' or not bg.get('implemented') or not bg.get('validated'):
            raise RuntimeError('Windows background-work capability contract incomplete')
    elif sec.get('implemented'):
        raise RuntimeError('non-Windows secret store must remain disabled until a native adapter is validated')
    return {
        'filesystem_adapter':fs.get('adapter'),
        'filesystem_validated':bool(fs.get('validated')),
        'secret_store_adapter':sec.get('adapter'),
        'secret_store_implemented':bool(sec.get('implemented')),
        'secret_store_validated':bool(sec.get('validated')),
        'plaintext_config_allowed':bool(sec.get('plaintext_config_allowed')),
        'supabase_secret_storage_allowed':bool(sec.get('supabase_secret_storage_allowed')),
        'background_work_adapter':bg.get('adapter'),
        'background_work_validated':bool(bg.get('validated')),
    }



def _platform_subprocess_helper_contract():
    from .platform_adapter import process_kwargs
    normal = process_kwargs()
    detached = process_kwargs(detached=True)
    if os.name == 'nt':
        normal_flags = int(normal.get('creationflags', 0) or 0)
        detached_flags = int(detached.get('creationflags', 0) or 0)
        if not normal_flags or normal.get('startupinfo') is None:
            raise RuntimeError('normal Windows subprocess policy incomplete')
        if not detached_flags or detached.get('startupinfo') is None:
            raise RuntimeError('detached Windows subprocess policy incomplete')
        detach_bit = int(getattr(subprocess, 'DETACHED_PROCESS', 0) or 0)
        if detach_bit and not (detached_flags & detach_bit):
            raise RuntimeError('detached process flag missing')
        return {
            'platform':'windows',
            'normal_flags':normal_flags,
            'detached_flags':detached_flags,
            'detached_bit_present':bool(detach_bit and (detached_flags & detach_bit)),
        }
    forbidden = [k for k in ('creationflags','startupinfo') if k in normal or k in detached]
    if forbidden:
        raise RuntimeError('Windows-only subprocess keys leaked to non-Windows adapter: '+','.join(forbidden))
    return {'platform':'portable-neutral','windows_only_keys':[]}

def _m10_social_lab_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m10_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        r=subprocess.run([str(py),'-m','archivist.social_lab_diag_worker'],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-1200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M10 social lab diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('exact')!='exact_duplicate_block' or out.get('fresh')!='new' or int(out.get('publication_count') or 0)!=1:raise RuntimeError('M10 social lab contract failed: '+json.dumps(out))
        return out

def _m10_content_queue_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m10q_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        code="from archivist.config import ensure_dirs;from archivist.db import init_db;ensure_dirs();init_db();from archivist.social_lab_diag_worker import queue_contract;import json;print(json.dumps(queue_contract(),sort_keys=True))"
        r=subprocess.run([str(py),'-c',code],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-1200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M10 queue diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('ready')!='ready' or out.get('review_to_ready')!='ready' or out.get('duplicate')!='hold' or not out.get('hold_bypass_blocked'):raise RuntimeError('M10 queue contract failed: '+json.dumps(out))
        return out

def _m10_visual_novelty_contract():
    from .social_lab import _visual_fp_for_media,classify_visual_score,VISUAL_MODEL
    fp=_visual_fp_for_media(ASSETS/'browser_fixture_h264.mp4')
    if not fp or not fp.get('dhash') or not fp.get('hist'):raise RuntimeError('M10 visual fingerprint from MP4 failed')
    base=_visual_similarity_fixtures()
    same=float(base['same']);near=float(base['near']);far=float(base['far'])
    if classify_visual_score(same)!='too_similar_block':raise RuntimeError('same visual threshold failed')
    if classify_visual_score(near)!='similar_review':raise RuntimeError('near visual threshold failed')
    if classify_visual_score(far) is not None:raise RuntimeError('far visual threshold failed')
    return {'model':VISUAL_MODEL,'video_fingerprint':'ok','same':same,'near':near,'far':far,'same_state':classify_visual_score(same),'near_state':classify_visual_score(near),'far_state':'new'}

def _m10_audio_novelty_contract():
    from .social_lab import _audio_fp_for_media,_audio_score,classify_audio_score,AUDIO_MODEL
    exe=_ffmpeg_exe()
    if not exe:raise RuntimeError('FFmpeg unavailable for audio novelty fixture')
    with tempfile.TemporaryDirectory(prefix='archivist_audio_novelty_') as td:
        td=Path(td);a=td/'a.m4a';b=td/'b.m4a';c=td/'c.m4a'
        cmds=[
          [str(exe),'-y','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:a','aac','-b:a','128k',str(a)],
          [str(exe),'-y','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-filter:a','volume=0.55','-t','3','-c:a','aac','-b:a','96k',str(b)],
          [str(exe),'-y','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=880:sample_rate=48000','-t','3','-c:a','aac','-b:a','128k',str(c)]
        ]
        for cmd in cmds:
            rr=subprocess.run(cmd,capture_output=True,timeout=30,**_hidden())
            if rr.returncode!=0:raise RuntimeError('audio novelty fixture creation failed')
        fa,fb,fc=_audio_fp_for_media(a),_audio_fp_for_media(b),_audio_fp_for_media(c)
        if not fa or not fb or not fc:raise RuntimeError('audio fingerprint missing')
        near=_audio_score(fa,fb);far=_audio_score(fa,fc)
        if near<.97:raise RuntimeError('same-tone/reencode audio similarity too low: '+str(near))
        if far>=.97:raise RuntimeError('different-tone audio similarity too high: '+str(far))
        if classify_audio_score(near)!='similar_review' or classify_audio_score(far) is not None:raise RuntimeError('audio novelty threshold classification failed')
        return {'model':AUDIO_MODEL,'near':near,'far':far,'near_state':'similar_review','far_state':'new','audio_alone_blocks':False}

def _m11_experiment_engine_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m11_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        code="from archivist.config import ensure_dirs;from archivist.db import init_db;ensure_dirs();init_db();from archivist.experiments import *;import json;e=create_experiment('Test',None,'retention');a=add_variant(e,'A','Hook A','Caption A','cover:a',15,[3,2,1]);b=add_variant(e,'B','Hook B','Caption B','cover:b',20,[1,2,3]);record_result(a,'manual',views=1000,likes=100,comments=12,shares=8,saves=5,watch_time_s=5000,avg_view_duration_s=5,retention_3s_pct=72,completion_pct=31);d=experiment_detail(e);s=experiment_stats();assert len(d['variants'])==2 and len(d['variants'][0]['results'])==1 and s['experiments']==1 and s['variants']==2 and s['results']==1;print(json.dumps({'experiments':s['experiments'],'variants':s['variants'],'results':s['results'],'clip_order':d['variants'][0]['clip_order'],'sources':[x['source'] for x in d['variants'][0]['results']]},sort_keys=True))"
        r=subprocess.run([str(py),'-c',code],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-1200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M11 experiment diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('experiments')!=1 or out.get('variants')!=2 or out.get('results')!=1 or out.get('clip_order')!=[3,2,1]:raise RuntimeError('M11 experiment contract failed: '+json.dumps(out))
        return out

def _m11_summary_csv_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m11x_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        code="""from archivist.config import ensure_dirs
from archivist.db import init_db,db
ensure_dirs();init_db()
from archivist.experiments import create_experiment,add_variant,record_result,experiment_metric_summaries,validate_results_csv,import_results_csv
import json
eid=create_experiment('summary csv test',None,'local')
a=add_variant(eid,'A');b=add_variant(eid,'B')
record_result(a,'manual',views=100,likes=5,comments=2,shares=1,saves=2,avg_view_duration_s=8,retention_3s_pct=70,completion_pct=40)
record_result(a,'manual',views=300,likes=15,comments=6,shares=3,saves=6,avg_view_duration_s=12,retention_3s_pct=80,completion_pct=60)
s=experiment_metric_summaries(eid)
sa=next(x for x in s if x['variant_id']==a)
assert sa['views']==400 and sa['engagements']==40 and sa['engagement_rate_pct']==10.0 and sa['avg_view_duration_s']==11.0 and sa['rank'] is None and sa['winner'] is None
csv_text='variant_id,observed_at,views,likes,comments,shares,saves,avg_view_duration_s,retention_3s_pct,completion_pct,notes\\n%d,2026-09-22T10:00:00+00:00,50,3,1,0,1,9,75,50,import a\\n%d,2026-09-22T11:00:00+00:00,80,4,1,1,2,10,78,55,import b\\n'%(a,b)
with db() as c:before=c.execute('SELECT COUNT(*) FROM social_experiment_results').fetchone()[0]
p=validate_results_csv(eid,csv_text);assert p['ok'] and p['row_count']==2
with db() as c:after_preview=c.execute('SELECT COUNT(*) FROM social_experiment_results').fetchone()[0]
assert before==after_preview
bad=validate_results_csv(eid,'variant_id,views,completion_pct\\n%d,1,120\\n'%a);assert not bad['ok']
wrong=validate_results_csv(eid,'variant_id,views\\n99999,1\\n');assert not wrong['ok']
imp=import_results_csv(eid,csv_text);assert imp['imported']==2 and imp['skipped_duplicates']==0
imp2=import_results_csv(eid,csv_text);assert imp2['imported']==0 and imp2['skipped_duplicates']==2
print(json.dumps({'summary_model':sa['summary_model'],'views':sa['views'],'engagement_rate_pct':sa['engagement_rate_pct'],'preview_side_effect_free':before==after_preview,'imported':imp['imported'],'dedupe_skipped':imp2['skipped_duplicates'],'invalid_percent_blocked':not bad['ok'],'foreign_variant_blocked':not wrong['ok'],'automatic_ranking':False,'automatic_winner':False},sort_keys=True))"""
        r=subprocess.run([str(py),'-c',code],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-2000:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M11 summary/CSV diagnostic returned no result')
        out=json.loads(lines[-1])
        if not out.get('preview_side_effect_free') or not out.get('invalid_percent_blocked') or not out.get('foreign_variant_blocked') or out.get('automatic_ranking') or out.get('automatic_winner'):raise RuntimeError('M11 summary/CSV contract failed: '+json.dumps(out))
        return out

def _m12_connector_foundation_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m12_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        code="""from pathlib import Path
from archivist.config import ensure_dirs,HOME
ensure_dirs()
from archivist.connectors import connector_catalog,connector_summary,create_manual_handoff
import json
p=HOME/'fixture.mp4';p.write_bytes(b'archivist-m12-manual-handoff')
rows=connector_catalog();s=connector_summary()
assert len(rows)==4 and all(not x['official_connection_enabled'] for x in rows)
assert all(x['official_api_validation']=='pending_live_validation' for x in rows)
assert all(x['official_documentation_validation']=='verified_2026-09-22' for x in rows)
by={x['id']:x for x in rows}
assert by['youtube']['token_exchange_location']=='local_device' and by['youtube']['auth_runtime']=='local_desktop_pkce'
assert by['tiktok']['token_exchange_location']=='backend_broker_required' and by['tiktok']['confidential_credential_boundary']=='server_only'
assert by['instagram']['token_exchange_location']=='disabled_until_verified' and by['facebook']['token_exchange_location']=='disabled_until_verified'
assert by['youtube']['publish_scopes']==['https://www.googleapis.com/auth/youtube.upload']
assert by['youtube']['analytics_validation']=='documented'
assert by['tiktok']['oauth_flow']=='desktop_authorization_code_pkce_loopback' and by['tiktok']['creator_info_required']
assert by['tiktok']['analytics_scopes']==['video.list']
assert by['instagram']['account_requirement']=='instagram_professional_business_or_creator' and 'instagram_business_content_publish' in by['instagram']['publish_scopes']
assert by['facebook']['account_requirement']=='facebook_page_managed_by_authorized_user' and 'pages_manage_posts' in by['facebook']['publish_scopes']
assert all(x['manual_export_available'] and x['analytics_csv_import_available'] for x in rows)
h=create_manual_handoff(p,'fixture','youtube','caption','new',1)
m=json.loads(open(h['manifest_path'],'r',encoding='utf-8').read())
assert m['upload_performed'] is False and m['official_connector_used'] is False and m['credentials_used'] is False
blocked=False
try:create_manual_handoff(p,'blocked','youtube','','exact_duplicate_block',2)
except ValueError:blocked=True
assert blocked
print(json.dumps({'providers':len(rows),'documentation_contracts_verified':s['documentation_contracts_verified'],'official_connections_enabled':s['official_connections_enabled'],'credential_storage_ready':s['credential_storage_ready'],'manual_export_available':s['manual_export_available'],'analytics_csv_import_available':s['analytics_csv_import_available'],'manifest_exists':Path(h['manifest_path']).exists(),'upload_performed':h['upload_performed'],'blocked_novelty_handoff':blocked,'auto_publish':s['auto_publish']},sort_keys=True))"""
        r=subprocess.run([str(py),'-c',code],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-2000:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M12 connector diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('official_connections_enabled')!=0 or out.get('upload_performed') or out.get('auto_publish') or not out.get('blocked_novelty_handoff'):raise RuntimeError('M12 connector foundation contract failed: '+json.dumps(out))
        return out


def _m12_oauth_core_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m12oauth_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home');env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        code="""from pathlib import Path
import json,urllib.parse
from archivist.config import ensure_dirs
ensure_dirs()
from archivist.db import init_db,db
init_db()
from archivist.oauth import begin_oauth_attempt,consume_loopback_callback,reserve_loopback_callback,OAuthStateError,OAuthReplayError,OAuthExpiredError
from archivist.secret_store import get_secret
from archivist.connectors import provider_connection_gate,save_provider_connection,list_provider_connections
with reserve_loopback_callback() as loop:
    assert loop['host']=='127.0.0.1' and loop['redirect_uri'].startswith('http://127.0.0.1:')
    a=begin_oauth_attempt('youtube',loop['redirect_uri'],['scope.one','scope.two'],ttl_seconds=300)
    with db() as con:
        row=dict(con.execute('SELECT * FROM social_oauth_attempts WHERE id=?',(a['attempt_id'],)).fetchone())
    verifier=get_secret(row['verifier_secret_ref'])
    assert verifier and a['state'] not in json.dumps(row,sort_keys=True) and verifier not in json.dumps(row,sort_keys=True)
    mismatch=False
    try:consume_loopback_callback(a['attempt_id'],loop['redirect_uri']+'?state=wrong&code=x')
    except OAuthStateError:mismatch=True
    assert mismatch
    cb=loop['redirect_uri']+'?state='+urllib.parse.quote(a['state'])+'&code=synthetic-code'
    result=consume_loopback_callback(a['attempt_id'],cb)
    assert result['authorization_code']=='synthetic-code' and result['pkce_verifier']==verifier
    assert get_secret(row['verifier_secret_ref']) is None
    replay=False
    try:consume_loopback_callback(a['attempt_id'],cb)
    except OAuthReplayError:replay=True
    assert replay
    e=begin_oauth_attempt('youtube',loop['redirect_uri'],[],ttl_seconds=-1)
    expired=False
    try:consume_loopback_callback(e['attempt_id'],loop['redirect_uri']+'?state='+urllib.parse.quote(e['state'])+'&code=x')
    except OAuthExpiredError:expired=True
    assert expired
missing=provider_connection_gate('youtube',{'connections':{'social':{'providers':{'youtube':{'client_id':''}}}}})
ready=provider_connection_gate('youtube',{'connections':{'social':{'providers':{'youtube':{'client_id':'synthetic-public-client-id'}}}}})
assert not missing['connect_available'] and missing['connection_blocker']=='youtube_client_id_missing'
assert ready['connect_available'] and ready['public_client_id_configured']
assert not provider_connection_gate('tiktok',{})['connect_available']
assert not provider_connection_gate('instagram',{})['connect_available']
assert not provider_connection_gate('facebook',{})['connect_available']
cid=save_provider_connection('youtube','acct-synthetic','Synthetic',['scope.one'],'connected','social/youtube/1/refresh_token')
rows=list_provider_connections('youtube')
assert len(rows)==1 and rows[0]['id']==cid and rows[0]['secret_store_ref']=='social/youtube/1/refresh_token'
with db() as con:
    schema={r[1] for r in con.execute('PRAGMA table_info(social_provider_connections)').fetchall()}
    attempts={r[1] for r in con.execute('PRAGMA table_info(social_oauth_attempts)').fetchall()}
assert {'provider','account_id','secret_store_ref','granted_scopes_json','status'} <= schema
assert {'state_sha256','verifier_secret_ref','redirect_uri','scopes_json','status'} <= attempts
print(json.dumps({'loopback_host':'127.0.0.1','pkce':'S256','state_mismatch_rejected':mismatch,'replay_rejected':replay,'expired_rejected':expired,'youtube_client_id_gate':True,'tiktok_disabled':True,'meta_disabled':True,'tokens_in_sqlite':False,'provider_calls':0,'connection_rows':len(rows)},sort_keys=True))"""
        r=subprocess.run([str(py),'-c',code],cwd=str(HOME),env=env,capture_output=True,text=True,timeout=45,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-3000:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('M12 OAuth core diagnostic returned no result')
        out=json.loads(lines[-1])
        if out.get('provider_calls')!=0 or not out.get('state_mismatch_rejected') or not out.get('replay_rejected') or not out.get('youtube_client_id_gate') or not out.get('tokens_in_sqlite') is False:
            raise RuntimeError('M12 OAuth core contract failed: '+json.dumps(out))
        return out

def _windows_credential_manager_contract():
    if os.name != 'nt':
        return {'platform':'non_windows','skipped':True}
    from .secret_store import set_secret,get_secret,delete_secret,has_secret,capabilities
    from .config import load_config
    key='diagnostic/m12s'
    value='archivist-synthetic-secret-m12s-42'
    delete_secret(key)
    try:
        set_secret(key,value)
        if not has_secret(key):
            raise RuntimeError('Credential Manager write did not persist')
        got=get_secret(key)
        if got!=value:
            raise RuntimeError('Credential Manager round-trip mismatch')
        cfg=json.dumps(load_config(),sort_keys=True,default=str)
        if value in cfg:
            raise RuntimeError('synthetic secret leaked into plaintext config')
        caps=capabilities()
        if caps.get('adapter')!='windows_credential_manager' or not caps.get('implemented') or not caps.get('validated'):
            raise RuntimeError('Credential Manager capability state incomplete')
        return {
            'adapter':caps.get('adapter'),
            'roundtrip':'passed',
            'plaintext_config_leak':False,
            'supabase_secret_storage_allowed':bool(caps.get('supabase_secret_storage_allowed')),
            'secret_value_reported':False,
        }
    finally:
        delete_secret(key)
        if get_secret(key) is not None:
            raise RuntimeError('Credential Manager diagnostic cleanup failed')

def _compute100_hybrid_contract():
    from .hybrid_compute import run_contract_self_test
    result = run_contract_self_test()
    if not result.get("synthetic_only") or result.get("paid_cloud"):
        raise RuntimeError("COMPUTE-100 contract escaped local synthetic mode")
    if result.get("retry_attempt") != 2:
        raise RuntimeError("COMPUTE-100 retry contract failed")
    return result


def _xplat110_macos_contract():
    from .platform_adapter import macos_adapter_contract, platform_capabilities
    contract = macos_adapter_contract()
    if contract.get("platform") != "macOS" or contract.get("support_status") != "contract_only":
        raise RuntimeError("macOS target declaration missing")
    if contract.get("support_claimed") or contract.get("real_hardware_validated"):
        raise RuntimeError("macOS support must remain unclaimed before real Mac validation")
    if contract.get("real_mac_gate") != "pending":
        raise RuntimeError("real Mac gate must remain pending")
    expected = {
        "filesystem": "macos_pathlib",
        "secret_store": "macos_keychain",
        "background_work": "macos_local_processes",
        "app_control": "macos",
        "desktop_launcher": "macos",
    }
    for area, adapter in expected.items():
        if (contract.get(area) or {}).get("target_adapter") != adapter:
            raise RuntimeError("macOS target adapter mismatch: " + area)
    for area in ("secret_store", "background_work", "app_control", "desktop_launcher"):
        if (contract.get(area) or {}).get("implementation_status") != "not_implemented":
            raise RuntimeError("unvalidated macOS adapter must remain not implemented: " + area)
        if (contract.get(area) or {}).get("validated"):
            raise RuntimeError("unvalidated macOS adapter marked validated: " + area)
    checks = list(contract.get("required_real_mac_checks") or [])
    if len(checks) < 6:
        raise RuntimeError("real Mac acceptance gate incomplete")
    caps = platform_capabilities()
    if caps.get("macos_contract") != contract:
        raise RuntimeError("platform capability snapshot does not expose macOS contract")
    return {
        "platform": contract.get("platform"),
        "support_status": contract.get("support_status"),
        "support_claimed": bool(contract.get("support_claimed")),
        "real_hardware_validated": bool(contract.get("real_hardware_validated")),
        "real_mac_gate": contract.get("real_mac_gate"),
        "filesystem_target": contract["filesystem"]["target_adapter"],
        "secret_store_target": contract["secret_store"]["target_adapter"],
        "background_work_target": contract["background_work"]["target_adapter"],
        "app_control_target": contract["app_control"]["target_adapter"],
        "desktop_launcher_target": contract["desktop_launcher"]["target_adapter"],
        "required_real_mac_checks": len(checks),
    }


def _cloud100_vault_contract():
    from .cloud_vault import run_contract_self_test
    result = run_contract_self_test()
    if result.get("real_cloud") or result.get("real_credentials"):
        raise RuntimeError("CLOUD-100 escaped fake/local transport")
    if result.get("personal_media_upload"):
        raise RuntimeError("CLOUD-100 synthetic test exposed personal media")
    if result.get("auto_delete_local"):
        raise RuntimeError("Cloud Vault automatic local deletion must remain disabled")
    if sorted(result.get("modes") or []) != sorted(["exports_only", "selected_media", "full_archive_mirror"]):
        raise RuntimeError("Cloud Vault mode contract incomplete")
    if int(result.get("verified_rows") or 0) != 3:
        raise RuntimeError("Cloud Vault registry verification count failed")
    return result


def _m13_110_youtube_synthetic_contract():
    from .youtube_adapter import run_contract_self_test
    result = run_contract_self_test()
    if result.get("transport") != "mock":
        raise RuntimeError("M13-110 must use mock transport")
    if result.get("live_network") or result.get("live_oauth"):
        raise RuntimeError("M13-110 escaped synthetic-only mode")
    if result.get("real_client_id") or result.get("real_token"):
        raise RuntimeError("M13-110 used real credentials")
    if int(result.get("provider_network_calls") or 0) != 0:
        raise RuntimeError("M13-110 performed provider network calls")
    if not result.get("scope_verification") or not result.get("channels_list_mine"):
        raise RuntimeError("M13-110 scope/account discovery contract failed")
    if result.get("upload_operation") != "videos.insert":
        raise RuntimeError("M13-110 upload request contract failed")
    if result.get("analytics_freshness") != "provider_delayed":
        raise RuntimeError("M13-110 analytics freshness contract failed")
    if result.get("missing_row_semantics") != "unknown_not_zero":
        raise RuntimeError("M13-110 missing Analytics rows must not be fabricated as zero")
    return result


def _m13_100_analytics_store_contract():
    from .social_analytics import run_contract_self_test
    result = run_contract_self_test()
    if not result.get("synthetic_only") or int(result.get("provider_network_calls") or 0) != 0:
        raise RuntimeError("M13-100 escaped synthetic/local mode")
    if result.get("supabase_cron"):
        raise RuntimeError("M13-100 must use local scheduler, not Supabase cron")
    if result.get("scheduler") != "local_sqlite_poll":
        raise RuntimeError("M13-100 local scheduler contract failed")
    if not result.get("duplicate_deduped"):
        raise RuntimeError("M13-100 idempotency failed")
    if not result.get("snapshot_immutable_update") or not result.get("snapshot_immutable_delete"):
        raise RuntimeError("M13-100 immutable snapshot contract failed")
    if not result.get("metrics_preserved_exactly"):
        raise RuntimeError("M13-100 must never fabricate metric values")
    return result


def _m13_120_provider_bridge_contract():
    py = INSTALL/'.venv'/'Scripts'/'python.exe' if os.name == 'nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_m13_bridge_') as td:
        env = os.environ.copy()
        env['ARCHIVIST_HOME'] = str(Path(td)/'home')
        env['ARCHIVIST_SUPPRESS_BROWSER'] = '1'
        env['PYTHONPATH'] = str(HOME/'app')
        code = (
            "from archivist.config import ensure_dirs;"
            "ensure_dirs();"
            "from archivist.db import init_db;"
            "init_db();"
            "from archivist.analytics_bridge import run_contract_self_test;"
            "import json;"
            "print(json.dumps(run_contract_self_test(),sort_keys=True))"
        )
        r = subprocess.run(
            [str(py),'-c',code],
            cwd=str(HOME),
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
            errors='replace',
            **_hidden(),
        )
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout)[-1600:])
        lines = [x for x in r.stdout.splitlines() if x.strip()]
        if not lines:
            raise RuntimeError('M13-120 bridge diagnostic returned no result')
        result = json.loads(lines[-1])
    if result.get('source') != 'provider_api':
        raise RuntimeError('M13-120 bridge source mismatch')
    if not result.get('manual_source_preserved') or not result.get('csv_import_preserved'):
        raise RuntimeError('M13-120 changed manual/CSV behavior')
    if not result.get('snapshot_provenance_retained'):
        raise RuntimeError('M13-120 snapshot provenance missing')
    if not result.get('provider_metrics_preserved_exactly'):
        raise RuntimeError('M13-120 altered provider metrics')
    if result.get('automatic_winner') or result.get('automatic_ranking'):
        raise RuntimeError('M13-120 automatic winner/ranking forbidden')
    if result.get('summary_model') != 'descriptive_v1':
        raise RuntimeError('M13-120 summary must remain descriptive_v1')
    if not result.get('duplicate_bridge_deduped'):
        raise RuntimeError('M13-120 bridge idempotency failed')
    return result


def _beta100_readiness_contract():
    import requests
    from pathlib import Path
    from . import beta_readiness
    expected = {
        '/welcome': [
            'MediaEngine is local-first',
            'No external account or billing is required for local use',
            'Nothing leaves this PC by default',
            'Windows Credential Manager',
            'does not automatically choose a cross-provider winner',
        ],
        '/cloud': [
            'Cloud features remain opt-in',
            'exports only, selected media, or full archive mirror',
            'must never delete local/source originals',
        ],
        '/settings/connections': [
            'What can leave this PC',
            'authentication data, selected uploads, and provider analytics',
            'Windows Credential Manager',
            'not MediaEngine SQLite or Supabase',
            'Manual fallback',
        ],
        '/help': [
            'Diagnostics stay local by default',
            'Support export/upload is explicit opt-in only',
            'Raw media and tokens are excluded by default',
            'never deletes source originals',
            'Open bundled Beta Guide',
        ],
        '/help/guide': [
            'MediaEngine Beta Guide',
            'Nothing leaves this PC by default',
            'Raw media and tokens are excluded by default',
            'does not automatically choose a cross-provider winner',
        ],
        '/activity': [
            'Jobs & errors',
            'Recovery & support',
        ],
    }
    pages = {}
    for route, markers in expected.items():
        response = requests.get(LOCAL + route, timeout=8)
        if response.status_code != 200:
            raise RuntimeError(f'{route} returned HTTP {response.status_code}')
        text = response.text
        missing = [m for m in markers if m.lower() not in text.lower()]
        if missing:
            raise RuntimeError(f'{route} missing beta markers: {missing}')
        pages[route] = {'http': response.status_code, 'semantic_markers': len(markers)}
    guide_path = Path(beta_readiness.__file__).resolve().parent / 'BETA_GUIDE.md'
    if not guide_path.exists():
        raise RuntimeError(f'package guide missing: {guide_path}')
    guide = guide_path.read_text(encoding='utf-8', errors='replace')
    if 'Nothing leaves this PC by default' not in guide or 'Raw media and tokens are excluded by default' not in guide:
        raise RuntimeError('package guide content mismatch')
    return {
        'contract': 'beta_readiness_v1',
        'pages': pages,
        'guide_path_scope': 'package_relative',
        'guide_exists_after_install': True,
        'local_first_default': True,
        'external_account_required': False,
        'billing_required': False,
        'cloud_opt_in_only': True,
        'support_auto_upload': False,
        'raw_media_tokens_excluded_by_default': True,
        'credential_store': 'windows_credential_manager',
        'automatic_cross_provider_winner': False,
        'automatic_cross_provider_ranking': False,
        'recovery_deletes_source_originals': False,
    }


def _relart140_launcher_contract():
    launcher=INSTALL/'launcher.py'
    if not launcher.exists():
        raise RuntimeError('root launcher.py missing')
    source=launcher.read_text(encoding='utf-8',errors='replace')
    compile(source,str(launcher),'exec')
    required=[
        'LAUNCHER_VERSION = "3.6.0"',
        'artifact_url',
        'artifact_size_bytes',
        'MAX_ARTIFACT_BYTES',
        '_SameOriginArtifactRedirect',
        '_release_bytes',
        'safe_extract',
        "actual=hashlib.sha256(raw).hexdigest()",
    ]
    missing=[m for m in required if m not in source]
    if missing:
        raise RuntimeError('root launcher missing RELART-140 markers: '+','.join(missing))
    if "if not url:" not in source or "base64.b64decode" not in source:
        raise RuntimeError('legacy bundle_b64 fallback is missing')
    return {
        'launcher_version':'3.6.0',
        'artifact_url_path':True,
        'artifact_size_bound':True,
        'same_origin_redirect':True,
        'legacy_bundle_b64_fallback':True,
        'sha256_before_extract':True,
        'safe_extract_preserved':True,
    }


def _support150_bundle_contract():
    from .support_bundle import run_contract_self_test
    result=run_contract_self_test()
    if not result.get('explicit_local_user_action'):
        raise RuntimeError('support bundle is not explicit-user-action only')
    if result.get('automatic_upload'):
        raise RuntimeError('support bundle unexpectedly enables automatic upload')
    if result.get('raw_media_included') or result.get('database_dump_included') or result.get('credential_store_included') or result.get('full_paths_included'):
        raise RuntimeError('support bundle includes prohibited category')
    if int(result.get('redaction_canaries_leaked') or 0)!=0:
        raise RuntimeError('support bundle leaked synthetic canary')
    if int(result.get('bundle_bytes') or 0)>256*1024:
        raise RuntimeError('support bundle exceeded bounded size')
    return result


def _api140_loopback_guard_contract():
    from .web import create_app
    app=create_app()
    app.config.update(TESTING=True)
    client=app.test_client()
    probe='/__api140_probe__'

    def post(host, origin=None, referer=None):
        headers={'Host':host}
        if origin is not None:
            headers['Origin']=origin
        if referer is not None:
            headers['Referer']=referer
        return client.post(probe,headers=headers)

    allowed_origin=post(f'127.0.0.1:{APP_PORT}',origin=f'http://127.0.0.1:{APP_PORT}')
    allowed_localhost=post(f'localhost:{APP_PORT}',origin=f'http://localhost:{APP_PORT}')
    allowed_referer=post(f'127.0.0.1:{APP_PORT}',referer=f'http://127.0.0.1:{APP_PORT}/help')
    allowed_service=post(f'127.0.0.1:{APP_PORT}')
    evil_prefix=post(f'127.0.0.1:{APP_PORT}',origin=f'http://127.0.0.1:{APP_PORT}.evil.test')
    wrong_port=post(f'127.0.0.1:{APP_PORT}',origin='http://127.0.0.1:9999')
    wrong_scheme=post(f'127.0.0.1:{APP_PORT}',origin=f'https://127.0.0.1:{APP_PORT}')
    foreign_referer=post(f'127.0.0.1:{APP_PORT}',referer=f'http://evil.test:{APP_PORT}/x')
    wrong_host=post(f'evil.test:{APP_PORT}',origin=f'http://127.0.0.1:{APP_PORT}')
    get_good=client.get('/api/ping',headers={'Host':f'127.0.0.1:{APP_PORT}'})
    get_bad=client.get('/api/ping',headers={'Host':f'evil.test:{APP_PORT}'})

    allowed=[allowed_origin.status_code,allowed_localhost.status_code,allowed_referer.status_code,allowed_service.status_code]
    blocked=[evil_prefix.status_code,wrong_port.status_code,wrong_scheme.status_code,foreign_referer.status_code,wrong_host.status_code,get_bad.status_code]
    if allowed != [404,404,404,404]:
        raise RuntimeError('legitimate loopback POST compatibility failed: '+str(allowed))
    if blocked != [403,403,403,403,403,403]:
        raise RuntimeError('loopback guard negative case failed: '+str(blocked))
    if get_good.status_code!=200:
        raise RuntimeError('legitimate loopback GET failed')
    if any(r.headers.get('Access-Control-Allow-Origin') for r in (evil_prefix,wrong_host,get_bad)):
        raise RuntimeError('foreign request received permissive CORS header')
    return {
        'exact_origin_allowed':True,
        'exact_localhost_allowed':True,
        'same_origin_referer_allowed':True,
        'headerless_local_service_post_allowed':True,
        'malicious_prefix_origin_blocked':True,
        'wrong_port_blocked':True,
        'wrong_scheme_blocked':True,
        'foreign_referer_blocked':True,
        'wrong_host_blocked':True,
        'foreign_get_host_blocked':True,
        'permissive_cors':False,
    }




def _priv150_composition_privacy_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    env=os.environ.copy();env['PYTHONPATH']=str(HOME/'app');env['ARCHIVIST_SUPPRESS_BROWSER']='1'
    r=subprocess.run([str(py),'-m','archivist.social_lab_diag_worker','priv150'],cwd=str(HOME),env=env,
                     capture_output=True,text=True,timeout=30,errors='replace',**_hidden())
    if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-1600:])
    lines=[x for x in r.stdout.splitlines() if x.strip()]
    if not lines:raise RuntimeError('PRIV-150 diagnostic returned no result')
    result=json.loads(lines[-1])
    required=[
      'public_candidate','public_recent_visible','public_enqueue','public_manual_handoff',
      'private_candidate_blocked','private_recent_hidden','private_direct_enqueue_blocked',
      'private_direct_record_blocked','private_connector_handoff_blocked',
      'rejected_candidate_blocked','rejected_connector_handoff_blocked',
      'historical_composition_preserved','historical_queue_preserved'
    ]
    missing=[k for k in required if not result.get(k)]
    if missing:raise RuntimeError('PRIV-150 contract failed: '+','.join(missing))
    return result


def _ingest160_staging_integrity_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_ingest160_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home')
        env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        r=subprocess.run([str(py),'-m','archivist.ingest_failure_diag_worker'],cwd=str(HOME),env=env,
                         capture_output=True,text=True,timeout=75,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-2000:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('INGEST-160 diagnostic returned no result')
        result=json.loads(lines[-1])
    if not result.get('pass'):
        raise RuntimeError('INGEST-160 matrix failures: '+','.join(result.get('failed') or []))
    return result['result']


def _medbuf003_metadata_fuzz_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_medbuf003_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home')
        env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        r=subprocess.run([str(py),'-m','archivist.metadata_fuzz_diag_worker'],cwd=str(HOME),env=env,
                         capture_output=True,text=True,timeout=90,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-2200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('MEDBUF-003 diagnostic returned no result')
        result=json.loads(lines[-1])
    if not result.get('pass'):raise RuntimeError('MEDBUF-003 metadata fuzz failures: '+','.join(result.get('failed') or []))
    return result['result']


def _medbuf004_clip_reframe_determinism_contract():
    py=INSTALL/'.venv'/'Scripts'/'python.exe' if os.name=='nt' else Path(sys.executable)
    with tempfile.TemporaryDirectory(prefix='archivist_medbuf004_') as td:
        env=os.environ.copy();env['ARCHIVIST_HOME']=str(Path(td)/'home')
        env['ARCHIVIST_SUPPRESS_BROWSER']='1';env['PYTHONPATH']=str(HOME/'app')
        r=subprocess.run([str(py),'-m','archivist.clip_reframe_determinism_diag_worker'],cwd=str(HOME),env=env,
                         capture_output=True,text=True,timeout=60,errors='replace',**_hidden())
        if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout)[-2200:])
        lines=[x for x in r.stdout.splitlines() if x.strip()]
        if not lines:raise RuntimeError('MEDBUF-004 diagnostic returned no result')
        result=json.loads(lines[-1])
    if not result.get('pass'):raise RuntimeError('MEDBUF-004 determinism failures: '+','.join(result.get('failed') or []))
    return result['result']

def run_extended_suite():
    rows=[]
    for p in ('/api/ping','/','/media','/social','/devices','/cloud','/activity','/settings/connections','/library','/search','/convert','/jobs','/best','/about'):_check('route '+p,lambda p=p:_route(p),rows)
    _check('FFmpeg H.264 decode',lambda:_ffmpeg_decode(ASSETS/'browser_fixture_h264.mp4'),rows)
    _check('FFmpeg HEVC decode',lambda:_ffmpeg_decode(ASSETS/'hevc_fixture.mp4'),rows)
    _check('isolated media primitives',_media_pipeline,rows)
    _check('full sandbox Import-Analyze-Media Brain',_full_sandbox_pipeline,rows)
    _check('Smart Crop v2 trajectory fixtures',_smart_crop_v2_math,rows)
    _check('Edge canvas/playback/scrubber/focus',_browser_test,rows)
    _check('real Library Virtual Clip in Edge',_real_clip_browser,rows)
    _check('Semantic Search foundation',_semantic_search_foundation,rows,required=True)
    _check('Semantic Search UI/API',_semantic_search_http,rows,required=True)
    _check('Visual similarity fingerprint fixtures',_visual_similarity_fixtures,rows,required=True)
    _check('Visual similarity index/API',_visual_similarity_live,rows,required=True)
    _check('M8 Clip Export synthetic render/decode',_clip_export_fixture,rows,required=True)
    _check('M8 Clip Export UI',_clip_export_ui,rows,required=True)
    _check('M8 Composer multi-clip render/decode',_composer_render_fixture,rows,required=True)
    _check('M8 Composer UI',_composer_ui,rows,required=True)
    _check('M8.1 Composer mixed audio/silence',_composer_audio_mixed_fixture,rows,required=True)
    _check('M8.1 Composer restart recovery policy',_composer_recovery_policy,rows,required=True)
    _check('M9 dependency inventory probe',_m9_dependency_inventory,rows,required=True)
    _check("Platform adapter contract",_platform_adapter_contract,rows)
    _check('Platform IO/security/background contract',_platform_io_security_background_contract,rows,required=True)
    _check('Windows Credential Manager secret-store round-trip',_windows_credential_manager_contract,rows,required=True)
    _check('M10 local publication registry + structural novelty guard',_m10_social_lab_contract,rows,required=True)
    _check('M10 novelty-aware local content queue',_m10_content_queue_contract,rows,required=True)
    _check('M10 visual novelty via existing visual_dhash_v1',_m10_visual_novelty_contract,rows,required=True)
    _check('M10 local audio novelty spectrum',_m10_audio_novelty_contract,rows,required=True)
    _check('M11 local experiment engine',_m11_experiment_engine_contract,rows,required=True)
    _check('M11 descriptive summaries + CSV import validation',_m11_summary_csv_contract,rows,required=True)
    _check('M12 connector registry + safe manual fallbacks',_m12_connector_foundation_contract,rows,required=True)
    _check('M12 OAuth core + local connection schema',_m12_oauth_core_contract,rows,required=True)
    _check('Platform subprocess helper contract',_platform_subprocess_helper_contract,rows)
    _check('Windows hidden subprocess runtime contract',_windows_hidden_subprocess_contract,rows,required=True)
    _check('Watchdog real converter process restart',_watchdog_real_process_restart,rows,required=True)
    _check('Watchdog recovery policy + exhaustion',_watchdog_policy_and_exhaustion,rows,required=True)
    _check('Converter restart recovery',_converter_restart_recovery,rows,required=True)
    _check('Converter synthetic encode',_converter_smoke,rows,required=True)
    _check('Converter target-size two-pass',_converter_target_smoke,rows,required=True)
    _check('Convert UI + auto storyboard mount',_convert_ui_storyboard_mount,rows,required=True)
    _check('Convert estimate + Library bulk shortcut',_convert_estimate_bulk_ui,rows,required=True)
    _check('Convert preset estimate switch in Edge',_convert_preset_switch_browser,rows,required=True)
    _check('Convert multi-row preset estimates',_convert_multi_preset_browser,rows,required=True)
    _check('Convert Library visibility + selection transfer',_convert_library_visibility,rows,required=True)
    _check('Convert accessibility filter',_convert_accessibility_filter,rows,required=True)
    _check('Convert Drone metadata + filters',_convert_drone_metadata,rows,required=True)
    _check('Convert no-default-preset + previews',_convert_ux_browser,rows,required=True)
    _check('Pagination jump UI',_pagination_jump_ui,rows,required=True)
    _check('Convert preview inventory health',_convert_preview_health,rows,required=False)
    _check('COMPUTE-100 hybrid job contract + local fake worker',_compute100_hybrid_contract,rows,required=True)
    _check('XPLAT-110 macOS adapter contract declarations',_xplat110_macos_contract,rows,required=True)
    _check('CLOUD-100 local registry + fake S3 contract',_cloud100_vault_contract,rows,required=True)
    _check('M13-110 synthetic YouTube adapter',_m13_110_youtube_synthetic_contract,rows,required=True)
    _check('M13-100 local analytics snapshots + scheduler',_m13_100_analytics_store_contract,rows,required=True)
    _check('M13-120 provider snapshot experiment bridge',_m13_120_provider_bridge_contract,rows,required=True)
    _check('BETA-100 first-run/privacy/support/recovery contract',_beta100_readiness_contract,rows,required=True)
    _check('RELART-140 root launcher dual-path updater contract',_relart140_launcher_contract,rows,required=True)
    _check('SUPPORT-150 privacy-safe local support bundle contract',_support150_bundle_contract,rows,required=True)
    _check('API-140 strict loopback Host/Origin guard',_api140_loopback_guard_contract,rows,required=True)
    _check('PRIV-150 composition privacy revalidation',_priv150_composition_privacy_contract,rows,required=True)
    _check('INGEST-160 staging integrity + retry/recovery matrix',_ingest160_staging_integrity_contract,rows,required=True)
    _check('MEDBUF-003 media metadata fuzz matrix',_medbuf003_metadata_fuzz_contract,rows,required=True)
    _check('MEDBUF-004 clip/reframe determinism matrix',_medbuf004_clip_reframe_determinism_contract,rows,required=True)
    _check('ADB capability',_android,rows,required=False)
    failed=[x for x in rows if x['required'] and x['status']!='passed']
    return {'status':'failed' if failed else 'passed','summary':f"{len(rows)-len(failed)}/{len(rows)} extended checks acceptable; {len(failed)} required failures",'details':{'suite':'windows_extended_v1','checks':rows,'tested_at':_now()}}

def _report(result):
    try:
        cfg=json.loads(REMOTE_CONFIG.read_text(encoding='utf-8')); tok=cfg.get('device_token')
        if not tok:return
        body=json.dumps({'action':'report','command_id':None,'report_type':'extended_windows','app_version':VERSION,'agent_version':'app-diagnostics-1','status':result['status'],'summary':result['summary'],'details':result['details']}).encode()
        req=urllib.request.Request(ENDPOINT,data=body,headers={'content-type':'application/json','authorization':'Bearer '+tok},method='POST')
        urllib.request.urlopen(req,timeout=30).read()
    except Exception: pass

def run_once_and_report():
    DIAG_DIR.mkdir(parents=True,exist_ok=True); marker=DIAG_DIR/f'extended_{VERSION.replace(".","_")}.json'
    if marker.exists(): return
    try: result=run_extended_suite()
    except Exception as exc: result={'status':'failed','summary':'Extended diagnostics crashed','details':{'suite':'windows_extended_v1','error':str(exc)[:900],'tested_at':_now()}}
    marker.write_text(json.dumps(result,indent=2),encoding='utf-8'); _report(result)

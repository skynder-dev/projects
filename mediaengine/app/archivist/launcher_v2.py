from __future__ import annotations

import base64, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request, webbrowser, zipfile
from datetime import datetime, timezone
from pathlib import Path

LAUNCHER_VERSION = "3.7.0"
HOME = Path(__file__).resolve().parent
DATA = HOME / "data"
VERSION_PATH = HOME / "version.txt"
CONFIG_PATH = HOME / "updater_config.json"
STATUS_PATH = DATA / "update_status.json"
def _port():
    try:
        p=int((HOME/"port.txt").read_text(encoding="utf-8").strip())
        return p if 1024<=p<=65535 else 8765
    except Exception:
        return 8765

HOST, PORT = "127.0.0.1", _port()


def version_tuple(v):
    out=[]
    for part in str(v).split('.'):
        n=''.join(c for c in part if c.isdigit()); out.append(int(n or 0))
    return tuple((out+[0,0,0])[:3])

def current_version():
    try: return VERSION_PATH.read_text(encoding='utf-8').strip() or '0.0.0'
    except Exception: return '0.0.0'

def write_status(**fields):
    try:
        DATA.mkdir(parents=True,exist_ok=True)
        p={"at":datetime.now(timezone.utc).isoformat(),**fields}; t=STATUS_PATH.with_suffix('.tmp'); t.write_text(json.dumps(p,indent=2),encoding='utf-8'); t.replace(STATUS_PATH)
    except Exception: pass

def server_alive(timeout=.35):
    try:
        with urllib.request.urlopen(f'http://{HOST}:{PORT}/api/ping',timeout=timeout) as r: return r.status==200
    except Exception: return False

def edge_candidates():
    candidates = []
    local = os.environ.get('LOCALAPPDATA')
    pf86 = os.environ.get('PROGRAMFILES(X86)')
    pf = os.environ.get('PROGRAMFILES')
    if local: candidates.append(Path(local)/'Microsoft'/'Edge'/'Application'/'msedge.exe')
    if pf86: candidates.append(Path(pf86)/'Microsoft'/'Edge'/'Application'/'msedge.exe')
    if pf: candidates.append(Path(pf)/'Microsoft'/'Edge'/'Application'/'msedge.exe')
    found = shutil.which('msedge.exe') or shutil.which('msedge')
    if found: candidates.append(Path(found))
    seen=set()
    for p in candidates:
        try: key=str(p.resolve()).lower()
        except Exception: key=str(p).lower()
        if key in seen: continue
        seen.add(key)
        if p.exists(): yield p

def open_user_interface(force_browser=False):
    url=f'http://{HOST}:{PORT}/'
    if not force_browser and os.name=='nt':
        for edge in edge_candidates():
            try:
                subprocess.Popen([str(edge), f'--app={url}', '--start-maximized'], cwd=str(HOME), close_fds=True, **hidden_kwargs())
                write_status(status='shell_opened', version=current_version(), shell='edge_app')
                return 'edge_app'
            except Exception:
                pass
    webbrowser.open(url)
    write_status(status='shell_opened', version=current_version(), shell='browser')
    return 'browser'

def hidden_kwargs():
    kw={}
    if os.name=='nt':
        kw['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)
        si=subprocess.STARTUPINFO(); si.dwFlags|=getattr(subprocess,'STARTF_USESHOWWINDOW',1); si.wShowWindow=getattr(subprocess,'SW_HIDE',0); kw['startupinfo']=si
    else: kw['start_new_session']=True
    return kw

def fetch_latest(cfg):
    base=cfg['supabase_url'].rstrip('/')+'/rest/v1/archivist_releases'
    params={'select':'version,bundle_b64,bundle_sha256,artifact_url,artifact_size_bytes,notes,min_launcher_version,created_at','channel':'eq.'+cfg.get('channel','stable'),'active':'eq.true','order':'created_at.desc','limit':'10'}
    req=urllib.request.Request(base+'?'+urllib.parse.urlencode(params),headers={'apikey':cfg['publishable_key'],'Accept':'application/json','User-Agent':f'ArchivistUpdater/{LAUNCHER_VERSION}'})
    with urllib.request.urlopen(req,timeout=10) as resp: rows=json.loads(resp.read().decode('utf-8'))
    rows.sort(key=lambda r:version_tuple(r.get('version','0')),reverse=True)
    return rows[0] if rows else None

def fetch_version(cfg, version):
    base=cfg['supabase_url'].rstrip('/')+'/rest/v1/archivist_releases'
    params={'select':'version,bundle_b64,bundle_sha256,artifact_url,artifact_size_bytes,notes,min_launcher_version,created_at','version':'eq.'+str(version),'limit':'1'}
    req=urllib.request.Request(base+'?'+urllib.parse.urlencode(params),headers={'apikey':cfg['publishable_key'],'Accept':'application/json','User-Agent':f'ArchivistUpdater/{LAUNCHER_VERSION}'})
    with urllib.request.urlopen(req,timeout=15) as resp: rows=json.loads(resp.read().decode('utf-8'))
    return rows[0] if rows else None

def safe_extract(zf,dest):
    root=dest.resolve()
    for info in zf.infolist():
        target=(dest/info.filename).resolve()
        if root!=target and root not in target.parents: raise RuntimeError('Unsafe path in update bundle')
    zf.extractall(dest)

def install_requirements(old_req,new_req):
    if not new_req.exists() or (old_req is not None and old_req==new_req.read_bytes()): return
    py=HOME/'.venv'/'Scripts'/'python.exe'
    if not py.exists(): raise RuntimeError('Python environment is missing')
    
    kw={}
    if os.name=='nt':
        kw['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)
        si=subprocess.STARTUPINFO(); si.dwFlags|=getattr(subprocess,'STARTF_USESHOWWINDOW',1); si.wShowWindow=getattr(subprocess,'SW_HIDE',0); kw['startupinfo']=si
    subprocess.run([str(py),'-m','pip','install','--disable-pip-version-check','--quiet','-r',str(new_req)],check=True,**kw)

def prune_backups(keep=6):
    root=DATA/'update_backups'
    try:
        dirs=sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p:p.stat().st_mtime, reverse=True)
        for p in dirs[int(keep):]: shutil.rmtree(p,ignore_errors=True)
    except Exception: pass


MAX_ARTIFACT_BYTES = 512 * 1024 * 1024

def _artifact_origin(url):
    p=urllib.parse.urlsplit(str(url or '').strip())
    if p.scheme.lower()!='https' or not p.hostname or p.username or p.password or p.fragment:
        raise RuntimeError('Artifact URL must be an absolute HTTPS URL')
    try:
        port=p.port or 443
    except ValueError:
        raise RuntimeError('Artifact URL port is invalid')
    return (p.scheme.lower(),p.hostname.lower(),int(port))

class _SameOriginArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _artifact_origin(req.full_url)!=_artifact_origin(newurl):
            raise RuntimeError('Artifact redirect changed origin')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _release_bytes(rel):
    url=str(rel.get('artifact_url') or '').strip()
    if not url:
        raw=base64.b64decode(rel['bundle_b64'],validate=True)
        if len(raw)>MAX_ARTIFACT_BYTES:
            raise RuntimeError('Legacy update bundle exceeds size ceiling')
        return raw
    try:
        declared=int(rel.get('artifact_size_bytes') or 0)
    except Exception:
        raise RuntimeError('Artifact size is invalid')
    if declared<=0 or declared>MAX_ARTIFACT_BYTES:
        raise RuntimeError('Artifact size exceeds allowed bounds')
    origin=_artifact_origin(url)
    opener=urllib.request.build_opener(_SameOriginArtifactRedirect())
    req=urllib.request.Request(url,headers={'Accept':'application/octet-stream','User-Agent':f'ArchivistUpdater/{LAUNCHER_VERSION}'})
    with opener.open(req,timeout=30) as resp:
        if _artifact_origin(resp.geturl())!=origin:
            raise RuntimeError('Artifact final URL changed origin')
        raw_len=resp.headers.get('Content-Length')
        if raw_len:
            try: header_len=int(raw_len)
            except Exception: raise RuntimeError('Artifact Content-Length is invalid')
            if header_len!=declared or header_len>MAX_ARTIFACT_BYTES:
                raise RuntimeError('Artifact Content-Length mismatch')
        out=bytearray()
        while True:
            chunk=resp.read(min(65536,declared+1-len(out)))
            if not chunk: break
            out.extend(chunk)
            if len(out)>declared or len(out)>MAX_ARTIFACT_BYTES:
                raise RuntimeError('Artifact stream exceeds declared size')
        if len(out)!=declared:
            raise RuntimeError('Artifact stream size mismatch')
        return bytes(out)


def apply_release(rel,installed):
    if version_tuple(rel.get('min_launcher_version') or '1.0.0')>version_tuple(LAUNCHER_VERSION): raise RuntimeError('Update needs a newer launcher')
    raw=_release_bytes(rel); actual=hashlib.sha256(raw).hexdigest(); expected=str(rel['bundle_sha256']).lower()
    if actual!=expected: raise RuntimeError('Update SHA-256 verification failed')
    DATA.mkdir(parents=True,exist_ok=True); stage=Path(tempfile.mkdtemp(prefix='archivist_update_',dir=str(DATA))); backup=DATA/'update_backups'/f"{installed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"; backup.mkdir(parents=True,exist_ok=True)
    req=HOME/'requirements.txt'; old_req=req.read_bytes() if req.exists() else None
    try:
        zp=stage/'release.zip'; zp.write_bytes(raw); unpack=stage/'unpacked'; unpack.mkdir()
        with zipfile.ZipFile(zp) as z: safe_extract(z,unpack)
        incoming=unpack/'app'; inreq=unpack/'requirements.txt'
        if not (incoming/'main.py').exists(): raise RuntimeError('Update bundle is missing app/main.py')
        cur=HOME/'app'
        if cur.exists(): shutil.copytree(cur,backup/'app')
        if req.exists(): shutil.copy2(req,backup/'requirements.txt')
        new=HOME/'app.__new__'; old=HOME/'app.__old__'; shutil.rmtree(new,ignore_errors=True); shutil.rmtree(old,ignore_errors=True); shutil.copytree(incoming,new)
        if cur.exists(): cur.replace(old)
        new.replace(cur)
        if inreq.exists(): shutil.copy2(inreq,req); install_requirements(old_req,req)
        VERSION_PATH.write_text(str(rel['version']),encoding='utf-8'); shutil.rmtree(old,ignore_errors=True)
        write_status(status='updated',from_version=installed,to_version=rel['version'],notes=rel.get('notes')); prune_backups()
    except Exception:
        try:
            cur=HOME/'app'
            if (backup/'app').exists(): shutil.rmtree(cur,ignore_errors=True); shutil.copytree(backup/'app',cur)
            if (backup/'requirements.txt').exists(): shutil.copy2(backup/'requirements.txt',req)
            VERSION_PATH.write_text(installed,encoding='utf-8')
        except Exception: pass
        raise
    finally: shutil.rmtree(stage,ignore_errors=True)

def check_update(force=False):
    installed=current_version()
    if not force and os.environ.get('ARCHIVIST_SKIP_UPDATE')=='1': return installed
    try:
        cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8')); latest=fetch_latest(cfg)
        if latest and version_tuple(latest['version'])>version_tuple(installed): apply_release(latest,installed); return str(latest['version'])
        write_status(status='up_to_date',version=installed)
    except Exception as exc: write_status(status='update_failed',version=installed,error=str(exc))
    return current_version()

def wait_server_down(seconds=12):
    end=time.time()+seconds
    while time.time()<end:
        if not server_alive(): return
        time.sleep(.25)

def restore_latest_backup(version):
    root=DATA/'update_backups'
    try:
        candidates=sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith(str(version)+'_')], key=lambda p:p.stat().st_mtime, reverse=True)
        if not candidates: return False
        b=candidates[0]; cur=HOME/'app'; req=HOME/'requirements.txt'
        if not (b/'app').exists(): return False
        shutil.rmtree(cur,ignore_errors=True); shutil.copytree(b/'app',cur)
        if (b/'requirements.txt').exists(): shutil.copy2(b/'requirements.txt',req)
        VERSION_PATH.write_text(str(version),encoding='utf-8')
        write_status(status='rolled_back',version=str(version),reason='new version failed startup health check')
        return True
    except Exception as exc:
        write_status(status='rollback_failed',version=str(version),error=str(exc)); return False

def wait_server_up(seconds=30):
    end=time.time()+seconds
    while time.time()<end:
        if server_alive(timeout=.5): return True
        time.sleep(.35)
    return False

def spawn_app(no_browser=False):
    pyw=HOME/'.venv'/'Scripts'/'pythonw.exe'; py=HOME/'.venv'/'Scripts'/'python.exe'; exe=pyw if pyw.exists() else py; main=HOME/'app'/'main.py'
    if not exe.exists() or not main.exists(): raise RuntimeError('Archivist installation is incomplete')
    env=os.environ.copy(); env['ARCHIVIST_HOME']=str(HOME); env['ARCHIVIST_V2_CHILD']='1'
    if no_browser: env['ARCHIVIST_SUPPRESS_BROWSER']='1'
    else: env.pop('ARCHIVIST_SUPPRESS_BROWSER',None)
    subprocess.Popen([str(exe),str(main),'--no-browser' if no_browser else '--open-browser'],cwd=str(HOME),env=env,close_fds=True,**hidden_kwargs())

def main():
    raw_args=list(sys.argv[1:]); args=set(raw_args); no_browser='--no-browser' in args; force_browser='--browser' in args; force='--update' in args; restart='--restart' in args
    install_version=next((x.split('=',1)[1] for x in raw_args if x.startswith('--install-version=')),None)
    # Manual launch while already running should only focus/open the existing web app.
    if server_alive() and not (force or restart or install_version):
        if not no_browser: open_user_interface(force_browser=force_browser)
        return 0
    if force or restart or install_version: wait_server_down()
    before=current_version()
    if install_version:
        try:
            cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8')); rel=fetch_version(cfg,install_version)
            if not rel: raise RuntimeError('Requested candidate release was not found')
            if str(rel.get('version'))!=str(install_version): raise RuntimeError('Candidate version mismatch')
            apply_release(rel,before); after=str(rel['version'])
        except Exception as exc:
            write_status(status='remote_update_failed',version=before,target=install_version,error=str(exc)); return 2
    else: after=before if restart else check_update(force=force)
    spawn_app(no_browser=True)
    if wait_server_up(30):
        write_status(status='running',version=current_version())
        if not no_browser: open_user_interface(force_browser=force_browser)
        return 0
    # A bad release must not strand the user with a dead desktop shortcut.
    if after!=before and restore_latest_backup(before):
        spawn_app(no_browser=True)
        if wait_server_up(30):
            if not no_browser: open_user_interface(force_browser=force_browser)
            return 0
    write_status(status='start_failed',version=current_version())
    return 1

if __name__=='__main__': raise SystemExit(main())

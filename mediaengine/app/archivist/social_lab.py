from __future__ import annotations
import hashlib,json,re
from difflib import SequenceMatcher
from pathlib import Path
from .db import db,now_iso

def _ids(v):
    out=[]
    for x in v or []:
        try:x=int(x)
        except Exception:continue
        if x not in out:out.append(x)
    return out

def _sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def _txt(v):return re.sub(r"\s+"," ",str(v or "").strip().lower())
def _seq(a,b):return SequenceMatcher(a=list(a or []),b=list(b or []),autojunk=False).ratio()
def _cap(a,b):
    a,b=_txt(a),_txt(b)
    if not a and not b:return 1.0
    if not a or not b:return 0.0
    return SequenceMatcher(a=a,b=b,autojunk=False).ratio()
def _jac(a,b):
    a,b=set(a or []),set(b or [])
    if not a and not b:return 1.0
    if not a or not b:return 0.0
    return len(a&b)/len(a|b)
def _json_ids(v):
    try:return _ids(json.loads(v or "[]"))
    except Exception:return []

def ensure_schema():
    with db() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS social_publications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,status TEXT NOT NULL DEFAULT 'exported',
        output_path TEXT,output_sha256 TEXT,composition_id INTEGER,title TEXT,platform TEXT,
        source_clip_ids_json TEXT NOT NULL DEFAULT '[]',clip_sequence_json TEXT NOT NULL DEFAULT '[]',
        template_key TEXT,caption_text TEXT,novelty_state TEXT,created_at TEXT NOT NULL,published_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_social_pub_sha ON social_publications(output_sha256);
        CREATE INDEX IF NOT EXISTS idx_social_pub_comp ON social_publications(composition_id);
        CREATE TABLE IF NOT EXISTS novelty_checks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_sha256 TEXT,result_state TEXT NOT NULL,
        exact_match_publication_id INTEGER,max_source_overlap REAL NOT NULL DEFAULT 0,
        max_sequence_similarity REAL NOT NULL DEFAULT 0,max_caption_similarity REAL NOT NULL DEFAULT 0,
        template_match INTEGER NOT NULL DEFAULT 0,compared_count INTEGER NOT NULL DEFAULT 0,
        detail_json TEXT,created_at TEXT NOT NULL);""");c.commit()

def publication_stats():
    ensure_schema()
    with db() as c:return {"publications":int(c.execute("SELECT COUNT(*) FROM social_publications").fetchone()[0]),"published":int(c.execute("SELECT COUNT(*) FROM social_publications WHERE status='published'").fetchone()[0]),"novelty_checks":int(c.execute("SELECT COUNT(*) FROM novelty_checks").fetchone()[0])}

def list_publications(limit=20):
    ensure_schema();limit=max(1,min(int(limit or 20),100))
    with db() as c:return [dict(r) for r in c.execute("SELECT id,status,composition_id,title,platform,novelty_state,created_at,published_at FROM social_publications ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]


def _composition_source_visibility(con,cid):
    rows=con.execute("""SELECT ci.clip_id,vc.id vc_id,i.id inventory_id,
      COALESCE(i.excluded,1) excluded,i.private_path,i.rejected_path,i.analysis_status
      FROM composition_items ci
      LEFT JOIN virtual_clips vc ON vc.id=ci.clip_id
      LEFT JOIN inventory i ON i.id=vc.inventory_id
      WHERE ci.composition_id=? ORDER BY ci.position""",(int(cid),)).fetchall()
    clip_ids=[];blocked=[]
    if not rows:
        return {"safe":False,"reason":"composition_sources_missing","clip_ids":[],"blocked":[]}
    for r in rows:
        clip_ids.append(int(r["clip_id"]))
        reason=None
        if r["vc_id"] is None or r["inventory_id"] is None:reason="source_missing"
        elif int(r["excluded"] or 0):reason="excluded"
        elif r["private_path"]:reason="private"
        elif r["rejected_path"]:reason="rejected"
        elif str(r["analysis_status"] or "")=="private":reason="private_analysis"
        if reason:blocked.append({"clip_id":int(r["clip_id"]),"reason":reason})
    return {"safe":not blocked,"reason":blocked[0]["reason"] if blocked else None,"clip_ids":clip_ids,"blocked":blocked}

def _require_composition_source_visibility(con,cid):
    state=_composition_source_visibility(con,cid)
    if not state["safe"]:
        raise ValueError("Composition sources are no longer exportable: "+str(state["reason"] or "blocked"))
    return state

def recent_rendered_compositions(limit=12):
    limit=max(1,min(int(limit or 12),50))
    out=[]
    with db() as c:
        try:
            rows=c.execute("SELECT id,title,aspect,status,output_bytes,updated_at FROM compositions WHERE status='finished' AND output_path IS NOT NULL ORDER BY id DESC LIMIT ?",(max(50,limit*8),)).fetchall()
            for row in rows:
                if _composition_source_visibility(c,int(row["id"]))["safe"]:
                    out.append(dict(row))
                    if len(out)>=limit:break
        except Exception:
            out=[]
    return out

def candidate_from_composition(cid):
    cid=int(cid)
    with db() as c:
        x=c.execute("SELECT id,title,aspect,status,output_path FROM compositions WHERE id=?",(cid,)).fetchone()
        if not x or x["status"]!="finished" or not x["output_path"]:raise ValueError("Composition is not a finished local render")
        visibility=_require_composition_source_visibility(c,cid)
    seq=visibility["clip_ids"];p=Path(x["output_path"])
    if not p.exists():raise ValueError("Composition output is unavailable")
    return {"composition_id":cid,"title":str(x["title"] or ""),"output_path":str(p),"output_sha256":_sha(p),"source_clip_ids":_ids(seq),"clip_sequence":seq,"template_key":"composer:"+str(x["aspect"] or "")}

def evaluate_candidate(*,output_path=None,output_sha256=None,source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",persist=True):
    ensure_schema();ids=_ids(source_clip_ids);seq=_ids(clip_sequence if clip_sequence is not None else ids)
    sha=str(output_sha256 or "").strip().lower() or (_sha(output_path) if output_path else "")
    template=str(template_key or "").strip();caption=str(caption_text or "");exact=None
    best={"source_overlap":0.0,"sequence_similarity":0.0,"caption_similarity":0.0,"template_match":False,"publication_id":None}
    with db() as c:
        pubs=c.execute("SELECT * FROM social_publications ORDER BY id DESC").fetchall()
        for r in pubs:
            if sha and str(r["output_sha256"] or "").lower()==sha:exact=int(r["id"]);break
            oi,os=_json_ids(r["source_clip_ids_json"]),_json_ids(r["clip_sequence_json"])
            ov,sq,cp,tm=_jac(ids,oi),_seq(seq,os),_cap(caption,r["caption_text"]),bool(template and str(r["template_key"] or "")==template)
            score=ov*.55+sq*.30+cp*.10+(.05 if tm else 0);bs=best["source_overlap"]*.55+best["sequence_similarity"]*.30+best["caption_similarity"]*.10+(.05 if best["template_match"] else 0)
            if score>bs:best={"source_overlap":round(ov,4),"sequence_similarity":round(sq,4),"caption_similarity":round(cp,4),"template_match":tm,"publication_id":int(r["id"])}
        state="exact_duplicate_block" if exact is not None else "too_similar_block" if best["source_overlap"]>=.90 and best["sequence_similarity"]>=.85 else "similar_review" if best["source_overlap"]>=.60 or best["sequence_similarity"]>=.65 or (best["template_match"] and best["caption_similarity"]>=.90) else "new"
        detail={"model":"novelty_guard_v1_structural","visual_similarity":"not_implemented","audio_similarity":"not_implemented","best_publication_id":best["publication_id"]}
        if persist:
            c.execute("INSERT INTO novelty_checks(candidate_sha256,result_state,exact_match_publication_id,max_source_overlap,max_sequence_similarity,max_caption_similarity,template_match,compared_count,detail_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(sha or None,state,exact,best["source_overlap"],best["sequence_similarity"],best["caption_similarity"],1 if best["template_match"] else 0,len(pubs),json.dumps(detail,sort_keys=True),now_iso()));c.commit()
    return {"state":state,"exact_match_publication_id":exact,"compared_count":len(pubs),**best,**detail}

def evaluate_composition(cid,caption_text=""):
    x=candidate_from_composition(cid)
    return evaluate_candidate(output_path=x["output_path"],output_sha256=x["output_sha256"],source_clip_ids=x["source_clip_ids"],clip_sequence=x["clip_sequence"],template_key=x["template_key"],caption_text=caption_text,persist=True)

def record_publication(*,output_path=None,output_sha256=None,composition_id=None,title="",status="exported",platform="",source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",novelty_state=None,published_at=None):
    ensure_schema();ids=_ids(source_clip_ids);seq=_ids(clip_sequence if clip_sequence is not None else ids);sha=str(output_sha256 or "").strip().lower() or (_sha(output_path) if output_path else "")
    with db() as c:
        old=c.execute("SELECT id FROM social_publications WHERE COALESCE(output_sha256,'')=? AND COALESCE(composition_id,-1)=? AND status=? AND COALESCE(platform,'')=? ORDER BY id DESC LIMIT 1",(sha,int(composition_id) if composition_id is not None else -1,str(status or "exported"),str(platform or ""))).fetchone()
        if old:return int(old["id"])
        cur=c.execute("INSERT INTO social_publications(status,output_path,output_sha256,composition_id,title,platform,source_clip_ids_json,clip_sequence_json,template_key,caption_text,novelty_state,created_at,published_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(str(status or "exported"),str(output_path or "") or None,sha or None,int(composition_id) if composition_id is not None else None,str(title or "")[:160],str(platform or "")[:80],json.dumps(ids),json.dumps(seq),str(template_key or "")[:120],str(caption_text or "")[:2000],str(novelty_state or "") or None,now_iso(),published_at));c.commit();return int(cur.lastrowid)

def record_composition(cid,status="exported",platform="",caption_text=""):
    x=candidate_from_composition(cid);r=evaluate_composition(cid,caption_text)
    pid=record_publication(output_path=x["output_path"],output_sha256=x["output_sha256"],composition_id=x["composition_id"],title=x["title"],status=status,platform=platform,source_clip_ids=x["source_clip_ids"],clip_sequence=x["clip_sequence"],template_key=x["template_key"],caption_text=caption_text,novelty_state=r["state"],published_at=now_iso() if status=="published" else None)
    return {"publication_id":pid,"novelty":r}

def ensure_queue_schema():
    ensure_schema()
    with db() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS social_queue(
        id INTEGER PRIMARY KEY AUTOINCREMENT,composition_id INTEGER,publication_id INTEGER,
        title TEXT,platform_target TEXT,caption_text TEXT,novelty_state TEXT NOT NULL,
        queue_state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_social_queue_state ON social_queue(queue_state,id);
        CREATE INDEX IF NOT EXISTS idx_social_queue_comp ON social_queue(composition_id);""");c.commit()

def queue_state_for_novelty(state):
    s=str(state or "")
    if s=="new":return "ready"
    if s=="similar_review":return "review"
    if s in ("too_similar_block","exact_duplicate_block"):return "hold"
    return "review"

def list_queue(limit=50):
    ensure_queue_schema();limit=max(1,min(int(limit or 50),200))
    with db() as c:return [dict(r) for r in c.execute("SELECT id,composition_id,publication_id,title,platform_target,caption_text,novelty_state,queue_state,created_at,updated_at FROM social_queue ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]

def enqueue_candidate(*,composition_id=None,publication_id=None,title="",platform_target="",caption_text="",novelty_state):
    ensure_queue_schema();state=queue_state_for_novelty(novelty_state);ts=now_iso()
    with db() as c:
        if composition_id is not None:
            _require_composition_source_visibility(c,int(composition_id))
            old=c.execute("SELECT id,queue_state FROM social_queue WHERE composition_id=? AND queue_state NOT IN ('done','canceled') ORDER BY id DESC LIMIT 1",(int(composition_id),)).fetchone()
            if old:return {"queue_id":int(old["id"]),"queue_state":str(old["queue_state"]),"existing":True}
        cur=c.execute("INSERT INTO social_queue(composition_id,publication_id,title,platform_target,caption_text,novelty_state,queue_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(int(composition_id) if composition_id is not None else None,int(publication_id) if publication_id is not None else None,str(title or "")[:160],str(platform_target or "")[:80],str(caption_text or "")[:2000],str(novelty_state),state,ts,ts));c.commit()
        return {"queue_id":int(cur.lastrowid),"queue_state":state,"existing":False}

def enqueue_composition(cid,platform_target="",caption_text=""):
    x=candidate_from_composition(cid);r=evaluate_composition(cid,caption_text)
    q=enqueue_candidate(composition_id=x["composition_id"],title=x["title"],platform_target=platform_target,caption_text=caption_text,novelty_state=r["state"])
    return {"novelty":r,**q}

def set_queue_state(queue_id,new_state):
    ensure_queue_schema();new=str(new_state or "").strip().lower()
    allowed={"ready":{"review","hold","done","canceled"},"review":{"ready","hold","canceled"},"hold":{"canceled"},"done":set(),"canceled":set()}
    with db() as c:
        row=c.execute("SELECT id,queue_state FROM social_queue WHERE id=?",(int(queue_id),)).fetchone()
        if not row:raise ValueError("Queue item not found")
        old=str(row["queue_state"])
        if new==old:return {"queue_id":int(queue_id),"queue_state":old,"unchanged":True}
        if new not in allowed.get(old,set()):raise ValueError("Queue transition not allowed: "+old+" -> "+new)
        c.execute("UPDATE social_queue SET queue_state=?,updated_at=? WHERE id=?",(new,now_iso(),int(queue_id)));c.commit()
    return {"queue_id":int(queue_id),"queue_state":new,"unchanged":False}

_structural_ensure_schema = ensure_schema

import subprocess as _novelty_subprocess
import tempfile as _novelty_tempfile
from .media import _ffmpeg_exe as _novelty_ffmpeg_exe
from .platform_adapter import process_kwargs as _novelty_process_kwargs
from .visual_similarity import _fingerprint_image as _m7_fingerprint_image, _score_fp as _m7_score_fp, MODEL as VISUAL_MODEL

def ensure_schema():
    _structural_ensure_schema()
    with db() as c:
        cols={r["name"] for r in c.execute("PRAGMA table_info(social_publications)").fetchall()}
        for name,ddl in (
            ("visual_model","TEXT"),("visual_dhash","TEXT"),("visual_hist_json","TEXT")
        ):
            if name not in cols:c.execute(f"ALTER TABLE social_publications ADD COLUMN {name} {ddl}")
        ncols={r["name"] for r in c.execute("PRAGMA table_info(novelty_checks)").fetchall()}
        for name,ddl in (("max_visual_similarity","REAL NOT NULL DEFAULT 0"),("visual_model","TEXT")):
            if name not in ncols:c.execute(f"ALTER TABLE novelty_checks ADD COLUMN {name} {ddl}")
        c.commit()

def _visual_fp_for_media(path):
    p=Path(path)
    if not p.exists():return None
    if p.suffix.lower() in (".jpg",".jpeg",".png",".bmp",".webp"):
        try:return _m7_fingerprint_image(p)
        except Exception:return None
    ff=_novelty_ffmpeg_exe()
    if not ff:return None
    with _novelty_tempfile.TemporaryDirectory(prefix="archivist_novelty_visual_") as td:
        dest=Path(td)/"frame.jpg"
        base=[str(ff),"-y","-hide_banner","-loglevel","error"]
        tries=[
            base+["-ss","0.5","-i",str(p),"-frames:v","1","-vf","scale=320:-2",str(dest)],
            base+["-i",str(p),"-frames:v","1","-vf","scale=320:-2",str(dest)]
        ]
        for cmd in tries:
            try:
                r=_novelty_subprocess.run(cmd,capture_output=True,timeout=30,**_novelty_process_kwargs())
                if r.returncode==0 and dest.exists() and dest.stat().st_size>100:
                    return _m7_fingerprint_image(dest)
            except Exception:
                pass
            dest.unlink(missing_ok=True)
    return None

def _visual_pack(fp):
    if not fp:return (None,None,None)
    return (VISUAL_MODEL,str(fp.get("dhash") or "") or None,json.dumps(fp.get("hist") or []))

def _visual_unpack(model,dhash,hist_json):
    if model!=VISUAL_MODEL or not dhash or not hist_json:return None
    try:return {"dhash":str(dhash),"hist":json.loads(hist_json)}
    except Exception:return None

def classify_visual_score(score):
    try:s=float(score)
    except Exception:return None
    if s>=0.97:return "too_similar_block"
    if s>=0.90:return "similar_review"
    return None

def evaluate_candidate(*,output_path=None,output_sha256=None,source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",persist=True):
    ensure_schema();ids=_ids(source_clip_ids);seq=_ids(clip_sequence if clip_sequence is not None else ids)
    sha=str(output_sha256 or "").strip().lower() or (_sha(output_path) if output_path else "")
    template=str(template_key or "").strip();caption=str(caption_text or "");exact=None
    candidate_fp=_visual_fp_for_media(output_path) if output_path else None
    best={"source_overlap":0.0,"sequence_similarity":0.0,"caption_similarity":0.0,"template_match":False,"publication_id":None}
    max_visual=0.0;visual_pub=None;visual_history=0
    with db() as c:
        pubs=c.execute("SELECT * FROM social_publications ORDER BY id DESC").fetchall()
        for r in pubs:
            if sha and str(r["output_sha256"] or "").lower()==sha:exact=int(r["id"]);break
            oi,os=_json_ids(r["source_clip_ids_json"]),_json_ids(r["clip_sequence_json"])
            ov,sq,cp,tm=_jac(ids,oi),_seq(seq,os),_cap(caption,r["caption_text"]),bool(template and str(r["template_key"] or "")==template)
            score=ov*.55+sq*.30+cp*.10+(.05 if tm else 0);bs=best["source_overlap"]*.55+best["sequence_similarity"]*.30+best["caption_similarity"]*.10+(.05 if best["template_match"] else 0)
            if score>bs:best={"source_overlap":round(ov,4),"sequence_similarity":round(sq,4),"caption_similarity":round(cp,4),"template_match":tm,"publication_id":int(r["id"])}
            pub_fp=_visual_unpack(r["visual_model"],r["visual_dhash"],r["visual_hist_json"])
            if candidate_fp and pub_fp:
                visual_history+=1
                try:vs=float(_m7_score_fp(candidate_fp,pub_fp))
                except Exception:vs=0.0
                if vs>max_visual:max_visual=vs;visual_pub=int(r["id"])
        visual_state=classify_visual_score(max_visual)
        structural_block=best["source_overlap"]>=.90 and best["sequence_similarity"]>=.85
        structural_review=best["source_overlap"]>=.60 or best["sequence_similarity"]>=.65 or (best["template_match"] and best["caption_similarity"]>=.90)
        state="exact_duplicate_block" if exact is not None else "too_similar_block" if structural_block or visual_state=="too_similar_block" else "similar_review" if structural_review or visual_state=="similar_review" else "new"
        detail={"model":"novelty_guard_v2_visual_structural","visual_model":VISUAL_MODEL,"max_visual_similarity":round(max_visual,4),"visual_publication_id":visual_pub,"visual_history_count":visual_history,"audio_similarity":"not_implemented","best_publication_id":best["publication_id"]}
        if persist:
            c.execute("INSERT INTO novelty_checks(candidate_sha256,result_state,exact_match_publication_id,max_source_overlap,max_sequence_similarity,max_caption_similarity,template_match,compared_count,detail_json,created_at,max_visual_similarity,visual_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(sha or None,state,exact,best["source_overlap"],best["sequence_similarity"],best["caption_similarity"],1 if best["template_match"] else 0,len(pubs),json.dumps(detail,sort_keys=True),now_iso(),round(max_visual,4),VISUAL_MODEL));c.commit()
    return {"state":state,"exact_match_publication_id":exact,"compared_count":len(pubs),**best,**detail}

def record_publication(*,output_path=None,output_sha256=None,composition_id=None,title="",status="exported",platform="",source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",novelty_state=None,published_at=None):
    ensure_schema();ids=_ids(source_clip_ids);seq=_ids(clip_sequence if clip_sequence is not None else ids);sha=str(output_sha256 or "").strip().lower() or (_sha(output_path) if output_path else "")
    fp=_visual_fp_for_media(output_path) if output_path else None
    vmodel,vdhash,vhist=_visual_pack(fp)
    with db() as c:
        old=c.execute("SELECT id FROM social_publications WHERE COALESCE(output_sha256,'')=? AND COALESCE(composition_id,-1)=? AND status=? AND COALESCE(platform,'')=? ORDER BY id DESC LIMIT 1",(sha,int(composition_id) if composition_id is not None else -1,str(status or "exported"),str(platform or ""))).fetchone()
        if old:
            if fp:c.execute("UPDATE social_publications SET visual_model=?,visual_dhash=?,visual_hist_json=? WHERE id=?",(vmodel,vdhash,vhist,int(old["id"])));c.commit()
            return int(old["id"])
        cur=c.execute("INSERT INTO social_publications(status,output_path,output_sha256,composition_id,title,platform,source_clip_ids_json,clip_sequence_json,template_key,caption_text,novelty_state,created_at,published_at,visual_model,visual_dhash,visual_hist_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(str(status or "exported"),str(output_path or "") or None,sha or None,int(composition_id) if composition_id is not None else None,str(title or "")[:160],str(platform or "")[:80],json.dumps(ids),json.dumps(seq),str(template_key or "")[:120],str(caption_text or "")[:2000],str(novelty_state or "") or None,now_iso(),published_at,vmodel,vdhash,vhist));c.commit();return int(cur.lastrowid)

_visual_ensure_schema = ensure_schema
_visual_evaluate_candidate = evaluate_candidate
_visual_record_publication = record_publication

import numpy as _audio_np
AUDIO_MODEL="audio_spectrum_v1"

def ensure_schema():
    _visual_ensure_schema()
    with db() as c:
        pcols={r["name"] for r in c.execute("PRAGMA table_info(social_publications)").fetchall()}
        for name,ddl in (("audio_model","TEXT"),("audio_fp_json","TEXT")):
            if name not in pcols:c.execute(f"ALTER TABLE social_publications ADD COLUMN {name} {ddl}")
        ncols={r["name"] for r in c.execute("PRAGMA table_info(novelty_checks)").fetchall()}
        for name,ddl in (("max_audio_similarity","REAL NOT NULL DEFAULT 0"),("audio_model","TEXT")):
            if name not in ncols:c.execute(f"ALTER TABLE novelty_checks ADD COLUMN {name} {ddl}")
        c.commit()

def _audio_fp_for_media(path):
    p=Path(path)
    if not p.exists():return None
    ff=_novelty_ffmpeg_exe()
    if not ff:return None
    try:
        r=_novelty_subprocess.run([str(ff),"-hide_banner","-loglevel","error","-i",str(p),"-vn","-ac","1","-ar","8000","-f","s16le","pipe:1"],capture_output=True,timeout=75,**_novelty_process_kwargs())
        if r.returncode!=0 or len(r.stdout)<1600:return None
        x=_audio_np.frombuffer(r.stdout,dtype=_audio_np.int16).astype(_audio_np.float32)/32768.0
        if x.size<800:return None
        max_samples=8000*180
        if x.size>max_samples:
            idx=_audio_np.linspace(0,x.size-1,max_samples,dtype=_audio_np.int64);x=x[idx]
        win=2048
        starts=_audio_np.linspace(0,max(0,x.size-win),min(32,max(1,x.size//win)),dtype=_audio_np.int64)
        specs=[]
        hann=_audio_np.hanning(win).astype(_audio_np.float32)
        edges=_audio_np.unique(_audio_np.geomspace(1,win//2+1,17).astype(_audio_np.int64))
        if len(edges)<17:edges=_audio_np.linspace(1,win//2+1,17,dtype=_audio_np.int64)
        for s in starts:
            seg=x[int(s):int(s)+win]
            if seg.size<win:seg=_audio_np.pad(seg,(0,win-seg.size))
            mag=_audio_np.abs(_audio_np.fft.rfft(seg*hann))
            bands=[]
            for a,b in zip(edges[:-1],edges[1:]):
                bands.append(float(_audio_np.log1p(mag[int(a):max(int(a)+1,int(b))].mean())))
            v=_audio_np.asarray(bands,dtype=_audio_np.float32);norm=float(_audio_np.linalg.norm(v))
            if norm>0:v/=norm
            specs.append(v)
        spectral=_audio_np.mean(_audio_np.stack(specs),axis=0);sn=float(_audio_np.linalg.norm(spectral))
        if sn>0:spectral/=sn
        chunks=_audio_np.array_split(x,24);energy=_audio_np.asarray([float(_audio_np.sqrt(_audio_np.mean(c*c))) if c.size else 0.0 for c in chunks],dtype=_audio_np.float32)
        em=float(energy.max()) if energy.size else 0.0
        if em>0:energy/=em
        return {"spectral":[round(float(v),6) for v in spectral],"energy":[round(float(v),6) for v in energy]}
    except Exception:
        return None

def _audio_score(a,b):
    if not a or not b:return 0.0
    try:
        sa=_audio_np.asarray(a.get("spectral") or [],dtype=_audio_np.float32);sb=_audio_np.asarray(b.get("spectral") or [],dtype=_audio_np.float32)
        ea=_audio_np.asarray(a.get("energy") or [],dtype=_audio_np.float32);eb=_audio_np.asarray(b.get("energy") or [],dtype=_audio_np.float32)
        if sa.size==0 or sb.size!=sa.size:return 0.0
        ss=float(_audio_np.dot(sa,sb)/(max(1e-8,float(_audio_np.linalg.norm(sa)*_audio_np.linalg.norm(sb)))))
        es=0.0
        if ea.size and eb.size==ea.size:es=float(_audio_np.dot(ea,eb)/(max(1e-8,float(_audio_np.linalg.norm(ea)*_audio_np.linalg.norm(eb)))))
        return round(max(0.0,min(1.0,.85*ss+.15*es)),4)
    except Exception:return 0.0

def classify_audio_score(score):
    try:s=float(score)
    except Exception:return None
    return "similar_review" if s>=0.97 else None

def evaluate_candidate(*,output_path=None,output_sha256=None,source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",persist=True):
    base=_visual_evaluate_candidate(output_path=output_path,output_sha256=output_sha256,source_clip_ids=source_clip_ids,clip_sequence=clip_sequence,template_key=template_key,caption_text=caption_text,persist=False)
    ensure_schema();candidate_audio=_audio_fp_for_media(output_path) if output_path else None
    max_audio=0.0;audio_pub=None;audio_history=0
    with db() as c:
        pubs=c.execute("SELECT id,audio_model,audio_fp_json FROM social_publications ORDER BY id DESC").fetchall()
        for r in pubs:
            if not candidate_audio or r["audio_model"]!=AUDIO_MODEL or not r["audio_fp_json"]:continue
            try:pub_fp=json.loads(r["audio_fp_json"])
            except Exception:continue
            audio_history+=1;s=_audio_score(candidate_audio,pub_fp)
            if s>max_audio:max_audio=s;audio_pub=int(r["id"])
        state=base["state"]
        strong_other=float(base.get("max_visual_similarity") or 0)>=.90 or float(base.get("source_overlap") or 0)>=.60
        if state not in ("exact_duplicate_block","too_similar_block"):
            if max_audio>=.985 and strong_other:state="too_similar_block"
            elif max_audio>=.97 and state=="new":state="similar_review"
        detail=dict(base);detail.update({"state":state,"model":"novelty_guard_v3_audio_visual_structural","audio_model":AUDIO_MODEL,"max_audio_similarity":round(max_audio,4),"audio_publication_id":audio_pub,"audio_history_count":audio_history})
        if persist:
            c.execute("INSERT INTO novelty_checks(candidate_sha256,result_state,exact_match_publication_id,max_source_overlap,max_sequence_similarity,max_caption_similarity,template_match,compared_count,detail_json,created_at,max_visual_similarity,visual_model,max_audio_similarity,audio_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(str(output_sha256 or "") or None,state,base.get("exact_match_publication_id"),float(base.get("source_overlap") or 0),float(base.get("sequence_similarity") or 0),float(base.get("caption_similarity") or 0),1 if base.get("template_match") else 0,int(base.get("compared_count") or 0),json.dumps({k:v for k,v in detail.items() if k not in ("state",)},sort_keys=True),now_iso(),float(base.get("max_visual_similarity") or 0),str(base.get("visual_model") or VISUAL_MODEL),round(max_audio,4),AUDIO_MODEL));c.commit()
    return detail

def record_publication(*,output_path=None,output_sha256=None,composition_id=None,title="",status="exported",platform="",source_clip_ids=None,clip_sequence=None,template_key="",caption_text="",novelty_state=None,published_at=None):
    if composition_id is not None:
        with db() as c:_require_composition_source_visibility(c,int(composition_id))
    pid=_visual_record_publication(output_path=output_path,output_sha256=output_sha256,composition_id=composition_id,title=title,status=status,platform=platform,source_clip_ids=source_clip_ids,clip_sequence=clip_sequence,template_key=template_key,caption_text=caption_text,novelty_state=novelty_state,published_at=published_at)
    fp=_audio_fp_for_media(output_path) if output_path else None
    if fp:
        with db() as c:c.execute("UPDATE social_publications SET audio_model=?,audio_fp_json=? WHERE id=?",(AUDIO_MODEL,json.dumps(fp),int(pid)));c.commit()
    return pid

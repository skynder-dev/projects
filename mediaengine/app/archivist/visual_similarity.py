from __future__ import annotations
import json, math
from pathlib import Path
from PIL import Image, ImageStat
from .db import db, now_iso
from .service import cached_thumbnail

MODEL="visual_dhash_v1"

def ensure_schema():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS visual_fingerprints(
          inventory_id INTEGER PRIMARY KEY REFERENCES inventory(id) ON DELETE CASCADE,
          model TEXT NOT NULL,
          dhash TEXT NOT NULL,
          hist_json TEXT NOT NULL,
          thumb_size INTEGER NOT NULL DEFAULT 0,
          thumb_mtime_ns INTEGER NOT NULL DEFAULT 0,
          indexed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_visual_fp_model ON visual_fingerprints(model);
        """)
        con.commit()

def _fingerprint_image(path):
    p=Path(path)
    with Image.open(p) as im:
        gray=im.convert("L").resize((9,8),Image.Resampling.LANCZOS)
        px=list(gray.getdata()); bits=0
        for y in range(8):
            for x in range(8):
                bits=(bits<<1) | (1 if px[y*9+x] > px[y*9+x+1] else 0)
        rgb=im.convert("RGB").resize((32,32),Image.Resampling.BILINEAR)
        hist=rgb.histogram()
        vec=[]
        for ch in range(3):
            h=hist[ch*256:(ch+1)*256]
            for b in range(8):
                vec.append(sum(h[b*32:(b+1)*32])/1024.0)
        return {"dhash":f"{bits:016x}","hist":vec}

def _score_fp(a,b):
    x=int(a["dhash"],16)^int(b["dhash"],16)
    ham=x.bit_count() if hasattr(int,"bit_count") else bin(x).count("1")
    dh=1.0-ham/64.0
    va=a["hist"]; vb=b["hist"]
    dist=math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(va,vb))/max(1,len(va)))
    color=max(0.0,1.0-min(1.0,dist))
    return round(0.82*dh+0.18*color,4)

def rebuild_index():
    ensure_schema()
    with db() as con:
        rows=[dict(r) for r in con.execute("""
          SELECT id FROM inventory
          WHERE excluded=0 AND work_selected=1
            AND private_path IS NULL AND rejected_path IS NULL
            AND analysis_status<>'private'
        """).fetchall()]
        alive=[]
        for r in rows:
            iid=int(r["id"]); p=cached_thumbnail(iid)
            if not p or not Path(p).exists(): continue
            st=Path(p).stat(); alive.append(iid)
            old=con.execute("SELECT thumb_size,thumb_mtime_ns FROM visual_fingerprints WHERE inventory_id=? AND model=?",(iid,MODEL)).fetchone()
            if old and int(old["thumb_size"] or 0)==int(st.st_size) and int(old["thumb_mtime_ns"] or 0)==int(st.st_mtime_ns):
                continue
            fp=_fingerprint_image(p)
            con.execute("""INSERT INTO visual_fingerprints(inventory_id,model,dhash,hist_json,thumb_size,thumb_mtime_ns,indexed_at)
              VALUES(?,?,?,?,?,?,?)
              ON CONFLICT(inventory_id) DO UPDATE SET model=excluded.model,dhash=excluded.dhash,hist_json=excluded.hist_json,
              thumb_size=excluded.thumb_size,thumb_mtime_ns=excluded.thumb_mtime_ns,indexed_at=excluded.indexed_at""",
              (iid,MODEL,fp["dhash"],json.dumps(fp["hist"]),int(st.st_size),int(st.st_mtime_ns),now_iso()))
        if alive:
            con.execute("DELETE FROM visual_fingerprints WHERE inventory_id NOT IN ("+",".join("?" for _ in alive)+")",alive)
        else:
            con.execute("DELETE FROM visual_fingerprints")
        con.commit()
        return len(alive)

def find_similar(inventory_id,limit=24):
    count=rebuild_index(); iid=int(inventory_id)
    with db() as con:
        t=con.execute("SELECT dhash,hist_json FROM visual_fingerprints WHERE inventory_id=? AND model=?",(iid,MODEL)).fetchone()
        if not t:return {"model":MODEL,"index_count":count,"results":[],"reason":"thumbnail_not_ready"}
        target={"dhash":t["dhash"],"hist":json.loads(t["hist_json"])}
        rows=[dict(r) for r in con.execute("""SELECT f.inventory_id,f.dhash,f.hist_json,i.filename,i.source_label,i.media_type,
          i.duration_ms,i.width,i.height,s.best_clip_id,s.best_clip_score
          FROM visual_fingerprints f JOIN inventory i ON i.id=f.inventory_id
          LEFT JOIN semantic_index s ON s.inventory_id=i.id
          WHERE f.model=? AND f.inventory_id<>? AND i.excluded=0 AND i.work_selected=1""",(MODEL,iid)).fetchall()]
    out=[]
    for r in rows:
        score=_score_fp(target,{"dhash":r.pop("dhash"),"hist":json.loads(r.pop("hist_json"))})
        r["visual_score"]=score; out.append(r)
    out.sort(key=lambda r:(r["visual_score"],float(r.get("best_clip_score") or 0),int(r["inventory_id"])),reverse=True)
    return {"model":MODEL,"index_count":count,"results":out[:max(1,min(100,int(limit)))]}

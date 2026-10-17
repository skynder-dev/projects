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

_VISIBLE = """excluded=0 AND work_selected=1 AND private_path IS NULL AND rejected_path IS NULL
            AND analysis_status<>'private' AND COALESCE(sha256,'') NOT IN (SELECT sha256 FROM ignored_hashes)"""
_LAST = {"at": 0.0, "count": 0}


def rebuild_index(max_age_s: float = 0.0):
    """Fingerprints of the visible Library's thumbnails. One query for the picture paths and the stored state, new or
    changed pictures written in short batches (the whole Library in one transaction held the write lock for seconds
    and could fail an import or a reel's progress with "database is locked"), the rest only compared."""
    import time as _t
    if max_age_s and _t.monotonic() - _LAST["at"] < max_age_s:
        return _LAST["count"]
    from .config import THUMBS
    ensure_schema()
    with db() as con:
        rows = [dict(r) for r in con.execute(f"""
          SELECT i.id, i.preview_path, f.thumb_size, f.thumb_mtime_ns, f.model
          FROM inventory i LEFT JOIN visual_fingerprints f ON f.inventory_id=i.id
          WHERE i.id IN (SELECT id FROM inventory WHERE {_VISIBLE})
        """).fetchall()]
    alive, todo = 0, []
    for r in rows:
        iid = int(r["id"])
        p = Path(r["preview_path"]) if r["preview_path"] and Path(r["preview_path"]).exists() else THUMBS / f"{iid}.jpg"
        try:
            st = p.stat()
        except OSError:
            continue
        alive += 1
        if r["model"] == MODEL and int(r["thumb_size"] or 0) == int(st.st_size) and int(r["thumb_mtime_ns"] or 0) == int(st.st_mtime_ns):
            continue
        try:
            fp = _fingerprint_image(p)
        except Exception:
            continue
        todo.append((iid, MODEL, fp["dhash"], json.dumps(fp["hist"]), int(st.st_size), int(st.st_mtime_ns), now_iso()))
        if len(todo) >= 200:
            _write(todo)
    _write(todo)
    with db() as con:      # (a subquery, not a list of ids: a list past ~32k ids overflowed SQLite)
        con.execute(f"DELETE FROM visual_fingerprints WHERE inventory_id NOT IN (SELECT id FROM inventory WHERE {_VISIBLE})")
        con.commit()
    _LAST.update(at=_t.monotonic(), count=alive)
    return alive


def _write(todo: list) -> None:
    if not todo:
        return
    with db() as con:
        con.executemany("""INSERT INTO visual_fingerprints(inventory_id,model,dhash,hist_json,thumb_size,thumb_mtime_ns,indexed_at)
          VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(inventory_id) DO UPDATE SET model=excluded.model,dhash=excluded.dhash,hist_json=excluded.hist_json,
          thumb_size=excluded.thumb_size,thumb_mtime_ns=excluded.thumb_mtime_ns,indexed_at=excluded.indexed_at""", todo)
        con.commit()
    todo.clear()

def find_similar(inventory_id,limit=24):
    try:   # the best-moment columns come from the search index; on a fresh library it may not exist yet (was HTTP 500)
        from .semantic_search import ensure_schema as _search_schema
        _search_schema()
    except Exception:
        pass
    count=rebuild_index(max_age_s=20); iid=int(inventory_id)   # (pages opened one after another reuse it)
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

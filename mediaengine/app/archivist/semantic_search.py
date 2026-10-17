from __future__ import annotations

import json, re
from .db import db, now_iso
from .media_brain import ensure_schema as ensure_media_brain_schema

SEARCH_MODEL="signals_v1"
STOPWORDS={"a","an","the","of","with","from","my","in","on","for","and","or","show","find","me","please",
           "video","videos","clip","clips","photo","photos","image","images",
           "мне","найди","покажи","в","на","из","и","или","мои","мое","моё"}

INTENT_PHRASES={
 "video":("video","videos","видео"),
 "image":("photo","photos","image","images","фото","fotograf"),
 "portrait":("vertical","portrait","reels","reel","shorts","вертик","портрет","vertikal","portret"),
 "landscape":("landscape","horizontal","wide","горизонт","gorizont"),
 "square":("square","квадрат","kvadrat"),
 "dark":("night","nighttime","dark","evening","ноч","темн","вечер","noch","temn","vecher"),
 "bright":("bright","daylight","sunny","day time","светл","день","svetl","den"),
 "high_motion":("high motion","action","moving","fast","dynamic","движ","динами","быстр","dvizh","dinamik","bystr"),
 "low_motion":("low motion","calm","static","steady","stable shot","спокой","статич","stabil","spokoy","statich"),
 "best":("best","top","highlight","best moments","луч","luchsh"),
 "drone":("drone","dji","дрон","dron"),
 "android":("android","phone","телефон","telefon"),
 "removable":("sd card","sd","usb","flash drive","карта памяти","флеш","karta","flash"),
 "fixed":("local folder","local folders","folder","папк","papk"),
 "audio":("audio","sound","music","звук","музык","zvuk","muzyk"),
 "silent":("silent","mute","no audio","without audio","без звука","bez zvuka"),
 "short":("short video","short clip","brief","корот","korot"),
 "long":("long video","long clip","lengthy","длин","dlin"),
 "safe":("privacy safe","safe","безопас","bezopas"),
 "rights_clear":("rights cleared","cleared rights","publishable","права очищ","razresh"),
 "quality":("high quality","quality","sharp","качеств","резк","kachestv","rezk"),
}

SEMANTIC_SCHEMA_VERSION="2"

def ensure_schema():
    ensure_media_brain_schema()
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS semantic_index(
            inventory_id INTEGER PRIMARY KEY REFERENCES inventory(id) ON DELETE CASCADE,
            model TEXT NOT NULL,
            text_terms TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            best_clip_id INTEGER,
            best_clip_score REAL,
            max_motion REAL,
            avg_brightness REAL,
            avg_detail REAL,
            clip_count INTEGER NOT NULL DEFAULT 0,
            indexed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_semantic_model ON semantic_index(model);
        CREATE TABLE IF NOT EXISTS semantic_dirty(
            inventory_id INTEGER PRIMARY KEY REFERENCES inventory(id) ON DELETE CASCADE,
            reason TEXT NOT NULL DEFAULT 'change',
            dirtied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS semantic_meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS trg_semantic_inventory_insert
        AFTER INSERT ON inventory
        BEGIN
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            VALUES(NEW.id,'inventory_insert',CURRENT_TIMESTAMP)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_semantic_inventory_update
        AFTER UPDATE OF filename,source_label,source_kind,media_type,duration_ms,width,height,
                        analysis_status,quality_status,quality_score,rights_status,rights_audio_present,
                        excluded,work_selected,private_path,rejected_path
        ON inventory
        BEGIN
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            VALUES(NEW.id,'inventory_update',CURRENT_TIMESTAMP)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_semantic_vclip_insert
        AFTER INSERT ON virtual_clips
        BEGIN
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            VALUES(NEW.inventory_id,'virtual_clip_insert',CURRENT_TIMESTAMP)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_semantic_vclip_update
        AFTER UPDATE ON virtual_clips
        BEGIN
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            VALUES(OLD.inventory_id,'virtual_clip_update',CURRENT_TIMESTAMP)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            VALUES(NEW.inventory_id,'virtual_clip_update',CURRENT_TIMESTAMP)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_semantic_vclip_delete
        AFTER DELETE ON virtual_clips
        BEGIN
            INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
            SELECT OLD.inventory_id,'virtual_clip_delete',CURRENT_TIMESTAMP
            WHERE EXISTS (SELECT 1 FROM inventory WHERE id=OLD.inventory_id)
            ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
        END;
        """)
        state={str(r["key"]):str(r["value"]) for r in con.execute("SELECT key,value FROM semantic_meta").fetchall()}
        if state.get("update_trigger")!="2":
            # only a real change marks a video for re-indexing (every unchanged rescan marked the whole catalog)
            con.executescript("""
            DROP TRIGGER IF EXISTS trg_semantic_inventory_update;
            CREATE TRIGGER trg_semantic_inventory_update
            AFTER UPDATE OF filename,source_label,source_kind,media_type,duration_ms,width,height,
                            analysis_status,quality_status,quality_score,rights_status,rights_audio_present,
                            excluded,work_selected,private_path,rejected_path
            ON inventory
            WHEN OLD.filename IS NOT NEW.filename OR OLD.source_label IS NOT NEW.source_label
              OR OLD.source_kind IS NOT NEW.source_kind OR OLD.media_type IS NOT NEW.media_type
              OR OLD.duration_ms IS NOT NEW.duration_ms OR OLD.width IS NOT NEW.width OR OLD.height IS NOT NEW.height
              OR OLD.analysis_status IS NOT NEW.analysis_status OR OLD.quality_status IS NOT NEW.quality_status
              OR OLD.quality_score IS NOT NEW.quality_score OR OLD.rights_status IS NOT NEW.rights_status
              OR OLD.rights_audio_present IS NOT NEW.rights_audio_present OR OLD.excluded IS NOT NEW.excluded
              OR OLD.work_selected IS NOT NEW.work_selected OR OLD.private_path IS NOT NEW.private_path
              OR OLD.rejected_path IS NOT NEW.rejected_path
            BEGIN
                INSERT INTO semantic_dirty(inventory_id,reason,dirtied_at)
                VALUES(NEW.id,'inventory_update',CURRENT_TIMESTAMP)
                ON CONFLICT(inventory_id) DO UPDATE SET reason=excluded.reason,dirtied_at=excluded.dirtied_at;
            END;
            INSERT INTO semantic_meta(key,value) VALUES('update_trigger','2') ON CONFLICT(key) DO UPDATE SET value=excluded.value;
            """)
        if state.get("schema_version")!=SEMANTIC_SCHEMA_VERSION or state.get("model")!=SEARCH_MODEL:
            ts=now_iso()
            con.execute("""INSERT OR REPLACE INTO semantic_dirty(inventory_id,reason,dirtied_at)
                           SELECT id,'schema_or_model_upgrade',? FROM inventory""",(ts,))
            con.execute("DELETE FROM semantic_index WHERE inventory_id NOT IN (SELECT id FROM inventory)")
            con.execute("""INSERT INTO semantic_meta(key,value) VALUES('schema_version',?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(SEMANTIC_SCHEMA_VERSION,))
            con.execute("""INSERT INTO semantic_meta(key,value) VALUES('model',?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(SEARCH_MODEL,))
        con.commit()

def _norm(s):
    return re.sub(r"\s+"," ",str(s or "").lower().replace("_"," ").replace("-"," ")).strip()

def parse_query(query):
    q=_norm(query)
    intents=set()
    consumed=set()
    for key,phrases in INTENT_PHRASES.items():
        for phrase in phrases:
            p=_norm(phrase)
            if p and p in q:
                intents.add(key)
                consumed.update(re.findall(r"[\w]+",p,re.UNICODE))
                break
    toks=[x for x in re.findall(r"[\w]+",q,re.UNICODE) if len(x)>=2 and x not in STOPWORDS and x not in consumed]
    if re.search(r"\bshort\b",q): intents.add("short")
    return {"query":q,"intents":sorted(intents),"tokens":toks[:20]}

def _orientation(w,h):
    try:w=float(w or 0);h=float(h or 0)
    except Exception:return "unknown"
    if w<=0 or h<=0:return "unknown"
    r=w/h
    if r<=.80:return "portrait"
    if r>=1.25:return "landscape"
    return "square"

def _duration_tag(ms):
    try:s=float(ms or 0)/1000.0
    except Exception:return "unknown"
    if s<=0:return "unknown"
    if s<=30:return "short"
    if s>180:return "long"
    return "medium"

def _row_tags(r):
    tags=set()
    mt=str(r.get("media_type") or "")
    if mt:tags.add(mt)
    orient=_orientation(r.get("width"),r.get("height"))
    if orient!="unknown":tags.add(orient)
    dtag=_duration_tag(r.get("duration_ms"))
    if dtag!="unknown":tags.add(dtag)
    sk=str(r.get("source_kind") or "")
    if sk:tags.add(sk)
    if int(r.get("rights_audio_present") or 0):tags.add("audio")
    else:tags.add("silent")
    if str(r.get("analysis_status") or "")=="safe":tags.add("safe")
    if str(r.get("rights_status") or "")=="cleared":tags.add("rights_clear")
    try:
        qs=float(r.get("quality_score") or 0)
        if qs>=75:tags.add("quality")
    except Exception:pass
    label=_norm(r.get("source_label"))
    fn=_norm(r.get("filename"))
    if "drone" in label or "dji" in label or fn.startswith("dji"):tags.add("drone")
    clips=int(r.get("clip_count") or 0)
    if clips:
        try:
            b=float(r.get("avg_brightness") or 0)
            if b<=.32:tags.add("dark")
            if b>=.68:tags.add("bright")
        except Exception:pass
        try:
            m=float(r.get("max_motion") or 0)
            if m>=.12:tags.add("high_motion")
            if m<=.035:tags.add("low_motion")
        except Exception:pass
        try:
            bs=float(r.get("best_clip_score") or 0)
            if bs>=78:tags.add("best")
            elif bs>=62:tags.add("good")
        except Exception:pass
        try:
            de=float(r.get("avg_detail") or 0)
            if de>=.72:tags.add("quality")
        except Exception:pass
    return sorted(tags)

def _refresh_dirty_index(limit=None):
    ensure_schema()
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            sql="SELECT inventory_id FROM semantic_dirty ORDER BY inventory_id"
            params=()
            if limit is not None:
                sql+=" LIMIT ?";params=(max(1,int(limit)),)
            ids=[int(r["inventory_id"]) for r in con.execute(sql,params).fetchall()]
            if not ids:
                count=int(con.execute("SELECT COUNT(*) AS n FROM semantic_index").fetchone()["n"])
                con.commit()
                return {"processed":0,"index_count":count}
            marks=",".join("?" for _ in ids)
            rows=[dict(x) for x in con.execute(f"""
                SELECT i.id,i.filename,i.source_label,i.source_kind,i.media_type,i.duration_ms,i.width,i.height,
                       i.analysis_status,i.quality_status,i.quality_score,i.rights_status,i.rights_audio_present,
                       COUNT(vc.id) clip_count,MAX(vc.score) best_clip_score,MAX(vc.motion) max_motion,
                       AVG(vc.brightness) avg_brightness,AVG(vc.detail) avg_detail,
                       GROUP_CONCAT(COALESCE(vc.reason,''),' ') clip_reasons,
                       (SELECT v2.id FROM virtual_clips v2 WHERE v2.inventory_id=i.id ORDER BY v2.score DESC,v2.id DESC LIMIT 1) best_clip_id
                FROM inventory i LEFT JOIN virtual_clips vc ON vc.inventory_id=i.id
                WHERE i.id IN ({marks}) AND i.excluded=0 AND i.work_selected=1
                  AND i.private_path IS NULL AND i.rejected_path IS NULL AND i.analysis_status<>'private'
                  AND COALESCE(i.sha256,'') NOT IN (SELECT sha256 FROM ignored_hashes)
                GROUP BY i.id
            """,ids).fetchall()]
            eligible={int(r["id"]):r for r in rows}
            ts=now_iso()
            for iid in ids:
                r=eligible.get(iid)
                if not r:
                    con.execute("DELETE FROM semantic_index WHERE inventory_id=?",(iid,))
                    continue
                tags=_row_tags(r)
                text=" ".join([_norm(r.get("filename")),_norm(r.get("source_label")),_norm(r.get("source_kind")),
                               _norm(r.get("media_type")),_norm(r.get("clip_reasons"))," ".join(tags)])
                con.execute("""INSERT INTO semantic_index(inventory_id,model,text_terms,tags_json,best_clip_id,best_clip_score,
                             max_motion,avg_brightness,avg_detail,clip_count,indexed_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?)
                             ON CONFLICT(inventory_id) DO UPDATE SET model=excluded.model,text_terms=excluded.text_terms,
                             tags_json=excluded.tags_json,best_clip_id=excluded.best_clip_id,best_clip_score=excluded.best_clip_score,
                             max_motion=excluded.max_motion,avg_brightness=excluded.avg_brightness,avg_detail=excluded.avg_detail,
                             clip_count=excluded.clip_count,indexed_at=excluded.indexed_at""",
                            (iid,SEARCH_MODEL,text,json.dumps(tags),r.get("best_clip_id"),r.get("best_clip_score"),
                             r.get("max_motion"),r.get("avg_brightness"),r.get("avg_detail"),int(r.get("clip_count") or 0),ts))
            con.execute("DELETE FROM semantic_dirty WHERE inventory_id IN ("+marks+")",ids)
            count=int(con.execute("SELECT COUNT(*) AS n FROM semantic_index").fetchone()["n"])
            con.commit()
            return {"processed":len(ids),"index_count":count}
        except Exception:
            con.rollback()
            raise

def _refresh_all():
    """Every marked video, 500 at a time: one list of all of them overflowed SQLite's variable limit on a big catalog
    (after a rescan every row was marked) and search failed for good."""
    while True:
        r=_refresh_dirty_index(500)
        if not r["processed"]:
            return r

def rebuild_index():
    ensure_schema()
    with db() as con:
        ts=now_iso()
        con.execute("""INSERT OR REPLACE INTO semantic_dirty(inventory_id,reason,dirtied_at)
                       SELECT id,'explicit_rebuild',? FROM inventory""",(ts,))
        con.execute("DELETE FROM semantic_index WHERE inventory_id NOT IN (SELECT id FROM inventory)")
        con.commit()
    return int(_refresh_all()["index_count"])

def search_library(query,limit=120):
    parsed=parse_query(query);q=parsed["query"]
    if not q:return {"query":"","intents":[],"tokens":[],"results":[],"index_count":int(_refresh_all()["index_count"]),"model":SEARCH_MODEL}
    count=int(_refresh_all()["index_count"]);intents=set(parsed["intents"]);tokens=parsed["tokens"]
    with db() as con:
        rows=[dict(x) for x in con.execute("""
            SELECT i.id,i.filename,i.source_label,i.source_kind,i.media_type,i.size_bytes,i.duration_ms,i.width,i.height,
                   i.analysis_status,i.quality_status,i.quality_score,i.rights_status,i.rights_audio_present,
                   s.text_terms,s.tags_json,s.best_clip_id,s.best_clip_score,s.max_motion,s.avg_brightness,s.avg_detail,s.clip_count
            FROM semantic_index s JOIN inventory i ON i.id=s.inventory_id
            WHERE i.excluded=0 AND i.work_selected=1 AND i.private_path IS NULL AND i.rejected_path IS NULL
              AND i.analysis_status<>'private' AND COALESCE(i.sha256,'') NOT IN (SELECT sha256 FROM ignored_hashes)
        """).fetchall()]
    scored=[]
    hard={"video","image","portrait","landscape","square","dark","bright","high_motion","low_motion",
          "drone","android","removable","fixed","audio","silent","short","long","safe","rights_clear"}
    for r in rows:
        tags=set(json.loads(r.get("tags_json") or "[]"));text=str(r.get("text_terms") or "")
        mismatch=False;score=0.0;why=[]
        for key in intents:
            if key in hard:
                if key in tags:score+=5.0;why.append(key.replace("_"," "))
                else:mismatch=True;break
            elif key=="best":
                bs=float(r.get("best_clip_score") or 0);score+=2.0+5.0*bs/100.0
                if "best" in tags:why.append("best Media Brain moment")
            elif key=="quality":
                qs=float(r.get("quality_score") or 0);de=float(r.get("avg_detail") or 0)
                score+=2.0+3.0*max(qs/100.0,de)
                if "quality" in tags:why.append("quality/detail")
        if mismatch:continue
        token_hits=0
        for t in tokens:
            if t in text:score+=1.8;token_hits+=1
        if tokens and token_hits==0 and not intents:continue
        if tokens and token_hits==0 and any(t not in {"best","top"} for t in tokens):
            continue
        if not intents and not tokens:continue
        score+=min(2.5,float(r.get("best_clip_score") or 0)/40.0)
        r["semantic_score"]=round(score,2);r["why"]=why[:5];r["tags"]=sorted(tags)
        scored.append(r)
    scored.sort(key=lambda x:(x["semantic_score"],float(x.get("best_clip_score") or 0),int(x["id"])),reverse=True)
    return {"query":q,"intents":parsed["intents"],"tokens":tokens,"results":scored[:max(1,min(500,int(limit)))],
            "index_count":count,"model":SEARCH_MODEL}

def capabilities():
    return ["orientation","duration","motion","brightness","quality","source","audio","privacy","rights","Media Brain score","filename/source text"]

from __future__ import annotations
import json
from .db import db,now_iso

EXPERIMENT_STATES=("draft","running","completed","archived")
VARIANT_STATES=("draft","ready","published","retired")

def _clip_order(value):
    if value is None:return []
    if isinstance(value,str):
        s=value.strip()
        if s.startswith("["):
            try:
                parsed=json.loads(s)
                raw=parsed if isinstance(parsed,list) else s.replace(";",",").split(",")
            except Exception:raw=s.replace(";",",").split(",")
        else:raw=s.replace(";",",").split(",")
    elif isinstance(value,(list,tuple)):raw=value
    else:raw=[value]
    out=[]
    for x in raw:
        try:i=int(str(x).strip())
        except Exception:continue
        if i not in out:out.append(i)
    return out[:50]

def _num(value,default=0.0,lo=0.0,hi=None):
    try:x=float(value)
    except Exception:x=float(default)
    if x<lo:x=lo
    if hi is not None and x>hi:x=hi
    return x

def _int(value,default=0,lo=0):
    try:x=int(float(value))
    except Exception:x=int(default)
    return max(lo,x)

def ensure_schema():
    with db() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS social_experiments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,composition_id INTEGER,
          objective TEXT,status TEXT NOT NULL DEFAULT 'draft',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_social_exp_status ON social_experiments(status,id);
        CREATE TABLE IF NOT EXISTS social_experiment_variants(
          id INTEGER PRIMARY KEY AUTOINCREMENT,experiment_id INTEGER NOT NULL REFERENCES social_experiments(id) ON DELETE CASCADE,
          label TEXT NOT NULL,hook_text TEXT,caption_text TEXT,cover_ref TEXT,target_duration_s REAL,
          clip_order_json TEXT NOT NULL DEFAULT '[]',notes TEXT,status TEXT NOT NULL DEFAULT 'draft',
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_social_variant_exp ON social_experiment_variants(experiment_id,id);
        CREATE TABLE IF NOT EXISTS social_experiment_results(
          id INTEGER PRIMARY KEY AUTOINCREMENT,variant_id INTEGER NOT NULL REFERENCES social_experiment_variants(id) ON DELETE CASCADE,
          source TEXT NOT NULL DEFAULT 'manual',observed_at TEXT,views INTEGER NOT NULL DEFAULT 0,
          likes INTEGER NOT NULL DEFAULT 0,comments INTEGER NOT NULL DEFAULT 0,shares INTEGER NOT NULL DEFAULT 0,
          saves INTEGER NOT NULL DEFAULT 0,watch_time_s REAL NOT NULL DEFAULT 0,avg_view_duration_s REAL NOT NULL DEFAULT 0,
          retention_3s_pct REAL,completion_pct REAL,notes TEXT,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_social_result_variant ON social_experiment_results(variant_id,id);
        """);c.commit()

def create_experiment(title,composition_id=None,objective=""):
    ensure_schema();title=str(title or "").strip()[:160] or "Untitled experiment";objective=str(objective or "").strip()[:1000];ts=now_iso()
    cid=None
    if composition_id not in (None,""):
        try:cid=int(composition_id)
        except Exception:cid=None
    with db() as c:
        cur=c.execute("INSERT INTO social_experiments(title,composition_id,objective,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",(title,cid,objective,"draft",ts,ts));c.commit();return int(cur.lastrowid)

def add_variant(experiment_id,label="",hook_text="",caption_text="",cover_ref="",target_duration_s=None,clip_order=None,notes=""):
    ensure_schema();eid=int(experiment_id);ts=now_iso()
    with db() as c:
        if not c.execute("SELECT 1 FROM social_experiments WHERE id=?",(eid,)).fetchone():raise ValueError("Experiment not found")
        dur=None if target_duration_s in (None,"") else _num(target_duration_s,0,0,180)
        order=_clip_order(clip_order)
        cur=c.execute("""INSERT INTO social_experiment_variants(experiment_id,label,hook_text,caption_text,cover_ref,target_duration_s,clip_order_json,notes,status,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(eid,str(label or "").strip()[:120] or "Variant",str(hook_text or "")[:500],str(caption_text or "")[:2000],str(cover_ref or "")[:500],dur,json.dumps(order),str(notes or "")[:1000],"draft",ts,ts));c.execute("UPDATE social_experiments SET updated_at=? WHERE id=?",(ts,eid));c.commit();return int(cur.lastrowid)

def set_experiment_status(experiment_id,status):
    ensure_schema();status=str(status or "").strip().lower()
    if status not in EXPERIMENT_STATES:raise ValueError("Unsupported experiment status")
    with db() as c:c.execute("UPDATE social_experiments SET status=?,updated_at=? WHERE id=?",(status,now_iso(),int(experiment_id)));c.commit()
    return status

def set_variant_status(variant_id,status):
    ensure_schema();status=str(status or "").strip().lower()
    if status not in VARIANT_STATES:raise ValueError("Unsupported variant status")
    with db() as c:c.execute("UPDATE social_experiment_variants SET status=?,updated_at=? WHERE id=?",(status,now_iso(),int(variant_id)));c.commit()
    return status

def record_result(variant_id,source="manual",observed_at=None,views=0,likes=0,comments=0,shares=0,saves=0,watch_time_s=0,avg_view_duration_s=0,retention_3s_pct=None,completion_pct=None,notes=""):
    ensure_schema();vid=int(variant_id);source=str(source or "manual").strip().lower()
    if source not in ("manual","import","provider_api"):raise ValueError("Result source must be manual, import or provider_api")
    with db() as c:
        if not c.execute("SELECT 1 FROM social_experiment_variants WHERE id=?",(vid,)).fetchone():raise ValueError("Variant not found")
        r3=None if retention_3s_pct in (None,"") else _num(retention_3s_pct,0,0,100)
        cp=None if completion_pct in (None,"") else _num(completion_pct,0,0,100)
        cur=c.execute("""INSERT INTO social_experiment_results(variant_id,source,observed_at,views,likes,comments,shares,saves,watch_time_s,avg_view_duration_s,retention_3s_pct,completion_pct,notes,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(vid,source,str(observed_at or "") or now_iso(),_int(views),_int(likes),_int(comments),_int(shares),_int(saves),_num(watch_time_s,0,0),_num(avg_view_duration_s,0,0),r3,cp,str(notes or "")[:1000],now_iso()));c.commit();return int(cur.lastrowid)

def list_experiments(limit=50):
    ensure_schema();limit=max(1,min(int(limit or 50),200))
    with db() as c:
        rows=c.execute("""SELECT e.*,COUNT(DISTINCT v.id) variant_count,COUNT(DISTINCT r.id) result_count
                          FROM social_experiments e LEFT JOIN social_experiment_variants v ON v.experiment_id=e.id
                          LEFT JOIN social_experiment_results r ON r.variant_id=v.id
                          GROUP BY e.id ORDER BY e.id DESC LIMIT ?""",(limit,)).fetchall()
    return [dict(r) for r in rows]

def experiment_detail(experiment_id):
    ensure_schema();eid=int(experiment_id)
    with db() as c:
        e=c.execute("SELECT * FROM social_experiments WHERE id=?",(eid,)).fetchone()
        if not e:return None
        variants=[dict(r) for r in c.execute("SELECT * FROM social_experiment_variants WHERE experiment_id=? ORDER BY id",(eid,)).fetchall()]
        for v in variants:
            v["clip_order"]=_clip_order(v.get("clip_order_json"))
            v["results"]=[dict(r) for r in c.execute("SELECT * FROM social_experiment_results WHERE variant_id=? ORDER BY id DESC",(int(v["id"]),)).fetchall()]
    return {"experiment":dict(e),"variants":variants}

def experiment_stats():
    ensure_schema()
    with db() as c:
        return {"experiments":int(c.execute("SELECT COUNT(*) FROM social_experiments").fetchone()[0]),"variants":int(c.execute("SELECT COUNT(*) FROM social_experiment_variants").fetchone()[0]),"results":int(c.execute("SELECT COUNT(*) FROM social_experiment_results").fetchone()[0])}

def experiment_metric_summaries(experiment_id):
    ensure_schema();eid=int(experiment_id)
    with db() as c:
        variants=[dict(r) for r in c.execute("SELECT id,label,status FROM social_experiment_variants WHERE experiment_id=? ORDER BY id",(eid,)).fetchall()]
        out=[]
        for v in variants:
            rows=[dict(r) for r in c.execute("SELECT * FROM social_experiment_results WHERE variant_id=? ORDER BY id",(int(v["id"]),)).fetchall()]
            total_views=sum(int(r.get("views") or 0) for r in rows)
            total_likes=sum(int(r.get("likes") or 0) for r in rows)
            total_comments=sum(int(r.get("comments") or 0) for r in rows)
            total_shares=sum(int(r.get("shares") or 0) for r in rows)
            total_saves=sum(int(r.get("saves") or 0) for r in rows)
            total_watch=sum(float(r.get("watch_time_s") or 0) for r in rows)
            weighted=[]
            for key in ("avg_view_duration_s","retention_3s_pct","completion_pct"):
                vals=[(float(r.get(key)),max(0,int(r.get("views") or 0))) for r in rows if r.get(key) is not None]
                if not vals:weighted.append(None);continue
                weight=sum(w for _,w in vals)
                weighted.append(round(sum(vv*w for vv,w in vals)/weight,4) if weight>0 else round(sum(vv for vv,_ in vals)/len(vals),4))
            engagement=total_likes+total_comments+total_shares+total_saves
            out.append({
                "variant_id":int(v["id"]),"label":v.get("label") or "","status":v.get("status") or "",
                "result_rows":len(rows),"views":total_views,"likes":total_likes,"comments":total_comments,
                "shares":total_shares,"saves":total_saves,"watch_time_s":round(total_watch,4),
                "engagements":engagement,
                "engagement_rate_pct":round(100.0*engagement/total_views,4) if total_views>0 else None,
                "avg_view_duration_s":weighted[0],"retention_3s_pct":weighted[1],"completion_pct":weighted[2],
                "summary_model":"descriptive_v1","rank":None,"winner":None
            })
    return out

def validate_results_csv(experiment_id,csv_text,max_rows=200):
    import csv,io
    from datetime import datetime
    ensure_schema();eid=int(experiment_id);text=str(csv_text or "")
    if len(text)>131072:return {"ok":False,"errors":["CSV exceeds 128 KiB limit"],"rows":[],"row_count":0}
    allowed={"variant_id","observed_at","views","likes","comments","shares","saves","watch_time_s","avg_view_duration_s","retention_3s_pct","completion_pct","notes"}
    metric_cols=allowed-{"variant_id","observed_at","notes"}
    errors=[];normalized=[]
    try:
        reader=csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        headers=[str(x or "").strip() for x in (reader.fieldnames or [])]
        unknown=[h for h in headers if h not in allowed]
        if "variant_id" not in headers:errors.append("Missing required header: variant_id")
        if unknown:errors.append("Unknown headers: "+", ".join(sorted(unknown)))
        if not any(h in metric_cols for h in headers):errors.append("CSV must include at least one metric column")
        with db() as c:
            valid_ids={int(r["id"]) for r in c.execute("SELECT id FROM social_experiment_variants WHERE experiment_id=?",(eid,)).fetchall()}
        for n,row in enumerate(reader,start=2):
            if len(normalized)>=int(max_rows):errors.append(f"Row limit exceeded: {max_rows}");break
            if not any(str(v or "").strip() for v in row.values()):continue
            row_errors=[]
            try:vid=int(str(row.get("variant_id") or "").strip())
            except Exception:vid=None;row_errors.append("variant_id must be an integer")
            if vid is not None and vid not in valid_ids:row_errors.append("variant_id does not belong to this experiment")
            observed=str(row.get("observed_at") or "").strip() or None
            if observed:
                try:datetime.fromisoformat(observed.replace("Z","+00:00"))
                except Exception:row_errors.append("observed_at must be ISO-8601")
            out={"variant_id":vid,"observed_at":observed}
            for key in ("views","likes","comments","shares","saves"):
                raw=str(row.get(key) or "").strip()
                if not raw:out[key]=0;continue
                try:
                    val=int(raw)
                    if val<0:raise ValueError()
                    out[key]=val
                except Exception:row_errors.append(key+" must be a non-negative integer");out[key]=0
            for key in ("watch_time_s","avg_view_duration_s"):
                raw=str(row.get(key) or "").strip()
                if not raw:out[key]=0.0;continue
                try:
                    val=float(raw)
                    if val<0:raise ValueError()
                    out[key]=val
                except Exception:row_errors.append(key+" must be a non-negative number");out[key]=0.0
            for key in ("retention_3s_pct","completion_pct"):
                raw=str(row.get(key) or "").strip()
                if not raw:out[key]=None;continue
                try:
                    val=float(raw)
                    if val<0 or val>100:raise ValueError()
                    out[key]=val
                except Exception:row_errors.append(key+" must be between 0 and 100");out[key]=None
            out["notes"]=str(row.get("notes") or "")[:1000]
            if row_errors:errors.append("Row "+str(n)+": "+"; ".join(row_errors))
            else:normalized.append(out)
    except Exception as exc:
        errors.append("CSV parse error: "+str(exc)[:200])
    return {"ok":not errors and bool(normalized),"errors":errors,"rows":normalized[:int(max_rows)],"row_count":len(normalized),"max_rows":int(max_rows)}

def import_results_csv(experiment_id,csv_text,max_rows=200):
    preview=validate_results_csv(experiment_id,csv_text,max_rows=max_rows)
    if not preview["ok"]:raise ValueError("CSV validation failed: "+" | ".join(preview["errors"][:10]))
    imported=0;skipped=0
    for row in preview["rows"]:
        with db() as c:
            old=c.execute("""SELECT id FROM social_experiment_results
              WHERE variant_id=? AND source='import' AND COALESCE(observed_at,'')=COALESCE(?,'')
              AND views=? AND likes=? AND comments=? AND shares=? AND saves=?
              AND watch_time_s=? AND avg_view_duration_s=?
              AND COALESCE(retention_3s_pct,-1)=COALESCE(?,-1)
              AND COALESCE(completion_pct,-1)=COALESCE(?,-1) AND COALESCE(notes,'')=COALESCE(?,'')
              ORDER BY id DESC LIMIT 1""",
              (row["variant_id"],row["observed_at"],row["views"],row["likes"],row["comments"],row["shares"],row["saves"],row["watch_time_s"],row["avg_view_duration_s"],row["retention_3s_pct"],row["completion_pct"],row["notes"])).fetchone()
        if old:skipped+=1;continue
        record_result(row["variant_id"],"import",observed_at=row["observed_at"],views=row["views"],likes=row["likes"],comments=row["comments"],shares=row["shares"],saves=row["saves"],watch_time_s=row["watch_time_s"],avg_view_duration_s=row["avg_view_duration_s"],retention_3s_pct=row["retention_3s_pct"],completion_pct=row["completion_pct"],notes=row["notes"])
        imported+=1
    return {"validated_rows":preview["row_count"],"imported":imported,"skipped_duplicates":skipped,"automatic_ranking":False,"automatic_winner":False}

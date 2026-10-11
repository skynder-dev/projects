from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path

def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _row(con, table, ident):
    r=con.execute(f"SELECT * FROM {table} WHERE id=?",(int(ident),)).fetchone()
    return dict(r) if r else None

def main():
    from archivist.config import CONFIG_PATH,STAGING,ensure_dirs
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps({
      "config_version":3,
      "sources":[],
      "privacy":{"enabled":False},
      "analysis":{"technical_quality":False,"storyboard_frames":4,"ffmpeg_threads":1},
      "ingest":{"min_free_gb":0,"analyze_after_import":False,"keep_failed_partials":False}
    }),encoding="utf-8")
    from archivist.db import init_db,db,upsert_inventory,create_job,recover_jobs
    import archivist.service as service
    init_db()
    root=Path(os.environ["ARCHIVIST_HOME"])
    srcdir=root/"fixture_sources";srcdir.mkdir(parents=True,exist_ok=True)

    def add(source_key,name,data,expected_size=None,kind="removable"):
        path=srcdir/name
        path.write_bytes(data)
        st=path.stat()
        row={
          "source_key":source_key,"source_kind":kind,"source_id":"synthetic",
          "source_label":"Synthetic Fixture","path":str(path),"filename":name,
          "ext":path.suffix or ".bin","media_type":"video","mime_type":"application/octet-stream",
          "size_bytes":int(st.st_size if expected_size is None else expected_size),
          "mtime":st.st_mtime,"date_taken":None,"duration_ms":None,"width":None,"height":None
        }
        with db() as con:
            upsert_inventory(con,row);con.commit()
            rid=int(con.execute("SELECT id FROM inventory WHERE source_key=?",(source_key,)).fetchone()["id"])
        return rid,path

    result={}

    # source_key upsert is idempotent.
    inv_a,path_a=add("syn:idempotent","same.mp4",b"A"*1024)
    with db() as con:
        before=int(con.execute("SELECT COUNT(*) FROM inventory WHERE source_key='syn:idempotent'").fetchone()[0])
        st=path_a.stat()
        upsert_inventory(con,{
          "source_key":"syn:idempotent","source_kind":"removable","source_id":"synthetic",
          "source_label":"Synthetic Fixture","path":str(path_a),"filename":"same.mp4",
          "ext":".mp4","media_type":"video","mime_type":"video/mp4","size_bytes":st.st_size,
          "mtime":st.st_mtime,"date_taken":None,"duration_ms":None,"width":None,"height":None
        });con.commit()
        after=int(con.execute("SELECT COUNT(*) FROM inventory WHERE source_key='syn:idempotent'").fetchone()[0])
    result["source_key_upsert_idempotent"]=before==1 and after==1

    # Duplicate IDs in a durable job are de-duped.
    jid_dup=create_job("import",[inv_a,inv_a,inv_a],{"matrix":"duplicate_ids"})
    with db() as con:
        result["duplicate_job_ids_deduped"]=int(con.execute("SELECT COUNT(*) FROM job_items WHERE job_id=?",(jid_dup,)).fetchone()[0])==1

    # Same visible filename cannot alias because staging path includes inventory id.
    inv_b,path_b=add("syn:same-name-2","same.mp4",b"B"*1024)
    with db() as con:
        ra=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_a,)).fetchone())
        rb=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_b,)).fetchone())
    result["same_name_destinations_distinct"]=service._staging_dest(ra)!=service._staging_dest(rb)

    # Truncated source relative to catalog size must fail and remove .part.
    inv_t,path_t=add("syn:truncated","truncated.mp4",b"T"*1024,expected_size=2048)
    jid_t=create_job("import",[inv_t],{"matrix":"truncated"})
    with db() as con:
        item_t=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_t,)).fetchone()["id"])
        row_t=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_t,)).fetchone())
    dest_t=service._staging_dest(row_t); part_t=dest_t.with_suffix(dest_t.suffix+".part")
    truncated_failed=False
    try: service._ensure_imported(row_t,jid_t,item_t)
    except RuntimeError as exc: truncated_failed="Copy verification failed" in str(exc)
    with db() as con:
        st_t=con.execute("SELECT import_status FROM inventory WHERE id=?",(inv_t,)).fetchone()["import_status"]
        con.execute("UPDATE job_items SET status='error',phase='error',error='synthetic truncated' WHERE id=?",(item_t,));con.commit()
    result["truncated_copy_rejected"]=truncated_failed and st_t=="error"
    result["failed_partial_removed"]=not part_t.exists() and not dest_t.exists()

    # retry_failed must create a new job containing only failed items.
    old_queue=service.queue_job
    service.queue_job=lambda kind,ids,options=None:create_job(kind,ids,options)
    try:
        jid_retry=service.retry_failed(jid_t)
    finally:
        service.queue_job=old_queue
    with db() as con:
        retry_items=[int(r["inventory_id"]) for r in con.execute("SELECT inventory_id FROM job_items WHERE job_id=? ORDER BY seq",(jid_retry,)).fetchall()]
    result["retry_only_failed"]=jid_retry!=jid_t and retry_items==[inv_t]

    # A stale partial must be replaced by a clean successful transfer.
    inv_s,path_s=add("syn:stale-part","stale.mp4",b"S"*1536)
    jid_s=create_job("import",[inv_s],{"matrix":"stale_part"})
    with db() as con:
        item_s=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_s,)).fetchone()["id"])
        row_s=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_s,)).fetchone())
    dest_s=service._staging_dest(row_s);part_s=dest_s.with_suffix(dest_s.suffix+".part")
    part_s.parent.mkdir(parents=True,exist_ok=True);part_s.write_bytes(b"stale-garbage")
    got_s=service._ensure_imported(row_s,jid_s,item_s)
    result["stale_partial_replaced"]=got_s==dest_s and not part_s.exists() and dest_s.read_bytes()==path_s.read_bytes()

    # Duplicate preflight should identify equal-content same-size known asset without staging copy.
    inv_known,path_known=add("syn:known","known.mp4",b"DUPLICATE-CONTENT")
    known_sha=_sha(path_known)
    with db() as con:
        con.execute("UPDATE inventory SET sha256=?,staging_path=? WHERE id=?",(known_sha,str(path_known),inv_known));con.commit()
    inv_dup,path_dup=add("syn:dup-source","dup-source.mp4",b"DUPLICATE-CONTENT")
    with db() as con: row_dup=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_dup,)).fetchone())
    dup_id,dup_sha=service._preflight_duplicate(row_dup)
    result["duplicate_preflight_detected"]=dup_id==inv_known and dup_sha==known_sha and not service._staging_dest(row_dup).exists()

    # Crash recovery: generic job requeues; imported phase is preserved; cancel stays cancelled; convert is untouched.
    inv_r,path_r=add("syn:recover","recover.mp4",b"R"*512)
    jid_r=create_job("import",[inv_r],{"matrix":"recover"})
    with db() as con:
        item_r=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_r,)).fetchone()["id"])
        con.execute("UPDATE jobs SET status='running',stage='analyze',started_at='old',worker_pid=123 WHERE id=?",(jid_r,))
        con.execute("UPDATE job_items SET status='analyzing',phase='imported',started_at='old' WHERE id=?",(item_r,))
        con.commit()
    recover_jobs()
    with db() as con:
        jr=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid_r,)).fetchone())
        ir=dict(con.execute("SELECT * FROM job_items WHERE id=?",(item_r,)).fetchone())
    result["restart_requeues_generic"]=jr["status"]=="queued" and jr["worker_pid"] is None
    result["restart_preserves_imported_phase"]=ir["status"]=="queued" and ir["phase"]=="imported"

    jid_c=create_job("import",[inv_r],{"matrix":"cancel"})
    with db() as con:
        item_c=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_c,)).fetchone()["id"])
        con.execute("UPDATE jobs SET status='running',cancel_requested=1 WHERE id=?",(jid_c,))
        con.execute("UPDATE job_items SET status='running',phase='importing' WHERE id=?",(item_c,));con.commit()
    recover_jobs()
    with db() as con:
        jc=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid_c,)).fetchone())
        ic=dict(con.execute("SELECT * FROM job_items WHERE id=?",(item_c,)).fetchone())
    result["cancel_recovery_terminal"]=jc["status"]=="cancelled" and ic["status"]=="skipped" and ic["phase"]=="cancelled"

    jid_v=create_job("convert",[inv_r],{"matrix":"convert_owned"})
    with db() as con:
        con.execute("UPDATE jobs SET status='running',stage='convert',worker_pid=456 WHERE id=?",(jid_v,));con.commit()
    recover_jobs()
    with db() as con: jv=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid_v,)).fetchone())
    result["generic_recovery_leaves_convert_owned"]=jv["status"]=="running" and jv["stage"]=="convert" and jv["worker_pid"] is None

    # Wrong-content same-size staging is replaced from an available source.
    inv_p,path_p=add("syn:poison","poison.mp4",b"P"*2048)
    jid_p=create_job("import",[inv_p],{"matrix":"same_size_poison"})
    with db() as con:
        item_p=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_p,)).fetchone()["id"])
        row_p=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_p,)).fetchone())
    dest_p=service._staging_dest(row_p);dest_p.parent.mkdir(parents=True,exist_ok=True);dest_p.write_bytes(b"X"*2048)
    got_p=service._ensure_imported(row_p,jid_p,item_p)
    result["same_size_existing_staging_integrity_verified"]=_sha(got_p)==_sha(path_p) and got_p.read_bytes()==path_p.read_bytes()

    # Known inventory SHA authorizes reuse even if the removable source is gone.
    inv_k,path_k=add("syn:known-reuse","known-reuse.mp4",b"K"*2048)
    known_reuse_sha=_sha(path_k)
    jid_k=create_job("import",[inv_k],{"matrix":"known_sha_reuse"})
    with db() as con:
        item_k=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_k,)).fetchone()["id"])
        con.execute("UPDATE inventory SET sha256=? WHERE id=?",(known_reuse_sha,inv_k));con.commit()
        row_k=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_k,)).fetchone())
    dest_k=service._staging_dest(row_k);dest_k.parent.mkdir(parents=True,exist_ok=True);dest_k.write_bytes(path_k.read_bytes());path_k.unlink()
    got_k=service._ensure_imported(row_k,jid_k,item_k)
    result["known_sha_matching_staging_reused_without_source"]=got_k==dest_k and _sha(got_k)==known_reuse_sha

    # Unknown integrity with source available must recopy and persist source SHA.
    inv_u,path_u=add("syn:unknown-recopy","unknown-recopy.mp4",b"U"*1536)
    jid_u=create_job("import",[inv_u],{"matrix":"unknown_recopy"})
    with db() as con:
        item_u=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_u,)).fetchone()["id"])
        row_u=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_u,)).fetchone())
    dest_u=service._staging_dest(row_u);dest_u.parent.mkdir(parents=True,exist_ok=True);dest_u.write_bytes(b"Z"*1536)
    got_u=service._ensure_imported(row_u,jid_u,item_u)
    with db() as con: sha_u=con.execute("SELECT sha256 FROM inventory WHERE id=?",(inv_u,)).fetchone()["sha256"]
    result["unknown_integrity_staging_recopied_when_source_available"]=got_u.read_bytes()==path_u.read_bytes() and sha_u==_sha(path_u)

    # Unknown integrity with no source must fail closed.
    inv_f,path_f=add("syn:unknown-no-source","unknown-no-source.mp4",b"F"*1024)
    jid_f=create_job("import",[inv_f],{"matrix":"unknown_no_source"})
    with db() as con:
        item_f=int(con.execute("SELECT id FROM job_items WHERE job_id=?",(jid_f,)).fetchone()["id"])
        row_f=dict(con.execute("SELECT * FROM inventory WHERE id=?",(inv_f,)).fetchone())
    dest_f=service._staging_dest(row_f);dest_f.parent.mkdir(parents=True,exist_ok=True);dest_f.write_bytes(b"Y"*1024);path_f.unlink()
    failed_closed=False
    try:service._ensure_imported(row_f,jid_f,item_f)
    except RuntimeError as exc:failed_closed="source file is unavailable" in str(exc).lower()
    result["unknown_integrity_staging_fails_closed_without_source"]=failed_closed

    required=list(result)
    failed=[k for k in required if not result[k]]
    print(json.dumps({"result":result,"failed":failed,"pass":not failed},sort_keys=True))

if __name__=="__main__":
    main()

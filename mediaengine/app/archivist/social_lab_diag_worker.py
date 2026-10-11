from __future__ import annotations
import json
import sqlite3,sys,tempfile
from pathlib import Path
from .config import HOME,ensure_dirs
from .db import init_db
from .social_lab import evaluate_candidate,list_publications,record_publication
def main():
    ensure_dirs();init_db();a=HOME/"m10_a.mp4";b=HOME/"m10_b.mp4";c=HOME/"m10_c.mp4"
    a.write_bytes(b"archivist-m10-a");b.write_bytes(b"archivist-m10-b");c.write_bytes(b"archivist-m10-c")
    first=evaluate_candidate(output_path=a,source_clip_ids=[1,2,3],clip_sequence=[1,2,3],template_key="composer:9:16",caption_text="first")
    pid=record_publication(output_path=a,title="baseline",status="published",source_clip_ids=[1,2,3],clip_sequence=[1,2,3],template_key="composer:9:16",caption_text="first",novelty_state=first["state"])
    exact=evaluate_candidate(output_path=a,source_clip_ids=[1,2,3],clip_sequence=[1,2,3],template_key="composer:9:16",caption_text="first")
    similar=evaluate_candidate(output_path=b,source_clip_ids=[1,2,4],clip_sequence=[1,2,4],template_key="composer:9:16",caption_text="alternate")
    fresh=evaluate_candidate(output_path=c,source_clip_ids=[90,91],clip_sequence=[90,91],template_key="composer:16:9",caption_text="different")
    pubs=list_publications(10)
    assert pid>0 and len(pubs)==1 and exact["state"]=="exact_duplicate_block" and similar["state"] in ("similar_review","too_similar_block") and fresh["state"]=="new"
    print(json.dumps({"publication_count":len(pubs),"exact":exact["state"],"similar":similar["state"],"fresh":fresh["state"],"model":fresh["model"]},sort_keys=True))
from .social_lab import enqueue_candidate,set_queue_state,list_queue
def queue_contract():
    a=enqueue_candidate(title="fresh",novelty_state="new")
    b=enqueue_candidate(title="similar",novelty_state="similar_review")
    c=enqueue_candidate(title="duplicate",novelty_state="exact_duplicate_block")
    assert a["queue_state"]=="ready" and b["queue_state"]=="review" and c["queue_state"]=="hold"
    moved=set_queue_state(b["queue_id"],"ready");assert moved["queue_state"]=="ready"
    blocked=False
    try:set_queue_state(c["queue_id"],"ready")
    except ValueError:blocked=True
    assert blocked
    rows=list_queue(10);assert len(rows)==3
    return {"ready":a["queue_state"],"review_to_ready":moved["queue_state"],"duplicate":c["queue_state"],"hold_bypass_blocked":blocked,"queue_count":len(rows)}

def privacy_transition_contract():
    from . import social_lab as social
    from . import connectors as connectors
    with tempfile.TemporaryDirectory(prefix="archivist_priv150_") as td:
        con=sqlite3.connect(":memory:");con.row_factory=sqlite3.Row
        old_db=social.db;old_connectors_db=connectors.db;old_home=connectors.HOME
        social.db=lambda:con;connectors.db=lambda:con;connectors.HOME=Path(td)
        try:
            con.executescript("""CREATE TABLE inventory(
              id INTEGER PRIMARY KEY,excluded INTEGER NOT NULL DEFAULT 0,
              private_path TEXT,rejected_path TEXT,analysis_status TEXT
            );
            CREATE TABLE virtual_clips(id INTEGER PRIMARY KEY,inventory_id INTEGER);
            CREATE TABLE compositions(
              id INTEGER PRIMARY KEY,title TEXT,aspect TEXT,status TEXT,output_path TEXT,
              output_bytes INTEGER DEFAULT 0,updated_at TEXT
            );
            CREATE TABLE composition_items(composition_id INTEGER,position INTEGER,clip_id INTEGER);
            """)
            out=Path(td)/"composition.mp4";out.write_bytes(b"privacy-transition-fixture")
            con.execute("INSERT INTO inventory(id,excluded,analysis_status) VALUES(1,0,'safe')")
            con.execute("INSERT INTO virtual_clips(id,inventory_id) VALUES(10,1)")
            con.execute("INSERT INTO compositions(id,title,aspect,status,output_path,output_bytes,updated_at) VALUES(1,'fixture','9:16','finished',?,?,?)",(str(out),out.stat().st_size,'now'))
            con.execute("INSERT INTO composition_items(composition_id,position,clip_id) VALUES(1,1,10)")
            con.commit()

            public=social.candidate_from_composition(1)
            recent_public=any(int(x["id"])==1 for x in social.recent_rendered_compositions(10))
            q=social.enqueue_candidate(composition_id=1,title="fixture",novelty_state="new")
            handoff=connectors.create_manual_handoff(str(out),composition_id=1,novelty_state="new")

            con.execute("UPDATE inventory SET private_path='Private\\fixture.mp4' WHERE id=1");con.commit()
            def blocked(fn):
                try:fn();return False
                except ValueError:return True
            private_candidate=blocked(lambda:social.candidate_from_composition(1))
            private_recent=not any(int(x["id"])==1 for x in social.recent_rendered_compositions(10))
            private_enqueue=blocked(lambda:social.enqueue_candidate(composition_id=1,title="blocked",novelty_state="new"))
            private_record=blocked(lambda:social.record_publication(output_path=str(out),composition_id=1,novelty_state="new"))
            private_handoff=blocked(lambda:connectors.create_manual_handoff(str(out),composition_id=1,novelty_state="new"))

            con.execute("UPDATE inventory SET private_path=NULL,rejected_path='Rejected\\fixture.mp4' WHERE id=1");con.commit()
            rejected_candidate=blocked(lambda:social.candidate_from_composition(1))
            rejected_handoff=blocked(lambda:connectors.create_manual_handoff(str(out),composition_id=1,novelty_state="new"))

            result={
              "public_candidate":public["composition_id"]==1,
              "public_recent_visible":recent_public,
              "public_enqueue":q["queue_state"]=="ready",
              "public_manual_handoff":Path(handoff["manifest_path"]).exists(),
              "private_candidate_blocked":private_candidate,
              "private_recent_hidden":private_recent,
              "private_direct_enqueue_blocked":private_enqueue,
              "private_direct_record_blocked":private_record,
              "private_connector_handoff_blocked":private_handoff,
              "rejected_candidate_blocked":rejected_candidate,
              "rejected_connector_handoff_blocked":rejected_handoff,
              "historical_composition_preserved":con.execute("SELECT COUNT(*) FROM compositions WHERE id=1").fetchone()[0]==1,
              "historical_queue_preserved":con.execute("SELECT COUNT(*) FROM social_queue WHERE composition_id=1").fetchone()[0]>=1
            }
            if not all(result.values()):raise RuntimeError("PRIV-150 synthetic contract failed: "+json.dumps(result,sort_keys=True))
            return result
        finally:
            social.db=old_db;connectors.db=old_connectors_db;connectors.HOME=old_home;con.close()

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "main"
    if mode=="priv150":print(json.dumps(privacy_transition_contract(),sort_keys=True))
    else:main()

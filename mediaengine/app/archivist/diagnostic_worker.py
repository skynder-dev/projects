from __future__ import annotations

import json, sys, time
from pathlib import Path

from .config import CONFIG_PATH, ensure_dirs
from .db import db, init_db, now_iso, upsert_inventory
from .media_brain import ensure_schema, interpolate_crop_keyframes, save_crop_trajectory, trajectories_for_clip, trajectory_for_clip

def wait_job(jid,seconds=150):
    end=time.time()+seconds
    while time.time()<end:
        with db() as con: row=con.execute('select * from jobs where id=?',(jid,)).fetchone()
        if row and row['status'] in ('finished','failed','cancelled'): return dict(row)
        time.sleep(.2)
    raise RuntimeError(f'job {jid} timeout')

def main():
    fixture=Path(sys.argv[1]).resolve(); assert fixture.exists()
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps({'config_version':2,'sources':[],'privacy':{'enabled':False},'analysis':{'technical_quality':True,'storyboard_frames':8,'ffmpeg_threads':2},'ingest':{'min_free_gb':0,'analyze_after_import':True,'keep_rejected':True}}),encoding='utf-8')
    init_db();ensure_schema()
    local=fixture;st=local.stat()
    row={'source_key':'diag:'+str(local),'source_kind':'fixed','source_id':'diagnostic-source','source_label':'Remote Lab fixture','path':str(local),'filename':local.name,'ext':'.mp4','media_type':'video','mime_type':'video/mp4','size_bytes':st.st_size,'mtime':st.st_mtime,'duration_ms':3000,'width':640,'height':360}
    with db() as con:
        upsert_inventory(con,row);con.commit();inv=int(con.execute('select id from inventory where source_key=?',(row['source_key'],)).fetchone()['id']);con.execute('update inventory set work_selected=1 where id=?',(inv,));con.commit()
    from .service import queue_job,start_workers
    start_workers();jid=queue_job('import_analyze',[inv],{'analyze':True});j1=wait_job(jid)
    if j1['status']!='finished' or j1['failed']:
        raise RuntimeError('import_analyze failed: '+str(j1.get('error') or j1.get('message')))
    jid2=queue_job('media_brain',[inv],{'preset':'general'});j2=wait_job(jid2)
    if j2['status']!='finished' or j2['failed']:
        raise RuntimeError('media_brain failed: '+str(j2.get('error') or j2.get('message')))
    end=time.time()+30
    while time.time()<end:
        with db() as con:
            invr=dict(con.execute('select * from inventory where id=?',(inv,)).fetchone());clips=con.execute('select count(*) n from virtual_clips where inventory_id=?',(inv,)).fetchone()['n'];crops=con.execute('select count(*) n from crop_plans cp join virtual_clips vc on vc.id=cp.clip_id where vc.inventory_id=?',(inv,)).fetchone()['n'];aspects=[x['aspect'] for x in con.execute('select distinct cp.aspect from crop_plans cp join virtual_clips vc on vc.id=cp.clip_id where vc.inventory_id=? order by cp.aspect',(inv,)).fetchall()]
        if clips and crops: break
        time.sleep(.2)
    assert invr['work_selected']==1 and invr['sha256'] and invr['analysis_version']==4
    assert clips>=1 and crops>=4 and set(aspects)=={'16:9','4:5','1:1','9:16'}
    with db() as con: clip=dict(con.execute('select * from virtual_clips where inventory_id=? order by id limit 1',(inv,)).fetchone())
    trajectories=trajectories_for_clip(clip['id'])
    assert set(trajectories)=={'16:9','4:5','1:1','9:16'}
    for trajectory in trajectories.values():
        keys=trajectory['keyframes']; assert len(keys)>=2 and trajectory['source']=='tracking_v1'
        mid=interpolate_crop_keyframes(keys,(clip['end_ms']-clip['start_ms'])//2)
        assert 0<=mid['x']<=1-mid['w']+1e-6 and 0<=mid['y']<=1-mid['h']+1e-6
    chosen=trajectories['9:16']; keys=[dict(k) for k in chosen['keyframes']]
    manual=dict(interpolate_crop_keyframes(keys,min(777,clip['end_ms']-clip['start_ms'])));manual['time_ms']=min(777,clip['end_ms']-clip['start_ms']);manual['locked']=1;manual['confidence']=1
    keys=[k for k in keys if k['time_ms']!=manual['time_ms']]+[manual];keys.sort(key=lambda k:k['time_ms'])
    save_crop_trajectory(clip['id'],'9:16',keys,preset=chosen['preset'],status='approved',confidence=chosen['confidence'],source='diagnostic_manual_review')
    persisted=trajectory_for_clip(clip['id'],'9:16');assert persisted['status']=='approved' and any(k['locked'] for k in persisted['keyframes'])
    print(json.dumps({'import_job':'finished','analysis_status':invr['analysis_status'],'quality_status':invr['quality_status'],'hash_created':True,'analysis_version':invr['analysis_version'],'media_brain_job':'finished','virtual_clips':clips,'crop_plans':crops,'crop_trajectories':len(trajectories),'trajectory_keyframes':sum(len(t['keyframes']) for t in trajectories.values()),'trajectory_source':'tracking_v1','manual_review_status':'approved','locked_keyframe_persisted':True,'aspects':aspects}))

if __name__=='__main__': main()

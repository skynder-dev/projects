#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('q',HERE/'medeng_drop_queue_v40.py')
q=importlib.util.module_from_spec(spec); import sys; sys.modules[spec.name]=q; spec.loader.exec_module(q)
checks=[]
def ck(name, cond, detail=None):
    checks.append({'name':name,'pass':bool(cond),'detail':detail})
    if not cond: raise AssertionError(name+(': '+str(detail) if detail else ''))

def write_cfg(root,obj):
    p=root/'AUTO_EDIT.json'; p.write_text(json.dumps(obj),encoding='utf-8'); return p

with tempfile.TemporaryDirectory(prefix='v42_pacing_') as td:
    root=Path(td)
    # Defaults preserve legacy rendering identity.
    cfg,full,render=q.load_job_config(None,30,False)
    ck('default_clip_5',cfg['clip_seconds']==5.0,cfg)
    ck('default_transition_025',cfg['transition_seconds']==0.25,cfg)
    ck('default_render_identity_legacy_none',render is None,render)

    # Approval/retry policy changes never alter render identity.
    p1=write_cfg(root,{'schema_version':1,'target_seconds':30,'clip_seconds':5,'transition_seconds':0.25,'approval_mode':'manual','ready_mode':'settle','max_attempts':1,'retry_backoff_seconds':30})
    c1,h1,r1=q.load_job_config(p1,30,False)
    p2=write_cfg(root,{'schema_version':1,'target_seconds':30,'clip_seconds':5,'transition_seconds':0.25,'approval_mode':'auto','ready_mode':'marker','max_attempts':4,'retry_backoff_seconds':120})
    c2,h2,r2=q.load_job_config(p2,30,False)
    ck('policy_changes_full_hash',h1!=h2,(h1,h2))
    ck('policy_changes_do_not_render_hash',r1==r2==None,(r1,r2))

    # Non-default pacing has deterministic render identity and different pace => different identity.
    pf=write_cfg(root,{'schema_version':1,'target_seconds':30,'clip_seconds':3,'transition_seconds':0.15,'approval_mode':'auto'})
    cf,hf,rf=q.load_job_config(pf,30,False)
    pr=write_cfg(root,{'schema_version':1,'target_seconds':30,'clip_seconds':7,'transition_seconds':0.4})
    cr,hr,rr=q.load_job_config(pr,30,False)
    ck('fast_render_identity_present',isinstance(rf,str) and len(rf)==64,rf)
    ck('relaxed_render_identity_present',isinstance(rr,str) and len(rr)==64,rr)
    ck('different_pacing_different_render_identity',rf!=rr,(rf,rr))

    # Same fast pacing, different approval policy => same render identity.
    pf2=write_cfg(root,{'schema_version':1,'target_seconds':30,'clip_seconds':3,'transition_seconds':0.15,'approval_mode':'manual','max_attempts':3})
    cf2,hf2,rf2=q.load_job_config(pf2,30,False)
    ck('same_pacing_same_render_identity',rf==rf2,(rf,rf2))
    ck('same_pacing_policy_changes_full_hash',hf!=hf2,(hf,hf2))

    # Range failures are fail-closed.
    bad=[
      ({'schema_version':1,'clip_seconds':1.0},'AUTO_EDIT_JSON_CLIP_SECONDS_RANGE_1_5_12'),
      ({'schema_version':1,'clip_seconds':13.0},'AUTO_EDIT_JSON_CLIP_SECONDS_RANGE_1_5_12'),
      ({'schema_version':1,'clip_seconds':3.0,'transition_seconds':1.3},'AUTO_EDIT_JSON_TRANSITION_SECONDS_RANGE'),
      ({'schema_version':1,'clip_seconds':5.0,'transition_seconds':-0.1},'AUTO_EDIT_JSON_TRANSITION_SECONDS_RANGE'),
    ]
    for i,(obj,needle) in enumerate(bad,1):
        p=write_cfg(root,obj)
        try:q.load_job_config(p,30,False); ok=False; err='NO_ERROR'
        except Exception as e: ok=needle in str(e); err=str(e)
        ck(f'invalid_pacing_{i}_fails_closed',ok,err)

print(json.dumps({'candidate':'MEDENG_V42_PACING_CONTRACT_TEST','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2))

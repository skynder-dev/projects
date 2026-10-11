#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, sys, tempfile, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
q43=load('q43',HERE/'medeng_drop_queue_v40.py')
def v42_pacing_identity(clip_seconds, transition_seconds):
    render_policy={}
    if abs(float(clip_seconds)-5.0)>1e-9 or abs(float(transition_seconds)-0.25)>1e-9:
        render_policy.update({'clip_seconds':float(clip_seconds),'transition_seconds':float(transition_seconds)})
    if not render_policy:
        return None
    canonical=json.dumps(render_policy,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(canonical.encode()).hexdigest()
checks=[]
def ck(name,cond,detail=None):
    checks.append({'name':name,'pass':bool(cond),'detail':detail})
    if not cond: raise AssertionError(name+(': '+str(detail) if detail else ''))
def cfg(root,obj):
    p=root/'AUTO_EDIT.json';p.write_text(json.dumps(obj),encoding='utf-8');return p
with tempfile.TemporaryDirectory(prefix='v43_audio_') as td:
    r=Path(td)
    c,full,render=q43.load_job_config(None,30,False)
    ck('default_audio_lufs_-18',c['audio_lufs']==-18.0,c)
    ck('default_audio_tp_-2',c['audio_true_peak_db']==-2.0,c)
    ck('default_render_identity_none',render is None,render)
    # V42 compatibility for default pacing and non-default pacing.
    p=cfg(r,{'schema_version':1,'target_seconds':30,'clip_seconds':3,'transition_seconds':0.15,'approval_mode':'auto'})
    _,_,r43=q43.load_job_config(p,30,False);r42=v42_pacing_identity(3,0.15)
    ck('v42_fast_pacing_identity_compatible',r43==r42,(r43,r42))
    p=cfg(r,{'schema_version':1,'target_seconds':30,'clip_seconds':7,'transition_seconds':0.4,'approval_mode':'manual'})
    _,_,r43b=q43.load_job_config(p,30,False);r42b=v42_pacing_identity(7,0.4)
    ck('v42_relaxed_pacing_identity_compatible',r43b==r42b,(r43b,r42b))
    # Audio target is render identity.
    p=cfg(r,{'schema_version':1,'target_seconds':30,'audio_lufs':-16,'audio_true_peak_db':-1.5,'approval_mode':'manual'})
    c16,h16,a16=q43.load_job_config(p,30,False)
    p=cfg(r,{'schema_version':1,'target_seconds':30,'audio_lufs':-22,'audio_true_peak_db':-3,'approval_mode':'manual'})
    c22,h22,a22=q43.load_job_config(p,30,False)
    ck('audio_identity_present',isinstance(a16,str) and len(a16)==64,a16)
    ck('different_audio_different_render_identity',a16!=a22,(a16,a22))
    # Same audio render target, operational policy changes only full config hash.
    p=cfg(r,{'schema_version':1,'target_seconds':30,'audio_lufs':-16,'audio_true_peak_db':-1.5,'approval_mode':'auto','ready_mode':'marker','max_attempts':4,'retry_backoff_seconds':120})
    c16b,h16b,a16b=q43.load_job_config(p,30,False)
    ck('same_audio_same_render_identity',a16==a16b,(a16,a16b))
    ck('audio_policy_change_full_hash_only',h16!=h16b,(h16,h16b))
    # Pacing + audio both participate deterministically.
    p=cfg(r,{'schema_version':1,'target_seconds':30,'clip_seconds':3,'transition_seconds':0.15,'audio_lufs':-16,'audio_true_peak_db':-1.5})
    _,_,combo=q43.load_job_config(p,30,False)
    ck('combined_render_identity_differs_from_pacing_only',combo!=r42,(combo,r42))
    ck('combined_render_identity_differs_from_audio_only',combo!=a16,(combo,a16))
    # Fail closed ranges.
    bad=[
      ({'schema_version':1,'audio_lufs':-25},'AUTO_EDIT_JSON_AUDIO_LUFS_RANGE_-24_-12'),
      ({'schema_version':1,'audio_lufs':-11},'AUTO_EDIT_JSON_AUDIO_LUFS_RANGE_-24_-12'),
      ({'schema_version':1,'audio_true_peak_db':-7},'AUTO_EDIT_JSON_AUDIO_TRUE_PEAK_DB_RANGE_-6_-1'),
      ({'schema_version':1,'audio_true_peak_db':-0.5},'AUTO_EDIT_JSON_AUDIO_TRUE_PEAK_DB_RANGE_-6_-1'),
    ]
    for i,(obj,needle) in enumerate(bad,1):
        p=cfg(r,obj)
        try:q43.load_job_config(p,30,False);ok=False;err='NO_ERROR'
        except Exception as e:ok=needle in str(e);err=str(e)
        ck(f'invalid_audio_{i}_fails_closed',ok,err)
print(json.dumps({'candidate':'MEDENG_V43_AUDIO_TARGET_CONTRACT','passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},indent=2))

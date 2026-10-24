"""Fixed source-only launcher with serialized, process-bound launch receipts."""
from pathlib import Path
import os,subprocess,sys,uuid
from socialreel.common import PipelineError,write_json,read_json
PYTHON=Path(r'CI_UNCONFIGURED/runtime-0')

def launch(store,job_id):
 store.folder(job_id)
 from socialreel.motion_state import motion_lock
 from socialreel.jobs import process_token
 with motion_lock(store.root,'cpu_launch_'+job_id,wait=3):
  job=store.get(job_id)
  if job['state']!='queued':return {'state':'existing_job','worker_started':False}
  receipt_path=store.folder(job_id)/'cpu_launcher.json'
  if receipt_path.exists():
   try:receipt=read_json(receipt_path)
   except (OSError,ValueError):raise PipelineError('Preparation launch receipt unreadable; no duplicate worker started')
   if not isinstance(receipt,dict):raise PipelineError('Preparation launch receipt malformed; no duplicate worker started')
   pid=receipt.get('pid');token=receipt.get('process_token')
   if type(pid) is not int or pid<=0:raise PipelineError('Preparation launch outcome unknown; cancel this queued attempt before an explicit retry')
   current=process_token(pid)
   if current is not None:
    if current=='unknown' or not token or current!=token:raise PipelineError('Preparation process identity uncertain; no duplicate worker started')
    return {'state':'existing_worker','worker_started':False,'pid':pid}
  if not PYTHON.is_file():raise PipelineError('Configured Social CPU Python unavailable; queued job preserved')
  from socialreel.local_editorial import authorized
  cfg=read_json(store.folder(job_id)/'config.json')
  if cfg.get('writer')!='template' and not authorized(cfg):raise PipelineError('Preparation writer is not authorized')
  from socialreel.common import ROOT
  code="import sys;sys.path.insert(0,sys.argv[1]);from socialreel.jobs import JobStore;s=JobStore(sys.argv[2]);j=s.get(sys.argv[3]);assert j['state']=='queued';s.work_once(sys.argv[3])"
  env=dict(os.environ,SOCIAL_CACHE_ONLY='1',SOCIAL_MODEL_IMPORT_AUDIT_FILE=str(store.folder(job_id)/'model_guard.json'),PYTHONUNBUFFERED='1',PYTHONIOENCODING='utf-8')
  for key in ['ANTHROPIC_API_KEY','OPENAI_API_KEY']:env.pop(key,None)
  intent={'state':'launch_intent','intent_id':uuid.uuid4().hex,'stop_after':'script','writer':cfg.get('writer'),'models_allowed':False,'editorial_runtime_allowed':authorized(cfg)}
  # Journal before spawning: a crash/uncertain outcome cannot silently spawn again.
  write_json(receipt_path,intent)
  with (store.folder(job_id)/'cpu_launcher.log').open('ab') as log:
   child=subprocess.Popen([str(PYTHON),'-c',code,str(ROOT),str(store.root),job_id],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=0x08000000)
  token=process_token(child.pid)
  write_json(receipt_path,{**intent,'pid':child.pid,'process_token':token,'state':'prepare_worker_requested'})
  return {'state':'prepare_worker_requested','worker_started':True,'pid':child.pid}

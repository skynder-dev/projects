"""Run an explicit prepared VACE micro-job in its own hidden native worker.

Invoked with the existing ComfyUI interpreter, which already includes aiohttp.
No model installation, auto-download, foreign queue mutation or identity approval.
"""
import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .common import HIDDEN_PROCESS, PipelineError, read_json, write_json, sha256_file
from .replacement import VACE_HOME


async def _execute_unlocked(directory, cancel_file=None):
    import aiohttp
    root = VACE_HOME.resolve()
    directory = Path(directory).resolve()
    if not directory.is_relative_to(root/'input'):
        raise PipelineError('Prepared input outside isolated VACE folder')
    from .replacement import validate_prepared
    validate_prepared(directory)
    plan = read_json(directory/'prepared.json')
    if plan.get('production_approved') or plan.get('identity_approved'):
        raise PipelineError('Experimental runner cannot confer production or presenter approval')
    for entry in plan['files']:
        path = (directory/entry['path']).resolve()
        if not path.is_relative_to(directory) or sha256_file(path) != entry['sha256']:
            raise PipelineError('Prepared input changed; prepare again before submission')
    graph = read_json(directory/'workflow_api.json')
    sample = graph['16']['inputs']
    if sample['steps'] != 20 or sample['sampler_name'] != 'uni_pc' or plan['frames'] != 17:
        raise PipelineError('Job exceeds tested micro-job contract')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8190)) == 0:
            raise PipelineError('VACE port already occupied; existing listener is not touched')
    async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=5)) as session:
        try:
            for port in (8188,8189):
                async with session.get(f'http://127.0.0.1:{port}/queue') as response:
                    queue = await response.json()
                if queue['queue_running'] or queue['queue_pending']:
                    raise PipelineError('Shared ComfyUI queue busy; no submission or eviction')
            async with session.get('http://127.0.0.1:11434/api/ps') as response:
                if any(model.get('size_vram',0) for model in (await response.json()).get('models',[])):
                    raise PipelineError('Shared Ollama GPU runner busy')
        except (aiohttp.ClientError,asyncio.TimeoutError) as error:
            raise PipelineError('Local GPU preflight service unavailable; own worker not started. Safe retry after service recovery.') from error
    free = int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True,**HIDDEN_PROCESS).splitlines()[0])
    if free < 7000:
        raise PipelineError('Insufficient free VRAM; no foreign models are unloaded')
    run_id = 'social_'+uuid.uuid4().hex
    output = root/'output'/run_id
    output.mkdir()
    stderr = root/'logs'/(run_id+'.stderr.log')
    stdout = root/'logs'/(run_id+'.stdout.log')
    record = {'status':'starting','prepared':str(directory),'test_scope':'experimental registered template only',
              'production_approved':False,'identity_approved':False,'progress':[]}
    def save(): write_json(output/'report.json',record)
    env = dict(os.environ,HF_HOME=str(root/'cache/huggingface'),TORCH_HOME=str(root/'cache/torch'),
               TEMP=str(root/'temp'),TMP=str(root/'temp'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    with stdout.open('wb') as standard_out, stderr.open('wb') as standard_err:
        worker = subprocess.Popen([sys.executable,'-s',str(root/'scripts/worker.py')],
                                  stdout=standard_out,stderr=standard_err,env=env,**HIDDEN_PROCESS)
        record['own_worker_pid']=worker.pid;save()
        pid = None
        try:
            started = time.monotonic();ready_limit=started+120
            async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=5)) as session:
                while time.monotonic() < ready_limit:
                    if worker.poll() is not None:
                        raise PipelineError('Own VACE worker exited during startup')
                    try:
                        async with session.get('http://127.0.0.1:8190/object_info',timeout=aiohttp.ClientTimeout(total=2)) as response:
                            info = await response.json()
                        if 'WanVaceToVideo' in info:
                            break
                    except (aiohttp.ClientError,asyncio.TimeoutError):
                        pass
                    await asyncio.sleep(.5)
                else:
                    raise PipelineError('Own VACE worker startup timeout')
                client=run_id;sampling=None;last_report=0;interrupted=False
                async with session.ws_connect('http://127.0.0.1:8190/ws?clientId='+client) as ws:
                    submitted=time.monotonic()
                    async with session.post('http://127.0.0.1:8190/prompt',json={'prompt':graph,'client_id':client}) as response:
                        reply=await response.json()
                    if 'prompt_id' not in reply:
                        raise PipelineError('Native workflow validation rejected the job')
                    pid=reply['prompt_id'];record.update(status='running',prompt_id=pid,api_submission_passed=True);save()
                    while time.monotonic()-submitted < 600:
                        try:
                            message=await asyncio.wait_for(ws.receive(),timeout=1)
                            if message.type == aiohttp.WSMsgType.TEXT:
                                event=json.loads(message.data);data=event.get('data',{})
                                if data.get('prompt_id') in (None,pid):
                                    if event['type']=='progress':
                                        record['progress'].append({'value':data['value'],'max':data['max'],'elapsed':round(time.monotonic()-submitted,3)});save()
                                    if event['type'] in ('execution_error','execution_interrupted'):
                                        record['status']=event['type'];save();return record
                        except asyncio.TimeoutError:
                            pass
                        text=stderr.read_text(errors='replace')
                        if sampling is None and re.search(r'0%\|.*?0/20',text):
                            sampling=time.monotonic();record['pre_sampling_seconds']=round(sampling-submitted,3)
                        cancelled=bool(cancel_file and Path(cancel_file).is_file())
                        elapsed=time.monotonic()-sampling if sampling else 0
                        value=record['progress'][-1]['value'] if record['progress'] else 0
                        forecast=elapsed*20/max(value,1)
                        if not interrupted and (cancelled or elapsed>=300 or (value>=2 and forecast>300)):
                            async with session.post('http://127.0.0.1:8190/interrupt',json={'prompt_id':pid}) as response:
                                record['interrupt_http']=response.status
                            interrupted=True;record['interrupt_reason']='cancelled' if cancelled else 'sampling budget/forecast';save()
                        if time.monotonic()-last_report >=30:
                            record['sampling_elapsed_seconds']=round(elapsed,3);record['sampling_forecast_seconds']=round(forecast,3);save();last_report=time.monotonic()
                            print(json.dumps({'status':record['status'],'sampling_seconds':round(elapsed)}),flush=True)
                        async with session.get('http://127.0.0.1:8190/history/'+pid) as response:
                            history=(await response.json()).get(pid)
                        if history:
                            if history.get('status',{}).get('status_str')!='success':
                                record['status']='failed';save();return record
                            record['history']=history
                            from .replacement import composite_output
                            result=composite_output(directory,history,output)
                            matches=re.findall(r'100%\|[^\n]*?20/20 \[(\d+):(\d+)',text)
                            record.update(result,status='technical_completed_review_required',
                                          total_seconds=round(time.monotonic()-started,3),
                                          sampling_seconds_tqdm=int(matches[-1][0])*60+int(matches[-1][1]) if matches else None)
                            save();return record
                    async with session.post('http://127.0.0.1:8190/interrupt',json={'prompt_id':pid}) as response:
                        record['interrupt_http']=response.status
                    record['status']='own_job_timeout';save();return record
        except Exception as error:
            record.update(status='failed',error_type=type(error).__name__,error=str(error)[:400]);save();raise
        finally:
            # Only the Popen object created here; never scan/kill another service.
            if worker.poll() is None:
                worker.terminate()
                try: worker.wait(timeout=10)
                except subprocess.TimeoutExpired: worker.kill();worker.wait(timeout=10)
            record['own_worker_stopped']=True;save()




async def execute(directory,cancel_file=None):
    from .motion_state import motion_lock
    with motion_lock(VACE_HOME,'prepare'):return await _execute_unlocked(directory,cancel_file)


if __name__ == '__main__':
    try:
        result=asyncio.run(execute(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None))
    except PipelineError as error:
        print(json.dumps({'status':'failed','error':str(error)}))
        raise SystemExit(2)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='technical_completed_review_required' else 2)

"""Persist model-free work at the existing pipeline boundary, without fake finished media."""
from pathlib import Path
from .common import read_json,write_json,sha256_file,sha256_bytes,utc_now,PipelineError

def save_preparation(tmp,out_root,run_id,rec,script,cfg,log,history_path,allow_repeat=False):
    from .voice import speech_text, speech_for_script
    information=bool(rec.get('public_money_source'))
    source_review=log.get('mode')=='live' and (log.get('nofo_check') or {}).get('checked') is True
    blockers=[] if source_review else [(log.get('nofo_check') or {}).get('reason') or 'Full official announcement review unavailable; listing facts alone do not confirm full conditions']
    if information and not source_review:blockers=['Public information content has not undergone an accepted actual live ingest']
    tasks=[{'id':'source_review','kind':'official_information_page_review' if information else 'official_full_announcement_review','state':'completed' if source_review else 'blocked',
            'depends_on':[],'evidence':log.get('nofo_check'),'blockers':list(blockers)}]
    dependency_review=(log.get('nofo_check') or {}).get('source_dependencies')
    if dependency_review:
        tasks.append({'id':'linked_policy_review','kind':'hash_bound_source_dependency_review','state':'completed' if dependency_review['overview_source_review_complete'] else 'blocked','depends_on':[],'evidence':dependency_review})
        tasks[0]['depends_on'].append('linked_policy_review')
    hold=cfg.get('generation_hold')
    if hold:
        blockers.append(hold);tasks.append({'id':'execution_authorization','kind':'explicit_operator_generation_hold','state':'blocked','depends_on':[],'blockers':[hold]})
    from .duration_preflight import assess as assess_duration
    duration=assess_duration(script,cfg['voice'])
    write_json(tmp/'duration_preflight.json',duration)
    tasks.append({'id':'duration_preflight','kind':'calibrated_pre_voice_duration_budget','state':'completed' if duration['pass'] else 'blocked','depends_on':[],'evidence':duration})
    if not duration['pass']:blockers.append(duration['reason'])
    from .source_quality import assess as assess_editorial,inspect_observation
    quality=assess_editorial(rec,script,read_json(tmp/'claims.json')['claims'],read_json(tmp/'storyboard.json'),cfg,source_observation=inspect_observation(tmp,rec))
    write_json(tmp/'source_quality.json',quality)
    blockers.extend(quality['generation_blockers'])
    source_gate=log.get('pre_voice_source_gate') or {'pass':False,'errors':['Production source freshness/deadline check not available']}
    blockers.extend(source_gate.get('errors') or ([] if source_gate.get('pass') else ['Production source readiness not confirmed']))
    tasks.append({'id':'source_currency','kind':'production_source_currency','state':'completed' if source_gate.get('pass') else 'blocked','depends_on':['source_review'],'evidence':source_gate})
    generation_ready=source_review and source_gate.get('pass') is True and not hold and duration['pass'] and quality['ready_for_generation']
    for index,segment in enumerate(script['segments'],1):
        tasks.append({'id':'voice_'+segment['id'],'kind':'tts','state':'not_started' if generation_ready else 'blocked',
                      'segment_id':segment['id'],'text':speech_for_script(script,segment['voiceover']),
                      'output':'audio/segment_%02d.wav'%index,'depends_on':['source_review','source_currency','duration_preflight']+(['execution_authorization'] if hold else []),
                      'settings':cfg['voice']})
        tasks.append({'id':'still_'+segment['id'],'kind':'native_social_still','state':'not_started',
                      'segment_id':segment['id'],'script_file':'script.json','depends_on':[],
                      'output':'mediaengine_handoff/stills/segment_%02d.png'%index})
    voices=[t['id'] for t in tasks if t['kind']=='tts'];stills=[t['id'] for t in tasks if t['kind']=='native_social_still']
    tasks.extend([
        {'id':'narration','kind':'assemble_measured_audio','depends_on':voices,'output':'audio/narration.wav'},
        {'id':'timing','kind':'measure_timing','depends_on':['narration'],'output':'timing.json'},
        {'id':'captions','kind':'offline_asr_and_captions','depends_on':['timing'],'outputs':['asr.json','subtitles.srt','subtitles.vtt']},
        {'id':'render','kind':'existing_social_renderer','depends_on':stills+['captions'],'output':'final/reel.mp4'},
        {'id':'verify','kind':'actual_media_verification','depends_on':['render']},
        {'id':'export','kind':'verified_package_and_current_source_check','depends_on':['verify']}])
    for task in tasks:task.setdefault('state','not_started')
    if script.get('editorial_contract')=='SOCIAL_BENEFIT_REEL_V1':
        tasks=[t for t in tasks if t['kind'] not in {'native_social_still','existing_social_renderer'}]
        tasks=[t for t in tasks if t['id'] not in {'render','verify','export'}]
        tasks.append({'id':'assembly_handoff','kind':'versioned_source_package_for_existing_assembler','state':'blocked','depends_on':['captions'],'blockers':['Assembly adapter not verified; no render or transport is implied']})
    write_json(tmp/'production_plan.json',{'schema':'SOCIAL_PREPARATION_V1','opportunity_id':rec['opportunity_id'],
        'tasks':tasks,'timing':None,'timing_reason':'Must be measured from actual WAV, never guessed',
        'source_review_note':log.get('nofo_check'),'model_execution_started':False,'model_execution_scope':'media generation only; editorial inference recorded separately','editorial_inference':log['writer'].get('local_editorial'),'ready_for_generation':generation_ready,'generation_blockers':blockers,
        'ready_for_publication':False,'accepted':False,'writer':log['writer']})
    if script.get('editorial_contract')=='SOCIAL_BENEFIT_REEL_V1':
        from .editorial_brief import assembly_contract
        package=assembly_contract(script,read_json(tmp/'storyboard.json'))
        package['source_quality']=quality
        package['inputs']={key:{'path':name,'sha256':sha256_file(tmp/name)} for key,name in {'script':'script.json','claims':'claims.json','storyboard':'storyboard.json','description':'description.md','source_quality':'source_quality.json'}.items()}
        write_json(tmp/'assembly-input.json',package)
    write_json(tmp/'preparation_config.json',cfg)
    if log.get('source_materialization'):
        derivation={**log['source_materialization'],'script_sha256':sha256_file(tmp/'script.json'),'claims_sha256':sha256_file(tmp/'claims.json'),'storyboard_sha256':sha256_file(tmp/'storyboard.json')}
        write_json(tmp/'source_materialization.json',derivation)
    files=[{'path':p.relative_to(tmp).as_posix(),'bytes':p.stat().st_size,'sha256':sha256_file(p)}
           for p in sorted(tmp.rglob('*')) if p.is_file()]
    identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in files).encode())
    write_json(tmp/'prepared.json',{'schema':'SOCIAL_PREPARATION_V1','state':'prepared_awaiting_generation',
        'accepted':False,'mode':log['mode'],'opportunity_id':rec['opportunity_id'],
        'preparation_id':identity,'files':files,'prepared_at':utc_now().isoformat(),
        'writer':log['writer'],'resumed_from_preparation_id':log.get('original_preparation_id'),'source_inputs_reused':log.get('source_inputs_reused',False),'model_execution_started':False,'model_execution_scope':'media generation only; editorial inference recorded separately','editorial_inference':log['writer'].get('local_editorial'),'ready_for_generation':generation_ready,'generation_blockers':blockers})
    destination=Path(out_root)/('prepared_'+run_id+'_'+identity[:12])
    from .preparation_history import publish_preparation
    entry={'opportunity_id':rec['opportunity_id'],'title':rec['title'],
           'preparation_id':identity,'directory':str(destination.resolve()),'state':'prepared_awaiting_generation'}
    publish_preparation(tmp,destination,history_path,entry,allow_repeat=allow_repeat)
    return destination


def verify_preparation(directory):
    root=Path(directory).resolve();manifest=read_json(root/'prepared.json')
    if manifest.get('schema')!='SOCIAL_PREPARATION_V1' or manifest.get('accepted') is not False or manifest.get('model_execution_started') is not False:
        raise PipelineError('Unknown or incorrectly accepted preparation')
    files=manifest.get('files') or []
    from .draft_check import entry_errors
    errors=entry_errors(files)
    if errors:raise PipelineError('; '.join(errors))
    required={'sources.json','topic.json','claims.json','script.json','storyboard.json','preparation_config.json','production_plan.json'}
    if not required.issubset({e['path'] for e in files}):raise PipelineError('Preparation missing required stage inputs')
    for entry in files:
        path=(root/entry['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size!=entry['bytes'] or sha256_file(path)!=entry['sha256']:
            raise PipelineError('Preparation input changed or unsafe: '+entry['path'])
    identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in files).encode())
    if identity!=manifest['preparation_id']:raise PipelineError('Preparation identity mismatch')
    if (root/'source/dependencies/dependency_graph.json').is_file():
        graph=read_json(root/'source/dependencies/dependency_graph.json')
        declared={e['path'] for e in files}
        for document in graph.get('documents',{}).values():
            for field in ('file','text_file'):
                if 'source/dependencies/'+str(document.get(field,'')) not in declared:raise PipelineError('Dependency bytes not declared in draft manifest')
        from .source_dependencies import verify
        result=verify(root/'source/dependencies',graph)
        if result.get('integrity_pass') is not True:raise PipelineError('Linked source integrity unconfirmed')
    if manifest.get('mode')=='source_only_fact_materialization':
        from .source_materialization import verify_materialization
        verify_materialization(root)
    return manifest

"""Common field contract and explicit writer-route provenance. Never execution approval."""
import hashlib,json
if __package__:from .narrative_checks import has_spoken_content,screen_field
else:from narrative_checks import has_spoken_content,screen_field
VERSION='SOCIAL_WRITER_FIELDS_V1'
PRODUCT='product_two_candidate_editorial_v211'
EXPERIMENT='experiment_single_narrative_v233'

def route(config=None,*,experiment=False):
    if experiment:return {'contract':VERSION,'route_id':EXPERIMENT,'source':'explicit_experiment_compiler','product_UI_connected':False,'configured_editorial_inference_allowed':False,'execution_evidence':'not_in_route_descriptor','quality_verified':False}
    if not isinstance(config,dict):return {'contract':VERSION,'route_id':'historical_route_unreported','source':'no_pinned_config','configured_editorial_inference_allowed':False,'execution_evidence':'not_in_route_descriptor','quality_verified':False}
    writer=config.get('writer','auto');policy=config.get('local_editorial') or {}
    enabled=writer=='ollama' and isinstance(policy,dict) and policy.get('enabled') is True and policy.get('execution_authorized') is True and not config.get('generation_hold') and not (config.get('llm') or {}).get('allow_spend')
    return {'contract':VERSION,'route_id':PRODUCT if writer=='ollama' else 'deterministic_source_bound' if writer in {'auto','template'} else 'unsupported_writer','source':'pinned_config_only_not_execution','requested_writer':writer,'configured_editorial_inference_allowed':enabled,'execution_evidence':'not_in_route_descriptor','quality_verified':False}

def fields(voices,screens):
    """Only common presence/staging checks; evidence and duration stay profile-specific."""
    shape_valid=isinstance(voices,list) and isinstance(screens,list)
    actual_voices=voices if isinstance(voices,list) else [None]
    actual_screens=screens if isinstance(screens,list) else [None]
    voice_rows=[{'index':i,'spoken_content_present':has_spoken_content(v)} for i,v in enumerate(actual_voices)]
    screen_rows=[{'index':i,'field':s.get('field','text') if isinstance(s,dict) else 'invalid','visible_text':screen_field(s.get('text'),s.get('layout_note')) if isinstance(s,dict) else screen_field(None)} for i,s in enumerate(actual_screens)]
    payload={'voices':voices,'screens':screens}
    try:digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    except (TypeError,ValueError):digest=None;shape_valid=False
    return {'contract':VERSION,'input_sha256':digest,'common_fields_valid':shape_valid and bool(voice_rows) and all(r['spoken_content_present'] for r in voice_rows) and all(r['visible_text']['preparation_valid'] for r in screen_rows),'voices':voice_rows,'screens':screen_rows,'evidence_coverage_verified':False,'semantic_entailment_verified':False,'quality_verified':False,'production_ready':False}

def script_fields(script):
    voices=[];screens=[]
    for i,scene in enumerate(script.get('segments') or []):
        voices.append(scene.get('voiceover'))
        for field in ('kicker','big','headline','sub'):
            value=(scene.get('on_screen') or {}).get(field)
            if value is not None and value!='':screens.append({'text':value,'field':str(i)+'.'+field})
    return fields(voices,screens)

"""Exact local ASR input lineage, computed before and checked after inference."""
from pathlib import Path
from .common import PipelineError,sha256_file,sha256_bytes,stable_json


def audio_inputs(narration,speech,timing,package,cfg=None):
    root=Path(package).resolve()
    def entry(path):
        path=Path(path).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise PipelineError('ASR audio outside owned input package or missing')
        return {'file':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha256_file(path)}
    result={'schema':'SOCIAL_ASR_INPUTS_V1','narration':entry(narration),
            'segments':[{'id':span['id'],**entry(root/span['audio'])} for span in timing],
            'expected_speech_sha256':sha256_bytes(stable_json(list(speech)).encode()),
            'timing_sha256':sha256_bytes(stable_json(list(timing)).encode()),
            'script_sha256':sha256_file(root/'script.json')}
    if cfg is not None:
        model=Path(cfg['model_dir'])/'model.bin'
        if not model.is_file():raise PipelineError('Local ASR model missing before inference')
        result['model']={'sha256':sha256_file(model),'bytes':model.stat().st_size,'device':'cpu','compute_type':'int8','cpu_threads':int(cfg.get('cpu_threads',4))}
    return result


def verify_audio_inputs(report,narration,speech,timing,package,cfg=None):
    saved=report.get('input_lineage')
    if not isinstance(saved,dict):raise PipelineError('ASR input lineage absent; old report is not an identity-verified cache')
    if saved.get('schema')=='SOCIAL_ASR_DERIVED_AUDIO_V1':
        from .derived_audio import verify
        return verify(report,narration,speech,timing,package)
    actual=audio_inputs(narration,speech,timing,package,cfg)
    if any(saved.get(key)!=value for key,value in actual.items()):raise PipelineError('ASR WAV/text/timing/model input changed; report reuse refused')
    return True

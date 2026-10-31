"""Explicit finite catalog intent; no keyword, model or source-language inference."""
from .common import PipelineError
TOPICS=('energy','wages','unclaimed')
def requested(cfg):
    selection=cfg.get('selection') or {}
    if 'public_reference_topic' not in selection:return None
    value=selection['public_reference_topic']
    if not isinstance(value,str) or value not in TOPICS:
        raise PipelineError('Unsupported explicit public_reference_topic; supported: energy, wages, unclaimed; no substitute source')
    return value

def validate_record(cfg,record):
    intent=requested(cfg)
    saved=record.get('public_reference_topic')
    if intent is None:intent=saved
    if intent is None:return None
    if intent not in TOPICS or saved is not None and saved!=intent:
        raise PipelineError('Explicit topic intent differs from saved research topic; no substitute')
    if (record.get('public_money_source') or {}).get('kind')!=intent:
        raise PipelineError('Research source kind differs from explicit topic intent; no concept request')
    return intent

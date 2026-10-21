"""Local Social configuration and read-only readiness checks; no model downloads."""
import importlib.metadata
import os
import shutil
from pathlib import Path

from .common import ROOT, AI_HOME, PipelineError, read_json, sha256_file,resolve_tool,RUNTIME_PATHS,RUNTIME_PATHS_ERROR


def load_config(path=None):
    path = Path(path or ROOT / 'config.json')
    cfg = read_json(path)
    local = ROOT / 'config.ai-local.json'
    if path.resolve() == (ROOT / 'config.json').resolve() and local.is_file():
        settings = read_json(local)
        # A missing selected model is an error, never permission to silently
        # switch to a different/default voice. Preserve the explicit selection.
        for key in ('voice', 'asr', 'writer', 'ollama', 'selection', 'llm', 'generation_hold', 'local_editorial'):
            if key in settings:
                if isinstance(settings[key],dict) and isinstance(cfg.get(key),dict):cfg[key]={**cfg[key],**settings[key]}
                else:cfg[key]=settings[key]
    return cfg


def validate_config(cfg,require_models=True):
    policy=cfg.get('local_editorial',{})
    if not isinstance(policy,dict) or any(type(policy.get(k,False)) is not bool for k in ['enabled','execution_authorized','cache_only']):raise PipelineError('Local editorial policy needs explicit boolean flags')
    hold=cfg.get('generation_hold')
    if hold is not None and (not isinstance(hold,str) or not hold.strip() or len(hold)>500):raise PipelineError('Generation hold must be a nonempty reason of at most 500 characters')
    if cfg.get('llm', {}).get('allow_spend'):
        raise PipelineError('Paid providers are not authorized for this local Social route')
    if cfg.get('writer', 'auto') not in {'auto', 'template', 'ollama'}:
        raise PipelineError('Local route requires writer auto, template or ollama')
    if cfg.get('voice', {}).get('backend') not in {'kokoro', 'piper', 'espeak', 'silent_test'}:
        raise PipelineError('Unknown voice backend')
    model = Path(cfg.get('asr', {}).get('model_dir', ''))
    if require_models and not (model / 'model.bin').is_file():
        raise PipelineError('Required offline ASR model is missing; no unverified narration or runtime download')
    if cfg.get('selection',{}).get('audience','general_us') not in {'general_us','small_business','institutional'}:raise PipelineError('Unknown target audience; choose a supported audience profile')
    if type(cfg.get('preparation_refresh_source',False)) is not bool:raise PipelineError('Pinned source refresh setting must be boolean')
    search = cfg.get('search', {})
    if not isinstance(search.get('keywords'), list) or not search['keywords']:
        raise PipelineError('Automatic topic discovery needs configured topics')
    if any(not isinstance(term,str) or not term.strip() or len(term)>200 for term in search['keywords']) or len(search['keywords'])>8:
        raise PipelineError('Automatic discovery needs 1..8 nonempty topics of at most 200 characters')
    if type(search.get('refresh_cached_details',False)) is not bool:raise PipelineError('Cached-detail refresh setting must be boolean')
    if type(search.get('pagination',False)) is not bool or type(search.get('max_search_requests',3)) is not int or not 1<=search.get('max_search_requests',3)<=3:
        raise PipelineError('Pagination requires a boolean and 1..3 search requests per run')
    if type(search.get('public_reference_fallback',True)) is not bool:raise PipelineError('Automatic public-reference fallback requires a boolean')
    if type(search.get('catalog_sample',False)) is not bool:
        raise PipelineError('Catalog sample setting must be boolean')
    if not 1 <= int(search.get('max_detail_fetch', 14)) <= 25:
        raise PipelineError('Detail request budget must be between 1 and 25')
    try:
        minimum=int(cfg.get('selection',{}).get('min_days_left',10))
        rows=int(search.get('rows',25))
    except (ValueError,TypeError) as error:
        raise PipelineError('Selection limits must be integers') from error
    if not 1 <= minimum <= 365 or not 1 <= rows <= 100:
        raise PipelineError('Selection needs 1..365 days left and 1..100 search rows')
    return cfg


def doctor(cfg=None, hashes=False):
    cfg = cfg or load_config()
    checks = []
    def check(name, passed, detail):
        checks.append({'check': name, 'pass': bool(passed), 'detail': detail})
    try:
        validate_config(cfg)
        check('configuration', True, 'CPU/local, no spend; offline ASR required')
    except (PipelineError, ValueError, TypeError) as e:
        check('configuration', False, str(e))
    for name in ('ffmpeg', 'ffprobe'):
        try:value=resolve_tool(name);check(name,bool(value),value or 'Configured tool missing; no download/fallback')
        except PipelineError as error:check(name,False,str(error))
    check('runtime_paths',RUNTIME_PATHS_ERROR is None,RUNTIME_PATHS_ERROR or 'Explicit paths or compatible local defaults')
    if RUNTIME_PATHS.get('python_executable'):check('python_executable',Path(RUNTIME_PATHS['python_executable']).is_file(),RUNTIME_PATHS['python_executable'])
    for name in ('kokoro', 'faster-whisper', 'Pillow', 'num2words', 'truststore'):
        try:
            version = importlib.metadata.version(name)
            check(name, True, version)
        except importlib.metadata.PackageNotFoundError:
            check(name, False, 'not installed in this interpreter')
    if cfg.get('voice', {}).get('backend') == 'kokoro':
        directory = Path(cfg['voice']['model_dir'])
        for name in ('kokoro-v1_0.pth', 'voices/af_heart.pt', 'config.json'):
            path = directory / name
            check('voice_file:' + name, path.is_file() and path.stat().st_size > 0,
                  sha256_file(path) if hashes and path.is_file() else str(path))
    check('runtime_downloads_disabled', os.environ.get('HF_HUB_OFFLINE') == '1' and
          os.environ.get('TRANSFORMERS_OFFLINE') == '1', 'offline model flags')
    return {'ready': all(item['pass'] for item in checks), 'checks': checks,
            'ai_home': str(AI_HOME), 'ui_integration': 'Not checked by model/config doctor; no UI was opened'}

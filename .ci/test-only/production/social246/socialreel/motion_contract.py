"""Motion text/schema checks: keep user metadata and never silently lose prompts."""
import copy,difflib
from .common import PipelineError
DEFAULT_PROMPT='The masked subject takes the appearance and clothing of the supplied reference image. Follow the source subject motion, framing and camera. Preserve the original unmasked background.'
FIELDS=set('id video mask reference default_reference mask_scope motion_prompt prompt media source_url license test_allowed identity_approved production_approved commercial_template_approved quality benchmark_only catalogue_kind source_window person_mask_verified ready_scope correction_manifest metadata_warnings control_type control_video'.split())
def normalize_template(item):
    if not isinstance(item,dict):raise PipelineError('Motion template must be an object; no input opened')
    value=copy.deepcopy(item);warnings=[]
    kind=value.get('control_type')
    if kind not in (None,'pose','depth'):raise PipelineError('Motion control_type must be pose or depth; no input opened')
    if (kind is None)!=('control_video' not in value):raise PipelineError('Structural pose/depth requires both control_type and hashed control_video; no gray fallback')
    if kind is not None and not isinstance(value['control_video'],dict):raise PipelineError('Structural control_video must contain path and sha256')
    for field in sorted(set(value)-FIELDS):
        match=difflib.get_close_matches(field,('motion_prompt','prompt','default_reference','mask_scope','video','mask'),n=1,cutoff=.8)
        if match:raise PipelineError('Unknown motion field '+field+'; did you mean '+match[0]+'? Original text preserved; no preparation started')
        warnings.append('Metadata field '+field+' is preserved but does not configure the workflow')
    texts=[]
    for field in ('motion_prompt','prompt'):
        if field in value:
            text=value[field]
            if not isinstance(text,str) or not text.strip() or len(text)>16000:raise PipelineError('Motion '+field+' must be nonempty text of at most 16000 characters; no input opened')
            texts.append((field,text))
    if len(texts)==2 and texts[0][1]!=texts[1][1]:raise PipelineError('Conflicting motion_prompt and prompt; choose one text explicitly; no input opened')
    if texts:
        value['motion_prompt']=texts[0][1]
        if 'prompt' in value:warnings.append('Legacy prompt accepted as motion_prompt; exact user text preserved')
    value['metadata_warnings']=warnings
    return value
def resolved_prompt(item):return normalize_template(item).get('motion_prompt',DEFAULT_PROMPT)

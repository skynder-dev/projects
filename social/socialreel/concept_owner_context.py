"""Small explicit owner editorial revision; never source evidence or approval."""
from .common import PipelineError,read_json,stable_json,sha256_bytes
from .concept_locks import motion_lock
from .concept_storage import write_json
FIELDS={'editorial_preference','audience','desired_angle'}
SCOPE='unverified_owner_editorial_context'
def digest(value):return sha256_bytes(stable_json(value).encode('utf-8'))
def _read(store,job_id):
    home=store.folder(job_id)/'concept_owner_context';head=home/'head.json'
    if not head.exists():return {'revision':'absent','context':{},'scope':SCOPE,'owner_approval':False,'source_evidence':False}
    revision=read_json(head).get('revision')
    if not isinstance(revision,str) or len(revision)!=64 or any(c not in '0123456789abcdef' for c in revision):raise PipelineError('Owner context revision invalid')
    value=read_json(home/'revisions'/(revision+'.json'))
    if digest(value)!=revision or value.get('job_id')!=job_id or value.get('scope')!=SCOPE or value.get('owner_approval') is not False or value.get('source_evidence') is not False:raise PipelineError('Owner context revision integrity mismatch')
    return {'revision':revision,**value}
def read(store,job_id):
    store.folder(job_id)
    with store.connect() as connection:
        if connection.execute('SELECT id FROM jobs WHERE id=?',(job_id,)).fetchone() is None:raise PipelineError('Research job not found')
    with motion_lock(store.root,'concept_owner_context_'+job_id,wait=5):return _read(store,job_id)
def save(store,job_id,expected_revision,context):
    store.folder(job_id)
    with store.connect() as connection:
        if connection.execute('SELECT id FROM jobs WHERE id=?',(job_id,)).fetchone() is None:raise PipelineError('Research job not found')
    if not isinstance(context,dict) or set(context)-FIELDS or any(not isinstance(v,str) or len(v)>1000 for v in context.values()):raise PipelineError('Owner context allows only editorial_preference, audience, desired_angle strings up to1000characters each')
    with motion_lock(store.root,'concept_owner_context_'+job_id,wait=5):
        current=_read(store,job_id)
        if expected_revision!=current['revision']:raise PipelineError('Owner context revision conflict; read current revision before saving')
        value={'schema':'SOCIAL_CONCEPT_OWNER_CONTEXT_V1','job_id':job_id,'parent_revision':current['revision'],'context':dict(context),'scope':SCOPE,'owner_approval':False,'source_evidence':False}
        revision=digest(value);home=store.folder(job_id)/'concept_owner_context';path=home/'revisions'/(revision+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(stable_json(value).encode('utf-8'))
        write_json(home/'head.json',{'revision':revision});return {'revision':revision,**value}

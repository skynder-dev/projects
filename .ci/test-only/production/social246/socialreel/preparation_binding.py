"""Bind immutable preparation bytes to this durable source/script request."""
from pathlib import Path
import json
from .common import PipelineError,read_json,sha256_file

def verify_request(store,job_id,directory,manifest):
 folder=store.folder(job_id);directory=Path(directory).resolve()
 if not directory.is_relative_to((folder/'runs').resolve()):raise PipelineError('Preparation is outside this owned job')
 with store.connect() as connection:row=connection.execute('SELECT request_json FROM jobs WHERE id=?',(job_id,)).fetchone()
 if row is None:raise PipelineError('Preparation request missing')
 request=json.loads(row['request_json']);config=read_json(folder/'config.json')
 if not isinstance(request,dict) or request.get('stop_after')!='script' or request.get('config')!=config:raise PipelineError('Preparation durable config/target differs from submitted request')
 if read_json(directory/'preparation_config.json')!=config:raise PipelineError('Preparation config belongs to a different request')
 lineage=request.get('source_materialization')
 if lineage is not None:
  if not isinstance(lineage,dict) or manifest.get('mode')!='source_only_fact_materialization' or request.get('models_allowed') is not False:raise PipelineError('Source materialization request differs')
  actual=read_json(directory/'source_materialization.json')
  if not lineage or any(actual.get(k)!=v for k,v in lineage.items()):raise PipelineError('Source materialization lineage belongs to another request')
  return {'schema':'SOCIAL_PREPARATION_REQUEST_BINDING_V1','config_bound':True,'source_materialization_lineage_bound':True,'semantic_approval':False}
 if manifest.get('mode')=='source_only_fact_materialization':raise PipelineError('Source materialization has no matching durable request')
 if request.get('opportunity') is not None and str(manifest.get('opportunity_id'))!=str(request['opportunity']):raise PipelineError('Prepared opportunity differs from requested opportunity')
 public=request.get('public_source')
 if public is not None:
  from .public_page import validate,verify_cache,allowed
  mode=validate(public,config);receipt=verify_cache(folder/'public_input')
  if receipt['mode']!=mode or manifest.get('opportunity_id')!='USA-GOV-UNCLAIMED-MONEY':raise PipelineError('Preparation belongs to a different public source request')
  topic=read_json(directory/'topic.json');record=topic.get('selected') or topic
  if not allowed(record.get('source_url','')):raise PipelineError('Prepared topic is not the requested fixed public source')
  for own,saved in [('receipt.json','public_page_receipt.json'),('page.raw','public_page.raw'),('page.html','public_page.html')]:
   if sha256_file(folder/'public_input'/own)!=sha256_file(directory/'source'/saved):raise PipelineError('Prepared source bytes/receipt differ from this job acquisition')
 resume=request.get('resume_preparation')
 if resume and manifest.get('resumed_from_preparation_id')!=resume.get('preparation_id'):raise PipelineError('Preparation resume lineage differs from submitted parent')
 return {'schema':'SOCIAL_PREPARATION_REQUEST_BINDING_V1','config_bound':True,'fixed_public_source_bound':public is not None,'resume_lineage_bound':bool(resume),'semantic_approval':False}

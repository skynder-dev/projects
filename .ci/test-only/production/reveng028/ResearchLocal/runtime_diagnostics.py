"""Offline filesystem/module availability only. Never loads a model or installs tools."""
from pathlib import Path
import argparse,json,sys,importlib.util,os
import collector_capabilities
def quality(root):
 try:
  import analysis_readiness
  id='qualified-comparison-001'
  names={'analysis-readiness.json'}|{'attribution-cases/'+id+'-'+x+'.json' for x in ['input','catalog','output','response']}|{'analysis-quality/'+id+'-'+x+'.json' for x in ['semantic-review','receipt','completion']}
  def fetch(name):
   if name not in names:raise ValueError('Unexpected quality evidence path')
   p=(root/name).resolve()
   if not p.is_relative_to(root) or p.stat().st_size>8388608:raise ValueError('Quality evidence outside root or oversized')
   return p.read_bytes()
  summary=analysis_readiness.verify(fetch,names)
  return {'semantic_AI_readiness':summary['status'],'analysis_quality':summary,'quality_evidence_error':None}
 except (ValueError,KeyError,TypeError,OSError,ImportError) as ex:return {'semantic_AI_readiness':'UNKNOWN_QUALITY_EVIDENCE_UNAVAILABLE','analysis_quality':None,'quality_evidence_error':str(ex)}

def diagnose(root,purpose='view'):
 root=Path(root).resolve();app=root.parent;config_path=root/'runtime-settings.json';config=json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
 if not isinstance(config,dict):raise ValueError('runtime-settings.json must be an object')
 def availability(key):
  value=config.get(key)
  if not value:return {'configured':False,'exists':False,'message':'Не настроено; просмотр/экспорт не требуют модели.'}
  if not isinstance(value,str):raise ValueError(key+' must be a local file path')
  value=os.path.expandvars(value)
  if value.startswith(('\\\\','//')):return {'configured':True,'exists':False,'message':'Диагностика поддерживает только локальные пути; сетевые папки не проверялись.'}
  path=Path(value);path=path if path.is_absolute() else app/path
  return {'configured':True,'exists':path.is_file(),'path':str(path.resolve()),'message':'Только проверка наличия файла; запуск/загрузка/готовность AI не подтверждены.'}
 capabilities=collector_capabilities.describe();modules=capabilities['modules'];version_ok=sys.version_info>=(3,10);collector=capabilities['wordpress_listing'];missing=[name for name,available in modules.items() if not available]
 message='История и сохранённые источники открываются без AI. Экспорт использует только стандартную библиотеку Python. '
 if not version_ok:message+='Нужен существующий Python3.10+; автоматической установки нет. '
 if missing:message+='Для HTML-сбора отсутствуют модули: '+', '.join(missing)+'. Укажите уже подготовленное окружение через crawler_python; ничего не скачивается. '
 else:message+='Зависимости сбора найдены; новый сбор этой диагностикой не запускается. '
 message+=' JSON API discovery uses standard-library adapters; HTML availability is separate. Missing HTML is an explicit source limitation, never evidence of no demand. No model execution or profitability qualification. '
 return {'status':'diagnosed','python':sys.executable,'python_version':sys.version.split()[0],'root':str(root),'history_without_AI':True,'export_available':version_ok,'collector_available':collector,'api_collector_available':capabilities['api'],'html_collector_available':capabilities['html'],'wordpress_listing_available':capabilities['wordpress_listing'],'collector_capabilities':capabilities,'collector_mode':'FULL_DISCOVERY'if collector else'API_ONLY_HTML_UNAVAILABLE'if capabilities['api']else'UNAVAILABLE','collector_imports_or_network_tested':False,'optional_collector_modules':modules,'optional_exchange_validator_available':importlib.util.find_spec('jsonschema') is not None,'replacement_boundary_file_present':(root/'executor_exchange.py').is_file(),'disabled_replacement_contract_present':(root/'executor-contract'/'exchange.json').is_file(),'executor':availability('executor_file'),'model':availability('model_file'),'automatic_AI_enabled':False,**quality(root),'message':message,'automatic_download':False,'source_requests':0,'model_requests':0,'weights_loaded':0}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path);parser.add_argument('--purpose',choices=['view','export','collect','api','html'],default='view');args=parser.parse_args()
 try:print(json.dumps(diagnose(args.root,args.purpose),ensure_ascii=True))
 except Exception as ex:print(json.dumps({'status':'diagnostic_error','message':type(ex).__name__+': '+str(ex),'automatic_download':False,'model_requests':0,'source_requests':0}));raise SystemExit(1)

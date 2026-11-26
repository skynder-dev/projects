"""Russian owner presentation only. Raw English source/script and machine values stay intact."""
import hashlib,json,re
from pathlib import Path
from .common import PipelineError,stable_json
CATALOG=json.loads((Path(__file__).with_name('owner_ru.json')).read_text(encoding='utf-8'))
VERSION=CATALOG['version']

def label(value):return CATALOG['labels'].get(value,CATALOG['states'].get(value,value))

def state(value):
 text=str(value)
 known=text in CATALOG['states']
 return {'code':'owner_state' if known else 'unmapped_owner_state','text_ru':CATALOG['states'].get(text,'Неизвестное состояние: требуется проверка; исходный технический код: '+text),'original':text,'localized':known}

def explain(value):
 text=str(value)
 if text in CATALOG['reasons']:return {'code':'known_'+hashlib.sha256(text.encode()).hexdigest()[:12],'text_ru':CATALOG['reasons'][text],'original':text,'localized':True}
 for prefix,ru in sorted(CATALOG['reason_prefixes'].items(),key=lambda row:-len(row[0])):
  if text.startswith(prefix):return {'code':'prefix_'+hashlib.sha256(prefix.encode()).hexdigest()[:12],'text_ru':ru,'original':text,'localized':True}
 if re.search('[А-Яа-яЁё]',text):return {'code':'owner_text_ru','text_ru':text,'original':text,'localized':True}
 return {'code':'unmapped_owner_diagnostic','text_ru':'Нужна проверка. Для этой причины пока нет точного русского пояснения; сохранено оригинальное техническое сообщение. Не запускайте повторно работу без выяснения причины.','original':text,'localized':False}

def build(value):
 messages=[];seen=set()
 fields={'warnings','generation_blockers','review_blockers','blockers','reasons','approval_invalid_reasons'}
 skip={'owner_view','script','claims','source','sources','evidence','claim_evidence','original','description','local_model_editorial','saved_decisions','concept','lineage'}
 def add(text,path):
  if not isinstance(text,str) or not text.strip() or text in seen or len(messages)>=64:return
  seen.add(text);row=explain(text);row['path']=path;messages.append(row)
 def walk(node,path='',depth=0):
  if depth>10:return
  if isinstance(node,dict):
   for key,item in node.items():
    if key in skip:continue
    here=path+'/'+key
    if key in {'state','queue_state','script_state'} and isinstance(item,str):
     row=state(item)
     if not row['localized'] and item not in seen and len(messages)<64:
      seen.add(item);row['path']=here;messages.append(row)
    elif key=='reason' and path.endswith('/editorial_decision'):add(item,here)
    elif key in fields and isinstance(item,list):
     for n,text in enumerate(item):add(text,here+'/'+str(n))
    elif key in {'detail','next_step','explanation','empty_reason','blocked_reason'} and (path.endswith('/waiting') or key in {'explanation','empty_reason','blocked_reason'} or key=='detail' and path==''):add(item,here)
    elif isinstance(item,(dict,list)):walk(item,here,depth+1)
  elif isinstance(node,list):
   for n,item in enumerate(node[:100]):walk(item,path+'/'+str(n),depth+1)
 walk(value)
 summary=['Исходные цитаты, названия, озвучка и экранный текст остаются на английском. Русские пояснения — отдельный слой, а не оригинал источника.','Сохранённые сведения не подтверждают текущую актуальность, право конкретного заявителя или разрешение на публикацию.']
 if value.get('script_state')=='unrendered_script_draft' or (value.get('current_material') or {}).get('requires_review'):summary.append('Есть непроверенная текущая правка или изменения источника. Одобрение прежних материалов на них не переносится.')
 if value.get('local_model_editorial'):summary.append('Комментарий модели и её варианты показаны без перевода как непроверенный совет. Это не подтверждение фактов или качества.')
 angle=value.get('saved_editorial_angle') or {};kind=(angle.get('money_scope') or {}).get('kind');category=((value.get('audience_fit') or {}).get(value.get('configured_audience')) or {}).get('category');benefit_key=kind if kind in CATALOG['benefit_explanations'] else 'institutional' if category=='institutional' else 'unknown'
 view={'language':'ru','source_language':'en','catalog_version':VERSION,'title_ru':'Пояснения для владельца','state_label_ru':state(value.get('state') or value.get('script_state') or value.get('queue_state') or 'review_required')['text_ru'],'summary_ru':summary,'benefit_explanation_ru':CATALOG['benefit_explanations'][benefit_key] if 'saved_editorial_angle' in value else None,'benefit_explanation_is_local_profile_summary_not_source_quote':True,'messages':messages,'unmapped_count':sum(not m['localized'] for m in messages),'source_translation_implied':False,'approval_implied':False}
 view['presentation_revision']=hashlib.sha256(stable_json(view).encode()).hexdigest();return view

def present(value):
 return {**value,'owner_view':build(value)} if isinstance(value,dict) else value

def error(original):
 if hasattr(original,'owner_message'):return original
 text=str(original);row=explain(text)
 original.args=(row['text_ru']+'\nОригинальное техническое сообщение, без перевода: '+text,)
 original.owner_code=row['code'];original.owner_message=row;original.original_error=text
 return original

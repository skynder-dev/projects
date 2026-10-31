"""Import/review saved model proposals only. No model/provider/network execution."""
from pathlib import Path
import json,os,argparse
import source_ledger as l,model_contract
def bind_v1(cat,contract,allow_historical=False):
 model_contract.validate_prompt(contract);actual={m['id']:m for m in cat['materials']}
 for id,field in contract['source_packet']['sources'].items():
  m=actual.get(id)
  if l.rawsha(field['text'].encode())!=field['text_sha256']:raise ValueError('Stored source snapshot text hash mismatch')
  if not allow_historical and not field['metadata'].get('origins'):raise ValueError('Origin-bound import requires saved provenance; missing origins remain unknown/unverified')
  if m is None:
   if allow_historical:continue
   raise ValueError('Cannot import a proposal for a source absent from current catalog')
  snapshot={'id':id,'text':field['text'],'text_sha256':field['text_sha256'],'metadata':field['metadata']}
  if not l.same_source_revision(m,snapshot) or field['mechanical_units']!=m['units']:raise ValueError('Contract source differs from exact source revision/origins')
def load(root,cat):
 p=Path(root)/'source-model-proposals.json'
 if not p.exists():return {'schema':'reveng-saved-source-proposals-v1','entries':[],'automatic_admission':False}
 data=l.unseal(l.read(p)[1])
 if data['schema']!='reveng-saved-source-proposals-v1' or data['automatic_admission'] is not False:raise ValueError('Invalid proposal policy')
 for w in data['entries']:
  row=l.unseal(w);bind(cat,row['contract'],allow_historical=True);validation=validate_row_result(row)
  if 'contract_provenance_pin' in row and row['contract_provenance_pin']!=contract_pin(row['contract']):raise ValueError('Saved contract/provenance pin mismatch')
  if row['semantic_status']!='UNVERIFIED_MODEL_PROPOSAL' or row['execution_receipt_verified'] is not False or row['automatic_admission'] is not False or row['literal_validation']!=validation:raise ValueError('Imported proposal cannot claim verified runtime/meaning')
 return data
def import_v1(root,contract,result,label):
 l.require_writable(root)
 root=Path(root).resolve();cat=l.catalog(root);bind(cat,contract);validation=model_contract.validate_result(contract,result)
 with l.writer_lock(root/'.source-proposal-write-v2.lock'):
  data=load(root,cat);row={'contract':contract,'result':result,'declared_model_label':label,'semantic_status':'UNVERIFIED_MODEL_PROPOSAL','execution_receipt_verified':False,'automatic_admission':False,'literal_validation':validation};row['contract_provenance_pin']=contract_pin(contract);w=l.seal(row)
  if any(import_identity(l.unseal(x))==import_identity(row) for x in data['entries']):raise ValueError('Saved proposal already imported')
  data['entries'].append(w);l.write(root/'source-model-proposals.json',l.seal(data));return {'status':'SAVED_UNVERIFIED_PROPOSAL_ONLY','entry_id':w['payload_sha256'],'model_calls':0,'automatic_admission':False}
def strict_json(raw):
 def pairs(values):
  d={}
  for k,v in values:
   if k in d:raise ValueError('Duplicate JSON key; no silent field overwrite')
   d[k]=v
  return d
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Non-JSON constant')))
# V2 integration below: raw bytes and derived journal remain separately sealed fields.
import base64,contract_v2,contract_v3,contract_v4
import response_diagnostics as rd
def is_v2(contract):return contract.get('contract_version')==contract_v2.VERSION
def is_v3(contract):return contract.get('contract_version') in {contract_v3.VERSION,contract_v3.LEGACY_VERSION,'reveng-source-unit-contract-v3.2','reveng-source-unit-contract-v3.3'}
def is_v4(contract):return contract.get('contract_version')==contract_v4.VERSION

def catalog_material_id(field):
 # Field catalogs use material-id:field-id, whereas the saved ledger keys the
 # material itself. Resolve only this explicit identity, never by equal text.
 identity=field.get('metadata',{}).get('id');source=field['source_id']
 if source==identity:return identity
 if isinstance(identity,str) and source==identity+':'+field['field_id']:return identity
 raise ValueError('Source field identity is not its exact saved material/field')
def validate_v2_contract(contract):
 fields=contract['source_catalog']
 expected=contract_v2.make(fields);expected['source_catalog']=fields
 if contract!=expected:raise ValueError('Unsupported/modified v2 schema or prompt')
 # Validate every fragment against the immutable field; duplicates are forbidden.
 for f in fields:
  if contract_v2.digest(f['text'])!=f['text_sha256']:raise ValueError('V2 source hash changed')
  if len({u['fragment_id'] for u in f['fragments']})!=len(f['fragments']):raise ValueError('Duplicate fragment ID')
  for u in f['fragments']:
   a,b=u['start'],u['end']
   if type(a)is not int or type(b)is not int or not 0<=a<b<=len(f['text']) or f['text'][a:b]!=u['quote']:raise ValueError('Invalid fragment')
 return fields
def bind(cat,contract,allow_historical=False):
 if is_v4(contract):
  contract_v4.validate(contract)
  return bind(cat,contract_v3.make(contract['source_catalog']),allow_historical)
 if is_v3(contract):
  contract_v3.validate(contract)
  legacy=contract_v2.make(contract['source_catalog']);legacy['source_catalog']=contract['source_catalog']
  return bind(cat,legacy,allow_historical)
 if not is_v2(contract):return bind_v1(cat,contract,allow_historical)
 fields=validate_v2_contract(contract);actual={m['id']:m for m in cat['materials']}
 if len({(f['source_id'],f['field_id']) for f in fields})!=len(fields):raise ValueError('Duplicate source/field')
 for f in fields:
  if f['field_id']!=f['metadata'].get('source_field','text'):raise ValueError('Field identity differs from source metadata')
  identity=catalog_material_id(f);m=actual.get(identity)
  if not allow_historical and not f['metadata'].get('origins'):raise ValueError('Origin-bound import requires saved provenance; missing origins remain unknown/unverified')
  if m is None:
   if allow_historical:continue
   raise ValueError('V2 source absent from current catalog')
  snapshot={'id':identity,'text':f['text'],'text_sha256':f['text_sha256'],'metadata':f['metadata']}
  if not l.same_source_revision(m,snapshot):raise ValueError('V2 source revision/origins differ')
  # A field-qualified identity also qualifies its mechanical unit hashes.
  # Require the same boundaries/quotes as the real material, then recompute
  # field IDs rather than trusting supplied fragment IDs.
  fieldunits=l.units(m['text'],f['source_id'])
  if [(u['start'],u['end'],u['quote']) for u in fieldunits]!=[(u['start'],u['end'],u['quote']) for u in m['units']]:raise ValueError('Field/material partition differs')
  expected=[{'fragment_id':u['id'],'start':u['start'],'end':u['end'],'quote':u['quote']} for u in fieldunits]
  if f['fragments']!=expected:raise ValueError('V2 premarked fragments differ from catalog')
def derive_v2(contract,raw):
 fields=validate_v2_contract(contract)
 content=rd.unwrap(raw)
 journal=contract_v2.bind(fields,content)
 if not journal['literal_binding_complete']:raise ValueError('V2 exact binding rejected: '+json.dumps(journal,ensure_ascii=True))
 model=strict_json(content.decode('utf-8'));sources={}
 for f in fields:
  sources[f['source_id']]={'status':'needs_review','source_id':f['source_id'],'source_text_sha256':f['text_sha256'],'reason':'No semantic approval; exact binding is not meaning verification'}
 for row in model['needs_review']:sources[row['source_id']]['reason']=row['reason']
 for check in journal['binding_checks']:
  e=model['annotations'][check['annotation_index']];sid=e['source_id'];target=sources[sid]
  if target['status']!='proposed_annotations':target.update(status='proposed_annotations',annotations=[]);target.pop('reason',None)
  target['annotations'].append({'category':e['category'],'citation':{'start':check['start'],'end':check['end'],'quote':e['quote']},'AI_reading_unverified':e['AI_reading_unverified'],'epistemic_status':'MODEL_PROPOSAL_NOT_VERIFIED_FACT','binding_method':'PROGRAM_COMPUTED_EXACT_V2','field_id':e['field_id']})
 result={'sources':sources,'automatic_admission':False}
 validation={'status':'STRUCTURE_AND_LITERAL_REFERENCES_ONLY','citations':len(journal['binding_checks']),'semantic_coverage':'MANUAL_REVIEW_REQUIRED','model_quality_PASS':False,'automatic_admission':False,'new_execution_authorized':False}
 return result,journal,validation
def validate_row_result(row):
 if is_v3(row['contract']) or is_v4(row['contract']):
  raw=base64.b64decode(row['raw_response_base64'],validate=True)
  if l.rawsha(raw)!=row['raw_response_sha256']:raise ValueError('Raw response hash mismatch')
  derived=(contract_v4 if is_v4(row['contract']) else contract_v3).derive(row['contract'],rd.unwrap(raw))
  if derived['result']!=row['result'] or derived['binding_journal']!=row['computed_binding_journal'] or row['semantic_review']!={'status':'NOT_REVIEWED','PASS':False}:raise ValueError('V3 derived binding/meaning changed')
  return derived['validation']
 if not is_v2(row['contract']):return model_contract.validate_result(row['contract'],row['result'])
 raw=base64.b64decode(row['raw_response_base64'],validate=True)
 if l.rawsha(raw)!=row['raw_response_sha256']:raise ValueError('Raw response hash mismatch')
 result,journal,validation=derive_v2(row['contract'],raw)
 if result!=row['result'] or journal!=row['computed_binding_journal'] or row['semantic_review']!={'status':'NOT_REVIEWED','PASS':False}:raise ValueError('V2 derived binding/meaning changed')
 return validation
def import_identity(row):
 # The optional local migration pin is derived integrity metadata, not a new
 # proposal. Call only after load() has validated any existing pin. Preserve
 # all contract/provenance, exact raw, label and validation fields in identity.
 return l.rawsha(l.canonical({k:v for k,v in row.items() if k!='contract_provenance_pin'}))

def contract_pin(contract):
 # Local immutable sealed-row pin, not publisher authentication or semantic proof.
 return {'contract_sha256':l.rawsha(l.canonical(contract)),'provenance_sha256':l.rawsha(l.canonical([f['metadata'] for f in contract['source_catalog']] if 'source_catalog' in contract else {k:v['metadata'] for k,v in contract['source_packet']['sources'].items()}))}

def bindings(data,cat):
 actual={m['id']:m for m in cat['materials']};ids=set(actual);out=[]
 for w in data['entries']:
  row=l.unseal(w);c=row['contract'];sourceids=[f['source_id'] for f in c['source_catalog']] if is_v2(c) or is_v3(c) or is_v4(c) else list(c['source_packet']['sources'])
  import proposal_quality
  materialids={f['source_id']:catalog_material_id(f) for f in c['source_catalog']} if is_v2(c) or is_v3(c) or is_v4(c) else {id:id for id in sourceids}
  fields={f['source_id']:f for f in c['source_catalog']} if 'source_catalog' in c else c['source_packet']['sources']
  statuses={}
  for id in sourceids:
   f=fields[id];identity=materialids[id];snapshot={'id':identity,'text':f['text'],'text_sha256':f['text_sha256'],'metadata':f['metadata']}
   statuses[id]=l.provenance_status(actual[identity],snapshot) if identity in actual else 'HISTORICAL_NOT_CURRENTLY_RESOLVABLE_UNVERIFIED'
  out.append({'entry_id':w['payload_sha256'],'contract_version':c.get('contract_version',c.get('schema')),'sources':statuses,'review_diagnostics':proposal_quality.for_row(row)})
 return out
def import_saved(root,contract,result,label):
 l.require_writable(root)
 if is_v3(contract) or is_v4(contract):
  if type(result)is not bytes:raise ValueError('V3 requires original saved response bytes')
  return import_v3_raw(root,contract,result,label)
 if is_v2(contract):
  if type(result)is not bytes:raise ValueError('V2 requires original saved response bytes, not reserialized object')
  return import_v2_raw(root,contract,result,label)
 return import_v1(root,contract,result,label)

def import_v3_raw(root,contract,raw,label):
 l.require_writable(root);root=Path(root).resolve();cat=l.catalog(root);bind(cat,contract)
 derived=(contract_v4 if is_v4(contract) else contract_v3).derive(contract,rd.unwrap(raw))
 row={'contract':contract,'result':derived['result'],'declared_model_label':label,'semantic_status':'UNVERIFIED_MODEL_PROPOSAL','execution_receipt_verified':False,'automatic_admission':False,'literal_validation':derived['validation'],'raw_response_base64':base64.b64encode(raw).decode('ascii'),'raw_response_sha256':l.rawsha(raw),'computed_binding_journal':derived['binding_journal'],'semantic_review':{'status':'NOT_REVIEWED','PASS':False}}
 with l.writer_lock(root/'.source-proposal-write-v2.lock'):
  data=load(root,cat);row['contract_provenance_pin']=contract_pin(contract);w=l.seal(row)
  if any(import_identity(l.unseal(x))==import_identity(row) for x in data['entries']):raise ValueError('Saved proposal already imported')
  data['entries'].append(w);l.write(root/'source-model-proposals.json',l.seal(data))
 return {'status':'SAVED_UNVERIFIED_PROPOSAL_ONLY','entry_id':w['payload_sha256'],'model_calls':0,'automatic_admission':False,'semantic_PASS':False}
def import_v2_raw(root,contract,raw,label):
 l.require_writable(root)
 root=Path(root).resolve();cat=l.catalog(root);bind(cat,contract)
 result,journal,validation=derive_v2(contract,raw)
 row={'contract':contract,'result':result,'declared_model_label':label,'semantic_status':'UNVERIFIED_MODEL_PROPOSAL','execution_receipt_verified':False,'automatic_admission':False,'literal_validation':validation,
      'raw_response_base64':base64.b64encode(raw).decode('ascii'),'raw_response_sha256':l.rawsha(raw),'computed_binding_journal':journal,'semantic_review':{'status':'NOT_REVIEWED','PASS':False}}
 with l.writer_lock(root/'.source-proposal-write-v2.lock'):
  data=load(root,cat);row['contract_provenance_pin']=contract_pin(contract);w=l.seal(row)
  if any(import_identity(l.unseal(x))==import_identity(row) for x in data['entries']):raise ValueError('Saved proposal already imported')
  data['entries'].append(w);l.write(root/'source-model-proposals.json',l.seal(data))
  return {'status':'SAVED_UNVERIFIED_PROPOSAL_ONLY','entry_id':w['payload_sha256'],'model_calls':0,'automatic_admission':False,'semantic_PASS':False,'binding_journal_sha256':l.rawsha(json.dumps(journal,sort_keys=True,ensure_ascii=False).encode())}
def cli():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--response',type=Path,required=True);p.add_argument('--save-rejected-diagnostic',action='store_true');a=p.parse_args()
 for path in [a.root,a.contract,a.response]:
  if '://' in str(path) or str(path).startswith(('\\\\','//')):raise ValueError('Bounded local files only')
 c=None;raw=None
 try:
  c=strict_json(l.read(a.contract)[0].decode('utf-8-sig'))
  with a.response.open('rb') as stream:raw=stream.read(rd.LIMIT+1)
  if len(raw)>rd.LIMIT:raise ValueError('Saved response exceeds8MiB')
  if is_v3(c) or is_v4(c):result=import_v3_raw(a.root,c,raw,'EXTERNAL_SAVED_FILE_UNVERIFIED_RUNTIME')
  elif is_v2(c):result=import_v2_raw(a.root,c,raw,'EXTERNAL_SAVED_FILE_UNVERIFIED_RUNTIME')
  else:result=import_v1(a.root,c,strict_json(rd.unwrap(raw).decode('utf-8-sig')),'EXTERNAL_SAVED_FILE_UNVERIFIED_RUNTIME')
 except (ValueError,KeyError,TypeError,UnicodeError,OSError) as ex:
  d=ex.diagnostic if isinstance(ex,rd.RejectedResponse) else {'schema':'reveng-response-diagnostic-v1','reason_code':'SOURCE_CONTRACT_OR_LITERAL_VALIDATION_REJECTED','message':str(ex)[:4096],'eligible_for_structure_validation':False,'research_imported':False,'automatic_admission':False,'semantic_PASS':False,'model_calls':0}
  result={'status':'REJECTED_RESPONSE_NOT_IMPORTED','reason_code':d['reason_code'],'message':d['message'],'research_imported':False,'automatic_admission':False,'semantic_PASS':False}
  if a.save_rejected_diagnostic and c is not None and raw is not None and len(raw)<=rd.LIMIT:
   try:result['saved_diagnostic']=rd.save_rejected(a.root,c,raw,d)
   except (ValueError,OSError) as save_error:result['diagnostic_save_error']=str(save_error)
  print(json.dumps(result,ensure_ascii=True))
  return 0 if a.save_rejected_diagnostic else 2
 print(json.dumps(result,ensure_ascii=True));return 0

if __name__=='__main__':raise SystemExit(cli())

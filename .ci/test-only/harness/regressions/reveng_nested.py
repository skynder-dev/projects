from pathlib import Path
import sys,json,zipfile,hashlib
src=Path(sys.argv[1]).resolve();C=Path(sys.argv[2]).resolve();R=C/'rc0010-owner-json-tests';sys.path.insert(0,str(src));import research_export as ex

report=json.loads((R/'REPORT.json').read_text(encoding='utf-8'));rows=[]
with zipfile.ZipFile(R/'valid_legacy/exports/проверка-😀.zip') as z:base={n:z.read(n) for n in z.namelist()}
def archive(name,files):
 p=R/(name+'.zip')
 with zipfile.ZipFile(p,'x') as z:
  for n,b in files.items():z.writestr(n,b)
 return p
for key in ['kind','files']:
 files=dict(base);text=files['manifest.json'].decode('utf-8');value='"bad-kind"' if key=='kind' else '[]';files['manifest.json']=('{"'+key+'":'+value+','+text.lstrip()[1:]).encode();p=archive('duplicate-manifest-'+key,files);error=''
 try:ex.verify(p)
 except ValueError as e:error=str(e)
 assert 'Duplicate' in error;rows.append({'case':'duplicate_manifest_'+key,'rejected':True,'error':error})
text='Synthetic recovery ё 😀';payload={'schema':'reveng-editor-recovery-v1','status':'INCOMPLETE_EDITOR_WORK_NOT_HYPOTHESIS','auto_admission':False,'saved_at':'2026-10-20T00:00:00Z','source_snapshot':{'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest()},'previous_id':'','start':-1,'end':-1,'fields':{k:'Synthetic field' for k in ['title','interpretation','assumptions','buyer_role','next_action','success','failure']}};good=json.dumps(payload,ensure_ascii=False);bad=good.replace('"title": "Synthetic field"','"title": "A", "title": "B"');name='manual-editor-recovery/'+('a'*32)+'.json'
for case,inner in [('valid',good),('duplicate',bad)]:
 root=R/('encoded-recovery-'+case);root.mkdir()
 for member in ['candidates.json','research-output-cards.json','analysis-queue.json','review-notes.json']:(root/member).write_bytes(base[member])
 p=root/name;p.parent.mkdir();p.write_text(json.dumps({'payload_json':inner,'payload_sha256':hashlib.sha256(inner.encode()).hexdigest()},ensure_ascii=False),encoding='utf-8');before=p.read_bytes();out=root/'exports/recovery.zip';error=''
 try:result=ex.export(root,out);ex.verify(out)
 except ValueError as e:error=str(e)
 if case=='valid':assert not error
 else:assert 'Duplicate' in error and not out.exists() and not out.with_suffix('.csv').exists() and p.read_bytes()==before
 rows.append({'case':'actual_export_encoded_recovery_'+case,'pass':True,'rejected':bool(error),'source_preserved':p.read_bytes()==before})
files=dict(base);raw=(R/'encoded-recovery-duplicate'/name).read_bytes();files[name]=raw;m=json.loads(files['manifest.json']);m['files'].append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)});m['incomplete_editor_recovery_files']=1;files['manifest.json']=json.dumps(m).encode();p=archive('import-encoded-recovery-duplicate',files);error=''
try:ex.verify(p)
except ValueError as e:error=str(e)
assert 'Duplicate' in error;rows.append({'case':'actual_verify_hash_valid_duplicate_recovery_payload','rejected':True,'error':error})
(R/'ARCHIVE-RECOVERY-EXTRA.json').write_text(json.dumps({'checks':rows},indent=2),encoding='utf-8');print(json.dumps({'extra_cases':len(rows)}))

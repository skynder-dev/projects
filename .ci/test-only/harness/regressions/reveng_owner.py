from pathlib import Path
import sys,json,hashlib,shutil,zipfile,io,subprocess
src=Path(sys.argv[1]).resolve();C=Path(sys.argv[2]).resolve();R=C/'rc0010-owner-json-tests';R.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(src));import research_export as ex,archive_preview as ap,editor_recovery

def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def home(name,owner):
 root=R/name;root.mkdir();dump(root/'candidates.json',[{'candidate_id':'candidate','title':'Synthetic valid legacy ё 😀','review_revision_hash':'a'*64}])
 for n,v in [('research-output-cards.json',{'cards':[]}),('analysis-queue.json',{'jobs':{}})]:v['integrity_sha256']=ex.sha(ex.canonical(v));dump(root/n,v)
 (root/'review-notes.json').write_text(owner,encoding='utf-8');return root
fixtures={'root_duplicate_ID':'{"candidate":{"decision":"hold"},"candidate":{"decision":"reject"}}','nested_duplicate_decision':'{"candidate":{"decision":"hold","decision":"reject"}}','nested_duplicate_provenance':'{"candidate":{"provenance":{"source":"saved-A","source":"saved-B"}}}','escaped_equivalent_ID':'{"candidate":{},"\\u0063andidate":{}}','array_nested_duplicate_ID':'{"candidate":{"history":[{"id":"A","id":"B"}]}}'}
valid={'valid_legacy':'{"candidate":{"decision":"hold","note":"old value"}}','valid_case_distinct_ID':'{"candidate":{"decision":"hold"},"Candidate":{"decision":"reject"}}','valid_Unicode':'{"кандидат":{"decision":"hold","note":"ё 😀 é �","date":"2026-01-01T00:00:00Z"}}','literal_duplicate_like_text':'{"candidate":{"note":"literal {\\"id\\":1,\\"id\\":2}","decision":"hold"}}'}
rows=[]
for name,raw in fixtures.items():
 root=home(name,raw);p=root/'review-notes.json';before=sha(p);out=root/'exports/rejected.zip';rejected=''
 try:ex.export(root,out)
 except ValueError as e:rejected=str(e)
 assert 'Duplicate' in rejected and sha(p)==before and not out.exists() and not out.with_suffix('.csv').exists();assert not list(root.rglob('*.tmp'));rows.append({'case':name,'export_rejected':True,'no_partial_ZIP_CSV':True,'source_preserved':True,'error':rejected})
 # Existing target artifacts must also remain untouched under malformed input.
 out.parent.mkdir(exist_ok=True);out.write_bytes(b'SYNTHETIC EXISTING ZIP');out.with_suffix('.csv').write_bytes(b'SYNTHETIC EXISTING CSV');pins=[sha(out),sha(out.with_suffix('.csv'))]
 try:ex.export(root,out)
 except ValueError:pass
 assert pins==[sha(out),sha(out.with_suffix('.csv'))]
for name,raw in valid.items():
 root=home(name,raw);result=ex.export(root,root/'exports/проверка-😀.zip');m=ex.verify(Path(result['zip']));assert json.loads(raw)==json.loads((root/'review-notes.json').read_text(encoding='utf-8'))
 with zipfile.ZipFile(result['zip']) as z:assert z.read('review-notes.json')==raw.encode('utf-8')
 preview=ap.preview(root,Path(result['zip']));assert not preview['workspace_replaced'];rows.append({'case':name,'pass':True,'original_owner_bytes_preserved':True,'preview_readonly':True})
good=R/'valid_legacy/exports/проверка-😀.zip'
with zipfile.ZipFile(good) as z:base={n:z.read(n) for n in z.namelist()}
for name,raw in fixtures.items():
 files=dict(base);files['review-notes.json']=raw.encode('utf-8');m=json.loads(files['manifest.json'])
 for entry in m['files']:
  if entry['path']=='review-notes.json':entry.update(bytes=len(files['review-notes.json']),sha256=hashlib.sha256(files['review-notes.json']).hexdigest())
 files['manifest.json']=json.dumps(m).encode();p=R/('import-'+name+'.zip')
 with zipfile.ZipFile(p,'x') as z:
  for n,b in files.items():z.writestr(n,b)
 before=sha(p);rejected=''
 try:ex.verify(p)
 except ValueError as e:rejected=str(e)
 assert 'Duplicate' in rejected and sha(p)==before;rows.append({'case':'verified_hash_archive_'+name,'verify_rejected':True,'input_archive_preserved':True})
# Encoded recovery payload is interpreted JSON, not arbitrary source prose.
text='Synthetic recovery ё 😀';payload={'schema':'reveng-editor-recovery-v1','status':'INCOMPLETE_EDITOR_WORK_NOT_HYPOTHESIS','auto_admission':False,'saved_at':'2026-10-20T00:00:00Z','source_snapshot':{'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest()},'previous_id':'','start':-1,'end':-1,'fields':{k:'Synthetic field' for k in ['title','interpretation','assumptions','buyer_role','next_action','success','failure']}};plain=json.dumps(payload,ensure_ascii=False);bad=plain.replace('"title": "Synthetic field"','"title": "A", "title": "B"');assert bad!=plain
for name,value,expect in [('valid_recovery',plain,True),('duplicate_encoded_recovery_field',bad,False)]:
 raw=json.dumps({'payload_json':value,'payload_sha256':hashlib.sha256(value.encode()).hexdigest()},ensure_ascii=False).encode();path='manual-editor-recovery/'+('a'*32)+'.json';ok=True
 try:assert editor_recovery.verify(lambda n:raw,{path})==1
 except ValueError:ok=False
 assert ok==expect;rows.append({'case':name,'pass':True,'accepted':ok})
report={'checks':rows,'fixtures':{**fixtures,**valid},'models':0,'production_source_only_two_files_changed':True,'no_closed_legacy_duplicate_reimport_rerun':True};dump(R/'REPORT.json',report);print(json.dumps({'checks':len(rows),'report':str(R/'REPORT.json')}))

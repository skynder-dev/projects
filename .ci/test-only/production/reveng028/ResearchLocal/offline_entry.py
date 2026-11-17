"""Portable offline entry to existing saved-evidence operations. No collector/executor."""
from pathlib import Path
import argparse,json,hashlib,shutil,sys,uuid

def main(argv=None):
 p=argparse.ArgumentParser(description='Saved evidence only; no network, models or GUI')
 p.add_argument('action',choices=['init-demo','check','compare','export','preview']);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--archive',type=Path)
 a=p.parse_args(argv);root=a.workspace.absolute()
 if str(root).startswith(('\\\\','//')):raise ValueError('Local workspace required')
 tools=Path(__file__).resolve().parent
 if a.action=='init-demo':
  if root.exists():raise ValueError('Choose a new empty workspace path; existing directories are never replaced')
  source=tools.parent/'example-workspace';inventory=json.loads((tools.parent/'example-workspace-manifest.json').read_text(encoding='utf-8'))
  actual={f.relative_to(source).as_posix()for f in source.rglob('*')if f.is_file()}
  if actual!=set(inventory['files']):raise ValueError('Bundled example inventory changed')
  for name,h in inventory['files'].items():
   path=(source/name).resolve()
   if not path.is_relative_to(source.resolve())or hashlib.sha256(path.read_bytes()).hexdigest()!=h:raise ValueError('Bundled example bytes changed')
  shutil.copytree(source,root);result={'status':'CREATED_CONTROLLED_EXAMPLE','workspace':str(root),'meaning':'Six historical cards and a controlled raw fixture; no new public capture, customer or market evidence'}
 else:
  if not root.is_dir():raise ValueError('Workspace missing; init-demo requires a new local path')
  import comparison_data,source_ledger
  if a.action=='check':
   data=comparison_data.build(root);result={'status':'SAVED_EVIDENCE_READABLE','rows':len(data['rows']),'winner_selected':False,'automatic_admission':False,'meaning':'Structural/local consistency only; no business or semantic readiness claim'}
  elif a.action=='compare':
   source_ledger.require_writable(root);data=comparison_data.build(root);comparison_data.save(root,data);result={'status':'BUILT_SAVED_COMPARISON','rows':len(data['rows']),'winner_selected':False,'automatic_admission':False}
  elif a.action=='export':
   import research_export
   result=research_export.export(root,root/'exports'/('saved-'+uuid.uuid4().hex[:12]+'.zip'))
  else:
   if a.archive is None:raise ValueError('preview requires --archive <local-research.zip>')
   import archive_preview
   result=archive_preview.preview(root,a.archive)
 result.update(network_calls=0,model_calls=0,GUI_constructed=False);print(json.dumps(result,ensure_ascii=True));return 0

if __name__=='__main__':
 try:raise SystemExit(main())
 except (ValueError,OSError,KeyError,TypeError)as ex:print(json.dumps({'status':'OFFLINE_COMMAND_REJECTED','error':str(ex),'network_calls':0,'model_calls':0},ensure_ascii=True));raise SystemExit(2)

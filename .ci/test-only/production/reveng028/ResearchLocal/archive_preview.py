"""Validate a research data archive and create an isolated readonly-view snapshot. Never imports code or replaces workspace."""
from pathlib import Path
import argparse,io,json,zipfile,hashlib,uuid,tempfile,shutil,stat
import research_export,comparison_data,restore_difference,portable_paths
LIMIT=128*1024*1024

def allocate_preview(parent,names):
 # Short generated directory names only; archive member paths/hashes never change.
 # Exact collisions (including concurrent exclusive mkdir) are retried, not reused.
 generated=['.readonly-research-preview','comparison-state.json','.comparison-write.lock']
 portable_paths.check_files([parent/p/name for p in ['.p-'+'0'*12,'verified-'+'0'*12] for name in names+generated],'Archive preview')
 parent.mkdir(exist_ok=True)
 for attempt in range(64):
  token=uuid.uuid4().hex[:12];temp=parent/('.p-'+token);final=parent/('verified-'+token)
  if final.exists():continue
  try:temp.mkdir()
  except FileExistsError:continue
  return temp,final
 raise ValueError('Preview directory collision; no previous preview reused or overwritten; retry')
def preview(root,archive):
 root=Path(root).resolve();value=str(archive)
 if value.startswith(('\\\\','//')) or '://' in value:raise ValueError('Only an explicitly selected local ZIP is supported')
 source=Path(archive).resolve()
 if source.suffix.lower()!='.zip' or source.stat().st_size>LIMIT:raise ValueError('Bounded local research ZIP required')
 raw=source.read_bytes()
 if len(raw)>LIMIT:raise ValueError('Archive exceeds128MiB')
 manifest=research_export.verify(io.BytesIO(raw));parent=root/'archive-previews'
 if parent.exists() and getattr(parent.stat(follow_symlinks=False),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:raise ValueError('Preview parent must not be a reparse point')
 if not parent.resolve().is_relative_to(root) or (parent.exists() and len(list(parent.iterdir()))>=8):raise ValueError('Preview scope invalid or eight previous previews retained; no automatic deletion')
 with zipfile.ZipFile(io.BytesIO(raw))as z:names=z.namelist()
 temp,final=allocate_preview(parent,names)
 assert temp.resolve().is_relative_to(parent.resolve())
 try:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   for name in z.namelist():
    target=(temp/name).resolve()
    if not target.is_relative_to(temp.resolve()):raise ValueError('Archive path outside preview')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(z.read(name))
  for info in manifest['files']:
   if hashlib.sha256((temp/info['path']).read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Restored data bytes mismatch')
  (temp/'.readonly-research-preview').write_text(json.dumps({'policy':'HISTORICAL_READ_ONLY_ARCHIVE','archive_sha256':hashlib.sha256(raw).hexdigest(),'execution_authorized':False,'portable_source_evidence':manifest.get('portable_source_evidence',{'schema':'legacy_metadata_only','meaning':'Referenced raw bytes/structured observation inclusion not guaranteed by this historical format'})}),encoding='utf-8')
  data=comparison_data.build(temp);comparison_data.save(temp,data,preserve_chain=True)
  differences=restore_difference.compare(root,temp,data)
  # On Windows rename fails if a concurrent process created final; never replace it.
  if final.exists():raise ValueError('Preview destination appeared; previous preview preserved; retry')
  temp.rename(final)
  return {'status':'VERIFIED_ISOLATED_ARCHIVE_PREVIEW','preview_root':str(final),'archive_sha256':hashlib.sha256(raw).hexdigest(),'files':len(manifest['files'])+1,'comparison_rows':len(data['rows']),'protected_decision_snapshot_present':(final/'decision-recovery-v1.json').is_file(),'portable_source_evidence':manifest.get('portable_source_evidence',{'schema':'legacy_metadata_only','meaning':'Historical archive has no guarantee of referenced raw or structured observation inclusion'}),'workspace_replaced':False,'code_imported_from_archive':False,'source_dates_refreshed':False,'models_started':0,'network_calls':0,'differences':differences,'meaning':'Historical data-only snapshot for readonly comparison; current workspace/owner decisions unchanged; not full application backup, validation or permission to execute'}
 finally:
  if temp.exists():
   resolved=temp.resolve()
   if not resolved.is_relative_to(parent.resolve()) or not temp.name.startswith('.p-'):raise ValueError('Unsafe cleanup target')
   shutil.rmtree(temp)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(preview(a.root,a.archive),ensure_ascii=True))
 except Exception as ex:print(json.dumps({'status':'ARCHIVE_PREVIEW_REJECTED','error':str(ex),'workspace_replaced':False,'network_calls':0,'model_calls':0},ensure_ascii=True));raise SystemExit(1)

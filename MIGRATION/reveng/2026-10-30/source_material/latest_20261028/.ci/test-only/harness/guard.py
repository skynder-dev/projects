import sys,runpy
def audit(e,a):
 if e.startswith('socket.')or e in ('subprocess.Popen','os.system','os.startfile','urllib.Request'):raise PermissionError('Offline test guard: '+e)
 if e=='import'and str(a[0]).split('.')[0]in ('torch','transformers','onnxruntime','faster_whisper'):raise PermissionError('No model imports')
sys.addaudithook(audit);p=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(p,run_name='__main__')

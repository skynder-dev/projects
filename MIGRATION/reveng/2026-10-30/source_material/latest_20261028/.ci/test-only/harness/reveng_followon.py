"""Mandatory actual RevEng follow-on checks in the existing owned Windows CI copy.

No source capture, model dispatch, GUI, artifact upload or dependency installation.
The explicit local-stdlib mode is partial evidence and is refused in GitHub Actions.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys
from canonical_source import verify_researchlocal

SUITES=(
 ('test_researchlocal_offline.py','--include-existing-tests'),
 ('test_identity_portable.py',None),
 ('test_capability_portable.py',''),
 ('test_hypothesis_contract.py',''),
 ('test_task_routing.py',''),
 ('test_price_experiment_projection.py',''),
 ('test_saved_analysis_context.py',''),
 ('test_collection_integrity.py',''),
 ('test_answer_cache_integrity.py',''),
 ('test_price_cache_integrity.py',''),
 ('test_price_ui_contract.py',''),
 ('test_owner_preference_overlay.py',''),
 ('test_integrated_ci_contract.py',''),
)

def hashes(folder):
 return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}

def verify_owned(repo,product):
 source=verify_researchlocal(repo);owned=product/'ResearchLocal'
 if hashes(owned)!=hashes(source):raise ValueError('Owned source differs from verified canonical source')
 manifest=json.loads((repo/'reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json').read_bytes())
 tests={r['path'][len('reveng/tests/'):]:r['sha256'] for r in manifest['files'] if r['path'].startswith('reveng/tests/')}
 if hashes(repo/'reveng/tests')!=tests:raise ValueError('Exact canonical test inventory mismatch')
 return owned

def python_commands(repo,product,local_stdlib_only=False):
 source=product/'ResearchLocal';tests=repo/'reveng/tests';guard=repo/'.ci/test-only/harness/guard.py';commands=[]
 for optimized in (False,True):
  for script,extra in SUITES:
   if local_stdlib_only and script=='test_capability_portable.py':continue
   if not (tests/script).is_file():raise ValueError('Required actual regression absent: '+script)
   flags=[str(source)] if extra is None else ['--source',str(source)]+([extra] if extra else [])
   command=[sys.executable,'-X','utf8','-I','-B']+(['-O'] if optimized else [])+[str(guard),str(tests/script),*flags]
   commands.append((script+(' optimized' if optimized else ' normal'),command))
 return commands

def native_commands(repo,product):
 compiler=Path(os.environ.get('SystemRoot','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe';build=product/'candidate-build';wrapper=build/'wrapper.exe';tests=repo/'reveng/tests'
 price=build/'TestPriceExperimentPresentation.exe';owner=build/'TestOwnerPreferencePresentation.exe';drain=build/'TestPortableRuntimeDrain.exe';outcome=build/'TestOperationOutcome.exe'
 # All probes bind to the actual full application assembly built by run.py.
 # CLR resolves that assembly beside the probes; LocalEntry/Forms are not invoked.
 refs=['/r:'+str(wrapper),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll']
 return [
  ('compile native offer probe',[str(compiler),'/nologo','/target:exe','/main:TestPriceExperimentPresentation','/out:'+str(price),*refs,str(tests/'TestPriceExperimentPresentation.cs')]),
  ('run native offer probe',[str(price),str(tests/'price_ui_vectors.json')]),
  ('compile native preference probe',[str(compiler),'/nologo','/target:exe','/main:TestOwnerPreferencePresentation','/out:'+str(owner),*refs,str(tests/'TestOwnerPreferencePresentation.cs')]),
  ('run native preference probe',[str(owner)]),
  ('compile runtime drain probe',[str(compiler),'/nologo','/target:exe','/main:TestPortableRuntimeDrain','/out:'+str(drain),*refs,str(tests/'TestPortableRuntimeDrain.cs')]),
  ('run runtime drain probe',[str(drain)]),
  ('compile operation outcome probe',[str(compiler),'/nologo','/target:exe','/main:TestOperationOutcome','/out:'+str(outcome),*refs,str(tests/'TestOperationOutcome.cs')]),
  ('run operation outcome probe',[str(outcome)]),
 ]

def execute(label,command,cwd,env):
 print('CHECK '+label,flush=True)
 result=subprocess.run(command,cwd=cwd,env=env,timeout=90,capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 print(result.stdout);print(result.stderr)
 if result.returncode:raise RuntimeError('Required RevEng check failed: '+label+' exit='+str(result.returncode))
 if label=='run native offer probe' and re.search(r'^PASS [1-9][0-9]* native formatter assertions;',result.stdout,re.M) is None:raise ValueError('Actual native offer assertion receipt absent')
 if label=='run operation outcome probe' and re.search(r'^PASS [1-9][0-9]* in-process operation-outcome assertions;',result.stdout,re.M) is None:raise ValueError('Actual operation-outcome assertion receipt absent')
 if label=='run runtime drain probe' and re.search(r'^PASS [1-9][0-9]* in-process runtime reader/drain assertions;',result.stdout,re.M) is None:raise ValueError('Actual runtime reader/drain assertion receipt absent')
 if label=='run native preference probe' and re.search(r'^PASS [1-9][0-9]* SYNTHETIC native preference presentation checks;',result.stdout,re.M) is None:raise ValueError('Actual native preference assertion receipt absent')

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('product',type=Path,help='Existing owned product copy with ResearchLocal and compiled candidate-build/wrapper.exe');parser.add_argument('--local-stdlib-only',action='store_true');args=parser.parse_args(argv)
 repo=Path(__file__).resolve().parents[3];product=args.product.resolve()
 if args.local_stdlib_only and os.environ.get('GITHUB_ACTIONS','').lower()=='true':raise ValueError('Partial local mode is forbidden in hosted CI')
 source=verify_owned(repo,product);before=hashes(source);tests_before=hashes(repo/'reveng/tests')
 if not args.local_stdlib_only:
  compiler=Path(os.environ.get('SystemRoot','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
  if os.name!='nt' or not compiler.is_file() or not (product/'candidate-build/wrapper.exe').is_file():raise ValueError('Native Windows compiler and actual compiled application are mandatory; no fallback')
 env={k:v for k,v in os.environ.items() if not any(word in k.upper() for word in ['TOKEN','SECRET','API_KEY','CREDENTIAL']) and k.upper() not in ['PYTHONPATH','PYTHONHOME']};env.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
 try:
  for label,command in python_commands(repo,product,args.local_stdlib_only):execute(label,command,product.parent,env)
  if args.local_stdlib_only:print('PARTIAL LOCAL PASS: stdlib checks only; API capability and native probes NOT_RUN by this command')
  else:
   for label,command in native_commands(repo,product):execute(label,command,product.parent,env)
   print('PASS integrated RevEng actual Python normal/optimized and compiled native probes; no GUI/model/live transport')
 finally:
  if hashes(source)!=before or hashes(repo/'reveng/tests')!=tests_before:raise AssertionError('Source/test bytes changed during follow-on checks')
  verify_owned(repo,product)

if __name__=='__main__':main()

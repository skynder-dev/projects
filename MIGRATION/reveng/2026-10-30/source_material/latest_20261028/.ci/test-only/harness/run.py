from pathlib import Path
import sys,os,json,hashlib,tempfile,shutil,subprocess
P=Path(__file__).resolve().parent.parent;project=sys.argv[1];pins=json.loads((P/'CANDIDATE_PINS.json').read_bytes())[project]
for name,h in pins['files'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
home=Path(tempfile.mkdtemp(prefix='test-only-ci-'));product=home/'renamed'
if project=='reveng028':
 from canonical_source import verify_researchlocal
 src=verify_researchlocal(P.parents[1]);product.mkdir();shutil.copytree(src,product/'ResearchLocal')
else:
 src=P/'production'/project;shutil.copytree(src,product)
env={k:v for k,v in os.environ.items()if not any(s in k.upper()for s in ['TOKEN','SECRET','API_KEY','CREDENTIAL'])and k.upper()not in ['PYTHONPATH','PYTHONHOME']};env.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
def run(args,cwd=home):
 r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,timeout=90,capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));print(r.stdout);print(r.stderr);assert r.returncode==0,(args,r.returncode);return r.stdout
if project=='reveng028':run([sys.executable,'-X','utf8','-B',P/'harness/test_canonical_source.py'])
if project in ['social246','reveng028']:
 guard=P/'harness/guard.py'
 run([sys.executable,'-X','utf8','-I','-B',guard,P/'harness'/('social_check.py'if project=='social246'else'reveng_check.py'),product])
 if project=='social246':run([sys.executable,'-X','utf8','-I','-B',guard,P/'harness/social_reopen.py',product/'relocated'])
 if project=='reveng028':
  run([sys.executable,'-B',P/'harness/reveng/review_races.py',product/'ResearchLocal',home/'races'])
  d=json.loads((home/'races/proof.json').read_bytes());assert d['cases']['two_workers']['pair_equal']and d['cases']['two_workers']['B']['status']=='rejected'and d['cases']['two_workers']['prior_revision_in_retry_history'];assert d['cases']['interrupted']['pair_equal_after_retry']and d['cases']['interrupted']['owner_note_same'];assert d['cases']['late_old_review']['new_bytes_preserved']
  (product/'candidate-build').mkdir();compiler=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe';run([compiler,'/nologo','/target:winexe','/main:LocalEntry','/out:'+str(product/'candidate-build/wrapper.exe'),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll',*sorted((product/'ResearchLocal').glob('*.cs'))]);run([compiler,'/nologo','/out:'+str(home/'probe.exe'),P/'harness/reveng/RevisionPublicationProbe.cs']);run([home/'probe.exe',product/'candidate-build/wrapper.exe',home/'races/interrupted']);print('PASS real offline queue races / interrupted publication / wrapper compile; no GUI or legacy EXE')
  outcome_root=home/'native-presentation';outcome_root.mkdir();outcome_root=outcome_root.resolve()
  run([compiler,'/nologo','/target:exe','/main:TestOutcome','/out:'+str(product/'candidate-build/TestOutcome.exe'),'/r:'+str(product/'candidate-build/wrapper.exe'),'/r:System.Web.Extensions.dll',P.parents[1]/'reveng/tests/TestOutcome.cs'])
  outcome=run([product/'candidate-build/TestOutcome.exe',outcome_root]);assert 'TOTAL 40 SYNTHETIC presentation checks' in outcome,'Native outcome assertion count missing'
else:
 run([sys.executable,'-X','utf8','-I','-B','-m','unittest','discover','-s',P.parents[1]/'forge/tests','-p','test_release_packaging.py','-v'])
 # Use an owned portable copy so test receipts never enter shipped source.
 lab=home/'forge-lab';shutil.copytree(P/'harness/forge',lab/'harness/forge');shutil.copytree(P/'fixtures/forge',lab/'fixtures/forge');shutil.copytree(product,lab/'production/forgeAlphaZero')
 shell=shutil.which('pwsh');assert shell,'PowerShell7.5+ required'
 run([shell,'-NoLogo','-NoProfile','-NonInteractive','-Command',"if($PSVersionTable.PSVersion -lt [version]'7.5'){throw 'PowerShell7.5+ required'}"])
 for name in ['Test-AlphaZero.ps1','Test-AlphaZeroHandler.ps1','Test-CausalContract.ps1']:run([shell,'-NoLogo','-NoProfile','-NonInteractive','-File',lab/'harness/forge'/name])
for name,h in pins['files'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h
print('PASS',project,'pinned source unchanged; output remains in owned temp root')


run([sys.executable,"-I","-B",P/"harness/offline_regressions.py",project,product,home/"regressions"])

if project=='reveng028':
 run([sys.executable,'-X','utf8','-I','-B',P.parents[1]/'reveng/tests/test_researchlocal_offline.py','--source',product/'ResearchLocal','--include-existing-tests'])
 run([sys.executable,'-X','utf8','-I','-B',P.parents[1]/'reveng/tests/test_identity_portable.py',product/'ResearchLocal'])
 run([sys.executable,'-X','utf8','-I','-B',P.parents[1]/'reveng/tests/test_capability_portable.py','--source',product/'ResearchLocal'])
 from reveng_followon import main as run_reveng_followon;run_reveng_followon([str(product)])
 verify_researchlocal(P.parents[1])
 print('PASS canonical ResearchLocal verified unchanged; historical snapshot was not executed')

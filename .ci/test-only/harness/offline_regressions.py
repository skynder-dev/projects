"""Dispatch existing bounded regressions in owned roots; never execute models."""
from pathlib import Path
import sys,os,json,subprocess,shutil
project=sys.argv[1];src=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
out.mkdir(parents=True,exist_ok=False);h=Path(__file__).resolve().parent;r=h/'regressions'
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',timeout=75,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 (out/('step-'+str(len(list(out.glob('step-*.log'))))+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
 assert p.returncode==0,(args,p.returncode,p.stdout[-2000:],p.stderr[-2000:])
if project=='forgeAlphaZero':
 shell=shutil.which('pwsh');assert shell,'PowerShell7.5+ required'
 run([shell,'-NoLogo','-NoProfile','-NonInteractive','-Command',"if($PSVersionTable.PSVersion -lt [version]'7.5'){throw 'PowerShell7.5+ required'}"])
 run([shell,'-NoLogo','-NoProfile','-NonInteractive','-File',r/'forge_fidelity.ps1','-Candidate',src,'-Output',out/'fidelity.json'])
 run([shell,'-NoLogo','-NoProfile','-NonInteractive','-File',r/'forge_unsaved.ps1','-Candidate',src,'-Root',out/'unsaved'])
elif project=='social246':
 node=shutil.which('node');assert node,'Existing Node.js required'
 run([node,r/'social_matrix.js','--source',src/'app/local_binding.js','--out',out/'matrix'])
 s=json.loads((out/'matrix/SUMMARY.json').read_bytes());assert s['scenarios']==129 and s['violatingScenarios']==0 and not s['scenarioErrors']
elif project=='reveng028':
 for test in ['reveng_owner.py','reveng_nested.py']:
  run([sys.executable,'-X','utf8','-I','-B',h/'guard.py',r/test,src/'ResearchLocal',out])
 run([sys.executable,'-X','utf8','-I','-B',r/'reveng_parity.py',src/'ResearchLocal',out])
else:raise ValueError('Unknown project')
(out/'RESULT.json').write_text(json.dumps({'project':project,'status':'PASS','models':0,'network':0,'scope':'Existing offline mechanical regressions; no model or native UI quality claim'},indent=2),encoding='utf-8')
print('PASS additional offline regressions',project)

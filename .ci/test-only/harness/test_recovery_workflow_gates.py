"""Local static tests, not an Actions execution or a new-product qualification.
Requires PyYAML in the review environment; never installs dependencies.
"""
from pathlib import Path
import ast,hashlib,json,re,tempfile,unittest
import yaml
ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'.ci/test-only'
BASE=json.loads((P/'fixtures/recovery_workflow_baseline.json').read_bytes())
BRANCH=BASE['branch']

class UniqueLoader(yaml.BaseLoader):
 pass
def mapping(loader,node):
 pairs=loader.construct_pairs(node)
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('Duplicate YAML key: '+key)
  result[key]=value
 return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
def parse(text):return yaml.load(text,Loader=UniqueLoader)
def workflow_paths(root):
 return {p.relative_to(root).as_posix() for p in (root/'.github/workflows').iterdir() if p.is_file() and p.suffix in {'.yml','.yaml'}}

# ASCII case variants of this fixed ASCII recovery name follow GitHub's
# case-insensitive comparison boundary; this is not a general expression VM.
CONCURRENCY="${{ (github.ref == 'refs/heads/"+BRANCH+"' || github.head_ref == '"+BRANCH+"') && format('social-reel-recovery-{0}-{1}', github.run_id, github.run_attempt) || 'social-reel' }}"
def concurrency_group(expression,ref,head='',run_id='123',run_attempt='1'):
 if expression != CONCURRENCY:raise ValueError('Unsupported concurrency expression')
 recovery=ref.lower()==('refs/heads/'+BRANCH).lower() or head.lower()==BRANCH.lower()
 return 'social-reel-recovery-'+run_id+'-'+run_attempt if recovery else 'social-reel'

def evaluate(expression,ref,head='',success=True):
 """Evaluate only the emitted, closed expression grammar; never eval workflow code."""
 expression=expression.strip()
 if expression.startswith('${{') and expression.endswith('}}'):expression=expression[3:-2].strip()
 pattern=r"github\.ref != '([^']+)' && github\.head_ref != '([^']+)' && \((success|always)\(\)\)"
 match=re.fullmatch(pattern,expression)
 if not match:raise ValueError('Unsupported guard expression')
 excluded_ref,excluded_head,status=match.groups()
 return ref.lower()!=excluded_ref.lower() and head.lower()!=excluded_head.lower() and (status=='always' or success)

class RecoveryGates(unittest.TestCase):
 def test_exact_workflow_set_and_no_yaml_ambiguity(self):
  paths=workflow_paths(ROOT)
  self.assertEqual(paths,{x['path'] for x in BASE['workflows']})
  self.assertEqual(len(paths),19)
  for row in BASE['workflows']:
   document=parse((ROOT/row['path']).read_text(encoding='utf-8'))
   self.assertIn('on',document);self.assertIn('jobs',document)
   self.assertTrue(set(document['on'])<= {'push','pull_request','workflow_dispatch'})

 def test_only_guards_changed_and_offline_suites_untouched(self):
  for row in BASE['workflows']:
   with self.subTest(path=row['path']):
    raw=(ROOT/row['path']).read_bytes();s=raw.decode();document=parse(s)
    s=s.replace("'social/socialreel/**', 'social/tests/**', 'social/CONCEPT_CORE_OFFLINE.md', '.ci/tests/**', ", '')
    s=s.replace("'forge/tests/**', 'forge/tools/build_release.py', ", '')
    s=s.replace("'reveng/ResearchLocal/**', 'reveng/tests/**', 'reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json', ", '')
    if row['eligible_offline']:
     self.assertEqual(document['permissions']['contents'],'read')
     self.assertNotIn('secrets.',s)
     self.assertNotIn('git push',s)
     if row['path']=='.github/workflows/test-only-reveng028.yml':
      # Restore only the three reviewed hosted-check edits to prove all other
      # baseline workflow behavior and permissions remain byte-identical.
      restored=s.replace("'.github/workflows/*.yml', '.github/workflows/*.yaml'", "'.github/workflows/test-only-*.yml'")
      restored=restored.replace('      - run: python -m pip install --only-binary=PyYAML --no-deps PyYAML==6.0.3\r\n','')
      restored=restored.replace('      - run: python -B .ci/test-only/harness/test_recovery_workflow_gates.py\r\n','')
      self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),row['sha256'])
     elif row['path']=='.github/workflows/test-only-social246.yml':
      restored=s.replace('      - run: python -m pip install --only-binary=pypdf --no-deps pypdf==6.10.0\r\n','')
      restored=restored.replace('      - run: python -X utf8 -I -B .ci/test-only/harness/guard.py .ci/tests/run_social_concept_core.py\r\n      - name: Verify canonical sources after concept tests\r\n        run: python -B .ci/test-only/harness/verify_files.py\r\n','')
      self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),row['sha256'])
     else:self.assertEqual(hashlib.sha256(s.encode()).hexdigest(),row['sha256'])
     continue
    self.assertEqual(set(document['jobs']),set(row['jobs']))
    for job,item in row['jobs'].items():
     self.assertEqual(s.count(item['guard_line']),sum(x['guard_line']==item['guard_line'] for x in row['jobs'].values()))
    # Restore each job's one modified/inserted line in reverse order, preserving CRLF.
    lines=s.splitlines(keepends=True);start=lines.index('jobs:\n') if 'jobs:\n' in lines else lines.index('jobs:\r\n')
    indices=[i for i in range(start+1,len(lines)) if re.match(r'^  [A-Za-z_][A-Za-z0-9_-]*:\s*$',lines[i].rstrip('\r\n'))]
    for ix,i in reversed(list(enumerate(indices))):
     end=indices[ix+1] if ix+1<len(indices) else len(lines);job=lines[i].strip()[:-1];item=row['jobs'][job]
     guards=[j for j in range(i+1,end) if lines[j]==item['guard_line']];self.assertEqual(len(guards),1)
     if item['original_if_line'] is None:lines.pop(guards[0])
     else:lines[guards[0]]=item['original_if_line']
    restored=''.join(lines)
    if row['path']=='.github/workflows/social-reel.yml':
     self.assertEqual(document['concurrency'],{'group':CONCURRENCY,'cancel-in-progress':'false'})
     restored=restored.replace('  group: '+CONCURRENCY,'  group: social-reel')
    self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),row['sha256'])

 def test_push_pull_request_and_manual_recovery_all_jobs_ineligible(self):
  cases=[('push','refs/heads/'+BRANCH,''),('workflow_dispatch','refs/heads/'+BRANCH,''),('pull_request','refs/pull/123/merge',BRANCH),('pull_request_target','refs/heads/main',BRANCH)]
  for variant in [BRANCH.upper(),'CI/github-CORE-20261022']:
   cases.extend([('push','refs/heads/'+variant,''),('workflow_dispatch','refs/heads/'+variant,''),('pull_request','refs/pull/123/merge',variant)])
  count=0
  for row in BASE['workflows']:
   if row['eligible_offline']:continue
   jobs=parse((ROOT/row['path']).read_text(encoding='utf-8'))['jobs']
   for job,item in row['jobs'].items():
    count+=1
    for event,ref,head in cases:
     for status in [True,False]:
      with self.subTest(workflow=row['path'],job=job,event=event,status=status):
       self.assertFalse(evaluate(jobs[job]['if'],ref,head,status))
  self.assertEqual(count,19)

 def test_unrelated_refs_preserve_success_and_always_semantics(self):
  cases=[('refs/heads/main',''),('refs/heads/other',''),('refs/pull/1/merge','unrelated'),('refs/heads/'+BRANCH+'-other',''),('refs/tags/v1','')]
  for row in BASE['workflows']:
   if row['eligible_offline']:continue
   jobs=parse((ROOT/row['path']).read_text(encoding='utf-8'))['jobs']
   for job,item in row['jobs'].items():
    for ref,head in cases:
     for success in [True,False]:
      expected=True if item['original_condition']=='always()' else success
      self.assertEqual(evaluate(jobs[job]['if'],ref,head,success),expected)

 def test_original_conditions_and_historical_source_pins_immutable(self):
  # These remain historical source pins, not evidence that canonical recovery is done.
  self.assertEqual(set(BASE.get('reviewed_canonical_integration',{})),{'.ci/test-only/harness/run.py'})
  for name,digest in BASE['immutable_baseline_files'].items():
   update=BASE.get('reviewed_canonical_integration',{}).get(name)
   if update:
    self.assertEqual(update['original_sha256'],digest);digest=update['sha256']
   self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
  pins=json.loads((P/'CANDIDATE_PINS.json').read_bytes())
  for project,values in pins.items():
   for name,digest in values['files'].items():
    with self.subTest(project=project,path=name):self.assertEqual(hashlib.sha256((P/name).read_bytes()).hexdigest(),digest)
  self.assertEqual(sum(item['original_condition']=='always()' for row in BASE['workflows'] for item in row['jobs'].values()),2)

 def test_social_concurrency_isolates_recovery_without_changing_other_refs(self):
  expression=parse((ROOT/'.github/workflows/social-reel.yml').read_text(encoding='utf-8'))['concurrency']['group']
  for variant in [BRANCH,BRANCH.upper(),'CI/github-CORE-20261022']:
   for ref,head in [('refs/heads/'+variant,''),('refs/pull/123/merge',variant)]:
    self.assertEqual(concurrency_group(expression,ref,head),'social-reel-recovery-123-1')
    self.assertNotEqual(concurrency_group(expression,ref,head,run_id='124'),'social-reel-recovery-123-1')
    self.assertNotEqual(concurrency_group(expression,ref,head,run_attempt='2'),'social-reel-recovery-123-1')
  for ref,head in [('refs/heads/main',''),('refs/heads/social/topic',''),('refs/heads/'+BRANCH+'-other',''),('refs/pull/3/merge','unrelated')]:
   self.assertEqual(concurrency_group(expression,ref,head),'social-reel')
  with self.assertRaises(ValueError):concurrency_group('social-reel','refs/heads/'+BRANCH)

 def test_yaml_extension_cannot_escape_inventory(self):
  # Synthetic fixture only; do not mutate the candidate or historical sources.
  with tempfile.TemporaryDirectory(prefix='workflow-inventory-') as tmp:
   root=Path(tmp);directory=root/'.github/workflows';directory.mkdir(parents=True)
   (directory/'safe.yml').write_text('jobs: {}\n',encoding='utf-8')
   expected={'.github/workflows/safe.yml'}
   self.assertEqual(workflow_paths(root),expected)
   (directory/'escape.yaml').write_text('jobs: {}\n',encoding='utf-8')
   self.assertNotEqual(workflow_paths(root),expected)
   self.assertIn('.github/workflows/escape.yaml',workflow_paths(root))

 def test_hosted_guard_is_required_and_uses_real_checkout(self):
  document=parse((ROOT/'.github/workflows/test-only-reveng028.yml').read_text(encoding='utf-8'))
  job=document['jobs']['offline'];self.assertNotIn('if',job)
  self.assertNotIn('continue-on-error',job)
  self.assertEqual(document['permissions'],{'contents':'read'})
  steps=job['steps'];commands=[step.get('run') for step in steps]
  command='python -B .ci/test-only/harness/test_recovery_workflow_gates.py'
  dependency='python -m pip install --only-binary=PyYAML --no-deps PyYAML==6.0.3'
  self.assertEqual(commands.count(command),1);self.assertEqual(commands.count(dependency),1)
  self.assertLess(commands.index(dependency),commands.index(command))
  self.assertLess(commands.index('python -B .ci/test-only/harness/verify_files.py'),commands.index(command))
  step=steps[commands.index(command)]
  self.assertEqual(step,{'run':command})  # no skip, alternate cwd, or failure suppression
  checkout=steps[0]
  self.assertEqual(checkout['uses'],'actions/checkout@v4')
  self.assertEqual(checkout['with'],{'persist-credentials':'false','ref':'${{ github.event.pull_request.head.sha || github.sha }}'})

 def test_workflow_text_io_is_explicit_utf8(self):
  # Windows locale defaults must not govern UTF-8 repository workflow decoding.
  tree=ast.parse(Path(__file__).read_bytes())
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in {'read_text','write_text'}:
    encoding=next((kw.value for kw in node.keywords if kw.arg=='encoding'),None)
    self.assertIsInstance(encoding,ast.Constant)
    self.assertEqual(encoding.value,'utf-8')
  with tempfile.TemporaryDirectory(prefix='workflow-utf8-') as tmp:
   fixture=Path(tmp)/'unicode.yaml'
   fixture.write_bytes('name: synthetic-Ж\njobs: {}\n'.encode('utf-8'))
   self.assertEqual(parse(fixture.read_text(encoding='utf-8'))['name'],'synthetic-Ж')

 def test_social_canonical_check_is_mandatory(self):
  job=parse((ROOT/'.github/workflows/test-only-social246.yml').read_text(encoding='utf-8'))['jobs']['offline']
  self.assertNotIn('if',job);self.assertNotIn('continue-on-error',job)
  steps=job['steps'];commands=[step.get('run') for step in steps]
  dependency='python -m pip install --only-binary=pypdf --no-deps pypdf==6.10.0'
  command='python -X utf8 -I -B .ci/test-only/harness/guard.py .ci/tests/run_social_concept_core.py'
  self.assertEqual(commands.count(dependency),1);self.assertEqual(commands.count(command),1)
  self.assertLess(commands.index(dependency),commands.index(command))
  self.assertEqual(steps[commands.index(command)],{'run':command})
  self.assertEqual(steps[commands.index(command)+1],{'name':'Verify canonical sources after concept tests','run':'python -B .ci/test-only/harness/verify_files.py'})

 def test_guard_mutations_rejected(self):
  sample=next(item['guard_line'].split('if:',1)[1].strip() for row in BASE['workflows'] for item in row['jobs'].values())
  for broken in [sample.replace(' && ',' || ',1),sample.replace("github.head_ref !=",'github.head_ref =='),sample.replace('always()', 'cancelled()') if 'always()' in sample else sample.replace('success()', 'cancelled()')]:
   with self.assertRaises(ValueError):evaluate(broken,'refs/heads/'+BRANCH)
  self.assertTrue(evaluate(sample.replace('refs/heads/'+BRANCH,'refs/heads/wrong').replace("'"+BRANCH+"'","'wrong'"),'refs/heads/'+BRANCH))

if __name__=='__main__':unittest.main(verbosity=2)

"""CI orchestration contracts only; native execution is a separate mandatory hosted step."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,os,shutil,sys,tempfile,unittest
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args();SOURCE=args.source.resolve();REPO=Path(__file__).resolve().parents[2];HARNESS=REPO/'.ci/test-only/harness';sys.dont_write_bytecode=True;sys.path.insert(0,str(HARNESS))
spec=importlib.util.spec_from_file_location('reveng_followon_contract',HARNESS/'reveng_followon.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class IntegratedCIContracts(unittest.TestCase):
 def test_full_plan_invokes_every_actual_suite_normal_and_optimized_under_guard(self):
  commands=runner.python_commands(REPO,SOURCE.parent);self.assertEqual(len(commands),2*len(runner.SUITES))
  for script,extra in runner.SUITES:
   entries=[command for _,command in commands if str(REPO/'reveng/tests'/script) in command];self.assertEqual(len(entries),2,script);self.assertEqual(sum('-O' in c for c in entries),1)
   for command in entries:
    self.assertEqual(command[:5],[sys.executable,'-X','utf8','-I','-B']);self.assertIn(str(HARNESS/'guard.py'),command);self.assertIn(str(SOURCE),command)
  self.assertTrue({'test_collection_integrity.py','test_answer_cache_integrity.py','test_price_cache_integrity.py','test_saved_analysis_context.py','test_owner_preference_overlay.py'}<={x[0] for x in runner.SUITES})
 def test_native_plan_compiles_and_runs_actual_application_bound_probes(self):
  product=SOURCE.parent;commands=runner.native_commands(REPO,product);self.assertEqual(len(commands),8)
  for index,name in [(0,'TestPriceExperimentPresentation'),(2,'TestOwnerPreferencePresentation'),(4,'TestPortableRuntimeDrain'),(6,'TestOperationOutcome')]:
   compile_command=commands[index][1];execute_command=commands[index+1][1];self.assertIn('/main:'+name,compile_command);self.assertIn('/r:'+str(product/'candidate-build/wrapper.exe'),compile_command);self.assertIn(str(REPO/'reveng/tests'/(name+'.cs')),compile_command);self.assertEqual(execute_command[0],str(product/'candidate-build'/(name+'.exe')))
  self.assertEqual(commands[1][1][1],str(REPO/'reveng/tests/price_ui_vectors.json'));self.assertEqual(len(commands[3][1]),1);self.assertEqual(len(commands[5][1]),1);self.assertEqual(len(commands[7][1]),1)
 def test_shared_runner_change_is_only_one_reveng_guarded_invocation(self):
  raw=(HARNESS/'run.py').read_bytes();hook=b" from reveng_followon import main as run_reveng_followon;run_reveng_followon([str(product)])\r\n";self.assertEqual(raw.count(hook),1)
  self.assertEqual(hashlib.sha256(raw.replace(hook,b'')).hexdigest(),'0a1bf377d64d4a3def4f660f468cdcb78bae3f91c7c6b8bcab948e9fe56ee099')
  tree=ast.parse(raw);guard=next(node for node in tree.body if isinstance(node,ast.If) and any(isinstance(x,ast.ImportFrom) and x.module=='reveng_followon' for x in ast.walk(node)))
  self.assertEqual(ast.dump(guard.test),ast.dump(ast.parse("project=='reveng028'",mode='eval').body));self.assertNotIn('--local-stdlib-only',raw.decode())
 def test_partial_local_mode_omits_only_unavailable_api_suite_and_is_forbidden_in_actions(self):
  commands=runner.python_commands(REPO,SOURCE.parent,local_stdlib_only=True);self.assertEqual(len(commands),2*(len(runner.SUITES)-1));self.assertFalse(any('test_capability_portable.py' in ' '.join(c) for _,c in commands))
  with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),self.assertRaisesRegex(ValueError,'Partial local mode is forbidden'):runner.main([str(SOURCE.parent),'--local-stdlib-only'])
 def test_actual_owned_source_validation_rejects_tamper(self):
  with tempfile.TemporaryDirectory(prefix='reveng-ci-owned-contract-') as temporary:
   product=Path(temporary);shutil.copytree(SOURCE,product/'ResearchLocal');self.assertEqual(runner.verify_owned(REPO,product),product/'ResearchLocal');path=product/'ResearchLocal/observation_history.py';path.write_bytes(path.read_bytes()+b'\n# SYNTHETIC tamper\n')
   with self.assertRaisesRegex(ValueError,'Owned source differs'):runner.verify_owned(REPO,product)
class RuntimeSourceContracts(unittest.TestCase):
 # Static source assertions only. Actual C# probe is mandatory in native plan,
 # but no C# execution or process-lifecycle qualification is inferred here.
 def text(self,name):return (SOURCE/name).read_text(encoding='utf-8-sig')
 def test_bounded_drain_checks_completion_before_result_and_never_waits_infinitely(self):
  source=self.text('PortableRuntime.cs');drain=source.split('public static string[] DrainOutput(',1)[1].split('static void ObserveFailure',1)[0]
  self.assertIn('if(!Task.WaitAll(new Task[]{output,error},timeout))throw new TimeoutException',drain);self.assertLess(drain.index('Task.WaitAll'),drain.index('output.Result'));self.assertIn('if(timeout<0)',drain);self.assertIn('.ConfigureAwait(false)',source);self.assertNotIn('ReadToEndAsync()',source)
 def test_capture_limit_preserves_largest_existing_receipt_contract(self):
  source=self.text('PortableRuntime.cs');self.assertIn('MaxCapturedCharacters=8388608',source);self.assertIn('UTF-16 characters',source)
  for name in ['SourceLedgerComparison.cs','ArchivePreview.cs']:self.assertIn('MaxJsonLength=8388608',self.text(name))
  self.assertIn('count>limit-text.Length',source);self.assertIn('throw new InvalidDataException',source)
 def test_cleanup_only_uses_owned_process_and_bounded_exit_confirmation(self):
  source=self.text('PortableRuntime.cs');self.assertEqual(source.count('process.Kill()'),1);self.assertIn('process.WaitForExit(CleanupTimeoutMilliseconds)',source);self.assertIn('CleanupTimeoutMilliseconds=1000',source);self.assertIn('ObserveFailure(output);ObserveFailure(error)',source);self.assertIn('CloseOwnedHandles(outputReader,errorReader,process,CleanupTimeoutMilliseconds)',source);self.assertIn('Task.Run(()=>owned.Dispose())',source);self.assertNotIn('using(var process=',source)
  for forbidden in ['Process.GetProcesses','GetProcessById','taskkill','Kill(true)','WaitForExit()']:self.assertNotIn(forbidden,source)
  run=source.split('public static string Run(',1)[1].split('public static bool Check(',1)[0];self.assertIn('throw new CompletionUnconfirmedException',run);self.assertIn('if(exitCode!=0)throw new InvalidOperationException',run);self.assertNotIn('receiptComplete',run)
 def test_all_six_mutating_callers_use_uncertain_message_and_proposal_is_retained(self):
  for name,prefix in [('RevEngLocalResearch.cs','Экспорт не выполнен: '),('EvidenceComparison.cs','Ревью не записано: '),('EvidenceComparison.cs','Экспорт идеи не выполнен: '),('SourceLedgerComparison.cs','Response was NOT imported: '),('SourceLedgerComparison.cs','Цитата не сохранена: '),('SourceLedgerComparison.cs','Источник/реестр не загружен: ')]:
   self.assertIn('"'+prefix+'"',self.text(name));self.assertIn('PortableRuntime.FailureMessage(ex,',self.text(name))
  source=self.text('SourceLedgerComparison.cs');self.assertIn('completionUnconfirmed=outcome==null&&(helperReturned||ex is PortableRuntime.CompletionUnconfirmedException)',source);self.assertIn('CleanupProposal(file,completionUnconfirmed,File.Delete)',source);self.assertIn('if(retain)return',source)
 def test_real_probe_is_in_process_not_a_substitute_or_tool_launch(self):
  probe=(REPO/'reveng/tests/TestPortableRuntimeDrain.cs').read_text();self.assertIn('PortableRuntime.ReadBoundedAsync(new NeverReader()',probe);self.assertIn('PortableRuntime.DrainOutput(',probe);self.assertIn('TaskCompletionSource<string>',probe)
  for forbidden in ['Process.Start','PortableRuntime.Run(','new Form(','new UserControl(','Task.Delay(']:self.assertNotIn(forbidden,probe)

class OperationOutcomeSourceContracts(unittest.TestCase):
 # Source/call-order checks, never native/UI execution.
 def text(self,name):return (SOURCE/name).read_text(encoding='utf-8-sig')
 def test_helper_return_is_marked_before_receipt_parsing(self):
  ledger=self.text('SourceLedgerComparison.cs');self.assertIn('helperReturned=true;bool imported;outcome=DescribeImportResult',ledger);self.assertIn('helperReturned=true;outcome=DescribeQuoteSaveResult',ledger);self.assertIn('rebuild&&helperReturned',ledger)
  review=self.text('EvidenceComparison.cs');self.assertIn('helperReturned=true;outcome=DescribeReviewResult',review)
  export=self.text('RevEngLocalResearch.cs');self.assertIn('helperReturned=true;{var result=new JavaScriptSerializer()',export);self.assertIn('DescribeExportFailure(ex,helperReturned,output)',export);self.assertIn('outcome!=null?WithExportDisplayWarning(outcome,ex.Message)',export);self.assertLess(export.index('outcome="Экспорт подтверждён квитанцией'),export.index('reportMessage.Text=outcome;'))
 def test_validated_outcomes_survive_refresh_warning(self):
  ledger=self.text('SourceLedgerComparison.cs');self.assertIn('string LoadData(bool rebuild)',ledger);self.assertIn('status.Text=WithRefreshWarning(outcome,warning)',ledger);self.assertIn('message=WithRefreshWarning(outcome,LoadData(false))',ledger);self.assertIn('outcome!=null?WithRefreshWarning(outcome,ex.Message)',ledger)
  review=self.text('EvidenceComparison.cs');self.assertIn('status.Text=WithReviewRefreshWarning(outcome,Rebuild())',review);self.assertIn('string Rebuild()',review);self.assertIn('return Reload()',review);self.assertIn('string Reload()',review)
 def test_staging_cleanup_is_contained_one_attempt_without_finally_delete(self):
  source=self.text('SourceLedgerComparison.cs');cleanup=source.split('public static string CleanupProposal(',1)[1].split('void ImportSaved()',1)[0];self.assertEqual(cleanup.count('remove(file)'),1);self.assertIn('catch(IOException',cleanup);self.assertIn('catch(UnauthorizedAccessException',cleanup);self.assertNotIn('finally{if(',source);self.assertIn('status.Text=message+(String.IsNullOrEmpty(cleanup)',source)
 def test_actual_native_probe_covers_saved_rejected_unknown_and_cleanup_without_forms(self):
  probe=(REPO/'reveng/tests/TestOperationOutcome.cs').read_text();self.assertIn('SourceLedgerComparison.DescribeImportResult(',probe);self.assertIn('REJECTED_RESPONSE_NOT_IMPORTED',probe);self.assertIn('EvidenceComparison.DescribeReviewResult(',probe);self.assertIn('LocalResearchController.DescribeExportFailure(',probe);self.assertIn('SourceLedgerComparison.CleanupProposal(',probe)
  for forbidden in ['new Form(','new SourceLedgerComparison(','Process.Start','PortableRuntime.Run(']:self.assertNotIn(forbidden,probe)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)

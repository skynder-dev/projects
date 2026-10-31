"""Source/preservation/wiring checks only: not PowerShell syntax or behavior execution."""
import hashlib,json,re,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
APP=HERE.parents[1]/'app/Merch_Forge_A5_Current'
def text(path):return path.read_text(encoding='utf-8-sig')
DRAFT=text(APP/'Modules/Forge.ResearchDrafts.ps1');CORE=text(APP/'Modules/Forge.LocalCore.ps1');WB=text(APP/'MerchForgeWorkbench.ps1')
def fn(source,name):
 m=re.search(r'^function '+re.escape(name)+r'\b',source,re.M)
 assert m,name
 n=re.search(r'^function ',source[m.end():],re.M)
 return source[m.start():m.end()+n.start() if n else len(source)]
class HistorySalesStatic(unittest.TestCase):
 def test_history_is_reachable_and_uses_real_saved_rows(self):
  op=fn(DRAFT,'Open-ResearchDraftItem');route=fn(DRAFT,'Enter-ResearchDraftSection')
  self.assertIn("@('edit','history')",route);self.assertIn('revisions=@(Get-ResearchDraftHistory $d)',op);self.assertIn('$RevisionList.ItemsSource=$script:Current.revisions',op);self.assertIn('Load-AuditHistory $key',op)
  self.assertIn('$RestoreRevisionButton.Add_Click({if(Test-CurrentIsResearchDraft){Restore-SelectedResearchDraftRevision;return}',WB)
 def test_history_clone_preserves_strings_and_does_not_decorate_source(self):
  history=fn(DRAFT,'Get-ResearchDraftHistory');self.assertIn('ConvertFrom-Json -DateKind String',history);self.assertIn('-Depth 60',history);self.assertNotIn('Add-OrSetProperty $revision',history)
 def test_restore_cancellation_and_stale_checks_precede_editor_mutation(self):
  source=fn(DRAFT,'Restore-SelectedResearchDraftRevision');first=source.index('$TitleBox.Text=')
  for token in ('if(!(Confirm $question)){return}','Get-ResearchDraftRestoreSource','revision_hash-cne$sourceHash','ConvertTo-ForgeBriefCanonicalJson'):self.assertLess(source.index(token),first)
  self.assertNotIn('Write-LocalCoreState',source);self.assertNotIn('Invoke-ForgeApi',source)
 def test_save_appends_and_binds_source_without_approval_copy(self):
  source=fn(DRAFT,'Save-ResearchDraftRevision');self.assertIn("@(Get-PropertyValue $d 'revisions')+@($rev)",source);self.assertIn("'source_revision_id' $SourceRevisionId",source)
  self.assertIn("$null-eq$restoreSource-and$newHash",source);self.assertIn('Get-ResearchDraftRestoreSource $d',source)
 def test_atomic_authority_reset_precedes_single_state_commit(self):
  source=fn(DRAFT,'Save-ResearchDraftRevision');commit=source.index('Write-LocalCoreState $s');preserve=source.index('Preserve-ForgeLocalReviewHistory')
  for token in ("'brief_approval' $null","'active_acceptance' $null","'accepted' $false","'owner_decision' 'UNDECIDED'","'publication' $null",'New-LocalCoreChecks $rev.revision_id','Invalidate-LocalCorePackages'):
   self.assertLess(preserve,source.index(token));self.assertLess(source.index(token),commit)
  self.assertEqual(1,source.count('Write-LocalCoreState'));self.assertNotIn('Remove-Item',source)
 def test_save_failure_keeps_publication_dirty(self):
  source=fn(DRAFT,'Save-CurrentResearchDraftRevision');self.assertLess(source.index('$committed=$true'),source.index('Set-PublicationDirty $false'))
 def test_sales_keeps_identity_and_uses_compound_receipt_keys(self):
  source=fn(CORE,'Import-LocalSalesCsvFromPath');snapshot=fn(CORE,'Get-ForgeSalesNormalizationSnapshot')
  for token in ('channel_raw','marketplace_raw','identity_contract'):self.assertIn(token,source);self.assertIn(token,snapshot)
  reconcile=fn(CORE,'Reconcile-LocalSalesLinks');self.assertIn('$exact=Get-LocalPublicationProductKey $row',reconcile);self.assertIn('$candidates.Count-eq1',reconcile);self.assertIn('$conflicts.ContainsKey',reconcile)
  self.assertNotIn("Get-PropertyValue $row 'currency'",reconcile)
 def test_explicit_wrong_dimensions_are_not_fallbacks(self):
  source=fn(CORE,'Reconcile-LocalSalesLinks');self.assertIn('if($channel-and$market)',source);self.assertIn('$channel-cne',source);self.assertIn('$market-cne',source)
  overlap=fn(CORE,'Get-LocalSalesOverlapSummary');self.assertIn('$_.marketplace-ceq$marketplace',overlap);self.assertIn('$_.channel-ceq$channel',overlap)
 def test_native_suite_loads_actual_ast_and_is_explicitly_bounded(self):
  source=text(HERE/'Test-ForgeHistoryAndSales.ps1');self.assertIn('Parser]::ParseFile',source);self.assertIn('. ([scriptblock]::Create($matches[0].Extent.Text))',source);self.assertIn('$sourceAfter',source);self.assertIn('DateKind String',source)
  self.assertNotIn('.ShowDialog(',source);self.assertNotIn('.Show(',source)
 def test_native_pins_and_identity_lists_match(self):
  pins=json.loads(text(HERE/'HistorySalesPins.json'));deps=json.loads(text(HERE/'HistorySalesDependencies.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for path,digest in pins['sources'].items():self.assertEqual(digest,sha(APP/path))
  for path,digest in pins['tests'].items():self.assertEqual(digest,sha(HERE/path))
  self.assertEqual(pins['expected_function_names'],[name for names in deps['functions'].values() for name in names]);self.assertEqual(pins['expected_case_names'],re.findall(r"^        Test-Case '([^']+)'",text(HERE/'Test-ForgeHistoryAndSales.ps1'),re.M))
  self.assertEqual(len(pins['expected_case_names']),len(set(pins['expected_case_names'])))
if __name__=='__main__':unittest.main()

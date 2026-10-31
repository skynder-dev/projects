"""Static source, call-order and identity checks only; not PowerShell parsing/runtime."""
from pathlib import Path
import hashlib,json,re,unittest
HERE=Path(__file__).resolve().parent;APP=HERE.parents[1]/'app/Merch_Forge_A5_Current'
def text(p):return p.read_text(encoding='utf-8-sig')
def fn(s,n):
 m=re.search(r'^function '+re.escape(n)+r'\b',s,re.M)
 if m is None:raise ValueError(n)
 nxt=re.search(r'^function |^\$script:AutoDataCopyEnabled',s[m.end():],re.M)
 return s[m.start():m.end()+nxt.start() if nxt else len(s)]
BACK=text(APP/'Modules/Forge.DataBackup.ps1');CORE=text(APP/'Modules/Forge.LocalCore.ps1');WB=text(APP/'MerchForgeWorkbench.ps1');AUTO=text(APP/'MerchForgeAutoDataCopy.ps1')
INSTALL=fn(BACK,'Install-BackupStage');RESTORE=fn(BACK,'Restore-ForgeDataBackupFromPath');CAPTURE=fn(BACK,'New-ForgeDataBackup');WRITER=fn(CORE,'Write-LocalCoreState')
class BackupStatic(unittest.TestCase):
 def test_both_current_tokens_rebased_under_same_lock_before_assets(self):
  for token in ("Add-OrSetProperty $st 'state_revision' ([int64](Get-PropertyValue $cur 'state_revision'))","Add-OrSetProperty $st 'last_write_id' ([string](Get-PropertyValue $cur 'last_write_id'))"):
   self.assertLess(INSTALL.index('Enter-LocalCoreMutationLock'),INSTALL.index(token));self.assertLess(INSTALL.index(token),INSTALL.index('New-LocalCoreRestoreContext'))
  self.assertIn('Write-LocalCoreState $st -MutationLock $MutationLock -RestoreContext $restoreContext',INSTALL)
  self.assertNotIn('Read-LocalCoreState;',INSTALL)
 def test_normal_writer_fences_remain_and_pending_guard_is_inside_lock(self):
  for token in ('$diskRev-eq$expectedRev-and[string](Get-PropertyValue $disk \'last_write_id\')-cne$expectedWriteId','$diskRev-ne$expectedRev','Assert-LocalCoreRestoreContext $RestoreContext $State $MutationLock','[IO.File]::Replace($tmp,$script:LocalCoreStatePath,$backupTmp,$true)'):self.assertIn(token,WRITER)
  self.assertLess(WRITER.index('Assert-LocalCoreMutationLock $MutationLock'),WRITER.index('Assert-LocalCoreDataRestoreAvailable $RestoreContext'))
  self.assertIn('Assert-LocalCoreDataRestoreAvailable',fn(CORE,'Read-LocalCoreState'))
 def test_before_copy_install_and_rollback_share_one_lock_order(self):
  self.assertLess(RESTORE.index('auto-copy.lock'),RESTORE.index('$stateLock=Enter-LocalCoreMutationLock'))
  self.assertLess(RESTORE.index('$stateLock=Enter-LocalCoreMutationLock'),RESTORE.index('New-ForgeDataBackup'))
  self.assertIn('New-ForgeDataBackup $root $before -MutationLock $stateLock',RESTORE)
  self.assertIn('Install-BackupStage $m $stage $root -MutationLock $stateLock',RESTORE)
  self.assertNotIn('Restore-ForgeDataBackupFromPath $before',RESTORE)
 def test_preflight_and_immutable_preimages_precede_marker_and_mutation(self):
  mark=INSTALL.index("[IO.File]::Move($markerTmp,$marker)")
  for token in ('Read-LocalCoreStateCandidate $stateSource','The verified restore stage changed','[IO.FileShare]::None','Restore preimage verification failed','Assert-LocalCoreRestoreContext $restoreContext $st $MutationLock','Write-BackupDurableText $journalPath'):
   self.assertLess(INSTALL.index(token),mark,token)
  self.assertLess(mark,INSTALL.index('Write-BackupStreamFromFile $handles'))
  self.assertIn('$stream.Flush($true)',fn(BACK,'Write-BackupDurableText'))
 def test_uncertain_commit_is_not_blindly_rolled_back(self):
  self.assertIn('if($planned-and$primary-ceq$planned){$committed=$true;',INSTALL)
  foreign=INSTALL.index("if($primary-cne$restoreContext.primary_sha256-or(Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath)-cne$restoreContext.backup_sha256)")
  self.assertLess(foreign,INSTALL.index('for($i=$rows.Count-1;'))
  self.assertIn('No rollback overwrote it',INSTALL)
 def test_pending_recovery_rollback_restores_previous_guard(self):
  self.assertIn('Restore-BackupPriorMarker $marker $markerSha $ExpectedPendingMarkerSha $transaction',INSTALL)
  prior=fn(BACK,'Restore-BackupPriorMarker')
  self.assertIn("if($PreviousSha-ceq'missing'){Remove-BackupOwnedMarker",prior)
  self.assertIn('(Get-LocalCoreRestoreFileFence $previous)-cne$PreviousSha',prior)
  self.assertIn('[IO.File]::Replace($temporary,$Path',prior)
 def test_existing_restore_route_can_recover_pending_without_manual_surgery(self):
  self.assertIn("Confirm 'A previous data restore is incomplete.",RESTORE)
  self.assertIn('No data was replaced',RESTORE)
  self.assertIn('-ExpectedPendingMarkerSha $pending',RESTORE)
  self.assertIn("'previous-marker.json'",INSTALL)
  self.assertIn("'recovery_preimage_not_a_consistent_workspace'",RESTORE)
 def test_recovery_startup_and_failed_same_session_restore_are_reachable(self):
  self.assertIn('$Window.Add_ContentRendered({if(Show-DataRestoreRecovery){return};Initialize-LocalCore;',WB)
  complete=fn(BACK,'Complete-DataBackupRestore');self.assertIn('if(-not $r.ok){$null=Show-DataRestoreRecovery;return $false}',complete)
  self.assertIn('if($script:DataRestoreRecoveryOnly){return}',fn(WB,'Refresh-Workbench'))
  ui=fn(BACK,'Show-DataRestoreRecovery')
  self.assertIn("$LoginGrid.Visibility='Collapsed';$AppGrid.Visibility='Visible'",ui);self.assertIn('$DataRestoreButton.IsEnabled=$true',ui)
  self.assertIn('if(-not $wasRecovery)',ui);self.assertIn('Windows.Controls.Primitives.Selector',ui)
  self.assertNotIn('Read-LocalCoreState',ui)
 def test_location_rewrite_is_only_live_pointers_not_hashed_history(self):
  move=fn(BACK,'Convert-BackupStatePaths')
  for token in ("'local_file_path'","'active_acceptance'","@('path','publication_receipt_template')"):self.assertIn(token,move)
  for token in ('review_history','publication_receipts','brief_approval','lineage_fingerprint'):self.assertNotIn(token,move)
  self.assertNotIn('Convert-BackupJsonRoot',INSTALL)
  self.assertNotIn("EndsWith('.json')",INSTALL)
  self.assertIn('$art=[string]$acc.local_file_path',fn(CORE,'Build-LocalAmazonPackage'))
 def test_capture_holds_all_inputs_and_detects_inventory_changes(self):
  self.assertIn('[IO.FileShare]::Read)',CAPTURE);self.assertIn('$stateLock=Enter-BackupStateLock $Root $MutationLock',CAPTURE)
  self.assertEqual(3,CAPTURE.count('Get-BackupRelativeFiles $Root'))
  self.assertLess(CAPTURE.index('foreach($rel in $files){'),CAPTURE.index('$fs=[IO.File]::Open($tmp'))
  self.assertIn("if($null-eq$h){throw ('Backup input was not copied:",CAPTURE)
  self.assertNotIn('return $null',fn(BACK,'Copy-FileIntoZipEntry'))
  self.assertNotIn('SilentlyContinue',fn(BACK,'Get-BackupRelativeFiles'))
 def test_capture_validates_primary_no_implicit_repair_and_labels_mixed_preimage(self):
  self.assertIn("if(-not $RecoveryPreimage){if(!$handles.ContainsKey('local-core-v1/state.json'))",CAPTURE)
  self.assertIn('Read-ForgeStateFileSnapshot',CAPTURE);self.assertNotIn('Read-LocalCoreState',CAPTURE)
  self.assertIn('recovery_preimage_not_a_consistent_workspace',CAPTURE)
  self.assertIn('$healthyCurrent=$false',RESTORE)
 def test_auto_helper_uses_existing_core_host_and_strict_parser_closure(self):
  self.assertTrue(AUTO.startswith('#requires -Version 7.5\n'))
  self.assertIn("Modules\\Forge.BriefApproval.ps1",AUTO)
  auto=fn(BACK,'Start-AutoDataCopyIfDue');self.assertIn("$ps=Join-Path $PSHOME 'pwsh.exe'",auto)
  self.assertNotIn('powershell.exe',auto)
  self.assertIn("$psExe=Join-Path $PSHOME 'pwsh.exe'",text(APP/'MerchForgeResearchDraftSelfTest.ps1'))
 def test_new_native_suite_uses_actual_writer_locks_zip_and_explicit_fault_wrappers(self):
  suite=text(HERE/'Test-ForgeBackupTransaction.ps1');pins=json.loads(text(HERE/'BackupPins.json'))
  for name in ('Write-LocalCoreState','Read-ForgeStateFileSnapshot','New-LocalCoreRestoreContext','Install-BackupStage','New-ForgeDataBackup','Read-ForgeDataBackup','Show-DataRestoreRecovery'):self.assertIn(name,pins['expected_function_names'])
  self.assertIn('. ([scriptblock]::Create($definitions[0].Extent.Text))',suite)
  self.assertIn("& $script:Actual['Write-LocalCoreState'] $State -MutationLock $MutationLock -RestoreContext $RestoreContext",suite)
  self.assertIn('INJECT_AFTER_REAL_COMMIT',suite);self.assertIn('INJECT_RECOVERY_ASSET_FAILURE',suite)
  self.assertEqual(pins['expected_case_names'],re.findall(r"^        Test-Case '([^']+)'",suite,re.M))
 def test_source_and_test_pins_match(self):
  pins=json.loads(text(HERE/'BackupPins.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for name,digest in pins['sources'].items():self.assertEqual(digest,sha(APP/name),name)
  for name,digest in pins['tests'].items():self.assertEqual(digest,sha(HERE/name),name)
  self.assertEqual(pins['expected_function_names'],[name for names in pins['functions'].values() for name in names])
if __name__=='__main__':unittest.main()

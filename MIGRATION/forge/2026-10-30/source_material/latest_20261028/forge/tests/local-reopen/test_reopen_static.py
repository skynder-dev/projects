"""Source/wiring/integrity only. Does not parse PowerShell or execute app behavior."""
from pathlib import Path
import hashlib,json,re,unittest
HERE=Path(__file__).resolve().parent
APP=HERE.parents[1]/'app/Merch_Forge_A5_Current'
def txt(p):return p.read_text(encoding='utf-8-sig')
def fn(source,name):
 m=re.search(r'^function '+re.escape(name)+r'\b',source,re.M);assert m,name
 n=re.search(r'^function ',source[m.end():],re.M)
 return source[m.start():m.end()+n.start() if n else len(source)]
CORE=txt(APP/'Modules/Forge.LocalCore.ps1');GATES=txt(APP/'Modules/Forge.Gates.ps1');DOMAIN=txt(APP/'Modules/Forge.DomainActions.ps1');WB=txt(APP/'MerchForgeWorkbench.ps1')
TARGET=fn(CORE,'Get-ForgeLocalReopenTarget');REOPEN=fn(CORE,'Reopen-LocalExactAcceptance')
class LocalReopenStatic(unittest.TestCase):
 def test_real_button_routes_local_before_server_rejection(self):
  route=fn(DOMAIN,'Reopen-CurrentAcceptance')
  self.assertIn('$ReopenAcceptanceButton.Add_Click({Reopen-CurrentAcceptance})',WB)
  self.assertLess(route.index('Reopen-LocalExactAcceptance'),route.index('if(Test-CurrentIsResearchDraft)'))
  self.assertLess(route.index('Reopen-LocalExactAcceptance'),route.index("Has-Cap 'accept'"))
  self.assertIn('return\n    }',route)
 def test_ui_captures_exact_displayed_target_and_can_enable_local_owner(self):
  gate=fn(GATES,'Update-AcceptanceControls')
  self.assertIn('$script:LocalReopenTarget=$null',gate)
  self.assertIn('Get-ForgeLocalReopenTarget (Read-LocalCoreState)',gate)
  self.assertIn('$canReopen=(-not $script:Busy-and-not $script:Dirty)',gate)
  self.assertIn('Acceptance record SHA-256: {2}',gate)
  self.assertIn('if($localReopenUnavailable){$canReopen=$false}',gate)
  self.assertIn('Update-LocalCoreStatusUi;Update-AcceptanceControls',fn(CORE,'Refresh-LocalArtworkUi'))
 def test_target_verifies_full_saved_brief_and_current_draft(self):
  for token in ('source_save_intent','source_revision_id','source_revision_hash','generation_brief_sha256','generation_brief_snapshot','ConvertTo-ResearchDraftConcept','sync_state','New-LocalAcceptanceFingerprint','$rows.Count-ne1'):
   self.assertIn(token,TARGET)
  self.assertNotIn('Write-LocalCoreState',TARGET)
 def test_target_does_not_require_present_artwork_or_clear_hold(self):
  for token in ('Get-Item','Test-Path','Get-FileSha256Hex','Assert-ForgeNoSemanticHold'):
   self.assertNotIn(token,TARGET)
 def test_new_acceptance_has_unique_instance_legacy_target_has_no_requirement(self):
  accept=fn(CORE,'Set-LocalExactAcceptance')
  self.assertIn("acceptance_id=('local-accept-'+[guid]::NewGuid().ToString('N'))",accept)
  self.assertIn('ConvertTo-Json -InputObject $acc -Depth 60 -Compress',TARGET)
  self.assertNotIn("Get-PropertyValue $acc 'acceptance_id'",TARGET)
 def test_reason_cancel_and_both_fresh_fences_precede_mutation(self):
  write=REOPEN.index('Write-LocalCoreState $s');preserve=REOPEN.index('Preserve-ForgeLocalReviewHistory')
  for token in ('$Reason=$Reason.Trim()','[string]::IsNullOrWhiteSpace($Reason)','if(!(Confirm $question','[object]::ReferenceEquals($view,$script:Current)'):
   self.assertLess(REOPEN.index(token),preserve)
  self.assertEqual(2,REOPEN.count('$fresh.frame_sha256-cne$target.frame_sha256'))
  self.assertIn('ConvertFrom-Json -DateKind String (ConvertTo-Json -InputObject $DisplayedTarget',REOPEN)
  self.assertLess(preserve,write)
  self.assertGreater(REOPEN.index('$script:PublicationDirty=$false'),write)
 def test_optimistic_store_fence_is_not_replaced(self):
  self.assertIn('state_revision=$rev;last_write_id=$writeId',TARGET)
  writer=fn(CORE,'Write-LocalCoreState')
  for token in ('Enter-LocalCoreMutationLock','$diskRev-ne$expectedRev',"'last_write_id')-cne$expectedWriteId",'[IO.File]::Replace('):self.assertIn(token,writer)
 def test_legacy_v2_write_token_contract_is_preserved_without_migration(self):
  self.assertIn("$writeValue=Get-PropertyValue $State 'last_write_id'",TARGET)
  self.assertIn("$writeValue-isnot[string]-or($writeId-and$writeId-cnotmatch'^[0-9a-fA-F]{32}$')",TARGET)
  self.assertNotIn('Add-OrSetProperty $State',TARGET)
 def test_single_commit_revokes_current_authority_after_snapshot(self):
  self.assertEqual(1,REOPEN.count('Write-LocalCoreState'))
  preserve=REOPEN.index('Preserve-ForgeLocalReviewHistory');write=REOPEN.index('Write-LocalCoreState $s')
  for token in ("'active_acceptance' $null","'accepted' $false",'New-LocalCoreChecks $target.revision_id',"'accepted_artwork_sha256' ''","'acceptance_fingerprint' ''",'Invalidate-LocalCorePackages'):
   self.assertLess(preserve,REOPEN.index(token));self.assertLess(REOPEN.index(token),write)
  for token in ("'brief_approval' $null","'owner_decision'",'Save-ResearchDraftRevision','New-ResearchDraftRevision'):
   self.assertNotIn(token,REOPEN)
 def test_prior_history_is_detached_and_new_reason_appended(self):
  history=fn(CORE,'Preserve-ForgeLocalReviewHistory')
  for token in ('ConvertFrom-Json -DateKind String',"'owner_reason' $OwnerReason","'packages' ([object[]]@(Get-PropertyValue $Lc 'packages'))","'review_history' ([object[]]@($prior+@($entry)))"):
   self.assertIn(token,history)
  render=fn(CORE,'Get-ForgeLocalReviewHistoryEvents');self.assertIn("Get-PropertyValue $entry 'owner_reason'",render)
 def test_no_file_deletion_or_generation_publication_reapproval_in_local_route(self):
  for token in ('Remove-Item','Copy-Item','Move-Item','[IO.File]::','Invoke-ForgeApi','Start-Process','Invoke-WebRequest','Invoke-RestMethod','Set-LocalExactAcceptance','Sync-LocalGenerationResults','Invoke-LocalCheckAutomation','Confirm-LocalGenerationBriefApproval'):
   self.assertNotIn(token,REOPEN)
 def test_postcommit_render_failure_cannot_claim_not_saved(self):
  self.assertIn('try{if($null-ne$button){$button.IsEnabled=$false}}catch{}',REOPEN)
  self.assertIn('try{if($null-ne$label){$label.Text=',REOPEN)
  self.assertIn("}catch{try{Write-AppLog 'WARN' ('Local acceptance withdrawal was saved",REOPEN)
  self.assertIn('try{Refresh-StageFilterIfActive}catch',REOPEN)
  self.assertNotIn('Local acceptance was not reopened',fn(DOMAIN,'Reopen-CurrentAcceptance'))
 def test_native_suite_is_actual_functions_and_pins_match(self):
  suite=HERE/'Test-ForgeLocalReopen.ps1';self.assertTrue(suite.exists())
  source=txt(suite);self.assertIn('Set-StrictMode -Version 2.0',source);self.assertIn('Parser]::ParseFile',source);self.assertIn('. ([scriptblock]::Create($matches[0].Extent.Text))',source)
  pins=json.loads(txt(HERE/'LocalReopenPins.json'));deps=json.loads(txt(HERE/'LocalReopenDependencies.json'))
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for path,digest in pins['sources'].items():self.assertEqual(digest,sha(APP/path),path)
  for path,digest in pins['tests'].items():self.assertEqual(digest,sha(HERE/path),path)
  self.assertEqual(pins['expected_function_names'],[n for ns in deps['functions'].values() for n in ns])
  self.assertEqual(pins['expected_case_names'],re.findall(r"^        Test-Case '([^']+)'",source,re.M))
if __name__=='__main__':unittest.main()

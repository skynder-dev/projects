$ErrorActionPreference='Stop'
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase
if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'STA required'}
function Get-PropertyValue($Object,$Name,$Default=$null){if($null-eq$Object){return $Default};if($Object-is[Collections.IDictionary]){return $Object[$Name]};$p=$Object.PSObject.Properties[$Name];if($null-ne$p){return $p.Value};return $Default}
function Ensure-Dir($Path){[void][IO.Directory]::CreateDirectory($Path)}
function Write-AppLog($Level,$Message){}
foreach($n in @('Forge.Media.ps1','Forge.DataViews.ps1','Forge.LocalCore.ps1','Forge.ResearchDrafts.ps1','Forge.ResearchImport.ps1','Forge.PublicEvidence.ps1','Forge.LocalAI.ps1')){. (Join-Path $PSScriptRoot ('runtime/Modules/'+$n))}
# Real WPF controls fixture for existing production injection point; no Window or invented Workbench bootstrap.
$parent=New-Object Windows.Controls.StackPanel;$LocalAIStatus=New-Object Windows.Controls.TextBlock;[void]$parent.Children.Add($LocalAIStatus)
Initialize-ForgeSemanticReviewUI
function Click($Button){$Button.RaiseEvent([Windows.RoutedEventArgs]::new([Windows.Controls.Button]::ClickEvent))}
$checks=[ordered]@{};function Check($N,[bool]$V){$checks[$N]=$V;if(!$V){throw ('FAILED '+$N)}}
Check 'actual_panel_mounted' ($script:SemanticReviewExpander.Parent-eq$parent)
Check 'no_outcome_default' ($script:SemanticReviewOutcome.SelectedIndex-eq-1)
$results=[ordered]@{}
foreach($name in @('positive','no_selection','blank_note','cancel','stale_revision','rejected')){
 $root=Join-Path $PSScriptRoot ('ui-'+$name+'-'+[guid]::NewGuid().ToString('N'));Copy-Item (Get-Content (Join-Path $PSScriptRoot 'fixture-state-path.txt') -Raw) $root -Recurse
 $script:StateRoot=$root;$script:LocalCoreRoot=Join-Path $root 'core';$script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json';$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'backup.json';$script:Dirty=$false;$script:PublicationDirty=$false
 $d=@(Get-ResearchDraftList (Read-LocalCoreState))[0];$key=$d.concept_key;$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d};$script:LastSemanticReviewUiReceipt=$null
 Clear-ForgeSemanticReviewUiBinding;$script:SemanticReviewNote.Text='Synthetic event test note only; not actual owner approval'
 $before=Get-FileSha256Hex $script:LocalCoreStatePath;$holdSha=Get-ForgeBriefSha256 $d.semantic_review_hold
 Click $script:SemanticReviewOpen
 Check ($name+'_snapshot_opened') ($null-ne$script:SemanticReviewDisplayedSnapshot)
 Check ($name+'_view_exact_snapshot') ((Get-ForgeBriefSha256 (ConvertFrom-ForgeJsonObjectStrict $script:SemanticReviewView.Text))-ceq(Get-ForgeBriefSha256 $script:SemanticReviewDisplayedSnapshot))
 Check ($name+'_contains_brief_source_relationship_hold') ($null-ne$script:SemanticReviewDisplayedSnapshot.full_saved_brief-and$script:SemanticReviewDisplayedSnapshot.source_records.Count-eq3-and$script:SemanticReviewDisplayedSnapshot.original_hold.relationship_exact-ceq$d.semantic_review_hold.relationship_exact)
 Check ($name+'_open_no_write') ((Get-FileSha256Hex $script:LocalCoreStatePath)-ceq$before)
 if($name-ne'no_selection'){$script:SemanticReviewOutcome.SelectedIndex=if($name-eq'rejected'){1}else{2}}
 if($name-eq'blank_note'){$script:SemanticReviewNote.Text='  '}
 if($name-eq'stale_revision'){
  $fields=Get-ResearchDraftCurrentFields $d|ConvertTo-Json -Depth 40|ConvertFrom-Json;$fields.title+=' изменено';$null=Save-ResearchDraftRevision $key $fields 'owner_edit' $d.current_revision_id;$before=Get-FileSha256Hex $script:LocalCoreStatePath
 }
 if($name-eq'cancel'){Click $script:SemanticReviewCancel}else{Click $script:SemanticReviewSubmit}
 $after=Get-ResearchDraft $key
 if($name-in@('positive','rejected')){
  Check ($name+'_real_receipt_recorded') ($script:LastSemanticReviewUiReceipt.recorded-eq$true-and@($after.semantic_reviews).Count-eq1)
  Check ($name+'_explicit_outcome_correct') ($after.semantic_reviews[-1].outcome-ceq$(if($name-eq'positive'){'REVIEWED_FOR_NEXT_REVIEW_STAGE'}else{'REJECTED'}))
  Check ($name+'_hold_historical_unchanged') ((Get-ForgeBriefSha256 $after.semantic_review_hold)-ceq$holdSha)
  if($name-eq'positive'){Assert-ForgeNoSemanticHold $key}else{$blocked=$false;try{Assert-ForgeNoSemanticHold $key}catch{$blocked=$_.Exception.Message-like'SEMANTIC_REVIEW_HOLD:*'};Check 'rejected_gate_blocks' $blocked}
 }else{
  Check ($name+'_no_receipt_or_write') ($null-eq$script:LastSemanticReviewUiReceipt-and(Get-FileSha256Hex $script:LocalCoreStatePath)-ceq$before-and@($after.semantic_reviews|Where-Object{$null-ne$_}).Count-eq0)
 }
 if($name-eq'no_selection'){Check 'selection_error_explicit' ($script:SemanticReviewStatus.Text-like'SEMANTIC_REVIEW_OUTCOME_REQUIRED:*')}
 if($name-eq'blank_note'){Check 'blank_note_error_explicit' ($script:SemanticReviewStatus.Text-eq'SEMANTIC_REVIEW_NOTE_REQUIRED')}
 if($name-eq'cancel'){Check 'cancel_preserves_note' ($script:SemanticReviewNote.Text-ceq'Synthetic event test note only; not actual owner approval')}
 if($name-eq'stale_revision'){Check 'stale_reject_no_rebinding' ($script:SemanticReviewStatus.Text-like'SEMANTIC_REVIEW_STALE:*'-and$null-eq$script:SemanticReviewDisplayedSnapshot-and!$script:SemanticReviewSubmit.IsEnabled)}
 Check ($name+'_owner_still_undecided') ((Get-LocalOwnerDecisionRecord $key (ConvertTo-ResearchDraftConcept $after)).decision-ceq'UNDECIDED')
 $results[$name]=[ordered]@{root=$root;status_text=$script:SemanticReviewStatus.Text;receipt=$script:LastSemanticReviewUiReceipt;no_artwork_or_export=$true}
}
Check 'no_window_created' ($null-eq[Windows.Application]::Current-or[Windows.Application]::Current.Windows.Count-eq0)
[ordered]@{status='REAL_WPF_HEADLESS_EVENTS_PASS';checks=$checks;results=$results;model_calls=0;windows_shown=0;visible_GUI_acceptance=$false;full_Workbench_bootstrap_verified=$false}|ConvertTo-Json -Depth 40|Set-Content (Join-Path $PSScriptRoot 'UI-TEST-RESULTS.json') -Encoding utf8

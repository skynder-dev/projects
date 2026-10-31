param([switch]$Reload,[string]$DataRoot)
$ErrorActionPreference='Stop'
function Get-PropertyValue($Object,$Name,$Default=$null){if($null-eq$Object){return $Default};if($Object-is[Collections.IDictionary]){return $Object[$Name]};$p=$Object.PSObject.Properties[$Name];if($null-ne$p){return $p.Value};return $Default}
function Ensure-Dir($Path){[void][IO.Directory]::CreateDirectory($Path)}
function Write-AppLog($Level,$Message){}
foreach($n in @('Forge.Media.ps1','Forge.DataViews.ps1','Forge.LocalCore.ps1','Forge.ResearchDrafts.ps1','Forge.ResearchImport.ps1','Forge.PublicEvidence.ps1','Forge.LocalAI.ps1')){. (Join-Path $PSScriptRoot ('runtime/Modules/'+$n))}
if(!$Reload){$DataRoot=Join-Path $PSScriptRoot ('case-'+[guid]::NewGuid().ToString('N'));Copy-Item (Get-Content (Join-Path $PSScriptRoot 'fixture-state-path.txt') -Raw) $DataRoot -Recurse}
$script:StateRoot=$DataRoot;$script:LocalCoreRoot=Join-Path $DataRoot 'core';$script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json';$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'backup.json';$script:Dirty=$false;$script:PublicationDirty=$false
$d=@(Get-ResearchDraftList (Read-LocalCoreState))[0];$key=$d.concept_key;$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d};$script:DiscoverSnapshot=$null
$checks=[ordered]@{};$refusalReasons=[ordered]@{};function Check($N,[bool]$V){$checks[$N]=$V;if($N-match'reject|blocks'){$refusalReasons[$N]=$script:LastRefusal};if(!$V){throw ('FAILED '+$N)}}
function Refused($Code){try{& $Code;return $false}catch{$script:LastRefusal=$_.Exception.Message;return $true}}
if($Reload){
 Check 'restart_semantic_receipt_current' (Test-ForgeSemanticReviewCurrent $d)
 Assert-ForgeNoSemanticHold $key
 Check 'restart_ordinary_generation_gate_blocks' (Refused {Assert-LocalGenerationBriefApproved})
 Check 'restart_owner_undecided' ((Get-LocalOwnerDecisionRecord $key (ConvertTo-ResearchDraftConcept $d)).decision-ceq'UNDECIDED')
 [ordered]@{status='RESTART_PASS';checks=$checks}|ConvertTo-Json -Depth 10|Set-Content (Join-Path $DataRoot 'restart.json') -Encoding utf8;return
}
$initial=Read-LocalCoreState;$initialOwner=(Get-LocalOwnerDecisionRecord $key (ConvertTo-ResearchDraftConcept $d)).decision;$holdSha=Get-ForgeBriefSha256 $d.semantic_review_hold
$snap=Get-ForgeSemanticReviewSnapshot $key
$before=Get-FileSha256Hex $script:LocalCoreStatePath
Check 'missing_intent_reject' (Refused {Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic explicit test note' 'NO_INTENT'})
Check 'blank_note_reject' (Refused {Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' '  ' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'})
Check 'no_success_default' ((Get-Command Record-ForgeSemanticReview).Parameters['Outcome'].Attributes.Mandatory-contains$true)
Check 'invalid_missing_outcome_reject' (Refused {Record-ForgeSemanticReview $snap '' 'Synthetic test' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'})
Check 'invalid_calls_no_write' ((Get-FileSha256Hex $script:LocalCoreStatePath)-ceq$before)
foreach($outcome in @('NEEDS_EDIT','REJECTED')){
 $snap=Get-ForgeSemanticReviewSnapshot $key;$n=Record-ForgeSemanticReview $snap $outcome 'Synthetic negative owner review; not an actual owner decision' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'
 Check ($outcome+'_recorded') $n.recorded
 Check ($outcome+'_hold_blocks') (Refused {Assert-ForgeNoSemanticHold $key})
}
$snap=Get-ForgeSemanticReviewSnapshot $key
# Competing real native state write invalidates snapshot CAS even if brief did not change.
$state=Read-LocalCoreState;Write-LocalCoreState $state
Check 'concurrent_state_reject' (Refused {Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic test note' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'})
$snap=Get-ForgeSemanticReviewSnapshot $key;$archive=Join-Path (Join-Path $DataRoot 'research-import-v1') ($snap.binding.source_sha256+'.source.json');$bytes=[IO.File]::ReadAllBytes($archive)
try{[IO.File]::WriteAllBytes($archive,($bytes+@(32)));Check 'changed_source_reject' (Refused {Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic test note' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'})}finally{[IO.File]::WriteAllBytes($archive,$bytes)}
$d=Get-ResearchDraft $key;$fields=Get-ResearchDraftCurrentFields $d|ConvertTo-Json -Depth 40|ConvertFrom-Json;$fields.title+=' новая';$edit=Save-ResearchDraftRevision $key $fields 'owner_edit' $d.current_revision_id
Check 'stale_revision_reject' (Refused {Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic test note' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'})
$d=Get-ResearchDraft $key;$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d}
$snap=Get-ForgeSemanticReviewSnapshot $key;$ok=Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic explicit callable review outcome for storage/guards only; not real owner approval' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'
Check 'positive_recorded' $ok.recorded
$d=Get-ResearchDraft $key;Check 'positive_only_semantic_gate_resolved' (Test-ForgeSemanticReviewCurrent $d);Assert-ForgeNoSemanticHold $key
Check 'ordinary_generation_gate_still_blocks' (Refused {Assert-LocalGenerationBriefApproved})
Check 'ordinary_job_gate_still_blocks' (Refused {Assert-ForgeGenerationJobBriefApproval ([pscustomobject]@{concept_key=$key}) (Read-LocalCoreState)})
Check 'hold_history_unchanged' ((Get-ForgeBriefSha256 $d.semantic_review_hold)-ceq$holdSha)
Check 'owner_decision_unchanged' ((Get-LocalOwnerDecisionRecord $key (ConvertTo-ResearchDraftConcept $d)).decision-ceq$initialOwner)
$pwsh=(Get-Process -Id $PID).Path
& $pwsh -NoProfile -File $PSCommandPath -Reload -DataRoot $DataRoot
Check 'restart_exit0' ($LASTEXITCODE-eq0)
Check 'restart_receipt' ((Get-Content (Join-Path $DataRoot 'restart.json') -Raw|ConvertFrom-Json).status-ceq'RESTART_PASS')
$retainedSourceOnly=Get-Content (Join-Path (Split-Path $PSScriptRoot) 'forge-core-birding-trial-001/owned-state/core/state.json') -Raw -Encoding utf8|ConvertFrom-Json
Check 'retained_source_only_state_blocks' (Refused {Assert-ForgeNoSemanticHold $key $retainedSourceOnly})
# Retain old positive state, then append a fresh negative receipt for the same brief.
$retainedPositiveState=Read-LocalCoreState;$retainedPositiveDraft=Get-ResearchDraft $key $retainedPositiveState
foreach($negative in @('NEEDS_EDIT','REJECTED')){
 $snap=Get-ForgeSemanticReviewSnapshot $key;$null=Record-ForgeSemanticReview $snap $negative 'Synthetic later negative review; retained positive must not pass' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'
 Check ('retained_positive_after_'+$negative+'_reject') (!(Test-ForgeSemanticReviewCurrent $retainedPositiveDraft))
 Check ('retained_state_after_'+$negative+'_blocks') (Refused {Assert-ForgeNoSemanticHold $key $retainedPositiveState})
 # Explicit new positive synthetic review, so the next case again starts from a current positive.
 $snap=Get-ForgeSemanticReviewSnapshot $key;$null=Record-ForgeSemanticReview $snap 'REVIEWED_FOR_NEXT_REVIEW_STAGE' 'Synthetic explicit next review for regression setup only' 'RECORD_EXPLICIT_SEMANTIC_REVIEW'
 $retainedPositiveState=Read-LocalCoreState;$retainedPositiveDraft=Get-ResearchDraft $key $retainedPositiveState
}
# Edit after positive review cannot inherit semantic clearance.
$d=Get-ResearchDraft $key;$fields=Get-ResearchDraftCurrentFields $d|ConvertTo-Json -Depth 40|ConvertFrom-Json;$fields.title+=' ещё';$null=Save-ResearchDraftRevision $key $fields 'owner_edit' $d.current_revision_id
Check 'edit_after_positive_blocks_again' (Refused {Assert-ForgeNoSemanticHold $key})
Check 'retained_positive_changed_brief_reject' (!(Test-ForgeSemanticReviewCurrent $retainedPositiveDraft))
Check 'retained_state_changed_brief_blocks' (Refused {Assert-ForgeNoSemanticHold $key $retainedPositiveState})
$d=Get-ResearchDraft $key;$fields=Get-ResearchDraftCurrentFields $d|ConvertTo-Json -Depth 40|ConvertFrom-Json;$fields.differentiation=$fields.differentiation.Replace('Качество печати не проверено.','');$null=Save-ResearchDraftRevision $key $fields 'owner_edit' $d.current_revision_id
$d=Get-ResearchDraft $key;$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d}
Check 'other_print_quality_guard_reject' (Refused {Get-ForgeSemanticReviewSnapshot $key})
[ordered]@{status='CALLABLE_SYNTHETIC_REVIEW_TESTS_PASS';checks=$checks;refusal_reasons=$refusalReasons;data_root=$DataRoot;model_calls=0;actual_owner_approval=$false;visible_UI_verified=$false;no_export=$true}|ConvertTo-Json -Depth 20|Set-Content (Join-Path $PSScriptRoot 'TEST-RESULTS.json') -Encoding utf8

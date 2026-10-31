param([string]$StatePath)
$ErrorActionPreference='Stop'
function Get-PropertyValue($Object,$Name,$Default=$null){if($null-eq$Object){return $Default};if($Object-is[Collections.IDictionary]){return $Object[$Name]};$p=$Object.PSObject.Properties[$Name];if($null-ne$p){return $p.Value};return $Default}
function Ensure-Dir($Path){[void][IO.Directory]::CreateDirectory($Path)}
function Write-AppLog($Level,$Message){}
foreach($n in @('Forge.Media.ps1','Forge.DataViews.ps1','Forge.LocalCore.ps1','Forge.ResearchDrafts.ps1','Forge.ResearchImport.ps1','Forge.PublicEvidence.ps1','Forge.LocalAI.ps1')){. (Join-Path $PSScriptRoot ('runtime/Modules/'+$n))}
$script:StateRoot=$StatePath;$script:LocalCoreRoot=Join-Path $StatePath 'core';$script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json';$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'backup.json'
$s=Read-LocalCoreState;$d=@(Get-ResearchDraftList $s)[0];$before=Get-FileSha256Hex $script:LocalCoreStatePath
if($d.semantic_review_hold.status-cne'PENDING'-or$d.semantic_review_hold.meaning_verified){throw 'HOLD lost'}
$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d)};$script:Dirty=$false
$checks=[ordered]@{}
foreach($name in @('approval','generation','export','acceptance','job')){
 $blocked=$false;try{switch($name){approval{Confirm-LocalGenerationBriefApproval} generation{Assert-LocalGenerationBriefApproved} export{Export-LocalGenerationBrief} acceptance{Get-ForgeLocalAcceptanceTarget $null $s} job{Assert-ForgeGenerationJobBriefApproval ([pscustomobject]@{concept_key=$d.concept_key}) $s}}}catch{if($_.Exception.Message-like'SEMANTIC_REVIEW_HOLD:*'){$blocked=$true}else{throw}};if(!$blocked){throw ('Not blocked '+$name)};$checks[$name]=$blocked
}
if((Get-FileSha256Hex $script:LocalCoreStatePath)-cne$before){throw 'Read/rejection mutated state'}
[ordered]@{status='RESTART_HOLD_AND5_BLOCKERS_PASS';checks=$checks;state_sha256=$before;relationship_exact=$d.semantic_review_hold.relationship_exact;owner=(Get-LocalOwnerDecisionRecord $d.concept_key (ConvertTo-ResearchDraftConcept $d)).decision;model_calls=0}|ConvertTo-Json -Depth 10|Set-Content (Join-Path $PSScriptRoot 'RESTART-RESULT.json') -Encoding utf8

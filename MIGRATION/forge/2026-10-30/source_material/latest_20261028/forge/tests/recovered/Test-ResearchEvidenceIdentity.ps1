#requires -Version 7.5
param(
    [Parameter(Mandatory=$true)][string]$ModuleRoot,
    [string]$OutputRoot,
    [ValidateSet('Run','Reload')][string]$Phase='Run'
)
$ErrorActionPreference='Stop'
if(!$OutputRoot){$OutputRoot=Join-Path ([IO.Path]::GetTempPath()) ('forge-evidence-regression-'+[guid]::NewGuid().ToString('N'))}
$ModuleRoot=[IO.Path]::GetFullPath($ModuleRoot)
$OutputRoot=[IO.Path]::GetFullPath($OutputRoot)
if($Phase-eq'Run'-and(Test-Path -LiteralPath $OutputRoot)){throw 'Use a fresh nonexistent output directory; existing user state must never be used.'}
# App bootstrap primitives only. Draft, import, hashing, state and review functions are REAL modules.
function Get-PropertyValue($Object,[string]$Name){
    if($null-eq$Object){return $null}
    if($Object-is[Collections.IDictionary]){return ,$Object[$Name]}
    $p=$Object.PSObject.Properties[$Name];if($null-ne$p){return ,$p.Value};return $null
}
function Ensure-Dir([string]$Path){[void][IO.Directory]::CreateDirectory($Path)}
function Write-AppLog([string]$Level,[string]$Message){Write-Verbose ($Level+': '+$Message)}
foreach($name in @('Forge.Media.ps1','Forge.LocalCore.ps1','Forge.DataViews.ps1','Forge.ResearchDrafts.ps1','Forge.ResearchImport.ps1','Forge.PublicEvidence.ps1')){. (Join-Path $ModuleRoot $name)}
$script:StateRoot=Join-Path $OutputRoot 'data'
$script:LocalCoreRoot=Join-Path $script:StateRoot 'local-core'
$script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json'
$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'state.last-good.json'
$script:Current=$null
$checks=[ordered]@{}
function Check([string]$Name,[bool]$Value){$checks[$Name]=$Value;if(!$Value){throw ('FAILED: '+$Name)}}
function StateSha {Get-FileSha256Hex $script:LocalCoreStatePath}
function SaveJson([string]$Path,$Value){[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 60),(New-Object Text.UTF8Encoding($false)))}
if($Phase-eq'Reload'){
    $expected=Get-Content (Join-Path $OutputRoot 'expected.json') -Raw|ConvertFrom-Json
    $s=Read-LocalCoreState
    foreach($entry in @($expected.drafts)){
        $d=Get-ResearchDraft $entry.key $s
        Check ('reload_'+$entry.label) ($null-ne$d-and$d.current_revision_id-ceq$entry.revision-and$d.provenance.research_packet.source_sha256-ceq$entry.source_sha256)
        $decision=Get-LocalOwnerDecisionRecord $entry.key (ConvertTo-ResearchDraftConcept $d) $s
        Check ('undecided_'+$entry.label) ($decision.decision-ceq'UNDECIDED')
    }
    $queue=@(Get-ResearchDraftQueueItems $s)
    Check 'queue_contains_A_and_B' (@($queue|Where-Object{$_.concept_key-in@($expected.drafts.key)}).Count-eq2)
    Check 'reload_did_not_write' ((StateSha)-ceq$expected.state_sha256)
    SaveJson (Join-Path $OutputRoot 'reload-receipt.json') ([ordered]@{status='PASS';checks=$checks;synthetic=$true})
    return
}
Ensure-Dir $OutputRoot
Write-LocalCoreState (New-LocalCoreState)
$at=[datetime]::UtcNow.AddDays(-1).ToString('o')
$inputA=[pscustomobject]@{
    schema='forge.research_import.v1';adapter_key='public_observations_v1';synthetic=$true;collected_at=$at
    niche=[pscustomobject]@{niche_key='isolated-evidence-test';name='Synthetic regression niche';audience='Synthetic test audience'}
    freshness_policy=[pscustomobject]@{max_age_days=7}
    observations=@([pscustomobject]@{source_url='https://example.org/synthetic-regression';observation_kind='audience_context';observation_text='Synthetic observation A, not market evidence.';observed_at=$at})
}
$pathA=Join-Path $OutputRoot 'source-A.json';SaveJson $pathA $inputA
$aSnapshot=Import-ForgeResearchFile $pathA
$a=New-ResearchConceptDraft $aSnapshot.niches[0] $aSnapshot ([datetime]::UtcNow) 'regression'
Check 'A_created' $a.created
$shaA=Get-FileSha256Hex $pathA
Check 'A_archived_exact' ((Get-FileSha256Hex (Join-Path (Join-Path $script:StateRoot 'research-import-v1') ($shaA+'.source.json')))-ceq$shaA)
$before=StateSha
$renamed=Join-Path $OutputRoot 'same-bytes-renamed.json';[IO.File]::Copy($pathA,$renamed)
$again=Import-ForgeResearchFile $renamed
$repeat=New-ResearchConceptDraft $again.niches[0] $again ([datetime]::UtcNow.AddHours(1)) 'different-backend-display'
Check 'same_bytes_renamed_dedup' (!$repeat.created-and$repeat.draft.concept_key-ceq$a.draft.concept_key)
Check 'dedup_no_state_write' ((StateSha)-ceq$before)
$agedPacket=ConvertFrom-PublicResearchExport $inputA $shaA ([datetime]::UtcNow.AddDays(10))
$aged=ConvertTo-ResearchDiscoverSnapshot $agedPacket
Check 'freshness_really_changed' ($aged.research_packet.rows[0].freshness-cne$aSnapshot.research_packet.rows[0].freshness)
$repeat=New-ResearchConceptDraft $aged.niches[0] $aged ([datetime]::UtcNow.AddDays(10)) 'aged'
Check 'aged_same_archive_dedup' (!$repeat.created-and$repeat.draft.concept_key-ceq$a.draft.concept_key-and(StateSha)-ceq$before)
$inputB=$inputA|ConvertTo-Json -Depth 60|ConvertFrom-Json
$inputB.observations[0].observation_text='Synthetic observation B changes evidence, not the niche summary.'
$pathB=Join-Path $OutputRoot 'source-B.json';SaveJson $pathB $inputB
$bSnapshot=Import-ForgeResearchFile $pathB
$b=New-ResearchConceptDraft $bSnapshot.niches[0] $bSnapshot ([datetime]::UtcNow) 'regression'
Check 'B_distinct_same_niche' ($b.created-and$b.draft.concept_key-cne$a.draft.concept_key)
$shaB=Get-FileSha256Hex $pathB
Check 'B_provenance_new_source' ($b.draft.provenance.research_packet.source_sha256-ceq$shaB-and$shaB-cne$shaA)
$before=StateSha
$bRepeat=New-ResearchConceptDraft $bSnapshot.niches[0] $bSnapshot ([datetime]::UtcNow) 'regression'
$returnA=New-ResearchConceptDraft $aSnapshot.niches[0] $aSnapshot ([datetime]::UtcNow) 'regression'
Check 'repeat_B_and_return_A' (!$bRepeat.created-and$bRepeat.draft.concept_key-ceq$b.draft.concept_key-and!$returnA.created-and$returnA.draft.concept_key-ceq$a.draft.concept_key-and(StateSha)-ceq$before)
foreach($d in @($a.draft,$b.draft)){
    Check ('authority_false_'+$d.concept_key) (!$d.authority.generation_authorized-and!$d.authority.paid_provider_authorized-and!$d.authority.accept_authorized-and!$d.authority.publication_authorized)
}
SaveJson (Join-Path $OutputRoot 'expected.json') ([ordered]@{state_sha256=(StateSha);drafts=@(
    [ordered]@{label='A';key=$a.draft.concept_key;revision=$a.draft.current_revision_id;source_sha256=$shaA},
    [ordered]@{label='B';key=$b.draft.concept_key;revision=$b.draft.current_revision_id;source_sha256=$shaB}
)})
$pwsh=(Get-Process -Id $PID).Path
& $pwsh -NoProfile -File $PSCommandPath -ModuleRoot $ModuleRoot -OutputRoot $OutputRoot -Phase Reload
Check 'fresh_process_exit' ($LASTEXITCODE-eq0)
Check 'fresh_process_receipt' ((Get-Content (Join-Path $OutputRoot 'reload-receipt.json') -Raw|ConvertFrom-Json).status-ceq'PASS')
SaveJson (Join-Path $OutputRoot 'receipt.json') ([ordered]@{status='PASS_PERSISTED_SYNTHETIC_RESEARCH_IDENTITY';checks=$checks;synthetic=$true;market_proof=$false;real_owner_approvals=0;model_calls=0;external_dispatch=0;data_root=$OutputRoot})
Write-Output ('PASS: '+$OutputRoot)

param([string]$Candidate,[string]$Root)
$ErrorActionPreference='Stop'
. (Join-Path $Candidate 'Modules/Forge.UI.Layout.ps1')
$script:ConfirmMessages=@();$script:AllowDiscard=$false
function Confirm($Message){$script:ConfirmMessages+=@($Message);return $script:AllowDiscard}
$hostFake=[pscustomobject]@{handlers=@()};$hostFake|Add-Member ScriptMethod add_Closing {param($h) $this.handlers+=@($h)}
Initialize-ForgeUnsavedCloseGuard $hostFake;Initialize-ForgeUnsavedCloseGuard $hostFake
if($hostFake.handlers.Count-ne1){throw 'Duplicate close hook'}
$rows=@()
foreach($case in @('clean','creative','publication','both')){
 $script:Dirty=$case-in@('creative','both');$script:PublicationDirty=$case-in@('publication','both');$argsFake=[pscustomobject]@{Cancel=$false};$before=$script:ConfirmMessages.Count
 & $hostFake.handlers[0] $hostFake $argsFake
 if($argsFake.Cancel-ne($case-ne'clean')){throw 'Close guard dirty mismatch'}
 if($case-eq'clean'-and$script:ConfirmMessages.Count-ne$before){throw 'Clean close prompted'}
 $rows+=@{case=$case;cancel=$argsFake.Cancel;pass=$true}
}
$script:AllowDiscard=$true;$argsFake=[pscustomobject]@{Cancel=$false};& $hostFake.handlers[0] $hostFake $argsFake
if($argsFake.Cancel){throw 'Explicit discard did not close'}
if(($script:ConfirmMessages -join ' ')-notlike'*cannot be recovered*'){throw 'Missing loss warning'}
$rows+=@{case='explicit_discard_allowed_no_save_claim';pass=$true}
$null=New-Item -ItemType Directory -Path $Root -Force
@{checks=$rows;registration_count=$hostFake.handlers.Count;scope='Actual registration and close event scriptblock on headless event adapter. WPF parent-window lookup not visually executed. No writes/model calls from guard.';dirty_state_retained_until_explicit_close=$true}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $Root 'UNSAVED-GUARD-REPORT.json') -Encoding utf8
Write-Output ('PASS Forge close guard '+$rows.Count)

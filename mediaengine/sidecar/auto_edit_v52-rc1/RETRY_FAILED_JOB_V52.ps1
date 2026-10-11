param(
 [Parameter(Mandatory=$true)][string]$JobId,
 [string]$ArchivistRoot = "D:\Archivist",
 [switch]$RunNow
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Q=Join-Path $ArchivistRoot 'sidecars\auto_edit\queue';$State=Join-Path (Join-Path (Join-Path $Q 'jobs') $JobId) 'job_state.json'
if(!(Test-Path -LiteralPath $State -PathType Leaf)){throw "V41 job not found: $JobId"}
$Obj=Get-Content -LiteralPath $State -Raw|ConvertFrom-Json
if([string]$Obj.status -notin @('failed','retry_wait','quarantined')){throw "V41 retry allowed only for failed/retry_wait/quarantined jobs; current=$($Obj.status)"}
if(!$Obj.fingerprint){throw 'V41 failed job fingerprint missing'}
$Req=Join-Path (Split-Path -Parent $State) 'RETRY.request';if(Test-Path -LiteralPath $Req){throw 'V41 retry request already pending'};$Tmp=$Req+'.tmp'
[ordered]@{candidate='MEDENG_DROP_QUEUE_V40_RC1';job_id=$JobId;fingerprint=[string]$Obj.fingerprint;requested_at_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath $Tmp -Encoding UTF8
Move-Item -LiteralPath $Tmp -Destination $Req
Write-Output "V41_EXACT_RETRY_REQUESTED job=$JobId fingerprint=$($Obj.fingerprint)"
if($RunNow){$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt';if(!(Test-Path $Ptr)){throw 'MediaEngine auto-edit sidecar not activated'};$Slot=(Get-Content $Ptr -Raw).Trim();$Rel=Join-Path (Join-Path $Side 'releases') $Slot;& (Join-Path $Rel 'RUN_AUTO_EDIT_QUEUE_V37.ps1') -ArchivistRoot $ArchivistRoot -Once}

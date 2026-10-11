param([Parameter(Mandatory=$true)][string]$JobId,[string]$ArchivistRoot="D:\Archivist",[switch]$RunNow)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt';if(!(Test-Path $Ptr)){throw 'MediaEngine auto-edit sidecar not activated'};$Slot=(Get-Content $Ptr -Raw).Trim();$Rel=Join-Path (Join-Path $Side 'releases') $Slot
& (Join-Path $Rel 'RETRY_FAILED_JOB_V52.ps1') -JobId $JobId -ArchivistRoot $ArchivistRoot -RunNow:$RunNow

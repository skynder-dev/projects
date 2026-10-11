param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Latest=Join-Path $ArchivistRoot 'AutoEditOutput\LATEST.json'
if(!(Test-Path -LiteralPath $Latest -PathType Leaf)){throw 'V37 latest result pointer missing'}
$Obj=Get-Content -LiteralPath $Latest -Raw|ConvertFrom-Json
$Dir=[string]$Obj.outbox
if(!$Dir -or !(Test-Path -LiteralPath $Dir -PathType Container)){throw 'V37 latest result folder missing'}
$Review=Join-Path $Dir 'Review'
if(!(Test-Path -LiteralPath (Join-Path $Review 'DELIVERY_MANIFEST.json') -PathType Leaf)){throw 'V37 latest Review bundle missing'}
Start-Process explorer.exe -ArgumentList @($Dir)
Write-Output "V37_LATEST_RESULT_OPENED $Dir"

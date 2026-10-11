param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Latest=Join-Path $ArchivistRoot 'AutoEditOutput\LATEST.json'
if(!(Test-Path -LiteralPath $Latest -PathType Leaf)){throw 'V37 latest result pointer missing'}
$Obj=Get-Content -LiteralPath $Latest -Raw|ConvertFrom-Json
$Out=[string]$Obj.outbox
if(!$Out -or !(Test-Path -LiteralPath $Out -PathType Container)){throw 'V37 latest result folder missing'}
$Template=Join-Path $Out 'Review\SELECTION_OVERRIDE_TEMPLATE.txt'
if(!(Test-Path -LiteralPath $Template -PathType Leaf)){throw 'V37 override template missing'}
$Dir=Join-Path $Out 'Override';New-Item -ItemType Directory -Force -Path $Dir|Out-Null
$Req=Join-Path $Dir 'SELECTION_OVERRIDE.request.txt'
if(!(Test-Path -LiteralPath $Req -PathType Leaf)){Copy-Item -LiteralPath $Template -Destination $Req}
Start-Process notepad.exe -ArgumentList @($Req)
Write-Output "V37_OVERRIDE_REQUEST_OPENED $Req"

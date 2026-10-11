param([string]$ArchivistRoot='D:\Archivist')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Latest=Join-Path $ArchivistRoot 'AutoEditOutput\LATEST.json';if(!(Test-Path $Latest)){throw 'V37 latest result pointer missing'}
$L=Get-Content -Raw $Latest|ConvertFrom-Json;$Out=[string]$L.outbox;if(!$Out -or !(Test-Path $Out -PathType Container)){throw 'V37 latest job invalid'}
$Cmp=Join-Path $Out 'Review\VariantComparison';if(!(Test-Path (Join-Path $Cmp 'COMPARISON_MANIFEST.json'))){throw 'V37 comparison missing'}
Start-Process explorer.exe -ArgumentList @($Cmp)

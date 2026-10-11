param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$P=Join-Path $ArchivistRoot 'AutoEditOutput\LATEST_APPROVED.json';if(!(Test-Path $P -PathType Leaf)){throw 'V37 no approved result yet'}
$O=Get-Content $P -Raw|ConvertFrom-Json;$M=[string]$O.approved_manifest;if(!$M -or !(Test-Path $M -PathType Leaf)){throw 'V37 approved manifest missing'}
$D=Split-Path -Parent $M;Start-Process explorer.exe -ArgumentList @($D);Write-Output "V37_APPROVED_OPENED $D"

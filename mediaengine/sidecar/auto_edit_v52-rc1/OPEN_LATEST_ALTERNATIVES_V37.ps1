param([string]$Root='D:\Archivist')
$ErrorActionPreference='Stop'
$out=Join-Path $Root 'AutoEditOutput'
$latest=Join-Path $out 'LATEST.json'
if(!(Test-Path $latest)){ throw 'LATEST_JOB_MISSING' }
$j=Get-Content -Raw $latest | ConvertFrom-Json
$job=Join-Path $out ([string]$j.job_id)
$alt=Join-Path $job 'Alternatives'
if(!(Test-Path (Join-Path $alt 'ALTERNATIVES_MANIFEST.json'))){ throw 'AUTO_ALTERNATIVES_MISSING' }
Start-Process explorer.exe $alt

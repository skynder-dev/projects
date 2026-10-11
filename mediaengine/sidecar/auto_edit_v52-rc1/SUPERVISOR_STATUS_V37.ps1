param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Q=Join-Path $ArchivistRoot 'sidecars\auto_edit\queue';New-Item -ItemType Directory -Force -Path $Q|Out-Null
$Sup=Join-Path $Q 'SUPERVISOR_STATE.json';$Queue=Join-Path $Q 'STATUS.txt';$Out=Join-Path $Q 'SUPERVISOR_STATUS.txt'
$lines=New-Object System.Collections.Generic.List[string];$lines.Add('MediaEngine Auto Edit — Supervisor + Queue');$lines.Add(('='*48));$lines.Add('')
if(Test-Path $Sup){$S=Get-Content $Sup -Raw|ConvertFrom-Json;$lines.Add("Supervisor: $($S.status)");$lines.Add("Supervisor PID: $($S.supervisor_pid)");$lines.Add("Child PID: $($S.child_pid)");$lines.Add("Restart count: $($S.restart_count)");if($S.last_rc -ne $null){$lines.Add("Last RC: $($S.last_rc)")}}else{$lines.Add('Supervisor: NOT STARTED')}
$Auto=Join-Path (Join-Path $ArchivistRoot 'sidecars\auto_edit') 'autostart_v37.json';$lines.Add("Start with Windows: $([bool](Test-Path $Auto))");$lines.Add('');if(Test-Path $Queue){$lines.Add((Get-Content $Queue -Raw))}else{$lines.Add('Queue: no scan has run yet.')}
$lines|Set-Content -LiteralPath $Out -Encoding UTF8
Get-Content -LiteralPath $Out -Raw

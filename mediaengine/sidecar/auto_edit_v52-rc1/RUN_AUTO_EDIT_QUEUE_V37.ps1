param(
  [string]$ArchivistRoot = "D:\Archivist",
  [string]$Inbox = "",
  [string]$Outbox = "",
  [string]$QueueRoot = "",
  [double]$TargetSeconds = 30,
  [double]$PerFileTimeoutSeconds = 180,
  [double]$JobHardTimeoutSeconds = 0,
  [double]$SettleSeconds = 5,
  [double]$BatchSettleSeconds = 30,
  [double]$PollSeconds = 3,
  [switch]$Once,
  [switch]$Watch,
  [switch]$RetryFailed,
  [switch]$RecoverStaleLock,
  [switch]$RequireBatchReadyMarker
)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$SidecarRoot=Join-Path $ArchivistRoot 'sidecars\auto_edit'; $Ptr=Join-Path $SidecarRoot 'current.txt'
if (!(Test-Path -LiteralPath $Ptr -PathType Leaf)) { throw 'MediaEngine auto-edit sidecar not activated' }
$Slot=(Get-Content -LiteralPath $Ptr -Raw).Trim(); if (!$Slot) { throw 'MediaEngine auto-edit empty sidecar pointer' }
$Rel=Join-Path (Join-Path $SidecarRoot 'releases') $Slot
$ManifestPath=Join-Path $Rel 'V52_PAYLOAD_MANIFEST.json'; if (!(Test-Path $ManifestPath)) { throw 'V48 payload manifest missing in active slot' }
$Manifest=Get-Content $ManifestPath -Raw | ConvertFrom-Json
if($Manifest.slot -ne $Slot){ throw "V42 active slot/manifest mismatch: $Slot" }
function HashFile([string]$p){ (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
foreach($f in $Manifest.files){$p=Join-Path $Rel $f.path;if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "V37 payload missing: $($f.path)"};if((Get-Item -LiteralPath $p).Length -ne [int64]$f.bytes){throw "V37 payload size changed: $($f.path)"};if((HashFile $p) -ne $f.sha256){throw "V37 payload hash changed: $($f.path)"}}
$AllowedCode=@{};foreach($f in $Manifest.files){$AllowedCode[$f.path.Replace('/','\').ToLowerInvariant()]=$true};$CodeExt=@('.py','.ps1','.cmd','.vbs','.pyc','.pyd','.dll')
Get-ChildItem -LiteralPath $Rel -File -Recurse | ForEach-Object {if($CodeExt -contains $_.Extension.ToLowerInvariant()){$rp=$_.FullName.Substring($Rel.Length).TrimStart('\').ToLowerInvariant();if(!$AllowedCode.ContainsKey($rp)){throw "V37 unexpected code file in active slot: $rp"}}}
$IPath=Join-Path $Rel 'install_manifest.json';if(!(Test-Path $IPath)){throw 'V37 install manifest missing'};$I=Get-Content $IPath -Raw|ConvertFrom-Json
foreach($pair in @(@($I.python,$I.python_sha256),@($I.ffmpeg,$I.ffmpeg_sha256),@($I.ffprobe,$I.ffprobe_sha256))){if(!(Test-Path -LiteralPath $pair[0] -PathType Leaf)){throw "V37 pinned runtime missing: $($pair[0])"};if((HashFile $pair[0]) -ne $pair[1]){throw "V37 pinned runtime changed: $($pair[0])"}}
if(!$Inbox){$Inbox=Join-Path $ArchivistRoot 'AutoEditInbox'};if(!$Outbox){$Outbox=Join-Path $ArchivistRoot 'AutoEditOutput'};if(!$QueueRoot){$QueueRoot=Join-Path $SidecarRoot 'queue'}
New-Item -ItemType Directory -Force -Path $Inbox,$Outbox,$QueueRoot|Out-Null
if($Once -and $Watch){throw 'Choose either -Once or -Watch, not both'};$Mode='--watch';if($Once){$Mode='--once'}
$env:PYTHONDONTWRITEBYTECODE='1';$env:MEDENG_FFMPEG=$I.ffmpeg;$env:MEDENG_FFPROBE=$I.ffprobe;$env:PATH=(Split-Path -Parent $I.ffmpeg)+';'+$env:PATH
$Queue=Join-Path $Rel 'medeng_drop_queue_v40.py';$args=@($Queue,$Mode,'--inbox',$Inbox,'--outbox',$Outbox,'--queue-root',$QueueRoot,'--target-seconds',"$TargetSeconds",'--per-file-timeout-s',"$PerFileTimeoutSeconds",'--settle-seconds',"$SettleSeconds",'--batch-settle-seconds',"$BatchSettleSeconds",'--poll-seconds',"$PollSeconds")
if($RetryFailed){throw 'V43 broad RetryFailed is disabled; use RETRY_FAILED_JOB_V43.ps1 -JobId <exact-job-id>'};if($JobHardTimeoutSeconds -gt 0){$args+=@('--job-hard-timeout-s',"$JobHardTimeoutSeconds")};if($RecoverStaleLock){$args+='--recover-stale-lock'};if($RequireBatchReadyMarker){$args+='--require-batch-ready-marker'}
& $I.python @args
if($LASTEXITCODE -ne 0){throw "V37 queue exited rc=$LASTEXITCODE"}

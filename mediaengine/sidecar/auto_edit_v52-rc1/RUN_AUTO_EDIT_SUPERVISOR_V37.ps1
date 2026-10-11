param(
  [string]$ArchivistRoot = "D:\Archivist",
  [string]$Inbox = "",
  [string]$Outbox = "",
  [double]$TargetSeconds = 30,
  [double]$PerFileTimeoutSeconds = 180,
  [double]$JobHardTimeoutSeconds = 0,
  [double]$SettleSeconds = 5,
  [double]$BatchSettleSeconds = 30,
  [double]$PollSeconds = 3,
  [double]$RestartDelaySeconds = 2,
  [int]$MaxRestarts = 3,
  [double]$RestartWindowSeconds = 60,
  [switch]$RequireBatchReadyMarker
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$SidecarRoot=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $SidecarRoot 'current.txt'
if(!(Test-Path -LiteralPath $Ptr -PathType Leaf)){throw 'MediaEngine auto-edit sidecar not activated'}
$Slot=(Get-Content -LiteralPath $Ptr -Raw).Trim();if(!$Slot){throw 'MediaEngine auto-edit empty sidecar pointer'}
$Rel=Join-Path (Join-Path $SidecarRoot 'releases') $Slot;$ManifestPath=Join-Path $Rel 'V52_PAYLOAD_MANIFEST.json'
if(!(Test-Path $ManifestPath)){throw 'V40 payload manifest missing'};$Manifest=Get-Content $ManifestPath -Raw|ConvertFrom-Json
if($Manifest.slot -ne $Slot){throw "V40 active slot/manifest mismatch: $Slot"}
function HashFile([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
foreach($f in $Manifest.files){$p=Join-Path $Rel $f.path;if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "V37 payload missing: $($f.path)"};if((Get-Item $p).Length -ne [int64]$f.bytes){throw "V37 payload size changed: $($f.path)"};if((HashFile $p)-ne $f.sha256){throw "V37 payload hash changed: $($f.path)"}}
$Allowed=@{};foreach($f in $Manifest.files){$Allowed[$f.path.Replace('/','\').ToLowerInvariant()]=$true};$CodeExt=@('.py','.ps1','.cmd','.vbs','.pyc','.pyd','.dll')
Get-ChildItem -LiteralPath $Rel -File -Recurse|ForEach-Object{if($CodeExt -contains $_.Extension.ToLowerInvariant()){$rp=$_.FullName.Substring($Rel.Length).TrimStart('\').ToLowerInvariant();if(!$Allowed.ContainsKey($rp)){throw "V37 unexpected code file in active slot: $rp"}}}
$IPath=Join-Path $Rel 'install_manifest.json';if(!(Test-Path $IPath)){throw 'V37 install manifest missing'};$I=Get-Content $IPath -Raw|ConvertFrom-Json
foreach($pair in @(@($I.python,$I.python_sha256),@($I.ffmpeg,$I.ffmpeg_sha256),@($I.ffprobe,$I.ffprobe_sha256))){if(!(Test-Path -LiteralPath $pair[0] -PathType Leaf)){throw "V37 pinned runtime missing: $($pair[0])"};if((HashFile $pair[0]) -ne $pair[1]){throw "V37 pinned runtime changed: $($pair[0])"}}
if(!$Inbox){$Inbox=Join-Path $ArchivistRoot 'AutoEditInbox'};if(!$Outbox){$Outbox=Join-Path $ArchivistRoot 'AutoEditOutput'};$Q=Join-Path $SidecarRoot 'queue'
New-Item -ItemType Directory -Force -Path $Inbox,$Outbox,$Q|Out-Null
$env:PYTHONDONTWRITEBYTECODE='1';$env:PATH=(Split-Path -Parent $I.ffmpeg)+';'+$env:PATH
$Sup=Join-Path $Rel 'medeng_queue_supervisor_v40.py';$Queue=Join-Path $Rel 'medeng_drop_queue_v40.py'
$args=@($Sup,'--queue',$Queue,'--inbox',$Inbox,'--outbox',$Outbox,'--queue-root',$Q,'--target-seconds',"$TargetSeconds",'--per-file-timeout-s',"$PerFileTimeoutSeconds",'--settle-seconds',"$SettleSeconds",'--batch-settle-seconds',"$BatchSettleSeconds",'--poll-seconds',"$PollSeconds",'--restart-delay-s',"$RestartDelaySeconds",'--max-restarts',"$MaxRestarts",'--restart-window-s',"$RestartWindowSeconds")
if($RequireBatchReadyMarker){$args+='--require-batch-ready-marker'}
if($JobHardTimeoutSeconds -gt 0){$args+=@('--job-hard-timeout-s',"$JobHardTimeoutSeconds")}
& $I.python @args
if($LASTEXITCODE -ne 0){throw "V37 supervisor exited rc=$LASTEXITCODE"}

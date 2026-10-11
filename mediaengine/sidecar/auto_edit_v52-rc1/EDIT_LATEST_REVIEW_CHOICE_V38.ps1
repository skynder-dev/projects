param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function HashFile([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt'
if(!(Test-Path -LiteralPath $Ptr -PathType Leaf)){throw 'V38 sidecar not activated'}
$Slot=(Get-Content -LiteralPath $Ptr -Raw).Trim();if(!$Slot){throw 'V38 empty sidecar pointer'}
$Rel=Join-Path (Join-Path $Side 'releases') $Slot
$ManifestPath=Join-Path $Rel 'V52_PAYLOAD_MANIFEST.json';if(!(Test-Path $ManifestPath)){throw 'V40 payload manifest missing'}
$Manifest=Get-Content $ManifestPath -Raw|ConvertFrom-Json;if($Manifest.slot -ne $Slot){throw 'V39 slot/manifest mismatch'}
$Allowed=@{};foreach($f in $Manifest.files){$p=Join-Path $Rel $f.path;if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "V38 payload missing: $($f.path)"};if((Get-Item $p).Length -ne [int64]$f.bytes){throw "V38 payload size changed: $($f.path)"};if((HashFile $p)-ne $f.sha256){throw "V38 payload hash changed: $($f.path)"};$Allowed[$f.path.Replace('/','\').ToLowerInvariant()]=$true}
$CodeExt=@('.py','.ps1','.cmd','.vbs','.pyc','.pyd','.dll');Get-ChildItem -LiteralPath $Rel -File -Recurse|ForEach-Object{if($CodeExt -contains $_.Extension.ToLowerInvariant()){$rp=$_.FullName.Substring($Rel.Length).TrimStart('\').ToLowerInvariant();if(!$Allowed.ContainsKey($rp)){throw "V38 unexpected code file: $rp"}}}
$IPath=Join-Path $Rel 'install_manifest.json';if(!(Test-Path $IPath)){throw 'V38 install manifest missing'};$I=Get-Content $IPath -Raw|ConvertFrom-Json
foreach($pair in @(@($I.python,$I.python_sha256),@($I.ffmpeg,$I.ffmpeg_sha256),@($I.ffprobe,$I.ffprobe_sha256))){if(!(Test-Path -LiteralPath $pair[0] -PathType Leaf)){throw "V38 pinned runtime missing: $($pair[0])"};if((HashFile $pair[0]) -ne $pair[1]){throw "V38 pinned runtime changed: $($pair[0])"}}
$Latest=Join-Path $ArchivistRoot 'AutoEditOutput\LATEST.json';if(!(Test-Path $Latest)){throw 'V38 latest result pointer missing'};$L=Get-Content $Latest -Raw|ConvertFrom-Json
$Out=[string]$L.outbox;if(!$Out -or !(Test-Path $Out -PathType Container)){throw 'V38 latest job invalid'}
$env:PYTHONDONTWRITEBYTECODE='1';$env:PATH=(Split-Path -Parent $I.ffmpeg)+';'+$env:PATH
& $I.python (Join-Path $Rel 'medeng_review_decision_v39.py') prepare --job-outdir $Out
if($LASTEXITCODE -ne 0){throw "V38 prepare choice failed rc=$LASTEXITCODE"}
$Choice=Join-Path $Out 'Review\CHOICE.txt';if(!(Test-Path $Choice)){throw 'V38 choice file missing'}
$Cmp=Join-Path $Out 'Review\VariantComparison';if(Test-Path $Cmp){Start-Process explorer.exe -ArgumentList @($Cmp)}
Start-Process notepad.exe -ArgumentList @($Choice)
Write-Output "V38_REVIEW_CHOICE_OPENED $Choice"

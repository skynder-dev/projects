param(
  [string]$ArchivistRoot = "D:\Archivist",
  [switch]$Activate,
  [switch]$ForceRestage
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Slot = "v52-rc1"
$SidecarRoot = Join-Path $ArchivistRoot "sidecars\auto_edit"
$Releases = Join-Path $SidecarRoot "releases"
$Target = Join-Path $Releases $Slot
$Pointer = Join-Path $SidecarRoot "current.txt"
$PayloadManifest = Join-Path $Here "V52_PAYLOAD_MANIFEST.json"

function Fail([string]$m) { throw "V48: $m" }
function Full([string]$p) { return [IO.Path]::GetFullPath($p) }
function Under([string]$child,[string]$parent) {
  $c=(Full $child).TrimEnd('\')+'\'; $p=(Full $parent).TrimEnd('\')+'\'
  return $c.StartsWith($p,[StringComparison]::OrdinalIgnoreCase)
}
function Hash([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }

if (!(Test-Path -LiteralPath $ArchivistRoot -PathType Container)) { Fail "canonical Archivist root missing: $ArchivistRoot" }
if (!(Under $SidecarRoot $ArchivistRoot)) { Fail "sidecar root escaped canonical root" }
if (!(Test-Path -LiteralPath $PayloadManifest -PathType Leaf)) { Fail "payload manifest missing" }
$Manifest = Get-Content -LiteralPath $PayloadManifest -Raw | ConvertFrom-Json
if ($Manifest.slot -ne $Slot) { Fail "slot mismatch" }

# Verify source payload before any write.
foreach ($f in $Manifest.files) {
  $src=Join-Path $Here $f.path
  if (!(Test-Path -LiteralPath $src -PathType Leaf)) { Fail "source payload missing: $($f.path)" }
  if ((Get-Item -LiteralPath $src).Length -ne [int64]$f.bytes) { Fail "source size mismatch: $($f.path)" }
  if ((Hash $src) -ne $f.sha256) { Fail "source hash mismatch: $($f.path)" }
}

New-Item -ItemType Directory -Force -Path $Releases | Out-Null
if (Test-Path -LiteralPath $Target) {
  if (!$ForceRestage) {
    Write-Output "V52 target slot already exists; verifying exact bytes."
  } else {
    if (!(Under $Target $SidecarRoot)) { Fail "refusing delete outside sidecar root" }
    Remove-Item -LiteralPath $Target -Recurse -Force
  }
}
if (!(Test-Path -LiteralPath $Target)) { New-Item -ItemType Directory -Force -Path $Target | Out-Null }

foreach ($f in $Manifest.files) {
  $src=Join-Path $Here $f.path; $dst=Join-Path $Target $f.path
  $parent=Split-Path -Parent $dst
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path -LiteralPath $dst) {
    if ((Get-Item -LiteralPath $dst).Length -ne [int64]$f.bytes -or (Hash $dst) -ne $f.sha256) {
      Fail "existing target differs: $($f.path)"
    }
  } else {
    Copy-Item -LiteralPath $src -Destination $dst
  }
}
foreach ($f in $Manifest.files) {
  $dst=Join-Path $Target $f.path
  if ((Get-Item -LiteralPath $dst).Length -ne [int64]$f.bytes -or (Hash $dst) -ne $f.sha256) { Fail "target verification failed: $($f.path)" }
}
# Retain the exact payload manifest in the installed slot for launch-time integrity checks.
# When invoked from an already staged slot (for activation/idempotent verification), $Here == $Target;
# PowerShell rejects Copy-Item source->itself, so verify identity and skip that no-op copy.
$InstalledPayloadManifest = Join-Path $Target "V52_PAYLOAD_MANIFEST.json"
if ((Full $PayloadManifest) -ne (Full $InstalledPayloadManifest)) {
  Copy-Item -LiteralPath $PayloadManifest -Destination $InstalledPayloadManifest -Force
} else {
  if (!(Test-Path -LiteralPath $InstalledPayloadManifest -PathType Leaf)) { Fail "installed payload manifest missing" }
}

# Resolve active stable release only for runtime discovery. Stable files are NEVER written.
$ActiveRelease = $null
$StablePtr = Join-Path $ArchivistRoot "current.txt"
if (Test-Path -LiteralPath $StablePtr -PathType Leaf) {
  $s=(Get-Content -LiteralPath $StablePtr -Raw).Trim()
  if ($s) {
    $cand=Join-Path (Join-Path $ArchivistRoot "releases") $s
    if (Test-Path -LiteralPath $cand -PathType Container) { $ActiveRelease=$cand }
  }
}

$pyCandidates = New-Object System.Collections.Generic.List[string]
if ($env:MEDENG_PYTHON) { $pyCandidates.Add($env:MEDENG_PYTHON) }
$pyCandidates.Add((Join-Path $ArchivistRoot ".venv\Scripts\python.exe"))
$pyCandidates.Add((Join-Path $ArchivistRoot "runtime\python.exe"))
$pyCandidates.Add((Join-Path $ArchivistRoot "python\python.exe"))
if ($ActiveRelease) {
  $pyCandidates.Add((Join-Path $ActiveRelease "runtime\python.exe"))
  $pyCandidates.Add((Join-Path $ActiveRelease "python.exe"))
}
$cmd=Get-Command python.exe -ErrorAction SilentlyContinue
if ($cmd) { $pyCandidates.Add($cmd.Source) }
$Python = $pyCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -Unique -First 1
if (!$Python) { Fail "no Python runtime found; slot staged but NOT activated" }

function ResolveTool([string]$name,[string]$envValue) {
  $c = New-Object System.Collections.Generic.List[string]
  if ($envValue) { $c.Add($envValue) }
  $c.Add((Join-Path $ArchivistRoot "ffmpeg\bin\$name.exe"))
  $c.Add((Join-Path $ArchivistRoot "tools\ffmpeg\bin\$name.exe"))
  if ($ActiveRelease) {
    $c.Add((Join-Path $ActiveRelease "ffmpeg\bin\$name.exe"))
    $c.Add((Join-Path $ActiveRelease "tools\ffmpeg\bin\$name.exe"))
    $c.Add((Join-Path $ActiveRelease "$name.exe"))
  }
  $gc=Get-Command "$name.exe" -ErrorAction SilentlyContinue
  if ($gc) { $c.Add($gc.Source) }
  return ($c | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -Unique -First 1)
}
$FFmpeg=ResolveTool "ffmpeg" $env:MEDENG_FFMPEG
if (!$FFmpeg) {
  $bundled=Get-ChildItem -LiteralPath (Join-Path $ArchivistRoot '.venv\Lib\site-packages\imageio_ffmpeg\binaries') -Filter 'ffmpeg-*.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1
  if($bundled){$FFmpeg=$bundled.FullName}
}
if (!$FFmpeg) { Fail "ffmpeg not found; slot staged but NOT activated" }
# V41 has no external ffprobe dependency. Keep compatibility fields pinned to the same verified FFmpeg binary
# so inherited V37/V38 launchers can verify one native runtime identity without a fake executable.
$FFprobe=$FFmpeg

$Probe=Join-Path $Target "v43_runtime_probe.py"
$ProbeTmp=Join-Path $Target "runtime_probe.tmp.json"
$ProbeFinal=Join-Path $Target "runtime_resolution.json"
& $Python $Probe --ffmpeg $FFmpeg --package-root $Target | Set-Content -LiteralPath $ProbeTmp -Encoding UTF8
if ($LASTEXITCODE -ne 0) { Remove-Item $ProbeTmp -Force -ErrorAction SilentlyContinue; Fail "runtime probe failed; slot staged but NOT activated" }
$ProbeObj=Get-Content $ProbeTmp -Raw | ConvertFrom-Json
if (!$ProbeObj.ok) { Remove-Item $ProbeTmp -Force -ErrorAction SilentlyContinue; Fail "runtime probe returned not-ok" }
Move-Item -LiteralPath $ProbeTmp -Destination $ProbeFinal -Force

$Install = [ordered]@{
  candidate='MEDENG_AUTO_EDIT_V52_VIDEO_QUALITY_SIDECAR_RC1'; slot=$Slot; installed_at_utc=[DateTime]::UtcNow.ToString('o')
  archivist_root=(Full $ArchivistRoot); sidecar_root=(Full $SidecarRoot); release_root=(Full $Target)
  python=(Full $Python); python_sha256=(Hash $Python)
  ffmpeg=(Full $FFmpeg); ffmpeg_sha256=(Hash $FFmpeg)
  ffprobe=(Full $FFprobe); ffprobe_sha256=(Hash $FFprobe)
  probe_backend='FFMPEG_INPUT_METADATA_V41'; external_ffprobe_required=$false; ffprobe_compatibility_alias=$true
  stable_pointer_touched=$false; stable_files_touched=$false
  activated=[bool]$Activate
}
$InstallPath=Join-Path $Target "install_manifest.json"
$Install | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$InstallPath.tmp" -Encoding UTF8
Move-Item -LiteralPath "$InstallPath.tmp" -Destination $InstallPath -Force

if ($Activate) {
  New-Item -ItemType Directory -Force -Path $SidecarRoot | Out-Null
  Set-Content -LiteralPath "$Pointer.tmp" -Value $Slot -Encoding ASCII -NoNewline
  Move-Item -LiteralPath "$Pointer.tmp" -Destination $Pointer -Force
  Write-Output "V52_ACTIVATED slot=$Slot"
} else {
  Write-Output "V52_STAGED_NOT_ACTIVE slot=$Slot"
}
Write-Output "python=$Python"
Write-Output "ffmpeg=$FFmpeg"
Write-Output "probe_backend=FFMPEG_INPUT_METADATA_V41"

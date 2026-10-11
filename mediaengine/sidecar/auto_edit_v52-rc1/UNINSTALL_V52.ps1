param(
  [string]$ArchivistRoot="D:\Archivist",
  [switch]$RemoveRelease,
  [switch]$RemoveQueueState
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Slot='v52-rc1';$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt';$Rel=Join-Path (Join-Path $Side 'releases') $Slot;$Q=Join-Path $Side 'queue'
function Full([string]$p){[IO.Path]::GetFullPath($p)};function Under([string]$c,[string]$p){((Full $c).TrimEnd('\')+'\').StartsWith(((Full $p).TrimEnd('\')+'\'),[StringComparison]::OrdinalIgnoreCase)}
# request graceful stop first
New-Item -ItemType Directory -Force -Path $Q|Out-Null;Set-Content -LiteralPath (Join-Path $Q 'STOP.request') -Value ([DateTime]::UtcNow.ToString('o')) -Encoding ASCII
# remove only our own Startup shortcut if present
$Startup=[Environment]::GetFolderPath('Startup');$Link=Join-Path $Startup 'MediaEngine Auto Edit Worker.lnk'
if(Test-Path $Link){$W=New-Object -ComObject WScript.Shell;$L=$W.CreateShortcut($Link);if(([string]$L.Arguments) -match 'Start_Auto_Edit_Inbox_V37\.vbs'){Remove-Item -LiteralPath $Link -Force}}
Remove-Item -LiteralPath (Join-Path $Side 'autostart_v37.json') -Force -ErrorAction SilentlyContinue
if(Test-Path $Ptr){$cur=(Get-Content $Ptr -Raw).Trim();if($cur -eq $Slot){Remove-Item $Ptr -Force}}
if($RemoveRelease -and (Test-Path $Rel)){if(!(Under $Rel $Side)){throw 'refusing delete outside sidecar root'};Remove-Item $Rel -Recurse -Force}
if($RemoveQueueState -and (Test-Path $Q)){if(!(Under $Q $Side)){throw 'refusing queue delete outside sidecar root'};Remove-Item $Q -Recurse -Force}
Write-Output 'V48_AUTO_EDIT_SIDECAR_DEACTIVATED_STABLE_OUTBOX_AND_APPROVED_RESULTS_UNTOUCHED'

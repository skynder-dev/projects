param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Startup=[Environment]::GetFolderPath('Startup');$Link=Join-Path $Startup 'MediaEngine Auto Edit Worker.lnk'
if(Test-Path $Link){$W=New-Object -ComObject WScript.Shell;$L=$W.CreateShortcut($Link);if(([string]$L.Arguments) -notmatch 'Start_Auto_Edit_Inbox_V37\.vbs'){throw 'V37 refusing to delete foreign Startup shortcut'};Remove-Item -LiteralPath $Link -Force}
Remove-Item -LiteralPath (Join-Path $Side 'autostart_v37.json') -Force -ErrorAction SilentlyContinue
Write-Output 'V37_AUTOSTART_DISABLED'

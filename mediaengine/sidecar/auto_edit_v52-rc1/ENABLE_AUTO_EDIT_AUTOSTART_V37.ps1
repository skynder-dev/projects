param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt';if(!(Test-Path $Ptr)){throw 'MediaEngine auto-edit sidecar not activated'}
$Slot=(Get-Content $Ptr -Raw).Trim();$Rel=Join-Path (Join-Path $Side 'releases') $Slot;$Start=Join-Path $Rel 'Start_Auto_Edit_Inbox_V37.vbs';if(!(Test-Path $Start)){throw 'V37 start script missing'}
$Startup=[Environment]::GetFolderPath('Startup');if(!$Startup){throw 'Windows Startup folder unavailable'};$Link=Join-Path $Startup 'MediaEngine Auto Edit Worker.lnk';$W=New-Object -ComObject WScript.Shell;$L=$W.CreateShortcut($Link);$L.TargetPath=(Join-Path $env:WINDIR 'System32\wscript.exe');$L.Arguments='"'+$Start+'"';$L.WorkingDirectory=$Rel;$L.Description='MediaEngine Auto Edit local worker';$L.Save()
[ordered]@{candidate='MEDENG_AUTO_EDIT_V37_ATOMIC_OVERRIDE_SIDECAR_RC1';enabled=$true;shortcut=$Link;target=$Start;enabled_at_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $Side 'autostart_v37.json') -Encoding UTF8
Write-Output "V37_AUTOSTART_ENABLED $Link"

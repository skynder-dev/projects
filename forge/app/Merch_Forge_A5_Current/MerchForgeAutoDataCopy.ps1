# Merch Forge · automatic daily data copy (runs hidden, in its own process, so the window never waits)
# Same format and checks as Home -> My data -> Save a copy. Keeps the newest copies in <data>\backups\auto-*.zip.
param([string]$StateRoot=(Join-Path $env:LOCALAPPDATA 'MerchForge'),[int]$Keep=7)
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
function Get-PropertyValue($Object,[string]$Name){ if($null -eq $Object){return $null}; if($Object -is [System.Collections.IDictionary]){ if($Object.Contains($Name)){return $Object[$Name]}; return $null }; $p=$Object.PSObject.Properties[$Name]; if($null -eq $p){return $null}; return $p.Value }
function Ensure-Dir([string]$Path){ if(-not (Test-Path -LiteralPath $Path)){ New-Item -ItemType Directory -Path $Path -Force | Out-Null } }
function Get-UiText([string]$Key,[string]$Fallback=''){ return $Fallback }
$script:StateRoot=$StateRoot; $script:UiText=$null; $script:StaticUiTranslations=$null
$script:AppVersion=''; try{ $m=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'candidate_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json; $script:AppVersion=[string]$m.desktop.app_version }catch{}
. (Join-Path $PSScriptRoot 'Modules\Forge.DataBackup.ps1')
$backups=Join-Path $StateRoot 'backups'; Ensure-Dir $backups
$status=Join-Path $backups 'auto-last.json'
$result=[ordered]@{schema='forge.auto_data_copy.v1';at=[DateTime]::UtcNow.ToString('o');ok=$false;file='';files=0;error=''}
try {
    if(-not (Test-Path -LiteralPath (Join-Path $StateRoot 'local-core-v1') -PathType Container)){ throw 'No local data yet.' }
    $zip=Join-Path $backups ('auto-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.zip')
    $r=New-ForgeDataBackup $StateRoot $zip
    $result.ok=$true; $result.file=$zip; $result.files=[int]$r.file_count
    foreach($old in @(Get-ChildItem -LiteralPath $backups -Filter 'auto-*.zip' -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -Skip $Keep)){ try{ Remove-Item -LiteralPath $old.FullName -Force }catch{} }
} catch { $result.error=$_.Exception.Message }
[IO.File]::WriteAllText($status,($result | ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
if($result.ok){ exit 0 } else { exit 1 }

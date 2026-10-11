param([string]$ArchivistRoot="D:\Archivist")
$ErrorActionPreference='Stop';$Q=Join-Path $ArchivistRoot 'sidecars\auto_edit\queue';New-Item -ItemType Directory -Force -Path $Q|Out-Null
Set-Content -LiteralPath (Join-Path $Q 'STOP.request') -Value ([DateTime]::UtcNow.ToString('o')) -Encoding ASCII
Write-Output 'V37_STOP_REQUESTED'

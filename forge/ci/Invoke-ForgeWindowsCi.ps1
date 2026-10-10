# Merch Forge · Windows CI driver (Windows PowerShell 5.1)
# 1) real startup preflight (integrity, parser, WPF XAML load, provider pipeline self-test)
# 2) research-draft headless self-test under Windows PowerShell 5.1 (incl. 054 rollback compatibility)
# 3) real WPF window smoke in two processes (create + restart), with screenshots
param([string]$RepoForge = (Split-Path $PSScriptRoot -Parent), [string]$OutDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'ci-out'))
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$app = Join-Path $RepoForge 'app\Merch_Forge_A5_Current'
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$summary = [ordered]@{ schema='forge.windows_ci.v1'; powershell=$PSVersionTable.PSVersion.ToString(); os=[Environment]::OSVersion.VersionString; executed_at=[DateTime]::UtcNow.ToString('o'); steps=[ordered]@{} }
function Step([string]$Name,[bool]$Ok,$Detail) { $summary.steps[$Name]=[ordered]@{pass=$Ok;detail=$Detail}; Write-Output ("[{0}] {1}" -f $(if($Ok){'PASS'}else{'FAIL'}),$Name) }
function Run-Child([string[]]$Arguments,[int]$TimeoutSec=600) {
    $p = Start-Process -FilePath $ps -ArgumentList $Arguments -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $OutDir 'child.out.txt') -RedirectStandardError (Join-Path $OutDir 'child.err.txt')
    if(-not $p.WaitForExit($TimeoutSec*1000)){ try{$p.Kill()}catch{}; return [pscustomobject]@{code=-1;out='TIMEOUT';err=''} }
    return [pscustomobject]@{code=$p.ExitCode;out=(Get-Content (Join-Path $OutDir 'child.out.txt') -Raw -ErrorAction SilentlyContinue);err=(Get-Content (Join-Path $OutDir 'child.err.txt') -Raw -ErrorAction SilentlyContinue)}
}
$env:LOCALAPPDATA = Join-Path $OutDir 'localappdata'; New-Item -ItemType Directory -Path $env:LOCALAPPDATA -Force | Out-Null
$env:TEMP = Join-Path $OutDir 'temp'; New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null

# 1) the real startup preflight, exactly as MerchForgeLauncher.cmd runs it
$r = Run-Child @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $app 'MerchForgePreflight.ps1'),'-PackageRoot',$app,'-RunProviderPipelineSelfTest') 900
Step 'preflight_integrity_parser_xaml_provider_selftest' ($r.code -eq 0) ([string]$r.out).Trim()

# 2) headless research-draft self-test on Windows PowerShell 5.1 (+ 054 rollback read)
$legacy = Join-Path $OutDir 'legacy054'
Expand-Archive -LiteralPath (Join-Path $RepoForge 'archive\054_Merch_Forge_DISCOVER_RESEARCH_RC.zip') -DestinationPath $legacy -Force
$st = Join-Path $OutDir 'research-draft-selftest.json'
$r = Run-Child @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $app 'MerchForgeResearchDraftSelfTest.ps1'),'-OutputPath',$st,'-LegacyPackageRoot',(Join-Path $legacy '054_Merch_Forge_DISCOVER_RESEARCH_RC\Merch_Forge_A5_Current')) 600
$stj = $null; if(Test-Path $st){ $stj = Get-Content $st -Raw -Encoding UTF8 | ConvertFrom-Json }
$failed=@(); if($stj){ foreach($ph in $stj.phases.PSObject.Properties){ if($ph.Value.PSObject.Properties['fatal']){$failed+=($ph.Name+': FATAL '+$ph.Value.fatal)}; if($ph.Value.PSObject.Properties['checks']){ foreach($c in $ph.Value.checks.PSObject.Properties){ if(-not $c.Value.pass){ $failed+=($ph.Name+'.'+$c.Name) } } } } }
Step 'research_draft_selftest_ps51' ($r.code -eq 0 -and $null -ne $stj -and $stj.status -eq 'PASS') ([ordered]@{status=$(if($stj){$stj.status}else{'no report'});passed=$(if($stj){$stj.passed}else{0});total=$(if($stj){$stj.total}else{0});failed=$failed;out=([string]$r.out).Trim()})

# 3) real WPF window smoke: CI-only copy of the Workbench with the hook dot-sourced before ShowDialog
$wb = Get-Content (Join-Path $app 'MerchForgeWorkbench.ps1') -Raw -Encoding UTF8
$marker = 'try { Write-AppLog ''INFO'' "Starting Workbench $script:AppVersion"; $null=$Window.ShowDialog()'
if($wb.IndexOf($marker) -lt 0){ Step 'wpf_hook_inserted' $false 'ShowDialog marker not found'; } else {
    $ciCopy = Join-Path $app 'MerchForgeWorkbench.ci.ps1'
    [IO.File]::WriteAllText($ciCopy, $wb.Replace($marker, ". `$env:FORGE_CI_HOOK`n"+$marker), (New-Object Text.UTF8Encoding($true)))
    $env:FORGE_CI_HOOK = Join-Path $PSScriptRoot 'ForgeWpfSmoke.hook.ps1'; $env:FORGE_CI_OUT = $OutDir
    foreach($phase in @('create','restart')){
        $env:FORGE_CI_PHASE = $phase; $env:FORGE_CI_RESULT = Join-Path $OutDir ("wpf-$phase.json"); Remove-Item $env:FORGE_CI_RESULT -ErrorAction SilentlyContinue
        $r = Run-Child @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-STA','-File',$ciCopy) 240
        $j=$null; if(Test-Path $env:FORGE_CI_RESULT){ $j = Get-Content $env:FORGE_CI_RESULT -Raw -Encoding UTF8 | ConvertFrom-Json }
        $bad=@(); if($j){ foreach($c in $j.checks.PSObject.Properties){ if(-not $c.Value.pass){ $bad += ($c.Name+' => '+$c.Value.detail) } } }
        $ok = ($null -ne $j -and $null -eq $j.fatal -and $bad.Count -eq 0 -and @($j.checks.PSObject.Properties).Count -gt 0)
        Step ("wpf_window_$phase") $ok ([ordered]@{checks=$(if($j){@($j.checks.PSObject.Properties).Count}else{0});failed=$bad;fatal=$(if($j){$j.fatal}else{'no result; exit '+$r.code});screenshots=$(if($j){$j.screenshots}else{@()});stderr=([string]$r.err).Trim()})
    }
    Remove-Item $ciCopy -Force -ErrorAction SilentlyContinue
}

$all = @($summary.steps.Values | Where-Object { -not $_.pass }).Count -eq 0
$summary.status = $(if($all){'PASS'}else{'FAIL'})
$summary | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $OutDir 'windows-ci-summary.json') -Encoding UTF8
if($env:GITHUB_STEP_SUMMARY){
    $md = @("## Merch Forge · Windows CI: **$($summary.status)**", '', "Windows PowerShell $($summary.powershell) · $($summary.os)", '', '| Step | Result |', '|---|---|')
    foreach($k in $summary.steps.Keys){ $md += ('| {0} | {1} |' -f $k, $(if($summary.steps[$k].pass){'PASS'}else{'**FAIL**'})) }
    $md += ''; $md += 'Screenshots and JSON reports: workflow artifact `forge-windows-ci`.'
    Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value ($md -join "`n") -Encoding UTF8
}
if($all){ exit 0 } else { exit 1 }

# Merch Forge · install / start / upgrade test on real Windows (Windows PowerShell 5.1)
# Uses the RELEASE ZIP exactly as the owner gets it:
#   A) extract -> double-click START_0xx_MERCH_FORGE.vbs -> the window opens -> close it -> clean exit
#   B) extract -> Install Merch Forge.vbs -> "installed" dialog -> files + desktop shortcut
#   C) install 054 first, then this release over it -> previous version kept as app.previous -> start the installed app
# Script-host dialogs (MsgBox) are read and answered through Windows UI Automation, like a person clicking OK.
param([Parameter(Mandatory=$true)][string]$RepoForge,[Parameter(Mandatory=$true)][string]$OutDir)
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$work=Join-Path $OutDir 'install-test'; if(Test-Path $work){ Remove-Item $work -Recurse -Force }; New-Item -ItemType Directory -Path $work -Force | Out-Null
$wscript=Join-Path $env:SystemRoot 'System32\wscript.exe'
$R=[ordered]@{checks=[ordered]@{};dialogs=@();notes=@()}
function Check([string]$Name,[bool]$Ok,$Detail=''){ $R.checks[$Name]=[ordered]@{pass=$Ok;detail=[string]$Detail} }

$manifest=Get-Content (Join-Path $RepoForge 'app\Merch_Forge_A5_Current\candidate_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$pkg=[string]$manifest.package_name; $num=('{0:000}' -f [int]$manifest.package_number)
$zip=Join-Path $RepoForge ('releases\'+$pkg+'.zip')
Check 'release_zip_present' (Test-Path -LiteralPath $zip) $zip

function Expand-Release([string]$Zip,[string]$Dest){ Expand-Archive -LiteralPath $Zip -DestinationPath $Dest -Force; return (Get-ChildItem -LiteralPath $Dest -Directory | Select-Object -First 1).FullName }
function Get-ProcessWindows([int]$ProcessId){
    $root=[Windows.Automation.AutomationElement]::RootElement
    $cond=New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::ProcessIdProperty,$ProcessId)
    return @($root.FindAll([Windows.Automation.TreeScope]::Children,$cond))
}
function Read-Dialog($W){
    $tc=New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Text)
    $texts=@($W.FindAll([Windows.Automation.TreeScope]::Descendants,$tc) | ForEach-Object { $_.Current.Name })
    return [pscustomobject]@{title=[string]$W.Current.Name;text=($texts -join ' ')}
}
function Press-Ok($W){
    $bc=New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Button)
    foreach($b in @($W.FindAll([Windows.Automation.TreeScope]::Descendants,$bc))){ if($b.Current.Name -in @('OK','ОК','Aceptar')){ $b.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true } }
    return $false
}
function Invoke-ScriptHost([string]$Vbs,[string]$Lad,[int]$TimeoutSec=240,[scriptblock]$UntilDone=$null){
    # Runs a .vbs like a double-click; answers every dialog with OK and records its text. Returns exit code and dialogs.
    $env:LOCALAPPDATA=$Lad
    $p=Start-Process -FilePath $wscript -ArgumentList ('"'+$Vbs+'"') -PassThru; $null=$p.Handle
    $seen=@(); $t0=[DateTime]::UtcNow
    while(-not $p.HasExited){
        foreach($w in @(Get-ProcessWindows $p.Id)){ try{ $d=Read-Dialog $w; $seen+=$d; $R.dialogs+=($d.title+': '+$d.text); $null=Press-Ok $w }catch{} }
        if($null -ne $UntilDone -and (& $UntilDone)){ break }
        if(([DateTime]::UtcNow-$t0).TotalSeconds -gt $TimeoutSec){ try{$p.Kill()}catch{}; return [pscustomobject]@{code=-1;dialogs=$seen;timeout=$true;process=$p} }
        Start-Sleep -Milliseconds 400
    }
    $code=$null; if($p.HasExited){ $p.WaitForExit(); $code=[int]$p.ExitCode }
    return [pscustomobject]@{code=$code;dialogs=$seen;timeout=$false;process=$p}
}
function Wait-File([string]$Pattern,[int]$TimeoutSec){ $t0=[DateTime]::UtcNow; while(([DateTime]::UtcNow-$t0).TotalSeconds -lt $TimeoutSec){ $f=@(Get-ChildItem -Path $Pattern -ErrorAction SilentlyContinue); if($f.Count){ return $f[0] }; Start-Sleep -Milliseconds 500 }; return $null }
function Find-AppWindowProcess([int]$TimeoutSec){
    $t0=[DateTime]::UtcNow
    while(([DateTime]::UtcNow-$t0).TotalSeconds -lt $TimeoutSec){
        $p=@(Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like 'Merch Forge*' }); if($p.Count){ return $p[0] }
        Start-Sleep -Milliseconds 500
    }
    return $null
}
function Test-StartAndClose([string]$Label,[string]$Vbs,[string]$Lad){
    # The start helper waits for the window's ready flag, then for the exit code; close the window like a person would.
    $logs=Join-Path $Lad 'MerchForge\logs'
    $env:LOCALAPPDATA=$Lad
    $helper=Start-Process -FilePath $wscript -ArgumentList ('"'+$Vbs+'"') -PassThru; $null=$helper.Handle
    $ready=Wait-File (Join-Path $logs 'MerchForge-ready-*.flag') 200
    Check ($Label+'_window_ready') ($null -ne $ready) $(if($ready){$ready.Name}else{'no ready flag; dialogs: '+(($R.dialogs) -join ' | ')})
    $app=Find-AppWindowProcess 60
    Check ($Label+'_window_visible') ($null -ne $app) $(if($app){$app.MainWindowTitle}else{'no window'})
    if($null -ne $app){ Start-Sleep -Seconds 3; $null=$app.CloseMainWindow() }
    $exit=Wait-File (Join-Path $logs 'MerchForge-exit-*.txt') 60
    $code=if($exit){([string](Get-Content -LiteralPath $exit.FullName -Raw)).Trim()}else{'none'}
    Check ($Label+'_clean_exit') ($code -eq '0') $code
    # the helper must end on its own without an error dialog
    $t0=[DateTime]::UtcNow; $dlg=@()
    while(-not $helper.HasExited -and ([DateTime]::UtcNow-$t0).TotalSeconds -lt 30){ foreach($w in @(Get-ProcessWindows $helper.Id)){ try{ $d=Read-Dialog $w; $dlg+=$d; $R.dialogs+=($d.title+': '+$d.text); $null=Press-Ok $w }catch{} }; Start-Sleep -Milliseconds 400 }
    if(-not $helper.HasExited){ try{$helper.Kill()}catch{} }
    Check ($Label+'_no_error_dialog') ($dlg.Count -eq 0) ((@($dlg | ForEach-Object { $_.title+': '+$_.text })) -join ' | ')
    $launch=@(Get-ChildItem -Path (Join-Path $logs 'MerchForge-launch-*.log') -ErrorAction SilentlyContinue)
    if($launch.Count){ $R.notes+=($Label+' launch log tail: '+(([string](Get-Content -LiteralPath $launch[0].FullName -Raw)) -replace '\s+',' ').Substring(0,[Math]::Min(400,([string](Get-Content -LiteralPath $launch[0].FullName -Raw)).Length))) }
}
function Get-Installed([string]$Lad){ $m=Join-Path $Lad 'Programs\MerchForge\app\candidate_manifest.json'; if(Test-Path -LiteralPath $m){ return (Get-Content -LiteralPath $m -Raw -Encoding UTF8 | ConvertFrom-Json) }; return $null }

try {
    # A) START from the extracted ZIP
    $relA=Expand-Release $zip (Join-Path $work 'a')
    $start=Join-Path $relA ('START_'+$num+'_MERCH_FORGE.vbs')
    Check 'start_entrypoint_present' (Test-Path -LiteralPath $start) $start
    Test-StartAndClose 'start' $start (Join-Path $work 'lad-start')

    # B) fresh install
    $relB=Expand-Release $zip (Join-Path $work 'b')
    $ladB=Join-Path $work 'lad-install'
    $r=Invoke-ScriptHost (Join-Path $relB 'Merch_Forge_A5_Current\Install Merch Forge.vbs') $ladB 300
    $ok=@($r.dialogs | Where-Object { $_.text -like '*Merch Forge is installed for this Windows account*' }).Count -eq 1
    Check 'install_success_dialog' ($ok -and $r.code -eq 0) ('exit '+$r.code+'; '+((@($r.dialogs | ForEach-Object { $_.title+': '+$_.text })) -join ' | '))
    $inst=Get-Installed $ladB
    Check 'install_files_and_version' ($null -ne $inst -and [string]$inst.package_name -eq $pkg -and -not (Test-Path (Join-Path $ladB 'Programs\MerchForge\install.lock'))) $(if($inst){[string]$inst.package_name}else{'not installed'})
    $lnk=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Merch Forge.lnk'
    Check 'install_desktop_shortcut' (Test-Path -LiteralPath $lnk) $lnk

    # C) upgrade over 054
    $ladC=Join-Path $work 'lad-upgrade'
    $old=Expand-Release (Join-Path $RepoForge 'archive\054_Merch_Forge_DISCOVER_RESEARCH_RC.zip') (Join-Path $work 'c054')
    $r0=Invoke-ScriptHost (Join-Path $old 'Merch_Forge_A5_Current\Install Merch Forge.vbs') $ladC 300
    $i0=Get-Installed $ladC
    Check 'upgrade_054_installed_first' ($r0.code -eq 0 -and $null -ne $i0 -and [string]$i0.package_name -like '054_*') $(if($i0){[string]$i0.package_name}else{'exit '+$r0.code})
    $relC=Expand-Release $zip (Join-Path $work 'cnew')
    $r1=Invoke-ScriptHost (Join-Path $relC 'Merch_Forge_A5_Current\Install Merch Forge.vbs') $ladC 300
    $i1=Get-Installed $ladC
    $prev=Join-Path $ladC 'Programs\MerchForge\app.previous\candidate_manifest.json'
    $p0=if(Test-Path -LiteralPath $prev){ Get-Content -LiteralPath $prev -Raw -Encoding UTF8 | ConvertFrom-Json }else{$null}
    Check 'upgrade_installed_new' ($r1.code -eq 0 -and $null -ne $i1 -and [string]$i1.package_name -eq $pkg -and [string]$i1.installer_generation -gt [string]$i0.installer_generation) ('exit '+$r1.code+'; '+$(if($i1){[string]$i1.package_name+' gen '+[string]$i1.installer_generation}else{'none'}))
    Check 'upgrade_keeps_previous' ($null -ne $p0 -and [string]$p0.package_name -like '054_*') $(if($p0){[string]$p0.package_name}else{'no app.previous'})
    Test-StartAndClose 'upgraded' (Join-Path $ladC 'Programs\MerchForge\app\Start Merch Forge.vbs') $ladC
    # Downgrade guard: installing 054 again over the new version must be refused without changes
    $r2=Invoke-ScriptHost (Join-Path $old 'Merch_Forge_A5_Current\Install Merch Forge.vbs') $ladC 300
    $i2=Get-Installed $ladC
    Check 'downgrade_blocked' ($r2.code -eq 22 -and $null -ne $i2 -and [string]$i2.package_name -eq $pkg) ('exit '+$r2.code+'; '+$(if($i2){[string]$i2.package_name}else{'none'}))
} catch {
    $R['fatal']=($_.Exception.Message+' @ '+$_.InvocationInfo.PositionMessage)
}
$R | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $OutDir 'install-test.json') -Encoding UTF8
$failed=@($R.checks.Keys | Where-Object { -not $R.checks[$_].pass })
if($R.Contains('fatal') -or $failed.Count){ exit 1 } else { exit 0 }

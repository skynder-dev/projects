# Merch Forge · Internal diagnostics boundary
# Hidden from primary product navigation. No product mutations.
function Get-AboutText {
    $backend=if($script:BackendVersion){[string]$script:BackendVersion}else{'Not connected'}
    return ("Product: Merch Forge Workbench`nApp version: {0}`nBackend version: {1}`nConnection: {2}`n`nMerch Forge is a private desktop workspace for reviewing concepts, generating and reviewing visual variants, preparing listing metadata, and assembling owner delivery packages. It is designed so the system prepares known information first; manual typing is an optional edit or override, not the normal workflow.`n`nGenerate, Accept, and external submission remain separate explicit owner actions." -f $script:AppVersion,$backend,$script:ConnectionState)
}
function Get-DiagnosticSummary {
    $actor=if($null -ne $script:Session){[string]$script:Session.actor_key}else{''}; $role=if($null -ne $script:Session){[string]$script:Session.role_key}else{''}
    $last=$script:LastDiagnostic
    return ("Merch Forge diagnostics`nApp: {0}`nBackend: {1}`nConnection: {2}`nEndpoint: {3}`nActor key: {4}`nRole key: {5}`nLog: {6}`n`nLast diagnostic`nWhen: {7}`nCategory: {8}`nHTTP: {9}`nAction: {10}`nUser message: {11}`nTechnical: {12}" -f $script:AppVersion,$(if($script:BackendVersion){$script:BackendVersion}else{'n/a'}),$script:ConnectionState,$script:ApiUrl,$actor,$role,$script:RuntimeLogPath,$last.when,$last.category,$last.http_status,$last.action,$last.user_message,$last.technical)
}
function Get-DiagnosticHumanSummary {
    $last=$script:LastDiagnostic
    $backend=if($script:BackendVersion){[string]$script:BackendVersion}else{'Not connected'}
    $lastLine=if($null -eq $last -or [string]::IsNullOrWhiteSpace([string]$last.when)){'No runtime issue has been recorded in this session.'}else{"Last issue: $($last.user_message)"}
    return ("Connection: {0}`nBackend: {1}`n{2}`n`nDiagnostics are read-only. Opening this panel never restarts, closes, or changes the Workbench." -f $script:ConnectionState,$backend,$lastLine)
}
function Hide-UtilityPanel {
    if($null -ne $UtilityOverlay){$UtilityOverlay.Visibility='Collapsed'}
    if($null -ne $MainTabs){$MainTabs.Focus() | Out-Null}
}
function Show-UtilityPanel([string]$Mode) {
    if($null -eq $UtilityOverlay){return}
    if($Mode -eq 'diagnostics'){
        $UtilityKicker.Text='SYSTEM HEALTH'
        $UtilityTitle.Text='Diagnostics'
        $UtilitySummaryText.Text='A safe, in-app view of connection and runtime health.'
        $UtilityBodyText.Text=Get-DiagnosticHumanSummary
        $UtilityTechnicalText.Text=Get-DiagnosticSummary
        $UtilityTechnicalExpander.Visibility='Visible'; $UtilityTechnicalExpander.IsExpanded=$false
        $UtilityCopyButton.Visibility='Visible'; $UtilityOpenLogButton.Visibility='Visible'
    } else {
        $UtilityKicker.Text='MERCH FORGE'
        $UtilityTitle.Text='About Merch Forge'
        $UtilitySummaryText.Text='Concept to owner-ready package, without turning you into a form operator.'
        $UtilityBodyText.Text=Get-AboutText
        $UtilityTechnicalText.Text=("Endpoint: {0}`nRuntime log: {1}" -f $script:ApiUrl,$script:RuntimeLogPath)
        $UtilityTechnicalExpander.Visibility='Visible'; $UtilityTechnicalExpander.IsExpanded=$false
        $UtilityCopyButton.Visibility='Collapsed'; $UtilityOpenLogButton.Visibility='Collapsed'
    }
    $UtilityOverlay.Visibility='Visible'
    $UtilityCloseButton.Focus() | Out-Null
}
function Show-About { try{Show-UtilityPanel 'about'}catch{Write-AppLog 'ERROR' ("About panel: "+$_.Exception.Message);$StatusText.Text='About panel is temporarily unavailable.'} }
function Show-Diagnostics { try{Show-UtilityPanel 'diagnostics'}catch{Write-AppLog 'ERROR' ("Diagnostics panel: "+$_.Exception.Message);$StatusText.Text='Diagnostics are temporarily unavailable. The Workbench remains open.'} }
function Open-DiagnosticLogSafe {
    try{Ensure-Dir $script:LogRoot;if(-not(Test-Path -LiteralPath $script:RuntimeLogPath)){Set-Content -LiteralPath $script:RuntimeLogPath -Value 'No diagnostic events yet.' -Encoding UTF8};Start-Process notepad.exe -ArgumentList @($script:RuntimeLogPath) -ErrorAction Stop | Out-Null}
    catch{Write-AppLog 'ERROR' ("Open log: "+$_.Exception.Message);$StatusText.Text='Could not open the log. The Workbench remains open.'}
}

# Merch Forge · Backend status boundary
# Owns unavailable detection, offline state and the layout-owned status card.
function Test-BackendUnavailableMessage([string]$Message) {
    $l=([string]$Message).ToLowerInvariant()
    return ($l -match 'http 5[0-9][0-9]|connect_timeout|timed out|timeout|database|internal server|server error|unable to connect|connection.*failed|network|offline|no such host|name resolution')
}
function Set-BackendBannerState([bool]$Visible) {
    if($null -ne $BackendBanner){$BackendBanner.Visibility=if($Visible){'Visible'}else{'Collapsed'}}
    if($null -ne $BackendBannerText){$BackendBannerText.Text=Get-UiText 'backend.unavailable' 'Backend unavailable'}
    if($null -ne $BackendRetryButton){$BackendRetryButton.Content=Get-UiText 'backend.retry' 'Retry';$BackendRetryButton.IsEnabled=(-not $script:Busy)}
}
function Enter-OfflineWorkbench([string]$Technical) {
    $human=Get-UiText 'backend.offline.body' 'Live workspace data is temporarily unavailable. Use Retry in the gold status card.'
    Write-AppLog 'WARN' ('Backend unavailable: '+$Technical)
    $code=0;if($Technical -match 'HTTP ([0-9]{3})'){try{$code=[int]$Matches[1]}catch{$code=0}}
    Set-LastDiagnostic 'backend_unavailable' $code 'retry_backend' $Technical $human
    $script:Session=$null;$script:BackendVersion=$null;$script:Current=$null;$script:ReviewWorkspace=$null;$script:Publication=$null;$script:Delivery=$null
    $script:ConnectionState='Backend unavailable';$script:OfflineMode=$true
    if($null -ne $LoginGrid){$LoginGrid.Visibility='Collapsed'};if($null -ne $AppGrid){$AppGrid.Visibility='Visible'}
    if($null -ne $BackendText){$BackendText.Text=Get-UiText 'backend.unavailable' 'Backend unavailable'}
    if($null -ne $StatusText){$StatusText.Text=Get-UiText 'backend.offline.status' 'Workbench open · waiting for service'}
    $cached=Load-OfflineQueueSnapshot
    if($cached -gt 0 -and $null -ne $ConceptList){$ConceptList.Visibility='Visible'}
    Set-BackendBannerState $true
    Apply-RoleUi;Show-HomeLanding $true
    if($null -ne $RefreshButton){$RefreshButton.IsEnabled=$true}
}

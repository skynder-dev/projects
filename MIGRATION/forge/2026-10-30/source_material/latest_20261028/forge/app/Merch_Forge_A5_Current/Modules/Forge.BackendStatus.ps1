# NEW canonical reconciliation: mobile relay import and automatic sync are excluded.
function Set-ForgeLocalReadUnavailable {
    $script:StageFilterCache=$null
    foreach($button in @($GenerateButton,$LocalApproveBriefButton,$LocalBuildPackageButton,$LocalAcceptButton,$AcceptButton,$SaveVariantReviewButton,$OwnerKeepButton,$OwnerEditDecisionButton,$OwnerRegenButton,$OwnerSkipButton,$OwnerClearDecisionButton)){if($null-ne$button){$button.IsEnabled=$false}}
    $message=if($script:ConnectionState-ceq'Connected'){Get-UiText 'connected.refresh.failed' 'Refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.'}else{Get-UiText 'local.refresh.failed' 'Local refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.'}
    foreach($label in @($PublicationPreflight,$DeliveryStatus,$AcceptanceStatus,$LocalCoreStatusText)){if($null-ne$label){$label.Text=$message}}
    $StatusText.Text=$message
}
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

# Direct local entry grants no server capabilities and loads no stored credentials.
function Enter-LocalWorkbench {
    $script:OwnerKey=$null;$script:Session=$null;$script:BackendVersion=$null
    $script:ConnectionState='Local';$script:OfflineMode=$true
    $LoginGrid.Visibility='Collapsed';$AppGrid.Visibility='Visible'
    Set-BackendBannerState $false
    Apply-RoleUi
    $ActorText.Text='Local';$BackendText.Text='Local'
    $null=Load-OfflineQueueSnapshot
    Show-HomeLanding $true
    Update-LocalCoreBusinessSurfaces
    $StatusText.Text=if($script:QueueSnapshotIssue){$script:QueueSnapshotIssue}else{'Local workspace ready'}
}
function Get-ForgeLocalRefreshView {
    $fields=@();foreach($control in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox,$PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox,$ConceptTitle,$ConceptMeta,$OverviewHook,$OverviewConcept,$OverviewBuyer,$OverviewWhy,$OverviewDifferent,$OverviewVisual,$OverviewMeaning,$OverviewStatus,$OverviewWarnings,$OverviewNext)){
        if($null-ne$control){$fields+=@([pscustomobject]@{control=$control;text=[string]$control.Text;enabled=[bool]$control.IsEnabled;readonly=$(if($null-ne$control.PSObject.Properties['IsReadOnly']){[bool]$control.IsReadOnly}else{$null})})}
    }
    return [pscustomobject]@{fields=$fields;current=$script:Current;restore_source=$script:RestoreSourceRevisionId;publication=$script:Publication;delivery=$script:Delivery;review=$script:ReviewWorkspace;editor=$script:LocalPublicationEditor;dirty=[bool]$script:Dirty;publication_dirty=[bool]$script:PublicationDirty;queue=@($script:Queue);snapshot_mode=$script:OfflineSnapshotMode;locale_item=$PublicationLocaleBox.SelectedItem;locale_enabled=[bool]$PublicationLocaleBox.IsEnabled}
}
function Restore-ForgeLocalRefreshView($View,[bool]$KeepLoadedQueue=$false) {
    $script:StageFilterCache=$null; $wasBusy=$script:Busy;$wasLoading=$script:ConceptLoadInProgress;$script:Busy=$true;$script:ConceptLoadInProgress=$true
    try{
        $script:Current=$View.current;$script:RestoreSourceRevisionId=$View.restore_source;$script:Publication=$View.publication;$script:Delivery=$View.delivery;$script:ReviewWorkspace=$View.review;$script:LocalPublicationEditor=$View.editor
        foreach($field in $View.fields){$field.control.Text=$field.text;$field.control.IsEnabled=$field.enabled;if($field.readonly-is[bool]){$field.control.IsReadOnly=$field.readonly}};$PublicationLocaleBox.SelectedItem=$View.locale_item;$PublicationLocaleBox.IsEnabled=$View.locale_enabled
        if(!$KeepLoadedQueue){$script:Queue=@($View.queue);$script:OfflineSnapshotMode=$View.snapshot_mode;Apply-Filter}
        $script:Dirty=$View.dirty;$script:PublicationDirty=$View.publication_dirty
    }finally{$script:Busy=$wasBusy;$script:ConceptLoadInProgress=$wasLoading}
    try{Set-Dirty $View.dirty}catch{};try{Set-PublicationDirty $View.publication_dirty}catch{}
    # Saving remains a fenced retry; generation/acceptance/package authority is not restored from a failed refresh.
    if($null-ne$SavePublicationButton-and$View.publication_dirty-and$null-ne$View.editor){$SavePublicationButton.IsEnabled=$true}
    Set-ForgeLocalReadUnavailable

}
function Refresh-LocalWorkbench {
    if(($script:Dirty-or$script:PublicationDirty)-and!(Confirm 'Refresh local workspace and discard unsaved creative/publication edits?')){return $false}
    $view=Get-ForgeLocalRefreshView
    try{
        $state=Read-LocalCoreState
        $wasLoading=$script:ConceptLoadInProgress;$script:ConceptLoadInProgress=$true
        try{$null=Load-OfflineQueueSnapshot $state}finally{$script:ConceptLoadInProgress=$wasLoading}
        if($script:QueueSnapshotCoreUnavailable){throw 'Local draft queue could not be verified.'}
        $item=$null
        if($null-ne$view.current){$key=[string]$view.current.concept.concept_key;$item=@($script:Queue|Where-Object{[string]$_.concept_key-ceq$key})|Select-Object -First 1
            if($null-eq$item){$missing=New-Object Exception 'The selected idea is not present in the refreshed queue. Your editor was preserved; select a current idea.';$missing.Data['forge_refresh_keep_loaded_queue']=$true;throw $missing}
        }
        $script:Dirty=$false;$script:PublicationDirty=$false
        if($null-ne$item){$opened=@(Open-ConceptItem $item $true);if(!(@($opened|Where-Object{$_-is[bool]-and$_}).Count)){$openError=New-Object Exception 'The selected idea could not be reopened. Your previous editor was preserved.';$openError.Data['forge_refresh_already_reported']=$true;throw $openError}}
        Update-LocalCoreBusinessSurfaces
        $StatusText.Text=if($script:QueueSnapshotIssue){$script:QueueSnapshotIssue}else{'Local workspace refreshed'}
        return $true
    }catch{
        $failure=$_.Exception;$keep=($failure.Data['forge_refresh_keep_loaded_queue']-is[bool]-and$failure.Data['forge_refresh_keep_loaded_queue'])
        Restore-ForgeLocalRefreshView $view $keep
        try{Update-LocalCoreBusinessSurfaces}catch{};try{Update-PortfolioPipelineSurface}catch{}
        $StatusText.Text=Get-UiText 'local.refresh.failed' 'Local refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.'
        Write-AppLog 'WARN' ('Local refresh retained previous editor: '+$failure.Message)
        if(!($failure.Data['forge_refresh_already_reported']-is[bool]-and$failure.Data['forge_refresh_already_reported'])){Show-Error ($StatusText.Text+' '+$failure.Message)}
        return $false
    }
}

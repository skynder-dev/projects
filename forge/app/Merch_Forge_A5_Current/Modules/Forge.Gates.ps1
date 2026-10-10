# Merch Forge · Capability and safety gates
# Owns fail-closed enablement and readiness states. No external submission.
function Has-Cap([string]$Name) {
    if($null -eq $script:Session -or $null -eq $script:Session.capabilities){return $false}
    $p=$script:Session.capabilities.PSObject.Properties[$Name]
    return ($null -ne $p -and [bool]$p.Value)
}
function Apply-RoleUi {
    $actor=if($null -ne $script:Session){[string]$script:Session.display_name}else{Get-UiText 'system.notconnected' 'Not connected'}
    $role=if($null -ne $script:Session){[string]$script:Session.role_key}else{''}
    $roleLabel=if($role){Get-RoleLabel $role}else{''}
    if($null -ne $ActorText){$ActorText.Text=if($roleLabel){"$actor · $roleLabel"}else{$actor}}
    $localPub=($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')); $canEdit=Has-Cap 'edit'; $canReview=Has-Cap 'review'; $canPub=((Has-Cap 'prepare_publication') -or $localPub)
    foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox)){$box.IsReadOnly=(-not $canEdit)}; if((Test-CurrentIsResearchDraft)){Set-DraftEditBoxesEditable $true}
    $VariantReviewState.IsEnabled=$canReview; $VariantReviewReason.IsEnabled=$canReview; $VariantReviewNote.IsReadOnly=(-not $canReview)
    foreach($box in @($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox)){$box.IsReadOnly=(-not $canPub)}
    if(-not $canEdit){$DirtyLabel.Text=Get-UiText 'role.readonly' 'Read-only for this role'}
    Update-CancelGenerationState; Update-VariantSelection; Update-AcceptanceControls
    Set-PublicationDirty $script:PublicationDirty; Set-Dirty $script:Dirty
}
function Set-PublicationDirty([bool]$Value) {
    $script:PublicationDirty=$Value; if($null -ne $PublicationDirtyLabel){$PublicationDirtyLabel.Text=if($Value){Get-UiText 'status.unsavedlisting' 'Unsaved listing changes'}else{''}}
    if($null -ne $SavePublicationButton){$localPub=($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core'));$can=($null -ne $script:Publication -and [bool]$script:Publication.workspace.current_revision_accepted -and ((Has-Cap 'prepare_publication') -or $localPub)); $SavePublicationButton.IsEnabled=(-not $script:Busy -and $Value -and $can)}
}
function Update-AcceptanceControls {
    if($null -eq $AcceptanceStatus -or $null -eq $ReopenAcceptanceButton){return}
    if($null -eq $script:Current){
        $AcceptButton.IsEnabled=$false;$ReopenAcceptanceButton.IsEnabled=$false;$StartIterationSameButton.IsEnabled=$false;$StartIterationEditButton.IsEnabled=$false;$GenerateButton.IsEnabled=$false;$SaveVariantReviewButton.IsEnabled=$false
        $AcceptanceStatus.Text='No concept loaded.';return
    }
    $c=Get-PropertyValue $script:Current 'concept'
    if($null -eq $c){
        $AcceptButton.IsEnabled=$false;$ReopenAcceptanceButton.IsEnabled=$false;$StartIterationSameButton.IsEnabled=$false;$StartIterationEditButton.IsEnabled=$false;$GenerateButton.IsEnabled=$false;$SaveVariantReviewButton.IsEnabled=$false
        $AcceptanceStatus.Text='Concept details are unavailable.';return
    }
    $rw=$null
    if($null -ne $script:ReviewWorkspace){$rw=Get-PropertyValue $script:ReviewWorkspace 'workspace'}
    $selected=@($VariantList.SelectedItems)
    $accepted=[bool](Get-PropertyValue $c 'current_revision_accepted')
    if($null -ne $rw){$accepted=([string](Get-PropertyValue $rw 'active_acceptance_id')).Length -gt 0}
    $localGenerate=Test-LocalProductionProviderReady;$canGenerate=(-not $script:Busy -and ((Has-Cap 'generate') -or $localGenerate) -and -not $script:Dirty -and -not $accepted -and -not (Test-CurrentIsResearchDraft))
    $rwAllowed=Get-PropertyValue $rw 'allowed_actions'
    if($null -ne $rwAllowed -and -not $localGenerate){$canGenerate=$canGenerate -and [bool](Get-PropertyValue $rwAllowed 'generate_or_regenerate_same_revision')}
    $GenerateButton.IsEnabled=$canGenerate
    $canReview=(-not $script:Busy -and (Has-Cap 'review') -and -not $accepted -and $selected.Count -eq 1)
    $canAccept=(-not $script:Busy -and (Has-Cap 'accept') -and -not $script:Dirty -and -not $accepted -and $selected.Count -eq 1)
    if($selected.Count -eq 1){
        $v=$selected[0]
        if([bool](Get-PropertyValue $v 'local_only')){$canReview=$false;$canAccept=$false}
        else {
            $allowed=Get-PropertyValue $v 'allowed_actions'
            if($null -ne $allowed){$canReview=$canReview -and [bool](Get-PropertyValue $allowed 'review'); $canAccept=$canAccept -and [bool](Get-PropertyValue $allowed 'accept')}
            elseif([bool](Get-PropertyValue $v 'stale_revision')){$canReview=$false;$canAccept=$false}
        }
    } else {$canReview=$false;$canAccept=$false}
    $SaveVariantReviewButton.IsEnabled=$canReview
    $AcceptButton.IsEnabled=$canAccept
    $currentAcceptance=[string](Get-PropertyValue $c 'current_acceptance_id')
    $canReopen=(-not $script:Busy -and (Has-Cap 'accept') -and -not $script:Dirty -and $accepted -and -not [string]::IsNullOrWhiteSpace($currentAcceptance))
    $canIterate=(-not $script:Busy -and (Has-Cap 'edit') -and $accepted)
    if($null -ne $rwAllowed){$canReopen=$canReopen -and [bool](Get-PropertyValue $rwAllowed 'reopen_acceptance'); $canIterate=$canIterate -and [bool](Get-PropertyValue $rwAllowed 'start_new_iteration')}
    $ReopenAcceptanceButton.IsEnabled=$canReopen
    $StartIterationSameButton.IsEnabled=($canIterate -and -not $script:Dirty)
    $StartIterationEditButton.IsEnabled=$canIterate
    $revNo=Get-PropertyValue $c 'current_revision_no'
    if($null -ne $rw){
        $reviewState=[string](Get-PropertyValue $rw 'review_workflow_state')
        $hasHistory=[bool](Get-PropertyValue $rw 'has_accepted_history')
        $AcceptanceStatus.Text=("Review state: {0}. " -f $reviewState)+
          $(if($accepted){"Accepted visual on revision $revNo. Reopen withdraws it; Start new iteration preserves it in history."}elseif($hasHistory){"Current revision is not accepted; an older accepted design remains in history."}else{"Current revision $revNo is not accepted."})
    } else {
        $AcceptanceStatus.Text=if($accepted){"Accepted exact revision $revNo."}else{"Current revision $revNo is not accepted."}
    }
}
function Set-Busy([bool]$Value,[string]$Message='Working…') {
    $script:Busy=$Value; $StatusText.Text=$Message; if($null -ne $BusyText){$BusyText.Text=$Message}; if($null -ne $BusyBanner){$BusyBanner.Visibility=if($Value){'Visible'}else{'Collapsed'}}
    $RefreshButton.IsEnabled=-not $Value; $ConceptList.IsEnabled=-not $Value; $SearchBox.IsEnabled=-not $Value; $FilterBox.IsEnabled=-not $Value; $SortBox.IsEnabled=-not $Value
    $SaveButton.IsEnabled=(-not $Value -and ((Has-Cap 'edit') -or (Test-CurrentIsResearchDraft)) -and $script:Dirty -and $null -ne $script:Current)
    $GenerateButton.IsEnabled=(-not $Value -and ((Has-Cap 'generate') -or (Test-LocalProductionProviderReady)) -and $null -ne $script:Current -and -not $script:Dirty -and -not (Test-CurrentIsResearchDraft))
    if($Value){$CancelGenerationButton.IsEnabled=$false}else{Update-CancelGenerationState}
    try { Update-AcceptanceControls } catch { Write-AppLog 'ERROR' ('Acceptance control refresh failed: '+$_.Exception.Message) }
    if($null -ne $SavePublicationButton){try{$pubWorkspace=Get-PropertyValue $script:Publication 'workspace';$localPub=($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core'));$can=($null -ne $pubWorkspace -and [bool](Get-PropertyValue $pubWorkspace 'current_revision_accepted') -and ((Has-Cap 'prepare_publication') -or $localPub)); $SavePublicationButton.IsEnabled=(-not $Value -and $script:PublicationDirty -and $can)}catch{$SavePublicationButton.IsEnabled=$false;Write-AppLog 'ERROR' ('Publication control refresh failed: '+$_.Exception.Message)}}
    try { Update-PackageButtons } catch { Write-AppLog 'ERROR' ('Package control refresh failed: '+$_.Exception.Message) }
    try { Update-OwnerDecisionControls } catch { Write-AppLog 'ERROR' ('Owner decision control refresh failed: '+$_.Exception.Message) }
}
function Show-GateState($Value) { return (Show-PublicationCheckState $Value) }
function Show-PublicationCheckState($Value) {
    $t=([string]$Value).Trim().ToLowerInvariant()
    switch($t){
        'pass' { return 'Ready' }
        'fail' { return 'Needs attention' }
        'needs_review' { return 'Needs attention' }
        'blocked' { return 'Blocked' }
        'not_required' { return 'Not required' }
        'pending' { return 'Not checked' }
        default { return 'Not checked' }
    }
}
function Show-PublicationBlocker($Value) {
    $t=([string]$Value).Trim().ToLowerInvariant()
    switch($t){
        'exact_accept_required' { return 'Accept a design version first.' }
        'accepted_visual_variant_required' { return 'Accept a generated visual first.' }
        'ip_screen_not_passed' { return 'Complete the IP check for this accepted version.' }
        'visual_qa_not_passed' { return 'Complete the visual check for this accepted version.' }
        'print_qa_not_passed' { return 'Complete the print check for this accepted version.' }
        default { if([string]::IsNullOrWhiteSpace($t)){return 'No internal creative or QA blocker.'}; return 'This accepted version still needs attention before preflight.' }
    }
}
function Update-PackageButtons {
    if($null -eq $ExportPackageButton){return}
    $ExportPackageButton.IsEnabled=$false; $SendToSocialButton.IsEnabled=$false; $PreparePackageButton.IsEnabled=$false
    if($script:Busy -or $null -eq $script:Delivery -or -not (Has-Cap 'edit')){return}
    $w=$script:Delivery.workspace; if($null -eq $w){return}
    if($null -ne $w.allowed_actions){
        $ExportPackageButton.IsEnabled=[bool]$w.allowed_actions.prepare_delivery_bundle
        $SendToSocialButton.IsEnabled=[bool]$w.allowed_actions.prepare_social_handoff
        $kind='generic_owner_export'; if($null -ne $PackageTargetBox.SelectedItem){$kind=[string]$PackageTargetBox.SelectedItem.Tag}
        switch($kind){
            'social_source_package' {$PreparePackageButton.IsEnabled=[bool]$w.allowed_actions.prepare_social_source_package}
            'amazon_owner_package' {$PreparePackageButton.IsEnabled=[bool]$w.allowed_actions.prepare_amazon_owner_package}
            default {$PreparePackageButton.IsEnabled=[bool]$w.allowed_actions.prepare_generic_owner_package}
        }
    }
}
function Update-CancelGenerationState { $g=$GenerationRequestList.SelectedItem; $isLocal=($null -ne $g -and [string](Get-PropertyValue $g 'request_origin') -eq 'local_worker'); $CancelGenerationButton.IsEnabled=(-not $script:Busy -and -not $isLocal -and (Has-Cap 'generate') -and $null -ne $g -and [string](Get-PropertyValue $g 'status') -eq 'queued') }

# Merch Forge · Read/view-model boundary
# Loads and formats workspace state for UI surfaces.
function Add-QueueDisplayProperties($Items) {
    foreach($item in @($Items)){
        $item|Add-Member -NotePropertyName workflow_label -NotePropertyValue (Show-WorkflowState $item.workflow_state) -Force
        $item|Add-Member -NotePropertyName workflow_foreground -NotePropertyValue (Get-WorkflowForeground $item.workflow_state) -Force
        $item|Add-Member -NotePropertyName workflow_background -NotePropertyValue (Get-WorkflowBackground $item.workflow_state) -Force
        $scoreLabel='—';try{$scoreLabel=[string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0:0.0}',[double]$item.score_total)}catch{}
        $item|Add-Member -NotePropertyName score_label -NotePropertyValue $scoreLabel -Force
    }
    return @($Items)
}
function Save-QueueSnapshot($Items) {
    try {
        Ensure-Dir $script:StateRoot
        $payload=[ordered]@{schema='forge.local_queue_snapshot.v1';saved_at=(Get-Date).ToUniversalTime().ToString('o');concepts=@($Items)}
        [System.IO.File]::WriteAllText($script:QueueSnapshotPath,($payload|ConvertTo-Json -Depth 14),(New-Object System.Text.UTF8Encoding($false)))
    } catch { Write-AppLog 'WARN' ('Queue snapshot save failed: '+$_.Exception.Message) }
}
function Read-QueueSnapshotFile([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){return @()}
    try {
        $j=Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json
        if($null -ne $j -and $j.PSObject.Properties.Name -contains 'concepts'){return @($j.concepts)}
        return @($j)
    } catch { Write-AppLog 'WARN' ('Queue snapshot read failed: '+$_.Exception.Message);return @() }
}
function Load-OfflineQueueSnapshot {
    $items=@()
    if(Test-Path -LiteralPath $script:QueueSnapshotPath -PathType Leaf){$items=@(Read-QueueSnapshotFile $script:QueueSnapshotPath)}
    if($items.Count -eq 0){$items=@(Read-QueueSnapshotFile $script:EmbeddedIdeasPath)}
    $script:OfflineSnapshotMode=($items.Count -gt 0)
    $script:Queue=@(Add-QueueDisplayProperties $items)
    Apply-Filter
    if($null -ne $QueueCountText){$QueueCountText.Text=((Get-UiText 'queue.cached' '{0} cached ideas') -f @($script:Queue).Count)}
    return @($script:Queue).Count
}
function Apply-Filter {
    $items=@($script:Queue)
    $q=([string]$SearchBox.Text).Trim().ToLowerInvariant()
    if(-not [string]::IsNullOrWhiteSpace($q)) { $items=@($items | Where-Object { (([string]$_.title)+' '+([string]$_.hook)+' '+([string]$_.niche_name)+' '+([string]$_.workflow_state)).ToLowerInvariant().Contains($q) }) }
    $state=if($null -ne $FilterBox.SelectedItem){[string]$FilterBox.SelectedItem.Tag}else{''}
    if(-not [string]::IsNullOrWhiteSpace($state)) { $items=@($items | Where-Object { [string]$_.workflow_state -eq $state }) }
    $sort=if($null -ne $SortBox.SelectedItem){[string]$SortBox.SelectedItem.Tag}else{'score'}
    if($sort -eq 'title') { $items=@($items | Sort-Object title) }
    elseif($sort -eq 'workflow') { $items=@($items | Sort-Object workflow_state,@{Expression='score_total';Descending=$true}) }
    else { $items=@($items | Sort-Object @{Expression='score_total';Descending=$true},title) }
    $count=@($items).Count
    $ConceptList.ItemsSource=$items
    $CompactConceptBox.ItemsSource=$items
    $QueueCountText.Text=((Get-UiText 'queue.shown' '{0} shown') -f $count)
    Set-QueueEmptyState $count
}
function Load-Queue {
    Set-Busy $true (Get-StaticUiText 'Loading concepts…')
    try {
        $r=Invoke-ForgeApi 'concept_queue' @{locale=$script:Locale}
        $raw=@($r.concepts)
        Save-QueueSnapshot $raw
        $script:OfflineSnapshotMode=$false
        $script:Queue=@(Add-QueueDisplayProperties $raw)
        Apply-Filter
        $script:ConnectionState='Connected'
        $BackendText.Text=Get-UiText 'system.connected' 'Connected'
        Update-GlobalBusinessSurfaces
        $StatusText.Text=if([int]$r.count -eq 0){Get-StaticUiText 'No concepts available in this workspace.'}else{("{0} {1}" -f $r.count,(Get-UiText 'queue.concepts' 'Ideas'))}
    } finally { Set-Busy $false $StatusText.Text }
}
# R2O module: Forge.BackendStatus.ps1
function Populate-Detail($d) {
    if($null -eq $d){throw 'Concept detail response is empty.'}
    $c=Get-PropertyValue $d 'concept'
    if($null -eq $c){throw 'Concept detail response has no concept payload.'}
    $script:RestoreSourceRevisionId=$null; $script:Current=$d
    Show-ConceptSurface

    # Core editor fields are required. Keep these fail-closed.
    $ConceptTitle.Text=[string](Get-PropertyValue $c 'title')
    $ConceptMeta.Text=("{0} · revision {1}" -f (Get-PropertyValue $c 'niche_name'),(Get-PropertyValue $c 'current_revision_no'))
    $TitleBox.Text=[string](Get-PropertyValue $c 'title'); $HookBox.Text=[string](Get-PropertyValue $c 'hook'); $ConceptTextBox.Text=[string](Get-PropertyValue $c 'concept_text'); $BuyerBox.Text=[string](Get-PropertyValue $c 'target_buyer'); $PurchaseBox.Text=[string](Get-PropertyValue $c 'purchase_reason'); $DifferentiationBox.Text=[string](Get-PropertyValue $c 'differentiation'); $VisualBox.Text=[string](Get-PropertyValue $c 'visual_direction_text')
    $spec=Get-PropertyValue $c 'production_spec'; $SpecBox.Text=if($null -eq $spec){'{}'}else{$spec | ConvertTo-Json -Depth 20}; $ReasonBox.Text=''; if($null -ne $GenerationBriefText){$GenerationBriefText.Text=Get-GenerationBriefSummary $c}

    # Product-facing Overview is the default landing surface; Edit is secondary.
    try {
        $oe=Get-LocalizedOwnerExplanation $c
        $OverviewHook.Text=[string](Get-PropertyValue $c 'hook')
        $OverviewConcept.Text=[string](Get-PropertyValue $c 'concept_text')
        $OverviewBuyer.Text=[string](Get-PropertyValue $c 'target_buyer')
        $OverviewWhy.Text=[string](Get-PropertyValue $c 'purchase_reason')
        $OverviewDifferent.Text=[string](Get-PropertyValue $c 'differentiation')
        $OverviewVisual.Text=[string](Get-PropertyValue $c 'visual_direction_text')
        $meaning=[string](Get-PropertyValue $oe 'joke_explanation'); if([string]::IsNullOrWhiteSpace($meaning)){$meaning=[string](Get-PropertyValue $oe 'line_meaning')}; if([string]::IsNullOrWhiteSpace($meaning)){$meaning=[string](Get-PropertyValue $c 'concept_text')}; $OverviewMeaning.Text=$meaning
        $overviewState=Get-OverviewWorkflowState $c; $OverviewStatus.Text=Show-WorkflowState $overviewState
        $warnings=@(Get-PropertyValue $d 'analysis_warnings'); $OverviewWarnings.Text=if($warnings.Count){$warnings -join ' · '}else{Get-StaticUiText 'No current analysis warning.'}
        $OverviewNext.Text=Get-OverviewNextAction $overviewState
        $OverviewVisualButton.IsEnabled=$true
        $OverviewEditButton.IsEnabled=((Has-Cap 'edit') -and -not [bool](Get-PropertyValue $c 'current_revision_accepted'))
        Select-MainTab 'Overview'; Update-MainTabUi
    } catch {
        Write-AppLog 'ERROR' ('Overview rendering unavailable: '+$_.Exception.Message)
        $OverviewHook.Text=[string](Get-PropertyValue $c 'hook'); $OverviewConcept.Text=[string](Get-PropertyValue $c 'concept_text'); $OverviewBuyer.Text=[string](Get-PropertyValue $c 'target_buyer'); $OverviewWhy.Text=[string](Get-PropertyValue $c 'purchase_reason'); $OverviewVisual.Text=[string](Get-PropertyValue $c 'visual_direction_text'); $OverviewMeaning.Text=''; $OverviewStatus.Text='Overview partially unavailable'; $OverviewWarnings.Text=''; $OverviewNext.Text='Use the other tabs for details.'; Select-MainTab 'Overview'; Update-MainTabUi
    }

    # Analysis is informative. Missing optional metadata must never break concept loading.
    try {
        $oe=Get-LocalizedOwnerExplanation $c; $common=Get-PropertyValue $c 'common_law'; $trigger=Get-PropertyValue $c 'purchase_trigger'
        $AnalysisPurchase.Text=[string](Get-PropertyValue $c 'purchase_reason')
        $AnalysisContext.Text=[string](Get-PropertyValue $oe 'profession_context')
        $AnalysisMeaning.Text=([string](Get-PropertyValue $oe 'line_meaning'))+"`n`n"+([string](Get-PropertyValue $oe 'joke_explanation'))
        $AnalysisEvidence.Text=("Common-law: {0}`nFederal: {1}`nPurchase trigger: {2}" -f (Show-PublicationCheckState ([string](Get-PropertyValue $common 'status'))),(Show-PublicationCheckState ([string](Get-PropertyValue $common 'federal_screen'))),([string](Get-PropertyValue $trigger 'purchase_trigger')))
        $scores=@(Get-PropertyValue $d 'scores')
        $AnalysisScores.Text=(@($scores | ForEach-Object { $label=(([string](Get-PropertyValue $_ 'dimension_key')) -replace '_',' '); if($label.Length -gt 0){$label=$label.Substring(0,1).ToUpperInvariant()+$label.Substring(1)}; "{0}: {1}/10" -f $label,(Get-PropertyValue $_ 'score') }) -join "`n")
        $scoreTech=(@($scores | ForEach-Object { "{0}: score={1}; confidence={2}; evidence={3}" -f (Get-PropertyValue $_ 'dimension_key'),(Get-PropertyValue $_ 'score'),(Get-PropertyValue $_ 'confidence'),(Get-PropertyValue $_ 'evidence') }) -join "`n")
        $AnalysisAdvanced.Text=("Source refs: {0}`n`nScore evidence:`n{1}" -f ((@(Get-PropertyValue $oe 'source_refs') -join ', ')),$scoreTech)
        $warnings=@(Get-PropertyValue $d 'analysis_warnings'); $AnalysisWarnings.Text=if($warnings.Count){(($warnings -join "`n• ")).Insert(0,'• ')}else{'No current analysis warnings.'}
    } catch {
        $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Concept analysis rendering unavailable: '+$technical)
        $AnalysisContext.Text='Analysis context is temporarily unavailable.'; $AnalysisMeaning.Text=''; $AnalysisEvidence.Text=''; $AnalysisScores.Text=''; $AnalysisAdvanced.Text=$technical; $AnalysisWarnings.Text='Concept editing remains available.'
    }

    # Revision/history preview is also non-fatal to the core editor.
    try {
        $revs=@(Get-PropertyValue $d 'revisions')
        foreach($r in $revs){$r|Add-Member -NotePropertyName display -NotePropertyValue ("Revision {0} · {1}" -f (Get-PropertyValue $r 'revision_no'),(Get-PropertyValue $r 'created_at')) -Force}
        $RevisionList.ItemsSource=$revs
        $CurrentRevisionPreview.Text=if($revs.Count){Format-Revision $revs[0]}else{'No revisions yet.'}
        $SelectedRevisionPreview.Text=if($revs.Count){'Select a revision to compare.'}else{'No revision available to compare.'}
        $RevisionAdvanced.Text=if($revs.Count){Format-RevisionAdvanced $revs[0]}else{''}; $AuditAdvanced.Text=''; $RestoreRevisionButton.IsEnabled=$false
    } catch {
        $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Revision rendering unavailable: '+$technical)
        $RevisionList.ItemsSource=$null; $CurrentRevisionPreview.Text='Revision history unavailable.'; $SelectedRevisionPreview.Text=''; $RevisionAdvanced.Text=$technical; $RestoreRevisionButton.IsEnabled=$false
    }

    # Generation/variant lists are optional until generation actually exists.
    try {
        $runs=@(); foreach($g in @(Get-PropertyValue $d 'generation_requests')){$g|Add-Member -NotePropertyName display -NotePropertyValue ("Run {0} · {1} · {2}" -f (Get-PropertyValue $g 'request_no'),(Show-GenerationKind (Get-PropertyValue $g 'request_kind')),(Show-GenerationStatus (Get-PropertyValue $g 'status'))) -Force; $runs+=$g}
        $GenerationRequestList.ItemsSource=$runs; $GenerationRequestList.SelectedItem=$null; $CancelGenerationButton.IsEnabled=$false; $GenerateButton.Content=if($runs.Count){'Re-generate variants…'}else{'Generate variants…'}
        $all=@(); foreach($v in @(Get-PropertyValue $d 'variants')){$stale=([string](Get-PropertyValue $v 'concept_revision_id') -ne [string](Get-PropertyValue $c 'current_revision_id')); $label=("Variant {0} · {1}" -f (Get-PropertyValue $v 'variant_index'),(Show-GenerationStatus (Get-PropertyValue $v 'status'))); if($stale){$label+=' · Older revision'}; $reviewState=[string](Get-PropertyValue $v 'review_state'); if($reviewState){$label+=(" · {0}" -f $reviewState)}; $v|Add-Member -NotePropertyName display -NotePropertyValue $label -Force; $v|Add-Member -NotePropertyName stale_revision -NotePropertyValue $stale -Force; $all+=$v}
        $VariantList.ItemsSource=$all; $VariantPreview.Text=if($all.Count){'Select a variant.'}else{'No generated variants yet.'}; $VariantAdvanced.Text=''; $VariantCompareA.Text=if($all.Count){'Select exactly two variants to compare.'}else{'No variants available to compare.'}; $VariantCompareB.Text=''; $CompareVariantsButton.IsEnabled=$false; $SaveVariantReviewButton.IsEnabled=$false; $GenerationStatus.Text=if($runs.Count -eq 0 -and $all.Count -eq 0){'No generation runs or variants yet.'}else{"$($runs.Count) generation run(s), $($all.Count) variant(s)"}; $ReopenReasonBox.Text=''
    } catch {
        $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Generation/variant rendering unavailable: '+$technical)
        $GenerationRequestList.ItemsSource=$null; $VariantList.ItemsSource=$null; $GenerationStatus.Text='Generation history unavailable; refresh before generating.'; $GenerateButton.IsEnabled=$false; $SaveVariantReviewButton.IsEnabled=$false; $AcceptButton.IsEnabled=$false
    }

    try { Set-Dirty $false; Update-AcceptanceControls } catch { Write-AppLog 'ERROR' ('Acceptance controls unavailable: '+$_.Exception.Message); $GenerateButton.IsEnabled=$false; $SaveVariantReviewButton.IsEnabled=$false; $AcceptButton.IsEnabled=$false }
}
function Load-AuditHistory([string]$Key) {
    $AuditList.ItemsSource=$null; $AuditDetail.Text=''
    try {
        $r=Invoke-ForgeApi 'audit_history' @{concept_key=$Key;include_technical=$false;limit=100}
        $events=@($r.events)
        foreach($e in $events){$e|Add-Member -NotePropertyName display -NotePropertyValue (("{0} · {1}`n{2}" -f ([DateTimeOffset]$e.event_at).ToLocalTime().ToString('yyyy-MM-dd HH:mm'),$e.title,$e.summary)) -Force}
        $AuditList.ItemsSource=$events
    } catch { $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Audit history unavailable: '+$technical); $AuditDetail.Text=Get-HumanErrorMessage $technical; $AuditAdvanced.Text=$technical }
}
function Load-Downstream([string]$Key) {
    if($null -eq $DownstreamLineage){return}
    try {
        $r=Invoke-ForgeApi 'publication_readiness' @{concept_key=$Key}; $d=$r.readiness
        $DownstreamLineage.Text=if([bool]$d.current_revision_accepted){("Accepted revision {0}`nVisual selected: {1}" -f $d.current_revision_no,$(if($d.accepted_visual_candidate_id){'Yes'}else{'No'}))}else{("Current revision {0} is not accepted." -f $d.current_revision_no)}
        $DownstreamIp.Text=('IP screen: '+(Show-GateState $d.ip_status))
        $DownstreamVisualQa.Text=('Visual QA: '+(Show-GateState $d.visual_qa_status))
        $DownstreamPrintQa.Text=('Print QA: '+(Show-GateState $d.print_qa_status))
        $DownstreamPolicy.Text=('Policy preflight: '+(Show-GateState $d.policy_preflight_status))
        $DownstreamEligibility.Text=if([bool]$d.downstream_eligible){'Eligible for internal policy/channel preflight preparation.'}else{'Not yet eligible for internal preflight.'}
        $DownstreamBlocker.Text=Show-PublicationBlocker $d.blocking_reason
        $DownstreamAdvanced.Text=Format-DownstreamAdvanced $d
        $DownstreamExternal.Text='External submission is not authorized. Amazon/other external Submit remains a separate explicit human authorization gate.'
    } catch {
        $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Downstream readiness unavailable: '+$technical); $DownstreamLineage.Text='Downstream readiness unavailable.'; $DownstreamIp.Text='IP screen: unavailable'; $DownstreamVisualQa.Text='Visual QA: unavailable'; $DownstreamPrintQa.Text='Print QA: unavailable'; $DownstreamPolicy.Text='Policy preflight: unavailable'; $DownstreamEligibility.Text='Not available'; $DownstreamBlocker.Text=Get-HumanErrorMessage $technical; $DownstreamAdvanced.Text=$technical; $DownstreamExternal.Text='External submission is not authorized.'
    }
}
function Load-Publication([string]$Key) {
    if($null -eq $PublicationCreativeStatus){return}
    try {
        $r=Invoke-ForgeApi 'publication_workspace' @{concept_key=$Key}; $script:Publication=$r; $w=$r.workspace
        try{Sync-LocalChecksFromLiveWorkspace $w}catch{}
        $PublicationCreativeStatus.Text=if([bool]$w.current_revision_accepted){("Accepted design · revision {0}`nVisual selected: {1}. Listing edits do not change the accepted design." -f $w.current_revision_no,$(if($w.accepted_visual_candidate_id){'Yes'}else{'No'}))}else{'No design accepted yet. Accept an exact design version before editing its listing.'}
        $draft=Get-SuggestedPublicationDraft $script:Current.concept
        $PublicationTitleBox.Text=Use-ValueOrSuggestion $w.listing_title $draft.title
        $PublicationBrandBox.Text=[string]$w.brand
        $PublicationBullet1Box.Text=Use-ValueOrSuggestion $w.bullet_1 $draft.bullet1
        $PublicationBullet2Box.Text=Use-ValueOrSuggestion $w.bullet_2 $draft.bullet2
        $PublicationDescriptionBox.Text=Use-ValueOrSuggestion $w.description $draft.description
        $existingKeywords=(@($w.keywords) -join ', '); $PublicationKeywordsBox.Text=Use-ValueOrSuggestion $existingKeywords $draft.keywords
        $PublicationReasonBox.Text=''
        Set-PublicationLocaleSelection ([string](Get-PropertyValue $w 'locale'))
        $hasSavedDraft=(-not [string]::IsNullOrWhiteSpace([string]$w.listing_title)) -or (-not [string]::IsNullOrWhiteSpace([string]$w.description))
        $PublicationDraftNote.Text=if($hasSavedDraft){'Current saved listing version loaded. Forge fills only missing fields from the concept; manual edits remain optional.'}else{'Draft prepared automatically from the concept. Review it; edit only if you want to change it.'}
        $PublicationBrandHint.Text=if([string]::IsNullOrWhiteSpace([string]$w.brand)){'No verified brand is stored for this concept. Forge will not invent one; use the verified account brand when the channel profile is available.'}else{'Loaded from the current saved listing version.'}
        $hist=@(); foreach($m in @($r.metadata_history)){$when='';try{$when=([DateTimeOffset]$m.created_at).ToLocalTime().ToString('yyyy-MM-dd HH:mm')}catch{$when=[string]$m.created_at};$m|Add-Member -NotePropertyName display -NotePropertyValue ("Listing v{0} · {1}`n{2}" -f $m.revision_no,$m.listing_title,$when) -Force;$hist+=$m}; $PublicationHistoryList.ItemsSource=$hist; if($null -ne $PublicationHistoryEmpty){$PublicationHistoryEmpty.Visibility=if($hist.Count){'Collapsed'}else{'Visible'}}; $PublicationHistoryList.Visibility=if($hist.Count){'Visible'}else{'Collapsed'}
        $PublicationCheckIp.Text=('IP · '+(Show-PublicationCheckState $w.ip_status))
        $PublicationCheckVisual.Text=('Visual · '+(Show-PublicationCheckState $w.visual_qa_status))
        $PublicationCheckPrint.Text=('Print · '+(Show-PublicationCheckState $w.print_qa_status))
        $PublicationCheckPolicy.Text=('Amazon policy · '+(Show-PublicationCheckState $w.policy_preflight_status))
        $PublicationEconomics.Text=Format-PublicationEconomics $w
        $blocker=Show-PublicationBlocker $w.blocking_reason
        if([bool]$w.preflight_input_ready){$PublicationPreflight.Text=("Ready for internal preflight.`nAmazon policy: {0}.`nPreflight does not submit anything." -f (Show-PublicationCheckState $w.policy_preflight_status))}else{$PublicationPreflight.Text=("Not ready for internal preflight.`n{0}`nPreflight does not submit anything." -f $blocker)}
        $PublicationExternal.Text='This Workbench cannot submit to Amazon. Unlock requires separate explicit Alex authorization plus fresh live Amazon editor/policy and royalty revalidation.'
        $PublicationAdvanced.Text=Format-PublicationAdvanced $w $r
        $enabled=[bool]$w.current_revision_accepted; foreach($box in @($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox)){$box.IsEnabled=$true;$box.IsReadOnly=(-not ($enabled -and (Has-Cap 'prepare_publication')))}; if($null -ne $PublicationLocaleBox){$PublicationLocaleBox.IsEnabled=($enabled -and (Has-Cap 'prepare_publication'))}
        Set-PublicationDirty $false
    } catch {
        $technical=$_.Exception.Message; Write-AppLog 'ERROR' ("Publication workspace load failed: {0}" -f $technical)
        $human=Get-HumanErrorMessage $technical; Set-LastDiagnostic 'publication_load' 0 'refresh' $technical $human; $script:Publication=$null; $PublicationCreativeStatus.Text='Publication details could not be loaded. Refresh and try again.'; $PublicationCheckIp.Text='IP · Not checked'; $PublicationCheckVisual.Text='Visual · Not checked'; $PublicationCheckPrint.Text='Print · Not checked'; $PublicationCheckPolicy.Text='Amazon policy · Not checked'; $PublicationEconomics.Text='Unavailable until Publication reloads.'; $PublicationPreflight.Text='Preflight is unavailable until Publication reloads.'; $PublicationExternal.Text='This Workbench cannot submit to Amazon.'; $PublicationAdvanced.Text=("Load error: {0}" -f $technical); $SavePublicationButton.IsEnabled=$false; Set-PublicationDirty $false
    }
}
function Load-Delivery([string]$Key) {
    if($null -eq $DeliveryStatus){return}
    try {
        $r=Invoke-ForgeApi 'delivery_readiness' @{concept_key=$Key}; $script:Delivery=$r; $w=$r.workspace
        $DeliveryStatus.Text=Format-DeliveryStatus $w
        $PackageBoundaryText.Text='Preparation only. Export does not mean saved locally; Social handoff does not mean approval; package preparation does not submit or publish.'
        Update-PackageButtons
    } catch {
        $script:Delivery=$null; $DeliveryStatus.Text='Package readiness could not be loaded. Refresh and try again.'; Update-PackageButtons
    }
}
function Load-Concept([string]$Key,[bool]$SkipDirtyPrompt=$false) {
    if((-not $SkipDirtyPrompt) -and ($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')) { return $false }
    $script:Dirty=$false; $script:PublicationDirty=$false
    Set-Busy $true 'Loading concept…'
    try {
        $d=Invoke-ForgeApi 'concept_detail' @{concept_key=$Key;locale=$script:Locale}
        $rw=Invoke-ForgeApi 'review_workspace' @{concept_key=$Key}; $script:ReviewWorkspace=$rw
        $v2=@()
        foreach($v in @($rw.variants)){
            $v|Add-Member -NotePropertyName id -NotePropertyValue ([string]$v.visual_candidate_id) -Force
            $v|Add-Member -NotePropertyName status -NotePropertyValue ([string]$v.variant_status) -Force
            $v|Add-Member -NotePropertyName review_state -NotePropertyValue ([string]$v.latest_review_state) -Force
            $v|Add-Member -NotePropertyName review_note -NotePropertyValue ([string]$v.latest_review_note) -Force
            $v|Add-Member -NotePropertyName stale_revision -NotePropertyValue $false -Force
            $v|Add-Member -NotePropertyName concept_revision_id -NotePropertyValue ([string]$v.concept_revision_id) -Force
            $v|Add-Member -NotePropertyName generation_request_id -NotePropertyValue ([string]$v.generation_request_id) -Force
            $v|Add-Member -NotePropertyName asset_metadata -NotePropertyValue ([pscustomobject]@{preview_health=[string]$v.preview_health;mime_type=[string]$v.mime_type;width_px=$v.width_px;height_px=$v.height_px}) -Force
            $v|Add-Member -NotePropertyName asset_availability -NotePropertyValue ([string]$v.preview_health) -Force
            $v2+=$v
        }
        $d.variants=$v2
        Populate-Detail $d; try{$null=Ensure-LocalCoreConceptFromCurrent;Update-OwnerDecisionControls}catch{Write-AppLog 'WARN' ('Local core concept mirror/owner review failed: '+$_.Exception.Message)}; Load-AuditHistory $Key; Load-Downstream $Key; Load-Publication $Key; Load-Delivery $Key
        $StatusText.Text='Concept loaded'; return $true
    } finally { Set-Busy $false $StatusText.Text }
}
function Open-OfflineConceptItem($Item) {
    if($null -eq $Item){return}
    $script:OfflineSnapshotMode=$true
    $c=[pscustomobject]@{
        concept_key=[string]$Item.concept_key
        title=[string]$Item.title
        hook=[string]$Item.hook
        niche_name=[string]$Item.niche_name
        current_revision_no='snapshot'
        current_revision_id=''
        current_content_hash=''
        current_revision_accepted=$false
        concept_text=[string]$Item.concept_text
        target_buyer=[string]$Item.target_buyer
        purchase_reason=[string]$Item.purchase_reason
        differentiation=[string]$Item.differentiation
        visual_direction_text=[string]$Item.visual_direction_text
        workflow_state=[string]$Item.workflow_state
    }
    $snapshotMaterial=([ordered]@{concept_key=$c.concept_key;title=$c.title;hook=$c.hook;concept_text=$c.concept_text;visual_direction_text=$c.visual_direction_text}|ConvertTo-Json -Depth 8 -Compress)
    $snapshotHash=Get-StringSha256Hex $snapshotMaterial
    $c.current_content_hash=$snapshotHash
    $c.current_revision_id=('snapshot-'+$snapshotHash.Substring(0,24))
    $script:Current=[pscustomobject]@{concept=$c}
    $script:ProductSection='ideas'
    Show-ConceptSurface
    $ConceptTitle.Text=[string]$c.title
    $ConceptMeta.Text=Get-UiText 'offline.snapshot.meta' 'Local snapshot · live service unavailable'
    $OverviewHook.Text=[string]$c.hook
    $OverviewConcept.Text=[string]$c.concept_text
    $OverviewBuyer.Text=[string]$c.target_buyer
    $OverviewWhy.Text=[string]$c.purchase_reason
    $OverviewDifferent.Text=[string]$c.differentiation
    $OverviewVisual.Text=[string]$c.visual_direction_text
    $OverviewMeaning.Text=[string]$Item.meaning
    $OverviewStatus.Text=Get-UiText 'queue.snapshot' 'Local snapshot'
    $OverviewWarnings.Text=Get-UiText 'offline.snapshot.warning' 'You are viewing the last known idea snapshot. Reconnect for live details.'
    $OverviewNext.Text=Get-UiText 'offline.snapshot.next' 'Reconnect to load live evidence, artwork and publication state.'
    $OverviewVisualButton.IsEnabled=$true
    $OverviewEditButton.IsEnabled=$false
    $null=Ensure-LocalCoreConceptFromCurrent
    Update-OwnerDecisionControls
    Enter-LocalCoreSection 'ideas'
    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
}
function Open-ConceptItem($Item,[bool]$SkipDirtyPrompt=$false) {
    if($script:ConceptLoadInProgress -or $null -eq $Item){return}
    if($script:OfflineMode){Open-OfflineConceptItem $Item;return}
    $key=([string]$Item.concept_key).Trim()
    if([string]::IsNullOrWhiteSpace($key)){Show-Error 'Selected concept has no concept key. Refresh the workspace.';return}
    if($null -ne $script:Current -and [string]$script:Current.concept.concept_key -eq $key){return}
    $script:ConceptLoadInProgress=$true
    try {
        if(-not (Load-Concept $key $SkipDirtyPrompt)){return}
    } catch {
        $technical=$_.Exception.Message
        Write-AppLog 'ERROR' ("Concept load failed for {0}: {1}" -f $key,$technical)
        Set-LastDiagnostic 'concept_load' 0 'refresh_or_retry' $technical (Get-HumanErrorMessage $technical)
        Show-Error ("Concept load failed: {0}" -f $technical)
        $StatusText.Text='Concept load failed'
    } finally {
        $script:ConceptLoadInProgress=$false
    }
}
function Open-ConceptFromPointer($OriginalSource) {
    if($null -eq $OriginalSource){return}
    try {
        $source=[System.Windows.DependencyObject]$OriginalSource
        $container=[System.Windows.Controls.ItemsControl]::ContainerFromElement($ConceptList,$source)
        if($null -eq $container -or -not ($container -is [System.Windows.Controls.ListBoxItem])){return}
        if(-not $container.IsSelected){$container.IsSelected=$true}
        Open-ConceptItem $container.DataContext
    } catch {
        Show-Error ("Concept click failed: {0}" -f $_.Exception.Message)
        $StatusText.Text='Concept click failed'
    }
}

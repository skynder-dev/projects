. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Merch Forge · Read/view-model boundary
# Loads and formats workspace state for UI surfaces.
function Add-QueueDisplayProperties($Items) {
    # A refreshed queue is an explicit freshness boundary, including external package changes.
    $script:StageFilterCache=$null
    foreach($item in @($Items)){if($null-eq$item){continue}
        $item|Add-Member -NotePropertyName workflow_label -NotePropertyValue (Show-WorkflowState (Get-PropertyValue $item 'workflow_state')) -Force
        $item|Add-Member -NotePropertyName workflow_foreground -NotePropertyValue (Get-WorkflowForeground (Get-PropertyValue $item 'workflow_state')) -Force
        $item|Add-Member -NotePropertyName workflow_background -NotePropertyValue (Get-WorkflowBackground (Get-PropertyValue $item 'workflow_state')) -Force
        $value=Get-PropertyValue $item 'score_total';$scoreLabel=if($null-eq$value){'-'}else{Get-UiText 'assessment.unverified' 'Unverified'}
        $item|Add-Member -NotePropertyName score_label -NotePropertyValue $scoreLabel -Force
    }
    return @($Items)
}
function Register-QueueSnapshotUiText {
    $texts=@{
        en=@{'queue.cache.failed'='Idea cache is unavailable. Existing files and the previous view were preserved. Restore a verified data copy or retry after fixing access; an empty workspace was not established.';'queue.cache.previous'='Showing the previous verified idea cache because the current cache could not be read. Review the saved revision before decisions; original files were preserved.'}
        ru=@{'queue.cache.failed'='Кеш идей недоступен. Файлы и прежний список сохранены. Восстановите проверенную копию данных или повторите после восстановления доступа; отсутствие идей не установлено.';'queue.cache.previous'='Показан предыдущий проверенный кеш идей: текущий кеш не удалось прочитать. Перед решением проверьте сохранённую версию; исходные файлы сохранены.'}
        es=@{'queue.cache.failed'='La caché de ideas no está disponible. Se conservaron los archivos y la vista anterior. Restaura una copia verificada o reintenta al recuperar acceso; no se confirmó un espacio vacío.';'queue.cache.previous'='Se muestra la caché anterior verificada porque no se pudo leer la actual. Revisa la revisión guardada antes de decidir; se conservaron los archivos originales.'}
    }
    foreach($loc in $texts.Keys){foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]}}
}
$script:QueueSnapshotIssue=''
function Read-QueueSnapshotFile([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path)-or!(Test-Path -LiteralPath $Path)){throw 'Requested queue cache is missing or inaccessible.'}
    $file=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if($file-isnot[IO.FileInfo]-or($file.Attributes-band[IO.FileAttributes]::ReparsePoint)-or$file.Length-le0-or$file.Length-gt8388608){throw 'Queue cache must be an ordinary UTF-8 JSON file of at most 8 MiB.'}
    $bytes=[IO.File]::ReadAllBytes($file.FullName);if($bytes.Length-le0-or$bytes.Length-gt8388608){throw 'Queue cache size changed or exceeds its bound.'}
    $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes).TrimStart([char]0xfeff)
    $j=if($text.TrimStart().StartsWith('[')){ConvertFrom-ForgeJsonObjectStrict ('{"concepts":'+$text+'}')}else{ConvertFrom-ForgeJsonObjectStrict $text}
    if($j.PSObject.Properties.Name-contains'concepts'){
        $schema=Get-PropertyValue $j 'schema';if($null-ne$schema-and$schema-notin@('forge.local_queue_snapshot.v1','forge.embedded_last_known_ideas.v1')){throw 'Unsupported queue cache schema.'}
        if($j.concepts-isnot[Array]){throw 'Queue concepts must be an array.'}
        $items=@($j.concepts)
    }else{$items=@($j)}
    $keys=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach($item in $items){$key=Get-PropertyValue $item 'concept_key';if($item-isnot[pscustomobject]-or$key-isnot[string]-or[string]::IsNullOrWhiteSpace($key)-or!$keys.Add($key)){throw 'Queue cache contains an invalid or duplicate idea identity.'}}
    return $items
}
function Commit-ForgeQueueSnapshotFile([string]$Temporary,[string]$Target,$Backup) {
    if(Test-Path -LiteralPath $Target){[IO.File]::Replace($Temporary,$Target,$Backup,$true)}else{[IO.File]::Move($Temporary,$Target)}
}
function Save-QueueSnapshot($Items) {
    $temporary=$null
    try {
        Ensure-Dir $script:StateRoot
        $payload=[ordered]@{schema='forge.local_queue_snapshot.v1';saved_at=[DateTime]::UtcNow.ToString('o');concepts=@($Items)}
        $bytes=[Text.Encoding]::UTF8.GetBytes(($payload|ConvertTo-Json -Depth 60))
        if($bytes.Length-gt8388608){throw 'Queue cache exceeds 8 MiB; previous cache preserved.'}
        $temporary=$script:QueueSnapshotPath+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
        $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
        $null=@(Read-QueueSnapshotFile $temporary)
        $backup=$null
        if(Test-Path -LiteralPath $script:QueueSnapshotPath){try{$null=@(Read-QueueSnapshotFile $script:QueueSnapshotPath);$backup=Join-Path $script:StateRoot 'queue-snapshot.previous.json'}catch{$backup=Join-Path $script:StateRoot ('queue-snapshot.invalid.'+[guid]::NewGuid().ToString('N')+'.json');Write-AppLog 'WARN' 'Damaged queue cache retained separately; not promoted to previous verified cache.'}}
        Commit-ForgeQueueSnapshotFile $temporary $script:QueueSnapshotPath $backup
        $script:QueueSnapshotIssue=''
    }catch{Write-AppLog 'WARN' ('Queue snapshot save failed: '+$_.Exception.Message)}
    finally{if($temporary-and(Test-Path -LiteralPath $temporary)){Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue}}
}
function Load-OfflineQueueSnapshot($State=$null) {
    $script:QueueSnapshotIssue='';$script:QueueSnapshotCoreUnavailable=$false;$previousSnapshotMode=$script:OfflineSnapshotMode;$items=@();$primaryExists=Test-Path -LiteralPath $script:QueueSnapshotPath
    $previous=Join-Path $script:StateRoot 'queue-snapshot.previous.json'
    try {
        if($primaryExists){$items=@(Read-QueueSnapshotFile $script:QueueSnapshotPath)}
        elseif(Test-Path -LiteralPath $previous){throw 'Primary queue cache is missing while previous cache remains.'}
        else{$items=@(Read-QueueSnapshotFile $script:EmbeddedIdeasPath);if($items.Count-eq0){$saved=if($null-ne$State){$State}else{Read-LocalCoreState};if(@($saved.concepts|Where-Object{$null-ne$_}).Count-gt0-or@($script:Queue|Where-Object{$null-ne$_}).Count-gt0){throw 'Idea cache is missing while existing local work remains.'}}}
    }catch{
        Write-AppLog 'WARN' ('Queue cache unavailable: '+$_.Exception.Message)
        $restored=$false
        if(Test-Path -LiteralPath $previous){try{$items=@(Read-QueueSnapshotFile $previous);$restored=$true}catch{Write-AppLog 'WARN' ('Previous queue cache unavailable: '+$_.Exception.Message)}}
        if($restored){$script:QueueSnapshotIssue=Get-UiText 'queue.cache.previous' 'Previous verified idea cache; current cache unavailable.'}
        else{$items=@($script:Queue|Where-Object{$null-ne$_});$script:QueueSnapshotIssue=Get-UiText 'queue.cache.failed' 'Idea cache unavailable; files and previous view preserved.'}
    }
    $script:OfflineSnapshotMode=($items.Count-gt0)
    try{$nextQueue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue $items $State));$script:Queue=$nextQueue}catch{$script:StageFilterCache=$null;$script:OfflineSnapshotMode=$previousSnapshotMode;$script:QueueSnapshotCoreUnavailable=$true;$script:QueueSnapshotIssue=Get-UiText 'local.refresh.failed' 'Local refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.';Write-AppLog 'WARN' ('Queue retained after local-state failure: '+$_.Exception.Message)}
    Apply-Filter
    if($null-ne$QueueCountText){$QueueCountText.Text=if($script:QueueSnapshotIssue){$script:QueueSnapshotIssue}else{(Get-UiText 'queue.cached' '{0} cached ideas')-f@($script:Queue).Count}}
    if($script:QueueSnapshotIssue-and$null-ne$StatusText){$StatusText.Text=$script:QueueSnapshotIssue}
    if($script:QueueSnapshotCoreUnavailable-and(Get-Command Set-ForgeLocalReadUnavailable -ErrorAction SilentlyContinue)){Set-ForgeLocalReadUnavailable}
    return @($script:Queue).Count
}

$script:StageFilterCache=$null
function Get-StageFilterMap {
    # Stages of all ideas, recomputed only when the local state file or the Ideas list changed (not on every keystroke).
    $stamp=''; try{ $stamp=[string](Get-Item -LiteralPath $script:LocalCoreStatePath -ErrorAction Stop).LastWriteTimeUtc.Ticks }catch{}
    try{
        $basis=[ordered]@{state_stamp=$stamp;queue_keys=@($script:Queue|ForEach-Object{[string](Get-PropertyValue $_ 'concept_key')});creative_dirty=[bool]$script:Dirty;listing_dirty=[bool]$script:PublicationDirty;current=$null}
        if($null-ne$script:Current){$visible=Get-LocalCurrentRevisionIdentity $script:Current.concept;$basis.current=[ordered]@{concept_key=[string](Get-PropertyValue $script:Current.concept 'concept_key');revision_id=$visible.id;revision_hash=$visible.hash;brief_sha256=(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $script:Current.concept))}}
        $key=Get-StringSha256Hex (ConvertTo-Json -InputObject $basis -Depth 8 -Compress)
    }catch{$script:StageFilterCache=$null;Write-AppLog 'WARN' ('Stage filter context unavailable: '+$_.Exception.Message);return @{}}
    if($null -ne $script:StageFilterCache -and $script:StageFilterCache.key -eq $key){ return $script:StageFilterCache.map }
    $map=@{}
    try { $pipe=Get-ForgePortfolioPipeline (Read-LocalCoreState) $script:Queue; foreach($r in @($pipe.rows)){ $map[[string]$r.concept_key]=[string]$r.stage } } catch { $script:StageFilterCache=$null;Write-AppLog 'WARN' ('Stage filter failed: '+$_.Exception.Message);return @{} }
    $script:StageFilterCache=[pscustomobject]@{key=$key;map=$map}
    return $map
}
function Refresh-StageFilterIfActive {
    try {if($null-ne$FilterBox-and$null-ne$FilterBox.SelectedItem-and[string]$FilterBox.SelectedItem.Tag-like'stage:*'){$wasLoading=$script:ConceptLoadInProgress;$script:ConceptLoadInProgress=$true;try{Apply-Filter}finally{$script:ConceptLoadInProgress=$wasLoading}}}catch{}
}
function Apply-Filter {
    $items=@($script:Queue)
    $q=([string]$SearchBox.Text).Trim().ToLowerInvariant()
    if(-not [string]::IsNullOrWhiteSpace($q)) { $items=@($items | Where-Object { (([string]$_.title)+' '+([string]$_.hook)+' '+([string]$_.niche_name)+' '+([string]$_.workflow_state)).ToLowerInvariant().Contains($q) }) }
    $state=if($null -ne $FilterBox.SelectedItem){[string]$FilterBox.SelectedItem.Tag}else{''}
    if($state -like 'stage:*') {
        # Pipeline stage from local data (decision, artwork, checks, package, receipt) - same as the Portfolio board.
        $want=$state.Substring(6); $stageOf=Get-StageFilterMap
        $items=@($items | Where-Object { $stageOf.ContainsKey([string]$_.concept_key) -and $stageOf[[string]$_.concept_key] -eq $want })
    }
    elseif(-not [string]::IsNullOrWhiteSpace($state)) { $items=@($items | Where-Object { [string]$_.workflow_state -eq $state }) }
    $sort=if($null -ne $SortBox.SelectedItem){[string]$SortBox.SelectedItem.Tag}else{'title'}
    if($sort -eq 'title') { $items=@($items | Sort-Object title) }
    elseif($sort -eq 'workflow') { $items=@($items | Sort-Object workflow_state,title) }
    elseif($sort-eq'score'){$items=@($items|Sort-Object @{Expression={Get-ForgeSourceScoreSortValue $_};Descending=$true},title)}else{$items=@($items|Sort-Object title)}
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
        $script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue $raw))
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
    $spec=Get-PropertyValue $c 'production_spec'; $SpecBox.Text=ConvertTo-ForgeProductionSpecEditorText $spec; $ReasonBox.Text=''; if($null -ne $GenerationBriefText){$GenerationBriefText.Text=Get-GenerationBriefSummary $c}

    # Product-facing Overview is the default landing surface; Edit is secondary.
    try {
        $oe=Get-LocalizedOwnerExplanation $c
        $OverviewHook.Text=[string](Get-PropertyValue $c 'hook')
        $OverviewConcept.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'concept_text')) ([string]$c.hook))
        $OverviewBuyer.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'target_buyer')) ([string]$c.hook))
        $OverviewWhy.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'purchase_reason')) ([string]$c.hook))
        $OverviewDifferent.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'differentiation')) ([string]$c.hook))
        $OverviewVisual.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'visual_direction_text')) ([string]$c.hook))
        $meaning=[string](Get-PropertyValue $oe 'joke_explanation'); if([string]::IsNullOrWhiteSpace($meaning)){$meaning=[string](Get-PropertyValue $oe 'line_meaning')}; if([string]::IsNullOrWhiteSpace($meaning)){$meaning=[string](Get-PropertyValue $c 'concept_text')}; $OverviewMeaning.Text=$meaning
        $overviewState=Get-OverviewWorkflowState $c; $OverviewStatus.Text=Show-WorkflowState $overviewState
        $warnings=@(Get-PropertyValue $d 'analysis_warnings'); $OverviewWarnings.Text=if($warnings.Count){$warnings -join ' · '}else{Get-StaticUiText 'No current analysis warning.'}
    $OverviewWarnings.Text=(Format-ForgeOwnerLanguageReview $c)+"`n`n"+$OverviewWarnings.Text
        $OverviewNext.Text=Get-OverviewNextAction $overviewState
        $OverviewVisualButton.IsEnabled=$true
        $OverviewEditButton.IsEnabled=((Has-Cap 'edit') -and -not [bool](Get-PropertyValue $c 'current_revision_accepted'))
        Select-MainTab 'Overview'; Update-MainTabUi
    } catch {
        Write-AppLog 'ERROR' ('Overview rendering unavailable: '+$_.Exception.Message)
        $OverviewHook.Text=[string](Get-PropertyValue $c 'hook'); $OverviewConcept.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'concept_text')) ([string]$c.hook)); $OverviewBuyer.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'target_buyer')) ([string]$c.hook)); $OverviewWhy.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'purchase_reason')) ([string]$c.hook)); $OverviewVisual.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'visual_direction_text')) ([string]$c.hook)); $OverviewMeaning.Text=''; $OverviewStatus.Text='Overview partially unavailable'; $OverviewWarnings.Text=''; $OverviewNext.Text='Use the other tabs for details.'; Select-MainTab 'Overview'; Update-MainTabUi
    $OverviewWarnings.Text=(Format-ForgeOwnerLanguageReview $c)+"`n`n"+$OverviewWarnings.Text
    }

    # Analysis is informative. Missing optional metadata must never break concept loading.
    try {
        $oe=Get-LocalizedOwnerExplanation $c; $common=Get-PropertyValue $c 'common_law'; $trigger=Get-PropertyValue $c 'purchase_trigger'
        $AnalysisPurchase.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $c 'purchase_reason')) ([string]$c.hook))
        $AnalysisContext.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $oe 'profession_context')) ([string]$c.hook))
        $AnalysisMeaning.Text=(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $oe 'line_meaning')) ([string]$c.hook))+"`n`n"+(Format-ForgeOwnerOriginal ([string](Get-PropertyValue $oe 'joke_explanation')) ([string]$c.hook))
        $AnalysisEvidence.Text=("Common-law: {0}`nFederal: {1}`nPurchase trigger: {2}" -f (Show-PublicationCheckState ([string](Get-PropertyValue $common 'status'))),(Show-PublicationCheckState ([string](Get-PropertyValue $common 'federal_screen'))),([string](Get-PropertyValue $trigger 'purchase_trigger')))
        $scores=@(Get-PropertyValue $d 'scores')
        $AnalysisScores.Text=(Get-UiText 'assessment.limit' 'Unverified source assessments, not a market ranking.')+"`n"+(@($scores|Where-Object{$null-ne$_}|ForEach-Object{([string](Get-PropertyValue $_ 'dimension_key')).Replace('_',' ')+': '+(Get-UiText 'assessment.unverified' 'Unverified')})-join"`n")
        $scoreTech=(@($scores | ForEach-Object { "{0}: score={1}; confidence={2}; evidence={3}" -f (Get-PropertyValue $_ 'dimension_key'),(Get-PropertyValue $_ 'score'),(Get-PropertyValue $_ 'confidence'),(Get-PropertyValue $_ 'evidence') }) -join "`n")
        $AnalysisAdvanced.Text=("Source refs: {0}`n`nRaw source assessments (method/date and link to apparel purchases not verified):`n{1}" -f ((@(Get-PropertyValue $oe 'source_refs') -join ', ')),$scoreTech)
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
    $AuditList.ItemsSource=$null; $AuditDetail.Text='';$localEvents=@()
    try {
        $localEvents=@(Get-ForgeLocalReviewHistoryEvents (Get-LocalCoreConcept $Key (Read-LocalCoreState)))
        if($script:OfflineMode-or$script:ConnectionState-ceq'Local'-or(Test-CurrentIsResearchDraft)){$AuditList.ItemsSource=$localEvents;return}
        $r=Invoke-ForgeApi 'audit_history' @{concept_key=$Key;include_technical=$false;limit=100}
        $events=@($r.events)
        foreach($e in $events){$e|Add-Member -NotePropertyName display -NotePropertyValue (("{0} · {1}`n{2}" -f ([DateTimeOffset]$e.event_at).ToLocalTime().ToString('yyyy-MM-dd HH:mm'),$e.title,$e.summary)) -Force}
        $AuditList.ItemsSource=@($events)+@($localEvents)
    } catch { $technical=$_.Exception.Message; Write-AppLog 'ERROR' ('Audit history unavailable: '+$technical); if($localEvents.Count){$AuditList.ItemsSource=$localEvents;$AuditDetail.Text=if($script:Locale-ceq'ru'){'Доступна только сохранённая локальная история. Историю подключённого сервиса загрузить не удалось.'}elseif($script:Locale-ceq'es'){'Solo esta disponible el historial local guardado. No se pudo cargar el historial conectado.'}else{'Only saved local history is available. Connected service history could not be loaded.'}}else{$AuditDetail.Text=Get-HumanErrorMessage $technical};$AuditAdvanced.Text=$technical }
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
    $publicationView=Get-ForgeLocalRefreshView
    try {
        $r=Invoke-ForgeApi 'publication_workspace' @{concept_key=$Key};$w=Get-PropertyValue $r 'workspace';Assert-ForgePublicationWorkspaceIdentity $w
        $returnedKey=[string](Get-PropertyValue $w 'concept_key');if($returnedKey-and$returnedKey-cne$Key){throw 'The listing response belongs to another idea.'}
        Add-OrSetProperty $r 'loaded_concept_key' $Key;$script:Publication=$r
        try{Sync-LocalChecksFromLiveWorkspace $w}catch{}
        $PublicationCreativeStatus.Text=if([bool]$w.current_revision_accepted){("Accepted design · revision {0}`nVisual selected: {1}. Listing edits do not change the accepted design." -f $w.current_revision_no,$(if($w.accepted_visual_candidate_id){'Yes'}else{'No'}))}else{'No design accepted yet. Accept an exact design version before editing its listing.'}
        $draft=Get-SuggestedPublicationDraft $script:Current.concept
        $PublicationTitleBox.Text=Use-ValueOrSuggestion $w.listing_title $draft.title
        $PublicationBrandBox.Text=[string]$w.brand
        $PublicationBullet1Box.Text=Use-ValueOrSuggestion $w.bullet_1 $draft.bullet1
        $PublicationBullet2Box.Text=Use-ValueOrSuggestion $w.bullet_2 $draft.bullet2
        $PublicationDescriptionBox.Text=Use-ValueOrSuggestion $w.description $draft.description
        $existingKeywords=(@($w.keywords) -join ', '); $PublicationKeywordsBox.Text=Use-ValueOrSuggestion $existingKeywords $draft.keywords
        if([string](Get-PropertyValue $w 'current_metadata_revision_id')){
            $PublicationTitleBox.Text=[string]$w.listing_title;$PublicationBrandBox.Text=[string]$w.brand;$PublicationBullet1Box.Text=[string]$w.bullet_1;$PublicationBullet2Box.Text=[string]$w.bullet_2;$PublicationDescriptionBox.Text=[string]$w.description;$PublicationKeywordsBox.Text=$existingKeywords
        }
        $PublicationReasonBox.Text=''
        Set-PublicationLocaleSelection ([string](Get-PropertyValue $w 'locale'))
        $hasSavedDraft=(-not [string]::IsNullOrWhiteSpace([string]$w.listing_title)) -or (-not [string]::IsNullOrWhiteSpace([string]$w.description))
        $PublicationDraftNote.Text=if([string](Get-PropertyValue $w 'current_metadata_revision_id')){'Exact saved listing version loaded. Empty saved fields were preserved.'}elseif($hasSavedDraft){'Current listing fields loaded; missing fields have suggestions for review.'}else{'Draft prepared automatically from the concept. Review it; edit only if you want to change it.'}
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
        Restore-ForgeLocalRefreshView $publicationView
        if($null-ne$script:Publication-and[string](Get-PropertyValue $script:Publication 'loaded_concept_key')-ceq$Key){Add-OrSetProperty $script:Publication 'save_outcome_unverified' $true}else{$script:Publication=$null}
        $human=Get-HumanErrorMessage $technical; Set-LastDiagnostic 'publication_load' 0 'refresh' $technical $human; $PublicationCreativeStatus.Text='Publication details could not be loaded. Refresh and try again.'; $PublicationCheckIp.Text='IP · Not checked'; $PublicationCheckVisual.Text='Visual · Not checked'; $PublicationCheckPrint.Text='Print · Not checked'; $PublicationCheckPolicy.Text='Amazon policy · Not checked'; $PublicationEconomics.Text='Unavailable until Publication reloads.'; $PublicationPreflight.Text='Preflight is unavailable until Publication reloads.'; $PublicationExternal.Text='This Workbench cannot submit to Amazon.'; $PublicationAdvanced.Text=("Load error: {0}" -f $technical); $SavePublicationButton.IsEnabled=$false; $script:PublicationDirty=$publicationView.publication_dirty
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
function Load-Concept([string]$Key,[bool]$SkipDirtyPrompt=$false,[string]$ExpectedBriefSha='',[string]$PriorIterationRevisionId='') {
    if(Test-ResearchDraftKey $Key){
        if((-not $SkipDirtyPrompt) -and ($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')){return $false}
        $draftFound=$false;try{$draftFound=($null -ne (Get-ResearchDraft $Key))}catch{Write-AppLog 'WARN' ('Research draft lookup failed: '+$_.Exception.Message)}
        if(-not $draftFound){Show-Error 'This research draft is not available in local Forge state. Refresh the Ideas list.';return $false}
        return (Open-ResearchDraftItem ([pscustomobject]@{concept_key=$Key}) $true)
    }
    if((-not $SkipDirtyPrompt) -and ($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')) { return $false }
    $view=Get-ForgeLocalRefreshView;$loadFailed=$false
    Set-Busy $true 'Loading concept…'
    try {
        $liveReadFrame=Get-ForgeLiveReadFrame $Key
        $liveIntent=Get-ForgePendingSourceSaveId $Key
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
        if($null-eq$d-or$null-eq(Get-PropertyValue $d 'concept')){throw 'Concept detail response is empty.'}
        if($true){$fresh=$d.concept;if([string](Get-PropertyValue $fresh 'concept_key')-cne$Key-or![string](Get-PropertyValue $fresh 'current_revision_id')-or[string](Get-PropertyValue $fresh 'current_content_hash')-cnotmatch'^[0-9a-fA-F]{64}$'-or$null-eq(Get-PropertyValue $fresh 'production_spec')){throw 'Fresh source identity or full specification is unavailable; the previous view was preserved.'};foreach($field in @('concept_key','niche_name','title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')){if($null-eq$fresh.PSObject.Properties[$field]-or($null-ne(Get-PropertyValue $fresh $field)-and(Get-PropertyValue $fresh $field)-isnot[string])){throw 'Fresh full source fields are unavailable; the previous view was preserved.'}}
            $null=New-ForgeGenerationBriefSnapshot $fresh}
        if($ExpectedBriefSha-and(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $d.concept))-cne$ExpectedBriefSha){throw 'Reloaded source does not match the requested full brief; save remains unresolved.'}
        if($PriorIterationRevisionId-and([string](Get-PropertyValue $d.concept 'current_revision_id')-ceq$PriorIterationRevisionId-or(Get-PropertyValue $d.concept 'current_revision_accepted')-isnot[bool]-or[bool](Get-PropertyValue $d.concept 'current_revision_accepted'))){throw 'The new unaccepted iteration could not be verified; the source change remains unresolved.'}
        Add-OrSetProperty $d.concept 'core_materialization_pending' $true;Add-OrSetProperty $d.concept 'core_prior_record_sha256' $liveReadFrame
        $d.variants=$v2
        Populate-Detail $d; Restore-RoleEditability; $null=Ensure-LocalCoreConceptFromCurrent -VerifiedLiveIntentId $liveIntent;Update-OwnerDecisionControls; Load-AuditHistory $Key; Load-Downstream $Key; Load-Publication $Key; Load-Delivery $Key
        $StatusText.Text='Concept loaded'; return $true
    } catch {$loadFailed=$true;Restore-ForgeLocalRefreshView $view;throw} finally { Set-Busy $false $StatusText.Text;if($loadFailed){Set-ForgeLocalReadUnavailable} }
}
function New-ForgeOfflineConceptSnapshot($Item) {
    $fields=@('title','hook','niche_name','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')
    $c=[pscustomobject]@{concept_key=[string](Get-PropertyValue $Item 'concept_key');current_revision_no='snapshot';current_revision_id='';current_content_hash='';current_revision_accepted=$false;workflow_state=[string](Get-PropertyValue $Item 'workflow_state');production_spec=[pscustomobject]@{};offline_brief_basis='cached_snapshot';offline_saved_brief_sha256='';offline_materialization_pending=$true;offline_prior_record_sha256='absent'}
    foreach($field in $fields){$c|Add-Member NoteProperty $field ([string](Get-PropertyValue $Item $field))}
    $specProperty=$Item.PSObject.Properties['production_spec']
    if($null-ne$specProperty){
        if($specProperty.Value-isnot[pscustomobject]-and$specProperty.Value-isnot[Collections.IDictionary]){throw (Get-UiText 'offline.spec.invalid' 'The cached production specification is invalid. Previous view and files were preserved; restore or reload the complete source.')}
        $c.production_spec=ConvertFrom-ForgeProductionSpecJson (ConvertTo-ForgeBriefCanonicalJson $specProperty.Value)
    }
    # Preserve the existing legacy snapshot identity for a genuinely new cached item.
    $material=([ordered]@{concept_key=$c.concept_key;title=$c.title;hook=$c.hook;concept_text=$c.concept_text;visual_direction_text=$c.visual_direction_text}|ConvertTo-Json -Depth 8 -Compress)
    $hash=Get-StringSha256Hex $material;$c.current_content_hash=$hash;$c.current_revision_id='snapshot-'+$hash.Substring(0,24)
    # Partial queue rows must not erase a complete, matching locally saved brief.
    $state=Read-LocalCoreState;$lc=Get-LocalCoreConcept $c.concept_key $state
    if($null-ne$lc){$c.offline_prior_record_sha256=Get-StringSha256Hex ($lc|ConvertTo-Json -Depth 60 -Compress)}
    if($null-ne$lc){
        $saved=Get-PropertyValue $lc 'generation_brief_snapshot';$savedSha=[string](Get-PropertyValue $lc 'generation_brief_sha256')
        if($null-ne$saved-and$savedSha-cmatch'^[0-9a-f]{64}$'-and[string](Get-PropertyValue $saved 'concept_key')-ceq$c.concept_key){
            $normalized=New-ForgeGenerationBriefSnapshot $saved
            $same=((Get-ForgeBriefSha256 $saved)-ceq$savedSha-and(Get-ForgeBriefSha256 $normalized)-ceq$savedSha)
            foreach($field in $fields){if($null-ne$Item.PSObject.Properties[$field]-and[string](Get-PropertyValue $Item $field)-cne[string](Get-PropertyValue $saved $field)){$same=$false}}
            if($null-ne$specProperty-and(ConvertTo-ForgeBriefCanonicalJson $c.production_spec)-cne(ConvertTo-ForgeBriefCanonicalJson $normalized.production_spec)){$same=$false}
            foreach($pair in @(@('current_revision_id','source_revision_id'),@('current_content_hash','source_revision_hash'))){$declared=[string](Get-PropertyValue $Item $pair[0]);if($declared-and$declared-cne[string](Get-PropertyValue $lc $pair[1])){$same=$false}}
            $rid=[string](Get-PropertyValue $lc 'source_revision_id');$rhash=[string](Get-PropertyValue $lc 'source_revision_hash')
            if($same-and$rid-and$rhash-cmatch'^[0-9a-f]{64}$'){
                foreach($field in $fields){$c.$field=[string](Get-PropertyValue $normalized $field)}
                $c.production_spec=$normalized.production_spec;$c.current_revision_id=$rid;$c.current_content_hash=$rhash;$c.offline_brief_basis='saved_local_brief';$c.offline_saved_brief_sha256=$savedSha
            }
        }
    }
    $partial=($null-eq$specProperty)
    foreach($field in $fields){if($null-eq$Item.PSObject.Properties[$field]){$partial=$true}}
    if($partial-and$null-ne$lc-and$null-ne(Get-PropertyValue $lc 'generation_brief_snapshot')-and$c.offline_brief_basis-cne'saved_local_brief'){
        throw (Get-UiText 'offline.brief.incomplete' 'The partial queue snapshot does not match a verified saved full brief. Previous view and files were preserved; reload the complete source before replacing it.')
    }
    return $c
}

function Open-OfflineConceptItem($Item,[bool]$SkipDirtyPrompt=$false) {
    if($null -eq $Item){return}
    $key=([string](Get-PropertyValue $Item 'concept_key')).Trim()
    if(!$key){Show-Error 'Selected concept has no concept key. Refresh the workspace.';return}
    if(!$SkipDirtyPrompt-and$null-ne$script:Current-and[string](Get-PropertyValue $script:Current.concept 'concept_key')-ceq$key){return}
    if(!$SkipDirtyPrompt-and($script:Dirty-or$script:PublicationDirty)-and!(Confirm 'Discard unsaved creative/publication edits and open another concept?')){return}
    try{$c=New-ForgeOfflineConceptSnapshot $Item}catch{Show-Error $_.Exception.Message;return $false}
    $script:Dirty=$false;Set-PublicationDirty $false;$script:Publication=$null
    $script:OfflineSnapshotMode=$true
    $script:Current=[pscustomobject]@{concept=$c}
    Restore-RoleEditability
    $script:ProductSection='ideas'
    Show-ConceptSurface
    $ConceptTitle.Text=[string]$c.title
    $ConceptMeta.Text=Get-UiText 'offline.snapshot.meta' 'Local snapshot · live service unavailable'
    $OverviewHook.Text=[string]$c.hook
    $OverviewConcept.Text=(Format-ForgeOwnerOriginal ([string]$c.concept_text) ([string]$c.hook))
    $OverviewBuyer.Text=(Format-ForgeOwnerOriginal ([string]$c.target_buyer) ([string]$c.hook))
    $OverviewWhy.Text=(Format-ForgeOwnerOriginal ([string]$c.purchase_reason) ([string]$c.hook))
    $OverviewDifferent.Text=(Format-ForgeOwnerOriginal ([string]$c.differentiation) ([string]$c.hook))
    $OverviewVisual.Text=(Format-ForgeOwnerOriginal ([string]$c.visual_direction_text) ([string]$c.hook))
    $OverviewMeaning.Text=[string](Get-PropertyValue $Item 'meaning')
    $OverviewStatus.Text=Get-UiText 'queue.snapshot' 'Local snapshot'
    $OverviewWarnings.Text=if($c.offline_brief_basis-ceq'saved_local_brief'){Get-UiText 'offline.savedbrief.warning' 'Showing the exact locally saved full brief. Live source freshness is not established.'}else{Get-UiText 'offline.snapshot.warning' 'You are viewing the last known idea snapshot. Reconnect for live details.'}
    $OverviewWarnings.Text=(Format-ForgeOwnerLanguageReview $c)+"`n`n"+$OverviewWarnings.Text
    $OverviewNext.Text=Get-UiText 'offline.snapshot.next' 'Reconnect to load live evidence, artwork and publication state.'
    $OverviewVisualButton.IsEnabled=$true
    $OverviewEditButton.IsEnabled=$false
    $persisted=Ensure-LocalCoreConceptFromCurrent
    $c.offline_materialization_pending=$false;$c.offline_brief_basis='saved_local_brief';$c.offline_saved_brief_sha256=[string](Get-PropertyValue $persisted 'generation_brief_sha256')
    Update-OwnerDecisionControls
    Enter-LocalCoreSection 'ideas'
    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'};return $true
}
function Open-ConceptItem($Item,[bool]$SkipDirtyPrompt=$false) {
    if($script:ConceptLoadInProgress -or $null -eq $Item){return}
    if([bool](Get-PropertyValue $Item 'is_local_draft')){Open-ResearchDraftItem $Item $SkipDirtyPrompt;return}
    if($script:OfflineMode){Open-OfflineConceptItem $Item $SkipDirtyPrompt;return}
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

function Register-SourceAssessmentUiText {
    if($null-eq$script:UiText){return}
    $texts=@{
        en=@{'assessment.unverified'='Unverified';'assessment.none'='No source rating';'assessment.limit'='Source-provided assessments have no verified method, collection date or link to apparel purchases. They are not a market ranking or probability of success.';'assessment.count'='Source reports {0} concept records; this is not demand or competition.';'assessment.raw'='Raw source assessment (unverified): {0}; confidence field: {1}.';'sort.score'='Source score (unverified)';'discover.rank'='Source topics';'discover.body'='Review source observations and their limits. Stored assessments do not establish demand or a market ranking.';'draft.create'='Create editable draft template';'draft.create.hint'='Creates an incomplete local template from source context. For complete proposed ideas, open a prepared Home card. No generation or approval.';'draft.provenance'='Source context: {0} | unverified source score {1}, confidence field {2} | loaded {3} | {4} linked notes. Not a demand estimate.'}
        ru=@{'assessment.unverified'='Не проверено';'assessment.none'='Оценки источника нет';'assessment.limit'='Оценки источника не имеют проверенной методики, даты сбора и связи с покупками одежды. Это не рейтинг рынка и не вероятность успеха.';'assessment.count'='Источник сообщает о {0} записях концептов; это не спрос или конкуренция.';'assessment.raw'='Исходная оценка источника (не проверена): {0}; поле уверенности: {1}.';'sort.score'='Оценка источника (не проверена)';'discover.rank'='Темы источника';'discover.body'='Изучите наблюдения и ограничения источников. Сохранённые оценки не доказывают спрос и не задают рейтинг рынка.';'draft.create'='Создать редактируемый шаблон';'draft.create.hint'='Создаёт незавершённый локальный шаблон из контекста источника. Готовые предложенные идеи доступны в карточках Home. Без генерации и approval.';'draft.provenance'='Контекст источника: {0} | непроверенная оценка {1}, поле уверенности {2} | загружено {3} | связанных заметок: {4}. Это не оценка спроса.'}
        es=@{'assessment.unverified'='Sin verificar';'assessment.none'='Sin valoración de origen';'assessment.limit'='Las valoraciones de origen no tienen método, fecha ni vínculo verificados con compras de ropa. No son una clasificación comercial ni probabilidad de éxito.';'assessment.count'='La fuente informa de {0} registros de conceptos; no es demanda ni competencia.';'assessment.raw'='Valoración original (sin verificar): {0}; campo de confianza: {1}.';'sort.score'='Puntuación de origen (sin verificar)';'discover.rank'='Temas de la fuente';'discover.body'='Revisa observaciones y límites de las fuentes. Las valoraciones guardadas no demuestran demanda ni clasificación comercial.';'draft.create'='Crear plantilla editable';'draft.create.hint'='Crea una plantilla local incompleta del contexto. Las ideas completas propuestas están en Home. Sin generación ni aprobación.';'draft.provenance'='Contexto de origen: {0} | valoración no verificada {1}, campo de confianza {2} | cargado {3} | {4} notas vinculadas. No estima demanda.'}
    }
    $texts.en['offline.savedbrief.warning']='Showing the exact locally saved full brief. Live source freshness is not established.'
    $texts.ru['offline.savedbrief.warning']='Показан точный полный бриф, сохранённый локально. Актуальность сетевого источника не установлена.'
    $texts.es['offline.savedbrief.warning']='Se muestra el brief completo exacto guardado localmente. No se ha establecido la actualidad de la fuente en línea.'
    $texts.en['offline.spec.invalid']='The cached production specification is invalid. Previous view and files were preserved; restore or reload the complete source.'
    $texts.ru['offline.spec.invalid']='В кеше некорректная производственная спецификация. Прежний вид и файлы сохранены; восстановите или загрузите полный источник.'
    $texts.es['offline.spec.invalid']='La especificación de producción en caché no es válida. Se conservaron la vista y los archivos; restaura o carga la fuente completa.'
    $texts.en['offline.brief.incomplete']='The partial queue snapshot does not match a verified saved full brief. Previous view and files were preserved; reload the complete source before replacing it.'
    $texts.ru['offline.brief.incomplete']='Частичный снимок очереди не соответствует проверенному полному брифу. Прежний вид и файлы сохранены; перед заменой загрузите полный источник.'
    $texts.es['offline.brief.incomplete']='La instantánea parcial no coincide con un brief completo verificado. Se conservaron la vista y los archivos; carga la fuente completa antes de reemplazarlo.'
    $texts.en['offline.brief.changed']='The saved local full brief changed after this view was captured. Your view and files were preserved; reopen the current saved version before deciding or exporting.'
    $texts.ru['offline.brief.changed']='Полный локальный бриф изменился после загрузки этого вида. Вид и файлы сохранены; перед решением или экспортом откройте актуальную сохранённую версию.'
    $texts.es['offline.brief.changed']='El brief local cambió después de capturar esta vista. Se conservaron vista y archivos; abre la versión guardada actual antes de decidir o exportar.'
    $texts.en['recovery.approval.review']='DRAFT package only. Workspace data was recovered; review and approve the exact saved idea and design again.'
    $texts.ru['recovery.approval.review']='Только черновой пакет. Данные восстановлены из копии; заново проверьте и одобрите точную сохранённую идею и дизайн-концепт.'
    $texts.es['recovery.approval.review']='Solo paquete DRAFT. Se recuperaron datos; vuelve a revisar y aprobar la idea y el diseño guardados exactos.'
    $texts.en['recovery.approval.dialog']='Workspace data was recovered from an earlier snapshot. Previous approval was not restored. Review the complete saved idea and design below before giving new approval.'
    $texts.ru['recovery.approval.dialog']='Данные рабочего пространства восстановлены из прежней копии. Старое одобрение не восстановлено. Перед новым одобрением проверьте полный сохранённый текст идеи и дизайн-концепта ниже.'
    $texts.es['recovery.approval.dialog']='Se recuperaron datos de una copia anterior. No se restauró la aprobación previa. Revisa la idea y el diseño completos guardados antes de aprobarlos de nuevo.'
    $texts.en['iteration.ack_unverified']='The server acknowledged the iteration, but the new unaccepted full brief could not be verified. Your edits were preserved. Refresh the saved idea before retrying; generation did not start.'
    $texts.ru['iteration.ack_unverified']='Сервер подтвердил итерацию, но новый непринятый полный бриф проверить не удалось. Ваши правки сохранены в редакторе. Обновите сохранённую идею перед повтором; генерация не запускалась.'
    $texts.es['iteration.ack_unverified']='El servidor confirmó la iteración, pero no se pudo verificar el nuevo brief completo sin aceptar. Se conservaron tus cambios. Actualiza la idea guardada antes de reintentar; no se inició la generación.'
    $texts.en['iteration.unverified']='The iteration outcome could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat or generation started.'
    $texts.ru['iteration.unverified']='Результат создания итерации проверить не удалось. Ваши правки сохранены в редакторе. Обновите сохранённую идею перед повтором; повторный запрос и генерация автоматически не запускались.'
    $texts.es['iteration.unverified']='No se pudo verificar el resultado de la iteración. Se conservaron tus cambios. Actualiza la idea guardada antes de reintentar; no se inició otra solicitud ni generación automáticamente.'
    $texts.en['iteration.listing_discard']=' Unsaved publication metadata will be discarded.'
    $texts.ru['iteration.listing_discard']=' Несохранённые данные публикации будут отброшены.'
    $texts.es['iteration.listing_discard']=' Se descartarán los metadatos de publicación sin guardar.'
    $texts.en['source.save.ack_unverified']='The server acknowledged the save, but the current full brief could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat was sent.'
    $texts.ru['source.save.ack_unverified']='Сервер подтвердил сохранение, но текущий полный бриф проверить не удалось. Ваши правки сохранены в редакторе. Обновите сохранённую идею перед повтором; повторный запрос автоматически не отправлялся.'
    $texts.es['source.save.ack_unverified']='El servidor confirmó el guardado, pero no se pudo verificar el brief completo actual. Se conservaron tus cambios. Actualiza la idea guardada antes de reintentar; no se envió otra solicitud automáticamente.'
    $texts.en['source.save.unverified']='The save outcome could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat was sent.'
    $texts.ru['source.save.unverified']='Результат сохранения проверить не удалось. Ваши правки сохранены в редакторе. Обновите сохранённую идею перед повтором; повторный запрос автоматически не отправлялся.'
    $texts.es['source.save.unverified']='No se pudo verificar el resultado del guardado. Se conservaron tus cambios. Actualiza la idea guardada antes de reintentar; no se envió otra solicitud automáticamente.'
    $texts.en['source.save.pending_package']='DRAFT package only. Source save is unresolved; reload the saved idea before reviewing readiness.'
    $texts.ru['source.save.pending_package']='Только черновой пакет. Исход сохранения идеи не проверен; обновите сохранённую идею перед проверкой готовности.'
    $texts.es['source.save.pending_package']='Solo paquete DRAFT. El guardado de la idea no está resuelto; vuelve a cargarla antes de revisar la preparación.'
    $texts.en['connected.refresh.failed']='Refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.'
    $texts.ru['connected.refresh.failed']='Не удалось проверить обновление. Прежний вид и несохранённые правки сохранены; повторите после восстановления доступа.'
    $texts.es['connected.refresh.failed']='No se pudo verificar la actualización. Se conservaron vista y cambios sin guardar; reintenta al recuperar acceso.'
    $texts.en['local.refresh.failed']='Local refresh could not be verified. Previous view and unsaved edits were preserved; retry after restoring access.'
    $texts.ru['local.refresh.failed']='Не удалось проверить локальное обновление. Прежний вид и несохранённые правки сохранены; повторите после восстановления доступа.'
    $texts.es['local.refresh.failed']='No se pudo verificar la actualización local. Se conservaron vista y cambios sin guardar; reintenta al recuperar acceso.'
    $texts.en['local.refresh.missingdraft']='This local draft is no longer in the saved workspace. Your editor was preserved; select or restore a current draft before deciding or generating.'
    $texts.ru['local.refresh.missingdraft']='Этого локального черновика больше нет в сохранённом рабочем пространстве. Редактор сохранён; перед решением или генерацией выберите или восстановите актуальный черновик.'
    $texts.es['local.refresh.missingdraft']='Este borrador ya no está en el espacio guardado. Se conservó el editor; selecciona o restaura un borrador actual antes de decidir o generar.'
    foreach($loc in $texts.Keys){if($null-eq$script:UiText[$loc]){$script:UiText[$loc]=@{}};foreach($key in $texts[$loc].Keys){$script:UiText[$loc][$key]=$texts[$loc][$key]}}
}
function Format-ForgeUnverifiedAssessmentValue($Value) {
    if($null-eq$Value){return 'unknown'}
    if($Value-is[bool]-or$Value-is[Array]-or$Value-is[pscustomobject]-or$Value-is[Collections.IDictionary]){return 'invalid non-numeric source value'}
    $number=0.0;$text=[Convert]::ToString($Value,[Globalization.CultureInfo]::InvariantCulture)
    if(![double]::TryParse($text,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$number)-or[double]::IsNaN($number)-or[double]::IsInfinity($number)){return 'invalid non-finite or non-numeric source value'}
    return $number.ToString('0.###',[Globalization.CultureInfo]::InvariantCulture)
}
function Get-ForgeSourceScoreSortValue($Item) {
    $value=Get-PropertyValue $Item 'score_total';$text=Format-ForgeUnverifiedAssessmentValue $value;$n=0.0
    if(![double]::TryParse($text,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$n)){return [double]::NegativeInfinity};return $n
}
function Get-ForgeSourceConceptCountText($Value) {
    if(($Value-is[int]-or$Value-is[long])-and$Value-ge0){return [string]$Value};return 'unknown'
}
function Format-ForgeUnverifiedSourceDimensions($Dimensions) {
    $lines=New-Object Collections.Generic.List[string]
    if($null-ne$Dimensions-and$Dimensions-isnot[pscustomobject]-and$Dimensions-isnot[Collections.IDictionary]){return 'Invalid source dimension metadata; no verified assessment.'}
    if($Dimensions-is[Collections.IDictionary]){foreach($key in @($Dimensions.Keys|Sort-Object)){if($null-ne$Dimensions[$key]){$lines.Add(([string]$key).Replace('_',' ')+': '+(Format-ForgeUnverifiedAssessmentValue $Dimensions[$key])+' (source assessment; unverified)')}}}
    elseif($null-ne$Dimensions){foreach($p in @($Dimensions.PSObject.Properties|Sort-Object Name)){if($null-ne$p.Value){$lines.Add(($p.Name.Replace('_',' ')+': '+(Format-ForgeUnverifiedAssessmentValue $p.Value)+' (source assessment; unverified)'))}}}
    return $lines-join[Environment]::NewLine
}

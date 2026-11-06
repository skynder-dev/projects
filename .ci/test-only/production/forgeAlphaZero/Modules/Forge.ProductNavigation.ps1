. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Merch Forge · Product navigation + global product surfaces
# Owns Home / Discover / Ideas / Artwork / Checks / Publish / Portfolio / Performance routing.
$script:LocalCoreRecoveryRequired=$false
function Set-ProductNavSelected([string]$Section) {
    $buttons=@($NavHomeButton,$NavDiscoverButton,$NavIdeasButton,$NavArtworkButton,$NavChecksButton,$NavPublishButton,$NavPortfolioButton,$NavPerformanceButton)
    foreach($b in $buttons){if($null -eq $b){continue};$active=([string]$b.Tag -eq $Section);$b.Background=if($active){$Window.FindResource('AccentSoft')}else{[Windows.Media.Brushes]::Transparent};$b.BorderBrush=if($active){$Window.FindResource('AccentStroke')}else{[Windows.Media.Brushes]::Transparent};$b.Foreground=if($active){$Window.FindResource('Text')}else{$Window.FindResource('Secondary')}}
}
function Hide-ProductSurfaces {
    foreach($surface in @($HomeLandingScroll,$DiscoverLandingScroll,$SectionLandingScroll,$PortfolioLandingScroll,$PerformanceLandingScroll,$MainTabs)){if($null -ne $surface){$surface.Visibility='Collapsed'}}
}
function Test-CurrentLocalCoreActivity {
    if($null -eq $script:Current){return $false}
    try {
        $variants=@(Get-LocalCoreVariantsForCurrent)
        if($variants.Count -gt 0){return $true}
        $key=[string](Get-PropertyValue $script:Current.concept 'concept_key')
        if([string]::IsNullOrWhiteSpace($key)){return $false}
        $lc=Get-LocalCoreConcept $key
        if($null -eq $lc){return $false}
        $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept
        $acc=Get-PropertyValue $lc 'active_acceptance'
        return ($null -ne $acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq [string]$identity.id -and [string](Get-PropertyValue $acc 'revision_hash') -eq [string]$identity.hash)
    } catch { return $false }
}

function Get-DiscoverProp($Object,[string]$Name,$Default=$null) {
    if($null -eq $Object){return $Default}; $p=$Object.PSObject.Properties[$Name]; if($null -eq $p){return $Default}; return $p.Value
}
function Add-DiscoverDisplayProperties($Rows) {
    foreach($n in @($Rows|Where-Object{$null-ne$_})){
        $score=Get-DiscoverProp $n 'score_total' $null
        $label=if($null-eq$score){'-'}else{Get-UiText 'assessment.unverified' 'Unverified'}
        $count=Get-ForgeSourceConceptCountText (Get-DiscoverProp $n 'concept_count' $null)
        $n|Add-Member NoteProperty score_label $label -Force
        $n|Add-Member NoteProperty meta_label (([string](Get-DiscoverProp $n 'category' ''))+' | '+((Get-UiText 'assessment.count' 'Source reports {0} concept records; not demand.')-f$count)) -Force
    };return @($Rows|Where-Object{$null-ne$_})
}
function Update-DiscoverDetail {
    if($null-eq$DiscoverNicheList){return};$n=$DiscoverNicheList.SelectedItem
    if($null-eq$n){$DiscoverDetailName.Text=Get-UiText 'discover.detail.empty' 'Select a niche';$DiscoverDetailAudience.Text='';$DiscoverDetailSummary.Text='';$DiscoverDetailDimensions.Text='';return}
    $DiscoverDetailName.Text=Format-ForgeOwnerOriginal ([string](Get-DiscoverProp $n 'name' ''))
    $DiscoverDetailAudience.Text=(Format-ForgeOwnerOriginal ([string](Get-DiscoverProp $n 'audience' '')))+' | '+(Get-UiText 'assessment.limit' 'Source assessment unverified; not demand.')
    $DiscoverDetailSummary.Text=Format-ForgeOwnerOriginal ([string](Get-DiscoverProp $n 'research_summary' ''))
    $raw=(Get-UiText 'assessment.raw' 'Unverified raw source assessment: {0}; confidence field: {1}.')-f(Format-ForgeUnverifiedAssessmentValue (Get-DiscoverProp $n 'score_total' $null)),(Format-ForgeUnverifiedAssessmentValue (Get-DiscoverProp $n 'score_confidence' $null))
    $DiscoverDetailDimensions.Text=$raw+[Environment]::NewLine+(Format-ForgeUnverifiedSourceDimensions (Get-DiscoverProp $n 'dimensions' $null))
}
function Render-DiscoverSnapshot($r,[string]$SelectIdentity='') {
    if($null-ne$ConceptMeta){$ConceptMeta.Text=if($null-eq$r){'Актуальных доказательств нет. Архив сохранён; возможность продаж и спрос не установлены.'}else{Get-UiText 'discover.body' 'Stored observations; source assessments do not establish a market ranking.'}}
    if($null-ne$DiscoverRankTitle){$DiscoverRankTitle.Text=Get-UiText 'discover.rank' 'Source topics'}
    $evidenceBox=$Window.FindName('ResearchEvidenceRows');if($null-ne$evidenceBox){$packet=Get-DiscoverProp $r 'research_packet' $null;$evidenceBox.Text=if($null-ne$packet){Format-ResearchEvidenceRows $packet}else{'Сохранённый снимок: актуальность сбора и доказательства для этой ниши здесь не установлены.'}}
    $stats=Get-DiscoverProp $r 'stats' $null
    $DiscoverNichesValue.Text=[string](Get-DiscoverProp $stats 'niches' 0);$DiscoverNotesValue.Text=[string](Get-DiscoverProp $stats 'research_notes' 0);$DiscoverSourcesValue.Text=[string](Get-DiscoverProp $stats 'active_sources' 0);$DiscoverConceptsValue.Text=[string](Get-DiscoverProp $stats 'concepts' 0)
    $rows=@(Add-DiscoverDisplayProperties @(Get-DiscoverProp $r 'niches' @())|Sort-Object name)
    $DiscoverNicheList.ItemsSource=$rows;$sel=0
    if($SelectIdentity){for($i=0;$i-lt$rows.Count;$i++){$id=Get-DiscoverNicheIdentity $rows[$i];if($null-ne$id-and[string]$id.value-ceq$SelectIdentity){$sel=$i;break}}}
    if($rows.Count){$DiscoverNicheList.SelectedIndex=$sel};Update-DiscoverDetail
    $notes=@(Get-DiscoverProp $r 'notes' @());$noteLines=New-Object Collections.Generic.List[string]
    foreach($x in $notes|Where-Object{$null-ne$_}){$topic=[string](Get-DiscoverProp $x 'topic' '');$conclusion=[string](Get-DiscoverProp $x 'conclusion' '');$conclusion=Format-ForgeOwnerOriginal $conclusion;$noteLines.Add(('- {0}: {1}'-f$topic,$conclusion))}
    $DiscoverRecentText.Text=if($noteLines.Count){$noteLines-join[Environment]::NewLine}else{'-'}
    $sources=@(Get-DiscoverProp $r 'sources' @());$sourceLines=New-Object Collections.Generic.List[string]
    foreach($x in $sources|Where-Object{$null-ne$_}|Select-Object -First 8){$sourceLines.Add(('- {0} | {1} | observed {2} | {3}'-f[ string](Get-DiscoverProp $x 'name' ''),[string](Get-DiscoverProp $x 'url' ''),[string](Get-DiscoverProp $x 'last_checked_at' ''),[string](Get-DiscoverProp $x 'source_class' '')))}
    $DiscoverSourcesText.Text=if($sourceLines.Count){$sourceLines-join[Environment]::NewLine}else{'-'}
}
function Clear-ForgeDiscoverAfterReadFailure([string]$Message) {
    $script:DiscoverSnapshot=$null;$script:DiscoverLoadedAt=$null
    Render-DiscoverSnapshot $null
    $DiscoverStatusText.Text=$Message
    Update-DiscoverDraftControls
}
function Load-DiscoverSnapshot([bool]$Force=$false) {
    if($script:Busy){return}
    try{$imported=Read-ForgeImportedResearch;if($null-ne$imported){$script:DiscoverSnapshot=$imported;$script:DiscoverLoadedAt=[DateTime]::UtcNow;Render-DiscoverSnapshot $imported;$DiscoverStatusText.Text='Imported observations loaded; collected '+$imported.research_packet.collected_at+'; review source freshness and gaps';Update-DiscoverDraftControls;return}}catch{Clear-ForgeDiscoverAfterReadFailure 'Imported research failed validation; current source selection cleared. Existing ideas and archives retained; reimport or restore a verified copy.';Write-AppLog 'WARN' ('Imported research unavailable: '+$_.Exception.Message);return}
    if($null-ne$script:DiscoverSnapshot-and[string](Get-PropertyValue $script:DiscoverSnapshot 'origin')-ceq'local_import'){Clear-ForgeDiscoverAfterReadFailure 'The previously selected import is no longer active. Source selection cleared; existing ideas and archives retained. Reimport or restore a verified copy.';return}
    if($script:OfflineMode -or [string]::IsNullOrWhiteSpace($script:OwnerKey)){
        Clear-ForgeDiscoverAfterReadFailure (Get-UiText 'discover.offline' 'Live research is unavailable. No current source selection; existing ideas and archives retained.'); return
    }
    if(-not $Force -and $null -ne $script:DiscoverSnapshot){return}
    Set-Busy $true (Get-UiText 'discover.loading' 'Loading live research…')
    try {
        $r=Invoke-ForgeApi 'discover_snapshot' @{}
        $script:DiscoverSnapshot=$r; $script:DiscoverLoadedAt=[datetime]::UtcNow
        Render-DiscoverSnapshot $r
        $DiscoverStatusText.Text=('{0} · {1:HH:mm} UTC' -f (Get-UiText 'discover.ready' 'Stored research snapshot loaded; collection freshness not established'),[datetime]$script:DiscoverLoadedAt)
    } catch {
        Clear-ForgeDiscoverAfterReadFailure (Get-UiText 'discover.offline' 'Research unavailable; current source selection cleared, existing ideas and archives retained.');Write-AppLog 'WARN' ('Discover load failed: '+$_.Exception.Message)
    } finally {Set-Busy $false ([string]$DiscoverStatusText.Text); try{Update-DiscoverDraftControls}catch{}}
}

function Set-SectionLanding([string]$Section) {
    $titleKey='section.ideas.title';$bodyKey='section.ideas.body';$fallbackTitle='Ideas';$fallbackBody='Choose an idea from the list to continue.'
    switch($Section){'artwork'{$titleKey='section.artwork.title';$bodyKey='section.artwork.body';$fallbackTitle='Artwork';$fallbackBody='Choose an idea to generate, compare and review artwork.'};'checks'{$titleKey='section.checks.title';$bodyKey='section.checks.body';$fallbackTitle='Checks';$fallbackBody='Choose an idea to review evidence.'};'publish'{$titleKey='section.publish.title';$bodyKey='section.publish.body';$fallbackTitle='Publish';$fallbackBody='Choose an accepted product to prepare listing metadata and delivery.'}}
    if($null -ne $SectionLandingTitle){$SectionLandingTitle.Text=Get-UiText $titleKey $fallbackTitle}; if($null -ne $SectionLandingBody){$SectionLandingBody.Text=Get-UiText $bodyKey $fallbackBody}
    if($null -ne $SectionLandingHint){$SectionLandingHint.Text=if($script:OfflineMode){Get-UiText 'backend.offline.body' 'Live workspace data is temporarily unavailable.'}else{Get-UiText 'home.ready.body' 'Live workspace data is available.'}}
}
function Update-GlobalBusinessSurfaces {
    # No synthetic commerce numbers. These stay em-dash until a live commerce adapter supplies verified values.
    foreach($v in @($HomeMetricPublishedValue,$HomeMetricSalesValue,$HomeMetricRoyaltiesValue,$HomeMetricAttentionValue)){if($null -ne $v){$v.Text='—'}}
    if($null -ne $HomeAlexBody){$HomeAlexBody.Text=if($script:OfflineMode){Get-UiText 'home.alex.offline' 'Reconnect to load decisions that need your attention.'}else{Get-UiText 'metric.waiting' 'Waiting for live data'}}
    if($null -ne $HomePerformanceBody){$HomePerformanceBody.Text=if($script:OfflineMode){Get-UiText 'home.performance.offline' 'Sales and royalties will appear here when live commerce data is connected.'}else{Get-UiText 'metric.waiting' 'Waiting for live data'}}
    try { Update-LocalCoreBusinessSurfaces } catch { Write-AppLog 'WARN' ('Local core business surface refresh failed: '+$_.Exception.Message) }
}
function Show-LocalCoreRecoverySurface {
    Hide-ProductSurfaces; $HomeLandingScroll.Visibility='Visible'; $script:ProductSection='home'
    if($null-ne$ContextNav){$ContextNav.Visibility='Collapsed'}
    $message=Get-UiText 'recovery.body' 'The local data could not be read. The original files have been preserved. Use My data > Restore to choose a verified ZIP copy. Research, approval and generation are paused until recovery succeeds.'
    $HomeConnectionText.Text=Get-UiText 'recovery.title' 'Local data needs recovery'
    $HomeConnectionBody.Text=$message; $DataAutoCopyText.Text=$message; $StatusText.Text=$message
    $DataRestoreButton.IsEnabled=$true
}
function Set-LocalCoreRecoveryMode([bool]$Enabled) {
    $script:LocalCoreRecoveryRequired=$Enabled
    if($Enabled){
        $script:RecoveryDisabledControls=@()
        foreach($control in @($ProductNav,$LocalAICreateButton,$LocalAIReviseButton,$LocalAICancelButton,$HomeStageIdeas,$HomeStageArtwork,$HomeStageChecks,$HomeStagePublish)){
            if($null-ne$control){$script:RecoveryDisabledControls+=,[pscustomobject]@{control=$control;enabled=$control.IsEnabled};$control.IsEnabled=$false}
        }
        foreach($timer in @($script:LocalAITimer,$script:VisionReviewTimer,$script:AutoResearchTimer,$script:PreparationTimer)){if($null-ne$timer){$timer.Stop()}}
        Show-LocalCoreRecoverySurface
    }else{
        foreach($row in @($script:RecoveryDisabledControls)){if($null-ne$row){$row.control.IsEnabled=[bool]$row.enabled}}
        $script:RecoveryDisabledControls=@()
    }
}
function Show-ProductSection([string]$Section) {
    if($script:LocalCoreRecoveryRequired){Show-LocalCoreRecoverySurface;return}
    if([string]::IsNullOrWhiteSpace($Section)){$Section='home'}
    $Section=$Section.ToLowerInvariant(); if(-not (@('home','discover','ideas','artwork','checks','publish','portfolio','performance') -contains $Section)){$Section='home'}
    $script:ProductSection=$Section; Hide-ProductSurfaces; Set-ProductNavSelected $Section
    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
    switch($Section){
        'home' { $HomeLandingScroll.Visibility='Visible'; if($null -ne $ConceptTitle){$ConceptTitle.Text=Get-UiText 'home.title' 'Business dashboard'}; if($null -ne $ConceptMeta){$ConceptMeta.Text=''} }
        'discover' { $DiscoverLandingScroll.Visibility='Visible'; if($null -ne $ConceptTitle){$ConceptTitle.Text=Get-UiText 'discover.title' 'Discover / Research'}; if($null -ne $ConceptMeta){$ConceptMeta.Text=Get-UiText 'discover.body' 'Ranked market opportunities backed by Forge research, evidence and concept depth.'}; Load-DiscoverSnapshot $false }
        'portfolio' { $PortfolioLandingScroll.Visibility='Visible'; if($null -ne $ConceptTitle){$ConceptTitle.Text=Get-UiText 'portfolio.title' 'Portfolio'}; if($null -ne $ConceptMeta){$ConceptMeta.Text=Get-UiText 'portfolio.body' 'Published products, channels and listing health.'}; try{Update-PortfolioPipelineSurface}catch{Write-AppLog 'WARN' ('Portfolio pipeline refresh failed: '+$_.Exception.Message)} }
        'performance' { $PerformanceLandingScroll.Visibility='Visible'; if($null -ne $ConceptTitle){$ConceptTitle.Text=Get-UiText 'performance.title' 'Performance'}; if($null -ne $ConceptMeta){$ConceptMeta.Text=Get-UiText 'performance.body' 'Sales, royalties and product momentum.'} }
        default {
            if($null -ne $script:Current){ try{Restore-ConceptHeader}catch{} }
            if($null -eq $script:Current){
                $SectionLandingScroll.Visibility='Visible';Set-SectionLanding $Section
                if($null -ne $ConceptTitle){$ConceptTitle.Text=$SectionLandingTitle.Text}
                if($null -ne $ConceptMeta){$ConceptMeta.Text=if($script:OfflineMode){Get-UiText 'backend.offline.status' 'Workbench open · waiting for service'}else{''}}
            } elseif((Test-CurrentIsResearchDraft) -and $Section -in @('ideas','artwork','checks','publish')) {
                Enter-ResearchDraftSection $Section
            } elseif($script:OfflineMode -and $script:OfflineSnapshotMode) {
                if($Section -eq 'ideas'){
                    $MainTabs.Visibility='Visible';Enter-LocalCoreSection 'ideas'
                    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
                } elseif($Section -in @('artwork','checks','publish')) {
                    Enter-LocalCoreSection $Section
                    if($null -ne $ConceptMeta){$ConceptMeta.Text=Get-UiText 'offline.snapshot.meta' 'Local snapshot · live service unavailable'}
                    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
                } else {
                    $SectionLandingScroll.Visibility='Visible';Set-SectionLanding $Section
                }
            } else {
                $useLocalCore=(Test-CurrentLocalCoreActivity)
                if($useLocalCore -and $Section -in @('artwork','checks','publish')) {
                    Enter-LocalCoreSection $Section
                    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
                } else {
                    $MainTabs.Visibility='Visible';Set-ConceptTabsEnabled $true
                    if($null -ne $ContextNav){$ContextNav.Visibility='Visible'}
                    switch($Section){'ideas'{Select-MainTab 'Overview'};'artwork'{Select-MainTab 'Visuals & Generate'};'checks'{Select-MainTab 'Evidence'};'publish'{Select-MainTab 'Publication'}}
                    Update-MainTabUi
                }
            }
        }
    }
    Update-GlobalBusinessSurfaces;Update-ResponsiveLayout
}
function Restore-ConceptHeader {
    # Portfolio/Performance/Home/Discover put their own title in the shared header; put the idea back when returning to it.
    if($null -eq $script:Current -or $null -eq $ConceptTitle){return}
    $c=Get-PropertyValue $script:Current 'concept'; if($null -eq $c){return}
    $ConceptTitle.Text=[string](Get-PropertyValue $c 'title')
    if($null -eq $ConceptMeta){return}
    if(Test-CurrentIsResearchDraft){ $ConceptMeta.Text=(Get-UiText 'draft.meta' 'Local research draft · revision {0} · not on the server') -f [int](Get-PropertyValue $c 'current_revision_no') }
    elseif($script:OfflineMode -and $script:OfflineSnapshotMode){ $ConceptMeta.Text=Get-UiText 'offline.snapshot.meta' 'Local snapshot · live service unavailable' }
    else { $ConceptMeta.Text=('{0} · revision {1}' -f (Get-PropertyValue $c 'niche_name'),(Get-PropertyValue $c 'current_revision_no')) }
}
function Show-HomeLanding([bool]$Offline=$false) { $script:OfflineMode=$Offline;Show-ProductSection 'home' }
function Show-ConceptSurface { if($null -eq $script:Current){Show-ProductSection $script:ProductSection;return};if(@('home','discover','portfolio','performance') -contains $script:ProductSection){$script:ProductSection='ideas'};Show-ProductSection $script:ProductSection }
function Go-Home { Show-ProductSection 'home' }

# Merch Forge · Product navigation + global product surfaces
# Owns Home / Discover / Ideas / Artwork / Checks / Publish / Portfolio / Performance routing.
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
    foreach($n in @($Rows)){
        $score=Get-DiscoverProp $n 'score_total' $null; $confidence=Get-DiscoverProp $n 'score_confidence' $null; $count=[int](Get-DiscoverProp $n 'concept_count' 0)
        $scoreLabel=if($null -eq $score){'—'}else{('{0:0.0}' -f [double]$score)}
        $meta=('{0} · confidence {1:0.#}% · {2} concept(s)' -f [string](Get-DiscoverProp $n 'category' ''),[double]($confidence),$count)
        $n | Add-Member -NotePropertyName score_label -NotePropertyValue $scoreLabel -Force
        $n | Add-Member -NotePropertyName meta_label -NotePropertyValue $meta -Force
    }; return @($Rows)
}
function Update-DiscoverDetail {
    if($null -eq $DiscoverNicheList){return}; $n=$DiscoverNicheList.SelectedItem
    if($null -eq $n){$DiscoverDetailName.Text=Get-UiText 'discover.detail.empty' 'Select a niche';$DiscoverDetailAudience.Text='';$DiscoverDetailSummary.Text='';$DiscoverDetailDimensions.Text='';return}
    $DiscoverDetailName.Text=[string](Get-DiscoverProp $n 'name' '')
    $DiscoverDetailAudience.Text=('{0} · score {1:0.0} · confidence {2:0.#}% · concepts {3}' -f [string](Get-DiscoverProp $n 'audience' ''),[double](Get-DiscoverProp $n 'score_total' 0),[double](Get-DiscoverProp $n 'score_confidence' 0),[int](Get-DiscoverProp $n 'concept_count' 0))
    $DiscoverDetailSummary.Text=[string](Get-DiscoverProp $n 'research_summary' '')
    $dims=Get-DiscoverProp $n 'dimensions' $null; $parts=New-Object System.Collections.Generic.List[string]
    if($null -ne $dims){foreach($p in $dims.PSObject.Properties | Sort-Object Name){if($null -ne $p.Value){$label=($p.Name -replace '_',' ');[void]$parts.Add(('{0}: {1:0.#}' -f $label,[double]$p.Value))}}}
    $DiscoverDetailDimensions.Text=($parts -join '  ·  ')
}
function Render-DiscoverSnapshot($r,[string]$SelectIdentity='') {
    # Pure rendering of an already-loaded snapshot (also used to re-render after a language switch).
        $stats=Get-DiscoverProp $r 'stats' $null
    $DiscoverNichesValue.Text=[string](Get-DiscoverProp $stats 'niches' 0);$DiscoverNotesValue.Text=[string](Get-DiscoverProp $stats 'research_notes' 0);$DiscoverSourcesValue.Text=[string](Get-DiscoverProp $stats 'active_sources' 0);$DiscoverConceptsValue.Text=[string](Get-DiscoverProp $stats 'concepts' 0)
    $rows=@(Add-DiscoverDisplayProperties @(Get-DiscoverProp $r 'niches' @()))
    $DiscoverNicheList.ItemsSource=$rows
    $sel=0; if($SelectIdentity){for($i=0;$i -lt $rows.Count;$i++){$id=Get-DiscoverNicheIdentity $rows[$i];if($null -ne $id -and [string]$id.value -eq $SelectIdentity){$sel=$i;break}}}
    if($rows.Count -gt 0){$DiscoverNicheList.SelectedIndex=$sel;Update-DiscoverDetail}else{Update-DiscoverDetail}
    $notes=@(Get-DiscoverProp $r 'notes' @());$noteLines=New-Object System.Collections.Generic.List[string];foreach($x in $notes | Select-Object -First 7){$topic=[string](Get-DiscoverProp $x 'topic' '');$conclusion=[string](Get-DiscoverProp $x 'conclusion' '');if($conclusion.Length -gt 180){$conclusion=$conclusion.Substring(0,177)+'...'};[void]$noteLines.Add(('• {0}: {1}' -f $topic,$conclusion))};$DiscoverRecentText.Text=if($noteLines.Count){$noteLines -join [Environment]::NewLine}else{'—'}
    $sources=@(Get-DiscoverProp $r 'sources' @());$sourceLines=New-Object System.Collections.Generic.List[string];foreach($x in $sources | Select-Object -First 8){$name=[string](Get-DiscoverProp $x 'name' '');$class=[string](Get-DiscoverProp $x 'source_class' '');[void]$sourceLines.Add(('• {0} · {1}' -f $name,$class))};$DiscoverSourcesText.Text=if($sourceLines.Count){$sourceLines -join [Environment]::NewLine}else{'—'}
}
function Load-DiscoverSnapshot([bool]$Force=$false) {
    if($script:Busy){return}
    if($script:OfflineMode -or [string]::IsNullOrWhiteSpace($script:OwnerKey)){
        $DiscoverStatusText.Text=Get-UiText 'discover.offline' 'Live research is unavailable. No market data is fabricated.'; return
    }
    if(-not $Force -and $null -ne $script:DiscoverSnapshot){return}
    Set-Busy $true (Get-UiText 'discover.loading' 'Loading live research…')
    try {
        $r=Invoke-ForgeApi 'discover_snapshot' @{}
        $script:DiscoverSnapshot=$r; $script:DiscoverLoadedAt=[datetime]::UtcNow
        Render-DiscoverSnapshot $r
        $DiscoverStatusText.Text=('{0} · {1:HH:mm} UTC' -f (Get-UiText 'discover.ready' 'Live research loaded'),[datetime]$script:DiscoverLoadedAt)
    } catch {
        $DiscoverStatusText.Text=Get-UiText 'discover.offline' 'Live research is unavailable. No market data is fabricated.';Write-AppLog 'WARN' ('Discover load failed: '+$_.Exception.Message)
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
function Show-ProductSection([string]$Section) {
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
                    if($null -ne $ConceptTitle){$ConceptTitle.Text=if($Section -eq 'artwork'){Get-UiText 'section.artwork.title' 'Artwork'}elseif($Section -eq 'checks'){Get-UiText 'section.checks.title' 'Checks'}else{Get-UiText 'section.publish.title' 'Publish'}}
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
function Show-HomeLanding([bool]$Offline=$false) { $script:OfflineMode=$Offline;Show-ProductSection 'home' }
function Show-ConceptSurface { if($null -eq $script:Current){Show-ProductSection $script:ProductSection;return};if(@('home','discover','portfolio','performance') -contains $script:ProductSection){$script:ProductSection='ideas'};Show-ProductSection $script:ProductSection }
function Go-Home { Show-ProductSection 'home' }

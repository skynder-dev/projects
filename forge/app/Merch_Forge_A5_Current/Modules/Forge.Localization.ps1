# Merch Forge · Localization boundary
# Owns EN/RU/ES UI text application and locale persistence. No product actions.
function Get-UiText([string]$Key,[string]$Fallback='') {
    $locale=if($script:SupportedLocales -contains [string]$script:Locale){[string]$script:Locale}else{'en'}
    $localTable=$script:UiText[$locale]; if($null -ne $localTable -and $localTable.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace([string]$localTable[$Key])){return [string]$localTable[$Key]}
    $en=$script:UiText['en']; if($null -ne $en -and $en.ContainsKey($Key)){return [string]$en[$Key]}
    return $Fallback
}
function Get-StaticUiText([string]$Source) {
    if([string]::IsNullOrWhiteSpace($Source)){return $Source}
    if($script:Locale -eq 'en'){return $Source}
    $table=$script:StaticUiTranslations[$script:Locale]
    if($null -ne $table -and $table.ContainsKey($Source)){return [string]$table[$Source]}
    return $Source
}
function Add-StaticLocaleBinding($Element,[string]$Property,[string]$Source) {
    if($null -eq $Element -or [string]::IsNullOrWhiteSpace($Source)){return}
    [void]$script:StaticLocaleRegistry.Add([pscustomobject]@{Element=$Element;Property=$Property;Source=$Source})
}
function Register-StaticLocaleTree($Root) {
    $script:StaticLocaleRegistry.Clear()
    $stack=New-Object System.Collections.Stack; $stack.Push($Root)
    while($stack.Count -gt 0){
        $el=$stack.Pop(); if($null -eq $el){continue}
        try {
            if($el -is [Windows.Controls.TextBlock]){Add-StaticLocaleBinding $el 'Text' ([string]$el.Text)}
            if($el -is [Windows.Controls.HeaderedContentControl] -and $el -isnot [Windows.Controls.TabItem] -and $el.Header -is [string]){Add-StaticLocaleBinding $el 'Header' ([string]$el.Header)}
            if($el -is [Windows.Controls.ContentControl] -and $el.Content -is [string]){Add-StaticLocaleBinding $el 'Content' ([string]$el.Content)}
            if($el -is [Windows.FrameworkElement] -and $el.ToolTip -is [string]){Add-StaticLocaleBinding $el 'ToolTip' ([string]$el.ToolTip)}
        } catch {}
        try { foreach($child in [Windows.LogicalTreeHelper]::GetChildren($el)){ if($child -is [Windows.DependencyObject]){$stack.Push($child)} } } catch {}
    }
}
function Apply-StaticLocaleUi {
    foreach($b in @($script:StaticLocaleRegistry)){
        try {
            $value=Get-StaticUiText ([string]$b.Source)
            switch([string]$b.Property){
                'Text' {$b.Element.Text=$value}
                'Content' {$b.Element.Content=$value}
                'Header' {$b.Element.Header=$value}
                'ToolTip' {$b.Element.ToolTip=$value}
            }
        } catch {}
    }
}
function Get-PublicationLocaleDefault {
    if($script:Locale -eq 'ru'){return 'ru-RU'}
    if($script:Locale -eq 'es'){return 'es-ES'}
    return 'en-US'
}
function Get-PublicationLocale {
    if($null -ne $PublicationLocaleBox -and $null -ne $PublicationLocaleBox.SelectedItem){
        $v=[string]$PublicationLocaleBox.SelectedItem.Tag
        if($v -in @('en-US','ru-RU','es-ES')){return $v}
    }
    return Get-PublicationLocaleDefault
}
function Set-PublicationLocaleSelection([string]$Locale) {
    $v=([string]$Locale).Trim(); if($v -notin @('en-US','ru-RU','es-ES')){$v=Get-PublicationLocaleDefault}
    if($null -eq $PublicationLocaleBox){return}
    foreach($item in @($PublicationLocaleBox.Items)){if([string]$item.Tag -eq $v){$PublicationLocaleBox.SelectedItem=$item;break}}
}
function Get-LocalizedOwnerExplanation($Concept) {
    $base=Get-PropertyValue $Concept 'owner_explanation'
    if($script:Locale -eq 'en' -or $null -eq $Concept){return $base}
    $effective=[string](Get-PropertyValue $base 'effective_locale')
    $fallback=[bool](Get-PropertyValue $base 'fallback_used')
    if($effective -eq $script:Locale -and -not $fallback){return $base}
    $revisionId=[string](Get-PropertyValue $Concept 'current_revision_id')
    if([string]::IsNullOrWhiteSpace($revisionId)){return $base}
    $entry=$script:OwnerExplanationTranslations[$revisionId]
    if($null -eq $entry){return $base}
    $overlay=$entry[$script:Locale]; if($null -eq $overlay){return $base}
    return [pscustomobject]@{
        profession_context=[string]$overlay.profession_context
        line_meaning=[string]$overlay.line_meaning
        joke_explanation=[string]$overlay.joke_explanation
        confidence=Get-PropertyValue $base 'confidence'
        source_refs=Get-PropertyValue $base 'source_refs'
        requested_locale=$script:Locale
        effective_locale=$script:Locale
        fallback_used=$false
        revision_binding=$revisionId
        translation_source='embedded_exact_revision_v1'
    }
}
function Load-UiLocale {
    try { if(Test-Path -LiteralPath $script:LocalePath){$v=(Get-Content -LiteralPath $script:LocalePath -Raw).Trim().ToLowerInvariant();if($script:SupportedLocales -contains $v){return $v}} } catch { Write-AppLog 'WARN' ('Locale read failed: '+$_.Exception.Message) }
    return 'en'
}
function Save-UiLocale([string]$Locale) {
    if(-not ($script:SupportedLocales -contains $Locale)){return}
    try { Ensure-Dir $script:StateRoot; Set-Content -LiteralPath $script:LocalePath -Value $Locale -Encoding ASCII -Force } catch { Write-AppLog 'WARN' ('Locale save failed: '+$_.Exception.Message) }
}
function Apply-LocaleUi {
    if($null -eq $Window){return}

    # Translate the static XAML tree first. Explicit/dynamic bindings below always win.
    Apply-StaticLocaleUi
    $Window.Title=Get-UiText 'window.title' 'Merch Forge · Product Workspace'

    if($null -ne $LanguageLabel){$LanguageLabel.Text=Get-UiText 'language.label' 'Language'}
    if($null -ne $LoginLanguageLabel){$LoginLanguageLabel.Text=Get-UiText 'language.label' 'Language'}
    if($null -ne $LanguageStatusText){
        $statusKey=if($script:Locale -eq 'ru'){'language.status.ru'}elseif($script:Locale -eq 'es'){'language.status.es'}else{'language.status.en'}
        $LanguageStatusText.Text=Get-UiText $statusKey 'English'
        $LanguageStatusText.ToolTip=if($script:Locale -eq 'ru'){'Русский интерфейс'}elseif($script:Locale -eq 'es'){'Interfaz en español'}else{'English UI'}
    }
    if($null -ne $LoginLanguageStatusText){
        $LoginLanguageStatusText.Text=if($script:Locale -eq 'ru'){Get-UiText 'language.status.ru' 'Русский'}elseif($script:Locale -eq 'es'){Get-UiText 'language.status.es' 'Español'}else{Get-UiText 'language.status.en' 'English'}
        $LoginLanguageStatusText.ToolTip=if($script:Locale -eq 'ru'){'Русский интерфейс'}elseif($script:Locale -eq 'es'){'Interfaz en español'}else{'English UI'}
    }
    if($null -ne $RememberBox){$RememberBox.Content=Get-UiText 'login.remember' 'Remember on this Windows account'}
    if($null -ne $ConnectButton){$ConnectButton.Content=Get-UiText 'login.open' 'Open Workbench'}
    if($null -ne $SavedAccessText){$SavedAccessText.Text=Get-UiText 'login.saved' 'Saved access is protected for your Windows account.'}

    if($null -ne $BackendBannerText){$BackendBannerText.Text=Get-UiText 'backend.unavailable' 'Backend unavailable'}
    if($null -ne $BackendRetryButton -and -not $script:Busy){$BackendRetryButton.Content=Get-UiText 'backend.retry' 'Retry'}
    if($null -ne $BackendText){$BackendText.Text=if($script:OfflineMode){Get-UiText 'backend.unavailable' 'Backend unavailable'}elseif($script:BackendVersion){Get-UiText 'system.connected' 'Connected'}else{Get-UiText 'system.notconnected' 'Not connected'}}
    if($null -ne $StatusText -and $script:OfflineMode){$StatusText.Text=Get-UiText 'backend.offline.status' 'Workbench open · waiting for service'}

    if($null -ne $ConceptsLabel){$ConceptsLabel.Text=Get-UiText 'queue.concepts' 'Ideas'}
    if($null -ne $SearchLabel){$SearchLabel.Text=Get-UiText 'queue.search' 'Search'}
    if($null -ne $StatusLabel){$StatusLabel.Text=Get-UiText 'queue.status' 'Status'}
    if($null -ne $SortLabel){$SortLabel.Text=Get-UiText 'queue.sort' 'Sort'}
    if($null -ne $SearchPlaceholder){$SearchPlaceholder.Text=Get-UiText 'queue.placeholder' 'Title, slogan or profession'}

    if($null -ne $FilterBox){
        foreach($item in @($FilterBox.Items)){
            switch([string]$item.Tag){
                '' {$item.Content=Get-UiText 'queue.all' 'All statuses'}
                'generation_ready' {$item.Content=Get-UiText 'queue.ready' 'Ready to generate'}
                'in_edit' {$item.Content=Get-UiText 'queue.editing' 'Editing'}
                'generation_requested' {$item.Content=Get-UiText 'queue.requested' 'Generation requested'}
                'has_variants' {$item.Content=Get-UiText 'queue.variants' 'Has variants'}
                'accepted' {$item.Content=Get-UiText 'queue.accepted' 'Accepted'}
                'blocked' {$item.Content=Get-UiText 'queue.blocked' 'Blocked'}
                'research_draft' {$item.Content=Get-UiText 'queue.draft' 'Research draft'}
            }
        }
    }
    if($null -ne $SortBox){
        foreach($item in @($SortBox.Items)){
            switch([string]$item.Tag){
                'score' {$item.Content=Get-UiText 'sort.score' 'Score: high to low'}
                'title' {$item.Content=Get-UiText 'sort.title' 'Title: A to Z'}
                'workflow' {$item.Content=Get-UiText 'sort.workflow' 'Workflow status'}
            }
        }
    }

    if($null -ne $OverviewVisualButton){$OverviewVisualButton.Content=Get-UiText 'overview.review' 'Review visuals / generation'}
    if($null -ne $OverviewEditButton){$OverviewEditButton.Content=Get-UiText 'overview.edit' 'Edit concept'}
    if($null -ne $LocalExportBriefButton){$LocalExportBriefButton.Content=Get-UiText 'local.brief' 'Export generation brief'}
    if($null -ne $LocalImportArtworkButton){$LocalImportArtworkButton.Content=Get-UiText 'local.import.art' 'Import artwork…'}
    if($null -ne $LocalAcceptButton){$LocalAcceptButton.Content=Get-UiText 'local.accept' 'Accept local artwork'}
    if($null -ne $LocalImportCheckEvidenceButton){$LocalImportCheckEvidenceButton.Content=Get-UiText 'local.import.checks' 'Import check evidence…'}
    if($null -ne $LocalBuildPackageButton){$LocalBuildPackageButton.Content=Get-UiText 'local.package' 'Build local Amazon package'}
    if($null -ne $LocalImportSalesButton){$LocalImportSalesButton.Content=Get-UiText 'local.sales' 'Import sales CSV…'}
    if($null -ne $LocalImportPublicationReceiptButton){$LocalImportPublicationReceiptButton.Content=Get-UiText 'local.publication.receipt' 'Import publication receipt…'}

    if($null -ne $NavHomeButton){$NavHomeButton.Content=Get-UiText 'nav.home' 'Home'}
    if($null -ne $NavDiscoverButton){$NavDiscoverButton.Content=Get-UiText 'nav.discover' 'Discover'}
    if($null -ne $NavIdeasButton){$NavIdeasButton.Content=Get-UiText 'nav.ideas' 'Ideas'}
    if($null -ne $NavArtworkButton){$NavArtworkButton.Content=Get-UiText 'nav.artwork' 'Artwork'}
    if($null -ne $NavChecksButton){$NavChecksButton.Content=Get-UiText 'nav.checks' 'Checks'}
    if($null -ne $NavPublishButton){$NavPublishButton.Content=Get-UiText 'nav.publish' 'Publish'}
    if($null -ne $NavPortfolioButton){$NavPortfolioButton.Content=Get-UiText 'nav.portfolio' 'Portfolio'}
    if($null -ne $NavPerformanceButton){$NavPerformanceButton.Content=Get-UiText 'nav.performance' 'Performance'}
    if($null -ne $ProductNavHint){$ProductNavHint.Text=Get-UiText 'product.workspace' 'Product workspace'}
    if($null -ne $SectionLandingKicker){$SectionLandingKicker.Text=Get-UiText 'section.kicker' 'PRODUCT WORKSPACE'}

    if($null -ne $ContextHistoryButton){$ContextHistoryButton.Content=Get-UiText 'context.history' 'History'}
    if($null -ne $ContextDeliveryButton){$ContextDeliveryButton.Content=Get-UiText 'context.delivery' 'Delivery'}
    if($null -ne $ContextEditButton){$ContextEditButton.Content=Get-UiText 'context.edit' 'Edit'}

    if($null -ne $HomeTitle){$HomeTitle.Text=Get-UiText 'home.title' 'Business dashboard'}
    if($null -ne $HomeBody){$HomeBody.Text=Get-UiText 'home.body' 'Ideas, products and results in one place — from first concept to sales.'}
    if($null -ne $HomeStatusLabel){$HomeStatusLabel.Text=Get-UiText 'home.status' 'WORKSPACE STATUS'}
    if($null -ne $HomeConnectionText){$HomeConnectionText.Text=if($script:OfflineMode){Get-UiText 'home.offline' 'Offline workspace'}else{Get-UiText 'home.ready' 'Connected'}}
    if($null -ne $HomeConnectionBody){$HomeConnectionBody.Text=if($script:OfflineMode){Get-UiText 'home.offline.body' 'The app stays usable. Live data will appear when the service reconnects.'}else{Get-UiText 'home.ready.body' 'Live workspace data is available.'}}
    if($null -ne $HomeMetricPublishedLabel){$HomeMetricPublishedLabel.Text=Get-UiText 'metric.published' 'Published'}
    if($null -ne $HomeMetricSalesLabel){$HomeMetricSalesLabel.Text=Get-UiText 'metric.sales30' 'Sales · 30 days'}
    if($null -ne $HomeMetricRoyaltiesLabel){$HomeMetricRoyaltiesLabel.Text=Get-UiText 'metric.royalties30' 'Royalties · 30 days'}
    if($null -ne $HomeMetricAttentionLabel){$HomeMetricAttentionLabel.Text=Get-UiText 'metric.attention' 'Needs attention'}
    foreach($x in @($HomeMetricPublishedHint,$HomeMetricSalesHint,$HomeMetricRoyaltiesHint,$HomeMetricAttentionHint)){if($null -ne $x){$x.Text=Get-UiText 'metric.waiting' 'Waiting for live data'}}
    if($null -ne $HomePipelineTitle){$HomePipelineTitle.Text=Get-UiText 'home.pipeline' 'Pipeline'}
    if($null -ne $HomePipelineBody){$HomePipelineBody.Text=Get-UiText 'home.pipeline.body' 'Move products through clear stages without mixing product work with application internals.'}
    if($null -ne $HomeStageIdeas){$HomeStageIdeas.Text=Get-UiText 'nav.ideas' 'Ideas'}
    if($null -ne $HomeStageArtwork){$HomeStageArtwork.Text=Get-UiText 'nav.artwork' 'Artwork'}
    if($null -ne $HomeStageChecks){$HomeStageChecks.Text=Get-UiText 'nav.checks' 'Checks'}
    if($null -ne $HomeStagePublish){$HomeStagePublish.Text=Get-UiText 'nav.publish' 'Publish'}
    if($null -ne $HomeAlexTitle){$HomeAlexTitle.Text=Get-UiText 'home.alex' 'Alex Needed'}
    if($null -ne $HomeAlexBody -and $script:OfflineMode){$HomeAlexBody.Text=Get-UiText 'home.alex.offline' 'Reconnect to load decisions that need your attention.'}
    if($null -ne $HomePerformanceTitle){$HomePerformanceTitle.Text=Get-UiText 'home.performance' 'Performance snapshot'}
    if($null -ne $HomePerformanceBody -and $script:OfflineMode){$HomePerformanceBody.Text=Get-UiText 'home.performance.offline' 'Sales and royalties will appear here when live commerce data is connected.'}


    if($null -ne $DiscoverTitle){$DiscoverTitle.Text=Get-UiText 'discover.title' 'Discover / Research'}
    if($null -ne $DiscoverBody){$DiscoverBody.Text=Get-UiText 'discover.body' 'Ranked market opportunities backed by Forge research, evidence and concept depth.'}
    if($null -ne $DiscoverRefreshButton){$DiscoverRefreshButton.Content=Get-UiText 'discover.refresh' 'Refresh research'}
    try{Update-DiscoverDraftControls}catch{}
    if($null -ne $DiscoverNichesLabel){$DiscoverNichesLabel.Text=Get-UiText 'discover.niches' 'Niches'}
    if($null -ne $DiscoverNotesLabel){$DiscoverNotesLabel.Text=Get-UiText 'discover.notes' 'Research notes'}
    if($null -ne $DiscoverSourcesLabel){$DiscoverSourcesLabel.Text=Get-UiText 'discover.sources' 'Active sources'}
    if($null -ne $DiscoverConceptsLabel){$DiscoverConceptsLabel.Text=Get-UiText 'discover.concepts' 'Concepts'}
    if($null -ne $DiscoverRankTitle){$DiscoverRankTitle.Text=Get-UiText 'discover.rank' 'Ranked opportunities'}
    if($null -ne $DiscoverDetailTitle){$DiscoverDetailTitle.Text=Get-UiText 'discover.detail' 'Opportunity detail'}
    if($null -ne $DiscoverRecentTitle){$DiscoverRecentTitle.Text=Get-UiText 'discover.recent' 'Recent research'}
    if($null -ne $DiscoverSourcesTitle){$DiscoverSourcesTitle.Text=Get-UiText 'discover.source.list' 'Evidence sources'}
    if($null -ne $PortfolioTitle){$PortfolioTitle.Text=Get-UiText 'portfolio.title' 'Portfolio'}
    if($null -ne $PortfolioBody){$PortfolioBody.Text=Get-UiText 'portfolio.body' 'Published products, channels and listing health.'}
    if($null -ne $PortfolioEmpty){$PortfolioEmpty.Text=Get-UiText 'portfolio.empty' 'Connect live commerce data to load your published products.'}
    if($null -ne $PerformanceTitle){$PerformanceTitle.Text=Get-UiText 'performance.title' 'Performance'}
    if($null -ne $PerformanceBody){$PerformanceBody.Text=Get-UiText 'performance.body' 'Sales, royalties and product momentum across 7 / 30 / 90 days.'}
    if($null -ne $PerformanceEmpty){$PerformanceEmpty.Text=Get-UiText 'performance.empty' 'Connect live commerce data to load sales and royalty performance.'}

    $tabKeys=@{overview='tab.overview';visuals='tab.visuals';history='tab.history';evidence='tab.evidence';delivery='tab.delivery';publication='tab.publication';edit='tab.edit'}
    foreach($tab in @($MainTabs.Items)){if($tab -is [Windows.Controls.TabItem]){$k=Get-MainTabKey $tab;if($tabKeys.ContainsKey($k)){$tab.Header=Get-UiText $tabKeys[$k] ([string]$tab.Header)}}}

    if($null -eq $script:Current -and (@('ideas','artwork','checks','publish') -contains $script:ProductSection)){Set-SectionLanding $script:ProductSection}
    try { Apply-RoleUi } catch {}
    try { if($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')){Load-LocalPublicationUi} } catch {}
    try { Update-LocalCoreBusinessSurfaces } catch {}
    try { Update-OwnerDecisionControls } catch {}
    try { Restore-DynamicSurfacesAfterLocale } catch { Write-AppLog 'WARN' ('Dynamic surface restore after locale change failed: '+$_.Exception.Message) }
    try { if(@($script:Queue).Count -gt 0){[void](Add-QueueDisplayProperties $script:Queue);Apply-Filter}else{Set-QueueEmptyState 0} } catch {}
    Update-ResponsiveLayout
}

function Set-UiLocale([string]$Locale,[bool]$Persist=$true) {
    $v=([string]$Locale).Trim().ToLowerInvariant(); if(-not ($script:SupportedLocales -contains $v)){return $false}
    if(($script:Dirty -or $script:PublicationDirty) -and $v -ne $script:Locale){
        $StatusText.Text=Get-UiText 'locale.dirty' 'Save or discard current edits before changing UI language.'
        return $false
    }
    $script:Locale=$v; if($Persist){Save-UiLocale $v}; Apply-LocaleUi; return $true
}
function Sync-LanguageSelector {
    $script:LocaleChangeInProgress=$true
    try {
        foreach($box in @($LanguageBox,$LoginLanguageBox)){if($null -eq $box){continue};foreach($item in @($box.Items)){if([string]$item.Tag -eq $script:Locale){$box.SelectedItem=$item;break}}}
        if($null -ne $LoginLangEn){$LoginLangEn.IsChecked=($script:Locale -eq 'en')}; if($null -ne $LoginLangRu){$LoginLangRu.IsChecked=($script:Locale -eq 'ru')}; if($null -ne $LoginLangEs){$LoginLangEs.IsChecked=($script:Locale -eq 'es')}
        if($null -ne $HeaderLangEn){$HeaderLangEn.IsChecked=($script:Locale -eq 'en')}; if($null -ne $HeaderLangRu){$HeaderLangRu.IsChecked=($script:Locale -eq 'ru')}; if($null -ne $HeaderLangEs){$HeaderLangEs.IsChecked=($script:Locale -eq 'es')}
    } finally { $script:LocaleChangeInProgress=$false }
}
function Initialize-UiLocale {
    if($script:StaticLocaleRegistry.Count -eq 0){Register-StaticLocaleTree $Window}
    $loaded=Load-UiLocale; if(-not ($script:SupportedLocales -contains $loaded)){$loaded='en'}; $script:Locale=$loaded
    Sync-LanguageSelector; Apply-LocaleUi
}

# Merch Forge · CI WPF smoke hook
# Dot-sourced into a CI-only copy of MerchForgeWorkbench.ps1 right before ShowDialog.
# Drives the REAL window with REAL controls: Discover -> Create concept draft -> owner review -> edit -> artwork brief -> restart.
# Network is impossible by construction: Invoke-ForgeApi returns a labelled fixture for discover_snapshot only and throws for
# everything else; Invoke-RestMethod / Invoke-WebRequest throw. Modal dialogs are captured instead of shown.

$script:Ci = [ordered]@{ phase=[string]$env:FORGE_CI_PHASE; checks=[ordered]@{}; api=@(); errors=@(); confirms=@(); screenshots=@(); fatal=$null; network=0 }
function Ci-Check([string]$Name,[bool]$Ok,$Detail='') { $script:Ci.checks[$Name]=[ordered]@{pass=$Ok;detail=[string]$Detail} }
function Show-Error([string]$Message) { $script:Ci.errors += $Message }
function Confirm([string]$Message,[string]$Title='Merch Forge') { $script:Ci.confirms += $Message; return $true }
function Show-FatalError([string]$Message) { $script:Ci.fatal = 'Show-FatalError: '+$Message }
function Invoke-RestMethod { $script:Ci.network++; throw 'CI: network disabled' }
function Invoke-WebRequest { $script:Ci.network++; throw 'CI: network disabled' }
function Get-CiFixture {
    $n1=[pscustomobject]@{niche_id='ci-fixture-nurses';name='CI FIXTURE · Night-shift nurses';category='profession';audience='ICU and ER nurses on night rotation';score_total=8.4;score_confidence=72;concept_count=3;research_summary='CI fixture summary (not market data): recurring humor about night shifts and coffee.';dimensions=[pscustomobject]@{demand=8.1;competition=6.2;evergreen=9.0}}
    $n2=[pscustomobject]@{niche_id='ci-fixture-welders';name='CI FIXTURE · Pipe welders';category='trade';audience='Union pipe welders';score_total=7.1;score_confidence=60;concept_count=0;research_summary='CI fixture summary (not market data).';dimensions=[pscustomobject]@{demand=7.0}}
    return [pscustomobject]@{ok=$true;contract='forge.discover_snapshot.v1';stats=[pscustomobject]@{niches=2;research_notes=2;active_sources=1;concepts=3};niches=@($n1,$n2)
        notes=@([pscustomobject]@{id='ci-note-1';niche_id='ci-fixture-nurses';topic='Shift humor';conclusion='CI fixture note linked to nurses.'},[pscustomobject]@{id='ci-note-2';topic='Unlinked';conclusion='CI fixture note without niche link.'})
        sources=@([pscustomobject]@{id='ci-src';name='CI fixture source';source_class='fixture'})}
}
function Invoke-ForgeApi([string]$Action,[hashtable]$Payload=@{}) { $script:Ci.api += $Action; if($Action -eq 'discover_snapshot'){ return (Get-CiFixture) }; throw ('CI: no backend for '+$Action) }

function Ci-Flush { $Window.UpdateLayout(); [Windows.Threading.Dispatcher]::CurrentDispatcher.Invoke([Action]{}, [Windows.Threading.DispatcherPriority]::Background) }
function Ci-Click($Button,[string]$Label) {
    if($null -eq $Button){ throw ('CI: missing control '+$Label) }
    if(-not $Button.IsEnabled){ throw ('CI: control is disabled, cannot click: '+$Label) }
    $Button.RaiseEvent((New-Object System.Windows.RoutedEventArgs ([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent)))
    Ci-Flush
}
function Ci-Shot([string]$Name) {
    try {
        Ci-Flush
        $w=[int][Math]::Max(1,$Window.ActualWidth); $h=[int][Math]::Max(1,$Window.ActualHeight)
        $rtb=New-Object System.Windows.Media.Imaging.RenderTargetBitmap($w,$h,96,96,[System.Windows.Media.PixelFormats]::Pbgra32)
        $rtb.Render($Window)
        $enc=New-Object System.Windows.Media.Imaging.PngBitmapEncoder; $enc.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($rtb))
        $path=Join-Path $env:FORGE_CI_OUT ($script:Ci.phase+'-'+$Name+'.png'); $fs=[IO.File]::Create($path); try{$enc.Save($fs)}finally{$fs.Close()}
        $script:Ci.screenshots += (Split-Path $path -Leaf)
    } catch { $script:Ci.errors += ('screenshot '+$Name+': '+$_.Exception.Message) }
}
function Ci-SelectedTabKey { if($null -eq $MainTabs.SelectedItem){return ''}; return (Get-MainTabKey $MainTabs.SelectedItem) }
function Ci-RevealApp {
    # Equivalent of a connected shell without a backend session: no capabilities, so live editing is read-only.
    $script:OwnerKey='ci-fixture-no-network'; $script:Session=$null; $script:ConnectionState='Connected'; $script:OfflineMode=$false; $script:OfflineSnapshotMode=$false
    $LoginGrid.Visibility='Collapsed'; $AppGrid.Visibility='Visible'
    $script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue @(Read-QueueSnapshotFile $script:EmbeddedIdeasPath))); Apply-Filter
    Ci-Flush
}
function Ci-Finish {
    try { [IO.File]::WriteAllText($env:FORGE_CI_RESULT,($script:Ci | ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false))) } catch {}
    $script:Dirty=$false; $script:PublicationDirty=$false
    $null=$Window.Dispatcher.BeginInvoke([Action]{ $Window.Close() })
}

$script:CiWatchdog=New-Object System.Windows.Threading.DispatcherTimer
$script:CiWatchdog.Interval=[TimeSpan]::FromSeconds(150)
$script:CiWatchdog.Add_Tick({ $script:CiWatchdog.Stop(); $script:Ci.fatal='watchdog timeout'; Ci-Finish })
$script:CiWatchdog.Start()

$Window.Add_ContentRendered({
    try {
        Ci-RevealApp
        Ci-Check 'window_rendered' ($Window.IsVisible -and $AppGrid.Visibility -eq 'Visible')
        Ci-Check 'app_version_reported' ($script:AppVersion -like '2.*') $script:AppVersion
        if($script:Ci.phase -eq 'create'){
            # Discover renders the (fixture) live snapshot through the real Load-DiscoverSnapshot code path
            Ci-Click $NavDiscoverButton 'NavDiscoverButton'
            Ci-Check 'discover_visible' ($DiscoverLandingScroll.Visibility -eq 'Visible')
            Ci-Check 'discover_two_niches' ($DiscoverNicheList.Items.Count -eq 2) $DiscoverNicheList.Items.Count
            Ci-Check 'discover_first_selected' ($DiscoverNicheList.SelectedIndex -eq 0 -and $DiscoverDetailName.Text -eq 'CI FIXTURE · Night-shift nurses') $DiscoverDetailName.Text
            Ci-Check 'create_button_enabled' ([bool]$DiscoverCreateDraftButton.IsEnabled)
            Ci-Check 'create_button_label_en' ([string]$DiscoverCreateDraftButton.Content -eq 'Create concept draft') $DiscoverCreateDraftButton.Content
            Ci-Check 'status_bar_not_stuck_working' ($StatusText.Text -notlike 'Working*') $StatusText.Text
            Ci-Shot '01-discover'
            # Create the draft with a real button click
            Ci-Click $DiscoverCreateDraftButton 'DiscoverCreateDraftButton'
            Ci-Check 'navigated_to_ideas' ($script:ProductSection -eq 'ideas' -and $DiscoverLandingScroll.Visibility -eq 'Collapsed' -and $MainTabs.Visibility -eq 'Visible') $script:ProductSection
            Ci-Check 'draft_is_current' ((Test-CurrentIsResearchDraft) -and $ConceptTitle.Text -eq 'CI FIXTURE · Night-shift nurses') $ConceptTitle.Text
            Ci-Check 'overview_tab_selected' ((Ci-SelectedTabKey) -eq 'overview') (Ci-SelectedTabKey)
            Ci-Check 'overview_status_research_draft' ($OverviewStatus.Text -eq 'Research draft') $OverviewStatus.Text
            Ci-Check 'overview_flags_missing_hook' ($OverviewNext.Text -like '*hook*') $OverviewNext.Text
            Ci-Check 'meta_says_local_not_server' ($ConceptMeta.Text -like '*not on the server*') $ConceptMeta.Text
            $inList=$false; foreach($i in @($ConceptList.Items)){ if([bool](Get-PropertyValue $i 'is_local_draft')){$inList=$true} }
            Ci-Check 'draft_in_ideas_list' $inList
            Ci-Check 'owner_buttons_enabled' ($OwnerKeepButton.IsEnabled -and $OwnerEditDecisionButton.IsEnabled -and $OwnerRegenButton.IsEnabled -and $OwnerSkipButton.IsEnabled)
            Ci-Check 'generate_disabled_for_draft' (-not $GenerateButton.IsEnabled)
            Ci-Shot '02-draft-overview'
            # Owner review: KEEP
            Ci-Click $OwnerKeepButton 'OwnerKeepButton'
            Ci-Check 'keep_selected' ([string]$OwnerKeepButton.FontWeight -eq 'Bold' -and $OwnerDecisionStatusText.Text -like '*KEEP*') $OwnerDecisionStatusText.Text
            Ci-Shot '03-keep'
            # Edit -> save new local revision (session has no server edit capability; drafts are still editable)
            Select-MainTab 'Edit'; Update-MainTabUi; Ci-Flush
            Ci-Check 'edit_tab_open' ((Ci-SelectedTabKey) -eq 'edit')
            Ci-Check 'edit_boxes_writable' (-not $HookBox.IsReadOnly -and -not $VisualBox.IsReadOnly)
            $HookBox.Text='CI hook: Running on caffeine and charting'; $VisualBox.Text='CI visual: bold typographic stack with a coffee cup'; Ci-Flush
            Ci-Check 'save_enabled_after_typing' ([bool]$SaveButton.IsEnabled -and $SaveButton.Visibility -eq 'Visible')
            Ci-Shot '04-edit'
            Ci-Click $SaveButton 'SaveButton'
            Ci-Check 'saved_revision_2' ($ConceptMeta.Text -like '*revision 2*') $ConceptMeta.Text
            Ci-Check 'decision_reset_after_edit' ($OwnerDecisionStatusText.Text -eq 'No decision yet') $OwnerDecisionStatusText.Text
            Ci-Check 'overview_shows_new_hook' ($OverviewHook.Text -eq 'CI hook: Running on caffeine and charting') $OverviewHook.Text
            Ci-Click $OwnerKeepButton 'OwnerKeepButton (rev 2)'
            Ci-Check 'keep_on_revision_2' ([string]$OwnerKeepButton.FontWeight -eq 'Bold')
            Ci-Shot '05-revision2-keep'
            # Artwork: no-dispatch brief only
            Ci-Click $NavArtworkButton 'NavArtworkButton'
            Ci-Check 'artwork_tab_selected' ((Ci-SelectedTabKey) -eq 'visuals') (Ci-SelectedTabKey)
            Ci-Check 'no_stale_variants' ($VariantList.Items.Count -eq 0) $VariantList.Items.Count
            Ci-Check 'generate_still_disabled' (-not $GenerateButton.IsEnabled)
            Ci-Click $LocalExportBriefButton 'LocalExportBriefButton'
            $briefDir=Join-Path $script:LocalCoreExportRoot (Get-LocalCoreSafeKey ([string]$script:Current.concept.concept_key))
            $briefs=@(Get-ChildItem -LiteralPath $briefDir -Filter 'generation-brief-*.json' -ErrorAction SilentlyContinue)
            $brief=$null; if($briefs.Count){$brief=Get-Content -LiteralPath $briefs[0].FullName -Raw -Encoding UTF8 | ConvertFrom-Json}
            Ci-Check 'brief_exported_no_dispatch' ($null -ne $brief -and -not [bool]$brief.external_generation_authorized -and [string]$brief.source_revision_id -eq [string]$script:Current.concept.current_revision_id)
            Ci-Shot '06-artwork'
            $before=$script:Ci.errors.Count; Queue-Generation
            Ci-Check 'generate_handler_blocks_draft' ($script:Ci.errors.Count -eq $before+1 -and $script:Ci.errors[-1] -like 'Research drafts cannot be generated*')
            # Portfolio pipeline board
            Ci-Click $NavPortfolioButton 'NavPortfolioButton'
            Ci-Check 'portfolio_visible' ($PortfolioLandingScroll.Visibility -eq 'Visible')
            Ci-Check 'portfolio_uses_full_width' ($QueueColumn.ActualWidth -lt 1 -and $PortfolioLandingScroll.ActualWidth -gt ($Window.ActualWidth*0.85)) ([string][int]$QueueColumn.ActualWidth+' / '+[string][int]$PortfolioLandingScroll.ActualWidth+' of '+[string][int]$Window.ActualWidth)
            $pipeItems=@($PortfolioPipelineList.Items); $mine=@($pipeItems | Where-Object { [string]$_.concept_key -eq [string]$script:Current.concept.concept_key })
            Ci-Check 'portfolio_lists_draft_keep' ($mine.Count -eq 1 -and [string]$mine[0].stage -eq 'keep_no_artwork' -and [string]$mine[0].stage_label -eq 'KEEP · no artwork') $(if($mine.Count){[string]$mine[0].stage_label}else{'missing'})
            Ci-Check 'portfolio_keep_first' ($pipeItems.Count -gt 1 -and [string]$pipeItems[0].concept_key -eq [string]$script:Current.concept.concept_key) $pipeItems.Count
            Ci-Check 'portfolio_counts' ($PipeKeepValue.Text -eq '1' -and [int]$PipeUndecidedValue.Text -ge 1 -and $PipePublishedValue.Text -eq '0') ($PipeUndecidedValue.Text+'/'+$PipeKeepValue.Text+'/'+$PipePublishedValue.Text)
            Ci-Check 'portfolio_niche_line' ($PortfolioNicheText.Text -like '*Night-shift nurses: KEEP 1*') $PortfolioNicheText.Text
            Ci-Shot '06b-portfolio'
            $draftKey=[string]$script:Current.concept.concept_key
            $PortfolioPipelineList.SelectedItem=$mine[0]; Ci-Flush
            Ci-Check 'portfolio_click_opens_idea' ($script:ProductSection -eq 'ideas' -and [string]$script:Current.concept.concept_key -eq $draftKey -and $MainTabs.Visibility -eq 'Visible') $script:ProductSection
            # Russian UI
            Ci-Click $HeaderLangRu 'HeaderLangRu'
            Ci-Check 'ru_draft_overview_rerendered' ($OverviewStatus.Text -eq 'Черновик исследования' -and $OverviewHook.Text -eq 'CI hook: Running on caffeine and charting') ($OverviewStatus.Text+' | '+$OverviewHook.Text)
            Ci-Shot '07a-draft-ru'
            Ci-Click $NavDiscoverButton 'NavDiscoverButton (ru)'
            Ci-Check 'ru_create_button_label' ([string]$DiscoverCreateDraftButton.Content -eq 'Создать черновик концепта') $DiscoverCreateDraftButton.Content
            Ci-Check 'ru_discover_numbers_kept' ($DiscoverNichesValue.Text -eq '2' -and $DiscoverConceptsValue.Text -eq '3') ($DiscoverNichesValue.Text+'/'+$DiscoverConceptsValue.Text)
            Ci-Check 'ru_discover_selection_kept' ($DiscoverDetailName.Text -eq 'CI FIXTURE · Night-shift nurses') $DiscoverDetailName.Text
            Ci-Check 'ru_discover_status_localized' ($DiscoverStatusText.Text -notlike 'Live research*') $DiscoverStatusText.Text
            Ci-Shot '07-discover-ru'
        } else {
            # Restart: a fresh process with the same LocalCore state
            $draft=$null; foreach($i in @($ConceptList.Items)){ if([bool](Get-PropertyValue $i 'is_local_draft')){$draft=$i} }
            Ci-Check 'draft_listed_after_restart' ($null -ne $draft)
            Ci-Check 'locale_ru_persisted' ($script:Locale -eq 'ru') $script:Locale
            $ConceptList.SelectedItem=$draft; Ci-Flush
            Ci-Check 'draft_opened_by_list_selection' ((Test-CurrentIsResearchDraft) -and $ConceptTitle.Text -eq 'CI FIXTURE · Night-shift nurses') $ConceptTitle.Text
            Ci-Check 'revision_2_after_restart' ([int]$script:Current.concept.current_revision_no -eq 2)
            Ci-Check 'hook_persisted' ($OverviewHook.Text -eq 'CI hook: Running on caffeine and charting') $OverviewHook.Text
            Ci-Check 'keep_persisted_after_restart' ([string]$OwnerKeepButton.FontWeight -eq 'Bold' -and $OwnerKeepButton.IsEnabled)
            Ci-Check 'ru_status_after_restart' ($OverviewStatus.Text -eq 'Черновик исследования') $OverviewStatus.Text
            Ci-Shot '08-after-restart'
            Ci-Click $NavPortfolioButton 'NavPortfolioButton (restart)'
            $mine=@(@($PortfolioPipelineList.Items) | Where-Object { [bool](Get-PropertyValue $_.queue_item 'is_local_draft') })
            Ci-Check 'portfolio_after_restart_ru' ($mine.Count -eq 1 -and [string]$mine[0].stage_label -eq 'ОСТАВИТЬ · нет макета' -and $PortfolioPipelineTitle.Text -eq 'Конвейер') $(if($mine.Count){[string]$mine[0].stage_label}else{'missing'})
            Ci-Shot '09-portfolio-ru'
        }
        Ci-Check 'only_discover_snapshot_api' (@($script:Ci.api | Where-Object { $_ -ne 'discover_snapshot' }).Count -eq 0) (($script:Ci.api) -join ',')
        Ci-Check 'no_network' ($script:Ci.network -eq 0)
        Ci-Check 'no_unexpected_errors' (@($script:Ci.errors | Where-Object { $_ -notlike 'Research drafts cannot be generated*' }).Count -eq 0) (($script:Ci.errors) -join ' | ')
    } catch {
        $script:Ci.fatal=($_.Exception.Message+' @ '+$_.InvocationInfo.PositionMessage)
        Ci-Shot 'zz-failure'
    } finally { $script:CiWatchdog.Stop(); Ci-Finish }
})

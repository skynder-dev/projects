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
    $n1=[pscustomobject]@{niche_key='ci-fixture-nurses';status='candidate';score_coverage=0.6;name='CI FIXTURE · Night-shift nurses';category='profession';audience='ICU and ER nurses on night rotation';score_total=8.4;score_confidence=72;concept_count=3;research_summary='CI fixture summary (not market data): recurring humor about night shifts and coffee.';dimensions=[pscustomobject]@{demand=8.1;competition=6.2;evergreen=9.0}}
    $n2=[pscustomobject]@{niche_key='ci-fixture-welders';status='candidate';score_coverage=0.4;name='CI FIXTURE · Pipe welders';category='trade';audience='Union pipe welders';score_total=7.1;score_confidence=60;concept_count=0;research_summary='CI fixture summary (not market data).';dimensions=[pscustomobject]@{demand=7.0}}
    return [pscustomobject]@{ok=$true;contract='forge.discover_snapshot.v1';stats=[pscustomobject]@{niches=2;research_notes=2;active_sources=1;concepts=3};niches=@($n1,$n2)
        notes=@([pscustomobject]@{id='ci-note-1';topic='Shift humor';conclusion='CI fixture note (live notes carry no niche link).';confidence=0.7;valid_as_of='2026-10-01'},[pscustomobject]@{id='ci-note-2';topic='Unlinked';conclusion='CI fixture note.';confidence=0.5;valid_as_of='2026-09-01'})
        sources=@([pscustomobject]@{name='CI fixture source';source_class='fixture';url='https://example.invalid/ci';jurisdiction='US';authority_level=1;last_checked_at='2026-10-01';active=$true})}
}
function Invoke-ForgeApi([string]$Action,[hashtable]$Payload=@{}) {
    $script:Ci.api += $Action
    if($script:Ci.phase -eq 'offline'){ throw 'HTTP 503 Service Unavailable (CI: backend is down in the offline phase)' }
    if($Action -eq 'discover_snapshot'){ return (Get-CiFixture) }; throw ('CI: no backend for '+$Action)
}

function Ci-Flush { $Window.UpdateLayout(); [Windows.Threading.Dispatcher]::CurrentDispatcher.Invoke([Action]{}, [Windows.Threading.DispatcherPriority]::Background) }
function Ci-Click($Button,[string]$Label) {
    if($null -eq $Button){ throw ('CI: missing control '+$Label) }
    if(-not $Button.IsEnabled){ throw ('CI: control is disabled, cannot click: '+$Label) }
    $Button.RaiseEvent((New-Object System.Windows.RoutedEventArgs ([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent)))
    Ci-Flush
}
function Ci-Shot([string]$Name,$Target=$null) {
    try {
        Ci-Flush
        if($null -eq $Target){$Target=$Window}
        $w=[int][Math]::Max(1,$Target.ActualWidth); $h=[int][Math]::Max(1,$Target.ActualHeight)
        $rtb=New-Object System.Windows.Media.Imaging.RenderTargetBitmap($w,$h,96,96,[System.Windows.Media.PixelFormats]::Pbgra32)
        $rtb.Render($Target)
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

# ---------- offline phase: crash hunt ----------
# Every visible, enabled, named button in every section and tab is clicked with the backend down.
# A crash = an exception escaping a click handler (in the real app that ends the window). Show-Error is fine.
$script:CiCrashes=@(); $script:CiClicked=@(); $script:CiClickStart=$null
function Ci-Try([string]$What,[scriptblock]$Do) {
    try { & $Do; Ci-Flush } catch { $script:CiCrashes += ($What+' => '+$_.Exception.Message+' @ '+[IO.Path]::GetFileName([string]$_.InvocationInfo.ScriptName)+':'+$_.InvocationInfo.ScriptLineNumber) }
}
function Ci-FindButtons($Root) {
    $out=New-Object System.Collections.Generic.List[object]; $stack=New-Object System.Collections.Stack; $stack.Push($Root)
    while($stack.Count -gt 0){
        $n=$stack.Pop()
        if($n -is [System.Windows.Controls.Button] -and -not [string]::IsNullOrWhiteSpace($n.Name)){ $out.Add($n) }
        $c=0; try{ $c=[System.Windows.Media.VisualTreeHelper]::GetChildrenCount($n) }catch{}
        for($i=$c-1;$i -ge 0;$i--){ $stack.Push([System.Windows.Media.VisualTreeHelper]::GetChild($n,$i)) }
    }
    return $out
}
$script:CiDenyButtons=@('ForgetButton','ConnectButton','HomeButton')
# Window-level buttons (they reset the open idea or open the side panel): clicked only in the final, idea-free pass.
$script:CiGlobalButtons=@('AboutButton','RefreshButton','BackendRetryButton','UtilityCloseTopButton','UtilityCloseButton','DiagnosticsButton','UtilityOpenLogButton')
function Ci-ClickAll([string]$Where,[scriptblock]$Return,[bool]$IncludeGlobal=$false) {
    $seen=@{}
    foreach($b in @(Ci-FindButtons $Window)){
        if(([DateTime]::UtcNow-$script:CiClickStart).TotalSeconds -gt 230){ return }
        $name=[string]$b.Name; if($seen.ContainsKey($name) -or $script:CiDenyButtons -contains $name -or $name -like 'Nav*'){continue}; $seen[$name]=$true
        if(-not $IncludeGlobal -and $script:CiGlobalButtons -contains $name){continue}
        if(-not $b.IsVisible -or -not $b.IsEnabled){continue}
        $script:CiClicked += ($Where+':'+$name)
        Ci-Try ($Where+' / '+$name) { $b.RaiseEvent((New-Object System.Windows.RoutedEventArgs ([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent))) }
        if($null -ne $Return){ Ci-Try ($Where+' / return after '+$name) $Return }
    }
}
function Ci-StubModalEntryPoints {
    # These open file pickers, modal windows, Explorer/Notepad or a blocking MessageBox; their file-processing parts are covered in other phases.
    # Win32 file pickers, Explorer/Notepad and blocking MessageBoxes cannot be answered from here: stub those entry points only.
    foreach($n in @('Import-AmazonPrintProfileFile','Open-LocalChecksFolder','Open-DiagnosticLogSafe','Import-LocalArtwork','Import-LocalCheckEvidence','Import-LocalPublicationReceipt','Import-LocalSalesCsv','Queue-Generation','Save-PublicationMetadata')){
        Set-Item -Path ('function:script:'+$n) -Value ([scriptblock]::Create("`$script:Ci.confirms += 'modal stub: $n'"))
    }
    # WPF dialogs (Confirm checks, Amazon profile) run for real: a timer presses their OK button (empty form -> validation text), then closes them.
    $script:CiDialogsAnswered=@()
    $script:CiDialogTimer=New-Object System.Windows.Threading.DispatcherTimer; $script:CiDialogTimer.Interval=[TimeSpan]::FromMilliseconds(250)
    $script:CiDialogTimer.Add_Tick({
        foreach($dw in @($Window.OwnedWindows)){
            if(-not $dw.IsVisible){continue}
            try{
                $ok=$dw.FindName('OkButton'); if($null -ne $ok){ $ok.RaiseEvent((New-Object System.Windows.RoutedEventArgs ([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent))) }
                $et=$dw.FindName('ErrorText'); $script:CiDialogsAnswered += ([string]$dw.Title+' => '+$(if($et){[string]$et.Text}else{''}))
                if($dw.IsVisible){ $dw.Close() }
            }catch{ $script:CiCrashes += ('dialog '+[string]$dw.Title+' => '+$_.Exception.Message) }
        }
    })
    $script:CiDialogTimer.Start()
}

# ---------- layout phase: three window widths, every section, clipped text detection ----------
function Ci-IsInsideListItem($El) {
    $p=$El; for($i=0;$i -lt 40 -and $null -ne $p;$i++){ if($p -is [System.Windows.Controls.ListBoxItem] -or $p -is [System.Windows.Controls.ComboBox]){ return $true }; try{ $p=[System.Windows.Media.VisualTreeHelper]::GetParent($p) }catch{ return $false } }
    return $false
}
function Ci-FindClippedText {
    # A single-line TextBlock whose text needs more width than it has is cut off (with or without an ellipsis).
    $out=New-Object System.Collections.Generic.List[string]; $stack=New-Object System.Collections.Stack; $stack.Push($Window)
    $dpi=1.0; try{ $dpi=[System.Windows.Media.VisualTreeHelper]::GetDpi($Window).PixelsPerDip }catch{}
    while($stack.Count -gt 0){
        $n=$stack.Pop()
        if($n -is [System.Windows.UIElement] -and -not $n.IsVisible){ continue }
        if($n -is [System.Windows.Controls.TextBlock] -and $n.TextWrapping -eq 'NoWrap' -and -not [string]::IsNullOrWhiteSpace($n.Text) -and $n.ActualWidth -gt 0 -and -not (Ci-IsInsideListItem $n)){
            try{
                $tf=New-Object System.Windows.Media.Typeface($n.FontFamily,$n.FontStyle,$n.FontWeight,$n.FontStretch)
                $ft=New-Object System.Windows.Media.FormattedText(($n.Text -split "`n")[0],[Globalization.CultureInfo]::CurrentUICulture,$n.FlowDirection,$tf,$n.FontSize,[System.Windows.Media.Brushes]::Black,$dpi)
                if($ft.WidthIncludingTrailingWhitespace -gt ($n.ActualWidth+1.5)){ $nm=if($n.Name){$n.Name}else{'"'+(($n.Text -split "`n")[0]).Substring(0,[Math]::Min(40,(($n.Text -split "`n")[0]).Length))+'"'}; [void]$out.Add(('{0} ({1:0}/{2:0})' -f $nm,$ft.WidthIncludingTrailingWhitespace,$n.ActualWidth)) }
            }catch{}
        }
        $c=0; try{ $c=[System.Windows.Media.VisualTreeHelper]::GetChildrenCount($n) }catch{}
        for($i=0;$i -lt $c;$i++){ $stack.Push([System.Windows.Media.VisualTreeHelper]::GetChild($n,$i)) }
    }
    return @($out | Sort-Object -Unique)
}

# ---------- untranslated UI text in RU ----------
function Ci-EnglishUiStrings {
    $set=New-Object 'System.Collections.Generic.HashSet[string]'
    foreach($v in @($script:UiText['en'].Values)){ $s=([string]$v).Trim(); if($s.Length -ge 3){ [void]$set.Add($s) } }
    foreach($b in @($script:StaticLocaleRegistry)){ $s=([string]$b.Source).Trim(); if($s.Length -ge 3){ [void]$set.Add($s) } }
    return ,$set
}
$script:CiBrandTexts=@('Merch Forge','MERCH FORGE','Amazon','Amazon Merch')
$script:CiDataControls=@('DiscoverDetailAudience','DiscoverDetailDimensions','DiscoverRecentText','DiscoverSourcesText','ConceptTitle','PerformanceLeadersText','DiscoverDetailName','DiscoverDetailMeta','DiscoverDetailSummary','OverviewHook','OverviewConcept','OverviewBuyer','OverviewWhy','OverviewDifferent','OverviewVisual','OverviewMeaning','AnalysisPurchase','AnalysisContext','AnalysisMeaning','GenerationBriefText','OverviewWarnings','LocalCoreStatusText')
function Ci-FindUntranslated($EnSet,[string]$Where) {
    $strict=New-Object System.Collections.Generic.List[string]; $loose=New-Object System.Collections.Generic.List[string]
    $stack=New-Object System.Collections.Stack; $stack.Push($Window)
    while($stack.Count -gt 0){
        $n=$stack.Pop()
        if($n -is [System.Windows.UIElement] -and -not $n.IsVisible){ continue }
        $txt=$null; $nm=''
        if($n -is [System.Windows.Controls.TextBlock]){ $txt=[string]$n.Text; $nm=[string]$n.Name }
        elseif($n -is [System.Windows.Controls.ContentControl] -and $n.Content -is [string]){ $txt=[string]$n.Content; $nm=[string]$n.Name }
        if($null -ne $txt){
            $tt=$txt.Trim()
            if($tt -and $tt -notmatch '[А-Яа-яЁё]' -and $tt -match '[A-Za-z]{3}' -and $script:CiBrandTexts -notcontains $tt){
                if($EnSet.Contains($tt)){ [void]$strict.Add($Where+': '+$(if($nm){$nm+'='}else{''})+$tt.Substring(0,[Math]::Min(70,$tt.Length))) }
                elseif(-not (Ci-IsInsideListItem $n) -and $script:CiDataControls -notcontains $nm -and @([regex]::Matches($tt,'[A-Za-z]{3,}')).Count -ge 3){ [void]$loose.Add($Where+': '+$(if($nm){$nm+'='}else{''})+$tt.Substring(0,[Math]::Min(70,$tt.Length))) }
            }
        }
        $c=0; try{ $c=[System.Windows.Media.VisualTreeHelper]::GetChildrenCount($n) }catch{}
        for($i=0;$i -lt $c;$i++){ $stack.Push([System.Windows.Media.VisualTreeHelper]::GetChild($n,$i)) }
    }
    return [pscustomobject]@{strict=@($strict);loose=@($loose)}
}

$script:CiWatchdog=New-Object System.Windows.Threading.DispatcherTimer
$script:CiWatchdog.Interval=[TimeSpan]::FromSeconds(360)
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
            Ci-Check 'portfolio_keep_shows_next_step' ([string]$mine[0].next_label -like '*Click to open: Artwork*') ([string]$mine[0].next_label)
            Ci-Check 'portfolio_click_opens_artwork' ($script:ProductSection -eq 'artwork' -and [string]$script:Current.concept.concept_key -eq $draftKey -and $MainTabs.Visibility -eq 'Visible' -and (Get-MainTabKey $MainTabs.SelectedItem) -eq 'visuals') ($script:ProductSection+' / '+(Get-MainTabKey $MainTabs.SelectedItem))
            Ci-Click $NavIdeasButton 'NavIdeasButton (back to idea)'
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
        } elseif($script:Ci.phase -eq 'package') {
            # Full local path on the draft from earlier phases: artwork -> exact accept -> Amazon profile -> listing -> checks -> READY package -> receipt -> sales
            $draft=$null; foreach($i in @($ConceptList.Items)){ if([bool](Get-PropertyValue $i 'is_local_draft')){$draft=$i} }
            $ConceptList.SelectedItem=$draft; Ci-Flush
            $key=[string]$script:Current.concept.concept_key
            Ci-Check 'pkg_draft_open' ((Test-CurrentIsResearchDraft) -and [int]$script:Current.concept.current_revision_no -eq 2) $key
            # 1) artwork import (the dialog's file-processing step) + exact accept through the real button
            Ci-Click $NavArtworkButton 'NavArtworkButton'
            $art=Join-Path $script:ModuleRoot '..\Data\SelfTest\mock-01.png'
            $null=Add-LocalArtworkFromPath ([IO.Path]::GetFullPath($art)) 'local-import' 'manual_artwork_bridge'; Refresh-LocalArtworkUi; Ci-Flush
            Ci-Check 'pkg_artwork_listed' ($VariantList.Items.Count -eq 1) $VariantList.Items.Count
            $VariantList.SelectedItem=$VariantList.Items[0]; Ci-Flush
            Ci-Click $LocalAcceptButton 'LocalAcceptButton'
            $lc=Get-LocalCoreConcept $key
            Ci-Check 'pkg_exact_accept' ($null -ne $lc.active_acceptance -and [string]$lc.active_acceptance.concept_revision_id -eq [string]$script:Current.concept.current_revision_id) ''
            Ci-Shot '10-accepted'
            Ci-Click $NavPortfolioButton 'NavPortfolioButton (accepted)'
            $row=@(@($PortfolioPipelineList.Items) | Where-Object { [string]$_.concept_key -eq $key })
            if($row.Count){ $PortfolioPipelineList.SelectedItem=$row[0]; Ci-Flush }
            Ci-Check 'portfolio_accepted_opens_checks' ($row.Count -eq 1 -and [string]$row[0].stage -eq 'artwork_accepted' -and $script:ProductSection -eq 'checks' -and (Get-MainTabKey $MainTabs.SelectedItem) -eq 'evidence' -and $ConceptTitle.Text -eq 'CI FIXTURE · Night-shift nurses') ($(if($row.Count){[string]$row[0].stage}else{'missing'})+' / '+$script:ProductSection+' / '+(Get-MainTabKey $MainTabs.SelectedItem))
            # 2) Amazon print profile through the in-app form (the standalone importer tool runs unchanged as a child process)
            Ci-Click $NavChecksButton 'NavChecksButton (profile)'
            Ci-Check 'prof_status_none_ru' ($AmazonProfileStatusText.Text -like 'Не импортирован*' -and [string]$AmazonProfileFormButton.Content -eq 'Заполнить Amazon-профиль…') ($AmazonProfileStatusText.Text+' | '+[string]$AmazonProfileFormButton.Content)
            # a stand-in "Amazon template" PNG (same canvas as the CI artwork, different bytes); the real artwork is refused as a template
            Add-Type -AssemblyName System.Drawing
            $tplPng=Join-Path $env:FORGE_CI_OUT 'ci-amazon-template.png'; $bmp=New-Object System.Drawing.Bitmap(1024,1024,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb); try{ $g=[System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::Transparent); $g.Dispose(); $bmp.Save($tplPng,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $bmp.Dispose() }
            $pd=New-AmazonProfileDialog; $pd.Show(); Ci-Flush
            Set-AmazonProfileDialogFile $pd ([IO.Path]::GetFullPath($art)); $pd.FindName('Days').Text='30'; $pd.FindName('Attest').IsChecked=$true; $pd.FindName('SourceRef').Text='https://merch.amazon.com/resource/Y28FFE5NLRYJG4V'; Ci-Flush
            $artAsTpl=Complete-AmazonProfileDialog $pd $false; Ci-Flush
            Ci-Check 'prof_refuses_artwork_as_template_ru' (-not $artAsTpl -and [string]$pd.FindName('ErrorText').Text -like 'Этот файл — один из ваших принятых макетов*') ([string]$pd.FindName('ErrorText').Text)
            $pd.FindName('Attest').IsChecked=$false; $pd.FindName('TemplateKey').Text=''
            Set-AmazonProfileDialogFile $pd $tplPng; Ci-Flush
            Ci-Check 'prof_png_size_autofilled' ($pd.FindName('Width').Text -eq '1024' -and $pd.FindName('Height').Text -eq '1024' -and $pd.FindName('FileSha').Text -like 'SHA-256 *' -and $pd.FindName('TemplateKey').Text -eq 'ci-amazon-template') ($pd.FindName('Width').Text+'x'+$pd.FindName('Height').Text+' '+$pd.FindName('TemplateKey').Text)
            $first=Complete-AmazonProfileDialog $pd $false; Ci-Flush
            Ci-Check 'prof_form_requires_attest_ru' (-not $first -and [string]$pd.FindName('ErrorText').Text -like 'Поставьте галочку*') ([string]$pd.FindName('ErrorText').Text)
            $pd.FindName('Attest').IsChecked=$true; Ci-Flush
            Ci-Shot '09b-amazon-profile-form' $pd
            $second=Complete-AmazonProfileDialog $pd $false; $att=$pd.Tag; $pd.Close(); Ci-Flush
            $ok=$false; if($second -and $null -ne $att){ $ok=Save-AmazonProfileAttestation $att }; Ci-Flush
            Ci-Check 'pkg_profile_imported' ($ok -and $null -ne (Get-LocalPolicyProfileBinding)) ($StatusText.Text+' | '+(($script:Ci.errors | Select-Object -Last 1)))
            Ci-Check 'prof_status_valid_ru' ($AmazonProfileStatusText.Text -like '1024 × 1024 пикс., 300 DPI · amazon.com_us / standard_tshirt · действует до *' -and $StatusText.Text -like 'Amazon-профиль печати сохранён*') ($AmazonProfileStatusText.Text+' | '+$StatusText.Text)
            Ci-Shot '09c-checks-profile'
            # 3) listing metadata through the Publication tab and its Save button
            Ci-Click $NavPublishButton 'NavPublishButton'
            $PublicationTitleBox.Text='Night Shift Nurse Coffee Fuel Funny ICU ER Nurse Gift'; $PublicationBrandBox.Text='CI Fixture Brand'; $PublicationBullet1Box.Text='Funny night shift nurse design for ICU and ER nurses.'; $PublicationBullet2Box.Text='Great gift for nurses who run on coffee.'; $PublicationDescriptionBox.Text='CI fixture listing.'; $PublicationKeywordsBox.Text='night shift nurse, icu nurse, er nurse'; $PublicationReasonBox.Text='ci'
            Ci-Flush
            Ci-Check 'pkg_save_listing_enabled' ([bool]$SavePublicationButton.IsEnabled)
            if($SavePublicationButton.IsEnabled){ Ci-Click $SavePublicationButton 'SavePublicationButton' } else { $null=Save-LocalPublicationMetadata }
            $lc=Get-LocalCoreConcept $key
            Ci-Check 'pkg_listing_saved' ($null -ne $lc.publication -and [string]$lc.publication.listing_title -like 'Night Shift Nurse*') ''
            Ci-Check 'pkg_print_check_pass_by_worker' ([string]$lc.checks.print.state -eq 'pass' -and [string]$lc.checks.print.source -eq 'trusted_local_check_worker') ([string]$lc.checks.print.state+' / '+[string]$lc.checks.print.note)
            # 4) owner confirms IP / policy / listing text through the in-app checklist form (writes v3 evidence, normal importer)
            $tplDir=Join-Path $script:LocalCoreExportRoot (Join-Path (Get-LocalCoreSafeKey $key) 'checks')
            Ci-Click $NavChecksButton 'NavChecksButton'
            $cl=@(Get-ChildItem -LiteralPath $tplDir -Filter 'check-evidence-*.CHECKLIST.txt' -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending)
            $clText=if($cl.Count){Get-Content -LiteralPath $cl[0].FullName -Raw -Encoding UTF8}else{''}
            Ci-Check 'chk_checklist_file_next_to_template' ($cl.Count -ge 1 -and $clText -like '*ЧЕК-ЛИСТ*' -and $clText -like '*tmsearch.uspto.gov*' -and $clText -like '*.template.json*') $(if($cl.Count){$cl[0].Name}else{'missing in '+$tplDir})
            Ci-Check 'chk_buttons_ru' ([string]$LocalConfirmChecksButton.Content -eq 'Подтвердить проверки…' -and [string]$LocalOpenChecksFolderButton.Content -eq 'Открыть папку проверок' -and $LocalConfirmChecksButton.IsVisible) ([string]$LocalConfirmChecksButton.Content+' | '+[string]$LocalOpenChecksFolderButton.Content)
            # A real local error in the RU UI must reach the owner as a readable Russian message
            $badPath=Join-Path $env:FORGE_CI_OUT 'ci-bad-evidence.json'; [IO.File]::WriteAllText($badPath,'{"schema":"forge.local_check_evidence.v0"}',(New-Object Text.UTF8Encoding($false)))
            $before=$script:Ci.errors.Count; Import-LocalCheckEvidenceFromPath $badPath
            $raw=if($script:Ci.errors.Count -gt $before){[string]$script:Ci.errors[-1]}else{''}
            $shown=if((Test-KnownUiMessage $raw)){Translate-UiMessage $raw}else{Translate-UiMessage (Get-HumanErrorMessage $raw)}
            Ci-Check 'msg_error_readable_ru' ($raw -eq 'Unsupported check evidence schema.' -and $shown -eq 'Неподдерживаемый формат файла подтверждений.') ($raw+' => '+$shown)
            $script:Ci.errors=@($script:Ci.errors | Select-Object -First $before)
            $dlg=New-ConfirmChecksDialog; $dlg.Show(); Ci-Flush
            foreach($n in @('ip','policy','metadata')){ $dlg.FindName('State_'+$n).SelectedIndex=1; $dlg.FindName('Ref_'+$n).Text='https://merch.amazon.com/resource/Y28FFE5NLRYJG4V'; $dlg.FindName('Note_'+$n).Text='CI fixture attestation (not a real legal or policy review).' }
            Ci-Flush
            $first=Complete-ConfirmChecksDialog $dlg $false; Ci-Flush
            Ci-Check 'chk_dialog_requires_confirm_ru' (-not $first -and [string]$dlg.FindName('ErrorText').Text -like 'Поставьте галочку*') ([string]$dlg.FindName('ErrorText').Text)
            $dlg.FindName('ConfirmBox').IsChecked=$true; Ci-Flush
            Ci-Shot '11a-confirm-checks-dialog' $dlg
            $second=Complete-ConfirmChecksDialog $dlg $false; $answers=$dlg.Tag; $dlg.Close(); Ci-Flush
            Ci-Check 'chk_dialog_accepts' ($second -and $null -ne $answers) ''
            $before=$script:Ci.errors.Count; $ok=$false; if($null -ne $answers){ $ok=Submit-OwnerCheckAnswers $answers.answers $answers.confirmed }; Ci-Flush
            Ci-Check 'chk_saved_status_ru' ($ok -and $StatusText.Text -like 'Проверки сохранены:*') $StatusText.Text
            Ci-Check 'chk_evidence_text_ru' ($AnalysisEvidence.Text -like 'IP · пройдено*' -and $AnalysisEvidence.Text -like '*Макет · пройдено*' -and $AnalysisEvidence.Text -like '*Текст карточки · пройдено*') ($AnalysisEvidence.Text.Substring(0,[Math]::Min(300,$AnalysisEvidence.Text.Length)))
            $lc=Get-LocalCoreConcept $key; $gate=Get-LocalCheckGateSnapshot $lc
            Ci-Check 'pkg_evidence_imported' ($script:Ci.errors.Count -eq $before) (($script:Ci.errors | Select-Object -Last 1))
            Ci-Check 'pkg_all_checks_ready' ([bool]$gate.all_ready) (($gate.checks | ConvertTo-Json -Depth 4 -Compress))
            Ci-Shot '11-checks'
            # 5) READY package through the real Build button
            Ci-Click $NavPublishButton 'NavPublishButton (build)'
            Ci-Check 'pkg_build_enabled' ([bool]$LocalBuildPackageButton.IsEnabled)
            if($LocalBuildPackageButton.IsEnabled){ Ci-Click $LocalBuildPackageButton 'LocalBuildPackageButton' } else { Build-LocalAmazonPackage }
            $lc=Get-LocalCoreConcept $key; $pk=@($lc.packages | Where-Object { [bool]$_.valid }) | Select-Object -Last 1
            Ci-Check 'pkg_ready_for_manual_upload' ($null -ne $pk -and [string]$pk.status -eq 'READY_FOR_MANUAL_UPLOAD' -and (Test-Path -LiteralPath ([string]$pk.path))) $(if($pk){[string]$pk.status}else{'no package'})
            Ci-Check 'pkg_status_bar_russian' ($StatusText.Text -like 'Локальный пакет для ручной загрузки создан. Статус: READY_FOR_MANUAL_UPLOAD*') $StatusText.Text
            Ci-Click $NavPortfolioButton 'NavPortfolioButton (package)'
            $row=@(@($PortfolioPipelineList.Items) | Where-Object { [string]$_.concept_key -eq $key })
            Ci-Check 'pkg_portfolio_package_ready' ($row.Count -eq 1 -and [string]$row[0].stage -eq 'package_ready' -and $PipePackageValue.Text -eq '1') $(if($row.Count){[string]$row[0].stage}else{'missing'})
            Ci-Shot '12-portfolio-package-ready'
            if($row.Count){ $PortfolioPipelineList.SelectedItem=$row[0]; Ci-Flush }
            Ci-Check 'portfolio_package_opens_publish' ($script:ProductSection -eq 'publish' -and (Get-MainTabKey $MainTabs.SelectedItem) -eq 'publication' -and [string]$row[0].next_label -like '*Нажмите, чтобы открыть: Публикация*') ($script:ProductSection+' / '+(Get-MainTabKey $MainTabs.SelectedItem)+' / '+[string]$row[0].next_label)
            # 6) publication receipt (owner records the manual upload) -> Published
            if($null -ne $pk){
                $rc=[ordered]@{schema='forge.local_publication_receipt.v3';concept_key=$key;package_sha256=[string]$pk.sha256;lineage_fingerprint=[string]$pk.acceptance_fingerprint;listing_hash=[string]$pk.listing_hash;preupload_gate_sha256=[string]$pk.preupload_gate_sha256;print_production_sha256=[string]$pk.print_production_sha256;channel='amazon_merch';marketplace=[string]$pk.marketplace;product_id='CI-ASIN-0001';published_at=[DateTime]::UtcNow.AddMinutes(-1).ToString('o');source='ci-owner-receipt';note='CI fixture receipt (nothing was uploaded).'}
                $rcPath=Join-Path $env:FORGE_CI_OUT 'ci-publication-receipt.json'; [IO.File]::WriteAllText($rcPath,($rc|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
                $before=$script:Ci.errors.Count; Import-LocalPublicationReceiptFromPath $rcPath; Update-LocalCoreBusinessSurfaces; Ci-Flush
                Ci-Check 'pkg_receipt_imported' ($script:Ci.errors.Count -eq $before) (($script:Ci.errors | Select-Object -Last 1))
                Ci-Click $NavPortfolioButton 'NavPortfolioButton (published)'
                $row=@(@($PortfolioPipelineList.Items) | Where-Object { [string]$_.concept_key -eq $key })
                Ci-Check 'pkg_portfolio_published' ($row.Count -eq 1 -and [string]$row[0].stage -eq 'published' -and $PipePublishedValue.Text -eq '1' -and $PortfolioProductsValue.Text -eq '1') ($PipePublishedValue.Text+' / '+$PortfolioProductsValue.Text)
                Ci-Shot '13-portfolio-published'
                # 7) sales CSV linked to the verified product id -> Performance numbers
                $csvPath=Join-Path $env:FORGE_CI_OUT 'ci-sales.csv'
                Set-Content -LiteralPath $csvPath -Encoding UTF8 -Value @('date,asin,units,royalty',([DateTime]::UtcNow.AddDays(-2).ToString('yyyy-MM-dd')+',CI-ASIN-0001,3,4.50'),([DateTime]::UtcNow.AddDays(-20).ToString('yyyy-MM-dd')+',CI-ASIN-0001,2,3.00'),([DateTime]::UtcNow.AddDays(-3).ToString('yyyy-MM-dd')+',UNKNOWN-ASIN,9,9.99'))
                $before=$script:Ci.errors.Count; Import-LocalSalesCsvFromPath $csvPath; Ci-Flush
                Ci-Check 'pkg_sales_imported' ($script:Ci.errors.Count -eq $before) (($script:Ci.errors | Select-Object -Last 1))
                Ci-Check 'pkg_sales_status_russian' ($StatusText.Text -like 'Импортировано строк: 3;*') $StatusText.Text
                Ci-Click $NavPerformanceButton 'NavPerformanceButton'
                Ci-Check 'pkg_performance_linked_only' ($PerfSales7Value.Text -eq '3' -and $PerfSales30Value.Text -eq '5' -and $PerfRoyalties30Value.Text -eq '$7.50') ($PerfSales7Value.Text+' / '+$PerfSales30Value.Text+' / '+$PerfRoyalties30Value.Text)
                Ci-Check 'pkg_performance_text_shows_amount' ($PerformanceEmpty.Text -like '*$7.50*' -and $PerformanceEmpty.Text -like '*роялти*') $PerformanceEmpty.Text
                Ci-Check 'pkg_home_text_shows_amounts' ($HomePerformanceBody.Text -like '*$4.50*' -and $HomePerformanceBody.Text -like '*$7.50*') $HomePerformanceBody.Text
                Ci-Check 'perf_leaders_list_product' ($PerformanceLeadersText.Text -like '*CI-ASIN-0001*' -and $PerformanceLeadersText.Text -like '*30 дн.: 5 шт., $7.50*') $PerformanceLeadersText.Text
                Ci-Check 'perf_attention_unknown_asin' ($PerformanceAttentionText.Text -like '*UNKNOWN-ASIN*' -and $PerformanceAttentionText.Text -like '*неизвестным ID*' -and $PerformanceAttentionText.Text -notlike '*CI-ASIN-0001*') $PerformanceAttentionText.Text
                Ci-Check 'home_attention_count' ($HomeMetricAttentionValue.Text -eq '1') $HomeMetricAttentionValue.Text
                Ci-Check 'home_hints_name_the_source_ru' ($HomeMetricSalesHint.Text -eq 'По импортированным продажам ваших товаров' -and $HomeMetricPublishedHint.Text -eq 'По импортированным квитанциям публикации') ($HomeMetricSalesHint.Text+' | '+$HomeMetricPublishedHint.Text)
                Ci-Shot '14-performance'
                # 8) data copy: save -> lose a draft -> restore -> everything (incl. the published product) is back
                Ci-Click $NavHomeButton 'NavHomeButton (data copy)'
                Ci-Check 'backup_buttons_ru' ([string]$DataBackupButton.Content -eq 'Сохранить копию…' -and [string]$DataRestoreButton.Content -eq 'Восстановить из копии…' -and $DataBackupButton.IsVisible) ([string]$DataBackupButton.Content+' | '+[string]$DataRestoreButton.Content)
                $bkz=Join-Path $env:FORGE_CI_OUT 'ci-data-copy.zip'; $bk=New-ForgeDataBackup $script:StateRoot $bkz
                $s0=Read-LocalCoreState; $nDrafts=@(Get-ResearchDraftList $s0).Count; Set-ResearchDraftList $s0 @(); Write-LocalCoreState $s0
                $before=$script:Ci.errors.Count; $okR=Complete-DataBackupRestore $bkz; Ci-Flush
                $s1=Read-LocalCoreState
                Ci-Check 'backup_restore_roundtrip' ($okR -and $script:Ci.errors.Count -eq $before -and @(Get-ResearchDraftList $s1).Count -eq $nDrafts -and $nDrafts -ge 1 -and $StatusText.Text -like 'Восстановлено файлов из копии:*') ([string]$bk.file_count+' files; drafts '+$nDrafts+' -> '+@(Get-ResearchDraftList $s1).Count+'; '+$StatusText.Text)
                $ins=Get-ForgePerformanceInsights $s1
                Ci-Check 'backup_restore_keeps_verified_product' (@($ins.leaders).Count -eq 1 -and [string]@($ins.leaders)[0].product_id -eq 'CI-ASIN-0001') (@($ins.leaders).Count)
                Ci-Shot '15-home-data-copy'
            }
        } elseif($script:Ci.phase -eq 'layout') {
            $draft=$null; foreach($i in @($ConceptList.Items)){ if([bool](Get-PropertyValue $i 'is_local_draft')){$draft=$i} }
            $ConceptList.SelectedItem=$draft; Ci-Flush
            $clip=[ordered]@{}; $reached=@()
            $screen=[System.Windows.SystemParameters]::PrimaryScreenWidth
            foreach($w in @(1024,1366,1920)){
                $Window.WindowState='Normal'; $Window.Left=0; $Window.Top=0; $Window.Width=$w; $Window.Height=$(if($w -ge 1920){1040}elseif($w -ge 1366){768}else{720}); Ci-Flush; Update-ResponsiveLayout; Ci-Flush
                $reached+=('{0}->{1:0}' -f $w,$Window.ActualWidth)
                foreach($sec in @('home','discover','ideas','artwork','checks','publish','portfolio','performance')){
                    Show-ProductSection $sec; Ci-Flush
                    $found=@(Ci-FindClippedText)
                    if($found.Count){ $clip[('{0}-{1}' -f $w,$sec)]=($found -join ', ') }
                    Ci-Shot ('w{0}-{1}' -f $w,$sec)
                }
            }
            $script:Ci['clipped']=$clip
            # RU: no English UI text left (product data excluded)
            if($script:Locale -ne 'ru'){ Ci-Click $HeaderLangRu 'HeaderLangRu (layout)' }
            $Window.Width=1366; $Window.Height=768; Ci-Flush
            $en=Ci-EnglishUiStrings; $strictAll=@(); $looseAll=@()
            foreach($sec in @('home','discover','portfolio','performance')){ Show-ProductSection $sec; Ci-Flush; $u=Ci-FindUntranslated $en $sec; $strictAll+=$u.strict; $looseAll+=$u.loose }
            foreach($sec in @('ideas','artwork','checks','publish')){
                Show-ProductSection $sec; Ci-Flush
                foreach($tab in @($MainTabs.Items)){
                    if(-not ($tab -is [System.Windows.Controls.TabItem]) -or -not $tab.IsEnabled -or $tab.Visibility -ne 'Visible' -or $MainTabs.Visibility -ne 'Visible'){continue}
                    $MainTabs.SelectedItem=$tab; Ci-Flush; $u=Ci-FindUntranslated $en ($sec+'#'+(Get-MainTabKey $tab)); $strictAll+=$u.strict; $looseAll+=$u.loose
                }
            }
            $strictAll=@($strictAll | Sort-Object -Unique); $looseAll=@($looseAll | Sort-Object -Unique)
            $script:Ci['untranslated_strict']=$strictAll; $script:Ci['untranslated_loose']=$looseAll
            Ci-Check 'ru_no_untranslated_ui_text' ($strictAll.Count -eq 0) ($strictAll -join ' || ')
            Ci-Check 'ru_no_english_sentences' ($looseAll.Count -eq 0) ((@($looseAll) | Select-Object -First 40) -join ' || ')
            Ci-Check 'layout_widths_reached' (@($reached | Where-Object { [int](($_ -split '->')[1]) -lt ([int](($_ -split '->')[0])-24) }).Count -eq 0) ('screen '+[string]$screen+'; '+($reached -join ', '))
            $wide=@($clip.Keys | Where-Object { $_ -notlike '1024-*' })
            Ci-Check 'layout_no_clipped_text_1366_1920' ($wide.Count -eq 0) ((@($wide | ForEach-Object { $_+': '+$clip[$_] })) -join ' || ')
            Ci-Check 'layout_clipped_text_1024_info' $true ((@($clip.Keys | Where-Object { $_ -like '1024-*' } | ForEach-Object { $_+': '+$clip[$_] })) -join ' || ')
        } elseif($script:Ci.phase -eq 'offline') {
            Ci-StubModalEntryPoints
            Enter-OfflineWorkbench 'HTTP 503 Service Unavailable (CI fixture: backend down)'; Ci-Flush
            Ci-Check 'offline_mode_on' ([bool]$script:OfflineMode -and $BackendBanner.Visibility -eq 'Visible' -and $HomeLandingScroll.Visibility -eq 'Visible') ([string]$script:OfflineMode)
            Ci-Shot '20-offline-home'
            $script:CiClickStart=[DateTime]::UtcNow
            Ci-Check 'offline_draft_listed' (@(@($ConceptList.Items) | Where-Object { [bool](Get-PropertyValue $_ 'is_local_draft') }).Count -ge 1) $ConceptList.Items.Count
            # 1) inside ideas: the research draft (full local path) and two offline snapshot ideas; every section and tab
            $items=@(@(@($ConceptList.Items) | Where-Object { [bool](Get-PropertyValue $_ 'is_local_draft') }) + @(@($ConceptList.Items) | Where-Object { -not [bool](Get-PropertyValue $_ 'is_local_draft') } | Select-Object -First 2))
            foreach($it in $items){
                $label=[string](Get-PropertyValue $it 'concept_key')
                Ci-Try ('open '+$label) { $ConceptList.SelectedItem=$null; Ci-Flush; $ConceptList.SelectedItem=$it }
                foreach($sec in @('ideas','artwork','checks','publish')){
                    $s=$sec; Ci-Try ('section '+$label+' '+$s) { Show-ProductSection $s }
                    $back=[scriptblock]::Create("if(`$script:ProductSection -ne '$s'){ Show-ProductSection '$s' }")
                    Ci-ClickAll ($label+'@'+$s) $back
                    foreach($tab in @($MainTabs.Items)){
                        if(-not ($tab -is [System.Windows.Controls.TabItem]) -or -not $tab.IsEnabled -or $tab.Visibility -ne 'Visible' -or $MainTabs.Visibility -ne 'Visible'){continue}
                        $tk=Get-MainTabKey $tab
                        Ci-Try ('tab '+$label+' '+$tk) { $MainTabs.SelectedItem=$tab }
                        Ci-ClickAll ($label+'@'+$s+'#'+$tk) $null
                    }
                }
            }
            # 2) every section without an idea, including the window-level buttons (Refresh / Retry / About / Diagnostics)
            foreach($sec in @('home','discover','ideas','artwork','checks','publish','portfolio','performance')){
                $nav=Get-Variable -Name ('Nav'+(Get-Culture).TextInfo.ToTitleCase($sec)+'Button') -ValueOnly -ErrorAction SilentlyContinue
                Ci-Try ('nav '+$sec) { Ci-Click $nav ('Nav '+$sec) }
                $s=$sec; Ci-ClickAll $sec ([scriptblock]::Create("if(`$script:ProductSection -ne '$s'){ Show-ProductSection '$s' }")) $true
            }
            Ci-Try 'portfolio rows' { Show-ProductSection 'portfolio'; foreach($row in @($PortfolioPipelineList.Items)){ $PortfolioPipelineList.SelectedItem=$row; Ci-Flush; Show-ProductSection 'portfolio' } }
            foreach($lang in @('Es','Ru','En')){ $lb=Get-Variable -Name ('HeaderLang'+$lang) -ValueOnly -ErrorAction SilentlyContinue; if($null -ne $lb){ Ci-Try ('lang '+$lang) { $lb.RaiseEvent((New-Object System.Windows.RoutedEventArgs ([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent))) } } }
            Ci-Try 'retry backend' { Ci-Click $BackendRetryButton 'BackendRetryButton' }
            Ci-Check 'offline_stays_offline_after_retry' ([bool]$script:OfflineMode) ([string]$script:ConnectionState)
            $distinct=@($script:CiClicked | ForEach-Object { ($_ -split ':')[-1] } | Sort-Object -Unique)
            Ci-Check 'offline_clicked_many' (@($script:CiClicked).Count -ge 60 -and $distinct.Count -ge 20) (([string]@($script:CiClicked).Count)+' clicks, '+[string]$distinct.Count+' distinct: '+($distinct -join ','))
            Ci-Check 'offline_no_crashes' (@($script:CiCrashes).Count -eq 0) ((@($script:CiCrashes) | Select-Object -First 12) -join ' || ')
            Ci-Check 'offline_real_dialogs_opened_and_validated' (@($script:CiDialogsAnswered | Where-Object { $_ -like '*=> ?*' }).Count -ge 1) ((@($script:CiDialogsAnswered) | Select-Object -First 6) -join ' || ')
            $script:Ci['clicked']=@($script:CiClicked); $script:Ci['crashes']=@($script:CiCrashes)
            Ci-Shot '21-offline-after-clicks'
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
        if($script:Ci.phase -ne 'offline'){ Ci-Check 'only_discover_snapshot_api' (@($script:Ci.api | Where-Object { $_ -ne 'discover_snapshot' }).Count -eq 0) (($script:Ci.api) -join ',') }
        Ci-Check 'no_network' ($script:Ci.network -eq 0)
        if($script:Ci.phase -ne 'offline'){ Ci-Check 'no_unexpected_errors' (@($script:Ci.errors | Where-Object { $_ -notlike 'Research drafts cannot be generated*' }).Count -eq 0) (($script:Ci.errors) -join ' | ') }
    } catch {
        $script:Ci.fatal=($_.Exception.Message+' @ '+$_.InvocationInfo.PositionMessage)
        Ci-Shot 'zz-failure'
    } finally { $script:CiWatchdog.Stop(); Ci-Finish }
})

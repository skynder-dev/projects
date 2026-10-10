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
            # 2) owner-attested Amazon profile through the real importer tool (non-interactive)
            $attest=[ordered]@{schema='forge.amazon_print_profile_attestation.v1';attested=$true;marketplace='amazon.com_us';product_type_key='standard_tshirt';template_key='ci-template';canvas_width_px=1024;canvas_height_px=1024;dpi=300;file_format='png';background='transparent';template_file_sha256=('a'*64);source_refs=@('https://merch.amazon.com/resource/Y28FFE5NLRYJG4V');captured_at=[DateTime]::UtcNow.AddMinutes(-5).ToString('o');valid_until=[DateTime]::UtcNow.AddDays(30).ToString('o')}
            $attestPath=Join-Path $env:FORGE_CI_OUT 'ci-profile-attestation.json'; [IO.File]::WriteAllText($attestPath,($attest|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
            $importer=[IO.Path]::GetFullPath((Join-Path $script:ModuleRoot '..\Import Amazon Print Profile.ps1'))
            $psExe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
            $impOut=& $psExe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $importer -SourcePath $attestPath -NonInteractive 2>&1 | Out-String
            Ci-Check 'pkg_profile_imported' ($LASTEXITCODE -eq 0 -and $null -ne (Get-LocalPolicyProfileBinding)) ($impOut.Trim())
            # 3) listing metadata through the Publication tab and its Save button
            Ci-Click $NavPublishButton 'NavPublishButton'
            $PublicationTitleBox.Text='Night Shift Nurse Coffee Fuel Funny ICU ER Nurse Gift'; $PublicationBrandBox.Text='CI Fixture Brand'; $PublicationBullet1Box.Text='Funny night shift nurse design for ICU and ER nurses.'; $PublicationBullet2Box.Text='Great gift for nurses who run on coffee.'; $PublicationDescriptionBox.Text='CI fixture listing.'; $PublicationKeywordsBox.Text='night shift nurse, icu nurse, er nurse'; $PublicationReasonBox.Text='ci'
            Ci-Flush
            Ci-Check 'pkg_save_listing_enabled' ([bool]$SavePublicationButton.IsEnabled)
            if($SavePublicationButton.IsEnabled){ Ci-Click $SavePublicationButton 'SavePublicationButton' } else { $null=Save-LocalPublicationMetadata }
            $lc=Get-LocalCoreConcept $key
            Ci-Check 'pkg_listing_saved' ($null -ne $lc.publication -and [string]$lc.publication.listing_title -like 'Night Shift Nurse*') ''
            Ci-Check 'pkg_print_check_pass_by_worker' ([string]$lc.checks.print.state -eq 'pass' -and [string]$lc.checks.print.source -eq 'trusted_local_check_worker') ([string]$lc.checks.print.state+' / '+[string]$lc.checks.print.note)
            # 4) owner evidence for IP / policy / metadata, filled from the app's own evidence template
            $tplDir=Join-Path $script:LocalCoreExportRoot (Join-Path (Get-LocalCoreSafeKey $key) 'checks')
            $tpl=@(Get-ChildItem -LiteralPath $tplDir -Filter 'check-evidence-*.template.json' | Sort-Object LastWriteTimeUtc -Descending)[0]
            $ev=Get-Content -LiteralPath $tpl.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach($n in @('visual','print')){ $ev.PSObject.Properties.Remove($n) }
            foreach($n in @('ip','policy','metadata')){ $c=$ev.$n; $c.state='pass'; $c.source='ci-owner-attestation'; $c.note='CI fixture attestation (not a real legal or policy review).'; $c.checked_at=[DateTime]::UtcNow.AddMinutes(-1).ToString('o'); $c.authority_kind='owner_attested_external'; $c.attested=$true; $c.evidence_refs=@('https://merch.amazon.com/resource/Y28FFE5NLRYJG4V') }
            $evPath=Join-Path $env:FORGE_CI_OUT 'ci-check-evidence.json'; [IO.File]::WriteAllText($evPath,($ev|ConvertTo-Json -Depth 20),(New-Object Text.UTF8Encoding($false)))
            Ci-Click $NavChecksButton 'NavChecksButton'
            # A real local error in the RU UI must reach the owner as a readable Russian message
            $badPath=Join-Path $env:FORGE_CI_OUT 'ci-bad-evidence.json'; [IO.File]::WriteAllText($badPath,'{"schema":"forge.local_check_evidence.v0"}',(New-Object Text.UTF8Encoding($false)))
            $before=$script:Ci.errors.Count; Import-LocalCheckEvidenceFromPath $badPath
            $raw=if($script:Ci.errors.Count -gt $before){[string]$script:Ci.errors[-1]}else{''}
            $shown=if((Test-KnownUiMessage $raw)){Translate-UiMessage $raw}else{Translate-UiMessage (Get-HumanErrorMessage $raw)}
            Ci-Check 'msg_error_readable_ru' ($raw -eq 'Unsupported check evidence schema.' -and $shown -eq 'Неподдерживаемый формат файла подтверждений.') ($raw+' => '+$shown)
            $script:Ci.errors=@($script:Ci.errors | Select-Object -First $before)
            $before=$script:Ci.errors.Count; Import-LocalCheckEvidenceFromPath $evPath; Ci-Flush
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
                Ci-Shot '14-performance'
            }
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

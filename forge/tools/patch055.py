import sys, os, io
root = sys.argv[1]
def patch(rel, pairs):
    p = os.path.join(root, rel)
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    crlf = '\r\n' in t
    for old, new in pairs:
        if crlf:
            old = old.replace('\n', '\r\n'); new = new.replace('\n', '\r\n')
        n = t.count(old)
        if n != 1:
            sys.exit(f'{rel}: expected 1 match, got {n}: {old[:90]!r}')
        t = t.replace(old, new)
    out = t.encode('utf-8')
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + out)
    print('patched', rel, 'bom' if bom else 'nobom', 'crlf' if crlf else 'lf')

DRAFT = "(Test-CurrentIsResearchDraft)"
patch('MerchForgeWorkbench.ps1', [
 ("# Version: 2.8.0-discover-research", "# Version: 2.9.0-research-draft"),
 ("$script:AppVersion = '2.8.0-forge-discover-research'", "$script:AppVersion = '2.9.0-forge-research-draft'"),
 (". (Join-Path $script:ModuleRoot 'Forge.LocalCore.ps1')", ". (Join-Path $script:ModuleRoot 'Forge.LocalCore.ps1')\n. (Join-Path $script:ModuleRoot 'Forge.ResearchDrafts.ps1')"),
 ('<TextBlock x:Name="DiscoverDetailDimensions" Style="{StaticResource MetaText}" Margin="0,12,0,0" TextWrapping="Wrap"/>',
  '<TextBlock x:Name="DiscoverDetailDimensions" Style="{StaticResource MetaText}" Margin="0,12,0,0" TextWrapping="Wrap"/><Button x:Name="DiscoverCreateDraftButton" Content="Create concept draft" Style="{StaticResource PrimaryButton}" IsEnabled="False" HorizontalAlignment="Left" Margin="0,16,0,0" AutomationProperties.Name="Create local concept draft from this niche"/><TextBlock x:Name="DiscoverDraftStatusText" Text="" Style="{StaticResource MetaText}" Margin="0,8,0,0" TextWrapping="Wrap"/>'),
 ('<ComboBoxItem Content="Blocked" Tag="blocked"/></ComboBox>', '<ComboBoxItem Content="Blocked" Tag="blocked"/><ComboBoxItem Content="Research draft" Tag="research_draft"/></ComboBox>'),
 ("function X([string]$Name){return $Window.FindName($Name)}", "Register-ResearchDraftUiText\nfunction X([string]$Name){return $Window.FindName($Name)}"),
 ("'blocked'{return (Get-StaticUiText 'Blocked')}default{return (Get-StaticUiText 'In progress')}}}", "'blocked'{return (Get-StaticUiText 'Blocked')}'research_draft'{return (Get-UiText 'draft.state' 'Research draft')}default{return (Get-StaticUiText 'In progress')}}}"),
 ("'blocked'{return '#F07878'}default{return '#93A0AD'}}}", "'blocked'{return '#F07878'}'research_draft'{return '#C4A4F2'}default{return '#93A0AD'}}}"),
 ("'blocked'{return '#381D22'}default{return '#1C2630'}}}", "'blocked'{return '#381D22'}'research_draft'{return '#2A2238'}default{return '#1C2630'}}}"),
 ("function Set-Dirty([bool]$Value) { $script:Dirty=$Value; $DirtyLabel.Text=if(-not (Has-Cap 'edit')){", "function Set-Dirty([bool]$Value) { $script:Dirty=$Value; $draftEdit="+DRAFT+"; $DirtyLabel.Text=if(-not ((Has-Cap 'edit') -or $draftEdit)){"),
 ("$SaveButton.IsEnabled=(-not $script:Busy -and (Has-Cap 'edit') -and $Value -and $null -ne $script:Current -and -not $accepted)", "$SaveButton.IsEnabled=(-not $script:Busy -and ((Has-Cap 'edit') -or $draftEdit) -and $Value -and $null -ne $script:Current -and -not $accepted)"),
 ("foreach($b in $editBoxes){$b.Add_TextChanged({ if($null -ne $script:Current -and -not $script:Busy -and (Has-Cap 'edit')){Set-Dirty $true} })}", "foreach($b in $editBoxes){$b.Add_TextChanged({ if($null -ne $script:Current -and -not $script:Busy -and ((Has-Cap 'edit') -or "+DRAFT+")){Set-Dirty $true} })}"),
 ("$OverviewVisualButton.Add_Click({if($script:OfflineMode){Show-ProductSection 'artwork'}", "$OverviewVisualButton.Add_Click({if($script:OfflineMode -or "+DRAFT+"){Show-ProductSection 'artwork'}"),
 ("$DiscoverRefreshButton.Add_Click({Load-DiscoverSnapshot $true})", "$DiscoverCreateDraftButton=X 'DiscoverCreateDraftButton'; $DiscoverDraftStatusText=X 'DiscoverDraftStatusText'\n$DiscoverRefreshButton.Add_Click({Load-DiscoverSnapshot $true})\n$DiscoverCreateDraftButton.Add_Click({Invoke-DiscoverCreateDraft})"),
 ("$DiscoverNicheList.Add_SelectionChanged({Update-DiscoverDetail})", "$DiscoverNicheList.Add_SelectionChanged({Update-DiscoverDetail;Update-DiscoverDraftControls})"),
])
patch('Modules/Forge.Gates.ps1', [
 ("$SaveButton.IsEnabled=(-not $Value -and (Has-Cap 'edit') -and $script:Dirty -and $null -ne $script:Current)", "$SaveButton.IsEnabled=(-not $Value -and ((Has-Cap 'edit') -or "+DRAFT+") -and $script:Dirty -and $null -ne $script:Current)"),
 ("$GenerateButton.IsEnabled=(-not $Value -and ((Has-Cap 'generate') -or (Test-LocalProductionProviderReady)) -and $null -ne $script:Current -and -not $script:Dirty)", "$GenerateButton.IsEnabled=(-not $Value -and ((Has-Cap 'generate') -or (Test-LocalProductionProviderReady)) -and $null -ne $script:Current -and -not $script:Dirty -and -not "+DRAFT+")"),
 ("foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox)){$box.IsReadOnly=(-not $canEdit)}", "foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox)){$box.IsReadOnly=(-not $canEdit)}; if("+DRAFT+"){Set-DraftEditBoxesEditable $true}"),
])
patch('Modules/Forge.DataViews.ps1', [
 ("$script:Queue=@(Add-QueueDisplayProperties $items)", "$script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue $items))"),
 ("$script:Queue=@(Add-QueueDisplayProperties $raw)", "$script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue $raw))"),
 ("        Populate-Detail $d; try{$null=Ensure-LocalCoreConceptFromCurrent", "        Populate-Detail $d; Restore-RoleEditability; try{$null=Ensure-LocalCoreConceptFromCurrent"),
 ("    if($script:ConceptLoadInProgress -or $null -eq $Item){return}\n", "    if($script:ConceptLoadInProgress -or $null -eq $Item){return}\n    if([bool](Get-PropertyValue $Item 'is_local_draft')){Open-ResearchDraftItem $Item;return}\n"),
 ("    $script:Current=[pscustomobject]@{concept=$c}\n", "    $script:Current=[pscustomobject]@{concept=$c}\n    Restore-RoleEditability\n"),
])
patch('Modules/Forge.ProductNavigation.ps1', [
 ("            } elseif($script:OfflineMode -and $script:OfflineSnapshotMode) {", "            } elseif("+DRAFT+" -and $Section -in @('ideas','artwork','checks','publish')) {\n                Enter-ResearchDraftSection $Section\n            } elseif($script:OfflineMode -and $script:OfflineSnapshotMode) {"),
 ("    } finally {Set-Busy $false}\n}\n\nfunction Set-SectionLanding", "    } finally {Set-Busy $false; try{Update-DiscoverDraftControls}catch{}}\n}\n\nfunction Set-SectionLanding"),
])
patch('Modules/Forge.Localization.ps1', [
 ("    if($null -ne $DiscoverRefreshButton){$DiscoverRefreshButton.Content=Get-UiText 'discover.refresh' 'Refresh research'}", "    if($null -ne $DiscoverRefreshButton){$DiscoverRefreshButton.Content=Get-UiText 'discover.refresh' 'Refresh research'}\n    try{Update-DiscoverDraftControls}catch{}"),
 ("                'blocked' {$item.Content=Get-UiText 'queue.blocked' 'Blocked'}", "                'blocked' {$item.Content=Get-UiText 'queue.blocked' 'Blocked'}\n                'research_draft' {$item.Content=Get-UiText 'queue.draft' 'Research draft'}"),
])

# Merch Forge · UI layout boundary
# Owns responsive layout primitives and concept-content navigation only.
function Confirm-ForgeWindowClose($EventArgs) {
    if(($script:Dirty-or$script:PublicationDirty)-and!(Confirm 'Close and discard unsaved creative/publication edits? Unsaved text is only in memory and cannot be recovered after closing or a crash. Explicitly save first to keep it.')){$EventArgs.Cancel=$true}
}
function Initialize-ForgeUnsavedCloseGuard($HostWindow) {
    if($null-eq$HostWindow-or[object]::ReferenceEquals($script:UnsavedGuardWindow,$HostWindow)){return}
    $HostWindow.add_Closing({param($sender,$eventArgs) Confirm-ForgeWindowClose $eventArgs})
    $script:UnsavedGuardWindow=$HostWindow
}
function Set-Thickness([double]$All) { return New-Object Windows.Thickness -ArgumentList $All }
function Set-GridLength([double]$Value) { return New-Object Windows.GridLength -ArgumentList $Value }
function New-StarGridLength([double]$Value) { return [System.Activator]::CreateInstance([Windows.GridLength],[object[]]@([double]$Value,[Windows.GridUnitType]::Star)) }
function Set-GridPos($Element,[int]$Column,[int]$Row=0) { if($null -ne $Element){[Windows.Controls.Grid]::SetColumn($Element,$Column);[Windows.Controls.Grid]::SetRow($Element,$Row)} }
function Set-QueueEmptyState([int]$VisibleCount) {
    if($null -eq $QueueEmptyPanel){return}
    if($VisibleCount -gt 0){$QueueEmptyPanel.Visibility='Collapsed';$ConceptList.Visibility='Visible';return}
    $ConceptList.Visibility='Collapsed';$QueueEmptyPanel.Visibility='Visible'
    if(@($script:Queue).Count -eq 0){
        $QueueEmptyTitle.Text=Get-UiText 'queue.empty' 'No ideas yet'
        $QueueEmptyBody.Text=Get-UiText 'queue.empty.body' 'There are no ideas in the local snapshot.'
    } else {
        $QueueEmptyTitle.Text=Get-UiText 'queue.nomatches' 'No matches'
        $QueueEmptyBody.Text=Get-UiText 'queue.nomatches.body' 'Try another search or choose All statuses.'
    }
}
function Set-ResponsivePair($GapColumn,$RightColumn,$RightPane,[bool]$Compact,[double]$DesktopGap=18,[double]$DesktopRightWeight=1) {
    if($Compact){$GapColumn.Width=Set-GridLength 0;$RightColumn.Width=Set-GridLength 0;Set-GridPos $RightPane 0 1;$RightPane.Margin=New-Object Windows.Thickness -ArgumentList 0,14,0,0}
    else{$GapColumn.Width=Set-GridLength $DesktopGap;$RightColumn.Width=New-StarGridLength $DesktopRightWeight;Set-GridPos $RightPane 2 0;$RightPane.Margin=Set-Thickness 0}
}
function Update-ResponsiveLayout {
    if($null -eq $Window -or $null -eq $WorkAreaGrid){return}
    $compact=($Window.ActualWidth -lt 980)
    if($compact){
        $QueueColumn.Width=Set-GridLength 0; $QueueGapColumn.Width=Set-GridLength 0; $ConceptPane.Visibility='Collapsed'
        $HomeButton.Visibility='Collapsed'; $CompactConceptBox.Visibility='Visible'; $ActorText.Visibility='Collapsed'; $LanguageLabel.Visibility='Collapsed'; $HeaderLanguageSegment.Visibility='Collapsed'; if($null -ne $ProductNavHint){$ProductNavHint.Visibility='Collapsed'}; foreach($b in @($NavHomeButton,$NavDiscoverButton,$NavIdeasButton,$NavArtworkButton,$NavChecksButton,$NavPublishButton,$NavPortfolioButton,$NavPerformanceButton)){if($null -ne $b){$b.Padding=New-Object Windows.Thickness -ArgumentList 9,7,9,7;$b.Margin=New-Object Windows.Thickness -ArgumentList 0,0,2,0}}
        $AboutButton.Content='?'; $AboutButton.ToolTip=(Get-UiText 'shell.about' 'About'); $DiagnosticsButton.Content='⋯'; $DiagnosticsButton.ToolTip=(Get-UiText 'shell.diagnostics' 'Diagnostics'); $RefreshButton.Content='↻'; $RefreshButton.ToolTip=(Get-UiText 'shell.refresh' 'Refresh'); $ForgetButton.Content='×'; $ForgetButton.ToolTip=(Get-UiText 'shell.signout' 'Sign out')
        foreach($b in @($AboutButton,$DiagnosticsButton,$RefreshButton,$ForgetButton)){$b.Margin=New-Object Windows.Thickness -ArgumentList 1,0,1,0;$b.MinWidth=36;$b.MinHeight=36}
        $CompactConceptBox.Width=[Math]::Max(80,[Math]::Min(220,$Window.ActualWidth-210))
        $WorkAreaGrid.Margin=Set-Thickness 6; $MainTabs.Margin=Set-Thickness 4; foreach($tab in $MainTabs.Items){if($tab -is [Windows.Controls.TabItem]){$tab.Padding=New-Object Windows.Thickness -ArgumentList 10,7,10,7;$tab.Margin=New-Object Windows.Thickness -ArgumentList 0,0,4,4}}
        $SaveButton.Content=(Get-StaticUiText 'Save'); $ConceptMeta.Visibility='Collapsed'; $DirtyLabel.Visibility='Collapsed'
        Set-ResponsivePair $EditGapColumn $EditRightColumn $EditRightPane $true 18 1
        Set-ResponsivePair $HistoryGapColumn $HistoryRightColumn $HistoryRightPane $true 12 2
        Set-ResponsivePair $HistoryDetailGapColumn $HistoryDetailRightColumn $HistoryDetailRightPane $true 12 1
        Set-ResponsivePair $VariantsGapColumn $VariantsRightColumn $VariantsRightPane $true 12 2
        Set-ResponsivePair $VariantMediaGapColumn $VariantMediaRightColumn $VariantMediaRightPane $true 12 1
        Set-ResponsivePair $PublicationGapColumn $PublicationRightColumn $PublicationRightPane $true 18 1
        # Compare and review sub-grids become one column.
        $VariantCompareGrid.ColumnDefinitions[1].Width=Set-GridLength 0;$VariantCompareGrid.ColumnDefinitions[2].Width=Set-GridLength 0;Set-GridPos $VariantCompareB 0 1;$VariantCompareB.Margin=New-Object Windows.Thickness -ArgumentList 0,8,0,0
        $VariantReviewGrid.ColumnDefinitions[1].Width=Set-GridLength 0;$VariantReviewGrid.ColumnDefinitions[2].Width=Set-GridLength 0;$VariantReviewGrid.ColumnDefinitions[3].Width=Set-GridLength 0;$VariantReviewGrid.ColumnDefinitions[4].Width=Set-GridLength 0;Set-GridPos $VariantReviewState 0 0;Set-GridPos $VariantReviewReason 0 1;Set-GridPos $VariantReviewNote 0 2;$VariantReviewState.Margin=Set-Thickness 0;$VariantReviewReason.Margin=New-Object Windows.Thickness -ArgumentList 0,8,0,0;$VariantReviewNote.Margin=New-Object Windows.Thickness -ArgumentList 0,8,0,0
    } else {
        $QueueColumn.Width=Set-GridLength 330; $QueueGapColumn.Width=Set-GridLength 12; $ConceptPane.Visibility='Visible'
        $HomeButton.Visibility='Visible'; $CompactConceptBox.Visibility='Collapsed'; $ActorText.Visibility='Visible'; $LanguageLabel.Visibility='Visible'; $HeaderLanguageSegment.Visibility='Visible'; if($null -ne $ProductNavHint){$ProductNavHint.Visibility='Visible'}; foreach($b in @($NavHomeButton,$NavDiscoverButton,$NavIdeasButton,$NavArtworkButton,$NavChecksButton,$NavPublishButton,$NavPortfolioButton,$NavPerformanceButton)){if($null -ne $b){$b.Padding=New-Object Windows.Thickness -ArgumentList 14,8,14,8;$b.Margin=New-Object Windows.Thickness -ArgumentList 0,0,5,0}}
        $AboutButton.Content=Get-UiText 'shell.about' 'About'; $DiagnosticsButton.Content=Get-UiText 'shell.diagnostics' 'Diagnostics'; $RefreshButton.Content=Get-UiText 'shell.refresh' 'Refresh'; $ForgetButton.Content=Get-UiText 'shell.signout' 'Sign out'
        foreach($b in @($AboutButton,$DiagnosticsButton,$RefreshButton,$ForgetButton)){$b.Margin=New-Object Windows.Thickness -ArgumentList 0,0,8,0}
        $CompactConceptBox.ClearValue([Windows.FrameworkElement]::WidthProperty)
        $WorkAreaGrid.Margin=Set-Thickness 16; $MainTabs.Margin=Set-Thickness 12; foreach($tab in $MainTabs.Items){if($tab -is [Windows.Controls.TabItem]){$tab.Padding=New-Object Windows.Thickness -ArgumentList 14,8,14,8;$tab.Margin=New-Object Windows.Thickness -ArgumentList 0,0,6,0}}
        $SaveButton.Content=(Get-StaticUiText 'Save new revision'); $ConceptMeta.Visibility='Visible'; $DirtyLabel.Visibility='Visible'
        Set-ResponsivePair $EditGapColumn $EditRightColumn $EditRightPane $false 18 1
        Set-ResponsivePair $HistoryGapColumn $HistoryRightColumn $HistoryRightPane $false 12 2
        Set-ResponsivePair $HistoryDetailGapColumn $HistoryDetailRightColumn $HistoryDetailRightPane $false 12 1
        Set-ResponsivePair $VariantsGapColumn $VariantsRightColumn $VariantsRightPane $false 12 2
        Set-ResponsivePair $VariantMediaGapColumn $VariantMediaRightColumn $VariantMediaRightPane $false 12 1
        Set-ResponsivePair $PublicationGapColumn $PublicationRightColumn $PublicationRightPane $false 18 1
        $VariantCompareGrid.ColumnDefinitions[1].Width=Set-GridLength 10;$VariantCompareGrid.ColumnDefinitions[2].Width=New-StarGridLength 1;Set-GridPos $VariantCompareB 2 0;$VariantCompareB.Margin=Set-Thickness 0
        $VariantReviewGrid.ColumnDefinitions[1].Width=Set-GridLength 8;$VariantReviewGrid.ColumnDefinitions[2].Width=Set-GridLength 210;$VariantReviewGrid.ColumnDefinitions[3].Width=Set-GridLength 8;$VariantReviewGrid.ColumnDefinitions[4].Width=New-StarGridLength 1;Set-GridPos $VariantReviewState 0 0;Set-GridPos $VariantReviewReason 2 0;Set-GridPos $VariantReviewNote 4 0;$VariantReviewState.Margin=Set-Thickness 0;$VariantReviewReason.Margin=Set-Thickness 0;$VariantReviewNote.Margin=Set-Thickness 0
    }
    if(@('home','portfolio','performance') -contains $script:ProductSection){$QueueColumn.Width=Set-GridLength 0;$QueueGapColumn.Width=Set-GridLength 0;$ConceptPane.Visibility='Collapsed';$CompactConceptBox.Visibility='Collapsed'}
    # The XAML gives QueueColumn MinWidth=340; without clearing it a 'hidden' queue still occupies 340px of empty space.
    $QueueColumn.MinWidth=if($QueueColumn.Width.Value -le 0){0}else{340}
}
function Select-MainTab([string]$Header) {
    if($null -eq $MainTabs){return}
    $map=@{'Overview'='overview';'Visuals & Generate'='visuals';'History'='history';'Evidence'='evidence';'Delivery'='delivery';'Publication'='publication';'Edit'='edit'}
    $target=if($map.ContainsKey($Header)){$map[$Header]}else{$Header.ToLowerInvariant()}
    foreach($tab in @($MainTabs.Items)) { if((Get-MainTabKey $tab) -eq $target){$MainTabs.SelectedItem=$tab;break} }
}
function Set-ConceptTabsEnabled([bool]$Enabled) {
    if($null -eq $MainTabs){return}
    foreach($tab in @($MainTabs.Items)){if($tab -is [Windows.Controls.TabItem]){$key=Get-MainTabKey $tab;$tab.IsEnabled=($Enabled -or $key -eq 'overview')}}
}
# R2O module: Forge.ProductNavigation.ps1
function Update-MainTabUi {
    if($null -eq $MainTabs -or $null -eq $MainTabs.SelectedItem){return}
    Initialize-ForgeUnsavedCloseGuard ([Windows.Window]::GetWindow($MainTabs))
    $isEdit=((Get-MainTabKey $MainTabs.SelectedItem) -eq 'edit')
    $SaveButton.Visibility=if($isEdit){'Visible'}else{'Collapsed'}
    $DirtyLabel.Visibility=if($isEdit){'Visible'}else{'Collapsed'}
}

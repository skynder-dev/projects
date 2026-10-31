# PREPARED native test. Extracts actual function ASTs; does not load Workbench/module initializers.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageRoot,
    [Parameter(Mandatory=$true)][string]$PinsPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory=$true)][string]$RunRoot
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot);$RunRoot=[IO.Path]::GetFullPath($RunRoot)
function Get-TestHash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Assert-Equal($Expected,$Actual,[string]$Message){if($Expected-cne$Actual){throw ($Message+'; expected='+[string]$Expected+' actual='+[string]$Actual)}}
function Assert-True($Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Assert-TestPath([string]$Path,[bool]$Directory){
    $item=Get-Item -LiteralPath $Path -Force
    Assert-Equal $Directory ([bool]$item.PSIsContainer) ('Path type '+$Path)
    $cursor=$item
    while($null-ne$cursor){
        Assert-Equal 0 ([int]($cursor.Attributes-band[IO.FileAttributes]::ReparsePoint)) ('No redirected path '+$cursor.FullName)
        $cursor=if($cursor-is[IO.DirectoryInfo]){$cursor.Parent}else{$cursor.Directory}
    }
}
Assert-TestPath $RunRoot $true;Assert-TestPath $PackageRoot $true;Assert-TestPath $PinsPath $false
Assert-Equal 0 @([IO.Directory]::GetFileSystemEntries($RunRoot)).Count 'Fresh empty private run root required'
Assert-True ($RunRoot-ne$PackageRoot-and-not$RunRoot.StartsWith($PackageRoot.TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'Run root must be outside source package'
$started=[DateTime]::UtcNow.ToString('o');$script:Cases=New-Object Collections.Generic.List[object];$loaded=New-Object Collections.Generic.List[string]
$sourceBefore=[ordered]@{};$sourceAfter=[ordered]@{};$testBefore=[ordered]@{};$testAfter=[ordered]@{};$failure=$null;$claim=$null;$receiptStream=$null;$pinsHash=Get-TestHash $PinsPath
try{
    $claim=[IO.File]::Open((Join-Path $RunRoot '.forge-locale.claim'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $idBytes=[Text.Encoding]::UTF8.GetBytes($RunId);$claim.Write($idBytes,0,$idBytes.Length);$claim.Flush($true)
    $receiptStream=[IO.File]::Open((Join-Path $RunRoot 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{
        Assert-True ($PSVersionTable.PSEdition-ceq'Core'-and$PSVersionTable.PSVersion-ge[version]'7.5'-and$PSVersionTable.PSVersion.ToString()-match'^\d+\.\d+(?:\.\d+){0,2}$') 'Already-installed stable PowerShell Core 7.5+ required'
        $pins=[IO.File]::ReadAllText($PinsPath)|ConvertFrom-Json -DateKind String
        Assert-Equal 'forge.locale_edit_preservation.pins.v1' $pins.schema 'Pin schema'
        foreach($entry in $pins.tests.PSObject.Properties){
            $p=Join-Path $PSScriptRoot $entry.Name;Assert-TestPath $p $false;$testBefore[$entry.Name]=Get-TestHash $p
            Assert-Equal $entry.Value $testBefore[$entry.Name] ('Pinned test '+$entry.Name)
        }
        foreach($entry in $pins.sources.PSObject.Properties){
            $p=Join-Path $PackageRoot $entry.Name;Assert-TestPath $p $false;$sourceBefore[$entry.Name]=Get-TestHash $p
            Assert-Equal $entry.Value $sourceBefore[$entry.Name] ('Pinned source '+$entry.Name)
            $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$errors)
            Assert-Equal 0 @($errors).Count ('Native parser '+$entry.Name)
            foreach($name in @($pins.functions.($entry.Name))){
                $definitions=@($ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq$name},$true))
                Assert-Equal 1 $definitions.Count ('Unique actual function '+$name)
                . ([scriptblock]::Create($definitions[0].Extent.Text))
                $loaded.Add($name)
            }
        }
        Assert-Equal ($pins.expected_function_names-join'|') ($loaded-join'|') 'Exact actual functions/order'
        $script:BoundaryCalls=0
        foreach($command in @('Invoke-WebRequest','Invoke-RestMethod','Invoke-ForgeApi','Start-Process','Set-LocalExactAcceptance','Build-LocalAmazonPackage','Write-LocalCoreState','Save-ResearchDraftRevision','Save-PublicationMetadata')){
            Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("`$script:BoundaryCalls++;throw 'Unexpected boundary: $command'"))
        }
        # Explicit seams: persistence, rendering, loaded preference, static registry and destructive draft loader.
        # No real durable store, UI renderer/WPF event, native dialog, publication or network is exercised.
        function Save-UiLocale([string]$Locale){$script:SaveCalls++;$script:SavedLocale=$Locale}
        function Apply-LocaleUi {$script:ApplyCalls++;Restore-DynamicSurfacesAfterLocale}
        function Get-UiText([string]$Key,[string]$Fallback){return $Fallback}
        function Load-UiLocale {return $script:LoadedLocale}
        function Register-StaticLocaleTree($Root){$script:RegisterCalls++;[void]$script:StaticLocaleRegistry.Add('synthetic-binding')}
        function Update-ListingHints {$script:HintsCalls++}
        function Update-PortfolioPipelineSurface {$script:PortfolioCalls++}
        function Open-ResearchDraftItem($Item,[bool]$Force){
            $script:OpenCalls++;$script:OpenKey=$Item.concept_key;$script:OpenForce=$Force
            # Models only the existing destructive effect of a forced draft reload (not the real loader).
            foreach($name in $script:EditorNames){(Get-Variable -Scope Script -Name $name).Value.Text='saved-'+$name}
            $script:Dirty=$false;$script:PublicationDirty=$false;$script:ProductSection='ideas'
        }
        function Show-ProductSection([string]$Section){$script:ShowCalls++;$script:ProductSection=$Section}
        function Reset-Test([string]$Locale='en',[bool]$Creative=$false,[bool]$Publication=$false){
            $script:SupportedLocales=@('en','ru','es');$script:Locale=$Locale;$script:LoadedLocale=$Locale
            $script:Dirty=$Creative;$script:PublicationDirty=$Publication;$script:LocaleChangeInProgress=$false
            $script:Current=[pscustomobject]@{local_research_draft=$true;concept=[pscustomobject]@{concept_key='rd-locale-test'}}
            $script:ProductSection='publish';$script:DiscoverSnapshot=$null;$script:DiscoverLoadedAt=$null
            $script:DiscoverNicheList=$null;$script:DiscoverStatusText=$null
            $script:SaveCalls=0;$script:ApplyCalls=0;$script:OpenCalls=0;$script:HintsCalls=0;$script:PortfolioCalls=0;$script:RegisterCalls=0;$script:ShowCalls=0
            $script:SavedLocale='unchanged-preference';$script:OpenKey='';$script:OpenForce=$false
            $script:StaticLocaleRegistry=New-Object Collections.Generic.List[object];$script:Window=[pscustomobject]@{Title='synthetic-window'}
            $script:StatusText=[pscustomobject]@{Text='unchanged-status'}
            $script:EditorNames=@('TitleBox','HookBox','ConceptTextBox','BuyerBox','PurchaseBox','DifferentiationBox','VisualBox','SpecBox','ReasonBox','PublicationTitleBox','PublicationBrandBox','PublicationBullet1Box','PublicationBullet2Box','PublicationDescriptionBox','PublicationKeywordsBox','PublicationReasonBox')
            foreach($name in $script:EditorNames){Set-Variable -Scope Script -Name $name -Value ([pscustomobject]@{Text=('unsaved-'+$Locale+'-'+$name+'-é-Ж')})}
            $script:PublicationLocaleBox=[pscustomobject]@{SelectedItem=[pscustomobject]@{Tag='es-ES'}}
            foreach($name in @('LanguageBox','LoginLanguageBox')){Set-Variable -Scope Script -Name $name -Value ([pscustomobject]@{Items=@([pscustomobject]@{Tag='en'},[pscustomobject]@{Tag='ru'},[pscustomobject]@{Tag='es'});SelectedItem=$null})}
            foreach($name in @('LoginLangEn','LoginLangRu','LoginLangEs','HeaderLangEn','HeaderLangRu','HeaderLangEs')){Set-Variable -Scope Script -Name $name -Value ([pscustomobject]@{IsChecked=$false})}
            $script:SavedState=[pscustomobject]@{revision='saved-revision';acceptance='saved-acceptance';package='saved-package';listing='saved-listing';receipt='historical-receipt'}
        }
        function Get-EditorFrame {
            $frame=[ordered]@{dirty=$script:Dirty;publication_dirty=$script:PublicationDirty;locale=$script:Locale;section=$script:ProductSection;publication_locale=$PublicationLocaleBox.SelectedItem.Tag;current=$script:Current;saved=$script:SavedState}
            foreach($name in $script:EditorNames){$frame[$name]=(Get-Variable -Scope Script -Name $name).Value.Text}
            return ($frame|ConvertTo-Json -Depth 20 -Compress)
        }
        function Assert-NoReload {Assert-Equal 0 $script:SaveCalls 'No preference save';Assert-Equal 0 $script:ApplyCalls 'No locale reapply';Assert-Equal 0 $script:OpenCalls 'No forced draft reopen'}
        function Test-Case([string]$Name,[scriptblock]$Body){try{& $Body;$script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';error=$null})}catch{$script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';error=$_.Exception.Message})}}
        foreach($locale in @('en','ru','es')){
            foreach($flags in @(@{name='clean';creative=$false;publication=$false},@{name='creative';creative=$true;publication=$false},@{name='publication';creative=$false;publication=$true},@{name='both';creative=$true;publication=$true})){
                Test-Case ('same_'+$locale+'_'+$flags.name) {
                    Reset-Test $locale $flags.creative $flags.publication;$before=Get-EditorFrame
                    for($repeat=0;$repeat-lt2;$repeat++){
                        Assert-Equal $true (Set-UiLocale $locale $true) 'Same locale succeeds';Sync-LanguageSelector
                        Assert-Equal $before (Get-EditorFrame) 'Repeated language action preserves every editor value/flag/current identity'
                    }
                    Assert-NoReload;Assert-Equal 'unchanged-status' $StatusText.Text 'No warning for same locale';Assert-Equal $locale $LanguageBox.SelectedItem.Tag 'Language selector synchronized';Assert-Equal $false $script:LocaleChangeInProgress 'Selector reentrancy flag cleared'
                }
            }
        }
        Test-Case 'same_normalized_input_is_noop' {Reset-Test 'ru' $false $true;$before=Get-EditorFrame;Assert-Equal $true (Set-UiLocale ' RU ' $false) 'Validated normalized same locale';Assert-Equal $before (Get-EditorFrame) 'Normalized input preserves editor';Assert-NoReload}
        Test-Case 'unsupported_input_rejected_before_noop' {Reset-Test 'xx' $true $true;$before=Get-EditorFrame;Assert-Equal $false (Set-UiLocale 'xx' $true) 'Unsupported current/requested locale cannot bypass validation';Assert-Equal $before (Get-EditorFrame) 'Invalid input preserves editor';Assert-NoReload}
        foreach($locale in @('en','ru','es')){
            $next=if($locale-eq'en'){'ru'}elseif($locale-eq'ru'){'es'}else{'en'}
            foreach($flags in @(@{name='creative';creative=$true;publication=$false},@{name='publication';creative=$false;publication=$true},@{name='both';creative=$true;publication=$true})){
                Test-Case ('different_'+$locale+'_'+$flags.name+'_blocked') {
                    Reset-Test $locale $flags.creative $flags.publication;$before=Get-EditorFrame
                    Assert-Equal $false (Set-UiLocale $next $true) 'Dirty locale change blocked';Sync-LanguageSelector
                    Assert-Equal $before (Get-EditorFrame) 'Dirty change preserves editor/current locale';Assert-NoReload
                    Assert-Equal 'Save or discard current edits before changing UI language.' $StatusText.Text 'Existing dirty warning';Assert-Equal $locale $LanguageBox.SelectedItem.Tag 'Rejected selector restored'
                }
            }
            foreach($persist in @($true,$false)){
                Test-Case ('different_'+$locale+'_clean_persist_'+$persist.ToString().ToLowerInvariant()) {
                    Reset-Test $locale;$saved=$script:SavedState|ConvertTo-Json -Compress
                    Assert-Equal $true (Set-UiLocale $next $persist) 'Clean change succeeds';Sync-LanguageSelector
                    Assert-Equal $next $script:Locale 'Changed UI locale';Assert-Equal ([int]$persist) $script:SaveCalls 'Persist behavior unchanged';Assert-Equal 1 $script:ApplyCalls 'One application';Assert-Equal 1 $script:OpenCalls 'Clean dynamic draft reloaded';Assert-True $script:OpenForce 'Existing force argument';Assert-Equal 'rd-locale-test' $script:OpenKey 'Exact current draft'
                    Assert-Equal $(if($persist){$next}else{'unchanged-preference'}) $script:SavedLocale 'Only requested preference persistence';Assert-Equal $saved ($script:SavedState|ConvertTo-Json -Compress) 'No saved concept/readiness mutation'
                }
            }
        }
        foreach($flags in @(@{name='creative';creative=$true;publication=$false},@{name='publication';creative=$false;publication=$true},@{name='both';creative=$true;publication=$true})){
            Test-Case ('helper_'+$flags.name+'_preserved') {Reset-Test 'en' $flags.creative $flags.publication;$before=Get-EditorFrame;Restore-DynamicSurfacesAfterLocale;Assert-Equal $before (Get-EditorFrame) 'Direct helper preserves dirty editor';Assert-Equal 0 $script:OpenCalls 'No force reopen';Assert-Equal 1 $script:HintsCalls 'Non-destructive hint refresh retained'}
        }
        Test-Case 'helper_clean_reopens_exact_draft' {Reset-Test;Restore-DynamicSurfacesAfterLocale;Assert-Equal 1 $script:OpenCalls 'Clean draft reload retained';Assert-Equal 'rd-locale-test' $script:OpenKey 'Exact identity';Assert-True $script:OpenForce 'Force only on clean editor'}
        Test-Case 'helper_clean_restores_portfolio_section' {Reset-Test;$script:ProductSection='portfolio';Restore-DynamicSurfacesAfterLocale;Assert-Equal 1 $script:OpenCalls 'Clean reload';Assert-Equal 1 $script:PortfolioCalls 'Portfolio refresh retained';Assert-Equal 1 $script:ShowCalls 'Previous section restored';Assert-Equal 'portfolio' $script:ProductSection 'Stay on portfolio'}
        Test-Case 'helper_nonresearch_does_not_reopen' {Reset-Test;$script:Current.local_research_draft=$false;$before=Get-EditorFrame;Restore-DynamicSurfacesAfterLocale;Assert-Equal 0 $script:OpenCalls 'Nonresearch not reloaded';Assert-Equal $before (Get-EditorFrame) 'Nonresearch editor intact'}
        foreach($locale in @('en','ru','es')){
            Test-Case ('initialize_'+$locale+'_still_applies') {Reset-Test $locale;$script:Current=$null;Initialize-UiLocale;Assert-Equal $locale $script:Locale 'Loaded locale';Assert-Equal 1 $script:ApplyCalls 'Startup explicitly applies even identical locale';Assert-Equal 1 $script:RegisterCalls 'Static tree registered';Assert-Equal 0 $script:SaveCalls 'Startup does not rewrite preference';Assert-Equal $locale $LoginLanguageBox.SelectedItem.Tag 'Startup selectors synchronized'}
        }
        Test-Case 'initialize_invalid_preference_falls_back' {Reset-Test;$script:Current=$null;$script:LoadedLocale='xx';Initialize-UiLocale;Assert-Equal 'en' $script:Locale 'Existing fallback';Assert-Equal 1 $script:ApplyCalls 'Fallback applied'}
        Test-Case 'initialize_existing_registry_reapplies' {Reset-Test;$script:Current=$null;[void]$script:StaticLocaleRegistry.Add('already-registered');Initialize-UiLocale;Initialize-UiLocale;Assert-Equal 2 $script:ApplyCalls 'Explicit initialization retains reapply';Assert-Equal 0 $script:RegisterCalls 'No duplicate registry'}
        Test-Case 'no_external_or_product_mutation_calls' {Assert-Equal 0 $script:BoundaryCalls 'No external calls or saves/approval/package actions'}
        Assert-Equal ($pins.expected_case_names-join'|') ((@($script:Cases|ForEach-Object{$_.name}))-join'|') 'Exact case identity/order'
        foreach($entry in $sourceBefore.GetEnumerator()){$sourceAfter[$entry.Key]=Get-TestHash (Join-Path $PackageRoot $entry.Key);Assert-Equal $entry.Value $sourceAfter[$entry.Key] ('Source unchanged '+$entry.Key)}
        foreach($entry in $testBefore.GetEnumerator()){$testAfter[$entry.Key]=Get-TestHash (Join-Path $PSScriptRoot $entry.Key);Assert-Equal $entry.Value $testAfter[$entry.Key] ('Test unchanged '+$entry.Key)}
        Assert-Equal $pinsHash (Get-TestHash $PinsPath) 'Pins unchanged'
        Assert-Equal 0 @($script:Cases|Where-Object{$_.status-ne'PASS'}).Count 'Every prepared case passes'
    }catch{$failure=$_.Exception.Message}
    $receipt=[ordered]@{schema='forge.locale_edit_preservation.native_receipt.v1';run_id=$RunId;started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o');package_root=$PackageRoot;run_root=$RunRoot;pins_sha256=$pinsHash;runtime=$PSVersionTable.PSVersion.ToString();status=$(if($null-eq$failure){'PASS'}else{'FAIL'});error=$failure;functions=@($loaded.ToArray());cases=@($script:Cases.ToArray());source_before=$sourceBefore;source_after=$sourceAfter;test_before=$testBefore;test_after=$testAfter;scope='Actual functions with explicit rendering/persistence/forced-reopen seams, not WPF or durable-state proof'}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 20));$receiptStream.Write($bytes,0,$bytes.Length);$receiptStream.Flush($true)
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}
if($null-ne$failure){throw $failure}

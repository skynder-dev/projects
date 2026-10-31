# NEW bounded provider reconciliation regression. Not a Workbench/app smoke test.
# Actual seven-file import closure; actual BackendStatus bodies. UI/local-state
# dependencies below are in-memory doubles, not a real transport/network sandbox.
# Run only under a supervisor with a process-tree deadline. Timeout, crash, absent
# receipt, nonzero exit, hash mismatch, or non-PASS receipt MUST fail the run.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$FrozenModuleRoot,
    [Parameter(Mandatory=$true)][string]$ProviderModuleRoot,
    [string]$ReceiptParent=([IO.Path]::GetTempPath()),
    [ValidatePattern('^[0-9a-f]{32}$')][string]$RunId=([Guid]::NewGuid().ToString('N'))
)
$ErrorActionPreference='Stop'
$started=[DateTime]::UtcNow.ToString('o')
$script:Cases=New-Object 'Collections.Generic.List[object]'
$script:Sources=New-Object 'Collections.Generic.List[object]'
$script:Loaded=New-Object 'Collections.Generic.List[object]'
$script:ImportAudit=New-Object 'Collections.Generic.List[object]'
$script:CheckCount=0
$script:BoundaryHits=New-Object 'Collections.Generic.List[object]'
$script:Fatal=''
$runRoot=Join-Path $ReceiptParent ('forge-provider-isolation-'+$RunId)
if(Test-Path -LiteralPath $runRoot){throw 'Fresh GUID root already exists; refusing receipt reuse.'}
[void][IO.Directory]::CreateDirectory($runRoot)
if((Get-Item -LiteralPath $runRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Receipt root is redirected.'}
$receiptPath=Join-Path $runRoot 'receipt.json'
$ownedRoot=Join-Path $runRoot 'Modules'
[void][IO.Directory]::CreateDirectory($ownedRoot)
Write-Host ('PROVIDER_ISOLATION_RUN_ID='+$RunId)
Write-Host ('PROVIDER_ISOLATION_RECEIPT='+$receiptPath)

function Get-IsolationHash([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}
    finally{$sha.Dispose()}
}
function Get-IsolationTextHash([string]$Text){return Get-IsolationHash ([Text.Encoding]::UTF8.GetBytes($Text))}
function Assert-Isolation([bool]$Condition,[string]$Message){
    $script:CheckCount++
    if(!$Condition){throw ('CHECK_FAILED: '+$Message)}
}
function Invoke-IsolationCase([string]$Name,[scriptblock]$Body){
    try{& $Body;$script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';detail=''})}
    catch{$script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';detail=$_.Exception.Message})}
    Write-Host ($script:Cases[$script:Cases.Count-1].status+': '+$Name)
}
function Get-IsolationAst([string]$Path){
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    Assert-Isolation (@($errors).Count -eq 0) ('Source parses: '+$Path)
    return $ast
}
function Assert-IsolationTopLevel($Ast,[string]$Name,[string[]]$AllowedImports){
    # Function declarations are inert here. Every other executable statement must
    # be exactly one of these reviewed literal sibling imports. No expression
    # evaluation is used to decide whether an import is permitted.
    if($null-ne$Ast.ParamBlock-or$null-ne$Ast.BeginBlock-or$null-ne$Ast.ProcessBlock-or$null-ne$Ast.DynamicParamBlock-or($null-ne$Ast.UsingStatements-and$Ast.UsingStatements.Count)-or($null-ne$Ast.Attributes-and$Ast.Attributes.Count)-or$null-ne$Ast.ScriptRequirements){throw ('UNREVIEWED_SCRIPT_HEADER: '+$Name)}
    if($null-eq$Ast.EndBlock-or($null-ne$Ast.EndBlock.Traps-and$Ast.EndBlock.Traps.Count)){throw ('UNREVIEWED_END_BLOCK: '+$Name)}
    $clean=$Ast.PSObject.Properties['CleanBlock']
    if($null-ne$clean-and$null-ne$clean.Value){throw ('UNREVIEWED_CLEAN_BLOCK: '+$Name)}
    $seen=@();$functions=@()
    foreach($statement in @($Ast.EndBlock.Statements)){
        if($statement-is[Management.Automation.Language.FunctionDefinitionAst]){
            if($statement.IsFilter-or$statement.Name-cnotmatch'^[A-Za-z][A-Za-z0-9-]*$'-or$functions-ccontains$statement.Name){throw ('UNREVIEWED_FUNCTION_DECLARATION: '+$Name)}
            $functions+=,$statement.Name;continue
        }
        $matched=$false
        foreach($import in $AllowedImports){
            $literal=". (Join-Path `$PSScriptRoot '"+$import+"')"
            if($statement.Extent.Text.Trim()-ceq$literal){
                if($statement-isnot[Management.Automation.Language.PipelineAst]-or$statement.PipelineElements.Count-ne1){throw 'UNREVIEWED_IMPORT_SHAPE'}
                $command=$statement.PipelineElements[0]
                if($command-isnot[Management.Automation.Language.CommandAst]-or$command.InvocationOperator-ne[Management.Automation.Language.TokenKind]::Dot-or$command.Redirections.Count){throw 'UNREVIEWED_IMPORT_COMMAND'}
                if($seen-ccontains$import){throw 'DUPLICATE_IMPORT'}
                $seen+=,$import;$matched=$true;break
            }
        }
        if(!$matched){throw ('UNREVIEWED_TOP_LEVEL: '+$Name+': '+$statement.Extent.Text)}
    }
    if(($seen.Count-ne$AllowedImports.Count)-or@($AllowedImports|Where-Object{$seen-cnotcontains$_}).Count){throw ('MISSING_REVIEWED_IMPORT: '+$Name)}
    if(!$functions.Count){throw ('NO_FUNCTIONS: '+$Name)}
    return [pscustomobject]@{name=$Name;functions=$functions.Count;imports=$seen;unreviewed_top_level=0}
}
function Assert-IsolationRejectedAst([string]$Text){
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseInput($Text,[ref]$tokens,[ref]$errors)
    Assert-Isolation (@($errors).Count-eq0) 'Negative allowlist fixture must parse.'
    $rejected=$false
    try{$null=Assert-IsolationTopLevel $ast 'synthetic-negative-fixture' @()}catch{$rejected=$true}
    Assert-Isolation $rejected 'Unreviewed executable top-level fixture must be rejected before import.'
}
function Assert-IsolationPaths {
    Assert-Isolation ($script:BoundaryHits.Count-eq0) 'No selected call path reached a source/model/mobile/transport probe.'
    Assert-Isolation (!(Test-Path -LiteralPath $script:StateRoot)) 'No real local-state storage may be created.'
    Assert-Isolation (!(Test-Path -LiteralPath (Join-Path $ownedRoot 'Forge.MobileRelayHook.ps1'))) 'Missing mobile module must never be fabricated.'
}
function Stop-IsolationBoundary([string]$Kind,[string]$Name){
    $script:BoundaryHits.Add([pscustomobject]@{kind=$Kind;name=$Name})
    throw ('UNEXPECTED_BOUNDARY_DISPATCH: '+$Kind+': '+$Name)
}
# Named failure probes, NOT a complete network firewall or actual transports.
# They intentionally do not provide generation-binding helpers or research UI.
function Start-ForgeMobileSyncIfAuthorized {Stop-IsolationBoundary 'mobile' 'Start-ForgeMobileSyncIfAuthorized'}
function Invoke-ForgeApi {Stop-IsolationBoundary 'supabase' 'Invoke-ForgeApi'}
function Get-ZazzleResearchSample {Stop-IsolationBoundary 'source' 'Get-ZazzleResearchSample'}
function New-ForgeLocalAIJsonRequest {Stop-IsolationBoundary 'model' 'New-ForgeLocalAIJsonRequest'}
function Invoke-WebRequest {Stop-IsolationBoundary 'transport' 'Invoke-WebRequest'}
function Invoke-RestMethod {Stop-IsolationBoundary 'transport' 'Invoke-RestMethod'}
function Start-Process {Stop-IsolationBoundary 'process' 'Start-Process'}

try{
    $FrozenModuleRoot=(Resolve-Path -LiteralPath $FrozenModuleRoot).ProviderPath
    $ProviderModuleRoot=(Resolve-Path -LiteralPath $ProviderModuleRoot).ProviderPath
    $specs=@(
        @{name='Forge.BackendStatus.ps1';root=$ProviderModuleRoot;sha='d3c1bd722836a2a90ac3afa83d8d0c288f9d04a6be5ef1ee9a1990e0c876ab42';imports=@()},
        @{name='Forge.DomainActions.ps1';root=$ProviderModuleRoot;sha='da9926f484a2b6bf9efa299569b2a0ee120a1a23a2cfd4b8f75db547636af7c9';imports=@('Forge.OwnerLanguage.ps1')},
        @{name='Forge.PublicSignals.ps1';root=$ProviderModuleRoot;sha='92fc5d755871b543e510f129dcb4e204a571c3897d26ea7f80962e5abf74a392';imports=@()},
        @{name='Forge.AutoResearch.ps1';root=$ProviderModuleRoot;sha='e5e720604994e6473d93c6d1da2e58eeae9b582d08752ad6d42c80a8ee24a3cc';imports=@()},
        @{name='Forge.OwnerLanguage.ps1';root=$FrozenModuleRoot;sha='09a60b0037a3f5eb0f1f5a67c25349ce17c6006fe848fd83747c6f3625670802';imports=@('Forge.ColourReview.ps1','Forge.InstrumentalClaims.ps1')},
        @{name='Forge.ColourReview.ps1';root=$FrozenModuleRoot;sha='af477f0fa7a36c14faa3a76ec8213cd421a6542351c65766821c220697432966';imports=@()},
        @{name='Forge.InstrumentalClaims.ps1';root=$FrozenModuleRoot;sha='493737322484e9998155369a33b8e2c0a7c3ef62045af26b3a117d2c521e1f86';imports=@()}
    )
    $asts=@{}
    foreach($spec in $specs){
        $path=Join-Path $spec.root $spec.name;$copy=Join-Path $ownedRoot $spec.name
        $file=Get-Item -LiteralPath $path -Force
        Assert-Isolation ($file-is[IO.FileInfo]-and!($file.Attributes-band[IO.FileAttributes]::ReparsePoint)) ('Ordinary input file: '+$spec.name)
        $bytes=[IO.File]::ReadAllBytes($path)
        $source=[pscustomobject]@{name=$spec.name;path=$path;expected_sha256=$spec.sha;before_sha256=(Get-IsolationHash $bytes);after_sha256='';copy=$copy;copy_before_sha256='';copy_after_sha256=''}
        $script:Sources.Add($source)
        Assert-Isolation ($source.before_sha256-ceq$spec.sha) ('Pinned reviewed source bytes: '+$spec.name)
        [IO.File]::WriteAllBytes($copy,$bytes)
        $source.copy_before_sha256=Get-IsolationHash ([IO.File]::ReadAllBytes($copy))
        Assert-Isolation ($source.copy_before_sha256-ceq$source.before_sha256) ('Byte-exact owned copy: '+$spec.name)
        $asts[$spec.name]=Get-IsolationAst $copy
        $script:ImportAudit.Add((Assert-IsolationTopLevel $asts[$spec.name] $spec.name $spec.imports))
    }
    Invoke-IsolationCase 'Fail-closed top-level allowlist rejects automatic work' {
        foreach($bad in @(
            'function Safe {} ; Start-ForgeMobileSyncIfAuthorized',
            'function Safe {} ; $x=Invoke-ForgeApi',
            'function Safe {} ; if($true){Invoke-ForgePublicSignalsRefresh}',
            'function Safe {} ; & { Start-AutoResearch }',
            "function Safe {} ; . (Join-Path `$PSScriptRoot 'Forge.MobileRelayHook.ps1')",
            "function Safe {} ; . (Join-Path (`$PSScriptRoot + (Invoke-ForgeApi)) 'Forge.OwnerLanguage.ps1')",
            'param($x=(Invoke-ForgeApi)) function Safe {}',
            'begin { New-ForgeLocalAIJsonRequest } end { function Safe {} }',
            'trap { Invoke-ForgeApi }; function Safe {}',
            "#requires -Modules UnreviewedModule`nfunction Safe {}"
        )){Assert-IsolationRejectedAst $bad}
        # Even an approved literal import cannot be followed by hidden work.
        $tokens=$null;$errors=$null
        $text=". (Join-Path `$PSScriptRoot 'Forge.OwnerLanguage.ps1'); Start-AutoResearch; function Safe {}"
        $ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
        $refused=$false;try{$null=Assert-IsolationTopLevel $ast 'synthetic-import-negative' @('Forge.OwnerLanguage.ps1')}catch{$refused=$true}
        Assert-Isolation $refused 'Approved import does not allow a second executable statement.'
    }
    # All seven sources were gated before executing even the first import.
    $script:ModuleRoot=$ownedRoot
    $script:StateRoot=Join-Path $runRoot 'state-must-not-exist'
    foreach($name in @('Forge.BackendStatus.ps1','Forge.DomainActions.ps1','Forge.PublicSignals.ps1','Forge.AutoResearch.ps1')){
        . (Join-Path $ownedRoot $name)
    }
    Invoke-IsolationCase 'Actual byte-exact provider imports define functions without dispatch' {
        $allNames=@{}
        foreach($spec in $specs){
            foreach($definition in @($asts[$spec.name].EndBlock.Statements|Where-Object{$_-is[Management.Automation.Language.FunctionDefinitionAst]})){
                Assert-Isolation (!$allNames.ContainsKey($definition.Name)) ('No overlapping imported function: '+$definition.Name)
                $allNames[$definition.Name]=$true
                $loaded=Get-Command -Name $definition.Name -CommandType Function
                Assert-Isolation ($loaded.ScriptBlock.Ast.Extent.Text-ceq$definition.Body.Extent.Text) ('Exact actual imported body: '+$definition.Name)
                Assert-Isolation ([IO.Path]::GetFullPath($loaded.ScriptBlock.File)-ceq[IO.Path]::GetFullPath((Join-Path $ownedRoot $spec.name))) ('Imported only from owned closure: '+$definition.Name)
                $script:Loaded.Add([pscustomobject]@{name=$definition.Name;file=$spec.name;body_sha256=(Get-IsolationTextHash $definition.Body.Extent.Text)})
            }
        }
        Assert-Isolation ($script:ImportAudit.Count-eq7) 'Complete actual seven-file import closure was reviewed.'
        Assert-IsolationPaths
    }
    # Static closed command graph for the actual BackendStatus bodies under test.
    # This rejects unseen invocations even on an unexecuted conditional branch.
    $allowedCommands=@{
        'Set-ForgeLocalReadUnavailable'=@('Get-UiText');
        'Set-BackendBannerState'=@('Get-UiText');
        'Enter-LocalWorkbench'=@('Set-BackendBannerState','Apply-RoleUi','Load-OfflineQueueSnapshot','Show-HomeLanding','Update-LocalCoreBusinessSurfaces');
        'Get-ForgeLocalRefreshView'=@();
        'Restore-ForgeLocalRefreshView'=@('Apply-Filter','Set-Dirty','Set-PublicationDirty','Set-ForgeLocalReadUnavailable');
        'Refresh-LocalWorkbench'=@('Confirm','Get-ForgeLocalRefreshView','Read-LocalCoreState','Load-OfflineQueueSnapshot','Where-Object','Select-Object','New-Object','Open-ConceptItem','Update-LocalCoreBusinessSurfaces','Restore-ForgeLocalRefreshView','Update-PortfolioPipelineSurface','Get-UiText','Write-AppLog','Show-Error')
    }
    foreach($entry in $allowedCommands.GetEnumerator()){
        $definition=@($asts['Forge.BackendStatus.ps1'].EndBlock.Statements|Where-Object{$_-is[Management.Automation.Language.FunctionDefinitionAst]-and$_.Name-ceq$entry.Key})
        Assert-Isolation ($definition.Count-eq1) ('One actual path function: '+$entry.Key)
        foreach($call in @($definition[0].Body.FindAll({param($node)$node-is[Management.Automation.Language.CommandAst]},$true))){
            $commandName=$call.GetCommandName()
            Assert-Isolation ($null-ne$commandName-and$entry.Value-ccontains$commandName-and$call.InvocationOperator-eq[Management.Automation.Language.TokenKind]::Unknown) ('Reviewed direct command in '+$entry.Key+': '+$call.Extent.Text)
        }
    }

    # EXPLICIT UI / LOCAL-STATE DEPENDENCY DOUBLES. No WPF, real core read,
    # queue storage, credentials, log files, or business-surface implementation.
    function Get-UiText([string]$Key,[string]$Fallback){return $Fallback}
    function Apply-RoleUi {$script:Calls.role++}
    function Show-HomeLanding([bool]$Visible){$script:Calls.home++}
    function Read-LocalCoreState {
        $script:Calls.read++
        if($script:FailAt-ceq'read'){throw 'SYNTHETIC_READ_FAILURE'}
        return [pscustomobject]@{synthetic_state=$true}
    }
    function Load-OfflineQueueSnapshot($State){
        $script:Calls.load++
        if($script:FailAt-ceq'entry-load'){throw 'SYNTHETIC_ENTRY_LOAD_FAILURE'}
        $script:Queue=@($script:NextQueue);$script:OfflineSnapshotMode='synthetic-loaded'
        if($script:FailAt-ceq'queue-unavailable'){$script:QueueSnapshotCoreUnavailable=$true}
        return $script:Queue.Count
    }
    function Open-ConceptItem($Item,[bool]$Forced){
        $script:Calls.open++
        $script:Current=[pscustomobject]@{concept=[pscustomobject]@{concept_key=$Item.concept_key};marker='synthetic-reopened'}
        $script:TitleBox.Text='synthetic reopened title'
        if($script:FailAt-ceq'open'){return $false}
        return $true
    }
    function Update-LocalCoreBusinessSurfaces {
        $script:Calls.surface++
        if($script:FailAt-ceq'surface'){throw 'SYNTHETIC_SURFACE_FAILURE'}
    }
    function Update-PortfolioPipelineSurface {$script:Calls.portfolio++}
    function Apply-Filter {$script:Calls.filter++}
    function Set-Dirty([bool]$Value){$script:Dirty=$Value}
    function Set-PublicationDirty([bool]$Value){$script:PublicationDirty=$Value}
    function Confirm([string]$Text){$script:Calls.confirm++;return $script:ConfirmResult}
    function Write-AppLog([string]$Level,[string]$Message){$script:Calls.log++}
    function Show-Error([string]$Message){$script:Calls.error++}
    $script:FieldNames=@('TitleBox','HookBox','ConceptTextBox','BuyerBox','PurchaseBox','DifferentiationBox','VisualBox','SpecBox','ReasonBox','PublicationTitleBox','PublicationBrandBox','PublicationBullet1Box','PublicationBullet2Box','PublicationDescriptionBox','PublicationKeywordsBox','PublicationReasonBox','ConceptTitle','ConceptMeta','OverviewHook','OverviewConcept','OverviewBuyer','OverviewWhy','OverviewDifferent','OverviewVisual','OverviewMeaning','OverviewStatus','OverviewWarnings','OverviewNext')
    $script:AuthorityNames=@('GenerateButton','LocalApproveBriefButton','LocalBuildPackageButton','LocalAcceptButton','AcceptButton','SaveVariantReviewButton','OwnerKeepButton','OwnerEditDecisionButton','OwnerRegenButton','OwnerSkipButton','OwnerClearDecisionButton')
    function Reset-IsolationFixture([bool]$Selected=$false,[bool]$Dirty=$false){
        $script:Calls=@{role=0;home=0;read=0;load=0;open=0;surface=0;portfolio=0;filter=0;confirm=0;log=0;error=0}
        $script:FailAt='';$script:ConfirmResult=$true
        foreach($name in @($script:FieldNames)+@($script:AuthorityNames)+@('BackendBanner','BackendBannerText','BackendRetryButton','LoginGrid','AppGrid','ActorText','BackendText','StatusText','PublicationLocaleBox','PublicationPreflight','DeliveryStatus','AcceptanceStatus','LocalCoreStatusText','SavePublicationButton')){
            Set-Variable -Name $name -Scope Script -Value ([pscustomobject]@{Text=('synthetic:'+ $name);IsEnabled=$true;IsReadOnly=$false;Visibility='Visible';Content='';SelectedItem='synthetic-en-US'})
        }
        $script:OwnerKey='synthetic-not-a-credential';$script:Session=[pscustomobject]@{synthetic=$true};$script:BackendVersion='synthetic';$script:ConnectionState='Local';$script:OfflineMode=$true
        $script:Busy=$false;$script:ConceptLoadInProgress=$false;$script:StageFilterCache='synthetic-cache'
        $script:Dirty=$Dirty;$script:PublicationDirty=$Dirty;$script:QueueSnapshotIssue=$null;$script:QueueSnapshotCoreUnavailable=$false
        $script:Current=if($Selected){[pscustomobject]@{concept=[pscustomobject]@{concept_key='synthetic-selected'};marker='original synthetic editor'}}else{$null}
        $script:RestoreSourceRevisionId='synthetic-restore';$script:Publication=[pscustomobject]@{marker='synthetic-publication'};$script:Delivery=[pscustomobject]@{marker='synthetic-delivery'};$script:ReviewWorkspace=[pscustomobject]@{marker='synthetic-review'};$script:LocalPublicationEditor=[pscustomobject]@{marker='synthetic-listing-editor'}
        $script:Queue=@([pscustomobject]@{concept_key='synthetic-old-queue'});$script:OfflineSnapshotMode='synthetic-original'
        $script:NextQueue=if($Selected){@([pscustomobject]@{concept_key='synthetic-selected'})}else{@()}
    }
    function Assert-IsolationPreserved($View,[bool]$KeepQueue=$false){
        foreach($field in $View.fields){
            Assert-Isolation ($field.control.Text-ceq$field.text) 'Unsaved text restored.'
            Assert-Isolation ($field.control.IsEnabled-eq$field.enabled-and$field.control.IsReadOnly-eq$field.readonly) 'Editor control flags restored.'
        }
        foreach($pair in @(@('Current','current'),@('Publication','publication'),@('Delivery','delivery'),@('ReviewWorkspace','review'),@('LocalPublicationEditor','editor'))){
            Assert-Isolation ([object]::ReferenceEquals((Get-Variable -Name $pair[0] -Scope Script -ValueOnly),$View.($pair[1]))) ('Original synthetic object restored: '+$pair[0])
        }
        Assert-Isolation ($script:RestoreSourceRevisionId-ceq$View.restore_source) 'Restore revision retained.'
        Assert-Isolation ($script:Dirty-eq$View.dirty-and$script:PublicationDirty-eq$View.publication_dirty) 'Unsaved edit flags retained.'
        Assert-Isolation ($PublicationLocaleBox.SelectedItem-ceq$View.locale_item-and$PublicationLocaleBox.IsEnabled-eq$View.locale_enabled) 'Listing locale retained.'
        if(!$KeepQueue){
            Assert-Isolation (($script:Queue|ConvertTo-Json -Depth 10 -Compress)-ceq($View.queue|ConvertTo-Json -Depth 10 -Compress)) 'Original queue restored.'
            Assert-Isolation ($script:OfflineSnapshotMode-ceq$View.snapshot_mode) 'Original queue mode restored.'
        }
        foreach($name in $script:AuthorityNames){Assert-Isolation (!(Get-Variable -Name $name -Scope Script -ValueOnly).IsEnabled) ('Failure does not restore authority: '+$name)}
        Assert-Isolation ($null-eq$script:StageFilterCache) 'Failed-read filter cache invalidated.'
        Assert-Isolation (!$script:Busy-and!$script:ConceptLoadInProgress) 'Temporary busy/loading flags restored.'
        Assert-IsolationPaths
    }
    Invoke-IsolationCase 'Fresh local entry clears capabilities without mobile or transport' {
        Reset-IsolationFixture
        Enter-LocalWorkbench
        Assert-Isolation ($null-eq$script:OwnerKey-and$null-eq$script:Session-and$null-eq$script:BackendVersion) 'Fresh entry clears server context.'
        Assert-Isolation ($script:ConnectionState-ceq'Local'-and$script:OfflineMode) 'Fresh entry remains local.'
        Assert-Isolation ($LoginGrid.Visibility-ceq'Collapsed'-and$AppGrid.Visibility-ceq'Visible'-and$BackendBanner.Visibility-ceq'Collapsed') 'Local shell visibility set.'
        Assert-Isolation ($ActorText.Text-ceq'Local'-and$BackendText.Text-ceq'Local'-and$StatusText.Text-ceq'Local workspace ready') 'Fresh local status is not a server connection.'
        Assert-Isolation ($script:Calls.load-eq1-and$script:Calls.read-eq0-and$script:Calls.surface-eq1-and$script:Calls.role-eq1-and$script:Calls.home-eq1) 'Only bounded local/UI dependencies called.'
        Assert-IsolationPaths
    }
    Invoke-IsolationCase 'Entry local-read exception does not start unrelated work' {
        Reset-IsolationFixture;$script:FailAt='entry-load';$caught=$false
        try{Enter-LocalWorkbench}catch{$caught=$_.Exception.Message-ceq'SYNTHETIC_ENTRY_LOAD_FAILURE'}
        Assert-Isolation $caught 'Actual entry propagates local dependency failure; no app recovery claim.'
        Assert-Isolation ($script:Calls.load-eq1-and$script:Calls.surface-eq0) 'Entry stops after failed load.'
        Assert-Isolation ($null-eq$script:OwnerKey-and$null-eq$script:Session) 'Failure cannot grant server context.'
        Assert-IsolationPaths
    }
    Invoke-IsolationCase 'Fresh empty refresh and repeated refresh remain local' {
        Reset-IsolationFixture
        Assert-Isolation (Refresh-LocalWorkbench) 'Fresh refresh succeeds with synthetic empty state.'
        Assert-Isolation (Refresh-LocalWorkbench) 'Repeat refresh succeeds without implicit dispatch.'
        Assert-Isolation ($script:Calls.read-eq2-and$script:Calls.load-eq2-and$script:Calls.open-eq0-and$script:Calls.surface-eq2) 'Each explicit refresh reads exactly once.'
        Assert-Isolation ($StatusText.Text-ceq'Local workspace refreshed') 'Local refresh status reported.'
        Assert-IsolationPaths
    }
    Invoke-IsolationCase 'Selected refresh follows the actual reopen path' {
        Reset-IsolationFixture $true $true
        Assert-Isolation (Refresh-LocalWorkbench) 'Selected refresh succeeds.'
        Assert-Isolation ($script:Calls.confirm-eq1-and$script:Calls.read-eq1-and$script:Calls.load-eq1-and$script:Calls.open-eq1) 'Confirm/read/load/reopen each occur once.'
        Assert-Isolation (!$script:Dirty-and!$script:PublicationDirty-and$script:Current.marker-ceq'synthetic-reopened') 'Confirmed refresh accepts only the local double result.'
        Assert-IsolationPaths
    }
    Invoke-IsolationCase 'Declined refresh preserves unsaved fields without reading state' {
        Reset-IsolationFixture $true $true;$script:ConfirmResult=$false
        $view=Get-ForgeLocalRefreshView;$before=$TitleBox.Text;$oldQueue=$script:Queue
        Assert-Isolation (!(Refresh-LocalWorkbench)) 'Declined refresh returns false.'
        Assert-Isolation ($script:Calls.confirm-eq1-and$script:Calls.read-eq0-and$script:Calls.load-eq0-and$script:Calls.surface-eq0) 'Decline performs no dependency work.'
        Assert-Isolation ($TitleBox.Text-ceq$before-and[object]::ReferenceEquals($script:Current,$view.current)-and$script:Dirty-and$script:PublicationDirty) 'Decline leaves editor and edits untouched.'
        Assert-Isolation ([object]::ReferenceEquals($script:Queue,$oldQueue)) 'Decline leaves original queue object untouched.'
        Assert-IsolationPaths
    }
    foreach($failure in @('read','queue-unavailable','open','surface')){
        Invoke-IsolationCase ('Failed '+$failure+' refresh preserves the actual captured editor') {
            Reset-IsolationFixture $true $true;$script:FailAt=$failure
            $view=Get-ForgeLocalRefreshView
            Assert-Isolation (!(Refresh-LocalWorkbench)) ('Failed '+$failure+' refresh returns false.')
            Assert-IsolationPreserved $view
            Assert-Isolation ($script:Calls.read-eq1) 'Failure never automatically retries the core read.'
            Assert-Isolation ($script:Calls.load-eq$(if($failure-ceq'read'){0}else{1})) 'Failure never automatically retries queue loading.'
            Assert-Isolation ($script:Calls.open-eq$(if($failure-in@('open','surface')){1}else{0})) 'Failure never automatically retries reopening.'
            Assert-Isolation ($script:Calls.error-eq$(if($failure-ceq'open'){0}else{1})) 'Already-reported reopen failure is not reported twice.'
            Assert-Isolation ($SavePublicationButton.IsEnabled) 'Preserved dirty listing remains a fenced save retry.'
        }
    }
    Invoke-IsolationCase 'Missing selected item keeps refreshed queue but preserves unsaved editor' {
        Reset-IsolationFixture $true $true
        $script:NextQueue=@([pscustomobject]@{concept_key='synthetic-different-item'})
        $view=Get-ForgeLocalRefreshView
        Assert-Isolation (!(Refresh-LocalWorkbench)) 'Missing selected item returns false.'
        Assert-IsolationPreserved $view $true
        Assert-Isolation ($script:Queue.Count-eq1-and$script:Queue[0].concept_key-ceq'synthetic-different-item'-and$script:OfflineSnapshotMode-ceq'synthetic-loaded') 'New verified synthetic queue retained for reselection.'
        Assert-Isolation ($script:Calls.open-eq0-and$script:Calls.filter-eq0-and$script:Calls.read-eq1) 'Missing item does not reopen, restore old queue, or retry.'
    }
}catch{$script:Fatal=$_.Exception.Message}
finally{
    # Always rehash actual inputs AND owned import bytes, including partial setup.
    foreach($source in $script:Sources){
        try{
            $source.after_sha256=Get-IsolationHash ([IO.File]::ReadAllBytes($source.path))
            $source.copy_after_sha256=Get-IsolationHash ([IO.File]::ReadAllBytes($source.copy))
            if($source.after_sha256-cne$source.before_sha256-or$source.copy_after_sha256-cne$source.before_sha256){throw 'Input or owned copy changed.'}
        }catch{
            $script:Cases.Add([pscustomobject]@{name=('Final source/copy preservation: '+$source.name);status='FAIL';detail=$_.Exception.Message})
        }
    }
    $failed=@($script:Cases|Where-Object{$_.status-cne'PASS'}).Count
    $status=if(!$script:Fatal-and$failed-eq0-and$script:Cases.Count-eq12-and$script:Sources.Count-eq7){'PASS'}else{'FAIL'}
    $receipt=[ordered]@{
        schema='forge.provider_isolation_receipt.v1';run_id=$RunId;status=$status;started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');
        scope='Actual seven-file definition-only imports and actual BackendStatus local entry/refresh bodies with explicit in-memory UI/local-state dependency doubles.';
        limitations=@('Not full Workbench/app/installed CI validation.','No research initializers, live source/model/mobile/Supabase calls, installs, or user PC.','Named probes are not a real transport firewall.','Business surfaces, queue/core persistence, UI events and generation bindings are not exercised.','Supervisor must fail process-tree timeout, nonzero exit, absent/stale/mismatched receipt.');
        fatal=$script:Fatal;checks=$script:CheckCount;case_count=$script:Cases.Count;cases=@($script:Cases.ToArray());
        sources=@($script:Sources.ToArray());imports=@($script:ImportAudit.ToArray());loaded_actual_functions=@($script:Loaded.ToArray());
        boundary_probe_hits=@($script:BoundaryHits.ToArray());owned_root=$runRoot;receipt=$receiptPath
    }
    [IO.File]::WriteAllText($receiptPath,($receipt|ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false)))
    Write-Host ('PROVIDER_ISOLATION_STATUS='+$status)
}
if($status-cne'PASS'){throw ('Provider isolation failed. Inspect fresh receipt: '+$receiptPath)}

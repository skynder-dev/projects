#requires -Version 7.5
[CmdletBinding()]
param(
    [string]$AppRoot=(Join-Path $PSScriptRoot '..\app\Merch_Forge_A5_Current'),
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory)][string]$EvidenceParent,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTestSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedInputManifestSha256
)
# Hosted Windows-only synthetic wiring regression. Never start Workbench.
# The caller pins this test and its manifest. Actual verified copies of Workbench and
# all 46 modules execute inside a fresh private root. Evidence is retained, not deleted.
# No PASS is emitted until UI cleanup, ownership and original/copy integrity checks finish.
# The external supervisor must require exit 0 + fresh matching PASS receipt and enforce
# a process-tree deadline. Kill, timeout, missing/partial/stale receipt are failures.
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$script:Assertions=New-Object 'Collections.Generic.List[string]'
$script:ForgeWiringErrors=New-Object 'Collections.Generic.List[string]'
$script:ForgeWiringSnapshots=New-Object 'Collections.Generic.List[object]'
$script:ForgeWiringIntegrity=New-Object 'Collections.Generic.List[object]'
$script:ForgeWiringStartedAt=[DateTime]::UtcNow.ToString('o')
$script:ForgeWiringPhase='setup'
$script:ForgeWiringStatus='BLOCKED'
$script:ForgeWiringExitCode=2
$script:ForgeWiringRunRoot=$null
$script:ForgeWiringClaimStream=$null
$script:ForgeWiringClaimPath=$null
$script:ForgeWiringClaimSha=''
$script:ForgeWiringExpectedOwner=$null
$script:ForgeWiringReceiptPath=$null
$script:ForgeWiringUiCompleted=$false
$script:ForgeWiringCleanupOk=$false
$script:ForgeWiringOwnershipOk=$false
$script:ForgeWiringExpectedInputs=49 # Workbench + 46 modules + test + input manifest
$script:ForgeWiringModuleNames=@();$originalModules=$null;$copiedModules=$null
$script:Window=$null;$script:WiringWindowClosed=$false
$script:LocalAITimer=$null;$script:LocalAIRequest=$null
function Assert-Wiring([bool]$Condition,[string]$Message){if(!$Condition){throw ('FAIL: '+$Message)};$script:Assertions.Add($Message)}
function Get-ReconciliationBlock([string]$Name){
    $pattern='(?s)# BEGIN NEW WORKBENCH RECONCILIATION '+[regex]::Escape($Name)+'\r?\n(.*?)# END NEW WORKBENCH RECONCILIATION '+[regex]::Escape($Name)
    $matches=[regex]::Matches($source,$pattern)
    if($matches.Count-ne1){throw ('Expected one integration block: '+$Name)}
    return $matches[0].Groups[1].Value
}
function Assert-ForgeWiringOrdinaryPath([string]$Path,[switch]$Directory){
    $full=[IO.Path]::GetFullPath($Path)
    if($full-cnotmatch'^[A-Za-z]:\\'-or$full.Substring(2).Contains(':')){throw 'Only ordinary local-drive paths are permitted for this test.'}
    $cursor=$full;$leaf=$true
    while($cursor){
        $item=Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
        if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw ('Redirected test path is forbidden: '+$cursor)}
        if(!$leaf-or$Directory){if($item-isnot[IO.DirectoryInfo]){throw ('Directory required: '+$cursor)}}
        elseif($item-isnot[IO.FileInfo]){throw ('Ordinary file required: '+$cursor)}
        $leaf=$false
        $parent=[IO.Directory]::GetParent($cursor)
        $cursor=if($null-eq$parent){$null}else{$parent.FullName}
    }
}
function Get-ForgeWiringByteHash([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Read-ForgeWiringBytes([string]$Path){
    Assert-ForgeWiringOrdinaryPath $Path
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $buffer=[IO.MemoryStream]::new()
    try{
        if($stream.Length-gt2MB){throw 'Test input exceeds its 2 MiB bound.'}
        $stream.CopyTo($buffer)
        if($buffer.Length-gt2MB){throw 'Test input grew beyond its 2 MiB bound.'}
        return ,$buffer.ToArray()
    }finally{$buffer.Dispose();$stream.Dispose()}
}
function Assert-ForgeWiringOwnedDirectory([string]$Directory){
    $full=[IO.Path]::GetFullPath($Directory)
    if($full-cne$script:ForgeWiringRunRoot-and!$full.StartsWith($script:ForgeWiringRunRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Test write escaped its owned run root.'}
    Assert-ForgeWiringOrdinaryPath $full -Directory
    $acl=Get-Acl -LiteralPath $script:ForgeWiringRunRoot -ErrorAction Stop
    if(!$acl.AreAccessRulesProtected-or$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cne$script:ForgeWiringExpectedOwner){throw 'Private test root ownership/ACL protection changed.'}
    $allow=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|Where-Object{$_.AccessControlType-eq[Security.AccessControl.AccessControlType]::Allow})
    if($allow.Count-ne1-or$allow[0].IdentityReference.Value-cne$script:ForgeWiringExpectedOwner-or($allow[0].FileSystemRights-band[Security.AccessControl.FileSystemRights]::FullControl)-ne[Security.AccessControl.FileSystemRights]::FullControl){throw 'Private test root access rules changed.'}
}
function Write-ForgeWiringNewFile([string]$Path,[byte[]]$Bytes){
    Assert-ForgeWiringOwnedDirectory ([IO.Path]::GetDirectoryName($Path))
    if(Test-Path -LiteralPath $Path){throw ('Existing test destination is never overwritten: '+$Path)}
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    Assert-ForgeWiringOrdinaryPath $Path
}
function Copy-ForgeWiringInput([string]$Name,[string]$Original,[string]$Copy,[string]$Expected){
    $bytes=Read-ForgeWiringBytes $Original;$actual=Get-ForgeWiringByteHash $bytes
    if($actual-cne$Expected){throw ('Pinned input hash mismatch: '+$Name)}
    Write-ForgeWiringNewFile $Copy $bytes
    $copyHash=Get-ForgeWiringByteHash (Read-ForgeWiringBytes $Copy)
    if($copyHash-cne$Expected){throw ('Copied input hash mismatch: '+$Name)}
    $script:ForgeWiringSnapshots.Add([pscustomobject]@{name=$Name;original_path=[IO.Path]::GetFullPath($Original);copy_path=[IO.Path]::GetFullPath($Copy);expected_sha256=$Expected;original_before_sha256=$actual;copy_before_sha256=$copyHash})
}
try {
    if($PSVersionTable.PSEdition-cne'Core'-or!$IsWindows){throw 'PowerShell Core 7.5+ on Windows is required.'}
    if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'The hosted supervisor must launch pwsh.exe -NoProfile -STA.'}
    $EvidenceParent=[IO.Path]::GetFullPath($EvidenceParent)
    Assert-ForgeWiringOrdinaryPath $EvidenceParent -Directory
    $script:ForgeWiringRunRoot=Join-Path $EvidenceParent ('forge-workbench-wiring-'+$RunId)
    if(Test-Path -LiteralPath $script:ForgeWiringRunRoot){throw 'Run root already exists. Use a fresh RunId; evidence is never reused or removed.'}
    # CreateDirectoryW fails atomically if the leaf already exists; Directory.CreateDirectory
    # alone would accept an existing directory after a check/create race.
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ForgeWiringNativeDirectory {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool CreateDirectoryW(string path, IntPtr securityAttributes);
}
'@
    if(![ForgeWiringNativeDirectory]::CreateDirectoryW($script:ForgeWiringRunRoot,[IntPtr]::Zero)){
        throw ('Exclusive run-root creation failed: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error())
    }
    Assert-ForgeWiringOrdinaryPath $script:ForgeWiringRunRoot -Directory
    $script:ForgeWiringClaimPath=Join-Path $script:ForgeWiringRunRoot 'ownership.json'
    $claim=[ordered]@{schema='forge.wpf_wiring_ownership.v1';run_id=$RunId;process_id=$PID;root=$script:ForgeWiringRunRoot;nonce=[guid]::NewGuid().ToString('N');started_at_utc=$script:ForgeWiringStartedAt}
    $claimBytes=[Text.Encoding]::UTF8.GetBytes(($claim|ConvertTo-Json -Depth 8 -Compress))
    $script:ForgeWiringClaimSha=Get-ForgeWiringByteHash $claimBytes
    $script:ForgeWiringClaimStream=[IO.File]::Open($script:ForgeWiringClaimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $script:ForgeWiringClaimStream.Write($claimBytes,0,$claimBytes.Length);$script:ForgeWiringClaimStream.Flush($true)
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    try{$sid=$identity.User;$script:ForgeWiringExpectedOwner=$sid.Value}finally{$identity.Dispose()}
    $acl=[Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false)
    $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit-bor[Security.AccessControl.InheritanceFlags]::ObjectInherit
    $rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,[Security.AccessControl.FileSystemRights]::FullControl,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
    $acl.AddAccessRule($rule);Set-Acl -LiteralPath $script:ForgeWiringRunRoot -AclObject $acl -ErrorAction Stop
    Assert-ForgeWiringOwnedDirectory $script:ForgeWiringRunRoot
    $script:ForgeWiringReceiptPath=Join-Path $script:ForgeWiringRunRoot ('receipt-'+$RunId+'.json')
    $inputsRoot=Join-Path $script:ForgeWiringRunRoot 'inputs'
    $copiedApp=Join-Path $inputsRoot 'app';$copiedModules=Join-Path $copiedApp 'Modules'
    foreach($directory in @($inputsRoot,$copiedApp,$copiedModules)){
        Assert-ForgeWiringOwnedDirectory ([IO.Path]::GetDirectoryName($directory))
        [void][IO.Directory]::CreateDirectory($directory);Assert-ForgeWiringOwnedDirectory $directory
    }
    $originalApp=[IO.Path]::GetFullPath($AppRoot);Assert-ForgeWiringOrdinaryPath $originalApp -Directory
    $originalModules=Join-Path $originalApp 'Modules';Assert-ForgeWiringOrdinaryPath $originalModules -Directory
    $originalManifest=Join-Path $PSScriptRoot 'WorkbenchReconciliationInputs.json'
    $script:ForgeWiringCopiedManifest=Join-Path $inputsRoot 'WorkbenchReconciliationInputs.json'
    Copy-ForgeWiringInput 'harness' $PSCommandPath (Join-Path $inputsRoot 'Test-WorkbenchReconciliationWpf.ps1') $ExpectedTestSha256
    Copy-ForgeWiringInput 'input_manifest' $originalManifest $script:ForgeWiringCopiedManifest $ExpectedInputManifestSha256
    $sealedInputs=Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString((Read-ForgeWiringBytes $script:ForgeWiringCopiedManifest))) -DateKind String
    $sourceModules=@(Get-ChildItem -LiteralPath $originalModules -File -Filter '*.ps1')
    if($sourceModules.Count-ne46-or@($sealedInputs.module_sha256.PSObject.Properties).Count-ne46){throw 'Exact 46-module sealed inventory required.'}
    $script:ForgeWiringModuleNames=@($sealedInputs.module_sha256.PSObject.Properties.Name|Sort-Object)
    Copy-ForgeWiringInput 'workbench' (Join-Path $originalApp 'MerchForgeWorkbench.ps1') (Join-Path $copiedApp 'MerchForgeWorkbench.ps1') ([string]$sealedInputs.candidate_workbench_sha256)
    foreach($property in $sealedInputs.module_sha256.PSObject.Properties){
        if($property.Name-cnotmatch'^Forge\.[A-Za-z.]+\.ps1$'-or[string]$property.Value-cnotmatch'^[0-9a-f]{64}$'){throw 'Invalid pinned module identity.'}
        Copy-ForgeWiringInput $property.Name (Join-Path $originalModules $property.Name) (Join-Path $copiedModules $property.Name) ([string]$property.Value)
    }
    Assert-Wiring ($script:ForgeWiringSnapshots.Count-eq$script:ForgeWiringExpectedInputs) 'All 49 pinned inputs copied with exact hashes into a private owned root'
    $AppRoot=$copiedApp;$workbenchPath=Join-Path $AppRoot 'MerchForgeWorkbench.ps1'
    $source=[Text.Encoding]::UTF8.GetString((Read-ForgeWiringBytes $workbenchPath)).TrimStart([char]0xfeff)
    $script:ForgeWiringPhase='wiring'
$tokens=$null;$parseErrors=$null
$workbenchAst=[Management.Automation.Language.Parser]::ParseFile($workbenchPath,[ref]$tokens,[ref]$parseErrors)
Assert-Wiring (@($parseErrors).Count-eq0) 'Candidate Workbench parses without executing startup'
function Get-WorkbenchFunction([string]$Name){
    $nodes=@($workbenchAst.FindAll({param($n) $n-is[Management.Automation.Language.FunctionDefinitionAst]-and$n.Name-ceq$Name},$false))
    if($nodes.Count-ne1){throw ('Expected one real Workbench function: '+$Name)}
    return $nodes[0].Extent.Text
}
# Execute only the dedicated early runtime block, never Workbench startup.
. ([scriptblock]::Create((Get-ReconciliationBlock 'RUNTIME')))
Assert-Wiring ($forgeRuntimeProbe.instant-is[string]) 'Core/DateKind direct-entry contract preserves timestamp text'
$script:ModuleRoot=Join-Path $AppRoot 'Modules'
$inputManifest=Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($script:ForgeWiringCopiedManifest)) -DateKind String
$moduleFiles=@(Get-ChildItem -LiteralPath $script:ModuleRoot -Filter '*.ps1' -File)
Assert-Wiring ($moduleFiles.Count-eq@($inputManifest.module_sha256.PSObject.Properties).Count) 'Exact sealed module inventory is present'
foreach($module in $moduleFiles){
    $expected=$inputManifest.module_sha256.PSObject.Properties[$module.Name]
    Assert-Wiring ($null-ne$expected-and(Get-FileHash -LiteralPath $module.FullName -Algorithm SHA256).Hash.ToLowerInvariant()-ceq[string]$expected.Value) ('Sealed module bytes: '+$module.Name)
    $tokens=$null;$parseErrors=$null
    $moduleAst=[Management.Automation.Language.Parser]::ParseFile($module.FullName,[ref]$tokens,[ref]$parseErrors)
    Assert-Wiring (@($parseErrors).Count-eq0) ('Actual module parses: '+$module.Name)
    # Imports may define functions, literal state, or dot-source another actual module.
    # Reject eager top-level command/process/network/timer work before importing anything.
    foreach($statement in $moduleAst.EndBlock.Statements){
        if($statement-is[Management.Automation.Language.FunctionDefinitionAst]){continue}
        if($statement-is[Management.Automation.Language.AssignmentStatementAst]){
            $calls=@($statement.Right.FindAll({param($n) $n-is[Management.Automation.Language.CommandAst]-or$n-is[Management.Automation.Language.InvokeMemberExpressionAst]},$true))
            if(!$calls.Count){continue}
            # The retained release-notes module computes a path only; it does not read it.
            if($module.Name-ceq'Forge.WhatsNew.ps1'-and$statement.Extent.Text-ceq'$script:WhatsNewPath = Join-Path $PSScriptRoot ''..\Data\Forge.WhatsNew.json'''){continue}
        }
        if($statement.Extent.Text-match'^\. \(Join-Path \$(?:script:ModuleRoot|PSScriptRoot) ''Forge\.[A-Za-z.]+\.ps1''\)$'){continue}
        throw ('Unexpected eager module statement: '+$module.Name+' line '+$statement.Extent.StartLineNumber)
    }
}
Assert-Wiring $true 'Module import ASTs contain no eager provider/source/model/timer calls'
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Net.Http
$script:StateRoot=Join-Path $script:ForgeWiringRunRoot 'state'
[void][IO.Directory]::CreateDirectory($script:StateRoot)
Assert-ForgeWiringOrdinaryPath $script:StateRoot -Directory
$script:LogRoot=Join-Path $script:StateRoot 'logs'
$script:RuntimeLogPath=Join-Path $script:LogRoot 'synthetic.log'
$script:Current=$null;$script:DiscoverSnapshot=$null;$script:Dirty=$false;$script:PublicationDirty=$false
$script:Busy=$false;$script:Locale='en';$script:Window=$null;$script:WiringWindowClosed=$false
$script:LocalCoreStatePath=Join-Path $script:StateRoot 'never-created-state.json'
$script:ConfirmAnswers=New-Object 'Collections.Generic.Queue[bool]'
$script:ConfirmPrompts=New-Object 'Collections.Generic.List[string]'
function Confirm([string]$Message,[string]$Title='Merch Forge'){
    $script:ConfirmPrompts.Add($Message)
    if(!$script:ConfirmAnswers.Count){throw 'Unexpected close confirmation: no synthetic answer supplied'}
    return $script:ConfirmAnswers.Dequeue()
}
function Click-Control($Control){
    $args=New-Object Windows.RoutedEventArgs ([Windows.Controls.Primitives.ButtonBase]::ClickEvent)
    $Control.RaiseEvent($args)
}
    . ([scriptblock]::Create((Get-ReconciliationBlock 'STATE')))
    # Import only the actual module statements selected from the real Workbench AST.
    $imports=@($workbenchAst.EndBlock.Statements|Where-Object{$_.Extent.Text-match'^\. \(Join-Path \$script:ModuleRoot ''Forge\.[A-Za-z.]+\.ps1''\)$'})
    Assert-Wiring ($imports.Count-ge30) 'Real Workbench import statements were selected, not synthetic providers'
    foreach($statement in $imports){. ([scriptblock]::Create($statement.Extent.Text))}
    foreach($name in @('Ensure-Dir','Write-AppLog','Get-PropertyValue','X','Invoke-ForgeWorkbenchCanonicalHold','Invoke-ForgeWorkbenchLocalEntry','Show-ForgeWorkbenchGenerationUnavailable','Refresh-Workbench')){
        . ([scriptblock]::Create((Get-WorkbenchFunction $name)))
    }
    $xamlMatches=[regex]::Matches($source,'(?s)\[xml\]\$xaml=@''\r?\n(.*?)\r?\n''@')
    Assert-Wiring ($xamlMatches.Count-eq1) 'Exactly one real Workbench XAML document was extracted'
    [xml]$xaml=$xamlMatches[0].Groups[1].Value
    $reader=New-Object Xml.XmlNodeReader $xaml
    try{$script:Window=[Windows.Markup.XamlReader]::Load($reader)}finally{$reader.Close()}
    . ([scriptblock]::Create((Get-ReconciliationBlock 'BINDINGS')))
    Assert-Wiring ($LocalAIPrompt-is[Windows.Controls.TextBox]-and$LocalAIStatus-is[Windows.Controls.TextBlock]) 'Prompt and status are actual bound WPF controls'
    Assert-Wiring ([object]::ReferenceEquals($LocalAIStatus.Parent,$LocalAIPanel)) 'Review status mounts directly in the real pinned Panel'
    Assert-Wiring ($null-eq(Get-Variable SemanticReviewExpander -Scope Script -ErrorAction SilentlyContinue)) 'Semantic mount sentinel is absent before initialization'
    Assert-Wiring ($null-eq(Get-Variable RejectedAIExpander -Scope Script -ErrorAction SilentlyContinue)) 'Rejected mount sentinel is absent before initialization'
    foreach($name in @('GenerateButton','CancelGenerationButton','GenerationStatus','StatusText')){Set-Variable -Name $name -Scope Script -Value (X $name)}
    . ([scriptblock]::Create((Get-ReconciliationBlock 'INITIALIZATION')))
    $Window.Add_Closed({$script:WiringWindowClosed=$true})
    Assert-Wiring ($LocalAITimer.IsEnabled-and$null-eq$LocalAIRequest) 'Completion timer starts with no model request'
    Assert-Wiring ($null-eq$AutoResearchTimer-and$null-eq$AutoResearchProcess) 'Provider helpers imported without research timer or process startup'
    Assert-Wiring ($RejectedAIExpander.Parent-eq$LocalAIPanel-and$SemanticReviewExpander.Parent-eq$LocalAIPanel) 'Actual module rejected and semantic controls mount in the pinned panel'
    $children=$LocalAIPanel.Children.Count
    Initialize-ForgeRejectedAIUI;Initialize-ForgeSemanticReviewUI
    Assert-Wiring ($LocalAIPanel.Children.Count-eq$children) 'Repeated review initialization does not duplicate controls'
    Assert-Wiring (!$SemanticReviewSubmit.IsEnabled-and$SemanticReviewOutcome.SelectedIndex-eq-1) 'Semantic review starts without a selected outcome or submit authority'
    Assert-Wiring ($null-eq$LastSemanticReviewUiReceipt-and$null-eq$LastLocalAISaveReceipt) 'Wiring did not create save or review receipts'
    # All clicks below are negative/idle paths that stop before transport or state saves.
    # Explicit local entry is reachable without backend Connect, with safe busy/dirty guards.
    $LocalEntryStatus.Text='synthetic busy sentinel';$script:Busy=$true
    Click-Control $LocalEntryButton
    Assert-Wiring ($LocalEntryStatus.Text-ceq'synthetic busy sentinel') 'Local-entry click is inert while busy'
    $script:Busy=$false;$script:Dirty=$true
    Click-Control $LocalEntryButton
    Assert-Wiring ($Dirty-and$LocalEntryStatus.Text-match'Save or discard') 'Local-entry click preserves existing unsaved edits'
    $script:ConnectionState='Local';$ConfirmAnswers.Enqueue($false);$before=$ConfirmPrompts.Count
    Refresh-Workbench
    Assert-Wiring ($Dirty-and$ConfirmPrompts.Count-eq$before+1-and$ConfirmPrompts[$before]-match'Refresh local workspace') 'Local refresh uses the actual local cancel guard without backend fallback'
    $script:Dirty=$false
    # Intentional UI-reference fault exercises the actual entry failure catch, not a provider stub.
    $script:LoginGrid=$null
    Click-Control $LocalEntryButton
    Assert-Wiring ($LocalEntryStatus.Text-match'No backend fallback was attempted'-and$null-eq$LocalAIRequest) 'A local-entry control failure is surfaced without backend/model fallback'
    $script:LoginGrid=X 'LoginGrid';$script:ConnectionState='Not connected';$script:OfflineMode=$false
    # Even if legacy role code enables these controls, their real callbacks are informational only.
    foreach($name in @('GenerateButton','CancelGenerationButton')){
        $pattern='\$'+$name+'\.Add_Click\(\{Show-ForgeWorkbenchGenerationUnavailable\}\)'
        $handlers=[regex]::Matches($source,$pattern)
        Assert-Wiring ($handlers.Count-eq1) ('One inert real generation callback: '+$name)
        . ([scriptblock]::Create($handlers[0].Value))
        $control=X $name;$control.IsEnabled=$true;$before=$ConfirmPrompts.Count
        Click-Control $control
        Assert-Wiring ($GenerationStatus.Text-match'Generation is unavailable'-and$ConfirmPrompts.Count-eq$before) ('Generation UI cannot confirm or dispatch: '+$name)
    }
    $capability=Initialize-GenerationWorkerBridge
    Assert-Wiring (!$capability.available-and$capability.code-ceq'matching_generation_worker_unavailable') 'Actual generation initializer returns explicit unavailable state without spool work'
    Click-Control $LocalAICreateButton
    Assert-Wiring ($null-eq$LocalAIRequest-and$LocalAIStatus.Text-match'4000') 'Create click reaches the real empty-prompt guard without transport'
    $LocalAIPrompt.Text='Synthetic instruction for negative wiring checks only'
    Click-Control $LocalAIReviseButton
    Assert-Wiring ($null-eq$LocalAIRequest-and$LocalAIStatus.Text-match'локальный черновик') 'Revise click refuses a missing local draft before transport'
    Click-Control $LocalAICanonicalHoldButton
    Assert-Wiring ($null-eq$LocalAIRequest-and!$CanonicalDesignExperiment-and$LocalAIStatus.Text-match'source-bound') 'Canonical action refuses a missing draft and leaves normal mode unchanged'
    $script:Current=[pscustomobject]@{local_research_draft=$true;concept=[pscustomobject]@{concept_key='rd-synthetic';current_revision_id='rev-synthetic'};draft=[pscustomobject]@{provenance=[pscustomobject]@{}}}
    Click-Control $LocalAICanonicalHoldButton
    Assert-Wiring ($null-eq$LocalAIRequest-and!$CanonicalDesignExperiment-and$LocalAIStatus.Text-match'bound source context') 'Canonical missing-source exception restores normal mode and starts no request'
    $script:Current=$null;$script:Dirty=$true
    Click-Control $LocalAICreateButton
    Assert-Wiring ($null-eq$LocalAIRequest-and$Dirty) 'Create click preserves unsaved edits and does not start transport'
    $script:Dirty=$false;$script:VisionReviewRequest=[pscustomobject]@{synthetic=$true}
    Click-Control $LocalAICreateButton
    Assert-Wiring ($null-eq$LocalAIRequest-and$LocalAIStatus.Text-match'vision') 'Vision-request exclusion guard is reachable under StrictMode'
    $script:VisionReviewRequest=$null
    # An inert request envelope tests actual Cancel disposal. HttpClient never sends.
    $cancel=[Threading.CancellationTokenSource]::new();$token=$cancel.Token
    $script:LocalAIRequest=[pscustomobject]@{Cancel=$cancel;Content=[Net.Http.StringContent]::new('synthetic');Client=[Net.Http.HttpClient]::new();Task=[Threading.Tasks.TaskCompletionSource[object]]::new().Task}
    $LocalAICreateButton.IsEnabled=$false;$LocalAIReviseButton.IsEnabled=$false;$LocalAICancelButton.IsEnabled=$true
    $LocalAICanonicalHoldButton.GetBindingExpression([Windows.UIElement]::IsEnabledProperty).UpdateTarget()
    Assert-Wiring (!$LocalAICanonicalHoldButton.IsEnabled) 'Canonical action follows the real active-request disabled state'
    Click-Control $LocalAICancelButton
    Assert-Wiring ($token.IsCancellationRequested-and$null-eq$LocalAIRequest-and!$LocalAICancelButton.IsEnabled) 'Cancel click cancels and releases the inert request without a save'
    Click-Control $LocalAICancelButton
    Complete-ForgeLocalAIRequest
    Assert-Wiring ($null-eq$LocalAIRequest-and$LocalAIPrompt.Text-ceq'Synthetic instruction for negative wiring checks only') 'Repeated cancel and idle completion preserve the prompt and start no retry'
    $SemanticReviewNote.Text='Synthetic owner note remains in memory'
    Click-Control $SemanticReviewOpen
    Assert-Wiring (!$SemanticReviewSubmit.IsEnabled-and$null-eq$SemanticReviewDisplayedSnapshot) 'Semantic open with no saved draft fails closed'
    Click-Control $SemanticReviewSubmit
    Assert-Wiring ($SemanticReviewStatus.Text-match'SEMANTIC_REVIEW_DISPLAY_REQUIRED'-and$null-eq$LastSemanticReviewUiReceipt) 'Semantic submit cannot record an undisplayed revision'
    Click-Control $SemanticReviewCancel
    Assert-Wiring ($SemanticReviewNote.Text-ceq'Synthetic owner note remains in memory'-and$SemanticReviewOutcome.SelectedIndex-eq-1) 'Semantic cancel retains the note and clears submission binding'
    $script:RejectedAIViewId='synthetic-missing-record'
    $RejectedAIEditor.Text='Synthetic unsaved rejected-copy edit'
    Assert-Wiring ($RejectedAIEditDirty-and$RejectedAIReviewStatus.Text-match'КОПИЯ НЕ СОХРАНЕНА') 'Actual rejected editor preserves dirty text when retained-copy save fails'
    Assert-Wiring (!(Test-Path -LiteralPath $LocalCoreStatePath)-and$null-eq$LastLocalAISaveReceipt) 'Negative wiring paths created no active draft state or save receipt'
    # Use actual WPF Closing events, but a deterministic owner-confirmation seam.
    # No Workbench ContentRendered, startup callback or ShowDialog was registered.
    $Window.ShowInTaskbar=$false;$Window.ShowActivated=$false;$Window.Opacity=0
    $Window.Show();$Window.Hide()
    Initialize-ForgeUnsavedCloseGuard $Window
    Initialize-ForgeUnsavedCloseGuard $Window
    $script:Dirty=$true;$script:PublicationDirty=$true
    $ConfirmAnswers.Enqueue($false);$before=$ConfirmPrompts.Count
    $Window.Close()
    Assert-Wiring ($ConfirmPrompts.Count-eq$before+1-and$ConfirmPrompts[$before]-match'rejected-proposal') 'Rejected-copy refusal cancels close before a second category prompt'
    Assert-Wiring ($RejectedAIEditor.Text-ceq'Synthetic unsaved rejected-copy edit'-and$RejectedAIEditDirty-and$Dirty-and$PublicationDirty) 'Cancelled close does not discard rejected or creative/publication text'
    $ConfirmAnswers.Enqueue($true);$ConfirmAnswers.Enqueue($false);$before=$ConfirmPrompts.Count
    $Window.Close()
    Assert-Wiring ($ConfirmPrompts.Count-eq$before+2-and$ConfirmPrompts[$before+1]-match'creative/publication') 'Separate rejected and creative/publication warnings each appear exactly once'
    $script:RejectedAIEditDirty=$false;$ConfirmAnswers.Enqueue($false);$before=$ConfirmPrompts.Count
    $Window.Close()
    Assert-Wiring ($ConfirmPrompts.Count-eq$before+1) 'Repeated close-guard initialization never duplicates the discard prompt'
    $script:Dirty=$false;$script:PublicationDirty=$false;$before=$ConfirmPrompts.Count
    $Window.Close()
    Assert-Wiring ($ConfirmPrompts.Count-eq$before-and!$LocalAITimer.IsEnabled-and$null-eq$LocalAIRequest) 'Clean close stops the completion timer without prompts or retries'
    Assert-Wiring ($ConfirmAnswers.Count-eq0) 'All synthetic close decisions were consumed exactly once'

    $script:ForgeWiringUiCompleted=$true
} catch {
    $script:ForgeWiringErrors.Add($_.Exception.ToString())
    $script:ForgeWiringStatus=if($script:ForgeWiringPhase-ceq'wiring'){'FAIL'}else{'BLOCKED'}
} finally {
    # Quiesce UI first; no synthetic evidence is deleted, moved or overwritten.
    $script:Dirty=$false;$script:PublicationDirty=$false;$script:RejectedAIEditDirty=$false
    try{
        if($null-ne$script:LocalAITimer){$script:LocalAITimer.Stop()}
        if($null-ne$script:LocalAIRequest){Stop-ForgeLocalAIRequest}
        if($null-ne$script:Window-and!$script:WiringWindowClosed){$script:Window.Close()}
        $script:ForgeWiringCleanupOk=$true
    }catch{$script:ForgeWiringErrors.Add('UI cleanup: '+$_.Exception.ToString());$script:ForgeWiringStatus='FAIL'}
    try{
        if($null-ne$script:ForgeWiringClaimStream){$script:ForgeWiringClaimStream.Dispose();$script:ForgeWiringClaimStream=$null}
        if($script:ForgeWiringRunRoot-and$script:ForgeWiringClaimSha-and$script:ForgeWiringExpectedOwner){
            Assert-ForgeWiringOwnedDirectory $script:ForgeWiringRunRoot
            if((Get-ForgeWiringByteHash (Read-ForgeWiringBytes $script:ForgeWiringClaimPath))-cne$script:ForgeWiringClaimSha){throw 'Exclusive ownership claim changed.'}
            $script:ForgeWiringOwnershipOk=$true
        }
    }catch{$script:ForgeWiringErrors.Add('Ownership integrity: '+$_.Exception.ToString());$script:ForgeWiringStatus='FAIL'}
    # Rehash both originals and actual executable copies after all UI callbacks stop.
    foreach($snapshot in $script:ForgeWiringSnapshots){
        $row=[ordered]@{name=$snapshot.name;original_path=$snapshot.original_path;copy_path=$snapshot.copy_path;expected_sha256=$snapshot.expected_sha256;original_before_sha256=$snapshot.original_before_sha256;copy_before_sha256=$snapshot.copy_before_sha256;original_after_sha256=$null;copy_after_sha256=$null;intact=$false}
        try{
            $row.original_after_sha256=Get-ForgeWiringByteHash (Read-ForgeWiringBytes $snapshot.original_path)
            $row.copy_after_sha256=Get-ForgeWiringByteHash (Read-ForgeWiringBytes $snapshot.copy_path)
            $row.intact=($row.original_after_sha256-ceq$snapshot.expected_sha256-and$row.copy_after_sha256-ceq$snapshot.expected_sha256)
            if(!$row.intact){throw ('Source/copy input changed: '+$snapshot.name)}
        }catch{$script:ForgeWiringErrors.Add('Input integrity: '+$_.Exception.ToString());$script:ForgeWiringStatus='FAIL'}
        $script:ForgeWiringIntegrity.Add([pscustomobject]$row)
    }
    $moduleInventoryOk=$false
    try{
        if($script:ForgeWiringModuleNames.Count-eq46-and$originalModules-and$copiedModules){
            foreach($directory in @($originalModules,$copiedModules)){
                Assert-ForgeWiringOrdinaryPath $directory -Directory
                $names=@(Get-ChildItem -LiteralPath $directory -File -Filter '*.ps1'|ForEach-Object{$_.Name}|Sort-Object)
                if(($names-join'|')-cne($script:ForgeWiringModuleNames-join'|')){throw 'Original/copied module inventory changed.'}
            }
            $moduleInventoryOk=$true
        }
    }catch{$script:ForgeWiringErrors.Add('Module inventory integrity: '+$_.Exception.ToString());$script:ForgeWiringStatus='FAIL'}
    $integrityOk=($moduleInventoryOk-and$script:ForgeWiringIntegrity.Count-eq$script:ForgeWiringExpectedInputs-and@($script:ForgeWiringIntegrity|Where-Object{!$_.intact}).Count-eq0)
    if($script:ForgeWiringUiCompleted-and$script:ForgeWiringCleanupOk-and$script:ForgeWiringOwnershipOk-and$integrityOk-and!$script:ForgeWiringErrors.Count){$script:ForgeWiringStatus='PASS';$script:ForgeWiringExitCode=0}
    elseif($script:ForgeWiringStatus-ceq'FAIL'){$script:ForgeWiringExitCode=1}else{$script:ForgeWiringStatus='BLOCKED';$script:ForgeWiringExitCode=2}
    # Last publication step, only after cleanup and every integrity outcome is known.
    # CreateNew means a stale/previous/partial receipt can never be replaced with PASS.
    if($script:ForgeWiringOwnershipOk-and$script:ForgeWiringReceiptPath){
        $receipt=[ordered]@{schema='forge.workbench_wpf_wiring_receipt.v1';run_id=$RunId;status=$script:ForgeWiringStatus;exit_code=$script:ForgeWiringExitCode;process_id=$PID;started_at_utc=$script:ForgeWiringStartedAt;finished_at_utc=[DateTime]::UtcNow.ToString('o');run_root=$script:ForgeWiringRunRoot;receipt_path=$script:ForgeWiringReceiptPath;expected_test_sha256=$ExpectedTestSha256;expected_input_manifest_sha256=$ExpectedInputManifestSha256;ownership_sha256=$script:ForgeWiringClaimSha;ui_assertions_completed=$script:ForgeWiringUiCompleted;cleanup_ok=$script:ForgeWiringCleanupOk;source_integrity_ok=$integrityOk;assertion_count=$script:Assertions.Count;checks=@($script:Assertions);inputs=@($script:ForgeWiringIntegrity);errors=@($script:ForgeWiringErrors);evidence_retained=$true;powershell=[string]$PSVersionTable.PSVersion;boundaries=@('Actual copied inputs only','No Workbench startup','No model or source requests','No real data','No generation/approval success paths','Supervisor must reject kill/timeout/missing receipt')}
        try{
            $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 12))
            Write-ForgeWiringNewFile $script:ForgeWiringReceiptPath $bytes
            Write-Output ('Receipt: '+$script:ForgeWiringReceiptPath)
        }catch{$script:ForgeWiringExitCode=3;[Console]::Error.WriteLine('Receipt publication failed; this invocation did not pass. '+$_.Exception.Message)}
    }else{
        $script:ForgeWiringExitCode=2
        [Console]::Error.WriteLine('BLOCKED: no proven private root for a receipt. Missing receipt must fail the supervising run.')
        foreach($errorText in $script:ForgeWiringErrors){[Console]::Error.WriteLine($errorText)}
    }
}
exit $script:ForgeWiringExitCode

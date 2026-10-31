# Native PowerShell only. Loads actual pinned product function ASTs, not module initializers.
# This is focused local acceptance withdrawal coverage, not durable-store or WPF QA.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageRoot,
    [Parameter(Mandatory=$true)][string]$PinsPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory=$true)][string]$RunRoot
)
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot)
$RunRoot=[IO.Path]::GetFullPath($RunRoot)
$started=[DateTime]::UtcNow.ToString('o')
function Get-TestHash([string]$Path) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
}
function Assert-TestPath([string]$Path,[bool]$Directory) {
    $item=Get-Item -LiteralPath $Path -Force
    if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw ('Redirected path rejected: '+$Path)}
    if([bool]$item.PSIsContainer-ne$Directory){throw ('Unexpected path type: '+$Path)}
    $cursor=if($Directory){[IO.DirectoryInfo]::new($item.FullName)}else{[IO.FileInfo]::new($item.FullName).Directory}
    while($null-ne$cursor){if(($cursor.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw ('Redirected ancestor rejected: '+$cursor.FullName)};$cursor=$cursor.Parent}
}
function Assert-True($Condition,[string]$Message){if(-not$Condition){throw $Message}}
function Assert-Equal($Expected,$Actual,[string]$Message){if($Expected-cne$Actual){throw ($Message+'; expected='+[string]$Expected+' actual='+[string]$Actual)}}
function Assert-Number([double]$Expected,$Actual,[string]$Message){if($null-eq$Actual-or[double]::IsNaN([double]$Actual)-or[double]::IsInfinity([double]$Actual)-or[math]::Abs($Expected-[double]$Actual)-gt0.000000001){throw ($Message+'; expected='+$Expected+' actual='+[string]$Actual)}}
function Test-Case([string]$Name,[scriptblock]$Body){
    try{& $Body;$script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';error=$null})}
    catch{$script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';error=$_.Exception.Message})}
}
Assert-TestPath $RunRoot $true
Assert-TestPath $PackageRoot $true
if(@([IO.Directory]::GetFileSystemEntries($RunRoot)).Count-ne0){throw 'Supervisor must provide a fresh, empty, private run root.'}
if($RunRoot-eq$PackageRoot-or$RunRoot.StartsWith($PackageRoot.TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Run root cannot be inside source package.'}
$claim=$null;$receiptStream=$null
try{
    $claim=[IO.File]::Open((Join-Path $RunRoot '.forge-local-reopen.claim'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $identity=[Text.Encoding]::UTF8.GetBytes($RunId);$claim.Write($identity,0,$identity.Length);$claim.Flush($true)
    $receiptStream=[IO.File]::Open((Join-Path $RunRoot 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $script:Cases=New-Object Collections.Generic.List[object]
    $loaded=New-Object Collections.Generic.List[object]
    $sourceBefore=[ordered]@{};$sourceAfter=[ordered]@{};$failure=$null;$unsupportedRuntime=$false;$dateKindAvailable=$false
    $testHash=Get-TestHash $PSCommandPath;$pinsHash=Get-TestHash $PinsPath
    $fixturePath=Join-Path $PSScriptRoot 'LocalReopenFixtures.json';$dependenciesPath=Join-Path $PSScriptRoot 'LocalReopenDependencies.json'
    $fixtureHash=Get-TestHash $fixturePath;$dependencyHash=Get-TestHash $dependenciesPath
    $preservedPath=Join-Path $RunRoot 'existing-synthetic-fixture.txt'
    [IO.File]::WriteAllText($preservedPath,'SYNTHETIC PRESERVATION SENTINEL - no existing fixture or original may be modified.',[Text.UTF8Encoding]::new($false))
    $preservedHash=Get-TestHash $preservedPath
    try{
        $jsonCommand=Get-Command 'Microsoft.PowerShell.Utility\ConvertFrom-Json' -ErrorAction SilentlyContinue
        $dateKindAvailable=($null-ne$jsonCommand-and$jsonCommand.Parameters.ContainsKey('DateKind'))
        $versionText=$PSVersionTable.PSVersion.ToString()
        if($PSVersionTable.PSEdition-cne'Core'-or$versionText-notmatch'^\d+\.\d+(?:\.\d+){0,2}$'-or$PSVersionTable.PSVersion.Major-lt7-or($PSVersionTable.PSVersion.Major-eq7-and$PSVersionTable.PSVersion.Minor-lt5)-or!$dateKindAvailable){$unsupportedRuntime=$true;throw 'Unsupported native host: PowerShell Core 7.5+ with explicit DateKind String is required.'}
        $pins=[IO.File]::ReadAllText($PinsPath)|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        Assert-Equal 'forge.local_reopen.pins.v1' $pins.schema 'Pinned source schema'
        Assert-Equal $testHash $pins.tests.'Test-ForgeLocalReopen.ps1' 'Pinned test hash'
        Assert-Equal $fixtureHash $pins.tests.'LocalReopenFixtures.json' 'Pinned fixture hash'
        Assert-Equal $dependencyHash $pins.tests.'LocalReopenDependencies.json' 'Pinned dependency hash'
        $dependencies=[IO.File]::ReadAllText($dependenciesPath)|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        foreach($source in $dependencies.functions.PSObject.Properties){
            $path=Join-Path $PackageRoot $source.Name;Assert-TestPath $path $false
            $hash=Get-TestHash $path;$sourceBefore[$source.Name]=$hash
            Assert-Equal $hash $pins.sources.($source.Name) ('Pinned source '+$source.Name)
            $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
            Assert-Equal 0 @($errors).Count ('Native parser errors in '+$source.Name)
            foreach($name in @($source.Value)){
                $matches=@($ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq$name},$true))
                Assert-Equal 1 $matches.Count ('Exactly one actual function '+$name)
                . ([scriptblock]::Create($matches[0].Extent.Text))
                $loaded.Add([pscustomobject]@{name=$name;source=$source.Name;start_line=$matches[0].Extent.StartLineNumber;end_line=$matches[0].Extent.EndLineNumber})
            }
        }
        $script:UiText=@{en=@{};ru=@{};es=@{}};$script:Locale='en';$script:SupportedLocales=@('en','ru','es')
        $script:ResearchDraftKeyPrefix='rd-';$script:ResearchDraftWorkflowState='research_draft'
        $script:ResearchDraftContentFields=@('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')
        $script:StateIndex=0;$script:InputHashes=[ordered]@{};$script:BoundaryAttempts=New-Object Collections.Generic.List[string]
        # Match the real Workbench strictness after receipt/input defaults exist.
        Set-StrictMode -Version 2.0
        function Json($Value){return (ConvertTo-Json -InputObject $Value -Depth 60 -Compress)}
        function Clone($Value){return (ConvertFrom-Json -DateKind String (Json $Value))}
        function Get-TestFixtureState {return (ConvertFrom-Json -DateKind String ([IO.File]::ReadAllText($script:FixtureStatePath)))}
        function Set-TestFixtureState($State){[IO.File]::WriteAllText($script:FixtureStatePath,(Json $State),[Text.UTF8Encoding]::new($false))}
        function Read-LocalCoreState {$script:ReadCount++;if($script:RejectRead){throw 'SYNTHETIC_READ_UNAVAILABLE'};return (Get-TestFixtureState)}
        function Write-LocalCoreState($State){
            $script:WriteAttempts++;if($script:BeforeWrite){& $script:BeforeWrite}
            if($script:RejectWrite){throw 'SYNTHETIC_STATE_CONFLICT'}
            $disk=Get-TestFixtureState
            if($State.state_revision-ne$disk.state_revision-or[string](Get-PropertyValue $State 'last_write_id')-cne[string](Get-PropertyValue $disk 'last_write_id')){throw 'SYNTHETIC_OPTIMISTIC_CONFLICT'}
            $script:WriteCount++;$State.state_revision++;Add-OrSetProperty $State 'last_write_id' ([guid]::NewGuid().ToString('N'));Set-TestFixtureState $State
            if($script:CommitThenThrow){throw 'SYNTHETIC_COMMITTED_THEN_VERIFICATION_ERROR'}
        }
        function Show-Error([string]$Message){$script:Errors.Add($Message)}
        function Confirm([string]$Message,[string]$Title){$script:Questions.Add($Message);if($script:OnConfirm){& $script:OnConfirm};if($script:Answers.Count-eq0){throw 'Unexpected confirmation.'};return $script:Answers.Dequeue()}
        function Set-PublicationDirty([bool]$Value){$script:PublicationDirty=$Value;if($script:RejectUi){throw 'SYNTHETIC_POSTCOMMIT_UI_FAILURE'}}
        function Format-LocalCheck([string]$Name,$Check,$Lc){return ($Name+':'+[string](Get-PropertyValue $Check 'state'))}
        function Load-LocalPublicationUi {$script:PublicationRefreshCount++}
        function Update-LocalCoreStatusUi {$script:StatusRefreshCount++}
        function Refresh-StageFilterIfActive {$script:StageRefreshCount++}
        function Test-LocalProductionProviderReady {return $false}
        function Write-AppLog([string]$Level,[string]$Message){$script:Logs.Add($Level+':'+$Message)}
        foreach($command in @('Invoke-ForgeApi','Load-Concept','Sync-LocalGenerationResults','Invoke-LocalCheckAutomation','Write-LocalCheckRequestBundle','New-ForgeBriefApprovalRecord','Start-LocalGenerationWorker','Invoke-ForgeLocalFlux','Start-Process','Invoke-WebRequest','Invoke-RestMethod','Invoke-Expression','Remove-Item','Copy-Item','Move-Item','Set-Content','Out-File','Add-Type')){
            Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("`$script:BoundaryAttempts.Add('$command');throw 'Unexpected external boundary: $command'"))
        }
        function New-Control {return [pscustomobject]@{Text='';IsEnabled=$true;ItemsSource=@();SelectedItems=@()}}
        function Reset-Test {
            $script:StateIndex++;$script:FixtureStatePath=Join-Path $RunRoot ('state-'+$script:StateIndex+'.json')
            $script:ReadCount=0;$script:WriteCount=0;$script:WriteAttempts=0;$script:PublicationRefreshCount=0;$script:StatusRefreshCount=0;$script:StageRefreshCount=0;$script:SetterAttempts=0
            $script:RejectRead=$false;$script:RejectWrite=$false;$script:RejectUi=$false;$script:CommitThenThrow=$false;$script:OnConfirm=$null;$script:BeforeWrite=$null
            $script:Errors=New-Object Collections.Generic.List[string];$script:Logs=New-Object Collections.Generic.List[string];$script:Questions=New-Object Collections.Generic.List[string];$script:Answers=New-Object Collections.Generic.Queue[bool]
            $script:Current=$null;$script:Dirty=$false;$script:PublicationDirty=$false;$script:Busy=$false;$script:ReviewWorkspace=$null;$script:Session=[pscustomobject]@{capabilities=[pscustomobject]@{accept=$false;edit=$false;review=$false;generate=$false}};$script:Locale='en'
            $script:LocalReopenTarget=$null;$script:LocalPublicationEditor=[pscustomobject]@{marker='synthetic editor'};$script:Publication=[pscustomobject]@{local_core=$true;workspace=[pscustomobject]@{current_revision_accepted=$true}}
            foreach($name in @('AcceptanceStatus','ReopenAcceptanceButton','AcceptButton','StartIterationSameButton','StartIterationEditButton','GenerateButton','SaveVariantReviewButton','SavePublicationButton','LocalBuildPackageButton','VariantList','AnalysisEvidence','AuditList','ReopenReasonBox','StatusText','LocalCoreStatusText','PublicationCreativeStatus','PublicationPreflight','DeliveryStatus','PublicationTitleBox')){Set-Variable -Scope Script -Name $name -Value (New-Control)}
            $script:ReopenReasonBox.Text='Owner found an error';$script:PublicationTitleBox.Text='Unsaved listing text'
            Set-TestFixtureState ([pscustomobject]@{schema='forge.local_core.v2';state_revision=7;last_write_id=('1'*32);sales_rows=@();sales_imports=@();publication_receipts=@();concepts=@();research_drafts=@();synthetic_only=$true})
        }
        function New-PreservedFile([string]$Suffix,[string]$Content){$path=Join-Path $RunRoot ('source-'+$script:StateIndex+$Suffix);[IO.File]::WriteAllText($path,$Content,[Text.UTF8Encoding]::new($false));$script:InputHashes[$path]=Get-TestHash $path;return $path}
        function Seed-Accepted([bool]$Research=$true) {
            Reset-Test;$key='rd-synthetic'
            $fields=[pscustomobject]@{title='Current saved idea';hook='Exact hook';concept_text='Exact idea';target_buyer='buyer';purchase_reason='reason';differentiation='difference';visual_direction_text='visual';production_spec=[pscustomobject]@{nested=[pscustomobject]@{dates=@('2026-01-02T03:04:05.1234000+05:45');empty=@();singleton=@('only');null_value=$null;enabled=$false;label='Пример';value=1.25}}}
            $hash=Get-ResearchDraftContentHash $key $fields;$revision=Clone $fields
            Add-OrSetProperty $revision 'revision_no' 2;Add-OrSetProperty $revision 'revision_id' 'rdrev-synthetic-2';Add-OrSetProperty $revision 'revision_hash' $hash
            $draft=[pscustomobject]@{concept_key=$key;status='draft';current_revision_no=2;current_revision_id=$revision.revision_id;current_revision_hash=$hash;revisions=@($revision);provenance=[pscustomobject]@{niche_name='synthetic'}}
            $concept=ConvertTo-ResearchDraftConcept $draft;$brief=New-ForgeGenerationBriefSnapshot $concept
            $art=New-PreservedFile '.artwork.bin' 'SYNTHETIC ARTWORK BYTES (not a decoded image)';$zip=New-PreservedFile '.archive.bin' 'SYNTHETIC ARCHIVE BYTES (not a verified ZIP)';$sha=Get-TestHash $art;$fp=New-LocalAcceptanceFingerprint $key $revision.revision_id $hash $sha
            $acceptance=[pscustomobject]@{acceptance_id='local-accept-original';concept_key=$key;concept_revision_id=$revision.revision_id;revision_hash=$hash;variant_id='local-artwork-1';asset_sha256=$sha;local_file_path=$art;accepted_at='2026-10-25T04:00:00.1234000+00:00';lineage_fingerprint=$fp;sync_state='local_only';source='local_artwork_import';provider_key='manual_artwork_bridge'}
            $lc=[pscustomobject]@{concept_key=$key;source_revision_id=$revision.revision_id;source_revision_hash=$hash;generation_brief_snapshot=$brief;generation_brief_sha256=(Get-ForgeBriefSha256 $brief);brief_approval=[pscustomobject]@{approval_id='existing-brief-approval';approved=$true;marker='fixture approval retained, not granted'};owner_decision='KEEP';owner_decision_revision_id=$revision.revision_id;owner_decision_revision_hash=$hash;owner_decision_at='2026-10-25T03:59:00+00:00';active_acceptance=$acceptance;publication=[pscustomobject]@{saved_at='2026-10-25T04:00:01+00:00';listing_title='Saved listing';keywords=@('one','two');accepted_artwork_sha256=$sha;acceptance_fingerprint=$fp;content_hash=('c'*64)};checks=(New-LocalCoreChecks $revision.revision_id $sha);artwork=@([pscustomobject]@{id='local-artwork-1';variant_index=1;accepted=$true;local_only=$true;local_file_path=$art;asset_sha256=$sha;concept_revision_id=$revision.revision_id;source_revision_hash=$hash;width_px=1;height_px=1});packages=@([pscustomobject]@{valid=$true;status='READY_FOR_MANUAL_UPLOAD';sha256=(Get-TestHash $zip);path=$zip;acceptance_fingerprint=$fp});review_history=@([pscustomobject]@{schema='forge.local_review_history.v1';id='prior';history_only=$true;context_sha256=('f'*64);captured_at='2026-10-20T04:00:00+00:00';reason='listing_changed';payload=[pscustomobject]@{source_revision_id='old';nested=[pscustomobject]@{date='2026-01-02T03:04:05.1234000+05:45';values=@('singleton')}}})}
            $lc.checks.visual.state='pass';$lc.checks.visual.note='Original exact evidence';$lc.checks.visual.authority_kind='owner_exact_accept';$lc.checks.visual.evidence_refs=@('sha256:'+ $sha)
            $s=Get-TestFixtureState;$s.concepts=@($lc);if($Research){$s.research_drafts=@($draft)};$s.publication_receipts=@([pscustomobject]@{concept_key=$key;product_id='PUBLISHED-ORIGINAL';package_sha256=(Get-TestHash $zip);history_marker='must stay byte-equivalent'});Set-TestFixtureState $s
            $script:Current=[pscustomobject]@{local_research_draft=$Research;concept=$concept};$script:VariantList.SelectedItems=@($lc.artwork[0])
            Update-AcceptanceControls
            Assert-True ($null-ne$script:LocalReopenTarget) 'Seed produces real displayed local target'
            return $script:LocalReopenTarget
        }
        function Assert-Throws([scriptblock]$Body,[string]$Pattern){$message='';try{& $Body}catch{$message=$_.Exception.Message};Assert-True ($message-like('*'+$Pattern+'*')) ('Expected refusal '+$Pattern+'; actual='+$message)}
        function Assert-NotWritten([string]$Hash){Assert-Equal 0 $script:WriteCount 'No committed write';Assert-Equal $Hash (Get-TestHash $script:FixtureStatePath) 'Saved bytes unchanged'}
        function Bump-SavedState([scriptblock]$Mutation){$s=Get-TestFixtureState;& $Mutation $s;$s.state_revision++;$s.last_write_id=[guid]::NewGuid().ToString('N');Set-TestFixtureState $s}
        function Commit-Reopen { $script:Answers.Enqueue($true);Reopen-CurrentAcceptance;Assert-Equal 0 $script:Errors.Count 'Actual Domain action succeeds';return (Get-TestFixtureState) }
        Test-Case 'local_owner_gate_and_real_domain_route_do_not_require_server_capability' {
            $target=Seed-Accepted;Assert-True (!(Has-Cap 'accept')) 'No server capability';Assert-True $ReopenAcceptanceButton.IsEnabled 'Real gate enabled';Assert-True (!$GenerateButton.IsEnabled-and!$StartIterationSameButton.IsEnabled-and!$StartIterationEditButton.IsEnabled) 'Not generation or server iteration'
            Assert-True ($AcceptanceStatus.Text.Contains($target.revision_id)-and$AcceptanceStatus.Text.Contains($target.artwork_sha256)-and$AcceptanceStatus.Text.Contains($target.acceptance_sha256)) 'Displayed exact identity'
            $s=Commit-Reopen;Assert-Equal 1 $script:WriteCount 'Real Domain route commits local action';Assert-Equal $null $s.concepts[0].active_acceptance 'Withdrawn'
        }
        Test-Case 'local_acceptance_on_nonresearch_concept_uses_local_route' {
            $target=Seed-Accepted $false;$s=Commit-Reopen;Assert-Equal $null $s.concepts[0].active_acceptance 'Local path on saved nonresearch concept';Assert-Equal 1 $script:WriteCount 'One local write'
        }
        Test-Case 'blank_reason_refused_before_confirmation_and_mutation' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$ReopenReasonBox.Text='  ';Reopen-CurrentAcceptance
            Assert-Equal 1 $script:Errors.Count 'Visible reason refusal';Assert-Equal 0 $script:Questions.Count 'No confirmation for blank reason';Assert-NotWritten $before
        }
        Test-Case 'cancel_preserves_acceptance_history_and_unsaved_listing' {
            $target=Seed-Accepted;$script:PublicationDirty=$true;$editor=Json $script:LocalPublicationEditor;$before=Get-TestHash $script:FixtureStatePath;$script:Answers.Enqueue($false);Reopen-CurrentAcceptance
            Assert-NotWritten $before;Assert-True $script:PublicationDirty 'Dirty marker retained';Assert-Equal $editor (Json $script:LocalPublicationEditor) 'Editor binding retained';Assert-Equal 0 $script:Errors.Count 'Cancel is not failure';Assert-True ($script:Questions[0].Contains('ONLY if withdrawal is saved')) 'Discard is contingent on commit'
        }
        Test-Case 'confirmation_binds_revision_artwork_acceptance_and_reason' {
            $target=Seed-Accepted;$script:Answers.Enqueue($false);Reopen-CurrentAcceptance;$q=$script:Questions[0]
            foreach($value in @($target.revision_id,$target.revision_hash,$target.artwork_sha256,$target.acceptance_sha256,$ReopenReasonBox.Text)){Assert-True ($q.Contains($value)) 'Confirmation includes exact identity/reason'}
            Assert-Equal 0 $script:WriteCount 'Canceled'
        }
        Test-Case 'stale_displayed_state_refused_before_dialog' {
            $target=Seed-Accepted;Bump-SavedState {param($s)$s.concepts[0].active_acceptance.acceptance_id='newer-acceptance'};$before=Get-TestHash $script:FixtureStatePath;Reopen-CurrentAcceptance
            Assert-Equal 1 $script:Errors.Count 'Stale displayed target refused';Assert-Equal 0 $script:Questions.Count 'No confirmation for different acceptance';Assert-NotWritten $before
        }
        Test-Case 'new_same_artwork_acceptance_during_confirmation_is_preserved' {
            $target=Seed-Accepted;$script:OnConfirm={Bump-SavedState {param($s)$s.concepts[0].active_acceptance.acceptance_id='accepted-again-same-artwork'}};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            $s=Get-TestFixtureState;Assert-Equal 'accepted-again-same-artwork' $s.concepts[0].active_acceptance.acceptance_id 'New same-artwork choice retained';Assert-Equal $target.artwork_sha256 $s.concepts[0].active_acceptance.asset_sha256 'Same artwork';Assert-Equal 0 $script:WriteCount 'Withdrawal no write';Assert-Equal 1 $script:Errors.Count 'Visible conflict'
        }
        Test-Case 'identical_legacy_acceptance_with_new_write_identity_is_preserved' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.concepts[0].active_acceptance.PSObject.Properties.Remove('acceptance_id');Set-TestFixtureState $s;Update-AcceptanceControls;$original=Json $s.concepts[0].active_acceptance
            $script:OnConfirm={Bump-SavedState {param($s)}};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal $original (Json (Get-TestFixtureState).concepts[0].active_acceptance) 'Identical legacy record retained';Assert-Equal 0 $script:WriteCount 'State write identity fences legacy instance'
        }
        Test-Case 'same_revision_changed_write_id_during_confirmation_is_preserved' {
            $target=Seed-Accepted;$script:OnConfirm={$s=Get-TestFixtureState;$s.last_write_id=('2'*32);Set-TestFixtureState $s};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal ('2'*32) (Get-TestFixtureState).last_write_id 'Same-revision newer write retained';Assert-Equal 0 $script:WriteCount 'No withdrawal'
        }
        Test-Case 'saved_brief_change_during_confirmation_is_preserved' {
            $target=Seed-Accepted;$script:OnConfirm={Bump-SavedState {param($s)$s.concepts[0].source_revision_id='new-revision'}};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal 'new-revision' (Get-TestFixtureState).concepts[0].source_revision_id 'New revision retained';Assert-Equal 0 $script:WriteCount 'No withdrawal'
        }
        Test-Case 'navigation_during_confirmation_preserves_new_view_and_state' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$script:OnConfirm={$script:Current=Clone $script:Current};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal 1 $script:Errors.Count 'Changed Current identity refused';Assert-NotWritten $before
        }
        Test-Case 'creative_edits_during_confirmation_are_not_discarded' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$script:OnConfirm={$script:Dirty=$true};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-True $script:Dirty 'Creative edits retained';Assert-NotWritten $before
        }
        Test-Case 'publication_dirty_change_during_confirmation_is_not_discarded' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$script:OnConfirm={$script:PublicationDirty=$true};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-True $script:PublicationDirty 'New listing edits retained';Assert-NotWritten $before
        }
        Test-Case 'busy_or_dirty_gates_disable_reopen_and_direct_action_refuses' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$script:Busy=$true;Update-AcceptanceControls;Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Busy disabled';Reopen-CurrentAcceptance;Assert-NotWritten $before
            $script:Busy=$false;$script:Dirty=$true;Update-AcceptanceControls;Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Dirty disabled';Reopen-CurrentAcceptance;Assert-NotWritten $before
        }
        Test-Case 'state_write_rejection_preserves_saved_and_unsaved_data' {
            $target=Seed-Accepted;$script:PublicationDirty=$true;$before=Get-TestHash $script:FixtureStatePath;$editor=$PublicationTitleBox.Text;$script:RejectWrite=$true;$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal 1 $script:WriteAttempts 'One attempted commit';Assert-NotWritten $before;Assert-True $script:PublicationDirty 'Dirty marker retained on failed write';Assert-Equal $editor $PublicationTitleBox.Text 'Unsaved editor text remains';Assert-Equal $null $script:LocalPublicationEditor 'Unverified binding not retained as authority';Assert-Equal 1 $script:Errors.Count 'Write failure visible'
        }
        Test-Case 'synthetic_write_race_is_not_retried_or_overwritten' {
            $target=Seed-Accepted;$script:BeforeWrite={Bump-SavedState {param($s)$s.concepts[0].active_acceptance.acceptance_id='racing-acceptance'}};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal 1 $script:WriteAttempts 'No retry';Assert-Equal 0 $script:WriteCount 'Mock optimistic fence rejected';Assert-Equal 'racing-acceptance' (Get-TestFixtureState).concepts[0].active_acceptance.acceptance_id 'Race preserved; actual store concurrency NOT established'
        }
        Test-Case 'success_revokes_current_authority_in_one_write' {
            $target=Seed-Accepted;$s=Commit-Reopen;$lc=$s.concepts[0]
            Assert-Equal 1 $script:WriteCount 'Single state commit';Assert-Equal $null $lc.active_acceptance 'Acceptance cleared';foreach($check in @('ip','visual','print','policy','metadata')){Assert-Equal 'needs_review' $lc.checks.$check.state 'Current evidence reset'}
            Assert-True (!$lc.artwork[0].accepted-and!$lc.packages[0].valid) 'Current flags revoked';Assert-Equal 'local_acceptance_reopened' $lc.packages[0].invalidation_reason 'Reason recorded';Assert-Equal '' $lc.publication.acceptance_fingerprint 'Listing acceptance binding cleared';Assert-Equal '' $lc.publication.accepted_artwork_sha256 'Listing artwork binding cleared'
        }
        Test-Case 'success_preserves_saved_idea_approval_owner_decision_and_revision' {
            $target=Seed-Accepted;$before=Get-TestFixtureState;$approval=Json $before.concepts[0].brief_approval;$draft=Json $before.research_drafts;$brief=Json $before.concepts[0].generation_brief_snapshot;$s=Commit-Reopen
            Assert-Equal $approval (Json $s.concepts[0].brief_approval) 'Existing idea approval unchanged, not regranted';Assert-Equal $draft (Json $s.research_drafts) 'No new revision';Assert-Equal $brief (Json $s.concepts[0].generation_brief_snapshot) 'Full brief unchanged';Assert-Equal 'KEEP' $s.concepts[0].owner_decision 'Idea decision unchanged'
        }
        Test-Case 'success_preserves_prior_history_and_full_withdrawn_evidence' {
            $target=Seed-Accepted;$before=Get-TestFixtureState;$prior=Json $before.concepts[0].review_history[0];$accept=Json $before.concepts[0].active_acceptance;$checks=Json $before.concepts[0].checks;$packages=Json $before.concepts[0].packages;$s=Commit-Reopen;$h=$s.concepts[0].review_history
            Assert-Equal 2 @($h).Count 'Append one historical event';Assert-Equal $prior (Json $h[0]) 'Prior historical payload unchanged';Assert-Equal $accept (Json $h[1].payload.active_acceptance) 'Exact withdrawn acceptance retained';Assert-Equal $checks (Json $h[1].payload.checks) 'Original checks retained';Assert-Equal $packages (Json $h[1].payload.packages) 'Prior package flags and records retained';Assert-True $h[1].history_only 'No authority from history';Assert-Equal 'Owner found an error' $h[1].owner_reason 'Exact owner reason retained'
        }
        Test-Case 'history_snapshot_is_detached_from_later_current_mutation' {
            $target=Seed-Accepted;$lc=(Get-TestFixtureState).concepts[0];$null=Preserve-ForgeLocalReviewHistory $lc 'artwork_acceptance_reopened' 'test reason';$snapshot=Json $lc.review_history[1].payload
            $lc.checks.visual.note='mutated current';$lc.publication.listing_title='mutated current';$lc.active_acceptance.acceptance_id='mutated current';$lc.packages[0].valid=$false
            Assert-Equal $snapshot (Json $lc.review_history[1].payload) 'No alias to current evidence'
        }
        Test-Case 'history_event_surfaces_owner_reason_without_restoring_authority' {
            $target=Seed-Accepted;$s=Commit-Reopen;$events=@(Get-ForgeLocalReviewHistoryEvents $s.concepts[0]);$event=@($events|Where-Object{$_.summary.Contains('Owner found an error')})
            Assert-Equal 1 $event.Count 'Reason visible in actual history projection';Assert-True $event[0].evidence.history_only 'Projection is historical';Assert-Equal $target.artwork_sha256 $event[0].evidence.artwork_sha256 'Exact historical artwork identity'
        }
        Test-Case 'success_preserves_artwork_archive_and_publication_receipts' {
            $target=Seed-Accepted;$before=Get-TestFixtureState;$receipt=Json $before.publication_receipts;$art=$before.concepts[0].artwork[0];$package=$before.concepts[0].packages[0];$s=Commit-Reopen
            Assert-Equal $receipt (Json $s.publication_receipts) 'Historical published receipts untouched';Assert-Equal $art.local_file_path $s.concepts[0].artwork[0].local_file_path 'Artwork reference retained';Assert-Equal $package.path $s.concepts[0].packages[0].path 'Archive reference retained';Assert-Equal $art.asset_sha256 (Get-TestHash $art.local_file_path) 'Artwork bytes intact';Assert-Equal $package.sha256 (Get-TestHash $package.path) 'Archive bytes intact';Assert-Equal 'Saved listing' $s.concepts[0].publication.listing_title 'Saved listing text retained'
        }
        Test-Case 'successful_withdrawal_clears_unsaved_listing_only_after_commit' {
            $target=Seed-Accepted;$script:PublicationDirty=$true;$s=Commit-Reopen
            Assert-True (!$script:PublicationDirty) 'Dirty flag cleared on success';Assert-Equal $null $script:LocalPublicationEditor 'Stale editor binding removed';Assert-True (!$script:Publication.workspace.current_revision_accepted) 'UI publication authority false';Assert-Equal 1 $script:WriteCount 'One commit'
        }
        Test-Case 'saved_reload_has_no_current_acceptance_or_delivery_readiness' {
            $target=Seed-Accepted;$s=Commit-Reopen;$script:Current=$null;$script:LocalReopenTarget=$null;$fresh=Get-TestFixtureState;$script:Current=[pscustomobject]@{local_research_draft=$true;concept=(ConvertTo-ResearchDraftConcept $fresh.research_drafts[0])};Update-AcceptanceControls
            Assert-Equal $null $script:LocalReopenTarget 'No target after detached disk reload';Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Reopen disabled after reload';$readiness=Get-LocalDeliveryReadiness $fresh.concepts[0] $fresh;Assert-True (!$readiness.ready) 'Actual readiness denies missing acceptance';Assert-Equal 'accepted_artwork_required' $readiness.reason 'No acceptance is authoritative blocker'
        }
        Test-Case 'postcommit_ui_failure_cannot_restore_current_readiness' {
            $target=Seed-Accepted;$script:RejectUi=$true;$s=Commit-Reopen
            Assert-Equal $null $s.concepts[0].active_acceptance 'Acceptance absent despite UI failure';Assert-True (!$s.concepts[0].packages[0].valid) 'Packages remain invalid';Assert-True (!$script:Publication.workspace.current_revision_accepted) 'UI authority cleared before failure';Assert-True (!$ReopenAcceptanceButton.IsEnabled-and!$SavePublicationButton.IsEnabled-and!$LocalBuildPackageButton.IsEnabled) 'Unsafe controls disabled';Assert-True (@($script:Logs|Where-Object{$_-like'*withdrawal was saved*'}).Count-eq1) 'Saved result distinguished from rendering failure'
        }
        Test-Case 'postcommit_button_setter_failure_does_not_report_rollback' {
            $target=Seed-Accepted;$script:ReopenAcceptanceButton=New-Object PSObject
            $script:ReopenAcceptanceButton|Add-Member -MemberType ScriptProperty -Name IsEnabled -Value {return $true} -SecondValue {param($Value)$script:SetterAttempts++;throw 'SYNTHETIC_BUTTON_SETTER_FAILURE'}
            $s=Commit-Reopen
            Assert-Equal $null $s.concepts[0].active_acceptance 'Withdrawal committed despite one failing control';Assert-Equal 1 $script:WriteCount 'No second mutation';Assert-True ($script:SetterAttempts-ge1) 'Failing setter exercised';Assert-True (!$SavePublicationButton.IsEnabled-and!$LocalBuildPackageButton.IsEnabled) 'Other controls disabled independently';Assert-True ($LocalCoreStatusText.Text.Contains('withdrawn')) 'Stale ready label removed';Assert-True ($StatusText.Text.Contains('withdrawn')) 'Domain reports saved withdrawal, not rollback'
        }
        Test-Case 'commit_then_throw_is_unverified_not_assumed_rollback_or_retried' {
            $target=Seed-Accepted;$script:PublicationDirty=$true;$editor=$PublicationTitleBox.Text;$script:CommitThenThrow=$true;$script:Answers.Enqueue($true);Reopen-CurrentAcceptance;$s=Get-TestFixtureState
            Assert-Equal 1 $script:WriteAttempts 'No retry';Assert-Equal 1 $script:WriteCount 'Synthetic commit did occur';Assert-Equal $null $s.concepts[0].active_acceptance 'Saved withdrawal retained';Assert-Equal 2 @($s.concepts[0].review_history).Count 'History appended once';Assert-True (!$script:Publication.workspace.current_revision_accepted) 'No stale UI authority';Assert-True $script:PublicationDirty 'Dirty flag preserved while outcome is uncertain';Assert-Equal $editor $PublicationTitleBox.Text 'Unsaved text preserved';Assert-True ($AcceptanceStatus.Text.Contains('unverified')) 'Outcome explicitly unverified';Assert-Equal 1 $script:Errors.Count 'Verification error surfaced'
        }
        Test-Case 'repeated_click_does_not_append_second_withdrawal_or_call_server' {
            $target=Seed-Accepted;$s=Commit-Reopen;$before=Get-TestHash $script:FixtureStatePath;Reopen-CurrentAcceptance
            Assert-Equal 1 $script:WriteCount 'Still exactly one write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'No duplicate event';Assert-Equal 1 $script:Questions.Count 'Only original confirmation'
        }
        Test-Case 'missing_artwork_file_does_not_trap_existing_acceptance' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.concepts[0].active_acceptance.local_file_path=Join-Path $RunRoot 'missing-artwork';$s.concepts[0].artwork[0].local_file_path=$s.concepts[0].active_acceptance.local_file_path;Set-TestFixtureState $s;Update-AcceptanceControls;$s=Commit-Reopen
            Assert-Equal $null $s.concepts[0].active_acceptance 'Owner can withdraw even if exact file is unavailable'
        }
        Test-Case 'legacy_acceptance_without_instance_id_can_be_explicitly_withdrawn' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.concepts[0].active_acceptance.PSObject.Properties.Remove('acceptance_id');Set-TestFixtureState $s;Update-AcceptanceControls;$s=Commit-Reopen
            Assert-Equal $null $s.concepts[0].active_acceptance 'Legacy exact local acceptance handled';Assert-Equal 1 $script:WriteCount 'One explicit write'
        }
        Test-Case 'legacy_absent_write_token_does_not_trap_acceptance' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.PSObject.Properties.Remove('last_write_id');Set-TestFixtureState $s;Update-AcceptanceControls;Assert-True $ReopenAcceptanceButton.IsEnabled 'Legacy absent token enabled';$s=Commit-Reopen;Assert-Equal $null $s.concepts[0].active_acceptance 'Withdrawn without unrelated migration write'
        }
        Test-Case 'legacy_null_write_token_does_not_trap_acceptance' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.last_write_id=$null;Set-TestFixtureState $s;Update-AcceptanceControls;Assert-True $ReopenAcceptanceButton.IsEnabled 'Legacy null token enabled';$s=Commit-Reopen;Assert-Equal $null $s.concepts[0].active_acceptance 'Withdrawn'
        }
        Test-Case 'legacy_empty_write_token_does_not_trap_acceptance' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.last_write_id='';Set-TestFixtureState $s;Update-AcceptanceControls;Assert-True $ReopenAcceptanceButton.IsEnabled 'Legacy empty token enabled';$s=Commit-Reopen;Assert-Equal $null $s.concepts[0].active_acceptance 'Withdrawn'
        }
        Test-Case 'mixed_case_write_token_is_compared_exactly' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.last_write_id=('Aa'*16);Set-TestFixtureState $s;Update-AcceptanceControls;Assert-True $ReopenAcceptanceButton.IsEnabled 'Valid mixed-case token enabled'
            $script:OnConfirm={$s=Get-TestFixtureState;$s.last_write_id=$s.last_write_id.ToLowerInvariant();Set-TestFixtureState $s};$script:Answers.Enqueue($true);Reopen-CurrentAcceptance;Assert-Equal 0 $script:WriteCount 'Case-changed write identity is fenced';Assert-Equal ('aa'*16) (Get-TestFixtureState).last_write_id 'Changed token preserved'
        }
        Test-Case 'nonstring_write_token_is_rejected_without_mutation' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.last_write_id=123;Set-TestFixtureState $s;$before=Get-TestHash $script:FixtureStatePath;Update-AcceptanceControls
            Assert-Equal $null $script:LocalReopenTarget 'Invalid token not coerced';Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Invalid token disables action';Assert-NotWritten $before
        }
        Test-Case 'unavailable_state_disables_reopen_without_saved_changes' {
            $target=Seed-Accepted;$before=Get-TestHash $script:FixtureStatePath;$script:RejectRead=$true;Update-AcceptanceControls
            Assert-Equal $null $script:LocalReopenTarget 'No stale captured target';Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Read failure disables action';Assert-NotWritten $before
        }
        Test-Case 'duplicate_saved_concept_is_not_a_withdrawal_target' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.concepts=@($s.concepts[0],(Clone $s.concepts[0]));Set-TestFixtureState $s;$before=Get-TestHash $script:FixtureStatePath;Update-AcceptanceControls
            Assert-Equal $null $script:LocalReopenTarget 'Ambiguous local target refused';Assert-True (!$ReopenAcceptanceButton.IsEnabled) 'Cannot withdraw arbitrary first row';Assert-NotWritten $before
        }
        Test-Case 'corrupt_history_prevents_withdrawal_without_losing_originals' {
            $target=Seed-Accepted;$s=Get-TestFixtureState;$s.concepts[0].review_history='corrupt-original';Set-TestFixtureState $s;Update-AcceptanceControls;$before=Get-TestHash $script:FixtureStatePath;$script:Answers.Enqueue($true);Reopen-CurrentAcceptance
            Assert-Equal 1 $script:Errors.Count 'Preservation refusal visible';Assert-NotWritten $before
        }
        Test-Case 'forbidden_network_generation_and_reapproval_boundaries_not_called' {
            Assert-Equal 0 $script:BoundaryAttempts.Count ('Unexpected guarded calls: '+($script:BoundaryAttempts-join','))
        }
        $actualNames=@($script:Cases|ForEach-Object{$_.name});Assert-Equal ($pins.expected_case_names-join'|') ($actualNames-join'|') 'Exact ordered native cases'
        $actualFunctions=@($loaded|ForEach-Object{$_.name});Assert-Equal ($pins.expected_function_names-join'|') ($actualFunctions-join'|') 'Exact actual function identity contract'
    } catch {$failure=$_.Exception.Message}
    finally{
        try{
            foreach($source in $pins.sources.PSObject.Properties){$sourceAfter[$source.Name]=Get-TestHash (Join-Path $PackageRoot $source.Name)}
            if($sourceBefore.Count-ne$sourceAfter.Count){throw 'Source count changed during native execution.'};foreach($key in $sourceBefore.Keys){if($sourceBefore[$key]-cne$sourceAfter[$key]){throw ('Source copy changed during native execution: '+$key)}}
            if((Get-TestHash $PSCommandPath)-cne$testHash-or(Get-TestHash $PinsPath)-cne$pinsHash-or(Get-TestHash $fixturePath)-cne$fixtureHash-or(Get-TestHash $dependenciesPath)-cne$dependencyHash){throw 'Test or fixture inputs changed during native execution.'}
            foreach($path in $script:InputHashes.Keys){if((Get-TestHash $path)-cne$script:InputHashes[$path]){throw ('Synthetic original artwork/archive bytes changed: '+$path)}}
            if((Get-TestHash $preservedPath)-cne$preservedHash){throw 'Synthetic preservation sentinel changed.'}
        }catch{if($null-eq$failure){$failure=$_.Exception.Message}}
        $failed=@($script:Cases|Where-Object{$_.status-cne'PASS'}).Count
        if($failed-gt0-and$null-eq$failure){$failure=([string]$failed+' native case(s) failed.')}
        if($script:Cases.Count-ne39-and$null-eq$failure){$failure='Exactly 39 native cases must run.'}
        $receipt=[ordered]@{
            schema='forge.local_reopen.native_receipt.v1';run_id=$RunId;status=$(if($unsupportedRuntime){'BLOCKED_UNSUPPORTED_NATIVE_RUNTIME'}elseif($null-eq$failure){'PASS'}else{'FAIL'});error=$failure
            started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');synthetic_only=$true
            powershell_version=$PSVersionTable.PSVersion.ToString();ps_edition=$PSVersionTable.PSEdition;date_kind_string_available=$dateKindAvailable;minimum_powershell_core='7.5'
            run_root=$RunRoot;package_copy_root=$PackageRoot;test_sha256=$testHash;pins_sha256=$pinsHash;fixtures_sha256=$fixtureHash;dependencies_sha256=$dependencyHash
            source_hashes_before=$sourceBefore;source_hashes_after=$sourceAfter;loaded_actual_functions=@($loaded.ToArray());explicit_doubles=$dependencies.doubles
            preserved_artifact_hashes=$script:InputHashes;case_count=$script:Cases.Count;failed_case_count=$failed;cases=@($script:Cases.ToArray());synthetic_fixture_sha256=$preservedHash
            real_data_loaded=$false;app_launched=$false;model_calls=0;network_calls=0;remote_writes=0
            scope='Actual local Reopen identity, mutation, history, Domain action and control gates with synthetic JSON persistence and plain UI seams. Detached saved reload is not actual app restart. No full-app, WPF, actual durable-store/concurrency or artwork/ZIP authority claim.'
        }
        $writer=[IO.StreamWriter]::new($receiptStream,[Text.UTF8Encoding]::new($false),4096,$true)
        try{$writer.Write(($receipt|ConvertTo-Json -Depth 16));$writer.Flush();$receiptStream.Flush($true)}finally{$writer.Dispose()}
    }
    if($null-ne$failure){throw $failure}
    Write-Output ('Native focused suite passed; supervisor must independently validate '+(Join-Path $RunRoot 'receipt.json'))
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}

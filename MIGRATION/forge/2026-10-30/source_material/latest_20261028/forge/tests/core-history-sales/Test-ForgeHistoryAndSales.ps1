# Native PowerShell only. Loads actual pinned product function ASTs, not module initializers.
# This is focused history/restore/sales-identity coverage, not receipt authority or WPF QA.
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
    $claim=[IO.File]::Open((Join-Path $RunRoot '.forge-performance.claim'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $identity=[Text.Encoding]::UTF8.GetBytes($RunId);$claim.Write($identity,0,$identity.Length);$claim.Flush($true)
    $receiptStream=[IO.File]::Open((Join-Path $RunRoot 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $script:Cases=New-Object Collections.Generic.List[object]
    $loaded=New-Object Collections.Generic.List[object]
    $sourceBefore=[ordered]@{};$sourceAfter=[ordered]@{};$failure=$null;$unsupportedRuntime=$false;$dateKindAvailable=$false
    $testHash=Get-TestHash $PSCommandPath;$pinsHash=Get-TestHash $PinsPath
    $fixturePath=Join-Path $PSScriptRoot 'HistorySalesFixtures.json';$dependenciesPath=Join-Path $PSScriptRoot 'HistorySalesDependencies.json'
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
        Assert-Equal 'forge.core_history_sales.pins.v1' $pins.schema 'Pinned source schema'
        Assert-Equal $testHash $pins.tests.'Test-ForgeHistoryAndSales.ps1' 'Pinned test hash'
        Assert-Equal $fixtureHash $pins.tests.'HistorySalesFixtures.json' 'Pinned fixture hash'
        Assert-Equal $dependencyHash $pins.tests.'HistorySalesDependencies.json' 'Pinned dependency hash'
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
        $script:InputHashes=[ordered]@{};$script:FixtureIndex=0;$script:StateIndex=0
        function Get-TestFixtureState {return (ConvertFrom-Json -DateKind String ([IO.File]::ReadAllText($script:FixtureStatePath)))}
        function Set-TestFixtureState($State){[IO.File]::WriteAllText($script:FixtureStatePath,($State|ConvertTo-Json -Depth 60 -Compress),[Text.UTF8Encoding]::new($false))}
        function Read-LocalCoreState {$script:ReadCount++;return (Get-TestFixtureState)}
        function Write-LocalCoreState($State){if($script:RejectWrite){throw 'SYNTHETIC_STATE_CONFLICT'};$script:WriteCount++;Set-TestFixtureState $State}
        function Show-Error([string]$Message){$script:Errors.Add($Message)}
        function Confirm([string]$Message,[string]$Title){$script:Questions.Add($Message);if($script:OnConfirm){& $script:OnConfirm};if($script:Answers.Count-eq0){throw 'Unexpected confirmation.'};return $script:Answers.Dequeue()}
        function Set-Dirty([bool]$Value){$script:Dirty=$Value}
        function Set-PublicationDirty([bool]$Value){$script:PublicationDirty=$Value}
        function Select-MainTab([string]$Value){$script:SelectedTab=$Value}
        function Update-MainTabUi {}
        function Update-OwnerDecisionControls {}
        function Clear-DraftStaleConceptSurfaces {}
        function Write-AppLog {}
        function Update-LocalCoreBusinessSurfaces {$script:RefreshCount++}
        function Refresh-ResearchDraftQueue {$script:RefreshCount++}
        function Open-ResearchDraftItem($Item,[bool]$Force){if($script:RejectReopen){return $false};$d=Get-ResearchDraft $Item.concept_key;$script:Current=[pscustomobject]@{local_research_draft=$true;draft=$d;concept=(ConvertTo-ResearchDraftConcept $d)};return $true}
        function Test-LocalPublicationReceiptAuthority($State,$Receipt){return ((Get-PropertyValue $Receipt 'fixture_authority')-is[bool]-and$Receipt.fixture_authority)}
        function Get-ForgeOwnerLanguageReview {return [pscustomobject]@{synthetic_only=$true;approved=$false}}
        function ConvertFrom-ForgeProductionSpecJson([string]$Text){if(!$Text.TrimStart().StartsWith('{')){throw 'Expected synthetic object'};return (ConvertFrom-Json -DateKind String $Text)}
        foreach($command in @('Assert-ForgeRejectedSaveBinding','Read-ForgeRejectedProposal','Assert-ForgeAIFieldsForSave','Start-LocalGenerationWorker','Invoke-ForgeLocalFlux','Start-Process','Invoke-WebRequest','Invoke-RestMethod','Invoke-Expression','Remove-Item','Copy-Item','Move-Item','Set-Content','Out-File','Add-Type')){
            Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("throw 'Unexpected external boundary: $command'"))
        }
        function Reset-Test {
            $script:StateIndex++;$script:FixtureStatePath=Join-Path $RunRoot ('state-'+$script:StateIndex+'.json')
            $script:ReadCount=0;$script:WriteCount=0;$script:RefreshCount=0;$script:RejectWrite=$false;$script:RejectReopen=$false;$script:OnConfirm=$null
            $script:Errors=New-Object Collections.Generic.List[string];$script:Questions=New-Object Collections.Generic.List[string];$script:Answers=New-Object Collections.Generic.Queue[bool]
            $script:Current=$null;$script:Dirty=$false;$script:PublicationDirty=$false;$script:Busy=$false;$script:RestoreSourceRevisionId=$null;$script:SelectedTab='History'
            foreach($name in @('TitleBox','HookBox','ConceptTextBox','BuyerBox','PurchaseBox','DifferentiationBox','VisualBox','SpecBox','ReasonBox','StatusText')){Set-Variable -Scope Script -Name $name -Value ([pscustomobject]@{Text=('unsaved-'+$name)})}
            $script:RevisionList=[pscustomobject]@{SelectedItem=$null}
            Set-TestFixtureState ([pscustomobject]@{sales_rows=@();sales_imports=@();publication_receipts=@();concepts=@();research_drafts=@();synthetic_only=$true})
        }
        function Get-EditorFrame {
            return (ConvertTo-Json -Depth 60 -Compress ([ordered]@{title=$TitleBox.Text;hook=$HookBox.Text;concept=$ConceptTextBox.Text;buyer=$BuyerBox.Text;purchase=$PurchaseBox.Text;different=$DifferentiationBox.Text;visual=$VisualBox.Text;spec=$SpecBox.Text;reason=$ReasonBox.Text;dirty=$script:Dirty;publication_dirty=$script:PublicationDirty;restore=$script:RestoreSourceRevisionId;tab=$script:SelectedTab}))
        }
        function New-Fields([string]$Title) {
            $spec=[pscustomobject]@{dates=@('2026-01-02T03:04:05.1234000+05:45');empty=@();singleton=@('only');null_value=$null;enabled=$false;label='Пример';value=1.25}
            for($i=0;$i-lt24;$i++){$spec=[pscustomobject]@{child=$spec}}
            return [pscustomobject]@{title=$Title;hook='Exact hook';concept_text='old concept';target_buyer='buyer';purchase_reason='reason';differentiation='difference';visual_direction_text='visual';production_spec=$spec}
        }
        function Seed-Draft {
            Reset-Test;$key='rd-synthetic';$one=New-ResearchDraftRevision $key 1 (New-Fields 'Old title') 'owner_edit';$two=New-ResearchDraftRevision $key 2 (New-Fields 'Current title') 'owner_edit'
            $draft=[pscustomobject]@{concept_key=$key;status='draft';current_revision_no=2;current_revision_id=$two.revision_id;current_revision_hash=$two.revision_hash;revisions=@($one,$two);provenance=[pscustomobject]@{niche_name='synthetic'}}
            $lc=[pscustomobject]@{concept_key=$key;source_revision_id=$two.revision_id;source_revision_hash=$two.revision_hash;brief_approval=[pscustomobject]@{approved=$true;marker='historical fixture only'};owner_decision='KEEP';active_acceptance=[pscustomobject]@{concept_revision_id=$two.revision_id;marker='never copy to restored revision'};publication=[pscustomobject]@{saved_at='2026-10-20';listing_title='Original published title'};checks=[pscustomobject]@{visual=[pscustomobject]@{state='pass';note='Original exact review'}};artwork=@([pscustomobject]@{accepted=$true;path='synthetic-original.png';sha256='artwork-original'});packages=@([pscustomobject]@{valid=$true;sha256='package-original'})}
            $state=Get-TestFixtureState;$state.research_drafts=@($draft);$state.concepts=@($lc);$state.publication_receipts=@([pscustomobject]@{concept_key=$key;product_id='PUBLISHED-ORIGINAL';package_sha256='package-original';history_marker='must stay byte-equivalent'});Set-TestFixtureState $state
            $script:Current=[pscustomobject]@{local_research_draft=$true;draft=$draft;concept=(ConvertTo-ResearchDraftConcept $draft)};$script:RevisionList.SelectedItem=@(Get-ResearchDraftHistory $draft|Where-Object{$_.revision_no-eq1})[0]
            $script:Dirty=$true;$script:PublicationDirty=$true
            return $draft
        }
        function Assert-Throws([scriptblock]$Body,[string]$Pattern){$message='';try{& $Body}catch{$message=$_.Exception.Message};Assert-True ($message-like('*'+$Pattern+'*')) ('Expected refusal '+$Pattern)}
        Test-Case 'history_is_detached_complete_and_ordered' {
            $draft=Seed-Draft;$before=ConvertTo-Json -Depth 60 -Compress $draft;$rows=@(Get-ResearchDraftHistory $draft)
            Assert-Equal 2 $rows.Count 'All actual saved revisions';Assert-Equal 2 $rows[0].revision_no 'Newest first';Assert-Equal $rows[1].revision_id $rows[1].id 'Shared UI identity alias'
            Assert-Equal (ConvertTo-ForgeBriefCanonicalJson $draft.revisions[0].production_spec) (ConvertTo-ForgeBriefCanonicalJson $rows[1].production_spec) 'Nested payload preserved'
            $rows[1].production_spec.child=[pscustomobject]@{changed=$true};$rows[1].title='mutated view'
            Assert-Equal $before (ConvertTo-Json -Depth 60 -Compress $draft) 'UI row cannot alter saved history'
        }
        Test-Case 'restore_source_detaches_full_nested_content' {
            $d=Seed-Draft;$s=Get-ResearchDraftRestoreSource $d $d.revisions[0].revision_id $d.current_revision_id
            Assert-Equal (Get-ResearchDraftContentHash $d.concept_key $d.revisions[0]) (Get-ResearchDraftContentHash $d.concept_key $s) 'Full content hash preserved'
            $node=$s.production_spec;for($i=0;$i-lt24;$i++){$node=$node.child};Assert-True ($node.dates-is[array]-and$node.dates[0]-is[string]) 'Singleton dates keep array/string shape';Assert-Equal '2026-01-02T03:04:05.1234000+05:45' $node.dates[0] 'Timestamp lexeme preserved'
        }
        Test-Case 'restore_source_rejects_missing_ambiguous_current_and_tampered' {
            $d=Seed-Draft;Assert-Throws {Get-ResearchDraftRestoreSource $d 'missing' $d.current_revision_id} 'DRAFT_RESTORE_SOURCE'
            Assert-Throws {Get-ResearchDraftRestoreSource $d $d.current_revision_id $d.current_revision_id} 'older saved'
            $d.revisions=@($d.revisions)+@($d.revisions[0]);Assert-Throws {Get-ResearchDraftRestoreSource $d $d.revisions[0].revision_id $d.current_revision_id} 'ambiguous'
            $d=Seed-Draft;$d.revisions[0].title='tampered';Assert-Throws {Get-ResearchDraftRestoreSource $d $d.revisions[0].revision_id $d.current_revision_id} 'hash does not match'
        }
        Test-Case 'restore_save_appends_new_unapproved_revision_and_preserves_history' {
            $d=Seed-Draft;$old=ConvertTo-Json -Depth 60 -Compress $d.revisions;$before=Get-TestFixtureState;$receipts=ConvertTo-Json -Depth 60 -Compress $before.publication_receipts;$source=$d.revisions[0]
            $r=Save-ResearchDraftRevision $d.concept_key $source 'restore' $d.current_revision_id -SourceRevisionId $source.revision_id
            $s=Get-TestFixtureState;$new=$s.research_drafts[0].revisions[2]
            Assert-True $r.saved 'Committed new revision';Assert-Equal 3 $new.revision_no 'Append monotonic revision';Assert-Equal $source.revision_id $new.source_revision_id 'Source lineage explicit';Assert-Equal $source.revision_hash $new.source_revision_hash 'Source hash retained';Assert-True ($new.revision_id-cne$source.revision_id) 'New revision identity'
            Assert-Equal $old (ConvertTo-Json -Depth 60 -Compress @($s.research_drafts[0].revisions|Select-Object -First 2)) 'Existing history unchanged'
            Assert-Equal (ConvertTo-ForgeBriefCanonicalJson $source.production_spec) (ConvertTo-ForgeBriefCanonicalJson $new.production_spec) 'All nested fields restored'
            Assert-Equal $receipts (ConvertTo-Json -Depth 60 -Compress $s.publication_receipts) 'Historical publication receipts unchanged'
            Assert-Equal 'artwork-original' $s.concepts[0].artwork[0].sha256 'Artwork hash unchanged';Assert-Equal 'package-original' $s.concepts[0].packages[0].sha256 'Package records retained'
            $history=$s.concepts[0].review_history[0].payload;Assert-Equal 'Original published title' $history.publication.listing_title 'Published listing retained in history';Assert-Equal 'Original exact review' $history.checks.visual.note 'Exact check evidence retained';Assert-Equal 'never copy to restored revision' $history.active_acceptance.marker 'Exact previous acceptance retained'
            Assert-Equal $null $s.concepts[0].brief_approval 'Approval revoked';Assert-True $s.concepts[0].review_history[0].history_only 'Prior review retained as history'
            Assert-Equal $null $s.concepts[0].active_acceptance 'No active acceptance after same commit';Assert-Equal 'UNDECIDED' $s.concepts[0].owner_decision 'Owner decision revoked atomically';Assert-True (!$s.concepts[0].artwork[0].accepted-and!$s.concepts[0].packages[0].valid) 'Artwork/package flags revoked';Assert-Equal 'synthetic-original.png' $s.concepts[0].artwork[0].path 'Original artwork retained';Assert-Equal $null (Get-PropertyValue $new 'active_acceptance') 'No historical artwork acceptance copied'
        }
        Test-Case 'same_content_restore_still_creates_new_identity' {
            $d=Seed-Draft;$source=$d.revisions[0];$r=Save-ResearchDraftRevision $d.concept_key $source 'restore' $d.current_revision_id -SourceRevisionId $source.revision_id
            $next=Save-ResearchDraftRevision $d.concept_key $source 'restore again' $r.draft.current_revision_id -SourceRevisionId $source.revision_id
            Assert-True $next.saved 'Explicit restore is not ordinary edit noop';Assert-Equal 4 $next.draft.current_revision_no 'Unique new revision'
        }
        Test-Case 'ordinary_identical_save_remains_noop' {
            $d=Seed-Draft;$before=Get-TestHash $script:FixtureStatePath;$r=Save-ResearchDraftRevision $d.concept_key $d.revisions[1] '' $d.current_revision_id
            Assert-True (!$r.saved) 'Ordinary noop unchanged';Assert-Equal 0 $script:WriteCount 'No write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Approval/history bytes unchanged'
        }
        Test-Case 'stale_restore_save_does_not_write' {
            $d=Seed-Draft;$before=Get-TestHash $script:FixtureStatePath
            Assert-Throws {Save-ResearchDraftRevision $d.concept_key $d.revisions[0] 'restore' 'stale' -SourceRevisionId $d.revisions[0].revision_id} 'DRAFT_STALE'
            Assert-Equal 0 $script:WriteCount 'No write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Saved data unchanged'
        }
        Test-Case 'restore_cancel_preserves_editor_and_state' {
            $d=Seed-Draft;$before=Get-TestHash $script:FixtureStatePath;$editor=Get-EditorFrame;$script:Answers.Enqueue($false)
            Restore-SelectedResearchDraftRevision
            Assert-Equal $editor (Get-EditorFrame) 'Cancel preserves all fields/dirty/source/tab';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'State unchanged';Assert-Equal 0 $script:ReadCount 'No read after cancel';Assert-Equal 0 $script:WriteCount 'No write'
        }
        Test-Case 'restore_stale_preserves_editor_and_state' {
            $d=Seed-Draft;$state=Get-TestFixtureState;$state.research_drafts[0].current_revision_id='newer-window';Set-TestFixtureState $state;$before=Get-TestHash $script:FixtureStatePath;$editor=Get-EditorFrame;$script:Answers.Enqueue($true)
            Restore-SelectedResearchDraftRevision
            Assert-Equal 1 $script:Errors.Count 'Stale visible refusal';Assert-Equal $editor (Get-EditorFrame) 'No editor replacement';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Newer saved state preserved'
        }
        Test-Case 'restore_navigation_during_confirm_preserves_editor' {
            $d=Seed-Draft;$editor=Get-EditorFrame;$script:Answers.Enqueue($true);$script:OnConfirm={$script:Current.concept.concept_key='another'}
            Restore-SelectedResearchDraftRevision
            Assert-Equal 1 $script:Errors.Count 'Navigation refused';Assert-Equal $editor (Get-EditorFrame) 'Unrelated editor not overwritten';Assert-Equal 0 $script:WriteCount 'No write'
        }
        Test-Case 'restore_ui_then_save_uses_real_revision_writer' {
            $d=Seed-Draft;$before=Get-TestHash $script:FixtureStatePath;$script:Answers.Enqueue($true)
            Restore-SelectedResearchDraftRevision
            Assert-Equal 'Old title' $TitleBox.Text 'Historical title staged';Assert-Equal $d.revisions[0].revision_id $script:RestoreSourceRevisionId 'Source bound';Assert-Equal 'Edit' $script:SelectedTab 'Existing editor route';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Staging has no save';Assert-True $script:Dirty 'Save available'
            $script:Answers.Enqueue($true);Save-CurrentResearchDraftRevision
            Assert-Equal 0 $script:Errors.Count 'No save error';Assert-Equal 1 $script:WriteCount 'One append write';Assert-Equal 3 $script:Current.concept.current_revision_no 'Saved revision reopened';Assert-True (!$script:Dirty-and!$script:PublicationDirty) 'Dirty cleared after commit'
        }
        Test-Case 'save_conflict_preserves_dirty_editor_and_publication' {
            $d=Seed-Draft;$script:Answers.Enqueue($true);Restore-SelectedResearchDraftRevision;$before=Get-TestHash $script:FixtureStatePath;$editor=Get-EditorFrame;$script:RejectWrite=$true;$script:Answers.Enqueue($true)
            Save-CurrentResearchDraftRevision
            Assert-Equal $editor (Get-EditorFrame) 'Conflict retains staged edits including publication dirty';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Conflict preserves saved history';Assert-Equal 0 $script:WriteCount 'No committed write';Assert-Equal 1 $script:Errors.Count 'Conflict surfaced'
        }
        Test-Case 'save_navigation_during_confirm_does_not_commit_captured_draft' {
            $d=Seed-Draft;$script:Answers.Enqueue($true);Restore-SelectedResearchDraftRevision;$before=Get-TestHash $script:FixtureStatePath;$editor=Get-EditorFrame
            $script:Answers.Enqueue($true);$script:OnConfirm={$script:Current.concept.concept_key='another'}
            Save-CurrentResearchDraftRevision
            Assert-Equal 0 $script:WriteCount 'Navigation prevents write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Both saved drafts untouched';Assert-Equal $editor (Get-EditorFrame) 'Editor and dirty state preserved';Assert-Equal 1 $script:Errors.Count 'Interrupted save surfaced'
        }
        Test-Case 'post_commit_reopen_failure_cannot_retain_current_acceptance' {
            $d=Seed-Draft;$script:Answers.Enqueue($true);Restore-SelectedResearchDraftRevision;$before=Get-TestFixtureState;$receipts=ConvertTo-Json -Depth 60 -Compress $before.publication_receipts;$script:RejectReopen=$true;$script:Answers.Enqueue($true)
            Save-CurrentResearchDraftRevision;$state=Get-TestFixtureState;$lc=$state.concepts[0]
            Assert-Equal 1 $script:WriteCount 'Revision and authority reset are one write';Assert-Equal 3 $state.research_drafts[0].current_revision_no 'Revision committed';Assert-Equal $null $script:Current 'Stale UI disabled after failed reopen'
            Assert-Equal $null $lc.active_acceptance 'No current acceptance remains';Assert-Equal $null $lc.brief_approval 'No current approval remains';Assert-Equal $null $lc.publication 'No current publication metadata';Assert-True (!$lc.artwork[0].accepted-and!$lc.packages[0].valid) 'No ready artwork/package flags';Assert-True $lc.review_history[0].history_only 'Prior authority remains historical';Assert-Equal $receipts (ConvertTo-Json -Depth 60 -Compress $state.publication_receipts) 'Published receipt survives reopen failure';Assert-Equal 'artwork-original' $lc.artwork[0].sha256 'Artwork identity retained';Assert-Equal 'synthetic-original.png' $lc.artwork[0].path 'Artwork file reference retained'
        }
        function New-Receipt([string]$Market,[string]$Channel='amazon_merch',[string]$Concept='concept-a') {return [pscustomobject]@{product_id='SAME-ID';channel=$Channel;marketplace=$Market;concept_key=$Concept;package_sha256='synthetic-package';lineage_fingerprint='synthetic-lineage';fixture_authority=$true}}
        function New-SalesRow([string]$Market='',[string]$Channel='',[string]$Currency='USD'){return [pscustomobject]@{product_id=' SAME-ID ';channel=$Channel;marketplace=$Market;currency=$Currency;date='2026-10-20';units=1;royalty=2.5;revenue=0;linked=$true;linked_product_key='stale-wrong-key'}}
        function Assert-Link($Receipts,$Row,[string]$Expected){$s=[pscustomobject]@{publication_receipts=@($Receipts);sales_rows=@($Row)};Reconcile-LocalSalesLinks $s;Assert-Equal $Expected $Row.linked_product_key 'Exact linked identity';Assert-Equal ([bool]$Expected) $Row.linked 'Linked boolean'}
        Test-Case 'exact_market_separates_same_product_id' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'de')) (New-SalesRow ' DE ' ' AMAZON_MERCH ') 'amazon_merch|de|same-id'}
        Test-Case 'explicit_wrong_market_never_falls_back' {Reset-Test;Assert-Link @((New-Receipt 'us')) (New-SalesRow 'de' 'amazon_merch') ''}
        Test-Case 'explicit_wrong_channel_never_falls_back' {Reset-Test;Assert-Link @((New-Receipt 'us')) (New-SalesRow 'us' 'other') ''}
        Test-Case 'missing_market_and_multiple_markets_remains_unlinked' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'de')) (New-SalesRow '' 'amazon_merch') ''}
        Test-Case 'missing_channel_can_use_unique_explicit_market' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'de')) (New-SalesRow 'de') 'amazon_merch|de|same-id'}
        Test-Case 'legacy_no_dimensions_requires_unique_identity' {Reset-Test;Assert-Link @((New-Receipt 'us')) (New-SalesRow) 'amazon_merch|us|same-id'}
        Test-Case 'currency_never_infers_market' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'de')) (New-SalesRow '' '' 'EUR') ''}
        Test-Case 'explicit_market_does_not_match_legacy_unknown_market' {Reset-Test;Assert-Link @((New-Receipt '')) (New-SalesRow 'de') ''}
        Test-Case 'invalid_receipt_is_not_link_authority' {Reset-Test;$r=New-Receipt 'us';$r.fixture_authority=$false;Assert-Link @($r) (New-SalesRow 'us' 'amazon_merch') ''}
        Test-Case 'conflicting_exact_identity_is_not_linked' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'us' 'amazon_merch' 'different-concept')) (New-SalesRow 'us' 'amazon_merch') ''}
        Test-Case 'duplicate_same_binding_is_not_ambiguous' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'us')) (New-SalesRow 'us' 'amazon_merch') 'amazon_merch|us|same-id'}
        Test-Case 'unrelated_explicit_receipt_cannot_mask_unique_matching_market' {Reset-Test;Assert-Link @((New-Receipt 'us'),(New-Receipt 'de' 'other')) (New-SalesRow 'us') 'amazon_merch|us|same-id'}
        function New-TestCsv([string]$Body){$script:FixtureIndex++;$p=Join-Path $RunRoot ('input-'+$script:FixtureIndex+'.csv');[IO.File]::WriteAllText($p,$Body,[Text.UTF8Encoding]::new($false));$script:InputHashes[$p]=Get-TestHash $p;return $p}
        Test-Case 'csv_import_preserves_explicit_identity_and_raw_values' {
            Reset-Test;$s=Get-TestFixtureState;$s.publication_receipts=@((New-Receipt 'us'),(New-Receipt 'de'));Set-TestFixtureState $s
            $p=New-TestCsv "Date,ASIN,Units,Royalty (EUR),Sales Channel,Marketplace`n2026-10-20,SAME-ID,1,2.50, AMAZON_MERCH , DE `n"
            Import-LocalSalesCsvFromPath $p;$s=Get-TestFixtureState;$r=$s.sales_rows[0]
            Assert-Equal 0 $script:Errors.Count 'Importer accepted';Assert-Equal 'amazon_merch' $r.channel 'Normalized channel';Assert-Equal 'de' $r.marketplace 'Normalized market';Assert-Equal ' AMAZON_MERCH ' $r.channel_raw 'Raw channel preserved';Assert-Equal ' DE ' $r.marketplace_raw 'Raw marketplace preserved';Assert-Equal 'amazon_merch|de|same-id' $r.linked_product_key 'Matched exact market';Assert-Equal 'EUR' $r.currency 'Currency behavior retained'
        }
        Test-Case 'csv_legacy_no_market_never_infers_from_currency' {
            Reset-Test;$s=Get-TestFixtureState;$s.publication_receipts=@((New-Receipt 'us'),(New-Receipt 'de'));Set-TestFixtureState $s
            $p=New-TestCsv "Date,ASIN,Units,Royalty (EUR)`n2026-10-20,SAME-ID,1,2.50`n";Import-LocalSalesCsvFromPath $p;$r=(Get-TestFixtureState).sales_rows[0]
            Assert-Equal 0 $script:Errors.Count 'Import accepted without guessed market';Assert-Equal '' $r.marketplace 'No inferred marketplace';Assert-True (!$r.linked) 'No currency-based linkage'
        }
        Test-Case 'exact_reimport_enriches_identity_without_duplicate_rows' {
            Reset-Test;$p=New-TestCsv "Date,ASIN,Units,Royalty (USD),Channel,Marketplace`n2026-10-20,SAME-ID,1,2.50,amazon_merch,us`n";Import-LocalSalesCsvFromPath $p;$s=Get-TestFixtureState
            foreach($name in @('channel','channel_raw','marketplace','marketplace_raw','identity_contract')){$s.sales_rows[0].PSObject.Properties.Remove($name)}
            $s.publication_receipts=@((New-Receipt 'us'),(New-Receipt 'de'));Set-TestFixtureState $s;$script:WriteCount=0
            Import-LocalSalesCsvFromPath $p;$s=Get-TestFixtureState
            Assert-Equal 0 $script:Errors.Count 'Revalidation accepted';Assert-Equal 1 @($s.sales_rows).Count 'No duplicate rows';Assert-Equal 1 @($s.sales_imports).Count 'No duplicate source';Assert-Equal 1 $script:WriteCount 'One enrichment write';Assert-Equal 'amazon_merch|us|same-id' $s.sales_rows[0].linked_product_key 'Link repaired from exact source';Assert-Equal 1 @($s.sales_imports[0].normalization_history).Count 'Prior normalized row retained'
            $script:WriteCount=0;Import-LocalSalesCsvFromPath $p;Assert-Equal 0 $script:WriteCount 'Repeated identical source is noop'
        }
        Test-Case 'overlap_respects_explicit_market_but_missing_stays_cautious' {
            Reset-Test;$old=New-SalesRow 'us' 'amazon_merch';$other=New-SalesRow 'de' 'amazon_merch';$s=[pscustomobject]@{sales_rows=@($old)}
            Assert-Equal 0 (Get-LocalSalesOverlapSummary $s @($other)).rows 'Different explicit markets not duplicate';$other.marketplace='';Assert-Equal 1 (Get-LocalSalesOverlapSummary $s @($other)).rows 'Missing market retains cautious overlap warning'
        }
        Test-Case 'ambiguous_date_still_refused_before_state_read' {
            Reset-Test;$before=Get-TestHash $script:FixtureStatePath;$p=New-TestCsv "Date,ASIN,Units,Royalty (USD),Channel,Marketplace`n03/04/2026,SAME-ID,1,2.50,amazon_merch,us`n";Import-LocalSalesCsvFromPath $p
            Assert-Equal 1 $script:Errors.Count 'Ambiguous date refusal retained';Assert-Equal 0 $script:ReadCount 'Refusal precedes state read';Assert-Equal 0 $script:WriteCount 'No write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'State unchanged'
        }
        Test-Case 'import_overlap_cancel_keeps_source_and_state' {
            Reset-Test;$p=New-TestCsv "Date,ASIN,Units,Royalty (USD),Channel,Marketplace,Title`n2026-10-20,SAME-ID,1,2.50,amazon_merch,us,First`n";Import-LocalSalesCsvFromPath $p
            $before=Get-TestHash $script:FixtureStatePath;$script:WriteCount=0;$script:Answers.Enqueue($false);$p=New-TestCsv "Date,ASIN,Units,Royalty (USD),Channel,Marketplace,Title`n2026-10-20,SAME-ID,1,2.50,amazon_merch,us,Second`n";Import-LocalSalesCsvFromPath $p
            Assert-Equal 0 $script:WriteCount 'Cancel no write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Cancel state unchanged';Assert-Equal 0 $script:Errors.Count 'Cancel not failure'
        }
        $actualNames=@($script:Cases|ForEach-Object{$_.name});Assert-Equal ($pins.expected_case_names-join'|') ($actualNames-join'|') 'Exact ordered native cases'
        $actualFunctions=@($loaded|ForEach-Object{$_.name});Assert-Equal ($pins.expected_function_names-join'|') ($actualFunctions-join'|') 'Exact actual function identity contract'
    } catch {$failure=$_.Exception.Message}
    finally{
        try{
            foreach($source in $pins.sources.PSObject.Properties){$sourceAfter[$source.Name]=Get-TestHash (Join-Path $PackageRoot $source.Name)}
            if($sourceBefore.Count-ne$sourceAfter.Count){throw 'Source count changed during native execution.'};foreach($key in $sourceBefore.Keys){if($sourceBefore[$key]-cne$sourceAfter[$key]){throw ('Source copy changed during native execution: '+$key)}}
            if((Get-TestHash $PSCommandPath)-cne$testHash-or(Get-TestHash $PinsPath)-cne$pinsHash-or(Get-TestHash $fixturePath)-cne$fixtureHash-or(Get-TestHash $dependenciesPath)-cne$dependencyHash){throw 'Test or fixture inputs changed during native execution.'}
            foreach($path in $script:InputHashes.Keys){if((Get-TestHash $path)-cne$script:InputHashes[$path]){throw ('Synthetic source CSV changed: '+$path)}}
            if((Get-TestHash $preservedPath)-cne$preservedHash){throw 'Synthetic preservation sentinel changed.'}
        }catch{if($null-eq$failure){$failure=$_.Exception.Message}}
        $failed=@($script:Cases|Where-Object{$_.status-cne'PASS'}).Count
        if($failed-gt0-and$null-eq$failure){$failure=([string]$failed+' native case(s) failed.')}
        if($script:Cases.Count-ne32-and$null-eq$failure){$failure='Exactly 32 native cases must run.'}
        $receipt=[ordered]@{
            schema='forge.core_history_sales.native_receipt.v1';run_id=$RunId;status=$(if($unsupportedRuntime){'BLOCKED_UNSUPPORTED_NATIVE_RUNTIME'}elseif($null-eq$failure){'PASS'}else{'FAIL'});error=$failure
            started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');synthetic_only=$true
            powershell_version=$PSVersionTable.PSVersion.ToString();ps_edition=$PSVersionTable.PSEdition;date_kind_string_available=$dateKindAvailable;minimum_powershell_core='7.5'
            run_root=$RunRoot;package_copy_root=$PackageRoot;test_sha256=$testHash;pins_sha256=$pinsHash;fixtures_sha256=$fixtureHash;dependencies_sha256=$dependencyHash
            source_hashes_before=$sourceBefore;source_hashes_after=$sourceAfter;loaded_actual_functions=@($loaded.ToArray());explicit_doubles=$dependencies.doubles
            input_csv_hashes=$script:InputHashes;case_count=$script:Cases.Count;failed_case_count=$failed;cases=@($script:Cases.ToArray());synthetic_fixture_sha256=$preservedHash
            real_data_loaded=$false;app_launched=$false;model_calls=0;network_calls=0;remote_writes=0
            scope='Actual revision/history/restore/save and CSV normalization/reconciliation functions with disclosed synthetic state/UI/parser/language/authority seams. No full-app, WPF, actual state-store or ZIP/receipt-authority claim.'
        }
        $writer=[IO.StreamWriter]::new($receiptStream,[Text.UTF8Encoding]::new($false),4096,$true)
        try{$writer.Write(($receipt|ConvertTo-Json -Depth 16));$writer.Flush();$receiptStream.Flush($true)}finally{$writer.Dispose()}
    }
    if($null-ne$failure){throw $failure}
    Write-Output ('Native focused suite passed; supervisor must independently validate '+(Join-Path $RunRoot 'receipt.json'))
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}

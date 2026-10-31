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
    $claim=[IO.File]::Open((Join-Path $RunRoot '.forge-backup.claim'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $idBytes=[Text.Encoding]::UTF8.GetBytes($RunId);$claim.Write($idBytes,0,$idBytes.Length);$claim.Flush($true)
    $receiptStream=[IO.File]::Open((Join-Path $RunRoot 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{
        Assert-True ($PSVersionTable.PSEdition-ceq'Core'-and$PSVersionTable.PSVersion-ge[version]'7.5'-and$PSVersionTable.PSVersion.ToString()-match'^\d+\.\d+(?:\.\d+){0,2}$') 'Already-installed stable PowerShell Core 7.5+ required'
        Assert-True ($env:OS-ceq'Windows_NT'-and[Threading.Thread]::CurrentThread.ApartmentState-eq'STA') 'Windows STA host required for actual path/sharing and focused WPF recovery fixtures'
        $pins=[IO.File]::ReadAllText($PinsPath)|ConvertFrom-Json -DateKind String
        Assert-Equal 'forge.backup_transaction.pins.v1' $pins.schema 'Pin schema'
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
        $script:Actual=@{}
        foreach($name in $loaded){$script:Actual[$name]=(Get-Item ('Function:'+$name)).ScriptBlock}
        $script:BoundaryCalls=0
        foreach($name in @('Invoke-WebRequest','Invoke-RestMethod','Invoke-ForgeApi','Start-Process','Set-LocalExactAcceptance','Build-LocalAmazonPackage','Start-LocalGenerationWorker')){Set-Item ('Function:'+$name) ([scriptblock]::Create("`$script:BoundaryCalls++;throw 'Unexpected external action: $name'"))}
        function Get-UiText([string]$Key,[string]$Fallback){return $Fallback}
        function Write-AppLog {}
        function Show-Error([string]$Message){$script:Errors.Add($Message)}
        function Confirm([string]$Message,[string]$Title){$script:Questions.Add($Message);if($script:OnConfirm){& $script:OnConfirm};return $script:ConfirmAnswer}
        function Test-Case([string]$Name,[scriptblock]$Body){try{& $Body;$script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';error=$null})}catch{$script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';error=$_.Exception.Message})}}
        function Assert-Throws([scriptblock]$Body,[string]$Pattern){$message='';try{& $Body}catch{$message=$_.Exception.Message};Assert-True ($message-like('*'+$Pattern+'*')) ('Expected refusal '+$Pattern+'; got '+$message)}
        function Write-TestText([string]$Path,[string]$Value){Ensure-Dir (Split-Path -Parent $Path);[IO.File]::WriteAllText($Path,$Value,(New-Object Text.UTF8Encoding($false)))}
        function Set-TestStateRaw($State){Write-TestText $script:LocalCoreStatePath ($State|ConvertTo-Json -Depth 60)}
        function Reset-Test {
            foreach($name in $script:Actual.Keys){Set-Item ('Function:script:'+$name) $script:Actual[$name]}
            $script:StateRoot=Join-Path $RunRoot ('workspace-'+[guid]::NewGuid().ToString('N'));$script:LocalCoreRoot=Join-Path $script:StateRoot 'local-core-v1'
            $script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json';$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'state.lastgood.json'
            $script:BackupIncludeDirs=@('local-core-v1','channel-profiles','generation-v1');$script:BackupIncludeFiles=@('ui-locale.txt','queue-snapshot.json');$script:BackupLastSkipped=0;$script:BackupChanged=$false
            $script:DataRestoreRecoveryOnly=$false;$script:DataRestoreDisabledControls=@();$script:AppVersion='synthetic-backup-test';$script:OnConfirm=$null;$script:ConfirmAnswer=$true
            $script:Errors=New-Object Collections.Generic.List[string];$script:Questions=New-Object Collections.Generic.List[string]
            $script:CopyCalls=0;$script:FaultOnce=$false;$script:Dirty=$false;$script:PublicationDirty=$false
            Ensure-Dir $script:LocalCoreRoot
            $state=New-LocalCoreState
            $state.concepts=@([pscustomobject]@{concept_key='rd-backup';title='old';brief_approval=[pscustomobject]@{marker='preserve-existing-manual-restore-semantics'};active_acceptance=[pscustomobject]@{marker='archived-exact-acceptance'};review_history=@([pscustomobject]@{history_only=$true;payload='immutable historical evidence'});artwork=@([pscustomobject]@{local_file_path=(Join-Path $script:LocalCoreRoot 'artwork\art.txt')});packages=@();checks=[pscustomobject]@{marker='archived-checks'}})
            $state.publication_receipts=@([pscustomobject]@{history_only=$true;marker='historical receipt retained'})
            Write-LocalCoreState $state
            $script:Asset=Join-Path $script:LocalCoreRoot 'artwork\art.txt';Write-TestText $script:Asset 'old artwork bytes'
            $script:Evidence=Join-Path $script:LocalCoreRoot 'imports\receipt.json';Write-TestText $script:Evidence ('{"immutable_path":"'+$script:StateRoot.Replace('\','\\')+'","hash_bound":true}')
            $script:Archive=Join-Path $RunRoot ('archive-'+[guid]::NewGuid().ToString('N')+'.zip');$null=New-ForgeDataBackup $script:StateRoot $script:Archive
            $script:ArchiveHash=Get-TestHash $script:Archive;$script:OldWriteId=$state.last_write_id
            $new=Read-LocalCoreStateCandidate $script:LocalCoreStatePath;$new.concepts[0].title='new';Write-LocalCoreState $new
            Write-TestText $script:Asset 'new artwork bytes';$script:Extra=Join-Path $script:LocalCoreRoot 'exports\newer.txt';Write-TestText $script:Extra 'newer file retained in recovery records'
            $script:BeforePrimary=Get-TestHash $script:LocalCoreStatePath;$script:BeforeBackup=Get-TestHash $script:LocalCoreBackupPath;$script:BeforeWriteId=$new.last_write_id;$script:BeforeRevision=$new.state_revision
        }
        function Assert-PriorFrame {
            Assert-Equal $script:BeforePrimary (Get-TestHash $script:LocalCoreStatePath) 'Prior primary exact bytes'
            Assert-Equal $script:BeforeBackup (Get-TestHash $script:LocalCoreBackupPath) 'Prior last-good exact bytes'
            Assert-Equal 'new artwork bytes' ([IO.File]::ReadAllText($script:Asset)) 'Prior asset bytes'
            Assert-True (Test-Path -LiteralPath $script:Extra) 'Prior extra file retained'
            Assert-Equal $script:ArchiveHash (Get-TestHash $script:Archive) 'Original selected archive unchanged'
        }
        function Assert-Restored {
            $state=Read-LocalCoreState
            Assert-Equal 'old' $state.concepts[0].title 'Historical selected content restored'
            Assert-Equal ($script:BeforeRevision+1) $state.state_revision 'Monotonic current revision'
            Assert-True ($state.last_write_id-cne$script:OldWriteId-and$state.last_write_id-cne$script:BeforeWriteId) 'Actual writer issues new identity'
            Assert-Equal 'old artwork bytes' ([IO.File]::ReadAllText($script:Asset)) 'Selected asset restored'
            Assert-True (!(Test-Path -LiteralPath $script:Extra)) 'Extra asset set aside'
            Assert-Equal 'preserve-existing-manual-restore-semantics' $state.concepts[0].brief_approval.marker 'No new approval reset or approval issuance'
            Assert-Equal 'immutable historical evidence' $state.concepts[0].review_history[0].payload 'History preserved'
            Assert-Equal 'historical receipt retained' $state.publication_receipts[0].marker 'Receipts preserved'
            Assert-Equal $script:ArchiveHash (Get-TestHash $script:Archive) 'Selected archive unchanged'
            Assert-True (!(Test-Path (Join-Path $script:LocalCoreRoot 'restore-transaction.json'))) 'Own marker cleared only after verified completion'
        }
        Test-Case 'older_archive_after_newer_write_uses_actual_writer' {Reset-Test;$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Restored;Assert-True (Test-Path $result.previous) 'Pre-restore archive retained'}
        Test-Case 'existing_writer_lock_refuses_without_mutation' {Reset-Test;$lock=Enter-LocalCoreMutationLock;try{$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Contending restore refused';Assert-PriorFrame}finally{$lock.Dispose()}}
        Test-Case 'verified_stage_swap_refused_before_assets' {Reset-Test;$stage=Join-Path $RunRoot ('stage-'+[guid]::NewGuid().ToString('N'));$m=Read-ForgeDataBackup $script:Archive $stage;Write-TestText (Join-Path $stage 'local-core-v1\artwork\art.txt') 'changed stage';Assert-Throws {Install-BackupStage $m $stage $script:StateRoot} 'stage changed';Assert-PriorFrame}
        Test-Case 'missing_primary_target_refused_before_assets' {Reset-Test;$stage=Join-Path $RunRoot ('stage-'+[guid]::NewGuid().ToString('N'));$m=Read-ForgeDataBackup $script:Archive $stage;$m.files=@($m.files|Where-Object{$_.path-cne'local-core-v1/state.json'});Assert-Throws {Install-BackupStage $m $stage $script:StateRoot} 'no primary state';Assert-PriorFrame}
        Test-Case 'unsupported_target_schema_refused_before_assets' {Reset-Test;$stage=Join-Path $RunRoot ('stage-'+[guid]::NewGuid().ToString('N'));$m=Read-ForgeDataBackup $script:Archive $stage;$p=Join-Path $stage 'local-core-v1\state.json';Write-TestText $p '{"schema":"future"}';Assert-Throws {Install-BackupStage $m $stage $script:StateRoot} 'Unsupported local-core state schema';Assert-PriorFrame}
        Test-Case 'asset_write_failure_rolls_back_exact_preimages' {
            Reset-Test
            function Write-BackupStreamFromFile([IO.Stream]$Destination,[string]$Source){& $script:Actual['Write-BackupStreamFromFile'] $Destination $Source;if(!$script:FaultOnce-and$Source-notlike'*preimages*'){$script:FaultOnce=$true;throw 'INJECT_AFTER_ASSET_WRITE'}}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Failure reported';Assert-PriorFrame;Assert-True (!(Test-Path (Join-Path $script:LocalCoreRoot 'restore-transaction.json'))) 'Successful rollback removes own marker'
        }
        Test-Case 'writer_precommit_refusal_rolls_back_assets_not_state' {
            Reset-Test
            function Write-LocalCoreState($State,[IO.FileStream]$MutationLock=$null,$RestoreContext=$null){throw 'INJECT_PRECOMMIT_REFUSAL'}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Refusal reported';Assert-PriorFrame
        }
        Test-Case 'actual_commit_then_throw_is_recognized_not_rolled_back' {
            Reset-Test
            function Write-LocalCoreState($State,[IO.FileStream]$MutationLock=$null,$RestoreContext=$null){& $script:Actual['Write-LocalCoreState'] $State -MutationLock $MutationLock -RestoreContext $RestoreContext;throw 'INJECT_AFTER_REAL_COMMIT'}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Restored
        }
        Test-Case 'foreign_state_change_never_blindly_rolled_back' {
            Reset-Test
            function Write-LocalCoreState($State,[IO.FileStream]$MutationLock=$null,$RestoreContext=$null){$foreign=Read-LocalCoreStateCandidate $script:LocalCoreStatePath;$foreign.concepts[0].title='foreign newer state';$foreign.state_revision+=1;$foreign.last_write_id=[guid]::NewGuid().ToString('N');Set-TestStateRaw $foreign;$script:ForeignHash=Get-TestHash $script:LocalCoreStatePath;& $script:Actual['Write-LocalCoreState'] $State -MutationLock $MutationLock -RestoreContext $RestoreContext}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Foreign state conflict';Assert-Equal $script:ForeignHash (Get-TestHash $script:LocalCoreStatePath) 'Foreign writer preserved';Assert-True (Test-Path (Join-Path $script:LocalCoreRoot 'restore-transaction.json')) 'Mixed outcome guarded';Assert-Throws {Read-LocalCoreState} 'Use My data > Restore'
        }
        Test-Case 'rollback_failure_retains_marker_and_recovery_preimages' {
            Reset-Test
            function Write-BackupStreamFromFile([IO.Stream]$Destination,[string]$Source){if($Source-like'*preimages*'){throw 'INJECT_ROLLBACK_FAILURE'};& $script:Actual['Write-BackupStreamFromFile'] $Destination $Source;throw 'INJECT_FORWARD_FAILURE'}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Failure retained';Assert-True (Test-Path (Join-Path $script:LocalCoreRoot 'restore-transaction.json')) 'Guard retained';Assert-Equal $script:BeforePrimary (Get-TestHash $script:LocalCoreStatePath) 'State not committed';Assert-True (@(Get-ChildItem (Join-Path $script:StateRoot 'backups') -Recurse -Filter journal.json).Count-gt0) 'Durable journal retained'
        }
        Test-Case 'pending_restore_cancel_preserves_current_bytes' {Reset-Test;$marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';Write-TestText $marker 'interrupted recovery record';$sha=Get-TestHash $marker;$script:ConfirmAnswer=$false;$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Cancelled';Assert-True $result.cancelled 'Explicit cancellation';Assert-PriorFrame;Assert-Equal $sha (Get-TestHash $marker) 'Marker unchanged'}
        Test-Case 'malformed_pending_marker_recoverable_through_existing_route' {Reset-Test;$marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';Write-TestText $marker '{interrupted marker bytes';$sha=Get-TestHash $marker;$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Restored;$retained=@(Get-ChildItem (Join-Path $script:StateRoot 'backups') -Recurse -Filter previous-marker.json);Assert-Equal 1 $retained.Count 'Previous raw marker retained';Assert-Equal $sha (Get-TestHash $retained[0].FullName) 'Malformed bytes retained exactly'}
        Test-Case 'pending_marker_changed_during_confirmation_refuses' {Reset-Test;$script:Marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';Write-TestText $script:Marker 'original';$script:OnConfirm={Write-TestText $script:Marker 'foreign marker'};$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Marker race refused';Assert-PriorFrame;Assert-Equal 'foreign marker' ([IO.File]::ReadAllText($script:Marker)) 'Foreign marker preserved'}
        Test-Case 'pending_marker_blocks_normal_reader_and_actual_writer' {Reset-Test;$state=Read-LocalCoreState;Write-TestText (Join-Path $script:LocalCoreRoot 'restore-transaction.json') 'pending';Assert-Throws {Read-LocalCoreState} 'restore is pending';Assert-Throws {Write-LocalCoreState $state} 'restore is pending';Assert-PriorFrame}
        Test-Case 'foreign_marker_not_removed_after_own_commit' {
            Reset-Test
            function Write-LocalCoreState($State,[IO.FileStream]$MutationLock=$null,$RestoreContext=$null){& $script:Actual['Write-LocalCoreState'] $State -MutationLock $MutationLock -RestoreContext $RestoreContext;Write-TestText (Join-Path $script:LocalCoreRoot 'restore-transaction.json') 'foreign marker'}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Foreign marker prevents completion claim';Assert-Equal 'foreign marker' ([IO.File]::ReadAllText((Join-Path $script:LocalCoreRoot 'restore-transaction.json'))) 'Foreign marker retained';Assert-Equal 'old' (Read-LocalCoreStateCandidate $script:LocalCoreStatePath).concepts[0].title 'Committed state not undone'
        }
        Test-Case 'capture_open_writer_refuses_and_preserves_destination' {Reset-Test;$output=Join-Path $RunRoot ('capture-'+[guid]::NewGuid().ToString('N')+'.zip');Write-TestText $output 'existing archive';$lock=[IO.File]::Open($script:Asset,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);try{Assert-Throws {New-ForgeDataBackup $script:StateRoot $output} 'open for writing';Assert-Equal 'existing archive' ([IO.File]::ReadAllText($output)) 'Existing archive untouched'}finally{$lock.Dispose()}}
        Test-Case 'capture_vanished_enumerated_file_aborts_not_skips' {
            Reset-Test;$output=Join-Path $RunRoot ('capture-'+[guid]::NewGuid().ToString('N')+'.zip')
            function Get-BackupRelativeFiles([string]$Root){$list=@(& $script:Actual['Get-BackupRelativeFiles'] $Root);if(!$script:FaultOnce){$script:FaultOnce=$true;[IO.File]::Delete($script:Extra)};return $list}
            Assert-Throws {New-ForgeDataBackup $script:StateRoot $output} 'disappeared';Assert-True (!(Test-Path $output)) 'No incomplete ZIP published'
        }
        Test-Case 'capture_inventory_growth_aborts_not_mixed_snapshot' {
            Reset-Test;$output=Join-Path $RunRoot ('capture-'+[guid]::NewGuid().ToString('N')+'.zip')
            function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName,[IO.Stream]$SourceStream=$null){$value=& $script:Actual['Copy-FileIntoZipEntry'] $Path $Zip $EntryName $SourceStream;if(!$script:FaultOnce){$script:FaultOnce=$true;Write-TestText (Join-Path $script:LocalCoreRoot 'exports\concurrent.txt') 'concurrent new file'};return $value}
            Assert-Throws {New-ForgeDataBackup $script:StateRoot $output} 'inventory changed';Assert-True (!(Test-Path $output)) 'No mixed ZIP published'
        }
        Test-Case 'capture_held_inputs_block_same_process_writes' {
            Reset-Test;$output=Join-Path $RunRoot ('capture-'+[guid]::NewGuid().ToString('N')+'.zip');$script:BlockedWrite=$false
            function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName,[IO.Stream]$SourceStream=$null){if(!$script:FaultOnce){$script:FaultOnce=$true;try{$h=[IO.File]::Open($script:Asset,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite);$h.Dispose()}catch{$script:BlockedWrite=$true}};return (& $script:Actual['Copy-FileIntoZipEntry'] $Path $Zip $EntryName $SourceStream)}
            $null=New-ForgeDataBackup $script:StateRoot $output;Assert-True $script:BlockedWrite 'Windows sharing rejects a concurrent writer';$stage=Join-Path $RunRoot ('check-'+[guid]::NewGuid().ToString('N'));$m=Read-ForgeDataBackup $output $stage;Assert-Equal 'locked_snapshot_v1' $m.consistency 'Coherent snapshot label'
        }
        Test-Case 'mixed_recovery_preimage_never_accepted_as_restore_source' {Reset-Test;Write-TestText (Join-Path $script:LocalCoreRoot 'restore-transaction.json') 'pending';$output=Join-Path $RunRoot ('mixed-'+[guid]::NewGuid().ToString('N')+'.zip');$lock=Enter-LocalCoreMutationLock;try{$null=New-ForgeDataBackup $script:StateRoot $output -MutationLock $lock -RecoveryPreimage $true}finally{$lock.Dispose()};$result=Restore-ForgeDataBackupFromPath $output;Assert-Equal $false $result.ok 'Mixed recovery image not a valid target';Assert-PriorFrame}
        Test-Case 'ordinary_capture_refuses_pending_workspace' {Reset-Test;Write-TestText (Join-Path $script:LocalCoreRoot 'restore-transaction.json') 'pending';Assert-Throws {New-ForgeDataBackup $script:StateRoot (Join-Path $RunRoot 'must-not-exist.zip')} 'restore is incomplete';Assert-PriorFrame}
        Test-Case 'relocation_changes_only_live_locations_not_evidence' {Reset-Test;$state=Read-LocalCoreState;$old=$script:StateRoot;$new='Z:\synthetic-moved-root';$state.concepts[0].review_history[0].payload=$old+'\immutable';$before=$state.publication_receipts|ConvertTo-Json -Depth 10;Convert-BackupStatePaths $state $old $new;Assert-True ($state.concepts[0].artwork[0].local_file_path.StartsWith($new)) 'Live pointer relocated';Assert-Equal ($old+'\immutable') $state.concepts[0].review_history[0].payload 'History not rewritten';Assert-Equal $before ($state.publication_receipts|ConvertTo-Json -Depth 10) 'Receipts unchanged'}
        Test-Case 'standalone_json_receipt_bytes_not_rewritten_on_restore' {Reset-Test;$sha=Get-TestHash $script:Evidence;$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Equal $sha (Get-TestHash $script:Evidence) 'Hash-bound JSON evidence exact'}
        Test-Case 'existing_state_recovery_artifacts_remain_immutable' {Reset-Test;$p=$script:LocalCoreStatePath+'.restore-before.synthetic.json';Write-TestText $p 'existing recovery evidence';$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Equal 'existing recovery evidence' ([IO.File]::ReadAllText($p)) 'Recovery evidence not moved or overwritten'}
        Test-Case 'before_snapshot_failure_precedes_any_install_mutation' {
            Reset-Test
            function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName,[IO.Stream]$SourceStream=$null){throw 'INJECT_SNAPSHOT_FAILURE'}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Snapshot failure';Assert-PriorFrame;Assert-True (!(Test-Path (Join-Path $script:LocalCoreRoot 'restore-transaction.json'))) 'No mutation marker created'
        }
        Test-Case 'recovery_home_exposes_existing_restore_without_state_read' {
            Reset-Test;Add-Type -AssemblyName PresentationFramework;Write-TestText (Join-Path $script:LocalCoreRoot 'restore-transaction.json') 'pending'
            $script:Window=New-Object Windows.Window;$panel=New-Object Windows.Controls.StackPanel;$script:Window.Content=$panel
            $script:DataRestoreButton=New-Object Windows.Controls.Button;$other=New-Object Windows.Controls.Button;$panel.Children.Add($script:DataRestoreButton)|Out-Null;$panel.Children.Add($other)|Out-Null
            $script:LoginGrid=New-Object Windows.Controls.Grid;$script:AppGrid=New-Object Windows.Controls.Grid;$script:HomeLandingScroll=New-Object Windows.Controls.ScrollViewer
            $script:StatusText=New-Object Windows.Controls.TextBlock;$script:DataAutoCopyText=New-Object Windows.Controls.TextBlock
            function Hide-ProductSurfaces {}
            Assert-True (Show-DataRestoreRecovery) 'Recovery route exposed';$savedCount=$script:DataRestoreDisabledControls.Count;Assert-True (Show-DataRestoreRecovery) 'Repeated recovery view';Assert-Equal $savedCount $script:DataRestoreDisabledControls.Count 'Repeated failure preserves original control states';Assert-True $script:DataRestoreButton.IsEnabled 'Existing Restore usable';Assert-Equal $false $other.IsEnabled 'Other actions disabled';Assert-Equal 'Visible' ([string]$script:AppGrid.Visibility) 'Login not blocking recovery';$script:Window.Close()
        }
        Test-Case 'failed_recovery_of_pending_workspace_restores_prior_marker' {
            Reset-Test;$marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';Write-TestText $marker 'prior incomplete workspace';$sha=Get-TestHash $marker
            function Write-BackupStreamFromFile([IO.Stream]$Destination,[string]$Source){& $script:Actual['Write-BackupStreamFromFile'] $Destination $Source;if(!$script:FaultOnce-and$Source-notlike'*preimages*'){$script:FaultOnce=$true;throw 'INJECT_RECOVERY_ASSET_FAILURE'}}
            $result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-Equal $false $result.ok 'Recovery attempt failed';Assert-PriorFrame;Assert-Equal $sha (Get-TestHash $marker) 'Prior pending marker restored exactly';Assert-Throws {Read-LocalCoreState} 'restore is pending'
        }
        Test-Case 'normal_capture_rejects_empty_primary_workspace' {Reset-Test;[IO.File]::Delete($script:LocalCoreStatePath);$output=Join-Path $RunRoot ('empty-'+[guid]::NewGuid().ToString('N')+'.zip');Assert-Throws {New-ForgeDataBackup $script:StateRoot $output} 'valid primary state';Assert-True (!(Test-Path $output)) 'No unusable backup published'}
        Test-Case 'normal_capture_rejects_malformed_primary_workspace' {Reset-Test;Write-TestText $script:LocalCoreStatePath '{broken';$output=Join-Path $RunRoot ('broken-'+[guid]::NewGuid().ToString('N')+'.zip');Assert-Throws {New-ForgeDataBackup $script:StateRoot $output} 'JSON';Assert-True (!(Test-Path $output)) 'No unusable backup published'}
        Test-Case 'verified_restore_can_recover_malformed_current_primary' {Reset-Test;Write-TestText $script:LocalCoreStatePath '{broken current primary';$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Equal 'old' (Read-LocalCoreState).concepts[0].title 'Valid archive recovered';$stage=Join-Path $RunRoot ('preimage-'+[guid]::NewGuid().ToString('N'));$m=Read-ForgeDataBackup $result.previous $stage;Assert-Equal 'recovery_preimage_not_a_consistent_workspace' $m.consistency 'Malformed old bytes labeled truthfully';Assert-Equal '{broken current primary' ([IO.File]::ReadAllText((Join-Path $stage 'local-core-v1\state.json'))) 'Malformed preimage retained exactly'}
        Test-Case 'verified_restore_can_recover_missing_current_primary' {Reset-Test;[IO.File]::Delete($script:LocalCoreStatePath);$result=Restore-ForgeDataBackupFromPath $script:Archive;Assert-True $result.ok ($script:Errors-join'; ');Assert-Equal 'old' (Read-LocalCoreState).concepts[0].title 'Missing primary restored from verified archive'}
        Test-Case 'relocation_updates_separate_active_acceptance_pointer' {Reset-Test;$state=Read-LocalCoreState;$old=$script:StateRoot;$new='Z:\synthetic-moved-root';Add-OrSetProperty $state.concepts[0].active_acceptance 'local_file_path' $script:Asset;Add-OrSetProperty $state.concepts[0].active_acceptance 'lineage_fingerprint' 'exact-fingerprint';Convert-BackupStatePaths $state $old $new;Assert-True ($state.concepts[0].active_acceptance.local_file_path.StartsWith($new)) 'Live package input points to restored root';Assert-Equal 'exact-fingerprint' $state.concepts[0].active_acceptance.lineage_fingerprint 'Identity unchanged'}
        Test-Case 'recovery_refresh_does_not_connect_backend' {Reset-Test;$script:DataRestoreRecoveryOnly=$true;function Connect-Workbench {throw 'Unexpected backend reconnect'};Refresh-Workbench}
        Test-Case 'no_external_generation_or_publication_actions' {Assert-Equal 0 $script:BoundaryCalls 'No external guarded boundary attempts'}
        Assert-Equal ($pins.expected_case_names-join'|') ((@($script:Cases|ForEach-Object{$_.name}))-join'|') 'Exact case identity/order'
        foreach($entry in $sourceBefore.GetEnumerator()){$sourceAfter[$entry.Key]=Get-TestHash (Join-Path $PackageRoot $entry.Key);Assert-Equal $entry.Value $sourceAfter[$entry.Key] ('Source unchanged '+$entry.Key)}
        foreach($entry in $testBefore.GetEnumerator()){$testAfter[$entry.Key]=Get-TestHash (Join-Path $PSScriptRoot $entry.Key);Assert-Equal $entry.Value $testAfter[$entry.Key] ('Test unchanged '+$entry.Key)}
        Assert-Equal $pinsHash (Get-TestHash $PinsPath) 'Pins unchanged'
        Assert-Equal 0 @($script:Cases|Where-Object{$_.status-ne'PASS'}).Count 'Every prepared case passes'
    }catch{$failure=$_.Exception.Message}
    $receipt=[ordered]@{schema='forge.backup_transaction.native_receipt.v1';run_id=$RunId;started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o');package_root=$PackageRoot;run_root=$RunRoot;pins_sha256=$pinsHash;runtime=$PSVersionTable.PSVersion.ToString();status=$(if($null-eq$failure){'PASS'}else{'FAIL'});error=$failure;functions=@($loaded.ToArray());cases=@($script:Cases.ToArray());source_before=$sourceBefore;source_after=$sourceAfter;test_before=$testBefore;test_after=$testAfter;scope='Actual writer, lock/context, ZIP and file operations against synthetic private workspace. Explicit fault wrappers, confirmations/status seams; focused WPF recovery controls only, not full app restart or process-crash proof.'}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 20));$receiptStream.Write($bytes,0,$bytes.Length);$receiptStream.Flush($true)
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}
if($null-ne$failure){throw $failure}

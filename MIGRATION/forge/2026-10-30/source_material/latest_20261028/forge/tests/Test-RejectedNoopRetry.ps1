# Separately authorized, function-level no-op reconciliation tests only.
# Does not import Forge or use real rejected records, state, approvals, models,
# network, package/export destinations, or the user's computer.
# External runner timeout supervision is required. Treat timeout, crash, missing
# receipt, nonzero exit, or non-PASS receipt as failure. A killed host may leave no
# final receipt; the GUID-owned root only prevents an earlier PASS being reused.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ModuleRoot)

$ErrorActionPreference='Stop'
$script:ScopeLabel='function-level synthetic dependency doubles'
$script:Cases=New-Object 'System.Collections.Generic.List[object]'
$script:Loaded=New-Object 'System.Collections.Generic.List[object]'
$script:CheckCount=0
$started=[DateTime]::UtcNow.ToString('o')
$runId=[Guid]::NewGuid().ToString('N')
$runRoot=Join-Path ([IO.Path]::GetTempPath()) ('forge-rejected-noop-retry-'+$runId)
if (Microsoft.PowerShell.Management\Test-Path -LiteralPath $runRoot) { throw 'Fresh test root already exists; refusing reuse.' }
[void][IO.Directory]::CreateDirectory($runRoot)
if ((Get-Item -LiteralPath $runRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Fresh test root is redirected.' }
$receiptPath=Join-Path $runRoot 'receipt.json'
$source=$null

function Get-TestBytesHash([byte[]]$Bytes) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-TestTextHash([string]$Text) { return Get-TestBytesHash ([Text.Encoding]::UTF8.GetBytes($Text)) }
function Get-TestJson($Value) { return ConvertTo-Json -InputObject $Value -Depth 60 -Compress }
function Copy-TestObject($Value) { return ConvertFrom-Json -InputObject (Get-TestJson $Value) }
function Assert-Test([bool]$Condition,[string]$Message) {
    $script:CheckCount++
    if (!$Condition) { throw ('CHECK_FAILED: '+$Message) }
}
function Invoke-TestCase([string]$Name,[scriptblock]$Body) {
    try {
        & $Body
        $script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';detail=''})
        Write-Host ('PASS: '+$Name)
    } catch {
        $script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';detail=$_.Exception.Message})
        Write-Host ('FAIL: '+$Name+': '+$_.Exception.Message)
    }
}
function Get-TestThrownMessage([scriptblock]$Body) {
    try { $null=& $Body } catch { return $_.Exception.Message }
    throw 'CHECK_FAILED: expected refusal, but the function returned.'
}

# All functions below are explicitly synthetic dependency doubles. Only Resolve-
# ForgeRejectedSave and Save-ForgeRejectedProposal are exact source functions.
# In particular, Test-ForgeRejectedProposal is NOT tested by this file.
function Get-PropertyValue($Object,[string]$Name) {
    if ($null -eq $Object) { return $null }
    $p=$Object.PSObject.Properties[$Name]
    if ($null -ne $p) { return ,$p.Value }
    return $null
}
function Add-OrSetProperty($Object,[string]$Name,$Value) {
    $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force
}
function Enter-ForgeRejectedWriteLock {
    $script:Calls.lock++
    $lock=[pscustomobject]@{scope='in-memory lock double; no file opened'}
    $lock | Add-Member -MemberType ScriptMethod -Name Dispose -Value {$script:Calls.unlock++}
    return $lock
}
function Read-ForgeRejectedProposal([string]$Id) {
    $script:Calls.read++
    if ($Id -cne $script:Proposal.id) { throw 'TEST_BAD_PROPOSAL_ID' }
    return $script:Proposal
}
function Get-ForgeRejectedDirectory([string]$Id) {
    if ($Id -cne $script:Proposal.id) { throw 'TEST_BAD_DIRECTORY_ID' }
    return $script:VirtualDirectory
}
function Test-Path([string]$LiteralPath) {
    if ($LiteralPath -cne $script:AttemptPath) { throw ('TEST_UNEXPECTED_PATH: '+$LiteralPath) }
    return $script:AttemptExists
}
function Read-ForgeRejectedJson([string]$Path) {
    $script:Calls.readAttempt++
    if ($Path -cne $script:AttemptPath) { throw 'TEST_BAD_ATTEMPT_READ_PATH' }
    return Copy-TestObject $script:Attempt
}
function Find-ForgeRejectedCommittedRevision($Proposal,$Attempt) {
    $script:Calls.findCommitted++
    return $null # Synthetic proof boundary: no committed matching revision.
}
function Get-FileSha256Hex([string]$Path) {
    $script:Calls.stateHash++
    if ($Path -cne $script:LocalCoreStatePath) { throw 'TEST_BAD_STATE_HASH_PATH' }
    return $script:ObservedStateSha
}
function Test-ForgeRejectedProposal([string]$Id,[string]$ExpectedEditSha) {
    $script:Calls.validate++
    if ($Id -cne $script:Proposal.id -or $ExpectedEditSha -cne $script:Proposal.edit.content_sha256) { throw 'TEST_STALE_EDIT' }
    return [pscustomobject]@{
        fields=[pscustomobject]@{title='synthetic no-op fields';__forge_rejection_id=$Id};
        evidence=[pscustomobject]@{scope='synthetic evidence, not an archive'}
    }
}
function Get-ForgeRejectedAttemptHistory($Attempt) {
    $script:Calls.history++
    return @([pscustomobject]@{outcome=$Attempt.outcome;scope='synthetic prior-attempt snapshot'})
}
function Write-ForgeRejectedAtomicJson([string]$Path,$Value) {
    $script:Calls.writeAttempt++
    if ($Path -cne $script:AttemptPath) { throw 'TEST_BAD_ATTEMPT_WRITE_PATH' }
    $script:Attempt=Copy-TestObject $Value
    $script:Writes.Add((Copy-TestObject $Value))
}
function Get-ResearchDraftContentHash([string]$Key,$Fields) { return Get-TestTextHash (Get-TestJson $Fields) }
function Save-ForgeLocalAIDraft($Fields,[string]$Prompt,[string]$ExistingKey,[string]$ExpectedRevision,$EvidenceContext,[string]$ReviewToken) {
    $script:Calls.save++
    if ($ReviewToken -cne $script:Proposal.id -or $Fields.__forge_rejection_id -cne $ReviewToken) { throw 'TEST_BAD_REVIEW_TOKEN' }
    # A labeled NO-OP acknowledgement, not a saved or approved record.
    return [pscustomobject]@{saved=$false;draft=[pscustomobject]@{current_revision_id='synthetic-unchanged-revision'}}
}
function Merge-ForgeLocalAIManualFields { throw 'TEST_UNEXPECTED_EXISTING_DRAFT' }
function Write-LocalCoreState { throw 'TEST_BOUNDARY_STOP: real state writes forbidden' }

function Set-TestAttempt([string]$Outcome) {
    $script:Calls=@{lock=0;unlock=0;read=0;readAttempt=0;findCommitted=0;stateHash=0;validate=0;history=0;writeAttempt=0;save=0}
    $script:Writes=New-Object 'System.Collections.Generic.List[object]'
    $script:Dirty=$false; $script:PublicationDirty=$false
    $script:VirtualDirectory=Join-Path $runRoot 'in-memory-proposal-only'
    $script:AttemptPath=Join-Path $script:VirtualDirectory 'save-attempt.json'
    $script:LocalCoreStatePath=Join-Path $runRoot 'in-memory-state-only.json'
    $script:ObservedStateSha=('a'*64)
    $script:AttemptExists=$true
    $content='{"synthetic":"edited proposal preserved"}'
    $script:Proposal=[pscustomobject]@{
        id=('rej-'+('b'*32)); raw_text='SYNTHETIC immutable original';
        raw_bytes=[Text.Encoding]::UTF8.GetBytes('SYNTHETIC immutable original');
        edit=[pscustomobject]@{content=$content;content_sha256=(Get-TestTextHash $content)};
        record=[pscustomobject]@{binding=[pscustomobject]@{concept_key='';revision_id=''}}
    }
    $script:Attempt=[pscustomobject]@{
        outcome=$Outcome; pre_state_sha256=$script:ObservedStateSha;
        edit_sha256=$script:Proposal.edit.content_sha256; history=@(); approved=$false
    }
}
function Assert-TestInputsUntouched([string]$Before,[string]$RawHash) {
    Assert-Test ((Get-TestJson $script:Proposal) -ceq $Before) 'Original raw/edit proposal objects must remain unchanged.'
    Assert-Test ((Get-TestBytesHash $script:Proposal.raw_bytes) -ceq $RawHash) 'Original raw bytes must remain unchanged.'
    Assert-Test (!(Microsoft.PowerShell.Management\Test-Path -LiteralPath $script:VirtualDirectory)) 'No real rejected storage directory may be created.'
    Assert-Test (!(Microsoft.PowerShell.Management\Test-Path -LiteralPath $script:LocalCoreStatePath)) 'No real core state file may be created.'
}

try {
    $ModuleRoot=(Resolve-Path -LiteralPath $ModuleRoot).ProviderPath
    $sourcePath=Join-Path $ModuleRoot 'Forge.RejectedAI.ps1'
    $copyPath=Join-Path $runRoot 'Forge.RejectedAI.ps1'
    $sourceBytes=[IO.File]::ReadAllBytes($sourcePath)
    [IO.File]::WriteAllBytes($copyPath,$sourceBytes)
    $source=[pscustomobject]@{
        path=$sourcePath;before_sha256=(Get-TestBytesHash $sourceBytes);after_sha256='';
        copied_path=$copyPath;copied_before_sha256=(Get-TestBytesHash ([IO.File]::ReadAllBytes($copyPath)));copied_after_sha256=''
    }
    Assert-Test ($source.before_sha256 -ceq $source.copied_before_sha256) 'Owned module copy must be byte-exact.'
    $tokens=$null; $parseErrors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($copyPath,[ref]$tokens,[ref]$parseErrors)
    Assert-Test (@($parseErrors).Count -eq 0) 'Copied canonical source must parse.'
    foreach ($name in @('Resolve-ForgeRejectedSave','Save-ForgeRejectedProposal')) {
        $definitions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object {$_.Name -ceq $name})
        Assert-Test ($definitions.Count -eq 1) ('Exactly one actual target: '+$name)
        $definition=$definitions[0]
        . ([scriptblock]::Create($definition.Extent.Text))
        $loaded=Get-Command -Name $name -CommandType Function
        Assert-Test ($loaded.ScriptBlock.Ast.Extent.Text -ceq $definition.Body.Extent.Text) ('Loaded exact copied source body: '+$name)
        $script:Loaded.Add([pscustomobject]@{name=$name;source=$sourcePath;parsed_owned_copy=$copyPath;definition_sha256=(Get-TestTextHash $definition.Extent.Text);body_sha256=(Get-TestTextHash $loaded.ScriptBlock.Ast.Extent.Text)})
    }
    foreach ($outcome in @('unchanged','pending')) {
        Invoke-TestCase ('No-confirm readback never retries or changes '+$outcome) {
            Set-TestAttempt $outcome
            $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes; $oldAttempt=Get-TestJson $script:Attempt
            $result=Resolve-ForgeRejectedSave $script:Proposal.id
            Assert-Test ($result.outcome -ceq 'not_committed_at_readback' -and !$result.saved -and !$result.automatic_retry -and !$result.approved) 'Readback is informational only.'
            Assert-Test ($script:Calls.findCommitted -eq 1 -and $script:Calls.lock -eq 1 -and $script:Calls.unlock -eq 1) 'Readback and lock disposal must actually run.'
            Assert-Test ($script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0 -and $script:Calls.validate -eq 0 -and $script:Calls.stateHash -eq 0) 'No-confirm readback cannot validate, write, save, or infer retry permission.'
            Assert-Test ((Get-TestJson $script:Attempt) -ceq $oldAttempt) 'No-confirm readback leaves attempt untouched.'
            Assert-TestInputsUntouched $before $rawHash
        }
        Invoke-TestCase ('Explicit matching-state reconciliation permits '+$outcome+' without saving') {
            Set-TestAttempt $outcome
            $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
            $result=Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted
            Assert-Test ($result.outcome -ceq 'reconciled_not_committed' -and !$result.saved -and $result.explicit_save_required -and !$result.automatic_retry -and !$result.approved) 'Reconciliation must require a later explicit save and confer no approval.'
            Assert-Test ($script:Calls.stateHash -eq 1 -and $script:Calls.validate -eq 1 -and $script:Calls.writeAttempt -eq 1) 'Exact-state and proposal validation precede one reconciliation receipt update.'
            Assert-Test ($script:Attempt.outcome -ceq 'reconciled_not_committed' -and $script:Attempt.history[0].outcome -ceq $outcome) 'Prior outcome must be retained in test history.'
            Assert-Test ($script:Calls.save -eq 0 -and $script:Calls.unlock -eq 1) 'Reconciliation itself never calls save; lock must be released.'
            Assert-TestInputsUntouched $before $rawHash
        }
    }
    foreach ($outcome in @('unchanged','pending')) {
        Invoke-TestCase ('Changed persisted-state identity refuses '+$outcome+' reconciliation') {
            Set-TestAttempt $outcome
            $script:ObservedStateSha=('c'*64)
            $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes; $oldAttempt=Get-TestJson $script:Attempt
            $message=Get-TestThrownMessage { Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted }
            Assert-Test ($message -ceq 'REJECTED_RECOVERY_UNCERTAIN: exact precommit state not proven; no retry authorized') 'Stale state must refuse exact retry permission.'
            Assert-Test ($script:Calls.stateHash -eq 1 -and $script:Calls.validate -eq 0 -and $script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0) 'Stale-state refusal must precede validation, receipt mutation, or save.'
            Assert-Test ((Get-TestJson $script:Attempt) -ceq $oldAttempt -and $script:Calls.unlock -eq 1) 'Refusal must preserve attempt and dispose lock.'
            Assert-TestInputsUntouched $before $rawHash
        }
    }
    foreach ($invalid in @('saved_unapproved','reconciled_not_committed','unexpected','')) {
        Invoke-TestCase ('Invalid prior outcome stays refused: ['+$invalid+']') {
            Set-TestAttempt $invalid
            $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes; $oldAttempt=Get-TestJson $script:Attempt
            $message=Get-TestThrownMessage { Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted }
            Assert-Test ($message.StartsWith('REJECTED_RECOVERY_UNCERTAIN:')) 'Only pending/unchanged may reconcile.'
            Assert-Test ($script:Calls.validate -eq 0 -and $script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0) 'Invalid prior outcomes must not reach mutation boundaries.'
            Assert-Test ((Get-TestJson $script:Attempt) -ceq $oldAttempt -and $script:Calls.unlock -eq 1) 'Refusal must preserve attempt and release lock.'
            Assert-TestInputsUntouched $before $rawHash
        }
    }
    Invoke-TestCase 'Malformed pre-state digest refuses explicit reconciliation' {
        Set-TestAttempt 'unchanged'; $script:Attempt.pre_state_sha256='not-a-sha256'
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
        $message=Get-TestThrownMessage { Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted }
        Assert-Test ($message.StartsWith('REJECTED_RECOVERY_UNCERTAIN:')) 'Malformed state identity must not authorize retry.'
        Assert-Test ($script:Calls.stateHash -eq 0 -and $script:Calls.validate -eq 0 -and $script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0) 'Malformed pre-state must stop before later boundaries.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'Actual Save target refuses an unreconciled unchanged attempt' {
        Set-TestAttempt 'unchanged'
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes; $oldAttempt=Get-TestJson $script:Attempt
        $message=Get-TestThrownMessage { Save-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256 }
        Assert-Test ($message.StartsWith('REJECTED_SAVE_RECONCILE:')) 'No-op outcome must not itself permit a save retry.'
        Assert-Test ($script:Calls.validate -eq 0 -and $script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0) 'Unreconciled no-op must not cross retry boundaries.'
        Assert-Test ((Get-TestJson $script:Attempt) -ceq $oldAttempt) 'Prior no-op attempt remains intact.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'A separately invoked explicit Save reaches only a synthetic no-op acknowledgement' {
        Set-TestAttempt 'unchanged'
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
        $null=Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted
        Assert-Test ($script:Calls.save -eq 0 -and $script:Calls.writeAttempt -eq 1) 'No automatic save may occur during reconciliation.'
        # This separate invocation is the test's explicit second action.
        $result=Save-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256
        Assert-Test ($result.saved -eq $false) 'Synthetic save boundary acknowledges no change, not a real save.'
        Assert-Test ($script:Calls.save -eq 1 -and $script:Calls.validate -eq 2) 'Only the separate Save invocation may call the save boundary once.'
        Assert-Test ($script:Calls.writeAttempt -eq 3 -and $script:Writes[1].outcome -ceq 'pending' -and $script:Writes[2].outcome -ceq 'unchanged') 'Existing pending -> unchanged receipt flow remains intact.'
        Assert-Test ($script:Attempt.outcome -ceq 'unchanged' -and $script:Attempt.approved -eq $false) 'A repeated no-op is still unapproved and needs explicit future reconciliation.'
        Assert-Test ($script:Calls.lock -eq 2 -and $script:Calls.unlock -eq 2) 'Both explicit transactions release their synthetic locks.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'A new retained edit before no-op reconciliation is validated explicitly, without parent rebase' {
        Set-TestAttempt 'unchanged'
        $oldEditSha=$script:Attempt.edit_sha256
        $script:Proposal.edit.content='{"synthetic":"new explicit edit after no-op"}'
        $script:Proposal.edit.content_sha256=Get-TestTextHash $script:Proposal.edit.content
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
        $result=Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted
        Assert-Test ($result.outcome -ceq 'reconciled_not_committed' -and !$result.saved -and !$result.automatic_retry) 'Explicit no-op reconciliation must accept the current validated edited copy only after exact pre-state proof.'
        Assert-Test ($script:Calls.stateHash -eq 1 -and $script:Calls.validate -eq 1 -and $script:Calls.save -eq 0) 'Current edit must be validated without automatically saving or rebasing.'
        Assert-Test ($script:Attempt.edit_sha256 -ceq $oldEditSha) 'Original attempted edit identity remains recorded until the separate explicit save.'
        $saved=Save-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256
        Assert-Test ($saved.saved -eq $false -and $script:Calls.save -eq 1) 'Separate explicit Save alone reaches the synthetic no-op boundary.'
        Assert-Test ($script:Writes[1].edit_sha256 -ceq $script:Proposal.edit.content_sha256) 'New pending attempt binds the current edit exactly.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'A changed edit does not loosen pending-attempt reconciliation' {
        Set-TestAttempt 'pending'
        $script:Proposal.edit.content='{"synthetic":"edit while prior attempt pending"}'
        $script:Proposal.edit.content_sha256=Get-TestTextHash $script:Proposal.edit.content
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes; $oldAttempt=Get-TestJson $script:Attempt
        $message=Get-TestThrownMessage { Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted }
        Assert-Test ($message -ceq 'TEST_STALE_EDIT') 'Pending attempts still require their original edit identity.'
        Assert-Test ($script:Calls.writeAttempt -eq 0 -and $script:Calls.save -eq 0 -and (Get-TestJson $script:Attempt) -ceq $oldAttempt) 'Pending stale-edit refusal cannot authorize retry or alter the attempt.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'A new edit after explicit reconciliation binds the separate Save invocation' {
        Set-TestAttempt 'unchanged'
        $null=Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted
        $script:Proposal.edit.content='{"synthetic":"new edit after reconciliation"}'
        $script:Proposal.edit.content_sha256=Get-TestTextHash $script:Proposal.edit.content
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
        $result=Save-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256
        Assert-Test ($result.saved -eq $false -and $script:Calls.save -eq 1) 'Only the later explicit Save may reach the no-op boundary.'
        Assert-Test ($script:Writes[1].edit_sha256 -ceq $script:Proposal.edit.content_sha256) 'Pending retry uses the new edit identity, never stale edit text.'
        Assert-TestInputsUntouched $before $rawHash
    }
    Invoke-TestCase 'State changed after reconciliation prevents a subsequent explicit Save' {
        Set-TestAttempt 'unchanged'
        $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
        $null=Resolve-ForgeRejectedSave $script:Proposal.id -ConfirmNotCommitted
        $oldAttempt=Get-TestJson $script:Attempt; $script:ObservedStateSha=('d'*64)
        $message=Get-TestThrownMessage { Save-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256 }
        Assert-Test ($message.StartsWith('REJECTED_SAVE_RECONCILE:')) 'A later state change must invalidate retry authority.'
        Assert-Test ($script:Calls.save -eq 0 -and $script:Calls.validate -eq 1 -and $script:Calls.writeAttempt -eq 1) 'Later staleness must stop before another validation/write/save.'
        Assert-Test ((Get-TestJson $script:Attempt) -ceq $oldAttempt) 'Later refusal must not alter reconciled receipt.'
        Assert-TestInputsUntouched $before $rawHash
    }
} catch {
    $script:Cases.Add([pscustomobject]@{name='Harness setup or unexpected execution failure';status='FAIL';detail=$_.Exception.Message})
} finally {
    if ($null -ne $source) {
        Invoke-TestCase 'Canonical and owned copy bytes remain unchanged' {
            $source.after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.path))
            $source.copied_after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.copied_path))
            Assert-Test ($source.after_sha256 -ceq $source.before_sha256) 'Canonical source must remain byte-identical.'
            Assert-Test ($source.copied_after_sha256 -ceq $source.before_sha256) 'Parsed owned copy must remain byte-identical.'
        }
    }
    $failed=@($script:Cases | Where-Object {$_.status -ceq 'FAIL'}).Count
    $status=if ($failed -eq 0 -and $script:Loaded.Count -eq 2 -and $script:CheckCount -gt 0) {'PASS'} else {'FAIL'}
    $receipt=[ordered]@{
        schema='forge.noop_reconciliation_test_receipt.v1';run_id=$runId;status=$status;scope=$script:ScopeLabel;
        started_at=$started;completed_at=[DateTime]::UtcNow.ToString('o');module_root=$ModuleRoot;
        fresh_owned_test_root=$runRoot;explicit_check_count=$script:CheckCount;source=$source;
        loaded_functions=@($script:Loaded.ToArray());cases=@($script:Cases.ToArray());failed_cases=$failed;
        dependency_doubles=@('in-memory lock/read/write attempts','proposal validation response','committed revision lookup','persisted-state digest','attempt history','explicit save no-op acknowledgement');
        limitations=@('Reconciliation and retry dispatch only, not complete recovery end-to-end.','No real source/currentness validation, locking, atomic file write, draft commit, or approval.','Raw/edit preservation covers synthetic in-memory inputs.','External runner timeout supervision is required. A killed host may leave no receipt; timeout, crash, missing receipt, nonzero exit, or non-PASS receipt must be treated as failure.','Only this invocation and recorded exact source bytes are represented.')
    }
    $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 60)); $stream.Write($bytes,0,$bytes.Length) }
    finally { $stream.Dispose() }
    Write-Host ('Receipt: '+$receiptPath)
    Write-Host ('Scope: '+$script:ScopeLabel)
}
if ($status -cne 'PASS') { throw ('No-op reconciliation checks failed; fresh FAIL receipt: '+$receiptPath) }
Write-Host ('PASS: '+$script:CheckCount+' explicit checks; '+$script:Cases.Count+' cases. No end-to-end recovery claim.')

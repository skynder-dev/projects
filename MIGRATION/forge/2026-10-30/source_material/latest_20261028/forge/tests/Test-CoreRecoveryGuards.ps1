# Run only in a separately authorized PowerShell runner. This file does not import
# Forge, start a model, use the network, or read a real Forge workspace.
# Scope: function-level synthetic dependency doubles, NOT end-to-end recovery,
# semantic-review validation, approval issuance, ZIP validation, or publication.
# The authorized runner must supervise this process with an external timeout and
# treat a timeout, crash, nonzero exit, missing receipt, or non-PASS receipt as a
# failure. A killed host cannot guarantee a final receipt; GUID isolation only
# prevents an earlier invocation's PASS from being reused.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ModuleRoot)

$ErrorActionPreference = 'Stop'
$script:ScopeLabel = 'function-level synthetic dependency doubles'
$script:Checks = New-Object 'System.Collections.Generic.List[object]'
$script:Sources = @{}
$script:LoadedFunctions = New-Object 'System.Collections.Generic.List[object]'
$script:CheckCount = 0
$started = [DateTime]::UtcNow.ToString('o')
$runId = [Guid]::NewGuid().ToString('N')
$runRoot = Join-Path ([IO.Path]::GetTempPath()) ('forge-core-recovery-guards-' + $runId)
if (Test-Path -LiteralPath $runRoot) { throw 'Fresh test root already exists; refusing reuse.' }
[void][IO.Directory]::CreateDirectory($runRoot)
if ((Get-Item -LiteralPath $runRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Fresh test root is redirected; refusing use.'
}
$receiptPath = Join-Path $runRoot 'receipt.json'

function Get-TestBytesHash([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-TestTextHash([string]$Text) { return Get-TestBytesHash ([Text.Encoding]::UTF8.GetBytes($Text)) }
function Get-TestJson($Value) { return ConvertTo-Json -InputObject $Value -Depth 60 -Compress }
function Copy-TestObject($Value) { return ConvertFrom-Json -InputObject (Get-TestJson $Value) }
function Assert-Test([bool]$Condition, [string]$Message) {
    $script:CheckCount++
    if (!$Condition) { throw ('CHECK_FAILED: ' + $Message) }
}
function Invoke-TestCase([string]$Name, [scriptblock]$Body) {
    try {
        & $Body
        $script:Checks.Add([pscustomobject]@{name=$Name; status='PASS'; detail=''})
        Write-Host ('PASS: ' + $Name)
    } catch {
        $script:Checks.Add([pscustomobject]@{name=$Name; status='FAIL'; detail=$_.Exception.Message})
        Write-Host ('FAIL: ' + $Name + ': ' + $_.Exception.Message)
    }
}
function Get-TestThrownMessage([scriptblock]$Body) {
    try { $null = & $Body } catch { return $_.Exception.Message }
    throw 'CHECK_FAILED: expected an exception, but the call returned.'
}
function Reset-TestCalls {
    $script:Calls = @{
        readProposal=0; wire=0; parser=0; context=0; fields=0; saveDraft=0;
        readState=0; semantic=0; recovery=0; briefApproval=0; zip=0;
        publication=0; artwork=0; staging=0; stateWrite=0; receiptWrite=0;
        localConcept=0; commitReadback=0
    }
    $script:Errors = New-Object 'System.Collections.Generic.List[string]'
    $script:FlatFailure = ''
}

# In-memory dependency doubles. None is a function under test. Property/spec/JSON
# helpers cover only the plain PSCustomObject fixture domain below; they are not
# substitutes for Forge's production normalization or schema validation.
function Get-PropertyValue($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [Collections.IDictionary]) { return ,$Object[$Name] }
    $p = $Object.PSObject.Properties[$Name]
    if ($null -ne $p) { return ,$p.Value }
    return $null
}
function Add-OrSetProperty($Object, [string]$Name, $Value) {
    $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force
}
function Get-ForgeProductionSpec($Object) { return Get-PropertyValue $Object 'production_spec' }
function ConvertTo-ForgeBriefCanonicalJson($Value) { return Get-TestJson $Value }
function Get-ForgeBriefSha256($Value) { return Get-TestTextHash (Get-TestJson $Value) }
function Read-ForgeRejectedProposal([string]$Id) {
    $script:Calls.readProposal++
    if ($Id -cne $script:Proposal.id) { throw 'TEST_BAD_PROPOSAL_ID' }
    return $script:Proposal
}
function Assert-ForgeLocalAIWireContract([string]$Content, $Format) {
    $script:Calls.wire++
    if ($Content -cne $script:Proposal.edit.content) { throw 'TEST_WRONG_EDIT_PASSED_TO_WIRE' }
    if ($script:FlatFailure -ceq 'wire') { throw 'TEST_FLAT_WIRE_REJECTED' }
}
function ConvertFrom-ForgeLocalAIContent([string]$Content) {
    $script:Calls.parser++
    if ($Content -cne $script:Proposal.edit.content) { throw 'TEST_WRONG_EDIT_PASSED_TO_PARSER' }
    if ($script:FlatFailure -ceq 'parser') { throw 'TEST_FLAT_PARSER_REJECTED' }
    return Copy-TestObject $script:FlatFields
}
function Get-ForgeRejectedValidationContext($Proposal) {
    $script:Calls.context++
    return [pscustomobject]@{scope='synthetic evidence context, not a source archive'}
}
function Assert-ForgeAIFieldsForSave($Fields, $Context) {
    $script:Calls.fields++
    if ($script:FlatFailure -ceq 'fields') { throw 'TEST_FLAT_FIELDS_REJECTED' }
}
function Save-ForgeLocalAIDraft {
    $script:Calls.saveDraft++
    throw 'TEST_BOUNDARY_STOP: saving a real draft is forbidden'
}
function Read-LocalCoreState {
    $script:Calls.readState++
    return $script:PersistedState
}
function Get-ResearchDraft([string]$ConceptKey, $State=$null) {
    if ($null -eq $State) { $State = $script:PersistedState }
    foreach ($draft in @($State.drafts)) { if ($draft.concept_key -ceq $ConceptKey) { return $draft } }
    return $null
}
function Test-ForgeSemanticReviewCurrent($Draft) {
    # Deliberate dependency response, not an implementation of semantic review.
    # The source/freshness and receipt cryptography are outside this harness.
    $script:Calls.semantic++
    $script:LastSemanticDraft = $Draft
    if ($script:SemanticException) { throw $script:SemanticException }
    return [bool]$script:SemanticCurrentResponse
}
function Test-ForgeRecoveryReviewRequired($Lc) { $script:Calls.recovery++; return $false }
function Assert-ForgeBriefApproval($Approval, $Brief, [string]$Id, [string]$Hash) {
    $script:Calls.briefApproval++
    if ($Approval.approval_id -cne 'synthetic-approval-not-issued' -or $Id -cne 'synthetic-rev') {
        throw 'TEST_BAD_APPROVAL_FIXTURE'
    }
}
function Get-LocalReadyPackageZipAuthority {
    $script:Calls.zip++
    throw 'TEST_BOUNDARY_STOP: no real ZIP authority is provided'
}
function Get-LocalDeliveryReadiness { throw 'TEST_EXPECTED_EXPLICIT_CACHED_READINESS' }
function Get-LocalCoreConcept {
    $script:Calls.localConcept++
    return $script:Lc
}
function Save-LocalPublicationMetadata {
    $script:Calls.publication++
    throw 'TEST_BOUNDARY_STOP: publication metadata writes are forbidden'
}
function Get-LocalArtworkInfo { $script:Calls.artwork++; throw 'TEST_BOUNDARY_STOP: artwork access is forbidden' }
function Get-FileSha256Hex { $script:Calls.artwork++; throw 'TEST_BOUNDARY_STOP: artifact reads are forbidden' }
function Assert-LocalPackageWorkspacePath { $script:Calls.staging++; throw 'TEST_BOUNDARY_STOP: staging is forbidden' }
function Copy-LocalAcceptedArtworkForPackage { $script:Calls.staging++; throw 'TEST_BOUNDARY_STOP: artwork copy is forbidden' }
function Write-LocalCoreState { $script:Calls.stateWrite++; throw 'TEST_BOUNDARY_STOP: state writes are forbidden' }
function Write-LocalPackageReceipt { $script:Calls.receiptWrite++; throw 'TEST_BOUNDARY_STOP: export receipts are forbidden' }
function Get-LocalPackageCommitOutcome { $script:Calls.commitReadback++; return 'not_committed' }
function Show-Error([string]$Message) { $script:Errors.Add($Message) }
function Write-AppLog { }

function New-TestFields([string]$Tag) {
    return [pscustomobject][ordered]@{
        title=($Tag+' title'); hook=($Tag+' hook'); concept_text=($Tag+' concept');
        target_buyer=($Tag+' buyer'); purchase_reason=($Tag+' reason');
        differentiation=($Tag+' difference'); visual_direction_text=($Tag+' visual');
        production_spec=[pscustomobject][ordered]@{
            composition=($Tag+' layout'); illustration=($Tag+' illustration');
            ink_palette=@($Tag+' ink'); avoid=@($Tag+' avoid')
        }
    }
}
function New-TestRevision([int]$Number, [string]$Reason, [string]$Tag, [switch]$CanonicalHold) {
    $revision = New-TestFields $Tag
    Add-OrSetProperty $revision 'revision_no' $Number
    Add-OrSetProperty $revision 'reason' $Reason
    Add-OrSetProperty $revision 'revision_id' ('synthetic-revision-'+$Number)
    Add-OrSetProperty $revision 'revision_hash' (Get-TestTextHash ('synthetic-revision-'+$Number))
    if ($CanonicalHold) {
        Add-OrSetProperty $revision 'semantic_review_hold' ([pscustomobject]@{
            schema='forge.semantic_hold.v1'; status='PENDING'; meaning_verified=$false;
            canonical_record_id=('canonical-'+('a'*32)); revision_id=$revision.revision_id;
            revision_hash=$revision.revision_hash
        })
    }
    return $revision
}
function Set-TestProposal([string]$SchemaKind) {
    $props = [pscustomobject]@{title=[pscustomobject]@{type='string'}}
    if ($SchemaKind -in @('design','both')) { Add-OrSetProperty $props 'design' ([pscustomobject]@{type='object'}) }
    if ($SchemaKind -in @('owner_context','both')) { Add-OrSetProperty $props 'owner_context' ([pscustomobject]@{type='object'}) }
    $content = '{"synthetic_edited_proposal":"not production input"}'
    $script:Proposal = [pscustomobject]@{
        id=('rej-'+('b'*32)); raw_text='SYNTHETIC ORIGINAL RESPONSE - immutable test input';
        raw_bytes=[Text.Encoding]::UTF8.GetBytes('SYNTHETIC ORIGINAL RESPONSE - immutable test input');
        edit=[pscustomobject]@{content=$content; content_sha256=(Get-TestTextHash $content)};
        request=[pscustomobject]@{format=[pscustomobject]@{type='object'; properties=$props}};
        record=[pscustomobject]@{binding=[pscustomobject]@{concept_key=''; revision_id=''}}
    }
    $script:FlatFields = New-TestFields 'flat-synthetic'
}
function Set-TestPackageState([string]$ReviewOutcome, [bool]$HasHold, [bool]$CurrentReview) {
    Reset-TestCalls
    $script:SemanticCurrentResponse = $CurrentReview
    # Model the real dependency's exception surface, not archive/freshness validation.
    $script:SemanticException = if ($ReviewOutcome -ceq 'STALE_SOURCE') {'Reimport/review stale observations before Qwen use'} else {''}
    $script:LastSemanticDraft = $null
    $draft = [pscustomobject]@{
        concept_key='synthetic-concept'; current_revision_id='synthetic-rev';
        current_revision_hash=('c'*64); semantic_reviews=@([pscustomobject]@{outcome=$ReviewOutcome})
    }
    if ($HasHold) { Add-OrSetProperty $draft 'semantic_review_hold' ([pscustomobject]@{schema='forge.semantic_hold.v1';status='PENDING'}) }
    $script:PersistedState = [pscustomobject]@{drafts=@($draft); state_revision=2}
    $script:Current = $null
    $script:Dirty = $false
    $script:PublicationDirty = $false
    $brief = [pscustomobject]@{scope='synthetic brief, not approved by an owner'}
    $script:Identity = [pscustomobject]@{id='synthetic-rev';hash=('c'*64)}
    $script:Lc = [pscustomobject]@{
        concept_key='synthetic-concept'; generation_brief_snapshot=$brief;
        generation_brief_sha256=(Get-ForgeBriefSha256 $brief);
        brief_approval=[pscustomobject]@{approval_id='synthetic-approval-not-issued'};
        active_acceptance=[pscustomobject]@{scope='synthetic prerequisite only'}
    }
    $script:CachedReady = [pscustomobject]@{
        ready=$true; identity=$script:Identity;
        acceptance=[pscustomobject]@{lineage_fingerprint='synthetic-acceptance';asset_sha256=('d'*64)};
        listing_hash=('e'*64)
    }
    $script:Package = [pscustomobject]@{
        valid=$true; status='READY_FOR_MANUAL_UPLOAD'; concept_revision_id='synthetic-rev';
        revision_hash=('c'*64); acceptance_fingerprint='synthetic-acceptance';
        artwork_sha256=('d'*64); listing_hash=('e'*64)
    }
    $script:StatusText = [pscustomobject]@{Text=''}
    $script:DeliveryStatus = [pscustomobject]@{Text=''}
    $script:PublicationPreflight = [pscustomobject]@{Text=''}
    # A safe nonexistent destination; no artifact path is ever opened by these tests.
    $script:LocalCorePackageRoot = Join-Path $runRoot 'forbidden-artifacts'
}

$fatal = ''
try {
    $ModuleRoot = (Resolve-Path -LiteralPath $ModuleRoot).ProviderPath
    $copyRoot=Join-Path $runRoot 'exact-module-copies'
    [void][IO.Directory]::CreateDirectory($copyRoot)
    $targets = [ordered]@{
        'Forge.LocalAI.ps1'=@('Merge-ForgeLocalAIManualFields');
        'Forge.RejectedAI.ps1'=@('Test-ForgeRejectedProposal');
        'Forge.LocalCore.ps1'=@('Assert-ForgeNoSemanticHold','Get-LocalPackageBriefApprovalSnapshot','Test-LocalPackageCurrentAuthority','Build-LocalAmazonPackage')
    }
    foreach ($fileName in $targets.Keys) {
        $path = Join-Path $ModuleRoot $fileName
        $bytes = [IO.File]::ReadAllBytes($path)
        $copyPath=Join-Path $copyRoot $fileName
        [IO.File]::WriteAllBytes($copyPath,$bytes)
        $script:Sources[$fileName] = [pscustomobject]@{
            path=$path; before_sha256=(Get-TestBytesHash $bytes); after_sha256='';
            copied_path=$copyPath; copied_before_sha256=(Get-TestBytesHash ([IO.File]::ReadAllBytes($copyPath))); copied_after_sha256=''
        }
        Assert-Test ($script:Sources[$fileName].copied_before_sha256 -ceq $script:Sources[$fileName].before_sha256) ('Owned copy is byte-exact: '+$fileName)
        $tokens = $null; $parseErrors = $null
        $ast = [Management.Automation.Language.Parser]::ParseFile($copyPath, [ref]$tokens, [ref]$parseErrors)
        Assert-Test (@($parseErrors).Count -eq 0) ('Source must parse: '+$fileName)
        foreach ($name in $targets[$fileName]) {
            $definitions = @($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}, $false) | Where-Object {$_.Name -ceq $name})
            Assert-Test ($definitions.Count -eq 1) ('Exactly one target definition: '+$name)
            $definition = $definitions[0]
            # Only the exact target function definition is evaluated. No module
            # top-level statements, dot-source chain, or inferred replacement.
            . ([scriptblock]::Create($definition.Extent.Text))
            $loaded = Get-Command -Name $name -CommandType Function
            Assert-Test ($loaded.ScriptBlock.Ast.Extent.Text -ceq $definition.Body.Extent.Text) ('Loaded exact source body: '+$name)
            $script:LoadedFunctions.Add([pscustomobject]@{
                name=$name; source=$path; parsed_owned_copy=$copyPath; definition_sha256=(Get-TestTextHash $definition.Extent.Text);
                body_sha256=(Get-TestTextHash $loaded.ScriptBlock.Ast.Extent.Text);
                source_start_line=$definition.Extent.StartLineNumber
            })
        }
    }
    Assert-Test ($script:LoadedFunctions.Count -eq 6) 'All six actual functions must be loaded.'
    $script:ResearchDraftContentFields = @('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')

    Invoke-TestCase 'Exact revision-local canonical HOLD is a model revision, not an owner edit' {
        $base = New-TestRevision 1 'local_ai_draft_unapproved' 'base'
        $model = New-TestRevision 2 'canonical_semantic_hold' 'model' -CanonicalHold
        $next = New-TestFields 'next-model'
        $expected = Get-TestJson $next
        $actual = Merge-ForgeLocalAIManualFields ([pscustomobject]@{revisions=@($base,$model)}) $next
        Assert-Test ((Get-TestJson $actual) -ceq $expected) 'Canonical model text and production spec must not become protected owner fields.'
    }
    foreach ($variant in @('absent','wrong_revision_id','wrong_revision_hash','wrong_schema','wrong_status','meaning_verified_true','meaning_verified_string','wrong_record_id')) {
        Invoke-TestCase ('Owner canonical_semantic_hold reason remains protected: '+$variant) {
            $base = New-TestRevision 1 'local_ai_draft_unapproved' 'base'
            $owner = New-TestRevision 2 'canonical_semantic_hold' 'owner' -CanonicalHold
            switch ($variant) {
                'absent' { $owner.PSObject.Properties.Remove('semantic_review_hold') }
                'wrong_revision_id' { $owner.semantic_review_hold.revision_id = 'another-revision' }
                'wrong_revision_hash' { $owner.semantic_review_hold.revision_hash = ('f'*64) }
                'wrong_schema' { $owner.semantic_review_hold.schema = 'not-a-canonical-hold' }
                'wrong_status' { $owner.semantic_review_hold.status = 'REVIEWED' }
                'meaning_verified_true' { $owner.semantic_review_hold.meaning_verified = $true }
                'meaning_verified_string' { $owner.semantic_review_hold.meaning_verified = 'false' }
                'wrong_record_id' { $owner.semantic_review_hold.canonical_record_id = 'not-canonical' }
            }
            $actual = Merge-ForgeLocalAIManualFields ([pscustomobject]@{revisions=@($base,$owner)}) (New-TestFields 'next')
            foreach ($field in $script:ResearchDraftContentFields) {
                Assert-Test ($actual.$field -ceq $owner.$field) ('Owner text must survive: '+$field)
            }
            Assert-Test ((Get-TestJson $actual.production_spec) -ceq (Get-TestJson $owner.production_spec)) 'Owner production spec must survive.'
        }
    }
    Invoke-TestCase 'Manual text, spec values, and spec deletions before and after model revisions survive' {
        $base = New-TestRevision 1 'local_ai_draft_unapproved' 'base'
        $before = Copy-TestObject $base
        $before.revision_no=2; $before.reason='owner edit before model'; $before.revision_id='owner-before'
        $before.title='OWNER title before'; $before.production_spec.composition='OWNER layout before'
        $before.production_spec.PSObject.Properties.Remove('avoid')
        $model = New-TestRevision 3 'canonical_semantic_hold' 'intermediate-model' -CanonicalHold
        $after = Copy-TestObject $model
        $after.revision_no=4; $after.reason='owner edit after model'; $after.revision_id='owner-after'
        $after.hook='OWNER hook after'; $after.production_spec.illustration='OWNER illustration after'
        $after.production_spec.ink_palette=@('OWNER red','OWNER black')
        $actual = Merge-ForgeLocalAIManualFields ([pscustomobject]@{revisions=@($after,$base,$model,$before)}) (New-TestFields 'next')
        Assert-Test ($actual.title -ceq 'OWNER title before') 'Manual text before model must survive.'
        Assert-Test ($actual.hook -ceq 'OWNER hook after') 'Manual text after model must survive.'
        Assert-Test ($actual.concept_text -ceq 'next concept') 'Untouched text must remain model-editable.'
        Assert-Test ($actual.production_spec.composition -ceq 'OWNER layout before') 'Manual spec before model must survive.'
        Assert-Test ($actual.production_spec.illustration -ceq 'OWNER illustration after') 'Manual spec after model must survive.'
        Assert-Test ((Get-TestJson $actual.production_spec.ink_palette) -ceq '["OWNER red","OWNER black"]') 'Manual array-valued spec must survive.'
        Assert-Test ($null -eq $actual.production_spec.PSObject.Properties['avoid']) 'Manual spec deletion must survive a later model revision.'
    }
    Invoke-TestCase 'Existing local_ai revision behavior remains model-editable' {
        $base=New-TestRevision 1 'local_ai_draft_unapproved' 'base'
        $model=New-TestRevision 2 'local_ai_revision_unapproved' 'model'
        $next=New-TestFields 'next'; $expected=Get-TestJson $next
        $actual=Merge-ForgeLocalAIManualFields ([pscustomobject]@{revisions=@($base,$model)}) $next
        Assert-Test ((Get-TestJson $actual) -ceq $expected) 'Existing local_ai revisions must still be skipped.'
    }

    foreach ($kind in @('design','owner_context','both')) {
        Invoke-TestCase ('Canonical rejected schema refuses before legacy dependencies: '+$kind) {
            Reset-TestCalls; Set-TestProposal $kind
            $before=Get-TestJson $script:Proposal; $rawHash=Get-TestBytesHash $script:Proposal.raw_bytes
            $message=Get-TestThrownMessage { Test-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256 }
            Assert-Test ($message -ceq 'REJECTED_CANONICAL_RECOVERY_UNAVAILABLE: Original canonical response and edited copy are retained. This legacy review path cannot safely save canonical proposals; no draft or approval was changed.') 'Exact canonical refusal must identify unavailable recovery.'
            Assert-Test ($script:Calls.readProposal -eq 1) 'The real target must read the retained proposal.'
            foreach ($name in @('wire','parser','context','fields','saveDraft','stateWrite')) { Assert-Test ($script:Calls[$name] -eq 0) ('Canonical refusal precedes '+$name) }
            Assert-Test ((Get-TestJson $script:Proposal) -ceq $before) 'Raw and edited proposal objects remain unchanged.'
            Assert-Test ((Get-TestBytesHash $script:Proposal.raw_bytes) -ceq $rawHash) 'Raw original bytes remain unchanged.'
        }
    }
    Invoke-TestCase 'Flat proposal still traverses validators and receives only the existing rejection marker' {
        Reset-TestCalls; Set-TestProposal 'flat'; $before=Get-TestJson $script:Proposal
        $result=Test-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256
        foreach ($name in @('readProposal','wire','parser','context','fields')) { Assert-Test ($script:Calls[$name] -eq 1) ('Flat validation dependency reached exactly once: '+$name) }
        Assert-Test ($result.fields.__forge_rejection_id -ceq $script:Proposal.id) 'Existing marker must contain exact rejected id.'
        Assert-Test ($result.mechanical_valid -eq $true -and $result.semantic_verified -eq $false -and $result.approved -eq $false) 'Mechanical validation must not confer semantic or owner approval.'
        $expected=Copy-TestObject $script:FlatFields; Add-OrSetProperty $expected '__forge_rejection_id' $script:Proposal.id
        Assert-Test ((Get-TestJson $result.fields) -ceq (Get-TestJson $expected)) 'Only the established rejection marker is added.'
        Assert-Test ((Get-TestJson $script:Proposal) -ceq $before) 'Flat raw/edit input remains unchanged.'
        Assert-Test ($script:Calls.saveDraft -eq 0) 'Validation must not save.'
    }
    foreach ($boundary in @('wire','parser','fields')) {
        Invoke-TestCase ('Flat validator failures still stop validation: '+$boundary) {
            Reset-TestCalls; Set-TestProposal 'flat'; $before=Get-TestJson $script:Proposal; $script:FlatFailure=$boundary
            $message=Get-TestThrownMessage { Test-ForgeRejectedProposal $script:Proposal.id $script:Proposal.edit.content_sha256 }
            Assert-Test ($message -ceq ('TEST_FLAT_'+$boundary.ToUpperInvariant()+'_REJECTED')) 'Original validator failure must propagate.'
            Assert-Test ($script:Calls[$boundary] -eq 1) 'The selected validation boundary must actually run.'
            if ($boundary -ceq 'wire') { Assert-Test ($script:Calls.parser -eq 0) 'Wire rejection must precede parser.' }
            Assert-Test ($script:Calls.saveDraft -eq 0 -and (Get-TestJson $script:Proposal) -ceq $before) 'Failed validation must not save or mutate retained bytes.'
        }
    }

    foreach ($outcome in @('NEEDS_EDIT','REJECTED','STALE_SOURCE')) {
        Invoke-TestCase ('Fresh semantic refusal blocks package brief approval: '+$outcome) {
            Set-TestPackageState $outcome $true $false
            $before=Get-TestJson $script:PersistedState
            $approval=Get-LocalPackageBriefApprovalSnapshot $script:Lc $script:Identity
            Assert-Test (!$approval.approved -and $approval.reason -ceq 'semantic_review_required') 'Negative/stale review denies package approval with the semantic-specific reason.'
            Assert-Test ($script:Calls.readState -eq 1 -and $script:Calls.semantic -eq 1) 'Real semantic HOLD guard must read persisted state and call the current-review dependency.'
            Assert-Test ($script:Calls.briefApproval -eq 0 -and $script:Calls.recovery -eq 0) 'Semantic gate must run before other approval dependencies.'
            Assert-Test ((Get-TestJson $script:PersistedState) -ceq $before) 'Guard must not mutate state.'
        }
        Invoke-TestCase ('Cached ready snapshot cannot bypass real semantic HOLD guard: '+$outcome) {
            Set-TestPackageState $outcome $true $false
            $supplied=Copy-TestObject $script:PersistedState
            $supplied.drafts[0].semantic_reviews=@([pscustomobject]@{outcome='REVIEWED_FOR_NEXT_REVIEW_STAGE'})
            $result=Test-LocalPackageCurrentAuthority $script:Package $script:Lc $script:CachedReady $supplied
            Assert-Test (!$result) 'Cached-ready package authority must be denied.'
            Assert-Test ($script:Calls.readState -eq 1 -and $script:Calls.semantic -eq 1) 'Denial must come through the actual semantic guard, not an unrelated missing package fixture.'
            Assert-Test ([object]::ReferenceEquals($script:LastSemanticDraft,$supplied.drafts[0])) 'Guard must pass the supplied draft to the semantic-current dependency for freshness verification.'
            Assert-Test ($script:Calls.zip -eq 0 -and $script:Calls.artwork -eq 0) 'Semantic refusal must precede archive/artifact validation.'
        }
        Invoke-TestCase ('Build stops before listing, artwork, or staging: '+$outcome) {
            Set-TestPackageState $outcome $true $false
            $script:Current=[pscustomobject]@{concept=[pscustomobject]@{concept_key='synthetic-concept'}}
            $before=Get-TestJson $script:PersistedState
            $null=Build-LocalAmazonPackage
            Assert-Test ($script:Calls.readState -eq 1 -and $script:Calls.semantic -eq 1) 'Build must invoke real semantic guard before any builder state read.'
            $expectedRefusal=if ($outcome -ceq 'STALE_SOURCE') {'Reimport/review stale observations before Qwen use'} else {'SEMANTIC_REVIEW_HOLD:'}
            Assert-Test ($script:Errors.Count -eq 1 -and $script:Errors[0].StartsWith($expectedRefusal)) 'Build must expose the semantic/source refusal, not a later incidental failure.'
            foreach ($name in @('localConcept','publication','artwork','staging','stateWrite','receiptWrite','saveDraft')) { Assert-Test ($script:Calls[$name] -eq 0) ('Build must not cross '+$name) }
            Assert-Test ($script:Calls.commitReadback -eq 1) 'Existing catch/readback path remains exercised.'
            Assert-Test (!(Test-Path -LiteralPath $script:LocalCorePackageRoot)) 'No staging/export directory may be created.'
            Assert-Test ((Get-TestJson $script:PersistedState) -ceq $before) 'Build refusal must leave synthetic persisted state unchanged.'
        }
    }
    Invoke-TestCase 'Persisted HOLD cannot be bypassed by supplied state lacking the HOLD' {
        Set-TestPackageState 'NEEDS_EDIT' $true $true
        $withoutHold=Copy-TestObject $script:PersistedState; $withoutHold.drafts[0].PSObject.Properties.Remove('semantic_review_hold')
        $message=Get-TestThrownMessage { Assert-ForgeNoSemanticHold 'synthetic-concept' $withoutHold }
        Assert-Test ($message.StartsWith('SEMANTIC_REVIEW_HOLD:')) 'Missing supplied HOLD must fail closed against persisted HOLD.'
        Assert-Test ($script:Calls.readState -eq 1 -and $script:Calls.semantic -eq 0) 'Missing supplied HOLD is rejected before semantic-current response.'
    }
    foreach ($path in @('legacy_no_hold','current_review')) {
        Invoke-TestCase ('Package brief approval positive control: '+$path) {
            $hasHold=($path -ceq 'current_review')
            Set-TestPackageState 'REVIEWED_FOR_NEXT_REVIEW_STAGE' $hasHold $true
            $before=Get-TestJson $script:PersistedState
            $approval=Get-LocalPackageBriefApprovalSnapshot $script:Lc $script:Identity
            Assert-Test ($approval.approved -eq $true -and $approval.reason -ceq 'exact_saved_idea_and_design_approved') 'Existing approval path must remain reachable with labeled synthetic prerequisites.'
            Assert-Test ($script:Calls.readState -eq 1) 'Positive control must still read persisted state.'
            Assert-Test ($script:Calls.semantic -eq [int]$hasHold) 'Semantic-current dependency is required only for HOLD fixtures.'
            Assert-Test ($script:Calls.briefApproval -eq 1 -and $script:Calls.recovery -eq 1) 'Other existing approval dependencies must run.'
            Assert-Test ($script:Calls.stateWrite -eq 0 -and (Get-TestJson $script:PersistedState) -ceq $before) 'No real or synthetic approval record is written.'
        }
        Invoke-TestCase ('Build positive control reaches only the forbidden write sentinel: '+$path) {
            $hasHold=($path -ceq 'current_review')
            Set-TestPackageState 'REVIEWED_FOR_NEXT_REVIEW_STAGE' $hasHold $true
            $script:Current=[pscustomobject]@{concept=[pscustomobject]@{concept_key='synthetic-concept'}}
            $null=Build-LocalAmazonPackage
            Assert-Test ($script:Calls.publication -eq 1) 'Nonblocking HOLD state must reach existing publication boundary.'
            Assert-Test ($script:Calls.semantic -eq [int]$hasHold) 'Real HOLD guard path must match the fixture.'
            Assert-Test ($script:Errors.Count -eq 1 -and $script:Errors[0] -ceq 'TEST_BOUNDARY_STOP: publication metadata writes are forbidden') 'The test must stop at its labeled boundary, never export.'
            Assert-Test ($script:Calls.artwork -eq 0 -and $script:Calls.staging -eq 0 -and $script:Calls.stateWrite -eq 0) 'Positive control must not create real artifacts or state.'
            Assert-Test (!(Test-Path -LiteralPath $script:LocalCorePackageRoot)) 'Positive control creates no package directory.'
        }
    }
} catch {
    $fatal=$_.Exception.Message
    $script:Checks.Add([pscustomobject]@{name='Harness setup or unexpected execution failure';status='FAIL';detail=$fatal})
} finally {
    foreach ($fileName in @($script:Sources.Keys)) {
        Invoke-TestCase ('Canonical source bytes unchanged: '+$fileName) {
            $source=$script:Sources[$fileName]
            $source.after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.path))
            $source.copied_after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.copied_path))
            Assert-Test ($source.after_sha256 -ceq $source.before_sha256) 'Canonical module source bytes changed during the test.'
            Assert-Test ($source.copied_after_sha256 -ceq $source.before_sha256) 'Owned exact module copy changed during the test.'
        }
    }
    $failed=@($script:Checks | Where-Object {$_.status -ceq 'FAIL'}).Count
    $status=if ($failed -eq 0 -and $script:LoadedFunctions.Count -eq 6 -and $script:CheckCount -gt 0) {'PASS'} else {'FAIL'}
    $receipt=[ordered]@{
        schema='forge.function_guard_test_receipt.v1'; run_id=$runId; status=$status;
        scope=$script:ScopeLabel; started_at=$started; completed_at=[DateTime]::UtcNow.ToString('o');
        module_root=$ModuleRoot; fresh_owned_test_root=$runRoot; explicit_check_count=$script:CheckCount;
        sources=@($script:Sources.Values); loaded_functions=@($script:LoadedFunctions.ToArray());
        cases=@($script:Checks.ToArray()); failed_cases=$failed;
        dependency_doubles=@('plain-object property/spec/JSON helpers','retained proposal reads','wire/parser/save validation boundaries','persisted state reads','semantic-current response','other approval prerequisites','UI error reporting','forbidden write/artifact boundaries');
        limitations=@('No full module import or full-stack claim.','Semantic-current response is a dependency double: real receipt/source freshness is not tested.','Flat schema validators are call/failure-propagation doubles, not schema correctness tests.','No actual owner approval, draft write, model inference, package ZIP, source archive, network call, export, or publication.','External runner timeout supervision is required. A killed host may leave no receipt; timeout, crash, missing receipt, nonzero exit, or non-PASS receipt must be treated as failure.','This receipt applies only to this invocation and the recorded exact module bytes.')
    }
    # CreateNew and a GUID-owned root prevent a previous PASS receipt from being
    # mistaken for this invocation. Normally completed failures write FAIL;
    # forced termination requires the external supervisor described above.
    $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $bytes=[Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 60)); $stream.Write($bytes,0,$bytes.Length) }
    finally { $stream.Dispose() }
    Write-Host ('Receipt: '+$receiptPath)
    Write-Host ('Scope: '+$script:ScopeLabel)
}
if ($status -cne 'PASS') { throw ('Core recovery guard checks failed; fresh FAIL receipt: '+$receiptPath) }
Write-Host ('PASS: '+$script:CheckCount+' explicit checks; '+$script:Checks.Count+' cases. No full-stack claim.')
